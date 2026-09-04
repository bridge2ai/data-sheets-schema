"""`--method` resolution for the CLI (#934): the label's own directory, or a
click error that names what was searched — never a Python traceback."""

from __future__ import annotations

import click

from data_sheets_schema.runs import method_for_label


def resolve_method(label: str, project: str | None = None) -> str:
    try:
        return method_for_label(label, project)
    except LookupError as exc:
        raise click.ClickException(str(exc)) from None
