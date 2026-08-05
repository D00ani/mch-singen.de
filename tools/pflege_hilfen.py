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
# Einsortieren
# ------------------------------------------------------------------

MONATE_DE_NR = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7,
    "october": 10, "december": 12,
}


def monat_nummer(text):
    return MONATE_DE_NR.get(text.strip().lower())


def datum_schluessel(text):
    """Macht aus verschiedenen Datumsschreibweisen einen vergleichbaren Wert:
       "15. Mai 2025" -> (2025, 5, 15)
       "2026"         -> (2026, 13, 32)  = irgendwann in dem Jahr, sortiert
                                           innerhalb des Jahres nach vorne
    """
    text = (text or "").strip()
    voll = re.search(r"(\d{1,2})\.\s*([A-Za-zÄÖÜäöüß]+)\s*(\d{4})", text)
    if voll:
        monat = monat_nummer(voll.group(2))
        if monat:
            return (int(voll.group(3)), monat, int(voll.group(1)))
    jahr = re.search(r"(\d{4})", text)
    if jahr:
        return (int(jahr.group(1)), 13, 32)
    return (0, 0, 0)


def einfuege_position(schluessel_liste, neuer_schluessel, absteigend=True):
    """Liefert den Index, an dem ein neuer Eintrag stehen muss, damit die
    Reihenfolge stimmt (absteigend = neueste zuerst)."""
    for position, vorhandener in enumerate(schluessel_liste):
        if (neuer_schluessel > vorhandener) if absteigend else (neuer_schluessel < vorhandener):
            return position
    return len(schluessel_liste)


def melde_einsortierung(position, gesamt):
    """Sagt dem Nutzer, wo der Eintrag landet."""
    if gesamt == 0:
        print("  Wird als erster Eintrag angelegt.")
    elif position == 0:
        print("  Wird ganz oben eingefuegt.")
    elif position >= gesamt:
        print("  Wird ganz unten angehaengt.")
    else:
        print(f"  Wird an Position {position + 1} von {gesamt + 1} einsortiert.")


# ------------------------------------------------------------------
# Pfade zu Medien (PDFs, Bilder)
# ------------------------------------------------------------------

MEDIEN_ORDNER = "media/"
EXTERNE_ANFAENGE = ("http://", "https://", "//", "mailto:", "tel:", "#", "data:")


def normalisiere_medienpfad(eingabe, praefix="../"):
    """Macht aus einer Eingabe einen web-tauglichen Medienpfad.

    Korrigiert die drei Stolpersteine dieses Projekts:
      - Backslashes aus dem Windows-Explorer  ->  Schraegstriche
      - fuehrender Schraegstrich (/media/...) ->  entfernt
      - fehlendes bzw. falsches '../'         ->  passend zum Speicherort

    praefix: '../' fuer Seiten in /pages/, '' fuer index.html und
    data/timer.txt (dort werden Pfade ab dem Hauptverzeichnis geschrieben).

    Gibt (pfad, korrekturen) zurueck - korrekturen ist eine Liste der
    vorgenommenen Aenderungen zum Anzeigen.
    """
    pfad = (eingabe or "").strip().replace("\\", "/")
    korrekturen = []

    if not pfad or pfad.startswith(EXTERNE_ANFAENGE):
        return pfad, korrekturen

    if "\\" in (eingabe or ""):
        korrekturen.append("Backslashes durch Schraegstriche ersetzt")

    entschlackt = re.sub(r"/{2,}", "/", pfad)
    if entschlackt != pfad:
        korrekturen.append("doppelte Schraegstriche entfernt")
        pfad = entschlackt

    # Fuehrende ../ und / abtrennen, damit der Pfad neu aufgebaut werden kann
    kern = pfad.lstrip("/")
    while kern.startswith("../"):
        kern = kern[3:]

    # Nur Medienpfade umbauen - Verweise auf andere Seiten (z. B.
    # "sommerferienprogramm.html") bleiben unangetastet.
    if not kern.startswith(MEDIEN_ORDNER):
        return pfad, korrekturen

    neu = praefix + kern
    if neu != pfad:
        if praefix and not pfad.startswith("../"):
            korrekturen.append("'../' ergaenzt (Unterseiten liegen in /pages/)")
        elif not praefix and pfad.startswith("../"):
            korrekturen.append("'../' entfernt (Pfad gilt ab dem Hauptverzeichnis)")
        elif pfad.startswith("/"):
            korrekturen.append("fuehrenden Schraegstrich entfernt")
        pfad = neu

    return pfad, korrekturen


def medienpfad_pruefen(pfad, praefix="../"):
    """Existiert die Datei? praefix bestimmt, worauf sich der Pfad bezieht."""
    if not pfad or pfad.startswith(EXTERNE_ANFAENGE):
        return True
    basis = os.path.join(ROOT, "pages") if praefix else ROOT
    return os.path.isfile(os.path.normpath(os.path.join(basis, pfad)))


