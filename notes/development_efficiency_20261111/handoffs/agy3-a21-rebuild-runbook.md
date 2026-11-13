# A21 Rebuild & Launch Runbook for the API-Only Route

Prepared by `agy3` for the Claude lead and repository owner, 2026-11-11. Read-only preparation; no commands in this runbook have been executed.

---

## 0. Current Standing Holds & Corrections Carried Forward

1. **Sequencing Hold (`D89`, `D93`, `D129`) Is Currently in Force:**
   - **D89** (`STATUS.md:777`, 2026-11-06): *"Hold A21; native comes first. agy's A21 monitor (part 56) is disarmed. The A21 registration (roster `d4ac7f88…`) stays valid at `launch-a21`/M4, and D88's launch word is suspended, not withdrawn."*
   - **D93** (`STATUS.md:767-769`, 2026-11-06): *"D35's freeze starts at the A21 rebuild: native integration lands first. A21 is then rebuilt and re-reviewed on the native-integrated main... The M4 A21 packet (roster `d4ac7f88…`) is kept as evidence. D88's word applies to it only if the owner reinstates it."*
   - **D129** (`STATUS.md:595-599`, 2026-11-09): *"Keep A21 held, per D93. The order: finish native integration first: U3-J2, then the U1+U3 PR with the D127 packets, then its review and merge. Then: agy rebuilds the A21 re-canary registration on native-integrated main, under a new label; the owner reviews it and gives the launch word within the ~$25 slice."*
   - **Status:** Nothing in `STATUS.md` releases `D89`, `D93`, or `D129`. Executing the API-only rebuild and launch on `<MAIN_AFTER_5808>` ahead of native `U1+U3` integration requires an **explicit owner release** of that sequencing hold (being requested by the Claude lead).
2. **PR `#5808` Specificity Scan Status (`exit: 1`, Not `0`):**
   - On PR `#5808` (`6792947ea6558d10c85106065b023cb57838835a`), `notes/final_generation_readiness_20261110/evidence/specificity-summary.json` records `exit: 1` with `9` violations, all under `run_controllers` at `notes/claudecode_direct/prepare_direct.py:348` (one) and `notes/matched_cborg_2026-09-13/prepare_registration.py` lines `19` (two), `20` (five), and `104` (one), and `0` under `api`. Those `9` violations are the retained open issues `#5582` through `#5590` (identical to baseline `main`), not a zero-violation pass.
3. **Slice Budget & Stop Trigger Require an Explicit Owner Choice (`D129` vs. `D58`/`D64`/`D88`):**
   - **D129** (`STATUS.md:597`) specifies that the owner gives the launch word for the rebuilt registration *"within the ~$25 slice"* (matching **D-C** item 1, `STATUS.md:92`: *"Budget: about $25 from the $420 ceiling"*).
   - **D58** (`STATUS.md:289`: *"The A21 slice rises from about $25 to $60"*), **D64** (`STATUS.md:326-327`: *"items 3, 4 and 16: one A21 attempt at $60... item 7: 'agy, stop command only'... at the trigger (about $51) or the 3 h clock"*), and **D88** (`STATUS.md:783`: *"$60 slice (D58/D64), $51 stop trigger, no --canary-baseline"*) were granted for the M4 registration `d4ac7f88…`, suspended by `D89`, and under `D93` (`STATUS.md:768`) apply *"only if the owner reinstates"* them.
   - Because CHORUS BC1 expected proxy spend is **$31.66** and capped spend is **$43.17** (`$44.25` with cache writes) (`a21_launch_packet_2026-11-05.md:23-30`), a `$25.00` cap will likely stop mid-run, whereas reinstating the `$60.00` slice (`$51.00` stop trigger + `$8.65` worst single in-flight call = `$59.65 < $60.00`) covers the full 7-call BC1 plan at caps. Section 3 presents `<SLICE_USD>` and `<TRIGGER_USD>` as an explicit owner choice at the launch word.

---

## 1. Ordered Steps After PR `#5808` Merges (`<MAIN_AFTER_5808>`)

Variables used below:
- `PRIMARY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`
- `LB=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21` (the dedicated launch-base worktree, currently detached at M4 `673838c51547278cfd79254670ec95421c7bcaf7`, with its own `.venv`, `data/preprocessed/`, `data/omission_contexts/`, and `data/ATTIC/`)
- `PY=$LB/.venv/bin/python`
- `P=<YYYY-MM-DD>a_claude-opus-5-api-bc1-a21` and `L=${P}_rep1` (new date-stamped label; increment the suffix letter if `a` exists)
- `OUT=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_${L}`

