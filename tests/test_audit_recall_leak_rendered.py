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

Several builders embed their inputs as JSON (the evaluation payload's
``complete_utf8_text`` values, the audit and finalization contracts' canonical
JSON), where a newline is the two characters ``\\n`` and a quote is ``\\"``.
The match therefore runs over every JSON object or array the rendered text
embeds, decoded, as well as over the text itself: each string value and key,
and all string values of the text joined in order, so a sentence split across
consecutive frames is found too (#3569).

``render_instruction`` is read back from the file the preparer rendered it
into and the registration pins, rather than called a second time: each call
replays the parent generation request, which takes seconds.

The registrations come from the pinned notes/ fixtures (``ancestry``,
``metadata_ancestry``), which stub only historical ancestry and refuse to
construct a provider. Everything is written under ``tmp_path``; the pinned
tree is checked unchanged after every test, imports included.

The audit-batch integration instruction and the direct arm are rendered too
(#3523):

- ``audit_batch_context.render_integration_context``, which ``batch_native``
  calls at run time with the workers' sealed proposals, on synthetic proposals
  under every navigation selection, with the worker artifacts and canonical
  row views it directs the integrator to Read. The proposals are model output,
  so a proposal that echoes the ground-truth directory or an observation is
  planted as well, and must be found;
- the notes/claudecode_direct system prompt and launch text: a registration
  prepared offline (``prepare_direct.build``, with the runtime and its login
  replaced by stand-ins) into ``tmp_path``, its launch text read back from the
  file the preparer rendered and the launcher streams, and its system prompt
  taken from the argument vector ``run_direct_canary.main`` itself builds for
  the child (the registered ``system.md`` followed by the command guidance of
  the policy it rebuilds), with the child replaced by a stand-in that captures
  its arguments and raises before anything is launched (#3740).

Not rendered: the worker-checkpoint branch of ``render_parent_instruction``
(it needs a completed, sealed batch attempt; its text is literals and hashes,
which the literal scan covers). What the workers actually return at run time
does not exist when this runs: the integration test shows the needle match
finds an echo in a proposal, not that no run will produce one. A paraphrase
stays out of reach of any text scan.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import uuid

import pytest

from data_sheets_schema import audit_batch_context, audit_batches
from data_sheets_schema.profiles import NEUTRAL
from tests.test_audit_recall_leak import (MATCHED, NAMES, ROOT, matches, needles,  # noqa: F401 (fixture)
                                          staged)  # noqa: F401 (fixture)

CONTROLS = ROOT / MATCHED
DIRECT = ROOT / "notes" / "claudecode_direct"
PINNED = (CONTROLS, DIRECT)


def _pinned_tree():
    """Size and mtime of every file under the pinned directories, bytecode aside."""
    return {str(p.relative_to(ROOT)): (p.stat().st_size, p.stat().st_mtime_ns)
            for directory in PINNED for p in directory.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts}


#: Taken before the first import from notes/, so a write at import time is seen too.
PINNED_BEFORE_IMPORT = _pinned_tree()

# The notes/ controls import each other as top-level modules, as their own
# tests do (their README and CI put these two directories on PYTHONPATH); the
# direct arm's scripts import them the same way, from their own directory.
for _path in (CONTROLS / "native_controls", CONTROLS, DIRECT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from audit_controls import batch_registration, prepare as audit_prepare  # noqa: E402
from audit_controls import registration as audit_registration  # noqa: E402
from audit_controls.test_context_preparation import ancestry, stage_prepare  # noqa: E402,F401 (fixture)
from audit_controls.test_source_metadata_upgrade import metadata_ancestry  # noqa: E402,F401 (fixture)
from finalization_controls import contract as final_contract, prepare as final_prepare  # noqa: E402
from finalization_controls import registration as final_registration  # noqa: E402
import native_command_policy  # noqa: E402
import prepare_direct as direct_preparation  # noqa: E402
import run_direct_canary as direct_launcher  # noqa: E402

BATCHES = {"kind": batch_registration.KIND, "worker_total_cap_usd": "12"}
PLANTED = "A planted synthetic observation that only a runtime input carries."


@pytest.fixture(autouse=True)
def pinned_tree_unchanged():
    """No import or rendering here writes a registration, ledger or anything else under
    the pinned notes/ directories."""
    yield
    assert _pinned_tree() == PINNED_BEFORE_IMPORT


_DECODER = json.JSONDecoder()
_OPENING = re.compile(r"[\[{]")


def _strings(value, keys):
    """String keys (into ``keys``) and values of a decoded JSON value, values in document order."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            keys.append(key)
            yield from _strings(item, keys)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item, keys)


def embedded_json_strings(text):
    """Every string in each JSON object or array ``text`` embeds, decoded, recursively.

    A rendered prompt carries its inputs JSON-escaped (``\\n``, ``\\"``), which
    whitespace folding cannot see through (#3569). Returned: each key and
    value, and every value joined in order, so one sentence split across
    consecutive frames is one string again.
    """
    found, values, index = [], [], 0
    while match := _OPENING.search(text, index):
        try:
            value, end = _DECODER.raw_decode(text, match.start())
        except ValueError:
            index = match.start() + 1
            continue
        keys = []
        values += list(_strings(value, keys))
        found += keys
        index = end
    for value in values:
        found += [value] + embedded_json_strings(value)
    return found + ["".join(values)] if values else found


def scanned_views(text):
    """The rendered text, and every string its embedded JSON decodes to."""
    return [text] + embedded_json_strings(text)


def _found(rendered, needles):
    assert rendered and all(isinstance(text, str) and text for text in rendered.values()), rendered.keys()
    return {name: hit for name, text in rendered.items()
            if (hit := sorted({n for view in scanned_views(text) for n in matches(view, needles)},
                              key=needles.index))}


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
    """The shape of evaluation_controls/test_instructions.py: a synthetic record and context.

    ``planted`` is the YAML text of the record's description value, as written.
    """
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


#: ``None`` is the renderer-20/21 text; the other two supply native Read payloads.
INTEGRATION_NAVIGATION = (None, "explicit_row_reads_v1", "explicit_child_reads_v1")
CLEAN_ISSUE = "Synthetic source-supported omission for integration consideration."
CLEAN_REASON = "Synthetic proposed judgment, not checked source support."


def worker_proposals(staged, tmp_path, issue=CLEAN_ISSUE, reason=CLEAN_REASON):
    """Sealed worker proposals as ``batch_native`` hands them over: one proposal per
    worker, its canonical row views, and the index binding them.

    ``issue`` and ``reason`` are the first worker's finding and row judgment;
    every other worker's are the clean ones. Shaped as in
    tests/test_audit_batch_context.py, on the leak guard's staged inputs.
    """
    plan, out = staged["plan"], tmp_path / "proposals"
    out.mkdir()
    evidence = [{"source": "example.txt", "chunk": "c001", "quote": "An example source statement."}]
    artifacts, data, rows = {}, {}, {}
    for number, worker in enumerate(plan["workers"]):
        values = []
        for row in plan["inventory"]["values"]:
            if row["path"] not in worker["paths"]:
                continue
            value = {"path": row["path"], "claims": [{
                "text": row["text"], "verdict": "supported", "attributed_to": [], "claim_status": "fact",
                "source_status": "fact", "evidence": evidence, "reason": reason if number == 0 else CLEAN_REASON}]}
            values.append(value)
            rows[row["path"]] = out / (audit_batches.object_sha256(value) + ".json")
            rows[row["path"]].write_bytes(audit_batches.canonical_bytes(value))
        proposal = {"findings": [{"severity": "low", "record": "full", "slot": "notes", "evidence": evidence,
                                  "issue": issue if number == 0 else CLEAN_ISSUE}],
                    "summary": "Synthetic worker proposal.",
                    "source_review": {"artifact": "original_full", "sha256": plan["original_full_sha256"],
                                      "values": values}}
        data[worker["id"]] = audit_batches.canonical_bytes(proposal)
        artifacts[worker["id"]] = out / (worker["id"] + ".json")
        artifacts[worker["id"]].write_bytes(data[worker["id"]])
    return artifacts, audit_batches.build_index(plan, data), rows


def rendered_integration(staged, proposals, navigation):
    """The integrator's instruction, and the proposals and row views it directs it to Read."""
    artifacts, index, rows = proposals
    rendered = {"integration context": audit_batch_context.render_integration_context(
        inputs=staged["files"], profile=NEUTRAL, project="example", plan=staged["plan"], worker_index=index,
        worker_artifacts=artifacts, row_artifacts=rows, audit_batch_navigation=navigation)}
    rendered.update({f"worker artifact {key}": path.read_text(encoding="utf-8") for key, path in artifacts.items()})
    rendered.update({f"row view {key}": path.read_text(encoding="utf-8") for key, path in rows.items()})
    return rendered


@pytest.fixture
def direct_registration(tmp_path, monkeypatch):
    """A direct-arm registration for CHORUS prepared offline into ``tmp_path``.

    The shape of notes/claudecode_direct/test_direct_arm.py's ``prepared``: the
    runtime is a script that prints its version and the login probe a
    stand-in, so no model, login or network is reached. The cohort is unique
    and one production never mints, so the planned output directories, which
    the preparer refuses to find existing and never creates, are never a
    real record's.
    """
    monkeypatch.chdir(ROOT)
    for name in direct_preparation.FORBIDDEN_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    runtime = tmp_path / "claude"
    runtime.write_text("#!/bin/sh\necho '2.1.272 (Claude Code)'\n")
    runtime.chmod(0o700)
    monkeypatch.setattr(direct_preparation, "auth_evidence", lambda executable, env: {
        "loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"})
    path = direct_preparation.build(SimpleNamespace(
        output=tmp_path / "registration", project="CHORUS", claude_executable=str(runtime), condition="generic_v9",
        render_version=17, cohort=f"test_fixture_{uuid.uuid4().hex[:8]}", label_date="2026-09-22",
        run_date="2026-09-22", deadline_seconds=21600, runaway_guard_usd="60", context_window=200000,
        max_output_tokens=64000))
    registration = json.loads(path.read_text(encoding="utf-8"))
    assert not any((ROOT / d).exists() for d in registration["generation"]["jobs"][0]["output_directories"])
    return SimpleNamespace(path=path, registration=registration, tmp_path=tmp_path)


class _ChildNotStarted(Exception):
    """Raised by the stand-in child: nothing is launched once its arguments are captured."""


def rendered_direct(direct, monkeypatch):
    """The direct child's system prompt and launch text, from ``run_direct_canary.main`` itself.

    The system prompt is assembled inline in ``main`` (the registered
    ``system.md`` followed by ``command_guidance`` of the rebuilt policy) and
    passed to the child as ``--system-prompt``; it has no builder of its own to
    call (#3740). So ``main`` runs, offline, on the registration with a review
    and launch word bound to it as ``bind_direct_launch.py`` writes them (the
    shape of notes/claudecode_direct/test_direct_arm.py's ``bind``), and
    ``execute_child`` is replaced by a stand-in that captures the argument
    vector and the instruction path and raises before any child exists. Every
    check ``main`` makes before the launch runs as written; the runtime's
    version query goes to the stand-in runtime the registration pins. The
    launch text is the instruction file ``execute_child`` streams to the child.
    """
    registration, job = direct.registration, direct.registration["generation"]["jobs"][0]
    registration_sha = direct_launcher.sha(direct.path)
    review, word = direct.tmp_path / "review_3740.json", direct.tmp_path / "word_3740.json"
    review.write_text(json.dumps({"verdict": "approve", "ci_conclusion": "success", "registration_sha256": registration_sha,
                                  "allowed_jobs": [job["id"]], "ci_head": registration["code_commit"], "ci_run_id": 1,
                                  "independent_review_sha256": "a" * 64}))
    word.write_text(json.dumps({"registration_sha256": registration_sha, "exact_response": "a synthetic launch word"}))
    captured = {}

    def child(argv, *, instruction, attempt, **_):
        captured.update(argv=list(argv), instruction=instruction, attempt=attempt)
        raise _ChildNotStarted()

    monkeypatch.setattr(direct_launcher.native, "execute_child", child)
    assert direct_launcher.main(["--registration", str(direct.path), "--review", str(review),
                                 "--launch-word", str(word), "--job", job["id"]]) == 1
    argv = captured["argv"]
    system = argv[argv.index("--system-prompt") + 1]
    started = json.loads((captured["attempt"] / "started.json").read_text(encoding="utf-8"))
    # The captured argument is the prompt the launcher attests on its receipt.
    assert started["effective_system_sha256"] == hashlib.sha256(system.encode("utf-8")).hexdigest()
    assert captured["instruction"] == job["instruction"]
    return {"system": system, "launch instruction": Path(captured["instruction"]).read_text(encoding="utf-8")}


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


@pytest.mark.parametrize("navigation", INTEGRATION_NAVIGATION)
def test_the_rendered_integration_context_quotes_nothing(staged, tmp_path, needles, navigation):
    """The integrator's instruction on clean proposals: the renderer adds nothing (#3523)."""
    rendered = rendered_integration(staged, worker_proposals(staged, tmp_path), navigation)
    context = rendered["integration context"]
    # Every worker's complete finding is inlined; the row judgments are behind the Reads.
    assert context.count(CLEAN_ISSUE) == len(staged["plan"]["workers"]) >= 2
    assert CLEAN_REASON not in context
    assert len(rendered) == 1 + len(staged["plan"]["workers"]) + len(staged["plan"]["inventory"]["values"])
    assert _found(rendered, [*needles, staged["observation"]]) == {}


def test_the_rendered_direct_arm_prompts_quote_nothing(direct_registration, monkeypatch, needles):
    """The direct arm's system prompt and launch text, assembled at run time (#3523, #3740)."""
    rendered = rendered_direct(direct_registration, monkeypatch)
    job = direct_registration.registration["generation"]["jobs"][0]
    policy = direct_launcher.build_command_policy(job, direct_registration.registration["python"],
                                                  direct_registration.registration["repository"])
    assert rendered["system"].endswith(native_command_policy.command_guidance(policy))
    # The launch text is the instruction the launcher re-renders and compares.
    assert rendered["launch instruction"] == direct_launcher.spec_for(job).instruction
    assert "# Agent runtime: Claude Code (direct)" in rendered["launch instruction"]
    assert rendered["system"].startswith((DIRECT / "system.md").read_text(encoding="utf-8"))
    assert len(rendered["system"]) > len((DIRECT / "system.md").read_text(encoding="utf-8"))
    assert _found(rendered, needles) == {}


#: A worker proposal is model output: what an echo of held-out text in one looks like.
ECHOED_PATH = "Compare data/audit_ground_truth/EXAMPLE_v1.yaml before deciding."
ECHOED_QUOTED = 'The reviewer "held out" a planted synthetic observation.'


@pytest.mark.parametrize("navigation", INTEGRATION_NAVIGATION)
@pytest.mark.parametrize("planting", ["path in a finding", "observation in a finding",
                                      "JSON-escaped observation in a finding", "observation in a row judgment"])
def test_a_proposal_that_echoes_held_out_text_is_found(staged, tmp_path, navigation, planting):
    """The sealed proposals reach the integrator verbatim, as JSON (#3523).

    A finding is inlined in the instruction and a row judgment is behind a
    Read of its canonical view; the worker artifact carries both.
    """
    observation = staged["observation"]
    needle, text = {"path in a finding": (NAMES[0], ECHOED_PATH),
                    "observation in a finding": (observation, observation),
                    "JSON-escaped observation in a finding": (ECHOED_QUOTED, ECHOED_QUOTED),
                    "observation in a row judgment": (observation, observation)}[planting]
    field = "reason" if planting.endswith("row judgment") else "issue"
    proposals = worker_proposals(staged, tmp_path, **{field: text})
    rendered = rendered_integration(staged, proposals, navigation)
    first = staged["plan"]["workers"][0]
    expected = {f"worker artifact {first['id']}": [needle]}
    if field == "issue":
        expected["integration context"] = [needle]
    else:
        expected.update({f"row view {path}": [needle] for path in first["paths"]})
    assert _found(rendered, [*NAMES, observation, ECHOED_QUOTED]) == expected
    if planting.startswith("JSON-escaped"):
        # The escaping is real: only the decoded JSON carries the quotation.
        assert matches(rendered["integration context"], [needle]) == []


def _planted_protocol(manifest, tmp_path):
    """A batch child re-reads the registered protocol file when its system is rendered."""
    protocol = tmp_path / "planted_protocol.md"
    protocol.write_text(Path(manifest["inputs"]["protocol"]).read_text() + "\n" + PLANTED + "\n")
    manifest["inputs"]["protocol"] = str(protocol)
    child = manifest["audit_batches"]["children"][0]["id"]
    return {f"{child} system": batch_registration.child_system(manifest, child)}


@pytest.mark.parametrize("builder", ["command guidance", "batch child system", "finalization report context",
                                     "evaluation instruction", "direct system prompt"])
def test_an_observation_in_a_runtime_input_reaches_the_rendered_scan(request, tmp_path, builder):
    """The gap the literal scan leaves (#3198): text no scanned source carries as a literal."""
    if builder == "direct system prompt":
        # A piece ``run_direct_canary.main`` assembles into the system prompt at run
        # time carries the observation: the prompt scanned is what main passes the
        # child, not a copy of its assembly (#3523, #3740).
        monkeypatch = request.getfixturevalue("monkeypatch")
        guidance = direct_launcher.command_guidance
        monkeypatch.setattr(direct_launcher, "command_guidance", lambda policy: guidance(policy) + PLANTED + "\n")
        rendered = {"system": rendered_direct(request.getfixturevalue("direct_registration"), monkeypatch)["system"]}
    elif builder == "command guidance":
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


#: The escapes json.dumps introduces: a quote (``\\"``) and a line break (``\\n``).
QUOTED = 'A planted "synthetic" observation that only a runtime input carries.'
ESCAPED_PLANTINGS = {
    "quoted": (QUOTED, "'" + QUOTED + "'"),
    "line-wrapped": (PLANTED, ">-\n  A planted synthetic observation\n  that only a runtime input carries."),
}


@pytest.mark.parametrize("planting", list(ESCAPED_PLANTINGS))
def test_an_observation_the_instruction_embeds_json_escaped_is_found(evaluation_instructions, tmp_path, planting):
    """The evaluation payload carries the record as a JSON string (#3569)."""
    needle, yaml_text = ESCAPED_PLANTINGS[planting]
    rendered = rendered_evaluation(evaluation_instructions, tmp_path, yaml_text)
    # The escaping is real: the raw rendered text alone does not carry the needle.
    assert matches(rendered["instruction"], [needle]) == []
    assert list(_found(rendered, [needle]).values()) == [[needle]]


def test_a_sentence_split_across_json_frames_is_found():
    """Bounded JSONL frames (as the finalization context lines are) may cut a sentence in two."""
    frames = "\n".join(json.dumps({"index": i, "text": part}) for i, part in
                       enumerate([PLANTED[:20], PLANTED[20:]], 1))
    assert matches(frames, [PLANTED]) == []
    assert _found({"frames": "Frames:\n" + frames + "\nEnd."}, [PLANTED]) == {"frames": [PLANTED]}


def test_json_nested_in_a_json_string_is_decoded_too():
    inner = json.dumps({"evidence": QUOTED})
    outer = "Payload:\n" + json.dumps({"complete_utf8_text": inner}, indent=2) + "\n"
    assert matches(outer, [QUOTED]) == []
    assert _found({"outer": outer}, [QUOTED]) == {"outer": [QUOTED]}
