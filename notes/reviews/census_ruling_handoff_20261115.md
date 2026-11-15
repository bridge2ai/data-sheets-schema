# Census ruling implemented; source-commit proof blocks the complete after measurement

The approved implementation is present, but uncommitted because Git could not create the worktree index lock. The complete local baseline make_case took 1314.544 seconds. A complete after time and capture-to-launch interval are not available: the patched run stopped at the unchanged source-commit proof after 75.682 seconds. Its first manifest write completed in 44.526 seconds, compared with 164.212 seconds for the baseline's first write. This is a measured phase improvement, not a demonstrated whole-case speedup or successful public launch.

At baseline make_case return, capture-to-ready was 59.528 seconds, leaving 1140.472 seconds against the unchanged 1200 second maximum age. That is not the capture-to-dispatch interval. The patched public correction canary refused before capture or launch at the same uncommitted-source proof, so its freshness margin remains unmeasured.

Validation: 278 focused manifest, mode, registration-shape, guard and adversarial tests passed. The final-source installed-environment cost canary passed: write 44.551 seconds with one generation, cached full verification 10.632 seconds with no generation, and light verification 10.367 seconds with no generation. The first real registration and public correction canaries both refused the uncommitted source. On rerun, registration confirmed that refusal; the public case instead refused a changed /Users/marcin ancestor identity during generation. This operational sensitivity is recorded without weakening the settled check. Do not report the complete registration matrix or public lifetime as passing; the failed canaries did not authorize an expensive matrix fan-out. Collection found 27537 tests and the 3 expected missing FAIRSCAPE-model collection errors. Scanner checks had 2 passes and 7 failures attributable to its unchanged manifest pin.

Pin proposal only: in .claude/skills/d4d-generation-specificity-audit/scan.py, the v3 entry for src/data_sheets_schema/native_environment_manifest.py should change from 790040b275d4d67aed40a6805835bb688030ec0ef3e7e004984aadcf4a2c10b7 to 6af3e242659a04fb84c424e1ca5279458bfc9974d12f392f2ba2444227b5f937. The scanner was not edited. The new digest was computed from the actual production file, not the temporary candidate.

Implemented behavior: each generate or light census has a fresh context-local directory resolver. It caches directory resolution by path string, records directory and symlink identities and symlink targets, and rechecks them before returning. Every included hashed payload is still opened, sized and hashed during full generation; fresh metadata/RECORD reads and the unowned scan remain. No live census survives a call. Write captures the first successful generation's file fingerprints, checks them with a fresh light census, persists the exact canonical manifest, seeds only an absent full-memo key, and invokes full verification to reread the persisted pin and run another live census. The key includes implementation content identity, and the loaded implementation refuses source drift. Existing successful fingerprints and cached refusals cannot be replaced by recreating an identical manifest pin.

Adversarial coverage includes mid-census ancestor replacement, symlink retargeting, same-size edits, metadata and RECORD changes, an added unowned file, changed implementation bytes, changes after generation and during publication, census disposal, ancestor reuse counts, and preservation of existing memo verdicts. A separate read-only review found the initial candidate's overwrite of existing memo entries; it was corrected and regression-tested. The lead should file the issue record in notes/reviews/census_ruling_findings_20261115.md. This helper made no GitHub write.

The first fixture's 15 verify calls are retained: one after manifest publication; two around preparation; six during composition; and six during reconstruction. Each composition operation calls verify_preparer before and after rendering. Each verify_preparer checks the declared pin and invokes preparation, whose two checks bracket fresh input/source/render work. The first check binds the declared pin; the later checks prove the live path and reconstruction still agree. These are distinct before/after boundaries, not proven identical checks in one step. Each project's preparation follows this path, and native_shared_registration_orchestration._recheck_verified explicitly forces full verification again at dispatch. No call was removed. The complete baseline make_case recorded 57 verify calls; the original 15-call observation described its first fixture only.

Timing scope: both measurements used the existing isolated venv and the same phase profiler from the assigned worktree. The baseline source commit and source digest are saved in before-ruling-canonical/source-commit.txt and source-sha256.txt. Baseline early phases overlapped small candidate validation jobs, and host contention varies; do not infer a controlled overall speedup ratio from the first-write comparison. Earlier failed harness runs are retained: a relative interpreter spelling refused canonical-path validation; a candidate runner briefly included its script directory in the import inventory; and creating a sibling scratch directory during a census correctly refused its changed ancestor identity. These are not passing timing results. No primary venv, freshness value, deadline, window, fixture capture order, protected file, prompt pin or controller pin changed. No native binary, provider, production capture, launch, push or GitHub write occurred.

The first two real canaries and the after profile refused with:

```text
consumed source differs from the reviewed commit: src/data_sheets_schema/native_environment_manifest.py
```

