

# Class: LicenseAndUseTerms 


_Will the dataset be distributed under a copyright or other IP license, and/or under applicable terms of use? Provide a link or copy of relevant licensing terms and any fees._

__





URI: [data_sheets_schema:LicenseAndUseTerms](https://w3id.org/bridge2ai/data-sheets-schema/LicenseAndUseTerms)





```mermaid
 classDiagram
    class LicenseAndUseTerms
    click LicenseAndUseTerms href "../LicenseAndUseTerms/"
      DatasetProperty <|-- LicenseAndUseTerms
        click DatasetProperty href "../DatasetProperty/"
      
      LicenseAndUseTerms : description
        
      LicenseAndUseTerms : id
        
      LicenseAndUseTerms : name
        
      LicenseAndUseTerms : used_software
        
          
    
        
        
        LicenseAndUseTerms --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **LicenseAndUseTerms**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [description](description.md) | * <br/> [String](String.md) | Description of the dataset's license and terms of use (including  links, cost... | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [license_and_use_terms](license_and_use_terms.md) | range | [LicenseAndUseTerms](LicenseAndUseTerms.md) |
| [DataSubset](DataSubset.md) | [license_and_use_terms](license_and_use_terms.md) | range | [LicenseAndUseTerms](LicenseAndUseTerms.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:LicenseAndUseTerms |
| native | data_sheets_schema:LicenseAndUseTerms |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: LicenseAndUseTerms
description: 'Will the dataset be distributed under a copyright or other IP license,
  and/or under applicable terms of use? Provide a link or copy of relevant licensing
  terms and any fees.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: 'Description of the dataset''s license and terms of use (including  links,
      costs, or usage constraints).

      '
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
name: LicenseAndUseTerms
description: 'Will the dataset be distributed under a copyright or other IP license,
  and/or under applicable terms of use? Provide a link or copy of relevant licensing
  terms and any fees.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: 'Description of the dataset''s license and terms of use (including  links,
      costs, or usage constraints).

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/data-governance
    alias: description
    owner: LicenseAndUseTerms
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
    owner: LicenseAndUseTerms
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
    owner: LicenseAndUseTerms
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
    owner: LicenseAndUseTerms
    domain_of:
    - NamedThing
    range: string

```
</details>