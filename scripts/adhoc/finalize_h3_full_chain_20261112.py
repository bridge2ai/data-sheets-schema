#!/usr/bin/env python3
"""Finalize H3 rehearsal, 2026-11-12: retained tests/map -> evidence and handoff.
Restores only the private composition config; no network, native or reservation.
Serves claude-lead-helper3-full-chain-rehearsal-20261112 assignment.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
W=Path(__file__).resolve().parents[2]
E=W.parent; S=E/'scratch-h3-packet-builder-20261112'; T=S/'composition-a/tree'
def load(p): return json.loads(p.read_bytes())
def pin(p):
    raw=p.read_bytes(); assert raw
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def git(root,*args):
    return subprocess.check_output(['/usr/bin/git','-c','core.hooksPath=/dev/null','-C',str(root),*args]).decode().strip()
def write(p,v): p.write_text(json.dumps(v,indent=2)+'\n')
runs=[]
for name in ['full-chain-canary-01','full-chain-rest-01','full-chain-final-01']:
    root=S/'tests'/name; outcome=load(root/'outcome.json'); xml=ET.parse(root/'pytest.xml')
    assert outcome['returncode']==0 and outcome['cleanup_verified'] and not outcome['observed_surviving_pids']
    assert not xml.findall('.//failure') and not xml.findall('.//error')
    runs.append({'name':name,'cases':len(xml.findall('.//testcase')),'log':pin(root/'pytest.log'),'junit':pin(root/'pytest.xml'),'outcome':pin(root/'outcome.json'),'cleanup_verified':True})
rest=S/'tests/full-chain-rest-01/cases/full-chain-cohort0/SYNTHETIC-chain'
last=S/'tests/full-chain-final-01/cases/full-chain-cohort0/SYNTHETIC-chain'
ts=load(rest/'timestamp-results.json')
# Exercise both new read-only CLI modes, retaining exact output. No new commit here.
evidence=S/'timestamp-cli-evidence.json'; write(evidence,ts['evidence'])
cli=[]
for args in [['--author-date-only'],['--verify-evidence',str(evidence)]]:
    command=[sys.executable,'-P','-B',str(W/'scripts/native_registration_timestamp.py'),'--registration',str(rest/'synthetic-registration.json'),*args]
    result=subprocess.run(command,text=True,capture_output=True,check=True)
    cli.append({'command':command,'stdout':result.stdout,'stderr':result.stderr,'returncode':result.returncode})
assert cli[0]['stdout'].strip()==ts['success']['valid_from']
assert json.loads(cli[1]['stdout'])['checked'] is True
write(S/'timestamp-cli-checks.json',cli)
receipt_path=S/'composition-a/composition.json'; receipt=load(receipt_path)
assert git(T,'rev-parse','HEAD')==receipt['composition_commit']
assert not git(T,'status','--porcelain')
assert not git(T,'remote')
protected=[]
for row in receipt['packets']:
    assert pin(T/row['path'])['sha256']==row['postimage_sha256']
    assert pin(W/row['path'])['sha256']==row['main_sha256']
    protected.append({'path':row['path'],'branch_sha256':pin(W/row['path'])['sha256'],'scratch_sha256':pin(T/row['path'])['sha256']})
config=T/'.git/config'; backup=T/'.git/config.bak-h3-full-chain-20261112'
assert pin(backup)['sha256']==receipt['config_original_sha256']
before=pin(config)
if receipt['config_restore_pending']:
    config.write_bytes(backup.read_bytes())
assert config.read_bytes()==backup.read_bytes()
restore={'backup':pin(backup),'before_restore':before,'restored':pin(config),'equal_original':True,'private_ci_url_present_after':False}
if not receipt['config_restore_pending']:
    restore=receipt['config_restoration']
assert 'ciRepositoryUrl' not in config.read_text()
receipt.update(config_restore_pending=False,config_restoration=restore,status='focused_rehearsal_passed_with_documented_refusals',sparse_materialization_added=['data/omission_contexts'])
write(receipt_path,receipt)
map_path=W/'notes/native_canary_packet_map_DRAFT_20261112/map.json'
notes=[
('Validated repository input through real CHORUS prefix and synthetic selection capture.','Real CHORUS manifest in prefix; invented manifest in synthetic chain.'),
('Validated source bytes/mapping; existing input, not a generated source.','Real baseline CHORUS bytes in prefix; fixture source in full chain.'),
('Built/validated manifest mapping in production selection path.','Real CHORUS declared chunks in prefix; fixture chunks in full chain.'),
('Validated by selection capture.','Real CHORUS omission context in prefix; fixture context in synthetic chain.'),
('Captured/validated via production schema closure path.','Installed schema assets; fixture selection declares synthetic inputs.'),
('Captured installed assets and validated profile.','Real bridge2ai prefix; neutral fixture profile in synthetic chain.'),
('Built and parsed through production receipt policy parser.','Draft registration identity; source-derived instrument; fixture policy in full chain.'),
('Built and validated through parse_selection and capture.','Real CHORUS prefix with draft locations; invented full-chain registration and locations.'),
('Synthetic provisional runtime consumed by prepare_synthetic and saved observation validation; real draft deliberately invalid.','Inert peer bytes, invented model/account/environment/limits; no binary observed.'),
('Synthetic saved authorization validated as part of observation/bound sequence; real draft deliberately invalid.','Fixture owner/time/word and authorization; not an owner act.'),
('Constructed for CLI rehearsal; account-choice validator not reached because D106 gate refuses first.','Fixture subject/runtime hashes and declarations; no owner choice inferred.'),
('Fabricated saved records passed production observation validator and final-runtime preparation.','All observation/transcript/request/process evidence invented; no probe ran.'),
('Built by native_u4b_runtime.prepare_synthetic and validated downstream.','Inert peer copies, fake observation, model/account/limits and fixture validity interval.'),
('Built by prepare_synthetic, checked by verify_preparer; fresh admit also passes.','Synthetic selection/runtime/job identifier; real source-derived instruction.'),
('Built by compose and validated by reconstruct_composition.','Synthetic preparation and exact derived instruction; real dependency closure.'),
('Saved fixture text accepted in permission/registration path; no production system approval.','Explicit SYNTHETIC label and command guidance from source.'),
('Built by permission_expectation and consumed by actual bound-probe verifier.','Synthetic runtime/source/paths; actual installed command policy.'),
('Seven fabricated traces and completion pass validate_bound_probe and registration verification.','Every trace/outcome fabricated; saved probe claims only, no execution or capture reservation.'),
('Built by synthetic_registration and checked by verified plus fresh admit.','Synthetic runtime, source, saved permissions, future attempt/evidence paths absent.'),
('Production commit/addition/blob/date validator passes scratch proof and rejects author time one second off.','New scratch registration-evidence repository and synthetic registration only.'),
('Declared CI schema passes genuine authorizations and fresh admit; no actual CI certified.','Invented workflow run URL/ref and successful check claims, explicitly labelled synthetic.'),
('Fixture review documents pass genuine current bundle validator.','Invented independent reviewer identities, decisions and timestamps; not real reviews.'),
('Fixture current terms/request pass bundle validation; no capture state created.','Invented owner/time, account_quiet true and requested directory; terms/margin read from source.'),
('Current bundle passes production adapter and admission, including sequence source pin.','Fixture reviews/owner plus actual dependency source hash; current kind/version source-derived.'),
('Fixture word passes review/CI/word join and fresh admit; no journal written.','Invented owner/time/word; actual fixture artifact hashes.'),
('No capture manifest built: public capture refuses D106 requires the selected Max subscription. Pure invented quota event feeds guard builder only.','Quota event invented; no recorded word state, capture claim, provider or account observation.'),
('Pure prepare_guard succeeds; current_guard_preparation refuses: capture registration has no recorded word state. No current guard admitted.','Invented quota event, capture index/count and fixture terms; no latest claim fabricated.')]
docs=load(map_path)['documents']; assert len(docs)==len(notes)==27
rows=[{'document':d['document'],'outcome':n[0],'synthetic_inputs_and_limits':n[1]} for d,n in zip(docs,notes)]
write(S/'full-chain-document-outcomes.json',{'historical_map':pin(map_path),'scope':'Current composition supplement; historical map retained unchanged.','documents':rows})
contract=load(last/'source-contract.json')
refusals=[load(rest/(cmd+'-refusal.json')) for cmd in ['capture-subscription-event','prepare-subscription-guard-v2','launch']]
anchors=[('native_launch_review.py',67,'Exact registration-addition commit/blob/parent checks'),('native_launch_review.py',137,'valid_from equals commit author time'),('native_u4b_policy.py',46,'Fourteen-day validity interval'),('native_capture_words.py',76,'valid_from <= word authorized_at <= now < valid_until'),('native_launch_review.py',328,'Review time cannot follow launch word'),('native_subscription_guard_v2.py',337,'Guard terms equal registered terms'),('native_subscription_guard_v2.py',364,'Capture/word chronology, current-clock freshness and margin'),('native_launch_sequence.py',56,'Delegation thirty-minute checks at entry and before capture')]
source_evidence=[{'file':pin(T/'src/data_sheets_schema'/f),'line':line,'meaning':meaning} for f,line,meaning in anchors]
probe=S/'probe-packet-draft-v2'; probe_pins=[pin(p) for p in sorted(probe.iterdir()) if p.is_file()]
answer='The detached composition now builds and validates the synthetic chain through runtime, preparation, composition, seven-trace saved permission evidence, registration, current review/CI/word join and fresh admission without creating reservations. All three public launch commands genuinely stop at "D106 requires the selected Max subscription"; no gate was bypassed. The pure guard builder works, while current-guard preparation refuses "capture registration has no recorded word state"; no capture or launch was performed.'
timestamp='The lead reads valid_from from the frozen registration runtime and uses that exact whole-second UTC value as the registration-addition commit author date, without selecting another date. After committing the exact bytes on the evidence branch, scripts/native_registration_timestamp.py --verify-evidence invokes the production validator and stops on any bytes, addition or author-time mismatch. The scratch proof passes for equality and refuses a one-second mismatch; no production date or commit was made.'
owner='The owner must supply or approve identity, actual UTC authorization time and D117 word, durable binary location, saved version/init and account facts, explicit environment, provisional limits, both probe deadlines, fresh evidence directory and separate account-choice records; ratification and the margin decision remain outstanding. The draft wrappers and nested DRAFT_NOT_AUTHORIZED word cannot authorize a run.'
details='## Evidence and boundaries\n\n'
details+=f'Branch: `codex/native-packet-builder-20261112`; final branch commit `{git(W,"rev-parse","HEAD")}`. Composition `{receipt["composition_commit"]}` uses candidate `{receipt["candidate"]}`, observer commits and helper2 head `d2efa55014e131f92733bf2c3a90c0830214dc89`; exact patch/post-image hashes are in `{receipt_path}`. Four protected branch files equal the recorded main bytes; protected post-images exist only in scratch. No conflicts were resolved.\n\n'
details+='Focused cohorts passed 1, 7 and 4 cases respectively (12 test executions, including repeated admission/guard checks). All runner outcomes report cleanup verified and no observed survivors; origin checks passed. This is not full CI, live permissions, identity authentication, quota observation or scientific acceptance. Production functions were exercised directly; the saved-step wrapper was not exercised end to end for every step.\n\n'
details+=f'Current source contract: `{json.dumps(contract,sort_keys=True)}`. The observed margin is not an owner decision. The historical map is retained; the table below supplements it against the composed source.\n\n'
details+='| Document | Outcome | Synthetic inputs and limits |\n|---|---|---|\n'
for row in rows: details+='| '+ ' | '.join(row.values())+' |\n'
details+='\n## Timestamp source and placement\n\n'
for f,line,meaning in anchors: details+=f'- `src/data_sheets_schema/{f}:{line}`: {meaning}.\n'
details+='\nThe committer timestamp remains normal Git metadata; the author date preserves the already frozen runtime value. Fractional seconds are refused rather than truncated. Capture age and margin use capture time/current clock, not commit time; word renewal requires a later authorization time. The procedure belongs to N1.9 prerequisites 4/5, before N1.5 event 1 completes; events 2/3 freeze owner terms and bundle. No normative N1 v12 change is needed; an author-date-versus-wall-clock clarification is useful. The runbook is updated with the procedure and helper2 sequence at N1.9 prerequisite 10 / N1.5 events 5–6.\n\n'
details+=f'Exact success/refusal evidence: `{rest/"timestamp-results.json"}`. Both read-only CLI modes also passed; evidence `{S/"timestamp-cli-checks.json"}`.\n\n'
details+='## Owner probe packet\n\n'
details+=f'Field-by-field values/placeholders, provenance, owner commitments, exact commands, expected files and refusal checks: `{probe/"probe-packet.DRAFT.md"}` and its JSON. The candidate documents are `{probe/"provisional-runtime.DRAFT.json"}` and `{probe/"authorization.DRAFT.json"}`. Tests confirm production readers reject these drafts.\n\n'
details+='Successful D117 probes would execute the native binary nine times: one observation, one version check and seven bound permission traces; saved validation executes it zero times. Observation uses the fixed OK prompt with a scripted loopback provider; bound permission traces can include CHORUS source/tool content locally. The version check targets a disabled loopback endpoint. No actual binary behavior or absence of unsolicited traffic has been established. The installed binary was only read and hashed; neither its updater filename nor its bytes establish an observed version or account state. No durable copy was selected or made.\n\n'
details+='## Findings and restoration\n\nH3-R1: the three CLI routes intentionally reject synthetic runtime at D106 before their account-choice validation or reservation path. Recommendation: preserve the production Max gate; a deeper public-route rehearsal needs separately authorized synthetic reservation coverage, not altered auth claims. H3-R2: latest-capture admission cannot succeed without recorded word/capture state, forbidden by this assignment; retain this explicit limit. Neither finding establishes a source defect outside this helper. Existing issue 5965 remains for complete CI; these focused tests do not settle it.\n\n'
details+=f'Test-only Git configuration was confined to `{config}` and restored byte-for-byte from its adjacent backup; restored SHA-256 `{restore["restored"]["sha256"]}`. Scratch has no remote and its tracked tree is clean. The extra sparse materialization was `data/omission_contexts`; it changes neither source HEAD nor protected content. No native process, model/provider call, capture/attempt/word reservation, sequence-start claim, push or GitHub write occurred. Synthetic saved probe claims are fixture evidence, not capture or launch reservations.\n'
value={'phase':'complete within offline/no-reservation bounds','answer':answer,'timestamp_procedure':timestamp,'owner_inputs':owner,'composition':receipt,'composition_pin':pin(receipt_path),'protected_verification':protected,'source_contract':contract,'tests':runs,'document_outcomes':rows,'document_outcomes_pin':pin(S/'full-chain-document-outcomes.json'),'timestamp':ts,'timestamp_cli_checks':pin(S/'timestamp-cli-checks.json'),'source_evidence':source_evidence,'cli_refusals':refusals,'guard_refusal':load(last/'latest-capture-refusal.json'),'admission':load(last/'admission-join.json'),'probe_drafts':probe_pins,'branch_commit':git(W,'rev-parse','HEAD'),'details_markdown':details}
assert chr(64) not in json.dumps(value)
write(S/'full-chain-final-evidence.json',value)
print(S/'full-chain-final-evidence.json')
