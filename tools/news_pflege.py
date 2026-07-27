# -*- coding: utf-8 -*-
"""
Interaktiv die News-Karten auf der Seite "Aktuelles" pflegen, statt
<div class="news-card">-Bloecke von Hand zu kopieren.

Beim Bearbeiten werden gezielt nur Datum, Titel, Beschreibung und die Links
ersetzt - alles andere im Kasten (z. B. Kalender-Schaltflaechen mit onclick)
bleibt unangetastet.

Ausfuehren: python tools/news_pflege.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
AKTUELLES_HTML = os.path.join(ROOT, "pages", "aktuelles.html")

KARTEN_START = re.compile(r'<div class="news-card[^"]*">')
ABSCHNITT_MUSTER = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)

BADGES = [
    ("Wertung", 'news-badge news-badge-wertung'),
    ("Termine", 'news-badge news-badge-termin'),
    ("Kein Kennzeichen", None),
]


def finde_block_ende(html, start):
    """Findet das </div>, das den bei start beginnenden <div> schliesst."""
    tiefe = 0
    position = start
    for treffer in re.finditer(r"<div\b[^>]*>|</div>", html[start:]):
        position = start + treffer.end()
        tiefe += 1 if treffer.group(0).startswith("<div") else -1
        if tiefe == 0:
            return position
    return position


def text_von(muster, block):
    treffer = re.search(muster, block, re.DOTALL)
    if not treffer:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", treffer.group(1))).strip()


def finde_karten(html):
    karten = []
    for treffer in KARTEN_START.finditer(html):
        start = treffer.start()
        ende = finde_block_ende(html, start)
        block = html[start:ende]

        abschnitt = "?"
        vorherige = list(ABSCHNITT_MUSTER.finditer(html[:start]))
        if vorherige:
            abschnitt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", vorherige[-1].group(1))).strip()

        karten.append({
            "start": start,
            "ende": ende,
            "block": block,
            "abschnitt": abschnitt,
            "datum": text_von(r'<span class="news-date">(.*?)</span>', block),
            "titel": text_von(r"<h3>(.*?)</h3>", block),
            "beschreibung": text_von(r'<p class="news-card-desc">(.*?)</p>', block),
            "links": re.findall(r'<a\s+href="([^"]*)"', block),
            "hat_schaltflaechen": "onclick=" in block,
        })
    return karten


def beschreibe(karte):
    return f"[{karte['abschnitt']}] {karte['titel'] or '(ohne Titel)'} - {karte['datum'] or 'ohne Datum'}"


def ersetze_inhalt(block, muster, neuer_wert):
    treffer = re.search(muster, block, re.DOTALL)
    if not treffer:
        return block
    return block[:treffer.start(1)] + neuer_wert + block[treffer.end(1):]


def karte_bearbeiten():
    html = h.lies_datei(AKTUELLES_HTML)
    karten = finde_karten(html)

    index = h.waehle_aus_liste(karten, "bearbeiten", beschreibe)
    if index is None:
        return
    karte = karten[index]

    print(f"\nAktuell: {beschreibe(karte)}")
    if karte["beschreibung"]:
        print(f"Text: {karte['beschreibung']}")
    print("\nEnter = aktuellen Wert behalten, x = ein Feld zurueck.\n")

    felder = []
    if karte["datum"] is not None:
        felder.append(("datum", lambda _: h.frage_mit_default("Datum/Zeitraum", karte["datum"])))
    if karte["titel"] is not None:
        felder.append(("titel", lambda _: h.frage_mit_default("Titel", karte["titel"])))
    if karte["beschreibung"] is not None:
        felder.append(("beschreibung", lambda _: h.frage_mit_default("Beschreibung", karte["beschreibung"])))

    eingaben = h.formular(felder) if felder else {}
    if eingaben is None:
        print("Abgebrochen.")
        return

    block = karte["block"]
    if "datum" in eingaben:
        block = ersetze_inhalt(block, r'<span class="news-date">(.*?)</span>', eingaben["datum"])
    if "titel" in eingaben:
        block = ersetze_inhalt(block, r"<h3>(.*?)</h3>", eingaben["titel"])
    if "beschreibung" in eingaben:
        block = ersetze_inhalt(block, r'<p class="news-card-desc">(.*?)</p>', eingaben["beschreibung"])

    if karte["links"]:
        print("\nLinks in dieser Karte:")
        for i, link in enumerate(karte["links"], start=1):
            print(f"  {i}) {link}")
        if h.frage_ja("Einen Link aendern? (j/n): "):
            nummer = h.waehle_option("Welchen Link?", karte["links"])
            alt = karte["links"][nummer]
            neu = h.frage_medienpfad("Neues Ziel", default=alt)
            if neu != alt:
                block = block.replace(f'href="{alt}"', f'href="{neu}"', 1)

    if block == karte["block"]:
        print("\nNichts geaendert.")
        return

    print("\nAenderung wird gespeichert.")
    if not h.frage_ja("Uebernehmen? (j/n): "):
        print("Abgebrochen.")
        return

    h.schreibe_datei(AKTUELLES_HTML, html[:karte["start"]] + block + html[karte["ende"]:])
    print(f"\nGespeichert in {os.path.relpath(AKTUELLES_HTML, ROOT)}")


def karte_hinzufuegen():
    html = h.lies_datei(AKTUELLES_HTML)
    karten = finde_karten(html)
    if not karten:
        print("\nKeine bestehende News-Karte gefunden - Vorlage fehlt.")
        return

    abschnitte = []
    for karte in karten:
        if karte["abschnitt"] not in abschnitte:
            abschnitte.append(karte["abschnitt"])

    eingaben = h.formular([
        ("abschnitt", lambda _: abschnitte[
            h.waehle_option("In welchen Abschnitt soll die Karte?", abschnitte)]),
        ("badge", lambda _: BADGES[
            h.waehle_option("Kennzeichen (farbiges Etikett oben in der Karte):",
                            BADGES, lambda eintrag: eintrag[0])]),
        ("datum", lambda _: h.frage("Datum/Zeitraum (z. B. 'Saison 2026' oder 'Sa, 08.08.2026'): ")),
        ("titel", lambda _: h.frage("Titel: ")),
        ("beschreibung", lambda _: h.frage("Beschreibung: ")),
        ("link_ziel", lambda _: h.frage_medienpfad(
            "Link-Ziel (leer = kein Link, z. B. ../media/dokumente/datei.pdf)", pflicht=False)),
        ("link_text", lambda werte: h.frage("Link-Beschriftung: ") if werte["link_ziel"] else ""),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    abschnitt = eingaben["abschnitt"]
    badge_name, badge_klasse = eingaben["badge"]
    datum, titel = eingaben["datum"], eingaben["titel"]
    beschreibung = eingaben["beschreibung"]
    link_ziel, link_text = eingaben["link_ziel"], eingaben["link_text"]

    einrueckung = " " * 12
    teile = [f'{einrueckung}<div class="news-card">']
    if badge_klasse:
        teile.append(f'{einrueckung}    <span class="{badge_klasse}">{badge_name}</span>')
    teile += [
        f"{einrueckung}    <div>",
        f'{einrueckung}        <span class="news-date">{datum}</span>',
        f"{einrueckung}        <h3>{titel}</h3>",
        f'{einrueckung}        <p class="news-card-desc">{beschreibung}</p>',
        f"{einrueckung}    </div>",
    ]
    if link_ziel:
        extern = ' target="_blank"' if link_ziel.startswith("http") else ""
        symbol = "fa-file-pdf" if link_ziel.lower().endswith(".pdf") else "fa-circle-info"
        teile += [
            f'{einrueckung}    <a href="{link_ziel}"{extern} class="news-link">',
            f'{einrueckung}        <span class="news-icon"><i class="fa-solid {symbol}"></i></span> {link_text}',
            f"{einrueckung}    </a>",
        ]
    teile.append(f"{einrueckung}</div>")
    neuer_block = "\r\n".join(teile)

    print("\nNeue Karte:")
    print(neuer_block)
    if not h.frage_ja(f"\nIn '{abschnitt}' einfuegen? (j/n): "):
        print("Abgebrochen.")
        return

    # Direkt vor die erste bestehende Karte dieses Abschnitts setzen
    erste = next(k for k in karten if k["abschnitt"] == abschnitt)
    zeilenanfang = html.rfind("\r\n", 0, erste["start"])
    einfuegepunkt = zeilenanfang + 2 if zeilenanfang != -1 else erste["start"]
    h.schreibe_datei(AKTUELLES_HTML, html[:einfuegepunkt] + neuer_block + "\r\n" + html[einfuegepunkt:])
    print(f"\nGespeichert in {os.path.relpath(AKTUELLES_HTML, ROOT)}")


def karte_loeschen():
    html = h.lies_datei(AKTUELLES_HTML)
    karten = finde_karten(html)

    index = h.waehle_aus_liste(karten, "loeschen", beschreibe)
    if index is None:
        return
    karte = karten[index]

    print(f"\nLoeschen: {beschreibe(karte)}")
    if karte["hat_schaltflaechen"]:
        print("ACHTUNG: Diese Karte enthaelt Schaltflaechen (z. B. Kalender-Download).")
    if not h.frage_ja("Wirklich loeschen? (j/n): "):
        print("Abgebrochen.")
        return

    # Ganze Zeile(n) entfernen: von der Einrueckung am Zeilenanfang bis
    # einschliesslich des Zeilenumbruchs am Ende des Kastens.
    start = karte["start"]
    while start > 0 and html[start - 1] in " \t":
        start -= 1
    ende = karte["ende"]
    if html[ende:ende + 2] == "\r\n":
        ende += 2

    h.schreibe_datei(AKTUELLES_HTML, html[:start] + html[ende:])
    print(f"\nGeloescht. {os.path.relpath(AKTUELLES_HTML, ROOT)} aktualisiert.")


def main():
    print("=" * 60)
    print("  News-Karten auf 'Aktuelles' pflegen")
    print("=" * 60)
    while True:
        aktion = h.menue("Was moechtest du tun?", [
            ("Neue Karte hinzufuegen", karte_hinzufuegen),
            ("Karte bearbeiten", karte_bearbeiten),
            ("Karte loeschen", karte_loeschen),
        ])
        if aktion is None:
            break
        h.fuehre_aus(aktion)
    print("\nFertig.")


if __name__ == "__main__":
    main()
