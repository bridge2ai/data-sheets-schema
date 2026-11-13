"""Attempt-local PyStow storage, excluded from model files and published evidence.

The runtime declares the path; the shared environment builder binds it to the
one-use attempt. Only the controller creates it, exclusively after reservation.
Retain it locally for a hidden-entry census, but never inventory/publish its
contents as generation evidence. No prior cache is reused or copied.
"""
from pathlib import Path
import os

ENVIRONMENT_KEY = 'PYSTOW_HOME'
DIRECTORY = 'helper-cache'


def declared_path(environment):
    """Validate the explicit cache path without reading or creating its contents."""
    value = environment.get(ENVIRONMENT_KEY)
    if (type(value) is not str or not value or any(ch in value for ch in ('\0', '\r', '\n'))
            or not Path(value).is_absolute() or str(Path(value)) != value
            or os.path.normpath(value) != value):
        raise ValueError('PYSTOW_HOME must declare a canonical absolute helper cache')
    cache, home = Path(value), Path(environment['HOME'])
    if cache == home or home in cache.parents or cache in home.parents:
        raise ValueError('helper cache and HOME must be disjoint')
    return cache


def for_attempt(environment, attempt):
    """Bind the declaration to one exact attempt, never a shared cache root."""
    cache = declared_path(environment)
    if cache != Path(attempt) / DIRECTORY:
        raise ValueError('PYSTOW_HOME must be the registered attempt helper-cache')
    return cache


def create_for_attempt(value):
    """Exclusive creation after a new attempt is reserved; refuse any old entry."""
    attempt = Path(value['attempt_directory'])
    cache = for_attempt(value['runtime']['environment'], attempt)
    if value['environment'].get(ENVIRONMENT_KEY) != str(cache):
        raise ValueError('child helper cache differs from runtime declaration')
    if not attempt.is_dir() or attempt.is_symlink() or attempt.resolve(strict=True) != attempt:
        raise ValueError('helper cache requires a physical reserved attempt')
    cache.mkdir(mode=0o700)  # No exist_ok: an empty old directory is spent too.
    fd = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    if cache.is_symlink() or cache.resolve(strict=True) != cache or any(cache.iterdir()):
        raise ValueError('new helper cache must be physical and empty')
    return cache
