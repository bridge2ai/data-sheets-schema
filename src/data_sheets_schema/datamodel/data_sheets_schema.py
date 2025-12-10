# Auto generated from data_sheets_schema.yaml by pythongen.py version: 0.0.1
# Generation date: 2025-12-06T14:00:42
# Schema: data-sheets-schema
#
# id: https://w3id.org/bridge2ai/data-sheets-schema
# description: A LinkML schema for Datasheets for Datasets.
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

from linkml_runtime.linkml_model.types import Boolean, Date, Datetime, Float, Integer, String, Uri, Uriorcurie
from linkml_runtime.utils.metamodelcore import Bool, URI, URIorCURIE, XSDDate, XSDDateTime

metamodel_version = "1.7.0"
version = None

# Namespaces
AIO = CurieNamespace('AIO', 'https://w3id.org/aio/')
B2AI_STANDARD = CurieNamespace('B2AI_STANDARD', 'https://w3id.org/bridge2ai/b2ai-standards-registry/')
B2AI_SUBSTRATE = CurieNamespace('B2AI_SUBSTRATE', 'https://w3id.org/bridge2ai/b2ai-standards-registry/')
B2AI_TOPIC = CurieNamespace('B2AI_TOPIC', 'https://w3id.org/bridge2ai/b2ai-standards-registry/')
DUO = CurieNamespace('DUO', 'http://purl.obolibrary.org/obo/DUO_')
BIOLINK = CurieNamespace('biolink', 'https://w3id.org/biolink/vocab/')
D4DCOMPOSITION = CurieNamespace('d4dcomposition', 'https://w3id.org/bridge2ai/data-sheets-schema/composition#')
D4DDATAGOVERNANCE = CurieNamespace('d4ddatagovernance', 'https://w3id.org/bridge2ai/data-sheets-schema/data-governance#')
D4DDISTRIBUTION = CurieNamespace('d4ddistribution', 'https://w3id.org/bridge2ai/data-sheets-schema/distribution#')
D4DETHICS = CurieNamespace('d4dethics', 'https://w3id.org/bridge2ai/data-sheets-schema/ethics#')
D4DHUMAN = CurieNamespace('d4dhuman', 'https://w3id.org/bridge2ai/data-sheets-schema/human#')
D4DMAINTENANCE = CurieNamespace('d4dmaintenance', 'https://w3id.org/bridge2ai/data-sheets-schema/maintenance#')
D4DMOTIVATION = CurieNamespace('d4dmotivation', 'https://w3id.org/bridge2ai/data-sheets-schema/motivation#')
D4DPREPROCESSING = CurieNamespace('d4dpreprocessing', 'https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling#')
D4DUSES = CurieNamespace('d4duses', 'https://w3id.org/bridge2ai/data-sheets-schema/uses#')
D4DVARIABLES = CurieNamespace('d4dvariables', 'https://w3id.org/bridge2ai/data-sheets-schema/variables#')
DATA_SHEETS_SCHEMA = CurieNamespace('data_sheets_schema', 'https://w3id.org/bridge2ai/data-sheets-schema/')
DATASETS = CurieNamespace('datasets', 'https://w3id.org/linkml/report')
DCAT = CurieNamespace('dcat', 'http://www.w3.org/ns/dcat#')
DCTERMS = CurieNamespace('dcterms', 'http://purl.org/dc/terms/')
EXAMPLE = CurieNamespace('example', 'https://example.org/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
MEDIATYPES = CurieNamespace('mediatypes', 'https://www.iana.org/assignments/media-types/')
PROV = CurieNamespace('prov', 'http://www.w3.org/ns/prov#')
QUDT = CurieNamespace('qudt', 'http://qudt.org/schema/qudt/')
SCHEMA = CurieNamespace('schema', 'http://schema.org/')
SH = CurieNamespace('sh', 'https://w3id.org/shacl/')
SKOS = CurieNamespace('skos', 'http://www.w3.org/2004/02/skos/core#')
DEFAULT_ = DATA_SHEETS_SCHEMA


# Types

# Class references
class NamedThingId(URIorCURIE):
    pass


class OrganizationId(NamedThingId):
    pass


class SoftwareId(NamedThingId):
    pass


class PersonId(NamedThingId):
    pass


class InformationId(NamedThingId):
    pass


class DatasetCollectionId(InformationId):
    pass


class DatasetId(InformationId):
    pass


class DataSubsetId(DatasetId):
    pass


class GrantorId(OrganizationId):
    pass


class GrantId(NamedThingId):
    pass


@dataclass(repr=False)
class NamedThing(YAMLRoot):
    """
    A generic grouping for any identifiable entity.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["Thing"]
    class_class_curie: ClassVar[str] = "schema:Thing"
    class_name: ClassVar[str] = "NamedThing"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.NamedThing

    id: Union[str, NamedThingId] = None
    name: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, NamedThingId):
            self.id = NamedThingId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Organization(NamedThing):
    """
    Represents a group or organization.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["Organization"]
    class_class_curie: ClassVar[str] = "schema:Organization"
    class_name: ClassVar[str] = "Organization"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Organization

    id: Union[str, OrganizationId] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OrganizationId):
            self.id = OrganizationId(self.id)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DatasetProperty(YAMLRoot):
    """
    Represents a single property of a dataset, or a set of related properties.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DatasetProperty"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DatasetProperty"
    class_name: ClassVar[str] = "DatasetProperty"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetProperty

    id: Optional[Union[str, URIorCURIE]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    used_software: Optional[Union[dict[Union[str, SoftwareId], Union[dict, "Software"]], list[Union[dict, "Software"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.id is not None and not isinstance(self.id, URIorCURIE):
            self.id = URIorCURIE(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        self._normalize_inlined_as_list(slot_name="used_software", slot_type=Software, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Software(NamedThing):
    """
    A software program or library.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["SoftwareApplication"]
    class_class_curie: ClassVar[str] = "schema:SoftwareApplication"
    class_name: ClassVar[str] = "Software"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Software

    id: Union[str, SoftwareId] = None
    version: Optional[str] = None
    license: Optional[str] = None
    url: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, SoftwareId):
            self.id = SoftwareId(self.id)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.license is not None and not isinstance(self.license, str):
            self.license = str(self.license)

        if self.url is not None and not isinstance(self.url, str):
            self.url = str(self.url)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Person(NamedThing):
    """
    An individual human being. This class represents a person in the context of a specific dataset. Attributes like
    affiliation and email represent the person's current or most relevant contact information for this dataset. For
    stable cross-dataset identification, use the ORCID field. Note that contributor roles (CRediT) are specified in
    the usage context (e.g., Creator class) rather than on the Person directly, since roles vary by dataset.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["Person"]
    class_class_curie: ClassVar[str] = "schema:Person"
    class_name: ClassVar[str] = "Person"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Person

    id: Union[str, PersonId] = None
    affiliation: Optional[Union[Union[str, OrganizationId], list[Union[str, OrganizationId]]]] = empty_list()
    email: Optional[str] = None
    orcid: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PersonId):
            self.id = PersonId(self.id)

        if not isinstance(self.affiliation, list):
            self.affiliation = [self.affiliation] if self.affiliation is not None else []
        self.affiliation = [v if isinstance(v, OrganizationId) else OrganizationId(v) for v in self.affiliation]

        if self.email is not None and not isinstance(self.email, str):
            self.email = str(self.email)

        if self.orcid is not None and not isinstance(self.orcid, str):
            self.orcid = str(self.orcid)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Information(NamedThing):
    """
    Grouping for datasets and data files
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Information"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Information"
    class_name: ClassVar[str] = "Information"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Information

    id: Union[str, InformationId] = None
    compression: Optional[Union[str, "CompressionEnum"]] = None
    conforms_to: Optional[str] = None
    conforms_to_class: Optional[str] = None
    conforms_to_schema: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[Union[str, XSDDateTime]] = None
    doi: Optional[str] = None
    download_url: Optional[Union[str, URI]] = None
    issued: Optional[Union[str, XSDDateTime]] = None
    keywords: Optional[Union[str, list[str]]] = empty_list()
    language: Optional[str] = None
    last_updated_on: Optional[Union[str, XSDDateTime]] = None
    license: Optional[str] = None
    modified_by: Optional[str] = None
    page: Optional[str] = None
    publisher: Optional[Union[str, URIorCURIE]] = None
    status: Optional[str] = None
    title: Optional[str] = None
    version: Optional[str] = None
    was_derived_from: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InformationId):
            self.id = InformationId(self.id)

        if self.compression is not None and not isinstance(self.compression, CompressionEnum):
            self.compression = CompressionEnum(self.compression)

        if self.conforms_to is not None and not isinstance(self.conforms_to, str):
            self.conforms_to = str(self.conforms_to)

        if self.conforms_to_class is not None and not isinstance(self.conforms_to_class, str):
            self.conforms_to_class = str(self.conforms_to_class)

        if self.conforms_to_schema is not None and not isinstance(self.conforms_to_schema, str):
            self.conforms_to_schema = str(self.conforms_to_schema)

        if self.created_by is not None and not isinstance(self.created_by, str):
            self.created_by = str(self.created_by)

        if self.created_on is not None and not isinstance(self.created_on, XSDDateTime):
            self.created_on = XSDDateTime(self.created_on)

        if self.doi is not None and not isinstance(self.doi, str):
            self.doi = str(self.doi)

        if self.download_url is not None and not isinstance(self.download_url, URI):
            self.download_url = URI(self.download_url)

        if self.issued is not None and not isinstance(self.issued, XSDDateTime):
            self.issued = XSDDateTime(self.issued)

        if not isinstance(self.keywords, list):
            self.keywords = [self.keywords] if self.keywords is not None else []
        self.keywords = [v if isinstance(v, str) else str(v) for v in self.keywords]

        if self.language is not None and not isinstance(self.language, str):
            self.language = str(self.language)

        if self.last_updated_on is not None and not isinstance(self.last_updated_on, XSDDateTime):
            self.last_updated_on = XSDDateTime(self.last_updated_on)

        if self.license is not None and not isinstance(self.license, str):
            self.license = str(self.license)

        if self.modified_by is not None and not isinstance(self.modified_by, str):
            self.modified_by = str(self.modified_by)

        if self.page is not None and not isinstance(self.page, str):
            self.page = str(self.page)

        if self.publisher is not None and not isinstance(self.publisher, URIorCURIE):
            self.publisher = URIorCURIE(self.publisher)

        if self.status is not None and not isinstance(self.status, str):
            self.status = str(self.status)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.was_derived_from is not None and not isinstance(self.was_derived_from, str):
            self.was_derived_from = str(self.was_derived_from)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DatasetCollection(Information):
    """
    A collection of related datasets, likely containing multiple files of multiple potential purposes and properties.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DatasetCollection"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DatasetCollection"
    class_name: ClassVar[str] = "DatasetCollection"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetCollection

    id: Union[str, DatasetCollectionId] = None
    resources: Optional[Union[dict[Union[str, DatasetId], Union[dict, "Dataset"]], list[Union[dict, "Dataset"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetCollectionId):
            self.id = DatasetCollectionId(self.id)

        self._normalize_inlined_as_list(slot_name="resources", slot_type=Dataset, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Dataset(Information):
    """
    A single component of related observations and/or information that can be read, manipulated, transformed, and
    otherwise interpreted.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DCAT["Distribution"]
    class_class_curie: ClassVar[str] = "dcat:Distribution"
    class_name: ClassVar[str] = "Dataset"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Dataset

    id: Union[str, DatasetId] = None
    bytes: Optional[int] = None
    dialect: Optional[str] = None
    encoding: Optional[Union[str, "EncodingEnum"]] = None
    format: Optional[Union[str, "FormatEnum"]] = None
    hash: Optional[str] = None
    md5: Optional[str] = None
    media_type: Optional[Union[str, "MediaTypeEnum"]] = None
    path: Optional[str] = None
    sha256: Optional[str] = None
    purposes: Optional[Union[Union[dict, "Purpose"], list[Union[dict, "Purpose"]]]] = empty_list()
    tasks: Optional[Union[Union[dict, "Task"], list[Union[dict, "Task"]]]] = empty_list()
    addressing_gaps: Optional[Union[Union[dict, "AddressingGap"], list[Union[dict, "AddressingGap"]]]] = empty_list()
    creators: Optional[Union[Union[dict, "Creator"], list[Union[dict, "Creator"]]]] = empty_list()
    funders: Optional[Union[Union[dict, "FundingMechanism"], list[Union[dict, "FundingMechanism"]]]] = empty_list()
    subsets: Optional[Union[dict[Union[str, DataSubsetId], Union[dict, "DataSubset"]], list[Union[dict, "DataSubset"]]]] = empty_dict()
    instances: Optional[Union[Union[dict, "Instance"], list[Union[dict, "Instance"]]]] = empty_list()
    anomalies: Optional[Union[Union[dict, "DataAnomaly"], list[Union[dict, "DataAnomaly"]]]] = empty_list()
    known_biases: Optional[Union[Union[dict, "DatasetBias"], list[Union[dict, "DatasetBias"]]]] = empty_list()
    known_limitations: Optional[Union[Union[dict, "DatasetLimitation"], list[Union[dict, "DatasetLimitation"]]]] = empty_list()
    external_resources: Optional[Union[Union[dict, "ExternalResource"], list[Union[dict, "ExternalResource"]]]] = empty_list()
    confidential_elements: Optional[Union[Union[dict, "Confidentiality"], list[Union[dict, "Confidentiality"]]]] = empty_list()
    content_warnings: Optional[Union[Union[dict, "ContentWarning"], list[Union[dict, "ContentWarning"]]]] = empty_list()
    subpopulations: Optional[Union[Union[dict, "Subpopulation"], list[Union[dict, "Subpopulation"]]]] = empty_list()
    sensitive_elements: Optional[Union[Union[dict, "SensitiveElement"], list[Union[dict, "SensitiveElement"]]]] = empty_list()
    acquisition_methods: Optional[Union[Union[dict, "InstanceAcquisition"], list[Union[dict, "InstanceAcquisition"]]]] = empty_list()
    collection_mechanisms: Optional[Union[Union[dict, "CollectionMechanism"], list[Union[dict, "CollectionMechanism"]]]] = empty_list()
    sampling_strategies: Optional[Union[Union[dict, "SamplingStrategy"], list[Union[dict, "SamplingStrategy"]]]] = empty_list()
    data_collectors: Optional[Union[Union[dict, "DataCollector"], list[Union[dict, "DataCollector"]]]] = empty_list()
    collection_timeframes: Optional[Union[Union[dict, "CollectionTimeframe"], list[Union[dict, "CollectionTimeframe"]]]] = empty_list()
    ethical_reviews: Optional[Union[Union[dict, "EthicalReview"], list[Union[dict, "EthicalReview"]]]] = empty_list()
    data_protection_impacts: Optional[Union[Union[dict, "DataProtectionImpact"], list[Union[dict, "DataProtectionImpact"]]]] = empty_list()
    human_subject_research: Optional[Union[dict, "HumanSubjectResearch"]] = None
    informed_consent: Optional[Union[Union[dict, "InformedConsent"], list[Union[dict, "InformedConsent"]]]] = empty_list()
    participant_privacy: Optional[Union[Union[dict, "ParticipantPrivacy"], list[Union[dict, "ParticipantPrivacy"]]]] = empty_list()
    participant_compensation: Optional[Union[dict, "HumanSubjectCompensation"]] = None
    vulnerable_populations: Optional[Union[dict, "VulnerablePopulations"]] = None
    preprocessing_strategies: Optional[Union[Union[dict, "PreprocessingStrategy"], list[Union[dict, "PreprocessingStrategy"]]]] = empty_list()
    cleaning_strategies: Optional[Union[Union[dict, "CleaningStrategy"], list[Union[dict, "CleaningStrategy"]]]] = empty_list()
    labeling_strategies: Optional[Union[Union[dict, "LabelingStrategy"], list[Union[dict, "LabelingStrategy"]]]] = empty_list()
    raw_sources: Optional[Union[Union[dict, "RawData"], list[Union[dict, "RawData"]]]] = empty_list()
    existing_uses: Optional[Union[Union[dict, "ExistingUse"], list[Union[dict, "ExistingUse"]]]] = empty_list()
    use_repository: Optional[Union[Union[dict, "UseRepository"], list[Union[dict, "UseRepository"]]]] = empty_list()
    other_tasks: Optional[Union[Union[dict, "OtherTask"], list[Union[dict, "OtherTask"]]]] = empty_list()
    future_use_impacts: Optional[Union[Union[dict, "FutureUseImpact"], list[Union[dict, "FutureUseImpact"]]]] = empty_list()
    discouraged_uses: Optional[Union[Union[dict, "DiscouragedUse"], list[Union[dict, "DiscouragedUse"]]]] = empty_list()
    intended_uses: Optional[Union[Union[dict, "IntendedUse"], list[Union[dict, "IntendedUse"]]]] = empty_list()
    prohibited_uses: Optional[Union[Union[dict, "ProhibitedUse"], list[Union[dict, "ProhibitedUse"]]]] = empty_list()
    distribution_formats: Optional[Union[Union[dict, "DistributionFormat"], list[Union[dict, "DistributionFormat"]]]] = empty_list()
    distribution_dates: Optional[Union[Union[dict, "DistributionDate"], list[Union[dict, "DistributionDate"]]]] = empty_list()
    license_and_use_terms: Optional[Union[dict, "LicenseAndUseTerms"]] = None
    ip_restrictions: Optional[Union[dict, "IPRestrictions"]] = None
    regulatory_restrictions: Optional[Union[dict, "ExportControlRegulatoryRestrictions"]] = None
    maintainers: Optional[Union[Union[dict, "Maintainer"], list[Union[dict, "Maintainer"]]]] = empty_list()
    errata: Optional[Union[Union[dict, "Erratum"], list[Union[dict, "Erratum"]]]] = empty_list()
    updates: Optional[Union[dict, "UpdatePlan"]] = None
    retention_limit: Optional[Union[dict, "RetentionLimits"]] = None
    version_access: Optional[Union[dict, "VersionAccess"]] = None
    extension_mechanism: Optional[Union[dict, "ExtensionMechanism"]] = None
    variables: Optional[Union[Union[dict, "VariableMetadata"], list[Union[dict, "VariableMetadata"]]]] = empty_list()
    is_deidentified: Optional[Union[dict, "Deidentification"]] = None
    is_tabular: Optional[Union[bool, Bool]] = None
    citation: Optional[str] = None
    parent_datasets: Optional[Union[dict[Union[str, DatasetId], Union[dict, "Dataset"]], list[Union[dict, "Dataset"]]]] = empty_dict()
    related_datasets: Optional[Union[Union[dict, "DatasetRelationship"], list[Union[dict, "DatasetRelationship"]]]] = empty_list()
    resources: Optional[Union[dict[Union[str, DatasetId], Union[dict, "Dataset"]], list[Union[dict, "Dataset"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetId):
            self.id = DatasetId(self.id)

        if self.bytes is not None and not isinstance(self.bytes, int):
            self.bytes = int(self.bytes)

        if self.dialect is not None and not isinstance(self.dialect, str):
            self.dialect = str(self.dialect)

        if self.encoding is not None and not isinstance(self.encoding, EncodingEnum):
            self.encoding = EncodingEnum(self.encoding)

        if self.format is not None and not isinstance(self.format, FormatEnum):
            self.format = FormatEnum(self.format)

        if self.hash is not None and not isinstance(self.hash, str):
            self.hash = str(self.hash)

        if self.md5 is not None and not isinstance(self.md5, str):
            self.md5 = str(self.md5)

        if self.media_type is not None and not isinstance(self.media_type, MediaTypeEnum):
            self.media_type = MediaTypeEnum(self.media_type)

        if self.path is not None and not isinstance(self.path, str):
            self.path = str(self.path)

        if self.sha256 is not None and not isinstance(self.sha256, str):
            self.sha256 = str(self.sha256)

        if not isinstance(self.purposes, list):
            self.purposes = [self.purposes] if self.purposes is not None else []
        self.purposes = [v if isinstance(v, Purpose) else Purpose(**as_dict(v)) for v in self.purposes]

        if not isinstance(self.tasks, list):
            self.tasks = [self.tasks] if self.tasks is not None else []
        self.tasks = [v if isinstance(v, Task) else Task(**as_dict(v)) for v in self.tasks]

        if not isinstance(self.addressing_gaps, list):
            self.addressing_gaps = [self.addressing_gaps] if self.addressing_gaps is not None else []
        self.addressing_gaps = [v if isinstance(v, AddressingGap) else AddressingGap(**as_dict(v)) for v in self.addressing_gaps]

        if not isinstance(self.creators, list):
            self.creators = [self.creators] if self.creators is not None else []
        self.creators = [v if isinstance(v, Creator) else Creator(**as_dict(v)) for v in self.creators]

        if not isinstance(self.funders, list):
            self.funders = [self.funders] if self.funders is not None else []
        self.funders = [v if isinstance(v, FundingMechanism) else FundingMechanism(**as_dict(v)) for v in self.funders]

        self._normalize_inlined_as_list(slot_name="subsets", slot_type=DataSubset, key_name="id", keyed=True)

        if not isinstance(self.instances, list):
            self.instances = [self.instances] if self.instances is not None else []
        self.instances = [v if isinstance(v, Instance) else Instance(**as_dict(v)) for v in self.instances]

        if not isinstance(self.anomalies, list):
            self.anomalies = [self.anomalies] if self.anomalies is not None else []
        self.anomalies = [v if isinstance(v, DataAnomaly) else DataAnomaly(**as_dict(v)) for v in self.anomalies]

        if not isinstance(self.known_biases, list):
            self.known_biases = [self.known_biases] if self.known_biases is not None else []
        self.known_biases = [v if isinstance(v, DatasetBias) else DatasetBias(**as_dict(v)) for v in self.known_biases]

        if not isinstance(self.known_limitations, list):
            self.known_limitations = [self.known_limitations] if self.known_limitations is not None else []
        self.known_limitations = [v if isinstance(v, DatasetLimitation) else DatasetLimitation(**as_dict(v)) for v in self.known_limitations]

        if not isinstance(self.external_resources, list):
            self.external_resources = [self.external_resources] if self.external_resources is not None else []
        self.external_resources = [v if isinstance(v, ExternalResource) else ExternalResource(**as_dict(v)) for v in self.external_resources]

        if not isinstance(self.confidential_elements, list):
            self.confidential_elements = [self.confidential_elements] if self.confidential_elements is not None else []
        self.confidential_elements = [v if isinstance(v, Confidentiality) else Confidentiality(**as_dict(v)) for v in self.confidential_elements]

        if not isinstance(self.content_warnings, list):
            self.content_warnings = [self.content_warnings] if self.content_warnings is not None else []
        self.content_warnings = [v if isinstance(v, ContentWarning) else ContentWarning(**as_dict(v)) for v in self.content_warnings]

        if not isinstance(self.subpopulations, list):
            self.subpopulations = [self.subpopulations] if self.subpopulations is not None else []
        self.subpopulations = [v if isinstance(v, Subpopulation) else Subpopulation(**as_dict(v)) for v in self.subpopulations]

        if not isinstance(self.sensitive_elements, list):
            self.sensitive_elements = [self.sensitive_elements] if self.sensitive_elements is not None else []
        self.sensitive_elements = [v if isinstance(v, SensitiveElement) else SensitiveElement(**as_dict(v)) for v in self.sensitive_elements]

        if not isinstance(self.acquisition_methods, list):
            self.acquisition_methods = [self.acquisition_methods] if self.acquisition_methods is not None else []
        self.acquisition_methods = [v if isinstance(v, InstanceAcquisition) else InstanceAcquisition(**as_dict(v)) for v in self.acquisition_methods]

        if not isinstance(self.collection_mechanisms, list):
            self.collection_mechanisms = [self.collection_mechanisms] if self.collection_mechanisms is not None else []
        self.collection_mechanisms = [v if isinstance(v, CollectionMechanism) else CollectionMechanism(**as_dict(v)) for v in self.collection_mechanisms]

        if not isinstance(self.sampling_strategies, list):
            self.sampling_strategies = [self.sampling_strategies] if self.sampling_strategies is not None else []
        self.sampling_strategies = [v if isinstance(v, SamplingStrategy) else SamplingStrategy(**as_dict(v)) for v in self.sampling_strategies]

        if not isinstance(self.data_collectors, list):
            self.data_collectors = [self.data_collectors] if self.data_collectors is not None else []
        self.data_collectors = [v if isinstance(v, DataCollector) else DataCollector(**as_dict(v)) for v in self.data_collectors]

        if not isinstance(self.collection_timeframes, list):
            self.collection_timeframes = [self.collection_timeframes] if self.collection_timeframes is not None else []
        self.collection_timeframes = [v if isinstance(v, CollectionTimeframe) else CollectionTimeframe(**as_dict(v)) for v in self.collection_timeframes]

        if not isinstance(self.ethical_reviews, list):
            self.ethical_reviews = [self.ethical_reviews] if self.ethical_reviews is not None else []
        self.ethical_reviews = [v if isinstance(v, EthicalReview) else EthicalReview(**as_dict(v)) for v in self.ethical_reviews]

        if not isinstance(self.data_protection_impacts, list):
            self.data_protection_impacts = [self.data_protection_impacts] if self.data_protection_impacts is not None else []
        self.data_protection_impacts = [v if isinstance(v, DataProtectionImpact) else DataProtectionImpact(**as_dict(v)) for v in self.data_protection_impacts]

        if self.human_subject_research is not None and not isinstance(self.human_subject_research, HumanSubjectResearch):
            self.human_subject_research = HumanSubjectResearch(**as_dict(self.human_subject_research))

        if not isinstance(self.informed_consent, list):
            self.informed_consent = [self.informed_consent] if self.informed_consent is not None else []
        self.informed_consent = [v if isinstance(v, InformedConsent) else InformedConsent(**as_dict(v)) for v in self.informed_consent]

        if not isinstance(self.participant_privacy, list):
            self.participant_privacy = [self.participant_privacy] if self.participant_privacy is not None else []
        self.participant_privacy = [v if isinstance(v, ParticipantPrivacy) else ParticipantPrivacy(**as_dict(v)) for v in self.participant_privacy]

        if self.participant_compensation is not None and not isinstance(self.participant_compensation, HumanSubjectCompensation):
            self.participant_compensation = HumanSubjectCompensation(**as_dict(self.participant_compensation))

        if self.vulnerable_populations is not None and not isinstance(self.vulnerable_populations, VulnerablePopulations):
            self.vulnerable_populations = VulnerablePopulations(**as_dict(self.vulnerable_populations))

        if not isinstance(self.preprocessing_strategies, list):
            self.preprocessing_strategies = [self.preprocessing_strategies] if self.preprocessing_strategies is not None else []
        self.preprocessing_strategies = [v if isinstance(v, PreprocessingStrategy) else PreprocessingStrategy(**as_dict(v)) for v in self.preprocessing_strategies]

        if not isinstance(self.cleaning_strategies, list):
            self.cleaning_strategies = [self.cleaning_strategies] if self.cleaning_strategies is not None else []
        self.cleaning_strategies = [v if isinstance(v, CleaningStrategy) else CleaningStrategy(**as_dict(v)) for v in self.cleaning_strategies]

        if not isinstance(self.labeling_strategies, list):
            self.labeling_strategies = [self.labeling_strategies] if self.labeling_strategies is not None else []
        self.labeling_strategies = [v if isinstance(v, LabelingStrategy) else LabelingStrategy(**as_dict(v)) for v in self.labeling_strategies]

        if not isinstance(self.raw_sources, list):
            self.raw_sources = [self.raw_sources] if self.raw_sources is not None else []
        self.raw_sources = [v if isinstance(v, RawData) else RawData(**as_dict(v)) for v in self.raw_sources]

        if not isinstance(self.existing_uses, list):
            self.existing_uses = [self.existing_uses] if self.existing_uses is not None else []
        self.existing_uses = [v if isinstance(v, ExistingUse) else ExistingUse(**as_dict(v)) for v in self.existing_uses]

        if not isinstance(self.use_repository, list):
            self.use_repository = [self.use_repository] if self.use_repository is not None else []
        self.use_repository = [v if isinstance(v, UseRepository) else UseRepository(**as_dict(v)) for v in self.use_repository]

        if not isinstance(self.other_tasks, list):
            self.other_tasks = [self.other_tasks] if self.other_tasks is not None else []
        self.other_tasks = [v if isinstance(v, OtherTask) else OtherTask(**as_dict(v)) for v in self.other_tasks]

        if not isinstance(self.future_use_impacts, list):
            self.future_use_impacts = [self.future_use_impacts] if self.future_use_impacts is not None else []
        self.future_use_impacts = [v if isinstance(v, FutureUseImpact) else FutureUseImpact(**as_dict(v)) for v in self.future_use_impacts]

        if not isinstance(self.discouraged_uses, list):
            self.discouraged_uses = [self.discouraged_uses] if self.discouraged_uses is not None else []
        self.discouraged_uses = [v if isinstance(v, DiscouragedUse) else DiscouragedUse(**as_dict(v)) for v in self.discouraged_uses]

        if not isinstance(self.intended_uses, list):
            self.intended_uses = [self.intended_uses] if self.intended_uses is not None else []
        self.intended_uses = [v if isinstance(v, IntendedUse) else IntendedUse(**as_dict(v)) for v in self.intended_uses]

        if not isinstance(self.prohibited_uses, list):
            self.prohibited_uses = [self.prohibited_uses] if self.prohibited_uses is not None else []
        self.prohibited_uses = [v if isinstance(v, ProhibitedUse) else ProhibitedUse(**as_dict(v)) for v in self.prohibited_uses]

        if not isinstance(self.distribution_formats, list):
            self.distribution_formats = [self.distribution_formats] if self.distribution_formats is not None else []
        self.distribution_formats = [v if isinstance(v, DistributionFormat) else DistributionFormat(**as_dict(v)) for v in self.distribution_formats]

        if not isinstance(self.distribution_dates, list):
            self.distribution_dates = [self.distribution_dates] if self.distribution_dates is not None else []
        self.distribution_dates = [v if isinstance(v, DistributionDate) else DistributionDate(**as_dict(v)) for v in self.distribution_dates]

        if self.license_and_use_terms is not None and not isinstance(self.license_and_use_terms, LicenseAndUseTerms):
            self.license_and_use_terms = LicenseAndUseTerms(**as_dict(self.license_and_use_terms))

        if self.ip_restrictions is not None and not isinstance(self.ip_restrictions, IPRestrictions):
            self.ip_restrictions = IPRestrictions(**as_dict(self.ip_restrictions))

        if self.regulatory_restrictions is not None and not isinstance(self.regulatory_restrictions, ExportControlRegulatoryRestrictions):
            self.regulatory_restrictions = ExportControlRegulatoryRestrictions(**as_dict(self.regulatory_restrictions))

        if not isinstance(self.maintainers, list):
            self.maintainers = [self.maintainers] if self.maintainers is not None else []
        self.maintainers = [v if isinstance(v, Maintainer) else Maintainer(**as_dict(v)) for v in self.maintainers]

        if not isinstance(self.errata, list):
            self.errata = [self.errata] if self.errata is not None else []
        self.errata = [v if isinstance(v, Erratum) else Erratum(**as_dict(v)) for v in self.errata]

        if self.updates is not None and not isinstance(self.updates, UpdatePlan):
            self.updates = UpdatePlan(**as_dict(self.updates))

        if self.retention_limit is not None and not isinstance(self.retention_limit, RetentionLimits):
            self.retention_limit = RetentionLimits(**as_dict(self.retention_limit))

        if self.version_access is not None and not isinstance(self.version_access, VersionAccess):
            self.version_access = VersionAccess(**as_dict(self.version_access))

        if self.extension_mechanism is not None and not isinstance(self.extension_mechanism, ExtensionMechanism):
            self.extension_mechanism = ExtensionMechanism(**as_dict(self.extension_mechanism))

        if not isinstance(self.variables, list):
            self.variables = [self.variables] if self.variables is not None else []
        self.variables = [v if isinstance(v, VariableMetadata) else VariableMetadata(**as_dict(v)) for v in self.variables]

        if self.is_deidentified is not None and not isinstance(self.is_deidentified, Deidentification):
            self.is_deidentified = Deidentification(**as_dict(self.is_deidentified))

        if self.is_tabular is not None and not isinstance(self.is_tabular, Bool):
            self.is_tabular = Bool(self.is_tabular)

        if self.citation is not None and not isinstance(self.citation, str):
            self.citation = str(self.citation)

        self._normalize_inlined_as_list(slot_name="parent_datasets", slot_type=Dataset, key_name="id", keyed=True)

        if not isinstance(self.related_datasets, list):
            self.related_datasets = [self.related_datasets] if self.related_datasets is not None else []
        self.related_datasets = [v if isinstance(v, DatasetRelationship) else DatasetRelationship(**as_dict(v)) for v in self.related_datasets]

        self._normalize_inlined_as_list(slot_name="resources", slot_type=Dataset, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DataSubset(Dataset):
    """
    A subset of a dataset, likely containing multiple files of multiple potential purposes and properties.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DataSubset"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DataSubset"
    class_name: ClassVar[str] = "DataSubset"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataSubset

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


@dataclass(repr=False)
class FormatDialect(YAMLRoot):
    """
    Additional format information for a file
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["FormatDialect"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:FormatDialect"
    class_name: ClassVar[str] = "FormatDialect"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.FormatDialect

    comment_prefix: Optional[str] = None
    delimiter: Optional[str] = None
    double_quote: Optional[str] = None
    header: Optional[str] = None
    quote_char: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.comment_prefix is not None and not isinstance(self.comment_prefix, str):
            self.comment_prefix = str(self.comment_prefix)

        if self.delimiter is not None and not isinstance(self.delimiter, str):
            self.delimiter = str(self.delimiter)

        if self.double_quote is not None and not isinstance(self.double_quote, str):
            self.double_quote = str(self.double_quote)

        if self.header is not None and not isinstance(self.header, str):
            self.header = str(self.header)

        if self.quote_char is not None and not isinstance(self.quote_char, str):
            self.quote_char = str(self.quote_char)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Purpose(DatasetProperty):
    """
    For what purpose was the dataset created?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["Purpose"]
    class_class_curie: ClassVar[str] = "d4dmotivation:Purpose"
    class_name: ClassVar[str] = "Purpose"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Purpose

    response: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.response is not None and not isinstance(self.response, str):
            self.response = str(self.response)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Task(DatasetProperty):
    """
    Was there a specific task in mind for the dataset's application?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["Task"]
    class_class_curie: ClassVar[str] = "d4dmotivation:Task"
    class_name: ClassVar[str] = "Task"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Task

    response: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.response is not None and not isinstance(self.response, str):
            self.response = str(self.response)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class AddressingGap(DatasetProperty):
    """
    Was there a specific gap that needed to be filled by creation of the dataset?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["AddressingGap"]
    class_class_curie: ClassVar[str] = "d4dmotivation:AddressingGap"
    class_name: ClassVar[str] = "AddressingGap"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.AddressingGap

    response: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.response is not None and not isinstance(self.response, str):
            self.response = str(self.response)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Creator(DatasetProperty):
    """
    Who created the dataset (e.g., which team, research group) and on behalf of which entity (e.g., company,
    institution, organization)? This may also be considered a team.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["Creator"]
    class_class_curie: ClassVar[str] = "d4dmotivation:Creator"
    class_name: ClassVar[str] = "Creator"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Creator

    principal_investigator: Optional[Union[str, PersonId]] = None
    affiliations: Optional[Union[dict[Union[str, OrganizationId], Union[dict, Organization]], list[Union[dict, Organization]]]] = empty_dict()
    credit_roles: Optional[Union[Union[str, "CRediTRoleEnum"], list[Union[str, "CRediTRoleEnum"]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.principal_investigator is not None and not isinstance(self.principal_investigator, PersonId):
            self.principal_investigator = PersonId(self.principal_investigator)

        self._normalize_inlined_as_list(slot_name="affiliations", slot_type=Organization, key_name="id", keyed=True)

        if not isinstance(self.credit_roles, list):
            self.credit_roles = [self.credit_roles] if self.credit_roles is not None else []
        self.credit_roles = [v if isinstance(v, CRediTRoleEnum) else CRediTRoleEnum(v) for v in self.credit_roles]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class FundingMechanism(DatasetProperty):
    """
    Who funded the creation of the dataset? If there is an associated grant, please provide the name of the grantor
    and the grant name and number.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["FundingMechanism"]
    class_class_curie: ClassVar[str] = "d4dmotivation:FundingMechanism"
    class_name: ClassVar[str] = "FundingMechanism"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.FundingMechanism

    grantor: Optional[Union[str, GrantorId]] = None
    grants: Optional[Union[dict[Union[str, GrantId], Union[dict, "Grant"]], list[Union[dict, "Grant"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.grantor is not None and not isinstance(self.grantor, GrantorId):
            self.grantor = GrantorId(self.grantor)

        self._normalize_inlined_as_list(slot_name="grants", slot_type=Grant, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Grantor(Organization):
    """
    The name and/or identifier of the organization providing monetary support or other resources supporting creation
    of the dataset.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["Grantor"]
    class_class_curie: ClassVar[str] = "d4dmotivation:Grantor"
    class_name: ClassVar[str] = "Grantor"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Grantor

    id: Union[str, GrantorId] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, GrantorId):
            self.id = GrantorId(self.id)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Grant(NamedThing):
    """
    The name and/or identifier of the specific mechanism providing monetary support or other resources supporting
    creation of the dataset.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMOTIVATION["Grant"]
    class_class_curie: ClassVar[str] = "d4dmotivation:Grant"
    class_name: ClassVar[str] = "Grant"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Grant

    id: Union[str, GrantId] = None
    grant_number: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, GrantId):
            self.id = GrantId(self.id)

        if self.grant_number is not None and not isinstance(self.grant_number, str):
            self.grant_number = str(self.grant_number)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Instance(DatasetProperty):
    """
    What do the instances that comprise the dataset represent (e.g., documents, photos, people, countries)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["Instance"]
    class_class_curie: ClassVar[str] = "d4dcomposition:Instance"
    class_name: ClassVar[str] = "Instance"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Instance

    data_topic: Optional[Union[str, URIorCURIE]] = None
    instance_type: Optional[str] = None
    data_substrate: Optional[Union[str, URIorCURIE]] = None
    counts: Optional[int] = None
    label: Optional[Union[bool, Bool]] = None
    label_description: Optional[str] = None
    sampling_strategies: Optional[Union[Union[dict, "SamplingStrategy"], list[Union[dict, "SamplingStrategy"]]]] = empty_list()
    missing_information: Optional[Union[Union[dict, "MissingInfo"], list[Union[dict, "MissingInfo"]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.data_topic is not None and not isinstance(self.data_topic, URIorCURIE):
            self.data_topic = URIorCURIE(self.data_topic)

        if self.instance_type is not None and not isinstance(self.instance_type, str):
            self.instance_type = str(self.instance_type)

        if self.data_substrate is not None and not isinstance(self.data_substrate, URIorCURIE):
            self.data_substrate = URIorCURIE(self.data_substrate)

        if self.counts is not None and not isinstance(self.counts, int):
            self.counts = int(self.counts)

        if self.label is not None and not isinstance(self.label, Bool):
            self.label = Bool(self.label)

        if self.label_description is not None and not isinstance(self.label_description, str):
            self.label_description = str(self.label_description)

        if not isinstance(self.sampling_strategies, list):
            self.sampling_strategies = [self.sampling_strategies] if self.sampling_strategies is not None else []
        self.sampling_strategies = [v if isinstance(v, SamplingStrategy) else SamplingStrategy(**as_dict(v)) for v in self.sampling_strategies]

        if not isinstance(self.missing_information, list):
            self.missing_information = [self.missing_information] if self.missing_information is not None else []
        self.missing_information = [v if isinstance(v, MissingInfo) else MissingInfo(**as_dict(v)) for v in self.missing_information]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SamplingStrategy(DatasetProperty):
    """
    Does the dataset contain all possible instances, or is it a sample (not necessarily random) of instances from a
    larger set? If so, how representative is it?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["SamplingStrategy"]
    class_class_curie: ClassVar[str] = "d4dcomposition:SamplingStrategy"
    class_name: ClassVar[str] = "SamplingStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.SamplingStrategy

    is_sample: Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]] = empty_list()
    is_random: Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]] = empty_list()
    source_data: Optional[Union[str, list[str]]] = empty_list()
    is_representative: Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]] = empty_list()
    representative_verification: Optional[Union[str, list[str]]] = empty_list()
    why_not_representative: Optional[Union[str, list[str]]] = empty_list()
    strategies: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.is_sample, list):
            self.is_sample = [self.is_sample] if self.is_sample is not None else []
        self.is_sample = [v if isinstance(v, Bool) else Bool(v) for v in self.is_sample]

        if not isinstance(self.is_random, list):
            self.is_random = [self.is_random] if self.is_random is not None else []
        self.is_random = [v if isinstance(v, Bool) else Bool(v) for v in self.is_random]

        if not isinstance(self.source_data, list):
            self.source_data = [self.source_data] if self.source_data is not None else []
        self.source_data = [v if isinstance(v, str) else str(v) for v in self.source_data]

        if not isinstance(self.is_representative, list):
            self.is_representative = [self.is_representative] if self.is_representative is not None else []
        self.is_representative = [v if isinstance(v, Bool) else Bool(v) for v in self.is_representative]

        if not isinstance(self.representative_verification, list):
            self.representative_verification = [self.representative_verification] if self.representative_verification is not None else []
        self.representative_verification = [v if isinstance(v, str) else str(v) for v in self.representative_verification]

        if not isinstance(self.why_not_representative, list):
            self.why_not_representative = [self.why_not_representative] if self.why_not_representative is not None else []
        self.why_not_representative = [v if isinstance(v, str) else str(v) for v in self.why_not_representative]

        if not isinstance(self.strategies, list):
            self.strategies = [self.strategies] if self.strategies is not None else []
        self.strategies = [v if isinstance(v, str) else str(v) for v in self.strategies]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class MissingInfo(DatasetProperty):
    """
    Is any information missing from individual instances? (e.g., unavailable data)
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["MissingInfo"]
    class_class_curie: ClassVar[str] = "d4dcomposition:MissingInfo"
    class_name: ClassVar[str] = "MissingInfo"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.MissingInfo

    missing: Optional[Union[str, list[str]]] = empty_list()
    why_missing: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.missing, list):
            self.missing = [self.missing] if self.missing is not None else []
        self.missing = [v if isinstance(v, str) else str(v) for v in self.missing]

        if not isinstance(self.why_missing, list):
            self.why_missing = [self.why_missing] if self.why_missing is not None else []
        self.why_missing = [v if isinstance(v, str) else str(v) for v in self.why_missing]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Relationships(DatasetProperty):
    """
    Are relationships between individual instances made explicit (e.g., users' movie ratings, social network links)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["Relationships"]
    class_class_curie: ClassVar[str] = "d4dcomposition:Relationships"
    class_name: ClassVar[str] = "Relationships"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Relationships

    relationship_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.relationship_details, list):
            self.relationship_details = [self.relationship_details] if self.relationship_details is not None else []
        self.relationship_details = [v if isinstance(v, str) else str(v) for v in self.relationship_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Splits(DatasetProperty):
    """
    Are there recommended data splits (e.g., training, validation, testing)? If so, how are they defined and why?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["Splits"]
    class_class_curie: ClassVar[str] = "d4dcomposition:Splits"
    class_name: ClassVar[str] = "Splits"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Splits

    split_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.split_details, list):
            self.split_details = [self.split_details] if self.split_details is not None else []
        self.split_details = [v if isinstance(v, str) else str(v) for v in self.split_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DataAnomaly(DatasetProperty):
    """
    Are there any errors, sources of noise, or redundancies in the dataset?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["DataAnomaly"]
    class_class_curie: ClassVar[str] = "d4dcomposition:DataAnomaly"
    class_name: ClassVar[str] = "DataAnomaly"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataAnomaly

    anomaly_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.anomaly_details, list):
            self.anomaly_details = [self.anomaly_details] if self.anomaly_details is not None else []
        self.anomaly_details = [v if isinstance(v, str) else str(v) for v in self.anomaly_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DatasetBias(DatasetProperty):
    """
    Documents known biases present in the dataset. Biases are systematic errors or prejudices that may affect the
    representativeness or fairness of the data. Distinct from anomalies (data quality issues) and limitations (scope
    constraints).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["DatasetBias"]
    class_class_curie: ClassVar[str] = "d4dcomposition:DatasetBias"
    class_name: ClassVar[str] = "DatasetBias"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetBias

    bias_type: Optional[Union[str, "BiasTypeEnum"]] = None
    bias_description: Optional[str] = None
    mitigation_strategy: Optional[str] = None
    affected_subsets: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.bias_type is not None and not isinstance(self.bias_type, BiasTypeEnum):
            self.bias_type = BiasTypeEnum(self.bias_type)

        if self.bias_description is not None and not isinstance(self.bias_description, str):
            self.bias_description = str(self.bias_description)

        if self.mitigation_strategy is not None and not isinstance(self.mitigation_strategy, str):
            self.mitigation_strategy = str(self.mitigation_strategy)

        if not isinstance(self.affected_subsets, list):
            self.affected_subsets = [self.affected_subsets] if self.affected_subsets is not None else []
        self.affected_subsets = [v if isinstance(v, str) else str(v) for v in self.affected_subsets]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DatasetLimitation(DatasetProperty):
    """
    Documents known limitations of the dataset that may affect its use or interpretation. Distinct from biases
    (systematic errors) and anomalies (data quality issues).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["DatasetLimitation"]
    class_class_curie: ClassVar[str] = "d4dcomposition:DatasetLimitation"
    class_name: ClassVar[str] = "DatasetLimitation"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetLimitation

    limitation_type: Optional[Union[str, "LimitationTypeEnum"]] = None
    limitation_description: Optional[str] = None
    scope_impact: Optional[str] = None
    recommended_mitigation: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.limitation_type is not None and not isinstance(self.limitation_type, LimitationTypeEnum):
            self.limitation_type = LimitationTypeEnum(self.limitation_type)

        if self.limitation_description is not None and not isinstance(self.limitation_description, str):
            self.limitation_description = str(self.limitation_description)

        if self.scope_impact is not None and not isinstance(self.scope_impact, str):
            self.scope_impact = str(self.scope_impact)

        if self.recommended_mitigation is not None and not isinstance(self.recommended_mitigation, str):
            self.recommended_mitigation = str(self.recommended_mitigation)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ExternalResource(DatasetProperty):
    """
    Is the dataset self-contained or does it rely on external resources (e.g., websites, other datasets)? If external,
    are there guarantees that those resources will remain available and unchanged?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["ExternalResource"]
    class_class_curie: ClassVar[str] = "d4dcomposition:ExternalResource"
    class_name: ClassVar[str] = "ExternalResource"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExternalResource

    external_resources: Optional[Union[str, list[str]]] = empty_list()
    future_guarantees: Optional[Union[str, list[str]]] = empty_list()
    archival: Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]] = empty_list()
    restrictions: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.external_resources, list):
            self.external_resources = [self.external_resources] if self.external_resources is not None else []
        self.external_resources = [v if isinstance(v, str) else str(v) for v in self.external_resources]

        if not isinstance(self.future_guarantees, list):
            self.future_guarantees = [self.future_guarantees] if self.future_guarantees is not None else []
        self.future_guarantees = [v if isinstance(v, str) else str(v) for v in self.future_guarantees]

        if not isinstance(self.archival, list):
            self.archival = [self.archival] if self.archival is not None else []
        self.archival = [v if isinstance(v, Bool) else Bool(v) for v in self.archival]

        if not isinstance(self.restrictions, list):
            self.restrictions = [self.restrictions] if self.restrictions is not None else []
        self.restrictions = [v if isinstance(v, str) else str(v) for v in self.restrictions]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Confidentiality(DatasetProperty):
    """
    Does the dataset contain data that might be confidential (e.g., protected by legal privilege, patient data,
    non-public communications)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["Confidentiality"]
    class_class_curie: ClassVar[str] = "d4dcomposition:Confidentiality"
    class_name: ClassVar[str] = "Confidentiality"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Confidentiality

    confidential_elements_present: Optional[Union[bool, Bool]] = None
    confidentiality_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.confidential_elements_present is not None and not isinstance(self.confidential_elements_present, Bool):
            self.confidential_elements_present = Bool(self.confidential_elements_present)

        if not isinstance(self.confidentiality_details, list):
            self.confidentiality_details = [self.confidentiality_details] if self.confidentiality_details is not None else []
        self.confidentiality_details = [v if isinstance(v, str) else str(v) for v in self.confidentiality_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ContentWarning(DatasetProperty):
    """
    Does the dataset contain any data that might be offensive, insulting, threatening, or otherwise anxiety-provoking
    if viewed directly?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["ContentWarning"]
    class_class_curie: ClassVar[str] = "d4dcomposition:ContentWarning"
    class_name: ClassVar[str] = "ContentWarning"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ContentWarning

    content_warnings_present: Optional[Union[bool, Bool]] = None
    warnings: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.content_warnings_present is not None and not isinstance(self.content_warnings_present, Bool):
            self.content_warnings_present = Bool(self.content_warnings_present)

        if not isinstance(self.warnings, list):
            self.warnings = [self.warnings] if self.warnings is not None else []
        self.warnings = [v if isinstance(v, str) else str(v) for v in self.warnings]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Subpopulation(DatasetProperty):
    """
    Does the dataset identify any subpopulations (e.g., by age, gender)? If so, how are they identified and what are
    their distributions?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["Subpopulation"]
    class_class_curie: ClassVar[str] = "d4dcomposition:Subpopulation"
    class_name: ClassVar[str] = "Subpopulation"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Subpopulation

    subpopulation_elements_present: Optional[Union[bool, Bool]] = None
    identification: Optional[Union[str, list[str]]] = empty_list()
    distribution: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.subpopulation_elements_present is not None and not isinstance(self.subpopulation_elements_present, Bool):
            self.subpopulation_elements_present = Bool(self.subpopulation_elements_present)

        if not isinstance(self.identification, list):
            self.identification = [self.identification] if self.identification is not None else []
        self.identification = [v if isinstance(v, str) else str(v) for v in self.identification]

        if not isinstance(self.distribution, list):
            self.distribution = [self.distribution] if self.distribution is not None else []
        self.distribution = [v if isinstance(v, str) else str(v) for v in self.distribution]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Deidentification(DatasetProperty):
    """
    Is it possible to identify individuals in the dataset, either directly or indirectly (in combination with other
    data)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["Deidentification"]
    class_class_curie: ClassVar[str] = "d4dcomposition:Deidentification"
    class_name: ClassVar[str] = "Deidentification"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Deidentification

    identifiable_elements_present: Optional[Union[bool, Bool]] = None
    method: Optional[str] = None
    identifiers_removed: Optional[Union[str, list[str]]] = empty_list()
    deidentification_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.identifiable_elements_present is not None and not isinstance(self.identifiable_elements_present, Bool):
            self.identifiable_elements_present = Bool(self.identifiable_elements_present)

        if self.method is not None and not isinstance(self.method, str):
            self.method = str(self.method)

        if not isinstance(self.identifiers_removed, list):
            self.identifiers_removed = [self.identifiers_removed] if self.identifiers_removed is not None else []
        self.identifiers_removed = [v if isinstance(v, str) else str(v) for v in self.identifiers_removed]

        if not isinstance(self.deidentification_details, list):
            self.deidentification_details = [self.deidentification_details] if self.deidentification_details is not None else []
        self.deidentification_details = [v if isinstance(v, str) else str(v) for v in self.deidentification_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SensitiveElement(DatasetProperty):
    """
    Does the dataset contain data that might be considered sensitive (e.g., race, sexual orientation, religion,
    biometrics)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["SensitiveElement"]
    class_class_curie: ClassVar[str] = "d4dcomposition:SensitiveElement"
    class_name: ClassVar[str] = "SensitiveElement"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.SensitiveElement

    sensitive_elements_present: Optional[Union[bool, Bool]] = None
    sensitivity_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.sensitive_elements_present is not None and not isinstance(self.sensitive_elements_present, Bool):
            self.sensitive_elements_present = Bool(self.sensitive_elements_present)

        if not isinstance(self.sensitivity_details, list):
            self.sensitivity_details = [self.sensitivity_details] if self.sensitivity_details is not None else []
        self.sensitivity_details = [v if isinstance(v, str) else str(v) for v in self.sensitivity_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DatasetRelationship(DatasetProperty):
    """
    Typed relationship to another dataset, enabling precise specification of how datasets relate to each other (e.g.,
    supplements, derives from, is version of). Supports RO-Crate-style dataset interlinking.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DCOMPOSITION["DatasetRelationship"]
    class_class_curie: ClassVar[str] = "d4dcomposition:DatasetRelationship"
    class_name: ClassVar[str] = "DatasetRelationship"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetRelationship

    target_dataset: str = None
    relationship_type: Union[str, "DatasetRelationshipTypeEnum"] = None
    description: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.target_dataset):
            self.MissingRequiredField("target_dataset")
        if not isinstance(self.target_dataset, str):
            self.target_dataset = str(self.target_dataset)

        if self._is_empty(self.relationship_type):
            self.MissingRequiredField("relationship_type")
        if not isinstance(self.relationship_type, DatasetRelationshipTypeEnum):
            self.relationship_type = DatasetRelationshipTypeEnum(self.relationship_type)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class InstanceAcquisition(DatasetProperty):
    """
    Describes how data associated with each instance was acquired (e.g., directly observed, reported by subjects,
    inferred).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["collection/InstanceAcquisition"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:collection/InstanceAcquisition"
    class_name: ClassVar[str] = "InstanceAcquisition"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.InstanceAcquisition

    was_directly_observed: Optional[Union[bool, Bool]] = None
    was_reported_by_subjects: Optional[Union[bool, Bool]] = None
    was_inferred_derived: Optional[Union[bool, Bool]] = None
    was_validated_verified: Optional[Union[bool, Bool]] = None
    acquisition_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.was_directly_observed is not None and not isinstance(self.was_directly_observed, Bool):
            self.was_directly_observed = Bool(self.was_directly_observed)

        if self.was_reported_by_subjects is not None and not isinstance(self.was_reported_by_subjects, Bool):
            self.was_reported_by_subjects = Bool(self.was_reported_by_subjects)

        if self.was_inferred_derived is not None and not isinstance(self.was_inferred_derived, Bool):
            self.was_inferred_derived = Bool(self.was_inferred_derived)

        if self.was_validated_verified is not None and not isinstance(self.was_validated_verified, Bool):
            self.was_validated_verified = Bool(self.was_validated_verified)

        if not isinstance(self.acquisition_details, list):
            self.acquisition_details = [self.acquisition_details] if self.acquisition_details is not None else []
        self.acquisition_details = [v if isinstance(v, str) else str(v) for v in self.acquisition_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CollectionMechanism(DatasetProperty):
    """
    What mechanisms or procedures were used to collect the data (e.g., hardware, manual curation, software APIs)? Also
    covers how these mechanisms were validated.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["collection/CollectionMechanism"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:collection/CollectionMechanism"
    class_name: ClassVar[str] = "CollectionMechanism"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionMechanism

    mechanism_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.mechanism_details, list):
            self.mechanism_details = [self.mechanism_details] if self.mechanism_details is not None else []
        self.mechanism_details = [v if isinstance(v, str) else str(v) for v in self.mechanism_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DataCollector(DatasetProperty):
    """
    Who was involved in the data collection (e.g., students, crowdworkers, contractors), and how they were compensated.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["collection/DataCollector"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:collection/DataCollector"
    class_name: ClassVar[str] = "DataCollector"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataCollector

    role: Optional[str] = None
    collector_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.role is not None and not isinstance(self.role, str):
            self.role = str(self.role)

        if not isinstance(self.collector_details, list):
            self.collector_details = [self.collector_details] if self.collector_details is not None else []
        self.collector_details = [v if isinstance(v, str) else str(v) for v in self.collector_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CollectionTimeframe(DatasetProperty):
    """
    Over what timeframe was the data collected, and does this timeframe match the creation timeframe of the underlying
    data?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["collection/CollectionTimeframe"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:collection/CollectionTimeframe"
    class_name: ClassVar[str] = "CollectionTimeframe"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionTimeframe

    start_date: Optional[Union[str, XSDDate]] = None
    end_date: Optional[Union[str, XSDDate]] = None
    timeframe_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.start_date is not None and not isinstance(self.start_date, XSDDate):
            self.start_date = XSDDate(self.start_date)

        if self.end_date is not None and not isinstance(self.end_date, XSDDate):
            self.end_date = XSDDate(self.end_date)

        if not isinstance(self.timeframe_details, list):
            self.timeframe_details = [self.timeframe_details] if self.timeframe_details is not None else []
        self.timeframe_details = [v if isinstance(v, str) else str(v) for v in self.timeframe_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DirectCollection(DatasetProperty):
    """
    Indicates whether the data was collected directly from the individuals in question or obtained via third
    parties/other sources.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["collection/DirectCollection"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:collection/DirectCollection"
    class_name: ClassVar[str] = "DirectCollection"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DirectCollection

    is_direct: Optional[Union[bool, Bool]] = None
    collection_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.is_direct is not None and not isinstance(self.is_direct, Bool):
            self.is_direct = Bool(self.is_direct)

        if not isinstance(self.collection_details, list):
            self.collection_details = [self.collection_details] if self.collection_details is not None else []
        self.collection_details = [v if isinstance(v, str) else str(v) for v in self.collection_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class PreprocessingStrategy(DatasetProperty):
    """
    Was any preprocessing of the data done (e.g., discretization or bucketing, tokenization, SIFT feature extraction)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DPREPROCESSING["PreprocessingStrategy"]
    class_class_curie: ClassVar[str] = "d4dpreprocessing:PreprocessingStrategy"
    class_name: ClassVar[str] = "PreprocessingStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.PreprocessingStrategy

    preprocessing_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.preprocessing_details, list):
            self.preprocessing_details = [self.preprocessing_details] if self.preprocessing_details is not None else []
        self.preprocessing_details = [v if isinstance(v, str) else str(v) for v in self.preprocessing_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CleaningStrategy(DatasetProperty):
    """
    Was any cleaning of the data done (e.g., removal of instances, processing of missing values)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DPREPROCESSING["CleaningStrategy"]
    class_class_curie: ClassVar[str] = "d4dpreprocessing:CleaningStrategy"
    class_name: ClassVar[str] = "CleaningStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CleaningStrategy

    cleaning_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.cleaning_details, list):
            self.cleaning_details = [self.cleaning_details] if self.cleaning_details is not None else []
        self.cleaning_details = [v if isinstance(v, str) else str(v) for v in self.cleaning_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class LabelingStrategy(DatasetProperty):
    """
    Was any labeling of the data done (e.g., part-of-speech tagging)? This class documents the annotation process and
    quality metrics.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DPREPROCESSING["LabelingStrategy"]
    class_class_curie: ClassVar[str] = "d4dpreprocessing:LabelingStrategy"
    class_name: ClassVar[str] = "LabelingStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.LabelingStrategy

    annotation_platform: Optional[str] = None
    annotations_per_item: Optional[int] = None
    inter_annotator_agreement: Optional[str] = None
    annotator_demographics: Optional[Union[str, list[str]]] = empty_list()
    labeling_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.annotation_platform is not None and not isinstance(self.annotation_platform, str):
            self.annotation_platform = str(self.annotation_platform)

        if self.annotations_per_item is not None and not isinstance(self.annotations_per_item, int):
            self.annotations_per_item = int(self.annotations_per_item)

        if self.inter_annotator_agreement is not None and not isinstance(self.inter_annotator_agreement, str):
            self.inter_annotator_agreement = str(self.inter_annotator_agreement)

        if not isinstance(self.annotator_demographics, list):
            self.annotator_demographics = [self.annotator_demographics] if self.annotator_demographics is not None else []
        self.annotator_demographics = [v if isinstance(v, str) else str(v) for v in self.annotator_demographics]

        if not isinstance(self.labeling_details, list):
            self.labeling_details = [self.labeling_details] if self.labeling_details is not None else []
        self.labeling_details = [v if isinstance(v, str) else str(v) for v in self.labeling_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class RawData(DatasetProperty):
    """
    Was the "raw" data saved in addition to the preprocessed/cleaned/labeled data? If so, please provide a link or
    other access point to the "raw" data.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DPREPROCESSING["RawData"]
    class_class_curie: ClassVar[str] = "d4dpreprocessing:RawData"
    class_name: ClassVar[str] = "RawData"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.RawData

    access_url: Optional[Union[str, URI]] = None
    raw_data_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.access_url is not None and not isinstance(self.access_url, URI):
            self.access_url = URI(self.access_url)

        if not isinstance(self.raw_data_details, list):
            self.raw_data_details = [self.raw_data_details] if self.raw_data_details is not None else []
        self.raw_data_details = [v if isinstance(v, str) else str(v) for v in self.raw_data_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ExistingUse(DatasetProperty):
    """
    Has the dataset been used for any tasks already?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["ExistingUse"]
    class_class_curie: ClassVar[str] = "d4duses:ExistingUse"
    class_name: ClassVar[str] = "ExistingUse"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExistingUse

    examples: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.examples, list):
            self.examples = [self.examples] if self.examples is not None else []
        self.examples = [v if isinstance(v, str) else str(v) for v in self.examples]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class UseRepository(DatasetProperty):
    """
    Is there a repository that links to any or all papers or systems that use the dataset? If so, provide a link or
    other access point.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["UseRepository"]
    class_class_curie: ClassVar[str] = "d4duses:UseRepository"
    class_name: ClassVar[str] = "UseRepository"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.UseRepository

    repository_url: Optional[Union[str, URI]] = None
    repository_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.repository_url is not None and not isinstance(self.repository_url, URI):
            self.repository_url = URI(self.repository_url)

        if not isinstance(self.repository_details, list):
            self.repository_details = [self.repository_details] if self.repository_details is not None else []
        self.repository_details = [v if isinstance(v, str) else str(v) for v in self.repository_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class OtherTask(DatasetProperty):
    """
    What other tasks could the dataset be used for?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["OtherTask"]
    class_class_curie: ClassVar[str] = "d4duses:OtherTask"
    class_name: ClassVar[str] = "OtherTask"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.OtherTask

    task_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.task_details, list):
            self.task_details = [self.task_details] if self.task_details is not None else []
        self.task_details = [v if isinstance(v, str) else str(v) for v in self.task_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class FutureUseImpact(DatasetProperty):
    """
    Is there anything about the dataset's composition or collection that might impact future uses or create risks/harm
    (e.g., unfair treatment, legal or financial risks)? If so, describe these impacts and any mitigation strategies.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["FutureUseImpact"]
    class_class_curie: ClassVar[str] = "d4duses:FutureUseImpact"
    class_name: ClassVar[str] = "FutureUseImpact"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.FutureUseImpact

    impact_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.impact_details, list):
            self.impact_details = [self.impact_details] if self.impact_details is not None else []
        self.impact_details = [v if isinstance(v, str) else str(v) for v in self.impact_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DiscouragedUse(DatasetProperty):
    """
    Are there tasks for which the dataset should not be used?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["DiscouragedUse"]
    class_class_curie: ClassVar[str] = "d4duses:DiscouragedUse"
    class_name: ClassVar[str] = "DiscouragedUse"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DiscouragedUse

    discouragement_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.discouragement_details, list):
            self.discouragement_details = [self.discouragement_details] if self.discouragement_details is not None else []
        self.discouragement_details = [v if isinstance(v, str) else str(v) for v in self.discouragement_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class IntendedUse(DatasetProperty):
    """
    Explicit statement of intended uses for this dataset. Complements FutureUseImpact by focusing on positive,
    recommended applications rather than risks. Aligns with RO-Crate "Intended Use" field.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["IntendedUse"]
    class_class_curie: ClassVar[str] = "d4duses:IntendedUse"
    class_name: ClassVar[str] = "IntendedUse"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.IntendedUse

    examples: Optional[Union[str, list[str]]] = empty_list()
    usage_notes: Optional[str] = None
    use_category: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.examples, list):
            self.examples = [self.examples] if self.examples is not None else []
        self.examples = [v if isinstance(v, str) else str(v) for v in self.examples]

        if self.usage_notes is not None and not isinstance(self.usage_notes, str):
            self.usage_notes = str(self.usage_notes)

        if not isinstance(self.use_category, list):
            self.use_category = [self.use_category] if self.use_category is not None else []
        self.use_category = [v if isinstance(v, str) else str(v) for v in self.use_category]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ProhibitedUse(DatasetProperty):
    """
    Explicit statement of prohibited or forbidden uses for this dataset. Stronger than DiscouragedUse - these are uses
    that are explicitly not permitted by license, ethics, or policy. Aligns with RO-Crate "Prohibited Uses" field.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DUSES["ProhibitedUse"]
    class_class_curie: ClassVar[str] = "d4duses:ProhibitedUse"
    class_name: ClassVar[str] = "ProhibitedUse"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ProhibitedUse

    prohibition_reason: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.prohibition_reason, list):
            self.prohibition_reason = [self.prohibition_reason] if self.prohibition_reason is not None else []
        self.prohibition_reason = [v if isinstance(v, str) else str(v) for v in self.prohibition_reason]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ThirdPartySharing(DatasetProperty):
    """
    Will the dataset be distributed to third parties outside of the entity (e.g., company, institution, organization)
    on behalf of which the dataset was created?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DDISTRIBUTION["ThirdPartySharing"]
    class_class_curie: ClassVar[str] = "d4ddistribution:ThirdPartySharing"
    class_name: ClassVar[str] = "ThirdPartySharing"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ThirdPartySharing

    is_shared: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.is_shared is not None and not isinstance(self.is_shared, Bool):
            self.is_shared = Bool(self.is_shared)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DistributionFormat(DatasetProperty):
    """
    How will the dataset be distributed (e.g., tarball on a website, API, GitHub)?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DDISTRIBUTION["DistributionFormat"]
    class_class_curie: ClassVar[str] = "d4ddistribution:DistributionFormat"
    class_name: ClassVar[str] = "DistributionFormat"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DistributionFormat

    access_urls: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.access_urls, list):
            self.access_urls = [self.access_urls] if self.access_urls is not None else []
        self.access_urls = [v if isinstance(v, str) else str(v) for v in self.access_urls]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DistributionDate(DatasetProperty):
    """
    When will the dataset be distributed?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DDISTRIBUTION["DistributionDate"]
    class_class_curie: ClassVar[str] = "d4ddistribution:DistributionDate"
    class_name: ClassVar[str] = "DistributionDate"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DistributionDate

    release_dates: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.release_dates, list):
            self.release_dates = [self.release_dates] if self.release_dates is not None else []
        self.release_dates = [v if isinstance(v, str) else str(v) for v in self.release_dates]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Maintainer(DatasetProperty):
    """
    Who will be supporting/hosting/maintaining the dataset?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMAINTENANCE["Maintainer"]
    class_class_curie: ClassVar[str] = "d4dmaintenance:Maintainer"
    class_name: ClassVar[str] = "Maintainer"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Maintainer

    role: Optional[Union[str, "CreatorOrMaintainerEnum"]] = None
    maintainer_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.role is not None and not isinstance(self.role, CreatorOrMaintainerEnum):
            self.role = CreatorOrMaintainerEnum(self.role)

        if not isinstance(self.maintainer_details, list):
            self.maintainer_details = [self.maintainer_details] if self.maintainer_details is not None else []
        self.maintainer_details = [v if isinstance(v, str) else str(v) for v in self.maintainer_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Erratum(DatasetProperty):
    """
    Is there an erratum? If so, please provide a link or other access point.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMAINTENANCE["Erratum"]
    class_class_curie: ClassVar[str] = "d4dmaintenance:Erratum"
    class_name: ClassVar[str] = "Erratum"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Erratum

    erratum_url: Optional[Union[str, URI]] = None
    erratum_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.erratum_url is not None and not isinstance(self.erratum_url, URI):
            self.erratum_url = URI(self.erratum_url)

        if not isinstance(self.erratum_details, list):
            self.erratum_details = [self.erratum_details] if self.erratum_details is not None else []
        self.erratum_details = [v if isinstance(v, str) else str(v) for v in self.erratum_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class UpdatePlan(DatasetProperty):
    """
    Will the dataset be updated (e.g., to correct labeling errors, add new instances, delete instances)? If so, how
    often, by whom, and how will these updates be communicated?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMAINTENANCE["UpdatePlan"]
    class_class_curie: ClassVar[str] = "d4dmaintenance:UpdatePlan"
    class_name: ClassVar[str] = "UpdatePlan"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.UpdatePlan

    frequency: Optional[str] = None
    update_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.frequency is not None and not isinstance(self.frequency, str):
            self.frequency = str(self.frequency)

        if not isinstance(self.update_details, list):
            self.update_details = [self.update_details] if self.update_details is not None else []
        self.update_details = [v if isinstance(v, str) else str(v) for v in self.update_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class RetentionLimits(DatasetProperty):
    """
    If the dataset relates to people, are there applicable limits on the retention of their data (e.g., were
    individuals told their data would be deleted after a certain time)? If so, please describe these limits and how
    they will be enforced.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMAINTENANCE["RetentionLimits"]
    class_class_curie: ClassVar[str] = "d4dmaintenance:RetentionLimits"
    class_name: ClassVar[str] = "RetentionLimits"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.RetentionLimits

    retention_period: Optional[str] = None
    retention_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.retention_period is not None and not isinstance(self.retention_period, str):
            self.retention_period = str(self.retention_period)

        if not isinstance(self.retention_details, list):
            self.retention_details = [self.retention_details] if self.retention_details is not None else []
        self.retention_details = [v if isinstance(v, str) else str(v) for v in self.retention_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class VersionAccess(DatasetProperty):
    """
    Will older versions of the dataset continue to be supported/hosted/maintained? If so, how? If not, how will
    obsolescence be communicated to dataset consumers?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMAINTENANCE["VersionAccess"]
    class_class_curie: ClassVar[str] = "d4dmaintenance:VersionAccess"
    class_name: ClassVar[str] = "VersionAccess"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.VersionAccess

    latest_version_doi: Optional[str] = None
    versions_available: Optional[Union[str, list[str]]] = empty_list()
    version_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.latest_version_doi is not None and not isinstance(self.latest_version_doi, str):
            self.latest_version_doi = str(self.latest_version_doi)

        if not isinstance(self.versions_available, list):
            self.versions_available = [self.versions_available] if self.versions_available is not None else []
        self.versions_available = [v if isinstance(v, str) else str(v) for v in self.versions_available]

        if not isinstance(self.version_details, list):
            self.version_details = [self.version_details] if self.version_details is not None else []
        self.version_details = [v if isinstance(v, str) else str(v) for v in self.version_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ExtensionMechanism(DatasetProperty):
    """
    If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so? If
    so, please describe how those contributions are validated and communicated.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DMAINTENANCE["ExtensionMechanism"]
    class_class_curie: ClassVar[str] = "d4dmaintenance:ExtensionMechanism"
    class_name: ClassVar[str] = "ExtensionMechanism"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExtensionMechanism

    contribution_url: Optional[Union[str, URI]] = None
    extension_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.contribution_url is not None and not isinstance(self.contribution_url, URI):
            self.contribution_url = URI(self.contribution_url)

        if not isinstance(self.extension_details, list):
            self.extension_details = [self.extension_details] if self.extension_details is not None else []
        self.extension_details = [v if isinstance(v, str) else str(v) for v in self.extension_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class EthicalReview(DatasetProperty):
    """
    Were any ethical or compliance review processes conducted (e.g., by an institutional review board)? If so, please
    provide a description of these review processes, including the frequency of review and documentation of outcomes,
    as well as a link or other access point to any supporting documentation.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DETHICS["EthicalReview"]
    class_class_curie: ClassVar[str] = "d4dethics:EthicalReview"
    class_name: ClassVar[str] = "EthicalReview"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.EthicalReview

    contact_person: Optional[Union[str, PersonId]] = None
    reviewing_organization: Optional[Union[str, OrganizationId]] = None
    review_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.contact_person is not None and not isinstance(self.contact_person, PersonId):
            self.contact_person = PersonId(self.contact_person)

        if self.reviewing_organization is not None and not isinstance(self.reviewing_organization, OrganizationId):
            self.reviewing_organization = OrganizationId(self.reviewing_organization)

        if not isinstance(self.review_details, list):
            self.review_details = [self.review_details] if self.review_details is not None else []
        self.review_details = [v if isinstance(v, str) else str(v) for v in self.review_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DataProtectionImpact(DatasetProperty):
    """
    Has an analysis of the potential impact of the dataset and its use on data subjects (e.g., a data protection
    impact analysis) been conducted? If so, please provide a description of this analysis, including the outcomes, and
    any supporting documentation.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DETHICS["DataProtectionImpact"]
    class_class_curie: ClassVar[str] = "d4dethics:DataProtectionImpact"
    class_name: ClassVar[str] = "DataProtectionImpact"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataProtectionImpact

    impact_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.impact_details, list):
            self.impact_details = [self.impact_details] if self.impact_details is not None else []
        self.impact_details = [v if isinstance(v, str) else str(v) for v in self.impact_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CollectionNotification(DatasetProperty):
    """
    Were the individuals in question notified about the data collection? If so, please describe (or show with
    screenshots, etc.) how notice was provided, and reproduce the language of the notification itself if possible.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DETHICS["CollectionNotification"]
    class_class_curie: ClassVar[str] = "d4dethics:CollectionNotification"
    class_name: ClassVar[str] = "CollectionNotification"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionNotification

    notification_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.notification_details, list):
            self.notification_details = [self.notification_details] if self.notification_details is not None else []
        self.notification_details = [v if isinstance(v, str) else str(v) for v in self.notification_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CollectionConsent(DatasetProperty):
    """
    Did the individuals in question consent to the collection and use of their data? If so, how was consent requested
    and provided, and what language did individuals consent to?
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DETHICS["CollectionConsent"]
    class_class_curie: ClassVar[str] = "d4dethics:CollectionConsent"
    class_name: ClassVar[str] = "CollectionConsent"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionConsent

    consent_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.consent_details, list):
            self.consent_details = [self.consent_details] if self.consent_details is not None else []
        self.consent_details = [v if isinstance(v, str) else str(v) for v in self.consent_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ConsentRevocation(DatasetProperty):
    """
    If consent was obtained, were the consenting individuals provided with a mechanism to revoke their consent in the
    future or for certain uses? If so, please describe.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DETHICS["ConsentRevocation"]
    class_class_curie: ClassVar[str] = "d4dethics:ConsentRevocation"
    class_name: ClassVar[str] = "ConsentRevocation"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ConsentRevocation

    revocation_details: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.revocation_details, list):
            self.revocation_details = [self.revocation_details] if self.revocation_details is not None else []
        self.revocation_details = [v if isinstance(v, str) else str(v) for v in self.revocation_details]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class HumanSubjectResearch(DatasetProperty):
    """
    Information about whether the dataset involves human subjects research and what regulatory or ethical review
    processes were followed.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DHUMAN["HumanSubjectResearch"]
    class_class_curie: ClassVar[str] = "d4dhuman:HumanSubjectResearch"
    class_name: ClassVar[str] = "HumanSubjectResearch"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.HumanSubjectResearch

    involves_human_subjects: Optional[Union[bool, Bool]] = None
    irb_approval: Optional[Union[str, list[str]]] = empty_list()
    ethics_review_board: Optional[Union[str, list[str]]] = empty_list()
    special_populations: Optional[Union[str, list[str]]] = empty_list()
    regulatory_compliance: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.involves_human_subjects is not None and not isinstance(self.involves_human_subjects, Bool):
            self.involves_human_subjects = Bool(self.involves_human_subjects)

        if not isinstance(self.irb_approval, list):
            self.irb_approval = [self.irb_approval] if self.irb_approval is not None else []
        self.irb_approval = [v if isinstance(v, str) else str(v) for v in self.irb_approval]

        if not isinstance(self.ethics_review_board, list):
            self.ethics_review_board = [self.ethics_review_board] if self.ethics_review_board is not None else []
        self.ethics_review_board = [v if isinstance(v, str) else str(v) for v in self.ethics_review_board]

        if not isinstance(self.special_populations, list):
            self.special_populations = [self.special_populations] if self.special_populations is not None else []
        self.special_populations = [v if isinstance(v, str) else str(v) for v in self.special_populations]

        if not isinstance(self.regulatory_compliance, list):
            self.regulatory_compliance = [self.regulatory_compliance] if self.regulatory_compliance is not None else []
        self.regulatory_compliance = [v if isinstance(v, str) else str(v) for v in self.regulatory_compliance]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class InformedConsent(DatasetProperty):
    """
    Details about informed consent procedures used in human subjects research.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DHUMAN["InformedConsent"]
    class_class_curie: ClassVar[str] = "d4dhuman:InformedConsent"
    class_name: ClassVar[str] = "InformedConsent"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.InformedConsent

    consent_obtained: Optional[Union[bool, Bool]] = None
    consent_type: Optional[Union[str, list[str]]] = empty_list()
    consent_documentation: Optional[Union[str, list[str]]] = empty_list()
    withdrawal_mechanism: Optional[Union[str, list[str]]] = empty_list()
    consent_scope: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.consent_obtained is not None and not isinstance(self.consent_obtained, Bool):
            self.consent_obtained = Bool(self.consent_obtained)

        if not isinstance(self.consent_type, list):
            self.consent_type = [self.consent_type] if self.consent_type is not None else []
        self.consent_type = [v if isinstance(v, str) else str(v) for v in self.consent_type]

        if not isinstance(self.consent_documentation, list):
            self.consent_documentation = [self.consent_documentation] if self.consent_documentation is not None else []
        self.consent_documentation = [v if isinstance(v, str) else str(v) for v in self.consent_documentation]

        if not isinstance(self.withdrawal_mechanism, list):
            self.withdrawal_mechanism = [self.withdrawal_mechanism] if self.withdrawal_mechanism is not None else []
        self.withdrawal_mechanism = [v if isinstance(v, str) else str(v) for v in self.withdrawal_mechanism]

        if not isinstance(self.consent_scope, list):
            self.consent_scope = [self.consent_scope] if self.consent_scope is not None else []
        self.consent_scope = [v if isinstance(v, str) else str(v) for v in self.consent_scope]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ParticipantPrivacy(DatasetProperty):
    """
    Information about privacy protections and anonymization procedures for human research participants.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DHUMAN["ParticipantPrivacy"]
    class_class_curie: ClassVar[str] = "d4dhuman:ParticipantPrivacy"
    class_name: ClassVar[str] = "ParticipantPrivacy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ParticipantPrivacy

    anonymization_method: Optional[Union[str, list[str]]] = empty_list()
    reidentification_risk: Optional[Union[str, list[str]]] = empty_list()
    privacy_techniques: Optional[Union[str, list[str]]] = empty_list()
    data_linkage: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.anonymization_method, list):
            self.anonymization_method = [self.anonymization_method] if self.anonymization_method is not None else []
        self.anonymization_method = [v if isinstance(v, str) else str(v) for v in self.anonymization_method]

        if not isinstance(self.reidentification_risk, list):
            self.reidentification_risk = [self.reidentification_risk] if self.reidentification_risk is not None else []
        self.reidentification_risk = [v if isinstance(v, str) else str(v) for v in self.reidentification_risk]

        if not isinstance(self.privacy_techniques, list):
            self.privacy_techniques = [self.privacy_techniques] if self.privacy_techniques is not None else []
        self.privacy_techniques = [v if isinstance(v, str) else str(v) for v in self.privacy_techniques]

        if not isinstance(self.data_linkage, list):
            self.data_linkage = [self.data_linkage] if self.data_linkage is not None else []
        self.data_linkage = [v if isinstance(v, str) else str(v) for v in self.data_linkage]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class HumanSubjectCompensation(DatasetProperty):
    """
    Information about compensation or incentives provided to human research participants.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DHUMAN["HumanSubjectCompensation"]
    class_class_curie: ClassVar[str] = "d4dhuman:HumanSubjectCompensation"
    class_name: ClassVar[str] = "HumanSubjectCompensation"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.HumanSubjectCompensation

    compensation_provided: Optional[Union[bool, Bool]] = None
    compensation_type: Optional[Union[str, list[str]]] = empty_list()
    compensation_amount: Optional[Union[str, list[str]]] = empty_list()
    compensation_rationale: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.compensation_provided is not None and not isinstance(self.compensation_provided, Bool):
            self.compensation_provided = Bool(self.compensation_provided)

        if not isinstance(self.compensation_type, list):
            self.compensation_type = [self.compensation_type] if self.compensation_type is not None else []
        self.compensation_type = [v if isinstance(v, str) else str(v) for v in self.compensation_type]

        if not isinstance(self.compensation_amount, list):
            self.compensation_amount = [self.compensation_amount] if self.compensation_amount is not None else []
        self.compensation_amount = [v if isinstance(v, str) else str(v) for v in self.compensation_amount]

        if not isinstance(self.compensation_rationale, list):
            self.compensation_rationale = [self.compensation_rationale] if self.compensation_rationale is not None else []
        self.compensation_rationale = [v if isinstance(v, str) else str(v) for v in self.compensation_rationale]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class VulnerablePopulations(DatasetProperty):
    """
    Information about protections for vulnerable populations in human subjects research.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DHUMAN["VulnerablePopulations"]
    class_class_curie: ClassVar[str] = "d4dhuman:VulnerablePopulations"
    class_name: ClassVar[str] = "VulnerablePopulations"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.VulnerablePopulations

    vulnerable_groups_included: Optional[Union[bool, Bool]] = None
    special_protections: Optional[Union[str, list[str]]] = empty_list()
    assent_procedures: Optional[Union[str, list[str]]] = empty_list()
    guardian_consent: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.vulnerable_groups_included is not None and not isinstance(self.vulnerable_groups_included, Bool):
            self.vulnerable_groups_included = Bool(self.vulnerable_groups_included)

        if not isinstance(self.special_protections, list):
            self.special_protections = [self.special_protections] if self.special_protections is not None else []
        self.special_protections = [v if isinstance(v, str) else str(v) for v in self.special_protections]

        if not isinstance(self.assent_procedures, list):
            self.assent_procedures = [self.assent_procedures] if self.assent_procedures is not None else []
        self.assent_procedures = [v if isinstance(v, str) else str(v) for v in self.assent_procedures]

        if not isinstance(self.guardian_consent, list):
            self.guardian_consent = [self.guardian_consent] if self.guardian_consent is not None else []
        self.guardian_consent = [v if isinstance(v, str) else str(v) for v in self.guardian_consent]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class LicenseAndUseTerms(DatasetProperty):
    """
    Will the dataset be distributed under a copyright or other IP license, and/or under applicable terms of use?
    Provide a link or copy of relevant licensing terms and any fees.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DDATAGOVERNANCE["LicenseAndUseTerms"]
    class_class_curie: ClassVar[str] = "d4ddatagovernance:LicenseAndUseTerms"
    class_name: ClassVar[str] = "LicenseAndUseTerms"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.LicenseAndUseTerms

    license_terms: Optional[Union[str, list[str]]] = empty_list()
    data_use_permission: Optional[Union[Union[str, "DataUsePermissionEnum"], list[Union[str, "DataUsePermissionEnum"]]]] = empty_list()
    contact_person: Optional[Union[str, PersonId]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.license_terms, list):
            self.license_terms = [self.license_terms] if self.license_terms is not None else []
        self.license_terms = [v if isinstance(v, str) else str(v) for v in self.license_terms]

        if not isinstance(self.data_use_permission, list):
            self.data_use_permission = [self.data_use_permission] if self.data_use_permission is not None else []
        self.data_use_permission = [v if isinstance(v, DataUsePermissionEnum) else DataUsePermissionEnum(v) for v in self.data_use_permission]

        if self.contact_person is not None and not isinstance(self.contact_person, PersonId):
            self.contact_person = PersonId(self.contact_person)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class IPRestrictions(DatasetProperty):
    """
    Have any third parties imposed IP-based or other restrictions on the data associated with the instances? If so,
    describe them and note any relevant fees or licensing terms. Maps to DUO terms related to commercial/non-profit
    use restrictions (NCU, NPU, NPUNCU).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DDATAGOVERNANCE["IPRestrictions"]
    class_class_curie: ClassVar[str] = "d4ddatagovernance:IPRestrictions"
    class_name: ClassVar[str] = "IPRestrictions"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.IPRestrictions

    restrictions: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.restrictions, list):
            self.restrictions = [self.restrictions] if self.restrictions is not None else []
        self.restrictions = [v if isinstance(v, str) else str(v) for v in self.restrictions]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ExportControlRegulatoryRestrictions(DatasetProperty):
    """
    Do any export controls or other regulatory restrictions apply to the dataset or to individual instances? Includes
    compliance tracking for regulations like HIPAA and other US regulations. If so, please describe these restrictions
    and provide a link or copy of any supporting documentation. Maps to DUO terms related to ethics approval,
    geographic restrictions, and institutional requirements.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = D4DDATAGOVERNANCE["ExportControlRegulatoryRestrictions"]
    class_class_curie: ClassVar[str] = "d4ddatagovernance:ExportControlRegulatoryRestrictions"
    class_name: ClassVar[str] = "ExportControlRegulatoryRestrictions"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExportControlRegulatoryRestrictions

    regulatory_restrictions: Optional[Union[str, list[str]]] = empty_list()
    hipaa_compliant: Optional[Union[str, "ComplianceStatusEnum"]] = None
    other_compliance: Optional[Union[str, list[str]]] = empty_list()
    confidentiality_level: Optional[Union[str, "ConfidentialityLevelEnum"]] = None
    governance_committee_contact: Optional[Union[str, PersonId]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if not isinstance(self.regulatory_restrictions, list):
            self.regulatory_restrictions = [self.regulatory_restrictions] if self.regulatory_restrictions is not None else []
        self.regulatory_restrictions = [v if isinstance(v, str) else str(v) for v in self.regulatory_restrictions]

        if self.hipaa_compliant is not None and not isinstance(self.hipaa_compliant, ComplianceStatusEnum):
            self.hipaa_compliant = ComplianceStatusEnum(self.hipaa_compliant)

        if not isinstance(self.other_compliance, list):
            self.other_compliance = [self.other_compliance] if self.other_compliance is not None else []
        self.other_compliance = [v if isinstance(v, str) else str(v) for v in self.other_compliance]

        if self.confidentiality_level is not None and not isinstance(self.confidentiality_level, ConfidentialityLevelEnum):
            self.confidentiality_level = ConfidentialityLevelEnum(self.confidentiality_level)

        if self.governance_committee_contact is not None and not isinstance(self.governance_committee_contact, PersonId):
            self.governance_committee_contact = PersonId(self.governance_committee_contact)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class VariableMetadata(DatasetProperty):
    """
    Metadata describing an individual variable, field, or column in a dataset. Variables may represent measurements,
    observations, derived values, or categorical attributes.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["PropertyValue"]
    class_class_curie: ClassVar[str] = "schema:PropertyValue"
    class_name: ClassVar[str] = "VariableMetadata"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.VariableMetadata

    variable_name: str = None
    data_type: Optional[Union[str, "VariableTypeEnum"]] = None
    unit: Optional[Union[str, URIorCURIE]] = None
    missing_value_code: Optional[Union[str, list[str]]] = empty_list()
    minimum_value: Optional[float] = None
    maximum_value: Optional[float] = None
    categories: Optional[Union[str, list[str]]] = empty_list()
    examples: Optional[Union[str, list[str]]] = empty_list()
    is_identifier: Optional[Union[bool, Bool]] = None
    is_sensitive: Optional[Union[bool, Bool]] = None
    precision: Optional[int] = None
    measurement_technique: Optional[str] = None
    derivation: Optional[str] = None
    quality_notes: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.variable_name):
            self.MissingRequiredField("variable_name")
        if not isinstance(self.variable_name, str):
            self.variable_name = str(self.variable_name)

        if self.data_type is not None and not isinstance(self.data_type, VariableTypeEnum):
            self.data_type = VariableTypeEnum(self.data_type)

        if self.unit is not None and not isinstance(self.unit, URIorCURIE):
            self.unit = URIorCURIE(self.unit)

        if not isinstance(self.missing_value_code, list):
            self.missing_value_code = [self.missing_value_code] if self.missing_value_code is not None else []
        self.missing_value_code = [v if isinstance(v, str) else str(v) for v in self.missing_value_code]

        if self.minimum_value is not None and not isinstance(self.minimum_value, float):
            self.minimum_value = float(self.minimum_value)

        if self.maximum_value is not None and not isinstance(self.maximum_value, float):
            self.maximum_value = float(self.maximum_value)

        if not isinstance(self.categories, list):
            self.categories = [self.categories] if self.categories is not None else []
        self.categories = [v if isinstance(v, str) else str(v) for v in self.categories]

        if not isinstance(self.examples, list):
            self.examples = [self.examples] if self.examples is not None else []
        self.examples = [v if isinstance(v, str) else str(v) for v in self.examples]

        if self.is_identifier is not None and not isinstance(self.is_identifier, Bool):
            self.is_identifier = Bool(self.is_identifier)

        if self.is_sensitive is not None and not isinstance(self.is_sensitive, Bool):
            self.is_sensitive = Bool(self.is_sensitive)

        if self.precision is not None and not isinstance(self.precision, int):
            self.precision = int(self.precision)

        if self.measurement_technique is not None and not isinstance(self.measurement_technique, str):
            self.measurement_technique = str(self.measurement_technique)

        if self.derivation is not None and not isinstance(self.derivation, str):
            self.derivation = str(self.derivation)

        if not isinstance(self.quality_notes, list):
            self.quality_notes = [self.quality_notes] if self.quality_notes is not None else []
        self.quality_notes = [v if isinstance(v, str) else str(v) for v in self.quality_notes]

        super().__post_init__(**kwargs)


# Enumerations
class FormatEnum(EnumDefinitionImpl):

    CSV = PermissibleValue(text="CSV")
    TSV = PermissibleValue(text="TSV")
    XML = PermissibleValue(text="XML")
    JSON = PermissibleValue(text="JSON")
    JSONL = PermissibleValue(text="JSONL")
    YAML = PermissibleValue(text="YAML")
    HTML = PermissibleValue(text="HTML")
    PDF = PermissibleValue(text="PDF")
    DOCX = PermissibleValue(text="DOCX")
    XLSX = PermissibleValue(text="XLSX")
    PPTX = PermissibleValue(text="PPTX")
    TXT = PermissibleValue(text="TXT")
    MD = PermissibleValue(text="MD")
    ZIP = PermissibleValue(text="ZIP")
    TAR = PermissibleValue(text="TAR")
    GZ = PermissibleValue(text="GZ")
    BZ2 = PermissibleValue(text="BZ2")
    XZ = PermissibleValue(text="XZ")

    _defn = EnumDefinition(
        name="FormatEnum",
    )

class MediaTypeEnum(EnumDefinitionImpl):

    _defn = EnumDefinition(
        name="MediaTypeEnum",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "text/csv",
            PermissibleValue(text="text/csv"))
        setattr(cls, "text/tab-separated-values",
            PermissibleValue(text="text/tab-separated-values"))
        setattr(cls, "application/json",
            PermissibleValue(text="application/json"))
        setattr(cls, "application/xml",
            PermissibleValue(text="application/xml"))
        setattr(cls, "text/xml",
            PermissibleValue(text="text/xml"))
        setattr(cls, "application/yaml",
            PermissibleValue(text="application/yaml"))
        setattr(cls, "text/yaml",
            PermissibleValue(text="text/yaml"))
        setattr(cls, "text/html",
            PermissibleValue(text="text/html"))
        setattr(cls, "application/pdf",
            PermissibleValue(text="application/pdf"))
        setattr(cls, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            PermissibleValue(text="application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
        setattr(cls, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            PermissibleValue(text="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        setattr(cls, "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            PermissibleValue(text="application/vnd.openxmlformats-officedocument.presentationml.presentation"))
        setattr(cls, "text/plain",
            PermissibleValue(text="text/plain"))
        setattr(cls, "text/markdown",
            PermissibleValue(text="text/markdown"))
        setattr(cls, "application/zip",
            PermissibleValue(text="application/zip"))
        setattr(cls, "application/x-tar",
            PermissibleValue(text="application/x-tar"))
        setattr(cls, "application/gzip",
            PermissibleValue(text="application/gzip"))
        setattr(cls, "application/x-bzip2",
            PermissibleValue(text="application/x-bzip2"))
        setattr(cls, "application/x-xz",
            PermissibleValue(text="application/x-xz"))

class CompressionEnum(EnumDefinitionImpl):

    gzip = PermissibleValue(text="gzip")
    bzip2 = PermissibleValue(text="bzip2")
    zip = PermissibleValue(text="zip")
    tar = PermissibleValue(text="tar")
    xz = PermissibleValue(text="xz")
    lzma = PermissibleValue(text="lzma")
    compress = PermissibleValue(text="compress")

    _defn = EnumDefinition(
        name="CompressionEnum",
    )

class EncodingEnum(EnumDefinitionImpl):

    ASCII = PermissibleValue(text="ASCII")
    Big5 = PermissibleValue(text="Big5")
    GB2312 = PermissibleValue(text="GB2312")
    Shift_JIS = PermissibleValue(text="Shift_JIS")

    _defn = EnumDefinition(
        name="EncodingEnum",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "EUC-JP",
            PermissibleValue(text="EUC-JP"))
        setattr(cls, "EUC-KR",
            PermissibleValue(text="EUC-KR"))
        setattr(cls, "EUC-TW",
            PermissibleValue(text="EUC-TW"))
        setattr(cls, "HZ-GB-2312",
            PermissibleValue(text="HZ-GB-2312"))
        setattr(cls, "ISO-2022-CN-EXT",
            PermissibleValue(text="ISO-2022-CN-EXT"))
        setattr(cls, "ISO-2022-CN",
            PermissibleValue(text="ISO-2022-CN"))
        setattr(cls, "ISO-2022-JP-2",
            PermissibleValue(text="ISO-2022-JP-2"))
        setattr(cls, "ISO-2022-JP",
            PermissibleValue(text="ISO-2022-JP"))
        setattr(cls, "ISO-2022-KR",
            PermissibleValue(text="ISO-2022-KR"))
        setattr(cls, "ISO-8859-10",
            PermissibleValue(text="ISO-8859-10"))
        setattr(cls, "ISO-8859-11",
            PermissibleValue(text="ISO-8859-11"))
        setattr(cls, "ISO-8859-13",
            PermissibleValue(text="ISO-8859-13"))
        setattr(cls, "ISO-8859-14",
            PermissibleValue(text="ISO-8859-14"))
        setattr(cls, "ISO-8859-15",
            PermissibleValue(text="ISO-8859-15"))
        setattr(cls, "ISO-8859-16",
            PermissibleValue(text="ISO-8859-16"))
        setattr(cls, "ISO-8859-1",
            PermissibleValue(text="ISO-8859-1"))
        setattr(cls, "ISO-8859-2",
            PermissibleValue(text="ISO-8859-2"))
        setattr(cls, "ISO-8859-3",
            PermissibleValue(text="ISO-8859-3"))
        setattr(cls, "ISO-8859-4",
            PermissibleValue(text="ISO-8859-4"))
        setattr(cls, "ISO-8859-5",
            PermissibleValue(text="ISO-8859-5"))
        setattr(cls, "ISO-8859-6",
            PermissibleValue(text="ISO-8859-6"))
        setattr(cls, "ISO-8859-7",
            PermissibleValue(text="ISO-8859-7"))
        setattr(cls, "ISO-8859-8",
            PermissibleValue(text="ISO-8859-8"))
        setattr(cls, "ISO-8859-9",
            PermissibleValue(text="ISO-8859-9"))
        setattr(cls, "KOI8-R",
            PermissibleValue(text="KOI8-R"))
        setattr(cls, "KOI8-U",
            PermissibleValue(text="KOI8-U"))
        setattr(cls, "UTF-16",
            PermissibleValue(text="UTF-16"))
        setattr(cls, "UTF-32",
            PermissibleValue(text="UTF-32"))
        setattr(cls, "UTF-7",
            PermissibleValue(text="UTF-7"))
        setattr(cls, "UTF-8",
            PermissibleValue(text="UTF-8"))

class CRediTRoleEnum(EnumDefinitionImpl):
    """
    Contributor roles based on the CRediT (Contributor Roles Taxonomy). See https://credit.niso.org/
    """
    conceptualization = PermissibleValue(
        text="conceptualization",
        description="Ideas; formulation or evolution of overarching research goals and aims")
    methodology = PermissibleValue(
        text="methodology",
        description="Development or design of methodology; creation of models")
    software = PermissibleValue(
        text="software",
        description="Programming, software development; designing computer programs")
    validation = PermissibleValue(
        text="validation",
        description="Verification of the overall replication/reproducibility of results")
    formal_analysis = PermissibleValue(
        text="formal_analysis",
        description="Application of statistical, mathematical, or other formal techniques")
    investigation = PermissibleValue(
        text="investigation",
        description="Conducting the research and investigation process")
    resources = PermissibleValue(
        text="resources",
        description="Provision of study materials, reagents, patients, laboratory samples, etc.")
    data_curation = PermissibleValue(
        text="data_curation",
        description="Management activities to annotate, scrub data and maintain research data")
    writing_original_draft = PermissibleValue(
        text="writing_original_draft",
        description="Preparation, creation and/or presentation of the published work")
    writing_review_editing = PermissibleValue(
        text="writing_review_editing",
        description="Critical review, commentary or revision of the work")
    visualization = PermissibleValue(
        text="visualization",
        description="Preparation, creation and/or presentation of visualizations/data presentation")
    supervision = PermissibleValue(
        text="supervision",
        description="Oversight and leadership responsibility for the research activity")
    project_administration = PermissibleValue(
        text="project_administration",
        description="Management and coordination responsibility for the research activity")
    funding_acquisition = PermissibleValue(
        text="funding_acquisition",
        description="Acquisition of the financial support for the project")

    _defn = EnumDefinition(
        name="CRediTRoleEnum",
        description="Contributor roles based on the CRediT (Contributor Roles Taxonomy). See https://credit.niso.org/",
    )

class BiasTypeEnum(EnumDefinitionImpl):
    """
    Types of bias that may be present in datasets. Values are mapped to the Artificial Intelligence Ontology (AIO)
    bias taxonomy from BioPortal. See https://bioportal.bioontology.org/ontologies/AIO
    """
    selection_bias = PermissibleValue(
        text="selection_bias",
        description="Bias arising from non-random selection of data or participants.")
    measurement_bias = PermissibleValue(
        text="measurement_bias",
        description="""Bias in how data is measured or recorded. Occurs when features and labels are proxies for desired quantities, potentially leading to differential performance.""",
        meaning=AIO["MeasurementBias"])
    historical_bias = PermissibleValue(
        text="historical_bias",
        description="""Bias reflecting historical inequities or societal biases. Long-standing biases encoded in society over time.""",
        meaning=AIO["HistoricalBias"])
    representation_bias = PermissibleValue(
        text="representation_bias",
        description="""Certain groups are over- or under-represented in the data. Results from non-random sampling of subgroups making trends non-generalizable to new populations.""",
        meaning=AIO["RepresentationBias"])
    aggregation_bias = PermissibleValue(
        text="aggregation_bias",
        description="""Bias from inappropriately combining distinct groups. Related to making inferences about individuals based on their group membership.""")
    algorithmic_bias = PermissibleValue(
        text="algorithmic_bias",
        description="""Bias introduced or amplified by algorithmic processing. Computational bias from data analysis processes and methods.""")
    sampling_bias = PermissibleValue(
        text="sampling_bias",
        description="Bias from sampling methodology not representative of the population.")
    annotation_bias = PermissibleValue(
        text="annotation_bias",
        description="""Bias introduced during data labeling or annotation. Occurs when annotators rely on heuristics or exhibit systematic patterns in labeling.""")
    confirmation_bias = PermissibleValue(
        text="confirmation_bias",
        description="""Bias from seeking data that confirms pre-existing beliefs. Tendency to prefer information that confirms existing beliefs, influencing the search for, interpretation of, and recall of information.""",
        meaning=AIO["ConfirmationBias"])

    _defn = EnumDefinition(
        name="BiasTypeEnum",
        description="""Types of bias that may be present in datasets. Values are mapped to the Artificial Intelligence Ontology (AIO) bias taxonomy from BioPortal. See https://bioportal.bioontology.org/ontologies/AIO""",
    )

class LimitationTypeEnum(EnumDefinitionImpl):
    """
    Types of limitations that may affect dataset use or interpretation. Distinct from biases (systematic errors) and
    anomalies (data quality issues).
    """
    scope_limitation = PermissibleValue(
        text="scope_limitation",
        description="""Dataset does not cover all intended use cases or populations. The scope of the dataset is narrower than the intended application domain.""")
    temporal_limitation = PermissibleValue(
        text="temporal_limitation",
        description="""Dataset is limited to specific time periods. Data may not reflect current conditions or may not be applicable to other time periods.""")
    coverage_limitation = PermissibleValue(
        text="coverage_limitation",
        description="""Dataset has incomplete coverage of target domain. Missing data points, categories, or geographic regions within the intended scope.""")
    methodological_limitation = PermissibleValue(
        text="methodological_limitation",
        description="""Data collection methodology introduces constraints. Limitations arising from how data was gathered, measured, or processed.""")
    representativeness_limitation = PermissibleValue(
        text="representativeness_limitation",
        description="""Dataset may not be representative of target population. Sample may not accurately reflect the broader population of interest.""")
    resolution_limitation = PermissibleValue(
        text="resolution_limitation",
        description="""Data granularity or resolution is insufficient for some uses. Level of detail may not support fine-grained analysis or specific applications.""")
    integration_limitation = PermissibleValue(
        text="integration_limitation",
        description="""Challenges in combining with other data sources. Incompatibilities in formats, identifiers, or schemas that hinder data integration.""")

    _defn = EnumDefinition(
        name="LimitationTypeEnum",
        description="""Types of limitations that may affect dataset use or interpretation. Distinct from biases (systematic errors) and anomalies (data quality issues).""",
    )

class VersionTypeEnum(EnumDefinitionImpl):
    """
    Type of version change using semantic versioning principles. See https://semver.org/
    """
    MAJOR = PermissibleValue(
        text="MAJOR",
        description="Incompatible changes, breaking backward compatibility")
    MINOR = PermissibleValue(
        text="MINOR",
        description="Backward-compatible new functionality or enhancements")
    PATCH = PermissibleValue(
        text="PATCH",
        description="Backward-compatible bug fixes or minor corrections")

    _defn = EnumDefinition(
        name="VersionTypeEnum",
        description="Type of version change using semantic versioning principles. See https://semver.org/",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "Windows-1250",
            PermissibleValue(text="Windows-1250"))
        setattr(cls, "Windows-1251",
            PermissibleValue(text="Windows-1251"))
        setattr(cls, "Windows-1252",
            PermissibleValue(text="Windows-1252"))
        setattr(cls, "Windows-1253",
            PermissibleValue(text="Windows-1253"))
        setattr(cls, "Windows-1254",
            PermissibleValue(text="Windows-1254"))
        setattr(cls, "Windows-1255",
            PermissibleValue(text="Windows-1255"))
        setattr(cls, "Windows-1256",
            PermissibleValue(text="Windows-1256"))
        setattr(cls, "Windows-1257",
            PermissibleValue(text="Windows-1257"))
        setattr(cls, "Windows-1258",
            PermissibleValue(text="Windows-1258"))

class CreatorOrMaintainerEnum(EnumDefinitionImpl):
    """
    Types of agents (persons or organizations) involved in dataset creation or maintenance. Mapped to schema.org
    organization types.
    """
    data_subject = PermissibleValue(
        text="data_subject",
        description="A person whose information is recorded in the dataset.")
    third_party = PermissibleValue(
        text="third_party",
        description="A third party not involved in the direct creation or maintenance.")
    researcher = PermissibleValue(
        text="researcher",
        description="A researcher involved in dataset creation or maintenance.")
    industry = PermissibleValue(
        text="industry",
        description="Industry professional involved in dataset creation or maintenance.")
    academic_institution = PermissibleValue(
        text="academic_institution",
        description="Academic institution responsible for dataset.")
    government_agency = PermissibleValue(
        text="government_agency",
        description="Government agency responsible for dataset.")
    commercial_entity = PermissibleValue(
        text="commercial_entity",
        description="Commercial entity responsible for dataset.")
    non_profit_organization = PermissibleValue(
        text="non_profit_organization",
        description="Non-profit organization responsible for dataset.")
    crowdsourced = PermissibleValue(
        text="crowdsourced",
        description="Dataset created through crowdsourcing efforts with multiple contributors.")
    automated_system = PermissibleValue(
        text="automated_system",
        description="Automated system or process responsible for dataset.")
    other = PermissibleValue(
        text="other",
        description="Other type of creator or maintainer not listed.")

    _defn = EnumDefinition(
        name="CreatorOrMaintainerEnum",
        description="""Types of agents (persons or organizations) involved in dataset creation or maintenance. Mapped to schema.org organization types.""",
    )

class Boolean(EnumDefinitionImpl):

    true = PermissibleValue(
        text="true",
        title="True")
    false = PermissibleValue(
        text="false",
        title="False")
    unknown = PermissibleValue(
        text="unknown",
        title="Unknown")

    _defn = EnumDefinition(
        name="Boolean",
    )

class DatasetRelationshipTypeEnum(EnumDefinitionImpl):
    """
    Standardized types of relationships between datasets, based on DataCite Metadata Schema RelationType controlled
    vocabulary and Dublin Core relationship terms. See https://datacite-metadata-schema.readthedocs.io/ and
    http://purl.org/dc/terms/
    """
    derives_from = PermissibleValue(
        text="derives_from",
        description="""This dataset is derived from the target dataset through processing, analysis, or transformation. Equivalent to DataCite IsDerivedFrom.""")
    supplements = PermissibleValue(
        text="supplements",
        description="This dataset supplements or adds to the target dataset. Equivalent to DataCite IsSupplementTo.")
    is_supplemented_by = PermissibleValue(
        text="is_supplemented_by",
        description="This dataset is supplemented by the target dataset. Equivalent to DataCite IsSupplementedBy.")
    is_version_of = PermissibleValue(
        text="is_version_of",
        description="""This dataset is a version of the target dataset (e.g., updated, corrected, or revised version). Equivalent to DataCite IsVersionOf.""")
    is_new_version_of = PermissibleValue(
        text="is_new_version_of",
        description="""This dataset is a new version that replaces or updates the target dataset. Equivalent to DataCite IsNewVersionOf.""")
    replaces = PermissibleValue(
        text="replaces",
        description="This dataset replaces or supersedes the target dataset. Equivalent to DataCite Obsoletes.")
    is_replaced_by = PermissibleValue(
        text="is_replaced_by",
        description="""This dataset is replaced or superseded by the target dataset. Equivalent to DataCite IsObsoletedBy.""")
    is_required_by = PermissibleValue(
        text="is_required_by",
        description="This dataset is required by the target dataset. Equivalent to DataCite IsRequiredBy.")
    requires = PermissibleValue(
        text="requires",
        description="This dataset requires the target dataset. Equivalent to DataCite Requires.")
    is_part_of = PermissibleValue(
        text="is_part_of",
        description="""This dataset is part of the target dataset (e.g., subset, component). Equivalent to DataCite IsPartOf.""")
    has_part = PermissibleValue(
        text="has_part",
        description="This dataset has the target dataset as a part. Equivalent to DataCite HasPart.")
    is_referenced_by = PermissibleValue(
        text="is_referenced_by",
        description="""This dataset is referenced or cited by the target dataset. Equivalent to DataCite IsReferencedBy.""")
    references = PermissibleValue(
        text="references",
        description="This dataset references or cites the target dataset. Equivalent to DataCite References.")
    is_identical_to = PermissibleValue(
        text="is_identical_to",
        description="""This dataset is identical to the target dataset (e.g., mirror, copy). Equivalent to DataCite IsIdenticalTo.""")

    _defn = EnumDefinition(
        name="DatasetRelationshipTypeEnum",
        description="""Standardized types of relationships between datasets, based on DataCite Metadata Schema RelationType controlled vocabulary and Dublin Core relationship terms. See https://datacite-metadata-schema.readthedocs.io/ and http://purl.org/dc/terms/""",
    )

class ComplianceStatusEnum(EnumDefinitionImpl):
    """
    Compliance status for regulatory frameworks. Indicates the extent to which a dataset complies with specific
    regulations (e.g., HIPAA, 45 CFR 46). These are workflow status values that may evolve as regulations are assessed
    or as the dataset is modified.
    """
    compliant = PermissibleValue(
        text="compliant",
        description="Dataset is compliant with the regulation. All requirements are met and documented.")
    partially_compliant = PermissibleValue(
        text="partially_compliant",
        description="""Dataset is partially compliant, with known limitations or gaps in compliance. Some but not all requirements are met.""")
    not_compliant = PermissibleValue(
        text="not_compliant",
        description="Dataset does not comply with the regulation. Significant requirements are not met.")
    not_applicable = PermissibleValue(
        text="not_applicable",
        description="Regulation does not apply to this dataset based on scope, jurisdiction, or subject matter.")
    under_review = PermissibleValue(
        text="under_review",
        description="""Compliance status is currently under review or assessment. Final determination has not been made.""")

    _defn = EnumDefinition(
        name="ComplianceStatusEnum",
        description="""Compliance status for regulatory frameworks. Indicates the extent to which a dataset complies with specific regulations (e.g., HIPAA, 45 CFR 46). These are workflow status values that may evolve as regulations are assessed or as the dataset is modified.""",
    )

class ConfidentialityLevelEnum(EnumDefinitionImpl):
    """
    Confidentiality classification levels for datasets indicating the degree of access restrictions and data
    sensitivity.
    NOTE: This enum classifies data sensitivity and access control (WHO can access), which is orthogonal to
    DataUsePermissionEnum that specifies use restrictions (WHAT authorized users can do with data).
    ConfidentialityLevelEnum determines access requirements, while DataUsePermissionEnum uses DUO terms to specify
    permitted uses once access is granted.
    """
    unrestricted = PermissibleValue(
        text="unrestricted",
        description="""No confidentiality restrictions. Data is publicly available with no access controls required. Equivalent to public or open access data.""")
    restricted = PermissibleValue(
        text="restricted",
        description="""Restricted access requiring approval or registration. Data contains sensitive information requiring controlled access. May require account creation, data use agreement, or institutional approval.""")
    confidential = PermissibleValue(
        text="confidential",
        description="""Highly confidential with strict access controls. Data contains highly sensitive information with significant privacy or security implications. Typically requires IRB approval, formal data use agreements, institutional authorization, or other formal vetting processes.""")

    _defn = EnumDefinition(
        name="ConfidentialityLevelEnum",
        description="""Confidentiality classification levels for datasets indicating the degree of access restrictions and data sensitivity.
NOTE: This enum classifies data sensitivity and access control (WHO can access), which is orthogonal to DataUsePermissionEnum that specifies use restrictions (WHAT authorized users can do with data). ConfidentialityLevelEnum determines access requirements, while DataUsePermissionEnum uses DUO terms to specify permitted uses once access is granted.""",
    )

class DataUsePermissionEnum(EnumDefinitionImpl):
    """
    Data use permissions and restrictions based on the Data Use Ontology (DUO). DUO is a standardized ontology for
    representing data use conditions developed by GA4GH. See https://github.com/EBISPOT/DUO
    """
    no_restriction = PermissibleValue(
        text="no_restriction",
        description="No restriction on data use",
        meaning=DUO["0000004"])
    general_research_use = PermissibleValue(
        text="general_research_use",
        description="Data available for any research purpose (GRU)",
        meaning=DUO["0000042"])
    health_medical_biomedical_research = PermissibleValue(
        text="health_medical_biomedical_research",
        description="Data limited to health, medical, or biomedical research (HMB)",
        meaning=DUO["0000006"])
    disease_specific_research = PermissibleValue(
        text="disease_specific_research",
        description="Data limited to research on specified disease(s) (DS)",
        meaning=DUO["0000007"])
    population_origins_ancestry_research = PermissibleValue(
        text="population_origins_ancestry_research",
        description="Data limited to population origins or ancestry research (POA)",
        meaning=DUO["0000011"])
    clinical_care_use = PermissibleValue(
        text="clinical_care_use",
        description="Data available for clinical care and applications (CC)",
        meaning=DUO["0000043"])
    no_commercial_use = PermissibleValue(
        text="no_commercial_use",
        description="Data use limited to non-commercial purposes (NCU)",
        meaning=DUO["0000046"])
    non_profit_use_only = PermissibleValue(
        text="non_profit_use_only",
        description="Data use limited to not-for-profit organizations (NPU)",
        meaning=DUO["0000045"])
    non_profit_use_and_non_commercial_use = PermissibleValue(
        text="non_profit_use_and_non_commercial_use",
        description="Data limited to not-for-profit organizations and non-commercial use (NPUNCU)",
        meaning=DUO["0000018"])
    no_methods_development = PermissibleValue(
        text="no_methods_development",
        description="Data cannot be used for methods or software development (NMDS)",
        meaning=DUO["0000015"])
    genetic_studies_only = PermissibleValue(
        text="genetic_studies_only",
        description="Data limited to genetic studies only (GSO)",
        meaning=DUO["0000016"])
    ethics_approval_required = PermissibleValue(
        text="ethics_approval_required",
        description="Ethics approval (e.g., IRB/ERB) required for data use (IRB)",
        meaning=DUO["0000021"])
    collaboration_required = PermissibleValue(
        text="collaboration_required",
        description="Collaboration with primary investigator required (COL)",
        meaning=DUO["0000020"])
    publication_required = PermissibleValue(
        text="publication_required",
        description="Results must be published/shared with research community (PUB)",
        meaning=DUO["0000019"])
    geographic_restriction = PermissibleValue(
        text="geographic_restriction",
        description="Data use limited to specific geographic region (GS)",
        meaning=DUO["0000022"])
    institution_specific = PermissibleValue(
        text="institution_specific",
        description="Data use limited to approved institutions (IS)",
        meaning=DUO["0000028"])
    project_specific = PermissibleValue(
        text="project_specific",
        description="Data use limited to approved project(s) (PS)",
        meaning=DUO["0000027"])
    user_specific = PermissibleValue(
        text="user_specific",
        description="Data use limited to approved users (US)",
        meaning=DUO["0000026"])
    time_limit = PermissibleValue(
        text="time_limit",
        description="Data use approved for limited time period (TS)",
        meaning=DUO["0000025"])
    return_to_database = PermissibleValue(
        text="return_to_database",
        description="Derived data must be returned to database/resource (RTN)",
        meaning=DUO["0000029"])
    publication_moratorium = PermissibleValue(
        text="publication_moratorium",
        description="Publication restricted until specified date (MOR)",
        meaning=DUO["0000024"])
    no_population_ancestry_research = PermissibleValue(
        text="no_population_ancestry_research",
        description="Population/ancestry research prohibited (NPOA)",
        meaning=DUO["0000044"])

    _defn = EnumDefinition(
        name="DataUsePermissionEnum",
        description="""Data use permissions and restrictions based on the Data Use Ontology (DUO). DUO is a standardized ontology for representing data use conditions developed by GA4GH. See https://github.com/EBISPOT/DUO""",
    )

class VariableTypeEnum(EnumDefinitionImpl):
    """
    Common data types for variables. Values are mapped to schema.org DataType vocabulary. See
    https://schema.org/DataType
    """
    integer = PermissibleValue(
        text="integer",
        description="Whole numbers.")
    float = PermissibleValue(
        text="float",
        description="Floating-point numbers (single precision).")
    double = PermissibleValue(
        text="double",
        description="Double-precision floating-point numbers.")
    string = PermissibleValue(
        text="string",
        description="Text strings.")
    boolean = PermissibleValue(
        text="boolean",
        description="True/false values.")
    date = PermissibleValue(
        text="date",
        description="Date values (without time).")
    datetime = PermissibleValue(
        text="datetime",
        description="Date and time values.")
    categorical = PermissibleValue(
        text="categorical",
        description="""Categorical/factor variables with finite set of discrete values. Often used for nominal data (unordered categories).""")
    ordinal = PermissibleValue(
        text="ordinal",
        description="""Ordered categorical variables where values have a meaningful sequence (e.g., low/medium/high, strongly disagree/disagree/agree/strongly agree).""")
    identifier = PermissibleValue(
        text="identifier",
        description="Unique identifiers or keys for records or entities.")
    json = PermissibleValue(
        text="json",
        description="JSON-encoded data structures.")
    array = PermissibleValue(
        text="array",
        description="Arrays or lists of values. May contain elements of the same or different types.")
    object = PermissibleValue(
        text="object",
        description="Complex structured objects or nested data structures.")

    _defn = EnumDefinition(
        name="VariableTypeEnum",
        description="""Common data types for variables. Values are mapped to schema.org DataType vocabulary. See https://schema.org/DataType""",
    )

# Slots
class slots:
    pass

slots.same_as = Slot(uri=SCHEMA.sameAs, name="same_as", curie=SCHEMA.curie('sameAs'),
                   model_uri=DATA_SHEETS_SCHEMA.same_as, domain=None, range=Optional[Union[Union[str, URIorCURIE], list[Union[str, URIorCURIE]]]])

slots.themes = Slot(uri=DCAT.theme, name="themes", curie=DCAT.curie('theme'),
                   model_uri=DATA_SHEETS_SCHEMA.themes, domain=None, range=Optional[Union[Union[str, URIorCURIE], list[Union[str, URIorCURIE]]]])

slots.title = Slot(uri=DCTERMS.title, name="title", curie=DCTERMS.curie('title'),
                   model_uri=DATA_SHEETS_SCHEMA.title, domain=None, range=Optional[str])

slots.language = Slot(uri=DCTERMS.language, name="language", curie=DCTERMS.curie('language'),
                   model_uri=DATA_SHEETS_SCHEMA.language, domain=None, range=Optional[str])

slots.publisher = Slot(uri=DCTERMS.publisher, name="publisher", curie=DCTERMS.curie('publisher'),
                   model_uri=DATA_SHEETS_SCHEMA.publisher, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.issued = Slot(uri=DCTERMS.issued, name="issued", curie=DCTERMS.curie('issued'),
                   model_uri=DATA_SHEETS_SCHEMA.issued, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.page = Slot(uri=DCAT.landingPage, name="page", curie=DCAT.curie('landingPage'),
                   model_uri=DATA_SHEETS_SCHEMA.page, domain=None, range=Optional[str])

slots.dialect = Slot(uri=DATA_SHEETS_SCHEMA.dialect, name="dialect", curie=DATA_SHEETS_SCHEMA.curie('dialect'),
                   model_uri=DATA_SHEETS_SCHEMA.dialect, domain=None, range=Optional[str])

slots.bytes = Slot(uri=DCAT.byteSize, name="bytes", curie=DCAT.curie('byteSize'),
                   model_uri=DATA_SHEETS_SCHEMA.bytes, domain=None, range=Optional[int])

slots.path = Slot(uri=SCHEMA.contentUrl, name="path", curie=SCHEMA.curie('contentUrl'),
                   model_uri=DATA_SHEETS_SCHEMA.path, domain=None, range=Optional[str])

slots.download_url = Slot(uri=DCAT.downloadURL, name="download_url", curie=DCAT.curie('downloadURL'),
                   model_uri=DATA_SHEETS_SCHEMA.download_url, domain=None, range=Optional[Union[str, URI]])

slots.format = Slot(uri=DCTERMS.format, name="format", curie=DCTERMS.curie('format'),
                   model_uri=DATA_SHEETS_SCHEMA.format, domain=None, range=Optional[Union[str, "FormatEnum"]])

slots.encoding = Slot(uri=DCAT.mediaType, name="encoding", curie=DCAT.curie('mediaType'),
                   model_uri=DATA_SHEETS_SCHEMA.encoding, domain=None, range=Optional[Union[str, "EncodingEnum"]])

slots.compression = Slot(uri=DCAT.compressFormat, name="compression", curie=DCAT.curie('compressFormat'),
                   model_uri=DATA_SHEETS_SCHEMA.compression, domain=None, range=Optional[Union[str, "CompressionEnum"]])

slots.media_type = Slot(uri=DCAT.mediaType, name="media_type", curie=DCAT.curie('mediaType'),
                   model_uri=DATA_SHEETS_SCHEMA.media_type, domain=None, range=Optional[Union[str, "MediaTypeEnum"]])

slots.hash = Slot(uri=DCTERMS.identifier, name="hash", curie=DCTERMS.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.hash, domain=None, range=Optional[str])

slots.md5 = Slot(uri=DCTERMS.identifier, name="md5", curie=DCTERMS.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.md5, domain=None, range=Optional[str])

slots.sha256 = Slot(uri=DCTERMS.identifier, name="sha256", curie=DCTERMS.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.sha256, domain=None, range=Optional[str])

slots.conforms_to = Slot(uri=DCTERMS.conformsTo, name="conforms_to", curie=DCTERMS.curie('conformsTo'),
                   model_uri=DATA_SHEETS_SCHEMA.conforms_to, domain=None, range=Optional[str])

slots.conforms_to_schema = Slot(uri=DCTERMS.conformsTo, name="conforms_to_schema", curie=DCTERMS.curie('conformsTo'),
                   model_uri=DATA_SHEETS_SCHEMA.conforms_to_schema, domain=None, range=Optional[str])

slots.conforms_to_class = Slot(uri=DCTERMS.conformsTo, name="conforms_to_class", curie=DCTERMS.curie('conformsTo'),
                   model_uri=DATA_SHEETS_SCHEMA.conforms_to_class, domain=None, range=Optional[str])

slots.license = Slot(uri=DCTERMS.license, name="license", curie=DCTERMS.curie('license'),
                   model_uri=DATA_SHEETS_SCHEMA.license, domain=None, range=Optional[str])

slots.keywords = Slot(uri=DCAT.keyword, name="keywords", curie=DCAT.curie('keyword'),
                   model_uri=DATA_SHEETS_SCHEMA.keywords, domain=None, range=Optional[Union[str, list[str]]])

slots.version = Slot(uri=DCTERMS.hasVersion, name="version", curie=DCTERMS.curie('hasVersion'),
                   model_uri=DATA_SHEETS_SCHEMA.version, domain=None, range=Optional[str])

slots.created_by = Slot(uri=DCTERMS.creator, name="created_by", curie=DCTERMS.curie('creator'),
                   model_uri=DATA_SHEETS_SCHEMA.created_by, domain=None, range=Optional[str])

slots.created_on = Slot(uri=DCTERMS.created, name="created_on", curie=DCTERMS.curie('created'),
                   model_uri=DATA_SHEETS_SCHEMA.created_on, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.last_updated_on = Slot(uri=DCTERMS.modified, name="last_updated_on", curie=DCTERMS.curie('modified'),
                   model_uri=DATA_SHEETS_SCHEMA.last_updated_on, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.modified_by = Slot(uri=DCTERMS.contributor, name="modified_by", curie=DCTERMS.curie('contributor'),
                   model_uri=DATA_SHEETS_SCHEMA.modified_by, domain=None, range=Optional[str])

slots.status = Slot(uri=DCTERMS.type, name="status", curie=DCTERMS.curie('type'),
                   model_uri=DATA_SHEETS_SCHEMA.status, domain=None, range=Optional[str])

slots.was_derived_from = Slot(uri=PROV.wasDerivedFrom, name="was_derived_from", curie=PROV.curie('wasDerivedFrom'),
                   model_uri=DATA_SHEETS_SCHEMA.was_derived_from, domain=None, range=Optional[str])

slots.doi = Slot(uri=DCTERMS.identifier, name="doi", curie=DCTERMS.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.doi, domain=None, range=Optional[str],
                   pattern=re.compile(r'10\.\d{4,}\/.+'))

slots.datasetCollection__resources = Slot(uri=DATA_SHEETS_SCHEMA.resources, name="datasetCollection__resources", curie=DATA_SHEETS_SCHEMA.curie('resources'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetCollection__resources, domain=None, range=Optional[Union[dict[Union[str, DatasetId], Union[dict, Dataset]], list[Union[dict, Dataset]]]])

slots.dataset__purposes = Slot(uri=DATA_SHEETS_SCHEMA.purposes, name="dataset__purposes", curie=DATA_SHEETS_SCHEMA.curie('purposes'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__purposes, domain=None, range=Optional[Union[Union[dict, Purpose], list[Union[dict, Purpose]]]])

slots.dataset__tasks = Slot(uri=DATA_SHEETS_SCHEMA.tasks, name="dataset__tasks", curie=DATA_SHEETS_SCHEMA.curie('tasks'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__tasks, domain=None, range=Optional[Union[Union[dict, Task], list[Union[dict, Task]]]])

slots.dataset__addressing_gaps = Slot(uri=DATA_SHEETS_SCHEMA.addressing_gaps, name="dataset__addressing_gaps", curie=DATA_SHEETS_SCHEMA.curie('addressing_gaps'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__addressing_gaps, domain=None, range=Optional[Union[Union[dict, AddressingGap], list[Union[dict, AddressingGap]]]])

slots.dataset__creators = Slot(uri=DATA_SHEETS_SCHEMA.creators, name="dataset__creators", curie=DATA_SHEETS_SCHEMA.curie('creators'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__creators, domain=None, range=Optional[Union[Union[dict, Creator], list[Union[dict, Creator]]]])

slots.dataset__funders = Slot(uri=DATA_SHEETS_SCHEMA.funders, name="dataset__funders", curie=DATA_SHEETS_SCHEMA.curie('funders'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__funders, domain=None, range=Optional[Union[Union[dict, FundingMechanism], list[Union[dict, FundingMechanism]]]])

slots.dataset__subsets = Slot(uri=DCAT.distribution, name="dataset__subsets", curie=DCAT.curie('distribution'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__subsets, domain=None, range=Optional[Union[dict[Union[str, DataSubsetId], Union[dict, DataSubset]], list[Union[dict, DataSubset]]]])

slots.dataset__instances = Slot(uri=DATA_SHEETS_SCHEMA.instances, name="dataset__instances", curie=DATA_SHEETS_SCHEMA.curie('instances'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__instances, domain=None, range=Optional[Union[Union[dict, Instance], list[Union[dict, Instance]]]])

slots.dataset__anomalies = Slot(uri=DATA_SHEETS_SCHEMA.anomalies, name="dataset__anomalies", curie=DATA_SHEETS_SCHEMA.curie('anomalies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__anomalies, domain=None, range=Optional[Union[Union[dict, DataAnomaly], list[Union[dict, DataAnomaly]]]])

slots.dataset__known_biases = Slot(uri=DATA_SHEETS_SCHEMA.known_biases, name="dataset__known_biases", curie=DATA_SHEETS_SCHEMA.curie('known_biases'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__known_biases, domain=None, range=Optional[Union[Union[dict, DatasetBias], list[Union[dict, DatasetBias]]]])

slots.dataset__known_limitations = Slot(uri=DATA_SHEETS_SCHEMA.known_limitations, name="dataset__known_limitations", curie=DATA_SHEETS_SCHEMA.curie('known_limitations'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__known_limitations, domain=None, range=Optional[Union[Union[dict, DatasetLimitation], list[Union[dict, DatasetLimitation]]]])

slots.dataset__external_resources = Slot(uri=DATA_SHEETS_SCHEMA.external_resources, name="dataset__external_resources", curie=DATA_SHEETS_SCHEMA.curie('external_resources'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__external_resources, domain=None, range=Optional[Union[Union[dict, ExternalResource], list[Union[dict, ExternalResource]]]])

slots.dataset__confidential_elements = Slot(uri=DATA_SHEETS_SCHEMA.confidential_elements, name="dataset__confidential_elements", curie=DATA_SHEETS_SCHEMA.curie('confidential_elements'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__confidential_elements, domain=None, range=Optional[Union[Union[dict, Confidentiality], list[Union[dict, Confidentiality]]]])

slots.dataset__content_warnings = Slot(uri=DATA_SHEETS_SCHEMA.content_warnings, name="dataset__content_warnings", curie=DATA_SHEETS_SCHEMA.curie('content_warnings'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__content_warnings, domain=None, range=Optional[Union[Union[dict, ContentWarning], list[Union[dict, ContentWarning]]]])

slots.dataset__subpopulations = Slot(uri=DATA_SHEETS_SCHEMA.subpopulations, name="dataset__subpopulations", curie=DATA_SHEETS_SCHEMA.curie('subpopulations'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__subpopulations, domain=None, range=Optional[Union[Union[dict, Subpopulation], list[Union[dict, Subpopulation]]]])

slots.dataset__sensitive_elements = Slot(uri=DATA_SHEETS_SCHEMA.sensitive_elements, name="dataset__sensitive_elements", curie=DATA_SHEETS_SCHEMA.curie('sensitive_elements'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__sensitive_elements, domain=None, range=Optional[Union[Union[dict, SensitiveElement], list[Union[dict, SensitiveElement]]]])

slots.dataset__acquisition_methods = Slot(uri=DATA_SHEETS_SCHEMA.acquisition_methods, name="dataset__acquisition_methods", curie=DATA_SHEETS_SCHEMA.curie('acquisition_methods'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__acquisition_methods, domain=None, range=Optional[Union[Union[dict, InstanceAcquisition], list[Union[dict, InstanceAcquisition]]]])

slots.dataset__collection_mechanisms = Slot(uri=DATA_SHEETS_SCHEMA.collection_mechanisms, name="dataset__collection_mechanisms", curie=DATA_SHEETS_SCHEMA.curie('collection_mechanisms'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__collection_mechanisms, domain=None, range=Optional[Union[Union[dict, CollectionMechanism], list[Union[dict, CollectionMechanism]]]])

slots.dataset__sampling_strategies = Slot(uri=DATA_SHEETS_SCHEMA.sampling_strategies, name="dataset__sampling_strategies", curie=DATA_SHEETS_SCHEMA.curie('sampling_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__sampling_strategies, domain=None, range=Optional[Union[Union[dict, SamplingStrategy], list[Union[dict, SamplingStrategy]]]])

slots.dataset__data_collectors = Slot(uri=DATA_SHEETS_SCHEMA.data_collectors, name="dataset__data_collectors", curie=DATA_SHEETS_SCHEMA.curie('data_collectors'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__data_collectors, domain=None, range=Optional[Union[Union[dict, DataCollector], list[Union[dict, DataCollector]]]])

slots.dataset__collection_timeframes = Slot(uri=DATA_SHEETS_SCHEMA.collection_timeframes, name="dataset__collection_timeframes", curie=DATA_SHEETS_SCHEMA.curie('collection_timeframes'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__collection_timeframes, domain=None, range=Optional[Union[Union[dict, CollectionTimeframe], list[Union[dict, CollectionTimeframe]]]])

slots.dataset__ethical_reviews = Slot(uri=DATA_SHEETS_SCHEMA.ethical_reviews, name="dataset__ethical_reviews", curie=DATA_SHEETS_SCHEMA.curie('ethical_reviews'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__ethical_reviews, domain=None, range=Optional[Union[Union[dict, EthicalReview], list[Union[dict, EthicalReview]]]])

slots.dataset__data_protection_impacts = Slot(uri=DATA_SHEETS_SCHEMA.data_protection_impacts, name="dataset__data_protection_impacts", curie=DATA_SHEETS_SCHEMA.curie('data_protection_impacts'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__data_protection_impacts, domain=None, range=Optional[Union[Union[dict, DataProtectionImpact], list[Union[dict, DataProtectionImpact]]]])

slots.dataset__human_subject_research = Slot(uri=DATA_SHEETS_SCHEMA.human_subject_research, name="dataset__human_subject_research", curie=DATA_SHEETS_SCHEMA.curie('human_subject_research'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__human_subject_research, domain=None, range=Optional[Union[dict, HumanSubjectResearch]])

slots.dataset__informed_consent = Slot(uri=DATA_SHEETS_SCHEMA.informed_consent, name="dataset__informed_consent", curie=DATA_SHEETS_SCHEMA.curie('informed_consent'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__informed_consent, domain=None, range=Optional[Union[Union[dict, InformedConsent], list[Union[dict, InformedConsent]]]])

slots.dataset__participant_privacy = Slot(uri=DATA_SHEETS_SCHEMA.participant_privacy, name="dataset__participant_privacy", curie=DATA_SHEETS_SCHEMA.curie('participant_privacy'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__participant_privacy, domain=None, range=Optional[Union[Union[dict, ParticipantPrivacy], list[Union[dict, ParticipantPrivacy]]]])

slots.dataset__participant_compensation = Slot(uri=DATA_SHEETS_SCHEMA.participant_compensation, name="dataset__participant_compensation", curie=DATA_SHEETS_SCHEMA.curie('participant_compensation'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__participant_compensation, domain=None, range=Optional[Union[dict, HumanSubjectCompensation]])

slots.dataset__vulnerable_populations = Slot(uri=DATA_SHEETS_SCHEMA.vulnerable_populations, name="dataset__vulnerable_populations", curie=DATA_SHEETS_SCHEMA.curie('vulnerable_populations'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__vulnerable_populations, domain=None, range=Optional[Union[dict, VulnerablePopulations]])

slots.dataset__preprocessing_strategies = Slot(uri=DATA_SHEETS_SCHEMA.preprocessing_strategies, name="dataset__preprocessing_strategies", curie=DATA_SHEETS_SCHEMA.curie('preprocessing_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__preprocessing_strategies, domain=None, range=Optional[Union[Union[dict, PreprocessingStrategy], list[Union[dict, PreprocessingStrategy]]]])

slots.dataset__cleaning_strategies = Slot(uri=DATA_SHEETS_SCHEMA.cleaning_strategies, name="dataset__cleaning_strategies", curie=DATA_SHEETS_SCHEMA.curie('cleaning_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__cleaning_strategies, domain=None, range=Optional[Union[Union[dict, CleaningStrategy], list[Union[dict, CleaningStrategy]]]])

slots.dataset__labeling_strategies = Slot(uri=DATA_SHEETS_SCHEMA.labeling_strategies, name="dataset__labeling_strategies", curie=DATA_SHEETS_SCHEMA.curie('labeling_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__labeling_strategies, domain=None, range=Optional[Union[Union[dict, LabelingStrategy], list[Union[dict, LabelingStrategy]]]])

slots.dataset__raw_sources = Slot(uri=DATA_SHEETS_SCHEMA.raw_sources, name="dataset__raw_sources", curie=DATA_SHEETS_SCHEMA.curie('raw_sources'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__raw_sources, domain=None, range=Optional[Union[Union[dict, RawData], list[Union[dict, RawData]]]])

slots.dataset__existing_uses = Slot(uri=DATA_SHEETS_SCHEMA.existing_uses, name="dataset__existing_uses", curie=DATA_SHEETS_SCHEMA.curie('existing_uses'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__existing_uses, domain=None, range=Optional[Union[Union[dict, ExistingUse], list[Union[dict, ExistingUse]]]])

slots.dataset__use_repository = Slot(uri=DATA_SHEETS_SCHEMA.use_repository, name="dataset__use_repository", curie=DATA_SHEETS_SCHEMA.curie('use_repository'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__use_repository, domain=None, range=Optional[Union[Union[dict, UseRepository], list[Union[dict, UseRepository]]]])

slots.dataset__other_tasks = Slot(uri=DATA_SHEETS_SCHEMA.other_tasks, name="dataset__other_tasks", curie=DATA_SHEETS_SCHEMA.curie('other_tasks'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__other_tasks, domain=None, range=Optional[Union[Union[dict, OtherTask], list[Union[dict, OtherTask]]]])

slots.dataset__future_use_impacts = Slot(uri=DATA_SHEETS_SCHEMA.future_use_impacts, name="dataset__future_use_impacts", curie=DATA_SHEETS_SCHEMA.curie('future_use_impacts'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__future_use_impacts, domain=None, range=Optional[Union[Union[dict, FutureUseImpact], list[Union[dict, FutureUseImpact]]]])

slots.dataset__discouraged_uses = Slot(uri=DATA_SHEETS_SCHEMA.discouraged_uses, name="dataset__discouraged_uses", curie=DATA_SHEETS_SCHEMA.curie('discouraged_uses'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__discouraged_uses, domain=None, range=Optional[Union[Union[dict, DiscouragedUse], list[Union[dict, DiscouragedUse]]]])

slots.dataset__intended_uses = Slot(uri=DATA_SHEETS_SCHEMA.intended_uses, name="dataset__intended_uses", curie=DATA_SHEETS_SCHEMA.curie('intended_uses'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__intended_uses, domain=None, range=Optional[Union[Union[dict, IntendedUse], list[Union[dict, IntendedUse]]]])

slots.dataset__prohibited_uses = Slot(uri=DATA_SHEETS_SCHEMA.prohibited_uses, name="dataset__prohibited_uses", curie=DATA_SHEETS_SCHEMA.curie('prohibited_uses'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__prohibited_uses, domain=None, range=Optional[Union[Union[dict, ProhibitedUse], list[Union[dict, ProhibitedUse]]]])

slots.dataset__distribution_formats = Slot(uri=DATA_SHEETS_SCHEMA.distribution_formats, name="dataset__distribution_formats", curie=DATA_SHEETS_SCHEMA.curie('distribution_formats'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__distribution_formats, domain=None, range=Optional[Union[Union[dict, DistributionFormat], list[Union[dict, DistributionFormat]]]])

slots.dataset__distribution_dates = Slot(uri=DATA_SHEETS_SCHEMA.distribution_dates, name="dataset__distribution_dates", curie=DATA_SHEETS_SCHEMA.curie('distribution_dates'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__distribution_dates, domain=None, range=Optional[Union[Union[dict, DistributionDate], list[Union[dict, DistributionDate]]]])

slots.dataset__license_and_use_terms = Slot(uri=DATA_SHEETS_SCHEMA.license_and_use_terms, name="dataset__license_and_use_terms", curie=DATA_SHEETS_SCHEMA.curie('license_and_use_terms'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__license_and_use_terms, domain=None, range=Optional[Union[dict, LicenseAndUseTerms]])

slots.dataset__ip_restrictions = Slot(uri=DATA_SHEETS_SCHEMA.ip_restrictions, name="dataset__ip_restrictions", curie=DATA_SHEETS_SCHEMA.curie('ip_restrictions'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__ip_restrictions, domain=None, range=Optional[Union[dict, IPRestrictions]])

slots.dataset__regulatory_restrictions = Slot(uri=DATA_SHEETS_SCHEMA.regulatory_restrictions, name="dataset__regulatory_restrictions", curie=DATA_SHEETS_SCHEMA.curie('regulatory_restrictions'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__regulatory_restrictions, domain=None, range=Optional[Union[dict, ExportControlRegulatoryRestrictions]])

slots.dataset__maintainers = Slot(uri=DATA_SHEETS_SCHEMA.maintainers, name="dataset__maintainers", curie=DATA_SHEETS_SCHEMA.curie('maintainers'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__maintainers, domain=None, range=Optional[Union[Union[dict, Maintainer], list[Union[dict, Maintainer]]]])

slots.dataset__errata = Slot(uri=DATA_SHEETS_SCHEMA.errata, name="dataset__errata", curie=DATA_SHEETS_SCHEMA.curie('errata'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__errata, domain=None, range=Optional[Union[Union[dict, Erratum], list[Union[dict, Erratum]]]])

slots.dataset__updates = Slot(uri=DATA_SHEETS_SCHEMA.updates, name="dataset__updates", curie=DATA_SHEETS_SCHEMA.curie('updates'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__updates, domain=None, range=Optional[Union[dict, UpdatePlan]])

slots.dataset__retention_limit = Slot(uri=DATA_SHEETS_SCHEMA.retention_limit, name="dataset__retention_limit", curie=DATA_SHEETS_SCHEMA.curie('retention_limit'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__retention_limit, domain=None, range=Optional[Union[dict, RetentionLimits]])

slots.dataset__version_access = Slot(uri=DATA_SHEETS_SCHEMA.version_access, name="dataset__version_access", curie=DATA_SHEETS_SCHEMA.curie('version_access'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__version_access, domain=None, range=Optional[Union[dict, VersionAccess]])

slots.dataset__extension_mechanism = Slot(uri=DATA_SHEETS_SCHEMA.extension_mechanism, name="dataset__extension_mechanism", curie=DATA_SHEETS_SCHEMA.curie('extension_mechanism'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__extension_mechanism, domain=None, range=Optional[Union[dict, ExtensionMechanism]])

slots.dataset__variables = Slot(uri=SCHEMA.variableMeasured, name="dataset__variables", curie=SCHEMA.curie('variableMeasured'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__variables, domain=None, range=Optional[Union[Union[dict, VariableMetadata], list[Union[dict, VariableMetadata]]]])

slots.dataset__is_deidentified = Slot(uri=DATA_SHEETS_SCHEMA.is_deidentified, name="dataset__is_deidentified", curie=DATA_SHEETS_SCHEMA.curie('is_deidentified'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__is_deidentified, domain=None, range=Optional[Union[dict, Deidentification]])

slots.dataset__is_tabular = Slot(uri=DATA_SHEETS_SCHEMA.is_tabular, name="dataset__is_tabular", curie=DATA_SHEETS_SCHEMA.curie('is_tabular'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__is_tabular, domain=None, range=Optional[Union[bool, Bool]])

slots.dataset__citation = Slot(uri=SCHEMA.citation, name="dataset__citation", curie=SCHEMA.curie('citation'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__citation, domain=None, range=Optional[str])

slots.dataset__parent_datasets = Slot(uri=SCHEMA.isPartOf, name="dataset__parent_datasets", curie=SCHEMA.curie('isPartOf'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__parent_datasets, domain=None, range=Optional[Union[dict[Union[str, DatasetId], Union[dict, Dataset]], list[Union[dict, Dataset]]]])

slots.dataset__related_datasets = Slot(uri=DATA_SHEETS_SCHEMA.related_datasets, name="dataset__related_datasets", curie=DATA_SHEETS_SCHEMA.curie('related_datasets'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__related_datasets, domain=None, range=Optional[Union[Union[dict, DatasetRelationship], list[Union[dict, DatasetRelationship]]]])

slots.dataset__resources = Slot(uri=DATA_SHEETS_SCHEMA.resources, name="dataset__resources", curie=DATA_SHEETS_SCHEMA.curie('resources'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__resources, domain=None, range=Optional[Union[dict[Union[str, DatasetId], Union[dict, Dataset]], list[Union[dict, Dataset]]]])

slots.dataSubset__is_data_split = Slot(uri=DATA_SHEETS_SCHEMA.is_data_split, name="dataSubset__is_data_split", curie=DATA_SHEETS_SCHEMA.curie('is_data_split'),
                   model_uri=DATA_SHEETS_SCHEMA.dataSubset__is_data_split, domain=None, range=Optional[Union[bool, Bool]])

slots.dataSubset__is_subpopulation = Slot(uri=DATA_SHEETS_SCHEMA.is_subpopulation, name="dataSubset__is_subpopulation", curie=DATA_SHEETS_SCHEMA.curie('is_subpopulation'),
                   model_uri=DATA_SHEETS_SCHEMA.dataSubset__is_subpopulation, domain=None, range=Optional[Union[bool, Bool]])

slots.namedThing__id = Slot(uri=SCHEMA.identifier, name="namedThing__id", curie=SCHEMA.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.namedThing__id, domain=None, range=URIRef)

slots.namedThing__name = Slot(uri=SCHEMA.name, name="namedThing__name", curie=SCHEMA.curie('name'),
                   model_uri=DATA_SHEETS_SCHEMA.namedThing__name, domain=None, range=Optional[str])

slots.namedThing__description = Slot(uri=SCHEMA.description, name="namedThing__description", curie=SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.namedThing__description, domain=None, range=Optional[str])

slots.datasetProperty__id = Slot(uri=SCHEMA.identifier, name="datasetProperty__id", curie=SCHEMA.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetProperty__id, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.datasetProperty__name = Slot(uri=SCHEMA.name, name="datasetProperty__name", curie=SCHEMA.curie('name'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetProperty__name, domain=None, range=Optional[str])

slots.datasetProperty__description = Slot(uri=SCHEMA.description, name="datasetProperty__description", curie=SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetProperty__description, domain=None, range=Optional[str])

slots.datasetProperty__used_software = Slot(uri=DATA_SHEETS_SCHEMA.used_software, name="datasetProperty__used_software", curie=DATA_SHEETS_SCHEMA.curie('used_software'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetProperty__used_software, domain=None, range=Optional[Union[dict[Union[str, SoftwareId], Union[dict, Software]], list[Union[dict, Software]]]])

slots.software__version = Slot(uri=SCHEMA.softwareVersion, name="software__version", curie=SCHEMA.curie('softwareVersion'),
                   model_uri=DATA_SHEETS_SCHEMA.software__version, domain=None, range=Optional[str])

slots.software__license = Slot(uri=SCHEMA.license, name="software__license", curie=SCHEMA.curie('license'),
                   model_uri=DATA_SHEETS_SCHEMA.software__license, domain=None, range=Optional[str])

slots.software__url = Slot(uri=SCHEMA.url, name="software__url", curie=SCHEMA.curie('url'),
                   model_uri=DATA_SHEETS_SCHEMA.software__url, domain=None, range=Optional[str])

slots.person__affiliation = Slot(uri=SCHEMA.affiliation, name="person__affiliation", curie=SCHEMA.curie('affiliation'),
                   model_uri=DATA_SHEETS_SCHEMA.person__affiliation, domain=None, range=Optional[Union[Union[str, OrganizationId], list[Union[str, OrganizationId]]]])

slots.person__email = Slot(uri=SCHEMA.email, name="person__email", curie=SCHEMA.curie('email'),
                   model_uri=DATA_SHEETS_SCHEMA.person__email, domain=None, range=Optional[str])

slots.person__orcid = Slot(uri=SCHEMA.identifier, name="person__orcid", curie=SCHEMA.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.person__orcid, domain=None, range=Optional[str],
                   pattern=re.compile(r'^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$'))

slots.formatDialect__comment_prefix = Slot(uri=DATA_SHEETS_SCHEMA.comment_prefix, name="formatDialect__comment_prefix", curie=DATA_SHEETS_SCHEMA.curie('comment_prefix'),
                   model_uri=DATA_SHEETS_SCHEMA.formatDialect__comment_prefix, domain=None, range=Optional[str])

slots.formatDialect__delimiter = Slot(uri=DATA_SHEETS_SCHEMA.delimiter, name="formatDialect__delimiter", curie=DATA_SHEETS_SCHEMA.curie('delimiter'),
                   model_uri=DATA_SHEETS_SCHEMA.formatDialect__delimiter, domain=None, range=Optional[str])

slots.formatDialect__double_quote = Slot(uri=DATA_SHEETS_SCHEMA.double_quote, name="formatDialect__double_quote", curie=DATA_SHEETS_SCHEMA.curie('double_quote'),
                   model_uri=DATA_SHEETS_SCHEMA.formatDialect__double_quote, domain=None, range=Optional[str])

slots.formatDialect__header = Slot(uri=DATA_SHEETS_SCHEMA.header, name="formatDialect__header", curie=DATA_SHEETS_SCHEMA.curie('header'),
                   model_uri=DATA_SHEETS_SCHEMA.formatDialect__header, domain=None, range=Optional[str])

slots.formatDialect__quote_char = Slot(uri=DATA_SHEETS_SCHEMA.quote_char, name="formatDialect__quote_char", curie=DATA_SHEETS_SCHEMA.curie('quote_char'),
                   model_uri=DATA_SHEETS_SCHEMA.formatDialect__quote_char, domain=None, range=Optional[str])

slots.purpose__response = Slot(uri=DCTERMS.description, name="purpose__response", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.purpose__response, domain=None, range=Optional[str])

slots.task__response = Slot(uri=DCTERMS.description, name="task__response", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.task__response, domain=None, range=Optional[str])

slots.addressingGap__response = Slot(uri=DCTERMS.description, name="addressingGap__response", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.addressingGap__response, domain=None, range=Optional[str])

slots.creator__principal_investigator = Slot(uri=DCTERMS.creator, name="creator__principal_investigator", curie=DCTERMS.curie('creator'),
                   model_uri=DATA_SHEETS_SCHEMA.creator__principal_investigator, domain=None, range=Optional[Union[str, PersonId]])

slots.creator__affiliations = Slot(uri=SCHEMA.affiliation, name="creator__affiliations", curie=SCHEMA.curie('affiliation'),
                   model_uri=DATA_SHEETS_SCHEMA.creator__affiliations, domain=None, range=Optional[Union[dict[Union[str, OrganizationId], Union[dict, Organization]], list[Union[dict, Organization]]]])

slots.creator__credit_roles = Slot(uri=D4DMOTIVATION.credit_roles, name="creator__credit_roles", curie=D4DMOTIVATION.curie('credit_roles'),
                   model_uri=DATA_SHEETS_SCHEMA.creator__credit_roles, domain=None, range=Optional[Union[Union[str, "CRediTRoleEnum"], list[Union[str, "CRediTRoleEnum"]]]])

slots.fundingMechanism__grantor = Slot(uri=SCHEMA.funder, name="fundingMechanism__grantor", curie=SCHEMA.curie('funder'),
                   model_uri=DATA_SHEETS_SCHEMA.fundingMechanism__grantor, domain=None, range=Optional[Union[str, GrantorId]])

slots.fundingMechanism__grants = Slot(uri=SCHEMA.funding, name="fundingMechanism__grants", curie=SCHEMA.curie('funding'),
                   model_uri=DATA_SHEETS_SCHEMA.fundingMechanism__grants, domain=None, range=Optional[Union[dict[Union[str, GrantId], Union[dict, Grant]], list[Union[dict, Grant]]]])

slots.grant__grant_number = Slot(uri=SCHEMA.identifier, name="grant__grant_number", curie=SCHEMA.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.grant__grant_number, domain=None, range=Optional[str])

slots.instance__data_topic = Slot(uri=DCAT.theme, name="instance__data_topic", curie=DCAT.curie('theme'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__data_topic, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.instance__instance_type = Slot(uri=DCTERMS.type, name="instance__instance_type", curie=DCTERMS.curie('type'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__instance_type, domain=None, range=Optional[str])

slots.instance__data_substrate = Slot(uri=DCTERMS.format, name="instance__data_substrate", curie=DCTERMS.curie('format'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__data_substrate, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.instance__counts = Slot(uri=SCHEMA.numberOfItems, name="instance__counts", curie=SCHEMA.curie('numberOfItems'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__counts, domain=None, range=Optional[int])

slots.instance__label = Slot(uri=D4DCOMPOSITION.label, name="instance__label", curie=D4DCOMPOSITION.curie('label'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__label, domain=None, range=Optional[Union[bool, Bool]])

slots.instance__label_description = Slot(uri=SCHEMA.description, name="instance__label_description", curie=SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__label_description, domain=None, range=Optional[str])

slots.instance__sampling_strategies = Slot(uri=D4DCOMPOSITION.sampling_strategies, name="instance__sampling_strategies", curie=D4DCOMPOSITION.curie('sampling_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__sampling_strategies, domain=None, range=Optional[Union[Union[dict, SamplingStrategy], list[Union[dict, SamplingStrategy]]]])

slots.instance__missing_information = Slot(uri=D4DCOMPOSITION.missing_information, name="instance__missing_information", curie=D4DCOMPOSITION.curie('missing_information'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__missing_information, domain=None, range=Optional[Union[Union[dict, MissingInfo], list[Union[dict, MissingInfo]]]])

slots.samplingStrategy__is_sample = Slot(uri=D4DCOMPOSITION.is_sample, name="samplingStrategy__is_sample", curie=D4DCOMPOSITION.curie('is_sample'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__is_sample, domain=None, range=Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]])

slots.samplingStrategy__is_random = Slot(uri=D4DCOMPOSITION.is_random, name="samplingStrategy__is_random", curie=D4DCOMPOSITION.curie('is_random'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__is_random, domain=None, range=Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]])

slots.samplingStrategy__source_data = Slot(uri=D4DCOMPOSITION.source_data, name="samplingStrategy__source_data", curie=D4DCOMPOSITION.curie('source_data'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__source_data, domain=None, range=Optional[Union[str, list[str]]])

slots.samplingStrategy__is_representative = Slot(uri=D4DCOMPOSITION.is_representative, name="samplingStrategy__is_representative", curie=D4DCOMPOSITION.curie('is_representative'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__is_representative, domain=None, range=Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]])

slots.samplingStrategy__representative_verification = Slot(uri=D4DCOMPOSITION.representative_verification, name="samplingStrategy__representative_verification", curie=D4DCOMPOSITION.curie('representative_verification'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__representative_verification, domain=None, range=Optional[Union[str, list[str]]])

slots.samplingStrategy__why_not_representative = Slot(uri=D4DCOMPOSITION.why_not_representative, name="samplingStrategy__why_not_representative", curie=D4DCOMPOSITION.curie('why_not_representative'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__why_not_representative, domain=None, range=Optional[Union[str, list[str]]])

slots.samplingStrategy__strategies = Slot(uri=D4DCOMPOSITION.strategies, name="samplingStrategy__strategies", curie=D4DCOMPOSITION.curie('strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__strategies, domain=None, range=Optional[Union[str, list[str]]])

slots.missingInfo__missing = Slot(uri=DCTERMS.description, name="missingInfo__missing", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.missingInfo__missing, domain=None, range=Optional[Union[str, list[str]]])

slots.missingInfo__why_missing = Slot(uri=DCTERMS.description, name="missingInfo__why_missing", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.missingInfo__why_missing, domain=None, range=Optional[Union[str, list[str]]])

slots.relationships__relationship_details = Slot(uri=DCTERMS.description, name="relationships__relationship_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.relationships__relationship_details, domain=None, range=Optional[Union[str, list[str]]])

slots.splits__split_details = Slot(uri=DCTERMS.description, name="splits__split_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.splits__split_details, domain=None, range=Optional[Union[str, list[str]]])

slots.dataAnomaly__anomaly_details = Slot(uri=DCTERMS.description, name="dataAnomaly__anomaly_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.dataAnomaly__anomaly_details, domain=None, range=Optional[Union[str, list[str]]])

slots.datasetBias__bias_type = Slot(uri=D4DCOMPOSITION.bias_type, name="datasetBias__bias_type", curie=D4DCOMPOSITION.curie('bias_type'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetBias__bias_type, domain=None, range=Optional[Union[str, "BiasTypeEnum"]])

slots.datasetBias__bias_description = Slot(uri=DCTERMS.description, name="datasetBias__bias_description", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetBias__bias_description, domain=None, range=Optional[str])

slots.datasetBias__mitigation_strategy = Slot(uri=D4DCOMPOSITION.mitigation_strategy, name="datasetBias__mitigation_strategy", curie=D4DCOMPOSITION.curie('mitigation_strategy'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetBias__mitigation_strategy, domain=None, range=Optional[str])

slots.datasetBias__affected_subsets = Slot(uri=D4DCOMPOSITION.affected_subsets, name="datasetBias__affected_subsets", curie=D4DCOMPOSITION.curie('affected_subsets'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetBias__affected_subsets, domain=None, range=Optional[Union[str, list[str]]])

slots.datasetLimitation__limitation_type = Slot(uri=D4DCOMPOSITION.limitation_type, name="datasetLimitation__limitation_type", curie=D4DCOMPOSITION.curie('limitation_type'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetLimitation__limitation_type, domain=None, range=Optional[Union[str, "LimitationTypeEnum"]])

slots.datasetLimitation__limitation_description = Slot(uri=DCTERMS.description, name="datasetLimitation__limitation_description", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetLimitation__limitation_description, domain=None, range=Optional[str])

slots.datasetLimitation__scope_impact = Slot(uri=D4DCOMPOSITION.scope_impact, name="datasetLimitation__scope_impact", curie=D4DCOMPOSITION.curie('scope_impact'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetLimitation__scope_impact, domain=None, range=Optional[str])

slots.datasetLimitation__recommended_mitigation = Slot(uri=D4DCOMPOSITION.recommended_mitigation, name="datasetLimitation__recommended_mitigation", curie=D4DCOMPOSITION.curie('recommended_mitigation'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetLimitation__recommended_mitigation, domain=None, range=Optional[str])

slots.externalResource__external_resources = Slot(uri=DCTERMS.references, name="externalResource__external_resources", curie=DCTERMS.curie('references'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__external_resources, domain=None, range=Optional[Union[str, list[str]]])

slots.externalResource__future_guarantees = Slot(uri=DCTERMS.description, name="externalResource__future_guarantees", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__future_guarantees, domain=None, range=Optional[Union[str, list[str]]])

slots.externalResource__archival = Slot(uri=D4DCOMPOSITION.archival, name="externalResource__archival", curie=D4DCOMPOSITION.curie('archival'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__archival, domain=None, range=Optional[Union[Union[bool, Bool], list[Union[bool, Bool]]]])

slots.externalResource__restrictions = Slot(uri=DCTERMS.accessRights, name="externalResource__restrictions", curie=DCTERMS.curie('accessRights'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__restrictions, domain=None, range=Optional[Union[str, list[str]]])

slots.confidentiality__confidential_elements_present = Slot(uri=D4DCOMPOSITION.confidential_elements_present, name="confidentiality__confidential_elements_present", curie=D4DCOMPOSITION.curie('confidential_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.confidentiality__confidential_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.confidentiality__confidentiality_details = Slot(uri=DCTERMS.description, name="confidentiality__confidentiality_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.confidentiality__confidentiality_details, domain=None, range=Optional[Union[str, list[str]]])

slots.contentWarning__content_warnings_present = Slot(uri=D4DCOMPOSITION.content_warnings_present, name="contentWarning__content_warnings_present", curie=D4DCOMPOSITION.curie('content_warnings_present'),
                   model_uri=DATA_SHEETS_SCHEMA.contentWarning__content_warnings_present, domain=None, range=Optional[Union[bool, Bool]])

slots.contentWarning__warnings = Slot(uri=DCTERMS.description, name="contentWarning__warnings", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.contentWarning__warnings, domain=None, range=Optional[Union[str, list[str]]])

slots.subpopulation__subpopulation_elements_present = Slot(uri=D4DCOMPOSITION.subpopulation_elements_present, name="subpopulation__subpopulation_elements_present", curie=D4DCOMPOSITION.curie('subpopulation_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.subpopulation__subpopulation_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.subpopulation__identification = Slot(uri=DCTERMS.description, name="subpopulation__identification", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.subpopulation__identification, domain=None, range=Optional[Union[str, list[str]]])

slots.subpopulation__distribution = Slot(uri=DCTERMS.description, name="subpopulation__distribution", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.subpopulation__distribution, domain=None, range=Optional[Union[str, list[str]]])

slots.deidentification__identifiable_elements_present = Slot(uri=D4DCOMPOSITION.identifiable_elements_present, name="deidentification__identifiable_elements_present", curie=D4DCOMPOSITION.curie('identifiable_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.deidentification__identifiable_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.deidentification__method = Slot(uri=D4DCOMPOSITION.method, name="deidentification__method", curie=D4DCOMPOSITION.curie('method'),
                   model_uri=DATA_SHEETS_SCHEMA.deidentification__method, domain=None, range=Optional[str])

slots.deidentification__identifiers_removed = Slot(uri=D4DCOMPOSITION.identifiers_removed, name="deidentification__identifiers_removed", curie=D4DCOMPOSITION.curie('identifiers_removed'),
                   model_uri=DATA_SHEETS_SCHEMA.deidentification__identifiers_removed, domain=None, range=Optional[Union[str, list[str]]])

slots.deidentification__deidentification_details = Slot(uri=DCTERMS.description, name="deidentification__deidentification_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.deidentification__deidentification_details, domain=None, range=Optional[Union[str, list[str]]])

slots.sensitiveElement__sensitive_elements_present = Slot(uri=D4DCOMPOSITION.sensitive_elements_present, name="sensitiveElement__sensitive_elements_present", curie=D4DCOMPOSITION.curie('sensitive_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.sensitiveElement__sensitive_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.sensitiveElement__sensitivity_details = Slot(uri=DCTERMS.description, name="sensitiveElement__sensitivity_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.sensitiveElement__sensitivity_details, domain=None, range=Optional[Union[str, list[str]]])

slots.datasetRelationship__target_dataset = Slot(uri=D4DCOMPOSITION.target_dataset, name="datasetRelationship__target_dataset", curie=D4DCOMPOSITION.curie('target_dataset'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetRelationship__target_dataset, domain=None, range=str)

slots.datasetRelationship__relationship_type = Slot(uri=D4DCOMPOSITION.relationship_type, name="datasetRelationship__relationship_type", curie=D4DCOMPOSITION.curie('relationship_type'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetRelationship__relationship_type, domain=None, range=Union[str, "DatasetRelationshipTypeEnum"])

slots.datasetRelationship__description = Slot(uri=D4DCOMPOSITION.description, name="datasetRelationship__description", curie=D4DCOMPOSITION.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetRelationship__description, domain=None, range=Optional[str])

slots.instanceAcquisition__was_directly_observed = Slot(uri=DATA_SHEETS_SCHEMA['collection/was_directly_observed'], name="instanceAcquisition__was_directly_observed", curie=DATA_SHEETS_SCHEMA.curie('collection/was_directly_observed'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_directly_observed, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__was_reported_by_subjects = Slot(uri=DATA_SHEETS_SCHEMA['collection/was_reported_by_subjects'], name="instanceAcquisition__was_reported_by_subjects", curie=DATA_SHEETS_SCHEMA.curie('collection/was_reported_by_subjects'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_reported_by_subjects, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__was_inferred_derived = Slot(uri=DATA_SHEETS_SCHEMA['collection/was_inferred_derived'], name="instanceAcquisition__was_inferred_derived", curie=DATA_SHEETS_SCHEMA.curie('collection/was_inferred_derived'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_inferred_derived, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__was_validated_verified = Slot(uri=DATA_SHEETS_SCHEMA['collection/was_validated_verified'], name="instanceAcquisition__was_validated_verified", curie=DATA_SHEETS_SCHEMA.curie('collection/was_validated_verified'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_validated_verified, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__acquisition_details = Slot(uri=DCTERMS.description, name="instanceAcquisition__acquisition_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__acquisition_details, domain=None, range=Optional[Union[str, list[str]]])

slots.collectionMechanism__mechanism_details = Slot(uri=DCTERMS.description, name="collectionMechanism__mechanism_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionMechanism__mechanism_details, domain=None, range=Optional[Union[str, list[str]]])

slots.dataCollector__role = Slot(uri=DATA_SHEETS_SCHEMA['collection/role'], name="dataCollector__role", curie=DATA_SHEETS_SCHEMA.curie('collection/role'),
                   model_uri=DATA_SHEETS_SCHEMA.dataCollector__role, domain=None, range=Optional[str])

slots.dataCollector__collector_details = Slot(uri=DCTERMS.description, name="dataCollector__collector_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.dataCollector__collector_details, domain=None, range=Optional[Union[str, list[str]]])

slots.collectionTimeframe__start_date = Slot(uri=DATA_SHEETS_SCHEMA['collection/start_date'], name="collectionTimeframe__start_date", curie=DATA_SHEETS_SCHEMA.curie('collection/start_date'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionTimeframe__start_date, domain=None, range=Optional[Union[str, XSDDate]])

slots.collectionTimeframe__end_date = Slot(uri=DATA_SHEETS_SCHEMA['collection/end_date'], name="collectionTimeframe__end_date", curie=DATA_SHEETS_SCHEMA.curie('collection/end_date'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionTimeframe__end_date, domain=None, range=Optional[Union[str, XSDDate]])

slots.collectionTimeframe__timeframe_details = Slot(uri=DCTERMS.description, name="collectionTimeframe__timeframe_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionTimeframe__timeframe_details, domain=None, range=Optional[Union[str, list[str]]])

slots.directCollection__is_direct = Slot(uri=DATA_SHEETS_SCHEMA['collection/is_direct'], name="directCollection__is_direct", curie=DATA_SHEETS_SCHEMA.curie('collection/is_direct'),
                   model_uri=DATA_SHEETS_SCHEMA.directCollection__is_direct, domain=None, range=Optional[Union[bool, Bool]])

slots.directCollection__collection_details = Slot(uri=DCTERMS.description, name="directCollection__collection_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.directCollection__collection_details, domain=None, range=Optional[Union[str, list[str]]])

slots.preprocessingStrategy__preprocessing_details = Slot(uri=DCTERMS.description, name="preprocessingStrategy__preprocessing_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.preprocessingStrategy__preprocessing_details, domain=None, range=Optional[Union[str, list[str]]])

slots.cleaningStrategy__cleaning_details = Slot(uri=DCTERMS.description, name="cleaningStrategy__cleaning_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.cleaningStrategy__cleaning_details, domain=None, range=Optional[Union[str, list[str]]])

slots.labelingStrategy__annotation_platform = Slot(uri=SCHEMA.instrument, name="labelingStrategy__annotation_platform", curie=SCHEMA.curie('instrument'),
                   model_uri=DATA_SHEETS_SCHEMA.labelingStrategy__annotation_platform, domain=None, range=Optional[str])

slots.labelingStrategy__annotations_per_item = Slot(uri=D4DPREPROCESSING.annotations_per_item, name="labelingStrategy__annotations_per_item", curie=D4DPREPROCESSING.curie('annotations_per_item'),
                   model_uri=DATA_SHEETS_SCHEMA.labelingStrategy__annotations_per_item, domain=None, range=Optional[int])

slots.labelingStrategy__inter_annotator_agreement = Slot(uri=SCHEMA.measurementMethod, name="labelingStrategy__inter_annotator_agreement", curie=SCHEMA.curie('measurementMethod'),
                   model_uri=DATA_SHEETS_SCHEMA.labelingStrategy__inter_annotator_agreement, domain=None, range=Optional[str])

slots.labelingStrategy__annotator_demographics = Slot(uri=D4DPREPROCESSING.annotator_demographics, name="labelingStrategy__annotator_demographics", curie=D4DPREPROCESSING.curie('annotator_demographics'),
                   model_uri=DATA_SHEETS_SCHEMA.labelingStrategy__annotator_demographics, domain=None, range=Optional[Union[str, list[str]]])

slots.labelingStrategy__labeling_details = Slot(uri=DCTERMS.description, name="labelingStrategy__labeling_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.labelingStrategy__labeling_details, domain=None, range=Optional[Union[str, list[str]]])

slots.rawData__access_url = Slot(uri=D4DPREPROCESSING.access_url, name="rawData__access_url", curie=D4DPREPROCESSING.curie('access_url'),
                   model_uri=DATA_SHEETS_SCHEMA.rawData__access_url, domain=None, range=Optional[Union[str, URI]])

slots.rawData__raw_data_details = Slot(uri=DCTERMS.description, name="rawData__raw_data_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.rawData__raw_data_details, domain=None, range=Optional[Union[str, list[str]]])

slots.existingUse__examples = Slot(uri=D4DUSES.examples, name="existingUse__examples", curie=D4DUSES.curie('examples'),
                   model_uri=DATA_SHEETS_SCHEMA.existingUse__examples, domain=None, range=Optional[Union[str, list[str]]])

slots.useRepository__repository_url = Slot(uri=D4DUSES.repository_url, name="useRepository__repository_url", curie=D4DUSES.curie('repository_url'),
                   model_uri=DATA_SHEETS_SCHEMA.useRepository__repository_url, domain=None, range=Optional[Union[str, URI]])

slots.useRepository__repository_details = Slot(uri=DCTERMS.description, name="useRepository__repository_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.useRepository__repository_details, domain=None, range=Optional[Union[str, list[str]]])

slots.otherTask__task_details = Slot(uri=DCTERMS.description, name="otherTask__task_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.otherTask__task_details, domain=None, range=Optional[Union[str, list[str]]])

slots.futureUseImpact__impact_details = Slot(uri=DCTERMS.description, name="futureUseImpact__impact_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.futureUseImpact__impact_details, domain=None, range=Optional[Union[str, list[str]]])

slots.discouragedUse__discouragement_details = Slot(uri=DCTERMS.description, name="discouragedUse__discouragement_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.discouragedUse__discouragement_details, domain=None, range=Optional[Union[str, list[str]]])

slots.intendedUse__examples = Slot(uri=D4DUSES.examples, name="intendedUse__examples", curie=D4DUSES.curie('examples'),
                   model_uri=DATA_SHEETS_SCHEMA.intendedUse__examples, domain=None, range=Optional[Union[str, list[str]]])

slots.intendedUse__usage_notes = Slot(uri=D4DUSES.usage_notes, name="intendedUse__usage_notes", curie=D4DUSES.curie('usage_notes'),
                   model_uri=DATA_SHEETS_SCHEMA.intendedUse__usage_notes, domain=None, range=Optional[str])

slots.intendedUse__use_category = Slot(uri=D4DUSES.use_category, name="intendedUse__use_category", curie=D4DUSES.curie('use_category'),
                   model_uri=DATA_SHEETS_SCHEMA.intendedUse__use_category, domain=None, range=Optional[Union[str, list[str]]])

slots.prohibitedUse__prohibition_reason = Slot(uri=D4DUSES.prohibition_reason, name="prohibitedUse__prohibition_reason", curie=D4DUSES.curie('prohibition_reason'),
                   model_uri=DATA_SHEETS_SCHEMA.prohibitedUse__prohibition_reason, domain=None, range=Optional[Union[str, list[str]]])

slots.thirdPartySharing__is_shared = Slot(uri=DCTERMS.accessRights, name="thirdPartySharing__is_shared", curie=DCTERMS.curie('accessRights'),
                   model_uri=DATA_SHEETS_SCHEMA.thirdPartySharing__is_shared, domain=None, range=Optional[Union[bool, Bool]])

slots.distributionFormat__access_urls = Slot(uri=DCAT.accessURL, name="distributionFormat__access_urls", curie=DCAT.curie('accessURL'),
                   model_uri=DATA_SHEETS_SCHEMA.distributionFormat__access_urls, domain=None, range=Optional[Union[str, list[str]]])

slots.distributionDate__release_dates = Slot(uri=DCTERMS.available, name="distributionDate__release_dates", curie=DCTERMS.curie('available'),
                   model_uri=DATA_SHEETS_SCHEMA.distributionDate__release_dates, domain=None, range=Optional[Union[str, list[str]]])

slots.maintainer__role = Slot(uri=SCHEMA.maintainer, name="maintainer__role", curie=SCHEMA.curie('maintainer'),
                   model_uri=DATA_SHEETS_SCHEMA.maintainer__role, domain=None, range=Optional[Union[str, "CreatorOrMaintainerEnum"]])

slots.maintainer__maintainer_details = Slot(uri=DCTERMS.description, name="maintainer__maintainer_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.maintainer__maintainer_details, domain=None, range=Optional[Union[str, list[str]]])

slots.erratum__erratum_url = Slot(uri=D4DMAINTENANCE.erratum_url, name="erratum__erratum_url", curie=D4DMAINTENANCE.curie('erratum_url'),
                   model_uri=DATA_SHEETS_SCHEMA.erratum__erratum_url, domain=None, range=Optional[Union[str, URI]])

slots.erratum__erratum_details = Slot(uri=DCTERMS.description, name="erratum__erratum_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.erratum__erratum_details, domain=None, range=Optional[Union[str, list[str]]])

slots.updatePlan__frequency = Slot(uri=D4DMAINTENANCE.frequency, name="updatePlan__frequency", curie=D4DMAINTENANCE.curie('frequency'),
                   model_uri=DATA_SHEETS_SCHEMA.updatePlan__frequency, domain=None, range=Optional[str])

slots.updatePlan__update_details = Slot(uri=DCTERMS.description, name="updatePlan__update_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.updatePlan__update_details, domain=None, range=Optional[Union[str, list[str]]])

slots.retentionLimits__retention_period = Slot(uri=D4DMAINTENANCE.retention_period, name="retentionLimits__retention_period", curie=D4DMAINTENANCE.curie('retention_period'),
                   model_uri=DATA_SHEETS_SCHEMA.retentionLimits__retention_period, domain=None, range=Optional[str])

slots.retentionLimits__retention_details = Slot(uri=DCTERMS.description, name="retentionLimits__retention_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.retentionLimits__retention_details, domain=None, range=Optional[Union[str, list[str]]])

slots.versionAccess__latest_version_doi = Slot(uri=D4DMAINTENANCE.latest_version_doi, name="versionAccess__latest_version_doi", curie=D4DMAINTENANCE.curie('latest_version_doi'),
                   model_uri=DATA_SHEETS_SCHEMA.versionAccess__latest_version_doi, domain=None, range=Optional[str])

slots.versionAccess__versions_available = Slot(uri=D4DMAINTENANCE.versions_available, name="versionAccess__versions_available", curie=D4DMAINTENANCE.curie('versions_available'),
                   model_uri=DATA_SHEETS_SCHEMA.versionAccess__versions_available, domain=None, range=Optional[Union[str, list[str]]])

slots.versionAccess__version_details = Slot(uri=DCTERMS.description, name="versionAccess__version_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.versionAccess__version_details, domain=None, range=Optional[Union[str, list[str]]])

slots.extensionMechanism__contribution_url = Slot(uri=D4DMAINTENANCE.contribution_url, name="extensionMechanism__contribution_url", curie=D4DMAINTENANCE.curie('contribution_url'),
                   model_uri=DATA_SHEETS_SCHEMA.extensionMechanism__contribution_url, domain=None, range=Optional[Union[str, URI]])

slots.extensionMechanism__extension_details = Slot(uri=DCTERMS.description, name="extensionMechanism__extension_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.extensionMechanism__extension_details, domain=None, range=Optional[Union[str, list[str]]])

slots.ethicalReview__contact_person = Slot(uri=SCHEMA.contactPoint, name="ethicalReview__contact_person", curie=SCHEMA.curie('contactPoint'),
                   model_uri=DATA_SHEETS_SCHEMA.ethicalReview__contact_person, domain=None, range=Optional[Union[str, PersonId]])

slots.ethicalReview__reviewing_organization = Slot(uri=SCHEMA.provider, name="ethicalReview__reviewing_organization", curie=SCHEMA.curie('provider'),
                   model_uri=DATA_SHEETS_SCHEMA.ethicalReview__reviewing_organization, domain=None, range=Optional[Union[str, OrganizationId]])

slots.ethicalReview__review_details = Slot(uri=DCTERMS.description, name="ethicalReview__review_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.ethicalReview__review_details, domain=None, range=Optional[Union[str, list[str]]])

slots.dataProtectionImpact__impact_details = Slot(uri=DCTERMS.description, name="dataProtectionImpact__impact_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.dataProtectionImpact__impact_details, domain=None, range=Optional[Union[str, list[str]]])

slots.collectionNotification__notification_details = Slot(uri=DCTERMS.description, name="collectionNotification__notification_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionNotification__notification_details, domain=None, range=Optional[Union[str, list[str]]])

slots.collectionConsent__consent_details = Slot(uri=DCTERMS.description, name="collectionConsent__consent_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionConsent__consent_details, domain=None, range=Optional[Union[str, list[str]]])

slots.consentRevocation__revocation_details = Slot(uri=DCTERMS.description, name="consentRevocation__revocation_details", curie=DCTERMS.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.consentRevocation__revocation_details, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectResearch__involves_human_subjects = Slot(uri=D4DHUMAN.involves_human_subjects, name="humanSubjectResearch__involves_human_subjects", curie=D4DHUMAN.curie('involves_human_subjects'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectResearch__involves_human_subjects, domain=None, range=Optional[Union[bool, Bool]])

slots.humanSubjectResearch__irb_approval = Slot(uri=D4DHUMAN.irb_approval, name="humanSubjectResearch__irb_approval", curie=D4DHUMAN.curie('irb_approval'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectResearch__irb_approval, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectResearch__ethics_review_board = Slot(uri=D4DHUMAN.ethics_review_board, name="humanSubjectResearch__ethics_review_board", curie=D4DHUMAN.curie('ethics_review_board'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectResearch__ethics_review_board, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectResearch__special_populations = Slot(uri=D4DHUMAN.special_populations, name="humanSubjectResearch__special_populations", curie=D4DHUMAN.curie('special_populations'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectResearch__special_populations, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectResearch__regulatory_compliance = Slot(uri=D4DHUMAN.regulatory_compliance, name="humanSubjectResearch__regulatory_compliance", curie=D4DHUMAN.curie('regulatory_compliance'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectResearch__regulatory_compliance, domain=None, range=Optional[Union[str, list[str]]])

slots.informedConsent__consent_obtained = Slot(uri=D4DHUMAN.consent_obtained, name="informedConsent__consent_obtained", curie=D4DHUMAN.curie('consent_obtained'),
                   model_uri=DATA_SHEETS_SCHEMA.informedConsent__consent_obtained, domain=None, range=Optional[Union[bool, Bool]])

slots.informedConsent__consent_type = Slot(uri=D4DHUMAN.consent_type, name="informedConsent__consent_type", curie=D4DHUMAN.curie('consent_type'),
                   model_uri=DATA_SHEETS_SCHEMA.informedConsent__consent_type, domain=None, range=Optional[Union[str, list[str]]])

slots.informedConsent__consent_documentation = Slot(uri=D4DHUMAN.consent_documentation, name="informedConsent__consent_documentation", curie=D4DHUMAN.curie('consent_documentation'),
                   model_uri=DATA_SHEETS_SCHEMA.informedConsent__consent_documentation, domain=None, range=Optional[Union[str, list[str]]])

slots.informedConsent__withdrawal_mechanism = Slot(uri=D4DHUMAN.withdrawal_mechanism, name="informedConsent__withdrawal_mechanism", curie=D4DHUMAN.curie('withdrawal_mechanism'),
                   model_uri=DATA_SHEETS_SCHEMA.informedConsent__withdrawal_mechanism, domain=None, range=Optional[Union[str, list[str]]])

slots.informedConsent__consent_scope = Slot(uri=D4DHUMAN.consent_scope, name="informedConsent__consent_scope", curie=D4DHUMAN.curie('consent_scope'),
                   model_uri=DATA_SHEETS_SCHEMA.informedConsent__consent_scope, domain=None, range=Optional[Union[str, list[str]]])

slots.participantPrivacy__anonymization_method = Slot(uri=D4DHUMAN.anonymization_method, name="participantPrivacy__anonymization_method", curie=D4DHUMAN.curie('anonymization_method'),
                   model_uri=DATA_SHEETS_SCHEMA.participantPrivacy__anonymization_method, domain=None, range=Optional[Union[str, list[str]]])

slots.participantPrivacy__reidentification_risk = Slot(uri=D4DHUMAN.reidentification_risk, name="participantPrivacy__reidentification_risk", curie=D4DHUMAN.curie('reidentification_risk'),
                   model_uri=DATA_SHEETS_SCHEMA.participantPrivacy__reidentification_risk, domain=None, range=Optional[Union[str, list[str]]])

slots.participantPrivacy__privacy_techniques = Slot(uri=D4DHUMAN.privacy_techniques, name="participantPrivacy__privacy_techniques", curie=D4DHUMAN.curie('privacy_techniques'),
                   model_uri=DATA_SHEETS_SCHEMA.participantPrivacy__privacy_techniques, domain=None, range=Optional[Union[str, list[str]]])

slots.participantPrivacy__data_linkage = Slot(uri=D4DHUMAN.data_linkage, name="participantPrivacy__data_linkage", curie=D4DHUMAN.curie('data_linkage'),
                   model_uri=DATA_SHEETS_SCHEMA.participantPrivacy__data_linkage, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectCompensation__compensation_provided = Slot(uri=D4DHUMAN.compensation_provided, name="humanSubjectCompensation__compensation_provided", curie=D4DHUMAN.curie('compensation_provided'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectCompensation__compensation_provided, domain=None, range=Optional[Union[bool, Bool]])

slots.humanSubjectCompensation__compensation_type = Slot(uri=D4DHUMAN.compensation_type, name="humanSubjectCompensation__compensation_type", curie=D4DHUMAN.curie('compensation_type'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectCompensation__compensation_type, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectCompensation__compensation_amount = Slot(uri=D4DHUMAN.compensation_amount, name="humanSubjectCompensation__compensation_amount", curie=D4DHUMAN.curie('compensation_amount'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectCompensation__compensation_amount, domain=None, range=Optional[Union[str, list[str]]])

slots.humanSubjectCompensation__compensation_rationale = Slot(uri=D4DHUMAN.compensation_rationale, name="humanSubjectCompensation__compensation_rationale", curie=D4DHUMAN.curie('compensation_rationale'),
                   model_uri=DATA_SHEETS_SCHEMA.humanSubjectCompensation__compensation_rationale, domain=None, range=Optional[Union[str, list[str]]])

slots.vulnerablePopulations__vulnerable_groups_included = Slot(uri=D4DHUMAN.vulnerable_groups_included, name="vulnerablePopulations__vulnerable_groups_included", curie=D4DHUMAN.curie('vulnerable_groups_included'),
                   model_uri=DATA_SHEETS_SCHEMA.vulnerablePopulations__vulnerable_groups_included, domain=None, range=Optional[Union[bool, Bool]])

slots.vulnerablePopulations__special_protections = Slot(uri=D4DHUMAN.special_protections, name="vulnerablePopulations__special_protections", curie=D4DHUMAN.curie('special_protections'),
                   model_uri=DATA_SHEETS_SCHEMA.vulnerablePopulations__special_protections, domain=None, range=Optional[Union[str, list[str]]])

slots.vulnerablePopulations__assent_procedures = Slot(uri=D4DHUMAN.assent_procedures, name="vulnerablePopulations__assent_procedures", curie=D4DHUMAN.curie('assent_procedures'),
                   model_uri=DATA_SHEETS_SCHEMA.vulnerablePopulations__assent_procedures, domain=None, range=Optional[Union[str, list[str]]])

slots.vulnerablePopulations__guardian_consent = Slot(uri=D4DHUMAN.guardian_consent, name="vulnerablePopulations__guardian_consent", curie=D4DHUMAN.curie('guardian_consent'),
                   model_uri=DATA_SHEETS_SCHEMA.vulnerablePopulations__guardian_consent, domain=None, range=Optional[Union[str, list[str]]])

slots.licenseAndUseTerms__license_terms = Slot(uri=DCTERMS.license, name="licenseAndUseTerms__license_terms", curie=DCTERMS.curie('license'),
                   model_uri=DATA_SHEETS_SCHEMA.licenseAndUseTerms__license_terms, domain=None, range=Optional[Union[str, list[str]]])

slots.licenseAndUseTerms__data_use_permission = Slot(uri=DUO['0000001'], name="licenseAndUseTerms__data_use_permission", curie=DUO.curie('0000001'),
                   model_uri=DATA_SHEETS_SCHEMA.licenseAndUseTerms__data_use_permission, domain=None, range=Optional[Union[Union[str, "DataUsePermissionEnum"], list[Union[str, "DataUsePermissionEnum"]]]])

slots.licenseAndUseTerms__contact_person = Slot(uri=SCHEMA.contactPoint, name="licenseAndUseTerms__contact_person", curie=SCHEMA.curie('contactPoint'),
                   model_uri=DATA_SHEETS_SCHEMA.licenseAndUseTerms__contact_person, domain=None, range=Optional[Union[str, PersonId]])

slots.iPRestrictions__restrictions = Slot(uri=DCTERMS.rights, name="iPRestrictions__restrictions", curie=DCTERMS.curie('rights'),
                   model_uri=DATA_SHEETS_SCHEMA.iPRestrictions__restrictions, domain=None, range=Optional[Union[str, list[str]]])

slots.exportControlRegulatoryRestrictions__regulatory_restrictions = Slot(uri=DCTERMS.accessRights, name="exportControlRegulatoryRestrictions__regulatory_restrictions", curie=DCTERMS.curie('accessRights'),
                   model_uri=DATA_SHEETS_SCHEMA.exportControlRegulatoryRestrictions__regulatory_restrictions, domain=None, range=Optional[Union[str, list[str]]])

slots.exportControlRegulatoryRestrictions__hipaa_compliant = Slot(uri=D4DDATAGOVERNANCE.hipaa_compliant, name="exportControlRegulatoryRestrictions__hipaa_compliant", curie=D4DDATAGOVERNANCE.curie('hipaa_compliant'),
                   model_uri=DATA_SHEETS_SCHEMA.exportControlRegulatoryRestrictions__hipaa_compliant, domain=None, range=Optional[Union[str, "ComplianceStatusEnum"]])

slots.exportControlRegulatoryRestrictions__other_compliance = Slot(uri=D4DDATAGOVERNANCE.other_compliance, name="exportControlRegulatoryRestrictions__other_compliance", curie=D4DDATAGOVERNANCE.curie('other_compliance'),
                   model_uri=DATA_SHEETS_SCHEMA.exportControlRegulatoryRestrictions__other_compliance, domain=None, range=Optional[Union[str, list[str]]])

slots.exportControlRegulatoryRestrictions__confidentiality_level = Slot(uri=D4DDATAGOVERNANCE.confidentiality_level, name="exportControlRegulatoryRestrictions__confidentiality_level", curie=D4DDATAGOVERNANCE.curie('confidentiality_level'),
                   model_uri=DATA_SHEETS_SCHEMA.exportControlRegulatoryRestrictions__confidentiality_level, domain=None, range=Optional[Union[str, "ConfidentialityLevelEnum"]])

slots.exportControlRegulatoryRestrictions__governance_committee_contact = Slot(uri=SCHEMA.contactPoint, name="exportControlRegulatoryRestrictions__governance_committee_contact", curie=SCHEMA.curie('contactPoint'),
                   model_uri=DATA_SHEETS_SCHEMA.exportControlRegulatoryRestrictions__governance_committee_contact, domain=None, range=Optional[Union[str, PersonId]])

slots.variableMetadata__variable_name = Slot(uri=SCHEMA.name, name="variableMetadata__variable_name", curie=SCHEMA.curie('name'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__variable_name, domain=None, range=str)

slots.variableMetadata__data_type = Slot(uri=SCHEMA.DataType, name="variableMetadata__data_type", curie=SCHEMA.curie('DataType'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__data_type, domain=None, range=Optional[Union[str, "VariableTypeEnum"]])

slots.variableMetadata__unit = Slot(uri=QUDT.unit, name="variableMetadata__unit", curie=QUDT.curie('unit'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__unit, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.variableMetadata__missing_value_code = Slot(uri=D4DVARIABLES.missing_value_code, name="variableMetadata__missing_value_code", curie=D4DVARIABLES.curie('missing_value_code'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__missing_value_code, domain=None, range=Optional[Union[str, list[str]]])

slots.variableMetadata__minimum_value = Slot(uri=SCHEMA.minValue, name="variableMetadata__minimum_value", curie=SCHEMA.curie('minValue'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__minimum_value, domain=None, range=Optional[float])

slots.variableMetadata__maximum_value = Slot(uri=SCHEMA.maxValue, name="variableMetadata__maximum_value", curie=SCHEMA.curie('maxValue'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__maximum_value, domain=None, range=Optional[float])

slots.variableMetadata__categories = Slot(uri=SCHEMA.valueReference, name="variableMetadata__categories", curie=SCHEMA.curie('valueReference'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__categories, domain=None, range=Optional[Union[str, list[str]]])

slots.variableMetadata__examples = Slot(uri=SKOS.example, name="variableMetadata__examples", curie=SKOS.curie('example'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__examples, domain=None, range=Optional[Union[str, list[str]]])

slots.variableMetadata__is_identifier = Slot(uri=SCHEMA.identifier, name="variableMetadata__is_identifier", curie=SCHEMA.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__is_identifier, domain=None, range=Optional[Union[bool, Bool]])

slots.variableMetadata__is_sensitive = Slot(uri=D4DVARIABLES.is_sensitive, name="variableMetadata__is_sensitive", curie=D4DVARIABLES.curie('is_sensitive'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__is_sensitive, domain=None, range=Optional[Union[bool, Bool]])

slots.variableMetadata__precision = Slot(uri=D4DVARIABLES.precision, name="variableMetadata__precision", curie=D4DVARIABLES.curie('precision'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__precision, domain=None, range=Optional[int])

slots.variableMetadata__measurement_technique = Slot(uri=SCHEMA.measurementTechnique, name="variableMetadata__measurement_technique", curie=SCHEMA.curie('measurementTechnique'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__measurement_technique, domain=None, range=Optional[str])

slots.variableMetadata__derivation = Slot(uri=D4DVARIABLES.derivation, name="variableMetadata__derivation", curie=D4DVARIABLES.curie('derivation'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__derivation, domain=None, range=Optional[str])

slots.variableMetadata__quality_notes = Slot(uri=D4DVARIABLES.quality_notes, name="variableMetadata__quality_notes", curie=D4DVARIABLES.curie('quality_notes'),
                   model_uri=DATA_SHEETS_SCHEMA.variableMetadata__quality_notes, domain=None, range=Optional[Union[str, list[str]]])
