"""Private completion transaction for standalone figure exports.

The fixed final name is provisional until all integrity checks succeed. The
hidden staging name is retained and is never a completion marker. This is not
crash recovery or a promise about future external mutation after commitment.
"""
from __future__ import annotations

import os
import stat
import sys


PENDING = '.figure-completion.pending'


def close_descriptor(fd, *, committed):
    """Close bookkeeping FDs without reporting committed output as failed."""
    active = sys.exc_info()[1]
    try:
        os.close(fd)
    except OSError as exc:
        if not committed:
            if active is not None:
                raise RuntimeError('figure publication failed; descriptor cleanup could not be certified') from active
            raise
        # All data-stream closes precede commitment. Avoid warnings, which can
        # be configured to raise; this cleanup diagnostic must remain nonfatal.
        try:
            os.write(2, ('Figure publication committed; bookkeeping descriptor '
                         f'cleanup failed (errno={exc.errno}); cleanup is not certified.\n').encode('ascii'))
        except OSError:
            pass


def _write_pending(owner, raw):
    duplicate = os.dup(owner)
    try:
        stream = os.fdopen(duplicate, 'wb')
    except BaseException:
        close_descriptor(duplicate, committed=False)
        raise
    write_error = None
    try:
        with stream:
            try:
                stream.write(raw)
            except BaseException as exc:
                write_error = exc
                raise
    except BaseException as exc:
        if write_error is not None and exc is not write_error:
            # Closing a buffered stream may fail after its write already did.
            # Preserve the first error and expose the cleanup error as cause.
            raise write_error from exc
        raise


def _named_owner(directory, name, identity):
    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or not os.path.samestat(info, identity):
        raise ValueError('figure completion file identity changed')


def _rollback(owner):
    # This FD was reserved before any data writes. Invalidation reaches the
    # same inode even if the directory moved or another hard link was made.
    # Never stat-then-unlink a pathname: that cannot preserve a winner replaced
    # between those calls. Retain the empty owned entry for diagnosis instead.
    try:
        os.ftruncate(owner, 0)
        if os.fstat(owner).st_size != 0:
            raise OSError('owned completion inode remains nonempty')
    except OSError as exc:
        raise RuntimeError('figure publication failed; completion invalidation could not be certified') from exc


def complete(directory, marker, raw, verify):
    """Commit exact prepared bytes exclusively, or invalidate the owned inode.

    ``verify`` runs the publisher's source/output/directory checks. Original
    publication exceptions survive successful rollback; failed rollback raises
    an explicit uncertainty error chained to the original exception. No other
    output is removed, and a foreign replacement is never opened for writes.
    """
    if marker not in ('manifest.json', 'report.json') or type(raw) is not bytes:
        raise ValueError('expected a fixed figure completion name and prepared bytes')
    owner = os.open(PENDING, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    committed = False
    try:
        identity = os.fstat(owner)
        _write_pending(owner, raw)  # Includes buffered data flush and close.
        _named_owner(directory, PENDING, identity)
        if os.pread(owner, len(raw) + 1, 0) != raw:
            raise ValueError('pending figure completion bytes changed')
        verify()
        # link is exclusive: an existing marker is never overwritten.
        os.link(PENDING, marker, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        _named_owner(directory, marker, identity)
        if os.pread(owner, len(raw) + 1, 0) != raw:
            raise ValueError('figure completion bytes changed')
        verify()
        _named_owner(directory, PENDING, identity)
        _named_owner(directory, marker, identity)
        if os.pread(owner, len(raw) + 1, 0) != raw:
            raise ValueError('figure completion bytes changed')
        committed = True
    except BaseException as original:
        try:
            _rollback(owner)
        except RuntimeError as cleanup:
            raise cleanup from original
        raise
    finally:
        close_descriptor(owner, committed=committed)
