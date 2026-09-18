"""Lossless framing and adversarial native delivery without providers or state."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import native_context as context


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path.resolve()
    source = root / 'sources';source.mkdir()
    documents = {}
    texts = {'bundle': 'Evidence α😀\\\t\r\n' * 4500,
             'instruction': 'Full current instruction\n' * 200,
             'empty': '', 'original_full': '\ufeffname: source\r\nnotes: "A\\B"\n'}
    for role, text in texts.items():
        path = source / (role + '.txt');path.write_bytes(text.encode('utf-8'));documents[role] = path
    condition = root / 'condition';condition.mkdir()
    before = {str(path): path.read_bytes() for path in documents.values()}
    block = context.prepare_context(condition / 'recovery', documents)
    pins = {str(path): sha(path) for path in [*documents.values(), *map(Path, context.bounded_paths(block))]}
    return block, documents, pins, before


def decode(path):
    return ''.join(json.loads(line)['text'] for line in Path(path).read_text().splitlines())


def native_read(block, descriptor, offset=1):
    limit = min(12, descriptor['line_count'] - offset + 1)
    lines = Path(descriptor['path']).read_text().split('\n')[offset - 1:offset - 1 + limit]
    event = {'tool_use_result': {'type': 'text', 'file': {'filePath': descriptor['path'],
        'startLine': offset, 'numLines': limit, 'totalLines': descriptor['line_count'],
        'content': '\n'.join(lines)}}}
    result = {'type': 'tool_result', 'tool_use_id': 'call-1',
        'content': '\n'.join(str(i) + '\t' + line for i, line in enumerate(lines, offset))}
    return event, result, limit


def test_lossless_complete_sources_bounded_index_and_read_ranges(prepared):
    block, documents, pins, before = prepared
    assert context.validate_context(block, documents, pins) == block
    recovered_index = json.loads(decode(block['index']['path']))
    assert recovered_index == {'kind': context.INDEX_KIND, 'documents': block['documents']}
    for descriptor in [block['index'], *[item['frames'] for item in block['documents'].values()]]:
        raw = Path(descriptor['path']).read_bytes()
        assert not raw.endswith(b'\n') and all(len(line) <= 1000 for line in raw.split(b'\n'))
        assert descriptor['line_count'] == len(raw.split(b'\n'))
        for offset in range(1, descriptor['line_count'] + 1, 12):
            event, result, limit = native_read(block, descriptor, offset)
            check = context.validate_read(block, descriptor['path'], offset, limit, event, result)
            assert check['offset'] == offset and check['limit'] == limit
    for role, path in documents.items():
        assert decode(block['documents'][role]['frames']['path']).encode('utf-8') == before[str(path)]
    assert before == {str(path): path.read_bytes() for path in documents.values()}
    text = context.render_recovery(block)
    assert block['index']['sha256'] in text and 'offset=1+12*k' in text
    assert 'does not assert that any document has been read again' in text
    with pytest.raises(ValueError, match='already exists'):
        context.prepare_context(Path(block['index']['path']).parent, documents)


def test_nonempty_frame_encoding_matches_existing_phase4():
    from finalization_controls.contract import context_lines
    for text in ('x', 'x' * 10000, '😀\r\n\\\t"' * 4000):
        assert context._frames(text) == context_lines(text)


def test_coherently_repinned_frame_and_index_cannot_replace_original_text(prepared):
    block, documents, pins, _ = prepared
    forged = deepcopy(block)
    frame = Path(forged['documents']['bundle']['frames']['path'])
    text = 'plausible but incomplete replacement source'
    raw = context._encoded(text);frame.write_bytes(raw)
    forged['documents']['bundle']['frames'] = context._metadata(frame, raw, text)
    index = Path(forged['index']['path'])
    text = context._json({'kind': context.INDEX_KIND, 'documents': forged['documents']})
    raw = context._encoded(text);index.write_bytes(raw)
    forged['index'] = context._metadata(index, raw, text)
    pins.update({str(frame): sha(frame), str(index): sha(index)})
    with pytest.raises(ValueError, match='exact registered documents'):
        context.validate_context(forged, documents, pins)


def test_large_index_is_itself_recovered_through_bounded_reads(tmp_path):
    root = tmp_path.resolve();source = root / 'complete_source'
    source.write_bytes(('😀' * 110000 + '\r\n').encode())
    condition = root / 'condition';condition.mkdir()
    documents = {f'role_{number:03d}': source for number in range(40)}
    block = context.prepare_context(condition / 'recovery', documents)
    assert block['index']['line_count'] > 12
    for offset in range(1, block['index']['line_count'] + 1, 12):
        event, result, limit = native_read(block, block['index'], offset)
        context.validate_read(block, block['index']['path'], offset, limit, event, result)
    # Repeated roles can faithfully reference the same original; no truncated
    # bootstrap or scientific substitution is introduced by the index itself.
    recovered = json.loads(decode(block['index']['path']))['documents']
    assert set(recovered) == set(documents)
    assert decode(recovered['role_039']['frames']['path']).encode() == source.read_bytes()


@pytest.mark.parametrize('damage', ['source', 'frame', 'index', 'missing_pin', 'wrong_pin',
    'role', 'source_path', 'frame_path', 'count_boolean', 'bytes_boolean', 'text_hash', 'extra_key', 'hardlink'])
def test_validation_rejects_changed_or_misrepresented_context(prepared, tmp_path, damage):
    block, documents, pins, _ = prepared
    entry = block['documents']['bundle'];frame = Path(entry['frames']['path'])
    if damage == 'source': documents['bundle'].write_text('different')
    elif damage == 'frame': frame.write_bytes(frame.read_bytes() + b'\n')
    elif damage == 'index': Path(block['index']['path']).write_text('{}')
    elif damage == 'missing_pin': pins.pop(str(frame))
    elif damage == 'wrong_pin': pins[str(frame)] = '0' * 64
    elif damage == 'role': block['documents']['../escape'] = block['documents'].pop('bundle')
    elif damage == 'source_path': entry['source']['path'] = str(documents['instruction'])
    elif damage == 'frame_path': entry['frames']['path'] = str(frame.parent / 'other.jsonl')
    elif damage == 'count_boolean': entry['frames']['line_count'] = True
    elif damage == 'bytes_boolean': entry['frames']['bytes'] = True
    elif damage == 'text_hash': entry['frames']['text_sha256'] = '0' * 64
    elif damage == 'extra_key': block['unexpected'] = True
    else: os.link(frame, tmp_path / 'alias')
    with pytest.raises(ValueError): context.validate_context(block, documents, pins)


@pytest.mark.parametrize('damage', ['error', 'untyped', 'missing_metadata', 'persisted', 'truncated',
    'wrong_number', 'wrong_raw', 'boolean_line', 'wrong_total', 'other_path', 'unbounded',
    'string_offset', 'boolean_offset', 'shifted', 'short_range', 'null_event', 'null_result', 'mutated_frame'])
def test_read_rejects_false_or_truncated_delivery(prepared, damage):
    block, _, _, _ = prepared;descriptor = block['documents']['bundle']['frames']
    event, result, limit = native_read(block, descriptor)
    path, offset = descriptor['path'], 1
    if damage == 'error': result['is_error'] = True
    elif damage == 'untyped': result['type'] = 'text'
    elif damage == 'missing_metadata': event.pop('tool_use_result')
    elif damage == 'persisted': result['content'] = 'Output written to /tmp/persisted.txt'
    elif damage == 'truncated': result['content'] = result['content'][:200]
    elif damage == 'wrong_number': result['content'] = '2\t' + result['content'][2:]
    elif damage == 'wrong_raw': event['tool_use_result']['file']['content'] = 'omitted content'
    elif damage == 'boolean_line': event['tool_use_result']['file']['startLine'] = True
    elif damage == 'wrong_total': event['tool_use_result']['file']['totalLines'] += 1
    elif damage == 'other_path': path = block['index']['path']
    elif damage == 'unbounded': limit = 13
    elif damage == 'string_offset': offset = '1'
    elif damage == 'boolean_offset': offset = True
    elif damage == 'shifted': offset = 2
    elif damage == 'short_range': limit = 11
    elif damage == 'null_event': event = None
    elif damage == 'null_result': result = None
    else: Path(path).write_bytes(Path(path).read_bytes() + b' ')
    with pytest.raises(ValueError): context.validate_read(block, path, offset, limit, event, result)


@pytest.mark.parametrize('damage', ['unsafe_role', 'reserved_role', 'symlink_source', 'invalid_utf8',
    'overlap', 'noncanonical_destination', 'wrong_directory', 'missing_parent'])
def test_preparation_refuses_bad_inputs_before_creating_recovery(tmp_path, damage):
    root = tmp_path.resolve();source = root / 'source';source.write_bytes(b'complete\r\nsource')
    condition = root / 'condition';condition.mkdir();destination = condition / 'recovery'
    documents = {'source': source}
    if damage == 'unsafe_role': documents = {'../source': source}
    elif damage == 'reserved_role': documents = {'index': source}
    elif damage == 'symlink_source':
        alias = root / 'alias';alias.symlink_to(source);documents = {'source': alias}
    elif damage == 'invalid_utf8': source.write_bytes(b'\xff')
    elif damage == 'overlap': destination = source / 'recovery'
    elif damage == 'noncanonical_destination': destination = str(condition) + '/./recovery'
    elif damage == 'wrong_directory': destination = condition / 'other'
    else: destination = condition / 'absent' / 'recovery'
    with pytest.raises((ValueError, UnicodeDecodeError)):
        context.prepare_context(destination, documents)
    assert not (condition / 'recovery').exists()
