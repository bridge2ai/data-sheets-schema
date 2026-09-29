# Attainability of rubric items, per bundle version (#2925)

A rubric zero cannot tell "the generator omitted it" from "the bundle never
states it". Each file here records the second half for **one bundle version**:
`<bundle stem>_<md5>.yaml`, with the bundle's path, md5 and sha256, the rubric
text it is keyed to (path and sha256), and one entry per rubric item (or per
route of an item) with a status, the method that decided it and the evidence.
The format is documented in `src/data_sheets_schema/attainability.py`.

- **Deterministic entries decide absence only.** Zero lines matching a check's
  pattern give `not_stated_in_source`; any match gives `unknown`, with the
  matching lines listed by chunk id and sha256. A match is never `supported`:
  the CHORUS "IRB" lines are a training curriculum.
- **Curator and judge entries** (`method: curator` / `judge:<id>`) may assert
  support; their snippets are checked against the bundle bytes, their reading
  is not.
- A file about a bundle that has since changed on disk stays valid: the
  validator reads the committed version whose hashes it records.
- The chunk rule is written out in full and must be one the chunker
  implements (`chunking.validate_rule`). The chunker reads only the two
  window bounds, and an empty rule as its own default, so an empty or
  invented rule is refused rather than silently chunked as another one.

```bash
python -m data_sheets_schema.attainability check                 # validate every file here
python -m data_sheets_schema.attainability derive --bundle PATH --md5 MD5 --write
python -m data_sheets_schema.attainability credited EVALUATION.json ...   # credited though not stated
```

| File | Bundle | Entries |
|---|---|---|
| `CHORUS_preprocessed_9b2ef4b6….yaml` | the bundle all six v7/v8 CHORUS reference records read | E1.1 (DOI/RRID route), E4.4, E10.2 `not_stated_in_source`; E4.1, E6.1 `unknown` |

Nothing here changes a score, a rubric or an evaluation.
