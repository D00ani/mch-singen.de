# -*- coding: utf-8 -*-
"""
Holt den aktuellen Stand des Kurs-Planers auf die Webseite.

Der Kurs-Planer (Streckenplaene fuer den Kartslalom zeichnen) wird in einem
eigenen Repo entwickelt:
    https://github.com/D00ani/BKC_Strecken_Planer
Auf der Webseite liegt davon eine unveraenderte Kopie im Ordner kurs-planer/,
erreichbar unter https://mch-singen.de/kurs-planer/ und verlinkt auf der
Kartsport-Seite.

Deshalb: im Ordner kurs-planer/ NICHTS von Hand aendern. Aenderungen gehoeren
ins Repo des Kurs-Planers - dieses Werkzeug holt sie danach hierher. Was dort
nicht (mehr) liegt, wird hier geloescht.

Ausfuehren: python tools/kursplaner_sync.py
Danach wie gewohnt veroeffentlichen.
"""
import io
import os
import sys
import urllib.error
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
ZIEL = os.path.join(ROOT, "kurs-planer")
REPO = "https://github.com/D00ani/BKC_Strecken_Planer"
ZIP_URL = REPO + "/archive/refs/heads/main.zip"

# Ohne diese Dateien ist es nicht der Kurs-Planer - dann lieber gar nichts
# anfassen, als den Ordner mit einem halben Stand zu ueberschreiben.
PFLICHT = ("index.html", "sw.js", "manifest.webmanifest")


def lade_zip():
    anfrage = urllib.request.Request(ZIP_URL, headers={"User-Agent": "MCH-Singen Kurs-Planer-Abgleich"})
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        return zipfile.ZipFile(io.BytesIO(antwort.read()))


def dateien_im_zip(archiv):
    """{relativer Pfad: Inhalt}. GitHub packt alles in einen Oberordner
    'BKC_Strecken_Planer-main/' - der faellt hier weg."""
    dateien = {}
    for eintrag in archiv.infolist():
        if eintrag.is_dir():
            continue
        teile = eintrag.filename.split("/")[1:]
        # Punkt-Dateien (.gitignore, .github/) und Texte fuer das Repo selbst
        # haben auf der Webseite nichts verloren.
        if not teile or any(teil.startswith(".") or teil == ".." for teil in teile):
            continue
        if len(teile) == 1 and teile[0].lower().endswith(".md"):
            continue
        dateien["/".join(teile)] = archiv.read(eintrag)
    return dateien


def _gleich(alt, neu):
    """Inhaltlich gleich? Git checkt Textdateien hier mit CRLF aus, im ZIP
    stehen sie mit LF - das allein ist keine Aenderung."""
    if alt == neu:
        return True
    if b"\0" in neu:
        return False
    return alt.replace(b"\r\n", b"\n") == neu.replace(b"\r\n", b"\n")


def uebernimm(dateien):
    """Schreibt den Stand nach kurs-planer/. Gibt (neu, geaendert, entfernt)
    als Listen relativer Pfade zurueck."""
    neu, geaendert, entfernt = [], [], []

    for pfad, inhalt in sorted(dateien.items()):
        ziel = os.path.join(ZIEL, pfad.replace("/", os.sep))
        if os.path.isfile(ziel):
            with open(ziel, "rb") as f:
                if _gleich(f.read(), inhalt):
                    continue
            geaendert.append(pfad)
        else:
            neu.append(pfad)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, "wb") as f:
            f.write(inhalt)

    for ordner, _, namen in os.walk(ZIEL, topdown=False):
        for name in namen:
            voll = os.path.join(ordner, name)
            pfad = os.path.relpath(voll, ZIEL).replace(os.sep, "/")
            if pfad not in dateien:
                os.remove(voll)
                entfernt.append(pfad)
        if ordner != ZIEL and not os.listdir(ordner):
            os.rmdir(ordner)

    return neu, geaendert, sorted(entfernt)


def abgleichen():
    """Gibt True zurueck, wenn sich im Ordner kurs-planer/ etwas geaendert hat."""
    print(f"\nLade {ZIP_URL} ...")
    try:
        archiv = lade_zip()
    except (urllib.error.URLError, OSError, zipfile.BadZipFile) as fehler:
        print(f"\nFEHLER - der Kurs-Planer liess sich nicht laden: {fehler}")
        print("Es wurde nichts geaendert.")
        return False

    dateien = dateien_im_zip(archiv)
    fehlend = [name for name in PFLICHT if name not in dateien]
    if fehlend:
        print(f"\nFEHLER - im geladenen Stand fehlt: {', '.join(fehlend)}")
        print("Es wurde nichts geaendert.")
        return False

    neu, geaendert, entfernt = uebernimm(dateien)

    # GitHub schreibt den Commit, aus dem das ZIP stammt, in dessen Kommentar
    stand = archiv.comment.decode("ascii", "replace")[:7] or "unbekannt"
    print(f"Stand im Repo: {stand} ({len(dateien)} Dateien)")

    if not (neu or geaendert or entfernt):
        print("\nkurs-planer/ war bereits aktuell.")
        return False

    for ueberschrift, liste in (("neu", neu), ("geaendert", geaendert), ("entfernt", entfernt)):
        if liste:
            print(f"\n{len(liste)} Datei(en) {ueberschrift}:")
            for pfad in liste:
                print(f"  kurs-planer/{pfad}")
    print("\nOnline ist das erst nach dem Veroeffentlichen.")
    return True


def main():
    print("=" * 60)
    print("  Kurs-Planer abgleichen")
    print("=" * 60)
    abgleichen()


if __name__ == "__main__":
    main()
