#!/usr/bin/env python
"""Exploratory: where adult, pediatric and historical-release identifiers sit in VOICE records.

Question: do identifiers of the related pediatric dataset, or of earlier releases of the adult
dataset, appear in fields that describe the record's own dataset?

Record set: every full record data/d4d_concatenated/{claudecode_agent,claudecode_api}/<label>/
VOICE*_d4d.yaml except the `gate_test` label (a runner gate test, not an experiment; it holds no
VOICE record at HEAD, and is excluded by name so a later one cannot slip in). At HEAD that is 50
records: 44 VOICE_d4d.yaml (declared referent: the adult Bridge2AI-Voice dataset) and 6
VOICE_PEDIATRIC_d4d.yaml (declared referent: the Bridge2AI-Voice Pediatric Dataset), the referent
being the one data/preprocessed/source_manifest.yaml `scope:` declares for the record's project key.
VOICE records in the other method directories (crate, crate_only, merged, assistant, gpt5, static
map, ...) are outside this set; they are counted at run time, named in the figure note and listed as
excluded rows of the records CSV. Every record must have a <method>_core/<label>/<P>_provenance.yaml sibling; the arm comes from its
model.agent_runtime (data_sheets_schema.runs.RUNTIME_KEYS) and the prompt condition from its
prompts.files (path + sha256). Records whose provenance lists no prompt file are grouped by
model.mode. Directory labels are not trusted for the condition: the 2026-08-07 "...-generic-v3"
label ran prompt file d4d_generic_arm_prompt.md (v1) per its provenance. Records later superseded
as canonical (provenance canonical_superseded_by) are kept and marked in the records CSV.

Identifier catalog (rows): built at run time and each entry verified against the file it is
claimed from, then matched in the records by DOI, PhysioNet URL path or Synapse ID:
- source_manifest.yaml scope.VOICE: referent_id (adult project DOI), the per-version DOIs in
  referent_note, related_but_distinct (pediatric project DOI and also_known_as release DOI/URL);
  scope.VOICE_PEDIATRIC.referent_note (pediatric release DOI);
- source_manifest.yaml projects.VOICE: the versioned PhysioNet URLs and `superseded_by`; the
  pediatric curation note (Synapse raw-audio ID, "v1.0.0 exists upstream but is superseded");
- the VOICE document bundle (data/preprocessed/concatenated/VOICE_preprocessed.txt): the adult
  raw-audio Synapse ID and the Health Data Nexus version 1.0 DOI;
- the records only: PhysioNet URLs for adult 2.0.x and pediatric 1.0.0.
Bare version strings ("3.0.0") are not counted; neither are software, publication or platform
identifiers (Zenodo DOIs, healthdatanexus.ai).

Field roles (columns), assigned per YAML leaf, first rule wins:
1 free text     - the leaf key is descriptive (description, notes, *_details, source_caveats, ...);
2 related/ext.  - the path passes through related_datasets, parent_datasets or external_resources;
3 root identity - a top-level id, doi, page or citation;
4 version       - the path passes through version_access, updates, distribution_dates or errata;
5 distribution  - the path starts at distribution_formats, file_collections, resources, raw_sources,
                  raw_data_sources, or is the top-level download_url;
6 other structured - everything else (mostly nested object ids that use a DOI as a namespace).
Every leaf key that holds a match must be in FREE_TEXT_KEYS or STRUCTURED_KEYS or the build stops.
A record counts once per (identifier, role) cell however many times it repeats the identifier.

Flag rule (a heuristic, labelled as such in the figure): a cell is flagged for review when an
identifier of the *other* dataset sits in a root, version, distribution or other-structured role,
or an earlier release of the record's own dataset sits in a root, distribution or other-structured
role. Earlier releases in version fields, anything in related/external links and anything in free
text are not flagged. A flagged placement is a candidate for review, not an established error: a
record written to describe both cohorts, a release history, or a raw-audio access note can
legitimately carry these identifiers.
"""
from __future__ import annotations

import re
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.figures import _style as st  # noqa: E402

sys.path.insert(0, str(st.ROOT / "src"))
from data_sheets_schema.runs import RUNTIME_KEYS  # noqa: E402

CONCAT = st.ROOT / "data" / "d4d_concatenated"
MANIFEST = st.ROOT / "data" / "preprocessed" / "source_manifest.yaml"
BUNDLE = st.ROOT / "data" / "preprocessed" / "concatenated" / "VOICE_preprocessed.txt"
METHODS = ["claudecode_agent", "claudecode_api"]
EXCLUDED_LABELS = {"gate_test": "runner gate test, not an experiment"}
REFERENT_OF_FILE = {"VOICE_d4d.yaml": "VOICE", "VOICE_PEDIATRIC_d4d.yaml": "VOICE_PEDIATRIC"}
REFERENT_TEXT = {"VOICE": "adult", "VOICE_PEDIATRIC": "pediatric"}

