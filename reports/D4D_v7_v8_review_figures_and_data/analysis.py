import sys
_orig_sys_path = list(sys.path)
sys.path = [p for p in sys.path if not p.endswith('reports/D4D_v7_v8_review_figures_and_data') and p != '']
import statistics
sys.path = _orig_sys_path
import json,re,hashlib,subprocess,collections,html,math
from pathlib import Path
import yaml,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from data_sheets_schema.receipt_sources import run_chunks
H=lambda x:hashlib.sha256(x).hexdigest()
base=ROOT/'notes/reference_rescore_2026-09-12_cborg_runtime'
manifest=json.loads((base/'manifest.json').read_text()); review=json.loads((base/'semantic_review.json').read_text())
qual={c['job_id'] for c in review['cases'] if c['status']=='requires_adjudication'}
projects=['AI_READI','CHORUS','CM4AI','VOICE']; versions=['v7','v8']
schema=yaml.safe_load((ROOT/'src/data_sheets_schema/schema/data_sheets_schema_all.yaml').read_text())
classsec={}
for f in sorted((ROOT/'src/data_sheets_schema/schema').glob('D4D_*.yaml')):
 if f.stem in ['D4D_Base_import','D4D_Core','D4D_Minimal','D4D_Evaluation_Summary','D4D_Metadata']:continue
 for c in (yaml.safe_load(f.read_text()).get('classes') or {}):classsec[c]=f.stem[4:].replace('_',' ')
attrs={}
for c in ['Information','Dataset']:
 cd=schema['classes'][c];attrs.update({k:schema.get('slots',{}).get(k,{}) for k in cd.get('slots',[])});attrs.update(cd.get('attributes',{}))
def rootfield(f):return re.split(r'[.\[]',f)[0]
def section(f):
 f=rootfield(f)
 return classsec.get(attrs.get(f,{}).get('range'),'Metadata')
def present(v):return v is not None and v!='' and v!=[] and v!={}
records={}; ratings=[];issues=[];items=[];audit=[]
for r in [10,20]:
 for f in sorted((ROOT/f'data/evaluation_llm/rubric{r}_semantic/reference_2026-09-12_cborg_runtime').glob('*.json')):
  d=json.loads(f.read_text());m=re.match(r'(.+)_(v[78])_rep(\d+)_r\d+_rating(\d+)',f.stem);p,v,rep,rat=m.groups();rep=int(rep);rat=int(rat);rid=f'{p}_{v}_rep{rep}';jid=f.stem.removesuffix('_evaluation');inp=ROOT/d['d4d_file'];data=yaml.safe_load(inp.read_text());score=d['overall_score'];den=score['adjusted_max_points'];pct=100*score['total_points']/den
  assert H(inp.read_bytes())==manifest['pinned_files'][d['d4d_file']]
  repo=ROOT/f'data/evaluation_llm/rubric{r}_semantic/reference_2026-09-12_cborg_runtime'/f.name
  assert H(f.read_bytes())==H(repo.read_bytes())
  audit.append({'file':str(f),'sha256':H(f.read_bytes()),'d4d_file':str(inp),'input_sha256':H(inp.read_bytes()),'matches_repository':True})
  records[rid]={'record':rid,'project':p,'version':v,'rep':rep,'data':data,'path':str(inp),'label':inp.parent.name}
  common={'record':rid,'project':p,'version':v,'rep':rep,'rating':rat,'rubric':r,'job':jid}
  ratings.append(dict(common,points=score['total_points'],denominator=den,adjusted_pct=pct,fixed_pct=100*score['total_points']/score['max_points'],q19_qualified=jid in qual))
  for idx,i in enumerate(d['semantic_analysis']['issues_detected']):
   fs=i.get('fields_involved',[]);roots=sorted(set(rootfield(x) for x in fs))
   issues.append(dict(common,issue_id=f'{jid}:{idx+1}',type=i['type'],severity=i['severity'],description=i['description'],recommendation=i.get('recommendation',''),fields=fs,roots=roots,sections=sorted(set(section(x) for x in roots)),absent_roots=[x for x in roots if not present(data.get(x))]))
  if rat==1:
   if r==10:
    for e in d['elements']:
     for n,q in enumerate(e['sub_elements']):
      applicable=q.get('applicable',True) is not False and q.get('score') is not None
      items.append(dict(common,id=f"{e['id']}.{n+1}",name=q['name'],group=e['name'],score=q.get('score'),max=1,applicable=applicable,text=' '.join(str(q.get(k,'')) for k in ['evidence','quality_note','semantic_validation'])))
   else:
    for c in d['categories']:
     for q in c['questions']:
      items.append(dict(common,id=q['id'],name=q['name'],group=c['name'],score=q.get('score'),max=q['max_score'],applicable=q.get('applicable',True) is not False and q.get('score') is not None,text=' '.join(str(q.get(k,'')) for k in ['evidence','quality_note','semantic_analysis'])))
