# Form subtype instrument boundary — 2026-09-11

Issue #1263 exposed an online cache miss that judged a current schema
specification while recording a historical schema digest. The classifier now
keeps its selected instrument frozen: cached labels remain replayable, but a
new call requires the generation digest and complete specification SHA256 to
match one captured inventory/vocabulary snapshot. Otherwise it refuses before
creating a client and directs new measurements to a fresh cache. The CLI names
the complete specification, or identifies a historical unattested replay.

New subtype labels use the same complete-specification calculation as fitness.
Review found #1268: the supplied fitness explanation was in the prompt but
missing from its cache key. New entries also record its SHA256 and distinguish
different explanations for the same value. Historical entries retain their
original keys and their original interpretation. Multiple complete specifications
require an explicit selection; a cache is not silently pooled.

Seven initial offline regressions failed before the fix. Review then checked
source/vocabulary drift, capture-to-prompt changes, historical fills, reason
changes, ambiguous cache selection and replay without a readable live schema.
All 117 targeted subtype, fitness and imported-schema tests pass. The helper
extraction does not change the existing fitness specification hash.

The audit at 2026-09-11T23:44:56Z replayed all 106 historical subtype labels
without initializing a client or making a call. Their published folded totals
remain collapsed cardinality 42→7 and hollow objects 8→50. The four fitness
cache files and subtype cache match main byte for byte; the companion JSON
pins them and records the exact reproduced table. No historical label, fitness
judgement, D4D record, semantic score or semantic agent definition was rewritten.
