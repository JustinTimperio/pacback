
# Pacback 
 **Index:**
1. [CLI Commands](https://github.com/JustinTimperio/pacback#pacback-cli-commands-and-flags)
2. [Install Instructions](https://github.com/JustinTimperio/pacback#install-instructions)
3. [User Guide](https://github.com/JustinTimperio/pacback#pacback-usage-examples)
4. [Developer Guide](https://github.com/JustinTimperio/pacback#pacbacks-design)
 
## Abstract:
Being at the head of Linux kernel and application development means access to the latest features but also often means dealing with the latest bugs. While I don't run into major bugs often, when they happen, they cripple my productivity. Reversing individual packages is generally a slow manual process and while some tools exist, none meet my needs. In particular, support for downgrading AUR packages is extremely lacking. To combat these issues I wrote pacback to automate various downgrade methods available for restoring Arch Linux to previous version states. 

## Core Features:

- Resilient Downgrades and Upgrades
- Rolling System Snapshots
- Rollback to Arch Archive Dates
- Easy Tracking of All System Additions, Removals, and Upgrades
- Native Support for AUR Packages
- Storage and Restoration of Version Dependent Files
- Multi-Threaded Operations


## Pacback CLI Commands and Flags:
Pacback offers several core commands that streamline the process of creating and restoring versions. The CLI is designed to be dead simple and provide detailed feedback and user control.

### Core Commands
* -c, --create_rp | Generate a pacback restore point. Takes a restore point # as an argument.\
*Example: `pacback -c 1`*
* -rp, --restore_point | Rollback to a previously generated restore point.\
*Example: `pacback -rp 1`*
* -ss, --snapshot | Restore the system to an automatically created snapshot.\
*Example: `pacback -ss 2`*
* -dt, --date | Rollback to a date in the Arch Linux Archive.\
*Example: `pacback -dt 2019/08/14`*
* -pkg, --package | - Rollback a list of packages looking for old versions on the system.\
*Example: `pacback -pkg zsh cpupower neovim`*

### Flags
* -f, --full_rp | Generate a pacback full restore point.\
*Example: `pacback -f -c 1`*
* -d, --add_dir | Add any custom directories to your restore point during a `--create_rp AND --full_rp`.\
*Example: `pacback -f -c 1 -d /dir1/to/add /dir2/to/add /dir3/to/add`*
* -nc, --no_confirm | Skip asking user questions during RP creation. Will answer yes to most input.\
*Example: `pacback -nc -c 1`*
* -l, --label | Add a label to your restore point.\
*Example: `pacback -nc -c 1 -f -l 'Production'`*

### Print Info
* -ls, --list | List information about all restore points and snapshots.\
*Example: `pacback -ls`*
* -i, --info | Print information about a retore point or snapshot.\
*Example: `pacback -i rp1` or `pacback -i ss1`*
* -df, --diff | Compare any two restore points or snapshots.\
*Example: `pacback -df rp1 rp2` or `pacback -df rp1 ss1`*
* -v, --version | Display pacback version and cache information.\
*Example: `pacback -v`*

### Utilities
* -cl, --clean | Clean old and orphaned pacakages along with old Restore Points.\
*Example: `pacback -cl`*
* -rm, --remove | Removes the selected restore point.\
*Example: `pacback -rm 12 -nc`*
* --install_hook | Install a pacman hook that creates a snapshot during each pacman transaction.\
*Example: `pacback --install_hook`*
* --remove_hook | Removes the pacman hook that creates snapshots.\
*Example: `pacback --remove_hook`*


## Install Instructions:
Pacback offers two AUR packages. (Special thanks to [Attila Greguss](https://github.com/Gr3q) for maintaining them.)

[pacback](https://aur.archlinux.org/packages/pacback): This is the recommended install for most users. Releases mark stable points in Pacbacks development, preventing unnecessary upgrades/changes that may introduce instability into production machines. 

[pacback-git](https://aur.archlinux.org/packages/pacback-git): This package fetches the latest version from git. The master branch will be unstable periodically but is ideal for anyone looking to contribute to pacback's development or if you want access to the latest features and patches.

## User Guide
While there are only a few CLI commands, they can be used in a wide variety of complex restoration tasks. The user guide has grown quite extensively in size and has been moved to its own page! [Check it out here!]()

## Developer Guide
Interested in helping develop pacback? Have questions about how it works? The detailed developer guide explains all the core features, codebase, and design philosophy of pacback. [Check it out here!]()
