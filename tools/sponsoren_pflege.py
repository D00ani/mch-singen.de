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


def _zeilenanfang(html, position):
    """Geht von position aus zurueck bis vor die Einrueckung der Zeile."""
    while position > 0 and html[position - 1] in " \t":
        position -= 1
    return position


def fuege_sponsor_ein(html, karte, sponsoren, stelle):
    """Setzt eine Bande an die gewaehlte Stelle. stelle 0 = ganz vorne."""
    if not sponsoren:
        anker = html.find(GRID_ANKER)
        einfuegepunkt = html.find("\r\n", anker) + 2
        return html[:einfuegepunkt] + karte + "\r\n" + html[einfuegepunkt:]
    if stelle == 0:
        anfang = _zeilenanfang(html, sponsoren[0]["match"].start())
        return html[:anfang] + karte + "\r\n" + html[anfang:]
    ende = sponsoren[stelle - 1]["match"].end()
    return html[:ende] + "\r\n" + karte + html[ende:]


def ersetze_sponsor(html, sponsor, karte):
    """Tauscht eine Bande gegen eine neu gebaute aus.

    Die vorhandene Einrueckung muss weichen - baue_karte bringt ihre
    eigene mit, sonst waechst sie bei jeder Aenderung um eine Stufe.
    """
    anfang = _zeilenanfang(html, sponsor["match"].start())
    return html[:anfang] + karte + html[sponsor["match"].end():]


def entferne_sponsor(html, sponsor):
    """Schneidet eine Bande samt ihrer Zeilen heraus."""
    anfang = _zeilenanfang(html, sponsor["match"].start())
    ende = sponsor["match"].end()
    if html[ende:ende + 2] == "\r\n":
        ende += 2
    return html[:anfang] + html[ende:]


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

    h.schreibe_datei(SPONSOREN_HTML,
                     fuege_sponsor_ein(html, neue_karte, sponsoren, stelle))
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

    h.schreibe_datei(SPONSOREN_HTML, ersetze_sponsor(html, sponsor, neue_karte))
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

    h.schreibe_datei(SPONSOREN_HTML, entferne_sponsor(html, sponsor))
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


# ------------------------------------------------------------------
# Linklisten: "Befreundete Vereine" und "Nuetzliche Links"
# ------------------------------------------------------------------

LINKLISTEN = [
    {"name": "Befreundete Vereine", "anker": "Befreundete Vereine"},
    {"name": "Nuetzliche Links", "anker": "Nützliche Links"},
]

LINK_MUSTER = re.compile(
    r'<li><a href="([^"]*)"[^>]*><i class="([^"]*)"></i>\s*(.*?)</a></li>'
)

# Haeufig gebrauchte Sinnbilder - freie Eingabe bleibt moeglich
SINNBILDER = [
    ("Zielflagge (Motorsport)", "fa-solid fa-flag-checkered"),
    ("Flagge", "fa-solid fa-flag"),
    ("Auto", "fa-solid fa-car"),
    ("Motorrad", "fa-solid fa-motorcycle"),
    ("Pokal", "fa-solid fa-trophy"),
    ("Stadt/Gebaeude", "fa-solid fa-city"),
    ("Diagramm (Ergebnisse)", "fa-solid fa-chart-line"),
    ("Verein/Gruppe", "fa-solid fa-users"),
    ("Kettenglied (allgemein)", "fa-solid fa-link"),
    ("Zielscheibe", "fa-solid fa-crosshairs"),
]


def finde_liste(html, anker):
    """Liefert (start, ende) des <ul>-Inhalts unter der passenden Ueberschrift."""
    pos = html.find(anker)
    if pos == -1:
        raise ValueError(f"Abschnitt '{anker}' nicht gefunden.")
    start = html.find("<ul class=\"link-card-grid\">", pos)
    if start == -1:
        raise ValueError(f"Liste unter '{anker}' nicht gefunden.")
    start += len("<ul class=\"link-card-grid\">")
    ende = html.find("</ul>", start)
    return start, ende


def finde_links(html, anker):
    start, ende = finde_liste(html, anker)
    inhalt = html[start:ende]
    return [{"link": m.group(1), "sinnbild": m.group(2), "name": m.group(3).strip()}
            for m in LINK_MUSTER.finditer(inhalt)], start, ende, inhalt


def baue_link(eintrag, einrueckung=" " * 12):
    extern = ' target="_blank" rel="noopener noreferrer"' if eintrag["link"].startswith("http") else ""
    return (f'{einrueckung}<li><a href="{eintrag["link"]}"{extern}>'
            f'<i class="{eintrag["sinnbild"]}"></i> {eintrag["name"]}</a></li>')


