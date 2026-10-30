#!/usr/bin/env bash
# Purpose: serial offline E3x × #5096 relocation checks, 2026-10-29.
# Inputs: check label, evidence directory, pytest arguments; external basetemp.
# Outputs: complete pytest log, JUnit XML, exit status; refs E3x / #5096 / #5213.
set -euo pipefail
e3x_label=${1:?check label required}
e3x_output=${2:?evidence directory required}
shift 2
e3x_root=$(git rev-parse --show-toplevel)
e3x_python=${E3X_PYTHON:-/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python}
case "$e3x_output/" in
    "$e3x_root/tmp/"*|/private/tmp/*|/tmp/*) ;;
    *) echo 'Use checkout/tmp or an external temporary evidence directory' >&2; exit 2 ;;
esac
e3x_temporary=${E3X_BASETEMP_ROOT:-/private/tmp/d4d-e3x-relocation-20261029}
case "$e3x_temporary/" in
    /private/tmp/*|/tmp/*) ;;
    *) echo 'pytest basetemp must be in external temporary storage' >&2; exit 2 ;;
esac
mkdir -p "$e3x_output" "$e3x_temporary"
test ! -e "$e3x_output/$e3x_label.log"
unset ANTHROPIC_API_KEY CBORG_API_KEY OPENAI_API_KEY AZURE_OPENAI_API_KEY
unset GOOGLE_API_KEY GEMINI_API_KEY OPENROUTER_API_KEY D4D_INSTALL_TESTS
unset ANTHROPIC_AUTH_TOKEN AZURE_OPENAI_AD_TOKEN
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export PYTHONPATH="$e3x_root/src:$e3x_root:$e3x_root/fairscape_models"
export PATH="$(dirname "$e3x_python"):$PATH"
export PYTHONDONTWRITEBYTECODE=1 PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 GIT_NO_LAZY_FETCH=1
export PYTHONPYCACHEPREFIX="$e3x_temporary/pycache"
e3x_command=("$e3x_python")
if [[ ${E3X_LOOPBACK_SANDBOX:-0} == 1 ]]; then
    e3x_command=(/usr/bin/sandbox-exec -f "$e3x_root/scripts/adhoc/e3x_offline_20261029.sb" "$e3x_python")
fi
if [[ ${E3X_NOTES_CONTROLS:-0} == 1 ]]; then
    # Native transport controls explicitly refuse a bytecode cache prefix.
    unset PYTHONPYCACHEPREFIX
    export PYTHONPATH="$PYTHONPATH:$e3x_root/notes/matched_cborg_2026-09-13:$e3x_root/notes/matched_cborg_2026-09-13/native_controls:$e3x_root/notes/matched_cborg_2026-09-13/evaluation_controls"
fi
{
    git rev-parse HEAD
    "$e3x_python" --version
    shasum -a 256 poetry.lock src/data_sheets_schema/evaluation/arm_comparison.py tests/test_arm_comparison.py
    shasum -a 256 "$0" scripts/adhoc/e3x_offline_20261029.sb .github/workflows/main.yaml utils/pytest_shard.py utils/ci_test_durations.json
    uptime
} > "$e3x_output/$e3x_label.inputs"
set +e
"${e3x_command[@]}" -m pytest -o addopts='' -p no:cacheprovider \
    --basetemp="$e3x_temporary/$e3x_label-tmp" \
    --junitxml="$e3x_output/$e3x_label.xml" "$@" \
    > "$e3x_output/$e3x_label.log" 2>&1
e3x_status=$?
set -e
printf '%s\n' "$e3x_status" > "$e3x_output/$e3x_label.exit"
test -s "$e3x_output/$e3x_label.log"
tail -n 12 "$e3x_output/$e3x_label.log"
exit "$e3x_status"
