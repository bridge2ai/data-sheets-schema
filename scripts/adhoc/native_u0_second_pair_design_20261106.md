# U0 second diagnostic pair — 2026-11-06

Authority: `notes/coordination/2026-11-06-codex-native-u0.md`, Next step 2.
This is a pre-measurement design record. No production change, provider/native
executable, network, push/gh or N=10 is authorized by this experiment.

The existing T1 evidence (2747e86c3f0521c1ef5c455d9be82428e4ca5be7)
puts 140.382 owner-thread CPU seconds in late inline/backfill, including
117.531 in recorded reconstruction and 105.862 in repeated schema products.
These regions overlap. Corrected runtime-token cost is 435 calls / 8.950
seconds, not the earlier instrumented 191 / 23.9 estimate.

Two separate cheap, source-bound, network-denied probes identify the actual
dependency transition. Importing `linkml.validator` imports rawloader, which
assigns `yaml.error.Mark = YAMLMark` and changes
`SchemaDefinition.MissingRequiredField`. Both optional reuse guards reject
the late Mark change. Eager validator import is rejected as a treatment:
it changes refusal timing/guard coverage and prevents T1 event-cache hits.

## Single proposed T2

Retain ordinary import order and all T1 bytes. Recognize only the exact
supported rawloader initialization in native catalog reuse, with distinct
markers before and after it. Keep original Mark and YAMLMark constructors,
methods and aliases guarded; accept no third alias or opaque callback.
Bind the shipped rawloader callback by compiling its source without executing
imports, including relevant globals/builtins and the original YAMLRoot callback.
Unavailable or changed dependency provenance disables optional reuse.

The owner-bounded catalog context rebuilds on a marker transition, rather
than relabeling a prior catalog. Existing byte/closure/identity keys and the
other caches' runtime-marker keys remain authoritative. No completed replay
verdict is newly cached and no validation is moved earlier or removed.
T1's late parser-event fallback remains unchanged.

Canary and mutation/refusal tests precede source freezing and the real pair.
They must cover late initialization, one fresh rebuild then warm reuse,
opaque/mutated Mark/callback/default/global/builtin dependencies, missing-name
and invalid-schema behavior, changed bytes/closure and token-None fallback.
Do not measure a treatment with unresolved guard defects.

## Measurement and interpretation

Create new `codex-native-u0-second-control-20261106` from T1, with identical
additional passive observer in both fresh arms; treatment is its sole-parent
descendant containing T2. Exact SHAs are pinned before launch. Original frozen
trees and evidence remain untouched. Use the same serial neutral node,
synthetic peer, scrubbed environment, OS network-denied descendants, separate
unchanged read-only host sampler, owned lock, and 180/900-second limits.
One fresh T1 control is the end-to-end canary; inspect side effects and cleanup
before one T1+T2 run. No replacement trial or campaign follows a failure.

The new observer measures actual guard returns/unwinds without extra guard
calls. Its reason-accounting CPU is only part of observer overhead. Both
fresh arms share identical instrumentation; original first-pair control does
not. Native parent-process final readback is verified by the exact test but
its CPU is not recorder-thread CPU.

Compare top-level completed owner-thread phases and all call counts. Fewer
internal schema/parse calls are the intended mechanism, so do not demand
equal internal work counts or silently override the existing analyzer's
equality gate. Verify completed synthetic gates, persisted records, final
full/core bytes and readback. If control is censored, retain its partial CPU
as a partial observation, not a completed-phase total. Historical cumulative
reductions must identify the original censoring and instrumentation change;
do not sum nested phases or two separate pairwise percentage changes.

Assess whether the combined diagnostic recorder CPU and observed contended
wall duration leave useful headroom within 180 seconds. No numeric owner
acceptance threshold was supplied. A successful one-pair result can justify
recommending a quiet-host N=10 campaign after reviewed U3 implementation,
but cannot establish reproducibility, quiet-host timing acceptance or an
expected-time confidence interval. Report an observed estimate with those
limits, not a guaranteed time. Stop after the report and STATUS update.
