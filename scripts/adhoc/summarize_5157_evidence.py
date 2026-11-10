"""Summarize #5157 offline pytest evidence, 2026-11-08.

Inputs: named runs under scratch-codex-5157, oldest first. Outputs: JSON
summary there and stdout; later results replace earlier cases by test identity.
"""
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

SCRATCH = Path(
    os.environ.get(
        'D4D_5157_SCRATCH',
        Path(__file__).resolve().parents[3] / 'scratch-codex-5157',
    )
)


def main(argv=None, scratch=None):
    base = Path(scratch) if scratch is not None else SCRATCH
    args = sys.argv[1:] if argv is None else list(argv)
    cases, runs = {}, []
    for name in args:
        if Path(name).name != name:
            raise SystemExit('Expected a run directory name, not a path')
        directory = base / name
        missing = [
            fname for fname in ('outcome.json', 'pytest.xml')
            if not (directory / fname).exists()
        ]
        if missing:
            runs.append({
                'name': name,
                'status': 'interrupted',
                'missing': missing,
                'tests': 0,
            })
            continue
        outcome = json.loads((directory / 'outcome.json').read_text())
        root = ET.parse(directory / 'pytest.xml').getroot()
        rows = []
        for case in root.iter('testcase'):
            problem = next((child for child in case
                            if child.tag in {'failure', 'error', 'skipped'}), None)
            row = {'id': case.attrib['classname'] + '::' + case.attrib['name'],
                   'status': problem.tag if problem is not None else 'passed',
                   'run': name}
            if problem is not None:
                row['detail'] = problem.text or problem.get('message', '')
            rows.append(row)
            cases[row['id']] = row
        runs.append({'name': name, **outcome, 'tests': len(rows)})
    counts = {status: sum(row['status'] == status for row in cases.values())
              for status in ('passed', 'failure', 'error', 'skipped')}
    result = {'runs': runs, 'latest_distinct_counts': counts,
              'cases': list(cases.values())}
    (base / 'validation-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'runs': runs, 'latest_distinct_counts': counts}, indent=2))
    return result


if __name__ == '__main__':
    main()
