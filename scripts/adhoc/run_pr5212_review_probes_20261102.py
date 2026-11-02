#!/usr/bin/env python3
"""#5212 round 7, 2026-11-02: run original reviewer probes against pinned code.

Inputs: --probe-dir (read-only reviewer helpers), then offline runner arguments.
Outputs: the standard scratch phase ledger; sources and probes remain unchanged.
The extra import path lets the original probes import their adjacent helpers.
"""
import argparse
from pathlib import Path
import runpy
import sys

p = argparse.ArgumentParser()
p.add_argument('--probe-dir', type=Path, required=True)
a, rest = p.parse_known_args()
assert a.probe_dir.is_dir()
sys.path.insert(0, str(a.probe_dir.resolve()))
runner = Path(__file__).with_name('run_d68_round4_20261101.py')
sys.argv = [str(runner), *rest]
runpy.run_path(str(runner), run_name='__main__')
