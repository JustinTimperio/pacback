#! /usr/bin/env python3
#### Utils used by pacback
from python_scripts import *
import tqdm

#<#><#><#><#><#><#>#<#>#<#
#+# Pacman Utils
#<#><#><#><#><#><#>#<#>#<#

def pacman_Q(replace_spaces=False):
    os.system("pacman -Q > /tmp/pacman_q.meta")
    l = read_list('/tmp/pacman_q.meta', typ='set')
    rm_file('/tmp/pacman_q.meta', sudo=True)
    if replace_spaces == True:
        rl = {s.strip().replace(' ', '-') for s in l}
        return rl
    else:
        return l

def fetch_paccache(pac_path=None):
    pac_cache = search_fs('/var/cache/pacman/pkg', 'set')
    user_cache = {f for f in search_fs('~/.cache', 'set') if f.endswith(".pkg.tar.xz")}

    if not pac_path == None:
        pacback_cache = {f for f in search_fs(pac_path, 'set') if f.endswith('.pkg.tar.xz')}
        fs_list = pac_cache.union(user_cache, pacback_cache)
    else:
        fs_list = pac_cache.union(user_cache)

    ### Check for Duplicate Packages in fs_list
    unique_pkgs = {p.split('/')[-1] for p in fs_list}
    if len(fs_list) != len(unique_pkgs):
        prWorking('Filtering Duplicate Packages...')
        new_fs = set()

        for u in unique_pkgs:
            u_split = u.split('/')[-1]
            for x in fs_list:
                if x.split('/')[-1] == u_split:
                    new_fs.add(x)
                    break
        return new_fs
    else:
        return fs_list

def search_paccache(pkg_list, fs_list):
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in pkg_list))) ### Packages like g++ need to be escaped
    found_pkgs = set()
    for f in fs_list:
        if re.findall(bulk_search, f.lower()):
            found_pkgs.add(f)
    return found_pkgs

def trim_pkg_list(pkg_list):
    pkg_split = {pkg.split('/')[-1] for pkg in pkg_list} ### Remove Dir Path
    pkg_split = {'-'.join(pkg.split('-')[:-1]) for pkg in pkg_split} ### Remove .pkg.tar.xz From Name
    return pkg_split


#<#><#><#><#><#><#>#<#>#<#
#+# Version Control
#<#><#><#><#><#><#>#<#>#<#

