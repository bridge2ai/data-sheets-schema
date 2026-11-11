#!/usr/bin/env python3
"""Regenerate schema 3.2.1 artifacts for #2975 and append 3.2.1 to release_history.yaml.

Purpose:
  Materialize the 3.2.1 patch release for #2975 (FileCollection.collection_type
  scalar prose alignment) without mutating any historical 2.0.0..3.2.0 release
  entries, deleting prior staging evidence, or touching repo-local tmp/.
Inputs:
  - src/data_sheets_schema/schema/D4D_FileCollection.yaml
  - src/data_sheets_schema/schema/data_sheets_schema.yaml
  - src/data_sheets_schema/schema/D4D_Core.yaml
  - src/data_sheets_schema/schema/data_sheets_schema_core.yaml
  - CITATION.cff
  - src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl
  - notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv
Outputs:
  - src/data_sheets_schema/schema/data_sheets_schema_all.yaml
  - src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
  - src/data_sheets_schema/datamodel/data_sheets_schema.py
  - project/{jsonschema,jsonld,owl}/*
  - src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv
  - src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv
  - src/data_sheets_schema/schema/release_history.yaml (appends 3.2.1, preserving 2.0.0..3.2.0 verbatim)
Issues: #2975, #5799, #5800, #5801 (Unit G2)
Date: 2026-11-10
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "src" / "data_sheets_schema" / "schema"
RELEASE_VERSION = "3.2.1"
DECLARED_DATE = "2026-11-10"
JSONLD_CTX_KEY = "\x40context"
RELOCATED_JSONLD_CTX = "project/jsonld/data_sheets_schema.context.jsonld"

# Exact expected 3.2.0 hashes from release_history.yaml to guarantee history preservation
EXPECTED_3_2_0_HASHES = {
    "full_source_sha256": "f232e9a2c70675a1d09bf96991621101294509e4bfd14bc6624873a7773ae51c",
    "full_merged_sha256": "cf4e0992a807cbf98efbf936b02d05ef48c438c437c3d380775aea9ab69302f7",
    "core_source_sha256": "cf48f77652bcf6b937e7c0e8d78eb9472d76980aae02f03a5581e15920bfe8e8",
    "core_merged_sha256": "db4c4fa49c33ccf14d79ac5c65098d868036ad211a3036df60437b9939220700",
}

DEFAULT_SCRATCH = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g2-2975-20261110"
)
DEFAULT_BIN_DIR = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_bin_dir(raw_bin_dir: Path) -> Path:
    """Preserve logical .venv/bin path without resolving symlinks to base Miniforge (#5799)."""
    bin_dir = Path(os.path.abspath(str(raw_bin_dir)))
    if "miniforge" in str(bin_dir).lower() or bin_dir.parent.name != ".venv":
        raise RuntimeError(
            f"Refusing non-virtualenv bin directory {bin_dir!s}; pass the project .venv/bin path (#5799)"
        )
    for tool in ("python", "gen-linkml", "gen-project"):
        candidate = bin_dir / tool
        if not candidate.exists():
            raise RuntimeError(f"Required executable missing in {bin_dir!s}: {candidate!s}")
    return bin_dir


def verify_source_declarations() -> dict[str, str]:
    files = {
        "CITATION.cff": ROOT / "CITATION.cff",
        "data_sheets_schema.yaml": SCHEMA / "data_sheets_schema.yaml",
        "data_sheets_schema_core.yaml": SCHEMA / "data_sheets_schema_core.yaml",
        "D4D_Core.yaml": SCHEMA / "D4D_Core.yaml",
    }
    versions: dict[str, str] = {}
    for label, path in files.items():
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        ver = str(doc.get("version", ""))
        if ver != RELEASE_VERSION:
            raise RuntimeError(f"{label} declares version={ver!r}, expected {RELEASE_VERSION!r}")
        versions[label] = ver

    fc_doc = yaml.safe_load((SCHEMA / "D4D_FileCollection.yaml").read_text(encoding="utf-8"))
    attr = fc_doc["classes"]["FileCollection"]["attributes"]["collection_type"]
    if attr.get("range") != "FileCollectionTypeEnum":
        raise RuntimeError(f"Unexpected range on FileCollection.collection_type: {attr.get('range')!r}")
    if bool(attr.get("multivalued", False)):
        raise RuntimeError("FileCollection.collection_type must remain single-valued (not multivalued)")
    desc = " ".join(str(attr.get("description", "")).split())
    for forbidden in ("Type(s)", "may have multiple types", "both types listed"):
        if forbidden in desc:
            raise RuntimeError(f"Contradictory phrase {forbidden!r} still present in collection_type description")
    return versions


def split_release_history_preserving_prior(history_text: str) -> str:
    marker = "  - version: 3.2.1\n"
    if marker in history_text:
        prefix, _ = history_text.split(marker, 1)
    else:
        prefix = history_text
        if not prefix.endswith("\n"):
            prefix += "\n"

    parsed = yaml.safe_load(prefix)
    releases = parsed.get("releases", [])
    versions = [str(r.get("version")) for r in releases]
    if versions != ["2.0.0", "3.0.0", "3.1.0", "3.2.0"]:
        raise RuntimeError(f"Historical release sequence unexpected: {versions!r}")
    rel_320 = releases[-1]
    for key, expected in EXPECTED_3_2_0_HASHES.items():
        actual = rel_320.get(key)
        if actual != expected:
            raise RuntimeError(f"3.2.0 {key} mutated: {actual!r} != {expected!r}")
    return prefix


def compute_api_schema_digests(
    full_merged_path: Path, core_merged_path: Path
) -> dict[str, dict[str, dict[str, str]]]:
    """Compute Dataset and CoreDataset API schema digests across neutral and bridge2ai profiles (#5800)."""
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from data_sheets_schema import profiles, schema_digest

    report: dict[str, dict[str, dict[str, str]]] = {}
    for prof in (profiles.NEUTRAL, profiles.BRIDGE2AI):
        report[prof.name] = {}
        for target_cls, schema_file in (
            ("Dataset", full_merged_path),
            ("CoreDataset", core_merged_path),
        ):
            if not schema_file.exists():
                raise RuntimeError(f"Merged schema missing for digest computation: {schema_file}")
            text = schema_digest.digest_text(target_cls, schema_path=schema_file, profile=prof)
            report[prof.name][target_cls] = {
                "md5": hashlib.md5(text.encode("utf-8")).hexdigest(),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
    return report


def assert_api_digests_unchanged(
    before: dict[str, dict[str, dict[str, str]]],
    after: dict[str, dict[str, dict[str, str]]],
) -> None:
    """Refuse if any full/Core API schema digest moved between baseline and 3.2.1 (#5800)."""
    diffs: list[str] = []
    for prof_name, before_classes in before.items():
        after_classes = after.get(prof_name, {})
        for cls_name, before_hashes in before_classes.items():
            after_hashes = after_classes.get(cls_name, {})
            if before_hashes != after_hashes:
                diffs.append(
                    f"{prof_name}.{cls_name}: before={before_hashes!r} != after={after_hashes!r}"
                )
    if diffs:
        raise RuntimeError(
            "API schema_digest changed unexpectedly (#5800); refusing to write unchanged-digest release claim: "
            + "; ".join(diffs)
        )


def relocate_staged_jsonld_context(staged_jsonld: Path, staged_context: Path, target_jsonld: Path) -> str:
    """Replace only the expected staged JSON-LD context file URI with the repo-relative path (#5799)."""
    doc = json.loads(staged_jsonld.read_text(encoding="utf-8"))
    context_list = doc.get(JSONLD_CTX_KEY)
    if not isinstance(context_list, list):
        raise RuntimeError(f"{staged_jsonld} missing list {JSONLD_CTX_KEY!r}")
    expected_staged_uri = Path(os.path.abspath(str(staged_context))).as_uri()
    occurrences = sum(1 for item in context_list if item == expected_staged_uri)
    if occurrences != 1:
        raise RuntimeError(
            f"Expected exactly 1 occurrence of staged context URI {expected_staged_uri!r} "
            f"in {staged_jsonld}, found {occurrences}: {context_list!r}"
        )
    doc[JSONLD_CTX_KEY] = [
        RELOCATED_JSONLD_CTX if item == expected_staged_uri else item
        for item in context_list
    ]
    if RELOCATED_JSONLD_CTX not in doc[JSONLD_CTX_KEY] or expected_staged_uri in doc[JSONLD_CTX_KEY]:
        raise RuntimeError("Failed to verify JSON-LD context URI relocation (#5799)")
    target_jsonld.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return expected_staged_uri


def format_3_2_1_entry(hashes: dict[str, str]) -> str:
    return (
        f"  - version: {RELEASE_VERSION}\n"
        f"    declared: {DECLARED_DATE}\n"
        f"    full_source_sha256: {hashes['full_source_sha256']}\n"
        f"    full_merged_sha256: {hashes['full_merged_sha256']}\n"
        f"    core_source_sha256: {hashes['core_source_sha256']}\n"
        f"    core_merged_sha256: {hashes['core_merged_sha256']}\n"
        "    note: >-\n"
        "      Aligns FileCollection.collection_type description in\n"
        "      D4D_FileCollection.yaml with its scalar FileCollectionTypeEnum\n"
        "      declaration (#2975): each FileCollection has one collection_type\n"
        "      value, and differently classified file groups use separate\n"
        "      FileCollection entries in file_collections. Neither profile's API\n"
        "      schema_digest md5 moved. Historical schema hashes stay unchanged.\n"
    )


def run_checked(cmd: list[str], *, env: dict[str, str]) -> None:
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def execute_build(scratch_dir: Path, raw_bin_dir: Path) -> dict[str, object]:
    bin_dir = validate_bin_dir(raw_bin_dir)
    verify_source_declarations()

    history_path = SCHEMA / "release_history.yaml"
    original_history = history_path.read_text(encoding="utf-8")
    preserved_prefix = split_release_history_preserving_prior(original_history)
    prefix_sha256 = hashlib.sha256(preserved_prefix.encode("utf-8")).hexdigest()

    # #5801: Never delete or overwrite an existing staging directory or receipt file.
    stage = scratch_dir / "stage"
    receipt_path = scratch_dir / "g2_release_3_2_1_receipt.json"
    if stage.exists():
        raise FileExistsError(
            f"Staging directory already exists (preserving prior evidence per #5801): {stage}. "
            "Pass a fresh --scratch-dir for a new attempt."
        )
    if receipt_path.exists():
        raise FileExistsError(
            f"Receipt path already exists (preserving prior evidence per #5801): {receipt_path}. "
            "Pass a fresh --scratch-dir for a new attempt."
        )

    # #5800: Capture all four baseline API digests BEFORE replacing merged schemas.
    full_merged_target = SCHEMA / "data_sheets_schema_all.yaml"
    core_merged_target = SCHEMA / "data_sheets_schema_core_all.yaml"
    baseline_digests = compute_api_schema_digests(full_merged_target, core_merged_target)

    stage.mkdir(parents=True, exist_ok=False)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    python_exe = str(bin_dir / "python")
    gen_linkml = str(bin_dir / "gen-linkml")
    gen_project = str(bin_dir / "gen-project")

    # #5799: Pass repository-relative schema paths from cwd=ROOT so source_file metadata
    # in generated schemas/exports stays repository-relative for schema_sync.py.
    rel_full_source = (SCHEMA / "data_sheets_schema.yaml").relative_to(ROOT).as_posix()
    rel_core_source = (SCHEMA / "data_sheets_schema_core.yaml").relative_to(ROOT).as_posix()

    # 1. Generate merged full schema (with leading '---\n' per Makefile full-schema target)
    raw_full = stage / "data_sheets_schema_all.raw.yaml"
    staged_full = stage / "data_sheets_schema_all.yaml"
    run_checked(
        [gen_linkml, "-o", str(raw_full), "-f", "yaml", rel_full_source],
        env=env,
    )
    staged_full.write_bytes(b"---\n" + raw_full.read_bytes())

    # 2. Generate merged core schema (per Makefile gen-core-schema target)
    staged_core = stage / "data_sheets_schema_core_all.yaml"
    run_checked(
        [gen_linkml, "-o", str(staged_core), "-f", "yaml", rel_core_source],
        env=env,
    )

    # 3. Generate project artifacts (python, jsonschema, jsonld, owl) in stage dir
    project_stage = stage / "project"
    run_checked(
        [
            gen_project,
            "-I",
            "python",
            "-I",
            "jsonschema",
            "-I",
            "jsonld",
            "-I",
            "owl",
            "-d",
            str(project_stage),
            rel_full_source,
        ],
        env=env,
    )

    # 4. Copy staged merged schemas and project artifacts into worktree in timestamp order,
    # relocating the staged JSON-LD context URI (#5799).
    shutil.copy2(staged_full, full_merged_target)
    shutil.copy2(staged_core, core_merged_target)
    shutil.copy2(
        project_stage / "data_sheets_schema.py",
        ROOT / "src" / "data_sheets_schema" / "datamodel" / "data_sheets_schema.py",
    )
    relocated_from_uri: str | None = None
    for subdir in ("jsonschema", "jsonld", "owl"):
        for generated_file in sorted((project_stage / subdir).iterdir()):
            if not generated_file.is_file():
                continue
            target = ROOT / "project" / subdir / generated_file.name
            if not target.exists():
                raise RuntimeError(f"Unexpected generated project artifact target: {target}")
            if subdir == "jsonld" and generated_file.name == "data_sheets_schema.jsonld":
                staged_ctx = project_stage / "jsonld" / "data_sheets_schema.context.jsonld"
                relocated_from_uri = relocate_staged_jsonld_context(generated_file, staged_ctx, target)
            else:
                shutil.copy2(generated_file, target)

    if relocated_from_uri is None:
        raise RuntimeError("data_sheets_schema.jsonld was not processed during staging copy (#5799)")

    # 5. Regenerate comprehensive SSSOM pair and run --check on both
    skos_path = ROOT / "src" / "data_sheets_schema" / "semantic_exchange" / "d4d_rocrate_skos_alignment.ttl"
    rec_path = ROOT / "notes" / "D4D_MISSING_URI_RECOMMENDATIONS.tsv"
    sssom_comp = ROOT / "src" / "data_sheets_schema" / "semantic_exchange" / "d4d_rocrate_sssom_comprehensive.tsv"
    sssom_uri = ROOT / "src" / "data_sheets_schema" / "semantic_exchange" / "d4d_rocrate_sssom_uri_comprehensive.tsv"
    script_comp = ROOT / "src" / "semantic_exchange" / "generate_comprehensive_sssom.py"
    script_uri = ROOT / "src" / "semantic_exchange" / "generate_comprehensive_sssom_uri.py"

    for script, out_path in ((script_comp, sssom_comp), (script_uri, sssom_uri)):
        run_checked(
            [
                python_exe,
                str(script),
                "--schema",
                str(full_merged_target),
                "--skos",
                str(skos_path),
                "--recommendations",
                str(rec_path),
                "--output",
                str(out_path),
            ],
            env=env,
        )
        run_checked(
            [
                python_exe,
                str(script),
                "--check",
                "--schema",
                str(full_merged_target),
                "--skos",
                str(skos_path),
                "--recommendations",
                str(rec_path),
                "--output",
                str(out_path),
            ],
            env=env,
        )

    # 6. #5800: Compute post-build API schema digests and assert equality with baseline
    # BEFORE writing the release_history.yaml entry claiming unchanged digests.
    after_digests = compute_api_schema_digests(full_merged_target, core_merged_target)
    assert_api_digests_unchanged(baseline_digests, after_digests)

    # 7. Measure the 4 schema hashes and append 3.2.1 to release_history.yaml
    hashes = {
        "full_source_sha256": sha256_file(SCHEMA / "data_sheets_schema.yaml"),
        "full_merged_sha256": sha256_file(full_merged_target),
        "core_source_sha256": sha256_file(SCHEMA / "data_sheets_schema_core.yaml"),
        "core_merged_sha256": sha256_file(core_merged_target),
    }
    new_history = preserved_prefix + format_3_2_1_entry(hashes)
    if not new_history.startswith(preserved_prefix):
        raise RuntimeError("Historical prefix check failed before writing release_history.yaml")
    history_path.write_text(new_history, encoding="utf-8")

    # Re-verify that the prefix on disk matches byte-for-byte
    re_read = history_path.read_text(encoding="utf-8")
    re_prefix = split_release_history_preserving_prior(re_read)
    if hashlib.sha256(re_prefix.encode("utf-8")).hexdigest() != prefix_sha256:
        raise RuntimeError("Historical prefix SHA-256 changed after writing release_history.yaml")

    receipt = {
        "release": RELEASE_VERSION,
        "declared": DECLARED_DATE,
        "bin_dir": str(bin_dir),
        "relative_schema_inputs": {
            "full": rel_full_source,
            "core": rel_core_source,
        },
        "jsonld_context_relocated_from": relocated_from_uri,
        "jsonld_context_relocated_to": RELOCATED_JSONLD_CTX,
        "historical_prefix_sha256": prefix_sha256,
        "hashes": hashes,
        "baseline_api_schema_digests": baseline_digests,
        "after_api_schema_digests": after_digests,
        "api_schema_digests_unchanged": baseline_digests == after_digests,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("dry-run", "execute"),
        default="dry-run",
        help="Validate source edits and history invariants (dry-run) or execute full build (execute).",
    )
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=DEFAULT_SCRATCH,
        help="External scratch directory for staged generation outputs (must not already contain stage/).",
    )
    parser.add_argument(
        "--bin-dir",
        type=Path,
        default=Path(sys.executable).parent if Path(sys.executable).parent.parent.name == ".venv" else DEFAULT_BIN_DIR,
        help="Virtualenv bin directory containing python, gen-linkml, and gen-project (symlink preserved).",
    )
    args = parser.parse_args()

    if args.mode == "dry-run":
        bin_dir = validate_bin_dir(args.bin_dir)
        versions = verify_source_declarations()
        history_text = (SCHEMA / "release_history.yaml").read_text(encoding="utf-8")
        prefix = split_release_history_preserving_prior(history_text)
        baseline_digests = compute_api_schema_digests(
            SCHEMA / "data_sheets_schema_all.yaml",
            SCHEMA / "data_sheets_schema_core_all.yaml",
        )
        summary = {
            "mode": "dry-run",
            "root": str(ROOT),
            "bin_dir": str(bin_dir),
            "verified_versions": versions,
            "historical_prefix_sha256": hashlib.sha256(prefix.encode("utf-8")).hexdigest(),
            "current_source_hashes": {
                "full_source_sha256": sha256_file(SCHEMA / "data_sheets_schema.yaml"),
                "core_source_sha256": sha256_file(SCHEMA / "data_sheets_schema_core.yaml"),
            },
            "baseline_api_schema_digests": baseline_digests,
        }
        print(json.dumps(summary, indent=2))
        return 0

    receipt = execute_build(args.scratch_dir, args.bin_dir)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
