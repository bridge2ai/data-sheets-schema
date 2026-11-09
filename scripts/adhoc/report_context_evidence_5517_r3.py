"""#5517 Round 3 audit/report, 2026-11-08.
Inputs: local diff, declared bundles, strict parser and scratch test artifacts.
Outputs: scratch audit/pin search; --handoff appends report and one codex STATUS
entry after commit. No network; shared report and STATUS are read back.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import yaml
from context_evidence_5517 import sources
from data_sheets_schema.evaluation_context import context_digest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
BASE = '55607a840'
def git(*args):
    return subprocess.check_output(['git', *args],cwd=ROOT,text=True)

spec = importlib.util.spec_from_file_location('strict',ROOT / 'tests/test_context_evidence_verbatim.py')
strict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strict)
rows, patterns = [], []
for path in strict.CONTEXTS:
    project = path.stem.removesuffix('_context')
    context = yaml.safe_load(path.read_text())
    oldraw = git('show',f'{BASE}:{path.relative_to(ROOT)}')
    old = yaml.safe_load(oldraw)
    patterns += [str(path.relative_to(ROOT)),path.name,hashlib.sha256(oldraw.encode()).hexdigest(),context_digest(old)]
    bp, bundle, manifest = sources(project)
    lines = bundle.splitlines(keepends=True)
    for pred, entry in context.items():
        assert entry['value'] is old[pred]['value']
        assert re.findall(r'\[curator_assertion:[^]]+\]',entry['evidence']) == re.findall(r'\[curator_assertion:[^]]+\]',old[pred]['evidence'])
        state, notes, owner = strict.validate_quotes(entry['evidence'],strict.source_chunks(path))
        _, _, _, quotes = strict.parse_evidence(entry['evidence'])
        locations = []
        for ids, quote in quotes:
            for cid in ids:
                chunk = next(c for c in manifest['chunks'] if c['id']==cid)
                chunktext = ''.join(lines[chunk['lines'][0]-1:chunk['lines'][1]])
                line = chunk['lines'][0]+chunktext[:chunktext.index(quote)].count('\n')
                locations.append(f'{bp.relative_to(ROOT)}:{line} ({cid})')
        rows.append(dict(project=project,predicate=pred,value=entry['value'],state=state,notes=notes,
                         quotes=[q for _,q in quotes],locations=locations,bundle_sha256=manifest['bundle_sha256']))
counts = Counter(r['state'] for r in rows)
assert counts == {'quoted':40,'absence_supported':1,'needs_owner':1} and len(rows)==42
pins = json.loads((SCRATCH / 'r3-pin-ledger.json').read_text())
note = 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md'
expected = git('show',f'{BASE}:{note}')
for pin in pins:
    expected = expected.replace(pin['old'],pin['new'])
assert (ROOT / note).read_text()==expected
allowed = {str(p.relative_to(ROOT)) for p in strict.CONTEXTS} | {note,
    'tests/test_context_evidence_verbatim.py','tests/test_evaluation_context_files.py',
    'scripts/adhoc/context_evidence_5517_r3.py','scripts/adhoc/report_context_evidence_5517_r3.py',
    'scripts/adhoc/context_evidence_5517_r3_kids_first_search.txt'}
assert set(git('diff',BASE,'--name-only').splitlines()) <= allowed
assert set(git('ls-files','--others','--exclude-standard').splitlines()) <= allowed
assert not git('diff','--check')
assert not git('diff',BASE,'--','src/','data/preprocessed/','data/rubric/',
               'notes/matched_cborg_2026-09-17_v10t/registration.public.json')
(SCRATCH / 'r3-audit.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
if '--search' in sys.argv:
    assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
    (SCRATCH / 'r3-pin-patterns.txt').write_text('\n'.join(sorted(set(patterns)))+'\n')
    with (SCRATCH / 'r3-pin-search.txt').open('w') as out:
        result = subprocess.run(['rg','--hidden','--no-ignore','--text','-n','-F','-f',str(SCRATCH / 'r3-pin-patterns.txt'),'.'],cwd=ROOT,stdout=out)
    assert result.returncode == 0
print(json.dumps(dict(counts=counts,values_preserved=len(rows),changed_pins=sum(p['old']!=p['new'] for p in pins))))
if '--handoff' not in sys.argv:
    sys.exit(0)
assert not git('status','--porcelain')
head = git('rev-parse','HEAD').strip()
results = []
for label in ('canary-r3','literal-r3review','focused-r3review','evaluation-r3'):
    log, xml = SCRATCH / f'{label}.log', SCRATCH / f'{label}.xml'
    assert log.stat().st_size and xml.stat().st_size
    suite = ET.parse(xml).getroot().find('testsuite')
    assert all(int(suite.get(k))==0 for k in ('failures','errors','skipped'))
    results.append(f'| {label} | {suite.get("tests")} | {suite.get("time")} | `{xml}` |')
report = ROOT.parent / 'plans/reviews/codex_5517_2026-11-08.md'
marker = '## Round 3 — quotation review and D103'
body = f'''\n\n{marker}

Local commit `{head}` on `codex/5517-context-evidence-20261108`, based on `{BASE}`. No push. All 42 values and both D52 curator strings retained. Inventory: **40 quoted + 1 absence_supported + 1 needs_owner = 42**. The strict lexical gate verifies exact source text and cited chunk/bundle hashes; it does not establish entailment automatically.

The four supported replacements use the review's exact quotations: CHORUS released OMOP rows, dataset controlled access, and transformation tooling; CM4AI's own mapping-data collection. Six VOICE entries now cite v3.1.0 and CM4AI ML intent cites the current June 2026 release. AI-READI's bare WFDB-name quotation was dropped.

**Needs owner:** AI_READI.processing_software remains true. REDCap documents collection; FAIRhub's curation platform is described as developing (1930–1931, c007). The healthsheet says “N/A - no labeling was performed” (4409, c018), which concerns labeling only. The contextual quotations neither prove actual processing-software use nor contradict the retained value.

**CM4AI.regulated_access=false is quoted:** the current release's Public (10), CC BY-NC-SA 4.0 and FDA Regulated: No fields support false. Notes explicitly consider the future commercial/ethics DAC role (3773–3774), external Perturb-seq embargoes (7061–7064) and temporary embargo (7088). None asserts credentialing, a signed DUA or DAC review for research access; embargoed streams remain withheld. Commercial licensing, governance contact, generic request-access UI and the cell-line MTA were also distinguished from data access gates.

**KIDS_FIRST.ml_training_dataset=false is absence_supported under D103:** the DRC purpose quotation is at 100–102, c003. The complete 32-line ignore-independent search is committed at `scripts/adhoc/context_evidence_5517_r3_kids_first_search.txt`, with exact JSON argv, scope and bundle SHA256. Pattern removes research/resource and adds artificial intelligence, deep learning, AI-ready, AI/ML, predictive, benchmark and split. The line-1440 CAVATICA ML environment is platform capability—D52's one possible downstream use—not an ML-training purpose for this resource. Training researchers, cost models and biological models do not contradict false. This search supports absence within the declared bundle, not universal absence.

### Validation

The CHORUS write canary was read back before remaining writes. The one-test canary's persisted log/XML passed before suites began; it exercises the same launcher, interpreter, two-worker mode and scratch environment, not scientific entailment. The strict suite checks all three states, rejects malformed metadata/nonverbatim quotations and reproduces the committed D103 search exactly.

| Run | Passed (zero failures/errors/skips) | Seconds | XML (log alongside) |
| --- | ---: | ---: | --- |
'''+ '\n'.join(results)+f'''

Existing interpreter: `data-sheets-schema/.venv/bin/python`; dependency files unchanged. Every pytest run used `-n 2`, a 3600-second process-group deadline, absolute `PYTHONPATH={ROOT}/src:{ROOT}`, disabled bytecode/cache and scratch-only basetemp/TMPDIR. Quiet lock checked before launch and supervised during tests; no interruptions. No native agent executable, network, provider, fetch/push/gh or protected edits. No new top-level execution directories. Scratch artifacts: `{SCRATCH}/r3-audit.json`, `r3-pin-ledger.json`, `r3-pin-patterns.txt`, `r3-pin-search.txt`, `r3-kids-first-search.txt` and the test logs/XML/basetemps. Helpers and the required durable search output are committed provenance.

### Live pins and read-only review

Five changed contexts have rotated normalized live hashes in the decision table; VOICE_PEDIATRIC is unchanged. The decision record differs only in these hashes. An ignore-independent repository search for context names/paths and previous raw/normalized hashes is retained in r3-pin-search.txt. No protected canonical pin update is required; historical registrations remain unchanged. The allowlisted whole diff excludes production, bundles, manifests, rubrics and historical records.

| Project | Prior live hash | Final hash |
| --- | --- | --- |
'''
for p in pins:
    body += f'| {p["project"]} | `{p["old"]}` | `{p["new"]}` |\n'
body += '\n### Updated reviewer table: all 42 entries\n\nJSON notation preserves source newlines. Context quotations for needs_owner and absence_supported are not direct proofs of the retained values.\n\n| Predicate | Value | Quotations | Bundle line / chunk | State |\n| --- | --- | --- | --- | --- |\n'
for r in rows:
    quotes = '<br>'.join('<code>'+html.escape(json.dumps(q,ensure_ascii=False)).replace('|','&#124;')+'</code>' for q in r['quotes'])
    body += f'| {r["project"]}.{r["predicate"]} | {str(r["value"]).lower()} | {quotes} | '+ '<br>'.join('`'+loc+'`' for loc in r['locations'])+f' | {r["state"]} |\n'
body += '\n**R3-F1 — issue-ready finding; GitHub filing deferred by the explicit offline/no-gh instruction.** Title: Incorrect REDCap source locator in AI-READI review notes. Read-only review found the notes pointed to 1164–1167 rather than 1005–1008. After ending that review pass, corrected the locator and rotated its live pin; repeated strict/focused checks passed on the correction. Original passing literal-r3/focused-r3 logs remain in scratch as superseded evidence. A subsequent read-only review found no further actionable defect. The remaining AI-READI evidence question is explicitly assigned to owner review under #5517/#2912. No PR, push or merge was attempted. After this report and exactly one codex STATUS entry, stopped.\n'
previous = report.read_text()
assert marker not in previous
report.write_text(previous+body)
assert report.read_text()==previous+body
status = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
previous = status.read_text()
entry = f'- {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} — **#5517 Round 3 / D103 complete; stopped.** Local commit `{head}`, no push. All 42 values preserved: 40 quoted + 1 absence_supported (Kids First ML) + 1 needs_owner (AI-READI processing software). Current-release citations corrected; five live pins rotated; Kids First search committed. Strict/focused/evaluation checks passed; report: `d4d-executions/plans/reviews/codex_5517_2026-11-08.md`, Round 3. Offline, no protected edits/native executable; quiet-lock, two-worker and deadline constraints observed. Owner disposition of AI-READI processing-software evidence remains.\n\n'
assert '#5517 Round 3 / D103 complete' not in previous
assert previous.count('### codex\n')==1
updated = previous.replace('### codex\n','### codex\n\n'+entry,1)
status.write_text(updated)
assert status.read_text()==updated
print('Report appended and exactly one codex STATUS entry verified; stop.')
