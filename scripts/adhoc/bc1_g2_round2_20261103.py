#!/usr/bin/env python3
# Purpose: retain round-2 merge attribution and reproducible integration evidence.
# Inputs: pinned local heads; outputs: scratch JSON ledger. BC1+G2 tasks 2/9,
# 2026-11-03. Offline; no protected source or historical evidence is authored.
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import bc1_g2_merge_audit_20261103 as merge_audit

ROUND1 = '92a1c4afa0df9ebb361f87eab1d5fd5bc0b11054'
G1_FIXES = 'bc8f981f758c46d5bb027c61294d8a67bf70ed30'
MERGE = '2a415eb5f62c1e75474aff32e8324cfaccbb4a8a'


def audit(output):
    merge_audit.TARGET, merge_audit.INCOMING = ROUND1, G1_FIXES
    merge_audit.BASE = subprocess.check_output(
        ['git', 'merge-base', ROUND1, G1_FIXES], cwd=ROOT).decode().strip()
    merge_audit.audit(output, MERGE)
    result = json.loads(output.read_bytes())
    assert not result['unattributed'], result['unattributed']
    assert sum(row['lost_count'] for row in result['files']) == 5


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('audit',))
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.output)
