import pathlib


BINFMT_TAG = 'a7996909642ee92942dcd6cff44b9b95f08dad64'
BINFMT_TARGET = pathlib.Path('/proc/sys/fs/binfmt_misc/qemu-aarch64')

NDT_SERVER_TAG = 'v0.20.6'
NDT_SERVER_ORIGIN = 'm-lab/ndt-server'

NETRICS_USER = 'ubuntu'
NETRICS_HOST = 'netrics.local'

MANAGE_PATH = pathlib.Path(__file__).absolute().parent

REPO_PATH = MANAGE_PATH.parent

ENV_FILE = REPO_PATH / '.env'

EXTENSION_PATH = REPO_PATH / 'src' / 'ext'
