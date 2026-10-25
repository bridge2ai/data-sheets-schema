# CHORUS generic_v10: declared native/API package differences

Prepared 2026-10-25 for N2c / #4354. **Declared differences, based on the completed independent r1 render review; no launch or scientific acceptance is asserted.** The comparison is between two complete generation packages. Sharing scientific assets does not make their complete instructions, effective stage inputs or execution procedures identical. Subsequent source-head parity and runtime acceptance results are recorded under `### codex` in the primary [STATUS.md][status]; the r1 evidence here remains immutable.

The owner's D26 decision selects the **default runtime profile** for Track N and names it **native agentic (direct arm)**. Profile1, the optional selected-owner execution protocol, is outside this delivery. It is distinct from both the `bridge2ai` scientific profile and the schema-owner context that the generation protocol still requires. Claude reviews this declaration; the owner reads it before any native launch. The decisions and required document contents are recorded in the [N2 prompt][n2-prompt].

## Package identities and output labels

| Identity | Native agentic (direct arm) | API arm |
| --- | --- | --- |
| Output route | `claudecode_direct` | `claudecode_api` |
| Selected shared protocol | `native_shared_generation_v1` | API shared generation v1 |
| Renderer | 26 | 25 |
| Receipt completion policy | Native v1 | API v2 |
| Execution | One native session with typed helper stages | Controller-managed API calls for ordinary and typed stages |
| Runtime profile in this delivery | Default; profile1 excluded | API runtime declaration |
| Full output directory | `data/d4d_concatenated/claudecode_direct/<label>/` | `data/d4d_concatenated/claudecode_api/<label>/` |
| Core output directory | `data/d4d_concatenated/claudecode_direct_core/<label>/` | `data/d4d_concatenated/claudecode_api_core/<label>/` |

Every accepted record must retain its actual registered label, project, source/context/schema and scientific-asset hashes, renderer/protocol selectors, runtime/model/provider/effort declarations and attempt identity. A directory name does not replace those declarations. Any table or figure comparing the arms must retain the arm and replicate identity. Typed worker outputs are components of one generation, not independent replicates. Historical labels and artifacts stay unchanged.

The native model/account/effort/caps and the exact comparison baseline remain properties of the selected registration; this document does not supply them from hypothetical sizing inputs. Native subscription use cannot be reported as API-equivalent tokens or dollars without measurements that establish that conversion.

## Source and evidence boundaries

The N2 series starts at the **cached** `origin/feat/v10-preflight-scripts` commit `7c1002caeb776ccb0caebb474e22e5558b7b9602`. This is a local Git identity, not a claim that GitHub has been freshly checked. N2a's [coordination record][status] establishes that the default behavior is distinct but the later N1 implementation still imports owner-profile modules through authority/controller/registration and receipt/recorder paths. It therefore requires a source cut, rather than merely omitting the owner tests. The recovery uses default-path modules from `a33d80d84c70cc9ee557f15d6e34fa73fc14f153`, before owner integration `123835c136492638d05206c31794bb38e90d4315`, plus individually reviewed later independent fixes and the N1 trial's protocol/rendering material.

The caller-side selection cut in [unit1 recovery][unit1-recovery] skips the API-only selector only after strict native validation, leaving `src/data_sheets_schema/shared_generation.py` unchanged. Neither that protected file nor `data/generations/canonical_hashes.yaml` is authorized for modification in this series. Permission and subscription libraries arrive with unit2 because registration/readback depend on them; unit3 supplies probe production and guard-enforcement regressions. Unit1's frozen head `44deb52206e4499cac93cd404970d5e753022f86` passed all **235 tests**, with zero failures, errors or skips and process exit 0, across its nine selection/contract/rendering and unchanged API regression modules. The [XML][unit1-xml] and [log][unit1-log] retain the 227.03-second run and one dependency deprecation warning. An earlier run passed its cases but failed the repository notes-preservation guard during concurrent documentation editing; it remains a failed run and is not the credited result. The final four-head integration and execution gates remain pending until recorded in the series handoff. N2a's dependency finding and the unit1 tests do not themselves prove complete-path acceptance.

The substantive differences below come from three explicit sources:

1. The complete **seven-hunk rendered comparison** and its [independent hunk/stage review][render-review], generated offline at `9315de8125e9504336a18bed4affb34c7662e8d0` in `current-target` mode. Its scope was `hypothetical_offline_not_registered`. The [actual diff][render-diff] has 843 lines / 110,807 bytes, SHA256 `bf82e8cb7cba8b1b928a0272e9cbfe50402d4750a3403491fa7770def796fe1e`.
2. [N1b §5.1–5.3][n1-assessment], including the distinction between a package comparison and a runtime-only experiment. Its earlier positive default-path results must be read together with the later N1c failure, below.
3. The complete current r1 render and [independent delta review][n2-delta-review], including every current hunk, both historical-to-current diffs and decoded recorder metadata. The review's [structured result][n2-structural-deltas] is SHA256 `f41074d24d223704a0e40dbf7f93346a884a0f95be372bbc7fb6a202ec8a6e85`.

The N1 evidence paths remain outside the N2 Git tree. The r1 artifacts and structured review result are retained inside this tree under `notes/native_n2_render_evidence_2026-10-25/`; their original paths are preserved below. Neither set is a current-head execution result or a claim of GitHub publication. Source references in the stage table refer to the reviewed N1 trial snapshot unless explicitly identified as the N2 base or r1. Future rebasing or scientific-asset changes require checking the applicable rows again; this declaration does not automatically describe every later API candidate.

### What was and was not byte-identical

