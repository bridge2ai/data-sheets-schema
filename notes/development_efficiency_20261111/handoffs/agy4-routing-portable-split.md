# AGY4 Read-Only Design: Shortening the `routing-portable` Dedicated CI Lane

- **Worker**: `agy4` (`E4`)
- **Date**: `2026-11-11`
- **Track**: CI efficiency (second priority), read-only design
- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-routing-portable-split.md`
- **Inspected source tree (read-only)**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111` (`main` `925d726d` + PR `#5808`)

---

## 1. Where the 31 Minutes Go

### 1.1 Saved Job and Step Timings Across Retained CI Runs

All figures below come from the saved GitHub Actions API responses and logs in this workspace; nothing was fetched.

| Run ID | Context | `routing-portable` Job Wall | Step 5 (`Run the required offline API case`) | Non-Test Job Overhead (Steps 1–4, 6–15) | Sibling `routing-regate` Step 5 | Sibling `routing-default-layout` Step 5 | Sibling `routing-dispatch` Step 5 | Saved Evidence Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `42947560899` | PR `#5808` (baseline) | **`1898s` (`31m38s`)** | **`1858s` (`30m58s`)** | `40s` (`2s` queue, `35s` setup, `3s` upload/post) | `574s` (`9m34s`) | `582s` (`9m42s`) | `643s` (`10m43s`) | `tmp/ci-observed-42947560899/run.json:2772-3251`, `post_ci_analysis_corrected.json:319-335` |
| `42916359440` | PR reference | **`1953s` (`32m33s`)** | **`1916s` (`31m56s`)** | `37s` | `591s` (`9m51s`) | `587s` (`9m47s`) | `845s` (`14m05s`) | `handoffs/captures-20261111/agy1-tab-20261111T072934Z.txt:425` |
| `42953302794` | `main` push | **`1892s` (`31m32s`)** | **`1865s` (`31m05s`)** | `27s` | `568s` (`9m28s`) | `584s` (`9m44s`) | `821s` (`13m41s`) | `tmp/ci-main-42953302794/run.json` (`job 130302438847`) |
| `42958252720` | PR `#5840` | **`1410s` (`23m30s`)** | **`1381s` (`23m01s`)** | `29s` | `644s` (`10m44s`) | `686s` (`11m26s`) | `835s` (`13m55s`) | `tmp/ci-evidence-42958252720/run-raw.json` (`job 130318406836`) |
| `42963052291` | PR `#5840` | **`1352s` (`22m32s`)** | **`1327s` (`22m07s`)** | `25s` | `591s` (`9m51s`) | `739s` (`12m19s`) | `562s` (`9m22s`) | `tmp/analysis-replacement-ci-20261111T053958Z/summary.json:18-74` |

In the baseline PR run `42947560899` (`job 130283922669`, `tmp/ci-observed-42947560899/run.json:3140-3251`), the `1898s` (`31m38s`) job wall time breaks down by step as:
- **Queue delay (`created_at` `02:39:57Z` to `started_at` `02:39:59Z`)**: `2s` (measured).
- **Step 1 (`Set up job`)**: `1s` (`02:40:00Z` to `02:40:01Z`, measured).
- **Step 2 (`Check out repository`)**: `22s` (`02:40:01Z` to `02:40:23Z`, measured).
- **Step 3 (`Initialise the FAIRSCAPE schema submodule`)**: `1s` (`02:40:23Z` to `02:40:24Z`, measured).
- **Step 4 (`Set up the cached project environment`)**: `10s` (`02:40:24Z` to `02:40:34Z`, measured).
- **Step 5 (`Run the required offline API case`)**: **`1858s` (`30m58s`, `02:40:34Z` to `03:11:32Z`, measured)**.
- **Step 6 (`Verify that the test run left the checkout clean`)**: `0s` (`03:11:32Z` to `03:11:32Z`, measured).
- **Step 7 (`Upload the test report`)**: `2s` (`03:11:32Z` to `03:11:34Z`, measured).
- **Steps 13–15 (`Post Set up...`, `Post Check out...`, `Complete job`)**: `3s` (`03:11:34Z` to `03:11:37Z`, measured).

### 1.2 Inside Step 5 (`1858s` in `42947560899`): Measured Bounds vs. Unmeasured Sub-Call Splits

The workflow step runs a **single-process** pytest command on the 4-vCPU `ubuntu-latest` runner (`.github/workflows/main.yaml:102-111`), leaving 3 of the 4 logical vCPUs idle:
```bash
poetry run python -m pytest tests -v -p no:cacheprovider -p utils.pytest_shard \
  --ci-lane="routing-portable" --junitxml="junit-py3.12-api-routing-portable.xml"
```
The JUnit XML artifact `tests-py3.12-api-routing-portable` (`1,205` bytes in `agy-ci-timing-refresh-20261111/tmp/run-42916359440/artifacts_roster.json:66-82`) was not downloaded in the saved evidence directories (only ordinary-shard XMLs `tests-py3.12-shard1..8` and `shard8.log` were saved), and JUnit XML records only a single testcase `time` attribute for `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` as a whole. Consequently, **individual sub-call timestamps inside `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` are `unmeasured` directly**, but the **sibling-lane differential in the same run (`42947560899`)** measures the exact prefix versus the additional `recheck_completed` reconstructions:

1. **Single-process pytest collection and deselection (`utils/pytest_shard.py:176-183`)**:
   - Collects all 674 test files (`23,272` items) in 1 process, selects `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes`, and deselects `23,271` items.
   - Exact single-process collection time in `routing-portable`: **unmeasured** (for reference, 4-worker xdist collection on Shard 8 took **`69.25s`** in `agy-ci-timing-refresh-20261111/tmp/run-42947560899/shard8.log:354-378`).
