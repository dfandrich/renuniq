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
import logging
import os
import tempfile
import textwrap
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
        self.old_env_patcher = patch.dict('os.environ', {
            'HOME': self.staging_dir.name,
            'XDG_CONFIG_HOME': os.path.join(self.staging_dir.name, 'xdg-config')})
        self.old_env_patcher.start()

    def tearDown(self):
        self.old_env_patcher.stop()
        os.chdir(self.old_dir)
        self.staging_dir.cleanup()

    def assertFilesEqual(self, files):
        """Ensure the set of file names equals what is expected."""
        dirs = os.listdir(self.staging_dir.name)
        dirs.sort()
        self.assertListEqual(files, dirs)

    def write_config_file(self):
        """Write a .renuniqrc test file with known contents."""
        path = os.path.join(self.staging_dir.name, '.renuniqrc')
        with open(path, 'w') as f:
            f.write(textwrap.dedent('''\
                default_template = "DT_%{NUM}"
                default_template_single = "DTS_%{NUM}"
                default_template_desc = "DTD_%{DESC}_%{NUM}"
                # Make sure a comment works
                default_template_desc_single = "DTDS_%{DESC}_%{NUM}"
            '''))

    def test_help(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-?'])

        self.assertEqual(rc, 1)
        # Check some sentinels to ensure help is there without having to update the test
        # for every small change
        self.assertIn('Usage: renuniq [', output.getvalue())
        self.assertIn('-n   Print what', output.getvalue())

    def test_license(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-L'])

        self.assertEqual(rc, 0)
        # Check some sentinels to ensure help is there without having to update the test
        # for every small change
        self.assertIn('by Daniel Fandrich', output.getvalue())
        self.assertIn('GNU General Public License', output.getvalue())

    def test_version(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-V'])

        self.assertEqual(rc, 0)
        self.assertRegex(output.getvalue(), r'^renuniq ver\. [0-9]+')

    def test_bad_option(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            # Needed to send messages to stderr under pytest
            logging.basicConfig(force=True)
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
        self.assertIn('mv file4.x RENAMED_4.x', output.getvalue())
        self.assertIn('mv file6.x RENAMED_6.x', output.getvalue())

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

    def test_count(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}',
                             'a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['TST_1', 'TST_2', 'TST_3', 'TST_4', 'TST_5', 'TST_6', 'TST_7'])

    def test_startcount(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}', '-c', '70',
                             'a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['TST_70', 'TST_71', 'TST_72', 'TST_73', 'TST_74', 'TST_75', 'TST_76'])

    def test_startcountwidth(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}', '-c', '9', 'a', 'b'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(['TST_09', 'TST_10', 'file10.x', 'file4.x', 'file6.x', 'file7572',
                               'withdata'])

    def test_interval(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}', '-i', '3', 'a', 'b', 'file10.x'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(['TST_1', 'TST_4', 'TST_7', 'file4.x', 'file6.x', 'file7572',
                               'withdata'])

    def test_intervalwidth(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}', '-i', '8', 'a', 'b', 'file10.x'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(['TST_01', 'TST_09', 'TST_17', 'file4.x', 'file6.x', 'file7572',
                               'withdata'])

    def test_intervalstartcount(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}', '-i', '100', '-c', 111,
                             'a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['TST_111', 'TST_211', 'TST_311', 'TST_411', 'TST_511', 'TST_611', 'TST_711', ])

    def test_intervalstartcountboundary(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'TST_%{NUM}', '-i', '100', 'a'])
        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['TST_1', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

    def test_quote_filenames(self):
        # Create some names that need special quoting
        for name in ('d-quote"', "s-quote'", 'redirect<'):
            path = os.path.join(self.staging_dir.name, name)
            with open(path, 'w'):
                pass  # just create an empty file
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = renuniq.rename(['UNITTEST', '-t', 'RENAMED_%{NUM}',
                                 'd-quote"', "s-quote'", 'redirect<'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(
                ['RENAMED_1', 'RENAMED_2', 'RENAMED_3', 'a', 'b', 'file10.x', 'file4.x', 'file6.x',
                 'file7572', 'withdata'])
        self.assertIn('mv \'d-quote"\' RENAMED_1', output.getvalue())
        self.assertIn('mv \'s-quote\'"\'"\'\' RENAMED_2', output.getvalue())
        self.assertIn('mv \'redirect<\' RENAMED_3', output.getvalue())

    def test_config_dt(self):
        self.write_config_file()

        rc = renuniq.rename(['UNITTEST', 'file4.x', 'file6.x', 'file10.x'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(['.renuniqrc', 'DT_1', 'DT_2', 'DT_3',
                               'a', 'b', 'file7572', 'withdata'])

    def test_config_dts(self):
        self.write_config_file()

        rc = renuniq.rename(['UNITTEST', 'a'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(['.renuniqrc', 'DTS_1', 'b', 'file10.x', 'file4.x', 'file6.x',
                               'file7572', 'withdata'])

    def test_config_dtd(self):
        self.write_config_file()

        rc = renuniq.rename(['UNITTEST', '-d', 'DESC', 'a', 'b'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(['.renuniqrc', 'DTD_DESC_1', 'DTD_DESC_2',
                               'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

    def test_config_dtds(self):
        self.write_config_file()

        rc = renuniq.rename(['UNITTEST', '-d', 'DESC', 'a'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(['.renuniqrc', 'DTDS_DESC_1', 'b', 'file10.x', 'file4.x', 'file6.x',
                               'file7572', 'withdata'])

    def test_config_xdg(self):
        # make sure a config file in the XDG dir loads, too
        configdir = os.path.join(self.staging_dir.name, 'xdg-config')
        os.mkdir(configdir)
        with open(os.path.join(configdir, 'renuniqrc'), 'w') as f:
            f.write('default_template_single = "FOUND_CONFIG_%{NUM}"')

        rc = renuniq.rename(['UNITTEST', 'a'])

        self.assertEqual(rc, 0)
        self.assertFilesEqual(['FOUND_CONFIG_1', 'b', 'file10.x', 'file4.x', 'file6.x',
                               'file7572', 'withdata', 'xdg-config'])

    def test_err_write(self):
        # Make directory read-only
        os.chmod(self.staging_dir.name, 0o500)

        rc = renuniq.rename(['UNITTEST', '-t', 'RENAMED_%{NUM}', 'a'])

        # Make directory writable again so it can be deleted
        os.chmod(self.staging_dir.name, 0o700)

        self.assertEqual(rc, 1)
        self.assertFilesEqual(
                ['a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

    def test_err_nonexistent_file(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'RENAMED_%{NUM}', 'XYZZY', 'a'])

        self.assertEqual(rc, 1)
        self.assertFilesEqual(
                ['RENAMED_1', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

    def test_err_bad_variable(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'RENAMED_%{XYZZY}', 'a'])

        self.assertEqual(rc, 1)
        self.assertFilesEqual(
                ['a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

    def test_err_overwrite_existing_file(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'withdata', 'a'])

        self.assertEqual(rc, 1)
        self.assertFilesEqual(
                ['a', 'b', 'file10.x', 'file4.x', 'file6.x', 'file7572', 'withdata'])

    def test_err_overwrite_renamed_file(self):
        rc = renuniq.rename(['UNITTEST', '-t', 'file%{NUM}.x', 'a', 'b', 'withdata', 'file6.x'])

        self.assertEqual(rc, 1)
        self.assertFilesEqual(
                ['file1.x', 'file10.x', 'file2.x', 'file3.x', 'file4.x', 'file6.x', 'file7572'])


if __name__ == '__main__':
    unittest.main()
