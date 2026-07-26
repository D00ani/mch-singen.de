# -*- coding: utf-8 -*-
"""
Aktualisiert das Copyright-Jahr ("(c) <Jahr>") im Footer aller Seiten auf das
aktuelle Jahr. Teil des jaehrlichen Updates, siehe README Abschnitt 9.

Einmal ausfuehren:
    python tools/update_copyright_year.py
"""
import glob
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAHR = str(date.today().year)
MUSTER = re.compile(r"©\s*\d{4}")


def html_dateien():
    treffer = glob.glob(os.path.join(ROOT, "*.html"))
    treffer += glob.glob(os.path.join(ROOT, "pages", "*.html"))
    return treffer


def main():
    geaendert = 0
    for pfad in html_dateien():
        with open(pfad, "r", encoding="utf-8") as f:
            inhalt = f.read()

        neu, anzahl = MUSTER.subn(f"© {JAHR}", inhalt)
        if anzahl and neu != inhalt:
            with open(pfad, "w", encoding="utf-8", newline="\n") as f:
                f.write(neu)
            geaendert += 1
            print(f"{os.path.relpath(pfad, ROOT)}: Copyright-Jahr -> {JAHR}")

    if geaendert:
        print(f"Fertig: {geaendert} Datei(en) aktualisiert.")
    else:
        print("Nichts zu tun - Copyright-Jahr ist bereits ueberall aktuell.")


if __name__ == "__main__":
    main()
