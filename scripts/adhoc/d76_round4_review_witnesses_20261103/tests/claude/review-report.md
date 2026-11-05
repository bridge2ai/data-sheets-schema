# PR #5213 D76 round-3 re-check at `d13c1711e` (Claude reviewer), 2026-11-02

A read-only, adversarial re-check of `d13c1711e19dcdcc7f624b66e15b735ebc0aab8f`, following
`plans/codex_logs/prompts/2026-11-02-5213-round3-recheck.md` (Claude column). I have not read
the Codex reviewer's round-3 report.

**Where everything ran:**
- **The head:** the detached checkout `d4d-executions/review-5213-d13c1711e`. It is clean
  afterwards, including ignored files; see "Side effects".
- **Failing-before runs:** pinned `git archive` copies of `0fa106e4d` and `87a8e7a80`, under
  `scratch-5213r3check/claude/trees/`. That is two copies; the head used its checkout.
- **Scratch:**
  - probes and scripts in `scratch-5213r3check/claude/scripts/adhoc/`;
  - logs, JUnit and `/usr/bin/time` output in `claude/logs/`;
  - basetemps in `claude/bt/`.
- **How pytest ran:** serially. There is no GNU `timeout` on this Mac, so a `perl alarm()`
  wrapper (`run_bounded.sh`) bounded every pytest run: 3,600 s, or 1,800 s per SG2 node.
  Nothing timed out.
- **No** repository edits, commits, checkout, reset, stash, clean, push, `gh`, network,
  provider calls or @-mentions.

## Verdict: ready after changes

Round 3 closes what round 2 left open:
- **The guard's anchor** survives every ordinary mutation route I tried:
  - `object.__setattr__`, `copy` and `deepcopy`, and `pickle`;
  - a subclass that skips `__post_init__`;
  - `str` and `PurePath` subclasses that lie;
  - mirror replacement, selector flips, and the round-2 private rewrite.

  Each refuses before authority, lock, date recovery or the client, in both resume modes.
- **Recorder counterparts** can no longer select another file.
- **The relative-instruction case**, including the root, is now recorded as "asserted".
- **The roster** is closed over every field.
- **Each CLI entry** guards before its authority check and its writes.

Three things still need a change or an owner decision:

1. **R3-1:** "verified" can be written for bytes the run never read.
2. **R3-2:** to admit the guard, the change adds about 960 lines to the generation-specificity
   scanner, and they encode this PR's function shapes.
3. **R3-3:** the SG2 deadline wrapper makes three ordinary tests depend on a clean, full git
   checkout.

The integration with main (R3-4) needs a stated order: "D68 → D76 → D69" cannot hold as
written.

## Findings

### R3-1. Minor (P2): `hash_basis: verified identical to the bytes consumed` certifies a path, not bytes
- **Where:**
  - `src/data_sheets_schema/cli/provenance.py:820`, where `input_verified` is set from
    `instruction_admitted` and `_record_absolute_input_declarations(...)`;
  - `:968-985`, which only checks that the instruction text names absolute bundle and chunk
    paths;
  - `src/data_sheets_schema/provenance.py:1768`.
- **Witness** (`test_r3_verified_basis.py`, `claude/logs/q2-verified-head.log`):
  - **Setup:**
    - render the agentic instruction in a subdirectory, which gives absolute spellings;
    - append a line to the bundle **in place** (same path, same inode);
    - record with the exact instruction and `--run-date`.
  - **Result:** exit 0, with `hash_basis: verified identical to the bytes consumed`.
  - **The attested md5 is not the md5 the run read**, and `unverified` lists only
    `model.reasoning_effort`.
  - **Controls:**
    - unchanged bytes give "verified" with matching md5;
    - a root render (relative spellings) gives `asserted …`, with
      `inputs.bundle_md5`, `inputs.chunks.sha256` and `inputs.source_manifest.md5` under
      `unverified`, as intended.
  - **At `0fa106e4d`:** all three say "verified", so the relative case is fixed and the
    absolute case is unchanged.
- **Why:** an absolute spelling bound by the instruction proves which *file* the run was told
  to read, not its bytes at that time. The brief's own criterion ("an absolute spelling the
  instruction binds") is weaker than the wording it licenses.
