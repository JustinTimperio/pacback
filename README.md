# Pacback - Alpha 1.4
**TLDR: This projects ultimate goal is to provide flexible, portable, and resilient downgrades while still maintaining a slim profile and fast performance.** 


## Abstract:
I love Arch Linux and rolling-release distros. Being at the head of Linux kernel and application development means access to the latest features and bug fixes. This also often means dealing with the latest bugs. While I don't run into major bugs often, when they happen, they cripple my productivity.  Manually reversing individual packages is generally a slow and manual process. While some tools exist, none meet my needs. In particular, support for rolling back AUR packages is extremely lacking.  

## Core Feature:

- Instant Rollback of -Syu Upgrades
- The Ability to Track All Additions, Removals, and Upgrades Made to the System
- Native AUR Support
- Automatically Save and Restore App Config Files
- FailProof Rollbacks Even When Caches Are Deleted
- Multi-Threaded File Checksumming and Restore Point Compression
- Rollback to Arch Archive Dates

-------------------

## Pacback-CLI Commands and Flags:
Pacback offers a few core commands that streamline the process of creating and restoring versions. The CLI is designed to be dead simple and provide detailed feedback and user control.

-sb, --snapback | Rollback packages to the version state stored before that last pacback upgrade.\
**Example: `pacback --snapback`**\
-rb, --rollback | Rollback to a previously generated restore point or to an archive date.\
**Example: `pacback --rollback 1` or `pacback --rollback 2019/08/14`**\
-Syu, --upgrade | Create a light restore point and run a full system upgrade. Use snapback to restore this version state.\
**Example: `pacback -Syu`**\
-c, --create_rp | Generate a pacback restore point. Takes a restore point # as an argument.\
**Example: `pacback -c 1`**\
-f, --full_rp | Generate a pacback full restore point.\
**Example: `pacback -f -c 1`**\
-pkg, --rollback_pkgs | - Rollback a list of packages looking for old versions on the system.\
**Example: `pacback -pkg package_1 package_2 package_3`**\
-d, --add_dir | Add any custom directories to your restore point during a `--create_rp AND --full_rp`.\
**Example: `pacback -f -c 1 -d /dir1/to/add /dir2/to/add /dir3/to/add`**\
-nc, --no_confirm | Skip asking user questions during RP creation. Will answer yes to all.\
**Example: `pacback -nc -c 1`**\
-u, --unlock_rollback -| Release any date rollback locks on /etc/pacman.d/mirrorlist. No argument is needed.\
**Example: `pacback --unlock_rollback`**\
-i, --info | Print information about a retore point.\
**Example: `pacback --info 1`**


------------------

## Install Instructions:
Where ever you clone the repository will act as the base directory for Restore Points.
1. `git clone --recurse-submodules https://github.com/JustinTimperio/pacback.git`
2. `pacman -S python-tqdm`
3. `sudo ln -s /dir/to/pacback/core/pacback.py /usr/bin/pacback`

------------------

## Pacback Usage Examples:
While there are only a few CLI commands, they can be used in a wide variety of complex restoration tasks. Below are some examples of how to use and deploy Pacback in your systems.

### Using pacback -Syu Instead of pacman -Syu
One of the problems with rolling releases is you never know when a problem might occur. It may be months before you run into an issue at which point, you will need to scramble to figure out when your system was stable last. Pacback offers a specialized command that helps solve this issue. Pacback will create a Light Restore Point numbered `00` before every `pacback -Syu` system upgrade. If you run into any issues with the upgrade, simply use `pacback --snapback` to instantly downgrade only the packages you upgraded and remove and additions.

1. Deploy a system upgrade with: `pacback -Syu`
2. Instantly rollback this update using: `pacback -sb`

