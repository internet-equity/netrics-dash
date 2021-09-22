from argcmdr import LocalRoot


class Management(LocalRoot):
    """manage local dashboard project"""

    def __init__(self, parser):
        parser.add_argument(
            '--image-repo',
            default='chicagocdac',
            metavar='NAME|URI',
            help="Docker organization repository or generic image repository URI with which to "
                 "tag and to which to push built images (default: %(default)s)",
        )
