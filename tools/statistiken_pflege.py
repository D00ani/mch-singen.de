# -*- coding: utf-8 -*-
"""
Interaktiv die Statistik-Seite pflegen (siehe README Abschnitt 5), ohne HTML
von Hand zu bearbeiten:
  - Top-Platzierungen
  - Wanderpokal-Sieger (Jugend/Erwachsen)
  - Vereinsbestleistungen (Rekord-Boxen)
  - Meilenstein-Zahlen (Gegruendet, Aktive Fahrer, Pokale, Mitglieder)
  - Diagramm-Werte inkl. Ueberschrift

Die Diagramm-Werte liegen in data/statistik.json - dadurch ist nach einer
Aenderung KEIN Build-Schritt noetig (frueher standen sie in js/statistiken.js).

Ausfuehren: python tools/statistiken_pflege.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
STATISTIKEN_HTML = os.path.join(ROOT, "pages", "statistiken.html")
STATISTIK_JSON = os.path.join(ROOT, "data", "statistik.json")

TABELLEN = [
    {
        "name": "Top-Platzierungen",
        "anker": "Unsere Top-Platzierungen",
        "spalten": ["Datum", "Fahrer/in", "Klasse", "Veranstaltung", "Platzierung"],
        "hervorhebbar": 4,
    },
    {
        "name": "Wanderpokal-Sieger (Jugend)",
        "anker": "Die Wanderpokal-Sieger (Jugend)",
        "spalten": ["Jahr", "Gewinner/in", "Klasse"],
        "hervorhebbar": None,
    },
    {
        "name": "Wanderpokal-Sieger (Erwachsen)",
        "anker": "Die Wanderpokal-Sieger (Erwachsen)",
        "spalten": ["Jahr", "Gewinner/in", "Klasse"],
        "hervorhebbar": None,
    },
]

DIAGRAMME = [
    {"id": "chartCurrent", "name": "Dieses Jahr (Bisher)", "automatisch": True},
    {"id": "chartGesamt", "name": "Gesamte Platzierungen (seit 2016)", "automatisch": False},
    {"id": "chart2025", "name": "Abgeschlossene Saison", "automatisch": False},
]

STRONG_MUSTER = re.compile(r"^<strong>(.*)</strong>$", re.DOTALL)


# ------------------------------------------------------------------
# Tabellen (Top-Platzierungen + Wanderpokale)
# ------------------------------------------------------------------

def finde_tbody(html, anker_text):
    pos = html.find(anker_text)
    if pos == -1:
        raise ValueError(f"Abschnitt '{anker_text}' nicht in statistiken.html gefunden.")
    start = html.find("<tbody>", pos)
    ende = html.find("</tbody>", start)
    if start == -1 or ende == -1:
        raise ValueError("Zugehoerige <tbody>...</tbody> nicht gefunden.")
    return start + len("<tbody>"), ende


def parse_zeilen(tbody_inhalt):
    return [re.findall(r"<td>(.*?)</td>", m.group(1), re.DOTALL)
            for m in re.finditer(r"<tr>(.*?)</tr>", tbody_inhalt, re.DOTALL)]


def erkenne_einrueckung(tbody_inhalt):
    m = re.search(r"[ \t]*<tr>", tbody_inhalt)
    return m.group(0)[:-len("<tr>")] if m else " " * 20


def ohne_hervorhebung(wert):
    treffer = STRONG_MUSTER.match(wert.strip())
    return (treffer.group(1), True) if treffer else (wert.strip(), False)


def baue_zeile(werte, einrueckung):
    return f"{einrueckung}<tr>" + "".join(f"<td>{w}</td>" for w in werte) + "</tr>"


def schreibe_tbody(html, start, ende, zeilen, einrueckung, tbody_inhalt):
    letzter = tbody_inhalt.rfind("</tr>")
    schluss = tbody_inhalt[letzter + len("</tr>"):] if letzter != -1 else "\r\n"
    if zeilen:
        neu = "\r\n" + "\r\n".join(baue_zeile(z, einrueckung) for z in zeilen) + schluss
    else:
        neu = schluss
    h.schreibe_datei(STATISTIKEN_HTML, html[:start] + neu + html[ende:])
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_HTML, ROOT)}")


def beschreibe_zeile(zeile):
    return " | ".join(ohne_hervorhebung(z)[0] for z in zeile)


def zeilen_schluessel(zeile):
    """Sortierwert einer Tabellenzeile - die erste Spalte ist bei allen
    Tabellen das Jahr bzw. das Datum."""
    return h.datum_schluessel(ohne_hervorhebung(zeile[0])[0] if zeile else "")


def bestaetige_neue_zeile(spalten, werte):
    """Letzter Schritt eines Formulars - mit 'x' geht es zurueck ins letzte Feld."""
    print(f"\nNeue Zeile: {beschreibe_zeile([werte[s] for s in spalten])}")
    return h.frage_ja("In die Tabelle einsortieren? (j/n): ")


def waehle_tabelle():
    return TABELLEN[h.waehle_option("Welche Tabelle?", TABELLEN, lambda t: t["name"])]


def tabelle_laden(tabelle):
    html = h.lies_datei(STATISTIKEN_HTML)
    start, ende = finde_tbody(html, tabelle["anker"])
    tbody_inhalt = html[start:ende]
    return html, start, ende, tbody_inhalt, parse_zeilen(tbody_inhalt), erkenne_einrueckung(tbody_inhalt)


def tabelle_hinzufuegen():
    tabelle = waehle_tabelle()
    html, start, ende, tbody_inhalt, zeilen, einrueckung = tabelle_laden(tabelle)

    print(f"\nAktuelle Eintraege in '{tabelle['name']}':")
    if zeilen:
        for i, z in enumerate(zeilen, start=1):
            print(f"  {i}) {beschreibe_zeile(z)}")
    else:
        print("  (noch keine)")

    print("\nNeuer Eintrag:")

    def feld(spalte, position):
        def abfrage(_):
            wert = h.frage(f"  {spalte}: ")
            if position == tabelle["hervorhebbar"] and h.frage_ja("  Fett hervorheben? (j/n): "):
                wert = f"<strong>{wert}</strong>"
            return wert
        return abfrage

    eingaben = h.formular(
        [(spalte, feld(spalte, position)) for position, spalte in enumerate(tabelle["spalten"])]
        + [("bestaetigt", lambda w: bestaetige_neue_zeile(tabelle["spalten"], w))]
    )
    if eingaben is None or not eingaben["bestaetigt"]:
        print("Abgebrochen.")
        return
    werte = [eingaben[spalte] for spalte in tabelle["spalten"]]

    # Nach Jahr bzw. Datum einsortieren (neueste zuerst), statt einfach
    # oben anzuhaengen.
    position = h.einfuege_position(
        [zeilen_schluessel(z) for z in zeilen], zeilen_schluessel(werte), absteigend=True
    )
    h.melde_einsortierung(position, len(zeilen))

    zeilen.insert(position, werte)
    schreibe_tbody(html, start, ende, zeilen, einrueckung, tbody_inhalt)


def tabelle_bearbeiten():
    tabelle = waehle_tabelle()
    html, start, ende, tbody_inhalt, zeilen, einrueckung = tabelle_laden(tabelle)

    index = h.waehle_aus_liste(zeilen, "bearbeiten", beschreibe_zeile)
    if index is None:
        return

    print(f"\nAktuell: {beschreibe_zeile(zeilen[index])}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.\n")

    def feld(spalte, position):
        def abfrage(_):
            alt_roh = zeilen[index][position] if position < len(zeilen[index]) else ""
            alt, war_fett = ohne_hervorhebung(alt_roh)
            neu = h.frage_mit_default(f"  {spalte}", alt)
            if war_fett:
                return f"<strong>{neu}</strong>"
            if position == tabelle["hervorhebbar"] and neu != alt and h.frage_ja("  Fett hervorheben? (j/n): "):
                return f"<strong>{neu}</strong>"
            return neu
        return abfrage

    def bestaetigen(werte):
        neue = [werte[spalte] for spalte in tabelle["spalten"]]
        print(f"\nAlt: {beschreibe_zeile(zeilen[index])}")
        print(f"Neu: {beschreibe_zeile(neue)}")
        return h.frage_ja("Aendern? (j/n): ")

    eingaben = h.formular(
        [(spalte, feld(spalte, position)) for position, spalte in enumerate(tabelle["spalten"])]
        + [("bestaetigt", bestaetigen)]
    )
    if eingaben is None or not eingaben["bestaetigt"]:
        print("Abgebrochen.")
        return

    zeilen[index] = [eingaben[spalte] for spalte in tabelle["spalten"]]
    schreibe_tbody(html, start, ende, zeilen, einrueckung, tbody_inhalt)


def tabelle_loeschen():
    tabelle = waehle_tabelle()
    html, start, ende, tbody_inhalt, zeilen, einrueckung = tabelle_laden(tabelle)

    index = h.waehle_aus_liste(zeilen, "loeschen", beschreibe_zeile)
    if index is None:
        return

    print(f"\nLoeschen: {beschreibe_zeile(zeilen[index])}")
    if not h.frage_ja("Wirklich loeschen? (j/n): "):
        print("Abgebrochen.")
        return

    del zeilen[index]
    schreibe_tbody(html, start, ende, zeilen, einrueckung, tbody_inhalt)


# ------------------------------------------------------------------
# Vereinsbestleistungen (Rekord-Boxen)
# ------------------------------------------------------------------

RECORD_BOX_MUSTER = re.compile(
    r'(<div class="record-box">\s*<h3>)(<i[^>]*></i>\s*)([^<]*?)(\s*</h3>\s*<p>)(.*?)(</p>\s*</div>)',
    re.DOTALL
)


def parse_record_boxes(html):
    boxen = []
    for m in RECORD_BOX_MUSTER.finditer(html):
        felder = []
        for teil in m.group(5).split("<br>"):
            fm = re.match(r"<strong>(.*?)</strong>\s*(.*)", teil.strip(), re.DOTALL)
            if fm:
                felder.append((fm.group(1).strip().rstrip(":"), fm.group(2).strip()))
        boxen.append({"match": m, "titel": m.group(3).strip(), "felder": felder})
    return boxen


def rekord_boxen_bearbeiten():
    html = h.lies_datei(STATISTIKEN_HTML)
    boxen = parse_record_boxes(html)

    index = h.waehle_aus_liste(
        boxen, "bearbeiten",
        lambda b: f"{b['titel']} - " + ", ".join(f"{label}: {wert}" for label, wert in b["felder"])
    )
    if index is None:
        return
    box = boxen[index]

    print(f"\nAktuell: {box['titel']}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.\n")

    felder = [("titel", lambda _: h.frage_mit_default("Titel", box["titel"]))]
    for nummer, (label, wert) in enumerate(box["felder"]):
        felder.append((f"label{nummer}", lambda _, l=label: h.frage_mit_default("  Feldname", l)))
        felder.append((f"wert{nummer}", lambda _, w=wert: h.frage_mit_default("  Wert", w)))

    def bestaetigen(werte):
        paare = [(werte[f"label{n}"], werte[f"wert{n}"]) for n in range(len(box["felder"]))]
        print(f"\nNeu: {werte['titel']} - " + ", ".join(f"{l}: {w}" for l, w in paare))
        return h.frage_ja("Aendern? (j/n): ")

    felder.append(("bestaetigt", bestaetigen))
    eingaben = h.formular(felder)
    if eingaben is None or not eingaben["bestaetigt"]:
        print("Abgebrochen.")
        return

    neuer_titel = eingaben["titel"]
    neue_felder = [(eingaben[f"label{n}"], eingaben[f"wert{n}"]) for n in range(len(box["felder"]))]

    m = box["match"]
    neuer_inhalt = "<br>".join(f"<strong>{label}:</strong> {wert}" for label, wert in neue_felder)
    ersatz = m.group(1) + m.group(2) + neuer_titel + m.group(4) + neuer_inhalt + m.group(6)

    h.schreibe_datei(STATISTIKEN_HTML, html[:m.start()] + ersatz + html[m.end():])
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_HTML, ROOT)}")


# ------------------------------------------------------------------
# Meilenstein-Zahlen
# ------------------------------------------------------------------

MEILENSTEIN_MUSTER = re.compile(
    r'(<span class="milestone-number" data-target=")(\d+)"([^>]*?)(>0</span>\s*'
    r'<span class="milestone-text"[^>]*>)(.*?)(</span>)',
    re.DOTALL
)


def meilensteine_bearbeiten():
    html = h.lies_datei(STATISTIKEN_HTML)
    treffer = list(MEILENSTEIN_MUSTER.finditer(html))
    if not treffer:
        print("\nKeine Meilenstein-Zahlen gefunden.")
        return

    def beschreibung(m):
        suffix = re.search(r'data-suffix="([^"]*)"', m.group(3))
        text = re.sub(r"<[^>]+>", " ", m.group(5)).strip()
        return f"{m.group(2)}{suffix.group(1) if suffix else ''} - {text}"

    index = h.waehle_aus_liste(treffer, "bearbeiten", beschreibung)
    if index is None:
        return
    m = treffer[index]

    suffix_treffer = re.search(r'data-suffix="([^"]*)"', m.group(3))
    alter_suffix = suffix_treffer.group(1) if suffix_treffer else ""

    print(f"\nAktuell: {beschreibung(m)}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.\n")

    def bestaetigen(werte):
        zusatz = "" if werte["suffix"] == "-" else werte["suffix"]
        print(f"\nNeu: {werte['zahl']}{zusatz}")
        return h.frage_ja("Aendern? (j/n): ")

    eingaben = h.formular([
        ("zahl", lambda _: h.frage_mit_default("Zahl", m.group(2), h.ZAHL_VALIDIERER)),
        ("suffix", lambda _: h.frage_mit_default("Zusatz hinter der Zahl ('-' = keiner)",
                                                 alter_suffix or "-", leer_erlaubt=True)),
        ("bestaetigt", bestaetigen),
    ])
    if eingaben is None or not eingaben["bestaetigt"]:
        print("Abgebrochen.")
        return

    neue_zahl = eingaben["zahl"]
    neuer_suffix = "" if eingaben["suffix"] == "-" else eingaben["suffix"]

    attribute = re.sub(r'\s*data-suffix="[^"]*"', "", m.group(3))
    if neuer_suffix:
        attribute += f' data-suffix="{neuer_suffix}"'

    ersatz = m.group(1) + neue_zahl + '"' + attribute + m.group(4) + m.group(5) + m.group(6)

    h.schreibe_datei(STATISTIKEN_HTML, html[:m.start()] + ersatz + html[m.end():])
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_HTML, ROOT)}")


# ------------------------------------------------------------------
# Diagramm-Werte (data/statistik.json) + Ueberschrift (HTML)
# ------------------------------------------------------------------

def lade_statistik_json():
    if not os.path.isfile(STATISTIK_JSON):
        return {}
    with open(STATISTIK_JSON, encoding="utf-8") as f:
        return json.load(f)


def speichere_statistik_json(daten):
    h.sicherung_anlegen(STATISTIK_JSON)
    os.makedirs(os.path.dirname(STATISTIK_JSON), exist_ok=True)
    with open(STATISTIK_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
        f.write("\n")


def chart_ueberschrift(html, chart_id):
    """Die <h3> gehoert zum selben Kasten wie das <canvas> und steht davor."""
    pos = html.find(f'id="{chart_id}"')
    if pos == -1:
        return None
    start = html.rfind("<h3", 0, pos)
    if start == -1:
        return None
    inhalt_start = html.find(">", start) + 1
    inhalt_ende = html.find("</h3>", inhalt_start)
    return inhalt_start, inhalt_ende, html[inhalt_start:inhalt_ende].strip()


def diagramme_bearbeiten():
    daten = lade_statistik_json()
    charts = {c["id"]: c for c in daten.get("charts", [])}
    html = h.lies_datei(STATISTIKEN_HTML)

    def beschreibung(d):
        ueberschrift = chart_ueberschrift(html, d["id"])
        titel = ueberschrift[2] if ueberschrift else d["name"]
        if d["automatisch"]:
            podium = daten.get("podium", {})
            werte = [podium.get("platz1"), podium.get("platz2"), podium.get("platz3")]
            return f"{titel}: {werte} (automatisch aus der Wertungs-PDF)"
        werte = charts.get(d["id"], {}).get("data", "noch nicht gesetzt")
        return f"{titel}: {werte}"

    index = h.waehle_aus_liste(DIAGRAMME, "bearbeiten", beschreibung)
    if index is None:
        return
    diagramm = DIAGRAMME[index]

    if diagramm["automatisch"]:
        print("\nDieses Diagramm wird automatisch aus der BKC-Wertungs-PDF berechnet")
        print("(Menuepunkt 'Jaehrliches technisches Update' bzw. tools/update_statistik.py).")
        print("Es sollte nicht von Hand geaendert werden.")
        return

    ueberschrift = chart_ueberschrift(html, diagramm["id"])
    inhalt_start = inhalt_ende = alter_titel = None
    if ueberschrift:
        inhalt_start, inhalt_ende, alter_titel = ueberschrift

    alte_werte = charts.get(diagramm["id"], {}).get("data", [0, 0, 0])
    print(f"\nAktuelle Werte: 1. Platz {alte_werte[0]}, 2. Platz {alte_werte[1]}, 3. Platz {alte_werte[2]}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.")

    felder = []
    if ueberschrift:
        felder.append(("titel", lambda _: h.frage_mit_default("\nUeberschrift", alter_titel)))
    for position, platz in enumerate((1, 2, 3)):
        felder.append((f"platz{platz}", lambda _, p=position, n=platz:
                       h.frage_mit_default(f"{n}. Platz", str(alte_werte[p]), h.ZAHL_VALIDIERER)))

    def bestaetigen(werte):
        titel = werte.get("titel") or diagramm["name"]
        print(f"\nNeu: {titel} - 1./2./3. Platz = "
              f"{werte['platz1']}/{werte['platz2']}/{werte['platz3']}")
        return h.frage_ja("Aendern? (j/n): ")

    felder.append(("bestaetigt", bestaetigen))
    eingaben = h.formular(felder)
    if eingaben is None or not eingaben["bestaetigt"]:
        print("Abgebrochen.")
        return

    neuer_titel = eingaben.get("titel")
    neue_werte = [int(eingaben[f"platz{platz}"]) for platz in (1, 2, 3)]

    liste = [c for c in daten.get("charts", []) if c["id"] != diagramm["id"]]
    liste.append({"id": diagramm["id"], "data": neue_werte})
    daten["charts"] = liste
    speichere_statistik_json(daten)
    print(f"Gespeichert in {os.path.relpath(STATISTIK_JSON, ROOT)}")

    if ueberschrift and neuer_titel != alter_titel:
        h.schreibe_datei(STATISTIKEN_HTML, html[:inhalt_start] + neuer_titel + html[inhalt_ende:])
        print(f"Ueberschrift in {os.path.relpath(STATISTIKEN_HTML, ROOT)} aktualisiert.")

    print("\nKein Build-Schritt noetig - die Werte werden beim Seitenaufruf gelesen.")


# ------------------------------------------------------------------
# Menue
# ------------------------------------------------------------------

def tabellen_menue():
    while True:
        aktion = h.menue("Tabellen-Eintrag:", [
            ("Hinzufuegen", tabelle_hinzufuegen),
            ("Bearbeiten", tabelle_bearbeiten),
            ("Loeschen", tabelle_loeschen),
        ])
        if aktion is None:
            return
        try:
            h.fuehre_aus(aktion)
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")


def main():
    print("=" * 60)
    print("  Statistiken-Seite pflegen")
    print("=" * 60)
    while True:
        aktion = h.menue("Was moechtest du pflegen?", [
            ("Tabellen (Top-Platzierungen, Wanderpokal-Sieger)", tabellen_menue),
            ("Vereinsbestleistungen (Rekord-Boxen)", rekord_boxen_bearbeiten),
            ("Meilenstein-Zahlen (Gegruendet, Fahrer, Pokale, Mitglieder)", meilensteine_bearbeiten),
            ("Diagramm-Werte und -Ueberschriften", diagramme_bearbeiten),
        ])
        if aktion is None:
            break
        try:
            h.fuehre_aus(aktion)
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")
    print("\nFertig.")


if __name__ == "__main__":
    main()
