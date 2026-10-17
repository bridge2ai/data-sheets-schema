"""Follow-up analyses. Run after the initial analysis; no source files are modified."""
import json,re,hashlib,collections,itertools,statistics,html,math,random
from pathlib import Path
import yaml,numpy as np
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parents[1];D=O/'data/followup';P=['AI_READI','CHORUS','CM4AI','VOICE'];ROOT=Path(__file__).resolve().parents[3]
load=lambda n:json.loads((O/'data'/f'{n}.json').read_text())
R=load('ratings');I=load('issues');Q=load('items');primary=[x for x in R if x['rating']==1];issues=[x for x in I if x['rating']==1];recmeta={x['record']:x for x in primary};rids=sorted(recmeta);A=load('input_audit');records={}
for a in A:
 p=Path(a['d4d_file']);p=p if p.exists() else (ROOT/str(a['d4d_file'])[str(a['d4d_file']).index('data/'):] if 'data/' in str(a['d4d_file']) else p)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==a['input_sha256'];r=re.match(r'(.+_v[78]_rep\d+)',Path(a['file']).name)[1];records[r]=yaml.safe_load(p.read_text())
assert len(records)==24
present=lambda x:x is not None and x!='' and x!=[] and x!={}
family=lambda t:'Accuracy/correctness' if t in ['correctness','content_accuracy'] else {'completeness':'Completeness','consistency':'Consistency','semantic_understanding':'Semantic understanding'}[t]
def save(n,x):(D/f'{n}.json').write_text(json.dumps(x,indent=2))
# Structural absence for the fixed, previously selected 16 fields. Do not select a new top list.
fields=list(load('summary')['missing_fields']);presence=[]
for rid in rids:
 for f in fields:
  found=present(records[rid].get(f));ids=[i['issue_id'] for i in issues if i['record']==rid and i['type']=='completeness' and f in i['roots']]
  presence.append({'record':rid,'project':recmeta[rid]['project'],'field':f,'populated':found,'completeness_mentioned':bool(ids),'issue_ids':ids,'state':'Populated' if found else ('Absent, mentioned' if ids else 'Absent, not mentioned')})
presummary=[{'field':f,**{state:sum(x['field']==f and x['state']==state for x in presence) for state in ['Absent, mentioned','Absent, not mentioned','Populated']}} for f in fields]
save('field_presence',presence);save('field_presence_summary',presummary)
# Positive-set agreement: no artificial universe of presumed negatives.
def fieldset(rid,rubric,rating,typed):
 return {(family(i['type']),f) if typed else f for i in I if i['record']==rid and i['rubric']==rubric and i['rating']==rating for f in i['roots']}
def overlap(a,b):
 u=a|b;inter=a&b
 return {'a_count':len(a),'b_count':len(b),'shared':len(inter),'union':len(u),'jaccard':len(inter)/len(u) if u else None,'dice':2*len(inter)/(len(a)+len(b)) if a or b else None,'a_only':sorted(a-b),'b_only':sorted(b-a)}
agreements=[]
for rid in rids:
 for typed in [False,True]:agreements.append({'record':rid,'project':recmeta[rid]['project'],'typed':typed,**overlap(fieldset(rid,10,1,typed),fieldset(rid,20,1,typed))})
repeats=[]
for p in P:
 rid=f'{p}_v7_rep1'
 for a,b in itertools.combinations([1,2,3],2):
  rr=[x for x in R if x['record']==rid and x['rubric']==10 and x['rating'] in [a,b]]
  for typed in [False,True]:repeats.append({'record':rid,'project':p,'ratings':[a,b],'typed':typed,'score_difference_pp':abs(rr[0]['adjusted_pct']-rr[1]['adjusted_pct']),**overlap(fieldset(rid,10,a,typed),fieldset(rid,10,b,typed))})
save('cross_rubric_agreement',agreements);save('repeat_agreement',repeats)
# Field-topic signatures: transparent grouping, not semantic adjudication.
# Strict preserves native type and all field roots. Broad pools accuracy labels and removes context-only roots.
def signature(i,broad=False):
 fs=sorted(set(i['roots'])-({'source_caveats','notes','description'} if broad else set())) or sorted(i['roots'])
 return (family(i['type']) if broad else i['type'],tuple(fs))
