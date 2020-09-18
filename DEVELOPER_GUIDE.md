# Pacback Developer Guide

This documentation is for anyone looking to gain a deeper understanding of how pacback works and as a reference guide for those contributing to its development. If you are interested in contributing to pacback, [join us on Gitter!](https://gitter.im/pacback/Development) 

**Table of Contents:**

-   [Design Philosophy](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#design-philosophy)
-   [Code Structure Overview](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#code-structure-overview)
-   [Metadata Files](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#metadata-files)
-   [Restore Points](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#restore-points)
-   [Snapshots](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#snapshots)
-   [SubType - Light](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#subtype---light)
-   [SubType - Full](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#subtype---full)
-   [Feature Path](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#feature-path)
-   [Known Bugs and Issues](https://github.com/JustinTimperio/pacback/blob/master/DEVELOPER_GUIDE.md#known-bugs-and-issues)

## Design Overview:

Pacback is written entirely in python3 and attempts to implement most features natively. Since its release, pacback has been aggressively optimized, which has greatly reduced each session's overall runtime. Pacback offers several utilities and automation tools but is primarily designed to use two core restore methods: **Restore Points and Snapshots** 

## Design Philosophy

As pacback has grown into a full application, a design philosophy has emerged to meet the demands of the application. The following four pillars inform every part of pacback's design and are ranked in order of importance. Each pillar builds on the previous and MUST NOT compromise the previous.

### Resilience and Safety

First and foremost, pacback is a tool designed for those encountering errors during an upgrade/change of their system. If pacback is unable to complete a restoration safely for the user, it has ZERO value as an application. Even worse than reaching some internal issue that causes an execution failure, is the improper restoration of packages or permanent damage a system's bootability. Pacback has a zero-tolerance mentality when approaching these types of errors and any **internal** command or function that has even a .01% of breaking someone's system. (Currently, pacback cannot catch and correct pacman errors but I hope to add this in the future.) This mentality extends deep into every piece of pacback's code. 

Pacback is designed to be extremely resilient in terms of its runtime and can automatically correct errors that most applications would consider radical edge cases. For example in the event a user has destroyed their mirrorlist or it was, by some ludicrously improbable event destroyed by pacback, a new mirrorlist can automatically be fetched without disrupting the restoration process. Pacback also has correction measures for duplicate cached packages, file corruption, lost files, user input errors, and multiple session overlap, just to name a few.

### Efficiency and Performance

Pacback takes efficiency and performance very seriously since snapshots are created during every pacman transaction. If any part of pacback's execution takes too long, it starts to compromise the ultimate utility of the application. For the most part, pacback has managed to stuff 90% of its total runtime into the space of 50ms-300ms depending on the complexity of the command and the speed of the os drive. It is important to distinguish pacback's internal execution and the programs that it relies on like pacman. The time it takes for pacman to fetch and install packages is not included, as pacback ultimately has no control over that process. 

### Automate Everything

From the beginning, pacback was designed as an automation tool. In most cases, if a task can automatically be resolved without a user, pacback attempts to automate it. While this obviously includes the process of upgrading or downgrading packages, it also includes cache cleaning, kernel change detection, and restore point organization. It is important to note, even though any of these processes could require virtually zero user input, pacback tends to ask the user before any change is actually committed to the system unless the `-no_confirm` flag is used.

### Functional Modular Code

Pacback is written in exclusively a functional style which you can learn more about [here](https://docs.python.org/3/howto/functional.html). This is done for a wide variety of reasons but most notably it produces highly modular code that can be easily abstracted across the codebase. Each function is treated as 'input/output' and nearly every function in the codebase expects some input and will return some result to be used by another function. The next section will go into much more detail about how the code is internally structured but for example, the file meta.py provides all the functions needed to read and interpret metadata files. If you were, say building a new feature that required you to read metadata files you could simply:

    import meta
    import session

    config = session.load_config()
    meta_dict = meta.read(config, meta_path)
    print(meta_dict)

## Code Structure Overview

### [pacback.py](https://github.com/JustinTimperio/pacback/blob/master/core/pacback.py)

This file acts as the main entry for pacback input and is softlinked in /usr/bin. This file is responsible for parsing and verifying all user input. This does not mean that input won't be rejected down the line, but that it is safe for functions down the line to process. This file is also responsible for starting the active session lock and loading the config file that will then be passed to all lower functions.

### [create.py](https://github.com/JustinTimperio/pacback/blob/master/core/create.py)

As the name implies, this file is responsible for all of pacback's creation functions. Since the addition of snapshots, there was a need for a more 'generic' create command. To cleanly allow for this, `create.restore_point()` and `create.snapshot()`assemble variables and prepares the system for its perspective creation process. Once complete these functions then pass their 'work' to `create.main()` for the actual assembly onto the file system. When the creation is complete `create.main()` terminates and returns to the origin function for final completion.

### [restore.py](https://github.com/JustinTimperio/pacback/blob/master/core/restore.py)

As the name implies, this file is responsible for all of pacback's restoration functions. Since pacback offers a diverse set of rollback commands, only `restore.restore_point()` and `restore.snapshot()` access the 'generic' `restore.main()` function. As with create.py, these functions prepare the system for their perspective restoration tasks, then hand off to `restore.main()` for the process of restoring the actual packages. This file also contains `restore.packages()` which allows for users to rollback individual packages and `restore.archive_date()` which lets the user fallback on a date in the Arch Linux Archive.<https://i.imgur.com/smxMBK8.jpg>

### [session.py](https://github.com/JustinTimperio/pacback/blob/master/core/session.py)

As pacback became more complicated, it became necessary to create and manage active session locks to prevent overlaps and collisions between multiple pacback and pacman sessions. This file is also responsible for creating and interpreting hook locks which are used to determine if a snapshot has been created recently. This is especially useful for AUR upgrades which typically upgrade one package at a time meaning that a single `yay -Syu` would produce a snapshot for every package being updated. 

### [user.py](https://github.com/JustinTimperio/pacback/blob/master/core/user.py)

This file is meant for any functions built explicitly for user management for pacback files. In most cases these functions don't impact the file system and simply organize and display information for the user. 

### [utils.py](https://github.com/JustinTimperio/pacback/blob/master/core/utils.py)

Utils.py is the backbone of pacback. These functions act as much of the core abstraction across pacback and is reserved for functions that are expected to be used by multiple other functions. Most of the code in this file has been highly optimized as it is referenced multiple times across the codebase. There are far too many functions in this file to cover here but, by far, the most important functions are `utils.scan_caches()` and `utils.search_cache()`.

### [meta.py](https://github.com/JustinTimperio/pacback/blob/master/core/meta.py)

Meta is responsible for the process of reading and interpreting raw meta data files. This is one of the only files that interacts with raw metadata files and interperts them into structured dictionaries for much easier abstraction throughout the codebase. This also extends to the act of comparing metadata files who's results are also parsed into dictionaries.

### [version.py](https://github.com/JustinTimperio/pacback/blob/master/core/version.py)

This is currently a small file that is currently only responsible for comparing pacback versions for logging reasons.

### [custom_dirs.py](https://github.com/JustinTimperio/pacback/blob/master/core/custom_dirs.py)

This file is responsible for managing all aspects of storing, comparing and restoring custom user files.

### [PAF](https://github.com/JustinTimperio/paf)

PAF or Python-Application-Framework is my personal framework for building and managing multiple python projects. This is easily the most referenced entity in the codebase and is responsible for most 'low level' work. Typically this module attempts to be as pragmatic as possible. While many pip modules exist that may solve some of these issues, PAF has a 'do it yourself' mentality.

## Metadata Files

Metadata files are pacback primary stored 'data structure' and contain information in a human-readable format about packages installed at the time of its creation along with other relevant system information. This information is used by pacback to restore package versions and provide general information to the user. Each metadata file will look something like this:

    ======= Pacback Info =======
    Version: 2.0.0
    Label: None
    Date Created: 2020/08/21
    Time Created: 16:21:53
    Type: Restore Point
    SubType: Full
    Packages Installed: 295
    Packages Cached: 294
    Package Cache Size: 1.52 GB
    Dir File Count: 25675
    Dir Raw Size: 1.63 GB
    Tar Compressed Size: 539.73 MB
    Tar Checksum: 18b87bf457f7aedb8a39a8ccf5a9dfc6

    ========= Dir List =========
    /home/conductor/test-core

    ======= Pacman List ========
    libedit 20191231_3.1-1
    libmicrohttpd 0.9.71-1
    .....
    ....
    ...

## Restore Points

### Light Restore Points

By default, pacback creates a Light restore point which consists of only a .meta file. When you fall back on this restore point, pacback will search your file system looking for old versions specified in the .meta file. If you have not cleared your cache or are rolling back a recent upgrade, Light restore points provide extremely fast and effective rollbacks. 

**Advantages:**

-   Light RP's are extremely small (~25KB)
-   Generating a Light RP's is fast (~50-100 milliseconds)
-   Low overhead means no impact on pacman upgrade times

**Disadvantages:**

-   Light RP's will fail to provide value if old package versions are removed every week (aka. paccahe -r)

### Full Restore Points

When the full flag is used, pacback searches through your file system looking for each package version installed. Pacback then creates a restore point folder which contains a hardlink to each compiled package ('package.pkg.tar.zst') installed on the system at the time of its creation, along with any additional files the user specifies.  

Full Restore Points also generate a .meta file with additional information needed for the Full restore point. When you fallback on a Full restore point, pacback runs its normal package checks giving you the ability to rollback packages and remove any new packages added since its creation. Once this is complete, if you have any config files saved, pacback will checksum each file and compare it to your file system. Pacback will then let you selectively overwrite each subsection of file type: Changed, Added, and Removed.

**Advantages:**

-   Full RP's are 100% self contained
-   Adding custom directories allows for the rollback of config files
-   Full RP's ensure that packages are not prematurely removed
-   Provides Light restore points additional resilience

**Disadvantages:**

-   Building full restore points takes slightly longer than light restore points depending on IO speed.

## Snapshots

Snapshots are a new addition and act as an auto-incrementing fallback point. Snapshots are simply a single metadata file but exist separate from restore points. Pacback installs an alpm hook that is triggered each time pacman makes a change to the system. This includes all installs, removals and upgrades made to the system. As the pacback creates new snapshots, each previous snapshot is shifted forward one slot until it reaches the max number defined by the user. 

![Snapshot Architecture](https://i.imgur.com/smxMBK8.jpg)

## SubType - Light

Subtypes are a more generic abstraction that arose out of the need for multiple restoration types. The light subtype implies that only a metadata file has been generated. In the future if any new additions are added to pacback, they will fall into the subtypes light or full.

## SubType - Full

Subtypes are a more generic abstraction that arose out of the need for multiple restoration types. The full subtype inplies that a metadata file has be generated along with a folder that contains all the packages needed for that restoration. Since each package is hardlinked to an inode, a package can be referenced an infinite number of times without duplication. A package will not be fully deleted from the system until all references to the inode are removed. This also provides light restore points additional resilience as they will automatically search full restore points for the packages they need.

![Pacback Inodes](https://i.imgur.com/eikZF2g.jpg)

## Feature Path

-   [x] Version Checking
-   [x] Version Migration
-   [x] Improved Cache and Restore Point Cleaning
-   [x] Pacman Hook
-   [x] Improved Searches for Individual Packages
-   [x] Internal Logging
-   [x] PEP8 Compliance(ish)
-   [x] Multi-Threaded Package Searches and Filtering
-   [x] Linux Filesystem Hierarchy Compliance
-   [x] Fix Checksumming
-   [x] AUR Package(s)
-   [x] Improved Internal Documentation
-   [x] Session Management
-   [x] Add Snapshot Cooldown Lock
-   [x] Retain Multiple Snapshots
-   [x] Better Color Output
-   [x] Add --diff to Compare Two Meta Files
-   [x] Improved SigInt (Ctrl-C) Handling
-   [ ] Parse/Intercept pacman output and errors
-   [ ] Automatic Correction of pacman Errors
-   [ ] Automated Code Testing
-   [ ] Full CI Pipeline for Releases
-   [ ] Support for Fetching Non-Cached Package Versions
-   [ ] Orchestrated Upgrades for Production Systems
-   [ ] Human Readable Timeline for Snapshots

## Known Bugs and Issues

This list is likely to change as new versions are released. Please read this carefully when updating versions or deploying pacback to new systems. If you run into any errors or are about to submit a bug, please check your log file located in '/var/log/pacback.log'.

-   **Pacback Skips Checksumming Files over 5GB.** - This is done for several reasons. First, Python sucks at reading large files. In my testing, checksumming took 30x-50x longer compared to the terminal equivalent. Second, storing and comparing large files is not really pacback's use-case. Packaging directories into a restore point is intended for saving the state of potentially thousands of small configuration files, not large archives or databases. 

-   **Fixed:** ~~**Pacback Creates Missing Directories as Root.** - Currently files are copied out of the restore point with the exact same permissions they went in with. The issue here is the creation of missing directories. When Pacback creates these directories the original permissions are not copied.~~ 
