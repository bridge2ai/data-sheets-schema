Found in review round 3 of PR #4021, head 7f54079ec.

### github_assistant gates on d4d_assistant_edit.md, which neither the workflow nor any playbook loads, under a false reason (minor)

Location: `.claude/skills/d4d-generation-specificity-audit/scan.py`:2140

**Scenario.** Every .github/workflows/d4d_assistant_*.md is added as github_assistant model_facing with the reason "assistant instruction file (loaded by /d4d-assistant and /d4d-webfetch)" (2138-2140). The `@d4dassistant` workflow runs only `poetry run d4d api run` (d4d-agent.yml:257-262) and loads no instruction file. d4d-assistant.md and d4d-webfetch.md name only d4d_assistant_create.md. d4d_assistant_edit.md is named only by CLAUDE.md:290, whose names the scanner does not follow, and by notes. A GC token there therefore becomes a github_assistant violation on text the GitHub assistant never reads, and the committed JSON states a false reason for this surface. The glob is also missing from the PR body's and SKILL.md's account of what stays hand-kept.

**Verification.** The finding holds at 7f54079ec. I reproduced it.

**Code.** `scan.py:1975` globs `.github/workflows/d4d_assistant_*.md`. `scan.py:2138-2140` adds every match as `github_assistant`/`model_facing`/live with the reason "assistant instruction file (loaded by /d4d-assistant and /d4d-webfetch)". `Surfaces.add` (639-659) keeps the first reason. For `d4d_assistant_create.md` the drain had already given the reason "a playbook names". For `d4d_assistant_edit.md` this false reason is the only one.

**Nothing on a generation path reads `d4d_assistant_edit.md`.**
- **The workflow.** `d4d-agent.yml:257-262` runs only `poetry run d4d api run`. Its own comment at 196-197 says it "does not handle open-ended edit requests". Since #173 it has loaded no instruction file. The old `run-claude-obo` step was removed.
- **The playbooks.** `d4d-assistant.md:15,46,89` and `d4d-webfetch.md:6,23,49` name only `create.md`. `create.md` never names `edit.md`.
- **Code.** No Python file reads `edit.md`. The config key `docs.edit_instructions_path` (`d4d_assistant_deterministic.config:154`) has no reader.
- **Search.** I ran a gitignore-independent `/usr/bin/grep -rl`. The shell's `grep` is a ugrep wrapper with `--ignore-files`, so I bypassed it. Outside `data/`, `docs/` and the frozen copies under `notes/matched_cborg*`, `edit.md` is named only by `CLAUDE.md:290`, `.github/workflows/README.md`, the config's `docs` block, `gpt5/README.md`, notes, the audit itself, and `tests/test_profiles.py:1608`, which is a guard test.
- **CLAUDE.md is not followed by design.** SKILL.md's Limits section says the scanner does not follow what `CLAUDE.md` names. In the scanner's own model, `edit.md` is therefore reached by nothing: it is absent from `facts.named_files`, and its only role is `github_assistant`.

**Reproduction.** I made a git-archive copy of 8a19955b5 with its own `git init` at `/private/tmp/claude-501/review-4021-3/verify-edit-md/main`.
- **Baseline.** The HEAD scanner gives 154 violations and exit 1. The JSON is identical to the committed `notes/generation_specificity_audit_2026-09-30.json` apart from `commit` and `root`.
- **Committed record.** The JSON entry for `surfaces['.github/workflows/d4d_assistant_edit.md']` is `roles {github_assistant: model_facing}` with the false `why`.
- **Planted token.** Appending "When editing a CHORUS datasheet, keep its consortium list." gives 155 violations. The new one is at `d4d_assistant_edit.md:849`, context prose, `gates_in ['github_assistant']`. That matches the finding exactly.

**Effect today.** The 85-entry `tracked_without_reason` queue, which the PR body cites for #4018, includes `d4d_assistant_edit.md:546`: "bridge2ai" in a raw.githubusercontent URL, attributed model-facing to `github_assistant`. The report's approach table still describes `github_assistant` as "the `@d4dassistant` workflow and its instruction files" (`scan.py:78`, report line 15). The workflow has no instruction files.

**The hand-kept sub-claim holds with a nuance.**
- SKILL.md's "What is left by hand" list (lines 80-97) and the PR body's "A few lists stay hand-kept" sentence both omit the assistant glob.
- But SKILL.md's table row at line 102 does disclose it as what `github_assistant` is "discovered from".

