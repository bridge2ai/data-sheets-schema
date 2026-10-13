# Parser and builder root enforcement (#4588)

The packaged and source-script parsers now use the shared authoritative
RO-Crate root selector. A metadata descriptor's `about` reference takes
precedence over a conventional `./` member, regardless of graph order.
Conflicting or unresolved descriptors, duplicate root identities and ambiguous
fallbacks leave the root unset with a diagnostic; they do not select a child.

Inspection remains available for empty and ambiguous graphs. Dataset building,
scoring, ranking and merging require a selected root before processing any
source. Batch operations preflight every input, including comparison sources
used to calculate uniqueness. Concatenation also preflights the combined graph
before writing its intermediate artifact. The legacy parser is a compatibility
wrapper around the installed implementation and retains its default progress
messages and direct-script entry point.

Related review fixes: #4591 prevents partial legacy batches and false CLI
success; #4592 supplies the real parser's entity inspection method. The
ID-keyed entity export refuses duplicate IDs rather than overwriting them.
Anonymous or malformed entries remain in the raw `graph` inspection view.

## Replay and interpretation

Run the same portable replay against baseline and candidate checkouts, each
with a fresh external output directory:

```sh
python -B notes/parser_root_policy_2026-10-07/replay.py \
  --repo . --output /private/tmp/parser-root-review-candidate
```

The replay uses the actual legacy semantic mapping TSV and LinkML validator.
It examines CHORUS, VOICE, CM4AI reduced, the original CM4AI ZIP member, and
the one-node VOICE provenance graph through both parser/builder entry points,
then reverses each array graph. The ZIP member is read in memory; review
inputs and records are written only to the new external directory. Source,
mapping, schema and output hashes bind the results.

Baseline commit: `e9884669561d54bfe4a56c7dcd06813787cc4187` (identical tree
to the retained isolated checkout at `e57acbbe1841cae6e7cbebc25a6cb587475a4442`).
Baseline legacy records fail actual schema validation: 33 errors for CHORUS,
153 for VOICE, 78 for each CM4AI input, and one for the packaged one-node
VOICE output. The old hidden parser crashes on that one-node graph before
building a record. The full errors are retained with the replay artifacts;
these are not validated publication records.

Schema construction and validation-before-publication are explicitly tracked
in #4594. The unrelated raw `d4d rocrate merge` API drift is tracked in #4593.
Neither is represented as fixed by this root-policy change. #2915 remains open.

No source bundle, historical output, deterministic label or figure is replaced
by this replay. This is a correctness and compatibility check, not evidence of
improved source coverage or scientific fidelity. Row retirement does not count
as coverage gain; intact source text alone does not establish `exactMatch` or
loss=`none`. The fig09 v8-replicate-1 comparison remains retrospective, and
human scientific reviews #2912 and #2921 remain pending.

## Verification result

- Independent adversarial source review found no blocking defect in the
  scoped root-policy changes.
- Integration suite: **974 passed, 6 skipped**. One skip requires optional
  linkml-map; five require optional FAIRSCAPE models. These are not counted
  as passing validation. Source hashes were unchanged throughout the run.
- Both consumer implementations now build all five replay inputs, with exact
  root/record equality after graph reversal. All nine previously built
  original records are byte-identical to baseline, including their existing
  validation errors. The newly supported hidden one-node VOICE path emits
  the same record as the packaged path (one existing missing-ID error).
- The maintained converter/static replay separately produced **eight valid
  converter records and three valid static records**, unchanged from the
  preceding #4586 replay. No legacy builder output was published as a valid
  record.
- Compact hashes, per-input results and test command are in
  [validation.json](validation.json). Full local logs and replay artifacts
  remain in `/private/tmp/d4d-4588-parser-roots-gxffLABS/`.

The audit also identified #4595: profile evaluation still uses a first-Dataset
selector. That follow-up must enforce the shared root policy before reporting
profile coverage. It remains outside this parser/builder change.
