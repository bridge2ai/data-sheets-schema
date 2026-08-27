Generate paired full D4D and D4D-core records for Bridge2AI Grand Challenge
projects using a model-neutral, schema-grounded agent workflow with four ordered
phases:

1. Generate the full D4D directly from the input documents.
2. Generate D4D-core from the same input documents plus the completed full D4D.
3. Audit both records against the current sources and provenance boundary.
4. Reconcile the full/core pair using schema-derived identity and consistency
   rules.

Phases 3 and 4 are required for production runs. Write a reconciliation report
even when no discrepancies are found. Run the requested phases for all four
projects (AI_READI, CHORUS, CM4AI, VOICE) unless the user names specific ones.

Before any phase, read and enforce
`.claude/agents/d4d-provenance-guard.md`.

Two execution modes are supported:

- **Independent mode:** one fresh agent context for Phase 1 and another for
  Phase 2, followed by orchestrator-controlled Phase 3 and Phase 4.
- **Four-phase project-agent mode:** one project agent runs full generation,
  core generation, source/provenance audit, and strict reconciliation
  sequentially. Phase 2 must still wait for a validated Phase 1 file and must
  read both declared inputs.

### Phase artifacts are snapshots; resume by artifact, not by memory

In independent mode each phase's on-disk artifact is its snapshot, exactly as
the API runner's progress file treats its phases. A relaunched run under the
**same version label** must skip any phase whose artifact already exists and
passes its validation commands, and record that under `phases_skipped` — the
same field the API path's resumed runs carry. Two rules make this safe:

- **Skip on validated artifact only.** An artifact that exists but fails
  validation is a phase that did not complete; re-run the phase rather than
  repairing the artifact in place, because a half-written file repaired by a
  later phase has no phase that attests it.
- **Never resume across labels.** An artifact under another label is another
  run's output; reading it is the prior-D4D leak the evidence boundary
  prohibits, whether or not the bytes would be identical.

## Arguments

- `$ARGUMENTS`: optional project name(s), and/or an output version label.
- Output version label: `{YYYY-MM-DD}_{provider-model-settings}` (for example,
  `2026-07-23_claude-opus-4.6-high` or
  `2026-07-23_gpt-5.6-sol-ultra-fast`). If not given, construct it from today's
  date and the selected model. All outputs for one run use the exact same label.
- Never overwrite a populated version directory, **with one exception**:
  resuming an incomplete run of the same label per the snapshots section above
  writes that run's remaining phases into its own directory — that is
  completion, not overwriting. A *complete* run is never resumed; for another
  run with the same date and model, append `-r2`, `-r3`, and so on.
- `-r{N}` means a **revision** (changed pipeline), not a replicate. For repeated
  samples of the *same* procedure, use `_rep{N}`; `d4d runs list` reports the two
  differently because runs that differ in procedure are not comparable as
  samples.

Header substitution fields used below:

| Field | Meaning |
|---|---|
| `{RUNTIME}` | what is executing — `Claude Code`, `Claude API (direct)`, `Codex CLI` |
| `{PROVIDER}` | `Anthropic`, `OpenAI`, or the proxy actually reached |
| `{MODEL}` | the model identifier the request carries |
| `{EFFORT}` | reasoning effort, where the runtime exposes one |
| `{MODE}` | `four-phase project agent` or `independent` |
| `{CONDITION}` | `generic` or `tuned` — see Prompt Conditions below |
| `{PROMPT_PATHS}` | the resolved prompt file(s) this run was launched with |
| `{METHOD}` | output method directory, e.g. `claudecode_agent` |

Substitute these; never leave a literal `{...}` in a written record, and never
carry over a value from a different runtime. Records once shipped headed
`Agent runtime: Claude Code` on `claude-opus-5[1m]` from a run that touched
neither, because a prompt written for one path was reused verbatim by another.

## Inputs (per project)

- Source documents: `data/preprocessed/concatenated/{PROJECT}_preprocessed.txt`
  (selected by `data/preprocessed/source_manifest.yaml`; run
  `make validate-preprocessing` first if inputs were re-downloaded)
- Full schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- Core schema: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)

### Scope: what the record is about

The bundle is the evidence. What the record is *about* is declared in the
`scope:` block of `data/preprocessed/source_manifest.yaml` — the referent, and
any dataset that is related to it but distinct from it, with the slot that
carries the relation. Read it with `d4d download scope --project {PROJECT}`.