The first canary run also reported that this helper created the summary report files under notes during the run. The individual cost assertion passed and both source-bound tests reached the source-commit refusal, but that run is not a clean whole-suite result. A second run of only the source-bound canaries, with report writing paused, removed that notes warning. Registration again refused at the source-commit proof; the public case instead refused during its first full generation because /Users/marcin changed identity during the census. The diagnostic does not identify the changed stat field or the actor. The required full ancestor identity check includes directory timestamps and therefore can conservatively refuse broader filesystem activity. This behavior was not weakened. The operational finding is recorded for the lead alongside the fixed memo finding; the full public lifetime remains unverified.

Commit attempt: git add returned Operation not permitted while creating /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.git/worktrees/codex-public-stale-20261115/index.lock. Per the assignment, there was no escalation or alternative-index workaround. The lead needs to commit the listed files, review and apply the scanner pin proposal, then rerun the after profile and public/registration canaries in fresh scratch locations. That remaining integration work is required before claiming the original stale-launch problem is resolved.

Files left on codex/public-stale-20261115:

- notes/reviews/census_ruling_20261115.json
- notes/reviews/census_ruling_20261115.md
- notes/reviews/census_ruling_findings_20261115.md
- notes/reviews/census_ruling_handoff_20261115.md
- scripts/adhoc/implement_census_resolution_20261115.py
- scripts/adhoc/measure_public_census_20261115.py
- scripts/adhoc/profile_public_stale_20261115.py
- scripts/adhoc/summarize_census_ruling_20261115.py
- scripts/adhoc/test_census_candidate_20261115.py
- scripts/adhoc/write_census_handoff_20261115.py
- src/data_sheets_schema/native_environment_manifest.py
- tests/test_native_environment_census.py
- tests/test_native_environment_cost.py

Before is complete; after stops at the source-commit proof. Zero calls means no completed call.
Phase durations include callees; rows must not be summed.

| Phase | Before calls | Before seconds | After calls | After seconds |
| --- | ---: | ---: | ---: | ---: |
| native_environment_manifest.py:_light_live | 59 | 996.170 | 4 | 38.749 |
| native_environment_manifest.py:generate | 4 | 178.148 | 1 | 24.835 |
| native_environment_manifest.py:verify | 57 | 1096.710 | 3 | 30.095 |
| native_environment_manifest.py:write | 2 | 262.030 | 1 | 44.526 |
| native_execution_registration_v2.py:prepare | 5 | 188.655 | 1 | 22.134 |
| native_execution_registration_v2.py:prepare_synthetic | 14 | 480.563 | 0 | 0.000 |
| native_shared_controller_orchestration.py:compose | 2 | 213.037 | 0 | 0.000 |
| native_shared_controller_orchestration.py:reconstruct_composition | 3 | 321.439 | 0 | 0.000 |
| native_shared_fixture.py:build_native_fixture | 1 | 452.680 | 0 | 0.000 |
| native_shared_registration_orchestration.py:synthetic_registration | 1 | 216.578 | 0 | 0.000 |
| native_shared_registration_orchestration.py:verified | 5 | 314.552 | 0 | 0.000 |
| native_subscription_capture.py:_current_authority | 2 | 134.427 | 0 | 0.000 |
| native_synthetic_evidence.py:authority_for | 1 | 257.642 | 0 | 0.000 |
| native_synthetic_evidence.py:bound_permission_for | 1 | 3.097 | 0 | 0.000 |
| native_synthetic_evidence.py:runtime_for | 1 | 0.036 | 0 | 0.000 |
| test_native_shared_execution.py:make_case | 1 | 1314.544 | 0 | 0.000 |

Reproduction and retained evidence:

- scripts/adhoc/implement_census_resolution_20261115.py records the transformation from the original pinned source; it refuses another input hash. Do not rerun it in place on the already-patched source.
- scripts/adhoc/profile_public_stale_20261115.py supplies the external process-group watchdog and phase measurement. The watchdog command arrays and return codes are saved in each run.log.
- scripts/adhoc/measure_public_census_20261115.py observes make_case and launch boundaries without changing gates.
- scripts/adhoc/test_census_candidate_20261115.py validated the generated candidate while the baseline source remained unchanged. Its temporary generated file is under the ignored .temp/census directory; the producer is retained on the branch.
- scripts/adhoc/summarize_census_ruling_20261115.py generates notes/reviews/census_ruling_20261115.json and its Markdown phase table from saved logs.
- scripts/adhoc/write_census_handoff_20261115.py generates this new handoff section from that summary, JUnit and cost evidence.
- Scratch root: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115
- Successful cost artifact: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-runs/canaries/test_installed_manifest_modes_0/manifest-cost.json
- Focused JUnit: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-focused.xml
- Canary JUnit: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-runs/canaries.xml
- Public timing artifact: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-runs/public-timing.jsonl
- Canary rerun JUnit: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-runs/commit-boundary.xml
- Canary rerun timing: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-runs/commit-boundary-timing.jsonl
- Scanner JUnit: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-runs/scanner.xml
- Final collection log: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ruling-final-collection.log

The JSON summary records SHA-256 values for the retained timing and test evidence. The public timing artifact has no launch-entry record because preparation refused before that boundary.