### Step 1.1 — Verify `<MAIN_AFTER_5808>` Ancestry, Idle Runner State & Move `launch-a21`
- **Who runs it:** `agy` (after explicit owner merge of PR `#5808` and owner release of `D89`/`D93`/`D129`).
- **Directory:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21` (`$LB`).
- **Commands:**
  ```bash
  git -C "$LB" fetch origin main
  git -C "$LB" rev-parse origin/main
  git -C "$LB" merge-base --is-ancestor 673838c51547278cfd79254670ec95421c7bcaf7 <MAIN_AFTER_5808>
  git -C "$LB" merge-base --is-ancestor 925d726d67cdd03fe28fdeafdde60fa27df57205 <MAIN_AFTER_5808>
  git -C "$LB" status --porcelain
  "$LB/.venv/bin/d4d" api status
  git -C "$LB" switch --detach <MAIN_AFTER_5808>
  cd "$LB" && poetry install
  "$PY" -c 'import data_sheets_schema, download; print(data_sheets_schema.__file__, download.__file__)'
  "$LB/.venv/bin/d4d" api prompts check --strict
  "$LB/.venv/bin/d4d" schema check-digest --strict
  ```
- **Persisted proof:** Save the output log to `$OUT.preflight.log`. It must contain:
  1. `HEAD` equal to `<MAIN_AFTER_5808>` and `git status --porcelain` showing only `?? poetry.toml`;
  2. `data_sheets_schema.__file__` and `download.__file__` resolving under `$LB/src/`;
  3. `d4d api status` reporting no live sweep and no lock;
  4. `d4d api prompts check --strict` and `d4d schema check-digest --strict` reporting zero drift on the `3.2.1` schema (`Dataset` and `CoreDataset` across `neutral` and `bridge2ai`).

### Step 1.2 — Build the CHORUS `generic_v10` (`BC1`) Registration, Sizing Sidecar & Batch Roster
- **Who runs it:** `agy`.
- **Directory:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21` (`$LB`), with `D4D_MANIFEST`, `CBORG_API_KEY`, and `ANTHROPIC_API_KEY` removed from the environment so no provider call is possible.
- **Commands:**
  ```bash
  env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$PY" \
    "$LB/scripts/build_api_registrations.py" \
    -p CHORUS -l "$L" --partition chorus \
    --bounded-carry-version 1 --bc1-fan-in 2 --aggregate-input-tokens 4500000 \
    --source-manifest "$LB/data/preprocessed/source_manifest.yaml" \
    --sizing-record "CHORUS=$LB/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate" \
    -o "$OUT" 2>&1 | tee "$OUT.builder.log"
  shasum -a 256 "$OUT/roster_${L}.json" "$OUT/registration_chorus_${L}.json" "$OUT/registration_chorus_${L}.sizing.json" | tee "$OUT.sha256"
  ```
- **Persisted proof:** Four non-empty files on disk:
  1. `$OUT/registration_chorus_${L}.json` (`format: "shared_generation_registration_v1"`, containing `"bounded_carry": {"version": 1, "fan_in": 2, ...}`, `"inputs.full_schema"` sha256 `bc560a3cd5d04c49e95fcbf33fa8ac349171df1a877e7e0882827bd526a95214`, `"inputs.core_schema"` sha256 `e174a7a6ec1b5eccef5ee4a8b9f8f773f48243c2d6012ff8a1b846b45a40d088`, and `"audit_limits.aggregate_input_tokens": 4500000`);
  2. `$OUT/registration_chorus_${L}.sizing.json` (`format: "typed_audit_input_sizing_record_v1"`, whose `registration_sha256` equals the SHA-256 of `registration_chorus_${L}.json` and whose `sizing.format` is `"bc1_input_sizing_v4"` with `3` workers, `2` integration groups, `1` final check = `7` calls);
  3. `$OUT/roster_${L}.json` (`format: "shared_generation_batch_roster_v2"`, 1 row for `CHORUS` / `$L` naming `registration_chorus_${L}.json` and its exact `registration_sha256`);
  4. `$OUT.sha256` and `$OUT.builder.log`, where the disk SHA-256s in `$OUT.sha256` match the `sha256=` digests printed in `$OUT.builder.log`.

### Step 1.3 — Offline `--check` Verification of the Written Registration & Roster
- **Who runs it:** `agy`.
- **Directory:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21` (`$LB`).
- **Command:**
  ```bash
  env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$PY" \
    "$LB/scripts/build_api_registrations.py" \
    -p CHORUS -l "$L" --partition chorus \
    --bounded-carry-version 1 --bc1-fan-in 2 --aggregate-input-tokens 4500000 \
    --source-manifest "$LB/data/preprocessed/source_manifest.yaml" \
    --sizing-record "CHORUS=$LB/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate" \
    -o "$OUT" --check 2>&1 | tee "$OUT.check.log"
  ```
- **Persisted proof:** `$OUT.check.log` on disk containing `✓ CHORUS: registration_chorus_${L}.json (sized: registration_chorus_${L}.sizing.json)`, `✓ Roster valid: roster_${L}.json`, and `All checks passed.`, while `$OUT.sha256` re-verified after `--check` shows all three JSON files unchanged byte-for-byte.

### Step 1.4 — No-Spend Launcher `--dry-run` Through the Exact Launch Path
- **Who runs it:** `agy` (using the same launcher, shell, and credential environment as the live launch, per the canary-first rule).
- **Directory:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21` (`$LB`).
- **Command:**
  ```bash
  "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" -- d4d api batch \
    --projects CHORUS --arm baseline --condition generic_v10 \
    --shared-generation-version 1 --shared-generation-registration "$OUT/roster_${L}.json" \
    --expect-sha256 <NEW_ROSTER_SHA256> \
    --api-playbook-version 2 --receipt-completion-version 2 \
    --replicates 1 --label-prefix "$P" \
    --max-cost-dollars <SLICE_USD> --dry-run 2>&1 | tee "$OUT.dryrun.log"
  ```
