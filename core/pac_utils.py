#! /usr/bin/env python3
import os
import re
import itertools
import datetime as dt
import multiprocessing as mp
import python_scripts as PS

log_file = '/var/log/pacback.log'
rp_paths = '/var/lib/pacback/restore-points'


#<#><#><#><#><#><#>#<#>#<#
#<># Utils For Other Funcs
#<#><#><#><#><#><#>#<#>#<#


def max_threads():
    cores = os.cpu_count()
    if cores >= 4:
        return 4
    else:
        return cores


def find_pkgs_in_dir(path):
    cache = {f for f in PS.Search_FS(path, 'set')
             if f.endswith(".pkg.tar.xz") or f.endswith(".pkg.tar.zst")}
    return cache


def first_pkg_path(pkgs, fs_list):
    paths = list()
    for pkg in pkgs:
        for f in fs_list:
            if f.split('/')[-1] == pkg:
                paths.append(f)
                break
    return paths


def search_pkg_chunk(search, fs_list):
    pkgs = list()
    for f in fs_list:
        if re.findall(search, f.lower()):
            pkgs.append(f)
    return pkgs


def trim_pkg_list(pkg_list):
    '''Removes prefix dir and x86_64.pkg.tar.zsd suffix.'''
    pkg_split = {pkg.split('/')[-1] for pkg in pkg_list}
    pkg_split = {'-'.join(pkg.split('-')[:-1]) for pkg in pkg_split}
    return pkg_split


#<#><#><#><#><#><#>#<#>#<#
#<># Pacman Utils
#<#><#><#><#><#><#>#<#>#<#


def pacman_Q(replace_spaces=False):
    '''Writes the output into /tmp, reads file, then removes file.'''
    os.system("pacman -Q > /tmp/pacman_q.meta")
    ql = PS.Read_List('/tmp/pacman_q.meta', typ='set')
    PS.RM_File('/tmp/pacman_q.meta', sudo=True)
    if replace_spaces is True:
        rl = {s.strip().replace(' ', '-') for s in ql}
        return rl
    else:
        return ql


def fetch_paccache():
    '''Always returns a unique list of pkgs found on the file sys.'''

    # Searches File System For Packages
    pacman_cache = find_pkgs_in_dir('/var/cache/pacman/pkg')
    root_cache = find_pkgs_in_dir('/root/.cache')
    pacback_cache = find_pkgs_in_dir('/var/lib/pacback')
    user_cache = set()
    users = os.listdir('/home')

    for u in users:
        u_pkgs = find_pkgs_in_dir('/home/' + u + '/.cache')
        user_cache = user_cache.union(u_pkgs)

    fs_list = pacman_cache.union(root_cache, pacback_cache, user_cache)
    PS.Write_To_Log('FetchPaccache', 'Searched ALL Package Cache Locations', log_file)

    unique_pkgs = PS.Trim_Dir(fs_list)
    if len(fs_list) != len(unique_pkgs):
        PS.prWorking('Filtering Duplicate Packages...')

        chunk_size = int(round(len(unique_pkgs) / max_threads(), 0)) + 1
        unique_pkgs = list(f for f in unique_pkgs)
        chunks = [unique_pkgs[i:i + chunk_size] for i in range(0, len(unique_pkgs), chunk_size)]

        with mp.Pool(processes=max_threads()) as pool:
            new_fs = pool.starmap(first_pkg_path, zip(chunks, itertools.repeat(fs_list)))
            new_fs = set(itertools.chain(*new_fs))

        PS.Write_To_Log('FetchPaccache', 'Returned ' + str(len(new_fs)) + ' Unique Cache Packages', log_file)
        return new_fs

    else:
        PS.Write_To_Log('FetchPaccache', 'Returned ' + str(len(fs_list)) + ' Cached Packages', log_file)
        return fs_list


def search_paccache(pkg_list, fs_list):
    '''Searches cache for matching pkg versions and returns results.'''
    PS.Write_To_Log('SearchPaccache', 'Started Search for ' + str(len(pkg_list)) + ' Packages', log_file)

    # Combing package names into one term provides much faster results
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in pkg_list)))
    chunk_size = int(round(len(fs_list) / max_threads(), 0)) + 1
    fs_list = list(f for f in fs_list)
    chunks = [fs_list[i:i + chunk_size] for i in range(0, len(fs_list), chunk_size)]

    with mp.Pool(processes=max_threads()) as pool:
        found_pkgs = pool.starmap(search_pkg_chunk, zip(itertools.repeat(bulk_search), chunks))
        found_pkgs = set(itertools.chain(*found_pkgs))

    PS.Write_To_Log('SearchPaccache', 'Found ' + str(len(found_pkgs)) + ' OUT OF ' + str(len(pkg_list)) + ' Packages', log_file)
    return found_pkgs


