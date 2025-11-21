

# Class: ExportControlRegulatoryRestrictions 


_Do any export controls or other regulatory restrictions apply to the dataset or to individual instances? If so, please describe these restrictions and provide a link or copy of any supporting documentation._

__





URI: [data_sheets_schema:ExportControlRegulatoryRestrictions](https://w3id.org/bridge2ai/data-sheets-schema/ExportControlRegulatoryRestrictions)





```mermaid
 classDiagram
    class ExportControlRegulatoryRestrictions
    click ExportControlRegulatoryRestrictions href "../ExportControlRegulatoryRestrictions/"
      DatasetProperty <|-- ExportControlRegulatoryRestrictions
        click DatasetProperty href "../DatasetProperty/"
      
      ExportControlRegulatoryRestrictions : description
        
      ExportControlRegulatoryRestrictions : id
        
      ExportControlRegulatoryRestrictions : name
        
      ExportControlRegulatoryRestrictions : used_software
        
          
    
        
        
        ExportControlRegulatoryRestrictions --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **ExportControlRegulatoryRestrictions**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [description](description.md) | * <br/> [String](String.md) | Export or regulatory restrictions on the dataset | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [regulatory_restrictions](regulatory_restrictions.md) | range | [ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md) |
| [DataSubset](DataSubset.md) | [regulatory_restrictions](regulatory_restrictions.md) | range | [ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:ExportControlRegulatoryRestrictions |
| native | data_sheets_schema:ExportControlRegulatoryRestrictions |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ExportControlRegulatoryRestrictions
description: 'Do any export controls or other regulatory restrictions apply to the
  dataset or to individual instances? If so, please describe these restrictions and
  provide a link or copy of any supporting documentation.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: Export or regulatory restrictions on the dataset.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/data-governance
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
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: ExportControlRegulatoryRestrictions
description: 'Do any export controls or other regulatory restrictions apply to the
  dataset or to individual instances? If so, please describe these restrictions and
  provide a link or copy of any supporting documentation.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: Export or regulatory restrictions on the dataset.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/data-governance
    alias: description
    owner: ExportControlRegulatoryRestrictions
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
    multivalued: true
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: ExportControlRegulatoryRestrictions
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
    owner: ExportControlRegulatoryRestrictions
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
    owner: ExportControlRegulatoryRestrictions
    domain_of:
    - NamedThing
    range: string

```
</details>