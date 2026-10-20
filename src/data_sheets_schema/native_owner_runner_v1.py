"""Private shared/history owner lifetime; no public execution route selects it.

Binding checks are local consistency, not launch permission or authentication.
The parent-only monotonic record is not admissible to independent helpers.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import threading
import time
from types import MappingProxyType

from . import native_attempt_supervisor as durable
from . import native_execution_authority as authority
from . import native_owner_control_v1 as owner
from . import native_shared_contract as c
from . import native_shared_evidence as evidence
from . import native_clock_domain_v1 as clocks
from . import native_stream_coordination_v1 as coordination

REQUEST_LIMIT = c.HARD_LIMITS['request_bytes']
TERMINAL_ROLES = MappingProxyType({
    'owner': ('stream-owner.json', 16_384),
    'owner_stop': ('stream-owner-stop.json', 16_384),
    'owner_runner_report': ('stream-owner-result.json', 16_384),
    'owner_close': ('stream-owner-close.json', 16_384),
    'owner_failure': ('stream-owner-failure.json', 16_384),
    'owner_control_record': ('stream-owner-control-record.bin', 16_777_216),
    'owner_worker_clock_close': ('stream-owner-worker-clock-close.json', 16_384),
    'owner_transcript_suffix': ('stream-owner-transcript-suffix.bin', 384_000_000),
    'owner_retention': ('stream-owner-retention.json', 65_536),
})
TERMINAL_ROLE_ORDER = tuple(role for role in TERMINAL_ROLES if role != 'owner_retention')
FILES = ('transcript.jsonl', 'control.jsonl', 'stderr.txt',
         *(item[0] for item in TERMINAL_ROLES.values()))
_FAILED_ROLES = MappingProxyType({'transcript_suffix': 'owner_transcript_suffix',
    'control_record': 'owner_control_record', 'worker_clock_close': 'owner_worker_clock_close'})
_TERMINAL_SCOPE = 'terminal_retention_only'
_ROW_KEYS = {'role', 'path', 'state', 'intended', 'retained', 'basis', 'write', 'observed_partial'}
_COUNT_KEYS = {'retained_members', 'retained_bytes', 'observed_partial_members', 'observed_partial_bytes'}
_BASES = MappingProxyType({
    'retained': frozenset(('retained_owned_owner', 'retained_owned_stop', 'retained_frozen_member')),
    'not_produced': frozenset(('control_not_created', 'absent_at_completed_stop_cut',
        'normal_close_without_failure_summary', 'summary_declares_no_intended_record',
        'normal_close_without_intended_record', 'close_declares_no_failed_suffix')),
    'capture_refused': frozenset(('owner_observation_refused', 'stop_create_not_completed',
        'stop_observation_refused', 'frozen_capture_unavailable', 'intended_record_bytes_unavailable',
        'failure_summary_capture_unavailable', 'close_report_capture_unavailable',
        'stop_cut_or_copy_unavailable', 'publication_preflight_refused')),
    'publication_failed': frozenset(('preflight_refused', 'write_failed_partial_observed',
        'partial_bytes_unavailable_or_uncaptured', 'not_attempted_after_publication_failure')),
})
_V2_PROFILE_PATHS = MappingProxyType({
    'coordination': 'src/data_sheets_schema/native_stream_coordination_v1.py',
    'control': 'src/data_sheets_schema/native_owner_control_v1.py',
    'runner': 'src/data_sheets_schema/native_owner_runner_v1.py',
    'clock': 'src/data_sheets_schema/native_clock_domain_v1.py',
})
_V2_CONTROLLER_SHA = 'd1f13def58c0832aea3644fb68806d829eb4ab6e087045f14d86f439aed557c1'


def validate_owner_record_v2(value):
    """Validate detached saved claims only; perform no live source/clock checks."""
    keys = {'format', 'coordination_profile', 'execution_sha256', 'started_sha256',
        'owner_pid', 'clock', 'start_ns', 'deadline_ns', 'duration_ns',
        'transcript', 'control', 'clock_domain'}
    if type(value) is not dict or set(value) != keys or value['format'] != 'native_stream_owner_v2':
        raise ValueError('owner record differs from the closed v2 contract')
    if type(value['clock']) is not str or value['clock'] != 'monotonic_ns':
        raise ValueError('owner record clock differs')
    c._hash(value['execution_sha256'], 'owner execution hash')
    c._hash(value['started_sha256'], 'owner started hash')
    for name in ('owner_pid', 'duration_ns', 'deadline_ns'):
        c.positive_int(value[name], 'owner ' + name)
    if type(value['start_ns']) is not int or value['start_ns'] < 0:
        raise ValueError('owner start requires a nonnegative exact integer')
    if value['deadline_ns'] != value['start_ns'] + value['duration_ns']:
        raise ValueError('owner deadline differs from its original duration')
    selected = value['coordination_profile']
    if (type(selected) is not dict
            or set(selected) != {'format', 'profile', 'base_controller_sources_sha256', 'implementations'}
            or selected['format'] != 'native_stream_snapshot_profile_v1' or type(selected['profile']) is not int
            or selected['profile'] != 1
            or selected['base_controller_sources_sha256'] != _V2_CONTROLLER_SHA
            or type(selected['implementations']) is not dict
            or set(selected['implementations']) != set(_V2_PROFILE_PATHS)):
        raise ValueError('owner record requires the exact four-role source profile')
    for role, path in _V2_PROFILE_PATHS.items():
        item = selected['implementations'][role]
        if type(item) is not dict or set(item) != {'path', 'sha256'} or item['path'] != path:
            raise ValueError('owner source role differs from its fixed path')
        c._hash(item['sha256'], 'owner source hash')
    identities, paths = set(), set()
    for role in ('transcript', 'control'):
        item = value[role]
        if (type(item) is not dict or set(item) != {'path', 'device', 'inode'}
                or type(item['device']) is not int or item['device'] < 0
                or type(item['inode']) is not int or item['inode'] <= 0):
            raise ValueError('owner stream identity is malformed')
        paths.add(c.canonical_path(item['path'], 'owner stream path'))
        identities.add((item['device'], item['inode']))
    if len(paths) != 2 or len(identities) != 2:
        raise ValueError('owner stream identities alias')
    result = {**value, 'clock_domain': clocks.validate_declaration(value['clock_domain'])}
    return json.loads(owner._json(result))


def _spawn(argv, *, stderr, cwd, env):
    """Fixed ordinary OS dispatch seam; no caller-selected launcher."""
    return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=stderr, cwd=cwd, env=env, start_new_session=True)


def _canonical(value):
    c._json_values(value)
    parts, size = [], 0
    for text in json.JSONEncoder(sort_keys=True, ensure_ascii=False,
            separators=(',', ':'), allow_nan=False).iterencode(value):
        raw = text.encode('utf-8')
        size += len(raw)
        if size > REQUEST_LIMIT:
            raise ValueError('private runner input exceeds the request bound')
        parts.append(raw)
    return b''.join(parts)


def _physical(value, label, *, directory=False):
    path = c.canonical_path(str(value), label)
    target = Path(path)
    if str(target.resolve(strict=True)) != path or (directory and not target.is_dir()):
        raise ValueError(label + ' is not its exact physical path')
    return target


def _error(error):
    raw = str(error).encode('utf-8', errors='backslashreplace')
    return {'type': type(error).__name__[:128],
            'message': raw.decode('utf-8') if len(raw) <= 512 else None,
            'message_identity': owner._pin(raw)}


def _terminal_json(value, limit=65_536):
    c._json_values(value)
    pieces, size = [], 0
    for text in json.JSONEncoder(sort_keys=True, ensure_ascii=False,
            separators=(',', ':'), allow_nan=False).iterencode(value):
        raw = text.encode('utf-8')
        size += len(raw)
        if size > limit:
            raise ValueError('terminal metadata exceeds its fixed byte bound')
        pieces.append(raw)
    return b''.join(pieces)


def _natural(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(label + ' requires a nonnegative exact integer')
    return value


def _boolean(value, label):
    if type(value) is not bool:
        raise ValueError(label + ' requires an exact boolean')
    return value


def _nullable_text(value, label):
    if value is not None and type(value) is not str:
        raise ValueError(label + ' requires text or null')


def _terminal_pin(value, limit=c.HARD_LIMITS['evidence_raw_total_bytes']):
    c.exact(value, {'bytes', 'sha256'}, 'terminal pin')
    if _natural(value['bytes'], 'terminal pin bytes') > limit:
        raise ValueError('terminal pin exceeds its role bound')
    c._hash(value['sha256'], 'terminal pin hash')
    return value


def _identity(value):
    c.exact(value, {'device', 'inode'}, 'terminal file identity')
    _natural(value['device'], 'terminal device')
    c.positive_int(value['inode'], 'terminal inode')
    return value


def _diagnostic(value):
    c.exact(value, {'type', 'message', 'message_identity'}, 'terminal error detail')
    if type(value['type']) is not str or not value['type'] or len(value['type']) > 128:
        raise ValueError('terminal error type is invalid')
    pin = _terminal_pin(value['message_identity'])
    message = value['message']
    _nullable_text(message, 'terminal error message')
    if message is not None and (len(message.encode('utf-8')) > 512
            or owner._pin(message.encode('utf-8')) != pin):
        raise ValueError('terminal retained error message differs from its pin')
    if message is None and pin['bytes'] <= 512:
        raise ValueError('terminal error omits a retainable message')


def _close_document(value):
    if type(value) is not dict:
        raise ValueError('terminal close report requires a closed object')
    base = {'format', 'worker_shutdown_complete', 'unfinished_workers', 'capture_complete',
        'tail_capture_complete', 'tail_reason', 'suffix_start', 'admitted_bytes', 'suffix',
        'role', 'operation_failed', 'admitted'}
    extra = {'cleanup_mode', 'close_start_ns', 'close_deadline_ns', 'written_bytes_at_stop',
        'admitted_bytes_at_stop', 'final_written_bytes', 'retention_error'}
    kind = value.get('format')
    if kind == 'native_owner_close_refused_v1':
        short = {'format', 'capture_complete', 'tail_capture_complete', 'cleanup_error', 'admitted'}
        long = short | {'worker_shutdown_complete', 'unfinished_workers', 'operation_failed', 'suffix_start', 'suffix'}
        if set(value) not in (short, long):
            raise ValueError('terminal close refusal fields differ')
        if any(value[k] is not False for k in ('capture_complete', 'tail_capture_complete', 'admitted')):
            raise ValueError('terminal close refusal claims completion')
        if type(value['cleanup_error']) is not str or not value['cleanup_error']:
            raise ValueError('terminal close refusal lacks error')
    elif kind in ('native_owner_close_v1', 'native_owner_close_v2'):
        keys = base | (extra if kind.endswith('v2') else set())
        if set(value) not in (keys, keys | {'cleanup_error'}):
            raise ValueError('terminal close fields differ')
        if value['role'] != 'transcript' or value['admitted'] is not False:
            raise ValueError('terminal close role/admission differs')
        _terminal_pin(value['suffix'], TERMINAL_ROLES['owner_transcript_suffix'][1])
        _natural(value['suffix_start'], 'terminal suffix start')
        for name in ('capture_complete', 'tail_capture_complete', 'operation_failed'):
            _boolean(value[name], 'terminal close ' + name)
        _nullable_text(value['tail_reason'], 'terminal tail reason')
        _natural(value['admitted_bytes'], 'terminal admitted bytes')
        if value['admitted_bytes'] > value['suffix_start']:
            raise ValueError('terminal admitted bytes exceed physical prefix')
        if 'cleanup_error' in value and (type(value['cleanup_error']) is not str
                or not value['cleanup_error'] or value['capture_complete']):
            raise ValueError('terminal close cleanup error claims completion')
        if value['capture_complete'] and (not value['tail_capture_complete']
                or value['tail_reason'] is not None or value['suffix']['bytes']
                or value['operation_failed']):
            raise ValueError('terminal close completion contradicts retained tail')
        if kind.endswith('v2'):
            for key in ('close_start_ns', 'close_deadline_ns', 'written_bytes_at_stop',
                        'admitted_bytes_at_stop', 'final_written_bytes'):
                _natural(value[key], 'terminal close ' + key)
            if (value['cleanup_mode'] != 'append'
                    or value['close_deadline_ns'] != value['close_start_ns'] + 250_000_000
                    or value['admitted_bytes_at_stop'] > value['written_bytes_at_stop']
                    or value['written_bytes_at_stop'] > value['final_written_bytes']
                    or value['suffix_start'] != value['final_written_bytes']
                    or value['admitted_bytes_at_stop'] != value['admitted_bytes']):
                raise ValueError('terminal close append accounting differs')
            _nullable_text(value['retention_error'], 'terminal retention error')
            if value['retention_error'] is not None and value['capture_complete']:
                raise ValueError('terminal retention error claims completion')
    else:
        raise ValueError('unknown terminal close format')
    if 'suffix' in value:
        _terminal_pin(value['suffix'], TERMINAL_ROLES['owner_transcript_suffix'][1])
        _natural(value['suffix_start'], 'terminal suffix start')
        if value['suffix_start'] + value['suffix']['bytes'] > c.HARD_LIMITS['stream_bytes']:
            raise ValueError('terminal suffix exceeds stream capacity')
    if 'unfinished_workers' in value:
        if type(value['unfinished_workers']) is not int or value['unfinished_workers'] not in (0, 1):
            raise ValueError('terminal worker count differs')
        if value['worker_shutdown_complete'] is not (value['unfinished_workers'] == 0):
            raise ValueError('terminal worker completion differs')
        _boolean(value['operation_failed'], 'terminal operation failure')
    return value


def _failure_document(value):
    base = {'format', 'first_stop', 'capture_state', 'active_kind', 'worker_started',
        'worker_finished', 'completed_result_captured', 'request_id', 'result',
        'intended_record_exists', 'control_commit', 'transcript'}
    if type(value) is not dict or value.get('format') != 'native_owner_failure_v1':
        raise ValueError('unknown terminal failure format')
    fallback = 'unretained_fields' in value
    optional = {'first_stop_identity', 'request_id_identity',
                'first_stop_retention_error', 'request_id_retention_error'}
    keys = base | ({'capture_error', 'unretained_fields'} if fallback else set())
    if fallback:
        if not keys <= set(value) or set(value) - keys - optional:
            raise ValueError('terminal failure fallback fields differ')
        fields = value['unretained_fields']
        if (type(fields) is not list or not fields or any(type(item) is not str for item in fields) or fields[0] != 'result'
                or len(fields) != len(set(fields)) or set(fields) - {'result', 'first_stop', 'request_id'}
                or value['capture_error'] != 'summary_bound'):
            raise ValueError('terminal failure fallback omissions differ')
    elif set(value) not in (base, base | {'capture_error'}):
        raise ValueError('terminal failure fields differ')
    if value['capture_state'] not in ('captured', 'capture_refused'):
        raise ValueError('terminal failure capture state differs')
    for key in ('completed_result_captured', 'intended_record_exists'):
        _boolean(value[key], 'terminal failure ' + key)
    if 'capture_error' in value:
        if (type(value['capture_error']) is not str or not value['capture_error']
                or value['capture_state'] != 'capture_refused' or value['result'] is not None
                or value['completed_result_captured'] is not False):
            raise ValueError('terminal failure refusal claims captured result')
    elif value['capture_state'] != 'captured':
        raise ValueError('terminal failure refusal lacks reason')
    _nullable_text(value['first_stop'], 'terminal first stop')
    _nullable_text(value['active_kind'], 'terminal active work')
    for key in ('worker_started', 'worker_finished'):
        item = value[key]
        if item is not None and (type(item) not in (int, float) or item < 0):
            raise ValueError('terminal worker timestamp differs')
    if fallback:
        for key in ('first_stop', 'request_id'):
            absent = key in value['unretained_fields']
            if absent and value[key] is not None:
                raise ValueError('terminal fallback retains an omitted identity')
            if key + '_identity' in value:
                pin = _terminal_pin(value[key + '_identity'])
                if not absent or pin['bytes'] <= 512 or key + '_retention_error' in value:
                    raise ValueError('terminal fallback identity pin differs')
            if key + '_retention_error' in value and (
                    not absent or value[key + '_retention_error'] != 'not_text'):
                raise ValueError('terminal fallback retention error differs')
    transcript = c.exact(value['transcript'],
        {'received_bytes', 'written_bytes', 'admitted_bytes', 'pending'}, 'terminal failure transcript')
    for key in ('received_bytes', 'written_bytes', 'admitted_bytes'):
        _natural(transcript[key], 'terminal failure ' + key)
    _terminal_pin(transcript['pending'], c.HARD_LIMITS['stream_bytes'])
    if not (transcript['admitted_bytes'] <= transcript['written_bytes'] <= transcript['received_bytes']
            <= c.HARD_LIMITS['stream_bytes']):
        raise ValueError('terminal failure prefix counters differ')
    if transcript['written_bytes'] + transcript['pending']['bytes'] != transcript['received_bytes']:
        raise ValueError('terminal failure pending bytes differ')
    commit = value['control_commit']
    if commit is not None:
        c.exact(commit, {'record', 'start', 'written', 'complete'}, 'terminal intended record')
        _terminal_pin(commit['record'])
        for key in ('start', 'written'):
            _natural(commit[key], 'terminal control ' + key)
        _boolean(commit['complete'], 'terminal control completion')
        if commit['written'] > commit['record']['bytes'] or (
                commit['complete'] and commit['written'] != commit['record']['bytes']):
            raise ValueError('terminal control record offsets differ')
    if not value['intended_record_exists'] and commit is not None:
        raise ValueError('terminal failure denies its intended record')
    return value


def _runner_document(value):
    base = {'format', 'state', 'dispatches', 'owner_published', 'stop_marker_published',
            'execution_authorized', 'native_acceptance'}
    if type(value) is not dict:
        raise ValueError('terminal runner report is not an object')
    kind = value.get('format')
    if kind == 'native_owner_runner_report_v1':
        c.exact(value, base | {'returncode', 'primary_error', 'cleanup_errors', 'control_close'}, 'runner report')
        if value['returncode'] is not None and type(value['returncode']) is not int:
            raise ValueError('terminal runner return code is invalid')
        if value['primary_error'] is not None:
            _diagnostic(value['primary_error'])
        if type(value['cleanup_errors']) is not list:
            raise ValueError('terminal cleanup errors require a list')
        for item in value['cleanup_errors']:
            c.exact(item, {'stage', 'error'}, 'terminal cleanup error')
            if type(item['stage']) is not str or not item['stage']:
                raise ValueError('terminal cleanup stage is invalid')
            _diagnostic(item['error'])
        if value['control_close'] is not None:
            _close_document(value['control_close'])
        if (value['state'] == 'completed') != (value['primary_error'] is None and not value['cleanup_errors']):
            raise ValueError('terminal runner state differs from its errors')
        if value['state'] == 'completed' and (value['dispatches'] != 1
                or value['owner_published'] is not True or value['stop_marker_published'] is not True):
            raise ValueError('terminal completed runner lacks its dispatch/owner/stop prerequisites')
    elif kind == 'native_owner_runner_report_refused_v1':
        c.exact(value, base | {'error'}, 'runner refusal')
        if value['state'] != 'failed' or type(value['error']) is not str or not value['error']:
            raise ValueError('terminal runner refusal lacks failure')
    else:
        raise ValueError('unknown terminal runner report format')
    if (value['state'] not in ('completed', 'failed') or type(value['dispatches']) is not int
            or value['dispatches'] not in (0, 1) or value['execution_authorized'] is not False
            or value['native_acceptance'] != 'not_assessed'):
        raise ValueError('terminal runner outcome is invalid')
    for key in ('owner_published', 'stop_marker_published'):
        _boolean(value[key], 'runner ' + key)
    if value['stop_marker_published'] and not value['owner_published']:
        raise ValueError('terminal runner stop has no owner')
    return value


def _terminal_document(role, raw):
    if type(raw) is not bytes or len(raw) > TERMINAL_ROLES[role][1]:
        raise ValueError('terminal payload exceeds its fixed role bound')
    if role in ('owner_control_record', 'owner_transcript_suffix'):
        return None
    value = c.strict_json(raw, 'terminal ' + role, TERMINAL_ROLES[role][1])
    if role == 'owner':
        return validate_owner_record_v2(value)
    if role == 'owner_stop':
        c.exact(value, {'format', 'owner_sha256'}, 'terminal stop')
        if value['format'] != 'native_stream_owner_stop_v1':
            raise ValueError('unknown terminal stop format')
        c._hash(value['owner_sha256'], 'terminal stop owner hash')
    elif role == 'owner_runner_report':
        _runner_document(value)
    elif role == 'owner_close':
        _close_document(value)
    elif role == 'owner_failure':
        _failure_document(value)
    elif role == 'owner_worker_clock_close':
        if type(value) is dict and set(value) == {'capture_refused', 'reason'}:
            if value['capture_refused'] is not True or value['reason'] != 'worker clock close diagnostic unavailable':
                raise ValueError('terminal worker close refusal differs')
        else:
            _diagnostic(value)
    return value


def _lifecycle(value):
    c.exact(value, {'format', 'owner_create_completed', 'owner_identity', 'attempt_identity',
        'stop_create_attempted', 'stop_create_completed', 'control_created', 'stop_cut_state',
        'failed_members_copy_state', 'failure_summary_copy_state', 'close_report_copy_state',
        'runner_report_state', 'failed_member_pins'}, 'terminal lifecycle')
    if value['format'] != 'native_owner_terminal_lifecycle_v1':
        raise ValueError('unknown terminal lifecycle')
    for name in ('owner_create_completed', 'stop_create_attempted', 'stop_create_completed', 'control_created'):
        _boolean(value[name], 'terminal lifecycle ' + name)
    if value['owner_create_completed'] and not value['control_created']:
        raise ValueError('terminal owned owner requires its previously constructed control')
    if value['stop_create_attempted'] is not value['owner_create_completed'] or (
            value['stop_create_completed'] and not value['stop_create_attempted']):
        raise ValueError('terminal stop lifecycle differs')
    if value['owner_identity'] is not None:
        c.exact(value['owner_identity'], evidence._METADATA, 'terminal original owner metadata')
        evidence._metadata(value['owner_identity'], value['owner_identity']['size'])
        if not value['owner_create_completed']:
            raise ValueError('terminal owner identity has no successful create')
    if value['attempt_identity'] is not None:
        _identity(value['attempt_identity'])
    for name in ('stop_cut_state', 'failed_members_copy_state'):
        if value[name] not in ('captured', 'unavailable', 'not_created'):
            raise ValueError('terminal lifecycle capture state differs')
        if (value[name] == 'not_created') == value['control_created']:
            raise ValueError('terminal lifecycle contradicts control creation')
    for name in ('failure_summary_copy_state', 'close_report_copy_state'):
        if value[name] not in ('present', 'absent', 'unavailable', 'not_created'):
            raise ValueError('terminal lifecycle copy state differs')
        if (value[name] == 'not_created') == value['control_created']:
            raise ValueError('terminal lifecycle copy contradicts control creation')
    if value['runner_report_state'] not in ('normal', 'refused', 'unavailable'):
        raise ValueError('terminal report capture state differs')
    pins = value['failed_member_pins']
    if type(pins) is not dict or set(pins) - set(_FAILED_ROLES):
        raise ValueError('terminal failed-member roster differs')
    for name, pin in pins.items():
        _terminal_pin(pin, TERMINAL_ROLES[_FAILED_ROLES[name]][1])
    if pins and value['failed_members_copy_state'] != 'captured':
        raise ValueError('terminal failed pins claim an incomplete copy')
    return value


def _no_failure(life, report, close):
    return (life['stop_cut_state'] == life['failed_members_copy_state'] == 'captured'
        and life['failure_summary_copy_state'] == 'absent'
        and report.get('format') == 'native_owner_runner_report_v1' and report['state'] == 'completed'
        and close is not None and close.get('capture_complete') is True
        and close.get('operation_failed') is False and close.get('unfinished_workers') == 0)


def _absence(role, life, report, close, failure):
    """Return only a justified absence/refusal, never infer from a missing file."""
    if role == 'owner_stop':
        return 'capture_refused', 'stop_create_not_completed'
    if role in ('owner', 'owner_runner_report'):
        return 'capture_refused', 'frozen_capture_unavailable'
    if not life['control_created']:
        return 'not_produced', 'control_not_created'
    if role == 'owner_close':
        return 'capture_refused', 'close_report_capture_unavailable'
    if role == 'owner_worker_clock_close':
        if life['stop_cut_state'] == life['failed_members_copy_state'] == 'captured':
            return 'not_produced', 'absent_at_completed_stop_cut'
        return 'capture_refused', 'stop_cut_or_copy_unavailable'
    if role == 'owner_failure':
        if _no_failure(life, report, close):
            return 'not_produced', 'normal_close_without_failure_summary'
        return 'capture_refused', 'failure_summary_capture_unavailable'
    if role == 'owner_control_record':
        if failure is not None and failure['intended_record_exists'] is False:
            return 'not_produced', 'summary_declares_no_intended_record'
        if _no_failure(life, report, close):
            return 'not_produced', 'normal_close_without_intended_record'
        return 'capture_refused', 'intended_record_bytes_unavailable'
    if role == 'owner_transcript_suffix':
        if (life['failed_members_copy_state'] == 'captured' and close is not None
                and close.get('capture_complete') is True and close.get('operation_failed') is False
                and close.get('suffix', {}).get('bytes') == 0 and close.get('unfinished_workers') == 0):
            return 'not_produced', 'close_declares_no_failed_suffix'
        return 'capture_refused', 'frozen_capture_unavailable'
    raise ValueError('unknown terminal absence role')


def _terminal_counts(rows):
    result = dict.fromkeys(_COUNT_KEYS, 0)
    for row in rows:
        for field, prefix in (('retained', 'retained'), ('observed_partial', 'observed_partial')):
            if row[field] is not None:
                result[prefix + '_members'] += 1
                result[prefix + '_bytes'] += row[field]['pin']['bytes']
    return result


def _terminal_read(directory_fd, role, expected_identity=None):
    """One bounded fixed-name observation, preserving the first close error."""
    name, limit = TERMINAL_ROLES[role]
    fd, primary = None, None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        before = evidence._stat(os.fstat(fd))
        evidence._metadata(before, before['size'])
        if before['size'] > limit:
            raise ValueError('terminal observed file exceeds its role bound')
        if expected_identity is not None and any(before[key] != expected_identity[key] for key in ('device', 'inode')):
            raise ValueError('terminal observed file differs from owned identity')
        pieces, offset = [], 0
        while offset <= limit:
            raw = os.pread(fd, min(65_536, limit + 1 - offset), offset)
            if not raw:
                break
            pieces.append(raw)
            offset += len(raw)
        raw = b''.join(pieces)
        after = evidence._stat(os.fstat(fd))
        path_info = evidence._stat(os.stat(name, dir_fd=directory_fd, follow_symlinks=False))
        if len(raw) != before['size'] or len(raw) > limit or after != before or path_info != before:
            raise ValueError('terminal observation changed during capture')
        return raw, {'pin': owner._pin(raw), 'metadata': before}
    except BaseException as error:
        primary = error
        raise
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except BaseException:
                if primary is None:
                    raise


def _terminal_write(directory_fd, role, raw):
    """Fixed create-only publication; failed owned bytes may be observed once."""
    name, limit = TERMINAL_ROLES[role]
    if type(raw) is not bytes or len(raw) > limit:
        raise ValueError('terminal write exceeds fixed role bound')
    write = {'attempted': True, 'owned_create': False, 'identity': None,
             'stage': 'create', 'error': None}
    fd = None
    primary = None
    retained = partial = None
    try:
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK,
                     0o600, dir_fd=directory_fd)
        write['owned_create'] = True
        info = evidence._stat(os.fstat(fd))
        evidence._metadata(info, 0)
        write['identity'] = {key: info[key] for key in ('device', 'inode')}
        write['stage'] = 'write'
        offset = 0
        while offset < len(raw):
            count = os.write(fd, memoryview(raw)[offset:offset + 65_536])
            if type(count) is not int or not 0 < count <= min(65_536, len(raw) - offset):
                raise OSError('terminal write made invalid progress')
            offset += count
        write['stage'] = 'file_fsync'
        os.fsync(fd)
        write['stage'] = 'readback'
        before = evidence._stat(os.fstat(fd))
        evidence._metadata(before, len(raw))
        offset = 0
        while offset < len(raw):
            part = os.pread(fd, min(65_536, len(raw) - offset), offset)
            if not part or part != raw[offset:offset + len(part)]:
                raise ValueError('terminal publication readback differs')
            offset += len(part)
        if os.pread(fd, 1, len(raw)) or evidence._stat(os.fstat(fd)) != before:
            raise ValueError('terminal publication changed during readback')
        if evidence._stat(os.stat(name, dir_fd=directory_fd, follow_symlinks=False)) != before:
            raise ValueError('terminal publication path differs from its owned descriptor')
        write['stage'] = 'directory_fsync'
        os.fsync(directory_fd)
        retained = {'pin': owner._pin(raw), 'metadata': before}
    except BaseException as error:
        primary = error
    finally:
        if fd is not None:
            try:
                if primary is None:
                    write['stage'] = 'close'
                os.close(fd)
            except BaseException as error:
                if primary is None:
                    primary = error
    if primary is None:
        write['stage'] = 'complete'
    else:
        write['error'] = _error(primary)
        retained = None
        if write['owned_create'] and write['identity'] is not None:
            try:
                _, partial = _terminal_read(directory_fd, role, write['identity'])
            except BaseException:
                pass
    return write, retained, partial, primary


def _terminal_identities(execution_raw, started_raw, owner_raw):
    value = c.strict_json(execution_raw, 'terminal execution', REQUEST_LIMIT)
    own = _terminal_document('owner', owner_raw)
    return {'selection_sha256': value['selection_sha256'], 'execution_sha256': c.sha(execution_raw),
        'composition_sha256': value['composition_sha256'], 'started_sha256': c.sha(started_raw),
        'owner_sha256': c.sha(owner_raw), 'profile': own['coordination_profile']}


def _write_account(value):
    c.exact(value, {'attempted', 'owned_create', 'identity', 'stage', 'error'}, 'terminal write accounting')
    for name in ('attempted', 'owned_create'):
        _boolean(value[name], 'terminal write ' + name)
    if value['identity'] is not None:
        _identity(value['identity'])
        if not value['owned_create']:
            raise ValueError('terminal write identity is not owned')
    if value['owned_create'] and not value['attempted']:
        raise ValueError('terminal create claims an unattempted write')
    stages = {'not_attempted', 'create', 'write', 'file_fsync', 'readback', 'directory_fsync', 'close', 'complete'}
    if type(value['stage']) is not str or value['stage'] not in stages or (value['stage'] == 'not_attempted') == value['attempted']:
        raise ValueError('terminal write stage differs from attempted status')
    if value['stage'] == 'complete' and (not value['owned_create'] or value['identity'] is None or value['error'] is not None):
        raise ValueError('terminal completed write lacks owned successful identity')
    if value['error'] is not None:
        _diagnostic(value['error'])
    return value


def _terminal_row(row, role, attempt):
    c.exact(row, _ROW_KEYS, 'terminal role row')
    if (row['role'] != role or row['path'] != str(PurePosixPath(attempt) / TERMINAL_ROLES[role][0])
            or type(row['state']) is not str or row['state'] not in _BASES
            or type(row['basis']) is not str or row['basis'] not in _BASES[row['state']]):
        raise ValueError('terminal role path/state/basis differs')
    if row['intended'] is not None:
        # An intended record can exceed its retainable role limit; that is an
        # explicit capture refusal, never a retained over-limit payload.
        _terminal_pin(row['intended'])
    for name in ('retained', 'observed_partial'):
        item = row[name]
        if item is not None:
            c.exact(item, {'pin', 'metadata'}, 'terminal captured ' + name)
            _terminal_pin(item['pin'], TERMINAL_ROLES[role][1])
            evidence._metadata(item['metadata'], item['pin']['bytes'])
    if row['write'] is not None:
        _write_account(row['write'])
    if row['state'] == 'retained':
        if row['retained'] is None or row['observed_partial'] is not None or row['intended'] != row['retained']['pin']:
            raise ValueError('terminal retained role differs from intended bytes')
        expected = 'retained_owned_owner' if role == 'owner' else ('retained_owned_stop' if role == 'owner_stop' else 'retained_frozen_member')
        if row['basis'] != expected:
            raise ValueError('terminal retained basis differs from role')
        if role in ('owner', 'owner_stop'):
            if row['write'] is not None:
                raise ValueError('terminal existing owner/stop is not a new write')
        elif row['write'] is None or row['write']['stage'] != 'complete':
            raise ValueError('terminal retained publication lacks completion')
    elif row['state'] in ('not_produced', 'capture_refused'):
        if row['retained'] is not None or row['observed_partial'] is not None or row['write'] is not None:
            raise ValueError('terminal absent/refused role claims publication bytes')
        if row['state'] == 'not_produced' and row['intended'] is not None:
            raise ValueError('terminal nonproduction contradicts intended bytes')
    else:
        if role in ('owner', 'owner_stop') or row['retained'] is not None or row['intended'] is None or row['write'] is None:
            raise ValueError('terminal failed publication lacks intended write')
        write = row['write']
        if write['stage'] == 'complete':
            raise ValueError('terminal failed publication claims completed write')
        if row['observed_partial'] is not None:
            if (not write['attempted'] or not write['owned_create'] or write['identity'] is None
                    or row['basis'] != 'write_failed_partial_observed'
                    or any(row['observed_partial']['metadata'][k] != write['identity'][k] for k in ('device', 'inode'))):
                raise ValueError('terminal failed partial is not its owned exclusive create')
        elif row['basis'] == 'write_failed_partial_observed':
            raise ValueError('terminal failed partial bytes are missing')
        if row['basis'] == 'preflight_refused':
            raise ValueError('terminal preflight refusal cannot have a published manifest')
        if row['basis'] == 'not_attempted_after_publication_failure':
            if write != {'attempted': False, 'owned_create': False, 'identity': None,
                         'stage': 'not_attempted', 'error': None}:
                raise ValueError('terminal unattempted role has write effects')
        elif write['error'] is None:
            raise ValueError('terminal failed write lacks original error')
    if row['write'] is not None and row['retained'] is not None:
        if any(row['retained']['metadata'][key] != row['write']['identity'][key] for key in ('device', 'inode')):
            raise ValueError('terminal retained file differs from exclusive-create identity')
    return row


def validate_terminal_capture(pool, value):
    """Validate the exact saved terminal closure, with no live authority or I/O."""
    from . import native_shared_capture as captured
    if type(pool) is not evidence.CapturePool or pool.stream_bindings:
        raise ValueError('terminal evidence requires an exact pool without stream bindings')
    selected = captured._saved_selection(pool, value)
    bounds = selected.bounds()
    total = sum(member.captured.pin.bytes for member in pool.members)
    if total > min(bounds['max_evidence_bytes'], c.HARD_LIMITS['evidence_raw_total_bytes']):
        raise ValueError('terminal closure exceeds its complete selected byte bound')
    execution = captured._saved_member(pool, 'execution_capture', selected.role('execution_capture')).captured
    actual, _ = captured._saved_owner_execution(selected, pool, execution)
    if c.canonical(actual) != c.canonical(value):
        raise ValueError('terminal execution argument differs from exact captured typed value')
    started = captured._saved_member(pool, 'started_capture', selected.role('started_capture')).captured
    attempt = actual['attempt_directory']
    own_member = captured._saved_member(pool, 'owner', str(PurePosixPath(attempt) / TERMINAL_ROLES['owner'][0]))
    own = captured._saved_owner(selected, pool, execution, started, own_member.captured)
    manifest_member = captured._saved_member(pool, 'owner_retention',
        str(PurePosixPath(attempt) / TERMINAL_ROLES['owner_retention'][0]))
    raw = manifest_member.captured.raw
    manifest = c.strict_json(raw, 'terminal manifest', TERMINAL_ROLES['owner_retention'][1])
    c.exact(manifest, {'format', 'scope', 'identities', 'lifecycle', 'runner_report', 'roles', 'counts',
        'retention_complete', 'execution_authorized', 'native_acceptance'}, 'terminal manifest')
    if (manifest['format'] != 'native_owner_terminal_retention_v1' or manifest['scope'] != _TERMINAL_SCOPE
            or manifest['execution_authorized'] is not False or manifest['native_acceptance'] != 'not_assessed'
            or _terminal_json(manifest) != raw):
        raise ValueError('terminal manifest format/canonical scope differs')
    expected_identities = _terminal_identities(execution.raw, started.raw, own_member.captured.raw)
    if c.canonical(manifest['identities']) != c.canonical(expected_identities):
        raise ValueError('terminal manifest identities differ from captured S/E/started/owner')
    life = _lifecycle(manifest['lifecycle'])
    if (not life['owner_create_completed'] or life['owner_identity'] is None
            or life['attempt_identity'] is None or not life['stop_create_attempted']):
        raise ValueError('terminal lifecycle lacks owned publication prerequisites')
    if type(manifest['roles']) is not list or len(manifest['roles']) != len(TERMINAL_ROLE_ORDER):
        raise ValueError('terminal manifest role denominator differs')
    rows = [_terminal_row(row, role, attempt) for row, role in zip(manifest['roles'], TERMINAL_ROLE_ORDER)]
    by_role = {row['role']: row for row in rows}
    if any(by_role[role]['state'] != 'retained' for role in ('owner', 'owner_runner_report')):
        raise ValueError('terminal closure lacks retained owner/runner prerequisites')
    allowed = {(item.pin.role, item.pin.path) for item in (selected.registration, selected.receipt_policy,
        *selected.authority, *(item for schema in selected.schemas for item in schema.sources), execution, started)}
    allowed.add(('owner_retention', manifest_member.captured.pin.path))
    documents, raw_by_role = {}, {}
    for row in rows:
        for field in ('retained', 'observed_partial'):
            record = row[field]
            if record is None:
                continue
            member = captured._saved_member(pool, row['role'], row['path'])
            if (owner._pin(member.captured.raw) != record['pin']
                    or c.canonical(record['metadata']) != member.metadata_json):
                raise ValueError('terminal captured bytes/metadata differ from manifest')
            allowed.add((row['role'], row['path']))
            if field == 'retained':
                documents[row['role']] = _terminal_document(row['role'], member.captured.raw)
                raw_by_role[row['role']] = member.captured.raw
    supplied = [(m.captured.pin.role, m.captured.pin.path) for m in pool.members]
    if len(supplied) != len(set(supplied)) or set(supplied) != allowed:
        raise ValueError('terminal pool contains missing, duplicate or extra roles')
    if by_role['owner']['retained']['metadata'] != life['owner_identity']:
        raise ValueError('terminal owner differs from original captured identity')
    report = documents['owner_runner_report']
    if owner._pin(raw_by_role['owner_runner_report']) != manifest['runner_report']:
        raise ValueError('terminal report differs from frozen intended report')
    _terminal_pin(manifest['runner_report'], TERMINAL_ROLES['owner_runner_report'][1])
    expected_report_state = 'normal' if report['format'] == 'native_owner_runner_report_v1' else 'refused'
    if (life['runner_report_state'] != expected_report_state
            or report['owner_published'] is not life['owner_create_completed']
            or report['stop_marker_published'] is not life['stop_create_completed']):
        raise ValueError('terminal runner report differs from frozen lifecycle')
    close = documents.get('owner_close')
    failure = documents.get('owner_failure')
    # A normal report retains its own close value even if the separate close
    # artifact could not be published. It remains the same declared lifecycle.
    report_close = report.get('control_close')
    if close is not None and report_close is not None and c.canonical(close) != c.canonical(report_close):
        raise ValueError('terminal close differs from frozen runner report')
    basis_close = close if close is not None else report_close
    if (basis_close is not None and basis_close.get('format') in ('native_owner_close_v1', 'native_owner_close_v2')
            and (failure is not None or life['failure_summary_copy_state'] == 'present')
            and basis_close['operation_failed'] is not True):
        raise ValueError('terminal normal close contradicts its retained failure-summary lifecycle')
    if report['format'] == 'native_owner_runner_report_v1':
        if life['close_report_copy_state'] == 'present' and report_close is None:
            raise ValueError('terminal close capture contradicts retained report')
        if life['close_report_copy_state'] in ('absent', 'not_created') and report_close is not None:
            raise ValueError('terminal report close contradicts absence')
    if by_role['owner_stop']['state'] == 'retained':
        if not life['stop_create_completed'] or documents['owner_stop']['owner_sha256'] != c.sha(raw_by_role['owner']):
            raise ValueError('terminal stop publication differs from owned marker')
    elif by_role['owner_stop']['state'] != 'capture_refused':
        raise ValueError('terminal eligible stop cannot be not produced')
    else:
        expected = 'stop_observation_refused' if life['stop_create_completed'] else 'stop_create_not_completed'
        if by_role['owner_stop']['basis'] != expected:
            raise ValueError('terminal stop refusal contradicts publication lifecycle')
    if by_role['owner_stop']['intended'] != owner._pin(owner._json(
            {'format': 'native_stream_owner_stop_v1', 'owner_sha256': c.sha(raw_by_role['owner'])})):
        raise ValueError('terminal intended stop bytes differ')
    prior_publication_failure = any(by_role[role]['state'] == 'capture_refused' and
        by_role[role]['basis'] in ('owner_observation_refused', 'stop_observation_refused')
        for role in ('owner', 'owner_stop'))
    for row in rows[2:]:
        if row['state'] == 'publication_failed':
            if prior_publication_failure and row['basis'] != 'not_attempted_after_publication_failure':
                raise ValueError('terminal payload write resumed after first publication failure')
            if row['basis'] == 'not_attempted_after_publication_failure' and not prior_publication_failure:
                raise ValueError('terminal unattempted write has no preceding publication failure')
            prior_publication_failure = True
        elif row['state'] == 'retained' and prior_publication_failure:
            raise ValueError('terminal payload resumed after first publication failure')
    for role in TERMINAL_ROLE_ORDER[3:]:
        row = by_role[role]
        name = next((key for key, found in _FAILED_ROLES.items() if found == role), None)
        frozen_pin = life['failed_member_pins'].get(name) if name is not None else None
        if frozen_pin is not None:
            if row['intended'] != frozen_pin or row['state'] not in ('retained', 'publication_failed'):
                raise ValueError('terminal failed member differs from frozen cut pin')
        elif name is not None and row['state'] in ('retained', 'publication_failed'):
            raise ValueError('terminal role was absent from frozen failed-member copy')
        if role == 'owner_close' and row['state'] in ('retained', 'publication_failed'):
            if life['close_report_copy_state'] != 'present':
                raise ValueError('terminal close bytes were not copied')
            if report_close is not None and row['intended'] != owner._pin(owner._json(report_close)):
                # Existing close fallbacks use canonical compact JSON too.
                raise ValueError('terminal close intended bytes differ from report')
        if role == 'owner_failure' and row['state'] in ('retained', 'publication_failed'):
            if life['failure_summary_copy_state'] != 'present':
                raise ValueError('terminal failure summary was not copied')
        if role in ('owner_close', 'owner_failure'):
            field = 'close_report_copy_state' if role == 'owner_close' else 'failure_summary_copy_state'
            if (life[field] == 'present') != (row['state'] in ('retained', 'publication_failed')):
                raise ValueError('terminal role state discards available frozen summary bytes')
        if row['state'] in ('not_produced', 'capture_refused'):
            expected = _absence(role, life, report, basis_close, failure)
            if (row['state'], row['basis']) != expected:
                raise ValueError('terminal absence/refusal is not established by frozen facts')
    if failure is not None:
        record = by_role['owner_control_record']
        commit = failure['control_commit']
        if record['state'] == 'retained':
            if not failure['intended_record_exists'] or commit is None or record['intended'] != commit['record']:
                raise ValueError('terminal retained control record differs from failure snapshot')
        if commit is not None and record['intended'] != commit['record']:
            raise ValueError('terminal intended record pin differs from failure summary')
        if basis_close is not None and basis_close.get('format') == 'native_owner_close_v2':
            transcript = failure['transcript']
            if (basis_close['written_bytes_at_stop'] != transcript['written_bytes']
                    or basis_close['admitted_bytes_at_stop'] != transcript['admitted_bytes']):
                raise ValueError('terminal failure cut and close entry accounting differ')
    suffix = by_role['owner_transcript_suffix']
    if suffix['state'] in ('retained', 'publication_failed') and basis_close is not None and 'suffix' in basis_close:
        if suffix['intended'] != basis_close['suffix']:
            raise ValueError('terminal unwritten suffix differs from close report')
    c.exact(manifest['counts'], _COUNT_KEYS, 'terminal manifest counts')
    for key in _COUNT_KEYS:
        _natural(manifest['counts'][key], 'terminal count ' + key)
    counts = _terminal_counts(rows)
    if manifest['counts'] != counts:
        raise ValueError('terminal manifest counts differ from retained bytes')
    complete = all(row['state'] in ('retained', 'not_produced') for row in rows)
    if manifest['retention_complete'] is not complete:
        raise ValueError('terminal retention status differs from complete denominator')
    return _terminal_json({'format': 'native_owner_terminal_evidence_v1', 'scope': _TERMINAL_SCOPE,
        'identities': expected_identities, 'roles': rows, 'counts': {'members': len(pool.members),
        'raw_bytes': total, **counts}, 'captured_manifest_complete': True,
        'publisher_completion_attested': False, 'retention_complete': complete,
        'execution_authorized': False, 'native_acceptance': 'not_assessed'})


def _binding(execution_raw, started_raw, *, selected, argv, instruction, attempt,
             cwd, env, deadline_seconds, command_policy):
    e = c.strict_json(execution_raw, 'private execution association', REQUEST_LIMIT)
    s = c.strict_json(started_raw, 'private started association', REQUEST_LIMIT)
    if (type(e) is not dict or e.get('kind') != c.KINDS['execution']
            or type(e.get('version')) is not int or e['version'] != 1
            or type(s) is not dict or s.get('kind') != 'd4d_native_shared_attempt'
            or type(s.get('version')) is not int or s['version'] != 1
            or s.get('state') != 'started' or type(s.get('dispatch_limit')) is not int
            or s['dispatch_limit'] != 1):
        raise ValueError('private runner requires shared execution/started association')
    attempt_path = _physical(attempt, 'attempt', directory=True)
    cwd_path = _physical(cwd, 'working directory', directory=True)
    if (type(e.get('attempt_id')) is not str or not e['attempt_id']
            or e['attempt_id'] != attempt_path.name or s.get('attempt_id') != e['attempt_id']
            or e.get('attempt_directory') != str(attempt_path)
            or e.get('working_directory') != str(cwd_path)
            or s.get('registration_sha256') != c.sha(execution_raw)
            or _canonical(e.get('dependencies')) != _canonical(selected)):
        raise ValueError('private runner execution/started binding differs')
    if (type(argv) is not list or not argv or any(type(v) is not str or not v for v in argv)
            or type(env) is not dict or any(type(k) is not str or type(v) is not str for k, v in env.items())
            or _canonical(argv) != _canonical(e.get('argv'))
            or _canonical(env) != _canonical(e.get('environment'))
            or type(e.get('runtime')) is not dict
            or type(e['runtime'].get('deadline_seconds')) is not int
            or e['runtime']['deadline_seconds'] != deadline_seconds):
        raise ValueError('private runner dispatch inputs differ from execution')
    if type(e.get('composition_raw_json')) is not str:
        raise ValueError('private runner requires captured composition bytes')
    composition_raw = e['composition_raw_json'].encode('utf-8')
    selected_c = c.strict_json(composition_raw, 'private composition association', REQUEST_LIMIT)
    if (type(selected_c) is not dict
            or selected_c.get('kind') != 'd4d_native_shared_callback_composition'
            or type(selected_c.get('version')) is not int or selected_c['version'] != 1
            or c.sha(composition_raw) != e.get('composition_sha256')
            or s.get('composition_sha256') != e.get('composition_sha256')
            or selected_c.get('working_directory') != str(cwd_path)):
        raise ValueError('private runner captured composition differs')
    instruction_path = _physical(instruction, 'instruction')
    if str(instruction_path) != selected_c.get('instruction_path'):
        raise ValueError('private runner instruction path differs')
    digest = c._hash(selected_c.get('instruction_sha256'), 'instruction digest')
    if e.get('instruction_sha256') != digest:
        raise ValueError('private runner instruction digests differ')
    captured = evidence.read_regular(str(instruction_path), 'instruction', max_bytes=REQUEST_LIMIT).captured.raw
    if c.sha(captured) != digest:
        raise ValueError('private runner instruction bytes differ')
    text = captured.decode('utf-8')
    policy_raw = _canonical(selected_c.get('policy'))
    if (type(command_policy) is not dict or type(selected_c.get('policy')) is not dict
            or c.sha(policy_raw) != selected_c.get('policy_sha256')
            or _canonical(command_policy) != policy_raw):
        raise ValueError('private runner command policy differs')
    if '--input-format' not in argv or argv.count('--input-format') != 1:
        raise ValueError('private runner requires one stream-json input selector')
    at = argv.index('--input-format')
    if at + 1 == len(argv) or argv[at + 1] != 'stream-json':
        raise ValueError('private runner requires stream-json input')
    return {'attempt': attempt_path, 'cwd': cwd_path, 'instruction_path': instruction_path,
            'instruction_raw': captured, 'instruction': text, 'policy_raw': policy_raw,
            'policy': c.strict_json(policy_raw, max_bytes=REQUEST_LIMIT),
            'argv': list(e['argv']), 'env': dict(e['environment']),
            'argv_raw': _canonical(argv), 'env_raw': _canonical(env)}


def _make_runner(scope, declaration, controls, control_class):
    """Fixed profile-only factory. No arbitrary module/launcher selection."""
    from . import native_owner_profile_v1 as profile
    bound = dict(controls)
    frozen = bound['run_native_canary']
    BudgetStop = bound['budgeted_cborg'].BudgetStop
    selected = authority.dependency_identity(stream_snapshot_profile=1)
    if _canonical(selected['stream_snapshot_profile']) != _canonical(declaration):
        raise ValueError('private runner selected source profile differs')

    def graph():
        scope.require()
        profile._origin('runner', sys.modules[__name__])
        if (any(sys.modules.get(name) is not module for name, module in bound.items())
                or frozen.BudgetStop is not BudgetStop or control_class.budget_stop_type is not BudgetStop):
            raise ValueError('private runner has a stale or foreign loader graph')

    graph()

    class BoundRunner:
        budget_stop_type = BudgetStop

        def __init__(self):
            self._entry = threading.Lock()
            self._used = False
            self._owner_bytes = None
            self._report_bytes = None
            self._failed = {}
            self._creator = threading.current_thread()
            self._terminal_ready = False
            self._terminal_used = False
            self._terminal_snapshot = None
            self._terminal_error = None
            self._terminal_publication = None
            self._terminal_execution = self._terminal_started = None
            self._terminal_attempt = None
            self._terminal_close = None
            self._terminal_life = {'format': 'native_owner_terminal_lifecycle_v1',
                'owner_create_completed': False, 'owner_identity': None, 'attempt_identity': None,
                'stop_create_attempted': False, 'stop_create_completed': False,
                'control_created': False, 'stop_cut_state': 'not_created',
                'failed_members_copy_state': 'not_created', 'failure_summary_copy_state': 'not_created',
                'close_report_copy_state': 'not_created', 'runner_report_state': 'unavailable',
                'failed_member_pins': {}}

        def owner_raw(self):
            return self._owner_bytes

        def report(self):
            return json.loads(self._report_bytes) if self._report_bytes is not None else None

        def failed_members(self):
            return dict(self._failed)

        def terminal_snapshot(self):
            if not self._terminal_ready:
                raise ValueError('private owner terminal snapshot is not ready')
            if self._terminal_snapshot is None:
                raise ValueError('private owner terminal snapshot capture refused') from self._terminal_error
            return self._terminal_snapshot

        def terminal_publication_report(self):
            return json.loads(self._terminal_publication) if self._terminal_publication is not None else None

        def _freeze_terminal(self):
            """Called once after descriptor/lease cleanup, never by a late getter."""
            try:
                life = self._terminal_life
                life['owner_create_completed'] = self._owner_bytes is not None
                life['runner_report_state'] = ('normal' if json.loads(self._report_bytes)['format']
                    == 'native_owner_runner_report_v1' else 'refused')
                payload = {}
                for role, raw in (('owner', self._owner_bytes), ('owner_runner_report', self._report_bytes),
                        ('owner_close', self._terminal_close), ('owner_failure', self._failed.get('failure_summary'))):
                    if raw is not None:
                        _terminal_document(role, raw)
                        payload[role] = raw
                for name, role in _FAILED_ROLES.items():
                    if name in self._failed:
                        raw = self._failed[name]
                        _terminal_document(role, raw)
                        payload[role] = raw
                        life['failed_member_pins'][name] = owner._pin(raw)
                if sum(map(len, payload.values())) > c.HARD_LIMITS['evidence_raw_total_bytes']:
                    raise ValueError('terminal snapshot exceeds aggregate byte bound')
                _lifecycle(life)
                projection = {'format': 'native_owner_terminal_snapshot_v1', 'lifecycle': life,
                    'runner_report': owner._pin(self._report_bytes),
                    'close_report': owner._pin(self._terminal_close) if self._terminal_close is not None else None,
                    'failure_summary': owner._pin(payload['owner_failure']) if 'owner_failure' in payload else None,
                    'failed_members': life['failed_member_pins']}
                self._terminal_snapshot = (_terminal_json(projection),
                    tuple((role, payload[role]) for role in TERMINAL_ROLE_ORDER if role in payload))
            except BaseException as error:
                self._terminal_error = error
            finally:
                self._terminal_ready = True

        def publish_terminal(self):
            if threading.current_thread() is not self._creator:
                raise ValueError('terminal publication requires its creator thread')
            with self._entry:
                if self._terminal_used:
                    raise ValueError('terminal publication is one-use')
                self._terminal_used = True
            result = {'format': 'native_owner_terminal_publication_v1', 'state': 'refused',
                'error': None, 'roles': [], 'manifest': None, 'manifest_finalized': False,
                'retention_complete': False, 'execution_authorized': False, 'native_acceptance': 'not_assessed'}
            primary = None
            directory_fd = None
            try:
                projection_raw, pairs = self.terminal_snapshot()
                projection = json.loads(projection_raw)
                life = projection['lifecycle']
                if (not life['owner_create_completed'] or life['owner_identity'] is None
                        or life['attempt_identity'] is None or self._terminal_attempt is None):
                    raise ValueError('terminal publication lacks its own captured owner/directory identity')
                payload = dict(pairs)
                attempt = self._terminal_attempt
                _physical(attempt, 'terminal attempt', directory=True)
                directory_fd = os.open(str(attempt), os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)

                def directory_current():
                    opened = os.fstat(directory_fd)
                    path_info = Path(attempt).lstat()
                    identity = life['attempt_identity']
                    if (not stat.S_ISDIR(opened.st_mode) or not stat.S_ISDIR(path_info.st_mode)
                            or any(getattr(info, attr) != identity[key]
                                   for info in (opened, path_info)
                                   for attr, key in (('st_dev', 'device'), ('st_ino', 'inode')))
                            or str(Path(attempt).resolve(strict=True)) != str(attempt)):
                        raise ValueError('terminal attempt directory differs from its original identity')

                directory_current()
                for role, (name, _) in TERMINAL_ROLES.items():
                    if role in ('owner', 'owner_stop'):
                        continue
                    try:
                        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise ValueError('terminal publication destination already exists: ' + name)
                report = _terminal_document('owner_runner_report', payload['owner_runner_report'])
                close = _terminal_document('owner_close', payload['owner_close']) if 'owner_close' in payload else None
                failure = _terminal_document('owner_failure', payload['owner_failure']) if 'owner_failure' in payload else None
                rows = []
                result['roles'] = rows
                for role in TERMINAL_ROLE_ORDER:
                    raw = payload.get(role)
                    if role == 'owner_stop':
                        raw = owner._json({'format': 'native_stream_owner_stop_v1',
                                         'owner_sha256': c.sha(payload['owner'])})
                    row = {'role': role, 'path': str(PurePosixPath(str(attempt)) / TERMINAL_ROLES[role][0]),
                        'state': 'capture_refused', 'intended': owner._pin(raw) if raw is not None else None,
                        'retained': None, 'basis': 'frozen_capture_unavailable', 'write': None,
                        'observed_partial': None}
                    rows.append(row)
                    if role in ('owner', 'owner_stop'):
                        if role == 'owner_stop' and not life['stop_create_completed']:
                            row['basis'] = 'stop_create_not_completed'
                            continue
                        try:
                            directory_current()
                            observed, retained = _terminal_read(directory_fd, role,
                                life['owner_identity'] if role == 'owner' else None)
                            if observed != raw or (role == 'owner' and retained['metadata'] != life['owner_identity']):
                                raise ValueError('terminal original publication differs from retained identity')
                            _terminal_document(role, observed)
                            directory_current()
                            row.update(state='retained', retained=retained, basis='retained_owned_' +
                                       ('owner' if role == 'owner' else 'stop'))
                        except BaseException as error:
                            row['basis'] = role + '_observation_refused' if role == 'owner' else 'stop_observation_refused'
                            if primary is None:
                                primary = error
                        continue
                    if raw is None:
                        row['state'], row['basis'] = _absence(role, life, report, close, failure)
                        if role == 'owner_control_record' and failure is not None and failure['control_commit'] is not None:
                            row['intended'] = failure['control_commit']['record']
                        continue
                    if primary is not None:
                        row.update(state='publication_failed', basis='not_attempted_after_publication_failure',
                            write={'attempted': False, 'owned_create': False, 'identity': None,
                                   'stage': 'not_attempted', 'error': None})
                        continue
                    try:
                        directory_current()
                        write, retained, partial, error = _terminal_write(directory_fd, role, raw)
                    except BaseException as error:
                        write = {'attempted': False, 'owned_create': False, 'identity': None,
                                 'stage': 'not_attempted', 'error': _error(error)}
                        retained = partial = None
                        failure_error = error
                    else:
                        failure_error = error
                        if failure_error is None:
                            try:
                                directory_current()
                            except BaseException as changed:
                                failure_error = changed
                                write.update(stage='readback', error=_error(changed))
                                partial, retained = retained, None
                    row.update(write=write, retained=retained, observed_partial=partial)
                    if failure_error is None:
                        row.update(state='retained', basis='retained_frozen_member')
                    else:
                        row.update(state='publication_failed', basis='write_failed_partial_observed' if partial is not None
                                   else 'partial_bytes_unavailable_or_uncaptured')
                        primary = failure_error
                retention_complete = all(row['state'] in ('retained', 'not_produced') for row in rows)
                identities = _terminal_identities(self._terminal_execution, self._terminal_started, payload['owner'])
                manifest = {'format': 'native_owner_terminal_retention_v1', 'scope': _TERMINAL_SCOPE,
                    'identities': identities, 'lifecycle': life, 'runner_report': projection['runner_report'],
                    'roles': rows, 'counts': _terminal_counts(rows), 'retention_complete': retention_complete,
                    'execution_authorized': False, 'native_acceptance': 'not_assessed'}
                raw = _terminal_json(manifest)
                # Manifest publication is one final attempt, never a payload retry.
                directory_current()
                write, retained, partial, error = _terminal_write(directory_fd, 'owner_retention', raw)
                result['manifest'] = {'path': str(attempt / TERMINAL_ROLES['owner_retention'][0]),
                    'intended': owner._pin(raw), 'write': write, 'retained': retained, 'observed_partial': partial}
                if error is None:
                    try:
                        directory_current()
                    except BaseException as changed:
                        error = changed
                        write.update(stage='readback', error=_error(changed))
                        result['manifest']['observed_partial'] = retained
                        result['manifest']['retained'] = None
                result['manifest_finalized'] = error is None
                result['retention_complete'] = retention_complete
                if primary is None:
                    primary = error
                result['state'] = 'published' if error is None and primary is None else 'publication_failed'
            except BaseException as error:
                if primary is None:
                    primary = error
                if result['roles']:
                    result['state'] = 'publication_failed'
            finally:
                if directory_fd is not None:
                    try:
                        os.close(directory_fd)
                    except BaseException as error:
                        if primary is None:
                            primary = error
                        result['state'] = 'publication_failed'
                        result['manifest_finalized'] = False
                if primary is not None:
                    result['error'] = _error(primary)
                self._terminal_publication = _terminal_json(result)
            if primary is not None:
                raise primary
            return self.terminal_publication_report()

        def execute_child(self, argv, *, proxy, instruction, attempt, cwd, env,
                          deadline_seconds, verify_launch, record_stop,
                          command_policy, command_classifier, event_observer,
                          execution_raw, started_raw, phase_spec=None):
            start = time.monotonic_ns()
            with self._entry:
                if self._used:
                    raise ValueError('private owner runner is one-use')
                self._used = True
            process = control = None
            primary = None
            cleanup = []
            dispatches = 0
            published = stopped = False
            result = None
            deadline = None
            parent_clock = None
            streams = {}
            anchors = {}

            def problem(stage, error):
                cleanup.append((stage, error))

            def close_stream(role, stream):
                try:
                    if not stream.closed:
                        stream.close()
                except BaseException as error:
                    problem('close_' + role, error)

            def budget():
                graph()
                parent_clock.require_current()
                if proxy.failed.is_set():
                    raise BudgetStop(proxy.failure)
                if time.monotonic_ns() >= deadline:
                    raise BudgetStop('native attempt deadline elapsed; retain all incomplete charge reservations')

            def stream_identity():
                for role, stream in streams.items():
                    path = Path(stream.name)
                    current = evidence._stat(os.fstat(stream.fileno()))
                    evidence._metadata(current, current['size'])
                    observed = evidence._stat(path.lstat())
                    if (observed != current or str(path.resolve(strict=True)) != str(path)
                            or any(current[k] != anchors[role][k] for k in ('device', 'inode'))):
                        raise ValueError('private runner owned stream identity changed')

            with ExitStack() as stack:
                try:
                    c.positive_int(deadline_seconds, 'private runner deadline seconds')
                    deadline = start + deadline_seconds * 1_000_000_000
                    graph()
                    if phase_spec is not None or not all(callable(f) for f in
                            (verify_launch, record_stop, command_classifier, event_observer)):
                        raise ValueError('private runner requires the fixed shared/history callbacks')
                    if type(getattr(proxy, 'failed', None)) is not threading.Event:
                        raise ValueError('private runner requires the actual proxy stop event')
                    parent_clock = clocks.capture_domain()
                    # First callback closes last, after all owned descriptors.
                    def close_clock():
                        try:
                            parent_clock.close()
                        except BaseException as error:
                            problem('clock_close', error)
                    stack.callback(close_clock)
                    budget()
                    values = _binding(execution_raw, started_raw, selected=selected,
                        argv=argv, instruction=instruction, attempt=attempt, cwd=cwd, env=env,
                        deadline_seconds=deadline_seconds, command_policy=command_policy)
                    if _canonical(values['policy'].get('pretool_control')) != _canonical(bound['native_control'].HISTORY_CONTRACT):
                        raise ValueError('private runner requires the unchanged history contract')
                    authority.require_committed(selected)
                    budget()
                    target = values['attempt']
                    self._terminal_execution, self._terminal_started = execution_raw, started_raw
                    self._terminal_attempt = target
                    target_info = target.lstat()
                    if not stat.S_ISDIR(target_info.st_mode):
                        raise ValueError('private runner attempt directory identity is unavailable')
                    self._terminal_life['attempt_identity'] = {'device': target_info.st_dev, 'inode': target_info.st_ino}
                    for name in FILES:
                        if os.path.lexists(target / name):
                            raise ValueError('private runner destination already exists: ' + name)
                    for role, name in (('transcript', 'transcript.jsonl'), ('control', 'control.jsonl'), ('stderr', 'stderr.txt')):
                        stream = (target / name).open('xb', buffering=0)
                        stack.callback(close_stream, role, stream)
                        streams[role] = stream
                        anchors[role] = evidence._stat(os.fstat(stream.fileno()))
                    stream_identity()
                    if len({(m['device'], m['inode']) for m in anchors.values()}) != len(anchors):
                        raise ValueError('private runner stream identities alias')
                    control = control_class(values['policy'], command_classifier, values['env'].get('CLAUDE_CONFIG_DIR'),
                        event_observer=event_observer, attempt_deadline_ns=deadline, stop_event=proxy.failed,
                        owner_clock_domain=parent_clock.declaration())
                    self._terminal_life.update(control_created=True, stop_cut_state='unavailable',
                        failed_members_copy_state='unavailable', failure_summary_copy_state='unavailable',
                        close_report_copy_state='unavailable')
                    parent_scope = coordination.reader_budget(control._owner_budget,
                        clock_lease=parent_clock)
                    parent_scope.__enter__()
                    def close_scope():
                        try:
                            parent_scope.__exit__(None, None, None)
                        except BaseException as error:
                            problem('clock_scope_close', error)
                    stack.callback(close_scope)
                    proxy.control_shutdown = {'control_initialized': True,
                        'control_shutdown_complete': False, 'unfinished_control_workers': None}
                    raw = owner._json(validate_owner_record_v2({'format': 'native_stream_owner_v2',
                        'coordination_profile': json.loads(scope.profile),
                        'execution_sha256': c.sha(execution_raw), 'started_sha256': c.sha(started_raw),
                        'owner_pid': os.getpid(), 'clock': 'monotonic_ns', 'start_ns': start,
                        'clock_domain': parent_clock.declaration(),
                        'deadline_ns': deadline, 'duration_ns': deadline_seconds * 1_000_000_000,
                        **{role: {'path': str(streams[role].name), 'device': anchors[role]['device'],
                            'inode': anchors[role]['inode']} for role in ('transcript', 'control')}}))
                    budget()
                    durable.durable_new(target / 'stream-owner.json', raw)
                    self._owner_bytes = raw
                    published = True
                    stream_identity()
                    owner_readback = evidence.read_regular(str(target / 'stream-owner.json'), 'owner',
                            max_bytes=owner.SUMMARY_LIMIT)
                    if owner_readback.captured.raw != raw:
                        raise ValueError('private runner published owner differs')
                    self._terminal_life['owner_identity'] = c.strict_json(owner_readback.metadata_json)
                    budget()
                    verify_launch()
                    budget()
                    if (_canonical(argv) != values['argv_raw'] or _canonical(env) != values['env_raw']
                            or _canonical(command_policy) != values['policy_raw']):
                        raise ValueError('private runner dispatch input changed during verification')
                    if evidence.read_regular(str(values['instruction_path']), 'instruction',
                            max_bytes=REQUEST_LIMIT).captured.raw != values['instruction_raw']:
                        raise ValueError('private runner instruction changed during verification')
                    authority.require_committed(selected)
                    stream_identity()
                    if evidence.read_regular(str(target / 'stream-owner.json'), 'owner',
                            max_bytes=owner.SUMMARY_LIMIT).captured.raw != raw:
                        raise ValueError('private runner owner changed during verification')
                    _physical(values['cwd'], 'working directory', directory=True)
                    _physical(target, 'attempt', directory=True)
                    budget()
                    process = _spawn(values['argv'], stderr=streams['stderr'],
                                     cwd=str(values['cwd']), env=values['env'])
                    dispatches = 1
                    stack.callback(close_stream, 'stdout', process.stdout)
                    stack.callback(close_stream, 'stdin', process.stdin)
                    control.start(process, streams['transcript'], streams['control'], values['instruction'])
                    while process.poll() is None or not control.stdout_closed:
                        budget()
                        control.service()
                    control.finish()
                    budget()
                    result = process.returncode
                except BaseException as error:
                    primary = error
                    if control is not None:
                        control._latch_failure(error)
                    try:
                        failed = getattr(proxy, 'failed', None)
                        if failed is None or not failed.is_set():
                            reason = str(error) if isinstance(error, BudgetStop) else 'unexpected ' + type(error).__name__
                            frozen.record_then_close(proxy, record_stop, reason)
                    except BaseException as secondary:
                        problem('record_stop', secondary)
                finally:
                    # All cleanup runs while the original owned files remain
                    # open. Each action is attempted even after an earlier one.
                    try:
                        if control is not None:
                            control._stop_history()
                    except BaseException as error:
                        problem('stop_control', error)
                    try:
                        proxy.close_admission()
                    except BaseException as error:
                        problem('close_admission', error)
                    if published:
                        self._terminal_life['stop_create_attempted'] = True
                        try:
                            durable.durable_new(target / 'stream-owner-stop.json', owner._json(
                                {'format': 'native_stream_owner_stop_v1', 'owner_sha256': c.sha(self._owner_bytes)}))
                            stopped = True
                            self._terminal_life['stop_create_completed'] = True
                        except BaseException as error:
                            problem('stop_marker', error)
                    try:
                        frozen.terminate_group(process)
                    except BaseException as error:
                        problem('terminate_group', error)
                    if control is not None:
                        try:
                            control.close_after_process_termination()
                        except BaseException as error:
                            problem('owner_close', error)
                        try:
                            self._failed = control.failed_members()
                            self._terminal_life['failed_members_copy_state'] = 'captured'
                            self._terminal_life['stop_cut_state'] = 'captured' if control._stop_snapshot_taken else 'unavailable'
                            if control._failure_json is not None:
                                self._failed['failure_summary'] = control._failure_json
                            self._terminal_life['failure_summary_copy_state'] = 'present' if control._failure_json is not None else 'absent'
                            self._terminal_close = control._close_json
                            self._terminal_life['close_report_copy_state'] = 'present' if self._terminal_close is not None else 'absent'
                            proxy.control_shutdown = {'control_initialized': True,
                                'control_shutdown_complete': control.control_shutdown_complete,
                                'unfinished_control_workers': control.unfinished_control_workers}
                        except BaseException as error:
                            problem('control_evidence', error)
            # Owned descriptors have now closed through non-masking cleanup
            # callbacks, so their failures belong in the immutable report.
            try:
                report = {'format': 'native_owner_runner_report_v1',
                        'state': 'failed' if primary is not None or cleanup else 'completed',
                        'dispatches': dispatches, 'owner_published': published,
                        'stop_marker_published': stopped, 'returncode': getattr(process, 'returncode', None),
                        'primary_error': _error(primary) if primary is not None else None,
                        'cleanup_errors': [{'stage': stage, 'error': _error(error)} for stage, error in cleanup],
                        'control_close': control.close_report() if control is not None else None,
                        'execution_authorized': False, 'native_acceptance': 'not_assessed'}
                self._report_bytes = owner._json(report)
            except BaseException as error:
                problem('report', error)
                self._report_bytes = json.dumps({'format': 'native_owner_runner_report_refused_v1',
                            'state': 'failed', 'dispatches': dispatches, 'owner_published': published,
                            'stop_marker_published': stopped, 'error': type(error).__name__,
                            'execution_authorized': False, 'native_acceptance': 'not_assessed'}).encode()
            self._freeze_terminal()
            if primary is not None:
                raise primary
            if cleanup:
                raise cleanup[0][1]
            return result

    return BoundRunner()