ROLES = ["root", "version", "dist", "other", "related", "text"]
ROLE_LABEL = {"root": "root\nidentity", "version": "version /\nrelease", "dist": "distribution\n/ resources",
              "other": "other\nstructured", "related": "related /\nexternal", "text": "free\ntext"}
ROLE_NAME = {"root": "root identity", "version": "version/release", "dist": "distribution/resources",
             "other": "other structured", "related": "related/external", "text": "free text"}
ROLE_RULE = {
    "text": "leaf key is descriptive: " ,
    "related": "path passes through related_datasets, parent_datasets or external_resources",
    "root": "top-level id, doi, page or citation",
    "version": "path passes through version_access, updates, distribution_dates or errata",
    "dist": "path starts at distribution_formats, file_collections, resources, raw_sources, raw_data_sources, or top-level download_url",
    "other": "any other structured leaf (mostly nested object ids that use a DOI as a namespace)",
}
FREE_TEXT_KEYS = {"description", "notes", "access_details", "version_details", "source_caveats",
                  "source_description", "recommended_mitigation", "raw_data_details", "future_guarantees"}
STRUCTURED_KEYS = {"id", "doi", "page", "citation", "download_url", "access_urls", "access_url",
                   "target_dataset", "versions_available", "latest_version_doi", "release_dates",
                   "erratum_url", "external_resources", "principal_investigator", "affected_subsets",
                   "contact_person", "committee_contact"}
ROLE_RULE["text"] += ", ".join(sorted(FREE_TEXT_KEYS))
RELATED_SEGS = {"related_datasets", "parent_datasets", "external_resources"}
ROOT_KEYS = {"id", "doi", "page", "citation"}
VERSION_SEGS = {"version_access", "updates", "distribution_dates", "errata"}
DIST_HEADS = {"distribution_formats", "file_collections", "resources", "raw_sources", "raw_data_sources"}

FLAG_FILL = st.STATUS["warning"]
# column labels for records whose provenance lists no prompt file, keyed by the exact model.mode;
# an unlisted mode stops the build instead of taking a guessed label
NO_FILE_MODES = {"four-phase project agent": "project\nagent, no file†",
                 "four-phase project agent, de-primed": "de-primed\nno file†"}
OUT_OF_SCOPE = "other method directory: outside the claudecode_agent/ + claudecode_api/ record set"


def vtuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def doi_rx(doi: str) -> str:
    return re.escape(doi.lower().replace("https://doi.org/", "").replace("doi:", ""))


