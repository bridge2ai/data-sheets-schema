"""#4354 U1 scanner admission controls; offline source copies, 2026-11-06.

The complete v2 render route must derive; missing or altered consumers refuse.
"""
import ast

import pytest

from tests.test_generation_specificity_delegated import ROOT, RUNNER, fixture_root, scan, scopes


def test_native_dispatch_with_caller_docstring_derives_api_scopes():
    result = scopes(ROOT)
    assert result
    selected = scan._delegated_turn_selection(scan._tree(ROOT / RUNNER),
        ast.parse('spec.receipt_completion_version', mode='eval').body, ROOT)
    assert selected['runtime'] == 'api' and selected['cases']
    assert all(case['values']['native_shared_generation_version'] == 0
               for case in selected['cases'])
    assert any('native_shared_render.py:' in citation for citation in selected['evidence'])


@pytest.mark.parametrize('statement', ['pass', 'local = None', 'return None'])
def test_executable_validator_prefix_is_not_ignored(tmp_path, statement):
    root = fixture_root(tmp_path)
    path = root / 'src/data_sheets_schema/native_shared_render.py'
    source = path.read_text()
    marker = "    version = getattr(spec, 'native_shared_generation_version', 0)"
    assert source.count(marker) == 1
    path.write_text(source.replace(marker, '    ' + statement + '\n' + marker))
    with pytest.raises(scan.ConfigError, match='native selector does not reach'):
        scopes(root)


def _native_route_root(tmp_path):
    root = fixture_root(tmp_path)
    for relative in ('cli/prompt.py', 'native_execution_registration_v2.py',
                     'native_shared_controller.py'):
        path = root / 'src/data_sheets_schema' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / 'src/data_sheets_schema' / relative).read_bytes())
    for relative in scan._NATIVE_V2_RENDER_SOURCES | scan._NATIVE_V2_INTEGRATED_RENDER_SOURCES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    return root


def test_static_generation_import_does_not_hide_an_existing_native_launch(tmp_path):
    """U4b moves a real argv producer into the generation closure, not out of use."""
    entry = tmp_path / 'src/data_sheets_schema/cli/prompt.py'
    launch = tmp_path / 'src/data_sheets_schema/native_launch.py'
    runner = tmp_path / RUNNER
    entry.parent.mkdir(parents=True)
    entry.write_text('def render():\n    pass\n')
    runner.write_text('class RunSpec:\n    pass\n')
    launch.write_text('from .api_runner import RunSpec\n'
                      "FLAGS = ('--print', '--safe-mode')\n"
                      'def command():\n'
                      '    spec = RunSpec()\n'
                      "    return ['claude', *FLAGS, '--system-prompt', 'instruction']\n")
    relative = launch.relative_to(tmp_path).as_posix()

    def inventory():
        parsed = {path: (path.read_text(), ast.parse(path.read_text()))
                  for path in (entry, launch, runner)}
        closure = scan._package_closure(tmp_path, ['data_sheets_schema.cli.prompt'])
        excluded = frozenset(path.relative_to(tmp_path).as_posix() for path in closure)
        controllers, _, _ = scan.run_controllers(tmp_path, parsed, {}, excluded)
        sources = scan._registered_launch_sources(tmp_path, parsed, {}, controllers, closure)
        return controllers, scan.launch_flags(sources, parsed)

    before_controllers, before = inventory()
    assert relative in before_controllers
    assert len(before) == 1
    assert before[0]['site'].startswith(relative + ':')
    assert before[0]['carries'] is None and before[0]['memory_off'] is None
    assert any('`*FLAGS`' in line and 'are not followed' in line for line in before[0]['evidence'])
    entry.write_text('from data_sheets_schema import native_launch\n'
                     'def render():\n    pass\n')
    after_controllers, after = inventory()
    assert relative not in after_controllers  # The generation role remains distinct.
    assert after == before                  # The unchanged argv is still inventoried.


