"""Issue 6233, 2026-11-14: report function costs from persisted diagnostics.

Input: one diagnostic case directory. Outputs: function-cost JSON and Markdown.
Monitoring clocks are thread CPU. Live cProfile statistics use elapsed time.
"""
import json
from pathlib import Path
import pstats
import sys

case = Path(sys.argv[1]).resolve(strict=True)
rows = [json.loads(line) for line in (case / 'callback-cpu.jsonl').read_text().splitlines()]
callbacks = [row for row in rows if row['event_type'] == 'control_request' and row['work'] == '_observe_event']
profiles = []
for path in sorted(case.glob('callback-*.prof')):
    stats = pstats.Stats(str(path))
    functions = []
    for (filename, line, name), (primitive, total, own, cumulative, callers) in stats.stats.items():
        if 'native_shared_' not in filename and not filename.endswith('/native_control.py'):
            continue
        functions.append({'file': filename, 'line': line, 'function': name,
                          'primitive_calls': primitive, 'calls': total,
                          'own_elapsed': own, 'cumulative_elapsed': cumulative})
    profiles.append({'path': str(path), 'total_elapsed': stats.total_tt,
                     'functions': sorted(functions, key=lambda item: -item['cumulative_elapsed'])})
result = {'scope': 'Inclusive nested function costs overlap and must not be summed. '
                   'Monitoring reports worker CPU. cProfile also records concurrent controller service; '
                   'its raw cumulative elapsed values can have inconsistent parent/child totals and '
                   'are retained for inspection, not reliable cost allocation. Use its call counts '
                   'and the independent monitoring clocks. The first canary did not collect function spans.',
          'callbacks': callbacks, 'profiles': profiles}
target = case / 'function-costs.json'
target.write_text(json.dumps(result, indent=2) + '\n')
result = json.loads(target.read_text())
lines = [result['scope'], '', '| Callback | Profiled | Function | Calls | Inclusive thread CPU s | Inclusive wall s |',
         '| ---: | --- | --- | ---: | ---: | ---: |']
for row in result['callbacks']:
    for function, value in sorted(row.get('functions', {}).items()):
        lines.append(f"| {row['calls']} | {row.get('cprofile_enabled', False)} | {function} | {value['calls']} | {value['thread_cpu']:.6f} | {value['wall']:.6f} |")
for profile in result['profiles']:
    lines += ['', profile['path'], '', '| Function | Calls | Own elapsed s | Cumulative elapsed s |',
              '| --- | ---: | ---: | ---: |']
    for item in profile['functions'][:25]:
        assert Path(item['file']).is_file(), item['file']
        label = item['file'] + ':' + item['function']
        lines.append(f"| {label} | {item['calls']} | {item['own_elapsed']:.6f} | {item['cumulative_elapsed']:.6f} |")
(case / 'function-costs.md').write_text('\n'.join(lines) + '\n')
print(json.dumps({'callbacks': len(callbacks), 'profiles': [p['path'] for p in profiles]}, indent=2))
