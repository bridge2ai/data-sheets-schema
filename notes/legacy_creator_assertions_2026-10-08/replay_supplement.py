"""External #4685 Creator supplement; run separately per reviewed checkout, never a publisher."""
import argparse
import contextlib
import hashlib
import importlib
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
NAMES = ('CHORUS', 'VOICE', 'CM4AI_reduced', 'VOICE_provenance', 'CM4AI_original')
INPUTS = {
    'CHORUS': ('data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json', '6d0fc1433008a525164154c635b604c98fb620787fbdcb02b87faf9bce643774'),
    'VOICE': ('data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json', 'a85057c8d60ed0e10dfac89a733a2ba399c33b7bbc5d291b89b1444dab1901d4'),
    'CM4AI_reduced': ('data/ro-crate_packages/CM4AI/processed/CM4AI_crate_metadata_reduced.json', '8f25e9478d1105a008769e25d2a2f67da8475c7218b58946f834ab448dec6610'),
    'VOICE_provenance': ('data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json', '2cedad47ab225713aca18bd250777fb741a5d5ee639e4b0e9cc63205adb08608'),
}
ARCHIVE = 'data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip'
ARCHIVE_SHA = 'a8a4fea0aa4cfb9797fe1871de064bf29563516c5de4aa834aa177fb7c6b1d4c'
MEMBER = 'cm4ai_release_metadata/ro-crate-metadata.json'
MEMBER_SHA = '836376f3a997204b14d4d8d3fba90d967b58cbe20726218c95d861b0cb11e66e'
REPLAY = 'notes/parser_root_policy_2026-10-07/replay.py'
REPLAY_SHA = '1c62c61e2cd646b23218594696ccd019989f6f8a26babc5fdbd1ccfcf351b9c2'
MAPPING = 'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'
SCHEMA = 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml'
MODULES = ('rocrate_parser', 'mapping_loader', 'd4d_builder', 'informativeness_scorer', 'rocrate_merger', 'field_prioritizer')
HISTORY = [f'data/ro-crate_packages/{name}/processed' for name in ('CHORUS', 'VOICE', 'CM4AI')]
HISTORY += ['data/d4d_concatenated/rocrate_static_map', 'data/d4d_concatenated/rocrate_mapped', 'notes/figures/fig09_mapping_revision_2026-10-07']
MAX_BYTES = 64 * 1024 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def read(path):
    require(path.is_file() and not path.is_symlink(), f'Expected regular non-symlink file: {path}')
    with path.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, f'File exceeds supplement bound: {path}')
    return raw


def pin(path):
    raw = read(path)
    return {'bytes': len(raw), 'sha256': digest(raw)}


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True).stdout


