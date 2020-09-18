#! /usr/bin/env python3
# I want to say this is my least favorite part of the whole codebase
# I almost regret adding this feature but its here now
# The code is not documented to the same standard because I hate
# working on this part of the codebase.

import re
import os
import shutil
import pickle
import tarfile
from rich.progress import track

# Local Modules
import paf
import utils


#################################################
# Make Missing Directories With Original Perms
###############################################

def make_missing_dirs(config, unpack_path, p_len):
    '''
    This is an add on function that restores permissions to folders.
    This was a known bug for all of alpha but is finally patched.
    Folder permissions aren't stored in a tar so a separate system
    was created to handle this using pickle and paf functions.
    '''
    fname = 'custom_dirs.make_missing_dirs()'
    # Find All Subdirs
    dirs = paf.find_subdirs(unpack_path)
    # Sort in Subdirs in Descending Paths
    dirs.sort(key=lambda x: x.count('/'))

    for d in dirs:
        if not os.path.exists(d[p_len:]):
            os.makedirs(d[p_len:])

    if os.path.exists(unpack_path + '/folder_permissions.pickle'):
        # Load Folder Permissions Pickle
        folder_perms = pickle.load(open(unpack_path + '/folder_permissions.pickle', 'rb'))

        for x in folder_perms:
            os.system('chmod ' + paf.perm_to_num(x[1]) + ' ' + paf.escape_bash_input(x[0]))
            os.system('chown ' + x[2] + ':' + x[3] + ' ' + paf.escape_bash_input(x[0]))

    else:
        paf.write_to_log(fname, 'Folder Permissions Pickle is Missing!', config['log'])


################################
# Clean Up and Repack On Exit
##############################

def repack(config, info, unpack_path):
    '''
    Cleans up after comparing an already created custom tar.
    '''
    fname = 'custom_dirs.repack()'
    paf.rm_dir(unpack_path, sudo=False)
    paf.write_to_log(fname, 'Cleaned Up Unpacked Files', config['log'])

    if os.path.exists(info['tar']):
        # Re-Compress Custom Tar
        print('Re-Compressing Tar...')
        if any(re.findall('pigz', l.lower()) for l in utils.pacman_Q()):
            os.system('/usr/bin/pigz ' + info['tar'] + ' -f')
        else:
            paf.gz_c(info['tar'], rm=True)
        paf.write_to_log(fname, 'Compressed ' + info['tar'], config['log'])


################################
# Compare Files With Checksum
##############################

def compare_files(config, dir_list, unpack_path, p_len):
    '''
    Compares and unpacked custom user files against the current system.
    Returns a dict of added, removed and changed files on the system.
    '''
    fname = 'custom_dirs.compare_files()'
    # Core Compare Results
    diff_added = set()
    diff_removed = set()
    diff_large = set()
    diff_noread = set()
    diff_changed = set()

    # Compare Checksums For Files That Exist
    paf.write_to_log(fname, 'Started Sorting and Comparing Files...', config['log'])

    # Search Directories
    unpack_files = paf.find_files(unpack_path)
    current_files = paf.find_files(dir_list)

    # Find Added Files and Remove From Csum Queue
    diff_added.update(current_files - {f[p_len:] for f in unpack_files})
    current_files.difference_update(diff_added)

    # Find Removed Files and Trim From Csum Queue
    diff_removed.update(unpack_files - {unpack_path + f for f in current_files})
    unpack_files.difference_update(diff_removed)
    try:
        diff_removed.remove(unpack_path + '/folder_permissions.pickle')
    except KeyError:
        paf.write_to_log(fname, 'Error: Couldn\'t Find Permission Pickle.', config['log'])

    # Only Checksum Files That Exist in Both Current AND Unpack
    paf.write_to_log(fname, 'Started Checksumming Custom Files...', config['log'])
    unpack_csum = paf.checksum_files(unpack_files, output='Checksumming Stored Files')
    current_csum = paf.checksum_files(current_files, output='Checksumming Current Files')
    paf.write_to_log(fname, 'Finished Checksumming Custom Files', config['log'])

    # Find Exceptions and Trim
    for csum in unpack_csum:
        if csum[1] == 'TOO LARGE!':
            diff_large.add(csum)
            unpack_csum.remove(csum)
            paf.write_to_log(fname, csum[0] + ' Was Too Large To Checksum!', config['log'])
        elif csum[1] == 'UNREADABLE!':
            diff_noread.add(csum)
            unpack_csum.remove(csum)
            paf.write_to_log(fname, csum[0] + ' Was Unreadable!', config['log'])

    for csum in current_csum:
        if csum[1] == 'TOO LARGE!':
            diff_large.add(csum)
            current_csum.remove(csum)
            paf.write_to_log(fname, csum[0] + ' Was Too Large To Checksum!', config['log'])
        elif csum[1] == 'UNREADABLE!':
            diff_noread.add(csum)
            current_csum.remove(csum)
            paf.write_to_log(fname, csum[0] + ' Was Unreadable!', config['log'])

    # Find Changed Files
    diff_changed.update(current_csum - {(tpl[0][p_len:], tpl[1]) for tpl in unpack_csum})
    paf.write_to_log(fname, 'Finished Comparing and Sorting Files', config['log'])

    compare_results = {
            'added': diff_added,
            'removed': diff_removed,
            'changed': diff_changed,
            'large': diff_large,
            'noread': diff_noread
            }

    return compare_results


