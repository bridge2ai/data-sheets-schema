#!/usr/bin/env python3
"""
Validate D4D evaluation JSON files against their schemas.

This ensures evaluations conform to the standardized schema, which in turn
ensures HTML renderers can reliably parse the output.
"""
import json
import re as _re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("ERROR: jsonschema package not installed")
    print("Install with: pip install jsonschema")
    sys.exit(1)


def load_schema(schema_path: Path) -> Dict:
    """Load JSON Schema file."""
    with open(schema_path, 'r') as f:
        return json.load(f)


def load_evaluation(eval_path: Path) -> Dict:
    """Load evaluation JSON file."""
    with open(eval_path, 'r') as f:
        return json.load(f)


#: Top-level keys of the shape that preceded the current agent contract.
#: rubric10 evaluations recorded before 2026 report `summary_scores` and
#: `element_scores`; the agents have instructed `overall_score` and `elements`
#: since. Such a record is not wrong, it is a different vintage — reporting it
#: as invalid buries the records that really are.
SUPERSEDED_SHAPE_KEYS = ("summary_scores", "element_scores")


def classify(eval_data: Dict, schema: Dict) -> Tuple[str, List[str]]:
    """Validate, distinguishing a superseded shape from a wrong value.

    Returns `("valid" | "superseded" | "invalid", errors)`.

    The distinction is the point. All 28 recorded evaluations failed before the
    schemas were brought up to the agents (#323), and "Invalid: 28" said nothing
    about which were merely old. Of the 20 that still fail, 12 predate the
    contract and 8 report `max_points: 84` — a maximum the rubric has never had
    (#314). Only the second kind is a defect in a record.
    """
    errors = []
    try:
        validate(instance=eval_data, schema=schema)
        return "valid", []
    except ValidationError as e:
        errors.append(f"Validation error: {e.message}")
        errors.append(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        if e.schema_path:
            errors.append(f"  Schema path: {' -> '.join(str(p) for p in e.schema_path)}")
        if any(k in eval_data for k in SUPERSEDED_SHAPE_KEYS):
            return "superseded", errors
        return "invalid", errors


def validate_evaluation(eval_data: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    """Back-compatible wrapper: superseded records are not valid."""
    status, errors = classify(eval_data, schema)
    return status == "valid", errors


#: A directory whose name marks its contents as kept evidence rather than a
#: live artifact: an archive, a superseded set, or a dated snapshot of one
#: arm's scores. An invalid record in one of these is what an older
#: instrument produced and must not be rewritten to satisfy today's schema,
#: so it is reported and does not fail the run.
KEPT_DIR = _re.compile(r"^(?:_archive|superseded)|^\d{4}-\d{2}-\d{2}(?:[_-]|$)")


def is_kept(path: Path, base: Path) -> bool:
    """Is any directory between `base` and `path` an archive marker?"""
    return any(KEPT_DIR.match(part) for part in path.relative_to(base).parts[:-1])


def discover(base: Path) -> List[Path]:
    """Every evaluation JSON under `base`, at any depth.

    The loop was `{rubric}_semantic/concatenated/*.json` — one directory per
    rubric, one level deep (#833). That reached 28 of the 204 semantic
    artifacts on disk: not `label_aware/`, which is where every evaluation
    since 2026-08 lives and which the cross-arm table reads, not the dated
    per-arm subdirectories beside it, and not the archives. The rubric a file
    declares decides which schema it is judged against, so the directory does
    not have to.
    """
    return sorted(base.rglob("*_evaluation.json"))


def main(eval_base: Path | None = None, schema_dir: Path | None = None) -> int:
    """Validate every evaluation JSON under `data/evaluation_llm`.

    The two roots are arguments so that the exit code — the thing #833 asked
    for, and the thing four tests of the helpers did not reach — can be
    exercised end to end over a tree built for the purpose.
    """
    base_dir = Path(__file__).parent.parent
    schema_dir = schema_dir or base_dir / "src" / "download" / "prompts"
    eval_base = eval_base or base_dir / "data" / "evaluation_llm"

    schemas = {
        "rubric10-semantic": load_schema(schema_dir / "rubric10_semantic_schema.json"),
        "rubric20-semantic": load_schema(schema_dir / "rubric20_semantic_schema.json"),
    }

    eval_files = discover(eval_base)
    if not eval_files:
        print(f"No evaluation files found in {eval_base}")
        return 1

    print(f"Found {len(eval_files)} evaluation file(s) under {eval_base}\n")

    counts = {("live", k): 0 for k in ("valid", "superseded", "invalid", "unreadable")}
    counts.update({("kept", k): 0 for k in ("valid", "superseded", "invalid", "unreadable")})
    no_schema: Dict[str, int] = {}
    live_invalid: List[Tuple[Path, List[str]]] = []
    kept_invalid: List[Tuple[Path, List[str]]] = []

    for eval_file in eval_files:
        where = "kept" if is_kept(eval_file, eval_base) else "live"
        shown = eval_file.relative_to(eval_base)
        try:
            eval_data = load_evaluation(eval_file)
        except Exception as e:
            print(f"❌ {shown}: failed to load: {e}")
            counts[(where, "unreadable")] += 1
            continue

        rubric = eval_data.get("rubric", "unknown")
        if rubric not in schemas:
            # Named and counted, not skipped in silence: the presence-style
            # rubric10/rubric20 outputs have no schema in this repository, and
            # a reader of the summary should see that they were not judged.
            no_schema[str(rubric)] = no_schema.get(str(rubric), 0) + 1
            continue

        status, errors = classify(eval_data, schemas[rubric])
        counts[(where, status)] += 1
        if status == "invalid":
            (kept_invalid if where == "kept" else live_invalid).append((shown, errors))
        elif status == "superseded":
            print(f"🕐 {shown}: superseded shape — {errors[0]}")

    for label, rows in (("live", live_invalid), ("kept as evidence", kept_invalid)):
        for shown, errors in rows:
            print(f"❌ {shown} ({label}):")
            for error in errors:
                print(f"     {error}")

    print()
    print("=" * 60)
    print("SUMMARY (judged against a schema):")
    for where in ("live", "kept"):
        row = {k: counts[(where, k)] for k in ("valid", "superseded", "invalid", "unreadable")}
        print(f"  {where:5}  valid {row['valid']:4}  superseded {row['superseded']:3}  "
              f"invalid {row['invalid']:3}  unreadable {row['unreadable']:3}")
    if no_schema:
        print("  no schema in this repository, not judged: "
              + ", ".join(f"{k} {v}" for k, v in sorted(no_schema.items())))
    print("=" * 60)

    # A superseded record is historical output of a contract that no longer
    # applies, and one kept under an archive marker is evidence of what an
    # older instrument produced: reported, never rewritten to pass. Only a
    # live invalid artifact fails the run.
    return 0 if not live_invalid and not counts[("live", "unreadable")] else 1


if __name__ == "__main__":
    sys.exit(main())
