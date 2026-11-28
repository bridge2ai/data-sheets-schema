#!/usr/bin/env python3
"""Build frozen root-scope v6 assets for issues 6358 and 6360, 2026-11-25.

Inputs: PR 6340 source commit and the accepted release-series data commit.
Outputs: exact-passage overrides, schemas, fifteen scope declarations and note.
Use --check to verify exact reproduction without changing any file.
This helper never starts a scorer, reads credentials or edits generated data.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import jsonschema


BASE = "483bed03b14a4c70d6e68dad6679631350a12b72"
FROZEN = "26b74b67e52b9b4fe7091ea45a0e86f81c6ef231"
DATA = "0a1bb84d1449edc27822fd76ffcfd1df7e913cd9"
INSTRUMENT = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
SOURCE_SHA256 = {
    "rubric10": "c817aa5fefd91552be68016818c8a87ab91b8798ac96666d975bc61af32c7fb3",
    "rubric20": "35de3a37264e80f48e6e037fed42b6cc586152058d4da6c08bad93b8096f588b",
}
COMPOSED_SHA256 = {
    "rubric10": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    "rubric20": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
}
REASON = (
    "The owner selected the complete submitted datasheet as the common comparison "
    "unit for every record of release series 2026-11-25c. Component entries remain "
    "part of that unmodified record; this declaration does not assert identical "
    "underlying release coverage or infer applicability predicates."
)
ROOT_RULE = """The independent scope-context file is required for this instrument. Its closed
keys are policy, input_sha256 and reason; policy must be root_dataset_v1 and
input_sha256 must bind the original record bytes. Never create, alter, infer or
copy this declaration from your assessment. Preserve the supplied scope file
and pass it to the validator with --scope-context. Missing, malformed, stale or
contradictory declarations refuse scoring. DatasetCollection and
CoreDatasetCollection declarations contradict this root-dataset instrument.
Every resource child must remain structurally valid, even though it is not a
separate scoring unit. Do not alter or add fields to the original input.

Score exactly the complete unwrapped submitted datasheet at path #, including
when it lists component datasets. Do not substitute a child or add separate
child scores. Fields retain their actual locations: do not copy a component's
values into its parent, or treat one sibling as another's missing evidence.
Rubric10 sub-elements also carry their source item_id (for example E1.1).
Each item includes applicable, applicability_status (applicable, unknown or
not_applicable), applicability_evidence, and exactly one unit_scores row at #.
The item score equals its sole applicable unit score. Preserve the original
score domains and applicability denominators. For N/A items, its unit score
is null. The result's aggregation policy remains single_dataset, with the
sole root unit and collection_metadata_inherited: false in evaluation_scope.
Also record selection_policy: root_dataset_v1 in evaluation_scope and the
SHA256 of the exact independent scope-context file as scope_context_sha256 in
metadata. This selection policy is distinct from the aggregation policy.

