#!/usr/bin/env python3
"""PR #5212/D55, 2026-10-28: summarize and pin serial offline acceptance evidence.

Inputs: external pytest XML/logs, retained parity capture, D42 outcomes. Output:
repository JSON report with counts, exact F2 results, eight verified request
body hashes, source pins and external artifact hashes. No evidence is deleted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=Path('/private/tmp/codex-5212-evidence'))
    args = parser.parse_args()
    batches = {}
    for path in sorted(args.evidence.rglob('*.xml')):
        root = ET.parse(path).getroot()
        cases = root.findall('.//testcase')
        failed = [c for c in cases if c.find('failure') is not None or c.find('error') is not None]
        skipped = [c for c in cases if c.find('skipped') is not None]
        batches[str(path.relative_to(args.evidence))] = {**pin(path), 'tests': len(cases),
            'passed': len(cases) - len(failed) - len(skipped), 'failed': len(failed), 'skipped': len(skipped),
            'failures': [c.attrib for c in failed]}
    f2 = (ROOT / 'notes/reviews/pr5212_d55_f2_nodes.txt').read_text().splitlines()
    required = ET.parse(args.evidence / 'required/results.xml').findall('.//testcase')
    before = ET.parse(args.evidence / 'before/results.xml').findall('.//testcase')
    def matches(node, case):
        file, name = node.split('::', 1)
        return case.get('classname') == file[:-3].replace('/', '.') and case.get('name') == name
    f2_results = []
    for node in f2:
        cases = [c for c in required if matches(node, c)]
        assert len(cases) == 1, node
        case = cases[0]
        original = [c for c in before if matches(node, c)]
        assert len(original) == 1 and original[0].find('failure') is not None, node
        f2_results.append({'node': node, 'before': 'failed', 'passed': case.find('failure') is None and case.find('error') is None
                           and case.find('skipped') is None})
    parity_dir = args.evidence / 'final-parity'
    summary = json.loads((parity_dir / 'summary.json').read_bytes())
    bodies = {}
    for name, row in summary['rows'].items():
        paths = {side: parity_dir / row[side]['path'].split('/parity/', 1)[1]
                 for side in ('baseline', 'candidate')}
        assert paths['baseline'].read_bytes() == paths['candidate'].read_bytes()
        assert hashlib.sha256(paths['candidate'].read_bytes()).hexdigest() == row['sha256']
        bodies[name] = {'bytes': row['bytes'], 'sha256': row['sha256'], 'identical': True}
    assert len(bodies) == 8
    artifacts = []
    archive = ROOT / 'notes/reviews/pr5212_d55_evidence_2026-10-28'
    for path in sorted(args.evidence.rglob('*')):
        if not path.is_file() or not (path.suffix in {'.log', '.xml', '.jsonl'}
                                     or path.name in {'production_sources.json', 'summary.json', 'capture.json',
                                                      'selection.txt', 'command.txt'}):
            continue
        destination = archive / path.relative_to(args.evidence)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != path.read_bytes():
            raise ValueError('refusing to overwrite different retained evidence: ' + str(destination))
        shutil.copy2(path, destination)
        artifacts.append({**pin(path), 'archive': str(destination.relative_to(ROOT))})
    sources = [pin(ROOT / p) for p in (
        'src/data_sheets_schema/latch_journal.py', 'src/data_sheets_schema/api_runner.py',
        'src/data_sheets_schema/source_heading_admission.py', 'src/data_sheets_schema/cli/api.py',
        'src/data_sheets_schema/shared_generation.py')]
    runtime_pins = json.loads((args.evidence / 'runtime/production_sources.json').read_bytes())
    for source in sources:
        relative = str(Path(source['path']).relative_to(ROOT))
        assert source['sha256'] == runtime_pins[relative], relative
    outcomes = args.evidence / 'tamper.jsonl'
    tamper = [json.loads(line) for line in outcomes.read_text().splitlines()]
    refusals = [row for row in tamper if row.get('outcome') == 'refused']
    assert len(tamper) == 23 and len(refusals) == 16
    assert all(row['dispatches'] == 0 and row.get('counts', 0) == 0 for row in refusals)
    result = {'base': 'db88ca68c1443a91e9264cbc632a8639376e99bc',
              'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
              'batches': batches, 'f2': f2_results, 'chorus_shared_v1': {
                  'baseline_commit': summary['baseline']['commit'], 'bodies': bodies,
                  'summary': pin(parity_dir / 'summary.json')},
              'tamper': tamper,
              'tamper_refusals': {'cases': len(refusals), 'dispatches': 0,
                                  'cases_measuring_token_counts': sum('counts' in row for row in refusals),
                                  'measured_token_counts': 0},
              'production_sources': sources, 'artifacts': artifacts,
              'scope': 'Serial selected offline tests; overlapping batches, not a full-suite or CI claim.'}
    out = ROOT / 'notes/reviews/pr5212_d55_evidence_2026-10-28.json'
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'batches': {k: {field: v[field] for field in ('passed', 'failed', 'skipped')}
                                for k, v in batches.items()},
                      'f2_passed': sum(r['passed'] for r in f2_results), 'parity_bodies': len(bodies),
                      'parity_baseline': summary['baseline']['commit'], 'body_pins': bodies,
                      'report': str(out)}, indent=2))


if __name__ == '__main__':
    main()