def test_generation_launch_inventory_retains_candidate_and_closure_boundaries(tmp_path):
    builder = ('from data_sheets_schema.api_runner import RunSpec\n'
               'def command():\n    spec = RunSpec()\n'
               "    return ['claude', '--safe-mode', '--system-prompt', 'instruction']\n")
    definitions = {
        'src/data_sheets_schema/native_launch.py': builder,
        'src/data_sheets_schema/unreached_launch.py': builder,
        'src/data_sheets_schema/native_probe.py': builder,
        'src/data_sheets_schema/evaluation/native_launch.py': builder,
        'src/data_sheets_schema/flags_only.py': "FLAGS = ['--system-prompt']\n",
        'src/data_sheets_schema/builder_only.py': 'from .api_runner import RunSpec\n',
    }
    parsed = {}
    for relative, source in definitions.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        parsed[path] = (source, ast.parse(source))
    closure = [path for path in parsed if path.name != 'unreached_launch.py']
    sources = scan._registered_launch_sources(tmp_path, parsed, {}, {}, closure)
    assert set(sources) == {'src/data_sheets_schema/native_launch.py'}
    rows = scan.launch_flags(sources, parsed)
    assert len(rows) == 1
    assert rows[0]['carries'] is True and rows[0]['memory_off'] is True


def test_api_meaning_refuses_missing_registered_launch_inventory(tmp_path):
    facts = {'conditions': {}, 'controllers': {}, 'legacy_scripts': []}
    with pytest.raises(scan.ConfigError, match='registered_launch_sources.*is missing'):
        scan.api_meaning(tmp_path, facts)


def test_generation_launch_inventory_distinguishes_api_execution_from_native_launch(tmp_path):
    runner = tmp_path / RUNNER
    runner.parent.mkdir(parents=True)
    runner.write_bytes((ROOT / RUNNER).read_bytes())
    api = tmp_path / 'src/data_sheets_schema/api_only_launch.py'
    api.write_text('from .api_runner import RunSpec, execute\n'
                   'def run(registration):\n'
                   "    spec = RunSpec(render_version=registration['renderer'])\n"
                   '    return execute(spec)\n')
    source = api.read_text()
    tree = ast.parse(source)
    parsed = {api: (source, tree)}
    relative = api.relative_to(tmp_path).as_posix()
    assert scan._builders_used(tree)
    assert scan._launch_evidence(tmp_path, api, tree, {}) == ['execute()']
    assert scan.launch_flags({relative: api}, parsed) == []
    assert scan._registered_launch_sources(tmp_path, parsed, {}, {}, [api]) == {}
    # Original controller membership is independent of the narrower additions.
    controllers = {relative: api}
    assert scan._registered_launch_sources(tmp_path, parsed, {}, controllers, [api]) == controllers


@pytest.mark.parametrize('replacement', [
    None,
    "spec.condition != 'generic_v10' or spec.render_version != 26",
    'spec.is_agentic',
    'False',
])
def test_generation_closure_keeps_native_continuation_and_its_actual_gate(tmp_path, replacement):
    """Importing a genuine continuation preserves its proof, including refusal failures."""
    relative = 'src/data_sheets_schema/native_shared_registration.py'
    continuation = tmp_path / relative
    entry = tmp_path / 'src/data_sheets_schema/cli/prompt.py'
    runner = tmp_path / RUNNER
    entry.parent.mkdir(parents=True)
    entry.write_text('def render():\n    pass\n')
    runner.write_text('class RunSpec:\n    pass\n')
    (tmp_path / scan.CLI_API).write_bytes((ROOT / scan.CLI_API).read_bytes())
    source = (ROOT / relative).read_text()
    original = "spec.condition != 'generic_v10' or spec.render_version != 26 or not spec.is_agentic"
    assert source.count(original) == 1
    if replacement is not None:
        source = source.replace(original, replacement, 1)
    continuation.write_text(source)
    runner_tree = scan._tree(ROOT / RUNNER)
    agentic = scan.condition_table(ROOT)['agentic_runtimes']

    def inventory():
        parsed = {path: (path.read_text(), ast.parse(path.read_text()))
                  for path in (entry, continuation, runner)}
        closure = scan._package_closure(tmp_path, ['data_sheets_schema.cli.prompt'])
        excluded = frozenset(path.relative_to(tmp_path).as_posix() for path in closure)
        controllers, _, _ = scan.run_controllers(tmp_path, parsed, {}, excluded)
        sources = scan._registered_launch_sources(tmp_path, parsed, {}, controllers, closure)
        proof = scan.audit_continuations(tmp_path, 20, sorted(sources), runner_tree, agentic)
        return controllers, proof

    before_controllers, before = inventory()
    assert relative in before_controllers
    entry.write_text('from data_sheets_schema import native_shared_registration\n'
                     'def render():\n    pass\n')
    after_controllers, after = inventory()
    assert relative not in after_controllers
    assert after == before
    assert [row['package'] for row in after['continuations']] == ['src/data_sheets_schema']
    if replacement is None:
        assert after['runtime_hybrid_possible'] is False
        assert after['ungated_continuations'] == after['uncovered'] == []
        assert {(row['path'], row['condition'], row['parent_renderer']) for row in after['gates']} == {
            (relative, 'generic_v10', 26)}
    else:
        assert after['runtime_hybrid_possible'] is True
        assert after['ungated_continuations'] == ['src/data_sheets_schema']
        assert after['gates'] == []