| Historical rendered artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Current-target API25 instruction | 84,736 | `489a4b59f675990bf2b37921be1a234bdac9dbe05f6ea3c031ed2c5b06dfcc78` |
| Hypothetical native26 instruction | 136,697 | `0b693a535bdccfb6d8f5f49410fc84b82c8af396cb2d82b68a3c84257f344ca4` |
| Each extracted uniform-rule section | 23,369 | `99ca630daa6fd80fe79bc074e95dbc0401249d9c9f654d60bf8f25206c16be42` |
| Complete R9 passage in that comparison | 2,213 | `debc8c4b03c616bed942eb9623f2f9a469e82cf0f5106d65bebeb551461e861a` |

The two extracted uniform sections were identical, and that complete R9 passage appeared verbatim exactly once in each instruction. **That render predates the final R9 correction.** The later [N1c alignment report][r9-report], at `db0573d96bb16ee32d3537ea0a9ad0ca607e355a`, checks a composed offline asset closure with the reviewed 4,433-byte R9 passage (SHA256 `2ae71e83e11a096764b63bc4037786d756d5e31523e3fe71701505b976eaf765`). It reports one occurrence in the projected rules and three stale-pin refusals. Its projected rules are 37,787 bytes, SHA256 `5a892a18910f51cc1e35b74c3c4a7dedda35dd9148e9359343f0b930ce6b438e`.

The later asset check is not a fresh full API/native render, an installed-target test or scientific approval. Unit4's first fresh full render is recorded below. The historical seven-hunk findings remain separately identified; equal hunk count does not mean their text or scientific conditions stayed unchanged.

The historical 2026-10-22a API instruction is also a separate artifact: 85,348 bytes, SHA256 `28b8805d17092b5b5a7b34b3ff93f7a83fe753cac1e5cbdb53ce8bb9c76badd3`. The [historical-byte review][historical-review] proves an additional 612-byte report-contract paragraph relative to the fixed current-target instruction, introduced by later source commit `77b94e457`. Its flat-assertion format changes procedure; claim/source-status agreement and qualification requirements affect scientific representation. Historical typed packets also contained eight differing contract/stage/seal fields. Matching prompt-file hashes alone therefore does not establish that 10-22a is a matched baseline for a new native run.

The original relocated API CLI refused a physical-root vocabulary mismatch. The offline current-target render retained this refusal and disclosed its historical resource access; it did not waive the guard or demonstrate a successful registered launch.

### Unit4 full render r1: current assets, hypothetical fixture

The first complete unit4 render used frozen source **`f0f980858506c60e769f54c5a85d58026568d4eb`**, with source Git tree `0413e0d0d2989684ccc17cc071cadd1fad75976d` and committed helper `scripts/adhoc/native_n2_render_parity_20261025.py` (SHA256 `24c25f12b941d2384d37496098ea80d55732698d83cda10257c500b60d0ea6a6`). Its [report][n2-render-report], SHA256 **`3d96966a29deb0c096ec7ce1164285f120111f5a8c33f8c619505277b1ad6de3`**, records `completed_offline_render_parity`, unchanged sources/inputs and captured module origins. Its scope is explicitly `hypothetical_current_package_render_not_registered`; `acceptance_eligible` and `launch_authorized` are false, and scientific acceptance is not assessed.

The linked copies preserve exact bytes from original render directory `/private/tmp/d4d-native-n2-parity-20261025-r1/`. The completed independent structural result was originally `/private/tmp/d4d-native-n2-delta-review-20261025/complete/structural_deltas.json`; the review records its helper and reproduction command. The render report's original classification field says independent review is pending because the report predates that review. Its bytes are retained unchanged; the linked completed review supplies the subsequent interpretation.

| r1 artifact | Bytes | SHA256 |
| --- | ---: | --- |
| [Current API25 instruction][n2-api-instruction] | 87,577 | `2e8efbeb608959740cd80ecdcddee35e965928525fe4564046c68bb0d3314083` |
| [Current native26 instruction][n2-native-instruction] | 131,395 | `cc503fd057e73ccef748f3f3d4926011d4b7eb1738a6d68bca3160846d5d9241` |
| Each extracted uniform-rule section | 25,589 | `c5c5b36189ee163f5669d514955a20ce6345b02fc839a39221d05afe0f56d0ee` |
| Complete R9 passage, exactly once in each instruction | 4,433 | `2ae71e83e11a096764b63bc4037786d756d5e31523e3fe71701505b976eaf765` |
| [Current API/native raw diff][n2-render-diff] | 103,909 | `00001a136c7277cbed96f56ed27aec0a543a0f4ff94c3b8a6c33fa3f2e2c8094` |
| [Historical-to-current API diff][n2-api-delta] | 10,045 | `305bfe1ac460818260680281cd3becaa6c5ab7c2a21d5f0c60cd4dd7668f15a0` |
| [Historical-to-current native diff][n2-native-delta] | 106,560 | `06d6c6624605ad4191403f9ef339d1f49043cd3b0fa27c84f335e3fb12df76f2` |

Uniform extraction uses unique start/end markers and trims surrounding whitespace only. The 25,589-byte extracted section is distinct from the earlier 37,787-byte composed projected-rules artifact. The selected current generic-v10 asset hash is `95511eeea60e5112c630c28bcc342f132d14efcf0d5485bbf26f3e81a0f4cc99`; the uniform-v2 asset hash is `cbf7e9f53e97a1d7dd953507308825e3c835daabcb8f6ee0a6a5dcd8bb9a048f`.

