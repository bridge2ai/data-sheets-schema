# AGY4 Handoff: Exact Command Packet for the One D132 `cpu-monitoring` Diagnostic Run (`382f0dfd1ce8`)

- **Worker**: `agy4` (`E4`)
- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-diagnostic-run-packet.md`
- **Track**: Native (read-only command packet; no diagnostic, arming, cleanup, or project import was executed by `agy4`).
- **Statement provenance markers**:
  - `[record]` — read directly from a retained JSON/XML/log/markdown artifact on disk (with file path and JSON field cited).
  - `[source]` — read directly from a repository script or module on disk (with file path, SHA-256, and line numbers cited).
  - `[inference]` — logical deduction combining `[record]` and `[source]` facts where no single JSON field stores the combined fact directly.

---

## 0. Provenance Script, Command Run, and Gitignore-Independent Searches

- `[source]` **Extraction and verification script**:
  - Path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/extract_wp1_diagnostic_packet_20261111.py`
  - Command executed (read-only standard-library extraction):
    ```sh
    /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/extract_wp1_diagnostic_packet_20261111.py
    ```
  - Machine-readable output written by the script:
    - Path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/diagnostic-packet-20261111/packet-facts.json`
    - Size: `63039` bytes
    - SHA-256: `5136a6aeaac5b99dd0c9423ec11334256af1f283a9ab9e555f26016ba3459d81`
- `[source]` **Gitignore-independent search methodology**:
  - Every statement below that a path or claim file does or does not exist was verified using two gitignore-independent mechanisms that inspect the POSIX filesystem directly without consulting `.gitignore`, `.ignore`, or global ignore rules:
    1. Python `os.path.lexists(...)` inside `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/extract_wp1_diagnostic_packet_20261111.py` (which tests `lstat(2)` directly, including broken symlinks and gitignored paths).
    2. Direct POSIX `find` invocations over `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans`:
       ```sh
       find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8 -maxdepth 2
       find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m -maxdepth 1 -name '*382f0dfd1ce8*'
       find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m -maxdepth 2 -name '*post-capture-ast-r2-20261111*' -o -name '*cleanup-wrapper-382f0dfd1ce8-r2*' -o -name '*config-restored-r2*' -o -name '*cpu-diagnostic-config*'
       find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans -maxdepth 2 -name '*lock*'
       ```

---

## 1. The Launch Command

### 1.1 Whether a JSON record holds the outermost `argv`, and what the records hold

- `[record]` **No JSON record in the interrupted diagnostic's artifacts stores the outermost supervisor `argv` (`native_wp1_validation_20261110.py` without `--supervised`) or the second-layer `--supervised` child `argv`.**
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111.supervisor.json` (SHA-256 `bca0c15bdd444723fcb087b11063b769ac58ff93b97d313969f74d3719880897`) records `"kind": "cpu-monitoring"`, `"limit_seconds": 900`, `"manifest": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-contract-382f0dfd1ce8.json"`, `"manifest_sha256": "df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e"`, `"returncode": 125`, and `"seconds": 894.5330245840014`, and has **no** `"command"` or `"argv"` field.
  - `[record]` Prose review note `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-capture-cleanup-20261111/notes/reviews/native_capture_acceptance_20261111.md` (`line 56`) records the CLI subcommand and `--label`:
    `The separately released invocation was cpu-monitoring --label post-capture-ast-20261111, using the same source/contract and already certified canary.`
- `[record]` **Outermost recorded `argv` in JSON (Process Layer 3 — inner WP1 driver `run_native_wp1_20261110.py`)**:
  - Record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111.outer.json` (SHA-256 `a879abcb672133fc4d10fd528e642646c506b54b76ba4c60bc76ca2a9be2b846`), field `"command"`:
    ```json
    [
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
      "-S",
      "-P",
      "-B",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/run_native_wp1_20261110.py",
      "--out",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111",
      "--workers",
      "1",
      "tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic"
    ]
    ```
- `[record]` **Innermost recorded process `argv` in JSON (Process Layer 4 — sandboxed worker `run_native_wp1_20261110.py --worker`)**:
  - Record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/plan.json` (SHA-256 `29d61001c798ed0ca7d613474006c4d5d2880168c087a4a4e26386997101f445`), field `"command"`:
    ```json
    [
      "/usr/bin/sandbox-exec",
      "-f",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/network-denied.sb",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/venv/bin/python",
      "-P",
      "-B",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/run_native_wp1_20261110.py",
      "--worker",
      "--out",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111",
      "--workers",
      "1",
      "tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic"
    ]
    ```
  - `[source]` In `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/run_native_wp1_20261110.py` (`lines 216-220`), `plan["command"]` is wrapped at `Popen` time with the child-admission gate (`native_wp1_child_gate_20261110.py`):
    `[plan['command'][0], plan['command'][1], plan['command'][2], plan['command'][3], '-S', '-P', '-B', str(WP1_CHILD_GATE), *plan['command'][3:]]`.
