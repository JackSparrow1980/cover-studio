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
# Cover Studio - interfaccia grafica: finestra principale, editor dei formati
# e stampa di cover, etichette per dischi e fogli di etichette adesive.

import os
import sys
sys.dont_write_bytecode = True   # non creare la cartella __pycache__/ accanto ai file
import json
import math
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango
import cairo

from formats import (BASE_FORMATS, all_formats, display_name,
                     load_custom_formats, save_custom_formats, validate_format,
                     label_defaults, print_size_mm, template_size_px,
                     section_widths_mm, section_names, A4_LANDSCAPE_MM,
                     FORMATS_FILE, is_base, factory_format,
                     HIDDEN_BASES_FILE, load_hidden_bases, save_hidden_bases,
                     PAGE_PRESETS, page_size_mm, sheet_label_positions,
                     sheet_defaults, DISC_OUTER_MIN, DISC_OUTER_MAX,
                     DISC_HOLE_MIN, DISC_HOLE_MAX, CUSTOM_PAGE_NAME)
from cover_render import (draw_cover, draw_label, draw_calibration, draw_test_marks, draw_sheet,
                          fit_placement,
                          CUT_GAP, CUT_LEN, CUT_DASH, CUT_GREY)

# Colori dei due riferimenti di posizione (uguali per ogni etichetta):
#  - orizzontale "Da sinistra"  -> arancione
#  - verticale  "Dall'alto/Dal basso" -> blu
SHEET_COL_LEFT = (0.91, 0.45, 0.05)
SHEET_COL_VERT = (0.11, 0.49, 0.84)
SHEET_COL_LEFT_HEX = "#e8730c"
SHEET_COL_VERT_HEX = "#1c7ed6"

# Link per la donazione facoltativa (aperto nel browser dalla finestra Guida).
PAYPAL_URL = "https://paypal.me/GiuseppeStramandino"

# --- Impostazioni persistenti (ultima cartella, ecc.) ---
CONFIG_DIR = os.path.expanduser("~/.config/cover-studio")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
# Impostazioni di stampa separate per tipo di formato (Cover vs Label), cosi'
# le scelte di uno non sovrascrivono quelle dell'altro. La Label salva anche
# la propria dimensione carta (es. 120x120.Borderless) dentro queste settings.
PRINT_SETTINGS_COVER = os.path.join(CONFIG_DIR, "print_settings_cover.ini")
PRINT_SETTINGS_LABEL = os.path.join(CONFIG_DIR, "print_settings_label.ini")
PRINT_SETTINGS_SHEET = os.path.join(CONFIG_DIR, "print_settings_sheet.ini")
# La dimensione carta (es. 120x120.Borderless) vive nella PageSetup, non nelle
# impostazioni: la salviamo a parte, catturandola dalla stampa reale.
PAGE_SETUP_LABEL = os.path.join(CONFIG_DIR, "page_setup_label.ini")

# Griglia della Stampa in serie: caselle fisse, 3 per fila, almeno 9 visibili.
BATCH_SLOT_W = 210
BATCH_SLOT_H = 160
BATCH_COLS = 3
BATCH_MIN_SLOTS = 9


# ---------------------------------------------------------------------------
# TESTI DELL'INTERFACCIA (raccolti qui per la futura traduzione multilingua).
# Tabella di testi per lingua. L'italiano e' la base "di sicurezza" sempre
# completa; l'inglese e' incorporato; altre lingue arrivano da file JSON nella
# cartella lingue (vedi sotto). All'avvio T viene riempito con la lingua scelta.
# ---------------------------------------------------------------------------
STRINGS_IT = {
    "app_title": "Cover Studio",
    "format": "Formato:",
    "load_image": "Carica immagine...",
    "remove_image": "Rimuovi immagine",
    "print": "Stampa...",
    "options": "Opzioni",
    # finestra "apri immagine"
    "choose_image": "Scegli l'immagine della cover",
    "cancel": "Annulla",
    "open": "Apri",
    "images": "Immagini",
    # barra di stato
    "st_print": "Stampa",
    "st_image": "Immagine",
    "st_none": "nessuna",
    "st_state": "Stato",
    "state_ready": "pronto",
    "state_loaded": "immagine caricata",
    "state_printed": "inviato in stampa",
    # errori
    "error": "Errore",
    "image_open_error": "Non riesco ad aprire l'immagine:\n%s",
    "print_error_title": "Errore di stampa",
    "print_error": "Si e' verificato un errore durante la stampa.",
    # finestra Opzioni
    "options_title": "Opzioni",
    "opt_cut": "Stampa linee di taglio",
    "opt_fold": "Stampa linee di piega",
    "opt_reset": "Ripristina impostazioni di fabbrica",
    "opt_offset_title": "Offset stampante (taratura)",
    "opt_offset_hint": "Correzione di centratura del vassoio, valida per tutti i dischi.\nSi imposta una volta sola, con una stampa di prova.",
    "opt_calib_testprint": "Stampa di prova",
    "opt_calib_reset": "Azzera taratura",
    "opt_calib_readout": "Offset X %+.1f mm    Y %+.1f mm",
    "opt_sec_print": "Stampa (cover)",
    "opt_sec_calib": "Taratura stampante (dischi)",
    "opt_sec_ui": "Interfaccia",
    "opt_tooltips": "Mostra i suggerimenti (tooltip)",
    "tt_tooltips": "Attiva o disattiva i fumetti di aiuto (al riavvio)",
    "tooltips_restart_note": "L'opzione sarà applicata al prossimo avvio dell'app.",
    "opt_sec_lang": "Lingua",
    "opt_lang_label": "Lingua dell'app:",
    "opt_lang_custom": "Per aggiungere o personalizzare una lingua, vedi la "
                       "Guida (pulsante «?»).",
    "lang_restart_note": "La nuova lingua sarà applicata al prossimo avvio dell'app.",
    "opt_sec_reset": "Ripristino",
    "reset_title": "Ripristinare le impostazioni di fabbrica?",
    "reset_msg": ("Questa operazione cancella tutti i formati che hai creato "
                  "e tutte le impostazioni di stampa salvate, e azzera misure "
                  "e offset delle etichette.\n\nNon e' annullabile. La finestra "
                  "e l'ultima cartella usata restano invariate.\n\nVuoi "
                  "procedere?"),
    "reset_done_title": "Ripristino completato",
    "reset_done": ("Formati e impostazioni di stampa sono stati riportati ai "
                   "valori di fabbrica."),
    "close": "Chiudi",
    # finestra Editor formato
    "editor": "Editor",
    "editor_title": "Editor formato",
    "ed_your_formats": "I tuoi formati:",
    "ed_new": "Nuovo",
    "ed_delete": "Elimina",
    "ed_name": "Nome:",
    "ed_unit": "Unità:",
    "ed_height": "Altezza:",
    "ed_totalw": "Larghezza tot.:",
    "ed_count": "N° sezioni:",
    "ed_sections": "Sezioni (max 3):",
    "ed_section": "Sezione",
    "ed_add_section": "+ sezione",
    "ed_del_section": "− sezione",
    "ed_spine": "Misura nel titolo:",
    "ed_spine_none": "nessuna",
    "ed_sum": "Somma:",
    "ed_mismatch": "non corrisponde alla larghezza totale",
    "ed_need_total": "Inserisci la larghezza totale",
    "ed_need_widths": "Inserisci le larghezze delle sezioni",
    "ed_save": "Salva",
    "ed_testprint": "Stampa di prova",
    "ed_testprint_tip": "Stampa il formato che stai creando, a vuoto (senza immagine), per provarlo prima di salvarlo.",
    "ed_invalid": "Dati non validi",
    "ed_confirm_delete": "Eliminare il formato «%s»?",
    "ed_revert": "Torna all'originale",
    "ed_restore_presets": "Ripristina preimpostati",
    "ed_restore_presets_tip": "Rimette i formati preimpostati di fabbrica che sono stati nascosti, rinominati o eliminati, senza toccare i tuoi formati personalizzati.",
    "ed_restore_presets_done_title": "Preimpostati ripristinati",
    "ed_restore_presets_done": "I formati preimpostati di fabbrica sono stati ripristinati. I tuoi formati personalizzati sono rimasti invariati.",
    "ed_modified": "  (modificato)",
    "ed_confirm_revert": "Riportare «%s» alla versione di fabbrica?",
    "ed_type": "Tipo:",
    "ed_type_cover": "Cover",
    "ed_type_disc": "Disco",
    "ed_type_sheet": "Label adesiva",
    "ed_page": "Formato foglio:",
    "ed_page_w": "Larghezza (mm):",
    "ed_page_h": "Altezza (mm):",
    "ed_sheet_count": "N° etichette:",
    "ed_sheet_ok": "Foglio valido",
    "ed_pos_label": "Etichetta %d:",
    "ed_pos_left": "Da sinistra:",
    "ed_pos_right": "Da destra:",
    "ed_pos_top": "Dall'alto:",
    "ed_pos_bottom": "Dal basso:",
    "ed_label_word": "Etichetta",
    "ed_mirror_lock": "Blocco speculare",
    "ed_mirror_tip": "Tiene le due etichette speculari: muovendone una, l'altra la rispecchia. Premi per sbloccare.",
    "m_left": "Sinistra",
    "m_right": "Destra",
    "m_top": "Alto",
    "m_bottom": "Basso",
    "sheet_margins": "Etichetta %d  —  Sinistra %.1f mm · Destra %.1f mm · Alto %.1f mm · Basso %.1f mm",
    "ed_outer": "Ø esterno (mm):",
    "ed_hole": "Ø foro (mm):",
    "ed_disc_ok": "Misure disco valide",
    "ed_disc_bad": "Il foro deve essere più piccolo dell'esterno (e maggiore di zero)",
    "ed_need_disc": "Inserisci diametro esterno e foro",
    "ed_hdr_name": "Nome",
    "ed_hdr_width": "Larghezza",
    "scrub_tip": "Tieni premuto e trascina in orizzontale per regolare",
    "yes": "Sì",
    "no": "No",
    # --- Guida / Informazioni (pulsante "?") ---
    "help": "?",
    "help_tooltip": "Guida e informazioni",
    "help_title": "Guida",
    "help_sec_cover": "Cover",
    "help_sec_disc": "Label disco",
    "help_sec_sheet": "Etichette adesive",
    "help_sec_print": "Stampa",
    "help_sec_lang": "Lingua e traduzione",
    "help_body_cover": (
        "Scegli il formato dalla tendina «Formato» in alto (per esempio CD, "
        "DVD…).\n\n"
        "Premi «Carica immagine…» e seleziona il file. L'immagine viene "
        "adattata automaticamente: entra tutta, centrata, con eventuali bande "
        "bianche ai lati se le proporzioni non combaciano. Così non viene mai "
        "tagliata.\n\n"
        "Nell'anteprima vedi le linee di taglio agli angoli e, se il formato "
        "ha più sezioni, le linee di piega tratteggiate in blu (queste ultime "
        "compaiono solo a schermo, non vengono stampate).\n\n"
        "Quando sei pronto premi «Stampa…»: la cover esce su foglio A4 "
        "orizzontale, alle dimensioni reali calibrate, con le linee di taglio "
        "fino al bordo del foglio.\n\n"
        "«Rimuovi immagine» toglie l'immagine e riporta l'anteprima vuota, con "
        "i nomi delle sezioni."
    ),
    "help_body_disc": (
        "I formati di tipo «Disco» hanno un diametro esterno e un foro "
        "centrale. Puoi crearne di nuovi o modificarli dall'Editor.\n\n"
        "Quando non c'è nessuna immagine caricata, l'anteprima mostra una "
        "maschera di calibrazione (cerchi concentrici con assi): serve a "
        "verificare la centratura della stampa sul supporto.\n\n"
        "La centratura sul vassoio si regola una sola volta, in Opzioni → "
        "«Taratura stampante (dischi)», con una stampa di prova: si spostano i "
        "valori X e Y finché il disco risulta centrato. Quella taratura vale "
        "poi per tutti i dischi.\n\n"
        "Al momento della stampa, nella finestra della stampante scegli la "
        "sorgente carta dedicata ai dischi (con la Epson ET-8500 si chiama "
        "«Disc»)."
    ),
    "help_body_sheet": (
        "I formati di tipo «Label adesiva» rappresentano un foglio (di "
        "dimensioni a tua scelta) con una o due etichette.\n\n"
        "Con i regolatori di posizione imposti la distanza di ogni etichetta "
        "dai bordi del foglio: da sinistra, da destra, dall'alto, dal basso. "
        "L'anteprima a destra mostra il foglio con le etichette già "
        "posizionate.\n\n"
        "Con due etichette puoi attivare il «Blocco speculare», l'icona a "
        "catenella: muovendo un'etichetta, l'altra la rispecchia "
        "automaticamente. Premi la catenella per sbloccare e spostarle in modo "
        "indipendente.\n\n"
        "Per stampare, carica l'immagine e premi «Stampa…»: viene riprodotta "
        "su ogni etichetta del foglio. Senza immagine, «Stampa…» produce una "
        "prova con i soli contorni e una crocetta, utile per allineare il "
        "foglio pre-fustellato."
    ),
    "help_body_print": (
        "Il pulsante «Stampa…» apre la finestra di stampa del sistema, dove "
        "scegli la stampante, la sorgente carta e la dimensione del foglio.\n\n"
        "In Opzioni puoi attivare o disattivare la stampa delle linee di "
        "taglio e delle linee di piega.\n\n"
        "«Stampa in serie» (pulsante in alto) serve a stampare più cover una "
        "dopo l'altra: aggiungi le immagini alla coda e le mandi in stampa "
        "tutte insieme.\n\n"
        "Funziona con qualunque stampante riconosciuta dal sistema. È stato "
        "provato con una Epson ET-8500, anche per la stampa diretta su disco. "
        "La stampa su disco richiede una stampante che la supporti."
    ),
    "help_body_lang": (
        "L'app è disponibile in italiano e in inglese (Opzioni → Lingua; il "
        "cambio si applica al riavvio).\n\n"
        "Puoi anche aggiungere una nuova lingua, o correggere le scritte "
        "esistenti, senza saper programmare. Al primo avvio l'app crea la "
        "cartella ~/.config/cover-studio/lang/ con due file modello: it.json e "
        "en.json.\n\n"
        "Per una nuova lingua: copia en.json e rinominalo con il codice della "
        "lingua (per esempio fr.json per il francese, de.json per il tedesco). "
        "Aprilo con un editor di testo, cambia la voce «_lang_name» con il nome "
        "della lingua (per esempio «Français») e traduci solo i testi tra "
        "virgolette a destra, lasciando intatte le parole a sinistra.\n\n"
        "Salva, riavvia l'app e scegli la nuova lingua in Opzioni → Lingua. Le "
        "scritte non tradotte restano automaticamente in italiano, così non "
        "resta mai nulla di vuoto."
    ),
    "help_about_title": "Informazioni",
    "help_app_line": "Cover Studio  ·  versione %s",
    "help_version": "1.0",
    "help_about_desc": ("Stampa di cover, etichette per dischi e fogli di "
                        "etichette adesive su Linux."),
    "help_license": "Licenza: GPL-3.0  —  software libero e open source",
    "help_donate": "Sostieni lo sviluppo",
    "help_donate_hint": ("Cover Studio è gratuito e open source. Se ti è utile "
                         "e ti va, puoi offrire un caffè."),
    # --- Tooltip barra principale ---
    "tt_format": "Scegli il tipo di stampa: cover, disco o etichetta adesiva",
    "tt_load": "Apri l'immagine da stampare",
    "tt_clear": "Togli l'immagine e svuota l'anteprima",
    "tt_batch": "Stampa più cover una dopo l'altra",
    "tt_editor": "Crea o modifica i formati di stampa",
    "tt_options": "Linee di taglio, taratura e altre impostazioni",
    "tt_print": "Apri la finestra di stampa",
    # generico
    "tt_close": "Chiudi questa finestra",
    # Opzioni
    "tt_opt_cut": "Stampa le linee di taglio agli angoli del foglio",
    "tt_opt_fold": "Stampa le linee di piega (formati con più sezioni)",
    "tt_offx": "Sposta la stampa del disco in orizzontale (mm)",
    "tt_offy": "Sposta la stampa del disco in verticale (mm)",
    "tt_calib_reset": "Riporta la taratura a zero",
    "tt_calib_test": "Stampa una pagina di prova per centrare il disco",
    "tt_lang": "Lingua dell'app (applicata al riavvio)",
    "tt_factory_reset": "Ripristina formati e impostazioni ai valori di fabbrica",
    "tt_donate": "Apri la pagina PayPal per la donazione",
    # Editor
    "tt_ed_list": "Seleziona un tuo formato da modificare",
    "tt_ed_new": "Crea un nuovo formato",
    "tt_ed_delete": "Elimina il formato selezionato",
    "tt_ed_name": "Nome del formato",
    "tt_ed_type": "Tipo di formato: cover, disco o etichetta adesiva",
    "tt_ed_unit": "Unità di misura: millimetri o pixel",
    "tt_ed_height": "Altezza della cover",
    "tt_ed_totalw": "Larghezza totale della cover",
    "tt_ed_count": "Numero di sezioni (per esempio fronte, dorso, retro)",
    "tt_ed_spine": "Quale sezione è il dorso",
    "tt_ed_outer": "Diametro esterno del disco (mm)",
    "tt_ed_hole": "Diametro del foro centrale (mm)",
    "tt_ed_page": "Dimensione del foglio",
    "tt_ed_page_w": "Larghezza del foglio personalizzato (mm)",
    "tt_ed_page_h": "Altezza del foglio personalizzato (mm)",
    "tt_ed_sheet_count": "Numero di etichette sul foglio",
    "tt_pos_h": "Distanza orizzontale dell'etichetta dal bordo del foglio (mm)",
    "tt_pos_v": "Distanza verticale dell'etichetta dal bordo del foglio (mm)",
    "tt_ed_save": "Salva il formato",
    "tt_ed_sec_name": "Nome della sezione",
    "tt_ed_sec_width": "Larghezza della sezione",
    # Stampa in serie
    "tt_batch_combo": "Formato delle cover da stampare in serie",
    "tt_batch_add": "Aggiungi un'immagine alla serie",
    "tt_batch_clear": "Svuota la serie",
    "tt_batch_print": "Stampa tutte le cover della serie",
    "tt_batch_trash": "Rimuovi questa cover dalla serie",
    # finestra Stampa in serie
    "batch": "Stampa in serie",
    "batch_title": "Stampa in serie",
    "batch_format": "Formato:",
    "batch_add": "Aggiungi...",
    "batch_clear": "Elimina tutte",
    "batch_print": "Stampa",
    "choose_images": "Scegli le immagini",
    "batch_empty": "Nessuna immagine. Usa «Aggiungi…» per iniziare.",
    "batch_count": "%d immagini in coda",
    # Label
    "lbl_outer": "Ø esterno:",
    "lbl_hole": "Ø foro:",
    "lbl_offx": "Offset X:",
    "lbl_offy": "Offset Y:",
    "lbl_status": "Disco",
    "lbl_print_next": "La stampa su disco (cassetto «Disc») e la sua calibrazione "
                      "arrivano nel passo successivo.",
}


