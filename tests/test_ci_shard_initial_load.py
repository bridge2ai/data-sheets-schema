"""Regression coverage for xdist initial queue pairing, issue 6289."""

from collections import Counter
import json

from tests.test_ci_sharding import _run


def _initial_load_queues_for_test(collected, workers):
    from types import SimpleNamespace
    from xdist.scheduler.load import LoadScheduling

    class Config:
        def getvalue(self, name):
            assert name == "tx"
            return ["popen"] * workers

        def getoption(self, name):
            assert name == "maxschedchunk"
            return 1

    class Worker:
        def __init__(self, number):
            self.gateway = SimpleNamespace(id=f"gw{number}")
            self.shutting_down = False
            self.sent = []

        def send_runtest_some(self, indices):
            self.sent.extend(indices)

        def shutdown(self):
            self.shutting_down = True

    scheduler = LoadScheduling(Config())
    nodes = [Worker(number) for number in range(workers)]
    for node in nodes:
        scheduler.add_node(node)
        scheduler.add_node_collection(node, collected)
    scheduler.schedule()
    assert Counter(index for node in nodes for index in node.sent) + Counter(
        scheduler.pending) == Counter(range(len(collected)))
    return [[collected[index] for index in node.sent] for node in nodes]


def _weighted_worker_order_for_test(nodeids, weights, workers, chunk=1, remote=True):
    from types import SimpleNamespace
    from xdist.remote import setup_config
    from utils.pytest_shard import pytest_collection_modifyitems

    class Config:
        def __init__(self):
            self.option = SimpleNamespace(numprocesses=workers, maxschedchunk=chunk,
                                          dist="load")
            self._d4d_shard_weights = weights
            self.deselected = []
            self.hook = SimpleNamespace(pytest_deselected=self.deselected_items)

        def getvalue(self, name):
            return getattr(self.option, name)

        def getoption(self, name, default=None):
            if name == "--ci-shard":
                return "1/1"
            if name == "--ci-lane":
                return None
            return getattr(self.option, name, default)

        def deselected_items(self, items):
            self.deselected.extend(items)

    config = Config()
    if remote:
        setup_config(config, None)
        config.workerinput = {"workercount": workers}
        assert config.option.numprocesses is None
        assert config.option.dist == "no"
    items = [SimpleNamespace(nodeid=nodeid) for nodeid in nodeids]
    originals = {id(item): item for item in items}
    pytest_collection_modifyitems(config, items)
    assert not config.deselected
    assert Counter(map(id, items)) == Counter(originals.keys())
    return [item.nodeid for item in items]


def test_initial_load_pairs_separate_expensive_files_for_two_and_four_workers(tmp_path):
    for workers in (2, 4):
        root = tmp_path / str(workers)
        root.mkdir()
        expensive = []
        weights = {}
        for number in range(workers):
            name = f"test_long_{number}.py"
            (root / name).write_text("def test_expensive(): pass\n")
            expensive.append(f"{name}::test_expensive")
            weights[name] = 100 - number
        cheap = [f"test_cheap.py::test_{number}" for number in range(4 * workers)]
        (root / "test_cheap.py").write_text("\n".join(
            f"def test_{number}(): pass" for number in range(4 * workers)))
        weights["test_cheap.py"] = len(cheap)
        (root / "timings.json").write_text(json.dumps({
            "schema_version": 1, "file_seconds": weights}))
        result = _run(root, "--collect-only", "--ci-shard=1/1",
                      "--ci-shard-timings=timings.json", "-n", str(workers),
                      "--dist=load", "--maxschedchunk=1")
        assert result.returncode == 0, result.stdout + result.stderr
        collected = [line for line in result.stdout.splitlines() if "::test_" in line]
        assert Counter(collected) == Counter(expensive + cheap)
        assert collected[0] == expensive[0]
        # Exercise the actual worker-side option rewriting as well as the
        # controller's collect-only integer worker-count fallback.
        remote = _weighted_worker_order_for_test(cheap + expensive, weights, workers)
        assert remote == collected
        queues = _initial_load_queues_for_test(collected, workers)
        assert all(len(queue) == 2 for queue in queues)
        assert all(sum(node in expensive for node in queue) == 1 for queue in queues)
        assert collected[2 * workers:] == cheap[workers:]


