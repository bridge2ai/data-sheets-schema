# Native CHORUS canary runbook — DRAFT, 2026-11-12

This is preparation, not permission to execute any live step. The offline prefix
was exercised on real CHORUS inputs. Full registration is blocked on this base
by the protected RunSpec constructor. The synthetic routing tests stop before
capture, guard preparation or launch implementations, and before any reservation.
They do not establish full-chain registration, CI, real account state, permission
behavior or scientific acceptance.

Source baseline: `058de60779412150c529e41c86c5cfe9047014da`. N1 reference:
`c289eed19e37e227e04dd5e0c4fc077da54184aa`, draft v12. Ratification, independent
reviews, approved protected integration, successful full CI and merge remain
separate prerequisites. This branch has review bundle v2, owner terms v1,
1200-second freshness and a 90-second pre-reservation margin. N1 v12 proposes
300 seconds and helper2 is preparing bundle v3 / terms v2. **Do not register a
production packet against this mismatch.** Switch the review adapter and rerun
all saved-input tests on the reviewed merged source first.

## Explicit locations

The examples below use shell variables assigned by the operator from the
reviewed packet. They are not environment-discovered defaults. Replace every
`/ABS/...` with a canonical physical absolute path, and select a new output
path for every producer. Do not source this document as a script.

```sh
CHECKOUT=/ABS/REVIEWED-MERGED-CHECKOUT
PYTHON=/ABS/REVIEWED-ISOLATED-VENV/bin/python
PACKET=/ABS/NEW-CHORUS-PACKET
INPUTS=/ABS/OWNER-AND-LEAD-SUPPLIED-INPUTS
ATTEMPT=/ABS/FUTURE-ATTEMPT-ID
EVIDENCE=/ABS/FUTURE-EVIDENCE
cd "$CHECKOUT"
```

The canary scope is CHORUS, baseline input documents, generic_v10 native shared
v1 renderer 26, bridge2ai profile, receipts v4 and pending diagnostic_pilot
coverage floor. Receipt-origin reporting is a secondary axis, not a switch to
receipts v5. N1 covers one canary, not production replicates; the floor rule and
any later replicate plan need their own ratification.

## Ordered actions

1. **Lead; owner approval required for merge and protected integration.** Finish
   independent code/scanner/CI review, owner-ratified N1 and approved integration.
   Use the normal reviewed branch/PR workflow; no merge command is delegated by
   this runbook. Record the actual merged SHA and clean source state:

   ```sh
   git -C "$CHECKOUT" rev-parse HEAD
   git -C "$CHECKOUT" status --porcelain=v1
   git -C "$CHECKOUT" diff --exit-code HEAD
   ```

   Inputs: approved PR, ratified amendment bytes, passing complete CI, reviewed
   source closure. Outputs: pinned source/dependency identity and saved CI
   evidence, with actual tested commit, workflow event/ref/hashes and each
   `required_checks(event)` result. Do not replace failed/cancelled shards with
   inferred success. Read-only Git checks alone do not prove those approvals.

2. **Worker; offline.** Build the real CHORUS input prefix in the isolated
   environment. Output parent must already exist; output itself must not.

   ```sh
   "$PYTHON" -P -B "$CHECKOUT/scripts/build_native_canary_packet.py" \
     --checkout "$CHECKOUT" --output "$PACKET/input-prefix" \
     --source-manifest "$CHECKOUT/data/preprocessed/source_manifest.yaml" \
     --bundle "$CHECKOUT/data/preprocessed/concatenated/CHORUS_preprocessed.txt" \
     --chunk-manifest "$CHECKOUT/data/preprocessed/chunks/CHORUS_chunks.yaml" \
     --context "$CHECKOUT/data/omission_contexts/chorus_omission_context.json" \
     --full-schema "$CHECKOUT/src/data_sheets_schema/schema/data_sheets_schema_all.yaml" \
     --core-schema "$CHECKOUT/src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml" \
     --stage-root "$ATTEMPT/stages" --project CHORUS --profile bridge2ai \
     --registration-id DRAFT-CHORUS-NATIVE-CANARY --label DRAFT-NOT-AUTHORITY
   ```

   Expected exit **2**, `status=dependency_stop`, with nonempty receipt-policy,
   selection, input-inventory and status files. Exit 1 is a production refusal;
   retain its status and stop. Existing output, altered chunks, profile mismatch,
   foreign resources and overlapping stage paths are refusals. This builder
   never executes any child process and denies network and outside writes.
   All pinned files must remain at their recorded paths with unchanged bytes.

