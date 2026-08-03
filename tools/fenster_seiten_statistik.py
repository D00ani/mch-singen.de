# -*- coding: utf-8 -*-
"""
Fensterseite fuer die Statistiken-Seite.

Fuenf Bereiche in einer Seite, oben umschaltbar: die drei Tabellen
(Top-Platzierungen, Wanderpokal Jugend und Erwachsen), die Rekord-Kaesten
und die Meilenstein-Zahlen. Die Diagramme entstehen aus der Wertungs-PDF
und werden ueber das technische Update erzeugt, nicht von Hand.

Gelesen und geschrieben wird mit den Funktionen aus statistiken_pflege.py.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import re
import sys
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fenster_bausteine as B
import pflege_hilfen as h
import statistiken_pflege as sp
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT

REKORDE = "Rekord-Kästen"
MEILENSTEINE = "Meilensteine"


class StatistikenSeite(Seite):
    titel = "Statistiken pflegen"
    untertitel = ("Tabellen, Rekord-Kästen und die Zahlen im Kopf der Seite. "
                  "Die Diagramme entstehen automatisch aus der Wertungs-PDF.")

    def baue(self):
        self.knopf_loeschen = self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf_neu = self.knopf("Neuer Eintrag", self.neu, "haupt")

        self.bereich = tk.StringVar(value=sp.TABELLEN[0]["name"])
        wahl = tk.Frame(self.fest, bg=B.FARBEN["grund"])
        wahl.pack(fill="x", pady=(0, 4))
        for name in [t["name"] for t in sp.TABELLEN] + [REKORDE, MEILENSTEINE]:
            tk.Radiobutton(wahl, text=name, value=name, variable=self.bereich,
                           command=self.aktualisieren, bg=B.FARBEN["grund"],
                           fg=B.FARBEN["text"], font=self.s.text, cursor="hand2",
                           activebackground=B.FARBEN["grund"],
                           selectcolor=B.FARBEN["karte"]).pack(side="left", padx=(0, 12))
        self.baum = None
        self.eintraege = []

    def _tabelle_gewaehlt(self):
        return next((t for t in sp.TABELLEN if t["name"] == self.bereich.get()), None)

    # -------------------------------------------------- Anzeige
    def aktualisieren(self):
        self.leeren()
        tabelle = self._tabelle_gewaehlt()

        # Nur Tabellen kennen Anlegen und Loeschen
        zustand = "normal" if tabelle else "disabled"
        farbe = B.FARBEN["blau"] if tabelle else B.FARBEN["matt"]
        self.knopf_neu.configure(state=zustand, bg=farbe)
        self.knopf_loeschen.configure(state=zustand)

        if tabelle:
            self._zeige_tabelle(tabelle)
        elif self.bereich.get() == REKORDE:
            self._zeige_rekorde()
        else:
            self._zeige_meilensteine()

        if self.baum:
            self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

    def _zeige_tabelle(self, tabelle):
        try:
            _, _, _, _, zeilen, _ = sp.tabelle_laden(tabelle)
        except ValueError as fehler:
            B.karte(self.inhalt, self.s, 0, "Tabelle nicht gefunden", str(fehler))
            self.baum = None
            return

        self.eintraege = zeilen
        B.abschnitt(self.inhalt, self.s, tabelle["name"], f"{len(zeilen)} Einträge")

        if not zeilen:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Noch keine Einträge.",
                    "Oben rechts auf „Neuer Eintrag“.")
            self.baum = None
            return

        spalten = tuple(tabelle["spalten"])
        breiten = [110] + [max(110, 620 // max(len(spalten) - 1, 1))] * (len(spalten) - 1)
        self.baum = self.tabelle(self.inhalt, spalten, breiten,
                                 hoehe=min(len(zeilen), 14), zeilenzahl=len(zeilen))
        for nummer, zeile in enumerate(zeilen):
            werte = []
            for wert in zeile:
                klartext, fett = sp.ohne_hervorhebung(wert)
                werte.append(B.lesbar(klartext) + ("  ●" if fett else ""))
            self.baum.insert("", "end", iid=str(nummer), values=tuple(werte))

        if tabelle["hervorhebbar"] is not None:
            tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                     font=self.s.klein, anchor="w",
                     text="●  = fett hervorgehoben").pack(anchor="w", pady=(10, 0))

    def _zeige_rekorde(self):
        html = h.lies_datei(sp.STATISTIKEN_HTML)
        self.eintraege = sp.parse_record_boxes(html)

        B.abschnitt(self.inhalt, self.s, "Rekord-Kästen",
                    f"{len(self.eintraege)} Kästen")

        if not self.eintraege:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Keine Rekord-Kästen gefunden.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Kasten", "Inhalt"), (230, 440),
                                 hoehe=min(len(self.eintraege), 12),
                                 zeilenzahl=len(self.eintraege))
        for nummer, box in enumerate(self.eintraege):
            inhalt = ", ".join(f"{label}: {wert}" for label, wert in box["felder"])
            self.baum.insert("", "end", iid=str(nummer),
                             values=(B.lesbar(box["titel"]), B.lesbar(inhalt)))

    def _zeige_meilensteine(self):
        html = h.lies_datei(sp.STATISTIKEN_HTML)
        self.eintraege = list(sp.MEILENSTEIN_MUSTER.finditer(html))

        B.abschnitt(self.inhalt, self.s, "Meilenstein-Zahlen",
                    "die grossen Zahlen im Kopf der Seite")

        if not self.eintraege:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Keine Meilenstein-Zahlen gefunden.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Zahl", "Beschriftung"), (120, 550),
                                 hoehe=min(len(self.eintraege), 12),
                                 zeilenzahl=len(self.eintraege))
        for nummer, treffer in enumerate(self.eintraege):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(treffer.group(2) + self._suffix(treffer),
                                     B.lesbar(re.sub(r"<[^>]+>", " ", treffer.group(5)).strip())))

    @staticmethod
    def _suffix(treffer):
        gefunden = re.search(r'data-suffix="([^"]*)"', treffer.group(3))
        return gefunden.group(1) if gefunden else ""

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Nichts gewählt",
                                "Bitte zuerst eine Zeile in der Liste anklicken.")
            return None
        return int(self.baum.selection()[0])

    # -------------------------------------------------- Tabellen
    def _tabellen_felder(self, tabelle, zeile=None):
        felder = []
        for position, spalte in enumerate(tabelle["spalten"]):
            wert = ""
            if zeile:
                wert = B.lesbar(sp.ohne_hervorhebung(zeile[position])[0])
            felder.append({"schluessel": spalte, "beschriftung": spalte,
                           "vorgabe": wert})
        if tabelle["hervorhebbar"] is not None:
            spalte = tabelle["spalten"][tabelle["hervorhebbar"]]
            fett = bool(zeile) and sp.ohne_hervorhebung(zeile[tabelle["hervorhebbar"]])[1]
            felder.append({"schluessel": "_fett", "beschriftung": f"„{spalte}“ fett",
                           "art": "auswahl", "optionen": ["nein", "ja"],
                           "vorgabe": "ja" if fett else "nein"})
        return felder

    def _werte_zu_zeile(self, tabelle, werte):
        zeile = [B.fuer_html(werte[spalte]) for spalte in tabelle["spalten"]]
        if tabelle["hervorhebbar"] is not None and werte.get("_fett") == "ja":
            stelle = tabelle["hervorhebbar"]
            zeile[stelle] = f"<strong>{zeile[stelle]}</strong>"
        return zeile

    def _tabelle_schreiben(self, tabelle, zeilen):
        html, start, ende, tbody_inhalt, _, einrueckung = sp.tabelle_laden(tabelle)
        sp.schreibe_tbody(html, start, ende, zeilen, einrueckung, tbody_inhalt)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def neu(self):
        tabelle = self._tabelle_gewaehlt()
        if not tabelle:
            return
        felder = self._tabellen_felder(tabelle)
        werte = B.frage_formular(
            self.rahmen, self.s, f"Neuer Eintrag — {tabelle['name']}",
            [{k: v for k, v in f.items() if k != "vorgabe"} for f in felder],
            {f["schluessel"]: f["vorgabe"] for f in felder},
            einleitung="Wird nach Jahr bzw. Datum einsortiert — die neuesten stehen oben.")
        if not werte:
            return

        zeile = self._werte_zu_zeile(tabelle, werte)
        zeilen = list(self.eintraege)
        stelle = h.einfuege_position([sp.zeilen_schluessel(z) for z in zeilen],
                                     sp.zeilen_schluessel(zeile), absteigend=True)
        zeilen.insert(stelle, zeile)
        self._tabelle_schreiben(tabelle, zeilen)

    # -------------------------------------------------- Bearbeiten
    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        tabelle = self._tabelle_gewaehlt()
        if tabelle:
            self._tabelle_bearbeiten(tabelle, nummer)
        elif self.bereich.get() == REKORDE:
            self._rekord_bearbeiten(nummer)
        else:
            self._meilenstein_bearbeiten(nummer)

    def _tabelle_bearbeiten(self, tabelle, nummer):
        felder = self._tabellen_felder(tabelle, self.eintraege[nummer])
        werte = B.frage_formular(
            self.rahmen, self.s, f"Eintrag bearbeiten — {tabelle['name']}",
            [{k: v for k, v in f.items() if k != "vorgabe"} for f in felder],
            {f["schluessel"]: f["vorgabe"] for f in felder},
            einleitung="Ändert sich das Jahr, wird der Eintrag neu einsortiert.")
        if not werte:
            return

        zeile = self._werte_zu_zeile(tabelle, werte)
        zeilen = list(self.eintraege)
        del zeilen[nummer]
        stelle = h.einfuege_position([sp.zeilen_schluessel(z) for z in zeilen],
                                     sp.zeilen_schluessel(zeile), absteigend=True)
        zeilen.insert(stelle, zeile)
        self._tabelle_schreiben(tabelle, zeilen)

    def _rekord_bearbeiten(self, nummer):
        box = self.eintraege[nummer]

        felder = [{"schluessel": "titel", "beschriftung": "Titel"}]
        werte = {"titel": B.lesbar(box["titel"])}
        for lauf, (label, wert) in enumerate(box["felder"]):
            felder += [
                {"schluessel": f"label{lauf}", "beschriftung": f"Feld {lauf + 1} — Name"},
                {"schluessel": f"wert{lauf}", "beschriftung": f"Feld {lauf + 1} — Wert",
                 "pflicht": False},
            ]
            werte[f"label{lauf}"] = B.lesbar(label)
            werte[f"wert{lauf}"] = B.lesbar(wert)

        neu = B.frage_formular(self.rahmen, self.s, "Rekord-Kasten bearbeiten",
                               felder, werte)
        if not neu:
            return

        paare = [(B.fuer_html(neu[f"label{lauf}"]), B.fuer_html(neu[f"wert{lauf}"]))
                 for lauf in range(len(box["felder"]))]
        inhalt = "<br>".join(f"<strong>{label}:</strong> {wert}" for label, wert in paare)

        html = h.lies_datei(sp.STATISTIKEN_HTML)
        # Positionen neu bestimmen - die Datei kann sich zwischenzeitlich
        # geaendert haben (zweites Fenster, Terminal-Werkzeug)
        boxen = sp.parse_record_boxes(html)
        if nummer >= len(boxen):
            messagebox.showerror("Nicht mehr vorhanden",
                                 "Der Kasten wurde zwischenzeitlich entfernt.")
            self.aktualisieren()
            return

        m = boxen[nummer]["match"]
        ersatz = (m.group(1) + m.group(2) + B.fuer_html(neu["titel"]) + m.group(4)
                  + inhalt + m.group(6))
        h.schreibe_datei(sp.STATISTIKEN_HTML, html[:m.start()] + ersatz + html[m.end():])
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def _meilenstein_bearbeiten(self, nummer):
        treffer = self.eintraege[nummer]
        text = B.lesbar(re.sub(r"<[^>]+>", " ", treffer.group(5)).strip())

        neu = B.frage_formular(
            self.rahmen, self.s, "Meilenstein-Zahl bearbeiten", [
                {"schluessel": "zahl", "beschriftung": "Zahl",
                 "pruefer": h.ZAHL_VALIDIERER},
                {"schluessel": "suffix", "beschriftung": "Zusatz", "pflicht": False,
                 "hinweis": "steht direkt hinter der Zahl, z. B. „+“ — leer = keiner"},
            ],
            {"zahl": treffer.group(2), "suffix": self._suffix(treffer)},
            einleitung=f"Beschriftung: {text}\n\nDie Zahl zählt beim Aufruf der Seite "
                       "von 0 hoch — das macht die Seite selbst.")
        if not neu:
            return

        html = h.lies_datei(sp.STATISTIKEN_HTML)
        alle = list(sp.MEILENSTEIN_MUSTER.finditer(html))
        if nummer >= len(alle):
            messagebox.showerror("Nicht mehr vorhanden",
                                 "Die Zahl wurde zwischenzeitlich entfernt.")
            self.aktualisieren()
            return

        m = alle[nummer]
        rest = m.group(3)
        if neu["suffix"]:
            if 'data-suffix="' in rest:
                rest = re.sub(r'data-suffix="[^"]*"', f'data-suffix="{neu["suffix"]}"', rest)
            else:
                rest += f' data-suffix="{neu["suffix"]}"'
        else:
            rest = re.sub(r'\s*data-suffix="[^"]*"', "", rest)

        ersatz = m.group(1) + neu["zahl"] + '"' + rest + m.group(4) + m.group(5) + m.group(6)
        h.schreibe_datei(sp.STATISTIKEN_HTML, html[:m.start()] + ersatz + html[m.end():])
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Loeschen
    def loeschen(self):
        tabelle = self._tabelle_gewaehlt()
        if not tabelle:
            return
        nummer = self._gewaehlt()
        if nummer is None:
            return

        if not messagebox.askyesno(
                "Eintrag löschen",
                f"{B.lesbar(sp.beschreibe_zeile(self.eintraege[nummer]))}\n\n"
                "Wirklich löschen?"):
            return

        zeilen = list(self.eintraege)
        del zeilen[nummer]
        self._tabelle_schreiben(tabelle, zeilen)
