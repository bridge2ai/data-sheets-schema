"""Literal historical text boundaries and explicit candidate authority."""
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import historical_digest as history
from data_sheets_schema import profile_identity, run_schema, schema_digest


SCHEMA = b'''id: https://example.org/historical-test
name: historical_test
prefixes:
  ex: https://example.org/
default_prefix: ex
default_range: string
classes:
  Dataset:
    attributes:
      choice:
        range: Choice
        required: true
      detail:
        range: Detail
  Detail:
    attributes:
      id:
        range: uriorcurie
        identifier: true
        required: true
      choice:
        range: Choice
      count:
        range: integer
      labels:
        range: string
        multivalued: true
      topic:
        range: string
        values_from: [TOPIC]
enums:
  Choice:
    permissible_values:
      a: {}
      b: {}
'''
VOCABULARY = b'vocabularies:\n  TOPIC:\n    TOPIC:2: Second\n    TOPIC:1: First\n'
PATH = '/captured/data_sheets_schema_all.yaml'

# These are literal reviewable historical strings, not the result of importing
# an old renderer or generating a golden file from the implementation.
HEADER = '''# Target class `Dataset` — slot inventory

Derived from `/captured/data_sheets_schema_all.yaml`. Structure only: this states what shape a record takes, never what any dataset contains.

2 slots. `[req]` must be populated; `[many]` takes a list. A slot with an enum range accepts only the listed values.

## `choice` — *Choice* [req]
Permitted: `a`, `b`

## `detail` — *Detail*

# Object ranges — required keys

A slot whose range is one of these takes an object (or list of objects). Any listed **required** key must be present on every such object, or the record fails validation.

'''
UNIVERSAL = 'On every object below: `id` is `uriorcurie`; `used_software` is `Software[]`. A value of the wrong kind for its declared range is a defect even when it reads well.\n\n'
REQUIRED = '- **Detail** — required: `id`\n'
OPTIONAL = '    - also accepts: `choice`, `count`, `labels`, `topic`\n'
ENUM = '    - `choice` accepts only: `a`, `b`\n'
RANGE = '    - ranges: `count`: integer\n'
TERMS = '    - `topic` draws from TOPIC (use `TOPIC:<id>`) — 2=Second, 1=First. If no term fits, omit the slot rather than approximate, and never restate the subject as prose here.\n'
GOLDEN = {
    'required_enum40': HEADER + REQUIRED,
    'nested_enum60': HEADER + REQUIRED + ENUM,
    'optional_keys': HEADER + REQUIRED + OPTIONAL + ENUM,
    'ranges_vocabulary': HEADER + UNIVERSAL + REQUIRED + OPTIONAL + RANGE + ENUM + TERMS,
    'canonical_paths': (HEADER + UNIVERSAL + REQUIRED + OPTIONAL + RANGE + ENUM + TERMS).replace(
        '/captured/data_sheets_schema_all.yaml', history.FULL_SCHEMA_PATH),
    'inline_depth2': (HEADER + UNIVERSAL + REQUIRED + OPTIONAL + RANGE + ENUM + TERMS).replace(
        '/captured/data_sheets_schema_all.yaml', history.FULL_SCHEMA_PATH),
}


@pytest.mark.parametrize('family', tuple(GOLDEN))
def test_six_literal_golden_texts(family):
    vocabulary = VOCABULARY if history.POLICIES[family].vocabulary else None
    text = history.render_captured(SCHEMA, PATH, family, vocabulary_bytes=vocabulary)
    assert text == GOLDEN[family]
    assert 'labels`: string[]' not in text


def test_enum_limit_and_nested_enum_boundary():
    raw = SCHEMA.replace(b'      a: {}\n      b: {}',
                         '\n'.join(f'      v{i:02}: {{}}' for i in range(41)).encode())
    early = history.render_captured(raw, PATH, 'required_enum40')
    later = history.render_captured(raw, PATH, 'nested_enum60')
    assert '`v39` (+1 more)' in early and '`v40`' not in early
    assert '`choice` accepts only:' not in early
    assert '`v39`, `v40`' in later and '(+1 more)' not in later
    assert '`choice` accepts only:' in later


