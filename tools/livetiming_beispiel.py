# -*- coding: utf-8 -*-
"""
Erzeugt Beispieldaten fuer die Live-Seite - zum Vorfuehren, wenn gerade
kein Rennen laeuft.

Die Namen sind frei erfunden und der Kopf der Seite weist die Daten als
Beispiel aus. Es sind KEINE echten Ergebnisse.

Sobald am Renntag das richtige Live-Timing laeuft, ueberschreibt es diese
Datei mit den echten Zeiten aus der Zeitmessung.

Ausfuehren: python tools/livetiming_beispiel.py
"""
import os
import random
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import livetiming_sync as lts

VERANSTALTUNG = "Bodensee Kart Cup · MCH Singen e.V. (Beispieldaten)"

VEREINE = ["MCH Singen", "AC Engen", "MSC Steißlingen", "AC Singen",
           "MSG Salemertal", "AMC Meßkirch"]

# Frei erfundene Namen - bewusst keine echten Mitglieder
VORNAMEN = ["Lena", "Jonas", "Mia", "Elias", "Emma", "Luca", "Hannah", "Finn",
            "Marie", "Noah", "Lea", "Paul", "Sophia", "Ben", "Clara", "Tim",
            "Nele", "Jakob", "Amelie", "Moritz", "Frieda", "Anton", "Ida",
            "Emil", "Johanna", "Theo", "Greta", "Linus", "Malia", "Jonte"]
NACHNAMEN = ["Bauer", "Wagner", "Keller", "Roth", "Vogt", "Hofmann", "Kern",
             "Brandt", "Seifert", "Ritter", "Kuhn", "Sommer", "Weiss", "Ebert",
             "Gerber", "Naumann", "Haas", "Reich", "Foerster", "Zimmer",
             "Berger", "Kaiser", "Lang", "Moser", "Stark", "Winkler"]

# Klasse -> (Anzahl Starter, mittlere Fahrzeit in Sekunden)
# Die jungen Klassen fahren die kleineren Kurse, deshalb unterschiedliche
# Grundzeiten.
KLASSEN = [
    ("1a", 7, 44.0),
    ("1b", 6, 42.5),
    ("2",  8, 40.0),
    ("3",  7, 38.5),
    ("4",  5, 37.5),
]


def _zeit(hundertstel):
    """4437 -> "00:44,37". Gerechnet wird durchgaengig in Hundertsteln:
    die Zeitmessung addiert die bereits angezeigten Zeiten, deshalb muss
    die Gesamtzeit exakt die Summe der beiden Laufzeiten sein."""
    return lts.hundertstel_in_zeit(max(0, int(hundertstel)))


def _starterfeld(zufall):
    """Baut ein Starterfeld mit eindeutigen Namen und Startnummern."""
    namen = set()
    feld = []
    nummer = 1
    for klasse, anzahl, grundzeit in KLASSEN:
        for _ in range(anzahl):
            while True:
                name = f"{zufall.choice(VORNAMEN)} {zufall.choice(NACHNAMEN)}"
                if name not in namen:
                    namen.add(name)
                    break
            feld.append({
                "nr": nummer,
                "name": name,
                "klasse": klasse,
                "verein": zufall.choice(VEREINE),
                "grundzeit": grundzeit,
                # Wie stark der Fahrer von der Grundzeit abweicht
                "koennen": zufall.uniform(-2.5, 4.5),
            })
            nummer += 1
    return feld


def _lauf(zufall, starter, streuung):
    """Ein Wertungslauf, alle Zeiten in Hundertstelsekunden."""
    sekunden = (starter["grundzeit"] + starter["koennen"]
                + zufall.uniform(-1.2, 1.8) + streuung)
    fahrzeit = max(1, int(round(sekunden * 100)))
    pylonen = zufall.choices([0, 0, 0, 1, 1, 2, 3], k=1)[0]
    fehler = zufall.choices([0, 0, 0, 0, 0, 1], k=1)[0]
    strafe = pylonen * 2 + fehler * 10          # wie in den Einstellungen
    return {
        "fahrzeit": fahrzeit,
        "pylonen": pylonen,
        "adw": fehler,
        "strafzeit": strafe,
        "gesamt": fahrzeit + strafe * 100,
    }


def _eintrag(starter, lauf, laufname, werte, platz):
    return {
        "klasse": f"Klasse {starter['klasse']}",
        "lauf": laufname,
        "platz": platz,
        "startnummer": starter["nr"],
        "name": starter["name"],
        "club": starter["verein"],
        "zeit_raw": _zeit(werte["fahrzeit"]),
        "fehler": f"({werte['strafzeit']})" if werte["strafzeit"] else "",
        "zeit_total": _zeit(werte["gesamt"]),
        "diff_first": "",
        "diff_prev": "",
    }


