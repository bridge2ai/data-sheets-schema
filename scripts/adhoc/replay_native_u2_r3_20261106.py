# Purpose: verify saved M7 bytes in original and current environments (#5508), 2026-11-06.
# Inputs: retained M7 packet/baseline. Output: scratch r3-replay.json; no fixture rewrites.
import json
import os
from pathlib import Path
import subprocess
import sys
R=Path(__file__).resolve().parents[2]; S=R.parent/'scratch-native-u2'
if len(sys.argv)>1:
    from data_sheets_schema import native_attribution_registration as old
    raw=(S/'v1-replay-final/registration.json').read_bytes()
    if sys.argv[1]=='original':
        from data_sheets_schema import native_attribution_controller as controller
        assert old.verified(raw)[1]['code_commit']=='8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
        assert controller.verified_composition((S/'v1-replay-final/composition.json').read_bytes())['version']==1
        print(json.dumps({'original_saved_registration':'verified','original_saved_composition':'verified'}))
    else:
        from data_sheets_schema import native_attribution_registration_v2 as new
        results={}
        for label,module,reason in [('v1',old,'checker identity'),('v2',new,'unsupported native attribution registration version')]:
            try: module.verified(raw)
            except ValueError as exc:
                assert reason in str(exc),str(exc)
                results[label]=str(exc)
            else: raise AssertionError('saved v1 record accepted by '+label)
        print(json.dumps(results))
else:
    if (R.parent/'plans/native_quiet_window.lock').exists(): raise SystemExit('quiet window: replay not started')
    results={}
    for mode,source in [('original',S/'baseline'),('current',R)]:
        env={k:v for k,v in os.environ.items() if not k.startswith(('ANTHROPIC_','CBORG_','OPENAI_','CLAUDE_'))}
        env.update(PYTHONPATH=str(source/'src'),PYTHONDONTWRITEBYTECODE='1',GIT_NO_LAZY_FETCH='1')
        raw=subprocess.check_output([sys.executable,'-B',str(Path(__file__).resolve()),mode],cwd=source,env=env,text=True,timeout=3600)
        results[mode]=json.loads(raw)
    (S/'r3-replay.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results))
