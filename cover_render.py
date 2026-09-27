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
# Cover Studio - disegno condiviso della cover (usato dalla stampa).
# Il contesto cairo deve essere gia' scalato a 1 unita' = 1 mm.
#
# In stampa, nei MARGINI (mai sopra l'immagine):
#  - crocini di TAGLIO a lunghezza fissa agli angoli del blocco, con simbolo
#    FORBICI;
#  - segni di PIEGA ai confini tra le sezioni (stesso stile dei tagli), con
#    simbolo PIEGA (icona "angolo piegato").
# I simboli sono disegnati a mano (vettoriali): identici su qualsiasi sistema,
# non dipendono dai font.

import math
import cairo
from formats import print_size_mm, section_boundaries_mm

CUT_GAP = 2.0           # distacco del segno dal bordo cover (mm)
CUT_LEN = 5.0           # lunghezza fissa del segno (mm)
CUT_LW = 0.1            # spessore finissimo dei segni (mm)
CUT_DASH = [1.0, 0.8]   # tratteggio fine (mm)
CUT_GREY = 0.5          # grigio

SYM_SIZE = 3.0          # dimensione dei simboli (mm)
SYM_OFFSET = 3.0        # distanza del simbolo dal segno (mm)
SYM_LW = 0.15           # spessore linea dei simboli (mm)


def cover_origin(fmt, page_mm):
    """(ox, oy, cover_w, cover_h) in mm: cover di stampa centrata nel foglio."""
    cover_w, cover_h = print_size_mm(fmt)
    page_w, page_h = page_mm
    ox = (page_w - cover_w) / 2.0
    oy = (page_h - cover_h) / 2.0
    return ox, oy, cover_w, cover_h


def fit_placement(img_w_px, img_h_px, ox, oy, cw, ch):
    """Modalita' ADATTA (fit): l'immagine entra TUTTA nell'area, centrata,
    mantenendo le proporzioni. Se il rapporto non combacia restano bande
    bianche, ma l'immagine non viene mai tagliata.
    Restituisce (scale_mm_per_px, img_ox, img_oy)."""
    s = min(cw / img_w_px, ch / img_h_px)
    drawn_w = img_w_px * s
    drawn_h = img_h_px * s
    img_ox = ox + (cw - drawn_w) / 2.0
    img_oy = oy + (ch - drawn_h) / 2.0
    return s, img_ox, img_oy