- `[record]` **Innermost recorded in-process `pytest.main(...)` argument list**:
  - Record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/pytest-command.json` (SHA-256 `4c353cf59db1f0de6bc2b520ebef15c64b65adff5383eb8e6a32a6de64fc014a`), field `"args"`:
    ```json
    [
      "-q",
      "-o",
      "addopts=",
      "-p",
      "no:cacheprovider",
      "--basetemp",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/cases",
      "--junitxml",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/pytest.xml",
      "-p",
      "xdist.plugin",
      "-n",
      "1",
      "tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic"
    ]
    ```

### 1.2 Exact reconstructed outermost `argv`, working directory, and environment

- `[source]` + `[inference]` Combining `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_validation_20261110.py` (`lines 217-225, 243-251, 990-1015, 1051-1056`), `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-wp1-preparation-20261111/notes/reviews/native_wp1_cpu_config_20261111.md` (`line 37`), and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-capture-cleanup-20261111/notes/reviews/native_capture_acceptance_20261111.md` (`line 56`), the **outermost process `argv` (Process Layer 1)** for the interrupted diagnostic was:
  ```json
  [
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
    "-S",
    "-P",
    "-B",
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_validation_20261110.py",
    "cpu-monitoring",
    "--label",
    "post-capture-ast-20261111",
    "--canary-out",
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-canary-capture-ast-20261111"
  ]
  ```
  - `[source]` Note on `--canary-out`: In `native_wp1_validation_20261110.py` (`lines 224-225` and `991`), `--canary-out` defaults to `SCRATCH_ROOT / f'wp1-{short_commit}-canary'` (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-canary`), which does **not** exist (`os.path.lexists == False`); because the certified canary for `382f0dfd1ce8` was run with `--label capture-ast-20261111` at `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-canary-capture-ast-20261111`, `--canary-out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-canary-capture-ast-20261111` (or a newly certified canary directory) is mandatory (`verify_canary_prerequisite`, `lines 616-674`, called at `lines 691` and `1013`).
  - `[source]` Process Layer 1 immediately spawns **Process Layer 2 (`--supervised`)** at `native_wp1_validation_20261110.py:1051-1056` with `argv`:
    ```json
    [
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
      "-S",
      "-P",
      "-B",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_validation_20261110.py",
      "--supervised",
      "cpu-monitoring",
      "--label",
      "post-capture-ast-20261111",
      "--canary-out",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-canary-capture-ast-20261111"
    ]
    ```
- `[source]` + `[record]` **Working directory**:
  - Outermost supervisor (`Layer 1`) and `--supervised` (`Layer 2`) run with `cwd=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3` (`ROOT = Path(__file__).resolve().parents[2]`, enforced at `native_wp1_validation_20261110.py:23, 725, 1055` and documented at `native_wp1_cpu_config_20261111.md:37`).
  - Inner worker (`Layer 4`) runs with `cwd=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8` (`plan.json` field `"source_root"`, set by `run_native_u3m_20261109.py:165` from `composition.json` field `"test_worktree"`).
- `[source]` + `[record]` **Environment requirements**:
  - **Outermost process (`Layer 1`)**:
    - `U3WP1_MANIFEST=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-contract-382f0dfd1ce8.json` (`native_wp1_validation_20261110.py:160, 994`; if omitted, it defaults to `wp1-contract-01bdcb22dad6.json` at `line 26`, which fails the `HEAD` commit check).
    - `U3WP1_LEASE_FD` must **not** be set in `os.environ` (`native_wp1_validation_20261110.py:1009`: `require('U3WP1_LEASE_FD' not in os.environ, 'quiet lease FD must not be inherited by non-lease WP1 kinds')`).
    - Invoked under a sanitized environment (`native_wp1_cpu_config_20261111.md:37` and `run_native_cpu_monitoring_once_20261111.sh:70-71`):
      `/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=en_US.UTF-8 U3WP1_MANIFEST=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-contract-382f0dfd1ce8.json`.
  - **Supervised child (`Layer 2`)** (`native_wp1_validation_20261110.py:1043-1050`):
    - Receives only `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `LANG=en_US.UTF-8`, `U3WP1_MANIFEST`, `U3WP1_OUTER_START_NS`, `U3WP1_OUTER_LIMIT_SECONDS=900`, `U3WP1_SUPERVISOR_PIPE_FD`, and `U3WP1_LOCK_FD`.
  - **Inner driver (`Layer 3`)** (`native_wp1_validation_20261110.py:706-718`):
    - Receives `U3M_MANIFEST=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/composition.json`, `U3M_MANIFEST_SHA=fe782d98b04ce7d35e244cd396c7a341b690a4943962db65d96a627bfdcf3a89`, `U3WP1_MANIFEST=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-contract-382f0dfd1ce8.json`, `U3WP1_MANIFEST_SHA=df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e`, `U3WP1_KIND=cpu-monitoring`, `U3WP1_CONSUMER_ARM=monitoring`, `U3WP1_MEASUREMENT_CLASS=unqualified_contended_cpu_diagnostic`, `U3K_PROFILE=control`, `U3K_OBSERVE=1`, `U3M_OBSERVE=1`, `U3M_DEPENDENCY_CANARY=0`, `U3WP1_STARTED_MONOTONIC`, `U3WP1_HARD_DEADLINE`, `U3WP1_DRIVER_PIPE_FD`, and `U3WP1_CHILD_GATE_FD`.
  - **Sandboxed worker (`Layer 4`)** (`plan.json` field `"environment"`):
    - Recorded in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/plan.json` (`lines 15-43` of `plan.json`, extracted at `packet-facts.json:493-520`).

---

## 2. The Configuration Arming

### 2.1 Exact byte difference between armed (`8a96cf34...`) and restored (`95a1f7d1...`)

- `[record]` Record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/composition.json` (SHA-256 `fe782d98b04ce7d35e244cd396c7a341b690a4943962db65d96a627bfdcf3a89`), field `"private_config"`:
  ```json
  {
    "backup": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config.bak-u3m-20261109",
    "configured_sha256": "8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76",
    "key": "d4d.cirepositoryurl",
    "original_mode": 420,
    "original_sha256": "95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1",
    "path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config",
    "value": "https://github.com/bridge2ai/data-sheets-schema.git"
  }
  ```
- `[record]` **Restored bytes (`95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1`, `173` bytes, mode `0o644` / `420`)** in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config.bak-u3m-20261109`:
  ```ini
  [core]
  	repositoryformatversion = 0
  	filemode = true
  	bare = false
  	logallrefupdates = true
  	ignorecase = true
  	precomposeunicode = true
  [extensions]
  	worktreeConfig = true
  ```
- `[record]` + `[source]` **Armed bytes (`8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76`, `250` bytes, mode `0o644` / `420`)**:
  - Consist of the exact `173` restored bytes followed by the `77`-byte section (`packet-facts.json:971-972, 997-999`):
    ```ini
    [d4d]
    	ciRepositoryUrl = https://github.com/bridge2ai/data-sheets-schema.git
    ```

### 2.2 Which tool writes the armed bytes and with what command

- `[record]` + `[source]` **Initial composition arming**:
  - Written during sparse composition preparation by `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-wp1-preparation-20261111/scripts/adhoc/prepare_native_wp1_canary_20261111.py` (SHA-256 `37963c7d81070dc6dee2b9727fa6fb0db91f9d620515d29e78ab46636b9699aa`, recorded in `composition.json` field `"helper_sha256"`, `line 245`) using:
    `git('config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git', cwd=tree)`
    (and likewise in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/compose_native_u3m_20261109.py`, SHA-256 `a61c01d768a9c88a7bcd10921b6fe84c6111649f42378553a06efba8bb34bb76`, `line 289`).
