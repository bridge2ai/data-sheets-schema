"""Update PR 5968 envelope tests under the lead ruling, 2026-11-16.

Input/output: bridge test source. Keep production authority unchanged.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'tests/test_native_execution_bridge_v2.py'
source = path.read_text()
start = source.index('def test_wire_still_invokes_pinned_envelope_check_after_structural_precheck(')
source = source[:start] + '''def test_wire_still_invokes_pinned_envelope_check_after_structural_precheck(prepared, monkeypatch):
    import data_sheets_schema
    from data_sheets_schema import native_shared_authority_wire as wire
    _, preparation = prepared
    loader = registration.authority.loaded_dependencies
    parse = c.strict_json
    check = wire.require_envelope
    observed = []

    def structural(*args, **kwargs):
        result = parse(*args, **kwargs)
        observed.append('structural')
        return result

    def envelope(value):
        assert observed == ['structural']
        result = check(value)
        observed.append('v3 envelope')
        return result

    def observe(identity):
        assert observed == ['structural', 'v3 envelope']
        observed.append('dependencies')
        monkeypatch.setattr(data_sheets_schema, 'native_shared_authority_wire', wire)
        monkeypatch.setattr(registration, 'c', c)
        with loader(identity) as controls:
            yield controls

    # Observe caller lookups, leaving real source-verified callables intact.
    monkeypatch.setattr(registration, 'c', SimpleNamespace(strict_json=structural))
    monkeypatch.setattr(data_sheets_schema, 'native_shared_authority_wire',
                        SimpleNamespace(require_envelope=envelope))
    monkeypatch.setattr(registration.authority, 'loaded_dependencies', contextmanager(observe))
    body, identity = registration._wire(c.canonical(preparation))
    assert body == preparation['registration']
    assert identity == preparation['registration']['dependencies']
    assert observed == ['structural', 'v3 envelope', 'dependencies']


def test_malformed_v3_envelopes_refuse_before_dependency_context(monkeypatch):
    from data_sheets_schema import native_shared_authority_wire as wire

    def forbidden(*args, **kwargs):
        pytest.fail('malformed envelope reached dependency authority')

    monkeypatch.setattr(registration.authority, 'dependency_identity', forbidden)
    monkeypatch.setattr(registration.authority, 'loaded_dependencies', forbidden)
    for kind in (wire.PREPARATION_KIND, wire.EXECUTION_KIND):
        valid = wire.envelope({'schema_version': 3, 'kind': kind})
        assert wire.require_envelope(valid) == valid['registration']
        invalid = [None, [], {**valid, 'extra': 1}]
        for field in valid:
            changed = deepcopy(valid)
            del changed[field]
            invalid.append(changed)
        for field, values in (
                ('authority_version', (1, 3, True, '2')),
                ('controller_sources_sha256', ('0' * 64, None)),
                ('registration', (None, []))):
            invalid.extend({**valid, field: value} for value in values)
        for field, values in (('schema_version', (2, 4, True, '3')),
                              ('kind', ('unknown', wire.HISTORICAL_PREPARATION_KIND))):
            for value in values:
                changed = deepcopy(valid)
                changed['registration'][field] = value
                invalid.append(changed)
            changed = deepcopy(valid)
            del changed['registration'][field]
            invalid.append(changed)
        for value in invalid:
            with pytest.raises(ValueError):
                registration._wire(c.canonical(value))
'''
assert chr(64) not in source[start:]
path.write_text(source)
