"""Held-out audit ground truth reaches no instruction and no registered input (#2921).

The observations score an audit only while the audit never saw them
(notes/native_audit_continuation_plan_2026-09-18.md). The native file policy is
an instruction-conformance check, not a filesystem sandbox, so the guard is
that nothing a generation or audit model is given names the ground-truth
directory or quotes an observation. These scans cover:

- the condition prompts, playbooks, agent definitions and assistant instructions;
- the matched arms' launch prompts and rubric system prompts, and every other
  directory under notes/ named ``prompts`` or ``initial_requests``: the rendered
  request bodies a registration writes (``prepare_registration.py``), and the
  launch prompts and request bodies of a registered run not yet executed
  (#3254). A future registration written the same way is found by its
  directory names, wherever under notes/ it lands;
- the direct and native arms' system prompts;
- the Python source under notes/ that builds model-facing text: the command
  guidance appended to both arms' system prompts, the audit system prompts and
  batch framing, the finalization and evaluation instructions, context recovery;
- the rendered audit-batch contexts and output contracts;
- the registered native inputs;
- every registration record under notes/, whose inputs may not
  name the directory;
- every file under src/ other than the instrument itself.

Each file is read as text, and a Python, JSON or YAML file also as the strings
it decodes to, so a quotation split across implicitly concatenated literals,
or written with escapes (``\\'``, ``\\"``, ``\\u2013``, YAML's ``''``), is
still found (#3175).

The files under notes/ are pinned: they are read here and never edited. A
committed ground-truth file that does not load, at any depth of the directory,
fails here too, and so does a file there that is neither a ground-truth file
nor the top-level README or schema (#3176). Finder's ``.DS_Store``, recognised
by its binary header, is the one other file skipped, at any depth.

Not scanned: a launch message typed at run time; a registration or a
rendered instruction written outside the repository; and one written inside
notes/ under a file name other than ``*registration*.json`` in a directory
named neither ``prompts`` nor ``initial_requests`` (the per-attempt
``prompt.txt`` files of the 2026-09-11/12 reference rescores, for example,
which predate the ground truth). Those are the operator's to keep clean. Not found: an observation paraphrased, or assembled
at run time from pieces that are not string literals in the scanned source.
"""
import ast
import json
from pathlib import Path
import sys

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
#: Directory names under notes/ that hold rendered model-facing text: launch
#: prompts, and the literal API request bodies prepare_registration.py writes
#: (#3254). Found by name, so a new registration's output directory is too.
RENDERED_INSTRUCTION_DIRS = ("prompts", "initial_requests")
#: The rendered instructions #3254 found unscanned; each must stay in the scanned set.
RENDERED_UNDER_NOTES = (
    f"{MATCHED}/initial_requests",
    f"{MATCHED}/drafts/five_study_sources_pending_unexecuted/initial_requests",
    f"{MATCHED}/drafts/five_study_sources_pending_unexecuted/prompts",
)
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
#: Relative to the directory: the top-level README and schema only (#3176).
NOT_GROUND_TRUTH = {Path("README.md"), Path(SCHEMA_NAME)}
FINDER_HEADER = b"\x00\x00\x00\x01Bud1"


def _finder_metadata(path):
    """A ``.DS_Store`` in Finder's binary format; one holding anything else is not skipped."""
    if path.name != ".DS_Store":
        return False
    with path.open("rb") as stream:
        return stream.read(len(FINDER_HEADER)) == FINDER_HEADER


def committed_observations(directory=GROUND_TRUTH):
    """Every observation in every ground-truth file under ``directory``, at any depth.

    A file that does not load raises, and so does any file that is neither a
    ground-truth file nor the top-level README or schema: under another name,
    or as a README or schema one level down, it would be neither loaded nor
    scanned for (#3103, #3176). Only Finder's own ``.DS_Store`` is skipped
    at any depth.
    """
    found = []
    for path in sorted(directory.rglob("*")):
        if (not path.is_file() or path.relative_to(directory) in NOT_GROUND_TRUTH
                or _finder_metadata(path)):
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


def rendered_instruction_trees(notes=ROOT / "notes"):
    """Every directory under ``notes`` named ``prompts`` or ``initial_requests`` (#3254)."""
    return sorted(p for p in notes.rglob("*")
                  if p.is_dir() and p.name in RENDERED_INSTRUCTION_DIRS and "__pycache__" not in p.parts)


