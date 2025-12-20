

# Class: FutureUseImpact 


_Is there anything about the dataset's composition or collection that might impact future uses or create risks/harm (e.g., unfair treatment, legal or financial risks)? If so, describe these impacts and any mitigation strategies._

__





URI: [data_sheets_schema:FutureUseImpact](https://w3id.org/bridge2ai/data-sheets-schema/FutureUseImpact)





```mermaid
 classDiagram
    class FutureUseImpact
    click FutureUseImpact href "../FutureUseImpact/"
      DatasetProperty <|-- FutureUseImpact
        click DatasetProperty href "../DatasetProperty/"
      
      FutureUseImpact : description
        
      FutureUseImpact : id
        
      FutureUseImpact : impact_details
        
      FutureUseImpact : name
        
      FutureUseImpact : used_software
        
          
    
        
        
        FutureUseImpact --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **FutureUseImpact**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [impact_details](impact_details.md) | * <br/> [String](String.md) | Details on potential impacts, risks, and mitigation strategies | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [future_use_impacts](future_use_impacts.md) | range | [FutureUseImpact](FutureUseImpact.md) |
| [DataSubset](DataSubset.md) | [future_use_impacts](future_use_impacts.md) | range | [FutureUseImpact](FutureUseImpact.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:FutureUseImpact |
| native | data_sheets_schema:FutureUseImpact |
| exact | rai:dataSocialImpact |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: FutureUseImpact
description: 'Is there anything about the dataset''s composition or collection that
  might impact future uses or create risks/harm (e.g., unfair treatment, legal or
  financial risks)? If so, describe these impacts and any mitigation strategies.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataSocialImpact
is_a: DatasetProperty
attributes:
  impact_details:
    name: impact_details
    description: 'Details on potential impacts, risks, and mitigation strategies.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - FutureUseImpact
    - DataProtectionImpact
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: FutureUseImpact
description: 'Is there anything about the dataset''s composition or collection that
  might impact future uses or create risks/harm (e.g., unfair treatment, legal or
  financial risks)? If so, describe these impacts and any mitigation strategies.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataSocialImpact
is_a: DatasetProperty
attributes:
  impact_details:
    name: impact_details
    description: 'Details on potential impacts, risks, and mitigation strategies.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    alias: impact_details
    owner: FutureUseImpact
    domain_of:
    - FutureUseImpact
    - DataProtectionImpact
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: FutureUseImpact
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
    owner: FutureUseImpact
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
    owner: FutureUseImpact
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
    owner: FutureUseImpact
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>