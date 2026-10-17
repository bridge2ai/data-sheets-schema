"""v8-only measurement from retained evaluation tables; original evaluations are not rerun."""
from pathlib import Path
import json,re,hashlib,collections,statistics,math,html,base64,zipfile
import yaml
from plotting import Canvas,heat,stacked
O=Path(__file__).resolve().parent;D=O/'data';D.mkdir(exist_ok=True);(O/'figures').mkdir(exist_ok=True);ROOT=Path(__file__).resolve().parents[2]
BASE=O.parent/'D4D_v7_v8_review_figures_and_data/data' if (O.parent/'D4D_v7_v8_review_figures_and_data/data/ratings.json').exists() else O/'data';load=lambda n:json.loads((BASE/f'{n}.json').read_text());P=['AI_READI','CHORUS','CM4AI','VOICE'];T=['completeness','consistency','content_accuracy','correctness','semantic_understanding']
R=[r for r in load('ratings') if r['version']=='v8' and r['rating']==1];I=[r for r in load('issues') if r['version']=='v8' and r['rating']==1];Q=[r for r in load('items') if r['version']=='v8' and r['rating']==1];L=[r for r in load('source_links') if r['version']=='v8'];rids=sorted({r['record'] for r in R});meta={r['record']:r for r in R};cross=load('section_mapping')
assert len(R)==24 and len(rids)==12 and all(r['version']=='v8' for r in R)
A=[a for a in load('input_audit') if '_v8_' in Path(a['file']).name];records={};audit=[]
for a in A:
 p=Path(a['d4d_file']);p=p if p.exists() else (ROOT/str(a['d4d_file'])[str(a['d4d_file']).index('data/'):] if 'data/' in str(a['d4d_file']) else p)
 f=Path(a['file']);f=f if f.exists() else (ROOT/str(a['file'])[str(a['file']).index('data/'):] if 'data/' in str(a['file']) else f)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==a['input_sha256'];assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256'];rid=re.match(r'(.+_v8_rep\d+)',f.name)[1];records[rid]=yaml.safe_load(p.read_text());audit.append(a)
assert len(records)==12 and len(A)==24
for r in R:
 q=[q for q in Q if q['job']==r['job'] and q['applicable']];assert sum(x['score'] for x in q)==r['points'];assert sum(x['max'] for x in q)==r['denominator']
save=lambda n,x:(D/f'{n}.json').write_text(json.dumps(x,indent=2))
SOURCES=[x for x in load('sources') if x['record'] in rids];RECOVERY=[x for x in load('source_recovery') if x['record'] in rids]
for n,x in [('ratings',R),('issues',I),('items',Q),('source_links',L),('input_audit',audit),('sources',SOURCES),('source_recovery',RECOVERY),('section_mapping',cross)]:save(n,x)
# Dataset scores and original applicability basis, computed strictly from v8.
score=[]
for p in P:
 for rub in [10,20]:
  a=[r for r in R if r['project']==p and r['rubric']==rub];score.append({'project':p,'rubric':rub,'n':len(a),'adjusted_mean':statistics.mean(r['adjusted_pct'] for r in a),'adjusted_min':min(r['adjusted_pct'] for r in a),'adjusted_max':max(r['adjusted_pct'] for r in a),'fixed_mean':statistics.mean(r['fixed_pct'] for r in a),'q19_qualified':sum(r['q19_qualified'] for r in a)})
save('score_summary',score)
# Figure 1: individual replicate dots with range and mean, no inferred confidence intervals.
c=Canvas(1340,590,'v8 recorded scores: show all three generation replicates','Adjusted percent. Dot colors identify rubric; red rings mark rubric20 Q19 qualifications. Axis shown: 50–100%.')
left=240;ww=790
for tick in range(50,101,10):
 x=left+ww*(tick-50)/50;c.line(x,112,x,450,'#e0e7ee');c.text(x-10,87,str(tick),14)
cols={10:'#168194',20:'#7952a1'}
for j,p in enumerate(P):
 y=145+j*87;c.text(30,y+7,p,18,bold=True)
 for k,rub in enumerate([10,20]):
  yy=y+k*33;a=sorted([r for r in R if r['project']==p and r['rubric']==rub],key=lambda r:r['rep']);values=[r['adjusted_pct'] for r in a];xx=lambda v:left+ww*(v-50)/50;c.line(xx(min(values)),yy,xx(max(values)),yy,cols[rub],2)
  for z,r in enumerate(a):
   x=xx(r['adjusted_pct']);dy=(z-1)*6
   if r['q19_qualified']:c.circle(x,yy+dy,8,'#b8493c');c.circle(x,yy+dy,6,'#ffffff')
   c.circle(x,yy+dy,4,cols[rub])
  mean=statistics.mean(values);c.line(xx(mean),yy-13,xx(mean),yy+13,'#172033',2);c.text(1060,yy-11,f'R{rub}: {mean:.1f} [{min(values):.1f}–{max(values):.1f}]',15)
