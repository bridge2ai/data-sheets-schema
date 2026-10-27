# BC1 bounded audit implementation — Wave 2, 2026-10-27

BC1 is an explicitly selected **new model-access condition**. This local branch
implements its codec, staged audit, recovery controller and registration sizing.
It does not authorize generation, scientific scoring or native-arm execution.
The protected shared-generation hooks are an **unapplied proposal**; the default
remains the historical implementation and BC1 selection refuses without hooks.

Branch: `codex/bc1-production-impl-20261027`, isolated worktree
`/private/tmp/d4d-codex-bc1-production-20261027`.
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

Initial frozen implementation `b2525adb92159776d3fbeb22ecf41f564143462a`:
**100 passed, 18 runtime fixture setup errors**, zero skips, 34.74s pytest;
tracked bytes unchanged and module origins verified. Outcome SHA-256
`df08568d305250e15e09173e4f371001e91642d1d58ba606164b4bed610d49cc`.
The failed batch is retained. Corrected controller, genuine public API pipeline,
write-footprint and affected legacy verification are pending; no final passing
suite claim is made at this checkpoint.

Remaining release work: owner review/application of the exact protected proposal,
fresh installed-source registrations, actual six-project/arm sizing on selected
inputs, cross-branch integration review, scientific approval of changed model
access, and a separately authorized canary. Recorder Priority 1 remains subject
to its independently recorded idle-host gate; BC1 tests do not clear it.
