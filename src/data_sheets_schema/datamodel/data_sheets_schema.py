# Auto generated from data_sheets_schema.yaml by pythongen.py version: 0.0.1
# Generation date: 2024-10-21T12:19:38
# Schema: data-sheets-schema
#
# id: https://w3id.org/bridge2ai/data-sheets-schema
# description: A LinkML schema for Datasheets for Datasets.
# license: MIT

import dataclasses
import re
from jsonasobj2 import JsonObj, as_dict
from typing import Optional, List, Union, Dict, ClassVar, Any
from dataclasses import dataclass
from linkml_runtime.linkml_model.meta import EnumDefinition, PermissibleValue, PvFormulaOptions

from linkml_runtime.utils.slot import Slot
from linkml_runtime.utils.metamodelcore import empty_list, empty_dict, bnode
from linkml_runtime.utils.yamlutils import YAMLRoot, extended_str, extended_float, extended_int
from linkml_runtime.utils.dataclass_extensions_376 import dataclasses_init_fn_with_kwargs
from linkml_runtime.utils.formatutils import camelcase, underscore, sfx
from linkml_runtime.utils.enumerations import EnumDefinitionImpl
from rdflib import Namespace, URIRef
from linkml_runtime.utils.curienamespace import CurieNamespace
from linkml_runtime.linkml_model.types import Boolean, Date, Datetime, Integer, String, Uri, Uriorcurie
from linkml_runtime.utils.metamodelcore import Bool, URI, URIorCURIE, XSDDate, XSDDateTime

metamodel_version = "1.7.0"
version = None

# Overwrite dataclasses _init_fn to add **kwargs in __init__
dataclasses._init_fn = dataclasses_init_fn_with_kwargs

