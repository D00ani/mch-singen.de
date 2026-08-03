# -*- coding: utf-8 -*-
"""
Raeumt media/ auf: findet Dateien, die von keiner Seite mehr verlinkt sind,
Dateien die unnoetig gross sind und Bilder ohne WebP-Fassung.

Jede Datei, die geloescht wird, landet vorher in .pflege-sicherungen - der
Menuepunkt "Letzte Aenderung rueckgaengig machen" holt sie zurueck.

Ausfuehren: python tools/medien_aufraeumen.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
MEDIA_DIR = os.path.join(ROOT, "media")

# Dateitypen, in denen ein Verweis auf eine Mediendatei stehen kann
TEXT_ENDUNGEN = (".html", ".css", ".js", ".txt", ".json", ".xml", ".py", ".md")

# Ordner, die beim Suchen nach Verweisen nichts beitragen
IGNORIERTE_ORDNER = {".git", ".pflege-sicherungen", "__pycache__", "node_modules", "media"}

BILD_ENDUNGEN = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
VIDEO_ENDUNGEN = (".mp4", ".webm", ".mov", ".m4v")

# Ab hier lohnt sich ein Blick (in KB)
GRENZE_BILD_KB = 300
GRENZE_PDF_KB = 2048
GRENZE_VIDEO_KB = 5120


# ------------------------------------------------------------------
# Einsammeln
# ------------------------------------------------------------------

def medien_dateien():
    treffer = []
    for verzeichnis, _, dateien in os.walk(MEDIA_DIR):
        for name in dateien:
            treffer.append(os.path.join(verzeichnis, name))
    return sorted(treffer)


def text_inhalte():
    """Liest alles ein, worin ein Verweis stehen koennte - getrennt nach
    "die Webseite selbst" und "die Werkzeuge unter tools/". Eine Datei, die
    nur noch im Werkzeug steht, ist auf der Seite naemlich nicht mehr zu
    sehen, gehoert aber trotzdem nicht ungefragt geloescht."""
    seite, werkzeuge = [], []
    for verzeichnis, unterordner, dateien in os.walk(ROOT):
        unterordner[:] = [u for u in unterordner if u not in IGNORIERTE_ORDNER]
        ist_werkzeug = os.path.basename(verzeichnis) == "tools"
        for name in dateien:
            if not name.lower().endswith(TEXT_ENDUNGEN):
                continue
            try:
                inhalt = h.lies_datei(os.path.join(verzeichnis, name))
            except (OSError, UnicodeDecodeError):
                continue
            (werkzeuge if ist_werkzeug else seite).append(inhalt)
    return "\n".join(seite), "\n".join(werkzeuge)


def finde_verwaiste(dateien, seiten_text, werkzeug_text):
    """Teilt die Dateien in "nirgends mehr erwaehnt" und "nur noch im
    Werkzeug erwaehnt" auf.

    Gesucht wird bewusst nur nach dem Dateinamen (nicht dem ganzen Pfad):
    lieber eine verwaiste Datei uebersehen, als eine noch benutzte zum
    Loeschen vorschlagen.
    """
    verwaist, nur_werkzeug = [], []
    for pfad in dateien:
        name = os.path.basename(pfad)
        if name in seiten_text:
            continue
        (nur_werkzeug if name in werkzeug_text else verwaist).append(pfad)
    return verwaist, nur_werkzeug


def finde_zu_grosse(dateien):
    treffer = []
    for pfad in dateien:
        kb = os.path.getsize(pfad) // 1024
        endung = os.path.splitext(pfad)[1].lower()
        if endung in VIDEO_ENDUNGEN:
            grenze, art = GRENZE_VIDEO_KB, "Video"
        elif endung == ".pdf":
            grenze, art = GRENZE_PDF_KB, "PDF"
        elif endung in BILD_ENDUNGEN:
            grenze, art = GRENZE_BILD_KB, "Bild"
        else:
            continue
        if kb > grenze:
            treffer.append((pfad, kb, art))
    return sorted(treffer, key=lambda e: -e[1])


def finde_ohne_webp(dateien):
    """JPG/PNG ohne WebP-Gegenstueck - das kostet Ladezeit bei jedem Besuch."""
    namen_je_ordner = {}
    for pfad in dateien:
        namen_je_ordner.setdefault(os.path.dirname(pfad), set()).add(os.path.basename(pfad))

    treffer = []
    for pfad in dateien:
        if not pfad.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        ordner = os.path.dirname(pfad)
        stamm = os.path.splitext(os.path.basename(pfad))[0]
        nachbarn = namen_je_ordner[ordner]
        hat_webp = (stamm + ".webp") in nachbarn or any(
            n.startswith(stamm + "-") and n.endswith(".webp") for n in nachbarn)
        if not hat_webp:
            treffer.append(pfad)
    return treffer


# ------------------------------------------------------------------
# Anzeigen
# ------------------------------------------------------------------

def kurz(pfad):
    return os.path.relpath(pfad, ROOT).replace(os.sep, "/")


def zeige_bericht(verwaist, nur_werkzeug, zu_gross, ohne_webp):
    gesamt_kb = sum(os.path.getsize(p) for p in verwaist) // 1024

    print("\n" + "=" * 60)
    print("  Medien-Bericht")
    print("=" * 60)

    if verwaist:
        print(f"\nVon keiner Seite verlinkt ({len(verwaist)} Datei(en), {gesamt_kb} KB):")
        for pfad in verwaist:
            print(f"  {kurz(pfad)}  ({os.path.getsize(pfad) // 1024} KB)")
    else:
        print("\nKeine verwaisten Dateien - jede Datei unter media/ wird verwendet.")

    if nur_werkzeug:
        print(f"\nNicht mehr auf der Seite, aber noch im Werkzeug eingetragen "
              f"({len(nur_werkzeug)} Datei(en)):")
        for pfad in nur_werkzeug:
            print(f"  {kurz(pfad)}  ({os.path.getsize(pfad) // 1024} KB)")
        print("  -> steht noch in tools/optimize_images.py o.ae.; erst dort austragen,")
        print("     dann taucht die Datei beim naechsten Lauf oben zum Loeschen auf")

    if zu_gross:
        print(f"\nUnnoetig gross ({len(zu_gross)} Datei(en)):")
        for pfad, kb, art in zu_gross:
            print(f"  {kurz(pfad)}  ({kb} KB, {art})")

    if ohne_webp:
        print(f"\nOhne WebP-Fassung ({len(ohne_webp)} Bild(er)):")
        for pfad in ohne_webp:
            print(f"  {kurz(pfad)}")
        print("  -> Menuepunkt 'Bilder aufnehmen' erzeugt die WebP-Fassung")


def zeige_video_tipps(zu_gross):
    videos = [(p, kb) for p, kb, art in zu_gross if art == "Video"]
    if not videos:
        return

    print("\n" + "=" * 60)
    print("  Videos kleiner bekommen")
    print("=" * 60)
    print("\nEin Video, das per autoplay laeuft, laedt JEDER Besucher komplett -")
    print("auch am Handy im Mobilfunknetz. Drei Stellschrauben, in dieser Reihenfolge:")
    print("\n  1. Tonspur raus, wenn das Video ohnehin stumm eingebunden ist ('muted')")
    print("  2. Neu kodieren - Vereinsvideos sind meist mit viel zu hoher Datenrate exportiert")
    print("  3. Modernes Format zusaetzlich anbieten (AV1 spart ca. die Haelfte)")
    print("\nDazu wird ffmpeg gebraucht (kostenlos, https://ffmpeg.org/download.html).")

    for pfad, kb in videos:
        stamm = os.path.splitext(kurz(pfad))[0]
        print(f"\n{kurz(pfad)} ({kb} KB):")
        print(f"  ffmpeg -i {kurz(pfad)} -c:v libsvtav1 -crf 34 -preset 6 -an {stamm}.av1.mp4")
        print(f"  ffmpeg -i {kurz(pfad)} -c:v libvpx-vp9 -crf 34 -b:v 0 -an {stamm}.webm")
        print(f"  ffmpeg -i {kurz(pfad)} -c:v libx264 -crf 24 -preset slow -an "
              f"-movflags +faststart {stamm}.klein.mp4")
        print("\n  Danach im HTML alle drei anbieten (der Browser nimmt das erste, das er kann):")
        print(f'    <source src="{stamm}.av1.mp4" type="video/mp4; codecs=av01.0.05M.08">')
        print(f'    <source src="{stamm}.webm" type="video/webm">')
        print(f'    <source src="{stamm}.klein.mp4" type="video/mp4">')


# ------------------------------------------------------------------
# Loeschen
# ------------------------------------------------------------------

def loesche_verwaiste(verwaist):
    if not verwaist:
        return

    print("\n" + "-" * 60)
    print("Verwaiste Dateien loeschen? Jede Datei wird vorher gesichert und")
    print("laesst sich ueber 'Letzte Aenderung rueckgaengig machen' zurueckholen.")

    wahl = h.waehle_option("Was moechtest du tun?", [
        "Nichts loeschen",
        "Einzeln entscheiden",
        f"Alle {len(verwaist)} verwaisten Dateien loeschen",
    ])

    if wahl == 0:
        print("\nNichts geloescht.")
        return

    zu_loeschen = verwaist
    if wahl == 1:
        zu_loeschen = []
        for pfad in verwaist:
            if h.frage_ja(f"  {kurz(pfad)} loeschen? (j/n): "):
                zu_loeschen.append(pfad)
    elif not h.frage_ja(f"\nWirklich alle {len(verwaist)} Dateien loeschen? (j/n): "):
        print("\nNichts geloescht.")
        return

    for pfad in zu_loeschen:
        h.sicherung_anlegen(pfad)
        os.remove(pfad)
        print(f"  Geloescht: {kurz(pfad)}")

    if zu_loeschen:
        print(f"\n{len(zu_loeschen)} Datei(en) geloescht (gesichert).")
    else:
        print("\nNichts geloescht.")


def main():
    print("=" * 60)
    print("  Medien aufraeumen")
    print("=" * 60)
    print("\nSuche Verweise in HTML, CSS, JS und den Daten-Dateien ...")

    dateien = medien_dateien()
    if not dateien:
        print("\nKeine Dateien unter media/ gefunden.")
        return

    seiten_text, werkzeug_text = text_inhalte()
    verwaist, nur_werkzeug = finde_verwaiste(dateien, seiten_text, werkzeug_text)
    zu_gross = finde_zu_grosse(dateien)
    ohne_webp = finde_ohne_webp(dateien)

    gesamt_mb = sum(os.path.getsize(p) for p in dateien) / 1024 / 1024
    print(f"{len(dateien)} Dateien unter media/, zusammen {gesamt_mb:.1f} MB.")

    zeige_bericht(verwaist, nur_werkzeug, zu_gross, ohne_webp)
    zeige_video_tipps(zu_gross)
    h.fuehre_aus(loesche_verwaiste, verwaist)

    print("\nFertig.")


if __name__ == "__main__":
    main()