def test_description_whitespace_and_exact_ellipsis_boundary():
    raw = SCHEMA.replace(b'      choice:\n',
                         b'      choice:\n        description: "one  two\\nthree"\n', 1)
    assert '\none two three\n' in history.render_captured(raw, PATH, 'required_enum40')
    raw = SCHEMA.replace(b'      choice:\n',
                         b'      choice:\n        description: "' + b'x' * 301 + b'"\n', 1)
    text = history.render_captured(raw, PATH, 'required_enum40')
    assert '\n' + 'x' * 299 + '…\n' in text
    assert 'x' * 300 not in text


def test_old_small_class_mirror_rule_and_initial_reference_frontier():
    raw = b'''id: https://example.org/mirror
name: mirror
default_range: string
classes:
  Dataset:
    attributes:
      child: {range: Child}
      title: {range: string}
  Child:
    attributes:
      id: {identifier: true, required: true}
      title: {range: string}
'''
    old = history.render_captured(raw, PATH, 'optional_keys')
    new = history.render_captured(raw, PATH, 'inline_depth2', vocabulary_bytes=VOCABULARY)
    assert '- **Child** — required: `id`\n' in new  # top-level reference still visited
    assert 'also accepts the same slots as the top-level listing above' in old
    assert '    - also accepts: `title`\n' in new
    assert 'also accepts the same slots as the top-level listing above' not in new


def test_second_level_inline_reference_and_universal_edges():
    raw = b'''id: https://example.org/edges
name: edges
default_range: string
classes:
  Dataset:
    attributes:
      child: {range: Child}
  Child:
    attributes:
      inline: {range: Inline}
      reference: {range: Reference}
      used_software: {range: Universal, inlined: true}
  Inline:
    attributes:
      number: {range: integer, required: true}
  Reference:
    attributes:
      id: {identifier: true, required: true}
  Universal:
    attributes:
      key: {required: true}
'''
    old = history.render_captured(raw, PATH, 'canonical_paths', vocabulary_bytes=VOCABULARY)
    new = history.render_captured(raw, PATH, 'inline_depth2', vocabulary_bytes=VOCABULARY)
    assert '- **Inline** — required: `number`\n' in new and '- **Inline**' not in old
    assert '`reference`: Reference (reference — a string, not an object)' in new
    assert '- **Reference**' not in new and '- **Universal**' not in new


@pytest.mark.parametrize('raw', [None, b'vocabularies: false\n', b'vocabularies: []\n',
                                b'vocabularies:\n  TOPIC: false\n'])
def test_explicit_vocabulary_is_required_and_validated(raw):
    with pytest.raises(ValueError):
        history.render_captured(SCHEMA, PATH, 'canonical_paths', vocabulary_bytes=raw)


def test_pre_vocabulary_family_refuses_a_supplied_pin():
    with pytest.raises(ValueError, match='did not use'):
        history.render_captured(SCHEMA, PATH, 'required_enum40', vocabulary_bytes=VOCABULARY)


@pytest.mark.parametrize('imports', [b'[linkml:types]', b'[current-file]'])
def test_imported_history_is_not_completed_from_installed_or_current_bytes(imports):
    with pytest.raises(ValueError, match='import-free'):
        history.render_captured(SCHEMA + b'imports: ' + imports + b'\n', PATH, 'required_enum40')


def test_runtime_boundary_is_explicit(monkeypatch):
    monkeypatch.setattr(history, 'version', lambda _: 'different')
    with pytest.raises(ValueError, match='linkml-runtime'):
        history.render_captured(SCHEMA, PATH, 'required_enum40')


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    root = tmp_path / 'git'
    root.mkdir()
    source = b"raise AssertionError('historical code must never execute')\n"
    for name, raw in ((history.RENDERER_PATH, source), (history.VOCABULARY_PATH, VOCABULARY)):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()
    git('init', '-q')
    git('add', '.')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org', 'commit', '-qm', 'fixture')
    commit = git('rev-parse', 'HEAD')
    monkeypatch.setattr(history, 'SOURCE_FAMILIES', {hashlib.sha256(source).hexdigest(): 'ranges_vocabulary'})
    monkeypatch.setattr(history, 'VOCABULARY_SHA256', hashlib.sha256(VOCABULARY).hexdigest())
    record = {'schema': {'full_path': PATH, 'full_sha256': hashlib.sha256(SCHEMA).hexdigest(),
                         'full_md5': hashlib.md5(SCHEMA).hexdigest(),
                         'digest_md5': hashlib.md5(GOLDEN['ranges_vocabulary'].encode()).hexdigest()},
              'repo': {'commit': commit, 'dirty': True}, 'software': {'linkml_runtime': '1.9.4'}}
    return root, record