def write_json(path, value):
    path.write_bytes(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8') + b'\n')


def exception(exc):
    return {'type': f'{type(exc).__module__}.{type(exc).__qualname__}', 'message': str(exc), 'args': repr(exc.args)}


def gate(record, publication):
    try:
        raw = publication.prepare_dataset(record)
        import yaml
        require(encoded(yaml.safe_load(raw)) == encoded(record), 'Dataset gate changed record')
        return {'status': 'accepted', 'bytes': len(raw), 'sha256': digest(raw)}
    except publication.PublicationError as exc:
        return {'status': 'refused', 'exception': exception(exc)}
    except Exception as exc:
        return {'status': 'error', 'exception': exception(exc)}


def inventory(repo, paths):
    return {name: pin(repo / name) for name in sorted(set(paths))}


def author_evidence(root):
    value = root.get('author')
    return {'author_present': 'author' in root, 'nonnull': value is not None,
            'immediate_assertion_units': (0 if value is None else len(value) if isinstance(value, list) else 1),
            'raw_value': value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--expect-commit', required=True)
    parser.add_argument('--role', choices=('baseline', 'candidate'), required=True)
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protect-repo', type=Path, action='append', required=True)
    args = parser.parse_args()
    repo, replay, out = (path.resolve() for path in (args.repo, args.replay, args.output))
    protected = [path.resolve() for path in args.protect_repo]
    require(len(set(protected)) == 2 and repo in protected, 'Name both distinct baseline/candidate checkouts')
    for source in [*protected, replay, Path(__file__).resolve(), Path(sys.executable).resolve()]:
        require(out != source and source not in out.parents and out not in source.parents,
                f'Output overlaps protected path: {source}')
    require(not out.exists() and not args.output.is_symlink(), 'Output must be new')
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == args.expect_commit, 'Unexpected checkout commit')
    require(not git(repo, 'status', '--porcelain', '--untracked-files=all').strip(), 'Selected checkout must be clean')
    require(digest(read(repo / REPLAY)) == REPLAY_SHA, 'Historical replay utility differs')

    summary_path = replay / 'summary.json'
    previous = json.loads(read(summary_path))
    require(tuple(previous['inputs']) == NAMES, 'Replay roster/order differs')
    require(previous['replay_sha256'] == REPLAY_SHA, 'Unexpected replay utility')
    source_paths = set(previous['code_sha256']) | {MAPPING, SCHEMA, REPLAY, 'pyproject.toml', 'poetry.lock',
        'src/data_sheets_schema/legacy_doi.py', 'src/data_sheets_schema/legacy_publication.py',
        'src/data_sheets_schema/legacy_root_identity.py',
        'src/data_sheets_schema/legacy_update_plan.py',
        'src/transformation/transform_api.py', 'src/fairscape_integration/cli.py',
        '.claude/agents/scripts/rocrate_to_d4d.py',
        'src/data_sheets_schema/scope.py', 'src/fairscape_integration/constants.py',
        'notes/parser_root_policy_2026-10-07/validation.json'}
    source_paths |= {prefix + name + '.py' for prefix in ('src/fairscape_integration/utils/', '.claude/agents/scripts/') for name in MODULES}
    if args.role == 'candidate':
        source_paths.add('src/data_sheets_schema/legacy_creators.py')
    source_pins = inventory(repo, source_paths)
    for name in source_paths:
        require(read(repo / name) == git(repo, 'show', args.expect_commit + ':' + name), f'Dirty selected file: {name}')
    for name, sha in previous['code_sha256'].items():
        require(source_pins[name]['sha256'] == sha, f'Replay source binding differs: {name}')
    require(source_pins[MAPPING]['sha256'] == previous['mapping']['sha256'], 'Replay mapping differs')
    require(source_pins[SCHEMA]['sha256'] == previous['schema']['sha256'], 'Replay schema differs')

    original = {}
    for name, (relative, sha) in INPUTS.items():
        original[name] = read(repo / relative)
        require(digest(original[name]) == sha, f'Original input differs: {name}')
    require(digest(read(repo / ARCHIVE)) == ARCHIVE_SHA, 'CM4AI archive differs')
    with zipfile.ZipFile(repo / ARCHIVE) as archive:
        matches = [entry for entry in archive.infolist() if entry.filename == MEMBER]
        require(len(matches) == 1 and not matches[0].is_dir() and matches[0].file_size <= MAX_BYTES, 'Invalid selected archive member')
        original['CM4AI_original'] = archive.read(MEMBER)
    require(digest(original['CM4AI_original']) == MEMBER_SHA, 'CM4AI member differs')
    replay_paths = [summary_path]
    for name in NAMES:
        require(previous['inputs'][name]['input_sha256'] == digest(original[name]), f'Replay input declaration differs: {name}')
        path = replay / 'inputs' / (name + '.json')
        require(read(path) == original[name], f'Replay input bytes differ: {name}')
        reversed_path = path.with_name(name + '.reversed.json')
        document = json.loads(original[name]); reverse = dict(document)
        if isinstance(document.get('@graph'), list):
            reverse['@graph'] = list(reversed(document['@graph']))
        require(encoded(json.loads(read(reversed_path))) == encoded(reverse), f'Reversed graph changed: {name}')
        replay_paths.extend([path, reversed_path])
        for implementation in ('packaged', 'hidden'):
            for suffix in ('', '_reversed'):
                stem = f'{name}_{implementation}{suffix}'
                replay_paths.extend(replay / (stem + ending) for ending in ('.yaml', '.log', '.result.json'))
    replay_pins = {str(path.relative_to(replay)): pin(path) for path in replay_paths}
    histories = []
    for relative in HISTORY:
        directory = repo / relative
        require(directory.is_dir(), f'Missing historical directory: {relative}')
        histories.extend(str(path.relative_to(repo)) for path in directory.rglob('*') if path.is_file())
    preservation_paths = source_paths | {p for p, _ in INPUTS.values()} | {ARCHIVE} | set(histories)
    before = inventory(repo, preservation_paths)
    interpreter = Path(sys.executable).resolve()
    runtime = {'python': sys.version, 'executable': str(interpreter), 'identity': pin(interpreter),
               'dependencies': {name: importlib.metadata.version(name) for name in ('PyYAML', 'linkml', 'linkml-runtime')}}

    sys.path.insert(0, str(repo / 'src'))
    import yaml
    from data_sheets_schema import legacy_publication as publication
    creator_helper = None
    if args.role == 'candidate':
        from data_sheets_schema import legacy_creators as creator_helper
        require(Path(creator_helper.__file__).resolve() == repo / 'src/data_sheets_schema/legacy_creators.py', 'Imported wrong Creator helper')
    implementations = {}
    for kind in ('packaged', 'hidden'):
        if kind == 'hidden':
            sys.path.insert(0, str(repo / '.claude/agents/scripts'))
        modules = {name: importlib.import_module(('fairscape_integration.utils.' if kind == 'packaged' else '') + name) for name in MODULES}
        for name, module in modules.items():
            prefix = 'src/fairscape_integration/utils/' if kind == 'packaged' else '.claude/agents/scripts/'
            require(Path(module.__file__).resolve() == repo / (prefix + name + '.py'), 'Imported wrong producer module')
        implementations[kind] = modules
    require(Path(publication.__file__).resolve() == repo / 'src/data_sheets_schema/legacy_publication.py', 'Imported wrong Dataset gate')
    out.mkdir(parents=True, exist_ok=False)
    result = {'format': 'legacy_creator_supplement_v1', 'role': args.role,
        'commit': args.expect_commit, 'tree': git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip(),
        'driver': pin(Path(__file__).resolve()), 'runtime': runtime, 'source_pins': source_pins,
        'replay_pins': replay_pins, 'preservation_before': before,
        'roster': list(NAMES), 'rows': [], 'rankings': [], 'merges': [],
        'expected': {'records': 20, 'rankings': 4, 'merges': 8},
        'scientific_eligibility': False, 'historical_publication': False,
        'limitations': ['Local observed byte/commit/runtime pins, not authenticated execution or a complete environment snapshot.',
            'Preservation enumeration includes hidden/ignored files in the named historical directories only.',
            'Mixed-roster mergers are software comparisons, not scientific combined datasets.',
            'Both arms contain reviewed root-ID and maintenance-plan construction. Candidate preserves complete author literals and assertions; it does not infer people, identities, roles or improved source coverage.',
            'Ranked-primary merges select the actual top-ranked source while preserving the fixed source order for all other inputs; this is not an auto-reordered CLI replay.',
            'This per-arm supplement records evidence only; cross-arm comparison must compare complete records, ranks, scores and merge disclosures rather than treating collection_complete as equivalence.',
            'Dataset refusals remain evidence. This supplement does not repair saved drafts, generate provider output, run a scoring campaign or publish corpus records.']}
    for kind, modules in implementations.items():
        mapping = modules['mapping_loader'].MappingLoader(str(repo / MAPPING))
        for order in ('original', 'reversed'):
            parsers = []
            for name in NAMES:
                source = replay / 'inputs' / (name + ('.reversed' if order == 'reversed' else '') + '.json')
                stem = name + '_' + kind + ('_reversed' if order == 'reversed' else '')
                row = {'input': name, 'implementation': kind, 'order': order}
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        parsed = modules['rocrate_parser'].ROCrateParser(str(source))
                    parsers.append(parsed)
                    root = parsed.require_root_dataset()
                    expected = previous['inputs'][name]['consumers'][kind][order]
                    require(expected.get('parse') == expected.get('build') == 'PASS', 'Original replay did not build this row')
                    record = yaml.safe_load(read(replay / (stem + '.yaml')))
                    require(digest(encoded(root)) == expected['root_sha256'], 'Selected root changed')
                    require(digest(encoded(record)) == expected['record_sha256'], 'Replay draft record changed')
                    require(pin(replay / (stem + '.yaml'))['sha256'] == expected['output_sha256'], 'Replay YAML changed')
                    row.update(status='recorded', record=record, root=root, gate=gate(record, publication),
                               raw_author_evidence=author_evidence(root),
                               source_presence=(creator_helper.author_source_presence(mapping, [parsed], [name]) if creator_helper else None),
                               original_validation=expected.get('validation'), original_validation_errors=expected.get('validation_errors'))
                except Exception as exc:
                    row.update(status='error', exception=exception(exc))
                result['rows'].append(row)
            ranks = {'implementation': kind, 'order': order}
            try:
                require(len(parsers) == len(NAMES), 'Incomplete parser denominator')
                with contextlib.redirect_stdout(io.StringIO()):
                    ranked = modules['informativeness_scorer'].InformativenessScorer().rank_rocrates(parsers, mapping)
                ranks.update(status='recorded', rows=[{'source': NAMES[parsers.index(p)], 'index': parsers.index(p), 'scores': scores, 'rank': rank} for p, scores, rank in ranked])
                auto_index = parsers.index(ranked[0][0])
            except Exception as exc:
                ranks.update(status='error', exception=exception(exc)); auto_index = None
            result['rankings'].append(ranks)
            for mode, index in [('ranked_primary', auto_index), ('voice_provenance_primary', NAMES.index('VOICE_provenance'))]:
                merged = {'implementation': kind, 'order': order, 'mode': mode, 'primary_index': index}
                log = io.StringIO()
                try:
                    require(index is not None and len(parsers) == len(NAMES), 'Primary unavailable or incomplete parser denominator')
                    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                        merger = modules['rocrate_merger'].ROCrateMerger(mapping)
                        record = merger.merge_rocrates(parsers, primary_index=index, source_names=list(NAMES))
                        report = merger.generate_merge_report(parsers, source_names=list(NAMES))
                    report_name = f'{kind}_{order}_{mode}.txt'
                    (out / report_name).write_text(report, encoding='utf-8')
                    merged.update(status='recorded', primary_name=merger.primary_name, record=record,
                        provenance=merger.get_provenance(), statistics=merger.get_merge_stats(),
                        root_identity_sources=getattr(merger, 'root_identity_sources', None),
                        creator_assertion_sources=(merger.get_creator_assertion_sources() if creator_helper else None),
                        source_presence=(merger.get_source_presence() if creator_helper else None),
                        report={'path': report_name, **pin(out / report_name)}, gate=gate(record, publication),
                        schema_errors=[str(item.message) for item in publication._validator(
                            str(repo / SCHEMA), source_pins[SCHEMA]['sha256']).validate(
                                yaml.safe_load(yaml.safe_dump(record)), 'Dataset').results])
                except Exception as exc:
                    merged.update(status='error', exception=exception(exc))
                (out / f'{kind}_{order}_{mode}.log').write_text(log.getvalue(), encoding='utf-8')
                result['merges'].append(merged)
            write_json(out / 'summary.json', result)
    result['preservation_after'] = inventory(repo, preservation_paths)
    result['inputs_preserved'] = result['preservation_after'] == before
    result['replay_preserved'] = replay_pins == {str(path.relative_to(replay)): pin(path) for path in replay_paths}
    result['runtime_preserved'] = pin(interpreter) == runtime['identity']
    result['driver_preserved'] = pin(Path(__file__).resolve()) == result['driver']
    result['missing'] = {key: max(0, count - len(result['rows' if key == 'records' else key])) for key, count in result['expected'].items()}
    result['errors'] = [dict(section=key, index=i, exception=row['exception']) for key in ('rows', 'rankings', 'merges') for i, row in enumerate(result[key]) if row['status'] == 'error']
    result['gate_errors'] = [dict(section=key, index=i, exception=row['gate']['exception']) for key in ('rows', 'merges') for i, row in enumerate(result[key]) if row.get('gate', {}).get('status') == 'error']
    result['collection_complete'] = not any(result['missing'].values()) and not result['errors'] and not result['gate_errors'] and all(result[key] for key in ('inputs_preserved', 'replay_preserved', 'runtime_preserved', 'driver_preserved'))
    write_json(out / 'summary.json', result)
    print(json.dumps({'output': str(out), 'collection_complete': result['collection_complete'], 'errors': len(result['errors']), 'missing': result['missing']}))
    return 0 if result['collection_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