- `[source]` + `[record]` **Standalone re-arming helpers**:
  1. Earlier `3cc113e2606c` helper `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-wp1-preparation-20261111/scripts/adhoc/native_wp1_private_config_20261111.py` (SHA-256 `8211214df16ed121db35a0abef5e373a435a2444a2a0cb112de15bc36fb04ca7`, `lines 24-27, 107-128`) is hardcoded to `HEAD = '3cc113e2606c563236d9c06098c5329ddd027a38'` and cannot arm `382f0dfd1ce8`.
  2. `382f0dfd1ce8`-pinned helper `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_private_config_rearm_restore_20261111.py` (SHA-256 `7cbd253801c6d0324b2cf9bf5622e3806761e8f85134c33dd28a6462829dbfed`, `lines 122-144`, recorded in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-config-rearm-382f0dfd1ce8-20261111/armed-20261111T163801Z.json` field `"helper_sha256"`) arms `composition-382f0dfd1ce8/tree/.git/config` with outer command:
     ```json
     [
       "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
       "-I",
       "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_private_config_rearm_restore_20261111.py",
       "arm"
     ]
     ```
     which runs (`lines 129-131`):
     ```json
     [
       "/usr/bin/git",
       "--no-replace-objects",
       "-c",
       "core.hooksPath=/dev/null",
       "config",
       "--local",
       "d4d.ciRepositoryUrl",
       "https://github.com/bridge2ai/data-sheets-schema.git"
     ]
     ```
     in `cwd=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree`, verifies that the resulting SHA-256 equals `8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76`, and writes `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-config-rearm-382f0dfd1ce8-20261111/armed-<UTC>.json`.

### 2.3 What the run needs the armed config for, and whether it can start with the restored config as it is now

- `[source]` **What the run needs it for**:
  - During the `fixture` phase of `tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic` (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/tests/test_native_u3k_profile.py:224-226`), `make_case(tmp_path, 'neutral')` calls `v2_reg.register_execution(...)`, which calls `_ci_repository_url(root, env)` in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/src/data_sheets_schema/native_execution_registration_v2.py` (`lines 142-160`).
  - `_ci_repository_url` runs `git config --local --get d4d.ciRepositoryUrl` against `worktree-382f0dfd1ce8` (whose shared `.git/config` is `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config` because `extensions.worktreeConfig = true`), falling back to `git config --local --get remote.origin.url`.
  - Because the private composition repository was initialized with `git init --quiet` and no `origin` remote (`prepare_native_wp1_canary_20261111.py:230`), `d4d.ciRepositoryUrl` in `tree/.git/config` is the **only** source of the repository URL.
- `[source]` + `[record]` **Whether the run can start with the restored configuration (`95a1f7d1...`) as it is now**:
  - **No.** `[record]` On disk right now (`packet-facts.json:992-996`), `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config` is in its restored state (`173` bytes, SHA-256 `95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1`).
  - `[source]` Outer preflight (`verify_contract_and_source` in `native_wp1_validation_20261110.py:553-595` and `verify_u3m_manifest` in `run_native_u3m_20261109.py:66-102`) does **not** check the SHA-256 of `tree/.git/config`, so the outer process would spawn the worker, and the run would then **fail inside the `fixture` phase (`make_case`)** at `native_execution_registration_v2.py:160` with `ValueError: v2 CI requires local d4d.ciRepositoryUrl or origin`.

---

## 3. The Restoration

### 3.1 Exact command of the reviewed cleanup wrapper (`4a5a483d...`) and what it writes

- `[record]` + `[source]` **Reviewed cleanup wrapper script**:
  - Path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-capture-cleanup-20261111/scripts/adhoc/cleanup_native_capture_config_20261111.py`
  - SHA-256 on disk (`packet-facts.json:406`): `4a5a483d8260a28713f6eea1ae49708a3c258a3944dbc0a4cf1579a3829a5446` (matches `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/cleanup-wrapper-382f0dfd1ce8-20261111/started.json` and `result.json`, field `"helper_sha256"`).
