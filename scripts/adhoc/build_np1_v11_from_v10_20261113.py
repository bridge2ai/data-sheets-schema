#!/usr/bin/env python3
"""Build draft v11 of analysis plan amendment NP1 from draft v10.

Purpose: apply the v11 rulings and the answers to the v10 reviews (issues
#6112 to #6129) to the v10 text, by line-anchored edits whose original lines
are asserted, so that the change from v10 to v11 is reproducible.
Inputs: v10 read from git at commit 2f5c66797 in the NP1 worktree, asserted
by sha256 f99b7e76...472b.
Output: the amendment file in the NP1 worktree, overwritten with v11; prints
its sha256, line count and byte count, and runs post-checks.
Serves: NP1 draft v11 (branch claude/native-production-amendment-np1-20261112).
Date: 2026-11-13. Written by a copy of the Claude lead; left uncommitted in
the report worktree, as directed.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

W = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
         "claude-native-production-amendment-np1-20261112")
REL = "notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md"
V10_COMMIT = "2f5c66797e8d304d1fcda6d0007ac501f3a27d92"
V10_SHA = "f99b7e76df2ba6b9ff81b69c65652ae441058b187bcf2ec4decf59ed4f04472b"

raw = subprocess.run(["git", "-C", str(W), "show", f"{V10_COMMIT}:{REL}"],
                     check=True, capture_output=True).stdout
assert hashlib.sha256(raw).hexdigest() == V10_SHA, "v10 bytes differ from the reviewed draft"
text = raw.decode("utf-8")
parts = text.split("\n")
assert parts[-1] == "", "v10 should end with one newline"
V = parts[:-1]
assert len(V) == 596, len(V)


def L(n):
    """v10 line n (1-based)."""
    return V[n - 1]


def block(s):
    return s.strip("\n").split("\n")


def sub(n, old, new):
    line = L(n)
    assert line.count(old) == 1, (n, old[:60], line.count(old))
    return line.replace(old, new)


ops = []  # (start, end, prefix_of_start, new_lines)


def replace(start, end, prefix, new_lines):
    assert L(start).startswith(prefix), (start, prefix, L(start)[:80])
    ops.append((start, end, new_lines))


def insert_after(n, prefix, new_lines):
    assert L(n).startswith(prefix), (n, prefix, L(n)[:80])
    ops.append((n + 1, n, new_lines))  # empty range before line n+1


# ---------------------------------------------------------------- header
replace(3, 3, "**Status: draft v10", block("""
**Status: draft v11, written by a copy of the Claude lead on 2026-11-13.**
"""))

replace(4, 5, "- **Earlier drafts.**", block("""
- **Earlier drafts.** v1 to v9, with their commits, hashes, reviews and issues (#5914 to #5925, #5940 to #5964, #5969 to #5988, #5996 to #6014, #6017 to #6029, #6032 to #6045, #6050 to #6064, #6075 to #6092, #6095 to #6109), are listed in the headers of v4 to v10. Each draft answered every finding of the one before; its response table is in its own commit. Review files are kept outside the repository and are cited by sha256.
- **v10** (commit `2f5c66797e8d304d1fcda6d0007ac501f3a27d92`, file sha256 `f99b7e76df2ba6b9ff81b69c65652ae441058b187bcf2ec4decf59ed4f04472b`) was reviewed twice, and both reviews said "ratifiable after listed fixes": a Codex CLI pass (review sha256 `fa03b5d563bd6f90919c7c65b6ef564255862f7374cabe5b3a9d9e7ab87b98ba`; 3 P1, 4 P2) and a Claude reviewer, a fresh session run on another model (review sha256 `b974dc0e16633c93e781f8b30c116433a709add60c1754f7e617196d090b61bb`; 1 P1, 4 P2, 10 P3). The 22 findings are filed as 18 issues, #6112 to #6129; four of the Codex findings are appended to the Claude issue on the same point.
"""))
assert L(5).startswith("- **v9** (commit")

replace(7, 20, "- **v9 → v10 closes", block("""
- **v10 → v11 tests the gate on what production will give it, and fixes when a repair ends the stratum.** Both reviews of v10 found that a defect in the gate could still show first after the reference run: no demonstrated case carried a registered floor, or the format the reference pilot will register on (the Claude review), and a differing pin could decide "not equal" before the permitted differences were considered (the Codex review). The Codex review also found that a defect stopping a registration before any reservation had no remedy, and that the point at which a repair ends the stratum could still be chosen after later readings. v11:
  - lets a differing pin decide "not equal" before validation only where it is a valid must-equal implementation or asset pin, and states the precedence of the three results (NP1.5);
  - runs the gate, before each launch word of the CHORUS reference pilot, on that registration's own packet: against itself, against another project's packet and against a packet carrying a registered floor. This is in addition to the demonstration before the canary, which now lists every case with its result, classes every leaf of every recorded document, and is repeated whenever the registration format changes before the reference (NP1.5, NP1.7);
  - makes the checkout path and the interpreter's path fields the gate holds identical, says that the validators run at that path from the reference's bytes, and says that their reconstruction of derived values is part of validation (NP1.5);
  - writes in the lead's approved contract for the environment manifest: version 3 preparation and execution documents, every hashed installed file verified at preparation and at dispatch, and version 2 refused for new registrations once version 3 is in; due before the CHORUS reference pilot's registration at the latest (NP1.5, NP1.7);
  - asks the owner, in a new item, whether the canary registers on the version 3 documents (NP1.7, NP1.10(as));
  - extends (ar) to defects that stop a registration before any reservation, fixes the end of the stratum at the moment a qualifying defect is filed, and states one scope and one test for an exploratory stratum (NP1.5, NP1.10(ar));
  - says what the floor's registration document carries, and names the four input pins of a project's tuple (NP1.2, NP1.5);
  - takes in D146 and corrects the passages it made stale; names the two sentences of amendment N1 that rest on D109's superseded clause; and says that Kids First could join only as its own stratum and that the canary changes no bound (Authority, NP1.2, NP1.5, NP1.9, NP1.10).

  There are 45 letters, (a) to (as). (aj) is retired; the other 44 are the items of the ballot.
- **v11 has not been reviewed.**
"""))
assert L(20) == "- **v10 has not been reviewed.**"

replace(32, 32, "  - the owner's decisions D138 to D145",
        [sub(32, "D138 to D145 (Authority)", "D138 to D147 (Authority)")])
replace(33, 33, "  - the independent review of the replay comparison script",
        [sub(33, " and the two reviews of v9 (#6095 to #6109), which",
             ", the two reviews of v9 (#6095 to #6109) and the two reviews of v10 (#6112 to #6129), which")])
assert L(37).startswith("- **Source references** are to commit") and L(37).endswith(".")
replace(37, 37, "- **Source references**", [L(37) + (
    " For v11 the author of this draft read, at commit `7b851213f3492144cfd5b83d6bbd9a8a040e9132`"
    " of the same branch, which the lead published on 2026-11-13 and which is cited below as"
    " \"the candidate\", the selection's input pins and profile (`native_shared_contract.py:716–735`)"
    " and the receipt-policy registration's parser (`:785–813`); and, at main"
    " `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`, the `profile:` keys of the study's source manifest"
    " and of the Kids First manifest.")])

# ---------------------------------------------------------------- responses
assert L(59).startswith("| Codex P2-3: the packet hash appears")
replace(40, 59, "## Responses to the reviews of v9", block("""
## Responses to the reviews of v10
Each issue stays open until a re-check of v11 confirms the answer. "Claude" and "Codex" name the two v10 reviews; both used the keys P1-1, P2-1 and so on, so each key is given with its review. The responses to the reviews of v9 are in v10's own commit.

| v10 finding | Issue | Answer in v11 | Where |
|---|---|---|---|
| Claude P1-1: before the reference exists, nothing shows the gate saying "equal" on what production will give it: a registered floor, or the format the reference pilot registers on | #6112 | Before each launch word of the CHORUS reference pilot, the gate is run with that registration's own packet as the reference: against itself, against a packet for another in-scope project built offline with that project's tuple, and against a packet carrying a registered floor whose value is marked synthetic. Each must give "equal"; a failure is corrected in the gate before that word. This is in addition to the demonstration before the canary. Every later comparison names the gate last run on the reference run's own registration, and that registration's reviews report the results | NP1.5, NP1.7, (aa), (al), (aq), (z) |
| Claude P2-1, with Codex P2-2: the demonstration leaves out cases, among them a valid floor transition, an unclassified field, a changed environment manifest and a wrong tuple; and the floor's registration document is not specified | #6113 | The demonstration lists every case with its expected result: six "equal" (a valid floor transition, an expired reference and a reference whose attempt consumed its reservation among them), ten "not equal" (two differences together, both listed, among them), four "cannot decide", and the mixed case of the precedence rule. A machine-checkable inventory classes every leaf of every recorded document, so that no derived document hides a scientific leaf. It is repeated whenever the format changes before the reference. The floor's registration is the reference's receipt-policy registration with `coverage_floor` replaced; its seven fields are named. Its `registration_id` is a per-run field, by the lead's ruling, which v11 follows rather than the review's proposal to keep the reference's id | NP1.5, (al) |
| Claude P2-2, with Codex P2-3: the validators tie each packet to its checkout path and interpreter, which v10 classed as per-run | #6114 | The checkout path and the interpreter's path are identical fields across the stratum. Among paths, only the per-attempt roots (attempt, evidence, output and stage), the paths under them and the per-attempt files (registration, instruction and probe) are per-run. The validators run at the reference's checkout path, under its interpreter, from bytes verified to equal the reference's source export, never from bytes that differ from its pins. Moving the checkout or the interpreter makes every later registration not equal until the move is undone; v10's sentence that a move does not end the stratum is withdrawn | NP1.5, (al) |
| Claude P2-3, with Codex P1-3: two scopes for which registrations a repair removes, two tests for an exploratory stratum, and an end of the stratum that can still be chosen after later readings | #6115 | One scope: a stratum ends "for every registration made after the boundary". The boundary is fixed when a qualifying defect is filed, which is before the next registration, and both reviewers record whether its repair needs changed must-equal bytes. If it does, no further registration is made from that moment. If it does not, the stratum continues, and that defect cannot later end it. One test for an exploratory stratum, the same in the body and in (ar). The sentence that the restriction "leaves no route" is replaced by a plain statement of what remains a judgement | NP1.5, (ar) |
| Claude P2-4, with Codex P2-1: the text on the environment manifest does not follow the lead's later ruling: the successor documents, the check at launch, the deadline and the canary | #6116 | The approved contract is written in: version 3 preparation and execution documents with one required `environment_manifest` pin, regenerated and checked at preparation and again at dispatch, and version 2 refused for new registrations once version 3 is in. The deadline is before the CHORUS reference pilot's registration at the latest, and before the canary's if the owner answers yes to the new item (as), which asks whether the canary carries version 3 and quotes N1.1. NP1b names whether the check at dispatch comes before the reservation, and the text says what each case costs | NP1.5, NP1.7, (aq), (as) |
| Claude P3-1: D146 made three passages stale | #6117 | D146 is quoted under Authority. The three passages now say that the owner approved the changed asset, with the basis sentence, and its pin, and that per the lead's record both are applied on the published candidate | Authority, NP1.5, NP1.7 |
| Claude P3-2: N1.4(B) row 5 and N1.5's premise rest on the D109 clause v10 supersedes, while v10 lists N1.4(B)'s rows as unchanged | #6118 | Both sentences are quoted and named as superseded for this amendment, beside D109's clause, and "Unchanged" excepts them. N1's text is not edited, and its item (ah) stands as ratified | NP1.5, NP1.9, (s) |
| Claude P3-3: "N1.5 requires that record" holds only after a "no" to N1's item (ah) | #6119 | Corrected: this amendment requires that record | NP1.5 |
| Claude P3-4: "no code ... is run to produce what the model reads" contradicts the validators the gate must run | #6120 | Rewritten: the gate runs no attempt and no behavioural replay, and calls no model and no binary. The only code it runs is the production validators, from the reference's bytes, and their deterministic reconstruction of derived values is part of validation | NP1.5, (al) |
| Claude P3-5: nothing makes the coded word bind the gate's result, and the validators' code is unnamed | #6121 | Each review of a registration made after the reference exists names the sha256s of the comparison-input manifest and of the gate's result. The coded word names the review bundle that carries both reviews (N1.9 item 4), so it binds them. The comparison-input manifest names the reference's source export by the digests it was checked against | NP1.5, NP1.7, (aa) |
| Claude P3-6: the input tuple's fifth member, the scope declaration, has no pin of its own | #6122 | The tuple is the four input files a selection pins: the study's source manifest as one whole file, and the project's bundle, chunk manifest and generation (omission) context. The scope declaration sits inside the context and the source manifest, and their sha256s cover it | NP1.2, NP1.5 |
| Claude P3-7: restoring host state to the reference's bytes is not said to be outside (ar) | #6123 | Said: restoring host state to the reference's bytes and paths is not a repair under (ar), and a registration made after the restoration is compared like any other | NP1.5, (al), (ar) |
| Claude P3-8: Kids First could be added only as a separate stratum | #6124 | Said, with the reason: its manifest declares the neutral profile and the study's the bridge2ai profile, and the profile is a field the gate holds identical, so no Kids First registration can equal the CHORUS reference | NP1.2, (c) |
| Claude P3-9: the shakedown cannot correct a bound | #6125 | Said in (ap) and under B: what the canary shows changes no bound. A bound found too small is corrected before the reference only by a ratified change to this amendment, under the bar, and after it only in a new stratum. A pilot stopped by a run-time bound is classed like any other stop, and an impossible limit concludes it | NP1.5, NP1.7, (ap) |
| Claude P3-10: a repair found before the reference pilot's first registration has no route | #6126 | Any registration of the CHORUS reference pilot made before the reference exists may be on a repaired source, with NP1b's checks repeated on it first | NP1.6, NP1.7, (z) |
| Codex P1-1: the early pin rule lets any differing pin decide "not equal" before the permitted differences are considered | #6127 | The shortcut applies only to a valid must-equal implementation or asset pin. Project-tuple substitutions, derived values and the floor's transition never take it. A prohibited difference established on valid evidence gives "not equal" even where other evidence is invalid; otherwise invalid or unclassified evidence gives "cannot decide". The result lists every difference and evidence problem it established | NP1.5, (al) |
| Codex P1-2: a gate or preparation defect found before the reservation has no remedy under (ar) | #6128 | (ar) also covers a preparation, registration or comparison defect, confirmed by both reviewers, that prevents an otherwise eligible registration before any reservation. It is recorded as a pre-reservation defect and spends no attempt. A repair that changes must-equal bytes still ends the stratum at its boundary | NP1.5, NP1.6, (ar) |
| Codex P2-4: equal `RECORD` bytes do not show equal installed files | #6129 | Generating the manifest, at preparation and at dispatch, checks every installed file that a third-party distribution's `RECORD` lists with a hash. A mismatch, a missing or unreadable file, or an editable install holds. Entries listed without a hash are named as unverified, by kind, with their count | NP1.5, (al) |
"""))

# ---------------------------------------------------------------- authority
insert_after(88, "    - **What they are not:**", block("""
  - **D146 and D147 (recorded 2026-11-13T04:37:43Z).** The owner answered, verbatim: "hash yes, shards yes".
    - **D146:** "The successor post-image of the protected `src/download/prompts/canonical_hashes.yaml` is approved at sha256 `d0de85f3da4bfa29a4bfc7ad6158abad5b3373a937a4e7e3b360217fa4eaf57f`, together with the receipt-policy asset it pins (`src/download/prompts/native_shared_receipt_policy_v1.md`, sha256 `8b0695212d94380949ddc523963021b1edcb3ebb9b6a52291d36238a92779f1c`, 2,510 bytes), including the lead's wording of the basis sentence:" The sentence it approves reads: "The registered production floor is the exact integer fraction with_receipt_at_receipt / receiptable_at_receipt: the coverage of the sealed phase-1 record under the completed effective receipt (basis receipted_part). Later edits of the record cannot change it." Per the lead's record, both files are applied on the published candidate (entry of 2026-11-13T04:46:50Z).
    - **D147** sets the CI shard counts. It does not bear on this amendment's rules.
    - **Not given:** "any merge approval, launch word or real-binary authorization."
"""))

insert_after(95, "  - **The gate's validators and an environment manifest**", block("""
  - **The environment manifest's versioned change** (entry of 2026-11-13T04:46:50Z). Helper 3 found that the manifest "cannot be bound without a new kind or version of a registered document (the preparation and execution have closed fields and fixed artifact roles)", so the ruling's condition for one more artifact could not be met. "**The lead approved its proposal** (`claude-lead-helper3-environment-manifest-ruling-20261113.md`, delivered at 04:46Z): successor preparation and execution kinds, one required `environment_manifest` pin regenerated and checked at launch, v2 kept historical only and refused for new registrations, within N1.9 item 4 as the review bundle's version 3 was; deadline before the CHORUS reference pilot's registration at the latest, aiming for the canary's source. Then the gate schema against the final format." NP1.5, NP1.7 and NP1.10(al), (aq) and (as) put it to the owner.
  - **Three refinements from the Codex review of v10** (entry of 2026-11-13T04:52:06Z): "the manifest verifies every hashed installed file against its `RECORD` entry at preparation and at dispatch, and an editable third-party install holds; the checkout path and the interpreter path are must-equal across the stratum (only the per-attempt roots and file paths are per-run); and the demonstration covers every branch, a valid floor transition included, with a machine-checkable field-coverage inventory, repeated whenever the format changes before the reference." With the checkout path identical, the reference's source export and the candidate's tree are one directory, so NP1.5 states the condition of the ruling of 04:21:26Z as: never from bytes that differ from the reference's pins. NP1.5 and NP1.10(al) put these to the owner.
  - **The rulings for v11** (entry of 2026-11-13T05:33:41Z): "the early pin shortcut only for valid must-equal pins, with a stated precedence; defects found before reservation inside item (ar); the stratum's end fixed when a qualifying defect is filed; the gate run on the reference pilot's own packet, another project's and a registered-floor packet before the reference pilot's launch word; the environment-manifest contract written in; checkout and interpreter paths must-equal; the full list of demonstration cases." The same entry names "**One new owner item:** whether the canary carries version 3 of the preparation and execution documents (the lead recommends yes, reading N1.1's axis as the authority's rules, unchanged apart from one required pin) or runs version 2 exactly as N1 ratified." That is NP1.10(as). It also records: "**Helper 3 had already implemented the successor kinds** before the lead weighed N1.1's wording: nine commits on `codex/native-environment-manifest-20261113` (`a3a79c06f` to `9afd6d64a`; kinds `d4d_native_shared_preparation_v3`, `d4d_native_shared_execution_registration_v3`, `d4d_native_environment_manifest`). They are kept; the owner's answer decides whether the canary's source carries them."
"""))

# ---------------------------------------------------------------- NP1.2
replace(120, 120, "  - **Scope is decided at NP1b, by one test of inputs.**", [sub(
    120,
    "**NP1b also pins each in-scope project's input tuple:** the study's source manifest as one whole file, and the project's bundle, chunk manifest, omission context and scope declaration, each by sha256. Every registration for that project must match it (NP1.5).",
    "**NP1b also pins each in-scope project's input tuple:** the four input files a selection pins (`native_shared_contract.py:716–725`, at the candidate), each by sha256: the study's source manifest as one whole file, and the project's bundle, chunk manifest and generation (omission) context. The project's scope declaration has no file of its own: it sits inside the context and the source manifest (`native_shared_selection.py:392–398`, audit, from the Claude review of v10), and their sha256s cover it. Every registration for that project must match the tuple (NP1.5).")])

replace(131, 131, "  - **A later addendum can add it,**", block("""
  - **A later addendum can add it only as its own stratum,** never compared with this one or pooled into it, once its inputs test is specified: which manifest bytes, how its vocabulary is declared, and under which limit set. No Kids First registration can equal the CHORUS reference: at main its manifest declares `profile: neutral` and the study's declares `profile: bridge2ai`, and a registration carries its profile (`native_shared_contract.py:726–732`), which changes what the model reads and so is a field the gate holds identical (NP1.5). Until such an addendum it has no native cell. It is labelled "not planned (NP1)", which is not missing, and it is counted nowhere. **If the answer is no,** the item returns for redrafting (NP1.10).
"""))

# ---------------------------------------------------------------- NP1.5 floor text
replace(215, 215, "  - **What this amendment changes in it**", [sub(
    215,
    "That supersedes D109's clause \"The measured value informs a registered native floor before any native replicate.\" D109's pending floor for the canary,",
    "That supersedes D109's clause \"The measured value informs a registered native floor before any native replicate.\" For this amendment it also supersedes the two sentences of amendment N1 that rest on that clause: N1.4(B) row 5's \"The measured counters inform a registered native floor before any native replicate (D109).\", and N1.5's premise for its item (ah), \"This canary supplies the reading a native replicate floor is computed from.\" N1's text is not edited, and its item (ah) stands as ratified: this amendment is still ratified before the canary's word (below). D109's pending floor for the canary,")])

replace(218, 218, "  - The policy asset said what the code at the cited commit did:", block("""
  - The policy asset said what the code at the cited commit did: "A pending floor remains a diagnostic pilot and cannot satisfy strict completion." That sentence is model-facing. The owner chose its replacement on 2026-11-12 (D142, quoted under Authority). The asset's pin sits in a protected file, and on 2026-11-13 the owner approved the changed asset and that file's new hash together (D146). Per the lead's record both are applied on the published candidate (NP1.7). The new sentence changes what the canary's model reads, so it is in the assets the canary's registration pins (below).
"""))

replace(223, 223, "  Registering a value makes new registration bytes", [L(223) +
        " What that document carries, and which of its fields may differ from the reference's, is set under the gate (below)."])

replace(229, 229, "  - **What the code does today.**", block("""
  - **What the code did at the cited commit.** The native `floor()` read only the final-record counters, `with_receipt` and `receiptable` (`native_shared_receipts.py:250–259`, `:296–307`), and the native registration had no basis field (`native_shared_contract.py:803–808`). The policy asset said the same: "The registered production floor is the exact integer fraction with_receipt / receiptable on the final record, using the unchanged receipt counters." D146 approved its replacement (Authority).
"""))

replace(231, 231, "  - **What it needs: an engineering prerequisite", [sub(
    231,
    "The policy asset's sentence quoted above is changed to name the basis, and that wording goes to the owner with the changed pin's hash (D142). NP1.7 gives its state.",
    "The policy asset's sentence quoted above is changed to name the basis, in the lead's wording, which the owner approved with the changed pin's hash (D146, quoted under Authority); per the lead's record it is applied on the published candidate (NP1.7).")])

replace(233, 233, "  - **What it changes for the canary itself.**", [sub(
    233,
    "Its row 0 is implemented by the #5939 repair, and its row 5 keeps the canary's reading reported and UNMEASURABLE.",
    "Its row 0 is implemented by the #5939 repair, and its row 5 keeps the canary's reading reported and UNMEASURABLE; row 5's last sentence, which restates D109's clause, is superseded for this amendment (above).")])

replace(242, 242, "  - **If the canary's word were given before this amendment was ratified,**", [sub(
    242, "N1.5 requires that record.",
    "this amendment requires that record. N1.5 asks for one only under its \"What a no leaves\", after a \"no\" to N1's item (ah), and D138 answered that item yes.")])

replace(251, 251, "  - **After the reference run the bar acts through NP1.10(ar).**", block("""
  - **After the reference run the bar acts through NP1.10(ar).** A change of a field the gate holds identical is then made only for a qualifying defect, and it ends this stratum for every registration made after the boundary that (ar) fixes (below), so "not admitted" has nothing left to act on there. Whether a later stratum is exploratory is decided by the one test (ar) states (below).
"""))

# ---------------------------------------------------------------- NP1.5 reference run and gate
assert L(254).startswith("- **The reference run** [proposed, NP1.10(al)].")
assert L(255).startswith("  - **What it is.**")
assert L(258).startswith("  - **No pilot is run again.**")
assert L(264).startswith("    - **the binary.**")
assert L(268).startswith("    - **the probe's limits.**")
assert L(269).startswith("- **The gate** [proposed, part of NP1.10(al)]")
assert L(271) == "  - **The principle.**"
assert L(287).startswith("  - **What it cannot show.**")
assert L(288).startswith("  - **The selection bounds** [proposed, NP1.10(ap)].")
assert L(289).startswith("  - **Where the run limits stand.**")

new_256 = sub(256,
              "the closed dependency registry of the package's own source files, the interpreter's version, the environment manifest, and every registered value",
              "the closed dependency registry of the package's own source files, the checkout path, the interpreter's identity and path, the environment manifest, and every registered value")
new_257 = sub(257,
              "**Equal:** the registration belongs to this stratum. **Not equal:**",
              "**Equal:** the registration belongs to this stratum, unless it is made after a boundary that NP1.10(ar) fixes (below). **Not equal:**")

R1 = block("""
  - **Production runs on frozen code.** After the reference run, a registration in which any field the schema classes as identical differs from the reference's, other than the floor's permitted change (below), is not equal and is not made under this amendment. That covers a change to a pinned file, an asset, the binary, the base system instructions, the selection bounds, the checkout path, the interpreter, the environment manifest, a registered value, or the gate's own script or data file. During production such a change is made only under NP1.10(ar), and it ends this stratum for every registration made after the boundary that item fixes (below). The registrations that carry it need a new prospective amendment, which names its own pilots before any of them runs and is bound by the bar above. This stratum's floor, its K_native and its readings never move, and a reading that a later stratum does not use is still reported. **There is no "equal change":** a change either leaves every identical field as it was, or it is made only under (ar), at a boundary. So D35's diagnostic canary does not arise inside this stratum (NP1.7).
  - **Repairs during production** [proposed, NP1.10(ar)]. After the reference run, a change to anything the gate holds identical is made only for a **qualifying defect**, and the stratum ends at a boundary fixed when that defect is filed.
    - **A qualifying defect** is one of two kinds:
      1. **a filed defect that stopped an attempt's acceptance,** where that attempt's primary cause class under NP1.6 is one of the plan's classes instrument (row 1), registration or environment (row 4), record shape (row 6) or transport (row 7) (plan lines 1350–1358). An unknown stop (row 9) qualifies only once the owner's adjudication reclassifies it into one of these. On this arm row 4 includes host and usage stops, and a row-6 stop is the model's own wrongly shaped value, because the arm has no write-time normaliser (NP1.6);
      2. **a defect that stops a registration before any reservation:** a preparation, registration or comparison defect, confirmed by both reviewers, that prevents an otherwise eligible registration. Examples are a field the gate's data file does not classify, a validator that refuses a correct packet, and host state that cannot be restored. It is recorded under its own classification, **a pre-reservation defect**, and it spends no attempt, because no reservation was consumed (NP1.6).

      A rule-level finding, a content slip, an impossible limit or a budget or clock stop does not qualify: the first two are about generated content, and the plan already makes a corrected limit a new condition identity (its row 5). **A change for any other reason is not made during production.**
    - **The boundary is fixed when the defect is filed.** A stop's defect is filed with the stop's classification, and a pre-reservation defect when the registration it prevents is held; either is filed before the next registration under this amendment. Both reviewers record, with the defect, whether its repair needs changed must-equal bytes, that is, a change to any field the gate holds identical or to the gate's own script or data file. No registration is made until both have recorded. Where they disagree, the owner adjudicates, as for any disagreement between the reviewers (D36); the boundary, if there is one, is still the moment of filing.
      - **If the repair needs changed must-equal bytes,** no further registration is made in this stratum from the moment of filing. The stratum ends there, for every registration made after the boundary, whether or not that registration would carry the repair.
      - **If it does not,** because the repair restores unchanged registered bytes or host state, or reads saved evidence again offline with the same code, the stratum continues. A defect once resolved without changed bytes cannot later end the stratum.
      - **Restoring host state to the reference's bytes and paths is not a repair under this item.** A registration made after the restoration is compared like any other.
    - **What it leaves.** This stratum's results stand as they are: its cells, accepted or not, keep their records and readings, and a cell it did not run is described by the plan's kinds of missing (lines 777–781). A later stratum, under its own prospective amendment, is reported separately; it is never pooled with this stratum and never put in its place.
    - **One test for an exploratory stratum,** the same here and in NP1.10(ar): a later stratum is exploratory unless it begins at a boundary this item fixes and every change it carries has the recorded reason the bar requires.
    - **Why only these, and why at filing.** A change after the reference run ends the stratum, so whether to take one, and when, are choices that production readings could otherwise steer. The trigger is tied to the plan's classes or to a defect that stops a registration before any reservation, and the end is fixed at the moment the defect is filed, so no one chooses when the stratum ends.
    - **What remains a judgement.** The stop's class, read by the plan's precedence; the reviewers' record of whether a repair needs changed must-equal bytes; and the owner's words, which can end production early by being withheld, as they always could (NP1.2). Each is recorded, and none may rest on a native quality value (the bar above). The leverage is bounded: this stratum's results stand, and a later stratum never replaces them.
  - **What this costs, and the precautions.** A repair of anything the gate holds identical cannot be taken into this stratum after the reference run, however small. The repairs the canary reveals go in before the CHORUS reference pilot registers (NP1.7). Changes nobody chooses would also stop further registrations, and the source shows which host state they touch (read by the lead at the cited commit, except where marked). **Restoring that state to the reference's bytes and paths is not a repair under NP1.10(ar):** a registration made after the restoration is compared like any other.
""")

R2 = block("""
    - **the interpreter and the third-party distributions.** The composition records the interpreter's path and its full version string (`native_shared_registration.py:116–119`; `native_shared_controller.py:100–106`). Both are identical fields, so an interpreter upgrade, or an interpreter at another path, makes later registrations not equal. The execution body's dependency registry pins the package's own source files by digest (`native_shared_registration.py:141–144`, `:253–254`, `:266–279`), not the third-party distributions, although the helpers execute LinkML, the term validator and their dependencies. Those are bound by the environment manifest (below), which the gate holds identical and which is checked again at dispatch. So a rebuilt environment whose distributions or installed files differ makes later registrations not equal, and a change after a registration is prepared holds its launch;
    - **the checkout.** Its absolute path is recorded as the working directory and in every absolute pin, and the validators the gate runs reconstruct it from the process that runs them. Launch re-verification refuses unless the working directory is the code's own root and equals the packet's recorded one, and unless the interpreter's path and version equal the running ones (`native_shared_registration_orchestration.py:168–170`, `:236–238`, audit, from the Claude review of v10). So the checkout path is an identical field: every registration of the stratum is built in the reference's checkout, at its path, and the bytes it holds must not change. Moving the checkout or the interpreter makes every registration built after the move not equal, so no further registration can be made in this stratum until the move is undone; a move that cannot be undone is a pre-reservation defect under NP1.10(ar);
    - **the reference's source export and saved files.** At every later registration the gate validates the reference's packet with the production validators, run from the reference's own source bytes (below). Validating a runtime declaration reads its saved probe and request files again and pins the durable copy again, comparing its path, device and inode as well as its bytes (`native_u4b_runtime.py:288–302`). So the source export, the packet, its saved files and the copy itself stay unchanged, the copy at the same path, until the last production cell's acceptance record is signed. A copy replaced by an identical file is a different file to that check, and it cannot be put back: the registrations after it cannot validate, which is a pre-reservation defect under NP1.10(ar);
""")

R3 = block("""
  - **What runs** (the lead's rulings, Authority). The gate runs no attempt and no behavioural replay, and calls no model and no binary. The only code it runs is the existing production validators, read-only, in an isolated process, at the reference's checkout path and under the reference's interpreter, from source bytes it has first verified to equal the reference run's own source export. It never runs bytes that differ from the reference's pins, so the candidate's code is never executed where it differs from the reference's. The validators reconstruct the derived values deterministically, the rendered instruction and the command guidance among them (`native_shared_registration.py:95–97`, `:110–111`, `:256`, audit, from the Claude review of v10). That reconstruction is part of validation, not a replay. The comparison of fields then reads data only.
""")

R4 = block("""
    1. **Identical:** every value that can change what runs, what the model reads or how acceptance is decided. Among them: the pins of the package source and of every other pinned file, the prompt assets, the `.claude` command and agent files, the schema closure, the closed dependency registry, the Claude Code binary's sha256, the base system-instructions bytes, the checkout path, the interpreter's identity and path, the environment manifest, the profile, the selection bounds (NP1.10(ap)), the run limits and every other runtime value, the values the observation probe records about the model and its limits, and every scientific registered value. A value that decides what runs is identical even where it is written as a path, such as the executable search path.
    2. **Per-run:** a value that only names or locates this run, even where the model reads it, as the model reads the run's own label and absolute paths (D126). Among them: identifiers (registration, selection, job, attempt and session, and the receipt-policy registration's `registration_id`), labels, the run's project, timestamps and validity dates, and the device and inode numbers that fingerprints record. Among paths, only these are per-run: the per-attempt roots (attempt, evidence, output and stage) and the paths under them, and the per-attempt files (the registration, instruction and probe files). Every other path is identical, and the data file names each path field and its class. The project-input fields are per-run only as far as the rule on a project's inputs allows (below).
    3. **Derived:** a value that pinned code computes from the fields above. Among them: the embedded preparation and composition documents, the command line and the environment, the command guidance appended to the system prompt, the selection, preparation, composition, policy, instruction, probe and expectation hashes, and the byte counts recorded beside them. The gate recomputes each from the candidate's own content and requires it to validate. A derived value is never merely exempted, and a whole embedded document classed as derived never hides one of its leaves from the identical check (below).
  - **Every leaf is classified.** A machine-checkable inventory lists every leaf of every document the packet records, the documents embedded as JSON and the collections with variable keys included, and gives each its class. A leaf the schema does not classify is "cannot decide" (below). The data file names each field by its location in the registration packet that the merged source builds, and both reviewers check it against that source.
  - **A project's inputs** must equal that project's input tuple pinned at NP1b, exactly: the four input files a selection pins, each by sha256, which are the study's source manifest as one whole file and the project's bundle, chunk manifest and generation (omission) context (NP1.2). Their sha256s cover the project's scope declaration, which sits inside the context and the source manifest. The reference's tuple is CHORUS's. A change to a tuple needs a prospective amendment; until one is ratified, a registration with other inputs is not equal.
  - **The environment manifest** (the lead's rulings, Authority).
    - **The documents.** Per the lead's record, the registration's preparation and execution documents take successor kinds, version 3: `d4d_native_shared_preparation_v3` and `d4d_native_shared_execution_registration_v3`. The preparation carries one more required file pin, `environment_manifest`, to a closed, versioned document of kind `d4d_native_environment_manifest`, and the execution binds it through the preparation it embeds. Once version 3 is in the source, version 2 documents stay readable as historical evidence only, and no route accepts them for a new registration.
    - **What it records.** The interpreter's semantic identity: its implementation, version and build. And, sorted and unique, each third-party distribution the native interpreter can import, with its name, its version and the sha256 of its installed `RECORD` file. The project's own package is covered by the source pins and is not in it.
    - **What generating it checks.** It is regenerated at preparation and again at dispatch. Each time, every installed file that a distribution's `RECORD` lists with a hash is read and checked against that hash. Entries listed without a hash, such as the `RECORD` file itself and compiled `.pyc` files, are named in the manifest as unverified, by kind, with their count. A mismatch, a missing or unreadable file, missing, ambiguous or unreadable metadata, or an editable or development install of a third-party distribution holds: the registration is not prepared, or the launch does not proceed.
    - **At dispatch.** The regenerated manifest must equal the pinned one, or the launch holds. NP1b names, from the merged source, whether this check comes before the attempt's reservation. Before it, a hold spends no attempt. After it, the attempt stops and counts, as a capture that is fresh at the reservation but stale at dispatch does (N1.5).
    - **In the gate** it is an identical field, as the interpreter's identity and path are.
    - **Its deadline** is the CHORUS reference pilot's registration at the latest, and the canary's registration if NP1.10(as) is answered yes (NP1.7).
  - **The floor's change** is the one permitted change of an identical value, and it is checked separately.
    - **What the floor's registration document carries.** It is a receipt-policy registration: a JSON document with exactly seven fields (`native_shared_contract.py:785–813`, at the candidate): `kind`, `version`, `registration_id`, `condition`, `runtime_policy_sha256` (the policy asset's sha256), `receipt_instrument_version` (4) and `coverage_floor`. A pending floor is exactly `{state: pending, mode: diagnostic_pilot}`; a registered one is exactly `{state: registered, numerator, denominator, basis: receipted_part}`.
    - **The floor's registration** (NP1.7 step 6) is the reference's receipt-policy registration with `coverage_floor` replaced by the registered value and its basis. Its `registration_id` is a per-run field, as every identifier is, and it may be new. Every other field is the reference's.
    - **The check.** The gate requires that the production cell's floor value and basis are exactly those of the floor's ratified registration, computed by NP1.10(s)'s arithmetic, and that every other field of its receipt-policy registration, `registration_id` apart, is identical to the reference's. The hashes that carry it are derived values and are recomputed. What that one value does inside a run, where helper output shows "pending" in a pilot and "passed" in production, is the pinned code acting on that value. It is never compared, because no run is executed.
  - **The comparison-input manifest.** Before it compares anything, the gate writes an immutable manifest that names its inputs by path and sha256: the reference's registration packet and the candidate's, each as the registration builder wrote it, before any gate result or review is added; the floor's registration, where it applies; the project's input tuple; the gate's script and data file; and the reference's source export, by the digests the gate checked it against. The manifest's sha256 covers the manifest file's bytes. The gate's result names that sha256, and the result and the registration's two reviews go in an outer evidence packet that refers to these hashes. No hash covers a file that refers back to it.
  - **Three results, disjoint, and their precedence.**
    - **The shortcut.** A must-equal implementation or asset pin whose recorded sha256 differs from the reference's establishes a prohibited difference from the pins alone, before any validation of the candidate, but only where that pin is valid: both packets can be read that far, its record is well formed, the data file classes its location as a must-equal implementation or asset pin, and the reference's packet has passed the validators. A project-tuple substitution, a derived value and the floor's transition never take the shortcut: they are judged only after both packets pass the validators.
    - **Equal:** both packets pass the production validators, every leaf is classified, every identical field is byte-identical, every derived field validates, the inputs equal the project's tuple, and the floor's change, where present, checks.
    - **Not equal:** a prohibited difference is established on valid evidence: by the shortcut, or, after both packets pass the validators, an identical field that differs, a project-input field that does not match the tuple, a floor value or basis other than the floor's ratified registration, or bounds other than the stratum's. It is the result even where other evidence is invalid, missing or unclassified. The registration is not made under this amendment.
    - **Cannot decide:** no prohibited difference is established, and some evidence is invalid or incomplete: a packet fails the production validators, a pinned file is missing, a leaf is not classified, or a derived value cannot be recomputed. It is a hold: that registration is not made until the cause is resolved. It is never a pass and never a reason for another pilot.
    - **What the result lists:** every difference and every evidence problem the gate established, not only the first. Where the shortcut decided, it says that the candidate was not validated.
  - **A defect in the gate itself.** Before the reference exists, the data file and the script are corrected and reviewed again, and the demonstration below is repeated. After the reference run, a "cannot decide" or a wrong result whose cause is in the gate's own script or data file is a comparison defect under NP1.10(ar): both reviewers confirm it, and its repair changes the gate's bytes, so the stratum ends at the boundary that item fixes. The gate is never run again with an edited list inside this stratum.
  - **Demonstrated before the canary's registration, and again whenever the format changes.** Both reviewers review the data file against this section, and the gate is run on registration packets built by the registration builder: rehearsal packets with the real structure, whose synthetic values are marked as synthetic in their bytes. The inventory is part of the demonstration: it shows every leaf classified. The saved output shows each case's result and the fields it names:
    - **equal:** a packet against itself; against the same project's later registration; against another project's registration, rebuilt with fresh identities, paths and dates and with that project's tuple; a valid transition from a pending floor to a registered one; a reference whose registered validity has passed, since a registration is valid for two weeks (amendment N1's item (g)) and production may well take longer; and a reference whose attempt has consumed its reservation;
    - **not equal:** a changed prompt asset; a changed binary hash; a changed bound; a changed interpreter version; a changed version of a third-party distribution; a changed installed file of one; a wrong floor value; a wrong floor basis; an internally valid registration with another project's tuple; and two prohibited differences together, both listed;
    - **cannot decide:** a missing artifact; an unknown field; an incorrect derived binding; and invalid evidence;
    - **the mixed case:** a prohibited difference in a valid must-equal pin together with invalid evidence elsewhere gives "not equal", listing both.

    The results are recorded with the canary's registration. If the demonstration fails, the data file is corrected before the canary, not after any reference exists. **Whenever a change before the reference changes the registration format,** the version 3 documents among them, the demonstration is repeated on the new format before the first registration on it, and recorded with that registration.
  - **Run on the reference pilot's own packet, before each of its launch words.** Before the launch word of each registration of the CHORUS reference pilot, the gate is run as production will run it, with that registration's own packet as the reference, against: (1) itself; (2) a packet for another in-scope project, built offline by the same source with that project's tuple; and (3) a packet carrying a registered floor and its basis, built as the floor's registration will be built, its value marked synthetic, with that synthetic registration as the floor's input. Each must give "equal". A failure is a defect in the gate: the data file or the script is corrected, and this run and the demonstration are repeated, before that word. This is in addition to the demonstration above. The results go in that registration's outer evidence packet, and its reviews report them (NP1.10(aa)).
    - **Which gate later comparisons use.** Every comparison after the reference names the script and data file last run under this rule on the reference run's own registration.
    - **What it shows, and what it does not.** It runs the gate on the real format and runtime profile of the packet that becomes the reference, and on the floor's transition, which every production registration takes. The two packets built offline make no binary call. Where they cannot carry evidence that only a binary call makes, the run records which fields stand in for it and how they are classed, and both reviewers check that no identical field was exempted to make a case pass. So it shows the gate's classification on production's format; it does not show that a real registration for another project will validate.
  - **When it runs in production.** The gate is run on every registration made after the reference exists, and must say "equal", before that attempt's launch word is asked for. A registration that is not equal cannot be launched under this amendment, and a registration made after a boundary is not in this stratum whatever the gate says.
  - **What the reviewers do.** NP1.10(aa) (NP1.7). Each review of a registration made after the reference exists names the sha256s of the comparison-input manifest and of the gate's result. The coded word names the review bundle that carries both reviews (N1.9 item 4), so it binds the result it was given on.