def test_initial_load_pairing_preserves_ties_file_order_and_occurrences():
    nodeids = ["test_a.py::test_same", "test_a.py::test_same",
               "test_b.py::test_0", "test_b.py::test_1",
               "test_c.py::test_0", "test_c.py::test_1",
               "test_d.py::test_0", "test_d.py::test_1",
               "test_m.py::test_0", "test_m.py::test_1"]
    weights = {"test_a.py": 20, "test_b.py": 20, "test_c.py": 2,
               "test_d.py": 2, "test_m.py": 10}
    ordered = _weighted_worker_order_for_test(nodeids, weights, 2)
    assert Counter(ordered) == Counter(nodeids)
    assert ordered[0] == nodeids[0]
    for paths in (("test_a.py", "test_b.py"), ("test_c.py", "test_d.py"),
                  ("test_m.py",)):
        assert [node for node in ordered if node.split("::", 1)[0] in paths] == [
            node for node in nodeids if node.split("::", 1)[0] in paths]
    for path in weights:
        assert [node for node in ordered if node.startswith(path + "::")] == [
            node for node in nodeids if node.startswith(path + "::")]
    assert ordered == nodeids[:4] + nodeids[8:10] + nodeids[4:8]
    singletons = ["test_x.py::test_expensive", "test_y.py::test_expensive"]
    cheap = nodeids[4:8]
    paired = _weighted_worker_order_for_test(cheap + singletons,
        {"test_x.py": 100, "test_y.py": 100, "test_c.py": 2, "test_d.py": 2}, 2)
    assert paired[:4] == [singletons[0], cheap[0], singletons[1], cheap[1]]
    assert [node for node in paired if node in singletons] == singletons
    assert [node for node in paired if node in cheap] == cheap
    assert Counter(paired) == Counter(cheap + singletons)


def test_initial_load_pairing_keeps_multi_case_pairs_and_original_file_counts():
    first = "test_single_first.py::test_expensive"
    second = "test_single_second.py::test_expensive"
    multiple = [f"test_multiple.py::test_{number}" for number in range(3)]
    cheap = [f"test_cheap.py::test_{number}" for number in range(8)]
    weights = {"test_single_first.py": 100, "test_multiple.py": 270,
               "test_single_second.py": 80, "test_cheap.py": 8}
    original = cheap + multiple + [first, second]
    ordered = _weighted_worker_order_for_test(original, weights, 4)
    assert Counter(ordered) == Counter(original)
    queues = _initial_load_queues_for_test(ordered, 4)
    assert queues == [[first, cheap[0]], multiple[:2],
                      [multiple[2], second], cheap[1:3]]
    assert ordered[8:] == cheap[3:]
    assert [node for node in ordered if node in multiple] == multiple
    assert [node for node in ordered if node in cheap] == cheap


def test_initial_load_pairing_keeps_equal_cost_and_ineligible_modes():
    equal = [f"test_equal.py::test_{number}" for number in range(8)]
    assert _weighted_worker_order_for_test(equal, {"test_equal.py": 8}, 4) == equal
    nodeids = [f"test_cheap.py::test_{number}" for number in range(7)] + [
        "test_long.py::test_expensive"]
    weights = {"test_cheap.py": 7, "test_long.py": 100}
    descending = nodeids[-1:] + nodeids[:-1]
    for workers in (None, 0, 1, "logical", True):
        assert _weighted_worker_order_for_test(nodeids, weights, workers) == descending
    for chunk in (None, 2):
        assert _weighted_worker_order_for_test(nodeids, weights, 2, chunk) == descending


def test_small_collections_keep_descending_order_for_round_robin_workers():
    expensive = [f"test_long_{number}.py::test_expensive" for number in range(3)]
    cheap = [f"test_cheap.py::test_{number}" for number in range(3)]
    weights = {node.split("::", 1)[0]: 100 - number
               for number, node in enumerate(expensive)}
    weights["test_cheap.py"] = 3
    ordered = _weighted_worker_order_for_test(cheap + expensive, weights, 4)
    assert ordered == expensive + cheap
    queues = _initial_load_queues_for_test(ordered, 4)
    assert all(sum(node in expensive for node in queue) <= 1 for queue in queues)
