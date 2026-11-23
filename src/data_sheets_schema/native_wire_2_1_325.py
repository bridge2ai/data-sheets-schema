"""Pure production wire predicates for the reviewed executable, PR6302.

2026-11-21. These predicates interpret captured frames, confer no authority and
do not import the scripted permission probe. Callers own ordering, session joins,
helper semantics, effect verification and the unchanged raw evidence.
"""
import ast
import posixpath
import re
from uuid import UUID

from . import native_shared_contract as c


VERSION = '2.1.325 (Claude Code)'
INIT_VERSION = '2.1.325'
EXECUTABLE_SHA256 = '84590fefe6338be9087f5814b61f9a54c5f21524163a4c127cb5a808e31009f2'
STATUS_BASIS = 'is_error_false_2_1_325'
FAILURE_STATUS_BASIS = 'is_error_true_exit_code_2_1_325'
WRITE_SUCCESS_SUFFIX = ' (file state is current in your context \u2014 no need to Read it back)'
_DERIVATION_RULE = (
    'shared slots copied from the full record; resources projected by id '
    'with full-only nested slots dropped; distributions built from '
    'file_collections (one per collection over the shared slots, '
    'total_bytes as bytes) and from each collection\'s File entries (one '
    'per file over the slots CoreDistribution and File share); dialect '
    'from the File entries when they agree on one value, else absent')


