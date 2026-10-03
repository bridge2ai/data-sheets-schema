#!/usr/bin/env python3
"""Additive per-rating model-family disclosure; no scoring or provider calls."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from data_sheets_schema.model_disclosure import GenerationBinding, build_report, render, write_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluations", nargs="+", type=Path)
    parser.add_argument("--generation-binding", nargs=3, action="append", default=[],
                        metavar=("EVALUATION", "INPUT", "PROVENANCE"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="anchor for recorded relative paths")
    parser.add_argument("--format", choices=("markdown", "csv", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="new output file (existing files are never replaced)")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.evaluations,
                              bindings=[GenerationBinding(*(Path(p) for p in triple))
                                        for triple in args.generation_binding], root=args.root)
        if args.output:
            write_report(report, args.output, format=args.format)
        else:
            sys.stdout.write(render(report, args.format))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        parser.exit(2, f"model disclosure: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
