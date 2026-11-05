# Purpose: run pytest (or a python script) offline for the G1 fix-round re-review:
# installs a socket audit hook that refuses non-loopback connections, removes the
# main checkout's src from sys.path, puts the worktree (cwd) first.
# Inputs: argv = ['pytest', args...] or ['script.py', args...]; run from a worktree root.
# Outputs: pytest exit status / script output. Reviewer helper, G1 re-review, 2026-10-30.
import os, sys, runpy

for key in list(os.environ):
    if key.endswith('_API_KEY'):
        os.environ.pop(key)

def offline(event, args):
    if event == "socket.connect":
        addr = args[1]
        if isinstance(addr, (str, bytes)) or (isinstance(addr, tuple) and addr and addr[0] in ("127.0.0.1", "::1", "localhost")):
            return
        raise RuntimeError("re-review offline guard: network forbidden: %s %r" % (event, args[:2]))
    if event == "socket.getaddrinfo":
        if args and args[0] in ("127.0.0.1", "::1", "localhost", None, b"127.0.0.1", b"localhost"):
            return
        raise RuntimeError("re-review offline guard: network forbidden: %s %r" % (event, args[:2]))

sys.addaudithook(offline)
_MAIN_SRC = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src"
sys.path[:] = [x for x in sys.path if x.rstrip("/") != _MAIN_SRC]
sys.path.insert(0, os.getcwd())
target, *rest = sys.argv[1:]
def _expand(args):
    # "@@path" expands to the node ids listed one per line in that file
    out = []
    for a in args:
        if a.startswith("@@"):
            out.extend(l.rstrip("\n") for l in open(a[2:], encoding="utf-8") if l.strip())
        else:
            out.append(a)
    return out

if target == "pytest":
    rest = _expand(rest)
    import pytest
    class ImmediateFailures:
        def pytest_runtest_logreport(self, report):
            if report.failed:
                print('\nP4a failure:', report.nodeid, '\n', report.longreprtext, flush=True)
    raise SystemExit(pytest.main(rest, plugins=[ImmediateFailures()]))
sys.argv = [target, *rest]
runpy.run_path(target, run_name="__main__")
