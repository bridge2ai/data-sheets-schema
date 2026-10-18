# Authoritative FAIRSCAPE root selection — 2026-10-07

The FAIRSCAPE-to-D4D converter now uses the static mapper's shared root selector. Ambiguous roots and broken explicit references produce a diagnostic before the converter writes a record. Reordering an ambiguous graph cannot select a different child Dataset. This addresses [#4586](https://github.com/bridge2ai/data-sheets-schema/issues/4586), with adversarial findings [#4587](https://github.com/bridge2ai/data-sheets-schema/issues/4587) and [#4589](https://github.com/bridge2ai/data-sheets-schema/issues/4589).

The shared selector recognizes crate-level `ro-crate-metadata.json`, legacy `ro-crate-metadata.jsonld`, and their explicit `./` aliases. Recognized descriptors must name one uniquely identified Dataset or ROCrate. Missing, empty, invalid, conflicting and unresolved references, duplicate descriptor/target identities and descriptor self-reference are refused. A nested member's metadata filename cannot override the crate descriptor merely because its basename matches.

The [RO-Crate structure specification](https://www.researchobject.org/ro-crate/specification/1.1/structure.html#ro-crate-metadata-file-ro-crate-metadatajson) places the metadata file at the crate root and documents the legacy `.jsonld` filename. This compacted-graph reader does not infer a document base from an arbitrary absolute metadata-looking IRI.

For descriptor-free legacy graphs, the implementation permits a unique typed conventional `./` or `.` root, otherwise a unique ROCrate, otherwise a unique Dataset. An invalid or ambiguous higher-priority candidate cannot be skipped in favor of a child. A unique anonymous node can still provide a separate DOI identifier; a present malformed `@id` is refused. Unrelated malformed member IDs cannot crash extraction after a valid root is selected.

## Validation and compatibility

The affected integration suites passed **779 tests**, with **six skips** recorded individually in [validation.json](validation.json). They cover root graph ordering, descriptor precedence and disagreement, malformed identities, anonymous-root compatibility, static mapping and reports, CLI output preservation, deterministic publication and figure consumers. Both direct converter CLIs refuse ambiguous input without creating a new destination or altering an existing one; `--no-validate` does not bypass root selection.

Baseline and candidate replays used the exact same eight inputs:

- Four bundled FAIRSCAPE/profile/round-trip examples.
- Original CHORUS and VOICE crate metadata.
- Original CM4AI metadata read directly from its committed ZIP member.
- CM4AI's processed reduced metadata as a separate compatibility fixture.

All eight converted records passed actual LinkML validation. Their serialized YAML bytes, record values and dropped-value diagnostics are unchanged from baseline `fb057076923d8616030bf239cc5505395eedb384`. The three working projects were also replayed through the static mapper: all three records validate and their contents are unchanged. Input/archive/member, record and producing-source hashes, plus successful command receipts, are retained in [validation.json](validation.json).

Reversing each graph preserves selected root identity and root-derived record contents. The FAIRSCAPE converter continues to emit file collections in graph order, so replay compares those collections as multisets, retaining multiplicity and complete member contents. The three static records are exactly unchanged under graph reversal.

This is a compatibility fix and refusal-policy change. Historical deterministic labels, working output files and fig09 artifacts are retained without rewriting; no new coverage score or semantic fidelity claim follows from the unchanged replay. The v8 comparison remains retrospective, and human scientific review under #2912 and #2921 remains pending.

## Reproduction and remaining scope

From an isolated checkout with the repository's Python dependencies installed, use an unused output directory:

```bash
python -B notes/fairscape_root_policy_2026-10-07/replay.py \
  --repo . --output /private/tmp/fairscape-root-replay-new
```

The script reads the original CM4AI ZIP member in memory, validates all outputs, tests graph reversal and writes records, diagnostics and hashes only to the new review directory. It was executed successfully against the candidate and produced the same evidence as the initial replay.

The separate parser copies and builder-based parse/transform/merge/rank entry points remain explicitly tracked by [#4588](https://github.com/bridge2ai/data-sheets-schema/issues/4588). Property routing (#4046), relationship typing (#4047), and held figure-set integration (#4385) remain separate. Parent [#2915](https://github.com/bridge2ai/data-sheets-schema/issues/2915) stays open; protected fixer and figure worktrees were not modified.
