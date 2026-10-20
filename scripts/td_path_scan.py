"""td_path_scan.py - Prueft das LAUFENDE TouchDesigner-Projekt auf absolute Pfade.

Im TouchDesigner ausfuehren (ueber den TD-MCP, Tool
touchdesigner_execute_python_script) - plattformneutral ueber project.folder:

    exec(open(project.folder + '/scripts/td_path_scan.py').read())

Bewertung:
  HARDCODED -> Parameter im Modus CONSTANT mit absolutem DATEI-Pfad: das ist der
               Fehler, den dieses Projekt nicht mehr haben will (erwartet: 0).
  RESOLVED  -> Modus EXPRESSION: der Wert wird zur Laufzeit aus /config gebaut,
               absolut ist hier nur das *Ergebnis* - kein Verstoss.
  OTHER     -> absolute Strings, die keine Dateipfade sind: OSC-Adressen
               (/song/MIDI_JOJO/...), Muster mit '*' und Node-Pfade (/project1/).
               Die bleiben bewusst Konstanten - kein Verstoss.
  BIND      -> wird ueber par.bindMaster geprueft, NICHT ueber den bindExpr-Text.
               intakt = Kontrollbus via Parent Shortcut (parent.Project.*,
               parent.Annotate.*); kaputt = der Master existiert nicht mehr.

Schreibt den Bericht nach <projekt>/Backup/td_path_scan_report.txt.
"""
import io
import os
import re

RX_ABS = re.compile(r'^(/[A-Za-z]|[A-Za-z]:[\\/]|~)')
# Datei-Pfad erkennen: Laufwerksbuchstabe, bekanntes Dateisystem-Root oder
# Dateiendung im letzten Segment. Alles andere ist OSC/Node-Pfad.
RX_DRIVE = re.compile(r'^[A-Za-z]:[\\/]')
RX_FSROOT = re.compile(
    r'^/(Volumes|Users|home|mnt|media|Applications|Library|System|private|tmp|opt|usr)/')
RX_EXT = re.compile(r'\.[A-Za-z0-9]{1,5}$')

# /config haelt die Kandidaten-Roots bewusst absolut; der MCP-Webserver wird
# vom launch-Skill gesetzt und darf nicht angefasst werden.
SKIP_NODES = ('/config', '/mcp_webserver_base')
REPORT_DIR = 'Backup'
REPORT_NAME = 'td_path_scan_report.txt'


def is_file_path(value):
    """True, wenn value wie ein Dateipfad aussieht (nicht wie eine OSC-Adresse)."""
    if RX_DRIVE.match(value):
        return True
    if RX_FSROOT.match(value):
        return True
    return bool(RX_EXT.search(value.rstrip('/').rsplit('/', 1)[-1]))


hardcoded = []
resolved = []
other = []
binds_ok = 0
binds_broken = []
shortcut_binds = 0

for node in op('/').findChildren():          # noqa: F821  (TD-Global)
    if any(node.path.startswith(s) for s in SKIP_NODES):
        continue
    try:
        pars = node.pars()
    except Exception:
        continue
    for par in pars:
        if par.mode.name == 'BIND' and str(par.bindExpr or ''):
            # Der bindExpr-Text ist nur die Beschriftung (bei diesem Projekt:
            # "parent.Project.par.X" - "Project" ist der Parent Shortcut des
            # COMPs, kein Op). Die Verdrahtung steckt in bindMaster.
            try:
                par.bindMaster
                binds_ok += 1
                if 'Project' in str(par.bindExpr):
                    shortcut_binds += 1
            except Exception as exc:
                binds_broken.append(node.path + ' | ' + par.name + ' | '
                                    + str(par.bindExpr) + ' | ' + str(exc)[:80])
            continue
        try:
            value = par.eval()
        except Exception:
            continue
        if not isinstance(value, str) or not RX_ABS.match(value.strip()):
            continue
        value = value.strip()
        row = node.path + ' | ' + par.name + ' | ' + value
        if not is_file_path(value):
            other.append(row)
        elif par.mode.name == 'CONSTANT':
            hardcoded.append(row)
        else:
            resolved.append(row + '   <- ' + str(par.expr or '')[:70])

lines = ['# TD-Pfad-Scan - ' + str(len(hardcoded)) + ' hardcoded Datei-Pfade, '
         + str(len(resolved)) + ' resolved (EXPRESSION), '
         + str(len(binds_broken)) + ' broken Binds, '
         + str(len(other)) + ' OSC/Node-Pfade (ok)',
         '# Binds intakt: ' + str(binds_ok) + ' (davon ' + str(shortcut_binds)
         + ' via Parent Shortcut "Project")', '',
         '## HARDCODED Datei-Pfade (Modus CONSTANT - muss weg)']
lines += sorted(hardcoded) or ['(keine)']
lines += ['', '## RESOLVED (Modus EXPRESSION - Ergebnis, ok)'] + sorted(resolved)
lines += ['', '## OTHER - OSC-Adressen / Node-Pfade (Modus CONSTANT - ok)'] + sorted(other)
lines += ['', '## BROKEN BINDS (bindMaster nicht aufloesbar - muss weg)'] + (
    sorted(binds_broken) or ['(keine)'])

out_dir = os.path.join(project.folder, REPORT_DIR)   # noqa: F821  (TD-Global)
try:
    os.makedirs(out_dir)
except OSError:
    pass
io.open(os.path.join(out_dir, REPORT_NAME), 'w', encoding='utf-8').write(
    '\n'.join(lines))
print('hardcoded_files=' + str(len(hardcoded))
      + ' resolved=' + str(len(resolved))
      + ' other=' + str(len(other))
      + ' binds_ok=' + str(binds_ok)
      + ' (shortcut=' + str(shortcut_binds) + ')'
      + ' broken_binds=' + str(len(binds_broken))
      + ' -> ' + REPORT_DIR + '/' + REPORT_NAME)
