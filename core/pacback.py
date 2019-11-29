#! /usr/bin/env python3
#### A utility for marking and restoring stable arch packages
version = '1.1.2'
from python_scripts import *
import re, tqdm, argparse #, pyinquirer

def prError(text): print("\u001b[31;1m{}\033[00m" .format(text))
def prSuccess(text): print("\u001b[32;1m{}\033[00m" .format(text))
def prWorking(text): print("\033[33m{}\033[00m" .format(text))
def prWarning(text): print("\033[93m{}\033[00m" .format(text))
def prChanged(text): print("\u001b[35m{}\033[00m" .format(text))
def prRemoved(text): print("\033[31m{}\033[00m" .format(text))
def prAdded(text): print("\033[94m{}\033[00m" .format(text))

#######################
### Create Restore Point
###################
def create_restore_point(rp_num, dir_list):
    rp_path = base_dir + '/restore-points/rp' + str(rp_num).zfill(2)
    rp_files = set()
    found_pkgs = set()

    ###################################
    ### Find Pkgs for Restore Point ###
    ###################################
    print('Retrieving Current Stable Packages...')
    ### Get Current Pkg List and Scan the File System
    os.system("pacman -Q | sed -e 's/ /-/g' > /tmp/pacback_sys.meta")
    packages = read_list('/tmp/pacback_sys.meta')
    os.system("pacman -Q > /tmp/pacback_sys.meta")
    cache_list = search_fs('~/.cache', 'set')
    fs_list = set(search_fs('/var/cache/pacman', 'set') | {f for f in cache_list if f.endswith(".pkg.tar.xz")})

    ### Loop Over Files Searching for Pkgs
    prWorking('Bulk Scanning for ' + str(len(packages)) + ' Packages...')
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in packages))) 
    for f in fs_list:
        if re.findall(bulk_search, f.lower()):
            found_pkgs.add(f + '<>/pac_cache/' + os.path.basename(f))

    ################################
    ### Find Custom Files for RP ###
    ################################
    if not len(dir_list) == 0:
        dir_gb = sum({os.path.getsize(path) for path in dir_list})
        ### Recursivly Add Files From Each Base Dir
        for path in dir_list:
            l = search_fs(path, 'set')
            for x in l:
                rp_files.add(x +'<>'+ x)
    else:
        dir_gb = 0

    ###########################
    ### Build Restore Point ###
    ###########################
    with tarfile.open(rp_path + '.tar', 'w') as tar:
        #  return print(rp_files)
        tar_files = found_pkgs.union(rp_files)
        for f in tqdm.tqdm(tar_files, desc='Building Restore Point'):
            s = f.split('<>')
            tar.add(s[0], s[1])

    ### Compress Restore Point if Files Added Larger Than 1GB
    if dir_gb > 1073741824:
        prWorking('Compressing Restore Point...')
        ### Check to See if pigz is Installed
        if any(re.findall(line.lower(), 'pigz') for line in packages):
            os.system('pigz ' + rp_path + '.tar -f')
        else:
            gz_c(rp_path, rm=True)

    ###############################
    ### Generate Meta Data File ###
    ###############################
    import datetime as dt
    meta_list = ['====== Pacback RP #'+ str(rp_num).zfill(2) +' ======',
                 'Packages Installed: ' + str(len(packages)),
                 'Packages in RP: ' + str(len(found_pkgs)),
                 'Date Created: ' + dt.datetime.now().strftime("%Y/%m/%d"),
                 'Pacback Version: ' + version,
                 ]
    if not len(dir_list) == 0:
        dir_meta = ['Dirs File Count: '+ str(len(rp_files)),
                    'Dirs Total GB: '+ str(round(dir_gb/1073741824, 4)),
                    '',
                    '========= Dir List =========']
        for dir in dir_list:
            dir_meta.append(dir)
            meta_list.extend(dir_meta)

    meta_list.append('')
    meta_list.append('======= Pacman List ========')
    for pkg in read_list('/tmp/pacback_sys.meta'):
        meta_list.append(pkg)
    export_list(rp_path + '.meta', meta_list)

    prSuccess('Restore Point #' + str(rp_num).zfill(2) + ' Successfully Created!')


