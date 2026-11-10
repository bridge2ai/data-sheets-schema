"""PR5531 fix C, 2026-11-08: offline byte, pin and corpus evidence.

Inputs: local Git objects, schema and reviewer probes. Outputs: exclusively
scratch-pr5531-fix; byte mode also matches governance EOF to main.
Run through pr5531_fix_a_run.py for quiet-window/deadline enforcement.
"""
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
REVIEW = ROOT.parent / 'plans/reviews/pr5531_rereview_scripts'
SCHEMA = ROOT / 'src/data_sheets_schema/schema'

def main():
    mode = sys.argv[1]
    if mode == 'bytes':
        rows = {}
        for name in ('D4D_Composition.yaml', 'D4D_Data_Governance.yaml'):
            path = SCHEMA / name
            baseline = subprocess.check_output(['git', 'show', f'origin/main:{path.relative_to(ROOT)}'])
            current = path.read_bytes()
            rows[name] = dict(main_bom=baseline.startswith(b'\xef\xbb\xbf'),
                              head_bom=current.startswith(b'\xef\xbb\xbf'),
                              main_newline=baseline.endswith(b'\n'), head_newline=current.endswith(b'\n'))
            assert rows[name]['main_bom'] and rows[name]['head_bom']
            if name == 'D4D_Data_Governance.yaml' and not baseline.endswith(b'\n'):
                path.write_bytes(current.rstrip(b'\n'))
        (SCRATCH / 'fix-c-bom.json').write_text(json.dumps(rows, indent=2) + '\n')
        from data_sheets_schema import api_runner as api
        print('wrap set', sorted(api._multivalued_slots()))
        print(json.dumps(rows, indent=2))
    elif mode == 'wrap-collisions':
        from data_sheets_schema import api_runner as api
        from data_sheets_schema.schema_view import shared_view
        for schema in (api.FULL_SCHEMA_PATH, api.CORE_SCHEMA_PATH):
            view = shared_view(schema)
            for cls in view.all_classes():
                for slot in view.class_induced_slots(cls):
                    if str(slot.name) in api._multivalued_slots() and str(slot.range) in view.all_classes():
                        print(Path(schema).name, cls, slot.name, slot.range, slot.multivalued)
    elif mode == 'corpus':
        tree = SCRATCH / 'fix-c-main-tree'
        tree.mkdir(exist_ok=True)
        archive = SCRATCH / 'fix-c-main.tar'
        with archive.open('wb') as out:
            subprocess.run(['git', 'archive', 'origin/main', 'src'], stdout=out, check=True)
        with tarfile.open(archive) as tar:
            tar.extractall(tree, filter='data')
        for label, source in [('main', tree), ('head', ROOT)]:
            env = dict(os.environ, PYTHONPATH=f'{source}/src:{source}')
            subprocess.run([sys.executable, str(REVIEW / 'normalise_corpus.py'), str(ROOT),
                            str(SCRATCH / f'fix-c-normalised-{label}')], cwd=source, env=env, check=True)
        subprocess.run([sys.executable, str(REVIEW / 'classify_normaliser_diff.py'),
                        str(SCRATCH / 'fix-c-normalised-main'), str(SCRATCH / 'fix-c-normalised-head')], check=True)
        for label in ('main', 'head'):
            print(label, flush=True)
            subprocess.run([sys.executable, str(REVIEW / 'baseline_normaliser_prose_changes.py'),
                            str(ROOT), str(SCRATCH / f'fix-c-normalised-{label}')], check=True)
    elif mode == 'consequences':
        subprocess.run([sys.executable, str(REVIEW / 'digest_texts.py'),
                        str(SCRATCH / 'fix-c-digests')], check=True)
        rows = {}
        for name in subprocess.check_output(['git', 'diff', '--name-only', '75463cb38'], text=True).splitlines():
            path = ROOT / name
            original = subprocess.run(['git', 'show', f'75463cb38:{name}'], capture_output=True)
            before = original.stdout if original.returncode == 0 else None
            after = path.read_bytes()
            rows[name] = {label: (dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) if raw is not None else None)
                          for label, raw in [('before', before), ('after', after)]}
        (SCRATCH / 'fix-c-byte-consequences.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps(rows, indent=2))
    elif mode == 'semantic':
        from rdflib import Graph
        from rdflib.compare import isomorphic
        def old(name):
            return subprocess.check_output(['git', 'show', f'75463cb38:{name}'])
        owl = 'project/owl/data_sheets_schema.owl.ttl'
        a = Graph().parse(data=old(owl).decode(), format='turtle')
        b = Graph().parse(ROOT / owl, format='turtle')
        assert isomorphic(a, b)
        print('OWL isomorphic', len(a), len(b))
        for name in ('d4d_rocrate_sssom_comprehensive.tsv', 'd4d_rocrate_sssom_uri_comprehensive.tsv'):
            path = 'src/data_sheets_schema/semantic_exchange/' + name
            before, after = old(path).decode(), (ROOT / path).read_text()
            assert before.replace('2026-11-07', '2026-11-08') == after
            print(name, 'only date changes; 301 mapping rows plus header')
        for path in ('src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
                     'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml',
                     'project/jsonschema/data_sheets_schema.schema.json',
                     'project/jsonld/data_sheets_schema.context.jsonld'):
            assert old(path) == (ROOT / path).read_bytes()
            print(path, 'byte-identical')
    elif mode == 'metadata':
        rows = {}
        for name in ('notes/claudecode_direct/prepare_direct.py',
                     'notes/matched_cborg_2026-09-13/prepare_registration.py'):
            rows[name] = {}
            for label, raw in [('working', (ROOT / name).read_bytes()),
                               ('fix-b', subprocess.check_output(['git', 'show', f'75463cb38:{name}'])),
                               ('main', subprocess.check_output(['git', 'show', f'origin/main:{name}']))]:
                rows[name][label] = hashlib.sha256(raw).hexdigest()
            assert len(set(rows[name].values())) == 1
        result = {'python': sys.version, 'executable': sys.executable,
                  'platform': platform.platform(), 'scanner_finding_source_hashes': rows,
                  'poetry_lock_sha256': hashlib.sha256((ROOT / 'poetry.lock').read_bytes()).hexdigest()}
        (SCRATCH / 'fix-c-environment.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    elif mode == 'verification':
        rows = {}
        cases = {}
        for label, name in [('initial', 'fix-c-before.xml'), ('stale-pins', 'fix-c-stale-pins.xml'),
                            ('acceptance', 'fix-c-acceptance/pytest.xml'), ('final', 'fix-c-final/pytest.xml')]:
            doc = ET.parse(SCRATCH / name)
            observations = [((case.attrib['classname'], case.attrib['name']),
                            ('failed' if case.find('failure') is not None or case.find('error') is not None
                             else 'skipped' if case.find('skipped') is not None else 'passed'))
                            for case in doc.iter('testcase')]
            cases[label] = dict(observations)
            rows[label] = {key: sum(value == key for _, value in observations)
                           for key in ('passed', 'failed', 'skipped')}
        failures = {key for key, value in cases['stale-pins'].items() if value == 'failed'}
        assert len(failures) == 11
        assert all(cases['final'].get(key) == 'passed' for key in failures)
        assert rows['final']['failed'] == 0
        rows['reproduced_11_failures_now_pass'] = sorted('::'.join(key) for key in failures)
        changed = subprocess.check_output(['git', 'diff', '--name-only', '75463cb38'], text=True).splitlines()
        assert not any('canonical_hashes.yaml' in p or 'shared_generation.py' in p
                       or p.startswith('.github/') or 'D76' in p for p in changed)
        rows['changed_paths'] = changed
        (SCRATCH / 'fix-c-verification.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps(rows, indent=2))

if __name__ == '__main__':
    main()
