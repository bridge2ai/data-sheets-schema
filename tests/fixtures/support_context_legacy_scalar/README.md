# Genuine pre-context scalar-policy fixtures

Captured from commit `3d256fccd8e37124cc78e4d56ef93b9481b34473`, before #4904,
using the original scalar-reference policy and no context-policy option.
`provenance.json` pins the root-run receipt and each copied artifact/source string.
`semantic.json` packages exact original UTF-8 inventory, target, specification and
request bytes for the ordinary and mixed neutral cases. Expected bytes were not
rebuilt with the new implementation.

The pending-report closure, descriptor and missing report retain original bytes,
including any historical recorded paths inside content-addressed evidence.
Readback must use the copied evidence and must not consult those old paths.
No private records, provider responses or scientific labels are included; both
selected controls remain pending and unscored.
