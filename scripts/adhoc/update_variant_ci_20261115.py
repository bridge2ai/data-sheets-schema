"""Add bounded failure collection to native CI cases; assignment 2026-11-15.

Input/output: main workflow. Preserve all job rosters and budgets.
"""
from pathlib import Path

path = Path('.github/workflows/main.yaml')
text = path.read_text()
for name in ('native-public-completion', 'native-public-long'):
    start = text.index('  ' + name + ':\n')
    end = text.index('\n  #', start) if name.endswith('long') else text.index('\n  native-public-long:', start)
    section = text[start:end]
    section = section.replace('            --durations=25',
        '            --basetemp="${{ runner.temp }}/native-case" \\\n            --durations=25')
    anchor = '      - name: Require the case to leave notes/, tests/ and utils/ untouched\n'
    step = ('      - name: Preserve bounded native failure diagnostics\n'
            '        if: failure()\n'
            '        run: |\n'
            '          poetry run python scripts/adhoc/collect_native_failure_evidence.py \\\n'
            '            "${{ runner.temp }}/native-case" test-results/native-failure\n')
    assert section.count(anchor) == 1
    section = section.replace(anchor, step + anchor)
    text = text[:start] + section + text[end:]
path.write_text(text)
