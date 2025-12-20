

# Class: Software 


_A software program or library._





URI: [schema:SoftwareApplication](http://schema.org/SoftwareApplication)





```mermaid
 classDiagram
    class Software
    click Software href "../Software/"
      NamedThing <|-- Software
        click NamedThing href "../NamedThing/"
      
      Software : description
        
      Software : id
        
      Software : license
        
      Software : name
        
      Software : url
        
      Software : version
        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * **Software**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [version](version.md) | 0..1 <br/> [String](String.md) |  | direct |
| [license](license.md) | 0..1 <br/> [String](String.md) |  | direct |
| [url](url.md) | 0..1 <br/> [String](String.md) |  | direct |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [DatasetProperty](DatasetProperty.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Purpose](Purpose.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Task](Task.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [AddressingGap](AddressingGap.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Creator](Creator.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [FundingMechanism](FundingMechanism.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Instance](Instance.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [SamplingStrategy](SamplingStrategy.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [MissingInfo](MissingInfo.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Relationships](Relationships.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Splits](Splits.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DataAnomaly](DataAnomaly.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DatasetBias](DatasetBias.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DatasetLimitation](DatasetLimitation.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ExternalResource](ExternalResource.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Confidentiality](Confidentiality.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ContentWarning](ContentWarning.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Subpopulation](Subpopulation.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Deidentification](Deidentification.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [SensitiveElement](SensitiveElement.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DatasetRelationship](DatasetRelationship.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [InstanceAcquisition](InstanceAcquisition.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [CollectionMechanism](CollectionMechanism.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DataCollector](DataCollector.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [CollectionTimeframe](CollectionTimeframe.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DirectCollection](DirectCollection.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [MissingDataDocumentation](MissingDataDocumentation.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [RawDataSource](RawDataSource.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [PreprocessingStrategy](PreprocessingStrategy.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [CleaningStrategy](CleaningStrategy.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [LabelingStrategy](LabelingStrategy.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [RawData](RawData.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ImputationProtocol](ImputationProtocol.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [AnnotationAnalysis](AnnotationAnalysis.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [MachineAnnotationTools](MachineAnnotationTools.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ExistingUse](ExistingUse.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [UseRepository](UseRepository.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [OtherTask](OtherTask.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [FutureUseImpact](FutureUseImpact.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DiscouragedUse](DiscouragedUse.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [IntendedUse](IntendedUse.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ProhibitedUse](ProhibitedUse.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ThirdPartySharing](ThirdPartySharing.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DistributionFormat](DistributionFormat.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DistributionDate](DistributionDate.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Maintainer](Maintainer.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [Erratum](Erratum.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [UpdatePlan](UpdatePlan.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [RetentionLimits](RetentionLimits.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [VersionAccess](VersionAccess.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ExtensionMechanism](ExtensionMechanism.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [EthicalReview](EthicalReview.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [DataProtectionImpact](DataProtectionImpact.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [CollectionNotification](CollectionNotification.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [CollectionConsent](CollectionConsent.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ConsentRevocation](ConsentRevocation.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [HumanSubjectResearch](HumanSubjectResearch.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [InformedConsent](InformedConsent.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ParticipantPrivacy](ParticipantPrivacy.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [HumanSubjectCompensation](HumanSubjectCompensation.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [VulnerablePopulations](VulnerablePopulations.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [LicenseAndUseTerms](LicenseAndUseTerms.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [IPRestrictions](IPRestrictions.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md) | [used_software](used_software.md) | range | [Software](Software.md) |
| [VariableMetadata](VariableMetadata.md) | [used_software](used_software.md) | range | [Software](Software.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:SoftwareApplication |
| native | data_sheets_schema:Software |
| exact | schema:SoftwareApplication |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Software
description: A software program or library.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:SoftwareApplication
is_a: NamedThing
attributes:
  version:
    name: version
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:softwareVersion
    domain_of:
    - Software
    - Information
    range: string
  license:
    name: license
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:license
    domain_of:
    - Software
    - Information
    range: string
  url:
    name: url
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:url
    domain_of:
    - Software
    range: string
class_uri: schema:SoftwareApplication

```
</details>

### Induced

<details>
```yaml
name: Software
description: A software program or library.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:SoftwareApplication
is_a: NamedThing
attributes:
  version:
    name: version
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:softwareVersion
    alias: version
    owner: Software
    domain_of:
    - Software
    - Information
    range: string
  license:
    name: license
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:license
    alias: license
    owner: Software
    domain_of:
    - Software
    - Information
    range: string
  url:
    name: url
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:url
    alias: url
    owner: Software
    domain_of:
    - Software
    range: string
  id:
    name: id
    description: A unique identifier for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:identifier
    identifier: true
    alias: id
    owner: Software
    domain_of:
    - NamedThing
    - DatasetProperty
    range: uriorcurie
    required: true
  name:
    name: name
    description: A human-readable name for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:name
    alias: name
    owner: Software
    domain_of:
    - NamedThing
    - DatasetProperty
    range: string
  description:
    name: description
    description: A human-readable description for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:description
    alias: description
    owner: Software
    domain_of:
    - NamedThing
    - DatasetProperty
    - DatasetRelationship
    range: string
class_uri: schema:SoftwareApplication

```
</details>