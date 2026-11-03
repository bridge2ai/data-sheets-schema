"""Exact nested canonical-JSON delta accounting for BC1/P4a1, 2026-10-31.

Inputs: before/after capture payloads. Outputs: every changed leaf, size summary
and BC1 report. Expands only embedded JSON whose original bytes are canonical;
accounts for each additional JSON string-escaping layer and added-key commas.
"""
from dataclasses import dataclass
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.bc1-byte-evidence'
REPORT = ROOT.parent / 'plans/reviews/bc1_route_byte_proof_2026-10-31.md'

def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

@dataclass
class Embedded:
    prefix: str
    value: object

def expand(value):
    if isinstance(value, dict):
        return {key: expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand(item) for item in value]
    if isinstance(value, str):
        starts = [value.find(ch) for ch in ('{', '[') if ch in value]
        if starts:
            start = min(starts)
            try:
                parsed = json.loads(value[start:])
                if canon(parsed).decode() == value[start:]:
                    return Embedded(value[:start], expand(parsed))
            except ValueError:
                pass
    return value

def collapse(value):
    if isinstance(value, Embedded):
        return value.prefix + canon(collapse(value.value)).decode()
    if isinstance(value, dict):
        return {key: collapse(item) for key, item in value.items()}
    if isinstance(value, list):
        return [collapse(item) for item in value]
    return value

def escaped(raw, depth):
    for _ in range(depth):
        raw = canon(raw.decode())[1:-1]
    return raw

def classify(path, before, after):
    if path.endswith('/annotations') and 'data_substrate/definition' in path:
        return 'termSources_core' if '/core_catalog/' in path else 'termSources_full'
    if path.endswith('/description') and 'data_substrate' in path:
        return 'description_core' if '/core_catalog/' in path else 'description_full'
    if isinstance(before, str) and isinstance(after, str) and ' a term from EDAM Data, EDAM Format, IANA media types' in after:
        return 'digest'
    if 'sha256' in path or path.endswith('/bytes') or path.endswith('/md5'):
        return 'pins'
    if 'prefix' in path.lower() and 'EDAM' in path:
        return 'edam_prefix'
    return 'other'

def differences(a, b, path='payload', depth=0):
    if a == b:
        return []
    if isinstance(a, Embedded) and isinstance(b, Embedded) and a.prefix == b.prefix:
        return differences(a.value, b.value, path + '/@json', depth + 1)
    rows = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            at = path + '/' + key
            if key not in a or key not in b:
                present = b if key not in a else a
                value = collapse(present[key])
                raw = canon(key) + b':' + canon(value) + (b',' if len(present) > 1 else b'')
                delta = len(escaped(raw, depth)) * (1 if key not in a else -1)
                old, new = (None, value) if key not in a else (value, None)
                rows.append({'path': at, 'before': old, 'after': new, 'delta': delta,
                    'unescaped_fragment_bytes': len(raw), 'escaping_layers': depth,
                    'kind': classify(at, old, new), 'operation': 'add' if key not in a else 'remove'})
            else:
                rows.extend(differences(a[key], b[key], at, depth))
        return rows
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (old, new) in enumerate(zip(a, b)):
            rows.extend(differences(old, new, path + '/' + str(i), depth))
        return rows
    a, b = collapse(a), collapse(b)
    delta = len(escaped(canon(b), depth)) - len(escaped(canon(a), depth))
    return [{'path': path, 'before': a, 'after': b, 'delta': delta,
             'escaping_layers': depth, 'kind': classify(path, a, b), 'operation': 'replace'}]

before = json.loads((OUT / 'before/capture.json').read_bytes())
after = json.loads((OUT / 'after/capture.json').read_bytes())
assert not before['errors'] and not after['errors']
assert before['payloads'].keys() == after['payloads'].keys()
assert before['python'] == after['python'] and before['packages'] == after['packages']
assert before['audit_limits'] == after['audit_limits'] and before['calibration'] == after['calibration']
assert before['source_pins'].keys() == after['source_pins'].keys()
for path, expected_pin in before['source_pins'].items():
    if '/src/data_sheets_schema/schema/' not in path:
        assert after['source_pins'][path] == expected_pin, path
