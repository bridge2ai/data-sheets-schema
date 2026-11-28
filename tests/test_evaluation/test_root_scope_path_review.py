"""PR 6366 reviewer path regressions, issues 6367-6370, 2026-11-25.

Ports the synthetic cases in review_pr6366_paths_20261125.py and its followup
and metadata helpers. Inputs are synthetic records and independent scope files;
outputs stay in pytest's external basetemp. Publication controls use only the
committed fake executable and the real exact-file validator, never a live CLI.
"""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from data_sheets_schema.evaluation.validate import validate_outputs
from data_sheets_schema.root_scope import assert_portable_output
from data_sheets_schema.semantic_evidence import check_evidence
from data_sheets_schema.semantic_evidence_authority import AUTHORITY_PATH, verify_authority
from tests.test_evaluation.test_root_scope_instrument import root_fixture
from tests.test_evaluation.test_semantic_context_scope import ROOT, record
from tests.test_codex_root_scope_scorer import items, root_scenario, scorer, write_case


UNC = r"\\fileserver\profiles\synthetic-owner\private\record.yaml"
CUSTOM_ABSOLUTE = "/custom-home/synthetic-owner/record.yaml"
WEB_URL = "https://example.org/home/record.yaml"
PROVENANCE_SECTIONS = ("metadata", "evaluation_metadata", "evaluation_model", "scorer_instrument", "model")
POINTER_VALUE = "Synthetic extension value"
CONSIDERED_LOCAL_PATHS = ("/Users/synthetic-owner/private/record.yaml", "/" + UNC)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def persist(result, output):
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def bind_document(result, source, declaration, document):
    source.write_text(yaml.safe_dump(document))
    scope = json.loads(declaration.read_bytes())
    scope["input_sha256"] = sha(source.read_bytes())
    declaration.write_text(json.dumps(scope, indent=2, sort_keys=True) + "\n")
    result["metadata"].update(input_sha256=sha(source.read_bytes()),
                              scope_context_sha256=sha(declaration.read_bytes()))


def bind_home_evidence(result, source, declaration, pointer):
    document = yaml.safe_load(source.read_bytes())
    document["home"] = {"title": POINTER_VALUE}
    bind_document(result, source, declaration, document)
    next(items(result))["unit_scores"][0]["cited"] = [{"path": pointer, "quote": POINTER_VALUE}]
    report = check_evidence(result, document, result["rubric"], unit_map={"#": document})
    assert report.passed, report.errors
    return document


