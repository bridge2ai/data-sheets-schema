"""Synthetic offline preparation fixtures, never real canary acceptance."""
from collections import Counter
import json
from pathlib import Path
import sys

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prepare_evaluation as prepare
from registration import BudgetStop, read_json, sha, verify_manifest
from api import render_request
from instructions import verify_instruction


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


@pytest.fixture
def accepted_fixture(tmp_path, monkeypatch):
    generation_dir = tmp_path / 'synthetic_generation'; generation_dir.mkdir()
    files = {}
    for variant, kind in [('full', 'Dataset'), ('core', 'CoreDataset')]:
        files[variant] = generation_dir / (variant + '.yaml')
        files[variant].write_text(yaml.safe_dump({kind: {
            'id': 'https://example.org/synthetic-offline-fixture', 'name': 'Synthetic test dataset',
            'description': 'Synthetic documentation retained only to test request construction.',
            'keywords': []}}, sort_keys=False))
    bundle = generation_dir / 'source.txt'; bundle.write_text('Synthetic source for an offline preparation fixture.\n')
    context = tmp_path / 'context.json'; context.write_text('{}\n')
    native = tmp_path / 'synthetic-version-only-runtime'
    native.write_text('#!/bin/sh\nprintf "%s\\n" "2.1.272 (Claude Code)"\n')
    native.chmod(0o700)
    billing = generation_dir / 'billing.json'
    source = {'repository': str(generation_dir), 'provider_base_url': 'https://api.cborg.lbl.gov',
        'provider_context_policy': 'headroom_bypass_v1',
        'model': {'model': 'claude-opus-5', 'route_model': 'vertex_ai/claude-opus-5'},
        'pinned_files': {'source.txt': sha(bundle)},
        'budget': {'ledger_path': str(billing), 'prices_per_token': {
            'input': 0.000005, 'output': 0.000025, 'cache_write': 0.00000625, 'cache_read': 0.0000005}},
        'generation': {'jobs': [{'id': 'synthetic_generation', 'project': 'synthetic-example',
            'method': 'author_supplied', 'profile': 'neutral', 'bundle': 'source.txt',
            'input_identity': {'bundle': {'path': str(bundle), 'sha256': sha(bundle)}},
            'outputs': {key: path.name for key, path in files.items()}}]}}
    source_path = write(generation_dir / 'registration.json', source)
    write(billing, {'manifest_sha256': sha(source_path), 'additional_cap_usd': '400', 'attempt_cap_usd': '5',
        'requests': [{'id': 'synthetic-prior-charge', 'attempt': 'synthetic-generation',
                      'status': 'settled', 'cost_usd': '100.00'}]})
    checkpoint = tmp_path / 'generation_checkpoint.json'; checkpoint.write_bytes(billing.read_bytes())
    acceptance = write(generation_dir / 'SYNTHETIC_acceptance_fixture.json', {
        'fixture_only': True, 'verdict': 'accept', 'registration_sha256': sha(source_path),
        'job_id': 'synthetic_generation', 'artifacts': {str(path): sha(path) for path in files.values()},
        'evaluation_sequence_state': str(tmp_path / 'separate_sequence/current.json')})
    # Capture must use injected local request collectors only. A provider
    # client constructor (including token counting) makes this test fail.
    import budgeted_cborg
    import anthropic
    monkeypatch.setattr(budgeted_cborg, 'cborg_client', lambda *a, **kw: pytest.fail('provider constructed during preparation'))
    monkeypatch.setattr(anthropic, 'Anthropic', lambda *a, **kw: pytest.fail('provider constructed during preparation'))
    return {'destination': tmp_path / 'prepared', 'generation_registration': source_path,
        'generation_acceptance': acceptance, 'generation_job_id': 'synthetic_generation',
        'context_path': context, 'billing_checkpoint': checkpoint, 'native_executable': native}