- `[source]` **Exact command (`argv`) of the reviewed cleanup wrapper** (`cleanup_native_capture_config_20261111.py:93`: `require(sys.argv[1:] == [], 'cleanup wrapper takes no CLI arguments')`):
  ```json
  [
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
    "-S",
    "-P",
    "-B",
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-capture-cleanup-20261111/scripts/adhoc/cleanup_native_capture_config_20261111.py"
  ]
  ```
  - `[source]` Internally (`lines 125-133`), `cleanup_native_capture_config_20261111.py` sets `sys.argv = [str(COMPOSER), 'cleanup', '--commit', COMMIT]` and executes `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/compose_native_u3m_20261109.py` (SHA-256 `a61c01d768a9c88a7bcd10921b6fe84c6111649f42378553a06efba8bb34bb76`) via `runpy.run_path(..., run_name='__main__')`, equivalent to:
    ```json
    [
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
      "-S",
      "-P",
      "-B",
      "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/compose_native_u3m_20261109.py",
      "cleanup",
      "--commit",
      "382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b"
    ]
    ```
- `[record]` + `[source]` **What `cleanup_native_capture_config_20261111.py` writes**:
  1. Creates `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/cleanup-wrapper-382f0dfd1ce8-20261111` (`mode=0o700`, `exist_ok=False`, `line 115`).
  2. Writes `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/cleanup-wrapper-382f0dfd1ce8-20261111/started.json` (`open('xb')`, `lines 63-67, 116-123`; SHA-256 `e810221671b235bf12c09dc7d810c19d754800fc8c8aa4a2b346f0c94df571df`).
  3. Via `compose_native_u3m_20261109.py:322-339`, writes temporary `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config.restore-u3m-20261109` (`open('xb')`), `chmod`s it to `0o644`, atomically replaces `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config` via `os.replace`, and writes `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/config-restored.json` (`open('xb')`, `lines 337-339`; SHA-256 `6fe0aadd244ddafef9d1dd900739cf3106f8482fdcfaedacff1186845ed649a5`).
  4. Writes `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/cleanup-wrapper-382f0dfd1ce8-20261111/result.json` (`open('xb')`, `lines 136-145`; SHA-256 `da12979d24312ec59e919de2fc4cfadcf722d97131637e77c976b7b76385850b`).

### 3.2 Write-once status of `cleanup-wrapper-382f0dfd1ce8-20261111` and `config-restored.json`, and new output names for a second restoration

- `[source]` + `[record]` **Both are strictly write-once and already exist on disk**:
  - `cleanup_native_capture_config_20261111.py` (`lines 33, 96-97, 115`) enforces:
    - `require(not os.path.lexists(EVIDENCE_DIR), f'wrapper evidence path already exists: {EVIDENCE_DIR}')` where `EVIDENCE_DIR = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/cleanup-wrapper-382f0dfd1ce8-20261111')` (`exists: true`).
    - `require(not os.path.lexists(RESTORED_REPORT), f'restoration report already exists: {RESTORED_REPORT}')` where `RESTORED_REPORT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/config-restored.json')` (`exists: true`).
  - `compose_native_u3m_20261109.py` (`lines 337-339`) also opens `composition_dir / 'config-restored.json'` with `open('xb')`, raising `FileExistsError` if `config-restored.json` exists.
  - Therefore, neither `cleanup_native_capture_config_20261111.py` nor `compose_native_u3m_20261109.py cleanup` can run a second time against `composition-382f0dfd1ce8`.
- `[record]` + `[source]` **New output names for post-rerun restoration**:
  - `[record]` In `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_private_config_rearm_restore_20261111.py` (SHA-256 `7cbd253801c6d0324b2cf9bf5622e3806761e8f85134c33dd28a6462829dbfed`, `lines 47-48, 88-98, 147-167`), the lead's helper uses:
    - Evidence directory: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-config-rearm-382f0dfd1ce8-20261111`
    - Write-once UTC-stamped filenames (`open('xb')`): `armed-<YYYYMMDDTHHMMSSZ>.json` and `restored-<YYYYMMDDTHHMMSSZ>.json` (specifically `armed-20261111T163801Z.json` and `restored-20261111T164546Z.json` for the D132 run), with temporary file `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config.restore-lead-20261111`.
  - `[record]` Additionally, the following round-2 write-once names were verified non-existent (`os.path.lexists == False` in `packet-facts.json:940-945` and `find` output empty):
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/cleanup-wrapper-382f0dfd1ce8-r2-20261111`
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/config-restored-r2-20261111.json`
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/cpu-diagnostic-config-r2`

---

## 4. Once-Only Claims and Names (`cpu-monitoring` Kind Specifically)

### 4.1 What makes a `cpu-monitoring` run refuse to start in the validator/runner tools