def build_catalog(manifest: dict, bundle: str) -> list[dict]:
    """Rows of the matrix, each verified against the file it is claimed from."""
    scope = manifest["scope"]
    adult, ped = scope["VOICE"], scope["VOICE_PEDIATRIC"]
    project_doi = adult["referent_id"]
    per_version = dict((v, d) for d, v in re.findall(r"(10\.13026/[a-z0-9-]+) \(([\d.]+)\)", adult["referent_note"]))
    assert per_version, "no per-version DOIs parsed from scope.VOICE.referent_note"
    # versioned PhysioNet URLs and supersession, from projects.VOICE
    entries = {}
    for e in manifest["projects"]["VOICE"]:
        m = re.match(r"https://physionet\.org/content/b2ai-voice/([\d.]+)/$", e.get("url", ""))
        if m:
            entries[m.group(1)] = e
    assert set(per_version) == set(entries), (per_version, sorted(entries))
    latest = max(per_version, key=vtuple)
    rel = [r for r in adult["related_but_distinct"] if r.get("manifest_key") == "VOICE_PEDIATRIC"]
    assert len(rel) == 1, "expected one pediatric related_but_distinct entry"
    rel = rel[0]
    assert rel["id"] == ped["referent_id"], (rel["id"], ped["referent_id"])
    ped_rel = re.search(r"Release ([\d.]+) is (10\.13026/[a-z0-9-]+)", ped["referent_note"])
    assert ped_rel, "no pediatric release DOI in scope.VOICE_PEDIATRIC.referent_note"
    ped_ver, ped_doi = ped_rel.groups()
    aka = rel["also_known_as"]
    assert any(ped_doi in a for a in aka), (ped_doi, aka)
    ped_url = [a for a in aka if "physionet.org/content/b2ai-voice-pediatric/" in a]
    assert ped_url and ped_url[0].rstrip("/").endswith(ped_ver), ped_url
    ped_entry = [e for e in manifest["projects"]["VOICE"] if e["id"] == rel["in_bundle"]][0]
    note = " ".join(ped_entry["curation_note"].split())
    ped_syn = re.search(r"Synapse \((syn\d+)\)", note).group(1)
    ped_old = re.search(r"Pediatric v([\d.]+) exists upstream but is superseded and was not captured", note).group(1)
    adult_syn = re.search(r"Raw Audio Data Access for Bridge2AI Voice Adult Cohort.*?Synapse:(syn\d+)", bundle, re.S).group(1)
    hdn = re.search(r"\(version 1\.0\)\. Health Data Nexus\.\s*https://doi\.org/(10\.57764/[a-z0-9-]+)", bundle).group(1)
    assert re.search(r"physionet\.org/content/b2ai-voice/\s", bundle), "unversioned adult PhysioNet URL not in bundle"
    pn = r"physionet\.org/content/b2ai-voice/"
    pp = r"physionet\.org/content/b2ai-voice-pediatric/"
    short = lambda d: d.split("/")[-1]
    cat = [dict(key="adult_all", dataset="VOICE", status="all versions",
                label="all versions (project DOI)",
                recog=f"{short(project_doi)} · …/b2ai-voice/ (no version)", src="scope",
                rx=doi_rx(project_doi) + "|" + pn + r"(?![0-9])",
                recognized_from="source_manifest scope.VOICE.referent_id; unversioned PhysioNet URL (bundle)")]
    for v in sorted(per_version, key=vtuple, reverse=True):
        superseded = entries[v].get("superseded_by")
        status = "latest captured" if v == latest else ("superseded" if superseded else "earlier release")
        cat.append(dict(key=f"adult_{v}", dataset="VOICE", status=status,
                        label=f"v{v}, {status}", recog=f"{short(per_version[v])} · …/b2ai-voice/{v}",
                        src="scope, manifest" + (" superseded_by" if superseded else ""),
                        rx=doi_rx(per_version[v]) + "|" + pn + re.escape(v) + r"(?![0-9.])",
                        recognized_from=f"scope.VOICE.referent_note DOI; projects.VOICE {entries[v]['id']} url"
                                        + (f"; superseded_by {superseded}" if superseded else "")))
        if v == "3.0.0":  # records-only releases between 3.0.0 and 1.1, kept in version order
            cat.append(dict(key="adult_2.0.x", dataset="VOICE", status="earlier release",
                            label="v2.0.x, earlier release", recog="…/b2ai-voice/2.0.0, 2.0.1 (URL only)",
                            src="records only", rx=pn + r"2\.\d",
                            recognized_from="records only: PhysioNet URL with a 2.x version; not in manifest or bundle"))
    cat.append(dict(key="adult_1.0_hdn", dataset="VOICE", status="earlier release",
                    label="v1.0 (Health Data Nexus), earlier release", recog=f"{hdn}", src="bundle",
                    rx=re.escape(hdn), recognized_from="VOICE bundle: citation '(version 1.0). Health Data Nexus.' DOI"))
    cat.append(dict(key="adult_raw_synapse", dataset="VOICE", status="raw audio",
                    label="raw audio on Synapse", recog=adult_syn, src="bundle", rx=re.escape(adult_syn),
                    recognized_from="VOICE bundle: 'Raw Audio Data Access for Bridge2AI Voice Adult Cohort' Synapse ID"))
    cat += [
        dict(key="ped_all", dataset="VOICE_PEDIATRIC", status="all versions",
             label="all versions (project DOI)", recog=f"{short(rel['id'])} · …/b2ai-voice-pediatric/ (no version)",
             src="scope", rx=doi_rx(rel["id"]) + "|" + pp + r"(?![0-9])",
             recognized_from="scope.VOICE.related_but_distinct id (= scope.VOICE_PEDIATRIC.referent_id); verification_url"),
        dict(key=f"ped_{ped_ver}", dataset="VOICE_PEDIATRIC", status="latest captured",
             label=f"v{ped_ver}, latest captured", recog=f"{short(ped_doi)} · …/pediatric/{ped_ver}", src="scope",
             rx=doi_rx(ped_doi) + "|" + pp + re.escape(ped_ver),
             recognized_from="scope.VOICE.related_but_distinct also_known_as; scope.VOICE_PEDIATRIC.referent_note"),
        dict(key=f"ped_{ped_old}", dataset="VOICE_PEDIATRIC", status="superseded",
             label=f"v{ped_old}, superseded, not captured", recog=f"…/pediatric/{ped_old} (URL only)",
             src="manifest note", rx=pp + re.escape(ped_old),
             recognized_from=f"projects.VOICE {ped_entry['id']} curation_note: 'v{ped_old} exists upstream but is superseded'"),
        dict(key="ped_raw_synapse", dataset="VOICE_PEDIATRIC", status="raw audio",
             label="raw audio on Synapse", recog=ped_syn, src="manifest note", rx=re.escape(ped_syn),
             recognized_from=f"projects.VOICE {ped_entry['id']} curation_note Synapse ID"),
    ]
    for c in cat:
        c["regex"] = re.compile(c["rx"], re.I)
    return cat


