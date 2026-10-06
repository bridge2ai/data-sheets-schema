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

Repeated historical records reuse only the pure Dataset inventory. This private
cache retains at most 32 entries and 16 MiB of accounted key/inventory object
graphs, evicts the least recently used entry, and bypasses oversized entries.
Its keys include the recovered bytes, logical path, renderer/runtime identity,
and effective construction functions, defaults and settings. Each consumer gets
a detached inventory; no SchemaView, record, comparison result or failure is
retained. Schemas declaring imports bypass retention because their root hash
does not cover installed LinkML import bytes. Every record still recovers and
verifies its schema, captures and validates current vocabularies, renders both
profile candidates, and makes a fresh comparison.

The comparison does not alter records, the digest inventory, generation
instructions, validation schemas or scoring. Pair comparison still compares a
recorded digest with the current digest to report instrument drift. Historical
slot-membership recovery remains independent of profile identification.

## Reconstructing historical digest text

For a historical profile comparison that remains unknown, the checker also
attempts a separate `historical_digest_text` reconstruction. It reuses the exact
full-schema bytes already recovered and verified against every recorded hash.
This diagnostic leaves the profile comparison and its strict behavior intact.

The supported input is an import-free `Dataset` schema with recorded and
installed `linkml-runtime` version 1.9.4. The selector reads the fixed renderer
path at the record's exact full Git commit, verifies the blob bytes, and selects
one of nine reviewed source identities. It never imports or executes historical
Python. Six compatibility policies reproduce those source versions' text:

| Family | Historical behavior |
| --- | --- |
| `required_enum40` | Top-level enum limit 40; one nested level showing required keys. |
| `nested_enum60` | Enum limit 60 and nested enum values. |
| `optional_keys` | Nested optional keys, including the original small-class overlap shortcut. |
| `ranges_vocabulary` | Nested range details and explicit registry vocabulary terms. |
| `canonical_paths` | Canonical source spelling for the known merged-schema basename. |
| `inline_depth2` | Two nested levels, reference labels, and overlap shorthand only above 24 optional keys. |

Every family displays top-level ranges. The last family's initial traversal
includes all top-level ranges; only traversal to the second nested level filters
for non-universal inlined edges. Enum and vocabulary insertion order, description
truncation, optional-key limits, and literal wording remain part of the digest.
The complete source SHA256 mapping lives in `historical_digest.SOURCE_FAMILIES`.

Families that used registry terms require the verified vocabulary blob at the
same recorded commit and its reviewed SHA256. Earlier families explicitly used
no vocabulary. Missing commits, unknown renderer blobs, unavailable vocabulary,
unsupported runtime versions and imported schemas produce an `unavailable`
result. The selector does not fetch missing objects, substitute current inputs,
or try every family until a digest matches. An audit may supply an explicit
read-only Git object repository through `reconstruct(..., git_root=...)`.

`reproduced` means the selected candidate's text has the originally recorded
MD5; the result also reports text SHA256, schema SHA256, source commit/blob/hash,
family, vocabulary identity and runtime. `not_reproduced` means those supported
candidate inputs produce a different digest. Neither result proves which dirty
working-tree implementation the original run consumed. The result keeps
`consumed_implementation_identity` unrecorded and reports any historical profile
as unrecorded or declared but unverified. An absent digest remains absent.

The selector considers exactly one recorded-commit candidate. It makes no claim
that the consumed implementation or historical profile is uniquely identified,
and no claim of scientific comparability follows from text agreement. Original
provenance and outputs remain unchanged.

Git reads use a fresh child environment with replacement refs, lazy fetching,
network protocols and ambient Git repository overrides disabled. Each command
has a five-second limit, identity output is limited to 64 bytes, and candidate
blob output to 1 MiB. Oversized or unavailable objects remain unavailable.

Repeated historical reconstruction also reuses successful immutable digest text
in a separate 32-entry, 16-MiB cache. The byte budget includes retained keys and
text; oversized entries bypass retention and least recently used entries are
evicted. Keys include the exact schema and vocabulary bytes, logical path,
family policy, runtime, and effective rendering/parsing/view dependencies.
Supported helper closure contents are snapshotted; opaque callable instances,
ambiguous closure state and cycles bypass retention.
Unsupported dependency state and rendering failures use the original renderer
without retention. No parsed document, SchemaView, record or conclusion is
stored. Every reconstruction still verifies schema authority and reads and
verifies the exact renderer/vocabulary Git blobs before using this pure work,
then constructs fresh candidate metadata and compares the recorded digest.
