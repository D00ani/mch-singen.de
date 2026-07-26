# -*- coding: utf-8 -*-
"""
Jaehrliches technisches Update: Statistik-Chart aus der BKC-Wertung,
Bilder, Copyright-Jahr im Footer und CSS/JS-Bundles neu bauen, danach
committen/mergen/pushen. Ersetzt das frühere jahres-update.bat.

Ausfuehren: python tools/jaehrliches_update.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_WORKTREE = os.path.join(os.path.dirname(ROOT), "mch-singen.de-main")

JN_VALIDIERER = lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n."


def frage(text, validierer=None):
    while True:
        antwort = input(text).strip()
        if validierer:
            fehler = validierer(antwort)
            if fehler:
                print(f"  -> {fehler}")
                continue
        return antwort


def checkliste():
    print("\nBitte VOR dem Fortfahren pruefen/erledigen (kann dieses Tool NICHT automatisieren):")
    print("  1. Neue Wertungs-PDF hochgeladen nach")
    print("     media/dokumente/wertungen/bkcgesamtwertung_<JAHR>.pdf ?")
    print("  2. data/timer.txt / timer_trial.txt - neue Renntermine eingetragen?")
    print("     (siehe Menuepunkt 'Renntermine verwalten')")
    print("  3. data/trainingstermine<JAHR>.txt neu angelegt und in js/aktuelles.js referenziert?")
    print("  4. Vereinsmeister-Zeile eingetragen?")
    print("     (siehe Menuepunkt 'Statistiken-Seite pflegen')")
    print("  5. Jahresarchiv ergaenzt?")
    print("     (siehe Menuepunkt 'Jahresarchiv pflegen')")
    weiter = frage("\nAlles erledigt oder nicht noetig - fortfahren? (j/n): ", JN_VALIDIERER)
    return weiter.lower() == "j"


def python_tool_ausfuehren(skriptname):
    pfad = os.path.join(ROOT, "tools", skriptname)
    ergebnis = subprocess.run([sys.executable, pfad], cwd=ROOT)
    return ergebnis.returncode == 0


def git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd)


def main():
    print("=" * 60)
    print("  Jaehrliches technisches Update")
    print("=" * 60)

    if not checkliste():
        print("\nAbgebrochen. Erst die obigen Punkte erledigen, dann erneut starten.")
        return

    schritte = [
        ("Statistik-Chart aus BKC-Wertung aktualisieren", "update_statistik.py"),
        ("Bilder als WebP neu erzeugen", "optimize_images.py"),
        ("Copyright-Jahr im Footer aktualisieren", "update_copyright_year.py"),
        ("CSS/JS-Bundles neu bauen", "build_assets.py"),
    ]
    for i, (beschreibung, skript) in enumerate(schritte, start=1):
        print(f"\n[{i}/{len(schritte)}] {beschreibung} ...")
        if not python_tool_ausfuehren(skript):
            print(f"\nFEHLER bei {skript} - abgebrochen.")
            return

    print("\n" + "=" * 60)
    print("  Automatische Schritte fertig. Geaenderte Dateien:")
    print("=" * 60)
    subprocess.run(["git", "status", "--short"], cwd=ROOT)

    push = frage("\nJetzt committen und auf main pushen? (j/n): ", JN_VALIDIERER)
    if push.lower() != "j":
        print("\nNicht gepusht. Aenderungen liegen unveraendert im Arbeitsordner (arbeit).")
        return

    if git(["add", "-A"], ROOT).returncode != 0:
        print("\nFEHLER bei 'git add'.")
        return
    commit = git(["commit", "-m", "Jaehrliches Update: Statistik, Bilder, Copyright-Jahr, Build"], ROOT)
    if commit.returncode != 0:
        print("\nNichts zu committen oder Fehler bei 'git commit' - siehe Meldung oben.")
        return

    if not os.path.isdir(MAIN_WORKTREE):
        print(f"\nFEHLER: {MAIN_WORKTREE} nicht gefunden - Merge/Push manuell durchfuehren.")
        return

    if git(["merge", "arbeit", "--no-edit"], MAIN_WORKTREE).returncode != 0:
        print("\nFEHLER beim Merge nach main - bitte manuell pruefen.")
        return
    if git(["push", "origin", "main"], MAIN_WORKTREE).returncode != 0:
        print("\nFEHLER beim Push - bitte manuell pruefen.")
        return
    git(["merge", "main", "--no-edit"], ROOT)

    print("\nFertig und gepusht! GitHub Pages braucht 1-3 Minuten.")


if __name__ == "__main__":
    main()
