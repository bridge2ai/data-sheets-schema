# Strict nested-support compatibility fixture

`semantic.json` preserves exact UTF-8 inventory, target, specification and
request byte strings captured at commit
`f2c050c1833c9a5c54c4373a02f6230578a27fe4`, before #4902 production edits.
The original capture receipt SHA-256 is
`40301a379129047d8e0b9b496d8ba505cbd6b80f29a7b84b7670f74f968f3284`.
These are two small synthetic records (ordinary and mixed inline string),
not private canaries, model judgments or calibration labels. All included
strings were copied from receipt-pinned files without rewriting their bytes;
JSON string escaping is only the portable container encoding.

Tests rebuild strict inventories and requests from the retained input record
and captured specification, and compare exact bytes. The ordinary schema YAML
is also retained. The `ordinary_saved` tree contains one exact old pending-calibration capture
and its original descriptor entrypoint. `saved-pins.json` records every byte
pin. Historical absolute path declarations remain unchanged inside those old
artifacts; recheck tests permit reads only from a relocated fixture tree. The
complete external captures remain intact. Old path and planning-code pins
must not be rewritten to make newly built whole plans look identical.
