"""The review pack: what a reviewer of a generated record needs, assembled
deterministically from the record's own provenance (#787).

The receipt validator (#708) is deterministic and leaves three questions to
judgement — whether a `nothing_relevant` chunk truly held nothing, whether a
verbatim snippet supports the value under it, whether the value is the right
reading of the passage — and a fourth no rubric can ask without the rule
text: whether the record followed the instruction it was sent. A pack turns
"review this record" into a fixed list of items, each with a pointer (chunk
id and line span, or slot path with its cited chunk and snippet), so the
review is specific, samplable, and checkable afterwards (`review_check`).

Everything comes from the provenance record: the instruction is
`prompts.request` (its text is re-rendered from the spec, or read from the
launcher's file when given), the bundle is `inputs.bundle_path`, the manifest
is `inputs.chunks`, the receipts are beside the core record. The sample is
seeded by the record's request hash, so two reviewers of one record see the
same items.
"""
from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path
from typing import Any

import yaml

#: The closed verdict vocabulary a review must use, per item kind.
VERDICTS = {
    "chunk_nothing_relevant": ("confirmed", "missed_content", "cannot_tell"),
    # `weak`: the snippet is verbatim and the passage is real, but it does
    # not answer the slot's question (a bare repository name receipting a
    # de-identification method) — #793.
    "slot_receipted": ("supported", "weak", "misread", "unsupported", "cannot_tell"),
    # `inferred`: no passage states it; it follows from stated lines. The
    # rules say such a value is an inference the record should not carry,
    # so it is adverse, but it is not the same finding as a fabrication.
    "slot_receiptless": ("bundle_supports", "inferred", "not_in_bundle", "exempt_by_nature", "cannot_tell"),
    "slot_reshaped": ("still_supported", "changed_meaning", "cannot_tell"),
    "rule": ("followed", "violated", "not_applicable", "cannot_tell"),
    # A `semantic-review-required` pair warning (#691): the deterministic
    # checker matched related full/core content and cannot judge whether the
    # relation holds semantically. `consistent`: the matched content says the
    # same thing; `divergent`: it does not, with paths and what differs.
    "pair_warning": ("consistent", "divergent", "cannot_tell"),
}
#: The verdicts that count against the record, per kind — derived, so a
#: verdict added above cannot be silently uncounted (#792).
AFFIRMATIVE = {"confirmed", "supported", "bundle_supports", "exempt_by_nature", "still_supported",
               "followed", "not_applicable", "consistent"}
ADVERSE = {k: tuple(v for v in vs if v not in AFFIRMATIVE and v != "cannot_tell") for k, vs in VERDICTS.items()}
def _anchored(rel: Path) -> Path:
    """cwd-proof (#822): a relative repo path resolved against the package
    root, so pack content cannot depend on the launch directory."""
    return rel if rel.is_absolute() else Path(__file__).resolve().parents[2] / rel


PAIR_SCHEMAS = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
                "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
SCHEMA_FILES = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml (class Dataset; slot descriptions)",
                "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml (class CoreDataset)")
#: What a reviewer cannot resolve from the pack alone is its own verdict, not
#: a pass: the pack reports how many, like UNMEASURABLE.
CANNOT_TELL = "cannot_tell"

DEFAULT_SAMPLE = {"receipted_slots": 25, "receiptless_slots": 25, "reshaped_slots": 25}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_paths(provenance: Path) -> dict[str, Path]:
    from data_sheets_schema.backfill_checks import record_paths as _rp
    p = _rp(provenance)
    core_dir = provenance.parent
    p["receipt"] = core_dir / f"{p['project']}_coverage_receipt.yaml"
    p["claims"] = core_dir / f"{p['project']}_receipts.yaml"
    p["review"] = core_dir / f"{p['project']}_review.yaml"
    p["pack"] = core_dir / f"{p['project']}_review_pack.yaml"
    p["review_b"] = core_dir / f"{p['project']}_review_b.yaml"
    p["instruction"] = core_dir / f"{p['project']}_review_instruction.md"
    return p