Both renderers select the same pinned original 10-22a CHORUS source inputs; the evidence directory also preserves captured copies. Their byte identities are:

| Retained scientific input | Bytes | SHA256 |
| --- | ---: | --- |
| Complete bundle | 35,920 | `27625709112a7b7796f4e778fcc33df9f908ba95e47dbc0b6e23a535cacc237c` |
| Chunk manifest | 1,945 | `ec9d81c54758d9db78ccc98a0a1de01643d224255f11f183cfebc2cfd793108a` |
| Generation context | 6,476 | `ac94a74bd0d7d6c656564d67e656c7dbcf6627dca4c147a876eded072a81a3b0` |
| Source manifest | 40,612 | `0c5078c84f81294488e1a32c61dfa0a468cd03bf4ca318bc3c3a24be8ea84528` |

The full/core schema and vocabulary bytes also match their historical pins, but r1 explicitly selects their current physical unit4 paths. Current prompt assets and configuration come from the frozen unit4 source. Historical registrations, ledger and instructions remain untouched. The original physical-root vocabulary refusal remains retained evidence, not a bypassed check.

The evidence directory contains a synthetic API registration fixture for the production offline rendering path, with a nonauthenticated hypothetical provider and `https://example.invalid`; no registration CLI, actual attempt or native runtime was run. Labels are `hypothetical-n2-render-20261025-api` and `hypothetical-n2-render-20261025-native`. Native selection/render carriers remain in memory and declare hypothetical limits, including two attribution drafts, rather than measured or approved launch limits. The API fixture retains historical CHORUS overrides: typed worker/omission/integration output caps 64,000 / 32,000 / 32,000, aggregate output 320,000, aggregate input 4,000,000, 18 calls and partition 80 / 12,288 / 4. These are neither current builder-default claims nor proof of matched native limits. Both receipt floors remain pending.

The current diff contains seven hunks, with headers listed below. The completed independent review covers all seven, both historical deltas and embedded recorder metadata. H6 contains additional model-visible API report guidance; both arms use expanded R9 rules compared with N1b. These are substantive declared differences, not path drift or unchanged historical conditions. **r1 is reviewed render evidence, not final unit4 runtime acceptance.** The later unit2 target-parser dependency correction `7ada9e7c4e817033cd7ed5c5fbe69ee453969895` and ongoing default permission-performance recovery postdate this render. Final-source parity and runtime results belong in the primary [STATUS.md][status], tied to their exact tested heads. A later render must preserve the scientific-parity checks and review any changed content; it need not reproduce every r1 byte when explicit hypothetical paths, labels or source identities relocate.

### Later API floor and budget decisions are separate source versions

Cached N2 base `7c1002cae` records D32 as a documentation decision; its API implementation does **not** yet contain A12/A13. The distinction matters when naming the eventual API comparator. The source checks below use exact local Git objects, not a claim that any branch has merged on GitHub:

| Selected source | Receipt-floor behavior | Output/partition behavior |
| --- | --- | --- |
| N2 cached base `7c1002caeb776ccb0caebb474e22e5558b7b9602` | `receipt_completion_policy.parse_registration` accepts a registered floor containing only `state`, `numerator`, `denominator`; `evaluate_floor` gates `with_receipt / receiptable`. | API report/reconcile caps are 96,000, route-clamped; report regate uses the report cap. The registration builder's defaults are worker/omission/integration 25,000 / 16,000 / 16,000, fixed aggregate output 150,000 and 18 calls, with default partition 384 paths / 65,536 bytes / 4 workers. These defaults are not a claim about historical canary overrides. |
| A12 `65e4133b35297b21dfa0ad72ca62a2c0ad77173f`, also present in the A13 merge below | No new floor meaning from A12 alone. | Shared-v1 report/reconcile become 128,000, route-clamped, and regate uses the report cap. Builder defaults become 64,000 / 32,000 / 32,000; explicit partition bounds are required, with the CHORUS baseline profile 80 / 12,288 / 4. Aggregate typed output is `max_workers * worker_output_tokens + omission_output_tokens + integration_output_tokens`; default typed call allowance is `max_workers + 2`. Receipt completion has its separate allowance. |
| A13 F1 / D32 implementation `f8c5ac73caba610d40c49aaceddb31ead3590a72` | API receipt-v2 registration may explicitly select `basis: receipted_part`. The denominator becomes `receiptable - added_after_receipt_unmatched`. An absent basis retains the old whole-final-record meaning. | Carries A12. Input aggregate remains a separately declared ceiling, not the sum of output caps. The builder still defaults the floor to pending; a numeric floor uses `receipted_part` unless the old `all_receiptable` form is explicitly chosen. |

For A13 F1, `added_after_receipt_unmatched` counts uncovered final leaves whose path **and** typed value are absent from the phase1 snapshot. The older path-only `added_after_receipt` counter is reported, not subtracted. A moved or renamed never-receipted value therefore remains in the gated denominator; an addition repeating a snapshot value remains gated too. Missing phase1 split evidence returns `unmeasurable`, with `passed=false`. This is **execution procedure with a changed scientific acceptance measure**, not evidence of a new model-facing instruction. Source: `receipt_completion_policy.py::parse_registration/evaluate_floor`, `receipts.py`'s phase1 path/value split and `scripts/build_api_registrations.py::parse_coverage_floor`, at the exact A13 head above. The [D32 record][status] and [decision packet][decision-packet] distinguish the re-canary's 19/20 receipted-part choice from later floor decisions.

