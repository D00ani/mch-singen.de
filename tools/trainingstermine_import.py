# -*- coding: utf-8 -*-
"""
Wandelt den Excel-Export der Trainings- und Renntermine in das Format um,
das die Webseite fuer den Kalender-Download braucht
(Tag;Monat;Jahr;Startzeit-Endzeit;Gruppe, siehe README Abschnitt 4), und
passt den Dateinamen-Verweis in js/aktuelles.js gleich mit an.

Hintergrund: Der Excel-Export ist Tab-getrennt (Datum, dann je eine Spalte
pro Trainingszeit mit der Gruppen-Nummer). js/aktuelles.js erwartet aber
Semikolons - ohne Umwandlung bleibt die heruntergeladene Kalenderdatei leer.

Ausfuehren: python tools/trainingstermine_import.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
DATA_DIR = os.path.join(ROOT, "data")
AKTUELLES_JS = os.path.join(ROOT, "js", "aktuelles.js")
INDEX_JS = os.path.join(ROOT, "js", "index.js")

MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]
# js/aktuelles.js kennt beide Schreibweisen, die Datei nutzt laut README Deutsch.
MONAT_ERKENNUNG = {m.lower(): m for m in MONATE_DE}
MONAT_ERKENNUNG.update({m.lower().replace("ä", "ae"): m for m in MONATE_DE})

DATUM_MUSTER = re.compile(r"(\d{1,2})\.\s*([A-Za-zÄÖÜäöüß]+)\s*(\d{4})")
ZEIT_MUSTER = re.compile(r"^\s*(\d{1,2})[:.](\d{2})\s*$")

STANDARD_ENDE = "13:30"


def lies_quelle(pfad):
    """Excel-Exporte sind haeufig nicht UTF-8 - Kodierung der Reihe nach probieren."""
    rohdaten = open(pfad, "rb").read()
    for kodierung in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return rohdaten.decode(kodierung), kodierung
        except UnicodeDecodeError:
            continue
    return rohdaten.decode("latin-1", errors="replace"), "latin-1"


def finde_quelldateien():
    """Tab-getrennte .txt-Dateien in /data/ - das sind die Excel-Exporte."""
    treffer = []
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.lower().endswith(".txt"):
            continue
        pfad = os.path.join(DATA_DIR, name)
        text, _ = lies_quelle(pfad)
        if "\t" in text:
            treffer.append(pfad)
    return treffer


def zeit_normalisieren(text):
    treffer = ZEIT_MUSTER.match(text)
    if not treffer:
        return None
    return f"{int(treffer.group(1)):02d}:{treffer.group(2)}"


def finde_zeitspalten(zeilen):
    """Sucht die Kopfzeile ("Datum | 9.00 | 11:30 | 13:30 | ...") und liefert
    je Spaltennummer die Trainings-Startzeit."""
    for zeile in zeilen:
        spalten = zeile.split("\t")
        if not spalten or "datum" not in spalten[0].strip().lower():
            continue
        zeiten = {}
        for index, spalte in enumerate(spalten[1:], start=1):
            zeit = zeit_normalisieren(spalte)
            if zeit:
                zeiten[index] = zeit
        if zeiten:
            return zeiten
    return {}


def zeit_plus_stunden(zeit, stunden):
    stunde, minute = (int(teil) for teil in zeit.split(":"))
    return f"{min(stunde + stunden, 23):02d}:{minute:02d}"


def endzeiten_bestimmen(zeitspalten):
    """Ende eines Trainings = Beginn des naechsten. Der letzte Block endet um
    13:30, bzw. zwei Stunden spaeter, falls er danach erst beginnt."""
    sortiert = sorted(zeitspalten.items())
    enden = {}
    for position, (index, start) in enumerate(sortiert):
        if position + 1 < len(sortiert):
            enden[index] = sortiert[position + 1][1]
        else:
            enden[index] = STANDARD_ENDE if start < STANDARD_ENDE else zeit_plus_stunden(start, 2)
    return enden


def parse_datum(text):
    treffer = DATUM_MUSTER.search(text)
    if not treffer:
        return None
    monat = MONAT_ERKENNUNG.get(treffer.group(2).lower())
    if not monat:
        return None
    return treffer.group(1).zfill(2), monat, treffer.group(3)


def gruppe_normalisieren(text):
    """'1' / '2' bleiben, '1/2' (beide Gruppen zusammen) wird zu 3 - so
    erkennt js/aktuelles.js den Termin fuer beide Gruppen."""
    wert = text.strip()
    if not wert:
        return None
    if wert in ("1", "2", "3"):
        return wert
    if re.fullmatch(r"1\s*[/+&]\s*2", wert):
        return "3"
    return None


def wandle_um(text):
    zeilen = [z.rstrip("\r") for z in text.split("\n")]
    zeitspalten = finde_zeitspalten(zeilen)
    if not zeitspalten:
        raise ValueError(
            "Kopfzeile mit den Trainingszeiten nicht gefunden.\n"
            "Erwartet wird eine Zeile, die mit 'Datum' beginnt und danach die\n"
            "Uhrzeiten enthaelt (z. B. 'Datum | 9.00 | 11:30 | 13:30 | Trainer')."
        )
    enden = endzeiten_bestimmen(zeitspalten)

    ergebnis = []
    uebersprungen = []
    for zeile in zeilen:
        spalten = zeile.split("\t")
        if len(spalten) < 2:
            continue
        datum = parse_datum(spalten[0])
        if not datum:
            continue
        tag, monat, jahr = datum

        gefunden = False
        for index, start in sorted(zeitspalten.items()):
            if index >= len(spalten):
                continue
            gruppe = gruppe_normalisieren(spalten[index])
            if gruppe:
                ergebnis.append(f"{tag};{monat};{jahr};{start}-{enden[index]};{gruppe}")
                gefunden = True
        if not gefunden:
            bemerkung = " ".join(s.strip() for s in spalten[1:] if s.strip())
            uebersprungen.append(f"{spalten[0].strip()}" + (f" ({bemerkung})" if bemerkung else ""))

    return ergebnis, uebersprungen, zeitspalten, enden


def js_referenz_anpassen(dateiname):
    """Setzt den Dateinamen in js/aktuelles.js (Kalender-Download) und
    js/index.js (Winterpause-Hinweis der Startseite) auf die neue Datei.
    Gibt True zurueck, wenn mindestens eine Datei geaendert wurde."""
    # Unterseiten holen die Datei mit "../data/", die Startseite mit "data/".
    muster = re.compile(r"(fetch\(['\"](?:\.\./)?data/)trainingstermine[^'\"]*(['\"]\))")
    geaendert = False

    for pfad in (AKTUELLES_JS, INDEX_JS):
        name = "js/" + os.path.basename(pfad)
        if not os.path.isfile(pfad):
            print(f"  Hinweis: {name} nicht gefunden - Verweis bitte selbst pruefen.")
            continue

        inhalt = h.lies_datei(pfad)
        treffer = muster.search(inhalt)
        if not treffer:
            print(f"  Hinweis: Verweis auf die Trainingstermine-Datei in {name} nicht gefunden.")
            continue

        alt = treffer.group(0)
        neu = f"{treffer.group(1)}{dateiname}{treffer.group(2)}"
        if alt == neu:
            print(f"  {name} zeigt bereits auf {dateiname} - nichts zu tun.")
            continue

        h.schreibe_datei(pfad, muster.sub(lambda m: neu, inhalt, count=1))
        print(f"  {name}: Verweis auf {dateiname} aktualisiert.")
        geaendert = True

    if geaendert:
        print("  WICHTIG: Danach 'Jaehrliches technisches Update' oder build_assets.py")
        print("  laufen lassen, sonst wirkt die JS-Aenderung nicht (siehe README Abschnitt 9).")
    return geaendert


def main():
    print("=" * 60)
    print("  Trainingstermine importieren")
    print("=" * 60)
    print("\nWandelt den Excel-Export in das Format um, das der Kalender-Download")
    print("der Webseite braucht.")

    quellen = finde_quelldateien()
    if not quellen:
        print(f"\nKeine Tab-getrennte .txt-Datei in {os.path.relpath(DATA_DIR, ROOT)} gefunden.")
        print("Excel-Export bitte als .txt (Tab-getrennt) dort ablegen und erneut starten.")
        return

    print("\nGefundene Excel-Export-Dateien:")
    index = h.waehle_aus_liste(
        quellen, "umwandeln", lambda p: os.path.relpath(p, ROOT)
    )
    if index is None:
        return
    quelle = quellen[index]

    text, kodierung = lies_quelle(quelle)
    if kodierung not in ("utf-8", "utf-8-sig"):
        print(f"\nHinweis: Datei ist {kodierung}-kodiert (Excel-Standard), wird nach UTF-8 umgewandelt -")
        print("damit werden Umlaute auf der Webseite wieder korrekt angezeigt.")

    try:
        zeilen, uebersprungen, zeitspalten, enden = wandle_um(text)
    except ValueError as fehler:
        print(f"\nFEHLER: {fehler}")
        return

    if not zeilen:
        print("\nKeine Trainingstermine erkannt - bitte pruefen, ob in den Zeit-Spalten")
        print("Gruppen-Nummern (1, 2 oder 1/2) stehen.")
        return

    print("\nErkannte Trainingszeiten:")
    for spalte, start in sorted(zeitspalten.items()):
        print(f"  Spalte {spalte + 1}: {start}-{enden[spalte]}")

    print(f"\n{len(zeilen)} Trainingstermin(e) erkannt:")
    for zeile in zeilen[:6]:
        print(f"  {zeile}")
    if len(zeilen) > 6:
        print(f"  ... und {len(zeilen) - 6} weitere")

    if uebersprungen:
        print(f"\n{len(uebersprungen)} Zeile(n) ohne Gruppen-Nummer uebersprungen (kein Training):")
        for eintrag in uebersprungen[:5]:
            print(f"  {eintrag}")
        if len(uebersprungen) > 5:
            print(f"  ... und {len(uebersprungen) - 5} weitere")

    jahr = zeilen[0].split(";")[2]
    zieldatei = os.path.join(DATA_DIR, f"trainingstermine{jahr}.txt")
    print(f"\nZiel: {os.path.relpath(zieldatei, ROOT)}")

    if not h.frage_ja("Umwandlung speichern? (j/n): "):
        print("Abgebrochen, nichts geaendert.")
        return

    if os.path.abspath(quelle) == os.path.abspath(zieldatei):
        aufbewahrung = os.path.join(DATA_DIR, f"trainingstermine{jahr}_excel-export.txt")
        h.schreibe_datei(aufbewahrung, text, sichern=False)
        print(f"  Original gesichert als {os.path.relpath(aufbewahrung, ROOT)}")

    h.schreibe_zeilen(zieldatei, zeilen)
    print(f"\nGespeichert: {os.path.relpath(zieldatei, ROOT)}")

    js_referenz_anpassen(os.path.basename(zieldatei))


if __name__ == "__main__":
    main()
