# Purpose: classify retained native-controls failures without re-running (#5508), 2026-11-06.
# Input: r3-native-controls.xml. Output: r3-control-failures.json and short counts.
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[2]; S=R.parent/'scratch-native-u2'
rows=[]
for case in ET.parse(S/'r3-native-controls.xml').getroot().findall('.//testcase'):
    failure=case.find('failure')
    if failure is None: failure=case.find('error')
    if failure is None: continue
    text=failure.text or ''
    rows.append({'case':case.attrib,'message':failure.attrib.get('message',''),'permission_error_in_trace':'PermissionError' in text,'socket_bind_in_trace':'socket.bind' in text,'process_inspection_in_trace':"'ps'" in text or '/bin/ps' in text})
(S/'r3-control-failures.json').write_text(json.dumps(rows,indent=2)+'\n')
baseline=S/'r3-baseline-native-control.xml'
if baseline.exists():
    old={c.attrib['name'] for c in ET.parse(baseline).getroot().findall('.//testcase') if c.find('failure') is not None or c.find('error') is not None}
    targets={r['case']['name'] for r in rows if not r['permission_error_in_trace']}
    targets.add('test_an_audit_continues_from_the_probe_and_takes_the_tip[completed]')
    comparison={'compared_cases':sorted(targets),'also_failed_on_M7':sorted(targets & old),'not_reproduced_on_M7':sorted(targets-old)}
    (S/'r3-baseline-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    print(json.dumps(comparison,indent=2))
print(json.dumps({'without_permission_trace':[{'case':r['case'],'message':r['message'][:500]} for r in rows if not r['permission_error_in_trace']]},indent=2))
print(json.dumps({'failures':len(rows),'by_file':dict(Counter(r['case'].get('classname') for r in rows)),'permission_trace_count':sum(r['permission_error_in_trace'] for r in rows),'examples':[{'case':r['case'],'message':r['message'][:300]} for r in rows[:5]]},indent=2))
