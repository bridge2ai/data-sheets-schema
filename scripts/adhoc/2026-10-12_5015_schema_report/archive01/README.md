# Completed-profile comparison report

Purpose: portable evidence for #5015, dated 2026-10-12; no PR yet. This helper reads saved metadata and pinned source text using only the standard library. It runs no tests, imports no project modules and executes no benchmark.

Do not run until root confirms profile03 has terminated. The explicit `--terminal-confirmed` flag records this operator prerequisite; successful final profiler state and JUnit are additionally required. Root may supply `--baseline-after` and `--candidate-after` manifests where available. Without them, the report says exactly which contemporaneous after evidence is absent. It never equates the profiler's installation-time source table with an after snapshot.

```sh
python3 scripts/adhoc/2026-10-12_5015_schema_report/compare_profiles.py --root /private/tmp/d4d-performance-implementation-20261012 --baseline /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profile-run01 --candidate /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profile-run03 --abba /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/schema-admission-abba01-results/summary.json --terminal-confirmed --output /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/schema-event-replay-comparison01.json
```

The report requires one passed target case, all three passed pytest phases, restored wrappers and no observer errors in both runs. It checks exact event ID/parent/function/exception/caller order,19 execute calls with6 successful returns,2,341 fresh captures and2,032 current assertions. The two complete test files must have identical hashes; their literal seven-mutation loop is checked independently by AST. Bundle/context are correctly distinguished from the five mutation cases entering `execute`.

Only the two admitted source files may differ between runs. Current source hashes and optional after receipts join the recorded inputs. All four ABBA outputs must agree, source/interpreter bindings must match and its old/new/new/old order must be exact. Raw times and host/load context are preserved. Output evidence uses filenames, labels and hashes plus repository-relative source paths, without temporary root paths, usernames, process IDs or thread IDs. It makes no statistical or scientific claim and does not sum overlapping timings.
