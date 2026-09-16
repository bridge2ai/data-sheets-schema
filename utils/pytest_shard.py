"""Partition collected tests by file without a maintained allowlist.

Opt in with ``python -m pytest -p utils.pytest_shard --ci-shard=1/4``.
Every collected file belongs to exactly one shard; new tests need no CI edit.
Keeping a file together avoids multiplying its module/class fixture setup.
"""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

import pytest


def pytest_addoption(parser):
    parser.addoption("--ci-shard", metavar="INDEX/TOTAL", default=None,
                     help="Run one deterministic, one-based shard of collected tests")
    parser.addoption("--ci-shard-timings", metavar="JSON", default=None,
                     help="Balance the collected files using recorded file durations")


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
    timing_path = config.getoption("--ci-shard-timings")
    if timing_path is not None:
        if value is None:
            raise pytest.UsageError("--ci-shard-timings requires --ci-shard")
        config._d4d_shard_weights = read_weights(timing_path)


def read_weights(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate timing key: {key}")
            result[key] = value
        return result
    try:
        data = json.loads(Path(path).read_text(), object_pairs_hook=unique)
        if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
                or data["schema_version"] != 1):
            raise ValueError("expected timing schema version 1")
        weights = data.get("file_seconds")
        if not isinstance(weights, dict) or not weights:
            raise ValueError("file_seconds must be a nonempty mapping")
        for name, duration in weights.items():
            if (not isinstance(name, str) or not name.endswith(".py")
                    or type(duration) not in (int, float)
                    or not math.isfinite(duration) or duration <= 0):
                raise ValueError(f"invalid file duration: {name}")
        return weights
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        raise pytest.UsageError(f"invalid --ci-shard-timings: {exc}") from exc


def _estimates(paths, weights):
    paths = set(paths)
    known = [weights[path] for path in paths if path in weights]
    fallback = median(known) if known else 1.0
    return {path: weights.get(path, fallback) for path in paths}


def balanced_files(paths, total, weights):
    """Schedule actual collected files; timing keys never select coverage."""
    estimates = _estimates(paths, weights)
    loads, counts = [0.0] * total, [0] * total
    assignments = {}
    for path in sorted(estimates, key=lambda path: (-estimates[path], path)):
        index = min(range(total), key=lambda index: (loads[index], counts[index], index))
        assignments[path] = index + 1
        loads[index] += estimates[path]
        counts[index] += 1
    return assignments


def shard_for(nodeid, total):
    path = nodeid.split("::", 1)[0]
    return int.from_bytes(hashlib.sha256(path.encode("utf-8")).digest(), "big") % total + 1


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    value = config.getoption("--ci-shard")
    if value is None:
        return
    index, total = _coordinates(value)
    weights = getattr(config, "_d4d_shard_weights", None)
    assignments = (balanced_files((item.nodeid.split("::", 1)[0] for item in items),
                                  total, weights) if weights is not None else None)
    selected, deselected = [], []
    for item in items:
        owner = (assignments[item.nodeid.split("::", 1)[0]] if assignments is not None
                 else shard_for(item.nodeid, total))
        (selected if owner == index else deselected).append(item)
    if weights is not None:
        counts = Counter(item.nodeid.split("::", 1)[0] for item in selected)
        estimates = _estimates(counts, weights)
        # Start expensive individual checks early. A file's total time alone
        # would put hundreds of cheap cases ahead of a single long corpus
        # check. Stable sorting retains the existing order within each file.
        selected.sort(key=lambda item: -estimates[item.nodeid.split("::", 1)[0]]
                      / counts[item.nodeid.split("::", 1)[0]])
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
    # Preserve pytest's NO_TESTS_COLLECTED exit status for an empty shard.
    # A typo or a missing corpus must never turn into a successful CI job.


def pytest_report_header(config):
    value = config.getoption("--ci-shard")
    if value is not None:
        if config.getoption("--ci-shard-timings") is not None:
            return f"CI shard {value}: measured file durations; every collected file included"
        return f"CI shard {value}: SHA-256 of each collected file path (includes corpus)"
