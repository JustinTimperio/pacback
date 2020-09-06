#! /usr/bin/env python3
import re
import os
import stat
import itertools
import multiprocessing as mp

# Local Modules
import paf


##############################
# Utils For Other Functions
############################

def remove_id(config, info):
    '''
    Remove a selected id based on type.
    '''
    fname = "utils.remove_id(" + info['type'] + info['id'] + ")"

    paf.rm_file(info['meta'], sudo=False)
    paf.rm_file(info['meta_md5'], sudo=False)
    if info['type'] == 'rp':
        paf.rm_dir(info['path'], sudo=False)

    paf.write_to_log(fname, 'Removal Complete', config['log'])


def find_pkgs_in_dir(path):
    '''
    Scans a target directory for files ending
    in the `.pkg.tar.zst` and `.pkg.tar.xz` extensions.
    '''
    cache = {f for f in paf.find_files(path)
             if f.endswith(".pkg.tar.xz") or f.endswith(".pkg.tar.zst")}
    return cache


def first_pkg_path(pkgs, fs_list):
    '''
    This is a throwaway function for processing paths in chunks.
    This scans a set of paths for a file, adding only the first result.
    '''
    paths = list()
    for pkg in pkgs:
        for f in fs_list:
            if f.split('/')[-1] == pkg:
                paths.append(f)
                break
    return paths


def trim_pkg_list(pkg_list):
    '''
    Removes prefix dir and x86_64.pkg.tar.zsd suffix.
    This seems to be the fastest way too reduce all file paths to a unique
    list of package versions present on the system.
    '''
    return {'-'.join(pkg.split('-')[:-1]) for pkg in paf.basenames(pkg_list)}


def search_pkg_chunk(search, fs_list):
    '''
    This is a throwaway function for processing pkgs in chunks.
    This takes a search term and returns the files that match.
    For reasons I don't totally understand, this function must
    exist outside of scan_caches() for local objects to be pickled.
    '''
    pkgs = list()
    for f in fs_list:
        if re.findall(search, f.lower()):
            pkgs.append(f)
    return pkgs


def user_pkg_search(search_pkg, cache):
    '''
    Provides more accurate searches for single pkg names without a version.
    '''
    pkgs = trim_pkg_list(cache)
    found = set()

    for p in pkgs:
        r = re.split("\d+-\d+|\d+(?:\.\d+)+|\d:\d+(?:\.\d+)+", p)[0]
        if r.strip()[-1] == '-':
            r = r.strip()[:-1]
        if re.fullmatch(re.escape(search_pkg.lower().strip()), r):
            found.add(p)

    if not found:
        paf.prWarning('No Packages Found! Extending Regex Search...')
        for p in pkgs:
            if re.findall(re.escape(search_pkg.lower().strip()), p):
                found.add(p)

    return found


def fetch_new_mirrorlist():
    '''
    Allows a user to fetch a new Arch Linux mirrorlist directly.
    Returns True if the download ran successfully and False if not.
    '''
    countries = ['all', 'US', 'CA', 'GB', 'AU', 'FR', 'DE', 'NL', 'JP', 'KR']
    country = paf.multi_choice_frame(countries)
    if country is not False:
        url = 'https://www.archlinux.org/mirrorlist/?country=' + country + '&protocol=https&use_mirror_status=on'
        paf.download_url(url, '/etc/pacman.d/mirrorlist')
        paf.sed_uncomment_line('Server', '/etc/pacman.d/mirrorlist', sudo=False)
        return True
    else:
        return False


############################
# Package And Cache Utils
##########################

def pacman_Q():
    '''
    Writes the output into /tmp, reads file, then removes file.
    '''
    os.system("pacman -Q > /tmp/pacman_q")
    pkg_list = paf.read_file('/tmp/pacman_q', typ='set')
    paf.rm_file('/tmp/pacman_q', sudo=False)
    return pkg_list


