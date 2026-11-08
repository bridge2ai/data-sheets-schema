"""C5 handoff through real A scopes; no positive stand-in or loader patch.

The ordinary-module mint below is an explicit negative adversarial fixture.
It never becomes an accepted C carrier or an execution registration.
"""
import hashlib
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_controls as ordinary_controls
from data_sheets_schema import native_shared_controls_orchestration as orchestration
from tests.test_native_execution_authority_v2 import isolated_modules

NAME = 'data_sheets_schema.native_shared_controls'
RELATIVE = 'src/data_sheets_schema/native_shared_controls.py'


def test_genuine_projection_handoff_to_fresh_source_consumer(isolated_modules):
    identity = authority.dependency_identity()
    pins = identity['base']['package_sources']
    previous = sys.modules.get(NAME)
    with orchestration.loaded_controls(identity) as projected:
        minted_module = sys.modules[NAME]
        assert minted_module is not ordinary_controls
        assert type(projected) is minted_module._PureControls
        assert authority.module_source_identity(minted_module) == {
            'name': NAME, 'path': str(authority.ROOT / RELATIVE), 'sha256': pins[RELATIVE]}
        with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
            assert consumer is minted_module
            assert consumer.require_controls(projected) is projected
            with authority.loaded_verified_package_module(
                    'data_sheets_schema.native_shared_policy', package_sources=pins) as policy:
                assert policy.pure_controls is consumer
                assert policy.pure_controls.require_controls(projected) is projected
                assert projected['native_readonly'].lookup_guidance()
        assert sys.modules[NAME] is minted_module
        assert minted_module.require_controls(projected) is projected
    assert sys.modules.get(NAME) is previous


def test_ordinary_import_mint_is_not_accepted_by_verified_consumer(isolated_modules):
    """A plausible ordinary mint remains outside A's verified module lifetime."""
    identity = authority.dependency_identity()
    ordinary_members = {}
    ordinary_carrier = None
    with orchestration.loaded_controls(identity) as projected:
        try:
            for name, members in ordinary_controls._MEMBERS.items():
                helper = sys.modules[name]
                helper_identity = authority.module_source_identity(helper)
                member = ordinary_controls._PureProjection(helper, helper_identity, members)
                ordinary_members[name] = member
                ordinary_controls._PROJECTION_ATTESTORS[member] = authority.module_source_identity
            ordinary_carrier = ordinary_controls._PureControls(ordinary_members)
            ordinary_controls._LOADER_CONTROLS[ordinary_carrier] = tuple(
                (name, member, tuple(sorted(member._identity.items())))
                for name, member in sorted(ordinary_members.items()))
            assert ordinary_controls.require_controls(ordinary_carrier) is ordinary_carrier
            with pytest.raises(ValueError, match='was not compiled from verified source bytes'):
                authority.module_source_identity(ordinary_controls)
            with authority.loaded_verified_package_module(
                    NAME, package_sources=identity['base']['package_sources']) as consumer:
                assert consumer.require_controls(projected) is projected
                with pytest.raises(ValueError, match='fixed pure-control projection'):
                    consumer.require_controls(ordinary_carrier)
                with pytest.raises(ValueError, match='fixed pure-control projection'):
                    ordinary_controls.require_controls(projected)
        finally:
            if ordinary_carrier is not None:
                ordinary_controls._LOADER_CONTROLS.pop(ordinary_carrier, None)
            for member in ordinary_members.values():
                member._active = False
                ordinary_controls._PROJECTION_ATTESTORS.pop(member, None)


def test_verified_consumer_refuses_unminted_forged_and_expired_carriers(isolated_modules):
    identity = authority.dependency_identity()
    pins = identity['base']['package_sources']
    with orchestration.loaded_controls(identity) as projected:
        with authority.loaded_verified_package_module(NAME, package_sources=pins) as consumer:
            copied = consumer._PureControls(dict(projected))
            for invalid in (None, {}, dict(projected), object()):
                with pytest.raises(ValueError, match='fixed pure-control projection'):
                    consumer.require_controls(invalid)
            with pytest.raises(ValueError, match='not minted by the active loader'):
                consumer.require_controls(copied)
            assert consumer.require_controls(projected) is projected
        retained_consumer = consumer
    with pytest.raises(ValueError, match='not minted by the active loader'):
        retained_consumer.require_controls(projected)
    with authority.loaded_verified_package_module(NAME, package_sources=pins) as fresh:
        assert fresh is not retained_consumer
        with pytest.raises(ValueError, match='fixed pure-control projection'):
            fresh.require_controls(projected)


def test_source_change_after_verified_scope_refuses_reuse_in_scratch(tmp_path, monkeypatch):
    """Exact real C source in scratch; no checkout mutation or loader substitution.

    This checks source revalidation at a nested A entry, not execution admission
    or a claim that merely calling an already-loaded pure function rereads files.
    """
    raw = Path(ordinary_controls.__file__).read_bytes()
    path = tmp_path / RELATIVE
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    pins = {RELATIVE: digest}
    monkeypatch.setattr(authority, 'ROOT', tmp_path)
    previous = sys.modules.get(NAME)
    with authority.loaded_verified_package_module(NAME, package_sources=pins) as verified:
        assert authority.module_source_identity(verified) == {
            'name': NAME, 'path': str(path), 'sha256': digest}
        path.write_bytes(raw + b'\n# changed after source verification\n')
        with pytest.raises(ValueError, match='source bytes differ from their pin'):
            with authority.loaded_verified_package_module(NAME, package_sources=pins):
                pytest.fail('changed source was reused as verified')
        assert sys.modules[NAME] is verified
    assert sys.modules.get(NAME) is previous
    assert path.read_bytes().endswith(b'# changed after source verification\n')
