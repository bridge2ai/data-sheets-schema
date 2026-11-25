"""A release series does not use native source attribution (review 2 of #6325, SF3; 2026-11-24).

`RunSpec` construction and the native attribution renderer read one runtime
set, `native_source_attribution.NATIVE_RUNTIMES`. Before this, construction
read the wider `CLAUDE_CODE_RUNTIMES`, which since #6324 also holds the
release-series runtime, so such a specification was admitted and then refused
at render for its renderer, the wrong cause.

Kept apart from `test_release_runtime.py`, whose dataset-token assertions the
D128 scanner records as test dependencies: an edit there that makes it read as
a generation test changes the scanned arrays. Offline; synthetic fixture only.
"""
from dataclasses import replace

import pytest

RELEASE = "Claude Code (release)"


def test_native_attribution_runtimes_are_the_claude_code_runtimes_less_the_release_series():
    """Pins the relation of the two sets; RunSpec construction reads the narrower one."""
    from data_sheets_schema.api_runner import CLAUDE_CODE_RUNTIMES
    from data_sheets_schema.native_source_attribution import NATIVE_RUNTIMES
    assert CLAUDE_CODE_RUNTIMES - NATIVE_RUNTIMES == {RELEASE}
    assert NATIVE_RUNTIMES <= CLAUDE_CODE_RUNTIMES


def _attribution_spec(tmp_path, runtime, version):
    from tests.test_source_metadata_renderer import fixture
    spec, _ = fixture(tmp_path, runtime)
    if not version:
        return replace(spec, render_version=16)
    return replace(spec, render_version=16, native_source_attribution_version=1, native_source_attribution_max_checks=2)


def test_release_runtime_with_native_attribution_is_refused_at_construction(tmp_path):
    with pytest.raises(ValueError, match=r"requires a native source-attribution runtime .*'Claude Code \(release\)' is not one"):
        _attribution_spec(tmp_path, RELEASE, 1)
    assert _attribution_spec(tmp_path, RELEASE, 0).native_source_attribution_version == 0   # without it, unchanged


@pytest.mark.parametrize("runtime", ["Claude Code", "Claude Code (direct)"])
def test_native_attribution_is_unchanged_for_the_other_claude_code_runtimes(tmp_path, runtime):
    spec = _attribution_spec(tmp_path, runtime, 1)
    assert spec.native_source_attribution_version == 1
    assert "Native source-attribution draft preflight v1" in spec.instruction