""")

new_288 = L(288) + (
    " **What the canary shows changes no bound.** The values are fixed before the canary's registration,"
    " and every later registration keeps them (NP1.6). A bound found too small is corrected before the"
    " reference only by a ratified change to this amendment, under the bar, and after it only in a new"
    " stratum. A pilot stopped by a run-time bound is classed by NP1.6 like any other stop; where that is"
    " an impossible limit (row 5), the pilot concludes without acceptance, and for AI_READI that takes it"
    " out of scope (NP1.6).")

big = ([L(254), L(255), new_256, new_257, L(258)] + R1 + [L(264)] + R2 + [L(268), L(269)] + R3
       + [L(271)] + R4 + [L(287), new_288, L(289)])
replace(254, 289, "- **The reference run** [proposed, NP1.10(al)].", big)

replace(314, 314, "- **How the value is registered**", [L(314) +
        " The document it registers is the reference's receipt-policy registration with `coverage_floor` replaced (the gate, above)."])

# ---------------------------------------------------------------- NP1.6
replace(325, 325, "  - **An attempt** is one launch", [sub(
    325, "A capture is not an attempt, and a refusal before the reservation consumes none.",
    "A capture is not an attempt, and a refusal before the reservation consumes none: a hold by the gate, or by the environment manifest's check before the reservation, consumes none either.")])
replace(327, 327, "- **Classification** [proposed, NP1.10(x)]", [L(327) +
        " A defect that stops a registration before any reservation is not an attempt's stop and takes none of these classes: it is recorded as a pre-reservation defect (NP1.10(ar))."])

replace(368, 368, "  - **Registrations on a repaired source.**", block("""
  - **Registrations on a repaired source.** A refusal before the reservation spends no attempt. Amendment N1 says a capture that fails the margin "is refused before the attempt's reservation, so it doesn't spend the attempt" (N1.5), and of a limits mismatch "It refuses this registration before any reservation, so no attempt is consumed." (N1.2). So, before any reference exists, **any registration of the CHORUS reference pilot may be on a repaired source:** its first registration, for a defect found after NP1b; a registration made again after a refusal before the reservation; and its second attempt's, after a first attempt that consumed its reservation. Each change has its recorded reason under NP1.5's bar and keeps the stratum's selection bounds. Before such a registration, NP1b's checks, N1.4(A)'s offline software proofs and amendment N1's reservation-to-dispatch measurement (its item (ab)) are repeated on that source (NP1.7), and before its launch word the gate is run on its own packet (NP1.5). What the accepted attempt pinned is the reference. The AI_READI pilot's registrations, its first and second attempts and any registration made again after a refusal before the reservation, are made only where the gate finds them equal to the reference; a change to a field the gate holds identical is made only under NP1.10(ar) (NP1.5), and is never taken into the pilot.