#<#><#><#><#><#><#>#<#>#<#
#<># Rollback Packages
#<#><#><#><#><#><#>#<#>#<#


def user_pkg_search(search_pkg, cache):
    '''Provides more accurate searches for single pkg names without a version.'''
    pkgs = trim_pkg_list(cache)
    found = set()

    for p in pkgs:
        r = re.split("\d+-\d+|\d+(?:\.\d+)+|\d:\d+(?:\.\d+)+", p)[0]
        if r.strip()[-1] == '-':
            x = r.strip()[:-1]
        else:
            x = r
        if re.fullmatch(re.escape(search_pkg.lower().strip()), x):
            found.add(p)

    if not found:
        PS.prError('No Packages Found!')
        if PS.YN_Frame('Do You Want to Extend the Regex Search?') is True:
            for p in pkgs:
                if re.findall(re.escape(search_pkg.lower().strip()), p):
                    found.add(p)

    return found


def rollback_packages(pkg_list):
    PS.prWorking('Searching File System for Packages...')
    cache = fetch_paccache(rp_paths)
    PS.Write_To_Log('UserSearch', 'Started Search for ' + ' '.join(pkg_list), log_file)

    for pkg in pkg_list:
        found_pkgs = user_pkg_search(pkg, cache)

        if found_pkgs:
            PS.Write_To_Log('UserSearch', 'Found ' + str(len(found_pkgs)) + 'pkgs for ' + pkg, log_file)
            PS.prSuccess('Pacback Found the Following Package Versions for ' + pkg + ':')
            answer = PS.Multi_Choice_Frame(found_pkgs)

            if answer is False:
                PS.Write_To_Log('UserSearch', 'User Force Exited Multi_Choice_Frame - ' + pkg, log_file)
                break
            for x in cache:
                if re.findall(re.escape(answer), x):
                    path = x

            PS.pacman(path, '-U')
            PS.Write_To_Log('UserSearch', 'Sent -U ' + path + ' to Pacman', log_file)

        else:
            PS.prError('No Packages Found Under the Name: ' + pkg)
            PS.Write_To_Log('UserSearch', 'Search ' + pkg.upper() + ' Returned Zero Results', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Better Cache Cleaning
#<#><#><#><#><#><#>#<#>#<#


def clean_cache(count):
    PS.Start_Log('Clean_Cache', log_file)
    PS.prWorking('Starting Advanced Cache Cleaning...')
    if PS.YN_Frame('Do You Want To Uninstall Orphaned Packages?') is True:
        os.system('sudo pacman -R $(pacman -Qtdq)')
        PS.Write_To_Log('Clean_Cache', 'Ran pacman -R $(pacman -Qtdq)', log_file)

    if PS.YN_Frame('Do You Want To Remove Old Versions of Installed Packages?') is True:
        os.system('sudo paccache -rk ' + count)
        PS.Write_To_Log('Clean_Cache', 'Ran paccache -rk ' + count, log_file)

    if PS.YN_Frame('Do You Want To Remove Cached Orphans?') is True:
        os.system('sudo paccache -ruk0')
        PS.Write_To_Log('Clean_Cache', 'Ran paccache -ruk0', log_file)

    if PS.YN_Frame('Do You Want To Check For Old Pacback Restore Points?') is True:
        PS.Write_To_Log('Clean_Cache', 'Started Search For Old RPs', log_file)
        metas = PS.Search_FS('/var/lib/pacback/restore-points', 'set')
        rps = {f for f in metas if f.endswith(".meta")}

        for m in rps:
            rp_num = m.split('/')[-1]
            # Find RP Create Date in Meta File
            meta = PS.Read_List(m)
            for l in meta:
                if l.split(':')[0] == 'Date Created':
                    target_date = l.split(':')[1].strip()
                    break

            # Parse and Format Dates for Compare
            today = dt.datetime.now().strftime("%Y/%m/%d")
            t_split = list(today.split('/'))
            today_date = dt.date(int(t_split[0]), int(t_split[1]), int(t_split[2]))
            o_split = list(target_date.split('/'))
            old_date = dt.date(int(o_split[0]), int(o_split[1]), int(o_split[2]))

            # Compare Days
            days = (today_date - old_date).days
            if days > 180:
                PS.prWarning(m.split('/')[-1] + ' Is Over 180 Days Old!')
                if PS.YN_Frame('Do You Want to Remove This Restore Point?') is True:
                    PS.RM_File(m, sudo=True)
                    PS.RM_Dir(m[:-5], sudo=True)
                    PS.prSuccess('Restore Point Removed!')
                    PS.Write_To_Log('Clean_Cache', 'Removed RP ' + rp_num, log_file)
            PS.prSuccess(rp_num + ' Is Only ' + str(days) + ' Days Old!')
            PS.Write_To_Log('Clean_Cache', 'RP ' + rp_num + ' Was Less Than 180 Days 0ld', log_file)

    PS.End_Log('Clean_Cache', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Unlock Mirrorlist
#<#><#><#><#><#><#>#<#>#<#


def unlock_rollback():
    PS.Start_Log('UnlockRollback', log_file)
    # Check if mirrorlist is locked
    if len(PS.Read_List('/etc/pacman.d/mirrorlist')) == 1:
        PS.Write_To_Log('UnlockRollback', 'Lock Detected on Mirrorlist', log_file)

        if os.path.exists('/etc/pacman.d/mirrolist.pacback'):
            PS.Write_To_Log('UnlockRollback', 'Backup Mirrorlist Is Missing', log_file)
            fetch = PS.YN_Frame('Pacback Can\'t Find Your Backup Mirrorlist! Do You Want to Fetch a New US HTTPS Mirrorlist?')
            if fetch is True:
                os.system("curl -s 'https://www.archlinux.org/mirrorlist/?country=US&protocol=https&use_mirror_status=on' | sed -e 's/^#Server/Server/' -e '/^#/d' | sudo tee /etc/pacman.d/mirrorlist.pacback >/dev/null")
            else:
                PS.Abort_With_Log('UnlockRollback', 'Backup Mirrorlist Is Missing and User Declined Download', 'Please Manually Replace Your Mirrorlist!', log_file)

        os.system('sudo cp /etc/pacman.d/mirrorlist.pacback /etc/pacman.d/mirrorlist')
        PS.Write_To_Log('UnlockRollback', 'Mirrorlist Was Restored Successfully', log_file)

    else:
        PS.Write_To_Log('UnlockRollback', 'No Mirrorlist Lock Was Found', log_file)
        PS.End_Log('UnlockRollback', log_file)
        return PS.prError('Pacback Does NOT Have an Active Date Lock!')

    # Update?
    update = PS.YN_Frame('Do You Want to Update Your System Now?')
    if update is True:
        os.system('sudo pacman -Syu')
        PS.Write_To_Log('UnlockRollback', 'User Ran -Syu Upgrade', log_file)
    if update is False:
        print('Skipping Update!')

    PS.End_Log('UnlockRollback', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Pacman Hook
#<#><#><#><#><#><#>#<#>#<#


def pacback_hook(install):
    '''Installs or removes a standard alpm hook in /etc/pacman.d/hooks
    Runs as a PreTransaction hook during every upgrade.'''
    PS.Start_Log('PacbackHook', log_file)

    if install is True:
        PS.MK_Dir('/etc/pacman.d/hooks', sudo=True)
        PS.Uncomment_Line_Sed('HookDir', '/etc/pacman.conf', sudo=True)
        if not os.path.exists('/etc/pacman.d/hooks/pacback.hook'):
            hook = ['[Trigger]',
                    'Operation = Upgrade',
                    'Type = Package',
                    'Target = *',
                    '',
                    '[Action]',
                    'Description = Pre-Upgrade Pacback Hook',
                    'Depends = pacman',
                    'When = PreTransaction',
                    'Exec = /usr/bin/pacback --hook']
            PS.Export_List('/etc/pacman.d/hooks/pacback.hook', hook)
            PS.prSuccess('Pacback Hook is Now Installed!')
            PS.Write_To_Log('InstallHook', 'Installed Pacback Hook Successfully', log_file)
        else:
            PS.prSuccess('Pacback Hook is Already Installed!')
            PS.Write_To_Log('InstallHook', 'Pacback Hook Was Already Installed', log_file)

    elif install is False:
        PS.RM_File('/etc/pacman.d/hooks/pacback.hook', sudo=True)
        PS.Write_To_Log('RemoveHook', 'Removed Pacback Hook Successfully', log_file)
        PS.prSuccess('Pacback Hook Removed!')

    PS.End_Log('PacbackHook', log_file)

#<#><#><#><#><#><#>#<#>#<#
#<># Show RP Info
#<#><#><#><#><#><#>#<#>#<#


def print_rp_info(num):
    rp_meta = rp_paths + '/rp' + num + '.meta'
    if os.path.exists(rp_meta):
        meta = PS.Read_List(rp_meta)
        meta = PS.Read_Between('Pacback RP', 'Pacman List', meta, re_flag=True)
        print('============================')
        for s in meta[:-1]:
            print(s)
        print('============================')

    elif os.path.exists(rp_meta):
        PS.prError('Meta is Missing For This Restore Point!')

    else:
        PS.prError('No Restore Point #' + num + ' Was NOT Found!')
