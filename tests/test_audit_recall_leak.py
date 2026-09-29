"""Held-out audit ground truth reaches no instruction and no registered input (#2921).

The observations score an audit only while the audit never saw them
(notes/native_audit_continuation_plan_2026-09-18.md). The native file policy is
an instruction-conformance check, not a filesystem sandbox, so the guard is
that nothing a generation or audit model is given names the ground-truth
directory or quotes an observation. These scans cover:

- the condition prompts, playbooks, agent definitions and assistant instructions;
- the matched arms' launch prompts and rubric system prompts;
- the direct and native arms' system prompts;
- the Python source under notes/ that builds model-facing text: the command
  guidance appended to both arms' system prompts, the audit system prompts and
  batch framing, the finalization and evaluation instructions, context recovery;
- the rendered audit-batch contexts and output contracts;
- the registered native inputs;
- every registration record under notes/, whose inputs may not
  name the directory;
- every file under src/ other than the instrument itself.

The files under notes/ are pinned: they are read here and never edited. A
committed ground-truth file that does not load, at any depth of the directory,
fails here too, and so does a file there that is neither a ground-truth file
nor the README or schema.

Not scanned: a launch message typed at run time, and a registration or a
rendered instruction written outside the repository. Those are the
operator's to keep clean.
"""
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import audit_batch_context, audit_batch_format, audit_batches, chunking
from data_sheets_schema.agentic_runtime import SCHEMAS
from data_sheets_schema.audit_recall import GroundTruthError, load_ground_truth
from data_sheets_schema.profiles import NEUTRAL
from data_sheets_schema.provenance import AGENT_PLAYBOOKS

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "data" / "audit_ground_truth"
SCHEMA_NAME = "ground_truth.schema.json"
NAMES = (GROUND_TRUTH.name, GROUND_TRUTH.name.replace("_", "-"))
INSTRUMENT = ROOT / "src" / "data_sheets_schema" / "audit_recall.py"
MATCHED = "notes/matched_cborg_2026-09-13"
INSTRUCTION_TREES = ("src/download/prompts", ".claude", ".github/workflows",
                     f"{MATCHED}/prompts")   # the matched arms' launch prompts, rubric system prompts
INSTRUCTION_FILES = ("notes/claudecode_direct/system.md",         # the direct arm's system prompt
                     f"{MATCHED}/native_controls/system.md")      # the native arm's (prepare_overlay)
#: Python whose string literals become model-facing text: command_guidance in
#: native_command_policy.py, appended to both arms' system prompts; the audit
#: SYSTEM and render_system, child_system and the parent instruction in
#: audit_controls; the finalization and evaluation instructions; context
#: recovery. Every non-test .py file under these is scanned as source text (#3096).
CONTROL_CODE_TREES = ("notes/claudecode_direct", MATCHED)
#: The model-facing files #3096 found unscanned; each must stay in the scanned set.
MODEL_FACING_UNDER_NOTES = (
    f"{MATCHED}/native_controls/system.md",
    f"{MATCHED}/native_controls/native_command_policy.py",
    f"{MATCHED}/native_controls/run_native_canary.py",
    f"{MATCHED}/audit_controls/prepare.py",
    f"{MATCHED}/audit_controls/batch_registration.py",
    f"{MATCHED}/audit_controls/batch_output.py",
    f"{MATCHED}/finalization_controls/prepare.py",
    f"{MATCHED}/evaluation_controls/instructions.py",
    f"{MATCHED}/native_context_control.py",
    "notes/claudecode_direct/run_direct_canary.py",
    "notes/claudecode_direct/prepare_direct.py",
)
REGISTERED_INPUT_TREES = ("data/preprocessed/chunks", "data/preprocessed/concatenated")
REGISTERED_INPUT_FILES = ("data/preprocessed/source_manifest.yaml",)
GROUND_TRUTH_SUFFIXES = {".yaml", ".yml", ".json"}
NOT_GROUND_TRUTH = {"README.md", SCHEMA_NAME, ".DS_Store"}


def committed_observations(directory=GROUND_TRUTH):
    """Every observation in every ground-truth file under ``directory``, at any depth.

    A file that does not load raises, and so does any file that is neither a
    ground-truth file nor the README or schema: under another name it would be
    neither loaded nor scanned for (#3103).
    """
    found = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name in NOT_GROUND_TRUTH:
            continue
        if path.suffix.lower() not in GROUND_TRUTH_SUFFIXES:
            raise ValueError(f"{path.relative_to(directory)}: not .yaml, .yml or .json, so its "
                             "observations would be neither loaded nor scanned for")
        found += [entry["observation"] for entry in load_ground_truth(path.read_bytes())["entries"]]
    return found


def _fold(text):
    # A prompt may wrap or recase a quoted sentence; neither hides it here.
    return " ".join(text.split()).casefold()


