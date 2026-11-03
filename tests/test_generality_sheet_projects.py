"""N: sheet synchronization admits projects from declared data before IO."""
import pytest
from scripts import update_raw_from_sheet as sheet


def test_sheet_project_universe_follows_manifest(tmp_path, monkeypatch):
    manifest = tmp_path / 'manifest.yaml'
    manifest.write_text('projects: {NEWPROJ: {sources: []}}\n')
    calls = []
    monkeypatch.setattr(sheet, 'read_sheet', lambda ident: calls.append(ident) or [])
    sheet.main(['--source-manifest', str(manifest), '--project', 'NEWPROJ', '--dry-run'])
    assert len(calls) == 1
    with pytest.raises(SystemExit):
        sheet.main(['--source-manifest', str(manifest), '--project', 'CHORUS', '--dry-run'])
    assert len(calls) == 1
