"""Pool v8 records by supplied source types; retain native-type and grouped tables."""
from pathlib import Path
import json,statistics,collections
from plotting import Canvas
O=Path(__file__).resolve().parent;D=O/'data'
load=lambda n:json.loads((D/f'{n}.json').read_text())
save=lambda n,x:(D/f'{n}.json').write_text(json.dumps(x,indent=2))
I=load('issues');Q=load('items');L=load('source_links');S=load('sources');R=load('ratings');groups=load('source_group_mapping');sections=sorted(set(load('section_mapping').values()));rids=sorted({r['record'] for r in R});projects={r['record']:r['project'] for r in R}
G=['Publications','Docs','Repositories','Structured','Terms','IRB','Awards','Tutorials']
# Conservative, single-section assignments by item definition and schema crosswalk.
# This is an analyst-derived profile, not an official section total.
mapping={
'Metadata':['1.1','1.2','1.3','1.4','2.3','3.3','6.1','10.2','10.3'],
'Composition':['2.5','4.2','5.1','5.2','9.1','9.2','9.3','9.4','10.5'],
'Data Governance':['2.1','2.2','3.1'],
'Distribution':['2.4'],
'Variables':['3.4'],
'Uses':['3.5'],
'Ethics':['4.1'],
'Human':['4.3','4.4','4.5'],
'Maintenance':['6.2','6.3','6.4'],
'Motivation':['7.1','7.2','7.3','7.4','7.5'],
'Collection':['8.1','8.2'],
'Preprocessing':['8.3']}
lookup={qid:sec for sec,ids in mapping.items() for qid in ids}
assert len(lookup)==sum(map(len,mapping.values()))
qnames={q['id']:q['name'] for q in Q if q['rubric']==10}
maprows=[{'item':qid,'name':name,'section':lookup.get(qid),'status':'included: narrow single-section item' if qid in lookup else 'excluded: broad, multi-section, or ambiguous scope'} for qid,name in qnames.items()]
save('section_document_score_mapping',maprows)
record_scores=[]
for rid in rids:
 for sec in sections:
  qs=[q for q in Q if q['record']==rid and q['rubric']==10 and lookup.get(q['id'])==sec and q['applicable']]
  mx=sum(q['max'] for q in qs);pts=sum(q['score'] for q in qs)
  record_scores.append({'record':rid,'section':sec,'applicable_items':len(qs),'points':pts,'maximum':mx,'percent':100*pts/mx if mx else None})
save('section_document_record_scores',record_scores)
out=[];mix=[];recordrows=[]
for level,types in [('family',G),('native',sorted({x['source_type'] for x in S}))]:
 for typ in types:
  selected=sorted({x['record'] for x in S if (groups[x['source_type']] if level=='family' else x['source_type'])==typ});assert selected
  mix.append({'level':level,'document_type':typ,'records':len(selected),'datasets':len({projects[r] for r in selected}),'dataset_names':sorted({projects[r] for r in selected})})
  for sec in sections:
   local=[]
   for rid in selected:
    iss=[x for x in I if x['record']==rid and sec in x['sections']]
    linked={x['root'] for x in L if x['record']==rid and x['section']==sec and x['root_present'] and (groups[x['source_type']] if level=='family' else x['source_type'])==typ}
    flags={f for x in I if x['record']==rid for f in x['roots']}
    scoped=[x for x in I if x['record']==rid and linked.intersection(x['roots'])]
    rs=next(x for x in record_scores if x['record']==rid and x['section']==sec)
    row={'level':level,'document_type':typ,'record':rid,'section':sec,'section_comment_count':len({x['issue_id'] for x in iss}),'section_flagged':bool(iss),'section_accuracy_flagged':any(x['type'] in ['content_accuracy','correctness'] for x in iss),'linked_populated_fields':len(linked),'linked_flagged_fields':len(linked&flags),'linked_flagged_percent':100*len(linked&flags)/len(linked) if linked else None,'selected_r10_percent':rs['percent'],'selected_r10_applicable_items':rs['applicable_items'],'linked_comment_count':len({x['issue_id'] for x in scoped})}
    for kind in ['completeness','consistency','content_accuracy','correctness','semantic_understanding']:row[kind+'_comments']=len({x['issue_id'] for x in iss if x['type']==kind})
    local.append(row);recordrows.append(row)
   scores=[x['selected_r10_percent'] for x in local if x['selected_r10_percent'] is not None];linked=[x for x in local if x['linked_flagged_percent'] is not None]
   row={'level':level,'document_type':typ,'section':sec,'available_records':len(local),'available_datasets':len({projects[r] for r in selected}),'mean_comments_per_record':statistics.mean(x['section_comment_count'] for x in local),'section_flagged_records':sum(x['section_flagged'] for x in local),'section_flagged_percent':100*sum(x['section_flagged'] for x in local)/len(local),'section_accuracy_flagged_records':sum(x['section_accuracy_flagged'] for x in local),'score_records':len(scores),'mean_selected_r10_percent':statistics.mean(scores) if scores else None,'mapped_items':len(mapping.get(sec,[])),'linked_records':len(linked),'linked_datasets':len({projects[x['record']] for x in linked}),'linked_record_field_pairs':sum(x['linked_populated_fields'] for x in linked),'linked_flagged_pairs':sum(x['linked_flagged_fields'] for x in linked),'mean_linked_flagged_percent':statistics.mean(x['linked_flagged_percent'] for x in linked) if linked else None}
   for kind in ['completeness','consistency','content_accuracy','correctness','semantic_understanding']:row[kind+'_comments']=sum(x[kind+'_comments'] for x in local)
   out.append(row)
