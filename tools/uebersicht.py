# -*- coding: utf-8 -*-
"""
Lagebericht beim Start der Webseiten-Pflege: was ist faellig, was ist
liegengeblieben, was ist noch nicht veroeffentlicht.

Sammelt nur bereits vorhandene Informationen (timer.txt, archiv.html,
Copyright-Jahr, Build-Stand, git) und schaut NICHT ins Internet - der
Bericht muss in unter einer Sekunde dastehen.

Ausfuehren: python tools/uebersicht.py
Wird ausserdem beim Start von tools/website_pflege.py angezeigt.
"""
import os
import re
import subprocess
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import pruefe_seite
import termine_verwalten as tv

ROOT = h.ROOT

# Dringlichkeit: bestimmt Reihenfolge und Zeichen vor der Zeile
LAGE, FAELLIG, HINWEIS, INFO = -1, 0, 1, 2
ZEICHEN = {LAGE: " ", FAELLIG: "!", HINWEIS: "-", INFO: " "}

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _hinweis(dringlichkeit, text, wohin=None, werkzeug=None):
    """werkzeug ist der Modulname, der das Problem loest (z. B.
    "ausschreibung_pdf") - das Fenster macht daraus einen Knopf, im
    Terminal steht stattdessen der Menuepunkt aus wohin."""
    return (dringlichkeit, text, wohin, werkzeug)


# ------------------------------------------------------------------
# Einzelne Pruefungen
# ------------------------------------------------------------------

def termin_datum(zeile):
    """Macht aus einer timer.txt-Zeile ein date - oder None."""
    teile = zeile.split(";")
    if len(teile) < 3:
        return None
    monat = tv.MONAT_ALIASE.get(teile[1].strip().lower())
    if not monat or not teile[0].strip().isdigit() or not teile[2].strip().isdigit():
        return None
    try:
        return date(int(teile[2]), monat[0], int(teile[0]))
    except ValueError:
        return None


def naechste_rennen(heute=None):
    """Je Sportart das naechste anstehende Rennen.

    Liefert Woerterbuecher mit sportart/tage/wann/beschreibung/datum - so
    koennen Terminalausgabe und Fenster dieselbe Quelle nutzen, statt die
    Rechnerei zweimal zu haben. tage ist None, wenn nichts mehr ansteht.
    """
    heute = heute or date.today()
    ergebnis = []
    for name, sportart in (("timer.txt", "Kart"), ("timer_trial.txt", "Trial")):
        zeilen = h.lies_zeilen(os.path.join(ROOT, "data", name))
        termine = [(termin_datum(z), z) for z in zeilen]
        termine = [(d, z) for d, z in termine if d]
        if not termine:
            continue

        kommend = sorted((d, z) for d, z in termine if d >= heute)
        altlast = [z for d, z in termine if d.year < heute.year]

        eintrag = {"sportart": sportart, "altlast": len(altlast),
                   "tage": None, "wann": "", "beschreibung": "", "datum": None,
                   "deutsch": ""}
        if kommend:
            wann_datum, zeile = kommend[0]
            tage = (wann_datum - heute).days
            teile = zeile.split(";")
            uhrzeit = teile[3].strip() if len(teile) > 3 else ""
            wo = " ".join(t.strip() for t in teile[4:6] if t.strip())
            eintrag.update(
                tage=tage,
                wann="heute" if tage == 0 else ("morgen" if tage == 1 else f"in {tage} Tagen"),
                beschreibung=tv.beschreibe_termin(zeile),
                datum=wann_datum,
                # Fuer Anzeigen, die nicht dem timer.txt-Format folgen muessen
                deutsch=" · ".join(teil for teil in (
                    f"{WOCHENTAGE[wann_datum.weekday()]} {wann_datum.strftime('%d.%m.%Y')}",
                    uhrzeit, wo) if teil))
        ergebnis.append(eintrag)
    return ergebnis


