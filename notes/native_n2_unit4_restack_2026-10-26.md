# Unit4 restack: installed-D38 helper checks

Refs #4354, #5170. Tested head:
`466cf410e38c685026c52a78c1a90b4d86048c3b` on
`codex/n2-4-restack-20261026`, in
`/private/tmp/d4d-codex-n2-4-restack-20261026`.

This head is the exact cherry-pick of reviewed helper/test commit
`f2dca0dd1f16769a10f65df96cb96caa2498a7cd` onto the fresh Unit4 restack.
It makes Unit4's historical render fixture explicitly use its old Git asset,
while adding the separate current installed-D38 checker and tests. The original
Unit4 worktree/ref and the final D38 worktree were not changed by this step.

The two focused modules passed **27 tests**, zero failures/errors/skips, one
dateutil deprecation warning, **3.32 s**, process exit 0. This run used the
primary checkout's absolute `.venv/bin/python`, standard Python startup,
`PYTHONDONTWRITEBYTECODE=1`, and explicit `PYTHONPATH` selecting this worktree's
`src` and repository root. `ANTHROPIC_API_KEY`, `CBORG_API_KEY` and
`OPENAI_API_KEY` were unset. **This pytest invocation is not a closed-namespace
or `-S -P -B` import proof.** No full render, full N2 suite, native binary,
provider call or runtime/scientific acceptance is claimed by this run.

The exact command, run from the worktree above, was:

```sh
env -u ANTHROPIC_API_KEY -u CBORG_API_KEY -u OPENAI_API_KEY \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/private/tmp/d4d-codex-n2-4-restack-20261026/src:/private/tmp/d4d-codex-n2-4-restack-20261026 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  --basetemp=/private/tmp/d4d-n2-unit4-d38-focused-20261026 \
  --junitxml=/private/tmp/d4d-n2-unit4-d38-focused-20261026.xml \
  tests/test_native_n2_installed_d38_20261026.py \
  tests/test_native_n2_render_parity_20261025.py \
  > /private/tmp/d4d-n2-unit4-d38-focused-20261026.log 2>&1
```

`git diff --exit-code f2dca0dd1f16769a10f65df96cb96caa2498a7cd HEAD -- src tests`
was empty, as was comparison of both render helpers. After testing,
`git diff --exit-code HEAD` and `git status --short --untracked-files=all`
were clean. Before/after SHA256 inventories of the two helper files and two
test files match exactly. Their common inventory SHA256 is
`c6a2429c73469f169d2d017f6ae2eba707bfb7f77d3bf6b0e5a20464d29c97f2`.

Byte-identical evidence copies:

- [Test log](native_n2_unit4_restack_2026-10-26/d4d-n2-unit4-d38-focused-20261026.log),
  SHA256 `40a720d7edb74a04c306b910bfc2602a2834b6e513cc7241d4bb6a14e5220590`.
- [JUnit](native_n2_unit4_restack_2026-10-26/d4d-n2-unit4-d38-focused-20261026.xml),
  SHA256 `884e0130588e90b0aa86db79377e852a8a6e4b5b810a2435014c2b98a18882b0`.
- [Before file hashes](native_n2_unit4_restack_2026-10-26/d4d-n2-unit4-d38-focused-20261026.before.sha256)
  and [after file hashes](native_n2_unit4_restack_2026-10-26/d4d-n2-unit4-d38-focused-20261026.after.sha256).

The evidence commit adds only this note and those four retained files after
the tested head; it is not a new test run. The originals remain in `/private/tmp`.
