# Assignment to Codex helper 3: the production registration packet for the native CHORUS canary, built and rehearsed as far as no authorization is needed

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your handoff on the import-origin failures and CI time is accepted. The lead's reading of it:

- The isolation fix (`f25230fe1`) stands. Its remaining 18 of 37 ids fail for the reason you gave, the protected files, and will be re-run where those are applied. Helper 1 does that.
- The scanner test's five-fold time is mostly the same failed discovery repeated in every test. Helper 1 is repairing the discovery failure itself. Your proposal to cache the failure in the test helper is **not** taken up now: once discovery succeeds it is cached already.
- No request for a CI capacity change goes to the owner yet. The weights are refreshed from a completed run once the suite passes.
- Commit your weights supplement and its test change on your branch as they are, with a message saying the measurements come from a failed run with two cancelled shards. Then stop work on that branch.

Your six findings H3-F1 to H3-F6 are noted; the lead files what needs filing.

## The next task, and why

Nobody has ever built a production registration for the native arm. The launch commands consume a registration, a runtime declaration, a review bundle, an owner statement, a coded word, an account-choice document and CI evidence; the source has validators and library functions for them, and the tests build them from fixtures with invented reviewers and CI. The critical path calls this gate G13 (`handoffs/codex-native-critical-path-20261112.md`, the rows G13 and G17 and the section "D117 probes and production packet readiness"). An inventory of the launch commands' inputs and of every builder-like function is in `handoffs/agy2-native-launch-inputs-20261112.md` and its JSON.

The canary is CHORUS, one run, under amendment N1 (draft v12: `git -C P show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`; read N1.1, N1.2, N1.3, N1.5 and N1.9).

## Where you work

A new worktree from the candidate's current head:

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-packet-builder-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-packet-builder-20261112 \
  058de60779412150c529e41c86c5cfe9047014da
```

Scratch and outputs go under `E/scratch-h3-packet-builder-20261112/`. New files only: do not edit existing source or tests. Helper 2 is changing the review bundle and owner statement (a new bundle version 3 and terms version 2, on `codex/native-launch-sequence-20261112`); build against the versions on your branch and keep the bundle and statement steps in their own module so they can be switched.

## Part 1: the map (data first)

For every document a production launch needs, from the source on your branch: its kind and version, the function that builds or prepares it, the function that validates it, every input it takes, and where each input comes from in production (a file in the repository, a manifest entry, the pinned binary's bytes, a probe's saved output, an owner's act, a review). Mark each input as one of: available now; needs the merged source; needs a real-binary probe; needs an owner act; needs an independent review. Write this as a JSON file and a table made from it.

## Part 2: the builder, as far as it can go without authorization

One script under `scripts/` on your branch (not `scripts/adhoc/`: it is meant to be reviewed and kept), with tests, that:

1. takes its inputs as explicit arguments and files, never from the environment;
2. calls the production prepare and validate functions; it re-implements none of them;
3. builds every document that needs no probe, no owner act and no review, for the real CHORUS inputs the repository declares (the source manifest, the bundle, the chunk manifest, the schema closure, the prompt assets, the profile);
4. stops with a plain message at the first document that needs a real-binary probe, an owner act or a review, naming exactly what is needed and the command that produces it;
5. never executes the Claude Code binary, never touches the network, and writes only under the output directory it is given, refusing to overwrite.

Reading the pinned binary's bytes to hash them is allowed. Executing it is not.

## Part 3: the rehearsal

Run the builder on the real CHORUS inputs in an isolated environment, as far as it goes, and keep the outputs under your scratch directory. Then, with the test suite's synthetic profile and fixtures clearly labelled as rehearsal and not as authority, show the rest of the chain end to end in a test: the remaining documents, the three launch commands' argument plumbing, and the stop before any reservation. Fixture reviewers and fixture CI must be impossible to mistake for approvals: label them in the bytes.

## Part 4: the runbook

A file `notes/native_canary_runbook_DRAFT_20261112.md` on your branch: every step from the merged source to the launch, in order, with the exact command, who performs it (worker, lead, owner), what it needs, and what it produces. Mark each step that needs the owner's authorization.

## Bounds

As in the context file. In addition: no real-binary execution of any kind, no probe, no capture. The protected files stay equal to main, so some production functions will refuse on your branch for the reason you already found; record exactly where, and do not work around it.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-registration-builder-20261112.md` with its JSON: answer first (how far the builder gets on real CHORUS inputs, where it stops and why, what the rehearsal proves and does not prove), then the map, then the test counts from saved output. Write a first version when Part 1 is done.
