#! /usr/bin/env python3
import re
import signal
import argparse
from functools import partial

# Local Modules
import paf
import user
import utils
import create
import restore
import session


##################
# CLI Arguments
################

parser = argparse.ArgumentParser(description="A package rollback utility for Arch Linux.")

# Creation
parser.add_argument("-c", "--create_rp", metavar=('1'),
                    help="Generate a pacback restore point.")
parser.add_argument("--hook", action='store_true',
                    help="Used exxlusively by the pacback hook to create snapshots.")

# Restoration
parser.add_argument("-rp", "--restore_point", metavar=('1'),
                    help="Rollback to a restore point.")
parser.add_argument("-ss", "--snapshot", metavar=('1'),
                    help="Rollback to a snapshot.")
parser.add_argument("-pkg", "--downgrade_pkg", nargs='*', default=[], metavar=('pkg_name'),
                    help="Rollback a list of packages.")
parser.add_argument("-dt", "--date", metavar=('2020/06/23'),
                    help="Rollback to a date in the Arch Archive.")

# Optional Arguments
parser.add_argument("-f", "--full_rp", action='store_true',
                    help="Create full restore point.")
parser.add_argument("-d", "--add_dir", nargs='*', default=[], metavar=('/path/here'),
                    help="Add custom directories to your restore point when using `--full_rp`.")
parser.add_argument("-nc", "--no_confirm", action='store_true',
                    help="Skip asking user questions. Will typically answer yes to all.")
parser.add_argument("-l", "--label", metavar=('Label Name'),
                    help="Tag your restore point with a label.")

# Utils
parser.add_argument("-ih", "--install_hook", action='store_true',
                    help="Install a pacman hook that creates snapshots.")
parser.add_argument("-rh", "--remove_hook", action='store_true',
                    help="Remove the pacman hook that creates snapshots.")
parser.add_argument("-cl", "--clean", action='store_true',
                    help="Clean old packages, orphaned packages, and old restore points.")
parser.add_argument("-rm", "--remove", metavar=('2'),
                    help="Removes the selected restore point.")

# Show Info
parser.add_argument("-v", "--version", action='store_true',
                    help="Display pacback version and cache info.")
parser.add_argument("-i", "--info", metavar=('1'),
                    help="Print information about a restore point.")
parser.add_argument("-df", "--diff", nargs=2, metavar=('1 2'),
                    help="Compare any two restore points or snapshots.")
parser.add_argument("-ls", "--list", action='store_true',
                    help="List information about all existing restore points and snapshots.")
# Will Add This At Some Point
#  parser.add_argument("-tl", "--timeline", action='store_true',
                    #  help="Calculate a timeline of changes between snapshots.")

################################
# Safely Init the Environment
##############################

args = parser.parse_args()
config = session.load_config()
session.lock(config)
session.setup(config)
signal.signal(signal.SIGINT, partial(session.sig_catcher, config))

##########################
# Display Info For User
########################

if args.version:
    print('Pacback Version: ' + config['version'])
    print('PAF Version: ' + config['paf'])
    cache = utils.cache_size(config)
    print('Reported Cache Size: ' + cache[0])
    print('Actual Cache Size: ' + cache[1])

if args.info:
    if re.findall(r'^(rp[0-9][0-9]$|rp[0-9]$|ss[0-9][0-9]$|ss[0-9])$', args.info):
        user.print_info(config, args.info)
    else:
        paf.prError('Invalid Input: Argument Must Specify Type and Number! (IE: rp02 or ss4)')

if args.list:
    user.list_all(config)

if args.diff:
    if all(re.search(r'^(rp[0-9][0-9]$|rp[0-9]$|ss[0-9][0-9]$|ss[0-9])$', d) for d in args.diff):
        user.diff_meta(config, args.diff[0], args.diff[1])
    else:
        paf.prError('Invalid Input: Argument Must Specify Type and Number! (IE: rp02 or ss4)')

######################
# Creation Commands
####################

if args.create_rp:
    if re.match(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.create_rp):
        create.restore_point(config, args.create_rp, args.full_rp, args.add_dir, args.no_confirm, args.label)
    else:
        paf.prError('Invalid Input: Argument Must Be An Integer Between 0-99!')

elif args.hook:
    create.snapshot(config, args.label)

#########################
# Restoration Commands
#######################

if args.downgrade_pkg:
    if not all(re.search(r'^(s*[0-9])', pkg) for pkg in args.downgrade_pkg):
        restore.packages(config, args.downgrade_pkg)
    else:
        paf.prError('Invalid Input: Package Names Should NOT Start With Digits!')

elif args.snapshot:
    if re.match(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.snapshot):
        restore.snapshot(config, args.snapshot)
    else:
        paf.prError('Invalid Input: Argument Must Be An Integer Between 0-99!')

elif args.restore_point:
    if re.match(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.restore_point):
        restore.restore_point(config, args.restore_point)
    else:
        paf.prError('Invalid Input: Argument Must Be An Integer Between 0-99!')

elif args.date:
    if re.match(r'([12]\d{3}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01]))', args.date):
        restore.archive_date(config, args.date)
    else:
        paf.prError('Invalid Input: Date Must Be in YYYY/MM/DD Format!')

#####################
# Pacback Utilities
###################

if args.remove:
    if re.findall(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.remove):
        user.remove_rp(config, args.remove, args.no_confirm)
    else:
        paf.prError('Invalid Input: Argument Must Be An Integer Between 0-99!')

elif args.clean:
    user.clean_cache(config, args.no_confirm)

elif args.install_hook:
    utils.pacman_hook(True, config)

elif args.remove_hook:
    utils.pacman_hook(False, config)

# Safely Close the Environment
session.unlock(config)
