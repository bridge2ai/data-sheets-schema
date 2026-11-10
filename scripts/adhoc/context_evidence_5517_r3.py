"""#5517 Round 3, 2026-11-08: apply reviewed quotations and D103.
Inputs: 55607a840 contexts and hash-verified local bundles. Outputs: contexts,
committed Kids First search, scratch audit and live-pin ledger. Offline only.
Run without arguments to plan, then --apply chorus (canary), then --apply all.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml
from context_evidence_5517 import sources
from data_sheets_schema.evaluation_context import context_digest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
BASE = '55607a840'
SEARCH = 'scripts/adhoc/context_evidence_5517_r3_kids_first_search.txt'
PATTERN = r'machine learning|training|\bAI\b|model|artificial intelligence|deep learning|AI-ready|AI/ML|predictive|benchmark|split'

def build():
    assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
    proposals, audit = {}, []
    for path in sorted((ROOT / 'data/context').glob('*_context.yaml')):
        project = path.stem.removesuffix('_context')
        old = subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT)}'], text=True)
        ctx = yaml.safe_load(old)
        bp, bundle, manifest = sources(project)
        assert hashlib.sha256(bp.read_bytes()).hexdigest() == manifest['bundle_sha256']
        lines = bundle.splitlines(keepends=True)
        def excerpt(first, last):
            return ''.join(lines[first-1:last]).rstrip('\n')
        def cite(quote, cid):
            chunk = next(c for c in manifest['chunks'] if c['id'] == cid)
            raw = ''.join(lines[chunk['lines'][0]-1:chunk['lines'][1]])
            assert hashlib.sha256(raw.encode()).hexdigest() == chunk['sha256']
            assert quote in raw, (project, cid, quote)
            return f'[chunks: {cid}] ' + json.dumps(quote, ensure_ascii=False)
        replacements = {}
        notes = {}
        states = {}
        if project == 'chorus':
            replacements = {'data_processing': [(excerpt(1074,1078),'c006')],
                            'regulated_access': [(excerpt(236,240),'c003')],
                            'processing_software': [('who have produced powerful open-source tooling for transforming and interacting with\n\nclinical data.','c007')]}
        elif project == 'cm4ai':
            replacements = {'data_collection': [('We use a combination of mapping techniques such as proteomic mass spectrometry, cellular imaging, and genetic perturbation via CRISPR/Cas9 to create a library of large-scale maps of cellular structure and function.','c016')],
                            'ml_training_dataset': [(excerpt(7095,7098),'c026')],
                            'regulated_access': [(excerpt(7133,7136),'c026'),(excerpt(7120,7121),'c026'),(excerpt(7080,7081),'c026')]}
            notes['regulated_access'] = ('Current June 2026 deposited files are public under CC BY-NC-SA 4.0 and FDA Regulated: No. Considered CM4AI:3773-3774: "A Data Access Committee will supervise ethical matters related to dataset\\ndistribution and potential dual licensing for commercial use." This future ethics/commercial-licensing role does not require research-access review. Considered external Perturb-seq embargoes at 7061-7064 and temporary pre-publication embargo at 7088: temporary withholding is not credentialing, DUA or DAC review. Commercial license negotiation (3771-3772), governance contact (7082-7083), generic Dataverse Request Access modals, and cell-line MTA (3215-3216) do not establish a data access gate. D52 value retained.')
        elif project == 'ai_readi':
            replacements = {'data_processing': [('Each CSV file in this directory is a one-to-one mapping to the OMOP CDM tables.','c015')],
                            'processing_software': [('problem, we are developing a cloud-based data management, curation\nand sharing platform called FAIRhub','c007'),('N/A - no labeling was performed','c018')]}
            states['processing_software'] = 'needs_owner'
            notes['processing_software'] = ('D52 value retained. Review of the declared bundle: REDCap at 1164-1167 describes collection, not processing; FAIRhub at 1930-1931 is still developing. The healthsheet at 4409 says N/A - no labeling was performed; this is limited to labeling and does not negate other processing. Neither excerpt establishes actual use of processing software. Owner disposition required; quotations provide context only.')
        elif project == 'kids_first':
            replacements = {'ml_training_dataset': [(excerpt(100,102),'c003')]}
            states['ml_training_dataset'] = 'absence_supported'
            command = ['rg','--hidden','--no-ignore','-n','-i',PATTERN,str(bp.relative_to(ROOT))]
            result = subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
            assert result.returncode == 0
            search = ('# #5517 D103 bundle search, 2026-11-08\n# Scope: complete declared bundle; ignored/hidden files included.\n'
                      f'# Bundle: {bp.relative_to(ROOT)}\n# SHA256: {manifest["bundle_sha256"]}\n'
                      '# Command (JSON argv): '+json.dumps(command)+'\n'
                      f'# Matching lines: {len(result.stdout.splitlines())}\n'+result.stdout)
            notes['ml_training_dataset'] = (f'D52 value retained. Absence-supported under D103, not a quotation proving false. Search scope: entire {bp.relative_to(ROOT)}; bundle sha256 {manifest["bundle_sha256"]}. Exact case-insensitive rg pattern: {PATTERN}; --hidden --no-ignore -n -i; {len(result.stdout.splitlines())} matching lines. Reproducible helper: scripts/adhoc/context_evidence_5517_r3.py; complete output: {SEARCH}. No dataset ML-training intent found. Considered line 1440, CAVATICA: "Users can also launch an environment optimized for machine learning and execution on GPU instances." Platform capability is D52 one possible downstream use, not a dataset training purpose. Researcher/misuse-prevention training and cost-prediction/benchmarking hits likewise do not contradict false.')
            (SCRATCH / 'r3-kids-first-search.txt').write_text(search)
        if project == 'ai_readi':
            notes['processing_software'] = notes['processing_software'].replace('1164-1167', '1005-1008')
        new = old
        for pred, entry in ctx.items():
            if pred in replacements:
                owner = re.findall(r'\[curator_assertion:[^]]+\]',entry['evidence'])
                state = states.get(pred,'quoted')
                parts = owner[:]
                if state != 'quoted':
                    parts.append(f'[{state}: true]')
                if pred in notes:
                    parts.append('[search_notes] '+json.dumps(notes[pred]))
                parts.extend(cite(q,c) for q,c in replacements[pred])
                entry['evidence'] = ' '.join(parts)
            elif project == 'voice' and pred != 'ml_training_dataset':
                entry['evidence'] = re.sub(r'c0(?:15|16|17)', 'c019' if pred == 'regulated_access' else 'c018', entry['evidence'])
                if pred == 'processing_software':
                    entry['evidence'] = cite(excerpt(5057,5059),'c019')
            block = re.search(rf'(?ms)^{pred}:\n.*?(?=^\w+:|\Z)',new)[0]
            ids = sorted(set(re.findall(r'\[chunks: (c\d{3})\]',entry['evidence'])))
            updated = re.sub(r'  # chunks: \[[^]]+\]','  # chunks: ['+', '.join(ids)+']',block)
            updated = re.sub(r'^  evidence:.*$',lambda _: '  evidence: '+json.dumps(entry['evidence'],ensure_ascii=False),updated,flags=re.M)
            new = new.replace(block,updated)
        assert yaml.safe_load(new) == ctx
        proposals[project] = new
    return proposals

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply',default='none',choices=['none','chorus','all'])
    args = parser.parse_args()
    proposals = build()
    for project, text in proposals.items():
        if args.apply in (project,'all'):
            path = ROOT / f'data/context/{project}_context.yaml'
            path.write_text(text)
            assert path.read_text() == text
    if args.apply == 'all':
        (ROOT / SEARCH).write_text((SCRATCH / 'r3-kids-first-search.txt').read_text())
        note = ROOT / 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md'
        text = subprocess.check_output(['git', 'show', f'{BASE}:{note.relative_to(ROOT)}'], text=True)
        ledger = []
        for project, proposal in proposals.items():
            line = next(l for l in text.splitlines() if l.startswith('| **'+project.upper()+'**'))
            old = re.search(r'`([a-f0-9]{64})`',line)[1]
            new = context_digest(yaml.safe_load(proposal))
            ledger.append(dict(project=project,old=old,new=new))
            text = text.replace(line,line.replace(old,new))
        note.write_text(text)
        (SCRATCH / 'r3-pin-ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print('Verified six proposals; applied '+args.apply)