2. **Module fixture `draft_files` (`tests/test_source_heading_runtime_api.py:21-41`)**:
   - Calls `draft.prepare(output_path=..., schema_path=..., mappings_path=..., supplement_path=...)` (`src/data_sheets_schema/source_heading_routing.py:589-600`), which captures the 6-file LinkML schema closure (`_capture_schema`), runs `ComprehensiveSSSOMGenerator.from_captured` + `render_sssom` (`_catalog` at `lines 240-304`), builds `_inventory`, and writes `supplement.yaml`.
   - Exact isolated duration: **unmeasured** (`~15s–20s` estimate noted in `handoffs/captures-20261111/agy1-tab-20261111T072934Z.txt:515`).
3. **Test setup `selected_spec(tmp_path, draft_files)` (`tests/test_source_heading_runtime_api.py:44-89`, called at `line 268`)**:
   - Builds `specification(tmp_path)`, `chunking.build_manifest(bundle, profile='d4d_full_Heather')`, `declaration(bundle, manifest)`, `routing.prepare_condition(...)` (`src/data_sheets_schema/source_heading_runtime.py:291-303` -> `_derive` -> `draft._check_captured_files` -> `_catalog`), and `registration_for(base, condition=condition)`.
   - Exact isolated duration: **unmeasured**.
4. **The single `api.execute(spec, client=c)` (`tests/test_source_heading_runtime_api.py:270`)**:
   - Executes the 7-phase scripted offline pipeline (`full`, `receipt_completion`, `typed_audit_worker`, `typed_audit_omission`, `typed_audit_integration`, `reconcile_full`, `report`), each checking generation and routing context (`src/data_sheets_schema/source_heading_admission.py:182-218` -> `routing.check_condition` -> `_catalog`), LinkML validation, receipt completion, typed-audit reconstruction, `complete.measure_form`, and `complete.publish_completed(spec)` (`src/data_sheets_schema/source_heading_completed.py:920-951`), which calls `capture_completed(spec)` (`lines 443-506`), including **1 internal `recheck_completed(raw)` call at `line 505`**.
   - Exact isolated duration: **unmeasured** on its own, **measured jointly with (1)–(3) and 2 explicit `recheck_completed` calls by `routing-default-layout` (`582s` Step 5 in `42947560899`) and `routing-regate` (`574s` Step 5 in `42947560899`)**.
5. **The 21 explicit `recheck_completed` reconstructions in `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` (`tests/test_source_heading_runtime_api.py:272-388`)**:
   - Look at `test_actual_default_layout_completed_capture` (`routing-default-layout`, `tests/test_source_heading_runtime_api.py:534-623`): it runs the **exact same prefix** — single-process pytest collection, `draft_files`, `selected_spec`, `api.execute(spec, client=c)` (with its 1 internal `recheck_completed` inside `publish_completed`), `initial = complete.recheck_completed(raw)` (`line 557`), and `CliRunner().invoke(cli, ['api', 'check-routing-completed', str(captured_file)])` (`line 616`) — in **`582s` (`9m42s`)** in `42947560899`.
   - `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` (`routing-portable`, `lines 258-391`) executes that exact same work **plus 19 additional `recheck_completed` calls** (`#2` at `line 317` and the 18 payload mutations `#4–#21` at `lines 321-388`):
     - **Measured differential in `42947560899`**: `1858s (routing-portable Step 5) - 582s (routing-default-layout Step 5) = 1276s (21m16s)` across the 19 additional `recheck_completed` calls (**`67.2s` mean per additional `recheck_completed` call**).
     - Counting all **21 explicit `recheck_completed` calls** in `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` (`#1` at `line 272`, `#2` at `line 317`, `#3` via `CliRunner` at `line 318`, and `#4–#21` across the 18 mutations at `lines 321-388`), a full-pass `recheck_completed` call takes `~75s`, so:
       - **`collection + draft_files + selected_spec + api.execute` (`lines 258-270`, including the 1 internal `recheck_completed` at `source_heading_completed.py:505`)**: **`~432s` (`7m12s`)** (`582s - 2 * 75s`).
       - **`initial = complete.recheck_completed(raw)` (`line 272`, Call `#1`)**: **`~75s` (`1m15s`)**, making the pre-sandbox prefix (`lines 258-273`) **`~507s` (`8m27s`)**.
       - **In-sandbox unmodified portable checks (`lines 317-320`, Calls `#2` and `#3`)**: **`~150s` (`2m30s`)**.
       - **In-sandbox 18 tamper/claim mutation `recheck_completed` calls (`lines 321-388`, Calls `#4–#21`)**: **`~1201s` (`20m01s`)**.

### 1.3 Complete Inventory of All 21 Explicit `recheck_completed` Calls and Their Reconstruction Depth