def test_native_complete_v2_route_derives():
    route = scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))
    assert route['cli'] == 'd4d prompt render-native-shared'
    assert route['enabled_values'] == [1]
    assert route['renderer'] == 26
    assert route['api_execute'] == 'refused before dry-run, locks or dispatch'
    assert route['model_calls_minimum'] is None
    assert route['runtime_binding']['path'] == 'src/data_sheets_schema/native_execution_registration_v2.py'
    assert any('native_execution_registration_v2.py:' in row for row in route['evidence'])
    assert 'separate acceptance gates' in route['runtime_binding']['basis']
    assert any(row.startswith('src/data_sheets_schema/cli/prompt.py:') for row in route['evidence'])


def test_native_route_requires_later_cli_consumer(tmp_path):
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema/cli/prompt.py'
    tree = ast.parse(path.read_text())
    tree.body = [n for n in tree.body if not isinstance(n, ast.FunctionDef)
                 or n.name != 'render_native_shared']
    path.write_text(ast.unparse(tree))
    with pytest.raises(scan.ConfigError, match='missing offline render CLI consumer'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('relative,before,after', [
    ('cli/prompt.py', 'preparation.prepare(selection, runtime_declaration,', 'preparation.prepare(runtime_declaration, selection,'),
    ('cli/prompt.py', "text = body['instruction']", "text = 'unrelated instruction'"),
    ('cli/prompt.py', "destination.open('x'", "destination.open('w'"),
    ('native_execution_registration_v2.py', '_require_registered_input_spellings(spec)', 'pass'),
    ('native_execution_registration_v2.py', 'native_shared_generation_version=1', 'native_shared_generation_version=0'),
    ('native_execution_registration_v2.py', 'registered_input_paths=True', 'registered_input_paths=False'),
    ('native_execution_registration_v2.py', ',\n        registered_input_paths=True', ''),
    ('native_execution_registration_v2.py', 'spec._native_shared_runtime_capture = runtime_capture', 'spec._native_shared_runtime_capture = None'),
    ('native_execution_registration_v2.py', 'instruction = spec.instruction', "instruction = 'unrelated instruction'"),
    ('native_execution_registration_v2.py', 'from . import native_shared_selection as selection', 'from . import native_shared_contract as selection'),
])
def test_native_v2_route_rejects_changed_producer(tmp_path, relative, before, after):
    root = _native_route_root(tmp_path)
    # Calibrate each mutation against the actual complete route.
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema' / relative
    source = path.read_text()
    assert before in source
    path.write_text(source.replace(before, after, 1))
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer|v2 producer import is not exact'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_native_v2_import_shadow_refuses_with_configuration_error(tmp_path):
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema/native_execution_registration_v2.py'
    path.write_text(path.read_text()+'\ndef changed_binding(c):\n    return c\n')
    with pytest.raises(scan.ConfigError, match='v2 preparation imported authority escapes fixed uses: c'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_native_v2_unused_import_shadow_reaches_binding_refusal(tmp_path):
    """An unused shadow passes the load-use proof and reaches the binding proof."""
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema/native_execution_registration_v2.py'
    # Unlike the sibling mutant, the parameter has no ast.Name/Load use for
    # closed_import_uses to reject. bound must independently reject ast.arg c.
    path.write_text(path.read_text()+'\ndef changed_binding(c):\n    return None\n')
    with pytest.raises(scan.ConfigError, match='v2 producer binding is replaced: c'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('relative,before,after,diagnostic', [
    ('src/data_sheets_schema/native_execution_registration_v2.py',
     "        value = controls['prepare_registration_v2'].envelope(body)",
     "        text = body['instruction'] + '\\nThis is the CHORUS dataset; use CHORUS naming.'\n"
     "        body = {**body, 'instruction': text, 'instruction_sha256': c.sha(text.encode('utf-8'))}\n"
     "        value = controls['prepare_registration_v2'].envelope(body)",
     'unsupported v2 render producer: _envelope'),
    ('src/data_sheets_schema/native_execution_registration_v2.py',
     'def _pin_map(captured, runtime, dependencies):',
     'def _pin_map(captured, runtime, dependencies):\n    dependencies = {}',
     'unsupported v2 render producer: _pin_map'),
    ('src/data_sheets_schema/native_execution_registration_v2.py',
     'def _job_id(value):', 'def _job_id(value):\n    return value',
     'unsupported v2 render producer: _job_id'),
    ('src/data_sheets_schema/native_execution_registration_v2.py',
     "        controls['prepare_registration_v2'].require_envelope(value)", '        pass',
     'unsupported v2 render producer: _envelope'),
    ('notes/matched_cborg_2026-09-13/prepare_registration_v2.py',
     '    return {"authority_version": 2, "controller_sources_sha256": SOURCES_SHA256,\n'
     '            "registration": registration}',
     '    registration = dict(registration)\n'
     '    registration["instruction"] = registration["instruction"] + "\\nThis is the CHORUS dataset; use CHORUS naming."\n'
     '    registration["instruction_sha256"] = hashlib.sha256(registration["instruction"].encode("utf-8")).hexdigest()\n'
     '    return {"authority_version": 2, "controller_sources_sha256": SOURCES_SHA256,\n'
     '            "registration": registration}',
     'v2 envelope authority source changed: notes/matched_cborg_2026-09-13/prepare_registration_v2.py'),
    ('notes/matched_cborg_2026-09-13/prepare_registration_v2.py',
     'def require_envelope(value):', 'def require_envelope(value):\n    return value["registration"]',
     'v2 envelope authority source changed: notes/matched_cborg_2026-09-13/prepare_registration_v2.py'),
    ('src/data_sheets_schema/native_execution_authority_v2.py',
     "        prepared = importlib.import_module('prepare_registration')",
     "        prepared = importlib.import_module('unknown_preparer')",
     'v2 envelope authority source changed: src/data_sheets_schema/native_execution_authority_v2.py'),
])
def test_native_v2_envelope_and_identity_producers_are_bound(tmp_path, relative, before, after, diagnostic):
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / relative
    source = path.read_text()
    assert source.count(before) == 1
    path.write_text(source.replace(before, after, 1))
    with pytest.raises(scan.ConfigError) as caught:
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    assert diagnostic in str(caught.value)


def test_native_non_v2_route_retains_configuration_refusal(tmp_path):
    root = _native_route_root(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema/cli/prompt.py'
    source = path.read_text()
    original = 'from data_sheets_schema import native_execution_registration_v2 as preparation'
    assert original in source
    path.write_text(source.replace(original,
        'from data_sheets_schema import unknown_preparation as preparation', 1))
    with pytest.raises(scan.ConfigError, match='unproved constructor, contract or runtime binding'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def _procedure_root(tmp_path):
    for relative in ('native_shared_stage/__init__.py', 'native_shared_receipts.py',
                     'typed_audit.py', 'audit_omissions.py', 'native_shared_render.py'):
        path = tmp_path / 'src/data_sheets_schema' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / 'src/data_sheets_schema' / relative).read_bytes())
    return tmp_path


def test_native_complete_response_roster_derives():
    result = scan.derive_native_shared_procedure(ROOT)
    assert result['protocol_responses']['formula'] == 'R + W + 2'
    assert result['model_calls_minimum'] is None
    assert [stage['kind'] for stage in result['stages']] == ['receipt', 'worker', 'omission', 'integration']


def _command_root(tmp_path):
    # Bounded discovery fixture uses the actual command table and entry point;
    # it does not stand in for a complete generation-route acceptance test.
    _native_route_root(tmp_path)  # Native-only attribution uses the genuine route proof.
    for relative in ('native_shared_render.py', 'native_shared_stage/__init__.py',
                     'native_shared_stage/__main__.py'):
        path = tmp_path / 'src/data_sheets_schema' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / 'src/data_sheets_schema' / relative).read_bytes())
    return tmp_path


def _command_discovery(root):
    surfaces = scan.Surfaces()
    surfaces.add('src/data_sheets_schema/native_shared_render.py', 'native_agentic',
                 'model_facing', 'live', 'actual shared-native command table', runs=False)
    facts = scan.discover_model_commands(root, {}, surfaces)
    return surfaces, facts


def test_native_model_command_discovers_main_and_imports(tmp_path):
    root = _command_root(tmp_path)
    entry = 'src/data_sheets_schema/native_shared_stage/__main__.py'
    surfaces, facts = _command_discovery(root)
    assert entry in surfaces.files and entry in facts
    assert 'native_agentic' in surfaces.files[entry].runs
    assert surfaces.files[entry].roles['native_agentic'] == 'model_facing'
    assert 'src/data_sheets_schema/native_shared_stage/__init__.py' in facts[entry]['imports']
    # F3c: model-readable stdout in the actual entry point must now gate.
    path = root / entry
    source = path.read_text()
    before = "    print(c.canonical(result).decode('utf-8'))"
    assert source.count(before) == 1
    path.write_text(source.replace(before,
        "    if 'CHORUS' in args.registration:\n"
        "        print('Note: this is the CHORUS dataset; prefer CHORUS naming.')\n" + before, 1))
    surfaces, _ = _command_discovery(root)
    hits = scan.scan_file(root, surfaces.files[entry], scan.load_tokens(ROOT))
    assert any(h['match'] == 'CHORUS' and h['model_facing'] and h['gates_in'] for h in hits)


def test_native_model_command_import_closure_and_other_package_are_discovered(tmp_path):
    root = _command_root(tmp_path)
    package = root / 'src/data_sheets_schema/second_command'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / '__main__.py').write_text("from . import helper\nprint(helper.result('selected'))\n")
    (package / 'helper.py').write_text("def result(project):\n    if project == 'CHORUS':\n        return 'cohort'\n")
    renderer = root / 'src/data_sheets_schema/native_shared_render.py'
    renderer.write_text(renderer.read_text() +
        "\nSECOND = {'second': ('python', '-m', 'data_sheets_schema.second_command')}\n")
    surfaces, facts = _command_discovery(root)
    entry = 'src/data_sheets_schema/second_command/__main__.py'
    helper = 'src/data_sheets_schema/second_command/helper.py'
    assert entry in facts and helper in facts[entry]['imports']
    hits = scan.scan_file(root, surfaces.files[helper], scan.load_tokens(ROOT))
    assert any(h['match'] == 'CHORUS' and h['code'] and h['gates_in'] for h in hits)


