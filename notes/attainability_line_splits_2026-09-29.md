# Line breaks the attainability checks do not read (#3199, #3246)

Measured 2026-09-29 at `4b37eedff` over the 22 bundle versions that
provenance records under `data/d4d_concatenated/` name. The bytes of each
version are resolved as the attainability validator resolves them: the file
on disk where it hashes to the recorded md5, else the committed version that
does. Regenerate the table with:

```bash
poetry run python scripts/measure_unhyphenated_line_splits.py --compare-window 10
```

The script writes nothing. The 10-line comparison takes about a minute.
With `--compare-window 14` the result is the same, but each VOICE version
takes 45 to 90 seconds instead of 8.

## A word split with no hyphen (#3199)

`attainability.matching_lines` reads a line break as a space, and a break
after a hyphen also as a split word or a hyphenated compound. It does not
read a break inside a word that has no hyphen.

The table's columns:
- **Letter/letter breaks**: breaks with a letter on both sides. The missing
  reading could apply only to these.
- **Split words**: breaks whose halves join to a word while neither half is
  a word. This is the issue's method. "A word" means an entry of the word
  list or a line-interior token of the same bundle.
- **Wraps that join**: breaks whose halves are both words and also join to
  one word. Reading every break as nothing would join these too, like
  'over' / 'sight'.
- **Checks moved** and **Moved if every break joins**: checks that have a
  match across such a break when the two lines are joined with no space.
  `status` means the check is `not_stated_in_source` today and would become
  `unknown`. `lines` means the check is already `unknown` and would only
  list more lines.

Word list: `/usr/share/dict/words` (sha256 `be41ad97963bf8dabedd5871d5d691596175269d540956b0f9965a885c2bbab9`, 234456 entries), plus each bundle's own line-interior tokens.

| Bundle | md5 | Records | Letter/letter breaks | Split words | Wraps that join | Checks moved | Moved if every break joins | Hyphenated breaks | Mixed windows | Most in one |
|---|---|---:|---:|---|---:|---|---|---:|---:|---:|
| `AI_READI_healthsheet_only.txt` | `a66b1681` | 12 | 12 | 0 | 1 | none | none | 0 | 0 | 0 |
| `AI_READI_preprocessed.txt` | `0f3abb51` | 23 | 1185 | 0 | 20 | none | none | 113 | 71 | 3 |
| `AI_READI_preprocessed.txt` | `20150c10` | 5 | 1153 | 0 | 19 | none | none | 111 | 71 | 3 |
| `AI_READI_preprocessed.txt` | `8aadffca` | 25 | 1159 | 0 | 19 | none | none | 111 | 71 | 3 |
| `AI_READI_preprocessed.txt` | `8abd7bf5` | 3 | 1185 | 0 | 20 | none | none | 113 | 71 | 3 |
| `AI_READI_preprocessed.txt` | `d22b61a9` | 4 | 1147 | 0 | 17 | none | none | 113 | 71 | 3 |
| `CHORUS_crate_only.txt` | `06ad867c` | 9 | 9 | 0 | 0 | none | none | 4 | 0 | 1 |
| `CHORUS_preprocessed.txt` | `1ce7d891` | 28 | 251 | 0 | 0 | none | none | 10 | 0 | 1 |
| `CHORUS_preprocessed.txt` | `9b2ef4b6` | 30 | 250 | 0 | 0 | none | none | 10 | 0 | 1 |
| `CHORUS_preprocessed_with_crate.txt` | `47c3bebd` | 9 | 260 | 0 | 0 | none | none | 14 | 0 | 1 |
| `CM4AI_crate_only.txt` | `965b0aa6` | 9 | 9 | 0 | 0 | none | none | 4 | 0 | 1 |
| `CM4AI_preprocessed.txt` | `1dfd34e5` | 18 | 3664 | 0 | 45 | none | none | 42 | 2 | 2 |
| `CM4AI_preprocessed.txt` | `3694e188` | 18 | 3669 | 0 | 45 | none | none | 42 | 2 | 2 |
| `CM4AI_preprocessed.txt` | `50037fc6` | 9 | 3664 | 0 | 45 | none | none | 42 | 2 | 2 |
| `CM4AI_preprocessed_with_crate.txt` | `09f234f1` | 9 | 3678 | 0 | 45 | none | none | 46 | 2 | 2 |
| `VOICE_PEDIATRIC_preprocessed.txt` | `008212ac` | 3 | 1005 | 0 | 7 | none | none | 15 | 0 | 1 |
| `VOICE_PEDIATRIC_preprocessed.txt` | `327c2920` | 3 | 1006 | 0 | 7 | none | none | 15 | 0 | 1 |
| `VOICE_crate_only.txt` | `e0da1c22` | 9 | 9 | 0 | 0 | none | none | 4 | 0 | 1 |
| `VOICE_preprocessed.txt` | `9193c3cb` | 5 | 1724 | priori/ty (line 498) | 17 | none | none | 87 | 104 | 4 |
| `VOICE_preprocessed.txt` | `dcd71717` | 21 | 1740 | priori/ty (line 498) | 17 | none | none | 87 | 104 | 4 |
| `VOICE_preprocessed.txt` | `e637eb75` | 18 | 1743 | priori/ty (line 498) | 17 | none | none | 87 | 104 | 4 |
| `VOICE_preprocessed_with_crate.txt` | `5c47f100` | 9 | 1752 | priori/ty (line 522) | 17 | none | none | 91 | 104 | 4 |

Read each on its own within 10 lines rather than 6, the hyphenated breaks move no check's matching lines on any version measured.

The one split found is 'a priori' / 'ty for the Bridge2AI-Voice
consortium', which is "a priority". It is in all four VOICE document
versions and in no other bundle. No check's pattern matches "priority".

Reading every letter/letter break as nothing also moves no check's status
or matching lines on any version. That covers up to 3,678 breaks per
bundle, including up to 45 ordinary wraps that would join.

**Decision.** Do not add the reading. Do not mark any of these versions
uncertifiable.
- On these 22 versions, neither choice would change an entry.
- Adding the reading would join ordinary wraps in every large bundle.

The word list and the bundle vocabulary leave out words neither contains,
so the split-word count is a lower bound. The "every break joins" column
has no such limit, because it joins every letter/letter break, and it moves
nothing.

A version PR3 certifies beyond these 22 should be measured first. If a
check moves on it, the reading or a "not certifiable" flag needs deciding
then.

## Mixed readings beyond six lines (#3246)

**Decision.** The bound `MIXED_WINDOW_LINES = 6` stays.
- Widening the window to 10 lines or to 14 lines moves no check's matching
  lines on any of the 22 versions.
- The widest windows cost 3^k - 3 readings for their k breaks. The most
  breaks in any one window is 4 (VOICE), and VOICE has 104 windows with two
  or more breaks.
- An exact method would match regexes over a lattice of readings. That is
  more machinery than any measured bundle needs.

Each entry's note and the README keep stating the limit. A version whose
table row shows many mixed windows or more than 4 breaks in one window
should be re-run with a wider `--compare-window` before it is certified.