In `src/data_sheets_schema/source_heading_completed.py:881-908`, `recheck_completed(raw)` executes 10 sequential verification stages:
1. `_decode(raw)` (`line 890`)
2. `_roster(selection, reader)` (`line 891`) — parses registration and runs `_authority(reg, ..., reader)` (`lines 151-166`), which calls `sg._capture_bytes(..., captured_only=True)` and `routing.check_condition` (`source_heading_runtime.py:306` -> `_derive` -> `draft._check_captured_files` -> `_catalog` SSSOM rebuild).
3. `_spec(selection, reader)` (`line 893`) — builds `_CompletedSpec`, runs `_authority` a **second time** (`line 305`, including a second `_catalog` SSSOM rebuild), validates ledger structure (`line 318`), computes `spec.input_identity()` (`line 322` -> `sg.digest_text` -> `SchemaView`), and verifies `record['api_usage'] == data['rows']` (`line 326`) and snapshot index (`lines 330-350`).
4. `_receipt(spec)` (`line 894`) — checks receipt request/response (`lines 369-388`, calling `spec.input_identity()` again) and validates `original_full` via `_validator_lines` (`JsonSchemaGenerator` over `captured_view(full_schema)`, `lines 391-392`).
5. `_typed(spec)` (`line 895`) — calls `typed_audit_runtime._rebuild` (`line 402`), reconstructing all 3 typed-audit stages (`worker`, `omission`, `integration`), each calling `routing.check_condition` (`_catalog` SSSOM rebuild × 3), and runs `typed.check(assembly, derivations=typed.DerivationCache())` (`line 417`).
6. `_ordinary(spec)` (`line 896`) — calls `admission._recheck` (`line 683`, checking all 3 ordinary stages `full`, `reconcile_full`, `report` via `_check_payload` -> `routing.check_condition` -> `_catalog` SSSOM rebuild × 3), builds `_normalization_rules` (`line 684`), derives `_core(spec, original_full, complete=False)` (`line 687`), rebuilds `api.build_phase` for `full`, `reconcile_full`, `report` (`lines 702, 730, 737`), checks final `full`/`core`/`report` bytes (`lines 810-812`), and runs `admission._completion_check` (`line 813`).
7. `shared_generation` equality check (`line 897`).
8. `_accounting(spec, selection)` (`line 899`) and `_reasoning(spec)` (`line 900`).
9. `_provenance_links(spec, selection)` (`line 901`) — checks instruction pin, schema profile/digest/SHA256, `full_path`/`core_path` and `full_md5`/`core_md5` claims (`lines 1027-1035`), bundle/manifest/output/validation/companion pins.
10. `_final_checks(spec, selection)` (`line 902`) — validates final `full` (`Dataset`) and `core` (`CoreDataset`) via `_validator_lines` (`JsonSchemaGenerator`), runs `_evidence_check`, `pair_schema_from_views` + `validate_pair_data`, `_captured_form`, `grounding._check_run`, and validates `GenerationRecord` provenance schema + `_report_check`.

Because most tamper mutations alter fields that are only checked in `_ordinary` (`line 896`) or `_provenance_links` (`line 901`) — and one mutation (`line 347`) is a **positive** check that runs all 10 stages — **13 of the 21 explicit `recheck_completed` calls execute through `_typed` and `_ordinary`**:

| Call # | Location in `tests/test_source_heading_runtime_api.py` | Case / Mutation | Stages Executed in `source_heading_completed.py` | Termination Line & Outcome | Depth Class |
| --- | --- | --- | --- | --- | --- |
| `#1` | `line 272` | `initial = complete.recheck_completed(raw)` (pre-relocation) | Stages 1–10 (`_decode` .. `_final_checks`) | `line 903` (returns `initial`) | Full (100%) |
| `#2` | `line 317` | `complete.recheck_completed(raw) == initial` (in sandbox) | Stages 1–10 (`_decode` .. `_final_checks`) | `line 903` (returns `initial`) | Full (100%) |
| `#3` | `line 318` | `CliRunner().invoke(cli, ['api', 'check-routing-completed', str(capture)])` | Stages 1–10 (`_decode` .. `_final_checks`) | `line 903` (exits `0`) | Full (100%) |
| `#4` | `line 324` | `changed_display`: `selection.path_display.core_source = 'unrelated-record.yaml'` | Stages 1–5 + start of Stage 6 (`_ordinary`) | `line 688` (`original core differs from actual deterministic derivation`) | Deep (~70%) |
| `#5` | `line 344` (`full`) | `with_schema_claims({'full_md5': '0'*32})` | Stages 1–8 + Stage 9 (`_provenance_links`) | `line 1035` (`completed provenance schema MD5 claim differs`) | Near-full (~88%) |
| `#6` | `line 346` (`full`) | `with_schema_claims({'full_path': 'unrelated/schema.yaml'})` | Stages 1–8 + Stage 9 (`_provenance_links`) | `line 1031` (`completed provenance schema path claim differs`) | Near-full (~88%) |
| `#7` | `line 344` (`core`) | `with_schema_claims({'core_md5': '0'*32})` | Stages 1–8 + Stage 9 (`_provenance_links`) | `line 1035` (`completed provenance schema MD5 claim differs`) | Near-full (~88%) |
| `#8` | `line 346` (`core`) | `with_schema_claims({'core_path': 'unrelated/schema.yaml'})` | Stages 1–8 + Stage 9 (`_provenance_links`) | `line 1031` (`completed provenance schema path claim differs`) | Near-full (~88%) |
| `#9` | `line 347` | `with_schema_claims(md5s) == initial` (valid MD5 claims) | Stages 1–10 (`_decode` .. `_final_checks`) | `line 903` (returns `initial`) | Full (100%) |
| `#10` | `line 361` (`targets[0]`) | Flip last byte of `spec.full_path` | Stages 1–6 (end of `_ordinary`) | `line 812` (`completed final full differs from actual phase lineage`) | Deep (~80%) |
| `#11` | `line 361` (`targets[1]`) | Flip last byte of `spec.core_path` | Stages 1–6 (end of `_ordinary`) | `line 812` (`completed final core differs from actual phase lineage`) | Deep (~80%) |
| `#12` | `line 361` (`targets[2]`) | Flip last byte of `spec.report_path` | Stages 1–6 (end of `_ordinary`) | `line 812` (`completed final report differs from actual phase lineage`) | Deep (~80%) |
| `#13` | `line 361` (`targets[3]`) | Flip last byte of `spec.bundle` | Stage 1 + Stage 2 (`_roster` -> `_authority`) | `line 164` (`captured authority bytes differ from registration`) | Early (~15%) |
| `#14` | `line 361` (`targets[4]`) | Flip last byte of `api._receipt_path(spec)` | Stages 1–4 (`_receipt`) | `line 388` (`captured effective receipt is not the checked complete result`) | Medium (~40%) |
| `#15` | `line 361` (`targets[5]`) | Flip last byte of `reg['inputs']['full_schema']['sources'][0]['path']` | Stage 1 + Stage 2 (`_roster` -> `_authority`) | `line 164` (`captured authority bytes differ from registration`) | Early (~15%) |
| `#16` | `line 361` (`targets[6]`) | Flip last byte of `reg['routing']['artifact']['path']` | Stage 1 + Stage 2 (`_roster` -> `_authority`) | `line 164` (`captured authority bytes differ from registration`) | Early (~15%) |
| `#17` | `line 378` (`usage_id`) | Ledger `rows[0]['id'] = 'tampered-call'` | Stages 1–3 (`_spec`) | `line 326` (`completed provenance generation/accounting differs`) | Early-Med (~30%) |
| `#18` | `line 378` (`usage_counter`) | Ledger `rows[0]['input_tokens'] += 1` | Stages 1–3 (`_spec`) | `line 326` (`completed provenance generation/accounting differs`) | Early-Med (~30%) |
| `#19` | `line 378` (`lost_admission`) | Ledger `rows[0].pop('routing_admission')` | Stages 1–5 + Stage 6 (`admission._recheck`) | `source_heading_admission.py:176` (`ordinary routing usage has no exactly associated request`) | Deep (~65%) |
| `#20` | `line 378` (`lost_typed_stage`) | Ledger `rows[2].pop('typed_audit_stage')` | Stages 1–4 + Stage 5 (`_typed`) | `line 404` (`typed audit usage stage mismatch`) | Medium (~50%) |
| `#21` | `line 387` (`missing`) | Delete intermediate `_full.yaml` from `files` and `blobs` | Stage 1 / Stage 2 (`_decode` / `_roster`) | `line 891` / `line 344` (missing snapshot file) | Early (~5%) |

