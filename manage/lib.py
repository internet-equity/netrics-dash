import grp
import os
import string

from argcmdr import Local
from descriptors import cachedclassproperty
from plumbum.cmd import sudo
from plumbum.commands import ExecutionModifier

from . import config


class _FGOut(ExecutionModifier):
    """plumbum execution modifier to echo output to shell.

    Unlike the built-in `FG`, stdin is *not* affected. This allows
    commands' stdin to be set programmatically.

    """
    __slots__ = ('retcode', 'timeout')

    def __init__(self, retcode=0, timeout=None):
        self.retcode = retcode
        self.timeout = timeout

    def __rand__(self, cmd):
        return cmd.run(retcode=self.retcode, stdout=None, stderr=None, timeout=self.timeout)


# FIXME: argcmdr should be smarter about default execution modification --
# FIXME: if the command's stdin is already set it shouldn't be touched
# FIXME: (by TEE namely) -- such that this modifier isn't necessary
# FIXME: (or at least not usually).

FGOut = _FGOut()


class _SHH(ExecutionModifier):
    """plumbum execution modifier to ensure output is not echoed to terminal

    essentially a no-op, this may be used to override argcmdr settings
    and cli flags controlling this feature, on a line-by-line basis, to
    hide unnecessary or problematic (e.g. highly verbose) command output.

    """
    __slots__ = ('retcode', 'timeout')

    def __init__(self, retcode=0, timeout=None):
        self.retcode = retcode
        self.timeout = timeout

    def __rand__(self, cmd):
        return cmd.run(retcode=self.retcode, timeout=self.timeout)


SHH = _SHH()


class PiCommandMixin:

    def __init__(self, parser):
        super().__init__(parser)

        parser.add_argument(
            '--username',
            default=config.NETRICS_USER,
            metavar='NAME',
            help="netrics host username (default: %(default)s)",
        )
        parser.add_argument(
            '--host',
            default=config.NETRICS_HOST,
            metavar='NETLOC',
            help="netrics local hostname or network locator (default: %(default)s)",
        )


class LocalPiCommand(PiCommandMixin, Local):
    pass


class DockerCommand(Local):

    @cachedclassproperty
    def docker(cls):
        if any(grp.getgrgid(group).gr_name == 'docker' for group in os.getgroups()):
            return cls.local['docker']

        return sudo['-E', '--preserve-env=PATH', 'docker']


class Template(string.Template):

    delimiter = '%'

    templates_path = config.MANAGE_PATH / 'template'

    @classmethod
    def render(cls, name, *contexts, **kwcontext):
        template_path = cls.templates_path / name
        template = cls(template_path.read_text())
        return template.substitute(*contexts, **kwcontext)
