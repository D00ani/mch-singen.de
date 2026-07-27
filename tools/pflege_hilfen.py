# -*- coding: utf-8 -*-
"""
Gemeinsame Bausteine fuer alle Pflege-Werkzeuge:
Eingabe-Abfragen mit Pruefung, Datei-Lesen/Schreiben unter Beibehaltung der
Zeilenenden und eine automatische Sicherung vor jeder Aenderung (damit sich
ein Vertipper ueber "Rueckgaengig" zurueckholen laesst).
"""
import os
import re
import shutil
import sys
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SICHERUNGS_DIR = os.path.join(ROOT, ".pflege-sicherungen")
PROTOKOLL = os.path.join(SICHERUNGS_DIR, "protokoll.txt")
MAX_SICHERUNGEN = 50


# ------------------------------------------------------------------
# Eingaben
# ------------------------------------------------------------------

JN_VALIDIERER = lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n."
TAG_VALIDIERER = lambda a: None if a.isdigit() and 1 <= int(a) <= 31 else "Muss eine Zahl von 1-31 sein."
JAHR_VALIDIERER = lambda a: None if a.isdigit() and len(a) == 4 else "Muss eine 4-stellige Jahreszahl sein."
UHRZEIT_VALIDIERER = lambda a: None if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", a) else "Format muss HH:MM sein (z. B. 09:00)."
ZAHL_VALIDIERER = lambda a: None if a.isdigit() else "Muss eine Zahl sein."
LINK_VALIDIERER = lambda a: None if a.startswith("http") else "Muss mit http(s):// beginnen."

ZURUECK_TASTE = "x"


class Zurueck(Exception):
    """Wird ausgeloest, wenn 'x' eingegeben wird - ein Schritt zurueck."""


def _ist_zurueck(antwort):
    return antwort.lower() == ZURUECK_TASTE


def frage(text, validierer=None, pflicht=True):
    """Fragt einen Wert ab. Mit 'x' geht es einen Schritt zurueck."""
    while True:
        antwort = input(text).strip()
        if _ist_zurueck(antwort):
            raise Zurueck()
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
    """Enter = aktuellen Wert behalten, 'x' = ein Schritt zurueck.
    Bei leer_erlaubt=True leert '-' den Wert."""
    while True:
        antwort = input(f"{text} [{default}]: ").strip()
        if _ist_zurueck(antwort):
            raise Zurueck()
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


def frage_ja(text):
    return frage(text, JN_VALIDIERER).lower() == "j"


def waehle_aus_liste(eintraege, aktion_text, beschriftung=str):
    """Zeigt eine nummerierte Liste und gibt den gewaehlten Index zurueck
    (oder None, wenn die Liste leer ist)."""
    if not eintraege:
        print("\nKeine Eintraege vorhanden.")
        return None
    for i, e in enumerate(eintraege, start=1):
        print(f"  {i}) {beschriftung(e)}")
    auswahl = frage(
        f"\nWelchen Eintrag {aktion_text}? (1-{len(eintraege)}, x = zurueck): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(eintraege) else "Ungueltige Auswahl."
    )
    return int(auswahl) - 1


def waehle_option(titel, optionen, beschriftung=str):
    """Nummerierte Auswahl mit eigener Ueberschrift. 'x' geht zurueck."""
    print(f"\n{titel}")
    for i, option in enumerate(optionen, start=1):
        print(f"  {i}) {beschriftung(option)}")
    wahl = frage(
        f"Auswahl (1-{len(optionen)}, x = zurueck): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(optionen) else "Ungueltige Auswahl."
    )
    return int(wahl) - 1


def menue(titel, punkte, mit_zurueck=True):
    """punkte: Liste von (Beschriftung, Funktion). Gibt die gewaehlte Funktion
    zurueck oder None bei 0 bzw. 'x'."""
    print(f"\n{titel}")
    for i, (beschriftung, _) in enumerate(punkte, start=1):
        print(f"  {i}) {beschriftung}")
    if mit_zurueck:
        print("  0) Zurueck")
    gueltig = {str(i) for i in range(1, len(punkte) + 1)} | ({"0"} if mit_zurueck else set())
    try:
        wahl = frage(
            f"Auswahl{' (x = zurueck)' if mit_zurueck else ''}: ",
            lambda a: None if a in gueltig else "Ungueltige Auswahl."
        )
    except Zurueck:
        return None
    if wahl == "0":
        return None
    return punkte[int(wahl) - 1][1]


def formular(felder):
    """Fragt mehrere Werte nacheinander ab. Mit 'x' geht es jeweils EIN Feld
    zurueck; 'x' im ersten Feld bricht das Formular ab (Rueckgabe None).

    felder: Liste von (schluessel, funktion(bisherige_werte) -> wert).
    """
    werte = {}
    position = 0
    while position < len(felder):
        schluessel, abfrage = felder[position]
        try:
            werte[schluessel] = abfrage(werte)
            position += 1
        except Zurueck:
            if position == 0:
                return None
            position -= 1
            werte.pop(felder[position][0], None)
            print("  (ein Schritt zurueck)")
    return werte


