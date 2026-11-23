#!/usr/bin/env python3
"""Measure the corpus pins three failing corpus tests hold, on this checkout.

Purpose: data PR data/agentic-v9-opus55-final-20261122 adds 16 generated
records and 30 semantic evaluations; seven corpus tests then failed. This
script recomputes, read-only, the figures that three of them pin, split into
what the files committed before the 2026-11-22 additions contribute and what
the additions contribute, so the report can say which pins move and why:

- tests/test_q19_rationale_lint.py::test_every_empty_slot_reason_in_the_committed_ratings_is_said_to_be_empty
- tests/test_q19_rationale_lint.py::test_the_absence_vocabulary_recall_measured_on_the_committed_text
- tests/test_status_context.py::test_the_committed_corpus_locates_every_snippet_and_names_the_five_joined_ones

Inputs: the tracked files under data/evaluation_llm and the coverage
receipts under data/d4d_concatenated (git ls-files, as the tests read them).
Outputs: a JSON report on stdout. Writes nothing.
Date: 2026-11-22.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data_sheets_schema import q19_rationale_lint as lint  # noqa: E402
from data_sheets_schema import status_context as sc  # noqa: E402

NEW = "2026-11-22"


def tracked(prefix):
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", prefix],
                         capture_output=True, text=True, check=True).stdout
    return [f for f in out.split("\0") if f]


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def q19_figures(files):
    documents, ratings = [], []
    for f in files:
        if not f.endswith(".json"):
            continue
        try:
            d = json.loads((ROOT / f).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        documents.append(d)
        if isinstance(d, dict) and d.get("rubric") == "rubric20-semantic" and f.endswith("_evaluation.json"):
            ratings.append((f, d))
    slot = lint.REPRESENTATION_CONCERNS["empty_slot"]
    empty = re.compile(r"\b(?:empty|absent|unpopulated|unused|no|not|none|nor|neither|lacks?"
                       r"|lacking|missing|without|null)\b", re.I)
    reasons = [(f, r) for f, _ in ratings for r in lint.lint_file(ROOT / f).reasons
               if r.concern == "empty_slot"]
    elsewhere = [(f, r.clause, r.sentence) for f, r in reasons if not empty.search(r.clause)]
    q19 = [s for _, d in ratings for _, s in lint._sentences(lint.q19_item(d)) if slot.search(s)]
    unmarked = [s for s in q19 if not lint._EMPTINESS.search(s)]
    inside = {s for _, d in ratings for _, s in lint._sentences(lint.q19_item(d))}
    outside = {s.strip() for d in documents for text in strings(d)
               for s in lint._SENTENCE.split(text)
               if s.strip() and slot.search(s) and s.strip() not in inside}
    return {
        "ratings": len(ratings),
        "empty_slot_reasons": len(reasons),
        "reasons_whose_clause_has_no_empty_word": elsewhere,
        "q19_slot_sentences": len(q19),
        "q19_unmarked": unmarked,
        "outside_slot_sentences": len(outside),
        "outside_set": sorted(outside),
    }


def main():
    files = tracked("data/evaluation_llm")
    before = [f for f in files if f"/{NEW}_" not in f]
    now, old = q19_figures(files), q19_figures(before)
    added_outside = sorted(set(now.pop("outside_set")) - set(old.pop("outside_set")))
    out = {"q19_all_tracked": now, "q19_without_2026-11-22": old,
           "outside_sentences_added_by_2026-11-22": added_outside}
    walk = sc.corpus_status_context(ROOT / "data" / "d4d_concatenated")
    t = walk["totals"]
    out["status_context_totals"] = {k: t[k] for k in (
        "receipts", "checked", "snippets", "located", "not_verified", "value_unresolved",
        "malformed_entries", "unlocated", "indeterminate", "located_by_form")}
    out["status_context_form_located"] = [u for p in walk["projects"].values()
                                          for u in p["form_located_snippets"]]
    json.dump(out, sys.stdout, indent=1, default=str)


if __name__ == "__main__":
    main()