#######################
### Rollback to RP
###################
def rollback_to_rp(rp_num):
    rp_path = base_dir + '/restore-points/rp' + str(rp_num).zfill(2)

    ############################
    ### Unpack Restore Point ###
    ############################
    if os.path.exists(rp_path + '.tar.gz'):
        prWorking('Decompressing Restore Point....')
        if any(re.findall(line.lower(), 'pigz') for line in meta):
            ### Decompress Restore Point with Pigz if Found
            os.system('pigz -d ' + rp_path + '.tar.gz -f')
        else:
            gz_d(rp_path + '.tar.gz')

    if os.path.exists(rp_path + '.tar'):
        ### Check if RP is Already Unpacked
        if os.path.exists(rp_path):
            shutil.rmtree(rp_path)
        prWorking('Unpacking Files from Restore Point Tar....')
        untar_dir(rp_path + '.tar')
    else:
        return prError('Restore Point #' + rp_num + ' Was NOT FOUND!')

    ######################################
    ### Install Restore Point Packages ###
    ######################################
    os.system('sudo pacman -U ' + str(rp_path).zfill(2) + '/pac_cache/*')
    shutil.rmtree(rp_path + '/pac_cache')
    
    ### Read RP Meta Data
    if os.path.exists(rp_path + '.meta'):
        meta = read_list(rp_path + '.meta')
        meta_dirs = read_between('========= Dir List =========','======= Pacman List ========', meta)[:-1]
        old_pkg = read_between('======= Pacman List ========','<Endless>', meta) 
        old_pkg = {pkg.split(' ')[0] for pkg in old_pkg}
    else:
        prError('Restore Point #' + str(rp_num).zfill(2) + ' Meta Data Was NOT FOUND!')
        return prError('Skipping Advanced Features!')
    
    ### Compare Current Pkg List
    os.system("pacman -Q > /tmp/pacback_sys.meta")
    current_pkg = read_list("/tmp/pacback_sys.meta")
    current_pkg = {pkg.split(' ')[0] for pkg in current_pkg}
    added_pkg = current_pkg.difference(old_pkg)
    
    ### Uninstall Old Packages?
    if len(added_pkg) > 0:
        prWarning('The Following Packages Are Installed But Are NOT Present in Restore Point #' + str(rp_num).zfill(2) + ':')
        for pkg in added_pkg:
            prAdded(pkg)
        if yn_frame('Do You Want to Remove These Packages?') == True:
            os.system('sudo pacman -R ' + ' '.join(added_pkg))

    if not len(meta_dirs) > 0:
        shutil.rmtree(rp_path)
        return prSuccess('Rollback to Restore Point #' + rp_num + ' Complete!')

    ##############################
    ### Diff Restore Files ###
    ##############################
    diff_yn = yn_frame('Do You Want to Checksum Diff Restore Point Files Against Your Current File System?')
    if diff_yn == False:
        print('Skipping Diff!')

    ### Diff Files Unpacked From Restore Point
    elif diff_yn == True:
        import multiprocessing as mp
        rp_fs = search_fs(rp_path)
        rp_fs_trim = set(path[len(rp_path):] for path in search_fs(rp_path))
        
        ### Checksum Restore Point Files
        with mp.Pool(os.cpu_count()) as pool:
            rp_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs),
                            total=len(rp_fs), desc='Checksumming Restore Point Files'))
            sf_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs_trim),
                            total=len(rp_fs_trim), desc='Checksumming Source Files'))

        ### Diff Restore Point Files Against Source
        rp_csum_trim = set(path[len(rp_path):] for path in rp_checksum)
        rp_diff = sf_checksum.difference(rp_csum_trim)
        
        ### Add Missing Files to Diffrent Set
        diff_removed = set()
        diff_changed = set()
        for csum in rp_diff:
            if re.findall('FILE MISSING', csum):
                diff_removed.add(csum)
            else:
                diff_changed.add(csum.split(' : ')[0] + ' : FILE CHANGED!')
        
        ### Check for Added Files
        src_fs = set()
        
        for x in meta_dirs:
            for l in search_fs(x):
                src_fs.add(l)
        diff_new = src_fs.difference(rp_fs_trim)

        ### Print Changed Files For User
        if len(diff_changed) + len(diff_new) + len(diff_removed) > 0:
            print('The Following Files Have Changed:')
            for f in diff_changed:
                prChanged(f)
            for f in diff_removed:
                prRemoved(f)
            for f in diff_new:
                prAdded(f + ' : NEW FILE!')
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


#######################
### Unlock Mirrorlist
###################
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
        return prError('Pacback Does NOT Have an Active Date Lock!')

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
parser.add_argument("-rb", "--rollback", metavar=('RP# or YYYY/MM/DD'), help="Rollback to a previously generated restore point or to an archive date.")
parser.add_argument("-c", "--create_rp", metavar=('RP#'), help="Generate a pacback restore point. Takes a restore point # as an argument.")
parser.add_argument("-d", "--add_dir", nargs='*', metavar=('/PATH'), help="Add any custom directories to your restore point during --gen_rp.")
parser.add_argument("-ur", "--unlock_rollback", action='store_true', help="Release any date rollback locks on /etc/pacman.d/mirrorlist. No argument is needed.")
args = parser.parse_args()

if args.rollback:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.rollback):
        rollback_to_rp(args.rollback)
    elif re.findall(r'^(?:[0-9]{2})?[0-9]{2}/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}$', args.rollback):
        rollback_to_date(args.rollback)
    else:
        prError('No Usable Argument! Rollback Arg Must be a Restore Point # or a Date.')

elif args.create_rp:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.create_rp):
        if args.add_dir:
            create_restore_point(args.create_rp, args.add_dir)
        else:
            create_restore_point(args.create_rp, dir_list=list())

    else:
        prError('No Usable Argument! Rollback # Must be an INT.')

elif args.unlock_rollback:
    unlock_rollback()

else:
    prError('No Usable Argument Given!')