"""))

# ---------------------------------------------------------------- NP1.7 prerequisites
for n, p in ((373, "  - **Before the canary's registration,**"), (374, "    - N1.9's list."),
             (375, "    - **#5939"), (376, "    - **#5966"), (377, "    - **#5967"),
             (379, "    - **The launch sequence"), (380, "    - **#6046"), (381, "    - **#6065"),
             (382, "    - **The two-set run-limits code**"), (383, "    - **The basis change**"),
             (384, "    - **The changed policy asset:**"), (385, "    - **The gate's script and data file**"),
             (386, "    - **The environment manifest**"), (387, "    - **The stratum's selection bounds**"),
             (388, "  - **Before NP1b,**"), (389, "    - **the recall adapter**")):
    assert L(n).startswith(p), (n, p)

prereq = ([sub(372, "through its entry stamped 04:24:02Z", "through its entry stamped 05:33:41Z"),
           L(373), L(374), L(375), L(376), L(377),
           sub(378, "an independent re-check closed #6016; on the published candidate.",
               "an independent re-check closed #6016; on the published candidate. A CI failure in its test, an import-origin isolation, is assigned."),
           L(379), L(380), L(381), L(382), L(383)]
          + block("""
    - **The changed policy asset:** the pending-floor sentence the owner chose (D142) and the sentence that names the at-receipt basis. The owner approved the asset and the pin registry's new hash together (D146); per the lead's record both are applied on the published candidate.
    - **The gate's script and data file** (NP1.5): the data file a closed field-level schema, reviewed by both reviewers against NP1.5 and demonstrated on rehearsal registration packets in the canary's registration format, with the results recorded with the canary's registration; the demonstration is repeated on each later format before the reference (NP1.5). Assigned, not written. The helper building it stopped twice for a design ruling, and the lead ruled on the validators, on the environment manifest and on three refinements from the Codex review of v10 (Authority). The earlier replay comparison is a development aid outside this amendment; an independent review found it unfit to be the gate (#6066 to #6073).
