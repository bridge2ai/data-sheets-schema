"""Reconcile U3-H packet, cohort, scanner and D126 evidence, 2026-11-09.

Inputs: a committed-source composition manifest, explicit required run labels,
the itemised scanner comparison and a discriminator cohort. Outputs: fresh
validation.json and FACTS.json in that manifest's U3-H owner-packet bundle.
Only local evidence and Git checks are read; packets are never installed and
tests/scanners/native programs are never launched. Owner prose stays pending.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
SCRATCH = EXEC / 'scratch-native-u1u3'
OUT = SCRATCH / 'u3h'
U3G_SOURCE = '26d3b0449b01f4276c177f9ea07a2757110441e8'
DISCRIMINATOR = ('tests/test_native_u4b_a5_producer_integration.py::'
                 'test_d126_in_checkout_manifest_pins_every_native_instruction_delta')


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + '\n').encode()


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def fresh(path, value):
    raw = encoded(value)
    with path.open('xb') as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise ValueError('artifact write verification failed: ' + str(path))
    return identity(path)


def verify_packets(g, c, h, manifest_path):
    manifest_path = g.physical(manifest_path, OUT)
    manifest = g.load(manifest_path)
    source = manifest['source_commit']
    tree = g.physical(manifest['tree'], OUT)
    bundle = g.physical(manifest['owner_bundle'], SCRATCH / 'owner-packets/u3h')
    g.need(bundle.name == source[:12], 'bundle is not named for the source commit')
    g.need(g.git('rev-parse', 'HEAD').decode().strip() == source, 'source HEAD moved')
    g.git('diff-index', '--quiet', 'HEAD', '--')
    g.need(g.git('rev-parse', 'HEAD', cwd=tree).decode().strip() == manifest['composition_commit'],
           'private composition HEAD moved')
    g.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    g.need(g.git('show', '-s', '--format=%P', 'HEAD', cwd=tree).decode().strip() == source,
           'private composition is not a direct child of the source')
    rows = manifest['packets']
    g.need(len(rows) == 4 and {row['name']: row['target'] for row in rows} == g.TARGETS,
           'packet roster differs from the four authorized targets')
    witnesses, patch_paths, result = {}, [], []
    canonical_before = canonical_after = None
    for row in rows:
        name, target = row['name'], row['target']
        frozen_path = ROOT / c.PACKET_DIRECTORY / (name + '.json')
        frozen = g.load(frozen_path)
        g.need(frozen_path.read_bytes() == c.strict_blob(source, str(frozen_path.relative_to(ROOT))),
               'frozen U1 metadata differs from source: ' + name)
        before, after = (ROOT / target).read_bytes(), (tree / target).read_bytes()
        g.need(before == c.strict_blob(source, target), 'source target differs from source commit')
        g.need(after == g.git('show', manifest['composition_commit'] + ':' + target, cwd=tree),
               'private target differs from composition commit')
        for suffix, raw in (('preimage', before), ('postimage', after)):
            path = g.physical(bundle / (name + '.' + suffix), bundle)
            g.need(path.read_bytes() == raw and sha(raw) == row[suffix + '_sha256'],
                   'packet image mismatch: ' + name + '.' + suffix)
            witnesses[str(path)] = sha(raw)
        path = g.physical(bundle / (name + '.patch'), bundle)
        patch_paths.append(str(path))
        g.need(sha(path.read_bytes()) == row['patch_sha256'], 'packet patch hash mismatch: ' + name)
        witnesses[str(path)] = sha(path.read_bytes())
        metadata = g.physical(bundle / (name + '.json'), bundle)
        g.need(g.load(metadata) == row, 'packet metadata differs from manifest: ' + name)
        witnesses[str(metadata)] = sha(metadata.read_bytes())
        g.need(row['preimage_sha256'] == frozen['preimage_sha256']
               and row['u1_postimage_sha256'] == frozen['postimage_sha256']
               and row['u1_patch_sha256'] == frozen['patch_sha256']
               and frozen['target'] == target, 'frozen U1 identity mismatch: ' + name)
        changed = name == 'canonical_hashes'
        g.need(row['changed_from_u1'] is changed, 'incorrect packet change declaration')
        if changed:
            g.need(sha(after) == h.EXPECTED_CANONICAL_SHA256,
                   'canonical postimage is not the independently reviewed two-addition variant')
            canonical_before, canonical_after = before, after
        else:
            frozen_patch = c.strict_blob(source, c.PACKET_DIRECTORY + '/' + name + '.patch')
            g.need(path.read_bytes() == frozen_patch and sha(after) == frozen['postimage_sha256'],
                   'unchanged U1 packet bytes differ: ' + name)
        result.append(dict(row, frozen_u1_metadata=frozen,
                           frozen_u1_metadata_sha256=sha(frozen_path.read_bytes())))
    # Reconstruct the exact original U1 postimage from the only two approved
    # location lines, then run the composer's independent byte/pin assertions.
    import yaml
    registry = yaml.safe_load(canonical_after)
    lines = canonical_after.splitlines(keepends=True)
    restored = list(lines)
    for asset in h.U1_ADDITIONS:
        g.need(registry['files'][asset]['pinned_in_repository'] == '.', 'U1 location is not dot')
        marker = ('  ' + asset + ':\n').encode()
        g.need(lines.count(marker) == 1, 'canonical asset block is not unique')
        start = lines.index(marker) + 1
        end = next((i for i in range(start, len(lines))
                    if lines[i].startswith(b'  ') and not lines[i].startswith(b'    ')), len(lines))
        indices = [i for i in range(start, end) if lines[i] == b'    pinned_in_repository: .\n']
        g.need(len(indices) == 1, 'canonical asset location line is not unique')
        restored[indices[0]] = ('    pinned_in_repository: ' + h.U1_LOCATION + '\n').encode()
    expected, changes = h.normalize_u1_additions(c, b''.join(restored), canonical_before)
    g.need(expected == canonical_after and changes == manifest['canonical_repository_path_changes'],
           'canonical normalization declaration differs from exact byte proof')
    c.sidecar_check(tree, c.strict_blob(source, c.PACKETS[-1][1]))
    g.need(set(g.git('diff', '--name-only', source, manifest['composition_commit'], cwd=tree)
               .decode().splitlines()) == set(g.TARGETS.values()), 'composition changes extra paths')
    g.git('apply', '--check', *patch_paths)
    g.git('apply', '--check', '--reverse', *patch_paths, cwd=tree)
    return manifest, tree, bundle, result, witnesses


def cohort_facts(g, manifest, labels, ledger):
    summaries = {row['run']: row for row in g.load(OUT / 'validation-summary.json')}
    rows = []
    for label in labels:
        row = summaries.get(label, {})
        composed = label.startswith('composed-')
        expected = manifest['composition_commit' if composed else 'source_commit']
        root = manifest['tree'] if composed else str(ROOT)
        origin = row.get('source_commit') == expected and row.get('source_root') == root
        counts = row.get('counts', {})
        executed = bool(row) and origin and not row.get('missing_artifacts', ['missing'])
        executed = bool(executed and row.get('malformed_xml') is None
            and row.get('returncode') in (0, 1) and row.get('cleanup_verified') is True
            and row.get('worker', {}).get('source_origin_checks_passed') is True
            and row.get('interrupted') in (None, False) and row.get('workers', 99) <= 2
            and 0 <= row.get('seconds', 9999) < 3300 and sum(counts.values()) > 0)
        rows.append(dict(label=label, present=bool(row), matches_current_source=origin,
            executed=executed, all_nodes_passed=executed and bool(row.get('completed_pass')),
            counts=counts, missing_artifacts=row.get('missing_artifacts', ['run absent']),
            skipped_nodes=[item for item in ledger if item['run'] == label and item['status'] == 'skipped'],
            failed_nodes=[item for item in ledger if item['run'] == label and item['status'] in ('failed', 'error')]))
    return rows


def affected_tests(g, source, labels):
    planner = module('u3h_final_planner', 'plan_native_u3h_20261109.py')
    inventory = module('u3h_final_reader_roster', 'native_u3h_registry_readers_20261109.py')
    readers = ['tests/' + name for name in planner.READERS]
    g.need(len(readers) == len(set(readers)) and set(readers) == set(inventory.READERS),
           'planner and reviewed registry-reader inventory differ')
    tracked = g.git('ls-tree', '-r', '--name-only', source, '--', 'tests').decode().splitlines()
    shared = sorted(name for name in tracked if re.fullmatch(r'tests/test_shared_generation_[^/]+\.py', name))
    g.need(shared, 'shared-generation test roster is empty')
    plans, covered, by_cohort = [], set(), {}
    for path in sorted(OUT.glob('*.json')):
        document = g.load(path)
        if not isinstance(document, dict) or document.get('kind') != 'native_u3h_offline_cohort_plan':
            continue
        selected = [row for row in document['cohorts'] if Path(row['out']).name in labels]
        if not selected:
            continue
        g.physical(path, OUT)
        plans.append(dict(identity(path), source_root=document['source_root'],
                          selected_cohorts=[row['name'] for row in selected]))
        for row in selected:
            g.need(Path(row['out']) == OUT / Path(row['out']).name, 'planner output is aliased')
            selected_files = {node.split('::')[0] for node in row['nodes']}
            covered.update(selected_files)
            by_cohort.setdefault(row['name'], set()).update(selected_files)
    files = []
    for name in sorted(set(readers) | set(shared)):
        raw = cblob = g.git('show', source + ':' + name)
        g.need((ROOT / name).read_bytes() == cblob, 'affected test differs from source: ' + name)
        files.append(dict(path=name, sha256=sha(raw), bytes=len(raw),
            registry_reader=name in readers, shared_generation_suite=name in shared,
            selected_in_required_plans=name in covered,
            offline_execution=('unavailable_network_install_opt_in' if name.endswith('test_installed_wheel.py')
                               else 'see_exact_node_ledger')))
    selected_identities = []
    for name in sorted(covered):
        raw = g.git('show', source + ':' + name)
        g.need((ROOT / name).read_bytes() == raw, 'planned test differs from source: ' + name)
        selected_identities.append(dict(path=name, sha256=sha(raw), bytes=len(raw),
            cohorts=sorted(key for key, names in by_cohort.items() if name in names)))
    return dict(registry_reader_count=len(readers), shared_generation_file_count=len(shared),
        files=files, planner=identity(ROOT / 'scripts/adhoc/plan_native_u3h_20261109.py'),
        cohort_plans=plans, all_required_files_selected=all(row['selected_in_required_plans'] for row in files),
        selected_cohort_file_identities=selected_identities,
        scope='Explicit planner registry readers plus every committed top-level test_shared_generation_*.py.')


def discriminator_facts(g, label, manifest, ledger):
    folder = g.physical(OUT / label, OUT)
    cases = g.physical(folder / 'cases', folder)
    observed = [row for row in ledger if row['run'] == label and row['node'].startswith(DISCRIMINATOR + '[')]
    g.need(len(observed) == 2 and all(row['status'] == 'passed' for row in observed),
           'D126 discriminator did not pass both runtime variants')
    paths, ignored_aliases = [], []
    for directory, dirs, files in os.walk(cases, followlinks=False):
        g.quiet()
        parent = Path(directory)
        for name in list(dirs):
            if (parent / name).is_symlink():
                ignored_aliases.append(str(parent / name))
                dirs.remove(name)
        if 'd126-instruction-delta.json' in files:
            paths.append(g.physical(parent / 'd126-instruction-delta.json', cases))
    g.need(len(paths) == 2, 'need exactly two physical D126 discriminator witnesses')
    values = []
    for path in sorted(paths):
        data = g.load(path)
        g.need(type(data) is dict and data.get('decision') == 'D126'
               and type(data.get('u4b_runtime')) is bool, 'invalid D126 evidence payload')
        before_path = g.physical(path.parent / 'before-instruction.txt', cases)
        after_path = g.physical(path.parent / 'after-instruction.txt', cases)
        before, after = before_path.read_bytes(), after_path.read_bytes()
        g.need(sha(before) == data['before_sha256'] and sha(after) == data['after_sha256'],
               'D126 raw instruction hash mismatch')
        left, right = before.splitlines(keepends=True), after.splitlines(keepends=True)
        g.need(len(left) == len(right), 'D126 instruction line count changed')
        actual = [i for i, (a, b) in enumerate(zip(left, right), 1) if a != b]
        changes = data['changed_lines']
        g.need(actual == [row['line_index1'] for row in changes]
               and len(changes) == data['expected_change_count'] == data['observed_change_count'] == 11,
               'D126 exact changed-line roster mismatch')
        for row in changes:
            index = row['line_index1'] - 1
            g.need(row['before'].encode() == left[index] and row['after'].encode() == right[index]
                   and row['before_sha256'] == sha(left[index]) and row['after_sha256'] == sha(right[index]),
                   'D126 exact changed-line bytes mismatch')
        g.need(data['unchanged_line_count'] == len(left) - 11, 'D126 unchanged line count mismatch')
        mapping = data['private_root_mapping']
        g.need(set(mapping) == {'checkout_root', 'test_artifact_root', 'interpreter'}
               and all(isinstance(value, str) and Path(value).is_absolute() for value in mapping.values()),
               'D126 root mapping missing or malformed')
        expected_root = manifest['tree'] if label.startswith('composed-') else str(ROOT)
        g.need(mapping['checkout_root'] == expected_root, 'D126 checkout does not match source')
        g.physical(mapping['test_artifact_root'], cases)
        replacements = sorted(((mapping['checkout_root'], '<CHECKOUT>'),
            (mapping['test_artifact_root'], '<CASE_ROOT>'), (mapping['interpreter'], '<PYTHON>')),
            key=lambda row: len(row[0]), reverse=True)

        def redact(text):
            for old, new in replacements:
                text = text.replace(old, new)
            return text

        presentation = [dict(role=row['role'], line_index1=row['line_index1'],
            before=redact(row['before']), after=redact(row['after'])) for row in changes]
        g.need(not any(prefix in encoded(presentation).decode() for prefix in
                       ('/Users/', '/private/tmp/', '/private/var/folders/')),
               'D126 presentation retains an unmapped private absolute path')
        values.append(dict(raw_evidence=identity(path), private_payload=data,
            raw_instructions=[identity(before_path), identity(after_path)],
            redacted_presentation=presentation, redacted_presentation_sha256=sha(encoded(presentation)),
            redaction_mapping=dict(replacements),
            redaction_policy='Literal longest-prefix replacement in presentation only; raw bytes and hashes are retained privately.',
            raw_and_redacted_bytes_claimed_equal=False, raw_publication_ready=False))
    g.need({value['private_payload']['u4b_runtime'] for value in values} == {False, True},
           'D126 witnesses do not cover historical and U4b runtimes')
    return dict(decision='D126_accept_declare_redact', run=label, exact_line_evidence=values,
        physical_witness_count=2, ignored_symlink_aliases=ignored_aliases,
        private_payload_exact=True, public_representation='redacted_presentation only')


def scanner_facts(g, path, manifest):
    path = g.physical(path, OUT)
    value = g.load(path)
    g.need(value.get('status') == 'prepared_itemised_comparisons_not_owner_retirement'
           and value.get('historical_gate_retired') is False, 'itemised comparison status differs')
    rows = {row['label']: row for row in value['inputs']}
    g.need({'saved_main_cf50', 'literal_f2_77b', 'candidate'} <= rows.keys(), 'scanner inputs missing')
    for label, expected in (('saved_main_cf50', g.SAVED_MAIN), ('literal_f2_77b', g.BASE),
                            ('candidate', manifest['composition_commit'])):
        row = rows[label]
        g.need(row['source']['commit'] == expected and row['tool_commit'] == manifest['source_commit'],
               'itemised source/tool identity differs: ' + label)
        directory = g.physical(row['run_directory'], OUT)
        g.need(sha((directory / 'run.json').read_bytes()) == row['run_json_sha256'],
               'scanner run witness changed: ' + label)
        if row['derivation_complete']:
            raw = (directory / 'scanner.json').read_bytes()
            g.need(sha(raw) == row['scanner_json_sha256'] and
                   {key: json.loads(raw)[key] for key in ('hits', 'violations', 'test_dependencies')} == row['arrays'],
                   'scanner full-array witness changed: ' + label)
        else:
            g.need(row['exit_code'] == 2 and row['arrays'] is None, 'incomplete scan wrongly represented')
    baseline_path = g.physical(SCRATCH / 'baseline-scanner.json', SCRATCH)
    baseline = g.load(baseline_path)['violations']
    g.need(len(baseline) == 9, 'saved baseline does not contain nine violations')
    exact = all(rows[name]['derivation_complete'] and rows[name]['arrays']['violations'] == baseline
                for name in ('saved_main_cf50', 'candidate'))
    return dict(itemised_artifact=identity(path), saved_baseline=identity(baseline_path),
        exact_nine_candidate_and_main=exact, candidate_commit=manifest['composition_commit'],
        literal_f2_exit_code=rows['literal_f2_77b']['exit_code'],
        literal_f2_derivation_complete=rows['literal_f2_77b']['derivation_complete'],
        literal_f2_comparison_status=next(row['status'] for row in value['comparisons']
                                        if row['before'] == 'literal_f2_77b'),
        comparisons=value['comparisons'], historical_d258_gate='pending_not_rerun_not_retired',
        owner_disposition_pending=True)


def nonpacket_changes(g, source):
    rows = []
    for label, base in (('since_f2', g.BASE), ('since_u3g_source', U3G_SOURCE)):
        names = g.git('diff', '--name-status', base, source).decode().splitlines()
        raw = g.git('diff', '--binary', '--full-index', base, source)
        g.need(not any(line.split('\t')[-1] in g.TARGETS.values() for line in names),
               'branch changes touch a protected packet target')
        rows.append(dict(basis=label, base_commit=base, source_commit=source,
            changed_paths=names, diff_sha256=sha(raw), diff_bytes=len(raw),
            classification='nonpacket_committed_branch_changes'))
    return dict(comparisons=rows,
        runtime_change='The native producer registered_input_paths=True change belongs to the nonpacket branch history; D126 accepts its absolute-path instruction effect. It is not part of any protected packet.',
        d126_discriminator='The in-checkout comparison explicitly holds runtime choice constant and contrasts the historical false control with the genuine registered producer.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--labels', nargs='+', required=True)
    p.add_argument('--itemized', type=Path, required=True)
    p.add_argument('--discriminator-run', required=True)
    p.add_argument('--parity-labels', nargs='*', help='Default: required labels ending in -parity.')
    a = p.parse_args()
    g = module('u3h_final_summary', 'summarize_native_u3g_20261109.py')
    g.s.OUT = OUT
    c = module('u3h_final_u1', 'compose_native_u1u3_20261108.py')
    h = module('u3h_final_composer', 'compose_native_u3h_20261109.py')
    g.quiet()
    g.physical(ROOT, EXEC)
    g.physical(OUT, SCRATCH)
    g.need(len(set(a.labels)) == len(a.labels) and all(re.fullmatch(r'(worktree|composed)-[a-z0-9-]+',
            label) for label in a.labels), 'required labels must be unique assigned cohort names')
    g.need(a.discriminator_run in a.labels, 'discriminator must be a required cohort')
    source = g.git('rev-parse', 'HEAD').decode().strip()
    g.need(c.strict_blob(source, str(Path(__file__).relative_to(ROOT))) == Path(__file__).read_bytes(),
           'finalizer must be committed with the source it evaluates')
    manifest, tree, bundle, packets, witnesses = verify_packets(g, c, h, a.manifest)
    for name in ('validation.json', 'FACTS.json'):
        g.need(not os.path.lexists(bundle / name), 'final evidence output already exists: ' + name)
    g.summary()
    ledger = g.load(OUT / 'exact-node-ledger.json')
    cohorts = cohort_facts(g, manifest, a.labels, ledger)
    parity = {}
    parity_labels = a.parity_labels if a.parity_labels is not None else [name for name in a.labels if name.endswith('-parity')]
    for label in parity_labels:
        g.need(label in a.labels, 'parity must be a required cohort')
        error = None
        try:
            g.parity(label)
        except ValueError as exc:
            error = str(exc)
        path = OUT / (label + '-comparison.json')
        data = g.load(path) if path.is_file() else []
        parity[label] = dict(total=len(data), equal=sum(row['equal'] for row in data),
                            passed=error is None and len(data) == 14 and all(row['equal'] for row in data),
                            error=error, evidence=identity(path) if path.is_file() else None)
    tests = affected_tests(g, source, a.labels)
    d126 = discriminator_facts(g, a.discriminator_run, manifest, ledger)
    scanner = scanner_facts(g, a.itemized, manifest)
    nonpacket = nonpacket_changes(g, source)
    flags = dict(proposed_packet_artifacts_verified=True, protected_worktree_unchanged=True,
        forward_check=True, reverse_check=True, required_cohorts=cohorts,
        required_cohorts_executed=all(row['executed'] for row in cohorts),
        required_cohorts_all_nodes_passed=all(row['all_nodes_passed'] for row in cohorts),
        registry_and_shared_files_selected=tests['all_required_files_selected'],
        installed_wheel_acceptance=False, installed_wheel_status='unavailable_offline_network_install_not_opted_in',
        saved_main_exact_nine=scanner['exact_nine_candidate_and_main'], raw_api_parity=parity,
        historical_d258_gate='pending_not_rerun_not_retired', owner_prose='pending_lead_not_created',
        native_execution_acceptance=False, provider_or_native_canary_acceptance=False)
    unmet = ['Owner review prose remains pending.', 'Historical d258 full-array gate remains pending; it was not rerun or retired.',
             'Installed-wheel acceptance is unavailable offline; skips do not count as acceptance.',
             'No real native/provider/canary acceptance is established by these offline tests.']
    unmet += ['Required cohort not completely executed: ' + row['label'] for row in cohorts if not row['executed']]
    unmet += ['Required cohort contains failures or skips: ' + row['label'] for row in cohorts
              if row['executed'] and not row['all_nodes_passed']]
    if not tests['all_required_files_selected']:
        unmet.append('The supplied cohort plans do not select every registry/shared-generation test file.')
    if not scanner['exact_nine_candidate_and_main']:
        unmet.append('Saved-main/candidate nine-violation equality is unmet.')
    if not scanner['literal_f2_derivation_complete']:
        unmet.append('Literal F2 scanner derivation is incomplete; exit 2 is not comparison acceptance.')
    if len(parity) != 2 or not all(value['passed'] for value in parity.values()):
        unmet.append('The pair of worktree/composed raw API parity gates is incomplete or failed.')
    for name in ('validation-summary.json', 'exact-node-ledger.json', 'evidence-hashes.json',
                 'protected-files.json', 'nonpassing-attempts.json'):
        witnesses[str(OUT / name)] = sha((OUT / name).read_bytes())
    packet_cohorts = {
        'canonical_hashes': {'registry', 'registry-shared'},
        'shared_generation': {'hooks', 'f2-core', 'f2-delegated', 'f2-specificity', 'd114',
                              'u4b', 'parity-canary', 'parity', 'registry-shared'},
        'api_runner_companion': {'hooks', 'f2-core', 'f2-delegated', 'f2-specificity', 'd114',
                                 'u4b', 'parity-canary', 'parity', 'registry-shared'},
        'run_spec_boundary_contracts': {'f2-core', 'hooks'},
    }
    for row in packets:
        selected = packet_cohorts[row['name']]
        row['affected_test_files'] = [item for item in tests['selected_cohort_file_identities']
                                     if selected.intersection(item['cohorts'])]
        row['planned_validation_cohorts'] = sorted(selected)
        row['validation_scope'] = ('Declared relevant cohort-file coverage, pinned to the source commit; '
            'not an exhaustive dynamic dependency claim. Exact-node outcomes and skips remain separate.')
    g.need(g.git('rev-parse', 'HEAD').decode().strip() == source, 'source HEAD moved while finalizing')
    g.git('diff-index', '--quiet', 'HEAD', '--')
    g.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    g.quiet()
    common = dict(status='offline_evidence_reconciled_unmet_gates_explicit', source_commit=source,
        composition_commit=manifest['composition_commit'], manifest=identity(a.manifest),
        owner_bundle=str(bundle), owner_review_status='pending_lead_text_not_written',
        no_native_acceptance=True, worktree_packets_installed=False, acceptance_flags=flags,
        unmet_gates=unmet, helper=identity(Path(__file__)))
    validation = dict(common, packets=packets, artifact_sha256=witnesses,
        all_retained_runs=g.load(OUT / 'validation-summary.json'),
        nonpassing_attempts=g.load(OUT / 'nonpassing-attempts.json'),
        scanner_comparison=scanner, d126_instruction_disclosure=d126,
        registry_and_shared_validation=tests, nonpacket_branch_changes=nonpacket)
    validation_identity = fresh(bundle / 'validation.json', validation)
    facts = dict(common, validation=validation_identity, packet_changes=packets,
        frozen_u1_identity_preserved_except_two_new_registry_locations=True,
        canonical_historical_entries_byte_identical=True,
        canonical_postimage_sha256=h.EXPECTED_CANONICAL_SHA256,
        d126_instruction_disclosure=d126, nonpacket_branch_changes=nonpacket,
        registry_and_shared_validation=tests, scanner_comparison=scanner,
        publication_warning='Private raw paths, exact raw lines and hashes are retained here. Only the separately identified redacted presentation is prepared for publication; FACTS.json itself is private.',
        required_cohorts_complete_definition='See executed versus all_nodes_passed flags separately; neither skips nor an unavailable installed-wheel run are converted to acceptance.')
    facts_identity = fresh(bundle / 'FACTS.json', facts)
    print(json.dumps(dict(validation=validation_identity, facts=facts_identity,
                          source_commit=source, unmet_gates=unmet), sort_keys=True))


if __name__ == '__main__':
    main()
