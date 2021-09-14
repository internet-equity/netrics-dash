import argcmdr


class Main(argcmdr.RootCommand):
    """Netrics Local Dashboard: Command-Line Interface"""


def main():
    # auto-load command-containing modules within this sub-package
    argcmdr.init_package(name='app.cmd')

    # invoke command hierarchy
    argcmdr.main(Main)