![Pacback Snapback](https://i.imgur.com/AX92cfz.gif)

### Simple System Maintenance for Developers
If you are like me you love to install and test the latest projects the community is working on. The downside of doing this is the slow build-up of packages as you try to remember why that you ever installed a set of packages. To avoid this you can use pacback  to create a restore point then install a bunch of experimental packages you only plan on keeping for a few days. After you're done, simply roll back to the Restore Point and all the packages you installed will be removed. 

In the following example, I will install Haskell which is a dependency nightmare. After installing it we will show how to quickly uninstall all your changes. 
1. First, we create a restore point with: `pacback -c 3`
2. Next we install Haskell packages with: `pacman -S stack` 
3. Once you are ready to remove Haskell use: `pacback -rb 3`

![Pacback Haskell](https://imgur.com/PzUznWZ.gif)

### Backup Version Sensitive Application Data
In some cases, config files many need to be modified when updating packages. In other cases, you may want to backup application data before deploying an upgrade incase of error or corruption. Pacback makes it extremely simple to store files like this and will automatically compare files you have stored against your current file system. Once checksumming is complete you can selectively overwrite each subsection of file type: Changed, Added, and Removed.

In this example we pack up an Apache websever and Postgresql database.
1. `pacback -c 1 -f -d /var/www /etc/httpd /var/lib/postgres/data`
2. `pacback -Syu`
3. `pacback -rb 1` 

![Pacback Saving App Data](https://imgur.com/Ag0NROG.gif)

### Rollback a List of Packages 
Most issues with an update stem from a single package or a set of related package. Pacback allows you to selectively rollback a list of packages using `pacback -pkg package_1 package_2 package_3`. Packback searches your file system looking for all versions assoicated with each package package name. When searching for a package, be as spesific as possible. Since generic names like 'linux' or 'gcc' apper in many package names, the search may be cluttered with unrelated packages.

In this example we selectively rollback 2 packages.
1. `pacback -pkg typescript electron4`

![Pacback Rolling Back a List of Packages](https://imgur.com/Rhy6iDn.gif)

### Rolling Back to an Archive Date
Another popular way to rollback package versions is to use the Arch Linux Archives to pull packages with directly with pacman. Pacback automates this entire process with the `pacback -rb` command. To rollback to a specific date, give `-rb` a date in YYYY/MM/DD format and Pacback will automatically save your mirrorlist, point a new mirrorlist to an archive URL, then run a full system downgrade. When every you are ready to jump back to the head, run `pacback -u` and Pacback with automatically retore your old mirrorlist. In the event that you destroy this backup, Pacback can automatically fetch a new HTTP US mirrorlist for the system.

1. `pacback -rb 2019/10/18`

![Pacback Rolling Back a Archive Date](https://imgur.com/nBaYYCB.gif)

------------------------

## Pacback's Design:
Pacback is written entirely in python3 and attempts to use as few pip packages as possible (currently only tqdm is needed). Pacback offers a number of utilities that primarily use two core restore methods: **Full and Light Restore Points.** These two types of restore points offer different drawbacks and advantages as you will see below.

### Light Restore Points
By default, Pacback creates a Light Restore Point which consists of only a .meta file. When you fall back on this restore point, Pacback will search your file system looking for old versions specified in the .meta file. If you have not cleared your cache or are rolling back a recent upgrade, Light Restore Points provide extremely fast and effective rollbacks. 

**Light Restore Point Advantages:**
 - Light RP's are Extremely Small (a few KB at max)
 - Generating a Light RP's is Fast (less than 1s)
 - Low Overhead Means No Impact on Pacman Upgrade Times When Using `pacback -Syu`

**Light Restore Point Disadvantages:**
 - Light RP's Will Fail to Provide Real Value If Old Package Versions Are Removed (aka. paccahe -r)
 - Light RP's Are Not Portable

### Full Restore Points
When a Full Restore Point is used, Pacback searches through your file system looking for each package version installed. Pacback then creates a Restore Point tar which contains all the compiled packages installed on the system at the time of its creation, along with any additional files the user specifies. Full Restore Points also generate a metadata file but even if you lose or delete this file, you will still be able to run a full system recovery and pacback will simply skip its more advanced features. 

When you fallback on a Full Restore Point, Pacback will unpack the tar and install all the packages contained within. It will also give you the ability to remove any new packages added since its creation. Once this is complete, if you have packed any config files into the restore point, Pacback with checksum each file and compare it to your file system. Pacback will then let you selectively overwrite each subsection of file type: Changed, Added, and Removed.

**Full Restore Point Advantages:**
 - Full RP's Are 100% Self Contained
 - Adding Custom Directories Allows for the Rollback of Config Files Associated with New Versions
 - Full RP's are Portable and Can Be Used to Deploy Staged Updates to Servers
 - Full RP's Can Backup Entire Systems and Applications

**Full Restore Point Disadvantages:**
 - Full RP's Are Large
 - Full RP's Create Duplicate Copies of Complied Packages Already Present in the Cache or in Other RP's
 - Full RP's are IO Bound During Compression and Decompression


### Metadata Files
Restore Point metadata files contain information in a human readable format about packages installed at the time of its creation along with other information. This information is used by Pacback to restore older versions of packages and provide general information about the Restore Point. Each meta data file will look something like this:

> ====== Pacback RP #02 ======  
Date Created: 2019/12/02  
Packages Installed: 1038  
Packages in RP: 0  
Size of Packages in RP: 0B  
Pacback Version: 1.3.0  
======= Pacman List ========  
a52dec 0.7.4-10  
aarch64-linux-gnu-binutils 2.33.1-1  
aarch64-linux-gnu-gcc 9.2.0-1  
aarch64-linux-gnu-glibc 2.30-1  
aarch64-linux-gnu-linux-api-headers 4.20-1
......
....
..
