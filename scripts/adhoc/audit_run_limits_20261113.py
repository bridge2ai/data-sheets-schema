#!/usr/bin/env python3
"""D143 source and frozen amendment inventory, 2026-11-13.
Inputs current native source and local draft-v12 object; outputs JSON evidence
and a line-addressed review document. Includes ignored/hidden source files.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--source-root', type=Path, help='Explicit combined source checkout; never changes that checkout.')
parser.add_argument('--controller-root', type=Path, help='Separate controller packet, when integration is pending.')
args=parser.parse_args()
DEST=Path(__file__).resolve().parents[2]
W=(args.source_root or DEST).resolve(strict=True);S=args.output
CONTROLLER=(args.controller_root or W).resolve(strict=True)
items=[
 ('native_run_limits.py','CANARY =','Changed: sole pair definitions and strict whole-pair validator.'),
 ('native_u4b_runtime.py','require_registered_pair(result)','Changed: final runtime profile admits only the declared pair.'),
 ('native_u4b_probe_sequence.py','require_registered_pair(runtime)','Changed: provisional runtime has the same pair restriction.'),
 ('native_u4b_policy.py','require_registered_pair(runtime)','Changed: registered admission validates the pair, without extending freshness.'),
 ('native_launch_review.py','budget, expected_deadline = require_registered_pair(runtime)','Changed: owner terms match the declared pair exactly; bundle and word retain their exact-byte joins.'),
 ('native_shared_runtime_values.py',"<= 86400",'Unchanged: generic one-day ceiling admits both values; production validators impose the narrower pairs.'),
 ('native_shared_registration.py',"'--max-budget-usd', runtime",'Unchanged: argv uses the declared budget verbatim.'),
 ('native_shared_registration.py',"'runtime': runtime,",'Unchanged: registration serializes the complete declared runtime.'),
 ('native_execution_orchestration.py',"deadline_seconds=value['runtime']['deadline_seconds']",'Unchanged: dispatch receives the declared deadline.'),
 ('native_execution_orchestration.py',"if value['runtime']['keep_awake']['policy']",'Unchanged: IOKit lifetime wraps the same dispatch and cleanup for either duration.'),
 ('native_attempt_supervisor.py','<= 3600','Unchanged: separate synthetic fixture supervisor local bound, not the native execution deadline.'),
 ('native_runtime_profiles.py','SYNTHETIC_DEADLINE_SECONDS =','Unchanged: separately declared synthetic profile remains fixed.'),
 ('native_shared_runtime_constants.py',"'deadline_seconds', 'budget_guard_usd'",'Unchanged: both values are already explicit wire keys; no new discriminant.'),
 ('native_shared_render.py',"'native_shared_runtime_declaration': _raw_identity(runtime)",'Runtime identity is carried in render metadata; the environment specification transports the complete metadata.'),
 ('native_shared_render.py',"'--render-spec-env'",'Candidate recorder reads D4D_RENDER_SPEC and binds it with --render-spec-sha256; selecting another pair changes the visible digest, not embedded budget/deadline literals.'),
 ('native_subscription_guard_v2.py','def _fresh(self):','Unchanged: age/reset checks repeat at dispatch; they do not certify quota throughout the longer run.'),
 ('native_subscription_guard_v2.py','def before_reservation(self):','Unchanged: the same registered reservation margin applies.'),
]
rows=[]
for filename,anchor,finding in items:
 p=W/'src/data_sheets_schema'/filename
 matches=[i for i,line in enumerate(p.read_text().splitlines(),1) if anchor in line]
 if not matches:raise ValueError((filename,anchor))
 rows.append({'path':str(p.relative_to(W)),'lines':matches,'finding':finding})
p=CONTROLLER/'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
for anchor,finding in [
 ('dispatch_ns = elapsed_ns()', 'Child runtime starts immediately before process creation on the continuous clock; admission is excluded.'),
 ('deadline = dispatch_ns + int(deadline_seconds * 1_000_000_000)', 'The declared 900, 21600 or 43200 seconds are measured from dispatch, including host suspension.'),
 ('admission = AdmissionTimer(entry_ns, seconds=ADMISSION_SECONDS, clock=elapsed_ns)', 'Separate 900-second admission bound begins at execute_child entry, before setup and verification.'),
]:
 matches=[i for i,line in enumerate(p.read_text().splitlines(),1) if anchor in line]
 if len(matches)!=1:raise ValueError(('required combined timer anchor',anchor,matches))
 rows.append({'path':str(p.relative_to(CONTROLLER)),'lines':matches,'finding':finding})
S.mkdir(parents=True,exist_ok=False)
search=subprocess.run(['rg','--hidden','--no-ignore','-n','21600|21,600|43200|43,200|six.hour|six hours|budget_guard_usd|pre_reservation_margin_seconds|elapsed_ns|ADMISSION_SECONDS','src/data_sheets_schema'],cwd=W,capture_output=True,text=True)
(S/'run-limit-source-search.txt').write_text(search.stdout)
draft=subprocess.check_output(['/usr/bin/git','show','c289eed19:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md'],cwd=W)
(S/'amendment-n1-v12.md').write_bytes(draft)
references=[{'line':i,'text':line} for i,line in enumerate(draft.decode().splitlines(),1) if re.search(r'21,600|21600|6 h|six.hours|six.hour',line)]
record={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip(),'controller_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=CONTROLLER,text=True).strip(),'source_inventory':rows,'draft_v12_sha256':hashlib.sha256(draft).hexdigest(),'draft_v12_six_hour_references':references,'search_includes_hidden_ignored':True}
(S/'run-limit-audit.json').write_text(json.dumps(record,indent=2)+'\n')
lines=['# Two registered native run-limit sets','',
 'D143 retains the canary shakedown pair and the production pair, defined only in `native_run_limits.py`. A caller supplies both fields explicitly. No project, label or bundle selects a pair. Mixed pairs, alternate decimal spellings, third values, missing values and boolean/float deadlines refuse. The separately declared synthetic profile is unchanged.','',
 'No registered document kind or version changes. Runtime, registration, owner terms, review bundle and coded word already carry or pin the complete runtime and exact registration bytes. A production run needs newly prepared and reviewed evidence under its selected pair. Historical canary bytes are not rewritten.','',
 '| Source | Treatment |','| --- | --- |']
for row in rows:lines.append('| `'+row['path']+':'+','.join(map(str,row['lines']))+'` | '+row['finding']+' |')
lines+=['','## Operational differences','',
 'A twelve-hour attempt spans more five-hour usage-window boundaries than a six-hour attempt: for fixed aligned five-hour windows, two or three rather than one or two, depending on dispatch phase. This is arithmetic, not a claim about provider reset scheduling. A weekly boundary may occur during either; the longer run has more exposure to one. Starting utilization is not a guarantee of twelve hours of available quota. Overage remains disabled and observed rate/quota stops remain sticky.','',
 'The candidate retains a 1200-second maximum observation age and a 300-second pre-reservation margin (57bcc018b): reservation is allowed through age 900 seconds and dispatch through age 1200 seconds. They bound evidence age at launch, not evidence freshness throughout the attempt; a twelve-hour deadline does not turn them into twelve-hour authority or refresh a consumed capture. The fourteen-day registered validity interval and exact owner-word joins remain unchanged.','',
 'The three IOKit assertions remain acquired through the attempt and released through the same cleanup. Idle-sleep assertions do not prevent lid sleep, power exhaustion or host interruption. The combined implementation checks AC power immediately before dispatch and records supplemental host-power observations. The child deadline begins immediately before process creation on mach_continuous_time on macOS or CLOCK_BOOTTIME on Linux; both include suspension. There is no adjustable-wall-clock fallback. The separate synthetic fixture supervisor retains its one-hour bound.','',
 'Admission has its own 900-second continuous-clock bound from execute_child entry through the dispatch origin. It includes controller setup and launch verification, consumes none of the declared child runtime, and does not extend subscription freshness. Periodic POSIX wakeups raise once on expiry through interruptible Python system calls; queued alarms are inert during unwinding. Teardown cancels the timer, holds SIGALRM blocked for another polling interval, drains pending delivery, and restores the handler and mask. The synchronous dispatch check remains authoritative. Expiry refuses dispatch and takes the existing failure-publication and keep-awake cleanup path. It cannot preempt uninterruptible kernel calls or C extensions that do not service signals. Earlier capture-to-reservation verification lies outside this admission bound.','',
 'Canary and production instructions differ through runtime-dependent render metadata and its digest. On the candidate (c577c0eff), the recorder uses --render-spec-env D4D_RENDER_SPEC plus --render-spec-sha256. The command contains the digest instead of embedded runtime JSON; changing the pair changes that model-visible digest and exact-command policy. The runtime declaration remains a registered readable input. The canary is therefore a shakedown, not the frozen production reference. The later reference pilot must use production terms.','',
 'Same-input compatibility is checked against exact source from the published base: prepared canary runtime bytes remain identical, and the unchanged saved canary registration/review/word bytes validate with equal derived terms. That saved-registration fixture is deliberately parser-scoped. A newly built complete registration binds package-source identities, so its bytes necessarily change when code changes; this test does not claim fresh full-registration byte identity across source revisions. No source pins are restamped to manufacture that identity.','',
 '## Frozen draft v12 references requiring production qualification','',
 'The historical draft is retained unchanged. The lead must qualify its universal six-hour statements for production; historical D14 source recommendations remain historical. The matching lines below are derived from the local frozen draft, not edited here.','']
for row in references:lines.append('- Line '+str(row['line'])+': '+row['text'])
(DEST/'docs/native-run-limits.md').write_text('\n'.join(lines)+'\n')
print(S/'run-limit-audit.json')
