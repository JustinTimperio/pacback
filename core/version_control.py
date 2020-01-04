#! /usr/bin/env python3
import os
import tarfile
import tqdm
import python_scripts as PS
import pac_utils as PU

log_file = '/var/log/pacback.log'
rp_paths = '/var/lib/pacback/restore-points'


#<#><#><#><#><#><#>#<#>#<#
#<># Version Control
#<#><#><#><#><#><#>#<#>#<#

def pre_fligh_check():
    if not os.getuid() == 0:
        PS.Start_Log('PreFlight', log_file)
        PS.Abort_With_Log('PreFlight', 'Not Root!', 'Pacback Must Be Run With Sudo OR As Root!', log_file)

    base_dir = os.path.dirname(os.path.realpath(__file__))[:-5]
    old_rp_path = base_dir + '/restore-points'
    if os.path.exists(old_rp_path):
        PS.Start_Log('PreFlight', log_file)
        PS.prError('Looks Like You Are Upgrading From A Version Before 1.6!')
        PS.prWorking('Migrating Your Restore Point Folder Now...')
        PS.MK_Dir('/var/lib/pacback', sudo=False)
        os.system('mv ' + old_rp_path + ' /var/lib/pacback')
        PS.Write_To_Log('PreFlight', 'Pacback Successfully Migrated To /var/lib/pacback', log_file)


def check_pacback_version(current_version, rp_path, meta_exists, meta):
    if meta_exists is False:
        PS.Write_To_Log('VersionControl', 'Restore Point is Missing MetaData', log_file)

        # Check for Full RP Created Before V1.5
        if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
            PS.prError('Full Restore Points Generated Before Version 1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
            PS.Abort_With_Log('VersionControl','RP Version is > V1.5 and MetaData is Missing',
                              'Without Meta Data Pacback Can\'t Upgrade This Restore Point!', log_file)

    elif meta_exists is True:
        # Find version in metadate file
        for m in meta:
            if m.split(':')[0] == 'Pacback Version':
                target_version = m.split(':')[1].strip()
                break

        # Parse version into vars
        cv_M = int(current_version.split('.')[0])
        cv_m = int(current_version.split('.')[1])
        cv_p = int(current_version.split('.')[2])
        ####
        tv_M = int(target_version.split('.')[0])
        tv_m = int(target_version.split('.')[1])
        tv_p = int(target_version.split('.')[2])

        if current_version != target_version:
            PS.Write_To_Log('VersionControl', 'Current Version ' + current_version + ' Miss-Matched With ' + target_version, log_file)
        else:
            PS.Write_To_Log('VersionControl', 'Both Versions Match ' + current_version, log_file)

        # Check for Full RP's Created Before V1.5
        if tv_M == 1 and tv_m < 5:
            if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
                PS.prError('Full Restore Points Generated Before V1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
                PS.Write_To_Log('VersionControl', 'Detected Restore Point Version Generated > V1.5', log_file)
                upgrade = PS.YN_Frame('Do You Want to Upgrade This Restore Point?')
                if upgrade is True:
                    upgrade_to_hardlinks(rp_path)
                else:
                    PS.Abort_With_Log('VersionControl', 'User Exited Upgrade',
                                      'Aborting!', log_file)


def upgrade_to_hardlinks(rp_path):
    # This is a Total Hack Job. Don't Judge Me :(
    PS.prWorking('Unpacking...')
    PS.Write_To_Log('HardlinkUpgrade', 'Unpacking Old Restore Point For Conversion', log_file)
    if os.path.exists(rp_path + '.tar.gz'):
        PS.GZ_D(rp_path + '.tar.gz')
    PS.Untar_Dir(rp_path + '.tar')
    PS.Write_To_Log('HardlinkUpgrade', 'Unpacked Restore Point', log_file)

    # Read and Parse Meta Data
    meta = PS.Read_List(rp_path + '.meta')
    meta_old_pkgs = PS.Read_Between('======= Pacman List ========', '<Endless>', meta)
    meta_dirs = PS.Read_Between('========= Dir List =========', '======= Pacman List ========', meta)[:-1]
    PS.Write_To_Log('HardlinkUpgrade', 'Read RP MetaData', log_file)

    # Find Existing Package
    pc = PS.Search_FS(rp_path + '/pac_cache')
    found = PU.search_paccache(PS.Replace_Spaces(meta_old_pkgs), PU.fetch_paccache())

    if len(found) == len(pc):
        PS.prSuccess('All Packages Found!')
        PS.Write_To_Log('HardlinkUpgrade', 'All Packages Where Found Elsewhere', log_file)
        PS.RM_Dir(rp_path + '/pac_cache', sudo=False)
        PS.MK_Dir(rp_path + '/pac_cache', sudo=False)
        for pkg in tqdm.tqdm(found, desc='Hardlinking Packages to Pacback RP'):
            os.system('sudo ln ' + pkg + ' ' + rp_path + '/pac_cache/' + pkg.split('/')[-1])
        PS.Write_To_Log('HardlinkUpgrade', 'Hardlinked Packages From Other Locations', log_file)

    elif len(found) < len(pc):
        PS.Write_To_Log('HardlinkUpgrade', 'Not All Packages Where Found. Mergeing With Hardlinks', log_file)
        duplicate = PS.Trim_Dir(pc).intersection(PS.Trim_Dir(found))
        for d in tqdm.tqdm(duplicate, desc='Mergeing and Hardlinking'):
            PS.RM_File(rp_path + '/pac_cache/' + d, sudo=False)
            for p in found:
                if p.split('/')[-1] == d.split('/')[-1]:
                    os.system('sudo ln ' + p + ' ' + rp_path + '/pac_cache/' + d)
                    break
        PS.Write_To_Log('HardlinkUpgrade', 'Successfully Merged Restore Point Packages', log_file)

    if len(meta_dirs) > 0:
        PS.Write_To_Log('HardlinkUpgrade', 'Detected Custom Files Saved In RP', log_file)
        f_list = set()
        rp_fs = PS.Search_FS(rp_path)
        for f in rp_fs:
            if f[len(rp_path):].split('/')[1] != 'pac_cache':
                f_list.add(f)

        with tarfile.open(rp_path + '/' + rp_path[-2:] + '_dirs.tar', 'w') as tar:
            for f in tqdm.tqdm(f_list, desc='Adding Dir\'s to Tar'):
                tar.add(f, f[len(rp_path):])
        PS.Write_To_Log('HardlinkUpgrade', 'Added Custom Files To New RP Tar', log_file)

        for d in meta_dirs:
            PS.RM_Dir(rp_path + '/' + d.split('/')[1], sudo=False)
        PS.Write_To_Log('HardlinkUpgrade', 'Cleaned Unpacked Custom Files', log_file)

    PS.RM_File(rp_path + '.tar', sudo=False)
    PS.Write_To_Log('HardlinkUpgrade', 'Removed Old Restore Point Tar', log_file)
    PS.prSuccess('RP Version Upgrade Complete!')
    PS.Write_To_Log('HardlinkUpgrade', 'Restore Point Upgrade Complete', log_file)