c.circle(70,500,5,cols[10]);c.text(84,489,'Rubric10',16);c.circle(245,500,5,cols[20]);c.text(259,489,'Rubric20',16);c.line(440,487,440,512,'#172033',2);c.text(455,489,'Mean; line spans min–max',16)
c.text(30,548,'12 records / 24 primary ratings. Replicate range is descriptive, not a confidence interval. Rubrics measure different constructs.',14);c.save('01_v8_scores')
# 2 item profile.
qrows=[];qvals=[];qtable=[]
shortnames={1:'Field completeness',2:'Entry length adequacy',3:'Keyword diversity',4:'File enumeration / type variety',5:'File size availability',6:'Dataset identification',7:'Funding / acknowledgements',8:'Ethical and privacy declarations',9:'Access and governance',10:'Interoperability / standards',11:'Tool and software transparency',12:'Collection protocol clarity',13:'Versioning / maintenance',14:'Associated publications',15:'Human subject representation',16:'Findability',17:'Accessibility',18:'Reuse guidance / social impact',19:'Integrity / provenance / quality',20:'Bias documentation / responsible AI'}
for qid in range(1,21):
 qrows.append(f'Q{qid:02d} '+shortnames[qid]);vals=[]
 for p in P:
  a=[q for q in Q if q['rubric']==20 and q['id']==qid and q['project']==p];aa=[q for q in a if q['applicable']];v=statistics.mean(100*q['score']/q['max'] for q in aa) if aa else None;vals.append(v);qtable.append({'question':qid,'name':a[0]['name'],'project':p,'applicable_n':len(aa),'total_n':len(a),'mean_percent':v,'full_n':sum(q['score']==q['max'] for q in aa),'partial_n':sum(0<q['score']<q['max'] for q in aa),'zero_n':sum(q['score']==0 for q in aa)})
 qvals.append(vals)
save('rubric20_profile',qtable)
heat('02_v8_item_profile','v8 rubric20 profile: where recorded scores are lost','Mean percentage of applicable item maximum; 3 records per dataset. Applicability counts are in the report table.',qrows,P,qvals,dec=0,foot='Q19 and selected CM4AI Q13 judgments remain qualified. Item percentages are not independently verified accuracy rates.')
# 3 presence, selecting only on v8 completeness comments and v8 structural absence.
present=lambda v:v is not None and v!='' and v!=[] and v!={}
flagged=collections.defaultdict(set);missing=collections.defaultdict(set);accuracy=collections.defaultdict(set)
for i in I:
 for f in i['roots']:
  if i['type']=='completeness':
   flagged[f].add(i['record'])
   if not present(records[i['record']].get(f)):missing[f].add(i['record'])
  if i['type'] in ['correctness','content_accuracy']:accuracy[f].add(i['record'])
fieldlist=sorted(missing,key=lambda f:(-len(missing[f]),-sum(not present(records[r].get(f)) for r in rids),f))[:12]
presence=[];prows=[]
for f in fieldlist:
 for rid in rids:
  populated=present(records[rid].get(f));mentioned=rid in flagged[f];presence.append({'record':rid,'project':meta[rid]['project'],'field':f,'populated':populated,'completeness_mentioned':mentioned,'state':'Populated' if populated else ('Absent, mentioned' if mentioned else 'Absent, not mentioned')})
 prows.append({'label':f,'field':f,**{s:sum(x['field']==f and x['state']==s for x in presence) for s in ['Absent, mentioned','Absent, not mentioned','Populated']}})
save('field_presence',presence);save('field_presence_summary',prows)
stacked('03_v8_missingness','v8 structural absence versus completeness comments','12 fields selected using v8 only, ranked by absent-field mentions. 12 records per field.',prows,['Absent, mentioned','Absent, not mentioned','Populated'],['#b75847','#d6b867','#39869b'],12,'Absence does not establish applicability or source availability. An access/landing page is not necessarily a valid download_url.')
# 4 native types by dataset, severity separately in tables.
typecounts=[{'project':p,'type':t,'count':sum(i['project']==p and i['type']==t for i in I)} for t in T for p in P]
severity=[{'project':p,'severity':s,'count':sum(i['project']==p and i['severity']==s for i in I)} for p in P for s in ['low','medium','high']]
save('issue_type_counts',typecounts);save('severity_counts',severity)
heat('04_v8_comment_types','v8 review comment types by dataset','Raw issue entries; 6 primary reviews per dataset (3 records × 2 rubrics).',T,P,[[sum(i['project']==p and i['type']==t for i in I) for p in P] for t in T],maxval=max(x['count'] for x in typecounts),foot='303 primary issue entries. Comments may repeat a concern across rubrics; native categories overlap conceptually.')
# 5 section profile: unique-record prevalence.
sections=sorted({s for i in I for s in i['sections']});sectable=[];sv=[]
for s in sections:
 vv=[]
 for t in T:
  rr=sorted({i['record'] for i in I if s in i['sections'] and i['type']==t});vv.append(len(rr));sectable.append({'section':s,'type':t,'records':rr,'record_count':len(rr),'denominator':12})
 sv.append(vv)
