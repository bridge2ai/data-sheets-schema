"""The notes/ instruction builders, rendered, quote no held-out observation (#3198).

tests/test_audit_recall_leak.py reads the Python under notes/ as source text
and as its string constants. That finds an observation pasted into a builder
as a literal, but not one a builder assembles at run time from a file it reads
or a value it formats. Here the builders are called, offline and against
synthetic inputs, and the same needle match runs over what they return:

- ``native_command_policy.command_guidance``, appended to both arms' system
  prompts, on a synthetic policy that selects every optional block;
- the audit ``prepare.SYSTEM`` / ``render_system`` and ``contract.render_instruction``
  on registrations the real preparer writes: the default condition, staged
  output, context recovery, the drafted persistent protocol-contract condition,
  and the fresh-context batch at renderers 20 and 23, whose every child system
  (``batch_registration.child_system``) and parent instruction and system are
  rendered too;
- the finalization ``render_system`` and ``render_instruction``, with and
  without context recovery, and the report context the trusted derivation
  writes (``contract._report_context``);
- ``evaluation_controls.instructions.render_instruction``, on a synthetic
  record and context shaped as in its own test;
- ``native_context_control.render_system``, through the recovery conditions above.

``render_instruction`` is read back from the file the preparer rendered it
into and the registration pins, rather than called a second time: each call
replays the parent generation request, which takes seconds.

The registrations come from the pinned notes/ fixtures (``ancestry``,
``metadata_ancestry``), which stub only historical ancestry and refuse to
construct a provider. Everything is written under ``tmp_path``; the pinned
tree is checked unchanged after every test, imports included.

Not rendered: the worker-checkpoint branch of ``render_parent_instruction``
(it needs a completed, sealed batch attempt; its text is literals and hashes,
which the literal scan covers); the audit-batch integration instruction
(``audit_batch_context.render_integration_context``, called by ``batch_native``
at run time with the workers' sealed proposals, which are model output); and
the notes/claudecode_direct builders, which the issue did not name. A paraphrase
stays out of reach of any text scan.
"""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from tests.test_audit_recall_leak import MATCHED, ROOT, matches, needles  # noqa: F401 (fixture)

CONTROLS = ROOT / MATCHED


