"""Root-only, merge-bound five-input legacy CLI publication; disabled by default."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write('\n')


def inventory(root):
    """Ignored-inclusive files/directories/symlinks; exclude only root .git."""
    root = Path(root)
    rows = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        if Path(parent) == root and '.git' in dirs:
            dirs.remove('.git')
        for name in dirs + files:
            path = Path(parent) / name
            if path == root / '.git':
                continue
            info = path.lstat()
            row = {'mode': stat.S_IMODE(info.st_mode)}
            if stat.S_ISLNK(info.st_mode):
                row.update(kind='symlink', target=os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                raw = path.read_bytes()
                row.update(kind='file', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            elif stat.S_ISDIR(info.st_mode):
                row['kind'] = 'directory'
            else:
                raise ValueError('Unsupported source inventory entry: ' + str(path))
            rows[str(path.relative_to(root))] = row
    return rows


def git_state(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    return {'head': git('rev-parse', 'HEAD'), 'tree': git('rev-parse', 'HEAD^{tree}'),
            'tracked_changes': git('diff', '--name-only', 'HEAD').splitlines(),
            'untracked': git('ls-files', '--others', '--exclude-standard').splitlines()}


def group_present(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_group(process):
    actions = []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not group_present(process.pid):
            break
        try:
            os.killpg(process.pid, sig)
            actions.append(sig.name)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        deadline = time.monotonic() + 2
        while group_present(process.pid) and time.monotonic() < deadline:
            time.sleep(0.05)
    return {'signals': actions, 'owned_group_absent': not group_present(process.pid)}


def require_natural_success(run_error, execution, closure):
    """A successful CLI may not rely on coordinator signals to clear its group."""
    assert (run_error is None and execution['exit_code'] == 0
            and closure['owned_group_absent'] and not closure['signals']), execution


def admitted_configuration():
    template = json.loads((HERE / 'configuration.disabled.json').read_text())
    bound = json.loads((HERE / 'configuration.bound.disabled.json').read_text())
    active = json.loads((HERE / 'configuration.enabled.json').read_text())
    assert template['binding'] is None and template['enabled'] is False
    assert bound == dict(template, binding=bound['binding']) and bound['enabled'] is False
    assert active == dict(bound, enabled=True)
    binding = bound['binding']
    assert set(binding) == {'source', 'head', 'tree', 'source_inventory', 'merged_pr_snapshot',
                            'ci_evidence', 'plugin_review_evidence', 'root_readiness', 'python',
                            'reviewed_pr_head', 'reviewed_pr_tree', 'diagnostic_validation_evidence'}
    assert binding['ci_evidence'] and binding['plugin_review_evidence']
    assert active['reviewed_pr_head'] is None and active['reviewed_pr_tree'] is None
    for key in ('reviewed_pr_head', 'reviewed_pr_tree'):
        assert type(binding[key]) is str and len(binding[key]) == 40
        assert all(ch in '0123456789abcdef' for ch in binding[key])
    assert set(binding['diagnostic_validation_evidence']) == {'candidate313', 'candidate39'}
    for row in active['pins'] + [binding['source_inventory'], binding['merged_pr_snapshot'],
            binding['root_readiness'], binding['python'], *binding['ci_evidence'],
            *binding['plugin_review_evidence'], *binding['diagnostic_validation_evidence'].values()]:
        assert pin(row['path']) == row, row['path']
    pr = json.loads(Path(binding['merged_pr_snapshot']['path']).read_text())
    assert pr['number'] == 4938 and pr['merged'] is True and pr['merged_at']
    assert pr['base']['repo']['full_name'] == 'bridge2ai/data-sheets-schema'
    assert pr['head']['sha'] == binding['reviewed_pr_head']
    assert pr['merge_commit_sha'] == binding['head']
    validation = json.loads(Path(active['diagnostic_validation_configuration']['path']).read_text())
    assert pin(validation['baseline_confirmation']['path']) == validation['baseline_confirmation']
    confirmation = json.loads(Path(validation['baseline_confirmation']['path']).read_text())
    assert confirmation == validation['baseline_confirmation_expected']
    assert confirmation['saved_semantic_failures_confirmed'] is True
    assert confirmation['original_wrapper_passed'] is False and confirmation['application_acceptance'] is False
    original = json.loads(Path(confirmation['original_execution']['path']).read_text())
    assert pin(confirmation['original_execution']['path']) == confirmation['original_execution']
    assert original['passed'] is False and original['expected_failure_confirmed'] is False
    assert original['application_test_acceptance'] is False and original['exit_code'] == 1
    assert original['junit'] == {'cases': 3, 'failures': 3, 'errors': 0, 'skipped': 0}
    assert original['error'] == {'type': 'AssertionError', 'message': 'Expected diagnostic assertion failures were not observed'}
    for name, receipt_pin in binding['diagnostic_validation_evidence'].items():
        result = json.loads(Path(receipt_pin['path']).read_text())
        slot = validation['slots'][name]
        assert result['phase'] == name and result['passed'] is True and result['error'] is None
        assert result['head'] == validation['head'] and result['tree_after'] == validation['base_tree']
        assert result['preserved'] is True and result['git_state_preserved'] is True
        assert not result['pin_changes'] and not result['changed_entries']
        assert result['candidate_pins'] == slot['candidate_pins']
        assert result['expected_nodeids'] == slot['expected_nodeids']
        assert result['junit'] == {'cases': slot['expected_cases'], 'failures': 0, 'errors': 0, 'skipped': 0}
        assert result['exit_code'] == 0 and result['application_test_acceptance'] is True
        assert result['expected_failure_confirmed'] is False
        assert result['baseline_confirmation'] == validation['baseline_confirmation']
        if name == 'candidate39':
            assert result['same_ordered_nodes_as313'] is True
    ready = json.loads(Path(binding['root_readiness']['path']).read_text())
    assert ready == {'format': 'legacy4594_root_readiness_v1',
        'reviewed_pr_head': binding['reviewed_pr_head'], 'reviewed_pr_tree': binding['reviewed_pr_tree'],
        'diagnostic_validation_evidence': binding['diagnostic_validation_evidence'], 'merged_head': binding['head'],
        'merged_tree': binding['tree'], 'required_ci_accepted': True,
        'actual_plugin_review_accepted': True, 'ci_evidence': binding['ci_evidence'],
        'plugin_review_evidence': binding['plugin_review_evidence'],
        'publication_package_approved': True}
    controls = json.loads(Path(active['serialization_controls_receipt']).read_text())
    assert controls['passed'] is True and controls['error'] is None
    assert controls['configuration'] == pin(HERE / 'configuration.disabled.json')
    assert controls['cases'] == active['serialization_control_cases']
    assert controls['version'] == active['python_version']
    assert controls['executable_realpath'] == os.path.realpath(binding['python']['path'])
    assert controls['source_records_only'] is True and controls['published_outputs_read'] is False
    assert controls['project_imports'] is False
    assert controls['preserved'] is True
    for row in controls['watched_pins'] + controls['yaml_pins']:
        assert pin(row['path']) == row, row['path']
    assert [row['form'] for row in controls['saved_oracles']] == [row['form'] for row in active['inputs']]
    return active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        raise SystemExit('Disabled: root must bind the actual merge and supply --run')
    config = admitted_configuration()
    binding = config['binding']
    source = Path(binding['source']).resolve()
    assert str(source) == binding['source']
    output = Path(config['output'])
    assert not output.is_relative_to(source) and not source.is_relative_to(output)
    assert not os.path.lexists(output)
    start_git = git_state(source)
    assert start_git == {'head': binding['head'], 'tree': binding['tree'],
                         'tracked_changes': [], 'untracked': []}
    source_pins = []
    for row in config['source_files']:
        actual = pin(source / row['relative'])
        assert (actual['bytes'], actual['sha256']) == (row['bytes'], row['sha256']), row['relative']
        source_pins.append(actual)
    before = inventory(source)
    assert before == json.loads(Path(binding['source_inventory']['path']).read_text())
    external_pins = [*config['pins'], binding['source_inventory'], binding['merged_pr_snapshot'],
        binding['root_readiness'], binding['python'], *binding['ci_evidence'],
        *binding['plugin_review_evidence'], *binding['diagnostic_validation_evidence'].values(),
        pin(HERE / 'configuration.bound.disabled.json'),
        pin(HERE / 'configuration.enabled.json'), pin(config['serialization_controls_receipt'])]
    output.mkdir(parents=True)
    (output / 'inputs').mkdir()
    (output / 'receipts').mkdir()
    write(output / 'source-before.json', before)
    error = None
    receipts = []
    staged = []
    process = None
    overall_start = time.monotonic()
    try:
        for item in config['inputs']:
            raw = Path(item['raw_input_pin']['path']).read_bytes()
            assert pin(item['raw_input_pin']['path']) == item['raw_input_pin']
            path = output / 'inputs' / (item['form'] + '.json')
            with path.open('xb') as stream:
                stream.write(raw)
            copied = pin(path)
            assert (copied['bytes'], copied['sha256']) == (item['raw_input_pin']['bytes'], item['raw_input_pin']['sha256'])
            staged.append({'form': item['form'], 'original': item['raw_input_pin'], 'staged': copied})
        write(output / 'input-acquisition.json', staged)
        for item in config['inputs']:
            form = item['form']
            command = [binding['python']['path'], '-I', '-B', str(HERE / 'worker.py'), form]
            env = dict(os.environ)
            for key in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONPYCACHEPREFIX', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
                env.pop(key, None)
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            launched = time.monotonic()
            run_error = None
            closure = None
            with (output / 'receipts' / (form + '.stdout.log')).open('xb') as stdout, \
                    (output / 'receipts' / (form + '.stderr.log')).open('xb') as stderr:
                process = subprocess.Popen(command, cwd=source, env=env, stdout=stdout,
                                           stderr=stderr, start_new_session=True)
                try:
                    process.wait(timeout=config['per_input_timeout_seconds'])
                except BaseException as exc:
                    run_error = {'type': type(exc).__name__, 'message': str(exc)}
                finally:
                    closure = stop_group(process)
                execution = {'form': form, 'argv': command, 'cwd': str(source), 'pid': process.pid,
                    'exit_code': process.returncode, 'elapsed_seconds': time.monotonic() - launched,
                    'error': run_error, 'closure': closure,
                    'environment_updates': {'PYTHONDONTWRITEBYTECODE': '1'},
                    'environment_removals': ['PYTHONHOME', 'PYTHONPATH', 'PYTHONPYCACHEPREFIX', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS']}
            write(output / 'receipts' / (form + '.execution.json'), execution)
            process = None
            receipts.append(execution)
            require_natural_success(run_error, execution, closure)
            result = json.loads((output / 'receipts' / (form + '.worker.json')).read_text())
            assert result['passed'] is True and result['cli_exit_code'] == 0 and not result['origin_findings']
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        cleanup = None
        if process is not None:
            try:
                cleanup = stop_group(process)
            except BaseException as exc:
                cleanup = {'error': {'type': type(exc).__name__, 'message': str(exc)}}
        preservation_errors = []
        after = None
        end_git = None
        changed = []
        try:
            after = inventory(source)
            write(output / 'source-after.json', after)
            changed = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
            end_git = git_state(source)
        except BaseException as exc:
            preservation_errors.append({'type': type(exc).__name__, 'message': str(exc)})
        pin_changes = []
        for row in external_pins + source_pins + [r['staged'] for r in staged]:
            try:
                assert pin(row['path']) == row
            except BaseException as exc:
                pin_changes.append({'path': row['path'], 'error': type(exc).__name__})
        preservation = {'source_entries': len(before), 'source_equal': after == before,
            'changed_entries': changed, 'git_before': start_git, 'git_after': end_git,
            'git_equal': start_git == end_git, 'pin_changes': pin_changes,
            'preservation_errors': preservation_errors, 'late_cleanup': cleanup}
        write(output / 'preservation.json', preservation)
        passed = (error is None and len(receipts) == 5 and after == before and start_git == end_git
                  and not pin_changes and not preservation_errors and cleanup is None)
        manifest = {'format': 'legacy4594_actual_cli_publication_release_v1', 'passed': passed,
            'label': config['label'], 'method': 'legacy_semantic_tsv',
            'policy': 'root_default_route_dispositions_v1', 'producer': binding,
            'source_files': source_pins, 'inputs': staged, 'actual_executions': receipts,
            'error': error, 'elapsed_seconds': time.monotonic() - overall_start,
            'prior_evidence': config['prior_evidence'], 'preservation': pin(output / 'preservation.json'),
            'limitations': config['limitations'], 'artifacts': [pin(p) for p in sorted(output.rglob('*')) if p.is_file()]}
        write(output / ('completed.json' if passed else 'failure.json'), manifest)
        print(json.dumps({'passed': passed, 'actual_cli_attempts': len(receipts), 'error': error,
                          'source_preserved': after == before, 'pin_changes': pin_changes}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
