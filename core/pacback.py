#! /usr/bin/python
#### A utility for marking and restoring stable arch packages
## Version 0.5
from python_scripts import *
import re, tqdm #, pyinquirer

base_dir = os.path.dirname(os.path.realpath(__file__))[:-5]
#######################
### Restore Points
###################

def create_restore_point(rp_num, dir_list='nil'):
    ### Get Current Pkg List and Scan the File System
    rp_path = base_dir + '/restore-points/rp' + str(rp_num)
    print('Retrieving Current Stable Packages...')
    os.system("pacman -Q | sed -e 's/ /-/g' > " + rp_path + '.inv')
    packages = read_list(rp_path + '.inv')
    fs_list = set(search_fs('/var/cache/pacman', 'set') | search_fs('~/.cache', 'set'))

    ### Each Pkg Name Needs to be Escaped (like c++)
    packages = read_list(rp_path + '.inv')
    re_pkgs = list(re.escape(pkg) for pkg in packages)
    bulk_search = ('|'.join(re_pkgs))
    
    ### Loop Over Files Searching for Pkgs
    found_pkgs = set()
    for f in tqdm.tqdm(fs_list, desc='Bulk Scanning for ' + str(len(packages)) + ' Packages'):
        if re.findall(bulk_search, f.lower()):
            found_pkgs.add(f)

    ### Add Pkgs to Tar
    with tarfile.open(rp_path + '.tar', 'w') as tar:
        for f in tqdm.tqdm(found_pkgs, desc='Adding Packages to Restore Point'):
            tar.add(f, '/pac_cache/' + os.path.basename(f))

    ### Add Any Additional Dirs to RP
    if dir_list is 'nil':
        pass
    else:
        for dir in dir_list:
            cfs_list = search_fs(dir)
            with tarfile.open(rp_path + '.tar', 'a') as tar:
                for f in tqdm.tqdm(cfs_list, desc='Adding ' + dir + ' to Restore Point'):
                    tar.add(f)
        ### Compress Restore Point with Pigz
        print('Compressing Restore Point...')
        os.system('pigz ' + rp_path + '.tar -f')

    ### Finish
    print('Restore Point #' + str(rp_num) + ' Sucessfully Created!')

###############

def rollback_to_rp(rp_num):
    rp_path = base_dir + '/restore-points/rp' + str(rp_num)
    
    ### Unpack Restore Point
    if os.path.exists(rp_path + '.tar.gz'):
        print('Decompressing Restore Point....')
        ### Decompress Restore Point with Pigz
        os.system('pigz -d ' + rp_path + '.tar.gz -f')
    if os.path.exists(rp_path + '.tar'):
        ### Check if RP is Already Unpacked
        if os.path.exists(rp_path):
            shutil.rmtree(rp_path)
        ### Untar RP
        print('Unpacking Files from Restore Point Tar....')
        untar_dir(rp_path + '.tar')
    else:
        return print('Restore Point #' + rp_num + ' Was NOT FOUND!')

    ### Install Restore Point Packages
    os.system('sudo pacman -U ' + rp_path + '/pac_cache/* --needed')
    shutil.rmtree(rp_path + '/pac_cache')
    
    ### Check If There Are Any Files to Diff
    rp_fs = search_fs(rp_path)
    if not len(rp_fs) > 0:
        return print('Rollback to Restore Point #' + rp_num + ' Complete!')
    diff_yn = yn_frame('Do You Want to Checksum Diff Restore Point Files Against Your Current File System?')
    if diff_yn == False:
        return print('Skipping Diff! Restored Files are Now Availble in: ' + rp_path)

    ### Diff Files Unpacked From Restore Point
    elif diff_yn == True:
        import multiprocessing as mp
        ### Checksum Restore Point Files
        with mp.Pool(os.cpu_count()) as pool:
            rp_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs),
                            total=len(rp_fs), desc='Checksumming Restore Point Files'))
        ### Checksum Source Files
        sf_fs = set(path[len(rp_path):] for path in rp_fs)
        with mp.Pool(os.cpu_count()) as pool:
            sf_checksum = set(tqdm.tqdm(pool.imap(checksum_file, sf_fs),
                            total=len(sf_fs), desc='Checksumming Source Files'))
        ### Diff Restore Point Files Against Source
        rp_checksum = set(path[len(rp_path):] for path in rp_checksum)
        diff = sf_checksum.difference(rp_checksum)
        if len(diff) > 0:
            print('The Following Files Have Changed:')
            for f in diff:
                print(f)
        else: 
            print('No Files Have Been Changed!')

#######################
### Rollback to Date
###################

def rollback_to_date(date):
    ### Validate Date Fromat and Build New URL
    if not re.findall(r'([12]\d{3}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01]))', date):
        sys.exit('Invalid Date! Date Must be YYYY/MM/DD')
    archive_url=('https://archive.archlinux.org/repos/' + date + '/$repo/os/$arch')
    
    if re.findall(r'(https://archive\.archlinux\.org/repos/[12]\d{3}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\$repo/os/\$arch)'):
        uncomment_line()

###############

def unlock_rollback():
    uncomment_lines('/etc/pacman.conf')
    return

#######################
### Parse Args
###################

### Tests
#  custom_list = ['~/.ssh']
#  create_restore_point(2, custom_list)
#  create_restore_point(2)
#  rollback_to_date('1990/12/12')
#  rollback_to_rp(2)

