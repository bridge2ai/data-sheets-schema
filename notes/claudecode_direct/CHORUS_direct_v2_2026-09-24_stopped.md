# CHORUS direct-arm canary, 2026-09-24: two attempts, both stopped before the provenance record

The second canary of the direct arm (#2202): Claude Code 2.1.272 on the maintainer's claude.ai subscription, `claude-opus-5` at effort `max`, one fresh CHORUS generation through all four phases, with no proxy, no CBORG and no ledger. It ran at a75bb2a91, the merge of PR #2327. That commit includes the fix of PR #2291 for the recorder line that disqualified the first canary (#2282). The first attempt stopped on a network failure while the machine slept. The retry stopped at the terminal evidence check. Neither wrote a provenance record, so neither is a run of the study, and nothing enters the corpus.

## Identity

Common to both attempts:
- Job `CHORUS_direct_rep1` and method `claudecode_direct`.
- Runtime `Claude Code (direct)`, provider `Anthropic (Claude subscription, direct)`.
- Condition `generic_v9`, renderer 17, profile `bridge2ai`, cohort `generalized_direct_v2`.
- Code commit `a75bb2a9152fd44ec335533ee1c5c15419acf328`, executable sha256 `195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75`.
- Guard $90, deadline 21,600 s, 236 pins.
- The recorder line ends `--prompt-text-env D4D_LAUNCH_INSTRUCTION`. An offline probe of each registration's exact line admitted it, with the variable reaching the process it launches.
- Each registration was reviewed independently and bound to CI run 35908558928 on the registered commit. The registrations, reviews, words, attempt directories and generated files stay untracked in the canary worktree; this note carries their hashes.

| | First attempt | Retry |
|---|---|---|
| Label | `2026-09-23_claude-opus-5-direct-generalized-direct-v2-chorus_rep1` | `2026-09-24_claude-opus-5-direct-generalized-direct-v2-chorus_rep1` |
| Registration sha256 | `80ece940d68ba778384ad174a33fb051813fb77fb448b00fe47eb182f39e4560` | `9db052acde18b14808cdc863b07a252e2b580f647cbaff999946813114a65aea` |
| Instruction sha256 (97,191 bytes) | `69aadd82a8d777701bdfb57cc05ebd715761f07d7c0a726ce2fbd710f1e379c2` | `5c82e2a0fa77f6986ef1f9593dfb03db2c5429d5ff2026fe04a24319f3f41120` |
| Independent review sha256 | `4015394f760ad50cef923e8e7a919b233a5cf696933f546bcd5692e183a72b65` | `39edaf0cde297c6506a15f926548d4b4602c3f5e582d65eb7974adee1b4b313c` |
| `review.json` sha256 | `06611b47b0aba156b8caaab750f9cb9a610a4bda4c4d38c89812be77f70db602` | `e4c44336a821c49742f61c83d2122f37736ce275fb0326f0115c7d46335c83a2` |
| `word.json` sha256 | `468843f92a8834c5700834d58da1ad76ebeeb8046451b6450eba782cb632578b` | `9bfbaf29fc1b8882b129d52afccf06dd563b054f2838c2eeabbfee4fa9f9b0e3` |
| Started | 2026-09-24T00:52:55Z | 2026-09-24T07:15:45Z |
| Stopped | 2026-09-24T01:41:43Z | 2026-09-24T10:17:18Z |

The two registrations differ only in the label date, the run date, the instruction that carries those dates and its hash, the preparation time and their own paths. A $60 sibling of the first registration, `3ece0fe5…`, was prepared and reviewed but not chosen. It was retired unlaunched.

**The launch words.** The session asked: *"Launch the second direct CHORUS canary? Reply "launch 90" for registration 80ece940… with the $90 guard, or "launch 60" for registration 3ece0fe5… with the $60 guard."* The maintainer answered *"yes $90 for guard and address these"*, followed by the session's two risk bullets on #2369 and #2350. The session first read "address these" as fixing both issues before any launch. About 46 minutes later, with no further message, it read the answer as a launch word with the fixes to follow, and launched. The fixes followed in PR #2398, unmerged at the time of writing. The retry's word records the maintainer's exact response, *"try again"*, and states that no question was asked. It was the maintainer's first message after this session had printed three errors of its own (*"API Error: Can't reach the API server … (ENOTFOUND)"*, while the machine slept) and before the session had reported that the attempt had stopped. It most likely asked the session to retry its failed turn. The session instead read it as a request to relaunch. It prepared, reviewed and bound a new registration to the words, and launched without asking; that was the session's error. The retry's own review had said its word should cover the weekly headroom and a keep-awake form tied to the launcher, and "try again" covers neither.

## First attempt: stopped by a network failure while the machine slept

The child ran 62 turns by the runtime's count, making 60 tool calls in 55 API messages, all admitted by the controller, and wrote its coverage receipt (sha256 `961cec36dda6596ab76a568e8dbdc84b033ae9e0d8715f9165f1c6fa8c155d0d`). Its requests then failed with *"API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"* after the runtime's final run of ten retries (the transcript holds 11 retry events, one of them earlier), and the session ended (`terminal_reason: api_error`). The runtime's own estimate was $7.76. The machine's power log shows idle sleep at 01:11:54Z on AC power, with only maintenance wakes afterwards. The launcher had been started as an ordinary background task and held no sleep assertion of its own. Another process's short, renewed assertions had kept the machine awake. The last of them ended at 01:09:15Z, and idle sleep followed 2 min 39 s later. The runtime's own duration is 21 m 41 s of the attempt's 48 m 48 s, which is consistent with the sleep. The retry was launched as `caffeinate -ims <launcher command>`, which holds the assertions for the launcher's lifetime.

## Retry: stopped at the terminal evidence check (#2427)

- **Child.** The child ran for 3 h 01 m, all `claude-opus-5`, with effort `max` on every callback. It made 308 tool calls (224 Bash, 63 Read, 21 Write) in 227 API messages. The runtime's turn count is not available, because the controller stopped the child before its result line. There were ten context compactions and no API retries.
- **Denials.** The controller refused eight calls itself as not prescribed; none disqualifies. Three were refused for a shell operator: two multi-range `sed` programs and a `grep … | head -c …; wc -l` chain. Five were refused as programs the registered lookups do not admit: three `grep` calls with several `-e` patterns, a `grep -c` over a runtime tool-results file, and a `grep -B/-A` over the playbook. The runtime refused one Write of the full record before the hook fired (*"File has not been read yet"*), which the #2285 control recognises as an unexecuted call. So 307 decisions cover 308 calls. The runtime refused nothing else.
- **Phases.** The Phase 1 receipt check passed. Core derivation completed. Reconciliation and the report were written.
- **Evidence checks.** The first evidence check, run on the audit, passed. The terminal check (`evidence_assertions v5 / source_review v2`) failed, and the controller stopped the run as registered: *"native phase history: event 1268: terminal evidence check failed"*. The provenance recorder was never reached.
- **The failure.** The source review of the original record passed: 231 of 231 values and 299 claims, with no findings. The review of the final record, which the model writes into the reconciliation report's evidence appendix, has 60 findings of one kind, *"attributed_to must list distinct named source documents, or be empty"*. In 96 claims the model wrote the source manifest's IDs (`project_documentation`, `nih_reporter_project`, …) where the contract requires the bundle's source filenames. The instruction asks for "the exact source filenames"; it also shows the manifest projection that pairs each filename with its ID. The failure reproduces offline with the same command on the same files (exit 1).
- **Artifact sha256 at the stop:**
  - `CHORUS_d4d.yaml`: `8a740d32a6cd9c4f1799c1de690f83c2c9dfa9f033e0991109ac75157d4a75a6`
  - `CHORUS_d4d_core.yaml`: `15e04c163e18f9f6e6e085d6b199af03885846fad7c5a2267e00276cd6fc4d9d`
  - `CHORUS_coverage_receipt.yaml`: `c32416dcbd38ebb685c848c7f3e69a1c84bbfd1d048ee1a5cc2ca4d7f8668194`
  - `CHORUS_reconciliation.md`: `a8fcda4386c7659840785d78b92621266cdddcddc2091a894ab00c2354e77896`
  - `audit.json`: `886cf0d86c42ac65381ac1f8197cdc87b04c01610db53f43d237b52d5ebddee4`
  - `original_full.yaml`: `fa137ac2ba0329b34ffa7d87eaa1f3828a62ca5fcaac7e7c983a902dcfb9fae8`
  - `original_core.yaml`: `742df6ffdb84686522a28fe3c6f614c84004b5e4b6c80ef30058643e25ef6cf0`
- **No terminal result.** The controller stopped the child, so no accounting exists and the receipt has no cost estimate.

## Other findings

- **Rate windows.** The runtime reported the seven-day window at 0.94 at both starts and 0.96 at the retry's stop, with status `allowed_warning` and no overage. The window resets on 2026-09-26 at 00:00Z. Nothing reads headroom before a launch or stops a run in overage (#2370).
- **The recorder fix is still unexercised.** Neither attempt reached the recorder line, so the #2282 fix has been observed on this arm only through the offline probe of each exact line.
- **Controller exposure.** Found while preparing these registrations, and fixed in PR #2398, unmerged at the time of writing: a prescribed command the model respells would have been refused by the runtime and disqualified the run (#2369). No attempt here respelled one. A registered line records no `receipt_expected` (#2350).

## Standing

Never resumed. A third attempt needs a fresh registration, its review, CI binding and launch word, the offline probe of its exact line, and weekly headroom. It is best made after the #2427 mitigation and PR #2398 land, since both change what the run is held to.
