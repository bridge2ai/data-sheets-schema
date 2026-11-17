# D159 changed locations

Generated from changes.json by scripts/adhoc/report_d159_limits_20261117.py.

| Location | Before | After |
|---|---|---|
| .github/workflows/main.yaml:25 | timeout-minutes: ${{ github.event_name == 'pull_request' && 45 &#124;&#124; 60 }} | timeout-minutes: ${{ github.event_name == 'pull_request' && 60 &#124;&#124; 80 }} |
| .github/workflows/main.yaml:175 | timeout-minutes: 45 | timeout-minutes: 60 |
| .github/workflows/main.yaml:224 | # Complete synthetic runs have a two-hour attempt budget plus setup. | # Complete synthetic runs have a 160-minute attempt budget plus 20-25 minutes of setup. |
| .github/workflows/main.yaml:225 | timeout-minutes: 180 | timeout-minutes: 240 |
| .github/workflows/main.yaml:275 | timeout-minutes: 45 | timeout-minutes: 60 |
| notes/matched_cborg_2026-09-13/budgeted_cborg.py:35 | LEGACY_UPSTREAM_READ_SECONDS = 1800 | LEGACY_UPSTREAM_READ_SECONDS = 2700 |
| notes/matched_cborg_2026-09-13/budgeted_cborg.py:36 | UPSTREAM_CONNECT_SECONDS = 20 | UPSTREAM_CONNECT_SECONDS = 40 |
| notes/matched_cborg_2026-09-13/budgeted_cborg.py:39 | POLICY_COUNT_TRY_SECONDS = 120 | POLICY_COUNT_TRY_SECONDS = 240 |
| notes/matched_cborg_2026-09-13/budgeted_cborg.py:40 | POLICY_COUNT_PAUSE_SECONDS = 5 | POLICY_COUNT_PAUSE_SECONDS = 10 |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:26 | 'callback_id': 'd4d_tool_policy_v2', 'initialize_timeout_seconds': 30, | 'callback_id': 'd4d_tool_policy_v2', 'initialize_timeout_seconds': 60, |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:27 | 'callback_timeout_seconds': 2, 'runtime_callback_timeout_seconds': 3} | 'callback_timeout_seconds': 4, 'runtime_callback_timeout_seconds': 6} |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:28 | # Explicit opt-in; legacy initialization/replay stays byte-identical (#2420). | # Explicit opt-in; both contracts use D159 time limits. |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:30 | 'callback_id': 'd4d_tool_policy_v3', 'initialize_timeout_seconds': 30, | 'callback_id': 'd4d_tool_policy_v3', 'initialize_timeout_seconds': 60, |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:31 | 'callback_timeout_seconds': 2, 'observer_timeout_seconds': 120, | 'callback_timeout_seconds': 4, 'observer_timeout_seconds': 240, |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:32 | 'runtime_callback_timeout_seconds': 125} | 'runtime_callback_timeout_seconds': 250} |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:37 | CONTROL_WORKER_JOIN_SECONDS = .25 | CONTROL_WORKER_JOIN_SECONDS = .5 |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:553 | ready = self.selector.select(.05) | ready = self.selector.select(.1) |
| notes/matched_cborg_2026-09-13/native_controls/native_control.py:625 | for key, _ in self.selector.select(.05): | for key, _ in self.selector.select(.1): |
| notes/matched_cborg_2026-09-13/native_controls/native_proxy.py:609 | def running(self, *, cleanup_timeout=2): | def running(self, *, cleanup_timeout=4): |
| notes/matched_cborg_2026-09-13/native_controls/native_proxy.py:638 | self.connection.settimeout(20) | self.connection.settimeout(40) |
| notes/matched_cborg_2026-09-13/native_controls/native_proxy.py:913 | self.thread.join(timeout=2) | self.thread.join(timeout=4) |
| notes/matched_cborg_2026-09-13/native_controls/probe_native_history.py:101 | elif name in ('selected_slow','selected_reject','legacy_slow'):time.sleep(4.0) | elif name in ('selected_slow','selected_reject','legacy_slow'):time.sleep(8.0) |
| notes/matched_cborg_2026-09-13/native_controls/probe_native_history.py:162 | if name=='selected_slow':passed=passed and observed[-1]['at']-observed[0]['at']>=4 and times[0]>=observed[-1]['at'] and classified[0]>=observed[-1]['at'] | if name=='selected_slow':passed=passed and observed[-1]['at']-observed[0]['at']>=8 and times[0]>=observed[-1]['at'] and classified[0]>=observed[-1]['at'] |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:444 | exited = reap_observed(process, 2) | exited = reap_observed(process, 4) |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:445 | deadline = time.monotonic() + 2 | deadline = time.monotonic() + 4 |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:454 | time.sleep(0.02) | time.sleep(0.04) |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:540 | time.sleep(0.02) | time.sleep(0.04) |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:567 | await_leader_exit(process, 2) | await_leader_exit(process, 4) |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:576 | if not reap_observed(process, 2): | if not reap_observed(process, 4): |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:577 | raise subprocess.TimeoutExpired(process.args, 2) | raise subprocess.TimeoutExpired(process.args, 4) |
| notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:682 | time.sleep(0.05) | time.sleep(0.1) |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:22 | 'matcher': 'Bash&#124;Read&#124;Write', 'hookCallbackIds': ['d4d_tool_policy_v3'], 'timeout': 125}] | 'matcher': 'Bash&#124;Read&#124;Write', 'hookCallbackIds': ['d4d_tool_policy_v3'], 'timeout': 250}] |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:24 | assert control.HISTORY_CONTRACT['observer_timeout_seconds'] == 120 | assert control.HISTORY_CONTRACT['observer_timeout_seconds'] == 240 |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:30 | lambda c: c.update(observer_timeout_seconds=121), lambda c: c.update(callback_timeout_seconds=3), | lambda c: c.update(observer_timeout_seconds=241), lambda c: c.update(callback_timeout_seconds=5), |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:31 | lambda c: c.update(runtime_callback_timeout_seconds=126), lambda c: c.update(extra=1), | lambda c: c.update(runtime_callback_timeout_seconds=251), lambda c: c.update(extra=1), |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:165 | # Advance history by more than the legacy host's 3 seconds; classifier | # Advance history by more than the legacy host's 6 seconds; classifier |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:166 | # starts afterwards and retains a separate 2-second completion budget. | # starts afterwards and retains a separate 4-second completion budget. |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:170 | clock[0] = 3.25 | clock[0] = 6.25 |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:211 | monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: started + 121)) | monkeypatch.setattr(control, 'time', SimpleNamespace(monotonic=lambda: started + 241)) |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:250 | clock[0] = 2.5  # completed at zero, still inside the distinct host 125s bound | clock[0] = 4.5  # completed at zero, still inside the distinct host 250s bound |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:258 | clock[0] = 2.5 | clock[0] = 4.5 |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:275 | clock[0] = 126. | clock[0] = 251. |
| notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py:533 | clock[0] = 126. | clock[0] = 251. |
| notes/matched_cborg_2026-09-13/native_controls/test_native_launch.py:1165 | #: deadline once per 0.05 s poll, and the clock runs at the real rate after the | #: deadline once per 0.1 s poll, and the clock runs at the real rate after the |
| notes/matched_cborg_2026-09-13/native_controls/test_native_launch.py:1264 | controller poll (0.05 s) is caught only when a deadline check happens to fall | controller poll (0.1 s) is caught only when a deadline check happens to fall |
| notes/matched_cborg_2026-09-13/native_controls/test_probe_native_history.py:35 | 'observer_entered':True,'observer_finished':True,'observer_duration_seconds':4.01,'classifier_calls':1, | 'observer_entered':True,'observer_finished':True,'observer_duration_seconds':8.01,'classifier_calls':1, |
| notes/matched_cborg_2026-09-13/native_controls/test_probe_native_history.py:48 | assert result['cases'][0]['observer_duration_seconds']>=4 | assert result['cases'][0]['observer_duration_seconds']>=8 |
| scripts/draft_native_probe_packet.py:95 | ('BASH_DEFAULT_TIMEOUT_MS','600000','registered native Bash helper timeout','source'), | ('BASH_DEFAULT_TIMEOUT_MS','1000000','registered native Bash helper timeout','source'), |
| scripts/draft_native_probe_packet.py:96 | ('BASH_MAX_TIMEOUT_MS','600000','registered native Bash helper maximum timeout','source'), | ('BASH_MAX_TIMEOUT_MS','1000000','registered native Bash helper maximum timeout','source'), |
| scripts/native_registration_timestamp.py:26 | '-C',str(repository),*arguments],env=env,stderr=subprocess.PIPE,timeout=30).decode().strip() | '-C',str(repository),*arguments],env=env,stderr=subprocess.PIPE,timeout=60).decode().strip() |
| src/data_sheets_schema/historical_digest.py:32 | _GIT_SECONDS = 5.0 | _GIT_SECONDS = 10.0 |
| src/data_sheets_schema/historical_digest.py:382 | process.wait(timeout=1) | process.wait(timeout=2) |
| src/data_sheets_schema/latch_journal.py:41 | env=env, capture_output=True, text=True, timeout=10) | env=env, capture_output=True, text=True, timeout=20) |
| src/data_sheets_schema/native_admission_timer.py:15 | ADMISSION_SECONDS = 900 | ADMISSION_SECONDS = 1500 |
| src/data_sheets_schema/native_admission_timer.py:16 | POLL_SECONDS = 0.1 | POLL_SECONDS = 0.2 |
| src/data_sheets_schema/native_execution.py:112 | env=env, capture_output=True, timeout=30, check=True) | env=env, capture_output=True, timeout=60, check=True) |
| src/data_sheets_schema/native_execution.py:116 | env=env, capture_output=True, timeout=30, check=True) | env=env, capture_output=True, timeout=60, check=True) |
| src/data_sheets_schema/native_execution_authority.py:93 | cwd=ROOT, env=git_env(), capture_output=True, timeout=30, check=True) | cwd=ROOT, env=git_env(), capture_output=True, timeout=60, check=True) |
| src/data_sheets_schema/native_execution_authority.py:119 | input=query, capture_output=True, timeout=30, check=True) | input=query, capture_output=True, timeout=60, check=True) |
| src/data_sheets_schema/native_execution_authority_v2.py:1218 | cwd=ROOT, env=git_env(), capture_output=True, timeout=30, check=True) | cwd=ROOT, env=git_env(), capture_output=True, timeout=60, check=True) |
| src/data_sheets_schema/native_execution_authority_v2.py:1245 | env=git_env(), input=query, capture_output=True, timeout=30, check=True) | env=git_env(), input=query, capture_output=True, timeout=60, check=True) |
| src/data_sheets_schema/native_execution_registration_v2.py:139 | *args], cwd=authority.ROOT, env=env, capture_output=True, timeout=30, check=False) | *args], cwd=authority.ROOT, env=env, capture_output=True, timeout=60, check=False) |
| src/data_sheets_schema/native_host_power.py:23 | def _local(argv, *, limit, timeout=8): | def _local(argv, *, limit, timeout=16): |
| src/data_sheets_schema/native_host_power.py:37 | if not selected.select(min(remaining, 0.1)): | if not selected.select(min(remaining, 0.2)): |
| src/data_sheets_schema/native_launch_review.py:64 | *arguments], env=env, capture_output=True, timeout=10) | *arguments], env=env, capture_output=True, timeout=20) |
| src/data_sheets_schema/native_launch_sequence.py:27 | COMMAND_WAIT_POLL_SECONDS = 0.1 | COMMAND_WAIT_POLL_SECONDS = 0.2 |
| src/data_sheets_schema/native_launch_sequence.py:335 | deadline = time.monotonic() + 2 | deadline = time.monotonic() + 4 |
| src/data_sheets_schema/native_launch_sequence.py:343 | time.sleep(0.02) | time.sleep(0.04) |
| src/data_sheets_schema/native_permission_probe.py:211 | for key, _ in selector.select(timeout=min(0.02, max(0, deadline - time.monotonic()))): | for key, _ in selector.select(timeout=min(0.04, max(0, deadline - time.monotonic()))): |
| src/data_sheets_schema/native_permission_probe.py:233 | check_codesign=False, runner=None, timeout_seconds=10): | check_codesign=False, runner=None, timeout_seconds=20): |
| src/data_sheets_schema/native_permission_probe.py:378 | process.wait(timeout=1) | process.wait(timeout=2) |
| src/data_sheets_schema/native_permission_probe.py:416 | for key, _ in selector.select(timeout=0.02): | for key, _ in selector.select(timeout=0.04): |
| src/data_sheets_schema/native_permission_probe.py:454 | time.sleep(0.001) | time.sleep(0.002) |
| src/data_sheets_schema/native_permission_probe.py:513 | drain_deadline = time.monotonic() + 1 | drain_deadline = time.monotonic() + 2 |
| src/data_sheets_schema/native_pre_dispatch_timing.py:48 | writer.join(timeout=2) | writer.join(timeout=4) |
| src/data_sheets_schema/native_prepared_worker.py:20 | POLL_SECONDS = 0.1 | POLL_SECONDS = 0.2 |
| src/data_sheets_schema/native_prepared_worker.py:21 | VERIFY_SECONDS = 300 | VERIFY_SECONDS = 600 |
| src/data_sheets_schema/native_probe_provider.py:32 | handler.connection.settimeout(min(1.0, remaining)) | handler.connection.settimeout(min(2.0, remaining)) |
| src/data_sheets_schema/native_probe_provider.py:160 | connection.settimeout(min(1.0, remaining)) | connection.settimeout(min(2.0, remaining)) |
| src/data_sheets_schema/native_probe_provider.py:219 | server.timeout = 0.05 | server.timeout = 0.1 |
| src/data_sheets_schema/native_probe_provider.py:236 | thread.join(timeout=2) | thread.join(timeout=4) |
| src/data_sheets_schema/native_run_limits.py:6 | CANARY = ('90', 21600) | CANARY = ('90', 28800) |
| src/data_sheets_schema/native_run_limits.py:7 | PRODUCTION = ('400', 43200) | PRODUCTION = ('400', 57600) |
| src/data_sheets_schema/native_runtime_profiles.py:23 | SYNTHETIC_DEADLINE_SECONDS = 7200 | SYNTHETIC_DEADLINE_SECONDS = 9600 |
| src/data_sheets_schema/native_shared_callback_orchestration.py:178 | # Match the classifier's existing 2-second window. Teardown is a separate | # Match the classifier's D159 4-second window. Teardown is a separate |
| src/data_sheets_schema/native_shared_callback_orchestration.py:179 | # grace period, not an extension of the 120-second observer acceptance window. | # grace period, not an extension of the 240-second observer acceptance window. |
| src/data_sheets_schema/native_shared_callback_orchestration.py:180 | CALLBACK_TEARDOWN_SECONDS = 2.0 | CALLBACK_TEARDOWN_SECONDS = 4.0 |
| src/data_sheets_schema/native_shared_permission_protocol.py:15 | 'callback_id': 'd4d_tool_policy_v2', 'initialize_timeout_seconds': 30, | 'callback_id': 'd4d_tool_policy_v2', 'initialize_timeout_seconds': 60, |
| src/data_sheets_schema/native_shared_permission_protocol.py:16 | 'callback_timeout_seconds': 2, 'runtime_callback_timeout_seconds': 3} | 'callback_timeout_seconds': 4, 'runtime_callback_timeout_seconds': 6} |
| src/data_sheets_schema/native_shared_permission_protocol.py:18 | 'callback_id': 'd4d_tool_policy_v3', 'initialize_timeout_seconds': 30, | 'callback_id': 'd4d_tool_policy_v3', 'initialize_timeout_seconds': 60, |
| src/data_sheets_schema/native_shared_permission_protocol.py:19 | 'callback_timeout_seconds': 2, 'observer_timeout_seconds': 120, | 'callback_timeout_seconds': 4, 'observer_timeout_seconds': 240, |
| src/data_sheets_schema/native_shared_permission_protocol.py:20 | 'runtime_callback_timeout_seconds': 125} | 'runtime_callback_timeout_seconds': 250} |
| src/data_sheets_schema/native_shared_runtime_values.py:29 | BASH_TIMEOUT_ENV = {'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000'} | BASH_TIMEOUT_ENV = {'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000'} |
| src/data_sheets_schema/native_shared_runtime_values.py:173 | raise ValueError('native Bash timeouts must both be exactly 600000 milliseconds') | raise ValueError('native Bash timeouts must both be exactly 1000000 milliseconds') |
| src/data_sheets_schema/native_shared_streams.py:124 | deadline = time.monotonic() + 0.02 | deadline = time.monotonic() + 0.04 |
| src/data_sheets_schema/native_shared_streams.py:126 | time.sleep(0.0001) | time.sleep(0.0002) |
| src/data_sheets_schema/native_subscription_capture.py:193 | deadline = time.monotonic() + 2 | deadline = time.monotonic() + 4 |
| src/data_sheets_schema/native_subscription_capture.py:201 | time.sleep(0.01) | time.sleep(0.02) |
| src/data_sheets_schema/native_subscription_capture.py:223 | for key, _ in selector.select(timeout=0.02): | for key, _ in selector.select(timeout=0.04): |
| src/data_sheets_schema/native_subscription_guard_v2.py:24 | MAX_AGE_SECONDS = 1200 | MAX_AGE_SECONDS = 1800 |
| src/data_sheets_schema/native_supervisor_authority.py:26 | env=git_env(), text=True, timeout=10).strip() | env=git_env(), text=True, timeout=20).strip() |
| src/data_sheets_schema/native_supervisor_authority_v2.py:26 | env=git_env(), text=True, timeout=10).strip() | env=git_env(), text=True, timeout=20).strip() |
| src/data_sheets_schema/native_u4b_policy.py:16 | 'max_age_seconds': 1200, | 'max_age_seconds': 1800, |
| src/data_sheets_schema/native_u4b_probe_sequence.py:318 | for key, _ in selector.select(timeout=0.02): | for key, _ in selector.select(timeout=0.04): |
| src/data_sheets_schema/prompt_registry.py:279 | timeout=10, cwd=str(cwd) if cwd else None, env=git_env())   # no borrowed GIT_DIR (#1728) | timeout=20, cwd=str(cwd) if cwd else None, env=git_env())   # no borrowed GIT_DIR (#1728) |
| src/data_sheets_schema/provenance.py:373 | r = subprocess.run(cmd, capture_output=True, timeout=15, cwd=str(cwd) if cwd else None, env=env) | r = subprocess.run(cmd, capture_output=True, timeout=30, cwd=str(cwd) if cwd else None, env=env) |
| tests/native_shared_fixture.py:208 | 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', | 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', |
| tests/native_shared_omission_fixture.py:243 | 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', | 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', |
| tests/test_ci_sharding.py:222 | assert job["timeout-minutes"] == 45 | assert job["timeout-minutes"] == 60 |
| tests/test_ci_sharding.py:223 | assert jobs["python-tests"]["timeout-minutes"] == "${{ github.event_name == 'pull_request' && 45 &#124;&#124; 60 }}" | assert jobs["python-tests"]["timeout-minutes"] == "${{ github.event_name == 'pull_request' && 60 &#124;&#124; 80 }}" |
| tests/test_ci_sharding.py:400 | ("native-public-completion", SHORT_NATIVE_LANES, "native", 45), | ("native-public-completion", SHORT_NATIVE_LANES, "native", 60), |
| tests/test_ci_sharding.py:401 | ("native-public-long", LONG_NATIVE_LANES, "native", 180), | ("native-public-long", LONG_NATIVE_LANES, "native", 240), |
| tests/test_native_admission_failure.py:33 | advanced[0] = 901 * 10**9  # Expire only after verification is entered. | advanced[0] = 1501 * 10**9  # Expire only after verification is entered. |
| tests/test_native_admission_failure.py:50 | # Keep the real 900-second bound and signal handler. The clock jump | # Keep the real 1500-second bound and signal handler. The clock jump |
| tests/test_native_admission_failure.py:105 | advance[0] = 901 * 10**9 | advance[0] = 1501 * 10**9 |
| tests/test_native_admission_timer.py:19 | timer = AdmissionTimer(clock(), seconds=900 if suspend else .2, clock=clock) | timer = AdmissionTimer(clock(), seconds=1500 if suspend else .2, clock=clock) |
| tests/test_native_admission_timer.py:26 | ticks[0] = 901 * 10**9 | ticks[0] = 1501 * 10**9 |
| tests/test_native_admission_timer.py:43 | timer = AdmissionTimer(100, seconds=900) | timer = AdmissionTimer(100, seconds=1500) |
| tests/test_native_admission_timer.py:44 | timer.check(900 * 10**9 + 99) | timer.check(1500 * 10**9 + 99) |
| tests/test_native_admission_timer.py:46 | timer.check(900 * 10**9 + 100) | timer.check(1500 * 10**9 + 100) |
| tests/test_native_attempt_deadline.py:21 | [at]pytest.mark.parametrize('seconds', [900, 21600, 43200]) | [at]pytest.mark.parametrize('seconds', [1500, 28800, 57600]) |
| tests/test_native_attempt_deadline.py:31 | ticks['continuous'] += 899 * 10**9  # Within admission's own bound; excluded from child time. | ticks['continuous'] += 1499 * 10**9  # Within admission's own bound; excluded from child time. |
| tests/test_native_attempt_deadline.py:46 | [at]pytest.mark.parametrize('seconds', [900, 21600, 43200]) | [at]pytest.mark.parametrize('seconds', [1500, 28800, 57600]) |
| tests/test_native_attempt_deadline.py:51 | def verify(): ticks['continuous'] += 899 * 10**9 | def verify(): ticks['continuous'] += 1499 * 10**9 |
| tests/test_native_attempt_deadline.py:58 | ticks['continuous'] += (seconds - 898) * 10**9 | ticks['continuous'] += (seconds - 1498) * 10**9 |
| tests/test_native_attempt_deadline.py:68 | [at]pytest.mark.parametrize('admission_seconds', [900, 901]) | [at]pytest.mark.parametrize('admission_seconds', [1500, 1501]) |
| tests/test_native_attempt_deadline.py:94 | cwd=tmp_path, env={}, deadline_seconds=900, verify_launch=verify) | cwd=tmp_path, env={}, deadline_seconds=1500, verify_launch=verify) |
| tests/test_native_ci_evidence.py:44 | assert result['declared_limits']['attempt_seconds'] == 900 | assert result['declared_limits']['attempt_seconds'] == 9600 |
| tests/test_native_ci_evidence.py:45 | assert result['declared_limits']['helper_seconds'] == 180 | assert result['declared_limits']['helper_seconds'] == 1000 |
| tests/test_native_ci_evidence.py:46 | assert result['declared_limits']['runner_seconds'] == 3600 | assert result['declared_limits']['runner_seconds'] == 14400 |
| tests/test_native_dispatch_boundary_d156.py:23 | clock[0] += 1201 | clock[0] += 1801 |
| tests/test_native_execution_registration_v2.py:81 | 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(tmp_path.resolve() / 'attempt' / 'helper-cache'), | 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', 'PYSTOW_HOME': str(tmp_path.resolve() / 'attempt' / 'helper-cache'), |
| tests/test_native_launch_review.py:14 | 'runtime': {'budget_guard_usd': '90', 'deadline_seconds': 21600, | 'runtime': {'budget_guard_usd': '90', 'deadline_seconds': 28800, |
| tests/test_native_launch_sequence.py:77 | 'runtime': {'budget_guard_usd': '90', 'deadline_seconds': 21600, 'model': 'fixture-model', | 'runtime': {'budget_guard_usd': '90', 'deadline_seconds': 28800, 'model': 'fixture-model', |
| tests/test_native_launch_sequence.py:84 | 'max_age_seconds': 1200, 'pre_reservation_margin_seconds': 300}})}, | 'max_age_seconds': 1800, 'pre_reservation_margin_seconds': 300}})}, |
| tests/test_native_launch_sequence.py:183 | source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1200) | source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1800) |
| tests/test_native_launch_sequence.py:230 | expiry = guard.strict_json(raw)['prepared_at'] + 1200 | expiry = guard.strict_json(raw)['prepared_at'] + 1800 |
| tests/test_native_launch_sequence.py:440 | attempt=attempt, source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1200) | attempt=attempt, source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1800) |
| tests/test_native_launch_sequence.py:442 | registration_raw=raw, attempt=attempt, max_age_seconds=1200) | registration_raw=raw, attempt=attempt, max_age_seconds=1800) |
| tests/test_native_launch_sequence_signals.py:155 | attempt=attempt, source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1200) | attempt=attempt, source_sha256='a' * 64, environment_sha256='b' * 64, max_age_seconds=1800) |
| tests/test_native_launch_sequence_signals.py:157 | registration_raw=raw, attempt=attempt, max_age_seconds=1200) | registration_raw=raw, attempt=attempt, max_age_seconds=1800) |
| tests/test_native_permission_probe.py:203 | assert kwargs["timeout"] == 10 and kwargs["stdin"] == probe.subprocess.DEVNULL | assert kwargs["timeout"] == 20 and kwargs["stdin"] == probe.subprocess.DEVNULL |
| tests/test_native_permission_probe.py:742 | assert timeout == 2 | assert timeout == 4 |
| tests/test_native_prepared_sequence.py:310 | monkeypatch.setattr(native_u4b_policy, 'registered_policy', lambda runtime: {'max_age_seconds': 1200}) | monkeypatch.setattr(native_u4b_policy, 'registered_policy', lambda runtime: {'max_age_seconds': 1800}) |
| tests/test_native_prepared_worker.py:18 | binding = dict(registration_raw=b'registration', attempt=attempt, max_age_seconds=1200) | binding = dict(registration_raw=b'registration', attempt=attempt, max_age_seconds=1800) |
| tests/test_native_prepared_worker.py:48 | monkeypatch.setattr(worker.time, 'time', lambda: 1300.0) | monkeypatch.setattr(worker.time, 'time', lambda: 1900.0) |
| tests/test_native_prepared_worker.py:56 | ticks = iter([0.0, 1200.0]) | ticks = iter([0.0, 1800.0]) |
| tests/test_native_prepared_worker.py:102 | max_age_seconds=1200, source_sha256='a' * 64, environment_sha256='b' * 64) | max_age_seconds=1800, source_sha256='a' * 64, environment_sha256='b' * 64) |
| tests/test_native_probe_drafts.py:32 | assert require_registered_pair(candidate)==CANARY==('90',21600) | assert require_registered_pair(candidate)==CANARY==('90',28800) |
| tests/test_native_recorder_env.py:36 | 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(config.parent / 'helper-cache')}} | 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', 'PYSTOW_HOME': str(config.parent / 'helper-cache')}} |
| tests/test_native_run_limits.py:37 | [at]pytest.mark.parametrize('pair', [('90',43200),('400',21600),('100',21600),('400',43201), | [at]pytest.mark.parametrize('pair', [('90',57600),('400',28800),('100',28800),('400',57601), |
| tests/test_native_run_limits.py:38 | ('90.0',21600),('400',43200.0),(90,21600),('90',True), | ('90.0',28800),('400',57600.0),(90,28800),('90',True), |
| tests/test_native_run_limits.py:39 | (None,21600),('90',None),([],21600)]) | (None,28800),('90',None),([],28800)]) |
| tests/test_native_run_limits.py:50 | [at]pytest.mark.parametrize('pair', [('90', 43200), ('400', 21600), ('100', 21600), | [at]pytest.mark.parametrize('pair', [('90', 57600), ('400', 28800), ('100', 28800), |
| tests/test_native_run_limits.py:51 | ('400', 43201), ('90.0', 21600)]) | ('400', 57601), ('90.0', 28800)]) |
| tests/test_native_shared_observations.py:12 | POLICY={'pretool_control':{'event':'PreToolUse','callback_id':'fixed','matcher':'Bash&#124;Read&#124;Write','runtime_callback_timeout_seconds':125}, | POLICY={'pretool_control':{'event':'PreToolUse','callback_id':'fixed','matcher':'Bash&#124;Read&#124;Write','runtime_callback_timeout_seconds':250}, |
| tests/test_native_shared_observations.py:163 | 'hooks':{'PreToolUse':[{'matcher':contract['matcher'],'hookCallbackIds':[contract['callback_id']],'timeout':125}]}}}} | 'hooks':{'PreToolUse':[{'matcher':contract['matcher'],'hookCallbackIds':[contract['callback_id']],'timeout':250}]}}}} |
| tests/test_native_shared_permission_protocol.py:116 | wrong_type = {**control.HISTORY_CONTRACT, 'initialize_timeout_seconds': 30.0} | wrong_type = {**control.HISTORY_CONTRACT, 'initialize_timeout_seconds': 60.0} |
| tests/test_native_subscription_guard_v2.py:27 | 'budget_guard_usd': '90', 'deadline_seconds': 21600, | 'budget_guard_usd': '90', 'deadline_seconds': 28800, |
| tests/test_native_synthetic_profiles.py:51 | 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'), | 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', 'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'), |
| tests/test_native_synthetic_profiles.py:76 | [at]pytest.mark.parametrize('replacement', [None, '120000', '600001', 600000]) | [at]pytest.mark.parametrize('replacement', [None, '120000', '1000001', 1000000]) |
| tests/test_native_synthetic_profiles.py:187 | changed['deadline_seconds'] = 21600 | changed['deadline_seconds'] = 28800 |
| tests/test_native_synthetic_profiles.py:240 | old['deadline_seconds'] = 21600 | old['deadline_seconds'] = 28800 |
| tests/test_native_u4b_a3_policy.py:22 | 'max_age_seconds': 1200, | 'max_age_seconds': 1800, |
| tests/test_native_u4b_a3_policy.py:65 | [at]pytest.mark.parametrize('capture_age,permits_reservation', [(899, True), (900, True), (901, False)]) | [at]pytest.mark.parametrize('capture_age,permits_reservation', [(1499, True), (1500, True), (1501, False)]) |
| tests/test_native_u4b_a3_policy.py:66 | def test_d138_latest_admissible_reservation_age_is_900_seconds(case, capture_age, permits_reservation): | def test_d138_latest_admissible_reservation_age_is_1500_seconds(case, capture_age, permits_reservation): |
| tests/test_native_u4b_a3_policy.py:68 | assert case['owner']['max_age_seconds'] == 1200 | assert case['owner']['max_age_seconds'] == 1800 |
| tests/test_native_u4b_a3_policy.py:80 | [at]pytest.mark.parametrize('dispatch_age,passes', [(1199, True), (1200, True), (1201, False)]) | [at]pytest.mark.parametrize('dispatch_age,passes', [(1799, True), (1800, True), (1801, False)]) |
| tests/test_native_u4b_a3_policy.py:82 | clock = [case['now'] + 900] | clock = [case['now'] + 1500] |
| tests/test_native_u4b_a4_review.py:33 | assert review.validate_bundle(raw, bundle_raw, word_raw)['deadline_seconds'] == 21600 | assert review.validate_bundle(raw, bundle_raw, word_raw)['deadline_seconds'] == 28800 |
| tests/test_native_u4b_a4_review.py:34 | assert review.validate_bundle(raw, bundle_raw, word_raw)['deadline_seconds'] == 21600 | assert review.validate_bundle(raw, bundle_raw, word_raw)['deadline_seconds'] == 28800 |
| tests/test_native_u4b_a4_review.py:105 | [at]pytest.mark.parametrize('deadline', [True, 0, 60, 900, 21599, 21601, 86400, 21600.0]) | [at]pytest.mark.parametrize('deadline', [True, 0, 60, 900, 28799, 28801, 86400, 28800.0]) |
| tests/test_native_u4b_a4_review.py:113 | with pytest.raises(ValueError, match='21600'): | with pytest.raises(ValueError, match='28800'): |
| tests/test_native_u4b_a4_review.py:189 | assert review.validate_bundle(*evidence)['deadline_seconds'] == 21600 | assert review.validate_bundle(*evidence)['deadline_seconds'] == 28800 |
| tests/test_native_u4b_probe_sequence.py:295 | assert invocation['environment']['BASH_DEFAULT_TIMEOUT_MS'] == '600000' | assert invocation['environment']['BASH_DEFAULT_TIMEOUT_MS'] == '1000000' |
| tests/test_native_u4b_probe_sequence.py:296 | assert invocation['environment']['BASH_MAX_TIMEOUT_MS'] == '600000' | assert invocation['environment']['BASH_MAX_TIMEOUT_MS'] == '1000000' |
| tests/test_native_u4b_runtime.py:57 | 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'), | 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', 'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'), |
| tests/test_native_u4b_runtime.py:59 | 'deadline_seconds': 21600, 'budget_guard_usd': '90', | 'deadline_seconds': 28800, 'budget_guard_usd': '90', |
| tests/utils/native_synthetic_evidence.py:45 | 'HOME': str(home), 'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(root / 'native-attempt' / 'helper-cache'), | 'HOME': str(home), 'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000', 'PYSTOW_HOME': str(root / 'native-attempt' / 'helper-cache'), |
| utils/native_ci_evidence.py:44 | LIMITS = {'attempt_seconds': 900, 'helper_seconds': 180, 'runner_seconds': 3600, | LIMITS = {'attempt_seconds': 9600, 'helper_seconds': 1000, 'runner_seconds': 14400, |

Unchanged limits and review findings are recorded in scripts/adhoc/d159_review_findings_20261117.json.

Inventory includes grep -rnE over src, native_controls, tests, scripts, utils, .claude, workflow and runbook; grep does not consult gitignore.
Historical observed timings, test-controlled short fault deadlines, caller-supplied durations, zero/nonblocking waits,
numeric size/count bounds, minimum floors and age rules are not reinterpreted as production work-time defaults.
