

# Class: RawData 


_Was the "raw" data saved in addition to the preprocessed/cleaned/labeled data? If so, please provide a link or other access point to the "raw" data._

__





URI: [data_sheets_schema:RawData](https://w3id.org/bridge2ai/data-sheets-schema/RawData)





```mermaid
 classDiagram
    class RawData
    click RawData href "../RawData/"
      DatasetProperty <|-- RawData
        click DatasetProperty href "../DatasetProperty/"
      
      RawData : access_url
        
      RawData : description
        
      RawData : id
        
      RawData : name
        
      RawData : raw_data_details
        
      RawData : used_software
        
          
    
        
        
        RawData --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **RawData**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [access_url](access_url.md) | 0..1 <br/> [Uri](Uri.md) | URL or access point for the raw data | direct |
| [raw_data_details](raw_data_details.md) | * <br/> [String](String.md) | Details on raw data availability and access procedures | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [raw_sources](raw_sources.md) | range | [RawData](RawData.md) |
| [DataSubset](DataSubset.md) | [raw_sources](raw_sources.md) | range | [RawData](RawData.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:RawData |
| native | data_sheets_schema:RawData |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: RawData
description: 'Was the "raw" data saved in addition to the preprocessed/cleaned/labeled
  data? If so, please provide a link or other access point to the "raw" data.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  access_url:
    name: access_url
    description: URL or access point for the raw data.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    domain_of:
    - RawData
    range: uri
  raw_data_details:
    name: raw_data_details
    description: 'Details on raw data availability and access procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - RawData
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: RawData
description: 'Was the "raw" data saved in addition to the preprocessed/cleaned/labeled
  data? If so, please provide a link or other access point to the "raw" data.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  access_url:
    name: access_url
    description: URL or access point for the raw data.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    alias: access_url
    owner: RawData
    domain_of:
    - RawData
    range: uri
  raw_data_details:
    name: raw_data_details
    description: 'Details on raw data availability and access procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/preprocessing-cleaning-labeling
    rank: 1000
    slot_uri: dcterms:description
    alias: raw_data_details
    owner: RawData
    domain_of:
    - RawData
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: RawData
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
    owner: RawData
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
    owner: RawData
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
    owner: RawData
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>