signatures=[];dedup=[]
for broad in [False,True]:
 g=collections.defaultdict(list)
 for i in issues:g[(i['record'],signature(i,broad))].append(i)
 for (rid,sig),rows in g.items():signatures.append({'record':rid,'project':recmeta[rid]['project'],'mode':'broad' if broad else 'strict','type':sig[0],'roots':list(sig[1]),'issue_ids':[x['issue_id'] for x in rows],'rubrics':sorted(set(x['rubric'] for x in rows))})
for p in P:dedup.append({'project':p,'raw_comments':sum(x['project']==p for x in issues),'strict_signatures':sum(x['project']==p and x['mode']=='strict' for x in signatures),'broad_signatures':sum(x['project']==p and x['mode']=='broad' for x in signatures)})
save('field_topic_signatures',signatures);save('deduplication_counts',dedup)
glob=collections.defaultdict(list)
for x in signatures:
 if x['mode']=='broad':glob[(x['type'],tuple(x['roots']))].append(x)
top=sorted(glob.items(),key=lambda x:(-len(x[1]),x[0]))[:16]
save('recurring_field_topics',[{'family':k[0],'roots':list(k[1]),'record_count':len(v),'records':[x['record'] for x in v],'issue_ids':sum((x['issue_ids'] for x in v),[])} for k,v in top])
# Uniform item omission. These are diagnostic score subsets, not corrected rubric scores.
sensitivity=[]
for rr in primary:
 if rr['rubric']!=20:continue
 qi=[q for q in Q if q['record']==rr['record'] and q['rubric']==20 and q['applicable']]
 for name,omit in [('Original',set()),('Without Q19',{19}),('Without Q13 & Q19',{13,19})]:
  a=[q for q in qi if q['id'] not in omit];points=sum(q['score'] for q in a);den=sum(q['max'] for q in a)
  sensitivity.append({'record':rr['record'],'project':rr['project'],'version':rr['version'],'view':name,'points':points,'applicable_max':den,'percent':100*points/den})
score_summary=[]
for p in P:
 for view in ['Original','Without Q19','Without Q13 & Q19']:
  vv={v:statistics.mean(x['percent'] for x in sensitivity if x['project']==p and x['version']==v and x['view']==view) for v in ['v7','v8']}
  score_summary.append({'project':p,'view':view,'v7_mean':vv['v7'],'v8_mean':vv['v8'],'v8_minus_v7':vv['v8']-vv['v7']})
save('score_sensitivity',sensitivity);save('score_sensitivity_summary',score_summary)
# Score-category distributions, with denominator visible.
itemdist=[]
for qid in range(1,21):
 rows=[q for q in Q if q['rubric']==20 and q['id']==qid];counts=collections.Counter('Not applicable' if not q['applicable'] else ('Full' if q['score']==q['max'] else ('Zero' if q['score']==0 else 'Partial')) for q in rows)
 itemdist.append({'question':qid,'name':rows[0]['name'],**{c:counts[c] for c in ['Full','Partial','Zero','Not applicable']}})
save('item_score_distribution',itemdist)
# Summary preserves full denominator detail for source-section figures from the earlier analysis.
source_contrasts=load('exploratory_statistics')['source_contrasts']
summary={'field_absence_total':sum(not x['populated'] for x in presence),'absence_mentioned':sum(not x['populated'] and x['completeness_mentioned'] for x in presence),'record_field_pairs':len(presence),'repeat_summary':{},'cross_rubric_summary':{},'strict_signature_total':sum(x['mode']=='strict' for x in signatures),'broad_signature_total':sum(x['mode']=='broad' for x in signatures),'sample_n':32}
for p in P:
 summary['repeat_summary'][p]={'mean_field_jaccard':statistics.mean(x['jaccard'] for x in repeats if x['project']==p and not x['typed']),'mean_typed_jaccard':statistics.mean(x['jaccard'] for x in repeats if x['project']==p and x['typed']),'score_range_pp':max(x['adjusted_pct'] for x in R if x['record']==f'{p}_v7_rep1' and x['rubric']==10)-min(x['adjusted_pct'] for x in R if x['record']==f'{p}_v7_rep1' and x['rubric']==10)}
 summary['cross_rubric_summary'][p]={'mean_field_jaccard':statistics.mean(x['jaccard'] for x in agreements if x['project']==p and not x['typed']),'mean_typed_jaccard':statistics.mean(x['jaccard'] for x in agreements if x['project']==p and x['typed'])}