**A scope constraint goes in the manifest, never in the launch text.** The VOICE
run of 2026-08-07 was sent a paragraph naming the project, the companion
pediatric dataset, a file not to read, and the issue number of the last time it
went wrong (#422). It worked, and it was per-GC adaptation invisible to every
prompt test, because it lived in the message rather than in a file. If a run
seems to need a constraint the bundle and the manifest cannot express, that is a
manifest bug — fix it there, where the next dataset inherits it.

A bundle may legitimately contain sources *about* a related dataset: VOICE's
does, and the manifest says so (`in_bundle: physionet_pediatric_1_1_0`).
Represent the relation through the declared slot — `related_datasets` — rather
than merging the two, and never as a nested object standing in for the other
dataset's own record. `d4d download scope --check` verifies afterwards that no
record identifies itself as a dataset its project declares distinct.

## Outputs (per project)

- Full: `data/d4d_concatenated/claudecode_agent/{VERSION}/{PROJECT}_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/{VERSION}/{PROJECT}_d4d_core.yaml`
- Required production reconciliation report:
  `data/d4d_concatenated/claudecode_agent_core/{VERSION}/{PROJECT}_reconciliation.md`

Never overwrite a previous version's directory; a new run gets a new `{VERSION}`.

## Factual Evidence Boundary

The current source bundle and manifest are the factual source of truth. Schema
files define structure, not dataset facts.

The schemas are the sole structural authority. Full structure comes from class
`Dataset` in `data_sheets_schema_all.yaml`; core structure comes from class
`CoreDataset` in `data_sheets_schema_core_all.yaml`. Resolve inherited slots,
class ranges, required fields, cardinality, inlining, `slot_usage`, and enums
from those schemas. No prior YAML or embedded documentation example may supply
or override structure.

- Phase 1 must not read any prior generated full or core D4D.
- Phase 2 may read only the exact Phase 1 full D4D from the same version label.
- Phase 2 must not read an older core, even as a template.
- Phase 3 may read only the current source bundle, manifest, schemas, and the
  same-run full/core pair.
- Phase 4 may read only the same Phase 3 inputs plus the Phase 3 audit findings
  for that exact pair.
- A fact found only in older generated YAML must be omitted.
- Historical source documents remain allowed when the current manifest
  explicitly selects them.

Before launching an agent, the orchestrator may inspect output directory names
only to choose a new version label. Do not put older D4D contents into an agent's
context.

### The one exception: derivation, which is not generation

The rules above govern **generation** — producing a record from source documents.
They exist to stop a fact with no evidence behind it migrating from an old record
into a new one, acquiring apparent support on the way.

A **derived** record is a different operation and the rules do not apply to it,
because the failure they prevent cannot occur:

- It consumes generated records *as its declared inputs*, not as a shortcut
  around evidence. Reading them is the operation, not a leak into it.
- It introduces no new facts. Every value in a derived record was already in a
  contributing record; a merge selects and combines, it never asserts.
- Its provenance says so. `record_mode: derived` names every contributing record
  by md5 and states the rule that combined them, so what it consumed is
  checkable rather than hidden — which is exactly what the boundary above is
  protecting.

Conditions, all of which must hold:

1. **A generation phase may never derive.** Phases 1–4 remain bound by the rules
   above without exception. Derivation runs after a set of complete runs exists,
   as a separate operation with its own method directory.
2. **Only complete, attested runs may contribute.** A partially-attested run
   cannot be placed, so combining it would produce a record whose inputs cannot
   be established. See `attestation()` in `runs.py`.
3. **The output is written under a distinct method**, never into a contributing
   run's directory, so a derived record can never be mistaken for a generated
   one or re-consumed as if it were.
4. **A derived record may not contribute to another derived record.** Chained
   merges make the source md5s an incomplete account of what the content came
   from, and the provenance stops being checkable in one step.
5. **A derived record is not a replicate.** It must not enter agreement or noise
   figures: it is an order statistic over the runs being measured, so including
   it would bias the very variance it was built from.

Anything that does not meet all five is generation, and is bound by the rules
above.

## Prompt Conditions and Priming

Every run belongs to exactly one prompt condition, and the record must say which.
Conditions come in two families, and the **generic** family has several
versions. `d4d api prompts check` lists the registered prompt files, and
`CONDITION_PROMPTS` in `src/data_sheets_schema/api_runner.py` is the registry
they are derived from — read it rather than trusting a list written here, which
is how this section came to claim only two conditions existed long after
`generic_v2` through `generic_v5` were registered (#603).

- **generic**, currently `generic` (v1) through `generic_v5`. Every project and
  every arm receives *the exact text of that version*; only mechanical fields
  are substituted (project, arm, method, bundle, label, runtime, provider,
  model). Nothing in any of them is specific to a project, dataset, or input
  set. Each version is its predecessor plus one marked block, so a run must
  name **which** version it used.
- **tuned** — `src/download/prompts/d4d_tuned_arm_prompt.md` plus the project's
  component file in `src/download/prompts/components/{PROJECT}.md`. Carries
  project-specific and input-set-specific content deliberately.

The difference between generic and tuned is what the prompt-condition study
measures, so **adding a project-specific sentence to any generic version
silently creates a new condition and destroys the comparison.**

### The priming taxonomy

Four kinds of statement can be added to a generation prompt. They are not
equivalent, and only the first two are ever acceptable:

| kind | example | generic | tuned |
|---|---|---|---|
| **decision rule** | "prefer omission over inference" | ✅ if applied to every project identically | ✅ |
| **factual disambiguation** | "this bundle describes a release programme, not one release" | ❌ project-specific | ✅ |
| **quality warning** | "earlier runs conflated two entities here" | ❌ | ⚠️ steers behaviour; avoid |
| **outcome expectation** | "expect roughly 60 populated slots" | ❌ | ❌ **never, in any condition** |

Outcome expectations are excluded from *both* conditions. They tell the model
what answer to produce rather than what the evidence is, so a record generated
under one cannot be read as evidence about the evidence.

`-deprimed` is **not** a third supported condition. It names the 2026-07-28
series that removed outcome expectations but retained per-project factual notes,
making it neither generic nor tuned. Those runs are retained under that label for
the record; do not create new ones.

### Uniform decision rules (all conditions, all projects)

**Read `.claude/commands/d4d-uniform-rules.md` and enforce every rule in it.**
It is the single copy; this section deliberately does not restate them, because
a second copy is what #563 was filed about.

### Recording the condition

Both file headers carry a `# Mode:` line naming the condition and a `# Prompt:`
line naming the resolved prompt file(s) — see the header blocks below. A record
that does not name its prompt condition cannot be placed in the study, and a run
launched without one of the registered prompt files is neither condition; say
so in the provenance `notes` rather than picking a label.

## Runtime Cases

### Claude Code

- Use fresh Task/subagent contexts.
- Either launch one project agent that performs all four phases sequentially,
  or launch fresh phase agents with exact-path handoff.
- Explicitly tell each agent that prior D4D content from the parent conversation
  is forbidden evidence.
- Record `Agent runtime: Claude Code`, `Provider: Anthropic`, and the exact model.

### Codex / GPT

The following launch instruction is for the outer orchestrator only. A worker
already running in the fresh Codex context must execute its assigned phases
directly and must not recursively invoke `codex`.

Before launching, resolve the exact model slug, supported reasoning effort, and
speed tier from the installed Codex model catalog. Preserve the user's requested
labels when the catalog supports them; do not silently map `ultra` to another
effort. Set `MODEL` and `EFFORT` to those exact values, then invoke each
generation pass with:

```bash
MODEL="gpt-5.6-sol"
EFFORT="ultra"

codex -a never exec -m "$MODEL" \
  -c "model_reasoning_effort=\"$EFFORT\"" \
  -c 'service_tier="priority"' \
  --enable fast_mode \
  -s workspace-write -C "$PWD" "<PASS-SPECIFIC PROMPT>"
```

The values above are the GPT-5.6-Sol ultra-fast profile used on 2026-07-23.
For another run, replace them only with values reported as supported by the
current local model catalog. Omit `service_tier="priority"` and `fast_mode`
unless the selected model supports the fast tier.

For independent mode, use one fresh `codex exec` invocation per project per
generation phase and run the two audits with exact-path handoff. For four-phase
project-agent mode, use one invocation per project and enforce explicit phase
gates. In either mode, Phase 2 must begin only after Phase 1 has produced and
validated the full YAML.

The prompt must name the exact allowed paths and state:

> Do not search or read any prior D4D output. The only generated YAML you may
> read is the exact same-run full/core path allowed for the current phase.

Record `Agent runtime: Codex CLI`, `Provider: OpenAI`, the exact model,
reasoning effort, and mode.

## Phase 1 - Full D4D from input documents

**Read the whole declared bundle before extracting anything.** The API path
has every byte of the bundle in context on every call; this path reads it
through a file tool, and the 2026-08-24 arm's agents read AI_READI, CM4AI
and VOICE piecewise and never opened roughly a fifth of each (#700). A slot
whose evidence sits in an unread window is recorded as absent,
indistinguishable from "the bundle does not support it". So:

1. count the bundle's lines (`wc -l`), then read it sequentially in
   consecutive `offset`/`limit` windows until every line has been read
   once — no gaps, no reliance on search to fill them;
2. **size windows by tokens, not lines.** The tool refuses any single read
   over ~25,000 tokens and returns nothing; in that arm 17 bundle reads
   failed this way and the lines they covered were never re-read. For these
   bundles ~400–500 lines per window is safe. **A read that errors counts as
   unread**: re-read that range in smaller windows before moving on;
3. only then extract. Search (`grep`) is for *re-finding* a passage you have
   already read, never a substitute for reading it;
4. the launcher records how much you actually read (`bundle_lines_read` in
   `run_observed`, from your transcript, counting successful reads only), so
   an unread window is visible in the record rather than silently absent.

Follow the method in `.claude/commands/d4d-agent.md` (read it first). Summary of the
non-negotiables:

1. Derive and constrain structure directly from class `Dataset` in the full
   schema. Follow inherited slots, class ranges, required fields, cardinality,
   inlining, `slot_usage`, and enums. Do not read a prior D4D example or assume
   a nested-object shape.
2. Extract exact field names from the schema; `d4d:docExample` annotations are
   illustrations, not defaults — every value must come from the source documents.
3. Extract per the checklist in `d4d-agent.md` (identity, creators, purpose, tasks,
   composition, collection, preprocessing, distribution, licensing, maintenance,
   access, funding, ethics, uses, limitations).
4. Validate (NON-SKIPPABLE, fix and re-run until clean):
   ```bash
   poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full_file>
   poetry run linkml-term-validator validate-data <full_file> \
     --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
     --target-class Dataset
   ```

File header:
```yaml
# D4D Datasheet for {PROJECT} Dataset
# Generation Method: schema-grounded agentic, phase 1
# Agent runtime: {RUNTIME}
# Provider: {PROVIDER}
# Model: {MODEL}
# Reasoning effort: {EFFORT}
# Mode: {MODE}, {CONDITION} prompt
# Prompt: {PROMPT_PATHS}
# Source bundle: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt
# Source manifest: data/preprocessed/source_manifest.yaml
# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
# Prior D4D factual reuse: prohibited
# Temperature: 0.0
# Generated: {DATE}
```

In independent mode, the Phase 1 agent writes only the full YAML. It must not
create a core record.

## Phase 2 - D4D-core derived from the full D4D

**The core is derived, not generated (#694).** `CoreDataset` is a subset of
`Dataset`; on the 2026-08-24 arm a deterministic projection reproduced 98.5%
of every generated core's slot values and the rest was the two core-only
slots. Generating it was where the API arm's pair errors came from. So Phase
2 is one command, run on the validated Phase 1 file:

```bash
poetry run d4d derive core \
  --full data/d4d_concatenated/claudecode_agent/{VERSION}/{PROJECT}_d4d.yaml \
  --out  data/d4d_concatenated/claudecode_agent_core/{VERSION}/{PROJECT}_d4d_core.yaml
```

It copies every schema-identical shared slot, projects `resources` by id,
builds `distributions` from `file_collections` over the slots the two classes
share, leaves `dialect` absent (it has no full-record source), writes the
core header from the full record's, and validates the result. A derived core
that fails validation means the *full* record carries a shape the core schema
rejects — fix the full record and re-derive; never edit the core by hand,
because Phase 4 will re-derive it anyway. Record the phase as `derive_core`.
Print the JSON the command emits into the reconciliation report; the
provenance recorder needs nothing else, the API path records the same facts
under `core_derivation`.

**Where the pinned condition text says otherwise, derivation wins.** The
generic ≤ v5 prompts predate #694: they describe "Phase 2 core generation"
and mandate a CORE HEADER BLOCK reading `schema-grounded agentic, phase 2`
with `Sources: {bundle} + {full}`. Under those conditions the derived
header (`derived by projection from the full record (#694)`,
`Sources: {full}`) supersedes that block — a header claiming a generation
that did not happen would be the false attestation this playbook exists to
prevent — and the run records it under `derive_core`. generic-v6 carries the
derived wording in its own text.

This is not the derivation the evidence boundary forbids. That rule
(*"A generation phase may never derive"*, above) is about consuming *other
runs'* records; a core projected from this run's own audited full record
consumes nothing the run did not itself generate from the declared bundle.

Anything the bundle supports that the full record lacks is added **to the
full record** in Phase 3's back-port, and the core inherits it on
re-derivation. That is where the former Phase 2 instruction "consult the
source documents to fill core fields the full record left empty" now lives;
a core field can no longer be filled by any path the full record's evidence
trail does not cover.

The rules below describe the generated core this phase replaced; they remain
the specification a derived core satisfies by construction, and they still
govern a run that for a stated reason cannot derive.

Inputs to this phase: the current source documents AND the exact same-run Phase
1 full D4D. No older full or core YAML is permitted. The core record is the
semantic exchange layer subset (CoreDataset, ~79 fields), not a fresh
independent extraction:

1. Read `src/data_sheets_schema/schema/D4D_Core.yaml` and the merged core schema
   to derive the exact `CoreDataset` field inventory and every nested class
   shape. Follow inherited slots, ranges, cardinality, inlining, `slot_usage`,
   and enums rather than copying a full-record structure mechanically.
2. For every core field that also exists in the full D4D, START from the full D4D's
   value. Consult the source documents to (a) fill core fields the full record left
   empty, and (b) catch anything the full extraction missed. If the documents
   support a value that is missing or different in the full D4D, use the source
   documents as ground truth and report the discrepancy for Phase 3.
3. Do not include facts in core that are absent from both the full D4D and the
   source documents.
4. Do not inspect an older core for field selection, wording, IDs, or values.
   Derive core structure from `D4D_Core.yaml`.
5. Validate (NON-SKIPPABLE):
   ```bash
   poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core_file>
   poetry run linkml-term-validator validate-data <core_file> \
     --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
     --target-class CoreDataset
   ```

File header:
```yaml
# D4D Core Datasheet for {PROJECT} Dataset
# Generation Method: schema-grounded agentic, phase 2
# Agent runtime: {RUNTIME}
# Provider: {PROVIDER}
# Schema: D4D Core (CoreDataset class), semantic exchange layer subset
# Schema path: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
# Model: {MODEL}
# Reasoning effort: {EFFORT}
# Mode: {MODE}, {CONDITION} prompt
# Prompt: {PROMPT_PATHS}
# Sources: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt + {full D4D path}
# Source manifest: data/preprocessed/source_manifest.yaml
# Prior D4D factual reuse: prohibited
# Temperature: 0.0
# Generated: {DATE}
```

In independent mode, the Phase 2 agent writes only the core YAML. It must not
rewrite the full YAML.

## Phase 3 - Source and provenance audit

Phase 3 establishes the canonical factual content before mechanical
reconciliation. It is not allowed to prefer a value merely because it appears
in either generated record.

1. Re-run schema and term validation for both outputs.
2. Confirm from the agent's read history that no prior-run D4D, evaluation, or
   reconciliation report was used.
3. Check both records against the current source bundle and manifest:
   - resolve source disagreements using authority, version, date, and scope;
   - identify unsupported, stale, omitted, or mis-scoped assertions;
   - verify repeated identifiers, versions, dates, counts, licenses, access
     rules, people, and organizations are internally consistent in each file;
   - keep historical values only when their historical scope is explicit;
   - audit shape as well as evidence (same contract as the API pipeline's
     audit phase): flag any value whose shape does not conform to the
     schema — prose where the schema requires a list, enum values the
     schema does not define, commentary embedded inside a name, identifier
     or affiliation value — and any slot-filling violation: structured
     slots left empty while their content sits in prose, narrative in
     `notes` that belongs in `description`, sibling values restated in
     `notes`, or evidence commentary outside `source_caveats`.
4. Back-port every source-supported Phase 2 discovery into the full record in
   the correct full-schema slot. Correct the full record first whenever the
   source audit changes a fact.
5. Apply the same corrected facts to core where its schema permits them, but do
   not shorten or paraphrase shared values in preparation for Phase 4.
6. Re-validate both files after every correction and record the source and
   provenance findings for the reconciliation report.

## Phase 4 - Strict full/core reconciliation

Phase 4 makes the Phase 3-audited full record canonical for every schema-
identical slot and proves consistency across the pair.

1. Derive the shared slots at runtime from `Dataset` and `CoreDataset` with
   LinkML `SchemaView`. Do not maintain a hand-written field list.
2. For every shared slot with the same induced range and cardinality:
   - it must be present in both records or absent from both;
   - its parsed YAML value must be deeply identical, including every nested
     mapping value and list item in the same order;
   - this rule includes narrative fields. Core must not condense, paraphrase,
     reorder, or omit shared content.
3. Handle shared slots whose schema ranges differ as explicit projections.
   `resources` is `Dataset` in full and `CoreDataset` in core: match resources
   by `id`, require equal coverage, and require deep identity for every nested
   schema-identical slot. Full-only nested slots are omitted from the core
   projection.
4. Reconcile related, non-identical representations semantically:
   - map full `file_collections` to core `distributions` and verify names,
     descriptions, paths, formats, compression, checksums, byte counts, access
     URLs, and release scope do not conflict;
   - compare `total_file_count` and `total_size_bytes` with distribution-level
     values when the represented scopes are the same;
   - check `dialect`, formats, and `is_tabular` agree;
   - check top-level identity/version/access facts agree with resources,
     version history, distributions, and repeated statements;
   - distinguish a historical release from a current release rather than
     treating their different values as a contradiction.
5. **Re-derive the core from the corrected full record** (Phase 2's command
   again, now with `--phase4-complete`, which writes the
   `# Phase 4 reconciliation: completed` header line the condition text
   mandates) after every Phase 3/4 correction to the full — the core is a
   function of the full and is never edited on its own. `--sync-core` is
   superseded by derivation and should not be needed; if it changes
   anything, the derivation is wrong and that is a bug to report, not a
   record to fix. Then run the pair checker as the final independent check:
   ```bash
   poetry run python -m data_sheets_schema.d4d_pair_consistency \
     --full <full_file> --core <core_file>
   ```
   Validator warnings mark related content that still requires the semantic
   review in step 4; warnings are not evidence that review occurred.
6. **Check the identifiers against the bundle, and the report against the
   record.** The API path runs both automatically at the end of every run; this
   path ran neither, so the arm that reads the rules was the arm that did not
   verify them (#563).
   ```bash
   poetry run python -c "
   from pathlib import Path
   from data_sheets_schema.grounding import check_run
   from data_sheets_schema.identifiers import uriorcurie_slots
   r = check_run(Path('<full_file>'), Path('<core_file>'), Path('<bundle>'),
                 uriorcurie_slots())
   if not r.get('checked'):
       print('NOT CHECKED:', r['reason'])
   else:
       print(r['distinct'])
       for f in {(x['kind'], x['identifier']) for x in r['findings']}:
           print(*f)"
   ```
   Any identifier reported `absent` is one this record states and the bundle
   does not (#547). Correct it or remove it — a correct identifier the evidence
   does not contain is still an unsupported claim. `minted_fragment` is fine:
   the base is attested and the fragment is ours.

   After writing the reconciliation report in step 8, check its claims against
   the record you actually produced:
   ```bash
   poetry run python -c "
   from pathlib import Path
   from data_sheets_schema.report_claims import check_report, declared_slots
   import yaml
   full = yaml.safe_load(Path('<full_file>').read_text())
   core = yaml.safe_load(Path('<core_file>').read_text())
   out = check_report(Path('<report_file>'), full, core, declared_slots())
   [print(f) for f in out['findings']]"
   ```
   Findings are printed once per identifier, not once per slot that repeats
   it: VOICE rep1 has 19 ungrounded identifiers across 78 occurrences, and the
   number to act on is 19.

   `removal_not_performed` means the report says a slot was removed and it is
   still there; `false_schema_claim` means the report says a slot is not
   declared and it is. Both are decidable, and in the 2026-08-13 API arm every
   record that emitted a `distributions` block claimed to have removed it (#546).
7. Re-run schema and term validation for both records.
8. Write `{PROJECT}_reconciliation.md` with separate Phase 3 and Phase 4
   sections: source/provenance findings, schema-derived shared-slot count,
   corrections, related-content mapping and review, files changed, all commands,
   and final results. If nothing diverged, say so explicitly.

   **Two sections have a fixed shape.** The report-claims checker
   (`d4d provenance backfill-checks`; #546) parses exactly two claim forms,
   and a report written in free prose registers zero claims — its "0
   findings" is then unmeasured, not clean (#684; 11 of 12 reports in the
   2026-08-24 arm). Write:

   - `## Claims` — one markdown table row per slot you removed from either
     record, the slot name in backticks in the first cell and the word
     **Removed** in the second: `| \`distributions\` | Removed | not declared on CoreDataset |`.
     The checker counts each such row and tests it (`removal_not_performed`
     if the slot is still there). Where you assert that a slot is not
     declared in the schema, say it in an `**Action:**` line naming the slot
     in backticks; the checker tests the assertion against the schema
     (`false_schema_claim` when the slot *is* declared) — note this scan
     does not add to `claims_checked`. If you removed nothing, write the
     single line `No slots were removed.` — **the checker does not yet read
     that sentinel** (#684 tracks it), so such a report still shows
     `claims_checked: 0`; write it anyway so the count is measured the day
     the checker learns it.
   - `## Semantic review` — one line per `semantic-review-required` warning
     the pair checker emitted (related-content pairs such as
     `file_collections` ↔ `distributions`), each ending in **reviewed:
     consistent** or **reviewed: corrected** with what changed. The warning
     is the checker saying the review is required; this section is the only
     evidence it happened (#691). No checker reads this section yet; it is
     for the human reviewer and for the parser #691 proposes. If the checker
     emitted no warnings, say so.

9. **Repair, then re-report — the API pipeline's closing loop, which this path
   previously lacked.** If step 6's checkers (grounding, report claims) or the
   final pair-consistency run reported findings that require changing either
   record: fix both records in one pass (`repair`, recorded as its own phase
   with `iterations` counting the fix-validate loops), re-run every validation
   from steps 5–7, and **rewrite the reconciliation report** so it describes
   the bytes that exist (`report_after_repair`). The API pipeline regenerates
   its report for the same reason (#604): a report describing bytes that no
   longer exist is the artifact a reviewer reads instead of the diff. If no
   finding required a change, there is no repair phase — do not record an
   empty one.

In independent mode, the orchestrator may perform Phases 3 and 4 without another
model invocation, but it must perform the same source review, deterministic
validation, semantic related-content review, and reporting.

## Provenance record (required, per project)

After Phase 4 validates, emit a machine-readable provenance record:

```bash
poetry run d4d provenance record \
  --project {PROJECT} --method {METHOD} --label {VERSION} \
  --input-bundle {EXACT INPUT BUNDLE PATH} \
  --prompt {EACH PROMPT FILE THE RUN CONSUMED} \
  --prompt-text {THE INSTRUCTION AS SENT} \
  --reasoning-effort {EFFORT, ONLY IF YOU KNOW IT} \
  --phase '{"name":"generate_full","completed":true,"artifacts":["{PROJECT}_d4d.yaml"],"observed":{"total_tokens":{TOTAL},"tool_uses":{COUNT},"duration_ms":{MS}}}' \
  --phase '{"name":"derive_core","completed":true,"artifacts":["{PROJECT}_d4d_core.yaml"]}' \
  --phase '{"name":"source_audit","completed":true}' \
  --phase '{"name":"reconcile","completed":true,"iterations":{HOW MANY TIMES YOU RAN VALIDATE-AND-ITERATE}}' \
  --phase '{"name":"report","completed":true,"artifacts":["{PROJECT}_reconciliation.md"]}' \
  --phase '{"name":"repair","completed":true,"iterations":{FIX-VALIDATE LOOPS}}' \
  --phase '{"name":"report_after_repair","completed":true}' \
  --phase-skipped {EACH PHASE A RESUME SKIPPED, IF ANY}
```

**Pass one `--phase` per phase you actually performed, in order.** The API path
records eight `api_usage` entries per run; this path recorded nothing, so its
phase structure existed only as prose in the reconciliation report — and #546
showed a report is not a reliable account of what happened. Every comparison
between the two arms was one-sided as a result (#562).

Record what you did, not what this file describes. A phase you performed is
listed with `--phase`; a phase a **resume** skipped because its validated
artifact already existed is listed with `--phase-skipped` (never both for one
phase); a phase that did not complete gets `"completed": false`. `iterations`
belongs only on a phase that actually loops — writing `1` on a phase that
cannot iterate implies the number was measured. `report` attests the
reconciliation report step 8 always writes. The `repair` and
`report_after_repair` phases exist only when Phase 4 step 9 actually ran a
repair; a run with no findings records neither.

**Token accounting has two different speakers, and only one may speak.** The
phase agent itself has no access to its own accounting (#400) and must not
estimate timing or tokens — that rule is unchanged. But an **orchestrator that
launched a phase as a subagent observes aggregate totals when it completes**
(total tokens, tool uses, wall duration), and may record what it observed by
adding an `"observed": {...}` block to that phase. Only phases the orchestrator
actually observed get one; a phase run inside a shared context has no
observable boundary and gets none. The block is deliberately not shaped like
`api_usage` — no input/output split, no per-call timing — so the two arms'
accounting can never be silently averaged. The recorder refuses `api_usage`
field names (`input_tokens`, `seconds`, …) inside a phase for the same reason.
**In four-phase project-agent mode there is no per-phase boundary to observe**
— the condition text mandates that mode, and one subagent runs all phases —
so record no per-phase `observed` blocks there; after the run has written its
own record, the orchestrator adds the whole-run totals it observed with

```bash
poetry run python scripts/agentic_observed.py --bundle {EXACT INPUT BUNDLE PATH} \
  {EVERY TRANSCRIPT FILE FOR THIS RUN, INCLUDING A KILLED FIRST INVOCATION}
d4d provenance annotate-observed --project {PROJECT} --method {METHOD} \
  --label {VERSION} --run '{THE JSON THE SCRIPT PRINTED}'
```

which is the one boundary that exists. The script sums token usage, tool
uses and wall duration across the transcripts and computes
`bundle_lines_read` / `bundle_lines_total` — the union of the run's
file-reading windows over the declared bundle (#700). Transcripts live under
the runner's config directory, which differs by account (`~/.claude` or
`~/.claude-work`); pass every invocation's transcript, or the total is the
killed run's (#688). Annotate once: a second annotation with different
values is refused, because an observation silently replaced is a measurement
dropped without trace.

`d4d provenance record` now writes the four deterministic check blocks
(pair consistency, report claims, grounding, form) into the record itself
(#687); `backfill-checks --execute` remains the repair route if that step
reports it could not compute them, and the only route for records
reconstructed by `d4d provenance backfill`, which does not compute them.
Reasoning capture remains impossible on this path either way
(`runtime_cannot_capture`): total spend is now measurable, the reasoning share
of it is not.

Writes `{METHOD}_core/{VERSION}/{PROJECT}_provenance.yaml` capturing schema
md5s, model and runtime identity, input bundle hash, repo commit, software
versions, hardware, output hashes and slot counts.

This is a **live** record: every field is observed at run time. It fails loudly
if the input bundle is unreadable, because a run that cannot identify its own
input has not produced reproducible output. Do not substitute a reconstructed
record — `d4d provenance backfill` exists only for runs that predate this step,
and it marks what it cannot recover rather than filling it in.

**Reasoning effort is established by the recorder, not by the header** (#397).
Where the model route carries it — the provider exposes effort as a model-name
suffix — it is read from there and marked observed. Where it does not, pass
`--reasoning-effort` *only if you actually know what the run was launched at*;
it is then recorded as asserted by the launcher. If you do not know, omit it:
the recorder writes no value and names the gap, which is the honest outcome.
**Never write "default", "n/a", "unspecified" or a guess** — a run that did not
choose an effort is a different claim from a run whose effort is unknown, and
neither is a run at high. Do not add a `# Reasoning effort:` line to the header
unless the prompt's header block asks for one; the header is defined by the
prompt condition, and adding to it by hand is the intervention this playbook
exists to prevent.

**The prompt is an input like the bundle.** `--prompt` may repeat; pass every
file the condition is built from. `--prompt-text` takes the instruction as
actually sent — render it with

```bash
d4d prompt render --project {PROJECT} --label {LABEL} \
                  --condition {CONDITION} --runtime 'Claude Code' --out <file>
```

rather than retyping it, so the text and its hash come from the same place.

`d4d prompt render` is the same command as `d4d api render-prompt` (#428). The
top-level spelling exists because this path is not the API path, and a launcher
following this playbook has no reason to look under a group named for the
runtime it is not using. From 2026-08-10 a run without a recorded instruction fails
`d4d runs check --strict` (#419): the gate was otherwise opt-in by omission,
since a launcher that simply passes neither flag records nothing and nothing
says so.

Recording the file is not the same as vouching for it. A paragraph edited into
a prompt file *before* rendering re-renders to itself, so the render gate
reports `match` about an instruction nobody published (#432). What catches that
is the canonical pin: `d4d api prompts check` compares each condition's prompt
against the hash this repo declared for it, and `d4d runs check` compares the
hash in the record. If either reports `uncanonical`, the run was made under
text that is not a published version of its condition — say so in the
reconciliation report rather than pinning the edit to make the check pass.

## Completion criteria (per project)

- Both YAML files pass their schema and term validations.
- Every emitted structure is derived from and permitted by its applicable
  schema.
- Every schema-identical shared slot has deeply identical parsed YAML content
  and identical presence in full and core.
- Every projected or semantically related field has been mapped and reviewed
  with zero unresolved contradictions within or between the two records.
- The core file header names both its source-document bundle and full YAML input.
- Both headers state that prior D4D factual reuse is prohibited.
- The provenance audit confirms that no older full/core YAML was used.
- `d4d download scope --check --project {PROJECT}` reports the record in
  scope: it does not identify itself as a dataset the manifest declares
  distinct from this project.
- The core header contains `Phase 4 reconciliation: completed`.
- The Phase 3/4 reconciliation report is present.
- The live provenance record is present and its `record_mode` is `live`, and it
  names both the prompt files and the instruction as sent.
- `d4d runs check --strict` passes for the run. **Recording provenance is not the
  same as recording it correctly.** This path writes provenance as a step
  separate from writing the artifacts, so a record can pin a state the files
  merely passed through — one reconciliation report was hashed before its
  closing rows were appended, and a whole series was hashed before its headers
  were edited. The API path cannot do this, because it writes provenance
  in-process after every phase; running the check gives this path the same
  property.

  **Re-recording no longer discards the verdict** (#396). `provenance record`
  used to rewrite the file from scratch and delete the `validation:` block that
  `d4d runs validate` had written, so a re-record silently failed the gate while
  printing a tick. It now carries the block forward when every artifact it names
  still hashes to what it recorded, and drops it with a warning naming the
  follow-up command when one does not. So the sequence is no longer
  order-critical: record and validate in either order, and re-record freely.
  Still run `d4d runs validate` once after the artifacts are final, because a
  run that has never been validated has no verdict to carry.
- Final summary to the user: per project, report full/core line counts as
  informational metadata, never as a quality gate, plus validation status.

## Settings

- Temperature: 0.0; values only from current allowed sources; prefer
  null/omission for unknowns.
- Phase 1 projects may run in parallel. Phase 2 projects may run in parallel only
  after all required full records exist. Never overlap phases for the same project.
- Four-phase project agents may run in parallel with each other, but each agent
  must execute its own four phases sequentially.
