#!/usr/bin/env python3
"""U3-M fixed-main scanner comparison, 2026-11-09.

Inputs: two completed full scan runs and unchanged D128 reference evidence.
Outputs: fresh full-array JSON and itemized Markdown below u3m. The new API
packet is proposed only. This never rewrites the frozen baseline or approval.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3m_l_comparator', ROOT / 'scripts/adhoc/compare_native_u3l_20261109.py')
l = importlib.util.module_from_spec(spec)
spec.loader.exec_module(l)
MAIN = '2cfc4666c2d81003d9cf5f432248b4217ef477e1'
OUT = l.SCRATCH / 'u3m'
POST = dict(l.D127, **{'src/data_sheets_schema/api_runner.py':
    '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    h, reader = l.reader()
    h.quiet()
    l.need(a.out.is_absolute() and a.out.parent == OUT and OUT.resolve(strict=True) == OUT
           and a.out.suffix == '.json' and not os.path.lexists(a.out)
           and not os.path.lexists(a.out.with_suffix('.md')), 'fresh physical M output required')
    approved, frozen = l.frozen_approval()
    baseline = l.read_run(h, 'fixed_main', a.baseline, source=MAIN)
    candidate = l.read_run(h, 'merged_candidate', a.candidate, tool=baseline['tool_commit'])
    l.need(l.same(baseline['tool_assets_sha256'], candidate['tool_assets_sha256']), 'instrument differs')
    for row in (baseline, candidate):
        l.need(l.same(row['source']['physical_input_mask'], approved['baseline']['physical_input_mask']),
               'physical input scope differs')
    root = Path(candidate['source_root'])
    l.need({path: l.sha((root / path).read_bytes()) for path in POST} == POST, 'proposed composition differs')
    gate = h.git('show', l.OLD_TOOL + ':' + l.GATE)
    l.need((ROOT / l.GATE).read_bytes() == gate and (root / l.GATE).read_bytes() == gate,
           'frozen D128 test changed')
    comparisons = [l.compare(label, left['arrays'], right['arrays']) for label, left, right in (
        ('fixed_main_vs_merged_candidate', baseline, candidate),
        ('frozen_approved_main_vs_fixed_main', frozen['baseline'], baseline),
        ('frozen_approved_candidate_vs_merged_candidate', frozen['reference_candidate'], candidate))]
    assets = l.asset_delta(approved['tool_assets_sha256'], baseline['tool_assets_sha256'])
    value = dict(kind='native_u3m_full_scanner_comparison', version=1,
        helper_sha256=l.sha(Path(__file__).read_bytes()), retained_reader=reader,
        array_comparator_sha256=l.sha(Path(l.__file__).read_bytes()),
        baseline=baseline, candidate=candidate, frozen_inputs=frozen,
        frozen_approval=approved, comparisons=comparisons, tool_asset_delta=assets,
        fixed_main=MAIN, frozen_baseline=l.MAIN,
        frozen_reference_candidate=l.REFERENCE, proposed_postimages_sha256=POST,
        proposed_api_owner_approval='pending_not_covered_by_D127',
        d128_gate_passed=False, instrument_approval_changed=False,
        reference_arrays_match=all(row['exact_arrays_equal'] for row in comparisons[1:]),
        scope='Diagnostic only: full ordered objects, duplicate occurrences and positional changes retained; no approval expansion.')
    l.frozen_approval()
    for label, path, old in (('fixed_main', a.baseline, baseline), ('merged_candidate', a.candidate, candidate)):
        l.need(l.same(l.read_run(h, label, path, source=old['source']['commit'], tool=old['tool_commit']), old),
               'retained scan evidence changed during comparison')
    h.quiet()
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with a.out.open('xb') as stream:
        stream.write(raw)
    l.need(a.out.read_bytes() == raw, 'full comparison did not persist')
    lines = ['# U3-M full scanner comparison', '', 'Diagnostic only; frozen D128 is unchanged and not passed.', '',
             'Full objects and ordered arrays: `' + str(a.out) + '`.', '',
             'New API postimage owner approval remains pending.', '']
    for i, comparison in enumerate(comparisons):
        lines.extend(['## ' + comparison['label'], ''])
        for name, ledger in comparison['arrays'].items():
            lines.append(f"- {name}: {ledger['before_count']} → {ledger['after_count']}; exact={ledger['exact_match_count']}; "
                         f"line-only={len(ledger['relocations'])}; fields={len(ledger['changed_fields'])}; "
                         f"added={len(ledger['added'])}; removed={len(ledger['removed'])}; "
                         f"ordered equality={ledger['exact_arrays_equal']}.")
            for kind in ('relocations', 'changed_fields', 'added', 'removed'):
                for j, row in enumerate(ledger[kind]):
                    old, new = row.get('before', {}), row.get('after', {})
                    pointer = f'/comparisons/{i}/arrays/{name}/{kind}/{j}'
                    lines.append(f"  - {kind}: before[{row.get('before_index')}] {old.get('path')}:{old.get('line')} "
                                 f"→ after[{row.get('after_index')}] {new.get('path')}:{new.get('line')}; "
                                 f"fields={row.get('differing_fields')}; full objects `{pointer}`.")
            lines.append(f"  - All {len(ledger['positional_differences'])} position differences: "
                         f"`/comparisons/{i}/arrays/{name}/positional_differences` (not additional object counts).")
        lines.append('')
    lines.extend(['## Scanner asset differences', ''])
    lines.extend('- `' + row['path'] + '`: `' + row.get('before_sha256', 'absent')
                 + '` → `' + row.get('after_sha256', 'absent') + '`.' for row in assets)
    rendered = ('\n'.join(lines) + '\n').encode()
    with a.out.with_suffix('.md').open('xb') as stream:
        stream.write(rendered)
    l.need(a.out.with_suffix('.md').read_bytes() == rendered, 'itemized index did not persist')
    print(json.dumps(dict(path=str(a.out), bytes=len(raw), sha256=l.sha(raw),
        reference_arrays_match=value['reference_arrays_match'], d128_gate_passed=False,
        markdown_sha256=l.sha(rendered))))


if __name__ == '__main__':
    main()
