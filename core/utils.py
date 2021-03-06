#! /usr/bin/env python3
import re
import os
import stat
import itertools
import subprocess
import multiprocessing as mp

# Local Modules
import paf


##############################
# Utils For Other Functions
############################

def remove_id(config, info):
    '''Remove a selected id based on type.'''
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
        if re.search(search, f.lower()):
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

def find_cache_paths(config):
    '''
    Fetch a list of every normal users configured homepath
    '''
    paths = list()
    for line in paf.read_file('/etc/pacman.conf'):
        if line.startswith('CacheDir'):
            paths.append(line.split('=')[-1].strip())

    if not paths:
        paths.append('/var/cache/pacman/pkg')

    for u in paf.list_normal_users():
        if os.path.exists(u[5] + '/.cache'):
            paths.append(u[5] + '/.cache')

    paths.append(config['basepath'])

    return paths


def pacman_Q():
    '''
    Captures the output of `pacman -Q` from stdout
    '''
    raw = subprocess.Popen('/usr/bin/pacman -Q', stdout=subprocess.PIPE, shell=True)
    out = str(raw.communicate())[3:]
    out = out.split('\n')
    out = set(out[0].split('\\n')[:-1])
    return out


def scan_caches(config):
    '''
    Always returns a unique list of pkgs found on the file sys.
    When searching through rp directories, many 'duplicate' hardlinked files exist.
    This logic ensures that the list of packages returned is actually unique.
    '''
    fname = 'utils.scan_caches()'
    paf.write_to_log(fname, 'Started Scaning Directories for Packages...', config['log'])

    # Searches Known Package Cache Locations
    pkg_paths = find_pkgs_in_dir(find_cache_paths(config))
    unique_pkgs = list(paf.basenames(pkg_paths))
    paf.write_to_log(fname, 'Searched ALL Package Cache Locations', config['log'])

    # Branch If Filter Is Needed
    if len(pkg_paths) != len(unique_pkgs):
        # Find Unique Packages By Inode Number
        inodes = set()
        inode_filter = set()

        for x in pkg_paths:
            i = os.lstat(x)[stat.ST_INO]
            if i in inodes:
                pass
            else:
                inode_filter.add(x)
                inodes.add(i)

        paf.write_to_log(fname, 'Found ' + str(len(inode_filter)) + ' Package Inode\'s!', config['log'])

        if len(inode_filter) != len(unique_pkgs):
            # THIS SHOULD BASICALLY NEVER RUN
            paf.write_to_log(fname, 'File System Contains None-Hardlinked Duplicate Packages!', config['log'])
            paf.write_to_log(fname, 'Attempting to Filter Packages With Regex...', config['log'])
            thread_cap = 4

            # This Chunks the List of unique_pkgs Into Peices
            chunk_size = int(round(len(unique_pkgs) / paf.max_threads(thread_cap), 0)) + 1
            chunks = [unique_pkgs[i:i + chunk_size] for i in range(0, len(unique_pkgs), chunk_size)]

            # Creates Pool of Threads to Filter Based on File Name
            with mp.Pool(processes=paf.max_threads(thread_cap)) as pool:
                filter_fs = pool.starmap(first_pkg_path, zip(chunks, itertools.repeat(inode_filter)))
                filter_fs = set(itertools.chain(*filter_fs))

        else:
            filter_fs = inode_filter

        paf.write_to_log(fname, 'Returned ' + str(len(filter_fs)) + ' Unique Cache Packages', config['log'])
        return filter_fs

    else:
        paf.write_to_log(fname, 'Returned ' + str(len(pkg_paths)) + ' Cached Packages', config['log'])
        return pkg_paths


def search_cache(pkg_list, fs_list, config):
    '''
    Searches the cache for matching pkg versions and returns the results.
    Because of the way files are named and the output given by pacman -Q,
    regex is needed to find the version in the cached package path.
    No performance is gained with more than 4 threads on this function.
    '''
    fname = 'utils.search_cache(' + str(len(pkg_list)) + ')'
    thread_cap = 4

    # Combing Package Names Into One Term Provides Much Faster Results
    paf.write_to_log(fname, 'Started Search for Matching Versions...', config['log'])
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in pkg_list)))

    # Chunks List of Searches Into Peices For Multi-Threaded Search
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
    Installs or removes a standard alpm hook in /usr/share/libalpm/hooks/
    which runs as a PreTransaction hook during every pacman transaction.
    `install = True` Installs Pacman Hook
    `install = False` Removes Pacman Hook
    '''

    if install is True:
        fname = 'utils.pacman_hook(install)'
        paf.write_to_log(fname, 'Starting Hook Installation...', config['log'])

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

        paf.export_iterable('/usr/share/libalpm/hooks/pacback.hook', hook)
        paf.prSuccess('Pacback Hook is Now Installed!')
        paf.write_to_log(fname, 'Installed Pacback PreTransaction Hook', config['log'])

    elif install is False:
        fname = 'utils.pacman_hook(remove)'
        paf.write_to_log(fname, 'Starting Hook Removal...', config['log'])

        paf.rm_file('/usr/share/libalpm/hooks/pacback.hook', sudo=False)
        paf.write_to_log(fname, 'Removed Pacback PreTransaction Hook', config['log'])
        paf.prSuccess('Pacback Hook Was Removed!')


###################################
# Check If Kernel Needs A Reboot
#################################

def reboot_check(config):
    '''
    Checks the running and installed kernel versions
    to determine if a reboot is needed.
    '''
    fname = 'utils.reboot_check()'

    cmd = "file -bL /boot/vmlinuz* | grep -o 'version [^ ]*' | cut -d ' ' -f 2 && uname -r"
    raw = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out = str(raw.communicate())[3:]
    out = out.split('\n')
    out = out[0].split('\\n')[:-1]

    if out[0].strip() != out[1].strip():
        paf.write_to_log(fname, 'The Installed Kernel Has Changed From ' + out[1].strip() + ' To ' + out[0].strip(), config['log'])
        paf.prWarning('Your Installed Kernel Has Changed From ' + out[1].strip() + ' To ' + out[0].strip())

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

    caches = find_cache_paths(config)
    pacman_cache = find_pkgs_in_dir(caches[0])
    user_cache = find_pkgs_in_dir(caches[1:-1])
    pacback_cache = find_pkgs_in_dir(caches[-1:])

    inodes = {os.lstat(x)[stat.ST_INO] for x in {*pacman_cache, *user_cache}}
    pacback_filter = set()

    for x in pacback_cache:
        i = os.lstat(x)[stat.ST_INO]
        if i in inodes:
            pass
        else:
            pacback_filter.add(x)
            inodes.add(i)

    all_cache = {*pacman_cache, *user_cache, *pacback_cache}
    pkg_total = len(pacman_cache) + len(user_cache) + len(pacback_filter)

    # Calculate Size On Disk
    pacman_size = paf.convert_size(paf.size_of_files(pacman_cache))
    user_size = paf.convert_size(paf.size_of_files(user_cache))
    pacback_size = paf.convert_size(paf.size_of_files(pacback_filter))
    reported_size = paf.convert_size(paf.size_of_files(all_cache))
    paf.write_to_log(fname, 'Returning Cache Size', config['log'])

    return (str(pkg_total), pacman_size, user_size, pacback_size, reported_size)
