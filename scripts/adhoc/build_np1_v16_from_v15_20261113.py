#!/usr/bin/env python3
"""Build draft v16 of analysis plan amendment NP1 from draft v15.

Purpose: apply the lead's five v16 rulings (coordination record, entry of
2026-11-13T09:10:05Z), which answer the final confirmation reviews of v15
(issues #6188 to #6190): the Codex reviewer's sentence on manifest
regeneration in place of the v15 fallback; launches held from the end of
every attempt, with "stop or rejection" in the filing sentences; the
frozen-code paragraph's result while a change is in place; line 134 citing
the coordination record; and the moved checkout on version 3. Exact
substring edits whose originals are asserted to occur once; quotations of
the coordination record are checked against it.
Inputs: v15 read from git at commit d44fe8283 in the NP1 worktree, asserted by
sha256 15dbe8cc...da8c; STATUS.md in the primary checkout, read only.
Output: the amendment file in the NP1 worktree, overwritten with v16; prints
its sha256, line count and byte count, and runs post-checks.
Serves: NP1 draft v16 (branch claude/native-production-amendment-np1-20261112).
Date: 2026-11-13. Written by a copy of the Claude lead.
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
V15_COMMIT = "d44fe8283a73150541a66f06cc1244caa4bf88ea"
V15_SHA = "15dbe8ccaaf2d0210f898d626bb92478488b961d236f821d5a33684b3115da8c"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V15_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V15_SHA, "v15 bytes differ from the reviewed draft"
text = raw.decode("utf-8")
assert len(text.split("\n")) - 1 == 687


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


# ---------------------------------------------------------------- quotations of the coordination record
REGEN = ("Before the first version 3 registration, review confirms that gate validation regenerates and checks "
         "the manifest against the live environment. If that cannot be confirmed, version 3 registrations remain "
         "held until it is corrected; no alternative gate result is inferred.")
Q16 = [
    f"\"{REGEN}\" This replaces the fallback in ruling 1 of 08:38:05Z, which stays quoted as history with a note "
    "that this sentence supersedes it.",
    "Launches are held from the end of every attempt until its acceptance, or the classification of its stop or "
    "rejection, is recorded. The filing sentences say \"stop or rejection\".",
    "At line 299, \"cannot decide\" while the change is in place, and \"not equal\" after the reference's host is "
    "restored.",
    "Cite this record's entries for the rulings, not the lead's messages to the author.",
    "On version 3, a real moved checkout also changes the manifest's declared excluded roots. So with the "
    "reference's host restored, the candidate's valid manifest pin differs and the result is \"not equal\". Only a "
    "candidate whose sole difference is the path gives \"cannot decide\".",
]
Q_V14_FIXES = "**draft v14 is being written** with the reviewers' own smallest fixes and these lead rulings"
Q_V14_EVERY = "every fix is the reviewer's own smallest fix with the lead's rulings of 08:28:36Z"
Q_FALLBACK = "Otherwise the result is \"not equal\" by the manifest's pin. Either way the registration is held."
status_text = STATUS.read_text(encoding="utf-8")
for quote in Q16 + [Q_V14_FIXES, Q_V14_EVERY, Q_FALLBACK]:
    assert status_text.count(quote) == 1, quote[:70]

HOLD = ("From the end of an attempt until its acceptance, or the classification of its stop or rejection, is "
        "recorded, no attempt is launched under this amendment.")
CLASSIFY = ("The classification of a stop or rejection, and the filing of its defect where it qualifies, precede "
            "the next registration and the next launch under this amendment.")
V3_CHECKOUT = ("On version 3, a real moved checkout also changes the environment manifest's declared excluded roots, "
               "so with the reference's host restored, a registration built in the moved checkout has a valid "
               "manifest pin that differs, and the result is \"not equal\"; only a candidate whose sole difference is "
               "the path gives \"cannot decide\".")

# ---------------------------------------------------------------- header
sub("**Status: draft v15, written by a copy of the Claude lead on 2026-11-13.**",
    "**Status: draft v16, written by a copy of the Claude lead on 2026-11-13.**")
insert_after("- **v14** (commit `bb3eaa8b5ffe2c17b3d16fb21634accf9104648b`", [
    "- **v15** (commit `d44fe8283a73150541a66f06cc1244caa4bf88ea`, file sha256 "
    "`15dbe8ccaaf2d0210f898d626bb92478488b961d236f821d5a33684b3115da8c`) had a final confirmation pass by both "
    "reviewers, and both said \"ratifiable after listed fixes\": a Codex CLI pass (review sha256 "
    "`67d0842fab5143e76d8500239d22fd6b31d004f780f758190f42937fd48cb711`; 1 P2) and a Claude reviewer, a fresh "
    "session (review sha256 `6feeb152e8e93273030d26a6b9876c165a585922cfa6e3d5eefba9d73443fc4b`; 1 P2, 1 P3). No "
    "two of the three findings are on the same point; they are filed as #6188 to #6190."])
sub("  - the \"cannot decide\" result for a rebuilt environment assumes that version 3 validation regenerates the "
    "manifest from the live environment, which the review of the version 3 documents confirms before the first "
    "version 3 registration; otherwise the result is \"not equal\", by the manifest's pin, and either way the "
    "registration is held (NP1.5);",
    "  - the \"cannot decide\" result for a rebuilt environment assumes that version 3 validation regenerates the "
    "manifest from the live environment, which the review of the version 3 documents confirms before the first "
    "version 3 registration; the fallback v15 gave for an unconfirmed review is superseded in v16, where version "
    "3 registrations remain held until it is corrected and no alternative gate result is inferred (NP1.5);")
insert_after("  - NP1.2's cost of the AI_READI pilot and item (s)'s pending-pilot clause carry the Claude review's", [
    "- **v15 → v16 applies the lead's five rulings on the final confirmation reviews** (Authority):",
    "  - the Codex review's sentence replaces v15's fallback: before the first version 3 registration, review "
    "confirms that gate validation regenerates and checks the manifest against the live environment; if that "
    "cannot be confirmed, version 3 registrations remain held until it is corrected, and no alternative gate "
    "result is inferred (NP1.5);",
    "  - a stop or rejection is filed with its classification, and launches are held from the end of every "
    "attempt until its acceptance, or the classification of its stop or rejection, is recorded (NP1.5, "
    "NP1.10(ar));",
    "  - the frozen-code paragraph gives \"cannot decide\" while a changed pinned file, interpreter or environment "
    "is still in place, and \"not equal\" after the reference's host is restored (NP1.5);",
    "  - the rulings for v14 are cited from the coordination record, not from a brief that is not on disk "
    "(Authority);",
    "  - on version 3 a real moved checkout also changes the manifest's declared excluded roots, so with the "
    "reference's host restored it gives \"not equal\"; only a candidate whose sole difference is the path gives "
    "\"cannot decide\" (NP1.5, NP1.10(al))."])
sub("- **v15 has not been reviewed.**", "- **v16 has not been reviewed.**")
sub("the two reviews of v11 (#6130 to #6138) and the two confirmation reviews of v13 (#6173 to #6183), which "
    "concern code",
    "the two reviews of v11 (#6130 to #6138), the two confirmation reviews of v13 (#6173 to #6183) and the two "
    "final confirmation reviews of v15 (#6188 to #6190), which concern code")

# ---------------------------------------------------------------- responses
insert_before("## Responses to the reviews of v13", [
    "## Responses to the reviews of v15",
    "Each issue stays open until a re-check of v16 confirms the answer. \"Claude\" and \"Codex\" name the two final "
    "confirmation reviews of v15. No two of their findings are on the same point, so each has its own issue.",
    "",
    "| v15 finding | Issue | Answer in v16 | Where |",
    "|---|---|---|---|",
    "| Codex P2-1: without live regeneration, an environment change does not necessarily produce a different "
    "recorded manifest pin | #6190 | The review's sentence replaces the fallback: before the first version 3 "
    "registration, review confirms that gate validation regenerates and checks the manifest against the live "
    "environment; if that cannot be confirmed, version 3 registrations remain held until it is corrected, and no "
    "alternative gate result is inferred. The lead's v15 ruling stays quoted as history, with a note that this "
    "sentence supersedes its fallback | Header, Authority, NP1.5 |",
    "| Claude P2-1: the launch hold and the filing rule cover a stop, not a rejection | #6188 | The review's "
    "wording: the defect of a stop or rejection is filed with its classification; the classification of a stop or "
    "rejection, and the filing of its defect where it qualifies, precede the next registration and the next "
    "launch; from the end of an attempt until its acceptance, or the classification of its stop or rejection, is "
    "recorded, no attempt is launched | NP1.5, (ar) |",
    "| Claude P3-1: the frozen-code paragraph still gives \"not equal\" for a change that is still in place | #6189 "
    "| The review's clause: \"cannot decide\" also while a changed pinned file, interpreter or environment is still "
    "in place at the reference's paths, a hold until the reference's paths, commit and host state are restored; "
    "and \"not equal\" for a registration built under such a change once the reference's host is restored | NP1.5 "
    "|",
    "| Claude, a note: the rulings for v14 cite a brief of the lead's that is not on disk | none | They now cite the "
    "coordination record's entries of 08:28:36Z and 08:38:05Z. No other citation of an unrecorded message or brief "
    "remains | Authority |",
    "",
])
sub("Each issue stays open until a re-check of v15 confirms the answer; v14 was not reviewed.",
    "The final confirmation reviews of v15 found these answers resolved, except that to #6173, which both found "
    "partly resolved, and that to #6174, which the Claude review found partly resolved; v16 completes both "
    "(above). Each issue stays open until a re-check of v16 confirms the answer.")
sub("| v13 finding | Issue | Answer in v15 | Where |", "| v13 finding | Issue | Answer in v16 | Where |")
sub("A rebuilt environment is treated the same way, on the lead's ruling that version 3 validation regenerates the "
    "manifest from the live environment, which the review of the version 3 documents confirms; otherwise the "
    "result is \"not equal\", by the manifest's pin, and either way the registration is held. The other statements "
    "of a changed version's result now say \"when it is compared with the reference's interpreter in place\"",
    "A rebuilt environment is treated the same way, on the lead's ruling that version 3 validation regenerates the "
    "manifest from the live environment: before the first version 3 registration, review confirms it, and if that "
    "cannot be confirmed, version 3 registrations remain held until it is corrected, with no alternative gate "
    "result inferred. The other statements of a changed version's result now say \"when it is compared with the "
    "reference's interpreter in place\", and the frozen-code paragraph gives \"cannot decide\" while such a change "
    "is in place")
sub("| #6174 | A stop's classification, and the filing of its defect where it qualifies, precede the next "
    "registration and the next launch; from a stop until its classification is recorded, no attempt is launched |",
    "| #6174 | The classification of a stop or rejection, and the filing of its defect where it qualifies, precede "
    "the next registration and the next launch; from the end of an attempt until its acceptance, or the "
    "classification of its stop or rejection, is recorded, no attempt is launched |")
sub("v14 completes those three (above), and v15 carries them. Each issue stays open until a re-check of v15 "
    "confirms the answer.",
    "v14 completes those three (above), and v15 and v16 carry them. Each issue stays open until a re-check of v16 "
    "confirms the answer.")
sub("| v11 finding | Issue | Answer in v15 | Where |", "| v11 finding | Issue | Answer in v16 | Where |")
sub("A moved checkout or interpreter path is not a sha256 pin, so it gives \"cannot decide\", a hold until the move "
    "is undone; restoring the paths allows another comparison.",
    "A moved checkout or interpreter path is not a sha256 pin, so where the path is the only difference it gives "
    "\"cannot decide\", a hold until the move is undone; restoring the paths allows another comparison. On version "
    "3 a real moved checkout also changes the manifest's declared excluded roots, so with the reference's host "
    "restored it gives \"not equal\" by the manifest's pin.")
sub("| #6137 | No attempt is launched from a stop until its classification is recorded, nor while a defect's "
    "classification is open,",
    "| #6137 | No attempt is launched from the end of an attempt until its acceptance, or the classification of its "
    "stop or rejection, is recorded, nor while a defect's classification is open,")

# ---------------------------------------------------------------- authority
sub("(entries of 2026-11-13T07:14:52Z, 07:32:30Z and 08:28:36Z). On the environment manifest's census:",
    "(entries of 2026-11-13T07:14:52Z, 07:32:30Z, 08:28:36Z and 08:38:05Z). On the environment manifest's census:")
sub("The lead's brief to the author of this draft adds the rulings where a review left a choice: the reviewers' own "
    "smallest fixes are applied; an interpreter upgrade or a rebuilt environment at the reference's paths is a "
    "hold, and one that cannot be undone is a pre-reservation defect; the launch hold starts at the stop; every "
    "file written during the stratum stays uncommitted in the production checkout or is committed from another "
    "worktree; and both kinds of file the Claude review names join the per-run paths.",
    f"The entry of 08:28:36Z also records that \"{Q_V14_FIXES}\", and the entry of 08:38:05Z that \"{Q_V14_EVERY}\". "
    "Those fixes include: an interpreter upgrade or a rebuilt environment at the reference's paths is a hold, and "
    "one that cannot be undone is a pre-reservation defect; the launch hold starts at the stop; every file written "
    "during the stratum stays uncommitted in the production checkout or is committed from another worktree; and "
    "both kinds of file the Claude review names join the per-run paths, the first of the two options that review "
    "offered.")
insert_after("  - **The rulings for v15** (entry of 2026-11-13T08:38:05Z)", [
    f"    - **Superseded in part.** The fallback in ruling (1), \"{Q_FALLBACK}\", is superseded by the Codex "
    "review's sentence that ruling (1) of v16 adopts (below). The ruling stays quoted above as history.",
    "  - **The rulings for v16** (entry of 2026-11-13T09:10:05Z), the lead's five rulings on the final "
    f"confirmation reviews of v15. (1) On the Codex review's P2-1, the reviewer's own text: {Q16[0]} (2) On the "
    f"Claude review's P2-1: \"{Q16[1]}\" (3) On its P3-1: \"{Q16[2]}\" (4) On line 134: \"{Q16[3]}\" (5) From the "
    f"lead's ruling on helper 3's H3-RF19: \"{Q16[4]}\" NP1.5 and NP1.10(al) and (ar) put them to the owner; (4) "
    "applies to this section."])

# ---------------------------------------------------------------- NP1.5: frozen code (ruling 3)
sub("the gate finds it \"not equal\", or \"cannot decide\" where the only difference is a moved checkout or "
    "interpreter path or another commit, a hold until the reference's paths and commit are restored.",
    "the gate finds it \"not equal\", or \"cannot decide\" where the only difference is a moved checkout or "
    "interpreter path or another commit, or while a changed pinned file, interpreter or environment is still in "
    "place at the reference's paths, a hold until the reference's paths, commit and host state are restored; a "
    "registration built under such a change and compared after the reference's host is restored gives \"not "
    "equal\".")

# ---------------------------------------------------------------- NP1.5: filing and launch hold (ruling 2)
sub("A stop's defect is filed with the stop's classification, and a pre-reservation defect when the registration "
    "it prevents is held; either is filed before the next registration under this amendment. A stop's "
    "classification, and the filing of its defect where it qualifies, precede the next registration and the next "
    "launch under this amendment. From a stop until its classification is recorded, no attempt is launched under "
    "this amendment.",
    "The defect of a stop or rejection is filed with its classification, and a pre-reservation defect when the "
    f"registration it prevents is held; either is filed before the next registration under this amendment. {CLASSIFY} "
    f"{HOLD}")

# ---------------------------------------------------------------- NP1.5: the environment (ruling 1)
sub("That \"cannot decide\" assumes that version 3 validation regenerates the manifest from the live environment "
    "(the lead's ruling, Authority); the review of the version 3 documents confirms it before the first version 3 "
    "registration. If validation does not regenerate it, the result is \"not equal\", by the manifest's pin. Either "
    "way the registration is held.",
    "That \"cannot decide\" assumes that version 3 validation regenerates the manifest from the live environment "
    f"(the lead's ruling, Authority). {REGEN}")

# ---------------------------------------------------------------- NP1.5: the moved checkout (ruling 5)
sub("A path is not a sha256 pin, so a registration built after the checkout or the interpreter has moved cannot be "
    "validated at the reference's path, and the gate's result is \"cannot decide\" (NP1.5's precedence, below). It "
    "is a hold until the move is undone, and restoring the paths allows another comparison.",
    "A path is not a sha256 pin, so a registration built after the checkout or the interpreter has moved cannot be "
    "validated at the reference's path, and where the path is its sole difference the gate's result is \"cannot "
    "decide\" (NP1.5's precedence, below). It is a hold until the move is undone, and restoring the paths allows "
    f"another comparison. {V3_CHECKOUT}")
sub("and, on a format that carries the environment manifest, a changed version of a third-party distribution and a "
    "changed installed file of one, by the manifest's pin;",
    "and, on a format that carries the environment manifest, a changed version of a third-party distribution, a "
    "changed installed file of one, and a candidate built in a really moved checkout and compared with the "
    "reference's host restored, whose manifest's declared excluded roots the move changes, by the manifest's pin;")
sub("a moved checkout or interpreter path, on either format, a hold until the move is undone;",
    "a moved checkout or interpreter path, on either format, where the path is the candidate's sole difference, a "
    "hold until the move is undone;")

# ---------------------------------------------------------------- NP1.10
sub("A note after an item says how it differs from v14; an item with no note is unchanged from v14. The letters "
    "are v14's: (aj) stays retired; (s) is changed.",
    "A note after an item says how it differs from v15; an item with no note is unchanged from v15. The letters "
    "are v15's: (aj) stays retired; (al) and (ar) are changed.")
sub(" *Changed: an AI_READI pilot repair after the reference run ends the stratum, in the pending-pilot clause.*", "")
# (al)
sub("a moved checkout or interpreter path, or another commit, is no such pin and gives \"cannot decide\", a hold "
    "until the reference's paths and commit are restored;",
    "a moved checkout or interpreter path, or another commit, is no such pin and, where it is the sole difference, "
    "gives \"cannot decide\", a hold until the reference's paths and commit are restored; on version 3 a real moved "
    "checkout also changes the manifest's declared excluded roots, so with the reference's host restored it gives "
    "\"not equal\" by the manifest's pin;")
sub("and, built again at the reference's commit, \"equal\", before the canary's registration",
    "and, built again at the reference's commit, \"equal\", and, on version 3, a candidate built in a really moved "
    "checkout, which with the reference's host restored gives \"not equal\" by the manifest's pin, while a "
    "candidate whose sole difference is the path gives \"cannot decide\", before the canary's registration")
sub("restoring that state is not a repair (NP1.5, NP1.6, NP1.7).",
    "restoring that state is not a repair (NP1.5, NP1.6, NP1.7). *Changed: on version 3, a real moved checkout "
    "gives \"not equal\" by the manifest's pin once the reference's host is restored, in the gate's rule and in the "
    "demonstration; only a path as the sole difference gives \"cannot decide\".*")
# (ar)
sub("both reviewers record whether its repair needs changed must-equal bytes. A stop's classification, and the "
    "filing of its defect where it qualifies, precede the next registration and the next launch under this "
    "amendment. From a stop until its classification is recorded, no attempt is launched under this amendment.",
    "both reviewers record whether its repair needs changed must-equal bytes. The defect of a stop or rejection is "
    f"filed with its classification. {CLASSIFY} {HOLD}")
sub("decided by the one test NP1.5 states under this item. A change for any other reason is not made during "
    "production (NP1.5).",
    "decided by the one test NP1.5 states under this item. A change for any other reason is not made during "
    "production (NP1.5). *Changed: a stop or rejection is filed with its classification, and launches are held "
    "from the end of every attempt until its acceptance, or that classification, is recorded.*")

# ---------------------------------------------------------------- write and check
out = W / REL
out.write_text(text, encoding="utf-8")
data = out.read_bytes()
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", len(data.decode("utf-8").split("\n")) - 1, "bytes", len(data))

assert "@" not in text
for stale in ("v15 has not been reviewed", "lead's brief", "From a stop until its classification",
              "If validation does not regenerate it", "A stop's classification", "A stop's defect is filed"):
    assert stale not in text, stale
assert text.count("Either way the registration is held.") == 2   # the v15 ruling, and the note quoting its fallback
assert text.count(HOLD) == 2 and text.count(CLASSIFY) == 2        # the body and (ar)
assert text.count(REGEN) == 2                                    # NP1.5 and the v16 ruling's quotation
for issue in (6188, 6189, 6190):
    assert f"#{issue}" in text, issue
letters = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*", text, flags=re.M)
assert len(letters) == 45 and letters[0] == "a" and letters[-1] == "as", len(letters)
notes = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*.*\*(?:Changed|New)[:.]", text, flags=re.M)
print("items with a change note:", notes)
assert notes == ["al", "ar"], notes
print("post-checks passed")
