# BC1 bounded audit implementation — Wave 2, 2026-10-27

BC1 is an explicitly selected **new model-access condition**. This local branch
implements its codec, staged audit, recovery controller and registration sizing.
It does not authorize generation, scientific scoring or native-arm execution.
The protected shared-generation hooks are an **unapplied proposal**; the default
remains the historical implementation and BC1 selection refuses without hooks.

Branch: `codex/bc1-production-impl-20261027`, isolated worktree
`/private/tmp/d4d-codex-bc1-production-20261027`.
Frozen implementation/test head:
`c9feaedc36a4bf77d9cf604f783748e29b9c1a21`, tested in the separate
`/private/tmp/d4d-codex-bc1-derivation-cache-20261027` checkout. Final evidence and
documentation commits on the delivery branch are recorded in the primary
`notes/coordination/STATUS.md`; they do not change tested source.
Dependencies: reviewed R9b repair and final evidence
`aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4`, plus reviewed A17
`fc9e1a5d89a7223d75fa1dc1c46f524fb51dea03`. Contrary to the delegation's ancestry
assumption, R9b's base contains neither A14 nor A17. A17 was merged locally;
this does **not** install A14, D38 or D41, rotate canonical prompt assets, or
establish compatibility with every other outstanding branch.

## Selected contract and retained evidence

- Select `RunSpec.bounded_carry_version=1` **and** an exact `bounded_carry`
  registration block. Supported parent tuple: shared generation 1,
  `generic_v10`, API renderer 25, playbook 2, receipt completion 2, direct API.
  Native and shared-generation-v2 routing remain unsupported.
- Codec `bc1_codec_v1` has deterministic round trips, exact UTF-8 byte spans,
  dictionary references, local repeated-string tables, explicit literal escapes
  and canonical `sha256_b64`. Neither hashes nor successful decoding certify
  scientific support. Strict types, duplicate-key refusal and separate expanded
  size/depth/node limits prevent ambiguous or unbounded decoding.
- Uniform visible envelopes are **98,304 worker bytes**, **131,072 integration
  bytes**, **262,144 concern-carry bytes**, and **32 open concerns**. Worker and
  integration output reservations remain **64,000 tokens including thinking**.
  A cap failure refuses; it never truncates, changes the partition or buys a
  replacement answer.
- The earlier design's fan-in interpretation is **one or two new workers per
  group**, followed by **one separate final cross-group consistency call**.
  Thus `W` workers require `W + 1 + ceil(W/fan_in) + 1` audit calls. This is not
  a universal maximum of two integration calls; the ambiguity was disclosed to
  the orchestrator and optional clarification remained unanswered.
- Complete original records, captured sources, every raw delivery, full worker
  reviews, explicit decisions, predecessors and complete machine audit remain
  available. Downstream model projection omits only untouched supporting or
  metadata review rows. Changed rows, concerns, full decision history, omission
  candidates and dispositions remain. The projection uses its own local string
  table and an empty external dictionary; it requires no external hash lookup.
- Each stage independently binds exact request, predecessor state and current
  row index. Every incoming finding needs an explicit decision. Terminal checks
  reuse source-review grammar, literal evidence, removal and omission-accounting
  validators. Reconciliation and final report source-review duties remain.
- Controller snapshots precede ledger pointer updates. A missing, orphaned or
  rewound checkpoint refuses; an admitted call without saved delivery is never
  repurchased. Complete saved responses can settle once on recovery. This is
  process-interruption handling, not cryptographic authenticity or a claim of
  directory-fsync power-loss durability.

Retiring rows does not count as better source coverage. Copying source wording
does not alone justify `exactMatch` or `none`. The output explicitly leaves
scientific support, exhaustive recall and novelty unverified.

## Context and sizing

BC1 sends complete captured reachable Dataset **and CoreDataset** definitions,
including descriptions and annotations. The complete schema and source bundle
remain in the actual wire; dictionary overhead is counted rather than assumed
free. Neutral vocabulary policy derives only from the explicit captured profile,
omission context and schema term-source declarations. External identifier syntax
does not prove ontology membership. Evaluation rationale is not used as a
generation-context fallback, and legitimate source wording is not censored.

The builder supports all six declared projects, requires each selected project's
own full/core/receipt sizing inputs and counts every group plus final call using
the production planner and wire formatter. Its sidecar binds source/code and
registration identities and verifies complete stage inventories and totals.
Historical profile coverage cannot waive BC1 sizing. The old A17 byte calibration
floor remains unchanged for historical mode.

Future responses and receipt decisions are unknown. Empty-future and visible-cap
ASCII scenarios are explicitly hypothetical; the inherited two-bytes/token ratio
is a planning assumption, not a provider count or upper bound. This branch does
not claim all six real campaigns fit. Actual request bytes, provider token
counts and aggregate allowances must pass before each dispatch. Full generation,
receipt, reconciliation and report costs remain separate from the audit roster.

