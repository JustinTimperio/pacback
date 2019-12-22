#! /usr/bin/env python3
import os
import re
import tqdm
import multiprocessing as mp
import python_scripts as PS


def diff_rp_files(rp_tar, meta_dirs, current_pkgs):
    '''Di'''
    custom_dirs = rp_tar[:-4]
    if os.path.exists(rp_tar + '.gz'):
        PS.prWorking('Decompressing Restore Point....')
        if any(re.findall('pigz', line.lower()) for line in current_pkgs):
            os.system('pigz -d ' + rp_tar + '.gz -f')  # Decompress With pigz
        else:
            PS.GZ_D(rp_tar + '.gz')  # Decompress with Python

    if os.path.exists(custom_dirs):
        PS.RM_Dir(custom_dirs, sudo=True)

    PS.prWorking('Unpacking Files from Restore Point Tar....')
    PS.Untar_Dir(rp_tar)

    diff_yn = PS.YN_Frame('Do You Want to Checksum Diff Restore Point Files Against Your Current File System?')
    if diff_yn is False:
        print('Skipping Diff!')
        pass

    elif diff_yn is True:
        rp_fs = PS.Search_FS(custom_dirs)
        rp_fs_trim = set(path[len(custom_dirs):] for path in PS.Search_FS(custom_dirs))

        # Checksum Restore Point Files with a MultiProcessing Pool
        with mp.Pool(os.cpu_count()) as pool:
            rp_checksum = set(tqdm.tqdm(pool.imap(PS.Checksum_File, rp_fs),
                                        total=len(rp_fs), desc='Checksumming Restore Point Files'))
            sf_checksum = set(tqdm.tqdm(pool.imap(PS.Checksum_File, rp_fs_trim),
                                        total=len(rp_fs_trim), desc='Checksumming Source Files'))

        # Compare Checksums For Files That Exist
        rp_csum_trim = set(path[len(custom_dirs):] for path in rp_checksum)
        rp_diff = sf_checksum.difference(rp_csum_trim)

        # Filter Removed and Changed Files
        diff_removed = set()
        diff_changed = set()
        for csum in rp_diff:
            if re.findall('FILE MISSING', csum):
                diff_removed.add(csum)
            else:
                diff_changed.add(csum.split(' : ')[0] + ' : FILE CHANGED!')

        # Find Added Files
        src_fs = set()
        for x in meta_dirs:
            for l in PS.Search_FS(x):
                src_fs.add(l)
        diff_new = src_fs.difference(rp_fs_trim)

        # Print Changed Files For User
        if len(diff_changed) + len(diff_new) + len(diff_removed) == 0:
            PS.RM_Dir(custom_dirs, sudo=True)
            return PS.prSuccess('No Files Have Been Changed!')

    #######################
    ### Overwrite Files ###
    #######################
    if diff_yn is False:
        PS.prWarning('YOU HAVE NOT CHECKSUMED THE RESTORE POINT! OVERWRITING ALL FILES CAN BE EXTREAMLY DANGOURS!')
        ow = PS.YN_Frame('Do You Still Want to Continue and Restore ALL Files In the Restore Point?')
        if ow is False:
            return print('Skipping Automatic File Restore! Restore Point Files Are Unpacked in ' + custom_dirs)

        elif ow is True:
            print('Starting Full File Restore! Please Be Patient As All Files are Overwritten...')
            rp_fs = PS.Search_FS(custom_dirs)
            for f in rp_fs:
                PS.prWorking('Please Be Patient. This May Take a While...')
                os.system('sudo mkdir -p ' + PS.Escape_Bash('/'.join(f.split('/')[:-1])) + ' && sudo cp -af ' + PS.Escape_Bash(f) + ' ' + PS.Escape_Bash(f[len(custom_dirs):]))

    elif diff_yn is True:
        ow = PS.YN_Frame('Do You Want to Automaticly Restore Changed and Missing Files?')
        if ow is False:
            return print('Skipping Automatic Restore! Restore Point Files Are Unpacked in ' + custom_dirs)

        if ow is True:
            if len(diff_changed) > 0:
                PS.prWarning('The Following Files Have Changed:')
                for f in diff_changed:
                    PS.prChanged(f)
                if PS.YN_Frame('Do You Want to Overwrite Files That Have Been CHANGED?') is True:
                    PS.prWorking('Please Be Patient. This May Take a While...')
                    for f in diff_changed:
                        fs = (f.split(' : ')[0])
                        os.system('sudo cp -af ' + PS.Escape_Bash(custom_dirs + fs) + ' ' + PS.Escape_Bash(fs))

        if len(diff_removed) > 0:
            PS.prWarning('The Following Files Have Removed:')
            for f in diff_removed:
                PS.prRemoved(f)
            if PS.YN_Frame('Do You Want to Add Files That Have Been REMOVED?') is True:
                PS.prWorking('Please Be Patient. This May Take a While...')
                for f in diff_removed:
                    fs = (f.split(' : ')[0])
                    os.system('sudo mkdir -p ' + PS.Escape_Bash('/'.join(fs.split('/')[:-1])) + ' && sudo cp -af ' + PS.Escape_Bash(custom_dirs + fs) + ' ' + PS.Escape_Bash(fs))

        if len(diff_new) > 0:
            for f in diff_new:
                PS.prAdded(f + ' : NEW FILE!')
            if PS.YN_Frame('Do You Want to Remove Files That Have Beend ADDED?') is True:
                PS.prWorking('Please Be Patient. This May Take a While...')
                for f in diff_new:
                    fs = (f.split(' : ')[0])
                    os.system('sudo rm ' + fs)

    PS.RM_Dir(custom_dirs, sudo=True)
    PS.prSuccess('File Restore Complete!')