save('section_review_prevalence',sectable)
heat('05_v8_sections','v8 review concerns across datasheet sections','Unique records with at least one comment of each type in a section; denominator 12.',sections,['Completeness','Consistency','Accuracy','Correctness','Semantics'],sv,maxval=12,foot='A comment can implicate several sections. Class-range mapping uses the retained schema crosswalk; counts cannot be summed as errors.')
# 6 accuracy-implicated field roots, independent of native consistency.
afields=sorted(accuracy,key=lambda f:(-len(accuracy[f]),f))[:12];atable=[]
for f in afields:
 for p in P:atable.append({'field':f,'project':p,'records':sorted(r for r in accuracy[f] if meta[r]['project']==p),'count':sum(meta[r]['project']==p for r in accuracy[f]),'denominator':3})
save('accuracy_field_prevalence',atable)
heat('06_v8_accuracy_fields','v8 fields implicated in accuracy / correctness comments','Unique records flagged by either rubric; denominator 3 per dataset. Top 12 roots selected from v8 only.',afields,P,[[sum(meta[r]['project']==p for r in accuracy[f]) for p in P] for f in afields],maxval=3,foot='Co-mentioned fields count as implicated. These are reviewer allegations, including source conflicts and omissions, not adjudicated errors.')
# 7 source-section provenance: semantic document types grouped for readable columns.
source_groups={'publication':'Publications','preprint':'Publications','white paper':'Publications','documentation':'Docs','historical documentation':'Docs','data resource':'Repositories','historical data release':'Repositories','structured metadata':'Structured','RO-Crate':'Structured','license':'Terms','DUA':'Terms','IRB':'IRB','NIH project page':'Awards','tutorial':'Tutorials'}
G=['Publications','Docs','Repositories','Structured','Terms','IRB','Awards','Tutorials'];assert all(l['source_type'] in source_groups for l in L)
ss=sorted({l['section'] for l in L});sourcetable=[];sourcevals=[]
for sec in ss:
 vv=[]
 for g in G:
  rr=sorted({l['record'] for l in L if l['section']==sec and source_groups[l['source_type']]==g});vv.append(len(rr));sourcetable.append({'section':sec,'source_group':g,'records':rr,'record_count':len(rr),'denominator':12})
 sourcevals.append(vv)
save('source_group_mapping',source_groups);save('source_section_coverage',sourcetable)
heat('07_v8_source_sections','v8 source document families and datasheet sections','Unique records with receipt-declared links, of 12. Source types are grouped into eight explicit families for readability.',ss,G,sourcevals,maxval=12,foot='Receipts declare support, not causation or verified entailment. Zero can reflect an unavailable source type rather than an extraction failure.')
# 8 source association: recompute the contrast from v8 links and reviews, not prior means.
targets=['NIH project page','data resource','documentation','publication'];outcomes={'Completeness':['completeness'],'Accuracy/correctness':['correctness','content_accuracy'],'Consistency':['consistency']}
universe={r:{l['root'] for l in L if l['record']==r and l['root_present']} for r in rids};sourcecontrasts=[];cells=[]
for t in targets:
 for name,types in outcomes.items():
  recorddiff={}
  for rid in rids:
   support={l['root'] for l in L if l['record']==rid and l['source_type']==t and l['root_present']};flags={f for i in I if i['record']==rid and i['type'] in types for f in i['roots']};ds=[]
   for sec in sorted({cross.get(f,'Metadata') for f in universe[rid]}):
    a={f for f in support if cross.get(f,'Metadata')==sec};b={f for f in universe[rid]-support if cross.get(f,'Metadata')==sec}
    if a and b:
     diff=100*(len(a&flags)/len(a)-len(b&flags)/len(b));ds.append(diff);cells.append({'record':rid,'project':meta[rid]['project'],'source_type':t,'outcome':name,'section':sec,'linked_fields':len(a),'linked_flagged':len(a&flags),'comparison_fields':len(b),'comparison_flagged':len(b&flags),'difference_pp':diff})
   if ds:recorddiff[rid]=statistics.mean(ds)
  for p in P:
   vals=[v for r,v in recorddiff.items() if meta[r]['project']==p];sourcecontrasts.append({'source_type':t,'outcome':name,'project':p,'eligible_records':len(vals),'mean_difference_pp':statistics.mean(vals) if vals else None})
