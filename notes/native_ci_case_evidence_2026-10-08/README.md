# Ordinary CI retention for two synthetic native cases (#4675)

At PR #4659 head `cfe61d29afc6edbf79cf6970e014fd951bee6d15`, CI run
37752376080 reported the existing native-attempt deadline as the first stop in
both full synthetic acceptance tests. Neutral failed after 996.515 seconds of
test time and omission after 990.305 seconds, each with phase 1 and core sealed
but no completed assembly. These durations include test setup/finalization.
Neither result identifies the expensive operation. The two shard artifacts
contained only JUnit; their 11.4 MB captured transcripts, control logs and case
files were unavailable for independent diagnosis.

The ordinary shard command now explicitly enables `utils.native_ci_evidence`.
Without `--native-ci-evidence-root`, the plugin performs no source reads,
capture or output writes. It does not select, filter, reorder or rerun tests.
Only these exact existing nodes can trigger case retention:

- `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`
- `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`

After their teardown report, the plugin uses their fixture-owned `tmp_path`
and the fixed `native26` or `native26-omissions` child. It creates a new output
under an external run/attempt/shard directory, then a worker directory and exact
node digest. Existing destinations refuse; no source or earlier evidence is
overwritten. The upload runs with `always()` and a 14-day retention period.
Missing upload files produce a workflow warning, not an invented passing case.

Each case manifest retains setup/call/teardown outcomes, selected source
head/tree and working-file hashes, the unchanged declared 900/180/120-second
limits, and before/archive/after inventories of file bytes and modes. Source
identity covers the named working files; it is not complete imported-code or
environment attestation. The source checkout and referenced schema/dependency
files outside the case are not copied by following paths in registration JSON.
Their available declarations remain in the captured case.

`retained` means that the snapshot bytes were stable during capture. It says
nothing about case completion or successful runtime/scientific acceptance.
`case_completeness` remains `not_assessed`. A fixed artifact availability roster
distinguishes regular files, links, missing files and uninspected/unavailable
cases, so an early partial directory cannot masquerade as complete evidence.
The inventories retain every case entry, including additional request/response
files. Cases exceeding 512 MiB of regular-file content or 10,000 entries refuse
with an explicit capture error; content is not silently truncated.

Directory traversal and regular-file reads use held descriptors and
`O_NOFOLLOW`; links are inventoried and archived as links. The collector does
not follow external links, JSON authority references or unrelated temporary
directories, and does not export process environments or invoke providers.
Nonregular files refuse. Before/archive/after disagreement remains an explicit
`capture_changed` outcome. Existing test failures and pytest exit codes remain
unchanged when capture succeeds or fails. Per-worker summaries distinguish
observed nodes from nodes not observed in that worker; another shard or worker
may have run them. A worker crash may leave only partial diagnostic output.

The two acceptance test bodies, production modules, helper commands,
registered deadlines, assertions and shard scheduling remain unchanged.
The dedicated `review/4354-offline-acceptance` workflow keeps its separate
serialized acceptance behavior. This diagnostic successor depends on the
unmerged native implementation in PR #4659 and is not a standalone main-based
adapter delivery. #4537 and #4354 remain open until their actual acceptance
obligations pass; all human/scientific/provider holds remain in place.

## Validation status

The first focused coordinator run at
`0893589bc8153a4416bf9c6f1370dd5771d01da2` completed with 34 passed and one
failed test (6.26 seconds reported by the coordinator; no warnings). The
failure was a test assumption that a symlink always has mode `0777`; this macOS
fixture's actual `lstat` mode was `0755`, which the implementation correctly
preserved. Under #4677, the assertion now uses the actual link mode and also
checks that mode in the archive. External-byte and non-dereference controls are
unchanged. No production behavior changed; a fresh focused run is pending.

The focused controls cover failed and partial cases, missing fixtures, collisions,
mode/byte drift, bounded refusal, unrelated-node exclusion, symlink isolation,
separate workers and preservation of original test outcomes. No native test,
provider call, diagnostic replay or CI rerun has been performed for this change.
Review issue #4677 adds an explicit archive root-directory member with its
captured mode, including for empty or early partial cases; the inventory must
describe actual archived entries.