def frage_medienpfad(text, default=None, praefix="../", pflicht=True):
    """Fragt einen Medienpfad ab, raeumt ihn auf und meldet Auffaelligkeiten."""
    while True:
        roh = (frage_mit_default(text, default) if default is not None
               else frage(f"{text}: ", pflicht=pflicht))
        pfad, korrekturen = normalisiere_medienpfad(roh, praefix)

        for hinweis in korrekturen:
            print(f"  Korrigiert: {hinweis}")
        if korrekturen:
            print(f"  -> {pfad}")

        if pfad and not pfad.startswith(EXTERNE_ANFAENGE):
            if not re.fullmatch(r"[a-z0-9/_.\-]+", pfad):
                print("  ACHTUNG: Grossbuchstaben, Umlaute oder Sonderzeichen im Pfad -")
                print("  der GitHub-Server unterscheidet Gross-/Kleinschreibung streng!")
            if not medienpfad_pruefen(pfad, praefix):
                print("  Hinweis: Diese Datei gibt es noch nicht - der Link bleibt tot,")
                print("  bis du sie hochlaedst.")
        return pfad


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


def _lesbarer_zeitpunkt(sicherungsname):
    z = sicherungsname.split("__")[0]
    return f"{z[6:8]}.{z[4:6]}.{z[0:4]} {z[9:11]}:{z[11:13]}:{z[13:15]}"


def sicherungs_verlauf():
    """Alle vorhandenen Sicherungen, je Datei gebuendelt, neueste zuerst.

    Liefert {relativer Pfad: [{sicherung, ziel, zeitpunkt, groesse}, ...]}.
    Der Ordner haelt bis zu MAX_SICHERUNGEN Staende - ueber 'Rueckgaengig'
    ist aber nur der letzte erreichbar, deshalb diese Uebersicht.
    """
    verlauf = {}
    for sicherungsname, relativ in _protokoll_eintraege():
        pfad = os.path.join(SICHERUNGS_DIR, sicherungsname)
        if not os.path.isfile(pfad):
            continue
        verlauf.setdefault(relativ, []).append({
            "sicherung": pfad,
            "ziel": os.path.join(ROOT, relativ),
            "relativ": relativ,
            "zeitpunkt": _lesbarer_zeitpunkt(sicherungsname),
            "groesse": os.path.getsize(pfad),
        })
    for staende in verlauf.values():
        staende.reverse()          # neueste zuerst
    return verlauf


def sicherung_einspielen(stand):
    """Spielt einen beliebigen Stand aus dem Verlauf zurueck.

    Anders als sicherung_zuruecknehmen() wird der Eintrag NICHT aus dem
    Protokoll entfernt - der aktuelle Stand wird vorher zusaetzlich
    gesichert, damit auch dieser Schritt umkehrbar bleibt.
    """
    if os.path.isfile(stand["ziel"]):
        sicherung_anlegen(stand["ziel"])
    os.makedirs(os.path.dirname(stand["ziel"]), exist_ok=True)
    shutil.copy2(stand["sicherung"], stand["ziel"])


def letzte_sicherung():
    """Was ein "Rueckgaengig" jetzt zurueckholen wuerde - oder None.

    Getrennt vom Ausfuehren, damit auch das Fenster (tools/pflege_fenster.py)
    danach fragen kann, ohne die Terminal-Abfrage mitzuschleppen.
    """
    eintraege = _protokoll_eintraege()
    while eintraege:
        sicherungsname, relativ = eintraege[-1]
        sicherungspfad = os.path.join(SICHERUNGS_DIR, sicherungsname)
        if os.path.isfile(sicherungspfad):
            return {
                "sicherung": sicherungspfad,
                "ziel": os.path.join(ROOT, relativ),
                "relativ": relativ,
                "zeitpunkt": _lesbarer_zeitpunkt(sicherungsname),
            }
        # Sicherungsdatei ist weg - Eintrag verwerfen und weiter zurueckgehen
        eintraege = eintraege[:-1]
        _protokoll_schreiben(eintraege)
    return None


def sicherung_zuruecknehmen(stand):
    """Spielt den von letzte_sicherung() gemeldeten Stand zurueck."""
    shutil.copy2(stand["sicherung"], stand["ziel"])
    os.remove(stand["sicherung"])
    _protokoll_schreiben(_protokoll_eintraege()[:-1])


def rueckgaengig():
    """Spielt die zuletzt gesicherte Datei zurueck."""
    stand = letzte_sicherung()
    if not stand:
        print("\nKeine Sicherung vorhanden - es gibt nichts rueckgaengig zu machen.")
        return

    print(f"\nLetzte Aenderung: {stand['relativ']}")
    print(f"Stand vor der Aenderung vom {stand['zeitpunkt']} wuerde wiederhergestellt.")
    try:
        bestaetigt = frage_ja("Wirklich rueckgaengig machen? (j/n): ")
    except Zurueck:
        bestaetigt = False
    if not bestaetigt:
        print("Abgebrochen.")
        return

    sicherung_zuruecknehmen(stand)
    print(f"\n{stand['relativ']} wurde auf den vorherigen Stand zurueckgesetzt.")
