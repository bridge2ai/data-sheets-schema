# Native CHORUS canary runbook — DRAFT, 2026-11-12

This is preparation, not permission to execute any live step. The offline prefix
was exercised on real CHORUS inputs. The authorized scratch composition now
builds synthetic preparation, composition, seven-trace saved permission evidence,
execution registration and the current review/owner join through production
functions. The public commands still refuse the synthetic profile at the Max
subscription gate; no gate is stubbed to get past it. No capture, word journal or
attempt reservation is made. This establishes saved-document construction, not
real account state, observed permission behavior, actual CI or scientific acceptance.

Composition baseline: `79089536b698dd2dd968233da4eadc8841f76b10`, the three
observer commits, helper2 head `d2efa55014e131f92733bf2c3a90c0830214dc89`, the
builder commits and the four hash-verified protected post-images. The detached
composition and exact receipts live under
`../scratch-h3-packet-builder-20261112/composition-a/`; no protected branch file
was changed. N1 reference:
`c289eed19e37e227e04dd5e0c4fc077da54184aa`, draft v12. Ratification, independent
reviews, approved protected integration, successful full CI and merge remain
separate prerequisites. The composition has review bundle v3, owner terms v2,
`sequence_script_sha256` and `account_quiet`. The adapter reads all versions and
admission terms from the source it runs against, including the receipt instrument
constraint where no public constant exists. Its inventory records the observed
source contract. The owner has not decided the margin: the observed source value
is not a decision. Do not replace it with N1's proposed value or freeze a production
packet before ratification and matching source exist.

N1.9 lists engineering prerequisites, not the event sequence. N1.5 contains the
ordered events. This runbook uses the following crosswalk:

| This runbook | N1.9 prerequisite | N1.5 event |
|---|---|---|
| Merged source and complete-path review | 1–11 | Before event 1 |
| Durable executable and observation/final runtime | 5, 6, 7 | Before event 1 |
| Registration timestamp/addition commit and independent review | 4, 5 | Before event 1 can be complete |
| Owner terms and frozen bundle with sequence bytes | 4, 10 | Events 2 and 3 |
| Owner one-attempt word | 4 | Event 4 |
| Single reviewed sequence: capture, latest guard, launch | 2, 3, 10 | Events 5 and 6 |
| Reservation-to-dispatch measurement | 11 | Engineering prerequisite, not exercised by this no-reservation rehearsal |

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
   later agree with the registration-addition commit's explicit author date.
   Read `valid_from` from this frozen document at step 11; never choose a second
   date or adjust the runtime to mask a mismatch. Use whole-second UTC precision:
   Git author timestamps cannot represent fractional seconds.

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
   with `verify_preparer`. The protected-main branch still refuses native fields;
   the authorized scratch post-images make this stage pass in the rehearsal.
   Production must use the independently reviewed merged implementation.

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
    separate; this worker does not publish. **Settled timestamp procedure:** the
    lead reads `valid_from` from the frozen runtime embedded in the registration,
    supplies that value explicitly as the Git author date, then calls the
    production equality validator on the actual commit. The lead does not select
    a new date, alter the runtime or claim that author time is the wall-clock
    instant when Git wrote the object. The committer time remains normal Git
    metadata. `native_registration_timestamp.py` demonstrates creation only for
    synthetic documents in a new scratch repository; its read-only date and
    verification modes also support the lead's reviewed production procedure.

    The scratch test passes for matching bytes/date and refuses a commit exactly
    one second off. No production timestamp or production commit was made.
    This is N1.9 prerequisites 4/5, before N1.5 event 1 (the registration and its
    reviews complete) and before events 2/3 freeze owner terms and the bundle.
    N1 v12's equality/order need no normative change. Clarifying that the author
    date is explicitly preserved from `valid_from`, not a newly observed commit
    time, would prevent an operator from using an ordinary later timestamp.

    ```sh
    REGISTRATION_AUTHOR_DATE="$("$PYTHON" -P -B "$CHECKOUT/scripts/native_registration_timestamp.py" --registration "$PACKET/registration/registration.json" --author-date-only)"
    git -C /ABS/REGISTRATION-EVIDENCE-REPOSITORY add -- /ABS/REGISTRATION-EVIDENCE-REPOSITORY/registration.json
    git -C /ABS/REGISTRATION-EVIDENCE-REPOSITORY commit --date "$REGISTRATION_AUTHOR_DATE" -m 'Archive exact native CHORUS canary registration'
    git -C /ABS/REGISTRATION-EVIDENCE-REPOSITORY rev-parse HEAD
    "$PYTHON" -P -B "$CHECKOUT/scripts/native_registration_timestamp.py" \
      --registration "$PACKET/registration/registration.json" \
      --verify-evidence "$INPUTS/registration-commit.json"
    ```

    `registration-commit.json` contains exactly `repository`, relative `path`
    and the actual full `commit` SHA just created. Verification re-reads the
    commit object, non-merge addition, regular-file blob, exact registration bytes
    and author date through `native_launch_review._registration_commit`.
    A refusal leaves the commit/evidence intact and stops bundle construction.

    Reviewers provide their own pinned documents; the owner provides terms and
    capture request. The lead assembles the bundle without inventing decisions.
    Bundle author/operator/reviewers must meet independence rules. Supply real
    CI evidence for exact source, not a URL-shaped invented success. Reconcile
    source-derived current bundle/terms and the reviewed sequence byte pin.
    The current bundle binds the actual dependency-pinned sequence source;
    owner terms require boolean `account_quiet: true`. These are declarations,
    not authenticated owner identity or account telemetry.

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
    actual `native_launch_sequence.py` artifact. This is N1.9 prerequisite 10
    and N1.5 events 5–6: one authorized capture → latest guard → launch sequence
    without pause or retry. The delegated-start command is:

    ```sh
    "$PYTHON" -P -B -m data_sheets_schema.native_launch_sequence \
      --registration "$PACKET/registration/registration.json" \
      --review "$INPUTS/review.json" --ci "$INPUTS/ci.json" \
      --launch-word "$INPUTS/launch-word.json" \
      --output-directory "$INPUTS/EXACT-REGISTERED-CAPTURE-DIRECTORY" \
      --subscription-guard "$INPUTS/NEW-GUARD.json" \
      --packet-directory "$INPUTS/NEW-SEQUENCE-PACKET" \
      --account-choice "$INPUTS/registration-account-choice.json" \
      --direction-recorded-at OWNER_RECORDED_UTC \
      --host-confirmed-at OWNER_HOST_CONFIRMATION_UTC
    ```

    Both timestamps are actual owner records, not generated defaults. For the
    owner's own start, omit both delegated flags. The script checks both
    thirty-minute windows at entry and immediately before capture. It retains
    its exact bytes as `sequence-script.py`, exclusively claims the sequence
    packet, saves command outputs/times and stops on any refusal. Reviewers
    recompute the saved script hash and compare it with the bundle's
    `sequence_script_sha256`; `sequence.json` is not a self-authenticating hash.
    This script itself creates a sequence-start claim, so it is not invoked in
    this no-reservation rehearsal.

    Capture creates its claim/reservation before contacting the subscription.
    It is not an offline readiness check. Guard preparation must select the
    latest claim, and launch checks freshness plus pre-reservation margin again.
    The reviewed sequence resolves the actual returned capture path and guard
    digest internally. No manual pause or substitute capture is allowed.
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

