# Review brief: helper 2's fixes for #6167 to #6172 and #6094, and its controller pin proposal

From the Claude lead, 2026-11-13. You are an independent reviewer. This is read-only. Do not edit, commit, push, run a native binary, call a provider or model, or write anywhere.

Repository worktree to read: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-helper-cache-home-20261112`. Every commit named here exists in its object store. Use `git show`, `git diff` and `git log`.

## Background

An earlier review is `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/native_run_limits_power_31fc33c1_7c1d972a_codex_review_2026-11-13.md`. It found six issues, #6167 to #6172. The ratified protocol N1 says: "**Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch." The lead's ruling for #6170 has four parts:
- the origin is the moment of child dispatch;
- the clock keeps counting while the host sleeps;
- it applies to every registered deadline (900, 21,600 and 43,200 seconds);
- AC power is rechecked immediately before dispatch.

For #6094, the lead asked for diagnostics that change no runtime decision: `execute_child` entry, dispatch, each helper call's start and end, and each model turn boundary.

Helper 2 merged the candidate `f7f8e8bff6ea14006957d8631f66346d91bcddcd` into each branch and then committed these:

| Branch | Head | New commits |
|---|---|---|
| `codex/native-production-run-limits-20261112` | `0df39c077fb8125dc381302046f4cf7f92a60592` | `94378cd62` (#6169), `0df39c077` (#6171) |
| `codex/native-host-power-20261113` | `916ad3af0adf278ab3bbde78be7c9fb3c4cc92f0` | `2c158ddfc` (#6167), `f377dba1d` (#6168), `feb1de325` (#6170), `a4f45bb93` (#6094 timing), `916ad3af0` (#6172) |
| `codex/native-helper-cache-home-20261112` | `9d743c87755030ddf687e3a5dd8a7a2b3b762437` | `9d743c877` (#6172, cache runner) |

What integration would add to the candidate is `git diff f7f8e8bff6ea14006957d8631f66346d91bcddcd <head>` for each branch.

**The controller pin proposal**, which is not applied: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-controller-pin-proposal-20261113.diff`. Its sha256 is `921eb9b024f7ab1a491b6d910aac4c1a880fed3477a9fba7330d2fc21d9695d7`. It rotates `src/data_sheets_schema/native_controller_sources_v1.json` and `_v2.json` to `source_commit` `916ad3af0` with new sha256 values for `native_control.py` and `run_native_canary.py`. It also updates three digest constants: `SOURCES_SHA256` in `native_attribution_controller.py` and `native_attribution_controller_v2.py`, and `CONTROLLER_SOURCES_SHA256` in `native_shared_authority_wire.py`. Helper 2's Codex session refused to apply it, as a trust-pin change reserved for the lead. Its handoff is `.../handoffs/codex-h2-run-limits-power-fixes-20261113.md` in the same report worktree.

## Questions

1. **Does each fix resolve its issue fully, and only that issue?** For #6170 check these points:
   - Is the deadline origin exactly at dispatch?
   - Does the clock count suspension on macOS (`mach_continuous_time`) and Linux (`CLOCK_BOOTTIME`)? Is there no fallback to an adjustable or suspension-excluding clock?
   - Is expiry detected if the child exited while the host was suspended?
   - Is AC rechecked immediately before dispatch?
   - **What now bounds the time spent in admission and launch verification,** which the old origin covered? If nothing bounds it, say whether that matters.
2. **The #6094 timing sidecar.** Is it bounded in size? Does it record any secret, credential, personal path or model-visible content beyond what the run already saves? Can a failure to write it change any runtime decision or the failure publication?
3. **#6167 and #6168.** Is the first launch error always kept, and publication never skipped? Is "no sleep" returned only from a recognized log that covers the interval?
4. **#6169, #6171 and #6172.** Does the strengthened test fail without the pair check? Does the documentation match the candidate? Are personal paths gone from all committed runners, including the cache runner already on the candidate? Is the sleep fixture synthetic?
5. **The pin proposal.** Recompute every proposed hash from the files at the branch heads, after applying the proposal where one digest covers another file. Does each one match? Is rotating both the v1 and v2 controller manifests consistent with how they were rotated before (`git log` on them)? Does anything else pin these controller files and still need an update?
6. **Integration.** Name every conflict or interaction from merging all three heads onto `f7f8e8bff`, then onto the lead's `ced0d51b2`, which adds helper 1's consumer-census update. Are the four protected files and guard v1 unchanged?

## Report

Your final message is the report. Give the verdict first:
- per branch: "integrate", "integrate after listed fixes" or "do not integrate";
- for the pin proposal: "apply" or "do not apply".

Then give findings as P1, P2 or P3. Each needs the file and line at the commit, the evidence and the smallest fix. Then say what you checked and what you did not check. Use plain language and short sentences. Use no at-sign characters.
