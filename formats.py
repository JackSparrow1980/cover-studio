#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 Giuseppe Stramandino
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Cover Studio - definizione dei formati (modello a SEZIONI) e conversioni.
# Modulo indipendente dall'interfaccia.
#
# MODELLO A SEZIONI
#   Un formato "cover" e' un blocco rettangolare diviso in N sezioni affiancate
#   orizzontalmente (massimo 3). Le pieghe cadono ai confini tra le sezioni e
#   sono SOLO guide a video (mai stampate). Il taglio e' unicamente sul blocco
#   esterno (i crocini agli angoli).
#
# CAMPO "spine_section"
#   Indica QUALE sezione e' la spina (indice 0..2) oppure None se non c'e'.
#   Se impostato, il nome mostrato include la larghezza della spina tra
#   parentesi, calcolata in automatico: es. "Cover DVD (14mm)".
#   Per i formati senza spina (label tonda, libretto a 2 sezioni...) None ->
#   nessuna parentesi.
#
# FORMATI BASE vs PERSONALIZZATI
#   - BASE_FORMATS: fissi, non modificabili (riferimenti sicuri).
#   - personalizzati: creati dall'utente, salvati in ~/.config/cover-studio/
#     formats.json, condivisibili.
#
# REGOLE UNITA'
#   - 'unit' ("px" o "mm"): unita' di altezza e larghezze sezione.
#   - mm (fisici) e px (nominali a 'dpi') si ricavano l'uno dall'altro.
#   - 'print_w_mm': None = misura naturale; altrimenti larghezza calibrata
#     (altezza sempre proporzionale, niente distorsione).

import os
import json
import copy

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0
A4_LANDSCAPE_MM = (297.0, 210.0)
DEFAULT_DPI = 300
MAX_SECTIONS = 3

# Limiti realistici per dischi ed etichette adesive (mm), basati sui supporti
# CD/DVD/BD e sulle etichette in commercio:
#  - esterno: da 80 mm (mini-disc) a 120 mm (disco fisico standard)
#  - foro/area centrale non stampata: dal foro fisico (~15 mm) fino a ~50 mm
DISC_OUTER_MIN = 80.0
DISC_OUTER_MAX = 120.0
DISC_HOLE_MIN = 15.0
DISC_HOLE_MAX = 50.0

CONFIG_DIR = os.path.expanduser("~/.config/cover-studio")
FORMATS_FILE = os.path.join(CONFIG_DIR, "formats.json")
# formati di fabbrica che l'utente ha "nascosto" rinominandoli: vengono tolti
# dall'elenco e si recuperano col Ripristino di fabbrica.
HIDDEN_BASES_FILE = os.path.join(CONFIG_DIR, "hidden_bases.json")


def px_to_mm(px, dpi):
    return px / dpi * MM_PER_INCH


def mm_to_px(mm, dpi):
    return mm / MM_PER_INCH * dpi


def mm_to_pt(mm):
    return mm / MM_PER_INCH * PT_PER_INCH


# ---------------------------------------------------------------------------
# Formati BASE (fissi, non modificabili).
# DVD : 1535 + 170 + 1535 = 3240 px ; spina centrale ~14 mm
# BD  : 1489 + 142 + 1489 = 3120 px ; spina centrale ~12 mm
# (Label tonda verra' aggiunta nella fase dedicata.)
# ---------------------------------------------------------------------------
BASE_FORMATS = {
    "Cover DVD": {
        "unit": "px", "dpi": 300, "height": 2175,
        "sections": [
            {"name": "Retro", "width": 1535},
            {"name": "Spina", "width": 170},
            {"name": "Fronte", "width": 1535},
        ],
        "kind": "cover", "print_w_mm": None, "spine_section": 1,
    },
    "Cover BD": {
        "unit": "px", "dpi": 300, "height": 1748,
        "sections": [
            {"name": "Retro", "width": 1489},
            {"name": "Spina", "width": 142},
            {"name": "Fronte", "width": 1489},
        ],
        "kind": "cover", "print_w_mm": None, "spine_section": 1,
    },
    "Disco": {
        "kind": "label",
        "outer_mm": 118.0,   # diametro esterno stampabile (standard dichiarato)
        "hole_mm": 22.0,     # diametro interno stampabile (standard hub-printable)
        "offset_x_mm": 0.0,  # taratura posizione sul disco
        "offset_y_mm": 0.0,
        "img_px": 1500,      # le label sono di norma 1500x1500 px
        "spine_section": None,
    },
    "Label adesiva": {
        "kind": "sheet",
        "page_name": "A4",
        "page_w_mm": 210.0,
        "page_h_mm": 297.0,
        "outer_mm": 118.0,
        "hole_mm": 22.0,
        "count": 2,
        "labels": [
            {"x_mm": 105.0, "y_mm": 74.25},
            {"x_mm": 105.0, "y_mm": 222.75},
        ],
        "mirror": True,
        "img_px": 1500,
        "spine_section": None,
    },
}


