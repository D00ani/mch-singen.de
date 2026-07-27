# -*- coding: utf-8 -*-
"""
Haelt sitemap.xml aktuell: setzt je Seite das <lastmod>-Datum auf das
Aenderungsdatum der HTML-Datei, meldet neue Seiten, die noch fehlen, und
Eintraege, deren Datei es nicht mehr gibt.

Seiten mit <meta name="robots" content="noindex"> gehoeren nicht in die
Sitemap und werden gemeldet (z. B. die Live-Timing-Seite).

Ausfuehren: python tools/update_sitemap.py
Laeuft ausserdem automatisch beim Veroeffentlichen mit.
"""
import glob
import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
SITEMAP = os.path.join(ROOT, "sitemap.xml")
BASIS_URL = "https://mch-singen.de/"

URL_BLOCK = re.compile(r"<url>\s*<loc>(.*?)</loc>(.*?)</url>", re.DOTALL)
LASTMOD = re.compile(r"(<lastmod>)(.*?)(</lastmod>)", re.DOTALL)
NOINDEX = re.compile(r'<meta\s+name="robots"[^>]*content="[^"]*noindex', re.IGNORECASE)


def seiten_dateien():
    return sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                  glob.glob(os.path.join(ROOT, "pages", "*.html")))


def url_zu_datei(url):
    pfad = (url[len(BASIS_URL):] if url.startswith(BASIS_URL) else url).strip("/")
    if not pfad:
        pfad = "index.html"  # die Startseite wird ohne Dateinamen verlinkt
    return os.path.join(ROOT, pfad.replace("/", os.sep))


def ist_noindex(pfad):
    try:
        return bool(NOINDEX.search(open(pfad, encoding="utf-8").read()))
    except OSError:
        return False


def aenderungsdatum(pfad):
    """Datum der letzten inhaltlichen Aenderung. Bevorzugt aus der
    Git-Historie, weil das Dateidatum sich schon beim Kopieren oder Auschecken
    aendert und dann falsche Angaben in der Sitemap stehen wuerden."""
    try:
        ergebnis = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", pfad],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        gemeldet = ergebnis.stdout.strip()
        if ergebnis.returncode == 0 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", gemeldet):
            return gemeldet
    except (OSError, subprocess.SubprocessError):
        pass
    return date.fromtimestamp(os.path.getmtime(pfad)).isoformat()


def pruefe_und_aktualisiere(automatisch=False):
    """Gibt True zurueck, wenn die Sitemap geaendert wurde."""
    if not os.path.isfile(SITEMAP):
        print("sitemap.xml nicht gefunden.")
        return False

    inhalt = h.lies_datei(SITEMAP)
    eingetragen = {}
    aktualisierungen = []
    fehlende_dateien = []
    faelschlich_drin = []

    def ersetze(treffer):
        url, rest = treffer.group(1).strip(), treffer.group(2)
        datei = url_zu_datei(url)
        eingetragen[os.path.normpath(datei)] = url

        if not os.path.isfile(datei):
            fehlende_dateien.append(url)
            return treffer.group(0)
        if ist_noindex(datei):
            faelschlich_drin.append(url)

        neues_datum = aenderungsdatum(datei)
        block = treffer.group(0)
        vorhanden = LASTMOD.search(rest)
        if vorhanden and vorhanden.group(2).strip() != neues_datum:
            aktualisierungen.append(f"{url}: {vorhanden.group(2).strip()} -> {neues_datum}")
            block = LASTMOD.sub(lambda m: m.group(1) + neues_datum + m.group(3), block, count=1)
        return block

    neuer_inhalt = URL_BLOCK.sub(ersetze, inhalt)

    fehlende_seiten = []
    for datei in seiten_dateien():
        if os.path.normpath(datei) in eingetragen:
            continue
        if ist_noindex(datei) or os.path.basename(datei) == "404.html":
            continue
        fehlende_seiten.append(os.path.relpath(datei, ROOT).replace(os.sep, "/"))

    if aktualisierungen:
        print(f"\n{len(aktualisierungen)} Datum/Daten aktualisiert:")
        for eintrag in aktualisierungen[:10]:
            print(f"  {eintrag}")
        if len(aktualisierungen) > 10:
            print(f"  ... und {len(aktualisierungen) - 10} weitere")
    elif not automatisch:
        print("\nAlle Datumsangaben waren bereits aktuell.")

    if fehlende_seiten:
        print(f"\nHinweis - {len(fehlende_seiten)} Seite(n) fehlen in der Sitemap:")
        for eintrag in fehlende_seiten:
            print(f"  {eintrag}")
    if fehlende_dateien:
        print(f"\nWARNUNG - {len(fehlende_dateien)} Sitemap-Eintrag/-Eintraege ohne Datei:")
        for eintrag in fehlende_dateien:
            print(f"  {eintrag}")
    if faelschlich_drin:
        print(f"\nWARNUNG - {len(faelschlich_drin)} Seite(n) stehen in der Sitemap, sind aber auf 'noindex':")
        for eintrag in faelschlich_drin:
            print(f"  {eintrag}")

    if neuer_inhalt != inhalt:
        h.schreibe_datei(SITEMAP, neuer_inhalt)
        print(f"\nGespeichert: {os.path.relpath(SITEMAP, ROOT)}")
        return True
    return False


def main():
    print("=" * 60)
    print("  Sitemap aktualisieren")
    print("=" * 60)
    pruefe_und_aktualisiere()


if __name__ == "__main__":
    main()