The synthetic composition exercises production preparation, composition,
permission-expectation construction, saved seven-trace verification, execution
registration, current review terms and review/CI/word joins. The pure guard
builder can serialize a synthetic event; current guard preparation still needs
a recorded word state and an actual latest capture claim. No such state was
fabricated. All three public CLI commands refuse the synthetic subscription at
the D106 Max gate with genuine registration verification and no gate stubs.
This is an intentional production/synthetic boundary, not a reason to change
the synthetic auth fields into a claimed real account. The exact refusal and
all remaining per-document limits are in the full-chain handoff.

The timestamp procedure's source anchors are
`native_launch_review.py:67` (commit/addition/blob checks) and line 137 (exact
`valid_from` equality) in the pinned composition. `native_u4b_policy.py:46`
requires the fourteen-day interval; `native_capture_words.py:76` requires
`valid_from <= authorized_at <= now < valid_until`. Review timestamps cannot
follow the launch word (`native_launch_review.py:328`). Capture chronology is
checked against the word (`native_subscription_guard_v2.py:387`); freshness and
margin use capture time and the current clock, not the Git author time.

## Owner probe packet (draft only)

`scripts/draft_native_probe_packet.py` generates field-by-field drafts and their
source/owner/observation provenance. The retained real-binary-byte draft is under
`../scratch-h3-packet-builder-20261112/probe-packet-draft-v2/`:
`provisional-runtime.DRAFT.json`, `authorization.DRAFT.json`, and
`probe-packet.DRAFT.json`/`.md`. They have invalid draft wrappers and the nested
word `DRAFT_NOT_AUTHORIZED`; neither the wrapper nor the nested candidate is an
approval. No binary version is inferred from its updater filename.

The owner must supply/approve durable binary location, actual saved version/init
and account facts, explicit environment, provisional limits, fresh evidence
directory, both deadlines, owner identity, actual UTC time and D117 word.
Final limits/thinking come from the saved observation. The source-derived
margin is reported only; the outstanding owner decision is not supplied here.

The two probe commands in steps 4 and 9 make nine native-process executions on
the successful path: one observation, one version check and seven permission
traces. All intended model traffic goes to the scripted loopback provider;
bound permission tool results can include CHORUS source content in that local
provider's saved traces. The version check uses a disabled loopback endpoint.
No external model call or account usage is intended by these invocations; no
claim about actual binary behavior is made without the separately authorized
probe. The saved validator runs no native process. A failure can stop earlier
and never grants a retry.

The map is generated by `scripts/adhoc/map_native_packet_20261112.py` from source
signatures and declared input origins. The offline test runner and the final
handoff record exact commands, test counts, artifact paths and hashes. Never
reuse the explicitly synthetic review/CI/word bytes as a production packet.
