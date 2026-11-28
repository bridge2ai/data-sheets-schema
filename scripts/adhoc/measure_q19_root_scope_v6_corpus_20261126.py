# Purpose: reproduce the Q19 corpus measurement and expose every added sentence
# for human classification. Inputs: tracked evaluations and a baseline Git ref.
# Output: JSON on stdout only. Serves PR 6372 corpus repair, 2026-11-26.
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema import q19_rationale_lint as lint


RECOMMENDATION = re.compile(
    r"^(?:populate|add|mirror|record|express|link|use|include|consider|document|fill|emit"
    r"|expose|publish|wire|instantiate|promote|set|move|provide|state|replace|encode|model"
    r"|capture|declare|convert|represent|reference|attach|list|map|split|clarify|name|keep"
    r"|resolve|attribute)\b", re.I)
EMPTY = re.compile(r"\b(?:empty|absent|unpopulated|unused|no|not|none|nor|neither|lacks?"
                   r"|lacking|missing|without|null)\b", re.I)


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True).stdout


def documents(ref=None):
    if ref:
        paths = git("ls-tree", "-r", "--name-only", "-z", ref,
                    "--", "data/evaluation_llm").decode().split("\0")
    else:
        paths = git("ls-files", "-z", "data/evaluation_llm").decode().split("\0")
    result = {}
    for name in paths:
        if not name.endswith(".json"):
            continue
        raw = git("show", f"{ref}:{name}") if ref else (ROOT / name).read_bytes()
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        result[name] = (value, hashlib.sha256(raw).hexdigest())
    return result


def strings(value, pointer="", context=None):
    if isinstance(value, str):
        yield pointer, value, context
    elif isinstance(value, dict):
        if any(key in value for key in ("quality_note", "semantic_analysis", "evidence")):
            context = value
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from strings(child, f"{pointer}/{escaped}", context)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from strings(child, f"{pointer}/{index}", context)


def measure(docs):
    ratings = {name: value for name, (value, _) in docs.items()
               if isinstance(value, dict) and value.get("rubric") == "rubric20-semantic"}
    slot = lint.REPRESENTATION_CONCERNS["empty_slot"]
    inside = {sentence for value in ratings.values()
              for _, sentence in lint._sentences(lint.q19_item(value))}
    q19 = [{"file": name, "field": field, "sentence": sentence,
            "marked": bool(lint._EMPTINESS.search(sentence))}
           for name, value in ratings.items()
           for field, sentence in lint._sentences(lint.q19_item(value))
           if slot.search(sentence)]
    outside = {}
    for name, (value, _) in docs.items():
        for pointer, text, context in strings(value):
            for sentence in lint._SENTENCE.split(text):
                sentence = sentence.strip()
                if not sentence or not slot.search(sentence) or sentence in inside:
                    continue
                outside.setdefault(sentence, []).append({
                    "file": name, "pointer": pointer, "context": context})
    reasons = []
    for name, value in ratings.items():
        for reason in lint.lint_q19(lint.q19_item(value)).reasons:
            if reason.concern == "empty_slot":
                reasons.append({"file": name, "sentence": reason.sentence,
                                "clause": reason.clause,
                                "clause_says_empty": bool(EMPTY.search(reason.clause))})
    marked = [sentence for sentence in outside if lint._EMPTINESS.search(sentence)]
    rest = [sentence for sentence in outside if not lint._EMPTINESS.search(sentence)]
    recommendations = [sentence for sentence in rest if RECOMMENDATION.match(sentence)]
    return {"counts": {"documents": len(docs), "ratings": len(ratings),
                       "empty_slot_reasons": len(reasons),
                       "neighboring_clause_reasons": sum(not r["clause_says_empty"] for r in reasons),
                       "q19_slot_sentences": len(q19),
                       "q19_unmarked": sum(not row["marked"] for row in q19),
                       "outside": len(outside), "outside_marked": len(marked),
                       "recommendations": len(recommendations),
                       "other_unmarked": len(rest) - len(recommendations)},
            "q19": q19, "empty_slot_reasons": reasons, "outside": outside}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="396f1114e")
    args = parser.parse_args()
    before_docs, after_docs = documents(args.baseline), documents()
    before, after = measure(before_docs), measure(after_docs)
    added = []
    for index, sentence in enumerate(sorted(set(after["outside"]) - set(before["outside"])), 1):
        marked = bool(lint._EMPTINESS.search(sentence))
        added.append({"id": f"S{index:03d}", "sentence": sentence,
                      "mechanical_class": "marked" if marked else (
                          "recommendation" if RECOMMENDATION.match(sentence) else "other_unmarked"),
                      "occurrences": after["outside"][sentence]})
    output = {"nice": os.getpriority(os.PRIO_PROCESS, 0),
              "baseline": git("rev-parse", args.baseline).decode().strip(),
              "head": git("rev-parse", "HEAD").decode().strip(),
              "linter_sha256": hashlib.sha256(Path(lint.__file__).read_bytes()).hexdigest(),
              "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "baseline_counts": before["counts"], "current_counts": after["counts"],
              "added_documents": {name: sha for name, (_, sha) in after_docs.items()
                                  if name not in before_docs},
              "changed_documents": [name for name in before_docs if name in after_docs
                                    and before_docs[name][1] != after_docs[name][1]],
              "new_q19_slot_sentences": [row for row in after["q19"] if row not in before["q19"]],
              "new_empty_slot_reasons": [row for row in after["empty_slot_reasons"]
                                         if row not in before["empty_slot_reasons"]],
              "removed_outside_sentences": sorted(set(before["outside"]) - set(after["outside"])),
              "added_outside_sentences": added}
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