save('source_association_cells',cells);save('source_associations',sourcecontrasts)
heat('08_v8_source_associations','v8 source associations vary by dataset','Within-record, within-section flagged-field-rate difference (pp): source-linked fields minus other receipt-linked fields.',[t+' / '+name for t in targets for name in outcomes],P,[[next(x['mean_difference_pp'] for x in sourcecontrasts if x['source_type']==t and x['outcome']==name and x['project']==p) for p in P] for t in targets for name in outcomes],maxval=50,dec=1,signed=True,foot='Descriptive associations, not source-caused errors. Equal eligible-section and then record weighting; at most 3 records per dataset.')
# Supporting measurements: agreement, item omission and r10 element profile (tables only).
family=lambda t:'Accuracy/correctness' if t in ['correctness','content_accuracy'] else t
agreements=[]
for rid in rids:
 for typed in [False,True]:
  a={(family(i['type']),f) if typed else f for i in I if i['record']==rid and i['rubric']==10 for f in i['roots']};b={(family(i['type']),f) if typed else f for i in I if i['record']==rid and i['rubric']==20 for f in i['roots']};agreements.append({'record':rid,'project':meta[rid]['project'],'typed':typed,'r10_fields':len(a),'r20_fields':len(b),'shared':len(a&b),'union':len(a|b),'jaccard':len(a&b)/len(a|b) if a or b else None})
sensitivity=[]
for r in R:
 if r['rubric']!=20:continue
 for name,omit in [('Original',set()),('Without Q19',{19}),('Without Q13 and Q19',{13,19})]:
  a=[q for q in Q if q['job']==r['job'] and q['applicable'] and q['id'] not in omit];sensitivity.append({'record':r['record'],'project':r['project'],'view':name,'points':sum(q['score'] for q in a),'max':sum(q['max'] for q in a),'percentage':100*sum(q['score'] for q in a)/sum(q['max'] for q in a)})
element=[]
for group in dict.fromkeys(q['group'] for q in Q if q['rubric']==10):
 for p in P:
  a=[q for q in Q if q['rubric']==10 and q['project']==p and q['group']==group and q['applicable']];element.append({'element':group,'project':p,'points':sum(q['score'] for q in a),'applicable_max':len(a),'percent':100*sum(q['score'] for q in a)/len(a) if a else None})
save('cross_rubric_agreement',agreements);save('score_sensitivity',sensitivity);save('rubric10_elements',element)
summary={'scope':'v8 only, rating1 only, recomputed from retained evaluation records','records':12,'primary_ratings':24,'datasets':4,'replicates_per_dataset':3,'issue_comments':len(I),'issues_by_type':dict(collections.Counter(i['type'] for i in I)),'issues_by_severity':dict(collections.Counter(i['severity'] for i in I)),'q19_qualified_ratings':sum(r['q19_qualified'] for r in R),'receipt_links':len(L),'receipt_links_unpopulated_roots':sum(not l['root_present'] for l in L),'structural_fields_selected':len(fieldlist),'selected_record_field_pairs':len(presence),'selected_absent_pairs':sum(not x['populated'] for x in presence),'selected_absent_mentioned_pairs':sum(not x['populated'] and x['completeness_mentioned'] for x in presence),'all_records_accuracy_flagged':len({i['record'] for i in I if i['type'] in ['correctness','content_accuracy']}),'qualified_jobs':[r['job'] for r in R if r['q19_qualified']]}
save('summary',summary)
validation={'v8_records':len(rids),'primary_ratings':len(R),'input_hash_checks':len(A),'evaluation_file_hash_checks':len(A),'score_and_denominator_arithmetic_checks':len(R),'v7_records_included':0,'repeat_ratings_included':0,'all_item_ids_consistent':len(Q)==12*70,'source_association_recomputed':'from v8 record-level fields, reviews, and receipt links','figures':8}
assert all('_v8_' in x['record'] for x in R+I+Q+L);assert all(sum(row[s] for s in ['Absent, mentioned','Absent, not mentioned','Populated'])==12 for row in prows)
save('validation',validation)
print(json.dumps(summary,indent=2));print(json.dumps(score,indent=2));print(json.dumps(prows,indent=2))