def schreibe_links(html, start, ende, eintraege, inhalt):
    einrueckung = " " * 12
    treffer = re.search(r"[ \t]*<li>", inhalt)
    if treffer:
        einrueckung = treffer.group(0)[:-len("<li>")]
    neu = "\r\n" + "\r\n".join(baue_link(e, einrueckung) for e in eintraege) + "\r\n" + " " * 8
    h.schreibe_datei(SPONSOREN_HTML, html[:start] + neu + html[ende:])
    print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")


def frage_sinnbild(vorgabe=None):
    moeglichkeiten = [f"{name}  ({klasse.split()[-1]})" for name, klasse in SINNBILDER]
    moeglichkeiten.append("Eigene Font-Awesome-Klasse eingeben")
    if vorgabe:
        moeglichkeiten.insert(0, f"Unveraendert lassen ({vorgabe.split()[-1]})")
    wahl = h.waehle_option("Welches Sinnbild?", moeglichkeiten)
    if vorgabe:
        if wahl == 0:
            return vorgabe
        wahl -= 1
    if wahl < len(SINNBILDER):
        return SINNBILDER[wahl][1]
    return h.frage("Font-Awesome-Klasse (z. B. 'fa-solid fa-star'): ")


def link_hinzufuegen(liste):
    html = lade_html()
    eintraege, start, ende, inhalt = finde_links(html, liste["anker"])

    eingaben = h.formular([
        ("name", lambda _: h.frage("Name: ")),
        ("link", lambda _: h.frage("Webadresse: ", h.LINK_VALIDIERER)),
        ("sinnbild", lambda _: frage_sinnbild()),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    neu = {"name": eingaben["name"], "link": eingaben["link"], "sinnbild": eingaben["sinnbild"]}
    print(f"\nNeu: {neu['name']} -> {neu['link']}")
    if not h.frage_ja("Hinzufuegen? (j/n): "):
        print("Abgebrochen.")
        return

    stelle = len(eintraege)
    if eintraege:
        moeglichkeiten = [f"Ganz oben (vor '{eintraege[0]['name']}')"]
        moeglichkeiten += [f"Nach '{e['name']}'" for e in eintraege]
        stelle = h.waehle_option("An welcher Stelle?", moeglichkeiten)

    eintraege.insert(stelle, neu)
    schreibe_links(html, start, ende, eintraege, inhalt)


def link_bearbeiten(liste):
    html = lade_html()
    eintraege, start, ende, inhalt = finde_links(html, liste["anker"])

    index = h.waehle_aus_liste(eintraege, "bearbeiten", lambda e: f"{e['name']}  ->  {e['link']}")
    if index is None:
        return
    alt = eintraege[index]

    print(f"\nAktuell: {alt['name']} -> {alt['link']}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.\n")
    eingaben = h.formular([
        ("name", lambda _: h.frage_mit_default("Name", alt["name"])),
        ("link", lambda _: h.frage_mit_default("Webadresse", alt["link"], h.LINK_VALIDIERER)),
        ("sinnbild", lambda _: frage_sinnbild(alt["sinnbild"])),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    print(f"\nNeu: {eingaben['name']} -> {eingaben['link']}")
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

    eintraege[index] = eingaben
    schreibe_links(html, start, ende, eintraege, inhalt)


def link_loeschen(liste):
    html = lade_html()
    eintraege, start, ende, inhalt = finde_links(html, liste["anker"])

    index = h.waehle_aus_liste(eintraege, "loeschen", lambda e: f"{e['name']}  ->  {e['link']}")
    if index is None:
        return

    print(f"\nLoeschen: {eintraege[index]['name']}")
    if not h.frage_ja("Wirklich loeschen? (j/n): "):
        print("Abgebrochen.")
        return

    del eintraege[index]
    schreibe_links(html, start, ende, eintraege, inhalt)


def linkliste_menue(liste):
    while True:
        try:
            eintraege, _, _, _ = finde_links(lade_html(), liste["anker"])
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")
            return
        print(f"\n{liste['name']}: {len(eintraege)} Eintraege")
        for i, e in enumerate(eintraege, start=1):
            print(f"  {i}) {e['name']}  ->  {e['link']}")

        aktion = h.menue(f"{liste['name']}:", [
            ("Eintrag hinzufuegen", lambda: link_hinzufuegen(liste)),
            ("Eintrag bearbeiten", lambda: link_bearbeiten(liste)),
            ("Eintrag entfernen", lambda: link_loeschen(liste)),
        ])
        if aktion is None:
            return
        h.fuehre_aus(aktion)


# ------------------------------------------------------------------
# Zahlen oben auf der Seite
# ------------------------------------------------------------------

ZAHL_MUSTER = re.compile(
    r'(<span class="milestone-number">)(.*?)(</span>\s*'
    r'<span class="milestone-text">)(.*?)(</span>)', re.DOTALL
)


def zahlen_bearbeiten():
    html = lade_html()
    treffer = list(ZAHL_MUSTER.finditer(html))
    if not treffer:
        print("\nKeine Zahlen gefunden.")
        return

    index = h.waehle_aus_liste(treffer, "bearbeiten", lambda m: f"{m.group(2)} - {m.group(4)}")
    if index is None:
        return
    m = treffer[index]

    print(f"\nAktuell: {m.group(2)} - {m.group(4)}")
    print("Enter = aktuellen Wert behalten, x = ein Feld zurueck.\n")
    eingaben = h.formular([
        ("zahl", lambda _: h.frage_mit_default("Zahl (z. B. 100+)", m.group(2))),
        ("text", lambda _: h.frage_mit_default("Beschriftung", m.group(4))),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    print(f"\nNeu: {eingaben['zahl']} - {eingaben['text']}")
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

    ersatz = m.group(1) + eingaben["zahl"] + m.group(3) + eingaben["text"] + m.group(5)
    h.schreibe_datei(SPONSOREN_HTML, html[:m.start()] + ersatz + html[m.end():])
    print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")


# ------------------------------------------------------------------
# Aufruf "Werde Sponsor"
# ------------------------------------------------------------------

VORTEIL_MUSTER = re.compile(
    r'(<div class="sponsor-cta-benefit">\s*<i class="[^"]*"></i>\s*<strong>)(.*?)(</strong>\s*<p>)(.*?)(</p>\s*</div>)',
    re.DOTALL
)
AUFRUF_TEXT_MUSTER = re.compile(
    r'(<div class="sponsor-cta-box">.*?<p[^>]*>)(.*?)(</p>)', re.DOTALL
)
AUFRUF_KNOPF_MUSTER = re.compile(
    r'(<a href="[^"]*" class="sponsor-cta-btn">\s*<i class="[^"]*"></i>)(.*?)(\s*</a>)', re.DOTALL
)


def aufruf_bearbeiten():
    html = lade_html()

    def einleitung_aendern():
        m = AUFRUF_TEXT_MUSTER.search(html)
        if not m:
            print("\nEinleitungstext nicht gefunden.")
            return
        print(f"\nAktuell: {m.group(2).strip()}")
        neu = h.frage_mit_default("\nNeuer Text", m.group(2).strip())
        if neu == m.group(2).strip() or not h.frage_ja("Aendern? (j/n): "):
            print("Abgebrochen.")
            return
        h.schreibe_datei(SPONSOREN_HTML,
                         html[:m.start(2)] + neu + html[m.end(2):])
        print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")

    def vorteile_aendern():
        treffer = list(VORTEIL_MUSTER.finditer(html))
        if not treffer:
            print("\nKeine Vorteils-Kaesten gefunden.")
            return
        index = h.waehle_aus_liste(treffer, "bearbeiten",
                                   lambda m: f"{m.group(2).strip()} - {m.group(4).strip()}")
        if index is None:
            return
        m = treffer[index]
        print(f"\nAktuell: {m.group(2).strip()}")
        eingaben = h.formular([
            ("titel", lambda _: h.frage_mit_default("Ueberschrift", m.group(2).strip())),
            ("text", lambda _: h.frage_mit_default("Text", m.group(4).strip())),
        ])
        if eingaben is None or not h.frage_ja("Aendern? (j/n): "):
            print("Abgebrochen.")
            return
        ersatz = m.group(1) + eingaben["titel"] + m.group(3) + eingaben["text"] + m.group(5)
        h.schreibe_datei(SPONSOREN_HTML, html[:m.start()] + ersatz + html[m.end():])
        print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")

    def knopf_aendern():
        m = AUFRUF_KNOPF_MUSTER.search(html)
        if not m:
            print("\nSchaltflaeche nicht gefunden.")
            return
        print(f"\nAktuell: {m.group(2).strip()}")
        neu = h.frage_mit_default("Beschriftung", m.group(2).strip())
        if not h.frage_ja("Aendern? (j/n): "):
            print("Abgebrochen.")
            return
        h.schreibe_datei(SPONSOREN_HTML, html[:m.start(2)] + " " + neu + html[m.end(2):])
        print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")

    aktion = h.menue("Was am Aufruf aendern?", [
        ("Einleitungstext", einleitung_aendern),
        ("Einen der drei Vorteils-Kaesten", vorteile_aendern),
        ("Beschriftung der Schaltflaeche", knopf_aendern),
    ])
    if aktion:
        h.fuehre_aus(aktion)


def logos_in_webp_umwandeln():
    """Wandelt noch als JPG/PNG eingebundene Logos in WebP um und stellt die
    Karten darauf um. Spart Ladezeit; WebP versteht heute jeder Browser."""
    html = lade_html()
    sponsoren = finde_sponsoren(html)

    offen = [s for s in sponsoren if not s["bild"].lower().endswith(".webp")]
    if not offen:
        print("\nAlle Logos sind bereits WebP.")
        return

    print(f"\n{len(offen)} Logo(s) sind noch JPG/PNG:")
    for sponsor in offen:
        print(f"  {sponsor['name']:28} {os.path.basename(sponsor['bild'])}")
    print("\nDas Werkzeug erzeugt die WebP-Fassung und bindet sie direkt ein.")
    print("Die alten JPG/PNG-Dateien bleiben zunaechst liegen.")
    if not h.frage_ja("Umwandeln? (j/n): "):
        print("Abgebrochen.")
        return

    alte_dateien = []
    for sponsor in sorted(offen, key=lambda s: -s["match"].start()):
        quelle = os.path.normpath(os.path.join(ROOT, "pages", sponsor["bild"]))
        if not os.path.isfile(quelle):
            print(f"  Uebersprungen (Datei fehlt): {sponsor['name']}")
            continue

        webp_name = erzeuge_webp(quelle)
        webp_relativ = f"../media/sponsoren/{webp_name}"
        masse = bildmasse(webp_relativ) or bildmasse(sponsor["bild"])
        breite, hoehe = anzeigegroesse(*masse)

        # WebP wird zur Hauptdatei, die getrennte <source>-Zeile entfaellt
        karte = baue_karte(sponsor["name"], sponsor["link"], webp_relativ, "", breite, hoehe)
        m = sponsor["match"]
        anfang = m.start()
        while anfang > 0 and html[anfang - 1] in " \t":
            anfang -= 1
        html = html[:anfang] + karte + html[m.end():]
        alte_dateien.append(quelle)
        print(f"  {sponsor['name']}: jetzt {webp_name} ({breite}x{hoehe})")

    h.schreibe_datei(SPONSOREN_HTML, html)
    print(f"\nGespeichert in {os.path.relpath(SPONSOREN_HTML, ROOT)}")

    if alte_dateien:
        print(f"\n{len(alte_dateien)} alte Bilddatei(en) werden nicht mehr gebraucht:")
        for pfad in alte_dateien:
            print(f"  {os.path.relpath(pfad, ROOT)} ({os.path.getsize(pfad) // 1024} KB)")
        if h.frage_ja("Jetzt loeschen? (j/n): "):
            for pfad in alte_dateien:
                os.remove(pfad)
            print("Geloescht.")
        else:
            print("Bleiben liegen - koennen jederzeit von Hand geloescht werden.")


def sponsoren_menue():
    while True:
        sponsoren = finde_sponsoren(lade_html())
        print(f"\nEingebunden: {len(sponsoren)} Sponsoren")
        for i, sponsor in enumerate(sponsoren, start=1):
            print(f"  {i}) {beschreibe(sponsor)}")

        aktion = h.menue("Sponsoren:", [
            ("Sponsor hinzufuegen (Logo einbinden)", sponsor_hinzufuegen),
            ("Sponsor bearbeiten (Name/Webseite)", sponsor_bearbeiten),
            ("Sponsor entfernen", sponsor_loeschen),
            ("Alle Logo-Groessen neu berechnen", groessen_neu_berechnen),
            ("Logos in WebP umwandeln (schnelleres Laden)", logos_in_webp_umwandeln),
        ])
        if aktion is None:
            return
        h.fuehre_aus(aktion)


def main():
    print("=" * 60)
    print("  Sponsoren-Seite pflegen")
    print("=" * 60)
    while True:
        aktion = h.menue("Welchen Bereich der Seite?", [
            ("Sponsoren (Logos)", sponsoren_menue),
            ("Befreundete Vereine", lambda: linkliste_menue(LINKLISTEN[0])),
            ("Nuetzliche Links", lambda: linkliste_menue(LINKLISTEN[1])),
            ("Zahlen oben (Gegruendet, Mitglieder, ...)", zahlen_bearbeiten),
            ("Aufruf 'Werde Sponsor'", aufruf_bearbeiten),
        ])
        if aktion is None:
            break
        h.fuehre_aus(aktion)
    print("\nFertig.")


if __name__ == "__main__":
    main()
