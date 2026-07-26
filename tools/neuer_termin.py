# -*- coding: utf-8 -*-
"""
Interaktiv einen neuen Renntermin (Kart oder Trial) validiert in
data/timer.txt bzw. data/timer_trial.txt eintragen, statt die Datei von
Hand mit Semikolons zu bearbeiten.

Ausfuehren: python tools/neuer_termin.py
"""
import os
import re
import sys
from datetime import date

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONATE_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]

MONAT_ALIASE = {}
for _i, (_en, _de) in enumerate(zip(MONATE_EN, MONATE_DE), start=1):
    MONAT_ALIASE[_en.lower()] = (_i, _en)
    MONAT_ALIASE[_de.lower()] = (_i, _en)
    MONAT_ALIASE[_en[:3].lower()] = (_i, _en)
    MONAT_ALIASE[_de[:3].lower()] = (_i, _en)

UMLAUT_ERSATZ = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue",
                                "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})


def frage(text, validierer=None, pflicht=True):
    while True:
        antwort = input(text).strip()
        if not antwort:
            if pflicht:
                print("  -> Darf nicht leer sein.")
                continue
            return antwort
        if validierer:
            fehler = validierer(antwort)
            if fehler:
                print(f"  -> {fehler}")
                continue
        return antwort


def slug(text):
    return text.translate(UMLAUT_ERSATZ).lower().replace(" ", "")


def lade_bekannte_orte(pfad):
    """Liest eine timer-Datei und sammelt bekannte (Verein, Ort) -> Maps-Link."""
    bekannte = {}
    reihenfolge = []
    if os.path.exists(pfad):
        with open(pfad, "r", encoding="utf-8") as f:
            for zeile in f:
                teile = zeile.strip().split(";")
                if len(teile) < 7:
                    continue
                schluessel = (teile[4], teile[5])
                if schluessel not in bekannte:
                    bekannte[schluessel] = teile[6]
                    reihenfolge.append(schluessel)
    return bekannte, reihenfolge


def waehle_verein_ort(zieldatei, mehrere_orte_erwartet):
    bekannte, reihenfolge = lade_bekannte_orte(zieldatei)

    if not mehrere_orte_erwartet and reihenfolge:
        verein, ort = reihenfolge[0]
        print(f"\nVerein/Ort (aus bestehenden Terminen uebernommen): {verein} {ort}")
        link = bekannte[(verein, ort)]
        neuer_link = frage(f"Maps-Link uebernehmen [{link}] (Enter = ok, sonst neuen Link eingeben): ", pflicht=False)
        return verein, ort, (neuer_link or link)

    print("\nBekannte Vereine/Orte:")
    for i, (verein, ort) in enumerate(reihenfolge, start=1):
        print(f"  {i}) {verein} {ort}")
    neu_idx = len(reihenfolge) + 1
    print(f"  {neu_idx}) Neuer Verein/Ort")

    auswahl = frage(
        f"\nAuswahl (1-{neu_idx}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= neu_idx else "Ungueltige Auswahl."
    )
    idx = int(auswahl)

    if idx <= len(reihenfolge):
        verein, ort = reihenfolge[idx - 1]
        link = bekannte[(verein, ort)]
        neuer_link = frage(f"  Maps-Link uebernehmen [{link}] (Enter = ok, sonst neuen Link eingeben): ", pflicht=False)
        return verein, ort, (neuer_link or link)

    verein = frage("  Verein-Kuerzel (z. B. AC, MSC, MSG, MCH): ")
    ort = frage("  Ort: ")
    link = frage("  Google-Maps-Link: ", lambda a: None if a.startswith("http") else "Muss mit http(s):// beginnen.")
    return verein, ort, link


def frage_datum():
    tag = frage("\nTag (1-31): ", lambda a: None if a.isdigit() and 1 <= int(a) <= 31 else "Muss eine Zahl von 1-31 sein.")

    def monat_validierer(a):
        return None if a.lower() in MONAT_ALIASE else "Unbekannter Monat (Deutsch oder Englisch, z. B. Juli/July)."
    monat_eingabe = frage("Monat (Deutsch oder Englisch, z. B. Juli): ", monat_validierer)
    monat_nr, monat_en = MONAT_ALIASE[monat_eingabe.lower()]

    jahr = frage("Jahr (z. B. 2026): ", lambda a: None if a.isdigit() and len(a) == 4 else "Muss eine 4-stellige Jahreszahl sein.")

    while True:
        try:
            date(int(jahr), monat_nr, int(tag))
            break
        except ValueError:
            print(f"  -> {tag}.{monat_nr}.{jahr} ist kein gueltiges Kalenderdatum.")
            tag = frage("Tag (1-31): ", lambda a: None if a.isdigit() and 1 <= int(a) <= 31 else "Muss eine Zahl von 1-31 sein.")

    uhrzeit = frage(
        "Uhrzeit (HH:MM, z. B. 09:00): ",
        lambda a: None if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", a) else "Format muss HH:MM sein (z. B. 09:00)."
    )
    return tag.zfill(2), monat_en, jahr, uhrzeit