def test_native_model_package_command_without_main_refuses(tmp_path):
    root = _command_root(tmp_path)
    _command_discovery(root)  # Exact fixture calibrates before removing its entry point.
    (root / 'src/data_sheets_schema/native_shared_stage/__main__.py').unlink()
    with pytest.raises(scan.ConfigError, match='model-facing package command lacks __main__.py'):
        _command_discovery(root)


def test_native_starred_cli_table_discovers_entry_but_not_every_group(tmp_path):
    root = _command_root(tmp_path)
    cli = root / 'src/data_sheets_schema/cli'
    (cli / '__init__.py').write_text('from . import review, evaluate\n')
    (cli / '__main__.py').write_text('from . import cli\ncli()\n')
    (cli / 'review.py').write_text("PROJECT = 'CHORUS'\n")
    (cli / 'evaluate.py').write_text("PROJECT = 'VOICE'\n")
    surfaces = scan.Surfaces()
    renderer = 'src/data_sheets_schema/native_shared_render.py'
    for approach in ('native_agentic', 'api', 'deterministic', 'github_assistant'):
        surfaces.add(renderer, approach, 'model_facing', 'live', 'imported renderer', runs=False)
    surfaces.add('src/data_sheets_schema/cli/review.py', 'native_agentic', 'exposed', 'live', 'unselected group', runs=False)
    facts = scan.discover_model_commands(root, {}, surfaces)
    entry = 'src/data_sheets_schema/cli/__main__.py'
    assert facts[entry]['approaches'] == ['native_agentic']
    assert surfaces.files[entry].roles == {'native_agentic': 'model_facing'}
    assert 'src/data_sheets_schema/cli/__init__.py' in facts[entry]['imports']
    assert surfaces.files['src/data_sheets_schema/cli/review.py'].roles == {'native_agentic': 'exposed'}
    assert 'src/data_sheets_schema/cli/evaluate.py' not in surfaces.files


