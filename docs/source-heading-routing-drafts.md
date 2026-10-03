# Offline source-heading routing drafts

`source_heading_routing_request_v1` produces inspectable UTF-8 prompt text with
mapping-derived slot candidates and an instruction to audit placement. It makes
no model call and does not register a generation condition. The separate lexical
`routing_diagnostics` instrument is unchanged.

A matched recipe is a **structural match to an explicitly supplied draft profile**.
It is not publisher authentication, a synonym claim, scientific acceptance, or
proof that a generated value belongs in a slot. Profiles and crosswalks retain
`authority_status: draft/unreviewed`, including the known development example.
Parent #2931 still requires scientific crosswalk review, live registration, an
authorized canary, and the separate overlap report.

## Prepare and independently check

From a checkout with its normal project environment, use the same interface for
neutral fixtures or explicitly selected real sources:

```sh
PYTHONPATH=src python -m data_sheets_schema.source_heading_routing prepare \
  --base base.txt --source source.json --profile profile.json \
  --crosswalk crosswalk.json --scope scope.json \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  --ttl src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl \
  --recommendations notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv \
  --comprehensive src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv \
  --output new-routing-draft
PYTHONPATH=src python -m data_sheets_schema.source_heading_routing check new-routing-draft
```

Optional `--archive original.zip --archive-member exact/member.json` captures
original archive bytes and verifies the JSON source equals its one exact member.
No extraction or source rewrite occurs. Archive and member identities are distinct.
Existing output directories are refused; failures can leave a partial directory
without a final manifest, which the checker refuses. Outputs and captures are
local evidence: review their contents before any publication.

The CLI is a checkout tool using the existing mapping compiler. It does not
pretend to be an installed provider client. Public Python entry points are
`prepare`, `check_files`, `write_new`, `check_directory`, and `append_prompt`.
All failures are refusals, never clean routing judgments.

## Explicit profile and scope

A crosswalk declares neutral display labels and property correspondences:

```json
{"format":"source_heading_crosswalk_v1","authority_status":"draft/unreviewed","rows":[
  {"id":"route-1","heading":"Completeness","profile_id":"example-profile",
   "local_property":"completeness","external_property":"rai:dataCollectionMissingData",
   "external_uri":"http://mlcommons.org/croissant/RAI/dataCollectionMissingData"}
]}
```

The profile has format `source_heading_profile_v1`, an `id`, the same draft
status, explicit local `prefixes`, and `bindings`. Each binding supplies
`row_id`, `evidence_id`, exact `source_sha256`, exact `entity_pointer`, exact
`entity_id` (or null only for an entity without an ID), and separate
`local_value_sha256` and `external_value_sha256` values. Hashes are SHA256 of
original source bytes or each complete decoded string's UTF-8 bytes, respectively.
A caller-supplied new profile is a new declared authority claim, never proof of
who published it.

The source scope is exactly:

```json
{"source_sha256":"<64 lowercase hex characters>","entity_pointers":["/@graph/0"]}
```

Pointers are exact RFC 6901 pointers, not wildcards or a subtree-search request.
Both properties must occur in the same selected object. Complete nonblank
strings are the only supported value shape. Each evidence value retains its
pointer, text, UTF-8 hash and decoded Unicode code-point span `[0, len(value)]`.
These are not raw JSON byte offsets. Unequal local/external values stay unequal;
co-occurrence does not make them semantically equivalent.

No filenames, project guesses, repeated headings, substring similarity, HTML or
Markdown conventions, remote context fetches, or cross-chunk reconstruction can
establish a match. A compact external property requires an explicit captured source-local prefix
that agrees with the draft profile. Profile prefixes never substitute for an
absent, remote-only or unsupported source namespace: those rows are unsupported.
A full URI property key binds directly. Conflicting local declarations are
ambiguous; remote contexts are never fetched.
An unchanged source copied to another filename retains the same byte identity.
Changed source bytes require a new declared binding.

Evidence lists matched, unmatched, ambiguous and unsupported records separately,
plus unbound crosswalk rows and selected entities without bindings. Competing
bindings remain visible and ambiguous. These counts are structural outcomes,
not precision, recall or independent corroboration counts.

## Mapping authority and prompt boundary

The catalog uses the existing comprehensive compiler's resolver and exact
in-memory regeneration under the table's recorded date, the same drift rule as
its `--check`. The captured-input constructor is additive; ordinary compiler
outputs and existing mapping artifacts stay unchanged. Complete local schema
imports and compiler/input bytes are captured, and replay cannot fetch an
uncaptured schema import. Different current implementation bytes are refused;
use the retained matching checkout to recheck historical drafts.

Only resolved curated RAI mappings for the effective Dataset slots qualify.
The catalog reports actual owners, induced range/cardinality, mapping source,
predicate and original slot-to-property direction. Other-owner ambiguity,
unresolved disagreements, NoTermFound, heuristic/recommended rows and non-RAI
mappings are excluded with reasons. Secondary declarations stay provenance,
not a second precedence resolver. All qualifying slots remain candidates for a
property; related/close mappings do not become exact mappings.

The supplement contains the generic audit duty and authority-derived slot and
property names. Source identities, profile names, headings, quotations and
binding evidence remain in separate captured payloads. The duty explains that
release timing alone does not establish sensitive/confidential contents while
preserving mixed content, negation and entity scope. No new lexical classifier
or finding kind is introduced.

The result is labeled `prompt_text_draft`, `offline_draft_not_registered` and
`execution: not_supported`. The base must be strict UTF-8 text. Its original
bytes are preserved and the enabled recipe appends one exact versioned separator
and deterministic supplement ending in one newline; disabled `append_prompt`
returns the base bytes unchanged. The opaque base is **not** checked for required
source context, transport structure or model suitability. No token, cost, model
context-fit or provider-ready claim is made.

The output directory holds `inputs.json`, `catalog.json`, `evidence.json`,
`base.txt`, `supplement.txt`, `prompt.txt`, and `manifest.json`. The manifest
binds all artifacts, recipe and actual added bytes. Checking reconstructs every
artifact from captures instead of trusting supplied outer hashes. Content hashes
protect identity; somebody who changes all inputs and reconstructs a new draft
has made a new declaration, not forged authenticated publisher provenance.

The specificity scanner lists this instruction surface separately as
`offline_draft`; it does not claim that a live generation arm reaches it. Existing
live prompt/digest/renderer behavior and its 42 sent-text surfaces are unchanged.

Source JSON has a 16,000,000-byte/300,000-value/64-level bound; base and individual authority inputs
have an 8,000,000-byte bound, the schema closure 16,000,000 bytes/256 files,
and the complete captured input object 64,000,000 bytes. Profile/crosswalk
rosters are bounded to 512 rows. Limits refuse excess; no source is truncated.
