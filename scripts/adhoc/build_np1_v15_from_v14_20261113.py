#!/usr/bin/env python3
"""Build draft v15 of analysis plan amendment NP1 from draft v14.

Purpose: apply the lead's three v15 rulings (coordination record, entry of
2026-11-13T08:38:05Z): the rebuilt-environment result's assumption about
version 3 validation; the end of the freeze on the reference's source export
and saved files; the AI_READI pilot's consequence in NP1.2's cost and in item
(s). Exact substring edits whose originals are asserted to occur once;
quotations of the coordination record are checked against it.
Inputs: v14 read from git at commit bb3eaa8b5 in the NP1 worktree, asserted by
sha256 1c2c7cdc...7b5a; STATUS.md in the primary checkout, read only.
Output: the amendment file in the NP1 worktree, overwritten with v15; prints
its sha256, line count and byte count, and runs post-checks.
Serves: NP1 draft v15 (branch claude/native-production-amendment-np1-20261112).
Date: 2026-11-13. Written by a copy of the Claude lead; left uncommitted in
the report worktree, as directed.
"""
import hashlib
import re
import subprocess
from pathlib import Path

W = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
         "claude-native-production-amendment-np1-20261112")
STATUS = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/"
              "notes/coordination/STATUS.md")
REL = "notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md"
V14_COMMIT = "bb3eaa8b5ffe2c17b3d16fb21634accf9104648b"
V14_SHA = "1c2c7cdc492e74a6005477aec4b2e846ce40d193409ca5c3116a20f5e7527b5a"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V14_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V14_SHA, "v14 bytes differ from the accepted draft"
text = raw.decode("utf-8")
assert len(text.split("\n")) - 1 == 681


def sub(old, new):
    global text
    n = text.count(old)
    assert n == 1, (n, old[:90])
    text = text.replace(old, new)


def line_starting(prefix):
    lines = text.split("\n")
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    assert len(hits) == 1, (prefix[:80], hits)
    return lines, hits[0]


def insert_after(prefix, new_lines):
    global text
    lines, i = line_starting(prefix)
    lines[i + 1:i + 1] = new_lines
    text = "\n".join(lines)


Q_ACCEPT = ("The lead accepted the copy's interpretations: two response tables, the line-40 list, the added "
            "citations, the copy into (al) and the header history.")
Q_R1 = ("The \"cannot decide\" result for a rebuilt environment assumes that version 3 validation regenerates "
        "the manifest from the live environment. The review of the version 3 documents confirms this before "
        "the first version 3 registration. Otherwise the result is \"not equal\" by the manifest's pin. Either "
        "way the registration is held.")
Q_R2 = ("The reference's source export and saved files stay frozen until the last production cell's acceptance "
        "record is signed, or until this stratum or the condition ends, the same end as the HEAD freeze.")
Q_R3 = ("The consequence for the AI_READI pilot after the reference run goes into NP1.2's \"What it costs\" and "
        "into item (s), in the reviewer's sentence.")
status_text = STATUS.read_text(encoding="utf-8")
for quote in (Q_ACCEPT, Q_R1, Q_R2, Q_R3):
    assert status_text.count(quote) == 1, quote[:60]

P38 = ("After the reference run, a stop or instrument case of the AI_READI pilot whose repair needs changed "
       "must-equal bytes ends this stratum at its filing (NP1.10(ar)), before the floor and before any "
       "production cell.")
FREEZE_END = ("until the last production cell's acceptance record is signed, or until this stratum or the native "
              "shared-v1 condition ends, whichever comes first")
assert text.count(FREEZE_END) == 1  # the HEAD freeze, whose words the export freeze takes

# ---------------------------------------------------------------- header
sub("**Status: draft v14, written by a copy of the Claude lead on 2026-11-13.**",
    "**Status: draft v15, written by a copy of the Claude lead on 2026-11-13.**")
insert_after("- **v13** (commit `668d62c431e9aaee93fc7ba3744f777b26797da3`", [
    "- **v14** (commit `bb3eaa8b5ffe2c17b3d16fb21634accf9104648b`, file sha256 "
    "`1c2c7cdc492e74a6005477aec4b2e846ce40d193409ca5c3116a20f5e7527b5a`) was not reviewed. The lead accepted "
    "it, with its author's interpretations, and gave three further rulings, which v15 applies (Authority)."])
insert_after("  - an AI_READI pilot repair after the reference run (NP1.5, NP1.10(e)), and the last state sentences", [
    "- **v14 → v15 applies the lead's three further rulings** (Authority):",
    "  - the \"cannot decide\" result for a rebuilt environment assumes that version 3 validation regenerates the "
    "manifest from the live environment, which the review of the version 3 documents confirms before the first "
    "version 3 registration; otherwise the result is \"not equal\", by the manifest's pin, and either way the "
    "registration is held (NP1.5);",
    "  - the reference's source export and saved files stay frozen until the HEAD freeze ends, in its words "
    "(NP1.5);",
    "  - NP1.2's cost of the AI_READI pilot and item (s)'s pending-pilot clause carry the Claude review's "
    "sentence on a repair of that pilot after the reference run (NP1.2, NP1.10(s))."])
sub("- **v14 has not been reviewed.**", "- **v15 has not been reviewed.**")

