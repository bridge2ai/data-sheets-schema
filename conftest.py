"""Keep standalone demonstrations out of pytest's whole-tree discovery.

These three historical scripts contain no pytest tests. Importing them loads
optional document-rendering tools or starts downloads. All actual tests,
including the separate notes/ CI suites, remain discoverable (G1 N1).
"""

collect_ignore = [
    'src/renderer/test_renderer.py',
    'src/renderer/test_yaml_extraction.py',
    'src/scripts_obsolete/download_module_test.py',
]
