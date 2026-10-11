import json,collections,itertools,math,html,base64
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;load=lambda n:json.loads((O/'data'/f'{n}.json').read_text());R=[x for x in load('ratings') if x['rating']==1];I=[x for x in load('issues') if x['rating']==1];L=load('source_links');Q=load('items');P=['AI_READI','CHORUS','CM4AI','VOICE'];rng=np.random.default_rng(29092026)
records=sorted(set(r['record'] for r in R));meta={r['record']:r for r in R};groups={'Completeness flags':['completeness'],'Accuracy/correctness flags':['correctness','content_accuracy'],'Consistency flags':['consistency']}
y={name:{rid:sum(i['record']==rid and i['type'] in types for i in I) for rid in records} for name,types in groups.items()}
for r in [10,20]:y[f'Rubric{r} adjusted score']={x['record']:x['adjusted_pct'] for x in R if x['rubric']==r}
y['Q1 completeness score']={x['record']:100*x['score']/x['max'] for x in Q if x['rubric']==20 and x['id']==1}
def bh(rows):
 order=sorted(range(len(rows)),key=lambda j:rows[j]['p']);v=1
 for rank,j in reversed(list(enumerate(order,1))):v=min(v,rows[j]['p']*len(rows)/rank);rows[j]['q_BH']=v
# Exact stratified permutation, equal weight to the 4 datasets.
C=np.array(list(itertools.combinations(range(6),3)));weights=np.full((20,6),-1/3)
for n,c in enumerate(C):weights[n,c]=1/3
version=[]
for name,yy in y.items():
 distributions=[];effects={}
 for p in P:
  ids=sorted(r for r in records if meta[r]['project']==p);vals=np.array([yy[r] for r in ids]);effects[p]=float(vals[3:].mean()-vals[:3].mean());distributions.append(weights@vals)
 null=distributions[0]
 for d in distributions[1:]:null=(null[:,None]+d[None,:]).ravel()
 null/=4;obs=np.mean(list(effects.values()));pv=float(np.mean(np.abs(null)>=abs(obs)-1e-10))
 version.append({'outcome':name,'v8_minus_v7':float(obs),'dataset_effects':effects,'p':pv,'permutations':len(null)})
bh(version)
# Within dataset x version associations: block-centered Pearson, permutation of y within 3 generation replicates.
blocks=[sorted(r for r in records if meta[r]['project']==p and meta[r]['version']==v) for p in P for v in ['v7','v8']];ordered=sum(blocks,[]);N=49999
perms=np.array(list(itertools.permutations(range(3))));draw=rng.integers(0,6,size=(N,8));assoc=[]
for yn in ['Accuracy/correctness flags','Consistency flags','Rubric10 adjusted score']:
 x=np.array([y['Q1 completeness score'][r] for r in ordered],float).reshape(8,3);a=np.array([y[yn][r] for r in ordered],float).reshape(8,3);x-=x.mean(axis=1,keepdims=True);a-=a.mean(axis=1,keepdims=True);den=np.sqrt((x*x).sum()*(a*a).sum());obs=float((x*a).sum()/den) if den else None
 if den:
  null=np.zeros(N)
  for b in range(8):null+=(a[b][perms[draw[:,b]]]*x[b]).sum(axis=1)
  null/=den;pv=float((1+np.sum(abs(null)>=abs(obs)-1e-10))/(N+1))
 else:pv=1
 assoc.append({'x':'Q1 completeness score','y':yn,'within_block_r':obs,'p':pv,'permutations':N,'blocks':8,'records':24,'blocks_with_x_variation':int(sum(np.any(z!=0) for z in x))})
bh(assoc)
# Source associations use within-record contrasts, aggregate to one contrast per underlying dataset.
universe={r:{x['root'] for x in L if x['record']==r and x['root_present']} for r in records};source=[]; section_rows=[]
for t in sorted({x['source_type'] for x in L}):
 support={r:{x['root'] for x in L if x['record']==r and x['source_type']==t and x['root_present']} for r in records}
 for name,types in groups.items():
  flagged={r:{f for i in I if i['record']==r and i['type'] in types for f in i['roots']} for r in records};diffs={}
  for r in records:
   aa=support[r];bb=universe[r]-aa
   if aa and bb:diffs[r]=100*(len(aa&flagged[r])/len(aa)-len(bb&flagged[r])/len(bb))
  ds={p:float(np.mean([v for r,v in diffs.items() if meta[r]['project']==p])) for p in P if any(meta[r]['project']==p for r in diffs)}
  unadjusted=ds.copy(); cross=load('section_mapping'); section_diffs={}
  for r in records:
   a=[]
   for sec in {cross.get(f,'Metadata') for f in universe[r]}:
    aa={f for f in support[r] if cross.get(f,'Metadata')==sec}; bb={f for f in universe[r]-support[r] if cross.get(f,'Metadata')==sec}
    if aa and bb:
     diff=100*(len(aa&flagged[r])/len(aa)-len(bb&flagged[r])/len(bb));a.append(diff)
     section_rows.append({'source_type':t,'outcome':name,'record':r,'project':meta[r]['project'],'section':sec,'linked_fields':len(aa),'linked_flagged':len(aa&flagged[r]),'comparison_fields':len(bb),'comparison_flagged':len(bb&flagged[r]),'difference_pp':diff})
   if a:section_diffs[r]=float(np.mean(a))
  ds={p:float(np.mean([v for r,v in section_diffs.items() if meta[r]['project']==p])) for p in P if any(meta[r]['project']==p for r in section_diffs)}
  n=sum(abs(v)>1e-12 for v in ds.values());pos=sum(v>1e-12 for v in ds.values());neg=n-pos
  pv=min(1,2*sum(math.comb(n,k) for k in range(min(pos,neg)+1))/2**n) if n else 1
  source.append({'source_type':t,'outcome':name,'mean_difference_pp':float(np.mean(list(ds.values()))) if ds else None,'dataset_effects':ds,'unadjusted_dataset_effects':unadjusted,'section_matched_records':len(section_diffs),'datasets':len(ds),'nonzero_datasets':n,'records_with_contrast':len(diffs),'p':pv if len(ds)>=3 else None,'test':'exact two-sided sign test across dataset contrasts' if len(ds)>=3 else 'not tested: fewer than 3 datasets'})
