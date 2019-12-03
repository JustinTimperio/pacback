#! /usr/bin/env python3
#### A utility for marking and restoring stable arch packages
version = '1.3.2'
from python_scripts import *
import tqdm, argparse

def prError(text): print("\u001b[31;1m{}\033[00m" .format(text))
def prSuccess(text): print("\u001b[32;1m{}\033[00m" .format(text))
def prWorking(text): print("\033[33m{}\033[00m" .format(text))
def prWarning(text): print("\033[93m{}\033[00m" .format(text))
def prChanged(text): print("\u001b[35m{}\033[00m" .format(text))
def prRemoved(text): print("\033[31m{}\033[00m" .format(text))
def prAdded(text): print("\033[94m{}\033[00m" .format(text))

#<#><#><#><#><#><#>#<#>#<#
#+# Create Restore Point
#<#><#><#><#><#><#>#<#>#<#

def create_restore_point(rp_num, rp_full, dir_list):
    rp_path = base_dir + '/restore-points/rp' + str(rp_num).zfill(2)
    if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz') or os.path.exists(rp_path + '.meta'):
        prWarning('Restore Point #' + str(rp_num).zfill(2) + ' Already Exists!') 
        if yn_frame('Do You Want to Overwrite It?') == True:
            rm_file(rp_path + '.tar', sudo=True)
            rm_file(rp_path + '.tar.gz', sudo=True)
            rm_file(rp_path + '.meta', sudo=True)

    ###################################
    ### Find Pkgs for Restore Point ###
    ###################################
    if rp_full == True:
        rp_files = set()
        found_pkgs = set()

        prWorking('Retrieving Current Packages...')
        os.system("pacman -Q | sed -e 's/ /-/g' > /tmp/pacback_sys.meta")
        packages = read_list('/tmp/pacback_sys.meta')

        ### Build System File Lists
        cache_list = search_fs('~/.cache', 'set')
        fs_list = set(search_fs('/var/cache/pacman', 'set') | {f for f in cache_list if f.endswith(".pkg.tar.xz")})
        ### Loop Over Files Searching for Pkgs
        prWorking('Bulk Scanning for ' + str(len(packages)) + ' Packages...')
        bulk_search = ('|'.join(list(re.escape(pkg) for pkg in packages))) ### Packages like g++ need to be escaped
        for f in fs_list:
            if re.findall(bulk_search, f.lower()):
                found_pkgs.add(f + '<>/pac_cache/' + os.path.basename(f))
        pac_size = 0
        for f in found_pkgs:
            pac_size += os.path.getsize(f.split('<>')[0])

        ################################
        ### Find Custom Files for RP ###
        ################################
        dir_size = 0
        if len(dir_list) > 0:
            for d in dir_list:
                for f in search_fs(d):
                    dir_size += os.path.getsize(f)

            for path in dir_list: ### Recursivly Add Files From Each Base Dir
                l = search_fs(path, 'set')
                for x in l:
                    rp_files.add(x +'<>'+ x)

        ###########################
        ### Build Restore Point ###
        ###########################
        with tarfile.open(rp_path + '.tar', 'w') as tar:
            tar_files = found_pkgs.union(rp_files) ### Combine Packages and Dirs
            for f in tqdm.tqdm(tar_files, desc='Building Restore Point'):
                s = f.split('<>')
                tar.add(s[0], s[1]) ### This Parses List of Files in the Format '/dir/in/system/<>/dir/in/tar'

        ### Compress Restore Point if Files Added Larger Than 1GB
        if dir_size > 1073741824:
            prWorking('Compressing Restore Point...')
            ### Check to See if pigz is Installed
            if any(re.findall('pigz', line.lower()) for line in packages):
                os.system('pigz ' + rp_path + '.tar -f')
            else:
                gz_c(rp_path + '.tar', rm=True)
    
    elif rp_full == False:
        print('Building Light Restore Point...')
        found_pkgs = set()
        pac_size = 0

    ###############################
    ### Generate Meta Data File ###
    ###############################
    import datetime as dt
    os.system("pacman -Q > /tmp/pacback_sys.meta")
    packages = read_list('/tmp/pacback_sys.meta')
    meta_list = ['====== Pacback RP #'+ str(rp_num).zfill(2) +' ======',
                 'Date Created: ' + dt.datetime.now().strftime("%Y/%m/%d"),
                 'Packages Installed: ' + str(len(packages)),
                 'Packages in RP: ' + str(len(found_pkgs)),
                 'Size of Packages in RP: ' + str(convert_size(pac_size)),
                 'Pacback Version: ' + version]
    if not len(dir_list) == 0:
        dir_meta = ['Dirs File Count: '+ str(len(rp_files)),
                    'Dirs Total Size: '+ str(convert_size(dir_size)),
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


#<#><#><#><#><#><#>#<#>#<#
#+# Rollback to RP
#<#><#><#><#><#><#>#<#>#<#

def rollback_to_rp(rp_num):
    rp_path = base_dir + '/restore-points/rp' + str(rp_num).zfill(2)
    os.system("pacman -Q > /tmp/pacback_sys.meta")
    current_pkg = read_list("/tmp/pacback_sys.meta")
    if os.path.exists(rp_path + '.tar') or os.path.exists(rp_path + '.tar.gz'):
        full_rp = True
    else:
        full_rp = False

    ### Read RP Meta Data
    if os.path.exists(rp_path + '.meta'):
        meta_exists = True
        meta = read_list(rp_path + '.meta')
        meta_dirs = read_between('========= Dir List =========','======= Pacman List ========', meta)[:-1]
        meta_old_pkg = read_between('======= Pacman List ========','<Endless>', meta)
        meta_old_pkg_strp = {pkg.split(' ')[0] for pkg in meta_old_pkg} ### Strip Version
        current_pkg_strp = {pkg.split(' ')[0] for pkg in current_pkg} ### Strip Version
        added_pkg = current_pkg_strp.difference(meta_old_pkg_strp)
    else:
        meta_exists = False
        added_pkg = None
        meta_old_pkg = None

    ### Branch Based on Existing Files
    if meta_exists == False and full_rp == False:
        return prError('Restore Point #' + str(rp_num).zfill(2) + ' Was NOT FOUND!')

    elif full_rp == True:
        ##########################
        ### Full Restore Point ###
        ##########################
        if os.path.exists(rp_path + '.tar.gz'):
            prWorking('Decompressing Restore Point....')
            if any(re.findall('pigz', line.lower()) for line in packages):
                os.system('pigz -d ' + rp_path + '.tar.gz -f') ### Decompress With pigz If Found
            else:
                gz_d(rp_path + '.tar.gz')

        if os.path.exists(rp_path + '.tar'):
            ### Clean RP is Already Unpacked
            if os.path.exists(rp_path):
                shutil.rmtree(rp_path)
            prWorking('Unpacking Files from Restore Point Tar....')
            untar_dir(rp_path + '.tar')

        ### Install Restore Point Packages
        os.system('sudo pacman --needed -U ' + str(rp_path).zfill(2) + '/pac_cache/*')
        shutil.rmtree(rp_path + '/pac_cache')

        if meta_exists == False:
            prError('Restore Point #' + str(rp_num).zfill(2) + ' Meta Data Was NOT FOUND!')
            return prError('Skipping Advanced Features!')

    elif meta_exists == True and full_rp == False:
        ###########################
        ### Light Restore Point ###
        ###########################
        prWorking('Bulk Scanning for ' + str(len(meta_old_pkg)) + ' Packages...')
        found_pkgs = set()

        ### Copied Mainly From Build RP Code
        search_list = {s.strip().replace(' ', '-') for s in meta_old_pkg}
        cache_list = search_fs('~/.cache', 'set')
        fs_list = set(search_fs('/var/cache/pacman', 'set') | {f for f in cache_list if f.endswith(".pkg.tar.xz")})
        bulk_search = ('|'.join(list(re.escape(pkg) for pkg in search_list))) ### Packages like g++ need to be escaped
        for f in fs_list:
            if re.findall(bulk_search, f.lower()):
                found_pkgs.add(f)

        ### Pass Comparison if All Packages Found
        if len(found_pkgs) == len(current_pkg):
            prSuccess('All Packages Found In Your Local File System!')
            os.system('sudo pacman --needed -U ' + ' '.join(found_pkgs))
       
        ### Show User Missing Packages
        elif len(found_pkgs) < len(current_pkg):
            pkg_split = {pkg.split('/')[-1] for pkg in found_pkgs}
            pkg_split = {'-'.join(pkg.split('-')[:-1]) for pkg in pkg_split}
            missing_pkg = search_list.difference(pkg_split)
            prWarning('Pacback Only Found '+ str(len(found_pkgs)) + ' Old Versions of ' + str(len(current_pkg)) + ' Packages Currently Installed')
            prWarning('Couldn\'t Find The Following Package Versions:')
            for pkg in missing_pkg:
                prError(pkg)
            if yn_frame('Do You Want To Continue Anyway?') == True:
                os.system('sudo pacman --needed -U ' + ' '.join(found_pkgs))
            else:
                return

    ### Uninstall New Packages? Executes When Meta is True and When Packages Have Been Added
    if len(added_pkg) > 0:
        prWarning('The Following Packages Are Installed But Are NOT Present in Restore Point #' + str(rp_num).zfill(2) + ':')
        for pkg in added_pkg:
            prAdded(pkg)
        if yn_frame('Do You Want to Remove These Packages From Your System?') == True:
            os.system('sudo pacman -R ' + ' '.join(added_pkg))

    ##########################
    ### Diff Restore Files ###
    ##########################
    if not len(meta_dirs) > 0:
        if full_rp == True:
            shutil.rmtree(rp_path)
        return prSuccess('Rollback to Restore Point #' + str(rp_num).zfill(2) + ' Complete!')

    else:
        diff_yn = yn_frame('Do You Want to Checksum Diff Restore Point Files Against Your Current File System?')
        if diff_yn == False:
            print('Skipping Diff!')
            pass

        elif diff_yn == True:
            import multiprocessing as mp
            rp_fs = search_fs(rp_path)
            rp_fs_trim = set(path[len(rp_path):] for path in search_fs(rp_path))

            ### Checksum Restore Point Files with a MultiProcessing Pool
            with mp.Pool(os.cpu_count()) as pool:
                rp_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs),
                                total=len(rp_fs), desc='Checksumming Restore Point Files'))
                sf_checksum = set(tqdm.tqdm(pool.imap(checksum_file, rp_fs_trim),
                                total=len(rp_fs_trim), desc='Checksumming Source Files'))

            ### Compare Checksums For Files That Exist
            rp_csum_trim = set(path[len(rp_path):] for path in rp_checksum)
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
            if len(diff_changed) + len(diff_new) + len(diff_removed) > 0:
                print('The Following Files Have Changed:')
                for f in diff_changed:
                    prChanged(f)
                for f in diff_removed:
                    prRemoved(f)
                for f in diff_new:
                    prAdded(f + ' : NEW FILE!')
            else:
                shutil.rmtree(rp_path)
                return print('No Files Have Been Changed!')

    #######################
    ### Overwrite Files ###
    #######################
    if diff_yn == False:
        prWarning('YOU HAVE NOT CHECKSUMED THE RESTORE POINT! OVERWRITING ALL FILES CAN BE EXTREAMLY DANGOURS!')
        ow = yn_frame('Do You Still Want to Continue and Restore ALL Files In the Restore Point?')
        if ow == False:
            return print('Skipping Automatic File Restore! Restore Point Files Are Unpacked in ' + rp_path)
        
        elif ow == True: 
            print('Starting Full File Restore! Please Be Patient As All Files are Overwritten...')
            rp_fs = search_fs(rp_path)
            for f in rp_fs:
                os.system('sudo mkdir -p ' + escape_bash('/'.join(f.split('/')[:-1])) + ' && sudo cp -af ' + escape_bash(f) + ' ' + escape_bash(f[len(rp_path):]))
        
    elif diff_yn == True:
        ow = yn_frame('Do You Want to Automaticly Restore Changed and Missing Files?')
        if ow == False:
            return print('Skipping Automatic Restore! Restore Point Files Are Unpacked in ' + rp_path)
        
        if ow == True:
            if len(diff_changed) > 0:
                if yn_frame('Do You Want to Overwrite Files That Have Been CHANGED?') == True:
                    for f in diff_changed:
                        fs = (f.split(' : ')[0])
                        os.system('sudo cp -af ' + escape_bash(rp_path + fs) + ' ' + escape_bash(fs))
            
            if len(diff_removed) > 0:
                if yn_frame('Do You Want to Add Files That Have Been REMOVED?') == True:
                    for f in diff_removed:
                        fs = (f.split(' : ')[0])
                        os.system('sudo mkdir -p ' + escape_bash('/'.join(fs.split('/')[:-1])) + ' && sudo cp -af ' + escape_bash(rp_path + fs) + ' ' + escape_bash(fs))
            
            if len(diff_new) > 0:
                if yn_frame('Do You Want to Remove Files That Have Beend ADDED?') == True:
                    for f in diff_new:
                        fs = (f.split(' : ')[0])
                        os.system('sudo rm ' + fs)
    shutil.rmtree(rp_path)
    prSuccess('File Restore Complete!')


