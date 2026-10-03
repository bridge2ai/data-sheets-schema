# Context around attainability joins (#3678)

Measured the same **22 exact bundle versions** as the unchanged [2026-09-29 table](attainability_line_splits_2026-09-29.md), using implementation `84a2e8962e4006aea7e9a96f894c04ea5ee910c0`. The tracked provenance inventory contains **286 files**: **279 name bundle identities**, and seven merged-core/curated records name no bundle under the canonical provenance reader. The manifest lists those seven files separately. All 22 path/MD5 identities and all 279 measured record memberships reproduce the historical table. [The machine-readable manifest](attainability_join_context_2026-10-02.json) pins the implementation files, word list, all 286 provenance inputs, their panel membership distinction, complete bundle MD5/SHA256 identities, recovered source authorities and per-version results. No bundle was missing or unmeasured.

The join run remains **K=2 consecutive breaks**. The certification gate now searches within **W=10 context lines**. Only the run introduces unhyphenated JOIN readings; outer ordinary breaks are spaces, and outer hyphens use each of the three uniform readings: space, drop and keep. Arbitrary mixed outer-hyphen readings combined with joins, joins outside one K-break run, three or more joins, and matches wider than W remain outside this search. A lexical candidate triggers source review; it does not establish support or change a rubric score. #3645 and the scientific attainability/aggregation decisions in #2925/#3046 remain separate.

The four-line counterexample `a data` / `protection` / `im` / `pact assessment` is now refused by the actual `derive --write` CLI, with no file changes. Its default deterministic draft remains unchanged; only certification is blocked. Omitted pure-helper context and all older measurement columns retain their prior behavior.

## Results

No check moved from absence to unknown on these 22 versions under the bounded contextual search. The contextual **status/lines categories** equal the legacy K=2 categories. This categorical result does not assert equality of every joined-match line set. The standalone VOICE benchmark below does compare those complete line sets and finds them equal on that version.

All 22 default document serializations are byte-identical to the parent implementation. Both historical CHORUS document versions, MD5 `1ce7d891fa81ad4b1f8290ddeec33461` and `9b2ef4b65d67957f79362266cab0bc7a`, retain the three deterministic absences E1.1/E4.4/E10.2 and produce **no certification refusal**. The full panel's actual certification checks likewise produce no refusals. All 412 captured input files stayed unchanged; no historical attainability file or old table was regenerated.

Word list: `/usr/share/dict/words` (sha256 `be41ad97963bf8dabedd5871d5d691596175269d540956b0f9965a885c2bbab9`, 234456 entries), plus each bundle's own line-interior tokens.

| Bundle | md5 | Records | Letter/letter breaks | Split words | Wraps that join | Checks moved | Breaks joined | Moved if every break joins | Hyphenated breaks | Mixed windows | Most in one | Moved if up to 2 breaks join | Moved with 10-line join context |
|---|---|---:|---:|---|---:|---|---:|---|---:|---:|---:|---|---|
| `AI_READI_healthsheet_only.txt` | `a66b1681` | 12 | 12 | 0 | 1 | none | 138 | none | 0 | 0 | 0 | none | none |
| `AI_READI_preprocessed.txt` | `0f3abb51` | 23 | 1188 | 0 | 20 | none | 5798 | version_string (lines) | 113 | 71 | 3 | version_string (lines) | version_string (lines) |
| `AI_READI_preprocessed.txt` | `20150c10` | 5 | 1156 | 0 | 19 | none | 4733 | version_string (lines) | 111 | 71 | 3 | version_string (lines) | version_string (lines) |
| `AI_READI_preprocessed.txt` | `8aadffca` | 25 | 1162 | 0 | 19 | none | 4742 | version_string (lines) | 111 | 71 | 3 | version_string (lines) | version_string (lines) |
| `AI_READI_preprocessed.txt` | `8abd7bf5` | 3 | 1185 | 0 | 20 | none | 5798 | version_string (lines) | 113 | 71 | 3 | version_string (lines) | version_string (lines) |
| `AI_READI_preprocessed.txt` | `d22b61a9` | 4 | 1147 | 0 | 17 | none | 5996 | version_string (lines) | 113 | 71 | 3 | version_string (lines) | version_string (lines) |
| `CHORUS_crate_only.txt` | `06ad867c` | 9 | 9 | 0 | 0 | none | 338 | none | 4 | 0 | 1 | none | none |
| `CHORUS_preprocessed.txt` | `1ce7d891` | 28 | 251 | 0 | 0 | none | 360 | none | 10 | 0 | 1 | none | none |
| `CHORUS_preprocessed.txt` | `9b2ef4b6` | 30 | 250 | 0 | 0 | none | 359 | none | 10 | 0 | 1 | none | none |
| `CHORUS_preprocessed_with_crate.txt` | `47c3bebd` | 9 | 260 | 0 | 0 | none | 701 | none | 14 | 0 | 1 | none | none |
| `CM4AI_crate_only.txt` | `965b0aa6` | 9 | 9 | 0 | 0 | none | 2188 | none | 4 | 0 | 1 | none | none |
| `CM4AI_preprocessed.txt` | `1dfd34e5` | 18 | 3691 | 0 | 45 | none | 6963 | none | 42 | 2 | 2 | none | none |
| `CM4AI_preprocessed.txt` | `3694e188` | 18 | 3696 | 0 | 45 | none | 6970 | none | 42 | 2 | 2 | none | none |
| `CM4AI_preprocessed.txt` | `50037fc6` | 9 | 3688 | 0 | 45 | none | 6963 | none | 42 | 2 | 2 | none | none |
| `CM4AI_preprocessed_with_crate.txt` | `09f234f1` | 9 | 3705 | 0 | 45 | none | 9161 | none | 46 | 2 | 2 | none | none |
| `VOICE_PEDIATRIC_preprocessed.txt` | `008212ac` | 3 | 1005 | 0 | 7 | none | 2479 | version_string (lines) | 15 | 0 | 1 | version_string (lines) | version_string (lines) |
| `VOICE_PEDIATRIC_preprocessed.txt` | `327c2920` | 3 | 1006 | 0 | 7 | none | 2481 | version_string (lines) | 15 | 0 | 1 | version_string (lines) | version_string (lines) |
| `VOICE_crate_only.txt` | `e0da1c22` | 9 | 9 | 0 | 0 | none | 9947 | none | 4 | 0 | 1 | none | none |
| `VOICE_preprocessed.txt` | `9193c3cb` | 5 | 1724 | priori/ty (line 498) | 17 | none | 5169 | version_string (lines) | 87 | 104 | 4 | version_string (lines) | version_string (lines) |
| `VOICE_preprocessed.txt` | `dcd71717` | 21 | 1740 | priori/ty (line 498) | 17 | none | 5165 | version_string (lines) | 87 | 104 | 4 | version_string (lines) | version_string (lines) |
| `VOICE_preprocessed.txt` | `e637eb75` | 18 | 1743 | priori/ty (line 498) | 17 | none | 5169 | version_string (lines) | 87 | 104 | 4 | version_string (lines) | version_string (lines) |
| `VOICE_preprocessed_with_crate.txt` | `5c47f100` | 9 | 1752 | priori/ty (line 522) | 17 | none | 15119 | version_string (lines) | 91 | 104 | 4 | version_string (lines) | version_string (lines) |

