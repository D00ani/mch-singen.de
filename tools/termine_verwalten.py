# -*- coding: utf-8 -*-
"""
Interaktiv Renntermine (Kart oder Trial) in data/timer.txt bzw.
data/timer_trial.txt hinzufuegen, bearbeiten oder loeschen - statt die
Dateien von Hand mit Semikolons zu bearbeiten.

Ausfuehren: python tools/termine_verwalten.py
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

TAG_VALIDIERER = lambda a: None if a.isdigit() and 1 <= int(a) <= 31 else "Muss eine Zahl von 1-31 sein."
JAHR_VALIDIERER = lambda a: None if a.isdigit() and len(a) == 4 else "Muss eine 4-stellige Jahreszahl sein."
UHRZEIT_VALIDIERER = lambda a: None if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", a) else "Format muss HH:MM sein (z. B. 09:00)."
JN_VALIDIERER = lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n."


def monat_validierer(a):
    return None if a.lower() in MONAT_ALIASE else "Unbekannter Monat (Deutsch oder Englisch, z. B. Juli/July)."


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


def frage_mit_default(text, default, validierer=None, leer_erlaubt=False):
    """Wie frage(), zeigt aber den aktuellen Wert als Default (Enter = behalten).
    Bei leer_erlaubt=True loescht '-' den Wert (leeres Feld)."""
    while True:
        antwort = input(f"{text} [{default}]: ").strip()
        if not antwort:
            return default
        if leer_erlaubt and antwort == "-":
            return ""
        if validierer:
            fehler = validierer(antwort)
            if fehler:
                print(f"  -> {fehler}")
                continue
        return antwort


def slug(text):
    return text.translate(UMLAUT_ERSATZ).lower().replace(" ", "")


def lade_zeilen(zieldatei):
    if not os.path.exists(zieldatei):
        return []
    with open(zieldatei, "r", encoding="utf-8") as f:
        return [z.strip() for z in f if z.strip()]


def erkenne_zeilenende(zieldatei):
    """Behaelt die bestehende Zeilenende-Konvention der Datei bei (dieses
    Projekt nutzt auf Windows durchgaengig CRLF fuer die data/*.txt-Dateien)."""
    if os.path.exists(zieldatei):
        with open(zieldatei, "rb") as f:
            if b"\r\n" in f.read():
                return "\r\n"
    return "\r\n"


def speichere_zeilen(zieldatei, zeilen):
    zeilenende = erkenne_zeilenende(zieldatei)
    with open(zieldatei, "w", encoding="utf-8", newline="") as f:
        for z in zeilen:
            f.write(z + zeilenende)


def zeige_zeilen(zeilen):
    for i, z in enumerate(zeilen, start=1):
        teile = z.split(";")
        if len(teile) >= 6:
            tag, monat, jahr, uhrzeit, verein, ort = teile[:6]
            print(f"  {i}) {tag}.{monat}.{jahr} {uhrzeit} - {verein} {ort}")
        else:
            print(f"  {i}) {z}")


def waehle_zeile(zeilen, aktion_text):
    zeige_zeilen(zeilen)
    auswahl = frage(
        f"\nWelchen Termin {aktion_text}? (1-{len(zeilen)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(zeilen) else "Ungueltige Auswahl."
    )
    return int(auswahl) - 1


def lade_bekannte_orte(zeilen):
    """Sammelt bekannte (Verein, Ort) -> Maps-Link aus den Zeilen einer Datei."""
    bekannte = {}
    reihenfolge = []
    for zeile in zeilen:
        teile = zeile.split(";")
        if len(teile) < 7:
            continue
        schluessel = (teile[4], teile[5])
        if schluessel not in bekannte:
            bekannte[schluessel] = teile[6]
            reihenfolge.append(schluessel)
    return bekannte, reihenfolge


def waehle_verein_ort(zeilen, mehrere_orte_erwartet):
    bekannte, reihenfolge = lade_bekannte_orte(zeilen)

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


def korrigiere_datum(tag, monat_nr, jahr):
    """Prueft, ob Tag/Monat/Jahr ein echtes Kalenderdatum ergeben (faengt
    z. B. 30. Februar ab) und fragt bei Bedarf nur den Tag erneut ab."""
    while True:
        try:
            date(int(jahr), monat_nr, int(tag))
            return tag
        except ValueError:
            print(f"  -> {tag}.{monat_nr}.{jahr} ist kein gueltiges Kalenderdatum.")
            tag = frage("Tag (1-31): ", TAG_VALIDIERER)


def frage_datum():
    tag = frage("\nTag (1-31): ", TAG_VALIDIERER)
    monat_eingabe = frage("Monat (Deutsch oder Englisch, z. B. Juli): ", monat_validierer)
    monat_nr, monat_en = MONAT_ALIASE[monat_eingabe.lower()]
    jahr = frage("Jahr (z. B. 2026): ", JAHR_VALIDIERER)
    tag = korrigiere_datum(tag, monat_nr, jahr)
    uhrzeit = frage("Uhrzeit (HH:MM, z. B. 09:00): ", UHRZEIT_VALIDIERER)
    return tag.zfill(2), monat_en, jahr, uhrzeit


def lade_letzten_pdf_link(zeilen, verein, ort, ausser_index=None):
    """Prueft, ob bisherige Termine fuer (verein, ort) sich eine PDF teilen
    (z. B. eine Saison-PDF wie bei Trial) oder jeweils eigene PDFs haben
    (z. B. eine Kurzausschreibung pro Rennen wie bei Kart)."""
    links = []
    for i, zeile in enumerate(zeilen):
        if i == ausser_index:
            continue
        teile = zeile.split(";")
        if len(teile) >= 8 and teile[4] == verein and teile[5] == ort:
            links.append(teile[7])
    if not links:
        return None, False
    geteilt = len(links) > 1 and len(set(links)) == 1
    return links[-1], geteilt


def frage_pdf(verein, ort, jahr, zeilen, ausser_index=None):
    letzter_link, geteilt = lade_letzten_pdf_link(zeilen, verein, ort, ausser_index)

    if geteilt and letzter_link:
        print(f"\nBisherige Termine fuer {verein} {ort} nutzen alle dieselbe PDF:")
        print(f"  {letzter_link}")
        eingabe = frage("Uebernehmen? (Enter = ja, eigenen Pfad eingeben, oder n = keine PDF): ", pflicht=False)
        if eingabe.lower() in ("n", "nein"):
            return ""
        pdf_link = eingabe if eingabe else letzter_link
    else:
        vorschlag = f"kurzausschreibung{slug(verein)}{slug(ort)}{jahr}.pdf"
        print(f"\nVorgeschlagener PDF-Dateiname: {vorschlag}")
        eingabe = frage("PDF-Pfad uebernehmen? (Enter = ja, eigenen Pfad eingeben, oder n = noch keine PDF): ", pflicht=False)
        if eingabe.lower() in ("n", "nein"):
            return ""
        pdf_link = eingabe if eingabe else f"media/dokumente/{vorschlag}"

    if pdf_link and not re.fullmatch(r"[a-z0-9/_.\-]+", pdf_link):
        print("  ACHTUNG: Der Pfad enthaelt Grossbuchstaben, Umlaute oder Sonderzeichen -")
        print("  GitHub-Server sind streng! Bitte beim Hochladen auf exakt diesen Namen achten.")
    return pdf_link


def pruefe_duplikat(zeilen, tag, monat_en, jahr, verein, ausser_index=None):
    for i, b in enumerate(zeilen):
        if i == ausser_index:
            continue
        teile = b.split(";")
        if len(teile) >= 5 and teile[0] == tag and teile[1] == monat_en and teile[2] == jahr and teile[4] == verein:
            print(f"\nACHTUNG: Es gibt schon einen Eintrag am {tag}.{monat_en}.{jahr} fuer '{verein}':")
            print(f"  {b}")
            weiter = frage("Trotzdem speichern? (j/n): ", JN_VALIDIERER)
            return weiter.lower() == "j"
    return True


def termin_hinzufuegen(zieldatei, mehrere_orte_erwartet):
    zeilen = lade_zeilen(zieldatei)
    verein, ort, link = waehle_verein_ort(zeilen, mehrere_orte_erwartet)
    tag, monat_en, jahr, uhrzeit = frage_datum()
    pdf_link = frage_pdf(verein, ort, jahr, zeilen)

    if not pruefe_duplikat(zeilen, tag, monat_en, jahr, verein):
        print("Abgebrochen.")
        return

    zeile = ";".join([tag, monat_en, jahr, uhrzeit, verein, ort, link, pdf_link])
    print("\nNeue Zeile:")
    print(f"  {zeile}")
    if frage("In die Datei eintragen? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen, nichts gespeichert.")
        return

    zeilen.append(zeile)
    speichere_zeilen(zieldatei, zeilen)
    print(f"\nGespeichert in {os.path.relpath(zieldatei, ROOT)}")


def termin_bearbeiten(zieldatei):
    zeilen = lade_zeilen(zieldatei)
    if not zeilen:
        print("\nKeine Termine vorhanden.")
        return

    idx = waehle_zeile(zeilen, "bearbeiten")
    alt = zeilen[idx].split(";")
    while len(alt) < 8:
        alt.append("")
    alt_tag, alt_monat, alt_jahr, alt_uhrzeit, alt_verein, alt_ort, alt_link, alt_pdf = alt[:8]

    print(f"\nAktuell: {zeilen[idx]}")
    print("Neue Werte eingeben (Enter = aktuellen Wert behalten).\n")

    tag = frage_mit_default("Tag (1-31)", alt_tag, TAG_VALIDIERER)
    monat_eingabe = frage_mit_default("Monat (Deutsch oder Englisch)", alt_monat, monat_validierer)
    monat_nr, monat_en = MONAT_ALIASE[monat_eingabe.lower()]
    jahr = frage_mit_default("Jahr", alt_jahr, JAHR_VALIDIERER)
    tag = korrigiere_datum(tag, monat_nr, jahr).zfill(2)
    uhrzeit = frage_mit_default("Uhrzeit (HH:MM)", alt_uhrzeit, UHRZEIT_VALIDIERER)
    verein = frage_mit_default("Verein-Kuerzel", alt_verein)
    ort = frage_mit_default("Ort", alt_ort)
    link = frage_mit_default("Maps-Link", alt_link, lambda a: None if a.startswith("http") else "Muss mit http(s):// beginnen.")
    pdf_link = frage_mit_default("PDF-Pfad ('-' = leeren)", alt_pdf, leer_erlaubt=True)

    if pdf_link and not re.fullmatch(r"[a-z0-9/_.\-]+", pdf_link):
        print("  ACHTUNG: Der Pfad enthaelt Grossbuchstaben, Umlaute oder Sonderzeichen -")
        print("  GitHub-Server sind streng! Bitte beim Hochladen auf exakt diesen Namen achten.")

    if not pruefe_duplikat(zeilen, tag, monat_en, jahr, verein, ausser_index=idx):
        print("Abgebrochen.")
        return

    neue_zeile = ";".join([tag, monat_en, jahr, uhrzeit, verein, ort, link, pdf_link])
    print(f"\nAlt: {zeilen[idx]}")
    print(f"Neu: {neue_zeile}")
    if frage("Aendern? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen, nichts geaendert.")
        return

    zeilen[idx] = neue_zeile
    speichere_zeilen(zieldatei, zeilen)
    print(f"\nGespeichert in {os.path.relpath(zieldatei, ROOT)}")


def termin_loeschen(zieldatei):
    zeilen = lade_zeilen(zieldatei)
    if not zeilen:
        print("\nKeine Termine vorhanden.")
        return

    idx = waehle_zeile(zeilen, "loeschen")
    print(f"\nLoeschen: {zeilen[idx]}")
    if frage("Wirklich loeschen? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen, nichts geloescht.")
        return

    del zeilen[idx]
    speichere_zeilen(zieldatei, zeilen)
    print(f"\nGeloescht. {os.path.relpath(zieldatei, ROOT)} aktualisiert.")


def sportart_waehlen():
    print("\n1) Kart\n2) Trial")
    sport = frage("Welche Sportart? (1/2): ", lambda a: None if a in ("1", "2") else "Bitte 1 oder 2 eingeben.")
    if sport == "1":
        return os.path.join(ROOT, "data", "timer.txt"), True
    return os.path.join(ROOT, "data", "timer_trial.txt"), False


def main():
    print("=" * 60)
    print("  Renntermine verwalten")
    print("=" * 60)

    while True:
        zieldatei, mehrere_orte = sportart_waehlen()

        print("\n1) Neuen Termin hinzufuegen\n2) Termin bearbeiten\n3) Termin loeschen")
        aktion = frage("Was moechtest du tun? (1-3): ", lambda a: None if a in ("1", "2", "3") else "Bitte 1, 2 oder 3.")

        if aktion == "1":
            termin_hinzufuegen(zieldatei, mehrere_orte)
        elif aktion == "2":
            termin_bearbeiten(zieldatei)
        else:
            termin_loeschen(zieldatei)

        weiter = frage("\nNoch etwas tun (weiterer Termin/Datei)? (j/n): ", JN_VALIDIERER)
        if weiter.lower() != "j":
            break

    print("\nFertig.")


if __name__ == "__main__":
    main()
