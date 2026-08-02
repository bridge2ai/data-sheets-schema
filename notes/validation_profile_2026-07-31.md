# Validation profile of the 2026-07-31 sweep

Regenerate with `python scripts/validation_profile.py`. No API calls; it reads
the records and runs `linkml-validate`.

**69 of 92 records validate (75%).** The 23 that do not are the subject of #215,
and this note explains why they are being measured rather than repaired.

## Why these are not being fixed in place

The obvious move — rewrite `IsNewVersionOf` to `is_new_version_of`, quote the
dates — is the wrong one, for two reasons.

**It would falsify the experiment.** These records are what the generator
produced under a stated prompt, model and temperature. That is the observation.
Editing them to look better makes the corpus a record of what we wish had been
generated, and every quality figure computed from it becomes uninterpretable.

**It would break provenance.** Each run's record pins its artifacts' hashes.
Editing the bytes makes those hashes disagree, and `d4d runs check` reports the
run as *drifted* — trading 23 validation errors for 23 broken provenance
records, which is a worse claim to make about a study corpus.

The failures are therefore evidence about generation quality, and the response
is to fix the *generator* and rerun, which is what the forward fixes do.

## By arm

| arm | invalid / total | rate |
|---|---|---|
| baseline (`claudecode_agent`) | 8 / 25 | 32% |
| baseline core | 2 / 25 | 8% |
| de_novo (`claudecode_agent_crate`) | 5 / 9 | 56% |
| de_novo core | 3 / 9 | 33% |
| crate_only | 2 / 9 | 22% |
| crate_only core | 3 / 9 | 33% |
| healthsheet | 0 / 3 | 0% |
| healthsheet core | 0 / 3 | 0% |

**The de_novo arm fails roughly twice as often as baseline** (8/18 = 44% against
10/50 = 20%), and healthsheet not at all. n is small — 3 records per project per
arm, and only 3 healthsheet records in total — so this is a signal worth
following, not a result. The plausible reading is that de_novo's larger, less
structured bundles give the model more room to invent shapes, but nothing here
tests that.

Core records fail less often than their full counterparts in every arm, which
is consistent with `CoreDataset` being the smaller target: 79 slots against 94,
and fewer object-ranged slots to get wrong.

## By cause

| records | cause | fixed forward? |
|---|---|---|
| 11 | temporal format | yes — `normalise_temporal()` on write |
| 9 | enum value not permitted | yes — DataCite alignment + digest exposure |
| 3 | wrong type (expected string) | no |
| 2 | union: no matching shape | no — see #226 |
| 3 | other | no |

The nine enum failures split into two kinds that deserve different treatment:

- **6 are DataCite spellings** — `IsNewVersionOf` (3), `HasPart` (3),
  `References` (1), `Continues` (1). The model reached for a vocabulary it knew
  because the schema digest never showed it the one the slot declares. Now
  fixed at the source.
- **2 are inventions** — `related_to`, and the free-text
  `is a later release in the same series as`. No vocabulary alignment repairs
  these; they are the model writing prose into an enum.

## What a rerun should show

Temporal and enum causes account for 20 of the 23 failures. If the forward fixes
work, a rerun under the current schema and digest should land near 3 remaining
failures rather than 23. If it does not, the fixes did not land and this note is
the baseline that says so.

The residue — wrong type, union shape, and the three unclassified — is
uninvestigated. #226 covers the union case, which is unsatisfiable by
construction and cannot be a generation defect at all.
