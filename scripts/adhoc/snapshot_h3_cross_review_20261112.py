#!/usr/bin/env python3
"""H3 read-only review inputs, 2026-11-12: exact helper2 commits -> own evidence.
No reviewed source edits/tests/launch; Git show only. Writes new review directory.
"""
import hashlib,json,subprocess
from pathlib import Path
W=Path(__file__).resolve().parents[2]; E=W.parent; S=E/'scratch-h3-packet-builder-20261112'; O=S/'cross-review'; O.mkdir(exist_ok=False)
commits=['d07eccefb59938f8b625498247259f17e5c155ec','34b46c3132ab7a5cab4f9bdf7634d38c77321369','e936cbb83d091cfab5c2e8b85bdd4c08a1b6b1e0','cf53497ae2ebfba1da9c64995590115c48437f77','d2efa55014e131f92733bf2c3a90c0830214dc89']
def git(*args): return subprocess.check_output(['/usr/bin/git','-C',str(W),*args])
pins=[]
def save(name,raw):
    path=O/name; path.write_bytes(raw); pins.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
for commit in commits: save(commit+'.diff',git('show','--format=fuller','--no-ext-diff',commit))
head=commits[-1]
for file in ['src/data_sheets_schema/native_launch_sequence.py','src/data_sheets_schema/native_launch_review.py','tests/test_native_launch_sequence.py','tests/test_native_review_bundle_v3.py']:
    save(Path(file).name,git('show',head+':'+file))
save('n1-v12.md',git('show','c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md'))
for name in ['codex-h2-launch-sequence-20261112.md','codex-h2-review-bundle-v3-20261112.md']:
    save(name,(E/'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'/name).read_bytes())
# Pins only; exact diff files may contain ordinary Git author addresses.
(O/'source-pins.json').write_text(json.dumps({'commits':commits,'files':pins},indent=2)+'\n')
print(O)