save('summary',summary)
# Graphics helper: identical vector and raster rendering.
FONT='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
class Canvas:
 def __init__(self,w,h,title,sub):
  self.w=w;self.h=h;self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/>'];self.text(30,20,title,27,bold=True);self.text(30,62,sub,16,color='#526277')
 def text(self,x,y,t,size=16,color='#172033',bold=False):
  self.d.text((x,y),str(t),font=ImageFont.truetype(BOLD if bold else FONT,size),fill=color);self.svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(str(t))}</text>')
 def rect(self,x,y,w,h,col):
  self.d.rectangle((x,y,x+w,y+h),fill=col);self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}"/>')
 def line(self,x,y,x2,y2,col='#ccd6df',width=1):
  self.d.line((x,y,x2,y2),fill=col,width=width);self.svg.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{width}"/>')
 def circle(self,x,y,r,col):
  self.d.ellipse((x-r,y-r,x+r,y+r),fill=col);self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
 def save(self,n):
  self.im.save(O/'figures'/f'{n}.png');(O/'figures'/f'{n}.svg').write_text(''.join(self.svg)+'</svg>')
def heat(name,title,sub,rows,cols,vals,maxval=100,dec=0,foot='',signed=False):
 left=max(285,min(510,max(map(len,rows))*8+40));cw=145;rh=38;w=max(1250,left+cw*len(cols)+45);h=180+rh*len(rows);c=Canvas(w,h,title,sub)
 for j,col in enumerate(cols):c.text(left+j*cw+5,105,col,14,bold=True)
 for i,row in enumerate(rows):
  y=137+i*rh;c.text(30,y+6,row,15)
  for j,v in enumerate(vals[i]):
   if v is None:col='#edf0f3';label='N/A';t=0
   else:
    t=min(abs(v)/maxval,1);end=(191,85,67) if signed and v<0 else (23,121,148);col='#%02x%02x%02x'%tuple(int(245*(1-t)+e*t) for e in end);label=f'{v:+.{dec}f}' if signed else f'{v:.{dec}f}'
   c.rect(left+j*cw,y,cw-3,rh-3,col);c.text(left+j*cw+15,y+6,label,16,color='white' if t>.7 else '#172033')
 c.text(30,h-27,foot,14);c.save(name)
def stacked(name,title,sub,rows,states,colors,den,foot):
 c=Canvas(1350,185+len(rows)*38,title,sub);left=340;ww=830
 for j,(state,col) in enumerate(zip(states,colors)):
  x=30+j*310;c.rect(x,101,14,14,col);c.text(x+22,97,state,15)
 for i,row in enumerate(rows):
  yy=139+i*38;c.text(30,yy+5,row['label'],15);x=left
  for state,col in zip(states,colors):
   n=row.get(state,0);w=ww*n/den
   if w:c.rect(x,yy,w,28,col)
   if w>=25:c.text(x+w/2-5,yy+4,n,15,color='white' if col not in ['#e1e8ee','#d6b867'] else '#172033')
   x+=w
  c.text(left+ww+12,yy+4,f'n={den}',14)
 c.text(30,c.h-28,foot,14);c.save(name)
