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

# Solange diese Datei existiert, geht der Arbeitsstand NICHT auf die echte
# Seite. Sie liegt im Projektordner ausserhalb beider Worktrees, damit Git
# sie weder versioniert noch beim Wechseln der Branches wegraeumt.
LIVE_SPERRE = os.path.join(os.path.dirname(ROOT), "LIVE-GESPERRT.txt")

JN_VALIDIERER = lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n."


def live_gesperrt():
    """True, solange der Arbeitsstand nur in die Beta-Vorschau darf."""
    return os.path.isfile(LIVE_SPERRE)


def sperr_hinweis():
    """Erklaerungstext, der statt einer Veroeffentlichung ausgegeben wird."""
    return (
        "\n" + "=" * 66 +
        "\n  VEROEFFENTLICHUNG GESPERRT"
        "\n" + "=" * 66 +
        "\n"
        "\n  Der Arbeitsstand geht derzeit nur in die Beta-Vorschau,"
        "\n  nicht auf mch-singen.de. Das ist so gewollt: die Website"
        "\n  wird umgebaut und soll erst in EINEM grossen Schritt live"
        "\n  gehen, nicht stueckweise."
        "\n"
        "\n  Vorschau aktualisieren (das ist der normale Weg):"
        "\n      python tools/beta_vorschau.py"
        "\n"
        "\n  Rennergebnisse sind davon nicht betroffen - die Live-Timing-"
        "\n  Synchronisation veroeffentlicht weiterhin ganz normal."
        "\n"
        "\n  Wenn wirklich alles live soll, siehe LIVE-GESPERRT.txt."
        "\n" + "=" * 66 + "\n"
    )


def frage(text, validierer=None):
    """Wie im uebrigen Werkzeug: 'x' bedeutet einen Schritt zurueck. Hier wird
    das wie ein 'n' behandelt, damit nichts ungewollt veroeffentlicht wird."""
    while True:
        antwort = input(text).strip()
        if antwort.lower() == "x":
            return "n"
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


def hat_aenderungen(cwd=ROOT):
    ergebnis = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True)
    return bool(ergebnis.stdout.strip())


def commit_merge_push(commit_message, cwd=ROOT, main_worktree=MAIN_WORKTREE):
    """Committet alle Aenderungen in arbeit, merged nach main und pusht.
    Gibt True zurueck, wenn erfolgreich gepusht wurde.

    Ist die Live-Sperre aktiv, wird NICHTS committet oder gepusht - der
    Abbruch erfolgt bewusst ganz am Anfang, damit kein halber Zustand
    entsteht."""
    if live_gesperrt():
        print(sperr_hinweis())
        return False

    if not hat_aenderungen(cwd):
        print("\nKeine Aenderungen zu committen.")
        return False

    if git(["add", "-A"], cwd).returncode != 0:
        print("\nFEHLER bei 'git add'.")
        return False
    if git(["commit", "-m", commit_message], cwd).returncode != 0:
        print("\nFEHLER bei 'git commit' - siehe Meldung oben.")
        return False

    if not os.path.isdir(main_worktree):
        print(f"\nFEHLER: {main_worktree} nicht gefunden - Merge/Push manuell durchfuehren.")
        return False

    if git(["merge", "arbeit", "--no-edit"], main_worktree).returncode != 0:
        print("\nFEHLER beim Merge nach main - bitte manuell pruefen.")
        return False
    if git(["push", "origin", "main"], main_worktree).returncode != 0:
        print("\nFEHLER beim Push - bitte manuell pruefen.")
        return False
    git(["merge", "main", "--no-edit"], cwd)

    print("\nGepusht! GitHub Pages braucht 1-3 Minuten.")
    return True


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

    commit_merge_push("Jaehrliches Update: Statistik, Bilder, Copyright-Jahr, Build")


if __name__ == "__main__":
    main()