3. **Owner and lead; OWNER ACT REQUIRED.** Supply actual account intent and host
   terms, choose a durable binary copy outside the updater tree, and supply its
   observed version/auth facts. Hashing bytes is offline; obtaining missing
   version/auth observations by executing the native binary is a separate
   owner-authorized action, not hidden in packet assembly. No command is
   automatically run to obtain them. Provisional runtime uses the closed runtime
   mapping validated by `native_u4b_probe_sequence.validate_provisional_runtime`.
   The owner supplies `authorization.json` with
   `AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES`, exact provisional-runtime digest,
   one-use directory and bounded observation/permission deadlines. The native
   authorization parser is the authority for its closed keys. Human actions
   have no shell command: the owner writes/ratifies the exact bytes and the lead
   records the act. No fake signature or approval placeholder is permitted.

   Requested/init/terminal model is `claude-opus-5[1m]`; assistant returned model
   is `claude-opus-5`; high effort; no auxiliary models; 1M disable variable `0`.
   LBL work Claude Max is the selected account, not proof of authentication.
   Deadline 21600 and budget 90 require the ratified terms. AC power, lid-open,
   overage-disabled and keep-awake declarations must reflect the actual host.
   Provisional declared limits must not be presented as observed limits.

4. **Authorized operator; OWNER D117 WORD REQUIRED. LIVE, NOT RUN HERE.** Make
   `observation-account-choice.json` from the actual D105/D106 owner choice,
   hashing this exact provisional runtime as both subject and runtime using the
   production canonical wire. The account-choice document is a declaration,
   not account authentication. Execute exactly one authorized observation:

   ```sh
   "$PYTHON" -P -B -m data_sheets_schema.native_generation observation-probe \
     --authorization "$INPUTS/authorization.json" \
     --runtime "$INPUTS/provisional-runtime.json" \
     --account-choice "$INPUTS/observation-account-choice.json"
   ```

   Outputs: saved observation manifest, invocation, transcript, native request
   and claim under the authorized directory. This is the scripted loopback
   protocol, not a subscription call. A failed observation is retained and
   stops the sequence; do not silently mint another authorization or directory.

5. **Worker; saved-input preparation after step 4.** Supply `runtime-inputs.json`
   with `runtime_path` and `arguments` containing exactly `probe_init_path`
   (complete transcript), `native_request_path`, `updater_source`, `updater_root`,
   `thinking_setting`, `thinking_basis`, `observation_probe_path`,
   `admission_policy`. Values come from actual saved observation/owner inputs.
   The admission object contains the ratified quota limits, freshness, margin,
   capture state directory and fourteen-day validity interval. Its dates must
   later agree with the actual registration-addition commit; do not invent them
   or adjust a committed packet to mask a mismatch.

   ```sh
   "$PYTHON" -P -B "$CHECKOUT/scripts/native_canary_saved_step.py" \
     --checkout "$CHECKOUT" --step runtime --inputs "$INPUTS/runtime-inputs.json" \
     --output "$PACKET/runtime"
   ```

   Outputs: production `prepare_runtime` plus `validate_prepared_runtime` result.
   The helper never fabricates observations, owner terms or version evidence.
   It does not copy/move binary or probe files. Keep all paths stable.

6. **Worker; saved-input preparation.** Supply `preparation-inputs.json` with
   `selection_path`, `runtime_path`, `job_id`, ISO `run_date`, and integer
   `max_draft_checks`, all from the registered plan. Invoke:

   ```sh
   "$PYTHON" -P -B "$CHECKOUT/scripts/native_canary_saved_step.py" \
     --checkout "$CHECKOUT" --step preparation --inputs "$INPUTS/preparation-inputs.json" \
     --output "$PACKET/preparation"
   ```

   Outputs: preparation envelope and exact derived instruction bytes, verified
   with `verify_preparer`. On this branch the protected RunSpec constructor
   refuses `native_shared_generation_version`; stop without patches or fallback.
   After merged integration this needs a fresh complete rehearsal.

7. **Worker then independent reviewers.** Supply `composition-inputs.json` with
   `preparation_path` and `instruction_path`; compose through the shared-native
   orchestration (not the older attribution controller):

   ```sh
   "$PYTHON" -P -B "$CHECKOUT/scripts/native_canary_saved_step.py" \
     --checkout "$CHECKOUT" --step composition --inputs "$INPUTS/composition-inputs.json" \
     --output "$PACKET/composition"
   ```

   Inputs include committed merged source, verified controls, exact instruction
   bytes and observation-backed runtime. Output: verified composition. Lead
   supplies explicit nonblank system text and reviewers assess it with the
   effective production command guidance. Do not substitute prompt text after
   expectation construction.

