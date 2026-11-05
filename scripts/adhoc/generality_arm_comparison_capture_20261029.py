#!/usr/bin/env python3
# Purpose: classify the full-suite committed-comparison failure against base.
# Inputs: selected checkout and external output filename, argv[1].
# Outputs: read-only rendered comparison and exact diff from committed report.
# G1 complete-suite acceptance, 2026-10-29. Does not rewrite historical reports.
import difflib
import importlib.util
import os
from pathlib import Path
import sys

root = Path(os.environ.get('G1_CHECKOUT_ROOT', Path(__file__).resolve().parents[2]))
output = Path(sys.argv[1]).resolve()
assert not output.is_relative_to(root.resolve())
spec = importlib.util.spec_from_file_location('arm_comparison', root / 'scripts/arm_comparison.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
data = module.collect()
scores = {rubric: {key: {project: module.rubric_scores(prefix, project, rubric)
                       for project in module.PROJECTS}
                  for key, _display, prefix, *_ in module.ARMS}
          for rubric in module.EVAL_DIRS}
rendered = module.render_markdown(data, scores)
output.write_text(rendered)
assert output.read_text() == rendered
delta = ''.join(difflib.unified_diff(module.OUT_MD.read_text().splitlines(True),
                                   rendered.splitlines(True),
                                   fromfile='committed', tofile='rendered'))
output.with_suffix('.diff').write_text(delta)
print(f'{len(rendered.encode())} rendered bytes; {len(delta.encode())} diff bytes; {output}')
