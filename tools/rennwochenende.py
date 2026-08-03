# -*- coding: utf-8 -*-
"""
Fuehrt durch alles, was nach einem Rennen ansteht.

Ohne diesen Assistenten sind es vier getrennte Menuepunkte, die man in der
richtigen Reihenfolge und vollstaendig abarbeiten muss - hier kommen sie
nacheinander, jeder einzeln ueberspringbar, mit dem gewaehlten Rennen als
Merkhilfe im Kopf des Fensters.

Es werden dieselben Werkzeuge aufgerufen wie ueber das Hauptmenue; dieser
Assistent haelt sie nur zusammen.

Ausfuehren: python tools/rennwochenende.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archiv_pflege
import news_pflege
import pflege_hilfen as h
import statistiken_pflege
import termine_verwalten as tv
import uebersicht

ROOT = h.ROOT
RUECKBLICK_TAGE = 35
MAX_VORSCHLAEGE = 8


def letzte_rennen(heute=None):
    """Die juengsten bereits gefahrenen Termine - eines davon ist gemeint."""
    heute = heute or date.today()
    frueheste = heute - timedelta(days=RUECKBLICK_TAGE)

    gefunden = []
    for name, sportart in (("timer.txt", "Kart"), ("timer_trial.txt", "Trial")):
        for zeile in h.lies_zeilen(os.path.join(ROOT, "data", name)):
            wann = uebersicht.termin_datum(zeile)
            if wann and frueheste <= wann <= heute:
                gefunden.append((wann, sportart, zeile))
    return sorted(gefunden, reverse=True)[:MAX_VORSCHLAEGE]


def waehle_rennen():
    rennen = letzte_rennen()
    if not rennen:
        print(f"\nIn den letzten {RUECKBLICK_TAGE} Tagen ist laut Terminliste kein")
        print("Rennen gewesen. Der Assistent laeuft trotzdem.")
        return None

    optionen = [f"{s}: {tv.beschreibe_termin(z)}" for _, s, z in rennen]
    optionen.append("Anderes / kein bestimmtes Rennen")
    try:
        wahl = h.waehle_option("Um welches Rennen geht es?", optionen)
    except h.Zurueck:
        return None
    if wahl >= len(rennen):
        return None
    wann, sportart, zeile = rennen[wahl]
    return f"{sportart}: {tv.beschreibe_termin(zeile)}"


def bilder_schritt():
    """Erst hier importieren - bilder_pflege beendet sich beim Start, wenn
    Pillow fehlt, und das soll nicht den ganzen Assistenten mitreissen."""
    try:
        import bilder_pflege
    except SystemExit:
        print("\nDas Bilder-Werkzeug braucht Pillow (pip install Pillow).")
        print("Schritt wird uebersprungen.")
        return
    bilder_pflege.main()


SCHRITTE = [
    ("Ergebnisse in die Statistik",
     "Top-Platzierungen der Fahrerinnen und Fahrer eintragen.",
     statistiken_pflege.tabelle_hinzufuegen),
    ("News-Karte auf 'Aktuelles'",
     "Kurzer Bericht, den Besucher auf der Aktuelles-Seite sehen.",
     news_pflege.karte_hinzufuegen),
    ("Bilder vom Rennen",
     "Fotos als WebP aufnehmen und den fertigen HTML-Block bekommen.\n"
     "     (Die Bilddateien vorher in media/bilder/ ablegen.)",
     bilder_schritt),
    ("Ergebnisliste ins Jahresarchiv",
     "Nur noetig, wenn es eine PDF zum Rennen oder zur Gesamtwertung gibt.",
     archiv_pflege.eintrag_verwalten),
]


def main():
    print("=" * 60)
    print("  Nach dem Rennen")
    print("=" * 60)
    print("\nDer Assistent geht die vier ueblichen Schritte der Reihe nach durch.")
    print("Jeder Schritt ist einzeln ueberspringbar - mit 'n' geht es weiter,")
    print("nichts wird uebergangen oder vergessen.")

    try:
        rennen = waehle_rennen()
    except h.Zurueck:
        return

    erledigt, uebersprungen = [], []

    for nummer, (titel, erklaerung, funktion) in enumerate(SCHRITTE, start=1):
        print("\n" + "=" * 60)
        if rennen:
            print(f"  {rennen}")
        print(f"  Schritt {nummer} von {len(SCHRITTE)}: {titel}")
        print("=" * 60)
        print(f"\n  {erklaerung}")

        try:
            machen = h.frage_ja("\nDiesen Schritt jetzt erledigen? (j/n): ")
        except h.Zurueck:
            print("\nAssistent abgebrochen. Erledigte Schritte bleiben erhalten.")
            break

        if not machen:
            uebersprungen.append(titel)
            continue

        h.fuehre_aus(funktion)
        erledigt.append(titel)

    print("\n" + "=" * 60)
    print("  Zusammenfassung")
    print("=" * 60)
    for titel in erledigt:
        print(f"  erledigt:      {titel}")
    for titel in uebersprungen:
        print(f"  uebersprungen: {titel}")
    if not erledigt:
        print("  Nichts geaendert.")
    else:
        print("\nVeroeffentlicht wird alles zusammen beim Beenden des Hauptmenues.")


if __name__ == "__main__":
    main()
