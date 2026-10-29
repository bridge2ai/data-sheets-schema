"""Offline causal regressions for claude's E3x re-review R1-R6, 2026-10-29."""
from pathlib import Path

from tests.test_audit_evaluation_comparability import (
    audit, isolated_execution_locks, no_network, no_unmocked_runtime,
    registered_audit, registered_case, registered_generation_inputs, registered_prepared,
    registered_problem, registered_roster, rewrite_plan,
)


def test_r1_record_outside_root_is_refused_without_crashing(registered_case):
    # Reviewer rn1: the authority root holds the record; --root holds only packages.
    root, output, prepared = registered_case
    sub_root = output.parent.parent
    record = Path(prepared.document()["record"]["path"])
    assert not record.is_relative_to(sub_root) and output.is_relative_to(sub_root)
    result = audit.audit(sub_root, roster_manifest=registered_roster(registered_case),
        registered_evaluations=[("explicit-v10", output.relative_to(sub_root))],
        authority_roots=[root])
    assert registered_problem(result) == ["registered_record_outside_root"]
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_r1_provenance_outside_root_is_refused_without_crashing(registered_case, tmp_path):
    root, output, prepared = registered_case
    old_pin = prepared.document()["generation_provenance"]
    external = tmp_path / "external-provenance.yaml"
    external.write_bytes(Path(old_pin["path"]).read_bytes())
    assert not external.is_relative_to(root)

    def relocate(plan):
        new_pin = {**old_pin, "path": str(external)}
        plan["generation_provenance"] = new_pin
        plan["authorities"] = [new_pin if pin == old_pin else pin for pin in plan["authorities"]]

    rewrite_plan(output, relocate)
    result = registered_audit(registered_case, authority_roots=[tmp_path])
    assert registered_problem(result) == ["registered_provenance_outside_root"]
    assert result["totals"]["bound_registered_rating_files"] == 0
