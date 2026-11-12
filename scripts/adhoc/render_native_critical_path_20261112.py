#!/usr/bin/env python3
"""Render the D134 native canary critical-path report, 2026-11-12.

Input: handoffs/codex-native-critical-path-20261112.json (source-reviewed gate ledger).
Output: sibling Markdown report, with every table generated from that JSON.
No production imports, tests, source edits, network, native or provider calls.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / 'notes/development_efficiency_20261111/handoffs'
INPUT = HANDOFF / 'codex-native-critical-path-20261112.json'
OUTPUT = HANDOFF / 'codex-native-critical-path-20261112.md'


def cell(value):
    if isinstance(value, list):
        value = '; '.join(str(item) for item in value) if value else 'none'
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def table(rows, columns):
    result = ['| ' + ' | '.join(label for _, label in columns) + ' |',
              '| ' + ' | '.join('---' for _ in columns) + ' |']
    for row in rows:
        result.append('| ' + ' | '.join(cell(row.get(key, '')) for key, _ in columns) + ' |')
    return '\n'.join(result)


def render(data):
    gates = data['gates']
    by_id = {row['id']: row for row in gates}
    assert len(by_id) == len(gates)
    required = {'id', 'gate', 'required_by', 'state', 'remains', 'who', 'effort_hours', 'depends_on'}
    finished = set()
    for row in gates:
        assert required <= row.keys()
        assert row['state'] in {'done', 'partial', 'not_started'}
        assert row['who'] in {'worker', 'lead', 'owner'}
        assert len(row['effort_hours']) == 2 and 0 <= row['effort_hours'][0] <= row['effort_hours'][1]
        assert set(row['depends_on']) <= finished, 'Gate list must be in dependency order'
        assert set(row.get('parallel_with', [])) <= by_id.keys()
        finished.add(row['id'])
    out = ['# Native first-canary critical path — 2026-11-12', '', data['answer'], '']
    out += data['scope'] + ['']
    out += ['**Dependency-ordered gates**', '', data['effort_basis'], '']
    display = [dict(row, effort=f"{row['effort_hours'][0]}–{row['effort_hours'][1]}") for row in gates]
    out += [table(display, [('id','ID'),('gate','Gate'),('state','State'),('who','Who'),
                            ('effort','Hours'),('depends_on','Depends on'),('parallel_with','Can run in parallel with')]), '']
    out += [table(gates, [('id','ID'),('required_by','Required by'),('evidence','Evidence / state basis'),('remains','Concrete remaining work')]), '']
    for section in data['sections']:
        out += ['**' + section['title'] + '**', '']
        out += section.get('paragraphs', []) + ['']
        if 'rows' in section:
            out += [table(section['rows'], [(col['key'], col['label']) for col in section['columns']]), '']
        if 'commands' in section:
            out += ['```sh', '\n'.join(section['commands']), '```', '']
        out += section.get('after', []) + ['']
    out += ['**Provenance and reproduction**', '',
            'The JSON is the gate ledger and the source of every table above. The helper validates gate fields, dependency order and the no-at-sign constraint; it runs no repository production code.', '',
            '```sh', 'env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \\',
            '  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \\',
            '  scripts/adhoc/render_native_critical_path_20261112.py', '```', '',
            'Helper: `scripts/adhoc/render_native_critical_path_20261112.py`.',
            'Only the requested JSON, Markdown and this helper were written. No run, test, source edit, configuration change, provider/native call, GitHub action or STATUS edit was performed; launch-a21 was not accessed.', '']
    return '\n'.join(out)


def main():
    raw = INPUT.read_bytes()
    assert chr(64) not in raw.decode(), 'At-sign forbidden in deliverable'
    data = json.loads(raw)
    report = render(data)
    assert chr(64) not in report, 'At-sign forbidden in deliverable'
    OUTPUT.write_text(report)
    assert OUTPUT.stat().st_size > 0 and OUTPUT.read_text() == report
    for path in (INPUT, OUTPUT):
        print(str(path))
        print(hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