- `[source]` In `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_validation_20261110.py` (`SHA-256: a995dba963a2a83d183dbb3fd523462d1fdd51b5a7132be7841c4b90557c0c6e`) and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/run_native_wp1_20261110.py` (`SHA-256: f5d99aa127d62651c85a12ad7626835be5c39c255966a3529deac7b61a676524`), a `cpu-monitoring` invocation refuses to start if any of the following exist:
  1. **Any of the 5 output paths derived from `--label <label>`** (`output_for_kind` at `native_wp1_validation_20261110.py:217-222` constructs `out = SCRATCH_ROOT / f'wp1-{short_commit}-cpu-monitoring-{label}'`; checked with `os.path.lexists(path)` at `lines 678-680` and `998-1002`, and `out.mkdir(mode=0o700, parents=False, exist_ok=False)` at `run_native_wp1_20261110.py:229`):
     - `<out>`
     - `<out>.supervisor.json` (`supervisor_record_path(out)`)
     - `<out>.outer.json` (`outer_record_path(out)`)
     - `<out>.outer.log` (`outer_log_path(out)`)
     - `<out>.qualification` (`qualification_dir_path(out)`)
  2. **The quiet-window lock path** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/native_quiet_window.lock` (`LOCK_PATH` at `native_wp1_quiet_20261110.py:21`; checked via `require(not os.path.lexists(LOCK_PATH), f'quiet-window lock path exists: {LOCK_PATH}')` at `native_wp1_validation_20261110.py:686, 1008`, `run_native_wp1_20261110.py:130`, and `run_native_u3m_20261109.py:105`).
  3. **An inherited `U3WP1_LEASE_FD` environment variable** (`native_wp1_validation_20261110.py:687, 1009` and `run_native_wp1_20261110.py:130`).
- `[source]` + `[record]` **How `.once.json` claim files apply**:
  - In `native_wp1_validation_20261110.py` (`lines 228-240, 692, 1014`), `verify_capture_recheck_not_claimed` and `claim_capture_recheck_once` check `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/capture-recheck-382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b-df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e.once.json` **only when `args.kind == 'capture-recheck'`** (`if args.kind == 'capture-recheck': verify_capture_recheck_not_claimed(...)`). That file (`exists: true`, SHA-256 `cd32553e34c1a8bdfb051654ec1d15fd9dc96e0f1ca558b4a27cfe7aee4bcade`) does **not** cause `native_wp1_validation_20261110.py cpu-monitoring` to refuse.
  - However, `[record]` + `[source]` the lead's D132 wrapper `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/run_native_cpu_monitoring_once_20261111.sh` (`SHA-256: dcf469a57cfa745b728076e42cc731d901c65db067e8b201adc7238a1d79ce3f`, `lines 51, 103, 152-153`) writes its own once-claim file:
    `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json`
    and refuses at `line 103` (`[ ! -e "$CLAIM" ] || fail "the diagnostic was already started once ($CLAIM); it is not retried"`).

### 4.2 Existing vs. unused output names for `cpu-monitoring` on `382f0dfd1ce8`

- `[record]` **Already-used `cpu-monitoring` labels and output directories on `382f0dfd1ce8`**:
  1. Interrupted run (`--label post-capture-ast-20261111`):
     `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111` (plus `.outer.json`, `.outer.log`, `.supervisor.json` — all exist).
  2. Lead D132 rerun (`--label lead-rerun-20261111`, executed `2026-11-11T16:38:13Z`–`16:45:46Z`):
     `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111` (plus `.outer.json`, `.outer.log`, `.supervisor.json` — all exist).
- `[record]` **Proposed unused output name (verified non-existent by `os.path.lexists` in `packet-facts.json:960-966` and `find`)**:
  - Proposed `--label`: `post-capture-ast-r2-20261111`
  - Resulting 5 paths (`all False` under `os.path.lexists` and `0` matches under `find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m -maxdepth 2 -name '*post-capture-ast-r2-20261111*'`):
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-r2-20261111`: `false`
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-r2-20261111.outer.json`: `false`
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-r2-20261111.outer.log`: `false`
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-r2-20261111.qualification`: `false`
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-r2-20261111.supervisor.json`: `false`

---

## 5. The Load Gate

- `[source]` **For `cpu-monitoring`, the tool itself does NOT enforce any host-load refusal gate; the `< 2.5` 1-minute load-per-CPU requirement is only the operator's check (or outer wrapper script's check).**
- `[source]` **Exact file and line citations**:
  1. `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_validation_20261110.py`:
     - `lines 55-57`:
       ```python
       QUALIFIED_KINDS = {'legacy', 'monitoring'}
       CPU_DIAGNOSTIC_KINDS = {'cpu-legacy', 'cpu-monitoring'}
       NO_LEASE_KINDS = {'canary', 'capture-recheck', *CPU_DIAGNOSTIC_KINDS}
       ```
     - `lines 1007-1028` (`main` for `args.kind in NO_LEASE_KINDS`): Checks `not os.path.lexists(LOCK_PATH)` (`line 1008`) and `'U3WP1_LEASE_FD' not in os.environ` (`line 1009`), verifies the canary prerequisite (`line 1013`), and spawns `--supervised` **without calling `qualify_host(...)`**.
     - `lines 685-691` (`supervised_main` for `args.kind in NO_LEASE_KINDS`): Sets `lease_record = None` (`line 688`) and `qualification_report = None` (`line 689`) without calling `qualify_host(...)`.
     - `lines 733-736`: Inside `run_supervised_driver`, `ps_cpu_sample(logical_cpus)` (`lines 69-94`) samples `os.getloadavg()[0] / max(logical_cpus, 1)` every `2.0` seconds during the run, **only** to record `max_one_minute_load_per_cpu` in `.outer.json` field `"host_contention"` (`lines 810-818, 891-899`). It never aborts or refuses the run based on host load.
  2. `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/run_native_wp1_20261110.py`:
     - `lines 125-138` (`verify_quiet_lease`): When `kind in NO_LEASE_KINDS` (`'cpu-monitoring'`), it returns `host_qualified: False, accepted_quiet_host_timing: False, wall_time_freshness_qualified: False` without checking host load.
     - `lines 197, 222-223`: Calls `u3m.host_load_snapshot()` (`run_native_u3m_20261109.py:130-137`) before and after the worker solely to write `<out>/host-load.json`.
  3. Contrast with `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_qualification_20261110.py`:
     - `lines 21-22, 165-170`: Enforces `MAX_ONE_MINUTE_LOAD_PER_CPU = 0.35`, `MAX_ROOT_CPU_PERCENT = 75.0`, and `MAX_NON_IDLE_PROCESS_CPU_PERCENT = 20.0`, which is called **only** for `QUALIFIED_KINDS = {'legacy', 'monitoring'}` (`native_wp1_validation_20261110.py:694-704, 1029-1039`).
- `[record]` Confirming this in the interrupted run's records:
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111/host-load.json` (`field: "before"`) shows `loadavg_1_5_15: [54.68798828125, 36.666015625, 29.74462890625]` (`5.47` load per CPU across `10` logical CPUs) and the tool still started without refusal.

