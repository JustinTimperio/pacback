# Pacback

 **Index:**

1.  [CLI Commands](https://github.com/JustinTimperio/pacback#pacback-cli-commands-and-flags)
2.  [Install Instructions](https://github.com/JustinTimperio/pacback#install-instructions)
3.  [User Guide](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md)
4.  [Developer Guide](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md)

## Abstract:

Being at the head of Linux kernel and application development means access to the latest features but also often means dealing with the latest bugs. While I don't run into major bugs often, when they happen, they cripple my productivity. Reversing individual packages is generally a slow manual process and while some tools exist, none meet my needs. In particular, support for downgrading AUR packages is extremely lacking. To combat these issues I wrote pacback to automate various downgrade methods for restoring Arch Linux to a previous version state. 

## Core Features:

-   Resilient Downgrades and Upgrades
-   Rolling System Snapshots
-   Rollback to Arch Archive Dates
-   Easy Tracking of All System Additions, Removals, and Upgrades
-   Native Support for AUR Packages
-   Storage and Restoration of Version Dependent Files
-   Multi-Threaded Operations

## Pacback CLI Commands and Flags:

Pacback offers several core commands that streamline the process of creating and restoring versions. The CLI is designed to be dead simple and provide detailed feedback and user control.

### Core Commands

-   \-c, --create_rp | Generate a pacback restore point. Takes a restore point # as an argument.\
    _Example: `pacback -c 1`_
-   \-rp, --restore_point | Rollback to a previously generated restore point.\
    _Example: `pacback -rp 1`_
-   \-ss, --snapshot | Restore the system to an automatically created snapshot.\
    _Example: `pacback -ss 2`_
-   \-dt, --date | Rollback to a date in the Arch Linux Archive.\
    _Example: `pacback -dt 2019/08/14`_
-   \-pkg, --package | - Rollback a list of packages looking for old versions on the system.\
    _Example: `pacback -pkg zsh cpupower neovim`_

### Flags

-   \-f, --full_rp | Generate a pacback full restore point.\
    _Example: `pacback -f -c 1`_
-   \-d, --add_dir | Add any custom directories to your restore point during a `--create_rp AND --full_rp`.\
    _Example: `pacback -f -c 1 -d /dir1/to/add /dir2/to/add /dir3/to/add`_
-   \-nc, --no_confirm | Skip asking user questions during RP creation. Will answer yes to most input.\
    _Example: `pacback -nc -c 1`_
-   \-l, --label | Add a label to your restore point.\
    _Example: `pacback -nc -c 1 -f -l 'Production'`_

### Print Info

-   \-ls, --list | List information about all restore points and snapshots.\
    _Example: `pacback -ls`_
-   \-i, --info | Print information about a retore point or snapshot.\
    _Example: `pacback -i rp1` or `pacback -i ss1`_
-   \-df, --diff | Compare any two restore points or snapshots.\
    _Example: `pacback -df rp1 rp2` or `pacback -df rp1 ss1`_
-   \-v, --version | Display pacback version and cache information.\
    _Example: `pacback -v`_

### Utilities

-   \-cache, --cache_size | Calculate reported and actual cache sizes.\
    _Example: `pacback -cache`_
-   \-cl, --clean | Clean old and orphaned pacakages along with old restore points.\
    _Example: `pacback -cl`_
-   \-rm, --remove | Removes the selected restore point.\
    _Example: `pacback -rm 12 -nc`_
-   \--install_hook | Install a pacman hook that creates a snapshot during each pacman transaction.\
    _Example: `pacback --install_hook`_
-   \--remove_hook | Removes the pacman hook that creates snapshots.\
    _Example: `pacback --remove_hook`_

## Install Instructions:

Pacback offers two AUR packages. (Special thanks to [Attila Greguss](https://github.com/Gr3q) for maintaining them.)

[pacback](https://aur.archlinux.org/packages/pacback): This is the recommended install for most users. Releases mark stable points in Pacbacks development, preventing unnecessary upgrades/changes that may introduce instability into production machines. 

[pacback-git](https://aur.archlinux.org/packages/pacback-git): This package fetches the latest version from git. The master branch will be unstable periodically but is ideal for anyone looking to contribute to pacback's development or if you want access to the latest features and patches.

## User Guide

While there are only a few CLI commands, they can be used in a wide variety of complex restoration tasks. The user guide has grown quite extensively in size and has been moved to its own page! [Check it out here!](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md)

## Developer Guide

Interested in helping develop pacback? Have questions about how it works? The detailed developer guide explains all the core features, codebase, and design philosophy of pacback. [Check it out here!](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md)