def draw_image_fit(cr, image_surface, ox, oy, cw, ch):
    """Disegna l'immagine adattata (centrata, senza ritaglio)."""
    iw = image_surface.get_width()
    ih = image_surface.get_height()
    s, img_ox, img_oy = fit_placement(iw, ih, ox, oy, cw, ch)
    cr.save()
    cr.translate(img_ox, img_oy)
    cr.scale(s, s)
    cr.rectangle(0, 0, iw, ih)
    cr.clip()
    cr.set_source_surface(image_surface, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()


# --------------------------------------------------------------------------
# SEGNI (tratteggiati, fini, grigi) - identici per taglio e piega
# --------------------------------------------------------------------------
def _set_mark_style(cr):
    cr.set_source_rgb(CUT_GREY, CUT_GREY, CUT_GREY)
    cr.set_line_width(CUT_LW)
    cr.set_dash(CUT_DASH)


def draw_crop_marks(cr, ox, oy, w, h):
    """8 crocini di TAGLIO agli angoli, a lunghezza fissa, staccati dalla cover."""
    g, L = CUT_GAP, CUT_LEN
    left, right, top, bot = ox, ox + w, oy, oy + h
    _set_mark_style(cr)
    cr.move_to(left, top - g - L); cr.line_to(left, top - g)
    cr.move_to(left - g - L, top); cr.line_to(left - g, top)
    cr.move_to(right, top - g - L); cr.line_to(right, top - g)
    cr.move_to(right + g, top); cr.line_to(right + g + L, top)
    cr.move_to(left, bot + g); cr.line_to(left, bot + g + L)
    cr.move_to(left - g - L, bot); cr.line_to(left - g, bot)
    cr.move_to(right, bot + g); cr.line_to(right, bot + g + L)
    cr.move_to(right + g, bot); cr.line_to(right + g + L, bot)
    cr.stroke()
    cr.set_dash([])


def draw_fold_marks(cr, fmt, ox, oy, w, h):
    """Segni di PIEGA ai confini interni tra le sezioni: due trattini corti
    (sopra e sotto), stesso stile dei tagli. Mai sopra l'immagine."""
    bounds = section_boundaries_mm(fmt, w)   # posizioni X (mm) delle pieghe
    if not bounds:
        return
    g, L = CUT_GAP, CUT_LEN
    top, bot = oy, oy + h
    _set_mark_style(cr)
    for b in bounds:
        x = ox + b
        cr.move_to(x, top - g - L); cr.line_to(x, top - g)
        cr.move_to(x, bot + g); cr.line_to(x, bot + g + L)
    cr.stroke()
    cr.set_dash([])


# --------------------------------------------------------------------------
# SIMBOLI vettoriali (disegnati a mano, indipendenti dai font)
# --------------------------------------------------------------------------
def draw_scissors(cr, cx, cy, s=SYM_SIZE):
    """Piccola forbice centrata in (cx, cy)."""
    cr.save()
    cr.set_source_rgb(CUT_GREY, CUT_GREY, CUT_GREY)
    cr.set_line_width(SYM_LW)
    cr.set_dash([])
    r = s * 0.16
    hl = (cx - s * 0.22, cy + s * 0.40)   # manico sinistro
    hr = (cx + s * 0.22, cy + s * 0.40)   # manico destro
    tl = (cx - s * 0.30, cy - s * 0.48)   # punta sinistra
    tr = (cx + s * 0.30, cy - s * 0.48)   # punta destra
    # lame incrociate
    cr.move_to(*hl); cr.line_to(*tr)
    cr.move_to(*hr); cr.line_to(*tl)
    cr.stroke()
    # anelli dei manici
    cr.arc(hl[0], hl[1], r, 0, 2 * math.pi); cr.stroke()
    cr.arc(hr[0], hr[1], r, 0, 2 * math.pi); cr.stroke()
    cr.restore()


def draw_fold_icon(cr, cx, cy, s=SYM_SIZE):
    """Piccola icona di PIEGA (quadrato con angolo piegato) centrata in (cx, cy)."""
    cr.save()
    cr.set_source_rgb(CUT_GREY, CUT_GREY, CUT_GREY)
    cr.set_line_width(SYM_LW)
    cr.set_dash([])
    half = s * 0.5
    x0, y0 = cx - half, cy - half
    fold = s * 0.38
    # contorno del foglietto con angolo alto-dx piegato
    cr.move_to(x0, y0)
    cr.line_to(x0 + s - fold, y0)
    cr.line_to(x0 + s, y0 + fold)
    cr.line_to(x0 + s, y0 + s)
    cr.line_to(x0, y0 + s)
    cr.close_path()
    cr.stroke()
    # triangolo dell'angolo piegato
    cr.move_to(x0 + s - fold, y0)
    cr.line_to(x0 + s - fold, y0 + fold)
    cr.line_to(x0 + s, y0 + fold)
    cr.stroke()
    cr.restore()


def draw_cut_symbols(cr, ox, oy, w, h):
    """Forbici accanto ai tagli esterni (in alto, ai lati del blocco)."""
    top = oy
    y = top - CUT_GAP - CUT_LEN / 2.0
    draw_scissors(cr, ox - SYM_OFFSET, y)          # lato sinistro
    draw_scissors(cr, ox + w + SYM_OFFSET, y)      # lato destro


def draw_fold_symbols(cr, fmt, ox, oy, w, h):
    """Icona piega accanto a ogni segno di piega (in alto)."""
    bounds = section_boundaries_mm(fmt, w)
    top = oy
    y = top - CUT_GAP - CUT_LEN / 2.0
    for b in bounds:
        draw_fold_icon(cr, ox + b + SYM_OFFSET, y)


def draw_cover(cr, fmt, page_mm, image_surface=None,
               show_cut=True, show_fold=True):
    """Immagine adattata (se presente) + segni di taglio e di piega.
    show_cut / show_fold: attivabili dal pannello opzioni (passo successivo)."""
    ox, oy, w, h = cover_origin(fmt, page_mm)
    if image_surface is not None:
        draw_image_fit(cr, image_surface, ox, oy, w, h)
    if show_cut:
        draw_crop_marks(cr, ox, oy, w, h)
        draw_cut_symbols(cr, ox, oy, w, h)
    if show_fold:
        draw_fold_marks(cr, fmt, ox, oy, w, h)
        draw_fold_symbols(cr, fmt, ox, oy, w, h)


def draw_label(cr, cx, cy, outer_r, hole_r, image_surface):
    """Disegna l'immagine ritagliata ad ANELLO: riempie la corona tra foro e
    bordo esterno, centrata sul disco. Niente inchiostro nel foro o oltre il
    bordo (in cairo: clip ad anello con regola pari/dispari).
    Tutte le misure nelle unita' correnti del contesto (mm in stampa)."""
    if image_surface is None or outer_r <= 0:
        return
    iw = image_surface.get_width()
    ih = image_surface.get_height()
    if iw <= 0 or ih <= 0:
        return
    side = 2.0 * outer_r
    s = min(side / iw, side / ih)   # adatta (contain) nel quadrato del disco
    dw, dh = iw * s, ih * s
    cr.save()
    cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    cr.arc(cx, cy, outer_r, 0, 2 * math.pi)
    cr.new_sub_path()
    cr.arc(cx, cy, max(hole_r, 0.0), 0, 2 * math.pi)
    cr.clip()
    cr.translate(cx - dw / 2.0, cy - dh / 2.0)
    cr.scale(s, s)
    cr.set_source_surface(image_surface, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()


def draw_sheet(cr, page_w, page_h, labels, outer_mm, hole_mm, image_surface=None,
               ink=(0.0, 0.0, 0.0), line_w=0.3):
    """Foglio di etichette adesive (tutto in mm, origine in alto a sinistra del
    foglio). 'labels' = lista di centri {'x_mm','y_mm'}. Per ogni etichetta:
    immagine ritagliata ad anello (se presente) + contorni esterno e foro."""
    outer_r = max(outer_mm, 0.0) / 2.0
    hole_r = max(hole_mm, 0.0) / 2.0
    cr.save()
    cr.set_source_rgb(*ink)
    cr.set_line_width(line_w)
    cr.rectangle(0, 0, page_w, page_h)        # bordo del foglio
    cr.stroke()
    for lab in (labels or []):
        x = lab.get("x_mm", page_w / 2.0)
        y = lab.get("y_mm", page_h / 2.0)
        if image_surface is not None:
            draw_label(cr, x, y, outer_r, hole_r, image_surface)
        cr.set_source_rgb(*ink)
        cr.set_line_width(line_w)
        cr.new_sub_path()
        cr.arc(x, y, outer_r, 0, 2 * math.pi)
        cr.stroke()
        if hole_r > 0:
            cr.new_sub_path()
            cr.arc(x, y, hole_r, 0, 2 * math.pi)
            cr.stroke()
    cr.restore()


def draw_test_marks(cr, cx, cy, outer_r, hole_r, ink=(0.0, 0.0, 0.0), line_w=0.3):
    """Stampa di prova (quando non c'e' immagine), alle misure REALI del
    formato: cerchio esterno, foro e crocetta al centro. Serve ad allineare a
    vuoto il disco o il foglio adesivo pre-fustellato. Misure in mm.
    Usata sia dalla stampa del Disco sia da quella del Foglio adesivo."""
    cr.save()
    cr.set_source_rgb(*ink)
    cr.set_line_width(line_w)
    if outer_r > 0:
        cr.new_sub_path()
        cr.arc(cx, cy, outer_r, 0, 2 * math.pi)
        cr.stroke()
    if hole_r > 0:
        cr.new_sub_path()
        cr.arc(cx, cy, hole_r, 0, 2 * math.pi)
        cr.stroke()
    # crocetta al centro (lunga come il foro, o 3 mm se non c'e' foro)
    cl = hole_r if hole_r > 0 else 3.0
    cr.move_to(cx - cl, cy)
    cr.line_to(cx + cl, cy)
    cr.move_to(cx, cy - cl)
    cr.line_to(cx, cy + cl)
    cr.stroke()
    cr.restore()


def draw_calibration(cr, cx, cy, hole_mm, outer_mm):
    """Maschera di taratura (stampata quando non c'e' immagine): righello di
    cerchi a diametri noti ogni 20 mm (20..120) + due assi, per misurare sul
    disco reale la scala e la centratura. Il cerchio 120 = bordo fisico del
    disco; il 20 = limite interno tipico. Misure in mm.
    hole_mm/outer_mm restano nella firma per compatibilita' (li usera' la
    futura vista di calibrazione); qui la maschera e' un righello fisso."""
    DIAMS = (20, 40, 60, 80, 100, 120)
    inner_r = DIAMS[0] / 2.0
    outer_r = DIAMS[-1] / 2.0
    NE = -math.pi / 4.0   # numeri su una diagonale, lontani dalla croce
    cos_ne, sin_ne = math.cos(NE), math.sin(NE)
    cr.save()
    cr.set_line_width(0.2)
    cr.select_font_face("Sans")
    cr.set_font_size(3.0)
    # 1) i cerchi: ogni arco apre una nuova sotto-traccia, cosi' non resta
    #    alcuna linea di collegamento tra un elemento e il successivo (erano
    #    le "codine" che facevano sembrare il numero riferito al cerchio dopo).
    cr.set_source_rgb(0.0, 0.0, 0.0)
    for d in DIAMS:
        cr.new_sub_path()
        cr.arc(cx, cy, d / 2.0, 0, 2 * math.pi)
        cr.stroke()
    # 2) croce centrale (orizzontale + verticale), per controllare la centratura
    for ang in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        cr.move_to(cx + math.cos(ang) * inner_r, cy + math.sin(ang) * inner_r)
        cr.line_to(cx + math.cos(ang) * outer_r, cy + math.sin(ang) * outer_r)
    cr.stroke()
    # 3) i numeri: ciascuno SUL proprio cerchio, con un piccolo stacco bianco
    #    sotto (come le quote sulle cartine). Solo i due estremi (20 e 120)
    #    vengono rientrati di pochi mm per non finire fuori dalla corona
    #    stampabile: il 20 verso il 40, il 120 verso il 100. Il rientro tiene
    #    conto dell'ingombro del numero lungo la diagonale (non solo l'altezza).
    pad = 0.7
    for d in DIAMS:
        s = "%d" % d
        ext = cr.text_extents(s)
        radial_half = (abs(cos_ne) * (ext.width / 2.0 + pad)
                       + abs(sin_ne) * (ext.height / 2.0 + pad)) + 0.3
        rl = d / 2.0
        rl = max(rl, inner_r + radial_half)   # rientra solo il 20 (verso il 40)
        rl = min(rl, outer_r - radial_half)   # rientra solo il 120 (verso il 100)
        px = cx + cos_ne * rl
        py = cy + sin_ne * rl
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(px - ext.width / 2.0 - pad, py - ext.height / 2.0 - pad,
                     ext.width + 2.0 * pad, ext.height + 2.0 * pad)
        cr.fill()
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.move_to(px - ext.width / 2.0 - ext.x_bearing,
                   py - ext.height / 2.0 - ext.y_bearing)
        cr.show_text(s)
    cr.restore()
