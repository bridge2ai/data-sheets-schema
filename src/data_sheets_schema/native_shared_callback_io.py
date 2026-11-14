"""Fixed callback publication primitives, with no verifier or deferred imports.

Same create-once and journal CAS semantics as the existing orchestration
writers. Paths and proposed bytes must already have passed the capture checks.
"""
import os
from pathlib import Path
import tempfile

from . import native_shared_contract as c
from .native_shared_evidence import read_regular


def _sync_directory(path):
    handle = os.open(path, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def durable_new(path, raw, *, staging_directory=None):
    path = Path(path)
    staging = path.parent if staging_directory is None else Path(staging_directory)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.pending-', dir=staging)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    try:
        _sync_directory(path.parent)
    except BaseException:
        # The final name already retains the complete bytes. Remove only its
        # redundant link so the evidence reader can still inspect that file.
        # Cleanup must not replace the original publication failure.
        try:
            os.unlink(temporary)
            _sync_directory(staging)
        except OSError:
            pass
        raise
    os.unlink(temporary)
    _sync_directory(staging)


def _mkdir_durable(path):
    missing = []
    parent = Path(path)
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError('output ancestor is not a regular directory')
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        _sync_directory(directory.parent)


def _replace_journal(destination, before, after):
    current = read_regular(str(destination), 'journal', max_bytes=c.HARD_LIMITS['journal_bytes'])
    if current.captured != before:
        raise ValueError('journal changed before its checked replacement')
    fd, temporary = tempfile.mkstemp(prefix='journal.partial-', dir=destination.parent)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(after.raw)
        stream.flush()
        os.fsync(stream.fileno())
    if read_regular(str(destination), 'journal', max_bytes=c.HARD_LIMITS['journal_bytes']) != current:
        raise ValueError('journal changed while its replacement was being persisted')
    os.replace(temporary, destination)
    _sync_directory(destination.parent)
    observed = read_regular(str(destination), 'journal', max_bytes=c.HARD_LIMITS['journal_bytes'])
    if observed.captured.pin != after.pin or observed.captured.raw != after.raw:
        raise ValueError('published journal differs from its proposed bytes')
    return observed
