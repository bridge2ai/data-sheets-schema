# Assignment to Codex helper 3: the equivalence comparison as a script, with its field list as data

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper3-start-claim-design-ruling-20261112.md` (issues #5992 and #5993).

## Why

The production amendment (NP1, draft v7: `git -C P show 814701f1a39df1d733c199797a3d692d3595ac82:notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md`, item (al) and the section it summarizes) decides which pilot reading counts by comparing the source a pilot ran with the source production will run. Equivalent: the pilot's reading stands and cannot be replaced. Not equivalent: the pilot is run again. That comparison must be fixed before any pilot runs, so that nobody interprets it after seeing a result.

A Codex CLI review of v7 (`E/plans/reviews/np1v7_814701f1_codex_review_2026-11-12.md`, findings P1-2 and P2-1) shows the draft's definition is not yet exact:

- "timestamps" and "paths under the attempt directory" name categories, not locations; the instruction contains shell commands with serialized JSON inside them, and stage requests contain nested identities;
- a permitted identity difference propagates into hashes the draft's list does not name: `native_shared_receipts.py`, about lines 446 to 468, puts `selection_sha256` into the receipt result and hashes that result into `receipt_carry.result_sha256`, which `native_shared_stage/__init__.py`, about line 331, exposes in later requests;
- helper output the model reads is not among the compared surfaces: `native_shared_receipts.py`, about lines 365 to 377, returns the initial receipt-check output;
- the recorder command in the instruction carries `--render-spec-json` with the raw runtime declaration, so literal values such as `deadline_seconds` and `budget_guard_usd` are model-facing content, not identities (`native_shared_render.py`, about lines 204 to 212 and 289 to 295).

The lead's decision: **the comparison is a script, and its list of permitted differences is a data file.** The amendment will point at both by commit and hash.

## What to build

On a new branch from the published candidate head (`git fetch origin` first; record the head you take):

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-equivalence-comparison-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-equivalence-comparison-20261112 \
  origin/codex/native-main-integration-20261112
```

One script under `scripts/` (kept and reviewed, not `scripts/adhoc/`), one data file beside it, and tests.

**Part 1, what the model reads.** Given two source trees (two commits of this repository, each exported to its own directory) and one fixed set of inputs, the script produces, for each tree, by calling that tree's own production functions offline: the complete rendered instruction; every stage request of a fixed synthetic sequence; the tool policy text and the permission expectation; the prompt assets and the schema closure; and every helper output the model reads on those saved inputs (at least the initial receipt-check output; find the others). It then compares the two sets byte for byte after applying only the transformations the data file lists.

- The data file names each permitted difference by **exact location**: which artifact, which field (a JSON pointer, also for JSON embedded in a command argument, which is parsed, not pattern-matched), and what kind of value is allowed to differ there (a sha256, an identifier, a timestamp in one named format, a path under the attempt directory).
- A dependent hash is never ignored: it is recomputed from the normalized content on both sides and must then agree. List each dependent hash and what it is computed from.
- Nothing is normalized by pattern across content: no "any timestamp", no "any path". Scientific content, prompt text, schema text and numeric settings are compared exactly. The runtime declaration's limit values are content.
- Three results, with distinct exit codes: **equal**; **not equal**, listing every difference with its location; **cannot decide** (an artifact could not be produced, or a difference sits at a location the data file does not cover in a field that looks like an identity). "Cannot decide" is a hold, never a pass and never a licence to re-run a pilot.

**Part 2, the acceptance and attempt rules.** The draft says this part is a written comparison that two reviewers confirm. Make it mechanical first: a second list in the data file of the rule-bearing objects (the gates, the floors and their thresholds, the receipt predicates, the attempt accounting, the cause classification, the registered limits and admission terms), each named as a module-level function, class or constant. The script reports whether each is byte-identical between the two trees, and lists every one that is not, with its diff. The reviewers then judge only the listed differences. Say how you established that the list is complete (for example: everything reachable from the completion gate and the attempt supervisor), and what the script does when an object on the list is missing in one tree (cannot decide).

**Demonstrations, as tests and as saved outputs:** the candidate against itself (equal); against a copy with a change that reaches nothing the model reads and no rule (equal); with one prompt asset sentence changed (not equal, the asset named); with a different deadline or guard in the runtime declaration (not equal, the recorder argument and field named); with a changed threshold (Part 2 lists it); with a different selection identity only (equal, the dependent hashes recomputed).

## Report as well

- The complete list of places where the runtime declaration, or a value in it, reaches something the model reads.
- Anything in what the model reads that you think should not be there (for example account or machine details inside the embedded declaration). Report it; change nothing.

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write. The script only reads the two trees and writes under an output directory it is given. Protected files are not changed.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-equivalence-comparison-20261112.md` with its JSON. Answer first: the commit; the script's and the data file's sha256; the number of permitted locations and of rule-bearing objects; the six demonstrations' results from saved output; and what the comparison still cannot see. Write a first version when the first demonstration runs.
