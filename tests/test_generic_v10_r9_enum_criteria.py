"""Tests for #5048: R9 criteria-defined enumerations in generic_v10 prompt and v2 rules."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from data_sheets_schema import receipts as rc
from data_sheets_schema.chunking import chunk_text, chunk_texts
from data_sheets_schema.datamodel.data_sheets_schema import (
    ComplianceStatusEnum,
    ConfidentialityLevelEnum,
    Dataset,
    ExportControlRegulatoryRestrictions,
)
from data_sheets_schema.shared_generation import ASSET_HASHES

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_V8 = REPO_ROOT / "src/download/prompts/d4d_generic_arm_prompt_v8.md"
PROMPT_V9 = REPO_ROOT / "src/download/prompts/d4d_generic_arm_prompt_v9.md"
PROMPT_V10 = REPO_ROOT / "src/download/prompts/d4d_generic_arm_prompt_v10.md"
RULES_V2 = REPO_ROOT / ".claude/commands/d4d-uniform-rules-v2.md"


class TestR9ConditionBoundaryAndParity:
    """Verify generic_v10 and v2 rules carry the R9 criteria-defined enum clarification
    while generic_v8 and generic_v9 prompt bytes remain bit-identical."""

    def test_v8_and_v9_prompt_digests_unchanged(self) -> None:
        v8_sha = hashlib.sha256(PROMPT_V8.read_bytes()).hexdigest()
        v9_sha = hashlib.sha256(PROMPT_V9.read_bytes()).hexdigest()
        assert v8_sha == "506af01bc9ab37ad8ba54cbb5d866bd4c0dc6c6a8aed6441117581a9406043fe"
        assert v9_sha == "a14c871598880ad490130be9ada71d67190488d3323b39d829441cbe7a67d051"
        assert "defined in the schema by observable" not in PROMPT_V8.read_text(encoding="utf-8")
        assert "defined in the schema by observable" not in PROMPT_V9.read_text(encoding="utf-8")

    def test_v10_and_uniform_rules_v2_state_r9_criteria_defined_enums(self) -> None:
        v10_text = " ".join(PROMPT_V10.read_text(encoding="utf-8").split())
        v2_text = " ".join(RULES_V2.read_text(encoding="utf-8").split())

        required_phrases = [
            "enumeration's permissible values are defined in the schema by observable criteria rather than by a bare category label, a passage that states the facts meeting a value's definition is a plain restatement of that value, and the coverage receipt for the slot is the passage stating those facts",
            "in `confidentiality_level` (ConfidentialityLevelEnum), a passage stating that the data are publicly available without access restrictions supports unrestricted",
            "a passage stating that access requires registration, a credentialed account, authorization or a data use agreement supports restricted",
            "a passage stating that access requires institutional review board, ethics or access-committee approval under strict controls supports confidential",
            "in `hipaa_compliant` (ComplianceStatusEnum), a passage stating that the dataset contains no human-subjects or protected health information supports not_applicable",
            "A label from an external classification scheme is recorded as prose where relevant and never mapped across schemes to an enumeration value unless the source also states the observable facts that meet the schema's definition.",
        ]
        for phrase in required_phrases:
            assert phrase in v10_text, f"Missing {phrase!r} in d4d_generic_arm_prompt_v10.md"
            assert phrase in v2_text, f"Missing {phrase!r} in d4d-uniform-rules-v2.md"

        assert (
            hashlib.sha256(RULES_V2.read_bytes()).hexdigest()
            == ASSET_HASHES[".claude/commands/d4d-uniform-rules-v2.md"]
        )


class TestR9CriteriaDefinedEnumFixtures:
    """Receipt and LinkML datamodel shape checks for R9 criteria-defined enumeration records.

    Note: ``receipts.check()`` verifies verbatim snippet presence and path coverage only;
    it does not evaluate semantic entailment of R9 criteria (which is enforced by the
    generation prompt and typed audit). These fixtures verify that a record populated under
    R9 (or omitting an unmapped external classification label) validates against the
    LinkML datamodel and passes coverage-receipt verification when receipted by the
    fact-stating passage.
    """

    def test_positive_fixture_access_criteria_populates_enum_with_fact_receipt(self) -> None:
        """A source passage stating observable access facts (registration + DUA) and
        non-human cell-line scope supports confidentiality_level='restricted' and
        hipaa_compliant='not_applicable' even without those literal enum tokens."""
        bundle = (
            "=" * 80 + "\nCONCATENATED DOCUMENT\n" + "=" * 80 + "\n\n"
            "FILE: access_policy.md\nPATH: docs/access_policy.md\nSIZE: 312 bytes\n"
            + "-" * 80 + "\n"
            "Dataset Overview: The Bridge2AI Cell Microscopy Benchmark.\n"
            "Access to the dataset requires user registration, a credentialed account, "
            "and execution of a Data Use Agreement (DUA).\n"
            "The dataset contains only cell-line microscopy images and no human subjects "
            "or protected health information.\n"
        )
        # Ensure literal enum tokens do not appear in the source text
        assert "restricted" not in bundle.lower()
        assert "not_applicable" not in bundle.lower()
        assert "not applicable" not in bundle.lower()

        ds = Dataset(
            id="https://example.org/cell-microscopy",
            name="cell-microscopy",
            title="The Bridge2AI Cell Microscopy Benchmark",
            regulatory_restrictions=ExportControlRegulatoryRestrictions(
                id="https://example.org/cell-microscopy#reg-restrictions",
                confidentiality_level="restricted",
                hipaa_compliant="not_applicable",
            ),
        )
        assert ds.regulatory_restrictions.confidentiality_level.code == ConfidentialityLevelEnum.restricted
        assert str(ds.regulatory_restrictions.confidentiality_level) == "restricted"
        assert ds.regulatory_restrictions.hipaa_compliant.code == ComplianceStatusEnum.not_applicable
        assert str(ds.regulatory_restrictions.hipaa_compliant) == "not_applicable"

        record = {
            "id": "https://example.org/cell-microscopy",
            "name": "cell-microscopy",
            "title": "The Bridge2AI Cell Microscopy Benchmark",
            "regulatory_restrictions": {
                "id": "https://example.org/cell-microscopy#reg-restrictions",
                "confidentiality_level": "restricted",
                "hipaa_compliant": "not_applicable",
            },
        }
        chunks = chunk_text(bundle)
        md5 = hashlib.md5(bundle.encode()).hexdigest()
        manifest = {"bundle_md5": md5, "chunks": chunks}
        texts = dict(zip([c["id"] for c in chunks], chunk_texts(bundle, chunks)))

        receipt = {
            "bundle_md5": md5,
            "chunks": [
                {"id": "c001", "status": "nothing_relevant", "reason": "bundle header"},
                {
                    "id": "c002",
                    "status": "extracted",
                    "extracted": [
                        {"slot": "id", "snippet": "The Bridge2AI Cell Microscopy Benchmark"},
                        {"slot": "name", "snippet": "Cell Microscopy"},
                        {"slot": "title", "snippet": "The Bridge2AI Cell Microscopy Benchmark"},
                        {
                            "slot": "regulatory_restrictions.confidentiality_level",
                            "snippet": (
                                "Access to the dataset requires user registration, a credentialed "
                                "account, and execution of a Data Use Agreement (DUA)."
                            ),
                        },
                        {
                            "slot": "regulatory_restrictions.hipaa_compliant",
                            "snippet": (
                                "contains only cell-line microscopy images and no human subjects "
                                "or protected health information"
                            ),
                        },
                    ],
                },
            ],
        }

        block = rc.check(receipt, manifest, texts, record, md5)
        assert block["findings"] == []
        assert block["slots"]["without_receipt"] == []
        assert block["snippets"]["verified"] == block["snippets"]["total"] == 5

    def test_negative_fixture_external_classification_label_without_access_facts(self) -> None:
        """A source passage stating only an external scheme label ('HL7:2N', 'Level 3')
        without observable access facts must leave confidentiality_level omitted and
        record the external label in prose."""
        bundle = (
            "=" * 80 + "\nCONCATENATED DOCUMENT\n" + "=" * 80 + "\n\n"
            "FILE: governance.md\nPATH: docs/governance.md\nSIZE: 180 bytes\n"
            + "-" * 80 + "\n"
            "Dataset Overview: The Synthetic Waveform Archive.\n"
            "External security classification tag assigned by upstream catalog: "
            "HL7:2N (Level 3 tier).\n"
        )

        # Unmapped external labels are not valid ConfidentialityLevelEnum values
        with pytest.raises(ValueError):
            ExportControlRegulatoryRestrictions(
                id="https://example.org/waveform#reg",
                confidentiality_level="HL7:2N",
            )

        # Under R9, confidentiality_level stays None and the external label is kept in prose
        ds = Dataset(
            id="https://example.org/waveform",
            name="waveform",
            title="The Synthetic Waveform Archive",
            regulatory_restrictions=ExportControlRegulatoryRestrictions(
                id="https://example.org/waveform#reg",
                confidentiality_level=None,
                regulatory_restrictions=[
                    "External security classification tag assigned by upstream catalog: HL7:2N (Level 3 tier)."
                ],
            ),
        )
        assert ds.regulatory_restrictions.confidentiality_level is None
        assert ds.regulatory_restrictions.regulatory_restrictions == [
            "External security classification tag assigned by upstream catalog: HL7:2N (Level 3 tier)."
        ]

        record = {
            "id": "https://example.org/waveform",
            "name": "waveform",
            "title": "The Synthetic Waveform Archive",
            "regulatory_restrictions": {
                "id": "https://example.org/waveform#reg",
                "regulatory_restrictions": [
                    "External security classification tag assigned by upstream catalog: HL7:2N (Level 3 tier)."
                ],
            },
        }
        chunks = chunk_text(bundle)
        md5 = hashlib.md5(bundle.encode()).hexdigest()
        manifest = {"bundle_md5": md5, "chunks": chunks}
        texts = dict(zip([c["id"] for c in chunks], chunk_texts(bundle, chunks)))

        receipt = {
            "bundle_md5": md5,
            "chunks": [
                {"id": "c001", "status": "nothing_relevant", "reason": "bundle header"},
                {
                    "id": "c002",
                    "status": "extracted",
                    "extracted": [
                        {"slot": "id", "snippet": "The Synthetic Waveform Archive"},
                        {"slot": "name", "snippet": "Waveform Archive"},
                        {"slot": "title", "snippet": "The Synthetic Waveform Archive"},
                        {
                            "slot": "regulatory_restrictions.regulatory_restrictions",
                            "snippet": (
                                "External security classification tag assigned by upstream catalog: "
                                "HL7:2N (Level 3 tier)."
                            ),
                        },
                    ],
                },
            ],
        }

        block = rc.check(receipt, manifest, texts, record, md5)
        assert block["findings"] == []
        assert block["slots"]["without_receipt"] == []
        assert block["snippets"]["verified"] == block["snippets"]["total"] == 4