---

## 6. What a Good Result Looks Like

### 6.1 Files that must exist afterwards

- `[source]` + `[record]` From `native_wp1_validation_20261110.py` (`lines 517-549, 882-925, 976-988`), `run_native_wp1_20261110.py` (`lines 229-263`), `u3k_metrics_plugin_20261109.py` (`lines 288-336`), and `test_native_u3k_profile.py` (`lines 249-277`), a completed `cpu-monitoring` run produces:
  1. **Sibling supervisor records next to `<out>/`**:
     - `<out>.supervisor.json`
     - `<out>.outer.json`
     - `<out>.outer.log`
  2. **Files inside `<out>/`**:
     - `<out>/phase-metrics/<worker_pid>-diagnostic.json` (exactly 1 file matching `*-diagnostic.json`)
     - `<out>/phase-metrics/<worker_pid>-measurement.json` (exactly 1 file matching `*-measurement.json`)
     - `<out>/pytest.xml`
     - `<out>/origins-after.json`
     - `<out>/worker-outcome.json`
     - `<out>/outcome.json`
     - `<out>/wp1-harness.json`
     - `<out>/wp1-cutoff.json`
     - `<out>/source-stability.json`
     - (alongside pre-launch `<out>/plan.json`, `<out>/pytest-command.json`, `<out>/bootstrap.json`, `<out>/dependency-links.json`, `<out>/network-denied.sb`, `<out>/network.json`, `<out>/origins-before.json`, `<out>/subprocess-origins.json`, `<out>/host-load.json`, `<out>/u3m-harness.json`, `<out>/wp1-quiet-lease.json`, `<out>/pytest.log`).

### 6.2 Fields the lead should read first (including the diagnostic result value and the 210-second reservation boundary)

1. **`<out>/phase-metrics/<worker_pid>-diagnostic.json`** (`[source]` written by `test_neutral_pre_reservation_diagnostic` at `tests/test_native_u3k_profile.py:249-277`):
   - `"outcome"`: **Read this first.** `[source]` Look at `tests/test_native_u3k_profile.py:242-247, 276`:
     - `"reached_reservation_without_effect"` means `synthetic_launch` passed `validate_subscription_Execution_before_reservation(...)` within the freshness window and reached the exact pre-reservation stop (`AttemptReservationBoundaryReached` on `attempt_dir.mkdir`) before creating any attempt or evidence directory.
     - `"genuine_refusal"` means `synthetic_launch` raised `ValueError` (specifically `"error": "subscription observation is stale or future-dated"` when wall time from capture to reservation exceeded the `210.0`-second freshness window). **Crucial caveat**: `test_neutral_pre_reservation_diagnostic` asserts `diagnostic['outcome'] in {'reached_reservation_without_effect', 'genuine_refusal'}` (`line 276`), so **`pytest.xml` and `.supervisor.json` report `returncode: 0` even when `"outcome"` is `"genuine_refusal"`!**
   - `"reservation_boundary"`:
     - Non-`null` sample dictionary (`process_cpu`, `thread_cpu`, `self_user_cpu`, `self_system_cpu`, `reaped_child_user_cpu`, `reaped_child_system_cpu`, `wall_monotonic`, `utc`) if `"outcome" == "reached_reservation_without_effect"`, or `null` if `"outcome" == "genuine_refusal"`.
   - `"capture_to_reservation_wall_seconds"` vs. the **`210`-second target**:
     - `[source]` In `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/src/data_sheets_schema/native_subscription_guard_v2.py` (`lines 429-447`) and `tests/test_native_u3k_profile.py` (`lines 257-260`), `"capture_age_limit_seconds": 300` and `"capture_margin_seconds": 90`, so `effective_capture_age_limit_seconds(900) = 300 - 90 = 210` seconds.
     - `validate_subscription_Execution_before_reservation` requires `( reservation_now - capture_timestamp ) <= 210.0` seconds.
     - When `"outcome" == "reached_reservation_without_effect"`, `"capture_to_reservation_wall_seconds"` is a float `<= 210.0` giving the exact margin against the `210`-second target; when `"outcome" == "genuine_refusal"`, `"capture_to_reservation_wall_seconds"` is `null` and `"error"` is `"subscription observation is stale or future-dated"`.
   - Safety & observer-stability fields in `<worker_pid>-diagnostic.json`:
     - `"attempt_exists": false` and `"evidence_exists": false` (no side effects).
     - `"open_call_rows": 0`, `"open_thread_stacks": 0`, `"profile_hook_restored": true`.
     - `"profile_stability.stable": true`, `"profile_stability.restored": true`, `"profile_stability.installation_verified": true`, `"profile_stability.attempts": []`, `"profile_stability.drift": []`.
     - `"consumer_observer_arm": "monitoring"`, `"consumer_observer_calls": []`.
