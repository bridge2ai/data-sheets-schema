#!/usr/bin/env python3
"""Export U5 comparison inputs into new U4b scratch, 2026-11-08 (#4354).

Inputs: the U5 helper's fixed local commits and current committed candidate.
Outputs: fresh immutable exports/manifests under scratch-native-u4b only.
No network, source worktree writes, overlays or prior evidence replacement.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u4b_input_exporter',
    ROOT / 'scripts/adhoc/native_u5_inputs_20261108.py')
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)
inputs.SCRATCH = ROOT.parent / 'scratch-native-u4b'

if __name__ == '__main__':
    inputs.main()
