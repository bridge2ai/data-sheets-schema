---
name: d4d-generation-specificity-audit
description: Audit the D4D generation process (native agentic, interactive Claude Code sessions, API, GitHub assistant, shared schema, deterministic arms, run controllers, legacy scripts) for text or code hardcoded to a Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program or to biomedical/clinical data (tracked), and report what "api" means in the code (monolithic or multi-phase, and whether any step of an API run is agentic). Use before or after changing anything in the generation path (prompts, playbooks, agents, CLAUDE.md, api_runner, schema, profiles, manifest handling, run controllers), before registering a new arm or condition, and when onboarding a non-Bridge2AI dataset. Offline, deterministic, no model calls.
metadata:
  category: audit
  requires_database: false
  requires_internet: false
  version: 1.2.0
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

- Needs only the standard library and PyYAML (use the project's interpreter,
  e.g. `poetry run python`). It never imports or executes the generation
  code: the runner's tables are read with `ast`.
- Without `--report`, the report and JSON go to a fresh temp directory and the
  paths are printed.
- `--self-test-only` runs only the seeded self-test.
- In a worktree, run it from the worktree (or pass `--root`); the default
  root is the checkout that holds the skill. To audit another commit, point
  `--root` at a checkout of it (a `git clone --shared` checked out at that
  commit records the commit in the report).

Exit status: `0` no violation; `1` at least one gc_project violation; `2` the
scan did not happen. A `2` comes from PyYAML not being importable, a failed
self-test, a malformed configuration (a missing token list, a malformed regex
in `tokens.yaml` or `exceptions.yaml`, a malformed exception), a discovered
surface that cannot be read, a derivation that found nothing in the code
("not derived: ..."), or any unexpected error (the traceback is printed). Do
not read a `2` as a clean result, and a crash is never a `1`.

The guard tests are `tests/test_generation_specificity_skill.py` and the
existing neutrality tests the scanner builds on:
`tests/test_neutral_generation_schema.py`, `tests/test_profiles.py`,
`tests/test_external_dataset_onboarding.py`. Run those too after changing a
generation surface. The skill's tests check that:

- the scanner sees: the self-test, and a token planted in a copy of a real
  surface under the role `discover()` gives it, including CLAUDE.md and the
  controller text that reaches a model by data flow;
- project-keyed tables, defaults and keys gate in run-shaping code; an
  exposed file never gates; a `__main__` block gates only where its module
  runs as a script;
- discovery finds every model client, controller and launcher (over `src/`,
  `notes/` and `scripts/`), every file a playbook, agent, assistant
  instruction or controller names, the deterministic arms and the upstream
  input from the code;
- the "api" section agrees with the runtime: the CLI default condition, the
  condition the GitHub assistant runs, the default renderers, the audit
  floor, the renderers `api_runner.execute` refuses, which conditions make
  each follow-up turn, and what a `tuned` instruction carries; a monolithic
  runner is reported monolithic; a renderer is read in any spelling; each
  derivation fails loudly when the code changes shape;
- a violation is exit 1, a clean scan 0, and a scan that did not happen 2.

None of them walks the record corpus, so none is marked `corpus`.

## What it scans

Surfaces are derived from the code: imports, calls, the files a text names,
and the names a file uses. What is left by hand, and why:

- `MODEL_FACING_MODULES` in `scan.py`: which top-level `data_sheets_schema`
  modules write text a model reads. An import graph does not say that. A
  test fails when a name on it is in none of the api, native or
  deterministic closures.
- The `shared_schema` files `profiles.py`, `registry.py`, the vocabulary pin
  and the study manifest, each with the reason it reaches a model.
- The pre-runner helpers in `src/download` that write prompts without calling
  a model (`process_*.py`, `*d4d*`, `prompt_loader`): a name glob.
- What Claude Code itself loads into a session (`CLAUDE.md`,
  `CLAUDE.local.md`, `.claude/CLAUDE.md`, `.claude/settings*.json`,
  `.claude/skills/*/SKILL.md`): the runtime's rule, not the repository's.
- The entry points: `.claude/commands/d4d-*.md` are the playbooks,
  `cli/download.py` is the `d4d download` group, `d4d-full-core.md` is the
  playbook whose CLI groups are followed.

