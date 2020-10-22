#! /usr/bin/env python3
import os
import datetime as dt
from rich.table import Table
from rich.console import Console

# Local Modules
import paf
import meta
import utils


#########################
# Remove Restore Point
#######################

def remove_rp(config, num, nc):
    fname = 'user.remove_rp(' + str(num) + ')'

    rm_info = {
            'id': str(num).zfill(2),
            'type': 'rp',
            'TYPE': 'Restore Point',
            'meta': config['rp_paths'] + '/rp' + str(num).zfill(2) + '.meta',
            'meta_md5': config['rp_paths'] + '/.rp' + str(num).zfill(2) + '.md5',
            'path': config['rp_paths'] + '/rp' + str(num).zfill(2)
            }

    if nc is False:
        if paf.yn_frame('Are You Sure You Want to Remove This Restore Point?') is False or None:
            return

    utils.remove_id(config, rm_info)
    paf.prSuccess('Restore Point Removed!')
    paf.write_to_log(fname, 'Removed Restore Point ' + num, config['log'])


#########################################
# List All Snapshot and Restore Points
#######################################

def list_all(config):
    '''
    This presents all the currently created restore points and snapshots.
    '''
    rps = sorted(m for m in paf.scan_dir(config['rp_paths'])[0] if m.endswith('.meta'))
    sss = sorted(m for m in paf.scan_dir(config['ss_paths'])[0] if m.endswith('.meta'))

    # Get Restore Point Data
    rps_data = list()
    for m in rps:
        num = m[-7] + m[-6]
        d = meta.read(config, m)
        rps_data.append(num + ' - Pkgs: ' + d['pkgs_installed'] + ' Created: ' + d['date'])
    if not rps_data:
        rps_data.append('NONE')

    # Get Snapshot Data
    sss_data = list()
    for m in sss:
        num = m[-7] + m[-6]
        d = meta.read(config, m)
        sss_data.append(num + ' - Pkgs: ' + d['pkgs_installed'] + ' Created: ' + d['date'])
    if not sss_data:
        sss_data.append('NONE')

    # Build Table
    t = Table(title='Pacback Restore Points and Snapshots')
    t.add_column('Restore Points', justify='left', style='white', no_wrap=True)
    t.add_column('Snapshots', justify='right', style='blue', no_wrap=True)

    # This Builds The Table Output Line by Line
    counter = 0
    for x in range(0, max(len(l) for l in [rps_data, sss_data])):
        try:
            a = str(rps_data[counter])
        except Exception:
            a = ''

        try:
            b = str(sss_data[counter])
        except Exception:
            b = ''

        t.add_row(a, b)
        counter += 1

    console = Console()
    console.print(t)


########################
# Print Info About ID
######################

def print_info(config, selction):
    '''
    This function processes a meta data file without validating it,
    then compares the file to now and presents the results in a table.
    This acts as a 'dry run' of sorts not only showing info in the meta data
    file but also showing what would be changed if actually restored.
    The code is kind of gross but I'm not inclined to fix it.
    '''
    # Build Base Vars
    m_num = selction[2:].zfill(2)

    if selction.startswith('rp'):
        m_path = config['rp_paths'] + '/rp' + m_num + '.meta'
    elif selction.startswith('ss'):
        m_path = config['ss_paths'] + '/ss' + m_num + '.meta'

    # Return if Missing
    if not os.path.exists(m_path):
        return paf.prError(selction.upper() + ' Was NOT Found!')

    # Load Meta and Compare
    m = meta.read(config, m_path)
    compare = meta.compare_now(config, m)

    # Build Data For Table
    c1 = [
        'Installed Packages: ' + m['pkgs_installed'],
        'Date: ' + m['date'],
        'Time: ' + m['time'],
        'Pacback Version: ' + m['version'],
        'User Label: ' + m['label']
    ]

    if m['stype'] == 'Full':
        c1.append('Packages Cached: ' + m['pkgs_cached'])
        c1.append('Cache Size: ' + m['cache_size'])

    if m['dir_list']:
        c1.append('')
        c1.append('File Count: ' + m['file_count'])
        c1.append('Raw File Size: ' + m['file_raw_size'])
        c1.append('Compressed Size: ' + m['tar_size'])
        c1.append('')
        c1.append('Directory List')
        c1.append('--------------')
        for d in m['dir_list']:
            c1.append(d)

    c2 = list(compare['c_pkgs'])
    if not c2:
        c2.append('NONE')

    c3 = list(compare['a_pkgs'])
    if not c3:
        c3.append('NONE')

    c4 = list(compare['r_pkgs'])
    if not c4:
        c4.append('NONE')

    # Build Table
    t = Table(title=m['type'] + ' #' + m_num)
    t.add_column('Meta Info', justify='left', style='bold white', no_wrap=True)
    t.add_column('Changed Since Creation', justify='center', style='yellow', no_wrap=True)
    t.add_column('Added Since Creation', justify='center', style='green', no_wrap=True)
    t.add_column('Removed Since Creation', justify='center', style='red', no_wrap=True)

    # This Builds The Table Output Line by Line
    counter = 0
    for x in range(0, max(len(l) for l in [c1, c2, c3, c4])):
        try:
            a = str(c1[counter])
        except Exception:
            a = ''

        try:
            b = str(c2[counter])
        except Exception:
            b = ''

        try:
            c = str(c3[counter])
        except Exception:
            c = ''

        try:
            d = str(c4[counter])
        except Exception:
            d = ''

        t.add_row(a, b, c, d)
        counter += 1

    console = Console()
    console.print(t)