@pytest.mark.parametrize('table', [
    "[('python', '-m', 'data_sheets_schema.second_command')]",
    "(('python', '-m', 'data_sheets_schema.second_command'),)",
])
def test_model_nested_command_tables_preserve_approaches_without_runtime_argv_reseeding(tmp_path, table):
    root = tmp_path
    package = root / 'src/data_sheets_schema/second_command'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    (package / '__main__.py').write_text('from . import helper\n')
    # Runtime argv in an imported module must not recursively acquire command authority.
    (package / 'helper.py').write_text("ARGV = ('python', '-m', 'data_sheets_schema.third_command')\n")
    other = package.parent / 'third_command'
    other.mkdir()
    (other / '__init__.py').write_text('')
    (other / '__main__.py').write_text("print('not a model command')\n")
    source = package.parent / 'table_fixture.py'
    source.write_text('COMMANDS = ' + table + '\n'
                      "RUNTIME_ARGV = ('python', '-m', 'data_sheets_schema.third_command')\n")
    surfaces = scan.Surfaces()
    relative = source.relative_to(root).as_posix()
    surfaces.add(relative, 'native_agentic', 'model_facing', 'live', 'explicit table fixture', runs=False)
    surfaces.add(relative, 'api', 'run_shaping', 'live', 'import only', runs=False)
    facts = scan.discover_model_commands(root, {}, surfaces)
    entry = 'src/data_sheets_schema/second_command/__main__.py'
    assert facts[entry]['approaches'] == ['native_agentic']
    assert surfaces.files[entry].roles == {'native_agentic': 'model_facing'}
    assert 'src/data_sheets_schema/third_command/__main__.py' not in facts
    assert 'src/data_sheets_schema/third_command/__main__.py' not in surfaces.files


