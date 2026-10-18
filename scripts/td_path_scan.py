"""td_path_scan.py - Prueft das LAUFENDE TouchDesigner-Projekt auf absolute Pfade.

Im TouchDesigner ausfuehren (ueber den TD-MCP, Tool
touchdesigner_execute_python_script):

    exec(open('C:/Code/td-dc-visuals/scripts/td_path_scan.py').read())

Bewertung:
  HARDCODED -> Parameter im Modus CONSTANT mit absolutem Pfad: das ist der Fehler,
               den dieses Projekt nicht mehr haben will (erwartet: 1 - s.u.).
  RESOLVED  -> Modus EXPRESSION: der Wert wird zur Laufzeit aus /config gebaut,
               absolut ist hier nur das *Ergebnis* - kein Verstoss.
  BIND      -> h\u00e4ngender BIND auf parent.Project.par.* (bekanntes Steuerungsproblem).

Schreibt den Bericht nach <projekt>/Backup/td_path_scan_report.txt.
"""
import io
import os
import re

RX_ABS = re.compile(r'^(/[A-Za-z]|[A-Za-z]:[\\/]|~)')
# /config haelt die Kandidaten-Roots bewusst absolut; der MCP-Webserver wird
# vom launch-Skill gesetzt und darf nicht angefasst werden.
SKIP_NODES = ('/config', '/mcp_webserver_base')
REPORT_DIR = 'Backup'
REPORT_NAME = 'td_path_scan_report.txt'

hardcoded = []
resolved = []
binds = []

for node in op('/').findChildren():          # noqa: F821  (TD-Global)
    if any(node.path.startswith(s) for s in SKIP_NODES):
        continue
    try:
        pars = node.pars()
    except Exception:
        continue
    for par in pars:
        if par.mode.name == 'BIND' and 'Project' in str(par.bindExpr or ''):
            binds.append(node.path + ' | ' + par.name + ' | ' + str(par.bindExpr))
            continue
        try:
            value = par.eval()
        except Exception:
            continue
        if not isinstance(value, str) or not RX_ABS.match(value.strip()):
            continue
        row = node.path + ' | ' + par.name + ' | ' + value.strip()
        if par.mode.name == 'CONSTANT':
            hardcoded.append(row)
        else:
            resolved.append(row + '   <- ' + str(par.expr or '')[:70])

lines = ['# TD-Pfad-Scan - ' + str(len(hardcoded)) + ' hardcoded, '
         + str(len(resolved)) + ' resolved (EXPRESSION), '
         + str(len(binds)) + ' dangling Project-Binds', '',
         '## HARDCODED (Modus CONSTANT - muss weg)']
lines += sorted(hardcoded) or ['(keine)']
lines += ['', '## RESOLVED (Modus EXPRESSION - Ergebnis, ok)'] + sorted(resolved)
lines += ['', '## DANGLING BINDS parent.Project.*'] + sorted(binds)

out_dir = os.path.join(project.folder, REPORT_DIR)   # noqa: F821  (TD-Global)
try:
    os.makedirs(out_dir)
except OSError:
    pass
io.open(os.path.join(out_dir, REPORT_NAME), 'w', encoding='utf-8').write(
    '\n'.join(lines))
print('hardcoded=' + str(len(hardcoded)) + ' resolved=' + str(len(resolved))
      + ' binds=' + str(len(binds)) + ' -> ' + REPORT_DIR + '/' + REPORT_NAME)
