---
name: d4d-generation-specificity-audit
description: Audit the D4D generation process (native agentic, API, GitHub assistant, shared schema, deterministic arms, legacy scripts) for text or code hardcoded to a Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program or to biomedical/clinical data (tracked), and report what "api" means in the code (monolithic or multi-phase, and whether any step is agentic). Use before or after changing anything in the generation path (prompts, playbooks, agents, api_runner, schema, profiles, manifest handling), before registering a new arm or condition, and when onboarding a non-Bridge2AI dataset. Offline, deterministic, no model calls.
metadata:
  category: audit
  requires_database: false
  requires_internet: false
  version: 1.0.0
---

# D4D generation-specificity audit (#4007)

The owner's rule: no project-specific code or text anywhere in the D4D
generation process, in any approach. Bridge2AI-program and biomedical/clinical
specificity may be acceptable, but each instance is tracked with a reason.
Separately, "api" must keep meaning the monolithic approach: one model call
whose input is the prompt, the full LinkML schema and the input documents
concatenated with separators. A combined native-agentic and API approach is
possible, and must be tracked as such.

This skill runs a scanner and reads its report. It does not fix findings,
edit pinned files, or launch any run.

## Run it

```bash
python .claude/skills/d4d-generation-specificity-audit/scan.py \
    --report notes/generation_specificity_audit_$(date +%F).md \
    --json   notes/generation_specificity_audit_$(date +%F).json
```

- Needs only the standard library and PyYAML. It never imports or executes the
  generation code: the runner's tables are read with `ast`.
- Without `--report`, the report and JSON go to a fresh temp directory and the
  paths are printed.
- `--self-test-only` runs only the seeded self-test.
- In a worktree, run it from the worktree (or pass `--root`); the default
  root is the checkout that holds the skill.

Exit status: `0` no violation; `1` at least one gc_project violation; `2` the
self-test or the configuration failed (missing token list, malformed
exception). A `2` means the scan did not happen. Do not read it as a clean
result.

The guard tests are `tests/test_generation_specificity_skill.py` (the scanner
sees, exceptions parse, a planted token is a violation, the API-meaning
section names the live conditions) and the existing neutrality tests it
builds on: `tests/test_neutral_generation_schema.py`, `tests/test_profiles.py`,
`tests/test_external_dataset_onboarding.py`. Run those too after changing a
generation surface.

## What it scans

Surfaces are discovered from entry points and globs, not a list of single
files:

| approach | discovered from |
|---|---|
| `native_agentic` | `.claude/commands/d4d-*.md`; `.claude/agents/*.md` (model-facing when a playbook or a live prompt names it, otherwise `exposed`, because `agentic_runtime.toolchain()` hands every agent file to a native run); the import closure of `agentic_runtime`, the CLI groups `d4d-full-core.md` runs, and the package modules the `notes/*/native_controls`, `audit_controls` and `claudecode_direct` controllers import; their `system.md` |
| `api` | the import closure of `cli/api.py` and `api_runner.py`; every condition in `api_runner.CONDITION_PROMPTS` (the newest `generic_vN` and the CLI default are **live**, the rest **historical**); the `tuned` prompt and components; evidence protocols (newest live); every file pinned in `canonical_hashes.yaml` |
| `github_assistant` | `.github/workflows/d4d_assistant_*.md`, `d4d-agent.yml`, the deterministic config, and the condition the workflow runs |
| `shared_schema` | the import closure of `data_sheets_schema.yaml` and `data_sheets_schema_core.yaml`, the merged files in `agentic_runtime.SCHEMAS`, `profiles.py`, `registry.py`, the vocabulary pin, the study manifest |
| `deterministic` | `healthsheet.py`, `rocrate_normalize.py` (these build bundles a model reads), `rocrate_map.py` and their CLIs |
| `legacy_monolithic` | `src/download/process_*.py`, the other `*d4d*` scripts there, `d4d_concatenated_*.txt`, `prompts/{claude,claudecode,gpt5,shared}/` |
| `shared_input` | download, preprocess and concatenate. Listed, never gates: these steps are upstream of every approach |

Each file is `model_facing` (its text reaches a model), `exposed` (available to
a native run, named by no playbook) or `run_shaping` (decides what runs).
`MODEL_FACING_MODULES` in `scan.py` is the one hand-kept list. A test fails
when a name on it is no longer in a discovered closure.

Tokens come from ONE source. The scanner parses `STUDY_IDENTITY`,
`STUDY_DESIGN` and `PROSE_ONLY` out of `tests/test_neutral_generation_schema.py`
and adds the extensions in `tokens.yaml`. Add a new token to `tokens.yaml` (or,
for schema text, to the neutrality test) rather than to `scan.py`.

Every hit is classified by context:

- `.py`: `string_literal` (a model-facing candidate), `code_branch` (a
  comparison, `match` case or `startswith` test on the value), `code_table`
  (a dict key, a bare-token dict value, a module constant, a `default=`),
  `docstring`, `comment`.
- `.md` and `.txt`: `instruction`, `example`, `prose`, `frontmatter`, or `header`.
  `header` is text above `## Prompt body` in a condition prompt; `prompt_body()`
  never sends it.
- `.yaml`: `prose` (description/title/comments), `example`, `value`, `comment`.

## Read the report

1. **Self-test line.** It must say `passed`. The self-test plants one token per
   category and a Python branch, table and comment in a temp file and checks
   each is found on the line where it was planted.
