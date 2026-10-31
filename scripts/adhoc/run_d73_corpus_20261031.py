#!/usr/bin/env python3
"""#5212/D73, 2026-10-31: run the retained D70 census in the offline environment.

Inputs: a local Git ref and an output path under scratch-5212fix.
Output: the existing per-record census, without writing any corpus record.
"""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
ref, destination = sys.argv[1:]
assert Path(destination).resolve().is_relative_to(SCRATCH)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d41_legacy_controls_20261029 import bootstrap
bootstrap(ROOT, SCRATCH)
sys.argv = ["d70_corpus_eligibility_20261030.py", "--ref", ref, "--output", destination]
runpy.run_path(str(ROOT / "scripts/adhoc/d70_corpus_eligibility_20261030.py"), run_name="__main__")