#<#><#><#><#><#><#>#<#>#<#
#+# Rollback to Date
#<#><#><#><#><#><#>#<#>#<#

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


#<#><#><#><#><#><#>#<#>#<#
#+# Unlock Mirrorlist
#<#><#><#><#><#><#>#<#>#<#

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


#<#><#><#><#><#><#>#<#>#<#
#+# CLI Args
#<#><#><#><#><#><#>#<#>#<#

parser = argparse.ArgumentParser(description="A reliable rollback utility for marking and restoring custom save points in Arch Linux.")
parser.add_argument("-sb", "--snapback", action='store_true', help="Rollback packages to the version state stored before that last pacback upgrade.")
parser.add_argument("-rb", "--rollback", metavar=('RP# or YYYY/MM/DD'), help="Rollback to a previously generated restore point or to an archive date.")
parser.add_argument("-Syu", "--upgrade", action='store_true', help="Create a light restore point and run a full system upgrade. Use snapback to restore this version state.")
parser.add_argument("-c", "--create_rp", metavar=('RP#'), help="Generate a pacback restore point. Takes a restore point # as an argument.")
parser.add_argument("-f", "--full_rp", action='store_true', help="Generate a pacback full restore point.")
parser.add_argument("-d", "--add_dir", nargs='*', default=[], metavar=('/PATH'), help="Add any custom directories to your restore point during a `--create_rp AND --full_rp`.")
parser.add_argument("-u", "--unlock_rollback", action='store_true', help="Release any date rollback locks on /etc/pacman.d/mirrorlist. No argument is needed.")
parser.add_argument("-i", "--info", metavar=('RP#'), help="Print information about a retore point.")
args = parser.parse_args()

