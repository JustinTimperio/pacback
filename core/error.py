#! /usr/bin/env python3
import re

# Local Modules
import paf
import utils


def too_many_pkgs_found(config, parms, found_pkgs, pkg_results):
    """
    This auto resolves some very bizzare edgecases I have run into.
    """
    fname = 'error.too_many_pkgs_found(' + parms['type'] + parms['id'] + ')'
    paf.write_to_log(fname, 'Starting Debug Proccess...', config['log'])

    found_files = utils.trim_pkg_list(paf.basenames(found_pkgs))
    search_files = paf.basenames(pkg_results['search'])
    bad_files = (found_files - search_files)
    paf.write_to_log(fname, 'Debug Proccess Found ' + str(len(bad_files)) + ' Files That Do Not Belong!', config['log'])

    if len(found_files) - len(search_files) == len(bad_files):
        paf.write_to_log(fname, 'Cleaning Found Files...', config['log'])
        bad_files_full = set()

        for b in bad_files:
            for f in found_pkgs:
                if re.search(b, f):
                    bad_files_full.add(f)

        for f in bad_files_full:
            found_pkgs.remove(f)

        paf.write_to_log(fname, 'Debug Process Was Able to Fix All Issues!', config['log'])
        return (True, found_pkgs)

    else:
        paf.write_to_log(fname, 'Debug Process Was NOT Able to Fix All Issues!', config['log'])
        return (False, found_pkgs)
