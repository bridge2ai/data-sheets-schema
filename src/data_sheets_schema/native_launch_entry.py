"""Trusted, load-once entry for the reviewed native launch sequence.

Trust: this small entry, Python/interpreter/site startup, the pure wire reader,
and the local OS/filesystem. The reviewed sequence is never imported here:
its one captured byte string is checked, compiled, executed and retained.
This is not protection against arbitrary code already controlling Python.
"""
import argparse
from pathlib import Path
import sys
from . import native_subscription_guard as wire

SEQUENCE_PATH=Path(__file__).resolve().with_name('native_launch_sequence.py')
SEQUENCE_KEY='src/data_sheets_schema/native_launch_sequence.py'


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    parser.add_argument('--registration',required=True)
    parser.add_argument('--review',required=True)
    selected,_=parser.parse_known_args(args)
    registration_raw=wire.read_regular(selected.registration,limit=32*1024*1024)
    review_raw=wire.read_regular(selected.review,limit=32*1024*1024)
    registration=wire.strict_json(registration_raw)
    review=wire.strict_json(review_raw)
    if (review.get('kind')!='d4d_native_execution_review_bundle_v3'
            or type(review.get('version')) is not int or review['version']!=3
            or review.get('registration_sha256')!=wire.sha(registration_raw)):
        raise ValueError('sequence entry requires the current registration-bound review')
    raw=wire.read_regular(SEQUENCE_PATH,limit=32*1024*1024)
    expected=registration['registration']['dependencies']['base']['package_sources'][SEQUENCE_KEY]
    if wire.sha(raw)!=expected or review.get('sequence_script_sha256')!=expected:
        raise ValueError('captured sequence bytes differ from the reviewed registration pin')
    namespace={'__name__':'data_sheets_schema._verified_launch_sequence',
               '__package__':'data_sheets_schema','__file__':str(SEQUENCE_PATH)}
    exec(compile(raw,str(SEQUENCE_PATH),'exec'),namespace)
    return namespace['_run_verified'](args,verified_script=raw,
        entry_inputs={Path(selected.registration):registration_raw,Path(selected.review):review_raw})


if __name__=='__main__':
    raise SystemExit(main())
