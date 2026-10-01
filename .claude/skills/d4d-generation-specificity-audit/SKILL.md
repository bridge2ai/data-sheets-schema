---
name: d4d-generation-specificity-audit
description: Audit the D4D generation process (native agentic, API, GitHub assistant, shared schema, deterministic arms, run controllers, legacy scripts) for text or code hardcoded to a Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program or to biomedical/clinical data (tracked), and report what "api" means in the code (monolithic or multi-phase, and whether any step of an API run is agentic). Use before or after changing anything in the generation path (prompts, playbooks, agents, api_runner, schema, profiles, manifest handling, run controllers), before registering a new arm or condition, and when onboarding a non-Bridge2AI dataset. Offline, deterministic, no model calls.
metadata:
  category: audit
  requires_database: false
  requires_internet: false
  version: 1.1.0
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
  root is the checkout that holds the skill. To audit another commit, point
  `--root` at a checkout of it.

Exit status: `0` no violation; `1` at least one gc_project violation; `2` the
scan did not happen. A `2` comes from a failed self-test, a malformed
configuration (a missing token list, a malformed regex in `tokens.yaml` or
`exceptions.yaml`, a malformed exception), a discovered surface that cannot
be read, a derivation in the "api" section that found nothing in the code
("api meaning not derived: ..."), or any unexpected error (the traceback is
printed). Do not read a `2` as a clean result, and a crash is never a `1`.

The guard tests are `tests/test_generation_specificity_skill.py` and the
existing neutrality tests the scanner builds on:
`tests/test_neutral_generation_schema.py`, `tests/test_profiles.py`,
`tests/test_external_dataset_onboarding.py`. Run those too after changing a
generation surface. The skill's tests check that:

- the scanner sees: the self-test, and a token planted in a copy of a real
  surface under the role `discover()` gives it;
- project-keyed tables, defaults and keys gate in run-shaping code;
- discovery finds every model client, controller and named playbook or agent;
- the "api" section agrees with the runtime: the CLI default condition and
  default renderers are what `cli/api.py`'s `_spec` builds, and the audit
  floor is where `build_phase` refuses the audit; each derivation is read in
  any spelling and fails loudly when the code changes shape;
- a broken configuration or an unexpected error is exit 2.

None of them walks the record corpus, so none is marked `corpus`.

## What it scans

Surfaces are derived from the code (imports, calls, the names a file uses),
not from a list of files. One name glob is left, for the pre-runner helper
scripts in `src/download` that write prompts without calling a model.

| approach | gates | discovered from |
|---|---|---|
| `native_agentic` | yes | `.claude/commands/d4d-*.md`; every command or agent that a playbook, a live condition prompt, a run controller or the assistant instructions name, by path, bare name (`d4d-validator`) or slash command (`/d4d-full-core`), followed through the files they name (model-facing); every other agent is `exposed`, because `agentic_runtime.toolchain()` hands every agent file to a native run; the import closure of `agentic_runtime`, of the CLI groups `d4d-full-core.md` runs, and of the package modules the run controllers import; `.claude/agents/scripts/*.py` |
| `api` | yes | the import closure of `cli/api.py` and `api_runner.py`; every condition in `api_runner.CONDITION_PROMPTS` (the newest `generic_vN` and the CLI default are **live**, the rest **historical**); the `tuned` prompt and components; evidence protocols (newest live); every file pinned in `canonical_hashes.yaml` |
| `github_assistant` | yes | `.github/workflows/d4d_assistant_*.md`, `d4d-agent.yml`, the deterministic config, and the condition the workflow runs |
| `shared_schema` | yes | the import closure of `data_sheets_schema.yaml` and `data_sheets_schema_core.yaml`, the merged files in `agentic_runtime.SCHEMAS`, `profiles.py`, `registry.py`, the vocabulary pin, the study manifest |
| `deterministic` | yes | `healthsheet.py`, `rocrate_normalize.py` (these build bundles a model reads), `rocrate_map.py` and their CLIs |
| `run_controllers` | yes | under `notes/`: every module (not a probe, not on an evaluation path) that uses a generation builder as code (`RunSpec`, `build_phase`, `phase_instruction`, `prompt_body`, `resolve_prompt`, `playbook_text`, `digest_text`, `assembly_digest`); every `notes/` module they import or pin by file name; every module that runs one (imports one, or stages one by file name), to a fixed point; the Markdown a controller names beside itself (`system.md`, model-facing) |
| `legacy_monolithic` | yes | every module under `src/` or `scripts/`, outside the generation closures, that calls a model client and names D4D or a datasheet (not an evaluator); the pre-runner helpers in `src/download` (`process_*.py`, `*d4d*`, `prompt_loader`: the name glob); `d4d_concatenated_*.txt`; `prompts/{claude,claudecode,gpt5,shared}/` |
| `shared_input` | no | download, preprocess and concatenate: upstream of every approach |
| `other_model_client` | no | a model client outside generation: under `notes/`, one outside the controller set (diagnostic probes, transports); evaluation modules a controller imports or that import one, and their imports; under `src/` or `scripts/`, an evaluator or a client that names no D4D record |

