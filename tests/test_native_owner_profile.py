"""Fixed private source profile; no runtime, provider, or execution route."""
from copy import deepcopy
import hashlib

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile


def test_omitted_and_exact_zero_keep_the_same_v1_identity_and_profile_absence():
    default = authority.dependency_identity()
    explicit = authority.dependency_identity(stream_snapshot_profile=0)
    assert default == explicit
    assert set(default) == {'version', 'base', 'additional_modules'}
    assert default['version'] == 1
    assert profile.source_profile(0) is None


def test_selected_profile_is_exact_fixed_source_bytes_and_agrees_with_package_authority():
    selected = authority.dependency_identity(stream_snapshot_profile=1)
    baseline = authority.dependency_identity()
    assert selected['version'] == 2
    assert selected['base'] == baseline['base']
    assert selected['additional_modules'] == baseline['additional_modules']
    declaration = selected['stream_snapshot_profile']
    assert declaration['format'] == 'native_stream_snapshot_profile_v1'
    assert declaration['profile'] == 1
    assert declaration['base_controller_sources_sha256'] == inherited.SOURCES_SHA256
    assert set(declaration['implementations']) == {'control', 'coordination', 'runner', 'clock'}
    for role, relative in profile.IMPLEMENTATIONS.items():
        pin = declaration['implementations'][role]
        assert pin['path'] == relative
        assert pin['sha256'] == hashlib.sha256((authority.ROOT / relative).read_bytes()).hexdigest()
        assert selected['base']['package_sources'][relative] == pin['sha256']
    assert selected['base']['package_sources'][profile.RESOLVER_PATH] == hashlib.sha256(
        (authority.ROOT / profile.RESOLVER_PATH).read_bytes()).hexdigest()
    profile.verify_profile(declaration, selected['base']['package_sources'])


def test_source_profile_output_is_detached_from_future_authority():
    original = profile.source_profile(1)
    changed = profile.source_profile(1)
    changed['implementations']['control']['sha256'] = '0' * 64
    changed['implementations'].clear()
    assert profile.source_profile(1) == original


def test_actual_selected_loader_binds_fresh_class_from_exact_frozen_graph():
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(identity) as controls:
        cls = profile.bind_control(identity['stream_snapshot_profile'], controls)
        other = profile.bind_control(identity['stream_snapshot_profile'], controls)
        assert cls is not other
        assert issubclass(cls, controls['native_control'].NativeControl)
        assert cls.budget_stop_type is controls['budgeted_cborg'].BudgetStop
        assert controls['native_control'].NativeControl is not cls
        assert 'native_owner_control_v1' not in controls


def test_selected_authority_is_proved_by_actual_named_git_blobs():
    # Coordinator commits the reviewed production closure before running this
    # check. A source-only/uncommitted proposal is deliberately insufficient.
    authority.require_committed(authority.dependency_identity(stream_snapshot_profile=1))


def test_v1_loader_never_establishes_a_selected_binding_scope():
    declaration = profile.source_profile(1)
    with authority.loaded_dependencies(authority.dependency_identity()) as controls:
        with pytest.raises(ValueError, match='selected loader scope'):
            profile.bind_control(declaration, controls)


def test_equal_copied_mapping_is_not_the_exact_yielded_authority():
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(identity) as controls:
        with pytest.raises(ValueError, match='selected loader scope'):
            profile.bind_control(identity['stream_snapshot_profile'], dict(controls))


@pytest.mark.parametrize('target', [profile.IMPLEMENTATIONS['control'], profile.RESOLVER_PATH])
@pytest.mark.parametrize('mutation', ['missing', 'changed'])
def test_fixed_source_profile_cannot_disagree_with_whole_package_authority(mutation, target):
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    declared = identity['stream_snapshot_profile']
    sources = deepcopy(identity['base']['package_sources'])
    if mutation == 'missing':
        sources.pop(target)
    else:
        sources[target] = '0' * 64
    with pytest.raises(ValueError, match='package source authority'):
        profile.verify_profile(declared, sources)
