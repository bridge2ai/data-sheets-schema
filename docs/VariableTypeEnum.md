# Enum: VariableTypeEnum 




_Common data types for variables. Values are mapped to schema.org DataType vocabulary. See https://schema.org/DataType_



URI: [data_sheets_schema:VariableTypeEnum](https://w3id.org/bridge2ai/data-sheets-schema/VariableTypeEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| integer | None | Whole numbers |
| float | None | Floating-point numbers (single precision) |
| double | None | Double-precision floating-point numbers |
| string | None | Text strings |
| boolean | None | True/false values |
| date | None | Date values (without time) |
| datetime | None | Date and time values |
| categorical | None | Categorical/factor variables with finite set of discrete values |
| ordinal | None | Ordered categorical variables where values have a meaningful sequence (e |
| identifier | None | Unique identifiers or keys for records or entities |
| json | None | JSON-encoded data structures |
| array | None | Arrays or lists of values |
| object | None | Complex structured objects or nested data structures |




## Slots

| Name | Description |
| ---  | --- |
| [data_type](data_type.md) | The data type of the variable (e |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: VariableTypeEnum
description: Common data types for variables. Values are mapped to schema.org DataType
  vocabulary. See https://schema.org/DataType
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  integer:
    text: integer
    description: Whole numbers.
    broad_mappings:
    - schema:Integer
  float:
    text: float
    description: Floating-point numbers (single precision).
    broad_mappings:
    - schema:Float
  double:
    text: double
    description: Double-precision floating-point numbers.
    broad_mappings:
    - schema:Number
  string:
    text: string
    description: Text strings.
    broad_mappings:
    - schema:Text
  boolean:
    text: boolean
    description: True/false values.
    broad_mappings:
    - schema:Boolean
  date:
    text: date
    description: Date values (without time).
    broad_mappings:
    - schema:Date
  datetime:
    text: datetime
    description: Date and time values.
    broad_mappings:
    - schema:DateTime
  categorical:
    text: categorical
    description: Categorical/factor variables with finite set of discrete values.
      Often used for nominal data (unordered categories).
    broad_mappings:
    - schema:Text
  ordinal:
    text: ordinal
    description: Ordered categorical variables where values have a meaningful sequence
      (e.g., low/medium/high, strongly disagree/disagree/agree/strongly agree).
    broad_mappings:
    - schema:Text
  identifier:
    text: identifier
    description: Unique identifiers or keys for records or entities.
    broad_mappings:
    - schema:Text
    - schema:identifier
  json:
    text: json
    description: JSON-encoded data structures.
    broad_mappings:
    - schema:Text
  array:
    text: array
    description: Arrays or lists of values. May contain elements of the same or different
      types.
    broad_mappings:
    - schema:ItemList
  object:
    text: object
    description: Complex structured objects or nested data structures.
    broad_mappings:
    - schema:StructuredValue

```
</details>