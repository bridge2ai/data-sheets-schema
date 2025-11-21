

# Class: Maintainer 


_Who will be supporting/hosting/maintaining the dataset?_

__





URI: [data_sheets_schema:Maintainer](https://w3id.org/bridge2ai/data-sheets-schema/Maintainer)





```mermaid
 classDiagram
    class Maintainer
    click Maintainer href "../Maintainer/"
      DatasetProperty <|-- Maintainer
        click DatasetProperty href "../DatasetProperty/"
      
      Maintainer : description
        
          
    
        
        
        Maintainer --> "*" CreatorOrMaintainerEnum : description
        click CreatorOrMaintainerEnum href "../CreatorOrMaintainerEnum/"
    

        
      Maintainer : id
        
      Maintainer : name
        
      Maintainer : used_software
        
          
    
        
        
        Maintainer --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **Maintainer**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [description](description.md) | * <br/> [CreatorOrMaintainerEnum](CreatorOrMaintainerEnum.md) | Name or role of the maintainer, possibly referencing  CreatorOrMaintainerEnum... | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [maintainers](maintainers.md) | range | [Maintainer](Maintainer.md) |
| [DataSubset](DataSubset.md) | [maintainers](maintainers.md) | range | [Maintainer](Maintainer.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Maintainer |
| native | data_sheets_schema:Maintainer |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Maintainer
description: 'Who will be supporting/hosting/maintaining the dataset?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: 'Name or role of the maintainer, possibly referencing  CreatorOrMaintainerEnum
      or other details.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
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
    range: CreatorOrMaintainerEnum
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: Maintainer
description: 'Who will be supporting/hosting/maintaining the dataset?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: 'Name or role of the maintainer, possibly referencing  CreatorOrMaintainerEnum
      or other details.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    alias: description
    owner: Maintainer
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
    range: CreatorOrMaintainerEnum
    multivalued: true
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: Maintainer
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
    owner: Maintainer
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
    owner: Maintainer
    domain_of:
    - NamedThing
    range: string

```
</details>