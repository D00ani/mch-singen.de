# -*- coding: utf-8 -*-
"""
Prueft die Webseite auf Fehler, die auf GitHub Pages erst nach dem Push
auffallen wuerden:
  - tote Verweise (Seiten, PDFs, Bilder, CSS/JS)
  - falsche Gross-/Kleinschreibung (Windows ist tolerant, GitHub-Linux nicht!)
  - in timer.txt angekuendigte Kurzausschreibungen, die noch fehlen
  - veraltete minifizierte Dateien (Build-Schritt vergessen)

Ausfuehren: python tools/pruefe_seite.py
Wird ausserdem automatisch vor dem Veroeffentlichen aufgerufen.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT

VERWEIS_MUSTER = re.compile(
    r'(?:href|src)="([^"#?]+\.(?:html|pdf|jpg|jpeg|png|webp|gif|svg|mp4|css|js|ico|txt|json|xml))"'
)

# Quelldatei -> erzeugte Datei (siehe tools/build_assets.py, README Abschnitt 9)
BUILD_PAARE = [
    ("css/style.css", "css/bundle.min.css"),
    ("css/index.css", "css/index.min.css"),
    ("css/kartsport.css", "css/kartsport.min.css"),
    ("css/live.css", "css/live.min.css"),
]


def html_dateien():
    return sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                  glob.glob(os.path.join(ROOT, "pages", "*.html")))


def exakt_vorhanden(pfad):
    """Prueft Schritt fuer Schritt, ob JEDER Pfadteil exakt so geschrieben auf
    der Platte liegt. Windows findet 'Foto.jpg' auch als 'foto.jpg' - der
    Linux-Server von GitHub nicht (README Abschnitt 8)."""
    pfad = os.path.normpath(pfad)
    if not os.path.exists(pfad):
        return False, None

    teile = []
    rest = pfad
    while True:
        rest, name = os.path.split(rest)
        if not name:
            break
        teile.append(name)
        if os.path.normpath(rest) == os.path.normpath(ROOT) or not rest:
            break
    teile.reverse()

    aktuell = rest if rest else ROOT
    for teil in teile:
        try:
            eintraege = os.listdir(aktuell)
        except OSError:
            return True, None
        if teil not in eintraege:
            richtig = next((e for e in eintraege if e.lower() == teil.lower()), None)
            return False, richtig
        aktuell = os.path.join(aktuell, teil)
    return True, None


def pruefe_verweise():
    tote, schreibweise = [], []
    for html in html_dateien():
        basis = os.path.dirname(html)
        anzeige = os.path.relpath(html, ROOT)
        inhalt = open(html, encoding="utf-8").read()
        for verweis in VERWEIS_MUSTER.findall(inhalt):
            if verweis.startswith(("http://", "https://", "//", "mailto:", "tel:", "data:")):
                continue
            # Verweise mit fuehrendem "/" zeigen ab der Wurzel der Webseite
            # (nutzt 404.html, weil die unter JEDER Adresse ausgeliefert wird).
            if verweis.startswith("/"):
                ziel = os.path.normpath(os.path.join(ROOT, verweis.lstrip("/")))
            else:
                ziel = os.path.normpath(os.path.join(basis, verweis))
            passt, richtig = exakt_vorhanden(ziel)
            if not passt and richtig is None:
                tote.append(f"{anzeige}: {verweis}")
            elif not passt:
                schreibweise.append(f"{anzeige}: {verweis} -> heisst wirklich '{richtig}'")
    return tote, schreibweise


def pruefe_angekuendigte_pdfs():
    fehlend = []
    for name in ("timer.txt", "timer_trial.txt"):
        pfad = os.path.join(ROOT, "data", name)
        for zeile in h.lies_zeilen(pfad):
            teile = zeile.split(";")
            if len(teile) < 8 or not teile[7].strip():
                continue
            if not os.path.isfile(os.path.join(ROOT, teile[7].strip().lstrip("/"))):
                fehlend.append(f"{name} ({teile[0]}.{teile[1]}.{teile[2]}): {teile[7].strip()}")
    return fehlend


def pruefe_build_aktuell():
    veraltet = []
    for quelle, erzeugt in BUILD_PAARE:
        quellpfad, zielpfad = os.path.join(ROOT, quelle), os.path.join(ROOT, erzeugt)
        if not os.path.isfile(quellpfad) or not os.path.isfile(zielpfad):
            continue
        if os.path.getmtime(quellpfad) > os.path.getmtime(zielpfad):
            veraltet.append(f"{quelle} ist neuer als {erzeugt}")

    for quellpfad in glob.glob(os.path.join(ROOT, "js", "*.js")):
        if quellpfad.endswith(".min.js"):
            continue
        zielpfad = quellpfad.replace(".js", ".min.js")
        if os.path.isfile(zielpfad) and os.path.getmtime(quellpfad) > os.path.getmtime(zielpfad):
            veraltet.append(f"js/{os.path.basename(quellpfad)} ist neuer als die .min.js-Fassung")
    return veraltet


def pruefe_alles(still=False):
    """Fuehrt alle Pruefungen aus. Gibt True zurueck, wenn nichts Kritisches
    gefunden wurde."""
    tote, schreibweise = pruefe_verweise()
    fehlende_pdfs = pruefe_angekuendigte_pdfs()
    veralteter_build = pruefe_build_aktuell()

    kritisch = bool(tote or schreibweise or veralteter_build)

    if not still or kritisch or fehlende_pdfs:
        print("\n" + "=" * 60)
        print("  Pruefergebnis")
        print("=" * 60)

    if tote:
        print(f"\nFEHLER - {len(tote)} toter Verweis / tote Verweise (Link fuehrt ins Leere):")
        for eintrag in tote:
            print(f"  {eintrag}")

    if schreibweise:
        print(f"\nFEHLER - {len(schreibweise)}x falsche Gross-/Kleinschreibung")
        print("(funktioniert lokal, aber NICHT auf dem GitHub-Server!):")
        for eintrag in schreibweise:
            print(f"  {eintrag}")

    if veralteter_build:
        print(f"\nWARNUNG - {len(veralteter_build)}x Build-Schritt fehlt")
        print("(die Aenderung ist online nicht sichtbar, siehe README Abschnitt 9):")
        for eintrag in veralteter_build:
            print(f"  {eintrag}")
        print("  -> Menuepunkt 'Jaehrliches technisches Update' oder tools/build_assets.py")

    if fehlende_pdfs:
        print(f"\nHinweis - {len(fehlende_pdfs)} angekuendigte PDF-Datei(en) noch nicht hochgeladen")
        print("(kein Fehler - der Download-Button bleibt einfach unsichtbar):")
        for eintrag in fehlende_pdfs:
            print(f"  {eintrag}")

    if not kritisch and not fehlende_pdfs:
        if not still:
            print("\nAlles in Ordnung - keine Probleme gefunden.")
    elif not kritisch:
        print("\nKeine Fehler - nur die Hinweise oben.")

    return not kritisch


def main():
    print("=" * 60)
    print("  Webseite pruefen")
    print("=" * 60)
    pruefe_alles()


if __name__ == "__main__":
    main()
