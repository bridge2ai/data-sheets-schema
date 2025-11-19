

# Class: DatasetProperty 


_Represents a single property of a dataset, or a set of related properties._





URI: [data_sheets_schema:DatasetProperty](https://w3id.org/bridge2ai/data-sheets-schema/DatasetProperty)





```mermaid
 classDiagram
    class DatasetProperty
    click DatasetProperty href "../DatasetProperty/"
      NamedThing <|-- DatasetProperty
        click NamedThing href "../NamedThing/"
      

      DatasetProperty <|-- Purpose
        click Purpose href "../Purpose/"
      DatasetProperty <|-- Task
        click Task href "../Task/"
      DatasetProperty <|-- AddressingGap
        click AddressingGap href "../AddressingGap/"
      DatasetProperty <|-- Creator
        click Creator href "../Creator/"
      DatasetProperty <|-- FundingMechanism
        click FundingMechanism href "../FundingMechanism/"
      DatasetProperty <|-- Instance
        click Instance href "../Instance/"
      DatasetProperty <|-- SamplingStrategy
        click SamplingStrategy href "../SamplingStrategy/"
      DatasetProperty <|-- MissingInfo
        click MissingInfo href "../MissingInfo/"
      DatasetProperty <|-- Relationships
        click Relationships href "../Relationships/"
      DatasetProperty <|-- Splits
        click Splits href "../Splits/"
      DatasetProperty <|-- DataAnomaly
        click DataAnomaly href "../DataAnomaly/"
      DatasetProperty <|-- ExternalResource
        click ExternalResource href "../ExternalResource/"
      DatasetProperty <|-- Confidentiality
        click Confidentiality href "../Confidentiality/"
      DatasetProperty <|-- ContentWarning
        click ContentWarning href "../ContentWarning/"
      DatasetProperty <|-- Subpopulation
        click Subpopulation href "../Subpopulation/"
      DatasetProperty <|-- Deidentification
        click Deidentification href "../Deidentification/"
      DatasetProperty <|-- SensitiveElement
        click SensitiveElement href "../SensitiveElement/"
      DatasetProperty <|-- InstanceAcquisition
        click InstanceAcquisition href "../InstanceAcquisition/"
      DatasetProperty <|-- CollectionMechanism
        click CollectionMechanism href "../CollectionMechanism/"
      DatasetProperty <|-- DataCollector
        click DataCollector href "../DataCollector/"
      DatasetProperty <|-- CollectionTimeframe
        click CollectionTimeframe href "../CollectionTimeframe/"
      DatasetProperty <|-- DirectCollection
        click DirectCollection href "../DirectCollection/"
      DatasetProperty <|-- PreprocessingStrategy
        click PreprocessingStrategy href "../PreprocessingStrategy/"
      DatasetProperty <|-- CleaningStrategy
        click CleaningStrategy href "../CleaningStrategy/"
      DatasetProperty <|-- LabelingStrategy
        click LabelingStrategy href "../LabelingStrategy/"
      DatasetProperty <|-- RawData
        click RawData href "../RawData/"
      DatasetProperty <|-- ExistingUse
        click ExistingUse href "../ExistingUse/"
      DatasetProperty <|-- UseRepository
        click UseRepository href "../UseRepository/"
      DatasetProperty <|-- OtherTask
        click OtherTask href "../OtherTask/"
      DatasetProperty <|-- FutureUseImpact
        click FutureUseImpact href "../FutureUseImpact/"
      DatasetProperty <|-- DiscouragedUse
        click DiscouragedUse href "../DiscouragedUse/"
      DatasetProperty <|-- ThirdPartySharing
        click ThirdPartySharing href "../ThirdPartySharing/"
      DatasetProperty <|-- DistributionFormat
        click DistributionFormat href "../DistributionFormat/"
      DatasetProperty <|-- DistributionDate
        click DistributionDate href "../DistributionDate/"
      DatasetProperty <|-- Maintainer
        click Maintainer href "../Maintainer/"
      DatasetProperty <|-- Erratum
        click Erratum href "../Erratum/"
      DatasetProperty <|-- UpdatePlan
        click UpdatePlan href "../UpdatePlan/"
      DatasetProperty <|-- RetentionLimits
        click RetentionLimits href "../RetentionLimits/"
      DatasetProperty <|-- VersionAccess
        click VersionAccess href "../VersionAccess/"
      DatasetProperty <|-- ExtensionMechanism
        click ExtensionMechanism href "../ExtensionMechanism/"
      DatasetProperty <|-- EthicalReview
        click EthicalReview href "../EthicalReview/"
      DatasetProperty <|-- DataProtectionImpact
        click DataProtectionImpact href "../DataProtectionImpact/"
      DatasetProperty <|-- CollectionNotification
        click CollectionNotification href "../CollectionNotification/"
      DatasetProperty <|-- CollectionConsent
        click CollectionConsent href "../CollectionConsent/"
      DatasetProperty <|-- ConsentRevocation
        click ConsentRevocation href "../ConsentRevocation/"
      DatasetProperty <|-- HumanSubjectResearch
        click HumanSubjectResearch href "../HumanSubjectResearch/"
      DatasetProperty <|-- InformedConsent
        click InformedConsent href "../InformedConsent/"
      DatasetProperty <|-- ParticipantPrivacy
        click ParticipantPrivacy href "../ParticipantPrivacy/"
      DatasetProperty <|-- HumanSubjectCompensation
        click HumanSubjectCompensation href "../HumanSubjectCompensation/"
      DatasetProperty <|-- VulnerablePopulations
        click VulnerablePopulations href "../VulnerablePopulations/"
      DatasetProperty <|-- LicenseAndUseTerms
        click LicenseAndUseTerms href "../LicenseAndUseTerms/"
      DatasetProperty <|-- IPRestrictions
        click IPRestrictions href "../IPRestrictions/"
      DatasetProperty <|-- ExportControlRegulatoryRestrictions
        click ExportControlRegulatoryRestrictions href "../ExportControlRegulatoryRestrictions/"
      

      DatasetProperty : description
        
      DatasetProperty : id
        
      DatasetProperty : name
        
      DatasetProperty : used_software
        
          
    
        
        
        DatasetProperty --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * **DatasetProperty**
        * [Purpose](Purpose.md)
        * [Task](Task.md)
        * [AddressingGap](AddressingGap.md)
        * [Creator](Creator.md)
        * [FundingMechanism](FundingMechanism.md)
        * [Instance](Instance.md)
        * [SamplingStrategy](SamplingStrategy.md)
        * [MissingInfo](MissingInfo.md)
        * [Relationships](Relationships.md)
        * [Splits](Splits.md)
        * [DataAnomaly](DataAnomaly.md)
        * [ExternalResource](ExternalResource.md)
        * [Confidentiality](Confidentiality.md)
        * [ContentWarning](ContentWarning.md)
        * [Subpopulation](Subpopulation.md)
        * [Deidentification](Deidentification.md)
        * [SensitiveElement](SensitiveElement.md)
        * [InstanceAcquisition](InstanceAcquisition.md)
        * [CollectionMechanism](CollectionMechanism.md)
        * [DataCollector](DataCollector.md)
        * [CollectionTimeframe](CollectionTimeframe.md)
        * [DirectCollection](DirectCollection.md)
        * [PreprocessingStrategy](PreprocessingStrategy.md)
        * [CleaningStrategy](CleaningStrategy.md)
        * [LabelingStrategy](LabelingStrategy.md)
        * [RawData](RawData.md)
        * [ExistingUse](ExistingUse.md)
        * [UseRepository](UseRepository.md)
        * [OtherTask](OtherTask.md)
        * [FutureUseImpact](FutureUseImpact.md)
        * [DiscouragedUse](DiscouragedUse.md)
        * [ThirdPartySharing](ThirdPartySharing.md)
        * [DistributionFormat](DistributionFormat.md)
        * [DistributionDate](DistributionDate.md)
        * [Maintainer](Maintainer.md)
        * [Erratum](Erratum.md)
        * [UpdatePlan](UpdatePlan.md)
        * [RetentionLimits](RetentionLimits.md)
        * [VersionAccess](VersionAccess.md)
        * [ExtensionMechanism](ExtensionMechanism.md)
        * [EthicalReview](EthicalReview.md)
        * [DataProtectionImpact](DataProtectionImpact.md)
        * [CollectionNotification](CollectionNotification.md)
        * [CollectionConsent](CollectionConsent.md)
        * [ConsentRevocation](ConsentRevocation.md)
        * [HumanSubjectResearch](HumanSubjectResearch.md)
        * [InformedConsent](InformedConsent.md)
        * [ParticipantPrivacy](ParticipantPrivacy.md)
        * [HumanSubjectCompensation](HumanSubjectCompensation.md)
        * [VulnerablePopulations](VulnerablePopulations.md)
        * [LicenseAndUseTerms](LicenseAndUseTerms.md)
        * [IPRestrictions](IPRestrictions.md)
        * [ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md)



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | direct |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |










## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DatasetProperty |
| native | data_sheets_schema:DatasetProperty |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DatasetProperty
description: Represents a single property of a dataset, or a set of related properties.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: NamedThing
attributes:
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DatasetProperty
description: Represents a single property of a dataset, or a set of related properties.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: NamedThing
attributes:
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: DatasetProperty
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
  id:
    name: id
    description: A unique identifier for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:identifier
    identifier: true
    alias: id
    owner: DatasetProperty
    domain_of:
    - NamedThing
    range: uriorcurie
    required: true
  name:
    name: name
    description: A human-readable name for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:name
    alias: name
    owner: DatasetProperty
    domain_of:
    - NamedThing
    range: string
  description:
    name: description
    description: A human-readable description for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:description
    alias: description
    owner: DatasetProperty
    domain_of:
    - NamedThing
    - Relationships
    - Splits
    - DataAnomaly
    - Confidentiality
    - Deidentification
    - SensitiveElement
    - InstanceAcquisition
    - CollectionMechanism
    - DataCollector
    - CollectionTimeframe
    - DirectCollection
    - PreprocessingStrategy
    - CleaningStrategy
    - LabelingStrategy
    - RawData
    - ExistingUse
    - UseRepository
    - OtherTask
    - FutureUseImpact
    - DiscouragedUse
    - ThirdPartySharing
    - DistributionFormat
    - DistributionDate
    - Maintainer
    - Erratum
    - UpdatePlan
    - RetentionLimits
    - VersionAccess
    - ExtensionMechanism
    - EthicalReview
    - DataProtectionImpact
    - CollectionNotification
    - CollectionConsent
    - ConsentRevocation
    - LicenseAndUseTerms
    - IPRestrictions
    - ExportControlRegulatoryRestrictions
    range: string

```
</details>