Join context: at most 10 lines, joins in one run of 2 consecutive breaks; outer hyphens read uniformly as space, drop or keep. Arbitrary mixed outer-hyphen readings combined with joins are not searched. Older columns are unchanged.

Read each on its own within 10 lines rather than 6, the hyphenated breaks move no check's matching lines on any version measured.

At 10 lines the most hyphenated breaks in one window is 6 (`VOICE_preprocessed.txt` `9193c3cb`, 178 windows with two or more), read 726 ways; the table's Mixed windows and Most in one columns are at 6 lines.

## Cost

Fresh sequential processes evaluated all five join patterns on the exact `VOICE_preprocessed_with_crate.txt` version `5c47f10064daed5d314dbd302fdff979`, with 15,119 joinable breaks. Source recovery and line indexing were outside the timed region. CPU uses `time.process_time`; wall time uses `time.perf_counter`; peak memory is process maximum resident size through the search. These are observations on the pinned Python/platform in the manifest, not universal timing guarantees.

| Search | CPU seconds | Wall seconds | Peak resident MiB |
|---|---:|---:|---:|
| Historical K=2, no context | 3.335 | 3.364 | 48.98 |
| K=2, W=10 context | 65.330 | 66.371 | 49.58 |

Context cost **19.6 times** the CPU time in this five-pattern benchmark. Readings are streamed, with deduplication confined to one window; there is no search cap or silent truncation. Certification evaluates only checks with deterministic absences, so these VOICE documents perform no join search during certification. A future large bundle with absences can incur this additional cost. The measured correctness change is retained without claiming the wider search is free or exhaustive.

## Reproduce

Use a fresh checkout with the manifest's implementation file hashes, the exact tracked provenance inputs and the word-list hash shown above:

```bash
python scripts/measure_unhyphenated_line_splits.py --compare-window 10 --joins-per-window 2 --join-context-lines 10 --json
```

The new context column is opt-in in the measuring script; omitting it retains the old columns and JSON shape. Contextual reports disclose exact bundle bytes and fail when a requested version cannot be recovered. A future corpus can contain other versions, so compare the complete path/MD5/SHA256 panel against this manifest before calling a run a reproduction of these 22 versions. The historical table was independently compared column-for-column: its record counts and measurements are all reproduced unchanged.

For a fixed-panel rerun regardless of future corpus membership, iterate `measurement.rows` from the manifest, recover each bundle with `attainability.resolve_bytes(path, md5=..., sha256=...)`, load the pinned word list with `measure_unhyphenated_line_splits.load_words`, and call `measure(text, dictionary, compare_window=10, joins_per_window=2, join_context_lines=10)`. Fail on any missing identity or result rather than filling zeroes. Per-version timing and default-document hashes are retained in `per_version_checks`.
