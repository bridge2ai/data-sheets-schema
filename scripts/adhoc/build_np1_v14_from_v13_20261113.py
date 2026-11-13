#!/usr/bin/env python3
"""Build draft v14 of analysis plan amendment NP1 from draft v13.

Purpose: apply the reviewers' smallest fixes from the two confirmation reviews
of v13 (issues #6173 to #6183), with the lead's rulings where a review left a
choice (coordination record, entries of 2026-11-13T07:14:52Z, 07:32:30Z and
08:28:36Z, and the lead's brief and its correction to ruling 9). Exact
substring edits whose originals are asserted to occur once; quotations of the
coordination record are checked against it.
Inputs: v13 read from git at commit 668d62c43 in the NP1 worktree, asserted by
sha256 db0905e5...3869; STATUS.md in the primary checkout, read only.
Output: the amendment file in the NP1 worktree, overwritten with v14; prints
its sha256, line count and byte count, and runs post-checks.
Serves: NP1 draft v14 (branch claude/native-production-amendment-np1-20261112).
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
V13_COMMIT = "668d62c431e9aaee93fc7ba3744f777b26797da3"
V13_SHA = "db0905e5fcb9c14e13b13e772cc184bb7bce95d9617eee3faf222dd70a5a3869"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V13_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V13_SHA, "v13 bytes differ from the reviewed draft"
text = raw.decode("utf-8")
assert len(text.split("\n")) - 1 == 652


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


def insert_before(prefix, new_lines):
    global text
    lines, i = line_starting(prefix)
    lines[i:i] = new_lines
    text = "\n".join(lines)


# Quotations of the coordination record used below; each is checked against STATUS.
Q_EM5 = ("the manifest lists every unowned file under the import roots by path, size and sha256, and the "
         "primary environment is not modified")
Q_ROOTS = ("**The lead adopted its recommendation:** the first-party checkout and the standard library stay "
           "excluded (source pins and interpreter identity), every unowned file in the remaining import roots "
           "is inventoried, and the manifest names the excluded roots.")
Q_PYC = ("`.pyc` files are excluded from the manifest's must-equal content. The registered environment sets "
         "`PYTHONDONTWRITEBYTECODE=1`, but tests and the API arm can write bytecode.")
Q_ANCHOR = "Anchor (b) on the first launch word of the CHORUS reference pilot."
Q_API = ("API comparison runs use another checkout during the stratum, because `api_runner` appends to the "
         "pinned `digest_inventory.yaml`.")
Q_D36 = "Mark D36 as the lead's reading for the owner's adjudication."
status_text = STATUS.read_text(encoding="utf-8")
for quote in (Q_EM5, Q_ROOTS, Q_PYC, Q_ANCHOR, Q_API, Q_D36):
    assert status_text.count(quote) == 1, quote[:60]

FIRST_WORD = "the first launch word of the CHORUS reference pilot"

# ---------------------------------------------------------------- header
sub("**Status: draft v13, written by a copy of the Claude lead on 2026-11-13.**",
    "**Status: draft v14, written by a copy of the Claude lead on 2026-11-13.**")
insert_after("- **v12** (commit `56f0c060e02e752d2ca1284fc4e091c219e0230c`", [
    "- **v13** (commit `668d62c431e9aaee93fc7ba3744f777b26797da3`, file sha256 "
    "`db0905e5fcb9c14e13b13e772cc184bb7bce95d9617eee3faf222dd70a5a3869`) had two confirmation reviews, and "
    "both said \"ratifiable after listed fixes\": a Codex CLI pass (review sha256 "
    "`4ad10964e2cc08e8fd1c5b063ef3bf6a35620d7e6f80c97c4b54338d13e01a4b`; 1 P1) and a Claude reviewer, a "
    "fresh session (review sha256 `fa932272b08e5b2b371ab268b4442f8d1c5499ecc48781334eec61812f989e2a`; 2 P2, "
    "8 P3). No two of the 11 findings are on the same point; they are filed as #6173 to #6183."])
sub("  - an interpreter version changed with its bytes unchanged is not a case a real interpreter produces: it "
    "leaves the demonstration, and a changed interpreter version gives \"not equal\" on either format (NP1.5);",
    "  - an interpreter version changed with its bytes unchanged is a case which the registered interpreter, a "
    "statically linked build, does not produce: it leaves the demonstration, and a changed interpreter version "
    "gives \"not equal\" on either format when it is compared with the reference's interpreter in place (NP1.5);")
insert_after("  - the state of each prerequisite leaves the text: NP1.7 lists each prerequisite and its deadline,", [
    "- **v13 → v14 applies the reviewers' own smallest fixes, with the lead's rulings where a review left a "
    "choice** (Authority):",
    "  - the floor list ends the stratum only for a defect under NP1.10(ar) whose repair requires changed "
    "must-equal values; otherwise the registration and the floor remain held (NP1.5, NP1.10(s));",
    "  - an interpreter upgrade or a rebuilt environment at the reference's paths gives \"cannot decide\", a "
    "hold until restored, and one that cannot be undone is a pre-reservation defect (NP1.5);",
    "  - the launch hold starts at the stop, and the owner's adjudication of a disagreement between the "
    "reviewers is marked as the lead's reading of D36 (NP1.5, NP1.10(ar));",
    "  - the frozen HEAD's operating conditions, two more kinds of per-run file, the substitution rule (ii) "
    "makes, and the qualifier \"with no pinned file changed\" on the other-commit case (NP1.5, NP1.10(al));",
    "  - the test for a later stratum anchored on the first launch word of the CHORUS reference pilot, with "
    "Kids First named (NP1.2, NP1.5, NP1.10(c));",
    "  - what the environment manifest records, with bytecode excluded from its must-equal content (NP1.5, "
    "NP1.10(al));",
    "  - an AI_READI pilot repair after the reference run (NP1.5, NP1.10(e)), and the last state sentences "
    "removed (Authority)."])
sub("- **v13 has not been reviewed.**", "- **v14 has not been reviewed.**")
sub("the two reviews of v10 (#6112 to #6129) and the two reviews of v11 (#6130 to #6138), which concern code",
    "the two reviews of v10 (#6112 to #6129), the two reviews of v11 (#6130 to #6138) and the two "
    "confirmation reviews of v13 (#6173 to #6183), which concern code")
sub("are taken from the coordination record: the state of repairs on unmerged branches, and a helper's offline "
    "checks of the projects' inputs.",
    "are taken from the coordination record: a helper's offline checks of the projects' inputs, and the design "
    "of the version 3 documents.")
sub("(`native_execution_registration_v2.py:176–192`, `:383`, `:489–497`, `:532–533`).\n",
    "(`native_execution_registration_v2.py:176–192`, `:383`, `:489–497`, `:532–533`). For v14 the author "
    "read, at the cited commit, the package's source pins (`native_attribution_registration_v2.py:56–62`); "
    "and, at the candidate, the registered environment's bytecode setting "
    "(`native_shared_runtime_values.py:31–34`) and the digest ledger the API runner writes "
    "(`api_runner.py:4774–4775`; `schema_digest.py:706`, `:721–759`).\n")

# ---------------------------------------------------------------- responses
V13_TABLE = [
    "## Responses to the reviews of v13",
    "Each issue stays open until a re-check of v14 confirms the answer. \"Claude\" and \"Codex\" name the two "
    "confirmation reviews of v13. No two of their findings are on the same point, so each has its own issue.",
    "",
    "| v13 finding | Issue | Answer in v14 | Where |",
    "|---|---|---|---|",
    "| Codex P1-1: the floor list ends the stratum for every defect under (ar), while (ar) ends it only when "
    "the repair needs changed must-equal values | #6183 | The ending branch is qualified as the review wrote "
    "it: where the cause is a defect under (ar) whose repair requires changed must-equal values, including a "
    "defect in the gate's script or data file, the stratum ends at the filing; otherwise the registration and "
    "the floor remain held until resolution under (ar). The answer to #6138 below says the same | NP1.5, (s) |",
    "| Claude P2-1: an interpreter upgrade at the reference's path gives \"cannot decide\", not \"not "
    "equal\" | #6173 | Relabelled with the review's wording: the reference's own packet then fails the "
    "validators, so every comparison gives \"cannot decide\", a hold until the reference's interpreter is "
    "restored; an upgrade that cannot be undone is a pre-reservation defect under (ar); a registration built "
    "under the changed interpreter and compared after the restoration gives \"not equal\". A rebuilt "
    "environment is treated the same way. The other statements of a changed version's result now say \"when "
    "it is compared with the reference's interpreter in place\" | Header, Authority, NP1.5 |",
    "| Claude P2-2: the launch hold starts at the filing, so a registration made earlier can be launched "
    "between a stop and its classification | #6174 | A stop's classification, and the filing of its defect "
    "where it qualifies, precede the next registration and the next launch; from a stop until its "
    "classification is recorded, no attempt is launched | NP1.5, (ar) |",
    "| Claude P3-1: ruling (4) applied only in part | #6175 | The state sentence under D146 is deleted, the "
    "D139 sentence keeps only where the lead read the instruction, and the header no longer says that "
    "statements \"per the lead's record\" include the state of repairs | Header, Authority |",
    "| Claude P3-2: the other-commit case gives \"cannot decide\" only when no pinned file differs | #6176 | "
    "\"with no pinned file changed\" is added to the case, and the frozen-code paragraph reads \"where the "
    "only difference is\" | NP1.5, (al) |",
    "| Claude P3-3: the frozen HEAD's operating conditions | #6177 | The freeze also ends when this stratum or "
    "the condition ends; every file written during the stratum stays uncommitted in the production checkout "
    "or is committed from another worktree; work that needs a commit, the API comparison runs included, runs "
    "in another checkout; a file added under the pinned roots makes the reference fail, like a changed one; "
    "and anything committed at a moved HEAD is copied out before a restoring checkout | NP1.5 |",
    "| Claude P3-4: the per-run paths leave out the base system-instructions file and the observation probe's "
    "saved files | #6178 | Both are added, where a registration writes its own | NP1.5, (al) |",
    "| Claude P3-5: rule (ii) contradicts \"the only code it runs\" and does not say how its packets are "
    "built | #6179 | \"The only code it runs\" names the one substitution rule (ii) makes, and under rule (ii) "
    "packets (2) and (3) are built and validated with that substitution, which the result lists | NP1.5, (al) |",
    "| Claude P3-6: three wording gaps in the test for a later stratum | #6180 | \"or one whose procedure "
    "change is not the repair of a qualifying defect\"; (b) anchored on the first launch word of the CHORUS "
    "reference pilot; NP1.2 and (c) say that a later Kids First stratum is exploratory unless its addendum "
    "was ratified before that word | NP1.2, NP1.5, (c) |",
    "| Claude P3-7: two statements about the environment go beyond the evidence | #6181 | \"which the "
    "registered interpreter, a statically linked build, does not produce\". What the manifest records is "
    "written in under the lead's rulings, with `.pyc` files excluded from its must-equal content and what "
    "that leaves unpinned | Header, Authority, NP1.5, (al) |",
    "| Claude P3-8: after the reference run, an AI_READI pilot repair ends the stratum, and (e) and the floor "
    "list do not say so | #6182 | Both say it now, in the review's words | NP1.5, (e) |",
    "| Claude, a point that predates v12: D36 does not mention adjudicating a disagreement between the "
    "reviewers | none | The owner's adjudication of such a disagreement is marked as the lead's reading of "
    "D36 | NP1.5, (ar) |",
    "",
]
insert_before("## Responses to the reviews of v11", V13_TABLE)
sub("Each issue stays open until a re-check of v13 confirms the answer; v12 was not reviewed.",
    "The confirmation reviews of v13 found these answers resolved, except those to #6131 and #6137, which "
    "the Claude review found partly resolved, and #6138, which the Codex review found partly resolved; v14 "
    "completes those three (above). Each issue stays open until a re-check of v14 confirms the answer.")
sub("| v11 finding | Issue | Answer in v13 | Where |", "| v11 finding | Issue | Answer in v14 | Where |")
sub("a changed interpreter version gives \"not equal\" on either format: recomposition checks the recorded "
    "version, and a real version change changes the pinned bytes.",
    "a changed interpreter version gives \"not equal\" on either format when it is compared with the "
    "reference's interpreter in place: recomposition checks the recorded version, and a real version change "
    "changes the pinned bytes.")
sub("or if the amendment that begins it was ratified before the reference run's launch word; otherwise it is "
    "exploratory. Before the reference exists,",
    f"or if the amendment that begins it was ratified before {FIRST_WORD}; otherwise it is exploratory. "
    "Before the reference exists,")
sub("| #6137 | No attempt is launched while a classification is open,",
    "| #6137 | No attempt is launched from a stop until its classification is recorded, nor while a defect's "
    "classification is open,")
sub("| #6138 | Where the gate cannot decide on the AI_READI pilot's registration because of a defect under (ar), "
    "as a cause in the gate itself is, the stratum ends at the filing, before the floor and before any "
    "production cell; otherwise the registration and the floor wait |",
    "| #6138 | Where the gate cannot decide on the AI_READI pilot's registration because of a defect under (ar) "
    "whose repair requires changed must-equal values, including a defect in the gate's script or data file, "
    "the stratum ends at the filing, before the floor and before any production cell; otherwise the "
    "registration and the floor remain held until resolution under (ar) |")

# ---------------------------------------------------------------- authority
sub("D139 approved a protected file's hash; per the lead's record the four protected files are on the published "
    "candidate, which is where the lead read what the instruction carries (NP1.5).",
    "D139 approved a protected file's hash; the lead read what the instruction carries at `6561dac3c` (NP1.5).")
sub(" Per the lead's record, both files are applied on the published candidate (entry of 2026-11-13T04:46:50Z).",
    "")
sub("so a changed interpreter gives \"not equal\" on version 2 as well: recomposition checks the recorded version",
    "so a changed interpreter gives \"not equal\" on version 2 as well when it is compared with the reference's "
    "interpreter in place: recomposition checks the recorded version")
sub("which no real interpreter produces (NP1.5).",
    "which the registered interpreter, a statically linked build, does not produce (NP1.5).")
insert_after("  - **The rulings for v13** (entry of 2026-11-13T07:14:52Z)", [
    "  - **The rulings for v14** (entries of 2026-11-13T07:14:52Z, 07:32:30Z and 08:28:36Z). On the "
    f"environment manifest's census: \"{Q_EM5}\" and \"{Q_ROOTS}\" With the reviews of v13: \"{Q_PYC}\", "
    f"\"{Q_ANCHOR}\", \"{Q_API}\" and \"{Q_D36}\" The lead's brief to the author of this draft adds the "
    "rulings where a review left a choice: the reviewers' own smallest fixes are applied; an interpreter "
    "upgrade or a rebuilt environment at the reference's paths is a hold, and one that cannot be undone is a "
    "pre-reservation defect; the launch hold starts at the stop; every file written during the stratum stays "
    "uncommitted in the production checkout or is committed from another worktree; and both kinds of file "
    "the Claude review names join the per-run paths. NP1.2, NP1.5 and NP1.10(c), (e), (s), (al) and (ar) put "
    "them to the owner."])

# ---------------------------------------------------------------- NP1.2: Kids First
sub("a field the gate holds identical (NP1.5). Until such an addendum it has no native cell.",
    "a field the gate holds identical (NP1.5). By the test for a later stratum (NP1.5), such a stratum is "
    f"exploratory unless its addendum was ratified before {FIRST_WORD}. Until such an addendum it has no "
    "native cell.")

# ---------------------------------------------------------------- NP1.5: frozen code and (ar)'s body
sub("or \"cannot decide\" where the difference is a moved checkout or interpreter path or another commit,",
    "or \"cannot decide\" where the only difference is a moved checkout or interpreter path or another commit,")
sub("A stop's defect is filed with the stop's classification, and a pre-reservation defect when the registration "
    "it prevents is held; either is filed before the next registration under this amendment.",
    "A stop's defect is filed with the stop's classification, and a pre-reservation defect when the registration "
    "it prevents is held; either is filed before the next registration under this amendment. A stop's "
    "classification, and the filing of its defect where it qualifies, precede the next registration and the "
    "next launch under this amendment. From a stop until its classification is recorded, no attempt is "
    "launched under this amendment.")
sub("as for any disagreement between the reviewers (D36).",
    "as for any disagreement between the reviewers (the lead's reading of D36).")
sub("(a) it begins at a boundary this item fixes and every change it carries has the recorded reason the bar "
    "requires, or (b) the amendment that begins it was ratified before the reference run's launch word. "
    "Otherwise it is exploratory. **A BC1-parity stratum** (NP1.9) **or one with a changed procedure** (NP1.7) "
    "carries a change that none of the bar's reasons covers, so (a) cannot hold for it: it is confirmatory "
    "only if its amendment was ratified before the reference run's launch word, and otherwise it is "
    "exploratory.",
    "(a) it begins at a boundary this item fixes and every change it carries has the recorded reason the bar "
    f"requires, or (b) the amendment that begins it was ratified before {FIRST_WORD}. Otherwise it is "
    "exploratory. **A BC1-parity stratum** (NP1.9) **or one whose procedure change** (NP1.7) **is not the "
    "repair of a qualifying defect** carries a change that none of the bar's reasons covers, so (a) cannot "
    f"hold for it: it is confirmatory only if its amendment was ratified before {FIRST_WORD}, and otherwise "
    "it is exploratory.")

# ---------------------------------------------------------------- NP1.5: host state
sub("All are identical fields. An interpreter upgrade makes later registrations not equal: recomposition checks "
    "the recorded version (`native_shared_registration.py:113–120`), and a real version change changes the "
    "interpreter's bytes, which the registry pins by sha256, so the shortcut decides on either format; on "
    "version 3 the environment manifest's pin records the interpreter's identity as well (below). An "
    "interpreter at another path makes them \"cannot decide\", a hold until the move is undone (the checkout, "
    "below).",
    "All are identical fields. An interpreter upgrade at the reference's path makes the reference's own packet "
    "fail the validators (`native_execution_registration_v2.py:188–192`, `:496–497`; "
    "`native_shared_registration.py:113–120`), so every comparison gives \"cannot decide\", a hold until the "
    "reference's interpreter is restored. An upgrade that cannot be undone is a pre-reservation defect under "
    "NP1.10(ar). A registration built under the changed interpreter and compared after the restoration gives "
    "\"not equal\", by the registry's sha256 pin of the interpreter and, on version 3, by the manifest's pin. "
    "A registration built under an interpreter at another path gives \"cannot decide\", a hold until the move "
    "is undone (the checkout, below).")
sub("So a rebuilt environment whose distributions or installed files differ makes later registrations not "
    "equal, and a change after a registration is prepared holds its launch;",
    "A rebuilt environment at the reference's paths is treated the same way: while its distributions or "
    "installed files differ from the reference's, the reference's own packet fails the validators and every "
    "comparison gives \"cannot decide\", a hold until the reference's environment is restored; a rebuild that "
    "cannot be undone is a pre-reservation defect under NP1.10(ar); and a registration built in the rebuilt "
    "environment and compared after the restoration gives \"not equal\", by the manifest's pin. A change "
    "after a registration is prepared holds its launch;")
sub("every registration of the stratum is built in the reference's checkout, at its path, and the files the "
    "registration pins must not change.",
    "every registration of the stratum is built in the reference's checkout, at its path, and the files the "
    "registration pins must not change. A file added under the pinned roots makes the reference's packet "
    "fail, like a changed one: the package's pins cover every `.py`, `.yaml` and `.json` file under "
    "`src/data_sheets_schema` in the working tree, tracked or not (`native_attribution_registration_v2.py:56–62`).")
sub("and the production checkout's HEAD does not move from the reference's registration until the last "
    "production cell's acceptance record is signed. Run data are committed from a separate worktree, or after "
    "the stratum.",
    "and the production checkout's HEAD does not move from the reference's registration until the last "
    "production cell's acceptance record is signed, or until this stratum or the native shared-v1 condition "
    "ends, whichever comes first. Every file written during the stratum stays uncommitted in the production "
    "checkout or is committed from another worktree: run data, the floor's registration, gate corrections, "
    "reviews and acceptance records. Work that needs a commit runs in another checkout. That includes the API "
    "comparison runs, because the API runner appends to the pinned "
    "`src/data_sheets_schema/schema/digest_inventory.yaml` (at the candidate, `api_runner.py:4774–4775`; "
    "`schema_digest.py:706`, `:721–759`).")
sub("Checking the reference's commit out again, with no pinned file changed, is a restoration under the rule "
    "above, and it permits another comparison.",
    "Before a restoring checkout, anything committed at the moved HEAD is copied out, because checking the "
    "reference's commit out again removes from the working tree the files that only the moved commit tracks. "
    "Checking the reference's commit out again, with no pinned file changed, is a restoration under the rule "
    "above, and it permits another comparison.")

# ---------------------------------------------------------------- NP1.5: the gate
sub("from source bytes it has first verified to equal the reference run's own source export. It never runs",
    "from source bytes it has first verified to equal the reference run's own source export, and, where rule "
    "(ii) applies, the one substitution that rule names (below). It never runs")
sub("probe and receipt-policy registration files. Their contents are judged by the rules here,",
    "probe and receipt-policy registration files, and the base system-instructions file and the observation "
    "probe's saved transcript, request and observation files, where a registration writes its own. Their "
    "contents are judged by the rules here,")
sub("    - **What it records.** The interpreter's semantic identity: its implementation, version and build. And, "
    "sorted and unique, each third-party distribution the native interpreter can import, with its name, its "
    "version and the sha256 of its installed `RECORD` file. The project's own package is covered by the "
    "source pins and is not in it.",
    "    - **What it records** (the lead's rulings, Authority). The interpreter's semantic identity: its "
    "implementation, version and build. Sorted and unique, each third-party distribution the native "
    "interpreter can import, with its name, its version, the sha256 of its installed `RECORD` file and the "
    "installed files verified against that `RECORD`. Every unowned file, one that no distribution's `RECORD` "
    "lists, by path, size and sha256, under the import roots other than the first-party checkout and the "
    "standard library, which the source pins and the interpreter's identity cover. And the excluded roots, "
    "named. The project's own package is covered by the source pins and is not in it.")
sub("Entries listed without a hash, such as the `RECORD` file itself and compiled `.pyc` files, are named in "
    "the manifest as unverified, by kind, with their count.",
    "Entries listed without a hash, such as the `RECORD` file itself, are named in the manifest as "
    "unverified, by kind, with their count.")
insert_after("    - **What generating it checks.** It is regenerated at preparation and again at dispatch.", [
    "    - **Bytecode** (the lead's rulings, Authority). `.pyc` files are excluded from the manifest's "
    "must-equal content: they are neither listed nor counted. Python writes bytecode on import. The "
    "registered environment sets `PYTHONDONTWRITEBYTECODE=1` (candidate `native_shared_runtime_values.py:34`), "
    "so the native child and its helpers write no bytecode; other uses of the same environment, such as tests "
    "or the API arm, can, which is why `.pyc` files are excluded from the manifest's must-equal content. What "
    "this leaves unpinned: an existing `.pyc` whose source metadata matches is still used."])
sub("and the reference's own packet while the checkout's HEAD is not the reference's commit)",
    "the reference's own packet while the checkout's HEAD is not the reference's commit; and the reference's "
    "own packet while the interpreter or environment at its paths is not the reference's)")
sub("and a candidate built at another commit of the same checkout, which the validators refuse",
    "and a candidate built at another commit of the same checkout with no pinned file changed, which the "
    "validators refuse")
sub("**(ii)** If the demonstration shows that the unchanged validators cannot accept such a probe, the gate "
    "validates (2) and (3) with only the saved-probe check replaced by a recomputation of the expected "
    "binding, and its result lists that substitution.",
    "**(ii)** If the demonstration shows that the unchanged validators cannot accept such a probe, only the "
    "saved-probe check is replaced by a recomputation of the expected binding: packets (2) and (3) are built "
    "and validated with the same substitution, and the result lists it.")

# ---------------------------------------------------------------- NP1.5: the floor list
sub("    - **a required pilot is still pending,** or waits on an instrument or unknown case (NP1.6): the floor "
    "waits for it;",
    "    - **a required pilot is still pending,** or waits on an instrument or unknown case (NP1.6): the floor "
    "waits for it. After the reference run, a stop or instrument case of the AI_READI pilot whose repair "
    "needs changed must-equal bytes ends this stratum at its filing (NP1.10(ar)), before the floor and before "
    "any production cell;")
sub("that registration waits, and so does the floor. Where the cause is a defect under NP1.10(ar), as a cause "
    "in the gate itself is, the floor does not wait: this stratum ends at the filing, before the floor and "
    "before any production cell;",
    "that registration waits, and so does the floor. Where the cause is a defect under NP1.10(ar) whose repair "
    "requires changed must-equal values, including a defect in the gate's script or data file, the stratum "
    "ends at the filing, before the floor and before any production cell. Otherwise the registration and the "
    "floor remain held until resolution under NP1.10(ar);")

# ---------------------------------------------------------------- NP1.10
sub("A note after an item says how it differs from v12; an item with no note is unchanged from v12. The letters "
    "are v12's: (aj) stays retired; (al) and (ar) are changed.",
    "A note after an item says how it differs from v13; an item with no note is unchanged from v13. The letters "
    "are v13's: (aj) stays retired; (c), (e), (s), (al) and (ar) are changed.")
# (c)
sub("and the profile is a field the gate holds identical. A no returns this item for redrafting (NP1.2).",
    "and the profile is a field the gate holds identical. A later Kids First stratum is exploratory unless its "
    f"addendum was ratified before {FIRST_WORD} (NP1.5). A no returns this item for redrafting (NP1.2). "
    "*Changed: when a later Kids First stratum is exploratory.*")
# (e)
sub("- **(e)** One native AI_READI pilot, not a replicate, with the floor pending, accepted before the floor's "
    "value is computed. A no means the floor comes from the CHORUS reference run alone, and AI_READI's first "
    "run is its first replicate (NP1.2).",
    "- **(e)** One native AI_READI pilot, not a replicate, with the floor pending, accepted before the floor's "
    "value is computed. After the reference run, a stop or instrument case of the AI_READI pilot whose repair "
    "needs changed must-equal bytes ends this stratum at its filing (NP1.10(ar)), before the floor and before "
    "any production cell. A no means the floor comes from the CHORUS reference run alone, and AI_READI's first "
    "run is its first replicate (NP1.2). *Changed: a repair of the pilot that needs changed must-equal bytes "
    "ends the stratum.*")
# (s)
sub("while the gate cannot decide on the AI_READI pilot's registration, unless the cause is a defect under "
    "(ar), as a cause in the gate itself is, which ends this stratum at its filing, before any production "
    "cell;",
    "while the gate cannot decide on the AI_READI pilot's registration, except that where the cause is a "
    "defect under (ar) whose repair requires changed must-equal values, including a defect in the gate's "
    "script or data file, the stratum ends at the filing, and otherwise the registration and the floor remain "
    "held until resolution under (ar);")
sub("until a prospective amendment restates them (NP1.5).\n",
    "until a prospective amendment restates them (NP1.5). *Changed: the ending branch qualified by changed "
    "must-equal values.*\n")
# (al)
sub("probe and receipt-policy registration files, the floor's registration among them) are;",
    "probe and receipt-policy registration files, the floor's registration among them, and the base "
    "system-instructions file and the observation probe's saved transcript, request and observation files, "
    "where a registration writes its own) are;")
sub("the interpreter's identity and each third-party distribution's name, version and `RECORD` hash, with "
    "every hashed installed file verified at preparation and at dispatch;",
    "the interpreter's identity; each third-party distribution's name, version and `RECORD` hash, with every "
    "hashed installed file verified at preparation and at dispatch; every unowned file under the import roots "
    "other than the first-party checkout and the standard library, by path, size and sha256, and the "
    "excluded roots, named; no `.pyc` file, listed or counted;")
sub("among them a candidate built at another commit of the same checkout, which gives",
    "among them a candidate built at another commit of the same checkout with no pinned file changed, which "
    "gives")
sub("if the demonstration shows that they cannot accept it, the gate validates those packets with only the "
    "saved-probe check replaced by a recomputation of the expected binding, and its result says so.",
    "if the demonstration shows that they cannot accept it, those packets are built and validated with the "
    "same substitution, only the saved-probe check replaced by a recomputation of the expected binding, and "
    "the result lists it.")
sub("*Changed: the commit a registration records is identical, every registration is built at the reference's "
    "commit, and the demonstration includes a candidate built at another commit.*",
    "*Changed: the other-commit case qualified; two more kinds of per-run file; rule (ii)'s substitution in "
    "building and validating; what the environment manifest records, with bytecode excluded.*")
# (ar)
sub("both reviewers record whether its repair needs changed must-equal bytes. No registration is made and no "
    "attempt is launched under this amendment until both have recorded and, where they disagree, until the "
    "owner has adjudicated.",
    "both reviewers record whether its repair needs changed must-equal bytes. A stop's classification, and the "
    "filing of its defect where it qualifies, precede the next registration and the next launch under this "
    "amendment. From a stop until its classification is recorded, no attempt is launched under this "
    "amendment. No registration is made and no attempt is launched under this amendment until both have "
    "recorded and, where they disagree, until the owner has adjudicated, by the lead's reading of D36.")
sub("*Changed: the commit under the restoration rule; the test for a later stratum, stated once in NP1.5.*",
    "*Changed: the launch hold starts at the stop; the owner's adjudication marked as the lead's reading of "
    "D36.*")

# ---------------------------------------------------------------- write and check
out = W / REL
out.write_text(text, encoding="utf-8")
data = out.read_bytes()
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", len(data.decode("utf-8").split("\n")) - 1, "bytes", len(data))

assert "@" not in text, "at-sign in the draft"
for stale in ("v13 has not been reviewed", "no real interpreter produces", "is not a case a real interpreter",
              "the state of repairs on unmerged branches", "the four protected files are on the published",
              "both files are applied on the published candidate", "as a cause in the gate itself is",
              "or one with a changed procedure", "compiled `.pyc` files", "The native helpers run with",
              "otherwise the registration and the floor wait |", "between the reviewers (D36)"):
    assert stale not in text, stale
for issue in range(6173, 6184):
    assert f"#{issue}" in text, issue
body = text.split("## NP1.1 What this amendment does", 1)[1]
assert "published candidate" not in body
assert "the reference run's launch word" not in body, "an unanchored (b) left in the body"
letters = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*", text, flags=re.M)
assert len(letters) == 45 and letters[0] == "a" and letters[-1] == "as", len(letters)
notes = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*.*\*(?:Changed|New)[:.]", text, flags=re.M)
print("items with a change note:", notes)
assert sorted(notes) == ["al", "ar", "c", "e", "s"], notes
print("post-checks passed")
