---
name: d4d-generation-specificity-audit
description: Audit the D4D generation process (native agentic, interactive Claude Code sessions, API, GitHub assistant, shared schema, deterministic arms, run controllers, legacy scripts) for text or code hardcoded to a Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program or to biomedical/clinical data (tracked), and report what "api" means in the code (monolithic or multi-phase, and whether any step of an API run is agentic). Use before or after changing anything in the generation path (prompts, playbooks, agents, CLAUDE.md, api_runner, schema, profiles, manifest handling, run controllers), before registering a new arm or condition, and when onboarding a non-Bridge2AI dataset. Offline, deterministic, no model calls.
metadata:
  category: audit
  requires_database: false
  requires_internet: false
  version: 1.8.1
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

- Needs only the standard library and PyYAML. Use the project's interpreter
  (`poetry run python`): the code is parsed with that interpreter's `ast`,
  and code it parses can need a newer Python (an f-string expression with a
  backslash parses only from 3.12). A Python file that does not parse stops
  the scan with exit 2 and is named with the interpreter; it is never read
  as a file with nothing that gates. The report names the interpreter. The
  scanner never imports or executes the generation code: the runner's
  tables are read with `ast`.
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
surface that cannot be read, a Python file under `src/`, `notes/` or
`scripts/`, or any Python surface, that does not parse, a derivation that
found nothing in the code ("not derived: ..."), or any unexpected error (the
traceback is printed). Do not read a `2` as a clean result, and a crash is
never a `1`.

The guard tests are `tests/test_generation_specificity_skill.py` and the
existing neutrality tests the scanner builds on:
`tests/test_neutral_generation_schema.py`, `tests/test_profiles.py`,
`tests/test_external_dataset_onboarding.py`. Run those too after changing a
generation surface. The skill's tests check that:

- the scanner sees: the self-test, and a token planted in a copy of a real
  surface under the role `discover()` gives it, including CLAUDE.md, the
  descriptions a session lists, a YAML comment a playbook's Read returns,
  and the controller text that reaches a model by data flow, a sentence in
  a constant that a model-text constant is built from included, and one a
  method call on such a constant puts in it from a top-level assignment
  (`D = PARTS.setdefault('d', POLICY)`, an assigned `append`);
- project-keyed tables, defaults, keys and arguments gate in run-shaping
  code (an `or` default, a value wrapped in `Path(...)`, an f-string or a
  `+` join, `click.Choice([...])`, a positional argument, `argv.append`, a
  regex or glob test, a `yield`), also in a workflow, a config, a JSON file
  and a shell script (an `if:`, `contains(fromJSON(...))`, a `case`, `[
  "$P" = X ]`, `--project X`, `${{ x || 'X' }}`, a per-project key, a
  settings `env` value, a hook `command` with or without JSON escapes); an
  exposed file gates only on the lines a session loads from it; a
  `__main__` block gates only where its module runs as a script, and a
  controller module runs as one only where something runs it, its own
  `__main__` block calling a launch or a command-line interface
  nothing else calls included;
- discovery finds every model client, controller and launcher (over `src/`,
  `notes/` and `scripts/`), every file a playbook, agent, loaded assistant
  instruction or controller names, the imports of every script they run,
  every CLI group they run, the deterministic arms and the upstream input
  from the code; an assistant instruction file nothing loads is not a
  surface;
- whether a registered native run loads what an interactive session loads
  is read from each launch's argv, and a launch is shown to pass a flag
  only where the flag is a literal element of the argv list it hands over
  as built: `--safe-mode` switches all of it off, `--bare` only the memory
  and the hooks; a flag a starred element would bring (a constant, a record
  field), a list built any other way (a concatenation such as `[...] + []`,
  a value wrapped in a call, a comprehension) and a name, attribute or item
  holding the list that is used any other way than to hand it on, that is a
  parameter, or whose binding a use may not see (an `if`, loop, `try`,
  `with` or `match` body the use does not share, a use before it) are not
  shown to switch anything off; a `--system-prompt-file` launch is a
  launch; the project settings and the hook scripts they run are found;
