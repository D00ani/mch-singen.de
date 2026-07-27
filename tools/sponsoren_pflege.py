# -*- coding: utf-8 -*-
"""
Sponsoren auf pages/sponsoren-links.html pflegen.

Beim Anlegen erledigt das Werkzeug alles, was sonst Handarbeit waere:
WebP-Fassung erzeugen, die Anzeigegroesse so berechnen, dass jedes Logo
dieselbe FLAECHE einnimmt (sonst wirken hochkante Logos kleiner als
querformatige), und die fertige Banden-Karte einsortieren.

Ausfuehren: python tools/sponsoren_pflege.py
Benoetigt: pip install Pillow
"""
import math
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Pillow fehlt. Bitte einmalig ausfuehren:  pip install Pillow")
    sys.exit(1)

ROOT = h.ROOT
SPONSOREN_HTML = os.path.join(ROOT, "pages", "sponsoren-links.html")
LOGO_DIR = os.path.join(ROOT, "media", "sponsoren")

# So gross soll jedes Logo erscheinen. Die Flaeche ist der Massstab, nicht
# Breite oder Hoehe - nur so wirken quer- und hochformatige Logos gleich gross.
ZIEL_FLAECHE = 9500
MAX_BREITE = 150
MAX_HOEHE = 110
WEBP_QUALITAET = 82

GRID_ANKER = '<div class="sponsor-grid">'
KARTEN_MUSTER = re.compile(
    r'<a href="([^"]*)"[^>]*class="sponsor-card">\s*'
    r'<picture>\s*(?:<source[^>]*srcset="([^"]*)"[^>]*>\s*)?'
    r'<img src="([^"]*)"\s+alt="([^"]*)"[^>]*>\s*</picture>\s*'
    r'<span class="sponsor-card-name">(.*?)</span>\s*</a>',
    re.DOTALL,
)


def anzeigegroesse(breite, hoehe):
    """Groesse, bei der das Logo dieselbe Flaeche wie alle anderen einnimmt."""
    faktor = math.sqrt(ZIEL_FLAECHE / (breite * hoehe))
    faktor = min(faktor, MAX_BREITE / breite, MAX_HOEHE / hoehe)
    return round(breite * faktor), round(hoehe * faktor)


def lade_html():
    return h.lies_datei(SPONSOREN_HTML)


def finde_sponsoren(html):
    sponsoren = []
    for treffer in KARTEN_MUSTER.finditer(html):
        sponsoren.append({
            "match": treffer,
            "link": treffer.group(1),
            "webp": treffer.group(2) or "",
            "bild": treffer.group(3),
            "alt": treffer.group(4),
            "name": treffer.group(5).strip(),
        })
    return sponsoren


def beschreibe(sponsor):
    ziel = sponsor["link"] if sponsor["link"] not in ("#", "") else "(kein Link)"
    return f"{sponsor['name']}  ->  {ziel}"


def baue_karte(name, link, bild_relativ, webp_relativ, breite, hoehe, einrueckung=" " * 12):
    extern = ' target="_blank" rel="noopener noreferrer"' if link.startswith("http") else ' target="_blank"'
    zeilen = [
        f'{einrueckung}<a href="{link}"{extern} class="sponsor-card">',
        f"{einrueckung}    <picture>",
    ]
    if webp_relativ:
        zeilen.append(f'{einrueckung}        <source type="image/webp" srcset="{webp_relativ}">')
    zeilen += [
        f'{einrueckung}        <img src="{bild_relativ}" alt="{name}" loading="lazy" '
        f'width="{breite}" height="{hoehe}" decoding="async">',
        f"{einrueckung}    </picture>",
        f'{einrueckung}    <span class="sponsor-card-name">{name}</span>',
        f"{einrueckung}</a>",
    ]
    return "\r\n".join(zeilen)


def bildmasse(relativer_pfad):
    """relativer_pfad ist der Webpfad ab /pages/, z. B. ../media/sponsoren/x.jpg"""
    absolut = os.path.normpath(os.path.join(ROOT, "pages", relativer_pfad))
    if not os.path.isfile(absolut):
        return None
    with Image.open(absolut) as bild:
        return bild.size


def erzeuge_webp(quelle_absolut):
    """Erzeugt die WebP-Fassung neben dem Original und gibt deren Namen zurueck."""
    basis, endung = os.path.splitext(quelle_absolut)
    if endung.lower() == ".webp":
        return os.path.basename(quelle_absolut)

    ziel = basis + ".webp"
    with Image.open(quelle_absolut) as bild:
        fassung = ImageOps.exif_transpose(bild)
        if fassung.width > 400:
            neue_hoehe = round(fassung.height * 400 / fassung.width)
            fassung = fassung.resize((400, neue_hoehe), Image.LANCZOS)
            ziel = f"{basis}-400.webp"
        fassung.save(ziel, "WEBP", quality=WEBP_QUALITAET, method=6)
    print(f"  WebP erzeugt: {os.path.relpath(ziel, ROOT)} ({os.path.getsize(ziel) // 1024} KB)")
    return os.path.basename(ziel)