**Not a duplicate.**
- #4016 asks the owner to reconcile the instruction files with the workflow. It does not address the scanner's classification or the false reason.
- The round-2 issue #4054 repeats the same false premise, that `/d4d-assistant` and `/d4d-webfetch` read `edit.md`.

**Mitigating factors.** Stale project docs (`CLAUDE.md:286-291`, the workflow README) still call `edit.md` a GitHub Actions assistant instruction file. `test_profiles.py` also treats it conservatively as playbook text. So flagging it could be defended as caution. Even so, the stated reachability reason is false and the approach it names is wrong.

**Severity: minor.** The false-positive gate is latent: no GC token is in `edit.md` today. The current output effect is one misattributed tracked hit and one false reason in the committed audit.

### Every run-controller module is marked as run as a script, so a __main__ demo in a helper that a controller only imports gates (minor)

Location: `.claude/skills/d4d-generation-specificity-audit/scan.py`:1956

**Scenario.** discover() adds every module in the controller set with Surfaces.add's default runs=True (scan.py:1955-1956), including modules found only as 'imported or staged by a controller'. Their `if __name__ == "__main__":` blocks therefore count. This contradicts SKILL.md ("nothing in a __main__ block counts for an approach that only imports the module") and the rule the PR used to close #4040.

**Verification.** The finding holds at head 7f54079ec. I reproduced it independently in /private/tmp/claude-501/review-4021-3/verify-main-runs/.

What the code does:
- At scan.py:1955-1956, every module in `controller_why` is added with `s.add(rel, "run_controllers", "run_shaping", "live", ...)` and no `runs=` argument. `Surfaces.add` defaults to `runs=True` (scan.py:643), so the module counts as run as a script.
- `run_controllers()` (scan.py:1370-1386) puts plain import targets into that same set, labelled "imported or staged by a controller".
- `scan_file` (scan.py:2305-2316) exempts `__main__` lines only for an approach that is not in `surface.runs`. Since `run_controllers` is always in `runs`, no controller-set module's `__main__` block is ever exempt.
- The other import closures behave differently. The api closure (1875), the native closure (2068) and the deterministic closure (2076) all pass `runs=False`.

What the scan reports at head:
- The full scan of the worktree gives 154 violations. A git-archive copy gives the same 154.
- There are 45 controllers, and all 45 have `runs_as_script_in == ['run_controllers']`. 35 of them are labelled "imported or staged by a controller".
- `audit_controls/transport.py` is only ever imported: by batch_native.py:25, audit_controls/native.py:31, registration.py:349 and 555, finalization_controls/registration.py, and the evaluation_controls modules. A grep that ignores .gitignore, run over everything except data/, found no `python transport.py`, no `-m` run and no `__file__` self-launch. transport_probe.py and evaluation_controls/registration.py name the file, but only to hash it.

Mutation (mutA, its own git init):
- I appended `if __name__ == "__main__":\n    DEMO_PROJECTS_4021 = ["CHORUS"]` to both transport.py and src/data_sheets_schema/chunking.py.
- The scan then reported 155 violations. The one new violation is transport.py:93: a `code_table`, `gates_in` `['run_controllers']`, `runs_as_script_in` `['run_controllers']`.
- The identical block in chunking.py:444 was marked `main_block: true` with `gates_in []`, so it is not a violation.

Docs this contradicts:
- SKILL.md:141-142: "nothing in a `__main__` block counts for an approach that only imports the module (it never runs that block)".
- SKILL.md:61-62.
- The PR body: "A `__main__` block counts only where its module runs as a script".
- The report's own text. scan.py:3509-3510 lists `__main__` blocks "of modules the gating approaches only import" among hits that do not fail, while the controller summary says "the rest are imported by a controller".

No test catches this. `test_a_main_block_counts_only_where_the_module_runs_as_a_script` uses a hand-built Surface. No test checks `runs` for controller-closure members. No recorded issue covers it either: #4040 was field_prioritizer, and none of #4008-#4020, #4041 or #4083-#4085 is about this.

Why minor and not higher:
- It is latent. 18 controller modules have `__main__` blocks, and none of those blocks contains any token hit today, so the 154 count and the verdicts are unaffected.
- It is a false positive, so it fails loudly rather than hiding anything.

A note for whoever fixes it: a blanket `runs=False` for import-closure members would be wrong. bounded_stream.py:49 and bounded_transport.py:113 relaunch themselves as worker scripts via `sys.executable` and `__file__`, so their `__main__` blocks do run in the generation path. The fix has to keep `runs=True` for staged files, self-launched workers, seeds and drivers, and drop it only for modules that are imported and nothing more.
