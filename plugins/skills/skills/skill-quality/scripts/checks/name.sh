#!/bin/bash
# Fails when the name is over 64 characters, uses characters other than
# a-z, 0-9 and -, or is not the directory name.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

name=$(skill_name)
if [ -n "$name" ]; then
  [ "${#name}" -le 64 ] || fail "$skill" "name is ${#name} characters, over 64" "rename it for discovery"
  [[ "$name" =~ ^[a-z0-9-]+$ ]] || fail "$skill" "name '$name' has characters other than a-z, 0-9 and -" "use lowercase words joined by -"
  [ "$name" = "${dir##*/}" ] || fail "$skill" "name '$name' is not the directory name '${dir##*/}'" "make the name and the directory the same"
fi
finish