#<#><#><#><#><#><#>#<#>#<#
#+# Args Flow Control
#<#><#><#><#><#><#>#<#>#<#
base_dir = os.path.dirname(os.path.realpath(__file__))[:-5]

if args.info:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.info):
        rp = base_dir + '/restore-points/rp' + str(args.info).zfill(2)
        if os.path.exists(rp + '.meta'):
            meta = read_list(rp + '.meta')
            meta = read_between('Pacback RP', 'Pacman List', meta, re_flag=True)
            for s in meta[:-1]:
                print(s)
        
        elif os.path.exists(rp + '.tar') or os.path.exists(rp + '.tar.gz'):
            prError('No Meta Exists For This Restore Point!')
        
        else:
            prError('No Restore Point #' + str(args.info).zfill(2) + ' Was NOT Found!')
    else:
        prError('No Usable Argument! Rollback Arg Must be a Restore Point # or a Date.')

elif args.upgrade:
    create_restore_point('00', args.full_rp, args.add_dir)
    os.system('sudo pacman -Syu')

elif args.snapback:
    if os.path.exists(base_dir + '/restore-points/rp00.meta'):
        rollback_to_rp('00')
    else:
        prError('No Snapback Found!')

elif args.rollback:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.rollback):
        rollback_to_rp(args.rollback)
    elif re.findall(r'^(?:[0-9]{2})?[0-9]{2}/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}$', args.rollback):
        rollback_to_date(args.rollback)
    else:
        prError('No Usable Argument! Rollback Arg Must be a Restore Point # or a Date.')

elif args.create_rp:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.create_rp):
        if args.full_rp:
            create_restore_point(args.create_rp, args.full_rp, args.add_dir)
        else:
            create_restore_point(args.create_rp, args.full_rp, args.add_dir)
    else:
        prError('You Are Missing Arguments! Refer to Documentation for Help.')

elif args.unlock_rollback:
    unlock_rollback()

else:
    prError('No Usable Argument Given!')
