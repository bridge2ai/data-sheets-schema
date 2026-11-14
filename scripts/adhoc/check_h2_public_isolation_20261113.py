#!/usr/bin/env python3
"""Record and close H2-RESUME-ISOLATION-F1 for issue 6200, 2026-11-13.
Inputs: saved JUnit session intervals and recorded cohort commands/outcomes.
Outputs: scratch isolation review. No tests or process control; original
failed evidence remains untouched. Intervals use same-host local JUnit clocks.
"""
import argparse
from datetime import datetime, timedelta
import json
import xml.etree.ElementTree as ET
import report_h2_resume_20261113 as report

DEST = report.SCRATCH / 'public-isolation-review.json'


def interval(path):
    suite, = list(ET.parse(path).iter('testsuite'))
    start = datetime.fromisoformat(suite.attrib['timestamp'])
    end = start + timedelta(seconds=float(suite.attrib['time']))
    return {'evidence': report.pin(path), 'hostname': suite.attrib['hostname'],
            'start': start.isoformat(), 'estimated_end': end.isoformat(),
            'reported_seconds': suite.attrib['time']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('record', 'verify'))
    args = parser.parse_args()
    if args.phase == 'record':
        preload = interval(report.SCRATCH / 'preload.xml')
        correction = interval(report.SCRATCH / 'correction/pytest.xml')
        assert preload['hostname'] == correction['hostname']
        begin = max(datetime.fromisoformat(row['start']) for row in (preload, correction))
        end = min(datetime.fromisoformat(row['estimated_end']) for row in (preload, correction))
        overlap = max(0, (end - begin).total_seconds())
        assert overlap > 0
        value = {'finding_id': 'H2-RESUME-ISOLATION-F1', 'status': 'rerun-required',
            'finding': 'The initial correction fixture setup overlapped the preload session, so that invocation does not establish exclusive execution within this assignment.',
            'interval_basis': 'Same-host local JUnit timestamps plus reported session durations; estimated intervals, not CPU measurements.',
            'original_intervals': {'preload': preload, 'correction': correction},
            'estimated_overlap_seconds': overlap,
            'required_rerun_cohort': 'correction-isolated',
            'causal_limit': 'No public failure or duration is attributed to this overlap.',
            'lead_filing_needed': True, 'github_issue_number': None,
            'filing_reason': 'Helper GitHub writes are prohibited; the lead must file this review finding.'}
        with DEST.open('x') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
    else:
        value = report.read_json(DEST)
        assert value['status'] == 'rerun-required'
        directory = report.SCRATCH / value['required_rerun_cohort']
        latest = report.load_cohort(directory)
        assert latest['complete'] and latest['counts']['total'] == 1
        current = interval(directory / 'pytest.xml')
        cohorts = [report.load_cohort(path) for path in sorted(report.SCRATCH.iterdir())
                   if path.is_dir() and (path / 'command.json').is_file()]
        cohorts.append(report.load_cohort(report.SCRATCH, preload=True))
        earlier = []
        for row in cohorts:
            if row['name'] == latest['name']:
                continue
            assert row['complete'], row['name']
            saved = interval(report.SCRATCH / 'preload.xml' if row['name'] == 'preload'
                             else report.SCRATCH / row['name'] / 'pytest.xml')
            assert saved['hostname'] == current['hostname']
            assert datetime.fromisoformat(saved['estimated_end']) <= datetime.fromisoformat(current['start']), row['name']
            earlier.append({'cohort': row['name'], **saved})
        proof = report.public_proof(cohorts, 'correction', report.PUBLIC['correction'])
        assert proof['cohort'] == latest['name'] and proof['isolated_command']
        assert 'correction' in proof['earlier_invocations']
        before = report.SCRATCH / 'public-isolation-review-before-rerun.json'
        with before.open('xb') as stream:
            stream.write(DEST.read_bytes())
        value.update(status='corrected-by-serial-rerun', rerun_interval=current,
            earlier_completed_cohorts=earlier, rerun_outcome=latest['outcome'],
            rerun_counts=latest['counts'], selected_public_proof=proof,
            prior_review=report.pin(before),
            scope='All recorded test cohorts in this assignment ended before the correction rerun started; unrelated host work is not certified.')
        DEST.write_text((json.dumps(value, indent=2) + '\n').replace(chr(64), '\\u0040'))
    print(json.dumps(report.pin(DEST)))


if __name__ == '__main__':
    main()
