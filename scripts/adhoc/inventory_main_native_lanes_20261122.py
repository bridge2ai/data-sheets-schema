"""PR6302 successor: main-only native CI inventory, 2026-11-22.

Inputs: committed workflow/partition source and read-only GitHub run45032209302.
Outputs: fresh source/CI evidence, exact lane roster and original failure files.
No pytest imports, tests, native/provider execution, installs or GitHub mutations.
"""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile


SOURCE = '0ca008a20a1a926b741a08b13ac262386a4d733e'
RUN = 45032209302
REPO = 'bridge2ai/data-sheets-schema'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fresh(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'evidence readback differs')
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)
            .replace(chr(64), '\\u0040') + '\n').encode()


def command(argv, cwd):
    result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('read-only command failed: ' + result.stderr.decode(errors='replace')[:2048])
    return result.stdout


def source_inventory(root):
    workflow = command(['git', 'show', SOURCE + ':.github/workflows/main.yaml'], root)
    partition = command(['git', 'show', SOURCE + ':utils/pytest_shard.py'], root)
    parsed = ast.parse(partition)
    assignments = [node.value for node in parsed.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'NATIVE_PUBLIC_CASE_LANES'
                           for target in node.targets)]
    require(len(assignments) == 1, 'native public lane map is ambiguous')
    lanes = ast.literal_eval(assignments[0])
    job_blocks = re.split(r'(?m)^  ([a-z0-9-]+):\n', workflow.decode())
    jobs = dict(zip(job_blocks[1::2], job_blocks[2::2]))
    excluded = []
    for job_name, block in jobs.items():
        condition = re.search(r'(?m)^    if: (.*)$', block)
        matrix = re.search(r'(?m)^        case: \[([^\]]*)\]$', block)
        if condition and matrix and 'native' in job_name:
            require(condition.group(1) == "github.event_name != 'pull_request'",
                    'unrecognized native event gate')
            names = [name.strip() for name in matrix.group(1).split(',')]
            require(all(name in lanes for name in names), 'main-only lane lacks an exact node mapping')
            excluded.extend(dict(job=job_name, event_gate=condition.group(1), lane=name, node=lanes[name])
                            for name in names)
    require(len(excluded) == len(lanes) and {row['lane'] for row in excluded} == set(lanes),
            'main-only native lane inventory is not closed')
    needs = re.search(r'(?m)^    needs: \[([^\]]*)\]$', jobs['test'])
    require(needs is not None, 'aggregate test dependencies missing')
    aggregate = [name.strip() for name in needs.group(1).split(',')]
    for row in excluded:
        row['aggregate_test_requires_job'] = row['job'] in aggregate
        row['ci_command_argv'] = ['poetry', 'run', 'python', '-m', 'pytest', 'tests', '-v',
            '-p', 'no:cacheprovider', '-p', 'utils.pytest_shard', '--ci-lane=' + row['lane'],
            '--basetemp=RUNNER_TEMP/native-case', '--durations=25', '--junitxml=test-results/pytest.xml']
        row['direct_serial_archive_pytest_args'] = ['-n0', '-vv', '--tb=long', row['node']]
    return excluded, aggregate, workflow, partition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    require(command(['git', 'rev-parse', 'HEAD'], root) == (SOURCE + '\n').encode(),
            'inventory requires selected immutable source HEAD')
    require(not args.output.exists() and args.output.parent.resolve() == args.output.parent,
            'fresh physical output required')
    args.output.mkdir()
    roster, aggregate, workflow, partition = source_inventory(root)
    sources = {}
    for name, raw in (('workflow', workflow), ('partition', partition)):
        sources[name] = dict(bytes=len(raw), sha256=sha(raw), encoding='base64',
                             raw_base64=base64.b64encode(raw).decode())
    fresh(args.output / 'original-source.json', json_bytes(sources))
    run_raw = command(['gh', 'run', 'view', str(RUN), '--repo', REPO, '--json',
        'databaseId,status,conclusion,event,headSha,headBranch,jobs,url'], root)
    run_pin = fresh(args.output / 'run-snapshot.json', run_raw)
    run = json.loads(run_raw)
    require(run['databaseId'] == RUN and run['headSha'] == SOURCE and run['event'] == 'push',
            'run source/event identity differs')
    artifacts_raw = command(['gh', 'api', 'repos/' + REPO + '/actions/runs/' + str(RUN)
                             + '/artifacts?per_page=100'], root)
    artifacts_pin = fresh(args.output / 'artifacts-snapshot.json', artifacts_raw)
    artifacts = json.loads(artifacts_raw)
    require(len(artifacts['artifacts']) == artifacts['total_count'], 'artifact snapshot pagination incomplete')
    for row in roster:
        expected_name = 'Python 3.12 / native case ' + row['lane']
        matches = [job for job in run['jobs'] if job['name'] == expected_name]
        require(len(matches) == 1, 'native lane job is not unique in run snapshot')
        job = matches[0]
        row['ci_job'] = job
        selected_artifacts = [value for value in artifacts['artifacts']
                              if value['name'] == 'tests-py3.12-native-' + row['lane']]
        require(len(selected_artifacts) <= 1, 'duplicate native lane artifact')
        row['artifact_available_at_snapshot'] = bool(selected_artifacts)
        if job['status'] != 'completed' or job['conclusion'] != 'failure':
            continue
        log_raw = command(['gh', 'api', '--allow-escape-sequences',
                           'repos/' + REPO + '/actions/jobs/' + str(job['databaseId']) + '/logs'], root)
        row['job_log'] = fresh(args.output / (row['lane'] + '-job.log'), log_raw)
        if not selected_artifacts:
            continue
        artifact = selected_artifacts[0]
        require(artifact['workflow_run']['id'] == RUN and artifact['workflow_run']['head_sha'] == SOURCE
                and not artifact['expired'], 'native artifact source binding differs')
        zipped = command(['gh', 'api', '--allow-escape-sequences',
                          'repos/' + REPO + '/actions/artifacts/' + str(artifact['id']) + '/zip'], root)
        row['artifact'] = artifact
        row['artifact_zip'] = fresh(args.output / (row['lane'] + '.zip'), zipped)
        destination = args.output / row['lane']
        destination.mkdir()
        with zipfile.ZipFile(io.BytesIO(zipped)) as bundle:
            names = [item.filename for item in bundle.infolist() if not item.is_dir()]
            require(len(names) == len(set(names)), 'artifact member names repeat')
            row['artifact_members'] = []
            for name in names:
                selected = PurePosixPath(name)
                require(not selected.is_absolute() and '..' not in selected.parts, 'artifact member escapes output')
                path = destination / name
                path.parent.mkdir(parents=True, exist_ok=True)
                row['artifact_members'].append(fresh(path, bundle.read(name)))
        xml = destination / 'pytest.xml'
        require(xml.is_file(), 'failed native artifact lacks original XML')
        cases = list(ET.fromstring(xml.read_bytes()).iter('testcase'))
        expected_file, expected_test = row['node'].split('::')
        require(len(cases) == 1 and cases[0].get('classname') == expected_file[:-3].replace('/', '.')
                and cases[0].get('name') == expected_test, 'dedicated artifact testcase identity differs')
        row['xml_cases'] = [dict(attributes=dict(case.attrib), outcomes=[
            dict(kind=child.tag, attributes=dict(child.attrib), text=child.text or '')
            for child in case if child.tag in ('failure', 'error', 'skipped')]) for case in cases]
    result = dict(kind='main_only_native_lane_inventory', version=1, source_commit=SOURCE,
        source=sources, run=run_pin, artifacts=artifacts_pin, lanes=roster,
        aggregate_test_needs=aggregate, run_status_at_snapshot=run['status'],
        run_conclusion_at_snapshot=run['conclusion'], helper=dict(path=str(Path(__file__)),
            sha256=sha(Path(__file__).read_bytes())),
        limits='Read-only source and GitHub snapshot. No local test, native binary or provider execution. '
               'Direct node archive arguments select the same test but do not claim the dedicated CI plugin gate.')
    receipt = fresh(args.output / 'inventory.json', json_bytes(result))
    print(json.dumps(dict(inventory=receipt, lanes=[dict(lane=row['lane'], node=row['node'],
        status=row['ci_job']['status'], conclusion=row['ci_job']['conclusion'],
        job_id=row['ci_job']['databaseId'], failures=[dict(kind=outcome['kind'],
            message=outcome['attributes'].get('message', '')) for case in row.get('xml_cases', [])
            for outcome in case['outcomes']]) for row in roster]),
        sort_keys=True).replace(chr(64), '\\u0040'))


if __name__ == '__main__':
    main()