The recovered native-v1 policy is different from that later API choice. At source `a33d80d84c70cc9ee557f15d6e34fa73fc14f153` and the N1 trial, `native_shared_contract.parse_receipt_policy` admits only the original exact fraction fields; it rejects a `basis` field. `native_shared_receipts.floor` obtains strict `with_receipt` and `receiptable` counters via `coverage_counts` and compares the registered fraction against the full receiptable denominator. It does not subtract `added_after_receipt_unmatched`. Source inspection of the recovered unit2 path as integrated at r1 head `f0f980858506c60e769f54c5a85d58026568d4eb` confirms the same parser and floor behavior, using `receipt_completion_policy.coverage_counts`. A numeric fraction such as 19/20 would therefore describe a different test across the two packages if the API selected `receipted_part`.

This is a source-level confirmation of the recovered default behavior, not new complete-path execution acceptance. Retain the original native meaning unless an explicitly reviewed change selects another condition. This declaration does not authorize changing the native denominator, importing A13, or claiming cross-arm receipt-floor parity. A native pending diagnostic floor also cannot be credited as satisfying the API re-canary's registered gate. The eventual comparison must state each run's actual floor basis and eligible denominator, separately from receipt support or audit recall.

The later API 128,000 stage caps and typed aggregate formula likewise do not establish equivalent native output limits: the native runtime's declared output ceiling is not API per-stage accounting. The final registration must state actual native limits and observed enforcement. Neither A12 nor D32 can be inferred from the string `generic_v10` alone. The fresh unit4 render/acceptance update must name which API source is being compared and recheck these rows if the series base advances.

## Historical seven-hunk classification and current delta

**Scientific** means what the model is told or shown, including structural schema/context exposure and evidence instructions. **Execution procedure** means how requests, stages, receipts, helper calls, corrections and recording operate. A mixed hunk is classified as both. A relocated clause is distinguished from a removed obligation.

The following headers and line numbers identify the historical N1b diff, not the new r1 diff.

| Historical hunk and exact diff header | Declared difference | Type |
| --- | --- | --- |
| H1, line3: `@@ -1,95 +1,40 @@` | API begins with supplied-text/no-tools boundaries, a single requested phase, schema/bundle declarations and phase duties. Native begins with whole-session pair generation, provenance and schema-authority rules, then requires declared-input tool reads. Runtime/header metadata is relocated to H6. Both preserve the prohibition on treating prior generated text as new source evidence, but the presentation and model-reading procedure differ. | Scientific + execution procedure |
| H2, line136: `@@ -450,7 +395,6 @@` | One empty line before the shared rules is removed. No scientific clause changes in this hunk. | Execution procedure: presentation only |
| H3, line144: `@@ -491,152 +435,134 @@` | API RETURN/metadata and protocol7's registered-batch/grammar prefix are replaced by native stages, receipt v1, role review and bounded attribution drafts. Role review moves here from H6. The removed prefix contains scientific duties as well as orchestration: complete evidence, source-first omissions, relationships, dispositions and no held-out answers. Native restates broad duties and later carries raw policies, but the initial text and emphasis are different. Native consumes one raw receipt answer or genuine zero-work, including failed/malformed/interrupted responses; its hypothetical selection allowed two attribution drafts before a sticky terminal check. | Scientific + execution procedure |
| H4, line425: `@@ -663,7 +589,7 @@` | Authoring an audit object becomes contributing under the current stage contract to a checked helper-assembled audit. The following evidence shapes remain unchanged. Assembly changes do not establish scientific acceptance. | Execution procedure |
| H5, line434: `@@ -930,7 +856,7 @@` | Adding `source_review` to an authored audit becomes including it in the checked assembled audit. The final report's claims/source-review obligation remains. | Execution procedure |
| H6, line443: `@@ -1017,128 +943,131 @@` | Native narrows terminal-stop wording to Phase3/4 evidence while allowing Phase1 receipt correction. API's bounded source-metadata projection, audit example and schema guidance are replaced at this location by captured context/vocabulary, source-manifest pin, explicit read/path/receipt/header/seal requirements and draft limits. Common reconciliation/report contracts remain; role review moved to H3. Native requests full schema imports. API supplies generation context separately in effective requests, so its absence from one top-level string is not proof of absence from the model's input. | Scientific + execution procedure |
| H7, line689: `@@ -1223,50 +1152,108 @@` | API receipt-runtime-v2 policy/registration is replaced by native exact helper commands and recorder metadata; native receipt v1 was already inserted in H3. Commands span source/schema/receipt checks, stage advancement, core derivation, inventories, attribution drafts, final evidence and recording. Embedded scientific assets/context are model-visible inputs; command ordering, destinations, seals and attempt metadata are procedure. Hypothetical runtime/permission declarations are not observed runtime evidence. | Scientific + execution procedure |

H2/H4/H5 are procedure-only; H1/H3/H6/H7 are mixed. This classifies all historical diff hunks. It does not reduce the full comparison to these headings: effective per-stage inputs and actual runtime behavior also matter.

The independently reviewed r1 current diff retains these seven positions, but H6 adds a scientific/procedural asymmetry beyond that historical classification:

| Current hunk | Exact r1 header | Current disposition |
| --- | --- | --- |
| H1 | `@@ -1,95 +1,40 @@` | Scientific + execution procedure; current fixture identities are hypothetical. |
| H2 | `@@ -481,7 +426,6 @@` | Presentation only; shared-rule location moves after R9 expansion. |
| H3 | `@@ -522,152 +466,134 @@` | Scientific + execution procedure; same native-stage versus API-prefix distinction. |
| H4 | `@@ -694,7 +620,7 @@` | Execution procedure; helper assembly wording. |
| H5 | `@@ -961,7 +887,7 @@` | Execution procedure; assembled source-review wording. |
| H6 | `@@ -1048,130 +974,131 @@` | Scientific + execution procedure, including the additional API-only final-report clarification below. |
| H7 | `@@ -1256,50 +1183,108 @@` | Scientific + execution procedure; the completed structured review distinguishes two changed scientific-asset pins from hypothetical paths/identities and confirms unchanged numerical bounds. |

