#!/usr/bin/env python
"""Consolidated cross-arm comparison: one table, one set of figures, regenerated
from the provenance records rather than transcribed.

Why a script and not a table: every hand-made arm table in notes/ has needed
a review round to correct a copied baseline or a mis-summed cell (#655,
#676). The numbers here are read from the records at run time. Regenerate
the published outputs when those records change; --check detects a stale
Markdown table without writing outputs.

Bases, stated once and printed into the output:

- **pair errors, report findings, grounding** come from each record's own
  blocks. Pair consistency is a deterministic artifact check. Grounding is
  measured against the record's declared bundle — for every arm shown, the
  record's `inputs.bundle_md5` still matches the bundle on disk, and the
  block was written either by the run or by `backfill-checks` against that
  same bundle (the record's `recorded_by` says which).
- **form metrics** (British spellings, undeclared prefixes, organisational
  fragments, GC label variants) are recomputed live from the artifacts with
  the current instrument (`grounding.form_facts`) and the merged-schema
  identifier rules recorded by each run (#4216). Unrecoverable schema pins
  fall back to today's rules, with the reason disclosed per record. Stored
  form blocks are not read or rewritten; their measurements may differ.
  GC label variants still use today's naming manifest rather than a run's
  schema or a historical manifest. **GC label variants are anachronistic for the v4 and
  22c arms**: the manifest `naming:` declaration they are counted against
  was decided 2026-08-22, after the v4 arm ran and the day the 22c arm did.
- **rubric scores** come from `data/evaluation_llm/rubric{10,20}_semantic/
  label_aware/`, matched by label, and only exist for canonical (or
  would-be canonical) records. Applicability (N/A) is itself evaluator
  output, so adjusted maxima can differ between evaluations of comparable
  records; points and adjusted maximum are both shown.
- **item discrimination** (#2927): per evaluator, never pooled across
  evaluators, and per rubric version where an evaluator's evaluations span
  more than one (#3290), the items at ceiling or floor, each project's
  distinct totals and the rubrics' pair agreement on both bases. A project
  with at most two distinct totals is flagged in the rubric tables: no
  within-project order.
- **evaluator vs generator** (#2928): each rubric evaluation's evaluator
  beside the model its record's provenance says generated it, and whether
  the two are one model family (`evaluation_model.same_family`), derived at
  report time; nothing is written back to an evaluation.
- **removal rows** (#2923): values deleted without a finding, the share of
  them `reconcile_full` removed (#3150), receipted values deleted and values
  rewritten in place without a finding (#3243), with the low-confidence
  flattenings (#3367) and the rewrites not the model's (#3366), are
  recomputed live and read-only (`removals.for_record`), with recorded-schema
  identifier aliases and per-record fallback/Person/enum basis disclosures; the
  unrecorded-removal count is the record's `report_claims` block.
- **omission candidates** (#3335): an intermittent slot a filling replicate
  receipts with a snippet verified in its own chunk, the record's bundle
  bytes recovered from git where they drifted
  (`replicate_structure.record_chunk_texts`); `–` exactly where no replicate
  of the group has a readable receipt; the receipts instrument's exempt keys
  (`conforms_to_class`, `conforms_to_schema`, `notes`, `source_caveats`; not
  `conforms_to` or `conforms_to_standard`, #4434) are commentary, never a
  candidate (#3892, #3893).
- **release inventory** (#3282): `release_inventory` on today's source and
  crate manifests, and on the source-manifest version each arm's records
  pinned; the doi/license/version/issued differences it explains are
  labelled corpus-driven beside the rubric10 sub-elements they decide.
- **spend is deliberately absent**: `api_usage` (billed input/output) and
  `run_observed` (cache-inclusive runner totals) are different quantities and
  must never sit in one column (#400).

Usage:
    poetry run python scripts/arm_comparison.py            # writes md + png
    poetry run python scripts/arm_comparison.py --no-figures
    poetry run python scripts/arm_comparison.py --check    # read-only Markdown check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import html
import os
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
# form_facts → declared_naming() reads the manifest cwd-relative (#673); run
# from anywhere else and every GC count silently becomes 0.
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_model import (  # noqa: E402
    SAME_FAMILY_DISCLAIMER, same_family_label,
)
from data_sheets_schema.grounding import (  # noqa: E402
    BRITISH_INSTRUMENT, PREFIX_INSTRUMENT, form_facts,
)
from data_sheets_schema.semantic_comparison import (  # noqa: E402
    discrimination, evaluator_key, instruments_of, render_discrimination, withheld_projects,
)
CONCAT = ROOT / "data" / "d4d_concatenated"
EVAL_DIRS = {
    "rubric10": ROOT / "data" / "evaluation_llm" / "rubric10_semantic" / "label_aware",
    "rubric20": ROOT / "data" / "evaluation_llm" / "rubric20_semantic" / "label_aware",
}
RUBRIC_MAX = {"rubric10": 50, "rubric20": 88}
OUT_MD = ROOT / "notes" / "arm_comparison.md"
OUT_FIG = ROOT / "notes" / "figures"

PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
METHOD = "claudecode_agent"     # the pre-v8 directory; per-label from `_method_for` (#934)


def _method_for(label: str, project: str) -> str:
    """The directory a run lives in: claudecode_agent through v7, claudecode_api
    from the v8 API baseline (#690). Falls back to METHOD for a label that is
    not on disk, so a missing run reads as missing rather than as an error."""
    try:
        from data_sheets_schema.runs import method_for_label
        return method_for_label(label, project, concat_dir=CONCAT)
    except LookupError as exc:
        if "both" in str(exc):
            raise                       # two copies is a question, not a default
        return METHOD

# (key, display, label prefix, runtime, role). Every arm is shown as mean ± SD
# over its replicates; `role == "worst"` additionally prints the per-project
# worst on this table's measurement basis. Gates read stored blocks separately.
ARMS = (
    ("v4", "v4 API (2026-08-13)", "2026-08-13_claude-opus-5-api-generic-v4",
     "Claude API via CBORG", "worst"),
    ("v5api", "v5 API (2026-08-22c)", "2026-08-22c_claude-opus-5-api-generic-v5",
     "Claude API via CBORG", "reps"),
    ("v5agentic", "v5 agentic (2026-08-24)",
     "2026-08-24_claude-opus-5-claudecode-generic-v5", "Claude Code", "reps"),
    ("v6agentic", "v6 agentic (2026-08-28)",
     "2026-08-28_claude-opus-5-claudecode-generic-v6", "Claude Code", "reps"),
    # The v7 API arm is partial: five canary runs under four label prefixes
    # (CHORUS ×2, AI_READI ×3), the fan-out deferred (#777). An explicit label
    # list, not a prefix; n is 0 for CM4AI and VOICE and the table says so.
    ("v7api", "v7 API canaries (2026-08-28…d, exploratory)",
     ["2026-08-28_claude-opus-5-api-generic-v7_rep1", "2026-08-28b_claude-opus-5-api-generic-v7_rep1",
      "2026-08-28c_claude-opus-5-api-generic-v7_rep1", "2026-08-28d_claude-opus-5-api-generic-v7_rep1"],
     "Claude API via CBORG", "reps"),
    # The v7 PRODUCTION matrix (2026-09-01, 12 records): the registered arm
    # (#838/#849), excluded cohort separate above. The first API arm complete
    # under the receipt protocol - the 12-vs-12 comparison against v6 agentic.
    ("v7prod", "v7 API production (2026-09-01)",
     "2026-09-01_claude-opus-5-api-generic-v7", "Claude API via CBORG", "reps"),
    # The v8 PRODUCTION matrix (12 records, 2026-09-05..07): two label
    # prefixes, since the VOICE and CHORUS canaries passed under 04f and
    # AI_READI (after #1029) and CM4AI (fourth canary) under 04g; the fill
    # kept each project's prefix so rep1..3 sit together. The 04f AI_READI
    # record (invalid, #1029) and the 04b..04e canaries are excluded.
    ("v8prod", "v8 API production (2026-09-04f/g)",
     [f"2026-09-04f_claude-opus-5-api-generic-v8_rep{r}" for r in (1, 2, 3)]
     + [f"2026-09-04g_claude-opus-5-api-generic-v8_rep{r}" for r in (1, 2, 3)],
     "Claude API via CBORG", "reps"),
)


def _rep_tag(label: str) -> str:
    """`rep2`, or for an arm spanning several label prefixes the date suffix
    too — `28c/rep1` — so three "rep1" cells are distinguishable."""
    head, rep = label.rsplit("_rep", 1)
    date = head.split("_", 1)[0]
    return f"rep{rep}" if date.count("-") == 2 and len(date) == 10 else f"{date[-3:]}/rep{rep}"


def arm_labels(prefix) -> list[str]:
    """The run labels an arm spans: `{prefix}_rep{1..3}`, or an explicit list."""
    return list(prefix) if isinstance(prefix, (list, tuple)) else [f"{prefix}_rep{r}" for r in (1, 2, 3)]

# metric key -> (display, source, higher-is-worse, caveat)
METRICS: dict[str, tuple[str, str, bool, str]] = {
    "ungrounded": ("ungrounded identifiers", "record", True,
                   "grounding.distinct.absent as measured against the bundle the run saw"),
    "orgfrag": ("organisational fragments", "live", True,
                "identifier slots from the run's merged schema, or the disclosed fallback"),
    "undeclared": ("undeclared prefixes", "live", True,
                   f"current prefix instrument: {PREFIX_INSTRUMENT}; declared prefixes and Person/identifier "
                   "slots from the run's merged schema, or the disclosed fallback. A familiar prefix "
                   "can be undeclared in that schema; this is not a verdict that the namespace is invented"),
    "british": ("British spellings", "live", True,
                f"current instrument: {BRITISH_INSTRUMENT}. Coupled with pair errors on the API arm: a "
                "full/core spelling split counts once per shared slot in both (#675)"),
    "pair": ("pair errors", "record", True,
             "deterministic artifact check, comparable across arms; the procedures "
             "that reduce it differ by runtime (#689) and it is coupled with British "
             "spellings (#675)"),
    "report": ("report findings", "record", True,
               "claims_checked counts backticked removal claims and, from v8, the "
               "dispositions table's presence rows (#929); false-schema-claim "
               "findings come from a separate scan that counts nothing. A 0 with "
               "claims_checked 0 is therefore unmeasured on the removal form, not held "
               "(#684) — shown as 0ᵘ; any finding > 0 is measured"),
    "minted": ("minted fragments (reported)", "record", False,
               "reported-only; every fragment hangs off an attested base wherever "
               "ungrounded is 0. Appetite varies 3→130 within one project (#685)"),
    "unreviewed": ("chunks unreviewed", "record", True,
                   "receipts (#708): manifest chunks with no receipt entry. Only arms whose "
                   "procedure wrote a coverage receipt carry a value; earlier arms are –, "
                   "not 0"),
    "unverified": ("snippets unverified", "record", True,
                   "receipts (#708): mismatched + unchecked snippets; same caveat"),
    "wrongchunk": ("snippets not in the chunk cited", "record", True,
                   "receipts (#763): verbatim in the bundle but not in the chunk cited — "
                   "attribution precision, reported not gated. Read it against `snippets "
                   "checked` on the row below, never as a bare count; the pooled rates "
                   "are in the receipt-coverage section"),
    "snippets": ("snippets checked", "record", False,
                 "receipts (#708): the denominator for `snippets not in the chunk cited` "
                 "and for unverified — the receipt's own snippet count, which is a "
                 "property of how much the model quoted, not of the record"),
    "leaves": ("populated leaves (full record)", "record", False,
               "count of populated leaf values in the full record (receipts.populated_leaves); "
               "informational — the v6 plan's prediction 5 is that it does not fall"),
    "noreceipt": ("slots without a receipt", "record", True,
                  "receipts (#708): receiptable populated leaves with no receipt; exempt "
                  "slots (runner-set, minted, commentary) are outside the denominator. "
                  "`receiptable` on the row below is that denominator, so coverage degree "
                  "is readable here rather than inferable (#902)"),
    "receiptable": ("receiptable slots (denominator)", "record", False,
                    "receipts (#708): populated leaves that are not exempt — the "
                    "denominator every receipt count on these rows shares. It varies "
                    "two- to three-fold between records of one arm, so a bare "
                    "without-a-receipt count compares nothing (#902)"),
    "neverreceipted": ("of those, never receipted", "record", True,
                       "receipts (#807): the receiptless leaf resolved in the phase-1 "
                       "snapshot, so the model never receipted it. Needs that snapshot — "
                       "the API path writes one and the agentic path does not, so an "
                       "agentic arm is – here, not 0 (#899)"),
    "addedafter": ("of those, added after the receipt", "record", True,
                   "receipts (#807): the receiptless leaf is absent from the phase-1 "
                   "snapshot, so reconciliation or repair added it after the receipt was "
                   "written and no receipt route existed (#742). Same snapshot caveat"),
    "unfoundedremovals": ("removals without a finding", "live", True,
                          "removals v3 (#2923): values the phase-1 snapshot carried and the final "
                          "full record does not, whose text does not survive under their nearest "
                          "surviving ancestor (a resolver URL and the CURIE it names read as one "
                          "text, #3129, and a British spelling and its American form, #3038; a "
                          "value of numbers only survives only as a scalar equal to it, never "
                          "quoted in prose, and never below five digits, #3243, #3130; for an "
                          "entry dropped from a list, in its recognised "
                          "continuation or beyond what the list's other entries account for, "
                          "#3076), and that no slot, review_paths or remove_relationship path of an "
                          "audit finding not scoped to the core record alone covers (#3079; a "
                          "finding index one past the end of its list read as the last entry, "
                          "#3077). Every phase after phase 1 is counted: reconcile_full, the "
                          "validator-driven repair rounds (repair_full_rN) and the record write. "
                          "A repair round acts on validation errors, not on the audit, so a value "
                          "it removes has a finding only by coincidence; the row below isolates "
                          "reconcile_full (#3150). Reported, not gated: unfounded says no such "
                          "path covers the value, not that removing it was wrong, and a value "
                          "only a core-only finding's path covers is counted here. A value "
                          "reworded, moved to another key or slot, or split across list members "
                          "reads as deleted, since the test is its own text surviving (#3207), "
                          "while a lost word or long number that coincidentally matches "
                          "surviving text still reads as flattened, so the count errs both ways "
                          "and bounds nothing (#3229); a scalar rewritten in place is not a "
                          "removal and is counted on its own row below (#3243). Needs the "
                          "snapshot, so an agentic arm is – here, not 0 (#899); – also where the "
                          "run's audit cannot be read unambiguously"),
    "unfoundedreconcile": ("of those, removed at reconcile_full", "live", True,
                           "removals v3 (#3150): the removals without a finding that "
                           "reconcile_full removed — the phase told to remove what a finding "
                           "identifies as unsupported, and so the one this row compares across "
                           "arms. The rest of the row above is values a repair round or the "
                           "write removed after reconcile_full still carried them, typically a "
                           "repair collapsing an object to a string and dropping its "
                           "constructed id. – wherever the row above is –, and where a phase "
                           "output is missing or unreadable, which leaves the removing phase "
                           "unattributed (#3152)"),
    "unfoundedrelocated": ("of those, with a relocation candidate", "live", True,
                           "removals v3 (#3223): the removals without a finding whose content "
                           "words (three or more; an identifier by its own text, starting and "
                           "ending where an identifier does, #3603, #3618) recur, 70% of "
                           "them or more, in one scalar of the final full record or one list of "
                           "scalars taken whole — a sign the value was reworded or moved rather "
                           "than lost. Reported only: no count above moves, a candidate is where "
                           "the words are, not proof the content survives, and on the labelled "
                           "sample the threshold was chosen on (notes/"
                           "removals_relocated_sample_2026-09-29.yaml) it was right about nine "
                           "times in ten and found about four relocations in five (both routes: "
                           "19 of its 64 rows are identifiers, decided by their own text, 5 found, "
                           "none wrong, none missed; on the 45 content-word rows alone precision "
                           "0.87, recall 0.77, #3613). A candidate "
                           "under source_caveats is a change of standing: the value is no longer a "
                           "claim. – wherever the removals row is –"),
    "lowconfidenceflat": ("low-confidence flattenings without a finding", "live", True,
                          "removals v3 (#3367): values the rule above reads as flattened, not "
                          "removed, by a needle of one or two normalised tokens (an identifier "
                          "aside) or by the dropped-entry surplus route — where a coincidental "
                          "match is likeliest — and that no finding path would cover were they "
                          "deleted. Reported only: no count moves. It is the most those routes "
                          "can have kept out of the removals-without-a-finding row, were every "
                          "one a coincidence, so it sizes that row's deflation in one direction; "
                          "a longer needle can still coincide, so it bounds nothing (#3229). "
                          "– wherever the removals row is –"),
    "receipteddeleted": ("receipted values deleted, not flattened", "live", True,
                         "removals v3 (#2923): removed values a coverage receipt named (on the "
                         "value, an entry above it, or the list it was a member of) whose text "
                         "did not survive by the rule above, founded or not — reworded or moved "
                         "values included (#3207), coincidentally flattened and in-place "
                         "rewritten ones not, so not a bound on receipted content lost (#3229). "
                         "Counted per value, "
                         "so not a subset of "
                         "the receipts block's `receipts_to_removed_values`, which counts receipt "
                         "paths that stopped resolving, flattenings included. – where the run "
                         "wrote no receipt or no snapshot"),
    "unfoundedrewrites": ("values rewritten in place without a finding", "live", True,
                          "removals v3 (#3243): scalars the final full record still carries at "
                          "their path, populated, where the value now there does not contain "
                          "their old normalised text (a resolver URL and its CURIE one text, "
                          "and a British spelling and its American form, #3038), "
                          "and that no finding path covers by the rule above. Not in the "
                          "removal rows: the in-place route v1 counted as carried (#3229). "
                          "Every phase after phase 1, repair rounds included. A rewording that "
                          "keeps the content is counted, and an edit that keeps the old text "
                          "inside the new one is not. – where the removal rows are –"),
    "unfoundedrewritesnotmodel": ("of those, not the model's", "live", True,
                                  "removals v3 (#3366): the rewrites without a finding whose new "
                                  "value is what the API runner's write-time normaliser writes "
                                  "from the old one (an enum alias to its permissible value, a "
                                  "date reshaped to its slot's range, a Person's mailto: id to a "
                                  "fragment on the record's own id; a British spelling and a "
                                  "resolver URL are no rewrite at all) or that sit at a path a "
                                  "curator's recorded amend disposition changed (#903) and, where "
                                  "phases are attributed, were made at write, after the last "
                                  "phase output (#3725). Reported "
                                  "only: counted in the row above, never subtracted. A form, not "
                                  "a provenance — a model that wrote the permissible value itself "
                                  "reads the same. – where the removal rows are –"),
    "unrecordedremovals": ("removals unrecorded in the report", "record", True,
                           "report_claims.removals_unrecorded (#1054): top-level slots the "
                           "phase-1 snapshot populated and the final full record does not, that "
                           "no `removed` row or removal sentence names. Top-level only, where "
                           "the rows above are per value; a finding only where the run was asked "
                           "for the dispositions table. – where the block read no snapshot"),
    "gc": ("GC label variants (reported)", "live", True,
           "reported-only; counted against the manifest naming declaration decided "
           "2026-08-22, so anachronistic for the v4 arm and same-day for 22c. For VOICE "
           "the count is the dataset's own PhysioNet title, lawful under the "
           "proper-noun carve-out (#674)"),
}


EXCLUDED_INVALID: dict[tuple[str, str], None] = {}   # (label, project) skipped as invalid; ordered, deduplicated


def load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


RECEIPT_KEYS = ("unreviewed", "unverified", "wrongchunk", "snippets", "noreceipt",
                "receiptable", "withreceipt", "neverreceipted", "addedafter")


def receipt_metrics(rcp: dict[str, Any]) -> dict[str, Any]:
    """The receipt row values for one record, or all None where the receipt
    was not checked — an unchecked receipt is not a measurement of zero."""
    if not rcp.get("checked"):
        return {k: None for k in RECEIPT_KEYS}
    from data_sheets_schema.canary import receipt_floors
    floors = receipt_floors(rcp)
    sn = rcp.get("snippets") or {}
    sl = rcp.get("slots") or {}
    receiptable = sl.get("receiptable")
    with_receipt = sl.get("with_receipt")
    # The stored `without_receipt` list is capped at 50 entries with the
    # remainder in `without_receipt_truncated`; #831's body divided by the
    # capped list and reported coverage at twice its real level. The two
    # integers are the definition, so subtract them where the block carries
    # them (every block on disk today, and they agree with the list
    # arithmetic on all of them) and keep the list only for a block that
    # predates the counters.
    if receiptable is not None and with_receipt is not None:
        noreceipt = int(receiptable) - int(with_receipt)
    else:
        noreceipt = (len(sl.get("without_receipt") or [])
                     + int(sl.get("without_receipt_truncated") or 0))
    # `never_receipted`/`added_after_receipt` are None, not 0, on a run with
    # no phase-1 snapshot to resolve the path against (#899) — the agentic
    # path writes none. A 0 would read as "reconciliation added nothing after
    # the receipt", which is not what an absent snapshot says.
    never = sl.get("never_receipted")
    added = sl.get("added_after_receipt")
    return {"unreviewed": floors["chunks unreviewed"],
            "unverified": floors["snippets unverified"],
            "wrongchunk": int(sn.get("adjacent") or 0) + int(sn.get("elsewhere") or 0)
            + int(sn.get("spans_boundary") or 0),
            "snippets": int(sn.get("total") or 0),
            "noreceipt": noreceipt,
            "receiptable": int(receiptable) if receiptable is not None else None,
            "withreceipt": int(with_receipt) if with_receipt is not None else None,
            "neverreceipted": int(never) if never is not None else None,
            "addedafter": int(added) if added is not None else None}


def removal_metrics(prov: Path, rec: dict[str, Any], *, include_basis: bool = False) -> dict[str, Any]:
    """The removal rows for one record (#2923): recomputed live from the
    phase-1 snapshot, the final record, the audit and the receipt
    (`removals.for_record`, read-only), and the report block's own
    unrecorded-removal count. None, never 0, where the snapshot, the audit,
    the receipt or the phase outputs a row needs is absent (#899, #3152)."""
    from data_sheets_schema.removals import for_record
    block = for_record(prov, record=rec)
    rc = rec.get("report_claims") or {}
    unrecorded = rc.get("removals_unrecorded_count") if rc.get("snapshot_checked") else None
    by_phase = block.get("unfounded_phase")
    result = {"unfoundedremovals": block["unfounded"],
            "unfoundedreconcile": by_phase.get("reconcile_full", 0) if by_phase is not None else None,
            "unfoundedrelocated": block.get("relocated_candidate_unfounded"),
            "receipteddeleted": (block["receipted"] or {}).get("deleted"),
            "lowconfidenceflat": block.get("flattened_low_confidence_unfounded"),
            "unfoundedrewrites": block.get("rewritten_unfounded"),
            "unfoundedrewritesnotmodel": block.get("rewritten_unfounded_not_model"),
            "unrecordedremovals": int(unrecorded) if unrecorded is not None else None}
    if include_basis:
        artifacts = block.get("artifacts") or {}
        result["removal_schema_basis"] = {
            "checked": block.get("checked"), "reason": block.get("reason"),
            "identifier_rules": artifacts.get("identifier_rules"),
            "person_slot_rules": artifacts.get("person_slot_rules"),
            "enum_alias_tables": artifacts.get("enum_alias_tables"),
        }
    return result


def run_metrics(label: str, project: str) -> dict[str, Any] | None:
    method = _method_for(label, project)
    core_dir = CONCAT / f"{method}_core" / label
    full = CONCAT / method / label / f"{project}_d4d.yaml"
    core = core_dir / f"{project}_d4d_core.yaml"
    prov = core_dir / f"{project}_provenance.yaml"
    if not (full.exists() and core.exists() and prov.exists()):
        return None
    rec = load(prov)
    if (rec.get("validation") or {}).get("passed") is False:
        # A record its own validation block declares invalid is evidence,
        # not an arm member (#1029: the AI_READI 2026-09-04f record, kept
        # and re-verdicted, sits under the same label prefix as the
        # retained VOICE and CHORUS canaries).
        EXCLUDED_INVALID[(label, project)] = None
        return None
    pc = rec.get("pair_consistency") or {}
    rc = rec.get("report_claims") or {}
    g = (rec.get("grounding") or {}).get("distinct") or {}

    # Current form instrument, with the run's recorded schema rules (#4216).
    # Keep the resolver basis: an unavailable pin explicitly falls back.
    form = form_facts(full, core, record=rec)

    def form_get(*keys: str) -> int | None:
        for k in keys:
            if form.get(k) is not None:
                v = form[k]
                return sum(v.values()) if isinstance(v, dict) else int(v)
        return None

    receipt_vals = receipt_metrics(rec.get("receipts") or {})
    from data_sheets_schema.receipts import populated_leaves
    leaves = len(populated_leaves(load(full)))
    return {
        "label": label,
        "form_schema_basis": form.get("schema_basis"),
        "leaves": leaves,
        **receipt_vals,
        **removal_metrics(core_dir / f"{project}_provenance.yaml", rec, include_basis=True),
        "ungrounded": g.get("absent"),
        "minted": g.get("minted_fragment"),
        "pair": pc.get("errors"),
        "report": len(rc.get("findings") or []) if rc else None,
        "claims_checked": rc.get("claims_checked"),
        "british": form_get("british_spellings"),
        "undeclared": form_get("undeclared_prefix_occurrences", "undeclared_prefixes"),
        "orgfrag": form_get("organisational_fragments"),
        "gc": form_get("gc_label_variant_occurrences", "gc_label_variants"),
        "runtime": (rec.get("model") or {}).get("agent_runtime"),
    }


def rubric_scores(prefix: str, project: str, rubric: str = "rubric10") -> list[dict[str, Any]]:
    out = []
    evals = EVAL_DIRS[rubric]
    if not evals.exists():
        return out
    for path in sorted(evals.glob(f"{project}_*_evaluation.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        label = str(d.get("label", ""))
        if label in arm_labels(prefix) and (label, project) not in EXCLUDED_INVALID:
            # The same exclusion as the metric table (#1052): an evaluation
            # of a record the Bases declare invalid is not an arm score.
            s = d.get("overall_score") or {}
            out.append({"label": label, "total": s.get("total_points"),
                        "max": s.get("max_points"),
                        "adjusted_max": s.get("adjusted_max_points"),
                        "pct": s.get("normalized_percentage"),
                        "evaluator": evaluator_key(d),
                        "generator": generator_model(label, project),
                        "file": path.name, "doc": d})
    return out


def generator_model(label: str, project: str) -> str | None:
    """The model the record's provenance says generated it (`model.model`,
    else `model.name`); None when the record or its model block is absent."""
    prov = CONCAT / f"{_method_for(label, project)}_core" / label / f"{project}_provenance.yaml"
    if not prov.exists():
        return None
    m = load(prov).get("model") or {}
    return m.get("model") or m.get("name") or None


def same_family_section(scores) -> list[str]:
    """Evaluator, generator and same-family status of every evaluation in the
    rubric tables (#2928), counted per (rubric, evaluator, generator)."""
    counts: dict[tuple[str, str, str], int] = {}
    for rubric, rs in scores.items():
        for arm in rs.values():
            for ss in arm.values():
                for s in ss:
                    key = (rubric, s.get("evaluator") or "unrecorded",
                           s.get("generator") or "unrecorded")
                    counts[key] = counts.get(key, 0) + 1
    lines = ["Evaluator and generator of the evaluations above, from each evaluation's "
             "model block and its record's provenance `model` (#2928):", "",
             "| rubric | evaluator | generator | same family | evaluations |",
             "|---|---|---|---|---|"]
    for (rubric, ev, gen), n in sorted(counts.items()):
        lines.append(f"| {rubric} | `{ev}` | `{gen}` | {same_family_label(ev, gen)} | {n} |")
    return lines + ["", SAME_FAMILY_DISCLAIMER, ""]


def collect() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """arm -> project -> [rep metrics]"""
    data: dict[str, dict[str, list[dict[str, Any]]]] = {}
    EXCLUDED_INVALID.clear()
    for key, _disp, prefix, _rt, _role in ARMS:
        data[key] = {}
        for p in PROJECTS:
            reps = [m for label in arm_labels(prefix) if (m := run_metrics(label, p))]
            data[key][p] = reps
    return data


def fmt(m: dict[str, Any], metric: str) -> str:
    v = m.get(metric)
    if v is None:
        return "–"
    # A finding is evidence the checker parsed something; only a 0 with zero
    # parsed claims is unmeasured rather than held (#684).
    if metric == "report" and v == 0 and (m.get("claims_checked") or 0) == 0:
        return f"{v}ᵘ"
    return str(v)


def measured(r: dict[str, Any], metric: str) -> bool:
    """Is this replicate's value a measurement? A report-findings 0 with zero
    parsed claims is unmeasured (#684) and must not enter a mean as a zero."""
    v = r.get(metric)
    if v is None:
        return False
    if metric == "report" and v == 0 and not r.get("claims_checked"):
        return False
    return True


def stats(reps: list[dict[str, Any]], metric: str) -> tuple[float, float, int] | None:
    """Mean and sample SD (ddof=1) over the *measured* replicates; None when
    there are none. n is always reported beside the figure: three replicates
    is a small sample, an SD on n=3 is a spread rather than a confidence
    interval, and with one outlier the SD is that outlier."""
    vals = [r[metric] for r in reps if measured(r, metric)]
    if not vals:
        return None
    mean = statistics.fmean(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return mean, sd, len(vals)


def cell(reps: list[dict[str, Any]], metric: str, role: str) -> str:
    """mean ± SD with the replicates in brackets; the baseline arm adds its
    per-project worst on the table's measurement basis. Canary gates read
    stored form blocks independently, so this live worst is not a stored
    threshold (#4217)."""
    raw = ",".join(fmt(r, metric) for r in reps)
    st = stats(reps, metric)
    if st is None:
        return f"– [{raw}]" if raw else "–"
    mean, sd, n = st
    # An SD needs two values; a single measured replicate gets its value and n.
    centre = f"{mean:.1f} ± {sd:.1f}" if n > 1 else f"{mean:.1f}"
    body = f"{centre} [{raw}]" + (f" (n={n})" if n != len(reps) else "")
    if role == "worst":
        body += f" worst {worst(reps, metric)}"
    return body


def worst(reps: list[dict[str, Any]], metric: str) -> str:
    """Per-project collapse for the baseline column: the worst value where
    the metric has a direction, the max (labelled as such in the header) for
    reported-only metrics that do not."""
    vals = [r[metric] for r in reps if r.get(metric) is not None]
    if not vals:
        return "–"
    w = max(vals)
    if metric == "report" and w == 0 and all((r.get("claims_checked") or 0) == 0 for r in reps):
        return f"{w}ᵘ"
    return str(w)


def pooled_receipts(reps: list[dict[str, Any]]) -> dict[str, Any]:
    """Receipt totals for an arm, pooled over its records.

    Pooled, not a mean of per-record rates: the receiptable denominator varies
    two- to three-fold within one arm (#902), and a mean of ratios would weight
    a 142-slot record like a 508-slot one. A key is summed only over the
    records that carry it, and stays None when none does — the never/added
    split needs a phase-1 snapshot the agentic path never wrote (#899), and 0
    there would assert something the arm did not measure.
    """
    out: dict[str, Any] = {"records": sum(1 for r in reps if r.get("receiptable") is not None)}
    for key in ("receiptable", "withreceipt", "neverreceipted", "addedafter",
                "snippets", "wrongchunk", "unverified", "unreviewed"):
        vals = [r[key] for r in reps if r.get(key) is not None]
        out[key] = sum(vals) if vals else None
    # The never/added split needs a phase-1 snapshot and `receiptable` does
    # not, so the two are carried by different sets of records in general
    # (#899). Dividing the snapshot-only numerator by the all-records
    # denominator would understate the rate with nothing on the page to say
    # so — the silent mis-measure #831's own body made once by dividing by a
    # capped list. The split gets its own denominator, over exactly the
    # records that carry it, and the count of those records travels with it.
    split = [r for r in reps if r.get("neverreceipted") is not None]
    out["split_records"] = len(split)
    out["split_receiptable"] = sum(r["receiptable"] for r in split
                                   if r.get("receiptable") is not None) or None
    return out


def _rate(num: Any, den: Any) -> str:
    """`n/d = p%`, or `–` where either side was not measured. A zero
    denominator is not 0% — it is nothing to divide."""
    if num is None or not den:
        return "–"
    return f"{num}/{den} = {100 * num / den:.1f}%"


def receipt_section(data) -> list[str]:
    lines = ["## Receipt coverage and attribution, pooled per arm (#831, #902)", "",
             "| arm | records | receiptable slots | with a receipt | never receipted | "
             "added after the receipt | snippets | not in the chunk cited |",
             "|---|---|---|---|---|---|---|---|"]
    for key, disp, _pfx, _rt, _role in ARMS:
        reps = [r for p in PROJECTS for r in data[key][p]]
        t = pooled_receipts(reps)
        if not t["records"]:
            continue
        lines.append(
            f"| {disp} | {t['records']} | {t['receiptable']} | "
            f"{_rate(t['withreceipt'], t['receiptable'])} | "
            f"{_rate(t['neverreceipted'], t['split_receiptable'])}"
            + (f" (of {t['split_records']} records)" if t["split_records"] not in (0, t["records"]) else "")
            + " | "
            f"{_rate(t['addedafter'], t['split_receiptable'])}"
            + (f" (of {t['split_records']} records)" if t["split_records"] not in (0, t["records"]) else "")
            + " | "
            f"{t['snippets'] if t['snippets'] is not None else '–'} | "
            f"{_rate(t['wrongchunk'], t['snippets'])} |")
    lines += ["",
              "Coverage **degree**, which the twelve v7 production reviewers read as a "
              "rule-15 violation on eight records and which is a property of the arm "
              "rather than of any one record (#902). The denominator is receiptable "
              "populated leaves: an entry receipt covers many leaves at once, so this is "
              "the strict leaf reading, and the exempt slots (runner-set, minted on an "
              "identifier the record carries, commentary) are outside it. Zero "
              "`not_in_bundle` verdicts were returned anywhere on the v7 production arm, "
              "so what these rows measure is how much of a record the receipt reaches, "
              "not whether its values are supported.", "",
              "The never/added split (#807) says which half of the gap the protocol could "
              "have closed: a leaf that resolves in the phase-1 snapshot was there to be "
              "receipted and was not, while one the snapshot does not carry was added by "
              "reconciliation or repair, which have no receipt route at all (#742). It "
              "needs that snapshot, so an agentic arm shows `–` and not 0. Its two rates "
              "are taken over the receiptable leaves of the records that carry it, "
              "which is every checked record of an arm or none of them today; where "
              "an arm ever mixes the two the row says how many records the split "
              "covers, because a numerator from one set of records over a "
              "denominator from another is not a rate.", "",
              "`not in the chunk cited` is attribution precision, reported and never "
              "gated (#763): the snippet is verbatim in the bundle, in a chunk other than "
              "the one the receipt names. It is an API-path number — the agentic protocol "
              "names chunk ids from the manifest it read, the API path infers them from "
              "`[cNNN]` marker lines in the cached bundle, and the marker side was checked "
              "byte-for-byte on the CM4AI canary and found correct (#873), so what the "
              "rate measures is the model mis-citing, usually one chunk early.", ""]
    return lines


# Arms whose records are not replicates of one configuration: the v7 API
# canaries are five runs under four labels, each label its own settings (#777).
NOT_REPLICATES = {"v7api": "five canary runs under four labels, each label its own settings (#777)"}


def replicate_structure_section(data) -> list[str]:
    """Structural agreement across each arm x project's replicates (#2932):
    which slots every, some or no replicate fills, and how far the entry
    counts of nested lists held by all of them disagree. The records are the
    ones the metric table counts — `collect()`'s labels, less
    EXCLUDED_INVALID."""
    from data_sheets_schema.replicate_structure import compare_structure, dataset_slots, summarize
    slots = dataset_slots()
    kinds = {k: sum(1 for v in slots.values() if v == k) for k in ("nested", "list", "scalar")}
    rows, wide, outside, totals = [], [], set(), {}
    for key, disp, _pfx, _rt, _role in ARMS:
        if key in NOT_REPLICATES:
            rows.append(f"| {disp} | – | – | not replicates: {NOT_REPLICATES[key]} | | | | |")
            continue
        tot: dict[str, int] = {}
        for p in PROJECTS:
            reps = data[key][p]
            if len(reps) < 2:
                rows.append(f"| {disp} | {p} | {len(reps)} | – | – | – | – | – |")
                continue
            recs = {_rep_tag(r["label"]): load(CONCAT / _method_for(r["label"], p) / r["label"] / f"{p}_d4d.yaml")
                    for r in reps}
            result = compare_structure(recs, slots)
            s = summarize(result)
            outside.update(s["outside_universe"])
            vals = {"records": len(reps), "all": s["all"], "some": s["some"], "none": s["none"],
                    "identical": s["identical"], "nested_in_all": s["nested_in_all"],
                    "nested_counted": s["nested_counted"], "differ": len(s["counts_differ"]),
                    "ge2": len(s["ratio_ge_2"]), "key": s["joined_by_key"],
                    "pos": s["joined_by_position"], "unaligned": s["unaligned"]}
            for k, v in vals.items():
                tot[k] = tot.get(k, 0) + v
            names = ", ".join(f"`{n}` ({c}/{len(reps)})" for n, c in s["intermittent"].items()) or "none"
            rows.append(_structure_row(disp, p, vals, names))
            if s["ratio_ge_2"]:
                wide.append(f"| {disp} | {p} | " + ", ".join(
                    f"`{n}` " + "/".join(str(c) for c in result["slots"][n]["counts"].values())
                    for n in s["ratio_ge_2"]) + " |")
        if tot:
            totals[key] = tot
            rows.append(_structure_row(f"**{disp}**", "**all projects**", tot, ""))
    prod = [totals[k] for k in ("v7prod", "v8prod") if k in totals]
    both = {k: sum(t[k] for t in prod) for k in ("nested_in_all", "nested_counted", "differ", "ge2", "some")}
    return ["## Replicate structure (#2932)", "",
            f"Per arm × project, over class `Dataset`'s {len(slots)} induced slots less "
            f"`source_caveats` ({kinds['nested']} class-ranged, {kinds['list']} lists of values, "
            f"{kinds['scalar']} scalar; `replicate_structure.dataset_slots`, today's merged "
            "schema for every arm). A replicate fills a slot when its value is not null, `\"\"`, "
            "`[]` or `{}`. **all / some / none**: slots filled in every, in some but not every "
            "(intermittent), and in no replicate; **identical**: of the slots filled in all, "
            "those whose key-sorted, whitespace-collapsed YAML is equal in every replicate. "
            "**Nested in all**: class-ranged slots filled in every replicate; **with a count**: "
            "those that are a list in every replicate — a single object has no item count and "
            "is outside the next two columns; **counts differ** and **max/min ≥ 2** are of those. "
            "**Entries joined**: list entries of those slots aligned one to one across each pair "
            "of replicates, by identity key (`receipts._entry_key`: the first `id`, `name`, "
            "`title`, … an entry carries) or, for a keyless entry, by its index "
            "(`joined_by_position`, #908's caveat: position is no evidence of identity), and "
            "the entries neither joined, counted on both sides.", "",
            "| arm | project | records | all / some / none | identical | nested in all: with a "
            "count / counts differ / max/min ≥ 2 | entries joined by key / by position / "
            "unaligned | intermittent slots (replicates filling it) |",
            "|---|---|---|---|---|---|---|---|", *rows, "",
            "Class-ranged slots filled in every replicate whose entry counts reach max/min ≥ 2 "
            "(counts per replicate, in label order):", "",
            "| arm | project | slots |", "|---|---|---|", *(wide or ["| – | – | none |"]), "",
            "Differences from the other measures. fig12 (#2303, `scripts/figures/"
            "fig12_replication_stability.py`, not on main) uses the same slot universe, "
            "emptiness and canonical form, over the 24 records of the frozen 2026-09-12 "
            "rescore manifest — exactly the v7 and v8 production records here — and compares "
            "whole values only (it also splits scalar strings into long text by observed "
            "length, which changes no count here). Its nested cells filled in all three "
            "include the single objects this table sets apart"
            + (f": over the v7 and v8 production arms, {both['nested_in_all']} such cells, of "
               f"which {both['nested_counted']} are lists with an item count, {both['differ']} "
               f"of those differing in count and {both['ge2']} reaching max/min ≥ 2; "
               f"{both['some']} intermittent cells" if len(prod) == 2 else "") + ". "
            "`runs.compare` counts record keys, so a key holding null or `[]` is present "
            "there and absent here. Only top-level slots are compared in this table; the "
            "structure below them is the next one (#3337). Every arm shown ran under an "
            "earlier schema release than today's, so a slot its release did not declare "
            "counts as unfilled. Record keys holding a value "
            "outside the universe: "
            + (", ".join(f"`{k}`" for k in sorted(outside)) if outside else "none") + ".", ""]


_RECEIPT_CACHE: dict[tuple[str, str, str], tuple[dict[str, int] | None, dict[str, Any] | None, str | None]] = {}


def _replicate_receipt(label: str, project: str) -> tuple[dict[str, int] | None, dict[str, Any] | None, str | None]:
    """(`replicate_structure.verified_by_path` of one record's coverage
    receipt, its phase-1 snapshot, why the snapshot is unusable). The first
    is None where it wrote no receipt or its chunk texts cannot be
    recovered; the second is None where the run left no usable snapshot;
    the third is None unless a snapshot is present and unusable
    (`receipts.phase1_snapshot_state`: a parse error, bytes that are not
    UTF-8, an empty document, a list or a scalar), so an absent snapshot
    (the agentic path writes none) is told apart from one that cannot be
    read (#3954, the #1124 precedent). Memoised."""
    key = (str(CONCAT), label, project)
    if key in _RECEIPT_CACHE:
        return _RECEIPT_CACHE[key]
    from data_sheets_schema.receipts import load_receipt, phase1_snapshot_state
    from data_sheets_schema.replicate_structure import record_chunk_texts, verified_by_path
    core_dir = CONCAT / f"{_method_for(label, project)}_core" / label
    receipt = core_dir / f"{project}_coverage_receipt.yaml"
    prov = core_dir / f"{project}_provenance.yaml"
    out: tuple[dict[str, int] | None, dict[str, Any] | None, str | None] = (None, None, None)
    if receipt.exists() and prov.exists():
        try:
            rec = load_receipt(receipt)
        except (OSError, ValueError, yaml.YAMLError):
            rec = None
        if rec is not None:
            texts, _basis = record_chunk_texts(load(prov).get("inputs") or {}, ROOT)
            if texts is not None:
                state, _path, snapshot, why = phase1_snapshot_state(receipt)
                out = (verified_by_path(rec, texts), snapshot,
                       (why or "unusable") if state == "unusable" else None)
    _RECEIPT_CACHE[key] = out
    return out


def _replicate_verified(label: str, project: str) -> dict[str, int] | None:
    """`replicate_structure.verified_by_slot` of one record's coverage
    receipt, or None where it wrote none or its chunk texts cannot be
    recovered — no receipt is not a receipt of nothing. Summed from
    `_replicate_receipt`'s per-path counts, which is what `verified_by_slot`
    does."""
    from data_sheets_schema.replicate_structure import top_slot
    paths, _snapshot, _unusable = _replicate_receipt(label, project)
    if paths is None:
        return None
    out: dict[str, int] = {}
    for path, n in paths.items():
        out[top_slot(path)] = out.get(top_slot(path), 0) + n
    return dict(sorted(out.items()))


def omission_candidate_section(data) -> list[str]:
    """Receipt-backed omission candidates among each arm x project's
    intermittent slots (#3335, #2932 1(c)), over the records the replicate
    structure table compares."""
    from data_sheets_schema.replicate_structure import (
        CANDIDATE, COMMENTARY, COMMENTARY_KEYS, UNMEASURED, compare_structure, dataset_slots,
        omission_candidates,
    )
    slots = dataset_slots()
    rows, totals = [], {}
    for key, disp, _pfx, _rt, _role in ARMS:
        if key in NOT_REPLICATES:
            continue
        tot = {"some": 0, CANDIDATE: 0, "not_candidate": 0, UNMEASURED: 0, COMMENTARY: 0}
        measured_any = False
        for p in PROJECTS:
            reps = data[key][p]
            if len(reps) < 2:
                continue
            tags = {_rep_tag(r["label"]): r["label"] for r in reps}
            recs = {t: load(CONCAT / _method_for(lab, p) / lab / f"{p}_d4d.yaml") for t, lab in tags.items()}
            result = compare_structure(recs, slots)
            oc = omission_candidates(result, {t: _replicate_verified(lab, p) for t, lab in tags.items()})
            n = len(oc["slots"])
            tot["some"] += n
            for k, v in oc["counts"].items():       # an unmeasured group adds its unmeasured slots,
                tot[k] += v                         # so the arm's row sums to its intermittent total
            if not oc["measured"]:
                rows.append(f"| {disp} | {p} | {n} | – | – | – |")
                continue
            measured_any = True
            c = oc["counts"]
            names = ", ".join(
                f"`{name}` (filled {len(s['filled_by'])}/{len(recs)}, receipted in {', '.join(s['receipted_in'])})"
                for name, s in oc["slots"].items() if s["status"] == CANDIDATE) or "none"
            per = " · ".join(f"{t} {len(v)}" + (f" ({', '.join(f'`{x}`' for x in v)})" if v else "")
                             for t, v in oc["per_replicate"].items())
            rows.append(f"| {disp} | {p} | {n} | {c[CANDIDATE]} / {c['not_candidate']} / {c[UNMEASURED]} / "
                        f"{c[COMMENTARY]} | {names} | {per} |")
        if measured_any:
            totals[key] = tot
            rows.append(f"| **{disp}** | **all projects** | {tot['some']} | {tot[CANDIDATE]} / "
                        f"{tot['not_candidate']} / {tot[UNMEASURED]} / {tot[COMMENTARY]} | | |")
    return ["### Receipt-backed omission candidates (#3335)", "",
            "Per arm × project, the intermittent slots of the replicate-structure table above. A slot is a **candidate** "
            "when at least one replicate that fills it carries a coverage-receipt snippet for it that "
            "verifies in the chunk it cites — the verification `receipts.check` counts as `verified`, "
            "after the receipt is inverted by slot (`receipts.claim_receipts`) and each receipt path "
            "is read at its top-level slot. A path through a key the receipts instrument exempts as "
            "commentary or runner-set (`receipts.EXEMPT_LEAVES` and `EXEMPT_SLOTS`: "
            + ", ".join(f"`{k}`" for k in COMMENTARY_KEYS) + ") counts for nothing, and an "
            "intermittent slot that is one of them is **commentary**: counted, not classified, "
            "never an omitted candidate. Each receipt is checked against the bytes its record hashed: the "
            "bundle on disk where it still hashes to the record's, else the committed version that "
            "does (`provenance.committed_bytes_for`), chunked under the record's own rule "
            "(`replicate_structure.record_chunk_texts`). **not**: every replicate that fills it has "
            "a receipt and none verifies a snippet for it; **unmeasured**: none does and some "
            "filling replicate has no readable receipt. The four counts sum to the intermittent "
            "slots. **Omitted candidates per record**: the "
            "candidate slots each replicate leaves empty. `–` exactly where no replicate of the "
            "group has a readable receipt — the arms whose procedure wrote none — and not 0; such a "
            "group's slots are unmeasured (or commentary) and are added to its arm's total as such. "
            "A group where some replicate has a readable receipt is shown in full, its unmeasured "
            "slots included. A candidate says "
            "the bundle supports the slot in one replicate's reading, not that leaving it out was "
            "wrong; only top-level slots are compared here, list entries one level down in the "
            "table after this one (#3880).", "",
            "| arm | project | intermittent | candidates / not / unmeasured / commentary | candidate slots "
            "(replicates filling it; receipted in) | omitted candidates per record |",
            "|---|---|---|---|---|---|", *(rows or ["| – | – | – | – | – | – |"]), ""]


def _replicate_groups(data, key: str):
    """(project, replicate tag -> label, tag -> full record) for each of one
    arm's projects the replicate-structure table compares: at least two
    records."""
    for p in PROJECTS:
        reps = data[key][p]
        if len(reps) < 2:
            continue
        tags = {_rep_tag(r["label"]): r["label"] for r in reps}
        yield p, tags, {t: load(CONCAT / _method_for(lab, p) / lab / f"{p}_d4d.yaml") for t, lab in tags.items()}


def _by_basis(v: dict[str, int]) -> str:
    return " / ".join(str(v[b]) for b in ("single", "key", "position"))


def nested_structure_section(data) -> list[str]:
    """Structure below the top level (#3337): `replicate_structure.compare_nested`
    over the replicate-structure table's groups, every count by join basis."""
    from data_sheets_schema.replicate_structure import (
        BASES, compare_nested, compare_structure, dataset_slots, summarize_nested,
    )
    slots = dataset_slots()
    rows, top = [], []
    for key, disp, _pfx, _rt, _role in ARMS:
        if key in NOT_REPLICATES:
            continue
        tot = {k: {b: 0 for b in BASES} for k in ("compared", "one_side", "differ")}
        unaligned, one_side_by_path, groups = 0, {}, 0
        for p, _tags, recs in _replicate_groups(data, key):
            nested = compare_nested(recs, compare_structure(recs, slots))
            s = summarize_nested(nested)
            groups += 1
            rows.append(f"| {disp} | {p} | {len(nested['slots'])} | {s['paths']} | {_by_basis(s['compared'])} | "
                        f"{_by_basis(s['one_side'])} | {_by_basis(s['differ'])} | {s['unaligned']} |")
            for k in tot:
                for b in BASES:
                    tot[k][b] += s[k][b]
            unaligned += s["unaligned"]
            for path, row in nested["paths"].items():
                cell = one_side_by_path.setdefault(path, {b: 0 for b in BASES})
                for b, c in row["by_basis"].items():
                    cell[b] += c["one_side"]
        if not groups:
            continue
        rows.append(f"| **{disp}** | **all projects** | | | {_by_basis(tot['compared'])} | "
                    f"{_by_basis(tot['one_side'])} | {_by_basis(tot['differ'])} | {unaligned} |")
        ranked = sorted(((sum(c.values()), path, c) for path, c in one_side_by_path.items() if sum(c.values())),
                        key=lambda x: (-x[0], x[1]))[:5]
        top.append(f"| {disp} | " + (", ".join(
            f"`{path}` {n} ({', '.join(f'{b} {c[b]}' for b in BASES if c[b])})" for n, path, c in ranked)
            or "none") + " |")
    return ["### Below the top level (#3337)", "",
            "Per arm × project, the class-ranged slots filled in every replicate (the table's "
            "**nested in all**, single objects included), walked pair by pair of replicates "
            "(`replicate_structure.compare_nested`): an object by field, a list by the one-to-one "
            "join the table above counts, recursively; `source_caveats` is skipped at any depth, as "
            "at the top level. At each path below the top level (`creators[*]`, "
            "`creators[*].affiliations[*].name`, `license.name`), every joined pair of values of "
            "which at least one is filled is one **comparison**: equal on the canonical form, "
            "**differ**, or **in one only** — filled in one replicate's entry and empty in the "
            "other's. A comparison is counted under its **join basis**, the weakest join on the "
            "way down: **single** (one object on each side, nothing to choose between), **key** "
            "(list entries joined by `receipts._entry_key`) or **position** (keyless entries "
            "joined by index; #908's caveat: no evidence of identity, so a position-basis "
            "difference may be two different entries rather than one entry that changed). The "
            "bases are never pooled. An entry and each of its fields are counted at their own "
            "paths, so the counts are path × pair, not values. **Entries unaligned**: entries a "
            "join left unpaired at any depth, counted on both sides, nothing below them compared; "
            "for the list slots with a count this includes the table's own unaligned column.", "",
            "| arm | project | slots walked | paths | comparisons single / key / position | in one only "
            "single / key / position | differ single / key / position | entries unaligned |",
            "|---|---|---|---|---|---|---|---|", *(rows or ["| – | – | – | – | – | – | – | – |"]), "",
            "Paths most often filled in one replicate's joined value and empty in the other's, per "
            "arm over its projects (in-one-only comparisons, then by join basis):", "",
            "| arm | paths |", "|---|---|", *(top or ["| – | none |"]), ""]


def _replicate_resolved(tags: dict[str, str], project: str,
                        recs: dict[str, Any]) -> tuple[dict[str, dict[str, int] | None], dict[str, int]]:
    """(replicate tag -> its verified receipt paths resolved into its final
    record, `replicate_structure.resolve_verified`'s `paths`, or None where
    it has no readable receipt; basis -> the group's verified snippets,
    resolved or not) for one arm x project group."""
    from data_sheets_schema.replicate_structure import resolve_verified
    resolved: dict[str, dict[str, int] | None] = {}
    basis: dict[str, int] = {}
    for t, lab in tags.items():
        paths, snapshot, unusable = _replicate_receipt(lab, project)
        if paths is None:
            resolved[t] = None
            continue
        rv = resolve_verified(paths, snapshot, recs[t], unusable=unusable)
        resolved[t] = rv["paths"]
        for b, n in rv["basis"].items():
            basis[b] = basis.get(b, 0) + n
    return resolved, basis


def entry_omission_section(data) -> list[str]:
    """Receipt-backed omission candidates among list entries (#3880 (1)),
    over the groups the replicate-structure table compares."""
    from data_sheets_schema.replicate_structure import (
        CANDIDATE, NOT_CANDIDATE, UNMEASURED, compare_structure, dataset_slots, entry_omission_candidates,
    )
    slots = dataset_slots()
    rows = []
    for key, disp, _pfx, _rt, _role in ARMS:
        if key in NOT_REPLICATES:
            continue
        tot = {"n": 0, "keyless": 0, CANDIDATE: 0, NOT_CANDIDATE: 0, UNMEASURED: 0}
        measured_any = False
        for p, tags, recs in _replicate_groups(data, key):
            resolved, basis = _replicate_resolved(tags, p, recs)
            eo = entry_omission_candidates(recs, compare_structure(recs, slots), resolved)
            n = len(eo["entries"])
            tot["n"] += n
            tot["keyless"] += eo["keyless"]
            for k, v in eo["counts"].items():
                tot[k] += v
            if not eo["measured"]:
                rows.append(f"| {disp} | {p} | {n} | – | {eo['keyless']} | – | – |")
                continue
            measured_any = True
            c = eo["counts"]
            rows.append(f"| {disp} | {p} | {n} | {c[CANDIDATE]} / {c[NOT_CANDIDATE]} / {c[UNMEASURED]} | "
                        f"{eo['keyless']} | " + (", ".join(f"{b} {v}" for b, v in sorted(basis.items())) or "none")
                        + " | " + " · ".join(f"{t} {v}" for t, v in eo["per_replicate"].items()) + " |")
        if measured_any:
            rows.append(f"| **{disp}** | **all projects** | {tot['n']} | {tot[CANDIDATE]} / {tot[NOT_CANDIDATE]} / "
                        f"{tot[UNMEASURED]} | {tot['keyless']} | | |")
    return ["### Receipt-backed omission candidates among list entries (#3880)", "",
            "One level down from the table above, over the list-valued class-ranged slots every "
            "replicate fills (the replicate-structure table's **with a count**): the entries some "
            "replicates carry and others do not. An entry is identified by `receipts._entry_key` "
            "and its occurrence among the entries sharing that key — the keyed join the "
            "replicate-structure table counts — so an entry is missing from a replicate exactly "
            "where that join leaves it unpaired. A **keyless** entry has no identity to be missing "
            "by (a position join is no evidence of one, #908): counted, never classified. An entry "
            "is a **candidate** when a replicate carrying it has a verified receipt snippet (as in "
            "the table above) on that entry or below it; a receipt on the list itself covers only "
            "the list (#721). A receipt path is followed into the final record by identity where "
            "the run left a phase-1 snapshot (`receipts.remap_path`, #899: `same`, `by_<key>`, "
            "`by_overlap`, `same_key_stripped`), read as written where it left none "
            "(`no_snapshot`, the agentic path: an index join), is not followed at all where the "
            "snapshot is present but unusable — a parse error, bytes that are not UTF-8, an empty "
            "document, a list or a scalar (`snapshot_unusable`, #1124: no index join stands in for "
            "it, so that replicate counts as having no readable receipt here), and resolves nowhere where its "
            "entry or leaf is gone (`entry_dropped`, `leaf_dropped`, `ambiguous`) or the snapshot "
            "never had it (`not_in_snapshot`), and resolves nowhere as `unresolved` where the path "
            "does not parse as a slot path or an index step finds a list in the snapshot and no "
            "list in the final record — the parse is tested first, so an unparseable path is "
            "`unresolved` with or without a snapshot, never `no_snapshot`; the reverse (an object "
            "in the snapshot, a list in the final record) is `leaf_dropped` at a key step and "
            "`not_in_snapshot` at an index step (#3997); "
            "**receipt paths by basis** counts the group's "
            "verified snippets, resolved or not. **not** and **unmeasured** as above, and `–` "
            "exactly where no replicate of the group has a readable receipt. **Omitted candidate "
            "entries per record**: how many candidate entries each replicate lacks. This table "
            "classifies the entries of top-level lists; the fields of objects and the entries of "
            "deeper lists are in the table after this one (#3934).", "",
            "| arm | project | entries in some replicates | candidates / not / unmeasured | keyless "
            "entries | receipt paths by basis | omitted candidate entries per record |",
            "|---|---|---|---|---|---|---|", *(rows or ["| – | – | – | – | – | – | – |"]), ""]


def nested_omission_section(data) -> list[str]:
    """Receipt-backed omission candidates below the first level (#3934): the
    fields of objects and the entries of nested lists, over the groups the
    replicate-structure table compares."""
    from data_sheets_schema.replicate_structure import (
        CANDIDATE, COMMENTARY, COMMENTARY_KEYS, EXCLUDED_SLOTS, NESTED_KINDS, NOT_CANDIDATE, UNMEASURED,
        compare_structure, dataset_slots, nested_omission_candidates,
    )
    slots = dataset_slots()
    shown = {"field": (CANDIDATE, NOT_CANDIDATE, UNMEASURED, COMMENTARY),     # an entry is never commentary
             "entry": (CANDIDATE, NOT_CANDIDATE, UNMEASURED)}
    rows, top = [], []
    # The legend names the keys the walk reads, not a wildcard (#4434):
    # `conforms_to_standard` matches `conforms_to_*` and is classified.
    skipped = ", ".join(f"`{k}`" for k in EXCLUDED_SLOTS)
    commentary = ", ".join(f"`{k}`" for k in COMMENTARY_KEYS if k not in EXCLUDED_SLOTS)

    def cells(counts: dict[str, dict[str, int]], measured: bool) -> list[str]:
        return [c for kind in NESTED_KINDS for c in (
            str(sum(counts[kind].values())),
            " / ".join(str(counts[kind][s]) for s in shown[kind]) if measured else "–")]

    for key, disp, _pfx, _rt, _role in ARMS:
        if key in NOT_REPLICATES:
            continue
        tot = {kind: dict.fromkeys(shown["field"], 0) for kind in NESTED_KINDS}
        unread = {"keyless": 0, "values": 0}
        measured_any, paths = False, {}
        for p, tags, recs in _replicate_groups(data, key):
            resolved, _basis = _replicate_resolved(tags, p, recs)
            no = nested_omission_candidates(recs, compare_structure(recs, slots), resolved)
            for kind in NESTED_KINDS:              # an unmeasured group adds its rows as unmeasured
                for s, v in no["counts"][kind].items():
                    tot[kind][s] += v
            for k in unread:
                unread[k] += no[k]
            left = f"{no['keyless']} / {no['values']}"
            if not no["measured"]:
                rows.append("| " + " | ".join([disp, p, *cells(no["counts"], False), left, "–"]) + " |")
                continue
            measured_any = True
            for r in no["rows"]:
                if r["status"] == CANDIDATE:
                    paths[r["path"]] = paths.get(r["path"], 0) + 1
            per = " · ".join(f"{t} {v['field']} + {v['entry']}" for t, v in no["per_replicate"].items())
            rows.append("| " + " | ".join([disp, p, *cells(no["counts"], True), left, per]) + " |")
        if measured_any:
            rows.append(f"| **{disp}** | **all projects** | " + " | ".join(cells(tot, True))
                        + f" | {unread['keyless']} / {unread['values']} | |")
            ranked = sorted(paths.items(), key=lambda x: (-x[1], x[0]))[:5]
            top.append(f"| {disp} | " + (", ".join(f"`{path}` {n}" for path, n in ranked) or "none") + " |")
    return ["### Receipt-backed omission candidates below the first level (#3934)", "",
            "Below the table above, from the same class-ranged slots every replicate fills — a slot "
            "holding one object as well as one holding a list — the fields and list entries that "
            "some replicates carry and others do not, wherever a chain of steps identifies them in "
            "every replicate (`replicate_structure.nested_omission_candidates`): a "
            "**single-object** step, into a field of an object every replicate holds there, and a "
            "**keyed-list** step, into an entry every replicate holds, identified as in the table "
            "above. A **field** is filled, as in the replicate-structure table, in some "
            "replicates' object and not in all. Of the keys the receipts instrument exempts (as in "
            "the omission-candidates table, #3335), " + skipped + " is skipped at any depth, as in "
            "the paths below the top level (#3337), and a field that is one of the others (" + commentary
            + ") is **commentary**: counted, never classified, never an omitted candidate; every "
            "other field is classified. A **nested entry** is an identified object in a list below "
            "the first level that some replicates' lists carry and others' do not. A keyed identity "
            "is that key's value as `receipts._entry_key` reads it, as in the table above: stripped "
            "of surrounding whitespace, and a resolver URL of a declared prefix read as its CURIE "
            "(`https://doi.org/10.x/y` and `doi:10.x/y` are one entry). Nothing else is "
            "normalised: an entry one replicate names otherwise, or identifies by another key (an "
            "affiliation by its ROR `id` in one replicate and by its `name` in another), reads as "
            "two entries, each missing from the other. Below the first "
            "level only objects are identified: a **keyless** object has no identity to be missing "
            "by (#908), and a string entry is a **value** whose only identity is its exact text — "
            "mostly the prose items of a list of values (`ip_restrictions.restrictions`, "
            "`version_access.versions_available`), where one replicate's rewording of another's "
            "item would read as two items, each missing from the other. Both are counted, never "
            "classified, as the items of a top-level list of values are not; whether such a list "
            "is filled at all is a field like any other. Nothing is read below a keyless entry at "
            "any level, below a field or entry some replicate lacks (it is a row, here or in the "
            "table above), or below a value that is a list in one replicate and not in another. A "
            "field or entry is a **candidate** when a replicate carrying it has a verified receipt "
            "path, resolved into its final record as in the table above, on it or below it at its "
            "own path in that replicate: a receipt credits it only through the same chain of "
            "entries, and one on an object or entry above it, or on the list holding an entry "
            "(#721), does not. **not**, **unmeasured** and `–` as above. **Omitted "
            "candidates per record**: the candidate fields + candidate nested entries each "
            "replicate lacks, each in an object or list that replicate holds.", "",
            "| arm | project | fields in some replicates | candidates / not / unmeasured / commentary "
            "| nested entries in some replicates | candidates / not / unmeasured | keyless / value "
            "entries | omitted candidates per record (fields + entries) |",
            "|---|---|---|---|---|---|---|---|", *(rows or ["| – | – | – | – | – | – | – | – |"]), "",
            "Paths with the most candidates, fields and nested entries together, per arm over its "
            "projects (`[*]` for each keyed-list step):", "",
            "| arm | paths |", "|---|---|", *(top or ["| – | none |"]), ""]


def receipted_where_empty_section(data) -> list[str]:
    """Slots a replicate leaves empty and yet receipts (#3880 (2)), beside
    what the removals block (#2923) says of that replicate's slot."""
    from data_sheets_schema.removals import for_record
    from data_sheets_schema.replicate_structure import (
        compare_structure, dataset_slots, receipted_where_empty, removal_status,
    )
    slots = dataset_slots()
    rows, status_tot, status_reps = [], {}, {}
    for key, disp, _pfx, _rt, _role in ARMS:
        if key in NOT_REPLICATES:
            continue
        for p, tags, recs in _replicate_groups(data, key):
            result = compare_structure(recs, slots)
            verified = {t: _replicate_verified(lab, p) for t, lab in tags.items()}
            if all(v is None for v in verified.values()):
                continue
            found = receipted_where_empty(result, verified)
            cells = []
            for name, reps in found.items():
                r = result["slots"][name]
                said = []
                for t in reps:
                    lab = tags[t]
                    prov = CONCAT / f"{_method_for(lab, p)}_core" / lab / f"{p}_provenance.yaml"
                    st = removal_status(for_record(prov, record=load(prov)), name)
                    status_tot[st] = status_tot.get(st, 0) + 1
                    status_reps.setdefault(st, set()).add((key, p, t))
                    said.append(f"{t} {verified[t][name]}, {st}")
                cells.append(f"`{name}` (filled {r['n_present']}/{r['n_replicates']}; {'; '.join(said)})")
            rows.append(f"| {disp} | {p} | {len(found)} | " + (", ".join(cells) or "none") + " |")
    return ["### Receipted where empty (#3880)", "",
            "Per arm × project with a readable receipt, the slots of the replicate-structure table "
            "that some replicate leaves empty (intermittent or absent) although its own receipt "
            "carries a snippet for the slot verified in the chunk it cites, as in the tables above "
            "(commentary keys aside). The receipt was written against the phase-1 record, so the "
            "value was receipted and is not in the final record. Beside each replicate: its "
            "verified snippets for the slot, then what the removals rows (#2923, "
            "`removals.for_record`, read-only) list for that replicate at the slot or below it — "
            "**deleted** or **flattened** (a phase-1 value removed by reconcile or repair, counted "
            "in the removal rows of the metric table, not again here), **no removal row** (the "
            "removals instrument found no phase-1 value there that went: the receipt names a path "
            "phase 1 did not fill), **rows truncated** (none among the listed rows, which are "
            "capped), or **removals unchecked** (no phase-1 snapshot to read removals against — "
            "the agentic path). A group none of whose replicates has a readable receipt is not "
            "listed.", "",
            "| arm | project | slots | slot (replicates filling it; per receipting replicate: verified "
            "snippets, removals) |",
            "|---|---|---|---|", *(rows or ["| – | – | – | – |"]), "",
            "Receipting replicates by removals status (distinct arm × project × replicate; one "
            "with slots of two statuses is counted under each): "
            + (", ".join(f"{k} {len(v)}" for k, v in sorted(status_reps.items())) or "none")
            + ". Slot × replicate instances by removals status: "
            + (", ".join(f"{k} {v}" for k, v in sorted(status_tot.items())) or "none") + ".", ""]


SOURCE_MANIFEST = Path("data/preprocessed/source_manifest.yaml")
CRATE_MANIFEST = Path("data/ro-crate_packages/crate_manifest.yaml")
#: The rubric10 sub-elements a release-level slot answers: (label, element
#: id, position within the element, the opening of its name). Matched by
#: position and checked by name, so a renamed sub-element is read as absent
#: rather than as another one.
RELEASE_SUBELEMENTS = (("E1.1", 1, 1, "Persistent Identifier"), ("E3.1", 3, 1, "License Terms"),
                       ("E6.1", 6, 1, "Dataset Version Number"), ("E10.2", 10, 2, "Citation and DOI"))


def _release_facts(inv: dict[str, Any]) -> tuple:
    """What a corpus holds on release evidence: its licence/DUA/IRB sources
    and its release records, crate included. Tier 1 is apart — a ranking the
    manifest declares, not a document the corpus holds."""
    return (tuple((k, tuple(e["source_id"] for e in v)) for k, v in inv["governance"].items()),
            tuple(e["source_id"] for e in inv["release_records"]), inv["crate_in_document_corpus"])


def _pinned_manifest_rows(data, today: bytes, crate: bytes | None) -> list[str]:
    """Per arm, the source-manifest version its records pinned
    (`inputs.source_manifest`), recovered from git by that hash, and whether
    the inventory under it equals today's."""
    from data_sheets_schema import release_inventory as ri
    from data_sheets_schema.provenance import GitUnavailable, committed_bytes_for
    rows = []
    for key, disp, _pfx, _rt, _role in ARMS:
        pins: dict[tuple, list[str]] = {}
        for p in PROJECTS:
            for r in data[key][p]:
                # Every collected record has one (`run_metrics` requires it);
                # a metrics row with no record behind it pins nothing.
                prov = (CONCAT / f"{_method_for(r['label'], p)}_core" / r["label"] / f"{p}_provenance.yaml"
                        if r.get("label") else None)
                if prov is None or not prov.exists():
                    continue
                sm = (load(prov).get("inputs") or {}).get("source_manifest") or {}
                pins.setdefault((sm.get("path"), sm.get("md5"), sm.get("sha256")), []).append(p)
        if not pins:
            continue
        for (path, md5, sha), projects in sorted(pins.items(), key=lambda kv: str(kv[0])):
            named = f"`{(md5 or sha or '')[:12]}` ({len(projects)} records)" if (md5 or sha) else \
                f"no hash recorded ({len(projects)} records)"
            # Git is asked only for a path and a hash; without either there is
            # nothing to recover, and the note says which is missing (#3903).
            if not path:
                rows.append(f"| {disp} | {named} | – | – | "
                            + ("the records pinned a hash but no source-manifest path" if (md5 or sha)
                               else "the records pinned no source manifest") + " |")
                continue
            if not (md5 or sha):
                rows.append(f"| {disp} | {named} | – | – | the records name `{path}` but pinned no "
                            "hash of it, so no version can be recovered |")
                continue
            try:
                got = committed_bytes_for(path, md5=md5, sha256=sha)
            except GitUnavailable as exc:
                rows.append(f"| {disp} | {named} | – | – | git could not supply it: {exc} |")
                continue
            if got is None:
                rows.append(f"| {disp} | {named} | – | – | no committed version of `{path}` hashes to it |")
                continue
            raw, entry = got
            ps = sorted(set(projects), key=PROJECTS.index)
            try:
                then = {p: ri.inventory(raw, crate, p) for p in ps}
            except ValueError as exc:
                rows.append(f"| {disp} | {named} | – | – | the inventory cannot read it: {exc} |")
                continue
            now = {p: ri.inventory(today, crate, p) for p in ps}
            corpus = [p for p in ps if _release_facts(then[p]) != _release_facts(now[p])]
            tier = [p for p in ps if [e["source_id"] for e in then[p]["tier1"]]
                    != [e["source_id"] for e in now[p]["tier1"]]]
            rows.append(f"| {disp} | {named}, committed {entry['date']} (`{entry['commit'][:10]}`) | "
                        + ("as today" if not corpus else "differs: " + ", ".join(corpus)) + " | "
                        + ("as today" if not tier else "differs: " + ", ".join(
                            f"{p} {then[p]['tier1_count']} (today {now[p]['tier1_count']})" for p in tier))
                        + " | |")
    return rows


def _release_subelement_rows(scores) -> list[str]:
    """Per project and evaluator, the release-level rubric10 sub-elements
    scored 1, over every evaluation the rubric10 table shows (each once)."""
    seen: dict[tuple[str, str], dict[str, list[int]]] = {}
    files: set[str] = set()
    for arm in (scores.get("rubric10") or {}).values():
        for p, ss in arm.items():
            for s in ss:
                if s["file"] in files or not s.get("doc"):
                    continue
                files.add(s["file"])
                cell = seen.setdefault((p, s.get("evaluator") or "unrecorded"),
                                       {lab: [0, 0, 0] for lab, *_ in RELEASE_SUBELEMENTS})
                elements = {e.get("id"): e for e in s["doc"].get("elements") or [] if isinstance(e, dict)}
                for lab, eid, pos, name in RELEASE_SUBELEMENTS:
                    subs = (elements.get(eid) or {}).get("sub_elements") or []
                    sub = subs[pos - 1] if len(subs) >= pos else None
                    if not (isinstance(sub, dict) and str(sub.get("name", "")).startswith(name)):
                        continue
                    if isinstance(sub.get("score"), (int, float)) and not isinstance(sub["score"], bool):
                        cell[lab][0] += 1 if sub["score"] > 0 else 0
                        cell[lab][1] += 1
                    elif sub.get("applicable") is False:
                        cell[lab][2] += 1               # N/A: evaluator output, out of the denominator
    return [f"| {p} | `{ev}` | " + " | ".join(
                (f"{k}/{n}" if n else "") + (", " if n and na else "") + (f"{na} N/A" if na else "")
                or "–" for k, n, na in cell.values()) + " |"
            for (p, ev), cell in sorted(seen.items(), key=lambda kv: (PROJECTS.index(kv[0][0]), kv[0][1]))]


def release_inventory_section(data, scores) -> list[str]:
    """The release-level corpus inventory (#2914, #3282): what release
    evidence each project's document corpus holds, whether each arm read the
    same, and the rubric10 sub-elements that evidence decides."""
    from data_sheets_schema import release_inventory as ri
    today = (ROOT / SOURCE_MANIFEST).read_bytes()
    crate_path = ROOT / CRATE_MANIFEST
    crate = crate_path.read_bytes() if crate_path.is_file() else None
    invs = {p: ri.inventory(today, crate, p) for p in PROJECTS}

    def ids(entries) -> str:
        return ", ".join(f"`{e['source_id']}`" + (" (superseded)" if e["superseded"] else "")
                         for e in entries) or "none"

    def policy(inv) -> str:
        cp = inv["crate_policy"]
        return f"`{cp['document_corpus']}`" if cp["status"] == "declared" else cp["status"].replace("_", " ")

    table = [f"| {p} | {inv['tier1_count']} ({inv['tier1_current_count']} current) | "
             f"{ids(inv['governance']['license'])} | {ids(inv['governance']['DUA'])} | "
             f"{ids(inv['governance']['IRB'])} | {ids(inv['release_records'])} | "
             f"{'yes' if inv['crate_in_document_corpus'] else 'no'} | {policy(inv)} |"
             for p, inv in invs.items()]
    lacking = ri.lacking_release_evidence(list(invs.values()))
    carrying = [p for p, inv in invs.items() if inv["crate_in_document_corpus"] and inv["governance"]["license"]]
    facts = []
    for p in carrying:
        facts.append(f"{p}'s document corpus carries its RO-Crate and its licence "
                     f"({ids([e for e in invs[p]['release_records'] if e['source_type'] == ri.CRATE_TYPE])}; "
                     f"{ids(invs[p]['governance']['license'])})")
    for p in lacking:
        inv = invs[p]
        none = [k for k in ri.GOVERNANCE_TYPES if not inv["governance"][k]]
        facts.append(f"{p}'s corpus has {inv['tier1_count']} tier-1 sources, no release record"
                     + (", no " + "/".join(none) + " source" if none else "")
                     + (f", and the crate manifest declares its crate `document_corpus: "
                        f"{inv['crate_policy']['document_corpus']}`"
                        if inv["crate_policy"]["status"] == "declared"
                        else f", and its crate is not in the corpus ({policy(inv)})"))
    sub = _release_subelement_rows(scores)
    crate_named = (f"`{CRATE_MANIFEST}` (`{hashlib.sha256(crate).hexdigest()[:12]}`)" if crate is not None
                   else "none (absent)")
    return ["## Release-level corpus inventory (#2914, #3282)", "",
            f"What release evidence each project's document corpus holds (`{ri.INSTRUMENT}`, "
            f"`d4d download release-inventory`), read from today's `{SOURCE_MANIFEST}` "
            f"(`{invs[PROJECTS[0]]['source_manifest_sha256'][:12]}`) and crate manifest {crate_named}. "
            "It counts what the manifests declare, not what the documents say: a source typed "
            "`license` is a licence source whatever its text, and a related-but-distinct dataset's "
            "declared `in_bundle` source is not this dataset's evidence.", "",
            "| project | tier-1 sources | licence | DUA | IRB | release records | crate in corpus | "
            "crate policy |", "|---|---|---|---|---|---|---|---|", *table, "",
            "The source-manifest version each arm's records pinned (`inputs.source_manifest`), "
            "recovered from git by that hash and inventoried against today's crate manifest — the "
            "records pin no crate-manifest hash, so that column is today's declaration for every "
            "arm. **Corpus** compares the licence/DUA/IRB sources and release records, crate "
            "included; **tier 1** compares the priority ranking the manifest declares, which is a "
            "ranking of the same documents and not a document:", "",
            "| arm | source manifest pinned | corpus release evidence | tier 1 | note |",
            "|---|---|---|---|---|", *_pinned_manifest_rows(data, today, crate), "",
            ("; ".join(facts) + ". " if facts else "")
            + (f"A record can state only the release facts its bundle carries, so differences between "
               f"projects on `doi`, `license`, `version` and `issued` are **corpus-driven** for "
               f"{', '.join(lacking)}, not a measure of generation quality, and so are the rubric10 "
               "sub-elements those slots decide:" if lacking else
               "Every project's corpus carries a release record or a licence/DUA source.")
            , "",
            "| project | evaluator | " + " | ".join(f"{lab} {name}" for lab, _e, _p, name in RELEASE_SUBELEMENTS)
            + " |", "|---|---|" + "---|" * len(RELEASE_SUBELEMENTS), *(sub or ["| – | – |" + " – |" * len(RELEASE_SUBELEMENTS)]),
            "",
            "Cells are evaluations scoring the sub-element 1 over those scoring it at all, and "
            "the evaluations that judged it not applicable (N/A is itself evaluator output), per "
            "evaluator (never pooled, #1058), over every rubric10 evaluation in the rubric tables "
            "below; `–` where none carries the sub-element under that name. A 0 where the corpus "
            "holds no such evidence is the corpus's, not the generator's.", ""]


def _structure_row(arm: str, project: str, v: dict[str, int], names: str) -> str:
    return (f"| {arm} | {project} | {v['records']} | {v['all']} / {v['some']} / {v['none']} | "
            f"{v['identical']} | {v['nested_in_all']}: {v['nested_counted']} / {v['differ']} / "
            f"{v['ge2']} | {v['key']} / {v['pos']} / {v['unaligned']} | {names} |")


def form_schema_section(data) -> list[str]:
    """Expose each live form measurement's schema resolution, including fallback."""
    def escaped(value):
        return html.escape(str(value), quote=False).replace("|", "&#124;").replace(
            "`", "&#96;").replace("\n", "<br>")

    lines = ["## Live form schema bases (#4216)", "",
             "The current form instrument is separate from its schema and naming inputs. "
             "Undeclared prefixes and the identifier walk (including organisational fragments) "
             "use the run's merged schema when recoverable. The resolution below states which "
             "bytes supplied those rules. Path/hash fields are the run's requested pins: if "
             "the source is today's schema, those fields do not attest that the requested "
             "historical bytes were used; the reason explains the fallback.", "",
             f"Current prefix instrument: {PREFIX_INSTRUMENT}. "
             f"Current British-spelling instrument: {BRITISH_INSTRUMENT}. "
             "GC label variants use the current `data/preprocessed/source_manifest.yaml` "
             "naming declaration, not the run's schema or a recovered historical manifest. "
             "Stored form blocks and canary gate baselines are not rewritten by this report.", "",
             "| arm | project | label | schema resolution |",
             "|---|---|---|---|"]
    for arm, display, *_rest in ARMS:
        for project in PROJECTS:
            for row in data[arm][project]:
                basis = row.get("form_schema_basis")
                text = (json.dumps(basis, sort_keys=True, ensure_ascii=False)
                        if basis is not None else "unrecorded — no schema basis supplied")
                lines.append("| " + " | ".join(escaped(v) for v in (
                    display, project, row.get("label", "unrecorded"), text)) + " |")
    return lines + [""]


def removal_schema_section(data) -> list[str]:
    """Keep the actual per-run removal inputs visible beside recomputed counts."""
    def escaped(value):
        return html.escape(str(value), quote=False).replace("|", "&#124;").replace(
            "`", "&#96;").replace("\n", "<br>")

    lines = ["## Live removal schema bases (#4286, #4296)", "",
             "Removal identity joins and resolver aliases use the run's recorded merged-schema "
             "rules when recoverable. The identifier basis distinguishes any requested historical "
             "pins from the actual current fallback and hashes the effective ordered alias table. "
             "Person-slot and enum-alias selectors retain their separately disclosed resolutions; "
             "the table does not assert that independently selected rules came from one capture. "
             "No stored record or canary gate baseline is rewritten. Different counts on this "
             "basis are not evidence of a generation improvement.", "",
             "The table omits the alias list itself but retains its digest, boundary rule and "
             "schema resolution. Unavailable authority or evidence stays unmeasured, not zero.", "",
             "| arm | project | label | removal measurement basis |", "|---|---|---|---|"]
    for arm, display, *_rest in ARMS:
        for project in PROJECTS:
            for row in data[arm][project]:
                basis = row.get("removal_schema_basis")
                if basis is not None:
                    basis = dict(basis)
                    identity = basis.get("identifier_rules")
                    if isinstance(identity, dict):
                        basis["identifier_rules"] = {k: v for k, v in identity.items() if k != "bases"}
                text = (json.dumps(basis, sort_keys=True, ensure_ascii=False)
                        if basis is not None else "unrecorded — no removal basis supplied")
                lines.append("| " + " | ".join(escaped(v) for v in (
                    display, project, row.get("label", "unrecorded"), text)) + " |")
    return lines + [""]


def render_markdown(data, scores) -> str:
    lines = ["# Cross-arm comparison (regenerated)", "",
             f"Generated by `scripts/arm_comparison.py` from the provenance records under "
             f"`data/d4d_concatenated/`; do not edit by hand — re-run the script.", "",
             "## Bases", "",
             "- pair errors, report findings, grounding: each record's own blocks. Pair "
             "is a deterministic artifact check; grounding is against the record's "
             "declared bundle, whose md5 still matches disk for every arm shown "
             "(`recorded_by` says whether the run or backfill-checks wrote it).",
             "- British spellings, undeclared prefixes, organisational fragments, GC "
             "label variants: **recomputed live** from the artifacts under the current "
             "instrument (`grounding.form_facts`), using each run's recorded merged-schema "
             "identifier rules where recoverable. Per-record schema resolution and any fallback "
             "to today's rules are disclosed below. Stored `form` blocks are not read or rewritten "
             "and may differ. GC variants still use the current naming manifest, whose declaration "
             "was decided 2026-08-22 — anachronistic for v4; it is not recovered from the run's schema.",
             "- rubric scores: `data/evaluation_llm/rubric{10,20}_semantic/label_aware/`. "
             "The v7 production and v8 arms were scored by `claude-opus-5[1m]` on "
             "2026-09-08; their superseded `claude-fable-5` scores are kept under "
             "`label_aware/superseded_fable5/`, outside this glob. **Every other arm "
             "shown is still Fable 5**, so a rubric row compares one evaluator "
             "within v7/v8 and a different one across the older arms — an "
             "evaluator is an instrument (#1058). N/A exclusions are evaluator "
             "judgements, so adjusted maxima can differ between comparable "
             "records, The Element 4 gate resolved both ways on CM4AI until 2026-09-08; it is now stated per sub-element and those six were rescored (#1060), so the CM4AI rubric10 cells here are not comparable to any figure quoted before that date.",
             "- removals without a finding (all phases, the reconcile_full share and the "
             "share with a relocation candidate), "
             "low-confidence flattenings without a finding (#3367), "
             "receipted values deleted, values rewritten in place without a finding and the "
             "share not the model's (#3366): "
             "**recomputed live** under removals v3 "
             "from the phase-1 snapshot, the phase outputs, the final full record, the audit "
             "and the receipt, with the record's amend dispositions (#903) "
             "(`removals.for_record`, #2923), read-only; no record carries a "
             "removals block. Identifier aliases use the recorded schema where recoverable, "
             "with the actual per-record rule bases and fallback disclosed below (#4286). "
             "Removals unrecorded in the report: the record's `report_claims` "
             "block.",
             "- spend: absent by design — `api_usage` and `run_observed` are different "
             "quantities (#400).",
             "- a record whose own `validation` block says `passed: false` is not an arm "
             "member (#1029): " + (", ".join(f"`{l}` {p}" for l, p in EXCLUDED_INVALID) if EXCLUDED_INVALID else "none excluded this run") + ".", "",
             "Arms: " + "; ".join(f"**{d}** — " + (", ".join(f"`{l}`" for l in pfx) if isinstance(pfx, (list, tuple)) else f"`{pfx}_rep{{1,2,3}}`") + f", {rt}"
                                   + (" (also shown with its per-project worst on this report's measurement basis — max for reported-only metrics)" if role == "worst" else "")
                                   for _k, d, pfx, rt, role in ARMS), ""]

    lines += form_schema_section(data)
    lines += removal_schema_section(data)
    lines += ["## Deterministic metrics — mean ± SD over replicates", "",
              "| metric | project | " + " | ".join(d for _k, d, *_ in ARMS) + " |",
              "|---|---|" + "|".join("---" for _ in ARMS) + "|"]
    for mk, (disp, _src, _hiw, _cav) in METRICS.items():
        for p in PROJECTS:
            cells = []
            for key, _d, _pfx, _rt, role in ARMS:
                cells.append(cell(data[key][p], mk, role))
            lines.append(f"| {disp} | {p} | " + " | ".join(cells) + " |")
    lines += ["", "Cells are mean ± sample SD over the *measured* replicates, with every "
              "replicate value in brackets; n is 3 unless stated. The baseline arm adds "
              "its per-project worst on this report's measurement basis. Canary gates read "
              "stored form blocks; this live recompute does not change their thresholds (#4217). Read "
              "the SD as a spread, not a confidence interval: with n = 3 and one outlier "
              "(e.g. [3,14,130]) the SD is that outlier, and the bracketed values are the "
              "better summary. ᵘ = unmeasured — the report-claims checker parsed zero "
              "claims (#684); unmeasured values are excluded from the mean and n, and a "
              "cell with no measured replicate shows only its raw values.", ""]

    lines += receipt_section(data)
    lines += replicate_structure_section(data)
    lines += nested_structure_section(data)
    lines += omission_candidate_section(data)
    lines += entry_omission_section(data)
    lines += nested_omission_section(data)
    lines += receipted_where_empty_section(data)

    lines += ["## Per-metric caveats (attached, not footnoted elsewhere)", ""]
    for mk, (disp, src, _hiw, cav) in METRICS.items():
        basis = "record block" if src == "record" else "live recompute, current instrument"
        lines.append(f"- **{disp}** — {basis}." + (f" {cav}." if cav else ""))
    lines.append("")

    lines += release_inventory_section(data, scores)

    cohorts = rubric_discrimination(scores)
    for rubric, rscores in scores.items():
        lines += [f"## {rubric.capitalize()}-semantic scores (every evaluated replicate; earlier arms have their canonical only)", "",
                  "| project | " + " | ".join(d for _k, d, *_ in ARMS) + " |",
                  "|---|" + "|".join("---" for _ in ARMS) + "|"]
        withheld: dict[str, list[tuple[str, dict[str, str]]]] = {}
        for evaluator, _arms, _versions, cohort in cohorts:
            for name in instruments_of(cohort, f"{rubric}-semantic"):
                # A rubric the cohort holds under several versions is gated
                # per version (#3290); the cell names the version then.
                who = evaluator + name[len(f"{rubric}-semantic"):]
                for project, reasons in withheld_projects(cohort, name).items():
                    withheld.setdefault(project, []).append((who, reasons))
        for p in PROJECTS:
            cells = []
            for key, _d, pfx, _rt, _role in ARMS:
                ss = rscores[key][p]
                cells.append("; ".join(
                    f"{s['total']}/{s['adjusted_max'] or s['max']} ({s['pct']}%, {_rep_tag(s['label'])})"
                    for s in ss) or "–")
            lines.append(f"| {_withheld_cell(p, withheld.get(p))} | " + " | ".join(cells) + " |")
        lines.append("")
    evaluators = sorted({s["evaluator"] for rs in scores.values() for arm in rs.values() for ss in arm.values() for s in ss if s.get("evaluator")})
    lines += [f"Evaluator model(s) recorded: {', '.join(evaluators) or 'none'}. "
              "Scores are shown as points / adjusted maximum after N/A exclusions; "
              "comparison requires the same evaluator, definition and applicability "
              "basis; raw points alone do not establish comparability. These historical "
              "scores are not results from the newly registered reference rescore. "
              "No gold standard exists (#177); the rubrics are "
              "not domain-neutral (#627); rubric20's N/A convention is #155's.", ""]
    lines += same_family_section(scores)
    for evaluator, arms, versions, cohort in cohorts:
        lines += render_discrimination(cohort, scope=f", {evaluator} evaluations", evaluator=evaluator)
        lines += [f"This cohort is every {evaluator} evaluation in the rubric tables above "
                  f"(arms {', '.join(arms)}; {versions}); evaluations by different evaluators "
                  "are not pooled, since an evaluator is an instrument (#1058), and a rubric held "
                  "under more than one version is measured per version (#3290). A project the "
                  "rubric tables flag has too few distinct totals across these arms' records to "
                  "rank them against each other on that rubric.", ""]
    return "\n".join(lines)


def rubric_discrimination(scores) -> list[tuple[str, list[str], str, dict[str, Any]]]:
    """The #2927 block per evaluator over every evaluation the rubric tables
    show, each file once however many arms list it: (evaluator, arm keys,
    rubric versions, block). Pooling evaluators would count their offsets as
    distinct totals and hide a project one evaluator cannot separate; for the
    same reason `discrimination` splits a rubric the cohort holds under more
    than one version by version (#3290)."""
    groups: dict[str, dict[str, tuple[str, dict]]] = {}
    for rubric, rs in scores.items():
        for arm, per_project in rs.items():
            for ss in per_project.values():
                for s in ss:
                    if s.get("doc"):
                        groups.setdefault(s.get("evaluator") or "unrecorded", {})[
                            f"{rubric}/{s['file']}"] = (arm, s["doc"])
    order = [key for key, *_ in ARMS]
    out = []
    for evaluator in sorted(groups):
        members = groups[evaluator]
        arms = sorted({arm for arm, _doc in members.values()}, key=order.index)
        versions = "; ".join(
            f"{rubric} v{', v'.join(sorted({str(d.get('version')) for _a, d in members.values() if d.get('rubric') == rubric}))}"
            for rubric in sorted({d.get("rubric") for _a, d in members.values()}))
        out.append((evaluator, arms, versions,
                    discrimination(members[k][1] for k in sorted(members))))
    return out


def _withheld_cell(project: str, flags: list[tuple[str, dict[str, str]]] | None) -> str:
    """The project cell of a rubric table, flagged where #2927 withholds its
    within-project order: per evaluator, and per basis where only one is."""
    parts = []
    for evaluator, reasons in flags or []:
        counts = sorted({r.split(" distinct", 1)[0] for r in reasons.values()})
        where = "" if len(reasons) == 2 else f", {next(iter(reasons))} basis"
        parts.append(f"{evaluator}{where}: {'/'.join(counts)} distinct "
                     f"total{'' if counts == ['1'] else 's'}")
    return f"{project} (no within-project order — {'; '.join(parts)})" if parts else project


def write_markdown(data, scores) -> None:
    OUT_MD.write_text(render_markdown(data, scores), encoding="utf-8")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")


def write_figures(data, scores) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT_FIG.mkdir(parents=True, exist_ok=True)
    colors = {"v4": "#9e9e9e", "v5api": "#4e79a7", "v5agentic": "#f28e2b",
              "v6agentic": "#e15759", "v7api": "#59a14f", "v7prod": "#1b7f3b",
              "v8prod": "#7b3fa0"}

    # One figure per metric: 4 project panels, one bar per arm = replicate mean,
    # error bar = sample SD (n printed under the bar). Replicates are dots.
    for mk, (disp, _src, _hiw, _cav) in METRICS.items():
        fig, axes = plt.subplots(1, len(PROJECTS), figsize=(13, 3.6), sharey=True)
        top = 0.0
        for ax, p in zip(axes, PROJECTS):
            ns: dict[int, int] = {}
            for i, (key, *_rest) in enumerate(ARMS):
                reps = data[key][p]
                st = stats(reps, mk)
                if st is not None:
                    mean, sd, n = st
                    top = max(top, mean + (sd if n > 1 else 0))
                    ax.bar(i, mean, color=colors[key], width=0.7, alpha=0.85)
                    # Counts cannot go below zero; the lower whisker is clipped.
                    # No whisker at all for a single measured replicate.
                    if n > 1:
                        ax.errorbar(i, mean, yerr=[[min(sd, mean)], [sd]], fmt="none",
                                    ecolor="black", capsize=4, lw=1)
                    ns[i] = n
                # Replicates as dots: filled when measured, hollow when the
                # value is an unmeasured 0ᵘ (#684) and so not in the mean.
                for j, r in enumerate(reps):
                    v = r.get(mk)
                    if v is None:
                        continue
                    x = i + (j - 1) * 0.12
                    top = max(top, v)
                    if measured(r, mk):
                        ax.scatter([x], [v], s=14, color="black", zorder=3)
                    else:
                        ax.scatter([x], [v], s=18, facecolors="white", edgecolors="black", zorder=3)
            ax.set_xticks(range(len(ARMS)))
            ax.set_xticklabels([f"{k}\nn={ns[i]}" if i in ns else f"{k}\n–"
                                for i, (k, *_) in enumerate(ARMS)], fontsize=7, rotation=30, ha="right")
            ax.set_title(p, fontsize=10)
            ax.spines[["top", "right"]].set_visible(False)
        # One shared y-range for the row, floored at zero (counts) and sized to
        # the tallest bar-plus-whisker across all panels — set once, after every
        # panel is drawn, so no panel's autoscale freezes the top early.
        axes[0].set_ylim(0, max(1.0, top) * 1.12)
        handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k, *_ in ARMS]
        fig.legend(handles, [d for _k, d, *_ in ARMS], loc="lower center", fontsize=8, ncol=4, frameon=False)
        fig.suptitle(f"{disp} — mean ± SD over measured replicates; dots = replicates, hollow = unmeasured", x=0.02, ha="left", fontsize=11)
        fig.tight_layout(rect=(0, 0.12, 1, 0.92))
        out = OUT_FIG / f"arm_comparison_{mk}.png"
        fig.savefig(out, dpi=150); plt.close(fig)
        print(f"wrote {out.relative_to(ROOT)}")

    for rubric, rscores in scores.items():
        _rubric_figure(rubric, rscores, colors)


def _rubric_figure(rubric, scores, colors) -> None:
    import matplotlib.pyplot as plt
    # Rubric scores: raw points per project per arm (canonicals only).
    fig, ax = plt.subplots(figsize=(8, 3.6))
    arm_keys = [k for k, *_ in ARMS if any(scores[k][p] for p in PROJECTS)]
    if not arm_keys:
        plt.close(fig); return
    absent = [d for k, d, *_ in ARMS if k not in arm_keys]
    for k in arm_keys:
        for p in PROJECTS:
            if len(scores[k][p]) > 1:
                print(f"warning: {len(scores[k][p])} evaluations match {k}/{p}; "
                      f"figure shows the first by filename", file=sys.stderr)
    width = 0.8 / max(1, len(arm_keys))
    for i, key in enumerate(arm_keys):
        vals = [(scores[key][p][0]["total"] if scores[key][p] else 0) for p in PROJECTS]
        xs = [j + i * width for j in range(len(PROJECTS))]
        ax.bar(xs, vals, width=width, color=colors[key],
               label=dict((k, d) for k, d, *_ in ARMS)[key])
        # Points are drawn against the unadjusted maximum; where an evaluation
        # excluded N/A questions its adjusted maximum is written on the bar so
        # the visual height is not read as a percentage (#696 review).
        for x, p, v in zip(xs, PROJECTS, vals):
            if scores[key][p]:
                s0 = scores[key][p][0]
                adj = s0.get("adjusted_max") or s0.get("max")
                ax.text(x, v + 0.5, f"{v}/{adj}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks([j + width * (len(arm_keys) - 1) / 2 for j in range(len(PROJECTS))])
    ax.set_xticklabels(PROJECTS); ax.set_ylim(0, RUBRIC_MAX[rubric] * 1.08)
    ax.set_ylabel(f"{rubric}-semantic points (axis: unadjusted max {RUBRIC_MAX[rubric]})")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=len(arm_keys))
    ax.set_title(f"{rubric.capitalize()}-semantic, canonical records (same evaluator; n = 1 per bar, no SD)",
                 fontsize=9, loc="left")
    if absent:
        fig.text(0.01, 0.01, f"No evaluations exist for: {', '.join(absent)}", fontsize=7, color="#555")
    fig.tight_layout()
    out = OUT_FIG / f"arm_comparison_{rubric}.png"
    fig.savefig(out, dpi=150); plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="check committed Markdown against current records; write no outputs")
    args = ap.parse_args()
    data = collect()
    scores = {rubric: {key: {p: rubric_scores(pfx, p, rubric) for p in PROJECTS}
                       for key, _d, pfx, *_ in ARMS} for rubric in EVAL_DIRS}
    missing = [(k, p) for k in data for p in PROJECTS if not data[k][p]]
    if missing:
        print(f"note: no complete runs for {missing}", file=sys.stderr)
    if EXCLUDED_INVALID:
        print(f"note: excluded as invalid by their own validation block: {EXCLUDED_INVALID}", file=sys.stderr)
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != render_markdown(data, scores):
            print("stale comparison Markdown; run scripts/arm_comparison.py to regenerate the table and figures",
                  file=sys.stderr)
            return 1
        print("comparison Markdown matches current records")
        return 0
    write_markdown(data, scores)
    if not args.no_figures:
        write_figures(data, scores)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
