# Purpose: freeze round-3 U2 closure (#5508), 2026-11-06.
# Input: committed helper revision. Outputs: v2 manifest and consumer hashes.
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
R=Path(__file__).resolve().parents[2]
commit=subprocess.check_output(['git','rev-parse',sys.argv[1]],cwd=R,text=True).strip()
p=R/'src/data_sheets_schema/native_controller_sources_v2.json'
manifest=json.loads(p.read_bytes());manifest['source_commit']=commit
for pin in manifest['modules'].values():
    raw=subprocess.check_output(['git','show',f"{commit}:{pin['path']}"],cwd=R)
    assert raw==(R/pin['path']).read_bytes()
    pin['sha256']=hashlib.sha256(raw).hexdigest()
p.write_text(json.dumps(manifest,indent=2)+'\n')
c=R/'src/data_sheets_schema/native_attribution_controller_v2.py'
c.write_text(re.sub(r"SOURCES_SHA256 = '[a-f0-9]+'", "SOURCES_SHA256 = '"+hashlib.sha256(p.read_bytes()).hexdigest()+"'",c.read_text()))
p=R/'src/data_sheets_schema/native_supervisor_authority_v2.py'
s=p.read_text(); old=json.loads(subprocess.check_output(['git','show','HEAD:src/data_sheets_schema/native_controller_sources_v2.json'],cwd=R))
raw=subprocess.check_output(['git','show',f'{commit}:notes/claudecode_direct/prepare_direct_v2.py'],cwd=R)
s=re.sub(r"('prepare_direct': .*?\n        'sha256': ')[a-f0-9]+",lambda m:m[1]+hashlib.sha256(raw).hexdigest(),s)
p.write_text(s)