def instruction_text(record: dict[str, Any], instruction_file: Path | None) -> tuple[str | None, str]:
    """(text, basis). The launcher's file when given and its hash matches the
    record; else re-rendered from the recorded spec; else None."""
    req = ((record.get("prompts") or {}).get("request")) or {}
    want = req.get("sha256")
    if instruction_file is not None and instruction_file.exists():
        text = instruction_file.read_text(encoding="utf-8")
        got = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if want and got == want:
            return text, f"file {instruction_file} (sha256 matches the record)"
        return text, f"file {instruction_file} (sha256 does NOT match the record's request)"
    spec = req.get("spec")
    if isinstance(spec, dict) and spec.get("condition"):
        try:
            from data_sheets_schema.api_runner import RunSpec, resolve_prompt
            run = record.get("run") or {}
            s = RunSpec(project=run.get("project"), arm=spec.get("arm", ""), method=run.get("method", "claudecode_agent"),
                        bundle=Path(spec.get("bundle", "")), label=run.get("label", ""),
                        condition=spec["condition"], manifest_line=spec.get("manifest_line", ""),
                        run_date=spec.get("run_date", ""), runtime=spec.get("runtime", ""),
                        provider=spec.get("provider"))
            text = resolve_prompt(s)
            got = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return text, ("re-rendered from the recorded spec (sha256 matches)" if got == want
                          else "re-rendered from the recorded spec (sha256 does NOT match — the prompt file has moved)")
        except Exception as exc:                                     # noqa: BLE001
            return None, f"could not re-render: {exc}"
    return None, "no instruction recoverable: the record has no spec and no file was given"


def rules_from(instruction: str) -> list[dict[str, str]]:
    """The instruction's rule bullets, each a checklist item. Bullets under
    the uniform rules and every `ADDED IN vN` block; continuation lines
    joined; the block named so a verdict can say which version's rule."""
    out: list[dict[str, str]] = []
    block = "uniform"
    cur: list[str] | None = None

    def flush() -> None:
        nonlocal cur
        if cur:
            text = " ".join(l.strip() for l in cur).strip()
            out.append({"id": f"rule-{len(out) + 1:02d}", "block": block, "text": text})
        cur = None

    started = False
    for line in instruction.splitlines():
        m = re.match(r"--- ADDED IN (v\d+) ---", line)
        if m:
            flush(); block = m.group(1); started = True; continue
        if re.match(r"--- END ADDED IN", line):
            flush(); continue
        if line.startswith("UNIFORM DECISION RULES"):
            flush(); block = "uniform"; started = True; continue
        if line.startswith("RETURN:"):
            flush(); break
        if not started:
            continue
        if line.startswith("- "):
            flush(); cur = [line[2:]]
        elif cur is not None and line.startswith("  ") and line.strip():
            cur.append(line)
        elif cur is not None and not line.strip():
            flush()
    flush()
    return out


#: What the pack shows for a receipt path the final record no longer has —
#: a leaf phase 4 deleted, an index into a list it collapsed. Distinct from
#: a genuine null leaf, which the pack shows as `null` (#808).
UNRESOLVED = "<path does not resolve in the record>"


def _value_at(record: Any, path: str, limit: int = 300) -> Any:
    """The record's value at a slot path, truncated for the pack (#791);
    :data:`UNRESOLVED` when the path does not reach a value."""
    cur = record
    for part in re.findall(r"[\w]+|\[\d+\]", path):
        try:
            if part.startswith("["):
                # a list index against a string would return a character —
                # a receipt path into a value reconcile collapsed to one string
                # does not resolve, it is not a one-letter value
                if not isinstance(cur, list):
                    return UNRESOLVED
                cur = cur[int(part[1:-1])]
            else:
                if not isinstance(cur, dict) or part not in cur:
                    return UNRESOLVED
                cur = cur[part]
        except (KeyError, IndexError, TypeError):
            return UNRESOLVED
    s = cur if isinstance(cur, (int, float, bool)) or cur is None else str(cur)
    return s[:limit] + "…" if isinstance(s, str) and len(s) > limit else s


