"""Receipt orchestration boundaries; not a genuine admitted helper positive.

CLI tests explicitly spy the capture/assessment boundary to isolate option and
report ordering. The lower-reader test uses a real bound reader context, but
spies receipt assessment: it proves forwarding/failure behavior, not receipt
admission. Capture's independent tests cover the actual admission predicate.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from importlib import import_module
from types import SimpleNamespace

import click
from click.testing import CliRunner
import pytest

from data_sheets_schema import corpus
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema import receipts as receipts_api
receipt_cli = import_module('data_sheets_schema.cli.receipts')
from tests.test_native_owner_live_reader import (
    declaration, entered_case, fixed_clock, reader_case, selected_controls,
)


def _cli_inputs(tmp_path):
    selection = tmp_path / 'selection.json'
    bundle = tmp_path / 'bundle.md'
    chunks = tmp_path / 'chunks.json'
    for path in (selection, bundle, chunks):
        path.write_text('explicit boundary fixture', encoding='utf-8')
    return ['--method', 'fixture_method', '--label', 'fixture_label', '--project', 'FIXTURE',
            '--native-shared-selection', str(selection), '--bundle', str(bundle),
            '--chunk-manifest', str(chunks), '--strict']


def test_selected_cli_reports_strict_outcome_only_after_successful_cleanup(monkeypatch, tmp_path):
    # Deliberately an orchestration spy, not a substituted authorization proof.
    events = []
    owner = SimpleNamespace(require_current=lambda: events.append('current'))
    @contextmanager
    def scope(path):
        events.append('enter')
        yield owner
        events.append('cleanup')
    monkeypatch.setattr(capture, '_helper_owner_scope', scope)
    original_echo = click.echo
    def echo(message=None, *args, **kwargs):
        assert events[-1] == 'cleanup'
        events.append('printed')
        return original_echo(message, *args, **kwargs)
    monkeypatch.setattr(click, 'echo', echo)
    for outcome in (0, 1):
        events.clear()
        def assess(**kwargs):
            assert kwargs['owner_context'] is owner
            kwargs['_output'].append('explicit assessment findings')
            events.append('assessment')
            return outcome
        monkeypatch.setattr(receipt_cli, '_check_body', assess)
        result = CliRunner().invoke(receipt_cli.check, _cli_inputs(tmp_path))
        assert result.exit_code == outcome
        assert result.output == 'explicit assessment findings\n'
        assert events == ['enter', 'assessment', 'current', 'cleanup', 'printed']


def test_cleanup_and_assessment_errors_never_flush_selected_buffer(monkeypatch, tmp_path):
    for failed_at in ('cleanup', 'assessment'):
        failure = OSError('explicit ' + failed_at + ' refusal')
        owner = SimpleNamespace(require_current=lambda: None)
        @contextmanager
        def scope(path):
            yield owner
            if failed_at == 'cleanup':
                raise failure
        def assess(**kwargs):
            kwargs['_output'].append('must not be acknowledged')
            if failed_at == 'assessment':
                raise failure
            return 0
        monkeypatch.setattr(capture, '_helper_owner_scope', scope)
        monkeypatch.setattr(receipt_cli, '_check_body', assess)
        result = CliRunner().invoke(receipt_cli.check, _cli_inputs(tmp_path))
        assert result.exit_code != 0 and result.exception is failure
        assert result.output == ''


def test_selected_cli_options_use_exact_fixed_envelope(monkeypatch, tmp_path):
    paths = {key: tmp_path / key for key in ('full', 'receipt', 'provenance', 'core_dir')}
    expected = {'selection_path': str(tmp_path / 'selection.json'),
                'method': 'fixture_method', 'label': 'fixture_label', 'project': 'FIXTURE',
                'bundle': str(tmp_path / 'bundle.md'), 'chunk_manifest': str(tmp_path / 'chunks.json'),
                'manifest': str(tmp_path / 'manifest.yaml'), 'command': 'fixed boundary command',
                'paths': paths}
    calls = []
    owner = SimpleNamespace(require_current=lambda: calls.append('current'))
    def admitted(path, *, owner_context):
        assert owner_context is owner
        calls.append('admitted')
        return deepcopy(expected)
    monkeypatch.setattr(capture, 'require_receipt_invocation', admitted)
    monkeypatch.setattr(corpus, 'manifest_override', lambda: Path(expected['manifest']))
    args = dict(selection_path=Path(expected['selection_path']), owner_context=owner,
                method=expected['method'], label=expected['label'], project=expected['project'],
                write=False, strict=True, bundle_opt=expected['bundle'],
                chunk_manifest=Path(expected['chunk_manifest']),
                receipt_completion_registration=None, transcripts=(), receipt_at_run=None,
                full_at_run=None)
    assert receipt_cli._selected_receipt_options(**args) == paths
    for key, value in [('write', True), ('strict', False), ('strict', 1),
                       ('receipt_completion_registration', tmp_path / 'api.json'),
                       ('transcripts', (tmp_path / 'transcript.jsonl',)),
                       ('receipt_at_run', tmp_path / 'receipt'), ('full_at_run', tmp_path / 'full')]:
        changed = {**args, key: value}
        assert type(changed[key]) is not type(args[key]) or changed[key] != args[key]
        calls.clear()
        with pytest.raises(click.UsageError, match='read-only registered options'):
            receipt_cli._selected_receipt_options(**changed)
        assert calls == []
    for key in ('selection_path', 'method', 'label', 'project', 'bundle_opt', 'chunk_manifest'):
        changed = {**args, key: None}
        assert changed[key] != args[key]
        calls.clear()
        with pytest.raises(click.UsageError, match='differ from the admitted registered command'):
            receipt_cli._selected_receipt_options(**changed)
        assert calls == ['admitted']
    for manifest in (None, tmp_path / 'other.yaml', object()):
        monkeypatch.setattr(corpus, 'manifest_override', lambda: manifest)
        with pytest.raises(click.UsageError, match='differ from the admitted registered command'):
            receipt_cli._selected_receipt_options(**args)


def test_default_and_omitted_owner_profiles_keep_default_dispatch(monkeypatch, tmp_path):
    events = []
    def assess(**kwargs):
        assert 'owner_context' not in kwargs and '_output' not in kwargs
        events.append('body')
        click.echo('default output')
    monkeypatch.setattr(receipt_cli, '_check_body', assess)
    def forbidden_scope(path):
        raise AssertionError('non-native route must not enter helper scope')
    monkeypatch.setattr(capture, '_helper_owner_scope', forbidden_scope)
    result = CliRunner().invoke(receipt_cli.check, ['--label', 'x', '--project', 'X'])
    assert result.exit_code == 0 and result.output == 'default output\n'
    assert events == ['body']
    events.clear()
    @contextmanager
    def default_scope(path):
        events.append('enter-default')
        yield None
        events.append('exit-default')
    monkeypatch.setattr(capture, '_helper_owner_scope', default_scope)
    result = CliRunner().invoke(receipt_cli.check, _cli_inputs(tmp_path))
    assert result.exit_code == 0 and result.output == 'default output\n'
    assert events == ['enter-default', 'body', 'exit-default']


def test_ambient_selected_scope_cannot_downgrade_to_unchecked_receipt(monkeypatch, tmp_path):
    # The malformed ambient marker is a refusal control, never positive authority.
    def no_policy(**kwargs):
        raise AssertionError('ambient refusal must precede policy/fallback')
    monkeypatch.setattr(policy, 'select_policy', no_policy)
    token = profile._ACTIVE.set(object())
    try:
        with pytest.raises(ValueError):
            receipts_api.block_for(tmp_path / 'full', tmp_path / 'receipt', None, None, True)
    finally:
        profile._ACTIVE.reset(token)
    with pytest.raises(ValueError, match='exact owner reader context'):
        receipts_api.block_for(tmp_path / 'full', tmp_path / 'receipt', None, None, True,
                               owner_context=object())


def test_actual_reader_context_forwards_record_to_live_boundary_and_preserves_errors(reader_case, monkeypatch):
    # Real loader/budget/owner reader; assessment is an explicit boundary spy.
    # Its synthetic stream has no admitted receipt command, so no live success is claimed.
    declaration = policy.native_render_declaration(reader_case['selection'])
    record = {'prompts': {'request': {'spec': deepcopy(declaration)}}}
    spec = SimpleNamespace(render_spec=lambda: deepcopy(declaration))
    seen = []
    failure = None
    def live(path, **kwargs):
        seen.append((path, kwargs))
        if failure is not None:
            raise failure
        return {'checked': False, 'reason': 'explicit assessment boundary only'}
    def forbidden_saved(*args, **kwargs):
        raise AssertionError('record presence must not select saved reconstruction')
    monkeypatch.setattr(capture, 'live_receipt_block', live)
    monkeypatch.setattr(capture, 'recorded_receipt_block', forbidden_saved)
    full = reader_case['root'] / 'full.yaml'
    receipt = reader_case['root'] / 'receipt.yaml'
    with entered_case(reader_case) as context:
        for supplied_record in (None, record):
            result = receipts_api.block_for(full, receipt, None, None, True,
                receipt_render_spec=declaration, snapshot_spec=spec,
                snapshot_record=supplied_record, owner_context=context)
            assert result['checked'] is False and result['reason'] == 'explicit assessment boundary only'
            path, args = seen[-1]
            assert path == reader_case['selection'].registration.pin.path
            assert args['owner_context'] is context and args['snapshot_record'] is supplied_record
            assert args['snapshot_spec'] is spec and args['full_path'] == full and args['receipt_path'] == receipt
        for failure in (ValueError('live admission refused'), OSError('live owner read failed')):
            with pytest.raises(type(failure)) as raised:
                receipts_api.block_for(full, receipt, None, None, True,
                    receipt_render_spec=declaration, snapshot_record=record, owner_context=context)
            assert raised.value is failure
        failure = None
        changed = deepcopy(declaration)
        changed['native_shared_generation_registration']['sha256'] = '0' * 64
        assert changed != declaration
        with pytest.raises(ValueError):
            receipts_api.block_for(full, receipt, None, None, True,
                receipt_render_spec=changed, snapshot_record=record, owner_context=context)
    before = len(seen)
    with pytest.raises(ValueError):
        receipts_api.block_for(full, receipt, None, None, True,
            receipt_render_spec=declaration, snapshot_record=record, owner_context=context)
    assert len(seen) == before
