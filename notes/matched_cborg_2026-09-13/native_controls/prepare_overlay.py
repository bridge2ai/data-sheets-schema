"""Freeze draft native execution controls without any model request."""
from datetime import datetime,timezone
from pathlib import Path
import argparse,hashlib,json,subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--registration',type=Path,default=BASE/'registration.json')
parser.add_argument('--output',type=Path,default=HERE/'overlay.json')
parser.add_argument('--claude-executable',type=Path,default=Path('/Users/marcin/.local/bin/claude'),
                    help='Exact runtime or alias; resolved bytes and version are pinned')
args=parser.parse_args()
registration=args.registration.resolve();r=json.loads(registration.read_bytes())
if Path(r['repository']).resolve()!=BASE.parents[1].resolve():
    raise SystemExit('Prepare a fresh source/instrument registration in this checkout before freezing its native overlay')
# Every `d4d <group> <command>` the native playbook prescribes and every module
# entry point the renderer-12 instruction prescribes, kept in a roster that
# test_native_launch.py checks against the playbook text (#1916, #1923). The
# v10q CHORUS run's eight denials were help exploration, `agents digest`, a
# heredoc, a `python -c` chained with a redirect and `wc`, a scratch write
# under /tmp and a `cat >>` on the receipt; it never called `prompt render`,
# which the playbook prescribes and the roster lacked, and `source_review`,
# which the instruction prescribes, was missing too.
import sys as _sys; _sys.path.insert(0, str(HERE))
from native_command_policy import build_command_policy
cli_alias=args.claude_executable
cli=cli_alias.resolve(strict=True)
assert subprocess.check_output([str(cli),'--version'],text=True).strip()==r['claude_version']
py=r['python']
jobs=[j for j in r['generation']['jobs'] if j['canary'] and j['execution_arm']=='agentic']
policies={j['id']:build_command_policy(j,py,r['repository']) for j in jobs}
files=[HERE/name for name in ('native_proxy.py','run_native_canary.py','prepare_overlay.py','prepare_overlay_roster.py','native_command_policy.py','native_readonly.py','native_control.py','system.md')]
files.extend(BASE/name for name in ('budgeted_cborg.py','run_api_canary.py','prepare_registration.py'))
files.append(cli.resolve())
value={'registered_at':datetime.now(timezone.utc).isoformat(),'status':'draft_awaiting_independent_review_and_prior_canary_acceptance',
 'registration':str(registration),'registration_sha256':sha(registration),'allowed_jobs':[j['id'] for j in jobs],
 'condition_boundary':'Native execution controls supplement the immutable source/instrument registration. They do not alter its source bytes, prompt files, schemas, profiles, cohort labels or budget ledger identity.',
 'shell_rule':'Only the registered helpers and the instruction-prescribed commands; no --help exploration, heredocs, ad-hoc scripts, programs the allowlist does not name chained into a command, or writes outside the run directories (#1916, #1929).',
 'claude_executable':str(cli),'observed_cli_alias':str(cli_alias),'claude_version':r['claude_version'],'system_prompt':str(HERE/'system.md'),
 'cli_flags':['--print','--safe-mode','--restricted','--strict-mcp-config','--disable-slash-commands','--no-session-persistence','--prompt-suggestions','false','--output-format','stream-json','--verbose','--permission-mode','dontAsk','--tools','Read,Write,Bash'],
 'per_job_command_policy':policies,'environment':{'DISABLE_NON_ESSENTIAL_MODEL_CALLS':'1','DISABLE_TELEMETRY':'1','CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS':'1'},
 'per_job_environment':{j['id']:{'D4D_MANIFEST':j['manifest'],'D4D_PROFILE':j['profile'],
     **({'D4D_LAUNCH_INSTRUCTION':j['instruction']} if j['render_spec']['render_version'] >= 9 else {})}
     for j in jobs},
 'credential_boundary':'Only the parent transport receives CBORG_API_KEY. The child receives an ephemeral local transport token and has no inherited provider, GitHub or OAuth credentials.',
 'accounting':'All native model calls, including auxiliary calls, pass serial admission against the same cumulative attempt and sequence ledger as the API arm. A fixed session name suppressed auxiliary title generation in the offline probe; the guard does not rely on that suppression.',
 'native_limits_observed_offline':{'context_window':200000,'max_output_tokens':64000},
 'limit_basis':'Installed CLI declaration during a scripted offline probe; distinct from CBORG route maxima (1M input, 128k output). Confirm runtime declaration, actual request ceilings and any compaction in the scientific trace.',
 'effort_policy':r['generation']['effort_policy'],'pinned_files':{str(p):sha(p) for p in files}}
path=args.output
path.parent.mkdir(parents=True,exist_ok=True)
with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps({'overlay_sha256':sha(path),'pinned_files':len(files),'allowed_jobs':value['allowed_jobs'],'status':value['status']},indent=2))