# --------------------------------------------------------------------------
# Inglese (incorporato). Le chiavi mancanti ricadono sull'italiano.
# --------------------------------------------------------------------------
STRINGS_EN = {
    "app_title": "Cover Studio",
    "help_tooltip": "Help and information",
    "tt_format": "Choose what to print: cover, disc or adhesive label",
    "tt_load": "Open the image to print",
    "tt_clear": "Remove the image and clear the preview",
    "tt_batch": "Print several covers one after another",
    "tt_editor": "Create or edit print formats",
    "tt_options": "Cut lines, calibration and other settings",
    "tt_print": "Open the print dialog",
    "tt_close": "Close this window",
    "tt_opt_cut": "Print cut lines at the sheet corners",
    "tt_opt_fold": "Print fold lines (multi-section formats)",
    "tt_offx": "Shift disc printing horizontally (mm)",
    "tt_offy": "Shift disc printing vertically (mm)",
    "tt_calib_reset": "Reset calibration to zero",
    "tt_calib_test": "Print a test page to center the disc",
    "tt_lang": "App language (applied after restart)",
    "tt_factory_reset": "Restore formats and settings to factory values",
    "tt_donate": "Open the PayPal donation page",
    "tt_ed_list": "Select one of your formats to edit",
    "tt_ed_new": "Create a new format",
    "tt_ed_delete": "Delete the selected format",
    "tt_ed_name": "Format name",
    "tt_ed_type": "Format type: cover, disc or adhesive label",
    "tt_ed_unit": "Unit: millimeters or pixels",
    "tt_ed_height": "Cover height",
    "tt_ed_totalw": "Total cover width",
    "tt_ed_count": "Number of sections (e.g. front, spine, back)",
    "tt_ed_spine": "Which section is the spine",
    "tt_ed_outer": "Disc outer diameter (mm)",
    "tt_ed_hole": "Center hole diameter (mm)",
    "tt_ed_page": "Sheet size",
    "tt_ed_page_w": "Custom sheet width (mm)",
    "tt_ed_page_h": "Custom sheet height (mm)",
    "tt_ed_sheet_count": "Number of labels on the sheet",
    "tt_pos_h": "Horizontal distance of the label from the sheet edge (mm)",
    "tt_pos_v": "Vertical distance of the label from the sheet edge (mm)",
    "tt_ed_save": "Save the format",
    "tt_ed_sec_name": "Section name",
    "tt_ed_sec_width": "Section width",
    "tt_batch_combo": "Format of the covers to batch print",
    "tt_batch_add": "Add an image to the batch",
    "tt_batch_clear": "Clear the batch",
    "tt_batch_print": "Print all covers in the batch",
    "tt_batch_trash": "Remove this cover from the batch",
    # --- Help / About ("?" button) ---
    "help": "?",
    "help_title": "Help",
    "help_sec_cover": "Cover",
    "help_sec_disc": "Disc label",
    "help_sec_sheet": "Adhesive labels",
    "help_sec_print": "Printing",
    "help_sec_lang": "Language and translation",
    "help_body_cover": (
        "Choose the format from the «Format» drop-down at the top (for "
        "example CD, DVD…).\n\n"
        "Click «Load image…» and select the file. The image is fitted "
        "automatically: it is shown whole and centered, with white bands at "
        "the sides if the proportions don't match. This way it is never "
        "cropped.\n\n"
        "The preview shows the cut lines at the corners and, if the format "
        "has several sections, the dashed blue fold lines (these are shown "
        "on screen only and are not printed).\n\n"
        "When you are ready, click «Print…»: the cover is printed on landscape "
        "A4 paper, at its real calibrated size, with the cut lines extending "
        "to the edge of the sheet.\n\n"
        "«Remove image» removes the image and returns the preview to its empty "
        "state, showing the section names."
    ),
    "help_body_disc": (
        "«Disc» formats have an outer diameter and a center hole. You can "
        "create new ones or edit them in the Editor.\n\n"
        "When no image is loaded, the preview shows a calibration pattern "
        "(concentric circles with axes): it is used to check that printing is "
        "centered on the disc.\n\n"
        "Centering on the tray is set only once, in Options → «Printer "
        "calibration (discs)», using a test print: adjust the X and Y values "
        "until the disc comes out centered. That calibration then applies to "
        "all discs.\n\n"
        "When printing, choose the paper source for discs in the printer "
        "dialog (on the Epson ET-8500 it is called «Disc»)."
    ),
    "help_body_sheet": (
        "«Adhesive label» formats represent a sheet (of any size you choose) "
        "with one or two labels.\n\n"
        "Use the position controls to set the distance of each label from "
        "the edges of the sheet: from the left, right, top or bottom. The "
        "preview on the right shows the sheet with the labels in place.\n\n"
        "With two labels you can turn on the «Mirror lock», the chain icon: "
        "when you move one label, the other mirrors it automatically. Click "
        "the chain to unlock them and move them independently.\n\n"
        "To print, load the image and click «Print…»: it is reproduced on "
        "every label of the sheet. Without an image, «Print…» produces a test "
        "page with just the outlines and a cross mark, useful for aligning "
        "pre-cut sheets."
    ),
    "help_body_print": (
        "The «Print…» button opens the system print dialog, where you choose "
        "the printer, the paper source and the paper size.\n\n"
        "In Options you can turn printing of cut lines and fold lines on or "
        "off.\n\n"
        "«Batch print» (button at the top) prints several covers one after "
        "another: add the images to the queue and send them all to the "
        "printer together.\n\n"
        "It works with any printer recognized by the system. It has been "
        "tested with an Epson ET-8500, including direct printing on discs. "
        "Printing on discs requires a printer that supports it."
    ),
    "help_body_lang": (
        "The app is available in Italian and English (Options → Language; "
        "the change is applied at the next start).\n\n"
        "You can also add a new language, or correct the existing texts, "
        "without any programming. On first start the app creates the folder "
        "~/.config/cover-studio/lang/ with two template files: it.json and "
        "en.json.\n\n"
        "For a new language: copy en.json and rename it with the language "
        "code (for example fr.json for French, de.json for German). Open it "
        "with a text editor, change the «_lang_name» entry to the name of the "
        "language (for example «Français») and translate only the texts in "
        "quotes on the right, leaving the words on the left unchanged.\n\n"
        "Save, restart the app and choose the new language in Options → "
        "Language. Any untranslated text automatically stays in Italian, so "
        "nothing is ever left blank."
    ),
    "help_about_title": "About",
    "help_app_line": "Cover Studio  ·  version %s",
    "help_version": "1.0",
    "help_about_desc": ("Printing of covers, disc labels and adhesive label "
                        "sheets on Linux."),
    "help_license": "License: GPL-3.0  —  free and open source software",
    "help_donate": "Support development",
    "help_donate_hint": ("Cover Studio is free and open source. If you find it "
                         "useful and feel like it, you can buy me a coffee."),
    "format": "Format:",
    "load_image": "Load image...",
    "remove_image": "Remove image",
    "print": "Print...",
    "options": "Options",
    "choose_image": "Choose the cover image",
    "cancel": "Cancel",
    "open": "Open",
    "images": "Images",
    "st_print": "Print",
    "st_image": "Image",
    "st_none": "none",
    "st_state": "State",
    "state_ready": "ready",
    "state_loaded": "image loaded",
    "state_printed": "sent to printer",
    "error": "Error",
    "image_open_error": "Cannot open the image:\n%s",
    "print_error_title": "Print error",
    "print_error": "An error occurred while printing.",
    "options_title": "Options",
    "opt_cut": "Print cut lines",
    "opt_fold": "Print fold lines",
    "opt_reset": "Restore factory settings",
    "opt_offset_title": "Printer offset (calibration)",
    "opt_offset_hint": "Tray centering correction, applied to all discs.\nSet it once, with a test print.",
    "opt_calib_testprint": "Test print",
    "opt_calib_reset": "Reset calibration",
    "opt_calib_readout": "Offset X %+.1f mm    Y %+.1f mm",
    "opt_sec_print": "Print (cover)",
    "opt_sec_calib": "Printer calibration (discs)",
    "opt_sec_ui": "Interface",
    "opt_tooltips": "Show tooltips",
    "tt_tooltips": "Turn the help bubbles on or off (at restart)",
    "tooltips_restart_note": "This option will be applied the next time you open the app.",
    "opt_sec_lang": "Language",
    "opt_lang_label": "App language:",
    "opt_lang_custom": "To add or customize a language, see Help (the \u201c?\u201d "
                       "button).",
    "lang_restart_note": "The new language will be applied the next time you open the app.",
    "opt_sec_reset": "Reset",
    "reset_title": "Restore factory settings?",
    "reset_msg": ("This will delete all the formats you have created and all "
                  "saved print settings, and reset label measurements and "
                  "offsets.\n\nThis cannot be undone. The window and the last "
                  "used folder stay unchanged.\n\nDo you want to proceed?"),
    "reset_done_title": "Reset complete",
    "reset_done": ("Formats and print settings have been restored to factory "
                   "values."),
    "close": "Close",
    "editor": "Editor",
    "editor_title": "Format editor",
    "ed_your_formats": "Your formats:",
    "ed_new": "New",
    "ed_delete": "Delete",
    "ed_name": "Name:",
    "ed_unit": "Unit:",
    "ed_height": "Height:",
    "ed_totalw": "Total width:",
    "ed_count": "No. of sections:",
    "ed_sections": "Sections (max 3):",
    "ed_section": "Section",
    "ed_add_section": "+ section",
    "ed_del_section": "− section",
    "ed_spine": "Measure in title:",
    "ed_spine_none": "none",
    "ed_sum": "Sum:",
    "ed_mismatch": "does not match the total width",
    "ed_need_total": "Enter the total width",
    "ed_need_widths": "Enter the section widths",
    "ed_save": "Save",
    "ed_testprint": "Test print",
    "ed_testprint_tip": "Prints the format you are creating, empty (no image), to try it before saving.",
    "ed_invalid": "Invalid data",
    "ed_confirm_delete": "Delete the format \u201c%s\u201d?",
    "ed_revert": "Restore original",
    "ed_restore_presets": "Restore presets",
    "ed_restore_presets_tip": "Brings back the factory preset formats that were hidden, renamed or deleted, without touching your custom formats.",
    "ed_restore_presets_done_title": "Presets restored",
    "ed_restore_presets_done": "The factory preset formats have been restored. Your custom formats are unchanged.",
    "ed_modified": "  (modified)",
    "ed_confirm_revert": "Restore \u201c%s\u201d to the factory version?",
    "ed_type": "Type:",
    "ed_type_cover": "Cover",
    "ed_type_disc": "Disc",
    "ed_type_sheet": "Adhesive label",
    "ed_page": "Sheet size:",
    "ed_page_w": "Width (mm):",
    "ed_page_h": "Height (mm):",
    "ed_sheet_count": "No. of labels:",
    "ed_sheet_ok": "Sheet valid",
    "ed_pos_label": "Label %d:",
    "ed_pos_left": "From left:",
    "ed_pos_right": "From right:",
    "ed_pos_top": "From top:",
    "ed_pos_bottom": "From bottom:",
    "ed_label_word": "Label",
    "ed_mirror_lock": "Mirror lock",
    "ed_mirror_tip": "Keeps the two labels mirrored: moving one mirrors the other. Click to unlock.",
    "m_left": "Left",
    "m_right": "Right",
    "m_top": "Top",
    "m_bottom": "Bottom",
    "sheet_margins": "Label %d  \u2014  Left %.1f mm \u00b7 Right %.1f mm \u00b7 Top %.1f mm \u00b7 Bottom %.1f mm",
    "ed_outer": "Ø outer (mm):",
    "ed_hole": "Ø hole (mm):",
    "ed_disc_ok": "Disc measurements valid",
    "ed_disc_bad": "The hole must be smaller than the outer (and greater than zero)",
    "ed_need_disc": "Enter outer and hole diameter",
    "ed_hdr_name": "Name",
    "ed_hdr_width": "Width",
    "scrub_tip": "Press and drag horizontally to adjust",
    "yes": "Yes",
    "no": "No",
    "batch": "Batch print",
    "batch_title": "Batch print",
    "batch_format": "Format:",
    "batch_add": "Add...",
    "batch_clear": "Clear all",
    "batch_print": "Print",
    "choose_images": "Choose the images",
    "batch_empty": "No images. Use \u201cAdd\u2026\u201d to start.",
    "batch_count": "%d images queued",
    "lbl_outer": "Ø outer:",
    "lbl_hole": "Ø hole:",
    "lbl_offx": "Offset X:",
    "lbl_offy": "Offset Y:",
    "lbl_status": "Disc",
    "lbl_print_next": "Disc printing (the \u201cDisc\u201d tray) and its calibration "
                      "come in the next step.",
}


# --------------------------------------------------------------------------
# Registro lingue + caricamento. Lingue incorporate (sicurezza) + file JSON
# personalizzabili dall'utente in ~/.config/cover-studio/lang/<codice>.json
# (l'utente puo' aggiungerne o modificarli; le chiavi mancanti ricadono
# sull'italiano, cosi' l'interfaccia non resta mai vuota).
# --------------------------------------------------------------------------
BUILTIN_LANGS = {"it": STRINGS_IT, "en": STRINGS_EN}
BUILTIN_LANG_NAMES = {"it": "Italiano", "en": "English"}
USER_LANG_DIR = os.path.join(CONFIG_DIR, "lang")


def _read_lang_file(code):
    """Legge ~/.config/cover-studio/lang/<code>.json se esiste, altrimenti None."""
    path = os.path.join(USER_LANG_DIR, code + ".json")
    try:
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def available_languages():
    """Elenco (codice, nome) delle lingue disponibili: prima le incorporate,
    poi eventuali file JSON aggiunti dall'utente."""
    langs = []
    seen = set()
    for code in ("it", "en"):
        langs.append((code, BUILTIN_LANG_NAMES[code]))
        seen.add(code)
    try:
        for fn in sorted(os.listdir(USER_LANG_DIR)):
            if not fn.endswith(".json"):
                continue
            code = fn[:-5]
            if code in seen:
                continue
            data = _read_lang_file(code)
            name = (data.get("_lang_name") if isinstance(data, dict) else None) or code
            langs.append((code, name))
            seen.add(code)
    except Exception:
        pass
    return langs


def language_name(code):
    for c, n in available_languages():
        if c == code:
            return n
    return code


def load_language(code):
    """Costruisce la tabella testi per la lingua scelta. Base = italiano
    (sempre completo), poi sovrappongo l'incorporata e infine l'eventuale file
    utente, cosi' nessuna scritta resta mai vuota."""
    merged = dict(STRINGS_IT)
    if code in BUILTIN_LANGS:
        merged.update(BUILTIN_LANGS[code])
    user = _read_lang_file(code)
    if user:
        merged.update({k: v for k, v in user.items() if isinstance(v, str)})
    return merged


