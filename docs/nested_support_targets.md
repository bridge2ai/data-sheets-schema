# Draft nested support targets

`data_sheets_schema.support_targets` supplies an offline engineering slice of
[#3342](https://github.com/bridge2ai/data-sheets-schema/issues/3342): a captured
schema, target inventory, contextual specifications and pure request rendering.
It does not execute a judge, reuse caches, calibrate a model, or authorize a run.
The existing support-v2 instrument, prompts, caches and behavior are unchanged.

An additional explicit policy addresses original strings where the selected
schema requires an inline class mapping ([#4902](https://github.com/bridge2ai/data-sheets-schema/issues/4902)).
The default remains strict. For an offline version-2 plan, select
`--relationship-policy inline-class-strings`; the Python inventory/planner
argument is `relationship_policy=support_targets.SCALAR_POLICY`.
This is a distinct draft instrument and prompt, using policy
`relationship_edge_and_attribute_value_inline_class_strings_v1`. It applies to
class-valued inline slots generally, rather than depending on a class named
`Person`. The observed 24-record coverage gap was Person-specific; that observation
does not establish scientific validity for other class ranges.

The opt-in policy retains a nonempty original string as one `relationship_edge`,
with its exact pointer, value, nearest containing entity and current induced
schema specification. It neither splits the string into people nor invents
identifiers, mappings or child attributes. The target's `representation` records
`schema_invalid_inline_class_string`; inventory and plan `representation_issues`
retain each affected pointer and range. This is a known shape mismatch, not a
successful schema validation, and a support verdict cannot repair it. Existing
seven-verdict precedence is unchanged. Unknown slots, malformed cardinality,
missing vocabularies and unsupported owner/slot constraints remain blocked;
the new scalar case also refuses inherited constraints on its range class.
Boolean/numeric/container values are not coerced into references. Proper inline
mappings keep their existing traversal.

Policy, instrument and request bytes are checked again during saved-result and
registered-execution reconstruction. Record/target IDs remain plan-local: equal
IDs do not permit evidence to cross plans or policies. Historical strict plans
retain their original interpretation and request identities. New-policy reports
separate selected-target representation issues, all issues verified in the
chosen records, and full-plan **declared** counts; unselected record evidence is
not reconstructed. These issues are a subset of relationship edges, not an
additional pooled denominator. Attribute values and top-level fitness remain
separate, and no verdict propagates to children or another facet.
Calibration reports retain their all-edge groups and additionally expose
`representation_counts` and `representation_groups` for the selected relationship
controls. These distinguish inline-string mismatches from other edges; "other"
does not mean schema-valid. The subsets contain the same observations, and their
metrics retain the existing pending-control and scientific-eligibility limits.

Instrument/context review, independently adjudicated controls, calibration,
private-source handling and paid-run authorization remain separate requirements.
Producing an additional question is not a semantic label or a scientific result.

```python
from pathlib import Path
from data_sheets_schema.support_targets import (
    NestedSupportSchema, inventory_targets, render_request, request_identity,
)

schema = NestedSupportSchema.from_schema(
    Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml"),
    root_class="Dataset",
    vocabulary={},  # Explicit captured registry values when the schema requires them.
)
inventory = inventory_targets(
    Path("record.yaml").read_bytes(), schema, artifact_kind="full",
)
target = inventory.target("/creators/0", kind="relationship_edge")
arguments = render_request(target, bundle="Document A\nSource text.", model="explicit-model")
identity = request_identity(target, bundle="Document A\nSource text.", model="explicit-model")
```

The schema must be explicitly selected. Local transitive imports are captured
once; uncaptured remote imports are refused. Specifications include complete
induced slot descriptions, class and ancestor meanings along the path, relevant
enums and the explicit caller vocabulary snapshot. Full unrelated class attribute
inventories are not sent. Inventory specifications are deduplicated in a shared
catalog; each target pins its specification reference. A single target expands
that specification for request rendering. No ambient profile is selected. A slot's
`values_from` names must have entries in that vocabulary or the target is blocked.
The [version-2 planner](offline_support_plan.md#nested-version-2) captures an
explicit profile vocabulary or caller-supplied vocabulary override together
with the selected manifest. This pure inventory API does not select them.

Each populated inline object or list member has a `relationship_edge` target,
such as `/creators/1` or `/data_governance/committee_contact`. Its question is
whether this entity occupies that relationship, independent of the truth of all
its attributes. Scalar fields and scalar-list members have `attribute_value`
targets, such as `/creators/1/name`, `/variables/0/variable_name`, and `/flags/0`.
This distinguishes an accurate name from an unsupported creator relationship.
The target keeps the slot chain so a generic nested name does not lose the
container's meaning. The two kinds have separate counts; there is no combined
support percentage or arbitrary conversion of typed verdicts to points.

Every target binds exact input bytes, artifact kind, root class/field inventory,
value, selected specification and context. The nearest containing mapping's
complete scalar siblings, scalar-list siblings and explicit qualifier fields
(`description`, `notes`, `source_caveats` and declaration fields) are included as
untrusted context, with its pointer, class, full-source digest and projected-value
digest. The selected slot is supplied separately as the target; unrelated
container siblings are omitted with their pointer, content hash and size recorded.
No retained description or qualifier is truncated. Anonymous mappings retain
this projected context and their path even without an identifier. The context
projection is versioned and remains an explicit readiness blocker pending review;
an application requiring an omitted container must expand/review the context
policy before execution, not treat an omission as evidence of absence.
Ancestor mappings supply identity and path, without automatically inheriting
collection metadata. A resource's creator is asserted of that resource, not the
outer collection. Anonymous entities retain their mapping and pointer. Context
declarations come from the selected value and direct containing mapping;
unrelated siblings' declarations and ancestor declarations are not inherited.
Publication `status` and `was_derived_from` remain value/context fields rather
than citation declarations. Natural-language attribution inside a value remains
visible to the model.

Pointers address the exact original document: wrappers are not stripped. RFC
6901 escaping is strict; array append, negative/leading-zero indices and missing
paths are refused. Zero and false are populated. Unknown schema fields, invalid
container/cardinality shapes, keyed inline maps, unions/conditional constraints,
type-discriminator transitions, and missing vocabularies are reported as blocked
paths. Unsupported class constraints are refused across the complete `is_a` and
mixin ancestry, including shared ancestors (#4232). URI references are never followed. Non-inline class references retain
their relationship assertion as a string-valued edge. Native YAML dates and
timestamps retain typed identities and faithful `value_yaml` rendering, including
time zones; their JSON previews are tagged. Every node is tagged for value and
context hashes, so dates, quoted date strings and ordinary tag-shaped mappings
remain distinct. The request sends the faithful YAML representation once, without
also repeating the JSON preview of the same text. Input bytes are never rewritten. Duplicate YAML keys,
unsupported scalar types such as binary values, nonfinite numbers and invalid roots are refused. Empty or
null fields do not create targets; empty/null members of a populated list are
reported as blocked.

Traversal defaults to 100,000 nodes and depth 64, at most 4 MB input and 64 MB
total compact target data plus shared specification catalog. Limits are explicit and pinned in the artifact
identity. Exceeding a limit raises instead of returning a truncated inventory.
Future context-policy changes alter the instrument and must be reviewed before
calibration. The public AI_READI v7 rep1 regression exercises the default limits
on its original 89 KB record, including a bounded per-creator request rather than
a copy of unrelated sibling collections. The renderer is pure: no client initialization, token-count API,
retry, network request or output-file write occurs.

The draft `grounding_v3` axis and `support_targets v3 draft (#3342)` identity are
distinct from v2. Request identity hashes all rendered arguments, including
model, output limit, prompt, exact target/context and bundle text. This is an
identity receipt, not a cache loader. Different artifact bytes, full/core kinds,
entity contexts, pointer positions or specifications cannot silently share an
old verdict. Returned dictionaries are private copies of immutable captured JSON.

Fitness remains explicitly top-level. Each nested target records a many-to-one
mapping to its original top-level field, without inventing a per-target fitness
verdict. For example `/resources/0/creators/1` maps to the old `/resources` field.
An independently versioned nested fitness instrument can replace that basis in
a later, reviewed integration.

## Engineering review — 2026-10-10

The nested engineering requested by #3342 is already available through the
deliberately separate v3 instrument introduced by
[PR #4252](https://github.com/bridge2ai/data-sheets-schema/pull/4252).
Extending `SupportJudgeV2` or adding another traversal would duplicate that path
and risk changing historical requests. This review found the following existing
coverage:

| Requirement | Implementation and regression coverage |
| --- | --- |
| Nested schema meaning and entity context | `support_targets` resolves exact pointers, induced nested slot specifications and the nearest containing entity. [Public defect-path controls](../tests/test_evaluation/test_nested_support_defect_context.py) exercise the shapes discussed in #1782/#1801/#1815 against the public full schema, including the maintainer-role enum, caveats and identical claims in different entities. The records are neutral examples, not adjudicated defect labels. |
| Usable offline planning with explicit identity | [Planner v2](offline_support_plan.md#nested-version-2) selects artifact kind, root class, schema and profile, records blocked paths, and captures target/context/specification/request identities. [Planner tests](../tests/test_evaluation/test_nested_support_plan.py) cover CLI opt-in, request reconstruction and unchanged default/explicit-v1 outputs. |
| Separate measurement denominators | Relationship edges and attribute values have separate support counts; top-level fitness remains a separate stratum. An edge asks about the relationship rather than grading its descendants again. Fitness mappings are many-to-one, and total requests are accounting totals. [Saved-result tests](../tests/test_evaluation/test_nested_support_results.py) distinguish selected-subset completion from all planned nested targets and reject altered count or target claims. |
| Saved judgment and actual request binding | The [saved-response reader](nested-support-results.md) reconstructs selected targets from captured inputs. The [registered executor](nested-support-execution.md) binds planned and effective request bytes, model, output limit, target and attempt. Its [local HTTP regression](../tests/test_evaluation/test_nested_support_execution.py) compares the actual received POST bytes with the captured effective request and checks offline readback. This is transport capability, not evidence of a provider scoring run. |

These controls establish software behavior only. Context projection and question
design still need independent instrument review; a supported path does not show
that a model detects its defect. Real-roster blocked paths, curator-adjudicated
controls and their provenance, #3343 empirical calibration, and per-run
registration and authorization remain separate obligations. This review grants
no approval, records no semantic scoring, and does not close #3342 or #2929.
Historical v2 prompts, defaults and saved artifacts remain unchanged.

## Remaining work before #3342 completion or paid calibration

- Independently review this resolver, context and question contract, including
  the choice of edge versus attribute strata and their reporting denominators.
- Review the opt-in offline planner version 2 in [offline_support_plan.md](offline_support_plan.md),
  including nested target counts, blocked-path coverage, requests and costs for
  the selected roster. Old top-level manifests and historical caches remain intact.
- Decide and test missing registry/profile coverage, unsupported schema shapes,
  and collection inheritance policies before calling the inventory complete for
  a real roster. The current report always carries unresolved readiness blockers.
- Freeze curator-adjudicated positive and supported controls, with exact local
  original/bundle hashes. Public tests here use neutral synthetic records and
  the public D4D schema; private rejected outputs are not distributed as fixtures.
- Separate record-support, artifact-local references and audit-classification
  controls. Supplying full/core context does not establish that this draft prompt
  detects self-reference defects. A multi-clause string still yields one verdict
  under declared precedence, not independent coverage of every clause.
- Select and review the exact registration before using the implemented
  [registered executor](nested-support-execution.md). The separate
  [saved-response reader](nested-support-results.md) validates captured replies;
  neither route reuses historical judgement caches or clears scientific holds.
  The [calibration evidence workflow](../notes/support_calibration_2026-10-07/README.md)
  binds explicit control labels to a registration and reports captured outcomes
  offline. It does not adjudicate labels or perform empirical calibration itself.
- Complete independent empirical calibration (#3343) and obtain the required
  paid-run authorization before a canary or the 24-record cohort.

Offline tests establish binding and rendering behavior, not model recall or
false-positive rates. This slice does not close #3342, #3343, #2929, or the
preserved generation-acceptance findings.
