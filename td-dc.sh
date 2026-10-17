#!/usr/bin/env bash
set -e

PROJECT_DIR="/Volumes/Visuals/TouchDesigner/td-dc-visuals"
TOE_FILE="$PROJECT_DIR/digital_carbs_visuals.toe"
TD_APP="/Applications/TouchDesigner.app"
AL_APP="/Applications/Ableton Live 12 Suite.app"
AL_FILE="/Volumes/Musik/Ableton/Projects/DIGITAL CARBS/Visuals/20260926_milla Project/20260926_milla.als"

open -a "$TD_APP" "$TOE_FILE"
open -a "$AL_APP" "$AL_FILE"

exec opencode "$PROJECT_DIR"