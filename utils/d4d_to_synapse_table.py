"""Publish the complete historical v8 HTML selection to Standards Explorer.

#5055, 2026-10-16. Reads the four declared HTML files and dedicated stylesheet;
updates the existing D4D_content table, preserving its schema and older snapshots.
"""

from collections import Counter
from pathlib import Path

import pandas as pd
import synapseclient
from synapseclient import Row, RowSet
from synapseclient.table import SelectColumn


TABLE_ID = "syn68885644"
SOURCE_FOLDER = Path("src/html/output")
CSS_NAME = "datasheet-v8.css"
HTML_TEMPLATE = "D4D_-_{project}_v8_human_readable.html"
ORG_ID_MAP = {
    "AI-READI": "B2AI_ORG:114",
    "CHORUS": "B2AI_ORG:115",
    "CM4AI": "B2AI_ORG:116",
    "VOICE": "B2AI_ORG:117",
}
COLUMNS = ["content_type", "content_id", "content_text"]
# Synapse documents LARGETEXT as less than 524,288 characters:
# https://python-docs.synapse.org/en/v4.13.0/reference/experimental/sync/table/
LARGETEXT_CHARACTER_LIMIT = 524_288


def _read_content(path: Path) -> str:
    """Read exact UTF-8 text, refusing absent, blank or oversized inputs."""
    text = path.read_bytes().decode("utf-8")
    if not text.strip():
        raise ValueError(f"Publication input is empty: {path}")
    # Count UTF-16 units conservatively, including non-BMP characters supported
    # by the Java-backed service, instead of assuming every character is ASCII.
    if len(text.encode("utf-16-le")) // 2 >= LARGETEXT_CHARACTER_LIMIT:
        raise ValueError(f"Publication input exceeds the Synapse LARGETEXT limit: {path}")
    return text


def load_publication(source_folder: Path = SOURCE_FOLDER) -> pd.DataFrame:
    """Load every required asset before authentication or any remote mutation."""
    source_folder = Path(source_folder)
    rows = [("css", "", _read_content(source_folder / CSS_NAME))]
    for project, organization in ORG_ID_MAP.items():
        path = source_folder / HTML_TEMPLATE.format(project=project)
        rows.append(("html", organization, _read_content(path)))
    return pd.DataFrame(rows, columns=COLUMNS)


def _content_rows(frame: pd.DataFrame) -> Counter:
    """Compare complete text and multiplicity independently of query row order."""
    if not set(COLUMNS).issubset(frame.columns):
        raise ValueError("Synapse query did not return the D4D content columns")
    return Counter(frame[COLUMNS].fillna("").itertuples(index=False, name=None))


def _capture_rows(syn, query: str) -> RowSet:
    """Materialize every JSON query page before inspecting or deleting rows."""
    result = syn.tableQuery(query, resultsAs="rowset")
    if not result.headers:
        # An empty query can omit headers; retain the existing table's columns.
        columns = {column.name: column for column in syn.getTableColumns(TABLE_ID)}
        result.headers = [SelectColumn.from_column(columns[name]) for name in COLUMNS]
    # TableQueryResult is a consumable iterator: asDataFrame() advances its
    # internal rowset to the final page. Capture the whole set first so deletion
    # cannot accidentally omit the earlier pages after verification.
    captured = result.asRowSet()
    if [header.name for header in captured.headers] != COLUMNS:
        raise ValueError("Synapse query did not return the declared D4D columns in order")
    return captured


def _rowset_frame(rows: RowSet) -> pd.DataFrame:
    return pd.DataFrame(
        [row["values"] for row in rows.rows],
        columns=[header.name for header in rows.headers],
    )


def generate_table(syn, d4d_df: pd.DataFrame):
    """Append and verify replacements before deleting the captured old rows.

    Synapse's legacy client does not make this sequence atomic. A failed append
    leaves the old rows intact; a later failure can leave extra current rows,
    but no new snapshot is published until the complete final content verifies.
    The portal continues to use its previously selected immutable snapshot.
    A retry captures all current rows and safely replaces them with one set.
    """
    expected = _content_rows(d4d_df)
    required = Counter({("css", ""): 1})
    required.update(("html", org) for org in ORG_ID_MAP.values())
    if Counter(d4d_df[COLUMNS[:2]].itertuples(index=False, name=None)) != required:
        raise ValueError("Publication must contain one stylesheet and all four organizations")
    if any(not isinstance(text, str) or not text.strip() for text in d4d_df.content_text):
        raise ValueError("Publication content must be nonempty text")

    query = f"SELECT content_type, content_id, content_text FROM {TABLE_ID}"
    existing_rows = _capture_rows(syn, query)
    existing = _content_rows(_rowset_frame(existing_rows))

    # The server's CSV reader discards empty physical lines inside multiline
    # cells (#5055 live round-trip evidence). Send exact strings as JSON RowSet
    # values, retaining the existing table ID and column IDs. No normalization.
    replacement = RowSet(
        tableId=TABLE_ID, headers=existing_rows.headers,
        rows=[Row(values=list(values)) for values in d4d_df[COLUMNS].itertuples(index=False, name=None)],
    )
    uploaded = syn.store(replacement)
    staged = _content_rows(_rowset_frame(_capture_rows(syn, query)))
    if staged != existing + expected:
        raise RuntimeError("Synapse upload verification failed; prior rows were not deleted")

    if existing:
        syn.delete(existing_rows)
    actual = _content_rows(_rowset_frame(_capture_rows(syn, query)))
    if actual != expected:
        raise RuntimeError("Synapse replacement verification failed; no snapshot was created")
    version = syn.create_snapshot_version(TABLE_ID)
    print(f"Published {len(d4d_df)} v8 content rows to {TABLE_ID}.{version}")
    return uploaded


def main():
    publication = load_publication()
    syn = synapseclient.login()
    generate_table(syn, publication)


if __name__ == "__main__":
    main()
