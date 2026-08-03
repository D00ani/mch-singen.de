# -*- coding: utf-8 -*-
"""
Uebersetzt die noch nicht veroeffentlichten Aenderungen in Klartext.

Statt
    M  pages/aktuelles.html
    M  data/timer.txt
steht da
    Aktuelles: 2 News-Karten neu (jetzt 7)
    Renntermine Kart: 1 Termin neu (05.October.2026 09:00 - MCH Singen)

damit vor dem Veroeffentlichen erkennbar ist, was tatsaechlich rausgeht.

Ausfuehren: python tools/aenderungsprotokoll.py
Wird ausserdem beim Veroeffentlichen angezeigt.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import termine_verwalten as tv

ROOT = h.ROOT

# Seite -> Name, den auch jemand versteht, der kein HTML kann
SEITEN_NAMEN = {
    "index.html": "Startseite",
    "404.html": "Fehlerseite (404)",
    "pages/aktuelles.html": "Aktuelles",
    "pages/archiv.html": "Jahresarchiv",
    "pages/statistiken.html": "Statistiken",
    "pages/sponsoren-links.html": "Sponsoren & Links",
    "pages/ueber-uns.html": "Über uns",
    "pages/faq.html": "Fragen & Antworten",
    "pages/kartsport.html": "Kartsport",
    "pages/trialsport.html": "Trialsport",
    "pages/geschichte.html": "Geschichte",
    "pages/kontakt.html": "Kontakt",
    "pages/live.html": "Live-Timing",
    "pages/mitglied-werden.html": "Mitglied werden",
    "pages/impressum-datenschutz.html": "Impressum & Datenschutz",
    "pages/sommerferienprogramm.html": "Sommerferienprogramm",
    "pages/suche.html": "Suche",
}

# Seite -> (Suchmuster, Einzahl, Mehrzahl): was auf der Seite gezaehlt wird
ZAEHLBAR = {
    "pages/aktuelles.html": (r'class="news-card', "News-Karte", "News-Karten"),
    "pages/archiv.html": (r"<summary>Saison \d{4}</summary>", "Saison", "Saisons"),
    "pages/faq.html": (r"<details", "Frage", "Fragen"),
    "pages/sponsoren-links.html": (r'src="\.\./media/sponsoren/', "Logo", "Logos"),
    "pages/statistiken.html": (r"<tr>", "Tabellenzeile", "Tabellenzeilen"),
}

TERMIN_DATEIEN = {
    "data/timer.txt": "Renntermine Kart",
    "data/timer_trial.txt": "Renntermine Trial",
}

TECHNISCH = (".min.css", ".min.js")


def git(*args):
    try:
        ergebnis = subprocess.run(["git"] + list(args), cwd=ROOT,
                                  capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return ergebnis.stdout if ergebnis.returncode == 0 else None


def alter_stand(pfad):
    """Inhalt der Datei beim letzten Veroeffentlichen ('' = neue Datei)."""
    inhalt = git("show", f"HEAD:{pfad}")
    return inhalt if inhalt is not None else ""


def neuer_stand(pfad):
    voll = os.path.join(ROOT, pfad.replace("/", os.sep))
    if not os.path.isfile(voll):
        return ""
    try:
        return h.lies_datei(voll)
    except (OSError, UnicodeDecodeError):
        return ""


def geaenderte_dateien():
    """(status, pfad) fuer alles, was noch nicht veroeffentlicht ist."""
    ausgabe = git("status", "--porcelain")
    if not ausgabe:
        return []

    dateien = []
    for zeile in ausgabe.splitlines():
        if len(zeile) < 4:
            continue
        status, pfad = zeile[:2], zeile[3:].strip().strip('"')
        if " -> " in pfad:                       # umbenannt
            pfad = pfad.split(" -> ")[-1]
        dateien.append((status, pfad))
    return dateien


# ------------------------------------------------------------------
# Einzelne Dateiarten beschreiben
# ------------------------------------------------------------------

def beschreibe_termine(pfad, name):
    alt = {z.strip() for z in alter_stand(pfad).splitlines() if z.strip()}
    neu = {z.strip() for z in neuer_stand(pfad).splitlines() if z.strip()}

    dazu = sorted(neu - alt, key=tv.termin_schluessel)
    weg = sorted(alt - neu, key=tv.termin_schluessel)
    if not dazu and not weg:
        return f"{name}: geändert"

    teile = []
    for zeilen, wort in ((dazu, "neu"), (weg, "gelöscht")):
        if not zeilen:
            continue
        beschreibungen = [tv.beschreibe_termin(z) for z in zeilen[:3]]
        rest = f" und {len(zeilen) - 3} weitere" if len(zeilen) > 3 else ""
        teile.append(f"{len(zeilen)} Termin(e) {wort} ({'; '.join(beschreibungen)}{rest})")
    return f"{name}: " + ", ".join(teile)


def beschreibe_gezaehlt(pfad, name):
    muster, einzahl, mehrzahl = ZAEHLBAR[pfad]
    vorher = len(re.findall(muster, alter_stand(pfad)))
    nachher = len(re.findall(muster, neuer_stand(pfad)))

    if nachher > vorher:
        anzahl = nachher - vorher
        wort = einzahl if anzahl == 1 else mehrzahl
        return f"{name}: {anzahl} {wort} neu (jetzt {nachher})"
    if nachher < vorher:
        anzahl = vorher - nachher
        wort = einzahl if anzahl == 1 else mehrzahl
        return f"{name}: {anzahl} {wort} entfernt (jetzt {nachher})"
    return f"{name}: Texte oder Angaben geändert"


def beschreibe_medien(status, pfad):
    art = "PDF" if pfad.lower().endswith(".pdf") else (
        "Video" if pfad.lower().endswith((".mp4", ".webm")) else "Bild")
    name = pfad.split("/")[-1]
    if status.strip() == "D":
        return f"{art} gelöscht: {name}"
    if status.strip() in ("??", "A"):
        return f"{art} neu: {name}"
    return f"{art} ersetzt: {name}"


def beschreibe_seite(pfad, name):
    alt, neu = alter_stand(pfad), neuer_stand(pfad)
    if not alt:
        return f"{name}: Seite neu angelegt"
    if not neu:
        return f"{name}: Seite gelöscht"

    dazu = len(neu.splitlines()) - len(alt.splitlines())
    if dazu > 0:
        return f"{name}: erweitert ({dazu} Zeile(n) mehr)"
    if dazu < 0:
        return f"{name}: gekürzt ({-dazu} Zeile(n) weniger)"
    return f"{name}: Text geändert"


def beschreibe(status, pfad):
    if pfad in TERMIN_DATEIEN:
        return beschreibe_termine(pfad, TERMIN_DATEIEN[pfad])
    if pfad in ZAEHLBAR and status.strip() not in ("??", "A", "D"):
        return beschreibe_gezaehlt(pfad, SEITEN_NAMEN.get(pfad, pfad))
    if pfad in SEITEN_NAMEN:
        return beschreibe_seite(pfad, SEITEN_NAMEN[pfad])
    if pfad.startswith("media/"):
        return beschreibe_medien(status, pfad)
    if pfad.endswith(TECHNISCH):
        return f"Technisch: {pfad} neu gebaut"
    if pfad.startswith("tools/"):
        return f"Werkzeug: {pfad}"
    if pfad.startswith(("css/", "js/")):
        return f"Technisch: {pfad} geändert"
    if pfad.startswith("data/"):
        return f"Daten: {pfad} geändert"
    if pfad == "sitemap.xml":
        return "Sitemap: Datumsangaben aktualisiert (passiert automatisch)"
    if pfad == "README.txt":
        return "Anleitung (README) ergänzt"
    if pfad in ("robots.txt", "CNAME", ".htaccess"):
        return f"Server-Einstellung: {pfad}"
    return f"Sonstiges: {pfad}"


# ------------------------------------------------------------------
# Ausgabe
# ------------------------------------------------------------------

def sammle():
    """Klartext-Zeilen fuer alles, was noch nicht veroeffentlicht ist."""
    zeilen = []
    for status, pfad in geaenderte_dateien_sicher():
        try:
            zeilen.append(beschreibe(status, pfad))
        except Exception:
            zeilen.append(f"Sonstiges: {pfad}")

    # Doppelte zusammenfassen (z. B. mehrere .min-Dateien)
    einmalig = []
    for zeile in zeilen:
        if zeile not in einmalig:
            einmalig.append(zeile)
    return einmalig


def geaenderte_dateien_sicher():
    try:
        return geaenderte_dateien()
    except Exception:
        return []


def zeige(zeilen=None):
    zeilen = sammle() if zeilen is None else zeilen
    if not zeilen:
        print("\nNichts geändert — es gibt nichts zu veröffentlichen.")
        return

    print(f"\nDiese {len(zeilen)} Änderung(en) gehen raus:")
    for zeile in zeilen:
        print(f"  - {zeile}")


def main():
    print("=" * 60)
    print("  Was ist seit dem letzten Veröffentlichen passiert?")
    print("=" * 60)
    zeige()


if __name__ == "__main__":
    main()
