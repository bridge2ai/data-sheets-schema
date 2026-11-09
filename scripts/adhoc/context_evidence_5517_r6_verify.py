"""PR #5532/#5517, 2026-11-08: reuse independent byte-containment review.

Input: committed HEAD, original reviewer script. Output: scratch-5517 JSON audit.
Only adaptation: recognize the new decision-note tag as a note token. All original
bundle/chunk hashes, quotation bytes, values and D52 comparisons remain unchanged.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-5517'
assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
path = ROOT.parent / 'plans/reviews/pr5532_review_scripts/verify_context_quotations.py'
spec = importlib.util.spec_from_file_location('independent_quotation_review', path)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
original = review.tokenize


def tokenize(evidence):
    return [(kind, 'search_notes' if kind == 'tag' and payload == 'context_note: D120' else payload)
            for kind, payload in original(evidence)]


review.tokenize = tokenize
review.self_test()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
report = review.audit(str(ROOT), head, review.DEFAULT_BASE)
report['adapter'] = 'Only context_note: D120 mapped to note token; strict allow-list checked by pytest.'
report['reviewer_script_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
output = OUT / 'r6-verbatim-audit.json'
output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
assert json.loads(output.read_text()) == report
print(json.dumps(report['totals'], indent=2))
print('reviewer_script_sha256:', report['reviewer_script_sha256'])
sys.exit(bool(report['totals']['not_contained'] or report['totals']['structural_problems']))
