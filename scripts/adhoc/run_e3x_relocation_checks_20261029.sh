#!/usr/bin/env bash
# Purpose: serial offline E3x × #5096 relocation checks, 2026-10-29.
# Inputs: check label, external evidence directory, pytest arguments.
# Outputs: complete pytest log, JUnit XML, exit status; refs E3x / #5096 / #5213.
set -euo pipefail
e3x_label=${1:?check label required}
e3x_output=${2:?external evidence directory required}
shift 2
e3x_root=$(git rev-parse --show-toplevel)
e3x_python=${E3X_PYTHON:-/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python}
case "$e3x_output/" in
    /private/tmp/*|/tmp/*) ;;
    *) echo 'Use an external temporary evidence directory' >&2; exit 2 ;;
esac
mkdir -p "$e3x_output"
test ! -e "$e3x_output/$e3x_label.log"
unset ANTHROPIC_API_KEY CBORG_API_KEY OPENAI_API_KEY AZURE_OPENAI_API_KEY
unset GOOGLE_API_KEY GEMINI_API_KEY OPENROUTER_API_KEY D4D_INSTALL_TESTS
export PYTHONPATH="$e3x_root/src:$e3x_root:$e3x_root/fairscape_models"
export PATH="$(dirname "$e3x_python"):$PATH"
export PYTHONDONTWRITEBYTECODE=1 PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 GIT_NO_LAZY_FETCH=1
export PYTHONPYCACHEPREFIX="$e3x_output/pycache"
{
    git rev-parse HEAD
    "$e3x_python" --version
    shasum -a 256 poetry.lock src/data_sheets_schema/evaluation/arm_comparison.py tests/test_arm_comparison.py
    uptime
} > "$e3x_output/$e3x_label.inputs"
set +e
"$e3x_python" -m pytest -o addopts='' -p no:cacheprovider \
    --basetemp="$e3x_output/$e3x_label-tmp" \
    --junitxml="$e3x_output/$e3x_label.xml" "$@" \
    > "$e3x_output/$e3x_label.log" 2>&1
e3x_status=$?
set -e
printf '%s\n' "$e3x_status" > "$e3x_output/$e3x_label.exit"
test -s "$e3x_output/$e3x_label.log"
tail -n 12 "$e3x_output/$e3x_label.log"
exit "$e3x_status"
