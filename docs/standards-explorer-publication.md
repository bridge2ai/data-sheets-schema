# Standards Explorer datasheets

The publication directory is `src/html/output/`. The v8 display selection is
the **retained baseline API full record, replicate 1, for each of the four
projects**. AI-READI and CM4AI use `2026-09-04g_..._rep1`; CHORUS and VOICE use
`2026-09-04f_..._rep1`. This is a uniform display selection, not a ranking by
evaluation score. Other replicates and rejected attempts remain in the repository.

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
a snapshot. The uploader requires the complete bundle before login, verifies new
rows before deleting the captured old rows, and snapshots only after verifying
the final contents. This is not a transactional replacement: a failed cleanup
can leave both old and new rows in the live table; the previous snapshot remains
the published version until a successful retry. No direct Synapse operation is
needed when merging the publication PR.

The registry's [publication workflow](https://github.com/bridge2ai/b2ai-standards-registry/blob/main/.github/workflows/project_data_change.yml)
then advances `mv_D4D_content` (`syn77626807`) and dependent views. It is scheduled
daily at 06:17 UTC; GitHub may delay it. Standards Explorer reads this materialized
view, so a successful D4D upload is not proof that the portal already displays
the new pages. Check the downstream refresh separately.

Tracking: [publication #5055](https://github.com/bridge2ai/data-sheets-schema/issues/5055)
and [renderer review #5056](https://github.com/bridge2ai/data-sheets-schema/issues/5056).
