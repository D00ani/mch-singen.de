# -*- coding: utf-8 -*-
"""
Fensterseiten fuer die Textinhalte: News-Karten und Fragen & Antworten.

Wie die uebrigen Pflegeseiten: Tabelle mit dem Vorhandenen, oben rechts
Neu/Bearbeiten/Loeschen, Eingabe ueber das gemeinsame Formularfenster.
Gelesen und geschrieben wird mit den Funktionen der Terminal-Werkzeuge.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import faq_pflege
import fenster_bausteine as B
import news_pflege
import pflege_hilfen as h
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT


# ------------------------------------------------------------------
# News-Karten
# ------------------------------------------------------------------

class NewsSeite(Seite):
    titel = "News-Karten auf „Aktuelles“"
    untertitel = ("Die Meldungen, die Besucher auf der Aktuelles-Seite sehen — "
                  "gegliedert nach den Abschnitten der Seite.")

    OBEN = "Ganz oben im Abschnitt"

    def baue(self):
        self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf("Neue Karte", self.neu, "haupt")
        self.baum = None
        self.karten = []

    def _html(self):
        return h.lies_datei(news_pflege.AKTUELLES_HTML)

    def aktualisieren(self):
        self.leeren()
        self.karten = news_pflege.finde_karten(self._html())

        abschnitte = []
        for karte in self.karten:
            if karte["abschnitt"] not in abschnitte:
                abschnitte.append(karte["abschnitt"])

        B.abschnitt(self.inhalt, self.s, "Karten",
                    f"{len(self.karten)} in {len(abschnitte)} Abschnitt(en)")

        if not self.karten:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Keine News-Karte gefunden.",
                    "Ohne bestehende Karte fehlt die Vorlage — bitte im Terminal anlegen.")
            self.baum = None
            return

        self.baum = self.tabelle(
            self.inhalt, ("Abschnitt", "Datum", "Titel", "Extras"),
            (170, 130, 280, 90), hoehe=min(len(self.karten), 14),
            zeilenzahl=len(self.karten))

        for nummer, karte in enumerate(self.karten):
            extras = []
            if karte["links"]:
                extras.append(f"{len(karte['links'])} Link(s)")
            if karte["hat_schaltflaechen"]:
                extras.append("Schaltfläche")
            self.baum.insert("", "end", iid=str(nummer),
                             values=(B.lesbar(karte["abschnitt"]),
                                     B.lesbar(karte["datum"]) or "—",
                                     B.lesbar(karte["titel"]) or "(ohne Titel)",
                                     ", ".join(extras)))
        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Keine Karte gewählt",
                                "Bitte zuerst eine Karte in der Liste anklicken.")
            return None
        return int(self.baum.selection()[0])

    # -------------------------------------------------- Neu
    def neu(self):
        if not self.karten:
            return

        abschnitte = []
        for karte in self.karten:
            if B.lesbar(karte["abschnitt"]) not in abschnitte:
                abschnitte.append(B.lesbar(karte["abschnitt"]))

        werte = B.frage_formular(
            self.rahmen, self.s, "Neue News-Karte", [
                {"schluessel": "abschnitt", "beschriftung": "Abschnitt",
                 "art": "auswahl", "optionen": abschnitte},
                {"schluessel": "badge", "beschriftung": "Kennzeichen", "art": "auswahl",
                 "optionen": [name for name, _ in news_pflege.BADGES],
                 "hinweis": "farbiges Etikett oben in der Karte"},
                {"schluessel": "datum", "beschriftung": "Datum",
                 "hinweis": "Freitext, z. B. „Saison 2026“ oder „Sa, 08.08.2026“"},
                {"schluessel": "titel", "beschriftung": "Titel"},
                {"schluessel": "beschreibung", "beschriftung": "Text", "art": "mehrzeilig"},
                {"schluessel": "link_ziel", "beschriftung": "Link-Ziel", "pflicht": False,
                 "hinweis": "leer = kein Link; z. B. ../media/dokumente/datei.pdf"},
                {"schluessel": "link_text", "beschriftung": "Link-Beschriftung",
                 "pflicht": False},
            ],
            einleitung="Das Datum ist bei News Freitext und lässt sich nicht sortieren — "
                       "die Stelle im Abschnitt wählst du gleich danach selbst.")
        if not werte:
            return

        im_abschnitt = [k for k in self.karten
                        if B.lesbar(k["abschnitt"]) == werte["abschnitt"]]
        if not im_abschnitt:
            messagebox.showerror("Abschnitt leer",
                                 "In diesem Abschnitt gibt es keine Karte als Bezugspunkt.")
            return

        stelle = 0
        if len(im_abschnitt) > 1:
            auswahl = B.frage_formular(
                self.rahmen, self.s, "Wohin im Abschnitt?", [
                    {"schluessel": "stelle", "beschriftung": "Position", "art": "auswahl",
                     "optionen": [self.OBEN] + [f"Nach „{B.lesbar(k['titel'])}“" for k in im_abschnitt]},
                ], einleitung=f"Abschnitt „{werte['abschnitt']}“ hat "
                              f"{len(im_abschnitt)} Karten.")
            if not auswahl:
                return
            moeglichkeiten = [self.OBEN] + [f"Nach „{B.lesbar(k['titel'])}“" for k in im_abschnitt]
            stelle = moeglichkeiten.index(auswahl["stelle"])

        badge = next(b for b in news_pflege.BADGES if b[0] == werte["badge"])
        link_ziel, korrekturen = h.normalisiere_medienpfad(werte["link_ziel"], praefix="../")
        if korrekturen:
            messagebox.showinfo("Pfad angepasst", "\n".join(korrekturen) + f"\n\n{link_ziel}")

        block = news_pflege.baue_karte(
            badge, B.fuer_html(werte["datum"]), B.fuer_html(werte["titel"]),
            B.fuer_html(werte["beschreibung"]), link_ziel, B.fuer_html(werte["link_text"]))

        if stelle == 0:
            bezug, davor = im_abschnitt[0], True
        else:
            bezug, davor = im_abschnitt[stelle - 1], False

        h.schreibe_datei(news_pflege.AKTUELLES_HTML,
                         news_pflege.fuege_karte_ein(self._html(), block, bezug, davor))
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Bearbeiten
    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        karte = self.karten[nummer]

        # Nur die Felder anbieten, die diese Karte wirklich hat - manche
        # Karten bestehen nur aus Titel und Schaltflaechen.
        felder, werte = [], {}
        for schluessel, beschriftung, art in (("datum", "Datum", "text"),
                                              ("titel", "Titel", "text"),
                                              ("beschreibung", "Text", "mehrzeilig")):
            if karte[schluessel] is not None:
                felder.append({"schluessel": schluessel, "beschriftung": beschriftung,
                               "art": art})
                werte[schluessel] = B.lesbar(karte[schluessel])

        if not felder:
            messagebox.showinfo(
                "Nichts zu ändern",
                "Diese Karte hat weder Datum noch Titel oder Text — vermutlich "
                "besteht sie nur aus Schaltflächen. Die müssen im HTML bearbeitet werden.")
            return

        hinweis = ("Diese Karte enthält Schaltflächen (z. B. Kalender-Download). "
                   "Die bleiben unverändert erhalten."
                   if karte["hat_schaltflaechen"] else None)
        neu = B.frage_formular(self.rahmen, self.s, "News-Karte bearbeiten", felder, werte,
                               einleitung=hinweis)
        if not neu:
            return

        block = karte["block"]
        muster = {"datum": r'<span class="news-date">(.*?)</span>',
                  "titel": r"<h3>(.*?)</h3>",
                  "beschreibung": r'<p class="news-card-desc">(.*?)</p>'}
        for schluessel, wert in neu.items():
            block = news_pflege.ersetze_inhalt(block, muster[schluessel],
                                               B.fuer_html(wert))

        html = self._html()
        h.schreibe_datei(news_pflege.AKTUELLES_HTML,
                         html[:karte["start"]] + block + html[karte["ende"]:])
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Loeschen
    def loeschen(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        karte = self.karten[nummer]

        warnung = ("\n\nACHTUNG: Diese Karte enthält Schaltflächen "
                   "(z. B. Kalender-Download)." if karte["hat_schaltflaechen"] else "")
        if not messagebox.askyesno(
                "News-Karte löschen",
                f"{news_pflege.beschreibe(karte)}{warnung}\n\nWirklich löschen?"):
            return

        h.schreibe_datei(news_pflege.AKTUELLES_HTML,
                         news_pflege.entferne_karte(self._html(), karte))
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Fragen & Antworten
# ------------------------------------------------------------------

class FaqSeite(Seite):
    titel = "Fragen & Antworten"
    untertitel = ("Die aufklappbaren Fragen auf der FAQ-Seite. Für Hervorhebungen und "
                  "Links reicht eine einfache Schreibweise — kein HTML nötig.")

    SCHREIBWEISE = ("**wichtig**  ergibt fetten Text\n"
                    "[Kartsport](kartsport.html)  ergibt einen Link auf die Seite")

    def baue(self):
        self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf("Neue Frage", self.neu, "haupt")
        self.baum = None
        self.fragen = []

    def _html(self):
        return faq_pflege.lade_html()

    def aktualisieren(self):
        self.leeren()
        self.fragen = faq_pflege.finde_fragen(self._html())

        B.abschnitt(self.inhalt, self.s, "Fragen", f"{len(self.fragen)} Einträge")

        if not self.fragen:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Noch keine Frage angelegt.",
                    "Oben rechts auf „Neue Frage“.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Frage", "Antwort"), (300, 370),
                                 hoehe=min(len(self.fragen), 14), zeilenzahl=len(self.fragen))
        for nummer, eintrag in enumerate(self.fragen):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(B.lesbar(eintrag["frage"]),
                                     B.lesbar(faq_pflege.kurz(eintrag["antwort_html"], 90))))
        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w",
                 text="Schreibweise in Antworten:\n" + self.SCHREIBWEISE).pack(
                     anchor="w", pady=(12, 0))

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Keine Frage gewählt",
                                "Bitte zuerst eine Frage in der Liste anklicken.")
            return None
        return int(self.baum.selection()[0])

    def _felder(self):
        return [
            {"schluessel": "frage", "beschriftung": "Frage"},
            {"schluessel": "antwort", "beschriftung": "Antwort", "art": "mehrzeilig",
             "hinweis": self.SCHREIBWEISE},
        ]

    def _pruefe_links(self, antwort_html):
        """Warnt, wenn eine verlinkte Seite gar nicht existiert."""
        import re
        fehlend = [ziel for ziel in re.findall(r'<a href="([^"]*)"', antwort_html)
                   if not ziel.startswith(("http", "mailto:", "tel:", "#"))
                   and not os.path.isfile(os.path.join(ROOT, "pages", ziel))]
        if fehlend:
            messagebox.showwarning(
                "Link zeigt ins Leere",
                "Diese verlinkten Seiten gibt es nicht:\n\n  " + "\n  ".join(fehlend) +
                "\n\nDie Frage wurde trotzdem gespeichert — bitte den Link prüfen.")

    def neu(self):
        werte = B.frage_formular(self.rahmen, self.s, "Neue Frage", self._felder(),
                                 einleitung="Die Frage wird unten angehängt.")
        if not werte:
            return

        antwort_html = faq_pflege.einfach_zu_html(B.fuer_html(werte["antwort"]))
        block = faq_pflege.baue_eintrag(B.fuer_html(werte["frage"]), antwort_html)

        html = self._html()
        if self.fragen:
            stelle = self.fragen[-1]["match"].end()
            neu = html[:stelle] + "\r\n" + block + html[stelle:]
        else:
            pos = html.find(faq_pflege.CONTAINER_ANKER)
            if pos == -1:
                messagebox.showerror("Nicht möglich",
                                     "Der Anker für die FAQ-Liste wurde nicht gefunden.")
                return
            stelle = html.find("\r\n", pos) + 2
            neu = html[:stelle] + block + "\r\n" + html[stelle:]

        h.schreibe_datei(faq_pflege.FAQ_HTML, neu)
        self._pruefe_links(antwort_html)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        eintrag = self.fragen[nummer]

        werte = B.frage_formular(
            self.rahmen, self.s, "Frage bearbeiten", self._felder(),
            {"frage": B.lesbar(eintrag["frage"]),
             "antwort": B.lesbar(faq_pflege.html_zu_einfach(eintrag["antwort_html"]))},
            einleitung="Vorhandenes HTML wurde in die einfache Schreibweise "
                       "zurückverwandelt — es geht nichts verloren.")
        if not werte:
            return

        antwort_html = faq_pflege.einfach_zu_html(B.fuer_html(werte["antwort"]))
        block = faq_pflege.baue_eintrag(B.fuer_html(werte["frage"]), antwort_html)

        html = self._html()
        treffer = eintrag["match"]
        start = treffer.start()
        # Eigene Einrueckung des Blocks - die vorhandene muss weichen
        while start > 0 and html[start - 1] in " \t":
            start -= 1
        h.schreibe_datei(faq_pflege.FAQ_HTML,
                         html[:start] + block + html[treffer.end():])
        self._pruefe_links(antwort_html)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def loeschen(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        eintrag = self.fragen[nummer]

        if not messagebox.askyesno("Frage löschen",
                                   f"{eintrag['frage']}\n\nWirklich löschen?"):
            return

        html = self._html()
        treffer = eintrag["match"]
        start, ende = treffer.start(), treffer.end()
        while start > 0 and html[start - 1] in " \t":
            start -= 1
        if html[ende:ende + 2] == "\r\n":
            ende += 2
        h.schreibe_datei(faq_pflege.FAQ_HTML, html[:start] + html[ende:])
        self.aktualisieren()
        self.app.fuss_auffrischen()
