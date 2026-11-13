"""Partition collected tests by file without a maintained allowlist.

Opt in with ``python -m pytest -p utils.pytest_shard --ci-shard=1/4``.
Every collected file belongs to exactly one shard; new tests need no CI edit.
Keeping a file together avoids multiplying its module/class fixture setup.
Explicit ``--ci-lane`` isolates ten slow offline API, SG2 and native public-path
cases while retaining the complete collected suite across the ordinary shards
and case lanes.
"""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

import pytest


API_CASE_LANES = {
    "routing-dispatch": "tests/test_source_heading_runtime_api.py::test_actual_sent_routing_counts_usage_and_completed_zero_calls",
    "routing-portable": "tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes",
    "routing-regate": "tests/test_source_heading_runtime_api.py::test_actual_regated_report_captured_lineage",
    "routing-default-layout": "tests/test_source_heading_runtime_api.py::test_actual_default_layout_completed_capture",
}

SG2_CASE_LANES = {
    f"sg2-{mode}": "tests/test_wave7_5213_d76_registration.py::"
    f"test_sg2_root_launch_completes_and_records_registered_paths[{mode}]"
    for mode in ("none", "conventional", "explicit")
}
# Each drives one complete synthetic native launch, from capture through
# reservation and dispatch to the completion gates (#6191). Beside xdist
# workers in an ordinary shard they miss the 900-second capture-to-reservation
# window (1,200 s maximum age less the 300 s margin) and starve their shard.
# Alone on the lead's host at load average 31, capture to reservation took
# 246 s.
NATIVE_PUBLIC_CASE_LANES = {
    "native-public-correction": "tests/test_native_shared_execution.py::"
    "test_actual_public_correction_three_workers_and_saved_completion",
    "native-public-variant": "tests/test_native_shared_execution_variant.py::"
    "test_actual_public_merged_omissions_and_all_chunk_statuses",
    "native-public-pending": "tests/test_native_pending_public_completion.py::"
    "test_pending_floor_public_completion_retains_diagnostic_reading",
}
DEDICATED_CASE_LANES = {**API_CASE_LANES, **SG2_CASE_LANES, **NATIVE_PUBLIC_CASE_LANES}


def partition_lanes(nodeids):
    """Partition the entire actual collection, never a test allowlist."""
    nodeids = list(nodeids)
    counts = Counter(nodeids)
    if len(set(DEDICATED_CASE_LANES.values())) != len(DEDICATED_CASE_LANES):
        raise pytest.UsageError("--ci-lane has duplicate dedicated targets")
    invalid = [node for node in DEDICATED_CASE_LANES.values() if counts[node] != 1]
    if invalid:
        raise pytest.UsageError("--ci-lane requires the complete collection with each "
                                "dedicated target exactly once: " + ", ".join(invalid))
    dedicated = set(DEDICATED_CASE_LANES.values())
    return {"ordinary": [node for node in nodeids if node not in dedicated],
            **{lane: [node] for lane, node in DEDICATED_CASE_LANES.items()}}


class _DedicatedCaseOutcome:
    """A required case cannot pass by skipping, xfail or collection alone."""

    def __init__(self, lane):
        self.expected = DEDICATED_CASE_LANES[lane]
        self.collection_matches = False
        self.reports = []

    @pytest.hookimpl(trylast=True)
    def pytest_collection_finish(self, session):
        self.collection_matches = [item.nodeid for item in session.items] == [self.expected]

    def pytest_runtest_logreport(self, report):
        self.reports.append((report.nodeid, report.when, report.outcome,
                             hasattr(report, "wasxfail")))

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        if exitstatus != pytest.ExitCode.OK or session.exitstatus != pytest.ExitCode.OK:
            return
        required = [(self.expected, phase, "passed", False)
                    for phase in ("setup", "call", "teardown")]
        if not self.collection_matches or self.reports != required:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
            reporter = session.config.pluginmanager.getplugin("terminalreporter")
            if reporter is not None:
                reporter.write_sep("=", "dedicated CI case did not pass setup, call and teardown")


def pytest_addoption(parser):
    parser.addoption("--ci-lane", choices=("ordinary", *DEDICATED_CASE_LANES), default=None,
                     help="Opt into ordinary shards or one required offline case")
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
    lane = config.getoption("--ci-lane")
    timing_path = config.getoption("--ci-shard-timings")
    if lane == "ordinary" and value is None:
        raise pytest.UsageError("--ci-lane=ordinary requires --ci-shard")
    if lane in DEDICATED_CASE_LANES:
        if value is not None or timing_path is not None:
            raise pytest.UsageError("dedicated --ci-lane forbids shard/timing options")
        if config.getoption("numprocesses", default=None) not in (None, 0):
            raise pytest.UsageError("dedicated --ci-lane requires a single process")
        config.pluginmanager.register(_DedicatedCaseOutcome(lane), "d4d-dedicated-case")
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
    lane = config.getoption("--ci-lane")
    if value is None and lane is None:
        return
    lane_deselected = []
    if lane is not None:
        partition = partition_lanes(item.nodeid for item in items)
        eligible = set(partition[lane])
        lane_deselected = [item for item in items if item.nodeid not in eligible]
        items[:] = [item for item in items if item.nodeid in eligible]
        if lane in DEDICATED_CASE_LANES:
            config.hook.pytest_deselected(items=lane_deselected)
            return
    index, total = _coordinates(value)
    weights = getattr(config, "_d4d_shard_weights", None)
    assignments = (balanced_files((item.nodeid.split("::", 1)[0] for item in items),
                                  total, weights) if weights is not None else None)
    selected, deselected = [], lane_deselected
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
    lane = config.getoption("--ci-lane")
    if lane in DEDICATED_CASE_LANES:
        return f"CI dedicated case {lane}: {DEDICATED_CASE_LANES[lane]}"
    if lane == "ordinary":
        return f"CI ordinary shard {config.getoption('--ci-shard')}: seven required cases run separately"
    value = config.getoption("--ci-shard")
    if value is not None:
        if config.getoption("--ci-shard-timings") is not None:
            return f"CI shard {value}: measured file durations; every collected file included"
        return f"CI shard {value}: SHA-256 of each collected file path (includes corpus)"