""")
          + [L(387), L(388), L(389)]
          + block("""
  - **Before the CHORUS reference pilot's registration at the latest,** and before the canary's registration if NP1.10(as) is answered yes:
    - **The environment manifest** (NP1.5): the version 3 preparation and execution documents with the `environment_manifest` pin, the manifest regenerated and checked at preparation and at dispatch, and version 2 refused for new registrations once version 3 is in. Per the lead's record, helper 3 has implemented the successor kinds in nine commits on a local branch (`a3a79c06f` to `9afd6d64a`), not yet reviewed or on the published candidate, and the three refinements of the lead's later ruling (Authority) are queued for the same helper.
""")
          + block("""
  - **Before each launch word of the CHORUS reference pilot:**
    - **the gate's run on that registration's own packet** (NP1.5).
- **The canary's registration format** [proposed, NP1.10(as)]. The version 3 documents change the kinds of two documents the canary's registration would carry. N1.1 ratified "execution authority v2" as one of the canary's protocol axes, whose binding bytes are "those of **the accepted U1+U3 merge commit on main**". The lead reads that axis as the authority's rules, which version 3 leaves unchanged apart from one required pin, and recommends that the canary carry version 3 (A), so that the shakedown exercises the format production uses. The alternative (B) keeps the canary on version 2, exactly as N1 ratified, and brings version 3 in before the CHORUS reference pilot's registration. The owner decides; NP1.10(as) quotes N1.1's text.
"""))
replace(372, 389, "- **Code that has to exist, each item with one deadline.**", prereq)

replace(403, 403, "   - names, as a conformance check on the merged source,", [sub(
    403, "the exact saved fields of the eligible record, of the pre-completion reading and of the acceptance record (NP1.4, NP1.6);",
    "the exact saved fields of the eligible record, of the pre-completion reading and of the acceptance record, and whether the environment manifest's check at dispatch comes before the reservation (NP1.4, NP1.5, NP1.6);")])

replace(407, 407, "   - records the sha256s of the gate's script and data file,", block("""
   - records the sha256s of the gate's script and data file as last demonstrated, and the stratum's selection bounds. Every comparison after the reference names the script and data file last run on the reference run's own registration before its launch word, which may correct those recorded here (NP1.5).