def label_defaults():
    f = BASE_FORMATS.get("Disco", {})
    return {
        "outer": f.get("outer_mm", 118.0),
        "hole": f.get("hole_mm", 21.0),
        "offx": f.get("offset_x_mm", 0.0),
        "offy": f.get("offset_y_mm", 0.0),
    }


# Fogli supportati per le etichette adesive (mm, verticale). "Personalizzato"
# usa le dimensioni libere scelte dall'utente (memorizzate nel formato).
PAGE_PRESETS = [
    ("A4", 210.0, 297.0),
    ("Personalizzato", 210.0, 297.0),
]
CUSTOM_PAGE_NAME = "Personalizzato"


def page_size_mm(name):
    for nm, w, h in PAGE_PRESETS:
        if nm == name:
            return (w, h)
    return (210.0, 297.0)


def sheet_label_positions(page_w, page_h, count):
    """Posizioni AUTOMATICHE (centri delle etichette) sul foglio:
    1 etichetta = al centro del foglio; 2 = foglio diviso in due, una al
    centro di ciascuna meta'."""
    cxm = page_w / 2.0
    if count <= 1:
        return [{"x_mm": cxm, "y_mm": page_h / 2.0}]
    return [{"x_mm": cxm, "y_mm": page_h / 4.0},
            {"x_mm": cxm, "y_mm": page_h * 3.0 / 4.0}]


def sheet_defaults():
    pw, ph = page_size_mm("A4")
    return {
        "kind": "sheet",
        "page_name": "A4",
        "page_w_mm": pw,
        "page_h_mm": ph,
        "outer_mm": 118.0,
        "hole_mm": 22.0,
        "count": 1,
        "labels": sheet_label_positions(pw, ph, 1),
        "img_px": 1500,
        "spine_section": None,
    }


def _dpi(f):
    return f.get("dpi", DEFAULT_DPI)


def _to_mm(f, value):
    return value if f["unit"] == "mm" else px_to_mm(value, _dpi(f))


def _to_px(f, value):
    return value if f["unit"] == "px" else mm_to_px(value, _dpi(f))


def total_width_units(f):
    return sum(s["width"] for s in f["sections"])


def template_size_mm(f):
    return _to_mm(f, total_width_units(f)), _to_mm(f, f["height"])


def template_size_px(f):
    w = _to_px(f, total_width_units(f))
    h = _to_px(f, f["height"])
    return int(round(w)), int(round(h))


def template_aspect(f):
    w, h = template_size_mm(f)
    return h / w if w else 1.0


def print_size_mm(f):
    pw = f.get("print_w_mm")
    if pw is None:
        return template_size_mm(f)
    return pw, pw * template_aspect(f)


def section_widths_mm(f, total_w_mm=None):
    nat_w, _ = template_size_mm(f)
    if total_w_mm is None:
        total_w_mm, _ = print_size_mm(f)
    scale = (total_w_mm / nat_w) if nat_w else 1.0
    return [_to_mm(f, s["width"]) * scale for s in f["sections"]]


def section_boundaries_mm(f, total_w_mm=None):
    widths = section_widths_mm(f, total_w_mm)
    xs = []
    acc = 0.0
    for w in widths[:-1]:
        acc += w
        xs.append(acc)
    return xs


def section_names(f):
    return [s.get("name", "") for s in f["sections"]]


# ---------------------------------------------------------------------------
# Nome mostrato: aggiunge la larghezza della spina tra parentesi, in automatico.
# ---------------------------------------------------------------------------
def _fmt_mm(w):
    r = round(w)
    if abs(w - r) < 0.5:          # vicino a un intero -> es. "14mm"
        return "%dmm" % int(r)
    return "%.1fmm" % w           # spina non intera -> es. "13.5mm"


def spine_width_mm(f):
    """Larghezza (mm) della sezione-spina, o None se il formato non ne ha."""
    if f.get("kind") == "label":
        return None
    idx = f.get("spine_section")
    if idx is None:
        return None
    widths = section_widths_mm(f)
    if isinstance(idx, int) and 0 <= idx < len(widths):
        return widths[idx]
    return None


def display_name(name, f):
    """Nome + larghezza spina tra parentesi se presente (es. 'Cover DVD (14mm)')."""
    w = spine_width_mm(f)
    if w is None:
        return name
    return "%s (%s)" % (name, _fmt_mm(w))


