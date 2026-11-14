#!/usr/bin/env python3
"""Add the lead-requested G3b comparison to H2 handoff, 2026-11-13.
Inputs: report source and saved binding review/comparison. Outputs: source edit,
historical source snapshot in scratch. Issue 6200; no tests or runtime calls.
"""
import json
import report_h2_resume_20261113 as report
from pathlib import Path


def main():
    path = Path(report.__file__)
    raw = path.read_text()
    review = report.read_json(report.SCRATCH / 'public-isolation-binding-review.json')
    assert report.sha(raw.encode()) == review['producer']['sha256']
    snapshot = report.SCRATCH / 'isolation-binding-reviewed-report-source.txt'
    with snapshot.open('x') as stream:
        stream.write(raw)
    assert report.pin(snapshot)['sha256'] == review['producer']['sha256']
    needle = "    static_diagnosis = read_json(static_diagnosis_path)"
    assert needle in raw and "g3b_path =" not in raw
    raw = raw.replace(needle, needle + "\n    g3b_path = SCRATCH / 'g3b-hang-comparison.json'\n    g3b = read_json(g3b_path)\n    binding_source = pin(SCRATCH / 'isolation-binding-reviewed-report-source.txt')\n    assert binding_source['sha256'] == isolation_binding['producer']['sha256']", 1)
    needle = "        'callback_static_diagnosis_evidence': pin(static_diagnosis_path),"
    assert needle in raw
    raw = raw.replace(needle, needle + "\n        'g3b_comparison': g3b, 'g3b_comparison_evidence': pin(g3b_path),\n        'isolation_binding_reviewed_report_source': binding_source,", 1)
    needle = "    lines += ['', 'Static callback-path diagnosis: `' + str(static_diagnosis_path) + '`.']"
    assert needle in raw
    raw = raw.replace(needle, needle + '''
    lines += ['', 'Lead G3b hang question: ' + g3b['answer'],
        'Completed denial-case stops: ' + '; '.join(row['first_stop'] for row in g3b['completed_cases']) + '.',
        g3b['interpretation'],
        'Evidence: `' + str(g3b_path) + '`. The inventory includes ignored and hidden files; directory aliases are not followed.',
        'The report source reviewed for H2-RESUME-REPORT-F2 is retained at `' + binding_source['path'] + '`; its hash matches the review record.']''', 1)
    path.write_text(raw)
    print(json.dumps({'snapshot': report.pin(snapshot), 'updated_report': report.pin(path)}))


if __name__ == '__main__':
    main()
