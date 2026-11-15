The environment manifest's repeated live filesystem census is a measured major preparation cost. Stop for a design decision; no production fix, fixture restamping, pin rotation, or successful public launch is claimed.

The first completed fixture-building phase took 526.575 seconds locally. It called manifest verification 15 times, totaling 439.849 cumulative seconds. A cached full verdict still runs a complete light census. This is not repeated full payload hashing alone. The source change for issue 6243 only changes window parsing and checks; it adds no environment traversal. The comparison against 725a9e5fe shows the manifest is new, while the guard and synthetic evidence fixture are byte-identical. No historical checkout timing was run.

Scope and limits: the full cProfile run was interrupted after its first manifest write and during preparation, preserving its profile. The lower-overhead phase run was stopped at the design boundary after the first fixture builder completed, during the second manifest write. Its external process-group watchdog recorded the termination in phases.log. Consequently, the exact full make_case duration, capture-to-launch interval, and allocation of every second of the CI failure remain unmeasured. These are partial diagnostics, not a completed public-case reproduction or a demonstrated speedup. Local CPython 3.13 on macOS differs from CI CPython 3.12, and another local Codex task was running.

The measured environment contains 281 third-party distributions, 35849 RECORD entries, 566336578 verified payload bytes, and 9 unowned files. The primary virtual environment was copied with cp -R into the assignment scratch directory. Only the copied project path file was redirected; its adjacent backup and undo instruction are in isolation.json. The primary virtual environment was not changed.

Completed phase measurements follow. Rows overlap: caller times include callees, so do not sum the table. The table is generated from phases.jsonl by scripts/adhoc/summarize_public_stale_20261115.py.

| Phase | Completed calls | Cumulative seconds | Maximum seconds |
| --- | ---: | ---: | ---: |
| native_environment_manifest.py:_light_live | 16 | 364.927 | 25.811 |
| native_environment_manifest.py:generate | 3 | 165.325 | 70.353 |
| native_environment_manifest.py:verify | 15 | 439.849 | 118.857 |
| native_environment_manifest.py:write | 1 | 168.275 | 168.275 |
| native_execution_registration_v2.py:prepare | 5 | 237.189 | 51.407 |
| native_shared_controller_orchestration.py:compose | 1 | 153.368 | 153.368 |
| native_shared_controller_orchestration.py:reconstruct_composition | 1 | 143.173 | 143.173 |
| native_shared_fixture.py:build_native_fixture | 1 | 526.575 | 526.575 |
| native_synthetic_evidence.py:runtime_for | 1 | 0.087 | 0.087 |

The partial cProfile recorded 11,050,979 lstat calls with 80.505 seconds of self time; pathlib.resolve accumulated 108.588 seconds, and the first manifest write accumulated 205.226 seconds under full profiling. These rounded values are retained in baseline-profile.txt and the structured partial_profile data. The lower-overhead trace measured the first manifest write at 168.275 seconds. Pure metadata validation memoization would not remove the dominant repeated ancestor traversal.

Recommended decision: authorize a separately reviewed census-scoped path-resolution design, with fresh RECORD and metadata reads, every included file checked, exact implementation identity, and end-of-census revalidation of all reused ancestor and symlink identities. Require adversarial ancestor replacement, symlink retargeting, same-size payload edits, metadata changes, and implementation changes before acceptance. The decision is whether that snapshot proof is an acceptable replacement for repeatedly resolving identical ancestor chains for every entry. Do not simply reuse a successful live census across calls, key a new verdict only on stat data, or move freshness checks. Also evaluate seeding the existing full-verification memo from write's first successful generation, retaining its race checks; that is a proposal, not an implemented or measured improvement. A patch would need a scanner source-pin proposal and the lead's review; no pin is changed here.

Observation order: tests/utils/native_synthetic_evidence.py authority_for first verifies registration, constructs and activates the invented owner word, reconstructs capture authority and reserves the synthetic slot. It then stamps capture_now immediately before constructing the invented event, claim, observations and capture manifest. current_guard_preparation runs afterward, and launch_case calls synthetic_launch after make_case returns. The production capture loop in src/data_sheets_schema/native_subscription_capture.py stamps a rate_limit_event when it is read, before guard preparation and dispatch as well. Thus the fixture already follows the production observation-before-guard order. Moving its timestamp after guard reconstruction would conceal real elapsed time, not correct fixture parity. src/data_sheets_schema/native_u4b_policy.py registers max_age_seconds as 1200. Freshness, margins, all windows and deadlines are unchanged.

CI confirmation: correction failed with stale-or-future-dated observation after 2421.65 seconds; pending after 3017.04 seconds; variant after 3048.60 seconds. All three logs are saved. Pending job 132959954885 and variant job 132959954692 were fetched after completion using read-only gh api. Total test duration is not observation age; the logs do not establish the missing capture-to-launch breakdown.

Validation: 281 focused manifest, mode, scanner, registration-shape and subscription-guard cases passed, with JUnit evidence. The wider suite was interrupted after its real registration rederivation test completed and the next parameterized fixture began. Pytest then raised a tmp_path stash KeyError during interruption cleanup; that batch has no clean final summary and must not be reported as a passing full registration suite. The complete shared-registration matrix remains unverified. Collection found 27521 tests and the three expected missing fairscape_models.rocrate errors. No complete public case was launched locally: preparation alone is already expensive, and this assignment stops for the design ruling. The diagnostic runs were bounded by an external process-group watchdog; no inherited alarm was used. No Claude binary, provider, capture, production launch, GitHub write or push occurred.

Files changed are diagnostic scripts and this report/data pair only. The four protected files, production code, tests, prompts and controller pins are untouched. The lead should record the unresolved census-design finding as an issue; this helper has no GitHub-write permission. There is no review-only pin diff because no pinned implementation changed.

Commit blocked: git add could not create the worktree index.lock because the sandbox returned Operation not permitted. Per assignment, no escalation or commit was attempted after that refusal. The following files remain uncommitted on codex/public-stale-20261115:

- scripts/adhoc/profile_public_stale_20261115.py
- scripts/adhoc/summarize_public_stale_20261115.py
- notes/reviews/public_stale_20261115.md
- notes/reviews/public_stale_20261115.json

Reproduce the retained summary from the worktree root:

```text
PYTHONPATH=$PWD/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/isolated-venv/bin/python scripts/adhoc/summarize_public_stale_20261115.py /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115 --report
```

The profiling producer is scripts/adhoc/profile_public_stale_20261115.py. It provides configure, bounded, phases, and cProfile modes. Use a fresh scratch case name for another cProfile run; the phases mode also consumes a fresh phases directory and must not overwrite retained evidence. The executed watchdog commands, elapsed times and return codes are saved in baseline.log, phases.log, tests-focused.log and collection.log. The interrupted wider pytest command is documented in the assignment session; tests-baseline.log preserves its output.

Evidence paths and SHA-256 values are recorded in /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-public-stale-20261115/notes/reviews/public_stale_20261115.json. Retained evidence files:

- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/isolation.json
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/baseline.prof
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/baseline-profile.txt
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/baseline.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/phases.jsonl
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/phases.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/tests-baseline.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/tests-focused.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/tests-focused.xml
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/collection.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/wide-collection.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ci-correction.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ci-variant.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ci-pending.log
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/ci-public-status.jsonl
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/comparison-numstat.txt
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-public-stale-20261115/guard-6243.diff
