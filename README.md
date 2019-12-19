
# Pacback - Alpha 1.5
**TLDR: This projects ultimate goal is to provide flexible and resilient downgrades while maintaining a slim profile and fast performance.**

***Warning: [On 2019/12/27 Arch Linux will be changing it's default compression method from .xz to .zst.](https://www.reddit.com/r/archlinux/comments/e7tbce/update_archdevpublic_rfc_devtools_changing) I've updated Pacback in advace and everything seems to be working correctly. If you run into any problems please submit an issue.***

### Index:
1. [CLI Commands](https://github.com/JustinTimperio/pacback#pacback-cli-commands-and-flags)
2. [Install](https://github.com/JustinTimperio/pacback#install-instructions)
3. [Examples](https://github.com/JustinTimperio/pacback#pacback-usage-examples)
4. [Pacback's Design](https://github.com/JustinTimperio/pacback#pacbacks-design)
5. [Feature Path and Bugs](https://github.com/JustinTimperio/pacback#feature-path-known-bugs-issues-and-limitations)
 

## Abstract:
I love Arch Linux and rolling-release distros. Being at the head of Linux kernel and application development means access to the latest features and bug fixes. This also often means dealing with the latest bugs. While I don't run into major bugs often, when they happen, they cripple my productivity. Reversing individual packages is generally a slow and manual process. While some tools exist, none meet my needs. In particular, support for rolling back AUR packages is extremely lacking.  

## Core Features:

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

### Core Commands
* -c, --create_rp | Generate a pacback restore point. Takes a restore point # as an argument.\
**Example: `pacback -c 1`**
* -f, --full_rp | Generate a pacback full restore point.\
**Example: `pacback -f -c 1`**
* -rb, --rollback | Rollback to a previously generated restore point or to an archive date.\
**Example: `pacback --rollback 1` or `pacback --rollback 2019/08/14`**
* -Syu, --upgrade | Create a light restore point and run a full system upgrade. Use snapback to restore this version state.\
**Example: `pacback -Syu`**
* -sb, --snapback | Rollback packages to the version state stored before that last pacback upgrade.\
**Example: `pacback --snapback`**
* -pkg, --rollback_pkgs | - Rollback a list of packages looking for old versions on the system.\
**Example: `pacback -pkg package_1 package_2 package_3`**
* -u, --unlock_rollback | Release any date rollback locks on /etc/pacman.d/mirrorlist. No argument is needed.\
**Example: `pacback --unlock_rollback`**

### Flags and Utils
* -rm, --clean | Clean old and orphaned pacakages along with old Restore Points. Provide the number of package you want keep.\
**Example: `pacback -rm 3`**
* -d, --add_dir | Add any custom directories to your restore point during a `--create_rp AND --full_rp`.\
**Example: `pacback -f -c 1 -d /dir1/to/add /dir2/to/add /dir3/to/add`**
* -nc, --no_confirm | Skip asking user questions during RP creation. Will answer yes to all.\
**Example: `pacback -nc -c 1`**
* -n, --notes | Add Custom Notes to Your Metadata File.\
**Example: `pacback -nc -c 1 -f -n 'Here Are Some Notes'`**
* -ih, --install_hook | Install a Pacman hook that creates a snapback restore point during each Pacman upgrade.\
**Example: `pacback --install_hook`**
* -rh, --remove_hook | Remove the Pacman hook that creates a snapback restore point during each Pacman upgrade.\
**Example: `pacback --remove_hook`**
* -i, --info | Print information about a retore point.\
**Example: `pacback --info 1`**
* -v, --version | Display Pacback Version.\
**Example: `pacback -v`**



------------------

## Install Instructions:
Where ever you clone the repository will act as the base directory for Restore Points.
1. `git clone --recurse-submodules https://github.com/JustinTimperio/pacback.git`
2. `pacman -S python-tqdm arch-install-scripts`
3. `sudo ln -s /dir/to/pacback/core/pacback.py /usr/bin/pacback`

------------------

## Pacback Usage Examples:
While there are only a few CLI commands, they can be used in a wide variety of complex restoration tasks. Below are some examples of how to use and deploy Pacback in your systems.

### FailProof -Syu Upgrades
One of the problems with rolling releases is you never know when a problem might occur. It may be months before you run into an issue at which point, you will need to scramble to figure out when your system was stable last. Pacback offers two solutions that help solve this issue. If you would like integrate Pacback directly with Pacman you can automaticlly install a Pacman hook that creates a Light Restore Point every time you upgrade with Pacman. Pacback also offers it's own `-Syu` if you don't want to use a hook. In both of these cases Pacback creates a Light Restore Point numbered `00` before every system upgrade. If you run into any issues with the upgrade, simply use `pacback --snapback` to instantly downgrade only the packages you upgraded and remove any additions.

Using Pacman:
1. Install the Pacback hook with: `pacback --install_hook`
2. Now use Pacman normally and when you need undo a upgrade use: `pacback --snapback`

Using Pacback:
1. Deploy a system upgrade with: `pacback -Syu`
2. Instantly rollback this update using: `pacback -sb`

![Pacback Snapback](https://i.imgur.com/AX92cfz.gif)

### Simple System Maintenance for Developers
If you are like me you love to install and test the latest projects the community is working on. The downside of doing this is the slow build-up of packages as you try to remember why that you ever installed a set of packages. To avoid this you can use pacback to create a restore point then install a bunch of experimental packages you only plan on keeping for a few days. After you're done, simply roll back to the Restore Point and all the packages you installed will be removed. 

In the following example, I will install Haskell which is a dependency nightmare. After installing it we will show how to quickly uninstall all your changes. 
1. First, we create a restore point with: `pacback -c 3`
2. Next we install Haskell packages with: `pacman -S stack` 
3. Once you are ready to remove Haskell use: `pacback -rb 3`

![Pacback Haskell](https://imgur.com/PzUznWZ.gif)

### Backup Version Sensitive Application Data
In some cases, config files may need to be modified when updating packages. In other cases, you may want to backup application data before deploying an upgrade in case of error or corruption. Pacback makes it extremely simple to store these files and will automatically compare files you have stored against your current file system. Once checksumming is complete you can selectively overwrite each subsection of file type: Changed, Added, and Removed.

In this example we pack up an Apache websever and Postgresql database.
1. `pacback -c 1 -f -d /var/www /etc/httpd /var/lib/postgres/data`
2. `pacback -Syu`
3. `pacback -rb 1` 

![Pacback Saving App Data](https://imgur.com/Ag0NROG.gif)

### Rollback a List of Packages 
Most issues stem from a single package or a set of related package. Pacback allows you to selectively rollback a list of packages using `pacback -pkg package_1 package_2 package_3`. Packback searches your file system looking for all versions associated with each package name. When searching for a package, be as specific as possible. Since generic names like 'linux' or 'gcc' appear in many package names, the search may be cluttered with unrelated packages.

In this example, we selectively rollback 2 packages.
1. `pacback -pkg typescript electron4`

![Pacback Rolling Back a List of Packages](https://imgur.com/Rhy6iDn.gif)

### Rolling Back to an Archive Date
Another popular way to rollback package versions is to use the Arch Linux Archives to pull packages directly with pacman. Pacback automates this entire process with the `pacback -rb` command. To rollback to a specific date, give `-rb` a date in YYYY/MM/DD format and Pacback will automatically save your mirrorlist, point a new mirrorlist to an archive URL, then run a full system downgrade. Whenever you are ready to jump back to the head, run `pacback -u` and Pacback with automatically retore your old mirrorlist. In the event that you destroy this backup, Pacback can automatically fetch a new HTTP US mirrorlist for the system.

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

### Full Restore Points
When a Full Restore Point is used, Pacback searches through your file system looking for each package version installed. Pacback then creates a Restore Point folder which contains a hardlink to each compiled package installed on the system at the time of its creation, along with any additional files the user specifies.  Since each package is a hardlinked to an inode, a package can be referenced an infinite number of times without duplication. A package will not be fully deleted from the system until all links to the inode are removed. This also provides light restore points additional resilience as they can search full restore points for the packages they need.


![https://i.imgur.com/eikZF2g.jpg](https://i.imgur.com/eikZF2g.jpg)

Full Restore Points also generate a metadata file but even if you lose or delete this file, you will still be able to run a full system rollback and pacback will simply skip its more advanced features. When you fallback on a Full Restore Point, Pacback runs its normal package checks giving you the ability rollback packages and remove any new packages added since its creation. Once this is complete, if you have any config files saved, Pacback will checksum each file and compare it to your file system. Pacback will then let you selectively overwrite each subsection of file type: Changed, Added, and Removed.

**Full Restore Point Advantages:**
 - Full RP's Are 100% Self Contained
 - Adding Custom Directories Allows for the Rollback of Config Files Associated with New Versions
 - Full RP's Ensure That Packages Are Not Prematurely Removed
 - Provides Light Restore Points Additional Resilience

**Full Restore Point Disadvantages:**
- Hardlinking Packages Can Take A Long Time
- The Addition of Thousands of Duplicate File Names Requires Pacback to Use Costly Duplication Filters
-  Full RP's Don't Protect Against Inode Corruption

------------------

## Metadata Files
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

------------------

## Feature Path, Known Bugs, Issues, and Limitations
This list is likely to have many changes and edits as new versions are released. Please read this carefully when updating versions or deploying pacback to new systems.

### Issues:
- **Pacback Skips Checksumming Files over 1GB.** - This is done for a number of reasons, first of which is that python sucks at this. I mean its god awful at reading large files. In my testing checksumming took 30x-50x longer compared to a terminal equivalent. The second reason large files are skipped is that this it is outside of Pacback's use-case. Packaging directories is intended for saving the state of potentially thousands of small configuration files, not large iso's or archives. 

- **Pacback Creates Missing Directories as Root.** - Currently files are copied out of the restore point with the exact same permissions they went in with. The issue here is the creation of missing directories. When Pacback creates these directories the original permissions are not copied. 

- ~~**My Full Restore Points Are No Longer Compatiable.** - This is because I have completely reworked Full Restore Points to be massively more effecient. I'm working on a way to convert these older restore points.~~

### Feature Path:
- [x] Version Checking
- [x] Version Migration
- [x] Improved Cache and Restore Point Cleaning
- [x] Pacman Hook
- [ ] Impoved Searches for Individual Packages
- [ ] Fix Checksumming
- [ ] Fix Directory Creation
- [ ] Better Color Output
- [ ] AUR Package
- [ ] Arch Archive Support for Singular Package Versions
- [ ] Faster Package Searches
- [ ] Improve Internal Documentation
