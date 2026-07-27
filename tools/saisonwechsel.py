# -*- coding: utf-8 -*-
"""
Fuehrt Schritt fuer Schritt durch den Jahreswechsel - dieselbe Reihenfolge
wie die Checkliste, aber jeder Punkt laesst sich direkt erledigen statt nur
abgehakt zu werden.

Ausfuehren: python tools/saisonwechsel.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archiv_pflege
import jaehrliches_update
import pflege_hilfen as h
import statistiken_pflege
import termine_verwalten
import trainingstermine_import

SCHRITTE = [
    (
        "Abgeschlossene Saison ins Archiv aufnehmen",
        "Legt den Ordner an, uebernimmt die Wertungs-PDF und traegt sie in archiv.html ein.",
        archiv_pflege.jahr_hinzufuegen,
    ),
    (
        "Diagramm der abgeschlossenen Saison einfrieren",
        "Endwerte eintragen und die Ueberschrift auf die abgelaufene Saison setzen.",
        statistiken_pflege.diagramme_bearbeiten,
    ),
    (
        "Vereinsmeister / Wanderpokal-Sieger des Jahres eintragen",
        "Neue Zeile in der Jugend- bzw. Erwachsenen-Tabelle.",
        statistiken_pflege.tabelle_hinzufuegen,
    ),
    (
        "Trainingstermine der neuen Saison importieren",
        "Excel-Export umwandeln und den Verweis in js/aktuelles.js anpassen.",
        trainingstermine_import.main,
    ),
    (
        "Renntermine der neuen Saison eintragen",
        "Kart- und Trial-Termine fuer Countdown und Kalender-Download.",
        termine_verwalten.main,
    ),
    (
        "Technisches Update und Veroeffentlichen",
        "Statistik-Chart, Bilder, Copyright-Jahr, Build - danach Push.",
        jaehrliches_update.main,
    ),
]


def main():
    print("=" * 60)
    print("  Saisonwechsel")
    print("=" * 60)
    print("\nWir gehen die Punkte der Reihe nach durch. Jeden Punkt kannst du")
    print("erledigen, ueberspringen (falls schon passiert oder nicht noetig)")
    print("oder den Assistenten hier beenden.")

    for nummer, (titel, erklaerung, funktion) in enumerate(SCHRITTE, start=1):
        print("\n" + "-" * 60)
        print(f"Schritt {nummer} von {len(SCHRITTE)}: {titel}")
        print(f"  {erklaerung}")
        print("-" * 60)

        antwort = h.frage(
            "  [j] jetzt erledigen  [u] ueberspringen  [b] beenden: ",
            lambda a: None if a.lower() in ("j", "u", "b") else "Bitte j, u oder b."
        ).lower()

        if antwort == "b":
            print("\nAssistent beendet. Die uebrigen Schritte kannst du spaeter")
            print("einzeln ueber das Hauptmenue erledigen.")
            return
        if antwort == "u":
            print("  Uebersprungen.")
            continue

        try:
            funktion()
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")
        except KeyboardInterrupt:
            print("\nSchritt abgebrochen.")

        if nummer < len(SCHRITTE) and not h.frage_ja("\nWeiter zum naechsten Schritt? (j/n): "):
            print("\nAssistent beendet.")
            return

    print("\n" + "=" * 60)
    print("  Saisonwechsel abgeschlossen.")
    print("=" * 60)


if __name__ == "__main__":
    main()
