#!/usr/bin/env python3
"""Purpose: build draft v9 of analysis plan amendment NP1 (native production
cells) from draft v8 by named, exact replacements, so that the change from v8
to v9 is reproducible and reviewable.

Inputs: the v8 file at commit 756c92b317bbcb3545526c2ea9c6d18bb0cab73d of the
worktree given as argument 1 (read with `git show`, its sha256 asserted).
Outputs: the v9 text written over notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md
in that worktree. Every replacement asserts that its anchor occurs exactly once.
Serves: owner direction D134, D135; the lead's rulings of 2026-11-13 for v9
(the gate as a comparison of pins; run limits B; one deadline per prerequisite);
issues #6075 to #6092 (the two reviews of v8). Date: 2026-11-13.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

V8_COMMIT = "756c92b317bbcb3545526c2ea9c6d18bb0cab73d"
V8_SHA = "be640a7e733bd63f9fe350ee657bf65c8cdf9a013f0227d5582e59b2e00f386a"
REL = "notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md"


def once(text, old, new):
    n = text.count(old)
    if n != 1:
        sys.exit(f"anchor occurs {n} times: {old[:90]!r}")
    return text.replace(old, new)


def block(text, start, end, new):
    i, j = text.count(start), text.count(end)
    if i != 1 or j != 1:
        sys.exit(f"block markers occur {i}/{j} times: {start[:70]!r} / {end[:70]!r}")
    a, b = text.index(start), text.index(end)
    if not a < b:
        sys.exit(f"block start after end: {start[:70]!r}")
    return text[:a] + new + text[b:]


def main(worktree):
    raw = subprocess.run(["git", "-C", worktree, "show", f"{V8_COMMIT}:{REL}"],
                         capture_output=True, check=True).stdout
    if hashlib.sha256(raw).hexdigest() != V8_SHA:
        sys.exit("v8 bytes differ from the expected sha256")
    t = raw.decode("utf-8")

    # ---- Header ----
    t = block(t, "**Status: draft v8, written by claude (lead) on 2026-11-13.**", "- **It is not binding until:**", HEADER)
    t = once(t, "N1's item (ah) is therefore binding: this amendment is ratified before the canary's word is given. NP1.5 makes that same event the condition for the canary's reading to count, and says what holds otherwise;",
             "N1's item (ah) is therefore binding: this amendment is ratified before the canary's word is given (NP1.5);")
    t = once(t, "NP1.5 says how those values bear on the choice of basis;",
             "the basis was put to the owner with them in view, and is answered (D140);")
    t = once(t, "  - no value from any native run under this condition.",
             "  - the independent review of the replay comparison script (#6066 to #6073), which concerns code and no native outcome;\n  - no value from any native run under this condition.")
    t = once(t, "For v8 the lead also read the profile's vocabulary rule there (NP1.2) and, at commit `6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834` of the same branch, a published draft that carries the four protected files the owner approved (D139), the lines that put the runtime declaration into the instruction (NP1.5).",
             "For v8 the lead also read the profile's vocabulary rule there (NP1.2). At commit `6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834` of the same branch, a published draft that carries the four protected files the owner approved (D139), the lead read the lines that put the runtime declaration into the instruction, for v8 and again for v9, and the selection bounds' ceilings and input check at the cited commit (NP1.5).")

    # ---- Responses ----
    t = block(t, "## Responses to the reviews of v7", "## Authority", RESPONSES)

    # ---- Authority ----
    t = once(t, "**After D143** the lead recommended changing its answer from B to A (NP1.7); the owner had not answered when this draft was written.",
             AFTER_D143)
    t = once(t, "- **Open in the plan and touched here:**", LEAD_DECISIONS + "- **Open in the plan and touched here:**")

    # ---- NP1.1 ----
    t = once(t, "| CHORUS | The N1 canary: n=1, descriptive, never a replicate. [proposed, NP1.10(al)] Where the canary cannot be the reference run, one CHORUS reference pilot: n=1, not a replicate. Then 3 production cells |",
             "| CHORUS | The N1 canary: n=1, descriptive, never a replicate; its reading is reported and is not a floor input. [proposed, NP1.10(al)] One CHORUS reference pilot under the production limit set: n=1, not a replicate, the stratum's reference. Then 3 production cells |")

    # ---- NP1.2 ----
    t = once(t, "with selection bounds set by the reference's rule (NP1.5) and the production limit set (NP1.7).",
             "with the selection bounds that the stratum's pinned selection-bounds rule gives for it (NP1.5) and the production limit set (NP1.7).")
    t = once(t, "NP1b runs the test on the reference run's source where that run has been accepted, and otherwise on the merged source on which the CHORUS reference pilot registers (NP1.7).",
             "NP1b runs the test on the exact source on which the CHORUS reference pilot registers, and the test is repeated there if that pilot's second attempt registers on a changed source (NP1.7).")
    t = once(t, "It applies no size limit below the source's own ceilings, and it does not test",
             "It applies no size limit of its own: the bounds come from the pinned rule, inside the source's own ceilings (NP1.5). It does not test")

    # ---- NP1.3 ----
    t = once(t, "in the document that registers the floor's value (NP1.7 step 6): in NP1b when no pilot is pending, otherwise in the floor's own amendment, after every pending pilot has concluded.",
             "in the document that registers the floor's value (NP1.7 step 6), which is the floor's own amendment, after every pending pilot has concluded.")

    # ---- NP1.4 ----
    t = once(t, "**The retention change** [answered: keep, NP1.10(n); D141]: **an engineering prerequisite of any pilot.**",
             "**The retention change** [answered: keep, NP1.10(n); D141]: **an engineering prerequisite, before the canary's registration** (NP1.7). That deadline is the lead's: D141 sets none beyond the repair of #6016.")

    # ---- NP1.5 ----
    t = once(t, "- **What D109 requires:** the canary's floor stays pending and its reading is reported; \"The measured value informs a registered native floor before any native replicate. No API threshold is copied\".",
             D109_BLOCK)
    t = once(t, "The stage-request hashes on both sides are retained, so the difference is shown and not inferred.",
             "The stage-request hashes on both sides are retained, so the difference is shown and not inferred. The gate validates it as the one permitted change of a registered value (below).")
    t = block(t, "- **When the rule is fixed.**", "- **No change may rest on a native result**", WHEN_FIXED)
    t = block(t, "- **No change may rest on a native result**", "- **The reference run**", BAR)
    t = block(t, "- **The reference run**", "- **The rule** [proposed, NP1.10(s)].", REFERENCE_AND_GATE)
    t = once(t, "  - **Eligible pilots:** the CHORUS reference run and, if NP1.10(e) is yes and AI_READI is in scope, the AI_READI native pilot. **The CHORUS reference run** is the N1 canary under one limit set where NP1.10(aj)'s condition held, and otherwise the first accepted attempt of the CHORUS reference pilot (above). Where the canary is not the reference, its reading is reported and is never an input.",
             "  - **Eligible pilots:** the reference run, which is the first accepted attempt of the CHORUS reference pilot (above), and, if NP1.10(e) is yes and AI_READI is in scope, the AI_READI native pilot. **The canary's reading is reported and is never an input;** that supersedes D109's clause quoted above.")
    t = once(t, "Its project stays in scope. A prospective amendment, reviewed as this one, says how the floor is set;",
             "Its project stays in scope. A prospective amendment, reviewed as this one, says how the floor is set; it is under the bar, which says what it may apply (above);")
    t = once(t, "    - **there is no reference run,** because the canary cannot be it and the CHORUS reference pilot concluded without acceptance (NP1.6): a prospective amendment says how the condition proceeds;",
             "    - **there is no reference run,** because the CHORUS reference pilot concluded without acceptance (NP1.6): a prospective amendment says how the condition proceeds;")
    t = once(t, "    - **the comparison's result for a pilot's registration is \"cannot decide\":** that registration waits, and so does the floor.",
             "    - **the gate's result for the AI_READI pilot's registration is \"cannot decide\":** that registration waits, and so does the floor;\n    - **the reference run's source no longer saves the fields this rule reads:** the floor waits for a prospective amendment that restates them (below).")

    # ---- NP1.6 ----
    t = once(t, "The pilots are the canary, the AI_READI pilot (NP1.10(e)) and, only where the canary cannot be the reference run, the CHORUS reference pilot (NP1.10(al)).",
             "The pilots are the canary, the CHORUS reference pilot (NP1.10(al)) and the AI_READI pilot (NP1.10(e)).")
    t = once(t, "and a further native CHORUS pilot needs a prospective amendment. **The CHORUS reference pilot:**",
             "and a further native CHORUS pilot needs a prospective amendment. That stops the CHORUS reference pilot too, which registers only after the canary is accepted: the canary is this amendment's feasibility gate (NP1.7 step 1). **The CHORUS reference pilot:**")
    t = block(t, "  - **The CHORUS reference pilot** [proposed, NP1.10(al)] exists only", "- **Missing cells** follow plan", REFERENCE_PILOT)

    # ---- NP1.7 ----
    t = block(t, "- **Before any pilot: code that has to exist.**", "1. **The canary is accepted under N1**", PREREQUISITES)
    t = once(t, "If the canary is rejected at rule level, or concludes without acceptance, NP1.6's table says what follows.",
             "If the canary is rejected at rule level, or concludes without acceptance, NP1.6's table says what follows; in either case the CHORUS reference pilot does not register.")
    t = once(t, "   - applies NP1.2's inputs test to every project on the study's source manifest, with its commands and saved outputs;",
             "   - applies NP1.2's inputs test to every project on the study's source manifest, with the pinned selection-bounds rule, its commands and saved outputs;")
    t = block(t, "   - confirms from that source which registered limit set or sets it accepts", "   It may change which whole projects are in scope", NP1B_BULLETS)
    t = once(t, "**Computing the floor's value by NP1.5's fixed rule is not such a choice:** it applies the rule to the accepted pilots' coverage readings, as the plan's A15 does (lines 1159–1162). **Every later change is under NP1.5's bar** (NP1.10(ao)).",
             NP1B_TAIL)
    t = block(t, "4. **The CHORUS reference pilot,** only where the canary cannot be the reference run", "- **Words and registrations.**", STEPS_4_TO_7)
    t = once(t, "Each review confirms that the comparison was run with the pinned script and data file on the right inputs; a reviewer does not judge a difference (NP1.5).",
             "Each review confirms that the gate was run with the pinned script and data file on the right two packets, and checks the recorded reasons NP1.5's bar requires; a reviewer does not judge a difference (NP1.5).")
    t = block(t, "- **Runtime terms** [answered: B, NP1.10(ab); D143]:", "  - **C (offered, not taken):**", RUNTIME_TERMS)
    t = once(t, "  - **Under A or B the production set is fixed before any native cost is measured.**",
             "  - **The production set is fixed before any native cost is measured.**")
    t = block(t, "  - **The count.**", "  - **What each attempt asks.**", COUNT)
    t = block(t, "- **One procedure** [proposed, NP1.10(ad)]:", "## NP1.8 The API arm under D134", ONE_PROCEDURE)

    # ---- NP1.8 ----
    t = once(t, "- **The API arm's own open items** are recorded in draft v7's NP1.8 and decided elsewhere: the classification of the A21 run of 2026-11-11 (#5874), the comparison registration's schema release, the provider account's budget, and the order of the rebuild under amendment N1's item (y).",
             API_OPEN_ITEMS)

    # ---- NP1.9 ----
    t = once(t, "- the text of amendment N1, including N1.5's terms for the canary and N1.4(B)'s rows. NP1.10(ab)'s recorded answer is B (D143), which changes none of N1's values; under A two of them would change, by a revision of amendment N1 and not by this amendment;",
             "- the text of amendment N1, including N1.5's terms for the canary and N1.4(B)'s rows. NP1.10(ab)'s answer, B (D143), changes none of N1's values;")
    t = once(t, "- D22, D25, D109's pending floor for the canary, and D113;",
             "- D22, D25, D113, and D109's pending floor for the canary, its diagnostic reporting and the canary's status as no replicate;")
    t = once(t, "- the API arm's scope rule, superseded by a fixed CHORUS-only set if NP1.10(af) is adopted (NP1.8);",
             "- the API arm's scope rule, superseded by a fixed CHORUS-only set if NP1.10(af) is adopted (NP1.8);\n- **D109's clause** \"The measured value informs a registered native floor before any native replicate.\": superseded if NP1.10(s) is adopted. The canary's reading is reported and is not a floor input; the floor comes from the CHORUS reference run and the AI_READI pilot (NP1.5);")
    t = block(t, "  - the repairs of #5939 (with #5994 and #5995),", "## NP1.10 Ratification", CANARY_CHANGES)

    # ---- NP1.10 ----
    head, sep, tail = t.partition("## NP1.10 Ratification")
    tail = re.sub(r" \*(Changed|Rewritten|Reworded|New)[^*\n]*\*(?=\n)", "", tail)
    t = head + sep + tail
    t = once(t, "A note after an item says how it differs from v7; an item with no note is unchanged from v7. The letters are v7's: none is retired, (c) and (al) are rewritten, and (an) and (ao) are new.",
             "A note after an item says how it differs from v8; an item with no note is unchanged from v8. The letters are v8's: (aj) is retired; (ad), (al), (ao), (s) and (z) are rewritten; (aa), (ab), (ak), (n) and (r) are changed.")
    t = block(t, "**Answered in advance.**", "**Ratification mechanics for (ak).**", ANSWERED)
    t = once(t, "- **Ten items carry a complete written alternative:** (e), (g), (h), (j), (n), (o), (r), (ab), (aj) and (an). Three of them are answered: (n), (r) and (ab). For the others a \"no\" adopts the alternative as written, and nothing is redrafted. (aj)'s is fixed: the canary's reading is not a floor input, the canary is not the reference run, and the CHORUS reference pilot is run. (an)'s is fixed too: the owner starts those sequences.",
             "- **Nine items carry a complete written alternative:** (e), (g), (h), (j), (n), (o), (r), (ab) and (an). Three of them are answered: (n), (r) and (ab). For the others a \"no\" adopts the alternative as written, and nothing is redrafted. (an)'s is fixed: the owner starts those sequences.")
    t = once(t, "- **A redraft changes this file.** For the canary to meet (aj)'s condition, the redraft is ratified before the canary's first coded word (NP1.5).",
             "- **A redraft changes this file,** and it is ratified before the first registration it governs (above).")
    t = block(t, "- **(n)**", "- **(o)**", ITEM_N)
    t = block(t, "- **(r)**", "- **(s)**", ITEM_R)
    t = block(t, "- **(s)**", "- **(t)**", ITEM_S)
    t = block(t, "- **(z)**", "- **(aa)**", ITEM_Z)
    t = block(t, "- **(aa)**", "- **(ab)**", ITEM_AA)
    t = block(t, "- **(ab)**", "- **(ac)**", ITEM_AB)
    t = block(t, "- **(ad)**", "- **(ae)**", ITEM_AD)
    t = block(t, "**Timing**\n", "**Convention**\n", RETIRED_AJ)
    t = once(t, "except for the ten items that carry a written alternative;",
             "except for the nine items that carry a written alternative;")
    t = block(t, "- **(ak)** What a \"no\" means:", "**Reference and starts**", ITEM_AK)
    t = block(t, "- **(al)**", "- **(am)**", ITEM_AL)
    if t.count("- **(ao)**") != 1:
        sys.exit("(ao) marker is not unique")
    t = t[:t.index("- **(ao)**")] + ITEM_AO  # (ao) is the file's last item

    Path(worktree, REL).write_text(t, encoding="utf-8")
    print(hashlib.sha256(t.encode("utf-8")).hexdigest(), len(t.splitlines()), "lines")


HEADER = r"""**Status: draft v9, written by claude (lead) on 2026-11-13.**
- **Earlier drafts.** v1 to v7, with their commits, hashes, reviews and issues (#5914 to #5925, #5940 to #5964, #5969 to #5988, #5996 to #6014, #6017 to #6029, #6032 to #6045, #6050 to #6064), are listed in the headers of v4 to v8. Each draft answered every finding of the one before; its response table is in its own commit. Review files are kept outside the repository and are cited by sha256.
- **v8** (commit `756c92b317bbcb3545526c2ea9c6d18bb0cab73d`, file sha256 `be640a7e733bd63f9fe350ee657bf65c8cdf9a013f0227d5582e59b2e00f386a`) was reviewed twice, and both reviews said "ratifiable after listed fixes": a Codex CLI pass (review sha256 `e435d804b1ee099cfb1e39725d29d801d20d87e624552cab2fc1ea320b6a39d8`; 2 P1, 7 P2, 2 P3) and a Claude reviewer, a fresh session run on another model (review sha256 `a55bdc8599375e8b962b76725244ac9c593af5366701ba044616575955209731`; 2 P1, 5 P2, 6 P3). The 24 findings are filed as 18 issues, #6075 to #6092; six of the Codex findings are appended to the Claude issue on the same point.
- **Two read-only source audits** of commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e` are cited below: a Codex CLI audit of the receipt floor (sha256 `4a6a95f65ca3cf96c1cc56b6c624b693fc432559d7cf3711c3076c7370abb35b`) and a Codex helper's audit of native eligibility (sha256 `4b42694ab342dbdcf2d9f0db0faf3bffe5a015bf87968cb669aee19d25b0c3db`).
- **v8 → v9 replaces the comparison and settles the run limits.** Both reviews of v8 found that its comparison could not admit the registrations the plan needs: a production cell's floor and a larger project's selection bounds reach what the model reads, and a replay on CHORUS's inputs cannot see code that only other projects reach. An independent review of the replay script itself found that it never reads the actual registrations (#6066 to #6073). v9:
  - makes the stratum's gate a comparison of the registrations' pins. Nothing is executed, every pinned file and registered value is compared byte for byte, and only a fixed list of per-run fields may differ. The floor's change from pending to registered is validated separately (NP1.5);
  - pins a selection-bounds rule before NP1b; each registration's bounds are validated by recomputing them under it (NP1.2, NP1.5);
  - records that the lead withdrew its recommendation of alternative A: D143's answer, B, stands. The canary is never the reference run, its reading is reported and is not a floor input, and one CHORUS reference pilot always runs. That supersedes one clause of D109, and v9 says so (NP1.5, NP1.6, NP1.7);
  - retires (aj), which decides nothing once the canary is never a floor input or the reference run (NP1.5);
  - gives every prerequisite one deadline, the power check and the short recorder line before the canary's registration (NP1.7);
  - requires a recorded reason for every change while the bar on native results is in force, and says what the bar does not forbid (NP1.5);
  - repeats NP1b's checks if the CHORUS reference pilot's second attempt registers on a changed source (NP1.7);
  - restores in its own text the API arm's open items, the budget requirement among them (NP1.8).

  There are 41 letters, (a) to (ao). (aj) is retired; the other 40 are the items of the ballot.
- **v9 has not been reviewed.**
"""

RESPONSES = r"""## Responses to the reviews of v8
Each issue stays open until a re-check of v9 confirms the answer. "Claude" and "Codex" name the two v8 reviews; both used the keys P1-1, P2-1 and so on, so each key is given with its review. The responses to the reviews of v7 are in v8's own commit.

| v8 finding | Issue | Answer in v9 | Where |
|---|---|---|---|
| Claude P1-1, with Codex P1-2: the selection bounds are pinned both as a rule and as values; one CHORUS replay cannot show what other projects' inputs reach | #6075 | The gate is a comparison of pins and executes nothing, so no replay limits what it sees. A selection-bounds rule is pinned before NP1b; each registration's bounds are validated by recomputing them under the rule, not compared with the reference's. The project-input fields are named | NP1.5, NP1.7, (al) |
| Claude P1-2, with Codex P1-1: the floor's change reaches what the model reads | #6076 | The floor's change from pending to registered is the one permitted change of a registered value, validated separately against NP1.10(s)'s arithmetic. What it does inside a run is not compared, because nothing is executed | NP1.5, (al) |
| Claude P2-1: the comparison is pinned without review, its rule list is incomplete, and a defect in it has no route | #6077 | The gate's script and data file are reviewed against NP1.5 before NP1b, with findings filed and closed. The gate compares every pinned file, so no list of rule-bearing objects is needed. A "cannot decide" caused by the gate itself is resolved only by a ratified prospective change. Writing or changing them is under the bar | NP1.5, NP1.7, (al), (ao) |
| Claude P2-2: no rule says which commit a later registration pins | #6078 | Which commit a registration was built from does not matter; only its pinned bytes do. After the reference run, any change to anything pinned ends the stratum for the registrations made after it | NP1.5, NP1.7, (ad) |
| Claude P2-3: the bar asks for no recorded reason and has no consequence | #6079 | Every change made while the bar is in force records its reason, and what of the native outcomes its author had seen, before any registration that would carry it. The reviewers check those records. A change without one, or one citing a barred value, is not admitted to this stratum | NP1.5, (ao) |
| Claude P2-4: what alternative A costs is understated | #6080 | The lead withdrew its recommendation of A on 2026-11-13, for the reason the review gives; D143's answer, B, stands. A is kept as the record of what was offered, with its cost | Authority, NP1.7, (ab) |
| Claude P2-5, with Codex P2-2: NP1b's checks and the reference pilot's source; the bounds rule before the reference exists | #6081 | NP1b runs every check on the exact source the CHORUS reference pilot registers on. If its second attempt registers on a changed source, the checks are repeated there first, with the same bounds rule. The rule is pinned before NP1b, and both attempts keep it | NP1.2, NP1.6, NP1.7, (z) |
| Claude P3-1, with Codex P2-3: the bar, read literally, forbids the floor's registration | #6082 | Applying the floor rule and the gate to their prescribed inputs is not forbidden; changing them because of what they give is. A filed defect may describe what a native record shows. The amendment for an accepted pilot with no usable fraction may apply NP1.10(s)'s rule to the pilots that have one, and may choose no other rule from an observed fraction | NP1.5, (ao) |
| Claude P3-2: three answered items carry unmarked additions | #6083 | (n)'s deadline and condition, and (r)'s sentence on a pending registration, are marked as the lead's. What B means for the canary is moved out of (ab) into (al) and (s) | NP1.10 |
| Claude P3-3, with Codex P2-5: the prerequisite lists disagree, and the power check has no deadline | #6084 | Each prerequisite has one deadline: before the canary's registration, or before NP1b. The power check (#6046) and the short recorder line (#6065) come before the canary's registration, by the lead's decisions | NP1.7, NP1.9 |
| Claude P3-4: under B a canary that is not accepted still stops the CHORUS reference pilot | #6085 | Kept, and said: the canary is this amendment's feasibility gate, and the reference pilot registers only after its acceptance | NP1.6, NP1.7 |
| Claude P3-5: a binary update, or a change in the probe's limits, ends the stratum with no precaution | #6086 | Both are said, with the precaution for the binary: the reference's pinned copy is kept, with automatic updates off for that copy, for all of production. The probe's limits are registered values; whether they can change while the binary stays the same is not known | NP1.5 |
| Claude P3-6, with Codex P3-2: small accuracy slips | #6087 | (s) lists the conformance case; the header no longer says NP1.5 discusses the basis; the reference is defined as the CHORUS reference pilot's first accepted attempt; the prerequisites' time is the time the record was read; the citation runs to `api_runner.py:1211` | Header, NP1.5, NP1.7, (s) |
| Codex P2-1: the system prompt's pin conflates fixed text with registration-specific guidance | #6088 | The base system-instructions file is compared byte for byte. The command guidance that pinned code generates from per-run values is on the per-run list, and each registration's raw effective-system hash is recorded | NP1.5 |
| Codex P2-4: a diagnostic canary has no outcome rule | #6089 | Moot: there is no "equal change" inside this stratum, so no diagnostic canary arises in it | NP1.7, (ad) |
| Codex P2-6: excluding the canary's reading changes D109 | #6090 | Said: the canary's reading is not a floor input, which supersedes D109's clause on the measured value. Its pending floor, diagnostic reporting and status as no replicate stand | NP1.5, NP1.9, (s) |
| Codex P2-7: the pointer to v7 carries the API budget requirement | #6091 | The API arm's open items are restored in v9's own text | NP1.8 |
| Codex P3-1: the count of first attempts needs its assumptions | #6092 | Stated: the study's five projects in scope, and (e) answered yes or no | NP1.7 |

"""

AFTER_D143 = r"""**After D143** the lead recommended changing its answer from B to A (coordination record, entry of 2026-11-12T23:47:29Z), and then withdrew that recommendation (entry of 2026-11-13T03:10:09Z): "**The lead withdraws its recommendation to change D143 from B to A.** Under A the canary, the first native run on the real binary, would become the stratum's frozen reference, and any repair it reveals would end the stratum and need a new amendment." and "**D143 stands; the owner need not answer the run-limits question.**" NP1.7 gives the rest of the lead's reason."""

LEAD_DECISIONS = r"""- **The lead's engineering decisions of 2026-11-13,** recorded in the coordination record. They are the lead's, not the owner's; this amendment adopts them only through its lettered items.
  - **The gate** (entry of 2026-11-13T02:48:47Z): "**The lead's decision: the stratum's gate becomes a comparison of pins, not a replay.** A production registration must pin the reference run's package source, prompt assets, `.claude` files, schema closure, closed dependency registry, Claude Code binary, base system instructions, selection-bounds policy and registered values byte for byte; only a fixed list of per-run fields may differ (the project's inputs, identifiers, timestamps, paths under the attempt directory, command guidance after those substitutions), and the pending-to-registered floor transition is validated separately against the amendment's arithmetic. Nothing from either tree is executed." and "Consequence, stated plainly: production runs on frozen code; any change to a pinned file after the reference run ends the stratum (no "equal change" path, so no D35 diagnostic canary)." NP1.5 and NP1.10(al) put it to the owner.
  - **The power check** (entry of 2026-11-13T02:44:44Z): "**The lead's decision on #6046:** the canary waits for the battery refusal and the sleep record. The second direct canary of 2026-09-24 was stopped by a macOS idle sleep (`pmset -g log`), and this machine slept four times on 2026-11-12."
  - **The short recorder line** (same entry, #6065): "**The lead's decision:** pass the render specification through the controller's environment, as the prompt text already is, before the reference run (after it, a change to what the model reads ends the stratum)." The lead then set its deadline earlier (entry of 2026-11-13T03:10:09Z): "one deadline for each prerequisite, with #6046 and #6065 before the canary".
"""

D109_BLOCK = r"""- **What D109 requires:** the canary's floor stays pending and its reading is reported; "The measured value informs a registered native floor before any native replicate. No API threshold is copied".
  - **What this amendment changes in it** [proposed, NP1.10(s)]: **the canary's reading is reported and is not a floor input.** That supersedes D109's clause "The measured value informs a registered native floor before any native replicate." D109's pending floor for the canary, its diagnostic reporting and the canary's status as no replicate stand. The reason is NP1.10(ab)'s answer, B: the canary runs under amendment N1's limit set, which no production cell does, so its reading is taken under conditions no production cell shares (NP1.7). The floor comes from the CHORUS reference run and the AI_READI pilot (below)."""

WHEN_FIXED = r"""- **When the rule is fixed.** The plan fixes its floor rule "before any pilot runs", and the later amendment "only computes its value" (§8, lines 1117–1121 and 1159–1162). The pilots whose readings this rule uses, the CHORUS reference pilot and the AI_READI pilot, register only under this amendment, so after it is ratified (NP1.7). Amendment N1's item (ah), ratified by D138, also requires that this amendment is ratified before the canary's word is given: "The native production amendment is ratified before this canary's word is given, so that none of its rules, the floor rule among them, is chosen after a native outcome it governs". N1.5 lets the review of the canary's registration go ahead before that.
  - **If the canary's word were given before this amendment was ratified,** in breach of N1's item (ah), the canary's reading would still enter nothing: it is never a floor input (above). The header of the ratified text then records when the canary's outcome became available, and what of it the lead, each reviewer and the owner had seen; N1.5 requires that record.
  - **A change to this amendment after its ratification** applies only to registrations made after the change is ratified, and it is under the bar below. A "no" that sends an item back for redrafting is ratified before the first registration it governs (NP1.10(ak)).
  - **(aj) is retired.** It made the canary's reading a floor input, and the canary the reference run, only if this amendment was ratified before the canary's first coded word. Under B neither can happen, so the item decided nothing.
"""

BAR = r"""- **No change may rest on a native result** [proposed, NP1.10(ao)]. The plan says of P4b: "It may not use any v10 quality value, A21's included, to choose a project or a threshold. Changing a rule needs its own prospective amendment, and it starts a new analysis stratum." (lines 322–325). This amendment carries that bar to everything that follows the canary.
  - **The rule.** From the canary's first coded word until the acceptance record of the last in-scope production cell is signed, or until the native shared-v1 condition ends under NP1.6, whichever comes first, nobody cites or relies on a coverage fraction, a rubric score, a review verdict, any other quality value or the content of any native record as a reason for any of these: a change to this amendment or a redraft of one of its items; a change of source, of an asset, of the binary, of a registered value, or of the gate's script or data file; the timing of either.
  - **What a change may cite:** a filed defect, which may describe what a native record shows; the class of a failed attempt under NP1.6, and which case of NP1.5 or NP1.6 occurred; and a prerequisite ratified with this amendment. So the amendments this text itself calls for, after a pilot that concluded without acceptance or after a change that ends the stratum, can say what triggered them.
  - **What it does not forbid: the applications this amendment prescribes.** Computing the floor's value by NP1.10(s)'s rule from the eligible pilots' readings, and running the gate on a registration, apply rules fixed here to their prescribed inputs. Changing that rule, the gate or their inputs because of what they give is forbidden. An amendment that a case of this section calls for, an accepted pilot with no usable fraction for example, may cite the case; it may set the floor by applying NP1.10(s)'s rule to the eligible pilots that have a usable fraction, and it may choose no other rule from an observed fraction.
  - **A recorded reason for every change.** Every change of this amendment, of source, of an asset, of the binary, of a registered value or of the gate made while the bar is in force records, before any registration that would carry it, its reason from the list above and what of the native outcomes its author had seen. The two reviewers of each later registration check those records for every change since the canary's first coded word. **A change with no such record, or one whose record cites a barred value, is not admitted to this stratum:** a registration that carries it is not made under this amendment.
  - **Usage, run time and the record.** Usage and run time are not quality values: the measured-usage packet reports them (NP1.7), and NP1b's own bar says what it may not do with them. The header of every change under this bar says what of the native outcomes its author, each reviewer and the owner had seen.
  - **A new stratum is bound by the same bar.** The amendment that follows a change that ends this stratum may not choose a threshold, a project or a pilot from a native coverage or quality value, and it says which earlier native results its author had seen.
"""

REFERENCE_AND_GATE = r"""- **The reference run** [proposed, NP1.10(al)]. One rule, with no pilot run again and no production source chosen.
  - **What it is.** The production stratum has one reference: **the first accepted attempt of the CHORUS reference pilot** (NP1.6), one native CHORUS pilot registered after NP1b and after the canary's acceptance, under the production limit set, with the floor pending. The canary is never the reference: it runs under amendment N1's limit set (NP1.10(ab), answered B), and a registered value that differs is never equal (below).
  - **What the reference fixes.** Everything that attempt's registration pinned: its package source and every other file it pins, its selected prompt assets, its schema closure, the closed dependency registry and its registered values. Three of those are things the model reads that are set per registration: **the Claude Code binary** (by sha256), **the base system-instructions file** (by sha256) and **the selection-bounds rule** (below). The system prompt the binary receives is that file followed by command guidance that pinned code generates from the registration's own values (`native_shared_registration.py:46`, `:247–256`, audit, from the Claude review of v7). The base file is compared byte for byte; the guidance is a per-run field (below).
  - **Every later registration is equal to the reference, or it is not in this stratum.** The AI_READI pilot's registration and every production cell's registration are compared with the reference by the gate below. **Equal:** the registration belongs to this stratum. **Not equal:** it does not, and it is not made under this amendment. **Which commit a registration was built from does not matter; only its pinned bytes do.** Nobody chooses a production commit, and nobody decides whether a difference matters.
  - **No pilot is run again.** A pilot's reading is never replaced by a second run of that pilot.
  - **Production runs on frozen code.** After the reference run, any change to a pinned file, to an asset, to the binary, to the base system instructions, to the selection-bounds rule, to the gate's own script or data file, or to a registered value outside the per-run list ends this stratum for the registrations made after it. Those need a new prospective amendment, which names its own pilots before any of them runs and is bound by the bar above. This stratum's floor, its K_native and its readings never move, and a reading that a later stratum does not use is still reported. **There is no "equal change":** a change either leaves every pinned byte as it was, or it ends the stratum. So D35's diagnostic canary does not arise inside this stratum (NP1.7).
  - **What this costs, and the precautions.** A repair of anything pinned cannot be taken into this stratum after the reference run, however small. The repairs the canary reveals go in before the CHORUS reference pilot registers (NP1.7). Two changes that nobody chooses would also end the stratum. **The binary:** the reference's pinned copy of the Claude Code binary is kept, unchanged and with automatic updates off for that copy, for all of production. **The probe's limits:** the runtime declaration's `limits`, which each registration takes from its own observation probe (N1.2), are registered values, so a change on the provider's side in the reported limits would end the stratum just as a binary update would. Whether those values can change while the binary stays the same is not known.
- **The gate** [proposed, part of NP1.10(al)]: a comparison of the registrations' pins, not a replay (the lead's decision, Authority). It is a script with a data file. Both are pinned by sha256 in the CHORUS reference pilot's registration packet, and both are reviewed against this section before NP1b (NP1.7): **an engineering prerequisite, assigned and not written.**
  - **What it reads:** two registration packets, the reference's and a candidate's, each first verified by the production validators. **Nothing from either source tree is executed.**
  - **Equal** if and only if every file the registration pins (the package source, the prompt assets, the `.claude` command and agent files, the schema closure and the closed dependency registry), the Claude Code binary's sha256, the base system-instructions bytes, the selection-bounds rule and every registered value are byte-identical to the reference's, except the fields on the per-run list.
  - **The per-run list,** in the gate's data file, names exactly these and nothing else:
    1. **the project's own inputs:** the bundle, the chunk manifest, the source-manifest entry, the omission context and the scope declaration, each by its pinned path and sha256;
    2. **the selection bounds' values.** The gate does not compare them with the reference's. It recomputes them under the pinned selection-bounds rule from the registration's own inputs, and requires them to equal what the registration declares;
    3. **identifiers:** the registration, selection, job and attempt identifiers;
    4. **timestamps,** in the format the registration declares;
    5. **paths under the attempt directory;**
    6. **the system prompt's command guidance,** which pinned code generates from the values above. The gate requires the generating code, which is pinned source, to be byte-identical, and records each registration's raw effective-system hash. An identity substitution in that guidance is not a change of the system prompt.
  - **The floor's change** is the one permitted change of a registered value, and it is validated separately. A pilot's receipt-policy registration carries `{state: pending, mode: diagnostic_pilot}`; a production cell's carries the registered fraction. The gate requires that the production cell's value and basis (`receipted_part`) are exactly those of the floor's ratified registration (NP1.7 step 6), computed by NP1.10(s)'s arithmetic, and that every other field of the receipt-policy registration is byte-identical. What that one value does inside a run, where helper output shows "pending" in a pilot and "passed" in production and the hashes that carry it differ, is the pinned code acting on that value. It is never compared, because nothing is executed.
  - **Three results.** **Equal.** **Not equal,** with every differing pin listed. **Cannot decide:** a packet fails its validators, or a field is neither byte-identical nor on the per-run list. "Cannot decide" is a hold: that registration is not made until the cause is repaired. It is never a pass and never a reason for another pilot. **A "cannot decide" whose cause is in the gate's own script or data file** is resolved only by a ratified prospective change to them, never by running the gate again with an edited list; until then that registration is not made.
  - **When it runs.** The gate is run on every later registration, and must say "equal", before that attempt's launch word is asked for. Its saved result names the script's, the data file's and both packets' sha256s, and is in the registration's packet. A registration that is not equal cannot be launched under this amendment.
  - **What the reviewers do.** The two reviewers of a registration confirm that the gate's script and data file are the pinned ones, that it was run on the right two packets, and that the saved result is the one in the packet. They do not interpret it.
  - **What it cannot show.** That the provider's model is the same from run to run; the plan declares that drift (lines 959–961). And nothing about behaviour: it shows that a run was given the reference's code, assets, binary and rules, with only the listed fields changed.
  - **The selection-bounds rule** [proposed, part of NP1.10(al)]. The bounds are values each registration supplies, inside ceilings the source fixes (`native_shared_contract.py:109–120`), and they gate a run: an input larger than its bound is refused (`:777–779`); an inventory larger than its bound stops the receipt check, and a stage request larger than its bound is refused (`native_shared_receipts.py:337–338`; `native_shared_stage/__init__.py:342–343`; audit, from the Claude review of v8). That review found no code that computes them. **This amendment requires a fixed rule:** a function from a project's inputs to its bounds, inside the source's ceilings, written down and pinned by sha256 with the gate. A rule that gives one set of values for every project, large enough for all of them, is a valid rule. It is fixed and reviewed before NP1b, which uses it in NP1.2's inputs test, and both attempts of the CHORUS reference pilot use it. It is an engineering prerequisite and is not written (NP1.7).
  - **Where the run limits stand.** With the four protected files the owner approved (D139), the instruction's recorder command carries `--render-spec-json`, whose value embeds the raw runtime declaration, and that declaration contains `deadline_seconds` and `budget_guard_usd` (`api_runner.py:1194–1211`; `native_shared_render.py:205–212`, `:289–295`, `:378–380`; `native_shared_runtime_constants.py:8–9`; read by the lead at `6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834`). The lead decided to pass the render specification through the controller's environment before the canary (#6065), which takes it out of the recorder line. The gate depends on neither: the limit set is a registered value, so the canary's registration, which declares amendment N1's set, is never equal to a production registration.
"""

REFERENCE_PILOT = r"""  - **The CHORUS reference pilot** [proposed, NP1.10(al)] always runs: under NP1.10(ab)'s answer, B, the canary cannot be the reference run, and the reference pilot's first accepted attempt is. It is one native CHORUS run, n=1, never a replicate and never one of this amendment's cells, with its own label, registration, two reviews and word. It is registered after NP1b, on the source NP1b checked, under the production limit set, with the floor pending as the canary's was; D109 set that state for the canary, and applying it here is part of that item. It registers only after the canary is accepted (NP1.7 step 1), and it runs before the AI_READI pilot. It is judged by rows B0–B7, with B5 reported and UNMEASURABLE. Its two attempts are its own. It is not a second run of the canary, which stays the n=1 feasibility result.
  - **Second attempts.** The AI_READI pilot's second attempt, like its first, registers only where the gate finds it equal to the reference; a change that is not equal ends this stratum (NP1.5) and is not taken into the pilot. The CHORUS reference pilot's second attempt comes before any reference exists, so it may register on a changed source. The change has its recorded reason under NP1.5's bar, the attempt keeps the selection-bounds rule NP1b used, and NP1b's checks are repeated on that source before it registers (NP1.7). What its accepted attempt pinned is the reference.
"""

PREREQUISITES = r"""- **Code that has to exist, each item with one deadline.** These are engineering prerequisites, not choices. No "no" to an item of this amendment adds to them (NP1.10). **Their state is given per the lead's record, as read on 2026-11-13 through its entry stamped 03:10:09Z; the author of this draft did not verify it.** "On the published candidate" means on the native integration branch's draft pull request. None of this code is merged into main.
  - **Before the canary's registration,** so that the canary, every pilot and every production cell run one source and one set of assets:
    - N1.9's list.
    - **#5939, the pending floor** (NP1.5), with its review follow-ups #5994 and #5995: repaired and committed; on the published candidate. A re-check of the follow-ups is not on record, and a CI failure that the #5994 repair caused (a new public function that needs a declaration in a protected file) is assigned.
    - **#5966, the helper cache** under HOME, which stopped the public completion path: repaired and independently reviewed; on the published candidate. The two gaps in its tests, #6030 and #6031, are assigned.
    - **#5967, the failure record** when the runtime validation itself fails, without which there is no exact failed readback (N1.4(A) item 6), with #6015: repaired; an independent re-check closed #6015; on the published candidate.
    - **The retention change** (NP1.4; answered keep, D141), with #6016: written; an independent re-check closed #6016; on the published candidate.
    - **The launch sequence, #5989 to #5993, with #6047, #6048 and #6074:** #5989 to #5991 are repaired and on the published candidate. A re-check found #5992 and #5993 not closed; their repairs, #6047 and #6048, are committed on a helper's branch, the correction for #6074 is to be committed beside them, and a re-check follows. Not on the published candidate yet. #6049 is a known limit that the lead ruled not blocking for the canary.
    - **#6046, the power check** before a launch sequence starts, and a record of a host sleep during a run: assigned, not written. The lead's decision (Authority).
    - **#6065, the short recorder line:** the render specification passed to the recorder through the controller's environment. Assigned, not written. The lead set it before the canary's registration (Authority): the first direct CHORUS canary was disqualified at its recorder line after a complete generation (#2282).
    - **The two-set run-limits code** (NP1.10(ab); D143): assigned, not written.
    - **The basis change** (NP1.5; answered at-receipt, D140): written on a separate local branch; its integration in D140's form is assigned.
    - **The changed policy asset:** the pending-floor sentence the owner chose (D142) and the sentence that names the at-receipt basis. The lead has prepared it locally; the changed pin registry's hash is with the owner, and nothing is applied (D142).
  - **Before NP1b,** because NP1b uses them and the CHORUS reference pilot's registration packet pins them:
    - **the gate's script and data file** (NP1.5), reviewed against NP1.5 by both reviewers, with their findings filed and closed: assigned, not written. The earlier replay comparison is a development aid outside this amendment; an independent review found it unfit to be the gate (#6066 to #6073);
    - **the selection-bounds rule** (NP1.5), reviewed the same way: not written.
"""

NP1B_BULLETS = r"""   - confirms that the source accepts exactly D143's two registered limit sets and no other values;
   - names, as a conformance check on the merged source, the exact saved fields of the eligible record, of the pre-completion reading and of the acceptance record (NP1.4, NP1.6);
   - pins the comparator manifest's record hashes, which include AI_READI's only if that comparator exists by then (NP1.3);
   - pins the recall adapter, the common checker's source hash and the schema closures;
   - names the exact source on which the CHORUS reference pilot registers, and runs every one of these checks on that source;
   - confirms that the gate's script and data file and the selection-bounds rule exist and were reviewed against NP1.5, and records their sha256s, which the CHORUS reference pilot's registration packet pins (NP1.5).

"""

NP1B_TAIL = r"""**It does not register the floor:** the CHORUS reference pilot runs after it (step 6). When the floor's registration computes the value by NP1.10(s)'s fixed rule, that is not such a choice: it applies the rule to the accepted pilots' coverage readings, as the plan's A15 does (lines 1159–1162). **Every later change is under NP1.5's bar** (NP1.10(ao)).

   **If the CHORUS reference pilot's second attempt registers on a changed source,** NP1b's checks are repeated on that source, in a dated addendum reviewed and ratified as NP1b is, before that attempt registers. The repeat applies the same tests with the same selection-bounds rule. It chooses nothing about scope or bounds from observed results: a project that passed on the first source and fails on the changed one is "not planned (NP1b: inputs)"."""

STEPS_4_TO_7 = r"""4. **The CHORUS reference pilot** (NP1.6): registered on the source NP1b checked, under the production limit set, after the canary's acceptance; run, and accepted or concluded under NP1.6. Its first accepted attempt is the reference run.
5. **The AI_READI pilot,** if NP1.10(e) is yes and AI_READI is in scope: a registration that the gate finds equal to the reference before its launch word is asked for; run, and accepted or concluded under NP1.6.
6. **The floor's registration** (NP1.5), in its own dated amendment, reviewed and ratified as NP1b is, after every pending pilot has concluded. It records the reference run and what it pinned, and every pilot's reading, the canary's included as a reported reading that is not an input, **and fixes K_native** (NP1.3). **No production cell registers before it.**
7. **Production cells, in NP1.2's order, one attempt at a time.** For each attempt:
   - a registration that the gate finds equal to the reference before the attempt's launch word is asked for, with the gate's saved result in its packet. It pins the full and core schema closures, the bundle, the chunk manifest and the source manifest (plan §11, lines 1404–1405), the runtime and its probes (N1.2, N1.9), the binary, the base system-instructions file, the selection-bounds rule and the bounds it gives for the project, the production limit set, and the receipt policy that carries the registered floor and its basis, each as the reference has it where the gate requires it;
   - two independent reviews of the registration and its packet (N1.3);
   - the owner's statement of launch terms and the coded word, which binds one attempt by construction (N1.5);
   - capture, guard and launch as N1.5 orders them, as one reviewed sequence with no automatic retry (amendment N1's item (z));
   - acceptance under NP1.6.
"""

RUNTIME_TERMS = r"""- **Runtime terms** [answered: B, NP1.10(ab); D143]: the owner chose B on 2026-11-12: "Run limits: two registered sets." (D143). The lead later recommended changing the answer to A, and withdrew that recommendation on 2026-11-13 (Authority). **B is the answer in force.** A and C are kept as the record of what was offered.
  - **What the source fixes today.** Every runtime that is not the synthetic test profile has to declare a deadline of exactly 21,600 seconds (`native_u4b_policy.py:19`, `N1_DEADLINE_SECONDS`, checked by `validate_runtime_terms`, `:53–63`) and the dollar guard "90" (`native_u4b_runtime.py:171`), which starts the binary with `--max-budget-usd 90` (N1.5; D110). A registration with other values is refused. Those are N1.5's terms for the canary.
  - **What the guard is on a subscription run.** It is a backstop against a runaway run, counted in the binary's own accounting of the run at API prices. No dollars are spent: amendment N1 records D14 as "The budget is subscription usage, plus a dollar backstop."
  - **Why the canary's terms cannot serve every run.** The plan's own estimates per run, for the API arm at API prices (lines 369–376), are: CHORUS about $37 expected and $49 at caps; CM4AI $83 and $102; VOICE $105 and $127; VOICE_PEDIATRIC $96 and $118, with the VOICE record as proxy; AI_READI $162 and $191; Kids First not priced. They come from another harness, and the binary's counter is its own accounting of a native run, so they are a proxy and not a measurement. On that proxy a $90 guard is expected to stop VOICE, VOICE_PEDIATRIC and AI_READI, and CM4AI is borderline. Those terms would lose most of the matrix.
  - **The inputs point the same way.** Per the lead's record of a helper's measurement on 2026-11-12, in bundle bytes and chunks: CHORUS 35,920 and 8; VOICE_PEDIATRIC 206,008 and 13; CM4AI 320,799 and 28; VOICE 376,446 and 22; AI_READI 430,393 and 25. CHORUS is by far the smallest, and the canary's run time says little about the others.
  - **B (the answer in force): two registered sets of terms, and nothing else.**
    - **The canary keeps amendment N1's terms,** a $90 guard and a 21,600 s deadline, and amendment N1 is not reopened. **Every pilot after the canary and every production cell runs under one production set, fixed here:** a $400 guard and a 43,200 s deadline. $400 is about 2.5 times the largest expected estimate, AI_READI's $162; the canary's $90 is about 2.4 times CHORUS's $37. The deadline is twice the canary's. Neither value rests on a native measurement, because none exists: "The values are the lead's proposal, accepted by the owner; nothing has measured a native run." (D143).
    - **The source change.** Before the canary, the source is changed to accept exactly these two registered sets and nothing else. A registration declares one set whole; a mixed pair or any other value is refused. The lead's additions to D143: no project is named in code, and nothing infers the set from the project. This is an engineering prerequisite and is not written (above).
    - **What B means for the canary.** The canary's registration declares amendment N1's set, a registered value no production registration has, so the gate never finds the canary equal to production. The two sets also accept different attempts: a CHORUS run that takes seven hours, or whose cost estimate passes $90, is accepted under the production set and stopped under the canary's. So the canary is not the reference run, and its reading is not a floor input (NP1.5). One CHORUS reference pilot runs under the production set after NP1b (NP1.6): one more native run, with its own two reviews and word.
    - **Why the lead withdrew A** (the lead's reasons, recorded on 2026-11-13): "Every earlier first run on the direct arm revealed something that needed a fix (#2282; the idle sleep of 2026-09-24; #2427). Under B the canary is N1's diagnostic pilot and a shakedown: repairs it reveals go in before the CHORUS reference pilot, at the cost of that one extra CHORUS run, and N1 stays as ratified."
  - **A (recommended by the lead after D143, then withdrawn; kept as the record):** one set for every run, the canary included: a $400 guard and a 43,200 s deadline. The canary would then be the reference run if accepted, and no CHORUS reference pilot would run. Its cost, which v8 understated: the first native run would become the frozen reference, so a repair it revealed to anything pinned would end the stratum before its first production cell; its registration would also have to pin the gate and the selection-bounds rule; and amendment N1's deadline (its item (p)) and the guard D110 decided would be revised and balloted again.
"""

COUNT = r"""  - **The count.** With the study's five projects in scope and NP1.10(e) answered yes: 16 first attempts (the canary, the CHORUS reference pilot, the AI_READI pilot, 12 replicates and VOICE_PEDIATRIC's cell); 15 if (e) is answered no. At most one further attempt per pilot or cell. A project out of scope removes its cells. No diagnostic canary arises inside this stratum (below). This is a count, not a budget or a schedule.
"""

ONE_PROCEDURE = r"""- **One procedure** [proposed, NP1.10(ad)]: every later registration, the AI_READI pilot's and every production cell's, is made only where the gate finds it equal to the reference (NP1.5), and before its launch word is asked for. The gate's saved result is in the registration's packet; it is not optional.
  - **After the reference run, a change to anything pinned ends this stratum** for the registrations made after it: the source, the assets, the binary, the base system instructions, the selection-bounds rule, the gate's own script or data file, or a registered value outside the per-run list. It needs its own prospective amendment before any of its cells registers, and it never moves this stratum's registered floor or K_native. A change to how attempts are admitted, retried, stopped, selected or retained is always such a change. The plan says why a changed procedure is a new stratum: D35's parity test and diagnostic canary "show that the engineering is sound, not that a changed selection process has the same estimand" (lines 1221–1236).
  - **There is no "equal change".** v8 let a change that its comparison found equal stay in the stratum on D35's terms: "Later runner changes require a CHORUS byte-parity test and one separately authorized diagnostic canary before remaining runs re-register." (plan §11, lines 1402–1404). Under the gate, a registration whose pinned bytes are unchanged is byte parity itself, and any other change ends the stratum. So no diagnostic canary arises inside this stratum, and what a diagnostic canary's ending would decide does not arise either.

"""

API_OPEN_ITEMS = r"""- **The API arm's own open items,** recorded here and decided elsewhere:
  - the A21 run of 2026-11-11 ended at its first typed-audit call on a provider refusal (#5874). Its classification under plan §10 has not been recorded. By the lead's reading it used one of the re-canary cell's two attempts (plan §7);
  - the schema release of the comparison registration (above). The API arm's ratified schema is 3.1.0 (D71(a), P4a amendment 1), and the A21 registration was built on main at 3.2.1 with no API-arm schema amendment on record (N1.6);
  - **the provider account's budget has to cover the comparison set, and it is read before any launch;**
  - the order of the rebuild and the start of D35's freeze follow amendment N1's item (y), answered yes (D138): the freeze starts at the rebuilt comparison registration."""

CANARY_CHANGES = r"""  - the prerequisites of NP1.7's list "before the canary's registration", which N1.9's list does not name: #5939 (with #5994 and #5995), #5966 (with #6030 and #6031), #5967 (with #6015), the retention change (with #6016), the launch sequence #5989 to #5993 (with #6047, #6048 and #6074), the power check #6046, the short recorder line #6065, the two-set run-limits code, the basis change and the changed policy asset;
  - the basis is at-receipt (D140): the canary's model reads the changed sentences of the policy asset, and the canary's pending reading may carry the at-receipt counters as a diagnostic. Its pending registration is unchanged and declares no basis;
  - records are kept (D141): a stopped or rejected canary attempt retains its full and core records;
  - the run limits (D143, B): the source the canary runs accepts both sets, and the canary's registration declares N1's. The canary is therefore never the reference run, and its reading is not a floor input (NP1.5, NP1.7);
  - amendment N1's item (ah), ratified by D138, requires that this amendment be ratified before the canary's word (NP1.5).

"""

ANSWERED = r"""**Answered in advance.** On 2026-11-12 the owner answered three items and gave one direction (D140, D141, D143, D145; Authority): (r) at-receipt, (n) keep, (ab) B, and (am) delegated starts allowed for production runs. They are marked "Answered" below. Their written alternatives are kept as the record of what was offered. Ratification records them as answered and does not ask them again. The lead's later recommendation to change (ab) to A was withdrawn on 2026-11-13 (Authority), so no answer is reopened. Those answers did not ratify this amendment: the record says "no ratification of amendment NP1, which is still in review".

"""

ITEM_N = r"""- **(n)** **Answered: keep (D141).** The incomplete capture retains the current full and core records with their sha256, so that a stopped or rejected attempt can have an eligible record. It depends on (m). The lead's additions, which D141 does not set: the deadline, before the canary's registration (NP1.7); and the condition, which NP1b confirms on the merged change, that the retained files are members of the capture's snapshot. The alternative that was offered, and not taken: the native eligible set limited to attempts whose recorder ran (NP1.4). *Changed: the lead's deadline, marked.*
"""

ITEM_R = r"""- **(r)** **Answered: at-receipt (D140).** The floor's basis is D37's at-receipt coverage. A registered numeric floor declares `basis: receipted_part`, and one without it is refused (D140, with the lead's ruling on its form). The lead's additions: a pending registration is unchanged and may carry the at-receipt counters as a diagnostic reading; and the code change is in the source the canary's registration pins. The basis does not change afterwards in this condition. The alternative that was offered, and not taken: the final-record basis (NP1.5). *Changed: the pending-registration sentence marked as the lead's.*
"""

ITEM_S = r"""- **(s)** The floor rule: the lowest of the eligible native pilots' at-receipt fractions, each read once from the final-stage check, rounded down to a multiple of 1/20 and capped at 19/20. The eligible pilots are the reference run, which is the first accepted attempt of the CHORUS reference pilot, and the AI_READI pilot. **The canary's reading is reported and is never an input; this supersedes D109's clause "The measured value informs a registered native floor before any native replicate."** D109's pending floor for the canary, its diagnostic reporting and the canary's status as no replicate stand. The lowest value that can be registered is 1/20. The floor is not registered, and no production cell registers: while a required pilot is pending; while an instrument finding on the two readings is open; while the gate cannot decide on the AI_READI pilot's registration; where an accepted pilot has no usable fraction, in which case its project stays in scope and a prospective amendment says how the floor is set; where there is no reference run; and where the reference run's source no longer saves the fields the rule reads, until a prospective amendment restates them (NP1.5). *Rewritten: the canary is never an input, which supersedes one clause of D109; the conformance case is listed.*
"""

ITEM_Z = r"""- **(z)** The staged procedure: no pilot or production registration under this amendment before the canary's acceptance record is signed; B6's reading of every canary attempt that kept a record before NP1b; then the measured-usage packet, then NP1b, then the CHORUS reference pilot, then the AI_READI pilot, then the floor's registration in its own amendment, each reviewed and ratified before the registrations that depend on it. NP1b applies rules, changes none, takes no number from the owner and does not register the floor; computing the floor by (s) is an application. If the CHORUS reference pilot's second attempt registers on a changed source, NP1b's checks are repeated on it first (NP1.5, NP1.7). *Rewritten: the CHORUS reference pilot always runs; NP1b's repeat.*
"""

ITEM_AA = r"""- **(aa)** Reviews: both reviewers review every registration, each registration with its own two review documents. Each review confirms that the gate was run with its pinned script and data file on the right two packets, and checks the recorded reasons the bar requires; a reviewer does not judge a difference (NP1.7). *Changed: the gate, and the recorded reasons.*
"""

ITEM_AB = r"""- **(ab)** **Answered: B (D143).** Runtime terms: two registered sets and nothing else. The canary keeps amendment N1's $90 guard and 21,600 s deadline, and every later pilot and every production cell runs under one production set, a $400 guard and a 43,200 s deadline. The lead's additions to D143: no project is named in code, and nothing infers the set from the project. The record of what was offered: A, one set for every run, which the lead recommended after D143 and withdrew on 2026-11-13; and C, the canary's terms for every run (NP1.7). *Changed: the recommendation of A withdrawn; what follows from B for the canary is (al)'s and (s)'s, not this item's.*
"""

ITEM_AD = r"""- **(ad)** One procedure: every later registration is made only where (al)'s gate finds it equal to the reference, before its launch word is asked for. After the reference run, a change to anything pinned ends this stratum for the registrations made after it and needs its own prospective amendment; it never moves this stratum's floor or K_native. There is no "equal change", so no diagnostic canary arises inside this stratum (NP1.7). *Rewritten: the gate in place of the comparison; no equal-change path.*
"""

RETIRED_AJ = r"""**Retired**
- **(aj)** Retired in v9. It made the canary's reading a floor input, and the canary the reference run, only if this amendment was ratified before the canary's first coded word. Under (ab)'s answer, B, the canary's reading is never a floor input and the canary is never the reference run, so the item decided nothing. Amendment N1's item (ah) still requires that this amendment is ratified before the canary's word (NP1.5).

"""

ITEM_AK = r"""- **(ak)** What a "no" means: it returns the item for redrafting, except for the nine items that carry a written alternative; a redraft is ratified before the first registration whose outcome it governs, as the table above names it; and production registrations wait for every unresolved analysis-defining item (NP1.10). *Changed: nine written alternatives, (aj) being retired.*

"""

ITEM_AL = r"""- **(al)** The reference run and the gate. The production stratum's reference is the first accepted attempt of the CHORUS reference pilot: one CHORUS pilot registered after NP1b and after the canary's acceptance, under the production limit set, with the floor pending. The reference is everything that attempt's registration pinned: the package source and every other pinned file, the prompt assets, the schema closure, the closed dependency registry, the registered values, the Claude Code binary, the base system-instructions file and the selection-bounds rule, which is fixed and reviewed before NP1b. The AI_READI pilot's registration and every production registration are equal to it by NP1.5's gate, or they are not in this stratum. The gate compares the two registration packets' pins and executes nothing; only the per-run list may differ, the bounds are validated by recomputing them under the rule, and the floor's change from pending to registered is validated separately. "Cannot decide" is a hold, and a defect in the gate itself is repaired only by a ratified prospective change. No pilot is run again, and after the reference run any change to anything pinned ends the stratum for the registrations made after it (NP1.5, NP1.6, NP1.7). *Rewritten: a comparison of pins, not a replay; the reference is always the CHORUS reference pilot's.*
"""

ITEM_AO = r"""- **(ao)** No change may rest on a native result. From the canary's first coded word until the last in-scope production cell's acceptance record is signed, or until the native shared-v1 condition ends, no coverage fraction, rubric score, review verdict, other quality value or content of a native record is cited or relied on as a reason for a change to this amendment, a change of source, asset, binary, registered value or the gate, or the timing of either. A change may cite a filed defect, which may describe what a native record shows, the class of a failed attempt and the case of NP1.5 or NP1.6 that occurred, and a ratified prerequisite. Applying the floor rule (s) and the gate to their prescribed inputs is not forbidden; changing them because of what they give is. Every change made while the bar is in force records its reason, and what of the native outcomes its author had seen, before any registration that would carry it; the reviewers of each later registration check those records; a change without such a record, or one citing a barred value, is not admitted to this stratum. A new stratum's amendment is bound by the same bar (NP1.5). *Rewritten: the applications it does not forbid, and the recorded reason with its consequence.*
"""

if __name__ == "__main__":
    main(sys.argv[1])
