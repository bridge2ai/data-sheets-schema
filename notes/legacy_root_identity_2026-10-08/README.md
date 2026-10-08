# Explicit legacy root identity (#4672)

The default legacy TSV now includes a required `Dataset.id` construction route,
selected by `Func=root_identifier_v1` on one covered `id` row with source
`identifier,@id`. Both legacy implementations use the already selected crate
root. A nonblank scalar `identifier` wins; absent, null or blank text falls back
to root `@id`. Present lists, objects, numbers and booleans refuse before changing
the prior builder or merger result. No identity is invented or borrowed from a
member dataset.

Recognized whole scalar DOIs are written as `doi:` CURIEs. The complete body,
including case and every trailing slash, survives. Other text and ARKs retain
their exact spelling; the ID route does not trim surrounding whitespace. The
separate `Dataset.doi` implementation is unchanged from the reviewed predecessor
`1a98255bb28451500d4864876a16d9c6c2f6b435`, including its suffix-preservation fix
for #4671.

The marker is an explicit selector, never executable TSV code. Unmarked custom
ID and no-ID tables keep their prior construction, reverse lookup and scoring
behavior. Misplaced, uncovered, duplicate or incompatible marked declarations
refuse at table loading, including rows otherwise skipped as headers. The
ordinary `identifier -> doi` reverse mapping wins in either row order.

Merged ID comes only from the configured primary source. Every marked input's
identity is checked before merge state changes; a secondary identity cannot fill
a missing primary identity. The existing merge report records the selected
primary, source properties, original input assertions and differing written IDs.
Those differences do not assert that sources describe the same entity. Required
identity construction is excluded from the scorer's coverage and uniqueness
denominators and from API and CLI source-coverage statistics. Existing ranking,
ties and automatic primary selection therefore retain their prior basis.
Review issue #4674 extended that exclusion to the API result metadata and both
CLI report/stdout consumers; their construction inventories remain separate.

All original default TSV rows are retained. The new row leaves its semantic
mapping, SKOS and information-loss claims unassessed. Successful construction or
literal preservation does not establish `exactMatch`, `none`, scientific source
coverage, or a valid complete Dataset. Missing required identity and remaining
Class/nested-creator/type errors still reach the mandatory publication gate;
legacy API metadata still requires the explicit `dataset_v1` result contract for
Dataset-only publication. Neither another mapper nor a generated identifier is
substituted on failure.

## Validation status

Implementation and focused tests are prepared for independent static review.
No tests, five-input replay, provider calls or real-record publication have been
run for this change yet. Tests exercise both real loaders, constructors, scorers
and mergers; complete DOI suffixes, graph reordering, fallback and refusal;
custom-table compatibility; merge preflight and primary-only identity; mandatory
publication and existing output preservation. Independent controls exercise a
real ranking reversal when an unmarked construction row is incorrectly counted,
and source-coverage reporting across result contracts.

The separately scheduled five-input comparison must retain the CHORUS, VOICE,
CM4AI reduced, CM4AI original archive member, and VOICE provenance evidence. It
must compare against the DOI-fixed predecessor and record all remaining
validation errors, with source preservation and unchanged ranking. Existing
historical records and the 43-row accepted-policy snapshot remain unchanged.

Parent issues #4594 and #2915 remain open for the broader construction,
validation, comparison and publication obligations. This repair does not resolve
human scientific review, applicability, routing or paid-execution holds.
