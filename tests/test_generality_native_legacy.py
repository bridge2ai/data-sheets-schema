"""F13/F14/F16: live examples are neutral and retired modules refuse before IO."""
from pathlib import Path
import re
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('path', ['src/download/interactive_d4d_wrapper.py',
    'src/download/claude_max_d4d_processor.py', 'scripts/fix_failed_extractions.py',
    'src/schema_extract/process_d4d_claude_API_temp0.py'])
def test_retired_modules_refuse_before_imports_or_outputs(path, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match='Historical D4D generator retired'):
        runpy.run_path(str(ROOT / path), run_name='__main__')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('path', ['.claude/commands/d4d-input-deep-research.md',
    '.claude/agents/d4d-review-record.md', 'notes/receipts_pattern_2026-08-27.md'])
def test_active_native_examples_have_no_study_identity(path):
    assert not re.search(r'CHORUS|AI.READ[Ii]|FAIRhub|PhysioNet|B2AI_TOPIC|bridge2ai-for',
                         (ROOT / path).read_text())
