"""Normalize section scores and comments; keep denominators and unmatched loss explicit."""
from pathlib import Path
import json,statistics,hashlib,re
import yaml
from plotting import Canvas,heat
O=Path(__file__).resolve().parent;D=O/'data';load=lambda n:json.loads((D/f'{n}.json').read_text());save=lambda n,x:(D/f'{n}.json').write_text(json.dumps(x,indent=2))
R=load('ratings');Q=load('items');I=load('issues');L=load('source_links');S=load('sources');cross=load('section_mapping');groups=load('source_group_mapping');mapping={x['item']:x['section'] for x in load('section_document_score_mapping') if x['section']};rids=sorted({r['record'] for r in R});projects={r['record']:r['project'] for r in R};P=sorted(set(projects.values()));secs=sorted(set(cross.values()));docs={}
ROOT=Path(__file__).resolve().parents[2]
for a in load('input_audit'):
 rid=re.match(r'(.+_v8_rep\d+)',Path(a['file']).name)[1]
 if rid not in docs:
  p=Path(a['d4d_file']);p=p if p.exists() else (ROOT/str(a['d4d_file'])[str(a['d4d_file']).index('data/'):] if 'data/' in str(a['d4d_file']) else p)
  b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==a['input_sha256'];docs[rid]=yaml.safe_load(b)
present=lambda v:v is not None and v!='' and v!=[] and v!={}
unknown=sorted({f for i in I for f in i['roots'] if f not in cross})
fields=[];score=[]
for rid in rids:
 for sec in secs:
  candidate={f for f,s in cross.items() if s==sec};pop={f for f in candidate if present(docs[rid].get(f))};linked={l['root'] for l in L if l['record']==rid and l['root_present'] and l['root'] in pop}
  for definition,univ in [('Mapped candidates',candidate),('Populated roots',pop),('Receipt-linked populated roots',linked)]:
   for outcome,types in [('Any comment',None),('Completeness',['completeness']),('Accuracy/correctness',['content_accuracy','correctness'])]:
    flagged={f for i in I if i['record']==rid and (types is None or i['type'] in types) for f in i['roots']};numer=len(univ&flagged)
    fields.append({'record':rid,'project':projects[rid],'section':sec,'denominator_definition':definition,'outcome':outcome,'eligible_fields':len(univ),'flagged_fields':numer,'percent':100*numer/len(univ) if univ else None,'absent_flagged_candidate_fields':len((candidate-pop)&flagged)})
 for sec in secs+['Unmapped items']:
  qs=[q for q in Q if q['record']==rid and q['rubric']==10 and q['applicable'] and mapping.get(q['id'],'Unmapped items')==sec];mx=sum(q['max'] for q in qs);loss=sum(q['max']-q['score'] for q in qs)
  score.append({'record':rid,'project':projects[rid],'section':sec,'applicable_points':mx,'lost_points':loss,'loss_percent':100*loss/mx if mx else None})
total_loss=sum(x['lost_points'] for x in score);total_max=sum(x['applicable_points'] for x in score)
summary=[];paired=[];bydata=[];loo=[]
for sec in secs+['Unmapped items']:
 rows=[x for x in score if x['section']==sec];mx=sum(x['applicable_points'] for x in rows);loss=sum(x['lost_points'] for x in rows);vals=[x['loss_percent'] for x in rows if x['loss_percent'] is not None]
 summary.append({'section':sec,'mapped_item_count':sum(s==sec for s in mapping.values()) if sec!='Unmapped items' else 50-len(mapping),'scored_records':len(vals),'applicable_points':mx,'lost_points':loss,'pooled_loss_percent':100*loss/mx if mx else None,'mean_record_loss_percent':statistics.mean(vals) if vals else None,'share_all_r10_lost_points_percent':100*loss/total_loss,'share_all_r10_available_points_percent':100*mx/total_max})
 for p in P:
  rr=[r for r in rows if r['project']==p];mm=sum(x['applicable_points'] for x in rr);ll=sum(x['lost_points'] for x in rr);bydata.append({'section':sec,'project':p,'applicable_points':mm,'lost_points':ll,'loss_percent':100*ll/mm if mm else None})
  other=[r for r in rows if r['project']!=p];mm=sum(x['applicable_points'] for x in other);ll=sum(x['lost_points'] for x in other);loo.append({'section':sec,'omitted_dataset':p,'applicable_points':mm,'loss_percent':100*ll/mm if mm else None})
 if sec=='Unmapped items':continue
 for row in rows:
  other=[x for x in score if x['record']==row['record'] and x['section'] not in (sec,'Unmapped items')];mm=sum(x['applicable_points'] for x in other);ll=sum(x['lost_points'] for x in other)
  paired.append({'record':row['record'],'project':row['project'],'section':sec,'section_loss_percent':row['loss_percent'],'other_mapped_loss_percent':100*ll/mm if mm else None,'difference_pp':row['loss_percent']-100*ll/mm if row['loss_percent'] is not None and mm else None})
field_summary=[]
for sec in secs:
 for definition in ['Mapped candidates','Populated roots','Receipt-linked populated roots']:
  for outcome in ['Any comment','Completeness','Accuracy/correctness']:
   rr=[x for x in fields if x['section']==sec and x['denominator_definition']==definition and x['outcome']==outcome];vals=[x['percent'] for x in rr if x['percent'] is not None];nn=sum(x['eligible_fields'] for x in rr);ff=sum(x['flagged_fields'] for x in rr)
   field_summary.append({'section':sec,'denominator_definition':definition,'outcome':outcome,'eligible_records':len(vals),'eligible_record_field_pairs':nn,'flagged_record_field_pairs':ff,'pooled_percent':100*ff/nn if nn else None,'mean_record_percent':statistics.mean(vals) if vals else None,'absent_flagged_candidate_pairs':sum(x['absent_flagged_candidate_fields'] for x in rr)})
