# Fresh full-schema synthetic checkpoint (#4618)

This driver prepares a **new fictional checkpoint** on recovered source
`0125eebbc214d0907c3b69d23758cd9441911a78`, then measures four actual reconstruction
operations plus two refusal controls. It does not replay the incomplete historical capture, launch a
native/provider/helper process, score a dataset, or evaluate the 900-second
acceptance requirement. It does not reconstruct unavailable source `4366dc…`.

The implementation and independent boundary tests were reviewed before
fixture construction or measurement. The original v1 preparation04 completed
in 514.869 seconds, retaining 68 case files and 1,194 imported-code pins. The
subsequent monolithic measurement01 reached its 600-second bound (parent wall
600.046644 seconds, child exit -9, no stdout or stderr, `result=null`). Parent
checks confirmed unchanged checkpoint, preparation report and original inputs.
Those artifacts remain untouched; the empty output cannot identify the stalled
operation or establish that any individual pair completed.

The v2 protocol below addresses [#4636](https://github.com/bridge2ai/data-sheets-schema/issues/4636)
with six independently selected pairs and offline collection. Fresh v2
preparation05 and all six selected pairs completed, followed by a complete
offline collection. The same-driver identity rule was retained; preparation04
was not reused. The measured source was commit
`9b5bfdaf27bfb0509dbffa2b470d9fb712fd223e`.

The driver imports the committed [retained-prefix utility](../native_profile_recovery_2026-10-07/trace_prefix_profile.py)
from this repository, requiring SHA256
`4097c8dff6e921b146feb49854b67487adc54b5a4da7943e22c9293849df01bf`.
That utility verifies all 9,214 recovered regular source files, the original
Actions archive and uploaded manifests, and all 83 retained case files. The
historical capture remains incomplete and unchanged. The two opaque historical
Git submodule identities are recorded; importing an unregistered source is
refused.

## Completed diagnostic results

The four-module suite passed **371 tests**, with no failures, errors or skips.
JUnit records 11.273 seconds; the coordinator reported 11.40 seconds at the
console. The third independent Codex static review approved the corrected
source with no material findings. The first two reviews and their findings
remain pinned in [validation.json](validation.json), alongside the earlier
failed preparations and monolithic timeout. JUnit establishes recorded outcomes;
the test-to-source association is separately recorded coordinator provenance.

Fresh preparation05 completed in **648.047 seconds** under its unchanged
900-second diagnostic bound. It retained 68 case files totaling 25,352,291
bytes and 1,194 imported-code identities. The checkpoint contains the consumed
receipt and first worker of three, with the next advance admitted but not
published. It remains an incomplete execution checkpoint.

All six separately invoked pairs completed within their individual 600-second
diagnostic bounds. Four pairs returned matching complete typed results; both
negative controls refused with matching complete exception graphs. The
collector independently reconstructed the denominator as **6/6 complete**, with
no failed or missing operations. Saved payloads, their hashes and all six
collection links were independently compared again while writing this note.

| Operation | Plain CPU / wall (s) | Instrumented CPU / wall (s) | Parent wall (s) | Both arms |
| --- | ---: | ---: | ---: | --- |
| `_load_live` | 20.747 / 23.463 | 132.332 / 149.361 | 261.421 | returned |
| `CallbackAdapter._run_fresh_owner` | 21.147 / 24.439 | 128.721 / 134.384 | 294.148 | returned |
| `decision_fresh_loaded_run` | 4.571 / 4.638 | 31.999 / 33.522 | 144.996 | returned |
| `current_effect_view_fresh_loaded_run` | 5.339 / 5.402 | 33.186 / 38.476 | 152.855 | returned |
| stale-worker-read control | 10.636 / 10.931 | 69.069 / 75.057 | 215.332 | refused |
| changed-authority control | 0.000240 / 0.000240 | 0.001213 / 0.001214 | 107.188 | refused |

The operation columns exclude each arm's separately recorded setup and
fingerprint work. Parent time also includes checkpoint reconstruction,
preflight, final verification and dispatch. Exact nanoseconds, setup and
verification timings, reconstruction call counts and payload sizes are in
`validation.json`. Instrumentation overhead and fixed plain-then-instrumented
cache order affect these measurements. This is **not a speed comparison**, an
optimization result, a whole-path fraction or native acceptance evidence.

Current byte verification found all 68 checkpoint files unchanged, including
hidden/ignored entries and modes; all 9,214 manifest-listed recovered regular
source files matched their bytes and Git modes. The 83 original retained regular
files matched their byte counts and hashes only. Extraction-normalized modes are
not claimed preserved: independent review found 55 regular-file modes differing
from the historical case manifest.
The union of the preparation and six operation import closures contains 1,195
files: 946 dependency, 159 interpreter and 90 recovered-source files. Every
declared file was rehashed, and the selected Python/Git byte, path and metadata
identities matched. Individual operation closures have 1,181 entries, except
the fresh callback owner with 1,182. These checks do not inventory every
installed dependency/resource or authenticate past execution.

The complete collection is 2,857,741 bytes (SHA256
`f684bfb1420d023293611d8f5f7880d5513d6f82332556ef6549c0450e294eed`).
All children, parents and collection fit the unchanged 4 MiB report ceiling.
Validation records the source tree `8e586a58a90e009719215ee7ac58d05adca2cd57`,
eight driver/utility/test/dependency-declaration pins and all report/review/XML
identities. External full reports and fictional case bytes remain retained;
this note publishes no raw typed payloads, source packet or machine-private
paths. All scientific eligibility, execution authorization, historical-capture
completion and native-acceptance flags remain **false**.

## What preparation constructs

`tests/native_shared_fixture.build_native_fixture` supplies the actual full and
core schema closures, a fictional neutral bundle, mechanically derived core
seed bytes, original receipt and `_Answers`. Its unused template declarations
are retained. A separate immutable selection/runtime/spec declares label
`offline-full-schema-4618-v1`, registration/attempt
`synthetic-full-schema-4618-v1`, run date `2026-10-07`, and runtime deadline 900
seconds. These are fresh synthetic identities, never historical labels.
The attempt directory's basename is the exact attempt identity. Only the shared
reservation parent is created before registration; the original registration's
fresh-path checks then verify that attempt, evidence, output and stage directories
remain new and disjoint. The first preparation correctly refused the earlier
basename mismatch; its failed case is retained, and this correction requires a
fresh preparation ([#4627](https://github.com/bridge2ai/data-sheets-schema/issues/4627)).

Preparation uses the unchanged offline permission-manifest helper as fabricated
software input. Actual registration validation checks that input; its acceptance
does **not** establish real observed permissions or launch authorization. Only
the selected function definitions are compiled from the verified fixture file;
pytest fixture decorators and test bodies are not executed.
The extraction namespace explicitly supplies the helpers' original module
dependencies, including `shlex` for the fabricated permission command records
([#4626](https://github.com/bridge2ai/data-sheets-schema/issues/4626)); the recovered
helper bodies remain unchanged.

The checkpoint follows this sequence:

1. Record synthetic initialization and initial helper settlements; write the
   fictional full record and original receipt; run actual phase-one sealing.
2. Use actual `capture_stage → _Replay.run → prepare_next/check_response →
   publish_stage` to admit and consume the nonzero receipt response.
3. Reach actual `await_core`, publish the independently derived core seed,
   record synthetic derive/check helper settlements, and run actual core
   sealing. The source inventory comes from real `source_review.inventory`.
4. Admit the first typed worker, deliver its complete request and mechanical
   `_Answers` response, and consume it through actual structural checks.
5. Admit the next advance without publishing it. All three workers remain in
   the packet. Exactly one worker is consumed; this is not completed execution.

For each response, the request Read settles first. The Write callback is
persisted without a grant; the real intent observer records the intent; the
grant is then persisted; only then is the response file created and its result
settled. No earlier grant is written and subsequently removed. This addresses
review issue [#4621](https://github.com/bridge2ai/data-sheets-schema/issues/4621).

Native and helper frames, auth/provider declarations, synthetic permissions and
supported/unsupported answer labels remain invented software data. No helper
CLI actually validates the synthetic success frames. Actual core derivation,
capture, seals, requests, response checks and stage publication run unchanged.

## Boundaries and measurements

Both phases run as fixed `-I -B -S` child commands. An explicit dependency
`site-packages` directory is added without executing `site` or `.pth` files.
Recovered Python modules—including directly loaded frozen controls—compile
verified `.py` bytes; a recovered-code execution audit refuses unverified
bytecode. Dependency Python sources also bypass bytecode caches. Imported
dependency/extension bytes are recorded and rechecked. Preparation's imported
closure is rechecked before measurement. These checks describe local bytes and
origins; they are not an authenticated interpreter or operating-system proof.

Before exposing recovered or dependency import paths, a small interpreter-only
bootstrap initializes `ctypes` under the source/extension tracking hooks.
Preexisting `ctypes` modules are refused. Every new file-backed bootstrap import
must originate in the selected interpreter's stdlib (excluding site-packages,
the recovered tree and the dependency tree) before its code executes. The
`ctypes` and `_endian` source paths are fixed to their stdlib locations; their
bytes and the `_ctypes` extension bytes enter `loaded_closure` and are rechecked.
Built-in/frozen modules belong to the separately pinned interpreter identity.
This permits the reviewed POSIX stdlib initialization of its existing process
handle, which the original preparation used. It supplies no later exception for
`CDLL(None)` or arbitrary libraries. The effect hook then denies all `ctypes.*`
events, including direct loading and symbol lookup, before selected recovered
and dependency paths become available. This is a local audit restriction, not a
complete operating-system sandbox
([#4647](https://github.com/bridge2ai/data-sheets-schema/issues/4647)).
`loaded_closure` covers imported Python/extension bytes, not a complete installed
environment or every metadata, dependency-resource or operating-system read.
Selected schema import closures, policy, runtime and case files have separate
complete pins; the existing authority checks declared dependency versions.
Environment disclosure uses only in-process values: `python` is `sys.version`,
`platform` is Python's `sys.platform` OS identifier, and `machine` is the kernel's
`os.uname().machine` architecture. It does not invoke `uname` or run platform or
processor feature probes. These fields keep the report's existing three-key
shape; `platform` is not a complete OS/version description.
Preparation 03 reached final report construction before the old
`platform.platform()` attempted a forbidden `uname -p` subprocess. Its failed
case is retained; the in-process reporting correction requires a fresh
preparation ([#4633](https://github.com/bridge2ai/data-sheets-schema/issues/4633)).
The parent also refuses a call without `-I -B -S` before loading the pinned
utility. Process replacement through `os.exec` is forbidden, as are subprocesses
outside the exact Git allowance; see review issue
[#4624](https://github.com/bridge2ai/data-sheets-schema/issues/4624).

Preparation may write only inside its new external case directory. Real journal
publication retains its exact-predecessor replacement and durable writes. All
create-once publications retain the original writer's atomic hard-link from a
single-link regular `.DESTINATION.pending-*` sibling to a new destination.
Both paths must be physical and inside the fresh preparation case; descriptor
overrides, symlinks, existing destinations and every measurement-phase link
remain forbidden. The second preparation correctly refused the earlier missing
allowance; its failed case is retained, and the driver correction requires a
fresh preparation ([#4628](https://github.com/bridge2ai/data-sheets-schema/issues/4628)). All
original recovery/source inputs are verified before and after. Measurement
forbids filesystem writes and networking. The sole process allowance is the
pinned local Git executable, at the recovered source directory, with exactly
`rev-parse HEAD` or `cat-file --batch`; the latter accepts only object queries at
the pinned commit. Git configuration/environment overrides are removed. Its
anonymous query stdin pipe is allowed; native/helper/provider commands are not.

The preparation resource ceiling is 900 wall seconds; **each explicitly selected
operation pair** has a 600-second ceiling.
Both are independent kill-and-reap bounds on diagnostic children. Preparation
performs repeated actual stage reconstructions and records each stage's CPU and
wall cost separately. The completed v2 preparation and pairs fit these ceilings;
this does not grant permission to relax any runtime acceptance limit. A timeout retains its partial
new case and reports `diagnostic_timeout`. It never retries or lengthens a bound
automatically.
If the child exits between timeout detection and group termination, the parent
still reaps it, verifies input preservation and publishes `diagnostic_timeout`
([#4625](https://github.com/bridge2ai/data-sheets-schema/issues/4625)).

Filesystem mutation checks validate the complete audit tuple. Directory-relative
descriptor overrides are refused for creation, removal, chmod, utime, rename
and link operations; descriptor forms of chmod, utime and truncate require a
descriptor already opened for writing inside the fresh case. Working-directory
changes, ownership/flag/extended-attribute mutations and symbolic links are
forbidden. These checks prevent a pathname checked inside the new case from
being applied through an unrelated directory descriptor to protected inputs
([#4646](https://github.com/bridge2ai/data-sheets-schema/issues/4646)).

Measurement selects exactly one ordered plain/instrumented pair per invocation:

- Actual `_load_live` on the frozen checkpoint.
- Actual `CallbackAdapter._run(endpoints)` with a fresh adapter and exact frozen
  stream identities/prefixes.
- Actual `decision()` on a newly reconstructed owner.
- Actual `current_effect_view()` on a newly reconstructed owner.
- Stale-worker-read refusal on independently reconstructed, in-memory mutants.
- Changed-selected-authority refusal on independently reconstructed, in-memory
  mutants.

The fixed catalog is `native_full_schema_operations_v1`; it retains all six
operations, including both negative controls. The driver never loops through
the catalog, automatically retries a pair, or extends its bound. A pair that
exceeds 600 seconds remains a timeout. Already completed operation reports are
immutable separate artifacts, so a later failure does not discard them.

Setup/reconstruction needed to obtain an operation's owner is outside that
operation's timer and is reported in that arm's `setup` CPU/wall nanoseconds.
Complete state/exception encoding is outside the operation timer and reported
as `fingerprint`. Each child separately reports `checkpoint_verification`
(real reconstruction and comparison with the prepared declaration), plus
`phase_overhead.preflight` and `phase_overhead.final_verification` for source,
runtime, import and file checks. Parent wall time includes dispatch, encoding
and other orchestration; these sub-timers are not claimed to partition every
instruction. All this work shares the selected pair's 600-second bound.
`_load_live` is measured separately. Instrumentation counts
actual calls to `_load_live`, `_decision_at`, `_checked_observations`,
`_Replay.run`, `_Replay._packet` and `Trace.__init__`; it does not replace their
implementations. Plain/instrumented timings share process caches in a fixed
order and must never be described as a speed improvement. Different selected
operations use separate children; their process caches are not shared.

The `_CapturedRun` fingerprint includes all exposed captured evidence, exact
bytes through typed hashes, complete reader member/pool/total state, and the
rendered RunSpec. It explicitly excludes RunSpec implementation caches and the
receipt catalog cache; it is an evidence projection, not an assertion that every
internal cache object is identical. Complete typed decision/effect returns and
bounded exception graphs are compared. Two separate in-memory controls change
the worker Read's history to the earlier receipt history and substitute selected
authority. They do not rewrite any frozen file and must both refuse with matching
complete exception graphs. File/stream hashes before and after remain exact.
Preparation report roles and identities are checked before reconstruction; the
preparation driver, parent/child interpreter, pinned Git and recovered provenance
must match the current selected identities. A driver edit requires a fresh
preparation. The parent validates the child's closed phase-specific result,
isolation flags and identities before reporting completion; the actual checkpoint
inventory and reconstructed summary must agree. Projection uses declared dataclass field
order, so process hash randomization cannot reorder the evidence fingerprint
([#4623](https://github.com/bridge2ai/data-sheets-schema/issues/4623)).

Both measurement and offline collection require the complete preparation parent
envelope: exact fields, scope, limitations, false eligibility flags, empty
operation denominator, fixed limits, successful child exit, nonnegative timing
and stream counts. They recompute the canonical child stdout digest and size
from the retained result. A partially reconstructed preparation envelope or a
rehashed operation binding cannot substitute for these checks
([#4640](https://github.com/bridge2ai/data-sheets-schema/issues/4640)).

Parent reports use `native_full_schema_checkpoint_v2`, with role
`checkpoint_preparation` or `measured_operation_pair`. Child reports use
`native_full_schema_checkpoint_child_v2`. An operation report binds its exact
selected operation to the raw preparation report SHA256/byte count, complete
case-inventory hash/counts, checkpoint summary, prepared import-closure digest,
driver/utility/source-provenance/Python/Git identities, fixed catalog and both
limits. This binding is retained on timeout or refusal as well as completion.
Each report explicitly lists the six-operation `completed`, `failed` and
`missing` denominator. A completed refusal control has parent status
`completed` and two matching `refused` arm outcomes; a parent
`diagnostic_refused` is a failed diagnostic, never a passing negative control.

## Offline collection

`collect` reads only the caller-selected preparation report, its current case
files and the explicitly supplied operation reports. It does not reload
recovered modules, run operations, invoke Git, inspect historical origin paths,
or infer missing measurements. It checks bounded strict JSON, report roles,
current case bytes and common identity bindings. Duplicate operation IDs and
mixed preparation/driver/runtime/source/case identities are refused.
Operation parents must retain the exact scope and limitations as well as the
closed fields and evidence bindings; changing those statements cannot be hidden
by an unchanged child-result hash
([#4648](https://github.com/bridge2ai/data-sheets-schema/issues/4648)).

Every completed child import closure must contain unique canonical
`recovered/`, `dependency/` or `interpreter/` relative origins, lowercase SHA256
digests and exact nonnegative integer byte counts. These checks do not reopen
historical paths. Origins shared with preparation must retain identical pins;
operation-specific imports may add entries, and preparation-only imports need
not occur during measurement. Each collected completed operation retains its
own final closure digest and entry count; failed diagnostics have no final
closure claim ([#4641](https://github.com/bridge2ai/data-sheets-schema/issues/4641)).

The collector recomputes pair agreement rather than accepting a saved parity
flag alone. Positive operations need two `returned` outcomes and matching
complete inline typed `semantics` payloads. Their complete-state digests are
recomputed from those payloads, and canonical payloads must also agree. Bare
matching hashes are insufficient. Refused arms have `semantics=null` and
returned arms have `refusal=null`. Refusal operations need two `refused` outcomes,
independently verified graph digests and identical complete bounded exception
graphs, including cause, context, suppression, typed arguments and notes. The
graph bound is 32 exception nodes, with valid references/cycles; typed values
are limited to 100,000 nodes and depth 128. Numeric counts and nanosecond timings
must be nonnegative integers, not booleans. No graph truncation substitutes for
equality. Typed values cover all tags emitted by the pinned utility, including
exact scalar types, bytes represented by size and digest, ordered lists/tuples,
dictionary pairs and named dataclass fields; nonfinite floats are refused.
Repeated canonical dictionary keys or repeated dataclass field names are also
refused; the saved ordering is preserved.

The complete report ceiling remains 4 MiB. A child checks its full encoded result
before writing any stdout. An oversized result becomes a retained parent
`diagnostic_refused` with no completed result; state is never truncated or moved
to an unreviewed side artifact. Parent and collection publications retain their
existing complete-report bound. The largest measured child stdout was
1,586,106 bytes and the largest operation parent was 1,593,651 bytes; the
six-operation collection was 2,857,741 bytes. All fit without truncation or a
cap increase
([#4642](https://github.com/bridge2ai/data-sheets-schema/issues/4642)).

If a completed child fits its limit but the enclosing parent report does not,
the parent retains a bounded `diagnostic_publication_refused` report with
`result=null`, the exact child stdout/stderr sizes and digests, child exit 0,
and the selected operation and binding. That operation remains failed in the
fixed denominator, and dispatch returns nonzero. The collector requires this
status to have a null result and successful child exit; it cannot count as a
completed pair or claim a final import closure. An oversized preparation is
likewise unusable for measurement. If even the failure envelope exceeds the
same ceiling, publication refuses before writing a report. No cap is raised,
state truncated, or earlier artifact replaced
([#4644](https://github.com/bridge2ai/data-sheets-schema/issues/4644)).

Collection publishes a new `native_full_schema_operation_collection_v1` report.
The operation denominator is recomputed in catalog order. Missing or failed
reports remain visible and produce `status="incomplete"` and exit 1. Only four
returned pairs plus both refused pairs, with every binding and preservation
check intact, produce `status="complete"` and exit 0. This is completion of the
diagnostic set, never scientific eligibility, execution authorization or native
acceptance. Collection verifies local artifacts and declarations; it does not
authenticate past execution. A caller must explicitly select which immutable
report to collect after any separately reviewed retry; duplicates never choose
a winning result automatically.

## Reviewed invocation shape

Select a Python installation with the recovered source's dependencies already
available. Supply its physical `site-packages` directory explicitly; no package
installation, dependency discovery or provider access is performed. Each output
must be a new sibling outside the source, recovery, dependency and checkpoint
trees. For example, after review:

```bash
PYTHON -I -B -S notes/native_full_schema_profile_2026-10-07/profile_checkpoint.py prepare \
  --source RECOVERY/source --recovery RECOVERY --dependencies SITE_PACKAGES \
  --output NEW_PREPARATION
PYTHON -I -B -S notes/native_full_schema_profile_2026-10-07/profile_checkpoint.py measure \
  --source RECOVERY/source --recovery RECOVERY --dependencies SITE_PACKAGES \
  --checkpoint NEW_PREPARATION --operation _load_live --output NEW_LOAD_MEASUREMENT
PYTHON -I -B -S notes/native_full_schema_profile_2026-10-07/profile_checkpoint.py collect \
  --checkpoint NEW_PREPARATION --reports NEW_LOAD_MEASUREMENT/report.json \
  --output NEW_PARTIAL_COLLECTION
```

Select the remaining five pairs in separate reviewed `measure` invocations using
these exact IDs, each with a new output directory:

| Operation ID | Required arm outcome |
| --- | --- |
| `_load_live` | returned |
| `CallbackAdapter._run_fresh_owner` | returned |
| `decision_fresh_loaded_run` | returned |
| `current_effect_view_fresh_loaded_run` | returned |
| `refusal_stale_worker_read_in_memory` | refused |
| `refusal_changed_selected_authority_in_memory` | refused |

Supply all six report paths to a subsequent explicit `collect` command for a
complete-set result. The one-report example above deliberately produces an
incomplete collection while retaining the completed pair. Empty report lists
likewise retain all six missing IDs. No command launches missing operations.

Keep the external reports and case intact. A committed result should contain
compact hashes, counts, timings, interpretation and bounded diagnostics—not the
raw fictional input packet, machine-private paths or complete permission fixture.
Every report retains `scientific_eligibility=false`, `execution_authorized=false`,
`native_acceptance_evaluated=false`, and `historical_capture_complete=false`.
Incomplete/failed diagnostics do not constitute an acceptance result.

Known duplicate Trace parsing is already tracked by
[#4537](https://github.com/bridge2ai/data-sheets-schema/issues/4537); repeated-prefix
parsing by [#4576](https://github.com/bridge2ai/data-sheets-schema/issues/4576).
This baseline makes no claim about residual costs in unavailable later code,
whole-path savings, or a fix for the native deadline. Parents
[#4354](https://github.com/bridge2ai/data-sheets-schema/issues/4354),
[#4400](https://github.com/bridge2ai/data-sheets-schema/issues/4400) and #4576 remain
open; deferred #4577/#4581 are outside this work.
