#! /usr/bin/env python3
import os
import datetime as dt

# Local Modules
import paf
import utils
import session
import custom_dirs


#########################
# Main Create Function
#######################

def main(config, info):
    '''
    This is pacbacks main method for orchestrating the creating of a
    fallback point. It shouldn't be called directly with create.main()
    but with a 'higher' level call the builds the info and stages the
    system for the actual creation process.
    '''
    fname = 'create.main(' + info['type'] + info['id'] + ')'
    paf.write_to_log(fname, 'Building ID:' + info['id'] + ' As ' + info['STYPE'] + ' ' + info['TYPE'], config['log'])

    # Light Restore Point
    if info['STYPE'] == 'Light':
        if info['dir_list']:
            session.abort_fail(fname, 'Custom Dirs Are Not Allowed With STYPE: ' + info['STYPE'],
                                   'Light ' + info['TYPE'] + ' DO NOT Support Custom Dirs! Please Use The `-f` Flag', config)
    # Full Restore Point
    elif info['STYPE'] == 'Full':
        pkg_search = paf.replace_spaces(utils.pacman_Q(), '-')
        found_pkgs = utils.search_cache(pkg_search, utils.scan_caches(config), config)
        pkg_size = paf.size_of_files(found_pkgs)

        # Ask About Missing Pkgs
        if len(found_pkgs) != len(pkg_search):
            paf.write_to_log(fname, 'Not All Packages Where Found!', config['log'])
            pkg_split = utils.trim_pkg_list(found_pkgs)
            print('')
            paf.prBold('=======================================')
            paf.prWarning('The Following Packages Where NOT Found!')
            paf.prBold('=======================================')
            for pkg in set(pkg_search - pkg_split):
                paf.prWarning(pkg)
            print('')

            if info['nc'] is False:
                if paf.yn_frame('Do You Still Want to Continue?') is False or None:
                    session.abort(fname, 'User Aborted Due to Missing Pkgs',
                                           'Aborting Creation!', config)

        # Make Folders and Hardlink Packages
        paf.mk_dir(info['path'], sudo=False)
        paf.mk_dir(info['pkgcache'], sudo=False)
        # This Is Much Faster Than A For Loop
        cmds = {'ln ' + paf.escape_bash_input(pkg) + ' ' + info['pkgcache']
                + '/' + paf.basename(pkg) for pkg in found_pkgs}
        os.system(' & '.join(cmds))
        paf.write_to_log(fname, 'HardLinked ' + str(len(found_pkgs)) + ' Packages', config['log'])

        # Search Custom Dir's
        if info['dir_list']:
            paf.write_to_log(fname, 'User Selected Version Dependent Folders For Storage', config['log'])
            pack_results = custom_dirs.store(config, info)

    # Generate Meta Data File
    current_pkgs = utils.pacman_Q()
    meta = [
        '======= Pacback Info =======',
        'Version: ' + config['version'],
        'Label: ' + info['label'],
        'Date Created: ' + dt.datetime.now().strftime("%Y/%m/%d"),
        'Time Created: ' + dt.datetime.now().strftime("%H:%M:%S"),
        'Type: ' + info['TYPE'],
        'SubType: ' + info['STYPE'],
        'Packages Installed: ' + str(len(current_pkgs))
        ]

    if info['STYPE'] == 'Full':
        meta.append('Packages Cached: ' + str(len(found_pkgs)))
        meta.append('Package Cache Size: ' + paf.convert_size(pkg_size))

    if info['dir_list']:
        meta.append('Dir File Count: ' + str(pack_results['file_count']))
        meta.append('Dir Raw Size: ' + pack_results['raw_size'])
        meta.append('Tar Compressed Size: ' + pack_results['compressed_size'])
        meta.append('Tar Checksum: ' + pack_results['csum'])

        meta.append('')
        meta.append('========= Dir List =========')
        for d in info['dir_list']:
            meta.append(d)

    meta.append('')
    meta.append('======= Pacman List ========')
    for pkg in current_pkgs:
        meta.append(pkg)

    # Export Final Meta Data File
    paf.export_iterable(info['meta'], meta)
    paf.write_to_log(fname, 'Generated Meta Data File', config['log'])
    # Checksum Meta Data File
    paf.export_iterable(info['meta_md5'], [paf.checksum_file(info['meta'])[1]])
    paf.write_to_log(fname, 'Generated Meta Data Checksum', config['log'])
    # Finish and Return
    paf.write_to_log(fname, 'Main Build Complete of ID:' + info['id'] + ' As ' + info['STYPE'] + ' ' + info['TYPE'], config['log'])


####################
# Create Snapshot
##################