In current H6, API final-report guidance explicitly requires flat claims, equality of supported claims' `claim_status` and `source_status`, `unstated` only for revised claims, and qualification/status agreement. That paragraph is absent from both retained N1b instructions and from r1's native top-level instruction. The underlying native evidence protocol already contains related shape and status duties; the new explicit placement is still a **model-visible scientific and procedural asymmetry**, not evidence that native validation permits those violations. It must be disclosed when comparing the packages.

Both old-to-current diffs expand R9 from 2,213 to 4,433 bytes: access-condition precedence, the least restrictive tier containing the dataset's own data, exclusion of metadata/documentation/code/sample/synthetic-only tiers, more specific HIPAA evidence, and factual derivation limited to the two named enum slots. These are substantive shared scientific-instruction changes. Exact current R9 equality does not imply equality with the historical canary. This describes the generation instrument; it is not an independent scientific or legal endorsement of its rules.

The [completed structured review][n2-delta-review] parsed all **17 command roles**, retaining all **37 changed command tokens** outside decoded recorder JSON: they are relocated paths or run labels. Its **74 changed recorder leaves** include two scientific-asset hashes/lengths and their resulting descriptor/registration identities, paths, labels, IDs, date and hypothetical limit-basis prose. No numerical bound, attribution-draft allowance, runtime model/provider/effort, receipt floor or protocol version changed between the historical hypothetical native render and r1. Generation context differs in exactly one leaf: its vocabulary identity path; scope assertions, source policy and raw vocabulary comments are unchanged. These are comparisons of declarations, not proof of actual reads or behavior. The raw reports remain immutable; this declaration records the subsequent interpretation.

## Effective stage and runtime differences

This table follows the [source-verified stage crosswalk][render-review]. It describes construction, not proof that a native model read every declared file or completed a stage.

| Stage or condition | API package | Native package | Type and consequence |
| --- | --- | --- | --- |
| Full generation | `api_runner.py` builds supplied complete chunk-marked bundle text, schema digest, ranking/naming/scope, selected generation context, phase instruction and API system message. | `native_shared_render.py` requires reads of the complete bundle/chunks/source manifest and full schema imports, then separate original full/receipt files and validation/sealing. | Scientific + execution procedure. Equal source hashes do not establish equal schema presentation, reading, attention or phase framing. |
| Message roles and conversation | Ordinary phases have the API phase system message; typed stages use their dedicated system message and separately constructed requests. | The model runs inside a native session with runtime instructions, tool observations and prior session history. | Scientific + execution procedure. Policy placement, accumulated context and runtime/tool behavior are registered conditions; the comparison does not isolate transport. |
| Receipt completion | Receipt v2 continuation carries the complete prior exchange and uncovered inventory under API transport, accounting and delivery controls. | Receipt v1 returns one raw answer or verified zero-work under a helper boundary, preserves distinct original/effective receipts and carries raw policies, generation and schema-owner context. Core does not exist before derivation. | Scientific + execution procedure. Shared quote-versus-support caveats and fixed-denominator duties do not equalize delivery, parsing or prior context. |
| Receipt parsing | The retained API decoder accepts one enclosing YAML fence. | Native decoding refuses that envelope. N1b sizing removed only the envelope to reuse historical content as a named proxy. | Execution procedure. The 1,958-byte historical answer and its 1,946 inner bytes are different submitted artifacts; proxy transport conversion is not native acceptance of the original bytes. |
| Receipt floor | Cached 7c uses the whole-final-record denominator; later A13/D32 API v2 can select `receipted_part` and subtract only `added_after_receipt_unmatched`. | Recovered native v1 accepts the old exact fraction fields and uses the whole receiptable denominator; no basis selector is supported. | Execution procedure and scientific acceptance interpretation. Equal fractions are not equal gates when denominator bases differ. Integration and any later native policy decision remain explicit, as detailed above. |
| Typed workers | `typed_audit.py` constructs compact shared context; `typed_audit_runtime.py` adds common policy, evidence, receipt carry, trimmed schema, generation context, binding and the inner request. It does not append the full top-level instruction. Each worker is an API call. | `native_shared_stage.py` wraps each inner request with all captured raw scientific policies and additional schema-owner context; the initial instruction remains in session history. Workers are logical stages of the session. | Scientific + execution procedure. Repeated raw policy and structural exposure differ. API has schema enums/trimmed owner context, so describing it as having no schema is incorrect. Workers are not experimental replicates. |
| Omission catalog | At the reviewed snapshot and cached N2 base, API removes `classes`/`slots` from the omission wire and supplies induced Dataset/Software/occupied-owner structure with slot descriptions, comments and mappings removed by `_TRIMMED_SLOT_KEYS`. | Native supplies the complete prepared omission request plus full omission schema/owner classes in outer context. | Scientific + execution procedure. This is a substantive structural-exposure difference. Later API schema-context changes require a new assessment; the current declaration does not silently apply to them. |
| Integration | A separate API request supplies the typed index and selected policy/omission/receipt/context contracts. | Integration follows completed receipt/workers/omission within the native session and retains the fuller outer policy/context wrapper. | Scientific + execution procedure. Both require authored dispositions and checked assembly, but context history and policy repetition differ. |
| Reconciliation | API carries prior artifacts and adds detailed `phase_instruction`, schema context and generation context. | Native instructs reconciliation after checked assembly, preserves supported content/qualifications and includes the shared reconciliation evidence contract. | Scientific + execution procedure. Common evidence clauses do not make all elaboration or context placement identical. |
| Final report and recheck | API builds computed audit counts, core inventory and final source-review inventory, plus detailed report/recheck instructions; its controller has a one-time `report_regate`. Current r1 additionally exposes the explicit flat-claim/status/qualification clarification in H6. | Native orders source-inventory reads, uses its report evidence contract and registered attribution draft-check allowance, then a terminal evidence check. It has related evidence-protocol obligations but lacks that API-only explicit paragraph and the matching top-level API computed-count block. | Scientific + execution procedure. Reporting presentation, explicit guidance and correction opportunities differ. The hypothetical allowance of two drafts is not an approved future registration value. |
| Recording and saved result | API controller owns provenance and destinations. | Native uses exact helper/recorder commands, including the saved instruction in `D4D_LAUNCH_INSTRUCTION`, selected render metadata and independent saved-result reconstruction. | Execution procedure; embedded context remains scientific input. Rendered commands are instructions, not evidence that gates ran or that a saved result is accepted. |
| Bounds and accounting | API reports provider usage, cache counters, per-request caps, stage/control retries and elapsed request accounting. | Native declares runtime/request/evidence/output ceilings, subscription guards and available observations. Its output declaration is not API per-stage enforcement or a measurement of actual hidden/context tokens. | Execution procedure. API dollars/tokens cannot quantify native weekly share. Quota, output growth and wall time remain unmeasured until an authorized observed run. |
| Permissions, lifecycle and resource access | API uses its registered client/endpoint and controller execution. | Native also requires captured binary and permission evidence, one-use reservation, fresh subscription/no-overage evidence, timeouts, first-error/cleanup behavior and terminal/readback checks. | Execution procedure. Synthetic offline peers do not prove installed binary, authentication, permission or quota compatibility. These conditions affect feasibility and must remain visible in the comparison. |

