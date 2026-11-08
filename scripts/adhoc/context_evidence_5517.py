"""Propose #5517 wording corrections from local bundles, 2026-11-08.

Inputs: committed contexts, source/chunk manifests and bundles. Outputs: bounded
context edits and reviewer table in the caller's scratch directory. No network.
Run with --apply PROJECT for the canary, then --apply all; default is read-only.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = "cf50d9a1c059f3b5030103378ccef33619475dde"
# project, predicate, flag, old phrase, proposed phrase, exact bundle snippet
CHANGES = [
    ("chorus", "data_processing", "SDOH", "SDOH", "OMOP", "Open source code to geocode OMOP Location entities via DeGauss"),
    ("cm4ai", "data_processing", "LLM-assisted", "LLM-assisted assembly naming", "assembly naming using large language models", "We systematically annotate this map, assisted by recent advances in large language models (LLMs)"),
    ("kids_first", "regulated_access", "FISMA", " under FISMA/NIST SP 800-53 security controls (c008)", "", "Comply with all applicable NIH data use policies and security requirements"),
    ("kids_first", "regulated_access", "HMB", " and adherence to study-specific consent groups such as GRU/HMB/DS,", " and adherence to participant consent and NIH policy,", "Approval only for research that aligns with participant consent and NIH policy"),
    ("kids_first", "data_collection", "WashU", "WashU McDonnell Genome Institute", "McDonnell Genome Institute at Washington University", "McDonnell Genome Institute at Washington University"),
    ("kids_first", "processing_software", "Recalibration", "GATK Base Quality Score Recalibration", "BAM output described as 'de-dupped and base score recalibrated'", "The resultant bam is de-dupped and base score recalibrated."),
    ("kids_first", "ml_training_dataset", "HPO-coded", "HPO-coded phenotypic", "phenotypic", "Phenotypes mapped to the Human Phenotype Ontology (HPO)"),
    ("voice", "shared_dataset", "TSVs", "TSVs", "TSV files", "all of the TSV data files have a data dictionary available with the data file"),
    ("voice_pediatric", "shared_dataset", "TSVs", "static acoustic feature TSVs", "static_features.tsv", "Each feature is present in the static_features.tsv file."),
    ("voice_pediatric", "data_processing", "Mel-filterbanks", "Mel-filterbanks", "Mel spectrograms", "torchaudio_mel_spectrograms.parquet (n=23533) contains Mel spectrograms of dimension 60xT generated with a 25ms window size, 10ms hop length, a 400-point FFT and 60 Mel bins."),
    ("ai_readi", "human_subjects", "IRB-approved", "IRB-approved human cohort", "human cohort with IRB approval", "AI- READI was approved by the Institutional Review Board"),
    ("ai_readi", "data_collection", "Vivosmart", "Vivosmart", "Vivosmart", "Garmin Vivosmart 5 for physical activity monitoring"),
    ("chorus", "processing_software", "OHDSI", "OHDSI", "OHDSI", "Workshops on using the OHDSI"),
    ("kids_first", "human_subjects", "RNA-seq", "RNA-seq", "RNA-Seq", "Kids First DRC RNA-Seq Workflow"),
    ("kids_first", "data_collection", "HGSC", "Baylor HGSC", "Baylor HGSC", "https://www.hgsc.bcm.edu/"),
    ("kids_first", "data_collection", "HudsonAlpha", "HudsonAlpha", "HudsonAlpha", 'sequencing: "HudsonAlpha Institute for Biotechnology"'),
    ("kids_first", "data_collection", "McDonnell", "McDonnell", "McDonnell", 'sequencing: "McDonnell Genome Institute at Washington University"'),
    ("kids_first", "data_processing", "GRCh38", "GRCh38", "hg38", "aligns/re-aligns to a bwa-indexed reference fasta, version hg38"),
    ("kids_first", "ml_training_dataset", "FHIR", "FHIR", "FHIR", "The Kids First DRC is structuring all Kids First data in a FHIR-based data service to make it more compatible with EHR data and other FHIR-based tools and data models."),
    ("voice", "human_subjects", "American", "five North American sites", "five recording sites", "There are five recording sites included in the dataset."),
    ("voice_pediatric", "data_processing", "MFCCs", "60 MFCCs", "Mel-frequency cepstrum coefficients of dimension 60xT", "torchaudio_mfcc.parquet (n=23533) contains Mel-frequency cepstrum coefficients of dimension 60xT using the same parameters as the mel spectrograms."),
]
WEAK = [
    ("chorus", "processing_software", "Open source code to geocode OMOP Location entities via DeGauss"),
    ("kids_first", "data_collection", "McDonnell Genome Institute at Washington University"),
    ("kids_first", "data_processing", "The Kids First Data Resource Center supports cross-study analysis of data files by using a set of standardized bioinformatic workflows."),
    ("kids_first", "processing_software", "The resultant bam is de-dupped and base score recalibrated."),
]


def sources(project):
    if project == "kids_first":
        manifest = ROOT / "notes/matched_cborg_2026-09-13/kids_first/chunks.yaml"
        directory = manifest.parent
    else:
        source_manifest = yaml.safe_load((ROOT / "data/preprocessed/source_manifest.yaml").read_text())
        assert project.upper() in source_manifest["projects"]
        manifest = ROOT / f"data/preprocessed/chunks/{project.upper()}_chunks.yaml"
        directory = ROOT / "data/preprocessed/concatenated"
    chunks = yaml.safe_load(manifest.read_text())
    bundle = directory / chunks["bundle"]
    return bundle, bundle.read_text(), chunks


def location(project, snippet):
    bundle, text, chunks = sources(project)
    assert snippet in text, (project, snippet)
    start = text.index(snippet)
    line = text[:start].count("\n") + 1
    end = line + snippet.count("\n")
    ids = [c["id"] for c in chunks["chunks"] if c["lines"][0] <= line and c["lines"][1] >= end]
    assert ids
    return f"{bundle.relative_to(ROOT)}:{line} ({','.join(ids)})", ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", default="none")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    originals = {}
    proposed = {}
    for path in sorted((ROOT / "data/context").glob("*_context.yaml")):
        project = path.stem.removesuffix("_context")
        originals[project] = subprocess.check_output(["git", "show", f"{BASE}:{path.relative_to(ROOT)}"], cwd=ROOT, text=True)
        proposed[project] = yaml.safe_load(originals[project])
    rows = []
    for project, predicate, flag, old, new, snippet in CHANGES:
        entry = proposed[project][predicate]
        assert old in entry["evidence"], (project, predicate, old)
        entry["evidence"] = entry["evidence"].replace(old, new)
        loc, ids = location(project, snippet)
        # Add the exact supporting chunk, keeping existing citations for other claims.
        tag = re.search(r"\[chunks: ([^]]+)\]", entry["evidence"])
        cited = sorted(set(tag[1].split(", ")) | set(ids))
        entry["evidence"] = entry["evidence"].replace(tag[0], f"[chunks: {', '.join(cited)}]", 1)
        disposition = "remove unsupported specific claim; high" if flag in {"FISMA", "HMB"} else "bundle wording; high literal / human entailment review pending"
        if flag == "HGSC":
            disposition = "add c003 partner URL; acronym expansion needs human authoring (medium)"
        if flag == "American":
            disposition = "remove geography pending release-specific human authoring; five-site snippet is supported"
        rows.append((project, predicate, flag, snippet, loc, disposition))
    for project, predicate, snippet in WEAK:
        entry = proposed[project][predicate]
        entry["evidence"] = re.sub(r"\bc002, ", "", entry["evidence"])
        loc, ids = location(project, snippet)
        tag = re.search(r"\[chunks: ([^]]+)\]", entry["evidence"])
        cited = sorted(set(tag[1].split(", ")) | set(ids))
        entry["evidence"] = entry["evidence"].replace(tag[0], f"[chunks: {', '.join(cited)}]", 1)
        rows.append((project, predicate, "near-empty c002", snippet, loc, "remove weak citation; high literal / human entailment review pending"))
    # OHDSI was specifically reported as present only outside cited chunks.
    entry = proposed["chorus"]["processing_software"]
    loc, ids = location("chorus", "Workshops on using the OHDSI")
    tag = re.search(r"\[chunks: ([^]]+)\]", entry["evidence"])
    entry["evidence"] = entry["evidence"].replace(tag[0], f"[chunks: {', '.join(sorted(set(tag[1].split(', ')) | set(ids)))}]", 1)
    for project, doc in proposed.items():
        text = originals[project]
        old_doc = yaml.safe_load(text)
        for predicate, entry in doc.items():
            old = old_doc[predicate]["evidence"]
            if old == entry["evidence"]:
                continue
            # Change evidence and its adjacent chunk comment only; preserve all decisions.
            old_line = next(line for line in text.splitlines() if line.startswith("  evidence:") and yaml.safe_load(line)["evidence"] == old)
            text = text.replace(old_line, "  evidence: " + json.dumps(entry["evidence"], ensure_ascii=False), 1)
            section_start = text.index(predicate + ":\n")
            section_end = text.find("\n\n", section_start)
            if section_end < 0:
                section_end = len(text)
            section = text[section_start:section_end]
            tag = re.search(r"\[chunks: ([^]]+)\]", entry["evidence"])
            section = re.sub(r"# chunks: \[[^]]+\]", f"# chunks: [{tag[1]}]", section)
            text = text[:section_start] + section + text[section_end:]
        assert {p: e['value'] for p, e in yaml.safe_load(text).items()} == {p: e['value'] for p, e in old_doc.items()}
        if args.apply in {project, "all"}:
            (ROOT / f"data/context/{project}_context.yaml").write_text(text)
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", "<br>")
    lines = ["# #5517 reviewer table — proposal for #2912", "", "All snippets are exact substrings of the declared bundles; locations are one-based. Values and owner decisions are unchanged. Removal does not assert that a claim is false, only that these bundles do not support the named formulation.", "", "| Context / term | Current string | Proposed string | Exact snippet | Location | Disposition / confidence |", "|---|---|---|---|---|---|"]
    for project, predicate, flag, snippet, loc, disposition in rows:
        old = yaml.safe_load(originals[project])[predicate]["evidence"]
        new = proposed[project][predicate]["evidence"]
        lines.append("| " + " | ".join(map(cell, (f"{project}.{predicate}: {flag}", old, new, snippet, loc, disposition))) + " |")
    (args.output / "reviewer-table.md").write_text("\n".join(lines) + "\n")
    print(f"Verified {len(rows)} review rows; apply={args.apply}")


if __name__ == "__main__":
    main()
