#!/usr/bin/env python3
# Rename files with their modification date, keeping enough of the end of the
# name to make a unique name
# Dan Fandrich
# Started May 22, 2006
# Bug:
#  renvideos -n _foo_ /tmp/vclp0*.mp4 /tmp/v/vv
# and
#  renvideos -n _foo_ /tmp/vclp0*.mp4 /tmp/w/vv
# should have the same prefix, but don't now
#

import getopt
import os
import re
import stat
import subprocess
import sys
import time

license = '''\
Copyright 2006-2021 by Daniel Fandrich <dan@coneharvesters.com>
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
'''

DEBUG = 0

CONFIG = {}
CONFIG['default_template'] = '%Y%m%d_%{UNIQSUFF}'
CONFIG['default_template_single'] = CONFIG['default_template']
CONFIG['default_template_desc'] = '%Y%m%d_%{DESC}_%{UNIQSUFF}'
CONFIG['default_template_desc_single'] = CONFIG['default_template_desc']


def printerr(msg):
    '''Print an error message to stderr including leading program name

    Displays a message of the form:
     progname: This is an error or warning message
    '''
    fn = os.path.basename(sys.argv[0])
    print(f"{fn}: {msg}", file=sys.stderr)


def getmtime(fn):
    return time.localtime(os.stat(fn)[stat.ST_MTIME])


class Substitute:
    'Substitute variables for their keys. Looks much like a dict.'
    def __init__(self, dict, num=0):
        self.dict = dict
        self.number = num

    def __getitem__(self, attr):
        if attr in self.dict:
            return self.dict[attr]
        elif attr == 'NUM':
            attr = self.dict['num_auto_width']
        if attr == 'NUM1':
            return '%01d' % self.number
        elif attr == 'NUM2':
            return '%02d' % self.number
        elif attr == 'NUM3':
            return '%03d' % self.number
        elif attr == 'NUM4':
            return '%04d' % self.number
        elif attr == 'NUM5':
            return '%05d' % self.number
        elif attr == 'NUM6':
            return '%06d' % self.number
        raise KeyError(attr)

    def nextitem(self):
        self.number = self.number + 1


def substvars(str, substdict):
    'Substitute %{foo} strings in str with the key in substdict'
    newpieces = []
    laststart = 0
    for i in re.finditer('%{([A-Za-z_0-9]*)}', str):
        varname = i.group(1)
        varvalue = substdict[varname]
        newpieces.append(str[laststart:i.span()[0]])
        newpieces.append(varvalue)
        laststart = i.span()[1]
    newpieces.append(str[laststart:])
    return ''.join(newpieces)


def make_subst_dict(fn, prefix, descriptor, num):
    'Create a substitution dictionary from the file information'
    base = os.path.basename(fn)
    direct = os.path.dirname(fn)
    # Add a trailing / if necessary
    direct = os.path.join(direct, '')
    endname = base[len(prefix):]
    extpos = base.rfind('.')
    if extpos >= 0:
        ext = base[extpos:]
        notext = base[:extpos]
    else:
        ext = ''
        notext = base

    dict = {}
    dict['UNIQSUFF'] = endname
    dict['DIR'] = direct
    dict['NAME'] = base
    dict['PATH'] = fn
    dict['EXT'] = ext
    dict['NOTEXT'] = notext
    dict['DESC'] = descriptor
    dict['num_auto_width'] = 'NUM%d' % num
    return dict


def safemove(fr, to):
    'Safely move a file potentially across filesystems'
    rc = subprocess.run(['mv', fr, to])
    if rc.returncode:
        printerr('Error renaming %s to %s' % (fr, to))
    # TODO: change this to use
    #  os.rename(f, newpath)
    # but check for posix.error: (18, 'Cross-device link')
    # and copy it instead


