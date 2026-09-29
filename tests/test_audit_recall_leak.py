"""Held-out audit ground truth reaches no instruction and no registered input (#2921).

The observations score an audit only while the audit never saw them
(notes/native_audit_continuation_plan_2026-09-18.md). The native file policy is
an instruction-conformance check, not a filesystem sandbox, so the guard is
that nothing a generation or audit model is given names the ground-truth
directory or quotes an observation. These scans cover the condition prompts,
playbooks, agent definitions and assistant instructions, the direct arm's
system prompt, the rendered audit-batch contexts and output contracts, the
registered native inputs, and every file under src/ other than the instrument
itself. A committed ground-truth file that does not load fails here too.
"""
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import audit_batch_context, audit_batch_format, audit_batches, chunking
from data_sheets_schema.agentic_runtime import SCHEMAS
from data_sheets_schema.audit_recall import load_ground_truth
from data_sheets_schema.profiles import NEUTRAL
from data_sheets_schema.provenance import AGENT_PLAYBOOKS

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "data" / "audit_ground_truth"
SCHEMA_NAME = "ground_truth.schema.json"
NAMES = (GROUND_TRUTH.name, GROUND_TRUTH.name.replace("_", "-"))
INSTRUMENT = ROOT / "src" / "data_sheets_schema" / "audit_recall.py"
INSTRUCTION_TREES = ("src/download/prompts", ".claude", ".github/workflows")
INSTRUCTION_FILES = ("notes/claudecode_direct/system.md",)
REGISTERED_INPUT_TREES = ("data/preprocessed/chunks", "data/preprocessed/concatenated")
REGISTERED_INPUT_FILES = ("data/preprocessed/source_manifest.yaml",)


def committed_observations():
    found = []
    for path in sorted(GROUND_TRUTH.iterdir()):
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json"} and path.name != SCHEMA_NAME:
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


def leaks(paths, needles):
    return {str(p.relative_to(ROOT)): found for p in paths
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
    assert (GROUND_TRUTH / SCHEMA_NAME).is_file()


def test_no_instruction_file_names_the_directory_or_quotes_an_observation(needles):
    assert leaks(files_under(*INSTRUCTION_TREES, *INSTRUCTION_FILES), needles) == {}


def test_no_registered_native_input_does(needles):
    registered = [ROOT / p for p in (*SCHEMAS, *AGENT_PLAYBOOKS)]
    registered += files_under(*REGISTERED_INPUT_TREES, *REGISTERED_INPUT_FILES)
    assert all(p.is_file() for p in registered)
    assert [p for p in registered if GROUND_TRUTH in p.resolve().parents] == []
    assert leaks(registered, needles) == {}


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
