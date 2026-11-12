#!/usr/bin/env python3
"""Registration author-time procedure and synthetic-only scratch proof.

Read valid_from from supplied registration runtime; never choose a date.
The create operation is restricted to the synthetic profile and a NEW scratch
repository. Production use requires a separately reviewed lead operation.
Verification delegates the exact-byte/addition/time check to production source.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def git(repository, *arguments, author_date=None):
    env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','GIT_CONFIG_GLOBAL':'/dev/null',
         'GIT_CONFIG_SYSTEM':'/dev/null','GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0',
         'GIT_AUTHOR_NAME':'SYNTHETIC registration timestamp proof',
         'GIT_AUTHOR_EMAIL':'synthetic'+chr(64)+'invalid',
         'GIT_COMMITTER_NAME':'SYNTHETIC registration timestamp proof',
         'GIT_COMMITTER_EMAIL':'synthetic'+chr(64)+'invalid'}
    if author_date is not None: env['GIT_AUTHOR_DATE']=author_date
    return subprocess.check_output(['/usr/bin/git','--no-replace-objects','-c','protocol.allow=never',
        '-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-c','core.fsmonitor=false',
        '-C',str(repository),*arguments],env=env,stderr=subprocess.PIPE,timeout=30).decode().strip()


def verify(registration_raw, evidence):
    from data_sheets_schema.native_launch_review import registration_fields, _registration_commit
    value=registration_fields(registration_raw)
    _registration_commit(evidence,registration_raw,value['runtime'])
    from data_sheets_schema.native_u4b_policy import registered_policy
    policy=registered_policy(value['runtime'])
    return {'scope':'Commit bytes/addition/author-time equality only; not launch authorization.',
            'valid_from':policy['valid_from'],'commit':evidence['commit'],'checked':True}


def archive_synthetic(registration_raw, repository):
    from data_sheets_schema.native_launch_review import registration_fields
    from data_sheets_schema.native_runtime_profiles import require_synthetic
    from data_sheets_schema.native_u4b_policy import registered_policy, timestamp
    value=registration_fields(registration_raw); require_synthetic(value['runtime'])
    start=registered_policy(value['runtime'])['valid_from']
    if timestamp(start,'valid_from') != int(timestamp(start,'valid_from')):
        raise ValueError('Git author time has whole-second resolution; supplied valid_from is fractional')
    repository=Path(repository)
    if not repository.is_absolute() or repository.resolve()!=repository:
        raise ValueError('scratch repository requires an absolute physical new path')
    repository.mkdir(exist_ok=False)
    git(repository,'init','-b','synthetic-registration-evidence')
    path=repository/'registration.json'
    with path.open('xb') as stream: stream.write(registration_raw)
    git(repository,'add','--','registration.json')
    git(repository,'commit','--date',start,'-m','SYNTHETIC exact registration author-time proof',author_date=start)
    evidence={'repository':str(repository),'path':'registration.json','commit':git(repository,'rev-parse','HEAD')}
    result=verify(registration_raw,evidence)
    with (repository/'timestamp-proof.json').open('x') as stream:
        json.dump({'scope':'SYNTHETIC; NO PRODUCTION COMMIT', 'evidence':evidence,'verification':result},stream,indent=2)
        stream.write('\n')
    return evidence


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    p.add_argument('--registration',type=Path,required=True)
    p.add_argument('--scratch-repository',type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(archive_synthetic(a.registration.read_bytes(),a.scratch_repository)))

if __name__=='__main__':
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    main()
