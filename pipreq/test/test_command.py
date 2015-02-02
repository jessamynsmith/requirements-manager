import os
from mock import MagicMock
import tempfile
import unittest

from pipreq import cli, command


class TestCommand(unittest.TestCase):

    def setUp(self):
        self.parser = cli.create_parser()
        self.rc_file_blank = tempfile.NamedTemporaryFile()
        self.blank_command = command.Command(self.parser.parse_args([]), self.rc_file_blank.name)

        self.rc_file = tempfile.NamedTemporaryFile()
        self.rc_file.write(b'[metadata]\nshared=common\n[development]\nmock=1.0\n'
                           b'[common]\nDjango=1.7\npsycopg2=2.5.4\n')
        self.rc_file.flush()
        self.populated_command = command.Command(self.parser.parse_args([]), self.rc_file.name)

    def test_init(self):
        self.assertTrue(self.populated_command.config.has_section('common'))
        self.assertTrue(self.populated_command.config.has_option('common', 'Django'))

        # Ensure that capitalization is preserved
        output_dir = tempfile.mkdtemp()
        filename = os.path.join(output_dir, '.rc')
        with open(filename, 'w') as output:
            self.populated_command.config.write(output)
        expected = ('[metadata]\nshared = common\n\n[development]\nmock = 1.0\n\n'
                    '[common]\nDjango = 1.7\npsycopg2 = 2.5.4\n\n')
        with open(filename, 'r') as output:
            self.assertEqual(expected, open(output.name).read())

    def test_add_section_new_section(self):
        self.blank_command._add_section('common')

        self.assertTrue(self.blank_command.config.has_section('common'))

    def test_add_section_duplicate_section(self):
        self.populated_command._add_section('common')

        self.assertTrue(self.populated_command.config.has_section('common'))

    def test_set_option(self):
        self.blank_command._set_option('common', 'Django', '1.7')

        self.assertTrue(self.blank_command.config.has_section('common'))
        self.assertTrue(self.blank_command.config.has_option('common', 'Django'))
        self.assertEqual('1.7', self.blank_command.config.get('common', 'Django'))

    def test_get_option_does_not_exist(self):
        section, value = self.blank_command._get_option('Django')

        self.assertEqual(None, section)
        self.assertEqual(None, value)

    def test_get_option_exists(self):
        section, value = self.populated_command._get_option('Django')

        self.assertEqual('common', section)
        self.assertEqual('1.7', value)

    def test_get_shared_section_does_not_exist(self):
        shared = self.blank_command._get_shared_section()

        self.assertEqual(None, shared)

    def test_get_shared_section_exists(self):
        shared = self.populated_command._get_shared_section()

        self.assertEqual('common', shared)

    def test_make_requirements_directory_does_not_exist(self):
        tempdir = tempfile.mkdtemp()

        req_dir = self.blank_command._make_requirements_directory(tempdir)

        self.assertEqual('%s/requirements' % tempdir, req_dir)

    def test_make_requirements_directory_exists(self):
        tempdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(tempdir, 'requirements'))

        req_dir = self.blank_command._make_requirements_directory(tempdir)

        self.assertEqual(os.path.join(tempdir, 'requirements'), req_dir)

    def test_format_requirements_line(self):
        line = self.blank_command._format_requirements_line('Django', '1.7')

        self.assertEqual('Django==1.7\n', line)

    def test_write_requirements_file_for_shared_section(self):
        req_file = tempfile.NamedTemporaryFile()
        reqs = {'Django': '1.7', 'psycopg2': '2.5.4'}

        self.blank_command._write_requirements_file('common', 'common', reqs, req_file.name)

        self.assertEqual(b'Django==1.7\npsycopg2==2.5.4\n', req_file.read())

    def test_write_requirements_file_with_shared_section(self):
        req_file = tempfile.NamedTemporaryFile()
        reqs = {'gunicorn': '19.1.1'}

        self.blank_command._write_requirements_file('common', 'production', reqs, req_file.name)

        self.assertEqual(b'-r common.txt\ngunicorn==19.1.1\n', req_file.read())

    def test_generate_requirements_files_no_data(self):
        tempdir = tempfile.mkdtemp()

        self.blank_command.generate_requirements_files(tempdir)

        self.assertTrue(os.path.exists(os.path.join(tempdir, 'requirements')))

    def test_generate_requirements_files_with_data(self):
        tempdir = tempfile.mkdtemp()
        self.populated_command.config.add_section('empty')

        self.populated_command.generate_requirements_files(tempdir)

        self.assertTrue(os.path.exists(os.path.join(tempdir, 'requirements')))
        common_reqs = open(os.path.join(tempdir, 'requirements', 'common.txt'))
        self.assertEqual('Django==1.7\npsycopg2==2.5.4\n', common_reqs.read())
        dev_reqs = open(os.path.join(tempdir, 'requirements', 'development.txt'))
        self.assertEqual('-r common.txt\nmock==1.0\n', dev_reqs.read())

    def test_run_generate_requirements_files(self):
        tempdir = tempfile.mkdtemp()
        self.populated_command.args = self.parser.parse_args(['-g'])

        self.populated_command.run(tempdir)

        self.assertTrue(os.path.exists(os.path.join(tempdir, 'requirements')))
        common_reqs = open(os.path.join(tempdir, 'requirements', 'common.txt'))
        self.assertEqual('Django==1.7\npsycopg2==2.5.4\n', common_reqs.read())
        dev_reqs = open(os.path.join(tempdir, 'requirements', 'development.txt'))
        self.assertEqual('-r common.txt\nmock==1.0\n', dev_reqs.read())