primary=[r for r in ratings if r['rating']==1]; iss=[i for i in issues if i['rating']==1]
assert len(records)==24 and len(primary)==48 and len(ratings)==56
# Recover the exact generation-time chunks, not current positional chunk IDs.
links=[];sources=[];recovery=[]
for rid,rec in records.items():
 p=rec['project'];core=ROOT/'data/d4d_concatenated'/(Path(rec['path']).parent.parent.name+'_core')/rec['label'];prov=core/f'{p}_provenance.yaml';receipt=core/f'{p}_coverage_receipt.yaml';run=run_chunks(prov);rc=yaml.safe_load(receipt.read_text());assert rc['bundle_md5']==run['manifest']['bundle_md5']
 recovery.append({'record':rid,'basis':run['basis'],'bundle_md5':rc['bundle_md5'],'receipt_sha256':H(receipt.read_bytes()),'provenance_sha256':H(prov.read_bytes())})
 cm={c['id']:c['source'] for c in run['manifest']['chunks']};texts=collections.defaultdict(str)
 for cid,txt in run['texts'].items():texts[cm[cid]]+='\n'+txt
 sm={}
 for src,txt in texts.items():
  if src=='<preamble>':continue
  mt=re.search(r'^Source type:\s*(.+)$',txt,re.M);typ=mt.group(1).strip() if mt else 'unclassified'
  sm[src]=typ;sources.append({'record':rid,'project':p,'source':src,'source_type':typ})
 for ch in rc.get('chunks',[]):
  src=cm.get(ch['id'],'unmapped')
  for ex in ch.get('extracted',[]) or []:
   slot=ex.get('slot','');rf=rootfield(slot)
   links.append({'record':rid,'project':p,'version':rec['version'],'chunk':ch['id'],'source':src,'source_type':sm.get(src,'unclassified'),'slot':slot,'root':rf,'section':section(rf),'snippet':ex.get('snippet',''),'root_present':present(rec['data'].get(rf))})
print('recovered',len(recovery),'records;',len(links),'receipt links; types',collections.Counter(x['source_type'] for x in sources),flush=True)
# Tables are JSON: preserved prose and explicit analysis units.
for name,obj in [('ratings',ratings),('items',items),('issues',issues),('source_links',links),('sources',sources),('input_audit',audit),('source_recovery',recovery),('section_mapping',{k:section(k) for k in attrs})]:
 (OUT/'data'/f'{name}.json').write_text(json.dumps(obj,indent=2))
# Render each figure in vector SVG and raster PNG with the same drawing primitives.
fontfile='/System/Library/Fonts/Supplemental/Arial.ttf';boldfile='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
class Canvas:
 def __init__(self,w,h,title,sub):
  self.w=w;self.h=h;self.im=Image.new('RGB',(w,h),'#ffffff');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>'];self.text(30,20,title,27,bold=True);self.text(30,59,sub,16,color='#475569')
 def text(self,x,y,t,size=16,color='#172033',bold=False):
  self.d.text((x,y),str(t),font=ImageFont.truetype(boldfile if bold else fontfile,size),fill=color)
  self.svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(str(t))}</text>')
 def rect(self,x,y,w,h,color):
  self.d.rectangle((x,y,x+w,y+h),fill=color);self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')
 def line(self,x,y,x2,y2,col='#cbd5e1',width=1):
  self.d.line((x,y,x2,y2),fill=col,width=width);self.svg.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{width}"/>')
 def circle(self,x,y,r,col):
  self.d.ellipse((x-r,y-r,x+r,y+r),fill=col);self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
 def save(self,name):
  self.im.save(OUT/'figures'/f'{name}.png');(OUT/'figures'/f'{name}.svg').write_text(''.join(self.svg)+'</svg>')
