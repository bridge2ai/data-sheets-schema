# Standards Explorer datasheets

The publication directory is `src/html/output/`. The v8 display selection uses
the **previously selected canonical baseline API full record for each project**:

| Project | Canonical replicate | Run prefix |
| --- | --- | --- |
| AI-READI | 2 | `2026-09-04g` |
| CHORUS | 2 | `2026-09-04f` |
| CM4AI | 3 | `2026-09-04g` |
| VOICE | 1 | `2026-09-04f` |

The existing `d4d runs canonical --runtime api --config 2026-09-04` resolver
identifies these choices from the original provenance. They were selected on
2026-09-08 using validity, review adverse counts (difference ≤2 treated as a tie),
coverage and label order, as documented in `notes/generic_v8_analysis_plan.md`.
The later `notes/review_selection_policy_2026-09-11.md` makes review counts
report-only for future selections and explicitly preserves existing canonical
decisions. Publishing these recorded choices does not rerank the replicates or
establish semantic-quality winners. Other replicates and rejected attempts remain
in the repository. The initial uniform-replicate-1 publication preparation is
retained in commit `289863340cf864bf0ed6ec2197ca8cb637eec5f1`; its attempted upload
did not publish a Synapse snapshot.

The exact paths, source hashes, original provenance hashes, render date and HTML
hashes are recorded in `src/html/output/v8-publication.json`. These are historical
v8 records generated with schema 2.0.0. Rendering does not regenerate them, migrate
them to the current schema, or establish scientific approval. Historical YAML,
HTML and shared CSS remain unchanged.

To reproduce the publication from the repository root:

```bash
PYTHONPATH=src:. poetry run python scripts/adhoc/render_v8_standards_explorer.py
PYTHONPATH=src:. poetry run python scripts/adhoc/render_v8_standards_explorer.py --check
poetry run python -m pytest tests/test_v8_standards_explorer_publication.py tests/test_d4d_to_synapse_table.py -q -p no:cacheprovider
```

The helper requires the pinned source commit to be available locally. It checks
the retained cohort and source bytes before writing, preserves every scalar value,
escapes literal source text, and uses recursive lists instead of lossy author or
funding tables. It embeds styles scoped to `.d4d-v8`, because the portal inserts
the HTML into its own page and does not load the publication's relative stylesheet.
`datasheet-v8.css` is also supplied for the existing Synapse table contract.

On a main-branch publication change, `.github/workflows/d4d_to_synapse_table.yml`
uploads four HTML rows and one CSS row to `D4D_content` (`syn68885644`) and creates
a snapshot. JSON RowSets preserve multiline HTML exactly; the Synapse CSV import
path skips empty physical lines, including inside quoted HTML cells. The uploader
requires the complete bundle before login, verifies new
rows before deleting the captured old rows, and snapshots only after verifying
the final contents. This is not a transactional replacement: a failed cleanup
can leave both old and new rows in the live table; the previous snapshot remains
the published version until a successful retry. No direct Synapse operation is
needed when merging the publication PR.

The first upload ([run 38981856572](https://github.com/bridge2ai/data-sheets-schema/actions/runs/38981856572))
authenticated and appended the five initial replicate-1 rows, then stopped on
exact read-back verification. It deleted no prior rows and created no snapshot.
Anonymous JSON queries confirmed all five previous rows remained identical to
snapshot 13. The new CSS was exact, while the four HTML cells lost only empty
lines: AI-READI 214, CHORUS 156, CM4AI 174 and VOICE 216. No nonempty lines changed.
The [diagnostic summary](standards-explorer-roundtrip-2026-10-16.json) records
hashes and differences. The [captured public JSON responses](standards-explorer-roundtrip-2026-10-16.tar.gz)
are retained as a compressed archive. `scripts/adhoc/inspect_v8_synapse_roundtrip.py`
reproduces the comparison with `--raw-dir` pointing to the extracted archive and
`--output-dir` pointing to a fresh external directory, with the failed upload pinned
to commit `289863340cf864bf0ed6ec2197ca8cb637eec5f1`. The corrected uploader uses
JSON for both append and verification; it retains exact comparisons and safely
replaces all captured old/staged rows only after the chosen canonical set verifies.

The registry's [publication workflow](https://github.com/bridge2ai/b2ai-standards-registry/blob/main/.github/workflows/project_data_change.yml)
then advances `mv_D4D_content` (`syn77626807`) and dependent views. It is scheduled
daily at 06:17 UTC; GitHub may delay it. Standards Explorer reads this materialized
view, so a successful D4D upload is not proof that the portal already displays
the new pages. Check the downstream refresh separately.

Tracking: [publication #5055](https://github.com/bridge2ai/data-sheets-schema/issues/5055)
and [renderer review #5056](https://github.com/bridge2ai/data-sheets-schema/issues/5056).
