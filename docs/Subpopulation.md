

# Class: Subpopulation 


_Does the dataset identify any subpopulations (e.g., by age, gender)? If so, how are they identified and what are their distributions?_

__





URI: [data_sheets_schema:Subpopulation](https://w3id.org/bridge2ai/data-sheets-schema/Subpopulation)





```mermaid
 classDiagram
    class Subpopulation
    click Subpopulation href "../Subpopulation/"
      DatasetProperty <|-- Subpopulation
        click DatasetProperty href "../DatasetProperty/"
      
      Subpopulation : description
        
      Subpopulation : distribution
        
      Subpopulation : id
        
      Subpopulation : identification
        
      Subpopulation : name
        
      Subpopulation : subpopulation_elements_present
        
      Subpopulation : used_software
        
          
    
        
        
        Subpopulation --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **Subpopulation**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [subpopulation_elements_present](subpopulation_elements_present.md) | 0..1 <br/> [Boolean](Boolean.md) | Indicates whether any subpopulations are explicitly identified | direct |
| [identification](identification.md) | * <br/> [String](String.md) |  | direct |
| [distribution](distribution.md) | * <br/> [String](String.md) |  | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [subpopulations](subpopulations.md) | range | [Subpopulation](Subpopulation.md) |
| [DataSubset](DataSubset.md) | [subpopulations](subpopulations.md) | range | [Subpopulation](Subpopulation.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Subpopulation |
| native | data_sheets_schema:Subpopulation |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Subpopulation
description: 'Does the dataset identify any subpopulations (e.g., by age, gender)?
  If so, how are they identified and what are their distributions?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  subpopulation_elements_present:
    name: subpopulation_elements_present
    description: Indicates whether any subpopulations are explicitly identified.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Subpopulation
    range: boolean
  identification:
    name: identification
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Subpopulation
    range: string
    multivalued: true
  distribution:
    name: distribution
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Subpopulation
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: Subpopulation
description: 'Does the dataset identify any subpopulations (e.g., by age, gender)?
  If so, how are they identified and what are their distributions?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  subpopulation_elements_present:
    name: subpopulation_elements_present
    description: Indicates whether any subpopulations are explicitly identified.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: subpopulation_elements_present
    owner: Subpopulation
    domain_of:
    - Subpopulation
    range: boolean
  identification:
    name: identification
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: identification
    owner: Subpopulation
    domain_of:
    - Subpopulation
    range: string
    multivalued: true
  distribution:
    name: distribution
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: distribution
    owner: Subpopulation
    domain_of:
    - Subpopulation
    range: string
    multivalued: true
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: Subpopulation
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
    owner: Subpopulation
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
    owner: Subpopulation
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
    owner: Subpopulation
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