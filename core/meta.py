#! /usr/bin/env python3
import re
import os

# Local Modules
import paf
import utils
import session


def find_in(meta_data, key):
    '''
    Fetches the value for a 'key: value' entry in the meta data.
    '''
    for m in meta_data:
        if m.split(':')[0].lower() == key.lower():
            value = ':'.join(m.split(':')[1:]).strip()
            return value
    return 'None'


######################################
# Read A Meta Data File Into A Dict
####################################

def read(config, meta_path):
    '''
    Reads the raw human readable meta file into a python dictionary.
    Uses meta.find_in() and paf.read_between() to the find values.
    '''
    meta_raw = paf.read_file(meta_path)

    meta_dict = {
            'version': find_in(meta_raw, 'Version'),
            'type': find_in(meta_raw, 'Type'),
            'stype': find_in(meta_raw, 'SubType'),
            'date': find_in(meta_raw, 'Date Created'),
            'time': find_in(meta_raw, 'Time Created'),
            'pkgs_installed': find_in(meta_raw, 'Packages Installed'),
            'pkg_list': set(paf.read_between(' Pacman List ', '<Endless>', meta_raw, re_flag=True)),
            'label': find_in(meta_raw, 'Label'),

            # Full Values
            'pkgs_cached': find_in(meta_raw, 'Packages Cached'),
            'cache_size': find_in(meta_raw, 'Package Cache Size'),
            'dir_list': set(paf.read_between(' Dir List ', ' Pacman List ', meta_raw, re_flag=True)[:-1]),
            'file_count': find_in(meta_raw, 'Dir File Count'),
            'file_raw_size': find_in(meta_raw, 'Dir Raw Size'),
            'tar_size': find_in(meta_raw, 'Tar Compressed Size'),
            'tar_csum': find_in(meta_raw, 'Tar Checksum')}

    return meta_dict


##############################
# Compare Two Package Lists
############################

def compare(config, old_pkgs, new_pkgs):
    '''
    Compares two list of packages and returns a dictionary containing
    changed, added, and removed packages. Also returns a formated list
    for searching with utils.search_cache().
    '''

    # Strips the Version
    old_pkg_strp = {pkg.split(' ')[0] for pkg in old_pkgs}
    current_pkg_strp = {pkg.split(' ')[0] for pkg in new_pkgs}
    added_pkgs = set(current_pkg_strp - old_pkg_strp)
    removed_pkgs = set(old_pkg_strp - current_pkg_strp)

    # Clears Removed Packages From changed_pkgs
    c_plus_r = set(old_pkgs - new_pkgs)
    search = ('|'.join(list(re.escape(pkg) for pkg in removed_pkgs)))
    changed_pkgs = set()
    for pkg in c_plus_r:
        if not re.findall(search, pkg.lower()):
            changed_pkgs.add(pkg)

    results = {
            'search': paf.replace_spaces(c_plus_r, '-'),
            'c_pkgs': changed_pkgs,
            'a_pkgs': added_pkgs,
            'r_pkgs': removed_pkgs}

    return results


#########################################
# Checksum And Validate Meta Integrity
#######################################

def validate(config, info):
    '''
    Checks if a meta file has become corrupted or is missing.
    '''
    fname = 'meta.validate(' + info['type'] + info['id'] + ')'

    if os.path.exists(info['meta']) and os.path.exists(info['meta_md5']):
        paf.write_to_log(fname, 'Meta File and Meta Checksum Are Present', config['log'])
        csum = str(open(info['meta_md5']).read()).strip()
        msum = str(paf.checksum_file(info['meta'])[1]).strip()

        if csum == msum:
            paf.write_to_log(fname, 'Meta Passed Checksum', config['log'])
            return

        elif csum != msum:
            paf.write_to_log(fname, 'Meta Checksum FAILED!', config['log'])
            paf.prError(info['TYPE'] + ' ' + info['id'] + ' Has Failed its Checksum Check!')
            paf.prError('This ' + info['TYPE'] + ' Has Likely Become Corrupt!')

            if paf.yn_frame('Do You Want to Remove This ' + info['TYPE'] + ' Now?') is True:
                utils.remove_id(config, info)
                session.abort(fname, 'User Deleted Corrupted ' + info['TYPE'],
                        info['TYPE'] + ' Was Removed. Exiting Now!', config)
            else:
                session.abort(fname, 'User Choose NOT to Remove Corrupted ' + info['TYPE'],
                        'Okay, Leaving the ' + info['TYPE'] + ' Alone. Exiting Now!', config)

    elif os.path.exists(info['meta']) and not os.path.exists(info['meta_md5']):
        paf.write_to_log(fname, 'Meta File is Missing its Checksum File!', config['log'])
        paf.prError(info['TYPE'] + ' ' + info['id'] + ' is Missing a Checksum!')

        if paf.yn_frame('Do You Still Want To Continue?') is False:
            session.abort(fname, 'User Exited Due to Missing Checksum File',
                    'Okay, Aborting Due to Missing Checksum', config)
        else:
            paf.write_to_log(fname, 'User Choose To Continue Even Though The Checksum is Missing', config['log'])
            return


#############################
# Higher Level 'API' Calls
###########################

def compare_meta(config, old_meta, new_meta):
    return compare(config, old_meta['pkg_list'], new_meta['pkg_list'])


def compare_now(config, old_meta):
    return compare(config, old_meta['pkg_list'], utils.pacman_Q())
