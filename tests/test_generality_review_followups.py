"""G1 N10-N12: quarantine provenance and public entry points agree."""
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_f16_exception_cites_the_standing_rule():
    doc = yaml.safe_load((ROOT / '.claude/skills/d4d-generation-specificity-audit/exceptions.yaml').read_text())
    entry = next(e for e in doc['exceptions'] if 'src/download/interactive_d4d_wrapper.py' in e['path'])
    assert '23:37Z standing generality rule' in entry['decision']


@pytest.mark.parametrize('family', ['rubric10', 'rubric20'])
def test_v5_output_examples_do_not_name_specific_registrars(family):
    text = (ROOT / f'src/download/prompts/{family}_semantic_v5_schema.json').read_text()
    assert 'valid_nih' not in text and 'valid_zenodo' not in text


def test_retired_make_entry_refuses_before_creating_output(tmp_path):
    result = subprocess.run(['make', '-f', str(ROOT / 'project.Makefile'),
                             'extract-d4d-individual-gpt5', 'PROJECT=NEWPROJ'],
                            cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'Retired historical generator (F16)' in result.stdout
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('directory', ['claudecode', 'gpt5'])
def test_legacy_readmes_route_new_generation_to_current_protocol(directory):
    text = (ROOT / f'src/download/prompts/{directory}/README.md').read_text()
    assert 'retired' in text and 'shared-generation-api-v1.md' in text
