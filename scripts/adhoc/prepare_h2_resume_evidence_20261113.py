#!/usr/bin/env python3
"""Save resumed preload command and enable bounded test cohorts, 2026-11-13.
Inputs: known executed command and task launcher. Outputs: provenance JSON and
launcher worker option; issues 6193-6202. Does not launch tests or change pins.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h2-resume-20261113'
python = str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python')
command = [python, '-m', 'pytest', 'tests/test_native_shared_callback_preloading.py',
    '-q', '-p', 'no:cacheprovider', '--basetemp=' + str(OUT / 'preload-cases'),
    '--junitxml=' + str(OUT / 'preload.xml')]
(OUT / 'preload-command.json').write_text(json.dumps({'command': command,
    'cwd': str(ROOT), 'environment': {'PYTHONPATH': str(ROOT / 'src'),
    'PYTHONDONTWRITEBYTECODE': '1'}, 'log': str(OUT / 'preload.log'),
    'provenance': 'Recorded from the executed shell command after launch; no completion claimed.'}, indent=2) + '\n')
p = ROOT / 'scripts/adhoc/run_h2_resume_20261113.py'
s = p.read_text()
s = s.replace("    p.add_argument('nodes', nargs='*')", "    p.add_argument('nodes', nargs='*')\n    p.add_argument('--workers', type=int, choices=range(5), default=0)")
s = s.replace("    args = p.parse_args()", "    args = p.parse_args()\n    if args.workers and args.cohort in (*PUBLIC, 'native', 'audit', 'budget'):\n        p.error('public tests and exact offline lanes must run serially')")
s = s.replace("    nodes = args.nodes or [PUBLIC[args.cohort]] if args.cohort in PUBLIC else args.nodes", "    nodes = args.nodes or ([PUBLIC[args.cohort]] if args.cohort in PUBLIC else [])")
s = s.replace("    argv += ['--basetemp='", "    if args.workers:\n        argv += ['-n', str(args.workers)]\n    argv += ['--basetemp='")
p.write_text(s)
