"""Exact installed LinkML and captured-byte completion boundaries."""
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, source_heading_completed as complete
from data_sheets_schema.schema_snapshot import capture_schema


@pytest.mark.parametrize("order", [("first", "second"), ("second", "first")])
def test_actual_linkml_cli_and_captured_validator_parity(tmp_path, order):
    from linkml.generators.jsonschemagen import JsonSchemaGenerator
    schema = tmp_path / 'schema.yaml'
    schema.write_text("""id: urn:synthetic:validation
name: validation
prefixes:
  linkml: https://w3id.org/linkml/
imports: [ORDER, linkml:types]
default_range: string
classes:
  Dataset:
    is_a: Base
    slots: [id, value]
slots:
  id:
    range: uriorcurie
    required: true
""".replace("ORDER", ", ".join(order)))
    (tmp_path/'first.yaml').write_text("""id: urn:synthetic:first
name: first
classes:
  Base:
    slots: [inherited]
slots:
  inherited:
    is_a: inherited_base
  inherited_base:
    range: string
  value:
    range: integer
""")
    (tmp_path/'second.yaml').write_text("""id: urn:synthetic:second
name: second
slots:
  value:
    range: string
""")
    snapshot = capture_schema(schema, strict=True)
    kw = dict(top_class='Dataset', not_closed=False, mergeimports=True, include_range_class_descendants=True)
    live_schema = json.loads(JsonSchemaGenerator(str(schema), **kw).serialize())
    captured_schema = complete._captured_json_schema(snapshot, cls="Dataset")
    assert captured_schema == live_schema
    samples = ['id: urn:sample\nvalue: 3\ninherited: inherited text\n', 'id: urn:sample\nunregistered: yes\n',
        '- id: urn:sample\n  value: wrong\n- id: urn:second\n---\nid: urn:third\nvalue: wrong\n',
        'id: urn:sample\nvalue: 1\nvalue: wrong\n', 'id: [broken\n']
    evidence = []
    for number, text in enumerate(samples):
        path = tmp_path / f'case-{number}.yaml'
        path.write_text(text)
        live = api._validator_lines(path, str(schema), 'Dataset')
        saved = complete._validator_lines(path.read_bytes(), path, snapshot, 'Dataset')
        # YAML parser traceback contains different stack frames, but both use
        # the same logical path/line/column and classify it as a record error.
        if number == 4:
            assert live[1] is saved[1] is None
            assert live[0] and saved[0]
            assert 'line 2, column 1' in str(live[0]) and 'line 2, column 1' in str(saved[0])
        else:
            assert saved == live
        evidence.append({'number':number,'live':live,'captured':saved})
    (tmp_path/'parity.json').write_text(json.dumps(evidence, indent=2))


@pytest.mark.parametrize('kind', ['form', 'grounding'])
def test_legacy_full_parse_error_precedes_unreadable_core(tmp_path, monkeypatch, kind):
    from data_sheets_schema import grounding
    full = tmp_path/'full.yaml'; full.write_text('name: [\n')
    core = tmp_path/'core.yaml'; core.mkdir()
    bundle = tmp_path/'bundle.txt'; bundle.write_text('synthetic bundle')
    reads = []
    read = Path.read_text
    def tracked(path, *a, **kw):
        reads.append(path)
        return read(path, *a, **kw)
    monkeypatch.setattr(Path, 'read_text', tracked)
    with pytest.raises(yaml.parser.ParserError):
        if kind == 'form':
            grounding.form_facts(full, core, slots=set())
        else:
            grounding.check_run(full, core, bundle, slots=set())
    assert core not in reads
    assert full in reads


def test_legacy_form_label_pass_keeps_second_ordered_read(tmp_path, monkeypatch):
    from data_sheets_schema import grounding
    full = tmp_path/'EXAMPLE_d4d.yaml'; full.write_text('name: Alternate\n')
    core = tmp_path/'core.yaml'; core.write_text('name: Alternate\n')
    reads = []
    read = Path.read_text
    def tracked(path, *a, **kw):
        if path in (full, core):
            reads.append(path)
        return read(path, *a, **kw)
    monkeypatch.setattr(Path, 'read_text', tracked)
    monkeypatch.setattr(grounding, 'declared_naming', lambda: {'EXAMPLE': {'canonical_label':'Canonical', 'variants':['Alternate']}})
    result = grounding.form_facts(full, core, slots=set())
    assert result['gc_label_variant_occurrences'] == 2
    assert reads == [full, core, full, core]


def test_legacy_multivalued_fallback_retains_already_yielded_names(monkeypatch):
    from types import SimpleNamespace
    from data_sheets_schema import schema_view
    class View:
        def __init__(self, full): self.full = full
        def all_classes(self): return ['Dataset']
        def class_induced_slots(self, _):
            yield SimpleNamespace(name='full_retained' if self.full else 'core_retained', multivalued=True, range='string')
            if self.full:
                raise ValueError('controlled late induced-slot failure')
    monkeypatch.setattr(schema_view, 'shared_view', lambda p: View(p == api.FULL_SCHEMA_PATH))
    monkeypatch.setattr(api, '_MULTIVALUED', None)
    assert api._multivalued_slots() == {'full_retained', 'core_retained'}