A module is a model client when it imports `anthropic`, `openai`,
`pydantic_ai` or `aurelian`, or calls `*.messages.create|stream`,
`*.chat.completions.create`, `*.responses.create`,
`openai.ChatCompletion.create` or an agent's `run`/`run_sync`. Imports and
calls are read from the code, so a comment that mentions one does not count.
Registered byte copies under `registrations/` are frozen evidence and are not
read. The report's "How the surfaces were found" section lists every
controller with the reason it was found and every model client with its
classification.

Each file is `model_facing` (its text reaches a model), `exposed` (available
to a native run, named by no playbook) or `run_shaping` (decides what runs).
In a run controller, the string literals of a function that renders what a
model receives (`render_*`, `*instruction`, `*_system`, `*prompt*`) are
model-facing although the module is run-shaping. `MODEL_FACING_MODULES` in
`scan.py` is the one hand-kept list, for the `src/` package. A test fails
when a name on it is no longer in a discovered closure.

Tokens come from ONE source. The scanner parses `STUDY_IDENTITY`,
`STUDY_DESIGN` and `PROSE_ONLY` out of `tests/test_neutral_generation_schema.py`
and adds the extensions in `tokens.yaml`. Add a new token to `tokens.yaml` (or,
for schema text, to the neutrality test) rather than to `scan.py`.

Every hit is classified by context:

- `.py`: `string_literal` (a model-facing candidate), `code_branch` (a
  comparison, `match` case or `startswith` test on the value), `code_table`,
  `docstring`, `comment`. A `code_table` is a bare-token string (no
  whitespace), or a collection of them, also through `frozenset()`, `set()`,
  `tuple()`, `list()`, in a table, default or key position: a dict key or
  value; a value assigned anywhere (a module constant, a function local, an
  attribute); a loop or comprehension iterable; a keyword argument; a
  parameter default; a returned value; a subscript key; an argument of
  `.get`, `.setdefault`, `.pop`, `getenv` or `getattr`. A string with
  whitespace is text and stays a `string_literal`. Each physical line of a
  literal is its own unit, read from the tokens that spell it, so the parts
  of an implicitly concatenated literal are reported on their own lines.
- `.md` and `.txt`: `instruction`, `example`, `prose`, `frontmatter`, or `header`.
  `header` is text above `## Prompt body` in a condition prompt; `prompt_body()`
  never sends it.
- `.yaml`: `prose` (description/title/comments), `example`, `value`, `comment`.

## Read the report

1. **Self-test line.** It must say `passed`. The self-test plants one token per
   category in a Markdown file, and in a Python file a branch, a comment, a
   dict key, a `frozenset` constant, a lookup default, a keyword argument, a
   loop tuple, a string literal, an implicitly concatenated literal and a
   triple-quoted block. It checks each is found with its category (Markdown)
   or context (Python) on the line where it was planted.
