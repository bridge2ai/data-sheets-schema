Perform deep research over a project's input documents with the Monarch
deep-research-client, producing cited research reports that become a
*declared, provenance-stamped supplementary source* for a D4D generation —
a research-augmented arm, never a silent enrichment of the baseline bundle.

## What this is for

The LLM-judge passes show the recurring gap classes in generated datasheets
are facts the input bundles simply lack: dataset DOIs and registry entries,
publications citing the dataset, governing license text, version history,
IRB records, related datasets. Deep research can recover exactly these —
with citations — but the result is *external evidence* and must be handled
under this repository's evidence rules.

## The client

`monarch-initiative/deep-research-client` — one CLI over OpenAI Deep
Research, Edison Scientific, Asta, Perplexity, Consensus, Cyberian and a
local Claude Code provider, with file-based caching.

```bash
uvx deep-research-client providers            # what is available here
uvx deep-research-client research "QUERY" \
  --provider <name> --cache-dir data/deep_research/cache -o <out.md>
```

Provider selection: use whichever key the environment supplies
(`OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `EDISON_API_KEY`, …). The
`claude_code` provider is auto-detected from the local `claude` CLI and
bills nothing extra — prefer it when no research key is configured
(verified available in this environment, alongside `cyberian`).
External providers are billed: apply the canary rule — one query end to
end, verify the report and the cache file exist and are non-empty, then
fan out.

## Evidence discipline (non-negotiable)

1. **Research output is secondary, model-generated evidence.** It carries
   citations; it is not a primary source. The generation prompt treats the
   baseline bundle as primary; research content may only *add* facts the
   bundle lacks, each traceable to a citation in the report.
2. **Never merge silently.** The augmented bundle is a new file with the
   research section explicitly delimited and declared; the baseline
   `{PROJECT}_preprocessed.txt` is never edited.
3. **Every report gets provenance**: provider, model, query text, run
   date, cache hit/miss, sha256 of the report — written beside the report.
4. **Conflicts route to `source_caveats`.** Where research contradicts the
   bundle, the record states both and cites both; it never silently
   prefers the research.
5. **Label the arm.** Any record generated from an augmented bundle uses a
   run label that names it (e.g. `..._research`) so it can never be
   mistaken for a baseline record.

## Workflow

1. **Extract research targets** from the project's bundle
   (`data/preprocessed/concatenated/{PROJECT}_preprocessed.txt`): dataset
   name and aliases, any DOIs, grant numbers, PI names, hosting platforms.

2. **Compose targeted queries** — one per gap class, grounded in the
   targets. The standard set:
   - "Publications and preprints that describe or use the {DATASET} dataset
     ({aliases}); give DOIs."
   - "Persistent identifiers, registry entries and repository records for
     {DATASET} (DOI, RRID, FAIRhub/PhysioNet/Zenodo entries)."
   - "The data use license or access agreement governing {DATASET}: name,
     version, terms, where published."
   - "Version history and release notes of {DATASET}: version numbers,
     dates, sizes, changes."
   - "IRB or ethics approvals of record for {DATASET} ({grant numbers}):
     institution, protocol number, consent model."
   - "Datasets related to {DATASET}: predecessors, subsets, companions."
   Skip queries whose answers the bundle already contains.

3. **Canary, then run.** One query first; verify the markdown report and
   cache entry exist and are non-empty. Then the rest, reusing
   `--cache-dir data/deep_research/cache` so re-runs are free.

4. **Save with provenance** under
   `data/deep_research/{PROJECT}/{YYYY-MM-DD}_{provider}/`:
   - `q{N}_{slug}.md` — the report as returned, citations intact
   - `provenance.yaml` — provider, model, date, per-query text, cache
     status, and sha256 per report

5. **Build the augmented bundle**
   `data/preprocessed/concatenated/{PROJECT}_preprocessed_with_research.txt`:
   the baseline bundle verbatim, then a delimited section per report:

   ```
   ================================================================
   SUPPLEMENTARY SOURCE (deep research; secondary evidence)
   Report: data/deep_research/{PROJECT}/{date}_{provider}/q1_publications.md
   Provider: {provider} | Generated: {date} | sha256: {hash}
   Claims below are citation-backed research findings, not primary
   documentation. Prefer the primary bundle on conflict; record
   conflicts in source_caveats.
   ================================================================
   {report content}
   ```

6. **Generate** with the API pipeline against the augmented bundle:

   ```bash
   poetry run d4d api run --project {PROJECT} --arm baseline \
     --condition generic_v3 \
     --bundle data/preprocessed/concatenated/{PROJECT}_preprocessed_with_research.txt \
     --label {date}_claude-opus-5-1m-generic-v3-research_rep1 --yes
   ```

   The label's `-research` suffix is the arm marker. Validate and collect
   telemetry as for any run (`d4d runs telemetry --label-prefix ...`).

7. **Assess the delta**: judge the research-armed record against the
   baseline-armed record of the same project (rubric agents), attributing
   score changes to specific research-supplied facts. The comparison —
   what deep research recovers that the bundle lacks, and whether the
   evidence chain survives — is the point of the experiment.
