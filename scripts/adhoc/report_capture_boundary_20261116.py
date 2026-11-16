"""Report D156 boundary work for the Claude lead, 2026-11-16.

Inputs: committed worktree, saved lane summaries and pin proposal in scratch.
Output: prepended handoff section; preserves the earlier protocol report.
Serves D156 and issues 6191 and 6207. No GitHub or runtime calls.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-capture-order-20261116'
HANDOFF = (ROOT.parent / 'codex-development-efficiency-20261111/notes/'
           'development_efficiency_20261111/handoffs/codex-capture-order-20261116.md')
TITLE = '# D156 continuation: dispatch boundary implemented; preparation ordering remains incomplete'


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    lines = [TITLE, '',
        'D156 is accepted as settled. The final dispatch freshness/reset check is implemented '
        'and committed. The preparation-before-capture change is not implemented, so this '
        'is not a completed Step 2 handoff and must not be used as launch readiness evidence.', '',
        'Current branch head: ' + head + '.', '',
        'The boundary change applies the existing reviewed proposal to the guard, execution '
        'engine and transport. It rechecks immutable in-memory authority and the current '
        'clock after activation, power probing, evidence writes and admission alarm teardown. '
        'It refuses stale observations, reset windows, backward clocks, changed authority '
        'and repeated boundary attempts. A successful check updates the saved snapshot '
        'dispatch timestamp; a refusal retains the consumed marker and earlier timestamp. '
        'The transport checks its admission deadline before Popen. This narrows the parent-side '
        'boundary; clock checking and process creation are still separate operations.', '',
        'Reservation determination: moving all controller activation ahead of capture would '
        'change protected reservation behavior. In native_shared_capture_orchestration.py, '
        'activate_admitted calls _activate_bound, which requires the actual reserved '
        'registration.json and started.json and creates execution_capture, started_capture, '
        'the genesis record and journal with one-use writes. Those effects must remain after '
        'guard consumption. This patch leaves them there.', '',
        'Remaining architecture question sent to the lead: the current sequence starts '
        'capture, guard and launch in separate processes. Retaining prepared controller '
        'state requires either one process with fresh rechecks or a prepared launch worker '
        'that preserves process isolation. No cached-verdict file was introduced. The '
        'helper-context instruction says, "If a task needs a design decision, stop there '
        'and report the choice with your recommendation." This is an implementation '
        'architecture question, not a request to revisit D156. Recommend preserving the '
        'existing process isolation with a prepared worker, with explicit one-use IPC and '
        'cleanup tests, if isolation remains part of the lead\'s required contract.', '',
        'Still required: preparation lifecycle and production sequence integration; matching '
        'synthetic fixture ordering; light fresh post-capture rechecks; capture-after-verification '
        'regression; complete requested regression suites; and the public correction measurement.', '',
        'Validation evidence', '']
    summaries = sorted(SCRATCH.glob('boundary-*-summary.json'))
    if not summaries:
        lines.append('No completed lane summary is available. The offline unit invocation '
                     'waited behind the shared host load gate; no passing test count is claimed.')
    for path in summaries:
        data = json.loads(path.read_text())
        lines.extend([str(path), '```json', json.dumps(data, indent=2), '```'])
    for path in sorted(SCRATCH.glob('boundary-unit-retry.log')):
        lines.extend([str(path), '```text', path.read_text().strip(), '```'])
    for path in sorted(SCRATCH.glob('boundary-*/**/*.xml')):
        tree = ET.parse(path).getroot()
        suites = [tree] if tree.tag == 'testsuite' else list(tree.findall('testsuite'))
        totals = {key: sum(int(s.get(key, 0)) for s in suites)
                  for key in ('tests', 'failures', 'errors', 'skipped')}
        lines.append(str(path) + ': ' + json.dumps(totals, sort_keys=True))
    pins = SCRATCH / 'boundary-pins.json'
    assert pins.is_file() and pins.stat().st_size
    lines.extend(['', 'Pin proposal: ' + str(pins) + '.',
        'Computed with the primary checkout\'s scripts/adhoc/compute_pin_chain_20261115.py '
        '--root set to this worktree, --propose --compact. No pin was edited. The report '
        'confirms protected_files_ok and identifies controller manifests, manifest consumers '
        'and scanner pin updates for lead integration.', '',
        'Capture-to-dispatch and final-callback observer/callback times are unavailable: '
        'the public correction case has not been run. No native binary or provider was invoked.', '',
        'Read-only review: inspected the committed guard, engine and transport diff separately '
        'from implementation. The unresolved preparation process boundary and unintegrated '
        'pin cascade remain findings for the lead ledger. No GitHub write was made; both '
        'requested GitHub issue reads failed because the API was unreachable. No push or PR '
        'was attempted, as this helper assignment forbids them.', '',
        'Helpers committed on this branch: scripts/adhoc/apply_capture_boundary_20261116.py '
        'and scripts/adhoc/report_capture_boundary_20261116.py. The application helper reuses '
        'the existing proposal generators and checks AST shape and preserved publication '
        'behavior before writing; the report helper creates this section from saved evidence.', '',
        '---', ''])
    prior = HANDOFF.read_text()
    old_title = '# Step 1 stop: ratified capture order requires an owner decision'
    prior = prior[prior.index(old_title):]
    text = '\n'.join(lines) + prior
    assert chr(64) not in text
    HANDOFF.write_text(text)
    assert HANDOFF.read_text() == text
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