"""))

replace(412, 412, "4. **The CHORUS reference pilot** (NP1.6):", block("""
4. **The CHORUS reference pilot** (NP1.6): registered on the source NP1b checked, or on a repaired source under NP1.6 with the repeat above, under the production limit set, after the canary's acceptance. Before the launch word of each of its registrations, the gate is run on that registration's own packet (NP1.5). Run, and accepted or concluded under NP1.6. Its first accepted attempt is the reference run.
"""))

replace(424, 424, "- **Reviews** [proposed, NP1.10(aa)]:", block("""
- **Reviews** [proposed, NP1.10(aa)]: both reviewers review every registration, and each registration has its own two review documents. N1.9 item 4 builds one review bundle per registration, and its reader checks each review. **For a registration made after the reference exists,** each review confirms that the gate was run with its pinned script and data file, that its comparison-input manifest names the right two packets and inputs, and that the saved result is the one in the outer evidence packet; and it names the sha256s of the comparison-input manifest and of the result. The coded word names the review bundle (N1.9 item 4), so it binds them. **For a registration of the CHORUS reference pilot,** made before any reference exists, each review confirms NP1b's conformance on the source it registers, and the repeat where NP1.6's repair rule applies, the pins that will define the reference, and the gate's results on its own packet (NP1.5). Every review checks the recorded reasons NP1.5's bar requires. A reviewer does not judge a difference (NP1.5).
"""))

assert L(433).endswith("one more native run, with its own two reviews and word.")
replace(433, 433, "    - **What B means for the canary.**", [L(433) +
        " The canary runs the stratum's selection bounds, so it exercises them, but what it shows changes no bound (NP1.10(ap))."])

l445 = sub(445, "**What ends the stratum is NP1.10(al)'s rule, not this item's** (NP1.5)",
           "**What ends the stratum is set by NP1.10(al) and (ar), not by this item** (NP1.5)")
assert l445.count("is not in this stratum. It needs its own prospective amendment,") == 1
l445 = l445.replace("is not in this stratum. It needs its own prospective amendment,",
                    "is not in this stratum, and neither is one made after a boundary that (ar) fixes. A changed registration needs its own prospective amendment,")
replace(445, 445, "  - **What ends the stratum is NP1.10(al)'s rule", [l445])

# ---------------------------------------------------------------- NP1.9
replace(482, 482, "- the text of amendment N1, including N1.5's terms", block("""
- the text of amendment N1, including N1.5's terms for the canary and N1.4(B)'s rows. NP1.10(ab)'s answer, B (D143), changes none of N1's values. For readers of this amendment, two of N1's sentences are superseded (below);
"""))
replace(492, 492, "- **D109's clause**", block("""
- **D109's clause** "The measured value informs a registered native floor before any native replicate.", and the two sentences of amendment N1 that rest on it: N1.4(B) row 5's "The measured counters inform a registered native floor before any native replicate (D109).", and N1.5's premise for its item (ah), "This canary supplies the reading a native replicate floor is computed from.": superseded if NP1.10(s) is adopted. The canary's reading is reported and is not a floor input; the floor comes from the CHORUS reference run and the AI_READI pilot (NP1.5). N1's item (ah) stands as ratified;
"""))
replace(494, 494, "  - the prerequisites of NP1.7's list", block("""
  - the prerequisites of NP1.7's list "before the canary's registration", which N1.9's list does not name: #5939 (with #5994 and #5995), #5966 (with #6030 and #6031), #5967 (with #6015), the retention change (with #6016), the launch sequence #5989 to #5993 (with #6047, #6048 and #6074), the power check #6046, the short recorder line #6065, the two-set run-limits code, the basis change, the changed policy asset (D146), the gate's script and data file with their demonstration, and the stratum's selection bounds; and the environment manifest, if NP1.10(as) is answered yes;
