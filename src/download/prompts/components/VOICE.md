# VOICE — GC-specific prompt components

## fact

The input bundle covers **two distinct cohorts**, not two versions of one:

- **Bridge2AI-Voice adult** — PhysioNet `b2ai-voice`, current release 3.1.0
  (published 2026-05-01, 833 participants). Earlier releases 1.1 and 3.0.0 also
  appear in the bundle.
- **Bridge2AI-Voice pediatric** — PhysioNet `b2ai-voice-pediatric`, release
  1.1.0 (published 2026-05-01, 300 participants aged 2–18, 23,533 derived
  recordings). A separate PhysioNet project under a separate protocol,
  recruited at the Hospital for Sick Children, with raw audio distributed via
  Synapse rather than the adult DACO/PhysioNet route.

These are separate cohorts under separate protocols. Represent what each source
states; do not merge their participant counts, protocols, or access conditions
into single figures.

Note the version numbers invite exactly this error: adult `1.1` and pediatric
`1.1.0` are different datasets, and nothing in the version string distinguishes
them.

Rationale: measured on 2026-07-28, the generic condition — which carries only
the uniform rule "do not merge distinct entities into a single claim" — reached
76.7% three-way agreement against 92.4% when this fact was supplied, the largest
single effect observed in the study.