- **Cheap fix:**
  - **Use the chunk manifest as byte evidence.** The instruction also binds the chunk manifest,
    and that file records the bundle digest the run chunked. Write "verified" only when the
    bound chunk manifest's `bundle_md5` equals the hashed bundle, or when a run-written digest
    (the native job's `input_identity`, or a ledger pin) does.
  - **Otherwise** write the "asserted" basis and the `unverified` rows.
  - **In my witness,** `inputs.chunks` is already `null` because the manifest's md5 no longer
    matches. That mismatch is exactly the evidence the basis ignores.

### R3-2. Major (scope/process; needs an owner decision, not a correctness defect): the specificity scanner was taught this PR's code shapes
- **Where:** `.claude/skills/d4d-generation-specificity-audit/scan.py:14089` onward, from
  commits `3dd6479b4` and `939c50146`. About 960 added lines.
- **What it adds:** `_PREFIX_IDENTITY_GRAMMARS` with nine "source-role grammars": `guard`,
  `lookup`, `remember`, `spellings`, `capture`, `replay`, `copy`, `deepcopy` and `predicate`.
  - **They are alpha-renamed** (identifier-agnostic), but they replicate the control flow of
    `_require_registered_input_spellings`, `_input_binding`, `_remember_input_binding`,
    `_freeze_input_binding`, `RunSpec.__copy__` and `RunSpec.__deepcopy__` statement by
    statement.
  - **Why they exist:** the scanner's prompt-adaptation proof expected `resolve_prompt` to begin
    with `body = prompt_body(spec.base_prompt)`. Round 3 put the guard first (`api_runner.py:1484`),
    and 28 tests in `test_generation_specificity_skill.py` failed.
- **Why it matters:**
  1. **Scope.** The round-3 brief (lead) lists production as four `src/` files plus CI weights,
     and "the rest" as tests, notes and helpers. This is a generality guard, changed to admit
     this PR. The PR note does disclose it, at `pr5213_d76_pr_note_2026-10-31.md:143-158`.
  2. **The owner's rule** (2026-10-28) is "no specific interventions unless part of a
     generalized approach". The grammar is structurally specific to D76's binding.
  3. **Lock-step coupling.** Any later change to the guard or binding (R3-1's fix, for
     example) must update the scanner grammar too, or about 28 specificity tests fail.
- **Soundness:** I did not audit the 960 lines. The author's R1–R7 adversarial ledger exists.
  The specificity module passes 357/357 per the author; I did not rerun it.
- **Simpler alternative:**
  1. Keep `resolve_prompt` unchanged and move the call to `RunSpec.instruction`, the cached
     property at `api_runner.py:1147`, which renders through `resolve_prompt`.
  2. Every other public entry (`plan`, `execute`, the CLI entries) already guards before
     rendering.
  3. Revert the scanner change.

  Alternatively, keep it and split it into its own PR, with an explicit owner decision under
  the generality rule.

### R3-3. Minor (test infrastructure): the SG2 wrapper ties three ordinary tests to a clean, full git checkout and to a dated review harness
- **Where:**
  - `tests/test_wave7_5213_d76_registration.py:53-97`, which runs
    `scripts/adhoc/run_d76_sg2_case_20261102.py` under `scripts/adhoc/d76_process_deadline_20261102.py`;
  - the child, which calls `d76_suite_common_20261031.source(ROOT)` and refuses unless every
    tracked file equals `HEAD` (`run_d76_sg2_case_20261102.py:91-93`).
- **Witness** (`sg2_child_preconditions.py`, `claude/logs/sg2-preconditions.log`):
  - on a non-git pinned copy, `source()` raises `CalledProcessError` (not a git repository);
  - on a temporary git repo, `tracked_exact` is `True` when clean and `False` after one
    uncommitted edit to a tracked file. The child then refuses: "SG2 child source must match
    its recorded commit".
- **Consequences:**
  - **A developer** running `pytest tests` with any uncommitted change to any tracked file
    gets three spurious failures.
  - **A sparse checkout, a git archive or a source distribution** cannot run them.
  - **The `-S` bootstrap** assumes a `lib/pythonX.Y/site-packages` venv layout. CI's in-project
    `.venv` satisfies it; a conda or system interpreter would not.
  - **The mechanism is node-specific.**
- **What is good:** the failure mode is bounded with a clear message:
  `SG2 … exceeded the 1800-second subprocess deadline; retained log: …`.
- **Fix:**
  - keep a generic subprocess deadline in a non-dated test utility (`tests/` or `utils/`);
  - keep the source/origin attestation inside the review evidence runner only, enabled by its
    own environment variable;
  - or skip attestation when the tree is not a clean git checkout.

### R3-4. Low (integration, read-only): "D68 → D76 → D69" cannot hold as written at main `ddfd45c3b`
- **Where:** `git merge-tree --write-tree ddfd45c3b d13c1711e` gives tree `3f3451fa…`
  (objects redirected to scratch). Its conflicts:
  - `src/data_sheets_schema/api_runner.py`: one hunk, in `execute`;
  - `utils/ci_test_durations.json`.

  `cli/api.py` and `tests/test_profiles.py` merge cleanly.
- **Main's order** in `execute`:
  1. the replay, dry-run, renderer and native refusals;
  2. `_prelock_checks`, which runs `selection_check`, then `assert_current` and
     `require_selected_resume_owner`, then `refuse_legacy_execution`, then `prepare()`, then
     `refuse_legacy_execution` again;
  3. `guarded_launch(… _exclusive_run)`.

  `refuse_legacy_execution` (`latch_journal.py:132`) carries both the D68 never-spend refusal
  and D69's ownership inventory (`_legacy_evidence`). Main runs it *after* authority, on
  purpose ("Keep existing authority refusals ahead of D69").
- **What can hold:** D76's contract puts the guard before authority. So the order that
  satisfies both PRs at every entry is: the refusals, then **D76**, then `_prelock_checks`
  (authority → D68/D69 → prepare → D68/D69).
  - **In execute:** this is resolving the conflict hunk by keeping
    `_require_registered_input_spellings(spec)` immediately before `_prelock_checks(...)`.
  - **In batch:** the merged `cli/api.py:1087` already guards each spec before `_shared_current`
    and before `_prelock_checks(selection_check=…)` at `:1159`.
- **Nothing is skipped** for a spec that passes D76. A spec failing D76 never reaches D68 or
  D69, but it is refused anyway.
- **Literal "D68 before D76" is impossible** unless `refuse_legacy_execution` is split, or D76
  moves after authority, which would break D76's own contract.
- **Unverified:** main's new #5212 tests have not been run against D76's universal
  construction-origin requirement. Round 3 refuses *every* spec without a binding at
  `resolve_prompt`, `plan` and `execute`, registered or not (`api_runner.py:3121-3124`). A
  main test that builds a spec without `__init__` or `from_render_spec` would now refuse
  earlier.

### R3-5. Residual (documented honestly): hostile Python can still forge the anchor
- **Witness** (`q2-anchor-head`): writing a forged entry into `_REGISTERED_INPUT_BINDINGS`
  (with a matching mirror), or monkeypatching `_require_registered_input_spellings`, reaches
  authority, lock, date recovery and the client.
- **This is the documented residual:**
  - "an API invariant, not a security boundary against arbitrary Python that can rewrite this
    module or its registry" (`api_runner.py:509-513`);
  - the PR note.
- **The statement does not overclaim.**
- **Fail-closed registry changes:** `clear()` and `pop()` refuse.

## Checked and sound

1. **The recorder** (Codex 1, R2-1; Issues 7 and 8).
   - **Anchoring:** relative inputs are anchored to the recording cwd
     (`cli/provenance.py:450`, `:632-643`).
   - **Agreement:** a candidate is admitted only when `spec_agrees` matches the anchor's
     identity: resolved path, `lstat` dev/ino/mode, and target size/mtime/ctime (`:913-948`).
   - **The final record** is rechecked against the anchors, and the bundle md5 against the
     anchor (`:850-866`).
   - **Aliasing fails closed, and does not admit another file:**
     - a symlink (lstat inode differs);
     - a hard link (resolved paths differ);
     - `..` (excluded);
     - case or NFC/NFD aliases on APFS (`resolve()` keeps the spelling, so they differ).
   - **Witnesses:**
     - Codex's `test_owner_counterpart_cannot_select_a_different_file[True/False]`: **pass at
       head**; at `0fa` both fail with `WRONG_FILE_ACCEPTED`.
     - My cross-corpus witness: at head, R2-root and R2-nested both exit 0 with
       `asserted …` and the gaps listed. At `0fa` both said "verified".
     - My residual probes: (a) and (b) give `('match', None)` ×4; (c) is refused.
2. **The anchor** (Codex 2, R2-2; Issue 9).
   - **Refused, with client `[]` and no authority, lock or date call, both resume modes:**
     - `object.__setattr__`;
     - `copy` and `deepcopy` of a mutated spec;
     - `pickle` (no origin);
     - a subclass skipping `__post_init__` (no origin);
     - `str` and `PurePath` subclasses whose `__fspath__` or `__eq__` lies (exact-type
       refusal);
     - registry `clear`/`pop`;
     - mirror replaced by an equal tuple, `None` or a list;
     - selector flips;
     - the round-2 private rewrite;
     - my round-2 `test_r2_boundary_probes` (12/12; at `0fa` the same file shows the two spends).
   - **`dataclasses.replace(bundle=decoy)`** is refused at construction.
   - **Shared generation** also compares against the parsed registration's paths, at
     construction (`:550-566`) and at the guard (`:3162`).
   - **`id()` reuse:** no collision in 200,000 allocations (inconclusive empirically). By
     construction, `_input_binding` requires `weakref()() is spec`, and the weakref callback
     removes only its own entry, so a forged object at a recycled id has no binding.
   - **Codex's** `test_private_anchor_replacement_cannot_restore_spend[empty/replaced]` passes
     at head and fails at `0fa`.
3. **Entries** (Codex 3, R2-3; Issue 10).
   - **My own enumeration, done before reading the author's list:**
     - **library:** `execute`, `plan`, dry-run, `resolve_prompt` / `RunSpec.instruction`, and
       native `write_registration`;
     - **CLI:** `render-prompt`, `plan`, `run` and `batch`;
     - **others that build specs:**
       - `provenance record` (fresh or replay specs; renders via `resolve_prompt`);
       - `review disposition` (an unregistered fresh spec);
       - GitHub `assistant_generation.prepare_attempt`;
       - the notes builders.
   - **The author's list covers every execution entry**, matching mine: `api_runner.py:1484`,
     `:3173`, `:7104` and `cli/api.py:643`, `:723`, `:796`, `:1076`.
   - **Batch** guards each spec at `:1076`, before `_shared_current` at `:1086`.
   - **Prompt-render** guards at `:643`, before `--out` is opened at `:667`. The author's
     `[render-*]` cases pass.
   - **Not first, but without a mutation window:**
     - `assistant_generation.py:289` runs `shared.preflight` (read-only authority) before the
       guarded `build_phase` at `:290`. The spec is built at `:282` in the same function.
     - Native `write_registration` with a cached instruction after mutation is refused by its
       own exact-identity check, and no file is written (`q2-anchor-head`).
     - Component helpers (`shared_generation.preflight`, `assert_current`, `capture`,
       `receipt_completion.registration`) are unguarded. They are read-only, and only reachable
       ahead of the guard by a library caller using them directly.
4. **SG2** (R2-4; Issue 11).
   - **Alone at head, fresh process, 1,800 s bound, all pass:**

     | Case | Wall | Max RSS (tree) |
     |---|---:|---:|
     | `[none]` | 678 s | 1,086,390,272 |
     | `[explicit]` | 693 s | 1,121,271,808 |
     | `[conventional]` | 699 s | 1,076,215,808 |

   - **The weights are measured, not invented.** Each is the maximum local observation plus
     10%, rounded up: 767.02→844, 683.66→753 and 702.10→773 (my arithmetic agrees). They come
     from the author's serial `0fa` diagnostic and historical JUnit. They are macOS/Python 3.13
     figures, not Linux/3.12; the file aggregate is 2,384.875 s.
   - **I agree the accumulation cause is unverified.**
     - My round-2 hang did not reproduce, either alone or in the same session minus the node.
     - The author's 49-case serial run did not hang. Cache size (SchemaView `induced_slot` 0 →
       6,554) and peak RSS (0.40 → 1.27 GB) grew, but no causal link is shown.
