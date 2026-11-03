"""P4a findings 4/5 validation triage, 2026-10-30.

Input: completed shard JUnit in .g1-round2-evidence. Output: exact failed nodes
and whether setup was blocked by the sandbox's loopback socket restriction.
No test execution, network or production-file writes.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.g1-round2-evidence'


def read_failures():
    result = []
    for case in ET.parse(OUT / 'shard-1.xml').findall('.//testcase'):
        failures = case.findall('failure') + case.findall('error')
        if not failures:
            continue
        parts = case.attrib['classname'].split('.')
        for end in range(len(parts), 0, -1):
            filename = '/'.join(parts[:end]) + '.py'
            if (ROOT / filename).is_file():
                node = '::'.join([filename, *parts[end:], case.attrib['name']])
                break
        else:
            raise AssertionError(case.attrib)
        trace = '\n'.join(f.text or '' for f in failures)
        loopback = ('self.socket.bind(self.server_address)' in trace
                    and 'PermissionError: [Errno 1] Operation not permitted' in trace)
        result.append({'node': node, 'kind': 'loopback_setup' if loopback else 'other',
                       'message': [f.attrib.get('message') for f in failures]})
    return result


if __name__ == '__main__':
    result = read_failures()
    destination = OUT / 'shard-failures.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
