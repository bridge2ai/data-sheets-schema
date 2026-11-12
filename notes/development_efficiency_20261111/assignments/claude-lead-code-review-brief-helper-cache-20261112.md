# Review brief: the helper cache location on the native route (read-only)

Read-only adversarial code review. You wrote none of this code. Do not edit, commit, push or write to GitHub; run no test, no model or provider call, and nothing that executes the Claude Code binary. Read with `git -C <worktree> show` and `git -C <worktree> diff` only.

## What to review

Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-helper-cache-home-20261112`. Base `ba1f56e4a9460fe87c1e0ea3cb35ed2d7405cfa0`; commit `e079e2f3a12ab1b8e5a9d40344932af8073bad3f` ("isolate PyStow helper cache per attempt outside HOME", issue 5966). If the branch has later commits by the same author, review them too and say which.

The defect: on the native route's public launch path, a helper command (`full_terms`) imports a term validator, which imports oaklib, which imports PyStow; PyStow writes `.data/README.md` and `.data/oaklib/` under HOME at import. The synthetic profile's guard then refuses the run: "synthetic HOME must contain no account or configuration artifacts".

The rules the repair had to follow (from the lead's assignment):

1. The empty-HOME and account-artifact guard is not relaxed anywhere, and no name under HOME is tolerated.
2. One code path for both profiles: the repair is in the environment the controller constructs for the native process, which the helpers inherit, so that production and the synthetic peer take the same path.
3. The cache location is a declared, per-attempt directory the controller creates empty, outside HOME, outside the staged source and outside the output roots that are inventoried or published, and present wherever the environment is declared, allow-listed, pinned or validated.
4. The model's file tools cannot read or write that directory, and nothing a previous attempt wrote can be in it.
5. Only the variable PyStow reads is set.

## Questions

1. Is each of the five rules met? For rule 2, trace the production profile and the synthetic profile to the point where the environment is handed to the process, and say whether they share the code that sets the variable. For rule 4, find the tool policy that decides which paths the model's Read, Write and Bash tools may touch and check the new directory against it; a Bash helper can of course write there, which is the point, but can a model-issued command read it back or list it?
2. Can the directory be a channel: created before the attempt and pre-populated, shared between attempts, reused on a resume, followed through a symlink, or placed by a caller-controlled path? Is its creation exclusive and its location derived only from registered values?
3. Does the cache directory, or anything in it, enter the evidence a reader verifies (the snapshot, the catalog, the published result), and if it is deliberately left out, is that stated and tested? Could its presence break an existing "nothing else was written" check?
4. Which declared identities move (runtime declaration, profiles, permission expectations, registration, pins)? Is any registered document's kind or version changed? Are the four protected files and guard v1 untouched (`src/data_sheets_schema/shared_generation.py`, `src/data_sheets_schema/api_runner.py`, `src/download/prompts/canonical_hashes.yaml`, `tests/utils/run_spec_boundary_contracts.json`)?
5. Does the change add any network access, or any behaviour that depends on a project's name?
6. Do the tests show the old refusal at the base and its absence after the repair, the guard still refusing a HOME with an entry, and a fresh directory per attempt? Do they assert the property or only a message?

## Output

Verdict first: acceptable as is, acceptable after listed fixes, or not acceptable. Then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title` (P1: weakens the guard, opens a channel into the model, or breaks production while fixing the test; P2: should be fixed before the final review; P3: minor), each with file and line, the concrete scenario and the smallest fix. Then what you checked and what you did not. Use no at-sign characters.
