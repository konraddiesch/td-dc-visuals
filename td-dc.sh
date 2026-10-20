#!/usr/bin/env bash
# td-dc - startet TouchDesigner (und optional das Ableton-Set) mit diesem Projekt
# und oeffnet opencode im Repo.
#
# Laeuft auf macOS und in WSL2 (TouchDesigner laeuft dort auf dem Windows-Host).
# Alle Projektpfade werden aus der Lage dieses Skripts abgeleitet - es gibt
# keinen fest verdrahteten Projektpfad. Pro Maschine ueberschreibbar:
#
#   TD_APP         macOS: Pfad zur TouchDesigner.app
#   ABLETON_APP    macOS: Name/Pfad der Ableton-App (Alias: AL_APP)
#   TD_EXE         WSL:   Pfad zur TouchDesigner.exe
#   DC_ABLETON_SET Pfad zum Ableton-Set (.als); leer = kein Set oeffnen
#                  (Alias: AL_FILE)
#
# App-Pfade sind OS-Konventionen (nicht maschinenspezifisch) und mit
# "os-path-ok" markiert, damit scripts/check_paths.py sie toleriert.
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TOE="$REPO_DIR/digital_carbs_visuals.toe"
ALS="${DC_ABLETON_SET:-${AL_FILE:-}}"

if [ ! -f "$TOE" ]; then
  echo "Projekt nicht gefunden: $TOE" >&2
  exit 1
fi

case "$(uname -s)" in
  Darwin)
    # macOS: Verhalten unveraendert (Defaults wie bisher, per Env ueberschreibbar)
    if [ -z "$ALS" ]; then
      ALS="/Volumes/Musik/Ableton/Projects/DIGITAL CARBS/Visuals/20260926_milla Project/20260926_milla.als"  # os-path-ok
    fi
    open -a "${TD_APP:-/Applications/TouchDesigner.app}" "$TOE"  # os-path-ok
    if [ -n "$ALS" ] && [ -f "$ALS" ]; then
      open -a "${ABLETON_APP:-${AL_APP:-/Applications/Ableton Live 12 Suite.app}}" "$ALS"  # os-path-ok
    fi
    ;;

  Linux)
    if ! grep -qi microsoft /proc/version 2>/dev/null; then
      echo "Kein macOS und kein WSL - bitte TouchDesigner manuell oeffnen: $TOE" >&2
      exit 1
    fi
    # WSL2: TouchDesigner laeuft auf dem Windows-Host -> via cmd.exe starten
    WSL_CMD="${WSL_CMD:-/mnt/c/Windows/System32/cmd.exe}"  # os-path-ok
    TD_EXE="${TD_EXE:-/mnt/c/Program Files/Derivative/TouchDesigner/bin/TouchDesigner.exe}"  # os-path-ok
    if [ ! -x "$WSL_CMD" ]; then
      echo "cmd.exe nicht erreichbar (WSL-Interop deaktiviert?): $WSL_CMD" >&2
      exit 1
    fi
    if [ ! -f "$TD_EXE" ]; then
      echo "TouchDesigner.exe nicht gefunden: $TD_EXE" >&2
      exit 1
    fi
    "$WSL_CMD" /c start "" "$(wslpath -w "$TD_EXE")" "$(wslpath -w "$TOE")"
    if [ -n "$ALS" ] && [ -f "$ALS" ]; then
      "$WSL_CMD" /c start "" "$(wslpath -w "$ALS")"
    fi
    ;;

  *)
    echo "Unbekanntes System: $(uname -s) - bitte TouchDesigner manuell oeffnen: $TOE" >&2
    exit 1
    ;;
esac

if command -v opencode >/dev/null 2>&1; then
  exec opencode "$REPO_DIR"
fi
echo "opencode nicht im PATH - Projekt liegt in $REPO_DIR" >&2