# ---------------------------------------------------------------- responses
sub("Each issue stays open until a re-check of v14 confirms the answer. \"Claude\" and \"Codex\" name the two "
    "confirmation reviews of v13.",
    "Each issue stays open until a re-check of v15 confirms the answer; v14 was not reviewed. \"Claude\" and "
    "\"Codex\" name the two confirmation reviews of v13.")
sub("| v13 finding | Issue | Answer in v14 | Where |", "| v13 finding | Issue | Answer in v15 | Where |")
sub("A rebuilt environment is treated the same way. The other statements",
    "A rebuilt environment is treated the same way, on the lead's ruling that version 3 validation regenerates "
    "the manifest from the live environment, which the review of the version 3 documents confirms; otherwise "
    "the result is \"not equal\", by the manifest's pin, and either way the registration is held. The other "
    "statements")
sub("| #6182 | Both say it now, in the review's words | NP1.5, (e) |",
    "| #6182 | Both say it now, in the review's words, and so do NP1.2's cost of the pilot and (s)'s "
    "pending-pilot clause | NP1.2, NP1.5, (e), (s) |")
sub("v14 completes those three (above). Each issue stays open until a re-check of v14 confirms the answer.",
    "v14 completes those three (above), and v15 carries them. Each issue stays open until a re-check of v15 "
    "confirms the answer.")
sub("| v11 finding | Issue | Answer in v14 | Where |", "| v11 finding | Issue | Answer in v15 | Where |")

# ---------------------------------------------------------------- authority
insert_after("  - **The rulings for v14** (entries of 2026-11-13T07:14:52Z, 07:32:30Z and 08:28:36Z)", [
    f"  - **The rulings for v15** (entry of 2026-11-13T08:38:05Z): \"{Q_ACCEPT}\" Its three rulings: (1) "
    f"\"{Q_R1}\" (2) \"{Q_R2}\" (3) \"{Q_R3}\" NP1.2, NP1.5 and NP1.10(s) put them to the owner."])

# ---------------------------------------------------------------- NP1.2
sub("  - **What it costs:** one more native run.",
    f"  - **What it costs:** one more native run. {P38}")

# ---------------------------------------------------------------- NP1.5
sub("and a registration built in the rebuilt environment and compared after the restoration gives \"not "
    "equal\", by the manifest's pin.",
    "and a registration built in the rebuilt environment and compared after the restoration gives \"not "
    "equal\", by the manifest's pin. That \"cannot decide\" assumes that version 3 validation regenerates the "
    "manifest from the live environment (the lead's ruling, Authority); the review of the version 3 documents "
    "confirms it before the first version 3 registration. If validation does not regenerate it, the result is "
    "\"not equal\", by the manifest's pin. Either way the registration is held.")
sub("; and the reference's own packet while the interpreter or environment at its paths is not the reference's)",
    "; the reference's own packet while the interpreter at its path is not the reference's; and, where version "
    "3 validation regenerates the manifest from the live environment, the reference's own packet while the "
    "environment at its paths is not the reference's)")
sub("stay unchanged, the copy at the same path, until the last production cell's acceptance record is signed.",
    f"stay unchanged, the copy at the same path, {FREEZE_END}.")

# ---------------------------------------------------------------- NP1.10
sub("A note after an item says how it differs from v13; an item with no note is unchanged from v13. The letters "
    "are v13's: (aj) stays retired; (c), (e), (s), (al) and (ar) are changed.",
    "A note after an item says how it differs from v14; an item with no note is unchanged from v14. The letters "
    "are v14's: (aj) stays retired; (s) is changed.")
for note in (" *Changed: when a later Kids First stratum is exploratory.*",
             " *Changed: a repair of the pilot that needs changed must-equal bytes ends the stratum.*",
             " *Changed: the other-commit case qualified; two more kinds of per-run file; rule (ii)'s substitution "
             "in building and validating; what the environment manifest records, with bytecode excluded.*",
             " *Changed: the launch hold starts at the stop; the owner's adjudication marked as the lead's reading "
             "of D36.*"):
    sub(note, "")
sub("no production cell registers: while a required pilot is pending; while an instrument finding",
    "no production cell registers: while a required pilot is pending, except that a" + P38[1:-1] +
    "; while an instrument finding")
sub("*Changed: the ending branch qualified by changed must-equal values.*",
    "*Changed: an AI_READI pilot repair after the reference run ends the stratum, in the pending-pilot "
    "clause.*")

# ---------------------------------------------------------------- write and check
out = W / REL
out.write_text(text, encoding="utf-8")
data = out.read_bytes()
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", len(data.decode("utf-8").split("\n")) - 1, "bytes", len(data))

assert "@" not in text
assert "v14 has not been reviewed" not in text
assert text.count(FREEZE_END) == 2, text.count(FREEZE_END)
assert text.count(P38) == 2, text.count(P38)          # (e) and NP1.2's cost, as whole sentences
assert text.count(P38[1:-1]) == 4, text.count(P38[1:-1])  # and the floor list and (s), inside a clause
assert text.count("(the lead's ruling, Authority); the review of the version 3 documents") == 1
letters = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*", text, flags=re.M)
assert len(letters) == 45 and letters[0] == "a" and letters[-1] == "as", len(letters)
notes = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*.*\*(?:Changed|New)[:.]", text, flags=re.M)
print("items with a change note:", notes)
assert notes == ["s"], notes
print("post-checks passed")
