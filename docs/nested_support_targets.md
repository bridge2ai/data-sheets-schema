# Draft nested support targets

`data_sheets_schema.support_targets` supplies an offline engineering slice of
[#3342](https://github.com/bridge2ai/data-sheets-schema/issues/3342): a captured
schema, target inventory, contextual specifications and pure request rendering.
It does not execute a judge, reuse caches, calibrate a model, or authorize a run.
The existing support-v2 instrument, prompts, caches and behavior are unchanged.

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
induced slot descriptions, class definitions along the path, enums and the
explicit caller vocabulary snapshot. No ambient profile is selected. A slot's
`values_from` names must have entries in that vocabulary or the target is blocked.
Profile-specific registry resolution and manifest selection belong to the later
planner integration.

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
value, full specification and context. The nearest containing mapping is
included in full as untrusted context, with its pointer, class and digest.
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
paths. URI references are never followed. Non-inline class references retain
their relationship assertion as a string-valued edge. Native YAML dates and
timestamps retain typed identities and faithful `value_yaml` rendering, including
time zones; their JSON previews are tagged. Every node is tagged for value and
context hashes, so dates, quoted date strings and ordinary tag-shaped mappings
remain distinct. Input bytes are never rewritten. Duplicate YAML keys,
unsupported scalar types such as binary values, nonfinite numbers and invalid roots are refused. Empty or
null fields do not create targets; empty/null members of a populated list are
reported as blocked.

Traversal defaults to 100,000 nodes and depth 64, at most 4 MB input and 64 MB
total rendered target data. Limits are explicit and pinned in the artifact
identity. Exceeding a limit raises instead of returning a truncated inventory.
Including complete nearest mappings is conservative and can be expensive;
future context reduction changes the instrument and must be reviewed before
calibration. The renderer is pure: no client initialization, token-count API,
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

## Remaining work before #3342 completion or paid calibration

- Independently review this resolver, context and question contract, including
  the choice of edge versus attribute strata and their reporting denominators.
- Integrate the reviewed contract into a new offline plan version after #3341;
  regenerate nested target counts, blocked-path coverage, requests and costs.
  Old top-level manifests and historical caches remain intact.
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
- Version and review execution, output validation, usage/reasoning ledgers and
  any cache loader. There is currently no v3 provider execution route.
- Complete independent empirical calibration (#3343) and obtain the required
  paid-run authorization before a canary or the 24-record cohort.

Offline tests establish binding and rendering behavior, not model recall or
false-positive rates. This slice does not close #3342, #3343, #2929, or the
preserved generation-acceptance findings.
