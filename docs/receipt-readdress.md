# Repair receipt addresses offline

`d4d receipts readdress` lists receipt entries whose addresses do not resolve in a
selected full record. It identifies entries by chunk ID and zero-based ordinal,
so two entries with the same old slot remain distinct.

```bash
d4d receipts readdress --receipt receipt.yaml --full full.yaml
```

The JSON output includes exact receipt/full SHA256 hashes, unresolved entries and
all structurally resolvable target paths. Paths are possibilities, not suggested
semantic matches. A resolving address does not show that its snippet supports the
value there. No files are written in this mode.

To apply repairs, save a version 1 JSON or YAML map using the displayed hashes:

```yaml
version: 1
receipt_sha256: <exact hash from the inventory>
full_sha256: <exact hash from the inventory>
moves:
  - chunk: c001
    entry: 0
    slot: old_address
    new_slot: names[0]
```

```bash
d4d receipts readdress --receipt receipt.yaml --full full.yaml \
  --map moves.yaml --out repaired-receipt.yaml
```

`--map` and `--out` must appear together. The output must be a new file; existing
files and symlinks are refused. The entire map is checked before writing. Stale
hashes, duplicate identities, an already resolving source slot, an unresolved
destination, extra map keys, snippet changes and drop actions are rejected. Every
field outside the selected slot strings must survive both the actual repair and
serialization unchanged, including types, order, snippets and chunk metadata.
Inputs are checked again before publication. An I/O failure can leave a partial
new output file; the command fails and never silently retries or overwrites it.

Inputs use the existing strict data-only reader: UTF-8 YAML/JSON mappings, unique
string keys, finite values, no cycles or merge keys, at most 8,000,000 bytes each,
64 nesting levels and 200,000 traversed values. Receipts require unique nonempty
chunk IDs, known statuses and string slot/snippet pairs for extracted chunks.
Dates and other supported YAML scalar types are preserved. Complete target-path
text is bounded to 8,000,000 UTF-8 bytes and JSON reports to 32,000,000 bytes;
overlarge inventories fail rather than omit entries.

The source receipt, full record, provenance and transcripts are never written.
A changed receipt hash does **not** inherit an earlier measured receipt origin.
The existing origin checker reports the new bytes as unknown and retains any
previous measurement under `prior` unless an applicable transcript is supplied.
This command does not fabricate a transcript, accept semantic support, alter a
completion gate, change the API's existing readdressing behavior, or authorize a
new command in a registered native session. Adopting the output into a run is a
separate operation under that run's existing rules.
