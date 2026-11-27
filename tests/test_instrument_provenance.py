"""Every semantic rubric evaluation resolves to the instrument that scored it.

Why this exists (#1077): an evaluation records `metadata.rubric_hash`, and
until this change the agents' output contract asked for "the sha256 of
rubric10.txt". That file is the rubric *text*. The rules that decide a score
live in the agent definition, and the text did not change across #1059,
#1060 or #1082 — the three revisions that moved scores. So a rubric-text hash
cannot tell two instruments apart, and the 29 rubric10 evaluations that
followed the contract **exactly** are the ones whose instrument their own
artifact cannot name, while the 24 that deviated can be identified. Obeying
the rule was the failure mode.

Nothing is lost, because both files are in git. `scripts/instrument_provenance.py`
resolves every evaluation to an agent version by one of two bases, and the
manifest it writes is what this checks:

- `recorded` — the artifact names its own instrument;
- `recovered_from_commit` — the hash is a rubric-text version, so the agent
  file as it stood in the commit that last wrote this evaluation's bytes is
  named instead. Weaker than a recorded claim, and labelled as one.

Not by timestamp (#1100): the workflow is revise, re-adjudicate, commit
together, so an evaluation's timestamp precedes the commit of the version
that produced it and a time lookup returns the version being replaced. It was
wrong on 19 of 43. The timestamp is also model-written and stale in places.

The test is that **no evaluation is unresolved**. A new evaluation whose
instrument cannot be placed either way fails here rather than joining the
corpus unidentifiable.
"""
import pytest
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "data" / "evaluation_instruments.json"
SCRIPT = ROOT / "scripts" / "instrument_provenance.py"
RUBRICS = ("rubric10_semantic", "rubric20_semantic")
AGENT_PATHS = {
    "rubric10_semantic": ".claude/agents/d4d-rubric10-semantic.md",
    "rubric20_semantic": ".claude/agents/d4d-rubric20-semantic.md",
}


def _shallow():
    """CI checks out at depth 1 (#1100), where `git log --all` sees one
    commit and every evaluation resolves to nothing. Tests that need history
    skip; the ones that check the checked-in manifest against the artifacts
    do not need it and still run."""
    out = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                         capture_output=True, text=True, cwd=ROOT).stdout
    return out.strip() == "true"


