"""Write the 6065/pin-comparison handoff from saved local evidence, 2026-11-13.
Inputs: source Git history, owned test XML/logs and replay manifest. Outputs:
the assigned Markdown/JSON handoff, with computed pins. No external actions.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parents[2]
E = R.parent
W = E / 'codex-native-recorder-env-20261113'
S = E / 'scratch-h3-recorder-20261113'
OUT = R / 'notes/development_efficiency_20261111/handoffs/codex-h3-recorder-env-and-pin-comparison-20261113'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
def git(*args): return subprocess.check_output(['git', '-C', str(W), *args], text=True).strip()
cohorts = {}
for folder in sorted((S / 'tests').iterdir()):
    if not folder.is_dir(): continue
    row = {'path': str(folder), 'complete': (folder / 'outcome.json').is_file()}
    for name in ('plan.json', 'outcome.json', 'pytest.xml', 'pytest.log'):
        if (folder / name).is_file(): row[name] = pin(folder / name)
    if row['complete']: row['outcome'] = json.loads((folder / 'outcome.json').read_bytes())
    if (folder / 'pytest.xml').is_file():
        cases = ET.parse(folder / 'pytest.xml').findall('.//testcase')
        row['counts'] = {'tests': len(cases), 'failed': sum(c.find('failure') is not None for c in cases),
            'errors': sum(c.find('error') is not None for c in cases), 'skipped': sum(c.find('skipped') is not None for c in cases)}
    cohorts[folder.name] = row
line_path = next((S / 'tests/recorder-focused-01/cases').glob('*/recorder-line.txt'))
line = line_path.read_text().removesuffix('\n')
protected = {}
for path in ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
        'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
        'src/data_sheets_schema/native_subscription_guard.py'):
    before = subprocess.check_output(['git', '-C', str(W), 'show', '8760de5ef:' + path])
    actual = (W / path).read_bytes()
    assert actual == before
    protected[path] = sha(actual)
report = {'status': 'Part 1 committed; validation and Part 2 design ruling pending',
    'branch': git('branch', '--show-current'), 'head': git('rev-parse', 'HEAD'),
    'base': git('rev-parse', '8760de5ef'), 'fetch': 'Attempted as assigned; GitHub DNS resolution failed. No publication.',
    'commits': git('log', '--reverse', '--format=%H %s', '8760de5ef..HEAD').splitlines(),
    'part1_commit': git('rev-parse', 'f57ac61da'), 'recorder_line': line,
    'recorder_line_characters': len(line), 'recorder_line_bytes': len(line.encode()),
    'recorder_line_evidence': pin(line_path), 'line_scope': 'Exact synthetic native26 model-facing line from the saved test; production paths remain registration-specific.',
    'model_facing_changes': ['recorder command in initial instruction', 'registered helper command table',
        'recorder command in tool policy and Bash allow rules', 'command guidance appended to the base system instructions',
        'derived instruction/system/command hashes in stage requests'],
    'supporting_changes': ['permission expectation recorder command and environment', 'production source pins'],
    'part2': {'status': 'design ruling requested; no gate implemented',
        'conflict': 'Existing production verified() reconstructs through pinned source execution and requires its exact checkout; data-only parsing is not equivalent validation.',
        'evidence': ['native_execution_registration_v2.py:_wire,verify_preparer,verified,_consumer',
            'native_execution_authority_v2.py:verified_source_module', 'native_shared_registration_orchestration.py:verified'],
        'choices': ['Add separately reviewed data-only production packet validation', 'Permit isolated existing production validation before data-only comparison'],
        'script_sha256': None, 'data_sha256': None, 'demonstrations': 'Not run; no equivalence claim.'},
    'part3': {'status': 'not started; ordered after Part 2'}, 'cohorts': cohorts,
    'protected_and_guard_v1_sha256': protected,
    'limitations': ['No real native binary, provider, model, permission probe, capture or launch was run.',
        'Only assigned CI groups investigated; the remaining CI failures and timed-out shards are not cleared.',
        'fixture-fixes cohort is non-acceptance: HEAD changed during a genuine registration test; fixed-ci-export replaces it.',
        'First merged export omitted Git metadata; merged-failure-git replaces its publication results.']}
for name in ('recorder-replay-01', 'recorder-replay-02'):
    p = S / name / 'manifest.json'
    if p.exists(): report.setdefault('replay', {})[name] = {'pin': pin(p), 'value': json.loads(p.read_bytes())}
OUT.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
text = f'''# Helper 3 recorder environment and pin comparison

Part 1 commit: `{report['part1_commit']}` on `{report['branch']}`. Status: {report['status']}.

The exact saved synthetic model-facing recorder line is {len(line)} characters ({len(line.encode())} UTF-8 bytes), excluding its newline:

```bash
{line}
```

The new ending is `--render-spec-env D4D_RENDER_SPEC --prompt-text-env D4D_LAUNCH_INSTRUCTION`. The controller supplies the JSON. The recorder admits only the literal variable name, rejects missing/empty values and conflicting options, and retains the existing reconstruction and exact instruction checks. The historical JSON option remains supported.

The 2282 notes show a literal environment-variable name was admitted while shell expansion was refused. This command uses no expansion and no inline JSON; an apostrophe inside the specification therefore never enters the command. Other independently supplied command paths still retain their existing spelling constraints. No runtime-permission admission is claimed without a real authorized probe.

Changed model-facing artifacts: {', '.join(report['model_facing_changes'])}. Permission expectation/environment and source pins are supporting changes. Replay confirmation is pending unless the companion JSON contains completed replay evidence; no claim is made from an unproduced snapshot.

## CI triage and launch carry

The baseline readback file passed 15 tests. The merged export reproduced all eight closed-wire failures: the component fixture was intentionally incomplete, and the new diagnostic preflight checks that shape. The repair supplies the closed wire with explicit placeholders; all production checks and existing assertions remain intact. The failure-publication file did not exist at the baseline. At the merged head, its seven tests pass in isolation once local Git metadata is supplied; the reported foreign-origin failure depends on broader collection/prior-state. The isolation repair uses the established fixture, with a historical collection import included in the fixed export run.

Preserved original repairs `48cb2d1f494add9903851af3c3babce31213af79` and `ef193e4eabc65a1c7ab39ecc64ad2945889f3416`; added H3-LR1 as `a22c51a9d082cad64eccb64c2de900b32e8e2630`, without rewriting. Their carried hashes and the two separate CI fixture commits are below. Fetch was attempted but failed to resolve GitHub; base is the locally available published `8760de5efe88b5af62e9d77e6335fa7e248017b6`.

'''
text += '\n'.join('- `' + item + '`' for item in report['commits']) + '\n\n## Saved checks\n\n'
for name, row in cohorts.items():
    text += '- ' + name + ': ' + json.dumps(row.get('counts', {'complete': row['complete']})) + '\n'
text += '''
The initial merged publication reproduction lacked Git metadata. The working-tree fixture run changed HEAD during registration reconstruction and is not acceptance. Both are retained, not relabelled as passes. The stable fixed export is the acceptance rerun.

## Part 2 decision required

No pin-comparison gate or allowlist is presented. The existing production verifier loads the pinned consumer source through `_consumer` and `verified_source_module`, rederives preparation, and requires its exact checkout. Calling it violates the requested prohibition on executing either input tree; substituting a structural parser would silently weaken validation. A ruling was requested: add separately reviewed data-only production packet validation, or permit isolated existing production validation before a data-only comparison. No self/other-project/prompt/binary/floor equivalence demonstrations are claimed. Script/data hashes are therefore absent.

Part 3 has not started; it follows Part 2. The four protected files and guard v1 match the base byte for byte (computed hashes in JSON). No real native binary, provider/model call, probe, capture, reservation, push or GitHub write. Synthetic tests write only their own evidence. Other CI failures and cancelled shards remain untriaged here.
'''
assert '@' not in text
OUT.with_suffix('.md').write_text(text)
print(json.dumps({suffix: pin(OUT.with_suffix(suffix)) for suffix in ('.md', '.json')}, indent=2))
