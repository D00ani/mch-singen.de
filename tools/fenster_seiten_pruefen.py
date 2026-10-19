# -*- coding: utf-8 -*-
"""
Fensterseite "Webseite prüfen" - prüfen UND gleich beheben.

Jeder Fund steht als eigene Zeile da, rechts die passenden Knöpfe:
  Tote Verweise         Pfad ändern (mit Vorschlägen) · Datei hinlegen · Stelle öffnen
  Groß-/Kleinschreibung Korrigieren (einzeln oder alle)
  Build fehlt           Jetzt bauen
  Angekündigte PDFs     PDF hinlegen · Pfad ändern · Austragen
  Externe Links         Adresse ändern · Im Browser testen
  alt-Texte             alt-Text eintragen
  Beschreibungen        Beschreibung bearbeiten
  Suchindex             In Suche aufnehmen · Eintrag entfernen
  Schreibweisen         Vereinheitlichen
Hinweise lassen sich außerdem ausblenden (tools/pruefe_ausnahmen.json),
Fehler bewusst nicht.

Die Logik steht in tools/pruefe_seite.py (finden) und
tools/pruef_reparatur.py (beheben). Jede Änderung legt eine Sicherung an -
"Rückgängig" in der Seitenleiste holt den alten Stand zurück.

Wird nicht direkt ausgeführt, siehe tools/pflege_fenster.py.
"""
import os
import re
import sys
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fenster_bausteine as B
import pflege_hilfen as h
import pruef_reparatur as R
import pruefe_seite as p
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT

# So viele Zeilen je Gruppe - der Rest erscheint nach dem Beheben
MAX_ZEILEN = 25


# ------------------------------------------------------------------
# Dialog: neuen Pfad wählen
# ------------------------------------------------------------------