def test_actual_alias_displays_preserve_live_headers_and_manifest(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from copy import deepcopy
    from data_sheets_schema import chunking, derive_core, shared_generation as sg
    manifest = tmp_path/'data/preprocessed/source_manifest.yaml'
    manifest.parent.mkdir(parents=True)
    manifest.write_text('projects: {}\n')
    target = tmp_path/'data/preprocessed/concatenated/canonical.txt'
    target.parent.mkdir(); target.write_text('FILE: sample\nsource text\n')
    alias = tmp_path/'alias.txt'; alias.symlink_to(target)
    actual_full = tmp_path/'physical-full.yaml'; actual_full.write_text('id: urn:sample\n')
    full_alias = tmp_path/'full-alias.yaml'; full_alias.symlink_to(actual_full)
    spec = SimpleNamespace(bundle=alias, manifest=manifest, full_path=full_alias)
    display = complete._live_path_display(spec)
    assert display['bundle_name'] == 'canonical.txt' != alias.name
    assert display['core_source'] == str(actual_full)
    chunks = chunking.manifest_from_bytes(alias.read_bytes(), chunking.canonical_name(alias, source_manifest=manifest))
    chunk_path = tmp_path/'chunks.yaml'
    raw = chunking.dump_manifest(chunks).encode()
    reg = {'inputs': {'bundle': {'path': str(alias)}, 'source_manifest': {'path': str(manifest)},
                      'chunk_manifest': {'path': str(chunk_path)}}}
    reader = complete._Reader(((str(chunk_path), raw),))
    text = '# D4D Datasheet for sample\n# Source bundle: original alias\n# Schema: full.yaml\nid: urn:sample\n'
    expected = [derive_core.core_header(text, full_alias, phase) for phase in (False, True)]
    def denied(*a, **kw):
        raise AssertionError('captured display attempted original filesystem access')
    monkeypatch.setattr(Path, 'resolve', denied)
    monkeypatch.setattr(Path, 'read_bytes', denied)
    assert complete._check_path_display(display, {'full': str(full_alias)}, reg, reader) == display
    assert [derive_core._core_header(text, display['core_source'], phase) for phase in (False, True)] == expected
    for key in ('full_path', 'bundle_path', 'source_manifest', 'bundle_name'):
        changed = deepcopy(display); changed[key] = 'unrelated'
        with pytest.raises(ValueError):
            complete._check_path_display(changed, {'full': str(full_alias)}, reg, reader)
    # A core display is producer metadata, checked against the actual derived
    # original and final headers by whole replay, not inferred from basename.
    assert derive_core._core_header(text, 'unrelated', False) != expected[0]


@pytest.mark.parametrize('newline', [b'\n', b'\r\n', b'\r'])
def test_captured_form_newlines_match_actual_measurement_and_keep_raw_pins(tmp_path, monkeypatch, newline):
    import base64
    from types import SimpleNamespace
    from data_sheets_schema import grounding, shared_generation as sg
    from data_sheets_schema.run_schema import IdentifierRules
    default = tmp_path/'data/preprocessed/source_manifest.yaml'
    default.parent.mkdir(parents=True)
    default.write_text('naming:\n  EXAMPLE:\n    canonical_label: Modern\n    variants: [Old]\n')
    monkeypatch.chdir(tmp_path)
    full, core = tmp_path/'EXAMPLE_d4d.yaml', tmp_path/'EXAMPLE_core.yaml'
    raw = b'description: "Old' + newline + b'Name"' + newline
    full.write_bytes(raw); core.write_bytes(raw)
    rules = IdentifierRules(frozenset(), frozenset(), frozenset(), ())
    observations=[]
    actual = grounding._form_facts(grounding._CapturedFormRows(full, core), full, set(), rules=rules,
                                    _naming_capture=observations)
    live = grounding._form_facts(grounding._FormRows(full, core), full, set(), rules=rules)
    assert actual == live and actual['gc_label_variant_occurrences'] == 2
    observation=observations[0]; data=observation['raw']
    row={'generation_id':'synthetic-helper', 'registration_sha256':sg.sha(b'synthetic-helper'),
        'full':sg.file_pin(full,raw), 'core':sg.file_pin(core,raw), 'result':actual,
        'naming':{'path':observation['path'],'present':True,'sha256':sg.sha(data),'bytes':len(data),
                  'base64':base64.b64encode(data).decode()}}
    # Fixed helper boundary only. The separate test uses real registered
    # measure_form; this tiny carrier isolates the precise CR-only defect.
    spec=SimpleNamespace(full_path=full,core_path=core,
        _ledger={'generation_id':'synthetic-helper', complete.FORM_KEY:row},
        _captured_authority=SimpleNamespace(registration=b'synthetic-helper'))
    def denied(*args, **kw):
        raise AssertionError('pure form re-opened or resolved its original inputs')
    monkeypatch.setattr(Path, 'open', denied); monkeypatch.setattr(Path, 'resolve', denied)
    assert complete._captured_form(spec, raw.decode(), raw.decode(), rules) == actual
    assert row['full']['sha256'] == sg.sha(raw)
    row['result'] = {**actual, 'checked': 1}
    with pytest.raises(complete.UsageLedgerError, match='consumed naming bytes'):
        complete._captured_form(spec, raw.decode(), raw.decode(), rules)
    row['result'] = actual
    # Absence is explicit; bool must not compare equal to a recorded zero.
    row['naming'] = {'path':str(default),'present':False,'sha256':None,'bytes':False,'base64':None}
    with pytest.raises(ValueError, match='byte count must be an integer'):
        complete._captured_form(spec, raw.decode(), raw.decode(), rules)


def test_selected_form_preserves_full_parse_before_core_read(tmp_path):
    from data_sheets_schema import grounding
    from data_sheets_schema.run_schema import IdentifierRules
    full=tmp_path/'full.yaml'; full.write_text('name: [\n')
    core=tmp_path/'core.yaml'; core.mkdir()
    rules=IdentifierRules(frozenset(), frozenset(), frozenset(), ())
    with pytest.raises(yaml.parser.ParserError):
        grounding._form_facts(grounding._CapturedFormRows(full,core), full, set(), rules=rules, _naming_capture=[])
