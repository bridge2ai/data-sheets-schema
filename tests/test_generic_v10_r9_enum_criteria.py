"""Tests for #5048 and D-E (#5097–#5099, #5102, #5103): R9 criteria-defined enumerations in generic_v10 prompt and v2 rules.

Note on #5099: #5099's audit of the other 16 enumerations is moot, because the R9 clause names a closed list of two (`confidentiality_level` and `hipaa_compliant`).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

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


# Text-unit assertions (each normalised for whitespace) required by D-E (#5097–#5099, #5102).
R9_TEXT_UNITS: dict[str, str] = {
    "opening_closed_two": (
        "Two enumeration slots, `confidentiality_level` and `hipaa_compliant`, are also "
        "populated from a passage that states the facts below: such a passage is a plain "
        "restatement of the value those facts support, and it is the slot's coverage receipt."
    ),
    "confidentiality_level_intro": (
        "`confidentiality_level` (ConfidentialityLevelEnum) records who can obtain this "
        "dataset's data, and how."
    ),
    "criterion_unrestricted": (
        "A passage stating that the data are publicly available to download, that anyone can "
        "download them, or that downloading them needs no account, registration, approval or "
        "signed agreement supports `unrestricted`, unless a passage states a condition below "
        "for the same data."
    ),
    "criterion_public_licence_carveout": (
        "A public license such as Creative Commons, a download page asking the user to confirm "
        "that license, a request to cite, or a form asking who is downloading is not such a "
        "condition."
    ),
    "criterion_restricted": (
        "A passage stating that access requires registration or an account, verified identity "
        "or credentials, approval of the request, sign-off by the requester's institution, or "
        "a data use agreement or dataset-specific license that the requester or their "
        "institution signs or accepts supports `restricted`."
    ),
    "criterion_confidential": (
        "A passage stating that each request is reviewed before access is granted, by a data "
        "access committee or office or by an institutional review board or ethics committee "
        "approving the requester's own use, supports `confidential`; a study's own ethics or "
        "IRB approval of collecting its data is not such review."
    ),
    "precedence_sentence": (
        "A route that requires such review is `confidential` whatever else it requires; one "
        "that requires only conditions supporting `restricted` is `restricted`."
    ),
    "tier_name_sentence": (
        'A gated tier\'s name, such as "registered access", "controlled access" or '
        '"credentialed access", states no conditions: it is recorded as prose and is never '
        "the receipt, and where no passage states the conditions of the tier the slot would "
        "record, the slot stays empty."
    ),
    "tier_sentence_least_restrictive": (
        "Where the documents describe several access tiers for this dataset, the slot records "
        "the least restrictive tier through which any of this dataset's own data can be "
        "obtained; a tier offering only metadata, documentation, code, a sample or a synthetic "
        "copy does not count."
    ),
    "tier_sentence_access_review_process": (
        "Each tier, with its conditions and the data it covers, is described in "
        "`data_governance.access_review_process`."
    ),
    "sensitivity_sentence": (
        "A statement of how sensitive the data are describes the data, not how access works, "
        "and does not decide `confidentiality_level`."
    ),
    "hipaa_clause_not_applicable": (
        "In `hipaa_compliant` (ComplianceStatusEnum), a passage stating that the dataset holds "
        "no data about human participants — for example, only cell lines, model organisms or "
        "simulated data — supports `not_applicable`."
    ),
    "hipaa_clauses_compliant_and_neither": (
        "A passage stating that the data were de-identified under HIPAA, whether it names "
        "HIPAA or its Safe Harbor or Expert Determination method, supports `compliant`; a "
        "passage stating only that the data contain no protected health information, or that "
        "they were de-identified without naming HIPAA or either method, supports neither value."
    ),
    "scope_sentence": (
        "No other enumeration slot is read this way: `data_type`, `collection_type` and every "
        "other enumeration slot remain under the rest of this rule."
    ),
    "foreign_label_sentence": (
        'A label from another classification scheme — an institution\'s data-security level '
        'such as "Level 3", an HL7 confidentiality code such as "HL7:2N" — is recorded as '
        "prose where relevant and is never mapped to an enumeration value or used as the "
        "receipt for one."
    ),
}

ABSENT_5093_PHRASES: tuple[str, ...] = (
    "contains no human-subjects or protected health information supports not_applicable",
    "publicly available without access restrictions supports unrestricted",
)


def _norm(text: str) -> str:
    return " ".join(text.split())


def check_r9_text_units(raw_text: str) -> list[str]:
    """Return a list of missing or forbidden unit names in ``raw_text``."""
    norm_text = _norm(raw_text)
    failures: list[str] = []
    for unit_name, expected in R9_TEXT_UNITS.items():
        if _norm(expected) not in norm_text:
            failures.append(f"missing:{unit_name}")
    for forbidden in ABSENT_5093_PHRASES:
        if _norm(forbidden) in norm_text:
            failures.append(f"forbidden:{forbidden}")
    return failures


class TestR9ConditionBoundaryAndParity:
    """Verify generic_v10 and v2 rules carry the D-E corrected R9 criteria-defined
    enum specification while generic_v8 and generic_v9 prompt bytes remain bit-identical."""

    def test_v8_and_v9_prompt_digests_unchanged(self) -> None:
        v8_sha = hashlib.sha256(PROMPT_V8.read_bytes()).hexdigest()
        v9_sha = hashlib.sha256(PROMPT_V9.read_bytes()).hexdigest()
        assert v8_sha == "506af01bc9ab37ad8ba54cbb5d866bd4c0dc6c6a8aed6441117581a9406043fe"
        assert v9_sha == "a14c871598880ad490130be9ada71d67190488d3323b39d829441cbe7a67d051"
        assert "Two enumeration slots" not in PROMPT_V8.read_text(encoding="utf-8")
        assert "Two enumeration slots" not in PROMPT_V9.read_text(encoding="utf-8")

    def test_v10_and_uniform_rules_v2_text_units_and_absences(self) -> None:
        v10_raw = PROMPT_V10.read_text(encoding="utf-8")
        v2_raw = RULES_V2.read_text(encoding="utf-8")

        assert check_r9_text_units(v10_raw) == []
        assert check_r9_text_units(v2_raw) == []

        for phrase in ABSENT_5093_PHRASES:
            assert _norm(phrase) not in _norm(v10_raw)
            assert _norm(phrase) not in _norm(v2_raw)

        # #5103 header notes
        assert "(#5048, #5097–#5099, #5102, 2026-10-23)" in _norm(v10_raw)
        assert "(updated 2026-10-23 for R9 criteria-defined enumerations: #5048, #5097–#5099, #5102)" in _norm(v2_raw)
        assert "Existing v9 text" not in v10_raw
        assert "immutable successor" not in v2_raw

        # #5099's audit of the other 16 enumerations is moot because the clause names a closed list of two.
        assert "Two enumeration slots, `confidentiality_level` and `hipaa_compliant`" in _norm(v10_raw)
        assert "No other enumeration slot is read this way" in _norm(v10_raw)

        # D38: American English "license" in the R9 span (no British "licence" in v10 body)
        v10_body = v10_raw.split("## Prompt body", 1)[1]
        assert "licence" not in v10_body.lower()
        assert "  those.\n" not in v10_raw

        assert (
            hashlib.sha256(PROMPT_V10.read_bytes()).hexdigest()
            == ASSET_HASHES["src/download/prompts/d4d_generic_arm_prompt_v10.md"]
        )
        assert (
            hashlib.sha256(RULES_V2.read_bytes()).hexdigest()
            == ASSET_HASHES[".claude/commands/d4d-uniform-rules-v2.md"]
        )


@pytest.mark.parametrize(
    "prompt_path",
    [PROMPT_V10, RULES_V2],
    ids=["generic_v10", "uniform_rules_v2"],
)
class TestR9MutationMetaTests:
    """Mutation meta-tests: each of the 5 specified mutations on the R9 text must fail
    on both d4d_generic_arm_prompt_v10.md and d4d-uniform-rules-v2.md without referencing
    the target unit string from R9_TEXT_UNITS."""

    @staticmethod
    def _base_text(prompt_path: Path) -> str:
        return _norm(prompt_path.read_text(encoding="utf-8"))

    def test_mutation_swap_restricted_and_confidential_fails(self, prompt_path: Path) -> None:
        text = self._base_text(prompt_path)
        placeholder = "__SWAP_TEMP_TOKEN__"
        mutated = (
            text.replace("`restricted`", placeholder)
            .replace("`confidential`", "`restricted`")
            .replace(placeholder, "`confidential`")
        )
        assert check_r9_text_units(mutated) != []

    def test_mutation_swap_unrestricted_and_restricted_fails(self, prompt_path: Path) -> None:
        text = self._base_text(prompt_path)
        placeholder = "__SWAP_TEMP_TOKEN__"
        mutated = (
            text.replace("`unrestricted`", placeholder)
            .replace("`restricted`", "`unrestricted`")
            .replace(placeholder, "`restricted`")
        )
        assert check_r9_text_units(mutated) != []

    def test_mutation_replace_least_with_most_fails(self, prompt_path: Path) -> None:
        text = self._base_text(prompt_path)
        mutated = text.replace(" least ", " most ")
        assert "missing:tier_sentence_least_restrictive" in check_r9_text_units(mutated)

    def test_mutation_swap_compliant_and_not_applicable_fails(self, prompt_path: Path) -> None:
        text = self._base_text(prompt_path)
        placeholder = "__SWAP_TEMP_TOKEN__"
        mutated = (
            text.replace("`compliant`", placeholder)
            .replace("`not_applicable`", "`compliant`")
            .replace(placeholder, "`not_applicable`")
        )
        assert check_r9_text_units(mutated) != []

    def test_mutation_delete_scope_sentence_fails(self, prompt_path: Path) -> None:
        text = self._base_text(prompt_path)
        before_anchor = "supports neither value. "
        after_anchor = " A label from another classification scheme"
        start = text.index(before_anchor) + len(before_anchor)
        end = text.index(after_anchor, start)
        mutated = text[:start] + text[end:]
        assert "missing:scope_sentence" in check_r9_text_units(mutated)


# Expectation fixtures for the canary and review pack (labelled as expectations for the
# canary and review pack because they do not read the prompt at runtime; nothing in
# canary or review-pack code consumes this table yet — the test below checks only that
# each expected value is accepted by the LinkML datamodel).
CANARY_AND_REVIEW_PACK_EXPECTATION_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "id": "cc_guestbook_dataverse",
        "passage": "Public Dataverse files with a CC confirmation and a guestbook",
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "unrestricted",
    },
    {
        "id": "collection_irb_plus_registration_dua",
        "passage": "The study's IRB approved data collection, and access needs registration plus a DUA",
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "restricted",
    },
    {
        "id": "controlled_access_bare_name_only",
        "passage": '"Controlled access" only',
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": None,
    },
    {
        "id": "controlled_access_plus_registration_and_licence",
        "passage": '"Controlled access" plus a registration-and-licence passage',
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "restricted",
        "receipt_note": "receipt on the conditions",
    },
    {
        "id": "login_licence_subset_tier_inside_committee_superset",
        "passage": "A login-and-licence subset tier, inside a superset tier that needs committee review",
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "restricted",
    },
    {
        "id": "open_sample_with_full_release_needing_registration",
        "passage": "An open sample, with the full release needing registration",
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "restricted",
    },
    {
        "id": "open_companion_dataset_with_this_one_credentialed_plus_dua",
        "passage": "A companion dataset described as open, with this one credentialed plus a DUA",
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "restricted",
    },
    {
        "id": "institutional_signoff_plus_dua_no_committee",
        "passage": "Institutional sign-off plus a DUA, with no committee",
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "restricted",
    },
    {
        "id": "no_phi_plus_hipaa_safe_harbor",
        "passage": '"No PHI" plus HIPAA Safe Harbor',
        "slot": "regulatory_restrictions.hipaa_compliant",
        "expected": "compliant",
    },
    {
        "id": "deidentified_with_no_hipaa",
        "passage": '"De-identified", with no HIPAA',
        "slot": "regulatory_restrictions.hipaa_compliant",
        "expected": None,
    },
    {
        "id": "apply_hipaa_deidentification_rules_yes",
        "passage": '"Apply the HIPAA de-identification rules? Yes"',
        "slot": "regulatory_restrictions.hipaa_compliant",
        "expected": "compliant",
    },
    {
        "id": "participant_app_no_login_required",
        "passage": 'A participant app with "no login required"',
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": "unchanged",
        "effect": "no effect on confidentiality_level",
    },
    {
        "id": "foreign_label_level3_or_hl7_2n_only",
        "passage": 'Only "Level 3" or "HL7:2N"',
        "slot": "regulatory_restrictions.confidentiality_level",
        "expected": None,
    },
    {
        "id": "whole_numbers_variable_passage",
        "passage": "A passage listing whole numbers for a variable",
        "slot": "data_type",
        "expected": None,
    },
)


class TestR9CanaryAndReviewPackExpectationFixtures:
    """Expectation fixtures for the canary and review pack (they do not read the prompt;
    nothing in canary or review-pack code consumes CANARY_AND_REVIEW_PACK_EXPECTATION_FIXTURES
    yet).

    Also verifies LinkML datamodel validation and ``receipts.check()`` coverage-receipt
    verification for records populated under the D-E R9 rules.
    """

    @pytest.mark.parametrize(
        "fixture",
        CANARY_AND_REVIEW_PACK_EXPECTATION_FIXTURES,
        ids=[f["id"] for f in CANARY_AND_REVIEW_PACK_EXPECTATION_FIXTURES],
    )
    def test_canary_and_review_pack_expectation_fixture_schema_validity(
        self, fixture: dict[str, Any]
    ) -> None:
        slot = fixture["slot"]
        expected = fixture["expected"]
        if slot == "regulatory_restrictions.confidentiality_level":
            if expected == "unchanged":
                # Passage about participant app login has no effect on dataset-release
                # confidentiality_level: whatever value was established by release-access
                # facts (including None) remains unchanged.
                for prior in (None, "unrestricted", "restricted", "confidential"):
                    reg = ExportControlRegulatoryRestrictions(
                        id="https://example.org/ds#reg",
                        confidentiality_level=prior,
                    )
                    if prior is None:
                        assert reg.confidentiality_level is None
                    else:
                        assert reg.confidentiality_level.code == ConfidentialityLevelEnum[prior]
                return
            reg = ExportControlRegulatoryRestrictions(
                id="https://example.org/ds#reg",
                confidentiality_level=expected,
            )
            if expected is None:
                assert reg.confidentiality_level is None
            else:
                assert str(reg.confidentiality_level) == expected
                assert reg.confidentiality_level.code == ConfidentialityLevelEnum[expected]
        elif slot == "regulatory_restrictions.hipaa_compliant":
            reg = ExportControlRegulatoryRestrictions(
                id="https://example.org/ds#reg",
                hipaa_compliant=expected,
            )
            if expected is None:
                assert reg.hipaa_compliant is None
            else:
                assert str(reg.hipaa_compliant) == expected
                assert reg.hipaa_compliant.code == ComplianceStatusEnum[expected]
        elif slot == "data_type":
            assert expected is None

    def test_all_14_expectation_fixtures_present(self) -> None:
        assert len(CANARY_AND_REVIEW_PACK_EXPECTATION_FIXTURES) == 14

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
            "The dataset contains only cell-line microscopy images and collects no health "
            "information about human individuals.\n"
        )
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
        assert ds.regulatory_restrictions.hipaa_compliant.code == ComplianceStatusEnum.not_applicable

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
                                "contains only cell-line microscopy images and collects no health "
                                "information about human individuals"
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
        """Datamodel check: external scheme tokens ('HL7:2N', 'Level 3') are not members
        of ConfidentialityLevelEnum and are rejected by ExportControlRegulatoryRestrictions."""
        with pytest.raises(ValueError):
            ExportControlRegulatoryRestrictions(
                id="https://example.org/waveform#reg",
                confidentiality_level="HL7:2N",
            )
