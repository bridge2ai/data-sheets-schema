"""Hold the first run of a sweep to a higher bar than the rest (#579).

`d4d api batch` counted a run as succeeded on schema validation alone. A run
whose full/core pair diverges, whose reconciliation report contradicts its own
record, or which carries identifiers absent from its bundle entered the
"succeeded" column. That is how the 2026-08-13 arm swept clean: twelve records,
all valid, `runs check --strict` exit 0, and eleven divergent pairs and
twenty-nine ungrounded identifiers inside them.

The canary rule says one unit is verified before the batch fans out. But the
canary's verdict *was* the batch's verdict, and the batch did not look at the
three checks — so a canary could pass while exhibiting precisely the defects the
arm was built to fix, and the sweep would proceed to spend the rest.

## A regression gate, not a perfection gate

v5 is a production run. Requiring zero pair errors would refuse to start, since
eleven of twelve v4 records have some. What the gate asks instead is whether the
canary is **worse than the worst v4 record for the same project** — a bar known
to be achievable, with room for the replicate variance that arm showed.

Three outcomes, and the middle one is the point:

``ok``
    no check regressed against the baseline.
``regressed``
    a check is worse than the worst baseline run for that project. Stop; the
    remaining runs would spend on a known regression.
``unmeasurable``
    a check could not run. Also stops: a canary whose instruments were blind
    has not verified anything, which is the failure #565 recorded one level
    down.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

OK = "ok"
REGRESSED = "regressed"
UNMEASURABLE = "unmeasurable"

#: (label, how to read a count out of a check block, lower-is-better)
#: Each is a count of a defect in one record, so it is comparable across arms
#: even when the schema has moved — unlike anything schema-dependent (#576).
METRICS = (
    ("pair errors", "pair", lambda b: int(b.get("errors") or 0)),
    ("report findings", "report", lambda b: len(b.get("findings") or [])),
    ("ungrounded identifiers", "grounding",
     lambda b: int((b.get("distinct") or b.get("counts") or {}).get("absent") or 0)),
    # #591. Invisible to the other three: a resolver URL for a declared prefix
    # grounds perfectly — `doi.org/10.60775/…` is in the bundle — so what is
    # wrong with it is form, not evidence. The v5 canary wrote 45 and passed a
    # gate that measured pair consistency, report claims and grounding, none of
    # which could see the rule v5 exists to enforce.
    # Distinct identifiers, not occurrences (#593). Every identifier appears in
    # both records of a pair, so an occurrence count is roughly double and reads
    # as twice the problem — the error #556 records for the grounding counts,
    # made again here: the canary's 45 is 22 distinct values.
    ("resolver URLs in identifier slots", "grounding",
     lambda b: len({f.get("value") for f in (b.get("findings") or [])
                    if f.get("kind") == "resolver_url_in_identifier_slot"})),
    # The three preregistered families the gate could not see (#602). Each is a
    # count of a defect in one record, so it survives a schema change between
    # arms the way slot counts do not (#576).
    ("organisational fragments", "form",
     lambda b: int(b.get("organisational_fragments") or 0)),
    ("undeclared prefixes", "form",
     lambda b: int(b.get("undeclared_prefix_occurrences") or 0)),
    ("British spellings", "form",
     lambda b: int(b.get("british_spellings") or 0)),
)

#: Measured and reported, never gated. Prediction 2 of the v5 plan is that
#: minted-fragment counts **rise or hold** — rule three redirects invention
#: rather than forbidding it — so "higher than baseline" is the intended
#: outcome, and a gate built on "higher is a regression" would fail the arm for
#: working. The plan also names the failure this number diagnoses: if `absent`
#: falls while this does not rise, the model is omitting identifiers rather
#: than anchoring them, which is a different result from the intended one and
#: must not be reported as it.
REPORTED_ONLY = (
    ("minted fragments", "grounding",
     lambda b: (int((b.get("distinct") or b.get("counts") or {})
                    ["minted_fragment"])
                if "minted_fragment" in (b.get("distinct")
                                         or b.get("counts") or {})
                else None)),
    # GC label variants (#668): reported, not gated, because the rule reaches
    # generation for the first time at the next condition — a gate needs a
    # baseline measured under the rule, which does not exist until that
    # condition has an arm. Recorded per-project worsts in the 2026-08-20b
    # arm, post-#669-counter: VOICE 57, all others 0 (the once-quoted 16/6
    # for CHORUS/AI_READI were the pre-fix counter reading headers and file
    # paths). The number to watch is whether the next canary lands below its
    # project's figure — for three projects that figure is zero.
    # Absent is None, not zero (#669 review): a record measured before the
    # counter existed has no value, and reading it as a measured 0 is the
    # not-established-is-not-fine error inside the module that names it.
    ("GC label variants", "form",
     lambda b: (int(b["gc_label_variant_occurrences"])
                if "gc_label_variant_occurrences" in b else None)),
    # Receipts (#708) are shown on every run and gated by `verdict` against
    # floors when the run's procedure wrote one; `_ran` reads `checked`, so
    # an unchecked block prints — (#727).
    ("snippets unattesting (below the floors)", "receipts",
     lambda b: (b.get("snippets") or {}).get("unattesting")),
    ("snippets bearing on no token of their value", "receipts",
     lambda b: (b.get("snippets") or {}).get("no_value_overlap")),
    ("entry receipts overlapping one leaf", "receipts",
     lambda b: (b.get("snippets") or {}).get("entry_single_leaf")),
    ("chunks unreviewed", "receipts", lambda b: receipt_floors(b)["chunks unreviewed"]),
    ("snippets unverified", "receipts", lambda b: receipt_floors(b)["snippets unverified"]),
    # Adjacent, elsewhere and boundary-spanning together: verbatim in the
    # bundle, not wholly inside the chunk cited (#786).
    ("snippets not in the chunk cited", "receipts",
     lambda b: int((b.get("snippets") or {}).get("adjacent") or 0) + int((b.get("snippets") or {}).get("elsewhere") or 0)
     + int((b.get("snippets") or {}).get("spans_boundary") or 0)),
)


#: Which metric answers each numbered prediction in
#: `notes/generic_v5_analysis_plan.md`. Declared so a prediction with no metric
#: is a test failure rather than something to notice later (#602).
#:
#: The gate's metric set and the plan's prediction set were never reconciled,
#: and the consequence was #591: a run regressed on the rule v5 exists to
#: enforce and the gate passed it, because nothing measured that rule. Fixing
#: that instance added one metric; this is the general form.
PREDICTION_METRICS = {
    1: "ungrounded identifiers",
    2: "minted fragments",              # reported, never gated — see REPORTED_ONLY
    3: "organisational fragments",
    4: "undeclared prefixes",
    5: "British spellings",
}


def receipt_floors(block: dict[str, Any]) -> dict[str, int]:
    """Defect counts read from a checked receipts block; each must be 0."""
    ch, sn = block.get("chunks") or {}, block.get("snippets") or {}
    total, reviewed = int(ch.get("total") or 0), int(ch.get("reviewed") or 0)
    return {
        "chunks unreviewed": max(0, total - reviewed),
        "snippets unverified": int(sn.get("mismatched") or 0) + int(sn.get("unchecked") or 0),
        # #891, registered in the v7 plan: addressing-shaped unresolved paths
        # (real structure, wrong interior index) are tolerated in proportion
        # to receipt exposure - ceil(total snippets / 200) - because a floor
        # of zero over 200+ probabilistic items gates on bookkeeping, not
        # fabrication. Fabrication-shaped paths stay in "receipt findings".
        # Denominator is VERIFIED snippets (#893): padding a receipt with
        # unattesting snippets must not buy tolerance.
        "addressing slips over tolerance": max(0, int(((block.get("slots") or {}).get("addressing_slips_count")) or 0)
                                               - -(-int(sn.get("verified") or 0) // 200)),
        # A receipt over a non-empty bundle that extracted nothing is not a
        # clean receipt; it is `checked: 0` wearing a pass (#684, DisMech #7252).
        # #893: vacuity is about ATTESTATION - a receipt whose snippets are
        # all below the floors has verified nothing (#684's lesson again).
        "receipts vacuous": int(total > 0 and int(sn.get("verified") or 0) == 0),
        # Findings not already counted above: a mismatched snippet is one
        # defect, not two lines (#727).
        # Wrong-chunk attributions are reported, never gated (#763): the
        # text is in the bundle, so support holds; attribution precision is
        # its own reported number.
        # Pre-cap integer when the block carries it (#840); the capped-list
        # count is the fallback for blocks written before it existed.
        "receipt findings": (int(block["findings_gated"]) if isinstance(block.get("findings_gated"), int)
                             else len([f for f in block.get("findings") or []
                                       if f.get("kind") not in ("snippet_mismatch", "snippet_empty",
                                                                "snippet_adjacent_chunk", "snippet_elsewhere_chunk",
                                                                "snippet_spans_boundary")])),
    }


def report_vacuous(block: Any) -> bool:
    """A report check that read no claim and found nothing (#684).

    `findings: []` over `claims_checked: 0` is not a held floor of zero: the
    checker had nothing to test. Findings with no checked claim (a false
    schema claim) are still findings, so only the empty case is vacuous.
    """
    if not isinstance(block, dict) or not _ran(block):
        return False
    return not (block.get("findings") or []) and not int(block.get("claims_checked") or 0)


def _ran(block: Any) -> bool:
    if not isinstance(block, dict):
        return False
    if "ran" in block:
        return bool(block["ran"])
    return bool(block.get("checked"))


def counts_from(checks: dict[str, Any],
                metrics=None) -> dict[str, int | None]:
    """One number per metric, or None where the check did not run."""
    out: dict[str, int | None] = {}
    for name, key, read in (metrics if metrics is not None else METRICS):
        block = (checks or {}).get(key)
        out[name] = read(block) if _ran(block) else None
    return out


def baseline_for(project: str, label_prefix: str,
                 method: str = "claudecode_agent",
                 concat_dir: Path | None = None) -> dict[str, int | None]:
    """The worst value each metric took across a baseline arm, for one project.

    The *worst*, deliberately. The best would make normal replicate variance
    read as a regression, and this gate stops a paid sweep — it should fire on
    a real step backwards, not on a run landing at the unlucky end of a spread
    the baseline arm itself showed.
    """
    import yaml

    from data_sheets_schema.provenance import CONCAT_DIR
    base = concat_dir or CONCAT_DIR
    worst: dict[str, int | None] = {name: None for name, _, _ in METRICS}
    for path in sorted(base.glob(
            f"{method}_core/{label_prefix}*/{project}_provenance.yaml")):
        rec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        counts = counts_from({"pair": rec.get("pair_consistency"),
                              "report": rec.get("report_claims"),
                              "grounding": rec.get("grounding"),
                              "form": rec.get("form")})
        if report_vacuous(rec.get("report_claims")):
            counts["report findings"] = None          # unmeasured, not 0 (#684)
        for name, value in counts.items():
            if value is None:
                continue
            worst[name] = value if worst[name] is None else max(worst[name],
                                                                value)
    return worst


def report_basis(project: str, label_prefix: str,
                 method: str = "claudecode_agent",
                 concat_dir: Path | None = None) -> dict[str, int]:
    """How the baseline arm's replicates stand on the report metric: how many
    measured a claim, how many were vacuous (ran, read none), how many never
    ran. `baseline_for` folds the last two into one None; the floor in
    `verdict` needs them apart (#599 again): a baseline whose checker never
    ran is not a baseline of zero findings.
    """
    import yaml
    from data_sheets_schema.provenance import CONCAT_DIR
    base = concat_dir or CONCAT_DIR
    out = {"measured": 0, "vacuous": 0, "unchecked": 0}
    for path in sorted(base.glob(
            f"{method}_core/{label_prefix}*/{project}_provenance.yaml")):
        rec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        block = rec.get("report_claims")
        if report_vacuous(block):
            out["vacuous"] += 1
        elif _ran(block):
            out["measured"] += 1
        else:
            out["unchecked"] += 1
    return out


def verdict(checks: dict[str, Any], baseline: dict[str, int | None],
            baseline_requested: bool = True,
            report_basis: dict[str, int] | None = None) -> dict[str, Any]:
    """Compare one run's checks against a baseline. See module docstring.

    `baseline_requested` distinguishes the two ways a bar can be missing, which
    the first version did not (#599). A baseline nobody asked for is an absence;
    a baseline that was named and matched no records is an **error**, and
    treating them alike meant a mistyped prefix returned `ok` for a run with 999
    defects in every metric.

    That is the distinction this whole corpus turns on — "not established" is
    not "fine" — missed inside the gate built to enforce it.
    """
    counts = counts_from(checks)
    # A vacuous report row (#684) is unmeasured. Under step E (#929) the
    # report phase is asked for a dispositions table, so a run whose block
    # says `dispositions_expected` and still reads no claim is blind — the
    # receipt precedent. An earlier record's vacuous row is reported as
    # unmeasured and not gated: the arm that defined this gate wrote no
    # readable claim, and the gate must stay satisfiable by it.
    rb = (checks or {}).get("report")
    report_note = None
    report_blind_note = None
    if report_vacuous(rb):
        counts["report findings"] = None
        if isinstance(rb, dict) and rb.get("dispositions_expected"):
            report_blind_note = ("blind: the run was asked for a dispositions table and the "
                                 "report carried no claim the checker reads (#929)")
        else:
            report_note = "unmeasured: the report carried no claim the checker reads (#684)"
    blind = [name for name, value in counts.items()
             if value is None and not (name == "report findings" and report_note)]
    unbaselined = [name for name, value in baseline.items() if value is None]
    # The report metric is unmeasured on 11 of 12 v7 production records
    # (#684): their reports carried no claim the checker reads. A baseline
    # whose replicates were *vacuous* — the checker ran and read nothing —
    # and none measured is a floor of 0 with its basis on the row. Only
    # that: a baseline whose checker never ran, or a mistyped prefix, stays
    # a missing baseline and fatal (#599). The caller says which it was
    # through `report_basis`; without it there is no floor.
    report_floor = ("report findings" in unbaselined
                    and bool(report_basis)
                    and report_basis.get("measured", 0) == 0
                    and report_basis.get("vacuous", 0) > 0)
    if report_floor:
        unbaselined = [n for n in unbaselined if n != "report findings"]
    rows = []
    regressions = []
    for name, value in counts.items():
        bar = baseline.get(name)
        row = {"metric": name, "run": value, "baseline_worst": bar}
        if name == "report findings" and report_floor:
            bar = row["baseline_worst"] = 0
            row["baseline_basis"] = (f"floor 0: {report_basis['vacuous']} baseline replicate(s) "
                                     "ran the report check and read no claim, none measured one (#684)")
        if name == "report findings" and (report_note or report_blind_note):
            row["note"] = report_note or report_blind_note
        if value is not None and bar is not None and value > bar:
            row["regressed"] = True
            regressions.append(f"{name}: {value} against a baseline worst of {bar}")
        rows.append(row)

    # Receipts (#708) are gated against absolute floors, not a baseline: no
    # earlier arm wrote one, and the floors are the receipt's own definition —
    # every chunk reviewed, every snippet verified. Three cases: the block says
    # the procedure wrote no receipt → not a metric for this run; it says one
    # was expected and none could be checked → blind (UNMEASURABLE, #613); it
    # was checked → floors.
    rb = (checks or {}).get("receipts")
    if isinstance(rb, dict) and rb.get("expected"):
        if not rb.get("checked"):
            blind.append("receipts")
            rows.append({"metric": "receipts", "run": None, "baseline_worst": None})
        else:
            for name, value in receipt_floors(rb).items():
                row = {"metric": name, "run": value, "baseline_worst": 0}
                if value > 0:
                    row["regressed"] = True
                    regressions.append(f"{name}: {value} against a floor of 0")
                rows.append(row)

    if blind:
        status = UNMEASURABLE
    elif baseline_requested and unbaselined:
        # A bar that was asked for and did not resolve cannot pass anything.
        status = UNMEASURABLE
    elif regressions:
        status = REGRESSED
    else:
        status = OK
    return {"status": status, "rows": rows, "blind": blind,
            "unbaselined": unbaselined if baseline_requested else [],
            "regressions": regressions}
