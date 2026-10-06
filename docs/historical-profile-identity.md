# Historical profile identity

`d4d runs check` compares a record's declared profile with its recorded digest.
When the record supplies a full-schema path and hash, the comparison uses only
schema bytes matching every supplied hash. Disk, recorded reconstruction and
Git recovery keep their existing precedence. Partial or malformed authority,
unavailable bytes, invalid schemas and uncovered local imports leave identity
unknown.

The checker renders profile candidates with the current digest renderer and
explicitly captured current vocabulary files. A candidate must reproduce the
recorded digest to establish a match. The stated profile takes precedence when
several profiles produce the same text. An exact match to another profile is a
conflict and remains fatal under `--strict`. If no candidate matches, historical
identity is unknown: recovering a schema does not recover an old renderer or
vocabulary. Unknown identity is reported separately and is not fatal.

A captured vocabulary file must contain a `vocabularies` mapping whose named
tables map string identifiers to string labels. Empty mappings are valid;
missing mappings, lists, booleans, numbers and nulls are unavailable evidence.

`profile_identity.capture(record)` returns the comparison status, reason,
schema-resolution basis, renderer identity, vocabulary hashes and candidate
digests. `provenance.profile_assessment(record)` returns findings and that
context from one capture. Existing `profile_problems` and record validation
continue to report structural and stored-spec conflicts. Records that declare
no full-schema authority retain the existing comparison with current digests,
including the missing-vocabulary finding.

The comparison does not alter records, the digest inventory, generation
instructions, validation schemas or scoring. Pair comparison still compares a
recorded digest with the current digest to report instrument drift. Historical
slot-membership recovery remains independent of profile identification.