Note: The Section 1.3 descriptions of Calls `#10` to `#21` above are superseded by the implementation handoff's table in `handoffs/agy4-routing-portable-a2-implementation.md`.

---

## 2. Whether the Mutations Are Independent Given One Completed Capture

**Yes — every check and mutation after `original.rename(preserved)` (`line 281`) is completely stateless and independent, operating on its own fresh `deepcopy(value)` in memory while all writes and original-path reads are hard-blocked.**

File and line evidence in `tests/test_source_heading_runtime_api.py:270-390`:
1. **Immutable base state (`lines 270-283`)**:
   - `result = api.execute(spec, client=c)` (`line 270`) writes the completed capture JSON to disk once.
   - `raw = Path(result['routing_completed_capture']['path']).read_bytes()` (`line 271`) is an immutable `bytes` object.
   - `initial = complete.recheck_completed(raw)` (`line 272`) is a pure dictionary result.
   - `value = json.loads(raw)` (`line 274`) is the parsed capture dictionary, and `reg = json.loads(...)` (`lines 275-278`) is the parsed registration dictionary. Neither `value` nor `reg` is ever mutated in place.
   - `original = tmp_path / 'output'` is renamed once to `preserved = tmp_path / 'preserved-output'` (`lines 279-281`), and `capture = tmp_path / 'relocated-capture.json'` is written once with `raw` (`line 282`).
2. **Read-only, no-network, forbidden-path monkeypatch guard (`lines 284-316`)**:
   - Inside `with monkeypatch.context() as m:` (`lines 306-388`), `checked_open` (`lines 290-294`) and `checked_os_open` (`lines 301-304`) raise `AssertionError('completed portable check wrote to disk')` on any write flag (`w`, `a`, `+`, `x`, `O_WRONLY`, `O_RDWR`, `O_CREAT`, `O_TRUNC`, `O_APPEND`) and raise `AssertionError('completed portable check touched original paths: ...')` if any path resolves into `forbidden` (`original` or `preserved`).
   - `socket.getaddrinfo`, `subprocess.Popen`, `socket.socket.connect`, `api.execute`, `c.messages.create`, and `c.messages.count_tokens` are all patched to `forbidden_call` (`lines 311-316`).
3. **Every mutation clones `value` via `deepcopy(value)` and passes ephemeral bytes to `complete.recheck_completed(...)`**:
   - **Call `#2` (`line 317`)**: `assert complete.recheck_completed(raw) == initial` reads immutable `raw`.
   - **Call `#3` (`line 318`)**: `CliRunner().invoke(cli, ['api', 'check-routing-completed', str(capture)])` reads `capture` (`relocated-capture.json`) read-only; `line 390` (`assert raw == capture.read_bytes()`) proves `capture` is untouched.
   - **Call `#4` (`lines 321-324`)**: `changed_display = deepcopy(value)` (`line 321`) mutates only `changed_display` and passes `sg.canonical(changed_display).encode('utf-8')`.
   - **Calls `#5–#9` (`lines 326-347`)**: `with_schema_claims(claims)` (`lines 326-337`) begins with `altered = deepcopy(value)` (`line 327`), re-serializes the provenance record inside `altered`, and returns `sg.canonical(altered).encode('utf-8')`. The dict `md5s` (`lines 339-342`) is computed strictly from unmodified `reg` and `value` (`hashlib.md5( bytes.fromhex(value['blobs'][root['sha256']]) ).hexdigest()`); it does not depend on the loop assertions at `lines 344, 346`.
   - **Calls `#10–#16` (`lines 348-361`)**: `targets` (`lines 348-350`) is a list of 7 path strings from unmodified `spec` and `reg`. Each iteration begins with `altered = deepcopy(value)` (`line 352`) and mutates only `altered['blobs'][sha]` and `altered['files'][entry]`.
   - **Calls `#17–#20` (`lines 364-378`)**: Each iteration over `('usage_id', 'usage_counter', 'lost_admission', 'lost_typed_stage')` begins with `altered = deepcopy(value)` (`line 365`) and mutates only `altered['blobs'][ledger_sha]` and `altered['files'][ledger_entry]`.
   - **Call `#21` (`lines 379-387`)**: Begins with `missing = deepcopy(value)` (`line 379`), reads `value['files']` and `value['blobs']` to find the intermediate `_full.yaml`, and mutates only `missing`.