- **Persisted proof:** `$OUT.dryrun.log` on disk containing the printed `BC1` plan (`bounded_carry_version=1`, `fan_in=2`, registered maximum `8` calls / `480,000` output tokens / `4,500,000` aggregate input tokens, and the 1-run `CHORUS` roster entry), plus post-check confirmation in `$OUT.dryrun.log` that `d4d api status` still shows no sweep/lock and no directory under `$LB/data/d4d_concatenated/claudecode_api{,_core}/$L` was created.

### Step 1.5 — Independent Registration Re-Review Against M4 (`673838c51`)
- **Who runs it:** `claude` (lead, or a read-only reviewer designated by `claude` under `D50`).
- **Directory:** Read-only comparison against `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/` and `$OUT/`.
- **Persisted proof:** A dated review report saved at `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/a21_registration_review_<YYYY-MM-DD>.md` verifying that across all 266 registration identity leaves and 20 rendered model-facing sizing payloads, every byte delta from the M4 registration (`f7e9b70555521d2f73bea6636a4389543b2233b871f29a7b0782e132a3d1f458`) is accounted for by the exact post-M4 changes listed in Section 2 below (`0` unexplained differences), and recording the new `<NEW_ROSTER_SHA256>` for the owner's launch word.

---

## 2. What the M4 Packet Pinned (`673838c51`) and What Moved Since (Re-Review Scope)

Checked mechanically on `2026-11-11` by `tmp/a21-pinned-closure-20261111/a21_pinned_closure_check.json` and `tmp/a21-pinned-closure-20261111/lead_independent_check.json` in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111`.

The M4 registration (`registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json`, sha256 `f7e9b70555521d2f73bea6636a4389543b2233b871f29a7b0782e132a3d1f458`, roster sha256 `d4ac7f88f1d3ad819eb5f101e25fc09d9e4a414e776e31632a9b96568a68ff00`) pinned 7 input files, 1 runtime config file, 9 prompt/command assets, 61 unique Python source files (`53` in `selection.stage_contracts.request_code_sha256` and `59` in `bounded_carry.contract.code`), and stage/contract probes.

Between M4 (`673838c51547278cfd79254670ec95421c7bcaf7`) and current `main` (`925d726d67cdd03fe28fdeafdde60fa27df57205`) plus PR `#5808` (`6792947ea6558d10c85106065b023cb57838835a`), **only the following pinned items moved**:

| Pinned Registration Field / File | M4 (`673838c51`, Schema `3.1.0`) SHA-256 | Current `main` (`925d726d6`) + PR `#5808` (`6792947ea`, Schema `3.2.1`) SHA-256 | Cause & Effect on Model-Facing Payloads |
|---|---|---|---|
| `inputs.full_schema.sources[0]` (`src/data_sheets_schema/schema/data_sheets_schema_all.yaml`) | `9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da` (`1,442,944` B) | `bc560a3cd5d04c49e95fcbf33fa8ac349171df1a877e7e0882827bd526a95214` (at `925d726d6` `3.2.0`: `cf4e0992...`) | **PR `#5531` (`3.2.0`, `D98`–`D99`)** added `d4d:termSourceIdentifierForms` on `data_substrate`/`data_topic` and restored `data_use_permission` `multivalued: true`. **PR `#5808` (`3.2.1`, `#2975`)** aligned `FileCollection.collection_type` prose with scalar `FileCollectionTypeEnum`. Updates `schema_context` and BC1 worker/omission catalog. |
| `inputs.core_schema.sources[0]` (`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`) | `2bb8827c45a4dac40e834064a65c95cfc13d258b129c3aa1b9cbccba9ef624db` (`1,299,631` B) | `e174a7a6ec1b5eccef5ee4a8b9f8f773f48243c2d6012ff8a1b846b45a40d088` (at `925d726d6` `3.2.0`: `db4c4fa4...`) | Same **PR `#5531` (`3.2.0`)** and **PR `#5808` (`3.2.1`)** schema releases. (`G2` verified that all 4 `Dataset`/`CoreDataset` API `schema_digest` hashes—`94fb1b7b...`, `47c57805...`, `c807b62f...`, `f3943c16...`—are unchanged between `3.2.0` and `3.2.1`, having moved once at `3.1.0 -> 3.2.0`.) |
| `src/data_sheets_schema/api_runner.py` (`request_code_sha256` & `bounded_carry.contract.code`) | `365a6431eb869c76d7d06dde7698ce9ce91414a0a2f6c1ad11e60f3a84113930` | `23dcc828d171000173bd521edfbc55b38bfcf6c0adb41c6b962c10f381e911bb` | **PR `#5531` (`3.2.0`)** updated `_multivalued_of` for `data_use_permission` (`D99`) and `3.2.0` migration checks. |
| `src/data_sheets_schema/schema_digest.py` (`request_code_sha256` & `bounded_carry.contract.code`) | `150a5f005ab1ed5fdf73f927559f15a3c7dbf34a0915ff2b83896991c1fcc095` | `c30d59fe48ee9bed78bd24bc89366e926e88dbefeba228ff132335066c0af54c` | **PR `#5531` (`3.2.0`)** updated digest rendering/inventory for `D98`–`D99`. |
| `src/data_sheets_schema/bc1_audit.py` (`bounded_carry.contract.code`) | `0e43a00224aa994b765ebc22746a92d044e864ea241f93bcffb8fa2a6b77b572` | `dbcf87a804dbc486fc76702ff643838c5713ab7129c585d6a7f0a6ec442a9fd7` | **PR `#5531` (`D98`, `#5471`)** derived `bc1_neutral_term_policy_v2` from `d4d:termSourceIdentifierForms`. |
| `src/data_sheets_schema/bc1_context.py` (`bounded_carry.contract.code` & `bounded_carry.contract.context`) | `a3ec22914277e643a125b40711c10f5a7a58e1575a7ec61986bd86dd42ed465e` (`bc1_neutral_term_policy_v1`) | `1e4877b555cae75449883be925713b12f9507c804a0604906a8221d566ae8378` (`bc1_neutral_term_policy_v2`) | **PR `#5531` (`D98`, `#5471`)** updated `bounded_carry.contract.context` to `bc1_neutral_term_policy_v2` (`annotation: "d4d:termSourceIdentifierForms"`). |