def role_of(path: list[str]) -> str:
    segs = [s for s in path if s != "[]"]
    leaf = segs[-1]
    if leaf in FREE_TEXT_KEYS:
        return "text"
    assert leaf in STRUCTURED_KEYS, f"unclassified leaf key {leaf!r} at {'.'.join(path)}"
    if RELATED_SEGS & set(segs):
        return "related"
    if len(segs) == 1 and leaf in ROOT_KEYS:
        return "root"
    if VERSION_SEGS & set(segs):
        return "version"
    if segs[0] in DIST_HEADS or segs == ["download_url"]:
        return "dist"
    return "other"


def flag_reason(referent: str, ident: dict, role: str) -> str:
    """Heuristic flag rule; empty string = not flagged."""
    if role in ("related", "text"):
        return ""
    if ident["dataset"] != referent:
        return f"{REFERENT_TEXT[ident['dataset']]} dataset identifier in a {role} role of a {REFERENT_TEXT[referent]} record"
    if ident["status"] in ("superseded", "earlier release") and role != "version":
        return f"earlier release of the record's own dataset in a {role} role"
    return ""


def condition_of(prov: dict) -> tuple[str, str, str, str]:
    """(condition key, column label, description, generic prompt version or "" when no file)."""
    files = (prov.get("prompts") or {}).get("files") or []
    if not files:
        mode = prov["model"].get("mode")
        assert mode in NO_FILE_MODES, (f"model.mode {mode!r} has no prompt file and no column label; "
                                       "add it to NO_FILE_MODES rather than guess one")
        return "mode:" + mode, NO_FILE_MODES[mode], f"no prompt file in provenance; model.mode '{mode}'", ""
    assert len(files) == 1, files
    path, sha = files[0]["path"], files[0]["sha256"]
    m = re.search(r"d4d_generic_arm_prompt(?:_v(\d+))?\.md$", path)
    assert m, path
    ver = m.group(1) or "1"
    return f"{path}@{sha[:8]}", f"generic v{ver}", f"{path} sha256 {sha[:12]}", ver


def load_records(catalog: list[dict]):
    records, excluded = [], []
    for method in METHODS:
        for p in sorted((CONCAT / method).glob("*/VOICE*_d4d.yaml")):
            label = p.parent.name
            if label in EXCLUDED_LABELS:
                excluded.append({"path": str(p.relative_to(st.ROOT)), "reason": EXCLUDED_LABELS[label]})
                continue
            referent = REFERENT_OF_FILE[p.name]
            prov_path = CONCAT / f"{method}_core" / label / (p.name[: -len("_d4d.yaml")] + "_provenance.yaml")
            assert prov_path.exists(), f"no provenance record for {p}"
            prov = yaml.safe_load(prov_path.read_text())
            assert prov["run"]["project"] == referent, (p, prov["run"]["project"])
            arm = RUNTIME_KEYS[str(prov["model"]["agent_runtime"]).strip().lower()]
            ckey, cshort, cdesc, pver = condition_of(prov)
            lver = re.search(r"generic-v(\d+)", label)
            doc = yaml.safe_load(p.read_text())
            hits = defaultdict(set)   # (ident key, role) -> YAML paths

            def walk(o, path):
                if isinstance(o, dict):
                    for k, v in o.items():
                        walk(v, path + [str(k)])
                elif isinstance(o, list):
                    for v in o:
                        walk(v, path + ["[]"])
                elif o is not None:
                    s = str(o)
                    for c in catalog:
                        if c["regex"].search(s):
                            hits[(c["key"], role_of(path))].add(".".join(path))
            walk(doc, [])
            sup = prov.get("canonical_superseded_by") or {}
            records.append({"path": str(p.relative_to(st.ROOT)), "method": method, "label": label,
                            "referent": referent, "arm": arm, "runtime": prov["model"]["agent_runtime"],
                            "condition_key": ckey, "condition_short": cshort, "condition_desc": cdesc,
                            "label_prompt_version": lver.group(1) if lver else "", "prompt_version": pver,
                            "generated": str(prov.get("record_generated_at", ""))[:10],
                            "canonical_superseded_by": sup.get("label", ""), "hits": hits})
    # nothing under the two method directories may escape the one-level glob above
    found = {str(p.relative_to(st.ROOT)) for m in METHODS for p in (CONCAT / m).rglob("VOICE*_d4d.yaml")}
    assert found == {r["path"] for r in records} | {e["path"] for e in excluded}, found ^ {r["path"] for r in records}
    # VOICE records in the other method directories: outside the record set, listed rather than dropped
    for p in sorted(CONCAT.rglob("VOICE*_d4d.yaml")):
        rel = p.relative_to(CONCAT)
        if rel.parts[0] not in METHODS:
            excluded.append({"path": str(p.relative_to(st.ROOT)), "reason": OUT_OF_SCOPE, "method": rel.parts[0]})
    return records, excluded


