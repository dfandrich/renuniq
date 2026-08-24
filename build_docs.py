"""Build documentation using pandoc."""

import pypandoc


def build_docs():
    """Convert project documentation files using Pandoc."""
    pypandoc.convert_file(
        'renuniq.1.md',
        to='man',
        outputfile='renuniq.1',
        extra_args=['--standalone']
    )


if __name__ == '__main__':
    build_docs()