def _option(argv, flag):
    positions = [index for index, value in enumerate(argv) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        raise ValueError('helper lacks its unique selected ' + flag)
    return argv[positions[0] + 1]


def _scope_warnings(lines, paths):
    """Parse scope_cmd's counted, possibly truncated resource warnings."""
    header = re.fullmatch(r'⚠️  ([12]) record\(s\), ([1-9][0-9]*) value\(s\) place a '
        r'related-but-distinct dataset outside its declared slot:', lines[1] if len(lines) > 1 else '')
    if not header or lines[0] != '':
        return False
    seen, values, index = set(), 0, 2
    while index < len(lines):
        selected = next((path for path in (paths['full'], paths['core'])
                         if lines[index] == '   ' + path), None)
        if selected is None or selected in seen:
            return False
        seen.add(selected)
        index += 1
        displayed = 0
        while index < len(lines) and re.fullmatch(r'      .+ = .+', lines[index]):
            displayed += 1
            index += 1
        if not 1 <= displayed <= 4:
            return False
        values += displayed
        more = re.fullmatch(r'      … ([1-9][0-9]*) more', lines[index]) if index < len(lines) else None
        if more:
            if displayed != 4:
                return False
            values += int(more.group(1))
            index += 1
    return len(seen) == int(header.group(1)) and values == int(header.group(2))


def helper_stdout(kind, stdout, commands, paths):
    """Check textual helpers against their emitting CLI, without running it.

    JSON phase helpers have their stronger existing protocol checks in
    PhaseState. These lexical checks do not replace independently checked
    artifacts, schema validity, source scope or recorder lineage.
    """
    if type(stdout) is not str or kind not in commands:
        raise ValueError('missing-numeric Bash has no selected helper output')
    argv, lines = commands[kind], stdout.splitlines()
    valid = False
    if kind == 'chunk_check':
        manifest = _option(argv, '--chunk-manifest')
        valid = re.fullmatch(r'   ✓ current ' + re.escape(manifest)
            + r': [1-9][0-9]* canonical chunks under the selected rule\n?', stdout) is not None
    elif kind in ('full_schema', 'core_schema'):
        valid = lines == ['No issues found']
    elif kind == 'full_terms':
        valid = lines == ['✅ Validation passed']
    elif kind in ('source_scope', 'final_scope'):
        project = _option(argv, '--project')
        valid = (len(lines) >= 2 and lines[0] == project
            and re.fullmatch(r'   about     .+  <.+>', lines[1]) is not None)
        declarations = lines[2:]
        if kind == 'final_scope':
            marker = '2 record(s) checked against the declaration'
            valid = valid and lines.count(marker) == 1
            if marker in lines:
                boundary = lines.index(marker)
                declarations = lines[2:boundary]
                tail = lines[boundary + 1:]
                valid = valid and bool(tail) and tail[0] == (
                    '   ✓ none is about a dataset its project declares distinct')
                # cli.download.scope_cmd reports resource warnings without
                # failing scope; unreadable/out-of-scope records still refuse.
                remaining = tail[1:]
                note = ("   (checked on the record's `id`; prose that discusses "
                        'a related dataset is legitimate and not inspected)')
                if remaining and remaining[-1] == note:
                    remaining = remaining[:-1]
                if remaining:
                    valid = valid and _scope_warnings(remaining, paths)
        valid = valid and all(not line or line.startswith((
            '   not about ', '             express as `')) for line in declarations)
    elif kind in ('derive_core', 'derive_final_core'):
        if (len(lines) == 3 and lines[0] == '✓ ' + paths['core']
                and lines[2] == '  linkml-validate: No issues found'):
            value = c.strict_json(lines[1].encode(), 'core derivation facts', c.HARD_LIMITS['request_bytes'])
            valid = (type(value) is dict and set(value) == {
                'derived', 'rule', 'from', 'identity_slots', 'projected_slots', 'distribution_slots', 'conditional'}
                and value['derived'] is True and value['rule'] == _DERIVATION_RULE
                and type(value['from']) is dict and set(value['from']) == {'path', 'md5'}
                and value['from']['path'] == paths['full']
                and type(value['from']['md5']) is str
                and re.fullmatch('[0-9a-f]{32}', value['from']['md5']) is not None
                and type(value['identity_slots']) is int and value['identity_slots'] > 0
                and type(value['projected_slots']) is list
                and all(type(item) is str for item in value['projected_slots'])
                and type(value['distribution_slots']) is dict
                and set(value['distribution_slots']) == {'collection', 'file'}
                and all(type(items) is list and all(type(item) is str for item in items)
                        for items in value['distribution_slots'].values())
                and value['conditional'] == {'dialect':
                    'derived only when every File-level dialect in the full record agrees on one value'})
    elif kind == 'pair':
        match = re.fullmatch(r'PASS: ([1-9][0-9]*) schema-identical slots; projected slots=(\[.*\]); '
            r'per-record slots \(exempt, must differ\)=(\[.*\])', lines[0] if lines else '')
        if match and len(lines) >= 3:
            try:
                slots = [ast.literal_eval(match.group(index)) for index in (2, 3)]
            except (ValueError, SyntaxError):
                slots = [None]
            valid = (all(type(value) is list and all(type(item) is str for item in value) for value in slots)
                and all(line.startswith('WARNING [') for line in lines[1:-2])
                and re.fullmatch(r'Presence context: (unavailable|no_recorded_digest|captured); '
                    r'recorded digest=[^;\n]+; schema_moved=(True|False); ledger inventory=(known|unknown)',
                    lines[-2]) is not None
                and lines[-1].startswith('Historical core inventory: '))
            if valid:
                inventory = c.strict_json(lines[-1][len('Historical core inventory: '):].encode(),
                    'pair historical inventory', c.HARD_LIMITS['request_bytes'])
                valid = (type(inventory) is dict
                    and inventory.get('status') in ('not_needed', 'unknown', 'recovered'))
    elif kind == 'recorder':
        project = _option(argv, '--project')
        destination = posixpath.join(posixpath.dirname(paths['core']), project + '_provenance.yaml')
        valid = bool(lines) and lines[0] == '✓ ' + destination
    if not valid:
        raise ValueError('missing-numeric Bash stdout is not the selected ' + str(kind) + ' helper output')


def profile(runtime):
    """Select only the complete reviewed executable identity, never a profile name."""
    executable = runtime.get('executable') if type(runtime) is dict else None
    return type(executable) is dict and (
        executable.get('version'), executable.get('init_version'), executable.get('sha256')) == (
            VERSION, INIT_VERSION, EXECUTABLE_SHA256)


def write_success_text(text, path, runtime):
    """Match presentation only; callers bind the admitted path, bytes and create."""
    if type(text) is not str or type(path) is not str:
        return False
    bare = 'File created successfully at: ' + path
    return text == bare or (profile(runtime) and text == bare + WRITE_SUCCESS_SUFFIX)


def _uuid(value):
    if type(value) is not str:
        raise ValueError('2.1.325 frame lacks a canonical UUID')
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise ValueError('2.1.325 frame lacks a canonical UUID') from error
    if str(parsed) != value:
        raise ValueError('2.1.325 frame lacks a canonical UUID')
    return value


def ui_prefix_session(event, runtime):
    """Validate the one possible startup frame; caller enforces its physical order."""
    if (not profile(runtime) or type(event) is not dict
            or set(event) != {'type', 'subtype', 'event', 'uuid', 'session_id'}
            or event['type'] != 'system' or event['subtype'] != 'ui_invalidate'
            or event['event'] != 'ui.render'):
        raise ValueError('unreviewed or malformed 2.1.325 UI prefix')
    _uuid(event['uuid'])
    return _uuid(event['session_id'])


def permission_denial(event, runtime):
    """Recognize an explicit failure frame without giving any tool success credit."""
    if (not profile(runtime) or type(event) is not dict or event.get('type') != 'system'
            or event.get('subtype') != 'permission_denied'):
        return False
    if (set(event) != {'type', 'subtype', 'tool_name', 'tool_use_id', 'decision_reason_type',
                      'decision_reason', 'message', 'uuid', 'session_id'}
            or event['tool_name'] not in ('Read', 'Write', 'Bash')
            or any(type(event[key]) is not str or not event[key] for key in (
                'tool_use_id', 'decision_reason_type', 'decision_reason', 'message'))):
        raise ValueError('malformed 2.1.325 permission denial')
    _uuid(event['uuid'])
    _uuid(event['session_id'])
    return True


def missing_numeric_bash_success(event, block, runtime):
    """Recognize a status basis, subject to the reader's expected helper output.

    False means the historical numeric contract still applies. A reviewed result
    without numeric aliases must satisfy every observed flag; absence is never
    an invented zero. Callers retain null plus STATUS_BASIS in their evidence.
    """
    metadata = event.get('tool_use_result')
    if (not profile(runtime) or type(metadata) is not dict
            or any(key in metadata for key in ('exitCode', 'exit_code'))):
        return False
    if (block.get('is_error') is not False
            or any(metadata.get(key) is not False for key in (
                'interrupted', 'isImage', 'noOutputExpected'))
            or any(type(metadata.get(key)) is not str for key in ('stdout', 'stderr'))
            or type(block.get('content')) is not str
            or metadata.get('error') is not None
            or any(metadata.get(key) is not None for key in (
                'backgroundTaskId', 'background_task_id', 'persistedOutputPath'))):
        raise ValueError('2.1.325 Bash result is contradictory, interrupted, pending or untyped')
    return True


def missing_numeric_bash_failure(event, block, runtime):
    """Read an observed nonzero status without inventing stdout or stderr.

    Other identities, numeric metadata and refusal text keep their existing
    readers. A matching failure carries merged output only, never JSON success.
    The caller must join a prescribed Bash admission and exclude a denial frame.
    """
    if (not profile(runtime) or type(event) is not dict or type(block) is not dict
            or type(event.get('tool_use_result')) is not str):
        return None
    content = block.get('content')
    if type(content) is not str or not content.startswith('Exit code '):
        return None
    message = event.get('message')
    expected_keys = {'type', 'message', 'parent_tool_use_id', 'session_id', 'uuid',
                     'timestamp', 'tool_use_result', 'tool_result_meta'}
    if (set(event) != expected_keys or event['type'] != 'user'
            or event['parent_tool_use_id'] is not None
            or type(message) is not dict or set(message) != {'role', 'content'}
            or message['role'] != 'user' or message['content'] != [block]
            or set(block) != {'type', 'tool_use_id', 'is_error', 'content'}
            or block['type'] != 'tool_result' or block['is_error'] is not True
            or type(block['tool_use_id']) is not str or not block['tool_use_id']):
        raise ValueError('native Bash failure lacks its exact failed tool result')
    _uuid(event['uuid'])
    _uuid(event['session_id'])
    from datetime import datetime, timedelta
    timestamp = event['timestamp']
    if type(timestamp) is not str or not timestamp.endswith('Z'):
        raise ValueError('native Bash failure timestamp is not UTC')
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + '+00:00')
    except ValueError as error:
        raise ValueError('native Bash failure timestamp is invalid') from error
    if parsed.utcoffset() != timedelta(0):
        raise ValueError('native Bash failure timestamp is not UTC')
    status = re.match(r'Exit code ([1-9][0-9]*)\n', content)
    annotation = [{'id': block['tool_use_id'], 'permission_decision': {
        'decision': 'accept', 'source': 'config', 'reason_type': 'rule'}}]
    if (status is None or event['tool_use_result'] != 'Error: ' + content
            or event['tool_result_meta'] != annotation):
        raise ValueError('native Bash failure status, wrapper or permission metadata differs')
    return int(status.group(1)), content[status.end():]


