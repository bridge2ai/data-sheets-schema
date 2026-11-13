# Review brief: analysis plan amendment N1, draft v7

Read-only adversarial review. You did not write this draft. Do not edit it, do not commit, push or write to GitHub, and run no test, model or provider call.

## What to review

- The file `notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` at commit `2fb0503757db041e009f21dd02a1d57a45a75a88` (draft v7, file sha256 `8a644c0efb968da23f45c533e757fcd06af495c3d15c73c442c9d4a8c5566a60`), checked out at `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-native-amendment-n1-v7-20261112/`.
- Against the previous draft v6.1 at commit `754fbfdae10dbe9fe3f4443725cf0fa2a696b49e` (file sha256 `741677373008237020d409a7f79365b3e2d0f188a16d996b5defb3a14af050aa`). The diff: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema diff 754fbfdae10dbe9fe3f4443725cf0fa2a696b49e 2fb0503757db041e009f21dd02a1d57a45a75a88`.

v6.1 was reviewed through six rounds and found ratifiable. This review is of the v7 changes and of anything they make inconsistent elsewhere in the file.

## What the draft claims about itself

It says v7 changes six things and nothing else (its header lists them). Check that claim against the diff.

## Sources to check its statements against

- Owner decisions and their exact words: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (search `D126`, `D129`, `D130`, `D131`, `D132`, `D133`, `D134`, `D43`, `D115`, `D118`). The file is long; use `grep -n`.
- The launch-path timing: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy4-freshness-value-table-20261112.json` and `.md`, and the estimate of untimed production steps in `handoffs/codex-native-critical-path-20261112.md` (section "Direct answer 3") in the same directory.
- The native source the freshness rule lives in, at commit `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`: `src/data_sheets_schema/native_u4b_policy.py`, `src/data_sheets_schema/native_subscription_guard_v2.py`, `src/data_sheets_schema/native_generation.py` (read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show <commit>:<path>`).
- The schema release: `src/data_sheets_schema/schema/release_history.yaml` and `src/data_sheets_schema/schema/data_sheets_schema.yaml` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`.

## Questions

1. Is every statement v7 adds or changes supported by the source it cites, with numbers and quotations exact? List each one that is not, with the line in the draft and the line in the source.
2. Does the diff contain any change outside the six the header lists?
3. Is the file internally consistent after the changes? In particular: every value marked `[proposed]` has a lettered item in N1.8 and the two say the same thing; no place still states or depends on the old freshness age or the old schema release where it should have changed; the arithmetic (age, margin, the latest reservation time) agrees everywhere; N1.5's event order, N1.3's D12 row and N1.8(z) do not contradict each other or D43; N1.6's sequencing text and N1.8(y) say the same thing.
4. Does any v7 change weaken a protection the previous draft had, or create a way to pass a gate that should refuse? Say what and how.
5. Is the reasoning given for the new freshness age sound on the evidence cited, and does the text overstate what the one timing shows?
6. Anything a careful owner would misread or be surprised by later.

## Output

A report with the verdict first (ratifiable as is, ratifiable after listed fixes, or not ratifiable), then findings numbered and graded P1 (blocks ratification), P2 (should be fixed before ratification) or P3 (wording), each with the draft's line number, the evidence, and the smallest fix. State what you checked and what you did not. Use no at-sign characters.
