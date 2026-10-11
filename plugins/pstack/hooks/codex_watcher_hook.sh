#!/bin/sh

input=$(cat) || exit 2
printf '%s' "$input" | grep -E '"agent_type"[[:space:]]*:[[:space:]]*"(pstack:)?(developer|reviewer)-codex"' >/dev/null
selected=$?
case "$selected" in
    1) exit 0 ;;
    0) ;;
    *) exit 2 ;;
esac

tokens=$(printf '%s' "$input" | grep -Eo '"([^"\\]|\\.)*"|[][{}:,]|[[:alnum:]_.+-]+') || exit 2
depth=0
key_expected=0
agent_key=0
agent_value=0
while IFS= read -r token; do
    if [ "$agent_value" = 1 ]; then
        case "$token" in
            '"developer-codex"'|'"pstack:developer-codex"'|'"reviewer-codex"'|'"pstack:reviewer-codex"')
                printf '%s' "$input" | timeout -k 1s 5s python3 "${CLAUDE_PLUGIN_ROOT}/hooks/codex_watcher_commands.py" || exit 2
                exit 0 ;;
            *) exit 0 ;;
        esac
    fi
    case "$token" in
        '{'|'[') depth=$((depth + 1)); key_expected=1 ;;
        '}'|']') depth=$((depth - 1)); key_expected=0 ;;
        ',') key_expected=1 ;;
        ':') agent_value=$agent_key; agent_key=0 ;;
        *)
            if [ "$depth" = 1 ] && [ "$key_expected" = 1 ] && [ "$token" = '"agent_type"' ]; then
                agent_key=1
            fi
            key_expected=0 ;;
    esac
done <<EOF
$tokens
EOF
exit 0