def scan_caches(config):
    '''
    Always returns a unique list of pkgs found on the file sys.
    When searching through rp directories, many 'duplicate' hardlinked files exist.
    This logic ensures that the list of packages returned is actually unique.
    '''
    fname = 'utils.scan_caches()'
    paf.write_to_log(fname, 'Started Scaning Directories for Packages...', config['log'])

    # Searches Known Package Cache Locations
    fs_paths = {config['basepath'], '/var/cache/pacman/pkg'}
    for u in os.listdir('/home'):
        fs_paths.add('/home/' + u + '/.cache')
    pkg_paths = find_pkgs_in_dir(fs_paths)
    unique_pkgs = paf.basenames(pkg_paths)
    paf.write_to_log(fname, 'Searched ALL Package Cache Locations', config['log'])

    # Branch If Filter Is Needed
    if len(pkg_paths) != len(unique_pkgs):
        # Find Unique Packages By Inode Number
        inodes = set()
        filter_fs = set()

        for x in pkg_paths:
            i = os.lstat(x)[stat.ST_INO]
            if i in inodes:
                pass
            else:
                filter_fs.add(x)
                inodes.add(i)

        #################################
        # THIS SHOULD BASICALLY NEVER RUN
        #################################
        if len(filter_fs) != len(unique_pkgs):
            paf.write_to_log(fname, 'File System is Messed Up and The User Has Somehow Duplicated Files!', config['log'])
            paf.write_to_log(fname, 'Attempting to Filter Packages With Regex...', config['log'])
            thread_cap = 4

            # This Chunks the List of unique_pkgs Into Peices
            chunk_size = int(round(len(unique_pkgs) / paf.max_threads(thread_cap), 0)) + 1
            unique_pkgs = list(f for f in unique_pkgs)
            chunks = [unique_pkgs[i:i + chunk_size] for i in range(0, len(unique_pkgs), chunk_size)]

            # Creates Pool of Threads to Filter Based on File Name
            with mp.Pool(processes=paf.max_threads(thread_cap)) as pool:
                filter_fs = pool.starmap(first_pkg_path, zip(chunks, itertools.repeat(pkg_paths)))
                filter_fs = set(itertools.chain(*filter_fs))

        paf.write_to_log(fname, 'Returned ' + str(len(filter_fs)) + ' Unique Cache Packages', config['log'])
        return filter_fs

    else:
        paf.write_to_log(fname, 'Returned ' + str(len(pkg_paths)) + ' Cached Packages', config['log'])
        return pkg_paths


def search_cache(pkg_list, fs_list, config):
    '''
    Searches the cache for matching pkg versions and returns results.
    Because of the way files are named, and the output given by pacman -Q
    regex is needed to find the version reported to the package path.
    No performance is gained with more than 4 threads on this function.
    '''
    fname = 'utils.search_cache(' + str(len(pkg_list)) + ')'
    thread_cap = 4

    # Combing package names into one term provides much faster results
    paf.write_to_log(fname, 'Started Search for Matching Versions...', config['log'])
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in pkg_list)))

    # Chunks list of searches into peices for multi-threaded search
    chunk_size = int(round(len(fs_list) / paf.max_threads(thread_cap), 0)) + 1
    fs_list = list(f for f in fs_list)
    chunks = [fs_list[i:i + chunk_size] for i in range(0, len(fs_list), chunk_size)]

    # Creates Pool of Threads to Run Regex Searches
    with mp.Pool(processes=paf.max_threads(thread_cap)) as pool:
        found_pkgs = pool.starmap(search_pkg_chunk, zip(itertools.repeat(bulk_search), chunks))
        found_pkgs = set(itertools.chain(*found_pkgs))

    paf.write_to_log(fname, 'Found ' + str(len(found_pkgs)) + ' OUT OF ' + str(len(pkg_list)) + ' Packages', config['log'])
    return found_pkgs


################################
# Pacman Pre-Transaction Hook
##############################

