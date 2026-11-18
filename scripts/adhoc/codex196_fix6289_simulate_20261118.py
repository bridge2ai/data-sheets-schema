#!/usr/bin/env python3
"""Issue 6289: estimate CI shards using real file assignment and xdist queues.

Date: 2026-11-18. Inputs: ordered complete pytest collection, candidate timing
weights, optional retained per-node phase sums and explicit moved-node mapping.
Outputs: one exclusive JSON report. No tests, native runtimes or providers run.
The real candidate balanced_files and installed xdist LoadScheduling are used;
fake workers complete supplied-duration events, including two-item lookahead.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import ast
from collections import Counter, deque
import hashlib
import heapq
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace

PRODUCER_RAW = Path(__file__).read_bytes()


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def json_read(path):
    return json.loads(Path(path).read_text())


def collection(path):
    raw = Path(path).read_text()
    if raw.lstrip().startswith(("[", "{")):
        value = json.loads(raw)
        if isinstance(value, dict):
            value = value["nodeids"]
    else:
        value = [line.strip() for line in raw.splitlines()
                 if ".py::" in line and line.strip().split("::", 1)[0].endswith(".py")]
    if (not isinstance(value, list) or not value
            or any(not isinstance(node, str) or ".py::" not in node for node in value)):
        raise ValueError("collection must contain ordered complete node IDs")
    return value


def load_sharder(root):
    path = Path(root).resolve(strict=True) / "utils/pytest_shard.py"
    spec = importlib.util.spec_from_file_location("issue6289_candidate_sharder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


class Worker:
    def __init__(self, index):
        self.index = index
        self.gateway = SimpleNamespace(id="gw" + str(index))
        self.shutting_down = False
        self.sent = []

    def send_runtest_some(self, indices):
        self.sent.extend(indices)

    def shutdown(self):
        self.shutting_down = True


def simulate_xdist(nodes, seconds, workers, fixture_model=None, multiplier=1.0):
    # Import only the scheduler; fake Worker objects never spawn a subprocess.
    from xdist.scheduler.load import LoadScheduling
    scheduler = object.__new__(LoadScheduling)
    scheduler.numnodes = workers
    scheduler.node2collection = {}
    scheduler.node2pending = {}
    scheduler.pending = []
    scheduler.collection = None
    scheduler.log = lambda *args, **kwargs: None
    scheduler.config = None
    scheduler.maxschedchunk = 1
    worker_list = [Worker(i) for i in range(workers)]
    for worker in worker_list:
        scheduler.add_node(worker)
        scheduler.add_node_collection(worker, nodes)
    scheduler.schedule()
    heap = []
    active = {}
    history = [[] for _ in worker_list]
    fixture_events = [[] for _ in worker_list]
    previous_modules = [None] * workers
    previous_nodes = [None] * workers
    active_fixtures = [set() for _ in worker_list]
    finished = set()
    clock = 0.0

    def start_available():
        for worker in worker_list:
            pending = scheduler.node2pending[worker]
            if worker.index in active or not pending:
                continue
            # remote.run_one_test obtains the following item before executing.
            # A shutdown marker supplies lookahead for the final single item.
            if len(pending) < 2 and not worker.shutting_down:
                continue
            item = pending[0]
            if item in finished:
                raise AssertionError("scheduler repeated an already completed item")
            active[worker.index] = item
            node = nodes[item]
            module = node.split("::", 1)[0]
            prior_node = previous_nodes[worker.index]
            module_entry = previous_modules[worker.index] != module
            if module_entry:
                active_fixtures[worker.index].clear()
            previous_modules[worker.index] = module
            previous_nodes[worker.index] = node
            duration = seconds[node]
            for number, fixture in enumerate((fixture_model or {}).get("fixtures", [])):
                if node not in fixture["consumer_nodes"]:
                    continue
                removed = fixture["recorded_setup_seconds"].get(node, 0.0) * multiplier
                cold = number not in active_fixtures[worker.index]
                added = fixture["cold_setup_seconds"] * multiplier if cold else 0.0
                duration = max(0.0, duration - removed) + added
                active_fixtures[worker.index].add(number)
                fixture_events[worker.index].append({"node": node, "cold": cold,
                    "previous_node": prior_node, "module_entry": module_entry,
                    "started_seconds": clock,
                    "removed_recorded_setup_seconds": removed, "added_setup_seconds": added})
            heapq.heappush(heap, (clock + duration, worker.index, item, clock, duration))

    start_available()
    while heap:
        clock, index, item, started, duration = heapq.heappop(heap)
        worker = worker_list[index]
        if active.pop(index) != item:
            raise AssertionError("worker event no longer matches its active item")
        finished.add(item)
        history[index].append((nodes[item], started, clock, duration))
        scheduler.mark_test_complete(worker, item, duration=duration)
        start_available()
    if finished != set(range(len(nodes))) or active or scheduler.has_pending:
        raise AssertionError("scheduler simulation did not finish exact collected items")
    sent = [item for worker in worker_list for item in worker.sent]
    if sorted(sent) != list(range(len(nodes))):
        raise AssertionError("scheduler did not dispatch every item exactly once")
    return {
        "makespan_seconds": round(max((rows[-1][2] for rows in history if rows), default=0), 3),
        "fixture_net_seconds": round(sum(event["added_setup_seconds"] - event["removed_recorded_setup_seconds"]
            for events in fixture_events for event in events), 3),
        "workers": [{"worker": "gw" + str(i), "items": len(rows),
            "fixture_events": fixture_events[i],
            "busy_seconds": round(sum(row[3] for row in rows), 3),
            "finished_seconds": round(rows[-1][2], 3) if rows else 0,
            "first_nodes": [row[0] for row in rows[:4]],
            "slowest_nodes": [{"node": row[0], "seconds": round(row[3], 3)}
                              for row in sorted(rows, key=lambda row: -row[3])[:5]]}
            for i, rows in enumerate(history)]}


def observations(paths, node_map):
    values, sources = {}, {}
    for path in paths:
        data = json_read(path)
        data = data.get("per_node", data)
        if not isinstance(data, dict):
            raise ValueError("node seconds must be a mapping")
        for old, entry in data.items():
            node = node_map.get(old, old)
            value = entry["seconds"] if isinstance(entry, dict) else entry
            if (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError("invalid duration for " + old)
            if node not in values or value > values[node]:
                values[node] = float(value)
                sources[node] = {"input": str(Path(path).resolve()), "original_node": old}
    return values, sources


def alternating_cost_groups(nodes, estimates, counts, limit=None):
    groups = {}
    for node in nodes:
        path = node.split("::", 1)[0]
        cost = estimates[path] / counts[path]
        groups.setdefault(cost, deque()).append(node)
    queues = deque(groups[cost] for cost in sorted(groups, reverse=True))
    output = []
    take_high = True
    while queues and (limit is None or len(output) < limit):
        selected = queues[0] if take_high else queues[-1]
        output.append(selected.popleft())
        if not selected:
            queues.popleft() if take_high else queues.pop()
        take_high = not take_high
    for remaining in queues:
        output.extend(remaining)
    if Counter(output) != Counter(nodes):
        raise AssertionError("alternating groups changed collection multiplicity")
    for path in counts:
        if ([node for node in nodes if node.split("::", 1)[0] == path]
                != [node for node in output if node.split("::", 1)[0] == path]):
            raise AssertionError("alternating groups changed within-file order")
    return output


def initial_singleton_pairs(nodes, estimates, counts, workers):
    groups = {}
    for node in nodes:
        path = node.split("::", 1)[0]
        groups.setdefault(estimates[path] / counts[path], deque()).append(node)
    queues = deque(groups[cost] for cost in sorted(groups, reverse=True))
    def take(high):
        group = queues[0] if high else queues[-1]
        node = group.popleft()
        if not group:
            queues.popleft() if high else queues.pop()
        return node
    result = []
    for _ in range(workers):
        first = take(True)
        result.append(first)
        result.append(take(counts[first.split("::", 1)[0]] != 1))
    for remaining in queues:
        result.extend(remaining)
    if Counter(result) != Counter(nodes):
        raise AssertionError("singleton pairing changed node coverage")
    for path in counts:
        if ([node for node in nodes if node.split("::", 1)[0] == path]
                != [node for node in result if node.split("::", 1)[0] == path]):
            raise AssertionError("singleton pairing changed within-file order")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--collection", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--node-seconds", action="append", default=[])
    ap.add_argument("--node-map", help="JSON mapping old node ID to moved node ID")
    ap.add_argument("--node-floors", help="Explicit modeled node floors; these are not measurements")
    ap.add_argument("--fixture-model", help="Explicit module-fixture cold-start sensitivity JSON")
    ap.add_argument("--evidence-metadata", action="append", default=[])
    ap.add_argument("--workers", nargs="+", type=int, default=[4, 2])
    ap.add_argument("--job-overhead-seconds", type=float, default=0.0)
    ap.add_argument("--duration-multiplier", type=float, default=1.0)
    ap.add_argument("--duration-model", choices=("evidence-residual", "conservative-floor"), default="evidence-residual")
    ap.add_argument("--item-order", choices=("candidate", "legacy-descending", "actual-candidate", "alternating-cost-groups", "initial-cost-groups", "initial-singletons"), default="candidate")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if (any(count <= 0 for count in args.workers) or len(set(args.workers)) != len(args.workers)
            or not math.isfinite(args.job_overhead_seconds) or args.job_overhead_seconds < 0
            or not math.isfinite(args.duration_multiplier) or args.duration_multiplier < 1):
        raise ValueError("workers, overhead or duration multiplier are invalid")
    output = Path(args.out)
    producer_snapshot = output.with_suffix(".producer.source")
    if output.exists() or output.with_suffix(".md").exists() or producer_snapshot.exists():
        raise FileExistsError("refusing to replace existing simulation evidence")
    sharder, sharder_path = load_sharder(args.root)
    all_nodes = collection(args.collection)
    ordinary = sharder.partition_lanes(all_nodes)["ordinary"]
    weights = sharder.read_weights(args.weights)
    node_map = json_read(args.node_map) if args.node_map else {}
    if (not isinstance(node_map, dict)
            or any(type(old) is not str or type(new) is not str for old, new in node_map.items())
            or len(set(node_map.values())) != len(node_map)):
        raise ValueError("moved node mapping must be one-to-one strings")
    missing_targets = set(node_map.values()) - set(all_nodes)
    if missing_targets:
        raise ValueError("moved mapping has uncollected targets: " + repr(sorted(missing_targets)))
    measured, measured_sources = observations(args.node_seconds, node_map)
    fixture_model = json_read(args.fixture_model) if args.fixture_model else None
    floors, _ = observations([args.node_floors], node_map) if args.node_floors else ({}, {})
    counts = Counter(node.split("::", 1)[0] for node in ordinary)
    estimates = sharder._estimates(counts, weights)
    if args.duration_model == "conservative-floor":
        seconds = {node: max(measured.get(node, 0.0), floors.get(node, 0.0),
                            estimates[node.split("::", 1)[0]] / counts[node.split("::", 1)[0]])
                        * args.duration_multiplier for node in ordinary}
    else:
        seconds = {}
        for path in counts:
            members = [node for node in ordinary if node.split("::", 1)[0] == path]
            fixed = [node for node in members if node in measured or node in floors]
            unknown = [node for node in members if node not in measured and node not in floors]
            fixed_total = sum(max(measured.get(node, 0.0), floors.get(node, 0.0)) for node in fixed)
            share = max(0.0, estimates[path] - fixed_total) / len(unknown) if unknown else 0.0
            seconds.update({node: max(measured.get(node, 0.0), floors.get(node, 0.0))
                * args.duration_multiplier for node in fixed})
            seconds.update({node: share * args.duration_multiplier for node in unknown})
    profiles = []
    for shard_count, limit_seconds in ((12, 3600), (8, 4800)):
        assignments = sharder.balanced_files(counts, shard_count, weights)
        rows = []
        for index in range(1, shard_count + 1):
            files = {path for path, owner in assignments.items() if owner == index}
            selected = [node for node in ordinary if node.split("::", 1)[0] in files]
            local_counts = Counter(node.split("::", 1)[0] for node in selected)
            sort_estimates = sharder._estimates(local_counts, weights)
            # This is the plugin's stable within-shard item sort, not an LPT sort.
            selected.sort(key=lambda node: -sort_estimates[node.split("::", 1)[0]]
                          / counts[node.split("::", 1)[0]])
            simulations = {}
            for workers in args.workers:
                ordered = (alternating_cost_groups(selected, sort_estimates, local_counts,
                        limit=2 * workers if args.item_order == "initial-cost-groups" else None)
                    if args.item_order in ("alternating-cost-groups", "initial-cost-groups") and workers >= 2
                    and len(selected) >= 2 * workers else selected)
                if args.item_order == "initial-singletons" and workers >= 2 and len(selected) >= 2 * workers:
                    ordered = initial_singleton_pairs(selected, sort_estimates, local_counts, workers)
                actual_matches_virtual = None
                if args.item_order == "actual-candidate":
                    items = [SimpleNamespace(nodeid=node) for node in selected]
                    config = SimpleNamespace(workerinput={"workercount": workers},
                        getoption=lambda name, default=None: 1 if name == "maxschedchunk" else default)
                    actual = sharder._pair_initial_load_items(config, items,
                        {path: sort_estimates[path] / count for path, count in local_counts.items()}, local_counts)
                    ordered = [item.nodeid for item in actual]
                    expected = (initial_singleton_pairs(selected, sort_estimates, local_counts, workers)
                        if workers >= 2 and len(selected) >= 2 * workers else selected)
                    actual_matches_virtual = ordered == expected
                    if not actual_matches_virtual or Counter(map(id, actual)) != Counter(map(id, items)):
                        raise AssertionError("actual candidate ordering differs from reviewed proposal or item identities")
                simulation = simulate_xdist(ordered, seconds, workers, fixture_model, args.duration_multiplier)
                simulation["actual_ordering_matches_virtual"] = actual_matches_virtual
                total = simulation["makespan_seconds"] + args.job_overhead_seconds
                simulation.update(predicted_job_seconds=round(total, 3),
                    limit_margin_seconds=round(limit_seconds - total, 3),
                    within_limit=total < limit_seconds)
                simulations[str(workers)] = simulation
            rows.append({"shard": index, "items": len(selected), "files": sorted(files),
                "within_shard_sort_estimates": sort_estimates,
                "scheduling_weight_seconds": round(sum(estimates[path] for path in files), 3),
                "modeled_item_seconds": round(sum(seconds[node] for node in selected), 3),
                "longest_item_seconds": round(max((seconds[node] for node in selected), default=0), 3),
                "simulations": simulations})
        profiles.append({"shards": shard_count, "limit_seconds": limit_seconds, "rows": rows})
    import xdist.scheduler.load as scheduler_source
    measured_used = set(ordinary) & set(measured)
    with producer_snapshot.open("xb") as stream:
        stream.write(PRODUCER_RAW)
    report = {
        "label": args.label,
        "kind": "issue6289_ci_scheduling_estimate",
        "completed_simulation": True,
        "ci_success_proven": False,
        "inputs": {"collection": pin(args.collection), "weights": pin(args.weights),
            "candidate_sharder": pin(sharder_path), "producer": pin(producer_snapshot),
            "producer_original_path": str(Path(__file__).resolve()),
            "xdist_scheduler": pin(scheduler_source.__file__),
            "node_seconds": [pin(path) for path in args.node_seconds],
            "node_map": pin(args.node_map) if args.node_map else None,
            "node_floors": pin(args.node_floors) if args.node_floors else None,
            "fixture_model": pin(args.fixture_model) if args.fixture_model else None,
            "evidence_metadata": [pin(path) for path in args.evidence_metadata]},
        "software": {"python": sys.version, "pytest": importlib.metadata.version("pytest"),
                     "pytest_xdist": importlib.metadata.version("pytest-xdist")},
        "model": {"assignment": "candidate balanced_files over actual ordinary collected file set",
            "item_order": args.item_order,
            "item_order_basis": ("actual candidate _pair_initial_load_items after stable descending file weight/count"
                if args.item_order == "actual-candidate" else
                "stable descending file weight/count; explicitly selected optional virtual ordering"),
            "worker_scheduler": "actual installed xdist LoadScheduling; maxschedchunk=1; two-item lookahead",
            "duration_model": args.duration_model,
            "item_duration": ("known observed seconds or explicit censored floor; unknown nodes share nonnegative file-weight residual"
                if args.duration_model == "evidence-residual" else
                "max(retained observed seconds, explicit modeled floor, estimated file weight / ordinary item count)"),
            "duration_multiplier": args.duration_multiplier,
            "job_overhead_seconds": args.job_overhead_seconds,
            "event_ties": "ascending worker index",
            "workers": args.workers,
            "fixture_sensitivity": fixture_model is not None,
            "limitations": [
                "Observed seconds may be printed phase sums or timestamp intervals; consult pinned measurement metadata.",
                "Censored test runtime has no measured upper bound; explicit floor inputs are scheduling hypotheses, not measured runtime lower bounds.",
                "File-share floors do not upper-bound unknown individual long cases.",
                "No CPU or filesystem contention, retries or worker crashes are modeled; only explicitly supplied fixture cold-start sensitivity is modeled.",
                "Measured concurrent wall durations may already include contention; no division by worker count.",
                "Job setup, collection, uploads and teardown count only through explicit job overhead.",
                "Actual worker count must be verified from CI headers; maxprocesses is only a ceiling.",
                "Passing predicted limits does not certify future CI success."]},
        "collection": {"all": len(all_nodes), "unique_nodeids": len(set(all_nodes)),
            "ordinary": len(ordinary),
            "dedicated": len(all_nodes) - len(ordinary), "ordinary_files": len(counts),
            "measured_nodes_used": len(measured_used),
            "unmatched_observed_nodes": sorted(set(measured) - set(all_nodes))},
        "file_models": {path: {"items": counts[path], "scheduling_weight_seconds": estimates[path],
            "per_item_floor_seconds": estimates[path] / counts[path],
            "explicit_weight": path in weights} for path in sorted(counts)},
        "observed_nodes": {node: {"observed_seconds": measured[node],
            "modeled_seconds": seconds[node], **measured_sources[node]} for node in sorted(measured_used)},
        "explicit_node_floors": floors,
        "profiles": profiles}
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").replace(chr(64), "\\u0040")
    with output.open("x") as stream:
        stream.write(raw)
    markdown = [args.label + ": scheduling estimates, not CI success evidence.", "",
        "Explicit non-test job allowance: " + str(args.job_overhead_seconds) + " seconds. "
        "Duration stress multiplier: " + str(args.duration_multiplier) + ".", "",
        "Report SHA256: " + pin(output)["sha256"] + ".", ""]
    for profile in profiles:
        markdown.extend([str(profile["shards"]) + " shards; job limit " + str(profile["limit_seconds"]) + " seconds.", "",
            "| Shard | Workers | Predicted job seconds | Margin seconds |", "|---:|---:|---:|---:|"])
        for row in profile["rows"]:
            for workers in args.workers:
                result = row["simulations"][str(workers)]
                markdown.append("| " + " | ".join(str(value) for value in (row["shard"], workers,
                    result["predicted_job_seconds"], result["limit_margin_seconds"])) + " |")
        markdown.append("")
    markdown.extend(["Unknown long cases and censored runtimes have no measured upper bound. "
        "The two-worker case is a sensitivity analysis; the observed CI jobs used four workers. "
        "Contention and other fixture costs are not independently reconstructed.", ""])
    with output.with_suffix(".md").open("x") as stream:
        stream.write("\n".join(markdown))
    summary = {"output": pin(output), "profiles": [{"shards": profile["shards"],
        "worst_job_seconds": {str(workers): max(row["simulations"][str(workers)]["predicted_job_seconds"]
            for row in profile["rows"]) for workers in args.workers}} for profile in profiles]}
    print(json.dumps(summary, sort_keys=True))


def prepare_inputs():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--archive", required=True)
    ap.add_argument("--collection-log", required=True)
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--measurements", required=True)
    ap.add_argument("--additional-measurements", action="append", default=[])
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--long-case-floor", type=float, default=2500.0)
    ap.add_argument("--admission-floor", type=float, default=3052.96)
    ap.add_argument("--rehearsal-floor", type=float, default=600.0)
    ap.add_argument("--split-prescribed", action="store_true")
    ap.add_argument("--split-attribution-saved", action="store_true")
    args = ap.parse_args(sys.argv[2:])
    out = Path(args.outdir)
    out.mkdir(exist_ok=False)
    with (out / "producer.source").open("xb") as stream:
        stream.write(PRODUCER_RAW)
    def save(name, value):
        raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").replace(chr(64), "\\u0040")
        with (out / name).open("x") as stream:
            stream.write(raw)
    sharder, _ = load_sharder(args.root)
    after = collection(args.collection_log)
    error_files = set(re.findall(r"^ERROR (tests/\S+\.py)$", Path(args.collection_log).read_text(), re.M))
    analysis = json_read(args.analysis)
    supplemental = []
    for job in analysis["jobs"]:
        for row in job["started_nodes"] + job["finished_nodes"]:
            node = row["node"]
            if node.split("::", 1)[0] in error_files and node not in supplemental:
                supplemental.append(node)
    if error_files != {node.split("::", 1)[0] for node in supplemental}:
        raise ValueError("CI did not supply every failed-collection file")
    after += supplemental
    after.sort(key=lambda node: node.split("::", 1)[0])
    original = "tests/test_native_shared_denials.py"
    moves = {original + "::test_denial_live_and_saved[" + tool + "-not_prescribed]":
        "tests/test_native_shared_denials_" + tool.lower() + ".py::test_denial_live_and_saved[" + tool + "-not_prescribed]"
        for tool in ("Bash", "Read", "Write")}
    inverse = {new: old for old, new in moves.items()}
    before = [inverse.get(node, node) for node in after]
    denial_order = [original + "::test_denial_live_and_saved[" + suffix + "]" for suffix in (
        "Bash-not_prescribed", "Bash-prescribed", "Bash-unclassifiable", "Read-not_prescribed", "Write-not_prescribed")]
    denial_order += [original + "::test_denied_file_replay_never_resolves_or_reads_target[" + tool + "]" for tool in ("Read", "Write")]
    before.sort(key=lambda node: (node.split("::", 1)[0], denial_order.index(node) if node in denial_order else 0))
    if args.split_prescribed:
        old = original + "::test_denial_live_and_saved[Bash-prescribed]"
        new = "tests/test_native_shared_denials_prescribed.py::test_denial_live_and_saved[Bash-prescribed]"
        moves[old] = new
        after = [new if node == old else node for node in after]
        after.sort(key=lambda node: node.split("::", 1)[0])
    if args.split_attribution_saved:
        for node in after:
            if node.startswith("tests/test_native_shared_attribution.py::test_saved_"):
                moves[node] = node.replace("tests/test_native_shared_attribution.py::", "tests/test_native_shared_attribution_saved.py::", 1)
        after = [moves.get(node, node) for node in after]
        after.sort(key=lambda node: node.split("::", 1)[0])
    baseline = json_read(Path(args.archive) / "utils/ci_test_durations.json")
    save("before-nodeids.json", before)
    save("after-nodeids.json", after)
    save("moved-node-map.json", moves)
    save("baseline-weights.json", baseline)
    measurements = json_read(args.measurements)
    if args.additional_measurements:
        combined = dict(measurements["per_node"])
        for extra_path in args.additional_measurements:
            for node, record in json_read(extra_path)["per_node"].items():
                if node not in combined or record["seconds"] > combined[node]["seconds"]:
                    combined[node] = record
        files = {}
        eligible = set(sharder.partition_lanes(before)["ordinary"])
        for node, record in combined.items():
            if node not in eligible:
                continue
            row = files.setdefault(node.split("::", 1)[0], {"measured_seconds": 0.0, "completed_nodes": 0})
            row["measured_seconds"] += record["seconds"]
            row["completed_nodes"] += 1
        measurements = {"per_node": combined, "files": files}
    ordinary = sharder.partition_lanes(before)["ordinary"]
    counts = Counter(node.split("::", 1)[0] for node in ordinary)
    changed = {}
    proposed = json.loads(json.dumps(baseline))
    for path, row in measurements["files"].items():
        if path not in counts:
            continue
        observed = row["measured_seconds"]
        old = baseline["file_seconds"].get(path)
        if observed >= 300 and (old is None or observed > old * 2):
            proposed["file_seconds"][path] = round(observed, 3)
            changed[path] = {"before": old, "after": round(observed, 3),
                "basis": "retained CI observed node seconds; incomplete files are lower bounds",
                "completed_nodes": row["completed_nodes"], "collected_ordinary_nodes": counts[path]}
    floors = {node: args.long_case_floor for node in denial_order[:5]}
    stalled = "tests/test_native_admission_failure.py::test_shared_engine_stalled_admission_publishes_and_stops_timing"
    floors[stalled] = args.admission_floor
    rehearsal = "tests/test_native_canary_packet_rehearsal.py::test_synthetic_preparation_roundtrips_without_production_authority"
    floors[rehearsal] = args.rehearsal_floor
    explicit = {original: (1 if args.split_prescribed else 2) * args.long_case_floor + 0.02,
        "tests/test_native_admission_failure.py": max(args.admission_floor + 12,
            measurements["files"].get("tests/test_native_admission_failure.py", {}).get("measured_seconds", 0)),
        "tests/test_native_canary_packet_rehearsal.py": args.rehearsal_floor +
            measurements["files"].get("tests/test_native_canary_packet_rehearsal.py", {}).get("measured_seconds", 0)}
    explicit.update({new.split("::", 1)[0]: args.long_case_floor for new in moves.values()})
    if args.split_attribution_saved:
        for path in ("tests/test_native_shared_attribution.py", "tests/test_native_shared_attribution_saved.py"):
            value = sum(record["seconds"] for node, record in measurements["per_node"].items()
                if node.startswith("tests/test_native_shared_attribution.py::")
                and moves.get(node, node).split("::", 1)[0] == path)
            proposed["file_seconds"][path] = round(value, 3)
            changed[path] = {"before": baseline["file_seconds"].get(path), "after": round(value, 3),
                "basis": "hypothetical pure saved-attribution move; retained per-node timing sum"}
            explicit.pop(path, None)
    for path, value in explicit.items():
        proposed["file_seconds"][path] = value
        changed[path] = {"before": baseline["file_seconds"].get(path), "after": value,
            "basis": "provisional censored-lifecycle scenario; not a measured upper bound"}
    proposed["issue6289_provisional_scenario"] = {"changes": changed,
        "measurements": pin(args.measurements), "long_case_floor_seconds": args.long_case_floor,
        "additional_measurements": [pin(path) for path in args.additional_measurements],
        "not_ci_success": True}
    save("provisional-weights.json", proposed)
    save("file-seconds-patch.json", {path: proposed["file_seconds"][path] for path in changed})
    save("modeled-node-floors.json", floors)
    stressed = dict(floors)
    for node in denial_order[:5]:
        stressed[node] = 3000.0
    stressed[rehearsal] = 1200.0
    save("modeled-node-floors-stress.json", stressed)
    packet_file = "tests/test_native_packet_full_chain.py"
    consumers = [node for node in before if node.startswith(packet_file + "::")
        and node != packet_file + "::test_full_chain_canary"]
    setup = {node: sum(record["seconds"] for record in measurements["per_node"].get(node, {}).get("printed_records", [])
        if record["phase"] == "setup") for node in consumers}
    save("fixture-sensitivity.json", {"fixtures": [{"module": packet_file,
        "consumer_nodes": consumers, "recorded_setup_seconds": setup,
        "cold_setup_seconds": max(setup.values(), default=0.0),
        "source": pin(Path(args.archive) / packet_file),
        "basis": "Complete-chain module-fixture sensitivity: subtract printed setup from recorded nodes; add maximum observed setup on each worker module entry requiring the fixture. This is not an upper bound."}]})
    assignments = sharder.balanced_files(counts, 12, baseline["file_seconds"])
    by_shard = []
    for job in analysis["jobs"]:
        match = re.search(r"shard (\d+)$", job["name"])
        if not match:
            continue
        index = int(match.group(1))
        expected = [node for node in ordinary if assignments[node.split("::", 1)[0]] == index]
        finished = Counter(row["node"] for row in job["finished_nodes"])
        started = {row["node"] for row in job["started_nodes"]}
        missing = list((Counter(expected) - finished).elements())
        foreign = sorted((set(finished) | started) - set(expected))
        by_shard.append({"shard": index, "job": job["id"], "header_items": job["collected_items"],
            "reconstructed_items": len(expected), "count_matches": len(expected) == job["collected_items"],
            "observed_foreign_nodes": foreign,
            "files": sorted({node.split("::", 1)[0] for node in expected}),
            "uncompleted_nodes": missing,
            "uncompleted_started": [node for node in missing if node in started],
            "not_observed_started": [node for node in missing if node not in started]})
    save("baseline-shard-validation.json", {"shards": by_shard})
    save("inputs-provenance.json", {"producer": pin(out / "producer.source"), "collection_log": pin(args.collection_log),
        "analysis": pin(args.analysis), "measurements": pin(args.measurements),
        "additional_measurements": [pin(path) for path in args.additional_measurements],
        "local_collected": len(after) - len(supplemental), "ci_supplement_count": len(supplemental),
        "hypothetical_additional_prescribed_split": args.split_prescribed,
        "hypothetical_saved_attribution_split": args.split_attribution_saved,
        "supplemental_files": sorted(error_files), "supplemental_nodes": supplemental,
        "limitation": "Supplemental missing-file item order follows first CI log observation, not a saved full collection order.",
        "moved_nodes": moves, "provisional_weight_changes": changed})
    print(json.dumps({"directory": str(out), "nodes": len(after), "supplement": len(supplemental),
        "header_matches": all(row["count_matches"] and not row["observed_foreign_nodes"] for row in by_shard),
        "weight_changes": len(changed)}))


def corrected_baseline_inventory(baseline, archive, output):
    prior = json_read(baseline / "inputs-provenance.json")
    analysis = json_read(prior["analysis"]["path"])
    sharder, sharder_path = load_sharder(archive)
    ordinary = sharder.partition_lanes(collection(baseline / "before-nodeids.json"))["ordinary"]
    counts = Counter(node.split("::", 1)[0] for node in ordinary)
    assignment = sharder.balanced_files(counts, 12, sharder.read_weights(baseline / "baseline-weights.json"))
    rows = []
    for job in analysis["jobs"]:
        match = re.search(r"shard (\d+)$", job["name"])
        if not match:
            continue
        index = int(match.group(1))
        log = Path(prior["analysis"]["path"]).parent / ("job-" + str(job["id"]) + ".api-escaped.log")
        started, finished, records = Counter(), Counter(), []
        for line_number, line in enumerate(log.read_text().splitlines(), 1):
            # The retained analysis deduplicates node identities. Parse raw events
            # here so a genuinely duplicate collected ID can finish twice.
            result = re.search(r"\[gw\d+\]\s+\[\s*\d+%\]\s+(PASSED|FAILED|SKIPPED|XFAIL|XPASS|ERROR)\s+(tests/.*\.py::.*)$", line)
            if result:
                node = result.group(2).strip()
                finished[node] += 1
                records.append({"node": node, "status": result.group(1), "line": line_number})
            start = re.match(r"^\S+Z\s+(tests/.*\.py::.*)$", line)
            if start:
                started[start.group(1).strip()] += 1
        expected = Counter(node for node in ordinary if assignment[node.split("::", 1)[0]] == index)
        missing = expected - finished
        observed_incomplete = missing & (started - finished)
        duplicates = {node: {"expected": count, "started": started[node], "finished": finished[node],
            "finish_records": [record for record in records if record["node"] == node]}
            for node, count in expected.items() if count > 1}
        rows.append({"shard": index, "job": job["id"], "log": pin(log),
            "header_items": job["collected_items"], "reconstructed_items": sum(expected.values()),
            "count_matches": sum(expected.values()) == job["collected_items"],
            "finished_unique_identities": len(finished), "finished_status_occurrences": sum(finished.values()),
            "completed_expected_occurrences": sum((expected & finished).values()),
            "missing_occurrences": sum(missing.values()),
            "uncompleted_nodes": list(missing.elements()),
            "uncompleted_started": list(observed_incomplete.elements()),
            "not_observed_started": list((missing - observed_incomplete).elements()),
            "observed_foreign_nodes": sorted((set(finished) | set(started)) - set(expected)),
            "excess_finish_occurrences": dict(finished - expected),
            "duplicate_collected_identities": duplicates})
    result = {"kind": "issue6289_baseline_occurrence_inventory", "shards": sorted(rows, key=lambda row: row["shard"]),
        "inputs": {"legacy_inventory": pin(baseline / "baseline-shard-validation.json"),
            "analysis": pin(prior["analysis"]["path"]), "collection": pin(baseline / "before-nodeids.json"),
            "weights": pin(baseline / "baseline-weights.json"), "sharder": pin(sharder_path)},
        "correction": "Raw status occurrences replace deduplicated analysis identities; missing means no retained terminal status, not proof that a test never ran.",
        "limitations": ["GitHub masking can change an identity in the raw log; foreign IDs remain explicit and are not silently normalized."]}
    with output.open("x") as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + "\n").replace(chr(64), "\\u0040"))
    return pin(output)


def final_inputs():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--archive", required=True)
    ap.add_argument("--collection-log")
    ap.add_argument("--provisional-from-source", action="store_true")
    ap.add_argument("--baseline-dir", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args(sys.argv[2:])
    root, baseline, archive = Path(args.root), Path(args.baseline_dir), Path(args.archive)
    out = Path(args.outdir)
    out.mkdir(exist_ok=False)
    def save(name, value):
        with (out / name).open("x") as stream:
            stream.write((json.dumps(value, indent=2, sort_keys=True) + "\n").replace(chr(64), "\\u0040"))
    with (out / "producer.source").open("xb") as stream:
        stream.write(PRODUCER_RAW)
    prior = json_read(baseline / "inputs-provenance.json")
    before = collection(baseline / "before-nodeids.json")
    moves = json_read(baseline / "moved-node-map.json")
    if bool(args.collection_log) == args.provisional_from_source:
        raise ValueError("choose actual collection log or provisional source reconstruction")
    expected_errors = set(prior["supplemental_files"])
    if args.collection_log:
        actual = collection(args.collection_log)
        errors = set(re.findall(r"^ERROR (tests/\S+\.py)$", Path(args.collection_log).read_text(), re.M))
        if errors != expected_errors:
            raise ValueError("final collection errors differ from preserved FAIRSCAPE supplement")
    for path in expected_errors:
        if (root / path).read_bytes() != (archive / path).read_bytes():
            raise ValueError("supplemented FAIRSCAPE source changed")
    new_file = "tests/test_ci_shard_initial_load.py"
    new_nodes = [new_file + "::" + node.name for node in ast.parse((root / new_file).read_text()).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
    if len(new_nodes) != 5 or len(moves) != 25:
        raise ValueError("expected five new checks and twenty-five moved nodes")
    if args.provisional_from_source:
        actual = [moves.get(node, node) for node in before] + new_nodes
        local_count = None
    else:
        local_count = len(actual)
        actual += prior["supplemental_nodes"]
    actual.sort(key=lambda node: node.split("::", 1)[0])
    expected = Counter(moves.get(node, node) for node in before) + Counter(new_nodes)
    if Counter(actual) != expected:
        raise ValueError("actual final node multiset differs: missing=" + repr(list((expected-Counter(actual)).elements()))
            + "; extra=" + repr(list((Counter(actual)-expected).elements())))
    inverse = {new: old for old, new in moves.items()}
    selected_files = {"tests/test_native_shared_denials.py", "tests/test_native_shared_attribution.py"}
    old_selected = [node for node in before if node.split("::", 1)[0] in selected_files]
    normalized_selected = [inverse.get(node, node) for node in actual
        if inverse.get(node, node).split("::", 1)[0] in selected_files]
    if len(old_selected) != 55 or Counter(old_selected) != Counter(normalized_selected):
        raise ValueError("the fifty-five existing denial/attribution cases changed")
    sharder, sharder_path = load_sharder(root)
    weights = sharder.read_weights(root / "utils/ci_test_durations.json")
    expected_weights = sharder.read_weights(baseline / "baseline-weights.json")
    patch = {path: round(value, 3) for path, value in json_read(baseline / "file-seconds-patch.json").items()}
    expected_weights.update(patch)
    if weights != expected_weights:
        raise ValueError("actual weights differ from the selected rounded twenty-five-entry patch")
    save("final-nodeids.json", actual)
    save("rounded-file-seconds-patch.json", patch)
    inventory_pin = corrected_baseline_inventory(baseline, archive, out / "baseline-occurrence-inventory.json")
    files = {moves.get(node, node).split("::", 1)[0] for node in old_selected} | {new_file}
    save("collection-verification.json", {
        "passed": True, "kind": "issue6289_final_collection_normalization",
        "provisional": args.provisional_from_source, "final_collection_verified": not args.provisional_from_source,
        "roster_basis": "source reconstruction pending pytest collection" if args.provisional_from_source else "actual pytest collection plus preserved unchanged FAIRSCAPE supplement",
        "local_collected": local_count, "supplemental_occurrences": len(prior["supplemental_nodes"]),
        "total_occurrences": len(actual), "unique_nodeids": len(set(actual)),
        "ordinary_occurrences": len(sharder.partition_lanes(actual)["ordinary"]),
        "existing_selected_cases": len(old_selected), "moved_cases": len(moves), "added_cases": new_nodes,
        "exact_counter_baseline_plus_five": True, "existing_fifty_five_normalized_equal": True,
        "weights_equal_rounded_selected_patch": True,
        "inputs": {"producer": pin(out / "producer.source"), "collection_log": pin(args.collection_log) if args.collection_log else None,
            "corrected_baseline_inventory": inventory_pin,
            "baseline_collection": pin(baseline / "before-nodeids.json"),
            "move_map": pin(baseline / "moved-node-map.json"), "supplement_provenance": pin(baseline / "inputs-provenance.json"),
            "actual_weights": pin(root / "utils/ci_test_durations.json"), "actual_sharder": pin(sharder_path)},
        "actual_test_sources": {path: pin(root / path) for path in sorted(files)},
        "limitations": ["Collection identity check only; body equivalence and test outcomes are separate evidence.",
            "FAIRSCAPE nodes remain supplemented from retained CI evidence after checking unchanged source bytes."]})
    print(json.dumps({"directory": str(out), "total": len(actual), "existing": len(old_selected),
        "moved": len(moves), "added": len(new_nodes), "passed": True}))


def counterfactual_inputs():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--actual-inputs", required=True)
    ap.add_argument("--baseline-dir", required=True)
    ap.add_argument("--undo", choices=("prescribed", "saved-attribution"), required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args(sys.argv[2:])
    out, actual, baseline = Path(args.outdir), Path(args.actual_inputs), Path(args.baseline_dir)
    out.mkdir(exist_ok=False)
    with (out / "producer.source").open("xb") as stream:
        stream.write(PRODUCER_RAW)
    original_moves = json_read(baseline / "moved-node-map.json")
    prefix = ("tests/test_native_shared_denials_prescribed.py::" if args.undo == "prescribed"
        else "tests/test_native_shared_attribution_saved.py::")
    inverse = {new: old for old, new in original_moves.items() if new.startswith(prefix)}
    moves = {old: new for old, new in original_moves.items() if new not in inverse}
    nodes = [inverse.get(node, node) for node in collection(actual / "final-nodeids.json")]
    # Restore the exact baseline within-file order for the recombined file.
    baseline_order = {node: index for index, node in enumerate(collection(baseline / "before-nodeids.json"))}
    reverse_all = {new: old for old, new in original_moves.items()}
    nodes.sort(key=lambda node: (node.split("::", 1)[0], baseline_order.get(reverse_all.get(node, node), len(baseline_order))))
    weights_path = Path(args.root) / "utils/ci_test_durations.json"
    weights = json_read(weights_path)
    source_file = prefix.split("::", 1)[0]
    target_file = next(iter(inverse.values())).split("::", 1)[0]
    weights["file_seconds"][target_file] = round(weights["file_seconds"][target_file] + weights["file_seconds"].pop(source_file), 3)
    def save(name, value):
        with (out / name).open("x") as stream:
            stream.write((json.dumps(value, indent=2, sort_keys=True) + "\n").replace(chr(64), "\\u0040"))
    save("nodeids.json", nodes)
    save("weights.json", weights)
    save("moved-node-map.json", moves)
    save("provenance.json", {"kind": "issue6289_counterfactual_inputs", "hypothetical": True,
        "undone_move": args.undo, "undone_node_count": len(inverse),
        "actual_inputs": pin(actual / "collection-verification.json"), "actual_weights": pin(weights_path),
        "baseline_move_map": pin(baseline / "moved-node-map.json"), "producer": pin(out / "producer.source"),
        "limitation": "Offline scheduling counterfactual only; candidate files are untouched and no tests ran."})
    print(json.dumps({"directory": str(out), "undone": len(inverse), "nodes": len(nodes)}))


def summarize_results():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(sys.argv[2:])
    rows = []
    for path in args.report:
        report = json_read(path)
        rows.append({"label": report["label"], "report": pin(path), "model": report["model"],
            "collection": report["collection"], "inputs": report["inputs"],
            "profiles": [{"shards": profile["shards"], "limit_seconds": profile["limit_seconds"],
                "worst": {str(workers): max((dict(shard=row["shard"], **row["simulations"][str(workers)])
                    for row in profile["rows"]), key=lambda value: value["predicted_job_seconds"])
                    for workers in report["model"]["workers"]}}
                for profile in report["profiles"]]})
    out = Path(args.out)
    snapshot = out.with_suffix(".producer.source")
    with snapshot.open("xb") as stream:
        stream.write(PRODUCER_RAW)
    with out.open("x") as stream:
        stream.write((json.dumps({"producer": pin(snapshot), "reports": rows}, indent=2, sort_keys=True) + "\n").replace(chr(64), "\\u0040"))
    print(json.dumps({"output": pin(out), "summaries": [{"label": row["label"],
        "profiles": [{"shards": p["shards"], "worst": {k: v["predicted_job_seconds"] for k, v in p["worst"].items()}}
            for p in row["profiles"]]} for row in rows]}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prepare-inputs":
        prepare_inputs()
    elif len(sys.argv) > 1 and sys.argv[1] == "final-inputs":
        final_inputs()
    elif len(sys.argv) > 1 and sys.argv[1] == "counterfactual-inputs":
        counterfactual_inputs()
    elif len(sys.argv) > 1 and sys.argv[1] == "summarize-results":
        summarize_results()
    else:
        main()
