# Related-dataset diagnostic policies

`d4d evaluate related-datasets` retains its `legacy_current` default. It reads
today's full-schema vocabulary and emits the same defects, text and exit codes
as the original inspector. `--schema-policy legacy_current` selects that policy
explicitly. The pure `related_datasets.inspect(record)` default is unchanged.

The opt-in `recorded` policy asks a different question: how do the current
captured artifact's relationships classify under its recorded full or core
schema? It reports the `related_dataset_diagnostics_v2` instrument and selected
authority separately for every artifact, including artifacts with no defects.
This is a diagnostic attribution check, not full schema validation, a quality
score, or evidence that the generation or its normalizer actually behaved in a
particular way. It does not modify records, provenance or historical reports.

```sh
# One explicit artifact needs both an explicit provenance and kind.
d4d evaluate related-datasets --schema-policy recorded \
  --provenance /path/to/provenance.yaml --kind full /path/to/record.yaml

# A canonical selection already carries each artifact's provenance and kind.
d4d evaluate related-datasets --schema-policy recorded --runtime api --json
```

`--provenance` and `--kind` accept one explicit artifact. They cannot be applied
to a list or implicitly reassigned to canonical records. `--json` is available
in recorded mode; it reports per-artifact results and selected, checked,
unavailable and defect counts. Recorded-mode exit codes are 0 when every
selected artifact was checked and has no reported defect, 1 for defects, and 2
when any artifact was unavailable. An unavailable artifact is never omitted or
reported as a clean zero.

The checker captures record and provenance bytes once. It validates the output
association's resolved path, any supplied byte length, and every supplied SHA256
and MD5 hash against those same bytes. Relative paths use the provenance's
established artifact root; an absolute flat provenance file cannot establish a
base for a relative output pin. Missing or contradictory associations are
unavailable. Output size alone is not a content hash.
Duplicate mapping keys and YAML merge declarations in either recorded-mode
input are unavailable, so parsing cannot silently discard a contradictory pin.
Other ordinary YAML scalar values, including dates, keep their normal types.

Some older provenance records name an output path and length but have no output
hash. These remain usable as explicitly labeled current-artifact recomputes:
`historical_output: unpinned`. The result includes the actual captured artifact
SHA256 and does not claim that it equals the bytes observed during generation.
`hash_verified` means the captured bytes match every supplied historical output
hash, not independent publisher authentication.

Recorded schema recovery uses `run_schema.run_schema_bytes` separately for full
and core, respecting every supplied SHA256/MD5 declaration for the selected
kind and existing reconstruction/Git recovery. Malformed or empty declarations
are unavailable even when another supplied hash is valid. The checker verifies
all supplied hashes against the returned immutable bytes; it does not borrow
declarations from the other kind. Unavailable historical authority never falls through to today's
schema. The result retains the recovery basis and the actual selected schema
SHA256, byte length, root class, relationship owner, enum and target range.
Rules come from one immutable schema byte snapshot. Local imports outside that
merged snapshot are refused; no mutable SchemaView is retained in the rules
cache.

Vocabulary follows the actual induced `Dataset.related_datasets` or
`CoreDataset.related_datasets` slot and its class's `relationship_type` range.
Enum-name substrings and the other record kind do not select authority. The
same snapshot must declare a scalar string `target_dataset` before the legacy
inline-target diagnostic applies. Missing slots, unsupported range expressions,
multivalued relationship/target fields, inherited or dynamic enums, conflicting
aliases and unreadable schemas are explicitly unavailable. The instrument
handles top-level relationship entries; it does not certify nested records or
all other validation constraints.

The four committed historical full records reproduced in #4301 have 18 values
that today's vocabulary calls aliases but their recorded schema calls unknown.
Their defect counts and exit codes do not change. Their historical core schemas
lack `CoreDataset.related_datasets`, so those core checks are unavailable. This
corrects the stated cause of a defect without measuring an improvement in
generation quality. Parent #4064 remains the broader historical-authority work.
