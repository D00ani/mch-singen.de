# -*- coding: utf-8 -*-
"""
Fensterseite fuer Vorstand & Trainer auf pages/ueber-uns.html.

Beide Bereiche in einer Baumansicht. Beim Bearbeiten werden gezielt
einzelne Felder ersetzt statt die Karte neu zu bauen - so bleiben
Besonderheiten einzelner Karten erhalten (eigener Bildausschnitt,
Instagram-Verlinkung, Spruch statt E-Mail).

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fenster_bausteine as B
import pflege_hilfen as h
import team_pflege
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT


class TeamSeite(Seite):
    titel = "Vorstand & Trainer"
    untertitel = ("Die Personen-Karten auf „Über uns“. Für ein neues Foto die Datei "
                  "vorher nach media/bilder/ueber-uns/ legen.")

    VORNE = "Ganz vorne"

    def baue(self):
        self.knopf("Entfernen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf("Neue Person", self.neu, "haupt")
        self.baum = None
        self.bereiche = []

    # -------------------------------------------------- Daten
    def _laden(self):
        """[(bereich, [personen])] fuer beide Abschnitte."""
        html = team_pflege.lade_html()
        geladen = []
        for bereich in team_pflege.BEREICHE:
            try:
                personen, grid_start, _ = team_pflege.finde_personen(html, bereich["anker"])
            except ValueError:
                personen, grid_start = [], None
            geladen.append((bereich, personen, grid_start))
        return html, geladen

    def aktualisieren(self):
        self.leeren()
        _, self.bereiche = self._laden()

        gesamt = sum(len(p) for _, p, _ in self.bereiche)
        B.abschnitt(self.inhalt, self.s, "Personen",
                    f"{gesamt} in {len(self.bereiche)} Bereichen")

        huelle = tk.Frame(self.inhalt, bg=B.FARBEN["grund"])
        huelle.pack(fill="both", expand=True)

        self.baum = ttk.Treeview(huelle, columns=("rolle", "kontakt"),
                                 show="tree headings", height=14)
        self.baum.heading("#0", text="BEREICH / NAME")
        self.baum.heading("rolle", text="ROLLE")
        self.baum.heading("kontakt", text="E-MAIL ODER SPRUCH")
        self.baum.column("#0", width=250)
        self.baum.column("rolle", width=230)
        self.baum.column("kontakt", width=250)
        leiste = ttk.Scrollbar(huelle, orient="vertical", command=self.baum.yview)
        self.baum.configure(yscrollcommand=leiste.set)
        leiste.pack(side="right", fill="y")
        self.baum.pack(side="left", fill="both", expand=True)

        for nummer, (bereich, personen, _) in enumerate(self.bereiche):
            knoten = self.baum.insert("", "end", iid=f"b{nummer}",
                                      text=f"{bereich['name']}   ({len(personen)})",
                                      open=True)
            for lauf, person in enumerate(personen):
                rolle = B.lesbar(person["rolle"] or person["kurzrolle"] or "")
                kontakt = B.lesbar(person["email"] or person["spruch"] or "")
                self.baum.insert(knoten, "end", iid=f"b{nummer}p{lauf}",
                                 text="  " + B.lesbar(person["name"]),
                                 values=(rolle, kontakt))

        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Beim Bearbeiten werden nur die geänderten Felder ersetzt — "
                       "eigene Bildausschnitte und Instagram-Verlinkungen bleiben "
                       "erhalten. Ein neuer Name zieht automatisch in Überschrift, "
                       "Bildbeschriftung und Bildbeschreibung mit.")).pack(
                           anchor="w", pady=(12, 0))

    def _auswahl(self):
        """(bereich_nummer, person_nummer oder None) - None ohne Auswahl."""
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Nichts gewählt",
                                "Bitte zuerst einen Bereich oder eine Person anklicken.")
            return None
        kennung = self.baum.selection()[0]
        if "p" in kennung:
            bereich, person = kennung[1:].split("p")
            return int(bereich), int(person)
        return int(kennung[1:]), None

    # -------------------------------------------------- Neu
    def neu(self):
        auswahl = self._auswahl()
        if not auswahl:
            return
        nummer, _ = auswahl
        html, bereiche = self._laden()
        bereich, personen, grid_start = bereiche[nummer]
        ist_vorstand = bereich["name"] == "Vorstand"

        frei = team_pflege.freie_bilder(html)
        if not frei:
            if not messagebox.askyesno(
                    "Kein freies Foto",
                    "In media/bilder/ueber-uns/ liegt kein Foto, das noch keiner Karte "
                    "zugeordnet ist.\n\nMit dem Platzhalter fortfahren?"):
                return
            frei = ["platzhalter.jpg"]

        felder = [
            {"schluessel": "bild", "beschriftung": "Foto", "art": "auswahl",
             "optionen": frei, "hinweis": "aus media/bilder/ueber-uns/"},
            {"schluessel": "name", "beschriftung": "Name"},
            {"schluessel": "kurzrolle", "beschriftung": "Rolle im Bild",
             "hinweis": "kurz, erscheint auf dem Foto"},
        ]
        if ist_vorstand:
            felder += [
                {"schluessel": "rolle", "beschriftung": "Rolle unter dem Namen"},
                {"schluessel": "email", "beschriftung": "E-Mail", "pflicht": False},
            ]
        else:
            felder.append({"schluessel": "spruch", "beschriftung": "Spruch",
                           "pflicht": False})

        if personen:
            felder.append({"schluessel": "stelle", "beschriftung": "Position",
                           "art": "auswahl",
                           "optionen": [self.VORNE] +
                                       [f"Nach {B.lesbar(p['name'])}" for p in personen]})

        werte = B.frage_formular(self.rahmen, self.s, f"Neue Person — {bereich['name']}",
                                 felder,
                                 einleitung="Das Foto muss schon im Ordner liegen. "
                                            "Die WebP-Fassung wird automatisch "
                                            "eingebunden, falls vorhanden.")
        if not werte:
            return

        karte = team_pflege.baue_personen_karte(
            ist_vorstand, werte["bild"], B.fuer_html(werte["name"]),
            B.fuer_html(werte["kurzrolle"]), B.fuer_html(werte.get("rolle", "")),
            werte.get("email", ""), B.fuer_html(werte.get("spruch", "")))

        stelle = 0
        if personen:
            moeglichkeiten = [self.VORNE] + [f"Nach {B.lesbar(p['name'])}" for p in personen]
            stelle = moeglichkeiten.index(werte["stelle"])

        h.schreibe_datei(team_pflege.UEBER_UNS_HTML,
                         team_pflege.fuege_person_ein(html, karte, personen,
                                                      stelle, grid_start))
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Bearbeiten
    def bearbeiten(self):
        auswahl = self._auswahl()
        if not auswahl:
            return
        nummer, lauf = auswahl
        if lauf is None:
            messagebox.showinfo("Bereich gewählt",
                                "Zum Ändern bitte eine einzelne Person anklicken.")
            return

        html, bereiche = self._laden()
        person = bereiche[nummer][1][lauf]

        # Nur anbieten, was diese Karte wirklich hat
        felder, werte = [{"schluessel": "name", "beschriftung": "Name"}], \
                        {"name": B.lesbar(person["name"])}
        for schluessel, beschriftung in (("kurzrolle", "Rolle im Bild"),
                                         ("rolle", "Rolle unter dem Namen"),
                                         ("spruch", "Spruch"),
                                         ("email", "E-Mail")):
            if person[schluessel] is not None:
                felder.append({"schluessel": schluessel, "beschriftung": beschriftung,
                               "pflicht": False})
                werte[schluessel] = B.lesbar(person[schluessel])

        neu = B.frage_formular(self.rahmen, self.s, "Person bearbeiten", felder, werte)
        if not neu:
            return

        # E-Mail und Bildpfade nicht als Text kodieren
        gesetzt = {s: (w if s == "email" else B.fuer_html(w)) for s, w in neu.items()}
        block = team_pflege.aendere_person(person, gesetzt)

        if block == person["block"]:
            messagebox.showinfo("Nichts geändert", "Die Angaben sind unverändert.")
            return

        h.schreibe_datei(team_pflege.UEBER_UNS_HTML,
                         html[:person["start"]] + block + html[person["ende"]:])
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Loeschen
    def loeschen(self):
        auswahl = self._auswahl()
        if not auswahl:
            return
        nummer, lauf = auswahl
        if lauf is None:
            messagebox.showinfo("Bereich gewählt",
                                "Zum Entfernen bitte eine einzelne Person anklicken.")
            return

        html, bereiche = self._laden()
        person = bereiche[nummer][1][lauf]

        if not messagebox.askyesno(
                "Person entfernen",
                f"{team_pflege.beschreibe(person)}\n\n"
                "Das Foto bleibt im Ordner liegen — nur die Karte verschwindet.\n\n"
                "Wirklich entfernen?"):
            return

        h.schreibe_datei(team_pflege.UEBER_UNS_HTML,
                         team_pflege.entferne_person(html, person))
        self.aktualisieren()
        self.app.fuss_auffrischen()
