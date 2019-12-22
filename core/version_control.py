#! /usr/bin/env python3
import os
import tarfile
import tqdm
import python_scripts as PS
import pac_utils as PU

#<#><#><#><#><#><#>#<#>#<#
#+# Version Control
#<#><#><#><#><#><#>#<#>#<#

def check_pacback_version(current_version, rp_path, meta_exists, meta):
    if meta_exists is False:
        # Check for Full RP Created Before V1.5
        if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
            PS.prError('Full Restore Points Generated Before Version 1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
            PS.prError('Without Meta Data Pacback Can\'t Upgrade This Restore Point!')
            fail = True
            return fail

    elif meta_exists is True:
        # Find version in metadate file
        for m in meta:
            if m.split(':')[0] == 'Pacback Version':
                target_version = m.split(':')[1]
                break

        # Parse version into vars
        cv_major = int(current_version.split('.')[0])
        cv_minor = int(current_version.split('.')[1])
        cv_patch = int(current_version.split('.')[2])
        ####
        tv_major = int(target_version.split('.')[0])
        tv_minor = int(target_version.split('.')[1])
        tv_patch = int(target_version.split('.')[2])

        # Check for Full RP's Created Before V1.5
        if tv_major == 1 and tv_minor < 5:
            if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
                PS.prError('Full Restore Points Generated Before V1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
                upgrade = PS.YN_Frame('Do You Want to Upgrade This Restore Point?')
                if upgrade is True:
                    upgrade_to_hardlinks(rp_path)
                else:
                    fail = True
                    return fail
    fail = False
    return fail


def upgrade_to_hardlinks(rp_path):
    # This is a Total Hack Job. Don't Judge Me :(
    PS.prWorking('Unpacking...')
    if os.path.exists(rp_path + '.tar.gz'):
        PS.GZ_D(rp_path + '.tar.gz')
    PS.Untar_Dir(rp_path + '.tar')

    # Read and Parse Meta Data
    meta = PS.Read_List(rp_path + '.meta')
    meta_old_pkgs = PS.Read_Between('======= Pacman List ========', '<Endless>', meta)
    meta_dirs = PS.Read_Between('========= Dir List =========', '======= Pacman List ========', meta)[:-1]

    # Find Existing Package
    pc = PS.Search_FS(rp_path + '/pac_cache')
    found = PU.search_paccache(PS.Replace_Spaces(meta_old_pkgs), PU.fetch_paccache())

    if len(found) == len(pc):
        PS.prSuccess('All Packages Found!')
        PS.RM_Dir(rp_path + '/pac_cache', sudo=True)
        PS.MK_Dir(rp_path + '/pac_cache', sudo=False)
        for pkg in tqdm.tqdm(found, desc='Hardlinking Packages to Pacback RP'):
            os.system('sudo ln ' + pkg + ' ' + rp_path + '/pac_cache/' + pkg.split('/')[-1])

    elif len(found) < len(pc):
        duplicate = PS.Trim_Dir(pc).intersection(PS.Trim_Dir(found))
        for d in tqdm.tqdm(duplicate, desc='Mergeing and Hardlinking'):
            PS.RM_File(rp_path + '/pac_cache/' + d, sudo=True)
            for p in found:
                if p.split('/')[-1] == d.split('/')[-1]:
                    os.system('sudo ln ' + p + ' ' + rp_path + '/pac_cache/' + d)
                    break

    if len(meta_dirs) > 0:
        f_list = set()
        rp_fs = PS.Search_FS(rp_path)
        for f in rp_fs:
            if f[len(rp_path):].split('/')[1] != 'pac_cache':
                f_list.add(f)

        with tarfile.open(rp_path + '/' + rp_path[-2:] + '_dirs.tar', 'w') as tar:
            for f in tqdm.tqdm(f_list, desc='Adding Dir\'s to Tar'):
                tar.add(f, f[len(rp_path):])

        for d in meta_dirs:
            PS.RM_Dir(rp_path + '/' + d.split('/')[1], sudo=True)

    PS.RM_File(rp_path + '.tar', sudo=True)
    PS.prSuccess('RP Version Upgrade Complete!')

def print_rp_info(rp_path):
    if os.path.exists(rp_path + '.meta'):
        meta = PS.Read_List(rp_path + '.meta')
        meta = PS.Read_Between('Pacback RP', 'Pacman List', meta, re_flag=True)
        print('============================')
        for s in meta[:-1]:
           print(s)
        print('============================')

    elif os.path.exists(rp_path):
        PS.prError('Meta is Missing For This Restore Point!')

    else:
        PS.prError('No Restore Point #' + num + ' Was NOT Found!')