### What Did NOT Move in the Registration's Pinned Closure
- **All other 57 pinned Python files** (`49` of `53` in `selection.stage_contracts.request_code_sha256` and `55` of `59` in `bounded_carry.contract.code`, including `shared_generation.py` `94b3cf68...`, `typed_audit.py` `f8461ced...`, `typed_audit_runtime.py` `448ec1ed...`, `bc1_runtime.py` `0614ea37...`, `bc1_selection.py` `6e9721a1...`, `bc1_registration.py` `416ec136...`, `receipt_completion.py` `7bc9ccd0...`).
- **All 9 prompt and command assets** in `selection.assets` and all 5 BC1 instruction hashes in `bounded_carry.contract.audit.instruction_sha256` plus the 3 omission contract hashes (`4cb51a48...`, `0b197cf8...`, `90d9e0fc...`).
- **All non-schema input pins (tracked in git and identical at both commits `673838c51` and `44b8a6595` and on disk in `launch-a21`)**: `CHORUS_preprocessed.txt` (`27625709...`), `CHORUS_chunks.yaml` (`ec9d81c5...`), `source_manifest.yaml` (`b28c3005...`), `chorus_omission_context.json` (`ac94a74b...`), `b2ai_registry_vocabularies.yaml` (`e8be07eb...`), and `.github/workflows/d4d_assistant_deterministic.config` (`0e0bd41d...`).
- **Merged PRs since M4 that are outside the registration's pinned closure:**
  - **PR `#5532` (`D101`–`D104`, `#5517`):** Modified `data/context/*_context.yaml` and `src/data_sheets_schema/evaluation/*` (evaluation applicability contexts, not `data/omission_contexts/chorus_omission_context.json`).
  - **PR `#5620` (`D105`/`D123`):** Modified `src/data_sheets_schema/cli/receipts.py` and `src/data_sheets_schema/transformation_measure{,_io}.py` (secondary post-run full-to-core transformation receipt; not in `REQUEST_CODE` or `EXTRA_CODE`).
  - **PR `#5677` (`#5676`):** Modified `tests/test_api_launcher.py` and `scripts/adhoc/*` only.
  - **PR `#5678` (`#5673`):** Modified `src/data_sheets_schema/prompt_registry.py` and `tests/test_prompt_registry.py` (`prompt_registry.py` is not in `REQUEST_CODE` or `EXTRA_CODE`, and `canonical_hashes.yaml` is unchanged).
  - **PRs `#5665`, `#5709`, `#5710`, `#5711`, `#5814`, `#5835`:** Modified scanner skill files, native attribution v2 / supervisor modules, tests, CI shard weights, and review notes; none is in the API registration's pinned file set.

---

## 3. Owner Launch Step, Stop Rule & Source Decisions

### Governing Decisions (with `STATUS.md` Line Citations)
- **Per-action launch word naming the registration SHA-256:**
  - **D07** (`STATUS.md:24`): *"$100 generic_v10 API pilot. CHORUS gets a $15 pilot plus $15 contingency. At most 2 billed attempts per cell. Each launch needs an explicit word naming the registration sha256."*
  - **D22** (`STATUS.md:23`): *"Withdraw them all: no standing authorizations. Every generic_v10 generation and evaluation needs its own owner word."*
- **Operator who runs the launch command:**
  - **D43** (`STATUS.md:186-188`): *"D43 (re-canary operator): 'You launch it (Recommended)'. This amends D41's operator clause. The owner runs the exact launch command from claude's launch packet, after giving the word on the sha256. agy and claude monitor read-only."*
- **Slice budget, stop trigger, who may run `d4d api stop`, wall-clock cap, and no `--canary-baseline`:**
  - **D58** (`STATUS.md:287-291`): *"BC1 is fixed for all projects. The A21 slice rises from about $25 to $60. The CHORUS re-canary runs under the fixed BC1."*
  - **D64** (`STATUS.md:326-332`): *"items 3, 4 and 16: one A21 attempt at $60, with redelivery decided after A21 through an amendment and a diagnostic canary; item 7: 'agy, stop command only' (not the recommendation). agy runs only `d4d api stop` at the trigger (about $51) or the 3 h clock; this amends D41/D43's monitor-only rule for A21... item 29: A21 descriptive for good... item 6: a 3 h wall clock."*
  - **D88** (`STATUS.md:782-785`): *"The owner selected 'Launch d4ac7f88 at $60': 'I have reviewed the registration. Launch word: d4ac7f88f1d3ad819eb5f101e25fc09d9e4a414e776e31632a9b96568a68ff00, $60 slice (D58/D64), $51 stop trigger, no --canary-baseline. I run the §4 command myself (D43).'"*
  - **D89 & D93** (`STATUS.md:777`, `STATUS.md:768`): `D89` suspended `D88`, and `D93` recorded that *"D88's word applies to it only if the owner reinstates it."*
  - **D129** (`STATUS.md:597`): *"agy rebuilds the A21 re-canary registration on native-integrated main, under a new label; the owner reviews it and gives the launch word within the ~$25 slice."*
  - **Owner budget choice required in the launch word:** Choose either **(Option A — reinstate D58/D64/D88)** `<SLICE_USD>=60.00` with `<TRIGGER_USD>=51` (covers expected `$31.66` and capped `$43.17`–`$44.25` plus `$8.65` worst single in-flight call = `$59.65 < $60.00`), or **(Option B — D129/D-C literal figure)** `<SLICE_USD>=25.00` with `<TRIGGER_USD>=16` (`$25.00 - $8.65 = $16.35`, noting that expected CHORUS BC1 spend is `$31.66`).

