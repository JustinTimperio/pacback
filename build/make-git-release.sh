#!/usr/bin/env bash

################
# Define Vars
##############

pkg_version=$(printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)")
base_path='/tmp/pacback-git'
buildpkg_path=$base_path/PKGBUILD
srcinfo_path=$base_path/.SRCINFO


####################
# Setup For Build
##################

script_path=$(realpath $0)
dir_path=$(dirname $script_path)
rm -fR $base_path
mkdir $base_path
cd $dir_path


#########################
# Create Build Package 
#######################

# Make BUILDPKG
cp $dir_path/BUILDPKG_GIT_TEMPLATE $buildpkg_path
sed -i "s/_VERSION_/$pkg_version/" $buildpkg_path

# Make SRCINFO
cd $base_path
makepkg --printsrcinfo > $srcinfo_path
