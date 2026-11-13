#!/usr/bin/env python3
"""Build draft v12 of analysis plan amendment NP1 from draft v11.

Purpose: apply the v12 rulings (coordination record, entry of
2026-11-13T06:48:36Z, and the lead's three corrections to the brief) and the
answers to the v11 reviews (issues #6130 to #6138) to the v11 text, by exact
substring edits whose originals are asserted to occur once, so that the
change from v11 to v12 is reproducible.
Inputs: v11 read from git at commit 890ee25c5 in the NP1 worktree, asserted
by sha256 c7342203...276f.
Output: the amendment file in the NP1 worktree, overwritten with v12; prints
its sha256, line count and byte count, and runs post-checks.
Serves: NP1 draft v12 (branch claude/native-production-amendment-np1-20261112).
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
V11_COMMIT = "890ee25c567e328f9d9c6feac3ffb9053511a781"
V11_SHA = "c734220397d15307c42154ab8b8fc8e76344fef1549950b190443bdffba0276f"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V11_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V11_SHA, "v11 bytes differ from the reviewed draft"
text = raw.decode("utf-8")
assert text.endswith("\n") and len(text.split("\n")) - 1 == 645, len(text.split("\n"))


def sub(old, new):
    """Replace one exact occurrence."""
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
    """Replace the one whole line that starts with prefix."""
    global text
    lines, i = line_starting(prefix)
    lines[i:i + 1] = new_lines
    text = "\n".join(lines)


def replace_lines(start_prefix, end_prefix, new_lines):
    """Replace the block from the line starting start_prefix through end_prefix."""
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
sub("**Status: draft v11, written by a copy of the Claude lead on 2026-11-13.**",
    "**Status: draft v12, written by a copy of the Claude lead on 2026-11-13.**")
sub("v1 to v9, with their commits, hashes, reviews and issues (#5914 to #5925, #5940 to #5964, "
    "#5969 to #5988, #5996 to #6014, #6017 to #6029, #6032 to #6045, #6050 to #6064, #6075 to #6092, "
    "#6095 to #6109), are listed in the headers of v4 to v10.",
    "v1 to v10, with their commits, hashes, reviews and issues (#5914 to #5925, #5940 to #5964, "
    "#5969 to #5988, #5996 to #6014, #6017 to #6029, #6032 to #6045, #6050 to #6064, #6075 to #6092, "
    "#6095 to #6109, #6112 to #6129), are listed in the headers of v4 to v11.")
replace_line("- **v10** (commit `2f5c66797e8d304d1fcda6d0007ac501f3a27d92`", [
    "- **v11** (commit `890ee25c567e328f9d9c6feac3ffb9053511a781`, file sha256 "
    "`c734220397d15307c42154ab8b8fc8e76344fef1549950b190443bdffba0276f`) was reviewed twice, and both "
    "reviews said \"ratifiable after listed fixes\": a Codex CLI pass (review sha256 "
    "`aea97c9dcea0ffb4d34516a8cef64ceebb160a020486fddfc16eb21c4c5432a9`; 3 P1, 1 P2) and a Claude "
    "reviewer, a fresh session run on another model (review sha256 "
    "`ea6c9aa6d53ef8cb673a6f6db8b11edb3982b99d7e28346cb9e9aa377231e3d4`; 2 P1, 3 P2, 4 P3). Partway "
    "through its review the Claude reviewer saw the lead's summary of the Codex review in the "
    "coordination record, and its report says so; where its findings overlap the Codex review, those "
    "parts are confirmations, not independent findings. The 13 findings are filed as 9 issues, #6130 "
    "to #6138; the four Codex findings are appended to the Claude issue on the same point."])
replace_lines("- **v10 → v11 tests the gate on what production will give it", "  - takes in D146 and corrects", [
    "- **v11 → v12 states the gate's results by its own precedence, and holds the stratum while a "
    "defect is classified.** The Codex review of v11 found, and the Claude review confirmed, listed "
    "results of the gate that its precedence cannot give: a wrong floor basis and a moved checkout "
    "give \"cannot decide\", not \"not equal\", and the environment-manifest cases cannot be shown on "
    "version 2. Both found that the run on the reference pilot's own packet needs another in-scope "
    "project, which CHORUS alone in scope does not have. The Claude review also found that "
    "registrations were not held while a defect's classification was open, that the offline packets "
    "of that run carry no real permission probe, that the floor's registration has to sit at its own "
    "path, and that the exploratory test reached strata it was not written for. v12:",
    "  - holds every registration and every launch under this amendment from the filing of a "
    "qualifying defect until its classification is settled, by the owner where the reviewers "
    "disagree, and for an unknown stop until the owner reclassifies it; a registration made before a "
    "boundary and not yet launched is withdrawn (NP1.5, NP1.10(ar));",
    "  - gives each listed case the result the precedence gives: a wrong or missing floor basis and a "
    "moved checkout or interpreter path are \"cannot decide\"; the environment manifest's pin and the "
    "dependency registry's sha256 pins, the interpreter's among them, take the shortcut (NP1.5);",
    "  - makes the environment-manifest cases conditional on NP1.10(as), which the owner has not "
    "answered: if it is answered no, they are not applicable before the canary and are required in "
    "full before the first version 3 registration; if it is answered yes, they are required before "
    "the canary's registration (NP1.5, NP1.7, NP1.10(al), (aq));",
    "  - classes as per-run the paths of the files each registration writes for itself, the floor's "
    "registration among them, and keeps the reference's pending receipt-policy registration at its "
    "path (NP1.5);",
    "  - fixes the run on the reference pilot's own packet: the inventory on the real packet and the "
    "packet against itself; a packet for each other in-scope project, or \"not applicable\" where "
    "there is none; the packet with the floor's registration substituted; and two rules for the "
    "offline packets' permission probes, one of which applies by a property of the unchanged "
    "validators (NP1.5);",
    "  - scopes the exploratory test to strata that follow this one after the reference run; binds "
    "the reference pilot's own gate runs to its coded word by hash; and says that the floor's list "
    "ends the stratum where NP1.10(ar) applies (NP1.5, NP1.7, NP1.10(aa), (ar), (s))."])
sub("- **v11 has not been reviewed.**", "- **v12 has not been reviewed.**")
sub("the two reviews of v9 (#6095 to #6109) and the two reviews of v10 (#6112 to #6129), which concern code",
    "the two reviews of v9 (#6095 to #6109), the two reviews of v10 (#6112 to #6129) and the two "
    "reviews of v11 (#6130 to #6138), which concern code")
sub("the `profile:` keys of the study's source manifest and of the Kids First manifest.\n",
    "the `profile:` keys of the study's source manifest and of the Kids First manifest. For v12 the "
    "author of this draft read, at the cited commit: the interpreter and working-directory fields of "
    "the composition and of the dependency registry, and their checks "
    "(`native_shared_registration.py:113–120`, `:245–246`; `native_shared_controller.py:93–105`, "
    "`:122–130`; `native_supervisor_authority_v2.py:45–49`; `native_execution_authority_v2.py:30`, "
    "`:1136–1149`; `native_execution_registration_v2.py:273–277`); the launch re-verification's "
    "checks (`native_shared_registration_orchestration.py:163–170`, `:232–239`); the permission "
    "expectation and the check of a saved probe against it (`native_shared_registration.py:161–182`, "
    "`:256–264`; `native_shared_permissions.py:1015–1019`); and the reserved and protected paths "
    "(`native_shared_registration.py:185–211`). At the candidate it read the selection's pins and "
    "their paths (`native_shared_contract.py:754–773`; `native_shared_selection.py:207–212`, "
    "`:371–383`, `:399`) and the receipt-policy parser's floor check "
    "(`native_shared_contract.py:797–812`).\n")

# ---------------------------------------------------------------- responses
TABLE = [
    "## Responses to the reviews of v11",
    "Each issue stays open until a re-check of v12 confirms the answer. \"Claude\" and \"Codex\" name "
    "the two v11 reviews; both used the keys P1-1, P2-1 and so on, so each key is given with its "
    "review. The responses to the reviews of v10 are in v11's own commit.",
    "",
    "| v11 finding | Issue | Answer in v12 | Where |",
    "|---|---|---|---|",
    "| Claude P1-1: while the reviewers disagree, or while an unknown stop waits to be reclassified, "
    "registrations are not held, so whether a run already seen belongs to the stratum can be decided "
    "after its outcome | #6130 | From the filing of a qualifying defect, no registration is made and "
    "no attempt is launched under this amendment until both reviewers have recorded whether its "
    "repair needs changed must-equal bytes and, where they disagree, until the owner has "
    "adjudicated. An unknown stop holds every registration and every launch until the owner "
    "reclassifies it; if it then qualifies, its defect is filed at the reclassification. The "
    "boundary, if there is one, is the moment of filing, and nothing is registered or launched "
    "between the filing and the decision | NP1.5, (ar) |",
    "| Claude P1-2, with Codex P1-1, P1-3 and P2-1: listed gate results contradict the gate's "
    "precedence: a wrong floor basis, a changed interpreter version, a moved checkout, and the "
    "environment cases on version 2 | #6131 | A wrong or missing floor basis is refused by the "
    "receipt-policy parser (`native_shared_contract.py:803–806`, at the candidate), so it gives "
    "\"cannot decide\"; a structurally valid other floor value stays \"not equal\". A moved checkout "
    "or interpreter path is not a sha256 pin, so it gives \"cannot decide\", a hold until the move is "
    "undone; restoring the paths allows another comparison. The environment manifest's pin is a "
    "must-equal implementation pin and takes the shortcut, by the lead's ruling, and so are the "
    "dependency registry's sha256 pins, the interpreter's among them, which the author found in the "
    "version 2 documents (Authority): a changed interpreter whose bytes differ gives \"not equal\" on "
    "either format, and a changed interpreter version alone gives \"not equal\" on version 3 and "
    "\"cannot decide\" on version 2. The environment-manifest cases follow NP1.10(as), which the "
    "owner has not answered: if it is answered no, they are not applicable before the canary and are "
    "required in full before the first version 3 registration; if it is answered yes, they are "
    "required before the canary's registration | NP1.5, NP1.7, (al), (aq) |",
    "| Claude P2-1, with Codex P1-2: the run on the reference pilot's own packet has two unmet "
    "preconditions: its offline packets carry no real permission probe, and with CHORUS alone in "
    "scope there is no other project | #6132 | The run is fixed now: the reference pilot's packet "
    "against itself, with the inventory on that real packet; a packet with each other in-scope "
    "project's real input tuple pinned at NP1b, recorded as \"not applicable\" where there is none; "
    "and the reference pilot's packet with the floor's registration substituted. Two rules are fixed "
    "for the offline packets' permission probes, and neither changes a validator: (i) a probe rebuilt "
    "offline for the packet's own selection, marked synthetic in the comparison-input manifest, which "
    "the unchanged validators accept; (ii) if the demonstration shows that they cannot accept one, "
    "validation with only the saved-probe check replaced by a recomputation of the expected binding, "
    "listed in the result. A refused packet is corrected in its construction, never by changing the "
    "gate's rule or data file to make a case pass | NP1.5, (al) |",
    "| Claude P2-2: the floor's registration must sit at a new path, which v11's path rule classes as "
    "identical | #6133 | The paths of the files each registration writes for itself are per-run: the "
    "registration and its selection, composition, runtime declaration, environment manifest, "
    "instruction, probe and receipt-policy registration files. Their contents are judged by the other "
    "rules. The floor's registration sits at its own path, and the reference's pending registration "
    "stays at its path, so that the reference's packet validates again at every later registration. "
    "The review named the receipt-policy registration, the composition and the runtime declaration; "
    "the selection and the environment manifest are added because each registration writes its own "
    "| NP1.5, (al) |",
    "| Claude P2-3: read literally, the one test makes every continuation after a failed canary or "
    "reference pilot exploratory | #6134 | The test applies only to a stratum that follows this one "
    "after the reference run. Before the reference exists, a repair after a failed canary or "
    "reference-pilot attempt follows the pre-reference rules and makes nothing exploratory, and a "
    "stratum begun then by a prospective amendment is classed by that amendment, under the bar | "
    "NP1.5, (ar) |",
    "| Claude P3-1: \"the bytes it holds must not change\" | #6135 | Now \"the files the registration "
    "pins must not change\": each attempt writes its records into the checkout | NP1.5 |",
    "| Claude P3-2: the reference pilot's own gate runs are not bound by hash | #6136 | Each review of "
    "a registration of the CHORUS reference pilot names the sha256s of each run's comparison-input "
    "manifest and result, so its coded word binds them, as for later registrations | NP1.5, NP1.7, "
    "(aa) |",
    "| Claude P3-3: a registration made before a boundary can still be launched after it | #6137 | No "
    "attempt is launched while a classification is open, and if the stratum ends, a registration made "
    "before the boundary and not yet launched is withdrawn, not launched after it | NP1.5, (ar) |",
    "| Claude P3-4: the floor list says the floor waits where (ar) ends the stratum | #6138 | Where "
    "the gate cannot decide on the AI_READI pilot's registration because of a defect under (ar), as a "
    "cause in the gate itself is, the stratum ends at the filing, before the floor and before any "
    "production cell; otherwise the registration and the floor wait | NP1.5, (s) |",
]
replace_lines("## Responses to the reviews of v10", "| Codex P2-4: equal `RECORD` bytes", TABLE)

# ---------------------------------------------------------------- authority
insert_after("  - **The rulings for v11** (entry of 2026-11-13T05:33:41Z)", [
    "  - **The rulings for v12** (entry of 2026-11-13T06:48:36Z): \"hold every registration and "
    "launch until a defect's classification is settled (by the owner where the reviewers disagree); "
    "gate results that follow the precedence (a wrong basis and a moved checkout give \"cannot "
    "decide\"; a valid different floor gives \"not equal\"; the environment manifest's pin is "
    "shortcut-eligible, so a changed interpreter version gives \"not equal\" on version 3 and "
    "\"cannot decide\" on version 2); the environment cases conditional on the owner's answer to "
    "item (as), which is still open; per-registration paths for the floor's registration; packets "
    "(2) and (3) carry an offline probe marked synthetic, with a fixed fallback to a recomputed "
    "binding if the unchanged validators refuse it; the exploratory test scoped to changes after the "
    "reference run.\" NP1.5 and NP1.10(aa), (al), (aq), (ar) and (s) put them to the owner.",
    "    - **Where this draft departs from that entry** (the author's reading of the source, not the "
    "lead's ruling): the version 2 documents carry the sha256 of the interpreter's bytes in the "
    "dependency registry (`python_sha256`: `native_supervisor_authority_v2.py:45–49`, which "
    "`native_execution_authority_v2.py:1136–1149` and `native_execution_registration_v2.py:273–277` "
    "put into the preparation; read by the author at the cited commit). That is a must-equal "
    "implementation pin, so a changed interpreter whose bytes differ gives \"not equal\" on version 2 "
    "as well. \"Cannot decide\" is version 2's result only where the recorded version changes and the "
    "interpreter's bytes do not (NP1.5)."])

# ---------------------------------------------------------------- NP1.5: the reference run and (ar)
sub("the closed dependency registry of the package's own source files,",
    "the closed dependency registry of the package's own source files and of the interpreter,")
sub("other than the floor's permitted change (below), is not equal and is not made under this amendment. "
    "That covers",
    "other than the floor's permitted change (below), is not made under this amendment: the gate finds "
    "it \"not equal\", or \"cannot decide\" where the difference is a moved checkout or interpreter "
    "path, which holds it until the move is undone. That covers")
sub("An unknown stop (row 9) qualifies only once the owner's adjudication reclassifies it into one of "
    "these. On this arm",
    "An unknown stop (row 9) qualifies only once the owner's adjudication reclassifies it into one of "
    "these, and until then it holds every registration and every launch (below). On this arm")
sub("No registration is made until both have recorded. Where they disagree, the owner adjudicates, as "
    "for any disagreement between the reviewers (D36); the boundary, if there is one, is still the "
    "moment of filing.",
    "**No registration is made and no attempt is launched under this amendment until both reviewers "
    "have recorded and, where they disagree, until the owner has adjudicated,** as for any "
    "disagreement between the reviewers (D36). **An unknown stop holds every registration and every "
    "launch under this amendment until the owner reclassifies it; if it then qualifies, its defect is "
    "filed at the reclassification.** The boundary, if there is one, is the moment of filing.")
sub("      - **If the repair needs changed must-equal bytes,** no further registration is made in this "
    "stratum from the moment of filing. The stratum ends there, for every registration made after the "
    "boundary, whether or not that registration would carry the repair.",
    "      - **If the repair needs changed must-equal bytes,** no further registration is made and no "
    "attempt of this stratum is launched from the moment of filing. The stratum ends there, for every "
    "registration made after the boundary, whether or not that registration would carry the repair. A "
    "registration made before the boundary and not yet launched is withdrawn, not launched after it.")
sub("    - **One test for an exploratory stratum,** the same here and in NP1.10(ar): a later stratum is "
    "exploratory unless it begins at a boundary this item fixes and every change it carries has the "
    "recorded reason the bar requires.",
    "    - **One test for an exploratory stratum,** the same here and in NP1.10(ar). It applies only to "
    "a stratum that follows this one after the reference run: such a stratum is exploratory unless it "
    "begins at a boundary this item fixes and every change it carries has the recorded reason the bar "
    "requires. Before the reference exists, a repair after a failed canary or reference-pilot attempt "
    "follows the pre-reference rules (NP1.6, NP1.7) and makes nothing exploratory, and a stratum begun "
    "then by a prospective amendment, after a pilot that concluded without acceptance, is classed by "
    "that amendment, under the bar.")
sub("and the end is fixed at the moment the defect is filed, so no one chooses when the stratum ends.",
    "and the end is fixed at the moment the defect is filed, so no one chooses when the stratum ends. "
    "Nothing is registered or launched while the classification is open, so no outcome can arrive "
    "between the filing and the decision on whether the stratum ends.")
sub("the reviewers' record of whether a repair needs changed must-equal bytes; and the owner's words,",
    "the reviewers' record of whether a repair needs changed must-equal bytes, and the owner's "
    "adjudication where they disagree or of an unknown stop; and the owner's words,")
replace_line("    - **the interpreter and the third-party distributions.**", [
    "    - **the interpreter and the third-party distributions.** The composition records the "
    "interpreter's path and its full version string (`native_shared_registration.py:116–119`; "
    "`native_shared_controller.py:100–106`), and the execution body's dependency registry records "
    "them again with the sha256 of the interpreter's bytes (`native_supervisor_authority_v2.py:45–49`). "
    "All are identical fields. An interpreter upgrade makes later registrations not equal: the "
    "registry's sha256 pin differs wherever the bytes do, and on version 3 the environment manifest's "
    "pin records the interpreter's identity (below). An interpreter at another path makes them "
    "\"cannot decide\", a hold until the move is undone (the checkout, below). The registry also pins "
    "the package's own source files by digest (`native_shared_registration.py:141–144`, `:253–254`, "
    "`:266–279`), but not the third-party distributions, although the helpers execute LinkML, the "
    "term validator and their dependencies. Those are bound by the environment manifest (below), "
    "which the gate holds identical and which is checked again at dispatch. So a rebuilt environment "
    "whose distributions or installed files differ makes later registrations not equal, and a change "
    "after a registration is prepared holds its launch;"])
replace_line("    - **the checkout.** Its absolute path is recorded", [
    "    - **the checkout.** Its absolute path is recorded as the working directory and in every "
    "absolute pin, and the validators the gate runs reconstruct it from the process that runs them "
    "(`native_shared_registration.py:113–120`, `:245–246`). Launch re-verification refuses unless the "
    "working directory is the code's own root and equals the packet's recorded one, and unless the "
    "interpreter's path and version equal the running ones "
    "(`native_shared_registration_orchestration.py:168–170`, `:236–238`). So the checkout path is an "
    "identical field: every registration of the stratum is built in the reference's checkout, at its "
    "path, and the files the registration pins must not change. A path is not a sha256 pin, so a "
    "registration built after the checkout or the interpreter has moved cannot be validated at the "
    "reference's path, and the gate's result is \"cannot decide\" (NP1.5's precedence, below). It is "
    "a hold until the move is undone, and restoring the paths allows another comparison. A move that "
    "cannot be undone is a pre-reservation defect under NP1.10(ar);"])

# ---------------------------------------------------------------- NP1.5: the gate
sub("Among paths, only these are per-run: the per-attempt roots (attempt, evidence, output and stage) "
    "and the paths under them, and the per-attempt files (the registration, instruction and probe "
    "files). Every other path is identical, and the data file names each path field and its class.",
    "Among paths, only these are per-run: the per-attempt roots (attempt, evidence, output and stage) "
    "and the paths under them, and the paths of the per-registration files, which each registration "
    "writes for itself and so cannot place at the reference's paths: the registration and its "
    "selection, composition, runtime declaration, environment manifest, instruction, probe and "
    "receipt-policy registration files. Their contents are judged by the rules here, never by their "
    "paths. Every other path is identical, and the data file names each path field and its class.")
sub("Its `registration_id` is a per-run field, as every identifier is, and it may be new. Every other "
    "field is the reference's.",
    "Its `registration_id` is a per-run field, as every identifier is, and it may be new. Every other "
    "field is the reference's. It is written at its own path: a selection pins its receipt-policy "
    "registration as a file, path and bytes together (`native_shared_contract.py:754`; "
    "`native_shared_selection.py:207–208`, `:377–383`; at the candidate), and the reference's pending "
    "registration stays at its own path, so that the reference's packet validates again at every "
    "later registration. That path is per-run (above).")
sub("The hashes that carry it are derived values and are recomputed. What that one value does inside a run,",
    "The receipt-policy registration's path may differ from the reference's; the file it names is "
    "checked as the floor's registration. The hashes that carry it are derived values and are "
    "recomputed. **A structurally valid floor value other than the ratified one is \"not equal\".** A "
    "basis other than `receipted_part`, or none, is refused by the receipt-policy parser "
    "(`native_shared_contract.py:803–806`, at the candidate), which the validators run when they "
    "rebuild the selection (`native_shared_selection.py:399`, at the candidate); that packet fails "
    "validation, and the result is \"cannot decide\" (below). What that one value does inside a run,")
sub("A project-tuple substitution, a derived value and the floor's transition never take the shortcut: "
    "they are judged only after both packets pass the validators.",
    "A project-tuple substitution, a derived value and the floor's transition never take the shortcut: "
    "they are judged only after both packets pass the validators. The environment manifest's pin is a "
    "must-equal implementation pin, and so are the dependency registry's sha256 pins, the "
    "interpreter's among them: each takes the shortcut. A path is not a sha256 pin and never takes it.")
sub("a floor value or basis other than the floor's ratified registration,",
    "a floor value other than the floor's ratified registration's,")
sub("a packet fails the production validators, a pinned file is missing, a leaf is not classified, or a "
    "derived value cannot be recomputed.",
    "a packet fails the production validators (among them a packet with a wrong or missing floor "
    "basis, and one built after the checkout or the interpreter moved), a pinned file is missing, a "
    "leaf is not classified, or a derived value cannot be recomputed.")
sub("The inventory is part of the demonstration: it shows every leaf classified. The saved output shows "
    "each case's result and the fields it names:",
    "The inventory is part of the demonstration: it shows every leaf classified. The demonstration "
    "also shows whether the unchanged validators accept a permission probe rebuilt offline for a "
    "packet's own selection and marked synthetic, which decides the rule for the run on the reference "
    "pilot's own packet (below). The saved output shows each case's result and the fields it names:")
sub("    - **not equal:** a changed prompt asset; a changed binary hash; a changed bound; a changed "
    "interpreter version; a changed version of a third-party distribution; a changed installed file of "
    "one; a wrong floor value; a wrong floor basis; an internally valid registration with another "
    "project's tuple; and two prohibited differences together, both listed;",
    "    - **not equal:** a changed prompt asset; a changed binary hash; a changed bound; a changed "
    "interpreter whose bytes differ, by the dependency registry's sha256 pin of them, on either "
    "format; a wrong floor value that is structurally valid; an internally valid registration with "
    "another project's tuple; two prohibited differences together, both listed; and, on a format that "
    "carries the environment manifest, a changed interpreter version, a changed version of a "
    "third-party distribution and a changed installed file of one, by the manifest's pin;")
sub("    - **cannot decide:** a missing artifact; an unknown field; an incorrect derived binding; and "
    "invalid evidence;",
    "    - **cannot decide:** a missing artifact; an unknown field; an incorrect derived binding; invalid "
    "evidence; a wrong or missing floor basis, which the parser refuses; a moved checkout or "
    "interpreter path, on either format, a hold until the move is undone; and, on version 2, which has "
    "no environment manifest, a changed interpreter version with the interpreter's bytes unchanged;")
sub("the demonstration is repeated on the new format before the first registration on it, and recorded "
    "with that registration.",
    "the demonstration is repeated on the new format before the first registration on it, and recorded "
    "with that registration. **The environment-manifest cases follow NP1.10(as), which the owner has "
    "not answered.** They are the cases decided by the manifest's pin (above). If (as) is answered no, "
    "the canary registers on version 2, which carries no manifest: those cases are not applicable "
    "before the canary, and the complete version 3 demonstration, those cases included, is required "
    "before the first version 3 registration. If (as) is answered yes, they are required before the "
    "canary's registration, with the rest of the demonstration.")
replace_line("  - **Run on the reference pilot's own packet, before each of its launch words.**", [
    "  - **Run on the reference pilot's own packet, before each of its launch words.** Before the "
    "launch word of each registration of the CHORUS reference pilot, the gate is run as production "
    "will run it, with that registration's own packet as the reference, against:",
    "    1. **itself,** with the inventory run on that real packet and showing every leaf classified;",
    "    2. **a packet for each other in-scope project,** built offline by the registration builder "
    "from the same source, with that project's real input tuple pinned at NP1b. Where no other "
    "project is in scope, as with CHORUS alone (NP1.2), this case is recorded as \"not applicable\";",
    "    3. **the reference pilot's packet with the floor's registration substituted:** a "
    "receipt-policy registration built as the floor's registration will be built, at its own path, "
    "carrying a registered floor and its basis with the value marked synthetic, and that synthetic "
    "registration as the floor's input.",
    "",
    "    Each must give \"equal\", apart from a case recorded as \"not applicable\". This is in addition "
    "to the demonstration above. The results go in that registration's outer evidence packet, and its "
    "reviews name the sha256s of each run's comparison-input manifest and result (NP1.10(aa)), so its "
    "coded word binds them.",
    "    - **The permission probes of packets (2) and (3).** The validators require a saved permission "
    "probe whose binding names the packet's own selection, instruction and system hashes "
    "(`native_shared_registration.py:168–180`, `:256–264`; `native_shared_permissions.py:1015–1019`), "
    "and only a binary call makes a real one. Two rules are fixed here, and neither changes a "
    "validator. **(i)** Each packet carries a permission probe rebuilt offline for its own selection "
    "and marked synthetic in the comparison-input manifest, and the unchanged validators accept it. "
    "**(ii)** If the demonstration shows that the unchanged validators cannot accept such a probe, the "
    "gate validates (2) and (3) with only the saved-probe check replaced by a recomputation of the "
    "expected binding, and its result lists that substitution. Which rule applies is a property of "
    "the validators, which the demonstration shows before the first registration on that format; no "
    "native outcome bears on it.",
    "    - **A failure.** A cause in the gate itself, such as a leaf the inventory does not classify, a "
    "wrong class or an error in the script, is a defect in the gate: the data file or the script is "
    "corrected and reviewed, and this run and the demonstration are repeated, before that word. A "
    "refusal of packet (2) or (3) by the validators is corrected in that packet's construction before "
    "that word. The gate's rule and data file are never changed to make a case pass."])
replace_line("    - **What it shows, and what it does not.** It runs the gate on the real format", [
    "    - **What it shows, and what it does not.** It runs the gate on the real format and runtime "
    "profile of the packet that becomes the reference, on every other in-scope project's real inputs, "
    "and on the floor's transition, which every production registration takes. The packets built "
    "offline make no binary call: their permission probes follow rule (i) or (ii) above, and the "
    "result says which. Where they cannot carry other evidence that only a binary call makes, the run "
    "records which fields stand in for it and how they are classed, and both reviewers check that no "
    "identical field was exempted to make a case pass. So it shows the gate's classification on "
    "production's format; it does not show that a real registration for another project will "
    "validate, or that a real probe will pass."])
sub("Each review of a registration made after the reference exists names the sha256s of the "
    "comparison-input manifest and of the gate's result. The coded word names the review bundle that "
    "carries both reviews (N1.9 item 4), so it binds the result it was given on.",
    "Each review of a registration made after the reference exists names the sha256s of the "
    "comparison-input manifest and of the gate's result, and each review of a registration of the "
    "CHORUS reference pilot names those of each run on its own packet. The coded word names the review "
    "bundle that carries both reviews (N1.9 item 4), so it binds the results it was given on.")

# ---------------------------------------------------------------- NP1.5: the floor list
sub("    - **the gate's result for the AI_READI pilot's registration is \"cannot decide\":** that "
    "registration waits, and so does the floor;",
    "    - **the gate's result for the AI_READI pilot's registration is \"cannot decide\":** that "
    "registration waits, and so does the floor. Where the cause is a defect under NP1.10(ar), as a "
    "cause in the gate itself is, the floor does not wait: this stratum ends at the filing, before the "
    "floor and before any production cell;")

# ---------------------------------------------------------------- NP1.7
sub("the demonstration is repeated on each later format before the reference (NP1.5). Assigned, not written.",
    "the demonstration is repeated on each later format before the reference (NP1.5). Its "
    "environment-manifest cases follow NP1.10(as): if (as) is answered no, they are not applicable "
    "before the canary and are required in full before the first version 3 registration; if it is "
    "answered yes, they are required before the canary's registration. The demonstration also shows "
    "which of the two probe rules applies to the run on the reference pilot's own packet (NP1.5). "
    "Assigned, not written.")
insert_after("    - **The environment manifest** (NP1.5): the version 3 preparation and execution documents", [
    "    - **The demonstration's environment-manifest cases** (NP1.5), in full, before the first version "
    "3 registration: the canary's if NP1.10(as) is answered yes; otherwise the first registration on "
    "version 3, the CHORUS reference pilot's at the latest."])
sub("the pins that will define the reference, and the gate's results on its own packet (NP1.5). Every "
    "review checks the recorded reasons NP1.5's bar requires.",
    "the pins that will define the reference, and the gate's results on its own packet, and names the "
    "sha256s of each of those runs' comparison-input manifests and results, so that the coded word "
    "binds them too (NP1.5). Every review checks the recorded reasons NP1.5's bar requires.")

# ---------------------------------------------------------------- NP1.9
sub("and the stratum's selection bounds; and the environment manifest, if NP1.10(as) is answered yes;",
    "and the stratum's selection bounds; and the environment manifest, with the demonstration's "
    "environment-manifest cases, if NP1.10(as) is answered yes;")

# ---------------------------------------------------------------- NP1.10
sub("A note after an item says how it differs from v10; an item with no note is unchanged from v10. The "
    "letters are v10's, with one added at the end: (as) is new; (aj) stays retired; (aa), (ak), (al), "
    "(ap), (aq), (ar), (c), (s) and (z) are changed.",
    "A note after an item says how it differs from v11; an item with no note is unchanged from v11. The "
    "letters are v11's: (aj) stays retired; (aa), (al), (aq), (ar) and (s) are changed.")
for note in (" *Changed: only as its own stratum.*",
             " *Changed: a repaired source for any registration of the reference pilot before the "
             "reference exists; which gate later comparisons name.*",
             " *Changed: ten items carry a written alternative, (as) among them.*",
             " *Changed: the canary changes no bound.*",
             " *New.*"):
    sub(note, "")
sub("while the gate cannot decide on the AI_READI pilot's registration;",
    "while the gate cannot decide on the AI_READI pilot's registration, unless the cause is a defect "
    "under (ar), as a cause in the gate itself is, which ends this stratum at its filing, before any "
    "production cell;")
sub("*Changed: N1's two sentences named.*",
    "*Changed: a \"cannot decide\" on the AI_READI pilot's registration whose cause is a defect under "
    "(ar) ends the stratum.*")
sub("For the CHORUS reference pilot, each confirms NP1b's conformance on its source, the pins that will "
    "define the reference, and the gate's results on its own packet. Every review checks the recorded "
    "reasons the bar requires; a reviewer does not judge a difference (NP1.7). *Changed: the word binds "
    "the gate's result; the reference pilot's own gate results.*",
    "For the CHORUS reference pilot, each confirms NP1b's conformance on its source, the pins that will "
    "define the reference, and the gate's results on its own packet, and names the sha256s of each of "
    "those runs' comparison-input manifests and results, so that its coded word binds them too. Every "
    "review checks the recorded reasons the bar requires; a reviewer does not judge a difference "
    "(NP1.7). *Changed: the reference pilot's own gate runs bound by hash.*")
# (al)
sub("and among paths only the per-attempt roots (attempt, evidence, output and stage), the paths under "
    "them and the per-attempt files (registration, instruction and probe) are;",
    "and among paths only the per-attempt roots (attempt, evidence, output and stage), the paths under "
    "them and the paths of the files each registration writes for itself (the registration and its "
    "selection, composition, runtime declaration, environment manifest, instruction, probe and "
    "receipt-policy registration files, the floor's registration among them) are;")
sub("The floor's change from pending to registered is checked separately against the floor's "
    "registration, which is the reference's receipt-policy registration with `coverage_floor` replaced.",
    "The floor's change from pending to registered is checked separately against the floor's "
    "registration, which is the reference's receipt-policy registration with `coverage_floor` "
    "replaced, at its own path; a structurally valid other value is \"not equal\", and a wrong or "
    "missing basis, which the parser refuses, is \"cannot decide\".")
sub("A differing pin decides \"not equal\" before validation only where it is a valid must-equal "
    "implementation or asset pin;",
    "A differing pin decides \"not equal\" before validation only where it is a valid must-equal "
    "implementation or asset pin, as the environment manifest's pin and the dependency registry's "
    "sha256 pins, the interpreter's among them, are; a moved checkout or interpreter path is no such "
    "pin and gives \"cannot decide\", a hold until the move is undone;")
sub("The data file is demonstrated on every listed case before the canary's registration and again "
    "whenever the format changes before the reference; and before each launch word of the CHORUS "
    "reference pilot the gate is run on that registration's own packet against itself, another "
    "project's packet and a packet carrying a registered floor, each giving \"equal\".",
    "The data file is demonstrated on every listed case before the canary's registration and again "
    "whenever the format changes before the reference; its environment-manifest cases follow (as): if "
    "(as) is answered no, they are not applicable before the canary and are required in full before "
    "the first version 3 registration, and if it is answered yes, they are required before the "
    "canary's registration. Before each launch word of the CHORUS reference pilot the gate is run on "
    "that registration's own packet: against itself, with the inventory on that real packet; against "
    "a packet with each other in-scope project's real tuple, recorded as \"not applicable\" where "
    "there is none; and against that packet with the floor's registration substituted; each giving "
    "\"equal\". Those offline packets carry a permission probe rebuilt offline for their own selection "
    "and marked synthetic, for the unchanged validators to accept; if the demonstration shows that they "
    "cannot accept it, the gate validates those packets with only the saved-probe check replaced by a "
    "recomputation of the expected binding, and its result says so. Neither rule changes a validator, "
    "and a refused packet is corrected in its construction, never by changing the gate's rule or data "
    "file to make a case pass.")
sub("*Changed: the shortcut and its precedence; the checkout and interpreter paths identical; the "
    "validators' reconstruction; the environment manifest's approved contract; the floor's registration "
    "document; the four input pins; every demonstration case and the inventory; the gate run on the "
    "reference pilot's own packet; restoration of host state.*",
    "*Changed: the gate's results by its precedence (the floor's basis, moved paths, the interpreter); "
    "the environment-manifest cases conditional on (as); per-registration paths, the floor's "
    "registration among them; the run on the reference pilot's own packet, with its probe rules and "
    "the case of no other project.*")
# (aq)
replace_line("- **(aq)** The prerequisites:", [
    "- **(aq)** The prerequisites: NP1.7's list, each item with its one deadline: before the canary's "
    "registration; before NP1b; before the CHORUS reference pilot's registration at the latest, for "
    "the environment manifest, which is due before the canary's registration if (as) is answered yes; "
    "for the demonstration's environment-manifest cases, before the canary's registration if (as) is "
    "answered yes, and if it is answered no, before the first version 3 registration, since they are "
    "not applicable before the canary; or before each launch word of the CHORUS reference pilot, for "
    "the gate's run on that registration's own packet. The list and its deadlines are the lead's "
    "(NP1.7). *Changed: the deadline of the demonstration's environment-manifest cases follows (as).*"])
# (ar)
replace_line("- **(ar)** Repairs during production:", [
    "- **(ar)** Repairs during production: after the reference run, a change to anything the gate holds "
    "identical is made only for a qualifying defect. That is a filed defect that stopped an attempt's "
    "acceptance, classed instrument, registration or environment, record shape or transport, or an "
    "unknown stop once reclassified into one of these; or a preparation, registration or comparison "
    "defect, confirmed by both reviewers, that prevents an otherwise eligible registration before any "
    "reservation, recorded as a pre-reservation defect and spending no attempt. The boundary is fixed "
    "when the defect is filed, before the next registration: both reviewers record whether its repair "
    "needs changed must-equal bytes. No registration is made and no attempt is launched under this "
    "amendment until both have recorded and, where they disagree, until the owner has adjudicated. An "
    "unknown stop holds every registration and every launch under this amendment until the owner "
    "reclassifies it; if it then qualifies, its defect is filed at the reclassification. If the repair "
    "needs changed must-equal bytes, no further registration is made and no attempt of this stratum is "
    "launched from the moment of filing, the stratum ends for every registration made after the "
    "boundary, and a registration made before it and not yet launched is withdrawn; if it does not, "
    "the stratum continues, and that defect cannot later end it. Restoring host state to the "
    "reference's bytes and paths is not a repair. This stratum's results stand under the plan's kinds "
    "of missing; a later stratum is reported separately, never pooled with this one and never put in "
    "its place. A stratum that follows this one after the reference run is exploratory unless it "
    "begins at a boundary this item fixes and every change it carries has the recorded reason the bar "
    "requires; before the reference exists, a repair after a failed canary or reference-pilot attempt "
    "follows the pre-reference rules and makes nothing exploratory, and a stratum begun then by a "
    "prospective amendment is classed by that amendment, under the bar. A change for any other reason "
    "is not made during production (NP1.5). *Changed: every registration and launch held while a "
    "classification is open; an unknown stop's defect filed at its reclassification; an unlaunched "
    "registration withdrawn; the exploratory test scoped to strata after the reference run.*"])

# ---------------------------------------------------------------- write and check
out = W / REL
out.write_text(text, encoding="utf-8")
data = out.read_bytes()
lines = data.decode("utf-8").split("\n")
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", len(lines) - 1, "bytes", len(data))

assert "@" not in text, "at-sign in the draft"
for stale in ("v11 has not been reviewed", "*New.*", "per-attempt files", "a wrong floor basis;",
              "a floor value or basis other than",
              "makes every registration built after the move not equal"):
    assert stale not in text, stale
# The old phrase survives only as the response table's quotation of the finding.
quoted = [l for l in text.split("\n") if "the bytes it holds must not change" in l]
assert len(quoted) == 1 and quoted[0].startswith("| Claude P3-1:"), quoted
for issue in range(6130, 6139):
    assert f"#{issue}" in text, issue
letters = re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*", text, flags=re.M)
assert len(letters) == 45 and letters[0] == "a" and letters[-1] == "as", (len(letters), letters[:3], letters[-3:])
notes = [m for m in re.findall(r"^- \*\*\(([a-z]{1,2})\)\*\*.*\*(Changed|New)[:.]", text, flags=re.M)]
print("items with a change note:", [n[0] for n in notes])
assert sorted(n[0] for n in notes) == sorted(["aa", "al", "aq", "ar", "s"]), notes
# (as) must stay an open question: nothing may say it was answered.
for claim in ("(as) is answered\" ", "answered (as)", "(as): answered", "Answered: A", "Answered: B (as)"):
    assert claim not in text, claim
print("post-checks passed")
