#!/usr/bin/env bash
# Purpose: count, per text block of the refused A21 BC1 worker request, words
#   that an automated safety filter could plausibly react to. A heuristic
#   only: the provider gave no reason for its refusal, and a count of zero or
#   more proves nothing about the cause. It shows where such vocabulary sits
#   (schema context, sources or instructions), to choose a diagnostic.
# Inputs: the request JSON (argument 1). Output: stdout, counts only.
# Serves: the A21 outcome record (owner decision D133). Date: 2026-11-11.
set -u
Q=${1:?request json}
TERMS='weapon|bioweapon|pathogen|virus|toxin|chemical agent|nuclear|radiolog|explosive|malware|exploit|ransomware|vulnerabilit|synthesi[sz]|gain.of.function|select agent|biosafety|dual.use|surveillance|self.harm|suicide|violence|abuse|trafficking|extremis|terroris|jailbreak|ignore (all|previous|prior)'
n=$(jq '.messages[0].content | length' "$Q")
i=0
while [ "$i" -lt "$n" ]; do
  echo "block $i ($(jq -r ".messages[0].content[$i].text" "$Q" | wc -c | tr -d ' ') bytes):"
  jq -r ".messages[0].content[$i].text" "$Q" | grep -oiE "$TERMS" | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -14 | sed 's/^/    /'
  i=$((i + 1))
done
