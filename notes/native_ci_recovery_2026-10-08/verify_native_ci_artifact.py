"""Offline metadata verifier for #4675 artifacts; reads ZIP/tar, never extracts.

Inputs are explicit downloaded GitHub metadata, archive and source-pin files.
No repository modules, subprocesses, imports from the archive or network calls.
This checks saved declarations and content consistency, not authenticated runs.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile


CASES = {
    'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion': 'native26',
    'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses': 'native26-omissions',
}
MAX_CASE_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 10000
MAX_METADATA_BYTES = 32 * 1024 * 1024
MAX_ARTIFACT_BYTES = 2 * MAX_CASE_BYTES + 64 * 1024 * 1024
SOURCE_NAMES = {
    'utils/native_ci_evidence.py', 'utils/native_shared_acceptance.py',
    'tests/test_native_shared_execution.py', 'tests/test_native_shared_execution_variant.py',
    'tests/native_shared_fixture.py', 'tests/native_shared_omission_fixture.py',
    'tests/fixtures/native_shared_execution/fake_cli.py', '.github/workflows/main.yaml',
}
KNOWN = (
    'actual-result.json', 'authority/runtime.json', 'authority/runtime-execution.json',
    'authority/selection.json', 'authority/composition-execution.json',
    'native-attempt/registration.json', 'native-attempt/started.json',
    'native-attempt/transcript.jsonl', 'native-attempt/control.jsonl',
    'native-attempt/stderr.txt', 'fresh-attempt/stages/journal.json',
)
LIMITS = {'attempt_seconds': 900, 'helper_seconds': 180, 'base_fixture_seconds': 120,
          'basis': 'Selected test/peer source declarations, not measured operation durations.'}


def need(value, message):
    if not value:
        raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_pin(path):
    size, digest = 0, hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            need(size <= MAX_ARTIFACT_BYTES, 'downloaded archive bound exceeded')
            digest.update(chunk)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def strict_json(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            need(key not in value, 'duplicate JSON key: ' + key)
            value[key] = item
        return value
    def nonfinite(value):
        raise ValueError('non-finite JSON: ' + value)
    def finite_float(value):
        number = float(value)
        need(math.isfinite(number), 'non-finite JSON numeric exponent')
        return number
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=nonfinite, parse_float=finite_float)


def read_json_file(path):
    with path.open('rb') as handle:
        raw = handle.read(MAX_METADATA_BYTES + 1)
    need(len(raw) <= MAX_METADATA_BYTES, 'local metadata bound exceeded')
    return strict_json(raw)


def canonical_relative(value):
    need(isinstance(value, str) and value and '\\' not in value, 'invalid relative name')
    path = PurePosixPath(value)
    need(not path.is_absolute() and str(path) == value and '..' not in path.parts,
         'noncanonical or escaping name: ' + value)
    return value


def read_member(zipped, name):
    member = zipped.getinfo(name)
    need(member.file_size <= MAX_METADATA_BYTES, 'metadata bound exceeded: ' + name)
    with zipped.open(member) as handle:
        raw = handle.read(MAX_METADATA_BYTES + 1)
    need(len(raw) == member.file_size and len(raw) <= MAX_METADATA_BYTES, 'metadata size mismatch')
    return raw


def check_source(value, expected):
    need(isinstance(value, dict), 'missing source identity')
    need(value['head'] == expected['merge_sha'] and value['tree'] == expected['tree_sha'],
         'source Git identity mismatch')
    need(set(value['files']) == SOURCE_NAMES, 'source roster mismatch')
    need(value['files'] == expected['files'], 'source file hashes mismatch')
    return {'head': value['head'], 'tree': value['tree'], 'files_checked': len(value['files'])}


def check_inventory(value):
    if value is None:
        return
    need(isinstance(value, dict) and len(value) <= MAX_ENTRIES, 'invalid inventory mapping')
    total = 0
    for name, row in value.items():
        if name != '.':
            canonical_relative(name)
        need(isinstance(row, dict), 'invalid inventory row')
        kind = row.get('type')
        keys = {'directory': {'type', 'mode'}, 'symlink': {'type', 'mode', 'target'},
                'file': {'type', 'mode', 'bytes', 'sha256'}}
        need(kind in keys and set(row) == keys[kind], 'inventory row fields mismatch')
        need(type(row['mode']) is int and 0 <= row['mode'] <= 0o7777, 'inventory mode type/value')
        if kind == 'file':
            need(type(row['bytes']) is int and row['bytes'] >= 0, 'inventory byte count type/value')
            need(isinstance(row['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', row['sha256']), 'inventory SHA type/value')
            total += row['bytes']
        elif kind == 'symlink':
            need(isinstance(row['target'], str), 'inventory link target type')
    need(total <= MAX_CASE_BYTES, 'inventory byte bound exceeded')
    need(value.get('.', {}).get('type') == 'directory', 'inventory root missing')


class LimitedReader:
    """Bound decompression before tarfile interprets even extended headers."""
    def __init__(self, handle, limit):
        self.handle, self.limit, self.seen = handle, limit, 0

    def read(self, size=-1):
        amount = self.limit - self.seen + 1
        raw = self.handle.read(amount if size < 0 else min(size, amount))
        self.seen += len(raw)
        need(self.seen <= self.limit, 'expanded tar stream bound exceeded')
        return raw


def inspect_tar(zipped, name):
    info = zipped.getinfo(name)
    need(info.file_size <= MAX_CASE_BYTES + 16 * 1024 * 1024, 'compressed case bound exceeded')
    inventory, captured, total = {}, {}, 0
    digest = hashlib.sha256()
    # Hash the exact compressed tar member separately, with a finite read.
    with zipped.open(name) as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    with zipped.open(name) as handle, gzip.GzipFile(fileobj=handle) as inflated, tarfile.open(
            fileobj=LimitedReader(inflated, MAX_CASE_BYTES + MAX_METADATA_BYTES), mode='r|') as archive:
        for member in archive:
            need(len(inventory) < MAX_ENTRIES, 'tar entry bound exceeded')
            raw_name = member.name
            if member.isdir() and raw_name.endswith('/'):
                raw_name = raw_name[:-1]
            canonical_relative(raw_name)
            need(raw_name == 'case' or raw_name.startswith('case/'), 'member outside selected case')
            relative = '.' if raw_name == 'case' else raw_name[5:]
            need(relative not in inventory, 'duplicate tar member: ' + relative)
            need(member.sparse is None, 'sparse member not emitted by retention writer')
            need(type(member.mode) is int and 0 <= member.mode <= 0o7777, 'invalid mode')
            row = {'mode': member.mode}
            if member.isdir():
                need(member.size == 0, 'directory with hidden payload')
                row['type'] = 'directory'
            elif member.issym():
                need(member.size == 0, 'link with hidden payload')
                row.update(type='symlink', target=member.linkname)
            elif member.isfile():
                need(member.size >= 0 and total + member.size <= MAX_CASE_BYTES, 'case byte bound exceeded')
                file_hash, size, pieces = hashlib.sha256(), 0, []
                selected = relative in {'actual-result.json', 'authority/runtime-execution.json',
                    'native-attempt/registration.json', 'native-attempt/started.json',
                    'native-attempt/transcript.jsonl', 'native-attempt/control.jsonl'}
                with archive.extractfile(member) as content:
                    while chunk := content.read(1024 * 1024):
                        size += len(chunk)
                        need(size <= member.size, 'member exceeds declared length')
                        file_hash.update(chunk)
                        if selected and member.size <= 64 * 1024 * 1024:
                            pieces.append(chunk)
                need(size == member.size, 'short tar member')
                total += size
                row.update(type='file', bytes=size, sha256=file_hash.hexdigest())
                if selected:
                    captured[relative] = b''.join(pieces) if pieces or size == 0 else None
            else:
                raise ValueError('unexpected member type (including hardlink): ' + relative)
            inventory[relative] = row
        while trailing := archive.fileobj.read(1024 * 1024):
            need(not trailing.strip(b'\x00'), 'non-padding content follows tar end marker')
    need(inventory.get('.', {}).get('type') == 'directory', 'explicit root directory missing (#4677)')
    for relative in inventory:
        if relative == '.':
            continue
        parent = str(PurePosixPath(relative).parent)
        need(inventory.get(parent, {}).get('type') == 'directory', 'missing or non-directory parent')
    return inventory, {'bytes': info.file_size, 'sha256': digest.hexdigest()}, captured


def result_diagnostics(captured, inventory, manifest):
    diagnostic = {'native_completion': 'not_inferred', 'result_available': False,
                  'transcript_available': captured.get('native-attempt/transcript.jsonl') is not None}
    raw = captured.get('actual-result.json')
    if raw is None:
        return diagnostic
    result = strict_json(raw)
    need(isinstance(result, dict), 'actual result is not a mapping')
    diagnostic.update(result_available=True, result_pin=pin(raw), state=result.get('state'),
                      runtime_gates_passed=result.get('runtime_gates_passed'), first_stop=result.get('first_stop'),
                      child_exit_code=result.get('child_exit_code'), shutdown=result.get('shutdown'))
    phase = result.get('gates', {}).get('live_attribution', {}).get('result', {}).get('phase_history')
    diagnostic['phase_history'] = phase
    pending = set(phase.get('pending_tool_ids', [])) if isinstance(phase, dict) else set()
    checked = []
    original = manifest['original_case'].rstrip('/') + '/'
    for identity, row in result.get('captured_files', {}).items():
        if not identity.startswith(original):
            checked.append({'identity': identity, 'status': 'outside_case_not_followed'})
            continue
        relative = identity[len(original):]
        canonical_relative(relative)
        actual = inventory.get(relative)
        matches = actual is not None and actual.get('type') == 'file' and all(actual.get(k) == row.get(k) for k in ('bytes', 'sha256'))
        checked.append({'relative': relative, 'matches_saved_capture': matches})
    diagnostic['saved_capture_bindings'] = checked
    transcript = captured.get('native-attempt/transcript.jsonl')
    if transcript is not None:
        observations, parse_errors, events = [], [], 0
        for index, line in enumerate(transcript.splitlines()):
            if not line.strip():
                continue
            try:
                event = strict_json(line)
                need(isinstance(event, dict), 'event is not a mapping')
                events += 1
                for content in event.get('message', {}).get('content', []) if isinstance(event.get('message'), dict) else []:
                    if isinstance(content, dict) and content.get('id') in pending:
                        observations.append({'line': index + 1, 'event_type': event.get('type'),
                                             'pending_tool': content})
            except Exception as exc:
                parse_errors.append({'line': index + 1, 'error': type(exc).__name__ + ': ' + str(exc)})
        diagnostic['transcript'] = {'events': events, 'ends_in_newline': transcript.endswith(b'\n'),
                                    'parse_errors': parse_errors, 'pending_tool_observations': observations}
    diagnostic['scope'] = 'Saved result and literal transcript inspection only; no replay, timing attribution or authenticated-execution claim.'
    return diagnostic


def verify(archive_path, metadata, expected):
    actual_pin = file_pin(archive_path)
    need(metadata['workflow_run']['id'] == expected['run_id'], 'wrong artifact run')
    need(metadata['workflow_run']['head_sha'] == expected['pr_head'], 'wrong artifact PR head')
    need(metadata['size_in_bytes'] == actual_pin['bytes'], 'downloaded artifact size mismatch')
    need(metadata['digest'] == 'sha256:' + actual_pin['sha256'], 'downloaded artifact digest mismatch')
    expected_prefix = 'native-synthetic-cases-' + expected['merge_sha'] + '-' + str(expected['run_id']) + '-'
    need(metadata['name'].startswith(expected_prefix), 'artifact name does not bind selected merge/run')
    result = {'artifact_id': metadata['id'], 'artifact_name': metadata['name'], 'archive': actual_pin,
              'run_id': expected['run_id'], 'pr_head': expected['pr_head'], 'cases': [], 'worker_outcomes': {},
              'verification_scope': 'Content consistency and declared GitHub/source bindings; not authenticated execution.'}
    with zipfile.ZipFile(archive_path) as zipped:
        files, total = {}, 0
        for info in zipped.infolist():
            name = info.filename[:-1] if info.is_dir() else info.filename
            canonical_relative(name)
            need(name not in files, 'duplicate ZIP member')
            need(len(files) < 128, 'unexpected ZIP entry count')
            total += info.file_size
            need(total <= MAX_ARTIFACT_BYTES, 'expanded ZIP bound exceeded')
            mode = info.external_attr >> 16
            need(mode & 0o170000 in (0, 0o040000, 0o100000), 'nonregular ZIP member')
            files[name] = info
            if info.is_dir():
                need(re.fullmatch(r'(?:controller|gw[0-9]+)(?:/[0-9a-f]{64})?', name), 'unexpected ZIP directory')
            else:
                need(name == 'selection.json' or re.fullmatch(r'(?:controller|gw[0-9]+)/(?:outcomes.json|[0-9a-f]{64}/(?:manifest.json|case.tar.gz))', name), 'unexpected ZIP file')
        selection = strict_json(read_member(zipped, 'selection.json'))
        need(selection['format'] == 'native_ci_selection_v1' and selection['cases'] == CASES, 'wrong closed node selection')
        result['source'] = check_source(selection['source'], expected)
        for name in sorted(files):
            if name.endswith('/outcomes.json'):
                result['worker_outcomes'][name.split('/')[0]] = strict_json(read_member(zipped, name))
        manifested = set()
        for name in sorted(files):
            if not name.endswith('/manifest.json'):
                continue
            worker, node_hash, _ = name.split('/')
            manifest = strict_json(read_member(zipped, name))
            node = manifest['node_id']
            need(node in CASES and hashlib.sha256(node.encode()).hexdigest() == node_hash, 'case node/path binding mismatch')
            need(manifest['worker'] == worker, 'case worker mismatch')
            check_source(manifest['source'], expected)
            need(manifest['format'] == 'native_ci_synthetic_case_v1', 'wrong case format')
            need(manifest['declared_limits'] == LIMITS, 'declared source limits changed')
            need(manifest['scientific_acceptance'] == 'not_assessed' and manifest['case_completeness'] == 'not_assessed', 'unexpected acceptance claim')
            status = manifest['status']
            need(status in {'retained', 'capture_changed', 'capture_failed', 'case_unavailable'}, 'unknown capture status')
            need(set(manifest['availability']) == set(KNOWN), 'availability roster mismatch')
            for key in ('before', 'archived', 'after'):
                check_inventory(manifest[key])
            need(type(manifest['unchanged']) is bool, 'unchanged flag must be an exact boolean')
            outcomes = manifest['test_outcome']
            need(isinstance(outcomes, dict) and set(outcomes) <= {'setup', 'call', 'teardown'}, 'test phase roster mismatch')
            for observation in outcomes.values():
                need(set(observation) == {'outcome', 'duration_seconds'} and observation['outcome'] in {'passed', 'failed', 'skipped'}, 'invalid test outcome')
                need(type(observation['duration_seconds']) in (int, float) and observation['duration_seconds'] >= 0, 'invalid phase duration')
            tar_name = name.removesuffix('manifest.json') + 'case.tar.gz'
            row = {'node_id': node, 'worker': worker, 'manifest_pin': pin(read_member(zipped, name)),
                   'capture_status': status, 'test_outcome': manifest['test_outcome'],
                   'case_completeness': manifest['case_completeness'], 'availability': manifest['availability']}
            if tar_name in files:
                manifested.add(tar_name)
                try:
                    inventory, tar_pin, captured = inspect_tar(zipped, tar_name)
                    row['actual_archive'] = tar_pin
                    row['actual_inventory'] = inventory
                    row['matches_archived_inventory'] = inventory == manifest['archived']
                    row['before_archived_after_equal'] = manifest['before'] == manifest['archived'] == manifest['after']
                    row['archive_pin_matches'] = manifest['archive'] == tar_pin
                    if status == 'retained':
                        need(row['matches_archived_inventory'] and row['before_archived_after_equal'] and row['archive_pin_matches'] and manifest['unchanged'] is True, 'retained archive consistency mismatch')
                        need(manifest['availability'] == {role: inventory.get(role, {}).get('type', 'absent') for role in KNOWN}, 'artifact availability mismatch')
                    try:
                        row['diagnostic'] = result_diagnostics(captured, inventory, manifest)
                    except Exception as exc:
                        # A stable snapshot can contain partial/malformed
                        # application JSON. Preserve its verified bytes and
                        # continue to other cases without calling it completion.
                        row['diagnostic'] = {'status': 'diagnostic_error',
                            'native_completion': 'not_inferred',
                            'error': type(exc).__name__ + ': ' + str(exc)}
                except Exception as exc:
                    row['archive_error'] = type(exc).__name__ + ': ' + str(exc)
                    need(status != 'retained', row['archive_error'])
            else:
                need(status in {'capture_failed', 'case_unavailable'}, 'successful/changed capture lacks archive')
                row['archive_available'] = False
            if status == 'case_unavailable':
                need(all(manifest[key] is None for key in ('before', 'archived', 'after', 'archive'))
                     and manifest['unchanged'] is False and tar_name not in files,
                     'unavailable case contains contradictory capture declarations')
            result['cases'].append(row)
        need({name for name in files if name.endswith('/case.tar.gz')} == manifested, 'tar has no case manifest')
    result['nodes_with_manifests'] = sorted({row['node_id'] for row in result['cases']})
    result['nodes_without_manifests_in_this_shard'] = sorted(set(CASES) - set(result['nodes_with_manifests']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.archive, read_json_file(args.metadata), read_json_file(args.expected))
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