save('section_document_summary',out);save('section_document_record_cells',recordrows);save('section_document_cohorts',mix)
def plot(name,title,subtitle,metric,denom,maxval,foot):
 left=255;cw=147;rh=51;c=Canvas(left+cw*8+35,190+rh*len(sections),title,subtitle)
 for j,g in enumerate(G):c.text(left+j*cw+4,109,g,14,bold=True)
 for i,sec in enumerate(sections):
  y=142+i*rh;c.text(28,y+13,sec,16)
  for j,g in enumerate(G):
   r=next(x for x in out if x['level']=='family' and x['document_type']==g and x['section']==sec);v=r[metric];n=r[denom];t=min(v/maxval,1) if v is not None else 0
   end=(25,119,145);col='#%02x%02x%02x'%tuple(int(245*(1-t)+z*t) for z in end) if v is not None else '#e7eaef';x=left+j*cw;c.rect(x,y,cw-3,rh-3,col)
   label=f'{v:.1f}' if v is not None else 'N/A';color='white' if t>.7 else '#172033';c.text(x+12,y+3,label,18,color=color);c.text(x+12,y+27,f'n={n} records',12,color=color)
 c.text(28,c.h-26,foot,14);c.save(name)
plot('09_v8_pooled_section_comments','Section comments by supplied document family — all v8 records pooled','Mean unique negative-review entries per record in each section. Document availability defines each overlapping column.','mean_comments_per_record','available_records',max(x['mean_comments_per_record'] for x in out if x['level']=='family'),'n is the number of records with that document family. Comments can repeat across rubrics and span multiple sections.')
plot('10_v8_pooled_section_scores','Selected rubric10 item scores by section and supplied document family','Mean record-level percentage of applicable mapped items. Analyst-defined partial section profile; higher values score better.','mean_selected_r10_percent','score_records',100,'n counts records with an applicable mapped item. FileCollection has no narrowly mapped item; N/A does not mean failure.')
plot('11_v8_pooled_linked_flags','Receipt-linked fields flagged in each section, by document family','Mean record-level percent of linked populated roots with any negative comment. Equal weight per eligible record.','mean_linked_flagged_percent','linked_records',100,'n counts records with populated receipt-linked fields in that cell. A flag on a root need not dispute the linked source claim.')
assert len(out)==len(sections)*(len(G)+len({x['source_type'] for x in S}))
assert all(x['record'] in rids for x in recordrows)
assert all(x['linked_flagged_fields']<=x['linked_populated_fields'] for x in recordrows)
print('Mapped items:',len(lookup),'of 50; pooled cells:',len(out),'record cells:',len(recordrows))
