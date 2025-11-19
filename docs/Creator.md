

# Class: Creator 


_Who created the dataset (e.g., which team, research group) and on behalf of which  entity (e.g., company, institution, organization)? This may also be considered a team._

__





URI: [data_sheets_schema:Creator](https://w3id.org/bridge2ai/data-sheets-schema/Creator)





```mermaid
 classDiagram
    class Creator
    click Creator href "../Creator/"
      DatasetProperty <|-- Creator
        click DatasetProperty href "../DatasetProperty/"
      
      Creator : affiliation
        
          
    
        
        
        Creator --> "0..1" Organization : affiliation
        click Organization href "../Organization/"
    

        
      Creator : description
        
      Creator : id
        
      Creator : name
        
      Creator : principal_investigator
        
          
    
        
        
        Creator --> "0..1" Person : principal_investigator
        click Person href "../Person/"
    

        
      Creator : used_software
        
          
    
        
        
        Creator --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **Creator**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [principal_investigator](principal_investigator.md) | 0..1 <br/> [Person](Person.md) | A key individual (Principal Investigator) responsible for or overseeing datas... | direct |
| [affiliation](affiliation.md) | 0..1 <br/> [Organization](Organization.md) | Organization(s) with which the creator or team is affiliated | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [creators](creators.md) | range | [Creator](Creator.md) |
| [DataSubset](DataSubset.md) | [creators](creators.md) | range | [Creator](Creator.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Creator |
| native | data_sheets_schema:Creator |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Creator
description: 'Who created the dataset (e.g., which team, research group) and on behalf
  of which  entity (e.g., company, institution, organization)? This may also be considered
  a team.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  principal_investigator:
    name: principal_investigator
    description: A key individual (Principal Investigator) responsible for or overseeing
      dataset creation.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    domain_of:
    - Creator
    range: Person
  affiliation:
    name: affiliation
    description: Organization(s) with which the creator or team is affiliated.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    domain_of:
    - Person
    - Creator
    range: Organization

```
</details>

### Induced

<details>
```yaml
name: Creator
description: 'Who created the dataset (e.g., which team, research group) and on behalf
  of which  entity (e.g., company, institution, organization)? This may also be considered
  a team.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  principal_investigator:
    name: principal_investigator
    description: A key individual (Principal Investigator) responsible for or overseeing
      dataset creation.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    rank: 1000
    alias: principal_investigator
    owner: Creator
    domain_of:
    - Creator
    range: Person
  affiliation:
    name: affiliation
    description: Organization(s) with which the creator or team is affiliated.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    alias: affiliation
    owner: Creator
    domain_of:
    - Person
    - Creator
    range: Organization
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: Creator
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
    owner: Creator
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
    owner: Creator
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
    owner: Creator
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