# Review-pack schema freshness — 2026-09-11

Issue #948 is resolved by reading identifier rules from the merged full schema.
A warm view of the modular root could retain imported identifier rules after
those modules changed and the merged schema was regenerated. The regression
uses the real LinkML generator, changes only an imported module, regenerates,
and checks that the next review pack sees the new rule. It fails before the
fix and passes after it. All 56 focused review-pack tests pass.

Adversarial review checked the path anchoring and unknown-root/missing-schema
gaps, then compared the modular and merged schema results over the 24 selected
v7/v8 records. Their 607 identifier leaves keep identical `identifier`, `forced`,
origin and bundle fields. However, 122 leaves across 17 records change only
`required` from false to true: the compiler makes identifier slots required.
The first parity assertion caught this; the companion JSON names every affected
record and path instead of claiming byte-identical pack output.

New packs use version 6 and explain this normalized `required` flag in their
own note. Version 5 and earlier packs retain their recorded interpretation;
no existing pack, review, D4D record, semantic score or rubric definition was
rewritten. Review selection remains report-only under #835. A final review
checked that this boundary is named and that `forced` decisions remain identical.
