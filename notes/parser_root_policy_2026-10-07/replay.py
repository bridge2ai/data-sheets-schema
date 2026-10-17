"""Replay #4588 parser/builder consumers; retain failures as review evidence.

Run separately against each checkout with a new output directory. This replay
does not publish records, change source bundles, or claim source coverage.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import traceback
import zipfile

sys.dont_write_bytecode = True


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def load_hidden(source, name):
    path = source / ".claude/agents/scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location("replay_hidden_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_one(implementation, source_path, mapping_path, destination, validator,
            target_class):
    """Keep parse/build errors distinct from schema validation failures."""
    import yaml

    parser_class, mapping_class, builder_class = implementation
    result = {}
    log = io.StringIO()
    stage = "parse"
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            parser = parser_class(str(source_path))
            root = parser.get_root_dataset()
            result.update(parse="PASS", root_id=root.get("@id") if root else None,
                          root_selected=root is not None,
                          root_sha256=digest(encoded(root)))
            stage = "build"
            mapping = mapping_class(str(mapping_path))
            record = builder_class(mapping).build_dataset(parser)
            record_path = destination.with_suffix(".yaml")
            record_path.write_text(yaml.safe_dump(record, sort_keys=False,
                                                 allow_unicode=True),
                                   encoding="utf-8")
            result.update(build="PASS", record_sha256=digest(encoded(record)),
                          output_sha256=digest(record_path.read_bytes()),
                          field_count=len(record))
            stage = "validation"
            # Validate the written/read-back record, using the actual LinkML
            # schema. Pre-existing invalid legacy records are evidence, not a
            # reason to call this replay successful or silently skip validation.
            readback = yaml.safe_load(record_path.read_text(encoding="utf-8"))
            errors = [entry.message for entry in
                      validator.validate(readback, target_class).results]
            result.update(validation="FAIL" if errors else "PASS",
                          validation_errors=errors)
        except Exception as exc:
            result[stage] = "ERROR"
            result["error"] = {"stage": stage, "type": type(exc).__name__,
                               "message": str(exc)}
            traceback.print_exc(file=log)
    destination.with_suffix(".log").write_text(log.getvalue(), encoding="utf-8")
    write_json(destination.with_suffix(".result.json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.repo.resolve()
    out = args.output.resolve()
    if out == source or source in out.parents:
        parser.error("--output must be outside the inspected repository")
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(source / "src"))

    from data_sheets_schema.rocrate_map import FULL_SCHEMA, TARGET_CLASS
    from fairscape_integration.fairscape_to_d4d import record_validator
    from fairscape_integration.utils.d4d_builder import D4DBuilder
    from fairscape_integration.utils.mapping_loader import MappingLoader
    from fairscape_integration.utils.rocrate_parser import ROCrateParser

    implementations = {
        "packaged": (ROCrateParser, MappingLoader, D4DBuilder),
        "hidden": (load_hidden(source, "rocrate_parser").ROCrateParser,
                   load_hidden(source, "mapping_loader").MappingLoader,
                   load_hidden(source, "d4d_builder").D4DBuilder),
    }
    mapping = source / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"
    schema = source / FULL_SCHEMA
    validator = record_validator(str(schema))
    paths = {
        "CHORUS": "data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json",
        "VOICE": "data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json",
        "CM4AI_reduced": "data/ro-crate_packages/CM4AI/processed/CM4AI_crate_metadata_reduced.json",
        "VOICE_provenance": "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json",
    }
    inputs = {name: ((source / path).read_bytes(), {"path": path})
              for name, path in paths.items()}
    archive = source / "data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip"
    member = "cm4ai_release_metadata/ro-crate-metadata.json"
    with zipfile.ZipFile(archive) as bundle:
        inputs["CM4AI_original"] = (
            bundle.read(member), {"path": str(archive.relative_to(source)),
                                  "archive_sha256": digest(archive.read_bytes()),
                                  "member": member})

    code_paths = ["src/data_sheets_schema/rocrate_sources.py",
                  "src/data_sheets_schema/rocrate_map.py",
                  "src/fairscape_integration/fairscape_to_d4d.py"]
    code_paths += [prefix + name + ".py"
                   for prefix in ("src/fairscape_integration/utils/",
                                  ".claude/agents/scripts/")
                   for name in ("rocrate_parser", "mapping_loader", "d4d_builder")]
    summary = {
        "replay_sha256": digest(Path(__file__).read_bytes()),
        "mapping": {"path": str(mapping.relative_to(source)),
                    "sha256": digest(mapping.read_bytes())},
        "schema": {"path": str(FULL_SCHEMA), "sha256": digest(schema.read_bytes())},
        "code_sha256": {path: digest((source / path).read_bytes()) for path in code_paths},
        "inputs": {},
    }
    input_dir = out / "inputs"
    input_dir.mkdir()
    for name, (raw, binding) in inputs.items():
        original_path = input_dir / (name + ".json")
        original_path.write_bytes(raw)
        crate = json.loads(raw)
        graph = crate.get("@graph")
        # For JSON-LD's one-node-object graph, there is only one order; keep its
        # original shape to test the consumer's compatibility behavior (#4187).
        reversed_crate = dict(crate)
        if isinstance(graph, list):
            reversed_crate["@graph"] = list(reversed(graph))
        reverse_path = input_dir / (name + ".reversed.json")
        write_json(reverse_path, reversed_crate)
        entry = dict(binding, input_sha256=digest(raw),
                     graph_shape="array" if isinstance(graph, list) else "node object",
                     consumers={})
        for consumer, implementation in implementations.items():
            result = run_one(implementation, original_path, mapping,
                             out / (name + "_" + consumer), validator, TARGET_CLASS)
            reverse = run_one(implementation, reverse_path, mapping,
                              out / (name + "_" + consumer + "_reversed"),
                              validator, TARGET_CLASS)
            both_parsed = result.get("parse") == reverse.get("parse") == "PASS"
            both_built = result.get("build") == reverse.get("build") == "PASS"
            entry["consumers"][consumer] = {
                "original": result, "reversed": reverse,
                "reversal": {
                    "root_equal": (result["root_sha256"] == reverse["root_sha256"]
                                   if both_parsed else None),
                    "record_equal": (result["record_sha256"] == reverse["record_sha256"]
                                     if both_built else None),
                    "comparison": "exact structural equality, including list order",
                },
            }
        summary["inputs"][name] = entry
        # Keep completed input evidence if a later input cannot be read.
        write_json(out / "summary.json", summary)
    print(json.dumps({"output": str(out), "inputs": len(inputs),
                      "consumer_runs": len(inputs) * len(implementations) * 2}))


if __name__ == "__main__":
    main()
