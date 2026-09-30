# Line breaks the attainability checks do not read (#3199, #3246)

Measured 2026-09-29 at `4b37eedff` over the 22 bundle versions that
provenance records under `data/d4d_concatenated/` name, and re-measured the
same day after review round 1 of PR #3419 widened the breaks the measure
joins (#3438) and added the wider window's own cost (#3439). The bytes of each
version are resolved as the attainability validator resolves them: the file
on disk where it hashes to the recorded md5, else the committed version that
does. Regenerate the table with:

```bash
poetry run python scripts/measure_unhyphenated_line_splits.py --compare-window 10 --joins-per-window 2
```

Re-measured 2026-09-30 with `--joins-per-window 2` (#3481), which adds the
last column: every run of two consecutive breaks read every way in which at
least one joins. The other columns are unchanged from the 2026-09-29 table.
That run took about 4.5 minutes of CPU time, most of it the 10-line comparison
and the two-break search on the largest bundles (VOICE_preprocessed_with_crate,
15,119 joinable breaks, 5 to 8 seconds for the two-break search alone).

The script writes nothing. It reads each provenance record as `credited`
does (`attainability.provenance_bundle`, #3579); a record that cannot be
read is listed under the table and the command exits 1. After review round
6 the reading was checked against the one before it on the same corpus: 22
versions named by 279 records, none unreadable, so the table is unchanged.
The 10-line comparison takes about a minute.
With `--compare-window 14` the result is the same, but each VOICE version
takes 45 to 90 seconds instead of 8.

## A word split with no hyphen (#3199)

`attainability.matching_lines` reads a line break as a space, and a break
after a hyphen also as a split word or a hyphenated compound. It does not
read a break inside a word that has no hyphen.

The table's columns:
- **Letter/letter breaks**: breaks with a letter, in any script, on both
  sides. The split-word test judges these.
- **Split words**: breaks whose halves join to a word while neither half is
  a word. This is the issue's method. "A word" means an entry of the word
  list or a line-interior token of the same bundle.
- **Wraps that join**: breaks whose halves are both words and also join to
  one word. Reading every break as nothing would join these too, like
  'over' / 'sight'.
- **Breaks joined**: every break between two lines that are not blank,
  except one after a hyphen, which `matching_lines` reads already. The
  missing reading could apply to any of these, not only to the letter/letter
  ones: the AI_READI bundles wrap their version as 'This documentation is
  for v' / '2.0.0', a letter/digit break (#3438).
- **Checks moved** and **Moved if every break joins**: checks that have a
  match across a split-word break, or across any of the breaks joined, when
  the two lines are joined with no space.
  `status` means the check is `not_stated_in_source` today and would become
  `unknown`. `lines` means the check is already `unknown` and would only
  list more lines.
- **Moved if up to 2 breaks join** (#3481): as those, for every run of two
  consecutive breaks read every way in which at least one is joined — a
  joinable break as a space or as nothing, a break after a hyphen under each
  of its three readings. It sees a word split over two unhyphenated breaks,
  a join beside a hyphen's reading, and a three-line statement whose one
  break is a space and the other the join, which the column before it does
  not. Like that column it reads no line outside the run: its three lines
  are all it searches, so a match over four or more lines is not found even
  when it needs only one join (#3672).

Word list: `/usr/share/dict/words` (sha256 `be41ad97963bf8dabedd5871d5d691596175269d540956b0f9965a885c2bbab9`, 234456 entries), plus each bundle's own line-interior tokens.

| Bundle | md5 | Records | Letter/letter breaks | Split words | Wraps that join | Checks moved | Breaks joined | Moved if every break joins | Hyphenated breaks | Mixed windows | Most in one | Moved if up to 2 breaks join |
|---|---|---:|---:|---|---:|---|---:|---|---:|---:|---:|---|
| `AI_READI_healthsheet_only.txt` | `a66b1681` | 12 | 12 | 0 | 1 | none | 138 | none | 0 | 0 | 0 | none |
| `AI_READI_preprocessed.txt` | `0f3abb51` | 23 | 1188 | 0 | 20 | none | 5798 | version_string (lines) | 113 | 71 | 3 | version_string (lines) |
| `AI_READI_preprocessed.txt` | `20150c10` | 5 | 1156 | 0 | 19 | none | 4733 | version_string (lines) | 111 | 71 | 3 | version_string (lines) |
| `AI_READI_preprocessed.txt` | `8aadffca` | 25 | 1162 | 0 | 19 | none | 4742 | version_string (lines) | 111 | 71 | 3 | version_string (lines) |
| `AI_READI_preprocessed.txt` | `8abd7bf5` | 3 | 1185 | 0 | 20 | none | 5798 | version_string (lines) | 113 | 71 | 3 | version_string (lines) |
| `AI_READI_preprocessed.txt` | `d22b61a9` | 4 | 1147 | 0 | 17 | none | 5996 | version_string (lines) | 113 | 71 | 3 | version_string (lines) |
| `CHORUS_crate_only.txt` | `06ad867c` | 9 | 9 | 0 | 0 | none | 338 | none | 4 | 0 | 1 | none |
| `CHORUS_preprocessed.txt` | `1ce7d891` | 28 | 251 | 0 | 0 | none | 360 | none | 10 | 0 | 1 | none |
| `CHORUS_preprocessed.txt` | `9b2ef4b6` | 30 | 250 | 0 | 0 | none | 359 | none | 10 | 0 | 1 | none |
| `CHORUS_preprocessed_with_crate.txt` | `47c3bebd` | 9 | 260 | 0 | 0 | none | 701 | none | 14 | 0 | 1 | none |
| `CM4AI_crate_only.txt` | `965b0aa6` | 9 | 9 | 0 | 0 | none | 2188 | none | 4 | 0 | 1 | none |
| `CM4AI_preprocessed.txt` | `1dfd34e5` | 18 | 3691 | 0 | 45 | none | 6963 | none | 42 | 2 | 2 | none |
| `CM4AI_preprocessed.txt` | `3694e188` | 18 | 3696 | 0 | 45 | none | 6970 | none | 42 | 2 | 2 | none |
| `CM4AI_preprocessed.txt` | `50037fc6` | 9 | 3688 | 0 | 45 | none | 6963 | none | 42 | 2 | 2 | none |
| `CM4AI_preprocessed_with_crate.txt` | `09f234f1` | 9 | 3705 | 0 | 45 | none | 9161 | none | 46 | 2 | 2 | none |
| `VOICE_PEDIATRIC_preprocessed.txt` | `008212ac` | 3 | 1005 | 0 | 7 | none | 2479 | version_string (lines) | 15 | 0 | 1 | version_string (lines) |
| `VOICE_PEDIATRIC_preprocessed.txt` | `327c2920` | 3 | 1006 | 0 | 7 | none | 2481 | version_string (lines) | 15 | 0 | 1 | version_string (lines) |
| `VOICE_crate_only.txt` | `e0da1c22` | 9 | 9 | 0 | 0 | none | 9947 | none | 4 | 0 | 1 | none |
| `VOICE_preprocessed.txt` | `9193c3cb` | 5 | 1724 | priori/ty (line 498) | 17 | none | 5169 | version_string (lines) | 87 | 104 | 4 | version_string (lines) |
| `VOICE_preprocessed.txt` | `dcd71717` | 21 | 1740 | priori/ty (line 498) | 17 | none | 5165 | version_string (lines) | 87 | 104 | 4 | version_string (lines) |
| `VOICE_preprocessed.txt` | `e637eb75` | 18 | 1743 | priori/ty (line 498) | 17 | none | 5169 | version_string (lines) | 87 | 104 | 4 | version_string (lines) |
| `VOICE_preprocessed_with_crate.txt` | `5c47f100` | 9 | 1752 | priori/ty (line 522) | 17 | none | 15119 | version_string (lines) | 91 | 104 | 4 | version_string (lines) |

Read each on its own within 10 lines rather than 6, the hyphenated breaks move no check's matching lines on any version measured.

At 10 lines the most hyphenated breaks in one window is 6 (`VOICE_preprocessed.txt` `9193c3cb`, 178 windows with two or more), read 726 ways; the table's Mixed windows and Most in one columns are at 6 lines.

The one split found is 'a priori' / 'ty for the Bridge2AI-Voice
consortium', which is "a priority". It is in all four VOICE document
versions and in no other bundle. No check's pattern matches "priority".

Reading each break as nothing, one break at a time, moves no check's status
on any version. It
adds lines to `version_string`, which is `unknown` on every version it
touches, in the AI_READI, VOICE and VOICE_PEDIATRIC document bundles. One of
those joins is a real split: 'This documentation is for v' / '2.0.0' in
every AI_READI document version, which joins to 'v2.0.0'. The others are
joins the reading would invent, such as a date and the next line's version
number ('Jan. 17, 2025' / '2.0.0'), a DOI after a version line, or a
section number after a sentence. That covers up to 15,119 breaks per bundle.

The first measure of this table joined only the letter/letter breaks, with
letters taken as ASCII, and read "moves nothing". That was true of those
breaks only; it missed the 'v' / '2.0.0' split and every break with a digit,
punctuation or a letter outside ASCII on one side (#3438).

**Decision.** Do not add the reading. Do not mark any of these versions
uncertifiable.
- On these 22 versions, neither choice would change an entry's status. The
  reading would add lines to `version_string` entries that are `unknown`
  already, most of them from joins it invents.
- Adding the reading would join ordinary wraps in every large bundle.

All three columns are lower bounds. The word list and the bundle vocabulary
leave out words neither contains, so the split-word count misses a split
into a word neither knows. The "every break joins" column has no word-list
limit, since it joins every break the reading could apply to, but it joins
them one at a time: it searches only the two lines on either side of one
break, joined, and reads no other line. A match that needs two breaks at once is not
searched there (#3470) — a word split over two unhyphenated breaks ('con' /
'sen' / 't'), one join beside a hyphen's reading ('con-' / 'sen' / 't'), or
a statement over three lines whose one break is a space and the other the
join ('a data' / 'protection im' / 'pact assessment', which the one-break
search reads as nothing while 'a data pro' / 'tection impact assessment'
moves `ethics_review`). The "up to 2 breaks join" column searches exactly
those (#3481), and on the 22 versions it reads what the one-break column
reads: no check's status moves, and `version_string` gains lines on the same
versions only. A match that needs three or more joins at once ('co' / 'ns'
/ 'en' / 't'), or a join and a hyphen's reading on breaks not both in one
run of two, is still not searched. Nor is a match that runs over more than
the three lines of one run, however few joins it needs: 'a data' /
'protection' / 'im' / 'pact assessment' needs one join ('im' / 'pact') and
is found by neither column, since the two-break search reads 'protection' /
'im' / 'pact' and never 'data' with them (#3672). So "moves no check's
status" is a result about matches whose joins lie in one run of up to two
breaks and whose lines are that run's three at most. The decision does not rest on it being exhaustive: it
rests on the cost of the reading, which a search over more breaks would only
raise.

A version certified beyond these 22 is checked when it is written (#3408):
`write_document`, which `derive --write` calls, runs the two-break search and
the 10-line window below on every deterministic `not_stated_in_source` entry
and refuses the file when either gives the check a match, naming the item and
the lines. It reads no word list, so it runs where `/usr/share/dict/words` is
missing. It has the two-break search's limits: a match over four or more
lines that needs a join, like the one above, passes it (#3672). A refused entry needs a curator's reading (a curator entry is kept
in place of the deterministic one), or the reading or a "not certifiable"
flag decided then. On these 22 versions it refuses nothing: the only
`not_stated_in_source` entries are on the two CHORUS document versions, and
no reading it adds matches there.

## Mixed readings beyond six lines (#3246)

**Decision.** The bound `MIXED_WINDOW_LINES = 6` stays.
- Widening the window to 10 lines or to 14 lines moves no check's matching
  lines on any of the 22 versions. That is a result at those two widths; a
  statement whose hyphens need different readings over more than 14 lines
  was not searched.
- A window costs 3^k - 3 readings for its k hyphenated breaks. At the
  current 6 lines the most breaks in one window is 4 (VOICE, 78 readings),
  and VOICE has 104 windows with two or more. The wider windows cost more
  (#3439): on VOICE_preprocessed a 10-line window holds up to 6 breaks (726
  readings, 175 to 179 windows with two or more across the four VOICE
  document versions) and a 14-line window up to 8 (6,558 readings, 256 to
  264 windows). That is why a VOICE version takes 45 to 90 seconds at 14
  lines. The most in one window elsewhere at 14 lines is 6 (AI_READI) and 2
  (CHORUS, CM4AI, VOICE_PEDIATRIC).
- An exact method would match regexes over a lattice of readings. That is
  more machinery than any measured bundle needs.

Each entry's note and the README keep stating the limit. The gate
`write_document` runs (#3408) reads a 10-line window on every absence it
certifies; a version whose table row shows many mixed windows or more than 4
breaks in one 6-line window should still be re-run with a wider
`--compare-window` before it is certified.
