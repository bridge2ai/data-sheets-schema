"""6233, 2026-11-14: write and verify the answer-first lead handoff.

Inputs: generated scratch evidence/tables, test logs, and current Git identity.
Output: the assigned external handoff; prints its computed SHA-256.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess


root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-native-bash-timeout-20261114'
handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-bash-timeout-20261114.md'
data = json.loads((scratch / 'evidence.json').read_text())
canary = json.loads((scratch / 'profile-deadline-canary/profile.json').read_text())
assert canary['error'].startswith('ProfileDeadline:')
assert 4 <= canary['wall_seconds'] < 15
assert (scratch / 'profile-deadline-canary/reads.pstats').stat().st_size > 0
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
commits = subprocess.check_output(['git', 'log', 'efb37afee..HEAD', '--format=%H %s'], cwd=root, text=True)
(scratch / 'local-commits.txt').write_text(commits)
tests = {}
for name in ('focused', 'propagation'):
    log = (scratch / (name + '.log')).read_text()
    matches = re.findall(r'\d+ passed[^\n]*', log)
    assert matches, name
    tests[name] = matches[-1]
assert (scratch / 'propagation-exit-status.txt').read_text().strip() == '0'
protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_controller_sources_v2.json',
    '.claude/skills/d4d-generation-specificity-audit/scan.py']
diff = subprocess.check_output(['git', 'diff', 'efb37afee', '--', *protected], cwd=root)
assert not diff
(scratch / 'protected-and-scanner.diff').write_bytes(diff)
profiles = data['profile']
correction = data['cases'][0]
unmeasured = ', '.join(row['id'] for row in correction['requests_without_timing']) or 'none'
pending_stages = [m for m in data['cases'][2]['metrics'] if m['label'] == 'stage advance']
longest = max(pending_stages, key=lambda m: m['wall_seconds'])
pins = '\n'.join(f"- `{name}`: `{digest}`" for name, digest in data['scanner_pins'].items())
text = f"""The Bash timeout repair is implemented and committed locally, but the native canary is not ready. All three offline public tests failed: correction and pending reached the unchanged overall attempt deadline; omissions reached the history callback response window. No observed first stop was a Bash helper timeout. Pending's stage advance completed in {longest['wall_seconds']:.6f} wall seconds, beyond the former synthetic 180-second limit. The longer registered timeout therefore removes a demonstrated helper failure mode, but does not close 6233 or the shutdown finding.

Recommendation: retain both registered Bash values at 600000 milliseconds, review the scanner pin proposal, and address repeated cold reconstruction and callback admission cost before another canary claim. Do not increase the overall deadline or callback response window on this evidence. No additional CPU optimization was implemented: changes to protected RunSpec behavior, cross-helper cache trust, or helper lifetime need a separate design decision. The partial CPU profile supports investigating immutable schema derivation reuse while retaining every fresh authority and filesystem check.

W = `{root}`. S = `{scratch}`. Branch: `codex/native-bash-timeout-20261114`. Final local head: `{head}`. The public runs bind their own saved source commits in S/evidence.json; all used the implementation before the later diagnostic/report-only commits. S/local-commits.txt records the complete local commit list. Nothing was pushed and no GitHub write, provider, model, or real native binary was invoked.

Implementation and consumer census

- W/src/data_sheets_schema/native_shared_runtime_values.py adds the two keys to the required and allowed version 2 environment and requires their exact string values. Version 1 constants and validation retain their old environment contract.
- W/src/data_sheets_schema/native_runtime_profiles.py requires the same values for synthetic declarations and rotates only the authorized synthetic peer pin in addition to that validation call. W/src/data_sheets_schema/native_shared_permissions.py applies exact values to production permission declarations; its derived closed environment already includes the complete registered key set.
- W/scripts/draft_native_probe_packet.py emits both fixed values. Updated runtime fixtures are W/tests/native_shared_fixture.py, W/tests/native_shared_omission_fixture.py, W/tests/utils/native_synthetic_evidence.py, W/tests/test_native_execution_registration_v2.py, W/tests/test_native_synthetic_profiles.py, W/tests/test_native_u4b_runtime.py, and W/tests/test_native_recorder_env.py.
- Existing forwarding is retained in W/src/data_sheets_schema/native_shared_registration.py, W/src/data_sheets_schema/native_subscription_capture.py, W/src/data_sheets_schema/native_u4b_probe_sequence.py, and W/src/data_sheets_schema/native_execution_orchestration.py. Each copies or passes the full explicit registered environment. W/src/data_sheets_schema/native_execution.py observes and hashes that complete environment. These files needed no additional key whitelist. W/tests/test_native_u4b_probe_sequence.py now asserts both values at the observation child boundary.
- Version 3 here is runtime-basis evidence handled by W/src/data_sheets_schema/native_u4b_runtime.py and the same version 2 environment validator, not a separate version 3 key set. The ignore-independent search across src and tests is recorded in S/v3-search.txt; it found no separate V3 environment constants or validate_runtime_v3 definition. S/environment-consumers.txt records the ignore-independent key/caller census.
- W/tests/fixtures/native_shared_execution/fake_cli.py reads its subprocess timeout from the child's BASH_DEFAULT_TIMEOUT_MS. Its stderr records each completed/reaped Bash invocation's wall time and resource.getrusage child user/system CPU deltas. It does not change callback grants, acceptance assertions, overall deadlines, or response windows.

