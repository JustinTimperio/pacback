#! /usr/bin/env python3
import re
import os

# Local Modules
import paf
import meta
import utils
import session
import version
import custom_dirs


#############################
# Main Package Restoration
###########################

def main(config, parms, pkg_results):
    '''
    This is the main restore logic for pacback. It should NOT be called directly as restore.main().
    This logic does the actual work of downgrading, removing, and installing packages.
    '''
    fname = 'restore.main(' + parms['type'] + parms['id'] + ')'

    # Branch if Packages Have Been Changed or Removed
    if pkg_results['search']:
        cache = utils.scan_caches(config)
        found_pkgs = utils.search_cache(pkg_results['search'], cache, config)

        # Branch if Packages are Missing
        if len(found_pkgs) != len(pkg_results['search']):
            missing_pkg = {pkg_results['search'] - utils.trim_pkg_list(found_pkgs)}
            paf.write_to_log(fname, str(len(found_pkgs)) + ' Out of ' + str(len(pkg_results['search'])) + ' Packages Found', config['log'])

            paf.prWarning('Couldn\'t Find The Following Package Versions:')
            for pkg in missing_pkg:
                paf.prError(pkg)
            if paf.yn_frame('Do You Want To Continue Anyway?') is False:
                session.abort_fail(fname, 'User Aborted Rollback Because of Missing Packages', 'Aborting Rollback!', config)

        else:
            paf.prSuccess('All Packages Found In Your Local File System!')
            paf.write_to_log(fname, 'Found All Changed and Removed Packages', config['log'])

        paf.pacman(' '.join(found_pkgs), '-U')
        paf.write_to_log(fname, 'Sent Pacman Selected Packages', config['log'])

    else:
        paf.prSuccess('No Packages Have Been Changed or Removed!')
        paf.write_to_log(fname, 'No Packages Have Been Changed or Removed', config['log'])

    # Branch if Packages Have Been Added
    if pkg_results['a_pkgs']:
        print('')
        paf.write_to_log(fname, str(len(pkg_results['a_pkgs'])) + ' Have Been Added Since Creation', config['log'])

        paf.prWarning(str(len(pkg_results['a_pkgs'])) + ' Packages Have Been Added Since Creation')
        for pkg in pkg_results['a_pkgs']:
            paf.prAdded(pkg)
        print('')
        if paf.yn_frame('Do You Want to Remove These Packages From Your System?') is True:
            print('')
            paf.pacman(' '.join(pkg_results['a_pkgs']), '-R')
            paf.write_to_log(fname, 'Sent Added Packages To `pacman -R`', config['log'])

    else:
        paf.prSuccess('No Packages Have Been Added!')
        paf.write_to_log(fname, 'No Packages Have Been Added', config['log'])


#####################
# Restore Snapshot
###################

