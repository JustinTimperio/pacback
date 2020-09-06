#!/usr/bin/env bash

################
# Define Vars
##############

pkg_version=$(cd .. && grep -Poi '\d+.\d+.\d+' core/session.py)
tar_name=$(echo pacback-$pkg_version-SOURCE-x86_64.tar)
zst_name=$(echo pacback-$pkg_version-SOURCE-x86_64.tar.zst)
base_path='/tmp/pacback'
tar_path=$base_path/$tar_name
zst_path=$base_path/$tar_name.zst
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


##########################
# Build Release Package
########################

# Add Config to Tar
find . -maxdepth 1 -type f -name 'config' -exec tar -rvf $tar_path --owner=0 --group=0 {} +

# Add Alpha Upgrade Script to Tar
find . -maxdepth 1 -type f -name 'alpha_upgrade.sh' -exec tar -rvf $tar_path --owner=0 --group=0 {} +

# Add License to Tar
cd ..
find . -maxdepth 1 -type f -name 'LICENSE' -exec tar -rvf $tar_path --owner=0 --group=0 {} +

# Add Core Files to Tar
cd core
find . -maxdepth 1 -type f -name '*.py' -exec tar -rvf $tar_path --owner=0 --group=0 --transform 's,.,core,' {} +

# Add PAF to Tar
cd paf
find . -maxdepth 1 -type f -name '*.py' -exec tar -rvf $tar_path --owner=0 --group=0 --transform 's,.,core/paf,' {} +

# Compress Source Package
zstd -z $tar_path
pkg_csum=$(sha512sum $zst_path | cut -d " " -f 1)
rm $tar_path


#########################
# Create Build Package 
#######################

# Make BUILDPKG
cp $dir_path/BUILDPKG_FULL_TEMPLATE $buildpkg_path
sed -i "s/_VERSION_/$pkg_version/" $buildpkg_path
sed -i "s/_PACKAGE_/$zst_name/" $buildpkg_path
sed -i "s/_PKG_CHECKSUM_/$pkg_csum/" $buildpkg_path

# Make SRCINFO
cd $base_path
makepkg --printsrcinfo > $srcinfo_path