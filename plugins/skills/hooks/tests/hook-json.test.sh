#!/bin/bash
# The shared JSON reader decodes each escape to the bytes JSON defines. Every
# plugin ships an identical copy of hook-json.awk, so this one table covers
# them all.

PLUGIN_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"
reader="$PLUGIN_ROOT_DIR/hooks/hook-json.awk"

# hex_of JSON PATH [VIA]: the bytes the reader prints for PATH, in hex.
hex_of() {
  printf '%s' "$1" | LC_ALL=C JSON_MODE=get JSON_PATH="$2" JSON_VIA="${3-}" awk -f "$reader" | od -An -tx1 | tr -d ' \n'
}

# decodes NAME JSON_STRING_BODY HEX: {"s": "<body>"} reads back as HEX.
decodes() {
  expect_equal "$1" "$3" "$(hex_of "{\"s\": \"$2\"}" /s)"
}

decodes "plain text" 'abc' 616263
decodes 'escaped quote' 'a\"b' 612262
decodes 'escaped backslash' 'a\\b' 615c62
decodes 'escaped backslash, then n' '\\n' 5c6e
decodes 'escaped backslash, then u0041' '\\u0041' 5c7530303431
decodes 'escaped backslash, then a quote' 'a\\\"b' 615c2262
decodes 'two escaped backslashes at the end' 'x\\\\' 785c5c
decodes 'slash' '\/' 2f
decodes 'backspace' '\b' 08
decodes 'form feed' '\f' 0c
decodes 'newline, tab, return' '\n\t\r' 0a090d
decodes 'three escapes in a row' 'a\nb\nc\n' 610a620a630a
decodes 'BMP code point' '\u00e9\u20AC' c3a9e282ac
decodes 'surrogate pair, then text' '\ud83d\ude00x' f09f988078
decodes 'upper-case surrogate pair' '\uD83D\uDE00' f09f9880
decodes 'high surrogate, text, low surrogate' '\ud83dx\ude00' eda0bd78edb880
decodes 'high surrogate before a non-surrogate' '\ud83d\u0041' eda0bd41
decodes 'lone low surrogate' '\ude00' edb880
decodes 'high surrogate before an escaped backslash' '\ud83d\\ude00' eda0bd5c7564653030
decodes 'last 3-byte code point' '\uFFFF' efbfbf
decodes 'U+0000 is dropped' 'a\u0000b' 6162
decodes 'quotes in prose' 'say \"hi\" ok\nsay \"hi\" ok' 7361792022686922206f6b0a7361792022686922206f6b
expect_equal "an escaped quote at the end of a string" 7822 "$(hex_of '{"s": "x\"", "t": "y"}' /s)"
expect_equal "a string that ends in an escaped backslash ends there" 79 "$(hex_of '{"s": "x\\", "t": "y"}' /t)"
expect_equal "a string nested in a string is parsed" 615c62 "$(hex_of '{"v": "{\"k\": \"a\\\\b\"}"}' /k /v)"

for bad in '{"s": "a}' '{"s": "a\x"}' '{"s": "a\u00e"}' "{\"s\": \"a$(printf '\t')b\"}" '{"s": "a\"}' '{"s": "a"} 1'; do
  expect_equal "malformed JSON prints nothing: $bad" "" "$(hex_of "$bad" /s)"
done
expect_equal "an unclosed string nested in a string prints nothing" "" "$(hex_of '{"v": "\"abc"}' '' /v)"

finish
