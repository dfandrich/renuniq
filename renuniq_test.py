# Tests for renuniq.py
#
# Copyright (C) 2021 Daniel Fandrich
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import contextlib
import io
import os
import tempfile
import time
import unittest
from unittest.mock import patch

import renuniq


class TestRenuniq(unittest.TestCase):

    def setUp(self):
        self.staging_dir = tempfile.TemporaryDirectory()
        self.old_dir = os.curdir
        os.chdir(self.staging_dir.name)
        # print(f"Test files are in {self.staging_dir.name}")
        ft = time.mktime(time.strptime('20210102', '%Y%m%d'))
        for name in ('file4.x', 'file6.x', 'file10.x', 'file7572', 'a', 'b'):
            path = os.path.join(self.staging_dir.name, name)
            with open(path, 'w'):
                pass  # just create an empty file
            os.utime(path, times=(ft, ft))  # set a known mtime

        with open(os.path.join(self.staging_dir.name, 'withdata'), 'w') as f:
            f.write('withdata')

        # Make sure the user's config file is ignored
        self.old_env_patcher = patch.dict('os.environ', {'HOME': self.staging_dir.name})
        self.old_env_patcher.start()

    def tearDown(self):
        self.old_env_patcher.stop()
        os.chdir(self.old_dir)
        print(f"Clearing {self.staging_dir.name}")
        self.staging_dir.cleanup()

    def assertFilesEqual(self, files):
        """Ensure the set of file names equals what is expected."""
        dirs = os.listdir(self.staging_dir.name)
        dirs.sort()
        self.assertListEqual(files, dirs)

    def test_help(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-?'])
        self.assertEqual(rc, 1)
        # Check some sentinels to ensure help is there without having to update the test
        # for every small change
        self.assertIn('Usage: renuniq [', output.getvalue())
        self.assertIn('-n  Print what', output.getvalue())

    def test_license(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-L'])
        self.assertEqual(rc, 0)
        # Check some sentinels to ensure help is there without having to update the test
        # for every small change
        self.assertIn('by Daniel Fandrich', output.getvalue())
        self.assertIn('GNU General Public License', output.getvalue())

    def test_bad_option(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            rc = renuniq.rename(['UNITTEST', '-^'])
        self.assertEqual(rc, 1)
        self.assertIn('Unsupported command-line', output.getvalue())

    def test_standard_template(self):
        rc = renuniq.rename(['UNITTEST', 'file4.x', 'file6.x', 'file10.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['20210102_10.x', '20210102_4.x', '20210102_6.x', 'a', 'b', 'file7572', 'withdata'])

    def test_standard_template_single(self):
        rc = renuniq.rename(['UNITTEST', 'file4.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['20210102_.x', 'a', 'b', 'file10.x', 'file6.x', 'file7572', 'withdata'])

    def test_standard_template_descriptor(self):
        rc = renuniq.rename(['UNITTEST', '-d', 'DESCRIPTOR', 'file4.x', 'file6.x', 'file10.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['20210102_DESCRIPTOR_10.x', '20210102_DESCRIPTOR_4.x', '20210102_DESCRIPTOR_6.x',
                 'a', 'b', 'file7572', 'withdata'])

    def test_standard_template_descriptor_single(self):
        rc = renuniq.rename(['UNITTEST', '-d', 'DESCRIPTOR', 'file4.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['20210102_DESCRIPTOR_.x', 'a', 'b', 'file10.x', 'file6.x', 'file7572', 'withdata'])

    def test_single_nosubst(self):
        rc = renuniq.rename(['UNITTEST', '-m', '-t', '%Y%m%d_%{UNIQSUFF}', 'file4.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['%Y%m%d_.x', 'a', 'b', 'file10.x', 'file6.x', 'file7572', 'withdata'])

    @patch('renuniq.time.time', return_value=time.mktime(time.strptime('20210202', '%Y%m%d')))
    def test_time_now(self, mock_time):
        rc = renuniq.rename(['UNITTEST', '-w', '-t', '%Y%m%d_%{UNIQSUFF}', 'file4.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['20210202_.x', 'a', 'b', 'file10.x', 'file6.x', 'file7572', 'withdata'])

    def test_rename_order(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{UNIQSUFF}', 'withdata', 'file4.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['TST_file4.x', 'TST_withdata', 'a', 'b', 'file10.x', 'file6.x', 'file7572'])
        with open('TST_withdata') as f:
            self.assertEqual(f.read(), 'withdata')

    def test_dry_run(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-n', '-t', 'RENAMED_%{UNIQSUFF}',
                                 'file4.x', 'file6.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])
        self.assertIn('mv "file4.x" "RENAMED_4.x"', output.getvalue())
        self.assertIn('mv "file6.x" "RENAMED_6.x"', output.getvalue())

    def test_substitutions(self):
        rc = renuniq.rename(['UNITTEST', '-d', 'DESC', '-t',
                             'SUB|%{NAME}|%{EXT}|%{NOTEXT}|%{DESC}|%{NUM}|'
                             '%{NUM1}|%{NUM2}|%{NUM3}|%{NUM4}|%{NUM5}|%{NUM6}|', 'withdata'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['SUB|withdata||withdata|DESC|1|1|01|001|0001|00001|000001|', 'a', 'b',
                 'file10.x', 'file4.x', 'file6.x', 'file7572'])

    def test_substitution_exts(self):
        rc = renuniq.rename(['UNITTEST', '-d', 'DESC', '-t', 'SUB|%{EXT}|%{NOTEXT}|%{NUM}',
                             'file4.x', 'file6.x', 'file10.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['SUB|.x|file10|3', 'SUB|.x|file4|1', 'SUB|.x|file6|2', 'a', 'b',
                 'file7572', 'withdata'])

    def test_substitution_dir_absolute(self):
        rename_file = os.path.join(self.staging_dir.name, 'withdata')
        rc = renuniq.rename(['UNITTEST', '-t', '%{DIR}RENAMED', rename_file])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['RENAMED', 'a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572'])

    def test_substitution_dir_cwd(self):
        rc = renuniq.rename(['UNITTEST', '-t', '%{DIR}RENAMED', 'withdata'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['RENAMED', 'a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572'])

    def test_substitutions_path_absolute(self):
        rename_file = os.path.join(self.staging_dir.name, 'withdata')
        rc = renuniq.rename(['UNITTEST', '-t', '%{PATH}|RENAMED', rename_file])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata|RENAMED'])

    def test_substitutions_path_cwd(self):
        rc = renuniq.rename(['UNITTEST', '-t', '%{PATH}|RENAMED', 'withdata'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata|RENAMED'])

    def test_substitution_name_absolute(self):
        rename_file = os.path.join(self.staging_dir.name, 'withdata')
        rc = renuniq.rename(['UNITTEST', '-t', 'SUB|%{NAME}', rename_file])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['SUB|withdata', 'a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572'])

    def test_substitution_10(self):
        # Create more files to get to at least 10
        for name in ('c', 'd', 'e'):
            path = os.path.join(self.staging_dir.name, name)
            with open(path, 'w'):
                pass  # just create an empty file

        rc = renuniq.rename(['UNITTEST', '-t', 'RENAMED_%{NUM}', 'a', 'b', 'c', 'd', 'e',
                             'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['RENAMED_01', 'RENAMED_02', 'RENAMED_03', 'RENAMED_04', 'RENAMED_05',
                 'RENAMED_06', 'RENAMED_07', 'RENAMED_08', 'RENAMED_09', 'RENAMED_10'])


if __name__ == '__main__':
    unittest.main()