def instruction_surfaces():
    rendered = [str(p.relative_to(ROOT)) for p in rendered_instruction_trees()]
    return list(dict.fromkeys(files_under(*INSTRUCTION_TREES, *INSTRUCTION_FILES, *rendered)
                              + control_code(*CONTROL_CODE_TREES)))


def registration_records():
    """Every registration record under notes/ (``*registration*.json``)."""
    return sorted(p for p in (ROOT / "notes").rglob("*registration*.json") if p.is_file())


def registered_inputs():
    return [ROOT / p for p in (*SCHEMAS, *AGENT_PLAYBOOKS)] + files_under(*REGISTERED_INPUT_TREES,
                                                                          *REGISTERED_INPUT_FILES)


def src_files():
    """Every file under src/ other than the instrument."""
    return [p for p in files_under("src") if p.resolve() != INSTRUMENT.resolve()]


def _python_strings(text):
    """The file's string constants in source order, or None where it does not parse.

    ``ast`` joins implicitly concatenated literals and resolves escapes, which
    the raw text keeps as ``" "`` seams and ``\\'`` (#3175). f-string pieces are
    constants too.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    constants = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    return [node.value for node in sorted(constants, key=lambda n: (n.lineno, n.col_offset))]


def _strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings_in(key)
            yield from _strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings_in(item)


def decoded_strings(path, text):
    """The strings a .py, .json, .yaml or .yml file decodes to; None for any other
    file, or one that does not decode."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".py":
            return _python_strings(text)
        if suffix == ".json":
            return list(_strings_in(json.loads(text)))
        if suffix in (".yaml", ".yml"):
            loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
            return [s for document in yaml.load_all(text, Loader=loader) for s in _strings_in(document)]
    except (ValueError, yaml.YAMLError):
        return None
    return None


def views(path):
    """The texts a scan reads for ``path``: the file as text and, where it
    decodes, its strings joined with nothing (a word split across ``+``) and
    with newlines (a sentence split across list items)."""
    text = path.read_bytes().decode("utf-8", errors="replace")
    strings = decoded_strings(path, text)
    return [text] if strings is None else [text, "".join(strings), "\n".join(strings)]


def leaks(paths, needles, root=ROOT):
    out = {}
    for path in paths:
        found = sorted({needle for view in views(path) for needle in matches(view, needles)},
                       key=needles.index)
        if found:
            out[str(path.relative_to(root))] = found
    return out


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


def test_the_rendered_instructions_under_notes_are_scanned():
    """The rendered request bodies and the pending run's launch prompts (#3254)."""
    scanned = {p.resolve() for p in instruction_surfaces()}
    for relative in RENDERED_UNDER_NOTES:
        files = files_under(relative)
        assert files, relative
        assert [str(f.relative_to(ROOT)) for f in files if f.resolve() not in scanned] == []


def test_a_new_registrations_prompts_and_requests_are_found_by_name(tmp_path):
    """A registration written into a new output directory is scanned without an edit here."""
    run = tmp_path / "some_new_run_2026-10-01" / "drafts" / "pending"
    for name in (*RENDERED_INSTRUCTION_DIRS, "reviews"):
        (run / name).mkdir(parents=True)
    (tmp_path / "__pycache__" / "prompts").mkdir(parents=True)
    assert [p.relative_to(tmp_path) for p in rendered_instruction_trees(tmp_path)] == [
        run.relative_to(tmp_path) / "initial_requests", run.relative_to(tmp_path) / "prompts"]


def test_no_instruction_file_names_the_directory_or_quotes_an_observation(needles):
    assert leaks(instruction_surfaces(), needles) == {}


def test_no_registered_native_input_does(needles):
    registered = registered_inputs()
    assert all(p.is_file() for p in registered)
    assert [p for p in registered if GROUND_TRUTH in p.resolve().parents] == []
    assert leaks(registered, needles) == {}


def test_no_registration_record_under_notes_does(needles):
    """A registration's inputs, pins and closures may not name the directory."""
    assert leaks(registration_records(), needles) == {}


def test_only_the_instrument_under_src_names_the_directory(needles):
    assert leaks(src_files(), needles) == {}
    assert leaks([INSTRUMENT], committed_observations()) == {}


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


