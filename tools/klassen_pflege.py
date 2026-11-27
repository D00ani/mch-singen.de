# -*- coding: utf-8 -*-
"""
Die Klassentabelle auf pages/kartsport.html ("Klassen & Altersgruppen").

Jede Zeile hat eine Klasse ("Klasse I a"), eine Voraussetzung ("Jahrgaenge
2008 · 2009 · 2010") und ist entweder Jugend- oder Erwachsenenklasse
(tr.kart-class-adult). Am Handy schaltet js/main.js (Abschnitt 25) daran
zwischen Jugend und Erwachsenen um.

Zum Saisonwechsel rutschen die Jahrgaenge der Jugendklassen um ein Jahr
weiter: jahrgaenge_verschieben() zaehlt jede vierstellige Jahreszahl der
Jugendzeilen hoch. Die Erwachsenenklassen haben keine Jahrgaenge.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import vorschau

ROOT = h.ROOT
KART_HTML = os.path.join(ROOT, "pages", "kartsport.html")
SEITE = "pages/kartsport.html"

_TBODY = re.compile(r'(<table class="[^"]*\bklassen-tabelle\b[^"]*">.*?<tbody>)(?P<inhalt>.*?)(?P<zu>\r?\n[ \t]*</tbody>)',
                    re.DOTALL)
_ZEILE = re.compile(r'<tr(?P<attr>[^>]*)>\s*<td>\s*<strong>(?P<klasse>.*?)</strong>\s*</td>\s*'
                    r'<td>(?P<voraus>.*?)</td>\s*</tr>', re.DOTALL)
_JAHR = re.compile(r"\b(19|20)\d\d\b")


def lies(text=None):
    """Liste von {"klasse", "voraussetzung", "erwachsen"} - Texte lesbar
    (ohne HTML-Schreibweise)."""
    text = h.lies_datei(KART_HTML) if text is None else text
    treffer = _TBODY.search(text)
    if not treffer:
        raise ValueError("Die Klassentabelle (table.klassen-tabelle) steht nicht mehr auf der Kart-Seite.")
    return [{"klasse": html.unescape(z.group("klasse")).strip(),
             "voraussetzung": " ".join(html.unescape(z.group("voraus")).split()),
             "erwachsen": "kart-class-adult" in z.group("attr")}
            for z in _ZEILE.finditer(treffer.group("inhalt"))]


def baue(text, klassen, markiere=None):
    """Seite mit neu gebauter Tabelle. markiere: Nummern der Zeilen, die in
    der Vorschau gelb erscheinen sollen."""
    treffer = _TBODY.search(text)
    if not treffer:
        raise ValueError("Die Klassentabelle (table.klassen-tabelle) steht nicht mehr auf der Kart-Seite.")
    nl = "\r\n" if "\r\n" in text else "\n"
    einrueckung = re.search(r"([ \t]*)</tbody>$", treffer.group("zu")).group(1) + " " * 4
    zeilen = []
    for nummer, k in enumerate(klassen):
        attr = ' class="kart-class-adult"' if k["erwachsen"] else ""
        tr = f"<tr{attr}>"
        if markiere and nummer in markiere:
            tr = vorschau.markiere_tag(tr)
        zeilen += [
            f"{einrueckung}{tr}",
            f"{einrueckung}    <td><strong>{html.escape(k['klasse'], quote=False)}</strong></td>",
            f"{einrueckung}    <td>{html.escape(k['voraussetzung'], quote=False)}</td>",
            f"{einrueckung}</tr>",
        ]
    inhalt = nl + nl.join(zeilen) if zeilen else ""
    return text[:treffer.start("inhalt")] + inhalt + text[treffer.end("inhalt"):]


def speichern(klassen):
    text = h.lies_datei(KART_HTML)
    neu = baue(text, klassen)
    if neu != text:
        h.schreibe_datei(KART_HTML, neu)
        return True
    return False


def vorschau_zeigen(klassen, markiere=None):
    """Oeffnet die Kart-Seite mit der geaenderten Tabelle im Browser."""
    text = h.lies_datei(KART_HTML)
    vorschau.entwurf_zeigen({SEITE: baue(text, klassen, markiere)}, SEITE)


def jahrgaenge_verschieben(klassen, schritt=1):
    """Neue Liste: in allen Jugendzeilen jede Jahreszahl um schritt weiter."""
    neu = []
    for k in klassen:
        k = dict(k)
        if not k["erwachsen"]:
            k["voraussetzung"] = _JAHR.sub(lambda m: str(int(m.group(0)) + schritt), k["voraussetzung"])
        neu.append(k)
    return neu


def jahrgaenge_kurz(klassen):
    """"2008-2018" - welche Jahrgaenge die Jugendklassen gerade abdecken."""
    jahre = [int(j.group(0)) for k in klassen if not k["erwachsen"]
             for j in _JAHR.finditer(k["voraussetzung"])]
    return f"{min(jahre)}–{max(jahre)}" if jahre else "-"


def pruefe_text(wert):
    if "<" in wert or ">" in wert:
        return "Bitte ohne spitze Klammern - hier steht nur Text."
    return None
