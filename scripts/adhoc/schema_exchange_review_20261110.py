"""Audit frozen exchange artifacts and one tiny forward export, 2026-11-10.

Inputs: review checkout, existing pinned FAIRSCAPE models in the primary checkout.
Outputs: notes/schema_review_20261110/exchange_static.json and exchange_canary.json.
Serves: requested schema alignment review; source and schemas remain unchanged.
Run with the primary existing .venv Python; 30-second alarm, no network.
"""
from __future__ import annotations

import csv
import io
import json
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT.parent.parent / "data-sheets-schema"
OUT = ROOT / "notes/schema_review_20261110"
SHA = "7233f193ad102a8488b31ec7333662c8fefaa996"


def tracked(path: str) -> str:
    return subprocess.check_output(["git", "show", f"{SHA}:{path}"], cwd=ROOT, text=True)


def table(path: str):
    return list(csv.DictReader(io.StringIO("\n".join(
        line for line in tracked(path).splitlines() if not line.startswith("#")
    )), delimiter="\t"))


def save(name: str, data):
    dest = OUT / name
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n")
    assert dest.stat().st_size > 0


def main():
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("30-second cap")))
    signal.alarm(30)
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(ROOT / "src"), str(PRIMARY / "fairscape_models")]
    from linkml_runtime.utils.schemaview import SchemaView
    from rdflib import Graph, URIRef

    label = table("src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv")
    structural = table("data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv")
    by_name = {row["subject_id"].split(":", 1)[-1]: row for row in label}
    core = SchemaView(str(ROOT / "src/data_sheets_schema/schema/D4D_Core.yaml"))
    core_rows = []
    for cls in ("CoreDataset", "CoreDistribution", "CoreDatasetCollection"):
        for slot in core.class_induced_slots(cls):
            mapping = by_name.get(slot.name)
            core_rows.append({"class": cls, "slot": slot.name,
                              "range": str(slot.range), "slot_uri": str(slot.slot_uri),
                              "comprehensive_status": mapping.get("mapping_status") if mapping else "absent",
                              "comprehensive_object": mapping.get("object_id") if mapping else None})
    ttl = Graph().parse(data=tracked("src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl"), format="turtle")
    predicates = {"http://www.w3.org/2004/02/skos/core#" + x for x in
                  ("exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch")}
    save("exchange_static.json", {"source_sha": SHA, "comprehensive_rows": len(label),
        "mapping_status_counts": dict(Counter(r["mapping_status"] for r in label)),
        "structural_rows": len(structural), "ttl_mapping_triples": sum(str(p) in predicates for _, p, _ in ttl),
        "core_induced_slots": dict(Counter(r["class"] for r in core_rows)),
        "core_rows": core_rows})

    from fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter
    import fairscape_integration.d4d_to_fairscape as exporter
    import fairscape_models.rocrate as model_module
    record = {"id": "https://example.org/review/dataset", "title": "Exchange review canary",
              "description": "Fictional record for a bounded offline export check.",
              "license": "CC0-1.0", "keywords": ["synthetic"],
              "creators": [{"principal_investigator": {"id": "https://example.org/person/a", "name": "Example Scientist"}}],
              "known_limitations": [{"limitation_description": "Synthetic only."}],
              "distributions": [{"path": "data.csv", "format": "CSV", "conforms_to": "BIDS", "conforms_to_standard": ["BIDS"]}]}
    converter = D4DToFairscapeConverter()
    model = converter.convert(record)
    wire = json.loads(model.model_dump_json(by_alias=True, exclude_none=True))
    root = next(x for x in wire["@graph"] if x["@id"] == "./")
    graph = Graph().parse(data=json.dumps(wire), format="json-ld", publicID="https://example.org/review/")
    descriptor = URIRef("https://example.org/review/ro-crate-metadata.json")
    valid, errors = converter.validate(model)
    save("exchange_canary.json", {"source_sha": SHA, "elapsed_seconds": time.monotonic()-started,
        "exporter_file": exporter.__file__, "model_file": model_module.__file__,
        "model_git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PRIMARY/"fairscape_models", text=True).strip(),
        "input": record, "input_schema_validation": "not run; field shapes checked against current Core source",
        "wire": wire, "model_valid": valid, "model_errors": errors,
        "checks": {"datePublished_present": "datePublished" in root,
                   "author": root.get("author"), "hasPart": root.get("hasPart"),
                   "known_limitation_text": root.get("rai:dataLimitations"),
                   "descriptor_conformance_predicates": sorted(str(p) for _, p, _ in graph.triples((descriptor, None, None)) if "conforms" in str(p)),
                   "source_dataset_id_present_in_wire": record["id"] in json.dumps(wire),
                   "distribution_standard_present_in_wire": "BIDS" in json.dumps(wire)},
        "route_evidence": converter.route_evidence,
        "limits": "One forward API call, not CLI, reverse conversion, SHACL conformance or broad coverage; no network."})
    print(json.dumps({"elapsed_seconds": time.monotonic()-started, "outputs": [str(OUT/"exchange_static.json"), str(OUT/"exchange_canary.json")], "model_valid": valid, "checks": json.loads((OUT/"exchange_canary.json").read_text())["checks"]}, indent=2))


if __name__ == "__main__":
    main()
