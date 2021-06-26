# renuniq

renuniq is a program to rename batches of files in a user-specified
pattern. The pattern is specified in the form of a template can include a
sequentially-increasing number, the file extension, the unique ending of a
series of similarly-named files, the date or time of the file, and more. An
ideal application is renaming files from a digital camera to include meaningful
data.

## Documentation

See the man page in [renuniq.1](renuniq.1.md)

## Installation

The latest source code can be obtained from
https://github.com/dfandrich/renuniq/

renuniq is written in Python 3 and requires at minimum Python ver. 3.7.  Build
and install the latest release of code from Github with:

    pip3 install https://glare.now.sh/dfandrich/renuniq/tar

Generate the man page from a local repository using pandoc (which must be
installed separately) with the command:

    python3 setup.py build_pandoc

The man page needs to be copied manually into the proper location with a
command like:

    sudo install -m 0644 renuniq.1 /usr/local/share/man/man1

The regression test suite can be run from a local repository with the command:

    python3 setup.py test

## Author

Daniel Fandrich <dan@coneharvesters.com>

This program is Copyright (C) 2021 Daniel Fandrich. It is distributed under the
terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
