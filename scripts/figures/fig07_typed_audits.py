#!/usr/bin/env python3
"""Plot explicitly selected checked typed audits; no legacy prose classification."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from data_sheets_schema.typed_audit_figure import prepare, publish


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly', action='append', required=True,
                        help='Raw typed assembly path; repeat explicitly in caller order')
    parser.add_argument('--output-dir', type=Path, required=True, help='Fresh destination directory')
    args = parser.parse_args(argv)
    try:
        manifest = publish(prepare(args.assembly), args.output_dir)
    except Exception as exc:
        parser.exit(2, f'typed audit figure refused: {type(exc).__name__}: {exc}\n')
    print(json.dumps({'state': manifest['state'], 'output_dir': str(args.output_dir),
                      'assembly_count': len(manifest['assemblies'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