8. **Worker; offline.** Supply `expectation-inputs.json` with `composition_path`,
   `system_path`, `config_directory` equal to the future attempt's `cli_config`.

   ```sh
   "$PYTHON" -P -B "$CHECKOUT/scripts/native_canary_saved_step.py" \
     --checkout "$CHECKOUT" --step expectation --inputs "$INPUTS/expectation-inputs.json" \
     --output "$PACKET/expectation"
   ```

   Output: exact permission expectation and recipe from reconstructed shared
   composition, current controls, system guidance and dependencies. No callback
   is armed; no attempt/config/evidence directory is created.

9. **Authorized operator; SAME OWNER D117 WORD REQUIRED. LIVE, NOT RUN HERE.**
   Supply the separately bound account-choice document for this expectation.

   ```sh
   "$PYTHON" -P -B -m data_sheets_schema.native_generation bound-permission-probe \
     --authorization "$INPUTS/authorization.json" \
     --expectation "$PACKET/expectation/expectation.json" \
     --account-choice "$INPUTS/permission-account-choice.json"
   "$PYTHON" -P -B -m data_sheets_schema.native_generation validate-probe-sequence \
     --runtime "$PACKET/runtime/runtime.json" --probe "$INPUTS/bound-permission-manifest.json" \
     --account-choice "$INPUTS/final-runtime-account-choice.json"
   ```

   The first command produces seven bound permission traces and version evidence.
   The second reads saved outputs only. Use the actual manifest location returned
   by the producer; the shown path denotes that same file, not an unpinned copy.
   A refusal stops registration; neither a generic permission probe nor fixture
   transcripts may substitute. The final-runtime choice hashes final runtime as
   subject; it differs from both preceding choices.

10. **Worker; offline.** Supply `registration-inputs.json` with
    `composition_path`, `system_path`, `permission_probe_path`, `attempt_id`,
    `attempt_directory`, `evidence_directory`, `max_draft_checks`, and explicit
    `receipt_origin_version`. Attempt basename must equal attempt ID. Future
    attempt, evidence, stages and generated output paths must remain fresh and
    disjoint from authority inputs.

    ```sh
    "$PYTHON" -P -B "$CHECKOUT/scripts/native_canary_saved_step.py" \
      --checkout "$CHECKOUT" --step registration --inputs "$INPUTS/registration-inputs.json" \
      --output "$PACKET/registration"
    ```

    Output: full production registration envelope, freshly reconstructed by the
    production verifier. Do not substitute a wire-shaped fixture envelope.

11. **Lead, independent Claude/Codex reviewers, owner; OWNER TERMS REQUIRED.**
    Archive the exact registration in the registration evidence repository on a
    branch, then record repository,
    relative path and commit in the review bundle. The author date anchors the
    registered validity interval. The lead's normal reviewed publication is
    separate; this worker does not publish. **Timestamp procedure needs lead and
    owner review before production:** the runtime already embeds `valid_from`,
    and the validator requires exact equality with the registration commit's
    author timestamp. An ordinary later `git commit` will generally differ.
    The recommendation is an explicitly agreed registration-authoring timestamp,
    preserved as the commit author date; never silently backdate or mint a date
    to make a failing packet pass. No timestamp is selected by this runbook.
    After that procedure is approved, assign `REGISTRATION_AUTHOR_DATE` to that
    exact reviewed UTC value and use these archival commands only once exact
    bytes are staged at the agreed evidence path:

    ```sh
    git -C /ABS/REGISTRATION-EVIDENCE-REPOSITORY add -- /ABS/REGISTRATION-EVIDENCE-REPOSITORY/registration.json
    git -C /ABS/REGISTRATION-EVIDENCE-REPOSITORY commit --date "$REGISTRATION_AUTHOR_DATE" -m 'Archive exact native CHORUS canary registration'
    git -C /ABS/REGISTRATION-EVIDENCE-REPOSITORY rev-parse HEAD
    ```

    Reviewers provide their own pinned documents; the owner provides terms and
    capture request. The lead assembles the bundle without inventing decisions.
    Bundle author/operator/reviewers must meet independence rules. Supply real
    CI evidence for exact source, not a URL-shaped invented success. Reconcile
    bundle v3/terms v2 and the reviewed three-command sequence byte pin before
    using the forthcoming helper2 route. This base's v2 adapter cannot assert
    those future requirements were checked.