| approach | gates | discovered from |
|---|---|---|
| `native_agentic` | yes | `.claude/commands/d4d-*.md`; every playbook or agent that a playbook, a live condition prompt, a run controller or the assistant instructions name, by path, bare name (`d4d-validator`) or slash command (`/d4d-full-core`), followed through the playbooks and agents they name (model-facing); every other file `agentic_runtime.toolchain()` hands a native run (it lists `*.md` in `.claude/commands` and `.claude/agents`, read with ast) is `exposed`; every other file those texts name by path or run (`python x.py`, `python -m mod`), with the namer's status; the import closure of `agentic_runtime`, of the CLI groups `d4d-full-core.md` runs, and of the package modules the run controllers import |
| `interactive_session` | yes | what Claude Code loads into a person's session in a checkout, where the `/d4d-*` playbooks run interactively: the project memory (`CLAUDE.md`, model-facing), the project settings and the hook scripts they run, and the skills (exposed). Interactive sessions only: the registered native launchers pass `--safe-mode`, which disables all of it, and the report names where |
| `api` | yes | the import closure of `cli/api.py` and `api_runner.py`; every condition in `api_runner.CONDITION_PROMPTS` (the newest `generic_vN`, the CLI default and the condition the GitHub assistant runs are **live**, the rest **historical**); the `tuned` components `resolve_prompt` inserts (`d4d_tuned_arm_prompt.md` is only hashed and named in a header, so it is run-shaping); evidence protocols (newest live); every file pinned in `canonical_hashes.yaml` |
| `github_assistant` | yes | `.github/workflows/d4d_assistant_*.md`, `d4d-agent.yml`, the deterministic config, the condition the workflow runs, and every file the instructions name or run (`src/github/*.py`, `scripts/check_budget.py`, ...) |
| `shared_schema` | yes | the import closure of `data_sheets_schema.yaml` and `data_sheets_schema_core.yaml`, the schemas `agentic_runtime.toolchain()` hands a native run, and the hand-kept files above |
| `deterministic` | yes | the arm commands: every CLI group outside the generation closures that names the bundle of an arm in `cli/api.py` `ARMS` other than the default one (today `cli/healthsheet.py` and `cli/rocrate.py`), and their import closure, followed through `data_sheets_schema`, `src.*` and the directories the code puts on `sys.path` (`setup_repo_imports` adds `.claude/agents/scripts`) |
| `run_controllers` | yes | under `notes/`: every module (not a probe, not on an evaluation path) that uses a generation builder as code (`RunSpec`, `build_phase`, `phase_instruction`, `prompt_body`, `resolve_prompt`, `playbook_text`, `digest_text`, `assembly_digest`); under `scripts/` or `src/`, outside the generation closures: a module that uses one and launches a run (calls the runner's `execute`, or hands a native runtime `--system-prompt`); every `notes/` or `scripts/` module they import or pin by file name; every module that runs one, to a fixed point; the Markdown a controller names beside itself (`system.md`, model-facing); every file a controller names in its literals |
| `legacy_monolithic` | yes | every module under `src/` or `scripts/`, outside the generation closures, that calls a model client and names D4D or a datasheet (not an evaluator); the pre-runner helpers in `src/download` (the name glob); `d4d_concatenated_*.txt`; every prompt set beside the conditions (`src/download/prompts/*/` other than the tuned components) |
| `shared_input` | no | the `src.download` modules the `d4d download` group imports (download, preprocess, concatenate) and the `src/download` modules they import: upstream of every approach, and where a closure stops |
| `other_model_client` | no | a model client outside generation: under `notes/`, one outside the controller set (diagnostic probes, transports); evaluation modules a controller imports or that import one, and their imports; under `src/` or `scripts/`, an evaluator or a client that names no D4D record |

A module is a model client when it imports `anthropic`, `openai`,
`pydantic_ai` or `aurelian`, or calls `*.messages.create|stream`,
`*.chat.completions.create`, `*.responses.create`,
`openai.ChatCompletion.create` or an agent's `run`/`run_sync`. Imports and
calls are read from the code, so a comment that mentions one does not count.
Registered byte copies under `registrations/` are frozen evidence and are not
read. The report's "How the surfaces were found" section lists the toolchain,
every controller with the reason it was found, every model client with its
classification, every named file and who names it, the interactive-session
evidence, the deterministic arm commands and the upstream input.

### Roles

A file has a role in each approach that reaches it: `model_facing` (its text
reaches a model), `run_shaping` (decides what runs) or `exposed` (available
to a native or interactive session, named by nothing live). Each approach
judges a hit by its own role:

- text (a string literal, prose, an example, an instruction, a value) counts
  where the role is model-facing;
- in run-shaping code, a string literal counts as text when it is model text:
  the body of a run-controller function named for it (`render_*`,
  `*instruction`, `*_system`, `*prompt*`), or code found by data flow. From
  every argv element after `--system-prompt` or `--append-system-prompt` in
  a controller, and from those functions' return values, the flow follows
  local assignments, marks a function whose result becomes part of the text
  (and follows its returns in turn, across imports) and a module constant the
  text is built from (`SYSTEM`, which `render_system` returns). Today that
  finds the `SYSTEM` constants of the audit and finalization preparers,
  `command_guidance` and `lookup_guidance`;
- a code branch or table counts unless the role is exposed;
- nothing in a `__main__` block counts for an approach that only imports the
  module (it never runs that block).

A hit is a violation when it is gc_project, has no exception, and some gating
approach counts it (`gates_in` in the JSON).

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
- `.yaml`: `prose` (description/title/comments), `example` (under the
  `examples` or `annotations` metaslot), `value`, `comment`. A key directly
  under `attributes:`, `slots:`, `classes:` and the like is an element's
  name, so a slot *named* `examples` is not the metaslot.

## Read the report

1. **Self-test line.** It must say `passed`. The self-test plants one token per
   category in a Markdown file, and in a Python file a branch, a comment, a
   dict key, a `frozenset` constant, a lookup default, a keyword argument, a
   loop tuple, a string literal, an implicitly concatenated literal and a
   triple-quoted block. It checks each is found with its category (Markdown)
   or context (Python) on the line where it was planted.
2. **Surfaces table and "How the surfaces were found".** Check that the file
   counts and violations per approach are plausible and that the controllers,
   named files and model clients listed are what you expect. A zero means
   discovery broke.
3. **gc_project violations.** These are the findings that fail the run. A
   violation is a Grand Challenge name, site or identifier in model-facing
   text, or in a code branch or table, that a gating approach counts, with no
   exception. The approach column says which.
4. **Tracked categories.** Counts per category and approach. The second table
   lists model-facing or code-level tracked hits that have no recorded reason.
   That table is the triage queue.
5. **gc_project hits that do not fail.** Comments, docstrings, headers,
   run-shaping literals, `__main__` blocks of imported modules, exposed
   files, non-gating approaches and excepted hits. Skim it for anything
   misclassified, for example prose in a comment-looking line that is
   actually sent.
6. **Tests asserting project-dependent generation behaviour.** Tests that
   exercise generation (`build_phase`, `resolve_prompt`, `RunSpec`, ...) and
   assert a project literal. They are listed, not failed. A test that pins
   neutral behaviour on a study project is fine. A test that pins
   project-specific behaviour documents a violation. The tests of this audit
   are not listed: they plant tokens to check the scanner.
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
- `CLAUDE.md` is auto-loaded into every interactive session in the checkout:
  its study content is a violation there, and moving it out of the
  auto-loaded file is an owner decision.
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
finds what it reads or stops the scan with "not derived: ..." and exit 2.
None falls back to a constant (#4025).

- `api_runner.PHASES`, `DERIVED_PHASES` and `CORE_DERIVED` give the model
  phases.
- `build_phase` shows which schema form is sent (`digest_text` or the merged
  `_all.yaml`).
- The follow-up turns are the model calls besides the phases: every call of
  the runner's model-call wrapper (the function taking a `phase` that calls
  the function that sends the request), with the phase it names read through
  literals, f-strings, locals, loops and what callers pass. Which conditions
  make a turn comes from `plan()`'s `conditional_calls` (re-addressing only
  under `RECEIPT_CONDITIONS`); a turn `plan()` does not list is made under
  every condition when no condition test guards its call path.
