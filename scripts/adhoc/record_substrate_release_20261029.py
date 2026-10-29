#!/usr/bin/env python3
# Purpose: append F6/D66 schema release hashes after Makefile generation.
# Inputs: full/core source and merged YAML; output: release_history.yaml.
# Generality G1, 2026-10-29; preserves previous release entries verbatim.
import hashlib
from pathlib import Path

schema = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/schema'
history = schema / 'release_history.yaml'
text = history.read_text()
assert '  - version: 3.1.0\n' not in text
addition = '  - version: 3.1.0\n    declared: 2026-10-29\n'
for kind, stem in (('full', 'data_sheets_schema'), ('core', 'data_sheets_schema_core')):
    for product, suffix in (('source', ''), ('merged', '_all')):
        digest = hashlib.sha256((schema / (stem + suffix + '.yaml')).read_bytes()).hexdigest()
        addition += f'    {kind}_{product}_sha256: {digest}\n'
addition += ('    note: >-\n'
             '      D66/F6 declares EDAM Data/Format and IANA media-type term sources\n'
             '      for Instance.data_substrate. The selected profile may additionally\n'
             '      supply its pinned registry. Historical schema hashes stay unchanged.\n')
history.write_text(text + addition)
assert history.read_text() == text + addition
