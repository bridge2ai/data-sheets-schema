#!/bin/sh
# Purpose: add macOS time(1) resource accounting to unchanged recorder trials.
# Inputs: existing measurement driver's Python arguments; outputs: normal worker
# stdout/stderr plus time -l statistics in the driver's existing pytest.log.
# Refs #5149/#5212, wave-2 recorder diagnosis; date 2026-10-27.
# This wrapper changes no test, runtime deadline, target source or environment.
set -eu
exec /usr/bin/time -l /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python "$@"
