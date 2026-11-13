#!/usr/bin/env python3
"""Issue 6046: configure an exact pending-source private four-packet composition.
Input/output: own composition helper; no production execution. 2026-11-13.
"""
from pathlib import Path
p=Path(__file__).with_name('prepare_host_power_composition_20261113.py');s=p.read_text()
s=s.replace('scratch-h2-helper-cache-20261112','scratch-h2-host-power-20261113')
s=s.replace("assert not h.git('status','--porcelain',cwd=W)","# Exact pending source paths below are copied and pinned in the private commit.")
needle="h.git('add','--',*(row['path'] for row in rows),cwd=tree)"
replacement="""pending = ['src/data_sheets_schema/native_host_power.py',
 'src/data_sheets_schema/native_launch_sequence.py', 'src/data_sheets_schema/native_execution_orchestration.py',
 'src/data_sheets_schema/native_shared_capture_orchestration.py', 'tests/test_native_host_power.py',
 'tests/test_native_launch_sequence.py', 'tests/test_native_shared_live_capture.py',
 'tests/fixtures/native_host_power/pmset-sleep-20261112.txt', 'docs/native-host-power.md']
for path in pending:
 target=tree/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((W/path).read_bytes())
h.git('add','--',*(row['path'] for row in rows),*pending,cwd=tree)"""
assert needle in s;s=s.replace(needle,replacement)
s=s.replace('Offline issue 5966 four-packet proof composition','Offline issue 6046 four-packet host-power composition')
s=s.replace("'candidate':'ba1f56e4a9460fe87c1e0ea3cb35ed2d7405cfa0'", "'candidate':'8760de5efe88b5af62e9d77e6335fa7e248017b6'")
s=s.replace("'repair_commit':base,", "'repair_commit':base,'pending_source_sha256':{p:h.sha((W/p).read_bytes()) for p in pending},")
p.write_text(s)
# Published 8760de5 already contains owner-approved postimages (6561dac3c).
s=p.read_text().replace("==row['main_sha256']", "==row['postimage_sha256']")
s=s.replace("for row in rows:(tree/row['path']).write_bytes((packet_base/'packets'/(row['name']+'.postimage')).read_bytes())", "# Protected postimages already exist unchanged in the published candidate.")
p.write_text(s)
