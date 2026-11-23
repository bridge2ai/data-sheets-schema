"""Remove withdrawn PR6302 refusal implementation, 2026-11-21.

Input/output: native_shared_permissions.py in this checkout. The approved
stage-root-grant decision requires real observer stops for every prohibited Write.
"""
from pathlib import Path


target = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/native_shared_permissions.py'
text = target.read_text()
start = text.index('def _native_refusal_trace(')
end = text.index('def _trace(', start)
target.write_text(text[:start] + text[end:])
