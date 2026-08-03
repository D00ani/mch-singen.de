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
    return sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                  glob.glob(os.path.join(ROOT, "pages", "*.html")))


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


def pruefe_verweise():
    tote, schreibweise = [], []
    for html in html_dateien():
        basis = os.path.dirname(html)
        anzeige = os.path.relpath(html, ROOT)
        inhalt = open(html, encoding="utf-8").read()
        for verweis in VERWEIS_MUSTER.findall(inhalt):
            if verweis.startswith(("http://", "https://", "//", "mailto:", "tel:", "data:")):
                continue
            # Verweise mit fuehrendem "/" zeigen ab der Wurzel der Webseite
            # (nutzt 404.html, weil die unter JEDER Adresse ausgeliefert wird).
            if verweis.startswith("/"):
                ziel = os.path.normpath(os.path.join(ROOT, verweis.lstrip("/")))
            else:
                ziel = os.path.normpath(os.path.join(basis, verweis))
            passt, richtig = exakt_vorhanden(ziel)
            if not passt and richtig is None:
                tote.append(f"{anzeige}: {verweis}")
            elif not passt:
                schreibweise.append(f"{anzeige}: {verweis} -> heisst wirklich '{richtig}'")
    return tote, schreibweise


def pruefe_angekuendigte_pdfs():
    fehlend = []
    for name in ("timer.txt", "timer_trial.txt"):
        pfad = os.path.join(ROOT, "data", name)
        for zeile in h.lies_zeilen(pfad):
            teile = zeile.split(";")
            if len(teile) < 8 or not teile[7].strip():
                continue
            if not os.path.isfile(os.path.join(ROOT, teile[7].strip().lstrip("/"))):
                fehlend.append(f"{name} ({teile[0]}.{teile[1]}.{teile[2]}): {teile[7].strip()}")
    return fehlend


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


def pruefe_alt_texte():
    """<img> ohne alt-Attribut. Ein LEERES alt ("") ist erlaubt und richtig
    fuer reine Deko-Bilder - gemeldet wird nur ein ganz fehlendes alt."""
    fehlend = []
    for html in html_dateien():
        anzeige = os.path.relpath(html, ROOT)
        for treffer in IMG_MUSTER.findall(open(html, encoding="utf-8").read()):
            if not re.search(r"\balt=", treffer, re.IGNORECASE):
                kurz = re.search(r'src="([^"]*)"', treffer)
                fehlend.append(f"{anzeige}: {kurz.group(1) if kurz else treffer[:60]}")
    return fehlend


def pruefe_doppelte_ids():
    """Dieselbe id zweimal auf einer Seite - dann greift JavaScript immer nur
    auf die erste zu, und der Rest funktioniert stillschweigend nicht."""
    doppelte = []
    for html in html_dateien():
        gesehen, mehrfach = set(), set()
        for wert in ID_MUSTER.findall(open(html, encoding="utf-8").read()):
            (mehrfach if wert in gesehen else gesehen).add(wert)
        for wert in sorted(mehrfach):
            doppelte.append(f"{os.path.relpath(html, ROOT)}: id=\"{wert}\"")
    return doppelte


def pruefe_meta():
    """Titel, Beschreibung, Vorschaubild und canonical - das, was Google und
    WhatsApp anzeigen, wenn jemand die Seite teilt."""
    maengel = []
    beschreibungen = {}

    for html in html_dateien():
        anzeige = os.path.relpath(html, ROOT)
        inhalt = open(html, encoding="utf-8").read()

        titel = TITEL_MUSTER.search(inhalt)
        if not titel or not titel.group(1).strip():
            maengel.append(f"{anzeige}: <title> fehlt oder ist leer")

        beschreibung = BESCHREIBUNG_MUSTER.search(inhalt)
        if not beschreibung or not beschreibung.group(1).strip():
            maengel.append(f"{anzeige}: meta-description fehlt (Google zeigt dann irgendeinen Textschnipsel)")
        else:
            text = beschreibung.group(1).strip()
            if len(text) < BESCHREIBUNG_MIN:
                maengel.append(f"{anzeige}: meta-description ist sehr kurz ({len(text)} Zeichen)")
            elif len(text) > BESCHREIBUNG_MAX:
                maengel.append(f"{anzeige}: meta-description wird abgeschnitten ({len(text)} von max. {BESCHREIBUNG_MAX} Zeichen)")
            beschreibungen.setdefault(text, []).append(anzeige)

        if not OG_BILD_MUSTER.search(inhalt):
            maengel.append(f"{anzeige}: og:image fehlt (kein Vorschaubild beim Teilen)")
        # 404.html wird unter jeder beliebigen Adresse ausgeliefert - ein
        # canonical waere dort schlicht falsch.
        if os.path.basename(html) != "404.html" and not CANONICAL_MUSTER.search(inhalt):
            maengel.append(f"{anzeige}: canonical-Link fehlt")

    for text, seiten in beschreibungen.items():
        if len(seiten) > 1:
            maengel.append(f"gleiche meta-description auf: {', '.join(seiten)}")

    return maengel


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


def pruefe_externe_links(fortschritt=True):
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
            kaputt.append(f"{adresse}\n      {grund} - verlinkt auf {', '.join(sorted(adressen[adresse]))}")
    return kaputt


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
    kaputte_links = pruefe_externe_links(fortschritt=not still) if extern else []

    kritisch = bool(tote or schreibweise or veralteter_build)
    hinweise = bool(fehlende_pdfs or ohne_alt or doppelte_ids or meta_maengel
                    or drittanbieter or kaputte_links)

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

    _abschnitt(f"WARNUNG - {len(kaputte_links)} externe(r) Link(s) antworten nicht:",
               kaputte_links,
               "Menuepunkt 'Sponsoren-Seite pflegen' bzw. Link im HTML korrigieren")

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

    extern = False
    try:
        extern = h.frage_ja("\nAuch die Links ins Internet pruefen? "
                            "(dauert ein paar Sekunden) (j/n): ")
    except (h.Zurueck, EOFError):
        pass

    pruefe_alles(extern=extern)


if __name__ == "__main__":
    main()