tested=[s for s in source if s['p'] is not None];bh(tested)
result={'version_tests':version,'conditional_associations':assoc,'source_contrasts':source,'seed':29092026,'multiplicity':'BH separately within version (6), conditional association (3), and eligible source contrast (12) families','assumptions':'Observational/exploratory. Permutations require exchangeable generation replicates within dataset or dataset-version blocks. Source sign tests require independent, sign-symmetric dataset contrasts under the null; 4 purposively chosen datasets limit generalization. No source causation or verified accuracy inference.'}
(O/'data/source_section_contrasts.json').write_text(json.dumps(section_rows,indent=2))
assert len(tested)==12 and len(version)==6 and len(assoc)==3
assert all(0<=x['p']<=x['q_BH']<=1 for x in version+assoc+tested)
(O/'data/exploratory_statistics.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
# Compact dot plots with project-level effects and the equal-project average.
font='/System/Library/Fonts/Supplemental/Arial.ttf';bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def panel(name,title,sub,rows,foot):
 w=1300;h=170+len(rows)*43+65;im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/>']
 def text(x,y,t,size=16,col='#172033',b=False):
  d.text((x,y),t,font=ImageFont.truetype(bold if b else font,size),fill=col);svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" fill="{col}">{html.escape(t)}</text>')
 def line(x,y,x2,y2,col='#e2e8f0'):
  d.line((x,y,x2,y2),fill=col);svg.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{col}"/>')
 def circ(x,y,r,col):
  d.ellipse((x-r,y-r,x+r,y+r),fill=col);svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
 text(30,20,title,26,b=True);text(30,62,sub,15);colors=dict(zip(P,['#137c8b','#e89535','#8464b7','#d25368']));bound=max(5,math.ceil(max(abs(v) for row in rows for v in row[1].values())/5)*5);left=440;ww=570
 for tick in [-bound,-bound/2,0,bound/2,bound]:
  x=left+ww*(tick+bound)/(2*bound);line(x,120,x,135+len(rows)*43,'#8496a7' if tick==0 else '#e2e8f0');text(x-15,98,f'{tick:g}',14)
 text(1050,98,'Mean / BH q',14,b=True)
 for i,(label,ds,mean,q) in enumerate(rows):
  yy=145+i*43;text(30,yy-10,label,15)
  for j,(p,v) in enumerate(ds.items()):circ(left+ww*(v+bound)/(2*bound),yy+(j-1.5)*3,5,colors[p])
  x=left+ww*(mean+bound)/(2*bound);line(x,yy-12,x,yy+12,'#172033');text(1040,yy-10,f'{mean:+.2f} / {q:.3f}' if q is not None else f'{mean:+.2f} / not tested',15)
 for j,p in enumerate(P):circ(80+j*200,h-70,5,colors[p]);text(92+j*200,h-80,p,14)
 text(30,h-35,foot,13);im.save(O/'figures'/f'{name}.png');(O/'figures'/f'{name}.svg').write_text(''.join(svg)+'</svg>')
panel('13_version_statistics','Exploratory version differences: v8 minus v7','Colored dots: dataset-specific differences; black tick: equal-dataset mean. Scores use percentage points; flags use counts.',[(r['outcome'],r['dataset_effects'],r['v8_minus_v7'],r['q_BH']) for r in version],'Exact stratified permutation (160,000 allocations); BH across 6 outcomes. Exchangeability assumed; execution confounding remains.')
panel('14_source_associations','Source-type associations with review flags','Flagged-field rate difference (percentage points), comparing fields within the same record and datasheet section.',[(r['source_type']+' / '+r['outcome'].replace(' flags',''),r['dataset_effects'],r['mean_difference_pp'],r.get('q_BH')) for r in tested],'Equal section, record, then dataset weighting; eligible sections need linked and unlinked fields. BH across 12 exploratory sign tests.')
