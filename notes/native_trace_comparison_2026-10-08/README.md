# Bounded Trace constructor comparison

[#4657](https://github.com/bridge2ai/data-sheets-schema/issues/4657) compares the
literal recovered `0125eebbc214d0907c3b69d23758cd9441911a78` constructor with the
newly reviewed single-decode candidate
`a8c11973da120cc0f792eef2d574dab7d910b09d` for
[#4537](https://github.com/bridge2ai/data-sheets-schema/issues/4537).
The candidate changes only the observations module: it decodes each stream once
inside a `Trace` construction and shares those rows between initialization checks
and indexing. Public initialization keeps its prior interface and validations.

This comparison has not yet run. Source review and focused tests must complete
before the coordinator starts the one bounded diagnostic.

The selected preparation05 report has SHA256
`b72bcea58c3a64be466b642fd6493a1da51865f7f8afd730d8816f9c01756f15`.
Its unchanged sibling `case` contains 68 files, 25,352,291 bytes. Final observation
`000017` (the eighteenth observation) binds the complete 61-line transcript and
22-line control stream. Both constructors receive those exact prefixes, session,
policy and runtime declarations. Original paths remain data; there is no replay,
registration, fixture construction, identity substitution or native execution.

The driver reuses the pinned stdlib-only utility from
`notes/native_profile_recovery_2026-10-07/trace_prefix_profile.py` (SHA256
`4097c8dff6e921b146feb49854b67487adc54b5a4da7943e22c9293849df01bf`)
for bounded file reads, original recovery verification and observable Trace
semantics. It compiles the exact three selected modules under their canonical
`data_sheets_schema` identities, with distinct baseline/candidate logical source
filenames. It neither loads package initializers nor reads Python import caches.
The candidate Git commit is a review reference; authority is the three literal
compiled module hashes, not a claim to verify the entire candidate tree.

The worker measures six uninstrumented complete constructors in fixed order
**baseline, candidate / candidate, baseline / baseline, candidate**. Module
instances persist across these calls, so a persistent cache cannot hide behind
reloading. Every timed constructor must return the same complete typed state and
request/admission/settlement/pending observations. Fingerprinting and JSON
serialization occur outside constructor timings. Setup, final input verification
and evidence packaging are disclosed separately. The ordered runs share process
and filesystem caches; they are constructor observations, not a whole-path speed
or deadline claim.

Separate untimed instrumentation counts calls only to the complete-stream `rows`
decoder: two per stream for baseline and one per stream for candidate. Its full
state must match the uninstrumented state. Three negative controls alter only
in-memory arguments (foreign session, exchanged stream roles, foreign runtime
model); complete bounded exception graphs must agree. A mutation control verifies
that two independently created instances do not share mutable outer or nested
state. No persistent cache is added to production.

The exact pending Bash call also exercises `current_advance` with its captured
command and with an explicitly different command. The former must return the same
admission; the latter must retain a complete refusal graph. Both queries run during
untimed semantic readback, participate in every full-state comparison, and remain
bound to the call identity and original command. They contribute four required
method controls across the two roles.

Full typed evidence retains literal byte values as base64, every Trace field,
all method outcomes and complete cause/context/suppression/note graphs. Equality
compares complete canonical payload bytes, never only their hashes. Two external
sidecars, `baseline.json.gz` and `candidate.json.gz`, each retain the complete
positive state once and the three refusal graphs. Each sidecar has a fixed 8 MiB
compressed and 128 MiB uncompressed bound (256 MiB total uncompressed); trailing
data, concatenated members, truncated streams and expansion beyond the bound are
refused. The strict JSON report is at most 4 MiB; the bounded child wire is at most
24 MiB. There is no truncation or automatic cap increase. Full sidecars can contain
private paths and are retained externally, not committed with compact notes.

The parent and child require `-I -B -S`. The child has no process, network, native
library or filesystem-write allowance. Its only output is the bounded result on
stdout. The parent enforces a fixed **120-second** wall deadline, kills and reaps
the child on timeout, verifies source/checkpoint/runtime preservation and validates
the complete result before publishing a fresh disjoint output directory. Timeout
or refusal preserves the required control denominator without claiming completion.
No retries, longer bound or alternate fixture are selected automatically.

Review finding [#4658](https://github.com/bridge2ai/data-sheets-schema/issues/4658)
required closed validation of complete typed positive/refusal payloads, all control
denominators, fixed scope limitations and exact integer/boolean metadata. The
parent now checks these in addition to compressed/uncompressed hashes and complete
role equality. Tests include validly rehashed forged evidence, rather than only
changed digests.

Review finding [#4661](https://github.com/bridge2ai/data-sheets-schema/issues/4661)
keeps the original deadline active after pipe EOF: a child that closes both output
streams but stays alive is terminated at the remaining deadline and reaped. EOF
does not start a fresh timeout or permit an unbounded normal wait.

Review findings [#4662](https://github.com/bridge2ai/data-sheets-schema/issues/4662)
and [#4663](https://github.com/bridge2ai/data-sheets-schema/issues/4663) added the
checkpoint-bound `current_advance` positive/refusal pair and audit denials for
extended attributes and file flags, including descriptor forms. The audit hook
restricts this fixed reviewed workload; it is not an operating-system sandbox.

Inputs are checked before and after execution. This includes the original
recovered source files, historical retained case bytes, all 68 current case files
(hidden files and modes included), the exact preparation report, selected compiled
modules, driver/utility and interpreter identity. Historical extraction-normalized
file modes are not asserted preserved. The checks and audit restrictions provide
local evidence, not authenticated execution or complete ABA protection.

The coordinator may run, only after independent review and focused tests:

```bash
PY=/path/to/selected/python
DRIVER_REPO=/path/to/native-trace-comparison-source
RECOVERY=/path/to/native-recovery
CANDIDATE=/path/to/native-parse-candidate-source
PREPARATION=/path/to/full-schema-preparation-05/report.json
OUTPUT=/path/to/new-external-constructor-comparison
"$PY" -I -B -S "$DRIVER_REPO/notes/native_trace_comparison_2026-10-08/compare_trace.py" \
  --baseline "$RECOVERY/source" --candidate "$CANDIDATE" \
  --recovery "$RECOVERY" --preparation "$PREPARATION" --output "$OUTPUT"
```

Focused modules are `tests/test_native_trace_comparison.py` and
`tests/test_native_trace_comparison_adversarial.py`; they use portable fixtures,
without running recovered native code or rebuilding the full-schema case.

The original retained-prefix and full-schema diagnostics remain unchanged. This
does not reconstruct unavailable `4366` code, complete a native generation,
evaluate the 900-second acceptance requirement, authorize a provider run or establish
scientific eligibility. #4354, #4400 and their acceptance obligations remain open;
#4576/#4577/#4581 retain their separate scope.
