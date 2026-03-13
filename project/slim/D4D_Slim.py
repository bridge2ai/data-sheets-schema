# Auto generated from D4D_Slim.yaml by pythongen.py version: 0.0.1
# Generation date: 2026-03-09T18:45:39
# Schema: data-sheets-schema-slim
#
# id: https://w3id.org/bridge2ai/data-sheets-schema/slim
# description: A slimmed-down version of the Datasheets for Datasets (D4D) schema optimized
#   for RO-Crate transformations. This schema includes only classes and attributes
#   with ≥50% coverage in RO-Crate mappings.
#
#   Coverage: 40% of full D4D schema (272/680 attributes)
#   Included classes: 5 (Dataset, DataSubset, DatasetCollection, Information, Software)
#   Excluded classes: 69 (all module-specific detail classes)
#
#   This slim schema is suitable for:
#   - RO-Crate JSON-LD to D4D YAML transformations
#   - Minimal dataset documentation requirements
#   - Progressive enhancement (add more fields as RO-Crate coverage grows)
#
#   See full D4D schema at: https://w3id.org/bridge2ai/data-sheets-schema
# license: MIT

import dataclasses
import re
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time
)
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Union
)

from jsonasobj2 import (
    JsonObj,
    as_dict
)
from linkml_runtime.linkml_model.meta import (
    EnumDefinition,
    PermissibleValue,
    PvFormulaOptions
)
from linkml_runtime.utils.curienamespace import CurieNamespace
from linkml_runtime.utils.enumerations import EnumDefinitionImpl
from linkml_runtime.utils.formatutils import (
    camelcase,
    sfx,
    underscore
)
from linkml_runtime.utils.metamodelcore import (
    bnode,
    empty_dict,
    empty_list
)
from linkml_runtime.utils.slot import Slot
from linkml_runtime.utils.yamlutils import (
    YAMLRoot,
    extended_float,
    extended_int,
    extended_str
)
from rdflib import (
    Namespace,
    URIRef
)

from linkml_runtime.linkml_model.types import Boolean, Date, Integer, String, Uri, Uriorcurie
from linkml_runtime.utils.metamodelcore import Bool, URI, URIorCURIE, XSDDate

metamodel_version = "1.7.0"
version = None

