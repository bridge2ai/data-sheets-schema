#!/usr/bin/env python3
# Purpose: compare complete installed-D38 and retained 01969 N2 render evidence.
# Inputs: exact two render reports/artifacts and pinned structural parser.
# Outputs: lossless text diffs and all structured changes for independent review.
# Refs #4354, #5170; 2026-10-27. Offline, read-only inputs; never executes commands.
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
PARSER = 'scripts/adhoc/native_n2_review_parity_deltas_20261025.py'
PARSER_SHA = 'f021e5bcdac5c400d1c51135926eec285382020705e95787dc1defa76a5eda45'
REPORTS = {
    'before': '4860510d6dc18f112e09309c1d065059aa295c58f39c91681007d28b04cca921',
    'after': 'c18485bc72e1ce659625781ca83f1ffc17213101cd51fd3d313454c91d370771',
}
NAMES = ('current-api25-instruction.txt', 'current-native26-instruction.txt',
         'instructions.diff', 'api-uniform-rules.txt', 'native-uniform-rules.txt',
         'reviewed-r9.txt', 'api-render-spec.json', 'native-render-spec.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('before', 'after', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    raw = (ROOT / PARSER).read_bytes()
    if sha(raw) != PARSER_SHA:
        raise ValueError('structural parser changed before execution')
    support = ModuleType('pinned_n2_delta_parser')
    support.__file__ = str(ROOT / PARSER)
    exec(compile(raw, support.__file__, 'exec'), support.__dict__)
    captured, texts, reports = {}, {}, {}
    for label in ('before', 'after'):
        folder = getattr(args, label).resolve(strict=True)
        report_path = folder / 'report.json'
        report_raw = report_path.read_bytes()
        if sha(report_raw) != REPORTS[label]:
            raise ValueError('render report changed: ' + label)
        reports[label] = support.load(report_raw)
        captured[str(report_path)] = report_raw
        texts[label] = {}
        for name in NAMES:
            candidates = [row for row in reports[label]['outputs'] if row['file'] == name]
            if len(candidates) != 1:
                raise ValueError('missing/ambiguous report output: ' + name)
            path = folder / name
            value = path.read_bytes()
            if len(value) != candidates[0]['bytes'] or sha(value) != candidates[0]['sha256']:
                raise ValueError('output does not match render report: ' + str(path))
            captured[str(path)] = value
            texts[label][name] = value.decode('utf-8')
    changes, structured = {}, {}
    for name in NAMES:
        changes[name + '.diff'] = ''.join(difflib.unified_diff(
            texts['before'][name].splitlines(keepends=True), texts['after'][name].splitlines(keepends=True),
            fromfile='01969/' + name, tofile='installed-D38/' + name))
    native = {label: support.commands(texts[label]['current-native26-instruction.txt'])
              for label in texts}
    structured['native_command_tokens'] = support.differences(native['before'][0], native['after'][0])
    structured['native_recorder_metadata'] = support.differences(native['before'][1], native['after'][1])
    structured['native_context'] = support.differences(
        support.native_context(texts['before']['current-native26-instruction.txt']),
        support.native_context(texts['after']['current-native26-instruction.txt']))
    structured['api_receipt'] = support.differences(
        support.api_receipt(texts['before']['current-api25-instruction.txt']),
        support.api_receipt(texts['after']['current-api25-instruction.txt']))
    for name in ('api-render-spec.json', 'native-render-spec.json'):
        structured[name] = support.differences(support.expand(support.load(texts['before'][name])),
                                                support.expand(support.load(texts['after'][name])))
    # A review aid only: replace parsed structures with explicit markers; full
    # original bytes and every structural leaf difference remain independently pinned.
    prose = {}
    for label in texts:
        text = texts[label]['current-native26-instruction.txt']
        text = re.sub(r'^([a-z][a-z0-9_]*):\n\n```bash\n([^\n]+)\n```',
                      lambda m: m[1] + ':\n\n<command tokens and recorder JSON reviewed separately>', text, flags=re.M)
        marker = '## Complete selected generation context\n\n'
        start = text.index(marker) + len(marker)
        _, end = json.JSONDecoder(object_pairs_hook=support.pairs).raw_decode(text[start:])
        text = text[:start] + '<complete generation context reviewed separately>' + text[start + end:]
        prose[label] = text
    changes['native-prose-only.diff'] = ''.join(difflib.unified_diff(
        prose['before'].splitlines(keepends=True), prose['after'].splitlines(keepends=True),
        fromfile='01969/native-prose', tofile='installed-D38/native-prose'))
    args.output.mkdir(parents=True, exist_ok=False)
    for name, text in changes.items():
        (args.output / name).write_text(text)
    for path, value in captured.items():
        if Path(path).read_bytes() != value:
            raise ValueError('comparison input changed: ' + path)
    result = {
        'scope': 'Complete same-arm text and structural comparison; no equivalence/acceptance inference.',
        'helper': {'path': str(Path(__file__)), 'sha256': sha(Path(__file__).read_bytes())},
        'parser': {'path': str(ROOT / PARSER), 'sha256': PARSER_SHA},
        'inputs': [{'path': p, 'bytes': len(v), 'sha256': sha(v)} for p, v in sorted(captured.items())],
        'source_heads': {label: reports[label]['source']['head'] for label in texts},
        'render_statuses': {label: reports[label]['status'] for label in texts},
        'same_arm_text_hunks': {name: [s for s in text.splitlines() if s.startswith('@@ ')]
                               for name, text in changes.items()},
        'current_between_arm_hunks': [s for s in texts['after']['instructions.diff'].splitlines() if s.startswith('@@ ')],
        'previous_between_arm_hunks': [s for s in texts['before']['instructions.diff'].splitlines() if s.startswith('@@ ')],
        'changes': structured,
        'input_bytes_unchanged': True,
        'outputs': [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                    for p in sorted(args.output.iterdir())],
    }
    (args.output / 'structural_deltas.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'output': str(args.output), 'change_counts': {key: len(rows) for key, rows in structured.items()}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