5. **The roster** (R2-5; Issue 12).
   - **Closed over `dataclasses.fields(RunSpec)`:** `RUNSPEC_FIELDS` at
     `test_wave7_5213_d76_round2_binding.py:155-195`, with the equality assertion at `:197`.
   - **Proved by a scratch subclass:** `test_r3_classification_proof.py` passes 7/7. Adding
     `input_authority`, `registered_inputs_v2`, `pinned_input_manifest`,
     `typed_audit_registration`, `native_execution_version` or `_private_inputs` fails the
     roster.
   - **Classifications:** I found no field that pins an input and is classed as not pinning
     one, in D76's sense (input locators and registration selectors). `profile`, `out_dir`,
     `_corpus_root` and `_agentic_toolchain` are reasonably classed as not pinning: they are
     otherwise pinned, or not D76 input locators.
6. **Test integrity and scope.**
   - **Pre-existing test changes** in `git diff 0fa106e4d d13c1711e -- tests notes`:
     - `test_cli/test_provenance_prompt.py` and `test_profiles.py` switch `build_record` from a
       `MagicMock` return to `wraps=pv.build_record`, which is stricter (real identities);
     - `test_wave7_5213_d76_registration.py` moves the SG2 body unchanged into
       `_assert_sg2_root_launch`;
     - `round2_binding` replaces the suffix filter with the closed roster.
   - **No assertion is removed or weakened.**
   - **Protected paths:** `shared_generation.py`, the only `canonical_hashes.yaml`
     (ignore-independent `find`), `data/` and `.github/` all have an empty diff from `0fa`.
   - **Generality:** no project name decides production behaviour, by `grep` of the added
     `src/` lines.
   - **`scripts/adhoc/` imports:** none from `src/`. Tests import them only through R3-3.