### Exact Launch Command (Run Personally by the Owner, `D43`)
In the owner's terminal (with `CBORG_API_KEY` set in the environment):
```bash
LB=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21
PY=$LB/.venv/bin/python
P=<YYYY-MM-DD>a_claude-opus-5-api-bc1-a21
L=${P}_rep1
REG=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_${L}
LOGS=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/codex_logs

"$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" --launch \
  --log "$LOGS/chorus_a21_${L}.log" -- d4d api batch \
  --projects CHORUS --arm baseline --condition generic_v10 \
  --shared-generation-version 1 --shared-generation-registration "$REG/roster_${L}.json" \
  --expect-sha256 <NEW_ROSTER_SHA256> \
  --api-playbook-version 2 --receipt-completion-version 2 \
  --replicates 1 --label-prefix "$P" \
  --max-cost-dollars <SLICE_USD> --yes
```

### Read-Only Monitoring & Stop Command (`D57`, `D64` Items 6 & 7)
- **At launch (`D57`, `STATUS.md:281-283`):** Record the detached launcher PID and the initial `latch_journal.jsonl` head SHA-256 printed in `$LOGS/chorus_a21_${L}.log`.
- **Read-only monitoring (`claude` and `agy`):**
  ```bash
  "$PY" "$LB/scripts/api_dollar_readout.py" --label "$L" --cap <SLICE_USD> --trigger <TRIGGER_USD> --watch
  ```
- **Stop rule (`D64` items 6 & 7, `STATUS.md:327, 332`):** If settled cost plus worst-case pending in-flight call reaches `$<TRIGGER_USD>` (`$51.00` under a `$60.00` slice), or wall-clock time reaches **3 hours** from launch, **only `agy` (or the owner)** runs:
  ```bash
  "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" -- d4d api stop --label-prefix "$P"
  ```
  and records the terminal journal-head SHA-256 (`D57`). Under `D56` (`STATUS.md:277-280`), a stopped or failed run is terminal and never resumed without a new owner decision.

---

## 4. Canary Verification Checklist (`A21`) & Batch Gate (`docs/final-generation-acceptance.md`)

### A. Files That Must Be on Disk and Non-Empty in `$LB`
Under `FULL_DIR=$LB/data/d4d_concatenated/claudecode_api/$L` and `CORE_DIR=$LB/data/d4d_concatenated/claudecode_api_core/$L`:
1. **Final full & Core datasheets (`G1` / `G3` §1–§2):**
   - `$FULL_DIR/CHORUS_full.yaml` and `$CORE_DIR/CHORUS_core.yaml` (non-empty YAML; header comments `# D4D Datasheet for CHORUS Dataset` / `# D4D Core Datasheet for CHORUS Dataset` and `# Arm: BASELINE (input documents only)`; valid against `3.2.1` full/Core schemas; `FileCollection.collection_type` scalar in `{raw_data, processed_data, simulated_data,harmonized_data,other}` where populated; Core derivation drift `0` and `d4d_pair_consistency` errors `0`).
2. **Evidence & provenance sidecars (`G3` §1, `D105`/`D123`):**
   - `$FULL_DIR/CHORUS_coverage_receipt.yaml` (`receipt_instrument_version: 4`, `bundle_md5` matching `CHORUS_preprocessed.txt`, `chunks` covering all declared chunk IDs);
   - `$FULL_DIR/CHORUS_generation_provenance.yaml` (recording `<MAIN_AFTER_5808>`, `registration_sha256`, and `3.2.1` schema digests);
   - `$FULL_DIR/CHORUS_audit_report.md` (verified against `report_claims.py` and `evidence_assertions.py`);
   - `$FULL_DIR/intermediate/CHORUS_receipt_completion_result.json` (with `receipt_after_sha256` matching the effective receipt);
   - Secondary non-gating full-to-core transformation receipt (`D105`/`D123`, `d4d receipts emit-transformation` / `verify-transformation`).
3. **Runtime integrity & usage ledger (`D41`, `D55`–`D57`):**
   - `$FULL_DIR/latch_journal.jsonl` (hash-chained journal whose start and terminal heads match the monitor record, `0` overrides or resets) and `$FULL_DIR/usage_ledger.json`.

