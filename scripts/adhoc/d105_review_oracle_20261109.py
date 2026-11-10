"""Independent PR review oracle retained for D105 regressions, 2026-11-09.

Source: scratch-pr5620-review/scripts/independent_oracle.py, PR #5620 review.
Input: a full-record mapping and explicitly supplied PairSchema. Output: expected
core-leaf pointers mapped to (rule, full-record pointers). This retains the
independent review oracle's algorithm; it imports no measurement implementation,
runs no corpus scan and writes nothing. Used by test_transformation_measure.py.
"""
from data_sheets_schema.derive_core import _distribution_slots


def esc(key):
    return str(key).replace("~", "~0").replace("/", "~1")


def leaves(value, path=""):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from leaves(child, path + "/" + esc(key))
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaves(child, path + "/" + str(index))
    else:
        yield path, value


def oracle(full, pair_schema):
    """Return target leaf -> (rule, source paths), independently of the trace."""
    ident = set(pair_schema.identity_slots)
    dslots = _distribution_slots(pair_schema)
    out = {}

    def copy_into(value, src, tgt, rule="copied"):
        for suffix, _ in leaves(value):
            out[tgt + suffix] = (rule, [src + suffix])

    for slot in ident:
        if slot in full:
            copy_into(full[slot], "/" + esc(slot), "/" + esc(slot))

    def project_resources(items, src, tgt):
        count = 0
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            source, target = f"{src}/{index}", f"{tgt}/{count}"
            got = False
            for key, value in item.items():
                if key in ident:
                    copy_into(value, f"{source}/{esc(key)}", f"{target}/{esc(key)}")
                    got = True
                elif key == "resources" and isinstance(value, list):
                    project_resources(value, f"{source}/resources", f"{target}/resources")
                    got = True
            if not got:
                out[target] = ("copied" if not item else "normalised", [source])
            count += 1
        if count == 0:
            out[tgt] = ("copied" if not items else "normalised", [src])

    if "resources" in full:
        project_resources(full["resources"], "/resources", "/resources")

    def dists(source, src, tgt):
        collections = source.get("file_collections")
        count = 0
        if isinstance(collections, list):
            for index, collection in enumerate(collections):
                if not isinstance(collection, dict):
                    continue
                entry = [slot for slot in dslots["collection"] if slot in collection]
                rename = "bytes" not in entry and collection.get("total_bytes") is not None
                if entry or rename:
                    for slot in entry:
                        copy_into(collection[slot], f"{src}/file_collections/{index}/{esc(slot)}",
                                  f"{tgt}/distributions/{count}/{esc(slot)}")
                    if rename:
                        copy_into(collection["total_bytes"], f"{src}/file_collections/{index}/total_bytes",
                                  f"{tgt}/distributions/{count}/bytes", rule="normalised")
                    count += 1
                for file_index, file in enumerate(collection.get("resources") or []):
                    if not isinstance(file, dict):
                        continue
                    selected = [slot for slot in dslots["file"] if slot in file]
                    if selected:
                        for slot in selected:
                            copy_into(file[slot], f"{src}/file_collections/{index}/resources/{file_index}/{esc(slot)}",
                                      f"{tgt}/distributions/{count}/{esc(slot)}")
                        count += 1
        # A projected resource's distributions use the last full object with
        # that string id, while its ordinary copied leaves retain their index.
        resources = source.get("resources") or []
        last = {}
        for index, resource in enumerate(resources):
            if isinstance(resource, dict) and isinstance(resource.get("id"), str):
                last[resource["id"]] = index
        count = 0
        for index, resource in enumerate(resources):
            if not isinstance(resource, dict):
                continue
            resource_id = resource.get("id") if "id" in ident else None
            if isinstance(resource_id, str) and resource_id in last:
                dists(resources[last[resource_id]], f"{src}/resources/{last[resource_id]}",
                      f"{tgt}/resources/{count}")
            count += 1

    dists(full, "", "")
    dialects = []
    for index, collection in enumerate(full.get("file_collections") or []):
        if isinstance(collection, dict):
            for file_index, file in enumerate(collection.get("resources") or []):
                if isinstance(file, dict) and file.get("dialect"):
                    dialects.append((f"/file_collections/{index}/resources/{file_index}/dialect", file["dialect"]))
    if dialects and all(value == dialects[0][1] for _, value in dialects):
        for suffix, _ in leaves(dialects[0][1]):
            out["/dialect" + suffix] = ("normalised", [path + suffix for path, _ in dialects])
    for constant in ("conforms_to_class", "conforms_to_schema"):
        out["/" + constant] = ("synthesised", [])
    return out