# ---------------------------------------------------------------------------
# Formati personalizzati: caricamento / salvataggio (~/.config/.../formats.json)
# ---------------------------------------------------------------------------
def load_custom_formats():
    """Carica i formati salvati dall'utente dal file formats.json.
    Puo' contenere sia formati NUOVI creati dall'utente sia VERSIONI MODIFICATE
    dei formati base (override): questi ultimi prendono il posto del base nel
    menu, ma l'originale di fabbrica in BASE_FORMATS resta intatto e si recupera
    con il ripristino o con 'torna all'originale'."""
    try:
        with open(FORMATS_FILE, encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        return {}


def save_custom_formats(d):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(FORMATS_FILE, "w", encoding="utf-8") as fp:
            json.dump(d, fp, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_hidden_bases():
    """Insieme dei nomi di formati di fabbrica che l'utente ha nascosto
    (rinominandoli). Si recuperano con il Ripristino di fabbrica."""
    try:
        with open(HIDDEN_BASES_FILE, encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        pass
    return set()


def save_hidden_bases(names):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(HIDDEN_BASES_FILE, "w", encoding="utf-8") as fp:
            json.dump(sorted(names), fp, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def all_formats():
    """Dizionario unito: prima i base (fissi, esclusi quelli nascosti dall'utente),
    poi i personalizzati."""
    hidden = load_hidden_bases()
    merged = {k: v for k, v in BASE_FORMATS.items() if k not in hidden}
    merged.update(load_custom_formats())
    return merged


def is_base(name):
    return name in BASE_FORMATS


def factory_format(name):
    """Copia indipendente del formato base di fabbrica (per 'torna all'originale'),
    o None se 'name' non e' un formato base."""
    f = BASE_FORMATS.get(name)
    return copy.deepcopy(f) if f is not None else None


def is_overridden(name):
    """True se 'name' e' un base di cui l'utente ha salvato una versione modificata."""
    return name in BASE_FORMATS and name in load_custom_formats()


def disc_geometry_error(outer, hole):
    """Verifica che esterno/foro siano misure realistiche per dischi/etichette.
    Ritorna un messaggio d'errore oppure None se va bene."""
    outer = outer or 0
    hole = hole or 0
    if outer < DISC_OUTER_MIN or outer > DISC_OUTER_MAX:
        return ("Il diametro esterno deve essere tra %g e %g mm."
                % (DISC_OUTER_MIN, DISC_OUTER_MAX))
    if hole < DISC_HOLE_MIN or hole > DISC_HOLE_MAX:
        return ("Il foro deve essere tra %g e %g mm."
                % (DISC_HOLE_MIN, DISC_HOLE_MAX))
    if hole >= outer:
        return "Il foro deve essere piu' piccolo del diametro esterno."
    return None


def validate_format(name, f, existing_names, original_name=None):
    """Controlli minimi prima di salvare un formato (per l'Editor).
    original_name: se si sta MODIFICANDO un formato gia' esistente, e' il suo
    nome; serve a permettere di risalvare con lo stesso nome (anche per i base)."""
    if not name or not name.strip():
        return False, "Il nome non puo' essere vuoto."
    # Il nome di un base si puo' usare solo modificando QUEL base (selezionandolo
    # dall'elenco), non creandone uno nuovo con lo stesso nome.
    if name in BASE_FORMATS and name != original_name:
        return False, ("«%s» e' un formato base: per modificarlo selezionalo "
                       "dall'elenco e salva." % name)
    # Nessun doppione con un ALTRO formato gia' esistente.
    if name != original_name and name in existing_names:
        return False, "Esiste gia' un formato con questo nome."
    # Controlli specifici delle cover (gli altri tipi avranno i propri).
    if f.get("kind", "cover") == "cover":
        secs = f.get("sections", [])
        if not (1 <= len(secs) <= MAX_SECTIONS):
            return False, "Le sezioni devono essere da 1 a %d." % MAX_SECTIONS
        if f.get("height", 0) <= 0:
            return False, "L'altezza deve essere maggiore di zero."
        for s in secs:
            if s.get("width", 0) <= 0:
                return False, "Ogni sezione deve avere larghezza maggiore di zero."
    elif f.get("kind") == "label":
        err = disc_geometry_error(f.get("outer_mm", 0), f.get("hole_mm", 0))
        if err:
            return False, err
    elif f.get("kind") == "sheet":
        pw = f.get("page_w_mm", 0) or 0
        ph = f.get("page_h_mm", 0) or 0
        outer = f.get("outer_mm", 0) or 0
        hole = f.get("hole_mm", 0) or 0
        count = f.get("count", 1)
        if pw <= 0 or ph <= 0:
            return False, "Le dimensioni del foglio devono essere positive."
        err = disc_geometry_error(outer, hole)
        if err:
            return False, err
        if count not in (1, 2):
            return False, "Le etichette per foglio devono essere 1 o 2."
        if outer > pw:
            return False, "L'etichetta e' piu' larga del foglio."
        if count == 1 and outer > ph:
            return False, "L'etichetta non entra nel foglio."
        if count == 2 and outer > ph / 2.0:
            return False, "Due etichette non entrano in altezza nel foglio."
    return True, ""
