# Pacback User Guide

**Table of Contents:**

-   [Get Snapshot and Restore Point Info](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#getting-snapshot-and-restore-point-info)
-   [Using Rolling System Snapshots](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#rolling-system-snapshots)
-   [Creating Permanent Restore Points](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#creating-permanent-restore-points)
-   [Rollback a List of Packages](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#rollback-a-list-of-packages)
-   [Rolling Back to an Archive Date](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#rolling-back-to-an-archive-date)
-   [Backup Version Sensitive Application Data](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#backup-version-sensitive-application-data)
-   [Automated Cache Cleaning](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#automated-cache-cleaning)
-   [Using the User Config File](https://github.com/JustinTimperio/pacback/blob/master/USER_GUIDE.md#using-the-user-config-file)

## Getting Snapshot and Restore Point Info

As you accumulate snapshots(SS) and restore points(RP) it can be easy to lose track of the changes you’ve made to the system. Pacback makes it easy not only to get information about an individual RP or SS but also easily compare any of your RP’s or SS’s. 

Let's say you want to get information about a restore point you created a few weeks ago. All you need to do is run `pacback -i rp30`:

![Get Info](https://i.imgur.com/oZexzd3.png)

You can also compare any two restore points or snapshots easily with the `--diff` command. Lets say you want to compare a restore point you created a few days ago and snapshot that was just generated a few hours ago. All you need to do is run `pacback -df rp11 ss5`:

![Diff Command](https://i.imgur.com/ghZoi95.png)

## Rolling System Snapshots

One of the problems with rolling releases is you never know when a problem might occur. It may be months before you run into an issue, at which point, you will need to scramble to figure out when your system was stable last. By using the integrated pacman hook, Pacback creates a restore point every time you make any change to the system. This means at any point you can revert your system to any point in time without creating a restore point ahead of time. This also gives a high degree of granularity when making many small changes throughout the day.

1.  Make a change to your system: `pacman -S tree rsync htop`
2.  Run `pacback -ls` and you should see a new snapshot in slot `#00`. Each time you make a change(add, remove, upgrade any package) a snapshot will be created during the transaction.
3.  To undo all the changes you just made simply `pacback -ss 0`.

![Pacback Snapshot](https://i.imgur.com/GE61yqe.gif)

## Creating Permanent Restore Points

Remember that one time all your packages were working perfectly? (God that was great.) Have a production system running perfectly that needs to be updated but you don't want to backup the whole disk? With pacback restore points, you don't have to lose that version state. Restore points are user-defined version states that describe a set of packages and even configuration files on your system that you don't want to lose track of. Unlike many backup utilities pacback doesn't need backup the whole disk. Instead, it hardlinks packages with inodes without duplicating the files so that pacback can maintain the smallest possible profile on your system.

To create a restore point, then get information about it:

1.  `pacback -nc -f -c 1 -l 'Production'`
2.  `pacback -i rp1`

![Restore Points](https://i.imgur.com/5f5d5HI.gif)

## Rollback a List of Packages

Most issues introduced by an upgrade stem from a single package or a set of related packages. Pacback allows you to selectively rollback a list of packages using `pacback -pkg`. Packback searches your file system looking for all versions associated with each package name. When searching, Pacback attempts to avoid matching generic names used by multiple packages (I.E. _xorg_ in _xorg_-server, _xorg_-docs, _xorg_-xauth). If no packages are found, the search parameters can be widened but it will likely show inaccurate results.

In this example, we selectively rollback 2 packages.

1.  `pacback -pkg typescript neofetch`

![Pacback Rolling Back a List of Packages](https://i.imgur.com/9bd4YRB.gif)

## Rolling Back to an Archive Date

Another popular way to rollback is to fetch packages directly from the Arch Linux Archives using pacman. Pacback automates this entire process with the `pacback -dt` command. To rollback to a specific date, give `-dt` a date in YYYY/MM/DD format and Pacback will automatically save your mirrorlist, point a new mirrorlist to an archive URL, then run a full system downgrade. 

1.  `pacback -rb 2019/10/18`

![Pacback Rolling Back an Archive Date](https://i.imgur.com/jhkeoCF.gif)

## Backup Version Sensitive Application Data

In some cases, config files may need to be modified when updating packages. In other cases, you may want to backup application data before deploying an upgrade in case of error or corruption. Pacback makes it extremely simple to store these files and will automatically compare files you have stored against your current file system. Once checksumming is complete you can selectively overwrite each subsection of file type: Changed, Added, and Removed.

In this example we pack up a custom directory containing over 10k files.

1.  `pacback -c 1 -f -nc -d /home/conductor/test-core`
2.  `pacback -rp 1` 

![Pacback Saving App Data](https://i.imgur.com/Us8LqGj.gif)

## Automated Cache Cleaning

Pacback is first and foremost an automation tool and this extends to system maintenance. Cleaning and managing the cached packages on a system is something that many of us forget to do. Pacback has an inbuilt function that lets you easily clean old and orphaned packages. It will also check each one of your restore points looking for old ones that can be purged from the system. 

![Pacback Cache Cleaning](https://i.imgur.com/UeL2H9B.gif)

## Using The User Config File

Pacback comes pre-configured out of the box, but for many users, there may be the need to customize pacback to meet the needs of their particular use case. Pacback creates a file `/etc/pacback.conf` which users can modify to meet their needs. This includes modifying some of pabacks lower level features like snapshot locks, and also allows the user to outright disable some features.

Below is the preconfigured config file:

```
## Pacback Config File
## Version 2.0.0

## Mandatory Settings

# Number Of Seconds Before The Snapshot Lock Expires
# MUST be an INT
hook_cooldown = 300

# Max Number Of Snapshots To Keep
# MUST be an INT
max_snapshots =  25

# Let The User Schedule a Reboot if Needed.
# If False Pacback Will Only Notify You
# MUST be True or False
reboot = True

## Optional Settings

# Number Of Minutes In Future To Schedule Reboot
# Only Runs After The Kernel Has Changed
# MUST be an INT
reboot_offset = 5

# Number of Old Cached Versions To Keep
# When Running a Pacback Cache Clean
# MUST be an INT
keep_versions = 3

# Number Of Days Before an RP is Flagged Old
# MUST be an INT
old_rp = 180

```