### B. Counters That Must Have Moved
1. **Usage ledger & readout counters (`usage_ledger.json` and `api_dollar_readout.py --json`):**
   - Settled call count `> 0` across all required phases (`full`, `receipt_completion`, the `7` BC1 typed-audit calls [`3` workers, `1` omission, `2` groups, `1` final], `reconcile_full`, `reconcile_core`, and `report` [`+ report_regate` if triggered]);
   - Typed-audit call count `<= 8` (`audit_limits.max_calls`), typed-audit settled input tokens `<= 4,500,000` (`audit_limits.aggregate_input_tokens`), and typed-audit settled output tokens `<= 480,000` (`audit_limits.aggregate_output_tokens`);
   - Total settled cost `<= <SLICE_USD>` (`$60.00` or `$25.00`), `abandoned_calls == 0`, and `transport_attempts == 1` per typed call.
2. **Receipt & snippet verification counters (`d4d api verdict`, `d4d runs check --strict`, `d4d receipts check --strict`):**
   - Unverified snippet count `== 0` (`100%` of quoted snippets verified against `CHORUS_preprocessed.txt`);
   - Phase-1 `receipted_part` coverage (`with_receipt / receiptable`, `D37`) reported cleanly (`coverage_floor` is `{"state": "pending", "mode": "diagnostic_pilot"}` for the canary).

### C. What `docs/final-generation-acceptance.md` Requires Before Any 15-Run Batch Launch
Per `docs/final-generation-acceptance.md` (§5–§7 on PR `#5808` `6792947ea6558d10c85106065b023cb57838835a`) and `D58`/`D64`:
1. All automated product checks (`scripts/adhoc/check_final_generation_products_20261110.py`, `d4d api verdict`, `d4d runs check --strict`, `d4d receipts check --strict`) pass on the `A21` CHORUS output pair with zero hand edits (`D41`/`D53`).
2. Blind source review by a fresh Claude session + Codex CLI pass (`D36`, `STATUS.md:132-135`), plus blind audit-recall observations pinned to `original_full`'s SHA-256 (`D19`), signed by the owner.
3. The post-`A21` owner decision packet (`STATUS.md:824-828`) is resolved by the owner based on `A21`'s measured cost:
   - the batch budget figure and funded project prefix (`CHORUS -> CM4AI -> VOICE -> AI_READI -> VOICE_PEDIATRIC -> Kids First`);
   - the sizing-evidence route for non-CHORUS projects (`R1` sizing runs, `R2` builder change, or `R3` descoping);
   - an explicit new owner launch word (`D07`, `D22`) naming the multi-project batch roster SHA-256.

---

## 5. What Can Be Exercised for Free Before PR `#5808` Merges (Described Only; Do Not Run)

- **`scripts/build_api_registrations.py --dry-run` (In-Memory Registration, BC1 Sizing & Roster Check):**
  - Passing `--dry-run` to `scripts/build_api_registrations.py` (`lines 1750-1752, 2028-2034`) executes `prepare_registration(...)`, `bc1_registration.size_inputs(...)`, `bc1_registration.check_sizing_record(...)`, `sg.parse_registration(...)`, and `build_roster(..., write_to_disk=False)` **entirely in memory without creating or writing any file on disk**. Using a scratch label (e.g., `-l preview_bc1_a21_rep1 -o /tmp/preview_a21_unused`) avoids touching any real label or `plans/` path.
  - **What `d4d-executions/claude-pr5808-combined-20261111` has vs. what it lacks on disk:**
    1. **Present in `claude-pr5808-combined-20261111`:** `src/**` (including the `3.2.1` schemas `bc560a3c...` and `e174a7a6...`), `.claude/**`, `.github/workflows/d4d_assistant_deterministic.config`, and `tests/fixtures/audit_batches/chorus_v10_2026-10-22a/{CHORUS_full,CHORUS_core,CHORUS_coverage_receipt}.yaml`.
    2. **Absent from `claude-pr5808-combined-20261111`'s sparse checkout:**
       - `config/audit_partitions.yaml` (`AUDIT_PARTITION_FILES`, read when `--partition chorus` is passed). Either `git -C .../claude-pr5808-combined-20261111 sparse-checkout add config` must materialize that 36-line tracked file, **or** `--partition chorus` must be replaced on the preview command line by its explicit bounds (`--max-paths 80 --max-inventory-bytes 12288 --max-workers 4 --aggregate-input-tokens 4500000`).
       - `data/preprocessed/*`, `data/omission_contexts/*`, and `data/ATTIC/*`. All three can be supplied read-only from `launch-a21/data/` via CLI flags without copying data into the preview worktree:
         - `--source-manifest "$LB/data/preprocessed/source_manifest.yaml"` (which also anchors `CHORUS_preprocessed.txt` and `CHORUS_chunks.yaml` inside `$LB/data/preprocessed/`),
         - `--context "$LB/data/omission_contexts/chorus_omission_context.json"` (required because `build_api_registrations.py:1163` otherwise searches `<worktree>/data/omission_contexts/`),
         - `--sizing-record "CHORUS=$LB/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate"`.
    3. **Import-isolation requirement (`build_api_registrations.py:74-90`):** Because `claude-pr5808-combined-20261111` has no `.venv`, invoking `$LB/.venv/bin/python` directly with `--worktree` will fail the mixed-checkout guard (`_selected_package.__path__` points to `$LB/src`). It must be invoked with `python -S` and explicit `PYTHONPATH`:
       ```bash
       PREVIEW=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111
       SITE=$LB/.venv/lib/python3.13/site-packages
       env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY \
         PYTHONPATH="$PREVIEW/src:$SITE" "$LB/.venv/bin/python" -S \
         "$PREVIEW/scripts/build_api_registrations.py" --worktree "$PREVIEW" \
         -p CHORUS -l preview_bc1_a21_rep1 \
         --max-paths 80 --max-inventory-bytes 12288 --max-workers 4 --aggregate-input-tokens 4500000 \
         --bounded-carry-version 1 --bc1-fan-in 2 \
         --source-manifest "$LB/data/preprocessed/source_manifest.yaml" \
         --context "$LB/data/omission_contexts/chorus_omission_context.json" \
         --sizing-record "CHORUS=$LB/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate" \
         -o /tmp/preview_a21_unused --dry-run
       ```
  - **Why `d4d api batch --dry-run` cannot run before the merge:** `d4d api batch --dry-run` requires the roster and registration JSON files to exist on disk (`build_api_registrations.py:1500-1510`) and checks `D76` single-checkout path ownership across `inputs.*` (`$LB` vs. `$PREVIEW`). It must run in Step 1.4 after `<MAIN_AFTER_5808>` is checked out in `$LB`.

