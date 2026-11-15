"""Successor wire controls; historical evidence never grants new admission."""
import pytest
from data_sheets_schema import native_shared_authority_wire as wire
from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as c


@pytest.mark.parametrize('kind,keys,scope', [
    (wire.HISTORICAL_PREPARATION_KIND, wire.PREPARATION_KEYS - {'environment_manifest'}, wire.PREPARATION_SCOPE),
    (wire.HISTORICAL_EXECUTION_KIND, wire.EXECUTION_KEYS, wire.EXECUTION_SCOPE),
])
def test_historical_evidence_cannot_be_registered(kind, keys, scope, monkeypatch):
    body = dict.fromkeys(keys)
    body.update(kind=kind, schema_version=2, execution=scope)
    if 'execution_gates' in body:
        body['execution_gates'] = list(wire.EXECUTION_GATES)
    envelope = dict(authority_version=2, controller_sources_sha256=wire.CONTROLLER_SOURCES_SHA256,
                    registration=body)
    assert wire.historical_body(envelope) == body
    def forbidden():
        pytest.fail('historical wire must refuse before authority work')
    monkeypatch.setattr(registration.authority, 'dependency_identity', forbidden)
    with pytest.raises(ValueError, match='requires v3'):
        registration._wire(c.canonical(envelope))
    with pytest.raises(ValueError, match='requires v3'):
        wire.envelope(body)


def test_current_preparation_requires_manifest_field():
    from data_sheets_schema import native_shared_controller as controller
    body = dict.fromkeys(wire.PREPARATION_KEYS - {'environment_manifest'})
    body.update(kind=wire.PREPARATION_KIND, schema_version=3, execution=wire.PREPARATION_SCOPE)
    with pytest.raises(ValueError):
        controller.captured_preparation_body(c.canonical(wire.envelope(body)))