# TODO: fix this so it
# picks up the variables read from in the .renuniqrc file
def usage():
    print('Usage: renuniq [-?hmnwL] [-c countstart] [-d descriptor] [-t template] filename...')
    print('  -m  Turn off strftime variable substitution in template')
    print("  -n  Print what would be executed but don't actually do it")
    print('  -w  Use the time now instead of mtime for strftime format strings')
    print('  -L  Display program license')
    print('''Substitutions:
%{UNIQSUFF} the unique suffix in the list of all files
%{DIR}      directory including trailing slash
%{NAME}     file name
%{PATH}     full name
%{EXT}      file extension (section including the last .)
%{NOTEXT}   file name up to the last .
%{DESC}     user-specified descriptor
%{NUM}      a 0-padded positive increasing integer of automatic width
%{NUMn}     a 0-padded positive increasing integer of width n (1<=n<=6)
strftime parameters on the modification time are also allowed, e.g. %Y, %m, %d''')
    print('Default template with no descriptor given: %s' % (CONFIG['default_template']))
    if CONFIG['default_template_single'] != CONFIG['default_template']:
        print('...for only a single file argument: %s' % (CONFIG['default_template_single']))
    print('Default template with descriptor given:    %s' % (CONFIG['default_template_desc']))
    if CONFIG['default_template_desc_single'] != CONFIG['default_template_desc']:
        print('...for only a single file argument: %s' % (CONFIG['default_template_desc_single']))


def rename(argv):
    try:
        optlist, args = getopt.getopt(argv[1:], '?c:d:hmnt:wL')
    except getopt.error:
        printerr('Unsupported command-line parameter')
        sys.exit(1)

    show_usage = 0
    names = args
    template = ''
    descriptor = ''
    strftime_enable = 1
    dry_run = 0
    count = 1
    use_time_now = 0

    for opt, arg in optlist:
        if opt == '-h' or \
           opt == '-?':
            show_usage = 1

        elif opt == '-c':
            try:
                count = int(arg)
            except ValueError:
                printerr('-c takes a numeric argument')
                sys.exit(1)

        elif opt == '-d':
            descriptor = arg

        elif opt == '-m':
            strftime_enable = not strftime_enable

        elif opt == '-n':
            dry_run = not dry_run

        elif opt == '-t':
            template = arg

        elif opt == '-w':
            use_time_now = 1

        elif opt == '-L':
            print(license, end='')
            sys.exit(0)

    # Read the config file before displaying help
    if 'HOME' in os.environ:
        config_path = os.path.join(os.environ['HOME'], '.renuniqrc')
        if os.path.exists(config_path):
            exec(open(config_path).read(), None, CONFIG)

    if not names:
        show_usage = 1

    if show_usage:
        usage()
        sys.exit(1)

    if not template:
        if descriptor:
            if len(names) == 1:
                template = CONFIG['default_template_desc_single']
            else:
                template = CONFIG['default_template_desc']
        else:
            if len(names) == 1:
                template = CONFIG['default_template_single']
            else:
                template = CONFIG['default_template']

    # What is the least suffix that will make a new name unique?
    pathprefix = os.path.commonprefix(names)
    dirprefix = os.path.dirname(pathprefix)
    prefix = os.path.basename(pathprefix)
    if dirprefix != os.path.dirname(names[0]):
        prefix = ''
    # Renaming a single file is a special case
    if len(names) < 2:
        extpos = prefix.rfind('.')
        if extpos >= 0:
            prefix = prefix[:extpos]
        else:
            prefix = ''

    if DEBUG:
        print('pathprefix', pathprefix)
        print('dirprefix', dirprefix)
        print('prefix', prefix)

    countmax = count + len(names) - 1
    for f in names:
        try:
            times = getmtime(f)
        except OSError:
            printerr('Skipping %s (not found)' % f)
            continue

        if use_time_now:
            times = time.localtime(time.time())
        dict = make_subst_dict(f, prefix, descriptor, len(repr(countmax)))
        substitute = Substitute(dict, count)
        count = count + 1

        try:
            newname = substvars(template, substitute)
        except KeyError as attr:
            printerr('Unknown substitution variable %s' % attr)
        else:
            if strftime_enable:
                newname = time.strftime(newname, times)

            if os.path.isabs(newname):
                newpath = newname
            else:
                direct = os.path.dirname(f)
                newpath = os.path.join(direct, newname)

            if os.path.exists(newpath):
                printerr('Skipping %s (%s already exists)' %
                         (f, newpath))
            else:
                print('mv "%s" "%s"' % (f, newpath))
                if not dry_run:
                    # Beware the race condition here
                    # between checking for existence and
                    # the actual move!
                    safemove(f, newpath)


if __name__ == '__main__':
    rename(sys.argv)
