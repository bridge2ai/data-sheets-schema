

# Class: ContentWarning 


_Does the dataset contain any data that might be offensive, insulting, threatening, or otherwise anxiety-provoking if viewed directly?_

__





URI: [data_sheets_schema:ContentWarning](https://w3id.org/bridge2ai/data-sheets-schema/ContentWarning)





```mermaid
 classDiagram
    class ContentWarning
    click ContentWarning href "../ContentWarning/"
      DatasetProperty <|-- ContentWarning
        click DatasetProperty href "../DatasetProperty/"
      
      ContentWarning : content_warnings_present
        
      ContentWarning : description
        
      ContentWarning : id
        
      ContentWarning : name
        
      ContentWarning : used_software
        
          
    
        
        
        ContentWarning --> "*" Software : used_software
        click Software href "../Software/"
    

        
      ContentWarning : warnings
        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **ContentWarning**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [content_warnings_present](content_warnings_present.md) | 0..1 <br/> [Boolean](Boolean.md) | Indicates whether any content warnings are needed | direct |
| [warnings](warnings.md) | * <br/> [String](String.md) |  | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [content_warnings](content_warnings.md) | range | [ContentWarning](ContentWarning.md) |
| [DataSubset](DataSubset.md) | [content_warnings](content_warnings.md) | range | [ContentWarning](ContentWarning.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:ContentWarning |
| native | data_sheets_schema:ContentWarning |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ContentWarning
description: 'Does the dataset contain any data that might be offensive, insulting,
  threatening, or otherwise anxiety-provoking if viewed directly?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  content_warnings_present:
    name: content_warnings_present
    description: Indicates whether any content warnings are needed.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - ContentWarning
    range: boolean
  warnings:
    name: warnings
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - ContentWarning
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: ContentWarning
description: 'Does the dataset contain any data that might be offensive, insulting,
  threatening, or otherwise anxiety-provoking if viewed directly?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  content_warnings_present:
    name: content_warnings_present
    description: Indicates whether any content warnings are needed.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: content_warnings_present
    owner: ContentWarning
    domain_of:
    - ContentWarning
    range: boolean
  warnings:
    name: warnings
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: warnings
    owner: ContentWarning
    domain_of:
    - ContentWarning
    range: string
    multivalued: true
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: ContentWarning
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
    owner: ContentWarning
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
    owner: ContentWarning
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
    owner: ContentWarning
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