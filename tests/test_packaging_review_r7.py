"""Exercise repair progress and installed metadata through their public effects."""
import base64
import csv
import hashlib
import importlib.metadata as metadata
from io import StringIO
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, provenance, resources
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec


def test_readable_repair_gets_another_round_when_schema_findings_increase(tmp_path, monkeypatch):
    """#1747: four parse diagnostics -> five shape findings -> valid YAML."""
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("Synthetic input\n")
    run = spec(project="EXTERNAL", bundle=bundle, manifest=None, profile="neutral", out_dir=tmp_path)
    run.full_path.write_text("id: x\ntitle: [unclosed\n", encoding="utf-8")

    class Repairs(FakeMessages):
        def create(self, **request):
            self.calls.append(request)
            marker = "shape-errors" if len(self.calls) == 1 else "clean"
            return FakeResponse(f"```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [{marker}]\n```")

    def validate(path, schema, cls):
        try:
            record = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            return ["yaml.parser.ParserError", "while parsing a flow sequence",
                    "expected ',' or ']'", "at line 3"], None
        if record["keywords"] == ["shape-errors"]:
            return [f"[ERROR] shape finding {n}" for n in range(5)], None
        return [], None

    monkeypatch.setattr(api, "_validator_lines", validate)
    client = SimpleNamespace(messages=Repairs())
    usage = []
    log = api._repair_invalid(run, client, {"name": "offline", "temperature": 0.0}, usage)
    assert len(client.messages.calls) == 2, log
    assert [row["findings"] for row in log if row["outcome"] == "applied"] == [4, 5]
    assert yaml.safe_load(run.full_path.read_text())["keywords"] == ["clean"]
    assert len(usage) == 2


@pytest.mark.parametrize("missing", ["METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "nested/RECORD"])
def test_deleted_shipped_metadata_is_a_dirty_install(tmp_path, monkeypatch, missing):
    """#1748: read the real distribution RECORD, including deleted rows."""
    info = tmp_path / "data_sheets_schema-1.0.dist-info"
    info.mkdir()
    files = {
        "data_sheets_schema/runtime.py": b"# shipped runtime\n",
        f"{info.name}/METADATA": b"Metadata-Version: 2.1\nName: data-sheets-schema\nVersion: 1.0\n",
        f"{info.name}/WHEEL": b"Wheel-Version: 1.0\n",
        f"{info.name}/entry_points.txt": b"[console_scripts]\nd4d = data_sheets_schema.cli:cli\n",
        f"{info.name}/licenses/LICENSE": b"License text\n",
        f"{info.name}/nested/RECORD": b"A shipped file, not installer bookkeeping\n",
    }
    rows = []
    for name, data in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        rows.append([name, f"sha256={digest}", str(len(data))])
    rows.append([f"{info.name}/RECORD", "", ""])
    out = StringIO()
    csv.writer(out).writerows(rows)
    (info / "RECORD").write_text(out.getvalue())
    dist = metadata.PathDistribution(info)
    monkeypatch.setattr(metadata, "distribution", lambda name: dist)
    monkeypatch.setattr(resources, "resource_root", lambda: (tmp_path, "install"))
    assert provenance.repo_facts()["dirty"] is False
    (info / missing).unlink()
    facts = provenance.repo_facts()
    assert facts["dirty"] is True, facts
    assert facts["dirty_paths"] == [f"{info.name}/{missing}"]


@pytest.mark.parametrize("name", ["RECORD", "INSTALLER", "REQUESTED", "direct_url.json"])
def test_missing_installer_bookkeeping_stays_exempt(tmp_path, name):
    good = tmp_path / "runtime.py"
    good.write_bytes(b"runtime")
    digest = base64.urlsafe_b64encode(hashlib.sha256(b"runtime").digest()).rstrip(b"=").decode()
    rows = [("data_sheets_schema/runtime.py", "sha256", digest, good),
            (f"data_sheets_schema-1.0.dist-info/{name}", None, None, tmp_path / name)]
    assert provenance._installed_files_changed(rows) == ([], True, [], False)
