#!/usr/bin/env bash

## Updates Meta Data Files and Directory Paths for Upgrade From Alpha
## The Script is Safe to Run Multiple Times

#########################
# Patch Metadata Files
#######################

base_path='/var/lib/pacback'

# Fix First Line
find $base_path -type f -name '*.meta' -exec sed -i '1 s/^====== Pacback RP.*/======= Pacback Info =======/' {} +

# Fix Version Field
find $base_path -type f -name '*.meta' -exec sed -i 's/^Pacback Version:/Version:/' {} +

## Removed For Safety During Multiple Runs
## This Value is Not Essential For Runtime
# Add Creation Time
# find $base_path -type f -name '*.meta' -exec sed -i '/^Date Created:.*/a Time Created: 00:00:00' {} +

# Add Type Fields
find $base_path -type f -name '*.meta' -exec sed -i '/^Time Created:.*/a Type: Restore Point' {} +
find $base_path -type f -name '*.meta' -exec sed -i 's/^Packages in RP: 0/SubType: Light/' {} +

# Remove Fields If No Packages Are Cached
find $base_path -type f -name '*.meta' -exec sed -i '/^Size of Packages in RP: 0B/d' {} +


##############################
# Patch Full Restore Points
############################

# Add SubType Field
find $base_path -type f -name '*.meta' -exec sed -i '/^Packages in RP:.*/i SubType: Full' {} +

# Fix Fields If Package Are Cached
find $base_path -type f -name '*.meta' -exec sed -i 's/^Packages in RP:/Packages Cached:/' {} +
find $base_path -type f -name '*.meta' -exec sed -i 's/^Size of Packages in RP:/Package Cache Size:/' {} +

# Fix Custom Dir Fields
find $base_path -type f -name '*.meta' -exec sed -i 's/^Dirs /Dir /' {} +

# Change Package Cache Folder Name
find $base_path/restore-points -type d -name 'pac_cache' -exec rename 'pac_cache' 'pkg-cache' {} +
