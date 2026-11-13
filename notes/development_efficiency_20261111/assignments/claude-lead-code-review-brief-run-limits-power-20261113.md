# Review brief: two native source branches from helper 2, plus one test merge

From the Claude lead, 2026-11-13. You are an independent reviewer. Your review is read-only: do not edit, commit, push, run a native binary, call a provider or model, or write anywhere except the one report file named at the end.

Repository worktree to read: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-helper-cache-home-20261112`. Use `git show`, `git diff` and `git log` with the commits below. Every commit named below exists in that repository's object store.

## What to review

1. **Two registered run-limit sets ("Case C"):** `8760de5efe88b5af62e9d77e6335fa7e248017b6..31fc33c1c72f06f219810841e3cc683da8068b1c`, on branch `codex/native-production-run-limits-20261112`. Owner decision D143 registers exactly two native run-limit pairs: the canary pair (spending stop 90 US dollars, 21,600 seconds) and the production pair (400 US dollars, 43,200 seconds). The helper says the code now accepts exactly those two declared pairs, refuses mixed, missing and third values, and changes no registered kind or version.
2. **Host power at launch (#6046):** `8760de5ef..7c1d972a1d92286bc791cca96f8dace0c18875e8`, on branch `codex/native-host-power-20261113`. The intent is that a launch sequence requires observed AC power and keeps evidence of host sleep. The machine is a laptop that slept four times on 2026-11-12, once into hibernation at 1% battery. The native child's timer uses monotonic time, while the ratified protocol describes the attempt deadline as wall time. On macOS the two differ across sleep.
3. **A test-only merge already on the candidate:** `7b851213f3492144cfd5b83d6bbd9a8a040e9132..f7f8e8bff6ea14006957d8631f66346d91bcddcd` (merge of `16248bc04`). The lead read this diff. Check independently that no test assertion is weakened and no production behaviour is relied on that the tests no longer check.

Context, read as needed:
- `R/notes/development_efficiency_20261111/assignments/claude-lead-helper2-three-failure-cases-20261112.md` (the assignment for both branches);
- the helper's handoff `R/notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112.md` ("Case C validation" and the power paragraphs);
- `docs/native-run-limits.md` and `docs/native-host-power.md` on the branches.

Here `R` = `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111`.

## Questions

1. **Correctness.** For each branch, does the code do what it claims, and only that? Check every accepted and refused input of the run-limit validation, including types, units, float spellings, and the canary and production pairs swapped between canary and production registrations. For power: what happens when the power source is AC, battery, unknown or unreadable; when it changes between registration, reservation and dispatch; and when the host sleeps during an attempt. Could the check block a legitimate launch on AC power, or let a launch proceed on battery? How are monotonic and wall time used, and does any deadline or freshness check misbehave across sleep?
2. **What the model reads.** Case C touches `native_u4b_policy.py`, `native_u4b_probe_sequence.py` and `native_launch_review.py`. Does any text, tool policy or command the model reads change? If so, name it exactly.
3. **Registered boundaries.** Is any registered document kind or version, any protected file, or guard v1 changed? The protected files are `src/data_sheets_schema/shared_generation.py`, `src/data_sheets_schema/api_runner.py`, `src/download/prompts/canonical_hashes.yaml` and `tests/utils/run_spec_boundary_contracts.json`. Do the branches change a consumer source that a registration pins, and is that change accounted for?
4. **Tests.** Does each branch's test set exercise the refusals as well as the acceptances? Name any untested branch of the new code.
5. **Public repository.** `tests/fixtures/native_host_power/pmset-sleep-20261112.txt` is this machine's real `pmset` log. Is anything in the committed files unsuitable for a public repository, such as host identifiers, user names or local paths? Would a synthetic fixture do?
6. **Integration.** Both branches are based on `8760de5ef`. The candidate is now `f7f8e8bff`. Name any conflict or interaction you can see without merging, for example with the recorder environment change `c577c0eff`, the 300-second margin `57bcc018b` or the helper-cache module.

## Report

Write one Markdown file:
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/native_run_limits_power_31fc33c1_7c1d972a_codex_review_2026-11-13.md`.

Lead with the verdict per branch: "integrate", "integrate after listed fixes" or "do not integrate". Then give the findings as P1, P2 or P3, each with file and line at the commit, the evidence, and the smallest fix. Then say what you checked and what you did not check. Plain language, short sentences. No at-sign mentions.
