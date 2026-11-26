# HTML previews of the 2026-11-25c release-series datasheets

One file per run: `<PROJECT>_rep<N>.html`, rendered with `d4d render html` from the full
record of label `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep<N>` under
`data/d4d_concatenated/claudecode_release/`, at main `483bed03b`.

These are previews for choosing and reviewing. They are not the canonical HTML under
`data/d4d_html/`; that is generated for the one replicate per project that is selected.

CM4AI replicates 1 and 3 were rendered with `--skip-validation`. Both records carry
`resources`, so the renderer's own pre-check validated them as `DatasetCollection` and
refused them; the records validate as `Dataset` under the schema (see `../gates/`).
CM4AI replicate 2 has no `resources` and rendered with the pre-check on, as did the other
twelve.

Checked with `scripts/adhoc/scan_data_pr_private_details_20261126.py`: no account name,
no absolute home-directory path and no usage wording in the 15 pages or the stylesheet.
The 16 email addresses it reports are contact addresses the datasheets state from their
sources.
