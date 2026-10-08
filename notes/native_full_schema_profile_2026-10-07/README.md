# Fresh full-schema synthetic checkpoint (#4618)

This driver prepares a **new fictional checkpoint** on recovered source
`0125eebbc214d0907c3b69d23758cd9441911a78`, then measures four actual reconstruction
operations. It does not replay the incomplete historical capture, launch a
native/provider/helper process, score a dataset, or evaluate the 900-second
acceptance requirement. It does not reconstruct unavailable source `4366dc…`.

The implementation and independent boundary tests must be reviewed before the
first fixture construction or measurement. This document currently describes
the unexecuted driver. Results and measured stage costs will be recorded only
after the serialized, independently reviewed run.

The driver imports the committed [retained-prefix utility](../native_profile_recovery_2026-10-07/trace_prefix_profile.py)
from this repository, requiring SHA256
`4097c8dff6e921b146feb49854b67487adc54b5a4da7943e22c9293849df01bf`.
That utility verifies all 9,214 recovered regular source files, the original
Actions archive and uploaded manifests, and all 83 retained case files. The
historical capture remains incomplete and unchanged. The two opaque historical
Git submodule identities are recorded; importing an unregistered source is
refused.

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
`loaded_closure` covers imported Python/extension bytes, not a complete installed
environment or every metadata, dependency-resource or operating-system read.
Selected schema import closures, policy, runtime and case files have separate
complete pins; the existing authority checks declared dependency versions.
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

The preparation resource ceiling is 900 wall seconds; measurement's is 600.
Both are independent kill-and-reap bounds on diagnostic children. Preparation
performs repeated actual stage reconstructions and records each stage's CPU and
wall cost separately. These initial conservative ceilings will be assessed
against those recorded costs; they are not measured performance estimates or
permission to relax any runtime acceptance limit. A timeout retains its partial
new case and reports `diagnostic_timeout`. It never retries or lengthens a bound
automatically.
If the child exits between timeout detection and group termination, the parent
still reaps it, verifies input preservation and publishes `diagnostic_timeout`
([#4625](https://github.com/bridge2ai/data-sheets-schema/issues/4625)).

Measurement performs an ordered plain/instrumented pair for:

- Actual `_load_live` on the frozen checkpoint.
- Actual `CallbackAdapter._run(endpoints)` with a fresh adapter and exact frozen
  stream identities/prefixes.
- Actual `decision()` on a newly reconstructed owner.
- Actual `current_effect_view()` on a newly reconstructed owner.

Setup/reconstruction needed to obtain an operation's owner is outside that
operation's timer. `_load_live` is measured separately. Instrumentation counts
actual calls to `_load_live`, `_decision_at`, `_checked_observations`,
`_Replay.run`, `_Replay._packet` and `Trace.__init__`; it does not replace their
implementations. Plain/instrumented timings share process caches in a fixed
order and must never be described as a speed improvement.

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
  --checkpoint NEW_PREPARATION --output NEW_MEASUREMENT
```

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
