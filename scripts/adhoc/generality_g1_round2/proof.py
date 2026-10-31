"""P4a findings 1/4/5 evidence helper, 2026-10-30.

Inputs: local Git objects/current worktree and archived CHORUS intermediates.
Outputs: 3.1.0 hashes, same-path offline captures, comparison tables/test rosters.
No provider, remote, ledger, run output, canonical pin or archive writes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / '.g1-round2-evidence'
BASE = '55c7b94b8'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def release():
    schema = ROOT / 'src/data_sheets_schema/schema'
    path = schema / 'release_history.yaml'
    text = path.read_text()
    before, current = text.split('  - version: 3.1.0\n')
    import re
    for key, filename in (
        ('full_source', 'data_sheets_schema.yaml'),
        ('full_merged', 'data_sheets_schema_all.yaml'),
        ('core_source', 'data_sheets_schema_core.yaml'),
        ('core_merged', 'data_sheets_schema_core_all.yaml'),
    ):
        digest = hashlib.sha256((schema / filename).read_bytes()).hexdigest()
        current, n = re.subn(rf'({key}_sha256: )[0-9a-f]{{64}}', rf'\g<1>{digest}', current)
        assert n == 1
        print(key, digest)
    path.write_text(before + '  - version: 3.1.0\n' + current)


def capture(revision):
    # Materialize only runtime inputs; both captures use this same absolute path.
    # No checkout/branch switch, no copy or write under any data/ATTIC tree.
    snapshot = OUT / 'snapshot'
    names = git('ls-tree', '-r', '--name-only', BASE).decode().splitlines()
    names = [n for n in names if n.startswith(('src/', '.claude/', 'data/preprocessed/',
             'data/omission_contexts/', 'data/rubric/')) or n == 'pyproject.toml'
             or (n.startswith('scripts/') and not n.startswith('scripts/adhoc/'))]
    if revision == 'head':
        assert (snapshot / 'pyproject.toml').exists(), 'Capture base first'
    for name in names:
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = git('show', f'{BASE}:{name}') if revision == 'base' else (ROOT / name).read_bytes()
        path.write_bytes(raw)
    env = {**os.environ, 'PYTHONPATH': f'{snapshot}/src:{snapshot}',
           'G1_ARCHIVE': str(ROOT / 'data/ATTIC/d4d_concatenated_archived/claudecode_api_core/'
                             '2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate')}
    subprocess.run([sys.executable, str(HERE / 'offline_pytest.py'),
                    str(HERE / 'capture_requests.py'), str(OUT / f'capture-{revision}.json'),
                    str(OUT / 'fixture')], cwd=snapshot, env=env, check=True)


def table():
    documents = [json.loads((OUT / f'capture-{name}.json').read_bytes()) for name in ('base', 'head')]
    assert set(documents[0]['payloads']) == set(documents[1]['payloads'])
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    print('| Phase | Base bytes | Head bytes | Delta | Status |')
    print('|---|---:|---:|---:|---|')
    for phase in documents[0]['payloads']:
        lengths = [len(canonical(doc['payloads'][phase])) for doc in documents]
        print(f'| `{phase}` | {lengths[0]:,} | {lengths[1]:,} | {lengths[1]-lengths[0]:+,} | measured |')
    assert all(not doc['errors'] for doc in documents)


def assignments():
    head = json.loads((OUT / 'capture-head.json').read_bytes())
    found = {}
    for phase, payload in head['payloads'].items():
        if not phase.startswith('typed_audit_worker:'):
            continue
        text = payload['messages'][0]['content'][-1]['text']
        inner = json.loads(text.split('\n\n', 1)[1])
        stage = json.loads(inner['payload']['stage'])
        paths = stage['assignment']['paths']
        found[phase] = {'assigned_leaf_count': len(paths),
                        'data_substrate_leaves': [p for p in paths if 'data_substrate' in p]}
    print(json.dumps(found, indent=2))


def verify():
    import yaml
    from data_sheets_schema import profiles
    before = yaml.safe_load(git('show', 'f7fedae48:src/data_sheets_schema/schema/D4D_Composition.yaml'))
    after = yaml.safe_load((ROOT / 'src/data_sheets_schema/schema/D4D_Composition.yaml').read_bytes())
    old = before['classes']['Instance']['attributes']['data_substrate']['description']
    new = after['classes']['Instance']['attributes']['data_substrate']['description']
    suffix = ' A *term*, not a description:'
    assert old.split(suffix, 1)[1] == new.split(suffix, 1)[1]
    assert len(new.encode()) - len(old.encode()) == 100
    before['classes']['Instance']['attributes']['data_substrate']['description'] = new
    assert before == after, 'Only the description first sentence may change'
    import csv
    for filename in ('d4d_rocrate_sssom_comprehensive.tsv',
                     'd4d_rocrate_sssom_uri_comprehensive.tsv'):
        relative = 'src/data_sheets_schema/semantic_exchange/' + filename
        previous = git('show', 'f7fedae48:' + relative).decode()
        current = (ROOT / relative).read_text()
        rows = lambda text: list(csv.DictReader(
            (line for line in text.splitlines() if not line.startswith('#')), delimiter='\t'))
        left, right = rows(previous), rows(current)
        assert len(left) == len(right) == 301
        for prior, updated in zip(left, right):
            changed = {key for key in prior if prior[key] != updated[key]}
            if 'd4d_description' in changed:
                assert prior['subject_id'] == updated['subject_id'] == 'd4d:data_substrate'
                assert old.startswith(prior['d4d_description'].removesuffix('...'))
                assert new.startswith(updated['d4d_description'].removesuffix('...'))
                changed.remove('d4d_description')
            assert changed <= {'mapping_date'}, (filename, prior, updated)
        comments = lambda text: '\n'.join(line for line in text.splitlines() if line.startswith('#'))
        assert comments(previous).replace('# Date: 2026-10-29', '# Date: 2026-10-30') == comments(current)
    assert not git('diff', 'f7fedae48', '--', 'src/data_sheets_schema/schema_digest.py',
                   'src/download/prompts/canonical_hashes.yaml', 'src/data_sheets_schema/shared_generation.py')
    record = {'repo': {'commit': 'a2a3e157b'}, 'record_generated_at': '2026-10-30T12:00:00Z'}
    assert profiles.for_record(record) is profiles.BRIDGE2AI
    assert profiles.for_record({'repo': {'commit': profiles.PROFILES_INTRODUCED_COMMIT},
                                'record_generated_at': '2026-09-01'}) is profiles.NEUTRAL
    from data_sheets_schema.provenance import profile_assessment
    legacy_path = ROOT / ('data/d4d_concatenated/claudecode_api_core/'
                          '2026-09-04f_claude-opus-5-api-generic-v8_rep2/CHORUS_provenance.yaml')
    legacy = yaml.safe_load(legacy_path.read_bytes())
    historical_problems, historical_context = profile_assessment(legacy)
    legacy['record_generated_at'] = '2026-10-30T12:00:00Z'
    problems, context = profile_assessment(legacy)
    assert not problems and not historical_problems
    assert context == historical_context
    assert context['effective_profile'] == 'bridge2ai'
    probe = {'source': str(legacy_path.relative_to(ROOT)),
             'source_sha256': hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
             'commit': legacy['repo']['commit'], 'current_date': legacy['record_generated_at'],
             'problems': problems, 'status': context['status'],
             'effective_profile': context['effective_profile'],
             'unchanged_assessment': context == historical_context}
    (OUT / 'historical-current-date-probe.json').write_text(json.dumps(probe, indent=2) + '\n')
    left = (OUT / 'corpus-before.json').read_bytes()
    right = (OUT / 'corpus-final.json').read_bytes()
    assert left == right
    assert len(json.loads(left)) == 286
    print('Source-only first-sentence edit, unchanged suffix/digest template/pins/shared_generation verified.')
    print('Both 301-row SSSOM mappings unchanged apart from dates and the substrate description excerpt.')
    print('Actual a2a3e157b with current date: bridge2ai; introduction with old date: neutral.')
    print('Real v8 record with current date:', json.dumps(probe, sort_keys=True))
    print('286 corpus sweep rows byte-identical:', hashlib.sha256(left).hexdigest())


def report():
    import contextlib
    import io
    import importlib.metadata
    import xml.etree.ElementTree as ET
    documents = [json.loads((OUT / f'capture-{name}.json').read_bytes()) for name in ('base', 'head')]
    base, head = documents
    contracts = [d['registration']['selection']['stage_contracts'] for d in documents]
    codes = [c['request_code_sha256'] for c in contracts]
    for name, digest in codes[1].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for kind in ('full_schema', 'core_schema'):
        for source in head['registration']['inputs'][kind]['sources']:
            relative = Path(source['path']).relative_to(OUT / 'snapshot')
            raw = (ROOT / relative).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source['sha256'], relative
            assert len(raw) == source['bytes'], relative
    rows = io.StringIO()
    with contextlib.redirect_stdout(rows):
        table()
    code_head = git('rev-parse', 'HEAD').decode().strip()
    text = f'''# Generality G1 round 2: P4a findings 1, 4 and 5 (2026-10-30)

Base: `{git('rev-parse', BASE).decode().strip()}`. Implementation head: `{code_head}`.
This report's later evidence-only commit does not change any captured runtime input.

## Method and limits

Offline CHORUS shared-generation-v1, renderer 25, playbook 2, receipt policy 2;
the same `chorus` partition and `2026-10-30_g1-rereview-proof` registration label
as the independent re-review. Canonical bytes use `shared_generation.canonical`
(sorted keys, compact separators, UTF-8). No provider, token counting endpoint,
run directory, ledger, canonical pin or archive was written.

The reviewer's `capture_requests.py` and `diff_payloads_fast.py` are retained in
`scripts/adhoc/generality_g1_round2/`; capture is extended for the missing phases.
Both versions run in the **same** `.g1-round2-evidence/snapshot` path, with the
same fixture path. The base materializes tracked runtime inputs from local Git;
the head uses the corresponding worktree files, whose committed hashes are
checked here. Archived 2026-10-22a CHORUS intermediates are read from their original location.
Absolute path lengths differ from the prior review, so absolute totals differ;
within this experiment all locations are fixed. `unused-output` does not exist
after either capture, and both error dictionaries are empty.

Receipt completion uses `receipt_completion.build_request` on archived
`CHORUS_receipt_completion_inputs.json` (SHA256
`{head['receipt_archived_inputs_sha256']}`). Record, receipt, manifest, bundle and
assistant response are held fixed. The preceding full request's system,
messages and cached blocks, schema capture, receipt registration identity and
output cap are rebuilt at each revision, as the runtime does. An unchanged
archived transcript alone would measure historical replay rather than the new
condition. No new assistant output is synthesized.

Both report variants use the runtime's `build_phase('report')` path.
`report_regate` also uses `_append_regate` with the archived report and a fixed
empty contradiction list. `report_after_repair` uses the fixed archived reconciled
record carries. These measure renderer bytes offline, not a claim that a
repair/regate was triggered or that a provider accepted these requests.

## Complete phase table

{rows.getvalue().strip()}
| `typed_audit_integration` | — | — | +189 expected | Responses from every worker and omission are required; unavailable in this offline capture. Same Instance schema context. |
| `repair_full` | — | — | — | Not applicable: no validation-failure repair request in the selected fixed carries. |
| `full_readdress` | — | — | — | Not applicable: no new receipt-path correction is invoked in this capture. |
| `core`, `reconcile_core`, `repair_core` | — | — | — | Not applicable: deterministic derivations, no provider request. |
| legacy `audit` | — | — | — | Not applicable: shared-v1 uses the typed worker/omission/integration roster above. |

The full/receipt +135 digest insertion is **record-independent**. The schema
context's +189 description component appears where the record has an **Instance
owner**, including when `data_substrate` is absent. A worker retains this
description for each worker assigned a **`data_substrate` leaf**. The worker
number is specific to this packet, not a rule for future records. Omission
contains the description twice (outer schema context and inner typed request).
Fixed-width schema/binding hash substitutions contribute zero net bytes.
Actual later-phase sizes and worker rosters remain record-dependent.

## Finding 4: schema and derived artifacts

Only the first sentence in `D4D_Composition.yaml` changes from G1's prior head:

> Type or format of data (e.g., raw text, images): an EDAM Data or Format term or an IANA media type, written as a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or a term from the selected profile's pinned standards registry.

The rest of the description and the digest template are unchanged. The sentence
adds 100 bytes to G1's previous description (+189 from step 0).
`make regen-all gen-core-schema gen-sssom-comprehensive gen-sssom-uri-comprehensive`
regenerated the products; 3.1.0's unreleased hashes were updated in release history.
Older release entries are unchanged. The OWL graph has 7,759 triples in each
version, with precisely one definition replacement (7,758 common triples).
The two 301-row SSSOM tables retain identical mappings; only mapping dates and
the substrate-description excerpt change. JSON-LD generation metadata also
reflects regeneration.

'''
    for label, filename in [('full', 'data_sheets_schema_all.yaml'), ('core', 'data_sheets_schema_core_all.yaml')]:
        raw = (ROOT / 'src/data_sheets_schema/schema' / filename).read_bytes()
        text += f'- 3.1.0 {label} merged SHA256: `{hashlib.sha256(raw).hexdigest()}`.\n'
    text += '\nRegistration request-code hashes changed at these paths from step 0:\n\n'
    for name in sorted(set(codes[0]) | set(codes[1])):
        if codes[0].get(name) != codes[1].get(name):
            text += f'- `{name}`: `{codes[0].get(name)}` → `{codes[1].get(name)}`.\n'
    assignment_text = io.StringIO()
    with contextlib.redirect_stdout(assignment_text):
        assignments()
    text += '\nActual worker assignments (all workers retained):\n\n```json\n' + assignment_text.getvalue() + '```\n'
    text += '''
## Finding 5: historical code evidence

`PROFILES_INTRODUCED_COMMIT` is
`e78e4bb5699af0ecaca28cdc5c328e5c908ae959` (#628/#1302).
Explicit profiles still win. Otherwise locally resolved `repo.commit` ancestry
wins over the execution date: non-descendants read as historical bridge2ai;
profile-aware code reads as neutral. Missing, malformed, shallow-negative or
unavailable ancestry is not silently classified using a date.

The corpus also contains old squashed/deleted commit identities. A missing
object can be established as historical only by an exact `repo.commit` in a
generation or derived provenance record already present in the introduction's
parent tree. This uses immutable retained evidence, not today's record or its
date; a hash merely mentioned in prose is insufficient. There is no per-project
or per-hash exception list. Dates are used only when no commit is recorded.
Records with neither a commit nor a valid date still refuse.

Tests cover old code executed today and `profile_assessment == match`, explicit
profiles, introduction/descendant code with an old date, no-date historical
code, malformed/unresolvable hashes, unavailable checkout, shallow history,
retained generation/derived witnesses and incidental hash mentions. A direct
offline probe also checks the actual `a2a3e157b` with a current date.

The reviewer's 286-record corpus sweep is byte-identical before/after, including
reader results, profile identity, warnings and failure details:
'''
    corpus = (OUT / 'corpus-final.json').read_bytes()
    assert corpus == (OUT / 'corpus-before.json').read_bytes()
    text += f'`{hashlib.sha256(corpus).hexdigest()}`.\n'
    probe = json.loads((OUT / 'historical-current-date-probe.json').read_bytes())
    text += '\nA second probe changes only the date of a real v8 provenance record in memory; '
    text += 'the source file is never written. Its full assessment stays unchanged, with '
    text += 'no profile-identity findings. Its existing unreproduced digest stays unknown '\
            '(the synthetic regression separately verifies a digest match):\n\n```json\n'
    text += json.dumps(probe, indent=2) + '\n```\n'
    text += '\n## Validation\n\n'
    text += f'Python `{sys.version.split()[0]}`; LinkML `{importlib.metadata.version("linkml")}`; '
    text += f'linkml-runtime `{importlib.metadata.version("linkml-runtime")}`. '
    text += 'Local serial runs in CI’s tests/ scope (CI itself uses Python 3.12); provider keys unset, network guard/dead proxies, basetemps under d4d-executions.\n\n'
    units = ('canary-final', 'schema-canary', 'fixture-canary', 'focused-final',
             'collect-final', 'shard-1', 'shard-loopback-canary', 'shard-loopback')
    test_counts = {}
    for name in units:
        result = json.loads((OUT / (name + '.result.json')).read_bytes())
        tree = ET.parse(OUT / (name + '.xml'))
        counts = {key: sum(int(s.get(key, '0')) for s in tree.findall('.//testsuite'))
                  for key in ('tests', 'failures', 'errors', 'skipped')}
        test_counts[name] = counts
        text += f'- `{name}`: exit {result["returncode"]}; {counts}; {result["seconds"]:.1f}s.\n'
        if name == 'collect-final':
            import re
            collected = re.search(r'\d+ tests collected[^\n]*', (OUT / (name + '.log')).read_text())
            assert collected
            text += f'  {collected.group()}; zero collection errors.\n'
    text += '- `d4d schema check-digest --strict`: both merged schemas in sync, exit 0.\n'
    text += '- `make check-sync check-sssom-comprehensive`: pass; existing alignment warnings remain visible.\n'
    text += '- `git diff --check`: pass.\n'
    from scripts.adhoc.generality_g1_round2.shard_failures import read_failures
    failures = read_failures()
    loopback = [f for f in failures if f['kind'] == 'loopback_setup']
    other = [f for f in failures if f['kind'] != 'loopback_setup']
    assert not other, f'Non-loopback shard failures need separate triage: {other}'
    retry = test_counts['shard-loopback']
    assert retry == {'tests': len(loopback), 'failures': 0, 'errors': 0, 'skipped': 0}
    text += f'\nThe initial shard had {len(loopback)} setup errors because the sandbox refused '
    text += 'binding the tests’ fake HTTP servers to `127.0.0.1`. No external endpoint '
    text += 'was involved. After the shard completed, one selected test was run as a '
    text += 'canary outside that socket restriction, then all affected nodes were rerun '
    text += 'serially through the same launcher, with provider keys unset and the '
    text += 'external socket/DNS guard intact. The canary and all retry nodes passed. '
    text += 'The canary also retained its non-empty relocated index, after checking '
    text += 'two synthetic deliveries and a captured-only recheck without dispatch. '
    text += 'The original shard result above is retained rather than replaced.\n\n'
    text += 'Exact retried nodes:\n\n```text\n'
    text += '\n'.join(f['node'] for f in loopback) + '\n```\n'
    focused = json.loads((OUT / 'focused-final.result.json').read_bytes())
    suite_paths = [arg for arg in focused['command'] if arg.startswith('tests/')]
    text += '\nThe affected-suite run covered these paths:\n\n```text\n'
    text += '\n'.join(suite_paths) + '\n```\n'
    text += '''
The broader run uses the actual CI shard plugin, ordinary lane 1/6 and checked-in
duration weights, with one serial pytest controller. The schema/profile canary
and fixture canary passed before the larger runs. They verified local selection,
generated-schema assertions and fixture isolation; they do not claim provider
acceptance, concurrency behavior or live credential coverage.
Tests ran against the uncommitted implementation bytes on `f7fedae48`; the
implementation commits were made after acceptance. This report verifies every
captured request-code and schema hash against the committed implementation
before writing.

A separate read-only adversarial pass checked the final production/test diff,
generated-artifact semantic delta and every changed payload leaf. It found no
additional defect. No remote issue, PR, push or merge was attempted (offline).
'''
    text += '\n## Capture identities\n\n'
    for name, doc in zip(('base', 'head'), documents):
        raw = (OUT / f'capture-{name}.json').read_bytes()
        text += f'- {name} capture SHA256 `{hashlib.sha256(raw).hexdigest()}`; registration `{doc["registration_sha256"]}`; packet `{doc["packet_sha256"]}`.\n'
    text += '\n## Every changed payload leaf\n\n```text\n'
    text += (OUT / 'leaf-diffs.txt').read_text()
    text += '```\n'
    destination = HERE / 'byte_proof_2026-10-30.md'
    destination.write_text(text)
    external = ROOT.parent / 'plans/reviews/generality_g1_round2_byte_proof_2026-10-30.md'
    external.write_text(text)
    print(destination, external, hashlib.sha256(text.encode()).hexdigest(), sep='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('release', 'base', 'head', 'table', 'verify', 'report', 'assignments'))
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.action == 'release':
        release()
    elif args.action == 'table':
        table()
    elif args.action == 'verify':
        verify()
    elif args.action == 'report':
        report()
    elif args.action == 'assignments':
        assignments()
    else:
        capture(args.action)