The scientific context itself needs careful interpretation. CHORUS's captured context declares the target referent, source hierarchy and vocabulary. The reviewed native instruction also exposes raw vocabulary comments containing historical corpus diagnostics and a statement about absence of a dataset DOI; recorder metadata repeats captured context. These are model-visible declarations, not independently verified applicability or support judgments. API effective requests separately carry generation context, so a missing top-level phrase does not prove unique native exposure. No behavioral contamination or effect was measured by the render review.

The common obligations remain substantive: preserve source/claim qualifications, account for every registered chunk including negative/redundant chunks, preserve candidate dispositions and lineage, derive/check assembly independently, rederive core and retain schema/pair/removal/attribution/final-evidence gates. A copied sentence, valid receipt, byte-identical asset or successful checker does not establish scientific support. In particular, a pending receipt floor remains pending and cannot be relabelled strict success.

## What the comparison can support

- Compare outcomes of the two **registered complete packages** on the selected CHORUS inputs, with the above differences disclosed and actual run/evaluation identities retained.
- Report measured completion/failure, accepted output characteristics, receipts, timing, cost or quota observations within the limits of each arm's measurements.
- Use a registered canary to demonstrate feasibility and the measured outcome of that particular package/run.
- Apply a subsequently approved blinded evaluation and report its actual acceptance scope and unresolved human judgments.

It cannot isolate the causal effect of runtime, tool use or agentic execution alone; claim identical effective prompts from shared asset hashes; treat workers as replicates; establish general superiority or scientific equivalence from one canary; infer human-reviewed support/applicability from software gates; convert API accounting into native subscription share; or retroactively treat historical 10-22a as a matched current baseline. Native outputs also need an approved rating/registration route before they can be joined to API/v8 ratings. The [E3x design note][e3x-design] at local head `d6eed9274145a7999b96622957ba1f95167c7ef4` proposes a separate E5-direct route after N11, with explicit native authority and shared identity-aware blinding. It is a design proposal; neither this declaration nor that note adopts the route, supplies human decisions or authorizes scoring.

If a later question requires a matched-input or runtime-only experiment, it needs a separately versioned condition and approval. Existing outputs and evidence must remain intact rather than being rewritten to create apparent equivalence.

## #4354 acceptance ledger