Therefore, **no mutation reads or writes anything produced by any other mutation**. Given the single completed capture state `(raw, value, initial, spec, reg, capture, forbidden)` with `original` relocated to `preserved`, all 20 post-`initial` checks (`#2–#21`) are pure, order-independent read-only checks.

---

## 3. Options and Their Costs

### Baseline Numbers Used Across All Options

- **Baseline run `42947560899`**:
  - `routing-portable` job wall: **`1898s` (`31m38s`)** = `40s` non-test job overhead + `1858s` (`30m58s`) Step 5.
  - Fixed single-capture build prefix (`collection + draft_files + selected_spec + api.execute + initial recheck_completed` at `lines 258-273`): **`507s` (`8m27s`)** (derived in Section 1.2 from `routing-default-layout` Step 5 `582s` minus its `CliRunner` `recheck_completed` call `~75s`; of that `507s`, collection is `~69s` and `draft_files + selected_spec + api.execute + initial` is `~438s`).
  - Remaining 20 in-sandbox `recheck_completed` calls (`#2–#21`, `lines 317-388`): **`1351s` (`22m31s`)** (`1858s - 507s`).
- **Other PR critical-path jobs in `42947560899` after AGY1's ordinary-shard rebalance**:
  - `Build Docs`: **`1166s` (`19m26s`)** (`tmp/ci-observed-42947560899/post_ci_analysis_corrected.json:314`).
  - Rebalanced 8 ordinary shards (per `handoffs/agy1-ci-result.md` and `reviews/analysis_replacement_ci.md`): **`~1260s–1380s` (`~21m00s–23m00s`)** on the `42947560899` runner speed (and `~19m30s–25m38s` observed across `42958252720` / `42963052291`).

---

### Option A: Split `routing-portable` into $k$ Dedicated Lanes, Each Building Its Own Completed Capture

Each dedicated lane remains a standard single-process pytest job (`--ci-lane=<name>`) owning 1 test function in `tests/test_source_heading_runtime_api.py`. Because each lane runs in a separate GitHub Actions VM, each lane independently pays the `40s` job overhead + `507s` single-capture build prefix (`547s` = **`9m07s` fixed cost per lane**) and executes $1/k$ of the `1351s` post-`initial` `recheck_completed` checks:
$$\text{Step 5}(k) = 507\text{s} + \frac{1351\text{s}}{k}, \qquad \text{Job Wall}(k) = 547\text{s} + \frac{1351\text{s}}{k}$$

- **Option A2 ($k = 2$ balanced dedicated lanes: e.g. `routing-portable` and `routing-portable-tamper`)**:
  - **Partition of the 20 post-`initial` checks (`1351s` total, `~675.5s` per lane)**:
    - **Lane 1 (`routing-portable`, Calls `#1` + `#2–#9`, `~675s` of post-`initial` work)**:
      - Runs `selected_spec` + `api.execute` + Call `#1` (`initial = complete.recheck_completed(raw)`), relocates `output` -> `preserved-output`, and runs inside the monkeypatch sandbox: Call `#2` (`complete.recheck_completed(raw) == initial`), Call `#3` (`CliRunner` `check-routing-completed`), Call `#4` (`changed_display`), Calls `#5–#8` (the 4 `with_schema_claims` path/MD5 refusals for `full` and `core`), and Call `#9` (`with_schema_claims(md5s) == initial`), then restores `preserved.rename(original)` and checks `raw == capture.read_bytes()`.
      - Depth profile: `#1` (prefix) + 3 full (`#2, #3, #9`), 4 near-full (`#5–#8`), 1 deep (`#4`) = **`~675s`** post-`initial`.
    - **Lane 2 (`routing-portable-tamper`, Calls `#1` + `#10–#21`, `~676s` of post-`initial` work)**:
      - Runs `selected_spec` + `api.execute` + Call `#1` (`initial = complete.recheck_completed(raw)`), relocates `output` -> `preserved-output`, and runs inside the identical monkeypatch sandbox: Calls `#10–#16` (the 7 `targets` byte-tamper refusals), Calls `#17–#20` (the 4 ledger tamper refusals `usage_id`, `usage_counter`, `lost_admission`, `lost_typed_stage`), and Call `#21` (`missing` intermediate `_full.yaml`), then restores `preserved.rename(original)`.
      - Depth profile: `#1` (prefix) + 4 deep (`#10–#12, #19`), 2 medium (`#14, #20`), 2 early-medium (`#17, #18`), 4 early (`#13, #15, #16, #21`) = **`~676s`** post-`initial`.
  - **Expected lane time (`42947560899` baseline)**:
    - Step 5: `507s + 676s = 1183s` (**`19m43s`**).
    - Job Wall: `1183s + 40s = 1223s` (**`20m23s`**) — saves **`11m15s` (`675s`, `-35.6%`)**.
    - (On the `42958252720`/`42963052291` runner speed where unsplit `routing-portable` was `22m32s–23m30s`, each lane is **`~14m50s–15m30s`**.)
  - **Cost of building the capture once per lane**: `1 × 547s = 9m07s` of duplicated runner time in 1 additional GitHub Actions job (PR job count increases from 18 to 19).
  - **New PR critical-path floor**: `max(rebalanced ordinary shards ~21m–23m, routing-portable 20m23s, Build Docs 19m26s)` = **`~21m–23m` (ordinary shards)**. `routing-portable` is removed from the critical path.
