

# Class: RetentionLimits 


_If the dataset relates to people, are there applicable limits on the retention of their data (e.g., were individuals told their data would be deleted after a certain time)? If so, please describe these limits and how they will be enforced._

__





URI: [data_sheets_schema:RetentionLimits](https://w3id.org/bridge2ai/data-sheets-schema/RetentionLimits)





```mermaid
 classDiagram
    class RetentionLimits
    click RetentionLimits href "../RetentionLimits/"
      DatasetProperty <|-- RetentionLimits
        click DatasetProperty href "../DatasetProperty/"
      
      RetentionLimits : description
        
      RetentionLimits : id
        
      RetentionLimits : name
        
      RetentionLimits : used_software
        
          
    
        
        
        RetentionLimits --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **RetentionLimits**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [description](description.md) | * <br/> [String](String.md) | Policies or regulations around data retention, including any  enforcement mec... | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [retention_limit](retention_limit.md) | range | [RetentionLimits](RetentionLimits.md) |
| [DataSubset](DataSubset.md) | [retention_limit](retention_limit.md) | range | [RetentionLimits](RetentionLimits.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:RetentionLimits |
| native | data_sheets_schema:RetentionLimits |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: RetentionLimits
description: 'If the dataset relates to people, are there applicable limits on the
  retention of their data (e.g., were individuals told their data would be deleted
  after a certain time)? If so, please describe these limits and how they will be
  enforced.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: 'Policies or regulations around data retention, including any  enforcement
      mechanisms or responsibilities.

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
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: RetentionLimits
description: 'If the dataset relates to people, are there applicable limits on the
  retention of their data (e.g., were individuals told their data would be deleted
  after a certain time)? If so, please describe these limits and how they will be
  enforced.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: 'Policies or regulations around data retention, including any  enforcement
      mechanisms or responsibilities.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    alias: description
    owner: RetentionLimits
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
    owner: RetentionLimits
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
    owner: RetentionLimits
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
    owner: RetentionLimits
    domain_of:
    - NamedThing
    range: string

```
</details>