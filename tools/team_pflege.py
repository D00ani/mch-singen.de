# -*- coding: utf-8 -*-
"""
Vorstand und Trainer-Team auf pages/ueber-uns.html pflegen.

Die Karten sind unterschiedlich aufgebaut: manche verlinken auf Instagram,
manche haben eine E-Mail-Adresse, manche einen Spruch. Beim Bearbeiten
werden deshalb gezielt einzelne Felder ersetzt - alles andere im Kasten
bleibt unangetastet.

Ausfuehren: python tools/team_pflege.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = h.ROOT
UEBER_UNS_HTML = os.path.join(ROOT, "pages", "ueber-uns.html")
BILDER_DIR = os.path.join(ROOT, "media", "bilder", "ueber-uns")

BEREICHE = [
    {"name": "Vorstand", "anker": "Unser Vorstand"},
    {"name": "Trainer-Team", "anker": "Unser Trainer-Team"},
]

KARTEN_START = re.compile(r'<(div|a)\b[^>]*class="trainer-card"')


def lade_html():
    return h.lies_datei(UEBER_UNS_HTML)


def finde_block_ende(html, start, tagname):
    """Findet das schliessende Tag zum Kasten, der bei start beginnt."""
    tiefe = 0
    position = start
    muster = re.compile(rf"<{tagname}\b[^>]*>|</{tagname}>")
    for treffer in muster.finditer(html, start):
        position = treffer.end()
        tiefe += 1 if not treffer.group(0).startswith("</") else -1
        if tiefe == 0:
            return position
    return position


def bereichsgrenzen(html, anker):
    pos = html.find(anker)
    if pos == -1:
        raise ValueError(f"Abschnitt '{anker}' nicht gefunden.")
    start = html.find('<div class="trainer-grid">', pos)
    if start == -1:
        raise ValueError(f"Kartenbereich unter '{anker}' nicht gefunden.")
    return start, finde_block_ende(html, start, "div")


def text_von(muster, block):
    treffer = re.search(muster, block, re.DOTALL)
    return treffer.group(1).strip() if treffer else None


def finde_personen(html, anker):
    start, ende = bereichsgrenzen(html, anker)
    personen = []
    for treffer in KARTEN_START.finditer(html, start, ende):
        karten_start = treffer.start()
        karten_ende = finde_block_ende(html, karten_start, treffer.group(1))
        block = html[karten_start:karten_ende]
        personen.append({
            "start": karten_start,
            "ende": karten_ende,
            "block": block,
            "name": text_von(r'<h3 class="trainer-name">(.*?)</h3>', block) or "?",
            "kurzrolle": text_von(r'<p class="trainer-role-overlay">(.*?)</p>', block),
            "rolle": text_von(r'<p class="member-role">(.*?)</p>', block),
            "spruch": text_von(r'<p class="trainer-quote">(.*?)</p>', block),
            "email": text_von(r'href="mailto:([^"]*)"', block),
            "instagram": text_von(r'<a class="trainer-card" href="([^"]*)"', block),
        })
    return personen, start, ende


def beschreibe(person):
    zusatz = person["rolle"] or person["kurzrolle"] or ""
    return f"{person['name']}" + (f"  -  {zusatz}" if zusatz else "")


def ersetze_feld(block, muster, neuer_wert):
    treffer = re.search(muster, block, re.DOTALL)
    if not treffer:
        return block
    return block[:treffer.start(1)] + neuer_wert + block[treffer.end(1):]


def person_bearbeiten(bereich):
    html = lade_html()
    personen, _, _ = finde_personen(html, bereich["anker"])

    index = h.waehle_aus_liste(personen, "bearbeiten", beschreibe)
    if index is None:
        return
    person = personen[index]

    print(f"\nAktuell: {person['name']}")
    for beschriftung, schluessel in [("Rolle (unter dem Namen)", "rolle"),
                                     ("Rolle (im Bild)", "kurzrolle"),
                                     ("Spruch", "spruch"), ("E-Mail", "email")]:
        if person[schluessel]:
            print(f"  {beschriftung}: {person[schluessel]}")
    print("\nEnter = unveraendert lassen, x = ein Feld zurueck.\n")

    felder = [("name", lambda _: h.frage_mit_default("Name", person["name"]))]
    if person["kurzrolle"] is not None:
        felder.append(("kurzrolle", lambda _: h.frage_mit_default("Rolle (im Bild)", person["kurzrolle"])))
    if person["rolle"] is not None:
        felder.append(("rolle", lambda _: h.frage_mit_default("Rolle (unter dem Namen)", person["rolle"])))
    if person["spruch"] is not None:
        felder.append(("spruch", lambda _: h.frage_mit_default("Spruch", person["spruch"])))
    if person["email"] is not None:
        felder.append(("email", lambda _: h.frage_mit_default("E-Mail", person["email"])))

    eingaben = h.formular(felder)
    if eingaben is None:
        print("Abgebrochen.")
        return

    block = person["block"]
    if eingaben["name"] != person["name"]:
        neu = eingaben["name"]
        block = ersetze_feld(block, r'<h3 class="trainer-name">(.*?)</h3>', neu)
        block = ersetze_feld(block, r'<p class="trainer-name-overlay">(.*?)</p>', neu)
        # alt-Text mitziehen, damit Bildbeschreibung und Name zusammenpassen
        block = re.sub(rf'alt="(?:Trainer )?{re.escape(person["name"])}"',
                       lambda m: m.group(0).replace(person["name"], neu), block)
    if "kurzrolle" in eingaben:
        block = ersetze_feld(block, r'<p class="trainer-role-overlay">(.*?)</p>', eingaben["kurzrolle"])
    if "rolle" in eingaben:
        block = ersetze_feld(block, r'<p class="member-role">(.*?)</p>', eingaben["rolle"])
    if "spruch" in eingaben:
        block = ersetze_feld(block, r'<p class="trainer-quote">(.*?)</p>', eingaben["spruch"])
    if "email" in eingaben and eingaben["email"] != person["email"]:
        block = block.replace(f'mailto:{person["email"]}', f'mailto:{eingaben["email"]}')
        block = re.sub(rf"(</i>\s*){re.escape(person['email'])}",
                       lambda m: m.group(1) + eingaben["email"], block)

    if block == person["block"]:
        print("\nNichts geaendert.")
        return
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

    h.schreibe_datei(UEBER_UNS_HTML, html[:person["start"]] + block + html[person["ende"]:])
    print(f"\nGespeichert in {os.path.relpath(UEBER_UNS_HTML, ROOT)}")


def freie_bilder(html):
    """Fotos im Ordner, die noch keiner Karte zugeordnet sind."""
    benutzt = set(re.findall(r'ueber-uns/([^"]+)', html))
    frei = []
    for name in sorted(os.listdir(BILDER_DIR)):
        if not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        if name in benutzt:
            continue
        stamm = re.sub(r"(-\d+)?\.(jpg|jpeg|png|webp)$", "", name, flags=re.I)
        if any(b.startswith(stamm) for b in benutzt):
            continue
        frei.append(name)
    return frei


def person_hinzufuegen(bereich):
    html = lade_html()
    personen, grid_start, _ = finde_personen(html, bereich["anker"])

    print("\nFoto auswaehlen (muss in media/bilder/ueber-uns/ liegen):")
    bilder = freie_bilder(html) or ["platzhalter.jpg"]
    bild_index = h.waehle_aus_liste(bilder, "verwenden", str)
    if bild_index is None:
        return
    bilddatei = bilder[bild_index]

    stamm, _ = os.path.splitext(bilddatei)
    webp = f"{stamm}.webp" if os.path.isfile(os.path.join(BILDER_DIR, f"{stamm}.webp")) else ""

    breite = hoehe = None
    if Image:
        try:
            with Image.open(os.path.join(BILDER_DIR, bilddatei)) as bild:
                breite, hoehe = bild.size
        except OSError:
            pass

    ist_vorstand = bereich["name"] == "Vorstand"
    felder = [
        ("name", lambda _: h.frage("\nName: ")),
        ("kurzrolle", lambda _: h.frage("Rolle (kurz, erscheint im Bild): ")),
    ]
    if ist_vorstand:
        felder += [
            ("rolle", lambda _: h.frage("Rolle (ausfuehrlich, unter dem Namen): ")),
            ("email", lambda _: h.frage("E-Mail (leer = keine): ", pflicht=False)),
        ]
    else:
        felder.append(("spruch", lambda _: h.frage("Spruch (leer = keiner): ", pflicht=False)))

    eingaben = h.formular(felder)
    if eingaben is None:
        print("Abgebrochen.")
        return

    name = eingaben["name"]
    e = " " * 12
    masse = f' width="{breite}" height="{hoehe}"' if breite else ""
    alt_text = name if ist_vorstand else f"Trainer {name}"

    zeilen = [
        f'{e}<div class="trainer-card">',
        f'{e}    <div class="trainer-img-wrapper">',
        f"{e}        <picture>",
    ]
    if webp:
        zeilen.append(f'{e}            <source type="image/webp" srcset="../media/bilder/ueber-uns/{webp}">')
    zeilen += [
        f'{e}            <img src="../media/bilder/ueber-uns/{bilddatei}" alt="{alt_text}" '
        f'class="trainer-img" loading="lazy"{masse} decoding="async">',
        f"{e}        </picture>",
        f'{e}        <div class="trainer-img-overlay">',
        f'{e}            <p class="trainer-name-overlay">{name}</p>',
        f'{e}            <p class="trainer-role-overlay">{eingaben["kurzrolle"]}</p>',
        f"{e}        </div>",
        f"{e}    </div>",
        f'{e}    <div class="trainer-info">',
        f'{e}        <h3 class="trainer-name">{name}</h3>',
    ]
    if ist_vorstand:
        zeilen.append(f'{e}        <p class="member-role">{eingaben["rolle"]}</p>')
        if eingaben.get("email"):
            zeilen += [
                f'{e}        <p class="member-contact" style="margin-top: 8px; font-size: 0.9em;">',
                f'{e}            <a href="mailto:{eingaben["email"]}" style="color: var(--text-color); text-decoration: none;">',
                f'{e}                <i class="fa-solid fa-envelope" style="color: var(--primary-blue); margin-right: 5px;"></i> {eingaben["email"]}',
                f"{e}            </a>",
                f"{e}        </p>",
            ]
    elif eingaben.get("spruch"):
        zeilen.append(f'{e}        <p class="trainer-quote">{eingaben["spruch"]}</p>')
    zeilen += [f"{e}    </div>", f"{e}</div>"]
    neue_karte = "\r\n".join(zeilen)

    print("\nNeue Karte:")
    print(neue_karte)
    if not h.frage_ja(f"\nIn '{bereich['name']}' einfuegen? (j/n): "):
        print("Abgebrochen.")
        return

    stelle = len(personen)
    if personen:
        moeglichkeiten = [f"Ganz vorne (vor '{personen[0]['name']}')"]
        moeglichkeiten += [f"Nach '{p['name']}'" for p in personen]
        stelle = h.waehle_option("An welcher Stelle?", moeglichkeiten)

    if not personen:
        einfuegepunkt = html.find("\r\n", grid_start) + 2
        neues_html = html[:einfuegepunkt] + neue_karte + "\r\n" + html[einfuegepunkt:]
    elif stelle == 0:
        anfang = personen[0]["start"]
        while anfang > 0 and html[anfang - 1] in " \t":
            anfang -= 1
        neues_html = html[:anfang] + neue_karte + "\r\n\r\n" + html[anfang:]
    else:
        ende = personen[stelle - 1]["ende"]
        neues_html = html[:ende] + "\r\n\r\n" + neue_karte + html[ende:]

    h.schreibe_datei(UEBER_UNS_HTML, neues_html)
    print(f"\nGespeichert in {os.path.relpath(UEBER_UNS_HTML, ROOT)}")


def person_loeschen(bereich):
    html = lade_html()
    personen, _, _ = finde_personen(html, bereich["anker"])

    index = h.waehle_aus_liste(personen, "entfernen", beschreibe)
    if index is None:
        return
    person = personen[index]

    print(f"\nEntfernen: {beschreibe(person)}")
    print("HINWEIS: Das Foto bleibt liegen, nur die Karte wird entfernt.")
    if not h.frage_ja("Wirklich entfernen? (j/n): "):
        print("Abgebrochen.")
        return

    anfang = person["start"]
    while anfang > 0 and html[anfang - 1] in " \t":
        anfang -= 1
    ende = person["ende"]
    while html[ende:ende + 2] == "\r\n":
        ende += 2

    h.schreibe_datei(UEBER_UNS_HTML, html[:anfang] + html[ende:])
    print(f"\nEntfernt. {os.path.relpath(UEBER_UNS_HTML, ROOT)} aktualisiert.")


def bereich_menue(bereich):
    while True:
        try:
            personen, _, _ = finde_personen(lade_html(), bereich["anker"])
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")
            return
        print(f"\n{bereich['name']}: {len(personen)} Personen")
        for i, person in enumerate(personen, start=1):
            print(f"  {i}) {beschreibe(person)}")

        aktion = h.menue(f"{bereich['name']}:", [
            ("Person hinzufuegen", lambda: person_hinzufuegen(bereich)),
            ("Person bearbeiten", lambda: person_bearbeiten(bereich)),
            ("Person entfernen", lambda: person_loeschen(bereich)),
        ])
        if aktion is None:
            return
        h.fuehre_aus(aktion)


def main():
    print("=" * 60)
    print("  Vorstand & Trainer pflegen")
    print("=" * 60)
    while True:
        aktion = h.menue("Welcher Bereich?", [
            (b["name"], (lambda bereich: lambda: bereich_menue(bereich))(b))
            for b in BEREICHE
        ])
        if aktion is None:
            break
        h.fuehre_aus(aktion)
    print("\nFertig.")


if __name__ == "__main__":
    main()
