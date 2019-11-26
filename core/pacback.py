#! /usr/bin/env python3
#### A utility for marking and restoring stable arch packages
version = '1.0.0'
from python_scripts import *
import re, tqdm, argparse #, pyinquirer

#######################
### Restore Points
###################

def create_restore_point(rp_num, dir_list):
    ### Get Current Pkg List and Scan the File System
    rp_path = base_dir + '/restore-points/rp' + str(rp_num).zfill(2)
    print('Retrieving Current Stable Packages...')
    os.system("pacman -Q | sed -e 's/ /-/g' > " + rp_path + '.meta')
    packages = read_list(rp_path + '.meta')
    cache_list = search_fs('~/.cache', 'set')
    fs_list = set(search_fs('/var/cache/pacman', 'set') | {f for f in cache_list if f.endswith(".pkg.tar.xz")})

    ### Each Pkg Name Needs to be Escaped (like c++)
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
    if len(dir_list) == 0:
        pass
    else:
        files = set()
        for path in dir_list:
            l = search_fs(path, 'set')
            for x in l:
                files.add(x)
        
        with tarfile.open(rp_path + '.tar', 'a') as tar:
            for f in tqdm.tqdm(files, desc='Adding Files to Restore Point'):
                tar.add(f)
        
        ### Compress Restore Point with Pigz if Larger Than 1GB
        dir_gb = sum({os.path.getsize(path) for path in files})
        if dir_gb > 1073741824:
            print('Compressing Restore Point...')
            os.system('pigz ' + rp_path + '.tar -f')

    ### Export Meta Data File
    import datetime as dt
    meta_list = ['====== Pacback RP #'+ str(rp_num).zfill(2) +' ======',
                 'Packages Installed: ' + str(len(packages)),
                 'Packages in RP: ' + str(len(found_pkgs)),
                 'Date Created: ' + dt.datetime.now().strftime("%Y/%m/%d"),
                 'Pacback Version: ' + version,
                 '',]
    if len(dir_list) == 0:
        pass
    else:
        meta_list.append('========= Dir List =========')
        meta_list.append('File Count: '+ str(len(files)))
        meta_list.append('Total GB: '+ str(round(dir_gb/1073741824, 3)))
        for dir in dir_list:
            meta_list.append(dir)
        meta_list.append('')

    meta_list.append('======= Pacman List ========')
    for pkg in packages:
        meta_list.append(pkg)
    export_list(rp_path + '.meta', meta_list)
    print('Restore Point #' + str(rp_num).zfill(2) + ' Successfully Created!')

###############

def rollback_to_rp(rp_num):
    rp_path = base_dir + '/restore-points/rp' + str(rp_num).zfill(2)
    
    ### Decompress Restore Point with Pigz
    if os.path.exists(rp_path + '.tar.gz'):
        print('Decompressing Restore Point....')
        os.system('pigz -d ' + rp_path + '.tar.gz -f')
    
    ### Unpack Restore Point
    if os.path.exists(rp_path + '.tar'):
        ### Check if RP is Already Unpacked
        if os.path.exists(rp_path):
            shutil.rmtree(rp_path)
        print('Unpacking Files from Restore Point Tar....')
        untar_dir(rp_path + '.tar')
    
    else:
        return print('Restore Point #' + rp_num + ' Was NOT FOUND!')

    ### Install Restore Point Packages
    os.system('sudo pacman -U ' + str(rp_path).zfill(2) + '/pac_cache/* --needed')
    shutil.rmtree(rp_path + '/pac_cache')
    
    ### Check If There Are Any Files to Diff
    rp_fs = search_fs(rp_path)
    if not len(rp_fs) > 0:
        return print('Rollback to Restore Point #' + rp_num + ' Complete!')
    diff_yn = yn_frame('Do You Want to Checksum Diff Restore Point Files Against Your Current File System?')
    if diff_yn == False:
        print('Skipping Diff! Restored Files are Now Available in: ' + rp_path)

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
        return print('Invalid Date! Date Must be YYYY/MM/DD Format.')
    
    ### Backup Mirrorlist
    if len(read_list('/etc/pacman.d/mirrorlist')) > 1:
        os.system('sudo cp /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist.pacback')
    os.system("echo 'Server=https://archive.archlinux.org/repos/" + date + "/$repo/os/$arch' | sudo tee /etc/pacman.d/mirrorlist >/dev/null")
    ### Run Pacman Update
    os.system('sudo pacman -Syyuu') 
    
###############

def unlock_rollback():
    ### Check if mirrorlist is locked
    if len(read_list('/etc/pacman.d/mirrorlist')) == 1:
        if os.path.exists('/etc/pacman.d/mirrolist.pacback'):
            list_fetch = yn_frame('Pacback Can\'t Find Your Backup Mirrorlist! Do You Want to Fetch a New US HTTPS Mirrorlist?')
            if list_fetch == True:
                os.system("curl -s 'https://www.archlinux.org/mirrorlist/?country=US&protocol=https&use_mirror_status=on' | sed -e 's/^#Server/Server/' -e '/^#/d' | sudo tee /etc/pacman.d/mirrorlist.pacback >/dev/null")
            else:
                sys.exit('Critical Error! Please Manually Replace Your Mirrorlist!')
        os.system('sudo cp /etc/pacman.d/mirrorlist.pacback /etc/pacman.d/mirrorlist')
    else:
        return print('Pacback Does NOT Have an Active Date Lock!')
    
    ### Update?
    update = yn_frame('Do You Want to Update Your System Now?')
    if update == True:
        os.system('sudo pacman -Syu') 
    if update == False:
        return print('Skipping Update!')

#######################
### Parse Args
###################
base_dir = os.path.dirname(os.path.realpath(__file__))[:-5]

parser = argparse.ArgumentParser(description="A reliable rollback utility for marking and restoring custom save points in Arch Linux.")
parser.add_argument("-rb", "--rollback", metavar=('RP# or YYYY/MM/DD'), help="Rollback to a previously generated restore point or to a date.")
parser.add_argument("-c", "--create_rp", metavar=('INT'), help="Generate a pacback restore point. Takes a restore point # as an argument.")
parser.add_argument("-d", "--add_dir", nargs='*', metavar=('/PATH'), help="Add any custom directories to your restore point during --gen_rp.")
parser.add_argument("-ur", "--unlock_rollback", action='store_true', help="Release any date rollback locks on /etc/pacman.d/mirrorlist. No argument is needed.")
args = parser.parse_args()

if args.rollback:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.rollback):
        rollback_to_rp(args.rollback)
    elif re.findall(r'^(?:[0-9]{2})?[0-9]{2}/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}$', args.rollback):
        rollback_to_date(args.rollback)
    else:
        print('No Usable Argument! Rollback Arg Must be a Restore Point # or a Date.')

elif args.create_rp:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.create_rp):
        if args.add_dir:
            create_restore_point(args.create_rp, args.add_dir)
        else:
            create_restore_point(args.create_rp, dir_list=list())

    else:
        print('No Usable Argument! Rollback # Must be an INT.')

elif args.unlock_rollback:
    unlock_rollback()
    
else:
    print('No Usable Argument Given!')
