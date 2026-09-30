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
- **The text is read line by line and whole.** The bundles are hard-wrapped,
  so a statement a line break splits still matches: the break is read as a
  space and, after a hyphen, as a split word (`con-` `sent`) or a hyphenated
  compound (`human-` `subjects`), the continuation line's indentation read as
  part of the break. Each break after a hyphen is read on its own within any
  six consecutive lines, so one statement can carry both kinds (`a data-`
  `protec-` `tion impact`). A word split with no hyphen is not read that way,
  nor a statement over more than six lines whose hyphens need different
  readings; every entry's note says so. Both limits were measured over the
  22 bundle versions provenance records name, within stated bounds, and
  neither moved a check's status there: reading each break as nothing, one
  break at a time, only adds lines to `version_string` entries that are
  `unknown` already, and widening the mixed window to 10 or 14 lines moves
  no check's lines. A match needing two unhyphenated joins at once, or one
  join beside another break's reading, was not searched, nor a window wider
  than 14 lines, so these are lower bounds
  (`notes/attainability_line_splits_2026-09-29.md`, #3199, #3246, #3438, #3470).
  Measure a new version before certifying it:
  `python scripts/measure_unhyphenated_line_splits.py --compare-window 10`.
- **A valid file's deterministic entries are the generator's output**, type
  for type: `hit_count: false` or snippet lines `[45.0, 45]` are refused,
  although Python compares them equal to `0` and `[45, 45]`. Every entry
  names its `route`, `null` included. The format is closed: a key it does not
  name, at any level (top, `bundle`, a `rubrics` identity, an entry, a
  snippet), makes the file invalid.
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

`check` reports a file it cannot read, or that is not UTF-8, as `INVALID`
and goes on to the next. `credited` names, per evaluation, the absences it
was checked against, and reports a row whose file can yield no finding as
`unchecked` with the reason — no file for the bundle version, a file that
pins no text of the evaluation's rubric (the CHORUS file and every rubric20
evaluation), or one that marks none of that rubric's items absent — and
counts those rows apart from the ones checked, whose zero is a measurement.
A credit on an item only a route entry marks absent (E1.1, whose persistent-URI
route no pattern settles) is listed as `credited_on_other_route` for a curator
to read, and is neither a finding nor a `--strict` failure. An evaluation
that cannot be read — not UTF-8, not JSON, an element with no `id`, a score
on an absence item that is not a finite number (a list, a boolean, NaN, an
integer too large for a float, #3577) — or whose record's provenance cannot
be read, or sits at a path carrying a NUL byte (in the evaluation's project,
method or label, #3578), or names a bundle version whose
attainability file name cannot be looked up — a component too long for
the file system, or a NUL byte in its path or md5 (#3469, #3541) — is reported on its own row as `unreadable`
with the file and the error, counted apart, and fails the run with or without
`--strict`; the evaluations after it are still reported.

| File | Bundle | Entries |
|---|---|---|
| `CHORUS_preprocessed_9b2ef4b6….yaml` | the bundle all six v7/v8 CHORUS reference records read | E1.1 (DOI/RRID route), E4.4, E10.2 `not_stated_in_source`; E4.1, E6.1 `unknown` |

Nothing here changes a score, a rubric or an evaluation.