def test_actual_renderers_prepare_twenty_rubric_ratings_and_all_eligible_slots(accepted_fixture):
    accepted_fixture['method'] = 'author_supplied_core'
    result = prepare.build_registration(**accepted_fixture)
    manifest = read_json(result['registration'])
    jobs = manifest['evaluation_jobs']
    counts = Counter(job['style'] for job in jobs)
    assert counts == {'semantic_agent': 12, 'field_agent': 4, 'direct_api_quality': 4, 'grounding': 6, 'fitness': 6}
    assert result['report']['rubric_ratings'] == 20
    assert result['report']['provider_calls'] == result['report']['token_count_calls'] == 0
    assert result['report']['remaining_allocation_usd'] == '300.00'
    assert {job['method'] for job in jobs} == {'author_supplied_core'}
    assert [not job['canary'] for job in jobs] == sorted(not job['canary'] for job in jobs)
    assert [job['rating'] > 1 for job in jobs] == sorted(job['rating'] > 1 for job in jobs)
    assert len(result['report']['planning_estimates']) == len(jobs)
    assert 'heuristic' in result['report']['cost_estimate']
    assert manifest['conditional_subtype']['selection'] == 'all_form_failures'
    assert all(job['style'] != 'subtype' for job in jobs)
    inventory = read_json(accepted_fixture['destination'] / 'slot_inventory.json')
    for variant in ('full', 'core'):
        assert [row['slot'] for row in inventory[variant]['included']] == ['description', 'id', 'name']
        assert inventory[variant]['excluded'][0]['slot'] == 'keywords'
        for style in ('grounding', 'fitness'):
            selected = [job for job in jobs if job['variant'] == variant and job['style'] == style]
            assert selected[0]['canary'] and selected[0]['slot'] == 'description'
            assert all(not job['canary'] and job['canary_acceptance'] for job in selected[1:])
    verify_manifest(manifest, result['registration'], sha(result['registration']))
    for job in jobs:
        if job['style'] in ('semantic_agent', 'field_agent'):
            verify_instruction(manifest, job)
        else:
            assert read_json(job['expected_request']) == render_request(manifest, job)
        assert not Path(job['candidate']).exists() and not Path(job['output']).exists()
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not Path(manifest['source_generation']['evaluation_sequence_state']).exists()
    assert not (accepted_fixture['destination'] / 'acceptances').exists()
    with pytest.raises(BudgetStop, match='already exists'):
        prepare.build_registration(**accepted_fixture)


@pytest.mark.parametrize('mutation', ['no_acceptance', 'changed_record', 'changed_bundle', 'pending_charge', 'stale_checkpoint', 'profile_override'])
def test_preparer_requires_actual_unchanged_acceptance_and_settled_budget(accepted_fixture, mutation):
    args = accepted_fixture
    generation = read_json(args['generation_registration'])
    acceptance = read_json(args['generation_acceptance'])
    if mutation == 'no_acceptance':
        acceptance['verdict'] = 'pending'; write(args['generation_acceptance'], acceptance)
    elif mutation == 'changed_record':
        full = Path(generation['repository']) / generation['generation']['jobs'][0]['outputs']['full']
        full.write_text('id: changed\n')
    elif mutation == 'changed_bundle':
        (Path(generation['repository']) / 'source.txt').write_text('Different source assertions after generation.\n')
    elif mutation == 'pending_charge':
        ledger = read_json(args['billing_checkpoint']); ledger['requests'][0]['status'] = 'pending'
        write(args['billing_checkpoint'], ledger); write(Path(generation['budget']['ledger_path']), ledger)
    elif mutation == 'stale_checkpoint':
        Path(generation['budget']['ledger_path']).write_text('{}\n')
    else:
        args['profile'] = 'bridge2ai'
    with pytest.raises(BudgetStop):
        prepare.build_registration(**args)
    assert not args['destination'].exists()


def test_ambiguous_resource_container_is_reported_without_scoring_only_its_children(tmp_path):
    source = tmp_path / 'ambiguous.yaml'
    source.write_text('id: parent\nresources:\n  - id: child\n')
    schema = prepare.ROOT / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml'
    with pytest.raises(BudgetStop, match='ambiguous dataset/collection'):
        prepare.slot_inventory(source, 'Dataset', schema)


def test_core_resources_are_components_under_the_explicit_core_class(tmp_path):
    source = tmp_path / 'core.yaml'
    source.write_text('CoreDataset:\n  id: parent\n  resources:\n    - id: child\n')
    schema = prepare.ROOT / 'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml'
    inventory = prepare.slot_inventory(source, 'CoreDataset', schema)
    assert all(row['unit_path'] == '#' for row in inventory['included'])
    assert any(row['slot'] == 'resources' for row in inventory['included'])
