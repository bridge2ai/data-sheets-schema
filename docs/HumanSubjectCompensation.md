

# Class: HumanSubjectCompensation 


_Information about compensation or incentives provided to human research participants._

__





URI: [data_sheets_schema:HumanSubjectCompensation](https://w3id.org/bridge2ai/data-sheets-schema/HumanSubjectCompensation)





```mermaid
 classDiagram
    class HumanSubjectCompensation
    click HumanSubjectCompensation href "../HumanSubjectCompensation/"
      DatasetProperty <|-- HumanSubjectCompensation
        click DatasetProperty href "../DatasetProperty/"
      
      HumanSubjectCompensation : compensation_amount
        
      HumanSubjectCompensation : compensation_provided
        
      HumanSubjectCompensation : compensation_rationale
        
      HumanSubjectCompensation : compensation_type
        
      HumanSubjectCompensation : description
        
      HumanSubjectCompensation : id
        
      HumanSubjectCompensation : name
        
      HumanSubjectCompensation : used_software
        
          
    
        
        
        HumanSubjectCompensation --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **HumanSubjectCompensation**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [compensation_provided](compensation_provided.md) | 0..1 <br/> [Boolean](Boolean.md) | Were participants compensated for their participation? | direct |
| [compensation_type](compensation_type.md) | * <br/> [String](String.md) | What type of compensation was provided (e | direct |
| [compensation_amount](compensation_amount.md) | * <br/> [String](String.md) | What was the amount or value of compensation provided? Include currency or eq... | direct |
| [compensation_rationale](compensation_rationale.md) | * <br/> [String](String.md) | What was the rationale for the compensation structure? How was the amount det... | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |










## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:HumanSubjectCompensation |
| native | data_sheets_schema:HumanSubjectCompensation |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: HumanSubjectCompensation
description: 'Information about compensation or incentives provided to human research
  participants.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  compensation_provided:
    name: compensation_provided
    description: Were participants compensated for their participation?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - HumanSubjectCompensation
    range: boolean
  compensation_type:
    name: compensation_type
    description: 'What type of compensation was provided (e.g., monetary payment,
      gift cards, course credit, other incentives)?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - HumanSubjectCompensation
    range: string
    multivalued: true
  compensation_amount:
    name: compensation_amount
    description: 'What was the amount or value of compensation provided? Include currency
      or equivalent value.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - HumanSubjectCompensation
    range: string
    multivalued: true
  compensation_rationale:
    name: compensation_rationale
    description: 'What was the rationale for the compensation structure? How was the
      amount determined to be appropriate?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - HumanSubjectCompensation
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: HumanSubjectCompensation
description: 'Information about compensation or incentives provided to human research
  participants.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  compensation_provided:
    name: compensation_provided
    description: Were participants compensated for their participation?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: compensation_provided
    owner: HumanSubjectCompensation
    domain_of:
    - HumanSubjectCompensation
    range: boolean
  compensation_type:
    name: compensation_type
    description: 'What type of compensation was provided (e.g., monetary payment,
      gift cards, course credit, other incentives)?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: compensation_type
    owner: HumanSubjectCompensation
    domain_of:
    - HumanSubjectCompensation
    range: string
    multivalued: true
  compensation_amount:
    name: compensation_amount
    description: 'What was the amount or value of compensation provided? Include currency
      or equivalent value.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: compensation_amount
    owner: HumanSubjectCompensation
    domain_of:
    - HumanSubjectCompensation
    range: string
    multivalued: true
  compensation_rationale:
    name: compensation_rationale
    description: 'What was the rationale for the compensation structure? How was the
      amount determined to be appropriate?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: compensation_rationale
    owner: HumanSubjectCompensation
    domain_of:
    - HumanSubjectCompensation
    range: string
    multivalued: true
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: HumanSubjectCompensation
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
    owner: HumanSubjectCompensation
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
    owner: HumanSubjectCompensation
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
    owner: HumanSubjectCompensation
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