def test_exact_validator_accepts_relative_artifacts_with_home_segments(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        result, source, declaration, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        result["method"] = "home"
        result["d4d_file"] = "data/d4d_concatenated/home/rep1/Toy_d4d.yaml"
        result["evaluation_model"] = {"session_logs": [{
            "path": "codex-home/sessions/home/rollout.jsonl", "sha256": "a" * 64,
        }]}
        result["metadata"]["source_path"] = "artifacts/home/result.json"
        persist(result, output)
        original = (source.read_bytes(), declaration.read_bytes(), output.read_bytes())
        assert validate_outputs([output], **kwargs) == 0
        assert (source.read_bytes(), declaration.read_bytes(), output.read_bytes()) == original


def test_exact_validator_treats_slash_and_dotted_home_evidence_equally(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        records = []
        for name, pointer in (("pointer", "/home/title"), ("dotted", "home.title")):
            result, source, declaration, output, kwargs = root_fixture(tmp_path / (rubric + "-" + name), rubric)
            document = bind_home_evidence(result, source, declaration, pointer)
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 0
            records.append((document, result["overall_score"],
                            next(items(result))["unit_scores"][0]["cited"][0]["quote"]))
        assert records[0] == records[1]


def test_exact_validator_refuses_unc_provenance_and_prose_but_accepts_urls(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        for section in ("metadata", "model", "prose"):
            result, _, _, output, kwargs = root_fixture(tmp_path / (rubric + "-" + section), rubric)
            if section == "prose":
                result["semantic_analysis"]["semantic_insights"] = ["Documentation " + WEB_URL]
            else:
                result.setdefault(section, {})["source_path"] = WEB_URL
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 0
            if section == "prose":
                result["semantic_analysis"]["semantic_insights"] = ["Source file: " + UNC]
            else:
                result[section]["source_path"] = UNC
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 1


def test_exact_validator_refuses_the_same_custom_path_in_every_metadata_section(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        for section in PROVENANCE_SECTIONS:
            result, _, _, output, kwargs = root_fixture(tmp_path / (rubric + "-" + section), rubric)
            result.setdefault(section, {})["source_path"] = WEB_URL
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 0
            result[section]["source_path"] = CUSTOM_ABSOLUTE
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 1


def test_exact_validator_keeps_all_structured_evidence_reader_contracts(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        result, source, declaration, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        document = yaml.safe_load(source.read_bytes())
        document["home"] = {"title": POINTER_VALUE, "values": ["first", "second"]}
        bind_document(result, source, declaration, document)
        row = next(items(result))["unit_scores"][0]
        row.update(cited=[{"path": "/home/title", "quote": POINTER_VALUE}],
                   absent=[{"path": "/errata"}], counts=[{"path": "/home/values", "claimed": 2}],
                   considered=["/home/title"])
        persist(result, output)
        assert validate_outputs([output], **kwargs) == 0
        original = json.dumps(row)
        for kind in ("cited", "absent", "counts", "considered"):
            row.clear()
            row.update(json.loads(original))
            if kind == "considered":
                row[kind] = ["/home//title"]
            else:
                row[kind][0]["path"] = "/home//title"
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 1


def test_exact_validator_allows_literal_backslashes_only_in_real_pointer_tokens(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        result, source, declaration, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        document = yaml.safe_load(source.read_bytes())
        key = r"\\fileserver\share"
        document[key] = POINTER_VALUE
        bind_document(result, source, declaration, document)
        next(items(result))["unit_scores"][0]["cited"] = [{"path": "/" + key, "quote": POINTER_VALUE}]
        persist(result, output)
        assert validate_outputs([output], **kwargs) == 0
        next(items(result))["unit_scores"][0]["cited"][0]["path"] = "/missing\\key"
        persist(result, output)
        assert validate_outputs([output], **kwargs) == 1


def test_exact_validator_never_exempts_quotes_or_metadata_pointer_lookalikes(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        for location in ("quote", "metadata"):
            result, source, declaration, output, kwargs = root_fixture(tmp_path / (rubric + "-" + location), rubric)
            local_path = "/home/private/file"
            if location == "quote":
                document = yaml.safe_load(source.read_bytes())
                document["home"] = {"title": local_path}
                bind_document(result, source, declaration, document)
                next(items(result))["unit_scores"][0]["cited"] = [{"path": "/home/title", "quote": local_path}]
                assert check_evidence(result, document, rubric, unit_map={"#": document}).passed
            else:
                result["metadata"]["cited"] = [{"path": local_path}]
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 1


def test_exact_validator_never_exempts_the_inactive_rubric_family(tmp_path):
    for rubric, groups, entries in (("rubric10", "categories", "questions"),
                                    ("rubric20", "elements", "sub_elements")):
        result, _, _, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        result[groups] = [{entries: [{"unit_scores": [{"cited": [{"path": WEB_URL}]}]}]}]
        persist(result, output)
        assert validate_outputs([output], **kwargs) == 0
        result[groups][0][entries][0]["unit_scores"][0]["cited"][0]["path"] = "/home/private/file"
        persist(result, output)
        assert validate_outputs([output], **kwargs) == 1


def bind_legitimate_considered(result, source, declaration):
    document = yaml.safe_load(source.read_bytes())
    document["home"] = {"title": POINTER_VALUE, "empty": [], "none": None}
    document[UNC] = "This is a literal document key, not a filesystem reference."
    bind_document(result, source, declaration, document)
    assert "errata" in verify_authority(result["metadata"])
    assert "errata" not in document
    paths = ["/home/title", "/home/empty", "/home/none", "/" + UNC, "/errata",
             "nonexistent_annotation"]
    next(items(result))["unit_scores"][0]["considered"] = paths
    assert check_evidence(result, document, result["rubric"], unit_map={"#": document}).passed
    return paths


def test_exact_validator_refuses_unestablished_considered_local_paths_in_both_rubrics(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        for index, path in enumerate(CONSIDERED_LOCAL_PATHS):
            result, source, _, output, kwargs = root_fixture(tmp_path / (rubric + "-" + str(index)), rubric)
            document = yaml.safe_load(source.read_bytes())
            names = verify_authority(result["metadata"])
            first_token = path[1:].split("/")[0]
            assert first_token not in document and first_token not in names
            next(items(result))["unit_scores"][0]["considered"] = [path]
            # Grammar alone accepts these; strict v6 acceptance must not publish them.
            assert check_evidence(result, document, rubric, unit_map={"#": document}).passed
            persist(result, output)
            assert validate_outputs([output], **kwargs) == 1


def test_exact_validator_preserves_resolving_and_authorized_missing_considered_paths(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        result, source, declaration, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        bind_legitimate_considered(result, source, declaration)
        persist(result, output)
        original = (source.read_bytes(), declaration.read_bytes(), output.read_bytes())
        assert validate_outputs([output], **kwargs) == 0
        assert (source.read_bytes(), declaration.read_bytes(), output.read_bytes()) == original


def test_legacy_exact_validator_retains_considered_path_grammar_semantics(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        directory = tmp_path / rubric
        directory.mkdir()
        result, source = record(directory, rubric)
        next(items(result))["unit_scores"][0]["considered"] = list(CONSIDERED_LOCAL_PATHS)
        output = directory / "evaluation.json"
        persist(result, output)
        original = source.read_bytes(), output.read_bytes()
        assert result["version"] == "3.0"
        assert validate_outputs(
            [output], input_path=source, definition_path=ROOT / f".claude/agents/d4d-{rubric}-semantic.md",
            context_path=source.with_name("caller-context.yaml"), semantic_version="3.0",
        ) == 0
        assert (source.read_bytes(), output.read_bytes()) == original


def test_considered_exemption_refuses_poisoned_authority_even_with_matching_metadata(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        result, source, _, _, _ = root_fixture(tmp_path / rubric, rubric)
        local_path = CONSIDERED_LOCAL_PATHS[0]
        next(items(result))["unit_scores"][0]["considered"] = [local_path]
        authority = json.loads((ROOT / AUTHORITY_PATH).read_bytes())
        authority["names"] = sorted(set(authority["names"]) | set(local_path[1:].split("/")))
        poisoned = (json.dumps(authority, sort_keys=True) + "\n").encode()
        result["metadata"]["evidence_authority_sha256"] = sha(poisoned)
        requested = []

        def resource_reader(path):
            assert path == AUTHORITY_PATH
            requested.append(path)
            return poisoned

        names = verify_authority(result["metadata"], resource_reader=resource_reader)
        assert set(local_path[1:].split("/")) <= names
        for document in (None, yaml.safe_load(source.read_bytes())):
            with pytest.raises(ValueError, match="frozen field-name authority"):
                assert_portable_output(result, document=document, resource_reader=resource_reader)
        assert requested == [AUTHORITY_PATH] * 3


def test_v6_schema_only_first_pass_still_requires_trusted_input_and_scope(tmp_path, capsys):
    for rubric in ("rubric10", "rubric20"):
        result, source, declaration, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        document = yaml.safe_load(source.read_bytes())
        document["home"] = {"title": POINTER_VALUE}
        bind_document(result, source, declaration, document)
        next(items(result))["unit_scores"][0]["considered"] = ["/home/title"]
        with pytest.raises(ValueError, match="local absolute"):
            assert_portable_output(result)
        assert_portable_output(result, document=document)
        persist(result, output)
        assert validate_outputs([output], **kwargs) == 0
        capsys.readouterr()
        assert validate_outputs([output], **{**kwargs, "input_path": None}) == 1
        assert "requires --input" in capsys.readouterr().out
        assert validate_outputs([output], **{**kwargs, "scope_context_path": None}) == 1
        assert "requires --scope-context" in capsys.readouterr().out
        next(items(result))["unit_scores"][0]["considered"] = [{"path": "/home/title"}]
        persist(result, output)
        with patch("data_sheets_schema.evaluation_context.load_document",
                   side_effect=AssertionError("malformed schema reached trusted input loading")):
            assert validate_outputs([output], **kwargs) == 1
        assert "not of type 'string'" in capsys.readouterr().out


def assert_fake_cleanup(args, plan, original_auth, original_record):
    run = Path(plan["run_directory"])
    assert not (run / "codex-home/auth.json").exists()
    assert args.auth_file.read_bytes() == original_auth
    assert Path(args.record).read_bytes() == original_record
    return json.loads((run / "receipt.json").read_bytes())


def test_fake_publication_accepts_method_home_and_both_evidence_spellings(tmp_path):
    for name, pointer in (("pointer", "/home/title"), ("dotted", "home.title")):
        args, tree, tools, evaluation = root_scenario(tmp_path / name)
        old = Path(args.record)
        relocated = tree / "data/d4d_concatenated/home" / args.label / old.name
        relocated.parent.mkdir(parents=True)
        old.rename(relocated)
        args.record = relocated
        args.method_directory = "home"
        evaluation["method"] = "home"
        evaluation["d4d_file"] = relocated.relative_to(tree).as_posix()
        bind_home_evidence(evaluation, relocated, args.scope_context, pointer)
        write_case(tools, evaluation)
        original_auth, original_record = args.auth_file.read_bytes(), relocated.read_bytes()
        plan = scorer.build_plan(args)
        scorer.execute(plan, args)
        output = Path(plan["output"])
        published = output.read_bytes()
        assert published and published == (tools / "validated-snapshot.json").read_bytes()
        result = json.loads(published)
        assert result["method"] == "home"
        assert result["d4d_file"] == evaluation["d4d_file"]
        assert next(items(result))["unit_scores"][0]["cited"] == [{"path": pointer, "quote": POINTER_VALUE}]
        assert result["overall_score"] == evaluation["overall_score"]
        checked = json.loads((tools / "real-validator-result.json").read_bytes())
        assert checked["returncode"] == 0
        assert checked["accepted_snapshot_sha256"] == sha(published)
        receipt = assert_fake_cleanup(args, plan, original_auth, original_record)
        assert receipt["status"] == "VALIDATED_AND_PUBLISHED"


def test_fake_publication_refuses_unc_in_metadata_model_and_prose(tmp_path):
    for section in ("metadata", "model", "prose"):
        args, _, tools, evaluation = root_scenario(tmp_path / section)
        if section == "prose":
            evaluation["semantic_analysis"]["semantic_insights"] = ["Source file: " + UNC]
        else:
            evaluation.setdefault(section, {})["source_path"] = UNC
        write_case(tools, evaluation)
        original_auth, original_record = args.auth_file.read_bytes(), Path(args.record).read_bytes()
        plan = scorer.build_plan(args)
        with pytest.raises(ValueError, match="absolute|UNC"):
            scorer.execute(plan, args)
        assert (tools / "invocation.json").is_file()
        assert not Path(plan["output"]).exists()
        receipt = assert_fake_cleanup(args, plan, original_auth, original_record)
        assert receipt["status"] == "REFUSED"


def test_fake_publication_refuses_unestablished_considered_local_paths_in_both_rubrics(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        for index, path in enumerate(CONSIDERED_LOCAL_PATHS):
            args, _, tools, evaluation = root_scenario(tmp_path / (rubric + "-" + str(index)), rubric)
            document = yaml.safe_load(Path(args.record).read_bytes())
            first_token = path[1:].split("/")[0]
            assert first_token not in document and first_token not in verify_authority(evaluation["metadata"])
            next(items(evaluation))["unit_scores"][0]["considered"] = [path]
            write_case(tools, evaluation)
            original_auth, original_record = args.auth_file.read_bytes(), Path(args.record).read_bytes()
            plan = scorer.build_plan(args)
            with pytest.raises(ValueError, match="absolute|UNC"):
                scorer.execute(plan, args)
            assert (tools / "invocation.json").is_file()
            assert not Path(plan["output"]).exists()
            receipt = assert_fake_cleanup(args, plan, original_auth, original_record)
            assert receipt["status"] == "REFUSED"


def test_fake_publication_preserves_established_considered_paths_in_both_rubrics(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        args, _, tools, evaluation = root_scenario(tmp_path / rubric, rubric)
        paths = bind_legitimate_considered(evaluation, Path(args.record), args.scope_context)
        write_case(tools, evaluation)
        original_auth, original_record = args.auth_file.read_bytes(), Path(args.record).read_bytes()
        plan = scorer.build_plan(args)
        scorer.execute(plan, args)
        published = Path(plan["output"]).read_bytes()
        assert published and published == (tools / "validated-snapshot.json").read_bytes()
        result = json.loads(published)
        assert next(items(result))["unit_scores"][0]["considered"] == paths
        assert result["overall_score"] == evaluation["overall_score"]
        checked = json.loads((tools / "real-validator-result.json").read_bytes())
        assert checked["returncode"] == 0
        assert checked["accepted_snapshot_sha256"] == sha(published)
        receipt = assert_fake_cleanup(args, plan, original_auth, original_record)
        assert receipt["status"] == "VALIDATED_AND_PUBLISHED"
