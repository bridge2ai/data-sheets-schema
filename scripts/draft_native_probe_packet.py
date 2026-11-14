#!/usr/bin/env python3
"""D117 owner DRAFT generator, 2026-11-12. Explicit source/binary -> NEW output.
Read source constants and binary bytes only; never execute a binary, probe,
provider, reservation or owner act. Draft wrappers intentionally fail wire shape.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

LABEL='DRAFT ONLY — NOT AUTHORIZED — NOT A RUNTIME OR PROBE AUTHORIZATION'


def generate(source, binary, output):
    source=Path(source); binary=Path(binary); output=Path(output)
    for path in (source,binary):
        if not path.is_absolute() or path.resolve(strict=True)!=path: raise ValueError('physical absolute input required')
    if not output.is_absolute() or output.resolve()!=output: raise ValueError('physical absolute output required')
    output.mkdir(exist_ok=False)
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(source/'src'))
    from data_sheets_schema.native_shared_runtime_values import executable_identity
    binary_pin=executable_identity(str(binary))
    facts=[]
    def constant(module,name):
        path=source/'src/data_sheets_schema'/(module+'.py')
        for node in ast.parse(path.read_bytes()).body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
                value=ast.literal_eval(node.value)
                facts.append({'module':module,'constant':name,'path':str(path),'line':node.lineno,'value':value,
                              'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                return value
        raise ValueError('missing source constant '+module+'.'+name)
    def constraint(module,function,field):
        path=source/'src/data_sheets_schema'/(module+'.py')
        fn=next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==function)
        found=[]
        for node in ast.walk(fn):
            if (isinstance(node,ast.Compare) and isinstance(node.left,ast.Subscript)
                    and isinstance(node.left.slice,ast.Constant) and node.left.slice.value==field
                    and len(node.comparators)==1 and isinstance(node.comparators[0],ast.Constant)
                    and isinstance(node.ops[0],(ast.Eq,ast.NotEq))):
                found.append((node.comparators[0].value,node.lineno))
        if len({x[0] for x in found})!=1: raise ValueError('ambiguous source constraint '+field)
        value,line=found[0]
        facts.append({'module':module,'function':function,'field':field,'path':str(path),'line':line,'value':value,
                      'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        return value
    route=constant('native_shared_runtime_values','ROUTE')
    requested=constant('native_model_aliases','REQUESTED'); returned=constant('native_model_aliases','RETURNED')
    basis_kind=constant('native_model_aliases','PROVISIONAL_KIND')
    effort=constant('native_permission_probe','U4_EFFORT')
    budget,deadline=constant('native_run_limits','CANARY')
    terms=constant('native_u4b_policy','TERM_VALUES')
    auth_kind=constant('native_u4b_probe_sequence','AUTH_KIND')
    provider=constant('native_u4b_probe_sequence','PROVIDER')
    protocol=constant('native_u4b_probe_sequence','PERMISSION_PROTOCOL')
    prompt=constant('native_u4b_probe_sequence','PROMPT')
    stops=constant('native_shared_permissions','STOPS')
    current_kind=constant('native_launch_review','CURRENT_KIND')
    current_terms=constant('native_launch_review','CURRENT_TERMS_KIND')
    provisional_version=constraint('native_u4b_probe_sequence','validate_provisional_runtime','version')
    authorization_version=constraint('native_u4b_probe_sequence','authorization','version')
    fields=[]
    def field(name,value,origin,status):
        fields.append({'field':name,'draft_value':value,'origin':origin,'status':status}); return value
    owner='OWNER_INPUT_REQUIRED'
    runtime={
        'route':field('runtime.route',route,'native_shared_runtime_values.ROUTE','source'),
        'executable':{'path':field('runtime.executable.path',owner+': durable physical copy outside updater','owner-selected durable path; not installed updater path','owner'),
            'sha256':field('runtime.executable.sha256',binary_pin['sha256'],'installed binary bytes, production executable_identity; applies to durable copy only if independently verified identical','read bytes'),
            'version':field('runtime.executable.version','SAVED_REAL_VERSION_REQUIRED','saved authorized version output; filename is not evidence','later observation'),
            'init_version':field('runtime.executable.init_version','SAVED_INIT_VERSION_REQUIRED','saved authorized init frame; cannot execute to discover it here','later observation')},
        'model':field('runtime.model',requested,'native_model_aliases.REQUESTED','source'),
        'auxiliary_models':field('runtime.auxiliary_models',[],'validate_provisional_runtime requires empty list','source'),
        'effort':field('runtime.effort',effort,'native_permission_probe.U4_EFFORT','source'),
        'limits':{'contextWindow':field('runtime.limits.contextWindow',owner+': positive provisional integer','owner provisional declaration; observation will replace with terminal limits','owner'),
                  'maxOutputTokens':field('runtime.limits.maxOutputTokens',owner+': positive integer no greater than contextWindow','owner provisional declaration; observation will replace it','owner')},
        'limits_basis':field('runtime.limits_basis',json.dumps({'kind':basis_kind,'version':provisional_version,'model_aliases':{'requested':requested,'returned':returned}},sort_keys=True,separators=(',',':')),'provisional basis shape checked by validate_provisional_runtime; no observation pin yet','source'),
        'provider':field('runtime.provider',owner+': explicit registered provider label','owner/runtime declaration; probe transport separately forced to loopback','owner'),
        'auth':{'loggedIn':field('runtime.auth.loggedIn',owner+': confirm true from actual authorized account evidence','validate_runtime requires true; no account queried','owner/later observation'),
                'authMethod':field('runtime.auth.authMethod','claude.ai','validate_runtime required value; owner must verify account actually matches','owner/later observation'),
                'apiProvider':field('runtime.auth.apiProvider','firstParty','validate_runtime required value; not observed here','owner/later observation'),
                'subscriptionType':field('runtime.auth.subscriptionType','max','validate_provisional_runtime required Max selection; D105/D106 owner intent','owner'),
                'expected_api_key_source':field('runtime.auth.expected_api_key_source','none','validate_runtime required production-account expectation; local probe injects an inert test key','owner')},
        'environment':{key:field('runtime.environment.'+key,value,origin,status) for key,value,origin,status in [
            ('PATH',owner+': colon-separated absolute paths','owner explicit PATH; no environment inherited','owner'),
            ('HOME',owner+': absolute account home','owner explicit registered home; not read for account state','owner'),
            ('PYSTOW_HOME',owner+': exact registered attempt directory / helper-cache','native_helper_cache.for_attempt; fresh per-attempt helper cache','owner'),
            ('BASH_DEFAULT_TIMEOUT_MS','600000','registered native Bash helper timeout','source'),
            ('BASH_MAX_TIMEOUT_MS','600000','registered native Bash helper maximum timeout','source'),
            ('CLAUDE_SECURESTORAGE_CONFIG_DIR',owner+': explicit value, possibly empty','owner registered secure-storage choice','owner'),
            ('CLAUDE_CODE_DISABLE_1M_CONTEXT','0','validate_provisional_runtime fixed 1M selection','source')]},
        'deadline_seconds':field('runtime.deadline_seconds',deadline,'native_run_limits.CANARY complete registered pair; owner approval still required','source/owner'),
        'budget_guard_usd':field('runtime.budget_guard_usd',budget,'native_run_limits.CANARY complete registered pair, not inferred billing','source/owner'),
        'keep_awake':{'policy':field('runtime.keep_awake.policy','macos_iokit_ims_v1','validate_runtime_terms required policy, subject to owner ratification','source/owner'),
                      'host_platform':field('runtime.keep_awake.host_platform','darwin','validate_runtime_terms required platform; no host gate measured here','source/owner'),
                      'basis':field('runtime.keep_awake.basis',owner+': actual host/AC/lid confirmation','owner attestation; no keep-awake acquisition performed','owner')}}
    authorization={'kind':field('authorization.kind',auth_kind,'native_u4b_probe_sequence.AUTH_KIND','source'),
        'version':field('authorization.version',authorization_version,'authorization exact version check','source'),
        'owner':field('authorization.owner',owner+': owner identity','actual owner, not fixture identity','owner'),
        'authorized_at':field('authorization.authorized_at',owner+': actual strict UTC instant','actual owner act; never generated from a guessed date','owner'),
        'word':field('authorization.word','DRAFT_NOT_AUTHORIZED','must be replaced ONLY by owner act granting AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES','owner'),
        'directory':field('authorization.directory',owner+': fresh physical evidence directory','owner-approved directory outside source and executable, existing parent','owner'),
        'provisional_runtime_sha256':field('authorization.provisional_runtime_sha256','FINAL_RUNTIME_BYTES_REQUIRED','hash only finalized canonical runtime, never this draft wrapper','later finalization'),
        'observation_deadline_seconds':field('authorization.observation_deadline_seconds',owner+': integer 1..min(600, runtime deadline)','authorization bound; commits to one observation deadline','owner'),
        'permission_deadline_seconds':field('authorization.permission_deadline_seconds',owner+': integer 1..min(600, runtime deadline)','one shared phase deadline covering version plus all traces','owner'),
        'provider':field('authorization.provider',provider,'native_u4b_probe_sequence.PROVIDER','source'),
        'permission_protocol':field('authorization.permission_protocol',protocol,'native_u4b_probe_sequence.PERMISSION_PROTOCOL','source')}
    documents={
        'provisional-runtime.DRAFT.json':{'kind':'DRAFT_NOT_A_RUNTIME','scope':LABEL,'candidate_runtime':runtime},
        'authorization.DRAFT.json':{'kind':'DRAFT_NOT_AN_AUTHORIZATION','scope':LABEL,'candidate_authorization':authorization}}
    packet={'scope':LABEL,'project':'CHORUS','arm':'BASELINE (input documents only)',
        'installed_binary_read_only':binary_pin,'binary_filename_not_version_evidence':binary.name,
        'fields':fields,'source_facts':facts,'running_source_contract':{'review_kind':current_kind,'terms_kind':current_terms,'admission_terms':terms},
        'owner_actions':[
            'Ratify required N1 items; the pre-reservation margin remains undecided. Source value is reported, not selected by this draft.',
            'Choose and approve durable binary copy, explicit account/home/storage/PATH, and actual version/auth evidence; hashing installed bytes does not approve their use.',
            'Supply provisional positive limits and both phase deadlines; final limits and thinking must come from saved observation output.',
            'Choose a fresh evidence directory; a failed claimed phase cannot be silently retried in a new directory.',
            'Supply owner identity, actual UTC authorization time and exact D117 word after reviewing final runtime hash and execution count.',
            'Supply separate D105/D106 account-choice bytes for observation runtime and later bound expectation; neither is account authentication.'],
        'commands':[
            'python -P -B -m data_sheets_schema.native_generation observation-probe --authorization /ABS/authorization.json --runtime /ABS/provisional-runtime.json --account-choice /ABS/observation-account-choice.json',
            'python -P -B -m data_sheets_schema.native_generation bound-permission-probe --authorization /ABS/authorization.json --expectation /ABS/expectation.json --account-choice /ABS/permission-account-choice.json',
            'python -P -B -m data_sheets_schema.native_generation validate-probe-sequence --runtime /ABS/final-runtime.json --probe /ABS/permission/permission-probe.json --account-choice /ABS/final-runtime-account-choice.json'],
        'execution_count':{'observation_native_processes':1,'bound_version_processes':1,'bound_trace_processes':1+len(stops),'successful_total':3+len(stops),'traces':['settled',*['stop-'+x for x in stops]],'readback_native_processes':0},
        'provider_scope':{'observation':'One successful model request containing fixed prompt '+repr(prompt)+' and CLI-generated system/request metadata, captured by scripted loopback provider; no CHORUS input supplied by observation invocation.',
            'version':'--version uses disabled endpoint http://127.0.0.1:1 and inert key, no model request intended.',
            'bound':'Seven scripted local-provider conversations, including returned tool results and selected source snippets; CHORUS/source bytes can reach the LOCAL scripted provider and retained traces. Do not call this content-free. No external model endpoint is configured; actual binary compliance remains unobserved.',
            'account':'Isolated config and inert local key; no intended account subscription usage. These settings are not evidence of a real account or of absence of unsolicited binary networking.'},
        'saved_outputs':{'observation':['authorization.json','provisional-runtime.json','observation-claim.json','observation/invocation.json','observation/requests/','observation/native_request.json','observation/transcript.jsonl','observation/observation.json','observation/stdout.jsonl','observation/stderr.txt','observation/failure.json on failure'],
            'bound':['bound-claim.json','expectation.json','permission/version.stdout','permission/version.stderr','permission/captured/','permission/verification.json','permission/transport-provider.py','permission/producer-evidence.json','permission/permission-probe.json','sequence.json']},
        'checks_and_refusals':['Closed canonical authorization JSON, exact kind/version/word/provider/protocol; unknown or draft wrapper fields refuse.',
            'Strict owner text and UTC timestamp; source validates syntax and bindings, not human authentication. No freshness/future-time comparison is performed by authorization itself.',
            'Complete closed runtime: physical executable and matching hash, explicit model aliases, high effort, Max declaration, 1M flag 0, budget string 90, positive limits, explicit environment without credential/redirect overrides.',
            'Authorization hashes exact canonical provisional runtime; deadlines are positive integers no greater than min(600, runtime deadline).',
            'Evidence directory is physical and disjoint from source/executable; observation requires existing parent and exclusive new directory.',
            'Bound phase requires saved observation, exact same authorization bytes and consistent final runtime; validates current expectation then creates exclusive bound claim before version/trace execution.',
            'Binary mutation, wrong version, missing/contradictory transcript/request/limits/thinking, failed cleanup, deadline/byte overflow, failed trace or source change stops; failed phase stays spent.'],
        'no_execution':True}
    documents['probe-packet.DRAFT.json']=packet
    for name,value in documents.items():
        with (output/name).open('x') as stream: json.dump(value,stream,indent=2,ensure_ascii=False); stream.write('\n')
    lines=['# D117 owner packet — DRAFT, not authorization','',LABEL,'',
           'The installed binary was read and hashed, never executed. Its updater filename is not an observed version. The durable copy has not been selected or created.','',
           '| Field | Draft value | Origin | Status |','|---|---|---|---|']
    for row in fields: lines.append('| '+row['field']+' | `'+json.dumps(row['draft_value'],ensure_ascii=False)+'` | '+row['origin']+' | '+row['status']+' |')
    lines+=['','Owner acts required:','']+['- '+x for x in packet['owner_actions']]
    lines+=['','Exact covered CLI commands (documentation only):','','```sh',*packet['commands'],'```','',
            'Successful path native execution count: '+str(packet['execution_count']['successful_total'])+' (one observation, one version check, '+str(1+len(stops))+' traces). Failures can stop earlier; there is no authorized retry. Saved validation executes no native process.','']
    for key,value in packet['provider_scope'].items(): lines += [key+': '+value,'']
    lines+=['Source checks and refusal conditions:','']+['- '+x for x in packet['checks_and_refusals']]
    lines+=['','Saved files: `'+json.dumps(packet['saved_outputs'])+'`.','',
            'Both draft wrappers and the nested authorization word are intentionally invalid. Finalization requires an explicit owner act and fresh production validation. Do not pass these DRAFT files to a producer.']
    with (output/'probe-packet.DRAFT.md').open('x') as stream: stream.write('\n'.join(lines)+'\n')
    print(json.dumps({'output':str(output),'binary_read_only':binary_pin,'native_executions':0,'files':sorted(documents)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True); p.add_argument('--binary',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); generate(a.source_root,a.binary,a.output)