This is instrument 2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6.
Publish beneath data/evaluation_llm/RUBRIC_semantic/label_aware/ followed by
that instrument id. The input identity d4d_file is repository-relative.
Published provenance must contain no absolute local filesystem paths. The
controller records each session log path relative to its run directory and
retains the log SHA256. Do not include local home, checkout or run-directory
paths in any output field. Raw process evidence is retained separately.
"""
RELATIVE_PATH = r"^(?!/|\\|[A-Za-z]:)(?!.*(?:^|[/\\])\.\.(?:[/\\]|$)).+$"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    return (encoded.replace(chr(64), "\\u0040") + "\n").encode()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"expected one source fragment: {old[:70]!r}")
    return text.replace(old, new, 1)


def render_overrides(raw, family, frozen):
    if sha(raw) != SOURCE_SHA256[family] or sha(frozen) != COMPOSED_SHA256[family]:
        raise ValueError("definition source or frozen composed bytes differ")
    text = raw.decode()
    original_rules = text[text.index("## Your Task"):text.index("## Output Format")]
    replacements = []

    def replace(original, replacement):
        nonlocal text
        if raw.decode().count(original) != 1:
            raise ValueError("override original is not unique in the frozen source")
        text = replace_once(text, original, replacement)
        replacements.append({"original": original, "replacement": replacement})

    replace(f"name: d4d-{family}-semantic\n", f"name: d4d-{family}-semantic-v6\n")
    replace("model: claude-opus-5\n", "model: gpt-6-astra\n")
    replace("## General context instrument v3\n", "## Independent root-scope instrument v6\n")
    replace('this instrument; never replace earlier scores. Emit version "3.0".',
            'this instrument; never replace earlier scores. Emit version "6.0".')
    replace('"version": "3.0",', '"version": "6.0",')
    start = text.index("An explicit Dataset or CoreDataset declaration")
    end = text.index("\nKeep fixed and adjusted denominators", start)
    replace(text[start:end], ROOT_RULE)
    replace("## Structured evidence and issue links (version 3)",
            "## Structured evidence and issue links (frozen v3 authority)")
    replace("new version 3 outputs use", "new version 6 outputs use")
    replace('"evaluation_scope": {\n    "policy": "single_dataset",',
            '"evaluation_scope": {\n    "selection_policy": "root_dataset_v1",\n    "policy": "single_dataset",')
    replace('"metadata": {\n    "instrument_sha256": "<sha256 of .claude/agents/' + f'd4d-{family}-semantic.md, this file>",',
            '"metadata": {\n    "scope_context_sha256": "<sha256 of the exact caller-supplied scope-context file>",\n'
            '    "instrument_sha256": "<sha256 of .claude/agents/' + f'd4d-{family}-semantic-v6.md, this file>",')
    command = ("poetry run python scripts/validate_evaluation_schema.py --file OUTPUT_PATH "
               f"--input ORIGINAL_D4D_PATH --agent-definition .claude/agents/d4d-{family}-semantic.md "
               f"--rubric {family}-semantic")
    replace(command, command.replace(f"d4d-{family}-semantic.md", f"d4d-{family}-semantic-v6.md")
            + " --semantic-version 6.0 --scope-context ORIGINAL_SCOPE_CONTEXT_PATH")
    replace("context shown below and the one-line input",
            "applicability context shown below, an independently supplied root scope, and the one-line input")
    if text[text.index("## Your Task"):text.index("## Output Format")] != original_rules:
        raise ValueError("rubric item criteria changed")
    if family == "rubric20":
        # Minimal neutral contexts distinguish every frozen notation change.
        for fragment in ("questions " + chr(64) + "5 each", "pass/fail " + chr(64) + "1 each",
                         "(4 numeric " + chr(64) + "5 each + Q5 pass/fail)",
                         "(4 numeric " + chr(64) + "5 each + Q6 pass/fail)",
                         "(5 numeric " + chr(64) + "5 each)",
                         "(4 numeric " + chr(64) + "5 each + Q16 pass/fail)"):
            replace(fragment, fragment.replace(chr(64), "at "))
    if text.encode() != frozen:
        raise ValueError("composition differs from the frozen reviewed definition")
    return json_bytes({"version": "root_scope_definition_overrides_v1", "rubric": family,
                       "replacements": replacements})


def root_rows(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "unit_scores":
                value.update(minItems=1, maxItems=1)
                value.setdefault("items", {}).setdefault("properties", {})["path"] = {"const": "#"}
            root_rows(value)
    elif isinstance(node, list):
        for item in node:
            root_rows(item)


def render_schema(raw, family):
    schema = json.loads(raw)
    original_score = copy.deepcopy(schema["properties"]["overall_score"])
    schema["$id"] = f"https://bridge2ai.github.io/data-sheets-schema/evaluation/{family}-semantic-v6.schema.json"
    schema["title"] += " — Root Scope Version 6"
    schema["description"] += "; independently declared whole-datasheet root scope"
    schema["properties"]["version"] = {"type": "string", "const": "6.0"}
    schema["properties"]["d4d_file"]["pattern"] = RELATIVE_PATH
    for clause in schema["allOf"]:
        clause["if"]["properties"]["version"] = {"const": "6.0"}
    scope = schema["properties"]["evaluation_scope"]
    scope["required"].append("selection_policy")
    scope["properties"]["selection_policy"] = {"const": "root_dataset_v1"}
    scope["properties"]["policy"] = {"const": "single_dataset"}
    scope["properties"]["units"]["maxItems"] = 1
    scope["properties"]["units"]["items"]["properties"]["path"] = {"const": "#"}
    metadata = schema["properties"]["metadata"]
    metadata["required"] = ["scope_context_sha256"]
    metadata["properties"]["scope_context_sha256"] = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    schema["properties"]["evaluation_model"] = {
        "type": "object",
        "properties": {"session_logs": {
            "type": "array", "items": {"type": "object", "required": ["path", "sha256"],
                "properties": {"path": {"type": "string", "pattern": RELATIVE_PATH},
                               "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}}}}},
    }
    root_rows(schema)
    if schema["properties"]["overall_score"] != original_score:
        raise ValueError("score totals or denominators changed")
    jsonschema.Draft7Validator.check_schema(schema)
    return json_bytes(schema)


def schema_controls(raw):
    schema = json.loads(raw)
    root = {"policy": "single_dataset", "selection_policy": "root_dataset_v1",
            "units": [{"path": "#", "id": "example:dataset"}],
            "collection_metadata_inherited": False}
    scope_validator = jsonschema.Draft7Validator(schema["properties"]["evaluation_scope"])
    scope_validator.validate(root)
    cases = []
    altered = copy.deepcopy(root)
    altered.pop("selection_policy")
    cases.append(("missing_selection", altered))
    altered = copy.deepcopy(root)
    altered["policy"] = "minimum_per_item_across_all_resource_datasets_v1"
    cases.append(("collection_policy", altered))
    altered = copy.deepcopy(root)
    altered["units"][0]["path"] = "#/resources/0"
    cases.append(("child_unit", altered))
    altered = copy.deepcopy(root)
    altered["units"].append(copy.deepcopy(altered["units"][0]))
    cases.append(("extra_root_unit", altered))
    for name, altered in cases:
        if scope_validator.is_valid(altered):
            raise ValueError(f"schema accepts {name}")
    metadata = jsonschema.Draft7Validator(schema["properties"]["metadata"])
    metadata.validate({"scope_context_sha256": "1" * 64})
    if metadata.is_valid({}) or metadata.is_valid({"scope_context_sha256": "A" * 64}):
        raise ValueError("schema accepts missing or malformed scope hash")
    path_schema = schema["properties"]["d4d_file"]
    paths = jsonschema.Draft7Validator(path_schema)
    paths.validate("data/d4d_concatenated/method/label/Toy_d4d.yaml")
    log_schema = schema["properties"]["evaluation_model"]["properties"]["session_logs"]["items"]["properties"]["path"]
    logs = jsonschema.Draft7Validator(log_schema)
    logs.validate("codex-home/sessions/rollout.jsonl")
    for path in ("/Users/example/run/file", "/home/example/file", "C:\\Users\\example\\file",
                 "../file", "data/../file", "data\\..\\file"):
        if paths.is_valid(path) or logs.is_valid(path):
            raise ValueError(f"schema accepts nonrelative artifact path: {path}")
    return {"valid_root_and_hash": True, "scope_refusals": [name for name, _ in cases],
            "missing_or_malformed_hash_refused": True, "relative_artifact_paths_checked": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-registration", action="store_true",
                        help="replace only the note frozen in the first root-scope candidate")
    args = parser.parse_args()
    root = args.repo_root.resolve()

    def git(*argv):
        return subprocess.run(["git", "-C", str(root), *argv], check=True, capture_output=True).stdout

    outputs = {}
    compositions = {}
    for family in ("rubric10", "rubric20"):
        source = f".claude/agents/d4d-{family}-semantic.md"
        frozen = git("show", f"{FROZEN}:.claude/agents/d4d-{family}-semantic-v6.md")
        override_path = f"data/rubric/root_scope_v6/{family}_definition_overrides.json"
        outputs[override_path] = render_overrides(git("show", f"{BASE}:{source}"), family, frozen)
        compositions[family] = {"source": source, "source_sha256": SOURCE_SHA256[family],
                                "override": override_path, "override_sha256": sha(outputs[override_path]),
                                "composed_sha256": COMPOSED_SHA256[family]}
        source = f"src/download/prompts/{family}_semantic_schema.json"
        outputs[f"src/download/prompts/{family}_semantic_v6_schema.json"] = render_schema(git("show", f"{BASE}:{source}"), family)

    paths = git("ls-tree", "-r", "--name-only", DATA, "data/d4d_concatenated/claudecode_release").decode().splitlines()
    paths = [path for path in paths if "/2026-11-25c_" in path and path.endswith("_d4d.yaml")]
    if len(paths) != 15:
        raise ValueError("accepted series must contain exactly fifteen records")
    rows = []
    for path in paths:
        raw = git("show", f"{DATA}:{path}")
        if (root / path).read_bytes() != raw:
            raise ValueError(f"working record differs from accepted data commit: {path}")
        label = Path(path).parent.name
        project = Path(path).name.removesuffix("_d4d.yaml")
        destination = f"data/evaluation_scope/2026-11-25c/{label}/{project}.scope.json"
        outputs[destination] = json_bytes({"policy": "root_dataset_v1", "input_sha256": sha(raw), "reason": REASON})
        rows.append((path, sha(raw), destination, sha(outputs[destination])))

    lines = [
        "# Root-scope Codex semantic instrument, 2026-11-25", "",
        f"Instrument: `{INSTRUMENT}`. Semantic version: `6.0`.", "",
        "Issues 6358 and 6360. The owner chose New mode for all 15 records of the",
        "accepted release series. This registration defines the new measurement;",
        "the build assignment authorizes offline checks only. Live canaries and",
        "subsequent scoring need separate owner authorization.", "",
        f"Base source: `{BASE}`. Accepted data: `{DATA}`.", "",
        "The evaluator is Codex with gpt-6-astra, ultra reasoning and requested fast",
        "service tier. Each invocation evaluates one original record with one rubric",
        "in a fresh isolated working directory. The controller retains observed",
        "session identity; it does not replace scores or repair their evidence.", "",
        "The independently supplied scope file has exactly policy, input_sha256 and",
        "reason. Selection is root_dataset_v1, bound to the original file bytes.",
        "Missing, stale, malformed or contradictory scope declarations refuse.",
        "An explicit DatasetCollection or CoreDatasetCollection contradicts this",
        "selection. Every resource child remains structurally validated. No project",
        "name decides selection, and no generated record gains a class declaration.", "",
        "The result uses aggregation policy single_dataset and exactly one unit at #.",
        "evaluation_scope also records selection_policy: root_dataset_v1; metadata",
        "records the exact caller file's scope_context_sha256. Applicability context",
        "and context_digest retain their existing meanings. Rubric items, score",
        "domains, denominators and frozen v3 evidence-name authority are unchanged.", "",
        "The existing v3 instrument and versions 4 and 5 retain their own resources",
        "and interpretation. Do not pool this instrument with legacy collection",
        "scores or another model/runtime measurement. Uniform root units do not",
        "assert that all records describe identical underlying release coverage.", "",
        "Issue 6360: published d4d_file is repository-relative; session log paths",
        "are relative to the run directory and retain their SHA256 values. Other",
        "absolute local paths must not enter the published object. The raw model",
        "response and private runtime evidence stay separate. Relativisation happens",
        "before exact-file validation and byte-bound publication, never afterward.", "",
        "New outputs are under:", "",
        f"`data/evaluation_llm/RUBRIC_semantic/label_aware/{INSTRUMENT}/PROJECT_LABEL_evaluation.json`", "",
        "Definitions are composed at plan time from the unchanged pinned v3 source",
        "and a pinned JSON list of exact original passages and replacements. Each",
        "original passage must occur exactly once at its replacement step; source,",
        "override and final composed hashes are checked. No new selectable agent",
        "file is registered under .claude/agents/. The model receives the exact",
        f"reviewed v6 definition bytes frozen at `{FROZEN}`.",
        "This revision changes provenance storage only. Its historical validation",
        "example remains byte-identical; the scorer supplies the actual captured",
        "composed definition to its validator instead of that example path.", "",
        "The source-definition SHA256, override-file SHA256 and composed-definition",
        "SHA256 are recorded together in each plan, prompt descriptor and receipt.",
        "The composed SHA256 remains metadata.instrument_sha256 in the evaluation.", "",
        "Versioned assets are reproduced by scripts/adhoc/prepare_root_scope_assets_20261125.py.",
        "Use its --check mode for a read-only exact-byte check. Its default mode",
        "creates missing assets and preserves byte-identical ones. The explicit",
        "--refresh-registration option replaces only this note's frozen first-pass",
        "bytes. Original sources and reviewed definitions are read from the pinned",
        "commits. The tables below are generated from those inputs.", "",
        "| Definition | Source SHA256 | Override SHA256 | Composed SHA256 |",
        "| --- | --- | --- | --- |",
    ]
    for family, item in compositions.items():
        lines.append(f"| {family} | {item['source_sha256']} | {item['override_sha256']} | {item['composed_sha256']} |")
    lines.extend(["",
        "| Registered asset | SHA256 |", "| --- | --- |",
    ])
    for path, raw in sorted(outputs.items()):
        if not path.startswith("data/evaluation_scope/"):
            lines.append(f"| {path} | {sha(raw)} |")
    for path in ("data/rubric/rubric10.txt", "data/rubric/rubric20.txt", "data/rubric/semantic_evidence_authority_v3.json"):
        lines.append(f"| {path} | {sha(git('show', BASE + ':' + path))} |")
    lines.extend(["", "| Original record | Input SHA256 | Scope file | Scope SHA256 |", "| --- | --- | --- | --- |"])
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    outputs["notes/root_scope_instrument_20261125.md"] = ("\n".join(lines) + "\n").encode()
    checks = {family: schema_controls(outputs[f"src/download/prompts/{family}_semantic_v6_schema.json"])
              for family in ("rubric10", "rubric20")}
    writes = []
    for path, raw in outputs.items():
        if chr(64).encode() in raw:
            raise ValueError(f"unexpected prohibited character: {path}")
        target = root / path
        if args.check:
            if not target.is_file() or target.read_bytes() != raw:
                raise ValueError(f"asset differs: {path}")
        elif target.exists():
            if target.read_bytes() == raw:
                continue
            if (path != "notes/root_scope_instrument_20261125.md" or not args.refresh_registration
                    or target.read_bytes() != git("show", f"{FROZEN}:{path}")):
                raise FileExistsError(target)
            writes.append((path, raw, "wb"))
        else:
            writes.append((path, raw, "xb"))
    if not args.check:
        for path, raw, mode in writes:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open(mode) as handle:
                handle.write(raw)
    print(json.dumps({"mode": "CHECK" if args.check else "BUILD", "instrument": INSTRUMENT,
                      "schema_controls": checks,
                      "definition_provenance": compositions,
                      "scope_declarations": len(rows), "assets": {path: sha(raw) for path, raw in sorted(outputs.items())}}, indent=2))


if __name__ == "__main__":
    main()
