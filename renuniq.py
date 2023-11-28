#!/usr/bin/env python3
"""Rename files following a user-defined template.

It can rename file including their modification dates, or by keeping enough of the end of
the name to make it unique, or a myriad of other ways.
"""

__author__ = 'Dan Fandrich'
__version__ = '2-dev'
__license__ = 'GPLv2+'

import getopt
import logging
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from typing import Dict, List, Mapping

LICENSE = """\
Copyright 2006-2023 by Daniel Fandrich <dan@coneharvesters.com>
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

LOG_LEVEL = logging.ERROR  # set to logging.DEBUG for debug logging

DEFAULT_CONFIG = {}  # type: dict[str, str]
DEFAULT_CONFIG['default_template'] = '%Y%m%d_%{UNIQSUFF}'
DEFAULT_CONFIG['default_template_single'] = DEFAULT_CONFIG['default_template']
DEFAULT_CONFIG['default_template_desc'] = '%Y%m%d_%{DESC}_%{UNIQSUFF}'
DEFAULT_CONFIG['default_template_desc_single'] = DEFAULT_CONFIG['default_template_desc']


def read_config(config: Dict[str, str]):
    'Read the configuration files.'
    home = os.environ['HOME'] if 'HOME' in os.environ else '/'
    if 'XDG_CONFIG_HOME' in os.environ:
        xdg_dir = os.environ['XDG_CONFIG_HOME']
    else:
        xdg_dir = os.path.join(home, '.config')

    # Reading XDG config dir first, then home dir config
    for config_path in [os.path.join(xdg_dir, 'renuniqrc'), os.path.join(home, '.renuniqrc')]:
        try:
            with open(config_path) as f:
                logging.debug(f'reading config {config_path}')
                exec(f.read(), None, config)
        except FileNotFoundError:
            pass  # Ignore the case where the file doesn't exist


def getmtime(fn: str) -> time.struct_time:
    return time.localtime(os.stat(fn)[stat.ST_MTIME])


class Substitute(dict):
    'Substitute variables for their keys. Looks much like a dict.'

    def __init__(self, d: dict, num: int, num_width: int):
        dict.__init__(self, d)
        self.number = num
        self.num_width = num_width

    def __getitem__(self, attr: str) -> str:
        if self.__contains__(attr):
            return dict.__getitem__(self, attr)
        elif attr == 'NUM':
            attr = f'NUM{self.num_width}'

        if attr == 'NUM1':
            return f'{self.number:01d}'
        elif attr == 'NUM2':
            return f'{self.number:02d}'
        elif attr == 'NUM3':
            return f'{self.number:03d}'
        elif attr == 'NUM4':
            return f'{self.number:04d}'
        elif attr == 'NUM5':
            return f'{self.number:05d}'
        elif attr == 'NUM6':
            return f'{self.number:06d}'
        raise KeyError(attr)


def substvars(s: str, substdict: Mapping[str, str]) -> str:
    'Substitute %{foo} strings in s with the key in substdict'
    newpieces = []
    laststart = 0
    for i in re.finditer('%{([A-Za-z_0-9]*)}', s):
        varname = i.group(1)
        varvalue = substdict[varname]
        newpieces.append(s[laststart:i.span()[0]])
        newpieces.append(varvalue)
        laststart = i.span()[1]
    newpieces.append(s[laststart:])
    return ''.join(newpieces)


def make_subst_dict(fn: str, prefix: str, descriptor: str) -> Dict[str, str]:
    'Create a substitution dictionary from the file information'
    base = os.path.basename(fn)
    direct = os.path.dirname(fn)
    # Add a trailing / if necessary
    direct = os.path.join(direct, '')
    endname = base[len(prefix):]
    notext, ext = os.path.splitext(base)
    logging.debug(f'endname={endname}')
    logging.debug(f'ext={ext}')

    subst = {}  # type: dict[str, str]
    subst['UNIQSUFF'] = endname
    subst['DIR'] = direct
    subst['NAME'] = base
    subst['PATH'] = fn
    subst['EXT'] = ext
    subst['NOTEXT'] = notext
    subst['DESC'] = descriptor
    return subst


def safemove(fr: str, to: str):
    'Safely move a file, potentially across filesystems'
    try:
        rc = subprocess.run(['mv', fr, to])
        if rc.returncode:
            raise PermissionError  # The most likely cause of error, but may be wrong
    except FileNotFoundError:
        # 'mv' couldn't be found. Fall back to Python-native move. This is inferior, as the
        # comments for the function admit, but it's better than nothing.
        shutil.move(fr, to)


def usage(config: Dict[str, str]):
    'Show program usage information'
    print('Usage: renuniq [-?hmnwLV] [-c countstart] [-d descriptor] [-i interval] [-t template] '
          'filename...')
    print('  -c N Start the sequential count at this integer')
    print('  -d X Set the value of the substitution variable %{DESC}')
    print('  -i N Increment the count by this integer')
    print('  -m   Turn off strftime variable substitution in template')
    print("  -n   Print what would be executed but don't actually do it")
    print('  -t X Set the template of the renamed file name')
    print('  -w   Use the time now instead of mtime for strftime format strings')
    print('  -L   Display program license')
    print('  -V   Display program version')
    print(textwrap.dedent("""\
          Substitutions:
            %{UNIQSUFF} the unique suffix in the list of all files
            %{DIR}      directory including trailing slash
            %{NAME}     file name
            %{PATH}     full name
            %{EXT}      file extension (section including the last .)
            %{NOTEXT}   file name up to the last .
            %{DESC}     user-specified descriptor
            %{NUM}      a 0-padded positive increasing integer of automatic width
            %{NUMn}     a 0-padded positive increasing integer of width n (1<=n<=6)
          strftime parameters on the modification time are also allowed, e.g. %Y, %m, %d"""))
    print(f'Default template with no descriptor given: {config["default_template"]}')
    if config['default_template_single'] != config['default_template']:
        print(f'...for only a single file argument: {config["default_template_single"]}')
    print(f'Default template with descriptor given:    {config["default_template_desc"]}')
    if config['default_template_desc_single'] != config['default_template_desc']:
        print(f'...for only a single file argument: {config["default_template_desc_single"]}')


def rename(argv: List[str]):
    'Rename files according to given criteria'
    try:
        optlist, args = getopt.getopt(argv[1:], '?c:d:hi:mnt:wLV')
    except getopt.error:
        logging.critical('Unsupported command-line parameter')
        return 1

    @dataclass
    class Opts:
        names: List[str]
        show_usage: bool = False
        template: str = ''
        descriptor: str = ''
        strftime_enable: bool = True
        dry_run: bool = False
        count: int = 1
        interval: int = 1
        use_time_now: bool = False

    opts = Opts(names=args)

    for opt, arg in optlist:
        if opt == '-h' or \
           opt == '-?':
            opts.show_usage = True

        elif opt == '-c':
            try:
                opts.count = int(arg)
            except ValueError:
                logging.critical('-c takes a numeric argument')
                return 1

        elif opt == '-d':
            opts.descriptor = arg

        elif opt == '-i':
            try:
                opts.interval = int(arg)
            except ValueError:
                logging.critical('-i takes a numeric argument')
                return 1

        elif opt == '-m':
            opts.strftime_enable = not opts.strftime_enable

        elif opt == '-n':
            opts.dry_run = not opts.dry_run

        elif opt == '-t':
            opts.template = arg

        elif opt == '-w':
            opts.use_time_now = True

        elif opt == '-L':
            print(LICENSE, end='')
            return 0

        elif opt == '-V':
            print(f'renuniq ver. {__version__}')
            return 0

    # Read the config file before displaying help
    config = DEFAULT_CONFIG.copy()
    read_config(config)

    if not opts.names:
        opts.show_usage = True

    if opts.show_usage:
        usage(config)
        return 1

    if not opts.template:
        if opts.descriptor:
            if len(opts.names) == 1:
                opts.template = config['default_template_desc_single']
            else:
                opts.template = config['default_template_desc']
        else:
            if len(opts.names) == 1:
                opts.template = config['default_template_single']
            else:
                opts.template = config['default_template']

    # What is the shortest suffix that will make a new name unique?
    pathprefix = os.path.commonprefix(opts.names)
    dirprefix = os.path.dirname(pathprefix)
    prefix = os.path.basename(pathprefix)
    if dirprefix != os.path.dirname(opts.names[0]):
        prefix = ''
    # Renaming a single file is a special case
    if len(opts.names) < 2:
        extpos = prefix.rfind('.')
        prefix = prefix[:extpos] if extpos >= 0 else ''

    logging.debug(f'pathprefix={pathprefix}')
    logging.debug(f'dirprefix={dirprefix}')
    logging.debug(f'prefix={prefix}')

    if opts.strftime_enable and opts.use_time_now:
        times = time.localtime(time.time())

    countmax = opts.count + (opts.interval * (len(opts.names) - 1))
    errors = 0

    # Loop around all files, renaming them
    count = opts.count
    for f in opts.names:
        if opts.strftime_enable and not opts.use_time_now:
            try:
                times = getmtime(f)
            except OSError:
                logging.error(f'Skipping {f} (not readable)')
                errors += 1
                continue

        substitutions = make_subst_dict(f, prefix, opts.descriptor)
        substitute = Substitute(substitutions, count, len(repr(countmax)))
        count += opts.interval

        try:
            # Substitute renuniq variables
            newname = substvars(opts.template, substitute)
        except KeyError as attr:
            logging.error(f'Unknown substitution variable {attr}')
            errors += 1
            continue

        if opts.strftime_enable:
            # Substitute strftime variables
            newname = time.strftime(newname, times)

        if os.path.isabs(newname):
            newpath = newname
        else:
            direct = os.path.dirname(f)
            newpath = os.path.join(direct, newname)

        if os.path.exists(newpath):
            logging.error(f'Skipping {f} ({newpath} already exists)')
            errors += 1
            continue

        print(f'mv {shlex.quote(f)} {shlex.quote(newpath)}')
        if not opts.dry_run:
            # Beware the race condition here between checking for existence and
            # the actual move!
            try:
                safemove(f, newpath)
            except PermissionError:
                logging.error(f'Error renaming {f} to {newpath}')
                errors += 1

    return 1 if errors else 0


def main():
    'Start renuniq from the command-line'
    logging.basicConfig(format='%(filename)s: %(message)s', level=LOG_LEVEL)
    exit(rename(sys.argv))


if __name__ == '__main__':
    main()
