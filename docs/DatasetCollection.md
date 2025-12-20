

# Class: DatasetCollection 


_A collection of related datasets, likely containing multiple files of multiple potential purposes and properties._





URI: [data_sheets_schema:DatasetCollection](https://w3id.org/bridge2ai/data-sheets-schema/DatasetCollection)





```mermaid
 classDiagram
    class DatasetCollection
    click DatasetCollection href "../DatasetCollection/"
      Information <|-- DatasetCollection
        click Information href "../Information/"
      
      DatasetCollection : compression
        
          
    
        
        
        DatasetCollection --> "0..1" CompressionEnum : compression
        click CompressionEnum href "../CompressionEnum/"
    

        
      DatasetCollection : conforms_to
        
      DatasetCollection : conforms_to_class
        
      DatasetCollection : conforms_to_schema
        
      DatasetCollection : created_by
        
      DatasetCollection : created_on
        
      DatasetCollection : description
        
      DatasetCollection : doi
        
      DatasetCollection : download_url
        
      DatasetCollection : id
        
      DatasetCollection : issued
        
      DatasetCollection : keywords
        
      DatasetCollection : language
        
      DatasetCollection : last_updated_on
        
      DatasetCollection : license
        
      DatasetCollection : modified_by
        
      DatasetCollection : name
        
      DatasetCollection : page
        
      DatasetCollection : publisher
        
      DatasetCollection : resources
        
          
    
        
        
        DatasetCollection --> "*" Dataset : resources
        click Dataset href "../Dataset/"
    

        
      DatasetCollection : status
        
      DatasetCollection : title
        
      DatasetCollection : version
        
      DatasetCollection : was_derived_from
        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [Information](Information.md)
        * **DatasetCollection**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [resources](resources.md) | * <br/> [Dataset](Dataset.md) | Sub-resources or component datasets | direct |
| [compression](compression.md) | 0..1 <br/> [CompressionEnum](CompressionEnum.md) | compression format used, if any | [Information](Information.md) |
| [conforms_to](conforms_to.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [conforms_to_class](conforms_to_class.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [conforms_to_schema](conforms_to_schema.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [created_by](created_by.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [created_on](created_on.md) | 0..1 <br/> [Datetime](Datetime.md) |  | [Information](Information.md) |
| [doi](doi.md) | 0..1 <br/> [String](String.md) | digital object identifier | [Information](Information.md) |
| [download_url](download_url.md) | 0..1 <br/> [Uri](Uri.md) | URL from which the data can be downloaded | [Information](Information.md) |
| [issued](issued.md) | 0..1 <br/> [Datetime](Datetime.md) |  | [Information](Information.md) |
| [keywords](keywords.md) | * <br/> [String](String.md) |  | [Information](Information.md) |
| [language](language.md) | 0..1 <br/> [String](String.md) | language in which the information is expressed | [Information](Information.md) |
| [last_updated_on](last_updated_on.md) | 0..1 <br/> [Datetime](Datetime.md) |  | [Information](Information.md) |
| [license](license.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [modified_by](modified_by.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [page](page.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [publisher](publisher.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) |  | [Information](Information.md) |
| [status](status.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [title](title.md) | 0..1 <br/> [String](String.md) | the official title of the element | [Information](Information.md) |
| [version](version.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [was_derived_from](was_derived_from.md) | 0..1 <br/> [String](String.md) |  | [Information](Information.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for a thing | [NamedThing](NamedThing.md) |









## Aliases


* file collection
* dataset collection
* data resource collection


## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DatasetCollection |
| native | data_sheets_schema:DatasetCollection |
| exact | dcat:Dataset |
| close | dcat:Catalog |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DatasetCollection
description: A collection of related datasets, likely containing multiple files of
  multiple potential purposes and properties.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
aliases:
- file collection
- dataset collection
- data resource collection
exact_mappings:
- dcat:Dataset
close_mappings:
- dcat:Catalog
is_a: Information
slots:
- resources
slot_usage:
  resources:
    name: resources
    inlined_as_list: true
tree_root: true

```
</details>

### Induced

<details>
```yaml
name: DatasetCollection
description: A collection of related datasets, likely containing multiple files of
  multiple potential purposes and properties.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
aliases:
- file collection
- dataset collection
- data resource collection
exact_mappings:
- dcat:Dataset
close_mappings:
- dcat:Catalog
is_a: Information
slot_usage:
  resources:
    name: resources
    inlined_as_list: true
attributes:
  resources:
    name: resources
    description: Sub-resources or component datasets. Used in DatasetCollection to
      contain Dataset objects, and in Dataset to allow nested resource structures.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    alias: resources
    owner: DatasetCollection
    domain_of:
    - DatasetCollection
    - Dataset
    range: Dataset
    multivalued: true
    inlined_as_list: true
  compression:
    name: compression
    description: compression format used, if any. e.g., gzip, bzip2, zip
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcat:compressFormat
    alias: compression
    owner: DatasetCollection
    domain_of:
    - Information
    range: CompressionEnum
  conforms_to:
    name: conforms_to
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:conformsTo
    alias: conforms_to
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  conforms_to_class:
    name: conforms_to_class
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:conformsTo
    alias: conforms_to_class
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  conforms_to_schema:
    name: conforms_to_schema
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:conformsTo
    alias: conforms_to_schema
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  created_by:
    name: created_by
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:creator
    alias: created_by
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  created_on:
    name: created_on
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:created
    alias: created_on
    owner: DatasetCollection
    domain_of:
    - Information
    range: datetime
  doi:
    name: doi
    description: digital object identifier
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:identifier
    alias: doi
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
    pattern: 10\.\d{4,}\/.+
  download_url:
    name: download_url
    description: URL from which the data can be downloaded. This is not the same as
      the landing page, which is a page that describes the dataset. Rather, this URL
      points directly to the data itself.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    exact_mappings:
    - schema:url
    rank: 1000
    slot_uri: dcat:downloadURL
    alias: download_url
    owner: DatasetCollection
    domain_of:
    - Information
    range: uri
  issued:
    name: issued
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:issued
    alias: issued
    owner: DatasetCollection
    domain_of:
    - Information
    range: datetime
  keywords:
    name: keywords
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcat:keyword
    alias: keywords
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
    multivalued: true
  language:
    name: language
    description: language in which the information is expressed
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    exact_mappings:
    - schema:inLanguage
    rank: 1000
    slot_uri: dcterms:language
    alias: language
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  last_updated_on:
    name: last_updated_on
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:modified
    alias: last_updated_on
    owner: DatasetCollection
    domain_of:
    - Information
    range: datetime
  license:
    name: license
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:license
    alias: license
    owner: DatasetCollection
    domain_of:
    - Software
    - Information
    range: string
  modified_by:
    name: modified_by
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:contributor
    alias: modified_by
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  page:
    name: page
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcat:landingPage
    alias: page
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  publisher:
    name: publisher
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:publisher
    alias: publisher
    owner: DatasetCollection
    domain_of:
    - Information
    range: uriorcurie
  status:
    name: status
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:type
    alias: status
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  title:
    name: title
    description: the official title of the element
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:title
    alias: title
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  version:
    name: version
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    rank: 1000
    slot_uri: dcterms:hasVersion
    alias: version
    owner: DatasetCollection
    domain_of:
    - Software
    - Information
    range: string
  was_derived_from:
    name: was_derived_from
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema
    exact_mappings:
    - dcterms:source
    rank: 1000
    slot_uri: prov:wasDerivedFrom
    alias: was_derived_from
    owner: DatasetCollection
    domain_of:
    - Information
    range: string
  id:
    name: id
    description: A unique identifier for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:identifier
    identifier: true
    alias: id
    owner: DatasetCollection
    domain_of:
    - NamedThing
    - DatasetProperty
    range: uriorcurie
  name:
    name: name
    description: A human-readable name for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:name
    alias: name
    owner: DatasetCollection
    domain_of:
    - NamedThing
    - DatasetProperty
    range: string
  description:
    name: description
    description: A human-readable description for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:description
    alias: description
    owner: DatasetCollection
    domain_of:
    - NamedThing
    - DatasetProperty
    - DatasetRelationship
    range: string
tree_root: true

```
</details>