def baue_beispieldaten(startwert=20260607):
    """Erzeugt einen vollstaendigen Renntag. Gleicher Startwert = gleiche
    Daten, damit sich die Datei nicht bei jedem Aufruf sinnlos aendert."""
    zufall = random.Random(startwert)
    feld = _starterfeld(zufall)

    ergebnisse = []
    for starter in feld:
        wl1 = _lauf(zufall, starter, 0.0)
        wl2 = _lauf(zufall, starter, zufall.uniform(-1.5, 0.5))  # meist etwas schneller
        ergebnisse.append((starter, wl1, wl2))

    # Ein Starter faellt im zweiten Lauf aus (ADW = ausgeschieden)
    ausfall = zufall.randrange(len(ergebnisse))

    eintraege = []
    for i, (starter, wl1, wl2) in enumerate(ergebnisse):
        eintraege.append(_eintrag(starter, 1, "1. WL", wl1, 0))
        if i == ausfall:
            zeile = _eintrag(starter, 2, "2. WL", wl2, 0)
            zeile["zeit_total"] = "ADW"
            zeile["fehler"] = ""
            eintraege.append(zeile)
            continue
        eintraege.append(_eintrag(starter, 2, "2. WL", wl2, 0))
        gesamt = {
            "fahrzeit": wl1["fahrzeit"] + wl2["fahrzeit"],
            "strafzeit": wl1["strafzeit"] + wl2["strafzeit"],
            "gesamt": wl1["gesamt"] + wl2["gesamt"],
        }
        eintraege.append(_eintrag(starter, 0, "Gesamt", gesamt, 0))

    # Platzierung und Rueckstaende genau wie im echten Werkzeug rechnen
    return _sortiere_und_werte(eintraege)


def _sortiere_und_werte(eintraege):
    gruppen = {}
    for e in eintraege:
        gruppen.setdefault((e["klasse"], e["lauf"]), []).append(e)

    fertig = []
    for schluessel in sorted(gruppen, key=lambda s: (lts._natuerlich(s[0]), s[1])):
        gruppe = gruppen[schluessel]
        gruppe.sort(key=lambda e: (lts.zeit_in_hundertstel(e["zeit_total"]) is None,
                                   lts.zeit_in_hundertstel(e["zeit_total"]) or 0,
                                   e["startnummer"]))
        bestzeit = None
        vorherige = None
        for platz, e in enumerate(gruppe, start=1):
            wert = lts.zeit_in_hundertstel(e["zeit_total"])
            e["platz"] = platz
            if wert is not None and bestzeit is None:
                bestzeit = wert
            if wert is not None and platz > 1:
                e["diff_first"] = "+" + lts.hundertstel_in_zeit(wert - bestzeit)
                if vorherige is not None:
                    e["diff_prev"] = "+" + lts.hundertstel_in_zeit(wert - vorherige)
            if wert is not None:
                vorherige = wert
        fertig.extend(gruppe)
    return fertig


def schreibe(datum=None):
    """Schreibt data/livedata.json. Das Archiv bleibt unangetastet -
    Beispieldaten gehoeren nicht in die Liste der Renntage."""
    jetzt = datetime.now()
    tag = datum or jetzt.strftime("%Y-%m-%d")
    daten = {
        "last_update": jetzt.strftime("%H:%M:%S"),
        "stand_iso": jetzt.astimezone().isoformat(timespec="seconds"),
        "datum": datetime.strptime(tag, "%Y-%m-%d").strftime("%d.%m.%Y"),
        "datum_iso": tag,
        "veranstaltung": VERANSTALTUNG,
        "quelle": "Beispieldaten",
        "results": baue_beispieldaten(),
    }
    lts.schreibe_livedata(daten, mit_archiv=False)
    return daten


def main():
    print("=" * 60)
    print("  Beispieldaten fuer die Live-Seite")
    print("=" * 60)
    print("\nErfundene Namen und Zeiten zum Vorfuehren der Seite.")
    print("Das Archiv wird NICHT angefasst.")
    print("Am Renntag ueberschreibt das Live-Timing diese Datei automatisch.")

    try:
        if not h_frage_ja("\nBeispieldaten jetzt erzeugen? (j/n): "):
            print("Abgebrochen.")
            return
    except Exception:
        return

    daten = schreibe()
    starter = len({(e["klasse"], e["startnummer"]) for e in daten["results"]})
    klassen = sorted({e["klasse"] for e in daten["results"]}, key=lts._natuerlich)
    print(f"\nGeschrieben: {len(daten['results'])} Ergebnisse, {starter} Starter")
    print(f"Klassen    : {', '.join(klassen)}")
    print(f"Renntag    : {daten['datum']}")
    print("\nZum Veroeffentlichen das Pflege-Werkzeug beenden (dann wird")
    print("automatisch gepusht) oder im Live-Timing 'Einmal abgleichen'")
    print("NICHT benutzen - das wuerde die Beispieldaten sofort ersetzen.")


def h_frage_ja(text):
    import pflege_hilfen as h
    return h.frage_ja(text)


if __name__ == "__main__":
    main()
