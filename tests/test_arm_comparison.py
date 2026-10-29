"""The receipt rows of the cross-arm table (#902, #831).

A count without its denominator compares nothing: receiptable leaves run from
142 to 508 within one arm. These pin the arithmetic behind the pooled section
— in particular that a rate's numerator and denominator come from the same set
of records, which is the mis-measure #831's own body made by dividing by a
list capped at 50 entries.
"""
import importlib.util
import hashlib
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "arm_comparison.py"


def _module():
    spec = importlib.util.spec_from_file_location("arm_comparison", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bundle_record(tmp_path, project="AI_READI", *, old=b"original", current=None):
    """Independent bundle/manifest pins for #4762, including changed disk bytes."""
    import yaml

    bundle = tmp_path / f"{project}.txt"
    bundle.write_bytes(old if current is None else current)
    manifest = tmp_path / f"{project}_chunks.yaml"
    raw = yaml.safe_dump({
        "bundle": bundle.name, "bundle_md5": hashlib.md5(old).hexdigest(),
        "chunks": [],
    }).encode()
    manifest.write_bytes(raw)
    return {
        "run": {"project": project, "label": "rep1"},
        "inputs": {"bundle_path": bundle.name,
                   "bundle_md5": hashlib.md5(old).hexdigest(),
                   "chunks": {"path": manifest.name,
                              "sha256": hashlib.sha256(raw).hexdigest()}},
    }, manifest, raw


def test_bundle_drift_checks_every_arm_project_and_replicate(tmp_path):
    from copy import deepcopy
    from data_sheets_schema.evaluation.arm_comparison import compare_bundle_drift

    records = []
    for project in ("AI_READI", "CM4AI", "VOICE"):
        rec, _, _ = _bundle_record(tmp_path, project, current=b"new")
        records.append(rec)
    matching, _, _ = _bundle_record(tmp_path, "CHORUS")
    latest = deepcopy(records[0])
    latest["inputs"]["bundle_md5"] = hashlib.md5(b"new").hexdigest()
    latest["inputs"].pop("chunks")
    mixed = deepcopy(matching)
    mixed["run"]["label"] = "rep2"
    mixed["inputs"]["bundle_md5"] = "a" * 32
    result = compare_bundle_drift({
        "v6": records, "v7": [matching, mixed], "v8": [matching],
        "v10": [latest], "unrun": [],
    }, tmp_path)
    assert result["v6"]["disk"] == {"match": 0, "drift": 3, "unknown": 0}
    assert result["v6"]["manifest"] == {"match": 3, "drift": 0, "unknown": 0}
    assert result["v7"]["disk"] == {"match": 1, "drift": 1, "unknown": 0}
    assert result["v7"]["manifest"]["drift"] == 1
    assert result["v8"]["disk"]["match"] == 1
    assert result["v10"]["disk"]["match"] == 1
    assert result["v10"]["manifest"]["unknown"] == 1
    assert result["unrun"]["count"] == 0


def test_bundle_drift_recovers_pinned_manifest_not_current_replacement(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, manifest, original = _bundle_record(tmp_path, current=b"new")
    manifest.write_bytes(b"bundle: AI_READI.txt\nbundle_md5: " + b"0" * 32 + b"\n")
    calls = []

    def recover(path, **pins):
        calls.append((path, pins))
        return original, {"commit": "a" * 40}

    result = bundle_drift(record, tmp_path, recover=recover)
    assert calls == [(manifest.name, {"md5": None, "sha256": hashlib.sha256(original).hexdigest()})]
    assert result["disk_status"] == "drift"
    assert result["manifest_status"] == "match"
    assert result["manifest_basis"] == "pinned manifest recovered from history"
    assert manifest.read_bytes().endswith(b"0" * 32 + b"\n")


@pytest.mark.parametrize("recovery", ["absent", "wrong_bytes", "git_unavailable"])
def test_bundle_drift_unavailable_history_never_uses_changed_manifest(tmp_path, recovery):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, manifest, _ = _bundle_record(tmp_path)
    manifest.write_bytes(b"changed")

    def recover(*args, **kwargs):
        if recovery == "git_unavailable":
            raise RuntimeError("shallow checkout")
        return None if recovery == "absent" else (b"changed", {})

    result = bundle_drift(record, tmp_path, recover=recover)
    assert result["disk_status"] == "match"
    assert result["manifest_status"] == "unknown"
    assert result["manifest_md5"] is None


def test_bundle_drift_requires_every_manifest_hash(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, _, raw = _bundle_record(tmp_path)
    record["inputs"]["chunks"]["md5"] = "0" * 32
    result = bundle_drift(record, tmp_path, recover=lambda *a, **k: (raw, {}))
    assert result["manifest_status"] == "unknown"


def test_bundle_drift_rejects_hash_pinned_duplicate_manifest_keys(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, manifest, raw = _bundle_record(tmp_path)
    raw += b"bundle_md5: " + b"0" * 32 + b"\n"
    manifest.write_bytes(raw)
    record["inputs"]["chunks"]["sha256"] = hashlib.sha256(raw).hexdigest()
    result = bundle_drift(record, tmp_path)
    assert result["manifest_md5"] is None
    assert result["manifest_status"] == "unknown"


def test_bundle_drift_history_lookup_uses_recorded_name_after_symlink_change(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, manifest, original = _bundle_record(tmp_path)
    target = tmp_path / "new_chunks.yaml"
    target.write_bytes(b"changed")
    manifest.unlink()
    manifest.symlink_to(target)
    calls = []

    def recover(path, **pins):
        calls.append(path)
        return original, {}

    assert bundle_drift(record, tmp_path, recover=recover)["manifest_status"] == "match"
    assert calls == [record["inputs"]["chunks"]["path"]]


@pytest.mark.parametrize("inputs", [{}, {"bundle_md5": "malformed"}, {"chunks": []}])
def test_bundle_drift_missing_pins_are_unknown_not_zero(tmp_path, inputs):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    result = bundle_drift({"inputs": inputs}, tmp_path,
                          recover=lambda *a, **k: pytest.fail("unbound historical lookup"))
    assert result["disk_status"] == result["manifest_status"] == "unknown"


def test_bundle_drift_does_not_cache_current_disk_identity(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, _, _ = _bundle_record(tmp_path)
    assert bundle_drift(record, tmp_path)["disk_status"] == "match"
    (tmp_path / "AI_READI.txt").write_bytes(b"changed")
    assert bundle_drift(record, tmp_path)["disk_status"] == "drift"
    (tmp_path / "AI_READI.txt").unlink()
    assert bundle_drift(record, tmp_path)["disk_status"] == "unknown"


def test_bundle_drift_rejects_manifest_for_another_bundle(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    record, manifest, raw = _bundle_record(tmp_path)
    raw = raw.replace(b"AI_READI.txt", b"OTHER.txt")
    manifest.write_bytes(raw)
    record["inputs"]["chunks"]["sha256"] = hashlib.sha256(raw).hexdigest()
    assert bundle_drift(record, tmp_path)["manifest_status"] == "unknown"


def test_bundle_drift_does_not_read_paths_outside_selected_checkout(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    root = tmp_path / "checkout"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_bytes(b"must not read")
    alias = root / "alias"
    alias.symlink_to(outside)
    for path in ("../private.txt", str(outside), "alias"):
        result = bundle_drift({"inputs": {"bundle_path": path, "bundle_md5": "a" * 32}}, root)
        assert result["disk_md5"] is None
        assert result["disk_status"] == "unknown"


def test_bundle_drift_rejects_external_manifest_link_back_into_checkout(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    root = tmp_path / "checkout"
    root.mkdir()
    target = root / "manifest.yaml"
    target.write_text("bundle: example.txt\n")
    external = tmp_path / "outside-link.yaml"
    external.symlink_to(target)
    result = bundle_drift({"inputs": {"chunks": {
        "path": str(external), "sha256": "a" * 64}}}, root,
        recover=lambda *a, **k: pytest.fail("external lexical name reached Git lookup"))
    assert result["manifest_status"] == "unknown"


def test_bundle_drift_report_retains_denominators_unknowns_and_record_labels(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import compare_bundle_drift, render_bundle_drift

    record, _, _ = _bundle_record(tmp_path, current=b"new")
    record["run"]["label"] = "rep1|unexpected\nheader"
    result = compare_bundle_drift({"v6": [record, {}], "v10": []}, tmp_path)
    text = "\n".join(render_bundle_drift(result))
    assert "| v6 | 2 | 0 / 1 / 1 | 1 / 0 / 1 |" in text
    assert "| v10 | 0 | 0 / 0 / 0 | 0 / 0 / 0 |" in text
    assert "supply no comparison evidence" in text
    assert "rep1\\|unexpected header" in text
    assert hashlib.md5(b"original").hexdigest() in text
    assert "Unknown evidence is not a match" in text


def test_bundle_drift_cli_reads_explicit_cohort_without_writing(tmp_path, capsys):
    import json
    import yaml
    from data_sheets_schema.evaluation.arm_comparison import main

    record, _, _ = _bundle_record(tmp_path, current=b"new")
    source = tmp_path / "record.yaml"
    source.write_text(yaml.safe_dump(record))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert main(["--root", str(tmp_path), "--arm", "v6=record.yaml", "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert set(result) == {"v6"}
    assert result["v6"]["disk"]["drift"] == 1
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "--arm", "v6=record.yaml", "--arm", "v6=record.yaml"])


def test_cross_arm_recorded_identity_is_independent_of_current_disk_drift(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import compare_bundle_drift, render_bundle_drift

    record, _, _ = _bundle_record(tmp_path, current=b"new")
    result = compare_bundle_drift({"v8": [record], "v10": [record, record]}, tmp_path)
    digest = record["inputs"]["bundle_md5"]
    for arm, count in (("v8", 1), ("v10", 2)):
        cell = result[arm]["recorded_bundles_by_project"]["AI_READI"]
        assert cell == {"record_count": count, "md5_counts": {digest: count},
                        "missing_count": 0, "malformed_count": 0,
                        "cross_arm_status": "unique_shared_recorded_identity"}
        assert result[arm]["disk"] == {"match": 0, "drift": count, "unknown": 0}
        assert result[arm]["manifest"] == {"match": count, "drift": 0, "unknown": 0}
    text = "\n".join(render_bundle_drift(result))
    assert f"{digest} × 2" in text and "unique shared recorded identity" in text
    assert "not proof that historical bytes were recovered" in text
    assert "Different source inputs can confound" in text


def test_cross_arm_different_recorded_bundles_can_each_match_their_manifest(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import compare_bundle_drift

    records = []
    for directory, value in (("old", b"old input"), ("new", b"new input")):
        root = tmp_path / directory
        root.mkdir()
        record, _, _ = _bundle_record(root, old=value)
        record["inputs"]["bundle_path"] = directory + "/" + record["inputs"]["bundle_path"]
        record["inputs"]["chunks"]["path"] = directory + "/" + record["inputs"]["chunks"]["path"]
        records.append(record)
    result = compare_bundle_drift({"v8": [records[0]], "v10": [records[1]]}, tmp_path)
    for block in result.values():
        assert block["manifest"] == {"match": 1, "drift": 0, "unknown": 0}
        assert block["recorded_bundles_by_project"]["AI_READI"]["cross_arm_status"] == "different_recorded_identities"


@pytest.mark.parametrize("case,status", [
    ("mixed", "heterogeneous_evidence"), ("missing", "insufficient_evidence"),
    ("malformed", "insufficient_evidence"), ("empty", "insufficient_evidence"),
    ("one_arm", "insufficient_evidence"),
])
def test_cross_arm_identity_never_chooses_a_representative_or_fills_unknowns(tmp_path, case, status):
    from copy import deepcopy
    from data_sheets_schema.evaluation.arm_comparison import compare_bundle_drift

    record, _, _ = _bundle_record(tmp_path)
    second = deepcopy(record)
    second["run"]["label"] = "rep2"
    if case == "mixed":
        second["inputs"]["bundle_md5"] = "a" * 32
    elif case == "missing":
        second["inputs"].pop("bundle_md5")
    elif case == "malformed":
        second["inputs"]["bundle_md5"] = "bad pin"
    arms = {"v8": [record, second], "v10": [] if case == "empty" else [record]}
    if case == "one_arm":
        arms.pop("v10")
    result = compare_bundle_drift(arms, tmp_path)
    cell = result["v8"]["recorded_bundles_by_project"]["AI_READI"]
    assert cell["cross_arm_status"] == status
    assert sum(cell["md5_counts"].values()) + cell["missing_count"] + cell["malformed_count"] == cell["record_count"] == 2
    assert cell["missing_count"] == int(case == "missing")
    assert cell["malformed_count"] == int(case == "malformed")
    if case == "mixed":
        assert cell["md5_counts"] == dict(sorted({record["inputs"]["bundle_md5"]: 1, "a" * 32: 1}.items()))
    if case == "empty":
        assert result["v10"]["recorded_bundles_by_project"]["AI_READI"] == {
            "record_count": 0, "md5_counts": {}, "missing_count": 0, "malformed_count": 0,
            "cross_arm_status": status}


def test_cross_arm_summaries_and_table_are_invariant_to_input_order(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import compare_bundle_drift, recorded_bundle_identity, render_bundle_drift

    first, _, _ = _bundle_record(tmp_path, "CHORUS")
    second, _, _ = _bundle_record(tmp_path, "VOICE")
    a = compare_bundle_drift({"v8": [first, second], "v10": [second, first]}, tmp_path)
    b = compare_bundle_drift({"v10": [first, second], "v8": [second, first]}, tmp_path)
    assert recorded_bundle_identity(a) == recorded_bundle_identity(b)
    assert list(recorded_bundle_identity(a)) == ["CHORUS", "VOICE"]
    assert "\n".join(render_bundle_drift(a)).split("Each record is compared separately")[0] == "\n".join(render_bundle_drift(b)).split("Each record is compared separately")[0]
    for arm in a:
        assert a[arm]["recorded_bundles_by_project"] == b[arm]["recorded_bundles_by_project"]


def test_cross_arm_absolute_paths_are_bounded_and_unsupported_relocation_stays_unknown(tmp_path, monkeypatch):
    from copy import deepcopy
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift

    root = tmp_path / "checkout"
    root.mkdir()
    record, manifest, _ = _bundle_record(root)
    record["inputs"]["bundle_path"] = str(root / "AI_READI.txt")
    record["inputs"]["chunks"]["path"] = str(manifest)
    assert bundle_drift(record, root)["manifest_status"] == "match"
    assert bundle_drift(record, root)["disk_status"] == "match"
    local = root / "data" / "preprocessed" / "AI_READI.txt"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"original")
    read_bytes = Path.read_bytes
    def bounded_read(path):
        assert path.is_relative_to(root), "external live input read"
        return read_bytes(path)
    monkeypatch.setattr(Path, "read_bytes", bounded_read)
    # A matching suffix (including ambiguous repeated suffixes) is not an owner.
    for outside in (tmp_path / "elsewhere" / "data" / "preprocessed" / local.name,
                    tmp_path / "data" / "preprocessed" / "old" / "data" / "preprocessed" / local.name):
        moved = deepcopy(record)
        moved["inputs"]["bundle_path"] = str(outside)
        result = bundle_drift(moved, root)
        assert result["disk_status"] == result["manifest_status"] == "unknown"
        assert result["disk_md5"] is None
        assert "external absolute-path relocation is unsupported" in result["disk_reason"]


def test_cross_arm_cli_json_and_markdown_expose_same_pins(tmp_path, capsys):
    import json
    import yaml
    from data_sheets_schema.evaluation.arm_comparison import main

    record, _, _ = _bundle_record(tmp_path)
    (tmp_path / "record.yaml").write_text(yaml.safe_dump(record))
    args = ["--root", str(tmp_path), "--arm", "v8=record.yaml", "--arm", "v10=record.yaml"]
    assert main(args + ["--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["v8"]["recorded_bundles_by_project"]["AI_READI"]["cross_arm_status"] == "unique_shared_recorded_identity"
    assert main(args + ["--format", "markdown"]) == 0
    text = capsys.readouterr().out
    assert f"{record['inputs']['bundle_md5']} × 1" in text
    assert "| project | v10 | v8 | cross-arm recorded identity |" in text


class Rate(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_a_zero_numerator_over_a_real_denominator_is_a_rate_not_a_dash(self):
        self.assertEqual(self.m._rate(0, 3400), "0/3400 = 0.0%")

    def test_nothing_measured_and_nothing_to_divide_are_both_a_dash(self):
        for num, den in ((None, 10), (5, 0), (5, None), (None, None)):
            with self.subTest(num=num, den=den):
                self.assertEqual(self.m._rate(num, den), "–")


class Pooled(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def _rec(self, **kw):
        base = dict(receiptable=100, withreceipt=50, neverreceipted=40, addedafter=10,
                    snippets=200, wrongchunk=4, unverified=0, unreviewed=0)
        base.update(kw)
        return base

    def test_a_key_no_record_carries_is_none_and_never_zero(self):
        """The agentic path writes no phase-1 snapshot, so its records carry no
        split. A 0 there would assert that reconciliation added nothing after
        the receipt, which is not what an absent snapshot says."""
        reps = [self._rec(neverreceipted=None, addedafter=None) for _ in range(3)]
        t = self.m.pooled_receipts(reps)
        self.assertIsNone(t["neverreceipted"])
        self.assertIsNone(t["addedafter"])
        self.assertEqual(t["receiptable"], 300)
        self.assertEqual(t["records"], 3)
        self.assertEqual(t["split_records"], 0)

    def test_the_split_is_divided_by_the_records_that_carry_it(self):
        """Not by every checked record: `receiptable` is carried by all of them
        and the split only by those with a snapshot, so pooling the two
        independently would divide a numerator from one set of records by a
        denominator from another."""
        reps = [self._rec(), self._rec(neverreceipted=None, addedafter=None)]
        t = self.m.pooled_receipts(reps)
        self.assertEqual(t["receiptable"], 200)          # both records
        self.assertEqual(t["split_receiptable"], 100)    # only the one with a split
        self.assertEqual(t["neverreceipted"], 40)
        self.assertEqual(t["split_records"], 1)
        self.assertEqual(self.m._rate(t["neverreceipted"], t["split_receiptable"]), "40/100 = 40.0%")
        # the wrong denominator would have halved it
        self.assertEqual(self.m._rate(t["neverreceipted"], t["receiptable"]), "40/200 = 20.0%")

    def test_records_counts_only_the_records_that_were_measured(self):
        reps = [self._rec(), self._rec(receiptable=None)]
        self.assertEqual(self.m.pooled_receipts(reps)["records"], 1)


class Metrics(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_an_unchecked_receipt_measures_nothing(self):
        for block in ({}, {"checked": False}, {"checked": None}):
            with self.subTest(block=block):
                self.assertEqual(set(self.m.receipt_metrics(block).values()), {None})

    def test_without_a_receipt_is_the_difference_not_the_capped_list(self):
        """The stored list is capped at 50 entries with the remainder in a
        counter beside it; #831's body divided by the capped list and reported
        coverage at twice its level."""
        block = {"checked": True, "snippets": {"total": 10},
                 "chunks": {"total": 4, "reviewed": 4},
                 "slots": {"receiptable": 300, "with_receipt": 100,
                           "without_receipt": [f"a[{i}]" for i in range(50)],
                           "without_receipt_truncated": 150}}
        self.assertEqual(self.m.receipt_metrics(block)["noreceipt"], 200)

    def test_a_block_predating_the_counters_falls_back_to_the_list(self):
        block = {"checked": True, "snippets": {"total": 10},
                 "chunks": {"total": 4, "reviewed": 4},
                 "slots": {"without_receipt": ["a", "b"], "without_receipt_truncated": 7}}
        out = self.m.receipt_metrics(block)
        self.assertEqual(out["noreceipt"], 9)
        self.assertIsNone(out["receiptable"])

    def test_the_split_passes_through_as_none_where_the_block_has_none(self):
        block = {"checked": True, "snippets": {"total": 10},
                 "chunks": {"total": 4, "reviewed": 4},
                 "slots": {"receiptable": 10, "with_receipt": 4,
                           "never_receipted": None, "added_after_receipt": None}}
        out = self.m.receipt_metrics(block)
        self.assertIsNone(out["neverreceipted"])
        self.assertIsNone(out["addedafter"])
        self.assertEqual(out["noreceipt"], 6)

    def test_wrongchunk_sums_the_three_attribution_kinds(self):
        block = {"checked": True, "chunks": {"total": 1, "reviewed": 1},
                 "snippets": {"total": 100, "adjacent": 3, "elsewhere": 2, "spans_boundary": 1},
                 "slots": {"receiptable": 10, "with_receipt": 10}}
        out = self.m.receipt_metrics(block)
        self.assertEqual((out["wrongchunk"], out["snippets"]), (6, 100))


class Section(unittest.TestCase):
    """The rendered rows, not only the arithmetic behind them: the denominator
    switch and the "(of N records)" suffix live in `receipt_section`, and a
    row is what a reader acts on (#1198 round 2)."""

    def setUp(self):
        self.m = _module()

    def _rec(self, **kw):
        base = dict(receiptable=100, withreceipt=50, neverreceipted=40, addedafter=10,
                    snippets=200, wrongchunk=4, unverified=0, unreviewed=0)
        base.update(kw)
        return base

    def _row(self, reps):
        data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
        first_arm, first_project = self.m.ARMS[0][0], self.m.PROJECTS[0]
        data[first_arm][first_project] = reps
        lines = self.m.receipt_section(data)
        body = [l for l in lines if l.startswith("| ") and not l.startswith("| arm")]
        return body[0] if body else ""

    def test_a_whole_arm_with_the_split_names_no_record_count(self):
        row = self._row([self._rec(), self._rec()])
        self.assertIn("80/200 = 40.0%", row)          # never, over both records
        self.assertNotIn("of 2 records", row)

    def test_an_arm_that_mixes_snapshot_and_no_snapshot_says_how_many_the_split_covers(self):
        row = self._row([self._rec(), self._rec(neverreceipted=None, addedafter=None)])
        self.assertIn("40/100 = 40.0%", row)           # the split's own denominator
        self.assertIn("(of 1 records)", row)
        self.assertIn("100/200 = 50.0%", row)          # coverage still over both

    def test_an_arm_with_no_split_at_all_shows_a_dash_and_no_suffix(self):
        row = self._row([self._rec(neverreceipted=None, addedafter=None) for _ in range(2)])
        self.assertRegex(row, r"\|\s+–\s+\|\s+–\s+\|")
        self.assertNotIn("of 0 records", row)

    def test_an_arm_with_no_measured_record_is_left_out_entirely(self):
        self.assertEqual(self._row([]), "")


def test_report_cells_keep_unmeasured_zeros_out_of_the_mean():
    m = _module()
    reps = [{"report": 0, "claims_checked": 0},
            {"report": 0, "claims_checked": 4},
            {"report": 2, "claims_checked": 0}]
    assert m.cell(reps, "report", "reps") == "1.0 ± 1.4 [0ᵘ,0,2] (n=2)"
    assert m.cell(reps[:1], "report", "reps") == "– [0ᵘ]"
    assert m.cell([{"report": None}], "report", "reps") == "– [–]"


def test_check_detects_report_changes_without_overwriting_any_output(tmp_path, monkeypatch, capsys):
    m = _module()
    data = {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}
    data["v8prod"]["CHORUS"] = [{"report": 0, "claims_checked": 5}]
    m.OUT_MD = tmp_path / "comparison.md"
    original = m.render_markdown(data, {})
    assert "## Bundle identity by arm" in original
    m.OUT_MD.write_text(original)
    monkeypatch.setattr(m, "collect", lambda: data)
    monkeypatch.setattr(m, "EVAL_DIRS", {})
    monkeypatch.setattr(m, "write_figures", lambda *args: pytest.fail("check must not write figures"))
    monkeypatch.setattr(m, "write_markdown", lambda *args: pytest.fail("check must not overwrite Markdown"))
    monkeypatch.setattr("sys.argv", ["arm_comparison.py", "--check"])
    assert m.main() == 0
    data["v8prod"]["CHORUS"][0]["report"] = 2
    assert m.main() == 1
    message = capsys.readouterr().err
    assert "GitUnavailable" in message and "--no-figures" in message
    assert m.OUT_MD.read_text() == original
    m.OUT_MD.unlink()
    assert m.main() == 1
    assert not m.OUT_MD.exists()


def test_report_bundle_drift_uses_selected_cohort_in_stable_order(tmp_path, monkeypatch):
    m = _module()
    monkeypatch.setattr(m, "ROOT", tmp_path)
    data = {key: {project: [] for project in m.PROJECTS} for key, *_ in m.ARMS}
    for project in reversed(m.PROJECTS):
        record, _, _ = _bundle_record(
            tmp_path, project, current=None if project == "CHORUS" else b"changed")
        data["v6agentic"][project] = [{"label": "rep1", "rec": record}]
    result = m.bundle_drift_by_arm(data)
    rows = result["v6agentic"]["records"]
    assert [row["project"] for row in rows] == sorted(m.PROJECTS)
    assert {row["project"]: row["disk_status"] for row in rows} == {
        "AI_READI": "drift", "CHORUS": "match", "CM4AI": "drift", "VOICE": "drift"}
    assert result["v6agentic"]["disk"] == {"match": 1, "drift": 3, "unknown": 0}
    assert all(row["manifest_status"] == "match" for row in rows)
    assert result["v8prod"]["count"] == 0


def test_bundle_drift_survives_real_metrics_collection(tmp_path, monkeypatch):
    import yaml

    m = _module()
    record, _, _ = _bundle_record(tmp_path, "CHORUS", current=b"revised")
    record["run"]["label"] = "fixture_rep1"
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CONCAT", tmp_path / "records")
    monkeypatch.setattr(m, "ARMS", (("fixture", "fixture", "fixture", "offline", "reps"),))
    monkeypatch.setattr(m, "PROJECTS", ("CHORUS",))
    monkeypatch.setattr(m, "_method_for", lambda *args: "fixture_method")
    monkeypatch.setattr(m, "form_facts", lambda *args, **kwargs: {})
    monkeypatch.setattr(m, "removal_metrics", lambda *args, **kwargs: {})
    for method, name, content in (
        ("fixture_method", "CHORUS_d4d.yaml", {"id": "ex:dataset"}),
        ("fixture_method_core", "CHORUS_d4d_core.yaml", {"id": "ex:dataset"}),
        ("fixture_method_core", "CHORUS_provenance.yaml", record),
    ):
        path = m.CONCAT / method / "fixture_rep1" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(content))
    result = m.bundle_drift_by_arm(m.collect())["fixture"]
    assert result["disk"] == {"match": 0, "drift": 1, "unknown": 0}
    assert result["manifest"] == {"match": 1, "drift": 0, "unknown": 0}
    assert result["records"][0]["label"] == "fixture_rep1"


def _assert_selected_bundle_invariants(m, data, comparisons):
    """Every selected provenance identity survives; observations may change."""
    assert list(comparisons) == [arm for arm, *_ in m.ARMS]
    states = {"match", "drift", "unknown"}
    for arm, block in comparisons.items():
        selected = sorted(((project, row["label"], row["rec"])
            for project in m.PROJECTS for row in data[arm][project]),
            key=lambda row: (row[0], row[1]))
        expected = [(record["run"]["project"], record["run"]["label"], record.get("inputs", {}).get("bundle_path"))
            for _, _, record in selected]
        rows = block["records"]
        assert block["count"] == len(selected) == len(rows)
        assert [(row["project"], row["label"], row["bundle_path"]) for row in rows] == expected
        for basis in ("disk", "manifest"):
            assert set(block[basis]) == states
            assert sum(block[basis].values()) == len(selected)
            assert all(type(value) is int and value >= 0 for value in block[basis].values())
            for state in states:
                assert block[basis][state] == sum(row[basis + "_status"] == state for row in rows)
            for row in rows:
                assert row[basis + "_status"] in states
                if row["recorded_md5"] is None or row[basis + "_md5"] is None:
                    assert row[basis + "_status"] == "unknown"


def test_bundle_invariants_survive_legitimate_revision_and_replicate_reordering(tmp_path, monkeypatch):
    m = _module()
    monkeypatch.setattr(m, "ROOT", tmp_path)
    data = {arm: {project: [] for project in m.PROJECTS} for arm, *_ in m.ARMS}
    record, _, _ = _bundle_record(tmp_path, "CHORUS")
    for label in ("rep2", "rep1"):
        rec = {**record, "run": {**record["run"], "label": label}}
        data["v6agentic"]["CHORUS"].append({"label": label, "rec": rec})
    unknown = {"run": {"project": "CHORUS", "label": "unknown"}, "inputs": {}}
    data["v8prod"]["CHORUS"].append({"label": "unknown", "rec": unknown})
    before = m.bundle_drift_by_arm(data)
    _assert_selected_bundle_invariants(m, data, before)
    assert [row["label"] for row in before["v6agentic"]["records"]] == ["rep1", "rep2"]
    (tmp_path / "CHORUS.txt").write_bytes(b"legitimate source revision")
    data["v6agentic"]["CHORUS"].reverse()
    after = m.bundle_drift_by_arm(data)
    _assert_selected_bundle_invariants(m, data, after)
    assert before["v6agentic"]["disk"] == {"match": 2, "drift": 0, "unknown": 0}
    assert after["v6agentic"]["disk"] == {"match": 0, "drift": 2, "unknown": 0}
    assert before["v8prod"]["disk"] == after["v8prod"]["disk"] == {"match": 0, "drift": 0, "unknown": 1}


def test_bundle_history_unavailable_remains_unknown(tmp_path):
    from data_sheets_schema.evaluation.arm_comparison import bundle_drift
    from data_sheets_schema.provenance import GitUnavailable
    record, manifest, _ = _bundle_record(tmp_path)
    manifest.write_bytes(b"replaced manifest")
    def unavailable(*args, **kwargs):
        raise GitUnavailable("shallow clone")
    result = bundle_drift(record, tmp_path, recover=unavailable)
    assert result["manifest_status"] == "unknown" and result["manifest_md5"] is None
    assert result["manifest_reason"] == "manifest recovery unavailable: GitUnavailable"


@pytest.mark.corpus
def test_committed_comparison_matches_current_records():
    """Catch stale measurements without fixing current bundle contents in tests."""
    m = _module()
    data = m.collect()
    _assert_selected_bundle_invariants(m, data, m.bundle_drift_by_arm(data))
    scores = {rubric: {key: {p: m.rubric_scores(prefix, p, rubric) for p in m.PROJECTS}
                      for key, _display, prefix, *_ in m.ARMS} for rubric in m.EVAL_DIRS}
    rendered = m.render_markdown(data, scores)
    assert "## Bundle identity by arm" in rendered
    assert m.OUT_MD.read_text(encoding="utf-8") == rendered, (
        "Inspect unavailable evidence (including GitUnavailable or shallow history) first; "
        "restore required history when available. After reviewing input changes, run "
        "scripts/arm_comparison.py --no-figures to refresh the committed Markdown.")


class RemovalRows(unittest.TestCase):
    """The removal rows (#2923): a record the classifier could not measure —
    no phase-1 snapshot, the agentic path's case — is `–`, never 0 (#899)."""

    def setUp(self):
        self.m = _module()

    def _rows(self, block, report_claims):
        from unittest import mock
        with mock.patch("data_sheets_schema.removals.for_record", return_value=block):
            return self.m.removal_metrics(Path("P_provenance.yaml"), {"report_claims": report_claims})

    def test_a_record_with_no_snapshot_is_unmeasured_on_every_removal_row(self):
        from data_sheets_schema.removals import classify
        rows = self._rows(classify(None, {}), {"snapshot_checked": False, "removals_unrecorded_count": None})
        self.assertEqual(rows, {"unfoundedremovals": None, "unfoundedreconcile": None, "unfoundedrelocated": None,
                                "lowconfidenceflat": None, "receipteddeleted": None, "unfoundedrewrites": None,
                                "unfoundedrewritesnotmodel": None, "unrecordedremovals": None})
        self.assertEqual({self.m.fmt(rows, k) for k in rows}, {"–"})
        self.assertEqual(self.m.cell([rows] * 3, "unfoundedremovals", "reps"), "– [–,–,–]")

    def test_a_measured_record_carries_its_counts_and_a_measured_zero_stays_zero(self):
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "data_governance": {"committee_name": "DAC"}, "license": "CC-BY"}
        receipt = {"chunks": [{"id": "c001", "status": "extracted",
                               "extracted": [{"slot": "data_governance.committee_name", "snippet": "the DAC"}]}]}
        block = classify(before, {"id": "doi:10.1/x", "license": "CC-BY"}, {"findings": []}, receipt=receipt)
        rows = self._rows(block, {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual(rows, {"unfoundedremovals": 1, "unfoundedreconcile": None, "unfoundedrelocated": 0,
                                "lowconfidenceflat": 0, "receipteddeleted": 1, "unfoundedrewrites": 0,
                                "unfoundedrewritesnotmodel": 0, "unrecordedremovals": 0})

    def test_an_unrecorded_count_the_block_did_not_measure_is_not_read(self):
        """`removals_unrecorded_count` is only a measurement where the report
        block read a snapshot."""
        from data_sheets_schema.removals import classify
        rows = self._rows(classify(None, {}), {"snapshot_checked": False, "removals_unrecorded_count": 0})
        self.assertIsNone(rows["unrecordedremovals"])

    def test_the_deletion_rows_say_a_reworded_or_moved_value_counts_as_deleted(self):
        """#3207: the text test is the value's own text surviving, so the
        published definitions must not read as true deletions; and #3229:
        coincidental flattening deflates them, so the definitions must not
        call them upper bounds."""
        for key in ("unfoundedremovals", "receipteddeleted"):
            text = self.m.METRICS[key][3]
            self.assertIn("removals v3", text)
            self.assertIn("reworded", text)
            self.assertNotIn("upper bound", text)        # #3229: the counts err both ways
            self.assertIn("#3207", text)
            self.assertIn("#3229", text)
        definition = self.m.METRICS["unfoundedremovals"][3]
        for phrase in ("a resolver URL and the CURIE it names read as one text, #3129",
                       "a British spelling and its American form, #3038",
                       "a value of numbers only survives only as a scalar equal to it, never quoted in prose, "
                       "and never below five digits, #3243, #3130",
                       "counted on its own row below (#3243)"):
            self.assertIn(phrase, definition)

    def test_the_rewrite_row_counts_unfounded_in_place_rewrites_apart_from_removals(self):
        """#3243: a carried scalar whose path now holds other text is on its
        own row, sorted by the same finding paths, never in the removal rows."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "license": "CC-BY", "description": "old words", "title": "t"}
        after = {"id": "doi:10.1/x", "license": "CC0", "description": "new words entirely", "title": "t"}
        rows = self._rows(classify(before, after, {"findings": [{"slot": "license", "issue": "x"}]}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedrewrites"]), (0, 1))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedrewrites"), keys.index("receipteddeleted") + 1)
        self.assertIn("#3243", self.m.METRICS["unfoundedrewrites"][3])

    def test_the_relocation_row_counts_unfounded_removals_with_a_candidate_and_moves_nothing(self):
        """#3223: a reported-only row under the removals, counting those
        whose words recur in one final scalar; the removal count beside it
        is what it was without the row."""
        from data_sheets_schema.removals import classify
        note = "The healthsheet answers N/A to the sampling strategy question for this release."
        before = {"id": "doi:10.1/x", "sampling": {"notes": note, "is_sample": True}, "license": "CC-BY"}
        after = {"id": "doi:10.1/x", "sampling": {"is_sample": True, "source_caveats":
                                                   "For this release's sampling strategy question the healthsheet answers N/A."}}
        rows = self._rows(classify(before, after, {"findings": []}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedrelocated"]), (2, 1))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedrelocated"), keys.index("unfoundedreconcile") + 1)
        definition = self.m.METRICS["unfoundedrelocated"][3]
        for phrase in ("#3223", "Reported only: no count above moves", "removals_relocated_sample_2026-09-29.yaml",
                       "change of standing"):
            self.assertIn(phrase, definition)

    def test_the_low_confidence_row_sizes_the_deflation_and_moves_nothing(self):
        """#3367: flattenings by a one- or two-token needle (or the surplus
        route) that no finding would found, beside the removals; the
        removal count is what it was."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "keywords": ["UF", "voice biomarkers of adults"], "license": "CC-BY"}
        after = {"id": "doi:10.1/x", "keywords": "UF; voice biomarkers of adults"}
        rows = self._rows(classify(before, after, {"findings": []}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedremovals"], rows["lowconfidenceflat"]), (1, 1))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("lowconfidenceflat"), keys.index("unfoundedrelocated") + 1)
        definition = self.m.METRICS["lowconfidenceflat"][3]
        for phrase in ("#3367", "Reported only: no count moves", "bounds nothing (#3229)"):
            self.assertIn(phrase, definition)

    def test_the_not_the_models_row_counts_normaliser_forms_and_amends_within_the_rewrites(self):
        """#3366: a sub-row of the rewrite row; the rewrite row keeps them."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "issued": "2024-05-01", "description": "old words", "title": "t"}
        after = {"id": "doi:10.1/x", "issued": "2024-05-01T00:00:00Z", "description": "new text", "title": "u"}
        rows = self._rows(classify(before, after, {"findings": []}, amended_paths={"title"}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedrewrites"], rows["unfoundedrewritesnotmodel"]), (3, 2))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedrewritesnotmodel"), keys.index("unfoundedrewrites") + 1)
        definition = self.m.METRICS["unfoundedrewritesnotmodel"][3]
        for phrase in ("#3366", "never subtracted", "curator's recorded amend disposition", "#903"):
            self.assertIn(phrase, definition)

    def test_the_low_confidence_and_not_the_models_rows_read_the_unfounded_subsets(self):
        """#3728: a founded low-confidence flattening, and a founded rewrite
        of the normaliser's form or at an amend, are in the block's totals
        and not in the rows, which are without a finding."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "keywords": ["UF", "voice biomarkers of adults"],
                  "data_governance": {"committee_name": "DAC", "notes": "reviewed yearly by the board"},
                  "issued": "2024-05-01", "title": "t", "description": "old words"}
        after = {"id": "doi:10.1/x", "keywords": "UF; voice biomarkers of adults",
                 "data_governance": "DAC reviewed yearly by the board",
                 "issued": "2024-05-01T00:00:00Z", "title": "u", "description": "new text"}
        block = classify(before, after, {"findings": [{"slot": "data_governance", "record": "full"},
                                                     {"slot": "issued", "record": "full"},
                                                     {"slot": "title", "record": "full"}]},
                         amended_paths={"title"})
        self.assertEqual((block["flattened_low_confidence"], block["rewritten"]), (2, 3))
        rows = self._rows(block, {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["lowconfidenceflat"], rows["unfoundedrewrites"], rows["unfoundedrewritesnotmodel"]),
                         (1, 1, 0))

    def test_the_rows_are_in_the_table(self):
        for key in ("unfoundedremovals", "unfoundedreconcile", "unfoundedrelocated", "lowconfidenceflat",
                    "receipteddeleted", "unfoundedrewrites", "unfoundedrewritesnotmodel", "unrecordedremovals"):
            self.assertIn(key, self.m.METRICS)
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedreconcile"), keys.index("unfoundedremovals") + 1)

    def test_the_reconcile_row_counts_only_what_reconcile_full_removed(self):
        """#3150: the all-phase row counts a repair round's removals too; the
        row below it counts reconcile_full's alone, a measured 0 where every
        unfounded value went at repair, and – where no phase is attributed."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "a": "1", "b": "2", "c": "3"}
        stages = [("reconcile_full", {"id": "doi:10.1/x", "b": "2", "c": "3"}),
                  ("repair_full_r1", {"id": "doi:10.1/x"})]
        claims = {"snapshot_checked": True, "removals_unrecorded_count": 0}
        rows = self._rows(classify(before, {"id": "doi:10.1/x"}, {"findings": []}, intermediates=stages), claims)
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedreconcile"]), (3, 1))
        at_repair = [("reconcile_full", before), ("repair_full_r1", {"id": "doi:10.1/x"})]
        rows = self._rows(classify(before, {"id": "doi:10.1/x"}, {"findings": []}, intermediates=at_repair), claims)
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedreconcile"]), (3, 0))
        gap = [("reconcile_full", None), ("repair_full_r1", {"id": "doi:10.1/x"})]
        rows = self._rows(classify(before, {"id": "doi:10.1/x"}, {"findings": []}, intermediates=gap), claims)
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedreconcile"]), (3, None))

    def test_the_all_phase_row_says_it_counts_every_phase(self):
        """#3150: the published definition names the repair rounds it
        counts and why they are split out."""
        definition = self.m.METRICS["unfoundedremovals"][3]
        for phrase in ("Every phase after phase 1 is counted", "repair_full_rN",
                       "acts on validation errors, not on the audit", "the row below isolates reconcile_full"):
            self.assertIn(phrase, definition)
        self.assertIn("reconcile_full removed", self.m.METRICS["unfoundedreconcile"][3])

    def test_the_row_definition_states_the_exclusions_the_classifier_applies(self):
        """#3079: a value only a core-only finding's path covers is counted
        in the row, and the published definition says so rather than 'no
        audit finding's path covers'; the past-end reading (#3077) and the
        dropped-entry rule (#3076) are stated with it."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "data_governance": {"committee_name": "DAC"}}
        block = classify(before, {"id": "doi:10.1/x"},
                         {"findings": [{"record": "core", "slot": "data_governance", "issue": "x"}]})
        rows = self._rows(block, {"snapshot_checked": True, "removals_unrecorded_count": 1})
        self.assertEqual((rows["unfoundedremovals"], block["unfounded_named_by_core_finding"]), (1, 1))
        definition = self.m.METRICS["unfoundedremovals"][3]
        for phrase in ("not scoped to the core record alone", "a value only a core-only finding's path covers "
                       "is counted here", "one past the end of its list read as the last entry",
                       "for an entry dropped from a list"):
            self.assertIn(phrase, definition)
        self.assertNotIn("no finding named the value", definition)


class ReleaseInventory(unittest.TestCase):
    """The release-level corpus inventory (#2914, #3282): a cross-project
    difference on doi, license, version or issued is labelled corpus-driven
    where the corpus holds no release evidence, and each arm's pinned
    manifest is inventoried rather than assumed to be today's."""

    def setUp(self):
        self.m = _module()
        self.empty = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}

    def _doc(self, e11, e102=None):
        sub = lambda name, score: ({"name": name, "score": score} if score is not None
                                   else {"name": name, "score": None, "applicable": False})
        return {"elements": [
            {"id": 1, "sub_elements": [sub("Persistent Identifier (DOI, RRID, or URI)", e11)]},
            {"id": 3, "sub_elements": [sub("License Terms Allow Reuse", 0)]},
            {"id": 6, "sub_elements": [sub("Renamed element", 1)]},
            {"id": 10, "sub_elements": [sub("Dataset Published on a Recognized Platform", 1),
                                        sub("Citation and DOI for Cross-referencing", e102)]}]}

    def test_the_corpus_limited_project_is_named_with_its_inventory(self):
        text = "\n".join(self.m.release_inventory_section(self.empty, {}))
        self.assertIn("| CHORUS | 0 (0 current) | none | none | none | none | no | `exclude` |", text)
        # #5042: no document corpus carries an RO-Crate any more; AI_READI keeps
        # its licence, IRB source and FAIRhub release records.
        self.assertIn("| AI_READI | 3 (2 current) | `dataset_license` | none | `irb_protocol` | "
                      "`fairhub_dataset` (superseded), `fairhub_dataset_v3`, "
                      "`fairhub_dataset_v3_api` | no | `allow` (no URL exclusion; the crate is not a "
                      "listed source) |", text)   # never a bare `allow` beside "no" (#5060 F4)
        self.assertNotIn("carries its RO-Crate", text)
        self.assertIn("CHORUS's corpus has 0 tier-1 sources, no release record, no license/DUA/IRB "
                      "source, and the crate manifest declares its crate `document_corpus: exclude`", text)
        self.assertIn("`doi`, `license`, `version` and `issued` are **corpus-driven** for CHORUS, "
                      "not a measure of generation quality", text)

    def test_release_subelements_are_counted_per_project_and_evaluator_with_na_apart(self):
        scores = {"rubric10": {"v7prod": {"CHORUS": [
            {"file": "a.json", "evaluator": "ev", "doc": self._doc(0)},
            {"file": "b.json", "evaluator": "ev", "doc": self._doc(1, 0)},
            {"file": "b.json", "evaluator": "ev", "doc": self._doc(1, 0)},     # the same file once
            {"file": "c.json", "evaluator": "other", "doc": self._doc(1, 1)}]}}}
        rows = self.m._release_subelement_rows(scores)
        # E6.1 is renamed in these docs, so it is read as absent, never as a score.
        self.assertEqual(rows, ["| CHORUS | `ev` | 1/2 | 0/2 | – | 0/1, 1 N/A |",
                                "| CHORUS | `other` | 1/1 | 0/1 | – | 1/1 |"])

    def test_a_pinned_manifest_whose_corpus_differs_from_todays_is_named(self):
        import tempfile
        from unittest import mock
        today = (self.m.ROOT / self.m.SOURCE_MANIFEST).read_bytes()
        crate = (self.m.ROOT / self.m.CRATE_MANIFEST).read_bytes()
        then = today.replace(b"source_type: license", b"source_type: documentation", 1)   # AI_READI's
        with tempfile.TemporaryDirectory() as tmp:
            concat = Path(tmp)
            data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
            for p, md5 in (("AI_READI", "a" * 32), ("CHORUS", "a" * 32), ("VOICE", "b" * 32)):
                d = concat / "claudecode_api_core" / "L_rep1"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{p}_provenance.yaml").write_text(
                    f"inputs:\n  source_manifest:\n    path: {self.m.SOURCE_MANIFEST}\n    md5: {md5}\n")
                data["v8prod"][p] = [{"label": "L_rep1"}]
            versions = {"a" * 32: (then, {"commit": "c" * 40, "date": "2026-09-01"})}
            with mock.patch.object(self.m, "CONCAT", concat), \
                    mock.patch.object(self.m, "_method_for", lambda label, project: "claudecode_api"), \
                    mock.patch("data_sheets_schema.provenance.committed_bytes_for",
                               lambda path, md5=None, sha256=None: versions.get(md5)):
                rows = self.m._pinned_manifest_rows(data, today, crate)
        self.assertEqual(rows, [
            "| v8 API production (2026-09-04f/g) | `aaaaaaaaaaaa` (2 records), committed 2026-09-01 "
            "(`cccccccccc`) | differs: AI_READI | as today | |",
            "| v8 API production (2026-09-04f/g) | `bbbbbbbbbbbb` (1 records) | – | – | "
            "no committed version of `data/preprocessed/source_manifest.yaml` hashes to it |"])

    def test_records_that_read_a_crate_today_s_corpus_dropped_are_noted(self):
        """#5060 F3: a pinned manifest that listed AI_READI's RO-Crate says in the
        note column that those records read it, since #5042 removed it."""
        import subprocess
        import tempfile
        from unittest import mock
        try:
            then = subprocess.run(["git", "show", f"1c4debbae^:{self.m.SOURCE_MANIFEST}"], cwd=self.m.ROOT,
                                  capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"the pre-#5042 manifest needs git history: {exc}")
        today = (self.m.ROOT / self.m.SOURCE_MANIFEST).read_bytes()
        crate = (self.m.ROOT / self.m.CRATE_MANIFEST).read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            concat = Path(tmp)
            data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
            d = concat / "claudecode_api_core" / "L_rep1"
            d.mkdir(parents=True)
            for p in ("AI_READI", "CHORUS"):
                (d / f"{p}_provenance.yaml").write_text(
                    f"inputs:\n  source_manifest:\n    path: {self.m.SOURCE_MANIFEST}\n    md5: {'a' * 32}\n")
                data["v8prod"][p] = [{"label": "L_rep1"}]
            with mock.patch.object(self.m, "CONCAT", concat), \
                    mock.patch.object(self.m, "_method_for", lambda label, project: "claudecode_api"), \
                    mock.patch("data_sheets_schema.provenance.committed_bytes_for",
                               lambda path, md5=None, sha256=None: (then, {"commit": "c" * 40, "date": "2026-10-13"})):
                rows = self.m._pinned_manifest_rows(data, today, crate)
        self.assertEqual(len(rows), 1)
        self.assertIn("| differs: AI_READI |", rows[0])
        self.assertTrue(rows[0].endswith("| these records read AI_READI's RO-Crate, which today's corpus no "
                                         "longer carries (#5042) |"), rows[0])

    def test_a_record_pinning_no_manifest_or_no_hash_says_so_and_git_is_not_asked(self):
        """#3903: `path: null` (a run that selected no manifest, #621) and a
        path with no hash are named as such, never as a git miss on `None`."""
        import tempfile
        from unittest import mock
        today = (self.m.ROOT / self.m.SOURCE_MANIFEST).read_bytes()
        crate = (self.m.ROOT / self.m.CRATE_MANIFEST).read_bytes()
        blocks = {"AI_READI": "path: null\n",
                  "CHORUS": f"path: {self.m.SOURCE_MANIFEST}\n",
                  "VOICE": "path: null\n    md5: " + "d" * 32 + "\n"}
        asked = []
        with tempfile.TemporaryDirectory() as tmp:
            concat = Path(tmp)
            data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
            d = concat / "claudecode_api_core" / "L_rep1"
            d.mkdir(parents=True)
            for p, block in blocks.items():
                (d / f"{p}_provenance.yaml").write_text("inputs:\n  source_manifest:\n    " + block)
                data["v8prod"][p] = [{"label": "L_rep1"}]
            with mock.patch.object(self.m, "CONCAT", concat), \
                    mock.patch.object(self.m, "_method_for", lambda label, project: "claudecode_api"), \
                    mock.patch("data_sheets_schema.provenance.committed_bytes_for",
                               lambda *a, **k: asked.append(a) or None):
                rows = self.m._pinned_manifest_rows(data, today, crate)
        self.assertEqual(asked, [])
        arm = "| v8 API production (2026-09-04f/g) |"
        self.assertEqual(sorted(rows), sorted([
            f"{arm} no hash recorded (1 records) | – | – | the records pinned no source manifest |",
            f"{arm} no hash recorded (1 records) | – | – | the records name "
            "`data/preprocessed/source_manifest.yaml` but pinned no hash of it, "
            "so no version can be recovered |",
            f"{arm} `dddddddddddd` (1 records) | – | – | "
            "the records pinned a hash but no source-manifest path |"]))
        self.assertFalse(any("`None`" in r for r in rows))


# Live form metrics carry the run's schema and disclose fallbacks (#4216).
@pytest.fixture
def form_run(tmp_path, monkeypatch):
    import hashlib
    import yaml

    m = _module()
    m.CONCAT = tmp_path / "concatenated"
    label, project = "test_run_rep1", "P"
    monkeypatch.setattr(m, "_method_for", lambda *_args: "claudecode_agent")
    monkeypatch.setattr(m, "removal_metrics", lambda *_args, include_basis=False: {})
    full = m.CONCAT / "claudecode_agent" / label / f"{project}_d4d.yaml"
    core = m.CONCAT / "claudecode_agent_core" / label / f"{project}_d4d_core.yaml"
    prov = core.parent / f"{project}_provenance.yaml"
    full.parent.mkdir(parents=True)
    core.parent.mkdir(parents=True)
    full.write_text(yaml.safe_dump({"id": "foo:1", "publisher": "doi:10.1/a",
                                   "description": "research centre",
                                   "variables": [{"unit": "ROR:032db5x82#bench"}]}))
    core.write_text(yaml.safe_dump({"id": "doi:10.1/core"}))
    schema = {"id": "https://example.org/run", "name": "run", "default_range": "string",
              "prefixes": {"foo": "https://foo.example.org/", "linkml": "https://w3id.org/linkml/"},
              "types": {"string": {"uri": "xsd:string", "base": "str"},
                        "uriorcurie": {"uri": "xsd:anyURI", "base": "URIorCURIE"}},
              "classes": {"Dataset": {"attributes": {
                  "id": {"range": "uriorcurie", "identifier": True},
                  "publisher": {"range": "uriorcurie"},
                  "variables": {"range": "VariableMetadata", "multivalued": True}}},
                  "VariableMetadata": {"attributes": {"unit": {"range": "uriorcurie"}}}}}
    schema_path = tmp_path / "run_all.yaml"
    schema_path.write_text(yaml.safe_dump(schema))
    record = {"schema": {"full_path": str(schema_path),
                         "full_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest()},
              "validation": {"passed": True}, "grounding": {"distinct": {"absent": 7}},
              "pair_consistency": {"errors": 3}, "report_claims": {"findings": [{}]},
              "form": {"undeclared_prefix_occurrences": 999}}
    prov.write_text(yaml.safe_dump(record))
    return m, label, project, full, core, prov, record


def test_live_form_uses_run_schema_for_prefixes_and_identifier_walk(form_run):
    m, label, project, full, core, prov, record = form_run
    before = {path: path.read_bytes() for path in (full, core, prov)}
    today = m.form_facts(full, core)
    row = m.run_metrics(label, project)
    assert today["undeclared_prefix_occurrences"] == 1
    assert today["organisational_fragments"] == 0
    assert row["undeclared"] == 3 and row["orgfrag"] == 1
    assert row["british"] == today["british_spellings"]
    assert row["gc"] == today["gc_label_variant_occurrences"]
    assert (row["ungrounded"], row["pair"], row["report"]) == (7, 3, 1)
    assert row["form_schema_basis"] == {"source": "the run's schema, on disk",
                                         "path": record["schema"]["full_path"],
                                         "sha256": record["schema"]["full_sha256"]}
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("unavailable", [False, True])
def test_schema_fallback_uses_todays_values_and_exposes_why(form_run, monkeypatch, unavailable):
    import yaml
    m, label, project, full, core, prov, record = form_run
    if unavailable:
        record["schema"]["full_sha256"] = "a" * 64
        monkeypatch.setattr("data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for",
                            lambda *_args, **_kwargs: None)
        def no_git(*_args, **_kwargs):
            raise FileNotFoundError("git unavailable")
        monkeypatch.setattr("data_sheets_schema.provenance.committed_bytes_for", no_git)
    else:
        record.pop("schema")
    prov.write_text(yaml.safe_dump(record))
    row = m.run_metrics(label, project)
    assert row["undeclared"] == 1 and row["orgfrag"] == 0
    assert row["form_schema_basis"]["source"] == "today's schema"
    expected = "git could not be run" if unavailable else "the record names no merged schema"
    assert expected in row["form_schema_basis"]["reason"]
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    data[m.ARMS[0][0]][m.PROJECTS[0]] = [row]
    rendered = "\n".join(m.form_schema_section(data))
    assert "today's schema" in rendered and expected in rendered
    assert label in rendered
    assert "do not attest that the requested historical bytes were used" in rendered
    assert "naming declaration, not the run's schema" in rendered
    assert "Current prefix instrument:" in rendered and "Current British-spelling instrument:" in rendered


def test_missing_or_invalid_runs_do_not_acquire_live_form_measurements(form_run, monkeypatch):
    import yaml
    m, label, project, _full, core, prov, record = form_run
    def unexpected(*_args, **_kwargs):
        pytest.fail("excluded records must not be measured")
    monkeypatch.setattr(m, "form_facts", unexpected)
    record["validation"]["passed"] = False
    prov.write_text(yaml.safe_dump(record))
    assert m.run_metrics(label, project) is None
    assert (label, project) in m.EXCLUDED_INVALID
    core.unlink()
    assert m.run_metrics(label, project) is None


def test_form_schema_section_escapes_recorded_basis_and_distinguishes_absence():
    m = _module()
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    data[m.ARMS[0][0]][m.PROJECTS[0]] = [
        {"label": "run|extra\nrow", "form_schema_basis": {"source": "today's schema",
         "reason": "bad | pin <schema> `name`"}}, {"label": "legacy"}]
    rendered = "\n".join(m.form_schema_section(data))
    assert "run&#124;extra<br>row" in rendered
    assert "bad &#124; pin &lt;schema&gt; &#96;name&#96;" in rendered
    assert "legacy | unrecorded — no schema basis supplied" in rendered


def test_live_reference_worst_is_distinguished_from_stored_canary_thresholds(tmp_path):
    m = _module()
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    # The historical v4 live recompute moves 0/6/0 to 116/56/51 (#4216).
    m.CONCAT = tmp_path
    data["v4"]["AI_READI"] = [{"undeclared": n, "label": f"fixture_rep{i}"}
                               for i, n in enumerate((116, 56, 51), 1)]
    for row in data["v4"]["AI_READI"]:
        full = tmp_path / "claudecode_agent" / row["label"] / "AI_READI_d4d.yaml"
        core = tmp_path / "claudecode_agent_core" / row["label"] / "AI_READI_d4d_core.yaml"
        full.parent.mkdir(parents=True)
        core.parent.mkdir(parents=True)
        full.write_text("id: ex:fixture\n")
        core.write_text("id: ex:fixture\n")
        (core.parent / "AI_READI_provenance.yaml").write_text("{}\n")
    text = m.render_markdown(data, {})
    assert "74.3 ± 36.2 [116,56,51] worst 116" in text
    assert "worst on this report's measurement basis" in text
    assert "Canary gates read stored form blocks" in text
    assert "this live recompute does not change their thresholds" in text
    assert "the value the canary gate holds runs against" not in text
    assert "the canary-gate baseline)" not in text


def test_arm_comparison_resolves_historical_worktree_preprocessed_paths(tmp_path: Path) -> None:
    """Historical provenance records with worktree-prefixed paths resolve under active root (#5115 N6)."""
    import yaml
    from data_sheets_schema.evaluation import arm_comparison

    bundle_rel = Path("data/preprocessed/individual/AI_READI/AI_READI_preprocessed.txt")
    chunks_rel = Path("data/preprocessed/individual/AI_READI/AI_READI_preprocessed.chunks.yaml")
    manifest_rel = Path("data/preprocessed/source_manifest.yaml")

    bundle_file = tmp_path / bundle_rel
    chunks_file = tmp_path / chunks_rel
    manifest_file = tmp_path / manifest_rel
    bundle_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)

    bundle_bytes = b"=== FILE: README.md ===\nHello AI_READI\n"
    bundle_file.write_bytes(bundle_bytes)
    bundle_md5 = hashlib.md5(bundle_bytes).hexdigest()

    chunks_doc = {
        "schema_version": "1.0",
        "bundle": bundle_rel.as_posix(),
        "bundle_md5": bundle_md5,
        "chunks": [
            {
                "id": "c001",
                "source_file": "README.md",
                "md5": bundle_md5,
            }
        ],
    }
    chunks_bytes = yaml.safe_dump(chunks_doc).encode("utf-8")
    chunks_file.write_bytes(chunks_bytes)

    manifest_bytes = b"project: AI_READI\nsources: []\n"
    manifest_file.write_bytes(manifest_bytes)

    old_wt = Path("/Users/nonexistent/d4d-executions/launch-base")
    record = {
        "run": {"project": "AI_READI", "label": "claudecode_opus46_generic_r1"},
        "inputs": {
            "bundle_path": str(old_wt / bundle_rel),
            "bundle_md5": bundle_md5,
            "chunks": {
                "path": str(old_wt / chunks_rel),
                "md5": hashlib.md5(chunks_bytes).hexdigest(),
                "sha256": hashlib.sha256(chunks_bytes).hexdigest(),
            },
            "source_manifest": {
                "path": str(old_wt / manifest_rel),
                "md5": hashlib.md5(manifest_bytes).hexdigest(),
            },
        },
    }

    resolved = arm_comparison._path(tmp_path, str(old_wt / bundle_rel))
    assert resolved == bundle_file.resolve()
    assert arm_comparison._path(tmp_path, str(old_wt / "secret/other.txt")) is None

    drift = arm_comparison.bundle_drift(record, tmp_path)
    assert drift["disk_status"] == "match"
    assert drift["manifest_status"] == "match"
    assert drift["manifest_basis"] == "pinned manifest on disk"

    chunks_file.write_bytes(b"modified on disk\n")
    recovered_paths: list[str] = []

    def _fake_recover(rel_path: str, *, md5: str | None = None, sha256: str | None = None):
        recovered_paths.append(rel_path)
        return (chunks_bytes, "deadbeef" * 5)

    drift_recovered = arm_comparison.bundle_drift(record, tmp_path, recover=_fake_recover)
    assert drift_recovered["manifest_status"] == "match"
    assert drift_recovered["manifest_basis"] == "pinned manifest recovered from history"
    assert recovered_paths == [chunks_rel.as_posix()]