---

## 6. Open Items Not Verified in This Read-Only Pass (Marked Unverified)

1. **Owner release of `D89` / `D93` / `D129` sequencing hold:** **Unverified** in `STATUS.md` (currently being requested by the Claude lead).
2. **Owner choice of A21 slice budget (`$60.00` with `$51.00` stop trigger under `D58`/`D64`/`D88` vs. `~$25.00` slice under `D129`):** **Unverified** for the post-`#5808` rebuild.
3. **Owner merge approval for PR `#5808` (`6792947ea6558d10c85106065b023cb57838835a`) and resulting `<MAIN_AFTER_5808>` commit SHA + post-merge `main` CI run ID:** **Unverified** (PR `#5808` is open at `6792947ea`).
4. **Exact post-`<MAIN_AFTER_5808>` registration, sizing sidecar, and roster SHA-256 digests (`<NEW_ROSTER_SHA256>`) and byte/token delta in `registration_chorus_${L}.sizing.json` from `3.2.0`/`3.2.1` schema additions:** **Unverified** (no registration build or dry-run was executed in this read-only pass).
5. **Live `CBORG_API_KEY` presence and validity in the owner's launch shell:** **Unverified** (credentials are never inspected or printed).
6. **Two calibration review notes (`bc1_fit_calibration_claude_2026-10-28.md` and `bc1_8f83d6cb3_claude_review_2026-10-28.md`):** Their SHA-256 constants hard-coded in `bc1_registration.py` (`7024eec0...` and `c705afbb...`) are unchanged because `bc1_registration.py` (`416ec136...`) is unchanged, and the notes themselves are not tracked in git and were not located in the inspected checkouts (**unverified, not absent**).

---

## Rehearsal on the merge preview

Per follow-up assignment `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy3-a21-builder-rehearsal.md`, one single no-write builder rehearsal (`--dry-run`) was executed against the local merge preview worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111` (commit `44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9`, merging `main` `925d726d` and PR `#5808` `6792947e`), reading inputs from `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/` and writing rehearsal artifacts only to `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/tmp/a21-builder-rehearsal-20261111/`.

