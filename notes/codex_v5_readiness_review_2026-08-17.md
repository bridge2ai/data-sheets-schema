# Codex readiness review #2 for a v5 generation arm — 2026-08-17

Second independent adversarial review, run after the eight PRs that closed the
findings of the first one (`notes/codex_v5_readiness_review_2026-08-15.md`).

| | |
|---|---|
| date | 2026-08-17 |
| reviewer | Codex (GPT-5.x), via the `codex:rescue` plugin |
| session id | `01a012ef-79a2-7550-a722-546ef5f626ac` |
| resume | `codex resume 01a012ef-79a2-7550-a722-546ef5f626ac` |
| repo state | `main` at `e6b99727` |
| scope | the delta since 2026-08-15: PRs #583, #584, #585, #586, #588, #592, #595, #597 |
| brief | assume the fixes introduced regressions — one already had (#591) |

**Verdict: not ready.** 13 defects — 2 blockers, 8 high, 3 medium.

The review is reproduced **verbatim** below. Nothing has been corrected,
softened or re-ordered, including where it contradicts claims made in this
repository's own PR descriptions or in my messages. Findings disputed after
verification are recorded in the issues filed from this review, not by editing
this file.

Absolute paths in the original have been made repo-relative so the links resolve
from inside the repository; nothing else is changed.

---

# Verdict

Not ready for a production v5 sweep. I found 13 current defects: 2 blockers, 8 high, and 3 medium. The most serious are a canary that accepts a nonexistent baseline, resume invalidation that can preserve downstream work against a replaced full record, known source conflicts that the new tier model cannot resolve, and a generation-record schema that is neither enforced nor mode-specific enough to validate a production record.

The v5 prompt itself is correctly registered and pinned: `d4d api prompts check --strict` reported all 11 prompt files canonical, and the pinned commit reproduces the current SHA-256.

## 1. v5 prompt, genericity, registry, and runtime parity

### Identifier provenance and fragment minting are mutually contradictory

- File: [d4d_generic_arm_prompt_v5.md:222–236](src/download/prompts/d4d_generic_arm_prompt_v5.md:222)
- Severity: high
- Blocks production v5: yes — the central identifier policy has two incompatible answers when evidence lacks an identifier.
- Concrete evidence:

  > “take it from the evidence or omit it”

  is immediately followed by:

  > “Where something needs an identifier and the evidence supplies none, hang it off one the evidence does supply”

  A fragment such as `attested-id#new-entity` is not itself stated in the evidence, so it violates the preceding absolute rule. The same conflict reaches Claude Code through [d4d-uniform-rules.md:70–82](.claude/commands/d4d-uniform-rules.md:70).
- Suggested fix direction: explicitly define fragment minting as a narrowly scoped exception, including when minting is required versus when omission is required.

### The Claude Code playbook still declares v5 to be an unsupported condition

- File: [d4d-full-core.md:164–175](.claude/commands/d4d-full-core.md:164), [d4d-full-core.md:208–214](.claude/commands/d4d-full-core.md:208), [d4d_generic_arm_prompt_v5.md:84–89](src/download/prompts/d4d_generic_arm_prompt_v5.md:84)
- Severity: high
- Blocks production v5: yes for Claude Code runs — the runtime is told to follow two conflicting condition registries.
- Concrete evidence: v5 orders the agent to read `d4d-full-core.md`. That playbook says:

  > “Two conditions exist”

  and defines `generic` as `d4d_generic_arm_prompt.md`, i.e. v1. It then says a run launched without “one of the two prompt files above is neither condition.” The rendered v5 instruction instead requires `generic-v5` and names `d4d_generic_arm_prompt_v5.md` in its headers.
- Suggested fix direction: derive or enumerate all registered conditions from `CONDITION_PROMPTS`, including `generic_v2` through `generic_v5`, and remove the “two conditions” assertion.

### v5’s own metadata still says four rules after adding the fifth

- File: [d4d_generic_arm_prompt_v5.md:3–16](src/download/prompts/d4d_generic_arm_prompt_v5.md:3), [api_runner.py:106–111](src/data_sheets_schema/api_runner.py:106), [generic_v5_analysis_plan.md:16–31](notes/generic_v5_analysis_plan.md:16)
- Severity: medium
- Blocks production v5: no, but it makes the condition and subsequent interpretation inaccurate.
- Concrete evidence: the marked block has five bullets at lines 213, 222, 229, 237, and 241, and the registry correctly calls source priority “the fifth v5 rule.” Nevertheless:

  - the prompt repeatedly says “four rules”;
  - `MULTI_RULE_BASES = {"v2": 3, "v5": 4}`;
  - the analysis plan preregisters “Four rules, in one block”;
  - [test_generic_v5_prompt.py:184–186](tests/test_download/test_generic_v5_prompt.py:184) still asserts the wrong count, despite another test correctly asserting five.
- Suggested fix direction: update all condition metadata and the analysis plan to five; do not change the pinned executable body while doing so.

## 2. Source-priority mechanism

### Known current-versus-superseded conflicts tie and therefore remain unresolved

- File: [source_manifest.yaml:222–227](data/preprocessed/source_manifest.yaml:222), [source_manifest.yaml:249–276](data/preprocessed/source_manifest.yaml:249), [source_priority.py:104–134](src/data_sheets_schema/source_priority.py:104), [api_runner.py:603–615](src/data_sheets_schema/api_runner.py:603)
- Severity: high
- Blocks production v5: yes — the mechanism fails on several explicitly documented release conflicts.
- Concrete evidence: tiers are assigned only by `source_type`. Thus old and current sources of the same type tie even where the manifest explicitly says which is current. Direct calls to `decide()` returned no winner for:

  - AI-READI `dataset_documentation` versus `dataset_documentation_v3`;
  - AI-READI `fairhub_dataset` versus `fairhub_dataset_v3`;
  - CM4AI October 2025 versus June 2026 Dataverse releases;
  - VOICE 3.0.0 versus 3.1.0.

  The API block sends only tier, ID, and source type, omitting `superseded_by`, `captured_at`, and the curation note saying “prefer this.” Meanwhile the agent playbook separately says to resolve conflicts using authority and recency at [d4d-agent.md:183–190](.claude/commands/d4d-agent.md:183), contrary to the equal-tier rule. API and agentic runs can therefore decide these conflicts differently.
- Suggested fix direction: add explicit per-source priority overrides for known supersession relationships, and send the decisive basis to both runtimes. Remove the independent recency tie-breaker or encode it consistently.

### Baseline rankings leak into arms whose manifest is explicitly “not used”

- File: [cli/api.py:13–25](src/data_sheets_schema/cli/api.py:13), [api_runner.py:589–615](src/data_sheets_schema/api_runner.py:589), [api_runner.py:642–653](src/data_sheets_schema/api_runner.py:642)
- Severity: high
- Blocks production v5: yes for crate-only and healthsheet v5 arms.
- Concrete evidence: `crate_only` declares:

  > `# Source manifest: not used (crate-only arm; single declared source bundle)`

  and `healthsheet` similarly says the manifest is not used. But every `build_phase()` unconditionally calls `source_ranking_block(spec.project)`, which reads that project’s baseline `source_manifest.yaml` entries. A CHORUS crate-only request therefore receives rankings for `project_documentation`, `cohort_2_webinar`, and other sources absent from the crate-only bundle.
- Suggested fix direction: make ranking derive from the actual declared bundle/arm manifest, and omit it for single-source arms.

## 3. Canary gate

### The gate is optional, and a nonexistent baseline evaluates as `ok`

- File: [cli/api.py:270–275](src/data_sheets_schema/cli/api.py:270), [cli/api.py:358–361](src/data_sheets_schema/cli/api.py:358), [canary.py:98–133](src/data_sheets_schema/canary.py:98)
- Severity: blocker
- Blocks production v5: yes — a typo disables the baseline comparison without warning.
- Concrete evidence:

  - `--canary-baseline` defaults to `None`, so no gate runs unless the operator opts in.
  - `baseline_for()` returns `None` for every metric when no records match.
  - `verdict()` treats only missing current-run measurements as blind; a missing baseline is ignored.

  A direct probe with baseline `TYPO_DOES_NOT_EXIST` and a current run containing 999 defects in every metric returned:

  ```text
  {'pair errors': None, 'report findings': None,
   'ungrounded identifiers': None,
   'resolver URLs in identifier slots': None}
  ok
  ```
- Suggested fix direction: require a baseline for `generic_v5`, fail if no baseline records or any baseline metric is unavailable, and retain `--no-canary-gate` only as an explicit auditable override.

### A completed first run cannot act as the canary when a batch is resumed

- File: [api_runner.py:2005–2029](src/data_sheets_schema/api_runner.py:2005), [cli/api.py:349–367](src/data_sheets_schema/cli/api.py:349)
- Severity: medium
- Blocks production v5: yes on an interrupted/resumed sweep.
- Concrete evidence: the completed-run early return includes usage, validation problems, and outputs, but omits `checks`. Batch then calls `counts_from(res.get("checks") or {})`; every metric becomes `None`, making the canary `unmeasurable`. Thus a batch interrupted after a successful canary cannot resume and fan out under the same gate.
- Suggested fix direction: return the stored, freshness-verified pair/report/grounding blocks on the completed-run path, or recompute them locally.

### The canary still does not measure three v5 rule families

- File: [canary.py:44–64](src/data_sheets_schema/canary.py:44), [generic_v5_analysis_plan.md:73–93](notes/generic_v5_analysis_plan.md:73)
- Severity: high
- Blocks production v5: yes — it can announce “canary ok” while breaking rules the v5 plan explicitly treats as production checks.
- Concrete evidence: `METRICS` contains pair errors, report findings, absent identifiers, and resolver URLs. It does not measure:

  - fragments on organization identifiers;
  - invented/undeclared prefixes or minted-fragment behavior;
  - generated British spelling.

  These are three of the five preregistered v5 outcome families. The same missing-metric pattern already allowed #591 through once.
- Suggested fix direction: add current-vs-baseline metrics for organization fragments, undeclared prefixes/minted fragments, and generated-prose spelling, using the existing baseline script’s stated counting rules.

## 4. Generation-record schema

### The schema is opt-in and accepts live records without their essential attestations

- File: [d4d_generation_record.yaml:98–201](src/data_sheets_schema/schema/d4d_generation_record.yaml:98), [provenance.py:791–823](src/data_sheets_schema/provenance.py:791), [cli/provenance.py:660–705](src/data_sheets_schema/cli/provenance.py:660)
- Severity: high
- Blocks production v5: yes — neither generation writer validates the record schema before declaring success.
- Concrete evidence:

  - `inputs`, `model`, `prompts`, `playbooks`, `companions`, `validation`, `pair_consistency`, `report_claims`, and `grounding` are all optional regardless of `record_mode`.
  - Their interiors are mostly `linkml:Any`.
  - `ProvenanceRecord.write()` simply calls `yaml.safe_dump`.
  - Schema validation exists only as the separate manual `d4d provenance validate-records` command.

  Consequently a `record_mode: live` record can validate while omitting the bundle, prompt, model, validation verdict, and all post-generation checks.
- Suggested fix direction: introduce mode-specific subclasses or validation rules, require live/API/agentic fields conditionally, and invoke schema validation in both record-writing paths before success.

### Several schema descriptions contradict the records the current writers produce

- File: [d4d_generation_record.yaml:43–45](src/data_sheets_schema/schema/d4d_generation_record.yaml:43), [d4d_generation_record.yaml:72–96](src/data_sheets_schema/schema/d4d_generation_record.yaml:72), [provenance.py:671–692](src/data_sheets_schema/provenance.py:671), [provenance.py:907–933](src/data_sheets_schema/provenance.py:907)
- Severity: medium
- Blocks production v5: no, but these fields cannot be interpreted according to their schema.
- Concrete evidence:

  - `record_type` is described as “Always `d4d_generation_provenance`,” while derived records write `d4d_derived_provenance`.
  - `outputs` is described as “by path and hash,” while `_artifact()` explicitly records no hash and explains why.
  - `schema.digest_md5` is described as the digest “the model was actually sent.” The agentic recorder computes it after generation at [cli/provenance.py:121–126](src/data_sheets_schema/cli/provenance.py:121), although Claude Code reads the schema files rather than receiving the API digest.
- Suggested fix direction: distinguish API-sent digest from agent-observed schema identity, describe output hashes as living in `validation.artifacts`, and enumerate record type consistently with record mode.

## 5. Reconcile/audit/report dataflow

### Resume invalidation is neither transitive nor bound to artifact bytes

- File: [api_runner.py:1189–1206](src/data_sheets_schema/api_runner.py:1189), [api_runner.py:2030–2065](src/data_sheets_schema/api_runner.py:2030), [api_runner.py:564–586](src/data_sheets_schema/api_runner.py:564)
- Severity: blocker
- Blocks production v5: yes — an interrupted run can ship core/report artifacts reconciled against a replaced full record.
- Concrete evidence:

  - Progress stores completed phase names and audit text, but no hashes of the artifacts the audit consumed.
  - When a full artifact is rejected, the code clears producers and only phases directly requiring `"Completed full record"`.
  - `reconcile_core` depends on `"Reconciled full record"` and `report` depends on that result, so neither is invalidated transitively.
  - After `reconcile_full` reruns, `reconcile_core` and `report` may remain in `done` and be skipped.

  Separately, a changed but still record-shaped artifact passes `_looks_like_a_record`; the old audit remains marked complete because no content hash ties it to the audited pair.
- Suggested fix direction: persist hashes for every phase input and invalidate the full transitive dependency closure whenever a producer changes or fails verification.

### The strengthened audit-shape check still accepts structurally unusable findings

- File: [api_runner.py:506–516](src/data_sheets_schema/api_runner.py:506), [api_runner.py:905–917](src/data_sheets_schema/api_runner.py:905)
- Severity: high
- Blocks production v5: yes — reconciliation can receive findings that cannot identify their target record.
- Concrete evidence: the phase contract requires a top-level `summary` and findings shaped as `{severity, record, slot, issue}`. `_audit_is_well_formed()` checks neither `summary` nor `record`; this passes:

  ```json
  {"findings": [{"severity": "high", "slot": "id", "issue": "wrong"}]}
  ```

  Both reconciliation phases are then asked to apply “findings that concern” their respective record, although the accepted finding does not state which record it concerns.
- Suggested fix direction: validate the exact audit object contract, including `record` with an enum and a required summary.

### The report still cannot observe its before/after diff, and repair can invalidate it afterwards

- File: [api_runner.py:544–553](src/data_sheets_schema/api_runner.py:544), [api_runner.py:578–585](src/data_sheets_schema/api_runner.py:578), [api_runner.py:2179–2184](src/data_sheets_schema/api_runner.py:2179), [api_runner.py:2254–2278](src/data_sheets_schema/api_runner.py:2254)
- Severity: high
- Blocks production v5: yes — the human-facing reconciliation artifact can remain stale while its limited check reports success.
- Concrete evidence:

  - The report is asked to state “what was changed in each record.”
  - Its inputs are audit findings plus reconciled full and core records; neither original record is sent.
  - `reconcile_core` overwrites the `"Completed core record"` carry entry with the reconciled core.
  - After the report is written, validator-driven repair may rewrite either record.
  - `report_claims.py` explicitly checks only two narrow claim forms and acknowledges skipped claims at [report_claims.py:24–42](src/data_sheets_schema/report_claims.py:24).

  Thus the report cannot directly compare before and after, and any later repair makes even the supplied post-state obsolete.
- Suggested fix direction: supply both original snapshots and final reconciled records, perform repair before report generation, then generate/check the report against the actual final bytes.

## 6. Reproducibility and silent wrongness

### Flat `--out-dir` runs record standard-layout outputs and companions instead of their real files

- File: [api_runner.py:280–314](src/data_sheets_schema/api_runner.py:280), [api_runner.py:2190–2199](src/data_sheets_schema/api_runner.py:2190), [provenance.py:1013–1016](src/data_sheets_schema/provenance.py:1013), [provenance.py:1250–1256](src/data_sheets_schema/provenance.py:1250)
- Severity: high
- Blocks production v5: yes if the supported flat-output mode is used.
- Concrete evidence: `RunSpec` correctly directs actual artifacts to `out_dir`, but `execute()` calls `build_record()` without passing those paths or an adjusted `concat_dir`. `build_record()` reconstructs outputs under `data/d4d_concatenated/{method}/{label}` and builds companions from the same standard layout. The record written into `out_dir` can therefore describe nonexistent or unrelated output/companion paths.
- Suggested fix direction: pass explicit full/core/report/metadata paths into the provenance builder instead of reconstructing them from method and label.

## Other

No additional confirmed defects outside the areas above. I excluded speculative model-behavior concerns where the repository did not provide an end-to-end control-flow trace.

Verification notes:

- HEAD was `e6b997275073bd595335d5651ff197ab1c1738ef`.
- The prompt registry strict check passed.
- Direct read-only probes reproduced the nonexistent-baseline `ok` verdict and all four same-tier source conflicts above.
- The targeted pytest selection could not start because this read-only sandbox exposes no writable temporary directory; no files were edited.

Codex session ID: 01a012ef-79a2-7550-a722-546ef5f626ac
Resume in Codex: codex resume 01a012ef-79a2-7550-a722-546ef5f626ac


---

*End of verbatim review.*
