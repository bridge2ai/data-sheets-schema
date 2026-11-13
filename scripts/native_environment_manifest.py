#!/usr/bin/env python3
"""Write a registration environment manifest using the registered interpreter.

Reads installed metadata only; refuses an existing output or incomplete metadata.
Run with the source export's registered import environment. No native binary is run.
"""
import argparse
import json
from data_sheets_schema.native_environment_manifest import write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        result = write(args.out)
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