stacked('15_structural_absence','Completeness comments do not enumerate all structural absences','Fixed list of 16 fields from the initial report; 24 records per row. No applicability or source-availability inference.',[dict(label=x['field'],**x) for x in presummary],['Absent, mentioned','Absent, not mentioned','Populated'],['#b75847','#d6b867','#39869b'],24,'Mentioned = at least one completeness comment names the field. Some absences are appropriate; access pages are not direct-download URLs.')
heat('16_agreement','Agreement on flagged fields differs from agreement on scores','Mean positive-set Jaccard overlap (%). Type-aware = (review family, field); higher is more overlap.',P,['Cross: fields','Cross: typed','Repeat: fields','Repeat: typed'],[[100*summary['cross_rubric_summary'][p]['mean_field_jaccard'],100*summary['cross_rubric_summary'][p]['mean_typed_jaccard'],100*summary['repeat_summary'][p]['mean_field_jaccard'],100*summary['repeat_summary'][p]['mean_typed_jaccard']] for p in P],dec=1,foot='Cross-rubric: 6 records/dataset. Repeat: 3 pairs of ratings on one fixed record/dataset. Overlap is not factual agreement.')
heat('17_score_sensitivity','Do version differences depend on the disputed rubric20 items?','Mean adjusted percentage-point difference, v8 minus v7; 3 records per version and dataset.',P,['Original','No Q19','No Q13/Q19'],[[next(x['v8_minus_v7'] for x in score_summary if x['project']==p and x['view']==v) for v in ['Original','Without Q19','Without Q13 & Q19']] for p in P],maxval=7,dec=2,signed=True,foot='Uniform item removal is a diagnostic, not a replacement or corrected rubric. Positive = higher recorded v8 score.')
heat('18_denominator_effect','Applicability changes the reported score most for CM4AI','Mean adjusted score minus fixed-denominator score, percentage points; original ratings only.',[p+' '+v for p in P for v in ['v7','v8']],['Rubric10','Rubric20'],[[statistics.mean(r['adjusted_pct']-r['fixed_pct'] for r in primary if r['project']==p and r['version']==v and r['rubric']==rub) for rub in [10,20]] for p in P for v in ['v7','v8']],maxval=8,dec=2,foot='Both percentages are valid summaries of different denominators. A larger uplift is not evidence of better documentation.')
heat('19_signature_counts','Repeated field topics account for some, but not all, review volume','Counts per dataset across 12 primary reviews. Grouping is within record; it cannot certify unique errors.',P,['Raw comments','Strict groups','Broad groups'],[[x['raw_comments'],x['strict_signatures'],x['broad_signatures']] for x in dedup],maxval=180,foot='Strict: native type + full root-field set. Broad: pooled accuracy labels, with generic context roots removed. Different concerns may merge.')
stacked('20_item_distributions','Rubric20 item distributions expose ceiling effects and exclusions','24 records per item; full, partial, zero, and not-applicable judgments shown separately.',[dict(label=f"Q{x['question']:02d} "+x['name'][:35],**x) for x in itemdist],['Full','Partial','Zero','Not applicable'],['#39869b','#d6b867','#b75847','#e1e8ee'],24,'The Q19 and selected Q13 judgments retain audit qualifications. Distribution is over recorded judgments, not verified quality.')
rows=[];vs=[]
for typ in ['NIH project page','data resource','documentation','publication']:
 for outcome in ['Completeness flags','Accuracy/correctness flags','Consistency flags']:
  x=next(x for x in source_contrasts if x['source_type']==typ and x['outcome']==outcome);rows.append(typ+' / '+outcome.replace(' flags',''));vs.append([x['dataset_effects'].get(p) for p in P])
heat('21_source_heterogeneity','Source associations are not uniform across datasets','Within-section flagged-field-rate contrast (percentage points): linked fields minus other receipt-linked fields.',rows,P,vs,maxval=45,dec=1,signed=True,foot='Same descriptive contrasts as the original report; no additional tests. N/A = source type lacks an eligible comparison in that dataset.')
# Narrower nested-path sensitivity is descriptive only: how much source-review linkage survives.
links=load('source_links');pathnorm=lambda x:re.sub(r'\[[^\]]*\]','',x)
linkpaths=collections.defaultdict(list)
for x in links:
 if x['root_present']:linkpaths[(x['record'],x['source_type'])].append(pathnorm(x['slot']))
matchrows=[]
for i in issues:
 for f in i['fields']:
  fp=pathnorm(f);root=re.split(r'[.\[]',fp)[0]
  for t in sorted({x['source_type'] for x in links if x['record']==i['record']}):
   candidates=[p for p in linkpaths[(i['record'],t)] if p.split('.')[0]==root]
   if not candidates:continue
   exact_nested='.' in fp and any(p==fp for p in candidates)
   ancestor='.' in fp and any(p.startswith(fp+'.') or fp.startswith(p+'.') for p in candidates)
   matchrows.append({'issue_id':i['issue_id'],'record':i['record'],'source_type':t,'field':f,'normalized_path':fp,'exact_nested_match':exact_nested,'ancestor_match_only':ancestor and not exact_nested,'root_only_comment':'.' not in fp,'candidate_receipt_paths':sorted(set(candidates))})