def test_model_package_imports_preserve_upstream_stop(tmp_path):
    root = _command_root(tmp_path)
    path = root / 'src/data_sheets_schema/native_shared_stage/__main__.py'
    path.write_text(path.read_text() + '\nfrom . import upstream_fixture\n')
    upstream = path.with_name('upstream_fixture.py')
    upstream.write_text("PROJECT = 'CHORUS'\n")
    surfaces = scan.Surfaces()
    surfaces.add('src/data_sheets_schema/native_shared_render.py', 'native_agentic',
                 'model_facing', 'live', 'actual native table', runs=False)
    facts = scan.discover_model_commands(root, {}, surfaces, stop={upstream.resolve()})
    relative = upstream.relative_to(root).as_posix()
    assert relative not in surfaces.files
    assert all(relative not in entry['imports'] for entry in facts.values())


@pytest.mark.parametrize('binding', [
    "args = ('python', '-m', 'data_sheets_schema.second_command')",
    "args: tuple = ('python', '-m', 'data_sheets_schema.second_command')",
    "prefix = ('python', '-m', 'data_sheets_schema.second_command')\nargs = prefix",
])
def test_model_named_table_direct_argv_alias_is_followed(tmp_path, binding):
    package = tmp_path / 'src/data_sheets_schema/second_command'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    (package / '__main__.py').write_text("print('a helper')\n")
    source = package.parent / 'table_fixture.py'
    source.write_text(binding + "\nCOMMANDS = {'advance': args}\n")
    surfaces = scan.Surfaces()
    surfaces.add(source.relative_to(tmp_path).as_posix(), 'native_agentic', 'model_facing',
                 'live', 'literal named table', runs=False)
    facts = scan.discover_model_commands(tmp_path, {}, surfaces)
    assert facts['src/data_sheets_schema/second_command/__main__.py']['approaches'] == ['native_agentic']


