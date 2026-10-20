"""Recorder path component controls, not an admitted/final helper execution.

The S, freshly bound rendering, command policy, clock lease and owner reader are
real. Only the preceding complete live-run/pending/final/record proof components
are doubles: a synthetic reader association cannot claim final native history.
The actual writer guard, helper association and filesystem checks run unchanged.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_shared_render import native_spec, declaration
from tests.test_native_owner_live_reader import reader_case, entered_case, sync_case
from tests.test_native_owner_runner import selected_controls, fixed_clock


@pytest.fixture
def destination_case(native_spec, request, tmp_path, monkeypatch):
    # Resolve reader_case only after native_spec has added its actual source
    # manifest to S. Do not combine bound's broad subprocess trap with the
    # actual reader binder, which must run its named-Git source proof.
    case = request.getfixturevalue('reader_case')
    root = case['root']
    other_cwd = root / 'other-working-directory'
    other_cwd.mkdir()
    binary = root / 'recorder-path-never-invoked'
    binary.write_bytes(b'#!/bin/sh\nexit 99\n')
    binary.chmod(0o700)
    runtime = c.strict_json(native_spec._native_shared_runtime_capture.raw)
    runtime['executable'].update(path=str(binary), sha256=c.sha(binary.read_bytes()))
    runtime['auth'] = {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
        'subscriptionType': 'synthetic-software-test', 'expected_api_key_source': 'none'}
    runtime['environment'] = {'PATH': '/usr/bin:/bin', 'HOME': str(root),
        'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '1'}
    runtime_path = root / 'recorder-path-runtime.json'
    runtime_path.write_bytes(c.canonical(runtime))

    @contextmanager
    def opened(layout='relative'):
        assert layout in ('relative', 'absolute')
        captured_cwd = root if layout == 'relative' else other_cwd
        ambient_cwd = other_cwd if layout == 'relative' else root
        with monkeypatch.context() as patch:
            patch.chdir(captured_cwd)
            spec = replace(native_spec)
            controller.bind_runtime(spec, runtime_path, 3)
            instruction = root / ('recorder-path-' + layout + '.md')
            instruction.write_bytes(spec.instruction.encode('utf-8'))
            derived = policy.command_policy(spec, str(instruction), controls=case['controls'])
            declared = derived['post_final_recorder']['destination']
            assert Path(declared).is_absolute() == (layout == 'absolute')
            assert Path(spec._agentic_artifact_paths['core']).is_absolute() == (layout == 'absolute')
            assert declared == str(Path(spec._agentic_artifact_paths['core']).parent /
                                   (spec.project + '_provenance.yaml'))
            destination = Path(declared) if layout == 'absolute' else captured_cwd / declared
            case['composition'].update(policy=derived, render_spec=spec.render_spec(),
                instruction_path=str(instruction), working_directory=str(captured_cwd))
            case['execution']['working_directory'] = str(captured_cwd)
            sync_case(case)
            run = SimpleNamespace(selection=case['selection'], composition=case['composition'],
                binding=SimpleNamespace(working_directory=str(captured_cwd)))
            record = {'prompts': {'request': {'spec': deepcopy(spec.render_spec())}},
                'native_shared_generation': {'component_fixture': 'no final-history claim'}}
            calls = []

            def load(selection_path, *, owner_context):
                assert selection_path == case['selection'].registration.pin.path
                assert owner_context is context
                owner_context.require_current()
                calls.append('load')
                return run

            def effect(actual):
                assert actual is run
                context.require_current()
                calls.append('effect')

            def pending(actual, roles):
                assert actual is run and roles == ('recorder',)
                calls.append('pending')
                return 'recorder'

            def final(actual):
                assert actual is run
                calls.append('final')
                return {}

            def record_identity(actual, spec_argument, actual_record):
                assert actual is run and spec_argument is None and actual_record is record
                calls.append('record')
                return actual

            patch.setattr(capture, '_load_live', load)
            patch.setattr(capture, '_require_run_effect', effect)
            patch.setattr(capture, '_pending_receipt_or_recorder', pending)
            patch.setattr(capture, '_current_provenance_block', final)
            patch.setattr(capture, '_record_matches_run', record_identity)
            with entered_case(case) as context:
                assert type(context) is coordination._OwnerReaderContext
                # Neither policy construction nor the supplied absolute target
                # may silently switch to this later ambient directory.
                patch.chdir(ambient_cwd)
                assert str(Path.cwd()) != run.binding.working_directory
                yield {'run': run, 'context': context, 'record': record, 'calls': calls,
                    'destination': destination, 'declared': declared, 'captured_cwd': captured_cwd,
                    'ambient_cwd': ambient_cwd}

    return opened


def guard(case, path):
    case['calls'].clear()
    capture.require_recorder_write(path, owner_context=case['context'], record=case['record'])


def test_bound_relative_and_absolute_recorder_destinations_use_captured_cwd(destination_case, monkeypatch):
    for layout in ('relative', 'absolute'):
        with destination_case(layout) as case:
            destination = case['destination']
            assert not destination.exists() and not destination.is_symlink()
            guard(case, destination)
            assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record', 'effect']
            # The guard admits only an address; it creates no output itself.
            assert not destination.exists() and not destination.is_symlink()
            if layout == 'relative':
                wrong = case['ambient_cwd'] / case['declared']
                with pytest.raises(ValueError, match='exact physical destination'):
                    guard(case, wrong)
                assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record']
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b'existing recorder bytes\n')
            try:
                guard(case, destination)
                assert destination.read_bytes() == b'existing recorder bytes\n'
                primary = RuntimeError('final selected effect refusal')
                prior_effect = capture._require_run_effect
                def refused_after_address(actual):
                    prior_effect(actual)
                    if case['calls'].count('effect') == 2:
                        raise primary
                with monkeypatch.context() as patch:
                    patch.setattr(capture, '_require_run_effect', refused_after_address)
                    with pytest.raises(RuntimeError) as caught:
                        guard(case, destination)
                    assert caught.value is primary
                assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record', 'effect']
                assert destination.read_bytes() == b'existing recorder bytes\n'
            finally:
                destination.unlink()


def test_recorder_raw_aliases_and_foreign_absolute_destinations_refuse(destination_case):
    with destination_case() as case:
        target = str(case['destination'])
        parent, leaf = target.rsplit('/', 1)
        for supplied in (parent + '/../' + leaf, parent + '/./' + leaf,
                         parent + '//' + leaf, str(case['ambient_cwd'] / leaf),
                         case['declared']):
            with pytest.raises(ValueError):
                guard(case, supplied)
            assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record']
        declaration = case['run'].composition['policy']['post_final_recorder']
        original = declaration['destination']
        for malformed in ('../' + original, './' + original, original.replace('/', '//', 1),
                          str(case['ambient_cwd'] / leaf), '', None):
            declaration['destination'] = malformed
            with pytest.raises(ValueError):
                guard(case, target)
            assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record']
        declaration['destination'] = original
        guard(case, target)
        assert case['calls'][-1] == 'effect'


def test_recorder_leaf_and_parent_symlinks_refuse_without_creating_output(destination_case):
    with destination_case() as case:
        target = case['destination']
        target.parent.mkdir(parents=True)
        other = target.with_name('other-record.yaml')
        other.write_bytes(b'component fixture only\n')
        target.symlink_to(other)
        try:
            with pytest.raises(ValueError, match='exact physical destination'):
                guard(case, target)
            assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record']
            assert other.read_bytes() == b'component fixture only\n'
        finally:
            target.unlink()
        saved_parent = target.parent.with_name(target.parent.name + '-actual')
        target.parent.rename(saved_parent)
        target.parent.symlink_to(saved_parent, target_is_directory=True)
        try:
            assert not target.exists() and not target.is_symlink()
            with pytest.raises(ValueError, match='exact physical destination'):
                guard(case, target)
            assert case['calls'] == ['load', 'effect', 'pending', 'final', 'record']
            assert not (saved_parent / target.name).exists()
        finally:
            target.parent.unlink()
            saved_parent.rename(target.parent)
        guard(case, target)
        assert case['calls'][-1] == 'effect' and not target.exists()
