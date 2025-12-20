

# Class: ExtensionMechanism 


_If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so? If so, please describe how those contributions are validated and communicated._

__





URI: [data_sheets_schema:ExtensionMechanism](https://w3id.org/bridge2ai/data-sheets-schema/ExtensionMechanism)





```mermaid
 classDiagram
    class ExtensionMechanism
    click ExtensionMechanism href "../ExtensionMechanism/"
      DatasetProperty <|-- ExtensionMechanism
        click DatasetProperty href "../DatasetProperty/"
      
      ExtensionMechanism : contribution_url
        
      ExtensionMechanism : description
        
      ExtensionMechanism : extension_details
        
      ExtensionMechanism : id
        
      ExtensionMechanism : name
        
      ExtensionMechanism : used_software
        
          
    
        
        
        ExtensionMechanism --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **ExtensionMechanism**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [contribution_url](contribution_url.md) | 0..1 <br/> [Uri](Uri.md) | URL for contribution guidelines or process | direct |
| [extension_details](extension_details.md) | * <br/> [String](String.md) | Details on extension mechanisms, contribution validation, and communication | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [extension_mechanism](extension_mechanism.md) | range | [ExtensionMechanism](ExtensionMechanism.md) |
| [DataSubset](DataSubset.md) | [extension_mechanism](extension_mechanism.md) | range | [ExtensionMechanism](ExtensionMechanism.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:ExtensionMechanism |
| native | data_sheets_schema:ExtensionMechanism |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ExtensionMechanism
description: 'If others want to extend/augment/build on/contribute to the dataset,
  is there a mechanism for them to do so? If so, please describe how those contributions
  are validated and communicated.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  contribution_url:
    name: contribution_url
    description: URL for contribution guidelines or process.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    domain_of:
    - ExtensionMechanism
    range: uri
  extension_details:
    name: extension_details
    description: 'Details on extension mechanisms, contribution validation, and communication.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - ExtensionMechanism
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: ExtensionMechanism
description: 'If others want to extend/augment/build on/contribute to the dataset,
  is there a mechanism for them to do so? If so, please describe how those contributions
  are validated and communicated.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  contribution_url:
    name: contribution_url
    description: URL for contribution guidelines or process.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    alias: contribution_url
    owner: ExtensionMechanism
    domain_of:
    - ExtensionMechanism
    range: uri
  extension_details:
    name: extension_details
    description: 'Details on extension mechanisms, contribution validation, and communication.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    alias: extension_details
    owner: ExtensionMechanism
    domain_of:
    - ExtensionMechanism
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: ExtensionMechanism
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
    owner: ExtensionMechanism
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
    owner: ExtensionMechanism
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
    owner: ExtensionMechanism
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>