- **Option A3 ($k = 3$ dedicated lanes)**:
  - **Expected lane time (`42947560899` baseline)**:
    - Step 5: `507s + 1351s / 3 = 957s` (**`15m57s`**).
    - Job Wall: `957s + 40s = 997s` (**`16m37s`**) — saves **`15m01s` (`901s`, `-47.5%`)**.
  - **Cost of building the capture once per lane**: `2 × 547s = 1094s` (`18m14s`) of duplicated runner time across 2 additional GitHub Actions jobs (PR job count increases from 18 to 20).
  - **New PR critical-path floor**: Still **`~21m–23m` (ordinary shards)** and bounded below by `Build Docs` (**`19m26s`**). Because Option A2 (`20m23s`) already drops `routing-portable` below the `~21m–23m` ordinary-shard floor and within `57s` of `Build Docs` (`19m26s`), the 3rd lane in Option A3 spends an extra `9m07s` of runner capacity for **zero additional reduction in PR wall time** below the ordinary-shard floor.
- **Files touched (Option A2 / A3)**:
  1. `tests/test_source_heading_runtime_api.py` (`lines 258-391`: extract shared setup/sandbox context helper and split test function into 2 functions).
  2. `utils/pytest_shard.py` (`lines 6, 20-25, 212`: add new lane key(s) to `API_CASE_LANES` and update docstring lane count).
  3. `.github/workflows/main.yaml` (`lines 46, 90`: add new lane name(s) to `api-completion` `matrix.case`).
  4. `tests/test_ci_sharding.py` (`line 59`: update `97` -> `98` for $k=2$, and `lines 262-286`: include the new lane in `test_dedicated_lane_exact_selection`).
  5. `utils/ci_sharding.md` (`lines 9-12, 49, 73, 168-174, 191-194`: update dedicated-lane prose counts).
- **What stays byte-for-byte the same check**:
  - Every `api.execute`, `complete.recheck_completed`, `CliRunner` invocation, `with_schema_claims`, byte-flip target, ledger mutation, missing-intermediate check, and `monkeypatch` guard runs the exact same production verifier code on the exact same canonical JSON bytes, and `_DedicatedCaseOutcome` (`utils/pytest_shard.py:50-77`) and `numprocesses` refusal (`lines 109-110`) remain **100% unchanged**.

---

### Option B: Parametrized Cases Inside the Single `routing-portable` Lane Run with `pytest-xdist` (Without Cross-Worker Capture Sharing)

Here `routing-portable` remains a single GitHub Actions job, `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` is parametrized into $N \ge 4$ items (e.g., 4 balanced groups or 20 individual checks) using a `module`-scoped fixture that builds the completed capture, and `.github/workflows/main.yaml:108-111` passes `-n logical --maxprocesses=4 --dist load --maxschedchunk=1` for `routing-portable`.

- **What would have to change in `utils/pytest_shard.py` and `.github/workflows/main.yaml`**:
  1. **`utils/pytest_shard.py:109-110` (`numprocesses` refusal)**: Currently raises `pytest.UsageError("dedicated --ci-lane requires a single process")` whenever `numprocesses not in (None, 0)`. It would have to permit `-n` either for all dedicated lanes or specifically for multi-node dedicated lanes (note `tests/test_ci_sharding.py:322` tests `--ci-lane=routing-dispatch -n 2`, which still exits `4` if only multi-node lanes allow `-n`).
  2. **`utils/pytest_shard.py:20-47` (`API_CASE_LANES` and `partition_lanes`)**: `API_CASE_LANES["routing-portable"]` would map to a tuple of expected parametrized node IDs (or node ID prefix) instead of a single string, and `partition_lanes` would validate that every expected parametrized node ID is present once.
  3. **`utils/pytest_shard.py:50-77` (`_DedicatedCaseOutcome`)**:
     - Under `pytest-xdist`, `pytest_collection_finish(session)` on the controller has `session.items == []` because collection occurs inside the `gw0..gw3` workers; the controller receives collected node IDs via `pytest_xdist_node_collection_finished(node, ids)`. `_DedicatedCaseOutcome` would have to implement `pytest_xdist_node_collection_finished` to verify that every worker collected the exact expected node IDs (`list(ids) == list(self.expected)`).
     - Because xdist workers interleave `pytest_runtest_logreport` events across items, `self.reports` on the controller is no longer a single fixed list `[(expected, "setup", "passed", False), (expected, "call", "passed", False), (expected, "teardown", "passed", False)]`; `_DedicatedCaseOutcome.pytest_sessionfinish` would have to group `self.reports` by `nodeid` and verify that each expected `nodeid` recorded `[("setup", "passed", False), ("call", "passed", False), ("teardown", "passed", False)]` with no extra reports.
- **What guarantee that weakens**:
  1. **Single-process collection/execution identity (`utils/pytest_shard.py:59-76, 109-110`; `utils/ci_sharding.md:180-184`)**: Today, a dedicated lane collects and executes in one Python process with no xdist controller/worker IPC layer. Allowing xdist means the controller relies on worker IPC (`pytest_xdist_node_collection_finished` and forwarded `TestReport`s) rather than direct in-process `session.items`.
  2. **4× redundant `api.execute` contention on the same 4-vCPU VM**: Because each xdist worker (`gw0..gw3`) is a separate OS process, a `module`-scoped fixture without cross-process sharing executes `draft_files` + `selected_spec` + `api.execute` **4 separate times concurrently on the same 4-vCPU runner**!