def pruefe_termine(heute):
    hinweise = []
    for rennen in naechste_rennen(heute):
        sportart = rennen["sportart"]

        if rennen["tage"] is None:
            hinweise.append(_hinweis(
                FAELLIG,
                f"{sportart}: kein kommender Termin mehr — neue Saison eintragen",
                'Menüpunkt "Renntermine verwalten"', "termine_verwalten"))
        else:
            hinweise.append(_hinweis(
                LAGE,
                f"Nächstes {sportart}-Rennen {rennen['wann']}: {rennen['beschreibung']}"))

        # Nur Termine aus ABGESCHLOSSENEN Jahren sind Altlast - schon gefahrene
        # Rennen der laufenden Saison gehoeren dort hin.
        if rennen["altlast"]:
            hinweise.append(_hinweis(
                HINWEIS,
                f"{sportart}: {rennen['altlast']} Termin(e) aus Vorjahren stehen noch in der Datei",
                'Menüpunkt "Renntermine verwalten" (löschen oder stehen lassen)',
                "termine_verwalten"))
    return hinweise


def pruefe_copyright(heute):
    jahre = set()
    for pfad in pruefe_seite.html_dateien():
        jahre.update(re.findall(r"©\s*(\d{4})", h.lies_datei(pfad)))
    veraltet = sorted(j for j in jahre if int(j) < heute.year)
    if veraltet:
        return [_hinweis(
            FAELLIG,
            f"Copyright im Footer steht auf {', '.join(veraltet)} — aktuell ist {heute.year}",
            'Menüpunkt "Technisches Update"', "jaehrliches_update")]
    return []


def pruefe_archiv(heute):
    """Ist die abgeschlossene Saison (Vorjahr) schon im Archiv?"""
    archiv = os.path.join(ROOT, "pages", "archiv.html")
    if not os.path.isfile(archiv):
        return []
    jahre = set(re.findall(r"<summary>Saison (\d{4})</summary>", h.lies_datei(archiv)))
    vorjahr = str(heute.year - 1)
    if vorjahr not in jahre:
        return [_hinweis(
            FAELLIG, f"Saison {vorjahr} fehlt noch im Jahresarchiv",
            'Menüpunkt "Jahresarchiv pflegen"', "archiv_pflege")]
    return []


def pruefe_trainingstermine(heute):
    """js/aktuelles.js verweist fest auf eine Jahresdatei - die muss zum
    Jahreswechsel mitwandern, sonst bleibt der ICS-Download leer."""
    aktuelles_js = os.path.join(ROOT, "js", "aktuelles.js")
    if not os.path.isfile(aktuelles_js):
        return []
    treffer = re.findall(r"trainingstermine(\d{4})\.txt", h.lies_datei(aktuelles_js))
    if not treffer:
        return []

    jahr = max(treffer)
    hinweise = []
    if int(jahr) < heute.year:
        hinweise.append(_hinweis(
            FAELLIG,
            f"js/aktuelles.js lädt noch trainingstermine{jahr}.txt (Jahr {heute.year} laeuft)",
            f"data/trainingstermine{heute.year}.txt anlegen und in js/aktuelles.js eintragen"))
    elif not os.path.isfile(os.path.join(ROOT, "data", f"trainingstermine{jahr}.txt")):
        hinweise.append(_hinweis(
            FAELLIG, f"data/trainingstermine{jahr}.txt fehlt, wird aber von js/aktuelles.js geladen"))
    return hinweise


def pruefe_wanderpokal(heute):
    """Wanderpokal-Sieger der abgeschlossenen Saison eingetragen?"""
    seite = os.path.join(ROOT, "pages", "statistiken.html")
    if not os.path.isfile(seite):
        return []
    inhalt = h.lies_datei(seite)
    vorjahr = str(heute.year - 1)
    # Grob: taucht das Vorjahr irgendwo in einer Tabellenzelle auf?
    if not re.search(rf"<td>\s*(<strong>)?\s*{vorjahr}\b", inhalt):
        return [_hinweis(
            HINWEIS, f"Wanderpokal-Sieger {vorjahr} scheinen noch zu fehlen",
            'Menüpunkt "Statistiken-Seite pflegen"', "statistiken_pflege")]
    return []