def test_verified_candidate_text_agreement_does_not_attest_original_inputs(candidate):
    root, record = candidate
    before = deepcopy(record)
    result = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    assert result['status'] == 'reproduced'
    assert result['text_sha256'] == hashlib.sha256(GOLDEN['ranges_vocabulary'].encode()).hexdigest()
    assert result['consumed_implementation_identity'] == result['historical_profile_identity'] == 'unrecorded'
    assert result['recorded_repo_dirty'] is True and record == before
    assert result['candidate']['commit'] == record['repo']['commit']
    # Current checkout files cannot replace the exact committed candidate.
    (root / history.RENDERER_PATH).write_text('different current code')
    (root / history.VOCABULARY_PATH).write_text('vocabularies: false')
    assert history.reconstruct(record, SCHEMA, PATH, git_root=root) == result


@pytest.mark.parametrize('change', ['digest', 'first_hash', 'second_hash', 'path', 'commit',
                                  'runtime', 'unknown_source', 'vocabulary_pin'])
def test_missing_or_conflicting_inputs_do_not_guess(candidate, monkeypatch, change):
    root, record = candidate
    if change == 'digest':
        record['schema']['digest_md5'] = '0' * 32
    elif change == 'first_hash':
        record['schema']['full_sha256'] = '0' * 64
    elif change == 'second_hash':
        record['schema']['full_md5'] = '0' * 32
    elif change == 'path':
        record['schema']['full_path'] = 'different'
    elif change == 'commit':
        record['repo']['commit'] = '1' * 40
    elif change == 'runtime':
        record['software']['linkml_runtime'] = 'unknown'
    elif change == 'unknown_source':
        monkeypatch.setattr(history, 'SOURCE_FAMILIES', {})
    else:
        monkeypatch.setattr(history, 'VOCABULARY_SHA256', '0' * 64)
    result = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    assert result['status'] == ('not_reproduced' if change == 'digest' else 'unavailable')
    assert result['consumed_implementation_identity'] == 'unrecorded'


def test_absent_digest_is_not_manufactured(candidate, monkeypatch):
    root, record = candidate
    del record['schema']['digest_md5']
    monkeypatch.setattr(history, '_git_blob', lambda *a: pytest.fail('no target digest'))
    result = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    assert result['status'] == 'no_recorded_digest' and result['text_sha256'] is None


def test_candidate_lookup_cannot_mutate_the_original_snapshot(candidate, monkeypatch):
    root, record = candidate
    original = history._git_blob

    def changing(commit, path, git_root):
        record['repo']['commit'] = '0' * 40
        record['schema']['digest_md5'] = '0' * 32
        record['software']['linkml_runtime'] = 'changed'
        return original(commit, path, git_root)

    expected_commit = record['repo']['commit']
    monkeypatch.setattr(history, '_git_blob', changing)
    result = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    assert result['status'] == 'reproduced' and result['candidate']['commit'] == expected_commit


def test_profile_unknown_stays_unknown_and_schema_is_recovered_once(candidate, monkeypatch, tmp_path):
    root, record = candidate
    path = tmp_path / 'old.yaml'
    path.write_bytes(SCHEMA)
    record['schema']['full_path'] = str(path)
    record['schema']['digest_md5'] = hashlib.md5(GOLDEN['ranges_vocabulary'].replace(PATH, str(path)).encode()).hexdigest()
    original_resolve, original_reconstruct = run_schema.run_schema_bytes, history.reconstruct
    calls = []

    def resolving(snapshot, **kwargs):
        calls.append(deepcopy(snapshot))
        return original_resolve(snapshot, **kwargs)

    monkeypatch.setattr(run_schema, 'run_schema_bytes', resolving)
    monkeypatch.setattr(history, 'reconstruct', lambda *a, **kw: original_reconstruct(*a, git_root=root, **kw))
    context = profile_identity.capture(record)
    assert len(calls) == 1
    assert context['status'] == 'unknown' and context['finding'] is None
    assert context['historical_digest_text']['status'] == 'reproduced'
    assert context['historical_digest_text']['historical_profile_identity'] == 'unrecorded'