summary, leaf_text = [], []
for name, bp in before['payloads'].items():
    ap = after['payloads'][name]
    a_raw, b_raw = (ROOT / bp['path']).read_bytes(), (ROOT / ap['path']).read_bytes()
    for raw, metadata in ((a_raw, bp), (b_raw, ap)):
        assert len(raw) == metadata['bytes'] and hashlib.sha256(raw).hexdigest() == metadata['sha256']
    a, b = expand(json.loads(a_raw)), expand(json.loads(b_raw))
    assert canon(collapse(a)) == a_raw and canon(collapse(b)) == b_raw
    leaves = differences(a, b)
    delta = len(b_raw) - len(a_raw)
    assert sum(row['delta'] for row in leaves) == delta, (name, delta, leaves)
    kinds = {}
    for leaf in leaves:
        group = kinds.setdefault(leaf['kind'], {'count': 0, 'delta': 0, 'occurrence_sizes': []})
        group['count'] += 1
        group['delta'] += leaf['delta']
        group['occurrence_sizes'].append(leaf['delta'])
    summary.append({'name': name, 'before': len(a_raw), 'after': len(b_raw), 'delta': delta,
                    'scenario': ap['scenario'], 'kinds': kinds})
    stem = name.replace(':', '__')
    (OUT / ('diff_' + stem + '.json')).write_bytes(canon(leaves))
    leaf_text.append(f'=== {name}: {len(a_raw)} -> {len(b_raw)} ({delta:+d})')
    for leaf in leaves:
        leaf_text.append(f"{leaf['path']} | {leaf['kind']} | {leaf['delta']:+d} wire bytes | {leaf['escaping_layers']} embedding(s)")
        old, new = leaf['before'], leaf['after']
        if isinstance(old, str) and isinstance(new, str) and max(len(old), len(new)) > 3000:
            leaf_text.extend(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm='', n=1))
        else:
            leaf_text.extend(['  before: ' + repr(old), '  after:  ' + repr(new)])
(OUT / 'summary.json').write_bytes(canon(summary))
(OUT / 'leaf-diffs.txt').write_text('\n'.join(leaf_text) + '\n')
for row in summary:
    print(row['name'], row['before'], row['after'], row['delta'], row['kinds'])

def table(rows):
    lines = ['| Request | Before bytes | After bytes | Delta |',
             '|---|---:|---:|---:|']
    for row in rows:
        lines.append(f"| `{row['name']}` | {row['before']:,} | {row['after']:,} | {row['delta']:+,} |")
    return '\n'.join(lines)

def identity(doc, suffix):
    return doc['source_pins'][str(ROOT / 'src/data_sheets_schema/schema' / suffix)]['sha256']

primary = [row for row in summary if row['scenario'] not in
    ('visible_cap_ascii_scenario', 'visible_cap_measured_escape', 'visible_cap_escaped_bound')]
extra = [row for row in summary if row not in primary]
expected = {'data_sheets_schema_all.yaml': '9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da',
            'data_sheets_schema_core_all.yaml': '2bb8827c45a4dac40e834064a65c95cfc13d258b129c3aa1b9cbccba9ef624db'}
matches = {name: identity(after, name) == digest for name, digest in expected.items()}
kind_rows = []
for row in primary:
    values = []
    for kind, group in row['kinds'].items():
        sizes = sorted(set(group['occurrence_sizes']))
        values.append(f"{kind}: {group['count']} × {sizes[0]:+d}" if len(sizes) == 1 else f'{kind}: {group}')
    kind_rows.append(f"| `{row['name']}` | {'; '.join(values)} |")