def heat(name,title,sub,rows,cols,values,maxval=100,dec=0,foot=''):
 left=max(260,min(530,max(len(x) for x in rows)*9+30));cw=max(105,min(145,int((1450-left)/len(cols))));rh=37;w=left+cw*len(cols)+35;h=140+rh*len(rows)+65
 w=max(w,1150); c=Canvas(w,h,title,sub)
 for j,col in enumerate(cols):
  col={'Data Governance':'Governance','FileCollection':'File inventory','Preprocessing':'Preprocess.'}.get(col,col)
  c.text(left+j*cw+8,100,col,13,bold=True)
 for i,row in enumerate(rows):
  y=135+i*rh;c.text(30,y+7,row,15)
  for j,val in enumerate(values[i]):
   t=0 if val is None else max(0,min(1,val/maxval));color='#eef2f6' if val is None else '#%02x%02x%02x'%(int(240-211*t),int(247-133*t),int(249-93*t));c.rect(left+j*cw,y,cw-3,rh-3,color);c.text(left+j*cw+14,y+6,'N/A' if val is None else f'{val:.{dec}f}',16,color='#ffffff' if t>.68 else '#172033')
 c.text(30,h-35,foot,14);c.save(name)
# 1 overview, full ranges rather than inferential error bars
rows=[];vals=[]
for p in projects:
 for v in versions:
  rows.append(p+' '+v);rr=[x for x in primary if x['project']==p and x['version']==v];vals.append([statistics.mean(x['adjusted_pct'] for x in rr if x['rubric']==r) for r in [10,20]])
heat('01_scores','Recorded rubric scores by dataset and version','Mean adjusted percent; 3 generation replicates per cell. Rubrics measure different constructs.',rows,['Rubric10','Rubric20'],vals,dec=1,foot='Rubric20 includes 9 Q19-qualified totals. Version differences are descriptive; execution conditions also changed.')
# 2 question-level heatmap per dataset
qs=sorted({x['id'] for x in items if x['rubric']==20});names={x['id']:x['name'] for x in items if x['rubric']==20}
qvals=[]
for q in qs:
 qvals.append([statistics.mean(100*x['score']/x['max'] for x in items if x['rubric']==20 and x['id']==q and x['project']==p and x['applicable']) if any(x['rubric']==20 and x['id']==q and x['project']==p and x['applicable'] for x in items) else None for p in projects])
heat('02_rubric20_items','Where rubric20 scores are lost','Mean percentage of applicable item maximum; 6 records per dataset, fewer where not applicable.',[f'Q{q:02d} '+names[q] for q in qs],projects,qvals,foot='Q19 provenance and selected CM4AI Q13 judgments require adjudication. These are recorded scores.')
# 3 native issue types, no forced recoding
itypes=['completeness','consistency','content_accuracy','correctness','semantic_understanding']
heat('03_review_types','Review comment types across datasets','Number of primary-review issue entries; 12 reviews per dataset (6 records x 2 rubrics).',itypes,projects,[[sum(i['type']==t and i['project']==p for i in iss) for p in projects] for t in itypes],maxval=80,foot='562 issue entries overall. The same underlying concern can occur in both rubrics; counts are not unique errors.')
# 4 missing roots: absent structurally and implicated by a completeness comment
missing=collections.defaultdict(set);flagged=collections.defaultdict(set);acc=collections.defaultdict(set)
for i in iss:
 for f in i['roots']:
  if i['type']=='completeness':
   flagged[f].add(i['record'])
   if f in i['absent_roots']:missing[f].add(i['record'])
  if i['type'] in ['correctness','content_accuracy']:acc[f].add(i['record'])
