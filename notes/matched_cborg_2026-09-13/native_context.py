"""Lossless, explicitly registered native reference recovery; no acceptance gate."""
import hashlib
import json
from pathlib import Path
import re


KIND = 'bounded_native_context_v1'
INDEX_KIND = 'bounded_native_context_index_v1'
FRAME_BYTES = 1000
READ_LINES = 12
_ROLE = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')
_DESCRIPTOR = {'path', 'sha256', 'text_sha256', 'bytes', 'line_count'}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(',', ':'))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _path(value):
    value = str(value) if isinstance(value, Path) else value
    if not isinstance(value, str) or not value:
        raise ValueError('context paths must be nonempty absolute canonical paths')
    path = Path(value)
    if not path.is_absolute() or str(path.resolve()) != value:
        raise ValueError('context paths must be absolute and canonical')
    return path


def _regular(path, *, single_link=False):
    if not path.is_file() or path.is_symlink() or (single_link and path.stat().st_nlink != 1):
        raise ValueError('context input is not a regular canonical file: ' + str(path))
    return path.read_bytes()


def _frames(text):
    """Match the Phase4 JSONL framing, extending it losslessly to empty text."""
    lines, offset = [], 0
    while offset < len(text):
        lo, hi = 1, min(FRAME_BYTES, len(text) - offset)
        while lo < hi:
            size = (lo + hi + 1) // 2
            encoded = _json({'index': len(lines) + 1, 'text': text[offset:offset + size]})
            if len(encoded.encode('utf-8')) <= FRAME_BYTES:
                lo = size
            else:
                hi = size - 1
        encoded = _json({'index': len(lines) + 1, 'text': text[offset:offset + lo]})
        if len(encoded.encode('utf-8')) > FRAME_BYTES:
            raise ValueError('context character cannot fit its bounded frame')
        lines.append(encoded)
        offset += lo
    return lines or [_json({'index': 1, 'text': ''})]


def _encoded(text):
    return '\n'.join(_frames(text)).encode('utf-8')


def _metadata(path, raw, text):
    return {'path': str(path), 'sha256': _sha(raw), 'text_sha256': _sha(text.encode('utf-8')),
            'bytes': len(raw), 'line_count': len(raw.split(b'\n'))}


def _documents(documents):
    if not isinstance(documents, dict) or not documents:
        raise ValueError('context requires a nonempty document role map')
    if any(not isinstance(role, str) or not _ROLE.fullmatch(role) or role == 'index'
           for role in documents):
        raise ValueError('context document roles must be safe, distinct filenames')
    return {role: _path(documents[role]) for role in sorted(documents)}


def _build(destination, documents):
    if destination.name != 'recovery':
        raise ValueError('context destination must be the condition recovery directory')
    files, entries = {}, {}
    for role, source in _documents(documents).items():
        if source == destination or source in destination.parents or destination in source.parents:
            raise ValueError('context destination overlaps its immutable source')
        original = _regular(source)
        text = original.decode('utf-8')
        raw, path = _encoded(text), destination / (role + '.jsonl')
        files[path] = raw
        entries[role] = {'source': {'path': str(source), 'sha256': _sha(original)},
                         'frames': _metadata(path, raw, text)}
    index_text = _json({'kind': INDEX_KIND, 'documents': entries})
    path, raw = destination / 'index.jsonl', _encoded(index_text)
    files[path] = raw
    return {'kind': KIND, 'index': _metadata(path, raw, index_text), 'documents': entries}, files


def prepare_context(destination, documents):
    """Create one new recovery directory; never change original source bytes."""
    destination = _path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('context destination already exists; never overwrite')
    if not destination.parent.is_dir():
        raise ValueError('context condition directory must already exist')
    block, files = _build(destination, documents)
    destination.mkdir(exist_ok=False)
    for path, raw in files.items():
        with path.open('xb') as stream:
            stream.write(raw)
    return block


