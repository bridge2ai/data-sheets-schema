# Purpose: serial offline U2 round-3 validation queue (#5508), 2026-11-06.
# Inputs: committed U2 tree. Outputs: scratch per-stage evidence and queue ledger.
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
R=Path(__file__).resolve().parents[2]; S=R.parent/'scratch-native-u2'; LOCK=R.parent/'plans/native_quiet_window.lock'
PY='/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python'
DRIVER=str(R/'scripts/adhoc/validate_native_u2_20261106.py')
MUTATE=str(R/'scripts/adhoc/mutate_native_u2_r3_20261106.py')
results=[]
def quiet():
    while LOCK.exists():
        value=json.loads(LOCK.read_bytes())
        end=datetime.fromisoformat(value['expected_end_utc'])
        stale=datetime.now(timezone.utc)>end+timedelta(minutes=30)
        print(json.dumps({'state':'quiet-window wait','expected_end':str(end),'stale_over_30_minutes':stale}),flush=True)
        time.sleep(60)

def run(name,command,must_pass=False):
    quiet()
    print('Starting '+name,flush=True)
    code=subprocess.call([PY,'-B',*command],cwd=R)
    results.append({'stage':name,'exit_code':code})
    (S/'r3-queue.json').write_text(json.dumps(results,indent=2)+'\n')
    if must_pass and code: raise SystemExit('Required canary failed: '+name)
    print('Finished '+name+': '+str(code),flush=True)

run('focused-final',[DRIVER,'r3-focused-final','tests/test_native_authority_v2.py','tests/test_native_preparer_v2_boundaries.py','tests/test_native_preparer_v2_equivalence.py','tests/test_native_authority_replay_v1.py'],True)
run('mutation-control',[MUTATE,'M0_control'],True)
control=json.loads((S/'r3-mutations3/M0_control.json').read_bytes()); assert control['returncode']==0
run('mutation-canary',[MUTATE,'M1_v2_render_skips_rendered_jobs'],True)
canary=S/'r3-mutations3/M1_v2_render_skips_rendered_jobs'
assert json.loads(canary.with_suffix('.json').read_bytes())['returncode']==1
log=canary.with_suffix('.log').read_text(); assert "'rendered_jobs.json'" in log and 'Extra items' in log
for name in ['M2_v2_registration_drops_controller_authority','M3b_v2_preparer_drops_registry_declares_repinned','M4b_v2_preparer_drops_roster_subset_check_repinned','M5_direct_v2_pins_historical_preparer_with_repinned_supervisor','M6_direct_v2_drops_mixed_refusal_with_repinned_supervisor','M7_v2_controller_drops_preload','M8_v2_render_content_changes','M9_v2_drops_external_pins']:
    run(name,[MUTATE,name],True)
run('saved-replay',[str(R/'scripts/adhoc/replay_native_u2_r3_20261106.py')])
run('native-authority',[DRIVER,'r3-native-authority','tests/test_native_attribution_controller.py','tests/test_native_attempt_supervisor.py','tests/test_native_source_attribution.py','tests/test_native_attribution_results.py'])
run('native-gates',[DRIVER,'r3-native-gates','tests/test_native_execution_gates.py','tests/test_native_execution_permissions.py','tests/test_native_receipt_origin_reporting.py','tests/test_native_source_roster.py','tests/test_generality_native_legacy.py','tests/test_prompt_registry.py','tests/test_claudecode_direct_arm.py'])
run('native-execution',[DRIVER,'r3-native-execution','tests/test_native_execution.py'])
run('direct-arm',[DRIVER,'r3-direct-arm','notes/claudecode_direct/test_direct_arm.py'])
run('native-controls',[DRIVER,'r3-native-controls','notes/matched_cborg_2026-09-13/native_controls'])
run('scanner',[DRIVER,'r3-scan'])
run('collection',[DRIVER,'r3-collect'])
run('summary',[str(R/'scripts/adhoc/summarize_native_u2_r3_20261106.py')])
