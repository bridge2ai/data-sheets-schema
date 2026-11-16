"""PR 5968 polluter verification evidence, 2026-11-16.

Inputs: replay directory containing saved trace and JUnit output.
Output: JSON counts, failures, and runtime-support transitions on stdout.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    trace = args.directory / 'executed-nodes.json.trace.jsonl'
    rows = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    transitions = []
    previous = None
    for index, row in enumerate(rows):
        if previous is None or row['supported'] != previous['supported']:
            transitions.append({'index': index, 'previous': previous, 'current': row})
        previous = row
    result = {'trace_records': len(rows), 'transitions': transitions}
    junit = args.directory / 'results/unit.xml'
    if junit.exists():
        tree = ET.parse(junit)
        result['suites'] = [suite.attrib for suite in tree.iter('testsuite')]
        result['failures'] = [
            {'case': case.attrib, 'outcomes': [child.attrib for child in case
                                             if child.tag in ('failure', 'error')]}
            for case in tree.iter('testcase') if case.find('failure') is not None
            or case.find('error') is not None]
        result['failure_message_counts'] = dict(Counter(
            outcome.get('message', '').split('\n', 1)[0]
            for failure in result['failures'] for outcome in failure['outcomes']))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
