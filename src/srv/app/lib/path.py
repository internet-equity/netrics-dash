import fcntl
import os


class PathLock:

    def __init__(self, path):
        self.path = path
        self.fd = None

    def open(self):
        self.fd = os.open(self.path, os.O_RDONLY)

    def lock(self):
        """acqiure advisory lock"""
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock(self):
        """force unlock"""
        fcntl.flock(self.fd, fcntl.LOCK_UN)

    def __enter__(self):
        assert os.path.exists(self.path)
        self.open()
        self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.close(self.fd)
