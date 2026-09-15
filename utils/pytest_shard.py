"""Partition collected tests by file without a maintained allowlist.

Opt in with ``python -m pytest -p utils.pytest_shard --ci-shard=1/4``.
Every collected file belongs to exactly one shard; new tests need no CI edit.
Keeping a file together avoids multiplying its module/class fixture setup.
"""

import hashlib

import pytest


def pytest_addoption(parser):
    parser.addoption("--ci-shard", metavar="INDEX/TOTAL", default=None,
                     help="Run one deterministic, one-based shard of collected tests")


def _coordinates(value):
    try:
        index, total = map(int, value.split("/"))
        if not 1 <= index <= total:
            raise ValueError
    except (ValueError, AttributeError):
        raise pytest.UsageError("--ci-shard must be INDEX/TOTAL with 1 <= INDEX <= TOTAL")
    return index, total


def pytest_configure(config):
    value = config.getoption("--ci-shard")
    if value is not None:
        _coordinates(value)


def shard_for(nodeid, total):
    path = nodeid.split("::", 1)[0]
    return int.from_bytes(hashlib.sha256(path.encode("utf-8")).digest(), "big") % total + 1


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    value = config.getoption("--ci-shard")
    if value is None:
        return
    index, total = _coordinates(value)
    selected, deselected = [], []
    for item in items:
        (selected if shard_for(item.nodeid, total) == index else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
    # Preserve pytest's NO_TESTS_COLLECTED exit status for an empty shard.
    # A typo or a missing corpus must never turn into a successful CI job.


def pytest_report_header(config):
    value = config.getoption("--ci-shard")
    if value is not None:
        return f"CI shard {value}: SHA-256 of each collected file path (includes corpus)"
