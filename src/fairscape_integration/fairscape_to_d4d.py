#!/usr/bin/env python3
"""
FAIRSCAPE RO-Crate to D4D Converter (Reverse Transformation)

Converts FAIRSCAPE RO-Crate JSON-LD to D4D YAML format.

Features:
- Field mapping written out in this module's extraction methods
- Vocabulary translation (schema.org → dcterms, etc.)
- Pydantic validation of input RO-Crate
- Output fitted to the schema's Dataset class: a key the class does not
  declare, or a value that cannot be shaped to its slot, is left out and
  named in `dropped` (#3969)
- LinkML validation of output D4D
"""

import json
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from data_sheets_schema.resources import resource_path
from data_sheets_schema.rocrate_map import FULL_SCHEMA, TARGET_CLASS, _coerce
from data_sheets_schema.schema_view import shared_view
from data_sheets_schema.scope import bare_doi

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import ROCrateV1_2
    FAIRSCAPE_AVAILABLE = True
except ImportError:
    FAIRSCAPE_AVAILABLE = False
    print("Warning: FAIRSCAPE models not available")


#: An ARK in the shape `grounding` matches, without a resolver: the `ark:`
#: label, an optional `/`, a NAAN of five to nine digits, `/` and the name.
ARK = re.compile(r"^ark:/?\d{5,9}/\S+$", re.IGNORECASE)

#: The global resolver the ARK specification names.
N2T_RESOLVER = "https://n2t.net/"


def resolvable_id(value: Any) -> Any:
    """An ARK as its n2t.net resolver URL; any other value as written (#3969).

    The schema's prefixes declare no `ark`, so `ark:59853/x` expands to
    nothing under them and `identifiers.classify` can only call it
    `uri_unverified`. `https://n2t.net/ark:59853/x` is an absolute IRI at
    the resolver the ARK specification names, which needs no declared
    prefix (`uri`). The ARK is kept as written after the resolver. A value
    already in a resolver's form, or one that is not an ARK, is left as it
    is.
    """
    if isinstance(value, str) and ARK.match(value.strip()):
        return N2T_RESOLVER + value.strip()
    return value


def _plain(value: Any) -> Any:
    """`value` with every mapping key a plain `str`.

    `rocrate_map._coerce` can key an object by a slot's name, a str subclass
    that `yaml.dump` (which `fairscape-cli rocrate-to-d4d` uses) writes as a
    python object tag rather than as the name.
    """
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