def snapshot(config, label):
    '''
    Assembles all the info and stages the file system needed for the creation
    of a new snapshot with id:00. This is only called by `pacback --hook`.
    '''
    num = '00'
    fname = 'create.snapshot(' + num + ')'
    paf.write_to_log(fname, 'Started Snapshot Creation...', config['log'])
    session.hlock_check(config)

    info = {
        'id': num,
        'type': 'ss',
        'TYPE': 'Snapshot',
        'stype': 'l',
        'STYPE': 'Light',
        'nc': True,
        'label': str(label),
        'meta': config['ss_paths'] + '/ss' + num + '.meta',
        'meta_md5': config['ss_paths'] + '/.ss' + num + '.md5',
        'dir_list': [],
        'path': config['ss_paths'] + '/ss' + num,
        'pkgcache': config['ss_paths'] + '/ss' + num + '/pkg-cache',
        'tar': config['ss_paths'] + '/ss' + num + '/ss' + num + '_dirs.tar'
        }

    # Shift Snapshots Forward So This Becomes Zero
    if os.path.exists(config['ss_paths'] + '/ss00.meta'):
        paf.write_to_log(fname, 'Shifting All Snapshots Forward +1...', config['log'])

        # Remove the Last Snapshot
        paf.rm_file(config['ss_paths'] + '/ss' + str(config['max_ss']).zfill(2) + '.meta', sudo=False)
        paf.rm_file(config['ss_paths'] + '/ss' + str(config['max_ss']).zfill(2) + '.md5', sudo=False)

        # Moves Each Snapshot Forward +1 and Cleans on Exceptions
        for n in range((config['max_ss'] - 1), -1, -1):
            meta_path_old = config['ss_paths'] + '/ss' + str(n).zfill(2) + '.meta'
            meta_path_new = config['ss_paths'] + '/ss' + str(n + 1).zfill(2) + '.meta'
            hash_path_old = config['ss_paths'] + '/.ss' + str(n).zfill(2) + '.md5'
            hash_path_new = config['ss_paths'] + '/.ss' + str(n + 1).zfill(2) + '.md5'
            meta_found = os.path.exists(meta_path_old)
            csum_found = os.path.exists(hash_path_old)

            if meta_found and csum_found:
                os.rename(meta_path_old, meta_path_new)
                os.rename(hash_path_old, hash_path_new)

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

        paf.write_to_log(fname, 'Finished Shifting Snapshots Forward', config['log'])

    else:
        paf.write_to_log(fname, 'Snapshot ID:00 Was Not Found, Shift Forward is Unnecessary.', config['log'])

    # Creates Snapshot After Pre-Transaction Work and Checks
    paf.write_to_log(fname, 'All Checks Passed! Ready For Snapshot Creation', config['log'])
    paf.prBold('Creating Snapshot...')
    main(config, info)

    # Prevents Back-to-Back Snapshots(Especially During AUR Upgrades)
    session.hlock_start(config)
    paf.write_to_log(fname, 'Snapshot Creation Complete!', config['log'])
    paf.prBold('Snapshot Creation Complete!')


#########################
# Create Restore Point
#######################

def restore_point(config, num, full_rp, dir_list, no_confirm, label):
    '''
    Assembles all the info and stages the file system needed for the creation
    of a restore point. It is assumed that user info is cleansed.
    '''
    num = str(num).zfill(2)
    fname = 'create.restore_point(' + num + ')'
    paf.write_to_log(fname, 'Started Restore Point Creation...', config['log'])

    info = {
        'id': num,
        'type': 'rp',
        'TYPE': 'Restore Point',
        'stype': 'f' if full_rp is True else 'l',
        'STYPE': 'Full' if full_rp is True else 'Light',
        'nc': no_confirm,
        'label': str(label),
        'meta': config['rp_paths'] + '/rp' + num + '.meta',
        'meta_md5': config['rp_paths'] + '/.rp' + num + '.md5',
        'dir_list': dir_list,
        'path': config['rp_paths'] + '/rp' + num,
        'pkgcache': config['rp_paths'] + '/rp' + num + '/pkg-cache',
        'tar': config['rp_paths'] + '/rp' + num + '/rp' + num + '_dirs.tar'
        }

    # Check for Pre-Existing Restore Point
    if os.path.exists(info['meta']) or os.path.exists(info['path']):
        paf.prWarning('Restore Point #' + info['id'] + ' Already Exists!')

        if info['nc'] is False:
            if paf.yn_frame('Do You Want to Overwrite It?') is False or None:
                session.abort(fname, 'User Aborted Overwrite of RP #' + info['id'], 'Aborting Creation!', config)
        utils.remove_id(config, info)

    # Create Restore Point After Checks
    paf.write_to_log(fname, 'All Checks Passed! Handing Off to create.main()', config['log'])
    paf.prBold('Building ' + info['STYPE'] + ' ' + info['TYPE'] + ' ' + info['id'] + '...')
    main(config, info)

    # Finish After Successful Creation
    paf.write_to_log(fname, 'Restore Point Creation Complete!', config['log'])
    paf.prBold('Restore Point Creation Complete!')
