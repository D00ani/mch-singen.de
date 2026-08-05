# -*- coding: utf-8 -*-
"""
Die restlichen Fensterseiten: Bilder aufnehmen, Trainingstermine
importieren und die beiden Assistenten (Nach dem Rennen, Saisonwechsel).

Die Assistenten sind im Fenster deutlich handlicher als im Terminal: statt
Unterwerkzeuge zu starten, springen sie direkt auf die passende Seite und
merken sich, was schon erledigt ist.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import sys
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fenster_bausteine as B
import pflege_hilfen as h
import trainingstermine_import as tti
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT


# ------------------------------------------------------------------
# Wiederherstellen aus dem Verlauf
# ------------------------------------------------------------------

class VerlaufSeite(Seite):
    titel = "Verlauf und Wiederherstellen"
    untertitel = ("Vor jeder Änderung legt das Werkzeug eine Sicherung an. Hier stehen "
                  "alle aufgehobenen Stände — nicht nur der letzte.")

    def baue(self):
        self.knopf("Wiederherstellen", self.wiederherstellen, "haupt")
        self.knopf("Neu einlesen", self.aktualisieren)
        self.baum = None
        self.staende = {}

    def aktualisieren(self):
        self.leeren()
        self.staende = h.sicherungs_verlauf()
        gesamt = sum(len(v) for v in self.staende.values())

        B.abschnitt(self.inhalt, self.s, "Aufgehobene Stände",
                    f"{gesamt} Stände zu {len(self.staende)} Datei(en) · "
                    f"Platz für {h.MAX_SICHERUNGEN}")

        if not self.staende:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Noch keine Sicherung vorhanden.",
                    "Sobald du etwas änderst, sammeln sich hier die Stände.")
            self.baum = None
            return

        huelle = tk.Frame(self.inhalt, bg=B.FARBEN["grund"])
        huelle.pack(fill="both", expand=True)
        self.baum = ttk.Treeview(huelle, columns=("zeit", "groesse"),
                                 show="tree headings", height=15)
        self.baum.heading("#0", text="DATEI / STAND")
        self.baum.heading("zeit", text="GESICHERT AM")
        self.baum.heading("groesse", text="GRÖSSE")
        self.baum.column("#0", width=360)
        self.baum.column("zeit", width=190)
        self.baum.column("groesse", width=100, anchor="e")
        leiste = ttk.Scrollbar(huelle, orient="vertical", command=self.baum.yview)
        self.baum.configure(yscrollcommand=leiste.set)
        leiste.pack(side="right", fill="y")
        self.baum.pack(side="left", fill="both", expand=True)

        for nummer, (relativ, liste) in enumerate(sorted(self.staende.items())):
            knoten = self.baum.insert("", "end", iid=f"d{nummer}",
                                      text=f"{relativ.replace(os.sep, '/')}   ({len(liste)})",
                                      values=(liste[0]["zeitpunkt"] + "  (neuester)", ""),
                                      open=nummer == 0)
            for lauf, stand in enumerate(liste):
                kb = stand["groesse"] / 1024
                self.baum.insert(knoten, "end", iid=f"d{nummer}s{lauf}",
                                 text=f"  Stand {lauf + 1}",
                                 values=(stand["zeitpunkt"],
                                         f"{kb/1024:.1f} MB" if kb > 1024 else f"{kb:.0f} KB"))
        self.baum.bind("<Double-1>", lambda _: self.wiederherstellen())

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Der aktuelle Stand wird vor dem Wiederherstellen selbst noch "
                       "gesichert — auch dieser Schritt lässt sich also zurücknehmen. "
                       f"Es werden die letzten {h.MAX_SICHERUNGEN} Änderungen "
                       "aufgehoben, ältere fallen heraus.")).pack(anchor="w", pady=(12, 0))

    def wiederherstellen(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Nichts gewählt",
                                "Bitte einen einzelnen Stand in der Liste anklicken.")
            return

        kennung = self.baum.selection()[0]
        if "s" not in kennung:
            messagebox.showinfo("Datei gewählt",
                                "Bitte einen einzelnen Stand unterhalb der Datei anklicken "
                                "— dort steht, von wann er ist.")
            return

        datei, lauf = (int(teil) for teil in kennung[1:].split("s"))
        relativ = sorted(self.staende)[datei]
        stand = self.staende[relativ][lauf]

        if not messagebox.askyesno(
                "Wiederherstellen",
                f"{relativ.replace(os.sep, '/')}\n\n"
                f"wird auf den Stand von {stand['zeitpunkt']} zurückgesetzt.\n\n"
                "Der jetzige Stand wird vorher gesichert.\n\nFortfahren?"):
            return

        try:
            h.sicherung_einspielen(stand)
        except OSError as fehler:
            messagebox.showerror("Fehlgeschlagen", str(fehler))
            return

        messagebox.showinfo("Wiederhergestellt",
                            f"{relativ.replace(os.sep, '/')} steht wieder auf dem "
                            f"Stand von {stand['zeitpunkt']}.")
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Bilder aufnehmen
# ------------------------------------------------------------------

class BilderSeite(Seite):
    titel = "Bilder aufnehmen"
    untertitel = ("Erzeugt die WebP-Fassungen und den fertigen HTML-Block. "
                  "Die Bilddatei vorher in den passenden Unterordner von media/bilder/ legen.")

    def baue(self):
        self.knopf("WebP erzeugen", self.aufnehmen, "haupt")
        self.knopf("Alle als Galerie", self.stapel)
        self.knopf("Neu einlesen", self.aktualisieren)
        self.baum = None
        self.kandidaten = []

    def _modul(self):
        """Erst hier importieren - ohne Pillow beendet sich das Modul."""
        try:
            import bilder_pflege
            return bilder_pflege
        except SystemExit:
            return None

    def aktualisieren(self):
        self.leeren()
        modul = self._modul()
        if modul is None:
            B.karte(self.inhalt, self.s, 0, "Pillow fehlt",
                    "Einmalig im Terminal ausführen:  pip install Pillow")
            self.baum = None
            return

        self.kandidaten = modul.finde_bilder_ohne_webp()
        B.abschnitt(self.inhalt, self.s, "Bilder ohne WebP-Fassung",
                    f"{len(self.kandidaten)} gefunden")

        if not self.kandidaten:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Alle Bilder unter media/ haben bereits eine WebP-Fassung.",
                    "Neues Bild zuerst in den passenden Unterordner von media/bilder/ legen.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Datei", "Größe", "Pixel"),
                                 (400, 110, 130), hoehe=min(len(self.kandidaten), 12),
                                 zeilenzahl=len(self.kandidaten))
        self.baum.configure(selectmode="extended")   # mehrere auf einmal waehlbar
        from PIL import Image
        for nummer, pfad in enumerate(self.kandidaten):
            try:
                with Image.open(pfad) as bild:
                    pixel = f"{bild.width}×{bild.height}"
            except OSError:
                pixel = "—"
            kb = os.path.getsize(pfad) / 1024
            groesse = f"{kb/1024:.1f} MB" if kb > 1024 else f"{kb:.0f} KB"
            self.baum.insert("", "end", iid=str(nummer),
                             values=(os.path.relpath(pfad, ROOT).replace(os.sep, "/"),
                                     groesse, pixel))
        self.baum.bind("<Double-1>", lambda _: self.aufnehmen())

    def aufnehmen(self):
        modul = self._modul()
        if modul is None or not self.kandidaten:
            return
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Kein Bild gewählt",
                                "Bitte zuerst ein Bild in der Liste anklicken.")
            return

        quelle = self.kandidaten[int(self.baum.selection()[0])]
        beschriftungen = []
        for eintrag in modul.VERWENDUNGEN:
            breiten = ("unverändert" if eintrag["breiten"] == [None]
                       else ", ".join(f"{b}px" for b in eintrag["breiten"]))
            beschriftungen.append(f"{eintrag['name']} — {breiten}")

        werte = B.frage_formular(
            self.rahmen, self.s, "Bild aufnehmen", [
                {"schluessel": "verwendung", "beschriftung": "Verwendung",
                 "art": "auswahl", "optionen": beschriftungen},
                {"schluessel": "alt", "beschriftung": "Bildbeschreibung",
                 "hinweis": "wichtig für Screenreader und Google"},
                {"schluessel": "ort", "beschriftung": "Wird eingebunden auf",
                 "art": "auswahl", "optionen": ["Unterseite in /pages/", "Startseite"]},
            ],
            einleitung=f"{os.path.relpath(quelle, ROOT)}\n\nDie Größen bestimmen, "
                       "welche WebP-Fassungen entstehen.")
        if not werte:
            return

        verwendung = modul.VERWENDUNGEN[beschriftungen.index(werte["verwendung"])]
        try:
            erzeugt, originalgroesse = modul.erzeuge_webp(quelle, verwendung["breiten"])
        except Exception as fehler:
            messagebox.showerror("Umwandlung fehlgeschlagen", str(fehler))
            return

        block = modul.baue_picture_block(
            quelle, erzeugt, originalgroesse,
            werte["ort"].startswith("Unterseite"), B.fuer_html(werte["alt"]))

        self.aktualisieren()
        self._zeige_block(erzeugt, block)
        self.app.fuss_auffrischen()

    def stapel(self):
        """Mehrere Fotos auf einmal - nach einem Rennen kommen 20, nicht eins."""
        modul = self._modul()
        if modul is None or not self.kandidaten:
            return

        gewaehlt = ([self.kandidaten[int(k)] for k in self.baum.selection()]
                    if self.baum and self.baum.selection() else list(self.kandidaten))

        werte = B.frage_formular(
            self.rahmen, self.s, f"{len(gewaehlt)} Bilder als Galerie", [
                {"schluessel": "alt", "beschriftung": "Bildbeschreibung",
                 "hinweis": "gilt für alle; wird durchnummeriert"},
                {"schluessel": "ort", "beschriftung": "Wird eingebunden auf",
                 "art": "auswahl", "optionen": ["Unterseite in /pages/", "Startseite"]},
            ],
            einleitung=("Alle gewählten Bilder werden als Galerie-Kacheln aufgenommen "
                        "(400 und 800 Pixel breit). Ohne Auswahl werden alle "
                        f"{len(self.kandidaten)} genommen."))
        if not werte:
            return

        von_unterseite = werte["ort"].startswith("Unterseite")
        breiten = next(v["breiten"] for v in modul.VERWENDUNGEN
                       if v["name"].startswith("Kleines"))

        bloecke, erzeugt_alle, fehler = [], [], []
        for nummer, quelle in enumerate(gewaehlt, start=1):
            try:
                erzeugt, masse = modul.erzeuge_webp(quelle, breiten)
            except Exception as f:
                fehler.append(f"{os.path.basename(quelle)}: {f}")
                continue
            erzeugt_alle += erzeugt
            beschriftung = B.fuer_html(f"{werte['alt']} ({nummer})")
            bloecke.append(modul.baue_picture_block(quelle, erzeugt, masse,
                                                    von_unterseite, beschriftung))

        if fehler:
            messagebox.showwarning("Nicht alle umgewandelt", "\n".join(fehler[:8]))
        if not bloecke:
            return

        einrueckung = " " * 16
        galerie = (f'{" " * 12}<div class="galerie-grid">\r\n'
                   + "\r\n".join(einrueckung + b.replace("\n", "\n" + " " * 4)
                                 for b in bloecke)
                   + f'\r\n{" " * 12}</div>')

        self.aktualisieren()
        self._zeige_block(erzeugt_alle, galerie,
                          f"{len(bloecke)} Bilder als Galerie")
        self.app.fuss_auffrischen()

    def _zeige_block(self, erzeugt, block, ueberschrift="Erzeugt"):
        B.abschnitt(self.inhalt, self.s, ueberschrift)
        for ziel, (breite, hoehe), kb in erzeugt:
            B.karte(self.inhalt, self.s, 2,
                    os.path.relpath(ziel, ROOT).replace(os.sep, "/"),
                    f"{breite}×{hoehe} Pixel · {kb} KB")

        B.abschnitt(self.inhalt, self.s, "Diesen Block ins HTML einfügen")
        kasten = tk.Text(self.inhalt, height=8, font=self.s.daten, wrap="none",
                         bg=B.FARBEN["karte"], fg=B.FARBEN["text"],
                         relief="solid", bd=1, padx=10, pady=8)
        kasten.pack(fill="x")
        kasten.insert("1.0", block)

        def kopieren():
            self.rahmen.clipboard_clear()
            self.rahmen.clipboard_append(block)
            messagebox.showinfo("Kopiert", "Der Block liegt in der Zwischenablage.")

        B.knopf(self.inhalt, "In die Zwischenablage", kopieren,
                self.s, "haupt").pack(anchor="w", pady=(10, 0))
        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Bilder brauchen keinen Build-Schritt. Wird ein bestehendes Bild "
                       "ERSETZT (gleicher Dateiname), stattdessen das technische Update "
                       "laufen lassen — das erzeugt die vorhandenen Fassungen neu.")).pack(
                           anchor="w", pady=(10, 0))


# ------------------------------------------------------------------
# Trainingstermine
# ------------------------------------------------------------------

class TrainingstermineSeite(Seite):
    titel = "Trainingstermine importieren"
    untertitel = ("Wandelt den Excel-Export in das Format um, das der Kalender-Download "
                  "braucht. Export vorher als .txt (Tab-getrennt) nach data/ legen.")

    def baue(self):
        self.knopf("Importieren", self.importieren, "haupt")
        self.knopf("Neu einlesen", self.aktualisieren)
        self.baum = None
        self.quellen = []

    def aktualisieren(self):
        self.leeren()
        try:
            self.quellen = tti.finde_quelldateien()
        except OSError as fehler:
            B.karte(self.inhalt, self.s, 0, "data/ nicht lesbar", str(fehler))
            self.baum = None
            return

        B.abschnitt(self.inhalt, self.s, "Gefundene Export-Dateien",
                    f"{len(self.quellen)} Tab-getrennte .txt in data/")

        if not self.quellen:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Keine Tab-getrennte .txt-Datei in data/ gefunden.",
                    "In Excel „Speichern unter“ → „Text (Tabstopp-getrennt)“, "
                    "dann nach data/ legen.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Datei", "Kodierung", "Termine erkannt"),
                                 (330, 130, 180), hoehe=min(len(self.quellen), 10),
                                 zeilenzahl=len(self.quellen))
        for nummer, pfad in enumerate(self.quellen):
            text, kodierung = tti.lies_quelle(pfad)
            try:
                zeilen, uebersprungen, _, _ = tti.wandle_um(text)
                erkannt = f"{len(zeilen)} Zeilen"
                if uebersprungen:
                    erkannt += f" ({len(uebersprungen)} übersprungen)"
            except ValueError:
                erkannt = "Kopfzeile fehlt"
            self.baum.insert("", "end", iid=str(nummer),
                             values=(os.path.relpath(pfad, ROOT).replace(os.sep, "/"),
                                     kodierung, erkannt))
        self.baum.bind("<Double-1>", lambda _: self.importieren())

    def importieren(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Keine Datei gewählt",
                                "Bitte zuerst eine Export-Datei anklicken.")
            return

        quelle = self.quellen[int(self.baum.selection()[0])]
        text, kodierung = tti.lies_quelle(quelle)
        try:
            zeilen, uebersprungen, _, _ = tti.wandle_um(text)
        except ValueError as fehler:
            messagebox.showerror("Umwandlung nicht möglich", str(fehler))
            return

        if not zeilen:
            messagebox.showerror("Nichts erkannt",
                                 "In der Datei wurden keine Trainingstermine gefunden.")
            return

        jahr = zeilen[0].split(";")[2]
        vorschlag = f"trainingstermine{jahr}.txt"

        hinweis = ""
        if kodierung not in ("utf-8", "utf-8-sig"):
            hinweis = (f"Die Datei ist {kodierung}-kodiert (Excel-Standard) und wird "
                       "nach UTF-8 umgewandelt, damit Umlaute stimmen.\n\n")
        if uebersprungen:
            hinweis += (f"{len(uebersprungen)} Zeile(n) ohne Trainingszeit werden "
                        "übersprungen (z. B. Ferien oder Bemerkungen).\n\n")

        werte = B.frage_formular(
            self.rahmen, self.s, "Trainingstermine importieren", [
                {"schluessel": "ziel", "beschriftung": "Zieldatei",
                 "hinweis": "liegt in data/"},
                {"schluessel": "js", "beschriftung": "js/aktuelles.js anpassen",
                 "art": "auswahl", "optionen": ["ja", "nein"],
                 "hinweis": "setzt den Verweis auf die neue Datei"},
            ],
            {"ziel": vorschlag, "js": "ja"},
            einleitung=f"{hinweis}{len(zeilen)} Termine erkannt.")
        if not werte:
            return

        ziel = os.path.join(tti.DATA_DIR, werte["ziel"])
        if os.path.isfile(ziel) and not messagebox.askyesno(
                "Datei ersetzen?", f"data/{werte['ziel']} gibt es bereits.\n\nErsetzen?"):
            return

        h.schreibe_zeilen(ziel, zeilen)

        nachricht = f"{len(zeilen)} Termine in data/{werte['ziel']} geschrieben."
        if werte["js"] == "ja":
            geaendert = tti.js_referenz_anpassen(werte["ziel"])
            nachricht += ("\n\njs/aktuelles.js zeigt jetzt auf diese Datei.\n"
                          "WICHTIG: Danach das technische Update laufen lassen, "
                          "sonst wirkt die JS-Änderung nicht."
                          if geaendert else
                          "\n\njs/aktuelles.js war bereits richtig eingestellt.")

        messagebox.showinfo("Importiert", nachricht)
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Assistenten
# ------------------------------------------------------------------

class AssistentSeite(Seite):
    """Basis fuer Schritt-fuer-Schritt-Assistenten.

    SCHRITTE: Liste von (Titel, Erklaerung, Seitenname oder None). Ein
    Seitenname macht aus dem Schritt einen Sprung auf die passende Seite -
    die Arbeit passiert dort, nicht in einem eigenen Fenster.
    """

    SCHRITTE = []

    def baue(self):
        self.knopf("Von vorne", self.zuruecksetzen)
        self.erledigt = set()

    def aktualisieren(self):
        self.leeren()
        offen = len(self.SCHRITTE) - len(self.erledigt)
        B.abschnitt(self.inhalt, self.s, "Schritte",
                    f"{len(self.erledigt)} von {len(self.SCHRITTE)} erledigt")

        for nummer, (titel, erklaerung, seite) in enumerate(self.SCHRITTE):
            fertig = nummer in self.erledigt
            stufe = 2 if fertig else (1 if nummer == min(
                (n for n in range(len(self.SCHRITTE)) if n not in self.erledigt),
                default=-1) else uebersicht.INFO)

            rahmen = B.karte(self.inhalt, self.s, stufe,
                             f"{nummer + 1}. {titel}" + ("   ✓" if fertig else ""),
                             erklaerung)
            leiste = tk.Frame(rahmen, bg=B.FARBEN["karte"])
            leiste.pack(side="right", padx=12)

            if not fertig:
                if seite:
                    B.knopf(leiste, "Öffnen", lambda n=nummer, s=seite: self._springe(n, s),
                            self.s, "neben", fg=B.FARBEN["blau"], padx=12,
                            pady=2).pack(side="left", padx=(0, 6))
                B.knopf(leiste, "Erledigt", lambda n=nummer: self._abhaken(n),
                        self.s, "neben", padx=12, pady=2).pack(side="left")
            else:
                B.knopf(leiste, "Nochmal", lambda n=nummer: self._aufheben(n),
                        self.s, "neben", padx=12, pady=2).pack(side="left")

        if offen == 0:
            B.karte(self.inhalt, self.s, 2, "Alle Schritte erledigt.",
                    "Veröffentlicht wird über die Leiste unten — dort steht auch, "
                    "was tatsächlich rausgeht.")

    def _springe(self, nummer, seite):
        self.erledigt.add(nummer)     # als erledigt merken, Rueckkehr zeigt den Haken
        self.app.zeige_seite(seite)

    def _abhaken(self, nummer):
        self.erledigt.add(nummer)
        self.aktualisieren()

    def _aufheben(self, nummer):
        self.erledigt.discard(nummer)
        self.aktualisieren()

    def zuruecksetzen(self):
        self.erledigt.clear()
        self.aktualisieren()


class RennwochenendeSeite(AssistentSeite):
    titel = "Nach dem Rennen"
    untertitel = ("Die vier Schritte, die nach jedem Rennen anfallen. Jeder Knopf "
                  "führt direkt auf die passende Seite.")

    SCHRITTE = [
        ("Ergebnisse in die Statistik",
         "Top-Platzierungen der Fahrerinnen und Fahrer eintragen.", "statistiken"),
        ("News-Karte auf „Aktuelles“",
         "Kurzer Bericht, den Besucher auf der Aktuelles-Seite sehen.", "news"),
        ("Bilder vom Rennen",
         "Fotos vorher in media/bilder/ ablegen — die WebP-Fassungen entstehen hier.",
         "bilder"),
        ("Ergebnisliste ins Jahresarchiv",
         "Nur nötig, wenn es eine PDF zum Rennen oder zur Gesamtwertung gibt.",
         "archiv"),
    ]

    def baue(self):
        super().baue()
        self.rennen = tk.Label(self.fest, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                               font=self.s.klein, anchor="w", justify="left")
        self.rennen.pack(fill="x", pady=(0, 6))

    def aktualisieren(self):
        self.rennen.configure(text=self._letztes_rennen())
        super().aktualisieren()

    @staticmethod
    def _letztes_rennen():
        heute = date.today()
        frueheste = heute - timedelta(days=35)
        gefunden = []
        for name, sportart in (("timer.txt", "Kart"), ("timer_trial.txt", "Trial")):
            for zeile in h.lies_zeilen(os.path.join(ROOT, "data", name)):
                wann = uebersicht.termin_datum(zeile)
                if wann and frueheste <= wann <= heute:
                    gefunden.append((wann, sportart, zeile))
        if not gefunden:
            return "In den letzten fünf Wochen war laut Terminliste kein Rennen."
        wann, sportart, _ = max(gefunden)
        return f"Letztes Rennen: {sportart} am {wann.strftime('%d.%m.%Y')}"


class SaisonwechselSeite(AssistentSeite):
    titel = "Saisonwechsel"
    untertitel = ("Alles, was zum Jahreswechsel ansteht — der Reihe nach. "
                  "Jeder Schritt lässt sich überspringen.")

    SCHRITTE = [
        ("Abgeschlossene Saison ins Archiv",
         "Saison anlegen und die Wertungs-PDF eintragen.", "archiv"),
        ("Vereinsmeister und Wanderpokal-Sieger",
         "Neue Zeile in der Jugend- bzw. Erwachsenen-Tabelle.", "statistiken"),
        ("Trainingstermine der neuen Saison",
         "Excel-Export umwandeln und den Verweis in js/aktuelles.js anpassen.",
         "trainingstermine"),
        ("Renntermine der neuen Saison",
         "Kart- und Trial-Termine für Countdown und Kalender-Download.", "termine"),
        ("Diagramm der abgeschlossenen Saison einfrieren",
         "Endwerte eintragen und die Überschrift auf die abgelaufene Saison setzen. "
         "Läuft im Terminal — die Diagramme sind der einzige Teil ohne Fensterseite.",
         None),
        ("Technisches Update",
         "Statistik-Diagramm, Bilder, Copyright-Jahr und die Bundles neu bauen.",
         "technik"),
    ]
