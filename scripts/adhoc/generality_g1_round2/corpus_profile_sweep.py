# Purpose: G1 review (F18) - read every committed provenance record the way the
# readers do (profiles.for_record on the full record; profile_identity via
# provenance.profile_assessment) and dump per-record results, so base and head
# can be compared. Inputs: argv[1] output JSON. Run from a worktree root.
# Reviewer helper, generality G1 review (0ba88ba12), 2026-10-29.
import json, subprocess, sys, warnings, yaml
from data_sheets_schema import profiles
from data_sheets_schema.provenance import profile_assessment
files = subprocess.run(['git', 'ls-files', 'data/d4d_concatenated/**/*_provenance.yaml'],
                       capture_output=True, text=True, check=True).stdout.split()
out = {}
for f in files:
    d = yaml.safe_load(open(f))
    row = {}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        try: row['for_record_full'] = profiles.for_record(d).name
        except Exception as e: row['for_record_full'] = 'ERR ' + type(e).__name__
        try: row['for_record_schema_only'] = profiles.for_record({'schema': d.get('schema')}).name
        except Exception as e: row['for_record_schema_only'] = 'ERR ' + type(e).__name__
        try:
            problems, ctx = profile_assessment(d)
            row.update(problems=problems, status=ctx.get('status'), effective=ctx.get('effective_profile'),
                       basis=ctx.get('profile_basis'), finding=ctx.get('finding'), reason=ctx.get('reason'))
        except Exception as e:
            row['assessment_error'] = f'{type(e).__name__}: {e}'[:300]
        row['warnings'] = sorted({str(x.message)[:120] for x in w})
    out[f] = row
json.dump(out, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(len(out))
