"""D59 review tables, 2026-10-28.

Input: measure_bc1_d59_20261028.py JSON. Output: requested Markdown review note.
Test counts are supplied explicitly after serial pytest; no provider/network use.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def number(value):
    return '—' if value is None else f'{value:,}'


def table(lines, headers, rows):
    lines.extend(['', '| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---'] * len(headers)) + '|'])
    lines.extend('| ' + ' | '.join(str(value) for value in row) + ' |' for row in rows)
    lines.append('')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tests', required=True, help='Verbatim final serial pytest result')
    parser.add_argument('--specificity', required=True)
    args = parser.parse_args()
    data = json.loads((ROOT / 'notes/reviews/bc1_d59_measurements_2026-10-28.json').read_bytes())
    chorus = data['CHORUS']
    lines = ['# BC1 D59 implementation and offline fit — 2026-10-28', '',
        'D59 is implemented for the common BC1 path: one full catalog, no per-slot `domain_of`, one bundle, '
        'and v10 A14 downstream. D60 is preserved: no typed-stage cache breakpoint. '
        '**The conservative F5/F7 gate still refuses the CHORUS plan at its existing limits.** '
        'The smaller requests do not make every possible bounded future carry fit; raising only the aggregate cannot fix an oversized call.', '',
        'This is offline implementation and sizing, not an A21 launch or a matrix decision. '
        'The $60 A21 owner decision is recorded here as context; no decision record or campaign budget was changed.', '',
        '## Change and calibration', '',
        '- The model-facing projection verifies the duplicate catalog against the captured catalog, replaces it '
        'with a SHA-256 reference, and references the codec dictionary chunks instead of repeating the bundle. '
        'Full host requests and response identities remain available to validators. Both full and core catalogs '
        'retain their definitions apart from the redundant inverse `domain_of` index.',
        '- `api_runner.build_phase` and `bc1_runtime.require_request` use the existing A14 implementation '
        'for full, receipt completion, reconcile, report and regate. The receipt continuation inherits its full request.',
        '- The registration’s BC1 contract explicitly records the calibration and source. Worker/omission use '
        '**2.48 bytes/token**. Integration uses **1.75**, rounding down the measured minimum 1.755 '
        '(reported as 1.76) to avoid rounding toward underestimation. The requested sensitivity columns use 2.48 and 2.77 for every call. '
        'These are extrapolations from saved usage, not measured BC1 token counts. The historical non-BC1 2.0 constant remains unchanged for byte parity.',
        '- F5 recomputes estimates from wire bytes, rejects inconsistent fit flags, enforces each per-call room '
        'and aggregate for every scenario, and runs before registration outputs are written.',
        '- F7 replaces the 86-byte receipt placeholder with `bc1_audit_carry` of the pinned saved receipt-completion result. '
        'A missing or mismatched result refuses sizing. Use the original intermediate directory containing '
        '`PROJECT_receipt_completion_result.json`, or supply `SizingRecord.receipt_result` in Python.',
        '- F7 retains the ASCII scenario for comparison and adds an escaped-byte bound. Valid JSON text can '
        'occupy four wire bytes per input byte after two string encodings. Backslash filler reaches that bound; '
        'it is explicitly **not a valid model response or token-density calibration**. No output cap is lowered, '
        'and no source material is truncated to force fit.', '',
        '## CHORUS typed calls', '',
        'Inputs are the retained K1v2 original full/core/effective receipt from 10-22a and the original '
        'launch-base receipt-completion result. All input pins are in the JSON companion. '
        'Before is the `8dd00263a` renderer/sizer on the same paths; after is the current pure production renderer. '
        'The baseline uses its original short receipt placeholder. Path lengths differ from the independent report, '
        'so its original byte totals are not substituted for this controlled comparison.', '',
        'F = empty future floor, A = visible caps with ASCII filler, E = conservative escaped cap bound. '
        'Fixed worker/omission rows appear once; each scenario adds its three integration calls. '
        'E did not exist in the old sizer, so its before cells are unmeasured. '
        'The recorded receipt carry is ' + number(chorus['receipt_carry']['bytes']) + ' UTF-8 bytes. '
        'Typed output reservations are 416,000 against the registered 480,000.']
    codes = {'captured_record': 'fixed', 'empty_future_floor': 'F', 'visible_cap_ascii_scenario': 'A', 'visible_cap_escaped_bound': 'E'}
    rows = []
    for row in chorus['typed']:
        stage = row['stage']
        call = stage.get('worker_id', stage.get('stage_id', 'omission'))
        rows.append([call, codes[row['scenario']], number(row['before_bytes']), number(row['wire_bytes']),
            number(row['before_tokens_2.48']), number(row['before_tokens_2.77']), number(row['tokens_2.48']),
            number(row['tokens_2.77']), number(row['estimated_input_tokens']), number(row['room']),
            'yes' if row['estimated_context_fits'] else '**no**'])
    table(lines, ['Call', 'Scenario', 'Before B', 'After B', 'Before /2.48', 'Before /2.77',
                  'After /2.48', 'After /2.77', 'Gate tokens', 'Room', 'Gate fit'], rows)
    table(lines, ['Scenario', 'Calls', 'Wire B', 'Tokens /2.48', 'Tokens /2.77', 'Calibrated tokens', 'Allowance', 'All calls fit'],
        [[codes[name], row['calls'], number(row['wire_bytes']), number(row['tokens_2.48']), number(row['tokens_2.77']),
          number(row['estimated_input_tokens']), number(chorus['allowance']), row['estimated_all_calls_fit']]
         for name, row in chorus['totals'].items()])
    table(lines, ['Before aggregate', 'Wire B', 'Tokens /2.48', 'Tokens /2.77', 'Allowance'],
        [[codes[scenario], *[number(sum(row[key] for row in chorus['typed']
            if row['scenario'] in ('captured_record', scenario)))
            for key in ('before_bytes', 'before_tokens_2.48', 'before_tokens_2.77')], number(chorus['allowance'])]
         for scenario in ('empty_future_floor', 'visible_cap_ascii_scenario')])
    lines.extend(['Gate diagnostic: `' + chorus['gate'] + '`.', '', '## CHORUS downstream calls', '',
        'Exact serialized bodies for stated historical-input scenarios. The future BC1 audit carry is unknown; '
        'F/A/E respectively supply zero bytes, 262,144 ASCII bytes, or 262,144 maximally escaping bytes. '
        'Full and receipt rows repeat because they do not depend on that audit carry. Receipt completion uses '
        'the saved 10-22a assistant response and continuation inventory after the newly rendered full message. '
        'Report-regate uses the saved report and an empty contradiction list; 10-22a has no saved regate body. '
        'These are reproducible rendered scenarios, not claims to know ungenerated live requests.'])
    table(lines, ['Phase', 'Scenario', 'Before B', 'After B', 'Before /2.48', 'Before /2.77', 'After /2.48', 'After /2.77', 'Room', 'Fit /2.48'],
        [[r['phase'], codes[r['scenario']], number(r['before']['wire_bytes']), number(r['after']['wire_bytes']),
          number(r['before']['tokens_2.48']), number(r['before']['tokens_2.77']), number(r['after']['tokens_2.48']),
          number(r['after']['tokens_2.77']), number(r['after']['room']), r['after']['fits_2.48']]
         for r in chorus['downstream']])
    lines.extend(['The 4M allowance covers the typed roster only. Downstream phases have separate parent limits; '
                  'they are not charged to the typed aggregate.', '', '## Other projects with their own records', '',
        'The production preparation refusals are preserved. Estimates use the report’s component-substitution '
        'method: current measured CHORUS envelope plus each project’s own bundle, original full/core, receipt, '
        'manifest, context and production-planned inventory, with the actual JSON nesting multiplicity. '
        'Workers use the largest CHORUS assignment tail; small project-specific owner, dictionary and identity '
        'differences are not exact. Receipt carry is explicitly the CHORUS proxy because no corresponding '
        'v8 receipt-completion result is available in these selected records. A filename search of the three '
        'selected `source_records` directories included hidden and gitignored files. '
        'No figure below is a launchable allowance.'])
    for project, item in data['other_projects'].items():
        lines.extend([f'### {project}', '', 'Production refusal: `' + str(item['production_refusal']) + '`.', '', item['basis']])
        # Compact only identical estimates; JSON retains the fully enumerated roster.
        groups = {}
        for row in item['rows']:
            key = tuple(row[k] for k in ('scenario', 'wire_bytes', 'tokens_2.48', 'tokens_2.77', 'calibrated_tokens', 'room'))
            groups.setdefault(key, []).append(row['call'])
        table(lines, ['Calls (each)', 'Scenario', 'Estimated B', '/2.48', '/2.77', 'Gate tokens', 'Room', 'Gate fit'],
            [[(', '.join(names) if len(names) < 3 else names[0] + ' … ' + names[-1] + f' ({len(names)} calls)'),
              codes[key[0]], *[number(x) for x in key[1:]], key[4] <= key[5]] for key, names in groups.items()])
        table(lines, ['Scenario', 'Aggregate /2.48', 'Aggregate /2.77', 'Required calibrated allowance', 'Profile comparison'],
            [[codes[name], number(row['tokens_2.48']), number(row['tokens_2.77']), number(row['calibrated_tokens']), '4,000,000']
             for name, row in item['totals'].items()])
        if 'downstream' in item:
            lines.extend(['', item['downstream_basis']])
            table(lines, ['Downstream phase', 'Scenario', 'Estimated B', '/2.48', '/2.77', 'Room', 'Fit /2.48'],
                [[r['phase'], codes[r['scenario']], number(r['wire_bytes']), number(r['tokens_2.48']),
                  number(r['tokens_2.77']), number(r['room']), r['fits_2.48']] for r in item['downstream']])
    table(lines, ['Project', 'Registered typed allowance', 'Required F', 'Required A', 'Required E'],
        [['CHORUS', number(chorus['allowance']), *[number(chorus['totals'][key]['estimated_input_tokens']) for key in codes if key != 'captured_record']]] +
        [[project, 'none (4M profile comparison)', *[number(item['totals'][key]['calibrated_tokens']) for key in codes if key != 'captured_record']]
         for project, item in data['other_projects'].items()])
    lines.extend(['These aggregate requirements do not waive per-call failures. VOICE_PEDIATRIC and KIDS_FIRST '
                  'are excluded from own-record estimates: the report’s selected K1v2 records for them are VOICE '
                  'and AI_READI proxies, respectively.', '', '## Non-BC1 byte parity and protected source', '',
        'Compared the actual canonical CHORUS registration output and all rendered shared-generation v1 '
        'request bodies against functions compiled directly from git `8dd00263a`, with identical input paths '
        'and substitutions. No BC1 flag is present in the parent registration. Legacy integration reuses the '
        'saved 10-22a inner request (no invented worker judgments); its production outer renderer is unchanged. '
        'No before/after path or digest normalization is applied.', '',
        f"Registration: **{data['registration_parity']['bytes']:,} bytes**, SHA-256 `{data['registration_parity']['sha256']}`, byte-identical."])
    table(lines, ['Request', 'Bytes (before = after)', 'SHA-256 (before = after)'],
        [[phase, number(row['wire_bytes']), '`' + row['sha256'] + '`'] for phase, row in data['non_bc1_request_parity'].items()])
    lines.extend(['`shared_generation.py` is unchanged: SHA-256 `' + data['protected_shared_generation_sha256'] + '`. '
        'No protected-file proposal is needed and its source pin does **not** need re-pinning. '
        'BC1 registrations must be rebuilt because the BC1 code/contract pins changed.', '',
        '## Validation and provenance', '', args.tests, '', args.specificity, '',
        'Tests ran serially with the requested interpreter, credentials unset, bytecode disabled, no pytest cache, '
        'and `--basetemp="$TMPDIR/codex-bc1-pt"`. No provider calls, `count_tokens`, network, `gh`, or push were used. '
        'Source run files were read only and checked against their recorded hashes after measurement. '
        'No STATUS, decision records, canonical_hashes.yaml, run directory, or ATTIC file was edited.', '',
        'Reproduce the measurements with:', '', '```sh',
        'env -u ANTHROPIC_API_KEY -u CBORG_API_KEY -u OPENAI_API_KEY PYTHONDONTWRITEBYTECODE=1 \\',
        '  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -B \\',
        '  scripts/adhoc/measure_bc1_d59_20261028.py', '```', '',
        'Helpers are retained in `scripts/adhoc/measure_bc1_d59_20261028.py`, '
        '`scripts/adhoc/report_bc1_d59_20261028.py` and '
        '`scripts/adhoc/bc1_d59_baseline_controls_20261028.py`. The JSON companion contains complete per-call estimates '
        'and input hashes. Historical inputs must remain at the documented paths; there is no network fallback.', '',
        'Outstanding: actual BC1 token counts and future response sizes require an authorized live canary. '
        'The current 4M CHORUS plan is refused offline; no canary, budget change or matrix launch was attempted. '
        'Other-project receipt identity/cardinality refusals remain explicit and their allowances are estimates.'])
    (ROOT / 'notes/reviews/bc1_d59_fix_2026-10-28.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
