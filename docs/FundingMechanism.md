

# Class: FundingMechanism 


_Who funded the creation of the dataset? If there is an associated grant, please provide the name of the grantor and the grant name and number._

__





URI: [data_sheets_schema:FundingMechanism](https://w3id.org/bridge2ai/data-sheets-schema/FundingMechanism)





```mermaid
 classDiagram
    class FundingMechanism
    click FundingMechanism href "../FundingMechanism/"
      DatasetProperty <|-- FundingMechanism
        click DatasetProperty href "../DatasetProperty/"
      
      FundingMechanism : description
        
      FundingMechanism : grant
        
          
    
        
        
        FundingMechanism --> "0..1" Grant : grant
        click Grant href "../Grant/"
    

        
      FundingMechanism : grantor
        
          
    
        
        
        FundingMechanism --> "0..1" Grantor : grantor
        click Grantor href "../Grantor/"
    

        
      FundingMechanism : id
        
      FundingMechanism : name
        
      FundingMechanism : used_software
        
          
    
        
        
        FundingMechanism --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **FundingMechanism**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [grantor](grantor.md) | 0..1 <br/> [Grantor](Grantor.md) | Name/identifier of the organization providing monetary or resource support | direct |
| [grant](grant.md) | 0..1 <br/> [Grant](Grant.md) | Name/identifier of the specific grant mechanism supporting dataset creation | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [funders](funders.md) | range | [FundingMechanism](FundingMechanism.md) |
| [DataSubset](DataSubset.md) | [funders](funders.md) | range | [FundingMechanism](FundingMechanism.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:FundingMechanism |
| native | data_sheets_schema:FundingMechanism |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: FundingMechanism
description: 'Who funded the creation of the dataset? If there is an associated grant,
  please provide the name of the grantor and the grant name and number.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  grantor:
    name: grantor
    description: Name/identifier of the organization providing monetary or resource
      support.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    domain_of:
    - FundingMechanism
    range: Grantor
  grant:
    name: grant
    description: Name/identifier of the specific grant mechanism supporting dataset
      creation.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    domain_of:
    - FundingMechanism
    range: Grant

```
</details>

### Induced

<details>
```yaml
name: FundingMechanism
description: 'Who funded the creation of the dataset? If there is an associated grant,
  please provide the name of the grantor and the grant name and number.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  grantor:
    name: grantor
    description: Name/identifier of the organization providing monetary or resource
      support.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    alias: grantor
    owner: FundingMechanism
    domain_of:
    - FundingMechanism
    range: Grantor
  grant:
    name: grant
    description: Name/identifier of the specific grant mechanism supporting dataset
      creation.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    alias: grant
    owner: FundingMechanism
    domain_of:
    - FundingMechanism
    range: Grant
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: FundingMechanism
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
    owner: FundingMechanism
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
    owner: FundingMechanism
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
    owner: FundingMechanism
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