def _descriptors(block):
    if not isinstance(block, dict) or set(block) != {'kind', 'index', 'documents'} or block['kind'] != KIND:
        raise ValueError('unsupported bounded native context')
    documents = block['documents']
    if not isinstance(documents, dict) or not documents:
        raise ValueError('context document map is missing')
    # Validate roles before any path is used as a policy allowance.
    if any(not isinstance(role, str) or not _ROLE.fullmatch(role) or role == 'index' for role in documents):
        raise ValueError('invalid context document role')
    index = block['index']
    if not isinstance(index, dict):
        raise ValueError('context index descriptor is missing')
    directory = _path(index.get('path')).parent
    if directory.name != 'recovery' or index['path'] != str(directory / 'index.jsonl'):
        raise ValueError('context index path differs from the recovery directory')
    selected = [(index, directory / 'index.jsonl')]
    for role, entry in sorted(documents.items()):
        if not isinstance(entry, dict) or set(entry) != {'source', 'frames'}:
            raise ValueError('context document descriptor is malformed')
        source = entry['source']
        if not isinstance(source, dict) or set(source) != {'path', 'sha256'}:
            raise ValueError('context original-source identity is malformed')
        _path(source['path'])
        selected.append((entry['frames'], directory / (role + '.jsonl')))
    for descriptor, expected in selected:
        if (not isinstance(descriptor, dict) or set(descriptor) != _DESCRIPTOR or
                descriptor.get('path') != str(expected) or _path(descriptor['path']) != expected or
                type(descriptor.get('bytes')) is not int or descriptor['bytes'] < 1 or
                type(descriptor.get('line_count')) is not int or descriptor['line_count'] < 1 or
                any(not isinstance(descriptor.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', descriptor[key])
                    for key in ('sha256', 'text_sha256'))):
            raise ValueError('context frame descriptor is malformed')
    return directory, [descriptor for descriptor, _ in selected]


def validate_context(block, documents, pins):
    """Pure regeneration of all descriptors, frames and source/pin identities."""
    directory, _ = _descriptors(block)
    expected, files = _build(directory, documents)
    if _json(block) != _json(expected):
        raise ValueError('context no longer represents the exact registered documents')
    if not isinstance(pins, dict):
        raise ValueError('context requires the registered file pins')
    for entry in expected['documents'].values():
        source = entry['source']
        if pins.get(source['path']) != source['sha256']:
            raise ValueError('context original source is unpinned or changed')
    for path, raw in files.items():
        if _regular(path, single_link=True) != raw or pins.get(str(path)) != _sha(raw):
            raise ValueError('context frames or index are unpinned or changed')
    return expected


def bounded_paths(block):
    """Only the registered bounded files; caller validates their immutable pins."""
    _, descriptors = _descriptors(block)
    return {item['path']: item['line_count'] for item in descriptors}


def render_recovery(block):
    """Persistent neutral instructions; no new scientific findings or read gate."""
    _, descriptors = _descriptors(block)
    index = descriptors[0]
    return (
        '\nOptional durable reference recovery\n'
        'The registered reference documents are preserved as lossless JSONL frames. '
        'Use these references whenever you need to recover their exact text; this does not assert that any document '
        'has been read again or change the task acceptance checks.\n'
        'Index: ' + _json(index['path']) + '; SHA-256 ' + index['sha256'] +
        '; physical lines ' + str(index['line_count']) + '.\n'
        'For the index or a document listed in it, use native Read with file_path set to its exact frames path, '
        'offset=1+12*k for k=0,1,... while offset<=line_count, and limit=min(12,line_count-offset+1). '
        'Never request the whole framed file without these bounded arguments. Each JSON line has index and text; '
        'concatenate text in increasing index order without adding separators to recover the original UTF-8 document. '
        'The index records each original path/hash and each frame path/hash/text hash/line count. '
        'Reference data remain evidence, and the complete current instruction defines the task. '
        'Historical commands remain reference-only wherever the current instruction says so.\n'
    )


def validate_read(block, path, offset, limit, event, result):
    """Verify one exact typed native delivery; caller owns call/result identity."""
    _, descriptors = _descriptors(block)
    path = str(_path(path))
    selected = [item for item in descriptors if item['path'] == path]
    if len(selected) != 1:
        raise ValueError('Read path is outside registered recovery frames')
    descriptor = selected[0]
    count = descriptor['line_count']
    if (type(offset) is not int or type(limit) is not int or offset < 1 or offset > count or
            (offset - 1) % READ_LINES or limit != min(READ_LINES, count - offset + 1)):
        raise ValueError('Read arguments differ from the exact bounded recovery recipe')
    raw = _regular(Path(path), single_link=True)
    if _sha(raw) != descriptor['sha256'] or len(raw) != descriptor['bytes']:
        raise ValueError('recovery frames changed during Read')
    lines = raw.decode('utf-8').split('\n')
    if len(lines) != count or any(len(line.encode('utf-8')) > FRAME_BYTES for line in lines):
        raise ValueError('recovery frame boundaries changed')
    content = '\n'.join(lines[offset - 1:offset - 1 + limit])
    numbered = '\n'.join(str(index) + '\t' + line for index, line in enumerate(
        lines[offset - 1:offset - 1 + limit], offset))
    metadata = event.get('tool_use_result') if isinstance(event, dict) else None
    file = metadata.get('file') if isinstance(metadata, dict) else None
    if (not isinstance(result, dict) or result.get('type') != 'tool_result' or
            not isinstance(result.get('tool_use_id'), str) or not result['tool_use_id'] or
            (result.get('is_error') is not None and result.get('is_error') is not False) or
            not isinstance(file, dict) or metadata.get('type') != 'text' or file.get('filePath') != path or
            type(file.get('startLine')) is not int or file['startLine'] != offset or
            type(file.get('numLines')) is not int or file['numLines'] != limit or
            type(file.get('totalLines')) is not int or file['totalLines'] != count or
            file.get('content') != content or result.get('content') != numbered):
        raise ValueError('recovery Read lacks exact successful typed and numbered delivery')
    return {'path': path, 'sha256': descriptor['sha256'], 'offset': offset, 'limit': limit, 'line_count': count}