class InstrumentManifest(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest("no manifest in this checkout")
        self.doc = json.loads(MANIFEST.read_text())

    def _live(self, rubric):
        base = ROOT / "data" / "evaluation_llm" / rubric
        return sorted(str(p.relative_to(base))
                      for p in base.rglob("*_evaluation.json")) \
            if base.exists() else []


class TestEveryEvaluationNamesItsInstrument(InstrumentManifest):
    def test_no_evaluation_is_unresolved(self):
        """The property the manifest exists for."""
        unresolved = [(rubric, name)
                      for rubric in RUBRICS
                      for name, entry in self.doc["rubrics"][rubric]["evaluations"].items()
                      if entry["basis"] == "unresolved"
                      or not entry.get("instrument_sha256")]
        self.assertEqual(unresolved, [])

    def test_the_manifest_covers_exactly_the_live_evaluations(self):
        for rubric in RUBRICS:
            with self.subTest(rubric=rubric):
                self.assertEqual(
                    sorted(self.doc["rubrics"][rubric]["evaluations"]),
                    self._live(rubric),
                    "run scripts/instrument_provenance.py --write")

    def test_a_recovered_basis_says_what_it_recovered_from(self):
        """A recovered claim must not read like a recorded one (#399)."""
        for rubric in RUBRICS:
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                if entry["basis"] != "recovered_from_commit":
                    continue
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertIn("recorded_hash_is", entry)
                    self.assertTrue(entry.get("recovered_from"),
                                    "a recovered instrument must name the "
                                    "commit it was recovered from")

    def test_an_uncommitted_evaluation_resolves_to_the_agent_on_disk(self):
        """#1100: `d4d evaluate llm` leaves an untracked evaluation, and
        resolving it from the previous commit would name an instrument that
        did not produce it — so the state immediately after producing a score
        failed the suite, saying the corpus was unidentifiable when the honest
        answer is "not committed yet; the instrument is the file on disk"."""
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        source = SCRIPT.read_text()
        self.assertIn('"basis": "working_tree"', source)
        self.assertIn("def _dirty(", source)

    def test_the_archived_scorings_are_in_scope(self):
        """The `superseded_*` directories hold the scorings #1059, #1060 and
        #1082 displaced — the direct evidence of the instrument changes this
        exists to make legible, and the first thing the glob left out."""
        names = set(self.doc["rubrics"]["rubric10_semantic"]["evaluations"])
        self.assertTrue(any(n.startswith("label_aware/superseded_") for n in names),
                        "no archived scoring is covered")
        for marker in ("superseded_software_threshold", "superseded_gate_v1",
                       "superseded_fable5"):
            with self.subTest(archive=marker):
                self.assertTrue(any(marker in n for n in names))

    def test_no_entry_is_resolved_by_timestamp(self):
        """#1100. A time lookup returns the version the run's own commit
        replaced — off by one towards the instrument the revision corrected,
        wrong on 19 of 43 — because the agent and its rescores are committed
        together. `evaluation_timestamp` is model-written besides, and three
        CM4AI files record a time hours before the commit of the text they
        hash. The basis must be the commit that carries the bytes."""
        for rubric in RUBRICS:
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertNotEqual(entry["basis"], "recovered_by_time")
                    self.assertNotIn("evaluated_at", entry)

    def test_recovered_commit_contains_the_evaluation_and_named_agent(self):
        """Verify both artifacts in git, including scores archived later."""
        if _shallow():
            self.skipTest("shallow clone: no history to resolve against")
        for rubric, agent in AGENT_PATHS.items():
            base = ROOT / "data" / "evaluation_llm" / rubric
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                if entry["basis"] != "recovered_from_commit":
                    continue
                with self.subTest(rubric=rubric, evaluation=name):
                    commit = entry["recovered_from"]
                    history = subprocess.run(
                        ["git", "log", "--follow", "--find-renames=100%",
                         "--format=%H", "--", str(base / name)],
                        capture_output=True, text=True, cwd=ROOT, check=True).stdout
                    self.assertTrue(any(c.startswith(commit) for c in history.split()))
                    # Its historic path may differ. Match the actual JSON
                    # blob against the rubric tree at the recovered commit.
                    evaluation_blob = subprocess.run(
                        ["git", "hash-object", str(base / name)],
                        capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
                    tree_blobs = subprocess.run(
                        ["git", "ls-tree", "-r", "--format=%(objectname)", commit,
                         "--", str(base.relative_to(ROOT))],
                        capture_output=True, text=True, cwd=ROOT, check=True).stdout.split()
                    self.assertIn(evaluation_blob, tree_blobs)
                    blob = subprocess.run(["git", "show", f"{commit}:{agent}"],
                                          capture_output=True, cwd=ROOT, check=True)
                    self.assertEqual(
                        hashlib.sha256(blob.stdout).hexdigest(),
                        entry["instrument_sha256"])

    def test_every_named_instrument_is_a_real_agent_version(self):
        """Against git, not against the manifest's own list (#1100).

        Checking `instrument_sha256` against the manifest's `agent_versions`
        was an internal-consistency check: a fabricated hash passed as long as
        it was also appended to that block. These are hashes of real blobs or
        they are nothing.
        """
        if _shallow():
            self.skipTest("shallow clone: no history to hash against")
        for rubric, agent in AGENT_PATHS.items():
            real = set()
            for commit in subprocess.run(
                    ["git", "log", "--all", "--format=%H", "--", agent],
                    capture_output=True, text=True, cwd=ROOT).stdout.split():
                blob = subprocess.run(["git", "show", f"{commit}:{agent}"],
                                      capture_output=True, cwd=ROOT)
                if not blob.returncode:
                    real.add(hashlib.sha256(blob.stdout).hexdigest())
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                with self.subTest(rubric=rubric, evaluation=name):
                    if entry["basis"] == "recorded_composed_definition":
                        from data_sheets_schema.root_scope_definition import compose_definition
                        composed, provenance = compose_definition(rubric.removesuffix("_semantic"), repo_root=ROOT)
                        self.assertEqual(entry, {"basis": "recorded_composed_definition",
                            "instrument_kind": "composed_agent_definition", "instrument_commit": None,
                            "instrument_sha256": hashlib.sha256(composed).hexdigest(), "composition": provenance})
                        artifact = json.loads((ROOT / "data/evaluation_llm" / rubric / name).read_text())
                        self.assertEqual(artifact["metadata"]["instrument_sha256"], entry["instrument_sha256"])
                        continue
                    self.assertIn(entry["instrument_sha256"], real)

    def test_a_recorded_instrument_is_read_from_the_new_key_when_present(self):
        """#1100: the resolver read only `rubric_hash`, so an evaluation that
        obeyed the revised contract and recorded its instrument outright was
        still resolved from its writing commit. Following the fix downgraded
        the evidence it produced."""
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        source = SCRIPT.read_text()
        self.assertIn('meta.get("instrument_sha256") or meta.get("rubric_hash")',
                      source)


class TestTheContractAsksForTheScoringRules(unittest.TestCase):
    """The fix itself: the contract now names the file whose bytes decide a
    score, not only the text it reads."""

    def test_both_agents_ask_for_their_own_hash(self):
        for name in ("d4d-rubric10-semantic", "d4d-rubric20-semantic"):
            with self.subTest(agent=name):
                text = (ROOT / ".claude" / "agents" / f"{name}.md").read_text()
                self.assertIn(f'"instrument_sha256": "<sha256 of '
                              f'.claude/agents/{name}.md, this file>"', text)
                self.assertIn("Why two hashes (#1077)", text)

    def test_the_rubric_hash_names_its_path(self):
        """`<sha256 of rubric10.txt>` named no path, which is part of why
        three different sources ended up in the field."""
        for name, rubric in (("d4d-rubric10-semantic", "rubric10"),
                             ("d4d-rubric20-semantic", "rubric20")):
            with self.subTest(agent=name):
                text = (ROOT / ".claude" / "agents" / f"{name}.md").read_text()
                # Version 2 examples carry a real source-text digest. Keep
                # the named source path beside the example so a caller knows
                # which bytes to hash, and verify that the example is current.
                digest = hashlib.sha256((ROOT / "data" / "rubric" / f"{rubric}.txt").read_bytes()).hexdigest()
                self.assertIn(f'"rubric_sha256": "{digest}"', text)
                self.assertIn(f"data/rubric/{rubric}.txt", text)


@pytest.mark.corpus   # walks the committed corpus; the main-branch lane (#1203)
class TestTheResolverIsReproducible(InstrumentManifest):
    def test_regenerating_the_manifest_changes_nothing(self):
        """Content, not counts (#1100).

        The first version compared the summary line, so a manifest whose
        entries had all moved to different — but equally distributed —
        instruments would have passed. It rebuilds and compares the mapping.
        """
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        if _shallow():
            self.skipTest("shallow clone: git history is not available")
        import importlib.util
        spec = importlib.util.spec_from_file_location("_ip", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for rubric in RUBRICS:
            with self.subTest(rubric=rubric):
                #: The whole block, not only the attributions (#1100). Every
                #: agent revision adds a version the committed manifest lacks
                #: while attributions and counts stay identical — which is how
                #: the first manifest shipped stale — so `agent_versions` has
                #: to be compared too.
                self.assertEqual(module.resolve(rubric),
                                 self.doc["rubrics"][rubric],
                                 "the manifest disagrees with a fresh resolve; "
                                 "run scripts/instrument_provenance.py --write")


def _composition_resolver():
    import importlib.util
    spec = importlib.util.spec_from_file_location("composition_resolver_controls", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _composition_case(tmp_path, monkeypatch, rubric):
    from data_sheets_schema.root_scope_definition import DEFINITION_PINS
    from tests.test_evaluation.test_root_scope_instrument import root_fixture
    result, _, _, _, _ = root_fixture(tmp_path / "shape", rubric)
    checkout = tmp_path / "checkout"
    pins = DEFINITION_PINS[rubric]
    for key in ("source_path", "overrides_path"):
        destination = checkout / pins[key]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / pins[key]).read_bytes())
    instrument = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
    result.update(instrument_id=instrument, scorer_instrument={"id": instrument})
    output = checkout / "data/evaluation_llm" / (rubric + "_semantic") / "label_aware" / instrument / "Toy_evaluation.json"
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(result))
    module = _composition_resolver()
    monkeypatch.setattr(module, "ROOT", checkout)
    monkeypatch.setattr(module, "versions", lambda path: [
        {"sha256": pins["source_sha256"], "first_seen": "synthetic", "commit": "legacy"}]
        if path == pins["source_path"] else [])
    def legacy_forbidden(*values):
        raise AssertionError("v6 fell through to legacy instrument recovery")
    monkeypatch.setattr(module, "_dirty", legacy_forbidden)
    monkeypatch.setattr(module, "_writing_commit", legacy_forbidden)
    return module, result, output, pins


def test_root_scope_composition_resolves_realistic_v6_shapes(tmp_path, monkeypatch, rubric):
    module, result, output, pins = _composition_case(tmp_path, monkeypatch, rubric)
    block = module.resolve(rubric + "_semantic")
    assert len(block["evaluations"]) == 1
    entry = next(iter(block["evaluations"].values()))
    assert entry == {"basis": "recorded_composed_definition", "instrument_kind": "composed_agent_definition",
                     "instrument_sha256": result["metadata"]["instrument_sha256"],
                     "instrument_commit": None, "composition": dict(pins)}
    assert output.read_text() == json.dumps(result)


def test_root_scope_composition_drift_never_recovers_a_legacy_agent(tmp_path, monkeypatch, rubric, mutation):
    module, result, output, pins = _composition_case(tmp_path, monkeypatch, rubric)
    if mutation in ("source", "override"):
        path = module.ROOT / pins["source_path" if mutation == "source" else "overrides_path"]
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "missing_digest":
        result["metadata"]["rubric_hash"] = result["metadata"].pop("instrument_sha256")
    elif mutation == "old_digest":
        result["metadata"]["instrument_sha256"] = pins["source_sha256"]
    elif mutation == "wrong_digest":
        result["metadata"]["instrument_sha256"] = "0" * 64
    elif mutation == "wrong_rubric":
        result["rubric"] = "rubric20-semantic" if rubric == "rubric10" else "rubric10-semantic"
    elif mutation == "unknown_kind":
        result["metadata"]["instrument_kind"] = "api_system_prompt"
    elif mutation == "wrong_version":
        result["version"] = "3.0"
    elif mutation == "missing_metadata":
        result.pop("metadata")
    elif mutation == "wrong_scope":
        result["evaluation_scope"]["units"][0]["path"] = "#/resources/0"
    output.write_text(json.dumps(result))
    # The real checkout remains valid. The explicit synthetic root must govern
    # composition even when cwd and installed resources could otherwise pass.
    monkeypatch.chdir(ROOT)
    entry = next(iter(module.resolve(rubric + "_semantic")["evaluations"].values()))
    assert entry["basis"] == "unresolved" and entry["instrument_sha256"] is None
    assert entry["instrument_commit"] is None and "reason" in entry


def test_root_scope_composition_independent_markers_prevent_fallback(tmp_path, monkeypatch, marker):
    module, result, output, _ = _composition_case(tmp_path, monkeypatch, "rubric20")
    malformed = {"metadata": result["metadata"]}
    if marker == "version":
        malformed["version"] = "6.0"
    elif marker == "scope":
        malformed["evaluation_scope"] = result["evaluation_scope"]
    elif marker == "instrument":
        malformed["instrument_id"] = result["instrument_id"]
    elif marker == "scorer":
        malformed["scorer_instrument"] = result["scorer_instrument"]
    if marker != "directory":
        plain = output.parents[1] / "historical-looking" / output.name
        plain.parent.mkdir()
        output.rename(plain)
        output = plain
    output.write_text(json.dumps(malformed))
    entry = next(iter(module.resolve("rubric20_semantic")["evaluations"].values()))
    assert entry["basis"] == "unresolved" and entry["instrument_sha256"] is None


def test_root_scope_composition_leaves_historical_resolution_unchanged(tmp_path, monkeypatch, ancestor):
    module = _composition_resolver()
    checkout = tmp_path / ancestor
    monkeypatch.setattr(module, "ROOT", checkout)
    base = checkout / "data/evaluation_llm/rubric10_semantic/label_aware"
    base.mkdir(parents=True)
    source = checkout / ".claude/agents/d4d-rubric10-semantic.md"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic historical scoring rules\n")
    agent_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    rubric_hash = hashlib.sha256(b"synthetic rubric text").hexdigest()
    agent = {"sha256": agent_hash, "first_seen": "synthetic", "commit": "abc12345"}
    text = {"sha256": rubric_hash, "first_seen": "synthetic", "commit": "def12345"}
    monkeypatch.setattr(module, "versions", lambda path: [agent] if path.endswith(".md") else [text])
    monkeypatch.setattr(module, "_dirty", lambda path: Path(path).name == "dirty_evaluation.json")
    monkeypatch.setattr(module, "_writing_commit", lambda path: "a" * 40)
    monkeypatch.setattr(module, "_agent_at", lambda *values: agent_hash)
    for name, meta in (("recorded", {"instrument_sha256": agent_hash}),
                       ("recovered", {"rubric_hash": rubric_hash}),
                       ("dirty", {"rubric_hash": rubric_hash})):
        (base / (name + "_evaluation.json")).write_text(json.dumps({"version": "3.0", "metadata": meta}))
    assert module.resolve("rubric10_semantic") == {"agent_versions": [agent], "evaluations": {
        "label_aware/recorded_evaluation.json": {"basis": "recorded", "instrument_sha256": agent_hash,
                                                 "instrument_commit": "abc12345"},
        "label_aware/recovered_evaluation.json": {"basis": "recovered_from_commit",
            "recorded_hash_is": "the rubric text, which does not identify the scoring rules",
            "recovered_from": "aaaaaaaa", "instrument_sha256": agent_hash, "instrument_commit": "abc12345"},
        "label_aware/dirty_evaluation.json": {"basis": "working_tree",
            "recorded_hash_is": "the rubric text, which does not identify the scoring rules",
            "recovered_from": "the agent file on disk; this evaluation is not committed",
            "instrument_sha256": agent_hash, "instrument_commit": "abc12345"}}}


test_root_scope_composition_resolves_realistic_v6_shapes = pytest.mark.parametrize(
    "rubric", ("rubric10", "rubric20"))(test_root_scope_composition_resolves_realistic_v6_shapes)
test_root_scope_composition_drift_never_recovers_a_legacy_agent = pytest.mark.parametrize(
    "rubric", ("rubric10", "rubric20"))(pytest.mark.parametrize("mutation", (
        "source", "override", "missing_digest", "old_digest", "wrong_digest", "wrong_rubric",
        "unknown_kind", "wrong_version", "missing_metadata", "wrong_scope"))(
        test_root_scope_composition_drift_never_recovers_a_legacy_agent))
test_root_scope_composition_independent_markers_prevent_fallback = pytest.mark.parametrize(
    "marker", ("version", "scope", "instrument", "scorer", "directory"))(
    test_root_scope_composition_independent_markers_prevent_fallback)
test_root_scope_composition_leaves_historical_resolution_unchanged = pytest.mark.parametrize(
    "ancestor", ("checkout", "checkout_root-scope-v6"))(
    test_root_scope_composition_leaves_historical_resolution_unchanged)


if __name__ == "__main__":
    unittest.main()
