"""Migrate C4 test call sites to the explicit orchestration boundary (2026-11-07).

Inputs: the C4 worktree's existing controls, attribution and fixture
tests. Outputs: import/call spelling changes only; assertions remain intact.
Serves native U3-C round 4. This is idempotent and never edits another worktree.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path, edits):
    target = ROOT / path
    text = target.read_text()
    for old, new in edits:
        if new in text:
            continue
        if old in text:
            text = text.replace(old, new)
        else:
            raise ValueError(f'missing migration preimage: {path}: {old}')
    target.write_text(text)


def main():
    replace('tests/test_native_shared_controls.py', [
        ('from data_sheets_schema import native_shared_controls as controls\n',
         'from data_sheets_schema import native_shared_controls as controls\nfrom data_sheets_schema import native_shared_controls_orchestration as orchestration\n'),
        ('controls.loaded_controls(', 'orchestration.loaded_controls(')])
    replace('tests/test_native_shared_attribution.py', [
        ('from data_sheets_schema import native_shared_controller as controller',
         'from data_sheets_schema import native_shared_controller_orchestration as controller'),
        ('from data_sheets_schema import native_shared_attribution as attribution\n',
         'from data_sheets_schema import native_shared_attribution as attribution\nfrom data_sheets_schema import native_shared_attribution_orchestration as live_attribution\n'),
        ('attribution.live(', 'live_attribution.live(')])
    replace('tests/native_shared_captured_fixture.py', [
        ('controller.inherited.SOURCES_SHA256', 'controller.wire.CONTROLLER_SOURCES_SHA256')])


if __name__ == '__main__':
    main()