def snapshot(config, id_num):
    '''
    This handles the process of restoring snapshots. This is pretty much the same as a 
    standard restore point but requires post-processing after the restoration to maintain
    the order of changes made to the system.
    '''
    id_num = str(id_num).zfill(2)
    fname = 'restore.snapshot(' + id_num + ')'
    paf.write_to_log(fname, 'Started Restoring Snapshot ID:' + id_num, config['log'])

    info = {
            'id': id_num,
            'type': 'ss',
            'TYPE': 'Snapshot',
            'meta': config['ss_paths'] + '/ss' + id_num + '.meta',
            'meta_md5': config['ss_paths'] + '/.ss' + id_num + '.md5',
            'path': config['ss_paths'] + '/ss' + id_num,
            'pkgcache': config['ss_paths'] + '/ss' + id_num + '/pkg-cache'
            }

    # Read Meta Data File, Check Version, Compare Results, Restore
    meta.validate(config, info)
    ss_dict = meta.read(config, info['meta'])
    version.compare(config, ss_dict['version'])
    main(config, info, meta.compare_now(config, ss_dict))

    # Resets Order So The Restored Version is Zero
    paf.write_to_log(fname, 'Started Rewinding Snapshots Back to Zero', config['log'])

    # Removes Snapshots From Zero to Restored Snapshot ID
    for n in range(0, int(info['id'])):
        rm_info = {
                'id': str(n).zfill(2),
                'type': 'ss',
                'TYPE': 'Snapshot',
                'meta': config['ss_paths'] + '/ss' + str(n).zfill(2) + '.meta',
                'meta_md5': config['ss_paths'] + '/.ss' + str(n).zfill(2) + '.md5'
                }
        utils.remove_id(config, rm_info)

    # Shifts Snapshots Back, So Now Retored Snapshot Is New Zero
    id_counter = 0
    for n in range(int(info['id']), (config['max_ss'] + 1)):
        meta_path_old = config['ss_paths'] + '/ss' + str(n).zfill(2) + '.meta'
        meta_path_new = config['ss_paths'] + '/ss' + str(id_counter) + '.meta'
        hash_path_old = config['ss_paths'] + '/.ss' + str(n).zfill(2) + '.md5'
        hash_path_new = config['ss_paths'] + '/.ss' + str(id_counter) + '.md5'
        meta_found = os.path.exists(meta_path_old)
        csum_found = os.path.exists(hash_path_old)

        if meta_found and csum_found:
            os.rename(meta_path_old, meta_path_new)
            os.rename(hash_path_old, hash_path_new)
            id_counter += 1
        elif meta_found and not csum_found:
            paf.write_to_log(fname, 'Snapshot ' + str(n).zfill(2) + ' is Missing it\'s Checksum File!', config['log'])
            paf.rm_file(meta_path_old, sudo=False)
            paf.write_to_log(fname, 'Removed Snapshot ID:' + str(n).zfill(2), config['log'])
        elif not meta_found and csum_found:
            paf.write_to_log(fname, hash_path_old + ' is an Orphaned Checksum', config['log'])
            paf.rm_file(hash_path_old, sudo=False)
            paf.write_to_log(fname, 'Removed Orphaned Checksum', config['log'])
        else:
            pass

    paf.write_to_log(fname, 'Finished Rewinding Snapshots Back to Zero', config['log'])

    # Finish Last Checks and Exit
    utils.reboot_check(config)
    paf.write_to_log(fname, 'Finished Restoring Snapshot ID:' + id_num, config['log'])


############################
# Restore A Restore Point
##########################

def restore_point(config, id_num):
    '''
    This preps the system for a restoration then hands off to restore.main() 
    '''
    id_num = str(id_num).zfill(2)
    fname = 'restore.restore_point(' + id_num + ')'
    paf.write_to_log(fname, 'Started Restoring Restore Point ID:' + id_num, config['log'])

    info = {
            'id': id_num,
            'type': 'ss',
            'TYPE': 'Snapshot',
            'meta': config['rp_paths'] + '/rp' + id_num + '.meta',
            'meta_md5': config['rp_paths'] + '/.rp' + id_num + '.md5',
            'path': config['rp_paths'] + '/rp' + id_num,
            'pkgcache': config['rp_paths'] + '/rp' + id_num + '/pkg-cache',
            'tar': config['rp_paths'] + '/rp' + id_num + '/rp' + id_num + '_dirs.tar',
            'tar.gz': config['rp_paths'] + '/rp' + id_num + '/rp' + id_num + '_dirs.tar.gz'
            }

    # Read Meta File, Check Version, Compare Results
    meta.validate(config, info)
    rp_dict = meta.read(config, info['meta'])
    version.compare(config, rp_dict['version'])
    main(config, info, meta.compare_now(config, rp_dict))

    # Unpack and Compare Directories Stored By User
    if rp_dict['dir_list']:
        custom_dirs.restore(config, info, rp_dict['dir_list'], rp_dict['tar_csum'])

    # Finish Last Checks and Exit
    utils.reboot_check(config)
    paf.write_to_log(fname, 'Finished Restoreing Restore Point ID:' + id_num, config['log'])


################################
# Manual User Package Restore
##############################

