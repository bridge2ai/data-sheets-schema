# Enum: ConfidentialityLevelEnum 




_Confidentiality classification levels for datasets indicating the degree of access restrictions and data sensitivity._

_NOTE: This enum classifies data sensitivity and access control (WHO can access), which is orthogonal to DataUsePermissionEnum that specifies use restrictions (WHAT authorized users can do with data). ConfidentialityLevelEnum determines access requirements, while DataUsePermissionEnum uses DUO terms to specify permitted uses once access is granted._



URI: [data_sheets_schema:ConfidentialityLevelEnum](https://w3id.org/bridge2ai/data-sheets-schema/ConfidentialityLevelEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| unrestricted | None | No confidentiality restrictions |
| restricted | None | Restricted access requiring approval or registration |
| confidential | None | Highly confidential with strict access controls |




## Slots

| Name | Description |
| ---  | --- |
| [confidentiality_level](confidentiality_level.md) | Confidentiality classification of the dataset indicating level of access rest... |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: ConfidentialityLevelEnum
description: 'Confidentiality classification levels for datasets indicating the degree
  of access restrictions and data sensitivity.

  NOTE: This enum classifies data sensitivity and access control (WHO can access),
  which is orthogonal to DataUsePermissionEnum that specifies use restrictions (WHAT
  authorized users can do with data). ConfidentialityLevelEnum determines access requirements,
  while DataUsePermissionEnum uses DUO terms to specify permitted uses once access
  is granted.'
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  unrestricted:
    text: unrestricted
    description: No confidentiality restrictions. Data is publicly available with
      no access controls required. Equivalent to public or open access data.
  restricted:
    text: restricted
    description: Restricted access requiring approval or registration. Data contains
      sensitive information requiring controlled access. May require account creation,
      data use agreement, or institutional approval.
  confidential:
    text: confidential
    description: Highly confidential with strict access controls. Data contains highly
      sensitive information with significant privacy or security implications. Typically
      requires IRB approval, formal data use agreements, institutional authorization,
      or other formal vetting processes.

```
</details>