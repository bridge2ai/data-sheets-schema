# Repository operating guide

Operating guidance v2, 2026-10-12 (#5017, #3863). This LinkML project represents
Datasheets for Datasets and includes generation, evaluation and provenance tools.
This is the current coding guide, not a generation prompt or study registration.
The [historical instruction archive](docs/agent-instructions-history/README.md)
preserves the prior guide byte-for-byte; open only the topic needed for a task.
Old counts, timings, routes and commands there are historical observations.

## Start with the task and preserve existing work

- Identify the affected checkout, current changes, task contract and owner before
  editing. Preserve other contributors' changes, branches, worktrees and evidence.
- Use an isolated worktree outside the repository for independent changes. Do not
  create scratch worktrees under `notes/`, where preservation checks inspect them.
- Never switch branches in a checkout with a live API sweep or agentic run.
  Use `d4d api status` for sweeps; a process-name search does not establish absence.
  Stop only the authorized run with `d4d api stop --label-prefix <prefix>`.
  Preserve stale locks as evidence; do not remove them to force another launch.
- Keep historical records, transcripts, receipts, registered prompts, schema
  releases and human judgments. A failed or superseded result is still evidence.
  A code change does not authorize a provider campaign, rescore, release or cleanup.
- Continue to honor explicit user holds, required reviews, protected worktrees,
  scientific approvals and publication constraints. This guide does not waive them.

## Environment and commands

Run development commands from the repository root in the selected environment.
Use the project's `pyproject.toml` and `poetry.lock`; record the interpreter and
dependency identity when comparing timings or reproducing a failure.

```bash
poetry install                         # dependency bootstrap; installs d4d
git submodule update --init fairscape_models  # required for full test collection
poetry run d4d --help                   # inspect the actual CLI
poetry run python -m pytest tests/test_example.py -q -p no:cacheprovider
make lint-modules test-modules          # early schema feedback when relevant
make test                              # schema + Python + example checks
```

Replace `tests/test_example.py` with the actual affected file or node ID.
**Do not use `make setup` as dependency bootstrap.** It generates project/example
and documentation files, stages paths and commits via `git-init-add`. `make install`
also runs `git init`; `poetry install` is the ordinary existing-checkout route.
Deployment and provider-running commands require the task's actual authorization.

## Source and generated files

- Edit schema sources in `src/data_sheets_schema/schema/`, not a `modules/`
  subdirectory. Modules import `D4D_Base_import.yaml`; prefer its base classes.
- Do not hand-edit `src/data_sheets_schema/datamodel/`, `project/`, or the merged
  `data_sheets_schema_all.yaml` and `data_sheets_schema_core_all.yaml` products.
- After schema edits, run `make regen-all`, then rebuild the core merged schema
  with `rm -f src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml && make gen-core-schema`;
  `regen-all` does not rebuild that product. Inspect the generated diff.
- Check `make check-sync` and `make check-digest`. Bump full/core release versions
  together for class, slot or enum changes; register changed merged-schema hashes
  in `src/data_sheets_schema/schema/release_history.yaml` in the same commit.
- Regenerate both comprehensive SSSOM tables when slots, owning classes,
  descriptions or mappings change: `make gen-sssom-comprehensive gen-sssom-uri-comprehensive`.
  `make check-sssom-comprehensive` checks without writing. Preserve old releases
  and checked report blocks; never restamp history as if it used new schema bytes.
- Keep generation schema imports neutral: no study facts or study-specific
  examples in model-facing fields. Schema namespace URIs and prefixes identify
  the schema itself. See `tests/test_neutral_generation_schema.py`.
- Use `null`/`None` for missing schema/Python values. Renderers may display these
  as empty strings; do not change the stored meaning to match the display.

## Search, iterate and validate

- Start with explicit code/test paths and bounded `rg` output. Search retained
  evidence separately. Do not send whole directory inventories into context.
- An absence claim requires ignored and hidden files: use `rg --hidden --no-ignore`
  in the stated relevant scope. Say what was searched; ordinary `rg` is not enough
  before declaring a file/reference absent or proposing deletion/deduplication.
- Save result-producing helper scripts in `scripts/adhoc/`, with purpose, inputs,
  outputs, issue/PR and date. Commit them with their results; keep intermediate
  data outside protected trees. Do not leave helper provenance only in `/tmp`.
- Run affected tests during iteration, then the required complete acceptance
  checks. Use explicit test paths: bare pytest can discover dated tests in `notes/`.
  Preserve notes/ and input files, including ignored paths; use external temporary
  outputs and a bytecode location outside protected trees where needed.
- Coordinate one shared worker budget across active sessions. Start focused runs
  serially; use bounded xdist only when it fits that budget. Nested pytest creates
  additional controllers/workers. Do not kill another owner's process for capacity.
- Keep comparative benchmarks serial in a known environment with recorded host
  load. Frozen source review can run in parallel when it cannot mutate measured inputs.
- Maintain one acceptance ledger: scope, deliberate limits, current source/test/
  environment identity, owners, unresolved defects and the next decisive check.
  Review deltas; reuse unchanged evidence only while its inputs and validity hold.
  A new behavior request is different from a violation of the accepted contract.
- Preserve required adversarial/plugin review and scientific gates. Focused green
  tests do not replace final checks. After new failures or changed inputs, repeat
  affected checks; avoid rerunning an unchanged complete gate without a reason.
- `make test` already includes `test-schema`; do not prescribe both in sequence
  as separate final gates. An early `make test-schema` is optional feedback, not
  a substitute for the later full check on final bytes.

## Current CI contract

[main.yaml](.github/workflows/main.yaml) and [CI partitioning](utils/ci_sharding.md)
define the executable policy. Pull requests run the complete collected `tests/`
suite **including corpus checks**, on six Python 3.12 shards. Main/manual runs
use four Python 3.12 shards. Each shard uses at most four xdist workers.
All events also run separate complete offline canary, audit/finalization and
evaluation jobs. Main/manual runs additionally build schema products and examples
in a separate checkout. The aggregate `test` check requires every applicable job.

Package metadata permits Python 3.9 and newer; this CI matrix alone establishes
no compatibility result on other interpreters. A `corpus` marker describes a
test's evidence scope, not permission to omit it from PRs. Mark whole-corpus
checks accurately and retain fixture checks in their appropriate scope.
Timing weights schedule the actual collection; they are never a test allowlist.
Keep release/install canaries and documentation/publication gates when applicable.

## Generation and scientific boundaries

- Read the exact selected playbook and provenance guard before generation. Use
  fresh generation contexts and current source documents, not facts copied from
  older generated YAML. Keep full/core derivation, audit, reconciliation and
  required receipts/checks; phase order and resume authority belong to that protocol.
- The selected source manifest is the project registry. Scope, source ranking,
  dataset relationships and naming belong there, not in launch-text adaptations.
  A run consults its selected manifest or explicitly none; chunk manifests must
  match the actual bundle bytes and recorded rule before receipt-dependent spend.
- Study defaults belong in the `bridge2ai` profile; `neutral` carries none.
  Resolve and record one profile per run; never infer it from a project name.
  Preserve `profile_basis` vocabulary, including `stated by the caller`,
  `rendered instruction`, `could not select one`, and `backfill-spec` recovery.
- Resolve resources at read time using the existing resource readers. An
  authoritative missing file must not fall back to another checkout's copy.
  `chunking.anchored` follows the resource
root; corpus data stays with the caller's selected tree.
- Prefer `schema_cache.load_yaml` for schema/provenance reads; preserve its copy
  and invalidation contract. Read-after-write verification must observe new bytes,
  not a stale cache. Do not cache away fresh evidence or validation requirements.
- Prompt files are pinned in `src/download/prompts/canonical_hashes.yaml`.
  Commit an authorized prompt change before rotating its pin with an explicit
  reason; changing a registered instrument requires its declared version boundary.
  Preserve immutable playbook versions and original captured instruction bytes.
  This guide's new memory bytes are not proof an older run read them.
- No repository gold standard exists: `curated` is a ChatGPT-chat comparison arm,
  not hand-curated truth, and its records describe superseded releases. Interpret
  arm differences against source coverage, release and instrument identity.
- Literal receipt matches and complete structure do not establish entailment or
  exhaustive recall. Receipt origin distinguishes contemporaneous from post-draft
  evidence; unknown measurements are not zero. Preserve snapshot/identity joins,
  captured hashes and prior measurements when rechecking or amending a record.
- Never invent reasoning effort or token usage. Keep observed model-route effort,
  launcher assertions and missing measurements distinct; do not write guesses such
  as "default". Partial thinking counts need coverage; absent logs are not low spend,
  and unfinalized streaming snapshots below the 4-chars/token payload floor are
  strict lower bounds on `output_tokens`, `reasoning_tokens_estimate`, and `thinking_tokens` (#5047):
  a message below its floor with no `stop_reason` line, in every sampled Claude Code
  subagent transcript from 2.1.278 on and some earlier ones, detected per message and
  recorded per invocation as `run_observed.invocations_snapshot_lower_bound` (#5068).
- A review reads its existing pinned pack, not a rewritten replacement. Preserve
  human dispositions and mark stale attestations explicitly. Review counts remain
  reported-only pending calibration under the [selection policy](notes/review_selection_policy_2026-09-11.md).
- Evaluator model selection is not proof of independence or reliability. Respect
  `evaluation_config.yaml`, explicit overrides, recorded cache models and separately
  registered rubric defaults; a model switch needs new registration/calibration.
  Validate each new semantic evaluation with the strict exact-file command:
  `poetry run python scripts/validate_evaluation_schema.py --file OUTPUT_PATH --rubric RUBRIC`.
  A historical corpus inventory can report kept invalid outputs; it cannot approve
  a new file. Preserve historical outputs rather than rewrite them for today's schema.

## Read only the guidance relevant to the task

| Task | Entry point |
|---|---|
| CLI commands and input/output conventions | [CLI reference](docs/cli.md), command `--help` |
| Schema versions and generated products | [Versioning](docs/VERSIONING.md), [release boundary](notes/schema_release_3.0.0_2026-09-16.md) |
| Existing generation playbooks | [Command index](.claude/commands/README.md); load only the selected version and its required guard |
| Registered shared API generation | [Shared-generation protocol](docs/shared-generation-api-v1.md); no default registration or native authorization |
| Generation-affecting text/code changes | [Specificity audit](.claude/skills/d4d-generation-specificity-audit/SKILL.md); use its actual scope and limits |
| Semantic evaluation | [Rubric usage](notes/RUBRIC_AGENT_USAGE.md), selected `.claude/agents/` instrument |
| GitHub assistant workflow | [Current assistant guide](.github/D4D_ASSISTANT_README.md), [workflow index](.github/workflows/README.md) |
| Full issue-queue triage | [Review skill](.claude/skills/review-open-issues/SKILL.md); not a prerequisite for every next edit |
| Receipt, provenance, resource and historical protocol details | [Historical topic index](docs/agent-instructions-history/README.md); confirm current behavior against source |

The GitHub assistant uses an authorized explicit request naming a repository input
directory, complete input preparation and `d4d api run`. It does not fetch linked
URLs or perform open-ended edits from feedback. The old assistant create/edit
instruction files are not loaded by that workflow; interactive playbooks that
explicitly select them remain separate instruments. Do not load a whole catalog
of agent bodies or automatically include the historical archive in each task.
