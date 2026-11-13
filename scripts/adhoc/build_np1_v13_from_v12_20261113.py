#!/usr/bin/env python3
"""Build draft v13 of analysis plan amendment NP1 from draft v12.

Purpose: apply the lead's four v13 rulings (coordination record, entry of
2026-11-13T07:14:52Z): source_commit must-equal with the checkout's HEAD under
the restoration rule; the unrealizable version-2 "version changed, bytes
unchanged" case dropped; the test for a later stratum; prerequisite states out
of the ratified text. Exact substring edits whose originals are asserted to
occur once, so the change from v12 to v13 is reproducible.
Inputs: v12 read from git at commit 56f0c060e in the NP1 worktree, asserted by
sha256 591c4f3f...615c.
Output: the amendment file in the NP1 worktree, overwritten with v13; prints
its sha256, line count and byte count, and runs post-checks.
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
V12_COMMIT = "56f0c060e02e752d2ca1284fc4e091c219e0230c"
V12_SHA = "591c4f3f69635090677ef209ef1f82b9e729edfea129ba58229e1e7755f7615c"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V12_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V12_SHA, "v12 bytes differ from the accepted draft"
text = raw.decode("utf-8")
assert text.endswith("\n") and len(text.split("\n")) - 1 == 644


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


def replace_line(prefix, new_lines):
    global text
    lines, i = line_starting(prefix)
    lines[i:i + 1] = new_lines
    text = "\n".join(lines)


def replace_lines(start_prefix, end_prefix, new_lines):
    global text
    lines, i = line_starting(start_prefix)
    _, j = line_starting(end_prefix)
    assert j >= i, (i, j)
    lines[i:j + 1] = new_lines
    text = "\n".join(lines)


def insert_after(prefix, new_lines):
    global text
    lines, i = line_starting(prefix)
    lines[i + 1:i + 1] = new_lines
    text = "\n".join(lines)


# ---------------------------------------------------------------- header
sub("**Status: draft v12, written by a copy of the Claude lead on 2026-11-13.**",
    "**Status: draft v13, written by a copy of the Claude lead on 2026-11-13.**")
insert_after("- **v11** (commit `890ee25c567e328f9d9c6feac3ffb9053511a781`", [
    "- **v12** (commit `56f0c060e02e752d2ca1284fc4e091c219e0230c`, file sha256 "
    "`591c4f3f69635090677ef209ef1f82b9e729edfea129ba58229e1e7755f7615c`) was not reviewed. The lead "
    "accepted it, with the departures from the lead's rulings that its author recorded, and gave four "
    "further rulings, which v13 applies (Authority)."])
insert_after("  - scopes the exploratory test to strata that follow this one after the reference run;", [
    "- **v12 → v13 applies the lead's four further rulings** (Authority):",
    "  - the commit a registration records, `source_commit`, is an identical field: every registration "
    "of the stratum is built at the reference's commit, the production checkout's HEAD does not move "
    "from the reference's registration until the last production cell's acceptance record is signed, "
    "run data are committed from a separate worktree or after the stratum, and checking the "
    "reference's commit out again is a restoration (NP1.5, NP1.10(al), (ar));",
    "  - an interpreter version changed with its bytes unchanged is not a case a real interpreter "
    "produces: it leaves the demonstration, and a changed interpreter version gives \"not equal\" on "
    "either format (NP1.5);",
    "  - a stratum after the reference run is confirmatory only if it begins at a boundary of "
    "NP1.10(ar) and every change it carries has the reason the bar requires, or if the amendment that "
    "begins it was ratified before the reference run's launch word; otherwise it is exploratory "
    "(NP1.5, NP1.10(ar));",
    "  - the state of each prerequisite leaves the text: NP1.7 lists each prerequisite and its "
    "deadline, and their states are kept in the coordination record and on the owner's ballot (NP1.4, "
    "NP1.5, NP1.7)."])
sub("- **v12 has not been reviewed.**", "- **v13 has not been reviewed.**")
sub("and the receipt-policy parser's floor check (`native_shared_contract.py:797–812`).\n",
    "and the receipt-policy parser's floor check (`native_shared_contract.py:797–812`). For v13 the "
    "author read, at the cited commit, how the dependency registry records the checkout's HEAD "
    "(`native_supervisor_authority_v2.py:24–26`, `:46–47`) and how the execution verifier compares a "
    "packet's recorded dependency identity with the live one "
    "(`native_execution_registration_v2.py:176–192`, `:383`, `:489–497`, `:532–533`).\n")

# ---------------------------------------------------------------- responses
sub("Each issue stays open until a re-check of v12 confirms the answer.",
    "Each issue stays open until a re-check of v13 confirms the answer; v12 was not reviewed.")
sub("| v11 finding | Issue | Answer in v12 | Where |", "| v11 finding | Issue | Answer in v13 | Where |")
sub("a changed interpreter whose bytes differ gives \"not equal\" on either format, and a changed "
    "interpreter version alone gives \"not equal\" on version 3 and \"cannot decide\" on version 2.",
    "a changed interpreter version gives \"not equal\" on either format: recomposition checks the "
    "recorded version, and a real version change changes the pinned bytes.")
sub("| #6134 | The test applies only to a stratum that follows this one after the reference run. Before "
    "the reference exists,",
    "| #6134 | A stratum after the reference run is confirmatory only if it begins at a boundary of (ar) "
    "and every change it carries has the reason the bar requires, or if the amendment that begins it "
    "was ratified before the reference run's launch word; otherwise it is exploratory. Before the "
    "reference exists,")

# ---------------------------------------------------------------- authority
sub("That is a must-equal implementation pin, so a changed interpreter whose bytes differ gives \"not "
    "equal\" on version 2 as well. \"Cannot decide\" is version 2's result only where the recorded "
    "version changes and the interpreter's bytes do not (NP1.5).",
    "That is a must-equal implementation pin, so a changed interpreter gives \"not equal\" on version 2 "
    "as well: recomposition checks the recorded version (`native_shared_registration.py:113–120`), and "
    "a real version change changes the pinned bytes. The lead accepted this reading (entry of "
    "2026-11-13T07:14:52Z, below), and v13 drops the case of a version changed with the bytes "
    "unchanged, which no real interpreter produces (NP1.5).")
insert_after("    - **Where this draft departs from that entry**", [
    "  - **The rulings for v13** (entry of 2026-11-13T07:14:52Z): \"The lead accepted the copy's "
    "departures.\" and \"**Draft v13 is being written with four more rulings.** (1) `source_commit` is "
    "must-equal: the production checkout's HEAD does not move from the reference's registration to "
    "the last acceptance record, and run data are committed from another worktree. (2) The version-2 "
    "\"version changed, bytes unchanged\" case is dropped as unrealizable. (3) A later stratum is "
    "confirmatory only at an (ar) boundary, or under an amendment ratified before the reference run's "
    "launch word. (4) Prerequisite states leave the ratified text for this record and the ballot.\" "
    "NP1.5, NP1.7 and NP1.10(al) and (ar) put them to the owner."])

# ---------------------------------------------------------------- NP1.4 and NP1.5: state readings
sub("(D141). NP1.7 gives its state. **This item depends on (m):**",
    "(D141). NP1.7 gives its deadline. **This item depends on (m):**")
sub("- **A defect at the cited commit, since repaired on the candidate (#5939).**",
    "- **A defect at the cited commit (#5939).**")
sub("Its repair is a prerequisite of any pilot (NP1.7 gives its state),",
    "Its repair is a prerequisite of any pilot (NP1.7),")
sub(" Per the lead's record both are applied on the published candidate (NP1.7).", "")
sub("which the owner approved with the changed pin's hash (D146, quoted under Authority); per the lead's "
    "record it is applied on the published candidate (NP1.7).",
    "which the owner approved with the changed pin's hash (D146, quoted under Authority).")
sub("which takes it out of the recorder line; per the lead's record that change is on the published "
    "candidate (NP1.7).",
    "which takes it out of the recorder line.")
sub("Both are an engineering prerequisite, due before the canary's registration, assigned and not written "
    "(NP1.7).",
    "Both are an engineering prerequisite, due before the canary's registration (NP1.7).")
sub("This is an engineering prerequisite and is not written (above).",
    "This is an engineering prerequisite (above).")

# ---------------------------------------------------------------- NP1.5: the commit
sub("the closed dependency registry of the package's own source files and of the interpreter, the "
    "checkout path,",
    "the closed dependency registry of the package's own source files and of the interpreter, the "
    "commit it was built at (the registry's `source_commit`), the checkout path,")
sub("**Which commit a registration was built from does not matter; only its pinned bytes do.**",
    "**Every registration of the stratum is built at the reference's commit** (the commit, below).")
sub("the gate finds it \"not equal\", or \"cannot decide\" where the difference is a moved checkout or "
    "interpreter path, which holds it until the move is undone. That covers a change to a pinned "
    "file, an asset, the binary, the base system instructions, the selection bounds, the checkout "
    "path, the interpreter,",
    "the gate finds it \"not equal\", or \"cannot decide\" where the difference is a moved checkout or "
    "interpreter path or another commit, a hold until the reference's paths and commit are restored. "
    "That covers a change to a pinned file, an asset, the binary, the base system instructions, the "
    "selection bounds, the checkout path, the checkout's commit, the interpreter,")
sub("      - **Restoring host state to the reference's bytes and paths is not a repair under this item.**",
    "      - **Restoring host state to the reference's bytes, paths and commit is not a repair under this "
    "item.**")
sub("**Restoring that state to the reference's bytes and paths is not a repair under NP1.10(ar):**",
    "**Restoring that state to the reference's bytes, paths and commit is not a repair under "
    "NP1.10(ar):**")
insert_after("    - **the checkout.** Its absolute path is recorded", [
    "    - **the commit.** The dependency registry records the checkout's HEAD commit as "
    "`source_commit` (`native_supervisor_authority_v2.py:24–26`, `:46–47`). It is an identical field: "
    "every registration of the stratum is built at the reference's commit, and the production "
    "checkout's HEAD does not move from the reference's registration until the last production cell's "
    "acceptance record is signed. Run data are committed from a separate worktree, or after the "
    "stratum. If HEAD moves, the validators refuse the reference's own packet, because they compare the "
    "dependency identity a packet records, its commit included, with the live one "
    "(`native_execution_registration_v2.py:188–192`, `:496–497`); no comparison can rest on that "
    "packet, so every result is \"cannot decide\", a hold (NP1.5's precedence, below). A registration "
    "made before the move cannot be launched while HEAD is elsewhere: launch re-verification refuses "
    "the same difference (`native_shared_registration_orchestration.py:163–165`). Checking the "
    "reference's commit out again, with no pinned file changed, is a restoration under the rule above, "
    "and it permits another comparison. A registration built while HEAD was elsewhere records that "
    "commit and can never be found equal; it is built again after the restoration;"])
sub("the schema closure, the closed dependency registry, the Claude Code binary's sha256,",
    "the schema closure, the closed dependency registry and the commit it records as `source_commit`, "
    "the Claude Code binary's sha256,")
sub("A path is not a sha256 pin and never takes it.", "A path or a commit is not a sha256 pin and never takes it.")
sub("(among them a packet with a wrong or missing floor basis, and one built after the checkout or the "
    "interpreter moved)",
    "(among them a packet with a wrong or missing floor basis; one built after the checkout or the "
    "interpreter moved, or at another commit; and the reference's own packet while the checkout's HEAD "
    "is not the reference's commit)")

# ---------------------------------------------------------------- NP1.5: the interpreter version
sub("All are identical fields. An interpreter upgrade makes later registrations not equal: the "
    "registry's sha256 pin differs wherever the bytes do, and on version 3 the environment manifest's "
    "pin records the interpreter's identity (below).",
    "All are identical fields. An interpreter upgrade makes later registrations not equal: "
    "recomposition checks the recorded version (`native_shared_registration.py:113–120`), and a real "
    "version change changes the interpreter's bytes, which the registry pins by sha256, so the "
    "shortcut decides on either format; on version 3 the environment manifest's pin records the "
    "interpreter's identity as well (below).")
sub("a changed interpreter whose bytes differ, by the dependency registry's sha256 pin of them, on "
    "either format;",
    "a changed interpreter version, on either format, by the dependency registry's sha256 pin of the "
    "interpreter's bytes, which a real version change changes, and on version 3 also by the manifest's "
    "pin;")
sub("and, on a format that carries the environment manifest, a changed interpreter version, a changed "
    "version of a third-party distribution and a changed installed file of one, by the manifest's pin;",
    "and, on a format that carries the environment manifest, a changed version of a third-party "
    "distribution and a changed installed file of one, by the manifest's pin;")
sub("; a moved checkout or interpreter path, on either format, a hold until the move is undone; and, on "
    "version 2, which has no environment manifest, a changed interpreter version with the interpreter's "
    "bytes unchanged;",
    "; and a moved checkout or interpreter path, on either format, a hold until the move is undone;")

# ---------------------------------------------------------------- NP1.5: the test for a later stratum
sub("    - **One test for an exploratory stratum,** the same here and in NP1.10(ar). It applies only to a "
    "stratum that follows this one after the reference run: such a stratum is exploratory unless it "
    "begins at a boundary this item fixes and every change it carries has the recorded reason the bar "
    "requires. Before the reference exists,",
    "    - **One test for a later stratum,** stated here once and adopted by NP1.10(ar). A stratum that "
    "follows this one after the reference run is confirmatory only if (a) it begins at a boundary this "
    "item fixes and every change it carries has the recorded reason the bar requires, or (b) the "
    "amendment that begins it was ratified before the reference run's launch word. Otherwise it is "
    "exploratory. **A BC1-parity stratum** (NP1.9) **or one with a changed procedure** (NP1.7) carries "
    "a change that none of the bar's reasons covers, so (a) cannot hold for it: it is confirmatory only "
    "if its amendment was ratified before the reference run's launch word, and otherwise it is "
    "exploratory. Before the reference exists,")

# ---------------------------------------------------------------- NP1.7: prerequisites without states
replace_lines("- **Code that has to exist, each item with one deadline.**",
              "    - **The environment manifest** (NP1.5): the version 3 preparation and execution documents", [
    "- **Code that has to exist, each item with one deadline.** These are engineering prerequisites. "
    "The list and its deadlines are the lead's, and NP1.10(aq) puts them to the owner. No \"no\" to an "
    "item of this amendment adds to them (NP1.10). This text lists each prerequisite and its deadline; "
    "their current states are kept in the coordination record and on the owner's ballot, not here.",
    "  - **Before the canary's registration,** so that the canary runs what production is meant to run. "
    "Repairs the canary reveals may still change the source before the CHORUS reference pilot "
    "registers (NP1.6):",
    "    - N1.9's list.",
    "    - **#5939, the pending floor** (NP1.5), with its review follow-ups #5994 and #5995.",
    "    - **#5966, the helper cache** under HOME, which stopped the public completion path, with the two "
    "gaps in its tests, #6030 and #6031.",
    "    - **#5967, the failure record** when the runtime validation itself fails, without which there is "
    "no exact failed readback (N1.4(A) item 6), with #6015.",
    "    - **The retention change** (NP1.4; answered keep, D141), with #6016.",
    "    - **The launch sequence, #5989 to #5993, with #6047, #6048 and #6074.** #6049 is a known limit "
    "that the lead ruled not blocking for the canary.",
    "    - **#6046, the power check** before a launch sequence starts, and a record of a host sleep during "
    "a run: the lead's decision (Authority).",
    "    - **#6065, the short recorder line:** the render specification passed to the recorder through "
    "the controller's environment, with its validation finding #6111. The lead set it before the "
    "canary's registration (Authority): the first direct CHORUS canary was disqualified at its recorder "
    "line after a complete generation (#2282).",
    "    - **The two-set run-limits code** (NP1.10(ab); D143).",
    "    - **The basis change** (NP1.5; answered at-receipt, D140), in D140's form: a numeric floor "
    "requires `basis: receipted_part`.",
    "    - **The changed policy asset:** the pending-floor sentence the owner chose (D142) and the "
    "sentence that names the at-receipt basis. The owner approved the asset and the pin registry's new "
    "hash together (D146).",
    "    - **The gate's script and data file** (NP1.5): the data file a closed field-level schema, "
    "reviewed by both reviewers against NP1.5 and demonstrated on rehearsal registration packets in the "
    "canary's registration format, with the results recorded with the canary's registration; the "
    "demonstration is repeated on each later format before the reference (NP1.5). Its "
    "environment-manifest cases follow NP1.10(as): if (as) is answered no, they are not applicable "
    "before the canary and are required in full before the first version 3 registration; if it is "
    "answered yes, they are required before the canary's registration. The demonstration also shows "
    "which of the two probe rules applies to the run on the reference pilot's own packet (NP1.5). The "
    "earlier replay comparison is a development aid outside this amendment; an independent review found "
    "it unfit to be the gate (#6066 to #6073).",
    "    - **The stratum's selection bounds** (NP1.5; NP1.10(ap)): one set, with its derivation from the "
    "largest declared input and its margin, recorded with the canary's registration.",
    "  - **Before NP1b,** because NP1b pins it:",
    "    - **the recall adapter** that applies the plan's recall counters, \"a script pinned by sha256 in "
    "the P4b amendment, before any confirmatory record exists; on the 12 historical v8 records it must "
    "reproduce this row's listed values, as a check of the adapter, not of any comparator\" (plan line "
    "1873; NP1.3).",
    "  - **Before the CHORUS reference pilot's registration at the latest,** and before the canary's "
    "registration if NP1.10(as) is answered yes:",
    "    - **The environment manifest** (NP1.5): the version 3 preparation and execution documents with "
    "the `environment_manifest` pin, the manifest regenerated and checked at preparation and at "
    "dispatch, and version 2 refused for new registrations once version 3 is in."])

# ---------------------------------------------------------------- NP1.10
sub("A note after an item says how it differs from v11; an item with no note is unchanged from v11. The "
    "letters are v11's: (aj) stays retired; (aa), (al), (aq), (ar) and (s) are changed.",
    "A note after an item says how it differs from v12; an item with no note is unchanged from v12. The "
    "letters are v12's: (aj) stays retired; (al) and (ar) are changed.")
for note in (" *Changed: a \"cannot decide\" on the AI_READI pilot's registration whose cause is a defect "
             "under (ar) ends the stratum.*",
             " *Changed: the reference pilot's own gate runs bound by hash.*",
             " *Changed: the deadline of the demonstration's environment-manifest cases follows (as).*"):
    sub(note, "")
# (al)
sub("is identical, the checkout path, the interpreter's identity and path and the environment manifest "
    "among them;",
    "is identical, the checkout path, the commit recorded as `source_commit`, the interpreter's "
    "identity and path and the environment manifest among them;")
sub("a moved checkout or interpreter path is no such pin and gives \"cannot decide\", a hold until the "
    "move is undone;",
    "a moved checkout or interpreter path, or another commit, is no such pin and gives \"cannot "
    "decide\", a hold until the reference's paths and commit are restored;")
sub("production depends on the host state NP1.5 names, and restoring that state is not a repair (NP1.5, "
    "NP1.6, NP1.7). *Changed: the gate's results by its precedence (the floor's basis, moved paths, the "
    "interpreter); the environment-manifest cases conditional on (as); per-registration paths, the "
    "floor's registration among them; the run on the reference pilot's own packet, with its probe rules "
    "and the case of no other project.*",
    "production depends on the host state NP1.5 names, the checkout's commit among them, and restoring "
    "that state is not a repair (NP1.5, NP1.6, NP1.7). *Changed: the commit a registration records is "
    "identical, and every registration is built at the reference's commit.*")
# (ar)
sub("Restoring host state to the reference's bytes and paths is not a repair. This stratum's results "
    "stand under the plan's kinds of missing; a later stratum is reported separately, never pooled with "
    "this one and never put in its place. A stratum that follows this one after the reference run is "
    "exploratory unless it begins at a boundary this item fixes and every change it carries has the "
    "recorded reason the bar requires; before the reference exists, a repair after a failed canary or "
    "reference-pilot attempt follows the pre-reference rules and makes nothing exploratory, and a "
    "stratum begun then by a prospective amendment is classed by that amendment, under the bar. A change "
    "for any other reason is not made during production (NP1.5). *Changed: every registration and "
    "launch held while a classification is open; an unknown stop's defect filed at its "
    "reclassification; an unlaunched registration withdrawn; the exploratory test scoped to strata after "
    "the reference run.*",
    "Restoring host state to the reference's bytes, paths and commit is not a repair. This stratum's "
    "results stand under the plan's kinds of missing; a later stratum is reported separately, never "
    "pooled with this one and never put in its place, and whether it is confirmatory or exploratory is "
    "decided by the one test NP1.5 states under this item. A change for any other reason is not made "
    "during production (NP1.5). *Changed: the commit under the restoration rule; the test for a later "
    "stratum, stated once in NP1.5.*")

# ---------------------------------------------------------------- write and check
out = W / REL
out.write_text(text, encoding="utf-8")
data = out.read_bytes()
lines = data.decode("utf-8").split("\n")
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", len(lines) - 1, "bytes", len(data))

assert "@" not in text, "at-sign in the draft"
for stale in ("Which commit a registration was built from", "bytes and paths", "gives its state",
              "with the interpreter's bytes unchanged", "Assigned, not written", "assigned, not written",
              "Its state is not on the lead's record", "None of this code is merged",
              "v12 has not been reviewed", "One test for an exploratory stratum"):
    assert stale not in text, stale
# Prerequisite states: no "published candidate" or "per the lead's record" outside the header and Authority,
# except the NP1.2 and NP1.7 readings of a helper's input checks and measurements, which are not states of a
# prerequisite.
body = text.split("## NP1.1 What this amendment does", 1)[1]
assert "published candidate" not in body, "a prerequisite state left in the body"
left = [l.strip()[:40] for l in body.split("\n") if "per the lead's record" in l.lower()]
print("'per the lead's record' left in the body:", left)
# The helper's input checks (NP1.2), the version 3 documents' design (NP1.5) and the helper's input
# measurement (NP1.7): none is the state of a prerequisite.
assert left == ["- **Where the inputs stand.** Per the le", "- **The documents.** Per the lead's reco",
                "- **The inputs point the same way.** Per"], left
letters = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*", text, flags=re.M)
assert len(letters) == 45 and letters[0] == "a" and letters[-1] == "as", len(letters)
notes = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*.*\*(?:Changed|New)[:.]", text, flags=re.M)
print("items with a change note:", notes)
assert sorted(notes) == ["al", "ar"], notes
assert text.count("source_commit") >= 6
print("post-checks passed")
