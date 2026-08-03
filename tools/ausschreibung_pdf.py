# -*- coding: utf-8 -*-
"""
Ausschreibungs-PDFs einpflegen.

Beim Eintragen eines Renntermins wird der PDF-Pfad schon angekuendigt -
die Datei selbst kommt oft erst Wochen spaeter per Mail. Bis dahin bleibt
der Download-Button unsichtbar. Dieses Werkzeug schliesst die Luecke:
es zeigt, welche PDFs noch fehlen, kopiert die Datei an genau die
angekuendigte Stelle und raeumt heikle Dateinamen auf.

Ausfuehren: python tools/ausschreibung_pdf.py
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import termine_verwalten as tv

ROOT = h.ROOT
TERMIN_DATEIEN = [
    (os.path.join(ROOT, "data", "timer.txt"), "Kart"),
    (os.path.join(ROOT, "data", "timer_trial.txt"), "Trial"),
]

PDF_SPALTE = 7          # Spalte mit dem PDF-Pfad in timer.txt
SAUBER_MUSTER = re.compile(r"[a-z0-9/_.\-]+")

UMLAUT_ERSATZ = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue",
    "ß": "ss", " ": "-",
})


# ------------------------------------------------------------------
# Termine und ihre PDFs einsammeln
# ------------------------------------------------------------------

def lade_termine():
    """Alle Termine als Liste von (datei, index, teile)."""
    termine = []
    for pfad, sportart in TERMIN_DATEIEN:
        for index, zeile in enumerate(h.lies_zeilen(pfad)):
            teile = zeile.split(";")
            if len(teile) >= 6:
                termine.append({"datei": pfad, "sportart": sportart,
                                "index": index, "teile": teile, "zeile": zeile})
    return termine


def pdf_pfad(termin):
    teile = termin["teile"]
    return teile[PDF_SPALTE].strip() if len(teile) > PDF_SPALTE else ""


def pdf_existiert(relativer_pfad):
    if not relativer_pfad:
        return False
    return os.path.isfile(os.path.join(ROOT, relativer_pfad.lstrip("/")))


def fehlende_ausschreibungen():
    """Angekuendigte, aber noch nicht hochgeladene PDFs - nach Pfad
    gruppiert, weil sich mehrere Termine eine PDF teilen koennen."""
    gruppen = {}
    for termin in lade_termine():
        pfad = pdf_pfad(termin)
        if pfad and not pdf_existiert(pfad):
            gruppen.setdefault(pfad, []).append(termin)
    return gruppen


def beschreibe_gruppe(pfad, termine):
    wann = ", ".join(tv.beschreibe_termin(t["zeile"]) for t in termine)
    return f"{pfad}\n     fuer: {wann}"


# ------------------------------------------------------------------
# PDF einpflegen
# ------------------------------------------------------------------

def ist_pdf(pfad):
    try:
        with open(pfad, "rb") as datei:
            return datei.read(5) == b"%PDF-"
    except OSError:
        return False


def bereinige_eingabe(eingabe):
    """Aus dem Explorer gezogene Pfade kommen oft in Anfuehrungszeichen."""
    return eingabe.strip().strip('"').strip("'")


def frage_quelldatei():
    """Fragt, wo die PDF gerade liegt (Downloads, Desktop, USB-Stick ...)."""
    print("\nWo liegt die PDF-Datei gerade?")
    print("Tipp: Die Datei im Explorer suchen, mit Rechtsklick 'Als Pfad kopieren'")
    print("und hier einfuegen (Rechtsklick ins Fenster).")

    while True:
        eingabe = bereinige_eingabe(h.frage("\nPfad zur PDF: "))
        quelle = os.path.expanduser(os.path.expandvars(eingabe))

        if not os.path.isfile(quelle):
            print(f"  -> Diese Datei gibt es nicht: {quelle}")
            continue
        if not ist_pdf(quelle):
            print("  -> Das ist keine PDF-Datei (der Inhalt sieht nicht danach aus).")
            if not h.frage_ja("  Trotzdem verwenden? (j/n): "):
                continue
        return quelle


def sauberer_name(name):
    """Macht aus 'Kurzausschreibung MSC Steißlingen.pdf' einen Namen, der
    auf dem Linux-Server von GitHub garantiert gefunden wird."""
    return name.translate(UMLAUT_ERSATZ).lower()


def pruefe_zielname(zielpfad):
    """Warnt bei Zeichen, die auf dem Server Aerger machen, und bietet
    einen sauberen Namen an. Gibt den (evtl. neuen) Pfad zurueck."""
    if SAUBER_MUSTER.fullmatch(zielpfad):
        return zielpfad

    vorschlag = sauberer_name(zielpfad)
    print(f"\nDer angekuendigte Name enthaelt Zeichen, die beim Hochladen leicht")
    print(f"schiefgehen (Grossbuchstaben, Umlaute oder Leerzeichen):")
    print(f"  bisher:  {zielpfad}")
    print(f"  sauber:  {vorschlag}")
    if h.frage_ja("Sauberen Namen verwenden? (aendert auch den Eintrag im Termin) (j/n): "):
        return vorschlag
    return zielpfad


def schreibe_pdf_pfad(termine, neuer_pfad):
    """Traegt einen geaenderten PDF-Pfad in die Termin-Dateien zurueck."""
    je_datei = {}
    for termin in termine:
        je_datei.setdefault(termin["datei"], []).append(termin)

    for datei, betroffene in je_datei.items():
        zeilen = h.lies_zeilen(datei)
        for termin in betroffene:
            teile = zeilen[termin["index"]].split(";")
            while len(teile) <= PDF_SPALTE:
                teile.append("")
            teile[PDF_SPALTE] = neuer_pfad
            zeilen[termin["index"]] = ";".join(teile)
        h.schreibe_zeilen(datei, zeilen)
        print(f"  {os.path.relpath(datei, ROOT)} aktualisiert "
              f"({len(betroffene)} Termin(e))")


def pdf_einpflegen():
    gruppen = fehlende_ausschreibungen()
    if not gruppen:
        print("\nAlle angekuendigten PDFs sind vorhanden - nichts zu tun.")
        print("(Eine PDF zu einem Termin hinzufuegen geht ueber")
        print(" 'Renntermine verwalten' -> 'Termin bearbeiten'.)")
        return

    print(f"\nEs fehlen noch {len(gruppen)} PDF-Datei(en):")
    pfade = list(gruppen)
    index = h.waehle_aus_liste(pfade, "hochladen",
                               lambda p: beschreibe_gruppe(p, gruppen[p]))
    if index is None:
        return

    zielpfad = pfade[index]
    betroffene = gruppen[zielpfad]

    quelle = frage_quelldatei()
    neuer_zielpfad = pruefe_zielname(zielpfad)

    ziel = os.path.join(ROOT, neuer_zielpfad.lstrip("/"))
    print("\nEs wird kopiert:")
    print(f"  von:  {quelle}")
    print(f"  nach: {os.path.relpath(ziel, ROOT)}")
    if os.path.isfile(ziel):
        print("  ACHTUNG: An dieser Stelle liegt bereits eine Datei - sie wird ersetzt.")
    if not h.frage_ja("\nKopieren? (j/n): "):
        print("Abgebrochen.")
        return

    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    if os.path.isfile(ziel):
        h.sicherung_anlegen(ziel)
    shutil.copy2(quelle, ziel)
    print(f"\nKopiert ({os.path.getsize(ziel) // 1024} KB).")

    if neuer_zielpfad != zielpfad:
        schreibe_pdf_pfad(betroffene, neuer_zielpfad)

    print("\nFertig - der Download-Button ist jetzt sichtbar bei:")
    for termin in betroffene:
        print(f"  {termin['sportart']}: {tv.beschreibe_termin(termin['zeile'])}")


# ------------------------------------------------------------------
# Namen aufraeumen
# ------------------------------------------------------------------

def heikle_namen():
    """Angekuendigte PDF-Pfade mit Zeichen, die auf dem Server stolpern."""
    treffer = {}
    for termin in lade_termine():
        pfad = pdf_pfad(termin)
        if pfad and not SAUBER_MUSTER.fullmatch(pfad):
            treffer.setdefault(pfad, []).append(termin)
    return treffer


def namen_aufraeumen():
    treffer = heikle_namen()
    if not treffer:
        print("\nAlle PDF-Pfade sind sauber geschrieben - nichts zu tun.")
        return

    print(f"\n{len(treffer)} PDF-Pfad(e) mit heiklen Zeichen:")
    print("(Windows ist da tolerant, der GitHub-Server nicht.)")

    for pfad, termine in treffer.items():
        vorschlag = sauberer_name(pfad)
        print("\n" + "-" * 60)
        print(f"  bisher:  {pfad}")
        print(f"  sauber:  {vorschlag}")
        print(f"  betrifft {len(termine)} Termin(e)")

        vorhanden = os.path.join(ROOT, pfad.lstrip("/"))
        if not os.path.isfile(vorhanden):
            print("  Die Datei ist noch nicht hochgeladen - es aendert sich nur der Eintrag.")

        try:
            if not h.frage_ja("  Umbenennen? (j/n): "):
                continue
        except h.Zurueck:
            return

        if os.path.isfile(vorhanden):
            neu = os.path.join(ROOT, vorschlag.lstrip("/"))
            os.makedirs(os.path.dirname(neu), exist_ok=True)
            h.sicherung_anlegen(vorhanden)
            os.replace(vorhanden, neu)
            print(f"  Datei umbenannt nach {vorschlag}")
        schreibe_pdf_pfad(termine, vorschlag)


def uebersicht():
    gruppen = fehlende_ausschreibungen()
    alle = lade_termine()
    mit_pdf = [t for t in alle if pdf_pfad(t)]
    ohne_pdf = [t for t in alle if not pdf_pfad(t)]

    print(f"\n{len(alle)} Termine insgesamt:")
    print(f"  {len(mit_pdf) - sum(len(v) for v in gruppen.values())} mit vorhandener PDF")
    print(f"  {sum(len(v) for v in gruppen.values())} mit angekuendigter, fehlender PDF")
    print(f"  {len(ohne_pdf)} ohne PDF-Angabe")

    if gruppen:
        print("\nEs fehlen:")
        for pfad, termine in gruppen.items():
            print(f"  {beschreibe_gruppe(pfad, termine)}")


def main():
    print("=" * 60)
    print("  Ausschreibungs-PDF einpflegen")
    print("=" * 60)

    while True:
        aktion = h.menue("Was moechtest du tun?", [
            ("Fehlende PDF hochladen und mit dem Termin verbinden", pdf_einpflegen),
            ("Uebersicht: welche PDFs fehlen noch?", uebersicht),
            ("Heikle Dateinamen aufraeumen (Umlaute, Grossbuchstaben)", namen_aufraeumen),
        ])
        if aktion is None:
            break
        h.fuehre_aus(aktion)

    print("\nFertig.")


if __name__ == "__main__":
    main()
