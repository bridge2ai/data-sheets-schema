#!/usr/bin/env python3
"""2026-11-12 #5967: adapt saved offline runner and composition recipe.
Inputs: accepted hardening tree, prior helper recipes; outputs: own helpers.
No runtime, network or provider execution.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
e = root.parent
runner = (root / 'scripts/adhoc/run_h3_hardening_tests_20261112.py').read_text()
runner = runner.replace('codex-native-launch-sequence-hardening-20261112', root.name).replace('scratch-h3-launch-hardening-20261112', 'scratch-h3-failure-record-20261112')
(root / 'scripts/adhoc/run_h3_failure_tests_20261112.py').write_text(runner)
recipe = (e / 'codex-native-packet-builder-20261112/scripts/adhoc/compose_h3_full_chain_20261112.py').read_text()
recipe = recipe.replace("S = E / 'scratch-h3-packet-builder-20261112'", "S = E / 'scratch-h3-failure-record-20261112'")
start = recipe.index("base = ")
end = recipe.index("spec = ", start)
recipe = recipe[:start] + "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--base', required=True)\nparser.add_argument('--name', required=True)\nargs = parser.parse_args()\nbase = args.base\ncommits = []\n" + recipe[end:]
recipe = recipe.replace("out = S / 'composition-a'", "out = S / args.name").replace('config.bak-h3-full-chain-20261112', 'config.bak-h3-failure-20261112')
(root / 'scripts/adhoc/compose_h3_failure_20261112.py').write_text(recipe)