def _id_slots(full: Any, root_class: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Every populated `…id` leaf of the record with whether the schema
    *forces* the id (#803) and whether the value is a *mint* (#823): `File`,
    `FileCollection`, `DataSubset` — and `Person` — ids are LinkML
    identifiers, so a record that documents those parts cannot omit the id.
    `forced` speaks only to the id's presence given the object; `minted`
    (a urn, or a fragment on the record's own id — `receipts._minted`) is
    what separates a labelled part from a world-facing reference, whose
    truth the evidence rules judge, not the fragment rule.

    Returns (entries, gap): entries carry {path, class, identifier, required,
    forced, minted}; a path whose class the walk cannot resolve is listed
    with resolvable: false rather than guessed. gap names why the flags are
    unavailable (no schema, no SchemaView, unknown root class) — named,
    not filled; exception class only, so pack bytes stay machine-neutral."""
    try:
        from linkml_runtime import SchemaView

        from data_sheets_schema.constants.schemas import SCHEMA_PATH
        from data_sheets_schema.receipts import _minted, populated_leaves
        schema_path = Path(SCHEMA_PATH)
        if not schema_path.is_absolute():                     # cwd-proof (#822)
            schema_path = Path(__file__).resolve().parents[2] / schema_path
        sv = SchemaView(str(schema_path))
    except Exception as e:                                    # noqa: BLE001
        return [], f"id slot flags unavailable: {type(e).__name__}"
    root = root_class or (full.get("conforms_to_class") if isinstance(full, dict) else None) or "Dataset"
    if not sv.get_class(root, strict=False):
        return [], f"id slot flags unavailable: root class {root} not in the schema"
    record_id = full.get("id") if isinstance(full, dict) and isinstance(full.get("id"), str) else None
    out: list[dict[str, Any]] = []
    for path, value in populated_leaves(full):
        if path == "id" or not path.endswith(".id"):          # the record's own id is exempt (#722)
            continue
        cls: str | None = root
        try:
            for name in [n for n in re.findall(r"[\w]+|\[\d+\]", path) if not n.startswith("[")][:-1]:
                rng = sv.induced_slot(name, cls).range
                cls = rng if rng and sv.get_class(rng, strict=False) else None
                if cls is None:
                    break
            if cls is None:
                out.append({"path": path, "resolvable": False})
                continue
            slot = sv.induced_slot("id", cls)
            ident, req = bool(slot.identifier), bool(slot.required)
            out.append({"path": path, "class": cls, "identifier": ident, "required": req,
                        "forced": ident or req, "minted": _minted(value, record_id)})
        except Exception:                                     # noqa: BLE001
            out.append({"path": path, "resolvable": False})
    return out, None


def build_pack(provenance: Path, instruction_file: Path | None = None,
               sample: dict[str, int] | None = None) -> dict[str, Any]:
    from data_sheets_schema.backfill_checks import _split_header
    from data_sheets_schema.chunking import chunk_texts, load_manifest
    from data_sheets_schema.receipts import claim_receipts, load_receipt

    sample = {**DEFAULT_SAMPLE, **(sample or {})}
    record = yaml.safe_load(_split_header(provenance.read_text(encoding="utf-8"))[1]) or {}
    paths = record_paths(provenance)
    run = record.get("run") or {}
    inputs = record.get("inputs") or {}
    seed = ((record.get("prompts") or {}).get("request") or {}).get("sha256") or _sha(provenance)
    rng = random.Random(seed)

    pack: dict[str, Any] = {
        "pack_version": 3,
        "run": {"label": run.get("label"), "project": run.get("project"), "method": run.get("method"),
                "condition": (((record.get("prompts") or {}).get("request") or {}).get("spec") or {}).get("condition")},
        # The path only: `review check --write` adds a block to this record,
        # so a hash of it here would make every re-run pack a different pack
        # (#792). The request hash below is what pins the run.
        "provenance": {"path": str(provenance),
                       "request_sha256": ((record.get("prompts") or {}).get("request") or {}).get("sha256")},
        "seed": seed,
        "schema": list(SCHEMA_FILES),
        "gaps": [],
    }

    text, basis = instruction_text(record, instruction_file)
    ipath = paths["instruction"]
    if text:
        ipath.write_text(text, encoding="utf-8")            # the reviewer reads the instruction, not its hash (#791)
    pack["instruction"] = {"basis": basis, "path": str(ipath) if text else None,
                           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
                           "chars": len(text) if text else 0}
    pack["rules"] = rules_from(text) if text else []
    if not text:
        pack["gaps"].append("instruction: " + basis)

    bundle = Path(inputs["bundle_path"]) if inputs.get("bundle_path") else None
    chunks_in = inputs.get("chunks") or {}
    manifest_path = Path(chunks_in["path"]) if chunks_in.get("path") else None
    pack["bundle"] = {"path": str(bundle) if bundle else None, "md5": inputs.get("bundle_md5"),
                      "manifest": str(manifest_path) if manifest_path else None}
    pack["records"] = {"full": str(paths["full"]), "core": str(paths["core"]),
                       "report": str(paths["report"]),
                       "receipt": str(paths["receipt"]) if paths["receipt"].exists() else None,
                       "claims": str(paths["claims"]) if paths["claims"].exists() else None}

    # --- every minted id, with whether the schema forced it (#803): the
    # instruction's fragment rule cannot be judged without this — a rule-14
    # verdict on an identifier slot charges the record with the schema.
    full_record = yaml.safe_load(paths["full"].read_text(encoding="utf-8")) or {} if paths["full"].exists() else {}
    id_entries, id_gap = _id_slots(full_record) if full_record else ([], "id slot flags unavailable: no full record")
    pack["id_slots"] = {"entries": id_entries,
                        "note": "forced: the schema declares this class's id as an identifier or required, "
                                "so the record could not omit the id given the object — it settles the id's "
                                "presence, not the object's. minted: a urn or a fragment on the record's own "
                                "id; false means a world-facing reference (a DOI, ROR, URL) whose truth the "
                                "evidence rules judge, not the fragment rule. The fragment rule is judged on "
                                "minted ids only, and a forced mint never violates it; resources[*].id is "
                                "also consumed by `d4d derive core`'s projection."}
    if id_gap:
        pack["gaps"].append(id_gap)

    # --- chunks marked nothing_relevant: every one, with its lines
    items: list[dict[str, Any]] = []
    if paths["receipt"].exists() and manifest_path and manifest_path.exists():
        receipt = load_receipt(paths["receipt"])
        manifest = load_manifest(manifest_path)
        span = {c["id"]: c for c in manifest["chunks"]}
        pack["bundle"]["lines"] = manifest.get("bundle_lines")
        pack["bundle"]["chunks"] = [{"id": c["id"], "lines": c["lines"], "source": c["source"]} for c in manifest["chunks"]]
        for e in receipt.get("chunks") or []:
            if e.get("status") == "nothing_relevant" and e.get("id") in span:
                c = span[e["id"]]
                items.append({"id": f"chunk-{e['id']}", "kind": "chunk_nothing_relevant",
                              "chunk": e["id"], "lines": c["lines"], "source": c["source"],
                              "agent_reason": e.get("reason"),
                              "question": "Does this chunk hold anything the record should carry and does not? "
                                          "Open the lines; answer against the full record."})
        # --- slots
        full = full_record
        claims = claim_receipts(receipt, full)
        rc = record.get("receipts") or {}
        receipted = sorted(claims["slots"])
        rng.shuffle(receipted)
        for slot in receipted[: sample["receipted_slots"]]:
            rs = claims["slots"][slot]["receipts"]
            items.append({"id": f"slot-{len(items) + 1:03d}", "kind": "slot_receipted", "slot": slot,
                          "value": _value_at(full, slot),
                          "receipts": [{"chunk": r["chunk"], "lines": span.get(r["chunk"], {}).get("lines"),
                                        "snippet": r["snippet"]} for r in rs],
                          "question": "Read the passage each snippet sits in. Does it support the record's value at "
                                      "this slot, as the slot's description asks, and is the value the right reading? "
                                      f"A value of {UNRESOLVED!r} means the final record has no value at this path: "
                                      "answer cannot_tell unless the receipt's statement survives elsewhere."})
        # The receiptless set from the receipt and the record themselves,
        # not the record's 50-entry walk-order prefix (#790): every populated,
        # non-exempt leaf no receipt path covers, sorted, then sampled.
        from data_sheets_schema.receipts import _covers, exempt, populated_leaves
        record_id = full.get("id") if isinstance(full.get("id"), str) else None
        without = sorted(p for p, v in populated_leaves(full)
                         if not exempt(p, v, record_id) and not any(_covers(r, p) for r in claims["slots"]))
        rng.shuffle(without)
        for slot in without[: sample["receiptless_slots"]]:
            items.append({"id": f"slot-{len(items) + 1:03d}", "kind": "slot_receiptless", "slot": slot,
                          "value": _value_at(full, slot),
                          "question": "No receipt names a passage for this value. Find one in the bundle, or "
                                      "conclude it is inferred from stated lines, or that the bundle does not "
                                      "state it, or that the slot is of a kind that has no passage."})
        reshaped = list(((rc.get("slots") or {}).get("reshaped_by_reconcile")) or [])
        for slot in reshaped[: sample["reshaped_slots"]]:
            items.append({"id": f"slot-{len(items) + 1:03d}", "kind": "slot_reshaped", "slot": slot,
                          "question": "A later phase reshaped this path after the receipt. Does the value now "
                                      "at the reshaped location still say what the receipted passage says?"})
        pack["counts"] = {"nothing_relevant_chunks": sum(1 for i in items if i["kind"] == "chunk_nothing_relevant"),
                          "receipted_slots_total": len(claims["slots"]),
                          "receiptless_slots_total": len(without),
                          "reshaped_slots_total": len(reshaped),
                          "sampled": {"receipted": min(sample["receipted_slots"], len(claims["slots"])),
                                      "receiptless": min(sample["receiptless_slots"], len(without))}}
    else:
        pack["gaps"].append("no coverage receipt or chunk manifest: chunk and slot items cannot be built")
        pack["counts"] = {}

    for r in pack["rules"]:
        items.append({"id": r["id"], "kind": "rule", "block": r["block"], "text": r["text"],
                      "question": "Did the record follow this rule? Cite the slot(s) that show it, or the violation."})
    # --- semantic-review-required pair warnings (#691): the provenance block
    # stores only a count, so the deterministic checker is re-run on the two
    # records; failure to run is a named gap, never a silent absence.
    try:
        from data_sheets_schema.d4d_pair_consistency import (
            load_pair_schema, pair_predates_current_schema, validate_pair_data)
        full_p, core_p = Path(pack["records"]["full"]), Path(pack["records"]["core"])
        if full_p.exists() and core_p.exists():
            rep = validate_pair_data(
                yaml.safe_load(full_p.read_text(encoding="utf-8")) or {},
                yaml.safe_load(core_p.read_text(encoding="utf-8")) or {},
                load_pair_schema(*(_anchored(Path(x)) for x in PAIR_SCHEMAS)),
                schema_moved=pair_predates_current_schema(core_p),
                run_digest=(record.get("schema") or {}).get("digest_md5"))
            n = 0
            for w in rep.warnings:
                if getattr(w, "code", None) != "semantic-review-required":
                    continue
                n += 1
                items.append({"id": f"pair-{n:02d}", "kind": "pair_warning",
                              "path": w.path, "checker_message": w.message,
                              "question": "The deterministic checker matched this related full/core "
                                          "content but cannot judge the relation semantically. Open "
                                          "both records at the path; do the matched values say the "
                                          "same thing? Answer with the paths compared and what "
                                          "differs, if anything."})
        else:
            pack["gaps"].append("pair warnings: full or core record missing; the checker did not run")
    except Exception as e:                                    # noqa: BLE001
        pack["gaps"].append(f"pair warnings unavailable: {type(e).__name__}")

    pack["items"] = items
    pack["verdicts"] = {k: list(v) for k, v in VERDICTS.items()}
    return pack


def write_pack(provenance: Path, instruction_file: Path | None = None,
               sample: dict[str, int] | None = None) -> tuple[Path, dict[str, Any]]:
    pack = build_pack(provenance, instruction_file, sample)
    out = record_paths(provenance)["pack"]
    from data_sheets_schema.provenance import _NoAliasDumper
    # chunk line spans are shared between `bundle.chunks` and the items; an
    # alias dumper would write the second as `*id001`
    out.write_text(yaml.dump(pack, Dumper=_NoAliasDumper, sort_keys=False, allow_unicode=True, width=10_000),
                   encoding="utf-8")
    return out, pack


def check_review(pack: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Does the review answer the pack? Every item once, with a verdict from
    its kind's vocabulary and a pointer that exists in the pack; the counts
    are affirmative and `cannot_tell` is its own number (#787)."""
    findings: list[dict[str, Any]] = []
    by_id = {i["id"]: i for i in pack.get("items") or []}
    answered: dict[str, dict[str, Any]] = {}
    for a in review.get("items") or []:
        if not isinstance(a, dict) or a.get("id") not in by_id:
            findings.append({"kind": "answer_for_unknown_item", "id": a.get("id") if isinstance(a, dict) else None})
            continue
        if a["id"] in answered:
            findings.append({"kind": "item_answered_twice", "id": a["id"]}); continue
        kind = by_id[a["id"]]["kind"]
        if a.get("verdict") not in VERDICTS[kind]:
            findings.append({"kind": "verdict_not_in_vocabulary", "id": a["id"], "verdict": a.get("verdict"),
                             "allowed": list(VERDICTS[kind])})
        if not str(a.get("evidence") or "").strip():
            findings.append({"kind": "verdict_without_evidence", "id": a["id"]})
        answered[a["id"]] = a
    unanswered = [i for i in by_id if i not in answered]
    if not review.get("pack_sha256"):
        findings.append({"kind": "review_without_pack_hash"})      # which pack was answered? (#792)
    elif pack.get("_sha256") and review["pack_sha256"] != pack["_sha256"]:
        findings.append({"kind": "review_of_another_pack", "pack": pack["_sha256"], "review": review["pack_sha256"]})
    by_kind: dict[str, dict[str, int]] = {}
    for iid, a in answered.items():
        k = by_id[iid]["kind"]; d = by_kind.setdefault(k, {})
        d[str(a.get("verdict"))] = d.get(str(a.get("verdict")), 0) + 1
    adverse = sum(v for k, d in by_kind.items() for verdict, v in d.items() if verdict in ADVERSE.get(k, ()))
    cannot = sum(d.get(CANNOT_TELL, 0) for d in by_kind.values())
    return {"checked": True, "items_total": len(by_id), "items_answered": len(answered),
            "unanswered": unanswered[:50], "unanswered_truncated": max(0, len(unanswered) - 50) or None,
            "by_kind": by_kind, "adverse": adverse, "cannot_tell": cannot,
            "findings": findings,
            "summary": (f"items {len(answered)}/{len(by_id)} answered · {adverse} adverse · {cannot} cannot_tell"
                        + (f" · {len(findings)} finding(s)" if findings else ""))}


# ---------------------------------------------------------------- reliability
def _verdict_class(verdict: Any) -> str:
    if verdict == "cannot_tell":
        return "cannot_tell"
    return "affirmative" if verdict in AFFIRMATIVE else "adverse"


def agree(pack: dict[str, Any], review_a: dict[str, Any], review_b: dict[str, Any]) -> dict[str, Any]:
    """Test–retest agreement between two independent reviews of ONE pack.

    Deterministic and offline. Both reviews must pin the pack's sha256 — two
    ratings of different packs are not paired observations. Cohen's kappa is
    computed on the collapsed affirmative/adverse/cannot_tell trichotomy: the
    full vocabulary has too many cells for ~50 items, and the trichotomy is
    what every downstream count (adverse rate) actually uses. Items either
    review left unanswered are excluded from kappa and counted apart. kappa
    is None when the marginals make chance agreement 1 (all items one class
    in both reviews — agreement is perfect but the statistic is undefined).
    """
    for name, rev in (("a", review_a), ("b", review_b)):
        if rev.get("pack_sha256") != pack.get("_sha256"):
            raise ValueError(f"review {name} pins {rev.get('pack_sha256')!r}, not this pack")
    va = {str(i.get("id")): i.get("verdict") for i in review_a.get("items") or []}
    vb = {str(i.get("id")): i.get("verdict") for i in review_b.get("items") or []}
    ids = [str(i.get("id")) for i in pack.get("items") or []]
    kinds = {str(i.get("id")): i.get("kind") for i in pack.get("items") or []}
    paired, unanswered = [], []
    for i in ids:
        # An item without a verdict is unanswered, not a rating: a missing
        # or null verdict must not class as adverse (#861).
        if va.get(i) is not None and vb.get(i) is not None:
            paired.append((i, va[i], vb[i]))
        else:
            unanswered.append(i)
    classes = ("affirmative", "adverse", "cannot_tell")
    n = len(paired)
    conf = {a: {b: 0 for b in classes} for a in classes}
    exact = 0
    disagreements = []
    by_kind: dict[str, dict[str, int]] = {}
    for i, a, b in paired:
        ca, cb = _verdict_class(a), _verdict_class(b)
        conf[ca][cb] += 1
        k = by_kind.setdefault(kinds.get(i, "?"), {"paired": 0, "class_agree": 0, "exact": 0})
        k["paired"] += 1
        if ca == cb:
            k["class_agree"] += 1
        if a == b:
            exact += 1; k["exact"] += 1
        if ca != cb:
            disagreements.append({"id": i, "kind": kinds.get(i), "a": a, "b": b})
    po = (sum(conf[c][c] for c in classes) / n) if n else None
    kappa = None
    if n:
        pe = sum((sum(conf[c].values()) / n) * (sum(conf[r][c] for r in classes) / n) for c in classes)
        kappa = round((po - pe) / (1 - pe), 3) if pe < 1 else None
    adverse_a = sum(1 for _i, a, _b in paired if _verdict_class(a) == "adverse")
    adverse_b = sum(1 for _i, _a, b in paired if _verdict_class(b) == "adverse")
    return {"paired_items": n, "unanswered_in_either": unanswered,
            "percent_class_agreement": round(100 * po, 1) if po is not None else None,
            "percent_exact_agreement": round(100 * exact / n, 1) if n else None,
            "kappa_class": kappa,
            "confusion": conf,
            "adverse_a": adverse_a, "adverse_b": adverse_b,
            "adverse_delta": adverse_b - adverse_a,
            "by_kind": by_kind,
            "disagreements": disagreements,
            "basis": "Cohen's kappa on affirmative/adverse/cannot_tell over items answered by both; "
                     "exact agreement is on the full vocabulary; single pack, both reviews pin its sha256"}