def pacman_hook(install, config):
    '''
    Installs or removes a standard alpm hook in /etc/pacman.d/hooks
    This runs as a PreTransaction hook during every transaction.
    `install = True` Installs Pacman Hook
    `install = False` Removes Pacman Hook
    '''

    if install is True:
        fname = 'utils.pacman_hook(install)'
        paf.write_to_log(fname, 'Starting Hook Installation...', config['log'])

        paf.mk_dir('/etc/pacman.d/hooks', sudo=False)
        paf.sed_uncomment_line('HookDir', '/etc/pacman.conf', sudo=False)
        hook = [
                '[Trigger]',
                'Operation = Install',
                'Operation = Remove',
                'Operation = Upgrade',
                'Type = Package',
                'Target = *',
                '',
                '[Action]',
                'Description = Pre-Upgrade Pacback Hook',
                'Depends = pacman',
                'When = PreTransaction',
                'Exec = /usr/bin/pacback --hook'
                ]

        paf.export_iterable('/etc/pacman.d/hooks/pacback.hook', hook)
        paf.prSuccess('Pacback Hook is Now Installed!')
        paf.write_to_log(fname, 'Installed Pacback PreTransaction Hook', config['log'])

    elif install is False:
        fname = 'utils.pacman_hook(remove)'
        paf.write_to_log(fname, 'Starting Hook Removal...', config['log'])

        paf.rm_file('/etc/pacman.d/hooks/pacback.hook', sudo=False)
        paf.write_to_log(fname, 'Removed Pacback PreTransaction Hook', config['log'])
        paf.prSuccess('Pacback Hook Was Removed!')


###################################
# Check If Kernel Needs A Reboot
#################################

def reboot_check(config):
    '''
    Checks running and installed kernel versions to determine if
    a reboot is needed.
    '''
    fname = 'utils.reboot_check()'

    os.system("file -bL /boot/vmlinuz* | grep -o 'version [^ ]*' | cut -d ' ' -f 2 > /tmp/reboot_check")
    os.system("uname -r >> /tmp/reboot_check")
    raw = paf.read_file('/tmp/reboot_check', 'list')
    paf.rm_file('/tmp/reboot_check', sudo=False)

    if raw[0].strip() != raw[1].strip():
        paf.write_to_log(fname, 'The Installed Kernel Has Changed From ' + raw[1].strip() + ' To ' + raw[0].strip(), config['log'])
        paf.prWarning('Your Installed Kernel Has Changed From ' + raw[1].strip() + ' To ' + raw[0].strip() + ' and a Reboot Is Needed!')

        if config['reboot'] is True:
            if paf.yn_frame('Do You Want To Schedule A Reboot In ' + str(config['reboot_offset']) + ' Minutes?') is True:
                os.system("shutdown -r $(date --date='" + str(config['reboot_offset']) + " minute' +%H:%M)")
                paf.write_to_log(fname, 'User Scheduled A Reboot In ' + str(config['reboot_offset']) + ' Minutes', config['log'])
            else:
                paf.write_to_log(fname, 'User Declined System Reboot', config['log'])
        else:
            paf.write_to_log(fname, 'A Reboot Is Needed For The Whole Downgrade To Take Affect!', config['log'])

    else:
        paf.write_to_log(fname, 'The Kernel Hasn\'t Been Changed, A Reboot is Unnecessary', config['log'])


################################
# Get Size of Cached Packages
##############################

def cache_size(config):
    '''
    Gets the size of cached packages reported by applications like du,
    and also the real size without counting hardlinks more than once.
    '''
    fname = 'utils.cache_size()'
    paf.write_to_log(fname, 'Started Calculating Cache Size...', config['log'])

    # Wish I Didn't Have to Copy This Code Over
    fs_paths = {config['basepath'], '/var/cache/pacman/pkg'}
    for u in os.listdir('/home'):
        fs_paths.add('/home/' + u + '/.cache')
    all_paths = find_pkgs_in_dir(fs_paths)
    unique_paths = scan_caches(config)

    # Calculate Size On Disk
    reported_size = paf.convert_size(paf.size_of_files(all_paths))
    actual_size = paf.convert_size(paf.size_of_files(unique_paths))
    paf.write_to_log(fname, 'Returning Cache Size', config['log'])

    return (reported_size, actual_size)
