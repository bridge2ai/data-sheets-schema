#!/usr/bin/env python3
"""Evidence-boundary scan of a release series' transcripts, 2026-11-25.

Purpose: the series driver's gate reports only the Read tool's paths. A generation session
also runs shell commands, and later projects of a stream run beside the stream's earlier
outputs and beside committed records of earlier series. This lists every tool call (any
tool) whose input names generated-record territory that is not the run's own: a
d4d_concatenated path without the run's own label, a d4d_concatenated path under the own
label that names another project, evaluation outputs, rendered HTML, per-source records,
the attic, another launch worktree, or an earlier series label. It also lists calls that
name the d4d_concatenated tree broadly (no label at all), since a recursive search or
listing from there reaches sibling records. No model call, nothing written to a worktree.

Inputs:  --series LABEL-PREFIX --model M --condition C --projects P1,P2,... then the launch
         worktrees.
Outputs: one line per flagged call (record, tool, reason, the call's input shortened), then
         a count per record; exit 0 when nothing is flagged, 1 otherwise.
Serves:  the release-series rerun 2026-11-25c (PR 6325, issue 6324). Date: 2026-11-25.
"""
import argparse
import glob
import json
import os
import re
import sys

TERRITORY = re.compile(r"d4d_concatenated[^\s\"'|;&)]*")
OTHER = re.compile(r"(data/evaluation[^\s\"'|;&)]*|d4d_html[^\s\"'|;&)]*|d4d_individual[^\s\"'|;&)]*"
                   r"|data/ATTIC[^\s\"'|;&)]*|release-series-2026\d{4}-rep\d|claudecode_agent[^\s\"'|;&)]*"
                   r"|20\d\d-\d\d-\d\d[a-z]?_claude[^\s\"'|;&)/]*)")


def expand_label_variables(text, label):
    """Substitute a variable the same call assigns the run's own label ($V, ${V}, {V}).

    Shell state does not persist between the session's Bash calls, so a variable used in a
    call is assigned in that call. Only a variable assigned exactly the own label is
    substituted; any other variable in a path stays as written and is flagged. The text is
    the call's input as JSON, so quotes around the assigned value may carry a backslash.
    """
    assigned = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[\\\"']*" + re.escape(label) + r"[\\\"']*(?![A-Za-z0-9_.-])", text)
    for name in set(assigned):
        text = re.sub(r"\$\{" + name + r"\}|\$" + name + r"\b|\{" + name + r"\}", lambda _: label, text)
        # Python concatenation: 'prefix/'+L+'/suffix'
        text = re.sub(r"[\\\"']+\s*\+\s*" + name + r"\s*\+\s*[\\\"']+", lambda _: label, text)
    return text


def flags(text, label, project, projects, own_tree):
    found = []
    for match in TERRITORY.finditer(text):
        path = match.group(0)
        if label not in path:
            reason = "d4d_concatenated path without the run's label"
            if path.rstrip("/") in ("d4d_concatenated", "d4d_concatenated/claudecode_release",
                                    "d4d_concatenated/claudecode_release_core"):
                reason = "d4d_concatenated tree named broadly"
            found.append((reason, path))
            continue
        tail = path.split(label, 1)[1]
        if not re.match(r"/%s_(d4d|coverage|reconciliation|provenance|receipts|reasoning|report|review)" % re.escape(project), tail):
            # The label directory itself, a glob in it, or a file that is not this
            # project's: a listing or a recursive read from here reaches sibling records.
            found.append(("the run's label directory, not this project's own file", path))
            continue
        for other in projects:
            if other != project and re.search(r"/%s_(d4d|coverage|reconciliation|provenance|receipts|reasoning)" % re.escape(other), tail):
                # VOICE is a prefix of VOICE_PEDIATRIC; the pattern above requires the
                # artifact suffix right after the project name, so the two do not collide.
                found.append(("another project's artifact under the run's label", path))
    for match in OTHER.finditer(text):
        token = match.group(0)
        if token.startswith("release-series-") and token == os.path.basename(own_tree):
            continue
        if re.match(r"20\d\d-\d\d-\d\d[a-z]?_claude", token) and token.startswith(label.split("_rep")[0]) \
                and label in text[match.start():match.start() + len(label) + 2]:
            continue
        found.append(("other generated or evaluation territory", token))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--condition", default="generic_v9")
    parser.add_argument("--projects", required=True)
    parser.add_argument("worktrees", nargs="+")
    args = parser.parse_args()
    projects = args.projects.split(",")
    stem = "%s_%s-claudecode-%s_rep" % (args.series, args.model, args.condition.replace("_", "-"))
    total = 0
    for tree in args.worktrees:
        for path in sorted(glob.glob(os.path.join(tree, ".temp/launch/transcripts", stem + "*", "*.stream.jsonl"))):
            label = os.path.basename(os.path.dirname(path))
            project = os.path.basename(path)[:-len(".stream.jsonl")]
            calls = flagged = 0
            by_tool = {}
            with open(path, encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(event, dict) or event.get("type") != "assistant":
                        continue
                    content = (event.get("message") or {}).get("content")
                    for block in content if isinstance(content, list) else []:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        calls += 1
                        by_tool[block.get("name")] = by_tool.get(block.get("name"), 0) + 1
                        # Write and Edit carry the record's own text; scan only their path.
                        payload = block.get("input") or {}
                        if block.get("name") in ("Write", "Edit", "NotebookEdit"):
                            text = str(payload.get("file_path", ""))
                        else:
                            # The decoded values, not their JSON form: an escaped newline
                            # before a variable name would otherwise join the name.
                            text = "\n".join(str(value) for value in payload.values())
                        text = expand_label_variables(text, label)
                        for reason, token in flags(text, label, project, projects, tree):
                            flagged += 1
                            print("%s %s | %s | %s | %s | %s" % (project, label[-4:], block.get("name"), reason,
                                                               token[:120], text[:300].replace("\n", " ")))
            total += flagged
            print("# %s %s: %d tool calls %s, %d flagged" % (project, label[-4:], calls,
                                                              json.dumps(by_tool, sort_keys=True), flagged))
    print("# total flagged: %d" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