def main() -> int:
    st.apply()
    manifest = yaml.safe_load(MANIFEST.read_text())
    catalog = build_catalog(manifest, BUNDLE.read_text())
    ident = {c["key"]: c for c in catalog}
    records, excluded = load_records(catalog)
    n_ref = Counter(r["referent"] for r in records)
    referents = ["VOICE", "VOICE_PEDIATRIC"]

    # conditions: (condition key, arm), ordered by first generation date
    first = {}
    for r in records:
        k = (r["condition_key"], r["arm"])
        first[k] = min(first.get(k, "9999"), r["generated"] + r["label"])
    conds = sorted(first, key=lambda k: first[k])
    cinfo = {}
    for k in conds:
        rs = [r for r in records if (r["condition_key"], r["arm"]) == k]
        cinfo[k] = {"short": rs[0]["condition_short"], "desc": rs[0]["condition_desc"], "arm": k[1],
                    "n": Counter(r["referent"] for r in rs), "labels": sorted({r["label"] for r in rs}),
                    "dates": "/".join(sorted({r["label"][5:10] for r in rs}))}
    # a prompt path run under two different hashes gets a revision tag
    by_short = defaultdict(set)
    for k in conds:
        by_short[cinfo[k]["short"]].add(k[0])
    for k in conds:
        if len(by_short[cinfo[k]["short"]]) > 1:
            cinfo[k]["short"] += f"\nrev {k[0].split('@')[1][:4]}"

    # matrix counts
    count = Counter()
    ccount = Counter()
    for r in records:
        for (ik, role) in r["hits"]:
            count[(r["referent"], ik, role)] += 1
            ccount[(r["referent"], ik, role, r["condition_key"], r["arm"])] += 1

    main_rows, cond_rows, place_rows, rec_rows = [], [], [], []
    for ref in referents:
        for c in catalog:
            for role in ROLES:
                k = count[(ref, c["key"], role)]
                reason = flag_reason(ref, c, role)
                main_rows.append({"record_referent": ref, "n_records": n_ref[ref], "identifier": c["key"],
                                  "identifier_dataset": c["dataset"], "identifier_status": c["status"],
                                  "role": role, "records_with_identifier_in_role": k,
                                  "share": round(k / n_ref[ref], 4), "flagged_for_review": bool(reason and k),
                                  "flag_rule": reason})
                for ck in conds:
                    n = cinfo[ck]["n"][ref]
                    cond_rows.append({"record_referent": ref, "identifier": c["key"], "role": role,
                                      "condition": ck[0], "arm": ck[1], "condition_label": cinfo[ck]["short"].replace("\n", " "),
                                      "n_records": n, "records_with_identifier_in_role": ccount[(ref, c["key"], role) + ck] if n else "",
                                      "applicable": bool(n), "flagged_for_review": bool(reason)})
    for r in records:
        flagged = sorted(f"{ik}@{role}" for (ik, role) in r["hits"] if flag_reason(r["referent"], ident[ik], role))
        rec_rows.append({k: r[k] for k in ("path", "method", "label", "referent", "arm", "runtime", "condition_key",
                                           "condition_desc", "label_prompt_version", "prompt_version",
                                           "generated", "canonical_superseded_by")}
                        | {"n_flagged_cells": len(flagged), "flagged_cells": "; ".join(flagged), "excluded": ""})
        for (ik, role), paths in sorted(r["hits"].items()):
            place_rows.append({"path": r["path"], "referent": r["referent"], "condition_key": r["condition_key"],
                               "arm": r["arm"], "identifier": ik, "role": role,
                               "flagged_for_review": bool(flag_reason(r["referent"], ident[ik], role)),
                               "yaml_paths": "; ".join(sorted(paths))})
    keys = list(rec_rows[0])
    rec_rows += [{k: "" for k in keys} | {"path": e["path"], "method": e.get("method", ""), "excluded": e["reason"]}
                 for e in excluded]
    other = Counter(e["method"] for e in excluded if e["reason"] == OUT_OF_SCOPE)
    n_other = sum(other.values())
    # directory labels whose "-vN" disagrees with the prompt file the provenance records
    mism = Counter((r["label"].split("_")[0], r["label_prompt_version"], r["prompt_version"]) for r in records
                   if r["label_prompt_version"] and r["prompt_version"]
                   and r["label_prompt_version"] != r["prompt_version"])
    mism_txt = "; ".join(f"the {d} '-v{lv}' label ({n} records) ran generic prompt v{pv}"
                         for (d, lv, pv), n in sorted(mism.items()))

    # ---------------------------------------------------------------- drawing
    cmap_idx = lambda share: min(len(st.SEQ) - 1, max(0, int(round(share * (len(st.SEQ) - 1)))))

    def cell(ax, x, y, k, n, flagged, na=False, w=0.94, h=0.86):
        if na:
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=st.INK["surface"], edgecolor=st.INK["axis"],
                                   hatch=st.HATCH, linewidth=0.0, zorder=2))
            ax.text(x, y, "n/a", ha="center", va="center", fontsize=6.3, color=st.INK["secondary"], zorder=4)
            return
        if k:
            i = cmap_idx(k / n)
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=st.SEQ[i], linewidth=0, zorder=2))
            tc = st.INK["surface"] if i >= 7 else st.INK["primary"]
            ax.text(x, y, str(k), ha="center", va="center", fontsize=7.6, color=tc, zorder=4,
                    fontweight="bold" if flagged else "normal")
        else:
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=st.INK["mid"], linewidth=0, zorder=2))
            ax.text(x, y, "0", ha="center", va="center", fontsize=6.5, color=st.INK["muted"], zorder=4)
        if flagged and k:
            ax.add_patch(Rectangle((x - w / 2 + 0.05, y - h / 2 + 0.05), w - 0.1, h - 0.1, facecolor="none",
                                   edgecolor=FLAG_FILL, linewidth=2.0, zorder=3))

    fig = plt.figure(figsize=(11.6, 12.4))
    LABW = 8.2                       # label band, in cell units
    GAP = 0.9
    xs_a = {("VOICE", role): i for i, role in enumerate(ROLES)}
    xs_a.update({("VOICE_PEDIATRIC", role): len(ROLES) + GAP + i for i, role in enumerate(ROLES)})
    ncols_total = 2 * len(ROLES) + GAP
    x_lo, x_hi = -LABW, max(ncols_total, len(conds)) + 0.2

    # ---- panel A
    rows_a, y = [], 0.0
    groups = [("VOICE", f"Adult dataset: Bridge2AI-Voice (declared referent of the {n_ref['VOICE']} VOICE records)"),
              ("VOICE_PEDIATRIC", "Pediatric dataset: related but distinct (manifest scope); referent of the "
                                  f"{n_ref['VOICE_PEDIATRIC']} VOICE_PEDIATRIC records")]
    for ds, head in groups:
        rows_a.append(("head", head, y)); y += 1.05
        for c in catalog:
            if c["dataset"] == ds:
                rows_a.append(("row", c, y)); y += 1.0
        y += 0.35
    ya_max = y
    axA = fig.add_axes([0.02, 0.505, 0.96, 0.45])
    axA.set_xlim(x_lo, x_hi); axA.set_ylim(ya_max, -2.3); axA.axis("off")
    for ref in referents:
        x0 = xs_a[(ref, ROLES[0])]
        x1 = xs_a[(ref, ROLES[-1])]
        axA.text((x0 + x1) / 2, -2.05, f"in {REFERENT_TEXT[ref]} records (n = {n_ref[ref]})", ha="center",
                 va="bottom", fontsize=8.5, fontweight="bold", color=st.INK["primary"])
        axA.plot([x0 - 0.45, x1 + 0.45], [-1.55, -1.55], color=st.INK["axis"], linewidth=0.8)
        for role in ROLES:
            axA.text(xs_a[(ref, role)], -0.62, ROLE_LABEL[role], ha="center", va="bottom", fontsize=6.8,
                     color=st.INK["secondary"], linespacing=1.05)
    for kind, obj, yy in rows_a:
        if kind == "head":
            axA.text(-LABW, yy, obj, ha="left", va="center", fontsize=7.8, fontweight="bold", color=st.INK["primary"])
            continue
        c = obj
        axA.text(-LABW + 0.25, yy - 0.13, c["label"], ha="left", va="center", fontsize=7.6, color=st.INK["primary"])
        axA.text(-LABW + 0.25, yy + 0.27, f"{c['recog']}  [{c['src']}]", ha="left", va="center", fontsize=6.2,
                 color=st.INK["muted"])
        for ref in referents:
            for role in ROLES:
                k = count[(ref, c["key"], role)]
                cell(axA, xs_a[(ref, role)], yy, k, n_ref[ref], bool(flag_reason(ref, c, role)))
    axA.text(-LABW, -2.05, "A   Records carrying each identifier, by field role", ha="left", va="bottom",
             fontsize=9.5, fontweight="bold", color=st.INK["primary"])

    # ---- panel B: flagged cells by prompt condition
    flagged_cells = [(ref, c, role) for ref in referents for c in catalog for role in ROLES
                     if flag_reason(ref, c, role) and count[(ref, c["key"], role)]]
    any_flag = Counter()
    for r in records:
        if any(flag_reason(r["referent"], ident[ik], role) for (ik, role) in r["hits"]):
            any_flag[(r["referent"], r["condition_key"], r["arm"])] += 1
    rows_b = [("any", ref) for ref in referents if n_ref[ref]] + [("cell", fc) for fc in flagged_cells]
    axB = fig.add_axes([0.02, 0.125, 0.96, 0.36])
    yb_max = len(rows_b) + 0.6
    axB.set_xlim(x_lo, x_hi); axB.set_ylim(yb_max, -4.9); axB.axis("off")
    xs_b = {ck: i + 0.0 for i, ck in enumerate(conds)}
    for ck in conds:
        info = cinfo[ck]
        x = xs_b[ck]
        axB.add_patch(Rectangle((x - 0.17, -3.62), 0.34, 0.34, facecolor=st.ARM_COLOR[info["arm"]], linewidth=0))
        axB.text(x, -3.12, info["short"] + "\n" + info["dates"], ha="center", va="top", fontsize=6.5, color=st.INK["primary"], linespacing=1.05)
        ntxt = f"n={info['n']['VOICE']}" + (f"\n+{info['n']['VOICE_PEDIATRIC']} ped." if info["n"]["VOICE_PEDIATRIC"] else "")
        axB.text(x, -0.62, ntxt, ha="center", va="bottom", fontsize=6.3, color=st.INK["secondary"])
    for i, (kind, obj) in enumerate(rows_b):
        yy = i + 0.35
        if kind == "any":
            ref = obj
            axB.text(-LABW + 0.25, yy, f"{REFERENT_TEXT[ref]} records with any flagged placement",
                     ha="left", va="center", fontsize=7.4, color=st.INK["primary"], fontweight="bold")
            for ck in conds:
                n = cinfo[ck]["n"][ref]
                cell(axB, xs_b[ck], yy, any_flag[(ref,) + ck], n, False, na=not n)
            continue
        ref, c, role = obj
        dsname = REFERENT_TEXT[c["dataset"]]
        axB.text(-LABW + 0.25, yy, f"{dsname} {c['label'].split(',')[0]}  in  {ROLE_NAME[role]}"
                 + ("" if ref == "VOICE" else f"  ({REFERENT_TEXT[ref]} records)"),
                 ha="left", va="center", fontsize=7.2, color=st.INK["primary"])
        for ck in conds:
            n = cinfo[ck]["n"][ref]
            cell(axB, xs_b[ck], yy, ccount[(ref, c["key"], role) + ck], n, False, na=not n)
    y_sep = len([r for r in rows_b if r[0] == "any"]) - 0.13   # under the "any flagged placement" rows,
    axB.plot([-LABW + 0.25, len(conds) - 0.5], [y_sep, y_sep], color=st.INK["axis"], linewidth=0.6)  # labels to last column
    axB.text(-LABW, -4.75, "B   Flagged cells of A, split by prompt condition and arm (records per column)", ha="left", va="top",
             fontsize=9.5, fontweight="bold", color=st.INK["primary"])

    # ---- legend and notes
    axL = fig.add_axes([0.02, 0.034, 0.96, 0.085]); axL.axis("off"); axL.set_xlim(0, 100); axL.set_ylim(0, 10)
    lx = 0.3
    for j, share in enumerate([0.02, 0.25, 0.5, 0.75, 1.0]):
        axL.add_patch(Rectangle((lx + j * 2.1, 7.4), 2.0, 1.6, facecolor=st.SEQ[cmap_idx(share)], linewidth=0))
    axL.text(lx, 6.9, "shade: share of the records counted in that column (n above it; light = few, dark = all); number: records", ha="left", va="top",
             fontsize=6.8, color=st.INK["secondary"])
    axL.add_patch(Rectangle((lx + 13.0, 7.4), 2.0, 1.6, facecolor=st.INK["mid"], linewidth=0))
    axL.text(lx + 15.4, 8.2, "0 records", ha="left", va="center", fontsize=6.8, color=st.INK["secondary"])
    axL.add_patch(Rectangle((lx + 22.0, 7.4), 2.0, 1.6, facecolor=st.INK["surface"], edgecolor=st.INK["axis"],
                            hatch=st.HATCH, linewidth=0))
    axL.text(lx + 24.4, 8.2, "n/a: no records of that referent", ha="left", va="center", fontsize=6.8, color=st.INK["secondary"])
    axL.add_patch(Rectangle((lx + 40.0, 7.4), 2.0, 1.6, facecolor=st.SEQ[4], edgecolor=FLAG_FILL, linewidth=2.0))
    axL.text(lx + 42.4, 8.2, "flagged for review by a heuristic rule, not an established error",
             ha="left", va="center", fontsize=6.8, color=st.INK["secondary"])
    for j, arm in enumerate(["api", "agentic"]):
        axL.add_patch(Rectangle((lx + 77.0 + j * 11.5, 7.6), 1.1, 1.3, facecolor=st.ARM_COLOR[arm], linewidth=0))
        axL.text(lx + 78.5 + j * 11.5, 8.2, {"api": "API arm", "agentic": "agentic arm"}[arm], ha="left",
                 va="center", fontsize=6.8, color=st.INK["secondary"])
    n_flag_rec = sum(1 for r in rec_rows if not r["excluded"] and r["n_flagged_cells"])
    note = ("Flag rule (heuristic): the other dataset's identifier in a root, version, distribution or other structured field, or an "
            "earlier release of the record's own dataset in a root, distribution or other structured field. Earlier releases in "
            "version fields, related/external links and free text are not flagged. A flagged placement needs review: a record "
            "written to cover both cohorts, a release history or a raw-audio note can carry these identifiers legitimately. "
            f"{n_flag_rec} of {len(records)} records carry at least one flagged placement. Identifiers are matched by DOI, "
            "PhysioNet URL path or Synapse ID; bare version strings and software or publication DOIs are not counted; a record "
            "counts once per cell. Conditions follow each record's provenance prompt file and hash, not its directory label"
            + (f" ({mism_txt})" if mism_txt else "") + ". † no prompt file recorded; condition from provenance model.mode. "
            "[scope], [manifest], [bundle], [records only]: where each identifier was taken from. "
            + (f"Not included: {n_other} VOICE records in {len(other)} other method directories ("
               + ", ".join(f"{m} {n}" for m, n in sorted(other.items())) + ")." if n_other else ""))
    axL.text(lx, 5.3, textwrap.fill(note, 245), ha="left", va="top", fontsize=6.6, color=st.INK["secondary"],
             linespacing=1.3)

    fig.suptitle("VOICE records: where adult, pediatric and earlier-release identifiers are placed",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=0.985)
    basis = (f"Record set: {len(records)} VOICE full records (VOICE*_d4d.yaml) under claudecode_agent/ and claudecode_api/, "
             f"{n_ref['VOICE']} adult + {n_ref['VOICE_PEDIATRIC']} pediatric, gate_test excluded; "
             f"{n_other} in {len(other)} other method dirs not included; identifiers: source_manifest.yaml, VOICE bundle, records")
    ident_rows = [{"identifier": c["key"], "dataset": c["dataset"], "status": c["status"], "label": c["label"],
                   "pattern": c["rx"], "recognized_from": c["recognized_from"]} for c in catalog]
    role_rows = [{"role": r, "rule": ROLE_RULE[r], "order": i} for i, r in
                 enumerate(["text", "related", "root", "version", "dist", "other"])]
    cond_tbl = [{"condition": k[0], "arm": k[1], "label": cinfo[k]["short"].replace("\n", " "), "description": cinfo[k]["desc"],
                 "n_adult": cinfo[k]["n"]["VOICE"], "n_pediatric": cinfo[k]["n"]["VOICE_PEDIATRIC"],
                 "run_labels": "; ".join(cinfo[k]["labels"]),
                 "adult_records_any_flag": any_flag[("VOICE",) + k],
                 "pediatric_records_any_flag": any_flag[("VOICE_PEDIATRIC",) + k] if cinfo[k]["n"]["VOICE_PEDIATRIC"] else ""}
                for k in conds]
    st.save(fig, "fig13_identifier_roles",
            {"main": main_rows, "by_condition": cond_rows, "conditions": cond_tbl, "records": rec_rows,
             "placements": place_rows, "identifiers": ident_rows, "roles": role_rows}, basis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
