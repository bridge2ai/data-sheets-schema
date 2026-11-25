# PR 6340 / issue 6348, 2026-11-25: invoke the real CLI with default SIGHUP.
# Input: scorer path and its offline fixture argv. Output: real CLI receipts.
# This removes inherited shell signal policy; only the test's fake child runs.
import runpy
import signal
import sys


signal.signal(signal.SIGHUP, signal.SIG_DFL)
sys.argv.pop(0)
runpy.run_path(sys.argv[0], run_name="__main__")
