"""PR5531 fix B evidence, 2026-11-08; adapted from the review's three probes.

Inputs: local origin/main objects, current merged schema, committed corpus.
Outputs: scratch JSON and review-script logs; no baseline rewrite or network.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import yaml
from data_sheets_schema import grounding as g, api_runner as api
from data_sheets_schema.identifiers import uriorcurie_slots

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
PRIMARY = ROOT.parent.parent / 'data-sheets-schema'
SCHEMA = 'src/data_sheets_schema/schema/'
def original(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'])

main_raw = original('origin/main', SCHEMA + 'data_sheets_schema_all.yaml')
main_path = SCRATCH / 'fix-b-main-schema.yaml'
main_path.write_bytes(main_raw)
main = yaml.safe_load(main_raw)
head = yaml.safe_load((ROOT / SCHEMA / 'data_sheets_schema_all.yaml').read_bytes())
assert main['prefixes'] == head['prefixes']
slots = set(uriorcurie_slots())
bases = [g.declared_bases_of(doc) for doc in (main, head)]
prefixes = [set(doc['prefixes']) for doc in (main, head)]
totals = [0, 0]
undeclared = [Counter(), Counter()]
changed = []
paths = subprocess.check_output(['git', 'ls-files', 'data/d4d_concatenated'], text=True).splitlines()
paths = [p for p in paths if Path(p).suffix == '.yaml' and '_d4d' in Path(p).name and len(Path(p).parts) == 5]
count = 0
example = None
for path in paths:
    rec = yaml.safe_load((ROOT / path).read_bytes())
    if not isinstance(rec, dict):
        continue
    count += 1
    rows = []
    for i in range(2):
        findings = g.resolver_urls_in_identifier_slots(rec, slots, bases=bases[i])
        totals[i] += len(findings)
        rows.append(findings)
        undeclared[i].update(g.undeclared_prefixes(rec, slots, prefixes=prefixes[i]))
    if rows[0] != rows[1]:
        changed.append(path)
    if example is None and 'CM4AI' in path and 'agentic' in path:
        example = path

text = 'instances:\n' + ''.join('- data_topic: ' + iri + '\n' for iri in (
    'http://id.nlm.nih.gov/mesh/D012640', 'http://purl.obolibrary.org/obo/GO_0008150',
    'http://purl.obolibrary.org/obo/NCIT_C18469', 'http://www.ebi.ac.uk/efo/EFO_0000001'))
normalized = [api.normalise_identifier_form(text, _tables=(frozenset(slots), tuple((b,p) for b,p in bs if b.endswith(('/', '#', '_', ':'))))) for bs in bases]
assert normalized[0] == normalized[1] == text
assert totals[0] == totals[1] and not changed and undeclared[0] == undeclared[1]

invalid = SCRATCH / 'fix-b-invalid.yaml'
invalid.write_text('id: example:invalid\nname: Example\nlicense_and_use_terms:\n  data_use_permission: general_research_use\n')
for name, args in (
    ('pr5531_resolver_url_row_20261108.py', [str(main_path), str(ROOT / (example or paths[0]))]),
    ('pr5531_resolver_url_extra_20261108.py', [str(main_path)]),
    ('pr5531_validator_lines_warning_20261108.py', [str(invalid)]),
):
    result = subprocess.run([sys.executable, str(PRIMARY / 'scripts/adhoc' / name), *args], capture_output=True, text=True, check=True)
    output = result.stdout + result.stderr
    (SCRATCH / ('fix-b-' + name + '.log')).write_text(output)
    assert 'Overriding with mapping' not in output and 'namespace is already mapped' not in output

def function_bytes(raw, name):
    text = raw.decode()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
code_path = 'src/data_sheets_schema/bc1_context.py'
assert function_bytes(original('origin/main', code_path), '_curie_prefixes') == function_bytes((ROOT / code_path).read_bytes(), '_curie_prefixes')
hashes = {}
for name in ('data_sheets_schema.yaml', 'data_sheets_schema_all.yaml', 'data_sheets_schema_core.yaml', 'data_sheets_schema_core_all.yaml'):
    hashes[name] = {ref: hashlib.sha256(original(ref, SCHEMA + name) if ref != 'fix-b' else (ROOT / SCHEMA / name).read_bytes()).hexdigest() for ref in ('origin/main', '5e382f0c4', 'fix-b')}
result = dict(records=count, resolver_findings=totals, resolver_delta=totals[1]-totals[0], changed_records=changed,
              undeclared_counts=[dict(c) for c in undeclared], undeclared_totals=[sum(c.values()) for c in undeclared],
              normalizer_outputs=normalized, schema_prefixes_equal=True, v1_curie_prefix_function_byte_identical=True, schema_sha256=hashes)
(SCRATCH / 'fix-b-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
