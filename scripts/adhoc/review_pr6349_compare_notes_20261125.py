# Review helper (PR 6349): compare committed notes/launch, gates, streams with launch-worktree originals.
# Kept as review 1 of PR 6349 ran it (independent read-only review, 2026-11-25; report in
# notes/release_series_2026-11-25/review_1_pr6349.md); the only change is that ROOT comes from
# the environment (D4D_EXECUTIONS_ROOT) instead of an absolute path.
import filecmp, glob, os, re
ROOT = os.environ["D4D_EXECUTIONS_ROOT"]  # the directory holding the launch worktrees
A = f"{ROOT}/release-series-data-20261125/notes/release_series_2026-11-25"
MAP = {"1": "release-series-20261125-rep2", "2": "release-series-20261125-rep1", "3": "release-series-20261125-rep3"}
diff = same = 0
for sub, orig in (("launch", ".temp/launch"), ("gates", ".temp/launch/gates")):
    for f in sorted(glob.glob(f"{A}/{sub}/*")):
        rep = re.findall(r"_rep(\d)", os.path.basename(f))[-1]
        o = f"{ROOT}/{MAP[rep]}/{orig}/{os.path.basename(f)}"
        if not os.path.exists(o):
            print("MISSING ORIGINAL", f); diff += 1
        elif filecmp.cmp(f, o, shallow=False):
            same += 1
        else:
            print("DIFF", sub, os.path.basename(f)); diff += 1
    # files in the originals that were not committed
    for rep, wt in MAP.items():
        for o in glob.glob(f"{ROOT}/{wt}/{orig}/*_rep{rep}*"):
            if os.path.isfile(o) and not os.path.exists(f"{A}/{sub}/{os.path.basename(o)}"):
                print("NOT COMMITTED", sub, os.path.basename(o))
print("same", same, "diff", diff)
for f in sorted(glob.glob(f"{A}/gates/*.txt")):
    n = sum(1 for l in open(f) if l.startswith("GATES:"))
    if n != 1: print("GATES lines", n, f)
