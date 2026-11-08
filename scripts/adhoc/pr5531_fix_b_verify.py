"""PR5531 fix B final read-only checks, 2026-11-08.

Inputs: local fix-A/main Git objects and final products; outputs: scratch JSON.
Checks protected paths, historical entries, legacy identity and OWL semantics.
"""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import xml.etree.ElementTree as ET
import yaml
from rdflib import Graph, Literal
from rdflib.compare import isomorphic
from data_sheets_schema import bc1_context as bc

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
def original(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'])

changed = subprocess.check_output(['git', 'diff', '5e382f0c4', '--name-only'], text=True).splitlines()
assert not any('sidecar' in p.lower() or 'd76' in p.lower() or 'canonical_hashes' in p or 'shared_generation' in p or p.startswith('.github/') for p in changed)
for path in ('src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml', 'src/data_sheets_schema/schema/digest_inventory.yaml'):
    assert (ROOT / path).read_bytes() == original('5e382f0c4', path)
history_path = 'src/data_sheets_schema/schema/release_history.yaml'
before = yaml.safe_load(original('5e382f0c4', history_path))
after = yaml.safe_load((ROOT / history_path).read_bytes())
assert before['releases'][:-1] == after['releases'][:-1]
assert yaml.safe_load(original('origin/main', 'src/data_sheets_schema/schema/D4D_Base_import.yaml'))['prefixes'] == yaml.safe_load((ROOT / 'src/data_sheets_schema/schema/D4D_Base_import.yaml').read_bytes())['prefixes']
legacy = ModuleType('pr5531_legacy_context')
legacy.__package__ = 'data_sheets_schema'
sys.modules[legacy.__name__] = legacy
exec(compile(original('origin/main', 'src/data_sheets_schema/bc1_context.py'), 'main/bc1_context.py', 'exec'), legacy.__dict__)
assert legacy.contract_identity() == bc.contract_identity(1)
owl = 'project/owl/data_sheets_schema.owl.ttl'
expected = Graph().parse(data=original('5e382f0c4', owl), format='turtle')
replacements = 0
for s, p, o in list(expected):
    if isinstance(o, Literal) and '{"prefix":"MeSH","local_prefix":""},' in str(o):
        expected.remove((s,p,o))
        expected.add((s,p,Literal(str(o).replace('{"prefix":"MeSH","local_prefix":""},', ''), lang=o.language, datatype=o.datatype)))
        replacements += 1
assert replacements > 0
assert isomorphic(expected, Graph().parse(ROOT / owl, format='turtle'))
tests = {p.name: [s.attrib for s in ET.parse(p).getroot().iter('testsuite')] for p in SCRATCH.glob('fix-b-*.xml')}
def cases(name):
    return {(c.attrib['classname'], c.attrib['name']): c
            for c in ET.parse(SCRATCH / name).getroot().iter('testcase')}
initial = cases('fix-b-acceptance.xml')
final = cases('fix-b-final-rerun.xml')
failed = {k for k, c in initial.items() if c.find('failure') is not None or c.find('error') is not None}
assert len(failed) == 3 and failed <= final.keys()
assert all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in final.values())
passed = {k for k, c in initial.items() if all(c.find(tag) is None for tag in ('failure', 'error', 'skipped'))} | final.keys()
skipped = {k for k, c in initial.items() if c.find('skipped') is not None}
special_cases = {k[1]: dict(c.attrib) for k, c in final.items()
                 if 'sizing_and_audit' in k[1] or 'journaled_before_parse' in k[1] or 'public_bc1_pipeline' in k[1]}
proofs = []
for path in (SCRATCH / 'fix-b-final-rerun').rglob('journal-proof.json'):
    data = path.read_bytes()
    proof = json.loads(data)
    assert proof['responses'] and proof['journal']
    proofs.append(dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), responses=len(proof['responses'])))
assert proofs
core_path = 'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml'
assert yaml.safe_load(original('origin/main', core_path))['prefixes'] == yaml.safe_load((ROOT / core_path).read_bytes())['prefixes']
result = dict(protected_unchanged=True, historical_releases_unchanged=True,
              v1_contract_identity_matches_main=True, base_prefixes_match_main=True,
              owl_expected_annotation_replacements=replacements, owl_semantics_match=True,
              tests=tests, changed_files=changed, initial_failures_cleared=sorted(failed),
              unique_passed=len(passed), unique_skipped=len(skipped), special_cases=special_cases,
              journal_proofs=proofs, core_prefixes_match_main=True)
(SCRATCH / 'fix-b-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