## Protected hook proposal

[Exact diff](bc1_shared_generation_patch_2026-10-27.diff), SHA-256
`10cb0ff8dd77d34ec150ae9b5447a82cdeef4402a477151f220a6c02685b0cb8`.
[Manifest](bc1_shared_generation_patch_2026-10-27.json), SHA-256
`94a576500595ae05e1cefe246796e04028ab6f1c37de5b9d493da726b0946842`.
The same diff is delivered to the requested sibling `d4d-executions/plans/` path.
It adds only explicit opt-in, strict parser, schema and plan hooks. AST parsing
and `git apply --check` pass; no protected file was written. Applying it changes
the captured source identity, so registrations must be rebuilt afterward.

The integration tests compile this exact proposal **in memory**. They check
interfaces under that disclosed adapter, not installed-source attestation or
launch readiness. No provider, native executable or network is used.

## Local review findings and verification

| Finding | Disposition |
| --- | --- |
| Complete core semantics missing from first selected schema renderer | Added independently captured reachable CoreDataset catalog and causal tests. |
| Replaying every earlier prefix repeatedly caused avoidable nested replay | Added linear captured-byte replay per operation; no trusted mutable cache or validation bypass. |
| Proposal and manifest could share an output path | Distinct resolved paths and exclusive fresh-file writes. |
| New controller fixture lacked mandatory identity fields | Test-only correction; snapshot guard remains strict. |
| Scripted omission response uses `format`, not `kind` | Test-only `.get('kind')` dispatch; production contract unchanged. |
| BC1's registered code closure was absent from shared-v1 output-footprint authorities | Added exactly the selected code paths before any writer; private hardlink collision cases verify refusal without source mutation. Off-mode resources retain their prior order. |
| Controller fake lacked the streamed transport interface used by the real API runner | Inherited the existing `FakeMessages.stream` wrapper; no production or assertion change. |

Initial frozen implementation `b2525adb92159776d3fbeb22ecf41f564143462a`:
**100 passed, 18 runtime fixture setup errors**, zero skips, 34.74s pytest;
tracked bytes unchanged and module origins verified. Outcome SHA-256
`df08568d305250e15e09173e4f371001e91642d1d58ba606164b4bed610d49cc`.
The failed batch is retained in the [completed-result archive](bc1_validation_2026-10-27_completed/README.md).

Affected legacy verification at `17ca65b0a00f8f3c665e1f7d343b93b121176320`:
**317 passed, one existing optional historical-data skip, zero failures/errors**,
1,490.60s pytest / 1,533.15s driver; source unchanged and both origin checks
complete. Outcome SHA-256
`629614afabc0b393144e10d103af276b538b62b3749be57db28b7304ce2b8b79`.
The skip requires `D4D_CHORUS_V10_TYPED_RUN` for a historical wire check; it is
not counted as a pass.

Corrected controller verification at
`f811ac0840775984e54efa573e873224c7d1831e`: **18 passed**, zero failures/errors/skips,
76.57s pytest / 79.35s driver; source unchanged and both origin checks complete.
Production is byte-identical to17ca; only the fake streaming interface changed.
Outcome SHA-256
`9304fbd759eb975f36d32b2c9c113b9f3d23d2e57e1f163ecb36e05358c723f0`.
The completed-result manifest SHA-256 is
`8939b3a8eaab39d26e95285fc612254845b967b459a698e2c3390699bdd54eb8`.
It preserves selected raw result bytes/modes, including failed evidence;
complete synthetic case directories remain external.

The original frozen17ca BC1 batch was interrupted after 3,282.66 pytest seconds:
106 passed and 12 failures from the already-corrected fake streaming interface.
The public API pipeline did not complete and the four write-footprint cases were
not reached. Source stayed unchanged; the driver retained both origin checks.
The [interrupted-result archive](bc1_validation_2026-10-27_interrupted/README.md)
preserves the original results and the differing driver timing field verbatim.
The c9 full run then completed **162 passed / 1 failed**, zero skips/errors,
493.57s pytest / 498.59s driver, with unchanged source and both origin checks.
All cache/controller/core cases passed. The public pipeline completed its report
but final provenance conformance rejected its BC1 completion shape; completed
replay was not reached. Outcome SHA-256
`05fc56bc55d2ed0235a39636b0fcebfadb91175b9f8568dcaa78f518f6ee7d84`;
[full-run archive](bc1_validation_2026-10-27_full_initial/manifest.json), manifest
SHA-256 `66c9dca788597a6eb710f2257a4fda2b7f09ec61193606f63b7aa62c10b7c2da`.
The remaining correction adds a dedicated closed BC1 provenance shape; it does
not change the runtime, compiler, dataset schema or conformance gate. Its focused
tests and public completed replay remain pending.
These cross-head results do not claim one fresh green repository-wide suite.