def packages(config, pkgs):
    '''
    Allows the user to rollback packages by name.
    Packages are not sent to pacman until the user has select all
    the packages they want to restore/change.
    '''
    # Startup
    fname = 'restore.packages(' + str(len(pkgs)) + ')'
    pkg_paths = list()
    cache = utils.scan_caches(config)

    # Search For Each Package Name And Let User Select Version
    paf.write_to_log(fname, 'Started Search for ' + ', '.join(pkgs), config['log'])
    for pkg in pkgs:
        found_pkgs = utils.user_pkg_search(pkg, cache)
        sort_pkgs = sorted(found_pkgs, reverse=True)

        if found_pkgs:
            paf.write_to_log(fname, 'Found ' + str(len(found_pkgs)) + ' Cached Versions for `' + pkg + '`', config['log'])
            paf.prSuccess('Pacback Found the Following Versions for `' + pkg + '`:')
            answer = paf.multi_choice_frame(sort_pkgs)

            # Lets User Abort Package Selection
            if answer is False or None:
                paf.write_to_log(fname, 'User Selected NOTHING For ' + pkg, config['log'])
            else:
                for x in cache:
                    if re.findall(re.escape(answer), x):
                        pkg_paths.append(x)
                        break

        else:
            paf.prError('No Packages Found Under the Name: ' + pkg)
            paf.write_to_log(fname, 'Search for ' + pkg.upper() + ' Returned ZERO Results!', config['log'])

    if pkg_paths:
        paf.pacman(' '.join(pkg_paths), '-U')
        paf.write_to_log(fname, 'Sent Pacman Selected Packages For Installation', config['log'])
    else:
        paf.write_to_log(fname, 'User Selected No Packages or No Packages Were Found', config['log'])


#############################
# Restore Packages to Date
###########################

def archive_date(config, date):
    '''
    This function simply automates the date rollback instructions found on the Arch Wiki.
    https://wiki.archlinux.org/index.php/Arch_Linux_Archive#How_to_restore_all_packages_to_a_specific_date
    '''
    # Startup
    fname = 'restore.archive_date(' + str(date) + ')'
    mirror = '/etc/pacman.d/mirrorlist'

    # Done as a Fail Safe
    if len(paf.read_file(mirror)) > 2:
        os.system('mv ' + mirror + ' ' + mirror + '.pacback')
        paf.write_to_log(fname, 'Backed Up Existing Mirrorlist', config['log'])
    else:
        paf.write_to_log(fname, 'Skipped Mirrorlist Backup. File Seems Miss-Formated!', config['log'])

    paf.export_iterable(mirror, ['## Set By Pacback', 'Server=https://archive.archlinux.org/repos/' + date + '/$repo/os/$arch'])
    paf.write_to_log(fname, 'Added ' + date + ' Archive URL To Mirrorlist', config['log'])

    # Run Pacman Update to Run Downgrade
    os.system('pacman -Syyuu')
    paf.write_to_log(fname, 'Sent -Syyuu to Pacman', config['log'])

    # Restore the Non-Archive URL Mirrorlist
    if os.path.exists(mirror + '.pacback') is False:
        paf.write_to_log(fname, 'Backup Mirrorlist Is Missing', config['log'])
        if paf.yn_frame('Missing Mirrorlist! Do You Want to Fetch a New HTTPS Mirrorlist?') is True:
            if utils.fetch_new_mirrorlist() is True:
                paf.write_to_log(fname, 'A New Mirrorlist Was Successfully Downloaded', config['log'])
            else:
                session.abort_fail(fname, 'User Declined Country Selection!',
                        'Please Manually Replace Your Mirrorlist!', config['log'])
        else:
            session.abort_fail(fname, 'Backup Mirrorlist Is Missing and User Declined Download!',
                    'Please Manually Replace Your Mirrorlist!', config['log'])
    else:
        os.system('mv ' + mirror + '.pacback ' + mirror)
        paf.write_to_log(fname, 'Backup Mirrorlist Was Restored Successfully', config['log'])
        os.system('pacman -Syy > /dev/null')
        paf.write_to_log(fname, 'Updated Pacman Database After Restoring Mirrorlist', config['log'])
