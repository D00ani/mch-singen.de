# -*- coding: utf-8 -*-
"""
Zentrales Werkzeug fuer die Pflege der MCH-Singen-Webseite - eine
Anlaufstelle fuer Termine, Statistiken, News, Archiv, Bilder und das
technische Update.

Beim Start steht, was gerade ansteht. Beim Beenden wird die Seite geprueft
und alles Geaenderte automatisch veroeffentlicht.

Ausfuehren: python tools/website_pflege.py
(oder per Doppelklick auf website-pflege.bat eine Ebene ueber mch-arbeit/)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aenderungsprotokoll
import archiv_pflege
import ausschreibung_pdf
import bilder_pflege
import faq_pflege
import jaehrliches_update
import livetiming_sync
import medien_aufraeumen
import news_pflege
import pflege_hilfen as h
import pruefe_seite
import rennwochenende
import saisonwechsel
import sponsoren_pflege
import statistiken_pflege
import team_pflege
import termine_verwalten
import trainingstermine_import
import uebersicht
import update_sitemap
import vorschau

# Reine Zeichenketten sind Zwischenueberschriften, Paare sind Menuepunkte.
MENUE = [
    "Inhalte pflegen",
    ("Live-Timing: Zeiten der Zeitmessung auf die Seite bringen", livetiming_sync.main),
    ("Nach dem Rennen: Ergebnisse, News, Bilder, Archiv am Stueck", rennwochenende.main),
    ("Renntermine (Kart/Trial) verwalten", termine_verwalten.main),
    ("Ausschreibungs-PDF einpflegen", ausschreibung_pdf.main),
    ("Trainingstermine importieren (Excel-Export)", trainingstermine_import.main),
    ("Statistiken-Seite pflegen (Platzierungen, Vereinsmeister, Rekorde, Zahlen)", statistiken_pflege.main),
    ("News-Karten auf 'Aktuelles' pflegen", news_pflege.main),
    ("Jahresarchiv pflegen", archiv_pflege.main),
    ("Sponsoren-Seite pflegen (Logos, Vereine, Links, Aufruf)", sponsoren_pflege.main),
    ("Vorstand & Trainer pflegen", team_pflege.main),
    ("Fragen & Antworten (FAQ) pflegen", faq_pflege.main),
    ("Bilder aufnehmen (WebP + HTML-Block)", bilder_pflege.main),

    "Nachsehen und pruefen",
    ("Vorschau im Browser (nur auf diesem Rechner)", vorschau.main),
    ("Webseite pruefen (tote Links, Schreibweise, Build)", pruefe_seite.main),
    ("Was steht an? (Uebersicht wie beim Start)", uebersicht.main),
    ("Medien aufraeumen (verwaiste und zu grosse Dateien)", medien_aufraeumen.main),

    "Technik",
    ("Saisonwechsel-Assistent (fuehrt durch den Jahreswechsel)", saisonwechsel.main),
    ("Technisches Update (Statistik/Bilder/Copyright/Build + Push)", jaehrliches_update.main),
    ("Letzte Aenderung rueckgaengig machen", h.rueckgaengig),
]

MENUEPUNKTE = [eintrag for eintrag in MENUE if isinstance(eintrag, tuple)]


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
    print("  Das wird veroeffentlicht:")
    print("=" * 60)
    aenderungsprotokoll.zeige()

    if not h.frage_ja("\nJetzt veroeffentlichen? (j/n): "):
        print("\nNicht veroeffentlicht. Die Aenderungen liegen weiterhin im")
        print("Arbeitsordner und gehen nicht verloren.")
        return

    jaehrliches_update.commit_merge_push("Webseiten-Pflege: Aenderungen aktualisiert")


def main():
    print("=" * 60)
    print("  MCH Singen - Webseiten-Pflege")
    print("=" * 60)

    h.fuehre_aus(uebersicht.zeige)

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
    nummer = 0
    for eintrag in MENUE:
        if isinstance(eintrag, str):
            print(f"\n  {eintrag}")
            continue
        nummer += 1
        print(f"  {nummer:2}) {eintrag[0]}")
    print("\n   0) Beenden")

    gueltig = {str(i) for i in range(1, len(MENUEPUNKTE) + 1)} | {"0"}
    try:
        wahl = h.frage("\nAuswahl: ", lambda a: None if a in gueltig else "Ungueltige Auswahl.")
    except h.Zurueck:
        return None  # 'x' im Hauptmenue = beenden
    return None if wahl == "0" else MENUEPUNKTE[int(wahl) - 1][1]


if __name__ == "__main__":
    main()