class TestCreateRcFile(unittest.TestCase):

    def setUp(self):
        self.parser = cli.create_parser()
        self.rc_file_blank = tempfile.NamedTemporaryFile()
        self.blank_command = command.Command(self.parser.parse_args([]), self.rc_file_blank.name)
        self.blank_command._remap_stdin = MagicMock()

        self.rc_file = tempfile.NamedTemporaryFile()
        self.rc_file.write(b'[metadata]\nshared=common\n[development]\nmock=1.0\n'
                           b'[common]\nDjango=1.7\npsycopg2=2.5.4\n')
        self.rc_file.flush()
        self.populated_command = command.Command(self.parser.parse_args([]), self.rc_file.name)
        self.populated_command._remap_stdin = MagicMock()
        self.populated_command._get_section = MagicMock(return_value='common')

    def test_get_section(self):
        self.blank_command._get_section_key = MagicMock(side_effect=['aaa', '2', '1'])

        section = self.blank_command._get_section('nose', {1: 'common'}, '')

        self.assertEqual('common', section)

    def test_create_rc_file_default_empty(self):
        packages = tempfile.NamedTemporaryFile()

        self.blank_command.create_rc_file(packages)

        expected = b'[metadata]\nshared = common\n\n[common]\n\n[development]\n\n[production]\n\n'
        self.assertEqual(expected, self.rc_file_blank.read())

    def test_create_rc_file_default_add_packages(self):
        packages = tempfile.NamedTemporaryFile()

        self.blank_command.create_rc_file(packages)

        expected = b'[metadata]\nshared = common\n\n[common]\n\n[development]\n\n[production]\n\n'
        self.assertEqual(expected, self.rc_file_blank.read())

    def test_create_rc_file(self):
        output_dir = tempfile.mkdtemp()
        filename = os.path.join(output_dir, 'packages.txt')
        with open(filename, 'w') as packages:
            packages.write('mock==1.2\nDjango==1.7\nnose==1.3\n')
        packages = open(filename, 'r')

        self.populated_command.create_rc_file(packages)

        expected = ['[metadata]\n', 'shared = common\n', '\n', '[development]\n', 'mock = 1.2\n',
                    '\n', '[common]\n', 'Django = 1.7\n', 'nose = 1.3\n', '\n']
        self.assertEqual(expected, open(self.populated_command.rc_filename).readlines())

    def test_run_create_rc_file(self):
        package_file = tempfile.NamedTemporaryFile()
        package_file.write(b'mock==1.2\nDjango==1.7\nnose==1.3\n')
        package_file.seek(0)
        self.populated_command.args = self.parser.parse_args(['-c', package_file.name])

        self.populated_command.run()

        expected = ['[metadata]\n', 'shared = common\n', '\n', '[development]\n', 'mock = 1.2\n',
                    '\n', '[common]\n', 'Django = 1.7\n', 'nose = 1.3\n', '\n']
        self.assertEqual(expected, open(self.populated_command.rc_filename).readlines())
