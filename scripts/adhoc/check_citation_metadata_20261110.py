#!/usr/bin/env python3
"""Check the Zenodo citation metadata added before the first Zenodo-archived release (2026-11-10).

Purpose: CITATION.cff is what Zenodo reads for authors, ORCIDs and affiliations when no .zenodo.json exists, and
GitHub shows "Cite this repository" only for a valid file. No CFF validator is installed offline, so this checks
the CFF 1.2.0 required fields and shapes, the ORCID checksum (ISO 7064 mod 11-2), project policy for the primary
author entry vs. CFF optional fields on additional authors, version parity across all schema/release declarations,
and that the files whose cookiecutter "My Name" placeholder was replaced still parse and hold non-empty values
with no placeholder.
Inputs: the repository root (argv[1], default repository root relative to this script).
Outputs: one line per check; exit 1 on any failure.
Serves: PR #5709 and validation issues #5732-#5736.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ORCID_RE = re.compile(r"^https://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$")
LICENSE_COPYRIGHT_RE = re.compile(r"(?m)^Copyright \(c\)\s+\d{4}\s+\S+")


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_https_url(value: Any) -> bool:
    if not _is_non_empty_str(value) or any(ch.isspace() for ch in value):
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and "." in parsed.netloc
        and bool(parsed.path and parsed.path != "/")
    )


def orcid_checksum_ok(orcid: str) -> bool:
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    expected = "X" if result == 10 else str(result)
    return digits[-1] == expected


def run_checks(root: Path | None = None) -> list[str]:
    repo_root = DEFAULT_ROOT if root is None else Path(root)
    failures: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(("ok   " if ok else "FAIL ") + what)
        if not ok:
            failures.append(what)

    def read_text_safe(rel_path: str) -> str | None:
        path = repo_root / rel_path
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            check(False, f"{rel_path} is readable ({exc})")
            return None

    def load_yaml_mapping(rel_path: str) -> dict[str, Any] | None:
        text = read_text_safe(rel_path)
        if text is None:
            return None
        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            check(False, f"{rel_path} parses as valid YAML ({exc.__class__.__name__})")
            return None
        is_mapping = isinstance(loaded, dict)
        check(is_mapping, f"{rel_path} parses to a mapping")
        return loaded if is_mapping else None

    cff_raw = load_yaml_mapping("CITATION.cff")
    cff: dict[str, Any] = cff_raw if cff_raw is not None else {}

    for key in ("cff-version", "message", "title", "authors"):
        check(key in cff, f"CITATION.cff has required key {key!r}")
    check(cff.get("cff-version") == "1.2.0", "cff-version is 1.2.0")
    check(_is_non_empty_str(cff.get("message")), "message is a non-empty string")
    check(_is_non_empty_str(cff.get("title")), "title is a non-empty string")
    check(cff.get("type") in ("software", "dataset"), "type is software or dataset")

    raw_authors = cff.get("authors")
    authors_ok = isinstance(raw_authors, list) and len(raw_authors) >= 1
    check(authors_ok, "authors is a non-empty list")
    authors_list: list[Any] = raw_authors if isinstance(raw_authors, list) else []

    for i, author in enumerate(authors_list):
        if not isinstance(author, dict):
            check(False, f"author {i} is a mapping with non-empty family-names or name")
            continue
        has_person_name = _is_non_empty_str(author.get("family-names")) and (
            "given-names" not in author or _is_non_empty_str(author.get("given-names"))
        )
        has_entity_name = _is_non_empty_str(author.get("name"))
        check(
            has_person_name or has_entity_name,
            f"author {i} has non-empty family-names (and given-names if present) or name",
        )
        # CFF 1.2.0 optional fields: validate shape/checksum whenever present on any author
        if "orcid" in author:
            orcid = author.get("orcid")
            m = ORCID_RE.fullmatch(orcid) if isinstance(orcid, str) else None
            check(bool(m), f"author {i} ORCID is an https://orcid.org/ URL")
            check(bool(m) and orcid_checksum_ok(m.group(1)), f"author {i} ORCID checksum is valid")
        if "affiliation" in author:
            check(
                _is_non_empty_str(author.get("affiliation")),
                f"author {i} affiliation is a non-empty string",
            )

    # Explicit project policy: primary author (author 0) declares ORCID and affiliation
    primary_author = authors_list[0] if authors_list and isinstance(authors_list[0], dict) else {}
    check(
        _is_non_empty_str(primary_author.get("orcid")) and _is_non_empty_str(primary_author.get("affiliation")),
        "project policy: primary author (author 0) declares ORCID and affiliation",
    )

    check(cff.get("license") == "MIT", "license is the SPDX id MIT")
    for key in ("repository-code", "url"):
        check(_is_valid_https_url(cff.get(key)), f"{key} is a valid https URL with host and path")

    raw_keywords = cff.get("keywords")
    keywords_ok = (
        isinstance(raw_keywords, list)
        and len(raw_keywords) >= 1
        and all(_is_non_empty_str(k) for k in raw_keywords)
    )
    check(keywords_ok, "keywords is a non-empty list of non-empty strings")

    cff_version = cff.get("version")
    cff_version_ok = isinstance(cff_version, str) and bool(SEMVER_RE.fullmatch(cff_version))
    check(cff_version_ok, f"CITATION.cff version {cff_version!r} is a semantic version string")

    for schema_rel in (
        "src/data_sheets_schema/schema/data_sheets_schema.yaml",
        "src/data_sheets_schema/schema/data_sheets_schema_core.yaml",
        "src/data_sheets_schema/schema/D4D_Core.yaml",
    ):
        schema_doc = load_yaml_mapping(schema_rel)
        declared_ver = schema_doc.get("version") if schema_doc is not None else None
        check(
            cff_version_ok and isinstance(declared_ver, str) and cff_version == declared_ver,
            f"CITATION.cff version {cff_version!r} equals {schema_rel} version {declared_ver!r}",
        )

    history_rel = "src/data_sheets_schema/schema/release_history.yaml"
    history_doc = load_yaml_mapping(history_rel)
    releases = history_doc.get("releases") if history_doc is not None else None
    latest_release = (
        releases[-1].get("version")
        if isinstance(releases, list) and releases and isinstance(releases[-1], dict)
        else None
    )
    check(
        cff_version_ok and isinstance(latest_release, str) and cff_version == latest_release,
        f"CITATION.cff version {cff_version!r} equals {history_rel} latest release {latest_release!r}",
    )

    pyproject_text = read_text_safe("pyproject.toml")
    pyproject: dict[str, Any] | None = None
    if pyproject_text is not None:
        try:
            loaded_toml = tomllib.loads(pyproject_text)
            pyproject = loaded_toml if isinstance(loaded_toml, dict) else None
            if pyproject is None:
                check(False, "pyproject.toml parses to a TOML table")
        except ValueError as exc:
            check(False, f"pyproject.toml parses as valid TOML ({exc})")
    if pyproject is not None:
        tool_sec = pyproject.get("tool")
        poetry_sec = tool_sec.get("poetry") if isinstance(tool_sec, dict) else None
        project_sec = pyproject.get("project") if isinstance(pyproject.get("project"), dict) else None
        authors_pp = (
            poetry_sec.get("authors")
            if isinstance(poetry_sec, dict) and "authors" in poetry_sec
            else (project_sec.get("authors") if isinstance(project_sec, dict) else None)
        )
        check(
            isinstance(authors_pp, list)
            and len(authors_pp) >= 1
            and all(_is_non_empty_str(entry) for entry in authors_pp),
            "pyproject.toml parses and declares non-empty authors",
        )
        deps_sec = poetry_sec.get("dependencies") if isinstance(poetry_sec, dict) else None
        tomli_dep = deps_sec.get("tomli") if isinstance(deps_sec, dict) else None
        tomli_declared = (
            isinstance(tomli_dep, dict)
            and _is_non_empty_str(tomli_dep.get("version"))
            and _is_non_empty_str(tomli_dep.get("python"))
            and "<3.11" in str(tomli_dep.get("python")).replace(" ", "")
        )
        check(
            tomli_declared,
            "pyproject.toml declares conditional tomli dependency for Python < 3.11",
        )

    cruft_text = read_text_safe(".cruft.json")
    if cruft_text is not None:
        try:
            cruft_doc = json.loads(cruft_text)
        except json.JSONDecodeError as exc:
            check(False, f".cruft.json parses as valid JSON ({exc.msg})")
            cruft_doc = None
        if cruft_doc is not None:
            cc = (
                cruft_doc.get("context", {}).get("cookiecutter", {})
                if isinstance(cruft_doc, dict) and isinstance(cruft_doc.get("context"), dict)
                else {}
            )
            check(
                isinstance(cc, dict)
                and _is_non_empty_str(cc.get("full_name"))
                and _is_non_empty_str(cc.get("__author")),
                ".cruft.json parses and declares non-empty full_name and __author",
            )

    about_doc = load_yaml_mapping("about.yaml")
    if about_doc is not None:
        check(_is_non_empty_str(about_doc.get("author")), "about.yaml declares non-empty author")

    license_text = read_text_safe("LICENSE")
    if license_text is not None:
        check(
            bool(LICENSE_COPYRIGHT_RE.search(license_text)),
            "LICENSE contains a non-empty Copyright (c) line",
        )

    for name in ("pyproject.toml", "LICENSE", "about.yaml", ".cruft.json", "CITATION.cff"):
        file_text = read_text_safe(name)
        if file_text is not None:
            check(
                "my name" not in file_text.lower(),
                f"{name} holds no case-insensitive 'My Name' placeholder",
            )

    print(f"{len(failures)} failure(s)")
    return failures


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    target_root = Path(args[0]) if args else DEFAULT_ROOT
    failures = run_checks(target_root)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