class FairscapeToD4DConverter:
    """Convert FAIRSCAPE RO-Crate to D4D YAML."""

    # Until #3884 the constructor took an SSSOM table (`--sssom`, defaulting
    # to the retired d4d_rocrate_sssom_mapping.tsv) and loaded it into an
    # attribute nothing read: the output was identical with it, with another
    # table and with none, apart from the `generated_date` timestamp every run
    # stamps. The field mapping is the code below.

    def __init__(self):
        #: What the last `convert` left out of the record, as (source,
        #: reason) pairs. The source is the crate property, or the path
        #: inside an object this converter built (#3969).
        self.dropped: List[Tuple[str, str]] = []
        self._view = None
        self._slots: Dict[str, Dict[str, Any]] = {}
        self._minted: Dict[str, int] = {}

    def convert(self, rocrate_input: Any) -> Dict[str, Any]:
        """
        Convert FAIRSCAPE RO-Crate to D4D dictionary.

        Args:
            rocrate_input: FAIRSCAPE RO-Crate (dict, Path, or ROCrateV1_2)

        Returns:
            D4D dictionary
        """
        self.dropped = []
        self._minted = {}

        # Load RO-Crate data
        if isinstance(rocrate_input, dict):
            rocrate_data = rocrate_input
        elif isinstance(rocrate_input, (str, Path)):
            with open(rocrate_input) as f:
                rocrate_data = json.load(f)
        elif FAIRSCAPE_AVAILABLE and isinstance(rocrate_input, ROCrateV1_2):
            rocrate_data = rocrate_input.model_dump(by_alias=True, exclude_none=True)
        else:
            raise ValueError(f"Unsupported input type: {type(rocrate_input)}")

        # Validate with Pydantic if available
        if FAIRSCAPE_AVAILABLE and isinstance(rocrate_data, dict):
            try:
                rocrate_model = ROCrateV1_2(**rocrate_data)
                print("✓ Input RO-Crate validated with FAIRSCAPE Pydantic models")
            except Exception as e:
                print(f"⚠ Warning: RO-Crate validation failed: {e}")

        # Extract Dataset entity and nested Datasets from @graph
        dataset, nested_datasets = self._extract_datasets(rocrate_data)

        if not dataset:
            raise ValueError("No Dataset entity found in RO-Crate @graph")

        # Convert to D4D
        d4d_dict = self._build_d4d(dataset, nested_datasets, rocrate_data)

        return d4d_dict

    def _extract_datasets(self, rocrate_data: Dict) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Extract main Dataset and nested Datasets from RO-Crate @graph.

        Returns:
            Tuple of (main_dataset, nested_datasets_list)
        """
        graph = rocrate_data.get('@graph', [])

        main_dataset = None
        nested_datasets = []
        hasPart_ids = set()

        # First pass: find main dataset and collect hasPart references
        for entity in graph:
            entity_type = entity.get('@type', [])
            if isinstance(entity_type, str):
                entity_type = [entity_type]

            if 'Dataset' in entity_type:
                # Skip metadata descriptor
                if entity.get('@id') == 'ro-crate-metadata.json':
                    continue

                # Main dataset is the root with @id "./" or has ROCrate type
                entity_id = entity.get('@id', '')
                if entity_id == './' or 'https://w3id.org/EVI#ROCrate' in entity_type:
                    main_dataset = entity
                    # Collect hasPart references
                    has_part = entity.get('hasPart', [])
                    for part in has_part:
                        if isinstance(part, dict) and '@id' in part:
                            hasPart_ids.add(part['@id'])
                        elif isinstance(part, str):
                            hasPart_ids.add(part)

        # Second pass: collect nested datasets (those referenced by hasPart)
        for entity in graph:
            entity_type = entity.get('@type', [])
            if isinstance(entity_type, str):
                entity_type = [entity_type]

            if 'Dataset' in entity_type:
                entity_id = entity.get('@id', '')
                if entity_id in hasPart_ids:
                    nested_datasets.append(entity)

        return main_dataset, nested_datasets

    def _build_d4d(self, dataset: Dict, nested_datasets: List[Dict], full_rocrate: Dict) -> Dict[str, Any]:
        """
        Build D4D dictionary from RO-Crate Dataset entity.

        The mappings name the D4D slot each crate property goes to. The
        record is then fitted to the schema's Dataset class (`_fit`), so it
        carries only keys the class declares, each shaped to its slot's
        range; what cannot be placed is recorded in `dropped` (#3969). The
        record no longer carries the converter's own `schema_version`,
        `generated_date` and `source` stamps, which are not D4D slots.

        Args:
            dataset: Main Dataset entity
            nested_datasets: Nested Dataset entities (FileCollections)
            full_rocrate: Full RO-Crate data

        Returns:
            D4D dictionary
        """
        d4d: Dict[str, Any] = {}
        # slot -> the crate property it was filled from, for `dropped`
        origin: Dict[str, str] = {}

        record_id = self._record_id(dataset)
        if record_id:
            d4d['id'] = record_id
            origin['id'] = 'identifier' if dataset.get('identifier') else '@id'

        # Convert nested Datasets to FileCollections
        file_collections = (self._build_file_collections(nested_datasets)
                            if nested_datasets else [])
        if file_collections:
            d4d['file_collections'] = file_collections
            origin['file_collections'] = 'hasPart'

        # A hasPart reference already converted to a FileCollection is not
        # repeated under resources.
        fc_ids = {fc.get('id') for fc in file_collections}
        complex_props = [
            (prop, slot, [r for r in value if r.get('id') not in fc_ids]
             if slot == 'resources' else value)
            for prop, slot, value in self._map_complex_properties(dataset)
        ]

        # In this order a later mapping supersedes an earlier one in a
        # single-valued slot (`_place`).
        for prop, slot, value in (self._map_basic_properties(dataset)
                                  + complex_props
                                  # EVI properties (computational provenance)
                                  + self._map_evi_properties(dataset)
                                  # RAI properties (responsible AI)
                                  + self._map_rai_properties(dataset)
                                  # custom D4D properties
                                  + self._map_d4d_properties(dataset)):
            self._place(d4d, origin, slot, value, prop)

        return self._fit(d4d, TARGET_CLASS, origin)

    def _record_id(self, dataset: Dict) -> Optional[str]:
        """The record's required `id`, taken from the crate root (#3969).

        The rule `rocrate_map.map_crate` applies to a crate root: its
        `identifier`, else its `@id`, never a minted value, so the record
        points back at the crate it came from. A DOI is written as the
        `doi:` CURIE (#974), an ARK as its n2t.net resolver URL. A root
        whose only identifier is an attached crate's `./` gives `./`, which
        is all such a crate supplies.
        """
        value = dataset.get('identifier') or dataset.get('@id')
        if isinstance(value, list):
            value = value[0] if value else None
        if not value:
            return None
        doi = bare_doi(value)
        return f"doi:{doi}" if doi else resolvable_id(str(value))

    def _place(self, d4d: Dict[str, Any], origin: Dict[str, str],
               slot: str, value: Any, prop: str) -> None:
        """Put `value`, read from crate property `prop`, in `slot`.

        Two crate properties can map to one slot: an `additionalProperty`
        entry and the property it duplicates, or the FAIRSCAPE spelling of
        a key and the one this repo's d4d_to_fairscape.py writes. A
        multivalued slot keeps each distinct value of both, so neither is
        chosen over the other. A single-valued slot keeps one value and
        records the other as dropped: a dedicated property's over an
        `additionalProperty` entry, FAIRSCAPE's own precedence (its
        datasheet mapping reads each dedicated key first and falls back to
        the `additionalProperty` entry), and otherwise the later mapping's.
        """
        if value in (None, '', [], {}):
            return
        if slot not in d4d:
            d4d[slot], origin[slot] = value, prop
            return
        held = d4d[slot]
        if held == value:
            return
        declared = self._class_slots(TARGET_CLASS).get(slot)
        if declared is not None and declared.multivalued:
            items = list(held) if isinstance(held, list) else [held]
            for item in (value if isinstance(value, list) else [value]):
                if item not in items:
                    items.append(item)
            d4d[slot], origin[slot] = items, f"{origin[slot]} + {prop}"
            return
        fallback = 'additionalProperty['
        if prop.startswith(fallback) and not origin[slot].startswith(fallback):
            self.dropped.append(
                (prop, f"superseded by {origin[slot]}, which also maps to `{slot}`"))
            return
        self.dropped.append(
            (origin[slot], f"superseded by {prop}, which also maps to `{slot}`"))
        d4d[slot], origin[slot] = value, prop

    def _schema_view(self):
        """The merged schema, read from any working directory (#1301)."""
        if self._view is None:
            self._view = shared_view(resource_path(FULL_SCHEMA))
        return self._view

    def _class_slots(self, cls: str) -> Dict[str, Any]:
        """The induced slots of `cls`, by name."""
        if cls not in self._slots:
            self._slots[cls] = {
                s.name: s for s in self._schema_view().class_induced_slots(cls)
            }
        return self._slots[cls]

    def _fit(self, obj: Dict[str, Any], cls: str, origin: Dict[str, str],
             where: str = '') -> Dict[str, Any]:
        """`obj` with only the keys `cls` declares, each value shaped to its
        slot by `_shape`.

        A key the class does not declare, and a value `_shape` cannot fit
        to its slot, are left out and recorded in `dropped` (#3969). `where`
        is the path of a nested object, which names what was dropped from it.
        """
        slots = self._class_slots(cls)
        fitted: Dict[str, Any] = {}
        for key, value in obj.items():
            source = origin.get(key) or f"{where}{key}"
            slot = slots.get(key)
            if slot is None:
                self.dropped.append(
                    (source, f"the schema declares no `{key}` slot on {cls}"))
                continue
            if value in (None, '', [], {}):
                continue
            shaped, why = self._shape(value, slot, f"{where}{key}")
            if shaped is None:
                self.dropped.append((source, f"not placed in `{key}`: {why}"))
                continue
            fitted[key] = shaped
        return fitted

    def _shape(self, value: Any, slot: Any, where: str) -> Tuple[Any, str]:
        """`(value, note)` shaped to `slot`'s range and cardinality.

        Crate values take the static-map arm's rule (`rocrate_map._coerce`):
        a DOI is the bare DOI, dates are date-times, enum values are kept
        only where permitted, and text becomes an object of a class range;
        so a crate value reaches a slot in one form whichever converter
        writes it. An object this converter built (a creator, a reference,
        a file collection) is fitted key by key, as the record is. The
        value is None, with the reason, when it cannot be shaped to the slot.
        """
        view = self._schema_view()
        cls = slot.range if slot.range and view.get_class(slot.range) else None
        items = value if isinstance(value, list) else [value]
        if cls and all(isinstance(item, dict)
                       and not any(str(k).startswith('@') for k in item)
                       for item in items):
            built = [self._fit(item, cls, {}, f"{where}[{n}].")
                     for n, item in enumerate(items)]
            built = [obj for obj in built if obj]
            if not built:
                return None, f"no {cls} slot holds any of its keys"
            if slot.multivalued:
                return built, ''
            if len(built) == 1:
                return built[0], ''
            return None, f"{len(built)} objects for a single-valued slot"
        if cls and not slot.multivalued and isinstance(value, list) and len(value) > 1:
            # `_coerce` joins a single-valued slot's list after shaping each
            # item into an object, which would join the objects; join the
            # text first, so the slot holds one object.
            value = '; '.join(str(item) for item in value)
        shaped, note = _coerce(value, slot, view, 'fairscape', self._minted)
        return _plain(shaped), note

    def _build_file_collections(self, nested_datasets: List[Dict]) -> List[Dict[str, Any]]:
        """
        Convert nested RO-Crate Datasets to D4D FileCollections.

        Args:
            nested_datasets: List of nested Dataset entities from RO-Crate

        Returns:
            List of FileCollection dictionaries
        """
        file_collections = []

        for dataset in nested_datasets:
            collection = {}

            # Map basic properties
            if '@id' in dataset:
                collection['id'] = resolvable_id(dataset['@id'])

            if 'name' in dataset:
                collection['name'] = dataset['name']

            if 'description' in dataset:
                collection['description'] = dataset['description']

            # Map collection-level properties
            # Note: encodingFormat, sha256, md5, format, bytes, encoding are now
            # file-level properties (on File objects), not FileCollection properties

            if 'contentSize' in dataset:
                # Parse size string to total_bytes (aggregate size)
                size_str = dataset['contentSize']
                size = self._parse_size(size_str) if isinstance(size_str, str) else size_str
                if size is None:
                    self.dropped.append((f"{dataset.get('@id')}.contentSize",
                                         f"{size_str!r} is not a size in bytes "
                                         "this converter can read"))
                else:
                    collection['total_bytes'] = size

            if 'contentUrl' in dataset:
                collection['path'] = dataset['contentUrl']

            if 'fileFormat' in dataset:
                collection['compression'] = dataset['fileFormat']

            # Map D4D-specific properties
            if 'd4d:collectionType' in dataset:
                # Single-valued in the schema: `_fit` unwraps a one-item
                # list and keeps only a FileCollectionTypeEnum value.
                collection['collection_type'] = dataset['d4d:collectionType']

            if 'd4d:fileCount' in dataset:
                collection['file_count'] = dataset['d4d:fileCount']

            # TODO: Parse nested Dataset's hasPart to build FileCollection.resources
            # Currently, file-level information in RO-Crate File entities is not converted
            # to FileCollection.resources (File objects). Future work: parse dataset['hasPart'],
            # fetch referenced File entities, and convert to D4D File objects in resources.

            # Only add non-empty collections
            if collection:
                file_collections.append(collection)

        return file_collections

    def _map_basic_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map basic Schema.org properties to D4D, as (crate property, slot, value)."""

        mapping = {
            # Direct mappings (same name)
            'name': 'title',
            'description': 'description',
            'keywords': 'keywords',
            'version': 'version',
            'license': 'license',
            'publisher': 'publisher',

            # Property name differences
            'identifier': 'doi',
            'datePublished': 'issued',
            'dateCreated': 'created_on',
            'dateModified': 'last_updated_on',
            'author': 'creators',
            'url': 'page',
            'contentUrl': 'download_url',
            # The schema has no Dataset `bytes`; its byte-size slot is
            # `total_size_bytes` (dcat:byteSize), the slot
            # rocrate_normalize remaps `bytes` to (#3969).
            'contentSize': 'total_size_bytes',
        }

        found = []

        for rocrate_prop, d4d_prop in mapping.items():
            if rocrate_prop in dataset:
                value = dataset[rocrate_prop]

                # Handle special transformations
                if rocrate_prop == 'author' and isinstance(value, str):
                    # Convert semicolon-separated string to Creator list
                    value = self._parse_authors(value)
                elif rocrate_prop == 'contentSize' and isinstance(value, str):
                    # Parse size string (e.g., "19.1 TB") to bytes
                    size = self._parse_size(value)
                    if size is None:
                        self.dropped.append((rocrate_prop,
                                             f"{value!r} is not a size in bytes "
                                             "this converter can read"))
                        continue
                    value = size

                found.append((rocrate_prop, d4d_prop, value))

        return found

    def _map_complex_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map complex/nested properties, as (crate property, slot, value)."""

        found = []

        # hasPart → resources (schema:hasPart), each a Dataset object
        if 'hasPart' in dataset:
            has_part = dataset['hasPart']
            if isinstance(has_part, list):
                found.append(('hasPart', 'resources',
                              self._references('hasPart', has_part)))

        # isPartOf → parent_datasets, the Dataset slot whose slot_uri is
        # schema:isPartOf; there is no `is_part_of` slot (#3969)
        if 'isPartOf' in dataset:
            is_part_of = dataset['isPartOf']
            if isinstance(is_part_of, list):
                found.append(('isPartOf', 'parent_datasets',
                              self._references('isPartOf', is_part_of)))

        # additionalProperty → custom metadata
        if 'additionalProperty' in dataset:
            additional = dataset['additionalProperty']
            if isinstance(additional, list):
                found.extend(self._parse_additional_properties(additional))

        return found

    def _references(self, prop: str, items: List[Any]) -> List[Dict[str, Any]]:
        """Crate references as the `{id: …}` objects a Dataset-ranged slot
        holds, an ARK as its resolver URL; an entry with no id is recorded
        in `dropped`."""
        references = []
        for item in items:
            ref = item.get('@id') if isinstance(item, dict) else item
            if isinstance(ref, str) and ref.strip():
                references.append({'id': resolvable_id(ref)})
            else:
                self.dropped.append((prop, f"an entry with no @id: {item!r}"))
        return references

    def _map_evi_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map EVI (Evidence) namespace properties, as (crate property, slot, value).

        Only `evi:formats` has a Dataset slot. The roll-up counts and the
        checksums name none, and `_fit` records them as dropped (#3969).
        """

        evi_mapping = {
            'evi:datasetCount': 'dataset_count',
            'evi:computationCount': 'computation_count',
            'evi:softwareCount': 'software_count',
            'evi:schemaCount': 'schema_count',
            'evi:totalEntities': 'total_entities',
            'evi:formats': 'distribution_formats',
            'evi:md5': 'md5',
            'evi:sha256': 'sha256',
        }

        return [(evi_prop, d4d_prop, dataset[evi_prop])
                for evi_prop, d4d_prop in evi_mapping.items()
                if evi_prop in dataset]

    def _map_rai_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map RAI (Responsible AI) properties, as (crate property, slot, value)."""

        rai_mapping = {
            'rai:dataUseCases': 'intended_uses',
            'rai:dataBiases': 'known_biases',
            'rai:dataLimitations': 'known_limitations',
            'rai:dataCollection': 'acquisition_methods',
            'rai:dataCollectionMissingData': 'missing_data_documentation',
            'rai:dataCollectionRawData': 'raw_data_sources',
            'rai:dataCollectionTimeframe': 'collection_timeframes',
            # FAIRSCAPE's ROCrateMetadataElem declares these three as
            # unprefixed `prohibitedUses` and `ethicalReview` and as
            # `rai:dataImputationProtocol`, so the `rai:` spellings never
            # matched a FAIRSCAPE crate (#3973). The `rai:` spellings stay
            # because d4d_to_fairscape.py writes them, and this repo's own
            # round trip reads them back. The three slots are multivalued,
            # so a crate carrying both spellings keeps both values (`_place`).
            'rai:prohibitedUses': 'prohibited_uses',
            'prohibitedUses': 'prohibited_uses',
            'rai:ethicalReview': 'ethical_reviews',
            'ethicalReview': 'ethical_reviews',
            'rai:personalSensitiveInformation': 'confidential_elements',
            'rai:dataSocialImpact': 'data_protection_impacts',
            'rai:dataReleaseMaintenancePlan': 'updates',
            'rai:dataPreprocessingProtocol': 'preprocessing_strategies',
            'rai:dataAnnotationProtocol': 'labeling_strategies',
            'rai:dataAnnotationAnalysis': 'annotation_analyses',
            # MachineAnnotationTools is the class the schema maps to
            # rai:machineAnnotationTools; there is no
            # `machine_annotation_analyses` slot (#3969).
            'rai:machineAnnotationTools': 'machine_annotation_tools',
            'rai:imputationProtocol': 'imputation_protocols',
            'rai:dataImputationProtocol': 'imputation_protocols',
        }

        return [(rai_prop, d4d_prop, dataset[rai_prop])
                for rai_prop, d4d_prop in rai_mapping.items()
                if rai_prop in dataset]

    def _map_d4d_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map D4D-specific namespace properties, as (crate property, slot, value)."""

        d4d_mapping = {
            'd4d:addressingGaps': 'addressing_gaps',
            'd4d:dataAnomalies': 'anomalies',
            'd4d:contentWarning': 'content_warnings',
            'd4d:informedConsent': 'informed_consent',
            'd4d:humanSubject': 'human_subject_research',
            # The slot whose slot_uri is d4d:atRiskPopulations; there is no
            # `vulnerable_populations` slot (#3969).
            'd4d:atRiskPopulations': 'at_risk_populations',
        }

        return [(d4d_ns_prop, d4d_prop, dataset[d4d_ns_prop])
                for d4d_ns_prop, d4d_prop in d4d_mapping.items()
                if d4d_ns_prop in dataset]

    def _parse_authors(self, author_string: str) -> List[Dict[str, str]]:
        """Parse semicolon-separated author string to Creator list.

        A Creator declares no `type` slot, so none is written (#3969).
        """
        authors = []

        for name in author_string.split(';'):
            name = name.strip()
            if name:
                authors.append({'name': name})

        return authors

    def _parse_size(self, size_string: str) -> Optional[int]:
        """Parse size string to bytes."""
        try:
            # Try direct int conversion
            return int(size_string)
        except ValueError:
            # Parse human-readable size (e.g., "19.1 TB")
            size_string = size_string.strip().upper()

            units = {
                'B': 1,
                'KB': 1024,
                'MB': 1024**2,
                'GB': 1024**3,
                'TB': 1024**4,
                'PB': 1024**5,
            }

            for unit, multiplier in units.items():
                if size_string.endswith(unit):
                    num_str = size_string[:-len(unit)].strip()
                    try:
                        return int(float(num_str) * multiplier)
                    except ValueError:
                        pass

            # Could not parse
            return None

    def _parse_additional_properties(self, additional: List[Dict]) -> List[Tuple[str, str, Any]]:
        """Parse additionalProperty list to D4D fields, as (source, slot, value).

        `Completeness` and `Data Governance Committee` name no Dataset slot,
        and `_fit` records them as dropped, as it does any other name that
        is not one (#3969).
        """
        found = []

        for prop in additional:
            if not isinstance(prop, dict):
                continue

            prop_type = prop.get('@type')
            if prop_type != 'PropertyValue':
                continue

            name = prop.get('name')
            value = prop.get('value')

            if not name:
                continue

            # Map known additional properties to D4D fields
            name_mapping = {
                'Completeness': 'completeness',
                'Human Subject': 'human_subject_research',
                'Prohibited Uses': 'prohibited_uses',
                'Data Governance Committee': 'data_governance_committee',
            }

            d4d_field = name_mapping.get(name, name.lower().replace(' ', '_'))
            found.append((f"additionalProperty[{name}]", d4d_field, value))

        return found

    def convert_and_save(
        self,
        rocrate_input: Any,
        output_file: Path,
        validate: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Convert RO-Crate to D4D and save as YAML.

        Args:
            rocrate_input: FAIRSCAPE RO-Crate input
            output_file: Output YAML file path
            validate: Validate against D4D schema

        Returns:
            (d4d_dict, is_valid)
        """
        # Convert
        d4d_dict = self.convert(rocrate_input)

        # Save
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            yaml.safe_dump(d4d_dict, f, default_flow_style=False, sort_keys=False)

        print(f"✓ D4D YAML saved to {output_file}")

        if self.dropped:
            print(f"⚠ {len(self.dropped)} crate value(s) not placed in the record:")
            for source, reason in self.dropped:
                print(f"  - {source}: {reason}")

        # Validate if requested
        is_valid = True
        if validate:
            is_valid = self._validate_d4d(output_file)

        return d4d_dict, is_valid

    def _validate_d4d(self, d4d_file: Path) -> bool:
        """Validate D4D YAML against schema."""
        try:
            from linkml.validator import validate
            from linkml_runtime.loaders import yaml_loader

            # From any working directory (#1301). A schema that cannot be
            # found means the record was not validated, which is not a pass
            # (#3969).
            schema_file = resource_path(FULL_SCHEMA)

            if not schema_file.exists():
                print(f"✗ Schema not found: {schema_file}; the record was not validated")
                return False

            # Load D4D data
            with open(d4d_file) as f:
                d4d_data = yaml.safe_load(f)

            # Validate
            report = validate(d4d_data, str(schema_file), target_class='Dataset')

            if report.results:
                print(f"✗ Validation failed with {len(report.results)} errors")
                for result in report.results[:5]:  # Show first 5 errors
                    print(f"  - {result.message}")
                return False
            else:
                print("✓ D4D YAML validated against schema")
                return True

        except Exception as e:
            print(f"⚠ Validation error: {e}")
            return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert FAIRSCAPE RO-Crate to D4D YAML'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input FAIRSCAPE RO-Crate JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output D4D YAML file'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip D4D schema validation'
    )

    args = parser.parse_args()

    # Convert
    converter = FairscapeToD4DConverter()

    print(f"\nConverting FAIRSCAPE RO-Crate → D4D YAML...")
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")

    try:
        d4d_dict, is_valid = converter.convert_and_save(
            Path(args.input),
            Path(args.output),
            validate=not args.no_validate
        )

        print(f"\n✓ Conversion complete")
        print(f"  D4D fields: {len(d4d_dict)}")
        print(f"  Validation: {'✓ PASSED' if is_valid else '✗ FAILED'}")

        return 0 if is_valid else 1

    except Exception as e:
        print(f"\n✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