"""))
insert_after(498, "  - the run limits (D143, B):", block("""
  - the registration format (NP1.10(as)): with a yes, the canary registers on the version 3 preparation and execution documents with the environment manifest, which the lead reads as within N1.1's "execution authority v2"; with a no, on version 2, as N1 ratified;
"""))

# ---------------------------------------------------------------- NP1.10
replace(502, 502, "Each letter is one decision,", block("""
Each letter is one decision, and a "yes" adopts exactly the value given. The cells themselves are D135's scope and are not a lettered item. "Amendment N1's item" always means a letter of N1, never one of these. A note after an item says how it differs from v10; an item with no note is unchanged from v10. The letters are v10's, with one added at the end: (as) is new; (aj) stays retired; (aa), (ak), (al), (ap), (aq), (ar), (c), (s) and (z) are changed.
"""))
replace(513, 513, "- **Nine items carry a complete written alternative:**", block("""
- **Ten items carry a complete written alternative:** (e), (g), (h), (j), (n), (o), (r), (ab), (an) and (as). Three of them are answered: (n), (r) and (ab). For the others a "no" adopts the alternative as written, and nothing is redrafted. (an)'s is fixed: the owner starts those sequences. (as)'s is B: the canary runs version 2, as N1 ratified.
"""))
replace(514, 514, "- **No \"no\" prescribes new engineering.**", block("""
- **No "no" prescribes new engineering.** (ab) and (as) are the items whose written alternatives differ in code, and each alternative is written out (NP1.7). Both of (as)'s alternatives need the same version 3 documents, at different deadlines.
"""))
replace(523, 523, "| (i), (p), (q), (ar) | the first production registration |", block("""
| (i), (p), (q) | the first production registration |
| (ar) | every registration after the reference run: the AI_READI pilot's and every production registration |
"""))
replace(533, 533, "- **(c)** Kids First", block("""
- **(c)** Kids First is not planned under this amendment. It has no native cell here and is labelled "not planned (NP1)", which is not missing. Its inputs sit under their own manifest with the neutral profile, the plan's `vocabulary: {}` cannot be written in a native registration, and it is the largest input and unpriced. A later addendum can add it once its inputs test is specified, and only as its own stratum, never compared with this one or pooled into it: its profile differs from the study's, and the profile is a field the gate holds identical. A no returns this item for redrafting (NP1.2). *Changed: only as its own stratum.*
"""))
l555 = sub(555,
           "**The canary's reading is reported and is never an input; this supersedes D109's clause \"The measured value informs a registered native floor before any native replicate.\"**",
           "**The canary's reading is reported and is never an input; this supersedes D109's clause \"The measured value informs a registered native floor before any native replicate.\", and, for this amendment, the two sentences of amendment N1 that rest on it (NP1.5).**")
replace(555, 555, "- **(s)** The floor rule", [l555 + " *Changed: N1's two sentences named.*"])

replace(566, 566, "- **(z)** The staged procedure", block("""
- **(z)** The staged procedure: no pilot or production registration under this amendment before the canary's acceptance record is signed; B6's reading of every canary attempt that kept a record before NP1b; then the measured-usage packet, then NP1b, then the CHORUS reference pilot, then the AI_READI pilot, then the floor's registration in its own amendment, each reviewed and ratified before the registrations that depend on it. NP1b applies rules, changes none, takes no number from the owner and does not register the floor; computing the floor by (s) is an application. NP1b pins each in-scope project's input tuple of four pins, and confirms on the reference pilot's source N1.4(A)'s offline software proofs and amendment N1's reservation-to-dispatch measurement, or repeats them. Any registration of the CHORUS reference pilot made before the reference exists may be on a repaired source (NP1.6); NP1b's checks, those proofs and that measurement are repeated on it first. NP1b records the gate's script and data file as last demonstrated; the comparisons after the reference name those last run on the reference run's own registration (NP1.5, NP1.6, NP1.7). *Changed: a repaired source for any registration of the reference pilot before the reference exists; which gate later comparisons name.*
"""))
replace(567, 567, "- **(aa)** Reviews", block("""
- **(aa)** Reviews: both reviewers review every registration, each registration with its own two review documents. For a registration made after the reference exists, each review confirms that the gate was run with its pinned script and data file on the right comparison-input manifest, and names the sha256s of that manifest and of the result, so that the coded word, which names the review bundle, binds them. For the CHORUS reference pilot, each confirms NP1b's conformance on its source, the pins that will define the reference, and the gate's results on its own packet. Every review checks the recorded reasons the bar requires; a reviewer does not judge a difference (NP1.7). *Changed: the word binds the gate's result; the reference pilot's own gate results.*
"""))
replace(570, 570, "- **(ad)** One procedure", [sub(570, " *Changed: the frozen-code rule is (al)'s only.*", "")])
replace(583, 583, "- **(ak)** What a \"no\" means", block("""
- **(ak)** What a "no" means: it returns the item for redrafting, except for the ten items that carry a written alternative; every redraft is ratified before the canary's first coded word, as amendment N1's item (ah) requires, so such a "no" holds the canary too, and the table's holds apply in addition; production registrations wait for every unresolved analysis-defining item (NP1.10). *Changed: ten items carry a written alternative, (as) among them.*
"""))
replace(586, 586, "- **(al)** The reference run and the gate.", block("""
- **(al)** The reference run and the gate. The production stratum's reference is the first accepted attempt of the CHORUS reference pilot: one CHORUS pilot registered after NP1b and after the canary's acceptance, under the production limit set, with the floor pending. The AI_READI pilot's registrations and every production registration are equal to it by NP1.5's gate, or they are not in this stratum; one made after a boundary that (ar) fixes is not in it either. The gate runs no attempt and no replay and calls no model or binary: it validates both packets with the production validators, read-only and isolated, at the reference's checkout path and under its interpreter, from bytes verified to equal the reference's source export and never from bytes that differ from its pins; their deterministic reconstruction of derived values is part of validation; then it compares data. Its data file is a closed field-level schema: a value that can change what runs, what the model reads or how acceptance is decided is identical, the checkout path, the interpreter's identity and path and the environment manifest among them; a value that only names or locates the run is per-run even where the model reads it, and among paths only the per-attempt roots (attempt, evidence, output and stage), the paths under them and the per-attempt files (registration, instruction and probe) are; a value derived from those is recomputed and must validate; a machine-checkable inventory classifies every leaf of every recorded document. A project's inputs must equal its tuple of four pins, fixed at NP1b. The floor's change from pending to registered is checked separately against the floor's registration, which is the reference's receipt-policy registration with `coverage_floor` replaced. The environment manifest: version 3 preparation and execution documents with one required `environment_manifest` pin; the interpreter's identity and each third-party distribution's name, version and `RECORD` hash, with every hashed installed file verified at preparation and at dispatch; a mismatch, a missing or unreadable file or an editable install holds; version 2 refused for new registrations once version 3 is in. A differing pin decides "not equal" before validation only where it is a valid must-equal implementation or asset pin; a prohibited difference established on valid evidence gives "not equal" even where other evidence is invalid, the result listing every difference and evidence problem established; otherwise invalid or unclassified evidence gives "cannot decide", a hold. Before each comparison the gate hashes an immutable comparison-input manifest, which names the reference's source export; its result and the reviews go in an outer evidence packet. The data file is demonstrated on every listed case before the canary's registration and again whenever the format changes before the reference; and before each launch word of the CHORUS reference pilot the gate is run on that registration's own packet against itself, another project's packet and a packet carrying a registered floor, each giving "equal". No pilot is run again. After the reference run, a registration that differs in any identical field, other than the floor's change, is not in this stratum; production depends on the host state NP1.5 names, and restoring that state is not a repair (NP1.5, NP1.6, NP1.7). *Changed: the shortcut and its precedence; the checkout and interpreter paths identical; the validators' reconstruction; the environment manifest's approved contract; the floor's registration document; the four input pins; every demonstration case and the inventory; the gate run on the reference pilot's own packet; restoration of host state.*
"""))
replace(591, 591, "- **(ao)** No change may rest", [sub(591, " *Changed: after the reference run the bar acts through (ar).*", "")])
replace(594, 594, "- **(ap)** The selection bounds", block("""
- **(ap)** The selection bounds: one set of values for every registration of the stratum and for the canary, chosen before the canary's registration from the largest input the study's source manifest declares, with a stated margin, inside the contract's ceilings, and derived bound by bound; the gate compares them byte for byte. What the canary shows changes no bound: a bound found too small is corrected before the reference only by a ratified change to this amendment, under the bar, and after it only in a new stratum. This is the lead's decision of 2026-11-13, put to the owner (NP1.5). *Changed: the canary changes no bound.*
"""))
replace(595, 595, "- **(aq)** The prerequisites", block("""
- **(aq)** The prerequisites: NP1.7's list, each item with its one deadline: before the canary's registration; before NP1b; before the CHORUS reference pilot's registration at the latest, for the environment manifest, which is due before the canary's registration if (as) is answered yes; or before each launch word of the CHORUS reference pilot, for the gate's run on that registration's own packet. The list and its deadlines are the lead's (NP1.7). *Changed: the environment manifest's deadline, and the gate's run on the reference pilot's own packet.*
"""))
replace(596, 596, "- **(ar)** Repairs during production", block("""
- **(ar)** Repairs during production: after the reference run, a change to anything the gate holds identical is made only for a qualifying defect. That is a filed defect that stopped an attempt's acceptance, classed instrument, registration or environment, record shape or transport, or an unknown stop once reclassified into one of these; or a preparation, registration or comparison defect, confirmed by both reviewers, that prevents an otherwise eligible registration before any reservation, recorded as a pre-reservation defect and spending no attempt. The boundary is fixed when the defect is filed, before the next registration: both reviewers record whether its repair needs changed must-equal bytes. If it does, no further registration is made from that moment, and the stratum ends for every registration made after the boundary; if it does not, the stratum continues, and that defect cannot later end it. Restoring host state to the reference's bytes and paths is not a repair. This stratum's results stand under the plan's kinds of missing; a later stratum is reported separately, never pooled with this one and never put in its place, and it is exploratory unless it begins at a boundary this item fixes and every change it carries has the recorded reason the bar requires. A change for any other reason is not made during production (NP1.5). *Changed: defects before any reservation; the boundary fixed at filing; one scope; one test for an exploratory stratum; restoration of host state.*

