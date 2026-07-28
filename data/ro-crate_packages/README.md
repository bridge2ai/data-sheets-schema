# RO-Crate Packages (per Grand Challenge)

Upstream-published RO-Crate packages for each Bridge2AI Grand Challenge,
downloaded as an **additional** D4D generation input. These support paired
generation runs — with and without crate data — so the crate's contribution can
be measured rather than assumed.

Not to be confused with:

- `data/ro-crate/` — D4D RO-Crate **profiles, specs, and examples** (authored here)
- `data/ro-crate_mapping/` — D4D ↔ RO-Crate **field mapping tables**

This directory holds **upstream data**, not artifacts we author.

## Layout

```
data/ro-crate_packages/
  crate_manifest.yaml          # source DOIs, file ids, sizes, verified md5s
  {PROJECT}/
    raw/                       # bytes exactly as downloaded — never edited
    crate/                     # extracted archive; gitignored, re-creatable
    processed/                 # normalized artifacts (d4d rocrate normalize)
```

`raw/` is the provenance anchor: every file's md5 is recorded in
`crate_manifest.yaml` and was verified against the upstream Dataverse-reported
checksum at capture time. Re-verify with:

```bash
md5 -r data/ro-crate_packages/*/raw/*
```

`crate/` is gitignored — CM4AI's extracted tree is ~47 MB, almost all of it
per-file listing HTML. Re-extract with:

```bash
cd data/ro-crate_packages/CM4AI && unzip -q -o raw/cm4ai_release_metadata.zip \
  && mv cm4ai_release_metadata crate
```

## Status

| Project | Source | Crate | Usable as-is? |
|---------|--------|-------|---------------|
| CHORUS | Dataverse `doi:10.18130/V3/XNBOPG` | standalone file set | Nearly — one key to drop |
| CM4AI | Dataverse `doi:10.18130/V3/HIGT4C` | inside `cm4ai_release_metadata.zip` | No — four repairs needed |
| AI_READI | *link pending* | — | — |
| VOICE | *link pending* | — | — |

## What each crate ships

Both crates follow the same four-artifact shape:

- **`ro-crate-metadata.json`** — RO-Crate JSON-LD with EVI typing and Croissant
  `rai:` (Responsible AI) fields. Carries the richest D4D-relevant content:
  limitations, biases, collection mechanisms, ethical review, IRB, access
  conditions, maintenance plan, intended uses, sensitive-information handling.
- **`ro-crate-linkml.yaml`** — a **D4D-shaped LinkML rendering** that declares
  `conforms_to: D4D Schema` and uses our slot names (`collection_mechanisms`,
  `known_biases`, `known_limitations`, `sensitive_elements`, `ethical_reviews`,
  `intended_uses`, …). The most directly usable artifact.
- **`ro-crate-datasheet.html`** — human-readable datasheet rendering.
- **`ai_ready_score.json`** — AI-readiness self-assessment across fairness,
  provenance, characterization, pre-model explainability, ethics,
  sustainability, and computability.

## Preprocessing determination

See **`notes/ROCRATE_INGESTION_STUDY.md`** for the full analysis: what validates,
what does not, the four CM4AI repairs, the size-reduction requirement, and the
upstream data-quality bugs found.
