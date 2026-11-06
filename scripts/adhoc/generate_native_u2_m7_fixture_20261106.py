# Purpose: generate the exact-M7 saved fixture for #5508, 2026-11-06.
# Inputs: exported M7 source and pytest fixtures. Outputs: saved registration/composition.

"""Replay frozen v1 authority in its original exported source environment."""
import json
import os
from pathlib import Path

import pytest

from data_sheets_schema import native_attribution_controller as controller
from data_sheets_schema import native_attribution_registration as draft
from tests.test_native_attribution_controller import selected
from tests.test_native_source_attribution import case
from tests.test_source_attribution_preflight import inputs


@pytest.mark.skipif(not os.environ.get('NATIVE_U2_V1_REPLAY'), reason='requires the exact M7 exported source environment')
def test_frozen_v1_record_roundtrip(selected):
    _, raw, _, _, composition = selected
    value = draft.verified(raw)[1]
    assert value['code_commit'] == '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
    assert not any('native_attribution_controller_v2' in key for key in value['checker_source_tree_sha256'])
    assert controller.verified_composition(composition)['version'] == 1
    destination = Path(os.environ['NATIVE_U2_V1_REPLAY'])
    destination.mkdir()
    (destination/'registration.json').write_bytes(raw)
    (destination/'composition.json').write_bytes(composition)
    (destination/'verified.json').write_text(json.dumps({'source_commit': value['code_commit'],
        'registration_sha256': draft._sha(raw), 'composition_sha256': draft._sha(composition),
        'controller_sources_sha256': controller.SOURCES_SHA256}, indent=2)+'\n')