class PfadDialog(tk.Toplevel):
    """Neues Ziel für einen Verweis wählen.

    Oben Vorschläge aus dem Projekt (Doppelklick übernimmt), darunter das
    Eingabefeld mit Live-Kontrolle, ob die Datei existiert. "Datei wählen"
    öffnet den Explorer; liegt die Datei außerhalb der Webseite, wird sie
    auf Wunsch hineinkopiert.

    basis: Seite, von der aus der Pfad im Feld gilt - oder None, dann gilt
    er ab dem Hauptordner (so stehen die Pfade in data/timer.txt).
    Nach wait_window() steht in .ergebnis der absolute Pfad oder None.
    """

    def __init__(self, eltern, schriften, titel, erklaerung, ziel, basis=None):
        super().__init__(eltern)
        self.s = schriften
        self.ziel = ziel
        self.basis = basis
        self.ergebnis = None

        self.title(titel)
        self.configure(bg=B.FARBEN["grund"])
        self.transient(eltern)
        self.resizable(False, False)

        kopf = tk.Frame(self, bg=B.FARBEN["tief"])
        kopf.pack(fill="x")
        tk.Label(kopf, text=titel, bg=B.FARBEN["tief"], fg=B.FARBEN["weiss"],
                 font=schriften.kopf).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(kopf, text=erklaerung, bg=B.FARBEN["tief"], fg=B.FARBEN["rail_text"],
                 font=schriften.klein, wraplength=600, justify="left").pack(
                     anchor="w", padx=20, pady=(0, 14))

        koerper = tk.Frame(self, bg=B.FARBEN["grund"])
        koerper.pack(fill="both", expand=True, padx=20, pady=16)

        self.vorschlaege = R.vorschlaege(ziel)
        tk.Label(koerper, text="Vorhandene Dateien, die gemeint sein könnten (Doppelklick übernimmt):"
                 if self.vorschlaege else "Keine ähnlich heißende Datei im Projekt gefunden.",
                 bg=B.FARBEN["grund"], fg=B.FARBEN["text"], font=schriften.text,
                 anchor="w").pack(anchor="w")
        if self.vorschlaege:
            self.liste = tk.Listbox(koerper, height=min(len(self.vorschlaege), 7), width=78,
                                    font=schriften.daten, relief="solid", bd=1,
                                    activestyle="none", selectbackground=B.FARBEN["blau"])
            for pfad in self.vorschlaege:
                self.liste.insert("end", R.anzeige(pfad))
            self.liste.pack(fill="x", pady=(4, 12))
            self.liste.bind("<<ListboxSelect>>", self._aus_liste)
            self.liste.bind("<Double-Button-1>", lambda _: self._uebernehmen())

        tk.Label(koerper, text="Neuer Pfad" + (" (wie er in der Seite steht)" if basis
                                               else " (ab Hauptordner)") + ":",
                 bg=B.FARBEN["grund"], fg=B.FARBEN["text"], font=schriften.text,
                 anchor="w").pack(anchor="w")
        zeile = tk.Frame(koerper, bg=B.FARBEN["grund"])
        zeile.pack(fill="x", pady=(4, 2))
        self.eingabe = tk.Entry(zeile, font=schriften.daten, width=64, relief="solid", bd=1)
        self.eingabe.pack(side="left", fill="x", expand=True, ipady=3)
        B.knopf(zeile, "Datei wählen …", self._waehlen, schriften, padx=10, pady=2).pack(
            side="left", padx=(8, 0))
        self.status = tk.Label(koerper, text="", bg=B.FARBEN["grund"], font=schriften.klein,
                               anchor="w")
        self.status.pack(anchor="w", pady=(2, 0))

        fuss = tk.Frame(self, bg=B.FARBEN["erhoben"],
                        highlightbackground=B.FARBEN["linie"], highlightthickness=1)
        fuss.pack(fill="x", side="bottom")
        B.knopf(fuss, "Übernehmen", self._uebernehmen, schriften, "haupt",
                padx=18, pady=7).pack(side="right", padx=(6, 18), pady=12)
        B.knopf(fuss, "Abbrechen", self.destroy, schriften).pack(side="right", pady=12)

        start = self.vorschlaege[0] if self.vorschlaege else ziel
        self._setze(start)
        if self.vorschlaege:
            self.liste.selection_set(0)
        self.eingabe.bind("<KeyRelease>", lambda _: self._pruefen())
        self.eingabe.bind("<Return>", lambda _: self._uebernehmen())
        self.bind("<Escape>", lambda _: self.destroy())

        self.update_idletasks()
        x = eltern.winfo_rootx() + (eltern.winfo_width() - self.winfo_width()) // 2
        y = eltern.winfo_rooty() + (eltern.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.eingabe.focus_set()

    # Pfad im Feld <-> absoluter Pfad
    def _text_fuer(self, pfad):
        if self.basis:
            return R.web_pfad(self.basis, pfad)
        return R.timer_pfad(pfad)

    def _absolut(self):
        text = self.eingabe.get().strip().replace("\\", "/")
        if not text:
            return None
        if self.basis and not text.startswith("/"):
            return os.path.normpath(os.path.join(os.path.dirname(self.basis), text))
        return os.path.normpath(os.path.join(ROOT, text.lstrip("/")))

    def _setze(self, pfad):
        self.eingabe.delete(0, "end")
        self.eingabe.insert(0, self._text_fuer(pfad))
        self._pruefen()

    def _pruefen(self):
        pfad = self._absolut()
        if not pfad:
            self.status.configure(text="", fg=B.FARBEN["gedimmt"])
        elif not R.im_projekt(pfad):
            self.status.configure(text="✗  Zeigt aus der Webseite heraus", fg=B.FARBEN["faellig"])
        elif os.path.isfile(pfad):
            passt, richtig = p.exakt_vorhanden(pfad)
            if passt:
                self.status.configure(text=f"✓  Datei vorhanden: {R.anzeige(pfad)}",
                                      fg=B.FARBEN["gut"])
            else:
                self.status.configure(text=f"⚠  Schreibweise stimmt nicht - heißt wirklich „{richtig}“",
                                      fg=B.FARBEN["hinweis"])
        else:
            self.status.configure(text="✗  Diese Datei gibt es nicht", fg=B.FARBEN["faellig"])

    def _aus_liste(self, _=None):
        auswahl = self.liste.curselection()
        if auswahl:
            self._setze(self.vorschlaege[auswahl[0]])

    def _waehlen(self):
        start = os.path.dirname(self.ziel) if os.path.isdir(os.path.dirname(self.ziel)) \
            else os.path.join(ROOT, "media")
        quelle = filedialog.askopenfilename(parent=self, title="Datei auswählen", initialdir=start)
        if not quelle:
            return
        quelle = os.path.normpath(quelle)
        if not R.im_projekt(quelle):
            zielordner = os.path.dirname(self.ziel)
            if not messagebox.askyesno(
                    "Datei liegt außerhalb der Webseite", parent=self,
                    message=f"{os.path.basename(quelle)} liegt nicht im Webseiten-Ordner.\n\n"
                            f"In den Ordner {R.anzeige(zielordner)}/ kopieren und dorthin verlinken?"):
                return
            try:
                quelle = R.ins_projekt_kopieren(quelle, zielordner)
            except OSError as fehler:
                messagebox.showerror("Kopieren fehlgeschlagen", str(fehler), parent=self)
                return
        self._setze(quelle)

    def _uebernehmen(self):
        pfad = self._absolut()
        if not pfad or not R.im_projekt(pfad):
            messagebox.showerror("Pfad prüfen", "Bitte einen Pfad innerhalb der Webseite angeben.",
                                 parent=self)
            return
        if not os.path.isfile(pfad) and not messagebox.askyesno(
                "Datei fehlt", parent=self,
                message="Diese Datei gibt es (noch) nicht - der Link bliebe tot.\n\n"
                        "Trotzdem so eintragen?"):
            return
        self.ergebnis = pfad
        self.destroy()


def frage_pfad(eltern, schriften, titel, erklaerung, ziel, basis=None):
    fenster = PfadDialog(eltern, schriften, titel, erklaerung, ziel, basis)
    eltern.wait_window(fenster)
    return fenster.ergebnis


# ------------------------------------------------------------------
# Die Seite
# ------------------------------------------------------------------

class PruefenSeite(Seite):
    titel = "Webseite prüfen"
    untertitel = ("Findet, was auf GitHub Pages kaputt wäre oder Besucher und Google stört - "
                  "und behebt es gleich hier. Jede Änderung lässt sich mit „Rückgängig“ zurücknehmen.")

    def baue(self):
        self.extern = tk.BooleanVar(value=False)
        self.knopf("Prüfung starten", self.starten, "haupt")
        tk.Checkbutton(self.aktionen, text="Internet-Links",
                       variable=self.extern, bg=B.FARBEN["grund"],
                       fg=B.FARBEN["text"], font=self.s.klein,
                       activebackground=B.FARBEN["grund"], selectcolor=B.FARBEN["karte"],
                       cursor="hand2").pack(side="right", padx=(0, 10))
        self.meldung = tk.Label(self.fest, text="", bg=B.FARBEN["grund"], fg=B.FARBEN["gut"],
                                font=self.s.fett, anchor="w", justify="left", wraplength=760)
        self.meldung.pack(fill="x")
        self.laeuft = False
        self.daten = None

    def aktualisieren(self):
        if not self.inhalt.winfo_children():
            self.leeren()
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Noch nicht geprüft.",
                    "Oben rechts auf „Prüfung starten“ - dauert ohne Internet-Links "
                    "nur ein paar Sekunden.")

    # -------------------------------------------------- Prüfen
    def starten(self):
        if self.laeuft:
            return
        self.laeuft = True
        self.leeren()
        B.karte(self.inhalt, self.s, uebersicht.INFO, "Prüfe …",
                "Bei eingeschalteter Internet-Prüfung dauert das ein paar Sekunden.")
        extern = self.extern.get()

        def arbeit():
            tote, schreibweise = p.befunde_verweise()
            return {
                "tote": tote,
                "schreibweise": schreibweise,
                "build": p.pruefe_build_aktuell(),
                "dritt": p.pruefe_drittanbieter(),
                "extern": p.befunde_externe_links(fortschritt=False) if extern else [],
                "ids": p.befunde_doppelte_ids(),
                "suche": p.befunde_suchindex(),
                "last": p.befunde_ladebudget(),
                "woerter": p.befunde_schreibweisen(),
                "alt": p.befunde_alt_texte(),
                "meta": p.befunde_meta(),
                "pdfs": p.befunde_pdfs(),
                "symbole": p.pruefe_symbole(),
            }

        B.im_hintergrund(self.rahmen, arbeit, self._fertig)

    def _fertig(self, daten):
        self.laeuft = False
        self.daten = daten
        self._zeigen()

    # -------------------------------------------------- Anzeige
    def _zeigen(self):
        self.leeren()
        d = self.daten
        menge = p.ausnahmen()

        def offen(liste):
            return p.ohne_ausgeblendete(liste, menge)

        gruppen = []   # (stufe, name, zeilen, gruppenknopf)

        # ---- Fehler
        tote = d["tote"]
        if tote:
            zeilen = []
            for ziel, stellen in R.nach_ziel(tote).items():
                seiten = ", ".join(sorted({b["anzeige"].replace(os.sep, "/") for b in stellen}))
                zeilen.append((R.anzeige(ziel), f"fehlt - verlinkt in {seiten}", [
                    ("Pfad ändern …", lambda z=ziel, s=stellen: self._pfad_aendern(z, s), "haupt"),
                    ("Datei hinlegen …", lambda z=ziel: self._hinlegen(z), "neben"),
                    ("Stelle öffnen", lambda s=stellen: R.stelle_oeffnen(s[0]["datei"], s[0]["verweis"]),
                     "neben"),
                ], None))
            gruppen.append((0, "Tote Verweise (Link führt ins Leere)", zeilen, None))

        if d["schreibweise"]:
            zeilen = []
            for ziel, stellen in R.nach_ziel(d["schreibweise"]).items():
                b = stellen[0]
                richtig = R.richtiger_pfad(b["datei"], b["verweis"])
                zeilen.append((f"{b['verweis']}  →  {richtig}",
                               "in " + ", ".join(sorted({s["anzeige"].replace(os.sep, "/") for s in stellen})),
                               [("Korrigieren", lambda s=stellen: self._schreibweise(s), "haupt")], None))
            gruppen.append((0, "Falsche Groß-/Kleinschreibung (bricht erst auf dem Server)", zeilen,
                            ("Alle korrigieren", lambda: self._schreibweise(d["schreibweise"]))))

        if d["build"]:
            zeilen = [(text, None, [], None) for text in d["build"]]
            gruppen.append((0, "Build-Schritt fehlt (Änderung ist online unsichtbar)", zeilen,
                            ("Jetzt bauen", self._bauen)))

        if d["dritt"]:
            zeilen = [(text, None, [("Klaro-Datei öffnen",
                                     lambda: R.stelle_oeffnen(os.path.join(ROOT, "js", "klaro-config.js")),
                                     "neben")], text) for text in offen(d["dritt"])]
            gruppen.append((0, "Externe Dienste ohne Klaro-Eintrag (DSGVO)", zeilen, None))

        # ---- Hinweise
        zeilen = []
        for b in offen(d["extern"]):
            seiten = ", ".join(R.anzeige(x) for x in b["dateien"])
            zeilen.append((b["adresse"], f"{b['grund']} - verlinkt auf {seiten}", [
                ("Adresse ändern …", lambda b=b: self._adresse(b), "haupt"),
                ("Im Browser testen", lambda b=b: webbrowser.open(b["adresse"]), "neben"),
            ], b["text"]))
        gruppen.append((1, "Externe Links ohne Antwort", zeilen, None))

        # Dieselbe PDF kann bei mehreren Terminen stehen - eine Zeile je PDF
        zeilen = []
        je_pdf = {}
        for b in offen(d["pdfs"]):
            je_pdf.setdefault(b["pdf"], []).append(b)
        for pdf, termine in je_pdf.items():
            wann = ", ".join(t["text"].split("(", 1)[1].split(")", 1)[0] for t in termine)
            b = termine[0]
            zeilen.append((pdf, f"angekündigt in {b['name']} für {wann} - die Datei fehlt noch", [
                ("PDF hinlegen …", lambda b=b: self._pdf_hinlegen(b), "haupt"),
                ("Pfad ändern …", lambda b=b: self._pdf_pfad(b), "neben"),
                ("Austragen", lambda b=b: self._pdf_austragen(b), "neben"),
            ], None))
            # Ausblenden gilt für alle Termine dieser PDF zugleich
            zeilen[-1] = zeilen[-1][:3] + ([t["text"] for t in termine],)
        gruppen.append((1, "Angekündigte PDFs noch nicht hochgeladen", zeilen, None))

        zeilen = []
        for b in offen(d["alt"]):
            zeilen.append((f"{R.anzeige(b['datei'])}: {b['src'] or 'Bild'}", "Bild ohne alt-Text", [
                ("alt-Text eintragen …", lambda b=b: self._alt(b), "haupt"),
                ("Stelle öffnen", lambda b=b: R.stelle_oeffnen(b["datei"], b["tag"]), "neben"),
            ], b["text"]))
        gruppen.append((1, "Bilder ohne alt-Text", zeilen, None))

        zeilen = []
        for b in offen(d["meta"]):
            if b["art"].startswith("beschreibung"):
                knoepfe = [("Beschreibung bearbeiten …", lambda b=b: self._beschreibung(b), "haupt")]
            else:
                such = {"titel": "<title", "og_bild": "og:", "canonical": "<head"}.get(b["art"])
                knoepfe = [("Stelle öffnen", lambda b=b, s=such: R.stelle_oeffnen(b["datei"], s), "neben")]
            zeilen.append((b["text"], None, knoepfe, b["text"]))
        gruppen.append((1, "Titel, Beschreibung, Vorschaubild", zeilen, None))

        zeilen = []
        for b in offen(d["suche"]):
            if b["art"] == "fehlt":
                knoepfe = [("In Suche aufnehmen …", lambda b=b: self._suche_aufnehmen(b), "haupt")]
            elif b["art"] == "tot":
                knoepfe = [("Eintrag entfernen", lambda b=b: self._suche_entfernen(b), "warnung")]
            else:
                knoepfe = [("Stelle öffnen", lambda b=b: R.stelle_oeffnen(b["datei"], b["suche"]), "neben")]
            zeilen.append((b["text"], None, knoepfe, b["text"]))
        gruppen.append((1, "Suche der Webseite", zeilen, None))

        zeilen = []
        for b in offen(d["woerter"]):
            zeilen.append((b["text"], None, [
                ("Vereinheitlichen", lambda b=b: self._woerter(b), "haupt")], b["text"]))
        gruppen.append((1, "Uneinheitliche Schreibweisen", zeilen, None))

        zeilen = []
        for b in offen(d["ids"]):
            zeilen.append((b["text"], "JavaScript findet nur das erste Element mit dieser id", [
                ("Stelle öffnen", lambda b=b: R.stelle_oeffnen(b["datei"], b["suche"]), "neben")],
                b["text"]))
        gruppen.append((1, "Dieselbe id mehrfach auf einer Seite", zeilen, None))

        zeilen = []
        for b in offen(d["last"]):
            zeilen.append((b["text"], None, [
                ("Medien aufräumen", lambda: self.app.zeige_seite("medien"), "neben")], b["text"]))
        gruppen.append((1, f"Seiten über {p.LADEBUDGET_KB // 1024} MB Ladegewicht", zeilen, None))

        zeilen = [(text, "python tools/icons_bauen.py neu laufen lassen", [], text)
                  for text in offen(d["symbole"])]
        gruppen.append((1, "Symbole fehlen in der Schrift", zeilen, None))

        gruppen = [g for g in gruppen if g[2]]
        ausgeblendet = self._ausgeblendet_zahl(menge)

        if not gruppen:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Alles in Ordnung - keine Probleme gefunden.",
                    "Weder tote Verweise noch Schreibweise, Build, alt-Texte oder Meta-Angaben.")
        else:
            fehler = sum(1 for g in gruppen if g[0] == 0)
            B.abschnitt(self.inhalt, self.s, "Ergebnis",
                        f"{fehler} Fehlergruppe(n), {len(gruppen) - fehler} Hinweisgruppe(n)")
            for stufe, name, zeilen, gruppenknopf in gruppen:
                self._gruppe(stufe, name, zeilen, gruppenknopf)

        if ausgeblendet:
            B.karte(self.inhalt, self.s, 2,
                    f"{ausgeblendet} bekannte(r) Hinweis(e) ausgeblendet",
                    "Erscheinen weder hier noch bei der Prüfung vor dem Veröffentlichen.",
                    "Wieder einblenden", self._einblenden)

    def _ausgeblendet_zahl(self, menge):
        alle = set()
        d = self.daten
        for liste in (d["dritt"], d["symbole"]):
            alle.update(liste)
        for schluessel in ("extern", "pdfs", "alt", "meta", "suche", "woerter", "ids", "last"):
            alle.update(b["text"] for b in d[schluessel])
        return len(alle & menge)

    def _gruppe(self, stufe, name, zeilen, gruppenknopf):
        kopf = tk.Frame(self.inhalt, bg=B.FARBEN["grund"])
        kopf.pack(fill="x", pady=(10, 6))
        farbe = B.STUFEN_FARBE.get(stufe, B.FARBEN["gedimmt"])
        tk.Label(kopf, text=("FEHLER  ·  " if stufe == 0 else "HINWEIS  ·  ") + name.upper(),
                 bg=B.FARBEN["grund"], fg=farbe, font=self.s.kopf).pack(side="left")
        tk.Label(kopf, text=str(len(zeilen)), bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein).pack(side="left", padx=8)
        if gruppenknopf:
            text, befehl = gruppenknopf
            B.knopf(kopf, text, befehl, self.s, "haupt", padx=10, pady=2).pack(side="right")

        for titel, unter, knoepfe, ausblend_text in zeilen[:MAX_ZEILEN]:
            if ausblend_text and stufe != 0:
                knoepfe = list(knoepfe) + [("Ausblenden", lambda t=ausblend_text: self._ausblenden(t),
                                            "neben")]
            self._zeile(stufe, titel, unter, knoepfe)
        if len(zeilen) > MAX_ZEILEN:
            tk.Label(self.inhalt, text=f"… und {len(zeilen) - MAX_ZEILEN} weitere - erscheinen nach dem "
                                       "Beheben der obigen.", bg=B.FARBEN["grund"],
                     fg=B.FARBEN["gedimmt"], font=self.s.klein).pack(anchor="w", pady=(0, 6))

    def _zeile(self, stufe, titel, unter, knoepfe):
        """Ein Fund: oben Pfad/Text, darunter die Knöpfe. Knöpfe UNTER dem
        Text, weil die Inhaltsfläche je nach Fenstergröße nur 680 bis 840
        Pixel breit ist - drei Knöpfe daneben hätten den Text abgeschnitten."""
        rahmen = tk.Frame(self.inhalt, bg=B.FARBEN["karte"],
                          highlightbackground=B.FARBEN["linie"], highlightthickness=1)
        rahmen.pack(fill="x", pady=(0, 6))
        tk.Frame(rahmen, bg=B.STUFEN_FARBE.get(stufe, B.FARBEN["gedimmt"]), width=4).pack(
            side="left", fill="y")

        inhalt = tk.Frame(rahmen, bg=B.FARBEN["karte"])
        inhalt.pack(side="left", fill="x", expand=True, padx=12, pady=(7, 8))
        tk.Label(inhalt, text=titel.replace("\\", "/"), bg=B.FARBEN["karte"], fg=B.FARBEN["text"],
                 font=self.s.daten, anchor="w", justify="left", wraplength=640).pack(anchor="w")
        if unter:
            tk.Label(inhalt, text=unter.replace("\\", "/"), bg=B.FARBEN["karte"],
                     fg=B.FARBEN["gedimmt"], font=self.s.klein, anchor="w", justify="left",
                     wraplength=640).pack(anchor="w")

        if knoepfe:
            leiste = tk.Frame(inhalt, bg=B.FARBEN["karte"])
            leiste.pack(fill="x", pady=(6, 0))
            for text, befehl, art in knoepfe:
                k = B.knopf(leiste, text, lambda b=befehl: self._sicher(b), self.s, art,
                            padx=10, pady=1)
                if text == "Ausblenden":
                    k.configure(fg=B.FARBEN["gedimmt"], relief="flat", bd=0)
                    k.pack(side="right")
                else:
                    k.pack(side="left", padx=(0, 6))

    # -------------------------------------------------- Hilfen
    def _sicher(self, befehl):
        """Jeder Knopf: Fehler als Meldung statt als stiller Absturz."""
        try:
            befehl()
        except FileExistsError as fehler:
            messagebox.showerror("Gibt es schon", str(fehler))
        except (OSError, ValueError) as fehler:
            messagebox.showerror("Hat nicht geklappt", str(fehler))

    def _geschafft(self, text):
        self.meldung.configure(text=f"✓  {text}", fg=B.FARBEN["gut"])
        self.app.fuss_auffrischen()
        self.starten()

    def _ausblenden(self, text):
        """text: Textzeile des Hinweises - oder eine Liste davon (z. B. alle
        Termine, die dieselbe PDF ankündigen)."""
        menge = p.ausnahmen()
        menge.update(text if isinstance(text, list) else [text])
        p.ausnahmen_speichern(menge)
        self.meldung.configure(text="Hinweis ausgeblendet - unten „Wieder einblenden“ holt ihn zurück.",
                               fg=B.FARBEN["gedimmt"])
        self._zeigen()

    def _einblenden(self):
        if not messagebox.askyesno("Wieder einblenden",
                                   "Alle ausgeblendeten Hinweise wieder anzeigen?"):
            return
        p.ausnahmen_speichern(set())
        self.meldung.configure(text="Alle Hinweise werden wieder angezeigt.", fg=B.FARBEN["gedimmt"])
        self._zeigen()

    # -------------------------------------------------- Aktionen: Verweise
    def _pfad_aendern(self, ziel, stellen):
        seiten = sorted({b["anzeige"].replace(os.sep, "/") for b in stellen})
        neu = frage_pfad(
            self.rahmen, self.s, "Pfad ändern",
            f"Die Seite{'n' if len(seiten) > 1 else ''} {', '.join(seiten)} "
            f"verlink{'en' if len(seiten) > 1 else 't'} auf {R.anzeige(ziel)} - "
            "die Datei gibt es nicht. Wähle, worauf der Link stattdessen zeigen soll. "
            "Jede Seite bekommt automatisch den passenden relativen Pfad.",
            ziel, basis=stellen[0]["datei"])
        if not neu:
            return
        bericht = R.ziel_umbiegen(stellen, neu)
        teile = [f"{seite}: {neu_pfad}" for seite, _, neu_pfad, _ in bericht]
        self._geschafft("Link geändert - " + "; ".join(teile))

    def _hinlegen(self, ziel):
        endung = os.path.splitext(ziel)[1].lower()
        quelle = filedialog.askopenfilename(
            title=f"Datei für {os.path.basename(ziel)} auswählen",
            filetypes=[(f"{endung[1:].upper()}-Dateien", f"*{endung}"), ("Alle Dateien", "*.*")])
        if not quelle:
            return
        if os.path.splitext(quelle)[1].lower() != endung and not messagebox.askyesno(
                "Andere Dateiart",
                f"Erwartet wird eine {endung}-Datei, gewählt ist {os.path.basename(quelle)}.\n\n"
                "Trotzdem unter dem erwarteten Namen ablegen?"):
            return
        R.datei_hinlegen(quelle, ziel)
        self._geschafft(f"Datei abgelegt: {R.anzeige(ziel)} (neue Datei - „Rückgängig“ löscht sie nicht)")

    def _schreibweise(self, stellen):
        bericht = R.schreibweise_korrigieren(stellen)
        self._geschafft(f"{len(bericht)} Pfad(e) korrigiert")

    def _bauen(self):
        self.meldung.configure(text="Baue die minifizierten Dateien …", fg=B.FARBEN["gedimmt"])

        def fertig(ergebnis):
            ok, ausgabe = ergebnis
            if ok:
                self._geschafft("Build fertig - die Änderungen sind jetzt auch online wirksam")
            else:
                messagebox.showerror("Build fehlgeschlagen", ausgabe[-1500:] or "Unbekannter Fehler")

        B.im_hintergrund(self.rahmen, R.bauen, fertig)

    # -------------------------------------------------- Aktionen: PDFs
    def _gleiche_pdfs(self, befund):
        return [b for b in self.daten["pdfs"] if b["pdf"] == befund["pdf"]]

    def _pdf_hinlegen(self, befund):
        quelle = filedialog.askopenfilename(
            title=f"PDF für {os.path.basename(befund['pdf'])} auswählen",
            filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")])
        if not quelle:
            return
        R.datei_hinlegen(quelle, befund["ziel"])
        self._geschafft(f"PDF abgelegt: {befund['pdf']} - der Download-Knopf erscheint jetzt")

    def _pdf_pfad(self, befund):
        neu = frage_pfad(self.rahmen, self.s, "Angekündigtes PDF umbiegen",
                         f"{befund['text']}\n\nWähle die PDF, die stattdessen angekündigt werden soll.",
                         befund["ziel"], basis=None)
        if not neu:
            return
        anzahl = 0
        for datei in sorted({b["datei"] for b in self._gleiche_pdfs(befund)}):
            anzahl += R.timer_pdf_aendern(datei, befund["pdf"], R.timer_pfad(neu))
        self._geschafft(f"{anzahl} Termin(e) zeigen jetzt auf {R.timer_pfad(neu)}")

    def _pdf_austragen(self, befund):
        gleiche = self._gleiche_pdfs(befund)
        if not messagebox.askyesno(
                "PDF austragen",
                f"{befund['pdf']}\n\nBei {len(gleiche)} Termin(en) wird die PDF-Angabe entfernt. "
                "Der Termin bleibt, nur der Knopf „Weitere Informationen“ fällt weg."):
            return
        anzahl = 0
        for datei in sorted({b["datei"] for b in gleiche}):
            anzahl += R.timer_pdf_aendern(datei, befund["pdf"], "")
        self._geschafft(f"PDF-Angabe bei {anzahl} Termin(en) ausgetragen")

    # -------------------------------------------------- Aktionen: Texte
    def _adresse(self, befund):
        werte = B.frage_formular(
            self.rahmen, self.s, "Adresse ändern",
            [{"schluessel": "adresse", "beschriftung": "Neue Adresse",
              "pruefer": h.LINK_VALIDIERER,
              "hinweis": "Wird auf allen Seiten ersetzt, die diesen Link enthalten."}],
            {"adresse": befund["adresse"]},
            einleitung=f"{befund['adresse']} antwortet nicht ({befund['grund']}).")
        if not werte or werte["adresse"] == befund["adresse"]:
            return
        anzahl = R.adresse_ersetzen(befund["dateien"], befund["adresse"], werte["adresse"])
        self._geschafft(f"Adresse {anzahl}x ersetzt")

    def _alt(self, befund):
        werte = B.frage_formular(
            self.rahmen, self.s, "alt-Text eintragen",
            [{"schluessel": "alt", "beschriftung": "Was ist zu sehen?", "pflicht": False,
              "hinweis": "Kurz beschreiben, z. B. „Kart im Pylonen-Slalom“. "
                         "Leer lassen bei reinem Schmuck."}],
            einleitung=f"{R.anzeige(befund['datei'])}: {befund['src'] or 'Bild'}\n"
                       "Den Text lesen Vorleseprogramme vor, und Google versteht damit das Bild.")
        if werte is None:
            return
        R.alt_eintragen(befund["datei"], befund["tag"], werte["alt"])
        self._geschafft(f"alt-Text eingetragen in {R.anzeige(befund['datei'])}")

    def _beschreibung(self, befund):
        dateien = befund.get("dateien") or [befund["datei"]]
        felder = []
        if len(dateien) > 1:
            felder.append({"schluessel": "seite", "beschriftung": "Für welche Seite?", "art": "auswahl",
                           "optionen": [R.anzeige(d) for d in dateien]})

        def pruefer(text):
            if len(text) < p.BESCHREIBUNG_MIN:
                return f"Zu kurz ({len(text)} Zeichen) - mindestens {p.BESCHREIBUNG_MIN}."
            if len(text) > p.BESCHREIBUNG_MAX:
                return f"Zu lang ({len(text)} Zeichen) - Google schneidet nach {p.BESCHREIBUNG_MAX} ab."
            return None

        felder.append({"schluessel": "text", "beschriftung": "Beschreibung", "art": "mehrzeilig",
                       "pruefer": pruefer,
                       "hinweis": f"{p.BESCHREIBUNG_MIN} bis {p.BESCHREIBUNG_MAX} Zeichen. Das zeigt "
                                  "Google unter dem Link und WhatsApp beim Teilen."})
        werte = B.frage_formular(
            self.rahmen, self.s, "Seitenbeschreibung", felder,
            {"text": R.beschreibung_lesen(dateien[0])},
            einleitung=befund["text"])
        if not werte:
            return
        datei = dateien[0]
        if "seite" in werte:
            datei = next(d for d in dateien if R.anzeige(d) == werte["seite"])
        R.beschreibung_setzen(datei, werte["text"])
        self._geschafft(f"Beschreibung von {R.anzeige(datei)} gespeichert")

    def _woerter(self, befund):
        if not messagebox.askyesno(
                "Schreibweise vereinheitlichen",
                f"{R.anzeige(befund['datei'])}\n\n„{befund['muster']}“ wird {befund['anzahl']}x durch "
                f"„{befund['gewuenscht']}“ ersetzt - nur im sichtbaren Text, nicht in Adressen."):
            return
        anzahl = R.schreibweise_vereinheitlichen(befund["datei"], befund["muster"], befund["gewuenscht"])
        self._geschafft(f"{anzahl}x „{befund['gewuenscht']}“ eingesetzt")

    # -------------------------------------------------- Aktionen: Suche
    def _suche_aufnehmen(self, befund):
        vorgabe = R.suche_vorgaben(befund["datei"])
        werte = B.frage_formular(
            self.rahmen, self.s, "In die Suche aufnehmen",
            [{"schluessel": "titel", "beschriftung": "Titel"},
             {"schluessel": "beschreibung", "beschriftung": "Kurzbeschreibung"},
             {"schluessel": "stichwoerter", "beschriftung": "Suchbegriffe", "pflicht": False,
              "hinweis": "Wörter, unter denen man die Seite finden soll, mit Leerzeichen getrennt."}],
            vorgabe,
            einleitung=f"{befund['name']} wird in js/suche.js eingetragen und ist danach über die "
                       "Suche der Webseite auffindbar. Der Build läuft anschließend automatisch.")
        if not werte:
            return
        R.suche_eintrag_anlegen(befund["datei"], werte["titel"], werte["beschreibung"],
                                werte.get("stichwoerter", ""))
        self._nach_suche(f"{befund['name']} in die Suche aufgenommen")

    def _suche_entfernen(self, befund):
        if not messagebox.askyesno("Eintrag entfernen",
                                   f"Den Suchindex-Eintrag für {befund['name']} entfernen? "
                                   "Die Seite gibt es nicht mehr."):
            return
        R.suche_eintrag_entfernen(befund["url"])
        self._nach_suche(f"Suchindex-Eintrag {befund['name']} entfernt")

    def _nach_suche(self, text):
        self.meldung.configure(text=f"{text} - baue js/suche.min.js …", fg=B.FARBEN["gedimmt"])

        def fertig(ergebnis):
            ok, ausgabe = ergebnis
            if not ok:
                messagebox.showerror("Build fehlgeschlagen", ausgabe[-1500:] or "Unbekannter Fehler")
            self._geschafft(text + (" - Build fertig" if ok else " - Build bitte nachholen"))

        B.im_hintergrund(self.rahmen, R.bauen, fertig)
