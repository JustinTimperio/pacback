#! /usr/bin/env python3
import os
import sys
import datetime as dt

# Local Modules
import paf


#######################
# Session Management
#####################

def lock(config):
    '''
    This checks if pacback is being run by root or sudo, then
    checks if an active session is already in progress.
    '''
    fname = 'session.lock()'
    if paf.am_i_root() is False:
        sys.exit('Critical Error: This Command Must Be Run As Root!')

    if os.path.exists(config['slock']):
        sys.exit('Critical Error! Pacback Already Has An Active Session Running.')

    paf.start_log(fname, config['log'])
    paf.write_to_log(fname, 'Passed Root Check', config['log'])
    os.system('touch ' + config['slock'])
    paf.write_to_log(fname, 'Started Active Session', config['log'])


def unlock(config):
    '''
    Removes the session lock defined by config['slock'].
    This releases the lock that was created by session.lock()
    '''
    fname = 'session.unlock()'
    paf.rm_file(config['slock'], sudo=False)
    paf.write_to_log(fname, 'Ended Active Session', config['log'])
    paf.end_log(fname, config['log'], config['log_length'])


def abort_fail(func, output, message, config):
    '''
    This is a surrogate function for other functions to safely abort runtime during a failure.
    It reports the func sending the kill signal as the origin, rather than session.abort().
    '''
    paf.write_to_log(func, 'FAILURE: ' + output, config['log'])
    unlock(config)
    paf.prError(message)
    sys.exit()


def abort(func, output, message, config):
    '''
    This is a surrogate function for other functions to safely abort runtime.
    It reports the func sending the kill signal as the origin, rather than session.abort().
    '''
    paf.write_to_log(func, 'ABORT: ' + output, config['log'])
    unlock(config)
    paf.prBold(message)
    sys.exit()


def sig_catcher(log, signum, frame):
    '''
    This is called whenever a exit signal is received.
    It lets pacback exit somewhat safely during the event of a kill.
    '''
    abort_fail('SIGINT', 'Caught SIGINT ' + str(signum), '\nAttempting Clean Exit', log)


#############################
# Snapshot Hook Management
###########################

def hlock_start(config):
    '''
    This starts a hook lock overwriting the previous lock.
    This should be triggered at the end of a successful --hook run.
    '''
    fname = 'session.hlock_start(' + str(config['hook_cooldown']) + ')'
    stime = 'Created: ' + dt.datetime.now().strftime("%Y:%m:%d:%H:%M:%S"),
    paf.export_iterable(config['hlock'], [stime])
    paf.write_to_log(fname, 'Created Hook Lock With ' + str(config['hook_cooldown']) + ' Second Cooldown', config['log'])


def hlock_kill(config):
    '''
    Removes the hook lock file without any checks.
    This currently isn't used anywhere, it's just future-proofing.
    '''
    fname = 'session.hlock_kill()'
    paf.rm_file(config['hlock'], sudo=False)
    paf.write_to_log(fname, 'Force Ended Hook Lock!', config['log'])


def hlock_check(config):
    '''
    If config['hlock'] exists it checks if it was created less than
    the number of seconds defined by config['hook_cooldown'].
    '''
    fname = 'session.hlock_check(' + str(config['hook_cooldown']) + ')'
    if os.path.exists(config['hlock']):
        f = str(open(config['hlock'], 'r').readlines())[11:-4]
        f = f.split(':')
        hc = dt.datetime(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]), int(f[5]))
        sec_dif = (dt.datetime.now() - hc).total_seconds()

        if sec_dif > config['hook_cooldown']:
            paf.write_to_log(fname, 'Passed Cooldown Check', config['log'])
        else:
            abort(fname, 'A Hook Lock Was Created ' + str(sec_dif) + ' Ago!',
                    'Aborting: The Last Snapshot Was Created Less Than ' + str(config['hook_cooldown']) + ' Seconds Ago!', config)
    else:
        paf.write_to_log(fname, 'Passed Check, No Previous Lock Found', config['log'])


##########################
# Load Config User File
########################

def load_config():
    '''
    Loads in user config options from /etc/pacback.conf and returns results
    '''
    mandatory = ['hook_cooldown', 'max_ss', 'reboot']
    optional = ['old_rp', 'keep_versions', 'reboot_offset', 'log_length', 'basepath', 'rp_paths', 'ss_paths']
    default = {
        'version': '2.0.1',
        'paf': '4f25050',
        'log': '/var/log/pacback.log',
        'slock': '/tmp/pacback_session.lck',
        'hlock': '/tmp/pacback_hook.lck',
        'basepath': '/var/lib/pacback',
        'rp_paths': '/var/lib/pacback/restore-points',
        'ss_paths': '/var/lib/pacback/snapshots',
        'hook_cooldown': 300,
        'max_ss': 25,
        'log_length': 0,  # 0 Sets the Log to Infinite
        'keep_versions': 3,
        'old_rp': 180,
        'reboot': True,
        'reboot_offset': 5
        }

    if os.path.exists('/etc/pacback.conf'):
        user_config = paf.read_config('/etc/pacback.conf', mandatory, optional)
        default.update(user_config)

    return default


##################
# Setup Pacback
################

def setup(config):
    '''
    Check if all the need folders and files are present for a active session
    '''
    fname = 'session.setup()'
    # Init Base Paths if First Run
    if os.path.exists(config['basepath']) is False:
        paf.mk_dir(config['basepath'], sudo=False)
        paf.write_to_log(fname, 'Created Basepath Folder at ' + config['basepath'], config['log'])

    if os.path.exists(config['rp_paths']) is False:
        paf.mk_dir(config['rp_paths'], sudo=False)
        paf.write_to_log(fname, 'Created Restore Point Folder at ' + config['rp_paths'], config['log'])

    if os.path.exists(config['ss_paths']) is False:
        paf.mk_dir(config['ss_paths'], sudo=False)
        paf.write_to_log(fname, 'Created Snapshot Folder at ' + config['ss_paths'], config['log'])

    if os.path.exists('/etc/pacback/config') is False:
        paf.write_to_log(fname, 'User Config File Is Missing!', config['log'])