# Namespaces
B2AI = CurieNamespace('B2AI', 'https://w3id.org/bridge2ai/standards-schema/')
B2AI_ORG = CurieNamespace('B2AI_ORG', 'https://w3id.org/bridge2ai/standards-organization-schema/')
B2AI_STANDARD = CurieNamespace('B2AI_STANDARD', 'https://w3id.org/bridge2ai/b2ai-standards-registry/')
B2AI_SUBSTRATE = CurieNamespace('B2AI_SUBSTRATE', 'https://w3id.org/bridge2ai/b2ai-standards-registry/')
B2AI_TOPIC = CurieNamespace('B2AI_TOPIC', 'https://w3id.org/bridge2ai/b2ai-standards-registry/')
MESH = CurieNamespace('MESH', 'http://id.nlm.nih.gov/mesh/')
BIBO = CurieNamespace('bibo', 'http://example.org/UNKNOWN/bibo/')
BIOLINK = CurieNamespace('biolink', 'https://w3id.org/biolink/vocab/')
CSVW = CurieNamespace('csvw', 'http://www.w3.org/ns/csvw#')
DATA_SHEETS_SCHEMA = CurieNamespace('data_sheets_schema', 'https://w3id.org/bridge2ai/data-sheets-schema/')
DATASETS = CurieNamespace('datasets', 'https://w3id.org/linkml/report')
DCAT = CurieNamespace('dcat', 'http://www.w3.org/ns/dcat#')
DCTERMS = CurieNamespace('dcterms', 'http://example.org/UNKNOWN/dcterms/')
EXAMPLE = CurieNamespace('example', 'https://example.org/')
FORMATS = CurieNamespace('formats', 'http://www.w3.org/ns/formats/')
FRICTIONLESS = CurieNamespace('frictionless', 'https://specs.frictionlessdata.io/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
MEDIATYPES = CurieNamespace('mediatypes', 'https://www.iana.org/assignments/media-types/')
NCIT = CurieNamespace('ncit', 'http://purl.obolibrary.org/obo/NCIT_')
OSLC = CurieNamespace('oslc', 'http://example.org/UNKNOWN/oslc/')
PAV = CurieNamespace('pav', 'http://purl.org/pav/')
PROV = CurieNamespace('prov', 'http://example.org/UNKNOWN/prov/')
RDFS = CurieNamespace('rdfs', 'http://www.w3.org/2000/01/rdf-schema#')
SCHEMA = CurieNamespace('schema', 'http://schema.org/')
SH = CurieNamespace('sh', 'https://w3id.org/shacl/')
SKOS = CurieNamespace('skos', 'http://www.w3.org/2004/02/skos/core#')
UBERON = CurieNamespace('uberon', 'http://purl.obolibrary.org/obo/uberon/core#')
VOID = CurieNamespace('void', 'http://rdfs.org/ns/void#')
WIKIDATA = CurieNamespace('wikidata', 'http://www.wikidata.org/wiki/')
XSD = CurieNamespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
DEFAULT_ = DATA_SHEETS_SCHEMA


# Types
class CategoryType(Uriorcurie):
    """ A primitive type in which the value denotes a class within the model. """
    type_class_uri = XSD["anyURI"]
    type_class_curie = "xsd:anyURI"
    type_name = "category_type"
    type_model_uri = DATA_SHEETS_SCHEMA.CategoryType


class EdamIdentifier(Uriorcurie):
    """ Identifier from EDAM ontology """
    type_class_uri = XSD["anyURI"]
    type_class_curie = "xsd:anyURI"
    type_name = "edam_identifier"
    type_model_uri = DATA_SHEETS_SCHEMA.EdamIdentifier


class MeshIdentifier(Uriorcurie):
    """ Identifier from Medical Subject Headings (MeSH) biomedical vocabulary. """
    type_class_uri = XSD["anyURI"]
    type_class_curie = "xsd:anyURI"
    type_name = "mesh_identifier"
    type_model_uri = DATA_SHEETS_SCHEMA.MeshIdentifier


class NcitIdentifier(Uriorcurie):
    """ Identifier from NCIT reference terminology with broad coverage of the cancer domain. """
    type_class_uri = XSD["anyURI"]
    type_class_curie = "xsd:anyURI"
    type_name = "ncit_identifier"
    type_model_uri = DATA_SHEETS_SCHEMA.NcitIdentifier


class RorIdentifier(Uriorcurie):
    """ Identifier from Research Organization Registry. """
    type_class_uri = XSD["anyURI"]
    type_class_curie = "xsd:anyURI"
    type_name = "ror_identifier"
    type_model_uri = DATA_SHEETS_SCHEMA.RorIdentifier


class WikidataIdentifier(Uriorcurie):
    """ Identifier from Wikidata open knowledge base. """
    type_class_uri = XSD["anyURI"]
    type_class_curie = "xsd:anyURI"
    type_name = "wikidata_identifier"
    type_model_uri = DATA_SHEETS_SCHEMA.WikidataIdentifier


# Class references
class InformationId(URIorCURIE):
    pass


class FormatDialectId(URIorCURIE):
    pass


class DatasetCollectionId(InformationId):
    pass


class DatasetId(InformationId):
    pass


class DataSubsetId(DatasetId):
    pass


class NamedThingId(URIorCURIE):
    pass


class PersonId(NamedThingId):
    pass


class DatasetPropertyId(NamedThingId):
    pass


class SoftwareId(NamedThingId):
    pass


class PurposeId(DatasetPropertyId):
    pass


class TaskId(DatasetPropertyId):
    pass


class AddressingGapId(DatasetPropertyId):
    pass


class CreatorId(DatasetPropertyId):
    pass


class FundingMechanismId(DatasetPropertyId):
    pass


class GrantId(NamedThingId):
    pass


class InstanceId(DatasetPropertyId):
    pass


class SamplingStrategyId(DatasetPropertyId):
    pass


class MissingInfoId(DatasetPropertyId):
    pass


class RelationshipsId(DatasetPropertyId):
    pass


class SplitsId(DatasetPropertyId):
    pass


class DataAnomalyId(DatasetPropertyId):
    pass


class ExternalResourceId(DatasetPropertyId):
    pass


class ConfidentialityId(DatasetPropertyId):
    pass


class ContentWarningId(DatasetPropertyId):
    pass


class SubpopulationId(DatasetPropertyId):
    pass


class DeidentificationId(DatasetPropertyId):
    pass


class SensitiveElementId(DatasetPropertyId):
    pass


class InstanceAcquisitionId(DatasetPropertyId):
    pass


class CollectionMechanismId(DatasetPropertyId):
    pass


class DataCollectorId(DatasetPropertyId):
    pass


class CollectionTimeframeId(DatasetPropertyId):
    pass


class EthicalReviewId(DatasetPropertyId):
    pass


class DirectCollectionId(DatasetPropertyId):
    pass


class CollectionNotificationId(DatasetPropertyId):
    pass


class CollectionConsentId(DatasetPropertyId):
    pass


class ConsentRevocationId(DatasetPropertyId):
    pass


class DataProtectionImpactId(DatasetPropertyId):
    pass


class PreprocessingStrategyId(DatasetPropertyId):
    pass


class CleaningStrategyId(DatasetPropertyId):
    pass


class LabelingStrategyId(DatasetPropertyId):
    pass


class RawDataId(DatasetPropertyId):
    pass


class ExistingUseId(DatasetPropertyId):
    pass


class UseRepositoryId(DatasetPropertyId):
    pass


class OtherTaskId(DatasetPropertyId):
    pass


class FutureUseImpactId(DatasetPropertyId):
    pass


class DiscouragedUseId(DatasetPropertyId):
    pass


class ThirdPartySharingId(DatasetPropertyId):
    pass


class DistributionFormatId(DatasetPropertyId):
    pass


class DistributionDateId(DatasetPropertyId):
    pass


class LicenseAndUseTermsId(DatasetPropertyId):
    pass


class IPRestrictionsId(DatasetPropertyId):
    pass


class ExportControlRegulatoryRestrictionsId(DatasetPropertyId):
    pass


class MaintainerId(DatasetPropertyId):
    pass


class ErratumId(DatasetPropertyId):
    pass


class UpdatePlanId(DatasetPropertyId):
    pass


class RetentionLimitsId(DatasetPropertyId):
    pass


class VersionAccessId(DatasetPropertyId):
    pass


class ExtensionMechanismId(DatasetPropertyId):
    pass


class AnatomicalEntityId(NamedThingId):
    pass


class OrganizationId(NamedThingId):
    pass


class GrantorId(OrganizationId):
    pass


@dataclass
class Information(YAMLRoot):
    """
    Grouping for datasets and data files
    """
    _inherited_slots: ClassVar[List[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Information"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Information"
    class_name: ClassVar[str] = "Information"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Information

    id: Union[str, InformationId] = None
    compression: Optional[Union[str, "CompressionEnum"]] = None
    conforms_to: Optional[Union[str, URIorCURIE]] = None
    conforms_to_class: Optional[Union[str, URIorCURIE]] = None
    conforms_to_schema: Optional[Union[str, URIorCURIE]] = None
    created_by: Optional[Union[Union[str, "CreatorOrMaintainerEnum"], List[Union[str, "CreatorOrMaintainerEnum"]]]] = empty_list()
    created_on: Optional[Union[str, XSDDateTime]] = None
    description: Optional[str] = None
    doi: Optional[Union[str, URIorCURIE]] = None
    download_url: Optional[Union[str, URI]] = None
    issued: Optional[Union[str, XSDDateTime]] = None
    keywords: Optional[Union[str, List[str]]] = empty_list()
    language: Optional[str] = None
    last_updated_on: Optional[Union[str, XSDDateTime]] = None
    license: Optional[str] = None
    modified_by: Optional[Union[str, "CreatorOrMaintainerEnum"]] = None
    page: Optional[str] = None
    publisher: Optional[Union[str, URIorCURIE]] = None
    status: Optional[Union[str, URIorCURIE]] = None
    title: Optional[str] = None
    version: Optional[str] = None
    was_derived_from: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InformationId):
            self.id = InformationId(self.id)

        if self.compression is not None and not isinstance(self.compression, CompressionEnum):
            self.compression = CompressionEnum(self.compression)

        if self.conforms_to is not None and not isinstance(self.conforms_to, URIorCURIE):
            self.conforms_to = URIorCURIE(self.conforms_to)

        if self.conforms_to_class is not None and not isinstance(self.conforms_to_class, URIorCURIE):
            self.conforms_to_class = URIorCURIE(self.conforms_to_class)

        if self.conforms_to_schema is not None and not isinstance(self.conforms_to_schema, URIorCURIE):
            self.conforms_to_schema = URIorCURIE(self.conforms_to_schema)

        if not isinstance(self.created_by, list):
            self.created_by = [self.created_by] if self.created_by is not None else []
        self.created_by = [v if isinstance(v, CreatorOrMaintainerEnum) else CreatorOrMaintainerEnum(v) for v in self.created_by]

        if self.created_on is not None and not isinstance(self.created_on, XSDDateTime):
            self.created_on = XSDDateTime(self.created_on)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.doi is not None and not isinstance(self.doi, URIorCURIE):
            self.doi = URIorCURIE(self.doi)

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

        if self.modified_by is not None and not isinstance(self.modified_by, CreatorOrMaintainerEnum):
            self.modified_by = CreatorOrMaintainerEnum(self.modified_by)

        if self.page is not None and not isinstance(self.page, str):
            self.page = str(self.page)

        if self.publisher is not None and not isinstance(self.publisher, URIorCURIE):
            self.publisher = URIorCURIE(self.publisher)

        if self.status is not None and not isinstance(self.status, URIorCURIE):
            self.status = URIorCURIE(self.status)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.was_derived_from is not None and not isinstance(self.was_derived_from, str):
            self.was_derived_from = str(self.was_derived_from)

        super().__post_init__(**kwargs)


@dataclass
class FormatDialect(YAMLRoot):
    """
    Additional format information for a file
    """
    _inherited_slots: ClassVar[List[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["FormatDialect"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:FormatDialect"
    class_name: ClassVar[str] = "FormatDialect"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.FormatDialect

    id: Union[str, FormatDialectId] = None
    comment_prefix: Optional[str] = None
    delimiter: Optional[str] = None
    double_quote: Optional[str] = None
    header: Optional[str] = None
    quote_char: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, FormatDialectId):
            self.id = FormatDialectId(self.id)

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


@dataclass
class DatasetCollection(Information):
    """
    A collection of related datasets, likely containing multiple files of multiple potential purposes and properties.
    """
    _inherited_slots: ClassVar[List[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DatasetCollection"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DatasetCollection"
    class_name: ClassVar[str] = "DatasetCollection"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetCollection

    id: Union[str, DatasetCollectionId] = None
    resources: Optional[Union[Union[str, DatasetId], List[Union[str, DatasetId]]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetCollectionId):
            self.id = DatasetCollectionId(self.id)

        if not isinstance(self.resources, list):
            self.resources = [self.resources] if self.resources is not None else []
        self.resources = [v if isinstance(v, DatasetId) else DatasetId(v) for v in self.resources]

        super().__post_init__(**kwargs)


@dataclass
class Dataset(Information):
    """
    A single component of related observations and/or information that can be read, manipulated, transformed, and
    otherwise interpreted.
    """
    _inherited_slots: ClassVar[List[str]] = []

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
    media_type: Optional[str] = None
    path: Optional[str] = None
    sha256: Optional[str] = None
    purposes: Optional[Union[Union[str, PurposeId], List[Union[str, PurposeId]]]] = empty_list()
    tasks: Optional[Union[Union[str, TaskId], List[Union[str, TaskId]]]] = empty_list()
    addressing_gaps: Optional[Union[Union[str, AddressingGapId], List[Union[str, AddressingGapId]]]] = empty_list()
    creators: Optional[Union[Union[str, CreatorId], List[Union[str, CreatorId]]]] = empty_list()
    funders: Optional[Union[Union[str, FundingMechanismId], List[Union[str, FundingMechanismId]]]] = empty_list()
    subsets: Optional[Union[Union[str, DataSubsetId], List[Union[str, DataSubsetId]]]] = empty_list()
    instances: Optional[Union[Union[str, InstanceId], List[Union[str, InstanceId]]]] = empty_list()
    anomalies: Optional[Union[Union[str, DataAnomalyId], List[Union[str, DataAnomalyId]]]] = empty_list()
    external_resources: Optional[Union[Union[str, ExternalResourceId], List[Union[str, ExternalResourceId]]]] = empty_list()
    confidential_elements: Optional[Union[Union[str, ConfidentialityId], List[Union[str, ConfidentialityId]]]] = empty_list()
    content_warnings: Optional[Union[Union[str, ContentWarningId], List[Union[str, ContentWarningId]]]] = empty_list()
    subpopulations: Optional[Union[Union[str, SubpopulationId], List[Union[str, SubpopulationId]]]] = empty_list()
    sensitive_elements: Optional[Union[Union[str, SensitiveElementId], List[Union[str, SensitiveElementId]]]] = empty_list()
    acquisition_methods: Optional[Union[Union[str, InstanceAcquisitionId], List[Union[str, InstanceAcquisitionId]]]] = empty_list()
    collection_mechanisms: Optional[Union[Union[str, CollectionMechanismId], List[Union[str, CollectionMechanismId]]]] = empty_list()
    sampling_strategies: Optional[Union[Union[str, SamplingStrategyId], List[Union[str, SamplingStrategyId]]]] = empty_list()
    data_collectors: Optional[Union[Union[str, DataCollectorId], List[Union[str, DataCollectorId]]]] = empty_list()
    collection_timeframes: Optional[Union[Union[str, CollectionTimeframeId], List[Union[str, CollectionTimeframeId]]]] = empty_list()
    ethical_reviews: Optional[Union[Union[str, EthicalReviewId], List[Union[str, EthicalReviewId]]]] = empty_list()
    data_protection_impacts: Optional[Union[Union[str, DataProtectionImpactId], List[Union[str, DataProtectionImpactId]]]] = empty_list()
    preprocessing_strategies: Optional[Union[Union[str, PreprocessingStrategyId], List[Union[str, PreprocessingStrategyId]]]] = empty_list()
    cleaning_strategies: Optional[Union[Union[str, CleaningStrategyId], List[Union[str, CleaningStrategyId]]]] = empty_list()
    labeling_strategies: Optional[Union[Union[str, LabelingStrategyId], List[Union[str, LabelingStrategyId]]]] = empty_list()
    raw_sources: Optional[Union[Union[str, RawDataId], List[Union[str, RawDataId]]]] = empty_list()
    existing_uses: Optional[Union[Union[str, ExistingUseId], List[Union[str, ExistingUseId]]]] = empty_list()
    use_repository: Optional[Union[Union[str, UseRepositoryId], List[Union[str, UseRepositoryId]]]] = empty_list()
    other_tasks: Optional[Union[Union[str, OtherTaskId], List[Union[str, OtherTaskId]]]] = empty_list()
    future_use_impacts: Optional[Union[Union[str, FutureUseImpactId], List[Union[str, FutureUseImpactId]]]] = empty_list()
    discouraged_uses: Optional[Union[Union[str, DiscouragedUseId], List[Union[str, DiscouragedUseId]]]] = empty_list()
    distribution_formats: Optional[Union[Union[str, DistributionFormatId], List[Union[str, DistributionFormatId]]]] = empty_list()
    distribution_dates: Optional[Union[Union[str, DistributionDateId], List[Union[str, DistributionDateId]]]] = empty_list()
    license_and_use_terms: Optional[Union[str, LicenseAndUseTermsId]] = None
    ip_restrictions: Optional[Union[str, IPRestrictionsId]] = None
    regulatory_restrictions: Optional[Union[str, ExportControlRegulatoryRestrictionsId]] = None
    maintainers: Optional[Union[Union[str, MaintainerId], List[Union[str, MaintainerId]]]] = empty_list()
    errata: Optional[Union[Union[str, ErratumId], List[Union[str, ErratumId]]]] = empty_list()
    updates: Optional[Union[str, UpdatePlanId]] = None
    retention_limit: Optional[Union[str, RetentionLimitsId]] = None
    version_access: Optional[Union[str, VersionAccessId]] = None
    extension_mechanism: Optional[Union[str, ExtensionMechanismId]] = None
    is_deidentified: Optional[Union[str, DeidentificationId]] = None
    is_tabular: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
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

        if self.media_type is not None and not isinstance(self.media_type, str):
            self.media_type = str(self.media_type)

        if self.path is not None and not isinstance(self.path, str):
            self.path = str(self.path)

        if self.sha256 is not None and not isinstance(self.sha256, str):
            self.sha256 = str(self.sha256)

        if not isinstance(self.purposes, list):
            self.purposes = [self.purposes] if self.purposes is not None else []
        self.purposes = [v if isinstance(v, PurposeId) else PurposeId(v) for v in self.purposes]

        if not isinstance(self.tasks, list):
            self.tasks = [self.tasks] if self.tasks is not None else []
        self.tasks = [v if isinstance(v, TaskId) else TaskId(v) for v in self.tasks]

        if not isinstance(self.addressing_gaps, list):
            self.addressing_gaps = [self.addressing_gaps] if self.addressing_gaps is not None else []
        self.addressing_gaps = [v if isinstance(v, AddressingGapId) else AddressingGapId(v) for v in self.addressing_gaps]

        if not isinstance(self.creators, list):
            self.creators = [self.creators] if self.creators is not None else []
        self.creators = [v if isinstance(v, CreatorId) else CreatorId(v) for v in self.creators]

        if not isinstance(self.funders, list):
            self.funders = [self.funders] if self.funders is not None else []
        self.funders = [v if isinstance(v, FundingMechanismId) else FundingMechanismId(v) for v in self.funders]

        if not isinstance(self.subsets, list):
            self.subsets = [self.subsets] if self.subsets is not None else []
        self.subsets = [v if isinstance(v, DataSubsetId) else DataSubsetId(v) for v in self.subsets]

        if not isinstance(self.instances, list):
            self.instances = [self.instances] if self.instances is not None else []
        self.instances = [v if isinstance(v, InstanceId) else InstanceId(v) for v in self.instances]

        if not isinstance(self.anomalies, list):
            self.anomalies = [self.anomalies] if self.anomalies is not None else []
        self.anomalies = [v if isinstance(v, DataAnomalyId) else DataAnomalyId(v) for v in self.anomalies]

        if not isinstance(self.external_resources, list):
            self.external_resources = [self.external_resources] if self.external_resources is not None else []
        self.external_resources = [v if isinstance(v, ExternalResourceId) else ExternalResourceId(v) for v in self.external_resources]

        if not isinstance(self.confidential_elements, list):
            self.confidential_elements = [self.confidential_elements] if self.confidential_elements is not None else []
        self.confidential_elements = [v if isinstance(v, ConfidentialityId) else ConfidentialityId(v) for v in self.confidential_elements]

        if not isinstance(self.content_warnings, list):
            self.content_warnings = [self.content_warnings] if self.content_warnings is not None else []
        self.content_warnings = [v if isinstance(v, ContentWarningId) else ContentWarningId(v) for v in self.content_warnings]

        if not isinstance(self.subpopulations, list):
            self.subpopulations = [self.subpopulations] if self.subpopulations is not None else []
        self.subpopulations = [v if isinstance(v, SubpopulationId) else SubpopulationId(v) for v in self.subpopulations]

        if not isinstance(self.sensitive_elements, list):
            self.sensitive_elements = [self.sensitive_elements] if self.sensitive_elements is not None else []
        self.sensitive_elements = [v if isinstance(v, SensitiveElementId) else SensitiveElementId(v) for v in self.sensitive_elements]

        if not isinstance(self.acquisition_methods, list):
            self.acquisition_methods = [self.acquisition_methods] if self.acquisition_methods is not None else []
        self.acquisition_methods = [v if isinstance(v, InstanceAcquisitionId) else InstanceAcquisitionId(v) for v in self.acquisition_methods]

        if not isinstance(self.collection_mechanisms, list):
            self.collection_mechanisms = [self.collection_mechanisms] if self.collection_mechanisms is not None else []
        self.collection_mechanisms = [v if isinstance(v, CollectionMechanismId) else CollectionMechanismId(v) for v in self.collection_mechanisms]

        if not isinstance(self.sampling_strategies, list):
            self.sampling_strategies = [self.sampling_strategies] if self.sampling_strategies is not None else []
        self.sampling_strategies = [v if isinstance(v, SamplingStrategyId) else SamplingStrategyId(v) for v in self.sampling_strategies]

        if not isinstance(self.data_collectors, list):
            self.data_collectors = [self.data_collectors] if self.data_collectors is not None else []
        self.data_collectors = [v if isinstance(v, DataCollectorId) else DataCollectorId(v) for v in self.data_collectors]

        if not isinstance(self.collection_timeframes, list):
            self.collection_timeframes = [self.collection_timeframes] if self.collection_timeframes is not None else []
        self.collection_timeframes = [v if isinstance(v, CollectionTimeframeId) else CollectionTimeframeId(v) for v in self.collection_timeframes]

        if not isinstance(self.ethical_reviews, list):
            self.ethical_reviews = [self.ethical_reviews] if self.ethical_reviews is not None else []
        self.ethical_reviews = [v if isinstance(v, EthicalReviewId) else EthicalReviewId(v) for v in self.ethical_reviews]

        if not isinstance(self.data_protection_impacts, list):
            self.data_protection_impacts = [self.data_protection_impacts] if self.data_protection_impacts is not None else []
        self.data_protection_impacts = [v if isinstance(v, DataProtectionImpactId) else DataProtectionImpactId(v) for v in self.data_protection_impacts]

        if not isinstance(self.preprocessing_strategies, list):
            self.preprocessing_strategies = [self.preprocessing_strategies] if self.preprocessing_strategies is not None else []
        self.preprocessing_strategies = [v if isinstance(v, PreprocessingStrategyId) else PreprocessingStrategyId(v) for v in self.preprocessing_strategies]

        if not isinstance(self.cleaning_strategies, list):
            self.cleaning_strategies = [self.cleaning_strategies] if self.cleaning_strategies is not None else []
        self.cleaning_strategies = [v if isinstance(v, CleaningStrategyId) else CleaningStrategyId(v) for v in self.cleaning_strategies]

        if not isinstance(self.labeling_strategies, list):
            self.labeling_strategies = [self.labeling_strategies] if self.labeling_strategies is not None else []
        self.labeling_strategies = [v if isinstance(v, LabelingStrategyId) else LabelingStrategyId(v) for v in self.labeling_strategies]

        if not isinstance(self.raw_sources, list):
            self.raw_sources = [self.raw_sources] if self.raw_sources is not None else []
        self.raw_sources = [v if isinstance(v, RawDataId) else RawDataId(v) for v in self.raw_sources]

        if not isinstance(self.existing_uses, list):
            self.existing_uses = [self.existing_uses] if self.existing_uses is not None else []
        self.existing_uses = [v if isinstance(v, ExistingUseId) else ExistingUseId(v) for v in self.existing_uses]

        if not isinstance(self.use_repository, list):
            self.use_repository = [self.use_repository] if self.use_repository is not None else []
        self.use_repository = [v if isinstance(v, UseRepositoryId) else UseRepositoryId(v) for v in self.use_repository]

        if not isinstance(self.other_tasks, list):
            self.other_tasks = [self.other_tasks] if self.other_tasks is not None else []
        self.other_tasks = [v if isinstance(v, OtherTaskId) else OtherTaskId(v) for v in self.other_tasks]

        if not isinstance(self.future_use_impacts, list):
            self.future_use_impacts = [self.future_use_impacts] if self.future_use_impacts is not None else []
        self.future_use_impacts = [v if isinstance(v, FutureUseImpactId) else FutureUseImpactId(v) for v in self.future_use_impacts]

        if not isinstance(self.discouraged_uses, list):
            self.discouraged_uses = [self.discouraged_uses] if self.discouraged_uses is not None else []
        self.discouraged_uses = [v if isinstance(v, DiscouragedUseId) else DiscouragedUseId(v) for v in self.discouraged_uses]

        if not isinstance(self.distribution_formats, list):
            self.distribution_formats = [self.distribution_formats] if self.distribution_formats is not None else []
        self.distribution_formats = [v if isinstance(v, DistributionFormatId) else DistributionFormatId(v) for v in self.distribution_formats]

        if not isinstance(self.distribution_dates, list):
            self.distribution_dates = [self.distribution_dates] if self.distribution_dates is not None else []
        self.distribution_dates = [v if isinstance(v, DistributionDateId) else DistributionDateId(v) for v in self.distribution_dates]

        if self.license_and_use_terms is not None and not isinstance(self.license_and_use_terms, LicenseAndUseTermsId):
            self.license_and_use_terms = LicenseAndUseTermsId(self.license_and_use_terms)

        if self.ip_restrictions is not None and not isinstance(self.ip_restrictions, IPRestrictionsId):
            self.ip_restrictions = IPRestrictionsId(self.ip_restrictions)

        if self.regulatory_restrictions is not None and not isinstance(self.regulatory_restrictions, ExportControlRegulatoryRestrictionsId):
            self.regulatory_restrictions = ExportControlRegulatoryRestrictionsId(self.regulatory_restrictions)

        if not isinstance(self.maintainers, list):
            self.maintainers = [self.maintainers] if self.maintainers is not None else []
        self.maintainers = [v if isinstance(v, MaintainerId) else MaintainerId(v) for v in self.maintainers]

        if not isinstance(self.errata, list):
            self.errata = [self.errata] if self.errata is not None else []
        self.errata = [v if isinstance(v, ErratumId) else ErratumId(v) for v in self.errata]

        if self.updates is not None and not isinstance(self.updates, UpdatePlanId):
            self.updates = UpdatePlanId(self.updates)

        if self.retention_limit is not None and not isinstance(self.retention_limit, RetentionLimitsId):
            self.retention_limit = RetentionLimitsId(self.retention_limit)

        if self.version_access is not None and not isinstance(self.version_access, VersionAccessId):
            self.version_access = VersionAccessId(self.version_access)

        if self.extension_mechanism is not None and not isinstance(self.extension_mechanism, ExtensionMechanismId):
            self.extension_mechanism = ExtensionMechanismId(self.extension_mechanism)

        if self.is_deidentified is not None and not isinstance(self.is_deidentified, DeidentificationId):
            self.is_deidentified = DeidentificationId(self.is_deidentified)

        if self.is_tabular is not None and not isinstance(self.is_tabular, Bool):
            self.is_tabular = Bool(self.is_tabular)

        super().__post_init__(**kwargs)


@dataclass
class DataSubset(Dataset):
    """
    A subset of a dataset, likely containing multiple files of multiple potential purposes and properties.
    """
    _inherited_slots: ClassVar[List[str]] = []

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DataSubset"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DataSubset"
    class_name: ClassVar[str] = "DataSubset"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataSubset

    id: Union[str, DataSubsetId] = None
    is_data_split: Optional[Union[bool, Bool]] = None
    is_subpopulation: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DataSubsetId):
            self.id = DataSubsetId(self.id)

        if self.is_data_split is not None and not isinstance(self.is_data_split, Bool):
            self.is_data_split = Bool(self.is_data_split)

        if self.is_subpopulation is not None and not isinstance(self.is_subpopulation, Bool):
            self.is_subpopulation = Bool(self.is_subpopulation)

        super().__post_init__(**kwargs)


@dataclass
class NamedThing(YAMLRoot):
    """
    A generic grouping for any identifiable entity
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = SCHEMA["Thing"]
    class_class_curie: ClassVar[str] = "schema:Thing"
    class_name: ClassVar[str] = "NamedThing"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.NamedThing

    id: Union[str, NamedThingId] = None
    category: Optional[Union[str, CategoryType]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    subclass_of: Optional[Union[Union[str, NamedThingId], List[Union[str, NamedThingId]]]] = empty_list()
    related_to: Optional[Union[Union[str, NamedThingId], List[Union[str, NamedThingId]]]] = empty_list()
    contributor_name: Optional[str] = None
    contributor_github_name: Optional[str] = None
    contributor_orcid: Optional[Union[str, URIorCURIE]] = None
    contribution_date: Optional[Union[str, XSDDate]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, NamedThingId):
            self.id = NamedThingId(self.id)

        self.category = str(self.class_class_curie)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.subclass_of, list):
            self.subclass_of = [self.subclass_of] if self.subclass_of is not None else []
        self.subclass_of = [v if isinstance(v, NamedThingId) else NamedThingId(v) for v in self.subclass_of]

        if not isinstance(self.related_to, list):
            self.related_to = [self.related_to] if self.related_to is not None else []
        self.related_to = [v if isinstance(v, NamedThingId) else NamedThingId(v) for v in self.related_to]

        if self.contributor_name is not None and not isinstance(self.contributor_name, str):
            self.contributor_name = str(self.contributor_name)

        if self.contributor_github_name is not None and not isinstance(self.contributor_github_name, str):
            self.contributor_github_name = str(self.contributor_github_name)

        if self.contributor_orcid is not None and not isinstance(self.contributor_orcid, URIorCURIE):
            self.contributor_orcid = URIorCURIE(self.contributor_orcid)

        if self.contribution_date is not None and not isinstance(self.contribution_date, XSDDate):
            self.contribution_date = XSDDate(self.contribution_date)

        super().__post_init__(**kwargs)


    def __new__(cls, *args, **kwargs):

        type_designator = "category"
        if not type_designator in kwargs:
            return super().__new__(cls,*args,**kwargs)
        else:
            type_designator_value = kwargs[type_designator]
            target_cls = cls._class_for("class_class_curie", type_designator_value)


            if target_cls is None:
                target_cls = cls._class_for("class_class_uri", type_designator_value)


            if target_cls is None:
                target_cls = cls._class_for("class_model_uri", type_designator_value)


            if target_cls is None:
                raise ValueError(f"Wrong type designator value: class {cls.__name__} "
                                 f"has no subclass with ['class_class_curie', 'class_class_uri', 'class_model_uri']='{kwargs[type_designator]}'")
            return super().__new__(target_cls,*args,**kwargs)



@dataclass
class Person(NamedThing):
    """
    An individual human being.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Person"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Person"
    class_name: ClassVar[str] = "Person"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Person

    id: Union[str, PersonId] = None
    affiliation: Optional[Union[Union[str, OrganizationId], List[Union[str, OrganizationId]]]] = empty_list()
    email: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PersonId):
            self.id = PersonId(self.id)

        if not isinstance(self.affiliation, list):
            self.affiliation = [self.affiliation] if self.affiliation is not None else []
        self.affiliation = [v if isinstance(v, OrganizationId) else OrganizationId(v) for v in self.affiliation]

        if self.email is not None and not isinstance(self.email, str):
            self.email = str(self.email)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DatasetProperty(NamedThing):
    """
    Represents a single property of a dataset, or a set of related properties.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DatasetProperty"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DatasetProperty"
    class_name: ClassVar[str] = "DatasetProperty"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DatasetProperty

    id: Union[str, DatasetPropertyId] = None
    used_software: Optional[Union[Union[str, SoftwareId], List[Union[str, SoftwareId]]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetPropertyId):
            self.id = DatasetPropertyId(self.id)

        if not isinstance(self.used_software, list):
            self.used_software = [self.used_software] if self.used_software is not None else []
        self.used_software = [v if isinstance(v, SoftwareId) else SoftwareId(v) for v in self.used_software]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Software(NamedThing):
    """
    A software program or library.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Software"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Software"
    class_name: ClassVar[str] = "Software"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Software

    id: Union[str, SoftwareId] = None
    version: Optional[str] = None
    license: Optional[str] = None
    url: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
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
        self.category = str(self.class_class_curie)


@dataclass
class Purpose(DatasetProperty):
    """
    For what purpose was the dataset created?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Purpose"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Purpose"
    class_name: ClassVar[str] = "Purpose"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Purpose

    id: Union[str, PurposeId] = None
    response: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PurposeId):
            self.id = PurposeId(self.id)

        if self.response is not None and not isinstance(self.response, str):
            self.response = str(self.response)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Task(DatasetProperty):
    """
    Was there a specific task in mind for the dataset's application?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Task"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Task"
    class_name: ClassVar[str] = "Task"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Task

    id: Union[str, TaskId] = None
    response: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, TaskId):
            self.id = TaskId(self.id)

        if self.response is not None and not isinstance(self.response, str):
            self.response = str(self.response)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class AddressingGap(DatasetProperty):
    """
    Was there a specific gap that needed to be filled by creation of the dataset?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["AddressingGap"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:AddressingGap"
    class_name: ClassVar[str] = "AddressingGap"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.AddressingGap

    id: Union[str, AddressingGapId] = None
    response: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, AddressingGapId):
            self.id = AddressingGapId(self.id)

        if self.response is not None and not isinstance(self.response, str):
            self.response = str(self.response)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Creator(DatasetProperty):
    """
    Who created the dataset (e.g., which team, research group) and on behalf of which entity (e.g., company,
    institution, organization)? This may also be considered a team.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Creator"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Creator"
    class_name: ClassVar[str] = "Creator"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Creator

    id: Union[str, CreatorId] = None
    principal_investigator: Optional[Union[str, PersonId]] = None
    affiliation: Optional[Union[str, OrganizationId]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CreatorId):
            self.id = CreatorId(self.id)

        if self.principal_investigator is not None and not isinstance(self.principal_investigator, PersonId):
            self.principal_investigator = PersonId(self.principal_investigator)

        if self.affiliation is not None and not isinstance(self.affiliation, OrganizationId):
            self.affiliation = OrganizationId(self.affiliation)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class FundingMechanism(DatasetProperty):
    """
    Who funded the creation of the dataset? If there is an associated grant, please provide the name of the grantor
    and the grant name and number.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["FundingMechanism"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:FundingMechanism"
    class_name: ClassVar[str] = "FundingMechanism"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.FundingMechanism

    id: Union[str, FundingMechanismId] = None
    grantor: Optional[Union[str, GrantorId]] = None
    grant: Optional[Union[str, GrantId]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, FundingMechanismId):
            self.id = FundingMechanismId(self.id)

        if self.grantor is not None and not isinstance(self.grantor, GrantorId):
            self.grantor = GrantorId(self.grantor)

        if self.grant is not None and not isinstance(self.grant, GrantId):
            self.grant = GrantId(self.grant)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Grant(NamedThing):
    """
    What is the name and/or identifier of the specific mechanism providing monetary support or other resources
    supporting creation of the dataset?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Grant"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Grant"
    class_name: ClassVar[str] = "Grant"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Grant

    id: Union[str, GrantId] = None
    grant_number: Optional[str] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, GrantId):
            self.id = GrantId(self.id)

        if self.grant_number is not None and not isinstance(self.grant_number, str):
            self.grant_number = str(self.grant_number)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Instance(DatasetProperty):
    """
    What do the instances that comprise the dataset represent (e.g., documents, photos, people, countries)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Instance"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Instance"
    class_name: ClassVar[str] = "Instance"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Instance

    id: Union[str, InstanceId] = None
    data_topic: Optional[Union[str, URIorCURIE]] = None
    instance_type: Optional[str] = None
    data_substrate: Optional[Union[str, URIorCURIE]] = None
    counts: Optional[int] = None
    label: Optional[Union[bool, Bool]] = None
    label_description: Optional[str] = None
    sampling_strategies: Optional[Union[Union[str, SamplingStrategyId], List[Union[str, SamplingStrategyId]]]] = empty_list()
    missing_information: Optional[Union[Union[str, MissingInfoId], List[Union[str, MissingInfoId]]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InstanceId):
            self.id = InstanceId(self.id)

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
        self.sampling_strategies = [v if isinstance(v, SamplingStrategyId) else SamplingStrategyId(v) for v in self.sampling_strategies]

        if not isinstance(self.missing_information, list):
            self.missing_information = [self.missing_information] if self.missing_information is not None else []
        self.missing_information = [v if isinstance(v, MissingInfoId) else MissingInfoId(v) for v in self.missing_information]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class SamplingStrategy(DatasetProperty):
    """
    Does the dataset contain all possible instances or is it a sample (not necessarily random) of instances from a
    larger set? If the dataset is a sample, then what is the larger set? Is the sample representative of the larger
    set (e.g., geographic coverage)? If so, please describe how this representativeness was validated/verified. If it
    is not representative of the larger set, please describe why not (e.g., to cover a more diverse range of
    instances, because instances were withheld or unavailable).
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["SamplingStrategy"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:SamplingStrategy"
    class_name: ClassVar[str] = "SamplingStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.SamplingStrategy

    id: Union[str, SamplingStrategyId] = None
    is_sample: Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]] = empty_list()
    is_random: Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]] = empty_list()
    source_data: Optional[Union[str, List[str]]] = empty_list()
    is_representative: Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]] = empty_list()
    representative_verification: Optional[Union[str, List[str]]] = empty_list()
    why_not_representative: Optional[Union[str, List[str]]] = empty_list()
    strategies: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, SamplingStrategyId):
            self.id = SamplingStrategyId(self.id)

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
        self.category = str(self.class_class_curie)