def lade_letzten_pdf_link(zieldatei, verein, ort):
    """Prueft, ob bisherige Termine fuer (verein, ort) sich eine PDF teilen
    (z. B. eine Saison-PDF wie bei Trial) oder jeweils eigene PDFs haben
    (z. B. eine Kurzausschreibung pro Rennen wie bei Kart)."""
    if not os.path.exists(zieldatei):
        return None, False
    links = []
    with open(zieldatei, "r", encoding="utf-8") as f:
        for zeile in f:
            teile = zeile.strip().split(";")
            if len(teile) >= 8 and teile[4] == verein and teile[5] == ort:
                links.append(teile[7])
    if not links:
        return None, False
    geteilt = len(links) > 1 and len(set(links)) == 1
    return links[-1], geteilt


def frage_pdf(verein, ort, jahr, zieldatei):
    letzter_link, geteilt = lade_letzten_pdf_link(zieldatei, verein, ort)

    if geteilt and letzter_link:
        print(f"\nBisherige Termine fuer {verein} {ort} nutzen alle dieselbe PDF:")
        print(f"  {letzter_link}")
        eingabe = frage(
            "Uebernehmen? (Enter = ja, eigenen Pfad eingeben, oder n = keine PDF): ",
            pflicht=False
        )
        if eingabe.lower() in ("n", "nein"):
            return ""
        pdf_link = eingabe if eingabe else letzter_link
    else:
        vorschlag = f"kurzausschreibung{slug(verein)}{slug(ort)}{jahr}.pdf"
        print(f"\nVorgeschlagener PDF-Dateiname: {vorschlag}")
        eingabe = frage(
            "PDF-Pfad uebernehmen? (Enter = ja, eigenen Pfad eingeben, oder n = noch keine PDF): ",
            pflicht=False
        )
        if eingabe.lower() in ("n", "nein"):
            return ""
        pdf_link = eingabe if eingabe else f"media/dokumente/{vorschlag}"

    if pdf_link and not re.fullmatch(r"[a-z0-9/_.\-]+", pdf_link):
        print("  ACHTUNG: Der Pfad enthaelt Grossbuchstaben, Umlaute oder Sonderzeichen -")
        print("  GitHub-Server sind streng! Bitte beim Hochladen auf exakt diesen Namen achten.")
    return pdf_link


def pruefe_duplikat(zieldatei, tag, monat_en, jahr, verein):
    if not os.path.exists(zieldatei):
        return True
    with open(zieldatei, "r", encoding="utf-8") as f:
        bestehende = [z.strip() for z in f if z.strip()]
    for b in bestehende:
        teile = b.split(";")
        if len(teile) >= 5 and teile[0] == tag and teile[1] == monat_en and teile[2] == jahr and teile[4] == verein:
            print(f"\nACHTUNG: Es gibt schon einen Eintrag am {tag}.{monat_en}.{jahr} fuer '{verein}':")
            print(f"  {b}")
            weiter = frage("Trotzdem eintragen? (j/n): ", lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n.")
            return weiter.lower() == "j"
    return True


def termin_eintragen():
    print("\n1) Kart\n2) Trial")
    sport = frage("Welche Sportart? (1/2): ", lambda a: None if a in ("1", "2") else "Bitte 1 oder 2 eingeben.")

    if sport == "1":
        zieldatei = os.path.join(ROOT, "data", "timer.txt")
        verein, ort, link = waehle_verein_ort(zieldatei, mehrere_orte_erwartet=True)
    else:
        zieldatei = os.path.join(ROOT, "data", "timer_trial.txt")
        verein, ort, link = waehle_verein_ort(zieldatei, mehrere_orte_erwartet=False)

    tag, monat_en, jahr, uhrzeit = frage_datum()
    pdf_link = frage_pdf(verein, ort, jahr, zieldatei)

    if not pruefe_duplikat(zieldatei, tag, monat_en, jahr, verein):
        print("Abgebrochen.")
        return

    zeile = ";".join([tag, monat_en, jahr, uhrzeit, verein, ort, link, pdf_link])

    print("\nNeue Zeile:")
    print(f"  {zeile}")
    bestaetigt = frage("In die Datei eintragen? (j/n): ", lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n.")
    if bestaetigt.lower() != "j":
        print("Abgebrochen, nichts gespeichert.")
        return

    with open(zieldatei, "a", encoding="utf-8", newline="\n") as f:
        f.write(zeile + "\n")
    print(f"\nGespeichert in {os.path.relpath(zieldatei, ROOT)}")


def main():
    print("=" * 60)
    print("  Neuen Renntermin eintragen")
    print("=" * 60)
    while True:
        termin_eintragen()
        weiter = frage("\nWeiteren Termin eintragen? (j/n): ", lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n.")
        if weiter.lower() != "j":
            break
    print("\nFertig.")


if __name__ == "__main__":
    main()
