# -*- coding: utf-8 -*-
"""
Der Bilder-Wechsler (Slider) oben auf der Startseite.

Er zeigt drei Bilder, jedes mit Beschriftung und Ziel-Link. Damit das
Weiterblaettern endlos wirkt, stehen im HTML fuenf Eintraege: vorne eine
Kopie von Bild 3, dann Bild 1 bis 3, hinten eine Kopie von Bild 1 (die
Kopien tragen aria-hidden="true"). js/index.js rechnet genau damit.

Geaendert werden nur Link, Beschriftung, Alternativtext und Bild - alles
andere (Ladeverhalten, sizes, Kommentare) bleibt, wie es ist. Die Kopien
werden automatisch mitgezogen.

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
STARTSEITE_HTML = os.path.join(ROOT, "index.html")
SEITE = "index.html"
BREITEN = [480, 800, 1600]          # wie "Grosses Bild" in bilder_pflege

_TRACK_ANFANG = '<div class="slider-track">'
_TRACK_ENDE = '<button class="slider-btn'
_SLIDE = re.compile(r'<a (?P<attr>[^>]*\bclass="slide"[^>]*)>(?P<innen>.*?)</a>', re.DOTALL)
_HREF = re.compile(r'href="([^"]*)"')
_SRCSET = re.compile(r'(<source[^>]*\ssrcset=")([^"]*)(")')
_IMG = re.compile(r"<img\b[^>]*>")
_TEXT = re.compile(r'(<div class="slide-caption-box">\s*<span>)(.*?)(</span>)', re.DOTALL)


def _bereich(text):
    anfang = text.find(_TRACK_ANFANG)
    ende = text.find(_TRACK_ENDE, anfang)
    if anfang == -1 or ende == -1:
        raise ValueError("Der Bilder-Wechsler (slider-track) steht nicht mehr auf der Startseite.")
    return anfang, ende


def _attribut(tag, name):
    m = re.search(rf'\s{name}="([^"]*)"', tag)
    return m.group(1) if m else ""


def finde(text=None):
    """Alle fuenf Eintraege in Reihenfolge: {"start", "ende", "klon", "link",
    "text", "alt", "bild", "srcset", "breite", "hoehe"} - Texte lesbar."""
    text = h.lies_datei(STARTSEITE_HTML) if text is None else text
    anfang, ende = _bereich(text)
    eintraege = []
    for m in _SLIDE.finditer(text, anfang, ende):
        innen = m.group("innen")
        img = _IMG.search(innen)
        img = img.group(0) if img else ""
        srcset = _SRCSET.search(innen)
        beschriftung = _TEXT.search(innen)
        eintraege.append({
            "start": m.start(), "ende": m.end(),
            "klon": 'aria-hidden="true"' in m.group("attr"),
            "link": _HREF.search(m.group("attr")).group(1),
            "text": html.unescape(beschriftung.group(2)).strip() if beschriftung else "",
            "alt": html.unescape(_attribut(img, "alt")),
            "bild": _attribut(img, "src"),
            "srcset": srcset.group(2) if srcset else "",
            "breite": _attribut(img, "width"), "hoehe": _attribut(img, "height"),
        })
    return eintraege


def bilder(text=None):
    """Nur die drei echten Bilder (ohne die Kopien fuer den Endlos-Lauf)."""
    return [e for e in finde(text) if not e["klon"]]


def _paare(eintraege):
    """{Index eines echten Bildes: [Indizes aller Eintraege, die es zeigen]}"""
    echte = [n for n, e in enumerate(eintraege) if not e["klon"]]
    paare = {n: [n] for n in echte}
    if echte and eintraege[0]["klon"]:
        paare[echte[-1]].append(0)
    if echte and eintraege[-1]["klon"]:
        paare[echte[0]].append(len(eintraege) - 1)
    return paare


def kopien_stimmen(text=None):
    """Liste von Hinweisen, wo eine Kopie nicht mehr zu ihrem Bild passt."""
    eintraege = finde(text)
    hinweise = []
    for echt, alle in _paare(eintraege).items():
        for n in alle:
            if n == echt:
                continue
            for feld in ("link", "text", "bild"):
                if eintraege[n][feld] != eintraege[echt][feld]:
                    hinweise.append(f"Kopie von Bild {sorted(_paare(eintraege)).index(echt) + 1}: "
                                    f"{feld} weicht ab")
    return hinweise


def _setze_attribut(tag, name, wert):
    if re.search(rf'\s{name}="[^"]*"', tag):
        return re.sub(rf'(\s{name}=")[^"]*(")', lambda m: m.group(1) + wert + m.group(2), tag, count=1)
    return tag


def _aendere(block, neu, markiert):
    """Ein <a class="slide">-Block mit neuen Angaben."""
    auf_ende = block.index(">") + 1
    auf = _setze_attribut(block[:auf_ende], "href", html.escape(neu["link"]))
    if markiert:
        auf = vorschau.markiere_tag(auf)
    innen = block[auf_ende:]
    innen = _TEXT.sub(lambda m: m.group(1) + html.escape(neu["text"], quote=False) + m.group(3),
                      innen, count=1)

    def img(m):
        tag = _setze_attribut(m.group(0), "src", html.escape(neu["bild"]))
        tag = _setze_attribut(tag, "alt", html.escape(neu["alt"]))
        tag = _setze_attribut(tag, "width", str(neu["breite"]))
        return _setze_attribut(tag, "height", str(neu["hoehe"]))

    innen = _IMG.sub(img, innen, count=1)

    def source(m):
        tag = m.group(0)
        tag = _SRCSET.sub(lambda s: s.group(1) + html.escape(neu["srcset"]) + s.group(3), tag)
        tag = _setze_attribut(tag, "width", str(neu["breite"]))
        return _setze_attribut(tag, "height", str(neu["hoehe"]))

    innen = re.sub(r"<source\b[^>]*>", source, innen, count=1)
    return auf + innen


def geaendert(text, nummer, neu, markiert=False):
    """Startseite, in der Bild nummer (0-2) samt seiner Kopie geaendert ist.
    neu: {"link", "text", "alt", "bild", "srcset", "breite", "hoehe"}"""
    eintraege = finde(text)
    echte = [n for n, e in enumerate(eintraege) if not e["klon"]]
    ziele = _paare(eintraege)[echte[nummer]]
    for n in sorted(ziele, reverse=True):          # von hinten, Positionen bleiben gueltig
        e = eintraege[n]
        text = text[:e["start"]] + _aendere(text[e["start"]:e["ende"]], neu, markiert) + text[e["ende"]:]
    return text


def webp_erzeugen(bild_relativ):
    """Erzeugt die WebP-Fassungen fuer ein neues Bild. Gibt (srcset, breite,
    hoehe) zurueck - Pfade ab der Startseite."""
    import bilder_pflege
    quelle = os.path.join(ROOT, bild_relativ)
    erzeugt, (breite, hoehe) = bilder_pflege.erzeuge_webp(quelle, BREITEN)
    srcset = ", ".join(f"{bilder_pflege.webseiten_pfad(ziel, False)} {groesse[0]}w"
                       for ziel, groesse, _ in erzeugt)
    return srcset, breite, hoehe


def bildmasse(bild_relativ):
    from PIL import Image, ImageOps
    with Image.open(os.path.join(ROOT, bild_relativ)) as bild:
        return ImageOps.exif_transpose(bild).size


def ziele():
    """Seiten, auf die ein Bild zeigen kann (Pfade ab der Startseite)."""
    ordner = os.path.join(ROOT, "pages")
    return [f"pages/{n}" for n in sorted(os.listdir(ordner))
            if n.endswith(".html") and "vorschlag" not in n
            and n not in ("underconstruction.html", "status.html", "suche.html", "shop.html")]


def vorschau_zeigen(text):
    vorschau.entwurf_zeigen({SEITE: text}, SEITE)


def speichern(text):
    if text != h.lies_datei(STARTSEITE_HTML):
        h.schreibe_datei(STARTSEITE_HTML, text)