2. **`<out>/phase-metrics/<worker_pid>-measurement.json`** (`[source]` written by `u3k_metrics_plugin_20261109.py:288-336`):
   - `"open_call_rows": 0` and `"open_thread_stacks": 0` (confirms all 457+ call rows closed cleanly).
   - `"phases"`: two phase objects (`"name": "fixture"`, `"outcome": "return"` and `"name": "launch"`, `"outcome": "return"` or `"exception"`), each with `"elapsed"` (`"wall_monotonic"`, `"process_cpu"`, `"self_user_cpu"`, `"self_system_cpu"`, `"reaped_child_user_cpu"`, `"reaped_child_system_cpu"`).
   - `"observed_reservation_windows"`: non-empty list if `reserve_validation_attempt` was entered, or `[]` if refused before reservation.
   - `"call_counts"` and `"calls"`: complete per-call CPU/wall table for `native_wp1_cpu_diagnostic_compare_20261110.py`.
3. **`<out>/pytest.xml`**:
   - `<testsuite ... errors="0" failures="0" skipped="0" tests="1">` with testcase `tests.test_native_u3k_profile::test_neutral_pre_reservation_diagnostic`.
4. **`<out>/origins-after.json`**:
   - `"package_paths": ["/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8/src/data_sheets_schema"]`
   - `"editable_finders": []`
   - `"fairscape_dependency.available": true` and `"fairscape_dependency.origin": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8/fairscape_models/__init__.py"`
5. **`<out>.supervisor.json` and `<out>.outer.json`**:
   - `"returncode": 0`, `"cleanup_verified": true`, `"forced_cleanup": false`, `"interrupted": null`, `"errors": []` (in `.supervisor.json`) and `"returncode": 0`, `"child_returncode": 0`, `"timed_out": false`, `"observed_surviving_pids": []`, `"host_contention"` (in `.outer.json`).

---

## 7. Anything That Makes the Run Unsafe to Start Now (Readiness & Live Blockers)

### 7.1 Technical integrity checks (all pass)

- `[record]` **Contract & implementation SHA-256 verification (`packet-facts.json:331-348`)**:
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-contract-382f0dfd1ce8.json` has SHA-256 `df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e`.
  - All `22` files in `contract["implementation_sha256"]` match on disk in **both** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3` (`all_implementation_files_match_source_root: true`) and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8` (`all_implementation_files_match_worktree: true`), including:
    - `scripts/adhoc/native_wp1_validation_20261110.py`: `a995dba963a2a83d183dbb3fd523462d1fdd51b5a7132be7841c4b90557c0c6e`
    - `scripts/adhoc/run_native_wp1_20261110.py`: `f5d99aa127d62651c85a12ad7626835be5c39c255966a3529deac7b61a676524`
    - `scripts/adhoc/native_wp1_quiet_20261110.py`: `5f4c4514357c9aaef25aa45b516998d68dd26646bc5cb7a76beafbd7a278b1c4`
    - `scripts/adhoc/native_wp1_qualification_20261110.py`: `d2bf4f275c9ba2bd39f1443c41465194d936de38b15fd9c3831e9a8161a7e862`
    - `scripts/adhoc/native_wp1_child_gate_20261110.py`: `ff6f61f6545666e17eb93621dd395f86cb8ef942f0dbecab716ff70562ac8ec3`
    - `scripts/adhoc/run_native_u3m_20261109.py`: `12377050c0155b99daff032a2bb6cf89bc1144b90db2e83c269e01356da99280`
    - `scripts/adhoc/u3k_metrics_plugin_20261109.py`: `34d3975bc5f08aa3b868535d8c8cc81dcad8d99a01b983b12ab959220e88dbde`
    - `scripts/adhoc/u3m_metrics_plugin_20261109.py`: `bc8d0dddc13f53630ab6358c2b93524455d1c6564c97fc1b36b878c493e5d069`
    - `tests/test_native_u3k_profile.py`: `419752a69c5b22f0a06fa63cf9992350bd2c36db3c06401db85499a06bf0f9e5`
- `[record]` **Composition & preimage/postimage verification (`packet-facts.json:349-366`)**:
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/composition.json` has SHA-256 `fe782d98b04ce7d35e244cd396c7a341b690a4943962db65d96a627bfdcf3a89` (`matches_contract_pin: true`), all 4 `protected_preimages_sha256` match (`all_protected_preimages_match: true`), and all 4 `packet_postimages_sha256` match (`all_packet_postimages_match: true`).
- `[record]` **Interpreter & dependency links (`packet-facts.json:300-322`)**:
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python` resolves to `/opt/homebrew/Caskroom/miniforge/base/bin/python3.13` with SHA-256 `e425798f8eff2a5bc2cc58fbcfb4accdceecacbd2cecf9eb97ebad8c9f8b2374` (`matches_contract_interpreter_sha256: true`).
  - All `564` dependency link targets recorded in `dependency-links.json` exist (`all_dependency_targets_exist: true`, `missing_dependency_targets: []`), and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/fairscape-dependency/manifest.json` (`8c80311d8702d4298fc8e09de5355a933e09145a5da756757f59ef756a8fb30f`) and `fairscape_models-37231802f7a0.tar` (`545f5c694a48da5c470b183dc86344b53362f005a846ac0427f81a69e4a1f8eb`) match.