##################################
# Full Overwrite W/out Checksum
################################

def force_overwrite(config, unpack_path, p_len):
    '''
    Restore Files Without Checksum
    '''
    fname = 'custom_dirs.force_overwrite()'

    # Allow Exit Since This Is Bad Idea
    paf.prWarning('OVERWRITING FILES WITHOUT CHECKSUMS CAN BE EXTREMELY DANGEROUS!')
    if paf.yn_frame('Do You Still Want to Continue and Restore ALL The Files You Stored?') is False:
        return

    # Overwrite Files
    paf.write_to_log(fname, 'Starting Force Overwrite Process...', config['log'])
    print('Starting Full File Restore! Please Be Patient As All Files are Overwritten...')
    fs_stored = paf.find_files(unpack_path)
    try:
        fs_stored.remove(unpack_path + '/folder_permissions.pickle')
    except Exception:
        pass
    make_missing_dirs(config, unpack_path, p_len)
    for f in track(fs_stored, description='Overwriting Files'):
        shutil.os(f, f[p_len:])

    paf.prSuccess('Done Overwriting Files!')
    paf.write_to_log(fname, 'Finished Force Overwrite Of Files', config['log'])


#####################################
# Overwrite Using Checksum Results
###################################

def smart_overwrite(config, csum_results, unpack_path, p_len):
    '''
    Main File Restoration Logic
    '''
    fname = 'custom_dirs.smart_overwrite()'

    if csum_results['changed']:
        paf.write_to_log(fname, 'Found ' + str(len(csum_results['changed'])) + ' Changed Files', config['log'])
        print('')
        print('#################################')
        paf.prWarning('The Following Files Have Changed:')
        print('#################################')
        print('')
        for f in list(csum_results['changed']):
            paf.prChanged(f[0])
        print('')

        if paf.yn_frame('Do You Want to Restore ' + str(len(csum_results['changed'])) + ' Files That Have Been CHANGED?') is True:
            for f in track(csum_results['changed'], description='Restoring Changed Files'):
                shutil.move(unpack_path + f[0], f[0])
            paf.write_to_log(fname, 'Restored Changed Files', config['log'])
        else:
            paf.write_to_log(fname, 'User Declined Restoring Changed Files', config['log'])

    if csum_results['removed']:
        paf.write_to_log(fname, 'Found ' + str(len(csum_results['removed'])) + ' Removed Files', config['log'])
        print('')
        print('######################################')
        paf.prWarning('The Following Files Have Been Removed:')
        print('######################################')
        print('')
        for f in list(csum_results['removed']):
            paf.prRemoved(f[p_len:])
        print('')

        if paf.yn_frame('Do You Want to Restore ' + str(len(csum_results['removed'])) + ' Files That Have Been REMOVED?') is True:
            make_missing_dirs(config, unpack_path, p_len)
            for f in track(csum_results['removed'], description='Restoring Removed Files'):
                os.shutil(f, f[p_len:])
            paf.write_to_log(fname, 'Restored Removed Files', config['log'])
        else:
            paf.write_to_log(fname, 'User Declined Restoring Removed Files', config['log'])

    if csum_results['added']:
        paf.write_to_log(fname, 'Found ' + str(len(csum_results['added'])) + ' New Files', config['log'])
        print('')
        print('####################################')
        paf.prWarning('The Following Files Have Been Added:')
        print('####################################')
        print('')
        for f in list(csum_results['added']):
            paf.prAdded(f)
        print('')

        if paf.yn_frame('Do You Want to Remove ' + str(len(csum_results['added'])) + ' Files That Have Been ADDED?') is True:
            for f in track(csum_results['added'], description='Removing New Files'):
                os.remove(f)
            paf.write_to_log(fname, 'Removed New Files', config['log'])
        else:
            paf.write_to_log(fname, 'User Declined Removing New Files', config['log'])

    paf.prSuccess('Done Restoring Files!')
    paf.write_to_log(fname, 'Done Restoring Files', config['log'])


###############################
# Restore Custom Directories
#############################

