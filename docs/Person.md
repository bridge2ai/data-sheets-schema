

# Class: Person 


_An individual human being._





URI: [data_sheets_schema:Person](https://w3id.org/bridge2ai/data-sheets-schema/Person)





```mermaid
 classDiagram
    class Person
    click Person href "../Person/"
      NamedThing <|-- Person
        click NamedThing href "../NamedThing/"
      
      Person : affiliation
        
          
    
        
        
        Person --> "*" Organization : affiliation
        click Organization href "../Organization/"
    

        
      Person : description
        
      Person : email
        
      Person : id
        
      Person : name
        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * **Person**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [affiliation](affiliation.md) | * <br/> [Organization](Organization.md) | The organization(s) to which the person belongs | direct |
| [email](email.md) | 0..1 <br/> [String](String.md) | The email address of the person | direct |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Creator](Creator.md) | [principal_investigator](principal_investigator.md) | range | [Person](Person.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Person |
| native | data_sheets_schema:Person |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Person
description: An individual human being.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: NamedThing
attributes:
  affiliation:
    name: affiliation
    description: The organization(s) to which the person belongs.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    domain_of:
    - Person
    - Creator
    range: Organization
    multivalued: true
  email:
    name: email
    description: The email address of the person.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    domain_of:
    - Person
    range: string

```
</details>

### Induced

<details>
```yaml
name: Person
description: An individual human being.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: NamedThing
attributes:
  affiliation:
    name: affiliation
    description: The organization(s) to which the person belongs.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: affiliation
    owner: Person
    domain_of:
    - Person
    - Creator
    range: Organization
    multivalued: true
  email:
    name: email
    description: The email address of the person.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: email
    owner: Person
    domain_of:
    - Person
    range: string
  id:
    name: id
    description: A unique identifier for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:identifier
    identifier: true
    alias: id
    owner: Person
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
    owner: Person
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
    owner: Person
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