def test_actual_git_replacement_and_ambient_repository_cannot_redirect_commit(candidate, monkeypatch, tmp_path):
    root, record = candidate
    commit = record['repo']['commit']
    original = history._git_blob(commit, history.RENDERER_PATH, root)
    (root / history.RENDERER_PATH).write_bytes(b'replacement renderer bytes\n')
    subprocess.check_call(['git', '-C', str(root), 'add', '.'])
    subprocess.check_call(['git', '-C', str(root), '-c', 'user.name=Fixture',
                           '-c', 'user.email=fixture@example.org', 'commit', '-qm', 'replacement'])
    replacement = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip()
    subprocess.check_call(['git', '-C', str(root), 'replace', commit, replacement])
    redirected = subprocess.check_output(['git', '-C', str(root), 'show', f'{commit}:{history.RENDERER_PATH}'])
    assert redirected != original[0]  # the real fixture exercises replacement
    monkeypatch.setenv('GIT_DIR', str(tmp_path / 'unrelated.git'))
    monkeypatch.setenv('GIT_NO_REPLACE_OBJECTS', '0')
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', 'core.bare')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', 'true')
    assert history._git_blob(commit, history.RENDERER_PATH, root) == original
    assert history.reconstruct(record, SCHEMA, PATH, git_root=root)['status'] == 'reproduced'


