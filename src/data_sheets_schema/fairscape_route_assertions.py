"""Finite converter assertions for #4046; no schema or mapping-table policy.

The converter supplies its selected root. Evidence describes parsed assertions
and observed output retention, not the truth of assertions or semantic coverage.
Only consulted values are snapshotted, following ``parent_evidence``.
"""
from __future__ import annotations

import hashlib
import json
import re

from data_sheets_schema.rocrate_assertions import HUMAN_KEYS, human_subject_record
from data_sheets_schema.rocrate_parent_admission import snapshot
from data_sheets_schema.rocrate_sources import _type_matches


ROUTES = {
    "citation": "citation",
    "rai:dataManipulationProtocol": "cleaning_strategies",
    "funder": "funders",
    "humanSubjects": "human_subject_research",
    "humanSubjectResearch": "human_subject_research",
    "completeness": None,
    "dataGovernanceCommittee": "data_governance",
    "rai:personalSensitiveInformation": "sensitive_elements",
    "rai:dataCollection": "collection_mechanisms",
    "rai:dataSocialImpact": "future_use_impacts",
    "rai:dataAnnotationProtocol": "labeling_strategies",
    "rai:dataAnnotationPlatform": "labeling_strategies",
    "rai:annotationsPerItem": "labeling_strategies",
}
CARRIERS = {
    "d4d:confidentialElements": "confidential_elements",
    "d4d:acquisitionMethods": "acquisition_methods",
    "d4d:dataProtectionImpacts": "data_protection_impacts",
    "d4d:labelingStrategies": "labeling_strategies",
}
LIST_TARGETS = frozenset(("funders", "cleaning_strategies", "sensitive_elements",
                         "collection_mechanisms", "future_use_impacts",
                         "labeling_strategies", *CARRIERS.values()))
PROPERTY_VALUES = {
    "Citation": "citation", "Cleaning Strategies": "cleaning_strategies",
    "Funders": "funders", "Human Subject": "human_subject_research",
    "Human Subject Research": "human_subject_research",
    "Data Governance": "data_governance",
    "Data Governance Committee": None, "Completeness": None,
}


def pointer_key(key):
    return key.replace("~", "~0").replace("/", "~1")


def property_value_target(name):
    """The finite covered subset of the converter's existing name resolution."""
    if type(name) is not str:
        return False, None
    if name in PROPERTY_VALUES:
        return True, PROPERTY_VALUES[name]
    slot = name.lower().replace(" ", "_")
    if slot in LIST_TARGETS or slot in ("citation", "human_subject_research", "data_governance"):
        return True, slot
    if slot in ("completeness", "data_governance_committee"):
        return True, None
    return False, None


def evidence_state(direction, kind=None):
    return {"contract": "fairscape-declared-assertions-v1", "direction": direction,
            "input": {"kind": kind, "source_sha256": None,
                      "source_bytes": None, "source_path": None},
            "status": "pending", "assertions": [], "error": None}