Scanner integration remains for the lead. Both complete runtime module bodies are pinned, so both expectations need review. S/scanner-pin-proposal.patch is generated and unapplied. The specificity scanner itself was not edited or claimed passing. New computed file hashes are:

{pins}

The authorized synthetic peer body SHA-256 is `{data['synthetic_peer_sha256']}`. No protected file, prompt pin, controller manifest, or controller pin changed; S/protected-and-scanner.diff is empty. No controller-manifest proposal is needed.

Measured outcomes

The following tables are generated by W/scripts/adhoc/summarize_bash_timeout_20261114.py from S/evidence.json and saved in S/tables.md. JUnit suite seconds are reported as recorded, not substituted for pytest's slightly different summary timer. Every case ran alone through W/scripts/adhoc/run_bash_timeout_case_20261114.sh. Each case directory contains command.txt, pytest.log, junit.xml, start/end records, and the saved attempt.

{(scratch / 'tables.md').read_text()}
CPU means the sum of child user and system CPU deltas, not wall time. It avoids counting time descheduled, but is not a claim that host conditions cannot affect CPU work. The ranking covers completed measured invocations in the stopped correction prefix, not a completed correction run. Requested correction tool calls without a terminal timing record: {unmeasured}. No CPU total or completion is invented for those calls. Full commands, all recorded helper timings, declared child timeout values, source commits, and missing-timing requests are in S/evidence.json. Each public result reports control_shutdown_complete false and an unfinished worker; that is evidence for the existing 6234 investigation, not a shutdown repair.

Read-only profiling and its limit

W/scripts/adhoc/profile_bash_helper_reads_20261114.py models fresh stage read boundaries without capture_stage, advance, or publication. S/stage-profile/profile.json and S/stage-profile/reads.pstats retain the original partial CPU-clock cProfile; S/stage-profile/profile.txt is its readable summary. It used {profiles['cpu_seconds']:.6f} resource CPU seconds over {profiles['wall_seconds']:.6f} wall seconds, and completed no modeled read boundary. The intended one-shot 600-second TimeoutError did not unwind promptly. I interrupted only that diagnostic; its recorded outcome is KeyboardInterrupt. The exact swallowing boundary was not established. These heavily instrumented inclusive costs overlap and are not normal helper budgets or a complete attribution of each helper.

The dominant partial costs are fresh reconstruction, repeated preparation verification, and YAML/schema parsing. The original profile and failed bound remain preserved. The diagnostic now uses repeating BaseException cancellation. A same-entry-point short canary requested {canary['requested_timeout_seconds']:.0f} seconds, stopped with ProfileDeadline after {canary['wall_seconds']:.6f} wall seconds, and saved non-empty profile data in S/profile-deadline-canary. This proves cancellation and persistence on that path; it does not prove a completed reconstruction or a hard OS-enforced bound against arbitrary swallowed signals.

Checks and review

S/focused.log: {tests['focused']}.
S/propagation.log: {tests['propagation']}.
The first propagation session passed its assertions but tripped the repository notes guard because I created the review note while it was running. S/propagation-notes-guard.log and S/propagation-notes-guard.xml preserve that contaminated session. The final propagation result above is a fresh rerun after committing the note, with exit status zero saved in S/propagation-exit-status.txt.
The focused cohort covers exact/missing/wrong-type timeout refusal, synthetic identity, legacy environment parity, probe drafting, runtime-basis validation, and recorder environment. The propagation cohort covers the observation child, full saved permission verification, and helper-cache boundaries. Successful public helpers also demonstrate environment forwarding. No real native binary timeout behavior was exercised.

The separate read-only source review retained all authority checks and found no production cache or relaxed assertion. W/notes/native_bash_timeout_review_20261114.md records findings for the lead because GitHub issue creation was forbidden: public completion failures, unfinished shutdown workers, pending scanner expectations, and the diagnostic timeout defect with its bounded repair. A full suite and scanner acceptance after the lead's pin rotation remain unverified. No further expensive retry or changed acceptance bound was launched.

Reproduction

From W, use the configured interpreter `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python` and PYTHONPATH pointing to W/src. All output arguments must remain under S and use fresh directories.

```text
bash scripts/adhoc/run_bash_timeout_case_20261114.sh correction NEW_BASENAME
bash scripts/adhoc/run_bash_timeout_case_20261114.sh omissions NEW_BASENAME
bash scripts/adhoc/run_bash_timeout_case_20261114.sh pending NEW_BASENAME
python scripts/adhoc/summarize_bash_timeout_20261114.py S
python scripts/adhoc/write_bash_timeout_handoff_20261114.py
```

The reporting scripts and diagnostic helpers are committed on this branch. W/scripts/adhoc/update_bash_timeout_fixtures_20261114.py preserves the one-time fixture/pin migration; do not rerun it on already updated files. Saved registrations bind their original source commits; do not rewrite their evidence to replay on a later source identity. This handoff is written in the assignment's external handoff directory for the lead and is not staged in the report worktree.
"""
assert chr(64) not in text
# Verify every W/ or S/ file reference in the prose; bare symbolic commands use
# W and S intentionally and are explained above, rather than nonexistent paths.
for prefix, relative in re.findall(r'\b([WS])/([A-Za-z0-9_./-]+)', text):
    relative = relative.rstrip('.')
    path = (root if prefix == 'W' else scratch) / relative
    assert path.exists(), path
assert Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python').exists()
handoff.write_text(text)
assert handoff.stat().st_size > 0 and handoff.read_text() == text
print(str(handoff))
print(hashlib.sha256(handoff.read_bytes()).hexdigest())