### Bounded pure derivation cache

Code review identifies repeated pure schema/packet derivations in
`bc1_audit._open/_derive`, plus repeated full/core schema-context rendering
during saved-stage replay. Legacy already memoizes analogous pure derivations.
This is a concrete optimization candidate, not proof of an algorithmic hang,
host-contention cause or measured speedup. Functional-test timings overlapped
other authorized work and are not idle-host performance measurements.

The isolated `codex/bc1-derivation-cache-20261027` correction adds a caller-owned
cache keyed by exact canonical input/schema closure bytes, full selection,
project, limits and current contract/asset identities. It returns privately
decoded values and a new omission Prepared object. The default retained audit
budget is eight entries / 64,000,000 bytes, counting keys and values. The
existing schema-text memo uses length/SHA-256 keys over both complete schema
closures, source names/paths, record and assigned paths; its separate default
budget is 32 entries / 128,000,000 encoded-value bytes. These are retention
limits, not a bound on whole-process peak memory.

Fresh authority/raw-response/evidence/accounting checks remain. Independent
terminal replay starts with a new cache; no acceptance verdict is cached.
Closed parser/function dependencies and current constants are rechecked before
reuse; unfamiliar changes bypass and clear both stores. Ordinary pure-check
interfaces remain uncached by default. Added tests cover byte parity,
invalidation, mutation isolation, retention and fresh terminal replay. All28
cache cases and all30 controller cases passed in the c9 full run.
No measured speedup or campaign-scale performance claim is made here.

The first cache verification at `c477590018bf192410a52635d603ffff5ab4c417`
reported **38 passed / 19 failed**. The default-value serializer rejected
PyYAML's loader-class default, so reuse was safely disabled. The correction at
`18f202dc3b29ee8557180e82009586c61a05a51a` then reported **1 passed / 1 failed**:
the token was valid at import but changed after actual preparation. The committed
diagnostic identified exactly LinkML's five first-use YAML constructor
registrations. The final correction initializes/disposes that known empty loader
once before capturing dependencies, never during refresh or from caller data.
All original assertions and later-mutation invalidation checks remain.

At c9, **3 positive cases passed** (0.43s pytest / 2.86s driver), including a
real warm lookup that makes zero uncached derivation calls and a changed-key
lookup that makes one. A separately retained diagnostic has zero token changes
after fixture creation and preparation and preserves its single retained entry.
This establishes the mechanism on the small fixture, not a measured speedup.

The c9 omission/selection/condition compatibility check passed **118 cases**,
zero failures/errors/skips, 36.29s pytest / 41.07s driver. Both runs confirmed
unchanged source and import origins. The 118 cases overlap the earlier 317-case
legacy run; do not add them into a unique-case total.

| Preserved result | Outcome/report SHA-256 |
| --- | --- |
| Initial cache 38P/19F | `7a2d0a998fd441f285cd8255858b474f3946c208057b48ec2b4b5e42943e1bdd` |
| First positive gate 1P/1F | `a593b440c9052543cfeb18a335594b5bd21e862862f5ac8940a61be0072024b9` |
| Constructor diagnosis before fix | `e0cc98556f38b795d8ba273dc75b66e1047602e41e0d4120980c238f1f34f8cf` |
| Final positive gate 3P | `60fd13fc4548d14e48f06de84883ac4fab351b198f253d21b5cea2a0761d98fd` |
| Constructor diagnosis after fix | `fa8b3116aaa1b8aba61908f59d19ed51bdc67be1e14dc33a66e395aecb7d9ff7` |
| Final legacy subset 118P | `508f6f11a1b547ba77783f80c99ed1aca720384465c79f97751c27e189ce850f` |

Lossless selected-result archives retain [initial failures](bc1_validation_2026-10-27_cache_initial/manifest.json),
[the first positive attempt](bc1_validation_2026-10-27_cache_positive_initial/manifest.json),
[the causal diagnostic](bc1_validation_2026-10-27_cache_diagnostic_before/manifest.json)
and [verified cache/legacy checks](bc1_validation_2026-10-27_cache_verified/manifest.json).
These manifests identify original paths, bytes, modes and exclusions; complete
synthetic run directories remain external. The diagnostic's bounded trace
includes harmless `GeneratorExit` notifications; the causal evidence is the
five constructor-token differences, not an inference that every traced event
is an application failure.

Remaining release work: owner review/application of the exact protected proposal,
fresh installed-source registrations, actual six-project/arm sizing on selected
inputs, cross-branch integration review, scientific approval of changed model
access, and a separately authorized canary. Recorder Priority 1 remains subject
to its independently recorded idle-host gate; BC1 tests do not clear it.