- the reason a PreToolUse hook gives a native run's model for a denial, and
  the classifier reasons that feed it, are model text, whether the
  controller sets the field as a dict entry, by item assignment, `+=`,
  `.setdefault()` or `.update()`, or from a local;
- the "api" section agrees with the runtime: the CLI default condition, the
  condition the GitHub assistant runs (a non-literal `--condition` is "not
  derived"), the default renderers, the audit floor, the renderers
  `api_runner.execute` refuses, which conditions make each follow-up turn,
  and what a `tuned` instruction carries; a monolithic runner is reported
  monolithic; a renderer is read in any spelling; each derivation fails
  loudly when the code changes shape;
- optional helper turns retain their actual imported model-call phase and source
  location, validated RunSpec option/default/API-renderer restriction, and positive
  caller guard. They appear separately from default-condition follow-ups. Unknown
  or compound selectors, unbound/shadowed imports, missing or mismatched phases,
  else-branch or unguarded calls, and unsupported helper indirection fail closed;
- a violation is exit 1, a clean scan 0, and a scan that did not happen 2,
  including a Python file that does not parse.

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
- What Claude Code itself loads into a session: `CLAUDE.md`,
  `CLAUDE.local.md`, `.claude/CLAUDE.md`, `.claude/settings*.json` and the
  hooks they run, and the name and description of every command
  (`.claude/commands/**/*.md`), agent (`.claude/agents/**/*.md`) and skill
  (`.claude/skills/*/SKILL.md`): the frontmatter `name` and `description`,
  else a command's first line. The runtime's rule, not the repository's.
- The entry points: `.claude/commands/d4d-*.md` are the playbooks,
  `cli/download.py` is the `d4d download` group, `d4d-agent.yml` is the
  `@d4dassistant` workflow, and `.github/workflows/d4d_assistant_*.md` are
  the assistant instruction files (a glob that finds them; each is a surface
  only where the workflow, a playbook or a loaded instruction loads it).
  `d4d-full-core.md`'s CLI groups seed the closure that the arms and
  launchers are excluded from; every playbook's, agent's and instruction's
  groups are followed.

| approach | gates | discovered from |
|---|---|---|
| `native_agentic` | yes | `.claude/commands/d4d-*.md`; every playbook or agent that a playbook, a live condition prompt, a run controller or a loaded assistant instruction names, by path, bare name (`d4d-validator`) or slash command (`/d4d-full-core`), followed through the playbooks and agents they name (model-facing); every other file `agentic_runtime.toolchain()` hands a native run (it lists `*.md` in `.claude/commands` and `.claude/agents`, read with ast) is `exposed`; every other file those texts name by path or run (`python x.py`, `python -m mod`), with the namer's status (a named YAML is read raw, so its comments count); what each script they run imports (`src/html/human_readable_renderer.py` reaches `data_sheets_schema.rendering.human_readable_renderer`); the import closure of `agentic_runtime`, of every CLI group they run (`d4d utils status` from `/d4d-agent`; a group only an exposed agent runs is exposed), and of the package modules the run controllers import |
| `interactive_session` | yes | what Claude Code loads into a person's session in a checkout, where the `/d4d-*` playbooks run interactively: the project memory (`CLAUDE.md`, model-facing), the project settings (run-shaping; read as code, so a project value in their `env` block gates) and the hook scripts they run (and what those import), and the name and description of every command, agent and skill, model-facing on those lines while the body is exposed. The report states, from each registered native launch's argv, whether every one is shown to pass `--safe-mode`; where one is not, the surfaces it is not shown to switch off are also `run_controllers` surfaces (`--bare` switches off the memory and the hooks, not the command, agent and skill descriptions). Today none of the four is: each takes its flags from a starred module constant or record field, which the sound rule does not follow (#4156), so every session surface counts in `run_controllers` too |
| `api` | yes | the import closure of `cli/api.py` and `api_runner.py`; every condition in `api_runner.CONDITION_PROMPTS` (the newest `generic_vN`, the CLI default and the condition the GitHub assistant runs are **live**, the rest **historical**); the `tuned` components `resolve_prompt` inserts (`d4d_tuned_arm_prompt.md` is only hashed and named in a header, so it is run-shaping); evidence protocols (newest live); every file pinned in `canonical_hashes.yaml` |
| `github_assistant` | yes | the `@d4dassistant` workflow `d4d-agent.yml`, every file it names or runs (an instruction it hands a model is model-facing, the rest run-shaping: the deterministic config, `.github/ai-controllers.json`, the schema it validates against), the condition its `d4d api run` runs, and an assistant instruction file only where the workflow loads it (today none: the workflow runs `d4d api run` and loads no instruction file). The runner it starts is the `api` approach |
| `shared_schema` | yes | the import closure of `data_sheets_schema.yaml` and `data_sheets_schema_core.yaml`, the schemas `agentic_runtime.toolchain()` hands a native run, and the hand-kept files above |
| `deterministic` | yes | the arm commands: every CLI group outside the generation closures that names the bundle of an arm in `cli/api.py` `ARMS` other than the default one (today `cli/healthsheet.py` and `cli/rocrate.py`), and their import closure, followed through `data_sheets_schema`, `src.*` and the directories the code puts on `sys.path` (`setup_repo_imports` adds `.claude/agents/scripts`) |
| `run_controllers` | yes | under `notes/`: every module (not a probe, not on an evaluation path) that uses a generation builder as code (`RunSpec`, `build_phase`, `phase_instruction`, `prompt_body`, `resolve_prompt`, `playbook_text`, `digest_text`, `assembly_digest`); under `scripts/` or `src/`, outside the generation closures: a module that uses one and launches a run (calls the runner's `execute`, or hands a native runtime `--system-prompt`); every `notes/` or `scripts/` module they import or pin by file name; every module that runs one, to a fixed point; the Markdown a controller names beside itself (`system.md`, model-facing); every file a controller names in its literals; and every interactive_session surface a registered native launch is not shown to switch off. A controller module runs as a script (its `__main__` block counts) only where something runs it: an argv (`[python, '-m', 'audit_controls.contract']`, a worker relaunching itself through `__file__`), a document beside it or a module docstring (`python -m audit_controls.native`), no module importing it (an entry point), or its own `__main__` block calling a module function that launches a run (an argv with a system prompt or a system-prompt file, the runner's `execute`: `run_native_canary.py`, `run_api_canary.py`) or a command-line interface (argparse, click) that nothing else calls (`prepare_registration.py`) |
| `legacy_monolithic` | yes | every module under `src/` or `scripts/`, outside the generation closures, that calls a model client and names D4D or a datasheet (not an evaluator); the pre-runner helpers in `src/download` (the name glob); `d4d_concatenated_*.txt`; every prompt set beside the conditions (`src/download/prompts/*/` other than the tuned components) |
| `shared_input` | no | the `src.download` modules the `d4d download` group imports (download, preprocess, concatenate) and the `src/download` modules they import: upstream of every approach, and where a closure stops |
| `other_model_client` | no | a model client outside generation and outside every generation closure: under `notes/`, one outside the controller set (diagnostic probes, transports); the `notes/` evaluation modules a controller imports or that import one, and their imports; under `src/` or `scripts/`, an evaluator or a client that names no D4D record. An evaluator a generation closure reaches is that approach's surface and gates there: `evaluation/evaluate_d4d_llm.py`, which the controller `prepare_registration.py` imports from the package, is in the native closure |

A module is a model client when it imports `anthropic`, `openai`,
`pydantic_ai` or `aurelian`, or calls `*.messages.create|stream`,
`*.chat.completions.create`, `*.responses.create`,
`openai.ChatCompletion.create` or an agent's `run`/`run_sync`. Imports and
calls are read from the code, so a comment that mentions one does not count.
Registered byte copies under `registrations/` are frozen evidence and are not
read. The report's "How the surfaces were found" section lists the toolchain,
every controller with the reason it was found and how it runs as a script,
every model client with its classification, the assistant instruction files
and what loads each, every named file and who names it, what the scripts they
run import, the CLI groups they run, the interactive-session evidence with
each registered launch's flags, the deterministic arm commands and the
upstream input.

### Roles

A file has a role in each approach that reaches it: `model_facing` (its text
reaches a model), `run_shaping` (decides what runs) or `exposed` (available
to a native or interactive session, named by nothing live). Each approach
judges a hit by its own role:

- text (a string literal, prose, an example, an instruction, a value) counts
  where the role is model-facing, and on the lines an approach loads whatever
  the role: the name and description a session lists of an exposed command,
  agent or skill;
- a YAML comment counts where the model reads the file raw: a playbook,
  agent, loaded instruction or controller text names it for the model to
  Read (the Read tool returns comments), and the schemas the toolchain hands
  a native run. A schema module only the digest renders drops its comments;
- in run-shaping code, a string literal counts as text when it is model
  text: the body of a run-controller function named for it (`render_*`,
  `*instruction`, `*_system`, `*prompt*`), or code found by data flow. From
  every argv element after `--system-prompt` or `--append-system-prompt` (or
  the value its `=` spelling carries) in a controller, from every value a
  controller gives a hook field Claude Code shows the model
  (`permissionDecisionReason`, the reason a PreToolUse hook gives for a
  denial, and `additionalContext`) under a literal key, as a dict entry, a
  keyword argument (`dict(...)`, `.update(...)`), an item assignment (plain,
  annotated or `+=`) or `.setdefault()`, and from those functions' return
  values, the flow follows local assignments, marks a literal that becomes
  part of the text, a function whose result does (and follows its returns in
  turn, across imports) and a module constant the text is built from
  (`SYSTEM`, which `render_system` returns). A constant so marked is
  followed in turn: every write of it at the top of its module is model
  text, and so is what that write puts in it, recursively and each
  constant once. A write is a top-level assignment to it (plain, annotated
  or augmented, or to an item or attribute of it), with its value, and any
  method call whose receiver holds it, wherever a top-level statement makes
  one on import (alone, in an assignment's value such as `D =
  PARTS.setdefault('d', POLICY)`, in another call's argument, in a
  condition or a block's body), with the call's arguments: any method can
  change the object it is called on. What a write puts in it is followed:
  the constants it names, of its module or imported by name (`POLICY` in
  `SYSTEM = POLICY + '...'`), the functions whose results become part of
  it, its literals. A hook field built from its function's parameters,
  directly or through its locals (`hook_output(classification, basis)`),
  is fed through threads and queues no data flow follows, so the
  classifiers that feed it are found by their decision: every controller
  function that returns a tuple whose decision element is a literal the hook
  function compares its decision parameter with (`'prescribed'`), widened by
  the other decisions such functions return (`'not_prescribed'`); the
  element in the reason's position is model text. Today that finds, among
  others, the `SYSTEM` constants of the audit and finalization preparers,
  `command_guidance` and `lookup_guidance`, the deny-reason text in
  `hook_output` and the reasons of the command, file and audit-validator
  classifiers;
- a code branch or table counts unless the role is exposed, in Python and in
  a YAML, config, JSON or shell file that no approach hands to a model
  (below);
- nothing in a `__main__` block counts for an approach that only imports the
  module (it never runs that block). A run-controller module runs as a script
  only where an argv, a document, nothing importing it, or its own
  `__main__` block (calling a function that launches a run, or a
  command-line interface nothing else calls) says so; an import by another
  controller is not a run.

A hit is a violation when it is gc_project, has no exception, and some gating
approach counts it (`gates_in` in the JSON).

Tokens come from ONE source. The scanner parses `STUDY_IDENTITY`,
`STUDY_DESIGN` and `PROSE_ONLY` out of `tests/test_neutral_generation_schema.py`
and adds the extensions in `tokens.yaml`. Add a new token to `tokens.yaml` (or,
for schema text, to the neutrality test) rather than to `scan.py`.

Every hit is classified by context:

- `.py`: `string_literal` (a model-facing candidate), `code_branch` (a
  comparison, a `match` case, or a test call on the value: `startswith`,
  `endswith`, `re.match`, `re.fullmatch`, `re.search`, `fnmatch`),
  `code_table`, `docstring`, `comment`. A `code_table` is a bare-token
  string (no whitespace) in a table, default, key or argument position: a
  dict key or value; a value assigned anywhere (a module constant, a
  function local, an attribute); a loop or comprehension iterable; a keyword
  or positional argument of any call (`argv.append("X")`, `run("X")`, a
  decorator's `click.Choice([...])`); a parameter default; a returned or
  yielded value; a subscript key. The whole value is read, so a bare token
  anywhere inside it counts: in a collection, in a call's arguments
  (`frozenset({...})`, `Path("data/X")`), as an `or`/`and` operand
  (`project or "X"`), an operand of `+`, `/` or `%`, an f-string's literal
  part, a method's object (`"X/{}".format(p)`) or a comprehension. A string
  with whitespace is text and stays a `string_literal`. Each physical line
  of a literal is its own unit, read from the tokens that spell it, so the
  parts of an implicitly concatenated literal are reported on their own
  lines; an f-string's parts too, from the tokens Python 3.12 gives them (an
  f-string with escapes, or under an older tokenizer, is reported from its
  first line).
- `.md` and `.txt`: `instruction`, `example`, `prose`, `frontmatter`, or `header`.
  `header` is text above `## Prompt body` in a condition prompt; `prompt_body()`
  never sends it.
- `.yaml`: `prose` (description/title/comments), `example` (under the
  `examples` or `annotations` metaslot), `value`, `comment`. A key directly
  under `attributes:`, `slots:`, `classes:` and the like is an element's
  name, so a slot *named* `examples` is not the metaslot.
- A YAML, `.config`, JSON or shell file that no approach hands to a model
  and some approach runs on (a workflow, the assistant config, the prompt
  pins, the project settings, the assistant's allow-list, a `.sh` script)
  also has code: `code_branch` for a GitHub expression's compared literal
  (`if: x == 'CM4AI'`, `contains(x, 'VOICE')`, also the JSON a `fromJSON`
  inside the test parses: `contains(fromJSON('["CHORUS"]'), x)`), a shell
  test's operand (`[ "$P" = "CHORUS" ]`, `[[ ]]`, `test`), an argument of an
  `if`/`while` condition, a `case` pattern, and a github-script string that
  is compared, a `case` label or an argument of `.includes` and the like;
  `code_table` for an expression default (`${{ x || 'CHORUS' }}`), any
  other `fromJSON` literal, a shell default (`${P:-CHORUS}`), assignment,
  long option value (`--project CHORUS`) or `for` list, a github-script
  string assigned or used as an object value, array item or default, a bare
  key (`CM4AI:`) or bare value of the data, and a JSON key or a JSON string
  value with no whitespace (`"D4D_MANIFEST": "data/CHORUS_manifest.yaml"`);
  a JSON hook `command` is read as shell, as the shell gets it: its JSON
  escapes (`\"`, `\\`, `\n`) are decoded first, a decoded line break starts
  a new shell line, and each span is mapped back to the text as written. A
  value with whitespace stays text, a key that is a file path (the pin
  registry's) is a key, not a table, and a prose key keeps its prose. Every
  `.sh` line is read this way.

## Read the report

1. **Self-test line.** It must say `passed`. The self-test plants one token per
   category in a Markdown file, and in a Python file a branch, a comment, a
   dict key, a `frozenset` constant, a lookup default, a keyword argument, a
   loop tuple, an `or` default, a value wrapped in `Path(...)`, a regex
   test, a string literal, an implicitly concatenated literal and a
   triple-quoted block. It checks each is found with its category (Markdown)
   or context (Python) on the line where it was planted.
2. **Surfaces table and "How the surfaces were found".** Check that the file
   counts and violations per approach are plausible and that the controllers,
   named files and model clients listed are what you expect. A zero means
   discovery broke. The interactive-sessions bullet says that registered runs
   are unaffected only when every registered native launch is shown to pass
   `--safe-mode`; otherwise it names the launch and why it is not shown,
   says whether it is shown to pass `--bare` (which switches off only the
   memory and the hooks), and the session surfaces it is not shown to switch
   off count in `run_controllers` too.
   The controller table says how each controller runs as a script, or that
   it is imported only.
3. **gc_project violations.** These are the findings that fail the run. A
   violation is a Grand Challenge name, site or identifier in model-facing
   text, or in a code branch or table, that a gating approach counts, with no
   exception. The approach column says which.
4. **Tracked categories.** Counts per category and approach. The second table
   lists model-facing or code-level tracked hits that have no recorded reason.
   That table is the triage queue.
5. **gc_project hits that do not fail.** Comments (outside a file the
   model reads raw), docstrings, headers, run-shaping literals, `__main__`
   blocks of imported modules, exposed files (outside the lines a session
   loads), non-gating approaches and excepted hits. Skim it for anything
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
  auto-loaded file is an owner decision. So is a project name in the
  description of a command, agent or skill, which every session lists:
  replace it with a neutral placeholder.
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
- Direct imported helpers in the runner's package import closure are also read
  for calls to that same runner wrapper, resolving function/module aliases and
  literal helper phase constants. Optional turns must agree with the plan and
  have an exact positive `if spec.<option>` caller guard. A recognized option has
  an annotated integer RunSpec field with default zero and unconditional raising
  validation of its finite integer domain and API-only renderer restriction.
  The JSON records the selection and call-path evidence; Markdown lists the
  option, default, runtime and renderer. Default condition shapes/lists exclude
  these opt-in turns. A direct positive opt-in block in RunSpec may additionally
  refuse `self.condition not in <declared set>` with an unconditional raise.
  Its exact nonempty literal module set, bound once and used only for membership,
  restricts the optional condition rows; renamed sets are derived from their
  values. The JSON retains the condition set and source evidence. Shadowed or
  mutated sets/spec conditions, compound predicates, else-branch restrictions,
  and unknown or nested guards fail closed (#4275). Calls to other validators
  are not interpreted as condition declarations. An unconditional raise or
  assertion in the initializer or positive opt-in body is not a proved
  admissible path and is refused (#4279). This bounded derivation does
  not assume arbitrary compound
  selectors, helper delegation or nested dead functions are equivalent; changed
  shapes stop with “not derived” until explicitly supported and tested (#4263).
- The guard in `build_phase` that raises on `render_version >= N` and
  `phase == "audit"`, in either order, gives the renderer from which the
  audit is a registered native batch. RunSpec's `render_version not in
  (...)` refusal gives the renderers it admits, and the raising test at the
  top of `api_runner.execute` the renderers it refuses before it runs.
- `RunSpec`'s `render_version = A if is_agentic else B` gives the default
  renderers, and the assignment under `if condition is None:` in
  `cli/api.py` gives the condition `d4d api` runs when given none;
  `d4d-agent.yml`'s `d4d api run` gives the condition the GitHub assistant
  runs: its literal `--condition` in any spelling, else, when it passes no
  `--condition` at all, that default. A `--condition` whose value is not a
  literal condition name (`"${{ inputs.condition }}"`, `$CONDITION`) is
  chosen when the workflow runs, so it is "not derived" (exit 2), never
  reported as the default.
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

- Recall of what reaches a model is not complete, and enumeration cannot
  make it so: each review of this skill found a channel the scan before it
  did not read (the descriptions a session lists, a YAML comment the Read
  tool returns, the reason a hook gives for a denial, a project default in
  a form the code reading did not know). A clean scan means that no listed
  token was found on a channel the scanner reads, not that no project text
  reaches a model. Channels known not to be read: what a process prints or
  writes for a model to read outside the hook fields below (a tool's output,
  a file a run writes and a later phase reads, a hook's stderr), environment
  variables a launcher sets in code, files a run reads that no text names,
  network responses, and the model's own earlier turns.
- A token list finds what it names. A project fact phrased without any listed
  token, such as a participant count or a site name, is invisible. Add
  tokens when a review finds one.
- Context classification is heuristic for Markdown, YAML, JSON and shell. A
  shell line is read on its own (with the state a `case` or a multi-line
  condition needs), so text inside a multi-line quoted string is read as
  commands. JSON is read line by line: a key and its value on separate lines
  are not paired, so a hook `command` split that way is read as text, not
  shell. Tokens are matched in the JSON as written, so a token spelled with
  a `\u` escape is not found. A Python value is read whole for bare tokens,
  so a project name passed to `print` or a logger as a bare token gates as
  code in run-shaping code; one inside a sentence stays text.
- The CLI package (`cli/__init__.py`) imports every group: a closure that
  reaches it stops there, and a group is followed where a playbook, agent or
  instruction runs it (`d4d <group> ...`). A group a controller's text names
  is not followed as a group; the package modules the controllers import
  are, through the native closure.
- A Python file a text names without running it is judged as run-shaping
  code; its comments and docstrings are not counted even if the model reads
  it.
- A registered launch is a list or tuple literal in a run controller that
  holds `--system-prompt`, `--append-system-prompt` or either's `-file`
  form, also as `--flag=value`; an argv that hands a native runtime
  neither (`claude -p` with the prompt on stdin) is not found, and a
  launch flag outside a list or tuple literal (an argv built by `.append`
  calls) is a launch whose flags cannot be read. Whether it passes
  `--safe-mode` (or `--bare`) is sound by construction (#4156): it is
  shown only where the flag is a literal element of that list, and the
  list is shown to be what the launch hands over, as built. That is so
  where the list is a call's argument itself, in a call whose value
  nothing keeps (a statement of its own, a `with` item); a value returned
  or yielded as it is; or the whole value of a plain or annotated
  assignment, in a function, to one name, or to an attribute or
  literal-key item of a name (`argv`, `self.argv`, `job['argv']`), where
  that assignment is the holder's one binding in the function and comes
  before every other use of it in the same statement list (each use sits
  in a statement that follows it there, at any depth, so the binding runs
  on every path to it), a name holder is not a parameter (#4166), and the
  function, nested functions and classes included, otherwise only hands
  the holder on whole (a direct argument of a call, a returned or yielded
  value) or reads it (a comparison, an f-string), with the name that holds
  an attribute or item held to the same rule. Everything else is "not shown",
  never "switches them off": a flag a starred element would bring (a
  module constant, an imported constant, a record field, a sum, a
  comprehension: `*CLI_FLAGS`, `*overlay['cli_flags']`), which is why none
  of the four registered launches is shown today; a list built any other
  way (a concatenation such as `[...] + []`; a call's argument where the
  call's value is kept, since that call may build the list launched, `argv
  = list([...])`, and so `proc = Popen([...])` too; a comprehension, a
  conditional, `or`, an augmented assignment, unpacking, `:=`, `yield
  from`); a list bound at module level or in a class body, bound to
  several targets, or held by something else (`self.cfg.argv`); a holder
  that is a parameter of the function, or whose binding a use may not see,
  because the binding sits in an `if`, loop, `try`, `with` or `match` body
  the use does not share or comes after the use (`def go(argv, enabled):`
  that rebinds `argv` only when `enabled`; an existing `self.argv` or
  `job['argv']` rebound that way, also where the function hands `job` on
  whole; #4166); and a holder used any other way (a method or attribute of
  it, an item or slice of it, `del`, `+=`, any other binding of the name
  by any statement, `global` or `nonlocal`, an alias, a star). Not read:
  what the code the list, or the object holding it, is handed to does
  with it (a callee that changes the list it is passed, or returns a new
  list that the function changes and launches in its place, `cmd =
  list(argv)`; a caller that changes a list a function returns); other
  code that holds that object meanwhile (another thread, a callback); code
  that reaches the function's names dynamically (`exec`, `eval`, frame
  objects); and how the command line parses the list: an element spelled
  `--safe-mode` is read as the flag even where the option before it takes
  it as its value (`'--name', '--safe-mode'`) or it follows `--`. "Has no
  `--safe-mode` element" (`carries` False) means the list is shown and
  holds neither the literal nor a starred element; a name or a call among
  its elements is read as some other argument. Only `--safe-mode` is read
  as switching off the command, agent and skill descriptions; `--bare`
  switches off the memory and the hooks, since its help says skills still
  resolve. A launch's
  `--add-dir`, `--settings`, `--agents` and `--setting-sources`, which can
  hand a run context explicitly, are not read.
- A controller module that another module imports runs as a script only
  where an argv, a document or docstring, or its own `__main__` block says
  so: a block that calls a module function launching a run (in that
  function or one it calls), or a command-line interface (argparse, click)
  nothing outside the block calls (tests are not read). A module whose
  `__main__` block does something else, with nothing else saying it runs,
  is judged as imported.
- Data flow is followed inside a function through assignments and across
  imported functions and constants; a call's arguments are followed for the
  constants they pass, not for the functions that compute them or the
  literals they pass, and a method on an object (`self.render()`) is not
  resolved. A module constant marked as model text is followed through its
  writes at the top of its module, recursively (#4156): its top-level
  assignments, and every method call whose receiver holds it wherever a
  top-level statement makes one on import, with the call's arguments
  (#4166). Not followed: an assignment to it inside a block there (`if`,
  `try`) or in a function (`global`), a method call on it in the body of a
  function or lambda, a function it is handed to (`register(C, v)`), a
  write through another name bound to it or to part of it (`X = C`, then
  `X.append(v)`), a constant reached as a module or class attribute (`m.C`,
  `Cls.C`) or re-exported through another module, and one bound only by
  unpacking. A model-facing module outside `MODEL_FACING_MODULES` whose
  text reaches a model only through another module's variable is classed
  by its role, not traced.
- Hook output is read in run controllers from the two fields Claude Code
  shows the model, `permissionDecisionReason` and `additionalContext`; a
  hook's stderr when it exits 2, the `reason` of a `decision: block` and
  what the session's own hook scripts print are not traced. A field is
  found where a controller writes it under a literal key: a dict entry, a
  keyword argument, an item assignment (plain, annotated or `+=`) or
  `.setdefault()`. One written under a key held in a name (`out[REASON] =
  ...`), through `setattr` or an attribute, or from a list of pairs
  (`dict(zip(...))`) is not found. The classifiers that feed a deny reason
  are found by their decision literal and by the reason's position in the
  pair they return (the reason parameter read in the field's value directly
  or through the hook function's locals, and the decision parameter where
  the hook function compares it); one whose decision is not a literal in a
  tuple it returns is not found, and every return of a classifier found is
  read as a reason, including one that never reaches the hook.
- A native continuation is recognised by `RunSpec.from_render_spec`; a
  controller that rebuilds a parent's spec field by field is recognised only
  through its renderer setter. The runtime of a setter is read from its call
  or dict, else from every runtime its module names.
- The runtime-hybrid verdict associates a continuation or setter with a gate
  by controller package (directory), not by call path. The report names every
  setter, continuation and gate so a reviewer can confirm the path.
- A file a text names is followed when the text is a playbook, an agent, a
  loaded assistant instruction, the `@d4dassistant` workflow or a
  controller. A note or guide they name is scanned, but what it names is not
  followed; nor is what `CLAUDE.md` names (it is a developer guide for the
  whole repository), so an assistant instruction file only `CLAUDE.md` names
  is not a surface. Templated paths (`{PROJECT}`), `data/` and `tests/` are
  not followed.
- Evaluation is not exempt for being evaluation. An evaluation module is
  `other_model_client` (listed, never gating) only where no generation
  closure reaches it: `evaluation/evaluate_d4d_llm.py`, which the controller
  `prepare_registration.py` imports from the package, is in the native
  closure and its code tables gate there; and every agent's name and
  description, the rubric agents' included, gates in `interactive_session`
  (`d4d-review-record.md`'s does today). An agent's body gates only where a
  live text names the agent.
- A nested `CLAUDE.md` is found under `src/`, `notes/` and `scripts/` only.
- Untracked or gitignored files are scanned when they exist under a
  discovered tree. The scanner does not consult `.gitignore`.

## Offline prompt drafts (#4293)

`offline_draft` separately scans the explicitly listed source-heading prompt-text
builder as model-facing instruction text. It gates specificity findings without
claiming that a live condition calls it or that a provider received its output.
Its declared source file must exist and parse. Source/evidence payloads supplied
to a draft remain data, and rendered-supplement tests separately check that their
project identities and quotations do not enter the neutral instructions. The
live `api_runner.sent_text_surfaces()` inventory remains unchanged.
