"""Publish the complete historical v8 HTML selection to Standards Explorer.

#5055, 2026-10-16. Reads the four declared HTML files and dedicated stylesheet;
updates the existing D4D_content table, preserving its schema and older snapshots.

2026-10-16: the brief switch to an inline JSON RowSet append (#5058) made
every publication exceed the ~483 KB body that Synapse's AWS WAF will inspect on
`/table/transaction/async/start`, so uploads were rejected outright (bare, non-
Synapse 403 from the ALB itself). Reverted to the CSV/S3 upload path, which has
carried every prior publication (v4 onward) since 2025-08-14 without ever hitting
that limit, because the bulk bytes travel to S3 directly and only a small job
reference crosses the inspected endpoint. That path's known cost is a Synapse
CSV-import quirk: verified against a real publish (table version 35), it collapses
every run of two or more consecutive bare `\n` characters inside a quoted
multiline cell down to a single `\n`; an isolated single newline anywhere,
including a leading or trailing one, or a CRLF-delimited blank line, survives
untouched (`\r` makes that line non-empty). This schema's HTML never puts a
multi-newline run inside a whitespace-significant element (no `<pre>`, and the
only `white-space: pre-wrap` rule in datasheet-v8.css applies to single-line
`source-value` spans with no embedded newlines), so the collapsed runs have no
visible effect on the rendered page. This quirk predates v8; it was simply never
checked for exact round-trip fidelity before #5055, and almost certainly affects
every prior snapshot of this table too. Accepted as a known, visually-inert,
long-standing limitation rather than leaving publication blocked; verification
below predicts and tolerates exactly this discrepancy and nothing else.
"""

from collections import Counter
from pathlib import Path
import re
import sys

import pandas as pd
import synapseclient
from synapseclient import RowSet, Table
from synapseclient.core.exceptions import SynapseHTTPError
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


def _log_http_error(error: SynapseHTTPError) -> None:
    """Print the raw response so a non-Synapse block (proxy/WAF) is distinguishable
    from a genuine Synapse rejection: Synapse's own API errors are JSON with a
    'reason'/'errorCode'; anything else (e.g. a bare HTML error page, or unexpected
    Server/Via headers) indicates something in front of Synapse intercepted the call.
    """
    response = getattr(error, "response", None)
    if response is None:
        print(f"SynapseHTTPError with no response object: {error}", file=sys.stderr)
        return
    print(f"HTTP {response.status_code} from {response.url}", file=sys.stderr)
    for header in ("Content-Type", "Server", "Via", "X-Cache", "X-Amzn-Trace-Id"):
        if header in response.headers:
            print(f"  {header}: {response.headers[header]}", file=sys.stderr)
    print(f"  body: {response.text[:500]!r}", file=sys.stderr)


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


def _collapse_consecutive_newlines(text: str) -> str:
    """Predict Synapse's CSV-import behavior, verified against a real publish
    (table version 35, 2026-10-16): it collapses every run of two or more
    consecutive bare `\\n` characters inside a quoted multiline cell down to a
    single `\\n`. An isolated single newline anywhere — including a leading or
    trailing one — is left untouched, and a CRLF-delimited blank line survives
    because the `\\r` makes that line non-empty. (An earlier line-based model,
    "drop every exactly-empty physical line", looked right offline but failed
    against the live table: it also ate a genuine leading blank line that
    Synapse actually preserves.) Used only so verification matches the
    accepted post-upload shape instead of failing on this known, visually-
    inert discrepancy every run.
    """
    return re.sub(r"\n{2,}", "\n", text)


def _accepted_after_csv_upload(frame: pd.DataFrame) -> Counter:
    normalized = frame.copy()
    normalized["content_text"] = normalized["content_text"].map(_collapse_consecutive_newlines)
    return _content_rows(normalized)


def generate_table(syn, d4d_df: pd.DataFrame):
    """Append and verify replacements before deleting the captured old rows.

    Synapse's legacy client does not make this sequence atomic. A failed append
    leaves the old rows intact; a later failure can leave extra current rows,
    but no new snapshot is published until the complete final content verifies.
    The portal continues to use its previously selected immutable snapshot.
    A retry captures all current rows and safely replaces them with one set.
    """
    required = Counter({("css", ""): 1})
    required.update(("html", org) for org in ORG_ID_MAP.values())
    if Counter(d4d_df[COLUMNS[:2]].itertuples(index=False, name=None)) != required:
        raise ValueError("Publication must contain one stylesheet and all four organizations")
    if any(not isinstance(text, str) or not text.strip() for text in d4d_df.content_text):
        raise ValueError("Publication content must be nonempty text")

    query = f"SELECT content_type, content_id, content_text FROM {TABLE_ID}"
    existing_rows = _capture_rows(syn, query)
    existing = _content_rows(_rowset_frame(existing_rows))
    expected_after_upload = _accepted_after_csv_upload(d4d_df)

    # Retains the existing table ID so the schema/column IDs carry over; the
    # CSV/S3 upload path avoids the WAF body-size block that an inline JSON
    # RowSet append hits at this payload size (see module docstring).
    try:
        uploaded = syn.store(Table(TABLE_ID, values=d4d_df))
    except SynapseHTTPError as error:
        _log_http_error(error)
        raise
    staged = _content_rows(_rowset_frame(_capture_rows(syn, query)))
    if staged != existing + expected_after_upload:
        raise RuntimeError("Synapse upload verification failed; prior rows were not deleted")

    if existing:
        syn.delete(existing_rows)
    actual = _content_rows(_rowset_frame(_capture_rows(syn, query)))
    if actual != expected_after_upload:
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
