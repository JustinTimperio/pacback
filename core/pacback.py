#! /usr/bin/python
#### A utility for marking and restoring stable arch packages 
## Version 0.2
from python_scripts import *
import re, tqdm #, pyinquirer

def create_restore_point(rp_num, dir_list='nil'):
    rp_path = '/usr/app/pacback/restore-points/rp' + str(rp_num)
    print('Retrieving Current Stable Packages...')
    os.system("sudo pacman -Q | sed -e 's/ /-/g' > " + rp_path + '.inv')
    packages = read_list(rp_path + '.inv')
    print('Scanning File System...')
    fs_list = set(set(search_fs('/var/cache/pacman')) | set(search_fs('~/.cache')))
    ### Print Len's
    print('Files Found : ' + str(len(fs_list)))
    
    ### Build Match Package Function 
    def match_pkg(pkg):
        try: n = re.compile(pkg, re.IGNORECASE) 
        except: return
        for f in tqdm.tqdm(fs_list, desc='Searching for ' + pkg):
            if re.findall(n, f.lower()):
                found_pkgs.add(f)
    
    ### For Loop Over All Packages
    found_pkgs = set()
    for pkg in tqdm.tqdm(packages, desc='Scanning for ' + str(len(packages)) + ' Packages in ' + str(len(fs_list)) + ' Files'):
        match_pkg(pkg)
   
    ### Add packages to tar
    with tarfile.open(rp_path + '.tar', 'w') as tar:
        for f in tqdm.tqdm(found_pkgs, desc='Adding Packages to Restore Archive'):
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

    print('Restore Point Sucessfully Generated!')


custom_list = ['~/.config', '~/.ssh']
create_restore_point(1, custom_list)