**The canary's registration format**
- **(as)** Whether the canary registers on the version 3 preparation and execution documents, with the environment manifest. Amendment N1.1 lists "execution authority v2;" among its "Protocol axes, kept separate:", and continues: "The first four exist today on native branches only. Their binding bytes are those of **the accepted U1+U3 merge commit on main** (the readiness plan's gate G0), which the registration names." The lead approved the version 3 documents as "within N1.9 item 4 as the review bundle's version 3 was" (Authority); N1.9 item 4 says "The v2 review reader is replaced or extended to accept it." **A yes adopts A, the lead's recommendation:** the canary carries version 3. The lead reads N1.1's axis as the authority's rules, which version 3 leaves unchanged apart from one required pin; that is the lead's reading, not an owner decision. The shakedown then exercises the registration format production uses, and the canary's registration waits until the version 3 documents are reviewed and in the source it registers. **A no adopts B:** the canary runs version 2 exactly as N1 ratified, and version 3 enters before the CHORUS reference pilot's registration. The demonstration is then repeated on version 3, and the reference pilot's attempts are the first real registrations in that format: a defect of the format found before the reference exists is repaired under NP1.6, and one found after it is a defect under (ar) (NP1.5, NP1.7). *New.*
"""))

# ---------------------------------------------------------------- apply
ops.sort(key=lambda o: o[0], reverse=True)
covered = []
for start, end, _ in ops:
    for s, e in covered:
        assert end < s or start > e or (end < start), ("overlap", start, end, s, e)
    if end >= start:
        covered.append((start, end))
out = list(V)
for start, end, new_lines in ops:
    if end < start:  # insertion before line `start`
        out[start - 1:start - 1] = new_lines
    else:
        out[start - 1:end] = new_lines
result = "\n".join(out) + "\n"

# ---------------------------------------------------------------- post-checks
problems = []
if "@" in result:
    problems.append("at-sign present")
# The response table quotes the v10 findings, so stale phrases are looked for outside it.
_head, _rest = result.split("## Responses to the reviews of v10", 1)
body = _head + _rest.split("## Authority", 1)[1]
for gone in ("for the registrations that carry it", "ends this stratum for the registrations made after it",
             "N1.5 requires that record", "Nine items carry", "nine items that carry",
             "There are 44 letters", "(a) to (ar).", "v10 has not been reviewed",
             "goes back to the owner as a number", "nothing is applied (D142)",
             "goes to the owner with the changed pin's hash", "leaves no route from a quality reading",
             "omission context and scope declaration, each by sha256", "the interpreter's version",
             "and the checkout and interpreter paths", "so moving the checkout does not by itself end the stratum",
             "entry stamped 04:24:02Z", "What the code does today"):
    if gone in body:
        problems.append("leftover: " + gone)
if result.count("never from the candidate's tree") > 1:
    problems.append("candidate's-tree wording outside the quoted ruling")
if re.search(r"\b(he|she|his|him|hers)\b", result, flags=re.I):
    problems.append("gendered pronoun")
if result.count("$") != text.count("$"):
    problems.append("dollar figures changed: %d -> %d" % (text.count("$"), result.count("$")))
sec = result.split("## NP1.10 ")[1]
letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s",
           "t", "u", "v", "w", "x", "y", "z"] + ["a" + c for c in "abcdefghijklmnopqrs"]
for x in letters:
    k = sec.count("- **(%s)**" % x)
    if k != 1:
        problems.append("item (%s) appears %d times" % (x, k))
if sec.count("- **(") != 45:
    problems.append("item count %d" % sec.count("- **("))
table = result.split("## Responses to the reviews of v10")[1].split("## Authority")[0]
for n in range(6112, 6130):
    if table.count("#%d " % n) + table.count("#%d|" % n) != 1:
        problems.append("issue #%d in table %d times" % (n, table.count("#%d" % n)))
if problems:
    print("POST-CHECK FAILURES:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

target = W / REL
target.write_text(result, encoding="utf-8")
data = target.read_bytes()
print("wrote", target)
print("sha256", hashlib.sha256(data).hexdigest())
print("lines", data.count(b"\n"), "bytes", len(data))
