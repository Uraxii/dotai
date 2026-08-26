#!/usr/bin/env bash
# run_headless.sh - drive Godot 4.x headless from a shell, generically.
#
# Discovers the Godot binary (Godots flatpak layout by default, overridable),
# runs it with --headless, filters the known-harmless dummy-renderer exit noise,
# and preserves the REAL exit code and real error lines.
#
# Usage:
#   run_headless.sh --project <dir> -s res://path/script.gd -- [script args...]
#   run_headless.sh --project <dir> --import
#   run_headless.sh --project <dir> <any raw godot args...>
#
# Wrapper options must come FIRST. The first token that is not a wrapper
# option ends option parsing; everything from there is forwarded to Godot
# VERBATIM (transparent passthrough), including Godot's own `--` separator.
# To pass user args to a script, use Godot's convention:
#   -s res://x.gd -- arg1 arg2   (args land in OS.get_cmdline_user_args()).
#
# Options (must precede raw Godot args):
#   --project <dir>   Godot project dir (folder holding project.godot). Required
#                     for most actions. Passed through as --path <dir>.
#   --godot <path>    Explicit Godot binary. Overrides discovery + $GODOT_BIN.
#   --no-filter       Do not filter the harmless leak/RID noise (raw output).
#   -h|--help         Show this help.
#
# Env:
#   GODOT_BIN         If set and executable, used as the binary.
#   GODOT_GLOB        Override the discovery glob (see DEFAULT_GLOB below).
#
# Exit code is Godot's own exit code (from your script's quit(code) or engine).
set -uo pipefail

# --- EDIT HERE if your Godot install lives elsewhere -------------------------
# Discovery glob for the Godots flatpak manager on this machine. Newest match
# (highest version string) wins. Adjust the pattern for a different install.
DEFAULT_GLOB="$HOME/.var/app/io.github.MakovWait.Godots/data/godot/app_userdata/Godots/versions/*/Godot_v*_linux*.x86_64"
# -----------------------------------------------------------------------------

GLOB="${GODOT_GLOB:-$DEFAULT_GLOB}"
GODOT=""
PROJECT=""
FILTER=1
PASS_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?--project needs a dir}"; shift 2;;
    --godot)   GODOT="${2:?--godot needs a path}"; shift 2;;
    --no-filter) FILTER=0; shift;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    # First non-wrapper token ends parsing; forward the rest verbatim to Godot
    # (transparent - Godot's own `--` separator is preserved).
    *) PASS_ARGS+=("$@"); break;;
  esac
done

discover_godot() {
  [[ -n "$GODOT" ]] && { echo "$GODOT"; return; }
  [[ -n "${GODOT_BIN:-}" && -x "${GODOT_BIN:-}" ]] && { echo "$GODOT_BIN"; return; }
  # Newest match by version-sorted name.
  local match
  match=$(ls -1 $GLOB 2>/dev/null | sort -V | tail -n1)
  echo "$match"
}

BIN="$(discover_godot)"
if [[ -z "$BIN" || ! -x "$BIN" ]]; then
  echo "run_headless.sh: could not find a Godot binary." >&2
  echo "  glob: $GLOB" >&2
  echo "  set GODOT_BIN, pass --godot <path>, or fix DEFAULT_GLOB." >&2
  exit 127
fi

CMD=("$BIN" --headless)
[[ -n "$PROJECT" ]] && CMD+=(--path "$PROJECT")
CMD+=("${PASS_ARGS[@]}")

echo "run_headless.sh: $BIN --headless ${PROJECT:+--path $PROJECT} ${PASS_ARGS[*]}" >&2

# Known-harmless noise from the headless dummy renderer at shutdown. These are
# NOT failures; the exit code is the source of truth. Extend if your engine
# build prints other benign shutdown lines.
NOISE='(Pages in use|RID allocations .* leaked at exit|Leaked instance|ObjectDB instances leaked at exit|resources still in use at exit|were leaked)'

if [[ $FILTER -eq 1 ]]; then
  # Preserve Godot's exit code through the pipe (pipefail is set).
  "${CMD[@]}" 2>&1 | grep -Ev "$NOISE"
  rc=${PIPESTATUS[0]}
else
  "${CMD[@]}"
  rc=$?
fi

echo "run_headless.sh: exit code $rc" >&2
exit "$rc"
