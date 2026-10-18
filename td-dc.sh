#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOE_FILE="$PROJECT_DIR/digital_carbs_visuals.toe"
TD_APP="${TD_APP:-/Applications/TouchDesigner.app}"
AL_APP="${AL_APP:-/Applications/Ableton Live 12 Suite.app}"
AL_FILE="${AL_FILE:-}"

open -a "$TD_APP" "$TOE_FILE"
if [ -n "$AL_FILE" ] && [ -e "$AL_FILE" ]; then
  open -a "$AL_APP" "$AL_FILE"
fi

exec opencode "$PROJECT_DIR"
