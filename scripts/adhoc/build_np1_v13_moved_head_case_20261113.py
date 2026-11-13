#!/usr/bin/env python3
"""Add the moved-HEAD demonstration case to NP1 draft v13, nothing else.

Purpose: the lead accepted v13 (581b89826) and asked for one addition: a
candidate built at another commit of the same checkout, listed among the
demonstration's "cannot decide" cases in NP1.5 and in item (al), citing
native_execution_registration_v2.py:188-192 and :496-497; built again at the
reference's commit it compares equal. (al) keeps its change note, extended.
Inputs: v13 read from git at commit 581b89826 in the NP1 worktree, asserted by
sha256 7cf57199...58ed.
Output: the amendment file in the NP1 worktree, overwritten; prints its
sha256, line count and byte count, and runs post-checks.
Serves: NP1 draft v13 (branch claude/native-production-amendment-np1-20261112).
Date: 2026-11-13. Written by a copy of the Claude lead; left uncommitted in
the report worktree, as directed.
"""
import hashlib
import re
import subprocess
from pathlib import Path

W = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
         "claude-native-production-amendment-np1-20261112")
REL = "notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md"
V13_COMMIT = "581b898269e8dbf6537f2db68bf9827e3a781c27"
V13_SHA = "7cf571994c22693014b96a22c94e891980f906602582be6486764209326f58ed"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V13_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V13_SHA, "v13 bytes differ from the accepted draft"
text = raw.decode("utf-8")
before_lines = len(text.split("\n")) - 1
assert before_lines == 652


def sub(old, new):
    global text
    n = text.count(old)
    assert n == 1, (n, old[:90])
    text = text.replace(old, new)


CITE = "(`native_execution_registration_v2.py:188–192`, `:496–497`)"

# NP1.5, the demonstration's "cannot decide" cases.
sub("a wrong or missing floor basis, which the parser refuses; and a moved checkout or interpreter path, "
    "on either format, a hold until the move is undone;",
    "a wrong or missing floor basis, which the parser refuses; a moved checkout or interpreter path, on "
    "either format, a hold until the move is undone; and a candidate built at another commit of the same "
    "checkout, which the validators refuse because they compare the commit a packet records with the "
    f"live one {CITE}; once the reference's commit is checked out again, the candidate built there "
    "gives \"equal\";")
# NP1.10(al), its demonstration sentence and its change note.
sub("The data file is demonstrated on every listed case before the canary's registration and again "
    "whenever the format changes before the reference;",
    "The data file is demonstrated on every listed case, among them a candidate built at another commit "
    f"of the same checkout, which gives \"cannot decide\" {CITE} and, built again at the reference's "
    "commit, \"equal\", before the canary's registration and again whenever the format changes before "
    "the reference;")
sub("*Changed: the commit a registration records is identical, and every registration is built at the "
    "reference's commit.*",
    "*Changed: the commit a registration records is identical, every registration is built at the "
    "reference's commit, and the demonstration includes a candidate built at another commit.*")

out = W / REL
out.write_text(text, encoding="utf-8")
data = out.read_bytes()
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", len(data.decode("utf-8").split("\n")) - 1, "bytes", len(data))
assert len(text.split("\n")) - 1 == before_lines
assert "@" not in text
assert text.count("another commit of the same checkout") == 2
notes = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*.*\*(?:Changed|New)[:.]", text, flags=re.M)
assert sorted(notes) == ["al", "ar"], notes
print("post-checks passed")