7. **Integration:** see R3-4.
8. **The non-green items.**
   - **The 2 run-lock failures:** `tests/test_run_lock.py::TestAgainstARealProcess` passes 4/4
     at `87a8e7a80` and at head here.
   - **The 27 native failures:** `notes/.../native_controls/test_native_launch.py` passes
     **97/97** at `87a8e7a80` in its own notes session. That covers all 27, including the five
     "indirect" `test_no_signal_reaches_the_group…` and
     `test_the_kill_step_excuses_a_refusal_only_once…` variants.
   - **So none reproduces outside the author's OS sandbox:** they are environmental there, not
     defects. The native files are byte-identical from `87a8` to `d13c`.
   - **The 14 original-probe failures:** all expected, none a regression.
     - **Codex drift wording, ×3 plus the Claude duplicate ×3:** the earlier guard's message.
     - **Codex and Claude defect observations, ×2:** they assert the old bug.
     - **Codex `test_replace_revalidates…`:** `dataclasses.replace` of an `init=False` field
       raises **TypeError** on Python 3.13.12 (verified here), where 3.12 raises ValueError. It
       is the same at `0fa`: an interpreter difference.
     - **Claude cross-corpus ×2:** my probe read an R1 path after exit 0; my fixed r3 copy
       shows "asserted".
     - **Claude classification ×3:** inverted expectations; the r3 proof passes.

