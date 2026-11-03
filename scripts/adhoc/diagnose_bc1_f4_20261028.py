"""F4 offline scanner diagnosis, 2026-10-28.

Inputs: current source and specificity scanner. Output: bounded exception-frame
or completed-scan evidence under notes/reviews. Never patches scanner semantics.
"""
import ast
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    path = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
    spec = importlib.util.spec_from_file_location('bc1_f4_scan', path)
    scan = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = scan
    spec.loader.exec_module(scan)
    try:
        report = scan.run(ROOT)
    except scan.ConfigError as exc:
        frames = []
        trace = exc.__traceback__
        while trace:
            frame = trace.tb_frame
            if frame.f_code.co_name in ('flow', 'effects', 'container_kind', 'refusal', '<dictcomp>'):
                local = frame.f_locals
                frames.append({'function': frame.f_code.co_name, 'line': trace.tb_lineno,
                    **{name: ast.unparse(value)[:1200] if isinstance(value, ast.AST) else str(value)[:1200]
                       for name in ('q', 'name', 'actual', 'formal', 'formal_name', 'node', 'kind', 'aliases', 'uncertain')
                       if (value := local.get(name)) is not None}})
            trace = trace.tb_next
        result = {'error': str(exc), 'frames': frames}
        (ROOT / 'notes/reviews/bc1_f4_diagnosis_2026-10-28.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return
    result = {'state': 'completed', 'exit': report['exit'],
              'self_test': report['self_test']['passed'],
              'model_facing_modules': report['facts']['model_facing_modules'],
              'violations': len(report['violations']),
              'bc1_violations': [hit for hit in report['violations']
                                 if hit.get('path', '').startswith('src/data_sheets_schema/bc1_')],
              'note': 'Completed scan can report repository-specificity violations; exit 1 is not ConfigError.'}
    (ROOT / 'notes/reviews/bc1_f4_diagnosis_2026-10-28.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