2. **Surfaces table and "How the surfaces were found".** Check that the file
   counts per approach are plausible and that the controllers and model
   clients listed are what you expect. A zero means discovery broke.
3. **gc_project violations.** These are the findings that fail the run. A
   violation is a Grand Challenge name, site or identifier in model-facing
   text, or in a code branch or table, in a gating surface, with no exception.
4. **Tracked categories.** Counts per category and approach. The second table
   lists model-facing or code-level tracked hits that have no recorded reason.
   That table is the triage queue.
5. **gc_project hits that do not fail.** Comments, docstrings, headers,
   run-shaping literals, exposed agent files, non-gating approaches and
   excepted hits. Skim it for anything misclassified, for example prose in a
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

The scanner derives the section from the code, and each derivation either
finds what it reads or stops the scan with "api meaning not derived: ..."
and exit 2. None falls back to a constant (#4025).

- `api_runner.PHASES`, `DERIVED_PHASES` and `CORE_DERIVED` give the model
  phases.
- `build_phase` shows which schema form is sent (`digest_text` or the merged
  `_all.yaml`).
- `PHASE_INSTRUCTIONS` keys outside the phases, plus the `build_*` builders,
  give the follow-up turns (re-address, regate, repair).
- The guard in `build_phase` that raises on `render_version >= N` and
  `phase == "audit"`, in either order, gives the renderer from which the
  audit is a registered native batch.
- `RunSpec`'s `render_version = A if is_agentic else B` gives the default
  renderers, and the assignment under `if condition is None:` in
  `cli/api.py` gives the condition `d4d api` runs when given none.
- Every module that sets a renderer at or above N (a `render_version=`
  keyword, a `["render_version"]` or `.render_version` assignment, a
  `"render_version"` entry), and the gate in its controller package that
  refuses a parent that is not an agentic run, give who can reach the native
  audit batch. `cli/api.py` is read for any way to hand `RunSpec` a renderer.
- Each condition's prompt body gives the playbook files it tells the model to
  read (paths and bare names).
- Every legacy script is checked for model call sites, a full-schema load and
  concatenated input.

Read it as follows:

- **MONOLITHIC** means one model call with prompt + full LinkML schema +
  concatenated documents. **MULTI-PHASE** means several calls, a schema
  digest, or follow-up turns.
- **prompt-level hybrid** means the prompt body tells the model to open
  `.claude/...` files that the API request never carries (#4014). The API
  model is then told to follow a procedure it cannot see. This is about the
  text, not the run.
- **runtime hybrid** means an API run part of which is done by a native agent.
  From renderer N, `build_phase` refuses the audit phase on every spec, and
  the audit is a registered native batch. That batch is reached only by
  native audit continuations, and each sits in a controller package that
  refuses a parent unless it is an agentic run (today
  `audit_controls/contract.py` accepts only an agentic `generic_v9` parent
  at renderer 14). So the whole lineage is native, and every API condition
  reads `no`. It reads `possible` only when some module sets a renderer of N
  or more with no such gate in its package. An API run that reached renderer
  N itself would stop at the audit, not become a hybrid. One condition name
  rendered by an agentic runtime is two procedures, not a hybrid run.

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
  role (or, in a controller, by the function it is in), not traced.
- The runtime-hybrid verdict associates a renderer setter with a gate by
  controller package (directory), not by call path. The report names every
  setter and gate so a reviewer can confirm the path (today `prepare.py`
  renders every continuation through `contract.render_instruction`).
- Evaluation is out of scope: evaluation modules and the rubric agents are
  listed, never gating.
- The pre-runner helpers in `src/download` that write prompts without calling
  a model are found by a name glob, the one glob left.
- Untracked or gitignored files are scanned when they exist under a
  discovered tree. The scanner does not consult `.gitignore`.