def seed_user_lang_files():
    """Scrive i file modello it.json / en.json nella cartella utente (se non
    esistono), cosi' chi vuole aggiungere una lingua puo' copiarne uno e
    tradurlo. Se non e' scrivibile, pazienza: le incorporate bastano."""
    try:
        os.makedirs(USER_LANG_DIR, exist_ok=True)
        for code, table in BUILTIN_LANGS.items():
            path = os.path.join(USER_LANG_DIR, code + ".json")
            if not os.path.exists(path):
                out = {"_lang_name": BUILTIN_LANG_NAMES[code]}
                out.update(table)
                with open(path, "w", encoding="utf-8") as fp:
                    json.dump(out, fp, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Tabella testi attiva. Parte in italiano; all'avvio viene riempita con la
# lingua salvata. Tutto il programma usa T["chiave"].
T = dict(STRINGS_IT)


def load_settings():
    try:
        with open(CONFIG_FILE) as fp:
            return json.load(fp)
    except Exception:
        return {}


def save_settings(d):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as fp:
            json.dump(d, fp)
    except Exception:
        pass


def _norm_numbers(v):
    """Normalizza i numeri (int/float arrotondati) per confrontare due formati
    senza falsi 'diversi' dovuti a 1535 vs 1535.0."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 3)
    if isinstance(v, dict):
        return {k: _norm_numbers(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm_numbers(x) for x in v]
    return v


def formats_equal(a, b):
    """True se due formati sono uguali a parte la forma dei numeri."""
    return _norm_numbers(a) == _norm_numbers(b)


def pixbuf_to_surface(pb):
    w, h = pb.get_width(), pb.get_height()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surface)
    Gdk.cairo_set_source_pixbuf(ctx, pb, 0, 0)
    ctx.paint()
    return surface


class CoverStudioWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=T["app_title"])
        self.set_border_width(10)

        self.current_format = "Cover DVD"
        self.formats = all_formats()      # base (fissi) + personalizzati
        self.image_surface = None
        self.image_name = None
        self.state = T["state_ready"]
        self.batch_items = []
        self.settings = load_settings()
        self.win_options = None
        self.win_help = None

        # Opzioni di stampa (default: entrambe attive)
        self.opt_show_cut = bool(self.settings.get("show_cut", True))
        self.opt_show_fold = bool(self.settings.get("show_fold", True))
        self.show_tooltips = bool(self.settings.get("show_tooltips", True))

        # Ripristina dimensione e posizione della finestra (con protezione
        # anti "fuori schermo"); altrimenti dimensione di default centrata.
        w = self.settings.get("win_w")
        h = self.settings.get("win_h")
        if isinstance(w, int) and isinstance(h, int) and w > 200 and h > 200:
            self.set_default_size(w, h)
        else:
            self.set_default_size(1000, 840)
        x = self.settings.get("win_x")
        y = self.settings.get("win_y")
        if isinstance(x, int) and isinstance(y, int) and self._point_on_screen(x, y):
            self.move(x, y)
        # salva geometria alla chiusura
        self.connect("delete-event", self.on_delete)

        # Impostazioni di stampa dell'ultima volta, separate Cover / Label.
        self.print_settings_cover = self._load_print_settings(PRINT_SETTINGS_COVER)
        self.print_settings_label = self._load_print_settings(PRINT_SETTINGS_LABEL)
        self.print_settings_sheet = self._load_print_settings(PRINT_SETTINGS_SHEET)
        # Pagina (dimensione carta) memorizzata per la Label, catturata dall'ultima
        # stampa reale; e' il modo affidabile per ricordare 120x120.Borderless.
        self.page_setup_label = self._load_page_setup(PAGE_SETUP_LABEL)
        self._captured_label_page_setup = None
        # Quale percorso ha lanciato la stampa in corso (per salvare nel posto giusto).
        self._print_target = "cover"

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(root)

        topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        topbar.pack_start(Gtk.Label(label=T["format"]), False, False, 0)

        self.format_names = list(self.formats.keys())
        self.combo = Gtk.ComboBoxText()
        for nm in self.format_names:
            self.combo.append_text(display_name(nm, self.formats[nm]))
        self.combo.set_active(0)
        self.combo.set_tooltip_text(T["tt_format"])
        self.combo.connect("changed", self.on_format_changed)
        topbar.pack_start(self.combo, False, False, 0)

        self.btn_load = Gtk.Button(label=T["load_image"])
        self.btn_load.set_tooltip_text(T["tt_load"])
        self.btn_load.connect("clicked", self.on_load_clicked)
        topbar.pack_start(self.btn_load, False, False, 0)

        self.btn_clear = Gtk.Button(label=T["remove_image"])
        self.btn_clear.set_tooltip_text(T["tt_clear"])
        self.btn_clear.connect("clicked", self.on_clear_clicked)
        self.btn_clear.set_sensitive(False)
        topbar.pack_start(self.btn_clear, False, False, 0)

        self.btn_print = Gtk.Button(label=T["print"])
        self.btn_print.get_style_context().add_class("suggested-action")
        self.btn_print.set_tooltip_text(T["tt_print"])
        self.btn_print.connect("clicked", self.on_print_clicked)
        topbar.pack_end(self.btn_print, False, False, 0)

        self.btn_help = Gtk.Button(label=T["help"])
        self.btn_help.set_tooltip_text(T["help_tooltip"])
        self.btn_help.connect("clicked", self.on_help_clicked)
        topbar.pack_end(self.btn_help, False, False, 0)

        self.btn_options = Gtk.Button(label=T["options"])
        self.btn_options.set_tooltip_text(T["tt_options"])
        self.btn_options.connect("clicked", self.on_options_clicked)
        topbar.pack_end(self.btn_options, False, False, 0)

        self.btn_editor = Gtk.Button(label=T["editor"])
        self.btn_editor.set_tooltip_text(T["tt_editor"])
        self.btn_editor.connect("clicked", self.on_editor_clicked)
        topbar.pack_end(self.btn_editor, False, False, 0)

        self.btn_batch = Gtk.Button(label=T["batch"])
        self.btn_batch.set_tooltip_text(T["tt_batch"])
        self.btn_batch.connect("clicked", self.on_batch_clicked)
        topbar.pack_end(self.btn_batch, False, False, 0)

        root.pack_start(topbar, False, False, 0)

        # (La vecchia barra disco in alto e' stata rimossa: esterno/foro sono
        #  proprieta' del supporto e si vedono nella barra di stato; gli offset
        #  di stampa sono diventati una taratura unica, in Opzioni.)

        self.preview = Gtk.DrawingArea()
        self.preview.connect("draw", self.on_draw_preview)
        frame = Gtk.Frame()
        frame.add(self.preview)
        root.pack_start(frame, True, True, 0)

        self.status = Gtk.Label()
        self.status.set_xalign(0.0)
        root.pack_start(self.status, False, False, 0)

        self.update_status()
        self._update_label_bar()
        self._apply_tooltip_pref(self)   # se i suggerimenti sono spenti, li rimuove

    def _fmt(self):
        f = dict(self.formats[self.current_format])
        f["_name"] = self.current_format
        return f

    def on_format_changed(self, combo):
        idx = combo.get_active()
        if 0 <= idx < len(self.format_names):
            self.current_format = self.format_names[idx]
            self._update_label_bar()
            self.update_status()
            self.preview.queue_draw()

    def _is_label(self, name=None):
        f = self.formats.get(name or self.current_format, {})
        return f.get("kind") == "label"

    def _is_sheet(self, name=None):
        f = self.formats.get(name or self.current_format, {})
        return f.get("kind") == "sheet"

    def _update_label_bar(self):
        # La barra disco in alto non esiste piu': esterno/foro stanno nel formato
        # (e nella barra di stato), gli offset sono in Opzioni. Metodo lasciato
        # come no-op per non toccare i punti che lo richiamano.
        pass

    def _label_params(self):
        # esterno/foro vengono dal SUPPORTO (formato); offset dalla TARATURA stampante
        f = self.formats.get(self.current_format, {})
        d = label_defaults()
        return {
            "outer": float(f.get("outer_mm", d["outer"])),
            "hole": float(f.get("hole_mm", d["hole"])),
            "offx": float(self.settings.get("printer_offx", 0.0)),
            "offy": float(self.settings.get("printer_offy", 0.0)),
        }

    def on_label_param_changed(self, spin, key):
        self.settings[key] = round(spin.get_value(), 1)
        save_settings(self.settings)
        self.update_status()
        self.preview.queue_draw()
        if getattr(self, "calib_area", None) is not None:
            self.calib_area.queue_draw()

    # ---------------- Vista di calibrazione (Opzioni) ----------------
    def _calib_metrics(self, area):
        alloc = area.get_allocation()
        W, H = alloc.width, alloc.height
        view_mm = 136.0
        margin = 18
        scale = (min(W, H) - 2 * margin) / view_mm
        return W, H, W / 2.0, H / 2.0, scale

    def _calib_draw(self, area, cr):
        W, H, cx, cy, scale = self._calib_metrics(area)
        if scale <= 0:
            return False
        # tela neutra: uguale su tema chiaro e scuro
        cr.set_source_rgb(0.94, 0.94, 0.94)
        cr.paint()
        # disco fisico (120 mm)
        cr.set_source_rgb(0.86, 0.86, 0.86)
        cr.arc(cx, cy, 60.0 * scale, 0, 2 * math.pi)
        cr.fill()
        # anelli di riferimento + misure (gli stessi della stampa di prova)
        cr.select_font_face("Sans")
        cr.set_font_size(11)
        NE = -math.pi / 4.0
        cos_ne, sin_ne = math.cos(NE), math.sin(NE)
        for d in (20, 40, 60, 80, 100, 120):
            r = (d / 2.0) * scale
            cr.set_source_rgb(0.45, 0.45, 0.45)
            cr.set_line_width(1.0)
            cr.new_sub_path()
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()
            s = "%d" % d
            ext = cr.text_extents(s)
            px = cx + cos_ne * r
            py = cy + sin_ne * r
            cr.set_source_rgb(0.94, 0.94, 0.94)            # alone
            cr.rectangle(px - ext.width / 2.0 - 2, py - ext.height / 2.0 - 2,
                         ext.width + 4, ext.height + 4)
            cr.fill()
            cr.set_source_rgb(0.30, 0.30, 0.30)
            cr.move_to(px - ext.width / 2.0 - ext.x_bearing,
                       py - ext.height / 2.0 - ext.y_bearing)
            cr.show_text(s)
        # bersaglio: centro vero del disco (fisso)
        cr.set_source_rgb(0.25, 0.25, 0.25)
        cr.set_line_width(1.0)
        cr.move_to(cx - 11, cy)
        cr.line_to(cx + 11, cy)
        cr.move_to(cx, cy - 11)
        cr.line_to(cx, cy + 11)
        cr.stroke()
        # segno dell'offset (accento), trascinabile
        offx = float(self.settings.get("printer_offx", 0.0))
        offy = float(self.settings.get("printer_offy", 0.0))
        mx, my = cx + offx * scale, cy + offy * scale
        # cerchio grande = bordo esterno "spostato": la sensazione di muovere il disco
        cr.set_source_rgba(0.10, 0.45, 0.90, 0.85)
        cr.set_line_width(1.6)
        cr.new_sub_path()
        cr.arc(mx, my, 60.0 * scale, 0, 2 * math.pi)
        cr.stroke()
        # linea dal centro vero al segno
        cr.set_source_rgba(0.10, 0.45, 0.90, 0.55)
        cr.set_line_width(1.5)
        cr.set_dash([4, 3])
        cr.move_to(cx, cy)
        cr.line_to(mx, my)
        cr.stroke()
        cr.set_dash([])
        # mirino del segno
        cr.set_source_rgb(0.10, 0.45, 0.90)
        cr.set_line_width(2.0)
        cr.new_sub_path()
        cr.arc(mx, my, 7, 0, 2 * math.pi)
        cr.stroke()
        cr.move_to(mx - 12, my)
        cr.line_to(mx + 12, my)
        cr.move_to(mx, my - 12)
        cr.line_to(mx, my + 12)
        cr.stroke()
        # lettura numerica
        cr.set_source_rgb(0.20, 0.20, 0.20)
        cr.set_font_size(12)
        cr.move_to(12, H - 12)
        cr.show_text(T["opt_calib_readout"] % (offx, offy))
        return False

    def _calib_apply_mouse(self, area, x, y):
        W, H, cx, cy, scale = self._calib_metrics(area)
        if scale <= 0:
            return
        mmx = max(-5.0, min(5.0, (x - cx) / scale))
        mmy = max(-5.0, min(5.0, (y - cy) / scale))
        # aggiorno gli spinner: salvano e ridisegnano tutto (anche questa vista)
        if getattr(self, "sp_offx", None) is not None:
            self.sp_offx.set_value(round(mmx, 1))
        if getattr(self, "sp_offy", None) is not None:
            self.sp_offy.set_value(round(mmy, 1))

    def _calib_press(self, area, event):
        if event.button == 1:
            self._calib_drag = True
            self._calib_apply_mouse(area, event.x, event.y)
        return True

    def _calib_motion(self, area, event):
        if getattr(self, "_calib_drag", False) and \
                (event.state & Gdk.ModifierType.BUTTON1_MASK):
            self._calib_apply_mouse(area, event.x, event.y)
        return True

    def _calib_release(self, area, event):
        self._calib_drag = False
        return True

    def on_calib_reset(self, button):
        # azzera solo la taratura (offset X/Y -> 0); gli spinner salvano e ridisegnano
        for sb in (getattr(self, "sp_offx", None), getattr(self, "sp_offy", None)):
            if sb is not None:
                sb.set_value(0.0)

    def on_calib_testprint(self, button):
        self._print_target = "label"          # riusa le impostazioni Label
        op = Gtk.PrintOperation()
        op.set_embed_page_setup(True)
        op.set_use_full_page(False)
        op.set_unit(Gtk.Unit.MM)
        op.set_n_pages(1)
        op.set_job_name(T["app_title"] + " - " + T["opt_calib_testprint"])
        if self.print_settings_label is not None:
            op.set_print_settings(self.print_settings_label)
        if self.page_setup_label is not None:
            op.set_default_page_setup(self.page_setup_label)
        op.set_allow_async(True)
        op.connect("draw-page", self.on_calib_test_draw_page)
        op.connect("done", self.on_print_done)
        self._print_op = op
        try:
            op.run(Gtk.PrintOperationAction.PRINT_DIALOG,
                   getattr(self, "win_options", None) or self)
        except Exception as e:
            self._print_op = None
            self._info(T["print_error_title"], str(e), error=True)

    def on_calib_test_draw_page(self, operation, context, page_nr):
        cr = context.get_cairo_context()          # gia' in millimetri
        try:
            self._captured_label_page_setup = context.get_page_setup()
        except Exception:
            self._captured_label_page_setup = None
        pw = context.get_width()
        ph = context.get_height()
        offx = float(self.settings.get("printer_offx", 0.0))
        offy = float(self.settings.get("printer_offy", 0.0))
        draw_calibration(cr, pw / 2.0 + offx, ph / 2.0 + offy, 20.0, 120.0)

    def _draw_label_preview(self, cr, area):
        p = self._label_params()
        alloc = area.get_allocation()
        W, H = alloc.width, alloc.height
        cr.set_source_rgb(0.90, 0.90, 0.90)
        cr.paint()
        VIEW_MM = 124.0                 # scala FISSA (non cambia coi diametri)
        margin = 28
        scale = (min(W, H) - 2 * margin) / VIEW_MM
        if scale <= 0:
            return
        # disco centrato: l'offset e' una taratura di stampa e si regola in Opzioni
        cx, cy = W / 2.0, H / 2.0
        outer_r = max(p["outer"], 0.0) / 2.0 * scale
        hole_r = max(p["hole"], 0.0) / 2.0 * scale

        # corpo del disco
        cr.set_source_rgb(0.82, 0.82, 0.82)
        cr.arc(cx, cy, outer_r, 0, 2 * math.pi)
        cr.fill()
        # immagine (se caricata), ritagliata all'anello disco
        if self.image_surface is not None:
            draw_label(cr, cx, cy, outer_r, hole_r, self.image_surface)
        # foro
        cr.set_source_rgb(1, 1, 1)
        cr.new_sub_path()
        cr.arc(cx, cy, hole_r, 0, 2 * math.pi)
        cr.fill()
        # contorni pieni: esterno = bordo stampabile, interno = foro
        cr.set_source_rgba(0.35, 0.35, 0.35, 0.95)
        cr.set_line_width(1.2)
        cr.new_sub_path()
        cr.arc(cx, cy, outer_r, 0, 2 * math.pi)
        cr.stroke()
        cr.new_sub_path()
        cr.arc(cx, cy, hole_r, 0, 2 * math.pi)
        cr.stroke()

    def update_status(self):
        f = self.formats[self.current_format]
        if f.get("kind") == "sheet":
            img = self.image_name or T["st_none"]
            txt = ("  %s  -  %s, %d etichette Ø %.1f mm  -  %s: %s  -  %s: %s"
                   % (display_name(self.current_format, f),
                      f.get("page_name", "A4"), f.get("count", 1),
                      f.get("outer_mm", 0.0),
                      T["st_image"], img, T["st_state"], self.state))
            self.status.set_text(txt)
            return
        if f.get("kind") == "label":
            p = self._label_params()
            img = self.image_name or T["st_none"]
            txt = ("  %s  -  Ø %.1f mm / foro %.1f mm  -  %s: %s  -  %s: %s"
                   % (display_name(self.current_format, f), p["outer"], p["hole"],
                      T["st_image"], img, T["st_state"], self.state))
            self.status.set_text(txt)
            return
        pxw, pxh = template_size_px(f)
        mmw, mmh = print_size_mm(f)
        img = self.image_name or T["st_none"]
        txt = ("  %s  -  %s %d x %d px (%.1f x %.1f mm)  -  %s: %s  -  %s: %s"
               % (display_name(self.current_format, f), T["st_print"], pxw, pxh,
                  mmw, mmh, T["st_image"], img, T["st_state"], self.state))
        self.status.set_text(txt)

    # ------------------------------------------------------------ IMMAGINE
    def on_load_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=T["choose_image"], parent=self,
            action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(T["cancel"], Gtk.ResponseType.CANCEL,
                           T["open"], Gtk.ResponseType.OK)
        dialog.add_filter(self._image_filter())

        # Ricorda l'ultima cartella usata
        last = self.settings.get("last_folder")
        if last and os.path.isdir(last):
            dialog.set_current_folder(last)

        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            dialog.destroy()
            self.load_image(path)
        else:
            dialog.destroy()

    def load_image(self, path):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(path)
            self.image_surface = pixbuf_to_surface(pb)
            self.image_name = os.path.basename(path)
            self.btn_clear.set_sensitive(True)
            # Salva la cartella per la prossima volta
            self.settings["last_folder"] = os.path.dirname(path)
            save_settings(self.settings)
            self.state = T["state_loaded"]
            self.update_status()
            self.preview.queue_draw()
        except Exception as e:
            self._info(T["error"], T["image_open_error"] % e, error=True)

    def on_clear_clicked(self, button):
        self.image_surface = None
        self.image_name = None
        self.state = T["state_ready"]
        self.btn_clear.set_sensitive(False)
        self.update_status()
        self.preview.queue_draw()

    # ------------------------------------------------------------ STAMPA
    def _load_print_settings(self, path):
        """Carica un file di impostazioni di stampa, o None se assente/illeggibile."""
        if os.path.exists(path):
            try:
                return Gtk.PrintSettings.new_from_file(path)
            except Exception:
                return None
        return None

    def _load_page_setup(self, path):
        """Carica una PageSetup salvata (la pagina della Label, es.
        120x120.Borderless), o None se assente/illeggibile."""
        if os.path.exists(path):
            try:
                return Gtk.PageSetup.new_from_file(path)
            except Exception:
                return None
        return None

    def on_print_clicked(self, button):
        if self._is_sheet():
            self.on_sheet_print()
            return
        if self._is_label():
            self.on_label_print()
            return
        self._print_target = "cover"
        op = Gtk.PrintOperation()
        setup = Gtk.PageSetup()
        setup.set_paper_size(Gtk.PaperSize.new("iso_a4"))
        setup.set_orientation(Gtk.PageOrientation.LANDSCAPE)
        op.set_default_page_setup(setup)
        op.set_use_full_page(False)
        op.set_unit(Gtk.Unit.MM)
        op.set_n_pages(1)
        op.set_job_name(T["app_title"] + " - " + self.current_format)

        # Riusa le impostazioni Cover dell'ultima stampa (carta, qualita'...)
        if self.print_settings_cover is not None:
            op.set_print_settings(self.print_settings_cover)

        # Stampa ASINCRONA: l'interfaccia non si blocca durante la stampa.
        # Teniamo un riferimento stabile all'operazione finche' non e' finita.
        op.set_allow_async(True)
        op.connect("draw-page", self.on_draw_page)
        op.connect("done", self.on_print_done)
        self._print_op = op
        try:
            op.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
        except Exception as e:
            self._print_op = None
            self._info(T["print_error_title"], str(e), error=True)

    def on_print_done(self, operation, result):
        if result == Gtk.PrintOperationResult.ERROR:
            self._info(T["print_error_title"], T["print_error"], error=True)
        elif result == Gtk.PrintOperationResult.APPLY:
            # Memorizza le impostazioni nel contenitore giusto (Cover o Label),
            # cosi' i due tipi non si sovrascrivono a vicenda.
            settings = operation.get_print_settings()
            if self._print_target == "label":
                self.print_settings_label = settings
                path = PRINT_SETTINGS_LABEL
            elif self._print_target == "sheet":
                self.print_settings_sheet = settings
                path = PRINT_SETTINGS_SHEET
            else:
                self.print_settings_cover = settings
                path = PRINT_SETTINGS_COVER
            try:
                os.makedirs(CONFIG_DIR, exist_ok=True)
                settings.to_file(path)
                # Per la Label salvo anche la pagina catturata (dimensione carta).
                if self._print_target == "label" and self._captured_label_page_setup is not None:
                    self._captured_label_page_setup.to_file(PAGE_SETUP_LABEL)
                    self.page_setup_label = self._captured_label_page_setup
            except Exception:
                pass
            self.state = T["state_printed"]
            self.update_status()
        self._print_op = None

    def on_draw_page(self, operation, context, page_nr):
        cr = context.get_cairo_context()   # gia' in millimetri
        # Dimensioni dell'AREA STAMPABILE (mm) della stampante scelta
        page_mm = (context.get_width(), context.get_height())
        draw_cover(cr, self._fmt(), page_mm, self.image_surface,
                   show_cut=self.opt_show_cut, show_fold=self.opt_show_fold)

    # --- stampa LABEL: niente A4 forzato, disegno tondo centrato nell'area ---
    def on_label_print(self):
        self._print_target = "label"
        op = Gtk.PrintOperation()
        # Abilitiamo la scelta di dimensione carta / orientamento nel dialogo,
        # cosi' l'utente puo' selezionare il formato disco (120x120.Borderless)
        # esposto dal driver.
        op.set_embed_page_setup(True)
        op.set_use_full_page(False)
        op.set_unit(Gtk.Unit.MM)
        op.set_n_pages(1)
        op.set_job_name(T["app_title"] + " - " + T["lbl_status"])
        # Ripristina le impostazioni Label dell'ultima volta...
        if self.print_settings_label is not None:
            op.set_print_settings(self.print_settings_label)
        # ...e la pagina scelta l'ultima volta (es. 120x120.Borderless), cosi' il
        # dialogo non riparte da A4. La pagina viene catturata in on_label_draw_page.
        if self.page_setup_label is not None:
            op.set_default_page_setup(self.page_setup_label)
        op.set_allow_async(True)
        op.connect("draw-page", self.on_label_draw_page)
        op.connect("done", self.on_print_done)
        self._print_op = op
        try:
            op.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
        except Exception as e:
            self._print_op = None
            self._info(T["print_error_title"], str(e), error=True)

    def on_label_draw_page(self, operation, context, page_nr):
        cr = context.get_cairo_context()        # gia' in millimetri
        # Catturo la pagina realmente usata (dimensione carta scelta nel dialogo):
        # la salveremo in on_print_done per riproporla la prossima volta.
        try:
            self._captured_label_page_setup = context.get_page_setup()
        except Exception:
            self._captured_label_page_setup = None
        pw = context.get_width()
        ph = context.get_height()
        p = self._label_params()
        cx = pw / 2.0 + p["offx"]
        cy = ph / 2.0 + p["offy"]
        outer_r = max(p["outer"], 0.0) / 2.0
        hole_r = max(p["hole"], 0.0) / 2.0
        if self.image_surface is not None:
            draw_label(cr, cx, cy, outer_r, hole_r, self.image_surface)
        else:
            # senza immagine: stampa di prova alle misure REALI del formato
            draw_test_marks(cr, cx, cy, outer_r, hole_r)

    # --- stampa FOGLIO adesivo: A4 a pagina intera, etichette nelle posizioni
    #     impostate; con immagine stampo solo le immagini, senza immagine una
    #     stampa di prova (contorni + crocetta) per allineare il foglio. ---
    def on_sheet_print(self):
        self._print_target = "sheet"
        f = self._fmt()
        pw = float(f.get("page_w_mm", 210.0))
        ph = float(f.get("page_h_mm", 297.0))
        op = Gtk.PrintOperation()
        # Pagina intera: l'origine e' l'angolo FISICO del foglio, cosi' le
        # etichette cadono esattamente dove sono sul foglio pre-fustellato.
        op.set_use_full_page(True)
        op.set_unit(Gtk.Unit.MM)
        op.set_n_pages(1)
        op.set_job_name(T["app_title"] + " - " + T["ed_type_sheet"])
        # Imposto la dimensione carta del formato (A4 o personalizzata), verticale.
        setup = Gtk.PageSetup()
        if abs(pw - 210.0) < 0.5 and abs(ph - 297.0) < 0.5:
            setup.set_paper_size(Gtk.PaperSize.new("iso_a4"))
        else:
            setup.set_paper_size(Gtk.PaperSize.new_custom(
                "cover-studio-sheet", "Cover Studio sheet",
                pw, ph, Gtk.Unit.MM))
        setup.set_orientation(Gtk.PageOrientation.PORTRAIT)
        op.set_default_page_setup(setup)
        # Riuso le impostazioni dell'ultima stampa di foglio (stampante, qualita').
        if self.print_settings_sheet is not None:
            op.set_print_settings(self.print_settings_sheet)
        op.set_allow_async(True)
        op.connect("draw-page", self.on_sheet_draw_page)
        op.connect("done", self.on_print_done)
        self._print_op = op
        try:
            op.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
        except Exception as e:
            self._print_op = None
            self._info(T["print_error_title"], str(e), error=True)

    def on_sheet_draw_page(self, operation, context, page_nr):
        cr = context.get_cairo_context()        # gia' in millimetri
        f = self._fmt()
        pw = float(f.get("page_w_mm", 210.0))
        ph = float(f.get("page_h_mm", 297.0))
        outer = float(f.get("outer_mm", 0.0))
        hole = float(f.get("hole_mm", 0.0))
        outer_r = max(outer, 0.0) / 2.0
        hole_r = max(hole, 0.0) / 2.0
        labels = f.get("labels") or sheet_label_positions(
            pw, ph, f.get("count", 1))
        if self.image_surface is not None:
            # stampa reale: solo l'immagine su ogni etichetta (niente contorni)
            for lab in labels:
                draw_label(cr, lab.get("x_mm", pw / 2.0),
                           lab.get("y_mm", ph / 2.0),
                           outer_r, hole_r, self.image_surface)
        else:
            # stampa di prova: contorni alle misure reali + crocetta (come il Disco)
            for lab in labels:
                draw_test_marks(cr, lab.get("x_mm", pw / 2.0),
                                lab.get("y_mm", ph / 2.0), outer_r, hole_r)

    def _info(self, title, text, error=False):
        mtype = Gtk.MessageType.ERROR if error else Gtk.MessageType.INFO
        d = Gtk.MessageDialog(transient_for=self, modal=True,
                              message_type=mtype, buttons=Gtk.ButtonsType.OK,
                              text=title)
        d.format_secondary_text(text)
        d.run()
        d.destroy()

    # ------------------------------------------------------------ OPZIONI
    def on_options_clicked(self, button):
        # Se gia' aperta, la porto in primo piano
        if self.win_options is not None:
            self.win_options.present()
            return

        win = Gtk.Window(title=T["options_title"])
        win.set_border_width(14)
        self.win_options = win

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        win.add(box)

        def _section(title, first=False):
            if not first:
                box.pack_start(Gtk.Separator(), False, False, 6)
            lbl = Gtk.Label(xalign=0.0)
            lbl.set_markup("<b>%s</b>" % title)
            box.pack_start(lbl, False, False, 0)

        def _col_header(col, title):
            lbl = Gtk.Label(xalign=0.0)
            lbl.set_markup("<b>%s</b>" % title)
            col.pack_start(lbl, False, False, 0)

        # === Riga superiore: tre colonne affiancate (larghezza uguale) ===
        toprow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        col_print = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_ui = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_lang = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        # stessa larghezza per le tre colonne, indipendente dal contenuto
        col_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        for _c in (col_print, col_ui, col_lang):
            col_group.add_widget(_c)
        toprow.pack_start(col_print, True, True, 0)
        toprow.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),
                          False, False, 0)
        toprow.pack_start(col_ui, True, True, 0)
        toprow.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),
                          False, False, 0)
        toprow.pack_start(col_lang, True, True, 0)
        box.pack_start(toprow, False, False, 0)

        # --- Colonna 1: Stampa (cover) ---
        _col_header(col_print, T["opt_sec_print"])
        chk_cut = Gtk.CheckButton(label=T["opt_cut"])
        chk_cut.set_active(self.opt_show_cut)
        chk_cut.set_tooltip_text(T["tt_opt_cut"])
        chk_cut.connect("toggled", self.on_opt_cut_toggled)
        col_print.pack_start(chk_cut, False, False, 0)
        self.chk_cut = chk_cut
        chk_fold = Gtk.CheckButton(label=T["opt_fold"])
        chk_fold.set_active(self.opt_show_fold)
        chk_fold.set_tooltip_text(T["tt_opt_fold"])
        chk_fold.connect("toggled", self.on_opt_fold_toggled)
        col_print.pack_start(chk_fold, False, False, 0)
        self.chk_fold = chk_fold

        # --- Colonna 2: Interfaccia ---
        _col_header(col_ui, T["opt_sec_ui"])
        chk_tips = Gtk.CheckButton(label=T["opt_tooltips"])
        chk_tips.set_active(self.show_tooltips)
        chk_tips.set_tooltip_text(T["tt_tooltips"])
        chk_tips.connect("toggled", self.on_opt_tooltips_toggled)
        col_ui.pack_start(chk_tips, False, False, 0)
        self.opt_tips_note = Gtk.Label(label="", xalign=0.0)
        self.opt_tips_note.set_sensitive(False)
        self.opt_tips_note.set_line_wrap(True)
        self.opt_tips_note.set_max_width_chars(28)
        col_ui.pack_start(self.opt_tips_note, False, False, 0)

        # --- Colonna 3: Lingua ---
        _col_header(col_lang, T["opt_sec_lang"])
        langrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        langrow.pack_start(Gtk.Label(label=T["opt_lang_label"], xalign=0.0),
                           False, False, 0)
        self.opt_lang_combo = Gtk.ComboBoxText()
        self.opt_lang_combo.set_tooltip_text(T["tt_lang"])
        self._lang_codes = []
        cur = self.settings.get("language", "it")
        active_idx = 0
        for i, (code, nm) in enumerate(available_languages()):
            self.opt_lang_combo.append_text(nm)
            self._lang_codes.append(code)
            if code == cur:
                active_idx = i
        self.opt_lang_combo.set_active(active_idx)
        self.opt_lang_combo.connect("changed", self.on_lang_changed)
        langrow.pack_start(self.opt_lang_combo, False, False, 0)
        col_lang.pack_start(langrow, False, False, 0)
        self.opt_lang_note = Gtk.Label(label="", xalign=0.0)
        self.opt_lang_note.set_sensitive(False)
        self.opt_lang_note.set_line_wrap(True)
        self.opt_lang_note.set_max_width_chars(28)
        col_lang.pack_start(self.opt_lang_note, False, False, 0)
        lang_custom = Gtk.Label(label=T["opt_lang_custom"], xalign=0.0)
        lang_custom.set_sensitive(False)
        lang_custom.set_line_wrap(True)
        lang_custom.set_max_width_chars(28)
        col_lang.pack_start(lang_custom, False, False, 0)

        # --- Taratura stampante (dischi) : due colonne ---
        _section(T["opt_sec_calib"])

        def _off_spin(key):
            adj = Gtk.Adjustment(value=float(self.settings.get(key, 0.0)),
                                 lower=-5, upper=5,
                                 step_increment=0.5, page_increment=2.5)
            sb = Gtk.SpinButton()
            sb.set_adjustment(adj)
            sb.set_digits(1)
            sb.set_width_chars(6)
            sb.connect("value-changed", self.on_label_param_changed, key)
            return sb

        calib_cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        cleft = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        cright = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        calib_cols.pack_start(cleft, False, False, 0)
        calib_cols.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),
                              False, False, 0)
        calib_cols.pack_start(cright, True, True, 0)
        box.pack_start(calib_cols, True, True, 0)

        # colonna sinistra: spiegazione, Offset X/Y, Stampa di prova
        hint = Gtk.Label(label=T["opt_offset_hint"], xalign=0.0)
        hint.set_line_wrap(True)
        hint.set_max_width_chars(34)
        cleft.pack_start(hint, False, False, 0)

        rx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.sp_offx = _off_spin("printer_offx")
        self.sp_offx.set_tooltip_text(T["tt_offx"])
        lx = Gtk.Label(label=T["lbl_offx"], xalign=0.0)
        lx.set_width_chars(9)
        rx.pack_start(self._attach_scrub(lx, -5, 5, 0.1,
                                         self.sp_offx.get_value,
                                         self.sp_offx.set_value),
                      False, False, 0)
        rx.pack_start(self.sp_offx, False, False, 0)
        cleft.pack_start(rx, False, False, 0)

        ry = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.sp_offy = _off_spin("printer_offy")
        self.sp_offy.set_tooltip_text(T["tt_offy"])
        ly = Gtk.Label(label=T["lbl_offy"], xalign=0.0)
        ly.set_width_chars(9)
        ry.pack_start(self._attach_scrub(ly, -5, 5, 0.1,
                                         self.sp_offy.get_value,
                                         self.sp_offy.set_value),
                      False, False, 0)
        ry.pack_start(self.sp_offy, False, False, 0)
        cleft.pack_start(ry, False, False, 0)

        btnrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_creset = Gtk.Button(label=T["opt_calib_reset"])
        btn_creset.set_tooltip_text(T["tt_calib_reset"])
        btn_creset.connect("clicked", self.on_calib_reset)
        btnrow.pack_start(btn_creset, False, False, 0)
        btn_test = Gtk.Button(label=T["opt_calib_testprint"])
        btn_test.set_tooltip_text(T["tt_calib_test"])
        btn_test.connect("clicked", self.on_calib_testprint)
        btnrow.pack_start(btn_test, False, False, 0)
        btnrow.set_halign(Gtk.Align.START)
        cleft.pack_start(btnrow, False, False, 6)

        # colonna destra: la vista di calibrazione (grande), segno trascinabile
        self._calib_drag = False
        self.calib_area = Gtk.DrawingArea()
        self.calib_area.set_size_request(340, 340)
        self.calib_area.connect("draw", self._calib_draw)
        cright.pack_start(self.calib_area, True, True, 0)

        # --- Ripristino ---
        _section(T["opt_sec_reset"])
        btn_reset = Gtk.Button(label=T["opt_reset"])
        btn_reset.get_style_context().add_class("destructive-action")
        btn_reset.set_tooltip_text(T["tt_factory_reset"])
        btn_reset.connect("clicked", self.on_factory_reset)
        box.pack_start(btn_reset, False, False, 0)

        btn_close = Gtk.Button(label=T["close"])
        btn_close.set_tooltip_text(T["tt_close"])
        btn_close.connect("clicked", lambda b: win.close())
        box.pack_start(btn_close, False, False, 6)

        win.connect("destroy", self.on_options_destroyed)
        self._present_child(win)

    def on_options_destroyed(self, win):
        self.win_options = None
        self.opt_tips_note = None
        self.chk_cut = None
        self.chk_fold = None
        self.sp_offx = None
        self.sp_offy = None
        self.calib_area = None

    # ------------------------------------------------------------ GUIDA ("?")
    def on_help_clicked(self, button):
        # Se gia' aperta, la porto in primo piano
        if self.win_help is not None:
            self.win_help.present()
            return

        win = Gtk.Window(title=T["help_title"])
        win.set_border_width(14)
        self.win_help = win

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        win.add(box)

        # --- Parte alta: elenco sezioni a sinistra, testo a destra ---
        # Le sezioni: (chiave titolo, chiave testo).
        sections = [
            ("help_sec_cover", "help_body_cover"),
            ("help_sec_disc",  "help_body_disc"),
            ("help_sec_sheet", "help_body_sheet"),
            ("help_sec_print", "help_body_print"),
            ("help_sec_lang",  "help_body_lang"),
        ]

        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cols.set_size_request(-1, 320)
        box.pack_start(cols, True, True, 0)

        # Elenco delle voci (sinistra)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for tkey, _ in sections:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=T[tkey], xalign=0.0)
            lbl.set_margin_top(6)
            lbl.set_margin_bottom(6)
            lbl.set_margin_start(8)
            lbl.set_margin_end(8)
            row.add(lbl)
            listbox.add(row)
        lb_frame = Gtk.Frame()
        lb_frame.add(listbox)
        lb_frame.set_size_request(170, -1)
        cols.pack_start(lb_frame, False, False, 0)

        # Testo della sezione (destra), scorrevole
        self.help_text = Gtk.Label(xalign=0.0, yalign=0.0)
        self.help_text.set_line_wrap(True)
        self.help_text.set_line_wrap_mode(Pango.WrapMode.WORD)
        self.help_text.set_selectable(True)
        self.help_text.set_margin_top(4)
        self.help_text.set_margin_bottom(4)
        self.help_text.set_margin_start(6)
        self.help_text.set_margin_end(6)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.help_text)
        sc_frame = Gtk.Frame()
        sc_frame.add(scroll)
        cols.pack_start(sc_frame, True, True, 0)

        self._help_sections = sections

        def on_row_selected(lb, row):
            if row is None:
                return
            idx = row.get_index()
            if 0 <= idx < len(self._help_sections):
                self.help_text.set_text(T[self._help_sections[idx][1]])

        listbox.connect("row-selected", on_row_selected)
        listbox.select_row(listbox.get_row_at_index(0))   # prima voce attiva

        # --- Riquadro Informazioni (in fondo) ---
        box.pack_start(Gtk.Separator(), False, False, 4)
        info_title = Gtk.Label(xalign=0.0)
        info_title.set_markup("<b>%s</b>" % T["help_about_title"])
        box.pack_start(info_title, False, False, 0)

        app_line = Gtk.Label(xalign=0.0)
        app_line.set_markup("<b>%s</b>" % (T["help_app_line"] % T["help_version"]))
        box.pack_start(app_line, False, False, 0)

        desc = Gtk.Label(label=T["help_about_desc"], xalign=0.0)
        desc.set_line_wrap(True)
        box.pack_start(desc, False, False, 0)

        lic = Gtk.Label(label=T["help_license"], xalign=0.0)
        box.pack_start(lic, False, False, 0)

        hint = Gtk.Label(label=T["help_donate_hint"], xalign=0.0)
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 4)

        donate_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_donate = Gtk.Button(label=T["help_donate"])
        btn_donate.set_tooltip_text(T["tt_donate"])
        btn_donate.connect("clicked", self.on_donate_clicked)
        donate_row.pack_start(btn_donate, False, False, 0)
        box.pack_start(donate_row, False, False, 0)

        # --- Chiudi ---
        box.pack_start(Gtk.Separator(), False, False, 4)
        btn_close = Gtk.Button(label=T["close"])
        btn_close.set_tooltip_text(T["tt_close"])
        btn_close.connect("clicked", lambda b: win.close())
        box.pack_start(btn_close, False, False, 0)

        win.connect("destroy", self.on_help_destroyed)
        self._present_child(win)

    def on_donate_clicked(self, button):
        # Apre il link della donazione nel browser predefinito.
        try:
            Gtk.show_uri_on_window(self.win_help or self, PAYPAL_URL,
                                   Gdk.CURRENT_TIME)
        except Exception:
            try:
                import webbrowser
                webbrowser.open(PAYPAL_URL)
            except Exception:
                pass

    def on_help_destroyed(self, win):
        self.win_help = None
        self.help_text = None
        self._help_sections = None

    def on_opt_cut_toggled(self, chk):
        self.opt_show_cut = chk.get_active()
        self.settings["show_cut"] = self.opt_show_cut
        save_settings(self.settings)

    def on_opt_fold_toggled(self, chk):
        self.opt_show_fold = chk.get_active()
        self.settings["show_fold"] = self.opt_show_fold
        save_settings(self.settings)

    def on_opt_tooltips_toggled(self, chk):
        # I tooltip si applicano al riavvio (come la lingua).
        self.show_tooltips = chk.get_active()
        self.settings["show_tooltips"] = self.show_tooltips
        save_settings(self.settings)
        if getattr(self, "opt_tips_note", None) is not None:
            self.opt_tips_note.set_text(T["tooltips_restart_note"])

    def on_lang_changed(self, combo):
        idx = combo.get_active()
        if idx < 0 or idx >= len(self._lang_codes):
            return
        code = self._lang_codes[idx]
        if code == self.settings.get("language", "it"):
            return
        self.settings["language"] = code
        save_settings(self.settings)
        # la lingua si applica al riavvio: lo segnalo sotto il selettore
        if getattr(self, "opt_lang_note", None) is not None:
            self.opt_lang_note.set_text(T["lang_restart_note"])

    def on_factory_reset(self, button):
        # Conferma esplicita: l'operazione e' distruttiva e non annullabile.
        parent = self.win_options if self.win_options is not None else self
        dlg = Gtk.MessageDialog(transient_for=parent, modal=True,
                                message_type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text=T["reset_title"])
        dlg.format_secondary_text(T["reset_msg"])
        resp = dlg.run()
        dlg.destroy()
        if resp != Gtk.ResponseType.OK:
            return

        # 1) cancella i file di formati e impostazioni di stampa (incluso il
        #    vecchio print_settings.ini se ancora presente).
        for path in (FORMATS_FILE, PRINT_SETTINGS_COVER, PRINT_SETTINGS_LABEL,
                     PRINT_SETTINGS_SHEET, PAGE_SETUP_LABEL, HIDDEN_BASES_FILE,
                     os.path.join(CONFIG_DIR, "print_settings.ini")):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        # 2) ripulisci da settings.json solo le voci di stampa/etichetta;
        #    finestra e ultima cartella restano.
        for key in ("label_outer", "label_hole", "label_offx", "label_offy",
                    "printer_offx", "printer_offy", "show_cut", "show_fold"):
            self.settings.pop(key, None)
        save_settings(self.settings)

        # 3) riporta lo stato in memoria ai valori di fabbrica
        self.print_settings_cover = None
        self.print_settings_label = None
        self.print_settings_sheet = None
        self.page_setup_label = None
        self._captured_label_page_setup = None
        self.opt_show_cut = True
        self.opt_show_fold = True

        # 4) azzera gli offset stampante (gli spinner sono in Opzioni: ci sono
        #    solo se quel dialog e' aperto, com'e' quando premi Ripristina)
        for sb in (getattr(self, "sp_offx", None), getattr(self, "sp_offy", None)):
            if sb is not None:
                sb.handler_block_by_func(self.on_label_param_changed)
                sb.set_value(0.0)
                sb.handler_unblock_by_func(self.on_label_param_changed)

        # 5) riallinea i checkbox Opzioni (se la finestra e' aperta)
        if getattr(self, "chk_cut", None) is not None:
            self.chk_cut.handler_block_by_func(self.on_opt_cut_toggled)
            self.chk_cut.set_active(True)
            self.chk_cut.handler_unblock_by_func(self.on_opt_cut_toggled)
        if getattr(self, "chk_fold", None) is not None:
            self.chk_fold.handler_block_by_func(self.on_opt_fold_toggled)
            self.chk_fold.set_active(True)
            self.chk_fold.handler_unblock_by_func(self.on_opt_fold_toggled)

        # 6) ricarica formati e ridisegna tutto, senza riavviare il programma
        self.refresh_formats()
        self._update_label_bar()
        self.preview.queue_draw()

        self._info(T["reset_done_title"], T["reset_done"])

    # ------------------------------------------------------------ FORMATI
    def refresh_formats(self, keep=None):
        """Ricarica i formati (base + personalizzati) e ricostruisce il menu."""
        self.formats = all_formats()
        self.format_names = list(self.formats.keys())
        self.combo.handler_block_by_func(self.on_format_changed)
        self.combo.remove_all()
        for nm in self.format_names:
            self.combo.append_text(display_name(nm, self.formats[nm]))
        target = keep if (keep in self.format_names) else self.current_format
        if target not in self.format_names:
            target = self.format_names[0]
        self.combo.set_active(self.format_names.index(target))
        self.combo.handler_unblock_by_func(self.on_format_changed)
        self.current_format = target
        self._update_label_bar()
        self.update_status()
        self.preview.queue_draw()

    # ------------------------------------------------------------ EDITOR
    def on_editor_clicked(self, button):
        if getattr(self, "win_editor", None) is not None:
            self.win_editor.present()
            return

        win = Gtk.Window(title=T["editor_title"])
        win.set_border_width(12)
        self.win_editor = win

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        win.add(root)

        # elenco formati personalizzati + Nuovo / Elimina
        rowtop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        rowtop.pack_start(Gtk.Label(label=T["ed_your_formats"]), False, False, 0)
        self.ed_list = Gtk.ComboBoxText()
        self.ed_list.set_tooltip_text(T["tt_ed_list"])
        self.ed_list.connect("changed", self.on_ed_select)
        rowtop.pack_start(self.ed_list, True, True, 0)
        btn_new = Gtk.Button(label=T["ed_new"])
        btn_new.set_tooltip_text(T["tt_ed_new"])
        btn_new.connect("clicked", self.on_ed_new)
        rowtop.pack_start(btn_new, False, False, 0)
        self.ed_btn_del = Gtk.Button(label=T["ed_delete"])
        self.ed_btn_del.set_tooltip_text(T["tt_ed_delete"])
        self.ed_btn_del.connect("clicked", self.on_ed_delete)
        rowtop.pack_start(self.ed_btn_del, False, False, 0)
        self.ed_btn_restore = Gtk.Button(label=T["ed_restore_presets"])
        self.ed_btn_restore.set_tooltip_text(T["ed_restore_presets_tip"])
        self.ed_btn_restore.connect("clicked", self.on_ed_restore_presets)
        self.ed_btn_restore.set_no_show_all(True)   # compare solo se serve
        rowtop.pack_start(self.ed_btn_restore, False, False, 0)
        root.pack_start(rowtop, False, False, 0)
        root.pack_start(Gtk.Separator(), False, False, 2)

        # Nome
        r1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r1.pack_start(Gtk.Label(label=T["ed_name"]), False, False, 0)
        self.ed_name = Gtk.Entry()
        self.ed_name.set_tooltip_text(T["tt_ed_name"])
        self.ed_name.connect("changed", self._ed_on_change)
        r1.pack_start(self.ed_name, True, True, 0)
        root.pack_start(r1, False, False, 0)

        # ---------- Form a DUE COLONNE ----------
        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        cols.set_margin_top(4)
        cols.set_margin_bottom(4)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cols.pack_start(left, False, False, 0)
        self.ed_form_sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        cols.pack_start(self.ed_form_sep, False, False, 0)
        cols.pack_start(right, True, True, 0)
        self.ed_form_right = right
        self.ed_cols = cols
        # ed_mid: form a sinistra, anteprima a destra (usata dal foglio)
        self.ed_mid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self.ed_mid.pack_start(cols, True, True, 0)
        self.ed_preview_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ed_mid.pack_start(self.ed_preview_right, True, True, 0)
        root.pack_start(self.ed_mid, False, False, 0)
        # ed_preview_bottom: anteprima sotto (usata da cover/disco)
        self.ed_preview_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(self.ed_preview_bottom, True, True, 0)

        def _field_row(label_text, widget, expand=False, scrub=None):
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=label_text, xalign=0.0)
            lbl.set_width_chars(15)                  # etichette allineate
            if scrub is not None:
                lo, hi, step, getter, setter = scrub
                head = self._attach_scrub(lbl, lo, hi, step, getter, setter)
            else:
                head = lbl
            r.pack_start(head, False, False, 0)
            r.pack_start(widget, expand, expand, 0)
            return r

        # Tipo (sempre visibile, in cima alla colonna sinistra)
        self.ed_type = Gtk.ComboBoxText()
        self.ed_type.append_text(T["ed_type_cover"])
        self.ed_type.append_text(T["ed_type_disc"])
        self.ed_type.append_text(T["ed_type_sheet"])
        self.ed_type.set_active(0)
        self.ed_type.set_tooltip_text(T["tt_ed_type"])
        self.ed_type.connect("changed", self._ed_on_type_changed)
        left.pack_start(_field_row(T["ed_type"], self.ed_type), False, False, 0)

        # Colonna sinistra, campi COVER: Unita' / Altezza / Larghezza
        self.ed_unit = Gtk.ComboBoxText()
        self.ed_unit.append_text("mm")
        self.ed_unit.append_text("px")
        self.ed_unit.set_active(0)
        self.ed_unit.set_tooltip_text(T["tt_ed_unit"])
        self.ed_unit.connect("changed", self._ed_on_change)
        self.ed_height = Gtk.Entry()
        self.ed_height.set_width_chars(10)
        self.ed_height.set_tooltip_text(T["tt_ed_height"])
        self.ed_height.connect("changed", self._ed_on_change)
        self.ed_totalw = Gtk.Entry()
        self.ed_totalw.set_width_chars(10)
        self.ed_totalw.set_tooltip_text(T["tt_ed_totalw"])
        self.ed_totalw.connect("changed", self._ed_on_change)
        left_cover = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_cover.pack_start(_field_row(T["ed_unit"], self.ed_unit), False, False, 0)
        left_cover.pack_start(_field_row(
            T["ed_height"], self.ed_height, scrub=(
                1, 100000, 1.0,
                lambda: self._parse(self.ed_height) or 0.0,
                lambda v: self.ed_height.set_text(self._num(v)))),
            False, False, 0)
        left_cover.pack_start(_field_row(
            T["ed_totalw"], self.ed_totalw, scrub=(
                1, 100000, 1.0,
                lambda: self._parse(self.ed_totalw) or 0.0,
                lambda v: self.ed_totalw.set_text(self._num(v)))),
            False, False, 0)
        left.pack_start(left_cover, False, False, 0)

        # Colonna destra, blocco SEZIONI (cover)
        right_cover = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        r3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r3.pack_start(Gtk.Label(label=T["ed_count"]), False, False, 0)
        self.ed_count = Gtk.ComboBoxText()
        for k in ("1", "2", "3"):
            self.ed_count.append_text(k)
        self.ed_count.set_active(0)
        self.ed_count.set_tooltip_text(T["tt_ed_count"])
        self.ed_count.connect("changed", self.on_ed_count_changed)
        r3.pack_start(self.ed_count, False, False, 0)
        r3.pack_start(Gtk.Label(label="   " + T["ed_spine"]), False, False, 0)
        self.ed_spine = Gtk.ComboBoxText()
        self.ed_spine.set_tooltip_text(T["tt_ed_spine"])
        self.ed_spine.connect("changed", self._ed_on_change)
        r3.pack_start(self.ed_spine, False, False, 0)
        right_cover.pack_start(r3, False, False, 0)
        self.ed_sec_label = Gtk.Label(label=T["ed_sections"], xalign=0.0)
        right_cover.pack_start(self.ed_sec_label, False, False, 0)
        # intestazione colonne: chiarisce cosa va scritto dove
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hsp = Gtk.Label(label="")
        hsp.set_width_chars(10)
        hdr.pack_start(hsp, False, False, 0)
        h_name = Gtk.Label(label=T["ed_hdr_name"], xalign=0.0)
        hdr.pack_start(h_name, True, True, 0)
        h_w = Gtk.Label(label=T["ed_hdr_width"], xalign=0.0)
        h_w.set_width_chars(8)
        hdr.pack_start(h_w, False, False, 0)
        right_cover.pack_start(hdr, False, False, 0)
        self.ed_sections_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right_cover.pack_start(self.ed_sections_box, False, False, 0)
        self.ed_rows = []
        right.pack_start(right_cover, True, True, 0)

        # Colonna destra, campi DISCO (esterno/foro)
        self.ed_disc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.ed_outer = Gtk.Entry()
        self.ed_outer.set_width_chars(10)
        self.ed_outer.set_tooltip_text(T["tt_ed_outer"])
        self.ed_outer.connect("changed", self._ed_on_disc_change)
        self.ed_hole = Gtk.Entry()
        self.ed_hole.set_width_chars(10)
        self.ed_hole.set_tooltip_text(T["tt_ed_hole"])
        self.ed_hole.connect("changed", self._ed_on_disc_change)
        self.ed_disc_box.pack_start(_field_row(
            T["ed_outer"], self.ed_outer, scrub=(
                DISC_OUTER_MIN, DISC_OUTER_MAX, 0.5,
                lambda: self._parse(self.ed_outer) or 0.0,
                lambda v: self.ed_outer.set_text(self._num(v)))),
            False, False, 0)
        self.ed_disc_box.pack_start(_field_row(
            T["ed_hole"], self.ed_hole, scrub=(
                DISC_HOLE_MIN, DISC_HOLE_MAX, 0.5,
                lambda: self._parse(self.ed_hole) or 0.0,
                lambda v: self.ed_hole.set_text(self._num(v)))),
            False, False, 0)
        right.pack_start(self.ed_disc_box, False, False, 0)

        # Colonna destra, campi LABEL ADESIVA (foglio + n etichette + esterno/foro)
        self.ed_sheet_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.ed_page = Gtk.ComboBoxText()
        for _nm, _w, _h in PAGE_PRESETS:
            self.ed_page.append_text(_nm)
        self.ed_page.set_active(0)
        self.ed_page.set_tooltip_text(T["tt_ed_page"])
        self.ed_page.connect("changed", self._ed_sheet_relayout)
        self.ed_count_sheet = Gtk.ComboBoxText()
        self.ed_count_sheet.append_text("1")
        self.ed_count_sheet.append_text("2")
        self.ed_count_sheet.set_active(0)
        self.ed_count_sheet.set_tooltip_text(T["tt_ed_sheet_count"])
        self.ed_count_sheet.connect("changed", self._ed_sheet_relayout)
        self.ed_s_outer = Gtk.Entry()
        self.ed_s_outer.set_width_chars(10)
        self.ed_s_outer.set_tooltip_text(T["tt_ed_outer"])
        self.ed_s_outer.connect("changed", self._ed_on_sheet_change)
        self.ed_s_hole = Gtk.Entry()
        self.ed_s_hole.set_width_chars(10)
        self.ed_s_hole.set_tooltip_text(T["tt_ed_hole"])
        self.ed_s_hole.connect("changed", self._ed_on_sheet_change)
        self.ed_sheet_box.pack_start(_field_row(T["ed_page"], self.ed_page), False, False, 0)
        self.ed_page_w = Gtk.Entry()
        self.ed_page_w.set_width_chars(10)
        self.ed_page_w.set_tooltip_text(T["tt_ed_page_w"])
        self.ed_page_w.connect("changed", self._ed_sheet_relayout)
        self.ed_page_h = Gtk.Entry()
        self.ed_page_h.set_width_chars(10)
        self.ed_page_h.set_tooltip_text(T["tt_ed_page_h"])
        self.ed_page_h.connect("changed", self._ed_sheet_relayout)
        self.ed_page_custom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.ed_page_custom_box.pack_start(_field_row(
            T["ed_page_w"], self.ed_page_w, scrub=(
                10, 2000, 1.0,
                lambda: self._parse(self.ed_page_w) or 0.0,
                lambda v: self.ed_page_w.set_text(self._num(v)))), False, False, 0)
        self.ed_page_custom_box.pack_start(_field_row(
            T["ed_page_h"], self.ed_page_h, scrub=(
                10, 2000, 1.0,
                lambda: self._parse(self.ed_page_h) or 0.0,
                lambda v: self.ed_page_h.set_text(self._num(v)))), False, False, 0)
        self.ed_sheet_box.pack_start(self.ed_page_custom_box, False, False, 0)
        self.ed_sheet_box.pack_start(_field_row(T["ed_sheet_count"], self.ed_count_sheet), False, False, 0)
        self.ed_sheet_box.pack_start(_field_row(
            T["ed_outer"], self.ed_s_outer, scrub=(
                DISC_OUTER_MIN, DISC_OUTER_MAX, 0.5,
                lambda: self._parse(self.ed_s_outer) or 0.0,
                lambda v: self.ed_s_outer.set_text(self._num(v)))),
            False, False, 0)
        self.ed_sheet_box.pack_start(_field_row(
            T["ed_hole"], self.ed_s_hole, scrub=(
                DISC_HOLE_MIN, DISC_HOLE_MAX, 0.5,
                lambda: self._parse(self.ed_s_hole) or 0.0,
                lambda v: self.ed_s_hole.set_text(self._num(v)))),
            False, False, 0)
        self.ed_pos_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.ed_sheet_box.pack_start(self.ed_pos_box, True, True, 0)
        left.pack_start(self.ed_sheet_box, True, True, 0)

        # Stato (Somma cover / Misure disco): sempre visibile, in fondo a destra
        self.ed_sumlabel = Gtk.Label(xalign=0.0)
        right.pack_start(self.ed_sumlabel, False, False, 0)

        # Gruppi da mostrare/nascondere in base al tipo
        self.ed_cover_widgets = [left_cover, right_cover]

        # Anteprima
        self.ed_preview = Gtk.DrawingArea()
        self.ed_preview.connect("draw", self.on_ed_draw)
        frame = Gtk.Frame()
        frame.add(self.ed_preview)
        self.ed_preview_frame = frame
        self.ed_preview_bottom.pack_start(frame, True, True, 0)

        # Salva / Chiudi (con barra di stato a sinistra)
        rb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.ed_sheet_status = Gtk.Label(xalign=0.0)
        self.ed_sheet_status.set_ellipsize(Pango.EllipsizeMode.END)
        rb.pack_start(self.ed_sheet_status, True, True, 6)
        self.ed_btn_save = Gtk.Button(label=T["ed_save"])
        self.ed_btn_save.get_style_context().add_class("suggested-action")
        self.ed_btn_save.set_sensitive(False)   # si abilita solo se il formato e' valido
        self.ed_btn_save.set_tooltip_text(T["tt_ed_save"])
        self.ed_btn_save.connect("clicked", self.on_ed_save)
        rb.pack_end(self.ed_btn_save, False, False, 0)
        btn_close = Gtk.Button(label=T["close"])
        btn_close.set_tooltip_text(T["tt_close"])
        btn_close.connect("clicked", lambda b: win.close())
        rb.pack_end(btn_close, False, False, 0)
        self.ed_btn_test = Gtk.Button(label=T["ed_testprint"])
        self.ed_btn_test.set_tooltip_text(T["ed_testprint_tip"])
        self.ed_btn_test.set_sensitive(False)   # solo se il formato e' valido
        self.ed_btn_test.connect("clicked", self.on_ed_test_print)
        rb.pack_end(self.ed_btn_test, False, False, 0)
        root.pack_start(rb, False, False, 0)

        win.connect("destroy", self.on_editor_destroyed)
        self._ed_reload_list()
        self.on_ed_new(None)
        self._present_child(win)
        self._ed_set_visibility()   # applica la visibilita' del tipo dopo show_all

    def on_editor_destroyed(self, win):
        self.win_editor = None

    # --- helper numerici ---
    def _ed_unit(self):
        return "px" if self.ed_unit.get_active() == 1 else "mm"

    def _ed_is_px(self):
        return self._ed_unit() == "px"

    def _parse(self, entry):
        try:
            return float(entry.get_text().replace(",", "."))
        except Exception:
            return None

    def _num(self, v):
        try:
            fv = float(v)
            if abs(fv - round(fv)) < 1e-9:
                return str(int(round(fv)))
            return ("%.2f" % fv).rstrip("0").rstrip(".")
        except Exception:
            return str(v)

    def _ed_distribute(self, total, n):
        if n <= 0 or total <= 0:
            return [0] * max(n, 0)
        if self._ed_is_px():
            base = int(total // n)
            parts = [base] * n
            parts[-1] += int(round(total)) - base * n
            return parts
        base = round(total / n, 1)
        parts = [base] * n
        parts[-1] = round(total - base * (n - 1), 1)
        return parts

    # --- righe sezione ---
    def _attach_scrub(self, label, lo, hi, step_per_px, get_value, set_value):
        """Rende l'etichetta uno 'scrubber' stile Photoshop: tieni premuto e
        trascina in orizzontale per aumentare/diminuire il valore (si ferma ai
        limiti). lo/hi possono essere numeri oppure funzioni (limiti dinamici)."""
        ev = Gtk.EventBox()
        ev.add(label)
        ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                      | Gdk.EventMask.BUTTON_RELEASE_MASK
                      | Gdk.EventMask.BUTTON1_MOTION_MASK
                      | Gdk.EventMask.ENTER_NOTIFY_MASK
                      | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        ev.set_tooltip_text(T["scrub_tip"])
        st = {"on": False, "x0": 0.0, "v0": 0.0}

        def _cursor(w, name):
            win = w.get_window()
            if win is not None:
                try:
                    win.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), name))
                except Exception:
                    pass

        def press(w, e):
            if e.button == 1:
                st["on"] = True
                st["x0"] = e.x_root
                st["v0"] = get_value()
            return False

        def motion(w, e):
            if st["on"] and (e.state & Gdk.ModifierType.BUTTON1_MASK):
                lov = lo() if callable(lo) else lo
                hiv = hi() if callable(hi) else hi
                v = st["v0"] + (e.x_root - st["x0"]) * step_per_px
                v = max(lov, min(hiv, v))
                set_value(v)
            return False

        def release(w, e):
            st["on"] = False
            return False

        def enter(w, e):
            _cursor(w, "ew-resize")
            return False

        def leave(w, e):
            _cursor(w, "default")
            return False

        ev.connect("button-press-event", press)
        ev.connect("motion-notify-event", motion)
        ev.connect("button-release-event", release)
        ev.connect("enter-notify-event", enter)
        ev.connect("leave-notify-event", leave)
        return ev

    def _ed_sec_width_max(self, ew):
        """Massimo per la larghezza di una sezione: il totale meno le altre."""
        total = self._parse(self.ed_totalw) or 0
        if total <= 0:
            return 100000.0
        others = sum((self._parse(r[1]) or 0)
                     for r in self.ed_rows if r[1] is not ew)
        return max(0.0, float(total) - float(others))

    def _ed_make_row(self, name="", width=""):
        idx = len(self.ed_rows)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=T["ed_section"] + " %d" % (idx + 1), xalign=0.0)
        lbl.set_width_chars(10)
        e_name = Gtk.Entry()
        e_name.set_text(name)
        e_name.set_width_chars(14)
        e_name.set_tooltip_text(T["tt_ed_sec_name"])
        e_name.connect("changed", self._ed_on_names_changed)
        e_w = Gtk.Entry()
        e_w.set_text(str(width))
        e_w.set_width_chars(8)
        e_w.set_tooltip_text(T["tt_ed_sec_width"])
        e_w.connect("changed", self._ed_on_change)
        # l'etichetta "Sezione N" e' anche maniglia scrub per la sua larghezza
        head = self._attach_scrub(
            lbl, 0, lambda ew=e_w: self._ed_sec_width_max(ew), 1.0,
            lambda ew=e_w: self._parse(ew) or 0.0,
            lambda v, ew=e_w: ew.set_text(self._num(v)))
        row.pack_start(head, False, False, 0)
        row.pack_start(e_name, True, True, 0)
        row.pack_start(e_w, False, False, 0)
        self.ed_sections_box.pack_start(row, False, False, 0)
        self.ed_rows.append((e_name, e_w, row))

    def _ed_clear_rows(self):
        for _, _, row in self.ed_rows:
            self.ed_sections_box.remove(row)
        self.ed_rows = []

    def _ed_build_rows(self, n, names=None, widths=None):
        self._ed_clear_rows()
        defaults = {1: ["Sezione 1"], 2: ["Sinistra", "Destra"],
                    3: ["Retro", "Spina", "Fronte"]}.get(n, ["Sezione 1"])
        for i in range(n):
            nm = names[i] if (names and i < len(names)) else defaults[i]
            wv = self._num(widths[i]) if (widths and i < len(widths)) else ""
            self._ed_make_row(nm, wv)
        self.ed_sections_box.show_all()
        self._ed_refresh_spine()

    def on_ed_count_changed(self, combo):
        n = combo.get_active() + 1
        total = self._parse(self.ed_totalw) or 0
        widths = self._ed_distribute(total, n) if total > 0 else None
        self._ed_build_rows(n, widths=widths)
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_sync_single(self):
        # con 1 sola sezione, la sua larghezza = larghezza totale (automatico)
        if len(self.ed_rows) == 1:
            total = self._parse(self.ed_totalw)
            if total is not None:
                e_w = self.ed_rows[0][1]
                e_w.handler_block_by_func(self._ed_on_change)
                e_w.set_text(self._num(total))
                e_w.handler_unblock_by_func(self._ed_on_change)

    def _ed_on_names_changed(self, entry):
        self._ed_refresh_spine()
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_on_change(self, *a):
        self._ed_sync_single()
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_refresh_spine(self):
        prev = self.ed_spine.get_active()
        self.ed_spine.remove_all()
        self.ed_spine.append_text(T["ed_spine_none"])
        for i, (e_name, _, _) in enumerate(self.ed_rows):
            nm = e_name.get_text().strip() or (T["ed_section"] + " %d" % (i + 1))
            self.ed_spine.append_text(nm)
        maxidx = len(self.ed_rows)
        self.ed_spine.set_active(prev if 0 <= prev <= maxidx else 0)

    # --- validazione: somma sezioni == larghezza totale ---
    def _ed_sum(self):
        s = 0.0
        for _, e_w, _ in self.ed_rows:
            v = self._parse(e_w)
            if v is None:
                return None
            s += v
        return s

    def _ed_validate(self):
        if self._ed_current_type() == "sheet":
            outer = self._parse(self.ed_s_outer)
            hole = self._parse(self.ed_s_hole)
            if outer is None or hole is None:
                self.ed_sumlabel.set_markup(
                    "<span foreground='#e5484d'>%s</span>" % T["ed_need_disc"])
                ok = False
            else:
                ok, msg = validate_format("x", self._ed_collect(), [], None)
                if ok:
                    self.ed_sumlabel.set_markup(
                        "<span foreground='#2ea043'>%s  &#10004;</span>"
                        % T["ed_sheet_ok"])
                else:
                    self.ed_sumlabel.set_markup(
                        "<span foreground='#e5484d'>%s</span>" % msg)
            name_ok = bool(self.ed_name.get_text().strip())
            if hasattr(self, "ed_btn_save"):
                self.ed_btn_save.set_sensitive(ok and name_ok)
            if hasattr(self, "ed_btn_test"):
                self.ed_btn_test.set_sensitive(ok)
            return ok
        if self._ed_current_type() == "label":
            outer = self._parse(self.ed_outer)
            hole = self._parse(self.ed_hole)
            if outer is None or hole is None:
                ok = False
                self.ed_sumlabel.set_markup(
                    "<span foreground='#e5484d'>%s</span>" % T["ed_need_disc"])
            else:
                ok, msg = validate_format("x", self._ed_collect(), [], None)
                if ok:
                    self.ed_sumlabel.set_markup(
                        "<span foreground='#2ea043'>%s  &#10004;</span>" % T["ed_disc_ok"])
                else:
                    self.ed_sumlabel.set_markup(
                        "<span foreground='#e5484d'>%s</span>" % msg)
            name_ok = bool(self.ed_name.get_text().strip())
            if hasattr(self, "ed_btn_save"):
                self.ed_btn_save.set_sensitive(ok and name_ok)
            if hasattr(self, "ed_btn_test"):
                self.ed_btn_test.set_sensitive(ok)
            return ok
        total = self._parse(self.ed_totalw)
        ssum = self._ed_sum()
        unit = self._ed_unit()
        ok = False
        if total is None or total <= 0:
            self.ed_sumlabel.set_markup(
                "<span foreground='#e5484d'>%s</span>" % T["ed_need_total"])
        elif ssum is None:
            self.ed_sumlabel.set_markup(
                "<span foreground='#e5484d'>%s</span>" % T["ed_need_widths"])
        else:
            match = (round(ssum) == round(total)) if self._ed_is_px() \
                else (abs(ssum - total) <= 0.05)
            if match:
                ok = True
                self.ed_sumlabel.set_markup(
                    "<span foreground='#2ea043'>%s %s / %s %s  &#10004;</span>"
                    % (T["ed_sum"], self._num(ssum), self._num(total), unit))
            else:
                self.ed_sumlabel.set_markup(
                    "<span foreground='#e5484d'>%s %s / %s %s  (%s)</span>"
                    % (T["ed_sum"], self._num(ssum), self._num(total), unit,
                       T["ed_mismatch"]))
        name_ok = bool(self.ed_name.get_text().strip())
        if hasattr(self, "ed_btn_save"):
            self.ed_btn_save.set_sensitive(ok and name_ok)
        if hasattr(self, "ed_btn_test"):
            self.ed_btn_test.set_sensitive(ok)
        return ok

    # --- elenco personalizzati ---
    def _ed_current_type(self):
        return {0: "cover", 1: "label", 2: "sheet"}.get(
            self.ed_type.get_active(), "cover")

    def _ed_set_visibility(self):
        """Mostra i campi del tipo scelto (cover / disco / label adesiva)."""
        t = self._ed_current_type()
        for w in self.ed_cover_widgets:
            w.show() if t == "cover" else w.hide()
        self.ed_disc_box.show() if t == "label" else self.ed_disc_box.hide()
        self.ed_sheet_box.show() if t == "sheet" else self.ed_sheet_box.hide()
        self._ed_page_custom_sync()
        self._ed_layout_for_type()
        self._ed_sheet_update_status()

    def _ed_layout_for_type(self):
        """Foglio: anteprima a destra (sfrutta l'altezza A4). Cover/disco:
        anteprima sotto, come prima."""
        if not hasattr(self, "ed_preview_frame"):
            return
        sheet = (self._ed_current_type() == "sheet")
        frame = self.ed_preview_frame
        if hasattr(self, "ed_form_sep"):
            self.ed_form_sep.set_visible(not sheet)
        if hasattr(self, "ed_form_right"):
            self.ed_form_right.set_visible(not sheet)
        target = self.ed_preview_right if sheet else self.ed_preview_bottom
        cur = frame.get_parent()
        if cur is not target:
            if cur is not None:
                cur.remove(frame)
            target.pack_start(frame, True, True, 0)
        self.ed_preview_right.set_visible(sheet)
        self.ed_preview_bottom.set_visible(not sheet)
        self.ed_mid.set_child_packing(self.ed_cols, not sheet, not sheet, 0,
                                      Gtk.PackType.START)
        parent = self.ed_mid.get_parent()
        if parent is not None:
            parent.set_child_packing(self.ed_mid, sheet, sheet, 0,
                                     Gtk.PackType.START)
            parent.set_child_packing(self.ed_preview_bottom, not sheet, not sheet,
                                     0, Gtk.PackType.START)
        frame.show_all()

    def _ed_set_type(self, kind, enabled):
        """Imposta il tipo (senza scatenare ricorsioni) e se e' modificabile."""
        self.ed_type.handler_block_by_func(self._ed_on_type_changed)
        self.ed_type.set_active({"cover": 0, "label": 1, "sheet": 2}.get(kind, 0))
        self.ed_type.handler_unblock_by_func(self._ed_on_type_changed)
        self.ed_type.set_sensitive(enabled)
        self._ed_set_visibility()

    def _ed_on_type_changed(self, combo):
        if self._ed_current_type() == "label":
            if not self.ed_outer.get_text().strip():
                self.ed_outer.set_text(self._num(118.0))
            if not self.ed_hole.get_text().strip():
                self.ed_hole.set_text(self._num(22.0))
        if self._ed_current_type() == "sheet":
            if not self.ed_s_outer.get_text().strip():
                self.ed_s_outer.set_text(self._num(118.0))
            if not self.ed_s_hole.get_text().strip():
                self.ed_s_hole.set_text(self._num(22.0))
        self._ed_set_visibility()
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_on_sheet_change(self, *a):
        # cambia esterno/foro: tengo le posizioni ma le riporto dentro al foglio
        self._ed_sheet_clamp()
        self._ed_sheet_refresh_pos()
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_sheet_relayout(self, *a):
        # cambia foglio o numero etichette: posizioni automatiche
        self._ed_page_custom_sync()
        pw, ph = self._ed_page_dims()
        count = self.ed_count_sheet.get_active() + 1
        self.ed_sheet_labels = sheet_label_positions(pw, ph, count)
        self.ed_sheet_active = 0
        self._ed_sheet_build_pos_rows()
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_sheet_clamp(self):
        pw, ph = self._ed_page_dims()
        r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
        for lab in (getattr(self, "ed_sheet_labels", None) or []):
            lab["x_mm"] = max(r, min(pw - r, lab["x_mm"]))
            lab["y_mm"] = max(r, min(ph - r, lab["y_mm"]))

    def _ed_page_name(self):
        return self.ed_page.get_active_text() or "A4"

    def _ed_page_dims(self):
        if self._ed_page_name() == CUSTOM_PAGE_NAME:
            return (self._parse(self.ed_page_w) or 0.0,
                    self._parse(self.ed_page_h) or 0.0)
        return page_size_mm(self._ed_page_name())

    def _ed_page_custom_sync(self):
        if not hasattr(self, "ed_page_custom_box"):
            return
        if self._ed_page_name() == CUSTOM_PAGE_NAME:
            self.ed_page_custom_box.show_all()
        else:
            self.ed_page_custom_box.hide()

    def _ed_sheet_update_status(self):
        """Barra di stato dell'Editor: misure di tutte le etichette insieme."""
        if not hasattr(self, "ed_sheet_status"):
            return
        if self._ed_current_type() != "sheet":
            self.ed_sheet_status.set_text("")
            return
        pw, ph = self._ed_page_dims()
        r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
        labels = getattr(self, "ed_sheet_labels", []) or []
        n = len(labels)
        parts = []
        for i, lab in enumerate(labels):
            ref_h = "right" if (n == 2 and i == 1) else "left"
            ref_v = "bottom" if (n == 2 and i == 1) else "top"
            hval = (lab["x_mm"] - r) if ref_h == "left" else (pw - (lab["x_mm"] + r))
            vval = (lab["y_mm"] - r) if ref_v == "top" else (ph - (lab["y_mm"] + r))
            hname = T["m_left"] if ref_h == "left" else T["m_right"]
            vname = T["m_top"] if ref_v == "top" else T["m_bottom"]
            parts.append("%s %d:  %s %.1f mm · %s %.1f mm"
                         % (T["ed_label_word"], i + 1, hname, hval, vname, vval))
        self.ed_sheet_status.set_text("       ".join(parts))

    def _ed_sheet_metrics(self, area):
        pw, ph = self._ed_page_dims()
        alloc = area.get_allocation()
        W, H = alloc.width, alloc.height
        margin = 18
        scale = min((W - 2 * margin) / pw, (H - 2 * margin) / ph) if pw and ph else 0
        ox = (W - pw * scale) / 2.0
        oy = (H - ph * scale) / 2.0
        return pw, ph, scale, ox, oy

    def _ed_sheet_px_to_mm(self, area, px, py):
        pw, ph, scale, ox, oy = self._ed_sheet_metrics(area)
        if scale <= 0:
            return None
        return ((px - ox) / scale, (py - oy) / scale)

    def _ed_sheet_press(self, area, e):
        if self._ed_current_type() != "sheet" or e.button != 1:
            return False
        pt = self._ed_sheet_px_to_mm(area, e.x, e.y)
        if pt is None:
            return False
        mx, my = pt
        r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
        labels = getattr(self, "ed_sheet_labels", []) or []
        for i, lab in enumerate(labels):
            if (mx - lab["x_mm"]) ** 2 + (my - lab["y_mm"]) ** 2 <= r * r:
                self.ed_sheet_active = i
                self._ed_sheet_drag = True
                self._ed_sheet_grab = (lab["x_mm"] - mx, lab["y_mm"] - my)
                self.ed_preview.queue_draw()
                break
        return False

    def _ed_sheet_motion(self, area, e):
        if self._ed_current_type() != "sheet":
            return False
        if not getattr(self, "_ed_sheet_drag", False):
            return False
        if not (e.state & Gdk.ModifierType.BUTTON1_MASK):
            return False
        pt = self._ed_sheet_px_to_mm(area, e.x, e.y)
        if pt is None:
            return False
        mx, my = pt
        gx, gy = getattr(self, "_ed_sheet_grab", (0.0, 0.0))
        i = self.ed_sheet_active
        if 0 <= i < len(self.ed_sheet_labels):
            nx, ny = self._ed_sheet_place(i, mx + gx, my + gy)
            self.ed_sheet_labels[i]["x_mm"] = nx
            self.ed_sheet_labels[i]["y_mm"] = ny
            self.ed_preview.queue_draw()
            self._ed_sheet_refresh_pos()
        return False

    def _ed_sheet_place(self, i, x, y):
        """Posiziona l'etichetta i: dentro al foglio e senza sovrapporsi alle
        altre (si ferma al contatto)."""
        pw, ph = self._ed_page_dims()
        r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
        x = max(r, min(pw - r, x))
        y = max(r, min(ph - r, y))
        for j, lab in enumerate(getattr(self, "ed_sheet_labels", [])):
            if j == i:
                continue
            dx, dy = x - lab["x_mm"], y - lab["y_mm"]
            d = math.hypot(dx, dy)
            mind = 2 * r
            if d < mind:
                if d < 1e-6:
                    dx, dy, d = 0.0, -1.0, 1.0
                x = lab["x_mm"] + dx / d * mind
                y = lab["y_mm"] + dy / d * mind
                x = max(r, min(pw - r, x))
                y = max(r, min(ph - r, y))
        return x, y

    def _ed_sheet_locked(self):
        return (getattr(self, "ed_sheet_lock", True)
                and len(getattr(self, "ed_sheet_labels", [])) == 2)

    def _ed_apply_mirror(self, i, x, y):
        """Vincolo speculare rispetto al centro del foglio: x2 = larghezza - x1,
        y2 = altezza - y1 (1ª a destra -> 2ª a sinistra; 1ª in alto -> 2ª in
        basso). Impedisce la sovrapposizione tenendo la driver a >= r dal centro."""
        pw, ph = self._ed_page_dims()
        r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
        cx, cy = pw / 2.0, ph / 2.0
        x = max(r, min(pw - r, x))
        y = max(r, min(ph - r, y))
        # niente sovrapposizione: l'etichetta deve stare ad almeno r dal centro
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy)
        if d < r:
            if d < 1e-6:
                dx, dy, d = 0.0, -1.0, 1.0
            x = cx + dx / d * r
            y = cy + dy / d * r
            x = max(r, min(pw - r, x))
            y = max(r, min(ph - r, y))
        # se vicino ai bordi la spinta non basta, la posizione sovrapporrebbe:
        # rifiuto il movimento (l'etichetta resta dov'era)
        if math.hypot(x - cx, y - cy) < r - 0.05:
            return
        self.ed_sheet_labels[i]["x_mm"] = x
        self.ed_sheet_labels[i]["y_mm"] = y
        self.ed_sheet_labels[1 - i]["x_mm"] = pw - x
        self.ed_sheet_labels[1 - i]["y_mm"] = ph - y

    def _ed_sheet_lock_toggled(self, btn):
        self.ed_sheet_lock = btn.get_active()
        if self.ed_sheet_lock and len(getattr(self, "ed_sheet_labels", [])) == 2:
            a = self.ed_sheet_labels[0]
            self._ed_apply_mirror(0, a["x_mm"], a["y_mm"])
            self.ed_preview.queue_draw()
            self._ed_sheet_refresh_pos()

    def _ed_sheet_release(self, area, e):
        self._ed_sheet_drag = False
        return False

    def _ed_pos_hmax(self):
        pw, ph = self._ed_page_dims()
        return max(0.0, pw - (self._parse(self.ed_s_outer) or 0.0))

    def _ed_pos_vmax(self):
        pw, ph = self._ed_page_dims()
        return max(0.0, ph - (self._parse(self.ed_s_outer) or 0.0))

    def _ensure_label_frame_css(self):
        """Stile dei riquadri «Etichetta N»: bordo arrotondato che segue la
        catenella — continuo quando è chiusa, tratteggiato quando è aperta,
        con gli stessi colori/spessori delle linee."""
        if getattr(self, "_label_frame_css_done", False):
            return
        self._label_frame_css_done = True
        css = b"""
        frame.ed-label-frame > border {
            border-radius: 7px;
        }
        frame.ed-frame-locked > border {
            border: 2px solid rgba(158,158,158,0.95);
            border-radius: 7px;
        }
        frame.ed-frame-unlocked > border {
            border: 2px dashed rgba(158,158,158,0.40);
            border-radius: 7px;
        }
        """
        try:
            prov = Gtk.CssProvider()
            prov.load_from_data(css)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), prov,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception:
            pass

    def _apply_frame_lock_style(self):
        """Mette il bordo continuo (catena chiusa) o tratteggiato (catena
        aperta) sui riquadri delle etichette."""
        locked = getattr(self, "ed_sheet_lock", True)
        cls_on = "ed-frame-locked" if locked else "ed-frame-unlocked"
        cls_off = "ed-frame-unlocked" if locked else "ed-frame-locked"
        for fr in (getattr(self, "ed_frame1", None),
                   getattr(self, "ed_frame2", None)):
            if fr is None:
                continue
            sc = fr.get_style_context()
            sc.remove_class(cls_off)
            sc.add_class(cls_on)

    def _ed_sheet_build_pos_rows(self):
        """Riquadri di posizione: uno per etichetta. Con 2 etichette, a destra
        compare la catenella (blocco speculare) collegata da due linee curve."""
        if not hasattr(self, "ed_pos_box"):
            return
        for ch in self.ed_pos_box.get_children():
            self.ed_pos_box.remove(ch)
        self.ed_pos_spins = []
        self.ed_frame1 = None
        self.ed_frame2 = None
        self.ed_chain_canvas = None
        labels = getattr(self, "ed_sheet_labels", []) or []
        n = len(labels)

        # linea divisoria orizzontale sopra i riquadri
        self.ed_pos_box.pack_start(
            Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)

        def _spin():
            sb = Gtk.SpinButton()
            sb.set_adjustment(Gtk.Adjustment(value=0, lower=0, upper=9999,
                                             step_increment=0.5, page_increment=5))
            sb.set_digits(1)
            sb.set_width_chars(7)
            return sb

        def _make_frame(idx, ref_h, ref_v):
            self._ensure_label_frame_css()
            fr = Gtk.Frame(label=" %s %d " % (T["ed_label_word"], idx + 1))
            fr.set_shadow_type(Gtk.ShadowType.IN)
            fr.get_style_context().add_class("ed-label-frame")
            grid = Gtk.Grid()
            grid.set_row_spacing(6)
            grid.set_column_spacing(8)
            grid.set_margin_top(6)
            grid.set_margin_bottom(8)
            grid.set_margin_start(8)
            grid.set_margin_end(8)
            horiz_txt = T["ed_pos_left"] if ref_h == "left" else T["ed_pos_right"]
            lh = Gtk.Label(xalign=0.0)
            lh.set_markup("<span foreground=\"%s\">%s</span>"
                          % (SHEET_COL_LEFT_HEX, horiz_txt))
            sb_h = _spin()
            sb_h.set_tooltip_text(T["tt_pos_h"])
            vert_txt = T["ed_pos_top"] if ref_v == "top" else T["ed_pos_bottom"]
            lv = Gtk.Label(xalign=0.0)
            lv.set_markup("<span foreground=\"%s\">%s</span>"
                          % (SHEET_COL_VERT_HEX, vert_txt))
            sb_v = _spin()
            sb_v.set_tooltip_text(T["tt_pos_v"])
            grid.attach(self._attach_scrub(lh, 0, self._ed_pos_hmax, 0.5,
                                           sb_h.get_value, sb_h.set_value), 0, 0, 1, 1)
            grid.attach(sb_h, 1, 0, 1, 1)
            grid.attach(self._attach_scrub(lv, 0, self._ed_pos_vmax, 0.5,
                                           sb_v.get_value, sb_v.set_value), 0, 1, 1, 1)
            grid.attach(sb_v, 1, 1, 1, 1)
            fr.add(grid)
            sb_h.connect("value-changed", self._ed_pos_changed, idx)
            sb_v.connect("value-changed", self._ed_pos_changed, idx)
            self.ed_pos_spins.append((sb_h, sb_v, ref_h, ref_v))
            return fr

        if n == 1:
            self.ed_frame1 = _make_frame(0, "left", "top")
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            col.pack_start(Gtk.Box(), True, True, 0)         # spazio elastico SOPRA
            col.pack_start(self.ed_frame1, False, False, 0)
            col.pack_start(Gtk.Box(), True, True, 0)         # spazio elastico SOTTO
            area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            area.pack_start(col, True, True, 0)
            spacer = Gtk.Box()                               # riserva lo spazio
            spacer.set_size_request(96, -1)                  # della catenella
            area.pack_start(spacer, False, False, 0)
            self.ed_pos_box.pack_start(area, True, True, 0)
        elif n == 2:
            area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.ed_frame1 = _make_frame(0, "left", "top")
            self.ed_frame2 = _make_frame(1, "right", "bottom")
            gap = Gtk.Box()
            gap.set_size_request(-1, 10)                     # stacco fisso tra i due
            col.pack_start(Gtk.Box(), True, True, 0)         # spazio elastico SOPRA
            col.pack_start(self.ed_frame1, False, False, 0)
            col.pack_start(gap, False, False, 0)
            col.pack_start(self.ed_frame2, False, False, 0)
            col.pack_start(Gtk.Box(), True, True, 0)         # spazio elastico SOTTO
            area.pack_start(col, True, True, 0)
            self.ed_chain_canvas = Gtk.DrawingArea()
            self.ed_chain_canvas.set_size_request(96, -1)
            self.ed_chain_canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            self.ed_chain_canvas.set_tooltip_text(T["ed_mirror_tip"])
            self.ed_chain_canvas.connect("draw", self._chain_draw)
            self.ed_chain_canvas.connect("button-press-event", self._chain_clicked)
            area.pack_start(self.ed_chain_canvas, False, False, 0)
            # ridisegna le curve quando i riquadri vengono ridimensionati/spostati
            self.ed_frame1.connect("size-allocate",
                                   lambda *a: self.ed_chain_canvas.queue_draw())
            self.ed_frame2.connect("size-allocate",
                                   lambda *a: self.ed_chain_canvas.queue_draw())
            self.ed_pos_box.pack_start(area, True, True, 0)
        if n == 1:
            # con una sola etichetta non c'è catena: bordo continuo
            self.ed_frame1.get_style_context().add_class("ed-frame-locked")
        elif n == 2:
            self._apply_frame_lock_style()
        self.ed_pos_box.show_all()
        self._ed_sheet_refresh_pos()

    def _frame_center_y(self, frame, area):
        if frame is None:
            return None
        fa = frame.get_allocation()
        res = frame.translate_coordinates(area, 0, fa.height / 2.0)
        return None if res is None else res[1]

    def _chain_ellipse(self, cr, cx, cy, rx, ry):
        """Percorso di un anello schiacciato (ellisse) con tratto uniforme."""
        cr.save()
        cr.translate(cx, cy)
        cr.scale(rx, ry)
        cr.new_sub_path()
        cr.arc(0, 0, 1.0, 0, 2 * math.pi)
        cr.restore()

    def _chain_draw(self, area, cr):
        alloc = area.get_allocation()
        W, H = alloc.width, alloc.height
        y1 = self._frame_center_y(self.ed_frame1, area)
        y2 = self._frame_center_y(self.ed_frame2, area)
        if y1 is None:
            y1 = H * 0.25
        if y2 is None:
            y2 = H * 0.75
        locked = getattr(self, "ed_sheet_lock", True)
        L = 16.0            # quanto la linea va a destra prima di curvare
        r = 9.0             # raggio della curva dolce a 90°
        cx = L              # gli anelli stanno sulla verticale, a x = L
        cy = (y1 + y2) / 2.0
        rx, ry = 7.0, 11.0                       # anelli alti e stretti, tipo "0"
        sep = 8.0 if locked else 15.0            # uniti o separati
        reach = sep + ry - 1.0                   # dove la linea tocca gli anelli

        # linee: orizzontale dal riquadro -> curva 90° -> verticale al centro
        if locked:
            cr.set_source_rgb(0.62, 0.62, 0.62)
            cr.set_line_width(2.0)
        else:
            cr.set_source_rgba(0.62, 0.62, 0.62, 0.35)
            cr.set_line_width(1.5)
            cr.set_dash([4, 3])
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        # Etichetta 1 (in alto): esce a destra, curva verso il basso
        cr.move_to(0, y1)
        cr.line_to(L - r, y1)
        cr.arc(L - r, y1 + r, r, -math.pi / 2.0, 0)
        cr.line_to(L, cy - reach)
        cr.stroke()
        # Etichetta 2 (in basso): esce a destra, curva verso l'alto
        cr.move_to(0, y2)
        cr.line_to(L - r, y2)
        cr.arc_negative(L - r, y2 - r, r, math.pi / 2.0, 0)
        cr.line_to(L, cy + reach)
        cr.stroke()
        cr.set_dash([])

        # 2 anelli schiacciati, semplici: solo tratto, nessun bagliore/contorno
        col = (0.80, 0.83, 0.90) if locked else (0.55, 0.55, 0.55)
        cr.set_source_rgb(*col)
        cr.set_line_width(3.0)
        self._chain_ellipse(cr, cx, cy - sep, rx, ry)
        cr.stroke()
        self._chain_ellipse(cr, cx, cy + sep, rx, ry)
        cr.stroke()
        return False

    def _chain_clicked(self, area, event):
        if event.button == 1:
            self.ed_sheet_lock = not getattr(self, "ed_sheet_lock", True)
            if self.ed_sheet_lock and len(getattr(self, "ed_sheet_labels", [])) == 2:
                a = self.ed_sheet_labels[0]
                self._ed_apply_mirror(0, a["x_mm"], a["y_mm"])
                self._ed_sheet_refresh_pos()
            self._apply_frame_lock_style()
            area.queue_draw()
            self.ed_preview.queue_draw()
        return True

    def _ed_sheet_refresh_pos(self):
        """Aggiorna le caselle a partire dalle posizioni correnti (dopo un
        trascinamento o un clamp)."""
        if getattr(self, "_ed_pos_updating", False):
            return
        self._ed_pos_updating = True
        try:
            pw, ph = self._ed_page_dims()
            r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
            for i, (sb_h, sb_v, ref_h, ref_v) in enumerate(getattr(self, "ed_pos_spins", [])):
                if i >= len(self.ed_sheet_labels):
                    break
                lab = self.ed_sheet_labels[i]
                h = (lab["x_mm"] - r) if ref_h == "left" else (pw - (lab["x_mm"] + r))
                v = (lab["y_mm"] - r) if ref_v == "top" else (ph - (lab["y_mm"] + r))
                sb_h.set_value(round(h, 1))
                sb_v.set_value(round(v, 1))
        finally:
            self._ed_pos_updating = False
        self._ed_sheet_update_status()

    def _ed_pos_changed(self, spin, i):
        if getattr(self, "_ed_pos_updating", False):
            return
        if i >= len(getattr(self, "ed_sheet_labels", [])):
            return
        sb_h, sb_v, ref_h, ref_v = self.ed_pos_spins[i]
        pw, ph = self._ed_page_dims()
        r = (self._parse(self.ed_s_outer) or 0.0) / 2.0
        x = (sb_h.get_value() + r) if ref_h == "left" \
            else (pw - r - sb_h.get_value())
        y = (sb_v.get_value() + r) if ref_v == "top" \
            else (ph - r - sb_v.get_value())
        if self._ed_sheet_locked():
            self._ed_apply_mirror(i, x, y)
        else:
            x, y = self._ed_sheet_place(i, x, y)
            self.ed_sheet_labels[i]["x_mm"] = x
            self.ed_sheet_labels[i]["y_mm"] = y
        self.ed_sheet_active = i
        self.ed_preview.queue_draw()
        self._ed_sheet_refresh_pos()

    def _ed_on_disc_change(self, *a):
        self._ed_validate()
        self.ed_preview.queue_draw()

    def _ed_reload_list(self):
        # ed_user = cio' che l'utente ha salvato (suoi formati + override dei base)
        self.ed_user = load_custom_formats()
        # nell'elenco mostro i formati di tipo cover, base e personalizzati
        self.ed_all = {nm: f for nm, f in all_formats().items()
                       if f.get("kind") in ("cover", "label", "sheet")}
        self.ed_list_names = list(self.ed_all.keys())
        self.ed_list.handler_block_by_func(self.on_ed_select)
        self.ed_list.remove_all()
        for nm in self.ed_list_names:
            # stesso nome visualizzato della schermata principale (con la misura
            # della spina, es. "Cover DVD (14mm)").
            self.ed_list.append_text(display_name(nm, self.ed_all[nm]))
        self.ed_list.set_active(-1)
        self.ed_list.handler_unblock_by_func(self.on_ed_select)
        self.ed_selected = None
        self._ed_update_del_button(None)
        # il pulsante "Ripristina preimpostati" compare solo se manca davvero
        # qualche formato di fabbrica (nascosto/rinominato/eliminato)
        if hasattr(self, "ed_btn_restore"):
            self.ed_btn_restore.set_visible(bool(load_hidden_bases()))

    def on_ed_restore_presets(self, button):
        # rimette tutti i preimpostati di fabbrica nascosti, SENZA toccare i
        # formati personalizzati ne' le impostazioni dell'app.
        save_hidden_bases(set())
        self._ed_reload_list()
        self.refresh_formats(keep=self.current_format)
        self._info(T["ed_restore_presets_done_title"],
                   T["ed_restore_presets_done"])

    def _is_modified_base(self, nm):
        """True se 'nm' e' un base con una versione salvata DIVERSA dall'originale."""
        return (is_base(nm) and nm in getattr(self, "ed_user", {})
                and not formats_equal(self.ed_user[nm], factory_format(nm)))

    def _ed_update_del_button(self, name):
        """Il pulsante: 'Elimina' per i tuoi formati, 'Torna all'originale' per
        i base (attivo solo se hai una versione modificata da annullare)."""
        if not name:
            self.ed_btn_del.set_label(T["ed_delete"])
            self.ed_btn_del.set_sensitive(False)
        elif is_base(name):
            self.ed_btn_del.set_label(T["ed_revert"])
            self.ed_btn_del.set_sensitive(self._is_modified_base(name))
        else:
            self.ed_btn_del.set_label(T["ed_delete"])
            self.ed_btn_del.set_sensitive(True)

    def on_ed_new(self, button):
        self.ed_list.handler_block_by_func(self.on_ed_select)
        self.ed_list.set_active(-1)
        self.ed_list.handler_unblock_by_func(self.on_ed_select)
        self.ed_selected = None
        self._ed_update_del_button(None)
        self._ed_set_type("cover", enabled=True)   # nuovo: tipo scegliibile
        self.ed_name.set_text("")
        self.ed_unit.set_active(0)
        self.ed_height.set_text("")
        self.ed_totalw.set_text("")
        self.ed_outer.set_text(self._num(118.0))
        self.ed_hole.set_text(self._num(22.0))
        self.ed_s_outer.set_text(self._num(118.0))
        self.ed_s_hole.set_text(self._num(22.0))
        self.ed_page.set_active(0)
        self.ed_page_w.set_text(self._num(210.0))
        self.ed_page_h.set_text(self._num(297.0))
        self.ed_count_sheet.set_active(0)
        self.ed_sheet_labels = sheet_label_positions(*page_size_mm("A4"), 1)
        self.ed_sheet_active = 0
        self._ed_sheet_drag = False
        self.ed_sheet_lock = True
        self._ed_sheet_build_pos_rows()
        self.ed_count.handler_block_by_func(self.on_ed_count_changed)
        self.ed_count.set_active(0)
        self.ed_count.handler_unblock_by_func(self.on_ed_count_changed)
        self._ed_build_rows(1)
        self._ed_validate()
        self.ed_preview.queue_draw()

    def on_ed_select(self, combo):
        idx = combo.get_active()
        if idx < 0 or idx >= len(self.ed_list_names):
            return
        nm = self.ed_list_names[idx]
        f = self.ed_all.get(nm)
        if f is None:
            return
        self.ed_name.set_text(nm)
        if f.get("kind") == "sheet":
            self._ed_set_type("sheet", enabled=False)
            pname = f.get("page_name", "A4")
            names = [p[0] for p in PAGE_PRESETS]
            if pname == "A4":
                self.ed_page.set_active(names.index("A4"))
            else:
                # Personalizzato (o vecchi formati non piu' in elenco)
                self.ed_page.set_active(names.index(CUSTOM_PAGE_NAME))
                self.ed_page_w.set_text(self._num(f.get("page_w_mm", 210.0)))
                self.ed_page_h.set_text(self._num(f.get("page_h_mm", 297.0)))
            self.ed_count_sheet.set_active(0 if f.get("count", 2) <= 1 else 1)
            self.ed_s_outer.set_text(self._num(f.get("outer_mm", "")))
            self.ed_s_hole.set_text(self._num(f.get("hole_mm", "")))
            pw, ph = self._ed_page_dims()
            count = self.ed_count_sheet.get_active() + 1
            labs = f.get("labels")
            if labs and len(labs) == count:
                self.ed_sheet_labels = [{"x_mm": float(p["x_mm"]),
                                         "y_mm": float(p["y_mm"])} for p in labs]
            else:
                self.ed_sheet_labels = sheet_label_positions(pw, ph, count)
            self.ed_sheet_active = 0
            self.ed_sheet_lock = bool(f.get("mirror", True))
            self._ed_sheet_build_pos_rows()
            self._ed_page_custom_sync()
        elif f.get("kind") == "label":
            # tipo Disco: blocco il selettore e carico esterno/foro
            self._ed_set_type("label", enabled=False)
            self.ed_outer.set_text(self._num(f.get("outer_mm", "")))
            self.ed_hole.set_text(self._num(f.get("hole_mm", "")))
        else:
            # tipo Cover
            self._ed_set_type("cover", enabled=False)
            self.ed_unit.set_active(1 if f.get("unit") == "px" else 0)
            self.ed_height.set_text(self._num(f.get("height", "")))
            secs = f.get("sections", [])
            total = sum(s.get("width", 0) for s in secs)
            self.ed_totalw.set_text(self._num(total))
            n = max(1, min(3, len(secs)))
            self.ed_count.handler_block_by_func(self.on_ed_count_changed)
            self.ed_count.set_active(n - 1)
            self.ed_count.handler_unblock_by_func(self.on_ed_count_changed)
            self._ed_build_rows(n, names=[s.get("name", "") for s in secs],
                                widths=[s.get("width", "") for s in secs])
            sp = f.get("spine_section")
            self.ed_spine.set_active((sp + 1) if isinstance(sp, int) else 0)
        self.ed_selected = nm
        self._ed_update_del_button(nm)
        self._ed_validate()
        self.ed_preview.queue_draw()

    # --- raccolta + salvataggio ---
    def _ed_collect(self):
        if self._ed_current_type() == "sheet":
            pname = self._ed_page_name()
            pw, ph = self._ed_page_dims()
            outer = self._parse(self.ed_s_outer) or 0.0
            hole = self._parse(self.ed_s_hole) or 0.0
            count = self.ed_count_sheet.get_active() + 1
            labels = getattr(self, "ed_sheet_labels", None)
            if not labels or len(labels) != count:
                labels = sheet_label_positions(pw, ph, count)
            labels = [{"x_mm": float(p["x_mm"]), "y_mm": float(p["y_mm"])}
                      for p in labels]
            return {"kind": "sheet", "page_name": pname,
                    "page_w_mm": pw, "page_h_mm": ph,
                    "outer_mm": outer, "hole_mm": hole, "count": count,
                    "labels": labels, "mirror": bool(getattr(self, "ed_sheet_lock", True)),
                    "img_px": 1500, "spine_section": None}
        if self._ed_current_type() == "label":
            outer = self._parse(self.ed_outer) or 0.0
            hole = self._parse(self.ed_hole) or 0.0
            return {"kind": "label", "outer_mm": outer, "hole_mm": hole,
                    "offset_x_mm": 0.0, "offset_y_mm": 0.0,
                    "img_px": 1500, "spine_section": None}
        unit = self._ed_unit()
        height = self._parse(self.ed_height) or 0.0
        sections = []
        for e_name, e_w, _ in self.ed_rows:
            w = self._parse(e_w) or 0.0
            sections.append({"name": e_name.get_text().strip() or "?", "width": w})
        sp_idx = self.ed_spine.get_active() - 1
        spine = sp_idx if 0 <= sp_idx < len(sections) else None
        return {"unit": unit, "dpi": 300, "height": height,
                "sections": sections, "kind": "cover", "print_w_mm": None,
                "spine_section": spine}

    def on_ed_save(self, button):
        if not self._ed_validate():
            return
        name = self.ed_name.get_text().strip()
        f = self._ed_collect()
        existing = list(all_formats().keys())
        ok, msg = validate_format(name, f, existing, original_name=self.ed_selected)
        if not ok:
            self._info(T["ed_invalid"], msg, error=True)
            return
        # salva nel dizionario utente: per un base diventa una versione modificata
        self.ed_user[name] = f
        # ...ma se un base e' identico all'originale, non e' una vera modifica:
        # niente versione salvata, niente "(modificato)".
        if is_base(name) and formats_equal(f, factory_format(name)):
            self.ed_user.pop(name, None)
        # RINOMINA: se ho cambiato il nome del formato che stavo modificando,
        # sostituisco il vecchio invece di duplicarlo. Per i formati di fabbrica
        # (che non si possono cancellare) lo "nascondo" dall'elenco: si recupera
        # con il Ripristino di fabbrica.
        hidden = load_hidden_bases()
        changed = False
        old = self.ed_selected
        if old and old != name:
            self.ed_user.pop(old, None)
            if is_base(old) and old not in hidden:
                hidden.add(old)
                changed = True
        # se salvo con il nome di un formato di fabbrica che era nascosto, lo
        # rendo di nuovo visibile (il nome torna in uso).
        if is_base(name) and name in hidden:
            hidden.discard(name)
            changed = True
        if changed:
            save_hidden_bases(hidden)
        save_custom_formats(self.ed_user)
        self._ed_reload_list()
        if name in self.ed_list_names:
            self.ed_list.handler_block_by_func(self.on_ed_select)
            self.ed_list.set_active(self.ed_list_names.index(name))
            self.ed_list.handler_unblock_by_func(self.on_ed_select)
            self.ed_selected = name
            self._ed_update_del_button(name)
        self.refresh_formats(keep=name)

    # --- Stampa di prova dall'editor: stampa il formato che si sta creando
    #     (valori correnti, NON salvati), a vuoto. Cover -> cornice taglio/piega;
    #     Disco -> cerchio/foro/crocetta sul vassoio; Foglio -> idem su A4. ---
    def on_ed_test_print(self, button):
        if not self._ed_validate():
            return
        f = self._ed_collect()
        self._ed_test_fmt = f
        kind = f.get("kind")
        parent = getattr(self, "win_editor", None) or self
        op = Gtk.PrintOperation()
        op.set_unit(Gtk.Unit.MM)
        op.set_n_pages(1)
        try:
            if kind == "sheet":
                self._print_target = "sheet"
                pw = float(f.get("page_w_mm", 210.0))
                ph = float(f.get("page_h_mm", 297.0))
                op.set_use_full_page(True)
                op.set_job_name("%s - %s (%s)" % (
                    T["app_title"], T["ed_type_sheet"], T["ed_testprint"]))
                setup = Gtk.PageSetup()
                if abs(pw - 210.0) < 0.5 and abs(ph - 297.0) < 0.5:
                    setup.set_paper_size(Gtk.PaperSize.new("iso_a4"))
                else:
                    setup.set_paper_size(Gtk.PaperSize.new_custom(
                        "cover-studio-sheet", "Cover Studio sheet",
                        pw, ph, Gtk.Unit.MM))
                setup.set_orientation(Gtk.PageOrientation.PORTRAIT)
                op.set_default_page_setup(setup)
                if self.print_settings_sheet is not None:
                    op.set_print_settings(self.print_settings_sheet)
                op.connect("draw-page", self.on_ed_test_sheet_draw)
            elif kind == "label":
                self._print_target = "label"
                op.set_embed_page_setup(True)
                op.set_use_full_page(False)
                op.set_job_name("%s - %s (%s)" % (
                    T["app_title"], T["ed_type_disc"], T["ed_testprint"]))
                if self.print_settings_label is not None:
                    op.set_print_settings(self.print_settings_label)
                if self.page_setup_label is not None:
                    op.set_default_page_setup(self.page_setup_label)
                op.connect("draw-page", self.on_ed_test_disc_draw)
            else:  # cover
                self._print_target = "cover"
                op.set_use_full_page(False)
                op.set_job_name("%s - %s (%s)" % (
                    T["app_title"], T["ed_type_cover"], T["ed_testprint"]))
                setup = Gtk.PageSetup()
                setup.set_paper_size(Gtk.PaperSize.new("iso_a4"))
                setup.set_orientation(Gtk.PageOrientation.LANDSCAPE)
                op.set_default_page_setup(setup)
                if self.print_settings_cover is not None:
                    op.set_print_settings(self.print_settings_cover)
                op.connect("draw-page", self.on_ed_test_cover_draw)
            op.set_allow_async(True)
            op.connect("done", self.on_print_done)
            self._print_op = op
            op.run(Gtk.PrintOperationAction.PRINT_DIALOG, parent)
        except Exception as e:
            self._print_op = None
            self._info(T["print_error_title"], str(e), error=True)

    def on_ed_test_sheet_draw(self, operation, context, page_nr):
        cr = context.get_cairo_context()        # gia' in millimetri
        f = self._ed_test_fmt
        pw = float(f.get("page_w_mm", 210.0))
        ph = float(f.get("page_h_mm", 297.0))
        outer_r = max(float(f.get("outer_mm", 0.0)), 0.0) / 2.0
        hole_r = max(float(f.get("hole_mm", 0.0)), 0.0) / 2.0
        labels = f.get("labels") or sheet_label_positions(
            pw, ph, f.get("count", 1))
        for lab in labels:
            draw_test_marks(cr, lab.get("x_mm", pw / 2.0),
                            lab.get("y_mm", ph / 2.0), outer_r, hole_r)

    def on_ed_test_disc_draw(self, operation, context, page_nr):
        cr = context.get_cairo_context()        # gia' in millimetri
        try:
            self._captured_label_page_setup = context.get_page_setup()
        except Exception:
            self._captured_label_page_setup = None
        pw = context.get_width()
        ph = context.get_height()
        f = self._ed_test_fmt
        outer_r = max(float(f.get("outer_mm", 0.0)), 0.0) / 2.0
        hole_r = max(float(f.get("hole_mm", 0.0)), 0.0) / 2.0
        offx = float(self.settings.get("printer_offx", 0.0))
        offy = float(self.settings.get("printer_offy", 0.0))
        draw_test_marks(cr, pw / 2.0 + offx, ph / 2.0 + offy, outer_r, hole_r)

    def on_ed_test_cover_draw(self, operation, context, page_nr):
        cr = context.get_cairo_context()        # gia' in millimetri
        page_mm = (context.get_width(), context.get_height())
        draw_cover(cr, self._ed_test_fmt, page_mm, None,
                   show_cut=self.opt_show_cut, show_fold=self.opt_show_fold)

    def on_ed_delete(self, button):
        name = self.ed_selected
        if not name:
            return
        if is_base(name):
            # "Torna all'originale": rimuove la versione modificata, se c'e'
            if name not in self.ed_user:
                return
            if not self._confirm(T["ed_confirm_revert"] % name):
                return
            del self.ed_user[name]
            save_custom_formats(self.ed_user)
            self._ed_reload_list()
            if name in self.ed_list_names:
                self.ed_list.handler_block_by_func(self.on_ed_select)
                self.ed_list.set_active(self.ed_list_names.index(name))
                self.ed_list.handler_unblock_by_func(self.on_ed_select)
                self.on_ed_select(self.ed_list)   # ricarica i valori di fabbrica
            self.refresh_formats(keep=name)
        else:
            # formato personalizzato: eliminazione vera
            if name not in self.ed_user:
                return
            if not self._confirm(T["ed_confirm_delete"] % name):
                return
            del self.ed_user[name]
            save_custom_formats(self.ed_user)
            self._ed_reload_list()
            self.on_ed_new(None)
            self.refresh_formats()

    def _confirm(self, text):
        d = Gtk.MessageDialog(transient_for=self.win_editor, modal=True,
                              message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.YES_NO, text=text)
        r = d.run()
        d.destroy()
        return r == Gtk.ResponseType.YES

    def on_ed_draw(self, area, cr):
        alloc = area.get_allocation()
        W, H = alloc.width, alloc.height
        cr.set_source_rgb(0.92, 0.92, 0.92)
        cr.paint()
        if self._ed_current_type() == "label":
            self._ed_draw_disc(cr, W, H)
            return False
        if self._ed_current_type() == "sheet":
            self._ed_draw_sheet(cr, W, H)
            return False
        f = self._ed_collect()
        try:
            cw, ch = print_size_mm(f)
        except Exception:
            return False
        if cw <= 0 or ch <= 0:
            return False
        margin = 22
        scale = min((W - 2 * margin) / cw, (H - 2 * margin) / ch)
        if scale <= 0:
            return False
        bw, bh = cw * scale, ch * scale
        ox, oy = (W - bw) / 2.0, (H - bh) / 2.0
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(ox, oy, bw, bh)
        cr.fill_preserve()
        cr.set_source_rgb(0.4, 0.4, 0.4)
        cr.set_line_width(1.0)
        cr.stroke()
        try:
            widths = section_widths_mm(f, cw)
        except Exception:
            widths = []
        acc = 0.0
        edges = [ox]
        for w in widths[:-1]:
            acc += w
            x = ox + acc / cw * bw
            edges.append(x)
            cr.set_source_rgba(0.4, 0.4, 0.9, 0.7)
            cr.set_dash([4.0, 4.0])
            cr.set_line_width(1.0)
            cr.move_to(x, oy)
            cr.line_to(x, oy + bh)
            cr.stroke()
            cr.set_dash([])
        edges.append(ox + bw)
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.select_font_face("Sans")
        cr.set_font_size(11)
        for i, nm in enumerate(section_names(f)):
            if i + 1 < len(edges):
                cxc = (edges[i] + edges[i + 1]) / 2.0
                ext = cr.text_extents(nm)
                cr.move_to(cxc - ext.width / 2.0, oy + bh / 2.0)
                cr.show_text(nm)
        return False

    def _sheet_draw_area(self, cr, W, H, fmt, image_surface):
        """Disegna un foglio di etichette adesive su una DrawingArea (tela neutra,
        foglio bianco in scala, etichette in grigio). Riusato da Editor e
        schermata principale."""
        pw = float(fmt.get("page_w_mm", 210.0))
        ph = float(fmt.get("page_h_mm", 297.0))
        outer = float(fmt.get("outer_mm", 0.0))
        hole = float(fmt.get("hole_mm", 0.0))
        labels = fmt.get("labels") or sheet_label_positions(pw, ph, fmt.get("count", 1))
        cr.set_source_rgb(0.90, 0.90, 0.90)        # tela neutra
        cr.paint()
        if pw <= 0 or ph <= 0:
            return
        margin = 18
        scale = min((W - 2 * margin) / pw, (H - 2 * margin) / ph)
        if scale <= 0:
            return
        ox = (W - pw * scale) / 2.0
        oy = (H - ph * scale) / 2.0
        cr.save()
        cr.translate(ox, oy)
        cr.scale(scale, scale)                     # ora in mm, origine foglio
        cr.set_source_rgb(1.0, 1.0, 1.0)           # foglio bianco
        cr.rectangle(0, 0, pw, ph)
        cr.fill()
        draw_sheet(cr, pw, ph, labels, outer, hole, image_surface,
                   ink=(0.35, 0.35, 0.35), line_w=0.4)
        cr.restore()

    def _ed_draw_sheet(self, cr, W, H):
        pname = self._ed_page_name()
        pw, ph = self._ed_page_dims()
        outer = self._parse(self.ed_s_outer) or 0.0
        hole = self._parse(self.ed_s_hole) or 0.0
        count = self.ed_count_sheet.get_active() + 1
        labels = getattr(self, "ed_sheet_labels", None)
        if not labels or len(labels) != count:
            labels = sheet_label_positions(pw, ph, count)
            self.ed_sheet_labels = labels
        r = outer / 2.0
        # tela + foglio in scala
        cr.set_source_rgb(0.90, 0.90, 0.90)
        cr.paint()
        margin = 18
        scale = min((W - 2 * margin) / pw, (H - 2 * margin) / ph) if pw and ph else 0
        if scale <= 0:
            return
        ox = (W - pw * scale) / 2.0
        oy = (H - ph * scale) / 2.0
        cr.save()
        cr.translate(ox, oy)
        cr.scale(scale, scale)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, pw, ph)
        cr.fill()
        draw_sheet(cr, pw, ph, labels, outer, hole, None,
                   ink=(0.35, 0.35, 0.35), line_w=0.4)
        cr.restore()
        # guide colorate ben visibili (in px): per ogni etichetta
        #  orizzontale (Da sinistra/Da destra) = arancione, verticale = blu
        def _px(mx, my):
            return (ox + mx * scale, oy + my * scale)

        r_px = r * scale
        if r > 0:
            cr.set_line_width(2.0)
            for li, lab in enumerate(labels):
                n = len(labels)
                ref_h = "right" if (n == 2 and li == 1) else "left"
                ref_v = "bottom" if (n == 2 and li == 1) else "top"
                px, py = _px(lab["x_mm"], lab["y_mm"])
                cr.set_dash([6, 4])
                cr.set_source_rgb(*SHEET_COL_LEFT)          # orizzontale
                if ref_h == "left":
                    cr.move_to(ox, py)
                    cr.line_to(px - r_px, py)
                else:
                    cr.move_to(px + r_px, py)
                    cr.line_to(ox + pw * scale, py)
                cr.stroke()
                cr.set_source_rgb(*SHEET_COL_VERT)          # verticale
                if ref_v == "top":
                    cr.move_to(px, oy)
                    cr.line_to(px, py - r_px)
                else:
                    cr.move_to(px, py + r_px)
                    cr.line_to(px, oy + ph * scale)
                cr.stroke()
                cr.set_dash([])
            ai = getattr(self, "ed_sheet_active", 0)
            if 0 <= ai < len(labels):
                axp, ayp = _px(labels[ai]["x_mm"], labels[ai]["y_mm"])
                cr.set_source_rgba(0.20, 0.20, 0.20, 0.9)
                cr.set_line_width(1.5)
                cr.new_sub_path()
                cr.arc(axp, ayp, r_px, 0, 2 * math.pi)
                cr.stroke()

    def _ed_draw_disc(self, cr, W, H):
        """Anteprima del disco nell'Editor: cerchio esterno + foro, in scala."""
        outer = self._parse(self.ed_outer) or 0.0
        hole = self._parse(self.ed_hole) or 0.0
        if outer <= 0:
            return
        margin = 22
        r = min(W - 2 * margin, H - 2 * margin) / 2.0
        if r <= 0:
            return
        cx, cy = W / 2.0, H / 2.0
        cr.set_source_rgb(1, 1, 1)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgb(0.4, 0.4, 0.4)
        cr.set_line_width(1.2)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        if 0 < hole < outer:
            rh = r * (hole / outer)
            cr.new_sub_path()
            cr.arc(cx, cy, rh, 0, 2 * math.pi)
            cr.stroke()

    # ------------------------------------------------------- STAMPA IN SERIE
    def _image_filter(self):
        flt = Gtk.FileFilter()
        flt.set_name(T["images"])
        flt.add_pixbuf_formats()
        return flt

    def _is_image(self, path):
        try:
            info = GdkPixbuf.Pixbuf.get_file_info(path)
            return info[0] is not None
        except Exception:
            return False

    def on_batch_clicked(self, button):
        if getattr(self, "win_batch", None) is not None:
            self.win_batch.present()
            return

        win = Gtk.Window(title=T["batch_title"])
        win.set_border_width(12)
        self.win_batch = win

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        win.add(root)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.pack_start(Gtk.Label(label=T["batch_format"]), False, False, 0)
        self.batch_combo = Gtk.ComboBoxText()
        self.batch_combo.set_tooltip_text(T["tt_batch_combo"])
        self.batch_format_names = [n for n in self.format_names
                                   if self.formats[n].get("kind") != "label"]
        for nm in self.batch_format_names:
            self.batch_combo.append_text(display_name(nm, self.formats[nm]))
        try:
            self.batch_combo.set_active(
                self.batch_format_names.index(self.current_format))
        except Exception:
            self.batch_combo.set_active(0)
        bar.pack_start(self.batch_combo, False, False, 0)
        btn_add = Gtk.Button(label=T["batch_add"])
        btn_add.set_tooltip_text(T["tt_batch_add"])
        btn_add.connect("clicked", self.on_batch_add)
        bar.pack_start(btn_add, False, False, 0)
        self.batch_btn_clear = Gtk.Button(label=T["batch_clear"])
        self.batch_btn_clear.set_tooltip_text(T["tt_batch_clear"])
        self.batch_btn_clear.connect("clicked", self.on_batch_clear)
        bar.pack_start(self.batch_btn_clear, False, False, 0)
        self.batch_btn_print = Gtk.Button(label=T["batch_print"])
        self.batch_btn_print.get_style_context().add_class("suggested-action")
        self.batch_btn_print.set_tooltip_text(T["tt_batch_print"])
        self.batch_btn_print.connect("clicked", self.on_batch_print)
        bar.pack_end(self.batch_btn_print, False, False, 0)
        root.pack_start(bar, False, False, 0)

        self.batch_scroll = Gtk.ScrolledWindow()
        self.batch_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.batch_scroll.connect("size-allocate", self._batch_on_resize)
        self.batch_grid = Gtk.Grid()
        self.batch_grid.set_row_spacing(10)
        self.batch_grid.set_column_spacing(10)
        self.batch_grid.set_column_homogeneous(True)   # 3 colonne uguali
        self.batch_grid.set_hexpand(True)              # riempie la larghezza
        self.batch_grid.set_valign(Gtk.Align.START)    # righe in alto, spazio fisso
        self.batch_grid.set_margin_top(6)
        self.batch_grid.set_margin_bottom(6)
        self.batch_grid.set_margin_start(4)
        self.batch_grid.set_margin_end(4)
        self.batch_scroll.add(self.batch_grid)
        root.pack_start(self.batch_scroll, True, True, 0)

        self.batch_status = Gtk.Label(xalign=0.0)
        root.pack_start(self.batch_status, False, False, 0)

        win.connect("destroy", self.on_batch_destroyed)
        self._batch_rebuild()
        self._present_child(win)

    def on_batch_destroyed(self, win):
        self.win_batch = None
        self.batch_items = []      # uscendo, la coda si svuota dalla memoria

    def on_batch_add(self, button):
        dialog = Gtk.FileChooserDialog(
            title=T["choose_images"], parent=self.win_batch,
            action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(T["cancel"], Gtk.ResponseType.CANCEL,
                           T["open"], Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        dialog.add_filter(self._image_filter())
        last = self.settings.get("last_folder")
        if last and os.path.isdir(last):
            dialog.set_current_folder(last)
        if dialog.run() == Gtk.ResponseType.OK:
            files = dialog.get_filenames()
            for path in files:
                if self._is_image(path):
                    self.batch_items.append(path)
            if files:
                self.settings["last_folder"] = os.path.dirname(files[-1])
                save_settings(self.settings)
        dialog.destroy()
        self._batch_rebuild()

    def on_batch_clear(self, button):
        self.batch_items = []
        self._batch_rebuild()

    def _batch_remove(self, index):
        if 0 <= index < len(self.batch_items):
            del self.batch_items[index]
            self._batch_rebuild()

    def _batch_rebuild(self):
        for ch in self.batch_grid.get_children():
            self.batch_grid.remove(ch)
        self.batch_cells = []
        n = len(self.batch_items)
        # solo le righe che servono (niente righe vuote minime)
        slots = ((n + BATCH_COLS - 1) // BATCH_COLS) * BATCH_COLS if n > 0 else 0
        for s in range(slots):
            if s < n:
                cell = self._batch_make_thumb(s, self.batch_items[s])
                self.batch_cells.append(cell)
            else:
                # spaziatore INVISIBILE: tiene le 3 colonne uguali senza mostrare nulla
                cell = Gtk.Box()
                cell.set_hexpand(True)
            self.batch_grid.attach(cell, s % BATCH_COLS, s // BATCH_COLS, 1, 1)
        self.batch_grid.show_all()
        self._batch_cell_h = -1            # forza il ricalcolo sulle nuove celle
        self._batch_apply_cell_size()
        self.batch_status.set_text(T["batch_empty"] if n == 0 else (T["batch_count"] % n))
        self.batch_btn_clear.set_sensitive(n > 0)
        self.batch_btn_print.set_sensitive(n > 0)

    def _batch_on_resize(self, widget, alloc):
        self._batch_apply_cell_size(alloc.width)

    def _batch_apply_cell_size(self, width=None):
        """Altezza delle celle in proporzione alla larghezza (3 per riga)."""
        if not getattr(self, "batch_cells", None):
            return
        if width is None:
            width = self.batch_scroll.get_allocation().width
        usable = width - 2 * 10 - 28        # 2 spazi tra colonne + barra scorrimento
        cell_w = max(120.0, usable / 3.0)
        cell_h = int(cell_w * (BATCH_SLOT_H / float(BATCH_SLOT_W)))
        if cell_h == getattr(self, "_batch_cell_h", -1):
            return                          # nessun cambiamento: evita rientri
        self._batch_cell_h = cell_h
        for cell in self.batch_cells:
            cell.set_size_request(-1, cell_h)

    def _batch_thumb_draw(self, area, cr, pb):
        if pb is None:
            return False
        alloc = area.get_allocation()
        W, H = alloc.width, alloc.height
        pw, ph = pb.get_width(), pb.get_height()
        pad = 6
        aw, ah = max(1, W - 2 * pad), max(1, H - 2 * pad)
        scale = min(aw / pw, ah / ph)
        dw, dh = pw * scale, ph * scale
        x, y = (W - dw) / 2.0, (H - dh) / 2.0
        cr.save()
        cr.translate(x, y)
        cr.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        cr.paint()
        cr.restore()
        return False

    def _batch_make_thumb(self, idx, path):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 600, 600, True)
        except Exception:
            pb = None
        area = Gtk.DrawingArea()
        area.set_hexpand(True)
        area.connect("draw", self._batch_thumb_draw, pb)

        overlay = Gtk.Overlay()
        overlay.add(area)
        trash = Gtk.Button()
        trash.set_image(Gtk.Image.new_from_icon_name("user-trash-symbolic",
                                                     Gtk.IconSize.LARGE_TOOLBAR))
        trash.set_tooltip_text(T["tt_batch_trash"])
        trash.set_halign(Gtk.Align.CENTER)
        trash.set_valign(Gtk.Align.CENTER)
        trash.set_no_show_all(True)
        trash.connect("clicked", lambda b, i=idx: self._batch_remove(i))
        overlay.add_overlay(trash)

        ev = Gtk.EventBox()
        ev.add(overlay)
        ev.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        ev.connect("enter-notify-event", lambda w, e: trash.show())
        ev.connect("leave-notify-event", self._batch_leave, trash)
        ev.set_tooltip_text(os.path.basename(path))
        ev.set_hexpand(True)
        ev.set_halign(Gtk.Align.FILL)
        ev.set_valign(Gtk.Align.START)
        self._apply_tooltip_pref(ev)   # rispetta la preferenza anche sulle celle
        return ev

    def _batch_leave(self, widget, event, trash):
        # non nascondere il cestino se il puntatore e' passato su un figlio
        # (cioe' sul cestino stesso): cosi' il clic va a buon fine
        if event.detail != Gdk.NotifyType.INFERIOR:
            trash.hide()

    # --- stampa della coda: un unico lavoro a piu' pagine ---
    def on_batch_print(self, button):
        if not self.batch_items:
            return
        idx = self.batch_combo.get_active()
        if not (0 <= idx < len(self.batch_format_names)):
            return
        self._batch_fmt_name = self.batch_format_names[idx]

        op = Gtk.PrintOperation()
        setup = Gtk.PageSetup()
        setup.set_paper_size(Gtk.PaperSize.new("iso_a4"))
        setup.set_orientation(Gtk.PageOrientation.LANDSCAPE)
        op.set_default_page_setup(setup)
        op.set_use_full_page(False)
        op.set_unit(Gtk.Unit.MM)
        op.set_n_pages(len(self.batch_items))
        op.set_job_name(T["app_title"] + " - " + T["batch_title"])
        self._print_target = "cover"
        if self.print_settings_cover is not None:
            op.set_print_settings(self.print_settings_cover)
        op.set_allow_async(True)
        op.connect("draw-page", self.on_batch_draw_page)
        op.connect("done", self.on_batch_done)
        self._batch_op = op
        try:
            op.run(Gtk.PrintOperationAction.PRINT_DIALOG, self.win_batch or self)
        except Exception as e:
            self._batch_op = None
            self._info(T["print_error_title"], str(e), error=True)

    def on_batch_draw_page(self, operation, context, page_nr):
        surface = None
        if 0 <= page_nr < len(self.batch_items):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(self.batch_items[page_nr])
                surface = pixbuf_to_surface(pb)
            except Exception:
                surface = None
        cr = context.get_cairo_context()
        page_mm = (context.get_width(), context.get_height())
        fmt = dict(self.formats[self._batch_fmt_name])
        fmt["_name"] = self._batch_fmt_name
        draw_cover(cr, fmt, page_mm, surface,
                   show_cut=self.opt_show_cut, show_fold=self.opt_show_fold)

    def on_batch_done(self, operation, result):
        if result == Gtk.PrintOperationResult.ERROR:
            self._info(T["print_error_title"], T["print_error"], error=True)
        elif result == Gtk.PrintOperationResult.APPLY:
            self.print_settings_cover = operation.get_print_settings()
            try:
                os.makedirs(CONFIG_DIR, exist_ok=True)
                self.print_settings_cover.to_file(PRINT_SETTINGS_COVER)
            except Exception:
                pass
        self._batch_op = None

    # ------------------------------------------------------ GEOMETRIA FINESTRA
    def _point_on_screen(self, x, y):
        """True se (x, y) cade dentro (con tolleranza) uno dei monitor."""
        try:
            display = Gdk.Display.get_default()
            for i in range(display.get_n_monitors()):
                g = display.get_monitor(i).get_geometry()
                if (g.x - 50) <= x <= (g.x + g.width - 50) and \
                   (g.y - 50) <= y <= (g.y + g.height - 50):
                    return True
        except Exception:
            return False
        return False

    def _window_center(self, win):
        """Centro (x, y) della finestra data."""
        x, y = win.get_position()
        w, h = win.get_size()
        return x + w / 2.0, y + h / 2.0

    def _save_geometry_now(self):
        try:
            w, h = self.get_size()
            x, y = self.get_position()
            self.settings["win_w"] = int(w)
            self.settings["win_h"] = int(h)
            self.settings["win_x"] = int(x)
            self.settings["win_y"] = int(y)
            save_settings(self.settings)
        except Exception:
            pass

    def on_delete(self, widget, event):
        # Salva dimensione e posizione prima di chiudere
        self._save_geometry_now()
        return False  # lascia proseguire la chiusura

    # ----------------------------------------------- FINESTRE SECONDARIE (regola)
    # Regola comune a TUTTE le finestre secondarie (Opzioni, Anteprima, Editor
    # formato, Stampa in serie):
    #  - all'apertura la principale viene NASCOSTA e la secondaria appare
    #    centrata dov'era la principale;
    #  - alla chiusura la principale riappare centrata dove l'utente ha
    #    lasciato la secondaria (e la nuova posizione viene memorizzata).
    def _disable_tooltips(self, w):
        # Toglie il fumetto da un controllo e da tutti i suoi figli.
        try:
            w.set_has_tooltip(False)
        except Exception:
            pass
        if isinstance(w, Gtk.Container):
            for c in w.get_children():
                self._disable_tooltips(c)

    def _apply_tooltip_pref(self, root):
        # I suggerimenti si attivano/disattivano al riavvio: se sono spenti,
        # rimuovo i fumetti da tutti i controlli della finestra indicata.
        if not getattr(self, "show_tooltips", True):
            self._disable_tooltips(root)

    def _present_child(self, win):
        win.connect("delete-event", self._child_on_delete)
        w, h = self.get_size()                       # stessa misura della principale
        win.set_default_size(w, h)
        self._apply_tooltip_pref(win)
        win.show_all()
        cx, cy = self._window_center(self)          # centro della principale
        win.move(int(cx - w / 2.0), int(cy - h / 2.0))
        self.hide()                                  # nasconde la principale

    def _child_on_delete(self, win, event):
        # La principale riappare centrata dove si trova ora la secondaria.
        # Lo spostamento va fatto DOPO che la principale e' di nuovo a schermo
        # (su X11 spostarla mentre e' nascosta non viene onorato la prima volta).
        try:
            cx, cy = self._window_center(win)
            w, h = self.get_size()
            self._pending_move = (int(cx - w / 2.0), int(cy - h / 2.0))
        except Exception:
            self._pending_move = None
        self.show()
        self.present()
        if self._pending_move:
            GLib.idle_add(self._apply_pending_move)
        return False  # lascia che la secondaria venga distrutta

    def _apply_pending_move(self):
        pos = getattr(self, "_pending_move", None)
        if pos:
            self.move(pos[0], pos[1])
            self._pending_move = None
            self._save_geometry_now()
        return False  # esegui una sola volta

    # ------------------------------------------------------------ ANTEPRIMA
    # L'anteprima mostra l'intero FOGLIO A4 con la cover centrata, cosi' si
    # vedono anche le linee di taglio che arrivano ai bordi.
    def on_draw_preview(self, area, cr):
        f = self.formats[self.current_format]
        if f.get("kind") == "label":
            self._draw_label_preview(cr, area)
            return False
        if f.get("kind") == "sheet":
            alloc = area.get_allocation()
            self._sheet_draw_area(cr, alloc.width, alloc.height, f,
                                  self.image_surface)
            return False
        cover_w, cover_h = print_size_mm(f)
        page_w, page_h = A4_LANDSCAPE_MM

        alloc = area.get_allocation()
        area_w, area_h = alloc.width, alloc.height

        cr.set_source_rgb(0.90, 0.90, 0.90)
        cr.paint()

        # Scala per far entrare l'intero foglio A4
        margin = 24
        scale = min((area_w - 2 * margin) / page_w, (area_h - 2 * margin) / page_h)
        pw = page_w * scale
        ph = page_h * scale
        pox = (area_w - pw) / 2.0   # origine foglio
        poy = (area_h - ph) / 2.0

        def X(mm): return pox + mm * scale
        def Y(mm): return poy + mm * scale

        # Foglio A4 (bianco)
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(pox, poy, pw, ph)
        cr.fill_preserve()
        cr.set_source_rgb(0.75, 0.75, 0.75)
        cr.set_line_width(1.0)
        cr.stroke()

        # Cover centrata nel foglio
        cx = (page_w - cover_w) / 2.0
        cy = (page_h - cover_h) / 2.0
        cover_px = cover_w * scale
        cover_py = cover_h * scale
        ox, oy = X(cx), Y(cy)

        # Immagine adattata (stesso identico calcolo della stampa)
        if self.image_surface is not None:
            iw = self.image_surface.get_width()
            ih = self.image_surface.get_height()
            s, iox, ioy = fit_placement(iw, ih, ox, oy, cover_px, cover_py)
            cr.save()
            cr.translate(iox, ioy)
            cr.scale(s, s)
            cr.rectangle(0, 0, iw, ih)
            cr.clip()
            cr.set_source_surface(self.image_surface, 0, 0)
            cr.get_source().set_filter(cairo.FILTER_GOOD)
            cr.paint()
            cr.restore()
        else:
            # area cover appena accennata
            cr.set_source_rgb(0.97, 0.97, 0.97)
            cr.rectangle(ox, oy, cover_px, cover_py)
            cr.fill()

        # Contorno area di stampa (a video, per "intravedere" la cover) +
        # crocini di taglio a lunghezza fissa identici a quelli stampati.
        left, right = ox, ox + cover_px
        top, bot = oy, oy + cover_py
        cr.set_source_rgba(CUT_GREY, CUT_GREY, CUT_GREY, 0.9)
        cr.set_line_width(1.0)
        cr.set_dash([5.0, 4.0])
        cr.rectangle(left, top, cover_px, cover_py)   # contorno area di stampa
        cr.stroke()

        # crocini agli angoli (lunghezza fissa, scalata a video)
        g = CUT_GAP * scale
        L = CUT_LEN * scale
        cr.set_dash([3.0, 2.5])
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

        # Pieghe (confini tra sezioni) - SOLO a schermo, non si stampano
        widths_px = [w / cover_w * cover_px for w in section_widths_mm(f, cover_w)]
        bounds = []
        acc = 0.0
        for w in widths_px[:-1]:
            acc += w
            bounds.append(ox + acc)
        cr.set_source_rgba(0.4, 0.4, 0.9, 0.6)
        cr.set_line_width(1.0)
        cr.set_dash([4.0, 4.0])
        for bx in bounds:
            cr.move_to(bx, oy); cr.line_to(bx, oy + cover_py)
        cr.stroke()
        cr.set_dash([])

        # Nomi delle sezioni (solo se non c'e' immagine, per non coprirla)
        if self.image_surface is None:
            cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.select_font_face("Sans")
            cr.set_font_size(11)
            names = section_names(f)
            edges = [ox] + bounds + [ox + cover_px]
            for i, nm in enumerate(names):
                cxc = (edges[i] + edges[i + 1]) / 2.0
                cyc = oy + cover_py / 2.0
                sec_w = edges[i + 1] - edges[i]
                if sec_w < 50:          # sezione stretta -> testo verticale
                    self._vtext(cr, nm, cxc, cyc)
                else:
                    self._ctext(cr, nm, cxc, cyc)
        return False

    def _ctext(self, cr, text, cx, cy):
        ext = cr.text_extents(text)
        cr.move_to(cx - ext.width / 2.0, cy + ext.height / 2.0)
        cr.show_text(text)

    def _vtext(self, cr, text, cx, cy):
        ext = cr.text_extents(text)
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(-math.pi / 2.0)
        cr.move_to(-ext.width / 2.0, ext.height / 2.0)
        cr.show_text(text)
        cr.restore()


def _detect_system_lang(codes):
    """Indovina la lingua dal sistema operativo (variabili d'ambiente).
    Se non e' tra quelle disponibili, ripiega su English."""
    raw = (os.environ.get("LANGUAGE") or os.environ.get("LC_ALL")
           or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "")
    code = raw.split(":")[0].split(".")[0].split("_")[0].split("-")[0].lower()
    if code in codes:
        return code
    return "en" if "en" in codes else (codes[0] if codes else "it")


def _first_run_language_dialog():
    """Finestrella mostrata SOLO al primo avvio (nessuna lingua salvata).
    Restituisce (codice_scelto, confermato)."""
    langs = available_languages()
    codes = [c for c, _ in langs]
    pre = _detect_system_lang(codes)
    dlg = Gtk.Dialog(title="Scegli la lingua   /   Choose language")
    dlg.set_modal(True)
    dlg.set_default_size(380, -1)
    dlg.add_button("OK", Gtk.ResponseType.OK)
    box = dlg.get_content_area()
    box.set_spacing(12)
    box.set_border_width(16)
    lbl = Gtk.Label(
        label="Scegli la lingua dell'applicazione\n"
              "Choose the application language")
    lbl.set_xalign(0.0)
    box.pack_start(lbl, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_tooltip_text("Lingua dell'applicazione  ·  Application language")
    active = 0
    for i, (c, nm) in enumerate(langs):
        combo.append_text(nm)
        if c == pre:
            active = i
    combo.set_active(active)
    box.pack_start(combo, False, False, 0)
    dlg.show_all()
    resp = dlg.run()
    idx = combo.get_active()
    chosen = codes[idx] if 0 <= idx < len(codes) else pre
    confirmed = (resp == Gtk.ResponseType.OK)
    dlg.destroy()
    return chosen, confirmed


def _apply_startup_language():
    """Prima di costruire l'interfaccia, riempie T con la lingua scelta.
    Al primo avvio (nessuna lingua salvata) chiede la lingua con una finestrella;
    poi la usa sempre, restando cambiabile da Opzioni. Scrive anche i file
    modello delle lingue nella cartella utente."""
    seed_user_lang_files()
    s = load_settings()
    code = s.get("language")
    if not code:
        # primo avvio: chiedo la lingua
        code, confirmed = _first_run_language_dialog()
        if confirmed:
            s["language"] = code
            save_settings(s)
        # se l'utente chiude senza confermare, uso la preselezione ma NON salvo:
        # cosi' alla prossima apertura la finestrella ricompare.
    if code:
        T.clear()
        T.update(load_language(code))


def main():
    _apply_startup_language()
    win = CoverStudioWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