save('path_linkage_sensitivity',matchrows)
for n in ['Original','Without Q19','Without Q13 & Q19']:assert len([x for x in sensitivity if x['view']==n])==24
for x in presummary:assert sum(x[c] for c in ['Absent, mentioned','Absent, not mentioned','Populated'])==24
save('checks',{'input_hashes_rechecked':len(A),'record_field_pairs':len(presence),'cross_rubric_comparisons':len(agreements)//2,'repeat_pairs':len(repeats)//2,'sensitivity_records':len(sensitivity),'original_item_sum_verified':all(abs(x['percent']-next(r['adjusted_pct'] for r in primary if r['record']==x['record'] and r['rubric']==20))<1e-9 for x in sensitivity if x['view']=='Original')})
print(json.dumps(summary,indent=2));print(json.dumps(score_summary,indent=2));print(json.dumps(presummary,indent=2))
# Provisional evidence-review dispositions for the balanced sample.
assess=json.loads((D/'sample_assessments.json').read_text());cats=list(dict.fromkeys(a['primary_disposition'] for a in assess));fams=['Completeness','Consistency','Accuracy/correctness','Semantic understanding']
heat('22_sample_dispositions','What the 32-comment evidence review changes','One primary disposition per comment; balanced sample, not a population estimate or human-validated gold standard.',cats,['Completeness','Consistency','Accuracy','Semantics'],[[sum(a['primary_disposition']==c and a['family']==f for a in assess) for f in fams] for c in cats],maxval=8,foot='Compound comments may contain valid and overstated components. Read the evidence table before interpreting any category as an error.')
# A reproducible, conservative coding of recurring topics; overlapping rules, not unique-error clustering.
rules={
 'Access URL representation':r'download_url',
 'De-identification tension':r'NoDeIdentification',
 'Institution attribution':r'Washington University in St[.]? Louis|University of Washington',
 'Processing-software role':r'used_software|software.{0,100}(produc|transform)|no software is named',
 'Variable-level documentation':r'variable.level|column.level|data dictionar|variables is absent|variables field|variables enumerates',
 'Impact assessment / social impacts':r'data_protection_impacts|future_use_impacts|DPIA|impact assessment',
 'Version / release context':r'version numbering|version.sequence|version string|release date|semi.annual|version history|errata',
 'Provenance representation':r'PROV.O|provenance graph|was_derived_from|parent_datasets',
}
assign=[]
for i in issues:
 for theme,pat in rules.items():
  if re.search(pat,i['description'],re.I):assign.append({'issue_id':i['issue_id'],'record':i['record'],'project':i['project'],'theme':theme})
save('topic_rules',rules);save('topic_assignments',assign)
heat('23_recurring_topics','Recurring review topics across generated records','Selected transparent text rules; each cell counts unique records (of 6), deduplicated across both rubrics.',list(rules),P,[[len({a['record'] for a in assign if a['theme']==t and a['project']==p}) for p in P] for t in rules],maxval=6,foot='Topics overlap and the list is not exhaustive. These are review themes, not adjudicated distinct defects or factual error rates.')
linkstates=['Root-only comment','Same nested path','Ancestor relation','Other path in root']
linksummary=[]
for t in sorted(set(x['source_type'] for x in matchrows)):
 rows=[x for x in matchrows if x['source_type']==t];counts=collections.Counter('Root-only comment' if x['root_only_comment'] else ('Same nested path' if x['exact_nested_match'] else ('Ancestor relation' if x['ancestor_match_only'] else 'Other path in root')) for x in rows)
 linksummary.append({'source_type':t,'n':len(rows),**{s:counts[s] for s in linkstates}})
save('path_linkage_summary',linksummary)
heat('24_path_specificity','How specific are the source-to-comment matches?','Percent of candidate (issue, field, source-type) links in each path category; n counts links, not independent observations.',[x['source_type']+f" (n={x['n']})" for x in linksummary],['Root-only','Same nested','Ancestor','Sibling/other'],[[100*x[s]/x['n'] for s in linkstates] for x in linksummary],maxval=100,dec=0,foot='Array indices are normalized away. Even a same-path match does not establish snippet entailment or attribute an error to that source.')
