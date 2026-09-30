#!/usr/bin/env python
"""Offline baseline of the self_disclaimed lint over a pinned set of records (#3041).

Runs `data_sheets_schema.self_disclaimed` (#2913) over the full records under
`data/d4d_concatenated/` and writes the counts to
`notes/self_disclaimed_baseline.md`: check (a)'s flagged, guarded and
out-of-scope matches on the final records, the phase-1 snapshot to final diff
(`intermediate/{P}_full.yaml`, as `receipts.phase1_snapshot_read` selects it)
and check (b) over each coverage receipt, by method and by label. The records,
snapshots and receipts are only read; no audit is read, because the corpus
audits carry no JSON pointers (so `removal_declared` and `named_by_finding`
cannot fire here).

The note counts a pinned set, as `scripts/absence_claims_baseline.py` does
(#2919, #3045). `notes/self_disclaimed_baseline_records.yaml` names each final
record by its path under the corpus and the sha256 of its bytes, with the
snapshot and the receipt it was paired with at `--repin` and their sha256. A
record added to the corpus later is reported and not counted. A pinned file
whose bytes changed, or that is gone, makes the note stale. `--repin` selects
the corpus as it stands and rewrites both files: it is the one act that moves
the baseline to other records.

The detail tables count under one named lexicon version, `LEXICON_VERSION`.
The versions table counts the same records under every version in
`container_lexicons/`, so registering a version makes the note stale, and its
effect on the corpus is the diff of the regenerated note. Moving the detail
tables to it is a deliberate change of `LEXICON_VERSION`.

A record is parsed as `d4d review self-disclaimed` parses it: one with
duplicate mapping keys is refused and listed as unreadable (#1029). The
refusal rule is `duplicate_keys`' own; only the parser differs, libyaml's
where PyYAML has it, since the pure-Python parse of the pinned files took
about a minute.

The note is regenerated, never edited by hand. A corpus-lane test rebuilds it
from the pinned files and fails when a pinned file changed or is gone, or
when the committed bytes differ.

Usage:
    poetry run python scripts/self_disclaimed_baseline.py            # rewrite the note from the pinned records
    poetry run python scripts/self_disclaimed_baseline.py --repin    # pin the corpus as it stands, then write both files
    poetry run python scripts/self_disclaimed_baseline.py --check    # read-only: exit 1 when stale
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema import duplicate_keys  # noqa: E402
from data_sheets_schema import receipts  # noqa: E402
from data_sheets_schema import self_disclaimed as sd  # noqa: E402

CORPUS = ROOT / "data" / "d4d_concatenated"
OUT_MD = ROOT / "notes" / "self_disclaimed_baseline.md"
PINS = ROOT / "notes" / "self_disclaimed_baseline_records.yaml"
RECORD_GLOB = "*_d4d.yaml"
#: The registered lexicon version the detail tables count under.
LEXICON_VERSION = 2
#: The companions a final record is paired with, in the pins and the note.
COMPANIONS = ("snapshot", "receipt")
#: The methods #3029 (#2913 PR1) counted: its figures are this subtotal, not
#: the all-methods total (#3703).
PR1_METHODS = ("claudecode_agent", "claudecode_api")
RETAINED = "self_disclaimed_retained"
RP_RETAINED = "role_predicate_retained"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_LOADER = duplicate_keys.FAST_LOADER


class Stale(Exception):
    """The pinned set cannot be counted as pinned: a pinned file changed or is
    gone, or the pin file is missing or malformed."""


def load_record(raw: bytes) -> dict:
    """A record parsed as the CLI parses it (`evidence_assertions.load_record`),
    or ValueError: not UTF-8, not YAML, a repeated key, or not a mapping.

    The duplicate-key rule is `duplicate_keys.find_duplicate_keys` (`<<`
    merges are not duplicates; `true` and `True` are one key), run on a node
    tree libyaml composes (#3704), and the value is loaded by libyaml's safe
    loader."""
    try:
        text = raw.decode("utf-8")
        if duplicate_keys.find_duplicate_keys(text, loader=_LOADER):
            raise ValueError("artifact has duplicate YAML mapping keys; its location is ambiguous")
        value = yaml.load(text, Loader=_LOADER)   # noqa: S506 (a safe loader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(type(exc).__name__) from exc
    if not isinstance(value, dict):
        raise ValueError("artifact must be a YAML mapping")
    return value


def versions() -> list[int]:
    """Every lexicon version in `container_lexicons/`, oldest first."""
    found = (re.fullmatch(r"self_disclaimed_v(\d+)\.yaml", p.name) for p in sd.LEXICON_DIR.iterdir())
    return sorted(int(m.group(1)) for m in found if m)


# ------------------------------------------------------------------ the pinned set
def record_paths(corpus: Path) -> list[Path]:
    """The full records: `*_d4d.yaml` in each method directory that does not
    end `_core`, and one label directory below it, sorted by path."""
    found: list[Path] = []
    for method in sorted(p for p in corpus.iterdir() if p.is_dir() and not p.name.endswith("_core")):
        found.extend(method.glob(RECORD_GLOB))
        found.extend(method.glob(f"*/{RECORD_GLOB}"))
    return sorted(found, key=lambda p: p.relative_to(corpus).as_posix())


def companions(corpus: Path, final: Path) -> dict[str, Path | None]:
    """The phase-1 snapshot and the coverage receipt of a labelled final
    record, in `{method}_core/{label}/`; none for a record with no label.

    The snapshot is the last of `intermediate/{P}_full.yaml` and
    `{P}_full_N.yaml` by N, the file-name rule `receipts.phase1_snapshot_read`
    falls back to. Its attested route reads a provenance record's paths
    relative to the working directory, so it is not used here; on the corpus
    as pinned the two select the same 87 files.
    """
    rel = final.relative_to(corpus)
    out: dict[str, Path | None] = dict.fromkeys(COMPANIONS)
    if len(rel.parts) != 3:
        return out
    project = final.name[: -len("_d4d.yaml")]
    core = corpus / f"{rel.parts[0]}_core" / rel.parts[1]
    receipt = core / f"{project}_coverage_receipt.yaml"
    if receipt.is_file():
        out["receipt"] = receipt
    stem = f"{project}_full"
    numbered = [p for p in (core / "intermediate").glob(f"{stem}_[0-9]*.yaml")
                if re.fullmatch(rf"{re.escape(stem)}_\d+\.yaml", p.name)]
    snaps = sorted((core / "intermediate").glob(f"{stem}.yaml")) + sorted(
        numbered, key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    if snaps:
        out["snapshot"] = snaps[-1]
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_records(corpus: Path) -> dict[str, dict[str, Any]]:
    """Every full record the corpus holds now, as `--repin` pins it."""
    pins: dict[str, dict[str, Any]] = {}
    for path in record_paths(corpus):
        entry: dict[str, Any] = {"sha256": _sha(path)}
        for name, companion in companions(corpus, path).items():
            entry[name] = (None if companion is None else
                           {"path": companion.relative_to(corpus).as_posix(), "sha256": _sha(companion)})
        pins[path.relative_to(corpus).as_posix()] = entry
    return pins


def unpinned(corpus: Path, pins: dict[str, Any]) -> list[str]:
    """Full records the pins do not name: reported, never counted or stale."""
    return [p.relative_to(corpus).as_posix() for p in record_paths(corpus)
            if p.relative_to(corpus).as_posix() not in pins]


def _pinned_path(value: Any) -> bool:
    parts = PurePosixPath(value).parts if isinstance(value, str) else ()
    return bool(parts) and not PurePosixPath(value).is_absolute() and ".." not in parts


def read_pins(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """The pinned set; a pin file that is missing or malformed is `Stale`."""
    path = path or PINS
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Stale(f"{_shown(path)} could not be read ({exc.strerror})") from exc
    except yaml.YAMLError as exc:
        raise Stale(f"{_shown(path)} does not parse") from exc
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, dict) or not records:
        raise Stale(f"{_shown(path)} has no `records` mapping")
    for rel, entry in records.items():
        ok = (_pinned_path(rel) and isinstance(entry, dict) and set(entry) == {"sha256", *COMPANIONS}
              and isinstance(entry["sha256"], str) and _SHA256.fullmatch(entry["sha256"]))
        for name in COMPANIONS if ok else ():
            c = entry[name]
            ok = c is None or (isinstance(c, dict) and set(c) == {"path", "sha256"} and _pinned_path(c["path"])
                               and isinstance(c["sha256"], str) and bool(_SHA256.fullmatch(c["sha256"])))
            if not ok:
                break
        if not ok:
            raise Stale(f"{_shown(path)}: {rel!r} is not a path under the corpus pinned to a sha256 "
                        f"with its {' and '.join(COMPANIONS)}")
    return dict(records)


def write_pins(pins: dict[str, dict[str, Any]], path: Path | None = None) -> None:
    path = path or PINS
    header = (f"# The records {_shown(OUT_MD)} counts (#3041): each full record's path under\n"
              f"# {_shown(CORPUS)}/ and the sha256 of its bytes, with the phase-1 snapshot and the\n"
              "# coverage receipt it was paired with. Written by scripts/self_disclaimed_baseline.py\n"
              "# --repin; never edited by hand.\n")
    body = yaml.safe_dump({"records": dict(sorted(pins.items()))}, sort_keys=False, width=1000)
    path.write_text(header + body, encoding="utf-8")


# ------------------------------------------------------------------ counting
def _read(corpus: Path, rel: str, sha: str, changed: list, missing: list) -> bytes | None:
    try:
        raw = (corpus / rel).read_bytes()
    except OSError:
        missing.append(rel)
        return None
    if hashlib.sha256(raw).hexdigest() != sha:
        changed.append(rel)
        return None
    return raw


def collect(corpus: Path = CORPUS, pins: dict[str, dict[str, Any]] | None = None,
            lexicon_versions: list[int] | None = None) -> dict[str, Any]:
    """Run the lint over the pinned files under each lexicon version.

    Without `pins`, the corpus as `--repin` would pin it. A pinned file whose
    bytes are not its pin, or that is gone, raises `Stale` naming each.
    """
    pins = current_records(corpus) if pins is None else pins
    lexicons = {v: sd.load_lexicon(sd.lexicon_path(v)) for v in (lexicon_versions or versions())}
    if LEXICON_VERSION not in lexicons:
        raise Stale(f"LEXICON_VERSION {LEXICON_VERSION} is not a lexicon in {sd.LEXICON_RESOURCE_DIR}")
    rows, changed, missing, digest_lines = [], [], [], []
    for rel in sorted(pins):
        entry = pins[rel]
        files = {"final": (rel, entry["sha256"])}
        files.update({n: (entry[n]["path"], entry[n]["sha256"]) for n in COMPANIONS if entry[n]})
        raws = {n: _read(corpus, p, s, changed, missing) for n, (p, s) in files.items()}
        digest_lines += [f"{p} {s}\n" for p, s in files.values()]
        if any(raw is None for raw in raws.values()):
            continue
        parsed, errors = {}, {}
        for name, raw in raws.items():
            try:
                parsed[name] = (receipts.load_receipt(corpus / files[name][0], raw=raw) if name == "receipt"
                                else load_record(raw))
            except yaml.YAMLError as exc:
                errors[name] = type(exc).__name__
            except (ValueError, UnicodeDecodeError) as exc:
                errors[name] = ("not a mapping with a `chunks` list" if name == "receipt" and
                                isinstance(exc, ValueError) and "chunks" in str(exc) else str(exc))
        parts = rel.split("/")
        row: dict[str, Any] = {"path": rel, "method": parts[0], "label": parts[1] if len(parts) == 3 else "-",
                               "files": {n: p for n, (p, _) in files.items()}, "errors": errors, "by_version": {}}
        for version, lexicon in lexicons.items():
            row["by_version"][version] = _lint(parsed, errors, lexicon)
        rows.append(row)
    if changed or missing:
        raise Stale(f"{len(changed)} pinned file(s) changed and {len(missing)} gone: "
                    + "; ".join([f"changed {r}" for r in changed] + [f"gone {r}" for r in missing]))
    digest = hashlib.sha256("".join(digest_lines).encode()).hexdigest()
    return {"lexicons": lexicons, "corpus": corpus, "records": rows, "record_set_sha256": digest}


def _lint(parsed: dict[str, Any], errors: dict[str, str], lexicon: sd.Lexicon) -> dict[str, Any]:
    """Check (a) on the final record; the snapshot-to-final diff where both
    parse; check (b) against the snapshot where there is one, else the final.
    Check (b) needs a readable final: with a snapshot it is classified to the
    final, and without one it is read from the final. So a refused final has
    no check (b) even where its snapshot parses, and a pinned snapshot that
    is refused is not replaced by the final: that pair has no diff and no
    check (b). A receipt no check (b) ran on is counted by `summarise` as
    `receipts_unchecked`, never under `receipts`."""
    final, snapshot, receipt = parsed.get("final"), parsed.get("snapshot"), parsed.get("receipt")
    out: dict[str, Any] = {"scan": sd.scan(final, lexicon) if final is not None else None,
                           "diff": None, "role_predicate": None, "role_predicate_diff": None}
    if "snapshot" in errors:
        return out
    if final is not None and snapshot is not None:
        d = sd.diff(snapshot, final, receipt=receipt, lexicon=lexicon)
        out["diff"] = {"original": d["original"], "lexicon_diff": d["lexicon_diff"], "final_only": d["final_only"]}
        out["role_predicate"] = d.get("role_predicate")
        out["role_predicate_diff"] = d.get("role_predicate_diff")
    elif receipt is not None and final is not None:
        out["role_predicate"] = sd.role_predicates(final, receipt, lexicon)
    return out


def _empty() -> dict[str, Any]:
    return {"records": 0, "unreadable": 0, "members": 0, "flagged": 0, "flagged_records": 0,
            "guarded": 0, "out_of_scope": 0,
            "pairs": 0, "pair_flags": 0, "final_only": 0, "classes": Counter(),
            "receipts": 0, "receipts_unchecked": 0, "rp_against_snapshot": 0, "rp_members": 0, "rp_flagged": 0,
            "rp_reasons": Counter(), "rp_classes": Counter()}


def summarise(collected: dict[str, Any], version: int) -> dict[str, Any]:
    """Counts under one lexicon version: by method, by method and label, in
    total, by rule, by guard and by out-of-scope reason."""
    methods: dict[str, dict] = {}
    labels: dict[tuple[str, str], dict] = {}
    total = _empty()
    rules: dict[str, dict] = {}
    guards: Counter = Counter()
    reasons: Counter = Counter()
    unreadable: list[str] = []
    for row in collected["records"]:
        lint = row["by_version"][version]
        buckets = (methods.setdefault(row["method"], _empty()),
                   labels.setdefault((row["method"], row["label"]), _empty()), total)
        for name, why in sorted(row["errors"].items()):
            unreadable.append(f"{row['files'][name]} ({why})")
        scan = lint["scan"]
        for b in buckets:
            b["records"] += 1
            b["unreadable"] += "final" in row["errors"]
            if row["files"].get("receipt") and "receipt" not in row["errors"]:
                # `receipts` is the receipts check (b) ran on; a readable
                # receipt whose final or snapshot was refused is not one.
                b["receipts" if lint["role_predicate"] is not None else "receipts_unchecked"] += 1
        if scan is not None:
            for b in buckets:
                b["members"] += scan["members_read"]
                b["flagged"] += len(scan["flags"])
                b["flagged_records"] += bool(scan["flags"])
                b["guarded"] += len(scan["guarded"])
                b["out_of_scope"] += len(scan["out_of_scope"])
            for flag in scan["flags"]:
                for hit in flag["hits"]:
                    _rule(rules, hit)["flag"] += 1
            for hit in scan["guarded"]:
                _rule(rules, hit)["guarded"] += 1
                guards[hit["guard"]] += 1
            for hit in scan["out_of_scope"]:
                _rule(rules, hit)["out_of_scope"] += 1
                reasons[hit["reason"]] += 1
        if lint["diff"] is not None:
            for b in buckets:
                b["pairs"] += 1
                b["pair_flags"] += len(lint["diff"]["original"]["flags"])
                b["final_only"] += len(lint["diff"]["final_only"])
                b["classes"].update(lint["diff"]["lexicon_diff"]["counts"])
        if lint["role_predicate"] is not None:
            rp = lint["role_predicate"]
            for b in buckets:
                b["rp_against_snapshot"] += lint["diff"] is not None
                b["rp_members"] += rp["members_read"]
                b["rp_flagged"] += len(rp["flags"])
                b["rp_reasons"].update(f["reason"] for f in rp["flags"])
                if lint["role_predicate_diff"] is not None:
                    b["rp_classes"].update(lint["role_predicate_diff"]["counts"])
    return {"methods": dict(sorted(methods.items())), "labels": dict(sorted(labels.items())), "total": total,
            "rules": dict(sorted(rules.items())), "guards": dict(sorted(guards.items())),
            "reasons": dict(sorted(reasons.items())), "unreadable": unreadable}


def _rule(rules: dict, hit: dict) -> dict:
    return rules.setdefault(hit["rule"], {"class": hit["class"], "flag": 0, "guarded": 0, "out_of_scope": 0})


# ------------------------------------------------------------------ the note
def _shown(path: Path) -> str:
    """Repository-relative where the path is under the checkout, else as given."""
    for candidate in (path, path.resolve()):
        try:
            return candidate.relative_to(ROOT).as_posix()
        except ValueError:
            continue
    return str(path)


def _table(header: list[str], rows: list[list[Any]], text: int = 1) -> list[str]:
    """A Markdown table whose first `text` columns are left-aligned."""
    return (["| " + " | ".join(header) + " |", "|" + "---|" * text + "---:|" * (len(header) - text)]
            + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def _scan_cells(m: dict) -> list[Any]:
    return [m["records"], m["unreadable"], m["members"], m["flagged"], m["flagged_records"],
            m["guarded"], m["out_of_scope"]]


def _diff_cells(m: dict) -> list[Any]:
    return ([m["pairs"], m["pair_flags"]] + [m["classes"][c] for c in (*sd.CLASSIFICATIONS, RETAINED)]
            + [m["final_only"]])


def _rp_cells(m: dict) -> list[Any]:
    return ([m["receipts"], m["receipts_unchecked"], m["rp_against_snapshot"], m["rp_members"], m["rp_flagged"],
             m["rp_reasons"]["no_receipt"], m["rp_reasons"]["no_role_predicate"]]
            + [m["rp_classes"][c] for c in (*sd.CLASSIFICATIONS, RP_RETAINED)])


SCAN_HEAD = ["records", "unreadable", "members read", "flagged members", "records flagged", "guarded",
             "out of scope"]
DIFF_HEAD = ["pairs", "snapshot flags", *sd.CLASSIFICATIONS, "retained", "final_only"]
RP_HEAD = ["receipts checked", "not checked", "against snapshot", "person-role members", "flagged", "no_receipt",
           "no_role_predicate", *sd.CLASSIFICATIONS, "retained"]


def render_markdown(collected: dict[str, Any]) -> str:
    lexicons: dict[int, sd.Lexicon] = collected["lexicons"]
    lexicon = lexicons[LEXICON_VERSION]
    corpus: Path = collected["corpus"]
    s = summarise(collected, LEXICON_VERSION)
    t = s["total"]
    lines = [
        "# Self-disclaimed container entries: corpus baseline",
        "",
        "Generated by `scripts/self_disclaimed_baseline.py` (#3041). Do not edit by hand: run the",
        "script to regenerate it, or `--check` to ask whether it still matches its pinned records.",
        "",
        f"- **Instrument:** {sd.INSTRUMENT}; the detail tables count under lexicon v{LEXICON_VERSION},",
        f"  `{lexicon.path}`, sha256 `{lexicon.sha256}`.",
        f"- **Records:** {t['records']} full records, pinned by path and sha256 in `{_shown(PINS)}`",
        "  with the phase-1 snapshot (the last of `intermediate/{P}_full.yaml` and `{P}_full_N.yaml`,",
        "  the file-name rule `receipts.phase1_snapshot_read` falls back to) and the coverage receipt",
        "  each was paired with; record-set sha256",
        f"  `{collected['record_set_sha256']}` over every pinned file's path and bytes. `--repin` pins",
        f"  every `{RECORD_GLOB}` under `{_shown(corpus)}/` in a method directory whose name does not",
        "  end `_core`, and one label directory below it. A record added since the last `--repin` is",
        "  reported by `--check` and not counted; a pinned file that changed or is gone makes this",
        "  note stale.",
        "- **Not read:** audits. The corpus audits carry no JSON pointers, so `removal_declared` and",
        "  `named_by_finding` cannot fire here; the direct-arm canaries that do carry them are replayed",
        "  as fixtures in `tests/test_self_disclaimed.py` (#3515).",
        "",
        "A flag is not a verdict on the placement: it says the entry's own words disclaim it. The",
        "counts are regular-expression matches under the named lexicon bytes and compare only with",
        "counts made under the same sha256. The lint is never gating, and nothing here writes a",
        "record or a provenance block. A file whose text repeats a mapping key is refused, as",
        "`d4d review self-disclaimed` refuses it, and counted as unreadable.",
        "",
        "## By lexicon version",
        "",
        "The same pinned files under every lexicon version in `container_lexicons/`. A version added",
        "there adds a row, so the note goes stale until it is regenerated, and the row is the",
        "version's effect on the corpus.",
        "",
    ]
    vrows = []
    for version, lx in lexicons.items():
        vt = summarise(collected, version)["total"]
        vrows.append([f"v{version}", f"`{lx.sha256[:12]}…`", vt["flagged"], vt["flagged_records"], vt["guarded"],
                      vt["out_of_scope"], vt["pair_flags"], vt["classes"]["removed"], vt["classes"][RETAINED],
                      vt["classes"]["identity_unresolved"], vt["final_only"], vt["rp_flagged"]])
    lines += _table(["lexicon", "sha256", "final: flagged members", "records flagged", "guarded", "out of scope",
                     "snapshot flags", "removed", "retained", "identity_unresolved", "final_only",
                     "check (b) flagged"], vrows, text=2)
    lines += ["", "## Check (a) on the final records", "", "### By method", "",
              f"#3029 (#2913 PR1) counted only the {' and '.join(f'`{m}`' for m in PR1_METHODS)} finals",
              "(34 flagged members, 26 guarded, 90 out of scope on the corpus as it stood then); its",
              f"figures compare with the `{' + '.join(PR1_METHODS)}` row, not with `**all**`, which",
              "counts every method's finals (#3703).", ""]
    sub = [s["methods"].get(m, _empty()) for m in PR1_METHODS]
    subtotal = [sum(cells) for cells in zip(*(_scan_cells(m) for m in sub))]
    lines += _table(["method", *SCAN_HEAD],
                    [[n, *_scan_cells(m)] for n, m in s["methods"].items()]
                    + [[f"*{' + '.join(PR1_METHODS)}*", *subtotal], ["**all**", *_scan_cells(t)]])
    lines += ["", "### By label", "", "Labels with at least one flagged, guarded or out-of-scope match.", ""]
    lines += _table(["method", "label", *SCAN_HEAD],
                    [[m, lab, *_scan_cells(c)] for (m, lab), c in s["labels"].items()
                     if c["flagged"] or c["guarded"] or c["out_of_scope"]], text=2)
    lines += ["", "### By rule", "", "A flagged member counts once per hit, so a rule's flags can exceed the",
              "flagged members.", ""]
    lines += _table(["rule", "class", "flag hits", "guarded", "out of scope"],
                    [[f"`{r}`", v["class"], v["flag"], v["guarded"], v["out_of_scope"]]
                     for r, v in s["rules"].items()], text=2)
    lines += ["", "### Guarded by guard, out of scope by reason", ""]
    lines += _table(["guard", "matches"], [[f"`{g}`", n] for g, n in s["guards"].items()])
    lines += [""]
    lines += _table(["reason", "matches"], [[f"`{r}`", n] for r, n in s["reasons"].items()])
    lines += ["", "## Phase-1 snapshot to final", "",
              "Each snapshot flag followed to the final record by identity and classified; `final_only`",
              "is a final flag no snapshot flag maps to.", "", "### By method", ""]
    pair_methods = [[n, *_diff_cells(m)] for n, m in s["methods"].items() if m["pairs"]]
    lines += _table(["method", *DIFF_HEAD], pair_methods + [["**all**", *_diff_cells(t)]])
    lines += ["", "### By label", "", "Pairs with at least one snapshot or final_only flag.", ""]
    lines += _table(["method", "label", *DIFF_HEAD],
                    [[m, lab, *_diff_cells(c)] for (m, lab), c in s["labels"].items()
                     if c["pair_flags"] or c["final_only"]], text=2)
    lines += ["", "## Check (b): coverage receipts", "",
              "Each person-role member no receipt snippet addressed to it names in one of its container's",
              "role predicates, read against the phase-1 snapshot where there is one, else the final;",
              "classified to the final where there is a snapshot. As #2913 predicted, it over-flags.",
              "`receipts checked` counts the receipts check (b) ran on; `not checked` a readable receipt",
              "whose final or snapshot was refused (see Unreadable), which has no check (b).", ""]
    rp_methods = [[n, *_rp_cells(m)] for n, m in s["methods"].items()
                  if m["receipts"] or m["receipts_unchecked"]]
    lines += _table(["method", *RP_HEAD], rp_methods + [["**all**", *_rp_cells(t)]])
    if s["unreadable"]:
        lines += ["", "## Unreadable", "",
                  "Refused. A refused final record is counted in `records` and `unreadable`, and a",
                  "readable receipt beside it under check (b)'s `not checked`; a pair whose final or",
                  "snapshot is refused has no diff and no check (b).", ""]
        lines += [f"- `{u}`" for u in s["unreadable"]]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="read-only: exit 1 when a pinned file changed or is gone, or the note does not "
                           "match the pinned records; a record the pins do not name is reported, not stale")
    mode.add_argument("--repin", action="store_true",
                      help="pin the full records the corpus holds now, then write the pins and the note")
    args = ap.parse_args(argv)
    try:
        pins = current_records(CORPUS) if args.repin else read_pins(PINS)
        collected = collect(CORPUS, pins=pins)
    except Stale as exc:
        print(f"stale: {exc}. Run scripts/self_disclaimed_baseline.py --repin to pin the corpus as it "
              "stands.", file=sys.stderr)
        return 1
    new = unpinned(CORPUS, pins)
    if new:
        named = "; ".join(new[:10]) + (f"; and {len(new) - 10} more" if len(new) > 10 else "")
        print(f"reported, not counted: {len(new)} full record(s) under {_shown(CORPUS)}/ are not in the "
              f"pinned set ({named}); --repin counts them", file=sys.stderr)
    text = render_markdown(collected)
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != text:
            print(f"stale: {_shown(OUT_MD)} does not match its {len(pins)} pinned records; "
                  "run scripts/self_disclaimed_baseline.py", file=sys.stderr)
            return 1
        print(f"{_shown(OUT_MD)} matches its {len(pins)} pinned records")
        return 0
    if args.repin:
        write_pins(pins, PINS)
        print(f"pinned {len(pins)} records in {_shown(PINS)}")
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"wrote {_shown(OUT_MD)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
