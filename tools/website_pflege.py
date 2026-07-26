# -*- coding: utf-8 -*-
"""
Zentrales Werkzeug fuer die Pflege der MCH-Singen-Webseite - eine
Anlaufstelle fuer Renntermine, Statistiken-Seite, Jahresarchiv und das
jaehrliche technische Update, statt mehrerer einzelner Skripte/bat-Dateien.

Ausfuehren: python tools/website_pflege.py
(oder per Doppelklick auf website-pflege.bat eine Ebene ueber mch-arbeit/)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archiv_pflege
import jaehrliches_update
import statistiken_pflege
import termine_verwalten


def frage(text, validierer=None):
    while True:
        antwort = input(text).strip()
        if validierer:
            fehler = validierer(antwort)
            if fehler:
                print(f"  -> {fehler}")
                continue
        return antwort


def main():
    print("=" * 60)
    print("  MCH Singen - Webseiten-Pflege")
    print("=" * 60)

    module = {
        "1": ("Renntermine (Kart/Trial) verwalten", termine_verwalten.main),
        "2": ("Statistiken-Seite pflegen (Vereinsmeister, Rekorde)", statistiken_pflege.main),
        "3": ("Jahresarchiv pflegen", archiv_pflege.main),
        "4": ("Jaehrliches technisches Update (Statistik/Bilder/Copyright/Build + Push)", jaehrliches_update.main),
    }

    while True:
        print("\nWas moechtest du tun?")
        for key, (beschreibung, _) in module.items():
            print(f"  {key}) {beschreibung}")
        print("  0) Beenden")

        gueltige = set(module) | {"0"}
        wahl = frage("\nAuswahl: ", lambda a: None if a in gueltige else "Ungueltige Auswahl.")

        if wahl == "0":
            break
        _, funktion = module[wahl]
        funktion()

    if jaehrliches_update.hat_aenderungen():
        print("\n" + "=" * 60)
        print("  Aenderungen werden automatisch veroeffentlicht:")
        print("=" * 60)
        subprocess.run(["git", "status", "--short"], cwd=jaehrliches_update.ROOT)
        jaehrliches_update.commit_merge_push("Webseiten-Pflege: Aenderungen aktualisiert")

    print("\nBis zum naechsten Mal!")


if __name__ == "__main__":
    main()
