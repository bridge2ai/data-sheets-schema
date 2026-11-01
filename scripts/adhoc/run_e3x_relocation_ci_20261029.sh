#!/usr/bin/env bash
# Purpose: finish serial offline CI-layout and E3x/D52 validation, 2026-10-29.
# Inputs: evidence directory after ci-ordinary-1 canary completes.
# Outputs: per-lane log/XML/status via the retained check launcher.
# Refs: E3x x #5096 relocation contract and #5213 composition.
set -euo pipefail
e3x_output=${1:?evidence directory required}
e3x_check=scripts/adhoc/run_e3x_relocation_checks_20261029.sh
e3x_head=$(git rev-parse HEAD)
test -s "$e3x_output/ci-ordinary-1.xml"
test -s "$e3x_output/ci-ordinary-1.exit"
export E3X_LOOPBACK_SANDBOX=1
e3x_failed=0
check() {
    if [[ -s "$e3x_output/$1.exit" ]]; then
        test "$(head -n 1 "$e3x_output/$1.inputs")" = "$e3x_head"
        test -s "$e3x_output/$1.xml"
        printf 'Retaining completed lane %s (exit %s)\n' "$1" "$(cat "$e3x_output/$1.exit")"
        if [[ $(cat "$e3x_output/$1.exit") != 0 ]]; then e3x_failed=1; fi
        return
    fi
    if [[ -e "$e3x_output/$1.log" ]]; then
        e3x_interrupted="$e3x_output/interrupted-$1-$(date -u +%Y%m%dT%H%M%SZ)"
        mkdir "$e3x_interrupted"
        for e3x_extension in log xml inputs; do
            if [[ -e "$e3x_output/$1.$e3x_extension" ]]; then
                mv "$e3x_output/$1.$e3x_extension" "$e3x_interrupted/"
            fi
        done
        printf 'Preserved incomplete lane evidence in %s\n' "$e3x_interrupted"
    fi
    if ! bash "$e3x_check" "$1" "$e3x_output" "${@:2}"; then
        e3x_failed=1
    fi
}
for e3x_shard in 2 3 4 5 6; do
    check "ci-ordinary-$e3x_shard" tests -v -p utils.pytest_shard \
        "--ci-shard=$e3x_shard/6" --ci-shard-timings=utils/ci_test_durations.json \
        --ci-lane=ordinary --durations=25
done
for e3x_lane in routing-dispatch routing-portable routing-regate routing-default-layout; do
    check "ci-$e3x_lane" tests -v -p utils.pytest_shard "--ci-lane=$e3x_lane" --durations=25
done
# Exact file roster from run_e3x_acceptance_20261029.sh (684 at 709099dbc).
check e3x-d52 -v \
    tests/test_arm_comparison.py tests/test_blind_review_pack.py \
    tests/test_registered_eval_runner.py tests/test_audit_evaluation_comparability.py \
    tests/test_d52_scoring.py tests/test_evaluation/test_evaluate_d4d.py \
    tests/test_evaluation/test_rubric20_scoring.py tests/test_evaluation/test_general_context.py \
    tests/test_evaluation/test_explicit_dataset_scope.py tests/test_d52_publication_labels.py \
    tests/test_e3x_fixes.py tests/test_e3x_blinding_fixes.py \
    tests/test_e3x_receipt_fixes.py tests/test_e3x_guard_kills.py \
    tests/test_e3x_rereview_fixes.py tests/test_e3x_rereview_kills.py
# The separate offline jobs in .github/workflows/main.yaml; no schema builds.
export E3X_NOTES_CONTROLS=1
check ci-budget -v \
    notes/matched_cborg_2026-09-13/test_budgeted_cborg.py \
    notes/matched_cborg_2026-09-13/test_budget_amendment.py \
    notes/matched_cborg_2026-09-13/test_second_budget_amendment.py \
    notes/matched_cborg_2026-09-13/test_budget_amendment_chain.py \
    notes/matched_cborg_2026-09-13/test_continuation_sequence.py \
    notes/matched_cborg_2026-09-13/test_sequence_claim.py
check ci-native -v \
    notes/matched_cborg_2026-09-13/native_controls/test_native_proxy.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_launch.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_command_policy.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_readonly.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_control.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_history_control.py \
    notes/matched_cborg_2026-09-13/native_controls/test_probe_native_history.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_file_policy.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_phase_history.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_phase_control.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_stall_policy.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_stall_controls.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_thinking_display.py \
    notes/matched_cborg_2026-09-13/native_controls/test_native_response_buffer.py \
    notes/matched_cborg_2026-09-13/native_controls/test_transport_probe.py \
    notes/matched_cborg_2026-09-13/native_controls/test_audit_after_probe.py \
    notes/claudecode_direct/test_direct_arm.py
check ci-audit -v notes/matched_cborg_2026-09-13/audit_controls \
    notes/matched_cborg_2026-09-13/finalization_controls
check ci-evaluation -v notes/matched_cborg_2026-09-13/evaluation_controls
exit "$e3x_failed"