12. **Owner; OWNER ONE-ATTEMPT WORD REQUIRED.** Review the concrete registration,
    runtime, CI, permission result and two-review bundle. Supply
    `AUTHORIZE_ONE_NATIVE_ATTEMPT` bound to their exact hashes, attempt/source/
    dependency identity, owner and timestamp. Human authorization is not a CLI
    action. The selected registration account-choice hashes the final registration
    subject and runtime. Worker can validate the saved join with
    `review-inputs.json` keys `registration_path`, `review_path`, `launch_word_path`:

    ```sh
    "$PYTHON" -P -B "$CHECKOUT/scripts/native_canary_saved_step.py" \
      --checkout "$CHECKOUT" --step review --inputs "$INPUTS/review-inputs.json" \
      --output "$PACKET/review-check"
    ```

    Output proves declared byte bindings only. It does not authenticate humans,
    establish successful CI or admit an attempt. All effectful admission gates
    still run at capture/launch.

13. **Owner or explicitly delegated lead; OWNER START DIRECTION REQUIRED.
    LIVE, NOT RUN HERE.** Confirm the actual host/AC/lid/overage/keep-awake state
    and stand down every session using the registered account, including
    monitoring. N1 v12's delegation is for one exact registration and lapses
    after thirty minutes; use the final ratified terms. Review and pin the
    helper2 sequence artifact, not these three stand-alone commands. They show
    the exact CLI inputs on this base and must execute as one authorized
    capture → guard → launch sequence without pause or unreviewed retry:

    ```sh
    "$PYTHON" -P -B -m data_sheets_schema.native_generation capture-subscription-event \
      --registration "$PACKET/registration/registration.json" \
      --review "$INPUTS/review.json" --launch-word "$INPUTS/launch-word.json" \
      --output-directory "$INPUTS/EXACT-REGISTERED-CAPTURE-DIRECTORY" \
      --account-choice "$INPUTS/registration-account-choice.json"
    "$PYTHON" -P -B -m data_sheets_schema.native_generation prepare-subscription-guard-v2 \
      --registration "$PACKET/registration/registration.json" \
      --review "$INPUTS/review.json" --launch-word "$INPUTS/launch-word.json" \
      --capture "$INPUTS/EXACT-LATEST-CAPTURE-MANIFEST.json" \
      --output "$INPUTS/NEW-GUARD.json" --account-choice "$INPUTS/registration-account-choice.json"
    "$PYTHON" -P -B -m data_sheets_schema.native_generation launch \
      --registration "$PACKET/registration/registration.json" \
      --review "$INPUTS/review.json" --ci "$INPUTS/ci.json" \
      --launch-word "$INPUTS/launch-word.json" --subscription-guard "$INPUTS/NEW-GUARD.json" \
      --subscription-guard-sha256 EXACT-GUARD-SHA256 \
      --account-choice "$INPUTS/registration-account-choice.json"
    ```

    Capture creates its claim/reservation before contacting the subscription.
    It is not an offline readiness check. Guard preparation must select the
    latest claim, and launch checks freshness plus pre-reservation margin again.
    Resolve the actual returned capture path and guard digest inside the reviewed
    sequence. Do not manually pause to fill these placeholders at launch time.
    Up to three captures in D115 is a bound, not permission here to retry; retain
    every failure/stop and obey the final sequence policy and owner word. A
    generation attempt is one-use. The second attempt, if any, needs its separately
    specified identity/review/word and N1's total-attempt bound.

14. **Worker and lead; offline readback after a genuinely authorized run.**

    ```sh
    "$PYTHON" -P -B -m data_sheets_schema.native_generation read-final \
      --registration "$PACKET/registration/registration.json" \
      --account-choice "$INPUTS/registration-account-choice.json"
    ```

    Preserve all terminal/stop/accounting/receipt evidence. Separate software
    completion from scientific acceptance. No native replicate starts until the
    ratified floor and production plan permit it.

## Rehearsal limits and retained evidence

The new saved-step helper makes the library producers addressable without inline
Python snippets. Only its review join and refusal boundaries have been exercised
on this base. Runtime production evidence, composition/expectation/registration
construction, full CI admission, real permissions and the final sequence need
rehearsal after protected integration; this document does not certify them.

The map is generated by `scripts/adhoc/map_native_packet_20261112.py` from source
signatures and declared input origins. The offline test runner and the final
handoff record exact commands, test counts, artifact paths and hashes. Never
reuse the explicitly synthetic review/CI/word bytes as a production packet.