- The guard in `build_phase` that raises on `render_version >= N` and
  `phase == "audit"`, in either order, gives the renderer from which the
  audit is a registered native batch. RunSpec's `render_version not in
  (...)` refusal gives the renderers it admits, and the raising test at the
  top of `api_runner.execute` the renderers it refuses before it runs.
- `RunSpec`'s `render_version = A if is_agentic else B` gives the default
  renderers, and the assignment under `if condition is None:` in
  `cli/api.py` gives the condition `d4d api` runs when given none;
  `d4d-agent.yml`'s `d4d api run` gives the condition the GitHub assistant
  runs (its `--condition`, else that default).
- Native continuations: run controllers that rebuild a parent run's spec
  (`RunSpec.from_render_spec`), at any renderer. Each one's controller package
  (directory) must hold a gate: an `if` that raises when `not
  spec.is_agentic` (or `spec.runtime not in AGENTIC_RUNTIMES`) is one of its
  `or` disjuncts. A guard on the condition alone, one that refuses agentic
  parents, or `a and not spec.is_agentic` is not a gate.
- Renderer setters: every `render_version=` keyword, `["render_version"]` or
  `.render_version` assignment and `"render_version"` entry in a controller,
  whatever its value: a literal, a constant, a local, an option (its
  `choices`, or unbounded without them), arithmetic (unbounded). A value read
  from a record, a registration, a spec or a caller passes on a renderer set
  elsewhere and is counted, not listed. A setter that can reach N is covered
  when its package holds a gate, or when its spec names an agentic runtime
  (its own call or dict, else every runtime its module names); otherwise a
  runtime hybrid is possible.
- `resolve_prompt`'s `if spec.condition == "tuned":` block gives what a tuned
  instruction carries: the path constants whose file text it reads (the
  components), as against the ones it only names (`TUNED_PROMPT`).
- An arm's shape is its condition's: `api_runner` never branches on the arm
  (checked), and an arm sets the bundle, method directory and manifest.
- The native row is read from `agentic_runtime.SCHEMAS` and the playbook's
  `Phase N` headings.
- Each condition's prompt body gives the playbook files it tells the model to
  read (paths and bare names).
- Every legacy script is checked for model call sites, a full-schema load and
  concatenated input.

Read it as follows:

- **MONOLITHIC** means one model call, no follow-up turn, and the full
  LinkML schema sent with the prompt and the concatenated documents.
  **MULTI-PHASE** means several model calls or a follow-up turn. **SINGLE-CALL
  (schema digest, not monolithic)** means one call that sends a schema digest
  instead of the full schema.
- **prompt-level hybrid** means the prompt body tells the model to open
  `.claude/...` files that the API request never carries (#4014). The API
  model is then told to follow a procedure it cannot see. This is about the
  text, not the run.
- **runtime hybrid** means an API run part of which is done by a native agent.
  It reads `no` when every native continuation sits in a gated package and
  every setter that can reach N is gated or agentic; `possible` when a
  continuation has no gate or a setter that can reach N has neither. An API
  run that reached N itself would stop at the audit (`build_phase` refuses
  it, and `execute` refuses renderers 19-23 today), not become a hybrid. One
  condition name rendered by an agentic runtime is two procedures, not a
  hybrid run.

When the section says that no live condition is MONOLITHIC, "api" in the
code no longer has the owner's meaning. Record that in the PR. A real
monolithic arm needs a new condition or method directory, a canary, and the
owner's approval before anything is billed.

## Limits

- A token list finds what it names. A project fact phrased without any listed
  token, such as a participant count or a site name, is invisible. Add
  tokens when a review finds one.
- Context classification is heuristic for Markdown and YAML.
- Data flow is followed inside a function through assignments and across
  imported functions and constants; a call's arguments are followed for the
  constants they pass, not for the functions that compute them, and a method
  on an object (`self.render()`) is not resolved. A model-facing module
  outside `MODEL_FACING_MODULES` whose text reaches a model only through
  another module's variable is classed by its role, not traced.
- A native continuation is recognised by `RunSpec.from_render_spec`; a
  controller that rebuilds a parent's spec field by field is recognised only
  through its renderer setter. The runtime of a setter is read from its call
  or dict, else from every runtime its module names.
- The runtime-hybrid verdict associates a continuation or setter with a gate
  by controller package (directory), not by call path. The report names every
  setter, continuation and gate so a reviewer can confirm the path.
- A file a text names is followed when the text is a playbook, an agent, an
  assistant instruction or a controller. A note or guide they name is
  scanned, but what it names is not followed; nor is what `CLAUDE.md` names
  (it is a developer guide for the whole repository). Templated paths
  (`{PROJECT}`), `data/` and `tests/` are not followed.
- Evaluation is out of scope: evaluation modules and the rubric agents are
  listed, never gating.
- A nested `CLAUDE.md` is found under `src/`, `notes/` and `scripts/` only.
- Untracked or gitignored files are scanned when they exist under a
  discovered tree. The scanner does not consult `.gitignore`.