# Source groups condition on input availability; still overlapping cohorts.
source_summary=[]
for level,types in [('family',sorted(set(groups.values()))),('native',sorted({s['source_type'] for s in S}))]:
 for typ in types:
  ids={s['record'] for s in S if (groups[s['source_type']] if level=='family' else s['source_type'])==typ}
  for x in field_summary:
   rr=[r for r in fields if r['record'] in ids and all(r[k]==x[k] for k in ['section','denominator_definition','outcome'])];nn=sum(r['eligible_fields'] for r in rr);ff=sum(r['flagged_fields'] for r in rr)
   source_summary.append({'level':level,'document_type':typ,**{k:x[k] for k in ['section','denominator_definition','outcome']},'available_records':len(ids),'eligible_records':sum(r['percent'] is not None for r in rr),'eligible_record_field_pairs':nn,'flagged_record_field_pairs':ff,'pooled_percent':100*ff/nn if nn else None})
for n,x in [('size_field_records',fields),('size_field_summary',field_summary),('size_score_records',score),('size_score_summary',summary),('size_score_by_dataset',bydata),('size_score_leave_one_dataset_out',loo),('size_score_paired_contrasts',paired),('size_source_field_summary',source_summary)]:save(n,x)
save('size_normalization_audit',{'records':len(rids),'rubric10_total_applicable_points':total_max,'rubric10_total_lost_points':total_loss,'mapped_items':len(mapping),'unmapped_items':50-len(mapping),'candidate_roots':len(cross),'review_roots_outside_crosswalk':unknown,'field_applicability':'Not established; field denominators are sensitivity definitions, not true applicable-field counts.','field_weighting':'Pooled record-field pairs; mean record rates also exported.','score_weighting':'Pooled applicable points; mean record rates also exported.'})
# Figure 12: normalized rate versus contribution, with denominator labels.
order=sorted(summary,key=lambda x:(x['pooled_loss_percent'] is None,-(x['pooled_loss_percent'] or 0)))
c=Canvas(1440,190+41*len(order),'Section score loss: rate versus contribution','Rubric10 only. Left: lost / applicable points. Right: share of ALL recorded rubric10 lost points, including unmapped items.')
for x,t in [(330,'Loss rate (%)'),(865,'Share of all lost points (%)')]:
 c.text(x,105,t,17,bold=True)
 for tick in [0,25,50,75,100]:c.text(x+tick*3.65,130,str(tick),12)
for i,r in enumerate(order):
 y=156+i*41;c.text(28,y+4,r['section'],16);v=r['pooled_loss_percent'];c.rect(330,y,365,23,'#eef2f5');c.rect(865,y,365,23,'#eef2f5')
 if v is not None:c.rect(330,y,3.65*v,23,'#187c95')
 c.text(705,y+2,f'{v:.1f}%' if v is not None else 'N/A',15);c.text(770,y+2,f"{r['lost_points']}/{r['applicable_points']}",13)
 share=r['share_all_r10_lost_points_percent'];c.rect(865,y,share*3.65,23,'#9762a4');c.text(1242,y+2,f'{share:.1f}%',15)
c.text(28,c.h-24,'39 mapped subelements; 11 unmapped. A one-item section can have a high loss rate but contribute few lost points.',14);c.save('12_v8_section_loss_normalized')
heat('13_v8_section_flag_denominators','Section flag proportions depend on the field denominator','Percent of eligible record–root pairs named in any negative comment; both rubrics. Each pair counted at most once.',secs,['Candidates','Populated','Receipt-linked'],[[next(x['pooled_percent'] for x in field_summary if x['section']==sec and x['denominator_definition']==de and x['outcome']=='Any comment') for de in ['Mapped candidates','Populated roots','Receipt-linked populated roots']] for sec in secs],dec=1,foot='Candidates include optional fields; populated/linked denominators exclude omissions. Root counts do not adjust nested section length.')
heat('14_v8_section_loss_consistency','Normalized section score loss across the four datasets','Lost rubric10 points / applicable mapped points (%), pooling three generations within each dataset.',secs,P,[[next(x['loss_percent'] for x in bydata if x['section']==sec and x['project']==p) for p in P] for sec in secs],dec=1,foot='Higher is more score loss. N/A = no applicable mapped points. These are four dataset contexts, not 12 independent datasets.')
print(json.dumps(summary,indent=2));print('Unknown review roots:',unknown)
robust=[]
for sec in secs:
 ds=[x for x in bydata if x['section']==sec and x['loss_percent'] is not None];ls=[x['loss_percent'] for x in loo if x['section']==sec and x['loss_percent'] is not None];rr=[x for x in paired if x['section']==sec and x['difference_pp'] is not None];dm=[statistics.mean(x['difference_pp'] for x in rr if x['project']==p) for p in P if any(x['project']==p for x in rr)]
 robust.append({'section':sec,'datasets_with_applicable_points':len(ds),'datasets_with_any_loss':sum(x['lost_points']>0 for x in ds),'min_leave_one_dataset_out_loss_percent':min(ls) if ls else None,'max_leave_one_dataset_out_loss_percent':max(ls) if ls else None,'paired_records':len(rr),'records_above_own_other_section_loss':sum(x['difference_pp']>1e-9 for x in rr),'records_equal_to_own_other_section_loss':sum(abs(x['difference_pp'])<=1e-9 for x in rr),'mean_within_record_difference_pp':statistics.mean(x['difference_pp'] for x in rr) if rr else None,'datasets_with_positive_mean_paired_difference':sum(x>1e-9 for x in dm)})
save('size_score_robustness',robust)
