# Recovered native Trace profiling baseline (#4614)

This is a new diagnostic of the published `0125eebbc214d0907c3b69d23758cd9441911a78`
source and its retained synthetic observation prefixes. It measures the real
`native_shared_observations.Trace` constructor. It does not run native
generation, callbacks, helper processes, fixture builders, a provider, an
acceptance test, a finalizer, or scientific scoring.

The recovered source predates the unavailable local `4366dc...` candidate.
The 546 CPU seconds and later 14.108% / 24.141% measurements are not reproduced
or used as comparators. Repeated parsing was already investigated in
[#4537](https://github.com/bridge2ai/data-sheets-schema/issues/4537) and
[#4576](https://github.com/bridge2ai/data-sheets-schema/issues/4576). This driver
establishes a recoverable baseline; it neither discovers a new bottleneck nor
revives the deferred #4577/#4581 optimizations.

## Exact inputs

The external recovery directory must retain this layout:

```text
recovery/
  artifact-11408295434.zip
  artifact/
    artifact-manifest.json
    case-manifest.json
    source-before.json
    source-after-neutral.json
    source-final.json
    ...all remaining original upload members...
  captured/cases/neutral/test_actual_public_correction_0/native26/
    ...83 original regular case files...
```

Supply the separate, clean detached source checkout with `--source`. No large
fixture, original machine path, raw transcript, credential, or private local
path is copied into this repository or the compact diagnostic report.

| Identity | Pin |
| --- | --- |
| Source commit | `0125eebbc214d0907c3b69d23758cd9441911a78` |
| Source tree | `142af4bfd8f32bd6b37d61434cfb30e8bfac5bf1` |
| Actions run / attempt | [37451274006](https://github.com/bridge2ai/data-sheets-schema/actions/runs/37451274006) / 1 |
| Artifact | `11408295434` |
| Artifact ZIP SHA-256 | `0ec5378065601dae7d81801a6ad051dd9cb07b82c6b99cf0b4ea4d8e4cbc0dae` |
| Source manifest SHA-256 | `53f8a7378e8babf3c746fef6c2e54c27d9bbba1c0bcd621cb91ee86c004a4798` |
| Case manifest SHA-256 | `1fc631110a8dc7d1db8ff28af35243e6edfddb8737d70aad32928410794d0de4` |

The historical attempt failed its original 900-second deadline. Its result has
3/15 gates passing, no terminal child exit, and complete control shutdown. The
omission case was not executed. It contains 67 transcript rows, 24 control rows,
and 15 recorded observation prefixes. Its final capture has only five members
and no complete saved replay pool. This diagnostic does not fill those gaps.

Before and after measurement, the driver verifies the complete original upload,
the 9,214 pinned source-file bytes and modes, and all 83 regular case files.
The two historical submodule gitlinks remain declared opaque dependencies;
their contents are not needed or imported. The original pytest-current symlink
is not followed. Each observation retains its exact path, stream identity,
byte endpoint, physical line count, hash, session, execution and selection
bindings. Original synthetic labels, policy, runtime and the 900-second
acceptance declaration are preserved. No prefix is extended, repaired or
substituted with a complete-history claim.

## Run after independent source review

Use a Python interpreter supporting this stdlib-only driver, with isolated
startup, bytecode writes disabled and site initialization disabled:

```sh
python3 -I -B -S notes/native_profile_recovery_2026-10-07/trace_prefix_profile.py \
  --source /path/to/recovered-0125-source \
  --recovery /path/to/recovery \
  --output /path/to/new-external-diagnostic
```

The destination must be new, outside both recovered inputs, with an existing
physical parent directory. The driver cannot overwrite an existing result.
It writes only `report.json` there, after checking preservation. Bad pins or
identity drift refuse publication. A worker timeout produces an explicitly
failed `diagnostic_timeout` report and nonzero exit status.

The parent dispatches one fixed `-I -B -S` child with a **120-second worker wall
limit**, killing and reaping it on timeout through `subprocess.run`. This is a
separate diagnostic limit; it does not change the historical 900-second native
acceptance limit or any native gate. Input verification before dispatch and
after completion is outside the worker wall limit. There is no retry/resume or
configurable command/provider route.

The child installs an audit hook rejecting process creation, networking and
filesystem writes before loading repository code. It compiles the verified
source bytes of exactly three stdlib-only modules: the contract, evidence
carriers and observations. It does not import a repository initializer or read
repository bytecode caches; `-B` alone would not provide that guarantee.

The parent and child bind the resolved interpreter's bytes, path identity and
file metadata before and after execution, and compare child startup flags and
driver hashes. Host paths are represented by hashes. This is checked local
identity and preservation, not authenticated execution or proof against an
adversarial replace-and-restore filesystem race.

## What the report means

For each prefix, the driver performs one plain construction followed by one
construction instrumented with `cProfile` using calling-thread CPU time. Both
record calling-thread CPU and wall time. Semantic readback and fingerprinting
are outside the timed constructor. Instrumentation overhead remains visible;
the ordered single pair is not an estimate of an optimization or a statistically
controlled speed comparison.

Parity fingerprints cover the entire typed Trace state, including frames,
calls, callbacks, decisions, results, policy, immutable prefix byte identities,
pending calls and each tool's request/admission/settlement result. Value types,
container order and complete bounded exception cause/context graphs are kept
distinct. Explicit foreign-session, exchanged-role and foreign-model controls
must refuse identically in both modes. Prefix return/refusal counts are stated
separately from instrumentation parity. Profiling rows use logical source names
or stdlib basenames and omit source documents and host paths.

The report always states `scientific_eligibility=false`,
`native_acceptance_passed=false` and `historical_capture_complete=false`.
Neither parity nor a short Trace duration establishes native completion,
scientific validity, a whole-path cost fraction, estimated savings, residual
`4366...` cost, or a fix for the acceptance deadline. A representative full-schema
synthetic `_load_live` / `_run` comparison requires a separately reviewed fixture
and driver. Parent issues #4354, #4400 and #4576 remain open.

Review follow-ups: #4615 requires complete exception-graph parity; #4616 requires
before/after interpreter identity and child startup binding. Their regressions
are in the focused tests accompanying this diagnostic.

## Recorded diagnostic and validation

[trace_prefix_report.json](trace_prefix_report.json) is the unmodified 381,405-byte
report from the first reviewed diagnostic. Its SHA-256 is
`f89c77bedf651c6271366ee91d96c33e6efbd63097026fe9869dfb7ab5027e9d`.
The full compact report is retained so each prefix's function profile and exact
parity hashes remain inspectable; it contains no raw source, transcript, original
machine path or local host path. The external original remains unchanged.
[validation.json](validation.json) records the report, driver and test-file pins,
the JUnit identity, all 58 test cases, exact aggregate times and scope holds.

All **15 retained prefixes returned successfully**, with matching complete typed
semantic fingerprints in plain and instrumented mode. The foreign-session,
exchanged-role and foreign-runtime-model controls all refused with matching
exception-graph fingerprints. Inputs were unchanged. All **58 focused tests
passed**, with zero errors, failures or skips. The original JUnit file has
SHA-256 `c3ca98ae95e724ffb93069e3518320cae144ba92f7f513f99ab44098422b2173`.

The measured driver SHA-256 is
`4097c8dff6e921b146feb49854b67487adc54b5a4da7943e22c9293849df01bf`.
The checked interpreter was CPython 3.13.12 on Darwin 25.5.0, arm64; interpreter
bytes and startup flags are pinned in the report. This differs from the
historical Actions environment recorded in the recovered artifact; no
cross-environment performance equivalence is asserted.

| Measure | Plain | Instrumented |
| --- | ---: | ---: |
| Sum of 15 constructor calling-thread CPU times | 1.313390459 s | 0.792906247 s |
| Sum of 15 constructor wall times | 1.347250874 s | 0.819710459 s |

The entire diagnostic child took **22.544208917 seconds**, within its separate
120-second limit. That duration includes verification, semantic readback,
fingerprinting and report construction; it is not a native generation time.
The three negative controls are recorded separately and are excluded from the
15-prefix constructor totals above.

The instrumented total is lower than the plain total. This is **not a speed
improvement**: each plain call and its untimed semantic readback precede its
instrumented call in the same process, and the recovered contract retains a
bounded `_JSON_VALIDATION` cache. There was no cache reset, counterbalanced
ordering or repeated independent sample. Those order and cache conditions limit
the interpretation; no effect size is inferred. The two `request_read` prefixes
show particularly large plain/instrumented differences, retained below rather
than discarded.

| Prefix | Observation | Transcript/control rows | Plain CPU (ms) | Instrumented CPU (ms) |
| ---: | --- | ---: | ---: | ---: |
| 0 | initialized | 2 / 2 | 0.865 | 1.219 |
| 1 | phase1_sealed | 32 / 12 | 5.005 | 5.453 |
| 2 | advance_admitted | 34 / 13 | 2.075 | 5.886 |
| 3 | advance_settled | 35 / 13 | 2.124 | 5.739 |
| 4 | request_read | 38 / 14 | 312.328 | 57.823 |
| 5 | response_intent | 40 / 14 | 48.824 | 54.087 |
| 6 | response_written | 41 / 15 | 63.413 | 54.912 |
| 7 | advance_admitted | 43 / 16 | 52.292 | 57.024 |
| 8 | advance_settled | 44 / 16 | 55.870 | 57.495 |
| 9 | core_sealed | 53 / 19 | 52.801 | 53.774 |
| 10 | advance_admitted | 58 / 21 | 54.487 | 56.445 |
| 11 | advance_settled | 59 / 21 | 56.423 | 58.237 |
| 12 | request_read | 62 / 22 | 392.905 | 103.810 |
| 13 | response_intent | 64 / 22 | 101.633 | 108.558 |
| 14 | response_written | 65 / 23 | 112.344 | 112.445 |

Each instrumented construction called `rows()` four times. That is an observed
property of this pinned old Trace implementation, consistent with the existing
#4537/#4576 investigations. It establishes neither the cost remaining in the
unavailable later source nor a justification for another acceptance attempt.
The last registered observation ends at 65/23 rows; verifying the retained
67/24-row streams does not invent observations for their unregistered tail.
