# -*- coding: utf-8 -*-
"""
Neue Bilder aufnehmen, ohne tools/optimize_images.py von Hand zu erweitern:
erzeugt die WebP-Fassung(en) in passender Groesse und gibt den fertigen
<picture>-Block zum Einfuegen ins HTML aus (siehe README Abschnitt 7).

Ausfuehren: python tools/bilder_pflege.py
Benoetigt: pip install Pillow
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Pillow fehlt. Bitte einmalig ausfuehren:  pip install Pillow")
    sys.exit(1)

ROOT = h.ROOT
BILDER_DIR = os.path.join(ROOT, "media", "bilder")
QUALITAET = 82

VERWENDUNGEN = [
    {
        "name": "Grosses Bild / Kopfbereich (volle Breite)",
        "breiten": [480, 800, 1600],
        "hinweis": "z. B. Startseiten-Slider",
    },
    {
        "name": "Bild im Textbereich (mittelgross)",
        "breiten": [650, 1300],
        "hinweis": "z. B. Bilder auf Unterseiten",
    },
    {
        "name": "Kleines Vorschaubild / Karte",
        "breiten": [400, 800],
        "hinweis": "z. B. Galerie-Kacheln",
    },
    {
        "name": "Logo / Sponsor (unveraendert, nur WebP)",
        "breiten": [None],
        "hinweis": "Groesse bleibt wie sie ist",
    },
]


def finde_bilder_ohne_webp():
    """Bilder unter media/, zu denen noch keine .webp-Fassung existiert."""
    treffer = []
    for verzeichnis, _, dateien in os.walk(os.path.join(ROOT, "media")):
        for name in sorted(dateien):
            if not name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            pfad = os.path.join(verzeichnis, name)
            basis = os.path.splitext(pfad)[0]
            hat_webp = os.path.isfile(basis + ".webp") or any(
                d.startswith(os.path.basename(basis) + "-") and d.endswith(".webp")
                for d in dateien
            )
            if not hat_webp:
                treffer.append(pfad)
    return treffer


def erzeuge_webp(quelle, breiten):
    bild = ImageOps.exif_transpose(Image.open(quelle))
    basis = os.path.splitext(quelle)[0]
    erzeugt = []
    for breite in breiten:
        if breite is None or breite >= bild.width:
            ziel = f"{basis}.webp" if breite is None else f"{basis}-{bild.width}.webp"
            fassung = bild
        else:
            ziel = f"{basis}-{breite}.webp"
            fassung = bild.resize((breite, round(bild.height * breite / bild.width)), Image.LANCZOS)
        fassung.save(ziel, "WEBP", quality=QUALITAET, method=6)
        erzeugt.append((ziel, fassung.size, os.path.getsize(ziel) // 1024))
    return erzeugt, bild.size


def webseiten_pfad(pfad, von_unterseite=True):
    relativ = os.path.relpath(pfad, ROOT).replace(os.sep, "/")
    return ("../" if von_unterseite else "") + relativ


def baue_picture_block(quelle, erzeugt, originalgroesse, von_unterseite, alt_text):
    quellen = []
    if len(erzeugt) > 1:
        eintraege = []
        for ziel, (breite, _), _ in erzeugt:
            eintraege.append(f"{webseiten_pfad(ziel, von_unterseite)} {breite}w")
        quellen.append(f'        <source type="image/webp" srcset="{", ".join(eintraege)}">')
    else:
        quellen.append(f'        <source type="image/webp" srcset="{webseiten_pfad(erzeugt[0][0], von_unterseite)}">')

    breite, hoehe = originalgroesse
    return (
        "<picture>\n"
        + "\n".join(quellen) + "\n"
        + f'        <img src="{webseiten_pfad(quelle, von_unterseite)}" alt="{alt_text}"\n'
        + f'             width="{breite}" height="{hoehe}" loading="lazy">\n'
        + "    </picture>"
    )


def bild_aufnehmen():
    kandidaten = finde_bilder_ohne_webp()
    if not kandidaten:
        print("\nAlle Bilder unter media/ haben bereits eine WebP-Fassung.")
        print("Neues Bild zuerst in den passenden Unterordner von media/bilder/ legen.")
        return

    print("\nBilder ohne WebP-Fassung:")
    index = h.waehle_aus_liste(kandidaten, "aufnehmen", lambda p: os.path.relpath(p, ROOT))
    if index is None:
        return
    quelle = kandidaten[index]

    with Image.open(quelle) as bild:
        print(f"\nGroesse: {bild.width}x{bild.height} Pixel, "
              f"{os.path.getsize(quelle) // 1024} KB")

    print("\nWofuer wird das Bild verwendet?")
    for i, verwendung in enumerate(VERWENDUNGEN, start=1):
        breiten = "unveraendert" if verwendung["breiten"] == [None] else \
            ", ".join(f"{b}px" for b in verwendung["breiten"])
        print(f"  {i}) {verwendung['name']}")
        print(f"     -> {breiten} ({verwendung['hinweis']})")
    wahl = int(h.frage(
        f"Auswahl (1-{len(VERWENDUNGEN)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(VERWENDUNGEN) else "Ungueltige Auswahl."
    )) - 1
    verwendung = VERWENDUNGEN[wahl]

    if not h.frage_ja(f"\nWebP-Fassung(en) fuer {os.path.relpath(quelle, ROOT)} erzeugen? (j/n): "):
        print("Abgebrochen.")
        return

    erzeugt, originalgroesse = erzeuge_webp(quelle, verwendung["breiten"])
    print("\nErzeugt:")
    for ziel, (breite, hoehe), kb in erzeugt:
        print(f"  {os.path.relpath(ziel, ROOT)}: {breite}x{hoehe}, {kb} KB")

    alt_text = h.frage("\nBildbeschreibung (alt-Text, wichtig fuer Barrierefreiheit): ")
    von_unterseite = h.frage_ja("Wird das Bild auf einer Unterseite in /pages/ eingebunden? (j/n): ")

    print("\n" + "=" * 60)
    print("  Diesen Block ins HTML einfuegen:")
    print("=" * 60)
    print(baue_picture_block(quelle, erzeugt, originalgroesse, von_unterseite, alt_text))
    print("=" * 60)
    print("\nHinweis: Bilder brauchen KEINEN Build-Schritt. Wenn du ein bestehendes")
    print("Bild ERSETZT (gleicher Dateiname), stattdessen tools/optimize_images.py")
    print("ausfuehren - das erzeugt die vorhandenen Fassungen neu.")


def main():
    print("=" * 60)
    print("  Bilder aufnehmen")
    print("=" * 60)
    while True:
        bild_aufnehmen()
        if not h.frage_ja("\nNoch ein Bild aufnehmen? (j/n): "):
            break
    print("\nFertig.")


if __name__ == "__main__":
    main()
