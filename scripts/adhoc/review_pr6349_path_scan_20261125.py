# Review helper (PR 6349 review, 2026-11-25): independent path scan of all tool inputs.
# Kept as review 1 of PR 6349 ran it (independent read-only review, 2026-11-25; report in
# notes/release_series_2026-11-25/review_1_pr6349.md); the only change is that ROOT comes from
# the environment (D4D_EXECUTIONS_ROOT) instead of an absolute path.
# Flags any project name other than the run's own, any label/rep other than own, any absolute
# path outside the own worktree, and any data/ tree other than preprocessed + own label dirs.
import json, os, glob, re, sys
ROOT = os.environ["D4D_EXECUTIONS_ROOT"]  # the directory holding the launch worktrees
MAP = {"1": "release-series-20261125-rep2", "2": "release-series-20261125-rep1", "3": "release-series-20261125-rep3"}
PROJ = ["VOICE_PEDIATRIC", "AI_READI", "CHORUS", "CM4AI", "VOICE"]
projre = re.compile(r"(?<![A-Za-z0-9])(VOICE_PEDIATRIC|AI_READI|CHORUS|CM4AI|VOICE)(?![A-Za-z0-9])")
labre = re.compile(r"20\d\d-\d\d-\d\d[a-z]?_[A-Za-z0-9._-]+")
absre = re.compile(r"(/Users/[^\s'\"`;|&)]*|~/[^\s'\"`;|&)]*|\$HOME[^\s'\"`;|&)]*|/private/[^\s'\"`;|&)]*|/tmp/[^\s'\"`;|&)]*|/var/[^\s'\"`;|&)]*)")
datare = re.compile(r"data/([A-Za-z0-9_.-]+)")
for rep, wt in MAP.items():
    own_wt = f"{ROOT}/{wt}"
    for path in sorted(glob.glob(f"{own_wt}/.temp/launch/transcripts/*/*.stream.jsonl")):
        label = os.path.basename(os.path.dirname(path)); proj = os.path.basename(path)[:-13]
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            if e.get("type") != "assistant": continue
            for b in (e.get("message") or {}).get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use": continue
                inp = b.get("input") or {}
                if b["name"] in ("Write", "Edit"):
                    text = inp.get("file_path", "")
                else:
                    text = "\n".join(str(v) for v in inp.values())
                hits = []
                for m in projre.finditer(text):
                    if m.group(1) != proj:
                        hits.append("project:" + m.group(1))
                for m in labre.finditer(text):
                    if not m.group(0).startswith(label):
                        hits.append("label:" + m.group(0))
                for m in re.finditer(r"_rep(\d)", text):
                    if m.group(1) != rep:
                        hits.append("rep:" + m.group(0))
                for m in absre.finditer(text):
                    a = m.group(0)
                    if not a.startswith(own_wt + "/") and a != own_wt:
                        hits.append("abs:" + a[:140])
                for m in datare.finditer(text):
                    if m.group(1) not in ("preprocessed", "d4d_concatenated"):
                        hits.append("data:" + m.group(0))
                for m in re.finditer(r"d4d_concatenated/([A-Za-z0-9_]+)", text):
                    if m.group(1) not in ("claudecode_release", "claudecode_release_core"):
                        hits.append("method:" + m.group(0))
                if hits:
                    print(f"rep{rep}\t{proj}\t{b['name']}\t{sorted(set(hits))}\t{text[:400]!r}")