# Namespaces
D4DSLIM = CurieNamespace('d4dslim', 'https://w3id.org/bridge2ai/data-sheets-schema/slim#')
DCAT = CurieNamespace('dcat', 'http://www.w3.org/ns/dcat#')
DCTERMS = CurieNamespace('dcterms', 'http://purl.org/dc/terms/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
PROV = CurieNamespace('prov', 'http://www.w3.org/ns/prov#')
SCHEMA = CurieNamespace('schema', 'http://schema.org/')
DEFAULT_ = D4DSLIM


# Types

# Class references
class InformationId(URIorCURIE):
    pass


class SoftwareId(InformationId):
    pass


class DatasetCollectionId(InformationId):
    pass


class DatasetId(InformationId):
    pass


class DataSubsetId(DatasetId):
    pass


@dataclass(repr=False)
class Information(YAMLRoot):
    """
    Abstract base class for information resources. Provides common metadata fields for datasets, collections, and
    other information artifacts.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DSLIM["Information"]
    class_class_curie: ClassVar[str] = "d4dslim:Information"
    class_name: ClassVar[str] = "Information"
    class_model_uri: ClassVar[URIRef] = D4DSLIM.Information

    id: Union[str, InformationId] = None
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[Union[str, list[str]]] = empty_list()
    language: Optional[str] = None
    license: Optional[str] = None
    doi: Optional[Union[str, URIorCURIE]] = None
    page: Optional[Union[str, URI]] = None
    download_url: Optional[Union[str, URI]] = None
    publisher: Optional[Union[str, URI]] = None
    version: Optional[str] = None
    issued: Optional[Union[str, XSDDate]] = None
    created_on: Optional[Union[str, XSDDate]] = None
    created_by: Optional[Union[str, list[str]]] = empty_list()
    last_updated_on: Optional[Union[str, XSDDate]] = None
    modified_by: Optional[Union[str, list[str]]] = empty_list()
    was_derived_from: Optional[str] = None
    conforms_to: Optional[Union[str, URI]] = None
    conforms_to_schema: Optional[Union[str, URI]] = None
    conforms_to_class: Optional[Union[str, URIorCURIE]] = None
    compression: Optional[Union[str, "CompressionEnum"]] = None
    status: Optional[Union[str, URI]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InformationId):
            self.id = InformationId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.keywords, list):
            self.keywords = [self.keywords] if self.keywords is not None else []
        self.keywords = [v if isinstance(v, str) else str(v) for v in self.keywords]

        if self.language is not None and not isinstance(self.language, str):
            self.language = str(self.language)

        if self.license is not None and not isinstance(self.license, str):
            self.license = str(self.license)

        if self.doi is not None and not isinstance(self.doi, URIorCURIE):
            self.doi = URIorCURIE(self.doi)

        if self.page is not None and not isinstance(self.page, URI):
            self.page = URI(self.page)

        if self.download_url is not None and not isinstance(self.download_url, URI):
            self.download_url = URI(self.download_url)

        if self.publisher is not None and not isinstance(self.publisher, URI):
            self.publisher = URI(self.publisher)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.issued is not None and not isinstance(self.issued, XSDDate):
            self.issued = XSDDate(self.issued)

        if self.created_on is not None and not isinstance(self.created_on, XSDDate):
            self.created_on = XSDDate(self.created_on)

        if not isinstance(self.created_by, list):
            self.created_by = [self.created_by] if self.created_by is not None else []
        self.created_by = [v if isinstance(v, str) else str(v) for v in self.created_by]

        if self.last_updated_on is not None and not isinstance(self.last_updated_on, XSDDate):
            self.last_updated_on = XSDDate(self.last_updated_on)

        if not isinstance(self.modified_by, list):
            self.modified_by = [self.modified_by] if self.modified_by is not None else []
        self.modified_by = [v if isinstance(v, str) else str(v) for v in self.modified_by]

        if self.was_derived_from is not None and not isinstance(self.was_derived_from, str):
            self.was_derived_from = str(self.was_derived_from)

        if self.conforms_to is not None and not isinstance(self.conforms_to, URI):
            self.conforms_to = URI(self.conforms_to)

        if self.conforms_to_schema is not None and not isinstance(self.conforms_to_schema, URI):
            self.conforms_to_schema = URI(self.conforms_to_schema)

        if self.conforms_to_class is not None and not isinstance(self.conforms_to_class, URIorCURIE):
            self.conforms_to_class = URIorCURIE(self.conforms_to_class)

        if self.compression is not None and not isinstance(self.compression, CompressionEnum):
            self.compression = CompressionEnum(self.compression)

        if self.status is not None and not isinstance(self.status, URI):
            self.status = URI(self.status)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Software(Information):
    """
    Information about software used in dataset creation, processing, or analysis.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DSLIM["Software"]
    class_class_curie: ClassVar[str] = "d4dslim:Software"
    class_name: ClassVar[str] = "Software"
    class_model_uri: ClassVar[URIRef] = D4DSLIM.Software

    id: Union[str, SoftwareId] = None
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    license: Optional[str] = None
    url: Optional[Union[str, URI]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, SoftwareId):
            self.id = SoftwareId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.license is not None and not isinstance(self.license, str):
            self.license = str(self.license)

        if self.url is not None and not isinstance(self.url, URI):
            self.url = URI(self.url)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DatasetCollection(Information):
    """
    A collection of related datasets, likely containing multiple files of multiple potential purposes and properties.
    This is the top-level container for grouping related data resources.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DSLIM["DatasetCollection"]
    class_class_curie: ClassVar[str] = "d4dslim:DatasetCollection"
    class_name: ClassVar[str] = "DatasetCollection"
    class_model_uri: ClassVar[URIRef] = D4DSLIM.DatasetCollection

    id: Union[str, DatasetCollectionId] = None
    resources: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetCollectionId):
            self.id = DatasetCollectionId(self.id)

        if not isinstance(self.resources, list):
            self.resources = [self.resources] if self.resources is not None else []
        self.resources = [v if isinstance(v, str) else str(v) for v in self.resources]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Dataset(Information):
    """
    A single component of related observations and/or information that can be read, manipulated, transformed, and
    otherwise interpreted. Represents a single data file or coherent data resource.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DCAT["Distribution"]
    class_class_curie: ClassVar[str] = "dcat:Distribution"
    class_name: ClassVar[str] = "Dataset"
    class_model_uri: ClassVar[URIRef] = D4DSLIM.Dataset

    id: Union[str, DatasetId] = None
    bytes: Optional[int] = None
    encoding: Optional[str] = None
    format: Optional[str] = None
    compression: Optional[Union[str, "CompressionEnum"]] = None
    hash: Optional[str] = None
    md5: Optional[str] = None
    sha256: Optional[str] = None
    media_type: Optional[str] = None
    is_tabular: Optional[Union[bool, Bool]] = None
    dialect: Optional[str] = None
    path: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    citation: Optional[str] = None
    doi: Optional[Union[str, URIorCURIE]] = None
    keywords: Optional[Union[str, list[str]]] = empty_list()
    language: Optional[str] = None
    page: Optional[Union[str, URI]] = None
    download_url: Optional[Union[str, URI]] = None
    was_derived_from: Optional[str] = None
    parent_datasets: Optional[Union[str, list[str]]] = empty_list()
    related_datasets: Optional[Union[str, list[str]]] = empty_list()
    creators: Optional[Union[str, list[str]]] = empty_list()
    created_on: Optional[Union[str, XSDDate]] = None
    created_by: Optional[Union[str, list[str]]] = empty_list()
    issued: Optional[Union[str, XSDDate]] = None
    last_updated_on: Optional[Union[str, XSDDate]] = None
    modified_by: Optional[Union[str, list[str]]] = empty_list()
    publisher: Optional[Union[str, URI]] = None
    version: Optional[str] = None
    funders: Optional[Union[str, list[str]]] = empty_list()
    conforms_to: Optional[Union[str, URI]] = None
    conforms_to_schema: Optional[Union[str, URI]] = None
    conforms_to_class: Optional[Union[str, URIorCURIE]] = None
    status: Optional[Union[str, URI]] = None
    purposes: Optional[Union[str, list[str]]] = empty_list()
    tasks: Optional[Union[str, list[str]]] = empty_list()
    addressing_gaps: Optional[Union[str, list[str]]] = empty_list()
    instances: Optional[Union[str, list[str]]] = empty_list()
    variables: Optional[Union[str, list[str]]] = empty_list()
    subsets: Optional[Union[str, list[str]]] = empty_list()
    subpopulations: Optional[Union[str, list[str]]] = empty_list()
    anomalies: Optional[Union[str, list[str]]] = empty_list()
    sensitive_elements: Optional[Union[str, list[str]]] = empty_list()
    confidential_elements: Optional[Union[str, list[str]]] = empty_list()
    known_biases: Optional[Union[str, list[str]]] = empty_list()
    known_limitations: Optional[Union[str, list[str]]] = empty_list()
    content_warnings: Optional[Union[str, list[str]]] = empty_list()
    external_resources: Optional[Union[str, list[str]]] = empty_list()
    collection_mechanisms: Optional[Union[str, list[str]]] = empty_list()
    acquisition_methods: Optional[Union[str, list[str]]] = empty_list()
    collection_timeframes: Optional[Union[str, list[str]]] = empty_list()
    data_collectors: Optional[Union[str, list[str]]] = empty_list()
    sampling_strategies: Optional[Union[str, list[str]]] = empty_list()
    missing_data_documentation: Optional[Union[str, list[str]]] = empty_list()
    raw_sources: Optional[Union[str, list[str]]] = empty_list()
    raw_data_sources: Optional[Union[str, list[str]]] = empty_list()
    preprocessing_strategies: Optional[Union[str, list[str]]] = empty_list()
    cleaning_strategies: Optional[Union[str, list[str]]] = empty_list()
    labeling_strategies: Optional[Union[str, list[str]]] = empty_list()
    imputation_protocols: Optional[Union[str, list[str]]] = empty_list()
    annotation_analyses: Optional[Union[str, list[str]]] = empty_list()
    machine_annotation_tools: Optional[Union[str, list[str]]] = empty_list()
    intended_uses: Optional[Union[str, list[str]]] = empty_list()
    other_tasks: Optional[Union[str, list[str]]] = empty_list()
    existing_uses: Optional[Union[str, list[str]]] = empty_list()
    discouraged_uses: Optional[Union[str, list[str]]] = empty_list()
    prohibited_uses: Optional[Union[str, list[str]]] = empty_list()
    future_use_impacts: Optional[Union[str, list[str]]] = empty_list()
    distribution_formats: Optional[Union[str, list[str]]] = empty_list()
    distribution_dates: Optional[Union[str, list[str]]] = empty_list()
    license: Optional[str] = None
    license_and_use_terms: Optional[Union[str, list[str]]] = empty_list()
    extension_mechanism: Optional[Union[str, list[str]]] = empty_list()
    use_repository: Optional[Union[str, list[str]]] = empty_list()
    version_access: Optional[Union[str, list[str]]] = empty_list()
    maintainers: Optional[Union[str, list[str]]] = empty_list()
    updates: Optional[Union[str, list[str]]] = empty_list()
    errata: Optional[Union[str, list[str]]] = empty_list()
    retention_limit: Optional[Union[str, list[str]]] = empty_list()
    ethical_reviews: Optional[Union[str, list[str]]] = empty_list()
    data_protection_impacts: Optional[Union[str, list[str]]] = empty_list()
    ip_restrictions: Optional[Union[str, list[str]]] = empty_list()
    regulatory_restrictions: Optional[Union[str, list[str]]] = empty_list()
    human_subject_research: Optional[Union[str, list[str]]] = empty_list()
    informed_consent: Optional[Union[str, list[str]]] = empty_list()
    vulnerable_populations: Optional[Union[str, list[str]]] = empty_list()
    is_deidentified: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetId):
            self.id = DatasetId(self.id)

        if self.bytes is not None and not isinstance(self.bytes, int):
            self.bytes = int(self.bytes)

        if self.encoding is not None and not isinstance(self.encoding, str):
            self.encoding = str(self.encoding)

        if self.format is not None and not isinstance(self.format, str):
            self.format = str(self.format)

        if self.compression is not None and not isinstance(self.compression, CompressionEnum):
            self.compression = CompressionEnum(self.compression)

        if self.hash is not None and not isinstance(self.hash, str):
            self.hash = str(self.hash)

        if self.md5 is not None and not isinstance(self.md5, str):
            self.md5 = str(self.md5)

        if self.sha256 is not None and not isinstance(self.sha256, str):
            self.sha256 = str(self.sha256)

        if self.media_type is not None and not isinstance(self.media_type, str):
            self.media_type = str(self.media_type)

        if self.is_tabular is not None and not isinstance(self.is_tabular, Bool):
            self.is_tabular = Bool(self.is_tabular)

        if self.dialect is not None and not isinstance(self.dialect, str):
            self.dialect = str(self.dialect)

        if self.path is not None and not isinstance(self.path, str):
            self.path = str(self.path)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.citation is not None and not isinstance(self.citation, str):
            self.citation = str(self.citation)

        if self.doi is not None and not isinstance(self.doi, URIorCURIE):
            self.doi = URIorCURIE(self.doi)

        if not isinstance(self.keywords, list):
            self.keywords = [self.keywords] if self.keywords is not None else []
        self.keywords = [v if isinstance(v, str) else str(v) for v in self.keywords]

        if self.language is not None and not isinstance(self.language, str):
            self.language = str(self.language)

        if self.page is not None and not isinstance(self.page, URI):
            self.page = URI(self.page)

        if self.download_url is not None and not isinstance(self.download_url, URI):
            self.download_url = URI(self.download_url)

        if self.was_derived_from is not None and not isinstance(self.was_derived_from, str):
            self.was_derived_from = str(self.was_derived_from)

        if not isinstance(self.parent_datasets, list):
            self.parent_datasets = [self.parent_datasets] if self.parent_datasets is not None else []
        self.parent_datasets = [v if isinstance(v, str) else str(v) for v in self.parent_datasets]

        if not isinstance(self.related_datasets, list):
            self.related_datasets = [self.related_datasets] if self.related_datasets is not None else []
        self.related_datasets = [v if isinstance(v, str) else str(v) for v in self.related_datasets]

        if not isinstance(self.creators, list):
            self.creators = [self.creators] if self.creators is not None else []
        self.creators = [v if isinstance(v, str) else str(v) for v in self.creators]

        if self.created_on is not None and not isinstance(self.created_on, XSDDate):
            self.created_on = XSDDate(self.created_on)

        if not isinstance(self.created_by, list):
            self.created_by = [self.created_by] if self.created_by is not None else []
        self.created_by = [v if isinstance(v, str) else str(v) for v in self.created_by]

        if self.issued is not None and not isinstance(self.issued, XSDDate):
            self.issued = XSDDate(self.issued)

        if self.last_updated_on is not None and not isinstance(self.last_updated_on, XSDDate):
            self.last_updated_on = XSDDate(self.last_updated_on)

        if not isinstance(self.modified_by, list):
            self.modified_by = [self.modified_by] if self.modified_by is not None else []
        self.modified_by = [v if isinstance(v, str) else str(v) for v in self.modified_by]

        if self.publisher is not None and not isinstance(self.publisher, URI):
            self.publisher = URI(self.publisher)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if not isinstance(self.funders, list):
            self.funders = [self.funders] if self.funders is not None else []
        self.funders = [v if isinstance(v, str) else str(v) for v in self.funders]

        if self.conforms_to is not None and not isinstance(self.conforms_to, URI):
            self.conforms_to = URI(self.conforms_to)

        if self.conforms_to_schema is not None and not isinstance(self.conforms_to_schema, URI):
            self.conforms_to_schema = URI(self.conforms_to_schema)

        if self.conforms_to_class is not None and not isinstance(self.conforms_to_class, URIorCURIE):
            self.conforms_to_class = URIorCURIE(self.conforms_to_class)

        if self.status is not None and not isinstance(self.status, URI):
            self.status = URI(self.status)

        if not isinstance(self.purposes, list):
            self.purposes = [self.purposes] if self.purposes is not None else []
        self.purposes = [v if isinstance(v, str) else str(v) for v in self.purposes]

        if not isinstance(self.tasks, list):
            self.tasks = [self.tasks] if self.tasks is not None else []
        self.tasks = [v if isinstance(v, str) else str(v) for v in self.tasks]

        if not isinstance(self.addressing_gaps, list):
            self.addressing_gaps = [self.addressing_gaps] if self.addressing_gaps is not None else []
        self.addressing_gaps = [v if isinstance(v, str) else str(v) for v in self.addressing_gaps]

        if not isinstance(self.instances, list):
            self.instances = [self.instances] if self.instances is not None else []
        self.instances = [v if isinstance(v, str) else str(v) for v in self.instances]

        if not isinstance(self.variables, list):
            self.variables = [self.variables] if self.variables is not None else []
        self.variables = [v if isinstance(v, str) else str(v) for v in self.variables]

        if not isinstance(self.subsets, list):
            self.subsets = [self.subsets] if self.subsets is not None else []
        self.subsets = [v if isinstance(v, str) else str(v) for v in self.subsets]

        if not isinstance(self.subpopulations, list):
            self.subpopulations = [self.subpopulations] if self.subpopulations is not None else []
        self.subpopulations = [v if isinstance(v, str) else str(v) for v in self.subpopulations]

        if not isinstance(self.anomalies, list):
            self.anomalies = [self.anomalies] if self.anomalies is not None else []
        self.anomalies = [v if isinstance(v, str) else str(v) for v in self.anomalies]

        if not isinstance(self.sensitive_elements, list):
            self.sensitive_elements = [self.sensitive_elements] if self.sensitive_elements is not None else []
        self.sensitive_elements = [v if isinstance(v, str) else str(v) for v in self.sensitive_elements]

        if not isinstance(self.confidential_elements, list):
            self.confidential_elements = [self.confidential_elements] if self.confidential_elements is not None else []
        self.confidential_elements = [v if isinstance(v, str) else str(v) for v in self.confidential_elements]

        if not isinstance(self.known_biases, list):
            self.known_biases = [self.known_biases] if self.known_biases is not None else []
        self.known_biases = [v if isinstance(v, str) else str(v) for v in self.known_biases]

        if not isinstance(self.known_limitations, list):
            self.known_limitations = [self.known_limitations] if self.known_limitations is not None else []
        self.known_limitations = [v if isinstance(v, str) else str(v) for v in self.known_limitations]

        if not isinstance(self.content_warnings, list):
            self.content_warnings = [self.content_warnings] if self.content_warnings is not None else []
        self.content_warnings = [v if isinstance(v, str) else str(v) for v in self.content_warnings]

        if not isinstance(self.external_resources, list):
            self.external_resources = [self.external_resources] if self.external_resources is not None else []
        self.external_resources = [v if isinstance(v, str) else str(v) for v in self.external_resources]

        if not isinstance(self.collection_mechanisms, list):
            self.collection_mechanisms = [self.collection_mechanisms] if self.collection_mechanisms is not None else []
        self.collection_mechanisms = [v if isinstance(v, str) else str(v) for v in self.collection_mechanisms]

        if not isinstance(self.acquisition_methods, list):
            self.acquisition_methods = [self.acquisition_methods] if self.acquisition_methods is not None else []
        self.acquisition_methods = [v if isinstance(v, str) else str(v) for v in self.acquisition_methods]

        if not isinstance(self.collection_timeframes, list):
            self.collection_timeframes = [self.collection_timeframes] if self.collection_timeframes is not None else []
        self.collection_timeframes = [v if isinstance(v, str) else str(v) for v in self.collection_timeframes]

        if not isinstance(self.data_collectors, list):
            self.data_collectors = [self.data_collectors] if self.data_collectors is not None else []
        self.data_collectors = [v if isinstance(v, str) else str(v) for v in self.data_collectors]

        if not isinstance(self.sampling_strategies, list):
            self.sampling_strategies = [self.sampling_strategies] if self.sampling_strategies is not None else []
        self.sampling_strategies = [v if isinstance(v, str) else str(v) for v in self.sampling_strategies]

        if not isinstance(self.missing_data_documentation, list):
            self.missing_data_documentation = [self.missing_data_documentation] if self.missing_data_documentation is not None else []
        self.missing_data_documentation = [v if isinstance(v, str) else str(v) for v in self.missing_data_documentation]

        if not isinstance(self.raw_sources, list):
            self.raw_sources = [self.raw_sources] if self.raw_sources is not None else []
        self.raw_sources = [v if isinstance(v, str) else str(v) for v in self.raw_sources]

        if not isinstance(self.raw_data_sources, list):
            self.raw_data_sources = [self.raw_data_sources] if self.raw_data_sources is not None else []
        self.raw_data_sources = [v if isinstance(v, str) else str(v) for v in self.raw_data_sources]

        if not isinstance(self.preprocessing_strategies, list):
            self.preprocessing_strategies = [self.preprocessing_strategies] if self.preprocessing_strategies is not None else []
        self.preprocessing_strategies = [v if isinstance(v, str) else str(v) for v in self.preprocessing_strategies]

        if not isinstance(self.cleaning_strategies, list):
            self.cleaning_strategies = [self.cleaning_strategies] if self.cleaning_strategies is not None else []
        self.cleaning_strategies = [v if isinstance(v, str) else str(v) for v in self.cleaning_strategies]

        if not isinstance(self.labeling_strategies, list):
            self.labeling_strategies = [self.labeling_strategies] if self.labeling_strategies is not None else []
        self.labeling_strategies = [v if isinstance(v, str) else str(v) for v in self.labeling_strategies]

        if not isinstance(self.imputation_protocols, list):
            self.imputation_protocols = [self.imputation_protocols] if self.imputation_protocols is not None else []
        self.imputation_protocols = [v if isinstance(v, str) else str(v) for v in self.imputation_protocols]

        if not isinstance(self.annotation_analyses, list):
            self.annotation_analyses = [self.annotation_analyses] if self.annotation_analyses is not None else []
        self.annotation_analyses = [v if isinstance(v, str) else str(v) for v in self.annotation_analyses]

        if not isinstance(self.machine_annotation_tools, list):
            self.machine_annotation_tools = [self.machine_annotation_tools] if self.machine_annotation_tools is not None else []
        self.machine_annotation_tools = [v if isinstance(v, str) else str(v) for v in self.machine_annotation_tools]

        if not isinstance(self.intended_uses, list):
            self.intended_uses = [self.intended_uses] if self.intended_uses is not None else []
        self.intended_uses = [v if isinstance(v, str) else str(v) for v in self.intended_uses]

        if not isinstance(self.other_tasks, list):
            self.other_tasks = [self.other_tasks] if self.other_tasks is not None else []
        self.other_tasks = [v if isinstance(v, str) else str(v) for v in self.other_tasks]

        if not isinstance(self.existing_uses, list):
            self.existing_uses = [self.existing_uses] if self.existing_uses is not None else []
        self.existing_uses = [v if isinstance(v, str) else str(v) for v in self.existing_uses]

        if not isinstance(self.discouraged_uses, list):
            self.discouraged_uses = [self.discouraged_uses] if self.discouraged_uses is not None else []
        self.discouraged_uses = [v if isinstance(v, str) else str(v) for v in self.discouraged_uses]

        if not isinstance(self.prohibited_uses, list):
            self.prohibited_uses = [self.prohibited_uses] if self.prohibited_uses is not None else []
        self.prohibited_uses = [v if isinstance(v, str) else str(v) for v in self.prohibited_uses]

        if not isinstance(self.future_use_impacts, list):
            self.future_use_impacts = [self.future_use_impacts] if self.future_use_impacts is not None else []
        self.future_use_impacts = [v if isinstance(v, str) else str(v) for v in self.future_use_impacts]

        if not isinstance(self.distribution_formats, list):
            self.distribution_formats = [self.distribution_formats] if self.distribution_formats is not None else []
        self.distribution_formats = [v if isinstance(v, str) else str(v) for v in self.distribution_formats]

        if not isinstance(self.distribution_dates, list):
            self.distribution_dates = [self.distribution_dates] if self.distribution_dates is not None else []
        self.distribution_dates = [v if isinstance(v, str) else str(v) for v in self.distribution_dates]

        if self.license is not None and not isinstance(self.license, str):
            self.license = str(self.license)

        if not isinstance(self.license_and_use_terms, list):
            self.license_and_use_terms = [self.license_and_use_terms] if self.license_and_use_terms is not None else []
        self.license_and_use_terms = [v if isinstance(v, str) else str(v) for v in self.license_and_use_terms]

        if not isinstance(self.extension_mechanism, list):
            self.extension_mechanism = [self.extension_mechanism] if self.extension_mechanism is not None else []
        self.extension_mechanism = [v if isinstance(v, str) else str(v) for v in self.extension_mechanism]

        if not isinstance(self.use_repository, list):
            self.use_repository = [self.use_repository] if self.use_repository is not None else []
        self.use_repository = [v if isinstance(v, str) else str(v) for v in self.use_repository]

        if not isinstance(self.version_access, list):
            self.version_access = [self.version_access] if self.version_access is not None else []
        self.version_access = [v if isinstance(v, str) else str(v) for v in self.version_access]

        if not isinstance(self.maintainers, list):
            self.maintainers = [self.maintainers] if self.maintainers is not None else []
        self.maintainers = [v if isinstance(v, str) else str(v) for v in self.maintainers]

        if not isinstance(self.updates, list):
            self.updates = [self.updates] if self.updates is not None else []
        self.updates = [v if isinstance(v, str) else str(v) for v in self.updates]

        if not isinstance(self.errata, list):
            self.errata = [self.errata] if self.errata is not None else []
        self.errata = [v if isinstance(v, str) else str(v) for v in self.errata]

        if not isinstance(self.retention_limit, list):
            self.retention_limit = [self.retention_limit] if self.retention_limit is not None else []
        self.retention_limit = [v if isinstance(v, str) else str(v) for v in self.retention_limit]

        if not isinstance(self.ethical_reviews, list):
            self.ethical_reviews = [self.ethical_reviews] if self.ethical_reviews is not None else []
        self.ethical_reviews = [v if isinstance(v, str) else str(v) for v in self.ethical_reviews]

        if not isinstance(self.data_protection_impacts, list):
            self.data_protection_impacts = [self.data_protection_impacts] if self.data_protection_impacts is not None else []
        self.data_protection_impacts = [v if isinstance(v, str) else str(v) for v in self.data_protection_impacts]

        if not isinstance(self.ip_restrictions, list):
            self.ip_restrictions = [self.ip_restrictions] if self.ip_restrictions is not None else []
        self.ip_restrictions = [v if isinstance(v, str) else str(v) for v in self.ip_restrictions]

        if not isinstance(self.regulatory_restrictions, list):
            self.regulatory_restrictions = [self.regulatory_restrictions] if self.regulatory_restrictions is not None else []
        self.regulatory_restrictions = [v if isinstance(v, str) else str(v) for v in self.regulatory_restrictions]

        if not isinstance(self.human_subject_research, list):
            self.human_subject_research = [self.human_subject_research] if self.human_subject_research is not None else []
        self.human_subject_research = [v if isinstance(v, str) else str(v) for v in self.human_subject_research]

        if not isinstance(self.informed_consent, list):
            self.informed_consent = [self.informed_consent] if self.informed_consent is not None else []
        self.informed_consent = [v if isinstance(v, str) else str(v) for v in self.informed_consent]

        if not isinstance(self.vulnerable_populations, list):
            self.vulnerable_populations = [self.vulnerable_populations] if self.vulnerable_populations is not None else []
        self.vulnerable_populations = [v if isinstance(v, str) else str(v) for v in self.vulnerable_populations]

        if self.is_deidentified is not None and not isinstance(self.is_deidentified, Bool):
            self.is_deidentified = Bool(self.is_deidentified)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DataSubset(Dataset):
    """
    A subset of a dataset, potentially representing a split (train/test/validation), a subpopulation, or another
    logical partition of the data.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DSLIM["DataSubset"]
    class_class_curie: ClassVar[str] = "d4dslim:DataSubset"
    class_name: ClassVar[str] = "DataSubset"
    class_model_uri: ClassVar[URIRef] = D4DSLIM.DataSubset

    id: Union[str, DataSubsetId] = None
    is_data_split: Optional[Union[bool, Bool]] = None
    is_subpopulation: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DataSubsetId):
            self.id = DataSubsetId(self.id)

        if self.is_data_split is not None and not isinstance(self.is_data_split, Bool):
            self.is_data_split = Bool(self.is_data_split)

        if self.is_subpopulation is not None and not isinstance(self.is_subpopulation, Bool):
            self.is_subpopulation = Bool(self.is_subpopulation)

        super().__post_init__(**kwargs)


# Enumerations
class CompressionEnum(EnumDefinitionImpl):
    """
    Compression format enumerations
    """
    GZIP = PermissibleValue(
        text="GZIP",
        description="gzip compression (.gz)")
    TAR = PermissibleValue(
        text="TAR",
        description="tar archive (.tar)")
    ZIP = PermissibleValue(
        text="ZIP",
        description="zip compression (.zip)")
    BZIP2 = PermissibleValue(
        text="BZIP2",
        description="bzip2 compression (.bz2)")
    XZ = PermissibleValue(
        text="XZ",
        description="xz compression (.xz)")
    ZSTD = PermissibleValue(
        text="ZSTD",
        description="Zstandard compression (.zst)")

    _defn = EnumDefinition(
        name="CompressionEnum",
        description="Compression format enumerations",
    )

# Slots
class slots:
    pass

slots.id = Slot(uri=D4DSLIM.id, name="id", curie=D4DSLIM.curie('id'),
                   model_uri=D4DSLIM.id, domain=None, range=URIRef)

slots.name = Slot(uri=D4DSLIM.name, name="name", curie=D4DSLIM.curie('name'),
                   model_uri=D4DSLIM.name, domain=None, range=Optional[str])

slots.title = Slot(uri=DCTERMS.title, name="title", curie=DCTERMS.curie('title'),
                   model_uri=D4DSLIM.title, domain=None, range=Optional[str])

slots.description = Slot(uri=DCTERMS.description, name="description", curie=DCTERMS.curie('description'),
                   model_uri=D4DSLIM.description, domain=None, range=Optional[str])

slots.keywords = Slot(uri=SCHEMA.keywords, name="keywords", curie=SCHEMA.curie('keywords'),
                   model_uri=D4DSLIM.keywords, domain=None, range=Optional[Union[str, list[str]]])

slots.language = Slot(uri=SCHEMA.inLanguage, name="language", curie=SCHEMA.curie('inLanguage'),
                   model_uri=D4DSLIM.language, domain=None, range=Optional[str])

slots.citation = Slot(uri=D4DSLIM.citation, name="citation", curie=D4DSLIM.curie('citation'),
                   model_uri=D4DSLIM.citation, domain=None, range=Optional[str])

slots.doi = Slot(uri=SCHEMA.identifier, name="doi", curie=SCHEMA.curie('identifier'),
                   model_uri=D4DSLIM.doi, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.page = Slot(uri=SCHEMA.url, name="page", curie=SCHEMA.curie('url'),
                   model_uri=D4DSLIM.page, domain=None, range=Optional[Union[str, URI]])

slots.download_url = Slot(uri=DCAT.downloadURL, name="download_url", curie=DCAT.curie('downloadURL'),
                   model_uri=D4DSLIM.download_url, domain=None, range=Optional[Union[str, URI]])

slots.url = Slot(uri=SCHEMA.url, name="url", curie=SCHEMA.curie('url'),
                   model_uri=D4DSLIM.url, domain=None, range=Optional[Union[str, URI]])

slots.license = Slot(uri=DCTERMS.license, name="license", curie=DCTERMS.curie('license'),
                   model_uri=D4DSLIM.license, domain=None, range=Optional[str])

slots.license_and_use_terms = Slot(uri=D4DSLIM.license_and_use_terms, name="license_and_use_terms", curie=D4DSLIM.curie('license_and_use_terms'),
                   model_uri=D4DSLIM.license_and_use_terms, domain=None, range=Optional[Union[str, list[str]]])

slots.version = Slot(uri=SCHEMA.version, name="version", curie=SCHEMA.curie('version'),
                   model_uri=D4DSLIM.version, domain=None, range=Optional[str])

slots.status = Slot(uri=D4DSLIM.status, name="status", curie=D4DSLIM.curie('status'),
                   model_uri=D4DSLIM.status, domain=None, range=Optional[Union[str, URI]])

slots.issued = Slot(uri=DCTERMS.issued, name="issued", curie=DCTERMS.curie('issued'),
                   model_uri=D4DSLIM.issued, domain=None, range=Optional[Union[str, XSDDate]])

slots.created_on = Slot(uri=SCHEMA.dateCreated, name="created_on", curie=SCHEMA.curie('dateCreated'),
                   model_uri=D4DSLIM.created_on, domain=None, range=Optional[Union[str, XSDDate]])

slots.last_updated_on = Slot(uri=SCHEMA.dateModified, name="last_updated_on", curie=SCHEMA.curie('dateModified'),
                   model_uri=D4DSLIM.last_updated_on, domain=None, range=Optional[Union[str, XSDDate]])

slots.created_by = Slot(uri=SCHEMA.creator, name="created_by", curie=SCHEMA.curie('creator'),
                   model_uri=D4DSLIM.created_by, domain=None, range=Optional[Union[str, list[str]]])

slots.modified_by = Slot(uri=D4DSLIM.modified_by, name="modified_by", curie=D4DSLIM.curie('modified_by'),
                   model_uri=D4DSLIM.modified_by, domain=None, range=Optional[Union[str, list[str]]])

slots.publisher = Slot(uri=SCHEMA.publisher, name="publisher", curie=SCHEMA.curie('publisher'),
                   model_uri=D4DSLIM.publisher, domain=None, range=Optional[Union[str, URI]])

slots.creators = Slot(uri=D4DSLIM.creators, name="creators", curie=D4DSLIM.curie('creators'),
                   model_uri=D4DSLIM.creators, domain=None, range=Optional[Union[str, list[str]]])

slots.funders = Slot(uri=D4DSLIM.funders, name="funders", curie=D4DSLIM.curie('funders'),
                   model_uri=D4DSLIM.funders, domain=None, range=Optional[Union[str, list[str]]])

slots.was_derived_from = Slot(uri=PROV.wasDerivedFrom, name="was_derived_from", curie=PROV.curie('wasDerivedFrom'),
                   model_uri=D4DSLIM.was_derived_from, domain=None, range=Optional[str])

slots.parent_datasets = Slot(uri=D4DSLIM.parent_datasets, name="parent_datasets", curie=D4DSLIM.curie('parent_datasets'),
                   model_uri=D4DSLIM.parent_datasets, domain=None, range=Optional[Union[str, list[str]]])

slots.related_datasets = Slot(uri=D4DSLIM.related_datasets, name="related_datasets", curie=D4DSLIM.curie('related_datasets'),
                   model_uri=D4DSLIM.related_datasets, domain=None, range=Optional[Union[str, list[str]]])

slots.conforms_to = Slot(uri=DCTERMS.conformsTo, name="conforms_to", curie=DCTERMS.curie('conformsTo'),
                   model_uri=D4DSLIM.conforms_to, domain=None, range=Optional[Union[str, URI]])

slots.conforms_to_schema = Slot(uri=D4DSLIM.conforms_to_schema, name="conforms_to_schema", curie=D4DSLIM.curie('conforms_to_schema'),
                   model_uri=D4DSLIM.conforms_to_schema, domain=None, range=Optional[Union[str, URI]])

slots.conforms_to_class = Slot(uri=D4DSLIM.conforms_to_class, name="conforms_to_class", curie=D4DSLIM.curie('conforms_to_class'),
                   model_uri=D4DSLIM.conforms_to_class, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.bytes = Slot(uri=SCHEMA.contentSize, name="bytes", curie=SCHEMA.curie('contentSize'),
                   model_uri=D4DSLIM.bytes, domain=None, range=Optional[int])

slots.compression = Slot(uri=D4DSLIM.compression, name="compression", curie=D4DSLIM.curie('compression'),
                   model_uri=D4DSLIM.compression, domain=None, range=Optional[Union[str, "CompressionEnum"]])

slots.encoding = Slot(uri=SCHEMA.encoding, name="encoding", curie=SCHEMA.curie('encoding'),
                   model_uri=D4DSLIM.encoding, domain=None, range=Optional[str])

slots.format = Slot(uri=D4DSLIM.format, name="format", curie=D4DSLIM.curie('format'),
                   model_uri=D4DSLIM.format, domain=None, range=Optional[str])

slots.media_type = Slot(uri=SCHEMA.encodingFormat, name="media_type", curie=SCHEMA.curie('encodingFormat'),
                   model_uri=D4DSLIM.media_type, domain=None, range=Optional[str])

slots.hash = Slot(uri=D4DSLIM.hash, name="hash", curie=D4DSLIM.curie('hash'),
                   model_uri=D4DSLIM.hash, domain=None, range=Optional[str])

slots.md5 = Slot(uri=D4DSLIM.md5, name="md5", curie=D4DSLIM.curie('md5'),
                   model_uri=D4DSLIM.md5, domain=None, range=Optional[str])

slots.sha256 = Slot(uri=D4DSLIM.sha256, name="sha256", curie=D4DSLIM.curie('sha256'),
                   model_uri=D4DSLIM.sha256, domain=None, range=Optional[str])

slots.is_tabular = Slot(uri=D4DSLIM.is_tabular, name="is_tabular", curie=D4DSLIM.curie('is_tabular'),
                   model_uri=D4DSLIM.is_tabular, domain=None, range=Optional[Union[bool, Bool]])

slots.dialect = Slot(uri=D4DSLIM.dialect, name="dialect", curie=D4DSLIM.curie('dialect'),
                   model_uri=D4DSLIM.dialect, domain=None, range=Optional[str])

slots.path = Slot(uri=D4DSLIM.path, name="path", curie=D4DSLIM.curie('path'),
                   model_uri=D4DSLIM.path, domain=None, range=Optional[str])

slots.resources = Slot(uri=D4DSLIM.resources, name="resources", curie=D4DSLIM.curie('resources'),
                   model_uri=D4DSLIM.resources, domain=None, range=Optional[Union[str, list[str]]])

slots.purposes = Slot(uri=D4DSLIM.purposes, name="purposes", curie=D4DSLIM.curie('purposes'),
                   model_uri=D4DSLIM.purposes, domain=None, range=Optional[Union[str, list[str]]])

slots.tasks = Slot(uri=D4DSLIM.tasks, name="tasks", curie=D4DSLIM.curie('tasks'),
                   model_uri=D4DSLIM.tasks, domain=None, range=Optional[Union[str, list[str]]])

slots.addressing_gaps = Slot(uri=D4DSLIM.addressing_gaps, name="addressing_gaps", curie=D4DSLIM.curie('addressing_gaps'),
                   model_uri=D4DSLIM.addressing_gaps, domain=None, range=Optional[Union[str, list[str]]])

slots.instances = Slot(uri=D4DSLIM.instances, name="instances", curie=D4DSLIM.curie('instances'),
                   model_uri=D4DSLIM.instances, domain=None, range=Optional[Union[str, list[str]]])

slots.variables = Slot(uri=D4DSLIM.variables, name="variables", curie=D4DSLIM.curie('variables'),
                   model_uri=D4DSLIM.variables, domain=None, range=Optional[Union[str, list[str]]])

slots.subsets = Slot(uri=D4DSLIM.subsets, name="subsets", curie=D4DSLIM.curie('subsets'),
                   model_uri=D4DSLIM.subsets, domain=None, range=Optional[Union[str, list[str]]])

slots.subpopulations = Slot(uri=D4DSLIM.subpopulations, name="subpopulations", curie=D4DSLIM.curie('subpopulations'),
                   model_uri=D4DSLIM.subpopulations, domain=None, range=Optional[Union[str, list[str]]])

slots.anomalies = Slot(uri=D4DSLIM.anomalies, name="anomalies", curie=D4DSLIM.curie('anomalies'),
                   model_uri=D4DSLIM.anomalies, domain=None, range=Optional[Union[str, list[str]]])

slots.sensitive_elements = Slot(uri=D4DSLIM.sensitive_elements, name="sensitive_elements", curie=D4DSLIM.curie('sensitive_elements'),
                   model_uri=D4DSLIM.sensitive_elements, domain=None, range=Optional[Union[str, list[str]]])

slots.confidential_elements = Slot(uri=D4DSLIM.confidential_elements, name="confidential_elements", curie=D4DSLIM.curie('confidential_elements'),
                   model_uri=D4DSLIM.confidential_elements, domain=None, range=Optional[Union[str, list[str]]])

slots.known_biases = Slot(uri=D4DSLIM.known_biases, name="known_biases", curie=D4DSLIM.curie('known_biases'),
                   model_uri=D4DSLIM.known_biases, domain=None, range=Optional[Union[str, list[str]]])

slots.known_limitations = Slot(uri=D4DSLIM.known_limitations, name="known_limitations", curie=D4DSLIM.curie('known_limitations'),
                   model_uri=D4DSLIM.known_limitations, domain=None, range=Optional[Union[str, list[str]]])

slots.content_warnings = Slot(uri=D4DSLIM.content_warnings, name="content_warnings", curie=D4DSLIM.curie('content_warnings'),
                   model_uri=D4DSLIM.content_warnings, domain=None, range=Optional[Union[str, list[str]]])

slots.external_resources = Slot(uri=D4DSLIM.external_resources, name="external_resources", curie=D4DSLIM.curie('external_resources'),
                   model_uri=D4DSLIM.external_resources, domain=None, range=Optional[Union[str, list[str]]])

slots.collection_mechanisms = Slot(uri=D4DSLIM.collection_mechanisms, name="collection_mechanisms", curie=D4DSLIM.curie('collection_mechanisms'),
                   model_uri=D4DSLIM.collection_mechanisms, domain=None, range=Optional[Union[str, list[str]]])

slots.acquisition_methods = Slot(uri=D4DSLIM.acquisition_methods, name="acquisition_methods", curie=D4DSLIM.curie('acquisition_methods'),
                   model_uri=D4DSLIM.acquisition_methods, domain=None, range=Optional[Union[str, list[str]]])

slots.collection_timeframes = Slot(uri=D4DSLIM.collection_timeframes, name="collection_timeframes", curie=D4DSLIM.curie('collection_timeframes'),
                   model_uri=D4DSLIM.collection_timeframes, domain=None, range=Optional[Union[str, list[str]]])

slots.data_collectors = Slot(uri=D4DSLIM.data_collectors, name="data_collectors", curie=D4DSLIM.curie('data_collectors'),
                   model_uri=D4DSLIM.data_collectors, domain=None, range=Optional[Union[str, list[str]]])

slots.sampling_strategies = Slot(uri=D4DSLIM.sampling_strategies, name="sampling_strategies", curie=D4DSLIM.curie('sampling_strategies'),
                   model_uri=D4DSLIM.sampling_strategies, domain=None, range=Optional[Union[str, list[str]]])

slots.missing_data_documentation = Slot(uri=D4DSLIM.missing_data_documentation, name="missing_data_documentation", curie=D4DSLIM.curie('missing_data_documentation'),
                   model_uri=D4DSLIM.missing_data_documentation, domain=None, range=Optional[Union[str, list[str]]])

slots.raw_sources = Slot(uri=D4DSLIM.raw_sources, name="raw_sources", curie=D4DSLIM.curie('raw_sources'),
                   model_uri=D4DSLIM.raw_sources, domain=None, range=Optional[Union[str, list[str]]])

slots.raw_data_sources = Slot(uri=D4DSLIM.raw_data_sources, name="raw_data_sources", curie=D4DSLIM.curie('raw_data_sources'),
                   model_uri=D4DSLIM.raw_data_sources, domain=None, range=Optional[Union[str, list[str]]])

slots.preprocessing_strategies = Slot(uri=D4DSLIM.preprocessing_strategies, name="preprocessing_strategies", curie=D4DSLIM.curie('preprocessing_strategies'),
                   model_uri=D4DSLIM.preprocessing_strategies, domain=None, range=Optional[Union[str, list[str]]])

slots.cleaning_strategies = Slot(uri=D4DSLIM.cleaning_strategies, name="cleaning_strategies", curie=D4DSLIM.curie('cleaning_strategies'),
                   model_uri=D4DSLIM.cleaning_strategies, domain=None, range=Optional[Union[str, list[str]]])

slots.labeling_strategies = Slot(uri=D4DSLIM.labeling_strategies, name="labeling_strategies", curie=D4DSLIM.curie('labeling_strategies'),
                   model_uri=D4DSLIM.labeling_strategies, domain=None, range=Optional[Union[str, list[str]]])

slots.imputation_protocols = Slot(uri=D4DSLIM.imputation_protocols, name="imputation_protocols", curie=D4DSLIM.curie('imputation_protocols'),
                   model_uri=D4DSLIM.imputation_protocols, domain=None, range=Optional[Union[str, list[str]]])

slots.annotation_analyses = Slot(uri=D4DSLIM.annotation_analyses, name="annotation_analyses", curie=D4DSLIM.curie('annotation_analyses'),
                   model_uri=D4DSLIM.annotation_analyses, domain=None, range=Optional[Union[str, list[str]]])

slots.machine_annotation_tools = Slot(uri=D4DSLIM.machine_annotation_tools, name="machine_annotation_tools", curie=D4DSLIM.curie('machine_annotation_tools'),
                   model_uri=D4DSLIM.machine_annotation_tools, domain=None, range=Optional[Union[str, list[str]]])

slots.intended_uses = Slot(uri=D4DSLIM.intended_uses, name="intended_uses", curie=D4DSLIM.curie('intended_uses'),
                   model_uri=D4DSLIM.intended_uses, domain=None, range=Optional[Union[str, list[str]]])

slots.other_tasks = Slot(uri=D4DSLIM.other_tasks, name="other_tasks", curie=D4DSLIM.curie('other_tasks'),
                   model_uri=D4DSLIM.other_tasks, domain=None, range=Optional[Union[str, list[str]]])

slots.existing_uses = Slot(uri=D4DSLIM.existing_uses, name="existing_uses", curie=D4DSLIM.curie('existing_uses'),
                   model_uri=D4DSLIM.existing_uses, domain=None, range=Optional[Union[str, list[str]]])

slots.discouraged_uses = Slot(uri=D4DSLIM.discouraged_uses, name="discouraged_uses", curie=D4DSLIM.curie('discouraged_uses'),
                   model_uri=D4DSLIM.discouraged_uses, domain=None, range=Optional[Union[str, list[str]]])

slots.prohibited_uses = Slot(uri=D4DSLIM.prohibited_uses, name="prohibited_uses", curie=D4DSLIM.curie('prohibited_uses'),
                   model_uri=D4DSLIM.prohibited_uses, domain=None, range=Optional[Union[str, list[str]]])

slots.future_use_impacts = Slot(uri=D4DSLIM.future_use_impacts, name="future_use_impacts", curie=D4DSLIM.curie('future_use_impacts'),
                   model_uri=D4DSLIM.future_use_impacts, domain=None, range=Optional[Union[str, list[str]]])

slots.distribution_formats = Slot(uri=D4DSLIM.distribution_formats, name="distribution_formats", curie=D4DSLIM.curie('distribution_formats'),
                   model_uri=D4DSLIM.distribution_formats, domain=None, range=Optional[Union[str, list[str]]])

slots.distribution_dates = Slot(uri=D4DSLIM.distribution_dates, name="distribution_dates", curie=D4DSLIM.curie('distribution_dates'),
                   model_uri=D4DSLIM.distribution_dates, domain=None, range=Optional[Union[str, list[str]]])

slots.extension_mechanism = Slot(uri=D4DSLIM.extension_mechanism, name="extension_mechanism", curie=D4DSLIM.curie('extension_mechanism'),
                   model_uri=D4DSLIM.extension_mechanism, domain=None, range=Optional[Union[str, list[str]]])

slots.use_repository = Slot(uri=D4DSLIM.use_repository, name="use_repository", curie=D4DSLIM.curie('use_repository'),
                   model_uri=D4DSLIM.use_repository, domain=None, range=Optional[Union[str, list[str]]])

slots.version_access = Slot(uri=D4DSLIM.version_access, name="version_access", curie=D4DSLIM.curie('version_access'),
                   model_uri=D4DSLIM.version_access, domain=None, range=Optional[Union[str, list[str]]])

slots.maintainers = Slot(uri=D4DSLIM.maintainers, name="maintainers", curie=D4DSLIM.curie('maintainers'),
                   model_uri=D4DSLIM.maintainers, domain=None, range=Optional[Union[str, list[str]]])

slots.updates = Slot(uri=D4DSLIM.updates, name="updates", curie=D4DSLIM.curie('updates'),
                   model_uri=D4DSLIM.updates, domain=None, range=Optional[Union[str, list[str]]])

slots.errata = Slot(uri=D4DSLIM.errata, name="errata", curie=D4DSLIM.curie('errata'),
                   model_uri=D4DSLIM.errata, domain=None, range=Optional[Union[str, list[str]]])

slots.retention_limit = Slot(uri=D4DSLIM.retention_limit, name="retention_limit", curie=D4DSLIM.curie('retention_limit'),
                   model_uri=D4DSLIM.retention_limit, domain=None, range=Optional[Union[str, list[str]]])

slots.ethical_reviews = Slot(uri=D4DSLIM.ethical_reviews, name="ethical_reviews", curie=D4DSLIM.curie('ethical_reviews'),
                   model_uri=D4DSLIM.ethical_reviews, domain=None, range=Optional[Union[str, list[str]]])

slots.data_protection_impacts = Slot(uri=D4DSLIM.data_protection_impacts, name="data_protection_impacts", curie=D4DSLIM.curie('data_protection_impacts'),
                   model_uri=D4DSLIM.data_protection_impacts, domain=None, range=Optional[Union[str, list[str]]])

slots.ip_restrictions = Slot(uri=D4DSLIM.ip_restrictions, name="ip_restrictions", curie=D4DSLIM.curie('ip_restrictions'),
                   model_uri=D4DSLIM.ip_restrictions, domain=None, range=Optional[Union[str, list[str]]])

slots.regulatory_restrictions = Slot(uri=D4DSLIM.regulatory_restrictions, name="regulatory_restrictions", curie=D4DSLIM.curie('regulatory_restrictions'),
                   model_uri=D4DSLIM.regulatory_restrictions, domain=None, range=Optional[Union[str, list[str]]])

slots.human_subject_research = Slot(uri=D4DSLIM.human_subject_research, name="human_subject_research", curie=D4DSLIM.curie('human_subject_research'),
                   model_uri=D4DSLIM.human_subject_research, domain=None, range=Optional[Union[str, list[str]]])

slots.informed_consent = Slot(uri=D4DSLIM.informed_consent, name="informed_consent", curie=D4DSLIM.curie('informed_consent'),
                   model_uri=D4DSLIM.informed_consent, domain=None, range=Optional[Union[str, list[str]]])

slots.vulnerable_populations = Slot(uri=D4DSLIM.vulnerable_populations, name="vulnerable_populations", curie=D4DSLIM.curie('vulnerable_populations'),
                   model_uri=D4DSLIM.vulnerable_populations, domain=None, range=Optional[Union[str, list[str]]])

slots.is_deidentified = Slot(uri=D4DSLIM.is_deidentified, name="is_deidentified", curie=D4DSLIM.curie('is_deidentified'),
                   model_uri=D4DSLIM.is_deidentified, domain=None, range=Optional[Union[bool, Bool]])

slots.is_data_split = Slot(uri=D4DSLIM.is_data_split, name="is_data_split", curie=D4DSLIM.curie('is_data_split'),
                   model_uri=D4DSLIM.is_data_split, domain=None, range=Optional[Union[bool, Bool]])

slots.is_subpopulation = Slot(uri=D4DSLIM.is_subpopulation, name="is_subpopulation", curie=D4DSLIM.curie('is_subpopulation'),
                   model_uri=D4DSLIM.is_subpopulation, domain=None, range=Optional[Union[bool, Bool]])

slots.DatasetCollection_resources = Slot(uri=D4DSLIM.resources, name="DatasetCollection_resources", curie=D4DSLIM.curie('resources'),
                   model_uri=D4DSLIM.DatasetCollection_resources, domain=DatasetCollection, range=Optional[Union[str, list[str]]])

slots.DataSubset_is_data_split = Slot(uri=D4DSLIM.is_data_split, name="DataSubset_is_data_split", curie=D4DSLIM.curie('is_data_split'),
                   model_uri=D4DSLIM.DataSubset_is_data_split, domain=DataSubset, range=Optional[Union[bool, Bool]])

slots.DataSubset_is_subpopulation = Slot(uri=D4DSLIM.is_subpopulation, name="DataSubset_is_subpopulation", curie=D4DSLIM.curie('is_subpopulation'),
                   model_uri=D4DSLIM.DataSubset_is_subpopulation, domain=DataSubset, range=Optional[Union[bool, Bool]])
