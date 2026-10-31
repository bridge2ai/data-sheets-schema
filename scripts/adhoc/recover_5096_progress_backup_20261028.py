#!/usr/bin/env python3
# Purpose: recover #5233's omitted eighth #5096 backup without modifying ATTIC.
# Input: exact preserved AGY progress JSON; outputs: byte-identical new copy and manifest.
# No providers/network; heuristic credential scan prints no values. Date: 2026-10-28.
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHA = '679aab514fb672586e234f4218a81397dd9d9e4ac1b9a8eb7c235bd471e963a6'
EXPECTED_SIZE = 23364
DESTINATION = ROOT / 'notes/canary_evidence_recovery_2026-10-28'
PATTERNS = {
    'credential_key': r'(?i)["\x27](?:api[_-]?key|access[_-]?token|auth[_-]?token|authorization|password|client[_-]?secret|secret[_-]?key)["\x27]\s*:',
    'private_key': r'-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----',
    'provider_key': r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})',
    'bearer_value': r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{16,}',
    'jwt': r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=DESTINATION)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA or len(raw) != EXPECTED_SIZE:
        raise ValueError('source bytes differ from the independently reviewed preserved original')
    text = raw.decode('utf-8')
    doc = json.loads(text)
    if type(doc) is not dict:
        raise ValueError('expected progress JSON object')
    # Decode embedded JSON strings for the credential heuristic, without printing values.
    strings = [text]
    def walk(value):
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(doc)
    matches = {name: sum(len(re.findall(pattern, value)) for value in strings)
               for name, pattern in PATTERNS.items()}
    if any(matches.values()):
        raise ValueError('credential heuristic requires manual review; counts only: ' + json.dumps(matches))
    manifest = {'source': str(args.source.resolve()), 'destination': 'CHORUS_api_progress.json',
                'sha256': digest, 'bytes': len(raw), 'artifact_sha256_recorded_in_original_readme': EXPECTED_SHA,
                'reviewed_data_head': 'ada98b56b73b60217ccacf02fef2af4393d6ecae',
                'source_label': '2026-10-20a_claude-opus-5-api-generic-v10_rep1',
                'purpose': 'Exact preserved pre-edit progress backup omitted by .gitignore; evidence only.',
                'credential_heuristic_counts': matches, 'credential_scan_limit': 'Heuristic only; no values printed.',
                'top_level_keys': sorted(doc), 'historical_files_modified': False,
                'scientific_acceptance': 'not granted'}
    args.output_dir.mkdir(exist_ok=True)
    with (args.output_dir / 'CHORUS_api_progress.json').open('xb') as handle:
        handle.write(raw)
    with (args.output_dir / 'manifest.json').open('x') as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'sha256': digest, 'bytes': len(raw), 'credential_heuristic_counts': matches,
                      'top_level_keys': sorted(doc)}, sort_keys=True))


if __name__ == '__main__':
    main()
