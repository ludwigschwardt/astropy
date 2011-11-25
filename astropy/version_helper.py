# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import division

import imp

from distutils import log

"""
Utilities for generating the version string for Astropy and the version.py
module, which contains version info for the package.

Within the generated astropy.version module, the `major`, `minor`, and `bugfix`
variables hold the respective parts of the version number (bugfix is '0' if
absent). The `release` variable is True if this is a release, and False if this
is a development version of astropy. For the actual version string, use::

    from astropy.version import version

or::

    from astropy import __version__

"""


def _version_split(version):
    """
    Split a version string into major, minor, and bugfix numbers (with bugfix
    optional, defaulting to 0).
    """

    if '-r' in version:
        version = version.split('-r', 1)[0]
    versplit = version.replace('dev', '').split('.')
    major = int(versplit[0])
    minor = int(versplit[1])
    bugfix = 0 if len(versplit) < 3 else int(versplit[2])
    return major, minor, bugfix


def _update_git_devstr(version, dir=None):
    """
    Updates the git revision string if and only if astropy is being imported
    directly from a git working copy.  This ensures that the revision number in
    the version string is accurate.
    """

    try:
        # Quick way to determine if we're in git or not
        devstr = get_git_devstr(sha=True, show_warning=False, dir=dir)
    except OSError:
        return version

    if not devstr:
        # Probably not in git so just pass silently
        return version

    if '-git-' in version:
        version_base = version.split('-git-', 1)[0]
    else:
        # By default we prefer to use the revision count for now
        if '-r' in version:
            version_base = version.split('-r', 1)[0]
        else:
            version_base = version
        devstr = get_git_devstr(show_warning=False, dir=dir)

    return version_base + devstr


def get_git_devstr(sha=False, show_warning=True, dir=None):
    """
    Determines the number of revisions in this repository.


    Parameters
    ----------
    sha : bool
        If True, the full SHA1 hash will be at the end of the devstr.
        Otherwise, the total count of commits in the repository will be
        used as a "revision number".

    show_warning : bool
        If True, issue a warning if git returns an error code, otherwise errors
        pass silently.

    dir : str or None
        If a string, specifies the directory to look in to find the git
        repository.  If None, the location of the file this function is in
        is used to infer the git repository location.

    Returns
    -------
    devstr : str
        A string that begins with 'dev' to be appended to the astropy version
        number string, or an empty string if git returns an error.

    """
    import os
    from subprocess import Popen, PIPE
    from warnings import warn

    if dir is None:
        dir = os.path.abspath(os.path.split(__file__)[0])

    if sha:
        cmd = 'rev-parse' # Faster for getting just the hash of HEAD
    else:
        cmd = 'rev-list'

    p = Popen(['git', cmd, 'HEAD'], cwd=dir,
              stdout=PIPE, stderr=PIPE, stdin=PIPE)
    stdout, stderr = p.communicate()

    if p.returncode == 128:
        if show_warning:
            warn('No git repository present! Using default dev version.')
        return ''
    elif p.returncode != 0:
        if show_warning:
            warn('Git failed while determining revision count: ' + stderr)
        return ''

    if sha:
        return '-git-' + stdout.decode('utf-8')[:40]
    else:
        nrev = stdout.decode('utf-8').count('\n')
        return  '-r%i' % nrev


# This is used by setup.py to create a new version.py - see that file for
# details
_frozen_version_py_template = """
# Autogenerated by astropy's setup.py on {timestamp}

import os
from astropy.version_helper import _update_git_devstr

version = _update_git_devstr({verstr!r}, dir=os.path.split(__file__)[0])

major = {major}
minor = {minor}
bugfix = {bugfix}

release = {rel}
debug = {debug}

"""[1:]


def _get_version_py_str(version, release, debug):

    import datetime

    timestamp = str(datetime.datetime.now())
    major, minor, bugfix = _version_split(version)
    return _frozen_version_py_template.format(timestamp=timestamp,
                                              verstr=version,
                                              major=major,
                                              minor=minor,
                                              bugfix=bugfix,
                                              rel=release, debug=debug)


def generate_version_py(packagename, version, release, debug=None):
    """Regenerate the version.py module if necessary."""

    import os
    import sys

    try:
        version_module = __import__(packagename + '.version')
        current_version = version_module.version
        current_release = version_module.release
        current_debug = version_module.debug
    except ImportError:
        version_module = None
        current_version = None
        current_release = None
        current_debug = None

    if debug is None:
        # Keep whatever the current value is, if it exists
        debug = bool(current_debug)

    version_py = os.path.join(packagename, 'version.py')

    if (current_version != version or current_release != release or
        current_debug != debug):
        if '-q' not in sys.argv and '--quiet' not in sys.argv:
            log.set_threshold(log.INFO)
        log.info('Freezing version number to {0}'.format(version_py))

        with open(version_py, 'w') as f:
            # This overwrites the actual version.py
            f.write(_get_version_py_str(version, release, debug))

        if version_module:
            imp.reload(version_module)
