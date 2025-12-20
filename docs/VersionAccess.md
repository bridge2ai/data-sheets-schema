

# Class: VersionAccess 


_Will older versions of the dataset continue to be supported/hosted/maintained? If so, how? If not, how will obsolescence be communicated to dataset consumers?_

__





URI: [data_sheets_schema:VersionAccess](https://w3id.org/bridge2ai/data-sheets-schema/VersionAccess)





```mermaid
 classDiagram
    class VersionAccess
    click VersionAccess href "../VersionAccess/"
      DatasetProperty <|-- VersionAccess
        click DatasetProperty href "../DatasetProperty/"
      
      VersionAccess : description
        
      VersionAccess : id
        
      VersionAccess : latest_version_doi
        
      VersionAccess : name
        
      VersionAccess : used_software
        
          
    
        
        
        VersionAccess --> "*" Software : used_software
        click Software href "../Software/"
    

        
      VersionAccess : version_details
        
      VersionAccess : versions_available
        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **VersionAccess**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [latest_version_doi](latest_version_doi.md) | 0..1 <br/> [String](String.md) | DOI or URL of the latest dataset version | direct |
| [versions_available](versions_available.md) | * <br/> [String](String.md) | List of available versions with metadata | direct |
| [version_details](version_details.md) | * <br/> [String](String.md) | Details on version support policies and obsolescence communication | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [version_access](version_access.md) | range | [VersionAccess](VersionAccess.md) |
| [DataSubset](DataSubset.md) | [version_access](version_access.md) | range | [VersionAccess](VersionAccess.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:VersionAccess |
| native | data_sheets_schema:VersionAccess |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: VersionAccess
description: 'Will older versions of the dataset continue to be supported/hosted/maintained?
  If so, how? If not, how will obsolescence be communicated to dataset consumers?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  latest_version_doi:
    name: latest_version_doi
    description: DOI or URL of the latest dataset version.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    domain_of:
    - VersionAccess
    range: string
  versions_available:
    name: versions_available
    description: List of available versions with metadata.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    domain_of:
    - VersionAccess
    range: string
    multivalued: true
  version_details:
    name: version_details
    description: 'Details on version support policies and obsolescence communication.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - VersionAccess
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: VersionAccess
description: 'Will older versions of the dataset continue to be supported/hosted/maintained?
  If so, how? If not, how will obsolescence be communicated to dataset consumers?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  latest_version_doi:
    name: latest_version_doi
    description: DOI or URL of the latest dataset version.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    alias: latest_version_doi
    owner: VersionAccess
    domain_of:
    - VersionAccess
    range: string
  versions_available:
    name: versions_available
    description: List of available versions with metadata.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    alias: versions_available
    owner: VersionAccess
    domain_of:
    - VersionAccess
    range: string
    multivalued: true
  version_details:
    name: version_details
    description: 'Details on version support policies and obsolescence communication.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    alias: version_details
    owner: VersionAccess
    domain_of:
    - VersionAccess
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: VersionAccess
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
    owner: VersionAccess
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
    owner: VersionAccess
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
    owner: VersionAccess
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>