@dataclass
class MissingInfo(DatasetProperty):
    """
    Is any information missing from individual instances? If so, please provide a description, explaining why this
    information is missing (e.g., because it was unavailable). This does not include intentionally removed
    information, but might include, e.g., redacted text.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["MissingInfo"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:MissingInfo"
    class_name: ClassVar[str] = "MissingInfo"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.MissingInfo

    id: Union[str, MissingInfoId] = None
    missing: Optional[Union[str, List[str]]] = empty_list()
    why_missing: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, MissingInfoId):
            self.id = MissingInfoId(self.id)

        if not isinstance(self.missing, list):
            self.missing = [self.missing] if self.missing is not None else []
        self.missing = [v if isinstance(v, str) else str(v) for v in self.missing]

        if not isinstance(self.why_missing, list):
            self.why_missing = [self.why_missing] if self.why_missing is not None else []
        self.why_missing = [v if isinstance(v, str) else str(v) for v in self.why_missing]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Relationships(DatasetProperty):
    """
    Are relationships between individual instances made explicit (e.g., users’ movie ratings, social network links)?
    If so, please describe how these relationships are made explicit.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Relationships"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Relationships"
    class_name: ClassVar[str] = "Relationships"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Relationships

    id: Union[str, RelationshipsId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, RelationshipsId):
            self.id = RelationshipsId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Splits(DatasetProperty):
    """
    Are there recommended data splits (e.g., training, development/validation, testing)? If so, please provide a
    description of these splits, explaining the rationale behind them.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Splits"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Splits"
    class_name: ClassVar[str] = "Splits"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Splits

    id: Union[str, SplitsId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, SplitsId):
            self.id = SplitsId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DataAnomaly(DatasetProperty):
    """
    Are there any errors, sources of noise, or redundancies in the dataset? If so, please provide a description.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DataAnomaly"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DataAnomaly"
    class_name: ClassVar[str] = "DataAnomaly"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataAnomaly

    id: Union[str, DataAnomalyId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DataAnomalyId):
            self.id = DataAnomalyId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ExternalResource(DatasetProperty):
    """
    Is the dataset self-contained, or does it link to or otherwise rely on external resources (e.g., websites, tweets,
    other datasets)? If it links to or relies on external resources, a) are there guarantees that they will exist, and
    remain constant, over time; b) are there official archival versions of the complete dataset (i.e., including the
    external resources as they existed at the time the dataset was created); c) are there any restrictions (e.g.,
    licenses, fees) associated with any of the external resources that might apply to a dataset consumer? Please
    provide descriptions of all external resources and any restrictions associated with them, as well as links or
    other access points, as appropriate.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ExternalResource"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ExternalResource"
    class_name: ClassVar[str] = "ExternalResource"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExternalResource

    id: Union[str, ExternalResourceId] = None
    external_resources: Optional[Union[str, List[str]]] = empty_list()
    future_guarantees: Optional[Union[str, List[str]]] = empty_list()
    archival: Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]] = empty_list()
    restrictions: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ExternalResourceId):
            self.id = ExternalResourceId(self.id)

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
        self.category = str(self.class_class_curie)


@dataclass
class Confidentiality(DatasetProperty):
    """
    Does the dataset contain data that might be considered confidential (e.g., data that is protected by legal
    privilege or by doctor patient confidentiality, data that includes the content of individuals’ non-public
    communications)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Confidentiality"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Confidentiality"
    class_name: ClassVar[str] = "Confidentiality"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Confidentiality

    id: Union[str, ConfidentialityId] = None
    confidential_elements_present: Optional[Union[bool, Bool]] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ConfidentialityId):
            self.id = ConfidentialityId(self.id)

        if self.confidential_elements_present is not None and not isinstance(self.confidential_elements_present, Bool):
            self.confidential_elements_present = Bool(self.confidential_elements_present)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ContentWarning(DatasetProperty):
    """
    Does the dataset contain data that, if viewed directly, might be offensive, insulting, threatening, or might
    otherwise cause anxiety? If so, please describe why.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ContentWarning"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ContentWarning"
    class_name: ClassVar[str] = "ContentWarning"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ContentWarning

    id: Union[str, ContentWarningId] = None
    content_warnings_present: Optional[Union[bool, Bool]] = None
    warnings: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ContentWarningId):
            self.id = ContentWarningId(self.id)

        if self.content_warnings_present is not None and not isinstance(self.content_warnings_present, Bool):
            self.content_warnings_present = Bool(self.content_warnings_present)

        if not isinstance(self.warnings, list):
            self.warnings = [self.warnings] if self.warnings is not None else []
        self.warnings = [v if isinstance(v, str) else str(v) for v in self.warnings]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Subpopulation(DatasetProperty):
    """
    Does the dataset identify any subpopulations (e.g., by age, gender)? If so, please describe how these
    subpopulations are identified and provide a description of their respective distributions within the dataset.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Subpopulation"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Subpopulation"
    class_name: ClassVar[str] = "Subpopulation"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Subpopulation

    id: Union[str, SubpopulationId] = None
    subpopulation_elements_present: Optional[Union[bool, Bool]] = None
    identification: Optional[Union[str, List[str]]] = empty_list()
    distribution: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, SubpopulationId):
            self.id = SubpopulationId(self.id)

        if self.subpopulation_elements_present is not None and not isinstance(self.subpopulation_elements_present, Bool):
            self.subpopulation_elements_present = Bool(self.subpopulation_elements_present)

        if not isinstance(self.identification, list):
            self.identification = [self.identification] if self.identification is not None else []
        self.identification = [v if isinstance(v, str) else str(v) for v in self.identification]

        if not isinstance(self.distribution, list):
            self.distribution = [self.distribution] if self.distribution is not None else []
        self.distribution = [v if isinstance(v, str) else str(v) for v in self.distribution]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Deidentification(DatasetProperty):
    """
    Is it possible to identify individuals (i.e., one or more natural persons), either directly or indirectly (i.e.,
    in combination with other data) from the dataset?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Deidentification"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Deidentification"
    class_name: ClassVar[str] = "Deidentification"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Deidentification

    id: Union[str, DeidentificationId] = None
    identifiable_elements_present: Optional[Union[bool, Bool]] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DeidentificationId):
            self.id = DeidentificationId(self.id)

        if self.identifiable_elements_present is not None and not isinstance(self.identifiable_elements_present, Bool):
            self.identifiable_elements_present = Bool(self.identifiable_elements_present)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class SensitiveElement(DatasetProperty):
    """
    Does the dataset contain data that might be considered sensitive in any way (e.g., data that reveals race or
    ethnic origins, sexual orientations, religious beliefs, political opinions or union memberships, or locations;
    financial or health data; biometric or genetic data; forms of government identification, such as social security
    numbers; criminal history)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["SensitiveElement"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:SensitiveElement"
    class_name: ClassVar[str] = "SensitiveElement"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.SensitiveElement

    id: Union[str, SensitiveElementId] = None
    sensitive_elements_present: Optional[Union[bool, Bool]] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, SensitiveElementId):
            self.id = SensitiveElementId(self.id)

        if self.sensitive_elements_present is not None and not isinstance(self.sensitive_elements_present, Bool):
            self.sensitive_elements_present = Bool(self.sensitive_elements_present)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class InstanceAcquisition(DatasetProperty):
    """
    How was the data associated with each instance acquired? Was the data directly observable (e.g., raw text, movie
    ratings), reported by subjects (e.g., survey responses), or indirectly inferred/derived from other data (e.g.,
    part-of-speech tags, model-based guesses for age or language)? If the data was reported by subjects or indirectly
    inferred/derived from other data, was the data validated/verified?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["InstanceAcquisition"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:InstanceAcquisition"
    class_name: ClassVar[str] = "InstanceAcquisition"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.InstanceAcquisition

    id: Union[str, InstanceAcquisitionId] = None
    description: Optional[Union[str, List[str]]] = empty_list()
    was_directly_observed: Optional[Union[bool, Bool]] = None
    was_reported_by_subjects: Optional[Union[bool, Bool]] = None
    was_inferred_derived: Optional[Union[bool, Bool]] = None
    was_validated_verified: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InstanceAcquisitionId):
            self.id = InstanceAcquisitionId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        if self.was_directly_observed is not None and not isinstance(self.was_directly_observed, Bool):
            self.was_directly_observed = Bool(self.was_directly_observed)

        if self.was_reported_by_subjects is not None and not isinstance(self.was_reported_by_subjects, Bool):
            self.was_reported_by_subjects = Bool(self.was_reported_by_subjects)

        if self.was_inferred_derived is not None and not isinstance(self.was_inferred_derived, Bool):
            self.was_inferred_derived = Bool(self.was_inferred_derived)

        if self.was_validated_verified is not None and not isinstance(self.was_validated_verified, Bool):
            self.was_validated_verified = Bool(self.was_validated_verified)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class CollectionMechanism(DatasetProperty):
    """
    What mechanisms or procedures were used to collect the data (e.g., hardware apparatuses or sensors, manual human
    curation, software programs, software APIs)? How were these mechanisms or procedures validated?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["CollectionMechanism"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:CollectionMechanism"
    class_name: ClassVar[str] = "CollectionMechanism"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionMechanism

    id: Union[str, CollectionMechanismId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CollectionMechanismId):
            self.id = CollectionMechanismId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DataCollector(DatasetProperty):
    """
    Who was involved in the data collection process (e.g., students, crowdworkers, contractors) and how were they
    compensated (e.g., how much were crowdworkers paid)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DataCollector"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DataCollector"
    class_name: ClassVar[str] = "DataCollector"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataCollector

    id: Union[str, DataCollectorId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DataCollectorId):
            self.id = DataCollectorId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class CollectionTimeframe(DatasetProperty):
    """
    Over what timeframe was the data collected? Does this timeframe match the creation timeframe of the data
    associated with the instances (e.g., recent crawl of old news articles)? If not, please describe the timeframe in
    which the data associated with the instances was created.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["CollectionTimeframe"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:CollectionTimeframe"
    class_name: ClassVar[str] = "CollectionTimeframe"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionTimeframe

    id: Union[str, CollectionTimeframeId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CollectionTimeframeId):
            self.id = CollectionTimeframeId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class EthicalReview(DatasetProperty):
    """
    Were any ethical review processes conducted (e.g., by an institutional review board)? If so, please provide a
    description of these review processes, including the outcomes, as well as a link or other access point to any
    supporting documentation.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["EthicalReview"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:EthicalReview"
    class_name: ClassVar[str] = "EthicalReview"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.EthicalReview

    id: Union[str, EthicalReviewId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, EthicalReviewId):
            self.id = EthicalReviewId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DirectCollection(DatasetProperty):
    """
    Did you collect the data from the individuals in question directly, or obtain it via third parties or other
    sources (e.g., websites)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DirectCollection"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DirectCollection"
    class_name: ClassVar[str] = "DirectCollection"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DirectCollection

    id: Union[str, DirectCollectionId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DirectCollectionId):
            self.id = DirectCollectionId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class CollectionNotification(DatasetProperty):
    """
    Were the individuals in question notified about the data collection? If so, please describe (or show with
    screenshots or other information) how notice was provided, and provide a link or other access point to, or
    otherwise reproduce, the exact language of the notification itself.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["CollectionNotification"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:CollectionNotification"
    class_name: ClassVar[str] = "CollectionNotification"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionNotification

    id: Union[str, CollectionNotificationId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CollectionNotificationId):
            self.id = CollectionNotificationId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class CollectionConsent(DatasetProperty):
    """
    Did the individuals in question consent to the collection and use of their data? If so, please describe (or show
    with screenshots or other information) how consent was requested and provided, and provide a link or other access
    point to, or otherwise reproduce, the exact language to which the individuals consented.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["CollectionConsent"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:CollectionConsent"
    class_name: ClassVar[str] = "CollectionConsent"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CollectionConsent

    id: Union[str, CollectionConsentId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CollectionConsentId):
            self.id = CollectionConsentId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ConsentRevocation(DatasetProperty):
    """
    If consent was obtained, were the consenting individuals provided with a mechanism to revoke their consent in the
    future or 8 for certain uses? If so, please provide a description, as well as a link or other access point to the
    mechanism (if appropriate).
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ConsentRevocation"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ConsentRevocation"
    class_name: ClassVar[str] = "ConsentRevocation"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ConsentRevocation

    id: Union[str, ConsentRevocationId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ConsentRevocationId):
            self.id = ConsentRevocationId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DataProtectionImpact(DatasetProperty):
    """
    Has an analysis of the potential impact of the dataset and its use on data subjects (e.g., a data protection
    impact analysis) been conducted? If so, please provide a description of this analysis, including the outcomes, as
    well as a link or other access point to any supporting documentation.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DataProtectionImpact"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DataProtectionImpact"
    class_name: ClassVar[str] = "DataProtectionImpact"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DataProtectionImpact

    id: Union[str, DataProtectionImpactId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DataProtectionImpactId):
            self.id = DataProtectionImpactId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class PreprocessingStrategy(DatasetProperty):
    """
    Was any preprocessing of the data done (e.g., discretization or bucketing, tokenization, SIFT feature extraction)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["PreprocessingStrategy"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:PreprocessingStrategy"
    class_name: ClassVar[str] = "PreprocessingStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.PreprocessingStrategy

    id: Union[str, PreprocessingStrategyId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PreprocessingStrategyId):
            self.id = PreprocessingStrategyId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class CleaningStrategy(DatasetProperty):
    """
    Was any cleaning of the data done (e.g., removal of instances, processing of missing values)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["CleaningStrategy"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:CleaningStrategy"
    class_name: ClassVar[str] = "CleaningStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.CleaningStrategy

    id: Union[str, CleaningStrategyId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CleaningStrategyId):
            self.id = CleaningStrategyId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class LabelingStrategy(DatasetProperty):
    """
    Was any preprocessing/cleaning/labeling of the data done (e.g., part-of-speech tagging)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["LabelingStrategy"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:LabelingStrategy"
    class_name: ClassVar[str] = "LabelingStrategy"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.LabelingStrategy

    id: Union[str, LabelingStrategyId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, LabelingStrategyId):
            self.id = LabelingStrategyId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class RawData(DatasetProperty):
    """
    Was the “raw” data saved in addition to the preprocessed/cleaned/labeled data (e.g., to support unanticipated
    future uses)? If so, please provide a link or other access point to the “raw” data.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["RawData"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:RawData"
    class_name: ClassVar[str] = "RawData"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.RawData

    id: Union[str, RawDataId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, RawDataId):
            self.id = RawDataId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ExistingUse(DatasetProperty):
    """
    Has the dataset been used for any tasks already?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ExistingUse"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ExistingUse"
    class_name: ClassVar[str] = "ExistingUse"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExistingUse

    id: Union[str, ExistingUseId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ExistingUseId):
            self.id = ExistingUseId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class UseRepository(DatasetProperty):
    """
    Is there a repository that links to any or all papers or systems that use the dataset? If so, please provide a
    link or other access point.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["UseRepository"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:UseRepository"
    class_name: ClassVar[str] = "UseRepository"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.UseRepository

    id: Union[str, UseRepositoryId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, UseRepositoryId):
            self.id = UseRepositoryId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class OtherTask(DatasetProperty):
    """
    What (other) tasks could the dataset be used for?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["OtherTask"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:OtherTask"
    class_name: ClassVar[str] = "OtherTask"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.OtherTask

    id: Union[str, OtherTaskId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OtherTaskId):
            self.id = OtherTaskId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class FutureUseImpact(DatasetProperty):
    """
    Is there anything about the composition of the dataset or the way it was collected and
    preprocessed/cleaned/labeled that might impact future uses? For example, is there anything that a dataset consumer
    might need to know to avoid uses that could result in unfair treatment of individuals or groups (e.g.,
    stereotyping, quality of service issues) or other risks or harms (e.g., legal risks, financial harms)? If so,
    please provide a description. Is there anything a dataset consumer could do to mitigate these risks or harms?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["FutureUseImpact"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:FutureUseImpact"
    class_name: ClassVar[str] = "FutureUseImpact"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.FutureUseImpact

    id: Union[str, FutureUseImpactId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, FutureUseImpactId):
            self.id = FutureUseImpactId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DiscouragedUse(DatasetProperty):
    """
    Are there tasks for which the dataset should not be used?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DiscouragedUse"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DiscouragedUse"
    class_name: ClassVar[str] = "DiscouragedUse"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DiscouragedUse

    id: Union[str, DiscouragedUseId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DiscouragedUseId):
            self.id = DiscouragedUseId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ThirdPartySharing(DatasetProperty):
    """
    Will the dataset be distributed to third parties outside of the entity (e.g., company, institution, organization)
    on behalf of which the dataset was created?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ThirdPartySharing"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ThirdPartySharing"
    class_name: ClassVar[str] = "ThirdPartySharing"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ThirdPartySharing

    id: Union[str, ThirdPartySharingId] = None
    description: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ThirdPartySharingId):
            self.id = ThirdPartySharingId(self.id)

        if self.description is not None and not isinstance(self.description, Bool):
            self.description = Bool(self.description)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DistributionFormat(DatasetProperty):
    """
    How will the dataset will be distributed (e.g., tarball on website, API, GitHub)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DistributionFormat"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DistributionFormat"
    class_name: ClassVar[str] = "DistributionFormat"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DistributionFormat

    id: Union[str, DistributionFormatId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DistributionFormatId):
            self.id = DistributionFormatId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class DistributionDate(DatasetProperty):
    """
    When will the dataset be distributed?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["DistributionDate"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:DistributionDate"
    class_name: ClassVar[str] = "DistributionDate"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.DistributionDate

    id: Union[str, DistributionDateId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DistributionDateId):
            self.id = DistributionDateId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class LicenseAndUseTerms(DatasetProperty):
    """
    Will the dataset be distributed under a copyright or other intellectual property (IP) license, and/or under
    applicable terms of use (ToU)? If so, please describe this license and/or ToU, and provide a link or other access
    point to, or otherwise reproduce, any relevant licensing terms or ToU, as well as any fees associated with these
    restrictions.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["LicenseAndUseTerms"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:LicenseAndUseTerms"
    class_name: ClassVar[str] = "LicenseAndUseTerms"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.LicenseAndUseTerms

    id: Union[str, LicenseAndUseTermsId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, LicenseAndUseTermsId):
            self.id = LicenseAndUseTermsId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class IPRestrictions(DatasetProperty):
    """
    Have any third parties imposed IP-based or other restrictions on the data associated with the instances? If so,
    please describe these restrictions, and provide a link or other access point to, or otherwise reproduce, any
    relevant licensing terms, as well as any fees associated with these restrictions.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["IPRestrictions"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:IPRestrictions"
    class_name: ClassVar[str] = "IPRestrictions"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.IPRestrictions

    id: Union[str, IPRestrictionsId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, IPRestrictionsId):
            self.id = IPRestrictionsId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ExportControlRegulatoryRestrictions(DatasetProperty):
    """
    Do any export controls or other regulatory restrictions apply to the dataset or to individual instances? If so,
    please describe these restrictions, and provide a link or other access point to, or otherwise reproduce, any
    supporting documentation.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ExportControlRegulatoryRestrictions"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ExportControlRegulatoryRestrictions"
    class_name: ClassVar[str] = "ExportControlRegulatoryRestrictions"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExportControlRegulatoryRestrictions

    id: Union[str, ExportControlRegulatoryRestrictionsId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ExportControlRegulatoryRestrictionsId):
            self.id = ExportControlRegulatoryRestrictionsId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Maintainer(DatasetProperty):
    """
    Who will be supporting/hosting/maintaining the dataset?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Maintainer"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Maintainer"
    class_name: ClassVar[str] = "Maintainer"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Maintainer

    id: Union[str, MaintainerId] = None
    description: Optional[Union[Union[str, "CreatorOrMaintainerEnum"], List[Union[str, "CreatorOrMaintainerEnum"]]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, MaintainerId):
            self.id = MaintainerId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, CreatorOrMaintainerEnum) else CreatorOrMaintainerEnum(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Erratum(DatasetProperty):
    """
    Is there an erratum? If so, please provide a link or other access point.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Erratum"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Erratum"
    class_name: ClassVar[str] = "Erratum"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Erratum

    id: Union[str, ErratumId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ErratumId):
            self.id = ErratumId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class UpdatePlan(DatasetProperty):
    """
    Will the dataset be updated (e.g., to correct labeling errors, add new instances, delete instances)? If so, please
    describe how often, by whom, and how updates will be communicated to dataset consumers (e.g., mailing list,
    GitHub)?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["UpdatePlan"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:UpdatePlan"
    class_name: ClassVar[str] = "UpdatePlan"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.UpdatePlan

    id: Union[str, UpdatePlanId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, UpdatePlanId):
            self.id = UpdatePlanId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class RetentionLimits(DatasetProperty):
    """
    If the dataset relates to people, are there applicable limits on the retention of the data associated with the
    instances (e.g., were the individuals in question told that their data would be retained for a fixed period of
    time and then deleted)? If so, please describe these limits and explain how they will be enforced.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["RetentionLimits"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:RetentionLimits"
    class_name: ClassVar[str] = "RetentionLimits"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.RetentionLimits

    id: Union[str, RetentionLimitsId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, RetentionLimitsId):
            self.id = RetentionLimitsId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class VersionAccess(DatasetProperty):
    """
    Will older versions of the dataset continue to be supported/hosted/maintained? If so, please describe how. If not,
    please describe how its obsolescence will be communicated to dataset consumers.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["VersionAccess"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:VersionAccess"
    class_name: ClassVar[str] = "VersionAccess"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.VersionAccess

    id: Union[str, VersionAccessId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, VersionAccessId):
            self.id = VersionAccessId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class ExtensionMechanism(DatasetProperty):
    """
    If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so? If
    so, please provide a description. Will these contributions be validated/verified? If so, please describe how. If
    not, why not? Is there a process for communicating/distributing these contributions to dataset consumers? If so,
    please provide a description.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["ExtensionMechanism"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:ExtensionMechanism"
    class_name: ClassVar[str] = "ExtensionMechanism"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.ExtensionMechanism

    id: Union[str, ExtensionMechanismId] = None
    description: Optional[Union[str, List[str]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ExtensionMechanismId):
            self.id = ExtensionMechanismId(self.id)

        if not isinstance(self.description, list):
            self.description = [self.description] if self.description is not None else []
        self.description = [v if isinstance(v, str) else str(v) for v in self.description]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class AnatomicalEntity(NamedThing):
    """
    A subcellular location, cell type or gross anatomical part
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = B2AI["AnatomicalEntity"]
    class_class_curie: ClassVar[str] = "B2AI:AnatomicalEntity"
    class_name: ClassVar[str] = "AnatomicalEntity"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.AnatomicalEntity

    id: Union[str, AnatomicalEntityId] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, AnatomicalEntityId):
            self.id = AnatomicalEntityId(self.id)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Organization(NamedThing):
    """
    Represents a group or organization related to or responsible for one or more Bridge2AI standards.
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = B2AI_ORG["Organization"]
    class_class_curie: ClassVar[str] = "B2AI_ORG:Organization"
    class_name: ClassVar[str] = "Organization"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Organization

    id: Union[str, OrganizationId] = None
    ror_id: Optional[Union[str, RorIdentifier]] = None
    wikidata_id: Optional[Union[str, WikidataIdentifier]] = None
    url: Optional[Union[str, URIorCURIE]] = None
    related_to: Optional[Union[Union[str, NamedThingId], List[Union[str, NamedThingId]]]] = empty_list()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OrganizationId):
            self.id = OrganizationId(self.id)

        if self.ror_id is not None and not isinstance(self.ror_id, RorIdentifier):
            self.ror_id = RorIdentifier(self.ror_id)

        if self.wikidata_id is not None and not isinstance(self.wikidata_id, WikidataIdentifier):
            self.wikidata_id = WikidataIdentifier(self.wikidata_id)

        if self.url is not None and not isinstance(self.url, URIorCURIE):
            self.url = URIorCURIE(self.url)

        if not isinstance(self.related_to, list):
            self.related_to = [self.related_to] if self.related_to is not None else []
        self.related_to = [v if isinstance(v, NamedThingId) else NamedThingId(v) for v in self.related_to]

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class Grantor(Organization):
    """
    What is the name and/or identifier of the organization providing monetary support or other resources supporting
    creation of the dataset?
    """
    _inherited_slots: ClassVar[List[str]] = ["subclass_of", "related_to"]

    class_class_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA["Grantor"]
    class_class_curie: ClassVar[str] = "data_sheets_schema:Grantor"
    class_name: ClassVar[str] = "Grantor"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.Grantor

    id: Union[str, GrantorId] = None

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, GrantorId):
            self.id = GrantorId(self.id)

        super().__post_init__(**kwargs)
        self.category = str(self.class_class_curie)


@dataclass
class OrganizationContainer(YAMLRoot):
    """
    A container for Organizations.
    """
    _inherited_slots: ClassVar[List[str]] = []

    class_class_uri: ClassVar[URIRef] = B2AI_ORG["OrganizationContainer"]
    class_class_curie: ClassVar[str] = "B2AI_ORG:OrganizationContainer"
    class_name: ClassVar[str] = "OrganizationContainer"
    class_model_uri: ClassVar[URIRef] = DATA_SHEETS_SCHEMA.OrganizationContainer

    organizations: Optional[Union[Dict[Union[str, OrganizationId], Union[dict, Organization]], List[Union[dict, Organization]]]] = empty_dict()

    def __post_init__(self, *_: List[str], **kwargs: Dict[str, Any]):
        self._normalize_inlined_as_list(slot_name="organizations", slot_type=Organization, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


# Enumerations
class CreatorOrMaintainerEnum(EnumDefinitionImpl):
    """
    The entity responsible for maintaining a dataset.
    """
    Person = PermissibleValue(text="Person")
    Organization = PermissibleValue(text="Organization")

    _defn = EnumDefinition(
        name="CreatorOrMaintainerEnum",
        description="The entity responsible for maintaining a dataset.",
    )

class MediaTypeEnum(EnumDefinitionImpl):

    csv = PermissibleValue(
        text="csv",
        meaning=MEDIATYPES["text/csv"])

    _defn = EnumDefinition(
        name="MediaTypeEnum",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "rdf-xml",
            PermissibleValue(
                text="rdf-xml",
                meaning=MEDIATYPES["application/rdf+xml"]))

class FormatEnum(EnumDefinitionImpl):

    N3 = PermissibleValue(
        text="N3",
        meaning=FORMATS["N3"])
    Microdata = PermissibleValue(
        text="Microdata",
        meaning=FORMATS["microdata"])
    POWDER = PermissibleValue(
        text="POWDER",
        meaning=FORMATS["POWDER"])
    RDFa = PermissibleValue(
        text="RDFa",
        meaning=FORMATS["RDFa"])
    Turtle = PermissibleValue(
        text="Turtle",
        meaning=FORMATS["Turtle"])
    TriG = PermissibleValue(
        text="TriG",
        meaning=FORMATS["TriG"])
    YAML = PermissibleValue(text="YAML")
    JSON = PermissibleValue(text="JSON")

    _defn = EnumDefinition(
        name="FormatEnum",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "JSON-LD",
            PermissibleValue(
                text="JSON-LD",
                meaning=FORMATS["JSON-LD"]))
        setattr(cls, "N-Triples",
            PermissibleValue(
                text="N-Triples",
                meaning=FORMATS["N-Triples"]))
        setattr(cls, "N-Quads",
            PermissibleValue(
                text="N-Quads",
                meaning=FORMATS["N-Quads"]))
        setattr(cls, "LD Patch",
            PermissibleValue(
                text="LD Patch",
                meaning=FORMATS["LD_Patch"]))
        setattr(cls, "OWL XML Serialization",
            PermissibleValue(
                text="OWL XML Serialization",
                meaning=FORMATS["OWL_XML"]))
        setattr(cls, "OWL Functional Syntax",
            PermissibleValue(
                text="OWL Functional Syntax",
                meaning=FORMATS["OWL_Functional"]))
        setattr(cls, "OWL Manchester Syntax",
            PermissibleValue(
                text="OWL Manchester Syntax",
                meaning=FORMATS["OWL_Manchester"]))
        setattr(cls, "POWDER-S",
            PermissibleValue(
                text="POWDER-S",
                meaning=FORMATS["POWDER-S"]))
        setattr(cls, "PROV-N",
            PermissibleValue(
                text="PROV-N",
                meaning=FORMATS["PROV-N"]))
        setattr(cls, "PROV-XML",
            PermissibleValue(
                text="PROV-XML",
                meaning=FORMATS["PROV-XML"]))
        setattr(cls, "RDF/JSON",
            PermissibleValue(
                text="RDF/JSON",
                meaning=FORMATS["RDF_JSON"]))
        setattr(cls, "RDF/XML",
            PermissibleValue(
                text="RDF/XML",
                meaning=FORMATS["RDF_XML"]))
        setattr(cls, "RIF XML Syntax",
            PermissibleValue(
                text="RIF XML Syntax",
                meaning=FORMATS["RIF_XML"]))
        setattr(cls, "SPARQL Results in XML",
            PermissibleValue(
                text="SPARQL Results in XML",
                meaning=FORMATS["SPARQL_Results_XML"]))
        setattr(cls, "SPARQL Results in JSON",
            PermissibleValue(
                text="SPARQL Results in JSON",
                meaning=FORMATS["SPARQL_Results_JSON"]))
        setattr(cls, "SPARQL Results in CSV",
            PermissibleValue(
                text="SPARQL Results in CSV",
                meaning=FORMATS["SPARQL_Results_CSV"]))
        setattr(cls, "SPARQL Results in TSV",
            PermissibleValue(
                text="SPARQL Results in TSV",
                meaning=FORMATS["SPARQL_Results_TSV"]))

class CompressionEnum(EnumDefinitionImpl):

    GZIP = PermissibleValue(text="GZIP")
    TAR = PermissibleValue(text="TAR")
    TARGZIP = PermissibleValue(text="TARGZIP")
    ZIP = PermissibleValue(text="ZIP")

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

class DataGeneratingProject(EnumDefinitionImpl):
    """
    One of the Bridge2AI Data Generating Projects.
    """
    aireadi = PermissibleValue(
        text="aireadi",
        description="""AI-READI: Uncovering the details of how human health is restored after disease, using type 2 diabetes as a model.""",
        meaning=None)
    chorus = PermissibleValue(
        text="chorus",
        description="""CHoRUS: Collaborative Hospital Repository Uniting Standards. Using imaging, clinical, and other data collected in an ICU setting for diagnosis and risk prediction.""",
        meaning=None)
    cm4ai = PermissibleValue(
        text="cm4ai",
        description="""CM4AI: Cell Maps for AI. Mapping spatiotemporal architecture of human cells to interpret cell structure/function in health and disease.""",
        meaning=None)
    voice = PermissibleValue(
        text="voice",
        description="""Voice as a Biomarker of Health: Building an ethically sourced, bioaccoustic database to understand disease like never before.""",
        meaning=None)

    _defn = EnumDefinition(
        name="DataGeneratingProject",
        description="One of the Bridge2AI Data Generating Projects.",
    )

# Slots
class slots:
    pass

slots.title = Slot(uri=DCTERMS.title, name="title", curie=DCTERMS.curie('title'),
                   model_uri=DATA_SHEETS_SCHEMA.title, domain=None, range=Optional[str])

slots.language = Slot(uri=DATA_SHEETS_SCHEMA.language, name="language", curie=DATA_SHEETS_SCHEMA.curie('language'),
                   model_uri=DATA_SHEETS_SCHEMA.language, domain=None, range=Optional[str])

slots.publisher = Slot(uri=DCTERMS.publisher, name="publisher", curie=DCTERMS.curie('publisher'),
                   model_uri=DATA_SHEETS_SCHEMA.publisher, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.issued = Slot(uri=DCTERMS.issued, name="issued", curie=DCTERMS.curie('issued'),
                   model_uri=DATA_SHEETS_SCHEMA.issued, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.page = Slot(uri=DCAT.landingPage, name="page", curie=DCAT.curie('landingPage'),
                   model_uri=DATA_SHEETS_SCHEMA.page, domain=None, range=Optional[str])

slots.dialect = Slot(uri=CSVW.dialect, name="dialect", curie=CSVW.curie('dialect'),
                   model_uri=DATA_SHEETS_SCHEMA.dialect, domain=None, range=Optional[str])

slots.bytes = Slot(uri=DCAT.byteSize, name="bytes", curie=DCAT.curie('byteSize'),
                   model_uri=DATA_SHEETS_SCHEMA.bytes, domain=None, range=Optional[int])

slots.path = Slot(uri=DATA_SHEETS_SCHEMA.path, name="path", curie=DATA_SHEETS_SCHEMA.curie('path'),
                   model_uri=DATA_SHEETS_SCHEMA.path, domain=None, range=Optional[str])

slots.download_url = Slot(uri=DCAT.downloadURL, name="download_url", curie=DCAT.curie('downloadURL'),
                   model_uri=DATA_SHEETS_SCHEMA.download_url, domain=None, range=Optional[Union[str, URI]])

slots.format = Slot(uri=DCTERMS.format, name="format", curie=DCTERMS.curie('format'),
                   model_uri=DATA_SHEETS_SCHEMA.format, domain=None, range=Optional[Union[str, "FormatEnum"]])

slots.compression = Slot(uri=DATA_SHEETS_SCHEMA.compression, name="compression", curie=DATA_SHEETS_SCHEMA.curie('compression'),
                   model_uri=DATA_SHEETS_SCHEMA.compression, domain=None, range=Optional[Union[str, "CompressionEnum"]])

slots.encoding = Slot(uri=DATA_SHEETS_SCHEMA.encoding, name="encoding", curie=DATA_SHEETS_SCHEMA.curie('encoding'),
                   model_uri=DATA_SHEETS_SCHEMA.encoding, domain=None, range=Optional[Union[str, "EncodingEnum"]])

slots.hash = Slot(uri=DATA_SHEETS_SCHEMA.hash, name="hash", curie=DATA_SHEETS_SCHEMA.curie('hash'),
                   model_uri=DATA_SHEETS_SCHEMA.hash, domain=None, range=Optional[str])

slots.sha256 = Slot(uri=DATA_SHEETS_SCHEMA.sha256, name="sha256", curie=DATA_SHEETS_SCHEMA.curie('sha256'),
                   model_uri=DATA_SHEETS_SCHEMA.sha256, domain=None, range=Optional[str])

slots.md5 = Slot(uri=DATA_SHEETS_SCHEMA.md5, name="md5", curie=DATA_SHEETS_SCHEMA.curie('md5'),
                   model_uri=DATA_SHEETS_SCHEMA.md5, domain=None, range=Optional[str])

slots.media_type = Slot(uri=DCAT.mediaType, name="media_type", curie=DCAT.curie('mediaType'),
                   model_uri=DATA_SHEETS_SCHEMA.media_type, domain=None, range=Optional[str])

slots.conforms_to = Slot(uri=DCTERMS.conformsTo, name="conforms_to", curie=DCTERMS.curie('conformsTo'),
                   model_uri=DATA_SHEETS_SCHEMA.conforms_to, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.conforms_to_schema = Slot(uri=DATA_SHEETS_SCHEMA.conforms_to_schema, name="conforms_to_schema", curie=DATA_SHEETS_SCHEMA.curie('conforms_to_schema'),
                   model_uri=DATA_SHEETS_SCHEMA.conforms_to_schema, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.conforms_to_class = Slot(uri=DATA_SHEETS_SCHEMA.conforms_to_class, name="conforms_to_class", curie=DATA_SHEETS_SCHEMA.curie('conforms_to_class'),
                   model_uri=DATA_SHEETS_SCHEMA.conforms_to_class, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.doi = Slot(uri=DATA_SHEETS_SCHEMA.doi, name="doi", curie=DATA_SHEETS_SCHEMA.curie('doi'),
                   model_uri=DATA_SHEETS_SCHEMA.doi, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.profile = Slot(uri=DATA_SHEETS_SCHEMA.profile, name="profile", curie=DATA_SHEETS_SCHEMA.curie('profile'),
                   model_uri=DATA_SHEETS_SCHEMA.profile, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.keywords = Slot(uri=DCAT.keyword, name="keywords", curie=DCAT.curie('keyword'),
                   model_uri=DATA_SHEETS_SCHEMA.keywords, domain=None, range=Optional[Union[str, List[str]]])

slots.themes = Slot(uri=DCAT.theme, name="themes", curie=DCAT.curie('theme'),
                   model_uri=DATA_SHEETS_SCHEMA.themes, domain=None, range=Optional[Union[Union[str, URIorCURIE], List[Union[str, URIorCURIE]]]])

slots.created_by = Slot(uri=PAV.createdBy, name="created_by", curie=PAV.curie('createdBy'),
                   model_uri=DATA_SHEETS_SCHEMA.created_by, domain=None, range=Optional[Union[Union[str, "CreatorOrMaintainerEnum"], List[Union[str, "CreatorOrMaintainerEnum"]]]])

slots.created_on = Slot(uri=PAV.createdOn, name="created_on", curie=PAV.curie('createdOn'),
                   model_uri=DATA_SHEETS_SCHEMA.created_on, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.last_updated_on = Slot(uri=PAV.lastUpdatedOn, name="last_updated_on", curie=PAV.curie('lastUpdatedOn'),
                   model_uri=DATA_SHEETS_SCHEMA.last_updated_on, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.modified_by = Slot(uri=OSLC.modifiedBy, name="modified_by", curie=OSLC.curie('modifiedBy'),
                   model_uri=DATA_SHEETS_SCHEMA.modified_by, domain=None, range=Optional[Union[str, "CreatorOrMaintainerEnum"]])

slots.status = Slot(uri=BIBO.status, name="status", curie=BIBO.curie('status'),
                   model_uri=DATA_SHEETS_SCHEMA.status, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.license = Slot(uri=DCTERMS.license, name="license", curie=DCTERMS.curie('license'),
                   model_uri=DATA_SHEETS_SCHEMA.license, domain=None, range=Optional[str])

slots.version = Slot(uri=PAV.version, name="version", curie=PAV.curie('version'),
                   model_uri=DATA_SHEETS_SCHEMA.version, domain=None, range=Optional[str])

slots.was_derived_from = Slot(uri=PROV.wasDerivedFrom, name="was_derived_from", curie=PROV.curie('wasDerivedFrom'),
                   model_uri=DATA_SHEETS_SCHEMA.was_derived_from, domain=None, range=Optional[str])

slots.node_property = Slot(uri=B2AI.node_property, name="node_property", curie=B2AI.curie('node_property'),
                   model_uri=DATA_SHEETS_SCHEMA.node_property, domain=NamedThing, range=Optional[str])

slots.id = Slot(uri=SCHEMA.identifier, name="id", curie=SCHEMA.curie('identifier'),
                   model_uri=DATA_SHEETS_SCHEMA.id, domain=None, range=URIRef)

slots.type = Slot(uri=B2AI.type, name="type", curie=B2AI.curie('type'),
                   model_uri=DATA_SHEETS_SCHEMA.type, domain=NamedThing, range=Optional[str])

slots.category = Slot(uri=B2AI.category, name="category", curie=B2AI.curie('category'),
                   model_uri=DATA_SHEETS_SCHEMA.category, domain=NamedThing, range=Optional[Union[str, CategoryType]])

slots.name = Slot(uri=SCHEMA.name, name="name", curie=SCHEMA.curie('name'),
                   model_uri=DATA_SHEETS_SCHEMA.name, domain=None, range=Optional[str])

slots.description = Slot(uri=SCHEMA.description, name="description", curie=SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.description, domain=None, range=Optional[str])

slots.edam_id = Slot(uri=B2AI.edam_id, name="edam_id", curie=B2AI.curie('edam_id'),
                   model_uri=DATA_SHEETS_SCHEMA.edam_id, domain=None, range=Optional[Union[str, EdamIdentifier]])

slots.mesh_id = Slot(uri=B2AI.mesh_id, name="mesh_id", curie=B2AI.curie('mesh_id'),
                   model_uri=DATA_SHEETS_SCHEMA.mesh_id, domain=None, range=Optional[Union[str, MeshIdentifier]])

slots.ncit_id = Slot(uri=B2AI.ncit_id, name="ncit_id", curie=B2AI.curie('ncit_id'),
                   model_uri=DATA_SHEETS_SCHEMA.ncit_id, domain=None, range=Optional[Union[str, NcitIdentifier]])

slots.url = Slot(uri=B2AI.url, name="url", curie=B2AI.curie('url'),
                   model_uri=DATA_SHEETS_SCHEMA.url, domain=NamedThing, range=Optional[Union[str, URIorCURIE]])

slots.xref = Slot(uri=B2AI.xref, name="xref", curie=B2AI.curie('xref'),
                   model_uri=DATA_SHEETS_SCHEMA.xref, domain=NamedThing, range=Optional[Union[Union[str, URIorCURIE], List[Union[str, URIorCURIE]]]])

slots.contributor_name = Slot(uri=B2AI.contributor_name, name="contributor_name", curie=B2AI.curie('contributor_name'),
                   model_uri=DATA_SHEETS_SCHEMA.contributor_name, domain=NamedThing, range=Optional[str])

slots.contributor_github_name = Slot(uri=B2AI.contributor_github_name, name="contributor_github_name", curie=B2AI.curie('contributor_github_name'),
                   model_uri=DATA_SHEETS_SCHEMA.contributor_github_name, domain=NamedThing, range=Optional[str])

slots.contributor_orcid = Slot(uri=B2AI.contributor_orcid, name="contributor_orcid", curie=B2AI.curie('contributor_orcid'),
                   model_uri=DATA_SHEETS_SCHEMA.contributor_orcid, domain=NamedThing, range=Optional[Union[str, URIorCURIE]])

slots.contribution_date = Slot(uri=B2AI.contribution_date, name="contribution_date", curie=B2AI.curie('contribution_date'),
                   model_uri=DATA_SHEETS_SCHEMA.contribution_date, domain=NamedThing, range=Optional[Union[str, XSDDate]])

slots.related_to = Slot(uri=B2AI.related_to, name="related_to", curie=B2AI.curie('related_to'),
                   model_uri=DATA_SHEETS_SCHEMA.related_to, domain=NamedThing, range=Optional[Union[Union[str, NamedThingId], List[Union[str, NamedThingId]]]])

slots.subclass_of = Slot(uri=B2AI.subclass_of, name="subclass_of", curie=B2AI.curie('subclass_of'),
                   model_uri=DATA_SHEETS_SCHEMA.subclass_of, domain=NamedThing, range=Optional[Union[Union[str, NamedThingId], List[Union[str, NamedThingId]]]])

slots.ror_id = Slot(uri=B2AI_ORG.ror_id, name="ror_id", curie=B2AI_ORG.curie('ror_id'),
                   model_uri=DATA_SHEETS_SCHEMA.ror_id, domain=None, range=Optional[Union[str, RorIdentifier]])

slots.wikidata_id = Slot(uri=B2AI_ORG.wikidata_id, name="wikidata_id", curie=B2AI_ORG.curie('wikidata_id'),
                   model_uri=DATA_SHEETS_SCHEMA.wikidata_id, domain=None, range=Optional[Union[str, WikidataIdentifier]])

slots.organizations = Slot(uri=B2AI_ORG.organizations, name="organizations", curie=B2AI_ORG.curie('organizations'),
                   model_uri=DATA_SHEETS_SCHEMA.organizations, domain=None, range=Optional[Union[Dict[Union[str, OrganizationId], Union[dict, Organization]], List[Union[dict, Organization]]]])

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

slots.person__affiliation = Slot(uri=DATA_SHEETS_SCHEMA.affiliation, name="person__affiliation", curie=DATA_SHEETS_SCHEMA.curie('affiliation'),
                   model_uri=DATA_SHEETS_SCHEMA.person__affiliation, domain=None, range=Optional[Union[Union[str, OrganizationId], List[Union[str, OrganizationId]]]])

slots.person__email = Slot(uri=DATA_SHEETS_SCHEMA.email, name="person__email", curie=DATA_SHEETS_SCHEMA.curie('email'),
                   model_uri=DATA_SHEETS_SCHEMA.person__email, domain=None, range=Optional[str])

slots.datasetProperty__used_software = Slot(uri=DATA_SHEETS_SCHEMA.used_software, name="datasetProperty__used_software", curie=DATA_SHEETS_SCHEMA.curie('used_software'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetProperty__used_software, domain=None, range=Optional[Union[Union[str, SoftwareId], List[Union[str, SoftwareId]]]])

slots.datasetCollection__resources = Slot(uri=DATA_SHEETS_SCHEMA.resources, name="datasetCollection__resources", curie=DATA_SHEETS_SCHEMA.curie('resources'),
                   model_uri=DATA_SHEETS_SCHEMA.datasetCollection__resources, domain=None, range=Optional[Union[Union[str, DatasetId], List[Union[str, DatasetId]]]])

slots.dataset__purposes = Slot(uri=DATA_SHEETS_SCHEMA.purposes, name="dataset__purposes", curie=DATA_SHEETS_SCHEMA.curie('purposes'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__purposes, domain=None, range=Optional[Union[Union[str, PurposeId], List[Union[str, PurposeId]]]])

slots.dataset__tasks = Slot(uri=DATA_SHEETS_SCHEMA.tasks, name="dataset__tasks", curie=DATA_SHEETS_SCHEMA.curie('tasks'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__tasks, domain=None, range=Optional[Union[Union[str, TaskId], List[Union[str, TaskId]]]])

slots.dataset__addressing_gaps = Slot(uri=DATA_SHEETS_SCHEMA.addressing_gaps, name="dataset__addressing_gaps", curie=DATA_SHEETS_SCHEMA.curie('addressing_gaps'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__addressing_gaps, domain=None, range=Optional[Union[Union[str, AddressingGapId], List[Union[str, AddressingGapId]]]])

slots.dataset__creators = Slot(uri=DATA_SHEETS_SCHEMA.creators, name="dataset__creators", curie=DATA_SHEETS_SCHEMA.curie('creators'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__creators, domain=None, range=Optional[Union[Union[str, CreatorId], List[Union[str, CreatorId]]]])

slots.dataset__funders = Slot(uri=DATA_SHEETS_SCHEMA.funders, name="dataset__funders", curie=DATA_SHEETS_SCHEMA.curie('funders'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__funders, domain=None, range=Optional[Union[Union[str, FundingMechanismId], List[Union[str, FundingMechanismId]]]])

slots.dataset__subsets = Slot(uri=DCAT.distribution, name="dataset__subsets", curie=DCAT.curie('distribution'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__subsets, domain=None, range=Optional[Union[Union[str, DataSubsetId], List[Union[str, DataSubsetId]]]])

slots.dataset__instances = Slot(uri=DATA_SHEETS_SCHEMA.instances, name="dataset__instances", curie=DATA_SHEETS_SCHEMA.curie('instances'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__instances, domain=None, range=Optional[Union[Union[str, InstanceId], List[Union[str, InstanceId]]]])

slots.dataset__anomalies = Slot(uri=DATA_SHEETS_SCHEMA.anomalies, name="dataset__anomalies", curie=DATA_SHEETS_SCHEMA.curie('anomalies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__anomalies, domain=None, range=Optional[Union[Union[str, DataAnomalyId], List[Union[str, DataAnomalyId]]]])

slots.dataset__external_resources = Slot(uri=DATA_SHEETS_SCHEMA.external_resources, name="dataset__external_resources", curie=DATA_SHEETS_SCHEMA.curie('external_resources'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__external_resources, domain=None, range=Optional[Union[Union[str, ExternalResourceId], List[Union[str, ExternalResourceId]]]])

slots.dataset__confidential_elements = Slot(uri=DATA_SHEETS_SCHEMA.confidential_elements, name="dataset__confidential_elements", curie=DATA_SHEETS_SCHEMA.curie('confidential_elements'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__confidential_elements, domain=None, range=Optional[Union[Union[str, ConfidentialityId], List[Union[str, ConfidentialityId]]]])

slots.dataset__content_warnings = Slot(uri=DATA_SHEETS_SCHEMA.content_warnings, name="dataset__content_warnings", curie=DATA_SHEETS_SCHEMA.curie('content_warnings'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__content_warnings, domain=None, range=Optional[Union[Union[str, ContentWarningId], List[Union[str, ContentWarningId]]]])

slots.dataset__subpopulations = Slot(uri=DATA_SHEETS_SCHEMA.subpopulations, name="dataset__subpopulations", curie=DATA_SHEETS_SCHEMA.curie('subpopulations'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__subpopulations, domain=None, range=Optional[Union[Union[str, SubpopulationId], List[Union[str, SubpopulationId]]]])

slots.dataset__sensitive_elements = Slot(uri=DATA_SHEETS_SCHEMA.sensitive_elements, name="dataset__sensitive_elements", curie=DATA_SHEETS_SCHEMA.curie('sensitive_elements'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__sensitive_elements, domain=None, range=Optional[Union[Union[str, SensitiveElementId], List[Union[str, SensitiveElementId]]]])

slots.dataset__acquisition_methods = Slot(uri=DATA_SHEETS_SCHEMA.acquisition_methods, name="dataset__acquisition_methods", curie=DATA_SHEETS_SCHEMA.curie('acquisition_methods'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__acquisition_methods, domain=None, range=Optional[Union[Union[str, InstanceAcquisitionId], List[Union[str, InstanceAcquisitionId]]]])

slots.dataset__collection_mechanisms = Slot(uri=DATA_SHEETS_SCHEMA.collection_mechanisms, name="dataset__collection_mechanisms", curie=DATA_SHEETS_SCHEMA.curie('collection_mechanisms'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__collection_mechanisms, domain=None, range=Optional[Union[Union[str, CollectionMechanismId], List[Union[str, CollectionMechanismId]]]])

slots.dataset__sampling_strategies = Slot(uri=DATA_SHEETS_SCHEMA.sampling_strategies, name="dataset__sampling_strategies", curie=DATA_SHEETS_SCHEMA.curie('sampling_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__sampling_strategies, domain=None, range=Optional[Union[Union[str, SamplingStrategyId], List[Union[str, SamplingStrategyId]]]])

slots.dataset__data_collectors = Slot(uri=DATA_SHEETS_SCHEMA.data_collectors, name="dataset__data_collectors", curie=DATA_SHEETS_SCHEMA.curie('data_collectors'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__data_collectors, domain=None, range=Optional[Union[Union[str, DataCollectorId], List[Union[str, DataCollectorId]]]])

slots.dataset__collection_timeframes = Slot(uri=DATA_SHEETS_SCHEMA.collection_timeframes, name="dataset__collection_timeframes", curie=DATA_SHEETS_SCHEMA.curie('collection_timeframes'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__collection_timeframes, domain=None, range=Optional[Union[Union[str, CollectionTimeframeId], List[Union[str, CollectionTimeframeId]]]])

slots.dataset__ethical_reviews = Slot(uri=DATA_SHEETS_SCHEMA.ethical_reviews, name="dataset__ethical_reviews", curie=DATA_SHEETS_SCHEMA.curie('ethical_reviews'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__ethical_reviews, domain=None, range=Optional[Union[Union[str, EthicalReviewId], List[Union[str, EthicalReviewId]]]])

slots.dataset__data_protection_impacts = Slot(uri=DATA_SHEETS_SCHEMA.data_protection_impacts, name="dataset__data_protection_impacts", curie=DATA_SHEETS_SCHEMA.curie('data_protection_impacts'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__data_protection_impacts, domain=None, range=Optional[Union[Union[str, DataProtectionImpactId], List[Union[str, DataProtectionImpactId]]]])

slots.dataset__preprocessing_strategies = Slot(uri=DATA_SHEETS_SCHEMA.preprocessing_strategies, name="dataset__preprocessing_strategies", curie=DATA_SHEETS_SCHEMA.curie('preprocessing_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__preprocessing_strategies, domain=None, range=Optional[Union[Union[str, PreprocessingStrategyId], List[Union[str, PreprocessingStrategyId]]]])

slots.dataset__cleaning_strategies = Slot(uri=DATA_SHEETS_SCHEMA.cleaning_strategies, name="dataset__cleaning_strategies", curie=DATA_SHEETS_SCHEMA.curie('cleaning_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__cleaning_strategies, domain=None, range=Optional[Union[Union[str, CleaningStrategyId], List[Union[str, CleaningStrategyId]]]])

slots.dataset__labeling_strategies = Slot(uri=DATA_SHEETS_SCHEMA.labeling_strategies, name="dataset__labeling_strategies", curie=DATA_SHEETS_SCHEMA.curie('labeling_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__labeling_strategies, domain=None, range=Optional[Union[Union[str, LabelingStrategyId], List[Union[str, LabelingStrategyId]]]])

slots.dataset__raw_sources = Slot(uri=DATA_SHEETS_SCHEMA.raw_sources, name="dataset__raw_sources", curie=DATA_SHEETS_SCHEMA.curie('raw_sources'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__raw_sources, domain=None, range=Optional[Union[Union[str, RawDataId], List[Union[str, RawDataId]]]])

slots.dataset__existing_uses = Slot(uri=DATA_SHEETS_SCHEMA.existing_uses, name="dataset__existing_uses", curie=DATA_SHEETS_SCHEMA.curie('existing_uses'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__existing_uses, domain=None, range=Optional[Union[Union[str, ExistingUseId], List[Union[str, ExistingUseId]]]])

slots.dataset__use_repository = Slot(uri=DATA_SHEETS_SCHEMA.use_repository, name="dataset__use_repository", curie=DATA_SHEETS_SCHEMA.curie('use_repository'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__use_repository, domain=None, range=Optional[Union[Union[str, UseRepositoryId], List[Union[str, UseRepositoryId]]]])

slots.dataset__other_tasks = Slot(uri=DATA_SHEETS_SCHEMA.other_tasks, name="dataset__other_tasks", curie=DATA_SHEETS_SCHEMA.curie('other_tasks'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__other_tasks, domain=None, range=Optional[Union[Union[str, OtherTaskId], List[Union[str, OtherTaskId]]]])

slots.dataset__future_use_impacts = Slot(uri=DATA_SHEETS_SCHEMA.future_use_impacts, name="dataset__future_use_impacts", curie=DATA_SHEETS_SCHEMA.curie('future_use_impacts'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__future_use_impacts, domain=None, range=Optional[Union[Union[str, FutureUseImpactId], List[Union[str, FutureUseImpactId]]]])

slots.dataset__discouraged_uses = Slot(uri=DATA_SHEETS_SCHEMA.discouraged_uses, name="dataset__discouraged_uses", curie=DATA_SHEETS_SCHEMA.curie('discouraged_uses'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__discouraged_uses, domain=None, range=Optional[Union[Union[str, DiscouragedUseId], List[Union[str, DiscouragedUseId]]]])

slots.dataset__distribution_formats = Slot(uri=DATA_SHEETS_SCHEMA.distribution_formats, name="dataset__distribution_formats", curie=DATA_SHEETS_SCHEMA.curie('distribution_formats'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__distribution_formats, domain=None, range=Optional[Union[Union[str, DistributionFormatId], List[Union[str, DistributionFormatId]]]])

slots.dataset__distribution_dates = Slot(uri=DATA_SHEETS_SCHEMA.distribution_dates, name="dataset__distribution_dates", curie=DATA_SHEETS_SCHEMA.curie('distribution_dates'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__distribution_dates, domain=None, range=Optional[Union[Union[str, DistributionDateId], List[Union[str, DistributionDateId]]]])

slots.dataset__license_and_use_terms = Slot(uri=DATA_SHEETS_SCHEMA.license_and_use_terms, name="dataset__license_and_use_terms", curie=DATA_SHEETS_SCHEMA.curie('license_and_use_terms'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__license_and_use_terms, domain=None, range=Optional[Union[str, LicenseAndUseTermsId]])

slots.dataset__ip_restrictions = Slot(uri=DATA_SHEETS_SCHEMA.ip_restrictions, name="dataset__ip_restrictions", curie=DATA_SHEETS_SCHEMA.curie('ip_restrictions'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__ip_restrictions, domain=None, range=Optional[Union[str, IPRestrictionsId]])

slots.dataset__regulatory_restrictions = Slot(uri=DATA_SHEETS_SCHEMA.regulatory_restrictions, name="dataset__regulatory_restrictions", curie=DATA_SHEETS_SCHEMA.curie('regulatory_restrictions'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__regulatory_restrictions, domain=None, range=Optional[Union[str, ExportControlRegulatoryRestrictionsId]])

slots.dataset__maintainers = Slot(uri=DATA_SHEETS_SCHEMA.maintainers, name="dataset__maintainers", curie=DATA_SHEETS_SCHEMA.curie('maintainers'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__maintainers, domain=None, range=Optional[Union[Union[str, MaintainerId], List[Union[str, MaintainerId]]]])

slots.dataset__errata = Slot(uri=DATA_SHEETS_SCHEMA.errata, name="dataset__errata", curie=DATA_SHEETS_SCHEMA.curie('errata'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__errata, domain=None, range=Optional[Union[Union[str, ErratumId], List[Union[str, ErratumId]]]])

slots.dataset__updates = Slot(uri=DATA_SHEETS_SCHEMA.updates, name="dataset__updates", curie=DATA_SHEETS_SCHEMA.curie('updates'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__updates, domain=None, range=Optional[Union[str, UpdatePlanId]])

slots.dataset__retention_limit = Slot(uri=DATA_SHEETS_SCHEMA.retention_limit, name="dataset__retention_limit", curie=DATA_SHEETS_SCHEMA.curie('retention_limit'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__retention_limit, domain=None, range=Optional[Union[str, RetentionLimitsId]])

slots.dataset__version_access = Slot(uri=DATA_SHEETS_SCHEMA.version_access, name="dataset__version_access", curie=DATA_SHEETS_SCHEMA.curie('version_access'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__version_access, domain=None, range=Optional[Union[str, VersionAccessId]])

slots.dataset__extension_mechanism = Slot(uri=DATA_SHEETS_SCHEMA.extension_mechanism, name="dataset__extension_mechanism", curie=DATA_SHEETS_SCHEMA.curie('extension_mechanism'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__extension_mechanism, domain=None, range=Optional[Union[str, ExtensionMechanismId]])

slots.dataset__is_deidentified = Slot(uri=DATA_SHEETS_SCHEMA.is_deidentified, name="dataset__is_deidentified", curie=DATA_SHEETS_SCHEMA.curie('is_deidentified'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__is_deidentified, domain=None, range=Optional[Union[str, DeidentificationId]])

slots.dataset__is_tabular = Slot(uri=DATA_SHEETS_SCHEMA.is_tabular, name="dataset__is_tabular", curie=DATA_SHEETS_SCHEMA.curie('is_tabular'),
                   model_uri=DATA_SHEETS_SCHEMA.dataset__is_tabular, domain=None, range=Optional[Union[bool, Bool]])

slots.dataSubset__is_data_split = Slot(uri=DATA_SHEETS_SCHEMA.is_data_split, name="dataSubset__is_data_split", curie=DATA_SHEETS_SCHEMA.curie('is_data_split'),
                   model_uri=DATA_SHEETS_SCHEMA.dataSubset__is_data_split, domain=None, range=Optional[Union[bool, Bool]])

slots.dataSubset__is_subpopulation = Slot(uri=DATA_SHEETS_SCHEMA.is_subpopulation, name="dataSubset__is_subpopulation", curie=DATA_SHEETS_SCHEMA.curie('is_subpopulation'),
                   model_uri=DATA_SHEETS_SCHEMA.dataSubset__is_subpopulation, domain=None, range=Optional[Union[bool, Bool]])

slots.software__version = Slot(uri=DATA_SHEETS_SCHEMA.version, name="software__version", curie=DATA_SHEETS_SCHEMA.curie('version'),
                   model_uri=DATA_SHEETS_SCHEMA.software__version, domain=None, range=Optional[str])

slots.software__license = Slot(uri=DATA_SHEETS_SCHEMA.license, name="software__license", curie=DATA_SHEETS_SCHEMA.curie('license'),
                   model_uri=DATA_SHEETS_SCHEMA.software__license, domain=None, range=Optional[str])

slots.software__url = Slot(uri=DATA_SHEETS_SCHEMA.url, name="software__url", curie=DATA_SHEETS_SCHEMA.curie('url'),
                   model_uri=DATA_SHEETS_SCHEMA.software__url, domain=None, range=Optional[str])

slots.purpose__response = Slot(uri=DATA_SHEETS_SCHEMA.response, name="purpose__response", curie=DATA_SHEETS_SCHEMA.curie('response'),
                   model_uri=DATA_SHEETS_SCHEMA.purpose__response, domain=None, range=Optional[str])

slots.task__response = Slot(uri=DATA_SHEETS_SCHEMA.response, name="task__response", curie=DATA_SHEETS_SCHEMA.curie('response'),
                   model_uri=DATA_SHEETS_SCHEMA.task__response, domain=None, range=Optional[str])

slots.addressingGap__response = Slot(uri=DATA_SHEETS_SCHEMA.response, name="addressingGap__response", curie=DATA_SHEETS_SCHEMA.curie('response'),
                   model_uri=DATA_SHEETS_SCHEMA.addressingGap__response, domain=None, range=Optional[str])

slots.creator__principal_investigator = Slot(uri=DATA_SHEETS_SCHEMA.principal_investigator, name="creator__principal_investigator", curie=DATA_SHEETS_SCHEMA.curie('principal_investigator'),
                   model_uri=DATA_SHEETS_SCHEMA.creator__principal_investigator, domain=None, range=Optional[Union[str, PersonId]])

slots.creator__affiliation = Slot(uri=DATA_SHEETS_SCHEMA.affiliation, name="creator__affiliation", curie=DATA_SHEETS_SCHEMA.curie('affiliation'),
                   model_uri=DATA_SHEETS_SCHEMA.creator__affiliation, domain=None, range=Optional[Union[str, OrganizationId]])

slots.fundingMechanism__grantor = Slot(uri=DATA_SHEETS_SCHEMA.grantor, name="fundingMechanism__grantor", curie=DATA_SHEETS_SCHEMA.curie('grantor'),
                   model_uri=DATA_SHEETS_SCHEMA.fundingMechanism__grantor, domain=None, range=Optional[Union[str, GrantorId]])

slots.fundingMechanism__grant = Slot(uri=DATA_SHEETS_SCHEMA.grant, name="fundingMechanism__grant", curie=DATA_SHEETS_SCHEMA.curie('grant'),
                   model_uri=DATA_SHEETS_SCHEMA.fundingMechanism__grant, domain=None, range=Optional[Union[str, GrantId]])

slots.grant__grant_number = Slot(uri=DATA_SHEETS_SCHEMA.grant_number, name="grant__grant_number", curie=DATA_SHEETS_SCHEMA.curie('grant_number'),
                   model_uri=DATA_SHEETS_SCHEMA.grant__grant_number, domain=None, range=Optional[str])

slots.instance__data_topic = Slot(uri=DATA_SHEETS_SCHEMA.data_topic, name="instance__data_topic", curie=DATA_SHEETS_SCHEMA.curie('data_topic'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__data_topic, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.instance__instance_type = Slot(uri=DATA_SHEETS_SCHEMA.instance_type, name="instance__instance_type", curie=DATA_SHEETS_SCHEMA.curie('instance_type'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__instance_type, domain=None, range=Optional[str])

slots.instance__data_substrate = Slot(uri=DATA_SHEETS_SCHEMA.data_substrate, name="instance__data_substrate", curie=DATA_SHEETS_SCHEMA.curie('data_substrate'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__data_substrate, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.instance__counts = Slot(uri=DATA_SHEETS_SCHEMA.counts, name="instance__counts", curie=DATA_SHEETS_SCHEMA.curie('counts'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__counts, domain=None, range=Optional[int])

slots.instance__label = Slot(uri=DATA_SHEETS_SCHEMA.label, name="instance__label", curie=DATA_SHEETS_SCHEMA.curie('label'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__label, domain=None, range=Optional[Union[bool, Bool]])

slots.instance__label_description = Slot(uri=DATA_SHEETS_SCHEMA.label_description, name="instance__label_description", curie=DATA_SHEETS_SCHEMA.curie('label_description'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__label_description, domain=None, range=Optional[str])

slots.instance__sampling_strategies = Slot(uri=DATA_SHEETS_SCHEMA.sampling_strategies, name="instance__sampling_strategies", curie=DATA_SHEETS_SCHEMA.curie('sampling_strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__sampling_strategies, domain=None, range=Optional[Union[Union[str, SamplingStrategyId], List[Union[str, SamplingStrategyId]]]])

slots.instance__missing_information = Slot(uri=DATA_SHEETS_SCHEMA.missing_information, name="instance__missing_information", curie=DATA_SHEETS_SCHEMA.curie('missing_information'),
                   model_uri=DATA_SHEETS_SCHEMA.instance__missing_information, domain=None, range=Optional[Union[Union[str, MissingInfoId], List[Union[str, MissingInfoId]]]])

slots.samplingStrategy__is_sample = Slot(uri=DATA_SHEETS_SCHEMA.is_sample, name="samplingStrategy__is_sample", curie=DATA_SHEETS_SCHEMA.curie('is_sample'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__is_sample, domain=None, range=Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]])

slots.samplingStrategy__is_random = Slot(uri=DATA_SHEETS_SCHEMA.is_random, name="samplingStrategy__is_random", curie=DATA_SHEETS_SCHEMA.curie('is_random'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__is_random, domain=None, range=Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]])

slots.samplingStrategy__source_data = Slot(uri=DATA_SHEETS_SCHEMA.source_data, name="samplingStrategy__source_data", curie=DATA_SHEETS_SCHEMA.curie('source_data'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__source_data, domain=None, range=Optional[Union[str, List[str]]])

slots.samplingStrategy__is_representative = Slot(uri=DATA_SHEETS_SCHEMA.is_representative, name="samplingStrategy__is_representative", curie=DATA_SHEETS_SCHEMA.curie('is_representative'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__is_representative, domain=None, range=Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]])

slots.samplingStrategy__representative_verification = Slot(uri=DATA_SHEETS_SCHEMA.representative_verification, name="samplingStrategy__representative_verification", curie=DATA_SHEETS_SCHEMA.curie('representative_verification'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__representative_verification, domain=None, range=Optional[Union[str, List[str]]])

slots.samplingStrategy__why_not_representative = Slot(uri=DATA_SHEETS_SCHEMA.why_not_representative, name="samplingStrategy__why_not_representative", curie=DATA_SHEETS_SCHEMA.curie('why_not_representative'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__why_not_representative, domain=None, range=Optional[Union[str, List[str]]])

slots.samplingStrategy__strategies = Slot(uri=DATA_SHEETS_SCHEMA.strategies, name="samplingStrategy__strategies", curie=DATA_SHEETS_SCHEMA.curie('strategies'),
                   model_uri=DATA_SHEETS_SCHEMA.samplingStrategy__strategies, domain=None, range=Optional[Union[str, List[str]]])

slots.missingInfo__missing = Slot(uri=DATA_SHEETS_SCHEMA.missing, name="missingInfo__missing", curie=DATA_SHEETS_SCHEMA.curie('missing'),
                   model_uri=DATA_SHEETS_SCHEMA.missingInfo__missing, domain=None, range=Optional[Union[str, List[str]]])

slots.missingInfo__why_missing = Slot(uri=DATA_SHEETS_SCHEMA.why_missing, name="missingInfo__why_missing", curie=DATA_SHEETS_SCHEMA.curie('why_missing'),
                   model_uri=DATA_SHEETS_SCHEMA.missingInfo__why_missing, domain=None, range=Optional[Union[str, List[str]]])

slots.relationships__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="relationships__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.relationships__description, domain=None, range=Optional[Union[str, List[str]]])

slots.splits__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="splits__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.splits__description, domain=None, range=Optional[Union[str, List[str]]])

slots.dataAnomaly__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="dataAnomaly__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.dataAnomaly__description, domain=None, range=Optional[Union[str, List[str]]])

slots.externalResource__external_resources = Slot(uri=DATA_SHEETS_SCHEMA.external_resources, name="externalResource__external_resources", curie=DATA_SHEETS_SCHEMA.curie('external_resources'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__external_resources, domain=None, range=Optional[Union[str, List[str]]])

slots.externalResource__future_guarantees = Slot(uri=DATA_SHEETS_SCHEMA.future_guarantees, name="externalResource__future_guarantees", curie=DATA_SHEETS_SCHEMA.curie('future_guarantees'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__future_guarantees, domain=None, range=Optional[Union[str, List[str]]])

slots.externalResource__archival = Slot(uri=DATA_SHEETS_SCHEMA.archival, name="externalResource__archival", curie=DATA_SHEETS_SCHEMA.curie('archival'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__archival, domain=None, range=Optional[Union[Union[bool, Bool], List[Union[bool, Bool]]]])

slots.externalResource__restrictions = Slot(uri=DATA_SHEETS_SCHEMA.restrictions, name="externalResource__restrictions", curie=DATA_SHEETS_SCHEMA.curie('restrictions'),
                   model_uri=DATA_SHEETS_SCHEMA.externalResource__restrictions, domain=None, range=Optional[Union[str, List[str]]])

slots.confidentiality__confidential_elements_present = Slot(uri=DATA_SHEETS_SCHEMA.confidential_elements_present, name="confidentiality__confidential_elements_present", curie=DATA_SHEETS_SCHEMA.curie('confidential_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.confidentiality__confidential_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.confidentiality__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="confidentiality__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.confidentiality__description, domain=None, range=Optional[Union[str, List[str]]])

slots.contentWarning__content_warnings_present = Slot(uri=DATA_SHEETS_SCHEMA.content_warnings_present, name="contentWarning__content_warnings_present", curie=DATA_SHEETS_SCHEMA.curie('content_warnings_present'),
                   model_uri=DATA_SHEETS_SCHEMA.contentWarning__content_warnings_present, domain=None, range=Optional[Union[bool, Bool]])

slots.contentWarning__warnings = Slot(uri=DATA_SHEETS_SCHEMA.warnings, name="contentWarning__warnings", curie=DATA_SHEETS_SCHEMA.curie('warnings'),
                   model_uri=DATA_SHEETS_SCHEMA.contentWarning__warnings, domain=None, range=Optional[Union[str, List[str]]])

slots.subpopulation__subpopulation_elements_present = Slot(uri=DATA_SHEETS_SCHEMA.subpopulation_elements_present, name="subpopulation__subpopulation_elements_present", curie=DATA_SHEETS_SCHEMA.curie('subpopulation_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.subpopulation__subpopulation_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.subpopulation__identification = Slot(uri=DATA_SHEETS_SCHEMA.identification, name="subpopulation__identification", curie=DATA_SHEETS_SCHEMA.curie('identification'),
                   model_uri=DATA_SHEETS_SCHEMA.subpopulation__identification, domain=None, range=Optional[Union[str, List[str]]])

slots.subpopulation__distribution = Slot(uri=DATA_SHEETS_SCHEMA.distribution, name="subpopulation__distribution", curie=DATA_SHEETS_SCHEMA.curie('distribution'),
                   model_uri=DATA_SHEETS_SCHEMA.subpopulation__distribution, domain=None, range=Optional[Union[str, List[str]]])

slots.deidentification__identifiable_elements_present = Slot(uri=DATA_SHEETS_SCHEMA.identifiable_elements_present, name="deidentification__identifiable_elements_present", curie=DATA_SHEETS_SCHEMA.curie('identifiable_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.deidentification__identifiable_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.deidentification__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="deidentification__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.deidentification__description, domain=None, range=Optional[Union[str, List[str]]])

slots.sensitiveElement__sensitive_elements_present = Slot(uri=DATA_SHEETS_SCHEMA.sensitive_elements_present, name="sensitiveElement__sensitive_elements_present", curie=DATA_SHEETS_SCHEMA.curie('sensitive_elements_present'),
                   model_uri=DATA_SHEETS_SCHEMA.sensitiveElement__sensitive_elements_present, domain=None, range=Optional[Union[bool, Bool]])

slots.sensitiveElement__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="sensitiveElement__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.sensitiveElement__description, domain=None, range=Optional[Union[str, List[str]]])

slots.instanceAcquisition__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="instanceAcquisition__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__description, domain=None, range=Optional[Union[str, List[str]]])

slots.instanceAcquisition__was_directly_observed = Slot(uri=DATA_SHEETS_SCHEMA.was_directly_observed, name="instanceAcquisition__was_directly_observed", curie=DATA_SHEETS_SCHEMA.curie('was_directly_observed'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_directly_observed, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__was_reported_by_subjects = Slot(uri=DATA_SHEETS_SCHEMA.was_reported_by_subjects, name="instanceAcquisition__was_reported_by_subjects", curie=DATA_SHEETS_SCHEMA.curie('was_reported_by_subjects'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_reported_by_subjects, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__was_inferred_derived = Slot(uri=DATA_SHEETS_SCHEMA.was_inferred_derived, name="instanceAcquisition__was_inferred_derived", curie=DATA_SHEETS_SCHEMA.curie('was_inferred_derived'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_inferred_derived, domain=None, range=Optional[Union[bool, Bool]])

slots.instanceAcquisition__was_validated_verified = Slot(uri=DATA_SHEETS_SCHEMA.was_validated_verified, name="instanceAcquisition__was_validated_verified", curie=DATA_SHEETS_SCHEMA.curie('was_validated_verified'),
                   model_uri=DATA_SHEETS_SCHEMA.instanceAcquisition__was_validated_verified, domain=None, range=Optional[Union[bool, Bool]])

slots.collectionMechanism__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="collectionMechanism__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionMechanism__description, domain=None, range=Optional[Union[str, List[str]]])

slots.dataCollector__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="dataCollector__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.dataCollector__description, domain=None, range=Optional[Union[str, List[str]]])

slots.collectionTimeframe__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="collectionTimeframe__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionTimeframe__description, domain=None, range=Optional[Union[str, List[str]]])

slots.ethicalReview__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="ethicalReview__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.ethicalReview__description, domain=None, range=Optional[Union[str, List[str]]])

slots.directCollection__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="directCollection__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.directCollection__description, domain=None, range=Optional[Union[str, List[str]]])

slots.collectionNotification__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="collectionNotification__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionNotification__description, domain=None, range=Optional[Union[str, List[str]]])

slots.collectionConsent__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="collectionConsent__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.collectionConsent__description, domain=None, range=Optional[Union[str, List[str]]])

slots.consentRevocation__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="consentRevocation__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.consentRevocation__description, domain=None, range=Optional[Union[str, List[str]]])

slots.dataProtectionImpact__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="dataProtectionImpact__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.dataProtectionImpact__description, domain=None, range=Optional[Union[str, List[str]]])

slots.preprocessingStrategy__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="preprocessingStrategy__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.preprocessingStrategy__description, domain=None, range=Optional[Union[str, List[str]]])

slots.cleaningStrategy__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="cleaningStrategy__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.cleaningStrategy__description, domain=None, range=Optional[Union[str, List[str]]])

slots.labelingStrategy__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="labelingStrategy__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.labelingStrategy__description, domain=None, range=Optional[Union[str, List[str]]])

slots.rawData__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="rawData__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.rawData__description, domain=None, range=Optional[Union[str, List[str]]])

slots.existingUse__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="existingUse__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.existingUse__description, domain=None, range=Optional[Union[str, List[str]]])

slots.useRepository__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="useRepository__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.useRepository__description, domain=None, range=Optional[Union[str, List[str]]])

slots.otherTask__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="otherTask__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.otherTask__description, domain=None, range=Optional[Union[str, List[str]]])

slots.futureUseImpact__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="futureUseImpact__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.futureUseImpact__description, domain=None, range=Optional[Union[str, List[str]]])

slots.discouragedUse__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="discouragedUse__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.discouragedUse__description, domain=None, range=Optional[Union[str, List[str]]])

slots.thirdPartySharing__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="thirdPartySharing__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.thirdPartySharing__description, domain=None, range=Optional[Union[bool, Bool]])

slots.distributionFormat__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="distributionFormat__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.distributionFormat__description, domain=None, range=Optional[Union[str, List[str]]])

slots.distributionDate__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="distributionDate__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.distributionDate__description, domain=None, range=Optional[Union[str, List[str]]])

slots.licenseAndUseTerms__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="licenseAndUseTerms__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.licenseAndUseTerms__description, domain=None, range=Optional[Union[str, List[str]]])

slots.iPRestrictions__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="iPRestrictions__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.iPRestrictions__description, domain=None, range=Optional[Union[str, List[str]]])

slots.exportControlRegulatoryRestrictions__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="exportControlRegulatoryRestrictions__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.exportControlRegulatoryRestrictions__description, domain=None, range=Optional[Union[str, List[str]]])

slots.maintainer__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="maintainer__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.maintainer__description, domain=None, range=Optional[Union[Union[str, "CreatorOrMaintainerEnum"], List[Union[str, "CreatorOrMaintainerEnum"]]]])

slots.erratum__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="erratum__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.erratum__description, domain=None, range=Optional[Union[str, List[str]]])

slots.updatePlan__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="updatePlan__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.updatePlan__description, domain=None, range=Optional[Union[str, List[str]]])

slots.retentionLimits__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="retentionLimits__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.retentionLimits__description, domain=None, range=Optional[Union[str, List[str]]])

slots.versionAccess__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="versionAccess__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.versionAccess__description, domain=None, range=Optional[Union[str, List[str]]])

slots.extensionMechanism__description = Slot(uri=DATA_SHEETS_SCHEMA.description, name="extensionMechanism__description", curie=DATA_SHEETS_SCHEMA.curie('description'),
                   model_uri=DATA_SHEETS_SCHEMA.extensionMechanism__description, domain=None, range=Optional[Union[str, List[str]]])