1. **Exact Command Executed** (saved in `tmp/a21-builder-rehearsal-20261111/command.txt`):
   ```bash
   env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY PYTHONDONTWRITEBYTECODE=1 \
     PYTHONPATH="/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/src:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/.venv/lib/python3.13/site-packages" \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/.venv/bin/python -S \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/scripts/build_api_registrations.py \
     --worktree /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111 \
     -p CHORUS -l preview_bc1_a21_rep1 --partition chorus \
     --bounded-carry-version 1 --bc1-fan-in 2 --aggregate-input-tokens 4500000 \
     --source-manifest /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/preprocessed/source_manifest.yaml \
     --context /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/omission_contexts/chorus_omission_context.json \
     --sizing-record CHORUS=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate \
     -o /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/tmp/a21-builder-rehearsal-20261111/unused-out --dry-run
   ```
   - Note on `--partition chorus`: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/config/audit_partitions.yaml` already resolves `--partition chorus` to `max_paths: 80`, `max_inventory_bytes: 12288`, `max_workers: 4`, `aggregate_input_tokens: 4500000`, `bounded_carry_version: 1`, `bc1_fan_in: 2`, and `expected_projects: [CHORUS]` (`scripts/build_api_registrations.py:1395-1455`).

2. **Exit Status** (saved in `tmp/a21-builder-rehearsal-20261111/exit_code.txt`):
   - `0` (first and only invocation).

3. **Full Printed Output** (saved in `tmp/a21-builder-rehearsal-20261111/rehearsal.log`):
   ```text
   Building registrations for ['CHORUS'] (arm: baseline, labels: ['preview_bc1_a21_rep1'])...
     ✓ CHORUS: registration_id=generic-v10-chorus-preview_bc1_a21_rep1 sha256=9d0a0eadb03aecc95629bf5e8b016badecc84c92d244b18e5e3631f97408b9b1 context_sha256=ac94a74bd0d7d6c656564d67e656c7dbcf6627dca4c147a876eded072a81a3b0
       BC1 actual record: 3 workers, 2 integration groups and one final check; 7 calls in this plan
       Future response scenarios are hypothetical; actual provider counts remain required.
       sizing record registration_chorus_preview_bc1_a21_rep1.sizing.json sha256=9d75bb76b894e6f903bd5970dcd3c6dd5d99da6e9475d1c9e824cdc93ee0574f
     ✓ Roster with 1 rows: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111/tmp/a21-builder-rehearsal-20261111/unused-out/roster_preview_bc1_a21_rep1.json (sha256=9cd1e97135740269f4b0658aa8e9d4c7daf1fe471851f5e0342c8a10ca39455a)
   [dry-run] Validated registrations and roster in memory without writing to disk.
   ```

4. **Printed Digests (Preview Values Only — Will Not Match Real Post-Merge `launch-a21` Values):**
   - **Preview `registration_id`:** `generic-v10-chorus-preview_bc1_a21_rep1`
   - **Preview registration SHA-256:** `9d0a0eadb03aecc95629bf5e8b016badecc84c92d244b18e5e3631f97408b9b1` (embeds preview worktree commit `44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9`, preview `--worktree` path, preview label `preview_bc1_a21_rep1`, and preview `-o .../unused-out` paths; the real post-merge digest will differ).
   - **Context SHA-256 (`chorus_omission_context.json`):** `ac94a74bd0d7d6c656564d67e656c7dbcf6627dca4c147a876eded072a81a3b0` (matches M4).
   - **Preview sizing sidecar (`registration_chorus_preview_bc1_a21_rep1.sizing.json`) SHA-256:** `9d75bb76b894e6f903bd5970dcd3c6dd5d99da6e9475d1c9e824cdc93ee0574f` (preview value only; will change when rebuilt with the real `registration_id` and post-merge registration SHA-256).
   - **Preview roster (`roster_preview_bc1_a21_rep1.json`) SHA-256:** `9cd1e97135740269f4b0658aa8e9d4c7daf1fe471851f5e0342c8a10ca39455a` (preview value only; will change when rebuilt with the real `launch-a21` registration path, sizing sidecar path, and SHA-256s).

5. **BC1 Sizing Line and Printed Warnings/Notes:**
   - **BC1 sizing line:** `BC1 actual record: 3 workers, 2 integration groups and one final check; 7 calls in this plan` (validated in memory against `--aggregate-input-tokens 4500000` and per-call rooms by `bc1_registration.check_sizing_record`).
   - **Printed notes:** `Future response scenarios are hypothetical; actual provider counts remain required.` and `[dry-run] Validated registrations and roster in memory without writing to disk.`
   - **Printed warnings:** None (`0` warnings on stdout or stderr).

6. **Before / After Proof That Nothing Was Written (`before.txt` vs. `after.txt` in `tmp/a21-builder-rehearsal-20261111/`):**
   - `launch-a21` (`git rev-parse HEAD`): `673838c51547278cfd79254670ec95421c7bcaf7` before and after.
   - `launch-a21` (`git status --porcelain`): `?? poetry.toml` before and after.
   - `$PREVIEW` (`claude-pr5808-combined-20261111` `git rev-parse HEAD`): `44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9` before and after.
   - `$PREVIEW` (`git status --porcelain`): empty before and after.
   - `tmp/a21-builder-rehearsal-20261111/unused-out`: `ABSENT` after the run (neither the directory nor any registration, sizing sidecar, or roster file was created on disk).
   - `find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans -newer .../marker.before`: zero files in `launch-a21/data` or `launch-a21/src`; the only file under `d4d-executions/plans` newer than `marker.before` was the external background monitor log `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/coordination_helpers/monitor_events.log` (no plan, roster, or registration file under `plans/` was touched).

7. **What This Rehearsal Does and Does Not Establish:**
   - **Does establish:**
     - Against the combined `3.2.1` merge preview (`44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9`), `scripts/build_api_registrations.py` with `--partition chorus --bounded-carry-version 1 --bc1-fan-in 2 --aggregate-input-tokens 4500000` cleanly captures both the `3.2.1` full schema (`src/data_sheets_schema/schema/data_sheets_schema_all.yaml`) and the `3.2.1` Core schema (`data_sheets_schema_core.yaml`), validates the 50 pinned code files and `bc1_neutral_term_policy_v2`, sizes the CHORUS `10-22a` record into `3` workers, `2` integration groups, and `1` final check (`7` calls total), and passes both `shared_generation.parse_registration` and `bc1_registration.check_sizing_record` within the `4,500,000` aggregate input token bound (`rehearsal.log`, exit `0`).
     - `--dry-run` performs full in-memory registration, sizing, and roster validation without creating `-o` or modifying `launch-a21` or `$PREVIEW`.
   - **Does not establish:**
     - The real post-merge registration SHA-256, sizing sidecar SHA-256, or `<NEW_ROSTER_SHA256>` (those depend on `<MAIN_AFTER_5808>`, the `launch-a21` worktree path, the real date-stamped label, and the real `d4d-executions/plans/` output directory).
     - The exact per-scenario token numbers inside `registration_chorus_${L}.sizing.json` on disk (since `--dry-run` validates in memory and does not write the sidecar file).
     - `d4d api batch --dry-run` launcher admission (which requires on-disk registration/roster files and single-checkout `D76` alignment in `launch-a21` after `<MAIN_AFTER_5808>` is checked out).
     - Human owner release of `D89` / `D93` / `D129` or merge approval for PR `#5808`.
