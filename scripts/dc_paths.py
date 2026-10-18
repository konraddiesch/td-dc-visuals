"""dc_paths - OS-agnostische Pfadaufloesung fuer digital_carbs_visuals.toe.

Geladen von /config/paths (Text DAT, Module-Flag, "Sync File" -> ./scripts/dc_paths.py).
Aufruf in Parameter-Expressions, z.B.:

    mod('/config/paths').media('Library/Recordings/Holz/totholz_1.mov')
    mod('/config/paths').lut('The One LUT/theOne.cube')
    mod('/config/paths').vst3('neutone')
    mod('/config/paths').samples('Geo/defcam.tog')
    mod('/config/paths').install('Config/PanelShortcuts.txt')
    mod('/config/paths').ableton_set()

Medien-Root - erster existierender Treffer gewinnt:
    DC_MEDIA_ROOT (Umgebungsvariable)  ->  /Volumes/Visuals (macOS)  ->  D:/ (Windows)
Der Root zeigt auf das Elternverzeichnis von Library/ (und Live/).
Keine absoluten Pfade in Nutzer-Parametern - nur hier, als Kandidatenliste.
"""

import os
import unicodedata

ENV_MEDIA = "DC_MEDIA_ROOT"
ENV_LUT = "DC_LUT_ROOT"
ENV_VST3 = "DC_VST3_ROOT"
ENV_ALS = "DC_ABLETON_SET"
ENV_SAMPLES = "DC_TD_SAMPLES"

# Kandidaten pro OS - Reihenfolge = Fallback-Reihenfolge
MAC_ROOT = "/Volumes/Visuals"
WIN_ROOT = "D:/"

MIX_MARKER = "/Library/Recordings"          # Media-Root ist gueltig, wenn das existiert
SAMPLES_CANDIDATES = [
    "C:/Program Files/Derivative/TouchDesigner/Samples",
    "/Applications/TouchDesigner.app/Contents/Resources/tfs/Samples",
]
INSTALL_CANDIDATES = [
    "C:/Program Files/Derivative/TouchDesigner",
    "/Applications/TouchDesigner.app/Contents/Resources/tfs",
]
VST3_CANDIDATES = [
    "C:/Program Files/Common Files/VST3",
    "/Library/Audio/Plug-Ins/VST3",
]
ALS_CANDIDATES = []                         # optional: pro Maschine via DC_ABLETON_SET


# --------------------------------------------------------------------------- #
# Helfer
# --------------------------------------------------------------------------- #

def _clean(path):
    """Windows-Backslashes und abschliessende Trenner vereinheitlichen."""
    return unicodedata.normalize("NFC", str(path)).replace("\\", "/").rstrip("/")


def _first(candidates, check):
    """Erster Kandidat, der `check` besteht; leere/unpruefbare werden uebersprungen."""
    for cand in candidates:
        if not cand:
            continue
        cand = _clean(cand)
        try:
            if check(cand):
                return cand
        except Exception:
            continue
    return ""


def _join(root, parts):
    if not root:
        return ""
    rel = "/".join(unicodedata.normalize("NFC", str(p)).strip("/") for p in parts)
    return _clean(root) + "/" + rel


def _td_attr(name):
    """app.<name> aus dem DAT-Namespace holen (app ist TD-Global, kein Import)."""
    try:
        return _clean(getattr(app, name))  # noqa: F821
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# Roots
# --------------------------------------------------------------------------- #

def media_root():
    """Wurzel, unter der Library/ (Recordings, Videos, LUTs) liegt."""
    return _first([os.environ.get(ENV_MEDIA), MAC_ROOT, WIN_ROOT],
                  lambda c: os.path.isdir(c + MIX_MARKER))


def lut_root():
    return _first([os.environ.get(ENV_LUT), _join(media_root(), ["Library/LUTs"])],
                  os.path.isdir)


def vst3_root():
    return _first([os.environ.get(ENV_VST3)] + VST3_CANDIDATES +
                  [os.path.expanduser("~/.vst3")], os.path.isdir)


def samples_folder():
    """TD-Samples-Ordner - bevorzugt direkt aus der TD-Installation."""
    return _clean(_td_attr("samplesFolder")) or _first(
        [os.environ.get(ENV_SAMPLES)] + SAMPLES_CANDIDATES, os.path.isdir)


def install_folder():
    """TD-Installationsordner (Config/, Samples/)."""
    return _clean(_td_attr("installFolder")) or _first(
        INSTALL_CANDIDATES, lambda c: os.path.isdir(c + "/Config"))


# --------------------------------------------------------------------------- #
# Pfad-Bauer
# --------------------------------------------------------------------------- #

def media(*parts):
    return _join(media_root(), parts)


def lut(*parts):
    return _join(lut_root(), parts)


def samples(*parts):
    return _join(samples_folder(), parts)


def install(*parts):
    return _join(install_folder(), parts)


def vst3(*parts):
    """Plugin-Pfad unter vst3_root(); probt die Bundle-Layouts pro OS."""
    root = vst3_root()
    rel = "/".join(str(p).strip("/") for p in parts)
    leaf = rel.rsplit("/", 1)[-1]
    stem = leaf[:-5] if leaf.endswith(".vst3") else leaf
    probes = []
    for base in [rel, rel + ".vst3"]:
        probes += [base + "/Contents/x86_64-win/" + stem + ".vst3",
                   base + "/Contents/MacOS/" + stem,
                   base]
    if not root:
        return ""
    for cand in probes:
        if os.path.exists(root + "/" + cand):
            return root + "/" + cand
    return ""


def ableton_set():
    """Ableton-Set (.als) dieser Maschine; ohne DC_ABLETON_SET leer."""
    return _first([os.environ.get(ENV_ALS)] + ALS_CANDIDATES, os.path.isfile)


def ocio_config():
    """ACES/OCIO-Config aus der TD-Installation (statt hartkodiertem Pfad)."""
    return samples("OpenColorIO/aces_1.3.0/studio-config-v2.0.0_aces-v1.3_ocio-v2.1.ocio")


# --------------------------------------------------------------------------- #
# Diagnose (sichtbar im /config-COMP)
# --------------------------------------------------------------------------- #

def report():
    return ("media=" + (media_root() or "NOT-FOUND")
            + " env=" + str(os.environ.get(ENV_MEDIA) or "-")
            + " | lut=" + (lut_root() or "-")
            + " | vst3=" + (vst3_root() or "-")
            + " | samples=" + (samples_folder() or "-"))


def check():
    """Existenz-Check der Roots; gibt Liste menschenlesbarer Zeilen zurueck."""
    rows = [("media_root", media_root()), ("lut_root", lut_root()),
            ("vst3_root", vst3_root()), ("samples", samples_folder()),
            ("install", install_folder()),
            ("movie", media("Library/Recordings/Holz/totholz_1.mov")),
            ("lut-file", lut("The One LUT/theOne.cube")),
            ("vst-file", vst3("neutone")),
            ("ocio", ocio_config()),
            ("ableton-set", ableton_set())]
    return [[k, v, "OK" if (v and os.path.exists(v)) else "MISSING"] for k, v in rows]