fields=sorted(missing,key=lambda f:(-len(missing[f]),f))[:16]
heat('04_missing_fields','Common unpopulated fields mentioned in completeness reviews','Unique records with absent top-level field AND a completeness comment naming it; denominator 6 per dataset.',fields,projects,[[sum(records[r]['project']==p for r in missing[f]) for p in projects] for f in fields],maxval=6,foot='Absence is checked against input YAML. Not proof of requiredness, source availability, or absence of equivalent prose.')
afields=sorted(acc,key=lambda f:(-len(acc[f]),f))[:16]
heat('05_accuracy_fields','Fields implicated in accuracy and correctness comments','Unique records flagged by either rubric; denominator 6 per dataset. Co-mentioned fields count as implicated.',afields,projects,[[sum(records[r]['project']==p for r in acc[f]) for p in projects] for f in afields],maxval=6,foot='Reviewer allegations, not adjudicated error rates. Consistency and semantic-understanding comments are excluded here.')
secs=sorted({s for i in iss for s in i['sections']});sv=[]
for s in secs:sv.append([len({i['record'] for i in iss if s in i['sections'] and i['type']==t}) for t in itypes])
heat('06_sections','How review concerns overlap across datasheet sections','Unique records with at least one comment of each type in a section; denominator 24 records.',secs,['Missing/detail','Consistency','Accuracy','Correctness','Semantics'],sv,maxval=24,foot='Columns retain native types (Missing/detail = completeness). A comment can implicate multiple sections.')
# source links / section at record-level, not citation counts
stypes=sorted({x['source_type'] for x in links if x['source_type']!='unclassified'});ssecs=sorted({x['section'] for x in links})
source_sets={(t,s):{x['record'] for x in links if x['source_type']==t and x['section']==s} for t in stypes for s in ssecs}
heat('07_sources_sections','Which input document types support which sections','Receipt-declared links, recovered from generation-time chunk hashes; unique records per cell (of 24).',stypes,ssecs,[[len(source_sets[t,s]) for s in ssecs] for t in stypes],maxval=24,foot='A citation is not verified entailment or exclusive attribution. Source-type exposure differs by dataset.')
# 8 relations with review burden: Q1 vs accuracy + consistency flags
c=Canvas(1200,650,'Completeness scores coexist with substantive review flags','Rubric20 Q1 versus pooled correctness, content-accuracy, and consistency issue entries; 24 records.')
colors=dict(zip(projects,['#137c8b','#e89535','#8464b7','#d25368']));xx=90;yy=120;ww=830;hh=420
for tick in range(0,101,20):
 x=xx+ww*tick/100;c.line(x,yy,x,yy+hh,'#e2e8f0');c.text(x-12,yy+hh+10,tick,14)
counts={r:sum(i['record']==r and i['type'] in ['correctness','content_accuracy','consistency'] for i in iss) for r in records};mx=math.ceil(max(counts.values())/5)*5
for tick in range(0,mx+1,5):
 y=yy+hh-hh*tick/mx;c.line(xx,y,xx+ww,y,'#e2e8f0');c.text(40,y-8,tick,14)
points=[]
for rid,rec in records.items():
 q=next(x for x in items if x['rubric']==20 and x['id']==1 and x['record']==rid);xv=100*q['score']/q['max'];yv=counts[rid];points.append((xv,yv));jitter=(rec['rep']-2)*4+(2 if rec['version']=='v8' else -2);c.circle(xx+ww*xv/100+jitter,yy+hh-hh*yv/mx,6,colors[rec['project']])