####################################
# Compare Two IDs Defined By User
##################################

def diff_meta(config, meta1, meta2):
    '''
    This function processes two meta data files without validating either.
    It will compare meta1 as base compared to meta2 then present the results in a table.
    The code is kind of gross but I'm not inclined to fix it.
    '''
    # Build Base Vars
    m1_num = meta1[2:].zfill(2)
    m2_num = meta2[2:].zfill(2)

    if meta1.startswith('rp'):
        m1_path = config['rp_paths'] + '/rp' + m1_num + '.meta'
    elif meta1.startswith('ss'):
        m1_path = config['ss_paths'] + '/ss' + m1_num + '.meta'

    if meta2.startswith('rp'):
        m2_path = config['rp_paths'] + '/rp' + m2_num + '.meta'
    elif meta2.startswith('ss'):
        m2_path = config['ss_paths'] + '/ss' + m2_num + '.meta'

    # Return if Missing
    if not os.path.exists(m1_path):
        return paf.prError(meta1.upper() + ' Was NOT Found!')

    if not os.path.exists(m2_path):
        return paf.prError(meta2.upper() + ' Was NOT Found!')

    # Read Meta Data
    m1 = meta.read(config, m1_path)
    m2 = meta.read(config, m2_path)
    compare = meta.compare_meta(config, m1, m2)

    # Build Info For Table
    c1 = [
        'Installed Packages: ' + m1['pkgs_installed'],
        'Date: ' + m1['date'],
        'Time: ' + m1['time'],
        'Pacback Version: ' + m1['version'],
        'User Label: ' + m1['label']
    ]

    if m1['stype'] == 'Full':
        c1.append('Packages Cached: ' + m1['pkgs_cached'])
        c1.append('Cache Size: ' + m1['cache_size'])

    if m1['dir_list']:
        c1.append('')
        c1.append('File Count: ' + m1['file_count'])
        c1.append('Raw File Size: ' + m1['file_raw_size'])
        c1.append('Compressed Size: ' + m1['tar_size'])
        c1.append('')
        c1.append('Directory List')
        c1.append('--------------')
        for d in m1['dir_list']:
            c1.append(d)

    c2 = list(compare['c_pkgs'])
    if not c2:
        c2.append('NONE')

    c3 = list(compare['a_pkgs'])
    if not c3:
        c3.append('NONE')

    c4 = list(compare['r_pkgs'])
    if not c4:
        c4.append('NONE')

    c5 = ['Installed Packages: ' + m2['pkgs_installed'],
            'Date: ' + m2['date'],
            'Time: ' + m2['time'],
            'Pacback Version: ' + m2['version'],
            'User Label: ' + m2['label']]

    if m2['stype'] == 'Full':
        c5.append('Packages Cached: ' + m2['pkgs_cached'])
        c5.append('Cache Size: ' + m2['cache_size'])

    if m2['dir_list']:
        c5.append('')
        c5.append('File Count: ' + m2['file_count'])
        c5.append('Raw File Size: ' + m2['file_raw_size'])
        c5.append('Compressed Size: ' + m2['tar_size'])
        c5.append('')
        c5.append('Directory List')
        c5.append('--------------')
        for d in m2['dir_list']:
            c5.append(d)

    # Build Table
    t = Table(title=m1['type'] + ' #' + m1_num + ' --------> ' + m2['type'] + ' #' + m2_num)
    t.add_column(meta1.upper() + ' Meta Info', justify='left', style='bold white', no_wrap=True)
    t.add_column('Changed Since Creation', justify='center', style='yellow', no_wrap=True)
    t.add_column('Added Since Creation', justify='center', style='green', no_wrap=True)
    t.add_column('Removed Since Creation', justify='center', style='red', no_wrap=True)
    t.add_column(meta2.upper() + ' Meta Info', justify='right', style='bold white', no_wrap=True)

    # This Builds The Table Output Line by Line
    counter = 0
    for x in range(0, max(len(l) for l in [c1, c2, c3, c4, c5])):
        try:
            a = str(c5[counter])
        except Exception:
            a = ''

        try:
            b = str(c2[counter])
        except Exception:
            b = ''

        try:
            c = str(c3[counter])
        except Exception:
            c = ''

        try:
            d = str(c4[counter])
        except Exception:
            d = ''

        try:
            e = str(c5[counter])
        except Exception:
            e = ''

        t.add_row(a, b, c, d, e)
        counter += 1

    console = Console()
    console.print(t)


##########################
# Better Cache Cleaning
########################