def pruefe_offene_arbeit():
    hinweise = []

    fehlende_pdfs = pruefe_seite.pruefe_angekuendigte_pdfs()
    if fehlende_pdfs:
        hinweise.append(_hinweis(
            HINWEIS, f"{len(fehlende_pdfs)} angekündigte PDF-Datei(en) fehlen noch",
            'Menüpunkt "Ausschreibungs-PDF einpflegen"', "ausschreibung_pdf"))

    veralteter_build = pruefe_seite.pruefe_build_aktuell()
    if veralteter_build:
        hinweise.append(_hinweis(
            FAELLIG, f"{len(veralteter_build)}x Build-Schritt fehlt — Änderung ist online unsichtbar",
            'Menüpunkt "Technisches Update"', "jaehrliches_update"))

    return hinweise


def _git(*args):
    try:
        ergebnis = subprocess.run(["git"] + list(args), cwd=ROOT,
                                  capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return ergebnis.stdout.strip() if ergebnis.returncode == 0 else None


def pruefe_veroeffentlichung(heute):
    hinweise = []

    status = _git("status", "--porcelain")
    if status is None:
        return []
    if status:
        anzahl = len(status.splitlines())
        hinweise.append(_hinweis(
            HINWEIS, f"{anzahl} Datei(en) geändert, aber noch nicht veröffentlicht",
            "beim Beenden bzw. über \"Veröffentlichen\""))

    letzter = _git("log", "-1", "--format=%cd", "--date=short")
    if letzter:
        try:
            tage = (heute - datetime.strptime(letzter, "%Y-%m-%d").date()).days
        except ValueError:
            return hinweise
        if tage > 60:
            hinweise.append(_hinweis(
                INFO, f"Letzte Veröffentlichung vor {tage} Tagen ({letzter})"))
    return hinweise


def pruefe_bilder():
    try:
        import bilder_pflege
    except SystemExit:
        return []  # Pillow fehlt - kein Grund, die Uebersicht abzubrechen
    ohne_webp = bilder_pflege.finde_bilder_ohne_webp()
    if ohne_webp:
        return [_hinweis(
            HINWEIS, f"{len(ohne_webp)} Bild(er) ohne WebP-Fassung (lädt unnötig langsam)",
            'Menüpunkt "Bilder aufnehmen"', "bilder_pflege")]
    return []


# ------------------------------------------------------------------
# Zusammenbauen und anzeigen
# ------------------------------------------------------------------

PRUEFUNGEN_MIT_DATUM = [
    pruefe_termine, pruefe_copyright, pruefe_archiv,
    pruefe_trainingstermine, pruefe_wanderpokal, pruefe_veroeffentlichung,
]
PRUEFUNGEN_OHNE_DATUM = [pruefe_offene_arbeit, pruefe_bilder]


def sammle(heute=None, ausser=()):
    """ausser: Namen von Pruefungen, die uebersprungen werden sollen - das
    Fenster laesst z. B. pruefe_veroeffentlichung weg, weil dieselbe Angabe
    dort schon in der Fussleiste steht."""
    heute = heute or date.today()
    hinweise = []
    for pruefung in PRUEFUNGEN_MIT_DATUM:
        if pruefung.__name__ in ausser:
            continue
        try:
            hinweise.extend(pruefung(heute))
        except Exception as fehler:            # eine kaputte Pruefung darf den
            hinweise.append(_hinweis(          # Start nicht blockieren
                INFO, f"({pruefung.__name__} konnte nicht laufen: {fehler})"))
    for pruefung in PRUEFUNGEN_OHNE_DATUM:
        if pruefung.__name__ in ausser:
            continue
        try:
            hinweise.extend(pruefung())
        except Exception as fehler:
            hinweise.append(_hinweis(INFO, f"({pruefung.__name__} konnte nicht laufen: {fehler})"))
    hinweise.sort(key=lambda e: e[0])
    return hinweise


def zeige(hinweise=None, ueberschrift=True):
    hinweise = sammle() if hinweise is None else hinweise

    if ueberschrift:
        print("\n" + "=" * 60)
        print("  Was steht an?")
        print("=" * 60)

    if not hinweise:
        print("\nNichts Offenes — alles auf Stand.")
        return

    print()
    for dringlichkeit, text, wohin, _werkzeug in hinweise:
        print(f"  {ZEICHEN[dringlichkeit]} {text}")
        if wohin:
            print(f"      -> {wohin}")

    if not any(e[0] == FAELLIG for e in hinweise):
        print("\n  Nichts Dringendes.")


def main():
    zeige()


if __name__ == "__main__":
    main()
