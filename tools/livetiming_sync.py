# -*- coding: utf-8 -*-
"""
Live-Timing: holt die Ergebnisse aus der Zeitmessung ab und stellt sie auf
die Webseite.

Ablauf im Dauerbetrieb (Menuepunkt "Live-Timing"):
  Zeitmessung schreibt in ihre Access-Datenbank
      -> dieses Werkzeug liest sie (nur lesend!) alle paar Sekunden
      -> baut daraus data/livedata.json
      -> committet/merged/pusht die Datei, sobald sich etwas geaendert hat
      -> pages/live.html holt sich die Datei alle 3 Sekunden selbst

WICHTIG: Am Programm "Zeitmessung_Kart" und an seiner Datenbank wird nichts
veraendert - es wird ausschliesslich gelesen.

Ausfuehren: python tools/livetiming_sync.py
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import zeitmessung_lesen

ROOT = h.ROOT
PROJEKT = os.path.dirname(ROOT)                       # Ordner ueber mch-arbeit/
MAIN_WORKTREE = os.path.join(PROJEKT, "mch-singen.de-main")
LIVEDATA = os.path.join(ROOT, "data", "livedata.json")
ARCHIV_ORDNER = os.path.join(ROOT, "data", "ergebnisse")
ARCHIV_INDEX = os.path.join(ARCHIV_ORDNER, "index.json")
KONFIG_DATEI = os.path.join(ROOT, "tools", "livetiming.config.json")

# Wo die Datenbank der Zeitmessung ueblicherweise liegt (relativ zum Ordner
# ueber mch-arbeit/), falls in der Konfiguration nichts hinterlegt ist.
STANDARD_DB = os.path.join(PROJEKT, "Zeitmessung_Kart", "Zeitmessung_Kart_Data",
                           "Zeitmessung_Kart_Data.accdb")
APP_CONFIG = os.path.join(PROJEKT, "Zeitmessung_Kart", "Zeitmessung_Kart", "App.config")

# LaufNr in der Datenbank -> Beschriftung der Knoepfe auf pages/live.html.
# envDB.LaufergebnisseSave speichert 1 = 1. Wertungslauf, 2 = 2. Wertungslauf,
# 0 = Gesamtergebnis. Trainingslaeufe schreibt die Zeitmessung NICHT in die
# Tabelle "Laufergebnisse" - fuer "TL" gibt es dort also keine Daten.
STANDARD_LAUF_NAMEN = {"1": "1. WL", "2": "2. WL", "0": "Gesamt"}

STANDARD_KONFIG = {
    "datenbank": "",
    "datum": "heute",
    "veranstaltung": "Bodensee Kart Cup · MCH Singen e.V.",
    "intervall_sekunden": 15,
    "veroeffentlichen": True,
    "mindestabstand_push_sekunden": 60,
    "lauf_namen": STANDARD_LAUF_NAMEN,
}


# ------------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------------

def lies_konfig():
    konfig = dict(STANDARD_KONFIG)
    if os.path.isfile(KONFIG_DATEI):
        try:
            with open(KONFIG_DATEI, encoding="utf-8") as f:
                konfig.update(json.load(f))
        except (OSError, ValueError) as fehler:
            print(f"  Hinweis: {os.path.basename(KONFIG_DATEI)} ist unlesbar "
                  f"({fehler}) - es gelten die Standardwerte.")
    return konfig


def schreibe_konfig(konfig):
    with open(KONFIG_DATEI, "w", encoding="utf-8", newline="\n") as f:
        json.dump(konfig, f, ensure_ascii=False, indent=2)
        f.write("\n")


def datenbank_aus_app_config():
    """Liest den Datenbankpfad aus der App.config der Zeitmessung - dann zeigt
    das Werkzeug automatisch auf dieselbe Datei wie das Programm."""
    if not os.path.isfile(APP_CONFIG):
        return ""
    try:
        with open(APP_CONFIG, encoding="utf-8") as f:
            inhalt = f.read()
    except OSError:
        return ""
    treffer = re.search(r'Data Source=([^"\';]+)', inhalt)
    return treffer.group(1).strip() if treffer else ""


def finde_datenbank(konfig):
    """Erster Treffer gewinnt: Konfiguration, App.config der Zeitmessung,
    Standardort im Projektordner."""
    for pfad in (konfig.get("datenbank", ""), datenbank_aus_app_config(), STANDARD_DB):
        if pfad and os.path.isfile(pfad):
            return os.path.abspath(pfad)
    return ""


# ------------------------------------------------------------------
# Zeiten
# ------------------------------------------------------------------

# Die Zeitmessung schreibt Zeiten als "mm:ss,hh" (frmZeitmessung.ZeitAnzeigen).
ZEIT_MUSTER = re.compile(r"^(\d{1,3}):([0-5]?\d),(\d{1,2})$")
UHRZEIT_MUSTER = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?")


def zeit_in_hundertstel(text):
    """"01:05,55" -> 6555. None, wenn keine Zeit dasteht (z. B. "ADW")."""
    treffer = ZEIT_MUSTER.match((text or "").strip())
    if not treffer:
        return None
    minuten, sekunden, hundertstel = treffer.groups()
    return (int(minuten) * 60 + int(sekunden)) * 100 + int(hundertstel.ljust(2, "0"))


def hundertstel_in_zeit(wert):
    """6555 -> "01:05,55"."""
    wert = abs(int(wert))
    return f"{wert // 6000:02d}:{wert // 100 % 60:02d},{wert % 100:02d}"


def _uhrzeit_schluessel(text):
    """"14:02:21" -> (14, 2, 21); unbrauchbare Werte sortieren nach ganz hinten."""
    treffer = UHRZEIT_MUSTER.match((text or "").strip())
    if not treffer:
        return (-1, -1, -1)
    return tuple(int(teil or 0) for teil in treffer.groups())


def _natuerlich(text):
    """Sortiert "1a" vor "1b" vor "2" vor "10" (statt rein alphabetisch)."""
    return [(0, int(teil)) if teil.isdigit() else (1, teil)
            for teil in re.split(r"(\d+)", text or "") if teil]


# ------------------------------------------------------------------
# Aus den Datenbankzeilen die Live-Tabelle bauen
# ------------------------------------------------------------------

def waehle_datum(zeilen, wunsch):
    """"heute" = heutiges Datum, "letzte" = juengster Tag mit Ergebnissen,
    sonst der angegebene Tag (YYYY-MM-DD)."""
    heute = datetime.now().strftime("%Y-%m-%d")
    if wunsch in ("", "heute"):
        return heute
    if wunsch == "letzte":
        tage = sorted({z["datum"] for z in zeilen if z["datum"]})
        return tage[-1] if tage else heute
    return wunsch


def _neueste_je_starter(zeilen, datum, lauf_namen):
    """Wiederholte Laeufe haengt die Zeitmessung als ZUSAETZLICHE Zeile an
    (frmStarter.cmdWiederholen_Click). Es zaehlt deshalb je Starter und Lauf
    nur der juengste Eintrag."""
    neueste = {}
    for position, zeile in enumerate(zeilen):
        if zeile["datum"] != datum or zeile["laufnr"] not in lauf_namen:
            continue
        if not zeile["starternr"] and not zeile["name"]:
            continue  # Leerzeile in der Datenbank
        schluessel = (zeile["laufnr"], zeile["starternr"], zeile["name"], zeile["klasse"])
        rang = (_uhrzeit_schluessel(zeile["uhrzeit"]), position)
        if schluessel not in neueste or rang > neueste[schluessel][0]:
            neueste[schluessel] = (rang, zeile)
    return [zeile for _, zeile in neueste.values()]


def _klassenname(klasse):
    """Die Zeitmessung speichert "1a", die Webseite zeigt "Klasse 1a"."""
    klasse = (klasse or "").strip()
    if not klasse:
        return "Ohne Klasse"
    return klasse if klasse.lower().startswith("klasse") else f"Klasse {klasse}"


def _startnummer(text):
    return int(text) if text.isdigit() else text


def _strafzeit_anzeige(zeile):
    """Die mittlere Zeile der Zeit-Spalte auf der Live-Seite: die Strafsekunden
    aus Pylonen und Fahrfehlern, z. B. "(12)". Leer, wenn es keine gab."""
    strafzeit = zeile["strafzeit"]
    if strafzeit.isdigit() and int(strafzeit) > 0:
        return f"({int(strafzeit)})"
    return ""


def baue_ergebnisse(zeilen, datum, lauf_namen):
    """Macht aus den Datenbankzeilen die Liste, die js/live.js erwartet:
    je Klasse und Lauf sortiert, mit Platz und Rueckstaenden."""
    gruppen = {}
    for zeile in _neueste_je_starter(zeilen, datum, lauf_namen):
        gruppen.setdefault((zeile["klasse"], zeile["laufnr"]), []).append(zeile)

    ergebnisse = []
    for klasse, laufnr in sorted(gruppen, key=lambda s: (_natuerlich(s[0]), s[1])):
        starter = gruppen[(klasse, laufnr)]
        # Schnellste Gesamtzeit zuerst; Starter ohne gueltige Zeit (z. B. "ADW")
        # ans Ende, dort nach Startnummer.
        starter.sort(key=lambda z: (zeit_in_hundertstel(z["gesamtzeit"]) is None,
                                    zeit_in_hundertstel(z["gesamtzeit"]) or 0,
                                    _natuerlich(z["starternr"])))

        bestzeit = None
        vorherige = None
        for platz, zeile in enumerate(starter, start=1):
            gesamt = zeit_in_hundertstel(zeile["gesamtzeit"])
            if gesamt is not None and bestzeit is None:
                bestzeit = gesamt

            rueckstand_erster = rueckstand_vorheriger = ""
            if gesamt is not None and platz > 1:
                if bestzeit is not None:
                    rueckstand_erster = "+" + hundertstel_in_zeit(gesamt - bestzeit)
                if vorherige is not None:
                    rueckstand_vorheriger = "+" + hundertstel_in_zeit(gesamt - vorherige)
            if gesamt is not None:
                vorherige = gesamt

            ergebnisse.append({
                "klasse": _klassenname(zeile["klasse"]),
                "lauf": lauf_namen[laufnr],
                "platz": platz,
                "startnummer": _startnummer(zeile["starternr"]),
                "name": zeile["name"],
                "club": zeile["verein"],
                "zeit_raw": zeile["fahrzeit"],
                "fehler": _strafzeit_anzeige(zeile),
                "zeit_total": zeile["gesamtzeit"],
                "diff_first": rueckstand_erster,
                "diff_prev": rueckstand_vorheriger,
            })
    return ergebnisse


def baue_livedata(zeilen, datum, lauf_namen, veranstaltung=""):
    ergebnisse = baue_ergebnisse(zeilen, datum, lauf_namen)
    jetzt = datetime.now()
    try:
        anzeigedatum = datetime.strptime(datum, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        anzeigedatum = datum
    return {
        "last_update": jetzt.strftime("%H:%M:%S"),
        # Voller Zeitstempel, damit die Seite ausrechnen kann, WIE ALT der
        # Stand ist - "07:38:52" allein sagt nichts darueber aus, ob die
        # Zeitnahme noch laeuft.
        "stand_iso": jetzt.astimezone().isoformat(timespec="seconds"),
        "datum": anzeigedatum,
        "datum_iso": datum,
        "veranstaltung": veranstaltung or STANDARD_KONFIG["veranstaltung"],
        "quelle": "Zeitmessung_Kart",
        "results": ergebnisse,
    }


# ------------------------------------------------------------------
# Datei schreiben und veroeffentlichen
# ------------------------------------------------------------------

def _inhaltskennung(daten):
    """Alles ausser dem Zeitstempel - nur wenn sich das aendert, muss neu
    geschrieben und gepusht werden."""
    return json.dumps([daten.get("datum"), daten.get("veranstaltung"),
                       daten.get("results")],
                      ensure_ascii=False, sort_keys=True)


def _json_schreiben(pfad, daten):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
        f.write("\n")


def archiviere(daten):
    """Legt den Stand zusaetzlich unter data/ergebnisse/<Renntag>.json ab und
    pflegt das Verzeichnis der Renntage. So bleiben vergangene Rennen
    erhalten, statt von der naechsten Veranstaltung ueberschrieben zu werden."""
    datum = daten.get("datum_iso") or ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum) or not daten.get("results"):
        return  # ohne sauberen Renntag oder ohne Ergebnisse nichts archivieren

    _json_schreiben(os.path.join(ARCHIV_ORDNER, f"{datum}.json"), daten)

    verzeichnis = []
    if os.path.isfile(ARCHIV_INDEX):
        try:
            with open(ARCHIV_INDEX, encoding="utf-8") as f:
                verzeichnis = json.load(f).get("renntage", [])
        except (OSError, ValueError):
            verzeichnis = []

    eintrag = {
        "datum": datum,
        "anzeige": daten.get("datum", datum),
        "veranstaltung": daten.get("veranstaltung", ""),
        "starter": len({(e["klasse"], e["startnummer"]) for e in daten["results"]}),
        "ergebnisse": len(daten["results"]),
    }
    verzeichnis = [e for e in verzeichnis if e.get("datum") != datum] + [eintrag]
    verzeichnis.sort(key=lambda e: e.get("datum", ""), reverse=True)
    _json_schreiben(ARCHIV_INDEX, {"renntage": verzeichnis})


def schreibe_livedata(daten, pfad=LIVEDATA, mit_archiv=True):
    """Schreibt data/livedata.json - aber nur, wenn sich wirklich etwas
    geaendert hat. Gibt True zurueck, wenn geschrieben wurde."""
    if os.path.isfile(pfad):
        try:
            with open(pfad, encoding="utf-8") as f:
                if _inhaltskennung(json.load(f)) == _inhaltskennung(daten):
                    return False
        except (OSError, ValueError):
            pass  # kaputte oder fehlende Datei: neu schreiben

    _json_schreiben(pfad, daten)
    if mit_archiv and pfad == LIVEDATA:
        archiviere(daten)
    return True


def _git(argumente, cwd):
    return subprocess.run(["git"] + argumente, cwd=cwd,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def veroeffentliche(nachricht):
    """Committet NUR die Ergebnisdateien, merged nach main und pusht.
    Bewusst nicht 'git add -A': waehrend einer Veranstaltung soll nichts
    anderes versehentlich mit veroeffentlicht werden.
    Gibt (erfolg, meldung) zurueck."""
    pfade = [os.path.relpath(LIVEDATA, ROOT).replace(os.sep, "/"),
             os.path.relpath(ARCHIV_ORDNER, ROOT).replace(os.sep, "/")]

    if _git(["add", "--"] + pfade, ROOT).returncode != 0:
        return False, "git add fehlgeschlagen"

    if not _git(["diff", "--cached", "--quiet", "--"] + pfade, ROOT).returncode:
        return True, "nichts zu committen"

    ergebnis = _git(["commit", "-m", nachricht, "--"] + pfade, ROOT)
    if ergebnis.returncode != 0:
        return False, f"git commit: {(ergebnis.stderr or ergebnis.stdout).strip()}"

    if not os.path.isdir(MAIN_WORKTREE):
        return False, f"{MAIN_WORKTREE} nicht gefunden - Merge/Push nicht moeglich"

    ergebnis = _git(["merge", "arbeit", "--no-edit"], MAIN_WORKTREE)
    if ergebnis.returncode != 0:
        return False, f"Merge nach main: {(ergebnis.stderr or ergebnis.stdout).strip()}"

    ergebnis = _git(["push", "origin", "main"], MAIN_WORKTREE)
    if ergebnis.returncode != 0:
        return False, f"Push: {(ergebnis.stderr or ergebnis.stdout).strip()}"

    _git(["merge", "main", "--no-edit"], ROOT)
    return True, "veroeffentlicht"


# ------------------------------------------------------------------
# Ein Durchlauf
# ------------------------------------------------------------------

class Abgleich:
    """Haelt den Zustand eines Live-Durchlaufs (Datenbank, Datum, Zaehler)."""

    def __init__(self, konfig, db_pfad, datum_wunsch=None):
        self.konfig = konfig
        self.db_pfad = db_pfad
        self.datum_wunsch = datum_wunsch or konfig.get("datum", "heute")
        self.lauf_namen = konfig.get("lauf_namen") or STANDARD_LAUF_NAMEN
        self.letzter_push = 0.0
        self.wartet_auf_push = False

    def einmal(self, veroeffentlichen):
        """Liest die Datenbank, schreibt die Datei und veroeffentlicht bei
        Bedarf. Gibt eine Statuszeile zurueck."""
        zeilen = zeitmessung_lesen.lies_laufergebnisse(self.db_pfad)
        datum = waehle_datum(zeilen, self.datum_wunsch)
        daten = baue_livedata(zeilen, datum, self.lauf_namen,
                              self.konfig.get("veranstaltung", ""))
        geaendert = schreibe_livedata(daten)

        anzahl = len(daten["results"])
        stand = f"{daten['last_update']}  {anzahl:3} Ergebnisse ({daten['datum']})"

        if geaendert:
            self.wartet_auf_push = True
        if not self.wartet_auf_push:
            return stand + "  - unveraendert"
        if not veroeffentlichen:
            return stand + "  - geschrieben (kein Push)"

        abstand = self.konfig.get("mindestabstand_push_sekunden", 60)
        wartezeit = abstand - (time.monotonic() - self.letzter_push)
        if self.letzter_push and wartezeit > 0:
            return stand + f"  - geschrieben, Push in {int(wartezeit)}s"

        erfolg, meldung = veroeffentliche(
            f"Live-Timing: Zwischenstand {daten['last_update']}")
        if erfolg:
            self.letzter_push = time.monotonic()
            self.wartet_auf_push = False
            return stand + "  - veroeffentlicht"
        self.letzter_push = time.monotonic()  # nicht sofort erneut probieren
        return stand + f"  - Push fehlgeschlagen: {meldung}"


# ------------------------------------------------------------------
# Bedienung
# ------------------------------------------------------------------

def _vorbereiten(konfig, datum_wunsch=None):
    """Sucht die Datenbank und meldet, wenn sie fehlt."""
    db_pfad = finde_datenbank(konfig)
    if not db_pfad:
        print("\nDie Datenbank der Zeitmessung wurde nicht gefunden.")
        print(f"  Gesucht wurde in: {konfig.get('datenbank') or '(nicht gesetzt)'}")
        print(f"                    {datenbank_aus_app_config() or '(App.config ohne Pfad)'}")
        print(f"                    {STANDARD_DB}")
        print("\nBitte im Menuepunkt 'Einstellungen' den Pfad zur Datei")
        print("Zeitmessung_Kart_Data.accdb eintragen.")
        return None
    return Abgleich(konfig, db_pfad, datum_wunsch)


def einmal_abgleichen(konfig=None, datum_wunsch=None, veroeffentlichen=None):
    konfig = konfig or lies_konfig()
    abgleich = _vorbereiten(konfig, datum_wunsch)
    if abgleich is None:
        return False
    if veroeffentlichen is None:
        veroeffentlichen = konfig.get("veroeffentlichen", True)

    print(f"\nDatenbank: {abgleich.db_pfad}")
    try:
        print("  " + abgleich.einmal(veroeffentlichen))
    except zeitmessung_lesen.LeseFehler as fehler:
        print(f"\nFEHLER beim Lesen der Zeitmessung:\n  {fehler}")
        return False
    return True


def live_betrieb(konfig=None, datum_wunsch=None, veroeffentlichen=None):
    konfig = konfig or lies_konfig()
    abgleich = _vorbereiten(konfig, datum_wunsch)
    if abgleich is None:
        return
    if veroeffentlichen is None:
        veroeffentlichen = konfig.get("veroeffentlichen", True)

    intervall = max(3, int(konfig.get("intervall_sekunden", 15)))

    print("\n" + "=" * 60)
    print("  Live-Timing laeuft")
    print("=" * 60)
    print(f"  Datenbank    : {abgleich.db_pfad}")
    print(f"  Tag          : {abgleich.datum_wunsch}")
    print(f"  Abgleich alle: {intervall} Sekunden")
    if veroeffentlichen:
        print(f"  Veroeffentl. : ja, fruehestens alle "
              f"{konfig.get('mindestabstand_push_sekunden', 60)} Sekunden")
        print("                 (GitHub Pages braucht danach 1-3 Minuten)")
    else:
        print("  Veroeffentl. : nein - es wird nur die Datei geschrieben")
    print("\n  Beenden mit Strg+C\n")

    fehler_in_folge = 0
    try:
        while True:
            try:
                print("  " + abgleich.einmal(veroeffentlichen), flush=True)
                fehler_in_folge = 0
            except zeitmessung_lesen.LeseFehler as fehler:
                fehler_in_folge += 1
                zeitpunkt = datetime.now().strftime("%H:%M:%S")
                print(f"  {zeitpunkt}  Zeitmessung nicht lesbar ({fehler_in_folge}. Versuch)",
                      flush=True)
                if fehler_in_folge == 1:
                    print(f"            {fehler}", flush=True)
            time.sleep(intervall)
    except KeyboardInterrupt:
        print("\n\n  Live-Timing beendet.")
        if abgleich.wartet_auf_push and veroeffentlichen:
            print("  Letzten Stand noch veroeffentlichen ...")
            erfolg, meldung = veroeffentliche("Live-Timing: Endstand")
            print(f"  {meldung}")


def einstellungen(konfig):
    """Fragt die Einstellungen ab und legt sie in tools/livetiming.config.json ab."""
    print("\nEinstellungen fuer das Live-Timing")
    print("  ('x' = zurueck, Enter = Wert behalten)")

    gefunden = finde_datenbank(konfig)
    db_pfad = h.frage_mit_default(
        "\nPfad zur Datei Zeitmessung_Kart_Data.accdb",
        konfig.get("datenbank") or gefunden or STANDARD_DB)
    db_pfad = db_pfad.strip().strip('"')
    if db_pfad and not os.path.isfile(db_pfad):
        print("  ACHTUNG: Diese Datei gibt es (noch) nicht.")

    datum = h.frage_mit_default(
        "Welcher Tag? ('heute', 'letzte' oder JJJJ-MM-TT)",
        konfig.get("datum", "heute"))

    veranstaltung = h.frage_mit_default(
        "Name der Veranstaltung (steht im Kopf der Live-Seite)",
        konfig.get("veranstaltung", STANDARD_KONFIG["veranstaltung"]))

    intervall = h.frage_mit_default(
        "Alle wieviel Sekunden nachschauen?",
        str(konfig.get("intervall_sekunden", 15)), h.ZAHL_VALIDIERER)

    veroeffentlichen = h.frage_ja(
        f"Aenderungen automatisch veroeffentlichen? "
        f"(j/n) [{'j' if konfig.get('veroeffentlichen', True) else 'n'}]: ")

    abstand = h.frage_mit_default(
        "Mindestabstand zwischen zwei Veroeffentlichungen (Sekunden)",
        str(konfig.get("mindestabstand_push_sekunden", 60)), h.ZAHL_VALIDIERER)

    konfig.update({
        "datenbank": db_pfad,
        "datum": datum.strip(),
        "veranstaltung": veranstaltung.strip(),
        "intervall_sekunden": int(intervall),
        "veroeffentlichen": veroeffentlichen,
        "mindestabstand_push_sekunden": int(abstand),
    })
    konfig.setdefault("lauf_namen", STANDARD_LAUF_NAMEN)
    schreibe_konfig(konfig)
    print(f"\nGespeichert in {os.path.relpath(KONFIG_DATEI, ROOT)}.")


def zeige_status(konfig):
    """Kurzer Selbsttest: Datenbank lesbar? Was steckt drin?"""
    db_pfad = finde_datenbank(konfig)
    print("\nStatus")
    print(f"  Datenbank : {db_pfad or 'NICHT GEFUNDEN'}")
    if not db_pfad:
        return

    try:
        zeilen = zeitmessung_lesen.lies_laufergebnisse(db_pfad)
    except zeitmessung_lesen.LeseFehler as fehler:
        print(f"  Lesen     : FEHLER - {fehler}")
        return

    tage = sorted({z["datum"] for z in zeilen if z["datum"]})
    weg = zeitmessung_lesen.letzter_weg
    print(f"  Lesen     : ok, {len(zeilen)} Zeilen")
    print(f"  Zugriff   : {weg['powershell']} mit {weg['treiber']}")
    print(f"  Renntage  : {', '.join(tage[-5:]) if tage else 'keine'}")

    datum = waehle_datum(zeilen, konfig.get("datum", "heute"))
    lauf_namen = konfig.get("lauf_namen") or STANDARD_LAUF_NAMEN
    ergebnisse = baue_ergebnisse(zeilen, datum, lauf_namen)
    print(f"  Gewaehlt  : {datum} -> {len(ergebnisse)} Ergebnisse")

    if ergebnisse:
        gruppen = {}
        for eintrag in ergebnisse:
            gruppen.setdefault((eintrag["klasse"], eintrag["lauf"]), 0)
            gruppen[(eintrag["klasse"], eintrag["lauf"])] += 1
        for (klasse, lauf), anzahl in sorted(gruppen.items()):
            print(f"              {klasse:<12} {lauf:<8} {anzahl:3} Starter")
    else:
        print("              (an diesem Tag hat die Zeitmessung nichts gespeichert)")

    if os.path.isfile(LIVEDATA):
        stand = datetime.fromtimestamp(os.path.getmtime(LIVEDATA))
        print(f"  livedata  : zuletzt geschrieben {stand:%d.%m.%Y %H:%M:%S}")


def _beispieldaten():
    """Erfundene Ergebnisse zum Vorfuehren der Seite (eigenes Werkzeug,
    damit dieses hier schlank bleibt)."""
    import livetiming_beispiel
    livetiming_beispiel.main()


def main():
    print("=" * 60)
    print("  MCH Singen - Live-Timing aus der Zeitmessung")
    print("=" * 60)
    print("\nDie Zeitmessung wird dabei nur gelesen und nicht veraendert.")

    konfig = lies_konfig()
    while True:
        punkte = [
            ("Live-Timing starten (laeuft bis Strg+C)", lambda: live_betrieb(konfig)),
            ("Einmal abgleichen und veroeffentlichen", lambda: einmal_abgleichen(konfig)),
            ("Nur Datei schreiben, nicht veroeffentlichen",
             lambda: einmal_abgleichen(konfig, veroeffentlichen=False)),
            ("Status / Selbsttest", lambda: zeige_status(konfig)),
            ("Einstellungen", lambda: einstellungen(konfig)),
            ("Beispieldaten zum Vorfuehren erzeugen", _beispieldaten),
        ]
        aktion = h.menue("Was moechtest du tun?", punkte)
        if aktion is None:
            return
        h.fuehre_aus(aktion)


def _argumente():
    zerleger = argparse.ArgumentParser(
        description="Live-Timing: Ergebnisse der Zeitmessung auf die Webseite bringen.")
    zerleger.add_argument("--live", action="store_true",
                          help="Dauerbetrieb ohne Menue")
    zerleger.add_argument("--einmal", action="store_true",
                          help="Einmal abgleichen und beenden")
    zerleger.add_argument("--datum",
                          help="'heute', 'letzte' oder JJJJ-MM-TT")
    zerleger.add_argument("--db", help="Pfad zur Zeitmessung_Kart_Data.accdb")
    zerleger.add_argument("--intervall", type=int,
                          help="Sekunden zwischen zwei Abgleichen")
    zerleger.add_argument("--kein-push", action="store_true",
                          help="Nur die Datei schreiben, nichts veroeffentlichen")
    zerleger.add_argument("--status", action="store_true",
                          help="Selbsttest ausgeben und beenden")
    return zerleger.parse_args()


if __name__ == "__main__":
    args = _argumente()
    einstellung = lies_konfig()
    if args.db:
        einstellung["datenbank"] = args.db
    if args.intervall:
        einstellung["intervall_sekunden"] = args.intervall
    veroeffentlichen_arg = False if args.kein_push else None

    if args.status:
        zeige_status(einstellung)
    elif args.einmal:
        einmal_abgleichen(einstellung, args.datum, veroeffentlichen_arg)
    elif args.live:
        live_betrieb(einstellung, args.datum, veroeffentlichen_arg)
    else:
        h.fuehre_aus(main)
