

# Class: Erratum 


_Is there an erratum? If so, please provide a link or other access point._

__





URI: [data_sheets_schema:Erratum](https://w3id.org/bridge2ai/data-sheets-schema/Erratum)





```mermaid
 classDiagram
    class Erratum
    click Erratum href "../Erratum/"
      DatasetProperty <|-- Erratum
        click DatasetProperty href "../DatasetProperty/"
      
      Erratum : description
        
      Erratum : erratum_details
        
      Erratum : erratum_url
        
      Erratum : id
        
      Erratum : name
        
      Erratum : used_software
        
          
    
        
        
        Erratum --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **Erratum**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [erratum_url](erratum_url.md) | 0..1 <br/> [Uri](Uri.md) | URL or access point for the erratum | direct |
| [erratum_details](erratum_details.md) | * <br/> [String](String.md) | Details on any errata or corrections to the dataset | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [errata](errata.md) | range | [Erratum](Erratum.md) |
| [DataSubset](DataSubset.md) | [errata](errata.md) | range | [Erratum](Erratum.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Erratum |
| native | data_sheets_schema:Erratum |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Erratum
description: 'Is there an erratum? If so, please provide a link or other access point.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  erratum_url:
    name: erratum_url
    description: URL or access point for the erratum.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    domain_of:
    - Erratum
    range: uri
  erratum_details:
    name: erratum_details
    description: 'Details on any errata or corrections to the dataset.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - Erratum
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: Erratum
description: 'Is there an erratum? If so, please provide a link or other access point.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  erratum_url:
    name: erratum_url
    description: URL or access point for the erratum.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    alias: erratum_url
    owner: Erratum
    domain_of:
    - Erratum
    range: uri
  erratum_details:
    name: erratum_details
    description: 'Details on any errata or corrections to the dataset.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    alias: erratum_details
    owner: Erratum
    domain_of:
    - Erratum
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: Erratum
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
    owner: Erratum
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
    owner: Erratum
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
    owner: Erratum
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>