annotation = next(row for row in summary if row['name'] == 'typed_audit_omission')['kinds']
full_annotation = annotation['termSources_full']['occurrence_sizes'][0]
core_annotation = annotation['termSources_core']['occurrence_sizes'][0]
omission_diff = json.loads((OUT / 'diff_typed_audit_omission.json').read_bytes())
unescaped_annotation = next(row['unescaped_fragment_bytes'] for row in omission_diff if row['kind'] == 'termSources_full')
assert not any('other' in row['kinds'] for row in summary), 'Unclassified changed leaf: inspect summary.json'
report = f'''# BC1 route byte proof for P4a amendment 1 — 2026-10-31

This is an offline schema-only paired comparison on BC1's actual request
renderer, using the archived 2026-10-22a CHORUS carries. It is not a composed
A21 launch registration, provider measurement, or evidence of accepted audit
responses. Canonical SDK-payload JSON is measured, excluding HTTP framing.

## Identities and prerequisite

- BC1 packet: `d00acf1e7d6d485abb4776f9ffb1cd12d2640baf`
  (`codex/wave7-bc1-packet-20261029`). Disposable local proof branch:
  `codex/bc1-route-byte-proof-20261031`.
- G1 schema source: `31a086e0ff0c6d247b733636e1fdaa995800ac6f`.
  Relevant changes: F6 `4574f72a4`, N7 `6e9a3545f`, final wording and release
  identity `93f01b228`. The first added the annotation/3.1.0 release, the second
  declared EDAM, and the third finalized the description and hashes.
- Before, schema **3.0.0**: full `{identity(before, 'data_sheets_schema_all.yaml')}`;
  core `{identity(before, 'data_sheets_schema_core_all.yaml')}`.
- After, schema **3.1.0**: full `{identity(after, 'data_sheets_schema_all.yaml')}`;
  core `{identity(after, 'data_sheets_schema_core_all.yaml')}`.
- Target match: full **{matches['data_sheets_schema_all.yaml']}**;
  core **{matches['data_sheets_schema_core_all.yaml']}**.
- Before registration SHA256 `{before['registration_sha256']}`;
  after `{after['registration_sha256']}`.

**Raw packet limitation:** registration on the untouched packet fails with
`shared-generation selected asset changed: .claude/commands/d4d-uniform-rules-v2.md`.
The failure is retained in `.bc1-byte-evidence/raw-packet-preflight/capture.json`.
As explicitly permitted, the already-reviewed
`notes/reviews/wave7_bc1_shared_generation_proposal_2026-10-29.diff` was applied
inside this scratch **before both captures**. Its SHA256 is
`274411de3448c32be0600bec33fd794bce747e24bffa7eff6dede01eb568c719`;
the resulting `shared_generation.py` SHA256 is
`94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d`.
It combines the existing six BC1 hooks with the reviewed A13/A14/D41 asset,
descriptor, schema-context and journal changes. This prerequisite is held
constant and contributes no before/after byte delta. Thus “before” here means
BC1's 3.0.0 packet with that disclosed renderability prerequisite, not a claim
that the unmodified packet rendered successfully.

No G1 runtime code was imported. In particular `schema_digest.py` already
matches G1 round 2 byte-for-byte, SHA256
`150a5f005ab1ed5fdf73f927559f15a3c7dbf34a0915ff2b83896991c1fcc095`.
Only `D4D_Composition.yaml`, `D4D_Base_import.yaml`, the full/core source version
files, and `release_history.yaml` were taken from G1. Makefile targets regenerate
the merged schemas and corresponding exported products. G1's unrelated
`d4d_generation_record.yaml`, `digest_inventory.yaml`, profile and API changes
were not copied.

## Registration and rendering method

`scripts/build_api_registrations.prepare_registration` selects CHORUS,
`partition='chorus'`, `bounded_carry_version=1`, fan-in 2, profile `bridge2ai`,
and `aggregate_input_tokens=4500000`. It runs the packet's ordinary BC1 sizing
and acceptance checks against the archived original full/core and effective
receipt. D63 is already in this packet: the exact integer ratio
`1185329 / 432784` (approximately 2.739 bytes/token), with D62's future-response
1.75 bytes/token and 1.25 escape factor. Both gated scenarios pass in both
conditions. No token-counting call is made. This `bridge2ai` registration needs
no G2 neutral-term parser change; none was applied.

The label, fixture path, scratch path, run date, generation placeholder and
all archive bytes are identical across the pair. Registration paths are fixed;
canonical payloads use sorted keys, compact separators, UTF-8 and no ASCII
escaping (`shared_generation.canonical`). Every saved payload is reread and
verified nonempty. The source pins, package versions and complete registration
are retained under each condition. Both capture error dictionaries are empty.

An observer of the normal `bc1_registration.size_inputs` payload sink saves
every call to `bc1_runtime.render_request`; it changes no renderer, sizing
input or acceptance result. Worker and omission inner requests come from
`bc1_audit.worker_request` and `omission_request`. Each contains one full and
one core catalog in `bc1_context.schema_context`; `model_catalog` removes only
`domain_of`. `model_request` replaces the duplicate inner full catalog with
its exact hash/reference, so it is not counted a second time.

**Integration limitation:** the archive contains shared-v1 responses, not BC1
responses. The three integration requests below are concrete offline sizing
scenarios from the production `render_stage_request`/`render_request` path,
with the production empty-future floor placeholders. They are not authenticated
or accepted live integration requests. The production cap and escape scenarios
are also retained below. No worker/omission response was fabricated as accepted.

`full`, `reconcile_full` and `report` use `api.build_phase` and
`receipt_completion.request_payload`. Receipt completion uses `build_request`
with the archived assistant response/record/receipt/manifest, rebuilding only
the initial full request, current schema capture and registration as in G1's
proof. For reconcile/report, the existing D59 empty-future BC1-audit-carry
scenario substitutes `model_carry=''` because no accepted BC1 final carry
exists; the real downstream contract and A14 schema renderer remain active.
The exact archived receipt result is supplied through `recover` without any
ledger or run output. These downstream totals are conditional renderer
measurements, not accepted replay of the historical shared-v1 audit as BC1.

## Main request table

{table(primary)}

## Exact kinds split

Each entry gives occurrence count × **wire-byte** contribution. `pins` groups
equal-length schema/catalog byte counts, SHA256s and request/registration/packet
identity pins. Full/core annotation contributions include the added key/comma
and all JSON escaping layers. A changed identity does not imply a byte increase.

| Request | Kinds (occurrences × bytes) |
|---|---|
{chr(10).join(kind_rows)}

The digest insertion is exactly 135 UTF-8 bytes:

```text
 a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);
```

The description expands by 189 bytes per rendered occurrence. BC1 includes
the description in both `catalog.classes.Instance.slots.data_substrate.definition`
and the corresponding `core_catalog` path for every typed request, irrespective
of worker assignment. Reconcile/report use the A14 occupied-owner context and
contain one occurrence. The digest is absent from the BC1 typed-audit requests.

The annotation is retained as LinkML's induced object, not just a bare string:

```json
{{"annotations":{{"d4d:termSources":{{"tag":"d4d:termSources","value":"EDAM Data, EDAM Format, IANA media types"}}}}}}
```

The added `annotations` member occupies **{unescaped_annotation} bytes** including
its separating comma in the catalog's canonical JSON. Encoding that catalog
inside a payload text block makes the contribution **+{full_annotation} wire
bytes in the full catalog** and **+{core_annotation} in the core catalog**,
once each per typed request. This annotation contribution is separate from the
two +189-byte descriptions. No other kind of model-facing change was found.

`EDAM: http://edamontology.org/` is **not rendered as a prefix table** in these
requests. EDAM's name in the description/digest is counted in those kinds.
The base-module prefix changes the merged-schema identities but adds no
separate prefix-declaration bytes. All leaf changes are assigned to the listed
kinds; the summary JSON exposes any `other` entry rather than hiding it.

## Additional integration size scenarios

{table(extra)}

`visible_cap_measured_escape` has the same actual ASCII payload as
`visible_cap_ascii_scenario`; its 1.25 expansion is an admission estimate,
not extra bytes silently added to the wire. `visible_cap_escaped_bound` uses
backslash placeholders and is advisory. These are explicitly hypothetical
future response strings. The paired schema delta is measured on each concrete
wire, independent of those hypothetical future string lengths.
Every row in this additional table has the same per-occurrence split as its
floor counterpart: description full +189, description core +189, annotation
full +123, annotation core +123, and 12 changed pin leaves at 0 bytes each;
digest and prefix-declaration contributions are 0.

## Evidence, verification and reproduction

- Scratch root: `{ROOT}`.
- Helpers: `scripts/adhoc/bc1_byte_proof/{{offline,capture,apply_schema,compare,refine_downstream}}.py`.
- `.bc1-byte-evidence/before/` and `after/`: each canonical request, registration,
  sizing record, expanded schema context and `capture.json` with SHA256/byte pins.
- [Summary JSON]({OUT / 'summary.json'}): every request and exact per-kind counts.
- [Per-leaf diffs]({OUT / 'leaf-diffs.txt'}): **every changed leaf**, with values or
  complete changed lines, embedding depth and contribution. `diff_*.json`
  retains the unabridged machine-readable before/after values and paths.
- `.bc1-byte-evidence/before/schema_sources/`: original five schema sources;
  the unchanged 3.0.0 merged schemas remain available at the BC1 base commit.
- `before-initial-extra-core-carry/` and `after-initial-extra-core-carry/`
  preserve the initial D59-style reconcile capture with an unnecessary core
  record. `refine_downstream.py` re-renders only downstream requests at each
  original schema identity, asserts exact `api.PHASE_NEEDS` carries, and restores
  every generated after byte. The tables above use those corrected runtime
  carry lists. The final capture helper already contains this correction.
- Rendering and Makefile regeneration ran serially. No test suite, provider,
  token endpoint, network, remote Git command, push, `gh`, ledger, or real
  branch edit was performed. The Python audit hook forbids socket operations;
  `-S -B` bypasses editable-install startup and bytecode writes. No run output
  directory was created. Full/core target hashes are checked above.

To reproduce in a fresh disposable worktree at the BC1 base, copy the helpers,
apply the same reviewed shared-generation diff, and run from that scratch:

```bash
PYTHON=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
LAUNCHER="$PWD/scripts/adhoc/bc1_byte_proof/offline.py"
"$PYTHON" -S -B "$LAUNCHER" scripts/adhoc/bc1_byte_proof/capture.py before
"$PYTHON" -S -B "$LAUNCHER" scripts/adhoc/bc1_byte_proof/apply_schema.py
make -j1 regen-all RUN="$PYTHON -S -B $LAUNCHER"
make -j1 -B gen-core-schema RUN="$PYTHON -S -B $LAUNCHER"
make -j1 gen-sssom-comprehensive gen-sssom-uri-comprehensive RUN="$PYTHON -S -B $LAUNCHER"
"$PYTHON" -S -B "$LAUNCHER" scripts/adhoc/bc1_byte_proof/capture.py after
"$PYTHON" -S -B "$LAUNCHER" scripts/adhoc/bc1_byte_proof/compare.py
```

The archive is read at `{ROOT.parent / 'codex-x-generality-g1'}`;
the capture helper records each exact archived input pin. Paths affect absolute
totals; both conditions must occupy the same path. `compare.py` checks lossless
decode/re-encode of every payload, accounts for every changed leaf including
embedded canonical JSON, and asserts that the sum of leaf contributions equals
the observed payload delta for every request. This verifies byte accounting,
not provider acceptance, live response validity or scientific equivalence.

The 20-payload before capture was the end-to-end canary: registration sizing
passed and canonical artifacts existed, were nonempty, and matched their pins
before any schema input changed. It does not exercise live credentials,
provider acceptance, load or concurrent requests. Helpers and evidence remain
in the scratch worktree. No commit, PR, remote issue or publication was attempted
for this explicitly offline proof.
'''
REPORT.write_text(report)
assert REPORT.read_text() == report and REPORT.stat().st_size
print('Report:', REPORT)
