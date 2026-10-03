#!/usr/bin/env python3
"""Render an explicitly selected structured Figure 11 without scoring inputs."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from data_sheets_schema.semantic_taxonomy_figure import prepare, publish


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = publish(prepare(args.selection), args.output_dir)
    except Exception as exc:
        print(f'Refused taxonomy figure: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({'state': report['state'], 'output_dir': str(args.output_dir),
                      'selection_occurrences': len(report['report']['ratings']),
                      'groups': len(report['report']['groups'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