def dataset_digest(record):
    """Bind the complete returned Dataset without archiving it in evidence."""
    encoded = json.dumps(record, ensure_ascii=True, allow_nan=False,
                         sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def same_json(left, right):
    """Exact JSON types, including boolean/number and signed float zero."""
    return dataset_digest({"value": left}) == dataset_digest({"value": right})


def canonical_count(value):
    """Exact integers or reversible ASCII decimal strings; never a bool."""
    if type(value) is int:
        return value
    if type(value) is str and re.fullmatch(r"(?:0|-?[1-9][0-9]*)", value):
        try:
            parsed = int(value)
            if str(parsed) == value:
                return parsed
        except (ValueError, OverflowError):
            pass
    return None


def annotation_projection(groups):
    """Finite wire summary; multiple groups never acquire a shared count."""
    result = {}
    if type(groups) is not list or not groups or not all(type(g) is dict for g in groups):
        return result
    if len(groups) == 1:
        item = groups[0]
        if type(item.get("data_annotation_protocol")) is str:
            result["rai:dataAnnotationProtocol"] = item["data_annotation_protocol"]
        if type(item.get("data_annotation_platform")) is str:
            result["rai:dataAnnotationPlatform"] = [item["data_annotation_platform"]]
        count = item.get("annotations_per_item")
        if type(count) is int:
            try:
                result["rai:annotationsPerItem"] = str(count)
            except (ValueError, OverflowError):
                pass
    elif all(set(g) == {"data_annotation_platform"}
             and type(g["data_annotation_platform"]) is str for g in groups):
        result["rai:dataAnnotationPlatform"] = [g["data_annotation_platform"] for g in groups]
    return result


def failed(state, exc):
    state["status"] = "failed"
    state["error"] = type(exc).__name__ + ": " + str(exc)
    for row in state["assertions"]:
        if row["decision"] == "constructed" or row.get("construction_observed"):
            row["retention"] = "unknown_failed"
            row["final_value"] = None


def assertion(source, pointer, present, raw, target):
    return {"source": source, "source_pointer": pointer,
            "presence": "missing" if not present else "null" if raw is None else "present",
            "raw": snapshot(raw) if present else None, "target": target,
            "decision": "unplaced" if present else "missing",
            "reason": "no supported projection" if present else "source key absent",
            "retention": "not_constructed", "final_value": None}


class DeclaredAssertions:
    """One reverse conversion's thirteen routes and finite read evidence."""

    def __init__(self, state, root, graph, root_index):
        self.state = state
        state.update(root_id=snapshot(root.get("@id")), root_graph_index=root_index)
        self.rows = state["assertions"]
        self.direct = {}
        self.candidates = []
        self.tracks = []
        self.legacy_queues = {}
        self.legacy = {}
        self.scalar_bindings = {}
        self.list_bindings = {}
        self.carrier_rows = {}
        self.carrier_tracks = []
        prefix = "/@graph/" + str(root_index) + "/"
        for key, target in ROUTES.items():
            row = assertion(key, prefix + pointer_key(key), key in root, root.get(key), target)
            self.rows.append(row)
            self.direct[key] = row
        for key in HUMAN_KEYS:
            if key not in self.direct:
                row = assertion(key, prefix + pointer_key(key), key in root,
                                root.get(key), "human_subject_research")
                self.rows.append(row)
                self.direct[key] = row

        for key, target in CARRIERS.items():
            if key in root:
                row = assertion(key, prefix + pointer_key(key), True, root[key], target)
                self.rows.append(row)
                self.carrier_rows[key] = row

        # These candidates still use the pre-existing fitter and priority rules.
        # Record their full source objects, not reconstructed names/values.
        if "d4d:humanSubject" in root:
            row = assertion("d4d:humanSubject", prefix + "d4d:humanSubject", True,
                            root["d4d:humanSubject"], "human_subject_research")
            row.update(decision="legacy", reason="existing alias candidate; canonical assertion takes priority")
            self.rows.append(row)
            self._legacy_row(row, "d4d:humanSubject")
        properties = root.get("additionalProperty")
        if properties is not None:
            for i, item in enumerate(properties if type(properties) is list else [properties]):
                covered, target = property_value_target(item.get("name")) if type(item) is dict else (False, None)
                if covered:
                    name = item["name"]
                    row = assertion("additionalProperty: " + name,
                                    prefix + "additionalProperty" + ("/" + str(i) if type(properties) is list else ""), True,
                                    item, target)
                    row.update(decision="legacy", reason="existing PropertyValue fitter; no per-occurrence retention inferred")
                    self.rows.append(row)
                    if not item.get("@type") or _type_matches(item, "PropertyValue"):
                        self._legacy_row(row, "additionalProperty[" + name + "]")
                    else:
                        row["reason"] = "existing parser refuses a value explicitly typed other than PropertyValue"

        self._text("citation", root.get("citation"))
        self._units("rai:dataManipulationProtocol", root.get("rai:dataManipulationProtocol"), "cleaning_details")
        self._units("funder", root.get("funder"), "grantor", references=True)
        self._text("dataGovernanceCommittee", root.get("dataGovernanceCommittee"), member="description")
        self._units("rai:personalSensitiveInformation", root.get("rai:personalSensitiveInformation"), "sensitivity_details")
        self._text("rai:dataCollection", root.get("rai:dataCollection"), member="mechanism_details", listed=True)
        self._text("rai:dataSocialImpact", root.get("rai:dataSocialImpact"), member="impact_details", listed=True)
        completeness = self.direct["completeness"]
        if completeness["presence"] != "missing":
            completeness.update(decision="deferred", reason="no Dataset completeness slot; no metric inferred")

        human, reason = human_subject_record(root, graph)
        if human is not None:
            human_rows = [self.direct[key] for key in HUMAN_KEYS
                          if key in root and root[key] is not None
                          and not (type(root[key]) in (str, list, dict) and not root[key])
                          and not (type(root[key]) is str and not root[key].strip())]
            # Keep every graph candidate consulted by explicit IRB identity,
            # including duplicate IDs which the approved helper refuses.
            irbs = root.get("irb")
            irbs = irbs if type(irbs) is list else [irbs]
            identifiers = []
            for value in irbs:
                identifier = value.get("@id") if type(value) is dict else value
                if type(identifier) is str and identifier.strip():
                    identifiers.append(identifier)
            for i, node in enumerate(graph):
                if type(node) is dict and node.get("@id") in identifiers:
                    row = assertion("irb.referenced_entity", "/@graph/" + str(i), True,
                                    node, "human_subject_research")
                    self.rows.append(row)
                    human_rows.append(row)
            self._candidate(human_rows, "human_subject_research", human, reason)

    def _legacy_row(self, row, source):
        token = len(self.legacy)
        self.legacy[token] = {"row": row, "units": {}, "omitted": False,
                              "admitted": False, "shaped": False}
        self.legacy_queues.setdefault(source, []).append(token)

    def before_place(self, slot, record, origin, rivals):
        order = [(origin.get(slot), record.get(slot))] + list(rivals.get(slot, []))
        return record.get(slot), origin.get(slot), slot in record, order

    def after_place(self, source, slot, value, before, record, origin, rivals):
        """Join actual old fitter admission without changing its source labels.

        Scalar candidates are unique after the existing duplicate check. Lists
        retain their actual input-position ownership; a later equal occurrence
        cannot claim an earlier occurrence's output merely by equality.
        """
        queue = self.legacy_queues.get(source, [])
        token = queue.pop(0) if queue else None
        state = self.legacy.get(token)
        if state is not None and state["row"]["target"] is None:
            state["row"]["reason"] = "existing fitter has no Dataset target for this occurrence"
            return
        if slot not in LIST_TARGETS and slot not in ("citation", "human_subject_research", "data_governance"):
            return
        if value in (None, '', [], {}):
            if state is not None:
                state["row"]["reason"] = "existing fitter does not construct an empty candidate"
            return
        if slot not in LIST_TARGETS:
            key = slot, source, id(value)
            actual = [(origin.get(slot), record.get(slot))] + list(rivals.get(slot, []))
            if state is not None:
                state["admitted"] = True
                old_position = next((i for i, (s, v) in enumerate(before[3]) if s == source and v is value), None)
                new_position = next((i for i, (s, v) in enumerate(actual) if s == source and v is value), None)
                moved_forward = old_position is not None and new_position is not None and new_position < old_position
                if new_position is not None and (key not in self.scalar_bindings or moved_forward):
                    self.scalar_bindings[key] = (value, token)
                    state["row"]["reason"] = "actual legacy candidate admitted; final settlement determines retention"
                else:
                    state["omitted"] = True
                    state["row"]["reason"] = "existing fitter discarded this redundant occurrence"
            return
        current = record.get(slot)
        previous, _, existed, _ = before
        if existed and current is previous:
            if state is not None:
                state.update(admitted=True, omitted=True)
                state["row"]["reason"] = "existing fitter discarded this redundant occurrence"
            return
        previous_units = previous if type(previous) is list else [previous]
        current_units = current if type(current) is list else [current]
        values = value if type(value) is list else [value]
        old = self.list_bindings.get((slot, id(previous))) if existed else None
        owners = list(old[1]) if old is not None and old[0] is previous else [None] * (len(previous_units) if existed else 0)
        if not existed:
            owners = [(token, i) if token is not None else None for i in range(len(current_units))]
        else:
            # _place keeps its complete old prefix and appends only the actual
            # nonduplicate new units. Identity joins those units to this source.
            for unit in current_units[len(previous_units):]:
                index = next(i for i, item in enumerate(values) if item is unit)
                owners.append((token, index) if token is not None else None)
        self.list_bindings[(slot, id(current))] = (current, owners)
        if state is not None:
            admitted = sum(owner is not None and owner[0] == token for owner in owners)
            state.update(admitted=True, omitted=admitted < len(values))
            state["row"]["reason"] = "actual legacy list occurrences admitted; duplicates follow the existing fitter"
            for owner in owners:
                if owner is not None and owner[0] == token:
                    state["units"].setdefault(owner[1], None)

    def object_shaped(self, slot, raw, index, obj, lost):
        """Called at the genuine per-item shaping boundary for two list slots."""
        binding = self.list_bindings.get((slot, id(raw)))
        if binding is None or binding[0] is not raw or index >= len(binding[1]):
            return
        owner = binding[1][index]
        if owner is None:
            return
        token, occurrence = owner
        state = self.legacy[token]
        state["shaped"] = True
        state["units"][occurrence] = (obj, snapshot(obj), bool(lost)) if obj else None
        if obj:
            state["row"]["construction_observed"] = True

    def scalar_shaped(self, slot, source, raw, shaped, lost):
        listing = self.list_bindings.get((slot, id(raw)))
        if listing is not None and listing[0] is raw:
            for owner in listing[1]:
                if owner is not None:
                    self.legacy[owner[0]]["shaped"] = True
            return
        binding = self.scalar_bindings.get((slot, source, id(raw)))
        if binding is None or binding[0] is not raw:
            return
        state = self.legacy[binding[1]]
        state["shaped"] = True
        state["source"] = source
        state["units"][0] = ((shaped, snapshot(shaped), bool(lost))
                             if shaped is not None else None)
        if shaped is not None:
            state["row"]["construction_observed"] = True
            # A canonical candidate can later queue this already-fitted value
            # as a rival. A genuine retry must retain the same source lineage.
            self.scalar_bindings[(slot, source, id(shaped))] = (shaped, binding[1])

    def _finish_legacy(self, record, origin):
        for state in self.legacy.values():
            row = state["row"]
            target = row["target"]
            units = state["units"]
            constructed = [unit for unit in units.values() if unit is not None]
            if not constructed:
                row["retention"] = ("not_retained" if state["admitted"] and not state["shaped"]
                                    else "not_constructed")
                if state["admitted"] and not state["shaped"] and not state["omitted"]:
                    row["reason"] += "; superseded without shaping; candidate validity was not evaluated"
                elif state["shaped"]:
                    row["reason"] += "; genuine shaping produced no retained constructor"
                continue
            final = record.get(target)
            outputs = final if target in LIST_TARGETS and type(final) is list else [final]
            if target not in LIST_TARGETS and origin.get(target) != state.get("source"):
                outputs = []
            intact = surviving = 0
            for obj, expected, lost in constructed:
                present = any(output is obj for output in outputs)
                surviving += present
                intact += present and not lost and same_json(obj, expected)
            row["retention"] = ("retained" if intact == len(units) and not state["omitted"]
                                else "partial" if surviving else "not_retained")
            row["reason"] += "; final retention joined to actual produced occurrences"

    def _candidate(self, rows, slot, value, reason):
        for row in rows:
            row.update(decision="constructed", reason=reason)
        self.candidates.append((rows, slot, value))

    def _text(self, key, value, member=None, listed=False):
        if type(value) is str:
            constructed = {member: value} if member else value
            self._candidate([self.direct[key]], ROUTES[key],
                            [constructed] if listed else constructed,
                            "whole source string; no splitting or inferred details")

    def _units(self, key, value, member, references=False):
        if self.direct[key]["presence"] == "missing":
            return
        values = value if type(value) is list else [value]
        objects, units = [], []
        for i, item in enumerate(values):
            text = item if type(item) is str else None
            if (references and type(item) is dict and set(item) == {"@id"}
                    and type(item["@id"]) is str and item["@id"].strip()):
                text = item["@id"]
            accepted = text is not None
            units.append({"index": i if type(value) is list else None,
                          "decision": "constructed" if accepted else "unplaced"})
            if accepted:
                objects.append({member: text})
        self.direct[key]["units"] = units
        if objects:
            self._candidate([self.direct[key]], ROUTES[key], objects,
                            "immediate supported units in source order, including duplicates; unsupported units remain raw evidence")

    def _carriers(self, record, origin, dropped, prepare_carrier):
        """Place explicit structured candidates for genuine final validation."""
        fitted_labeling = []
        for key, row in self.carrier_rows.items():
            raw, slot = row["raw"], row["target"]
            values = raw if type(raw) is list else [raw]
            row["units"] = [{"index": i if type(raw) is list else None,
                             "decision": "unplaced"} for i in range(len(values))]
            # These are explicit D4D objects, not prose for generic shaping.
            # The ordinary final validator decides their fields and types;
            # pre-shaping would discard valid empty strings/group structure.
            admitted = [snapshot(item) if type(item) is dict else None for item in values]
            built, indices = prepare_carrier(admitted) if any(item is not None for item in admitted) else ([], [])
            expected = []
            for obj, index in zip(built, indices):
                row["units"][index]["decision"] = "constructed"
                expected.append(snapshot(values[index]))
            if built or type(raw) is list and not raw:
                row.update(decision="constructed", reason="explicit structured carrier submitted to final validation; independent groups and duplicates retained")
                record[slot] = built + record.get(slot, [])
                origin[slot] = key
                self.carrier_tracks.append((row, slot, built, expected))
            for unit in row["units"]:
                if unit["decision"] == "unplaced":
                    dropped.append((key, "carrier occurrence not constructed; exact value retained in route_evidence"))
            if key == "d4d:labelingStrategies":
                fitted_labeling = built
        return fitted_labeling

    def _annotations(self, carrier):
        keys = ("rai:dataAnnotationProtocol", "rai:dataAnnotationPlatform", "rai:annotationsPerItem")
        fields = ("data_annotation_protocol", "data_annotation_platform", "annotations_per_item")
        projected = annotation_projection(carrier)
        independent = []
        raw_protocol = self.direct[keys[0]]["raw"]
        raw_platform = self.direct[keys[1]]["raw"]
        summary = type(raw_protocol) is not list and not (type(raw_platform) is list and len(raw_platform) > 1)
        grouped, grouped_rows = {}, []
        for key, field in zip(keys, fields):
            row = self.direct[key]
            raw = row["raw"]
            if row["presence"] in ("missing", "null"):
                continue
            if field == "annotations_per_item":
                value = canonical_count(raw)
                values = [] if value is None else [value]
                compare = str(value) if value is not None and type(raw) is str else raw
                if type(raw) is int:
                    try:
                        compare = str(raw)
                    except (ValueError, OverflowError):
                        compare = None
                row["units"] = [{"index": None, "decision": "constructed" if values else "unplaced"}]
            else:
                units = raw if type(raw) is list else [raw]
                values = [v for v in units if type(v) is str]
                row["units"] = [{"index": i if type(raw) is list else None,
                                 "decision": "constructed" if type(v) is str else "unplaced"}
                                for i, v in enumerate(units)]
                compare = raw
            if key in projected and same_json(compare, projected[key]):
                row.update(decision="redundant_projection", construction_observed=True,
                           reason="exact finite projection of explicit carrier candidate; final validation still determines retention")
                self.tracks.append(([row], "labeling_strategies", list(carrier), snapshot(carrier), key))
                continue
            if not values:
                continue
            reason = ("independent canonical assertion differs from carrier projection; no overwrite or inferred association"
                      if carrier else "declared root annotation summary; no inferred workflow")
            row.update(decision="constructed", reason=reason)
            if summary and len(values) == 1:
                grouped[field] = values[0]
                grouped_rows.append(row)
            else:
                independent.append(([row], "labeling_strategies", [{field: value} for value in values]))
        if grouped:
            independent.append((grouped_rows, "labeling_strategies", [grouped]))
        return independent

    def apply(self, record, origin, rivals, dropped, prepare_carrier):
        """Place precise constructors after generic shaping, before validation.

        Lists retain all canonical occurrences; old fitted list candidates follow.
        A singular old candidate remains available if final validation rejects
        the canonical value. Genuine ``_settle`` still decides the final record.
        """
        carrier = self._carriers(record, origin, dropped, prepare_carrier)
        annotations = self._annotations(carrier)
        for row in self.direct.values():
            unplaced = [unit for unit in row.get("units", []) if unit["decision"] == "unplaced"]
            if unplaced:
                for unit in unplaced:
                    suffix = "[" + str(unit["index"]) + "]" if unit["index"] is not None else ""
                    dropped.append((row["source"] + suffix,
                                    "unsupported assertion unit; exact value retained in route_evidence"))
            elif row["decision"] == "unplaced" and row["presence"] == "present":
                dropped.append((row["source"], "no supported projection; exact value retained in route_evidence"))
        for rows, slot, value in self.candidates:
            source = rows[0]["source"]
            if type(value) is list:
                previous = record.get(slot, [])
                record[slot] = value + previous
                refs = list(value)
            else:
                if slot in record:
                    rivals.setdefault(slot, []).insert(0, (origin[slot], record[slot]))
                record[slot] = value
                refs = [value]
            origin[slot] = source
            expected = snapshot(value)
            self.tracks.append((rows, slot, refs, expected, source))
        # Preserve explicit carrier groups first; canonical disagreements are
        # independent groups after them, never merged into a carrier object.
        for rows, slot, value in annotations:
            record[slot] = record.get(slot, []) + value
            origin[slot] = rows[0]["source"]
            self.tracks.append((rows, slot, list(value), snapshot(value), rows[0]["source"]))

    def finish(self, record, origin):
        for row in self.rows:
            slot = row["target"]
            row["final_value"] = snapshot(record.get(slot)) if slot else None
        self._finish_legacy(record, origin)
        for row, slot, refs, expected in self.carrier_tracks:
            actual = record.get(slot, [])
            intact = sum(any(item is ref and same_json(item, wanted) for item in actual)
                         for ref, wanted in zip(refs, expected))
            surviving = sum(any(item is ref for item in actual) for ref in refs)
            omitted = any(unit["decision"] == "unplaced" for unit in row["units"])
            row["retention"] = ("retained" if type(actual) is list and slot in record and intact == len(refs) and not omitted
                                else "partial" if surviving else "not_retained")
        for rows, slot, refs, expected, source in self.tracks:
            value = record.get(slot)
            if type(expected) is list:
                actual = value if type(value) is list else []
                intact = sum(any(item is ref and same_json(item, wanted) for item in actual)
                             for ref, wanted in zip(refs, expected))
                surviving = sum(any(item is ref for item in actual) for ref in refs)
                retained = "retained" if intact == len(refs) else "partial" if surviving else "not_retained"
            elif type(expected) is dict:
                retained = ("retained" if value is refs[0] and same_json(value, expected)
                            else "partial" if value is refs[0] else "not_retained")
            else:
                retained = "retained" if origin.get(slot) == source and type(value) is type(expected) and value == expected else "not_retained"
            for row in rows:
                row["retention"] = ("partial" if retained == "retained" and any(
                    unit["decision"] == "unplaced" for unit in row.get("units", [])) else retained)
        self.state["status"] = "complete"
        try:
            self.state["final_dataset_sha256"] = dataset_digest(record)
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            # This optional full-output binding must not impose a new finite
            # JSON restriction on unrelated fields accepted by the old schema.
            self.state.update(final_dataset_sha256=None, final_dataset_binding="unavailable",
                              final_dataset_binding_reason=type(exc).__name__ + ": " + str(exc))
        else:
            self.state.update(final_dataset_binding="bound", final_dataset_binding_reason=None)


def forward_projections(state, data):
    """Project only finite, unambiguous declared scalar fields.

    Rich/multiple objects remain complete outgoing assertion evidence; they are
    never flattened into strings. Independent humanSubjects and committee names
    cannot be invented from an arbitrary D4D description.
    """
    result = {}
    routes = (("citation", "citation", None),
              ("cleaning_strategies", "rai:dataManipulationProtocol", "cleaning_details"),
              ("funders", "funder", "grantor"),
              ("collection_mechanisms", "rai:dataCollection", "mechanism_details"),
              ("future_use_impacts", "rai:dataSocialImpact", "impact_details"),
              ("sensitive_elements", "rai:personalSensitiveInformation", "sensitivity_details"),
              ("human_subject_research", "humanSubjectResearch", "involves_human_subjects"),
              ("data_governance", "dataGovernanceCommittee", None))
    for source, target, member in routes:
        raw = data.get(source)
        row = assertion(source, "/" + source, source in data, raw, target)
        state["assertions"].append(row)
        value = None
        if source == "citation" and type(raw) is str:
            value = raw
        elif source in ("cleaning_strategies", "funders", "collection_mechanisms", "future_use_impacts"):
            if (type(raw) is list and len(raw) == 1 and type(raw[0]) is dict
                    and set(raw[0]) == {member} and type(raw[0][member]) is str):
                value = raw[0][member]
        elif source == "sensitive_elements":
            if (type(raw) is list and all(type(item) is dict and set(item) == {member}
                                         and type(item[member]) is str for item in raw)):
                value = [item[member] for item in raw]
        elif source == "human_subject_research" and type(raw) is dict and type(raw.get(member)) is bool:
            value = "Yes" if raw[member] else "No"
        if value is not None:
            result[target] = value
            row.update(decision="constructed", projected_value=value,
                       reason="canonical scalar projection; original typed value retained in raw evidence")
        elif source in data:
            row["reason"] = "no unambiguous scalar projection; no flattening or narrative inference"
    for target, source in CARRIERS.items():
        raw = data.get(source)
        row = assertion(source, "/" + source, source in data, raw, target)
        state["assertions"].append(row)
        if type(raw) in (dict, list):
            result[target] = snapshot(raw)
            row.update(decision="constructed", projected_value=snapshot(raw),
                       reason="complete explicit compatibility carrier; model extra transport does not validate D4D semantics")
        elif source in data:
            row["reason"] = "structured carrier requires an object or list; source value remains evidence"
    groups = data.get("labeling_strategies")
    summary = annotation_projection(groups)
    for target in ("rai:dataAnnotationProtocol", "rai:dataAnnotationPlatform", "rai:annotationsPerItem"):
        row = assertion("labeling_strategies", "/labeling_strategies",
                        "labeling_strategies" in data, groups, target)
        state["assertions"].append(row)
        if target in summary:
            result[target] = summary[target]
            row.update(decision="constructed", projected_value=summary[target],
                       reason="finite annotation projection; exact count integers use canonical ASCII decimal strings")
        elif "labeling_strategies" in data:
            row["reason"] = "no unambiguous typed annotation projection; full grouping remains in compatibility carrier"
    return result


def supplied_projections(state, data, evidence, projected):
    """Reuse finite supplied assertions only with an exact full Dataset join.

    This optional caller-supplied evidence is not an authenticated claim about
    a file. Its input metadata remains labelled as evidence supplied by the
    caller; the forward converter has not acquired those original bytes.
    """
    if evidence is None:
        return
    evidence = snapshot(evidence)
    if (type(evidence) is not dict
            or evidence.get("contract") != "fairscape-declared-assertions-v1"
            or evidence.get("direction") != "fairscape_to_d4d"
            or evidence.get("status") != "complete" or evidence.get("error") is not None
            or evidence.get("final_dataset_binding") != "bound"
            or type(evidence.get("final_dataset_sha256")) is not str):
        raise ValueError("source_evidence must describe this complete final Dataset")
    try:
        same_dataset = evidence["final_dataset_sha256"] == dataset_digest(data)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("source_evidence cannot bind this complete final Dataset") from exc
    if not same_dataset:
        raise ValueError("source_evidence must describe this complete final Dataset")
    rows = evidence.get("assertions")
    if type(rows) is not list:
        raise ValueError("source_evidence assertions must be a finite list")
    direct = {}
    allowed = set(ROUTES) | set(CARRIERS) | set(HUMAN_KEYS) | {"d4d:humanSubject", "irb.referenced_entity"}
    allowed.update("additionalProperty: " + key for key in PROPERTY_VALUES)
    root_index = evidence.get("root_graph_index")
    if type(root_index) is not int or root_index < 0:
        raise ValueError("source_evidence has no original root index")
    for row in rows:
        known = (type(row) is dict and type(row.get("source")) is str and
                 (row["source"] in allowed or (row["source"].startswith("additionalProperty: ")
                  and property_value_target(row["source"][20:])[0])))
        if (not known
                or row.get("presence") not in ("missing", "null", "present")):
            raise ValueError("source_evidence contains an unknown assertion")
        key = row["source"]
        if key in ROUTES:
            if (key in direct or row.get("target") != ROUTES[key]
                    or row.get("source_pointer") != "/@graph/" + str(root_index) + "/" + pointer_key(key)
                    or "raw" not in row):
                raise ValueError("source_evidence has conflicting direct assertion identities")
            if ((row["presence"] in ("missing", "null") and row["raw"] is not None)
                    or (row["presence"] == "present" and row["raw"] is None)):
                raise ValueError("source_evidence presence disagrees with raw assertion")
            target = ROUTES[key]
            if target and not same_json(data.get(target), row.get("final_value")):
                raise ValueError("source_evidence final target differs from the Dataset")
            direct[key] = row
    if set(direct) != set(ROUTES):
        raise ValueError("source_evidence omits a declared source assertion")
    state["supplied_source_evidence"] = evidence
    for key in ("humanSubjects", "humanSubjectResearch", "completeness", "dataGovernanceCommittee"):
        row = direct[key]
        if row["presence"] == "missing":
            continue
        value = row["raw"]
        output = assertion(key, row["source_pointer"], True, value, key)
        output["source_kind"] = "supplied_reverse_evidence"
        state["assertions"].append(output)
        supported = type(value) is str
        if key in ("humanSubjects", "humanSubjectResearch") and type(value) is bool:
            value = "Yes" if value else "No"
            supported = True
        if supported:
            # A source narrative is not silently replaced by a canonical token.
            # Both projections remain visible if they differ.
            if key in projected and projected[key] != value:
                for old in state["assertions"]:
                    if old is not output and old["target"] == key and old["decision"] == "constructed":
                        old.update(decision="unplaced", reason="supplied source assertion retained instead of canonical token")
                        old.pop("projected_value", None)
            projected[key] = value
            output.update(decision="constructed", projected_value=value,
                          reason="supplied assertion re-emitted; booleans use canonical Yes/No, no new fact inferred")
        else:
            output["reason"] = "typed scalar field cannot carry this supplied value; exact raw assertion retained"


def finish_forward(state, root):
    for row in state["assertions"]:
        target = row["target"]
        row["final_value"] = snapshot(root.get(target))
        if row["decision"] == "constructed":
            expected = row.pop("projected_value")
            row["retention"] = ("retained" if target in root and same_json(root[target], expected)
                                else "not_retained")
    state["status"] = "complete"
