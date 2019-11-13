#! /usr/bin/python
#### A utility for marking and restoring stable arch packages 
## Version 0.3
from python_scripts import *
import re, tqdm #, pyinquirer

def create_restore_point(rp_num, dir_list='nil'):
    rp_path = '/usr/app/pacback/restore-points/rp' + str(rp_num)
    print('Retrieving Current Stable Packages...')
    os.system("pacman -Q | sed -e 's/ /-/g' > " + rp_path + '.inv')
    packages = read_list(rp_path + '.inv')
    print('Scanning File System...')
    fs_list = set(search_fs('/var/cache/pacman', 'set') | search_fs('~/.cache', 'set'))
    
    ### Loop Over Files Searching for Pkg's
    found_pkgs = set()
    packages = list(re.escape(pkg) for pkg in packages)
    bulk_search = ('|'.join(packages))
    for f in tqdm.tqdm(fs_list, desc='Bulk Scanning for ' + str(len(packages)) + ' Packages in ' + str(len(fs_list)) + ' Files'):
        if re.findall(bulk_search, f.lower()):
            found_pkgs.add(f)
   
    ### Add packages to tar
    with tarfile.open(rp_path + '.tar', 'w') as tar:
        for f in tqdm.tqdm(found_pkgs, desc='Adding Found Packages to Restore Archive'):
            tar.add(f, '/pac_cache/' + os.path.basename(f))

    ### Add Any Additional Dirs to Backup
    if dir_list is 'nil':
        return
    else:
        for dir in dir_list:
            cfs_list = search_fs(dir)
            with tarfile.open(rp_path + '.tar', 'a') as tar:
                for f in tqdm.tqdm(cfs_list, desc='Adding ' + dir + ' to Restore Archive'):
                    tar.add(f)

    print('Restore Point ' + str(rp_num) + ' Sucessfully Created!')


custom_list = ['~/.config', '~/.ssh']
create_restore_point(1, custom_list)
