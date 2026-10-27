"""Pure exact tool observations resolved only through captured stream prefixes.

These checks establish internal raw-event consistency. They do not authenticate
native messages, prove model attention, or authorize any filesystem operation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema.native_shared_evidence import event


def _same(left,right):
    return c.canonical(left)==c.canonical(right)


def rows(prefix):
    if type(prefix) is not c.EvidencePrefix:
        raise ValueError('observation requires an exact captured prefix')
    result=[]
    for number,part in enumerate(prefix.raw.split(b'\n')[:-1],1):
        raw=part+b'\n'
        # Split only physical LF, not embedded Unicode line separators.
        if not raw.endswith(b'\n') or not raw.strip():
            raise ValueError('native prefix contains an incomplete or blank physical row')
        value=c.strict_json(raw,'native observed row',16*1024*1024)
        if type(value) is not dict:
            raise ValueError('native observed row is not an object')
        result.append((number,raw,value))
    return tuple(result)


def reference(prefix,line,block=None):
    lines=prefix.raw.split(b'\n')
    if type(line) is not int or not 1<=line<len(lines):
        raise ValueError('event reference exceeds the actually observed prefix')
    raw=lines[line-1]+b'\n'
    value=c.strict_json(raw,'observed frame',16*1024*1024)
    if block is not None:
        content=value.get('message',{}).get('content')
        if type(block) is not int or type(content) is not list or not 0<=block<len(content):
            raise ValueError('event block does not identify actual native content')
        value=content[block]
    return c.EventRef(prefix.stream,line,block,c.sha(raw),c.sha(c.canonical(value)))


def _frame(value,session,role=None):
    if value.get('session_id')!=session or value.get('parent_tool_use_id') is not None:
        raise ValueError('observed event belongs to a foreign or child session')
    message=value.get('message')
    if role is not None and (type(message) is not dict or message.get('role',role)!=role):
        raise ValueError('native event has a contradictory message role')
    return value


@dataclass(frozen=True)
class ToolEvidence:
    call: c.ObservedCall
    result: c.EventRef
    result_event: c.EventRef


class Trace:
    """Index complete observed prefixes without live reads or future rows.

    The final stream/control checker remains mandatory. This index establishes
    unique selected call/callback/admission/result joins for durable stage
    observations, including a currently admitted but still pending advance.
    """
    def __init__(self,transcript,control,*,session_id,policy,runtime):
        if transcript.stream!='transcript' or control.stream!='control':
            raise ValueError('observation streams have exchanged roles')
        self.transcript,self.control=transcript,control
        self.session,self.policy=session_id,policy
        initialized,*_=initialization(transcript,control,policy=policy,runtime=runtime)
        if initialized!=session_id:
            raise ValueError('supplied observation session differs from actual init')
        if type(session_id) is not str or not session_id:
            raise ValueError('observation requires actual initialized session')
        self.calls={};self.callbacks={};self.results={};self.decisions={}
        self.frames={};self.terminal=None
        callback_ids=set()
        for number,raw,value in rows(transcript):
            self.frames[number]=value
            kind=value.get('type')
            if value.get('parent_tool_use_id') is not None:
                raise ValueError('native prefix contains a child-session frame')
            if kind in ('assistant','user','result'):
                message=value.get('message')
                if value.get('model',runtime['model'])!=runtime['model'] or (
                        type(message) is dict and message.get('model',runtime['model'])!=runtime['model']):
                    raise ValueError('native event contradicts the selected model')
            if self.terminal is not None:
                raise ValueError('native events appear after terminal completion')
            if kind=='control_cancel_request':
                raise ValueError('native callback cancellation is terminal')
            if kind=='result':
                _frame(value,self.session)
                self.terminal=number
            if kind in ('assistant','user'):
                _frame(value,self.session,kind)
                content=value['message'].get('content')
                if type(content) is not list:
                    raise ValueError('native content is not an observed block list')
                for offset,item in enumerate(content):
                    if type(item) is not dict:
                        raise ValueError('native message contains an untyped block')
                    identity=item.get('id') if item.get('type')=='tool_use' else item.get('tool_use_id')
                    if item.get('type')=='tool_use':
                        if (kind!='assistant' or type(identity) is not str or not identity or identity in self.calls
                                or item.get('name') not in ('Read','Write','Bash') or type(item.get('input')) is not dict):
                            raise ValueError('native tool call has ambiguous identity or input')
                        self.calls[identity]=(number,offset,item)
                    elif item.get('type')=='tool_result':
                        if (kind!='user' or identity not in self.calls or identity in self.results
                                or self.calls[identity][0]>=number):
                            raise ValueError('native result lacks its unique preceding call')
                        self.results[identity]=(number,offset,item)
            if kind=='control_request':
                request=value.get('request');data=request.get('input') if type(request) is dict else None
                if type(data) is not dict:
                    raise ValueError('observed callback input is malformed')
                identity=data.get('tool_use_id');callback=value.get('request_id')
                if (identity not in self.calls or identity in self.callbacks or identity in self.results
                        or type(callback) is not str or not callback or callback in callback_ids
                        or request.get('subtype')!='hook_callback'
                        or request.get('callback_id')!=policy['pretool_control']['callback_id']
                        or request.get('tool_use_id') not in (None,identity)
                        or data.get('hook_event_name')!=policy['pretool_control']['event']
                        or data.get('cwd')!=policy['readonly_lookups']['repository']
                        or data.get('session_id',session_id)!=session_id):
                    raise ValueError('callback differs from its current initialized tool call')
                call=self.calls[identity]
                if (call[0]>=number or data.get('tool_name')!=call[2]['name']
                        or not _same(data.get('tool_input'),call[2]['input'])):
                    raise ValueError('callback input differs in spelling, value or type from its observed call')
                self.callbacks[identity]=(number,value);callback_ids.add(callback)
        for number,raw,value in rows(control):
            if value.get('kind')!='decision':continue
            request=value.get('request');data=request.get('request',{}).get('input',{}) if type(request) is dict else {}
            identity=data.get('tool_use_id')
            if (identity not in self.callbacks or identity in self.decisions
                    or not _same(request,self.callbacks[identity][1])
                    or value.get('classification') not in ('prescribed','not_prescribed')
                    or type(value.get('basis')) is not str):
                raise ValueError('parent decision has no unique exact observed callback')
            classification,basis=value['classification'],value['basis']
            output={} if classification=='prescribed' else {'hookSpecificOutput':{
                'hookEventName':'PreToolUse','permissionDecision':'deny',
                'permissionDecisionReason':'Outside the registered tool policy: '+basis}}
            expected={'type':'control_response','response':{'subtype':'success',
                'request_id':request['request_id'],'response':output}}
            if not _same(value.get('response'),expected):
                raise ValueError('parent decision response contradicts its classification')
            self.decisions[identity]=(number,value)

    def request(self,identity):
        if identity not in self.calls or identity not in self.callbacks:
            raise ValueError('tool lacks an observed call and callback')
        line,offset,call=self.calls[identity]
        return c.ObservedToolRequest(call=reference(self.transcript,line,offset),
            callback=reference(self.transcript,self.callbacks[identity][0]),
            input_json=c.canonical(call['input']),session_id=self.session,
            tool_name=call['name'],tool_use_id=identity)

    def admitted(self,identity):
        request=self.request(identity)
        if identity not in self.decisions or self.decisions[identity][1]['classification']!='prescribed':
            raise ValueError('tool has no exact parent admission')
        return c.ObservedCall(call=request.call,callback=request.callback,
            admission=reference(self.control,self.decisions[identity][0]),input_json=request.input_json,
            session_id=request.session_id,tool_name=request.tool_name,tool_use_id=identity)

    def settled(self,identity):
        admitted=self.admitted(identity)
        if identity not in self.results:
            raise ValueError('observed tool remains pending')
        line,offset,_=self.results[identity]
        if line<=self.callbacks[identity][0]:
            raise ValueError('tool result precedes its callback')
        return ToolEvidence(admitted,reference(self.transcript,line,offset),reference(self.transcript,line))

    def pending(self):
        return tuple(identity for identity in self.calls if identity not in self.results)

    def current_advance(self,identity,command):
        admitted=self.admitted(identity)
        inputs=c.strict_json(admitted.input_json,'advance input',c.HARD_LIMITS['request_bytes'])
        if (self.pending()!=(identity,) or admitted.tool_name!='Bash' or inputs.get('command')!=command
                or self.terminal is not None):
            raise ValueError('advance is not the sole pending exact admitted helper')
        return admitted


def _successful(trace,evidence):
    if type(evidence) is not ToolEvidence:
        raise ValueError('result check requires exact settled tool evidence')
    actual=trace.settled(evidence.call.tool_use_id)
    if actual!=evidence:
        raise ValueError('result reference differs from fresh captured event joins')
    block=event(trace.transcript,evidence.result)
    frame=event(trace.transcript,evidence.result_event)
    metadata=frame.get('tool_use_result')
    if (block.get('is_error',False) is not False or type(metadata) is not dict
            or metadata.get('error') is not None
            or metadata.get('interrupted',False) is not False
            or any(metadata.get(k) is not None for k in ('backgroundTaskId','background_task_id','persistedOutputPath'))):
        raise ValueError('tool result is errored, interrupted, partial or backgrounded')
    exits=[metadata[k] for k in ('exitCode','exit_code') if k in metadata]
    if any(type(value) is not int or value!=0 for value in exits):
        raise ValueError('tool result has contradictory or unsuccessful exit metadata')
    return block,frame,metadata


def complete_request_read(trace,evidence,request):
    """Require the whole exact current outer request in the actual Read result."""
    if type(request) is not c.CapturedArtifact or evidence.call.tool_name!='Read':
        raise ValueError('current request requires its exact captured Read')
    if c.strict_json(evidence.call.input_json)!={'file_path':request.pin.path}:
        raise ValueError('current request Read is ranged or names another path')
    block,frame,metadata=_successful(trace,evidence)
    text=request.raw.decode('utf-8');lines=text.split('\n')
    rendered='\n'.join(f'{index}\t{line}' for index,line in enumerate(lines,1))
    expected={'filePath':request.pin.path,'content':text,'numLines':len(lines),'startLine':1,'totalLines':len(lines)}
    if (metadata.get('type')!='text' or not _same(metadata.get('file'),expected)
            or block.get('content')!=rendered):
        raise ValueError('Read did not deliver the complete exact current request')
    return evidence


def first_response_write(trace,evidence,response,*,intent_input_json):
    """Require a successful first create with exact intent and captured bytes."""
    if type(response) is not c.CapturedArtifact or evidence.call.tool_name!='Write':
        raise ValueError('response requires its exact captured first Write')
    expected={'file_path':response.pin.path,'content':response.raw.decode('utf-8')}
    if not _same(c.strict_json(evidence.call.input_json,max_bytes=c.HARD_LIMITS['request_bytes']),expected) or evidence.call.input_json!=intent_input_json:
        raise ValueError('response bytes differ from the original admitted Write intent')
    block,frame,metadata=_successful(trace,evidence)
    if (metadata.get('type')!='create' or metadata.get('filePath')!=response.pin.path
            or metadata.get('content')!=expected['content'] or metadata.get('originalFile') is not None
            or metadata.get('userModified',False) is not False or metadata.get('structuredPatch',[])!=[]
            or block.get('content')!='File created successfully at: '+response.pin.path):
        raise ValueError('response was not the exact successful first file creation')
    return evidence


def helper_result(trace,evidence,expected):
    """A helper acknowledges its exact typed publication in both result channels."""
    if evidence.call.tool_name!='Bash':
        raise ValueError('stage publication acknowledgement is not a Bash helper')
    block,frame,metadata=_successful(trace,evidence)
    for value in (block.get('content'),metadata.get('stdout')):
        if type(value) is not str or not _same(c.strict_json(value.encode(),'helper result',c.HARD_LIMITS['metadata_record_bytes']),expected):
            raise ValueError('helper acknowledgement differs from actual published effects')
    if metadata.get('stderr','')!='':
        raise ValueError('stage helper stderr contradicts successful publication')
    return evidence


def initialization(transcript,control,*,policy,runtime):
    """Bind actual ordered initialization to the selected runtime and policy."""
    native=list(rows(transcript));parent=list(rows(control))
    sent=[row for row in parent if row[2].get('kind')=='initialize_sent']
    acknowledgements=[row for row in parent if row[2].get('kind')=='initialize_ack']
    replies=[row for row in native if row[2].get('type')=='control_response']
    initialized=[row for row in native if row[2].get('type')=='system' and row[2].get('subtype')=='init']
    if len(sent)!=1 or len(acknowledgements)!=1 or len(replies)!=1 or len(initialized)!=1:
        raise ValueError('native initialization is missing, duplicate or contradictory')
    contract=policy['pretool_control'];identity='d4d_initialize_v1'
    expected={'type':'control_request','request_id':identity,'request':{'subtype':'initialize',
        'hooks':{contract['event']:[{'matcher':contract['matcher'],'hookCallbackIds':[contract['callback_id']],
            'timeout':contract['runtime_callback_timeout_seconds']}]}}}
    policy_sha=c.sha(json.dumps(policy,sort_keys=True,separators=(',',':')).encode())
    ack=replies[0][2];init=initialized[0][2]
    if (not _same(sent[0][2].get('frame'),expected) or sent[0][2].get('policy_sha256')!=policy_sha
            or not _same(acknowledgements[0][2].get('frame'),ack)
            or sent[0][0]>=acknowledgements[0][0] or replies[0][0]>=initialized[0][0]
            or type(ack.get('response')) is not dict or ack['response'].get('subtype')!='success'
            or ack['response'].get('request_id')!=identity or ack['response'].get('error') is not None):
        raise ValueError('native initialization does not bind the selected callback policy')
    session=init.get('session_id')
    if (type(session) is not str or not session or init.get('parent_tool_use_id') is not None
            or init.get('cwd')!=policy['readonly_lookups']['repository']
            or init.get('model')!=runtime['model']
            or init.get('claude_code_version')!=runtime['executable']['init_version']
            or init.get('apiKeySource')!=runtime['auth']['expected_api_key_source']
            or type(init.get('tools')) is not list or any(type(tool) is not str for tool in init['tools'])
            or len(init['tools'])!=len(set(init['tools'])) or not {'Bash','Read','Write'}<=set(init['tools'])):
        raise ValueError('native init differs from selected runtime, route or file tools')
    if any(row[0]<initialized[0][0] and row[2].get('type') in ('assistant','user','control_request','result') for row in native):
        raise ValueError('tool/session evidence precedes actual initialized runtime')
    return session,reference(control,sent[0][0]),reference(transcript,replies[0][0]),reference(transcript,initialized[0][0])
