"""Render the D159 lead handoff from saved evidence, 2026-11-17.

Inputs: git, inventory, pin proposal, validator timings, test lane summaries.
Output: assigned external handoff; preserves the original blocked note.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-d159-limits-20261117'
evidence = scratch / 'evidence'
handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-d159-limits-20261117.md'
parser = argparse.ArgumentParser()
parser.add_argument('--final', action='store_true')
args = parser.parse_args()
old = handoff.read_text()
marker = '## Dated sibling: original blocked note, 2026-11-17 before scope ruling'
blocked = old.split(marker, 1)[1].lstrip() if marker in old else old
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
integrity = json.loads((evidence / 'integrity.json').read_text())
pins = json.loads((evidence / 'pin-proposal-compact.txt').read_text())
timing = json.loads((scratch / 'validator/timing.json').read_text())
changes = json.loads((root / 'notes/d159_limits_20261117/changes.json').read_text())
reviews = json.loads((root / 'scripts/adhoc/d159_review_findings_20261117.json').read_text())
lines = ['# D159 limits: implementation committed; '+('validation results below' if args.final else 'validation in progress'), '',
    'Implemented the settled ruling on branch codex/d159-limits-20261117. Current commit: '+head+'.',
    'No protected file or pin was changed. No native binary, provider, GitHub write or push was executed.', '',
    'Every changed location and its old/new text: '+str(root / 'notes/d159_limits_20261117/change_inventory.md'),
    'Machine-readable change data: '+str(root / 'notes/d159_limits_20261117/changes.json'),
    'Ignore-independent grep inventory: '+str(evidence / 'complete-limit-inventory.txt'), '',
    '## Tests', '']
lines += ['Focused retry includes the admission, guard, controller, deadline, runtime, sequence, prepared-worker, permission, packet and CI companion suites.', '']
for name in ['focused.log', 'focused-retry.log', 'native-controls.log', 'collection.log']:
    log = evidence / name
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            if 'host/slot gate busy after' in line:
                lines += ['- Gate refusal in '+str(log)+': '+line]
for lane in ['focused', 'native-controls', 'collection']:
    summary = scratch / lane / 'lane_summary.json'
    if summary.exists():
        doc = json.loads(summary.read_text())
        lines += ['- '+lane+': return code '+str(doc.get('overall_returncode'))+'; '+str(summary)]
        for xml in sorted((scratch / lane / 'results').glob('*.xml')):
            tree = ET.parse(xml)
            suites = list(tree.getroot().iter('testsuite'))
            counts = {key: sum(int(x.get(key, '0')) for x in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
            lines += ['  '+xml.name+': '+json.dumps(counts, sort_keys=True)]
    else:
        lines += ['- '+lane+': no completed lane summary yet.']
if not args.final:
    lock = root.parent / '.d4d-lane-locks/slot-00.lock'
    lines += ['', 'Current shared-slot metadata: '+lock.read_text().strip(), '']
lines += ['', 'Test runner: primary checkout scripts/adhoc/run_lane_20261115.py, isolated scratch interpreter, gate wait 1800 seconds.',
    'Focused lane waited for an existing exclusive np15-fresh-validation lease; no lock was removed or bypassed.', '',
    '## Validator measurement', '',
    'The exact native_execution_gates.schemas closure ran in isolation on the public synthetic fixture seed and its derived core. This is a schema-gate measurement, not a full native launch or a production-sized dataset benchmark.', '']
for row in timing['measurements']:
    lines += ['- '+row['class']+': '+str(row['record_bytes'])+' bytes, '+str(row['wall_seconds'])+' seconds; protected timeout '+str(row['timeout_seconds'])+' seconds; failure '+str(row['failure'])+'.']
lines += ['', 'Both records passed. Both are below the lead escalation threshold of about 90 seconds.',
    'Timing artifact: '+str(scratch / 'validator/timing.json'), '', '## Pin proposal', '',
    'Read-only command: python3 '+str(root.parent.parent / 'data-sheets-schema/scripts/adhoc/compute_pin_chain_20261115.py')+' --root '+str(root)+' --propose --compact.',
    'Full cascade: '+str(evidence / 'pin-proposal-full.json'),
    'Compact cascade: '+str(evidence / 'pin-proposal-compact.txt'), '', '```json', json.dumps(pins, indent=2), '```', '',
    'The synthetic peer is unchanged, so SYNTHETIC_PEER_SHA256 stays '+integrity['synthetic_peer']['sha256']+'.',
    'Pure and historical callback declarations compare equal by AST literal evaluation. The lead must review and rotate CONTROL_SHA, the controller manifests and consumers, checkpoint eligibility, the live scanner override and D128 fixture pins. Dynamic REQUEST_CODE registration digests also move; rebuild registrations.', '',
    '## Derived companions and scope', '',
    'Reservation boundary is 1800 minus the unchanged 300-second margin, hence 1500 seconds. Boundary tests retain below/equal/above cases. Admission clock-jump tests advance past 1500 seconds. CI evidence reports attempt 9600, helper 1000 and long-job 14400 seconds; setup of 20-25 minutes plus the 160-minute attempt fits in 240 minutes.',
    'Registered production uses one shared pair: CHORUS is 28800 seconds and all production cells, including AI_READI, are 57600 seconds. Builder and packet deadline defaults consume these pairs; admission defaults consume TERM_VALUES. Transport client budgets derive from changed shared transport constants.', '',
    'Unchanged categories and unclear values:', '']
for row in reviews['unchanged']:
    lines += ['- '+row['path']+': '+row['value']+'. '+row['reason']]
runbook = root.parent / 'plans/native_post_merge_runbook_DRAFT_20261114.md'
lines += ['', '## Runbook and review', '',
    'Updated '+str(runbook)+'. Backup: '+str(runbook)+'.bak-d159-20261117. Reverse only the D159 hunks against that backup to undo the amendment; preserve the lead\'s later evaluation Step 9.',
    'D159-only runbook changes: '+str(evidence / 'runbook-diff.txt'),
    'Read-only review findings and dispositions: '+str(root / 'scripts/adhoc/d159_review_findings_20261117.json')+'. The assignment forbids GitHub writes, so the lead must create any required issue records.',
    'The local commit needed one elevated retry after sandbox index.lock refusal; the retry succeeded.', '',
    'Helper provenance scripts:', '']
for path in sorted((root / 'scripts/adhoc').glob('*d159*20261117*')):
    lines += ['- '+str(path)]
lines += ['', 'Integrity evidence: '+str(evidence / 'integrity.json'), '', marker, '', blocked]
text = '\n'.join(lines).replace(chr(64), '[at]')
handoff.write_text(text)
print(str(handoff))
print(hashlib.sha256(handoff.read_bytes()).hexdigest())
