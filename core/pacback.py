#! /usr/bin/env python3
# A utility for marking and restoring stable arch packages
import argparse
import re
import os
import create_rp as cp
import rollback_rp as rb
import pac_utils as pu
import version_control as vc
from python_scripts import prError


#<#><#><#><#><#><#>#<#>#<#
#<># CLI Args
#<#><#><#><#><#><#>#<#>#<#


parser = argparse.ArgumentParser(description="A reliable rollback utility for marking and restoring custom save points in Arch Linux.")
# Pacback -Syu
parser.add_argument("-Syu", "--upgrade", action='store_true',
                    help="Create a light restore point and run a full system upgrade. Use snapback to restore this version state.")
parser.add_argument("-sb", "--snapback", action='store_true',
                    help="Rollback packages to the version state stored before that last pacback upgrade.")
parser.add_argument("--hook", action='store_true', help="Used Exclusivly by the Pacback Hook.")
# Base RP Functions
parser.add_argument("-rb", "--rollback", metavar=('RP# or YYYY/MM/DD'),
                    help="Rollback to a previously generated restore point or to an archive date.")
parser.add_argument("-pkg", "--rollback_pkgs", nargs='*', default=[], metavar=('PACKAGE_NAME'),
                    help="Rollback a list of packages looking for old versions on the system.")
parser.add_argument("-c", "--create_rp", metavar=('RP#'),
                    help="Generate a pacback restore point. Takes a restore point # as an argument.")
parser.add_argument("-f", "--full_rp", action='store_true',
                    help="Generate a pacback full restore point.")
parser.add_argument("-d", "--add_dir", nargs='*', default=[], metavar=('/PATH'),
                    help="Add any custom directories to your restore point during a `--create_rp AND --full_rp`.")
parser.add_argument("-u", "--unlock_rollback", action='store_true',
                    help="Release any date rollback locks on /etc/pacman.d/mirrorlist. No argument is needed.")
# Utils
parser.add_argument("-ih", "--install_hook", action='store_true',
                    help="Install a Pacman hook that creates a snapback restore point during each Pacman Upgrade.")
parser.add_argument("-rh", "--remove_hook", action='store_true',
                    help="Remove the Pacman hook that creates a snapback restore point during each Pacman Upgrade.")
parser.add_argument("-i", "--info", metavar=('RP#'),
                    help="Print information about a retore point.")
parser.add_argument("-nc", "--no_confirm", action='store_true',
                    help="Skip asking user questions during RP creation. Will answer yes to all.")
parser.add_argument("-v", "--version", action='store_true',
                    help="Display Pacback Version.")
parser.add_argument("-rm", "--clean", metavar=('# Versions to Keep'),
                    help="Clean Old and Orphaned Pacakages. Provide the number of package you want keep.")
parser.add_argument("-n", "--notes", metavar=('SOME NOTES HERE'),
                    help="Add Custom Notes to Your Metadata File.")
args = parser.parse_args()


#<#><#><#><#><#><#>#<#>#<#
#<># Args Flow Control
#<#><#><#><#><#><#>#<#>#<#

version = '1.6.0'
vc.pre_fligh_check()

if args.version:
    print('Pacback Version: ' + version)

if args.info:
    if re.findall(r'^([0-9]|0[1-9]|[1-9][0-9])$', args.info):
        num = str(args.info).zfill(2)
        pu.print_rp_info(num)
    else:
        prError('Info Args Must Be in INT Format!')

if args.clean:
    pu.clean_cache(args.clean)

elif args.install_hook:
    pu.pacback_hook(install=True)

elif args.remove_hook:
    pu.pacback_hook(install=False)

elif args.rollback_pkgs:
    pu.rollback_packages(args.rollback_pkgs)

elif args.hook:
    args.no_confirm = True
    cp.create_restore_point('00', args.full_rp, args.add_dir)

elif args.upgrade:
    cp.create_restore_point('00', args.full_rp, args.add_dir)
    os.system('sudo pacman -Syu')

elif args.snapback:
    if os.path.exists('/var/app/pacback/restore-points/rp00.meta'):
        rb.rollback_to_rp('00')
    else:
        prError('No Snapback Found!')

elif args.rollback:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.rollback):
        rb.rollback_to_rp(version, args.rollback)
    elif re.findall(r'^(?:[0-9]{2})?[0-9]{2}/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}$', args.rollback):
        rb.rollback_to_date(args.rollback)
    else:
        prError('No Usable Argument! Rollback Arg Must be a Restore Point # or a Date.')

elif args.create_rp:
    if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.create_rp):
        cp.create_restore_point(version, args.create_rp, args.full_rp, args.add_dir, args.no_confirm, args.notes)
    else:
        prError('Create RP Args Must Be INT or Date! Refer to Documentation for Help.')

elif args.unlock_rollback:
    pu.unlock_rollback()

elif not args.info or not args.version:
    pass

else:
    prError('No Usable Argument Given!')
