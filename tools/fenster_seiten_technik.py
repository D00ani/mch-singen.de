# -*- coding: utf-8 -*-
"""
Fensterseite fuer das technische Update.

Fuehrt dieselben vier Schritte aus wie tools/jaehrliches_update.py, zeigt
dabei aber laufend an, welcher gerade laeuft und was er ausgibt - im
Terminal rauscht das sonst durch.

Veroeffentlicht wird hier NICHT: das laeuft ueber die Fussleiste, damit
es nur eine Stelle gibt, an der etwas online geht.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import subprocess
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fenster_bausteine as B
import pflege_hilfen as h
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT

SCHRITTE = [
    ("update_statistik.py", "Statistik-Diagramm",
     "Liest die BKC-Wertungs-PDF aus und schreibt data/statistik.json neu."),
    ("optimize_images.py", "Bilder als WebP",
     "Erzeugt alle WebP-Fassungen neu — nötig, wenn ein Bild ersetzt wurde."),
    ("update_copyright_year.py", "Copyright-Jahr",
     "Setzt „© <Jahr>“ im Fußbereich aller Seiten auf das laufende Jahr."),
    ("build_assets.py", "CSS/JS-Bundles",
     "Baut die .min-Dateien. Ohne diesen Schritt sind CSS/JS-Änderungen online unsichtbar."),
]

CHECKLISTE = [
    "Neue Wertungs-PDF liegt unter media/dokumente/wertungen/bkcgesamtwertung_<Jahr>.pdf?",
    "Renntermine der neuen Saison eingetragen?",
    "Trainingstermine der neuen Saison angelegt und in js/aktuelles.js eingetragen?",
    "Vereinsmeister und Wanderpokal-Sieger nachgetragen?",
    "Jahresarchiv um die abgeschlossene Saison ergänzt?",
]


class TechnikSeite(Seite):
    titel = "Technisches Update"
    untertitel = ("Vier Schritte, die nach inhaltlichen Änderungen fällig werden. "
                  "Veröffentlicht wird nichts — das läuft über die Leiste unten.")

    def baue(self):
        self.knopf_start = self.knopf("Update starten", self.starten, "haupt")
        self.laeuft = False
        self.marken = {}

    def aktualisieren(self):
        if self.laeuft:
            return
        self.leeren()

        B.abschnitt(self.inhalt, self.s, "Vorher abhaken",
                    "kann das Werkzeug nicht selbst prüfen")
        for punkt in CHECKLISTE:
            B.karte(self.inhalt, self.s, uebersicht.INFO, punkt)

        tk.Frame(self.inhalt, bg=B.FARBEN["linie"], height=1).pack(fill="x", pady=14)

        B.abschnitt(self.inhalt, self.s, "Schritte", f"{len(SCHRITTE)} nacheinander")
        self.marken = {}
        for skript, name, erklaerung in SCHRITTE:
            rahmen = B.karte(self.inhalt, self.s, uebersicht.INFO, name, erklaerung)
            marke = tk.Label(rahmen, text="offen", bg=B.FARBEN["karte"],
                             fg=B.FARBEN["gedimmt"], font=self.s.label)
            marke.pack(side="right", padx=14)
            self.marken[skript] = marke

        self.protokoll = tk.Text(self.inhalt, height=12, font=self.s.daten, wrap="word",
                                 bg=B.FARBEN["karte"], fg=B.FARBEN["text"],
                                 relief="solid", bd=1, padx=10, pady=8)
        self.protokoll.pack(fill="both", expand=True, pady=(14, 0))
        self.protokoll.insert("1.0", "Noch nicht gestartet.\n")
        self.protokoll.configure(state="disabled")

    def _schreibe(self, text, ersetzen=False):
        self.protokoll.configure(state="normal")
        if ersetzen:
            self.protokoll.delete("1.0", "end")
        self.protokoll.insert("end", text)
        self.protokoll.see("end")
        self.protokoll.configure(state="disabled")

    def _marke(self, skript, text, farbe):
        if skript in self.marken:
            self.marken[skript].configure(text=text, fg=farbe)

    def starten(self):
        if self.laeuft:
            return
        self.laeuft = True
        self.knopf_start.configure(state="disabled", bg=B.FARBEN["matt"], text="Läuft …")
        self._schreibe("", ersetzen=True)
        self._naechster(0)

    def _naechster(self, nummer):
        if nummer >= len(SCHRITTE):
            self._fertig()
            return

        skript, name, _ = SCHRITTE[nummer]
        self._marke(skript, "läuft …", B.FARBEN["blau"])
        self._schreibe(f"[{nummer + 1}/{len(SCHRITTE)}] {name} ({skript})\n")

        def arbeit():
            ergebnis = subprocess.run(
                [sys.executable, os.path.join(ROOT, "tools", skript)],
                cwd=ROOT, capture_output=True, text=True,
                encoding="utf-8", errors="replace")
            return ergebnis.returncode, (ergebnis.stdout or "") + (ergebnis.stderr or "")

        B.im_hintergrund(self.rahmen, arbeit,
                         lambda e: self._schritt_fertig(nummer, *e))

    def _schritt_fertig(self, nummer, code, ausgabe):
        skript, name, _ = SCHRITTE[nummer]
        for zeile in ausgabe.strip().splitlines():
            self._schreibe("      " + zeile + "\n")

        if code == 0:
            self._marke(skript, "erledigt", B.FARBEN["gut"])
            self._schreibe("\n")
            self._naechster(nummer + 1)
        else:
            self._marke(skript, "fehlgeschlagen", B.FARBEN["faellig"])
            self._schreibe(f"\nAbgebrochen: {name} endete mit Fehler {code}.\n"
                           "Die folgenden Schritte wurden nicht ausgeführt.\n")
            self._fertig(erfolg=False)

    def _fertig(self, erfolg=True):
        self.laeuft = False
        self.knopf_start.configure(state="normal", bg=B.FARBEN["blau"],
                                   text="Erneut starten" if erfolg else "Nochmal versuchen")
        if erfolg:
            self._schreibe("Alle Schritte erledigt.\n\n"
                           "Was sich geändert hat, steht unten in der Leiste — "
                           "veröffentlicht wird erst auf Knopfdruck.\n")
        self.app.fuss_auffrischen()
