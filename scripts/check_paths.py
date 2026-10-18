#!/usr/bin/env python3
"""check_paths.py - Guard gegen absolute OS-Pfade in versionierten Dateien.

Findet maschinenspezifische Pfade (macOS-Volumes, Windows-Laufwerke, WSL-Mounts,
/Users, /Applications) in allen von git verfolgten *Textdateien*.

  Fehler   -> Exit-Code 1  (Code, Config, Skripte)
  Warnung  -> Exit-Code 0  (*.md: Doku darf Maschinenpfade dokumentieren)

Absichtliche Ausnahmen pro Zeile mit dem Marker  os-path-ok  kennzeichnen.
Binaere Projektdateien (.toe/.tox) sind hier nicht pruefbar - dafuer
scripts/td_path_scan.py im laufenden TouchDesigner ausfuehren.

    python3 scripts/check_paths.py
"""
import re
import subprocess
import sys

PATTERNS = [
    (re.compile(r'/Volumes/[A-Za-z]'), 'macOS-Volume'),
    (re.compile(r'/mnt/[a-z]/'), 'WSL-Mount'),
    (re.compile(r'/Users/[A-Za-z]'), 'macOS-Home'),
    (re.compile(r'/Applications/'), 'macOS-App'),
    (re.compile(r'(^|[\s"\'=(])[A-Za-z]:[\\/]'), 'Windows-Laufwerk'),
    (re.compile(r'\\\\[A-Za-z0-9._-]+\\'), 'Windows-UNC'),
]

MARKER = 'os-path-ok'
# dc_paths.py enthaelt bewusst die Kandidaten-Roots (genau eine Stelle im Repo)
SKIP_FILES = {'scripts/check_paths.py', 'scripts/dc_paths.py'}
MAX_BYTES = 2 * 1024 * 1024


def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-z'], capture_output=True, check=True)
    return [f for f in out.stdout.decode('utf-8', 'replace').split('\0') if f]


def main():
    errors = warnings = checked = skipped = 0
    for name in tracked_files():
        if name in SKIP_FILES:
            continue
        try:
            with open(name, 'rb') as fh:
                raw = fh.read(MAX_BYTES)
        except OSError:
            continue
        if b'\0' in raw:                      # Binaerdatei (.toe/.tox/.chan ...)
            skipped += 1
            continue
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            skipped += 1
            continue
        checked += 1
        is_doc = name.lower().endswith(('.md', '.txt'))
        for lineno, line in enumerate(text.splitlines(), 1):
            if MARKER in line:
                continue
            for rx, kind in PATTERNS:
                m = rx.search(line)
                if not m:
                    continue
                label = 'WARN' if is_doc else 'ERROR'
                if is_doc:
                    warnings += 1
                else:
                    errors += 1
                print(f'{label} {name}:{lineno} [{kind}] {m.group(0).strip()} '
                      f'... {line.strip()[:90]}')
                break

    print(f'\n{checked} Textdateien geprueft, {skipped} uebersprungen (binaer)'
          f' - {errors} Fehler, {warnings} Warnungen')
    if errors:
        print('Absolute Pfade in Code/Config: bitte ueber scripts/dc_paths.py '
              'bzw. relative Pfade loesen (oder Marker "os-path-ok" setzen).')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
