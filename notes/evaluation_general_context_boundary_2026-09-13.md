# Evaluation general-context boundary — 2026-09-13

This registers the implementation boundary for #1300, #627, #159 and #1414.
It does not register a model run. No record was generated or rescored, and no
runtime quoted a new definition digest. Earlier evaluations remain the record
of their original instruments; new results must be written beside them under
an explicitly named instrument.

## Work order and verification

Finish the explicit input and recovery work in PR #1367 first. Then merge this
evaluation stage after independent review and full CI, followed by the existing
profile PR #1436 (#1302/#628), then installable packaging (#1301). Use isolated
worktrees, file and resolve review findings, merge only reviewed green heads,
and remove completed branches. Source downloads remain deferred.

Both API and agentic generation remain in scope, with full/core outputs and
all registered input styles. Evaluation includes both rubrics' deterministic
presence checks, direct API quality judges, conversational quality agents and
semantic agents; schema/provenance, grounding/receipt/report checks; source and
record semantic review; and human adjudication and repeated ratings. This
stage changes the rubric execution contracts and reusable identity schemas.
The other evaluation styles retain their existing behavior.

## Instrument and applicability

Presence scoring is instrument version 2.0. Direct API quality judging is
2.0-general-context; quality and semantic agent outputs are version 2.0. These
are distinct instruments. Rubric10 remains binary. Direct API and quality
agent rubric20 numeric scores retain their 0–5 domain; semantic rubric20
retains discrete 0/3/5 bands. Pass/fail questions remain binary. Full maxima
remain 50 and 88.

The caller declares human_subjects, regulated_access, shared_dataset,
ml_training_dataset, data_collection, data_processing and processing_software
as true, false or unknown, with evidence. Source rubrics assign predicates to
items; no project name or missing scoring field establishes non-applicability.
False excludes only its assigned items, with null scores and a named exclusion.
Unknown stays in the denominator. A zero applicable maximum has an undefined
percentage. Fixed and adjusted percentages and excluded-item identities are
reported separately. Equivalent biomedical/clinical governance frameworks
satisfy the same scope; study affiliation earns no credit.

All terminal collection resources are assessed, including nested resources;
distribution evidence belongs to its dataset. Collection metadata is not
implicitly inherited, and siblings cannot fill each other's gaps. Per-item
collection scores are the minimum across all resource scores, under
minimum_per_item_across_all_resource_datasets_v1. Every item retains resource
paths and evidence. This conservative coverage rule is a new condition and
must not be pooled with the previous first-resource behavior.

Generation-method and dataset identities are arbitrary nonempty strings.
Study membership remains a profile/manifest concern. Source item identifiers
and names, applicability, scope coverage, score domains and arithmetic remain
strict. New semantic outputs must validate against both the original input
bytes and the exact agent definition; stale or unspecified definition pins
fail. A byte match verifies the supplied definition identity, while the
registered launcher/check-echo remains responsible for proving what ran.

## Definition pins and preservation

The machine-readable companion, evaluation_general_context_boundary_2026-09-13.json,
records every changed scoring asset and implementation SHA256, the presence
instrument digest and the actual expanded API system-prompt digests.

| Agent definition | SHA256 |
|---|---|
| `d4d-rubric10.md` | `c872457ac69d286f36a4864b27a2bfb17427a4924dfb7301a336413a70e7deae` |
| `d4d-rubric20.md` | `0908520cc229d0b582b443e09f2768c424822fa61c249efaf0067d3faa9fc538` |
| `d4d-rubric10-semantic.md` | `1f15e8c49a5e76c18d52d86b1a53681fbb048f2fe879edfd0a7aa61e0eba1e60` |
| `d4d-rubric20-semantic.md` | `463c7547e5fb91260920cbae8d902c15969173a964c5fcba7fae6d9a89e3877a` |

The earlier completed CBORG condition remains bound to its original schemas,
rubrics, definitions and helper bytes by merged PR #1396. Its read-only audit
still verifies 56 accepted ratings, 450 preservation hashes, one historical v9
canary record and six observed generation requests. No old score, audit or
measurement input is rewritten. Cost qualifications in that audit remain
unchanged.

## Future measurements

A future CBORG evaluation or generation run needs its own concrete registration
and available-provider/model check. Start with a reviewed one-record canary,
prepend the agent preamble and verify check-echo for agentic ratings, then use
the chosen cohort only after acceptance. The earlier user preference for a
24-record v7/v8 cohort and a separate v9 generation canary remains recorded in
the overarching plan; it does not authorize silently repeating the completed
manuscript condition under this new instrument. Name all conditions, preserve
previous outputs, and record dates, actually quoted definition digests and the
exact records evaluated. Repeatability requires the registered repeat ratings.

## Local validation before review

The evaluation/renderer/identity suite passed 557 tests. After final source-name,
report and CLI-preservation changes, 87 focused tests passed, including complete
agent examples, API reply acceptance, stale definition refusal, individual-file
project selection, collection coverage, and repeated external-file CLI exports.
Tests use local fixtures and fake providers. Full CI and independent review
remain required before merge.
