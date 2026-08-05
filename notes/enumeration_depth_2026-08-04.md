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

    agent   items 1690   checkable 858 (51%)   anchors 2514   found 1799 (72%)
    API     items 2528   checkable 829 (33%)   anchors 1367   found 1236 (90%)

**Read the coverage column before the grounding column.** Half the agent's items
and two thirds of the API's carry nothing verifiable at all, so neither 72% nor
90% is a statement about the record as a whole.

The two numbers have to be read together, and doing so is what makes the
comparison hard rather than easy:

- The agent puts **1.8× as many checkable anchors** into half as many items —
  its entries carry substantially more specific, falsifiable content.
- A larger share of those anchors are **not found** in the sources (72% against
  90%). That is consistent with the agent inventing more, and equally consistent
  with it paraphrasing identifiers, citing things stated across document
  boundaries, or elaborating from context. Substring matching cannot separate
  these.

**What this does not establish.** It measures verifiability, not truth. An anchor
found in the source shows the record did not invent that token; it says nothing
about whether the surrounding claim is right. Both arms are measured identically,
so the comparison is sound even though each absolute rate is a lower bound.

## What follows

**Do not add an enumeration question to rubric20.** The judge receives only the
D4D record — `rubric20_system_prompt.md` says "Read the provided D4D YAML file" —
so it cannot see sources and any question it asked would score a count. On these
numbers a count question would have ranked the API arm *above* the agent arm
while the 28% of its anchors that are unverified went unexamined.

**Do not change the API arm to imitate the agent before the rerun.** The gap is a
finding about runtimes, and generic-v3's value is being a clean prompt condition
comparable to v1 and v2. Changing generation mid-study destroys the comparison
the study exists to make. If elaboration depth matters for the manuscript, the
agent arm is already a legitimate arm with data on disk.

**Report both numbers wherever depth is discussed.** Items and characters move in
opposite directions here; either alone supports the wrong conclusion, as this
note's own correction demonstrates.
