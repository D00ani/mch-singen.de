# -*- coding: utf-8 -*-
"""
Die Zeitleiste auf pages/geschichte.html.

Jeder Abschnitt ist ein
    <div class="history-section">
        <h2>1954: Die Gründung</h2>
        <p>...</p>
        <p>...</p>
        (evtl. weitere Bloecke wie die Liste <div class="event-list">)
    </div>
Im Fenster wird daraus Ueberschrift + Text: Absaetze durch eine Leerzeile
getrennt, **fett** fuer Hervorhebungen, [Text](seite.html) fuer Links -
dieselbe Schreibweise wie bei den Fragen & Antworten.

Weitere Bloecke im Abschnitt (die Liste beim Jahr 1979) bleiben beim
Bearbeiten erhalten und stehen danach hinter den Absaetzen. Was zwischen
den Abschnitten steht (Trennlinien, auskommentierte Bildplaetze), wird nie
angefasst.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import faq_pflege
import pflege_hilfen as h
import vorschau

ROOT = h.ROOT
GESCHICHTE_HTML = os.path.join(ROOT, "pages", "geschichte.html")
SEITE = "pages/geschichte.html"
ANFANG = '<div class="history-section">'
_TAG = re.compile(r"<(/?)div\b[^>]*>", re.IGNORECASE)
_KOMMENTAR = re.compile(r"<!--.*?-->", re.DOTALL)
_ABSATZ = re.compile(r"<p>(.*?)</p>", re.DOTALL)
_UEBERSCHRIFT = re.compile(r"\s*<h2>(.*?)</h2>", re.DOTALL)


def _kommentare_ausblenden(text):
    """Gleich lange Fassung, in der Kommentare durch Leerzeichen ersetzt
    sind - so findet die Suche keine auskommentierten Abschnitte, die
    Positionen stimmen aber weiterhin."""
    return _KOMMENTAR.sub(lambda m: " " * len(m.group(0)), text)


def finde(text=None):
    """Liste der Abschnitte: {"start", "ende", "titel", "absaetze" (HTML),
    "rest" (HTML der uebrigen Bloecke), "einrueckung"} - start/ende sind
    Positionen in text, ende zeigt hinter das schliessende </div>."""
    text = h.lies_datei(GESCHICHTE_HTML) if text is None else text
    suche = _kommentare_ausblenden(text)
    abschnitte = []
    pos = 0
    while True:
        start = suche.find(ANFANG, pos)
        if start == -1:
            break
        tiefe, ende = 0, None
        for tag in _TAG.finditer(suche, start):
            tiefe += -1 if tag.group(1) else 1
            if tiefe == 0:
                ende = tag.end()
                break
        if ende is None:
            raise ValueError("Ein Abschnitt der Zeitleiste ist nicht geschlossen (</div> fehlt).")
        innen = text[start + len(ANFANG):ende - len("</div>")]
        kopf = _UEBERSCHRIFT.match(innen)
        titel = kopf.group(1) if kopf else ""
        rumpf = innen[kopf.end():] if kopf else innen
        absaetze = [m.group(1).strip() for m in _ABSATZ.finditer(rumpf)]
        rest = _ABSATZ.sub("", rumpf).strip()
        zeilenanfang = text.rfind("\n", 0, start) + 1
        abschnitte.append({"start": start, "ende": ende, "titel": titel, "absaetze": absaetze,
                           "rest": rest, "einrueckung": text[zeilenanfang:start]})
        pos = ende
    return abschnitte


# ------------------------------------------------------------------
# Umwandlung fuers Fenster
# ------------------------------------------------------------------

def titel_lesbar(abschnitt):
    return html.unescape(abschnitt["titel"]).strip()


def text_lesbar(abschnitt):
    """Absaetze in der einfachen Schreibweise, getrennt durch Leerzeilen."""
    return "\n\n".join(html.unescape(faq_pflege.html_zu_einfach(a)) for a in abschnitt["absaetze"])


def hat_sonderinhalt(abschnitt):
    """True, wenn ein Absatz mehr als **fett** und Links enthaelt."""
    return any(faq_pflege.hat_sonderinhalt(a) for a in abschnitt["absaetze"])


def absaetze_aus_text(text):
    """Einfache Schreibweise -> Liste von Absatz-HTML."""
    bloecke = re.split(r"\n\s*\n", text.strip())
    return [faq_pflege.einfach_zu_html(html.escape(" ".join(b.split()), quote=False))
            for b in bloecke if b.strip()]


def baue_abschnitt(titel, absaetze_html, rest="", einrueckung=" " * 8, nl="\r\n", markiert=False):
    """Kompletter <div class="history-section">-Block (ohne Einrueckung der
    ersten Zeile - die steht schon im Text davor)."""
    innen = einrueckung + " " * 4
    auf = vorschau.markiere_tag(ANFANG) if markiert else ANFANG
    zeilen = [auf, f"{innen}<h2>{html.escape(titel.strip(), quote=False)}</h2>"]
    zeilen += [f"{innen}<p>{a}</p>" for a in absaetze_html]
    if rest:
        zeilen += ["", innen + rest.strip()]
    zeilen.append(f"{einrueckung}</div>")
    return nl.join(zeilen)


# ------------------------------------------------------------------
# Aendern
# ------------------------------------------------------------------

def _nl(text):
    return "\r\n" if "\r\n" in text else "\n"


def ersetzt(text, nummer, titel, absaetze_html, markiert=False, alten_text_behalten=False):
    """Seite, in der Abschnitt nummer neu gebaut ist."""
    abschnitt = finde(text)[nummer]
    if alten_text_behalten:
        absaetze_html = abschnitt["absaetze"]
    block = baue_abschnitt(titel, absaetze_html, abschnitt["rest"], abschnitt["einrueckung"],
                           _nl(text), markiert)
    return text[:abschnitt["start"]] + block + text[abschnitt["ende"]:]


def eingefuegt(text, stelle, titel, absaetze_html, markiert=False):
    """Seite mit neuem Abschnitt an Position stelle (0 = ganz vorne,
    len = ganz hinten). Der neue Abschnitt steht direkt neben seinem
    Nachbarn - Trennlinien bleiben, wo sie sind."""
    abschnitte = finde(text)
    nl = _nl(text)
    if not abschnitte:
        raise ValueError("Auf der Geschichte-Seite wurde kein Abschnitt gefunden.")
    einrueckung = abschnitte[0]["einrueckung"]
    block = einrueckung + baue_abschnitt(titel, absaetze_html, "", einrueckung, nl, markiert)
    if stelle < len(abschnitte):
        zeilenanfang = abschnitte[stelle]["start"] - len(abschnitte[stelle]["einrueckung"])
        return text[:zeilenanfang] + block + nl + nl + text[zeilenanfang:]
    ende = abschnitte[-1]["ende"]
    return text[:ende] + nl + nl + block + text[ende:]


def entfernt(text, nummer):
    """Seite ohne Abschnitt nummer - samt Einrueckung und einer Leerzeile."""
    abschnitt = finde(text)[nummer]
    anfang = abschnitt["start"] - len(abschnitt["einrueckung"])
    ende = abschnitt["ende"]
    # Zeilenende und eine folgende Leerzeile mitnehmen
    for _ in range(2):
        m = re.match(r"[ \t]*\r?\n", text[ende:])
        if not m:
            break
        ende += m.end()
    return text[:anfang] + text[ende:]


def speichern(neuer_text):
    if neuer_text != h.lies_datei(GESCHICHTE_HTML):
        h.schreibe_datei(GESCHICHTE_HTML, neuer_text)


def vorschau_zeigen(neuer_text):
    vorschau.entwurf_zeigen({SEITE: neuer_text}, SEITE)


def pruefe_titel(wert):
    if "<" in wert or ">" in wert:
        return "Bitte ohne spitze Klammern."
    return None


def pruefe_text(wert):
    if re.search(r"<[a-zA-Z/]", wert):
        return "Bitte kein HTML - **fett** und [Text](seite.html) reichen."
    if wert.count("**") % 2:
        return "Fettschrift bitte mit ** davor UND dahinter, z. B. **wichtig**."
    return None
