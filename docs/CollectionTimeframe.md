

# Class: CollectionTimeframe 


_Over what timeframe was the data collected, and does this timeframe match the creation timeframe of the underlying data?_

__





URI: [data_sheets_schema:CollectionTimeframe](https://w3id.org/bridge2ai/data-sheets-schema/CollectionTimeframe)





```mermaid
 classDiagram
    class CollectionTimeframe
    click CollectionTimeframe href "../CollectionTimeframe/"
      DatasetProperty <|-- CollectionTimeframe
        click DatasetProperty href "../DatasetProperty/"
      
      CollectionTimeframe : description
        
      CollectionTimeframe : end_date
        
      CollectionTimeframe : id
        
      CollectionTimeframe : name
        
      CollectionTimeframe : start_date
        
      CollectionTimeframe : timeframe_details
        
      CollectionTimeframe : used_software
        
          
    
        
        
        CollectionTimeframe --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **CollectionTimeframe**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [start_date](start_date.md) | 0..1 <br/> [Date](Date.md) | Start date of data collection | direct |
| [end_date](end_date.md) | 0..1 <br/> [Date](Date.md) | End date of data collection | direct |
| [timeframe_details](timeframe_details.md) | * <br/> [String](String.md) | Details on the collection timeframe and relationship to data creation dates | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [collection_timeframes](collection_timeframes.md) | range | [CollectionTimeframe](CollectionTimeframe.md) |
| [DataSubset](DataSubset.md) | [collection_timeframes](collection_timeframes.md) | range | [CollectionTimeframe](CollectionTimeframe.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:CollectionTimeframe |
| native | data_sheets_schema:CollectionTimeframe |
| exact | rai:dataCollectionTimeframe |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: CollectionTimeframe
description: 'Over what timeframe was the data collected, and does this timeframe
  match the creation timeframe of the underlying data?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataCollectionTimeframe
is_a: DatasetProperty
attributes:
  start_date:
    name: start_date
    description: Start date of data collection
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - CollectionTimeframe
    range: date
  end_date:
    name: end_date
    description: End date of data collection
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - CollectionTimeframe
    range: date
  timeframe_details:
    name: timeframe_details
    description: 'Details on the collection timeframe and relationship to data creation
      dates.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - CollectionTimeframe
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: CollectionTimeframe
description: 'Over what timeframe was the data collected, and does this timeframe
  match the creation timeframe of the underlying data?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataCollectionTimeframe
is_a: DatasetProperty
attributes:
  start_date:
    name: start_date
    description: Start date of data collection
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: start_date
    owner: CollectionTimeframe
    domain_of:
    - CollectionTimeframe
    range: date
  end_date:
    name: end_date
    description: End date of data collection
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: end_date
    owner: CollectionTimeframe
    domain_of:
    - CollectionTimeframe
    range: date
  timeframe_details:
    name: timeframe_details
    description: 'Details on the collection timeframe and relationship to data creation
      dates.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    alias: timeframe_details
    owner: CollectionTimeframe
    domain_of:
    - CollectionTimeframe
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: CollectionTimeframe
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
    owner: CollectionTimeframe
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
    owner: CollectionTimeframe
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
    owner: CollectionTimeframe
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>