The [original local #4354 body][issue4354] is the acceptance source. The historical [generation plan, N2–N3][generation-plan] additionally requires both selected public native fixtures to finish inside their unchanged **900-second** runtime limit, exact-head green tests/CI, independent review and delivery verification. D26 removes profile1 from the canary path; it does not waive the default-path gates. The shorter earlier offline-acceptance summary is not treated as proof of present acceptance.

The table records the declaration's r1 evidence cutoff. Subsequent final-source parity, integrated-head test outcomes and 900-second fixture results are reported under `### codex` in the primary [STATUS.md][status]; no later pass is inferred here.

| Requirement | Evidence needed for this series | Status at the r1 evidence cutoff |
| --- | --- | --- |
| 1. Explicit additive selection and captured identities; refuse missing/conflicting declarations before consumption | Unit1 selection/contract tests; preserve old selectors and historical artifacts; exact source and asset identities | Unit1 at `44deb52206e4499cac93cd404970d5e753022f86`: 235 passed, zero failures/errors/skips, exit 0; final integrated-head acceptance pending |
| 2. Correct selected neutral rules and actual phase protocol; long shared contract occurs once | Unit4 full native/API render, complete R9/uniform extraction and occurrence checks, all new differences reviewed | r1 at `f0f980858506c60e769f54c5a85d58026568d4eb`: 25,589-byte uniform sections equal, 4,433-byte R9 exactly once each; independent review of all seven hunks, both historical deltas and structured metadata complete, with H6/R9 differences disclosed. Final-source parity is separately recorded in STATUS.md. |
| 3. Real supervisor-boundary receipt → workers → omission → integration → independent assembly | Default-path execution and adversarial cases for mandatory chunks/workers, immutable inputs, exact requests/replies and checked disposition lineage | Fresh series-head completion and fault results pending |
| 4. Exact assembly/audit carry through reconcile, full owner context, final gates and saved readback | Genuine offline helper path, rederived core and recorder/readback assertions; no success-flag-only acceptance | Historical neutral recorder timeout unresolved; fresh 900-second gate pending |
| 5. Permission/authority/one-use/timeout/first-error/cleanup/readback; honest unsupported limits | Unit3 guard/lifecycle tests plus final integration; no relaxed deadline, invented usage or strict success from pending floor | Fresh series-head evidence pending; real binary/account evidence remains a later separately authorized gate |
| 6. Public adapter with ordinary Python peer and genuine helpers; correction and adversarial failures | Both public completion fixtures plus missing/stale workers, omitted chunks, changed authority, unrelated assembly, corrupt lineage, interruption and cleanup cases | Synthetic evidence only; final fixture runs pending |
| 7. Descriptor/guide/scanner and delivery review after full-path validation | Four local heads/test records, final source-scanner checks, independent adversarial review, exact-head full CI and merged-byte verification | Local staged delivery in progress; no published/merged acceptance asserted |

The two default-profile public nodes are:

- `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`
- `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`

Their common fixture explicitly declares `deadline_seconds = 900`. Successful synthetic completion must include `runtime_gates_passed`, `completed_pending_independent_review`, all required checked gates, saved readback and repeat-launch refusal. It must still report `scientific_acceptance: not_assessed`. Passing these fixtures would establish bounded software behavior, not actual native binary/provider/scientific acceptance.

### Every N1c-3 failure and its disposition

The completed N1c full run at `2a9c60d435f9aaa7bf94596eae3bb4f16e638d77` recorded **22,363 passed, 15 failed, 0 errors and 46 skipped** across 22,424 cases. Its [XML][full-xml] SHA256 is `5b90b42c72dee5c33be4ce071f1605bf73db42a2f22f7d683adeac2932bc9f3f`. Skips are not passes. Sources and before/after identities were stable; that makes it a valid failed run, not green acceptance.

Rows1–14 are selected-owner failures. **N2's default-profile cut leaves each deferred and unfixed on the original lane; exclusion is not a repair.** The failure mechanism is stated only as far as the retained traces establish. Several intended adversarial assertions were never reached because earlier deadlines stopped the run. Prior intermittent passes and same-node original-N failures do not prove a common cause or inheritance from target main.

| # | Exact failed node | Last observed boundary | N2 disposition |
| ---: | --- | --- | --- |
| 1 | `tests/test_native_owner_receipt_process.py::test_registered_receipt_process_reads_current_inputs_with_real_clock` | Expected incomplete-terminal refusal was masked by owner deadline; receipt child exhausted its remaining window. | Profile1 deferred/unfixed; no default-path credit |
| 2 | `tests/test_native_owner_stage_helper.py::test_registered_helper_process_publishes_first_receipt_stage_with_real_clock` | Expected incomplete-terminal refusal was masked by owner deadline after phase1 seal; advance child timed out. | Profile1 deferred/unfixed; no default-path credit |
| 3 | `tests/test_native_owner_stage_helper_adversarial.py::test_independent_scope_direct_publisher_and_terminal_context_boundaries` | Pre-admission owner deadline; intended publisher/terminal-context injections masked. | Profile1 deferred/unfixed |
| 4 | `tests/test_native_owner_stage_helper_adversarial.py::test_helper_refuses_ambient_budget_and_malformed_selected_discriminators` | Pre-admission owner deadline; prior cost comparison censored by unequal progress. | Profile1 deferred/unfixed |
| 5 | `tests/test_native_owner_stage_helper_adversarial.py::test_helper_domain_precedes_deadline_and_expiry_precedes_loader` | Pre-admission owner deadline; intended ordering injection masked; isolated integrated pass exists. | Profile1 deferred/unfixed |
| 6 | `tests/test_native_owner_stage_helper_adversarial.py::test_equal_owner_bytes_on_another_inode_refuse_bootstrap` | Pre-admission owner deadline; inode refusal assertion masked; isolated integrated pass exists. | Profile1 deferred/unfixed |
| 7 | `tests/test_native_owner_stage_helper_adversarial.py::test_both_actual_cas_callers_accept_proposed_successor_only[publish]` | Pre-admission owner deadline; current run does not reproduce the later historical origin refusal. | Profile1 deferred/unfixed |
| 8 | `tests/test_native_owner_stage_helper_adversarial.py::test_both_actual_cas_callers_accept_proposed_successor_only[append]` | Pre-admission owner deadline; CAS work masked; isolated integrated pass exists. | Profile1 deferred/unfixed |
| 9 | `tests/test_native_owner_stage_helper_adversarial.py::test_both_cas_callpaths_stop_inside_staging_before_replace[publish-persisted]` | Pre-admission owner deadline; staging/no-replace injection masked; isolated integrated pass exists. | Profile1 deferred/unfixed |
| 10 | `tests/test_native_owner_stage_helper_adversarial.py::test_both_cas_callpaths_stop_inside_staging_before_replace[append-predecessor]` | Distinct 65-second waiter assertion: no pending advance within unchanged attempt window. This is not the same observed exception as owner `BudgetStop`. | Profile1 deferred/unfixed |
| 11 | `tests/test_native_owner_stage_helper_adversarial.py::test_selected_cas_partial_write_keeps_first_error_over_close` | Pre-admission owner deadline; partial-write/close-error assertions masked. | Profile1 deferred/unfixed |
| 12 | `tests/test_native_owner_stage_helper_adversarial.py::test_main_acknowledges_only_after_cleanup_and_preserves_body_error[none]` | Helper was admitted; permission/owner reconstruction then hit the deadline before successful scope entry. | Profile1 deferred/unfixed |
| 13 | `tests/test_native_owner_stage_helper_adversarial.py::test_main_acknowledges_only_after_cleanup_and_preserves_body_error[cleanup_only]` | Pre-admission owner deadline; intended cleanup-only fault masked. | Profile1 deferred/unfixed |
| 14 | `tests/test_native_owner_stage_helper_adversarial.py::test_main_acknowledges_only_after_cleanup_and_preserves_body_error[body_and_cleanup]` | Pre-admission owner deadline; intended body/cleanup precedence masked. | Profile1 deferred/unfixed |
| 15 | `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion` | Recorder subprocess exceeded the synthetic peer's 180-second helper timeout; result had incomplete evidence and no terminal. | Default-path acceptance failure; **unresolved until a fresh unchanged-900-second series-head test and saved-result evidence establish completion** |

The [owner classification][owner-failures] and [non-owner classification][nonowner-failures] retain the traces and history. Row15's JUnit duration was **888.565 seconds**, which includes fixture/test accounting and does not prove expiry of the enclosing 900-second runtime limit. The journal reached `assembly_checked` sequence22 and initial provenance existed; no completed inline check blocks or recorder tool result were retained. The [recorder triage][recorder-triage] leaves the internal blocked operation unresolved. Contention, cache cost and a particular recorder function are not established causes.

The omission counterpart passed in that same run in **703.810 seconds**; it does not waive row15. Earlier default-path passes also do not override the later failed gate. The cache repair and scanner suites passed in the N1c full run (44 cache tests and 451 scanner/specificity tests); those narrower passes do not establish complete-path acceptance. N2's fresh results must name their own source heads, fixture outcomes and remaining failures.

## Review and launch boundary

This is the completed r1 comparison declaration and an acceptance ledger, not an authorization to launch. Before delivery/comparison, the handoff and primary [STATUS.md][status] must record validation of the N2a dependency cut, four final branch heads and their test results; pin final-source render/parity evidence and review any changes from r1; resolve or retain every failure with evidence; and obtain the required independent review, exact-head CI and merged-byte verification. Identity/path relocation alone need not reproduce the entire r1 instruction hash, but it must remain explicit in the new comparison. Before any native launch, the selected registration also needs the owner's actual model/account/effort/caps, fresh genuine binary/permission/subscription evidence and explicit launch authorization. Scientific applicability, recall annotations, support, receipt floors and evaluation decisions retain their own review obligations.

No provider call, live probe, real registration, launch, GitHub operation or push was performed to prepare this document. r1 wrote a clearly labelled synthetic registration fixture only in its evidence directory for offline rendering.

[n2-prompt]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/2026-10-23-codex-n2-prompt.md
[status]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md
[decision-packet]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/2026-10-25-owner-decision-packet.md
[n1-assessment]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/2026-10-23-codex-n1-assessment.md
[unit1-recovery]: native_n2_unit1_recovery_2026-10-25.json
[unit1-xml]: /private/tmp/d4d-codex-n2-1-44deb5220.xml
[unit1-log]: /private/tmp/d4d-codex-n2-1-44deb5220.log
[n2-render-report]: native_n2_render_evidence_2026-10-25/r1/report.json
[n2-render-diff]: native_n2_render_evidence_2026-10-25/r1/instructions.diff
[n2-api-instruction]: native_n2_render_evidence_2026-10-25/r1/current-api25-instruction.txt
[n2-native-instruction]: native_n2_render_evidence_2026-10-25/r1/current-native26-instruction.txt
[n2-api-delta]: native_n2_render_evidence_2026-10-25/r1/historical-to-current-api.diff
[n2-native-delta]: native_n2_render_evidence_2026-10-25/r1/historical-to-current-native.diff
[n2-delta-review]: native_n2_parity_delta_review_2026-10-25.md
[n2-structural-deltas]: native_n2_render_evidence_2026-10-25/r1-structural-deltas.json
[e3x-design]: /private/tmp/d4d-codex-e3x-20261025/notes/e3x_evaluation_routes_2026-10-25.md
[render-review]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1b-current-target-instruction-review.md
[render-diff]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1b-render-current-target-20261023/instructions.diff
[historical-review]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1b-api-historical-byte-diff-review.md
[r9-report]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1c-r9-alignment-db0573d96-20261024/report.json
[issue4354]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/.local_drafts/issue_loop_2026-10-02/d4d-native-shared-adapter-issue-root.md
[generation-plan]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/tree/notes/d4d_generation_plan_2026-10-09.md
[full-xml]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1b-n1c-postrepair-full-2a9c60d43-20261023/set-d/pytest.xml
[owner-failures]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1c-final-owner-failure-classification.md
[nonowner-failures]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1c-final-nonowner-classification.md
[recorder-triage]: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n1-2026-10-23/evidence/n1c-neutral-900-recorder-timeout-triage.md
