#!/bin/sh
# Install the pinned bd release for linux amd64 into the given directory.
#
#     scripts/install-bd.sh <bin dir>
#
# The hash is the release's own checksums.txt entry, copied here so a
# replaced release asset fails the check instead of installing.
set -eu

VERSION=1.3.1
SHA256=3219443a9734b89b93fb16ee8d65844759fa1b3cd3cf139c606b7353cfb0715c
ARCHIVE="beads_${VERSION}_linux_amd64.tar.gz"
URL="https://github.com/gastownhall/beads/releases/download/v${VERSION}/${ARCHIVE}"

bin_dir=${1:?usage: install-bd.sh <bin dir>}
download=$(mktemp -d)
trap 'rm -rf "$download"' EXIT

curl -fsSL -o "$download/$ARCHIVE" "$URL"
echo "$SHA256  $download/$ARCHIVE" | sha256sum -c -
mkdir -p "$bin_dir"
tar -xzf "$download/$ARCHIVE" -C "$bin_dir" bd
"$bin_dir/bd" --version
