"""Independent checks of pooled measures and all report artifacts."""
from pathlib import Path
import json,statistics,re,xml.etree.ElementTree as ET
from PIL import Image
O=Path(__file__).resolve().parent;D=O/'data';load=lambda n:json.loads((D/f'{n}.json').read_text())
I=load('issues');S=load('sources');L=load('source_links');Q=load('items');groups=load('source_group_mapping');rows=load('section_document_record_cells');summ=load('section_document_summary');maps={x['item']:x['section'] for x in load('section_document_score_mapping') if x['section']}
assert len(maps)==39
for x in rows:
 assert '_v8_' in x['record']
 comments={i['issue_id'] for i in I if i['record']==x['record'] and x['section'] in i['sections']}
 assert x['section_comment_count']==len(comments)
 a=[q for q in Q if q['record']==x['record'] and q['rubric']==10 and q['applicable'] and maps.get(q['id'])==x['section']]
 expected=sum(q['score'] for q in a)/sum(q['max'] for q in a)*100 if a else None
 assert (expected is None and x['selected_r10_percent'] is None) or abs(expected-x['selected_r10_percent'])<1e-9
for x in summ:
 cells=[r for r in rows if all(r[k]==x[k] for k in ['level','document_type','section'])]
 assert len(cells)==x['available_records']
 assert abs(statistics.mean(r['section_comment_count'] for r in cells)-x['mean_comments_per_record'])<1e-9
 for src,dst,den in [('selected_r10_percent','mean_selected_r10_percent','score_records'),('linked_flagged_percent','mean_linked_flagged_percent','linked_records')]:
  vals=[r[src] for r in cells if r[src] is not None];assert len(vals)==x[den]
  assert (not vals and x[dst] is None) or abs(statistics.mean(vals)-x[dst])<1e-9
# Verify the pooled availability groups stated as identical in the prose.
cohort=lambda g:{r['record'] for r in S if groups[r['source_type']]==g}
assert cohort('Docs')==cohort('Awards') and len(cohort('Docs'))==12
assert cohort('Publications')==cohort('Repositories')==cohort('Terms')
for f in (O/'figures').glob('*.svg'):ET.parse(f)
for f in (O/'figures').glob('*.png'):
 with Image.open(f) as im:im.verify()
s=(O/'D4D_v8_summary.html').read_text();assert s.count('<figure>')==14 and s.count('class="issue"')==303 and 'id="pooled-sections"' in s
for href in re.findall(r'href="([^"]+)"',s):
 if href.startswith('#'):assert 'id="'+href[1:]+'"' in s
 else:assert (O/href).is_file(),href
v=load('validation');v.pop('all_8_svg_files_parse',None);v.pop('all_8_png_files_verify',None);v.update({'figures':14,'html_embedded_figures':14,'all_svg_files_parse':True,'all_png_files_verify':True,'pooled_section_document_record_cells':len(rows),'pooled_section_document_summary_cells':len(summ),'single_section_rubric10_items':39,'pooled_comment_and_score_arithmetic_verified':True,'overlapping_cohort_claims_verified':True,'plots_visually_checked':'Original eight-figure contact sheet and new three pooled section figures'})
(D/'validation.json').write_text(json.dumps(v,indent=2));print('Validated 14 figures, 303 comments,',len(rows),'pooled record cells and',len(summ),'summary cells.')
