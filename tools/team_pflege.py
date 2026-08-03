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


FELD_MUSTER = {
    "kurzrolle": r'<p class="trainer-role-overlay">(.*?)</p>',
    "rolle": r'<p class="member-role">(.*?)</p>',
    "spruch": r'<p class="trainer-quote">(.*?)</p>',
}


def aendere_person(person, werte):
    """Setzt geaenderte Felder in den Kartenblock ein und gibt ihn zurueck.

    Gezielt einzelne Felder statt Neubau der Karte - so bleiben
    Besonderheiten erhalten (eigener Bildausschnitt, Instagram-Verlinkung).
    Ein geaenderter Name zieht an allen drei Stellen mit: Ueberschrift,
    Beschriftung im Bild und Bildbeschreibung.
    """
    block = person["block"]

    if werte.get("name") and werte["name"] != person["name"]:
        neu = werte["name"]
        block = ersetze_feld(block, r'<h3 class="trainer-name">(.*?)</h3>', neu)
        block = ersetze_feld(block, r'<p class="trainer-name-overlay">(.*?)</p>', neu)
        block = re.sub(rf'alt="(?:Trainer )?{re.escape(person["name"])}"',
                       lambda m: m.group(0).replace(person["name"], neu), block)

    for schluessel, muster in FELD_MUSTER.items():
        if schluessel in werte:
            block = ersetze_feld(block, muster, werte[schluessel])

    if "email" in werte and werte["email"] != person["email"] and person["email"]:
        block = block.replace(f'mailto:{person["email"]}', f'mailto:{werte["email"]}')
        block = re.sub(rf"(</i>\s*){re.escape(person['email'])}",
                       lambda m: m.group(1) + werte["email"], block)

    return block


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

    block = aendere_person(person, eingaben)

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


def bildmasse(bilddatei):
    """(breite, hoehe) des Fotos - oder (None, None), wenn Pillow fehlt."""
    if not Image:
        return None, None
    try:
        with Image.open(os.path.join(BILDER_DIR, bilddatei)) as bild:
            return bild.size
    except OSError:
        return None, None


def webp_fassung(bilddatei):
    stamm, _ = os.path.splitext(bilddatei)
    return f"{stamm}.webp" if os.path.isfile(os.path.join(BILDER_DIR, f"{stamm}.webp")) else ""


def baue_personen_karte(ist_vorstand, bilddatei, name, kurzrolle,
                        rolle="", email="", spruch="", einrueckung=" " * 12):
    """Baut den HTML-Block einer Personen-Karte.

    Vorstand bekommt Rolle und E-Mail, das Trainer-Team einen Spruch -
    beides ist optional und faellt weg, wenn nichts angegeben ist.
    """
    e = einrueckung
    webp = webp_fassung(bilddatei)
    breite, hoehe = bildmasse(bilddatei)
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
        f'{e}            <p class="trainer-role-overlay">{kurzrolle}</p>',
        f"{e}        </div>",
        f"{e}    </div>",
        f'{e}    <div class="trainer-info">',
        f'{e}        <h3 class="trainer-name">{name}</h3>',
    ]
    if ist_vorstand:
        zeilen.append(f'{e}        <p class="member-role">{rolle}</p>')
        if email:
            zeilen += [
                f'{e}        <p class="member-contact" style="margin-top: 8px; font-size: 0.9em;">',
                f'{e}            <a href="mailto:{email}" style="color: var(--text-color); text-decoration: none;">',
                f'{e}                <i class="fa-solid fa-envelope" style="color: var(--primary-blue); margin-right: 5px;"></i> {email}',
                f"{e}            </a>",
                f"{e}        </p>",
            ]
    elif spruch:
        zeilen.append(f'{e}        <p class="trainer-quote">{spruch}</p>')
    zeilen += [f"{e}    </div>", f"{e}</div>"]
    return "\r\n".join(zeilen)


def fuege_person_ein(html, karte, personen, stelle, grid_start):
    """Setzt eine Karte an die gewaehlte Stelle des Bereichs.

    stelle 0 = ganz vorne, sonst hinter personen[stelle - 1].
    """
    if not personen:
        einfuegepunkt = html.find("\r\n", grid_start) + 2
        return html[:einfuegepunkt] + karte + "\r\n" + html[einfuegepunkt:]
    if stelle == 0:
        anfang = personen[0]["start"]
        while anfang > 0 and html[anfang - 1] in " \t":
            anfang -= 1
        return html[:anfang] + karte + "\r\n\r\n" + html[anfang:]
    ende = personen[stelle - 1]["ende"]
    return html[:ende] + "\r\n\r\n" + karte + html[ende:]


def entferne_person(html, person):
    """Schneidet eine Personen-Karte samt ihrer Zeilen heraus."""
    anfang = person["start"]
    while anfang > 0 and html[anfang - 1] in " \t":
        anfang -= 1
    ende = person["ende"]
    while html[ende:ende + 2] == "\r\n":
        ende += 2
    return html[:anfang] + html[ende:]


def person_hinzufuegen(bereich):
    html = lade_html()
    personen, grid_start, _ = finde_personen(html, bereich["anker"])

    print("\nFoto auswaehlen (muss in media/bilder/ueber-uns/ liegen):")
    bilder = freie_bilder(html) or ["platzhalter.jpg"]
    bild_index = h.waehle_aus_liste(bilder, "verwenden", str)
    if bild_index is None:
        return
    bilddatei = bilder[bild_index]

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

    neue_karte = baue_personen_karte(
        ist_vorstand, bilddatei, eingaben["name"], eingaben["kurzrolle"],
        eingaben.get("rolle", ""), eingaben.get("email", ""), eingaben.get("spruch", ""))

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

    h.schreibe_datei(UEBER_UNS_HTML,
                     fuege_person_ein(html, neue_karte, personen, stelle, grid_start))
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

    h.schreibe_datei(UEBER_UNS_HTML, entferne_person(html, person))
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