- **Expected lane time (`42947560899` baseline)**:
  - 4-worker xdist collection: `~69s` (measured in `shard8.log:354-378`).
  - 4 workers concurrently running `draft_files + selected_spec + api.execute + initial` (`~438s` single-core work × 4 processes on 4 vCPUs, with ~10–15% CPU/memory contention): **`~485s–505s`**.
  - 4 workers executing the `1351s` of post-`initial` `recheck_completed` checks across 4 vCPUs (`1351s / 3.84 ≈ 352s` + `~20s` tail): **`~372s`**.
  - Total Step 5: `69s + 495s + 372s = 936s` (**`15m36s`**).
  - Total Job Wall: `936s + 40s = 976s` (**`16m16s`**) — saves **`15m22s` (`922s`)**, but wastes `3 × 438s = 1314s` (`21m54s`) of CPU time on the VM rebuilding the identical completed capture 3 extra times.
- **Files touched**: `tests/test_source_heading_runtime_api.py`, `utils/pytest_shard.py`, `.github/workflows/main.yaml`, `tests/test_ci_sharding.py`, `utils/ci_sharding.md`.

---

### Option C: Building the Completed Capture Once and Sharing It Across Cases

Today, `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` **already** builds the completed capture only once (`api.execute` at `line 270`), and then spends `1351s` (`22m31s`) running 20 post-`initial` `recheck_completed` calls serially on **1 vCPU** while **3 of the 4 vCPUs on the `ubuntu-latest` runner sit idle**. Sharing a single completed capture across parallel workers can be done in two ways:

#### Variant C1: Single `routing-portable` Lane + `pytest-xdist` (`-n logical --maxprocesses=4`) + File-Locked Shared Capture in `tmp_path_factory.getbasetemp().parent`
- **How it works**:
  1. Parametrize `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` into 4 balanced groups (or 20 individual checks) inside `tests/test_source_heading_runtime_api.py`.
  2. In a `module`-scoped fixture, coordinate across the 4 xdist workers using standard-library `fcntl.flock` on `shared_root = tmp_path_factory.getbasetemp().parent / "routing_portable_shared"`:
     - The first worker acquiring the lock runs `draft.prepare`, `selected_spec`, `api.execute(spec, client=c)`, `raw = capture_path.read_bytes()`, `initial = complete.recheck_completed(raw)`, renames `original` (`output`) to `preserved` (`preserved-output`), writes `relocated-capture.json`, and writes a small JSON manifest (`initial`, `reg`, `spec` path metadata, `forbidden` paths) into `shared_root`.
     - The other 3 workers block on `fcntl.flock` (consuming 0% CPU while Worker 0 runs `api.execute`), then read `(raw, value, initial, reg, spec_paths, forbidden, capture)` from `shared_root` in `<0.1s`.
  3. All 4 workers then execute the parametrized `recheck_completed` checks in parallel inside the exact same read-only `monkeypatch.context()` sandbox (with `preserved.rename(original)` removed or performed only when creating the capture, since no check inside the sandbox accesses `original` or `preserved`).
- **Expected lane time (`42947560899` baseline)**:
  - 4-worker xdist collection: `~69s` (measured in `shard8.log:354-378`).
  - Single-worker `draft_files + selected_spec + api.execute + initial` while 3 workers sleep on `fcntl.flock`: **`~438s`** (`507s - 69s`).
  - Parallel execution of the `1351s` of post-`initial` `recheck_completed` checks across 4 vCPUs (`1351s / 3.84 = 352s` + `~15s` scheduling tail): **`~367s`**.
  - Total Step 5: `69s + 438s + 367s = 874s` (**`14m34s`**).
  - Total Job Wall: `874s + 40s = 914s` (**`15m14s`**) — saves **`16m24s` (`984s`, `-51.8%`)**, uses **0 extra GitHub Actions jobs**, and builds `api.execute` **only once**.
- **Files touched**: `tests/test_source_heading_runtime_api.py`, `utils/pytest_shard.py`, `.github/workflows/main.yaml`, `tests/test_ci_sharding.py`, `utils/ci_sharding.md`.
- **What guarantee it weakens**: Same plugin change as Option B (multi-node `_DedicatedCaseOutcome` and xdist `pytest_xdist_node_collection_finished` on the controller), plus the final `preserved.rename(original)` restoration at `line 389` cannot run mid-suite while sibling workers are still asserting `forbidden` paths.

#### Variant C2: Producer Job + Consumer Matrix Jobs in `.github/workflows/main.yaml`
- **How it works**: One GitHub Actions job builds the capture (`~547s`) and uploads it via `actions/upload-artifact`; $k$ downstream jobs download it and run subsets of `recheck_completed`.
- **Why it is strictly worse than C1 and A2**: Because the consumer jobs cannot start until the producer job finishes (`547s`), and each consumer job then pays another `40s` job setup + `69s` pytest collection + `1351s / k` execution, a 2-consumer pipeline takes `547s + 40s + 69s + 676s = 1332s` (**`22m12s`**) — **slower** than Option A2 (`20m23s`) and Option C1 (`15m14s`), while requiring workflow graph restructuring and changing the test to read a pre-built capture artifact instead of calling `api.execute` in-test.

---

### Summary Comparison Table (`42947560899` Baseline)

