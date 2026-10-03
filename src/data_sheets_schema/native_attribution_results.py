"""Versioned offline native attribution replay; no launcher or generation acceptance.

All semantic checks consume captured bytes. The capture stage verifies the
current source authority and records current file metadata, which is not proof
of a superseded intermediate file. Historical controller helpers stay frozen.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import source_attribution_preflight as preflight
from data_sheets_schema import evidence_assertions as evidence

VERSION = 1
INSTRUMENT = 'native attribution saved-trace finalization v1'
SCOPE = 'Additional declared attribution/control evidence only; not full generation acceptance, provider authentication or launch authorization.'


def _rows(raw, label):
    rows = []
    for number, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        if not line.strip():
            raise ValueError(f'{label} has a blank physical record at line {number}')
        value = draft._json(line)
        if type(value) is not dict:
            raise ValueError(f'{label} record {number} is not an object')
        rows.append(value)
    if not rows:
        raise ValueError(f'{label} is empty')
    return rows


class Capture:
    """Read each resolved file once; never fall back to live reads after sealing."""
    def __init__(self, root):
        self.root = Path(root)
        self.aliases, self.metadata, self.raw = {}, {}, {}
        self.alias_metadata = {}
        self.roles = {}
        self.sealed = False

    def path(self, value):
        if not isinstance(value, (str, Path)) or not str(value).strip() or '\0' in str(value):
            raise ValueError('missing or malformed captured path')
        literal = Path(value)
        literal = literal if literal.is_absolute() else self.root / literal
        key = str(literal)
        if key not in self.aliases:
            if self.sealed:
                raise ValueError('replay requested an uncaptured path')
            target = literal.resolve()
            self.aliases[key] = str(target)
            self.alias_metadata[key] = {'symlink': literal.is_symlink()}
            if str(target) not in self.metadata:
                try:
                    info = target.stat()
                    self.metadata[str(target)] = {'exists': True, 'regular': stat.S_ISREG(info.st_mode),
                        'links': info.st_nlink, 'device': info.st_dev, 'inode': info.st_ino,
                        'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
                except FileNotFoundError:
                    self.metadata[str(target)] = {'exists': False, 'regular': False}
            self.aliases.setdefault(str(target), str(target))
            self.alias_metadata.setdefault(str(target), {'symlink': False})
        return Path(self.aliases[key])

    def read(self, value, role):
        path = self.path(value)
        key = str(path)
        self.roles.setdefault(key, set()).add(role)
        if key not in self.raw:
            if self.sealed:
                raise ValueError('replay requested uncaptured bytes')
            if not self.metadata[key]['regular']:
                raise ValueError(f'{role} is not a regular file')
            with path.open('rb') as stream:
                before = os.fstat(stream.fileno())
                raw = stream.read()
                after = os.fstat(stream.fileno())
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
            if any(getattr(before, k) != getattr(after, k) for k in fields) or len(raw) != before.st_size:
                raise ValueError(f'{role} changed during capture')
            meta = self.metadata[key]
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    meta['device'], meta['inode'], meta['size'], meta['mtime_ns']):
                raise ValueError(f'{role} metadata changed during capture')
            self.raw[key] = raw
        return self.raw[key]

    def identity(self):
        return {path: {'sha256': draft._sha(raw), 'bytes': len(raw), 'roles': sorted(self.roles[path])}
                for path, raw in sorted(self.raw.items())}

    def verify_unchanged(self):
        """Publication guard only: checks still use the immutable captured bytes."""
        for path, raw in self.raw.items():
            if Path(path).read_bytes() != raw:
                raise ValueError('captured input changed before report publication')
        for original, target in self.aliases.items():
            if str(Path(original).resolve()) != target:
                raise ValueError('captured path identity changed before report publication')
            if Path(original).is_symlink() != self.alias_metadata[original]['symlink']:
                raise ValueError('captured path metadata changed before report publication')
        for path, expected in self.metadata.items():
            try:
                info = Path(path).stat()
                current = {'exists': True, 'regular': stat.S_ISREG(info.st_mode), 'links': info.st_nlink,
                    'device': info.st_dev, 'inode': info.st_ino, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
            except FileNotFoundError:
                current = {'exists': False, 'regular': False}
            if current != expected:
                raise ValueError('captured file metadata changed before report publication')


def _final_evidence(snapshot, spec):
    """Byte-only equivalent of the selected native evidence checker consumer."""
    paths = spec._agentic_artifact_paths
    directory = Path(paths['core']).parent / 'evidence'
    artifacts = {'original_full': directory/'original_full.yaml', 'original_core': directory/'original_core.yaml',
                 'final_full': Path(paths['full']), 'final_core': Path(paths['core'])}
    raws = {key: snapshot.read(path, key) for key, path in artifacts.items()}
    texts = {key: raw.decode('utf-8') for key, raw in raws.items()}
    protocol = evidence.protocol_for_renderer(spec.render_version)
    source_raw = snapshot.read(spec.manifest, 'source_manifest') if spec.manifest_used else None
    authority = {'source_manifest_raw': source_raw, 'project': spec.project} if protocol in (5, 6, 7) else {}
    evidence._review_authority(protocol, spec.manifest if spec.manifest_used else None,
                               spec.project if spec.manifest_used else None)
    chunks, pins = evidence.source_chunks_from_bytes(snapshot.read(spec.bundle, 'bundle'),
        snapshot.read(spec.chunk_manifest, 'chunk_manifest'))
    audit_raw = snapshot.read(directory/'audit.json', 'audit')
    audit = evidence.load_json(audit_raw)
    from data_sheets_schema.api_runner import _audit_shape_problem
    shape = _audit_shape_problem(audit) if isinstance(audit, dict) else 'audit must be an object'
    if shape:
        raise ValueError(shape)
    out = evidence.check_audit(audit, artifacts={k:v for k,v in texts.items() if k.startswith('original_')},
                               chunks=chunks, protocol_version=protocol, **authority)
    if source_raw is not None:
        pins['source_manifest'] = draft._sha(source_raw)
    pins['audit'] = draft._sha(audit_raw)
    pins.update({key: draft._sha(raw) for key, raw in raws.items()})
    out['findings'] += evidence.check_relationship_removals(audit, evidence.load_record(texts['original_full']),
        evidence.load_record(texts['final_full']), protocol_version=protocol, original_raw=raws['original_full'])
    report_raw = snapshot.read(paths['report'], 'report')
    pins['report'] = draft._sha(report_raw)
    try:
        checked = evidence.check_report(report_raw.decode('utf-8'), artifacts=texts, chunks=chunks,
                                         protocol_version=protocol, **authority)
        out['assertions_checked'] += checked['assertions_checked']
        out['findings'] += checked['findings']
        if 'source_review_final' in checked:
            out['source_review_final'] = checked['source_review_final']
    except (ValueError, UnicodeError) as exc:
        out['findings'].append(evidence._problem('evidence_contract', str(exc)))
    out['artifact_sha256'] = pins
    out['scope'] = 'Declared evidence only; semantic support and omitted claims require independent review.'
    return out


class CapturedDraft(draft.NativeAttributionState):
    def __init__(self, registration_raw, snapshot):
        super().__init__(registration_raw, live=True)
        self.snapshot = snapshot
        self.final_check = False
        self.commands = draft._commands(self.spec)
        self.actual_preflight = None

    def _command_kind(self, command):
        return draft.command_kind(command, self.spec, expected=self.commands)

    def _target_path(self, path):
        return self.snapshot.path(path)

    def _check_current(self, problems):
        # Intermediate passes may legitimately name superseded report bytes.
        if not self.final_check:
            return
        current = self.actual_preflight
        if current is None:
            raise ValueError('draft checker result was not captured before sealing')
        if not current['passed'] or draft._encoded(current) != draft._encoded(self.accepted['payload']):
            problems.append('draft pass differs from actual checker on captured saved bytes')
        else:
            self.accepted['observation']['verified_against_current_saved_bytes'] = True

    def compute_preflight(self):
        if self.snapshot.sealed:
            raise ValueError('semantic checks must be captured before sealing')
        spec = self.spec
        args = {'report_raw': self.snapshot.read(spec._agentic_artifact_paths['report'], 'report'),
                'record_raw': self.snapshot.read(spec._agentic_artifact_paths['full'], 'final_full'),
                'bundle_raw': self.snapshot.read(spec.bundle, 'bundle'),
                'chunk_manifest_raw': self.snapshot.read(spec.chunk_manifest, 'chunk_manifest'),
                'protocol_version': evidence.protocol_for_renderer(spec.render_version)}
        if spec.manifest_used:
            args.update(source_manifest_raw=self.snapshot.read(spec.manifest, 'source_manifest'), project=spec.project)
        self.actual_preflight = preflight.check_bytes(**args)

    def finish(self):
        self.final_check = True
        return self.report(complete=True)


class CapturedFiles:
    """The frozen file policy's unbounded branch over captured metadata only.

    Compositions v1 do not select bounded-read/write policies. Those policies
    require their own reviewed replay version rather than a permissive fallback.
    """
    def __init__(self, snapshot, policy, controls, config_root=None):
        self.snapshot = snapshot
        paths = policy['readonly_lookups']
        if paths.get('bounded_reads') or paths.get('write_paths') is not None:
            raise ValueError('bounded file policy is unsupported by saved replay v1')
        self.root = Path(paths['repository'])
        self.inputs = {Path(p) for p in paths['inputs']}
        self.outputs = [Path(p) for p in paths['output_directories']]
        self.config = snapshot.path(config_root) if config_root else None
        self.session, self.persisted = None, {}
        self.BudgetStop = controls['budgeted_cborg'].BudgetStop

    def target(self, value):
        return self.snapshot.path(value)

    def matches(self, tool, original, callback):
        if tool == 'Bash':
            return draft._encoded(original) == draft._encoded(callback)
        left, right = dict(original), dict(callback)
        try:
            one, two = self.target(left.pop('file_path')), self.target(right.pop('file_path'))
        except (OSError, ValueError, RuntimeError, KeyError):
            return False
        return one == two and draft._encoded(left) == draft._encoded(right)

    def classify(self, tool, payload):
        try:
            target = self.target(payload.get('file_path'))
            meta = self.snapshot.metadata[str(target)]
            if tool == 'Read' and target in self.inputs:
                return 'prescribed', 'a registered input the instruction reads'
            if any(folder in target.parents for folder in self.outputs):
                if meta['exists'] and (not meta['regular'] or meta['links'] != 1):
                    return 'not_prescribed', 'an output target that is not a single-link regular file'
                if target in self.inputs:
                    return 'not_prescribed', 'a registered input cannot be overwritten'
                return 'prescribed', 'a file inside the registered output directories'
            if tool == 'Read' and str(target) in self.persisted:
                if self.fingerprint(target) != self.persisted[str(target)]['file']:
                    raise self.BudgetStop('native persisted tool output changed before its read')
                return 'prescribed', 'an unchanged persisted result from this native session'
        except self.BudgetStop:
            raise
        except (OSError, ValueError, RuntimeError) as error:
            raise self.BudgetStop('native file target could not be resolved') from error
        return 'not_prescribed', 'a path outside the registered inputs and outputs'

    def fingerprint(self, path):
        target = self.target(path)
        meta = self.snapshot.metadata[str(target)]
        if target != Path(path) or not meta['regular'] or meta['links'] != 1:
            raise self.BudgetStop('native persisted output is not a single-link regular file')
        raw = self.snapshot.read(path, 'persisted_output')
        return {'bytes': len(raw), 'sha256': draft._sha(raw)}

    def observe(self, event, calls, decisions):
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            session = event.get('session_id')
            if (self.session is not None or event.get('cwd') != str(self.root) or
                    not isinstance(session, str) or not re.fullmatch(r'[0-9a-f-]{36}', session)):
                raise self.BudgetStop('native file policy has ambiguous session identity')
            self.session = session
        metadata = event.get('tool_use_result')
        if not isinstance(metadata, dict) or 'persistedOutputPath' not in metadata:
            return None
        try:
            if event.get('type') != 'user' or self.config is None or self.session is None:
                raise ValueError('persisted result outside an initialized native session')
            if event.get('session_id') != self.session:
                raise ValueError('persisted result belongs to another session')
            blocks = event['message']['content']
            if not isinstance(blocks, list) or len(blocks) != 1:
                raise ValueError('ambiguous persisted result')
            block = blocks[0]
            identity = block['tool_use_id']
            if (block.get('type') != 'tool_result' or calls.get(identity, {}).get('name') != 'Bash'
                    or decisions.get(identity) != 'prescribed'):
                raise ValueError('persisted result lacks a prescribed Bash call')
            raw_path = metadata['persistedOutputPath']
            path = Path(raw_path)
            project = re.sub(r'[^a-zA-Z0-9]', '-', str(self.root))
            directory = self.config / 'projects' / project / self.session / 'tool-results'
            if (not path.is_absolute() or path.parent != directory or self.target(path) != path
                    or not re.fullmatch(r'[A-Za-z0-9_-]+\.txt', path.name)):
                raise ValueError('persisted result outside the current tool-results directory')
            content = block.get('content')
            if (not isinstance(content, str) or not content.startswith('<persisted-output>\n')
                    or f'Full output saved to: {raw_path}\n' not in content):
                raise ValueError('native result metadata disagrees with its wrapper')
            fingerprint = self.fingerprint(path)
            size = metadata.get('persistedOutputSize')
            if type(size) is not int or size != fingerprint['bytes']:
                raise ValueError('persisted result size disagrees with native metadata')
            value = {'kind': 'persisted_output', 'tool_use_id': identity, 'path': str(path), 'file': fingerprint}
            if str(path) in self.persisted:
                raise ValueError('persisted result path was reused')
            self.persisted[str(path)] = value
            return value
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            raise self.BudgetStop('native persisted tool output has invalid provenance') from error


def _control_lifecycle(events, records, controls):
    """Preserve the live controller's initialization and terminal barriers.

    The frozen historical reconciliation alone does not enforce these states.
    This additional versioned check never changes its legacy output contract.
    """
    initialized = terminal = False
    problems = []
    init_id = controls['native_control'].INIT_ID
    if [record.get('kind') for record in records[:2]] != ['initialize_sent', 'initialize_ack']:
        problems.append('native control journal must begin with initialization then acknowledgement')
    for line, event in enumerate(events, 1):
        kind = event.get('type')
        if kind == 'control_response':
            response = event.get('response')
            if (initialized or terminal or not isinstance(response, dict)
                    or response.get('request_id') != init_id or response.get('subtype') != 'success'):
                problems.append(f'native control initialization was refused or ambiguous at line {line}')
            else:
                initialized = True
        elif kind == 'control_cancel_request':
            problems.append(f'native control callback was cancelled or timed out at line {line}')
        elif kind == 'control_request':
            if not initialized or terminal or event.get('request_id') == init_id:
                problems.append(f'native callback is outside the initialized run at line {line}')
        elif isinstance(kind, str) and kind.startswith('control_'):
            problems.append(f'unsupported native control frame at line {line}')
        elif kind == 'result':
            if not initialized or terminal:
                problems.append(f'native result is outside the initialized run at line {line}')
            terminal = True
        blocks = _blocks(event)
        if isinstance(blocks, list) and any(isinstance(block, dict) and
                block.get('type') in ('tool_use', 'tool_result') for block in blocks):
            if not initialized or terminal:
                problems.append(f'native tool event is outside the initialized run at line {line}')
    if not initialized:
        problems.append('native control lacks successful initialization')
    if not terminal:
        problems.append('native control lacks a terminal result')
    return {'checked': True, 'initialized': initialized, 'terminal': terminal, 'problems': problems}


# Versioned adaptation of the frozen ordered control reconciliation.
def _control_history(events, records, policy, classify, files, controls):
    """Reconcile every tool with parent decisions in native event order."""
    native = controls['native_control']
    BudgetStop = controls['budgeted_cborg'].BudgetStop
    control_contract, initialize_frame = native.control_contract, native.initialize_frame
    BLANK_FRAME_TYPE, INIT_ID, TOOLS = native.BLANK_FRAME_TYPE, native.INIT_ID, native.TOOLS
    digest, hook_output = native.digest, native.hook_output
    input_validation_rejection = native.input_validation_rejection
    problems = []
    try:
        contract = control_contract(policy)
        blank_lines = [line for line, event in enumerate(events, 1)
                       if event.get('type') == BLANK_FRAME_TYPE]
        if blank_lines:
            problems.append('native transcript has blank physical frames; history is uncheckable')
        if any(r.get('kind') not in ('initialize_sent', 'initialize_ack', 'decision', 'persisted_output',
                                    'input_rejected_before_callback') for r in records):
            problems.append('native control evidence contains an unrecognized record')
        sent = [r for r in records if r.get('kind') == 'initialize_sent']
        ack = [r for r in records if r.get('kind') == 'initialize_ack']
        if len(sent) != 1 or draft._encoded(sent[0].get('frame')) != draft._encoded(initialize_frame(contract)) or sent[0].get('policy_sha256') != digest(policy):
            problems.append('native control initialization does not bind this policy')
        if (len(ack) != 1 or draft._encoded(ack[0].get('frame')) not in [draft._encoded(e) for e in events] or
            ack[0]['frame'].get('response', {}).get('subtype') != 'success' or
            ack[0]['frame'].get('response', {}).get('request_id') != INIT_ID):
            problems.append('native control has no unique successful initialization evidence')
        decisions = {}
        for record in (r for r in records if r['kind'] == 'decision'):
            decisions.setdefault(record['request']['request_id'], []).append(record)
        calls, results, callbacks, classifications = {}, {}, {}, {}
        call_events, result_events, call_sessions = {}, {}, {}
        observed_files, input_rejections = [], []
        ack_lines = [line for line, event in enumerate(events, 1)
                     if len(ack) == 1 and event == ack[0].get('frame')]
        terminal_lines = [line for line, event in enumerate(events, 1) if event.get('type') == 'result']
        for line, event in enumerate(events, 1):
            message = event.get('message')
            if isinstance(message, dict) and isinstance(message.get('content'), list):
                for block in message['content']:
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'tool_use':
                        if block.get('name') not in TOOLS:
                            problems.append('native transcript uses an unregistered tool')
                        identity = block.get('id')
                        if not isinstance(identity, str) or not identity or identity in calls:
                            problems.append('native tool call lacks a unique identity')
                        calls[identity] = (line, block)
                        call_events[identity] = event
                        call_sessions[identity] = files.session
                    elif block.get('type') == 'tool_result':
                        results.setdefault(block.get('tool_use_id'), []).append((line, block))
                        result_events[line] = event
            if event.get('type') == 'control_request':
                request = event['request']; data = request['input']
                identity = data['tool_use_id']; request_id = event['request_id']
                callbacks.setdefault(identity, []).append((line, request_id))
                matches = decisions.get(request_id, [])
                if identity not in calls or len(matches) != 1:
                    problems.append('native callback lacks one preceding call and parent decision')
                    continue
                call_line, call = calls[identity]
                tool, payload = call['name'], call['input']
                if tool == 'Bash':
                    classification, basis = classify(payload['command'], policy['python'], set(), policy)
                elif tool in ('Read', 'Write'):
                    classification, basis = files.classify(tool, payload)
                else:
                    raise ValueError('unregistered tool')
                classifications[identity] = classification
                record = matches[0]
                expected = {'type': 'control_response', 'response': {'subtype': 'success',
                            'request_id': request_id, 'response': hook_output(classification, basis)}}
                if (draft._encoded(record['request']) != draft._encoded(event) or not call_line < line or
                    request.get('subtype') != 'hook_callback' or request.get('callback_id') != contract['callback_id'] or
                    data.get('hook_event_name') != contract['event'] or data.get('tool_name') != tool or
                    data.get('cwd') != policy['readonly_lookups']['repository'] or
                    not files.matches(tool, payload, data.get('tool_input', {})) or request.get('tool_use_id') not in (None, identity) or
                    record.get('classification') != classification or record.get('basis') != basis or
                    draft._encoded(record.get('response')) != draft._encoded(expected)):
                    problems.append('native control decision disagrees with its observed tool or registered policy')
            observed = files.observe(event, {key: value[1] for key, value in calls.items()}, classifications)
            if observed is not None:
                observed_files.append(observed)
        for identity, (call_line, call) in calls.items():
            matches, replies = callbacks.get(identity, []), results.get(identity, [])
            if (not matches and len(replies) == 1 and len(ack_lines) == 1 and
                ack_lines[0] < call_line < replies[0][0] and
                not any(line <= replies[0][0] for line in terminal_lines)):
                rejection = input_validation_rejection(call_events[identity], call,
                    result_events[replies[0][0]], call_line, replies[0][0], call_sessions[identity])
                if rejection is not None:
                    input_rejections.append(rejection)
                    continue
            if (len(matches) != 1 or len(replies) != 1 or
                not call_line < matches[0][0] < replies[0][0]):
                problems.append('native tool call lacks unique subsequent callback and result evidence')
            elif classifications.get(identity) != 'prescribed' and replies[0][1].get('is_error') is not True:
                problems.append('native denied tool has a successful result')
        if set(results) - set(calls):
            problems.append('native tool result has no observed call')
        if Counter(rid for values in callbacks.values() for _, rid in values) != Counter({rid: 1 for rid in decisions}):
            problems.append('native callbacks lack exactly one control response each')
        recorded_files = [{k: v for k, v in r.items() if k != 'at'} for r in records if r['kind'] == 'persisted_output']
        if draft._encoded(recorded_files) != draft._encoded(observed_files):
            problems.append('native persisted-output evidence differs from its observed origin or current bytes')
        input_rejections.sort(key=lambda value: value['result_line'])
        recorded_rejections = [{k: v for k, v in r.items() if k != 'at'} for r in records
                               if r['kind'] == 'input_rejected_before_callback']
        if draft._encoded(recorded_rejections) != draft._encoded(input_rejections):
            problems.append('native input-rejection evidence differs from its unique observed call and result')
        return {'checked': not blank_lines, 'bash_calls': sum(call['name'] == 'Bash' for _, call in calls.values()),
                'file_calls': sum(call['name'] in ('Read', 'Write') for _, call in calls.values()),
                'decisions': sum(map(len, decisions.values())),
                'input_rejections': input_rejections,
                'persisted_output_paths': list(files.persisted), 'problems': problems}
    except BudgetStop as error:
        # These messages originate in the local file policy, not provider errors.
        return {'checked': False, 'problems': [f'native control evidence failed file policy: {error}']}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
        return {'checked': False, 'problems': [f'native control evidence is missing or malformed ({type(error).__name__})']}


# Same structured checks; classifier is explicit only in this new API.
def command_history(events, command_policy, denials, classify):
    """Check every observed Bash call, including nonzero command exits.

    A denied call did not execute and retains the maintainer's separate denial
    policy. A tool error by itself does not prove denial or lack of side effects.
    This audit checks command conformance, not whether required steps happened.
    """
    denied = {d.get('tool_use_id') for d in denials if isinstance(d, dict)}
    calls = []
    results = {}
    result_errors = {}
    problems = []
    for line, event in enumerate(events, 1):
        message = event.get('message')
        if not isinstance(message, dict) or not isinstance(message.get('content'), list):
            continue
        for block in message['content']:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                calls.append((line, block))
            elif block.get('type') == 'tool_result':
                results.setdefault(block.get('tool_use_id'), []).append(line)
                result_errors.setdefault(block.get('tool_use_id'), []).append(block.get('is_error'))
    checked = []
    seen = set()
    for line, call in calls:
        identity = call.get('id')
        if not isinstance(identity, str) or not identity or identity in seen:
            problems.append(f'Bash call at transcript line {line} has missing or duplicate identity')
            continue
        seen.add(identity)
        entry = {'tool_use_id': identity, 'call_line': line, 'result_lines': results.get(identity, [])}
        if identity in denied:
            entry['classification'] = 'denied_not_executed'
            if result_errors.get(identity) != [True]:
                problems.append(f'Bash denial at transcript line {line} lacks one matching error result')
        else:
            payload = call.get('input')
            command = payload.get('command') if isinstance(payload, dict) else None
            if not isinstance(command, str) or not command.strip():
                entry.update(classification='unclassifiable', basis='missing or empty Bash command')
            else:
                classification, basis = classify(command, command_policy['python'], set(), command_policy)
                entry.update(classification=classification, basis=basis, command=command[:1000])
            if entry['classification'] != 'prescribed':
                problems.append(f'nonconforming executed Bash call at transcript line {line}: {entry["basis"]}')
        if len(entry['result_lines']) != 1 or entry['result_lines'][0] <= line:
            problems.append(f'Bash call at transcript line {line} lacks one subsequent tool result')
        checked.append(entry)
    return {'checked': True, 'calls': checked, 'problems': problems}


def classify_denials(denials, policy, classify, controls, instruction):
    """Reuse frozen non-Bash denial rules; only the classifier is composed."""
    old = controls['run_native_canary'].classify_denials(denials, instruction_text=instruction,
        python=policy['python'], repository=policy['readonly_lookups']['repository'],
        output_directories=policy['readonly_lookups']['output_directories'],
        readable_inputs=policy['readonly_lookups']['inputs'], command_policy=policy)
    if isinstance(denials, list):
        for item, result in zip(denials, old):
            if (isinstance(item, dict) and item.get('tool_name') == 'Bash'
                    and isinstance(item.get('tool_input'), dict)):
                command = item['tool_input'].get('command')
                if isinstance(command, str) and command.strip():
                    result['classification'], result['basis'] = classify(command, policy['python'], set(), policy)
    return old


def _blocks(event):
    message = event.get('message')
    return message.get('content', []) if isinstance(message, dict) else []


def capture(composition_path, transcript_path, control_path, *, config_root=None):
    """Prepare one current-authority snapshot. Old code pins are never upgraded."""
    snap = Capture(Path.cwd().resolve())
    raw = snap.read(composition_path, 'composition')
    value = composition.verified_composition(raw)
    controls = composition.load_controls()
    registration_raw = value['registration_raw_json'].encode('utf-8')
    state = CapturedDraft(registration_raw, snap)
    spec, policy = state.spec, value['policy']
    from data_sheets_schema.resources import resource_path
    for relative, expected in state.reg['checker_source_tree_sha256'].items():
        if draft._sha(snap.read(resource_path(Path(relative)), 'checker_source')) != expected:
            raise ValueError('captured checker source differs from registration')
    for relative, expected in state.reg['prompt_files_sha256'].items():
        if draft._sha(snap.read(resource_path(Path(relative)), 'selected_prompt')) != expected:
            raise ValueError('captured prompt source differs from registration')
    for pin in value['controller_sources']['modules'].values():
        if draft._sha(snap.read(composition.ROOT/pin['path'], 'frozen_controller_source')) != pin['sha256']:
            raise ValueError('captured controller source differs from composition')
    events = _rows(snap.read(transcript_path, 'transcript'), 'transcript')
    records = _rows(snap.read(control_path, 'control'), 'control')
    for event in events:
        if event.get('type') == 'control_request':
            request = event.get('request')
            if (not isinstance(event.get('request_id'), str) or not event['request_id']
                    or not isinstance(request, dict) or not isinstance(request.get('input'), dict)):
                raise ValueError('malformed saved callback request')
    for path in policy['readonly_lookups']['inputs']:
        snap.read(path, 'registered_readable_input')
    for key, pin in state.reg['inputs'].items():
        if draft._sha(snap.read(pin['path'], key)) != pin['sha256']:
            raise ValueError('captured selected source differs from registration')
    for pin in value['metadata_inputs'].values():
        if draft._sha(snap.read(pin['path'], 'selected_metadata_input')) != pin['sha256']:
            raise ValueError('captured metadata input differs from composition')
    instruction_raw = snap.read(value['instruction_path'], 'instruction')
    if draft._sha(instruction_raw) != value['instruction_sha256']:
        raise ValueError('captured instruction differs from composition')
    artifacts = spec._agentic_artifact_paths
    directory = Path(artifacts['core']).parent/'evidence'
    for role, path in {'final_full': artifacts['full'], 'final_core': artifacts['core'],
            'report': artifacts['report'], 'original_full': directory/'original_full.yaml',
            'original_core': directory/'original_core.yaml', 'audit': directory/'audit.json'}.items():
        snap.read(path, role)
    metadata_path = policy['post_final_recorder']['destination']
    if snap.metadata[str(snap.path(metadata_path))]['regular']:
        snap.read(metadata_path, 'provenance')
    if config_root is not None:
        snap.path(config_root)
    commands = set()
    denials = []
    for event in events:
        if event.get('type') == 'result' and 'permission_denials' in event:
            denials.append(event['permission_denials'])
        blocks = _blocks(event)
        for item in blocks if isinstance(blocks, list) else []:
            if not isinstance(item, dict) or item.get('type') != 'tool_use':
                continue
            args = item.get('input')
            if not isinstance(args, dict):
                continue
            if item.get('name') == 'Bash' and isinstance(args.get('command'), str):
                commands.add(args['command'])
            elif item.get('name') in ('Read', 'Write') and isinstance(args.get('file_path'), str):
                snap.path(args['file_path'])
        if event.get('type') == 'control_request':
            payload = ((event.get('request') or {}).get('input') or {}).get('tool_input')
            if isinstance(payload, dict) and isinstance(payload.get('file_path'), str):
                snap.path(payload['file_path'])
        meta = event.get('tool_use_result')
        if isinstance(meta, dict) and isinstance(meta.get('persistedOutputPath'), str):
            # A config root may also contain authentication files. Only capture
            # the exact native tool-results grammar, never arbitrary descendants.
            declared = Path(meta['persistedOutputPath'])
            path = snap.path(declared)
            session = event.get('session_id')
            directory = (snap.path(config_root)/'projects'/re.sub(r'[^a-zA-Z0-9]', '-', str(snap.root))
                         /session/'tool-results') if config_root is not None and isinstance(session, str) else None
            if (event.get('type') == 'user' and directory is not None
                    and re.fullmatch(r'[0-9a-f-]{36}', session)
                    and declared.is_absolute() and declared == path and path.parent == directory
                    and re.fullmatch(r'[A-Za-z0-9_-]+\.txt', path.name)):
                snap.read(path, 'persisted_output')
    for rows in denials:
        if isinstance(rows, list):
            for item in rows:
                if isinstance(item, dict) and isinstance(item.get('tool_input'), dict):
                    args = item['tool_input']
                    if item.get('tool_name') == 'Bash' and isinstance(args.get('command'), str):
                        commands.add(args['command'])
                    elif isinstance(args.get('file_path'), str):
                        snap.path(args['file_path'])
    # Current metadata is captured explicitly. It cannot establish what a file
    # contained at an earlier intermediate Read or Write.
    inputs = {Path(p) for p in policy['readonly_lookups']['inputs']}
    outputs = [Path(p) for p in policy['readonly_lookups']['output_directories']]
    for target, meta in list(snap.metadata.items()):
        path = Path(target)
        if meta['regular'] and (path in inputs or any(p in path.parents for p in outputs)):
            snap.read(path, 'observed_current_file')
    classifications, readonly = {}, {}
    grammar = controls['native_command_policy']
    lookups = controls['native_readonly']
    for command in sorted(commands):
        # Freeze the pure policy decision along with every path resolution used
        # by the small lookup grammar. Replay never consults the live filesystem.
        for part in lookups.pipeline_parts(command):
            words, _ = grammar._simple_command(part)
            if words and words[0] in lookups.PROGRAMS:
                for path in lookups._paths(words) or []:
                    if path != '-':
                        target = snap.path(path)
                        meta = snap.metadata[str(target)]
                        if meta['regular'] and (target in inputs or any(p in target.parents for p in outputs)):
                            snap.read(target, 'lookup_current_file')
        classifications[command] = composition._classify(command, policy['python'], set(), policy, controls)
        readonly[command] = lookups.lookup_command(command, policy['readonly_lookups'], grammar._simple_command)
    files = CapturedFiles(snap, policy, controls, config_root)
    state.compute_preflight()
    final_result = _final_evidence(snap, spec)
    def captured_classifier(command, python, programs, supplied_policy):
        if python != policy['python'] or draft._encoded(supplied_policy) != draft._encoded(policy):
            raise ValueError('saved classifier policy differs from composition')
        if command not in classifications:
            raise ValueError('saved classifier requested an uncaptured command')
        return classifications[command]
    terminals = [event for event in events if event.get('type') == 'result']
    terminal = terminals[0] if len(terminals) == 1 else {}
    classified_denials = classify_denials(terminal.get('permission_denials'), policy,
        captured_classifier, controls, instruction_raw.decode('utf-8'))
    # Verify code/selection authority a second time; semantic checks below still
    # consume the captured artifact bytes, not newly read record/report files.
    composition.verified_composition(raw)
    snap.verify_unchanged()
    snap.sealed = True
    return {'snapshot': snap, 'composition_raw': raw, 'composition': value, 'state': state,
            'events': events, 'records': records, 'policy': policy, 'controls': controls,
            'files': files, 'classifications': classifications, 'readonly': readonly,
            'instruction': instruction_raw.decode('utf-8'), 'final_result': final_result,
            'denials': classified_denials}


def _saved_draft(prepared, classify):
    state = deepcopy(prepared['state'])
    state.snapshot = prepared['snapshot']
    policy = prepared['policy']
    recorder = policy['post_final_recorder']['command']
    last_final, recorder_call, recorder_done = None, None, False
    problems = []
    for event in prepared['events']:
        preserved = set()
        for item in _blocks(event) if isinstance(_blocks(event), list) else []:
            if not isinstance(item, dict):
                continue
            try:
                if item.get('type') == 'tool_use':
                    if recorder_done:
                        raise ValueError('tool continuation after completed final recorder')
                    args = item.get('input') or {}
                    if item.get('name') == 'Write':
                        last_final = None
                    if item.get('name') == 'Bash':
                        command = args.get('command')
                        kind = state._command_kind(command)
                        if kind == 'draft':
                            last_final = None
                        elif command == recorder:
                            if last_final is None or recorder_call is not None or state.pending:
                                raise ValueError('recorder lacks one settled final evidence pass or repeats')
                            recorder_call = item.get('id')
                            preserved.add(command)
                        elif state.checks and kind is None:
                            if not prepared['readonly'].get(command, False):
                                raise ValueError('draft correction permits report Writes and registered read-only checks only')
                            preserved.add(command)
                elif item.get('type') == 'tool_result':
                    identity = item.get('tool_use_id')
                    row = state.pending.get(identity)
                    if row and row['kind'] == 'final_evidence':
                        payload = draft._json(item.get('content'))
                        meta = event.get('tool_use_result') or {}
                        if 'stdout' in meta and draft._encoded(draft._json(meta['stdout'])) != draft._encoded(payload):
                            raise ValueError('final evidence tool output and stdout disagree')
                        if type(payload) is not dict or payload.get('checked') is not True or payload.get('findings') != []:
                            raise ValueError('final evidence has unusable or failed checker content')
                        last_final = payload
                    if identity == recorder_call:
                        meta = event.get('tool_use_result') or {}
                        exits = [meta[k] for k in ('exitCode', 'exit_code') if k in meta]
                        if (not exits or any(type(code) is not int or code != 0 for code in exits)
                                or item.get('is_error') is not False
                                or any(meta.get(k) for k in ('interrupted', 'backgroundTaskId', 'background_task_id'))):
                            raise ValueError('registered recorder failed or has unusable result')
                        destination = policy['post_final_recorder']['destination']
                        recorded_path = state.snapshot.path(destination)
                        metadata = state.snapshot.metadata[str(recorded_path)]
                        alias = state.snapshot.alias_metadata[str(Path(destination))]
                        if (not metadata['regular'] or metadata.get('links') != 1 or alias['symlink']):
                            raise ValueError('completed recorder metadata must be a regular non-symlink single-link file')
                        state.snapshot.read(destination, 'provenance')
                        recorder_done = True
            except (ValueError, TypeError, KeyError) as exc:
                problems.append(str(exc))
        if event.get('type') == 'control_request':
            data = (event.get('request') or {}).get('input') or {}
            identity = data.get('tool_use_id')
            row = state.pending.get(identity)
            if row and (row['kind'] in ('draft', 'final_evidence') or identity == recorder_call):
                if set(state.pending) != {identity}:
                    problems.append('draft/final/recorder callback overlaps another pending tool')
        state.observe(event, preserved_shell_commands=preserved)
    report = state.finish()
    report['problems'] += problems
    report['draft_gate_passed'] = report['draft_gate_passed'] and not problems
    return report, last_final, recorder_done


def check_capture(prepared):
    """Replay a sealed capture; never launch or silently read uncaptured files."""
    snap = prepared['snapshot']
    if not snap.sealed:
        raise ValueError('saved replay requires a sealed capture')
    policy, controls = prepared['policy'], prepared['controls']
    def classify(command, python, programs, supplied_policy):
        if python != policy['python'] or draft._encoded(supplied_policy) != draft._encoded(policy):
            raise ValueError('saved classifier policy differs from composition')
        if command not in prepared['classifications']:
            raise ValueError('saved classifier requested an uncaptured command')
        return prepared['classifications'][command]
    events = prepared['events']
    finals = [(n, event) for n, event in enumerate(events) if event.get('type') == 'result']
    trace_problems = []
    if len(finals) != 1:
        trace_problems.append('saved trace lacks one terminal result; stopped or partial history is not complete')
    terminal = finals[0][1] if len(finals) == 1 else {}
    if len(finals) == 1:
        if any(_blocks(event) or event.get('type') == 'control_request' for event in events[finals[0][0]+1:]):
            trace_problems.append('saved trace continues after its terminal result')
        if (('is_error' in terminal and terminal['is_error'] is not False)
                or terminal.get('terminal_reason', 'completed') != 'completed'
                or terminal.get('stop_reason', 'end_turn') != 'end_turn'
                or (isinstance(terminal.get('subtype'), str) and terminal['subtype'].startswith('error'))):
            trace_problems.append('saved terminal result reports failure or an unusable state')
    denials = deepcopy(prepared['denials'])
    commands = command_history(events, policy, denials, classify)
    control = _control_history(events, prepared['records'], policy, classify, deepcopy(prepared['files']), controls)
    lifecycle = _control_lifecycle(events, prepared['records'], controls)
    draft_report, last_final, recorder_done = _saved_draft(prepared, classify)
    actual_final = deepcopy(prepared['final_result'])
    final_problems = []
    if last_final is None:
        final_problems.append('no current final evidence result observed')
    elif draft._encoded(last_final) != draft._encoded(actual_final):
        final_problems.append('final evidence result differs from captured saved bytes')
    if not actual_final.get('checked') or actual_final.get('findings'):
        final_problems.append('actual final evidence checker did not pass on captured bytes')
    denial_problems = controls['run_native_canary'].denial_problems(denials)
    problems = (trace_problems + commands['problems'] + control['problems'] + lifecycle['problems']
                + draft_report['problems'] + final_problems + denial_problems)
    return {'instrument': INSTRUMENT, 'version': VERSION, 'scope': SCOPE, 'checked': True,
        'additional_gate_passed': not problems and draft_report['draft_gate_passed'],
        'generation_acceptance': 'not_assessed', 'problems': problems,
        'composition_sha256': draft._sha(prepared['composition_raw']),
        'registration_sha256': prepared['composition']['registration_sha256'],
        'embedded_raw_registration': {'sha256': prepared['composition']['registration_sha256'],
            'bytes': len(prepared['composition']['registration_raw_json'].encode('utf-8'))},
        'authority': {'code_commit': prepared['state'].reg['code_commit'],
            'package_source_tree_sha256': prepared['state'].reg['checker_source_tree_sha256'],
            'controller_sources_sha256': prepared['composition']['controller_sources_sha256'],
            'policy_sha256': prepared['composition']['policy_sha256']},
        'raw_files': snap.identity(), 'captured_path_aliases': deepcopy(snap.aliases),
        'captured_path_metadata': deepcopy(snap.alias_metadata),
        'current_file_metadata': deepcopy(snap.metadata),
        'metadata_scope': 'Current capture only; historical intermediate bytes are not reconstructed.',
        'command_history': commands, 'control_history': control, 'control_lifecycle': lifecycle,
        'denial_classification': denials,
        'denials_reported_in_terminal': 'permission_denials' in terminal,
        'draft_history': draft_report, 'final_evidence': actual_final,
        'recorder_completed_in_trace': recorder_done,
        'requirements_not_assessed': ['full generation completion', 'complete generation phase history', 'usage/accounting', 'native permission proof',
                                     'schema/pair/receipt acceptance', 'scientific support', 'launch authorization']}


def check_files(composition_path, transcript_path, control_path, *, config_root=None):
    prepared = capture(composition_path, transcript_path, control_path, config_root=config_root)
    return check_capture(prepared)


def write_report(prepared, destination):
    result = check_capture(prepared)
    prepared['snapshot'].verify_unchanged()
    target = Path(destination)
    canonical = target.resolve()
    if any(canonical == Path(path) or (target.exists() and target.samefile(path))
           for path in prepared['snapshot'].raw):
        raise ValueError('report destination aliases a captured input')
    if str(canonical) in prepared['snapshot'].metadata:
        raise ValueError('report destination is a captured artifact or metadata target')
    preserved_directories = [Path(path).resolve() for path in
                             prepared['policy']['readonly_lookups']['output_directories']]
    preserved_directories += [Path(path).parent for path, roles in prepared['snapshot'].roles.items()
                              if {'transcript', 'control'} & roles]
    if any(canonical.is_relative_to(directory) for directory in preserved_directories):
        raise ValueError('report output cannot modify a retained attempt or registered output directory')
    if canonical.is_relative_to(composition.ROOT/'src') or canonical.is_relative_to(composition.ROOT/'notes'):
        raise ValueError('report output cannot modify source authority or historical controls')
    raw = draft._encoded(result)
    # A fully written and flushed private staging file precedes the exclusive
    # publication link. I/O failure cannot leave a valid-looking final report.
    with tempfile.NamedTemporaryFile(mode='wb', prefix='.native-attribution-pending-',
                                     dir=target.parent, delete=False) as stream:
        pending = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    prepared['snapshot'].verify_unchanged()
    os.link(pending, target)  # Exclusive: a racing existing destination survives.
    pending.unlink()  # Only this writer's own staging link; never an input.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composition', type=Path, required=True)
    parser.add_argument('--transcript', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--config-root', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        prepared = capture(args.composition, args.transcript, args.control, config_root=args.config_root)
        result = write_report(prepared, args.out) if args.out else check_capture(prepared)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(json.dumps({'instrument': INSTRUMENT, 'checked': False, 'additional_gate_passed': False,
                          'generation_acceptance': 'not_assessed', 'error': str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['additional_gate_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