def denied_tool_result(event, block, runtime, *, tool_name, tool_use_id,
                       basis=None, permission_denied=None):
    """Validate a bound native refusal; callers retain its failed classification.

    Hook refusals require the independently reconstructed callback basis. Config
    refusals require the preceding checked system frame for that same tool.
    Neither a free-form error string nor this predicate grants any tool credit.
    """
    if not profile(runtime) or type(event.get('tool_use_result')) is not str:
        return False
    message = event.get('message')
    if (event.get('type') != 'user' or event.get('parent_tool_use_id') is not None
            or type(message) is not dict or set(message) != {'role', 'content'}
            or message['role'] != 'user' or message['content'] != [block]
            or set(block) != {'type', 'tool_use_id', 'is_error', 'content'}
            or block['type'] != 'tool_result' or block['tool_use_id'] != tool_use_id
            or block['is_error'] is not True or type(block['content']) is not str):
        raise ValueError('native refusal lacks its exact failed tool result')
    allowed = {'type', 'message', 'session_id', 'uuid', 'parent_tool_use_id', 'timestamp',
               'tool_use_result', 'tool_result_meta'}
    if not set(event) <= allowed:
        raise ValueError('native refusal has an unsupported result envelope')
    if 'timestamp' in event:
        from datetime import datetime, timedelta
        timestamp = event['timestamp']
        if type(timestamp) is not str or not timestamp.endswith('Z'):
            raise ValueError('native refusal timestamp is not UTC')
        try:
            parsed = datetime.fromisoformat(timestamp[:-1] + '+00:00')
        except ValueError as error:
            raise ValueError('native refusal timestamp is invalid') from error
        if parsed.utcoffset() != timedelta(0):
            raise ValueError('native refusal timestamp is not UTC')
    if permission_denied is not None:
        if (not permission_denial(permission_denied, runtime)
                or permission_denied['tool_use_id'] != tool_use_id
                or permission_denied['tool_name'] != tool_name
                or permission_denied['session_id'] != event.get('session_id')):
            raise ValueError('native refusal differs from its permission denial')
        content = permission_denied['message']
        source, reason = 'config', permission_denied['decision_reason_type']
    else:
        if type(basis) is not str or not basis:
            raise ValueError('native hook refusal lacks its classified callback basis')
        content = 'PreToolUse:' + tool_name + ' hook error: Outside the registered tool policy: ' + basis
        source, reason = 'hook', 'hook'
    expected = [{'id': tool_use_id, 'non_execution_kind': 'permission-rule',
                 'permission_decision': {'decision': 'reject', 'source': source,
                                         'reason_type': reason}}]
    if (block['content'] != content or event['tool_use_result'] != 'Error: ' + content
            or event.get('tool_result_meta') != expected):
        raise ValueError('native refusal wrapper or permission metadata differs')
    return True