@pytest.mark.parametrize('bindings', [
    "args = ('python', '-m', 'data_sheets_schema.second_command')\n"
    "args = ('python', '-m', 'data_sheets_schema.third_command')\n",
    "first = ('python', '-m', 'data_sheets_schema.second_command')\n"
    "second = ('python', '-m', 'data_sheets_schema.third_command')\n"
    "args = first\nargs = second\n",
])
def test_model_named_table_ambiguous_argv_alias_refuses(tmp_path, bindings):
    source = tmp_path / 'src/data_sheets_schema/table_fixture.py'
    source.parent.mkdir(parents=True)
    source.write_text(bindings + "COMMANDS = {'advance': args}\n")
    surfaces = scan.Surfaces()
    surfaces.add(source.relative_to(tmp_path).as_posix(), 'native_agentic', 'model_facing',
                 'live', 'ambiguous named table', runs=False)
    with pytest.raises(scan.ConfigError, match='ambiguous argv alias: args'):
        scan.discover_model_commands(tmp_path, {}, surfaces)


@pytest.mark.parametrize('relative,before,after', [
    ('native_shared_stage/__init__.py', "roster += [('omission', 'omission'), ('integration', 'integration')]", "roster += [('integration', 'integration')]"),
    ('native_shared_stage/__init__.py', "'_catalog_lookup': catalog_reuse._CatalogLookup(self.catalogs, selection)", "'_catalog_lookup': None"),
    ('typed_audit.py', 'if captured_assets is None:\n        prepared = omissions.prepare', 'if captured_assets is not None:\n        prepared = omissions.prepare'),
    ('typed_audit.py', "if k not in (\"classes\", \"slots\")", "if k not in (\"classes\", \"slots\", \"terms\")"),
    ('audit_omissions.py', 'for key, value in chunks.items()]', "for key, value in chunks.items() if prior.get(key) != 'nothing_relevant']"),
    ('audit_omissions.py', 'owners=owners, chunks=chunks, prior=prior,', 'owners=owners, chunks={}, prior=prior,'),
])
def test_native_response_roster_refuses_changed_producer(tmp_path, relative, before, after):
    root = _procedure_root(tmp_path)
    assert scan.derive_native_shared_procedure(root)
    path = root / 'src/data_sheets_schema' / relative
    source = path.read_text()
    assert before in source
    path.write_text(source.replace(before, after, 1))
    with pytest.raises(scan.ConfigError, match='native shared response roster'):
        scan.derive_native_shared_procedure(root)


