# -*- coding: utf-8 -*-
"""
Zentrales Werkzeug fuer die Pflege der MCH-Singen-Webseite - eine
Anlaufstelle fuer Termine, Statistiken, News, Archiv, Bilder und das
technische Update.

Beim Beenden wird die Seite geprueft und alles Geaenderte automatisch
veroeffentlicht.

Ausfuehren: python tools/website_pflege.py
(oder per Doppelklick auf website-pflege.bat eine Ebene ueber mch-arbeit/)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archiv_pflege
import bilder_pflege
import jaehrliches_update
import news_pflege
import pflege_hilfen as h
import pruefe_seite
import saisonwechsel
import sponsoren_pflege
import statistiken_pflege
import termine_verwalten
import trainingstermine_import
import update_sitemap

MENUEPUNKTE = [
    ("Renntermine (Kart/Trial) verwalten", termine_verwalten.main),
    ("Trainingstermine importieren (Excel-Export)", trainingstermine_import.main),
    ("Statistiken-Seite pflegen (Platzierungen, Vereinsmeister, Rekorde, Zahlen)", statistiken_pflege.main),
    ("News-Karten auf 'Aktuelles' pflegen", news_pflege.main),
    ("Jahresarchiv pflegen", archiv_pflege.main),
    ("Sponsoren pflegen", sponsoren_pflege.main),
    ("Bilder aufnehmen (WebP + HTML-Block)", bilder_pflege.main),
    ("Webseite pruefen (tote Links, Schreibweise, Build)", pruefe_seite.main),
    ("Saisonwechsel-Assistent (fuehrt durch den Jahreswechsel)", saisonwechsel.main),
    ("Technisches Update (Statistik/Bilder/Copyright/Build + Push)", jaehrliches_update.main),
    ("Letzte Aenderung rueckgaengig machen", h.rueckgaengig),
]


def veroeffentlichen():
    """Prueft die Seite und veroeffentlicht dann alles Geaenderte."""
    if not jaehrliches_update.hat_aenderungen():
        return

    print("\n" + "=" * 60)
    print("  Vor dem Veroeffentlichen: Seite pruefen")
    print("=" * 60)
    update_sitemap.pruefe_und_aktualisiere(automatisch=True)
    sauber = pruefe_seite.pruefe_alles(still=True)

    if not sauber:
        print("\nEs wurden Probleme gefunden (siehe oben).")
        if not h.frage_ja("Trotzdem veroeffentlichen? (j/n): "):
            print("\nNicht veroeffentlicht. Die Aenderungen liegen weiterhin im")
            print("Arbeitsordner und gehen nicht verloren.")
            return

    print("\n" + "=" * 60)
    print("  Diese Aenderungen werden veroeffentlicht:")
    print("=" * 60)
    subprocess.run(["git", "status", "--short"], cwd=h.ROOT)
    jaehrliches_update.commit_merge_push("Webseiten-Pflege: Aenderungen aktualisiert")


def main():
    print("=" * 60)
    print("  MCH Singen - Webseiten-Pflege")
    print("=" * 60)

    print("\nTipp: Mit 'x' kommst du an jeder Stelle einen Schritt zurueck.")

    while True:
        aktion = _hauptmenue()
        if aktion is None:
            break
        h.fuehre_aus(aktion)

    h.fuehre_aus(veroeffentlichen)
    print("\nBis zum naechsten Mal!")


def _hauptmenue():
    print("\nWas moechtest du tun?")
    for i, (beschriftung, _) in enumerate(MENUEPUNKTE, start=1):
        print(f"  {i:2}) {beschriftung}")
    print("   0) Beenden")

    gueltig = {str(i) for i in range(1, len(MENUEPUNKTE) + 1)} | {"0"}
    try:
        wahl = h.frage("\nAuswahl: ", lambda a: None if a in gueltig else "Ungueltige Auswahl.")
    except h.Zurueck:
        return None  # 'x' im Hauptmenue = beenden
    return None if wahl == "0" else MENUEPUNKTE[int(wahl) - 1][1]


if __name__ == "__main__":
    main()
