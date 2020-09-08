#! /usr/bin/env python3

# Local Modules
import paf
import session


def compare(config, target_version):
    '''
    Parses the versions and forks if an upgrade is needed.
    '''
    fname = 'version.compare()'

    # Current Version
    cv_M = int(config['version'].split('.')[0])
    cv_m = int(config['version'].split('.')[1])
    cv_p = int(config['version'].split('.')[2])

    # Target Version
    tv_M = int(target_version.split('.')[0])
    tv_m = int(target_version.split('.')[1])
    tv_p = int(target_version.split('.')[2])

    versions = ((cv_M, cv_m, cv_p), (tv_M, tv_m, tv_p))

    if config['version'] != target_version:
        paf.write_to_log(fname, 'Current Version ' + config['version'] + ' Miss-Matched With ' + target_version, config['log'])

        # Check for Versions <= V1.5
        if tv_M == 1 and tv_m < 5:
            paf.prError('Restore Points Generated Before V1.5.0 Are Not Backwards Compatible With Newer Versions of Pacback!')
            paf.write_to_log(fname, 'Detected a Restore Point Version Generated > V1.5', config['log'])
            session.abort_fail(fname, 'Can\'t Upgrade or Restore Versions Created Before V1.5',
                    'Aborting!', config['log'])

        # Check for V1.5 to V1.7
        elif tv_M == 1 and tv_m > 5:
            paf.write_to_log(fname, 'Detected Alpha Restore Point!', config['log'])

    else:
        paf.write_to_log(fname, 'Both Versions Match ' + config['version'], config['log'])

    return versions
