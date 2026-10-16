"""Offline publication safety tests for #5055, 2026-10-16.

Use the real Synapse Table CSV adapter and a fake remote table; no login, network,
model calls or changes to historical publication assets are performed.
"""

from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
import yaml

from utils import d4d_to_synapse_table as publisher


ROOT = Path(__file__).resolve().parents[1]
FILES = [publisher.CSS_NAME] + [
    publisher.HTML_TEMPLATE.format(project=project)
    for project in publisher.ORG_ID_MAP
]


@pytest.fixture
def publication_files(tmp_path):
    folder = tmp_path / "src/html/output"
    folder.mkdir(parents=True)
    for name in FILES:
        (folder / name).write_bytes(f"{name}\r\nπ and \"quoted, text\"\n".encode())
    # Old assets must never be selected as a fallback for missing v8 content.
    for project in publisher.ORG_ID_MAP:
        (folder / f"D4D_-_{project}_v4_human_readable.html").write_text("historical v4")
    (folder / "datasheet-common.css").write_text("historical css")
    return folder


class Query:
    def __init__(self, frame):
        self.frame = frame.copy(deep=True)

    def asDataFrame(self):
        return self.frame.copy(deep=True)


class RemoteTable:
    """Model append, captured-row deletion and snapshots with persistent row IDs."""

    def __init__(self, existing=None, fail=None):
        if existing is None:
            existing = pd.DataFrame(
                [("css", "", "old css"), ("html", "B2AI_ORG:114", "old HTML")],
                columns=publisher.COLUMNS,
            )
        self.rows = existing.copy(deep=True)
        self.next_id = len(existing)
        self.events = []
        self.snapshots = []
        self.fail = fail

    def tableQuery(self, query):
        assert query == (
            "SELECT content_type, content_id, content_text FROM syn68885644"
        )
        self.events.append("query")
        return Query(self.rows.iloc[::-1])  # Query ordering is not stable.

    def store(self, table):
        self.events.append("store")
        assert table.tableId == publisher.TABLE_ID
        if self.fail == "store":
            raise RuntimeError("synthetic upload failure")
        # Exercise Synapse's actual DataFrame → CSV → DataFrame path, including
        # commas, Unicode, CRLF and quotes in complete HTML/CSS content.
        uploaded = table.asDataFrame().fillna("")
        assert list(uploaded.columns) == publisher.COLUMNS
        uploaded.index = range(self.next_id, self.next_id + len(uploaded))
        self.next_id += len(uploaded)
        if self.fail == "corrupt_upload":
            uploaded.iloc[-1, 2] = "truncated HTML"
        self.rows = pd.concat([self.rows, uploaded])
        return table

    def delete(self, query):
        self.events.append("delete")
        if self.fail == "delete":
            raise RuntimeError("synthetic deletion failure")
        self.rows = self.rows.drop(query.frame.index)
        if self.fail == "corrupt_replacement":
            self.rows.iloc[-1, 2] = "changed after deletion"

    def create_snapshot_version(self, table_id):
        self.events.append("snapshot")
        assert table_id == publisher.TABLE_ID
        if self.fail == "snapshot":
            raise RuntimeError("synthetic snapshot failure")
        self.snapshots.append(self.rows.copy(deep=True))
        return 9


def test_loads_only_complete_v8_assets_without_rewriting_text(publication_files):
    result = publisher.load_publication(publication_files)
    assert result.content_type.tolist() == ["css", "html", "html", "html", "html"]
    assert result.content_id.tolist() == ["", *publisher.ORG_ID_MAP.values()]
    assert result.content_text.tolist() == [
        (publication_files / name).read_bytes().decode() for name in FILES
    ]


@pytest.mark.parametrize("name", FILES)
@pytest.mark.parametrize("failure", ["missing", "blank", "invalid_utf8", "oversized"])
def test_invalid_publication_refuses_before_login(
    publication_files, monkeypatch, name, failure
):
    path = publication_files / name
    if failure == "missing":
        path.unlink()
    elif failure == "blank":
        path.write_text(" \n\t")
    elif failure == "invalid_utf8":
        path.write_bytes(b"\xff")
    else:
        path.write_text("x" * publisher.LARGETEXT_CHARACTER_LIMIT)
    monkeypatch.chdir(publication_files.parents[2])
    login = Mock(side_effect=AssertionError("must not authenticate"))
    monkeypatch.setattr(publisher.synapseclient, "login", login)
    with pytest.raises((FileNotFoundError, ValueError, UnicodeDecodeError)):
        publisher.main()
    login.assert_not_called()