@pytest.mark.parametrize('mutation', [
    "self.options['_catalog_lookup'] = None",
    "self.options['captured_assets'] = None",
    "self.options.update(_catalog_lookup=None)",
    "self.options.pop('derivations')",
    "opts = self.options\n        opts['_catalog_lookup'] = None",
    "del self.options['_catalog_lookup']",
    "setattr(self, 'options', {})",
    "self.__dict__['options'] = {}",
    "getattr(self, 'options')['_catalog_lookup'] = None",
    "vars(self)['options']['_catalog_lookup'] = None",
    "opts = getattr(self, 'options')\n        opts['_catalog_lookup'] = None",
    "fields = vars(self)\n        fields['options']['_catalog_lookup'] = None",
])
def test_native_packet_options_refuse_mutation_and_alias_escape(tmp_path, mutation):
    root = _procedure_root(tmp_path)
    assert scan.derive_native_shared_procedure(root)
    path = root / 'src/data_sheets_schema/native_shared_stage/__init__.py'
    source = path.read_text()
    before = '        self.pending = None\n        self.pending_predecessor = None'
    assert source.count(before) == 1
    path.write_text(source.replace(before, '        ' + mutation + '\n' + before, 1))
    with pytest.raises(scan.ConfigError, match='native packet options are replaced, mutated or aliased'):
        scan.derive_native_shared_procedure(root)


@pytest.mark.parametrize('before,after', [
    ('key = raw, token', 'key = token'),
    ('return value, candidate', 'return {"project": "CHORUS"}, candidate'),
    ('retain_native(candidate, limit=limit)', 'pass'),
    ('events.clear()', "events.append('CHORUS')"),
    ('if not reusable or _token(limit) != token:', 'if not reusable:'),
    ('from . import audit_omissions as _omissions', 'from . import unknown as _omissions'),
    ('        events.clear()\n    return value, candidate',
     "        events.clear()\n    if isinstance(value, dict):\n        value = {**value, 'description': 'CHORUS cohort'}\n    return value, candidate"),
])
def test_native_event_parser_summary_is_bound_to_complete_source(tmp_path, before, after):
    # Exercise actual surface scanning, not a direct digest-helper assertion.
    # This also refuses a return changed to bypass text_flow's container edge.
    relative = 'src/data_sheets_schema/native_schema_event_reuse.py'
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    source = (ROOT / relative).read_text()
    path.write_text(source)

    surface = scan.Surface(relative, ['native_agentic'], 'model_facing', 'live', 'native parser dependency')
    tokens = scan.load_tokens(ROOT)
    assert isinstance(scan.scan_file(tmp_path, surface, tokens), list)
    assert before in source
    path.write_text(source.replace(before, after, 1))
    with pytest.raises(scan.ConfigError, match='parser transport source changed'):
        scan.scan_file(tmp_path, surface, tokens)


def test_native_route_cannot_omit_bc1_exclusion(tmp_path):
    root = fixture_root(tmp_path)
    path = root / 'src/data_sheets_schema/native_shared_render.py'
    source = path.read_text()
    marker = ",\n                'bounded_carry_version'):"
    assert source.count(marker) == 1
    path.write_text(source.replace(marker, "):", 1))
    with pytest.raises(scan.ConfigError, match='unsupported delegated admission prefix'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_only_leading_literal_docstring_is_ignored():
    body = ast.parse('"contract"\npass\n"not a docstring"').body
    result = scan._without_docstring(body)
    assert len(result) == 2 and isinstance(result[0], ast.Pass)
    assert result[1] is body[2]


@pytest.mark.parametrize('replacement', ['pass', '_require_registered_input_spellings(other)',
                                       '_require_registered_input_spellings(spec)\n    local = None'])
def test_phase_prefix_cannot_gain_unproved_work(tmp_path, replacement):
    root = fixture_root(tmp_path)
    path = root / RUNNER
    source = path.read_text()
    start = source.index('def build_phase(')
    before, after = source[:start], source[start:]
    after = after.replace('    _require_registered_input_spellings(spec)', '    ' + replacement, 1)
    path.write_text(before + after)
    with pytest.raises(scan.ConfigError, match='phase input invariant|prompt/phase route'):
        scan.derive_native_shared_route(root, scan._tree(path))