def _synthetic_git_child(monkeypatch, code):
    """Exercise real bounded pipes, without executing historical renderer code."""
    import sys
    actual = subprocess.Popen
    children = []
    environments = []

    def start(arguments, **kwargs):
        environments.append(kwargs['env'])
        child = actual([sys.executable, '-c', code], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(history.subprocess, 'Popen', start)
    return children, environments


def test_git_output_bound_and_no_network_child_environment(monkeypatch, tmp_path):
    children, environments = _synthetic_git_child(monkeypatch, 'import sys; sys.stdout.buffer.write(b"x" * 65)')
    with pytest.raises(ValueError, match='byte limit'):
        history._git_output(['synthetic'], tmp_path, 64)
    assert all(child.poll() is not None for child in children)
    assert environments[0]['GIT_NO_REPLACE_OBJECTS'] == '1'
    assert environments[0]['GIT_NO_LAZY_FETCH'] == '1'
    assert environments[0]['GIT_ALLOW_PROTOCOL'] == ''
    assert environments[0]['GIT_TERMINAL_PROMPT'] == '0'


def test_git_output_exact_boundary_is_accepted(monkeypatch, tmp_path):
    _synthetic_git_child(monkeypatch, 'import sys; sys.stdout.buffer.write(b"x" * 64)')
    assert history._git_output(['synthetic'], tmp_path, 64) == b'x' * 64


def test_git_deadline_reaps_the_child(monkeypatch, tmp_path):
    children, _ = _synthetic_git_child(monkeypatch, 'import time; time.sleep(30)')
    monkeypatch.setattr(history, '_GIT_SECONDS', .05)
    with pytest.raises(ValueError, match='time limit'):
        history._git_output(['synthetic'], tmp_path, 64)
    assert all(child.poll() is not None for child in children)


def test_git_missing_object_does_not_fall_back(candidate):
    root, _ = candidate
    with pytest.raises(ValueError, match='unavailable'):
        history._git_blob('0' * 40, history.RENDERER_PATH, root)


def test_git_blob_hash_is_still_verified(monkeypatch, tmp_path):
    replies = iter([b'1' * 40 + b'\n', b'different bytes'])
    monkeypatch.setattr(history, '_git_output', lambda *a: next(replies))
    with pytest.raises(ValueError, match='object identity'):
        history._git_blob('0' * 40, history.RENDERER_PATH, tmp_path)


def test_sixty_enum_limit_applies_to_top_and_nested_values():
    raw = SCHEMA.replace(b'      a: {}\n      b: {}',
                         '\n'.join(f'      v{i:02}: {{}}' for i in range(61)).encode())
    text = history.render_captured(raw, PATH, 'nested_enum60')
    assert text.count('`v59` (+1 more)') == 2
    assert '`v60`' not in text


@pytest.mark.parametrize('count', [24, 25])
def test_inline_mirror_shortcut_requires_more_than_twenty_four_optional_keys(count):
    top = '\n'.join(f'      a{i:02}: {{range: string}}' for i in range(count))
    raw = (f'id: https://example.org/optional-limit\nname: optional_limit\ndefault_range: string\n'
           f'classes:\n  Dataset:\n    attributes:\n      child: {{range: Child}}\n{top}\n'
           f'  Child:\n    attributes:\n{top}\n').encode()
    text = history.render_captured(raw, PATH, 'inline_depth2', vocabulary_bytes=VOCABULARY)
    assert ('also accepts the same slots as the top-level listing above' in text) is (count > 24)
    if count == 24:
        assert 'also accepts: `a00`, `a01`' in text and '`a23`\n' in text


def test_runs_check_reports_text_agreement_without_changing_profile_or_strict_result(monkeypatch):
    from click.testing import CliRunner
    from data_sheets_schema import provenance
    from data_sheets_schema.cli import runs as runs_cli
    root = Path(__file__).resolve().parents[1]
    label = '2026-07-31_claude-opus-5-api-generic_rep2'
    monkeypatch.chdir(root)
    context = {'status': 'unknown', 'reason': 'original historical profile remains unknown'}
    monkeypatch.setattr(provenance, 'profile_assessment', lambda record: ([], deepcopy(context)))
    arguments = ['check', '--strict', '--method', 'claudecode_agent_crate_only',
                 '--label', label, '--project', 'CHORUS']
    before = CliRunner().invoke(runs_cli.runs, arguments)
    context['historical_digest_text'] = {
        'status': 'reproduced', 'reason': 'candidate text agrees; consumed identity remains unrecorded'}
    after = CliRunner().invoke(runs_cli.runs, arguments)
    assert after.exit_code == before.exit_code
    assert 'historical profile identity is not established' in after.output
    assert 'historical digest-text reconstruction(s)' in after.output
    assert 'Candidate agreement does not attest the consumed implementation or profile' in after.output
    assert 'reproduced: candidate text agrees; consumed identity remains unrecorded' in after.output
    assert 'two instruments' not in after.output


@pytest.mark.parametrize('family', tuple(GOLDEN))
@pytest.mark.parametrize('logical_path, normalized', [
    ('./captured/custom.yaml', 'captured/custom.yaml'),
    ('captured//custom.yaml', 'captured/custom.yaml'),
    ('captured/./custom.yaml', 'captured/custom.yaml'),
    ('./captured/data_sheets_schema_all.yaml', 'captured/data_sheets_schema_all.yaml'),
    ('captured//data_sheets_schema_all.yaml', 'captured/data_sheets_schema_all.yaml'),
    ('captured/./data_sheets_schema_all.yaml', 'captured/data_sheets_schema_all.yaml'),
])
def test_original_path_display_and_later_canonical_basename(family, logical_path, normalized):
    vocabulary = VOCABULARY if history.POLICIES[family].vocabulary else None
    text = history.render_captured(SCHEMA, logical_path, family, vocabulary_bytes=vocabulary)
    shown = (history.FULL_SCHEMA_PATH if family in ('canonical_paths', 'inline_depth2') and
             normalized.endswith('/data_sheets_schema_all.yaml') else normalized)
    assert text.splitlines()[2] == (
        f'Derived from `{shown}`. Structure only: this states what shape a record takes, '
        'never what any dataset contains.')


def test_display_normalization_does_not_normalize_declared_authority(candidate):
    root, record = candidate
    record['schema']['full_path'] = './captured/custom.yaml'
    result = history.reconstruct(record, SCHEMA, 'captured/custom.yaml', git_root=root)
    assert result['status'] == 'unavailable'
    assert 'path/bytes do not match the declaration' in result['reason']
