"""Issue 6233, 2026-11-14: persist the measured baseline before any fix.

Inputs: assigned scratch summary JSON/Markdown and actual callback artifacts.
Outputs: baseline verification JSON, assigned handoff, printed measured extrema.
"""
import hashlib
import json
from pathlib import Path
import sys

scratch = Path(sys.argv[1])
handoff = Path(sys.argv[2])
data = json.loads((scratch / 'callback-summary.json').read_text())
case = next(item for item in data if item['case'] == 'correction-canary2')
rows = case['rows']
observer = [r for r in rows if r['event_type'] == 'control_request' and r['work'] == '_observe_event' and not r['unwound']]
early = [r for r in observer if r['calls'] <= 10]
largest = sorted(observer, key=lambda row: row['thread_cpu'], reverse=True)[:2]
attempt = Path(rows[-1]['timing_directory'])
transcript = [json.loads(line) for line in (attempt / 'transcript.jsonl').read_text().splitlines()]
for row in rows:
    event = transcript[row['line'] - 1]
    assert event['type'] == row['event_type']
    if row['event_type'] == 'control_request':
        assert event['request']['input']['tool_use_id'] == row['tool_use_id']
        assert event['request']['input']['tool_name'] == row['tool']
    assert all(row[key] >= 0 for key in ('thread_cpu', 'process_cpu', 'wall'))
timing, malformed = [], []
for number, line in enumerate((attempt / 'host-controller-timing.jsonl').read_text().splitlines(), 1):
    try:
        timing.append(json.loads(line))
    except ValueError as error:
        malformed.append({'line': number, 'error': str(error)})
persisted = [r for r in timing if r.get('kind') == 'callback_cpu']
sources = [Path(case['source']), attempt / 'transcript.jsonl', attempt / 'host-controller-timing.jsonl']
proof = {'early_observer_cpu_min': min(r['thread_cpu'] for r in early),
         'early_observer_cpu_max': max(r['thread_cpu'] for r in early),
         'largest_callbacks': largest, 'fit': case['fits'], 'verified_timing_rows': len(rows),
         'combined_timing_malformed_rows': malformed, 'combined_timing_matches': persisted == rows,
         'sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}}
proof_path = scratch / 'baseline-verification.json'
proof_path.write_text(json.dumps(proof, indent=2) + '\n')
proof = json.loads(proof_path.read_text())
peak = proof['largest_callbacks'][0]
text = f"""Yes: measured observer CPU grows with the recorded history; contention alone does not explain it. This is the baseline, persisted before any production fix. Function profiles, the fix, and the three final public results remain pending.

In the isolated correction run, the first ten PreToolUse observers cost {proof['early_observer_cpu_min']:.6f} to {proof['early_observer_cpu_max']:.6f} thread CPU seconds. Callback {peak['calls']} costs {peak['thread_cpu']:.6f} thread CPU seconds, with {peak['records'].get('observation', 0)} observation captures and {peak['records'].get('record', 0)} stage-record captures. Classifier measurements and all other ordered observer barriers are shown below. The two largest measured PreToolUse observer calls are {[row['calls'] for row in proof['largest_callbacks']]}. Linear fits are descriptive across changing stages, not a claim of a universal linear law or a controlled causal estimate.

The diagnostic verified {proof['verified_timing_rows']} independent callback-cpu.jsonl rows against their exact transcript lines and tool identities. The combined host-controller-timing.jsonl is defective: {len(proof['combined_timing_malformed_rows'])} malformed rows were found. The initial diagnostic appended through a separate descriptor, while the original controller descriptor did not use append mode and could overwrite those additions. The malformed evidence is preserved; no repair is presented as original evidence. The independent callback CPU file is intact and supplies this baseline. The diagnostic now uses Timing.record for supplemental controller rows, and needs a fresh persistence canary. Proof and computed source hashes: {proof_path}.

Saved attempts remain read-only. A direct adapter-construction probe stopped in get_type_hints with NameError for ArtifactPin before observation; the traceback is in {scratch / 'saved-boundary.json'}. That cold diagnostic boundary is not a production-defect claim. Independently, the live adapter requires one-use admission, and initialization refuses an existing session binding. Replaying observation would publish into saved absolute stage paths. The assignment's fresh synthetic fallback was used, with the real NativeControl._observe_event and NativeControl._classify_frame functions and no substituted production callable.

The first diagnostic canary failed before pytest execution because PY_UNWIND cannot return monitoring.DISABLE. The corrected canary ran the actual public correction test. Its initial instrumentation counts regular captures but does not count live transcript capture extents; these cells explicitly say not instrumented. The enhanced diagnostic adds live-stream capture counts and per-function CPU. No missing count is treated as zero.

The guarded public test reserves cProfile's slot. A separate diagnostic can invoke the same public synthetic API and profile selected real callbacks without entering or changing that test-only guard. Such a run is a profiling diagnostic, not a claimed public-test pass. Its cProfile times use the built-in elapsed timer; independent thread CPU clocks remain the performance measure, and profiled callbacks are excluded from slope fits.

No production file, protected file, pin, deadline or acceptance rule has changed. No GitHub write or push has occurred. The host-load reading is saved in {scratch / 'host-load-during-canary.txt'}.

Proposed implementation, pending profiles: keep a separate verified-prefix owner keyed weakly by the actual active Admission in native_shared_capture_orchestration. Standalone helpers and final strict replay remain uncached. Before reuse, freshly capture every earlier referenced artifact and both stream prefixes, compare exact pins and prefix hashes, require the ordered journal-record and observation prefixes to extend unchanged, and retain all source/admission reconstruction. Refuse a changed prefix rather than silently invalidating and accepting its replacement. Resume observation causal-state checks only for the new suffix. Reuse stage decisions only for identical verified inputs, and consider compact checkpoints for already checked stages if profiles show historical stage reconstruction dominates. Do not put accepted verification state in the existing pure receipt-catalog cache. Mutations to old transcript bytes, old journal content, old stage records and old observations must be tested at the next callback boundary. No such optimization has been applied yet.

The correction pytest completed with a deadline failure. Its shell wrapper subsequently returned status 2 because the running shell script had been edited while Bash was still consuming it. The recovered wrapper status is recorded separately in correction-canary2/launcher-exit-status-recovered.txt; it is not represented as pytest's exit status. The fresh profiling canary's launcher is left unchanged while it runs.

Reproduce the table with the assigned interpreter and PYTHONPATH, running scripts/adhoc/summarize_callback_growth_20261114.py with the assigned scratch path. This handoff was generated by scripts/adhoc/write_callback_baseline_handoff_20261114.py from that saved JSON and Markdown. The launcher is scripts/adhoc/run_callback_growth_20261114.sh; it uses the same public test nodes as run_bash_timeout_case_20261114.sh, with assigned scratch and diagnostic instrumentation.

"""
text += (scratch / 'callback-summary.md').read_text()
assert chr(64) not in text
handoff.write_text(text)
print(json.dumps({'largest_callbacks': [row['calls'] for row in largest],
                  'early_cpu': [proof['early_observer_cpu_min'], proof['early_observer_cpu_max']],
                  'peak_cpu': peak['thread_cpu'], 'verified_rows': len(rows),
                  'handoff_sha256': hashlib.sha256(handoff.read_bytes()).hexdigest()}, indent=2))