## Counts

| Run | Result |
|---|---|
| Every `tests/test_wave7_5213_d76_*.py` (15 files) at head, three SG2 nodes deselected | **302 passed**, 3 deselected, 753 s, max RSS 1.17 GB |
| SG2 `[none]` / `[explicit]` / `[conventional]` alone at head | **1 passed each**: 678 s / 693 s / 699 s |
| Round-3 regressions at head (inside the run above): round3 binding, copy_origin, recorder, replay_flag | **42 + 25 + 9 + 6 = 82 passed** |
| Same 82 at `0fa106e4d` (scratch tree, with head's `round2_binding` fixture copied in) | **59 failed, 22 passed, 1 error** (setup `git rev-parse` in the non-git tree); author: 62 F / 20 P |
| `test_r3_anchor_probes.py` | head **22 passed**. `0fa`: 12 passed, 3 failed (`PurePath` spend, `id` setup, private-rewrite spend), 7 skipped (no registry) |
| `test_r3_classification_proof.py` (head) | 7 passed |
| `test_r3_cross_corpus_recorder.py` | 2 passed at each head: head says "asserted", `0fa` says "verified" |
| `test_r3_verified_basis.py` | 3 passed at each head (observational). R3-1 witness at head |
| `test_probe_recorder_residuals.py` (round 2) | 5 passed at each head: (a)/(b) `match`, (c) refused |
| `test_r2_boundary_probes.py` (round 2) | 12 passed at each head. Head: every bypass refused; `0fa`: two spends |
| Codex round-2 witnesses (owner counterpart ×2, private anchor ×2) | head **4 passed**; `0fa` 4 failed |
| `test_run_lock.py::TestAgainstARealProcess` | 4 passed at `87a8e7a80`; 4 passed at head |
| `native_controls/test_native_launch.py` (notes session) | **97 passed** at `87a8e7a80` |

**Logs:** `scratch-5213r3check/claude/logs/` (`q1-*`, `q2-*`, `q3-*`, `sg2-preconditions.log`,
`merge-tree.txt`, `merged_api_runner.py`).

**Not run:**
- the full suite, shards and the 107 historical nodes (not requested);
- the specificity module;
- main's tests against the merged tree.

**Side effects:**
- **My first run of `sg2_child_preconditions.py`** used `-I`, which ignores
  `PYTHONDONTWRITEBYTECODE`. It left one `.pyc` in the checkout's `scripts/adhoc/__pycache__/`
  (13:53:48). I removed that file and the empty directory by name at 13:53:56; the script now
  sets `sys.dont_write_bytecode`.
- **The checkout is now clean,** including ignored files.
- **`git merge-tree` objects** went to `claude/gitobj/`.
