#! /usr/bin/env python3
import re
import os
import tqdm
import multiprocessing as mp
import python_scripts as PS
import pac_utils as pu
import version_control as vc

log_file = '/var/log/pacback.log'
rp_paths = '/var/lib/pacback/restore-points'

#<#><#><#><#><#><#>#<#>#<#
#<># Rollback to Date
#<#><#><#><#><#><#>#<#>#<#


def rollback_to_date(date):
    PS.Start_Log('RollbackToDate', log_file)
    # Validate Date Fromat and Build New URL
    if not re.findall(r'([12]\d{3}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01]))', date):
        PS.Abort_With_Log('RollbackToDate', 'Aborting Due to Invalid Date Format',
                          'Invalid Date! Date Must be YYYY/MM/DD Format', log_file)

    # Backup Mirrorlist
    if len(PS.Read_List('/etc/pacman.d/mirrorlist')) > 1:
        os.system('sudo cp /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist.pacback')
        PS.Write_To_Log('RollbackToDate', 'Backed Up Old Mirrorlist', log_file)
    os.system("echo 'Server=https://archive.archlinux.org/repos/" + date + 
              "/$repo/os/$arch' | sudo tee /etc/pacman.d/mirrorlist >/dev/null")
    PS.Write_To_Log('RollbackToDate', 'Added Archive URL To Mirrorlist', log_file)

    # Run Pacman Update
    os.system('sudo pacman -Syyuu')
    PS.Write_To_Log('RollbackToDate', 'Ran pacman -Syyuu', log_file)
    PS.End_Log('RollbackToDate', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Rollback to RP
#<#><#><#><#><#><#>#<#>#<#


def rollback_to_rp(version, rp_num):
    PS.Start_Log('RollbackRP', log_file)
    #####################
    # Stage Rollback Vars
    #####################
    rp_num = str(rp_num).zfill(2)
    rp_path = '/var/lib/pacback/restore-points/rp' + rp_num
    rp_tar = rp_path + '/' + rp_num + '_dirs.tar'
    rp_meta = rp_path + '.meta'
    current_pkgs = pu.pacman_Q()

    # Set Full RP Status
    if os.path.exists(rp_path):
        full_rp = True
        PS.Write_To_Log('RollbackRP', 'RP #' + rp_num + ' Is Full RP', log_file)
    else:
        full_rp = False
        PS.Write_To_Log('RollbackRP', 'RP #' + rp_num + ' Is Light RP', log_file)

    # Set Meta Status, Read Meta, Diff Packages, Set Vars
    if os.path.exists(rp_meta):
        meta_exists = True
        PS.Write_To_Log('RollbackRP', 'RP #' + rp_num + ' Has MetaData', log_file)
        meta = PS.Read_List(rp_meta)
        meta_dirs = PS.Read_Between('= Dir List =', '= Pacman List =', meta, re_flag=True)[:-1]
        meta_old_pkgs = PS.Read_Between('= Pacman List =', '<Endless>', meta, re_flag=True)

        # Checking for New and Changed Packages
        changed_pkgs = set(set(meta_old_pkgs) - current_pkgs)
        meta_old_pkg_strp = {pkg.split(' ')[0] for pkg in meta_old_pkgs}
        current_pkg_strp = {pkg.split(' ')[0] for pkg in current_pkgs}
        added_pkgs = set(current_pkg_strp - meta_old_pkg_strp)
        m_search = PS.Replace_Spaces(changed_pkgs)
        PS.Write_To_Log('RollbackRP', 'Finished Reading RP MetaData', log_file)

    else:
        meta_exists = False
        meta = None
        PS.Write_To_Log('RollbackRP', 'RP #' + rp_num + ' Is Missing MetaData', log_file)

    # Abort If No Files Are Found
    if meta_exists is False and full_rp is False:
        PS.Abort_With_Log('RollbackRP', 'Restore Point #' + rp_num + ' Was NOT FOUND!',
                          'Restore Point #' + rp_num + ' Was NOT FOUND!', log_file)

    # Compare Versions
    vc.check_pacback_version(version, rp_path, meta_exists, meta)

    ####################
    # Full Restore Point
    ####################
    if full_rp is True:
        if meta_exists is True:
            # Pass If No Packages Have Changed
            if len(changed_pkgs) > 0:
                PS.prSuccess('No Packages Have Been Upgraded!')
                PS.Write_To_Log('RollbackRP', 'No Packages Have Been Upgraded', log_file)
            else:
                found_pkgs = pu.search_paccache(m_search, pu.fetch_paccache())
                PS.pacman(' '.join(found_pkgs), '-U')
                PS.Write_To_Log('RollbackRP', 'Send Found Packages to pacman -U', log_file)

        elif meta_exists is False:
            rp_cache = rp_path + '/pac_cache'
            PS.pacman(rp_cache + '/*', '--needed -U')
            PS.Write_To_Log('RollbackRP', 'Send pacman -U /* --needed', log_file)
            PS.prError('Restore Point #' + rp_num + ' MetaData Was NOT FOUND!')
            PS.Abort_With_Log('RollbackRP', 'Meta Is Missing So Skipping Advanced Features',
                              'Skipping Advanced Features!', log_file)

    #####################
    # Light Restore Point
    #####################
    elif meta_exists is True and full_rp is False:

        # Pass If No Packages Have Changed
        if len(changed_pkgs) > 0:
            PS.prWorking('Bulk Scanning for ' + str(len(meta_old_pkgs)) + ' Packages...')
            found_pkgs = pu.search_paccache(m_search, pu.fetch_paccache())
        else:
            PS.prSuccess('No Packages Have Been Upgraded!')
            PS.Write_To_Log('RollbackRP', 'No Packages Have Been Upgraded', log_file)
            found_pkgs = {}

        if len(changed_pkgs) == 0:
            pass

        # Pass Comparison if All Packages Found
        elif len(found_pkgs) == len(changed_pkgs):
            PS.prSuccess('All Packages Found In Your Local File System!')
            PS.Write_To_Log('RollbackRP', 'All Packages Found', log_file)
            PS.pacman(' '.join(found_pkgs), '--needed -U')
            PS.Write_To_Log('RollbackRP', 'Sent Found Packages To pacman -U', log_file)

        # Branch if Packages are Missing
        elif len(found_pkgs) < len(changed_pkgs):
            PS.Write_To_Log('RollbackRP', str(len(found_pkgs) - len(changed_pkgs)) + ' Packages Are Where Not Found', log_file)
            missing_pkg = set(m_search - pu.trim_pkg_list(found_pkgs))

            # Show Missing Pkgs
            PS.prWarning('Couldn\'t Find The Following Package Versions:')
            for pkg in missing_pkg:
                PS.prError(pkg)

            if PS.YN_Frame('Do You Want To Continue Anyway?') is True:
                PS.pacman(' '.join(found_pkgs), '-U')
                PS.Write_To_Log('RollbackRP', 'Sent Found Packages To pacman -U', log_file)
            else:
                PS.Abort_With_Log('RollbackRP', 'User Aborted Rollback Because of Missing Packages',
                                  'Aborting Rollback!', log_file)

    # Ask User If They Want to Remove New Packages
    if len(added_pkgs) > 0:
        PS.prWarning('The Following Packages Are Installed But Are NOT Present in Restore Point #' + rp_num + ':')
        PS.Write_To_Log('RollbackRP', str(len(added_pkgs)) + ' Have Been Added Since RP Creation', log_file)
        for pkg in added_pkgs:
            PS.prAdded(pkg)
        if PS.YN_Frame('Do You Want to Remove These Packages From Your System?') is True:
            PS.pacman(' '.join(added_pkgs), '-R')
            PS.Write_To_Log('RollbackRP', 'Sent Added Packages To pacman -R', log_file)
    else:
        PS.Write_To_Log('RollbackRP', 'No Packages Have Been Added Since RP Creation', log_file)

    ##########################
    # Diff Restore Point Files
    ##########################
    if len(meta_dirs) > 0:
        custom_dirs = rp_tar[:-4]
        if os.path.exists(rp_tar + '.gz'):
            PS.prWorking('Decompressing Restore Point....')
            if any(re.findall('pigz', line.lower()) for line in current_pkgs):
                os.system('pigz -d ' + rp_tar + '.gz -f')
            else:
                PS.GZ_D(rp_tar + '.gz')

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

        #################
        # Overwrite Files
        #################
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

    else:
        PS.prSuccess('Rollback to Restore Point #' + rp_num + ' Complete!')
        PS.Write_To_Log('RollbackRP', 'Rollback to RP #' + rp_num + ' Complete', log_file)

    PS.End_Log('RollbackRP', log_file)