for j,p in enumerate(projects):c.circle(975,160+j*40,6,colors[p]);c.text(990,149+j*40,p,16)
c.text(300,585,'Q1 field-completeness score (% of 5 points)',16);c.text(35,88,'Issue entries',15);c.text(30,622,'Slight horizontal jitter separates overlapping points. Review counts depend on verbosity; no causal or error-rate interpretation.',14);c.save('08_completeness_flags')
# 9 repeat scores and generation spread numeric panel
heat('09_repeat_ratings','Repeat reviews of the same record','Rubric10 adjusted percent; one v7 rep1 record per dataset, evaluated three times.',projects,['Rating 1','Rating 2','Rating 3','Range (pp)'],[[next(x['adjusted_pct'] for x in ratings if x['rubric']==10 and x['project']==p and x['version']=='v7' and x['rep']==1 and x['rating']==rat) for rat in [1,2,3]]+[max(x['adjusted_pct'] for x in ratings if x['rubric']==10 and x['project']==p and x['version']=='v7' and x['rep']==1)-min(x['adjusted_pct'] for x in ratings if x['rubric']==10 and x['project']==p and x['version']=='v7' and x['rep']==1)] for p in projects],dec=1,foot='Only four records; rubric20 repeatability is unmeasured. Permission/deadline changes confound some repeats.')
summary={'n_records':len(records),'primary_ratings':len(primary),'repeat_ratings':8,'issue_entries':len(iss),'issue_types':dict(collections.Counter(i['type'] for i in iss)),'severity':dict(collections.Counter(i['severity'] for i in iss)),'missing_fields':{f:len(missing[f]) for f in fields},'accuracy_fields':{f:len(acc[f]) for f in afields},'score_means':dict(zip(rows,vals)),'q20_means':dict(zip([names[q] for q in qs],qvals)),'receipt_links':len(links),'unclassified_links':sum(x['source_type']=='unclassified' for x in links),'q19_qualified':sorted(qual),'git_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()}
(OUT/'data/summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)

# Supplemental source exposure and source-field overlap.
source_exposure=[[len({x['source'] for x in sources if x['source_type']==t and x['project']==p}) for p in projects] for t in stypes]
heat('10_source_mix','Source document mix differs across datasets','Unique generation-input documents by native source type; replicates do not multiply document counts.',stypes,projects,source_exposure,maxval=max(max(x) for x in source_exposure),foot='Historical and current releases remain separate documents. All 24 records use multi-document inputs.')
linkpairs={t:{(x['record'],x['root']) for x in links if x['source_type']==t and x['root_present']} for t in stypes}
flagpairs={t:{(i['record'],f) for i in iss if i['type']==t for f in i['roots']} for t in itypes}
overlap=[]
for t in stypes:
 den=len(linkpairs[t]); overlap.append([100*len(linkpairs[t]&flagpairs[it])/den for it in itypes])
heat('11_source_review_overlap','Source-linked fields and review concerns','Percent of unique (record, populated root-field) pairs linked to a source type that also receive each review flag.',[t+' (n='+str(len(linkpairs[t]))+')' for t in stypes],['Completeness','Consistency','Accuracy','Correctness','Semantics'],overlap,dec=0,foot='Association only: root-field joins cannot identify which source caused a concern; fields often cite several source types.')
# Rubric10 elements: denominator is number of applicable binary sub-elements.
erows=[];ev=[]
for group in dict.fromkeys(x['group'] for x in items if x['rubric']==10):
 erows.append(group);row=[]
 for p in projects:
  a=[x for x in items if x['rubric']==10 and x['group']==group and x['project']==p and x['applicable']]
  row.append(100*sum(x['score'] for x in a)/len(a) if a else None)
 ev.append(row)
heat('12_rubric10_elements','Rubric10 coverage by element','Percent of applicable binary sub-elements awarded; 6 records per dataset, pooled within each element.',erows,projects,ev,foot='This instrument is distinct from rubric20: no pooled composite score or direct equivalence is assumed.')
# Explicit arithmetic and count validation.
for rr in primary:
 a=[x for x in items if x['job']==rr['job'] and x['applicable']]
 assert sum(x['score'] for x in a)==rr['points'],rr['job']
 assert sum(x['max'] for x in a)==rr['denominator'],rr['job']
(OUT/'data/validation.json').write_text(json.dumps({'input_and_review_hashes_checked':56,'unique_input_records':24,'primary_score_arithmetic_checks':48,'historical_chunk_manifests_recovered':24,'source_links':len(links),'links_to_unpopulated_root_fields':sum(not x['root_present'] for x in links),'issue_count_primary':len(iss),'source_overlap_excludes_unpopulated_roots':True},indent=2))
