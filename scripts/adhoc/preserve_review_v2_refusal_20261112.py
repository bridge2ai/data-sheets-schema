#!/usr/bin/env python3
"""Preserve historical approval-only version refusal while admitting bundle v3.
Inputs/outputs: execution registration reader; helper-2 Part C, 2026-11-12.
Also make the audit retain scanner configuration failure evidence without
assuming a scanner report exists when the scan explicitly did not run.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
path = root / 'src/data_sheets_schema/native_execution_registration_v2.py'
raw = path.read_text()
old = "    for name, record in records.items():\n        if (type(record) is not dict or type(record.get('version')) is not int\n                or (name != 'review' and record['version'] != VERSION)"
new = "    from . import native_launch_review as launch_review\n    for name, record in records.items():\n        if (type(record) is not dict or type(record.get('version')) is not int\n                or record['version'] != (3 if name == 'review' and\n                    record.get('kind') == launch_review.CURRENT_KIND else VERSION)"
assert raw.count(old) == 1
raw = raw.replace(old, new)
old = "    review = records['review']\n    from . import native_launch_review as launch_review"
assert raw.count(old) == 1
path.write_text(raw.replace(old, "    review = records['review']"))
path = root / 'scripts/adhoc/audit_review_bundle_v3_20261112.py'
raw = path.read_text()
old = "        files = ('scanner.md', 'scanner.json', 'network.json', 'origins-before.json', 'outcome.json')"
assert raw.count(old) == 1
new = "        files = tuple(name for name in ('scanner.md', 'scanner.json', 'scanner-command.json',\n            'pytest.log', 'network.json', 'origins-before.json', 'origins-after.json',\n            'subprocess-origins.json', 'outcome.json') if (directory / name).is_file())"
path.write_text(raw.replace(old, new))