def _pinned_tree():
    """Size and mtime of every file under the pinned directory, bytecode aside."""
    return {str(p.relative_to(CONTROLS)): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in CONTROLS.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


#: Taken before the first import from notes/, so a write at import time is seen too.
PINNED_BEFORE_IMPORT = _pinned_tree()

# The notes/ controls import each other as top-level modules, as their own
# tests do (their README and CI put these two directories on PYTHONPATH).
for _path in (CONTROLS / "native_controls", CONTROLS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from audit_controls import batch_registration, prepare as audit_prepare  # noqa: E402
from audit_controls import registration as audit_registration  # noqa: E402
from audit_controls.test_context_preparation import ancestry, stage_prepare  # noqa: E402,F401 (fixture)
from audit_controls.test_source_metadata_upgrade import metadata_ancestry  # noqa: E402,F401 (fixture)
from finalization_controls import contract as final_contract, prepare as final_prepare  # noqa: E402
from finalization_controls import registration as final_registration  # noqa: E402
import native_command_policy  # noqa: E402

BATCHES = {"kind": batch_registration.KIND, "worker_total_cap_usd": "12"}
PLANTED = "A planted synthetic observation that only a runtime input carries."


@pytest.fixture(autouse=True)
def pinned_tree_unchanged():
    """No import or rendering here writes a registration, ledger or anything else under notes/."""
    yield
    assert _pinned_tree() == PINNED_BEFORE_IMPORT


def _found(rendered, needles):
    assert rendered and all(isinstance(text, str) and text for text in rendered.values()), rendered.keys()
    return {name: hit for name, text in rendered.items() if (hit := matches(text, needles))}


def command_policy(planted=""):
    """Every optional block of the guidance: literal admission, helpers, lookup admission."""
    return {"literal_admission": native_command_policy.LITERAL_ADMISSION,
            "lookup_literal_admission": native_command_policy.LOOKUP_LITERAL_ADMISSION,
            "command_examples": ["python -c 'print(1)'"],
            "helper_arguments": {"spellings": {"receipts": ["d4d receipts check --label synthetic"]}},
            "readonly_lookups": {"inputs": ["/synthetic/inputs/record.yaml" + planted],
                                 "output_directories": ["/synthetic/output"]}}


def rendered_command_guidance(planted=""):
    return {"command_guidance": native_command_policy.command_guidance(command_policy(planted))}


AUDIT_CONDITIONS = {
    "default": ("ancestry", {}),
    "context recovery": ("ancestry", {"context_recovery": True}),
    "staged output": ("ancestry", {"staged_audit_output": True}),
    "staged output, context recovery": ("ancestry", {"staged_audit_output": True, "context_recovery": True}),
    "drafts, persistent contract": ("metadata_ancestry", {
        "draft_audit_grammar": True, "schema_semantic_context": True, "persistent_audit_contract": True}),
    "drafts, persistent contract, context recovery": ("metadata_ancestry", {
        "draft_audit_grammar": True, "persistent_audit_contract": True, "context_recovery": True}),
    "batch renderer 20": ("metadata_ancestry", {"audit_batches": BATCHES}),
    "batch renderer 23": ("metadata_ancestry", {
        "audit_batches": BATCHES, "audit_batch_format": True, "audit_batch_navigation": True,
        "audit_worker_navigation": True}),
}


def rendered_audit(request, tmp_path, condition):
    fixture, options = AUDIT_CONDITIONS[condition]
    args = request.getfixturevalue(fixture)[0]
    path = audit_prepare.prepare(**args, destination=tmp_path / "audit", **options)
    manifest = audit_registration.validate_registration(path)
    # The preparer wrote contract.render_instruction(manifest) there and pinned it;
    # rendering it again replays the parent generation request (seconds each).
    rendered = {"SYSTEM": audit_prepare.SYSTEM, "system": audit_prepare.render_system(manifest),
                "instruction": Path(manifest["job"]["instruction"]).read_text(encoding="utf-8")}
    if "audit_batches" in manifest:
        rendered["parent system"] = batch_registration.render_parent_system(manifest)
        rendered["parent instruction"] = batch_registration.render_parent_instruction(manifest)
        for child in manifest["audit_batches"]["children"]:
            rendered[f"{child['id']} system"] = batch_registration.child_system(manifest, child["id"])
    return manifest, rendered


def rendered_finalization(ancestry, tmp_path, recovery, full="description: The service is planned.\n"):
    path, _, _ = stage_prepare("finalization", ancestry, tmp_path / "final", recovery)
    manifest = final_registration.validate_registration(path)
    return {"SYSTEM": final_prepare.SYSTEM, "system": final_prepare.render_system(manifest),
            "instruction": Path(manifest["job"]["instruction"]).read_text(encoding="utf-8"),
            "report context": final_contract._report_context(manifest, full, full)}


@pytest.fixture
def evaluation_instructions():
    """``instructions`` imports its siblings as top-level ``registration`` and
    ``validation``, names the audit and finalization controls also use; they
    are loaded for this test only and dropped afterwards."""
    directory = CONTROLS / "evaluation_controls"
    before = set(sys.modules)
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location("recall_leak_evaluation_instructions",
                                                      directory / "instructions.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(directory))
        for name in set(sys.modules) - before:
            if Path(getattr(sys.modules[name], "__file__", None) or "/").parent == directory:
                del sys.modules[name]


def rendered_evaluation(instructions, tmp_path, planted=""):
    """The shape of evaluation_controls/test_instructions.py: a synthetic record and context."""
    source = tmp_path / "record.yaml"
    source.write_text(f"conforms_to_class: Dataset\nname: Synthetic record\ndescription: {planted or 'x'}\n")
    context = tmp_path / "context.json"
    context.write_text(json.dumps({"human_subjects": {"value": True, "evidence": "Synthetic source"}}))
    job = {"id": "synthetic-rating1", "style": "semantic_agent", "rubric": "rubric10-semantic",
           "variant": "full", "class_name": "Dataset", "project": "example", "method": "synthetic",
           "input": str(source), "context_path": str(context),
           "agent_definition": str(ROOT / ".claude/agents/d4d-rubric10-semantic.md"),
           "rubric_file": str(ROOT / "data/rubric/rubric10.txt"),
           "candidate": str(tmp_path / "output/result.json"), "instruction": str(tmp_path / "instruction.txt")}
    manifest = {"python": sys.executable, "model": {"model": "synthetic-model"},
                "prompts_dir": str(ROOT / "src/download/prompts"),
                "pinned_files": {job[k]: instructions.sha(job[k])
                                 for k in ("input", "context_path", "agent_definition", "rubric_file")}}
    return {"instruction": instructions.render_instruction(manifest, job)}


def test_the_rendered_command_guidance_quotes_nothing(needles):
    assert _found(rendered_command_guidance(), needles) == {}


@pytest.mark.parametrize("condition", list(AUDIT_CONDITIONS))
def test_the_rendered_audit_prompts_quote_nothing(request, tmp_path, needles, condition):
    manifest, rendered = rendered_audit(request, tmp_path, condition)
    if condition.startswith("batch"):
        # Every child's system, and the parent identity rather than the scientific instruction.
        assert {f"{c['id']} system" for c in manifest["audit_batches"]["children"]} < rendered.keys()
        assert rendered["instruction"] == rendered["parent instruction"]
    else:
        assert Path(manifest["inputs"]["original_full"]).read_text() in rendered["instruction"]
    if "context recovery" in condition:
        assert "Persistent registered context recovery" in rendered["system"]
    assert _found(rendered, needles) == {}


@pytest.mark.parametrize("recovery", [False, True])
def test_the_rendered_finalization_prompts_quote_nothing(ancestry, tmp_path, needles, recovery):
    rendered = rendered_finalization(ancestry, tmp_path, recovery)
    assert ("Persistent registered context recovery" in rendered["system"]) is recovery
    assert _found(rendered, needles) == {}


def test_the_rendered_evaluation_instruction_quotes_nothing(evaluation_instructions, tmp_path, needles):
    assert _found(rendered_evaluation(evaluation_instructions, tmp_path), needles) == {}


def _planted_protocol(manifest, tmp_path):
    """A batch child re-reads the registered protocol file when its system is rendered."""
    protocol = tmp_path / "planted_protocol.md"
    protocol.write_text(Path(manifest["inputs"]["protocol"]).read_text() + "\n" + PLANTED + "\n")
    manifest["inputs"]["protocol"] = str(protocol)
    child = manifest["audit_batches"]["children"][0]["id"]
    return {f"{child} system": batch_registration.child_system(manifest, child)}


@pytest.mark.parametrize("builder", ["command guidance", "batch child system", "finalization report context",
                                     "evaluation instruction"])
def test_an_observation_in_a_runtime_input_reaches_the_rendered_scan(request, tmp_path, builder):
    """The gap the literal scan leaves (#3198): text no scanned source carries as a literal."""
    if builder == "command guidance":
        rendered = rendered_command_guidance(planted=" " + PLANTED)
    elif builder == "batch child system":
        manifest, _ = rendered_audit(request, tmp_path, "batch renderer 23")
        rendered = _planted_protocol(manifest, tmp_path)
    elif builder == "finalization report context":
        rendered = rendered_finalization(request.getfixturevalue("ancestry"), tmp_path, False,
                                         full=f"description: {PLANTED}\n")
    else:
        rendered = rendered_evaluation(request.getfixturevalue("evaluation_instructions"), tmp_path, PLANTED)
    assert list(_found(rendered, [PLANTED]).values()) == [[PLANTED]]
