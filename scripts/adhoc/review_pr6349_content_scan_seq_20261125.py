# Review helper (PR 6349 review, 2026-11-25): content-level evidence-boundary check.
# Kept as review 1 of PR 6349 ran it (independent read-only review, 2026-11-25; report in
# notes/release_series_2026-11-25/review_1_pr6349.md); the only change is that ROOT comes from
# the environment (D4D_EXECUTIONS_ROOT) instead of an absolute path.
# For each transcript, flag tool-result lines that occur in some OTHER generated record /
# evaluation / html / attic file but not in the run's allowed inputs or its own outputs.
import json, os, glob, re, sys, collections
ROOT = os.environ["D4D_EXECUTIONS_ROOT"]  # the directory holding the launch worktrees
A = f"{ROOT}/release-series-data-20261125"
MAP = {"1": "release-series-20261125-rep2", "2": "release-series-20261125-rep1", "3": "release-series-20261125-rep3"}
MINLEN = 40
STRIPS = [re.compile(r"^\s*\d+\t"), re.compile(r"^\s*\d+→"), re.compile(r"^[^\s:]+:\d+[:-]"), re.compile(r"^\d+[:-]")]

def norm_variants(line):
    out = {line.strip()}
    for s in STRIPS:
        out.add(s.sub("", line).strip())
    return {v for v in out if len(v) >= MINLEN}

def file_lines(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return {l.strip() for l in f if len(l.strip()) >= MINLEN}
    except Exception:
        return set()

# foreign territory: record -> lines
foreign_files = []
for pat in ["data/d4d_concatenated/**/*", "data/evaluation*/**/*", "data/ATTIC/**/*", "data/d4d_html/**/*", "data/d4d_individual/**/*"]:
    for p in glob.glob(os.path.join(A, pat), recursive=True):
        if os.path.isfile(p) and os.path.getsize(p) < 20_000_000 and not p.endswith((".gz", ".png", ".pdf", ".zip", ".tar")):
            foreign_files.append(p)
print("foreign files:", len(foreign_files), file=sys.stderr)
line_owner = collections.defaultdict(set)
for p in foreign_files:
    rel = os.path.relpath(p, A)
    for l in file_lines(p):
        line_owner[l].add(rel)
print("foreign lines:", len(line_owner), file=sys.stderr)

common_allowed = set()
for pat in ["src/**/*.py", "src/**/*.yaml", "src/**/*.md", ".claude/**/*.md", "notes/receipts_pattern_2026-08-27.md", "data/preprocessed/source_manifest.yaml", "CLAUDE.md"]:
    for p in glob.glob(os.path.join(A, pat), recursive=True):
        common_allowed |= file_lines(p)

for rep, wt in MAP.items():
    for path in sorted(glob.glob(f"{ROOT}/{wt}/.temp/launch/transcripts/*/*.stream.jsonl")):
        label = os.path.basename(os.path.dirname(path)); proj = os.path.basename(path)[:-13]
        own_files = [f"data/d4d_concatenated/claudecode_release/{label}/{proj}_d4d.yaml"] + \
            [f"data/d4d_concatenated/claudecode_release_core/{label}/{proj}_{s}" for s in ("d4d_core.yaml", "coverage_receipt.yaml", "provenance.yaml", "receipts.yaml", "reconciliation.md")]
        allowed = set(common_allowed)
        allowed |= file_lines(f"{A}/data/preprocessed/concatenated/{proj}_preprocessed.txt")
        allowed |= file_lines(f"{A}/data/preprocessed/chunks/{proj}_chunks.yaml")
        allowed |= file_lines(f"{ROOT}/{wt}/.temp/launch/{proj}_{label}.md")
        for f in [x for x in own_files if x.endswith(("provenance.yaml","receipts.yaml","d4d_core.yaml"))]:
            allowed |= file_lines(f"{A}/{f}")
        results = []; written = {}
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            m = e.get("message") or {}
            for b in m.get("content") or [] if isinstance(m.get("content"), list) else []:
                if not isinstance(b, dict): continue
                if e.get("type") == "assistant" and b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit"):
                    inp = b.get("input") or {}
                    for k in ("content", "new_string"):
                        for l in str(inp.get(k, "")).splitlines():
                            for v in norm_variants(l):
                                written.setdefault(v, len(results))
                if e.get("type") == "user" and b.get("type") == "tool_result":
                    c = b.get("content")
                    if isinstance(c, list):
                        c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
                    results.append((str(c), len(results)))
        hits = collections.Counter(); owners = collections.Counter()
        for txt, allowed_then in results:
            for l in txt.splitlines():
                vs = norm_variants(l)
                if not vs or vs & allowed or any(written.get(v, 10**9) < allowed_then for v in vs): continue
                for v in vs:
                    if v in line_owner:
                        own_rel = set(own_files)
                        others = line_owner[v] - own_rel
                        if others:
                            hits[v[:160]] += 1
                            for o in others: owners[o.split("/")[0] + "/" + "/".join(o.split("/")[1:3])] += 1
                        break
        print(f"== rep{rep} {proj}: {len(results)} results, {sum(hits.values())} foreign-only lines ({len(hits)} distinct)")
        for v, n in hits.most_common(12):
            print(f"   {n}x {v!r}  <- {sorted(line_owner.get(v, []))[:3]}")