def freie_logodateien(html):
    """Logos im Ordner, die noch keiner Sponsoren-Karte zugeordnet sind."""
    schon_benutzt = set()
    for sponsor in finde_sponsoren(html):
        for pfad in (sponsor["bild"], sponsor["webp"]):
            if pfad:
                schon_benutzt.add(os.path.basename(pfad))

    frei = []
    for name in sorted(os.listdir(LOGO_DIR)):
        if not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        if name in schon_benutzt:
            continue
        # WebP-Ableitungen eines bereits genutzten Logos nicht anbieten
        stamm = re.sub(r"(-\d+)?\.webp$", "", name)
        if any(b.startswith(stamm + ".") for b in schon_benutzt):
            continue
        frei.append(os.path.join(LOGO_DIR, name))
    return frei


# ------------------------------------------------------------------
# Aktionen
# ------------------------------------------------------------------

def sponsor_hinzufuegen():
    html = lade_html()
    sponsoren = finde_sponsoren(html)

    kandidaten = freie_logodateien(html)
    if not kandidaten:
        print(f"\nKeine neuen Logos in {os.path.relpath(LOGO_DIR, ROOT)} gefunden.")
        print("Logo-Datei zuerst dort ablegen (Dateiname klein, ohne Umlaute/Leerzeichen).")
        return

    print("\nNoch nicht eingebundene Logos:")
    index = h.waehle_aus_liste(kandidaten, "einbinden", lambda p: os.path.basename(p))
    if index is None:
        return
    quelle = kandidaten[index]

    with Image.open(quelle) as bild:
        original_breite, original_hoehe = bild.size
    breite, hoehe = anzeigegroesse(original_breite, original_hoehe)
    print(f"\n  Original: {original_breite}x{original_hoehe} Pixel")
    print(f"  Wird angezeigt mit {breite}x{hoehe} Pixel (flaechengleich zu den anderen Logos)")

    eingaben = h.formular([
        ("name", lambda _: h.frage("\nName des Sponsors: ")),
        ("link", lambda _: h.frage("Webseite (leer = kein Link): ", pflicht=False)),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return
    name = eingaben["name"]
    link = eingaben["link"] or "#"

    webp_name = erzeuge_webp(quelle)
    bild_relativ = f"../media/sponsoren/{os.path.basename(quelle)}"
    webp_relativ = f"../media/sponsoren/{webp_name}" if webp_name != os.path.basename(quelle) else ""

    neue_karte = baue_karte(name, link, bild_relativ, webp_relativ, breite, hoehe)
    print("\nNeue Sponsoren-Bande:")
    print(neue_karte)
    if not h.frage_ja("\nEinfuegen? (j/n): "):
        print("Abgebrochen.")
        return

    stelle = 0
    if sponsoren:
        moeglichkeiten = [f"Ganz vorne (vor '{sponsoren[0]['name']}')"]
        moeglichkeiten += [f"Nach '{s['name']}'" for s in sponsoren]
        stelle = h.waehle_option("An welcher Stelle?", moeglichkeiten)

    if not sponsoren:
        anker = html.find(GRID_ANKER)
        einfuegepunkt = html.find("\r\n", anker) + 2
        neues_html = html[:einfuegepunkt] + neue_karte + "\r\n" + html[einfuegepunkt:]
    elif stelle == 0:
        anfang = sponsoren[0]["match"].start()
        while anfang > 0 and html[anfang - 1] in " \t":
            anfang -= 1
        neues_html = html[:anfang] + neue_karte + "\r\n" + html[anfang:]
    else:
        ende = sponsoren[stelle - 1]["match"].end()
        neues_html = html[:ende] + "\r\n" + neue_karte + html[ende:]

    h.schreibe_datei(SPONSOREN_HTML, neues_html)
    print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")


def sponsor_bearbeiten():
    html = lade_html()
    sponsoren = finde_sponsoren(html)

    index = h.waehle_aus_liste(sponsoren, "bearbeiten", beschreibe)
    if index is None:
        return
    sponsor = sponsoren[index]

    print(f"\nAktuell: {beschreibe(sponsor)}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.\n")

    eingaben = h.formular([
        ("name", lambda _: h.frage_mit_default("Name", sponsor["name"])),
        ("link", lambda _: h.frage_mit_default("Webseite ('-' = kein Link)",
                                               sponsor["link"], leer_erlaubt=True)),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    name = eingaben["name"]
    link = eingaben["link"] or "#"

    masse = bildmasse(sponsor["bild"])
    if masse:
        breite, hoehe = anzeigegroesse(*masse)
    else:
        print(f"  Hinweis: Bilddatei {sponsor['bild']} nicht gefunden - Groesse bleibt unveraendert.")
        alt = re.search(r'width="(\d+)"\s+height="(\d+)"', sponsor["match"].group(0))
        breite, hoehe = (int(alt.group(1)), int(alt.group(2))) if alt else (120, 80)

    neue_karte = baue_karte(name, link, sponsor["bild"], sponsor["webp"], breite, hoehe)
    print(f"\nNeu: {name} -> {link}")
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

    m = sponsor["match"]
    anfang = m.start()
    while anfang > 0 and html[anfang - 1] in " \t":
        anfang -= 1
    h.schreibe_datei(SPONSOREN_HTML, html[:anfang] + neue_karte + html[m.end():])
    print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")


def sponsor_loeschen():
    html = lade_html()
    sponsoren = finde_sponsoren(html)

    index = h.waehle_aus_liste(sponsoren, "loeschen", beschreibe)
    if index is None:
        return
    sponsor = sponsoren[index]

    print(f"\nLoeschen: {sponsor['name']}")
    print("HINWEIS: Die Logo-Dateien bleiben liegen, nur die Karte wird entfernt.")
    if not h.frage_ja("Wirklich loeschen? (j/n): "):
        print("Abgebrochen.")
        return

    m = sponsor["match"]
    anfang = m.start()
    while anfang > 0 and html[anfang - 1] in " \t":
        anfang -= 1
    ende = m.end()
    if html[ende:ende + 2] == "\r\n":
        ende += 2

    h.schreibe_datei(SPONSOREN_HTML, html[:anfang] + html[ende:])
    print(f"\nGeloescht. {os.path.relpath(SPONSOREN_HTML, ROOT)} aktualisiert.")


def groessen_neu_berechnen():
    """Rechnet die Anzeigegroessen aller Logos neu - z. B. nachdem ein Logo
    ausgetauscht wurde."""
    html = lade_html()
    sponsoren = finde_sponsoren(html)
    if not sponsoren:
        print("\nKeine Sponsoren gefunden.")
        return

    aenderungen = []
    for sponsor in sponsoren:
        masse = bildmasse(sponsor["bild"])
        if not masse:
            print(f"  Uebersprungen (Datei fehlt): {sponsor['name']}")
            continue
        neu = anzeigegroesse(*masse)
        alt_treffer = re.search(r'width="(\d+)"\s+height="(\d+)"', sponsor["match"].group(0))
        alt = (int(alt_treffer.group(1)), int(alt_treffer.group(2))) if alt_treffer else None
        if alt != neu:
            aenderungen.append((sponsor, alt, neu))

    if not aenderungen:
        print("\nAlle Groessen sind bereits korrekt.")
        return

    print(f"\n{len(aenderungen)} Logo(s) bekommen eine neue Groesse:")
    for sponsor, alt, neu in aenderungen:
        vorher = f"{alt[0]}x{alt[1]}" if alt else "ohne Angabe"
        print(f"  {sponsor['name']:28} {vorher:12} ->  {neu[0]}x{neu[1]}")

    if not h.frage_ja("\nUebernehmen? (j/n): "):
        print("Abgebrochen.")
        return

    # Von hinten nach vorne ersetzen, damit die Fundstellen gueltig bleiben
    for sponsor, _, (breite, hoehe) in sorted(aenderungen, key=lambda e: -e[0]["match"].start()):
        m = sponsor["match"]
        karte = baue_karte(sponsor["name"], sponsor["link"], sponsor["bild"],
                           sponsor["webp"], breite, hoehe)
        anfang = m.start()
        while anfang > 0 and html[anfang - 1] in " \t":
            anfang -= 1
        html = html[:anfang] + karte + html[m.end():]

    h.schreibe_datei(SPONSOREN_HTML, html)
    print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")


def main():
    print("=" * 60)
    print("  Sponsoren pflegen")
    print("=" * 60)
    while True:
        sponsoren = finde_sponsoren(lade_html())
        print(f"\nAktuell eingebunden: {len(sponsoren)} Sponsoren")
        for i, sponsor in enumerate(sponsoren, start=1):
            print(f"  {i}) {beschreibe(sponsor)}")

        aktion = h.menue("Was moechtest du tun?", [
            ("Sponsor hinzufuegen (Logo einbinden)", sponsor_hinzufuegen),
            ("Sponsor bearbeiten (Name/Webseite)", sponsor_bearbeiten),
            ("Sponsor entfernen", sponsor_loeschen),
            ("Alle Logo-Groessen neu berechnen", groessen_neu_berechnen),
        ])
        if aktion is None:
            break
        h.fuehre_aus(aktion)
    print("\nFertig.")


if __name__ == "__main__":
    main()
