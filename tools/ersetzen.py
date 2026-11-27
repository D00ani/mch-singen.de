# -*- coding: utf-8 -*-
"""
Suchen und Ersetzen ueber alle veroeffentlichten Seiten.

Gesucht wird nur im Text, den Besucher sehen (und im Seitentitel) - nicht
in Skripten, Stilangaben, Kommentaren, Attributen oder Links. So kann ein
Ersetzen keine Technik kaputt machen. Ein Leerzeichen im Suchtext passt
auch auf einen Zeilenwechsel im HTML.

Jeder Treffer wird einzeln ausgewaehlt; ersetzt werden nur die gewaehlten.
Geschrieben wird mit Sicherung (rueckgaengig ueber den Verlauf).

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import seitentexte
import vorschau

ROOT = h.ROOT
# Automatisch erzeugt - Aenderungen von Hand waeren beim naechsten Mal weg
AUSGENOMMEN = {"pages/status.html"}
_KEIN_TEXT = re.compile(r"<!--.*?-->|<script\b.*?</script\s*>|<style\b.*?</style\s*>|<[^>]*>",
                        re.DOTALL | re.IGNORECASE)


def dateien():
    return [d for d in seitentexte.html_dateien()
            if seitentexte._anzeige(d) not in AUSGENOMMEN]


def _textstuecke(text):
    """(Anfang, Ende) aller Textstuecke zwischen Tags, Kommentaren usw."""
    pos = 0
    for m in _KEIN_TEXT.finditer(text):
        if m.start() > pos:
            yield pos, m.start()
        pos = m.end()
    if pos < len(text):
        yield pos, len(text)


def muster(suchtext, gross_klein=False):
    worte = suchtext.split()
    if not worte:
        return None
    return re.compile(r"\s+".join(re.escape(w) for w in worte), 0 if gross_klein else re.IGNORECASE)


def _umfeld(text):
    return " ".join(text.split())


def suche(suchtext, gross_klein=False, rand=45):
    """Liste von Treffern: {"datei", "seite", "zeile", "stueck" (Anfang,
    Ende im Datei-Text), "roh" (das Stueck, zur Kontrolle), "start", "ende"
    (Position im lesbaren Stueck), "vorher", "treffer", "nachher"}"""
    regel = muster(suchtext, gross_klein)
    if regel is None:
        return []
    treffer = []
    for datei in dateien():
        text = h.lies_datei(datei)
        for anfang, ende in _textstuecke(text):
            roh = text[anfang:ende]
            lesbar = html.unescape(roh)
            for m in regel.finditer(lesbar):
                treffer.append({
                    "datei": datei, "seite": seitentexte._anzeige(datei),
                    "zeile": text.count("\n", 0, anfang) + roh.count("\n", 0, m.start()) + 1,
                    "stueck": (anfang, ende), "roh": roh,
                    "start": m.start(), "ende": m.end(),
                    "vorher": _umfeld(lesbar[max(0, m.start() - rand):m.start()]),
                    "treffer": _umfeld(m.group(0)),
                    "nachher": _umfeld(lesbar[m.end():m.end() + rand]),
                })
    return treffer


def _neue_texte(treffer, ersatz, markieren=False):
    """{Datei: neuer Text} - die gewaehlten Treffer ersetzt."""
    nach_datei = {}
    for t in treffer:
        nach_datei.setdefault(t["datei"], []).append(t)

    ergebnis = {}
    for datei, liste in nach_datei.items():
        text = h.lies_datei(datei)
        nach_stueck = {}
        for t in liste:
            nach_stueck.setdefault(t["stueck"], []).append(t)
        # von hinten nach vorne, damit die Positionen davor gueltig bleiben
        for (anfang, ende), stellen in sorted(nach_stueck.items(), reverse=True):
            roh = text[anfang:ende]
            if roh != stellen[0]["roh"]:
                raise ValueError(f"{stellen[0]['seite']} hat sich seit der Suche geändert - "
                                 "bitte noch einmal suchen.")
            lesbar = html.unescape(roh)
            # Ohne &-Schreibweise im Stueck bleibt der Rest Zeichen fuer Zeichen
            # gleich; sonst wird das Stueck einheitlich neu geschrieben.
            gleich = (lambda s: s) if "&" not in roh else (lambda s: html.escape(s, quote=False))
            neu = html.escape(ersatz, quote=False)
            if markieren:
                neu = f"<mark {vorschau.MARKE}>{neu}</mark>"
            teile, pos = [], 0
            for t in sorted(stellen, key=lambda t: t["start"]):
                if t["start"] < pos:
                    continue        # ueberlappend - kann bei Mehrfachtreffern nicht vorkommen
                teile += [gleich(lesbar[pos:t["start"]]), neu]
                pos = t["ende"]
            teile.append(gleich(lesbar[pos:]))
            text = text[:anfang] + "".join(teile) + text[ende:]
        ergebnis[datei] = text
    return ergebnis


def ersetze(treffer, ersatz):
    """Schreibt die Ersetzungen. Gibt die Liste der geaenderten Seiten zurueck."""
    geaendert = []
    for datei, text in _neue_texte(treffer, ersatz).items():
        if text != h.lies_datei(datei):
            h.schreibe_datei(datei, text)
            geaendert.append(seitentexte._anzeige(datei))
    return geaendert


def vorschau_zeigen(treffer, ersatz):
    if not treffer:
        return "Bitte zuerst Treffer auswählen."
    seiten = _neue_texte(treffer, ersatz, markieren=True)
    start = seitentexte._anzeige(treffer[0]["datei"])
    vorschau.entwurf_zeigen({seitentexte._anzeige(d): t for d, t in seiten.items()}, start)
    return None


def pruefe_ersatz(wert):
    if "<" in wert or ">" in wert:
        return "Bitte ohne spitze Klammern - ersetzt wird nur Text."
    return None
