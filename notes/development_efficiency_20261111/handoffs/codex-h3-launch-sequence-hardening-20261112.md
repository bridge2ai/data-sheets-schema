# Helper 3 launch-sequence hardening — 2026-11-12

final. No registered-document kind/version changed.

- `b832233b798da1f350a764f49f19039195fab4c5`: fix(native): consume delegated directions across packet paths (#5989). Files: `scripts/adhoc/prepare_h3_hardening_runner_20261112.py`, `scripts/adhoc/report_h3_hardening_20261112.py`, `scripts/adhoc/run_h3_hardening_tests_20261112.py`, `src/data_sheets_schema/native_launch_sequence.py`, `src/data_sheets_schema/native_sequence_start.py`, `tests/test_native_launch_sequence.py`, `tests/test_native_sequence_start.py`.
- `9abf48b31122da7a89ba462274a8e3980d1b7973`: fix(native): execute and retain the once-verified sequence bytes (#5990). Files: `notes/native_launch_hardening_DRAFT_20261112.md`, `scripts/adhoc/update_h3_sequence_entry_tests_20261112.py`, `src/data_sheets_schema/native_launch_entry.py`, `src/data_sheets_schema/native_launch_sequence.py`, `tests/test_native_launch_entry.py`, `tests/test_native_launch_sequence.py`, `tests/test_native_sequence_start.py`.
- `c1ad9baa19a5b938d7976541bed27a73eee32d8c`: fix(native): bind child consumption to parent input digests (#5991). Files: `notes/native_launch_hardening_DRAFT_20261112.md`, `src/data_sheets_schema/native_execution_orchestration.py`, `src/data_sheets_schema/native_generation.py`, `src/data_sheets_schema/native_launch_sequence.py`, `src/data_sheets_schema/native_sequence_inputs.py`, `src/data_sheets_schema/native_shared_execution_orchestration.py`, `src/data_sheets_schema/native_subscription_capture.py`, `tests/test_native_launch_sequence.py`, `tests/test_native_sequence_inputs.py`, `tests/test_native_sequence_start.py`.

| Cohort | Cases | Failures | Errors | Exit | Cleanup |
|---|---:|---:|---:|---:|---|
| direction-canary | 1 | 0 | 0 | 0 | True |
| direction-full | 107 | 1 | 0 | 1 | True |
| entry-full | 111 | 0 | 0 | 0 | True |
| final-candidate-regressions | 150 | 0 | 0 | 0 | True |
| final-touched | 125 | 0 | 0 | 0 | True |
| inputs-canary | 1 | 1 | 0 | 1 | True |
| inputs-canary-02 | 1 | 0 | 0 | 0 | True |
| inputs-full | 124 | 1 | 0 | 1 | True |

## Result and trust boundary

All three requested repairs are implemented in separate commits, in issue order. After the third commit, every touched test file ran whole: 125 passed. The subsequent required candidate launch-sequence and review-bundle files ran whole: 150 passed. Counts overlap across cohorts; they are not distinct-test totals. Final runner results report successful source-origin checks, cleanup verified and no observed survivors.

After #5990 the interpreter and site startup, the small native_launch_entry.py entry, the pure wire reader, and local OS/filesystem remain trusted. The reviewed sequence is not imported by that entry: one captured byte string is compared with the registration package-source pin and current review pin, compiled, executed and handed to the body for retention. The entry checks the review's registration binding before executing it. The old sequence main delegates to the entry for compatibility; the documented entry is native_launch_entry, and the private verified-body API is not an operator entry. This does not defend against arbitrary code already controlling Python or authenticate a human, host confirmation, direction or quiet account.

No review-bundle, owner-terms or execution-registration kind/version changed. The direction claims are local start records, and sequence-inputs is a closed invocation argument, not registered authorization. The existing real command consumers still perform full reconstruction and current authority checks. No verifier-bootstrap import was added inside the verified consumer; native_launch_review.py remains unchanged. Existing document versions do not make old source pins reusable: new package/dependency/permission/review pins must be derived from the eventual integrated source.

## Repair details

### #5989

A start record lives under the registered attempt parent, at .native-sequence-starts/<registration-sha256>/. The recorded direction UTC instant is the direction identity within that registration, normalized so different fractional spellings cannot bypass the exclusive claim. A host confirmation update cannot renew it. The exclusive direction claim is independent of the packet directory, fsynced and kept after failure; partial claims are not cleared. New recorded directions must have distinct recorded times, supplied by the owner rather than invented by the helper. Owner starts, with neither delegated flag, retain separate unique records and remain repeatable. The capture limits-mismatch latch and capture/word/attempt reservation code are unchanged.

The regression simulates a transient capture-command refusal, retries with a different packet and equivalent direction timestamp plus refreshed host confirmation, and verifies zero further command calls. A newly recorded direction reaches the three fabricated commands and retains the first claim. Separate tests cover repeatable owner starts, a symlinked state directory, and claim latency crossing a delegated deadline. The last delegated-time check now occurs after durable start claiming and immediately before the first child command.

### #5990

The load-A/replace-with-B witness reads A, replaces disk with reviewed B, then proves the captured A is refused before execution, packet creation, start claiming or capture. A complementary inert-body witness proves the verified capture is what executes and is passed for retention even if disk changes afterwards. The actual sequence body is tested through the entry with fabricated child commands, and the candidate copied-package subprocess test also traverses the entry. The retained bytes are never supplied by rereading __file__ inside the executing body.

Candidate sequence unit tests exercise the private body with explicitly captured fixture bytes so clock and command substitutions remain local to those tests. This is not a claim that their fixtures authenticate the entry; the independent entry tests and copied-package subprocess cover that boundary. The output-order test spy now observes command-output JSON only, preserving its assertions that all three outputs exist before parsing.

### #5991

Every child receives the five original input paths and digests (registration, review, word, account choice and CI), plus the saved capture manifest for guard preparation or the guard for launch. The closed roster and argument-path equality are checked before consumer work. The child compares the exact registration/account-choice/review/word bytes consumed, not only an earlier preflight read. Guard reconstruction compares the actual capture-manifest bytes under its current-word lock. The launch entry carries expected review/CI/word digests through native_shared_execution_orchestration.launch and native_execution_orchestration.launch into the engine's recaptured authority, before any reservation; existing fresh-admission equality then keeps later captures joined to those bytes. The guard's existing expected digest remains required. Standalone callers without sequence input pins keep their existing behavior; the reviewed sequence always supplies them.

The replacement canary constructs two review/word joins accepted by the genuine current bundle validator, replaces both after the parent's saved check, and proves the child refuses before registration admission or any capture actuator. This is component evidence with synthetic registration/review fixtures, not an actual production registration or full live admission. Other tests cover every original input, replacement after child preflight, the engine's actual authority comparison before effects, the capture-manifest reader, malformed/extra/missing pins, and digest forwarding by all three sequence commands.

## Retained failures and limits

The direction-full cohort initially had 106 passes and one failure: its broad JSON spy assumed the newly added registration parse was command output. That fixture was narrowed to command-output documents, retaining all original output-persistence assertions. The first input replacement canary and inputs-full cohort correctly refused the changed launch word, but the test expected the review to be reported first. Input checking now follows the declared BASE order rather than JSON key order; the exact review-refusal assertion is unchanged. Both failed logs and reruns are retained, and all final whole-file cohorts pass.

No real executable, provider/model call, real capture, word/attempt reservation, or production sequence start was performed. Synthetic direction/start records and invented command outputs are test artifacts under this helper's scratch only. No paid probe, complete production registration, full CI, scanner clearance or scientific acceptance is claimed. These repairs now need independent review because helper3 is their author.

## Integration and final state

Branch codex/native-launch-sequence-hardening-20261112 starts at published candidate 0fc003a86081891abbe8e130ac760c01da06423e. Exact commit-to-file mappings are above and in the JSON. No edits were made to helper1's pending-floor files (cli/receipts.py, native_shared_capture_orchestration.py, native_shared_gates.py), helper2's worktree, or its native controller environment construction. The common execution and capture orchestration files listed in #5991 should be included in the lead's integration ordering.

Git comparison confirms the four protected files equal main 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1, and guard v1 equals the published candidate. Guard-v1 SHA-256 is ab72f90faf0b4ba6150a5dd53d1f832feb4f0f5496485734228b00c613c65edc. The worktree is clean. The copied runner retains its original trailing blank line; whole-branch git diff --check reports that one cosmetic EOF warning at scripts/adhoc/run_h3_hardening_tests_20261112.py:419. No source/test whitespace errors were reported. Nothing was pushed or published.

Test evidence root: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-launch-hardening-20261112/tests/. Each cohort has its log, JUnit, origin witnesses and outcome/cleanup record; JSON pins every log, JUnit and outcome. The first handoff was written when #5989 was committed. The committed report helper reconstructs this final handoff with --final using the retained final-details.json.

