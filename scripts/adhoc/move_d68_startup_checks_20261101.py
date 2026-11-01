#!/usr/bin/env python3
"""#5212 round 4, 2026-11-01: move existing startup checks before locks.

Input/output: api_runner.py in this branch; preserves the schema diagnostics.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/api_runner.py'
text = path.read_text()
start = text.index('    from data_sheets_schema.schema_sync import (', text.index('def _execute('))
end = text.index('    usage: list[dict[str, Any]] = []', start)
block = text[start:end]
block = block.replace('    from data_sheets_schema.provenance import build_record, record_path_for\n\n', '')
no_resume = '''    if spec.shared_generation_version and not resume:
        if latch_journal._legacy_evidence(spec):
            raise UsageLedgerError("shared generation cannot reuse spent outputs with no-resume; register a fresh run")
'''
assert no_resume in block
block = block.replace(no_resume, '')
helper = '''def _startup_checks(spec, client):
    """Read-only checks: a failed startup must leave no lock or run file."""
''' + block + '    return settings, client\n\n\n'
text = text[:start] + '''    from data_sheets_schema.provenance import build_record, record_path_for
    settings, client = _startup_checks(spec, client)
''' + text[end:]
text = text.replace('def _execute(spec: RunSpec,', helper + 'def _execute(spec: RunSpec,', 1)
path.write_text(text)