def matches(text, needles):
    folded = _fold(text)
    return [needle for needle in needles if _fold(needle) in folded]


def files_under(*relatives):
    out = []
    for relative in relatives:
        base = ROOT / relative
        if base.is_file():
            out.append(base)
        elif base.is_dir():
            out += [p for p in sorted(base.rglob("*"))
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    return out


def control_code(*relatives):
    """The non-test Python source under ``relatives``."""
    return [p for p in files_under(*relatives)
            if p.suffix == ".py" and not p.name.startswith("test_") and "test_fixtures" not in p.parts]


def instruction_surfaces():
    return files_under(*INSTRUCTION_TREES, *INSTRUCTION_FILES) + control_code(*CONTROL_CODE_TREES)


def registration_records():
    """Every registration record under notes/ (``*registration*.json``)."""
    return sorted(p for p in (ROOT / "notes").rglob("*registration*.json") if p.is_file())


def leaks(paths, needles, root=ROOT):
    return {str(p.relative_to(root)): found for p in paths
            if (found := matches(p.read_bytes().decode("utf-8", errors="replace"), needles))}


@pytest.fixture(scope="module")
def needles():
    return list(NAMES) + committed_observations()


def test_the_scanner_finds_a_wrapped_recased_needle():
    """Otherwise every scan below passes by matching nothing."""
    planted = "Synthetic held-out observation\nthat a prompt   wrapped."
    assert matches("see DATA/Audit_Ground_Truth/x", NAMES) == [NAMES[0]]
    assert matches("... synthetic HELD-OUT observation that a prompt wrapped. ...", [planted]) == [planted]
    assert matches("an audit ground truth is prose", NAMES) == []


def test_the_scanned_surfaces_exist():
    for relative in INSTRUCTION_TREES + INSTRUCTION_FILES + REGISTERED_INPUT_TREES + REGISTERED_INPUT_FILES:
        assert files_under(relative), relative
    for relative in CONTROL_CODE_TREES:
        assert control_code(relative), relative
    assert ROOT / MATCHED / "registration.json" in registration_records()
    assert (GROUND_TRUTH / SCHEMA_NAME).is_file()


def test_the_model_facing_files_under_notes_are_scanned():
    """The native arm's system prompt, its command guidance and the audit framing (#3096)."""
    scanned = {p.resolve() for p in instruction_surfaces()}
    assert [f for f in MODEL_FACING_UNDER_NOTES if (ROOT / f).resolve() not in scanned] == []


def test_no_instruction_file_names_the_directory_or_quotes_an_observation(needles):
    assert leaks(instruction_surfaces(), needles) == {}


def test_no_registered_native_input_does(needles):
    registered = [ROOT / p for p in (*SCHEMAS, *AGENT_PLAYBOOKS)]
    registered += files_under(*REGISTERED_INPUT_TREES, *REGISTERED_INPUT_FILES)
    assert all(p.is_file() for p in registered)
    assert [p for p in registered if GROUND_TRUTH in p.resolve().parents] == []
    assert leaks(registered, needles) == {}


def test_no_registration_record_under_notes_does(needles):
    """A registration's inputs, pins and closures may not name the directory."""
    assert leaks(registration_records(), needles) == {}


def test_only_the_instrument_under_src_names_the_directory(needles):
    others = [p for p in files_under("src") if p.resolve() != INSTRUMENT.resolve()]
    assert leaks(others, needles) == {}
    assert matches(INSTRUMENT.read_text(encoding="utf-8"), committed_observations()) == []


def test_audit_duties_and_output_contracts_do_not(needles):
    texts = {"common": audit_batch_context.COMMON_DUTIES, "worker": audit_batch_context.WORKER_DUTIES,
             "global": audit_batch_context.GLOBAL_DUTIES,
             "format worker": audit_batch_format.render("worker"),
             "format integration": audit_batch_format.render("integration")}
    assert {name: found for name, text in texts.items() if (found := matches(text, needles))} == {}


def _ground_truth_file(observation, ident="ex-001"):
    """A loadable synthetic ground-truth file carrying ``observation``."""
    entry = {"id": ident, "target_original_full_sha256": "a" * 64, "paths": ["/title"],
             "kind": "other", "governing_source": {"bundle_sha256": "b" * 64, "chunk": "c001", "lines": [1, 2]},
             "observation": observation, "reviewer_role": "independent reviewer",
             "reviewed_on": "2026-09-18", "provenance_note": "notes/example_review.md", "held_out": True}
    return yaml.safe_dump({"format": "audit_ground_truth_v1", "project": "EXAMPLE", "entries": [entry]})


def test_the_collector_loads_every_ground_truth_file_at_any_depth(tmp_path):
    (tmp_path / "EXAMPLE_v1.yaml").write_text(_ground_truth_file("First synthetic observation."))
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "EXAMPLE_v2.YML").write_text(_ground_truth_file("Nested synthetic observation."))
    (tmp_path / "README.md").write_text("Not ground truth.\n")
    (tmp_path / SCHEMA_NAME).write_text("{}\n")
    assert committed_observations(tmp_path) == ["First synthetic observation.", "Nested synthetic observation."]