def fuehre_aus(funktion, *args, **kwargs):
    """Ruft eine Aktion auf und faengt ein 'x' ab, das bis hierher
    durchgereicht wurde - dann landet man wieder im Menue."""
    try:
        return funktion(*args, **kwargs)
    except Zurueck:
        print("  (zurueck)")
        return None


# ------------------------------------------------------------------
# Dateien lesen/schreiben (Zeilenenden bleiben erhalten)
# ------------------------------------------------------------------

def lies_datei(pfad):
    with open(pfad, "r", encoding="utf-8", newline="") as f:
        return f.read()


def schreibe_datei(pfad, inhalt, sichern=True):
    """Schreibt die Datei unveraendert (newline='') und legt vorher eine
    Sicherung an, damit die Aenderung rueckgaengig gemacht werden kann."""
    if sichern:
        sicherung_anlegen(pfad)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(inhalt)


def erkenne_zeilenende(pfad, standard="\r\n"):
    if os.path.exists(pfad):
        with open(pfad, "rb") as f:
            inhalt = f.read()
        if b"\r\n" in inhalt:
            return "\r\n"
        if b"\n" in inhalt:
            return "\n"
    return standard


def lies_zeilen(pfad):
    if not os.path.exists(pfad):
        return []
    with open(pfad, "r", encoding="utf-8") as f:
        return [z.strip() for z in f if z.strip()]


def schreibe_zeilen(pfad, zeilen, sichern=True):
    zeilenende = erkenne_zeilenende(pfad)
    schreibe_datei(pfad, "".join(z + zeilenende for z in zeilen), sichern=sichern)


# ------------------------------------------------------------------
# Sicherung / Rueckgaengig
# ------------------------------------------------------------------

def sicherung_anlegen(pfad):
    """Kopiert die bestehende Datei nach .pflege-sicherungen/ und merkt sich
    im Protokoll, wohin sie zurueckgespielt werden muss."""
    if not os.path.isfile(pfad):
        return
    os.makedirs(SICHERUNGS_DIR, exist_ok=True)
    zeitstempel = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    relativ = os.path.relpath(pfad, ROOT)
    sicherungsname = f"{zeitstempel}__{relativ.replace(os.sep, '#')}"
    shutil.copy2(pfad, os.path.join(SICHERUNGS_DIR, sicherungsname))
    with open(PROTOKOLL, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{sicherungsname}\t{relativ}\n")
    _alte_sicherungen_aufraeumen()


def _protokoll_eintraege():
    if not os.path.isfile(PROTOKOLL):
        return []
    eintraege = []
    with open(PROTOKOLL, "r", encoding="utf-8") as f:
        for zeile in f:
            teile = zeile.rstrip("\n").split("\t")
            if len(teile) == 2:
                eintraege.append(tuple(teile))
    return eintraege


def _protokoll_schreiben(eintraege):
    with open(PROTOKOLL, "w", encoding="utf-8", newline="\n") as f:
        for sicherungsname, relativ in eintraege:
            f.write(f"{sicherungsname}\t{relativ}\n")


def _alte_sicherungen_aufraeumen():
    eintraege = _protokoll_eintraege()
    if len(eintraege) <= MAX_SICHERUNGEN:
        return
    for sicherungsname, _ in eintraege[:-MAX_SICHERUNGEN]:
        pfad = os.path.join(SICHERUNGS_DIR, sicherungsname)
        if os.path.isfile(pfad):
            os.remove(pfad)
    _protokoll_schreiben(eintraege[-MAX_SICHERUNGEN:])


def rueckgaengig():
    """Spielt die zuletzt gesicherte Datei zurueck."""
    eintraege = _protokoll_eintraege()
    if not eintraege:
        print("\nKeine Sicherung vorhanden - es gibt nichts rueckgaengig zu machen.")
        return

    sicherungsname, relativ = eintraege[-1]
    sicherungspfad = os.path.join(SICHERUNGS_DIR, sicherungsname)
    zielpfad = os.path.join(ROOT, relativ)

    if not os.path.isfile(sicherungspfad):
        print(f"\nSicherungsdatei fehlt ({sicherungsname}) - Eintrag wird verworfen.")
        _protokoll_schreiben(eintraege[:-1])
        return

    zeitpunkt = sicherungsname.split("__")[0]
    lesbar = f"{zeitpunkt[6:8]}.{zeitpunkt[4:6]}.{zeitpunkt[0:4]} {zeitpunkt[9:11]}:{zeitpunkt[11:13]}:{zeitpunkt[13:15]}"
    print(f"\nLetzte Aenderung: {relativ}")
    print(f"Stand vor der Aenderung vom {lesbar} wuerde wiederhergestellt.")
    try:
        bestaetigt = frage_ja("Wirklich rueckgaengig machen? (j/n): ")
    except Zurueck:
        bestaetigt = False
    if not bestaetigt:
        print("Abgebrochen.")
        return

    shutil.copy2(sicherungspfad, zielpfad)
    os.remove(sicherungspfad)
    _protokoll_schreiben(eintraege[:-1])
    print(f"\n{relativ} wurde auf den vorherigen Stand zurueckgesetzt.")
