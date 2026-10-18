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
a snapshot via the CSV/S3 upload path (`synapseclient.Table(tableId, values=df)`),
the same mechanism every publication has used since 2025-08-14. The uploader
requires the complete bundle before login, verifies new rows before deleting the
captured old rows, and snapshots only after verifying the final contents. This is
not a transactional replacement: a failed cleanup can leave both old and new rows
in the live table; the previous snapshot remains the published version until a
successful retry. No direct Synapse operation is needed when merging the
publication PR.

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
to commit `289863340cf864bf0ed6ec2197ca8cb637eec5f1`.

The next fix (`0b484c15e`, #5058) switched the append itself to an inline JSON
RowSet, preserving blank lines exactly. That traded one problem for another: the
single-request JSON body for this publication's five rows (~483 KB of JSON-encoded
HTML/CSS) exceeds what AWS WAF will inspect on
`/entity/{id}/table/transaction/async/start` for Synapse's production API — every
run was rejected with a bare, non-Synapse `403 Forbidden` straight from the load
balancer (`Server: awselb/2.0`), before Synapse's application layer ever saw the
request. A same-day fix reverted the append to the CSV/S3 path described above,
re-accepting the known content loss. That loss predates v8 entirely — every
CSV-based upload since 2025-08-14 was almost certainly equally affected; #5055's
live round-trip check was simply the first time anyone verified exact byte
fidelity against the live table. It is also confirmed visually inert: this
schema's HTML never places a multi-newline run inside a whitespace-significant
element (no `<pre>`; the only `white-space: pre-wrap` rule in
`datasheet-v8.css` applies to single-line `source-value` spans, none of which
contain an embedded newline in any v8 file).

The exact mechanism was initially mismodeled as "drop every exactly-empty
physical line," which matched offline tests but failed verification against
the real table (table version 35, same-day retry): that model also ate a
genuine leading blank line that Synapse actually preserves. Checked directly
against the version-35 row content, the real rule is narrower — Synapse's
CSV-import collapses every run of two or more consecutive bare `\n` characters
inside a quoted multiline cell down to one; an isolated single newline
anywhere, including a leading or trailing one, or a CRLF-delimited blank line,
survives untouched. This reproduces all four HTML cells and the CSS cell
byte-for-byte. `generate_table`'s verification now predicts and tolerates
exactly this discrepancy (`_collapse_consecutive_newlines` in
`utils/d4d_to_synapse_table.py`) and still fails on any other content mismatch.

The registry's [publication workflow](https://github.com/bridge2ai/b2ai-standards-registry/blob/main/.github/workflows/project_data_change.yml)
then advances `mv_D4D_content` (`syn77626807`) and dependent views. It is scheduled
daily at 06:17 UTC; GitHub may delay it. Standards Explorer reads this materialized
view, so a successful D4D upload is not proof that the portal already displays
the new pages. Check the downstream refresh separately.

Tracking: [publication #5055](https://github.com/bridge2ai/data-sheets-schema/issues/5055)
and [renderer review #5056](https://github.com/bridge2ai/data-sheets-schema/issues/5056).