def check_pacback_version(current_version, rp_path, target_version='nil'):
    ### Failsafe When Meta Is Missing
    if target_version == 'nil':
        ### Check for Full RP Created Before V1.5
        if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
            prError('Full Restore Points Generated Before Version 1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
            prError('Without Meta Data Pacback Can\'t Upgrade This Restore Point!')
            fail = True
            return fail

    ### Parse Version if Meta Exists
    else:
        cv_major = int(current_version.split('.')[0])
        cv_minor = int(current_version.split('.')[1])
        cv_patch = int(current_version.split('.')[2])
        ####
        tv_major = int(target_version.split('.')[0])
        tv_minor = int(target_version.split('.')[1])
        tv_patch = int(target_version.split('.')[2])

        ### Check for Full RP's Created Before V1.5
        if tv_major == 1 and tv_minor < 5:
            if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
                prError('Full Restore Points Generated Before V1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
                upgrade = yn_frame('Do You Want to Upgrade This Restore Point?')
                if upgrade == True:
                    upgrade_to_hardlinks(rp_path)
                else:
                    fail = True
                    return fail
    fail = False
    return fail

def upgrade_to_hardlinks(rp_path):
    ### This is a Total Hack Job. Don't Judge Me :(
    prWorking('Unpacking...')
    if os.path.exists(rp_path + '.tar.gz'):
        gz_d(rp_path + '.tar.gz') ### Decompress with Python
    untar_dir(rp_path + '.tar')

    ### Read and Parse Meta Data
    meta = read_list(rp_path + '.meta')
    meta_old_pkgs = read_between('======= Pacman List ========','<Endless>', meta)
    meta_dirs = read_between('========= Dir List =========','======= Pacman List ========', meta)[:-1]
    m_search = {s.strip().replace(' ', '-') for s in meta_old_pkgs}

    ### Find Existing Package
    pc = search_fs(rp_path + '/pac_cache')
    found = search_paccache(m_search, fetch_paccache())

    if len(found) == len(pc):
        prSuccess('All Packages Found!')
        rm_dir(rp_path + '/pac_cache', sudo=True)
        mkdir(rp_path + '/pac_cache', sudo=False)
        for pkg in tqdm.tqdm(found, desc='Hardlinking Packages to Pacback RP'):
            os.system('sudo ln ' + pkg + ' ' + rp_path + '/pac_cache/' + pkg.split('/')[-1])

    elif len(found) < len(pc):
        duplicate = {pkg.split('/')[-1] for pkg in pc}.intersection({pkg.split('/')[-1] for pkg in found})
        for d in tqdm.tqdm(duplicate, desc='Mergeing and Hardlinking'):
            rm_file(rp_path + '/pac_cache/' + d, sudo=True)
            for p in found:
                if p.split('/')[-1] == d.split('/')[-1]:
                    os.system('sudo ln ' + p + ' ' + rp_path + '/pac_cache/' + d)
                    break

    if len(meta_dirs) > 0:
        f_list = set()
        rp_fs = search_fs(rp_path)
        for f in rp_fs:
            if f[len(rp_path):].split('/')[1] != 'pac_cache':
                f_list.add(f)

        with tarfile.open(rp_path + '/' + rp_path[-2:] + '_dirs.tar', 'w') as tar:
            for f in tqdm.tqdm(f_list, desc='Adding Dir\'s to Tar'):
                tar.add(f, f[len(rp_path):])

        for d in meta_dirs:
            rm_dir(rp_path + '/' + d.split('/')[1], sudo=True)

    rm_file(rp_path + '.tar', sudo=True)
    prSuccess('RP Version Upgrade Complete!')


#<#><#><#><#><#><#>#<#>#<#
#+# Pacman Hook
#<#><#><#><#><#><#>#<#>#<#

def pacback_hook(install):
    if install == True:
        mkdir('/etc/pacman.d/hooks', sudo=True)
        uncomment_line_sed('HookDir', '/etc/pacman.conf', sudo=True)
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
            for h in hook:
                os.system('echo ' + escape_bash(h) + '| sudo tee -a /etc/pacman.d/hooks/pacback.hook > /dev/null')
            prSuccess('Pacback Hook is Now Installed!')
        else:
            prSuccess('Pacback Hook is Already Installed!')

    elif install == False:
        rm_file('/etc/pacman.d/hooks/pacback.hook', sudo=True)
        prSuccess('Pacback Hook Removed!')


#<#><#><#><#><#><#>#<#>#<#
#+# Better Cache Cleaning
#<#><#><#><#><#><#>#<#>#<#

def clean_cache(count, base_dir):
    prWorking('Starting Advanced Cache Cleaning...')
    if yn_frame('Do You Want To Uninstall Orphaned Packages?') == True:
        os.system('sudo pacman -R $(pacman -Qtdq)')

    if yn_frame('Do You Want To Remove Old Versions of Installed Packages?') == True:
        os.system('sudo paccache -rk ' + count)
    
    if yn_frame('Do You Want To Remove Cached Orphans?') == True:
        os.system('sudo paccache -ruk0')

    if yn_frame('Do You Want To Check For Old Pacback Restore Points?') == True:
        import datetime as dt
        rps = {f for f in search_fs(base_dir + '/restore-points', 'set') if f.endswith(".meta")}
        
        for m in rps:
            ### Find Create Date in Meta
            meta = read_list(m)
            for l in meta:
                if l.split(':')[0] == 'Date Created':
                    target_date = l.split(':')[1].strip()
                    break
            
            ### Parse and Format Dates for Compare
            today =  dt.datetime.now().strftime("%Y/%m/%d")
            t_split = list(today.split('/'))
            today_date = dt.date(int(t_split[0]), int(t_split[1]), int(t_split[2])) 
            o_split = list(target_date.split('/'))
            old_date = dt.date(int(o_split[0]), int(o_split[1]), int(o_split[2])) 

            ### Compare Days
            days = (today_date - old_date).days
            if days > 180:
                prWarning(m.split('/')[-1] + ' Is Over 180 Days Old!')
                if yn_frame('Do You Want to Remove This Restore Point?') == True:
                    rm_file(m, sudo=True)
                    rm_dir(m[:-5], sudo=True)
                    prSuccess('Restore Point Removed!')
            prSuccess(m.split('/')[-1] + ' Passed Comparison!')


#<#><#><#><#><#><#>#<#>#<#
#+# Diff RP Files
#<#><#><#><#><#><#>#<#>#<#

def diff_rp_files(rp_tar, meta_dirs, current_pkgs):
    custom_dirs = rp_tar[:-4]
    ### Decompress if .gz
    if os.path.exists(rp_tar + '.gz'):
        prWorking('Decompressing Restore Point....')
        if any(re.findall('pigz', line.lower()) for line in current_pkgs):
            os.system('pigz -d ' + rp_tar + '.gz -f') ### Decompress With pigz
        else:
            gz_d(rp_tar + '.gz') ### Decompress with Python

    ### Remove if Custom Dirs Unpacked
    if os.path.exists(custom_dirs):
        rm_dir(custom_dirs, sudo=True)

    ### Untar RP
    prWorking('Unpacking Files from Restore Point Tar....')
    untar_dir(rp_tar)

    diff_yn = yn_frame('Do You Want to Checksum Diff Restore Point Files Against Your Current File System?')
    if diff_yn == False:
        print('Skipping Diff!')
        pass

    elif diff_yn == True:
        import multiprocessing as mp
        rp_fs = search_fs(custom_dirs)
        rp_fs_trim = set(path[len(custom_dirs):] for path in search_fs(custom_dirs))

        ### Checksum Restore Point Files with a MultiProcessing Pool
        with mp.Pool(os.cpu_count()) as pool:
            rp_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs),
                            total=len(rp_fs), desc='Checksumming Restore Point Files'))
            sf_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs_trim),
                            total=len(rp_fs_trim), desc='Checksumming Source Files'))

        ### Compare Checksums For Files That Exist
        rp_csum_trim = set(path[len(custom_dirs):] for path in rp_checksum)
        rp_diff = sf_checksum.difference(rp_csum_trim)

        ### Filter Removed and Changed Files
        diff_removed = set()
        diff_changed = set()
        for csum in rp_diff:
            if re.findall('FILE MISSING', csum):
                diff_removed.add(csum)
            else:
                diff_changed.add(csum.split(' : ')[0] + ' : FILE CHANGED!')

        ### Find Added Files
        src_fs = set()
        for x in meta_dirs:
            for l in search_fs(x):
                src_fs.add(l)
        diff_new = src_fs.difference(rp_fs_trim)

        ### Print Changed Files For User
        if len(diff_changed) + len(diff_new) + len(diff_removed) == 0:
            rm_dir(custom_dirs, sudo=True)
            return prSuccess('No Files Have Been Changed!')

    #######################
    ### Overwrite Files ###
    #######################
    if diff_yn == False:
        prWarning('YOU HAVE NOT CHECKSUMED THE RESTORE POINT! OVERWRITING ALL FILES CAN BE EXTREAMLY DANGOURS!')
        ow = yn_frame('Do You Still Want to Continue and Restore ALL Files In the Restore Point?')
        if ow == False:
            return print('Skipping Automatic File Restore! Restore Point Files Are Unpacked in ' + custom_dirs)

        elif ow == True:
            print('Starting Full File Restore! Please Be Patient As All Files are Overwritten...')
            rp_fs = search_fs(custom_dirs)
            for f in rp_fs:
                prWorking('Please Be Patient. This May Take a While...')
                os.system('sudo mkdir -p ' + escape_bash('/'.join(f.split('/')[:-1])) + ' && sudo cp -af ' + escape_bash(f) + ' ' + escape_bash(f[len(custom_dirs):]))

    elif diff_yn == True:
        ow = yn_frame('Do You Want to Automaticly Restore Changed and Missing Files?')
        if ow == False:
            return print('Skipping Automatic Restore! Restore Point Files Are Unpacked in ' + custom_dirs)

        if ow == True:
            if len(diff_changed) > 0:
                prWarning('The Following Files Have Changed:')
                for f in diff_changed:
                    prChanged(f)
                if yn_frame('Do You Want to Overwrite Files That Have Been CHANGED?') == True:
                    prWorking('Please Be Patient. This May Take a While...')
                    for f in diff_changed:
                        fs = (f.split(' : ')[0])
                        os.system('sudo cp -af ' + escape_bash(custom_dirs + fs) + ' ' + escape_bash(fs))

        if len(diff_removed) > 0:
            prWarning('The Following Files Have Removed:')
            for f in diff_removed:
                prRemoved(f)
            if yn_frame('Do You Want to Add Files That Have Been REMOVED?') == True:
                prWorking('Please Be Patient. This May Take a While...')
                for f in diff_removed:
                    fs = (f.split(' : ')[0])
                    os.system('sudo mkdir -p ' + escape_bash('/'.join(fs.split('/')[:-1])) + ' && sudo cp -af ' + escape_bash(custom_dirs + fs) + ' ' + escape_bash(fs))

        if len(diff_new) > 0:
            for f in diff_new:
                prAdded(f + ' : NEW FILE!')
            if yn_frame('Do You Want to Remove Files That Have Beend ADDED?') == True:
                prWorking('Please Be Patient. This May Take a While...')
                for f in diff_new:
                    fs = (f.split(' : ')[0])
                    os.system('sudo rm ' + fs)

    rm_dir(custom_dirs, sudo=True)
    prSuccess('File Restore Complete!')
