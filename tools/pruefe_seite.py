# -*- coding: utf-8 -*-
"""
Prueft die Webseite auf Fehler, die auf GitHub Pages erst nach dem Push
auffallen wuerden:
  - tote Verweise (Seiten, PDFs, Bilder, CSS/JS)
  - falsche Gross-/Kleinschreibung (Windows ist tolerant, GitHub-Linux nicht!)
  - in timer.txt angekuendigte Kurzausschreibungen, die noch fehlen
  - veraltete minifizierte Dateien (Build-Schritt vergessen)

Ausfuehren: python tools/pruefe_seite.py
Wird ausserdem automatisch vor dem Veroeffentlichen aufgerufen.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT

VERWEIS_MUSTER = re.compile(
    r'(?:href|src)="([^"#?]+\.(?:html|pdf|jpg|jpeg|png|webp|gif|svg|mp4|css|js|ico|txt|json|xml))"'
)

# Quelldatei -> erzeugte Datei (siehe tools/build_assets.py, README Abschnitt 9)
BUILD_PAARE = [
    ("css/style.css", "css/bundle.min.css"),
    ("css/index.css", "css/index.min.css"),
    ("css/kartsport.css", "css/kartsport.min.css"),
    ("css/live.css", "css/live.min.css"),
]


def html_dateien():
    """Alle Seiten, die veroeffentlicht werden.

    Was Git ignoriert (.gitignore), geht nie online - z. B. die lokalen
    Entwurfs-Vorschauen vorschlag-*.html. Die werden nicht mitgeprueft,
    sonst meldet die Pruefung Dinge, die auf der Webseite nie auftauchen.
    """
    alle = sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                  glob.glob(os.path.join(ROOT, "pages", "*.html")))
    ignoriert = _von_git_ignoriert(alle)
    return [d for d in alle if d not in ignoriert]


def _von_git_ignoriert(dateien):
    """Teilmenge von dateien, die .gitignore ausschliesst. Ohne Git (oder
    ausserhalb des Repos) wird einfach nichts ausgeschlossen."""
    import subprocess
    if not dateien:
        return set()
    # Als Bytes mit "/" und "\n": im Textmodus macht Windows aus "\n" ein
    # "\r\n", und Git sucht dann nach "datei.html\r" - findet also nichts.
    eingabe = "\n".join(os.path.relpath(d, ROOT).replace(os.sep, "/") for d in dateien) + "\n"
    try:
        ergebnis = subprocess.run(
            ["git", "check-ignore", "--stdin"], cwd=ROOT,
            input=eingabe.encode("utf-8"), capture_output=True, timeout=10,
            creationflags=0x08000000 if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {os.path.normpath(os.path.join(ROOT, z.strip()))
            for z in ergebnis.stdout.decode("utf-8", "replace").splitlines() if z.strip()}


def exakt_vorhanden(pfad):
    """Prueft Schritt fuer Schritt, ob JEDER Pfadteil exakt so geschrieben auf
    der Platte liegt. Windows findet 'Foto.jpg' auch als 'foto.jpg' - der
    Linux-Server von GitHub nicht (README Abschnitt 8)."""
    pfad = os.path.normpath(pfad)
    if not os.path.exists(pfad):
        return False, None

    teile = []
    rest = pfad
    while True:
        rest, name = os.path.split(rest)
        if not name:
            break
        teile.append(name)
        if os.path.normpath(rest) == os.path.normpath(ROOT) or not rest:
            break
    teile.reverse()

    aktuell = rest if rest else ROOT
    for teil in teile:
        try:
            eintraege = os.listdir(aktuell)
        except OSError:
            return True, None
        if teil not in eintraege:
            richtig = next((e for e in eintraege if e.lower() == teil.lower()), None)
            return False, richtig
        aktuell = os.path.join(aktuell, teil)
    return True, None


# Jede Pruefung gibt es zweimal:
#   befunde_xyz()  - strukturiert (Datei, Pfad, Stelle ...), damit die
#                    Reparatur in tools/pruef_reparatur.py und im Pflege-
#                    Fenster weiss, WAS genau sie anfassen muss
#   pruefe_xyz()   - dieselben Funde als Textzeilen, wie bisher
# Das Feld "text" eines Befunds ist genau die Textzeile - es dient auch als
# Schluessel fuer ausgeblendete Hinweise (tools/pruefe_ausnahmen.json).

def verweis_ziel(html, verweis):
    """Absoluter Pfad, auf den ein Verweis in einer Seite zeigt."""
    # Verweise mit fuehrendem "/" zeigen ab der Wurzel der Webseite
    # (nutzt 404.html, weil die unter JEDER Adresse ausgeliefert wird).
    if verweis.startswith("/"):
        return os.path.normpath(os.path.join(ROOT, verweis.lstrip("/")))
    return os.path.normpath(os.path.join(os.path.dirname(html), verweis))


def befunde_verweise():
    tote, schreibweise = [], []
    for html in html_dateien():
        anzeige = os.path.relpath(html, ROOT)
        inhalt = open(html, encoding="utf-8").read()
        for verweis in VERWEIS_MUSTER.findall(inhalt):
            if verweis.startswith(("http://", "https://", "//", "mailto:", "tel:", "data:")):
                continue
            ziel = verweis_ziel(html, verweis)
            passt, richtig = exakt_vorhanden(ziel)
            befund = {"datei": html, "anzeige": anzeige, "verweis": verweis, "ziel": ziel}
            if not passt and richtig is None:
                befund["text"] = f"{anzeige}: {verweis}"
                tote.append(befund)
            elif not passt:
                befund["richtig"] = richtig
                befund["text"] = f"{anzeige}: {verweis} -> heisst wirklich '{richtig}'"
                schreibweise.append(befund)
    return tote, schreibweise


def pruefe_verweise():
    tote, schreibweise = befunde_verweise()
    return [b["text"] for b in tote], [b["text"] for b in schreibweise]


TIMER_DATEIEN = ("timer.txt", "timer_trial.txt")


def befunde_pdfs():
    fehlend = []
    for name in TIMER_DATEIEN:
        pfad = os.path.join(ROOT, "data", name)
        for zeile in h.lies_zeilen(pfad):
            teile = zeile.split(";")
            if len(teile) < 8 or not teile[7].strip():
                continue
            pdf = teile[7].strip()
            if not os.path.isfile(os.path.join(ROOT, pdf.lstrip("/"))):
                fehlend.append({
                    "datei": pfad, "name": name, "pdf": pdf,
                    "ziel": os.path.normpath(os.path.join(ROOT, pdf.lstrip("/"))),
                    "text": f"{name} ({teile[0]}.{teile[1]}.{teile[2]}): {pdf}",
                })
    return fehlend


def pruefe_angekuendigte_pdfs():
    return [b["text"] for b in befunde_pdfs()]


def pruefe_build_aktuell():
    veraltet = []
    for quelle, erzeugt in BUILD_PAARE:
        quellpfad, zielpfad = os.path.join(ROOT, quelle), os.path.join(ROOT, erzeugt)
        if not os.path.isfile(quellpfad) or not os.path.isfile(zielpfad):
            continue
        if os.path.getmtime(quellpfad) > os.path.getmtime(zielpfad):
            veraltet.append(f"{quelle} ist neuer als {erzeugt}")

    for quellpfad in glob.glob(os.path.join(ROOT, "js", "*.js")):
        if quellpfad.endswith(".min.js"):
            continue
        zielpfad = quellpfad.replace(".js", ".min.js")
        if os.path.isfile(zielpfad) and os.path.getmtime(quellpfad) > os.path.getmtime(zielpfad):
            veraltet.append(f"js/{os.path.basename(quellpfad)} ist neuer als die .min.js-Fassung")
    return veraltet


# ------------------------------------------------------------------
# Barrierefreiheit, Suchmaschinen, Datenschutz
# ------------------------------------------------------------------

IMG_MUSTER = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ID_MUSTER = re.compile(r'\bid="([^"]+)"')
TITEL_MUSTER = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
BESCHREIBUNG_MUSTER = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"', re.IGNORECASE)
OG_BILD_MUSTER = re.compile(r'<meta\s+property="og:image"', re.IGNORECASE)
CANONICAL_MUSTER = re.compile(r'<link\s+rel="canonical"', re.IGNORECASE)

# Externe Adressen, die eingebunden werden (Skripte, Rahmen, Stile, Bilder).
# Reine Text-Links (<a href>) zaehlen nicht - die laden nichts nach.
EINBINDUNG_MUSTER = re.compile(
    r'<(script|iframe|link|img|source)\b[^>]*?(?:src|href|data-src)="(https?://[^"]+)"',
    re.IGNORECASE)

# Hosts, die zur Seite selbst gehoeren und deshalb nichts nachladen
EIGENE_HOSTS = ("mch-singen.de", "www.mch-singen.de")

# Empfehlung von Google: Beschreibung zwischen 50 und 160 Zeichen
BESCHREIBUNG_MIN, BESCHREIBUNG_MAX = 50, 160


def befunde_alt_texte():
    """<img> ohne alt-Attribut. Ein LEERES alt ("") ist erlaubt und richtig
    fuer reine Deko-Bilder - gemeldet wird nur ein ganz fehlendes alt."""
    fehlend = []
    for html in html_dateien():
        anzeige = os.path.relpath(html, ROOT)
        for treffer in IMG_MUSTER.findall(open(html, encoding="utf-8").read()):
            if not re.search(r"\balt=", treffer, re.IGNORECASE):
                kurz = re.search(r'src="([^"]*)"', treffer)
                fehlend.append({
                    "datei": html, "anzeige": anzeige,
                    "src": kurz.group(1) if kurz else None, "tag": treffer,
                    "text": f"{anzeige}: {kurz.group(1) if kurz else treffer[:60]}",
                })
    return fehlend


def pruefe_alt_texte():
    return [b["text"] for b in befunde_alt_texte()]


def befunde_doppelte_ids():
    """Dieselbe id zweimal auf einer Seite - dann greift JavaScript immer nur
    auf die erste zu, und der Rest funktioniert stillschweigend nicht."""
    doppelte = []
    for html in html_dateien():
        gesehen, mehrfach = set(), set()
        for wert in ID_MUSTER.findall(open(html, encoding="utf-8").read()):
            (mehrfach if wert in gesehen else gesehen).add(wert)
        for wert in sorted(mehrfach):
            doppelte.append({"datei": html, "wert": wert, "suche": f'id="{wert}"',
                             "text": f"{os.path.relpath(html, ROOT)}: id=\"{wert}\""})
    return doppelte


def pruefe_doppelte_ids():
    return [b["text"] for b in befunde_doppelte_ids()]


def befunde_meta():
    """Titel, Beschreibung, Vorschaubild und canonical - das, was Google und
    WhatsApp anzeigen, wenn jemand die Seite teilt.

    art: titel, beschreibung_fehlt, beschreibung_kurz, beschreibung_lang,
         og_bild, canonical, beschreibung_doppelt
    """
    maengel = []
    beschreibungen = {}

    def melde(html, art, text):
        maengel.append({"datei": html, "art": art, "text": text})

    for html in html_dateien():
        if os.path.basename(html) in INTERNE_SEITEN:
            continue
        anzeige = os.path.relpath(html, ROOT)
        inhalt = open(html, encoding="utf-8").read()

        titel = TITEL_MUSTER.search(inhalt)
        if not titel or not titel.group(1).strip():
            melde(html, "titel", f"{anzeige}: <title> fehlt oder ist leer")

        beschreibung = BESCHREIBUNG_MUSTER.search(inhalt)
        if not beschreibung or not beschreibung.group(1).strip():
            melde(html, "beschreibung_fehlt",
                  f"{anzeige}: meta-description fehlt (Google zeigt dann irgendeinen Textschnipsel)")
        else:
            text = beschreibung.group(1).strip()
            if len(text) < BESCHREIBUNG_MIN:
                melde(html, "beschreibung_kurz",
                      f"{anzeige}: meta-description ist sehr kurz ({len(text)} Zeichen)")
            elif len(text) > BESCHREIBUNG_MAX:
                melde(html, "beschreibung_lang",
                      f"{anzeige}: meta-description wird abgeschnitten ({len(text)} von max. {BESCHREIBUNG_MAX} Zeichen)")
            beschreibungen.setdefault(text, []).append(html)

        if not OG_BILD_MUSTER.search(inhalt):
            melde(html, "og_bild", f"{anzeige}: og:image fehlt (kein Vorschaubild beim Teilen)")
        # 404.html wird unter jeder beliebigen Adresse ausgeliefert - ein
        # canonical waere dort schlicht falsch.
        if os.path.basename(html) != "404.html" and not CANONICAL_MUSTER.search(inhalt):
            melde(html, "canonical", f"{anzeige}: canonical-Link fehlt")

    for text, seiten in beschreibungen.items():
        if len(seiten) > 1:
            anzeigen = [os.path.relpath(s, ROOT) for s in seiten]
            maengel.append({"datei": seiten[0], "dateien": seiten, "art": "beschreibung_doppelt",
                            "text": f"gleiche meta-description auf: {', '.join(anzeigen)}"})

    return maengel


def pruefe_meta():
    return [b["text"] for b in befunde_meta()]


def klaro_dienste():
    """Namen der in js/klaro-config.js eingetragenen Dienste."""
    pfad = os.path.join(ROOT, "js", "klaro-config.js")
    if not os.path.isfile(pfad):
        return set()
    return set(re.findall(r"name:\s*'([^']+)'", open(pfad, encoding="utf-8").read()))


def pruefe_drittanbieter():
    """Externe Skripte/Rahmen/Schriften, die beim Aufruf der Seite Daten an
    Dritte senden. Jeder davon braucht einen Eintrag in js/klaro-config.js,
    sonst laedt er ohne Einwilligung (DSGVO)."""
    dienste = klaro_dienste()
    # Was Klaro bereits abdeckt, erkennt man am Namen des Dienstes im Host
    bekannt = {d.lower() for d in dienste}
    gefunden = {}

    for html in html_dateien():
        inhalt = open(html, encoding="utf-8").read()
        for tag, adresse in EINBINDUNG_MUSTER.findall(inhalt):
            host = adresse.split("/")[2].lower()
            if host in EIGENE_HOSTS:
                continue
            # Klaro-gesteuerte Einbindungen tragen data-name="<dienst>"
            if any(teil in host.replace(".", "") for teil in bekannt):
                continue
            gefunden.setdefault(host, set()).add(
                f"{os.path.relpath(html, ROOT)} (<{tag}>)")

    return [f"{host} - eingebunden in {', '.join(sorted(stellen))}"
            for host, stellen in sorted(gefunden.items())]


def externe_adressen():
    """Alle externen Links der Seite, einmalig gesammelt."""
    adressen = {}
    muster = re.compile(r'href="(https?://[^"#]+)"')
    for html in html_dateien():
        anzeige = os.path.relpath(html, ROOT)
        for adresse in muster.findall(open(html, encoding="utf-8").read()):
            if adresse.split("/")[2].lower() in EIGENE_HOSTS:
                continue
            adressen.setdefault(adresse, set()).add(anzeige)
    return adressen


def _adresse_erreichbar(adresse):
    """Gibt None zurueck, wenn alles in Ordnung ist, sonst den Grund."""
    import urllib.error
    import urllib.request

    kopf = {"User-Agent": "Mozilla/5.0 (MCH-Singen Linkpruefung)"}
    for methode in ("HEAD", "GET"):
        anfrage = urllib.request.Request(adresse, headers=kopf, method=methode)
        try:
            with urllib.request.urlopen(anfrage, timeout=12) as antwort:
                if antwort.status < 400:
                    return None
                return f"Status {antwort.status}"
        except urllib.error.HTTPError as fehler:
            if fehler.code in (403, 405, 501) and methode == "HEAD":
                continue  # Server mag kein HEAD - mit GET erneut versuchen
            if fehler.code in (403, 429):
                return None  # Bot-Abwehr, kein kaputter Link
            return f"Status {fehler.code}"
        except urllib.error.URLError as fehler:
            return f"nicht erreichbar ({fehler.reason})"
        except Exception as fehler:
            return f"Fehler ({fehler})"
    return None


def befunde_externe_links(fortschritt=True):
    """Ruft jede externe Adresse einmal auf. Braucht Internet und ein paar
    Sekunden - laeuft deshalb nur auf ausdrueckliche Anforderung."""
    from concurrent.futures import ThreadPoolExecutor

    adressen = externe_adressen()
    if not adressen:
        return []

    if fortschritt:
        print(f"\nPruefe {len(adressen)} externe Adresse(n) ...")

    kaputt = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        ergebnisse = list(pool.map(_adresse_erreichbar, adressen))
    for adresse, grund in zip(adressen, ergebnisse):
        if grund:
            seiten = sorted(adressen[adresse])
            kaputt.append({
                "adresse": adresse, "grund": grund,
                "dateien": [os.path.join(ROOT, s) for s in seiten],
                "text": f"{adresse}\n      {grund} - verlinkt auf {', '.join(seiten)}",
            })
    return kaputt


def pruefe_externe_links(fortschritt=True):
    return [b["text"] for b in befunde_externe_links(fortschritt)]


# ------------------------------------------------------------------
# Suchindex, Ladegewicht, Schreibweisen
# ------------------------------------------------------------------

SUCHE_JS = os.path.join(ROOT, "js", "suche.js")
SUCHE_EINTRAG = re.compile(
    r"url:\s*'([^']*)'\s*,\s*titel:\s*'([^']*)'\s*,\s*beschreibung:\s*'([^']*)'", re.DOTALL)

# Seiten, die bewusst nicht in der Suche auftauchen
NICHT_SUCHBAR = {"suche.html", "404.html", "underconstruction.html", "status.html"}

# Von tools/statusseite.py erzeugt: nur fuer uns, nicht fuer Besucher.
# Titel, Beschreibung und Vorschaubild braucht sie deshalb nicht.
INTERNE_SEITEN = {"status.html"}


def befunde_suchindex():
    """js/suche.js traegt die durchsuchbaren Seiten fest ein. Wird eine
    Seite neu angelegt, merkt das sonst niemand - sie ist dann ueber die
    Suche der Webseite einfach nicht auffindbar.

    art: fehlt (Seite nicht im Index), tot (Index zeigt ins Leere),
         leer (Titel oder Beschreibung leer)
    """
    if not os.path.isfile(SUCHE_JS):
        return []

    inhalt = open(SUCHE_JS, encoding="utf-8").read()
    eintraege = SUCHE_EINTRAG.findall(inhalt)
    im_index = {os.path.basename(url) for url, _, _ in eintraege}

    maengel = []
    for pfad in html_dateien():
        name = os.path.basename(pfad)
        if name in NICHT_SUCHBAR or name in im_index:
            continue
        maengel.append({"art": "fehlt", "name": name, "datei": pfad,
                        "text": f"{name} fehlt im Suchindex - ueber die Suche nicht auffindbar"})

    for url, titel, beschreibung in eintraege:
        # Der Index enthaelt auch Verweise nach draussen (z. B. den Shop) -
        # die zeigen auf keine eigene Seite und muessen nicht existieren.
        # Frueher wurde hier jede Adresse mit Punkt uebersprungen - also auch
        # "aktuelles.html" und "../index.html". Die Pruefung auf tote
        # Eintraege hat dadurch nie gegriffen.
        erstes = url.split("/")[0]
        if url.startswith(("http://", "https://", "//")) or (
                "." in erstes and erstes not in (".", "..") and not erstes.endswith(".html")):
            continue
        name = os.path.basename(url.rstrip("/")) or url
        # suche.js liegt in pages/ - die Adressen gelten von dort aus.
        # Ordner-Adressen ("../kurs-planer/") zeigen auf deren index.html.
        ziel = os.path.normpath(os.path.join(ROOT, "pages", url))
        if url.endswith("/"):
            ziel = os.path.join(ziel, "index.html")
        if not os.path.isfile(ziel):
            maengel.append({"art": "tot", "name": name, "url": url, "datei": SUCHE_JS,
                            "suche": f"url: '{url}'",
                            "text": f"Suchindex verweist auf {name} - diese Seite gibt es nicht"})
        elif not titel.strip() or not beschreibung.strip():
            maengel.append({"art": "leer", "name": name, "url": url, "datei": SUCHE_JS,
                            "suche": f"url: '{url}'",
                            "text": f"Suchindex-Eintrag {name}: Titel oder Beschreibung ist leer"})

    return maengel


def pruefe_suchindex():
    return [b["text"] for b in befunde_suchindex()]


# Was der Browser ungefragt nachlaedt (verlinkte PDFs gehoeren NICHT dazu)
LADE_TAG = re.compile(r"<(img|source|script|video|link|picture|/picture)\b([^>]*)>", re.IGNORECASE)
LADE_ATTR = re.compile(r'(src|srcset|href|poster)="([^"]+)"', re.IGNORECASE)

# Ab hier wird es auf einer Mobilverbindung unangenehm
LADEBUDGET_KB = 2500


def _dateigroesse(basis, verweis):
    pfad = verweis.strip().split(" ")[0]
    if not pfad or pfad.startswith(("http://", "https://", "//", "mailto:", "tel:", "#", "data:")):
        return 0, None
    voll = os.path.normpath(os.path.join(basis, pfad.lstrip("/")))
    if not os.path.isfile(voll):
        return 0, None
    return os.path.getsize(voll), voll


def seitengewicht(html):
    """(KB, groesste Einzeldatei) - was beim Aufruf der Seite wirklich laedt.

    Innerhalb eines <picture> holt der Browser genau EINE Fassung. Deshalb
    zaehlt hier nur die groesste davon (schlechtester Fall), nicht die Summe.
    """
    basis = os.path.dirname(html)
    inhalt = open(html, encoding="utf-8").read()

    summe = os.path.getsize(html)
    gesehen = set()
    groesste = (0, "")
    in_picture = False
    picture_kandidaten = []

    def uebernimm(groesse, voll):
        nonlocal summe, groesste
        if voll in gesehen:
            return
        gesehen.add(voll)
        summe += groesse
        if groesse > groesste[0]:
            groesste = (groesse, os.path.relpath(voll, ROOT).replace(os.sep, "/"))

    for tag, rest in LADE_TAG.findall(inhalt):
        tag = tag.lower()
        if tag == "picture":
            in_picture, picture_kandidaten = True, []
            continue
        if tag == "/picture":
            if picture_kandidaten:
                uebernimm(*max(picture_kandidaten, key=lambda e: e[0]))
            in_picture = False
            continue
        if tag == "link" and not re.search(r'rel="(stylesheet|icon|apple-touch-icon)"', rest, re.I):
            continue

        for attr, wert in LADE_ATTR.findall(rest):
            if tag == "link" and attr.lower() != "href":
                continue
            for teil in wert.split(","):
                groesse, voll = _dateigroesse(basis, teil)
                if not voll:
                    continue
                if in_picture and tag in ("source", "img"):
                    picture_kandidaten.append((groesse, voll))
                else:
                    uebernimm(groesse, voll)

    return summe // 1024, groesste


def befunde_ladebudget():
    schwer = []
    for pfad in html_dateien():
        kb, (groesste_kb, groesste_datei) = seitengewicht(pfad)
        if kb > LADEBUDGET_KB:
            anzeige = os.path.relpath(pfad, ROOT)
            schwer.append({"datei": pfad, "groesste": groesste_datei,
                           "text": f"{anzeige}: {kb / 1024:.1f} MB laden beim Aufruf "
                                   f"(groesste Datei: {groesste_datei}, {groesste_kb // 1024} KB)"})
    return sorted(schwer, key=lambda b: b["text"], reverse=True)


def pruefe_ladebudget():
    return [b["text"] for b in befunde_ladebudget()]


# Gewuenschte Schreibweise -> was stattdessen im Text steht.
# Abgeleitet aus dem Bestand: die jeweils klar haeufigere Form gewinnt.
SCHREIBWEISEN = [
    ("MCH Singen",         [r"MCH-Singen"]),
    ("Trialsport",         [r"Trial-Sport"]),
    ("Kartslalom",         [r"Kart-Slalom", r"Kart Slalom"]),
    ("Bodensee-Kart-Cup",  [r"Bodensee Kart Cup", r"Bodensee-Kart Cup"]),
    ("Kartsport",          [r"Kart-Sport"]),
]


def befunde_schreibweisen():
    """Vereinsbegriffe einheitlich halten. Ueber Jahre und mehrere Autoren
    driftet das auseinander, ohne dass es beim Lesen auffaellt."""
    treffer = []
    for pfad in html_dateien():
        anzeige = os.path.relpath(pfad, ROOT)
        inhalt = open(pfad, encoding="utf-8").read()
        # Nur sichtbarer Text - in Adressen und Klassennamen ist die
        # Schreibweise oft bewusst anders (z. B. trial-sport.html)
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", inhalt, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)

        for gewuenscht, falsche in SCHREIBWEISEN:
            for muster in falsche:
                anzahl = len(re.findall(muster, text))
                if anzahl:
                    treffer.append({"datei": pfad, "muster": muster, "gewuenscht": gewuenscht,
                                    "anzahl": anzahl,
                                    "text": f"{anzeige}: {anzahl}x \"{muster}\" - "
                                            f"ueblich ist \"{gewuenscht}\""})
    return treffer


def pruefe_schreibweisen():
    return [b["text"] for b in befunde_schreibweisen()]


# ------------------------------------------------------------------
# Ausgeblendete Hinweise
# ------------------------------------------------------------------
# Manche Hinweise sind bekannt und gewollt (z. B. eine lokale Testseite
# ohne Suchindex-Eintrag). Im Pflege-Fenster lassen sie sich ausblenden;
# gemerkt wird die Textzeile des Hinweises. Nur HINWEISE - echte Fehler
# (tote Verweise, Schreibweise, Build) lassen sich bewusst nicht
# ausblenden, sonst ginge ein kaputter Link unbemerkt online.

AUSNAHMEN_DATEI = os.path.join(ROOT, "tools", "pruefe_ausnahmen.json")


def ausnahmen():
    import json
    if not os.path.isfile(AUSNAHMEN_DATEI):
        return set()
    try:
        with open(AUSNAHMEN_DATEI, encoding="utf-8") as f:
            return set(json.load(f).get("ausgeblendet", []))
    except (OSError, ValueError):
        return set()


def ausnahmen_speichern(menge):
    import json
    with open(AUSNAHMEN_DATEI, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"ausgeblendet": sorted(menge)}, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ohne_ausgeblendete(eintraege, menge=None):
    """Filtert Textzeilen oder Befunde (dict mit "text") gegen die Liste."""
    menge = ausnahmen() if menge is None else menge
    return [e for e in eintraege
            if (e["text"] if isinstance(e, dict) else e) not in menge]


# ------------------------------------------------------------------
# Alles zusammen
# ------------------------------------------------------------------

def _abschnitt(ueberschrift, eintraege, nachsatz=None):
    if not eintraege:
        return
    print(f"\n{ueberschrift}")
    for eintrag in eintraege:
        print(f"  {eintrag}")
    if nachsatz:
        print(f"  -> {nachsatz}")


def pruefe_symbole():
    """Symbole, die benutzt werden, aber nicht mehr in der ausgelieferten
    Font-Awesome-Fassung stecken.

    css/all.min.css und die drei Schriftdateien enthalten nur noch die rund
    70 Symbole, die auf der Seite vorkommen (tools/icons_bauen.py) - das
    spart 290 KB pro Aufruf. Der Haken: kommt ueber ein Pflege-Werkzeug ein
    neues Symbol dazu, ist es NICHT enthalten und die Stelle bleibt einfach
    leer. Kein Fehler, kein Ersatzzeichen, nur eine Luecke. Deshalb hier.
    """
    treffer = []
    try:
        import icons_bauen
    except ImportError:
        return treffer

    ausgeliefert = os.path.join(ROOT, "css", "all.min.css")
    if not os.path.isfile(ausgeliefert):
        return treffer
    css = open(ausgeliefert, encoding="utf-8").read()

    vorhanden = set()
    for auswahl, _ in icons_bauen.REGEL.findall(css):
        for name in auswahl.split(","):
            vorhanden.add(name.lstrip("."))

    je_familie, herkunft = icons_bauen.sammle()
    for familie in sorted(je_familie):
        for name in sorted(je_familie[familie]):
            if name in vorhanden:
                continue
            wo = ", ".join(sorted(herkunft.get(name, []))[:3])
            treffer.append(f"{name} ({familie}) fehlt in css/all.min.css - benutzt in: {wo}")
    return treffer


def pruefe_alles(still=False, extern=False):
    """Fuehrt alle Pruefungen aus. Gibt True zurueck, wenn nichts Kritisches
    gefunden wurde. extern=True prueft zusaetzlich die Links ins Internet."""
    tote, schreibweise = pruefe_verweise()
    fehlende_pdfs = pruefe_angekuendigte_pdfs()
    veralteter_build = pruefe_build_aktuell()
    ohne_alt = pruefe_alt_texte()
    doppelte_ids = pruefe_doppelte_ids()
    meta_maengel = pruefe_meta()
    drittanbieter = pruefe_drittanbieter()
    suchindex = pruefe_suchindex()
    ladebudget = pruefe_ladebudget()
    schreibweisen = pruefe_schreibweisen()
    fehlende_symbole = pruefe_symbole()
    kaputte_links = pruefe_externe_links(fortschritt=not still) if extern else []

    # Ausgeblendete Hinweise (Pflege-Fenster -> Webseite pruefen) fallen weg
    menge = ausnahmen()
    vorher = sum(map(len, (fehlende_pdfs, ohne_alt, doppelte_ids, meta_maengel, drittanbieter,
                           kaputte_links, suchindex, ladebudget, schreibweisen, fehlende_symbole)))
    (fehlende_pdfs, ohne_alt, doppelte_ids, meta_maengel, drittanbieter, kaputte_links,
     suchindex, ladebudget, schreibweisen, fehlende_symbole) = (
        ohne_ausgeblendete(liste, menge) for liste in
        (fehlende_pdfs, ohne_alt, doppelte_ids, meta_maengel, drittanbieter, kaputte_links,
         suchindex, ladebudget, schreibweisen, fehlende_symbole))
    ausgeblendet = vorher - sum(map(len, (fehlende_pdfs, ohne_alt, doppelte_ids, meta_maengel,
                                          drittanbieter, kaputte_links, suchindex, ladebudget,
                                          schreibweisen, fehlende_symbole)))

    kritisch = bool(tote or schreibweise or veralteter_build)
    hinweise = bool(fehlende_pdfs or ohne_alt or doppelte_ids or meta_maengel
                    or drittanbieter or kaputte_links or suchindex
                    or ladebudget or schreibweisen or fehlende_symbole)

    if not still or kritisch or hinweise:
        print("\n" + "=" * 60)
        print("  Pruefergebnis")
        print("=" * 60)

    _abschnitt(f"FEHLER - {len(tote)} toter Verweis / tote Verweise (Link fuehrt ins Leere):",
               tote)

    _abschnitt(f"FEHLER - {len(schreibweise)}x falsche Gross-/Kleinschreibung\n"
               "(funktioniert lokal, aber NICHT auf dem GitHub-Server!):",
               schreibweise)

    _abschnitt(f"WARNUNG - {len(veralteter_build)}x Build-Schritt fehlt\n"
               "(die Aenderung ist online nicht sichtbar, siehe README Abschnitt 9):",
               veralteter_build,
               "Menuepunkt 'Technisches Update' oder tools/build_assets.py")

    _abschnitt(f"WARNUNG - {len(drittanbieter)} externe(r) Dienst(e) ohne Klaro-Eintrag\n"
               "(laedt ohne Einwilligung nach - DSGVO!):",
               drittanbieter,
               "Dienst in js/klaro-config.js eintragen oder Einbindung entfernen")

    _abschnitt(f"WARNUNG - {len(fehlende_symbole)} Symbol(e) nicht in der Schrift\n"
               "(die Stelle bleibt auf der Seite einfach leer):",
               fehlende_symbole,
               "python tools/icons_bauen.py neu laufen lassen")

    _abschnitt(f"WARNUNG - {len(kaputte_links)} externe(r) Link(s) antworten nicht:",
               kaputte_links,
               "Menuepunkt 'Sponsoren-Seite pflegen' bzw. Link im HTML korrigieren")

    _abschnitt(f"Hinweis - {len(suchindex)} Punkt(e) beim Suchindex\n"
               "(js/suche.js fuehrt die durchsuchbaren Seiten fest auf):",
               suchindex)

    _abschnitt(f"Hinweis - {len(ladebudget)} Seite(n) ueber {LADEBUDGET_KB // 1024} MB Ladegewicht\n"
               "(das laedt bei jedem Aufruf, auch am Handy):",
               ladebudget,
               "Menuepunkt 'Medien aufraeumen' zeigt, was sich verkleinern laesst")

    _abschnitt(f"Hinweis - {len(schreibweisen)} uneinheitliche Schreibweise(n):",
               schreibweisen)

    _abschnitt(f"Hinweis - {len(doppelte_ids)}x dieselbe id auf einer Seite\n"
               "(JavaScript findet dann nur das erste Element):",
               doppelte_ids)

    _abschnitt(f"Hinweis - {len(ohne_alt)} Bild(er) ohne alt-Text\n"
               "(Screenreader und Google sehen nichts):",
               ohne_alt,
               "Menuepunkt 'Bilder aufnehmen' fragt den alt-Text ab")

    _abschnitt(f"Hinweis - {len(meta_maengel)} Punkt(e) bei Titel/Beschreibung/Vorschaubild:",
               meta_maengel)

    _abschnitt(f"Hinweis - {len(fehlende_pdfs)} angekuendigte PDF-Datei(en) noch nicht hochgeladen\n"
               "(kein Fehler - der Download-Button bleibt einfach unsichtbar):",
               fehlende_pdfs,
               "Menuepunkt 'Ausschreibungs-PDF einpflegen'")

    if ausgeblendet and not still:
        print(f"\n({ausgeblendet} bekannte(r) Hinweis(e) ausgeblendet - "
              "Pflege-Fenster -> Webseite pruefen -> Wieder einblenden)")

    if not kritisch and not hinweise:
        if not still:
            print("\nAlles in Ordnung - keine Probleme gefunden.")
    elif not kritisch:
        print("\nKeine Fehler - nur die Hinweise oben.")

    return not kritisch


def main():
    print("=" * 60)
    print("  Webseite pruefen")
    print("=" * 60)

    # Nur nachfragen, wenn jemand davorsitzt. Im Hintergrund (ohne
    # Tastatur) hat die Frage den Lauf frueher endlos warten lassen.
    interaktiv = sys.stdin is not None and sys.stdin.isatty()

    extern = "--extern" in sys.argv
    if interaktiv and not extern:
        try:
            extern = h.frage_ja("\nAuch die Links ins Internet pruefen? "
                                "(dauert ein paar Sekunden) (j/n): ")
        except (h.Zurueck, EOFError):
            pass

    sauber = pruefe_alles(extern=extern)

    # Fehler gleich hier beheben (tote Verweise, Schreibweise, Build) -
    # dieselben Funktionen wie im Pflege-Fenster (tools/pruef_reparatur.py)
    if not sauber and interaktiv:
        try:
            if h.frage_ja("\nGefundene Fehler jetzt beheben? (j/n): "):
                import pruef_reparatur
                pruef_reparatur.terminal_reparatur()
        except (h.Zurueck, EOFError):
            pass


if __name__ == "__main__":
    main()
