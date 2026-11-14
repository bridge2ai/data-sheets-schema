"""Remove unused alternate trace parser for PR 5968 issue 6222, 2026-11-14.

Input/output: native_shared_capture.py in this checkout. Run after the saved
ignore-independent reference search establishes that the definition is unused.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/native_shared_capture.py'
raw = path.read_text()
start = raw.index('def _extend_trace(')
end = raw.index('@dataclass\nclass _CapturedRun:', start)
path.write_text(raw[:start] + raw[end:])