def restore(config, info, dir_list, checksum):
    '''
    This is the main 'api' entrance point for file restoration.
    This function orchestrates the process handing of work to other funcs.
    '''
    fname = 'custom_dirs.restore()'
    unpack_path = info['tar'][:-4]
    p_len = len(unpack_path)
    paf.write_to_log(fname, 'PLACE HOLDER', config['log'])

    # Decompress Tar
    if os.path.exists(info['tar.gz']):
        paf.prWarning('Decompressing Custom Tar....')
        if any(re.findall('pigz', line.lower()) for line in utils.pacman_Q()):
            os.system('/usr/bin/pigz -d ' + info['tar.gz'] + ' -f')
            paf.write_to_log(fname, 'Decompressed Tar With Pigz', config['log'])
        else:
            paf.gz_d(info['tar.gz'])
            paf.write_to_log(fname, 'Decompressed Tar With Python', config['log'])

    # Check Tar Csum And Unpack
    if os.path.exists(info['tar']):
        # Checksum Tar
        print('Checking Integrity of Tar...')
        tar_csum = paf.checksum_file(info['tar'])[1]
        paf.write_to_log(fname, 'Checksummed Tar', config['log'])

        if tar_csum == checksum:
            paf.write_to_log(fname, 'Tar Passed Checksum Integrity Check', config['log'])
            paf.prSuccess('Tar Passed Integrity Check')
        else:
            paf.write_to_log(fname, 'Custom Tar Failed Integrity Check!', config['log'])
            paf.prError('Custom Tar Failed Integrity Check!')
            paf.prBold('Skipping Custom File Restoration!')
            return

        # Clean Then Unpack Tar
        paf.prWarning('Unpacking Files from Tar....')
        paf.rm_dir(unpack_path, sudo=True)
        paf.untar_dir(info['tar'])
        paf.write_to_log(fname, 'Unpacked Custom Files From Tar', config['log'])

    else:
        # Skip If Tar is Missing
        paf.write_to_log(fname, 'Meta Data File Spesifies A Tar That is Now Missing!', config['log'])
        paf.prError('This Restore Point is Missing It\'s Custom Tar!')
        return

    if paf.yn_frame('Do You Want to Compare Restore Point Files Against Your Current File System?') is True:
        results = compare_files(config, dir_list, unpack_path, p_len)
        # Exit If No Changes Made to Files
        if len(results['added']) + len(results['removed']) + len(results['changed']) == 0:
            paf.write_to_log(fname, 'Checksum Returned 0 Changed, Removed or Added Files', config['log'])
            paf.prSuccess('No Changes Have Been Made to Your File System!')
        else:
            smart_overwrite(config, results, unpack_path, p_len)

    else:
        force_overwrite(config, unpack_path, p_len)

    # Cleanup After Runtime
    repack(config, info, unpack_path)


#############################
# Store Custom Directories
###########################

def store(config, info):
    '''
    Packs up user defined directories.
    '''
    fname = 'custom_dirs.pack()'
    paf.write_to_log(fname, str(len(info['dir_list'])) + ' Folders Selected For Storage', config['log'])

    # Fetch Folder Permissions and Pickle
    folder_perms = set()
    for d in info['dir_list']:
        folder_perms.update(paf.get_permissions(d, 'folders'))
    pickle.dump(folder_perms, (open('/tmp/folder_permissions.pickle', 'wb')))
    # Scan For Files
    files = paf.find_files(info['dir_list'])

    # Pack Custom Files Into Tar
    with tarfile.open(info['tar'], 'w') as tar:
        tar.add('/tmp/folder_permissions.pickle', arcname='folder_permissions.pickle')
        for f in track(files, description='Adding Files to Tar'):
            tar.add(f)
    paf.rm_file('/tmp/folder_permissions.pickle', sudo=False)

    paf.write_to_log(fname, 'Created ' + info['tar'], config['log'])

    # Create Checksum for Tar
    print('Creating Checksum...')
    pack_csum = paf.checksum_file(info['tar'])[1]
    paf.write_to_log(fname, 'Checksummed Tar ', config['log'])

    # Compresses Custom Tar
    print('Compressing Custom Tar...')
    if any(re.findall('pigz', l.lower()) for l in utils.pacman_Q()):
        os.system('pigz ' + info['tar'] + ' -f')
    else:
        paf.gz_c(info['tar'], rm=True)
    paf.write_to_log(fname, 'Compressed ' + info['tar'], config['log'])

    pack_results = {
            'file_count': len(files),
            'raw_size': paf.convert_size(paf.size_of_files(files)),
            'compressed_size': paf.convert_size(os.path.getsize(info['tar'] + '.gz')),
            'csum': pack_csum
            }

    return pack_results
