"""Complete-directory preparation and actual workflow shell wiring (#4450).

The three PDFs are synthetic PDF1.4 documents, never captured research data.
encrypted.pdf is Standard Security R2 with an empty user password: accepting
that password must still not admit an encrypted document. These tests run the
real locked pdfminer converter. Only billed/remote workflow commands are faked.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/github/assistant_bundle.py"
WORKFLOW = ROOT / ".github/workflows/d4d-agent.yml"
FIXTURES = ROOT / "tests/fixtures/assistant_bundle"
SPEC = importlib.util.spec_from_file_location("assistant_bundle", SCRIPT)
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)
HEAD = "a" * 40


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "inputs/Unit"
    directory.mkdir(parents=True)
    output = tmp_path / "prepared"
    output.mkdir()
    return directory, output


def prepare(workspace):
    directory, output = workspace
    return bundle.prepare(directory.parent, directory.name, output, HEAD)


def mixed(directory):
    docs = {
        "a.txt": b"\xef\xbb\xbfFirst\r\nsecond\rlast\n# End source\n",
        "b.md": "# Unicode: café Ω\n".encode(),
        "nested/a.txt": b"Distinct duplicate basename\n",
        "c.json": b'{ "x": 1, "x": 2 }\r\n',
        "d.HTML": b'<script>literal()</script>&amp;<a href="https://invalid">x</a>',
        ".hidden.txt": b"Hidden source\n",
        "space and\nnewline.txt": b"Filename is data\n",
        "empty.txt": b"",
        "e.pdf": (FIXTURES / "text.pdf").read_bytes(),
    }
    for name, raw in docs.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return docs


def test_actual_mixed_formats_preserve_every_byte_and_provenance(workspace):
    directory, output = workspace
    docs = mixed(directory)
    raw, manifest = prepare(workspace)
    assert [row["path"] for row in manifest["members"]] == sorted(docs)
    assert manifest["source_commit"] == HEAD
    assert manifest["input_directory"] == "inputs/Unit"
    assert manifest["bundle"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["bundle"]["bytes"] == len(raw)
    for row in manifest["members"]:
        original = docs[row["path"]]
        content = raw[row["content_start"]:row["content_end"]]
        assert row["raw_bytes"] == len(original)
        assert row["raw_sha256"] == hashlib.sha256(original).hexdigest()
        assert row["content_bytes"] == len(content)
        assert row["content_sha256"] == hashlib.sha256(content).hexdigest()
        assert (directory / row["path"]).read_bytes() == original
        if row["path"].endswith(".pdf"):
            assert content == b"Synthetic PDF source marker\n\n\x0c"
            assert row["conversion"]["version"] == "20221105"
        else:
            assert content == original
    another = output.with_name("other-output")
    another.mkdir()
    assert bundle.prepare(directory.parent, "Unit", another, HEAD) == (raw, manifest)
    assert str(output).encode() not in raw


def test_six_member_cm4ai_shape_and_hardlinked_occurrences(workspace):
    directory, _ = workspace
    for i in range(5):
        (directory / f"source{i}.txt").write_text(f"source {i}")
    (directory / "doi.json").write_bytes(b'{"doi":"synthetic"}')
    raw, manifest = prepare(workspace)
    assert len(manifest["members"]) == 6
    for i in range(5):
        assert f"source {i}".encode() in raw
    os.link(directory / "source0.txt", directory / "alias.txt")
    _, again = prepare(workspace)
    assert len(again["members"]) == 7
    assert again["members"][0]["path"] == "alias.txt"


@pytest.mark.parametrize("name,raw,reason", [
    ("bad.txt", b"\xff", "UnicodeDecodeError"),
    ("unknown.yaml", b"name: unknown", "unsupported format"),
    ("no-extension", b"text", "unsupported format"),
    ("broken.pdf", b"%PDF-1.4\nnot a document", "PDFSyntaxError"),
    ("empty.pdf", None, "no extractable text"),
    ("encrypted.pdf", None, "encrypted"),
])
def test_actual_format_refusals_are_not_partial_success(workspace, name, raw, reason):
    directory, output = workspace
    (directory / "a-good.txt").write_text("Included only if all succeed")
    (directory / name).write_bytes((FIXTURES / name).read_bytes() if raw is None else raw)
    with pytest.raises(bundle.PreparationError, match=reason):
        prepare(workspace)
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("payload", [None, b"", b" \r\n\t"])
def test_no_usable_input_refuses(workspace, payload):
    directory, _ = workspace
    if payload is not None:
        (directory / "empty.txt").write_bytes(payload)
    with pytest.raises(bundle.PreparationError, match="no documents|no non-whitespace"):
        prepare(workspace)


@pytest.mark.parametrize("kind", ["file-link", "directory-link", "dangling-link", "fifo"])
def test_nonregular_members_refuse_without_following(workspace, kind):
    directory, _ = workspace
    (directory / "good.txt").write_text("good")
    outside = directory.parents[1] / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("must not enter the bundle")
    bad = directory / "bad.txt"
    if kind == "fifo":
        os.mkfifo(bad)
    else:
        target = {"file-link": outside / "secret.txt", "directory-link": outside,
                  "dangling-link": outside / "missing"}[kind]
        bad.symlink_to(target)
    with pytest.raises(bundle.PreparationError, match="nonregular"):
        prepare(workspace)


@pytest.mark.parametrize("kind", ["escape", "overlap", "nonempty", "output-link", "dataset-link"])
def test_input_and_output_boundaries(workspace, kind):
    directory, output = workspace
    (directory / "good.txt").write_text("good")
    dataset = "Unit"
    if kind == "escape":
        dataset = "../Unit"
    elif kind == "overlap":
        output = directory / "output"
        output.mkdir()
    elif kind == "nonempty":
        (output / "prior.txt").write_text("preserved")
    elif kind == "output-link":
        link = output.with_name("output-link")
        link.symlink_to(output)
        output = link
    else:
        (directory.parent / "Alias").symlink_to(directory)
        dataset = "Alias"
    with pytest.raises(bundle.PreparationError):
        bundle.prepare(directory.parent, dataset, output, HEAD)


@pytest.mark.parametrize("kind", ["membership", "same-size-content"])
def test_source_change_during_conversion_refuses(workspace, monkeypatch, kind):
    directory, output = workspace
    target = directory / "a.txt"
    target.write_bytes(b"old")
    original = bundle._convert

    def change(raw, suffix):
        converted = original(raw, suffix)
        if kind == "membership":
            (directory / "new.txt").write_bytes(b"new")
        else:
            old = target.stat()
            target.write_bytes(b"new")
            os.utime(target, ns=(old.st_atime_ns, old.st_mtime_ns))
        return converted

    monkeypatch.setattr(bundle, "_convert", change)
    with pytest.raises(bundle.PreparationError, match="changed"):
        prepare(workspace)
    assert list(output.iterdir()) == []


def test_first_read_atime_is_not_a_content_change(workspace):
    directory, _ = workspace
    path = directory / "a.txt"
    path.write_bytes(b"content")
    os.utime(path, ns=(0, path.stat().st_mtime_ns))
    assert prepare(workspace)[1]["members"][0]["raw_bytes"] == 7


def test_converter_version_is_observed_and_refuses_mismatch(workspace, monkeypatch):
    directory, _ = workspace
    (directory / "text.pdf").write_bytes((FIXTURES / "text.pdf").read_bytes())
    monkeypatch.setattr(bundle.importlib.metadata, "version", lambda name: "unreviewed")
    with pytest.raises(bundle.PreparationError, match="converter version"):
        prepare(workspace)


@pytest.mark.parametrize("failed_name", ["input_manifest.json", "github-output"])
def test_publication_io_failure_returns_failure(workspace, monkeypatch, failed_name):
    directory, output = workspace
    (directory / "good.txt").write_text("good")
    actual_open = Path.open

    def fail(path, *args, **kwargs):
        if path.name == failed_name:
            raise OSError("injected export failure")
        return actual_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail)
    assert bundle.main(["--inputs-root", str(directory.parent), "--dataset", "Unit",
                        "--output-dir", str(output), "--source-commit", HEAD,
                        "--github-output", str(output.parent / "github-output")]) == 1
    assert not (output.parent / "github-output").exists()


SHIM = r'''import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
event = {'command': name, 'args': args}
if name == 'poetry' and args[:2] == ['run', 'python']:
    os.execv(sys.executable, [sys.executable, '-B'] + args[2:])
if name == 'poetry' and args[:4] == ['run', 'd4d', 'api', 'run']:
    source = pathlib.Path(args[args.index('--bundle') + 1])
    event['bundle'] = source.read_bytes().hex()
    target = pathlib.Path(args[args.index('--out-dir') + 1]); target.mkdir(parents=True, exist_ok=True)
    project = args[args.index('--project') + 1]
    for suffix in ['_d4d.yaml', '_d4d_core.yaml', '_reconciliation.md', '_provenance.yaml']:
        (target / (project + suffix)).write_text('synthetic generated artifact\n')
elif name == 'poetry' and args[:2] != ['run', 'linkml-validate']:
    raise SystemExit('unexpected poetry invocation')
if name == 'git' and args == ['rev-parse', 'HEAD']:
    state = pathlib.Path(os.environ['GIT_STATE'])
    event['resolved_head'] = state.read_text() if state.exists() else 'a' * 40
    print(event['resolved_head'])
elif name == 'git' and args[0] not in ['config', 'checkout', 'add', 'commit', 'push']:
    raise SystemExit('unexpected git invocation')
if name == 'git' and args[0] == 'add':
    event['staged'] = {p: pathlib.Path(p).read_bytes().hex() for p in args[1:]}
if name == 'git' and args[0] == 'commit':
    pathlib.Path(os.environ['GIT_STATE']).write_text('b' * 40)
if name == 'gh' and args[:2] == ['pr', 'create']:
    print('https://example.invalid/synthetic-pr')
elif name == 'gh' and args[:2] != ['issue', 'comment']:
    raise SystemExit('unexpected gh invocation')
with open(os.environ['EVENTS'], 'a') as stream:
    stream.write(json.dumps(event) + '\n')
'''


def workflow_workspace(tmp_path):
    work = tmp_path / "checkout"
    work.mkdir()
    script = work / "src/github/assistant_bundle.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    inputs = work / "data/sheets_d4dassistant/inputs/Unit"
    inputs.mkdir(parents=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ["poetry", "git", "gh"]:
        path = bindir / name
        path.write_text("#!" + sys.executable + "\n" + SHIM)
        path.chmod(0o700)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = {"PATH": str(bindir) + os.pathsep + os.defpath,
           "PYTHONDONTWRITEBYTECODE": "1", "RUNNER_TEMP": str(runtime),
           "GITHUB_OUTPUT": str(tmp_path / "github-output"), "DATASET": "Unit",
           "GIT_STATE": str(tmp_path / "generated-commit"),
           "EVENTS": str(tmp_path / "events.jsonl")}
    return work, inputs, env


def run_step(step, work, env, values):
    def replace(match):
        key = match.group(1).strip()
        assert key in values, key
        return values[key]

    text = re.sub(r"\$\{\{(.*?)\}\}", replace, step["run"])
    return subprocess.run(["/bin/bash", "-e"], input=text, text=True, cwd=work,
                          env=env, capture_output=True, timeout=30)


def steps():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    respond = workflow["jobs"]["respond-to-mention"]
    return workflow, {s.get("id") or s["name"]: s for s in respond["steps"]}


def test_actual_workflow_shell_hands_complete_bundle_and_stages_manifest(tmp_path):
    work, inputs, env = workflow_workspace(tmp_path)
    docs = mixed(inputs)
    _, selected = steps()
    result = run_step(selected["resolve"], work, env, {})
    assert result.returncode == 0, result.stderr
    outputs = dict(line.split("=", 1) for line in Path(env["GITHUB_OUTPUT"]).read_text().splitlines())
    values = {"steps.resolve.outputs." + k: v for k, v in outputs.items()}
    values["needs.check-mention.outputs.item-number"] = "123"
    values["github.server_url"] = "https://example.invalid"
    values["github.repository"] = "owner/repository"
    for name in ["Generate datasheet", "Validate against the schema", "pr"]:
        result = run_step(selected[name], work, env, values)
        assert result.returncode == 0, (name, result.stderr)
    events = [json.loads(line) for line in Path(env["EVENTS"]).read_text().splitlines()]
    generation = [e for e in events if e["command"] == "poetry" and e["args"][:4] == ["run", "d4d", "api", "run"]]
    assert len(generation) == 1
    assert generation[0]["args"] == ["run", "d4d", "api", "run", "--project", "Unit",
        "--bundle", outputs["bundle"], "--out-dir", "data/sheets_d4dassistant",
        "--label", outputs["label"], "--yes"]
    raw = bytes.fromhex(generation[0]["bundle"])
    manifest_path = work / "data/sheets_d4dassistant/Unit_input_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest_path.read_bytes() == Path(outputs["input-manifest"]).read_bytes()
    assert [row["path"] for row in manifest["members"]] == sorted(docs)
    assert manifest["bundle"]["sha256"] == hashlib.sha256(raw).hexdigest()
    added = next(e for e in events if e["command"] == "git" and e["args"][0] == "add")
    assert len(added["staged"]) == 5
    assert bytes.fromhex(added["staged"]["data/sheets_d4dassistant/Unit_input_manifest.json"]) == manifest_path.read_bytes()
    pr = next(e for e in events if e["command"] == "gh")
    body = pr["args"][pr["args"].index("--body") + 1]
    expected_url = ("https://example.invalid/owner/repository/blob/" + "b" * 40
                    + "/data/sheets_d4dassistant/Unit_input_manifest.json")
    assert f"[Input manifest]({expected_url})" in body
    assert manifest["bundle"]["sha256"] in body
    assert manifest["source_commit"] == "a" * 40
    heads = [(i, event["resolved_head"]) for i, event in enumerate(events)
             if "resolved_head" in event]
    commit_index = next(i for i, event in enumerate(events)
                        if event["command"] == "git" and event["args"][0] == "commit")
    push_index = next(i for i, event in enumerate(events)
                      if event["command"] == "git" and event["args"][0] == "push")
    assert [head for _, head in heads] == ["a" * 40, "b" * 40]
    assert heads[0][0] < commit_index < heads[1][0] < push_index
    assert f"All {len(docs)} input documents" in body


@pytest.mark.parametrize("kind", ["invalid-utf8", "unknown", "empty", "encrypted", "symlink"])
def test_preparation_failure_blocks_workflow_generation_and_reports(tmp_path, kind):
    work, inputs, env = workflow_workspace(tmp_path)
    if kind == "invalid-utf8":
        (inputs / "bad.txt").write_bytes(b"\xff")
    elif kind == "unknown":
        (inputs / "bad.zip").write_bytes(b"zip")
    elif kind == "encrypted":
        (inputs / "bad.pdf").write_bytes((FIXTURES / "encrypted.pdf").read_bytes())
    elif kind == "symlink":
        (inputs / "bad.txt").symlink_to(tmp_path / "absent")
    _, selected = steps()
    result = run_step(selected["resolve"], work, env, {})
    assert result.returncode != 0
    assert not Path(env["GITHUB_OUTPUT"]).exists()
    for name in ["Generate datasheet", "Validate against the schema", "pr"]:
        assert "if" not in selected[name]  # Actions' default success prerequisite.
    values = {"job.status": "failure", "steps.resolve.outcome": "failure",
              "steps.resolve.outputs.dataset": "", "steps.pr.outputs.url": "",
              "needs.check-mention.outputs.item-number": "123",
              "github.server_url": "https://example.invalid", "github.repository": "a/b",
              "github.run_id": "99"}
    result = run_step(selected["Report back on the issue"], work, env, values)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in Path(env["EVENTS"]).read_text().splitlines()]
    assert all(e["command"] != "poetry" for e in events)
    assert not any(e["command"] == "git" and e["args"][0] != "rev-parse" for e in events)
    assert "before generation" in events[-1]["args"][-1]


def test_no_request_is_not_eligible_and_generation_keeps_exact_options():
    workflow, selected = steps()
    jobs = workflow["jobs"]
    assert jobs["respond-to-mention"]["if"] == "needs.check-mention.outputs.qualified-mention == 'true'"
    assert jobs["check-mention"]["outputs"]["qualified-mention"] == "${{ steps.request.outputs.request }}"
    assert selected["resolve"]["env"] == {"DATASET": "${{ needs.check-mention.outputs.dataset }}"}
    assert "outputs.prompt" not in WORKFLOW.read_text()
    assert "find " not in selected["resolve"]["run"] and "head -1" not in selected["resolve"]["run"]
    assert "--condition" not in selected["Generate datasheet"]["run"]
    assert "--yes" in selected["Generate datasheet"]["run"]
