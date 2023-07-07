# renuniq setuptools build file
import distutils
import os

from setuptools import Command, setup


class BuildDocsCommand(Command):
    """Custom setuptools command to build man page using pandoc."""
    description = 'Build documentation with pandoc'
    user_options = []

    def initialize_options(self):
        self.pandoc_files = []

    def finalize_options(self):
        options = self.distribution.get_option_dict('options')
        self.pandoc_files = [f for f in options['pandoc_files'][1].split('\n') if f]

    def run(self):
        for in_file in self.pandoc_files:
            # Expecting a filename like 'foo.1.md'
            fn, ext = os.path.splitext(in_file)
            if not ext:
                # Use a safer file given an unexpected filename
                fn = os.path.join(in_file, '.out')
            command = ['pandoc', in_file, '-s', '-t', 'man', '-o', fn]
            self.announce('Running command: %s' % ' '.join(command), level=distutils.log.INFO)
            self.spawn(command)


if __name__ == "__main__":
    setup(cmdclass={'build_pandoc': BuildDocsCommand})