def test_only_the_top_level_readme_and_schema_are_exempt(tmp_path):
    """A README or schema one level down is loaded or refused like any other file (#3176)."""
    nested = tmp_path / "CHORUS"
    nested.mkdir()
    (tmp_path / "README.md").write_text("Not ground truth.\n")
    (tmp_path / SCHEMA_NAME).write_text("{}\n")
    (nested / SCHEMA_NAME).write_text(_ground_truth_file("Kept under the schema's name, one level down."))
    assert committed_observations(tmp_path) == ["Kept under the schema's name, one level down."]
    (nested / "README.md").write_text(_ground_truth_file("Kept under the README's name, one level down."))
    with pytest.raises(ValueError, match=r"CHORUS/README\.md: not \.yaml.*neither loaded nor scanned"):
        committed_observations(tmp_path)


def test_finder_metadata_is_skipped_at_any_depth_and_any_other_ds_store_is_not(tmp_path):
    finder = FINDER_HEADER + bytes(28)
    (tmp_path / "sub").mkdir()
    (tmp_path / ".DS_Store").write_bytes(finder)
    (tmp_path / "sub" / ".DS_Store").write_bytes(finder)
    assert committed_observations(tmp_path) == []
    (tmp_path / "sub" / ".DS_Store").write_text(_ground_truth_file("Kept in a .DS_Store."))
    with pytest.raises(ValueError, match=r"\.DS_Store: not \.yaml.*neither loaded nor scanned"):
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


PLAIN = "A planted synthetic observation of a defect."
APOSTROPHE = "The planted record's maintainer is a synthetic observation."
QUOTED = 'A "planted" synthetic observation of a defect.'
DASHED = "A planted synthetic observation \u2013 of a defect."


@pytest.mark.parametrize("name, observation, content", [
    # The style of native_command_policy.command_guidance and batch_registration.child_system.
    ("wrapped.py", PLAIN, 'GUIDANCE = ("Audit carefully. A planted synthetic "\n'
                          '            "observation of a defect.")\n'),
    ("apostrophe.py", APOSTROPHE, "TEXT = 'The planted record\\'s maintainer is a synthetic observation.'\n"),
    ("quote.py", QUOTED, 'TEXT = "A \\"planted\\" synthetic observation of a defect."\n'),
    ("fstring.py", APOSTROPHE, "TEXT = f'The planted record\\'s maintainer is a synthetic observation. {x}'\n"),
    ("plus.py", PLAIN, 'TEXT = "A planted synth" + "etic observation of a defect."\n'),
    # ast.walk is breadth first, so " of a defect." comes out first unless sorted.
    ("nested_plus.py", PLAIN, 'TEXT = ("A planted synth" + "etic observation") + " of a defect."\n'),
    # json.dumps with its default ensure_ascii, as the registration records are written.
    ("registration.json", DASHED, json.dumps({"system": "Audit. " + DASHED})),
    ("lines.json", PLAIN, json.dumps({"system": ["A planted synthetic", "observation of a defect."]})),
    ("single.yaml", APOSTROPHE, yaml.safe_dump({"text": APOSTROPHE}, default_style="'")),
    ("double.yaml", DASHED, yaml.safe_dump({"text": DASHED}, default_style='"', allow_unicode=False)),
])
def test_an_observation_is_found_in_the_strings_a_file_decodes_to(tmp_path, name, observation, content):
    """Seams between literals and escapes hide a quotation from the raw text (#3175)."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    assert matches(content, [observation]) == []
    assert leaks([path], [*NAMES, observation], root=tmp_path) == {name: [observation]}


def test_a_file_that_does_not_decode_is_still_read_as_text(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text(f'GUIDANCE = ("{PLAIN}"\n')
    assert decoded_strings(broken, broken.read_text()) is None
    assert leaks([broken], [PLAIN], root=tmp_path) == {"broken.py": [PLAIN]}


def test_every_scanned_python_json_and_yaml_file_decodes():
    """Otherwise its decoded strings are lost and only its raw text is scanned (#3175)."""
    scanned = {p.resolve(): p for p in (*instruction_surfaces(), *registered_inputs(),
                                        *registration_records(), *src_files(), INSTRUMENT)}
    structured = [p for p in scanned.values() if p.suffix.lower() in (".py", ".json", ".yaml", ".yml")]
    if sys.version_info < (3, 12):
        # PEP 701 f-strings (src/download/claude_max_d4d_processor.py) parse only
        # from 3.12; the 3.12 lane reads the same bytes.
        structured = [p for p in structured if p.suffix != ".py"]
    assert len(structured) > 200
    undecoded = [str(p.relative_to(ROOT)) for p in structured
                 if decoded_strings(p, p.read_bytes().decode("utf-8", errors="replace")) is None]
    assert undecoded == []


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