| Option | Extra CI Jobs | `api.execute` Runs | Touches `_DedicatedCaseOutcome` / `-n` Rule? | Expected `routing-portable` Step 5 | Expected `routing-portable` Job Wall | Wall Time Saved vs. `31m38s` | New PR Critical-Path Floor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Current (`main`)** | `0` | `1` | No | `1858s` (`30m58s`) | `1898s` (`31m38s`) | `0s` | `31m38s` (`routing-portable`) |
| **Option A2 (`k = 2` dedicated lanes)** | `+1` | `2` (`1` per lane) | **No** | `1183s` (`19m43s`) | **`1223s` (`20m23s`)** | **`-11m15s` (`-35.6%`)** | **`~21m–23m`** (rebalanced ordinary shards; `Build Docs` is `19m26s`) |
| **Option A3 (`k = 3` dedicated lanes)** | `+2` | `3` (`1` per lane) | **No** | `957s` (`15m57s`) | `997s` (`16m37s`) | `-15m01s` (`-47.5%`) | **`~21m–23m`** (ordinary shards; `Build Docs` is `19m26s`) |
| **Option B (`1` lane, xdist `4` workers, per-worker capture)** | `0` | `4` (`1` per worker) | Yes | `936s` (`15m36s`) | `976s` (`16m16s`) | `-15m22s` (`-48.6%`) | **`~21m–23m`** (ordinary shards; `Build Docs` is `19m26s`) |
| **Option C1 (`1` lane, xdist `4` workers, `fcntl.flock` shared capture)** | `0` | `1` (shared) | Yes | `874s` (`14m34s`) | **`914s` (`15m14s`)** | **`-16m24s` (`-51.8%`)** | **`~21m–23m`** (ordinary shards; `Build Docs` is `19m26s`) |

---

## 4. What Must Not Be Done

1. **Do not cache or short-circuit catalog, schema, or phase reconstructions in production verifiers**:
   - The repeated reconstructions in `src/data_sheets_schema/source_heading_routing.py` (`_catalog`, `_capture_schema`), `src/data_sheets_schema/source_heading_runtime.py` (`prepare_condition`, `check_condition`, `_derive`), `src/data_sheets_schema/source_heading_admission.py` (`_recheck`, `_check_payload`), and `src/data_sheets_schema/source_heading_completed.py` (`recheck_completed`, `_roster`, `_spec`, `_authority`, `_receipt`, `_typed`, `_ordinary`, `_provenance_links`, `_final_checks`) are intentional independent-verification invariants. Every `recheck_completed` call must continue to reconstruct authority, schema views, SSSOM catalog, typed-audit assembly, and ordinary phase lineage from scratch from the passed-in capture bytes alone.
2. **Do not touch protected files**:
   - `api_runner.py`, `shared_generation.py`, `canonical_hashes.yaml`, the boundary contracts, and the scanner must not be modified.
3. **Do not drop, merge, or weaken any of the 21 explicit `recheck_completed` checks or the `monkeypatch` portability sandbox**:
   - Every positive check (`initial` pre-relocation at `line 272`, in-sandbox `recheck_completed(raw) == initial` at `line 317`, `CliRunner` `check-routing-completed` at `line 318`, and `with_schema_claims(md5s) == initial` at `line 347`) and every negative `UsageLedgerError` refusal (`changed_display` at `line 324`, the 4 bad `full`/`core` path/MD5 schema claims at `lines 344, 346`, the 7 tampered `targets` at `line 361`, the 4 tampered ledger kinds at `line 378`, and `missing` intermediate `_full.yaml` at `line 387`) must run under the exact same read-only, no-network, forbidden-original-path `monkeypatch.context()` guard.

---

## 5. Recommendation

**Recommend Option A2: Split `routing-portable` into 2 balanced dedicated lanes (`routing-portable` and `routing-portable-tamper`), each running in a single process with its own completed capture.**

### Why Option A2 Wins
1. **Eliminates `routing-portable` as the PR critical-path bottleneck**:
   - Reduces `routing-portable` wall time on the `42947560899` baseline from **`31m38s` (`1898s`)** to **`20m23s` (`1223s`)** per lane (and **`~15m00s`** on the `42958252720`/`42963052291` runners), placing it **below** the rebalanced ordinary-shard floor (`~21m–23m`) and within `57s` of `Build Docs` (`19m26s`). No further shortening of `routing-portable` (such as A3 at `16m37s` or C1 at `15m14s`) can lower overall PR wall time below the `~21m–23m` ordinary-shard and `19m26s` `Build Docs` floor.
2. **Preserves 100% of `_DedicatedCaseOutcome` and single-process guarantees**:
   - Neither `_DedicatedCaseOutcome` (`utils/pytest_shard.py:50-77`) nor the `dedicated --ci-lane requires a single process` rule (`utils/pytest_shard.py:109-110`, `tests/test_ci_sharding.py:322`) is weakened. Every dedicated lane continues to collect and execute **1 test node ID** in **1 process** with exact `("setup", "call", "teardown")` report verification and full `original.rename(preserved)` / `preserved.rename(original)` lifecycle isolation.
3. **Minimal, localized diff (`5` non-protected files)**:
   - In `tests/test_source_heading_runtime_api.py` (`lines 258-391`), extract the shared setup/sandbox context manager (`selected_spec` -> `api.execute` -> `initial` -> `original.rename(preserved)` -> `monkeypatch.context()` -> `preserved.rename(original)`) and split the assertions into:
     - `test_actual_completed_capture_is_portable_and_refuses_changed_claims` (`routing-portable`: Calls `#1` + `#2–#9`), and
     - `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` (`routing-portable-tamper`: Calls `#1` + `#10–#21`).
   - Add `"routing-portable-tamper"` to `API_CASE_LANES` in `utils/pytest_shard.py:20-25`, `matrix.case` in `.github/workflows/main.yaml:90`, `tests/test_ci_sharding.py:59, 262-286`, and `utils/ci_sharding.md`.
