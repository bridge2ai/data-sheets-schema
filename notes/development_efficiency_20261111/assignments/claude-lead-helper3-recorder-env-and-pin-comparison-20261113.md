# Assignment to Codex helper 3: a short recorder line, and the stratum gate as a comparison of pins

From the Claude lead, 2026-11-13. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper3-launch-recheck-followup-20261113.md` (issues #6047 and #6048).

## Standing

Your comparison handoff is accepted as work done (`handoffs/codex-h3-equivalence-comparison-20261112.md`, SHA-256 `f6eded41480f27ccdbafb6d7b657bb79ac76517c813bcf6507ad67ad3fdf7325`; commit `e82c36abdb2b25a55b71c2e67552edc7a7c1f8b5`). Two things came out of it.

**Your exposure note is now issue #6065.** The model runs the prescribed recorder command itself, and the tool policy admits only the exact registered command; in your replay the recorder's `--render-spec-json` argument is about 20,700 characters of a 115,709-character instruction. The first direct CHORUS canary was disqualified at its recorder line after a complete generation (#2282), and respelled commands were seen (#2398).

**An independent review of the comparison** (`E/plans/reviews/native_equivalence_e82c36ab_codex_review_2026-11-13.md`, SHA-256 `47af856a4aa36c672ca25d2aa6d6f58b9bfbabbfa93c460fc0ee0a51c3c52918`) says it is a useful synthetic regression comparator but does not establish registration equivalence: it never sees the actual registrations, the executable dependency boundary is open, and five more findings (filed as #6066 to #6073). **The lead's decision:** the stratum's gate becomes a comparison of pins, not a replay. Your inventory already treats every module-level object of the package as rule-bearing, so any substantive package change is "not equal" anyway; the replay adds little to byte identity of what the registration pins, and costs most of the review findings. The replay stays as a development aid.

## Part 1: the recorder line (#6065), before anything else in this file

On a new branch `codex/native-recorder-env-20261113` from the published head (`git fetch origin`; at least `8760de5efe88b5af62e9d77e6335fa7e248017b6`, plus your #6047 and #6048 commits if they are not yet there: say how you carried them).

- The recorder receives the render specification through the environment the controller constructs for the native process, the same way it already receives the prompt text (`--prompt-text-env D4D_LAUNCH_INSTRUCTION`): for example `--render-spec-env D4D_RENDER_SPEC`. The prescribed line in the instruction, the command table, the system guidance and the permission expectation becomes short and fixed.
- The recorder still verifies the specification it reads against the registration, exactly as strictly as now; a missing or different value refuses.
- Read #2282's notes on what the runtime admits (a literal environment-variable name passed as an argument was admitted; a `${…}` expansion was refused; an apostrophe in the specification was refused in every form) and say how the new line avoids each.
- Name every model-facing artifact that changes and confirm from the replay aid that nothing else the model reads changes. No protected file may change; if the change needs one, stop and propose.
- Tests: the short line is what the model is given; the recorder refuses a missing, empty or altered specification; the synthetic public path still records. Run the touched test files whole.

## Part 2: the pin comparison (the stratum gate)

On a new branch `codex/native-pin-comparison-20261113` from Part 1's head. One script under `scripts/` with tests:

- **Inputs:** two registration packets (the reference run's and a candidate's), each first verified by the production validators; nothing from either source tree is executed.
- **Rule:** equal if and only if every pinned file (package source, prompt assets, `.claude` command and agent files, schema closure, the closed dependency registry), the Claude Code binary's sha256, the base system-instructions bytes, the selection-bounds policy and every registered value are byte-identical, except a fixed list of per-run fields kept in a data file beside the script. Start the list from what a registration actually varies: the project's own inputs (name each field: bundle, chunk manifest, source-manifest entry, omission context, scope), registration, selection, job and attempt identifiers, timestamps, paths under the attempt directory, and the effective system prompt's command guidance after those identity substitutions (P2-1 of the NP1 v8 review).
- **The floor transition** (pending for a pilot, a registered numeric floor for a production cell) is the one permitted value change, validated separately: the candidate's floor must be exactly the value and basis (`receipted_part`) the amendment's arithmetic gives, supplied as an input with its own hash.
- **Three results:** equal; not equal, listing every differing pin; cannot decide (a packet fails validation, a field is neither pinned-equal nor on the list). "Cannot decide" is a hold.
- **Binding:** the result records the script's and data file's sha256, both packets' sha256 and the floor input's sha256; the data file is versioned and a changed list is a new version.

## Part 3: the replay, kept as an aid

Leave `native_equivalence_compare.py` as a development aid that shows whether a candidate change touches what the model reads before a reference exists. Apply only the cheap fixes so that it does not mislead: a rule-object difference is "not equal" (#6068); the permission expectation is supporting evidence, not model-read content (#6069); an unexpected helper exception holds (#6073). Document in the script that it is not the stratum gate. Do not do the larger findings (#6066, #6067, #6070 to #6072) for the aid.

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write; protected files unchanged; guard v1 byte-identical.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-recorder-env-and-pin-comparison-20261113.md` with its JSON. Answer first: Part 1's commit, the new recorder line as the model sees it and its length, and every model-facing artifact that changed; Part 2's commit, the script's and data file's sha256, the list of permitted per-run fields, and the results on: a packet against itself, against a packet for another project, against one with a changed prompt asset, with a changed binary hash, and with a wrong floor value; Part 3's commit. Write a first version when Part 1 is committed.
