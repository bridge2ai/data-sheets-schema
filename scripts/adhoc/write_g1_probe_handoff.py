"""Write G1's answer-first handoff from retained test and Git outputs.

Inputs: committed worktree and .temp/g1 logs. Outputs: handoff and evidence JSON.
Serves review issues 6204, 6209, 6210, 6219, 6226, 6228; 2026-11-14.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path.cwd()
logs = root / '.temp/g1'
out = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-pr5968-probe-fixes-20261114.md')

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

def summary(name):
    lines = (logs / name).read_text().splitlines()
    return next(line for line in reversed(lines) if re.search(r'\d+ (passed|failed|errors?)', line))

protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_controller_sources_v1.json',
    'src/data_sheets_schema/native_controller_sources_v2.json']
assert not git('diff', 'f8604be5a', '--', *protected)
for manifest in protected[-2:]:
    for row in json.loads((root / manifest).read_text())['modules'].values():
        assert not git('diff', 'f8604be5a', '--', row['path'])

issues = {
    6204: ('Fixed', 'Scoped SIGINT/SIGTERM unwinding covers loaded inputs, the version child and permission traces. Cleanup ignores repeated stops and restores handlers. Proving tests: test_permission_stop_unwinds_and_restores_handlers and test_native_boundary_reaps_closes_and_retains_failed_evidence[sigterm].'),
    6209: ('Fixed', 'Input snapshots persist before the version child; observer snapshots persist at capture; completed traces persist before the next trace; failure.json retains the exception. Proving test: test_captured_inputs_survive_later_failure_without_authority_fixture[True]. The existing genuine-consumer regression is retained but its fixture refuses this mandated scratch location.'),
    6210: ('Fixed', 'Normal completion waits for stderr EOF. Cleanup drains both pipes under byte/time bounds before closing; unprocessed stdout and drainage status remain separate evidence. Incomplete drainage refuses success. Proving tests: test_shutdown_tail_retains_bytes_and_explicitly_marks_truncation, test_shutdown_tail_times_out_on_inherited_open_pipe and test_native_boundary_reaps_closes_and_retains_failed_evidence.'),
    6219: ('Fixed', 'A claimed bound phase records exception type/message, authorization digest and permission-directory existence. Failed claims remain spent; retries cannot replace the original failure. Proving test: test_bound_failure_record_preserves_claim_without_runtime_fixture.'),
    6226: ('Fixed', 'The checked transport source is retained before child work and supplies the final evidence digest. No post-run Path.read_bytes reopening or transport-capability shadowing remains. Proving test: test_captured_inputs_survive_later_failure_without_authority_fixture[False].'),
    6228: ('Fixed', 'The gate requires explicit dontAsk and success fields, including refusal of missing fields. The synthetic Python peer and incomplete gate fixture now supply them; only the synthetic peer hash changed. Proving tests: test_terminal_requires_explicit_permission_and_success, test_all_fifteen_gates_remain_present_on_incomplete_capture and the synthetic-profile test file.'),
}
data = {'head': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
        'base': git('rev-parse', 'f8604be5a'), 'commits': git('log', '--format=%H %s', 'f8604be5a..HEAD'),
        'summary': summary('final-suite.log'), 'exit': (logs / 'final-suite.exit').read_text().strip(),
        'logs': {name: {'sha256': hashlib.sha256((logs/name).read_bytes()).hexdigest(), 'summary': summary(name)}
                 for name in ('final-suite.log', 'committed.log', 'diagnostic.log', 'profiles.log', 'captured-unit.log', 'bound-unit.log')}}
(logs / 'handoff-evidence.json').write_text(json.dumps(data, indent=2) + '\n')
text = '''G1: all assigned fixes are committed locally. No issue is disputed or deferred. Focused offline regressions prove each fix; the full test run is not green because the assignment's required in-worktree scratch path violates existing authority-overlap checks. No native binary, external model/provider, push or GitHub write was used.

'''
text += f"Branch: `{data['branch']}`. Head: `{data['head']}`. Base: `{data['base']}`.\n\n"
for issue, (status, description) in issues.items():
    commits = git('log', '--format=%H %s', f'--grep=#{issue}', 'f8604be5a..HEAD')
    text += f'Issue #{issue}: {status}. {description}\n\nLocal commits:\n\n'
    text += '\n'.join('- `' + line + '`' for line in commits.splitlines()) + '\n\n'
text += f'''Validation: `{data['summary']}`. Pytest exit code: `{data['exit']}`. These are complete test-file runs for permission probe, bound sequence, model aliases, shared gates, execution gates and synthetic profiles. The passing tests include the focused regressions named above. Existing permission/sequence fixtures fail before exercising their test bodies with “neutral roots overlap authority” or “probe sequence directory overlaps source or the selected executable”. The refusal is preserved; no production check or assertion was weakened.

Reproduce from this worktree: `bash scripts/adhoc/verify_g1_probe_review.sh`. It sets the required interpreter, PYTHONPATH, PYTHONDONTWRITEBYTECODE and in-worktree basetemp, and uses the permitted worker limit. The command and complete result remain in [{root / 'scripts/adhoc/verify_g1_probe_review.sh'}]({root / 'scripts/adhoc/verify_g1_probe_review.sh'}) and [{logs / 'final-suite.log'}]({logs / 'final-suite.log'}).

Earlier diagnostics remain retained. The broad integration run was deliberately interrupted after reproducing the scratch-path failures: `{summary('committed.log')}`. Its incomplete gate-fixture failure was corrected in a test-only follow-up commit; the final shared-gate run verifies that correction. Initial uncommitted-source runs also failed the existing committed-source requirement. One attempted invocation named a nonexistent runtime-profile test file and collected no tests; the actual synthetic-profile file was subsequently run. No earlier failure is being represented as a pass.

Review: a separate read-only pass checked the final diff. Exclusive publication, one-shot claims, deadline checks and verification remain enforced. Protected files, both controller manifests and every source named in those manifests are unchanged from the base. No model-facing instruction or prompt was edited. Tests exercise invented data and mocked process/consumer boundaries; this does not authorize or verify a live D117 probe. The genuine consumer and full integration checks need the lead to resolve the scratch-location conflict before claiming a green suite. Recommend an explicitly authorized scratch directory outside the source tree, as the earlier helper context specified; do not relax overlap refusals.

All tracked changes are committed. Test-only follow-up commits preserve the original issue commits without amendment or rebasing. The handoff is written in the assigned report worktree. `.temp/` is untracked in this checkout, despite the assignment describing it as ignored; it contains retained evidence and was not added to Git or deleted.

Helper provenance: [{root / 'scripts/adhoc/fix_g1_probe_review.py'}]({root / 'scripts/adhoc/fix_g1_probe_review.py'}), [{root / 'scripts/adhoc/verify_g1_probe_review.sh'}]({root / 'scripts/adhoc/verify_g1_probe_review.sh'}), [{root / 'scripts/adhoc/write_g1_probe_handoff.py'}]({root / 'scripts/adhoc/write_g1_probe_handoff.py'}). Evidence and computed log digests: [{logs / 'handoff-evidence.json'}]({logs / 'handoff-evidence.json'}).
'''
assert chr(64) not in text
for path in re.findall(r'\]\((/[^)]+)\)', text):
    assert Path(path).is_file(), path
out.write_text(text)
assert out.stat().st_size and out.read_text() == text
print(out)
print('SHA-256:', hashlib.sha256(out.read_bytes()).hexdigest())