2. **Surfaces table.** Check that the file counts per approach are plausible. A
   zero means discovery broke.
3. **gc_project violations.** These are the findings that fail the run. A
   violation is a Grand Challenge name, site or identifier in model-facing
   text, or in a code branch or table, in a gating surface, with no exception.
4. **Tracked categories.** Counts per category and approach. The second table
   lists model-facing or code-level tracked hits that have no recorded reason.
   That table is the triage queue.
5. **gc_project hits that do not fail.** Comments, docstrings, headers,
   run-shaping literals, exposed agent files, upstream steps and excepted
   hits. Skim it for anything misclassified, for example prose in a
   comment-looking line that is actually sent.
6. **Tests asserting project-dependent generation behaviour.** Tests that
   exercise generation (`build_phase`, `resolve_prompt`, `RunSpec`, ...) and
   assert a project literal. They are listed, not failed. A test that pins
   neutral behaviour on a study project is fine. A test that pins
   project-specific behaviour documents a violation.
7. **Exceptions.** Hits per entry. An unused entry is stale or its finding
   was fixed. Remove it.
8. **What "api" means.** See below.

## Triage each category

**gc_project: a violation. Fix it in a follow-up PR, never with an
exception to make the run pass.**

- A fact about the dataset (name, programme phrase, DOI, platform, scope,
  related dataset) goes in the manifest (`data/preprocessed/source_manifest.yaml`:
  `naming`, `scope`, `source_priority`, ...). The runner renders it only for
  that project's bundle.
- A study default (arm project lists, healthsheet input, aliases, vocabulary)
  goes in the `bridge2ai` profile in `profiles.py`. `neutral` carries none.
- An example in an instruction is replaced with a neutral placeholder
  (`<platform>`, `example.org`, `10.xxxx/...`).
- A code branch or table keyed on a project name is replaced by a lookup in
  the manifest or the profile. A launcher default (`--project CHORUS`) is
  removed, so the caller must name the project.
- A pinned prompt (`src/download/prompts/**`, `canonical_hashes.yaml`) cannot
  be edited in place. The fix is a new condition or a retirement, decided by
  the owner.
- Legacy scripts: fix them, or retire them in a dated, owner-approved change.

**bridge2ai_program and biomedical_clinical: tracked.** Each hit
in a generation surface needs a reason recorded in `exceptions.yaml`. Acceptable
reasons include the schema's own namespace (`w3id.org/bridge2ai`, `B2AI_*`
prefixes), the human-subjects modules that model clinical datasets by design,
and a generic rule that applies to any human-subjects dataset. When the
reason is weak, move the term to the profile or generalize the wording
("ethics approval" for "IRB"). Report it either way.

## Add a tracked exception

Edit `.claude/skills/d4d-generation-specificity-audit/exceptions.yaml`:

```yaml
  - path: src/data_sheets_schema/schema/D4D_Human.yaml   # glob; list allowed
    category: biomedical_clinical                         # and/or token: 'HIPAA'
    context: [prose, example]                             # optional
    reason: >-
      Why this hit is acceptable where it is.
    decision: '#NNNN (the issue, PR or owner decision that settled it)'
```

`reason` and `decision` are required, and an entry must name a `token` or a
`category`. An excepted hit is still listed under its exception number.
Exceptions classify findings; they never hide one. A gc_project exception
needs an owner decision explaining why the fact cannot live in the manifest
or profile. The seeded gc_project exceptions are `profiles.py`, the study
manifest, the vocabulary pin, the pinned `tuned` prompts and the changelog
headers of the generic prompts, and `constants/projects.py` (analysis only).

## Check the "api meaning" section

The scanner derives the section from the code:

- `api_runner.PHASES`, `DERIVED_PHASES` and `CORE_DERIVED` give the model
  phases.
- `build_phase` shows which schema form is sent (`digest_text` or the merged
  `_all.yaml`).
- `PHASE_INSTRUCTIONS` keys outside the phases, plus the `build_*` builders,
  give the follow-up turns (re-address, regate, repair).
- The renderer guard in `build_phase` gives the agentic step (from the
  renderer number it names, the audit requires the native batch).
- Each condition's prompt body gives the playbook files it tells the model to
  read.
- The legacy `process_*.py` scripts are checked for call sites, a full-schema
  load and concatenated input.

Read it as follows:

- **MONOLITHIC** means one model call with prompt + full LinkML schema +
  concatenated documents. **MULTI-PHASE** means several calls, a schema
  digest, or follow-up turns.
- **agentic-only instruction** means the prompt body tells the model to open
  `.claude/...` files that the API request never carries. The API model is
  then told to follow a procedure it cannot see.
- **agentic step** gives the renderer from which a phase is done by a native
  agent. A run registered at that renderer is a hybrid.

When the section says that no live condition is MONOLITHIC, "api" in the
code no longer has the owner's meaning. Record that in the PR. A real
monolithic arm needs a new condition or method directory, a canary, and the
owner's approval before anything is billed.

## Limits

- A token list finds what it names. A project fact phrased without any listed
  token, such as a participant count or a site name, is invisible. Add
  tokens when a review finds one.
- Context classification is heuristic for Markdown and YAML. A Python string
  that reaches a model only through a variable is classified by the file's
  role, not traced.
- Untracked or gitignored files are scanned when they exist under a
  discovered glob. The scanner does not consult `.gitignore`.
- The `notes/` controllers are scanned as generation code because the
  registered native and direct runs execute them.
