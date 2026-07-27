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


def waehle_tabelle():
    print("\nWelche Tabelle?")
    for i, t in enumerate(TABELLEN, start=1):
        print(f"  {i}) {t['name']}")
    wahl = h.frage(
        f"Auswahl (1-{len(TABELLEN)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(TABELLEN) else "Ungueltige Auswahl."
    )
    return TABELLEN[int(wahl) - 1]


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
    werte = []
    for position, spalte in enumerate(tabelle["spalten"]):
        wert = h.frage(f"  {spalte}: ")
        if position == tabelle["hervorhebbar"] and h.frage_ja("  Fett hervorheben? (j/n): "):
            wert = f"<strong>{wert}</strong>"
        werte.append(wert)

    print(f"\nNeue Zeile: {beschreibe_zeile(werte)}")
    if not h.frage_ja("Oben in die Tabelle einfuegen? (j/n): "):
        print("Abgebrochen.")
        return

    neue_zeile = baue_zeile(werte, einrueckung)
    erster_umbruch = tbody_inhalt.find("\r\n")
    if erster_umbruch == -1:
        neuer_inhalt = "\r\n" + neue_zeile + tbody_inhalt
    else:
        neuer_inhalt = (tbody_inhalt[:erster_umbruch + 2] + neue_zeile + "\r\n"
                        + tbody_inhalt[erster_umbruch + 2:])
    h.schreibe_datei(STATISTIKEN_HTML, html[:start] + neuer_inhalt + html[ende:])
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_HTML, ROOT)}")


def tabelle_bearbeiten():
    tabelle = waehle_tabelle()
    html, start, ende, tbody_inhalt, zeilen, einrueckung = tabelle_laden(tabelle)

    index = h.waehle_aus_liste(zeilen, "bearbeiten", beschreibe_zeile)
    if index is None:
        return

    print(f"\nAktuell: {beschreibe_zeile(zeilen[index])}")
    print("Enter = aktuellen Wert behalten.\n")
    neue_werte = []
    for position, spalte in enumerate(tabelle["spalten"]):
        alt_roh = zeilen[index][position] if position < len(zeilen[index]) else ""
        alt, war_fett = ohne_hervorhebung(alt_roh)
        neu = h.frage_mit_default(f"  {spalte}", alt)
        if war_fett:
            neu = f"<strong>{neu}</strong>"
        elif position == tabelle["hervorhebbar"] and neu != alt and h.frage_ja("  Fett hervorheben? (j/n): "):
            neu = f"<strong>{neu}</strong>"
        neue_werte.append(neu)

    print(f"\nAlt: {beschreibe_zeile(zeilen[index])}")
    print(f"Neu: {beschreibe_zeile(neue_werte)}")
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

    zeilen[index] = neue_werte
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
    neuer_titel = h.frage_mit_default("Titel", box["titel"])
    neue_felder = []
    for label, wert in box["felder"]:
        neues_label = h.frage_mit_default("  Feldname", label)
        neuer_wert = h.frage_mit_default("  Wert", wert)
        neue_felder.append((neues_label, neuer_wert))

    m = box["match"]
    neuer_inhalt = "<br>".join(f"<strong>{label}:</strong> {wert}" for label, wert in neue_felder)
    ersatz = m.group(1) + m.group(2) + neuer_titel + m.group(4) + neuer_inhalt + m.group(6)

    print(f"\nNeu: {neuer_titel} - " + ", ".join(f"{l}: {w}" for l, w in neue_felder))
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

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
    neue_zahl = h.frage_mit_default("Zahl", m.group(2), h.ZAHL_VALIDIERER)
    neuer_suffix = h.frage_mit_default("Zusatz hinter der Zahl ('-' = keiner)", alter_suffix or "-",
                                       leer_erlaubt=True)
    if neuer_suffix == "-":
        neuer_suffix = ""

    attribute = re.sub(r'\s*data-suffix="[^"]*"', "", m.group(3))
    if neuer_suffix:
        attribute += f' data-suffix="{neuer_suffix}"'

    ersatz = m.group(1) + neue_zahl + '"' + attribute + m.group(4) + m.group(5) + m.group(6)
    print(f"\nNeu: {neue_zahl}{neuer_suffix}")
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

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
    if ueberschrift:
        inhalt_start, inhalt_ende, alter_titel = ueberschrift
        neuer_titel = h.frage_mit_default("\nUeberschrift", alter_titel)
    else:
        neuer_titel = alter_titel = None

    alte_werte = charts.get(diagramm["id"], {}).get("data", [0, 0, 0])
    print(f"\nAktuelle Werte: 1. Platz {alte_werte[0]}, 2. Platz {alte_werte[1]}, 3. Platz {alte_werte[2]}")
    neue_werte = [
        int(h.frage_mit_default(f"{platz}. Platz", str(alte_werte[position]), h.ZAHL_VALIDIERER))
        for position, platz in enumerate((1, 2, 3))
    ]

    print(f"\nNeu: {neuer_titel or diagramm['name']} - 1./2./3. Platz = "
          f"{neue_werte[0]}/{neue_werte[1]}/{neue_werte[2]}")
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

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
            aktion()
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
            aktion()
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")
    print("\nFertig.")


if __name__ == "__main__":
    main()