def clean_cache(config, nc):
    '''
    This provides automated cache cleaning using pacman, paccache, and pacback.
    '''
    fname = 'utils.clean_cache()'
    paf.prBold('Starting Advanced Cache Cleaning...')
    paf.write_to_log(fname, 'Starting Advanced Cache Cleaning...', config['log'])
    print('')

    if nc is True or paf.yn_frame('Do You Want To Uninstall Orphaned Packages?') is True:
        os.system('/usr/bin/pacman -R $(/usr/bin/pacman -Qtdq)')
        paf.write_to_log(fname, 'Removed Orphaned Packages', config['log'])

    if nc is True or paf.yn_frame('Do You Want To Remove Old Versions of Installed Packages?') is True:
        os.system('/usr/bin/paccache -rk ' + str(config['keep_versions']))
        paf.write_to_log(fname, 'Removed Old Package Versions', config['log'])

    if nc is True or paf.yn_frame('Do You Want To Remove Cached Orphans?') is True:
        os.system('/usr/bin/paccache -ruk0')
        paf.write_to_log(fname, 'Removed Cached Orphans', config['log'])

    if nc is True or paf.yn_frame('Do You Want To Check For Old Pacback Restore Points?') is True:
        paf.write_to_log(fname, 'Starting Search For Old Restore Points...', config['log'])
        meta_paths = sorted(f for f in paf.find_files(config['rp_paths']) if f.endswith(".meta"))

        today = dt.datetime.now().strftime("%Y/%m/%d")
        t_split = (today.split('/'))
        today_dt = dt.date(int(t_split[0]), int(t_split[1]), int(t_split[2]))

        for m in meta_paths:
            rp_info = {
                    'id': m[-7] + m[-6],
                    'type': 'rp',
                    'TYPE': 'Restore Point',
                    'meta': m,
                    'meta_md5': config['rp_paths'] + '/.rp' + m[-7] + m[-6] + '.md5',
                    'path': config['rp_paths'] + '/rp' + m[-7] + m[-6],
                    'pkgcache': config['rp_paths'] + '/rp' + m[-7] + m[-6] + '/pkg-cache'}

            # Format Dates for Compare
            m_dict = meta.read(config, m)
            o_split = (m_dict['date'].split('/'))
            old_dt = dt.date(int(o_split[0]), int(o_split[1]), int(o_split[2]))

            # Check How Old Restore Point Is
            days = (today_dt - old_dt).days
            if days > config['old_rp']:
                paf.prWarning('Failed: ' + rp_info['TYPE'] + ' ' + rp_info['id'] + ' Is ' + str(days) + ' Days Old!')
                paf.write_to_log(fname, rp_info['TYPE'] + ' ' + rp_info['id'] + ' Is ' + str(days) + ' Days Old!', config['log'])
                if paf.yn_frame('Do You Want to Remove This ' + rp_info['TYPE'] + '?') is True:
                    utils.remove_id(config, rp_info)
                    paf.prSuccess('Restore Point Removed!')
                else:
                    paf.write_to_log(fname, 'User Declined Removal of ' + rp_info['TYPE'] + ' ' + rp_info['id'], config['log'])

            else:
                paf.prSuccess('Passed: ' + rp_info['TYPE'] + ' ' + rp_info['id'] + ' Is ' + str(days) + ' Days Old')
                paf.write_to_log(fname, rp_info['TYPE'] + ' ' + rp_info['id'] + ' Is ' + str(days) + ' Days Old', config['log'])

    paf.write_to_log(fname, 'Finished Advanced Cache Cleaning', config['log'])


#  def ss_timeline(config, num1, num2):
    #  '''
    #  In the future I would like to add something that looks like this.
    #  '''
    #   ---------------------  NOW  -----------------------
    #   Time: -xxx days | Packages: xxxx | Kernel: xx.xx.xx
    #   ---------------------------------------------------
    #          ^                ^                ^
    #          |                |                |
    #     Changed: xxx     Removed: xxx     Added: xxx
    #          |                |                |
    #   --------------------- SS 00 -----------------------
    #   Time: -xxx days | Packages: xxxx | Kernel: xx.xx.xx
    #   ---------------------------------------------------
    #          ^                ^                ^
    #          |                |                |
    #     Changed: xxx     Removed: xxx     Added: xxx
    #          |                |                |
    #   --------------------- SS 01 -----------------------
    #   Time: -xxx days | Packages: xxxx | Kernel: xx.xx.xx
    #   ---------------------------------------------------
    #          ^                ^                ^
    #          |                |                |
    #     Changed: xxx     Removed: xxx     Added: xxx
    #          |                |                |
    #   --------------------- SS 02 -----------------------
    #   Time: -xxx days | Packages: xxxx | Kernel: xx.xx.xx
    #   ---------------------------------------------------
    #          ^                ^                ^
    #          |                |                |
    #     Changed: xxx     Removed: xxx     Added: xxx
    #          |                |                |
    #   --------------------- SS 03 -----------------------
    #   Time: -xxx days | Packages: xxxx | Kernel: xx.xx.xx
    #   ---------------------------------------------------
