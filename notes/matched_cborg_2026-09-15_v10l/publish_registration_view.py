"""Publish review metadata without exporting machine-specific launch paths."""
import hashlib
import json
import os
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    registration=HERE/'registration.json';overlay=HERE/'native_overlay.json'
    r=json.loads(registration.read_bytes());o=json.loads(overlay.read_bytes())
    prior=os.path.commonpath([row['path'] for row in r['prior_attempt_artifacts']])
    bindings=[(r['repository'],'<repository>'),(prior,'<prior-condition-repository>'),
              (r['python'],'<registered-python>'),(o['claude_executable'],'<registered-claude>'),
              (o['observed_cli_alias'],'<observed-cli-alias>')]
    def scrub(value):
        if isinstance(value,str):
            for original,symbol in sorted(bindings,key=lambda pair:len(pair[0]),reverse=True):
                value=value.replace(original,symbol)
            return value
        if isinstance(value,list):return [scrub(v) for v in value]
        if isinstance(value,dict):return {scrub(k):scrub(v) for k,v in value.items()}
        return value
    for source,value,name in [(registration,r,'registration.public.json'),(overlay,o,'native_overlay.public.json')]:
        public={'kind':'public_review_view_not_executable','original_sha256':sha(source),
                'transform':'Only machine-specific path bindings are replaced by named placeholders. Original launch files remain local and unchanged.',
                'view':scrub(value)}
        text=json.dumps(public,indent=2)+'\n'
        if '/Users/' in text or '/private/tmp/' in text or '/private/var/' in text:
            raise RuntimeError('public view still contains an unbound machine path')
        path=HERE/name
        if path.exists():raise FileExistsError(path)
        path.write_text(text)
    inventory=[]
    for job in r['generation']['jobs']:
        for key in ['instruction','initial_request']:
            if key not in job:continue
            path=Path(job[key]);raw=path.read_bytes()
            inventory.append({'job':job['id'],'kind':key,'local_original_sha256':sha(path),
                'normalized_review_sha256':hashlib.sha256(scrub(raw.decode()).encode()).hexdigest(),
                'bytes':len(raw)})
    with (HERE/'launch_input_inventory.json').open('x') as out:
        json.dump({'purpose':'Exact local originals are not published; public source files and renderer permit reconstruction. Normalization only substitutes machine paths.',
                   'inputs':inventory},out,indent=2);out.write('\n')
    print(json.dumps({'public_views':2,'launch_inputs':len(inventory),'registration_sha256':sha(registration)}))


if __name__=='__main__':main()
