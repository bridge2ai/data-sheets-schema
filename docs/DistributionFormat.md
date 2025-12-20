

# Class: DistributionFormat 


_How will the dataset be distributed (e.g., tarball on a website, API, GitHub)?_

__





URI: [data_sheets_schema:DistributionFormat](https://w3id.org/bridge2ai/data-sheets-schema/DistributionFormat)





```mermaid
 classDiagram
    class DistributionFormat
    click DistributionFormat href "../DistributionFormat/"
      DatasetProperty <|-- DistributionFormat
        click DatasetProperty href "../DatasetProperty/"
      
      DistributionFormat : access_urls
        
      DistributionFormat : description
        
      DistributionFormat : id
        
      DistributionFormat : name
        
      DistributionFormat : used_software
        
          
    
        
        
        DistributionFormat --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DistributionFormat**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [access_urls](access_urls.md) | * <br/> [String](String.md) | Details of the distribution channel(s) or format(s) | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [distribution_formats](distribution_formats.md) | range | [DistributionFormat](DistributionFormat.md) |
| [DataSubset](DataSubset.md) | [distribution_formats](distribution_formats.md) | range | [DistributionFormat](DistributionFormat.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DistributionFormat |
| native | data_sheets_schema:DistributionFormat |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DistributionFormat
description: 'How will the dataset be distributed (e.g., tarball on a website, API,
  GitHub)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  access_urls:
    name: access_urls
    description: Details of the distribution channel(s) or format(s).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/distribution
    rank: 1000
    slot_uri: dcat:accessURL
    domain_of:
    - DistributionFormat
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DistributionFormat
description: 'How will the dataset be distributed (e.g., tarball on a website, API,
  GitHub)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  access_urls:
    name: access_urls
    description: Details of the distribution channel(s) or format(s).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/distribution
    rank: 1000
    slot_uri: dcat:accessURL
    alias: access_urls
    owner: DistributionFormat
    domain_of:
    - DistributionFormat
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DistributionFormat
    domain_of:
    - NamedThing
    - DatasetProperty
    range: uriorcurie
  name:
    name: name
    description: A human-readable name for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:name
    alias: name
    owner: DistributionFormat
    domain_of:
    - NamedThing
    - DatasetProperty
    range: string
  description:
    name: description
    description: A human-readable description for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:description
    alias: description
    owner: DistributionFormat
    domain_of:
    - NamedThing
    - DatasetProperty
    - DatasetRelationship
    range: string
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: DistributionFormat
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>