- `[record]` **No stale quiet-window lock (`packet-facts.json:967-968`)**:
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/native_quiet_window.lock` does **not** exist (`os.path.lexists == False`, verified also by `find /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans -maxdepth 2 -name '*lock*'`).

### 7.2 CRITICAL BLOCKER: The one D132-approved `cpu-monitoring` run has ALREADY been claimed and completed (`16:38:13Z`–`16:45:46Z`)

- `[record]` **While `agy4` was preparing this read-only packet, the lead's runner script `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/run_native_cpu_monitoring_once_20261111.sh` (SHA-256 `dcf469a57cfa745b728076e42cc731d901c65db067e8b201adc7238a1d79ce3f`) already claimed and executed the single D132-authorized `cpu-monitoring` diagnostic run to completion (`packet-facts.json:623-927`)**:
  1. **Once-claim file now exists on disk**:
     - Path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json`
     - SHA-256: `dbd0d1d8e3fd3e915d6070e57a19730a0311aefe0da6647b808ad3b4b401fed0`
     - Content:
       ```json
       {
         "authority": "owner decision D132",
         "contract_sha256": "df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e",
         "output": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111",
         "source_commit": "382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b",
         "started_utc": "2026-11-11T16:38:13Z"
       }
       ```
  2. **Completed diagnostic run artifacts on disk**:
     - Output directory: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111`
     - Supervisor record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111.supervisor.json` (SHA-256 `32404f066fcbc25341f3f25e5d7da0dc59ea2588c66afd93c47116114e1743ac`):
       `"returncode": 0`, `"cleanup_verified": true`, `"forced_cleanup": false`, `"interrupted": null`, `"seconds": 452.4003569170018`.
     - Outer record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111.outer.json` (SHA-256 `5c265b93e819e6f68ee6f72735e8dff0073b6f090e65c6a012d862c7fc49baae`):
       `"host_contention": {"logical_cpus": 10, "max_one_minute_load_per_cpu": 2.743603515625, "mean_cpu_percent": 97.77601918465227, "peak_cpu_percent": 100.0, "qualified": false, "samples": 417}`.
     - Diagnostic JSON: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics/67941-diagnostic.json` (SHA-256 `33b032291d891f06249596da823d2a6f26d87d59317388f078b3a399ffc21cba`):
       - `"outcome": "genuine_refusal"`
       - `"error": "subscription observation is stale or future-dated"`
       - `"capture_timestamp": "2026-11-11T16:40:32.438672Z"`
       - `"observed_at": "2026-11-11T16:45:38.987869+00:00"`
       - `"reservation_boundary": null`
       - `"capture_to_reservation_wall_seconds": null`
       - `"attempt_exists": false`, `"evidence_exists": false`, `"open_call_rows": 0`, `"open_thread_stacks": 0`, `"profile_hook_restored": true`, `"profile_stability.stable": true`.
     - Measurement JSON: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics/67941-measurement.json` (`958,870` bytes, SHA-256 `12cba82d359f98d39220db521d8920130da94f863b554d265c0116736738a31d`):
       - `"open_call_rows": 0` (`1,122` total completed call rows: `0..457` in `fixture`, `457..1122` in `launch`).
       - `fixture` phase: `"outcome": "return"`, `wall_monotonic`: `138.84294000000227` s, `process_cpu`: `110.88049` s (`self_user_cpu`: `91.630159` s, `self_system_cpu`: `19.250331` s, `reaped_child_user_cpu`: `3.219667` s, `reaped_child_system_cpu`: `5.910107` s).
       - `launch` phase: `"outcome": "exception"`, `"error": "ValueError: subscription observation is stale or future-dated"`, `wall_monotonic`: `295.7458925420069` s, `process_cpu`: `243.398143` s (`self_user_cpu`: `183.60912399999998` s, `self_system_cpu`: `59.789018999999996` s, `reaped_child_user_cpu`: `5.833375` s, `reaped_child_system_cpu`: `11.474900000000002` s).
  3. **Private Git configuration has already been restored**:
     - Record: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-config-rearm-382f0dfd1ce8-20261111/restored-20261111T164546Z.json` (SHA-256 `af9ee3328d06f2d68525eb1783d255ce6bc5eb79d3af421571b9a2f5721544b9`).
     - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config` is back at `95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1` (`173` bytes, mode `0o644`, equal to `config.bak-u3m-20261109`).
- `[inference]` **Operational conclusion for the lead**:
  - **Do NOT launch another `cpu-monitoring` run.** The one D132-approved diagnostic run has already been executed (`wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111`), its complete `67941-diagnostic.json` and `67941-measurement.json` (`1,122` closed call rows, `open_call_rows: 0`) are on disk, its once-claim `lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json` is in place, and the private Git config is restored to `95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1`.
