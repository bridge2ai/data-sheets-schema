"""Synthetic final-generation acceptance contract for D4D schema (G1).

Covers one minimal positive full -> Core -> pair-consistency -> HTML fixture and
four diagnostic single-field negative mutations against the active checkout's
LinkML schemas:
1. Narrative array on scalar Dataset.description (/description)
2. Bare Person string on Creator.principal_investigator (/creators/0/principal_investigator)
3. Unnormalized scalar permission on LicenseAndUseTerms.data_use_permission
   (/license_and_use_terms/data_use_permission)
4. List-valued FileCollection.collection_type (/file_collections/0/collection_type)

Permission normalization and CLI renderer CSS/output behavior are covered by
existing tests (tests/test_pr5531_regressions.py and tests/test_cli/test_render.py).
This synthetic fixture proves schema/projection/render mechanics only, not
scientific adequacy or live native whole-route acceptance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema import (
    d4d_pair_consistency,
    derive_core,
    instance_lint,
    resources,
)
from data_sheets_schema.rendering import human_readable_renderer
from data_sheets_schema.rendering.human_readable_renderer import render_yaml_file


REPO_ROOT = Path(__file__).resolve().parent.parent
FULL_SCHEMA_REL = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE_SCHEMA_REL = "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"
FULL_SCHEMA_PATH = REPO_ROOT / FULL_SCHEMA_REL
CORE_SCHEMA_PATH = REPO_ROOT / CORE_SCHEMA_REL


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_positive_full_dataset() -> dict[str, Any]:
    """Return a minimal valid full Dataset exercising 3.2.x acceptance shapes."""
    pi_person = {"id": "ORCID:0000-0002-1825-0097", "name": "Ada Lovelace", "orcid": "0000-0002-1825-0097"}
    contact_person = {"id": "ORCID:0000-0001-5109-3700", "name": "Grace Hopper", "orcid": "0000-0001-5109-3700"}
    dac_person = {"id": "ORCID:0000-0003-1415-9265", "name": "Katherine Johnson", "orcid": "0000-0003-1415-9265"}
    return {
        "id": "https://example.org/d4d/synthetic-acceptance",
        "name": "synthetic_acceptance",
        "title": "Synthetic Final Generation Acceptance",
        "description": "Scalar dataset narrative for final-generation acceptance.",
        "conforms_to": "https://w3id.org/bridge2ai/data-sheets-schema",
        "conforms_to_standard": ["OMOP_CDM", "WFDB"],
        "conforms_to_class": "Dataset",
        "conforms_to_schema": FULL_SCHEMA_REL,
        "purposes": [
            {
                "id": "https://example.org/d4d/synthetic-acceptance#purpose-1",
                "response": "Scalar purpose response for acceptance testing.",
            }
        ],
        "creators": [
            {
                "id": "https://example.org/d4d/synthetic-acceptance#creator-1",
                "principal_investigator": pi_person,
            }
        ],
        "license_and_use_terms": {
            "id": "https://example.org/d4d/synthetic-acceptance#terms-1",
            "data_use_permission": ["health_medical_biomedical_research", "no_commercial_use"],
            "contact_person": contact_person,
        },
        "data_governance": {
            "id": "https://example.org/d4d/synthetic-acceptance#gov-1",
            "committee_contact": dac_person,
            "committee_members": [dac_person],
        },
        "file_collections": [
            {
                "id": "https://example.org/d4d/synthetic-acceptance#coll-processed",
                "name": "processed_tables",
                "path": "data/processed",
                "collection_type": "processed_data",
                "total_bytes": 2048,
                "conforms_to_standard": ["OMOP_CDM"],
                "resources": [
                    {
                        "id": "https://example.org/d4d/synthetic-acceptance#file-table",
                        "name": "observations.tsv",
                        "path": "data/processed/observations.tsv",
                        "file_type": "data_file",
                        "bytes": 2048,
                        "format": "TSV",
                        "encoding": "UTF-8",
                        "media_type": "text/tab-separated-values",
                        "sha256": "eb363fc0980025a34410bf2ff9b617a10996401f2bd24d2cef403ce2bda4fd44",
                        "conforms_to": "https://ohdsi.github.io/CommonDataModel/",
                        "conforms_to_standard": ["OMOP_CDM"],
                    }
                ],
            },
            {
                "id": "https://example.org/d4d/synthetic-acceptance#coll-raw",
                "name": "raw_waveforms",
                "path": "data/raw",
                "collection_type": "raw_data",
                "total_bytes": 4096,
                "conforms_to_standard": ["WFDB"],
                "resources": [
                    {
                        "id": "https://example.org/d4d/synthetic-acceptance#file-waveform",
                        "name": "waveforms.tsv",
                        "path": "data/raw/waveforms.tsv",
                        "file_type": "data_file",
                        "bytes": 4096,
                        "format": "TSV",
                        "encoding": "UTF-8",
                        "media_type": "text/tab-separated-values",
                        "sha256": "61503bf2b1fb5dc43a8a21258ea14162c56da3fb446f43502eb66ca20e677a14",
                        "conforms_to": "https://wfdb.io/",
                        "conforms_to_standard": ["WFDB"],
                    }
                ],
            },
        ],
        "variables": [
            {
                "variable_name": "var_heart_rate_bpm",
                "data_type": "float",
                "measurement_technique": "technique_optical_ppg_v1",
                "description": "Resting heart rate variable.",
            }
        ],
        "splits": [
            {
                "name": "split_benchmark_v1",
                "split_details": "split_stratified_80_20_detail_v1",
            }
        ],
        "participant_privacy": [
            {
                "privacy_techniques": "privacy_k_anonymity_k5_v1",
                "reidentification_risk": "risk_low_expert_determination_v1",
            }
        ],
    }


def test_positive_full_to_core_pair_and_html_acceptance(tmp_path: Path) -> None:
    """Verify positive full Dataset -> CoreDataset -> pair consistency -> HTML rendering."""
    checked_modules = {}
    for mod in (derive_core, d4d_pair_consistency, instance_lint, human_readable_renderer, resources):
        resolved_mod = Path(mod.__file__).resolve()
        assert resolved_mod.is_relative_to(REPO_ROOT)
        checked_modules[mod.__name__] = str(resolved_mod)
    assert resources.CHECKOUT_ROOT.resolve() == REPO_ROOT

    pair_schema = d4d_pair_consistency.load_pair_schema(FULL_SCHEMA_PATH, CORE_SCHEMA_PATH)
    full_data = build_positive_full_dataset()
    full_snapshot = copy.deepcopy(full_data)

    full_report = instance_lint.lint_instance(full_data, str(FULL_SCHEMA_PATH), "Dataset")
    assert full_report.valid, [e.to_dict() for e in full_report.errors]
    assert full_report.errors == []
    assert full_data == full_snapshot

    full_yaml_path = tmp_path / "synthetic_acceptance_full.yaml"
    core_yaml_path = tmp_path / "synthetic_acceptance_core.yaml"
    html_output_path = tmp_path / "rendered" / "synthetic_acceptance_full.html"
    css_output_path = tmp_path / "rendered" / "datasheet-common.css"
    evidence_path = tmp_path / "g1_acceptance_evidence.json"

    full_yaml_path.write_text(yaml.safe_dump(full_data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    full_bytes_before = full_yaml_path.read_bytes()
    assert instance_lint.lint_file(full_yaml_path, str(FULL_SCHEMA_PATH), "Dataset").valid

    derived_core = derive_core.derive_core(full_data, pair_schema)
    assert full_data == full_snapshot

    derive_core.write_core(full_yaml_path, core_yaml_path, pair_schema)
    assert full_yaml_path.read_bytes() == full_bytes_before

    core_report = instance_lint.lint_file(core_yaml_path, str(CORE_SCHEMA_PATH), "CoreDataset")
    assert core_report.valid, [e.to_dict() for e in core_report.errors]
    assert core_report.errors == []

    core_loaded = yaml.safe_load(core_yaml_path.read_text(encoding="utf-8"))
    assert core_loaded == derived_core
    core_snapshot = copy.deepcopy(core_loaded)

    pair_report = d4d_pair_consistency.validate_pair_data(full_data, core_loaded, pair_schema)
    assert pair_report.passed, [e.message for e in pair_report.errors]
    assert pair_report.errors == []
    assert full_data == full_snapshot
    assert core_loaded == core_snapshot

    assert core_loaded["creators"][0]["principal_investigator"] == full_data["creators"][0]["principal_investigator"]
    assert core_loaded["license_and_use_terms"]["contact_person"] == full_data["license_and_use_terms"]["contact_person"]
    assert core_loaded["data_governance"]["committee_contact"] == full_data["data_governance"]["committee_contact"]
    assert core_loaded["data_governance"]["committee_members"] == full_data["data_governance"]["committee_members"]
    assert core_loaded["license_and_use_terms"]["data_use_permission"] == full_data["license_and_use_terms"]["data_use_permission"]

    dist_by_id = {d["id"]: d for d in core_loaded["distributions"]}
    assert set(dist_by_id) == {
        "https://example.org/d4d/synthetic-acceptance#coll-processed",
        "https://example.org/d4d/synthetic-acceptance#file-table",
        "https://example.org/d4d/synthetic-acceptance#coll-raw",
        "https://example.org/d4d/synthetic-acceptance#file-waveform",
    }
    coll_dist = dist_by_id["https://example.org/d4d/synthetic-acceptance#coll-processed"]
    assert coll_dist["bytes"] == 2048
    assert coll_dist["conforms_to_standard"] == ["OMOP_CDM"]

    file_dist = dist_by_id["https://example.org/d4d/synthetic-acceptance#file-table"]
    assert file_dist["bytes"] == 2048
    assert file_dist["format"] == "TSV"
    assert file_dist["conforms_to"] == "https://ohdsi.github.io/CommonDataModel/"
    assert file_dist["conforms_to_standard"] == ["OMOP_CDM"]
    assert file_dist["sha256"] == "eb363fc0980025a34410bf2ff9b617a10996401f2bd24d2cef403ce2bda4fd44"

    for omitted_slot in ("file_collections", "participant_privacy", "splits", "variables"):
        assert omitted_slot in full_data
        assert omitted_slot not in core_loaded

    render_yaml_file(full_yaml_path, html_output_path)
    assert full_yaml_path.read_bytes() == full_bytes_before
    assert html_output_path.is_file() and html_output_path.stat().st_size > 0
    assert css_output_path.is_file() and css_output_path.stat().st_size > 0
    html_text = html_output_path.read_text(encoding="utf-8")
    for token in (
        "Synthetic Final Generation Acceptance",
        "Scalar dataset narrative for final-generation acceptance.",
        "Ada Lovelace",
        "0000-0002-1825-0097",
        "health_medical_biomedical_research",
        "no_commercial_use",
        "processed_data",
        "raw_data",
        "observations.tsv",
        "eb363fc0980025a34410bf2ff9b617a10996401f2bd24d2cef403ce2bda4fd44",
        "OMOP_CDM",
        "WFDB",
        "var_heart_rate_bpm",
        "technique_optical_ppg_v1",
        "split_stratified_80_20_detail_v1",
        "privacy_k_anonymity_k5_v1",
        "risk_low_expert_determination_v1",
    ):
        assert token in html_text, f"Missing expected value in HTML: {token!r}"

    evidence = {
        "code": {"repo_root": str(REPO_ROOT), "test_file": str(Path(__file__).resolve()), "modules": checked_modules},
        "schema": {
            "full_schema_path": str(FULL_SCHEMA_PATH),
            "full_schema_sha256": full_report.schema_sha256,
            "full_schema_version": str(pair_schema.full_view.schema.version),
            "core_schema_path": str(CORE_SCHEMA_PATH),
            "core_schema_sha256": core_report.schema_sha256,
            "core_schema_version": str(pair_schema.core_view.schema.version),
        },
        "interpreter": {"executable": sys.executable, "version": sys.version},
        "artifacts": {
            name: {"path": str(p), "bytes": p.stat().st_size, "sha256": _sha256_file(p)}
            for name, p in (
                ("full_yaml", full_yaml_path),
                ("core_yaml", core_yaml_path),
                ("rendered_html", html_output_path),
                ("rendered_css", css_output_path),
            )
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert evidence_path.is_file() and evidence_path.stat().st_size > 0


def test_negative_shape_mutations_fail_for_exact_field() -> None:
    """Verify four single-field mutations on copies of the valid fixture fail at the exact path."""
    base_full = build_positive_full_dataset()
    assert instance_lint.lint_instance(base_full, str(FULL_SCHEMA_PATH), "Dataset").valid

    cases: list[tuple[str, Any]] = [
        ("/description", lambda d: d.__setitem__("description", ["Paragraph 1", "Paragraph 2"])),
        ("/creators/0/principal_investigator", lambda d: d["creators"][0].__setitem__("principal_investigator", "Ada Lovelace")),
        ("/license_and_use_terms/data_use_permission", lambda d: d["license_and_use_terms"].__setitem__("data_use_permission", "health_medical_biomedical_research")),
        ("/file_collections/0/collection_type", lambda d: d["file_collections"][0].__setitem__("collection_type", ["processed_data", "raw_data"])),
    ]
    for expected_path, mutate in cases:
        candidate = copy.deepcopy(base_full)
        mutate(candidate)
        report = instance_lint.lint_instance(candidate, str(FULL_SCHEMA_PATH), "Dataset")
        assert not report.valid, f"Expected failure at {expected_path}"
        observed = {(err.code, err.path) for err in report.errors}
        assert observed == {("schema-violation", expected_path)}, (
            f"Expected only ('schema-violation', {expected_path!r}), got {report.errors}"
        )
