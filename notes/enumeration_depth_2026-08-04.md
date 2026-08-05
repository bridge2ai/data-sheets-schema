# The API writes fewer, longer entries — not fewer entries

**This corrects the finding in #332.** That issue reported the agent runtime
enumerating "about twice as many items" as the direct API. Measured properly, the
API enumerates **more** items on all four projects. What the agent produces is
more *text per item*.

The original claim came from per-slot character counts, which measure
elaboration, and from an item count taken over the minority of items that carry a
structured label. Both were read as depth. They are not.

## The measurement

Paired runs, `2026-07-28_claude-opus-5-generic` against
`2026-07-31_claude-opus-5-api-generic`: identical prompt file
(`d4d_generic_arm_prompt.md`), identical four-phase mode, differing only in
`Agent runtime` (Claude Code against Claude API direct). Three replicates each.

| project | items agent | items API | chars agent | chars API |
|---|---|---|---|---|
| AI_READI | 170 | 226 | 121,512 | 87,704 |
| CHORUS | 129 | 140 | 52,881 | 34,539 |
| CM4AI | 139 | 249 | 104,836 | 70,011 |
| VOICE | 126 | 227 | 120,071 | 87,704 |

**The API enumerates more and writes less.** Both consistently, across all four
projects — the two measures point in opposite directions, which is why reporting
either alone is misleading.

Per slot the item counts are mixed rather than uniform: the agent lists more
`variables` on AI_READI (45 against 22) and more `resources`, while the API lists
more `external_resources` everywhere and nearly three times the `creators` on
CM4AI. The character counts are not mixed — the agent writes more in almost every
slot, up to 13× on CM4AI `resources`.

So the reader's impression of "thinner" records is about **elaboration per
entry**, not how many entries there are.

## How much of this can be checked at all

`src/data_sheets_schema/enumeration.py` measures grounding by looking for
*anchors* — DOIs, ORCIDs, RRIDs, URLs, grant numbers and other tokens mixing
letters and digits — verbatim in the project's source bundle. Ordinary prose is
deliberately not matched: every English word appears somewhere in a 200 KB
bundle, so counting those would drive every rate to 100%.

    agent   items 1690   checkable 641 (38%)
            identifier anchors 1264   found 1225 (97%)
            url anchors         459   found  424 (92%)

    API     items 2528   checkable 763 (30%)
            identifier anchors  948   found  929 (98%)
            url anchors         303   found  300 (99%)

**Read the coverage line before the grounding lines.** Under two fifths of the
agent's items and under a third of the API's carry anything verifiable, so none
of these rates describes a record as a whole.

**On identifier fidelity the two arms are indistinguishable: 97% and 98%.**
Whatever separates them, it is not one arm inventing DOIs, ORCIDs or grant
numbers that the other does not.

### Two corrections that produced those numbers

An earlier version of this note reported 72% against 90% and called the gap
"consistent with the agent inventing more". It was not. Two measurement faults
produced almost all of it, both found in review:

**Minted identifiers (#335).** A record mints its own `id` —
`CM4AI_creator_release_authors`, `aireadi:variable_ntprobnp` — which by
construction cannot appear in a source. Counting those as anchors that were not
found measured identifier *style* and penalised whichever arm gives things stable
identifiers. `id` is now excluded from anchor extraction.

**URLs against prose (#336).** Of the 119 `creators` anchors the agent emitted
that were not found, **115 were URLs**, and they were institutional homepages:
`vumc.org`, `emory.edu`, `ufl.edu`, `sickkids.ca`, `wustl.edu`,
`weill.cornell.edu`, `usf.edu`. Those are correct Bridge2AI VOICE affiliations.
The sources name them in prose — "Vanderbilt University Medical Center" — and the
record supplies the canonical URL. That is enrichment from world knowledge, and
substring matching cannot tell it from invention. URL anchors are now counted
separately so the confound is visible rather than buried in one rate.

The residual difference is in URL grounding, 92% against 99%, and it means the
agent supplies more canonical URLs for entities the sources name in prose. It is
not a fidelity gap.

### What this does not establish

It measures verifiability, not truth. An anchor found in the source shows the
record did not invent that token; it says nothing about whether the surrounding
claim is right, and a *missing* anchor may be paraphrase, cross-document
inference, or enrichment as above. Both arms are measured identically, so the
comparison holds even though each absolute rate is a lower bound.

Normalising by text volume is also worth stating: the agent writes 1.4× the
characters, and its *found* anchor density is 1.50 per 1,000 characters against
the API's 1.47. Per unit of text, verified content is equally dense.

## What follows

**Do not add an enumeration question to rubric20.** The judge receives only the
D4D record — `rubric20_system_prompt.md` says "Read the provided D4D YAML file" —
so it cannot see sources and any question it asked would score a count. On these
numbers a count question would have ranked the API arm *above* the agent arm on
item count alone, while saying nothing about the fact that under two fifths of
either arm's items carry anything checkable at all.

**Do not change the API arm to imitate the agent before the rerun.** The gap is a
finding about runtimes, and generic-v3's value is being a clean prompt condition
comparable to v1 and v2. Changing generation mid-study destroys the comparison
the study exists to make. If elaboration depth matters for the manuscript, the
agent arm is already a legitimate arm with data on disk.

**Report both numbers wherever depth is discussed.** Items and characters move in
opposite directions here; either alone supports the wrong conclusion, as this
note's own correction demonstrates.
