# VOICE_PEDIATRIC — GC-specific prompt components

## fact

The input bundle is scoped to the **pediatric** cohort, but it also carries
programme-level documents that state **adult** figures, and at the point where
they appear the cohort is not named.

- **This dataset** — Bridge2AI-Voice Pediatric, PhysioNet `b2ai-voice-pediatric`
  release 1.1.0, DOI `10.13026/h995-bt35`. Derived audio features for **23,533
  recordings collected from 300 participants aged 2–18**, recruited at the
  Hospital for Sick Children. Raw audio is distributed via Synapse rather than
  the PhysioNet route.
- **Also present in the bundle** — the Bridge2AI-Voice adult dataset,
  PhysioNet `b2ai-voice`, release 3.1.0. The programme documents state "there
  are currently around **833** instances", which is the adult count.

Attribute each figure to the cohort its source states it for. The adult figures
are in the bundle because the programme documents that cover this release also
cover the adult one, not because they describe this dataset.

Note the version numbers invite the error in both directions: adult `3.1.0` and
pediatric `1.1.0` are different datasets, and a release string alone does not
distinguish them.

Rationale: this is the mirror of the fact supplied to the adult project, which
moved three-way agreement from 76.7% to 92.4% — the largest single effect
measured in the study. Where the adult bundle risks absorbing pediatric figures,
this one risks absorbing adult figures, and `833` against this dataset's 300 is
the specific value at risk.

The referent itself is **not** restated here. It is declared in the `scope:`
block of `data/preprocessed/source_manifest.yaml`, where `d4d download scope
--check` can verify it and where the next dataset inherits the mechanism (#422).
A component that repeated it would be a second copy that could drift from the
checkable one.
