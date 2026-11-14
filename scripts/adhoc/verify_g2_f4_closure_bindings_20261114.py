#!/usr/bin/env python3
# Verify G2 F4/legacy/proposal closure bindings without final closure, 2026-11-14.
# Inputs: frozen closure, saved clean149 and interrupted publication evidence.
# Outputs: exclusive closure-bindings.json under the fresh F4 reporting proof.
# No tests, project imports, source edits or final handoff/closure generation.
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
TARGET = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
OUT = SCRATCH / 'report-closure-pin-verification-after-f4-reuse/closure-bindings.json'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    assert OUT.parent.is_dir() and not OUT.exists()
    closure = runpy.run_path(str(TARGET))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    legacy = []
    for identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):
        row, detail = closure['close'](identity, lambda evidence, details: closure['close_legacy_rerun'](
            identity, [SCRATCH / 'legacy-full-serial'], head, evidence, details))
        assert row['status'] == 'verified', row
        legacy.append({'result': row, 'details': detail})
    binding_evidence = []
    binding = closure['publication_binding'](head, binding_evidence)
    assert binding['production_unchanged'] is True
    assert binding['applied_commit'] == '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
    assert binding['test_correction_commit'] == '21367471df2e7d2f761153e1b91b218a705c62c6'
    proposal_path = SCRATCH / 'proposal-6207-after-6217/proposal.json'
    review_path = SCRATCH / 'review-6207-after-6217.json'
    proposal = json.loads(proposal_path.read_bytes())
    applicability = closure['proposal_applicability'](json.loads(review_path.read_bytes()), proposal, head)
    assert applicability['passed'] is True
    apply = subprocess.run(['git', 'apply', '--check', proposal['patch']['path']],
                           cwd=ROOT, capture_output=True, check=False)
    assert apply.returncode == 0, apply.stderr
    publication_dirs = [SCRATCH / 'final-regressions', SCRATCH / 'publication-public-canary']
    oracle, details = closure['close']('G2-REVIEW-6217-F4', lambda evidence, details:
        closure['close_publication_oracle'](publication_dirs, head, evidence, details))
    assert oracle['status'] == 'not_verified', 'partial or interrupted proof must not close F4'
    result = {'status': 'verified', 'closure': pin(TARGET), 'producer': pin(Path(__file__).resolve()),
        'head': head, 'legacy': legacy, 'publication_binding': binding,
        'publication_binding_evidence': binding_evidence, 'proposal_applicability': applicability,
        'proposal': pin(proposal_path), 'proposal_review': pin(review_path),
        'apply_check': {'returncode': apply.returncode, 'stdout': apply.stdout.decode(), 'stderr': apply.stderr.decode()},
        'publication_oracle_pending': {'result': oracle, 'details': details},
        'scope': 'Actual standalone closure functions only; original149 evidence reused on the bounded reviewed delta, production2070/test213 binding checked, and F4 remains not_verified without fresh full-file proof. The canary command is considered only as a selector, not a completed outcome.'}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with OUT.open('xb') as stream:
        stream.write(raw)
    assert OUT.read_bytes() == raw
    print(json.dumps({'output': pin(OUT), 'legacy_statuses': [row['result']['status'] for row in legacy],
                      'publication_oracle_status': oracle['status']}))


if __name__ == '__main__':
    main()