def test_a_committed_file_that_does_not_load_or_is_not_ground_truth_fails_the_guard(tmp_path):
    bad = tmp_path / "sub" / "BAD_v1.yaml"
    bad.parent.mkdir()
    bad.write_text(yaml.safe_dump({"format": "audit_ground_truth_v1", "project": "EXAMPLE",
                                   "entries": [{"observation": "Incomplete."}]}))
    with pytest.raises(GroundTruthError):
        committed_observations(tmp_path)
    bad.unlink()
    (tmp_path / "CHORUS_v1.yaml.txt").write_text(_ground_truth_file("Misnamed synthetic observation."))
    with pytest.raises(ValueError, match="neither loaded nor scanned"):
        committed_observations(tmp_path)


def test_a_collected_observation_quoted_in_an_instruction_is_a_leak(tmp_path):
    """The observation half of the scan, end to end, on a synthetic directory."""
    truth = tmp_path / "truth"
    truth.mkdir()
    (truth / "EXAMPLE_v1.yaml").write_text(_ground_truth_file("A planted synthetic observation of a defect."))
    prompt = tmp_path / "system.md"
    prompt.write_text("Audit carefully.\nA PLANTED synthetic observation\n  of a defect.\n")
    clean = tmp_path / "clean.md"
    clean.write_text("Audit carefully.\n")
    needles = [*NAMES, *committed_observations(truth)]
    assert leaks([prompt, clean], needles, root=tmp_path) == {
        "system.md": ["A planted synthetic observation of a defect."]}


@pytest.fixture
def staged(tmp_path):
    """Synthetic registered inputs beside a planted ground-truth directory."""
    schema = {"id": "https://example.invalid/leak", "name": "leak", "default_range": "string",
              "prefixes": {"ex": "https://example.invalid/leak/",
                           "xsd": "http://www.w3.org/2001/XMLSchema#"}, "default_prefix": "ex",
              "types": {"string": {"base": "str", "uri": "xsd:string"}},
              "classes": {"Dataset": {"attributes": {"caption": {}, "notes": {}}},
                          "CoreDataset": {"is_a": "Dataset"}}}
    files = {role: tmp_path / (role + ".yaml") for role in audit_batch_context.REQUIRED_INPUTS}
    for role in ("full_schema", "core_schema"):
        files[role].write_text(yaml.safe_dump(schema, sort_keys=False))
    for role in ("original_full", "original_core"):
        files[role].write_text(yaml.safe_dump({"caption": "Example caption.", "notes": "Example note."}))
    bundle = "FILE: example.txt\nPATH: evidence/example.txt\nAn example source statement.\n"
    files["bundle"].write_text(bundle)
    files["chunk_manifest"].write_text(yaml.safe_dump(
        chunking.manifest_from_bytes(bundle.encode(), files["bundle"].name), sort_keys=False))
    files["source_manifest"].write_text(yaml.safe_dump({"profile": "neutral", "projects": {
        "example": [{"id": "example", "source_type": "documentation", "processed_file": "example.txt"}]}}))
    files["protocol"].write_text("Synthetic protocol placeholder.\n")
    planted = tmp_path / GROUND_TRUTH.name
    planted.mkdir()
    observation = "Planted synthetic observation that no rendered context may carry."
    (planted / "EXAMPLE_v1.yaml").write_text(yaml.safe_dump({"entries": [{"observation": observation}]}))
    plan = audit_batches.make_plan(files["original_full"].read_text(), max_paths=1)
    return {"files": files, "plan": plan, "planted": planted, "observation": observation}


def test_rendered_audit_contexts_do_not_sweep_in_a_sibling_directory(staged, needles):
    plan = staged["plan"]
    rendered = {worker["id"]: audit_batch_context.render_worker_context(
        inputs=staged["files"], profile=NEUTRAL, project="example", plan=plan, worker_id=worker["id"])
        for worker in plan["workers"]}
    rendered["integration base"] = audit_batch_context.render_integration_base_context(
        inputs=staged["files"], profile=NEUTRAL, project="example", plan=plan)
    assert len(rendered) >= 3
    found = {name: hit for name, text in rendered.items()
             if (hit := matches(text, [*needles, staged["observation"]]))}
    assert found == {}


def test_a_ground_truth_role_is_not_an_admissible_audit_input(staged):
    inputs = {**staged["files"], "ground_truth": staged["planted"] / "EXAMPLE_v1.yaml"}
    with pytest.raises(audit_batch_context.BatchContextError, match="unexpected_scientific_input_roles"):
        audit_batch_context.render_integration_base_context(
            inputs=inputs, profile=NEUTRAL, project="example", plan=staged["plan"])
