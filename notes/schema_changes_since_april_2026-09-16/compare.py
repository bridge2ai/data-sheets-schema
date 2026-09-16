"""Reproduce the April-to-September schema inventory without changing inputs.

Run with the repository's Python environment from any checkout containing the
three commits. Snapshots and compiled validators go in a temporary directory;
only the evidence JSON is written beside this script. No network/model calls.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import tempfile

import yaml
from jsonschema.validators import validator_for
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.utils.schemaview import SchemaView


REVISIONS = {
    "generation_2026_04_10": "9912ac2379b1a5b747c6b3941a32a18968dbd07d",
    "poster_2026_04_28": "e141852f532e6a0cea47992ffe9afc0f20a7c6a5",
    "current_2026_09_16": "a9c8bc05f1353206733afca207c80085547c1700",
}
SCHEMA_DIR = "src/data_sheets_schema/schema"
ROOTS = {"full": ("data_sheets_schema.yaml", "Dataset"),
         "core": ("data_sheets_schema_core.yaml", "CoreDataset")}
STRUCTURAL = {
    "range", "required", "recommended", "multivalued", "inlined", "inlined_as_list",
    "identifier", "key", "pattern", "minimum_value", "maximum_value", "minimum_cardinality",
    "maximum_cardinality", "equals_string", "equals_number", "equals_expression",
    "any_of", "all_of", "none_of", "exactly_one_of", "ifabsent", "readonly",
    "values_from", "bindings", "enum_range", "structured_pattern",
}
MAPPINGS = {"slot_uri", "class_uri", "exact_mappings", "close_mappings",
            "broad_mappings", "narrow_mappings", "related_mappings", "meaning"}


def git(*args):
    return subprocess.check_output(["git", *args])


def primitive(value):
    return json.loads(json.dumps(value, default=str))


def object_dict(value):
    return primitive(json_dumper.to_dict(value))


def changes(before, after, path=()):
    if isinstance(before, dict) and isinstance(after, dict):
        out = []
        for key in sorted(before.keys() | after.keys()):
            if key not in before:
                out.append({"path": [*path, key], "change": "added", "after": after[key]})
            elif key not in after:
                out.append({"path": [*path, key], "change": "removed", "before": before[key]})
            else:
                out.extend(changes(before[key], after[key], (*path, key)))
        return out
    return ([] if before == after else
            [{"path": list(path), "change": "changed", "before": before, "after": after}])


def view_inventory(path, root_class):
    sv = SchemaView(str(path))
    classes = sv.all_classes()
    fields = {}
    for name in sorted(classes):
        fields[name] = {
            str(slot.name): {k: v for k, v in object_dict(slot).items()
                             if k not in {"from_schema", "owner", "domain_of", "name", "alias"}}
            for slot in sv.class_induced_slots(name)
        }
    return {
        "root_class": root_class,
        "declared_version": str(sv.schema.version) if sv.schema.version else None,
        "classes": sorted(classes),
        "class_hierarchy": {name: {k: v for k, v in object_dict(cls).items()
                                    if k in {"is_a", "mixins", "abstract", "mixin", "class_uri"}}
                            for name, cls in classes.items()},
        "global_slots": sorted(sv.all_slots(attributes=False)),
        "root_fields": sorted(fields[root_class]),
        "fields": fields,
        "enums": {name: object_dict(enum) for name, enum in sv.all_enums().items()},
        "types": {name: object_dict(typ) for name, typ in sv.all_types().items()},
        "prefixes": {str(name): str(uri) for name, uri in sv.namespaces().items()},
    }


def compare_views(before, after):
    common = set(before["fields"]) & set(after["fields"])
    field_changes = []
    for cls in sorted(common):
        for entry in changes(before["fields"][cls], after["fields"][cls], (cls,)):
            prop = entry["path"][2] if len(entry["path"]) > 2 else None
            entry["category"] = ("field membership" if prop is None else
                                 "structure/constraints" if prop in STRUCTURAL else
                                 "semantic mapping" if prop in MAPPINGS else
                                 "guidance/metadata")
            field_changes.append(entry)
    return {
        "classes_added": sorted(set(after["classes"]) - set(before["classes"])),
        "classes_removed": sorted(set(before["classes"]) - set(after["classes"])),
        "new_class_fields": {name: after["fields"][name] for name in sorted(
            set(after["classes"]) - set(before["classes"]))},
        "root_fields_added": sorted(set(after["root_fields"]) - set(before["root_fields"])),
        "root_fields_removed": sorted(set(before["root_fields"]) - set(after["root_fields"])),
        "class_hierarchy_changes": changes(before["class_hierarchy"], after["class_hierarchy"]),
        "field_change_counts": dict(Counter(c["category"] for c in field_changes)),
        "field_changes": field_changes,
        "enum_changes": changes(before["enums"], after["enums"]),
        "type_changes": changes(before["types"], after["types"]),
        "prefix_changes": changes(before["prefixes"], after["prefixes"]),
    }


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate key {key!r} on line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validation_error(error):
    return {
        "path": "/" + "/".join(map(str, error.absolute_path)),
        "validator": error.validator,
        "message": error.message,
        "schema_path": list(error.absolute_schema_path),
        "causes": [validation_error(child) for child in error.context],
    }


def main():
    result = {
        "revisions": REVISIONS,
        "toolchain": {p: version(p) for p in ("linkml", "linkml-runtime", "jsonschema", "PyYAML")},
        "method": "Effective imported source schemas, class-induced fields, fixed current compiler for all three revisions; historical runtime is not recreated. Source changes exclude generated *_all.yaml expansions, which remain in the hash manifests. Induced-field counts repeat inherited changes once per class.",
        "snapshots": {}, "comparisons": {}, "april_records": [],
    }
    inventories = {}
    sources = {}
    with tempfile.TemporaryDirectory(prefix="d4d-schema-comparison-") as tmp:
        for label, commit in REVISIONS.items():
            folder = Path(tmp) / label
            folder.mkdir()
            files = git("ls-tree", "-r", "--name-only", commit, SCHEMA_DIR).decode().splitlines()
            manifest = {}
            sources[label] = {}
            for name in files:
                content = git("show", f"{commit}:{name}")
                (folder / Path(name).name).write_bytes(content)
                manifest[name] = hashlib.sha256(content).hexdigest()
                if not name.endswith("_all.yaml"):
                    sources[label][Path(name).name] = primitive(yaml.load(content, Loader=UniqueLoader))
            inventories[label] = {}
            snapshots = {"files_sha256": manifest, "views": {}}
            for kind, (filename, root_class) in ROOTS.items():
                inventory = view_inventory(folder / filename, root_class)
                inventories[label][kind] = inventory
                snapshots["views"][kind] = {
                    "declared_version": inventory["declared_version"],
                    "classes": inventory["classes"],
                    "root_fields": inventory["root_fields"],
                    "counts": {"classes": len(inventory["classes"]),
                               "global_slots": len(inventory["global_slots"]),
                               "root_fields": len(inventory["root_fields"]),
                               "enums": len(inventory["enums"]),
                               "enum_values": sum(len(e.get("permissible_values", {})) for e in inventory["enums"].values()),
                               "class_field_pairs": sum(map(len, inventory["fields"].values()))},
                }
                print(label, kind, snapshots["views"][kind]["counts"], flush=True)
                compiled = json.loads(JsonSchemaGenerator(
                    str(folder / filename), top_class=root_class, not_closed=False,
                    include_range_class_descendants=True).serialize())
                validator_type = validator_for(compiled)
                validator_type.check_schema(compiled)
                validator = validator_type(compiled, format_checker=validator_type.FORMAT_CHECKER)
                for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
                    method = "claudecode_agent" + ("_core" if kind == "core" else "")
                    record_path = f"data/d4d_concatenated/{method}/{project}_d4d{'_core' if kind == 'core' else ''}.yaml"
                    raw = git("show", f"{REVISIONS['generation_2026_04_10']}:{record_path}")
                    data = yaml.load(raw, Loader=UniqueLoader)
                    # JSON Schema consumes JSON. Dates parsed by PyYAML are
                    # represented as the corresponding ISO strings in all runs.
                    data = json.loads(json.dumps(data, default=lambda v: v.isoformat() if isinstance(v, (date, datetime)) else str(v)))
                    errors = sorted(validator.iter_errors(data), key=lambda e: (tuple(map(str, e.absolute_path)), e.message))
                    result["april_records"].append({
                        "schema_revision": label, "kind": kind, "record": record_path,
                        "record_sha256": hashlib.sha256(raw).hexdigest(),
                        "valid": not errors,
                        "errors": [validation_error(error) for error in errors],
                    })
                    print("  ", project, "valid" if not errors else f"{len(errors)} errors", flush=True)
            result["snapshots"][label] = snapshots
        pairs = [("generation_2026_04_10", "poster_2026_04_28"),
                 ("generation_2026_04_10", "current_2026_09_16"),
                 ("poster_2026_04_28", "current_2026_09_16")]
        for old, new in pairs:
            result["comparisons"][f"{old}..{new}"] = {
                kind: compare_views(inventories[old][kind], inventories[new][kind]) for kind in ROOTS}
            result["comparisons"][f"{old}..{new}"]["source_changes"] = changes(sources[old], sources[new])
    target = Path(__file__).with_name("evidence.json")
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(target, flush=True)


if __name__ == "__main__":
    main()
