"""Complete-directory preparation (#4450).

The three PDFs are synthetic PDF1.4 documents, never captured research data.
encrypted.pdf is Standard Security R2 with an empty user password: accepting
that password must still not admit an encrypted document. These tests run the
real locked pdfminer converter. Workflow wiring is in test_assistant_workflow.py.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/github/assistant_bundle.py"
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