def test_non_bmp_content_respects_server_character_budget(publication_files):
    (publication_files / FILES[0]).write_text(
        "😀" * (publisher.LARGETEXT_CHARACTER_LIMIT // 2)
    )
    with pytest.raises(ValueError, match="LARGETEXT"):
        publisher.load_publication(publication_files)


def test_upload_verifies_before_deleting_and_snapshotting(publication_files):
    expected = publisher.load_publication(publication_files)
    remote = RemoteTable()
    publisher.generate_table(remote, expected)
    assert remote.events == ["query", "store", "query", "delete", "query", "snapshot"]
    assert publisher._content_rows(remote.rows) == publisher._content_rows(expected)
    assert publisher._content_rows(remote.snapshots[0]) == publisher._content_rows(expected)


@pytest.mark.parametrize("failure", ["store", "corrupt_upload"])
def test_failed_upload_preserves_all_old_rows(publication_files, failure):
    remote = RemoteTable(fail=failure)
    old_rows = remote.rows.copy(deep=True)
    with pytest.raises(RuntimeError):
        publisher.generate_table(remote, publisher.load_publication(publication_files))
    pd.testing.assert_frame_equal(remote.rows.loc[old_rows.index], old_rows)
    assert "delete" not in remote.events
    assert "snapshot" not in remote.events


@pytest.mark.parametrize("failure", ["delete", "corrupt_replacement", "snapshot"])
def test_failure_after_append_does_not_publish_and_retry_recovers(publication_files, failure):
    expected = publisher.load_publication(publication_files)
    remote = RemoteTable(fail=failure)
    with pytest.raises(RuntimeError):
        publisher.generate_table(remote, expected)
    assert remote.snapshots == []
    remote.fail = None
    publisher.generate_table(remote, expected)
    assert publisher._content_rows(remote.rows) == publisher._content_rows(expected)
    assert len(remote.rows) == 5
    assert len(remote.snapshots) == 1


def test_empty_existing_table_never_calls_delete(publication_files):
    remote = RemoteTable(pd.DataFrame(columns=publisher.COLUMNS))
    publisher.generate_table(remote, publisher.load_publication(publication_files))
    assert "delete" not in remote.events
    assert len(remote.snapshots[0]) == 5


@pytest.mark.parametrize("malformation", ["missing", "duplicate", "wrong_org", "empty_text"])
def test_incomplete_direct_call_cannot_mutate_remote(publication_files, malformation):
    data = publisher.load_publication(publication_files)
    if malformation == "missing":
        data = data.iloc[:-1]
    elif malformation == "duplicate":
        data = pd.concat([data, data.iloc[[1]]])
    elif malformation == "wrong_org":
        data.loc[1, "content_id"] = "B2AI_ORG:999"
    else:
        data.loc[1, "content_text"] = ""
    remote = RemoteTable()
    with pytest.raises(ValueError):
        publisher.generate_table(remote, data)
    assert remote.events == []


def test_workflow_serializes_publications_and_covers_selector_changes():
    config = yaml.safe_load((ROOT / ".github/workflows/d4d_to_synapse_table.yml").read_text())
    triggers = config.get("on", config.get(True))
    assert triggers["push"]["branches"] == ["main"]
    assert set(triggers["push"]["paths"]) >= {
        "src/html/output/*", "utils/d4d_to_synapse_table.py",
        ".github/workflows/d4d_to_synapse_table.yml",
    }
    assert "workflow_dispatch" in triggers
    assert config["concurrency"] == {
        "group": "d4d-synapse-publish", "cancel-in-progress": False,
    }
    job = config["jobs"]["update_d4d_table"]
    assert job["if"] == "github.ref == 'refs/heads/main'"
    steps = job["steps"]
    upload = [step for step in steps if "utils/d4d_to_synapse_table.py" in step.get("run", "")]
    assert len(upload) == 1
    assert upload[0]["run"] == "poetry run python utils/d4d_to_synapse_table.py"
    assert "continue-on-error" not in upload[0]
