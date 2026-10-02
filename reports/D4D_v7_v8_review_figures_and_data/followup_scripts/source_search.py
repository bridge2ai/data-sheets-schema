import json,re,hashlib
from pathlib import Path
O=Path('outputs/data/followup')
queries={
'S01':[r'PublicDownloadSelfAttestationRequired'],
'S02':[r'No identifiers were collected',r'Safe Harbor'],
'S03':[r'No identifiers were collected',r'Safe Harbor'],
'S04':[r'WASHINGTON UNIVERSITY IN ST. LOUIS',r'Department of Ophthalmology'],
'S05':[r'impact analysis',r'data protection impact'],
'S06':[r'No identifiers were collected',r'Safe Harbor'],
'S07':[r'WASHINGTON UNIVERSITY IN ST. LOUIS',r'Department of Ophthalmology'],
'S08':[r'Optomed Aurora'],
'S09':[r'2022-09-01',r'2026-11-30'],
'S10':[r'50,000',r'45K',r'7,642',r'1000 images'],
'S11':[r'50,000',r'45K',r'7,642',r'1000 images'],
'S12':[r'MIT License',r'sign a licensing'],
'S13':[r'sign a licensing'],
'S14':[r'controlled access'],
'S15':[r'mgh.havard.edu'],
'S16':[r'holdout test set'],
'S17':[r'quality control'],
'S18':[r'not contain predicted cell maps',r'Cell Mapping Toolkit'],
'S19':[r'dataset.xhtml\?persistentId=doi:10.18130/V3/HIGT4C'],
'S20':[r'untreated, paclitaxel',r'AP-MS data.*treated'],
'S21':[r'Available at.*MassIVE',r'Available at.*Figshare',r'MSV000',r'PXD0'],
'S22':[r'Version 2\.1',r'Version 2\.0'],
'S23':[r'mass spectroscopy'],
'S24':[r'University of Virginia Dataverse, V2',r'Version 2\.0'],
'S25':[r'n_frames',r'data dictionary'],
'S26':[r'semi.annual'],
'S27':[r'RRID:SCR_007345'],
'S28':[r'B2AI_TOPIC:36',r'B2AI_SUBSTRATE:69'],
'S29':[r'distribution.*disease',r'833'],
'S30':[r'10.13026/8xbn-nq66'],
'S31':[r'potential impact.*data subjects',r'impact analysis'],
'S32':[r'pediatric voice',r'participants.*18',r'adult'],
}
for sid,qs in queries.items():
 ev=json.loads((O/f'{sid}_evidence.json').read_text());D=Path('work/followup')/ev['record'];manifest=json.loads((D/'manifest.json').read_text());meta={x['id']:x for x in manifest['chunks']};matches=[]
 for q in qs:
  used=set()
  for f in sorted(D.glob('c*.txt')):
   txt=f.read_text();m=re.search(q,txt,re.I)
   if m and meta[f.stem]['source'] not in used:
    used.add(meta[f.stem]['source']);matches.append({'query':q,'chunk':f.stem,'source':meta[f.stem]['source'],'chunk_sha256':meta[f.stem]['sha256'],'excerpt':txt[max(0,m.start()-180):m.end()+300]})
    if len(used)>=2:break
 ev['source_search_queries']=qs;ev['source_excerpts']=matches;(O/f'{sid}_evidence.json').write_text(json.dumps(ev,indent=2))
 print(sid)
 for x in matches:print(x['chunk'],x['source'],re.sub(r'\s+',' ',x['excerpt']))
