# Bounded Trace constructor comparison

[#4657](https://github.com/bridge2ai/data-sheets-schema/issues/4657) compares the
literal recovered `0125eebbc214d0907c3b69d23758cd9441911a78` constructor with the
newly reviewed single-decode candidate
`a8c11973da120cc0f792eef2d574dab7d910b09d` for
[#4537](https://github.com/bridge2ai/data-sheets-schema/issues/4537).
The candidate changes only the observations module: it decodes each stream once
inside a `Trace` construction and shares those rows between initialization checks
and indexing. Public initialization keeps its prior interface and validations.

The reviewed diagnostic completed successfully at commit
`0dcb348271af127b10819430d5da6d8f7bd45d1b` (tree
`e86b9ce04ec9029b3c943dabf76d5d04425feff4`). The comparison/retained-utility suite
passed **184 tests** with no failures, errors or skips (1.791 seconds in JUnit;
1.82 seconds reported by the coordinator). The candidate's new and original
observation tests passed **90 tests** with no failures, errors or skips (0.267
seconds in JUnit; 0.30 seconds reported). No warnings were reported for either run.
[validation.json](validation.json) records exact source, test, dependency-declaration,
runtime and saved-evidence pins. JUnit records outcomes; the coordinator's recorded
invocations and clean source observations bind those runs to the listed commits.

All six timed constructors returned identical complete typed evidence. Both
external sidecars contain exactly the same 32,722,082 uncompressed bytes and are
3,147,518 bytes compressed. Independent saved-file inspection compared the full
uncompressed bytes, strict canonical JSON, literal stream contents and exception
graphs. Each role retained 20 tool identities: 20 request returns, 20 admission
returns, 19 settlement returns and the expected one pending-settlement refusal.
All three constructor refusal controls, both instance-isolation controls and all
four exact/wrong-command advance controls passed. No required control is missing
or failed, and no output was truncated. Separate decode instrumentation observed
two complete row decodes per stream in the baseline and one in the candidate.

All timing samples are retained in their actual fixed order:

| Sample | Role | Constructor thread CPU (s) | Constructor wall (s) | Separate fingerprint wall (s) |
| --- | --- | ---: | ---: | ---: |
| 0 | Baseline | 0.667125708 | 0.721220833 | 1.326371625 |
| 1 | Candidate | 0.601513584 | 0.638150625 | 1.153758584 |
| 2 | Candidate | 0.054824542 | 0.055006167 | 1.105517167 |
| 3 | Baseline | 0.101295041 | 0.101522416 | 1.158434083 |
| 4 | Baseline | 0.094097125 | 0.102659917 | 1.072663834 |
| 5 | Candidate | 0.051591542 | 0.051591833 | 1.025288167 |

The observed constructor CPU medians are 0.101295041 seconds for baseline and
0.054824542 seconds for candidate. The first sample for each role is much slower
than its later samples. These runs share process and filesystem caches, so order
and warm-up effects limit interpretation. These six observations do not establish
a general speedup, callback parsing fraction or the native 900-second acceptance.

The worker completed in 19.361871709 seconds; the parent's bounded child interval
was 19.499938791 seconds, within the fixed 120-second limit. Worker setup took
2.181910917 seconds, final input verification 2.117788583 seconds and evidence
packaging 1.222370625 seconds. Fingerprinting is shown separately above. Other
untimed method, refusal, decode and instance checks remain part of total worker
time; these values are not an exhaustive performance attribution.

The exact external report is 8,754 bytes with SHA256
`a9c9dfb2fbb556086f078084f2bb1a745057c38f527388eb5a4787d478823537`.
Both gzip sidecars have SHA256
`3d482b17552dd6e73f0bb31454d8e4806420fbd563c81df485576cc439adfb82`;
their uncompressed SHA256 is
`aa0367166aeb0c04490f6586f19555a023175f38be0edf69837c93b6c49b1782`.
They remain external because complete evidence contains original private paths.

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

The coordinator ran the following command shape after independent review and
focused tests. Paths below are placeholders; rerunning requires a fresh external
output directory and explicit serialization with other local work:

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
#4537 remains open until its broader acceptance/integration obligations are met,
and #4576/#4577/#4581 retain their separate scope. This evidence fulfills the
bounded constructor-comparison obligation of #4657; candidate PR #4659 still has
its separate integration and CI requirements. This main-branch notes change closes
only #4657 and its four review findings after merge.
