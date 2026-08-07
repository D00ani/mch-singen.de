# -*- coding: utf-8 -*-
"""
Arbeitsstand in die Beta-Vorschau schieben.

Das ist der normale Weg, solange die Live-Sperre aktiv ist: der Stand geht
nach https://github.com/D00ani/mch_singen_beta und NICHT auf mch-singen.de.

Ablauf:
  1. CSS/JS-Bundles neu bauen
  2. Alle Aenderungen in 'arbeit' committen
  3. 'arbeit' in den Branch 'beta-vorschau' mergen
  4. 'beta-vorschau' als 'main' in den Beta-Repo pushen
  5. Zurueck auf 'arbeit' wechseln

Warum ein eigener Branch 'beta-vorschau':
  Der Arbeitsordner enthaelt die Datei CNAME mit "mch-singen.de". GitHub
  Pages liest sie aus dem veroeffentlichten Branch und leitet daraus die
  Domain ab. Laege sie im Beta-Repo, wuerde GitHub versuchen, die echte
  Domain dorthin umzubiegen. 'beta-vorschau' ist deshalb identisch mit
  'arbeit', nur ohne CNAME.

Ausfuehren: python tools/beta_vorschau.py [-m "Commit-Text"]
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BETA_REMOTE = "beta"
BETA_URL = "https://github.com/D00ani/mch_singen_beta.git"
VORSCHAU_BRANCH = "beta-vorschau"
ARBEITS_BRANCH = "arbeit"


def git(argumente, still=False):
    """Git im Arbeitsordner ausfuehren. wincred, weil der Git Credential
    Manager in diesem Setup nicht nachfragen kann (siehe README)."""
    befehl = ["git", "-c", "credential.helper=wincred"] + argumente
    umgebung = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(befehl, cwd=ROOT, env=umgebung, text=True,
                          encoding="utf-8", errors="replace",
                          capture_output=still)


def git_text(argumente):
    ergebnis = git(argumente, still=True)
    return ergebnis.stdout.strip() if ergebnis.returncode == 0 else ""


def abbruch(text, zurueck_auf_arbeit=True):
    print(f"\nABBRUCH: {text}")
    if zurueck_auf_arbeit and git_text(["branch", "--show-current"]) != ARBEITS_BRANCH:
        git(["checkout", ARBEITS_BRANCH], still=True)
        print(f"Zurueck auf Branch '{ARBEITS_BRANCH}'.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Arbeitsstand in die Beta-Vorschau schieben.")
    parser.add_argument("-m", "--nachricht", default="Arbeitsstand aktualisiert",
                        help="Commit-Text fuer noch nicht committete Aenderungen")
    args = parser.parse_args()

    print("=" * 60)
    print("  BETA-VORSCHAU AKTUALISIEREN")
    print("=" * 60)

    start_branch = git_text(["branch", "--show-current"])
    if start_branch != ARBEITS_BRANCH:
        abbruch(f"Du bist auf Branch '{start_branch}', erwartet wird '{ARBEITS_BRANCH}'.",
                zurueck_auf_arbeit=False)

    # --- Remote sicherstellen ---
    if BETA_REMOTE not in git_text(["remote"]).split():
        print(f"\n[0/5] Remote '{BETA_REMOTE}' anlegen ...")
        git(["remote", "add", BETA_REMOTE, BETA_URL], still=True)

    # --- 1. Bundles bauen ---
    print("\n[1/5] Bundles bauen ...")
    bau = subprocess.run([sys.executable, os.path.join("tools", "build_assets.py")],
                         cwd=ROOT, text=True)
    if bau.returncode != 0:
        abbruch("build_assets.py ist fehlgeschlagen.", zurueck_auf_arbeit=False)

    # --- 2. Committen ---
    print("\n[2/5] Aenderungen committen ...")
    if git_text(["status", "--porcelain"]):
        git(["add", "-A"], still=True)
        if git(["commit", "-m", args.nachricht], still=True).returncode != 0:
            abbruch("git commit fehlgeschlagen.", zurueck_auf_arbeit=False)
        print(f"  committet: {args.nachricht}")
    else:
        print("  nichts zu committen, Stand ist schon gesichert")

    # --- 3. In den Vorschau-Branch mergen ---
    print(f"\n[3/5] Nach '{VORSCHAU_BRANCH}' mergen ...")
    if git(["checkout", VORSCHAU_BRANCH], still=True).returncode != 0:
        abbruch(f"Branch '{VORSCHAU_BRANCH}' nicht gefunden.", zurueck_auf_arbeit=False)

    if git(["merge", ARBEITS_BRANCH, "--no-edit"], still=True).returncode != 0:
        abbruch("Merge fehlgeschlagen - bitte von Hand pruefen.")

    # Sicherheitsnetz: ohne diese Pruefung koennte die CNAME-Datei
    # unbemerkt mitwandern und im Beta-Repo die echte Domain kapern.
    if os.path.isfile(os.path.join(ROOT, "CNAME")):
        abbruch("CNAME liegt im Vorschau-Branch. Nicht gepusht. "
                "Bitte 'git rm CNAME' auf '" + VORSCHAU_BRANCH + "' ausfuehren.")

    # --- 4. Pushen ---
    print(f"\n[4/5] In den Beta-Repo pushen ...")
    if git(["push", "-f", BETA_REMOTE, f"{VORSCHAU_BRANCH}:main"], still=True).returncode != 0:
        abbruch("Push fehlgeschlagen. Internet? Zugangsdaten?")

    # --- 5. Zurueck ---
    print(f"\n[5/5] Zurueck auf '{ARBEITS_BRANCH}' ...")
    git(["checkout", ARBEITS_BRANCH], still=True)

    jetziger = git_text(["branch", "--show-current"])
    if jetziger != ARBEITS_BRANCH:
        print(f"\nWARNUNG: Du stehst auf '{jetziger}', nicht auf '{ARBEITS_BRANCH}'.")
        print(f"Bitte von Hand: git checkout {ARBEITS_BRANCH}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  FERTIG")
    print("=" * 60)
    print("\n  Vorschau: https://d00ani.github.io/mch_singen_beta/")
    print("  GitHub Pages braucht 1-3 Minuten.")
    print("\n  Die echte Seite mch-singen.de ist unveraendert.\n")


if __name__ == "__main__":
    main()
