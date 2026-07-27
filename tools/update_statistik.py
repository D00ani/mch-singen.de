# -*- coding: utf-8 -*-
"""
Aktualisiert den Chart "Dieses Jahr (Bisher)" auf der Statistik-Seite
automatisch aus der BKC-Vereinswertung (PDF) - kein Handzaehlen mehr noetig.

Liest die aktuelle Saison-PDF aus /media/dokumente/wertungen/, findet darin
die Vereinswertungs-Tabelle (Rang, Verein, 1./2./3.-Platzierungen je Lauf,
Gesamtpunkte) und sucht die Zeile fuer "MCH Singen". Das Ergebnis wird nach
/data/statistik.json geschrieben, das js/statistiken.js beim Laden der Seite
einliest.

Nach JEDEM Update der Wertungs-PDF (z. B. nach einem Renn-Wochenende)
ausfuehren:
    python tools/update_statistik.py
Danach WIE IMMER bei JS-Aenderungen (siehe README Abschnitt 9) - hier aber
NICHT noetig, da nur die JSON-Datei neu geschrieben wird, nicht statistiken.js.

Benoetigt: pip install pdfplumber
"""
import glob
import json
import os
import re
from datetime import date

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WERTUNGEN_DIR = os.path.join(ROOT, "media", "dokumente", "wertungen")
OUTPUT_PATH = os.path.join(ROOT, "data", "statistik.json")
VEREIN = "mch singen"


def finde_aktuelle_pdf():
    """Nimmt die bkcgesamtwertung_*.pdf mit dem hoechsten Jahr im Dateinamen."""
    kandidaten = glob.glob(os.path.join(WERTUNGEN_DIR, "bkcgesamtwertung_*.pdf"))
    if not kandidaten:
        raise SystemExit(f"Keine bkcgesamtwertung_*.pdf gefunden in: {WERTUNGEN_DIR}")

    def jahr_im_namen(pfad):
        treffer = re.search(r"(\d{4})", os.path.basename(pfad))
        return int(treffer.group(1)) if treffer else 0

    return max(kandidaten, key=jahr_im_namen)


def zur_zahl(zelle):
    """Wandelt eine Tabellenzelle robust in eine Zahl um (0 bei leer/Text)."""
    if not zelle:
        return 0
    text = zelle.strip().replace(",", ".")
    try:
        return round(float(text))
    except ValueError:
        return 0


def ist_vereinswertungs_tabelle(rows):
    """
    Die Vereinswertung ist die einzige Tabelle in der PDF, deren Kopfzeile
    "1./2./3./Pkt" (bzw. "Punkte") mehrfach wiederholt - einmal pro Renn-Lauf.
    Die Klassen-Tabellen (Platzierung je Fahrer) haben dieses Muster nicht.
    """
    for row in rows:
        text = " ".join((c or "") for c in row).lower()
        if text.count("pkt") >= 3 or text.count("punkte") >= 3:
            return True
    return False


def werte_verein_zeile_aus(rows):
    """Findet die Zeile von VEREIN und summiert Platz 1/2/3 ueber alle Laeufe."""
    for row in rows:
        zellen = [(c or "").strip() for c in row]
        if len(zellen) < 4:
            continue
        if not zellen[0].isdigit() or VEREIN not in zellen[1].lower():
            continue

        rang = int(zellen[0])
        zahlen = [zur_zahl(c) for c in zellen[2:]]
        gesamtpunkte = zahlen[-1]
        lauf_werte = zahlen[:-1]

        # Je Lauf 4 Spalten: [1. Platz, 2. Platz, 3. Platz, Punkte-des-Laufs]
        platz1 = sum(lauf_werte[i] for i in range(0, len(lauf_werte), 4))
        platz2 = sum(lauf_werte[i] for i in range(1, len(lauf_werte), 4))
        platz3 = sum(lauf_werte[i] for i in range(2, len(lauf_werte), 4))
        return rang, platz1, platz2, platz3, gesamtpunkte

    return None


def main():
    pdf_pfad = finde_aktuelle_pdf()

    vereinswertung = None
    with pdfplumber.open(pdf_pfad) as pdf:
        for page in pdf.pages:
            for table in page.find_tables():
                rows = table.extract()
                if ist_vereinswertungs_tabelle(rows):
                    vereinswertung = rows
                    break
            if vereinswertung:
                break

    if vereinswertung is None:
        raise SystemExit(
            "Die Vereinswertungs-Tabelle wurde in der PDF nicht gefunden.\n"
            "Hat sich der Aufbau der PDF geaendert? -> tools/update_statistik.py pruefen."
        )

    ergebnis = werte_verein_zeile_aus(vereinswertung)
    if ergebnis is None:
        raise SystemExit(f"'{VEREIN}' wurde in der Vereinswertungs-Tabelle nicht gefunden.")

    rang, platz1, platz2, platz3, punkte = ergebnis
    saison_treffer = re.search(r"(\d{4})", os.path.basename(pdf_pfad))

    # Bestehende Datei einlesen, damit von Hand gepflegte Werte (z. B. die
    # Diagramme unter "charts", siehe tools/statistiken_pflege.py) erhalten
    # bleiben - hier werden nur die aus der PDF berechneten Felder ersetzt.
    daten = {}
    if os.path.isfile(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                daten = json.load(f)
        except (json.JSONDecodeError, OSError):
            daten = {}

    daten.update({
        "saison": saison_treffer.group(1) if saison_treffer else None,
        "quelle": os.path.basename(pdf_pfad),
        "aktualisiert": date.today().isoformat(),
        "rang": rang,
        "podium": {"platz1": platz1, "platz2": platz2, "platz3": platz3},
        "punkte": punkte,
    })

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Quelle:      {os.path.basename(pdf_pfad)}")
    print(f"MCH Singen:  Rang {rang}, {punkte} Punkte, Podium 1./2./3. = "
          f"{platz1}/{platz2}/{platz3}")
    print(f"Geschrieben: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
