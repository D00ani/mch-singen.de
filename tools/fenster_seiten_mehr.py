# -*- coding: utf-8 -*-
"""
Weitere Fensterseiten: Kart-Klassen, Zeitleiste der Geschichte, Bilder-
Wechsler der Startseite und Suchen & Ersetzen ueber alle Seiten.

Jede Seite liest und schreibt ueber ihr eigenes Modul (klassen_pflege,
geschichte_pflege, slider_pflege, ersetzen) und bietet im Formular eine
Vorschau im Browser an, bevor etwas gespeichert wird.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ersetzen
import fenster_bausteine as B
import geschichte_pflege as gp
import klassen_pflege as kp
import pflege_hilfen as h
import slider_pflege as sl
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT


def _fehler_zeigen(titel, fehler):
    messagebox.showerror(titel, str(fehler))


# ------------------------------------------------------------------
# Kart-Klassen
# ------------------------------------------------------------------

class KlassenSeite(Seite):
    titel = "Kart-Klassen"
    untertitel = ("Die Tabelle „Klassen & Altersgruppen“ auf der Kart-Seite. Zum Saisonwechsel "
                  "rutschen die Jahrgänge der Jugendklassen mit einem Knopf weiter.")

    JUGEND, ERWACHSENE = "Jugendklasse (mit Jahrgängen)", "Erwachsenenklasse"
    VORNE = "Ganz vorne"

    def baue(self):
        self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf("Neue Klasse", self.neu)
        self.knopf("Jahrgänge +1", self.jahrgaenge, "haupt")
        self.baum = None
        self.klassen = []

    def aktualisieren(self):
        self.leeren()
        try:
            self.klassen = kp.lies()
        except (OSError, ValueError) as fehler:
            B.karte(self.inhalt, self.s, uebersicht.FAELLIG, "Tabelle nicht gefunden", str(fehler))
            self.baum = None
            return

        B.abschnitt(self.inhalt, self.s, "Klassen & Altersgruppen",
                    f"{len(self.klassen)} Klassen · Jugendklassen: Jahrgänge "
                    f"{kp.jahrgaenge_kurz(self.klassen)}")
        self.baum = self.tabelle(self.inhalt, ("Klasse", "Voraussetzung", "Gruppe"), (130, 380, 160),
                                 hoehe=min(max(len(self.klassen), 1), 12),
                                 zeilenzahl=len(self.klassen))
        for nummer, k in enumerate(self.klassen):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(k["klasse"], k["voraussetzung"],
                                     "Erwachsene" if k["erwachsen"] else "Jugend"))
        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Am Handy schaltet die Seite zwischen Jugend und Erwachsenen um - "
                       "deshalb gehört zu jeder Klasse die Gruppe. „Jahrgänge +1“ zählt jede "
                       "Jahreszahl der Jugendklassen um eins hoch; die Erwachsenenklassen "
                       "bleiben unverändert.")).pack(anchor="w", pady=(12, 0))

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Keine Klasse gewählt", "Bitte zuerst eine Klasse in der Liste anklicken.")
            return None
        return int(self.baum.selection()[0])

    def _felder(self, mit_stelle=False):
        felder = [
            {"schluessel": "klasse", "beschriftung": "Klasse", "hinweis": "z. B. „Klasse I a“",
             "pruefer": kp.pruefe_text},
            {"schluessel": "voraussetzung", "beschriftung": "Voraussetzung",
             "hinweis": "z. B. „Jahrgänge 2008 · 2009 · 2010“ oder „Herren ab 18 Jahren“",
             "pruefer": kp.pruefe_text},
            {"schluessel": "gruppe", "beschriftung": "Gruppe", "art": "auswahl",
             "optionen": [self.JUGEND, self.ERWACHSENE]},
        ]
        if mit_stelle:
            felder.append({"schluessel": "stelle", "beschriftung": "Einsortieren", "art": "auswahl",
                           "optionen": [self.VORNE] + [f"Nach {k['klasse']}" for k in self.klassen]})
        return felder

    def _aus_werten(self, werte):
        return {"klasse": " ".join(werte.get("klasse", "").split()),
                "voraussetzung": " ".join(werte.get("voraussetzung", "").split()),
                "erwachsen": werte.get("gruppe") == self.ERWACHSENE}

    def _speichern(self, klassen):
        try:
            kp.speichern(klassen)
        except (OSError, ValueError) as fehler:
            _fehler_zeigen("Nicht gespeichert", fehler)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        k = self.klassen[nummer]

        def vorschau(werte):
            neu = list(self.klassen)
            neu[nummer] = self._aus_werten(werte)
            kp.vorschau_zeigen(neu, {nummer})

        werte = B.frage_formular(
            self.rahmen, self.s, "Klasse bearbeiten", self._felder(),
            {"klasse": k["klasse"], "voraussetzung": k["voraussetzung"],
             "gruppe": self.ERWACHSENE if k["erwachsen"] else self.JUGEND},
            vorschau=vorschau)
        if not werte:
            return
        neu = list(self.klassen)
        neu[nummer] = self._aus_werten(werte)
        self._speichern(neu)

    def neu(self):
        def liste(werte):
            stelle = 0
            if werte.get("stelle", self.VORNE) != self.VORNE:
                stelle = [f"Nach {k['klasse']}" for k in self.klassen].index(werte["stelle"]) + 1
            neu = list(self.klassen)
            neu.insert(stelle, self._aus_werten(werte))
            return neu, stelle

        def vorschau(werte):
            neu, stelle = liste(werte)
            kp.vorschau_zeigen(neu, {stelle})

        letzte = f"Nach {self.klassen[-1]['klasse']}" if self.klassen else self.VORNE
        werte = B.frage_formular(self.rahmen, self.s, "Neue Klasse", self._felder(True),
                                 {"gruppe": self.JUGEND, "stelle": letzte}, vorschau=vorschau)
        if not werte:
            return
        self._speichern(liste(werte)[0])

    def loeschen(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        k = self.klassen[nummer]
        if not messagebox.askyesno("Klasse löschen",
                                   f"{k['klasse']} - {k['voraussetzung']}\n\nWirklich löschen?"):
            return
        neu = list(self.klassen)
        del neu[nummer]
        self._speichern(neu)

    def jahrgaenge(self):
        if not self.klassen:
            return
        neu = kp.jahrgaenge_verschieben(self.klassen)
        aenderungen = [f"{a['klasse']}:  {a['voraussetzung']}  →  {b['voraussetzung']}"
                       for a, b in zip(self.klassen, neu) if a != b]
        if not aenderungen:
            messagebox.showinfo("Nichts zu tun", "In den Jugendklassen steht keine Jahreszahl.")
            return
        werte = B.frage_formular(
            self.rahmen, self.s, "Jahrgänge eine Saison weiterschieben", [],
            einleitung="Das ändert sich auf der Kart-Seite:\n\n" + "\n".join(aenderungen)
                       + "\n\nMit „Speichern“ übernehmen.",
            vorschau=lambda _: kp.vorschau_zeigen(
                neu, {n for n, (a, b) in enumerate(zip(self.klassen, neu)) if a != b}))
        if werte is None:
            return
        self._speichern(neu)


# ------------------------------------------------------------------
# Zeitleiste der Geschichte
# ------------------------------------------------------------------

class GeschichteSeite(Seite):
    titel = "Geschichte"
    untertitel = ("Die Zeitleiste auf der Seite „Geschichte des MCH“: Abschnitte bearbeiten, "
                  "neue einfügen, alte entfernen.")

    SCHREIBWEISE = ("Leerzeile = neuer Absatz · **wichtig** = fett · "
                    "[Kartsport](kartsport.html) = Link")
    AM_ENDE = "Am Ende"

    def baue(self):
        self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf("Neuer Abschnitt", self.neu, "haupt")
        self.baum = None
        self.abschnitte = []

    def aktualisieren(self):
        self.leeren()
        try:
            self.abschnitte = gp.finde()
        except (OSError, ValueError) as fehler:
            B.karte(self.inhalt, self.s, uebersicht.FAELLIG, "Zeitleiste nicht lesbar", str(fehler))
            self.baum = None
            return

        B.abschnitt(self.inhalt, self.s, "Abschnitte", f"{len(self.abschnitte)} Einträge, von oben nach unten")
        self.baum = self.tabelle(self.inhalt, ("Überschrift", "Text", "Absätze"), (260, 360, 70),
                                 hoehe=min(max(len(self.abschnitte), 1), 12),
                                 zeilenzahl=len(self.abschnitte))
        for nummer, a in enumerate(self.abschnitte):
            text = gp.text_lesbar(a).replace("\n\n", " / ")
            anzahl = str(len(a["absaetze"])) + (" + Liste" if a["rest"] else "")
            self.baum.insert("", "end", iid=str(nummer),
                             values=(gp.titel_lesbar(a), text[:90] + ("…" if len(text) > 90 else ""),
                                     anzahl))
        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Schreibweise im Text:  " + self.SCHREIBWEISE + "\n"
                       "Trennlinien und Bildplätze zwischen den Abschnitten bleiben, wo sie sind. "
                       "Die Liste beim Jahr 1979 bleibt beim Bearbeiten erhalten.")).pack(
                           anchor="w", pady=(12, 0))

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Kein Abschnitt gewählt", "Bitte zuerst einen Abschnitt anklicken.")
            return None
        return int(self.baum.selection()[0])

    def _felder(self, abschnitt=None, stellen=None):
        hinweis = self.SCHREIBWEISE
        if abschnitt and abschnitt["rest"]:
            hinweis += "\nDie Liste unter dem Text bleibt erhalten."
        felder = [
            {"schluessel": "titel", "beschriftung": "Überschrift",
             "hinweis": "z. B. „1954: Die Gründung“", "pruefer": gp.pruefe_titel},
            {"schluessel": "text", "beschriftung": "Text", "art": "mehrzeilig",
             "hoehe": 12, "breite": 62, "hinweis": hinweis, "pruefer": gp.pruefe_text},
        ]
        if stellen:
            felder.append({"schluessel": "stelle", "beschriftung": "Einfügen", "art": "auswahl",
                           "optionen": stellen})
        return felder

    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        a = self.abschnitte[nummer]
        alter_text = gp.text_lesbar(a)
        sonder = gp.hat_sonderinhalt(a)
        einleitung = ("Ein Absatz enthält eine Formatierung, die die einfache Schreibweise nicht "
                      "kennt. Bleibt der Text unverändert, bleibt sie erhalten." if sonder else
                      "Vorhandenes HTML wurde in die einfache Schreibweise übersetzt - es geht nichts verloren.")

        def seite_mit(werte, markiert):
            behalten = werte["text"] == alter_text
            return gp.ersetzt(h.lies_datei(gp.GESCHICHTE_HTML), nummer, werte["titel"],
                              gp.absaetze_aus_text(werte["text"]), markiert, behalten)

        werte = B.frage_formular(self.rahmen, self.s, "Abschnitt bearbeiten", self._felder(a),
                                 {"titel": gp.titel_lesbar(a), "text": alter_text},
                                 einleitung=einleitung,
                                 vorschau=lambda w: gp.vorschau_zeigen(seite_mit(w, True)))
        if not werte:
            return
        if sonder and werte["text"] != alter_text and not messagebox.askyesno(
                "Formatierung geht verloren",
                "Der geänderte Text wird ohne die besondere Formatierung gespeichert.\n\nTrotzdem speichern?"):
            return
        try:
            gp.speichern(seite_mit(werte, False))
        except (OSError, ValueError, IndexError) as fehler:
            _fehler_zeigen("Nicht gespeichert", fehler)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def neu(self):
        stellen = [f"Vor „{gp.titel_lesbar(a)}“" for a in self.abschnitte] + [self.AM_ENDE]

        def seite_mit(werte, markiert):
            stelle = stellen.index(werte.get("stelle", self.AM_ENDE))
            return gp.eingefuegt(h.lies_datei(gp.GESCHICHTE_HTML), stelle, werte["titel"],
                                 gp.absaetze_aus_text(werte["text"]), markiert)

        werte = B.frage_formular(self.rahmen, self.s, "Neuer Abschnitt", self._felder(stellen=stellen),
                                 {"stelle": self.AM_ENDE},
                                 einleitung="Ein neuer Abschnitt der Zeitleiste - meist am Ende.",
                                 vorschau=lambda w: gp.vorschau_zeigen(seite_mit(w, True)))
        if not werte:
            return
        try:
            gp.speichern(seite_mit(werte, False))
        except (OSError, ValueError) as fehler:
            _fehler_zeigen("Nicht gespeichert", fehler)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def loeschen(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        a = self.abschnitte[nummer]
        zusatz = "\n\nDie Liste in diesem Abschnitt verschwindet mit." if a["rest"] else ""
        if not messagebox.askyesno("Abschnitt löschen",
                                   f"„{gp.titel_lesbar(a)}“{zusatz}\n\nWirklich löschen?"):
            return
        try:
            gp.speichern(gp.entfernt(h.lies_datei(gp.GESCHICHTE_HTML), nummer))
        except (OSError, ValueError, IndexError) as fehler:
            _fehler_zeigen("Nicht gelöscht", fehler)
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Bilder-Wechsler der Startseite
# ------------------------------------------------------------------

class SliderSeite(Seite):
    titel = "Bilder der Startseite"
    untertitel = ("Die drei wechselnden Bilder oben auf der Startseite: Bild, Beschriftung und "
                  "wohin ein Klick führt.")

    def baue(self):
        self.knopf("Bearbeiten", self.bearbeiten, "haupt")
        self.baum = None
        self.bilder = []

    def aktualisieren(self):
        self.leeren()
        try:
            self.bilder = sl.bilder()
            hinweise = sl.kopien_stimmen()
        except (OSError, ValueError) as fehler:
            B.karte(self.inhalt, self.s, uebersicht.FAELLIG, "Bilder-Wechsler nicht gefunden", str(fehler))
            self.baum = None
            return

        if hinweise:
            B.karte(self.inhalt, self.s, uebersicht.HINWEIS, "Die Kopien für den Endlos-Lauf weichen ab",
                    "; ".join(hinweise) + " - beim Weiterblättern springt dann das Bild.",
                    "Angleichen", self.angleichen)

        B.abschnitt(self.inhalt, self.s, "Bilder", "in der Reihenfolge, in der sie erscheinen")
        self.baum = self.tabelle(self.inhalt, ("Nr.", "Beschriftung", "Führt zu", "Bild"),
                                 (40, 220, 200, 230), hoehe=max(len(self.bilder), 1),
                                 zeilenzahl=len(self.bilder))
        for nummer, b in enumerate(self.bilder):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(nummer + 1, b["text"], b["link"], b["bild"].split("/")[-1]))
        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Ein neues Bild am besten vorher in media/bilder/ ablegen (JPG oder PNG, "
                       "querformatig 4:3). Beim Speichern entstehen die schnellen WebP-Fassungen "
                       "von selbst. Damit das Blättern endlos wirkt, stehen Bild 1 und 3 im HTML "
                       "doppelt - die Kopien zieht das Fenster automatisch mit.")).pack(
                           anchor="w", pady=(12, 0))

    def _pruefe_bild(self, wert):
        pfad = os.path.join(ROOT, wert)
        if not os.path.isfile(pfad):
            return "Die Datei gibt es nicht - bitte über „Auswählen…“ wählen."
        if not wert.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return "Bitte ein Bild (JPG, PNG oder WebP)."
        return None

    def _neu(self, alt, werte, fuer_vorschau):
        neu = {"link": werte["link"].strip(), "text": " ".join(werte["text"].split()),
               "alt": " ".join(werte["alt"].split()), "bild": werte["bild"].strip(),
               "srcset": alt["srcset"], "breite": alt["breite"], "hoehe": alt["hoehe"]}
        if neu["bild"] != alt["bild"]:
            if fuer_vorschau:
                # Fuer die Vorschau keine Dateien erzeugen - das Bild selbst reicht
                neu["srcset"] = neu["bild"]
                neu["breite"], neu["hoehe"] = sl.bildmasse(neu["bild"])
            else:
                neu["srcset"], neu["breite"], neu["hoehe"] = sl.webp_erzeugen(neu["bild"])
        return neu

    def bearbeiten(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Kein Bild gewählt", "Bitte zuerst ein Bild in der Liste anklicken.")
            return
        nummer = int(self.baum.selection()[0])
        alt = self.bilder[nummer]
        felder = [
            {"schluessel": "text", "beschriftung": "Beschriftung", "hinweis": "steht unten im Bild"},
            {"schluessel": "link", "beschriftung": "Führt zu", "art": "auswahl", "frei": True,
             "optionen": sl.ziele(), "hinweis": "Seite der Webseite - eine volle Adresse (https://…) geht auch"},
            {"schluessel": "alt", "beschriftung": "Bildbeschreibung",
             "hinweis": "für Vorleseprogramme und Suchmaschinen - was ist zu sehen?"},
            {"schluessel": "bild", "beschriftung": "Bild", "art": "datei", "basis": ROOT,
             "ordner": "media/bilder", "praefix": "", "pruefer": self._pruefe_bild,
             "typen": [("Bilder", "*.jpg *.jpeg *.png *.webp"), ("Alle Dateien", "*.*")]},
        ]

        def vorschau(werte):
            fehler = self._pruefe_bild(werte["bild"])
            if fehler:
                return fehler
            text = sl.geaendert(h.lies_datei(sl.STARTSEITE_HTML), nummer,
                                self._neu(alt, werte, True), markiert=True)
            sl.vorschau_zeigen(text)

        werte = B.frage_formular(self.rahmen, self.s, f"Bild {nummer + 1} bearbeiten", felder,
                                 {k: alt[k] for k in ("text", "link", "alt", "bild")},
                                 vorschau=vorschau)
        if not werte:
            return
        try:
            neu = self._neu(alt, werte, False)
            sl.speichern(sl.geaendert(h.lies_datei(sl.STARTSEITE_HTML), nummer, neu))
        except (OSError, ValueError) as fehler:
            _fehler_zeigen("Nicht gespeichert", fehler)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def angleichen(self):
        text = h.lies_datei(sl.STARTSEITE_HTML)
        for nummer, b in enumerate(sl.bilder(text)):
            text = sl.geaendert(text, nummer, b)
        sl.speichern(text)
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Suchen & Ersetzen
# ------------------------------------------------------------------

class ErsetzenSeite(Seite):
    titel = "Suchen & Ersetzen"
    untertitel = ("Sucht im sichtbaren Text aller Seiten - Technik, Links und Kommentare bleiben "
                  "unberührt. Ersetzt wird nur, was du in der Liste auswählst.")

    def baue(self):
        self.knopf("Ausgewählte ersetzen", self.ersetzen_auswahl, "haupt")
        self.knopf("Einzeln bestätigen", self.einzeln)
        self.knopf("Vorschau", self.vorschau)
        self.baum = None
        self.treffer = []

        zeile = tk.Frame(self.fest, bg=B.FARBEN["grund"])
        zeile.pack(fill="x", pady=(0, 4))
        self.such = self._eingabe(zeile, "Suchen:", 26)
        self.ersatz = self._eingabe(zeile, "Ersetzen durch:", 26)
        self.gross_klein = tk.BooleanVar(value=False)
        tk.Checkbutton(zeile, text="Groß/klein beachten", variable=self.gross_klein,
                       command=self.suchen, bg=B.FARBEN["grund"], fg=B.FARBEN["text"],
                       font=self.s.klein, activebackground=B.FARBEN["grund"],
                       selectcolor=B.FARBEN["karte"]).pack(side="left", padx=(0, 10))
        B.knopf(zeile, "Suchen", self.suchen, self.s, padx=12, pady=2).pack(side="left")
        self.such.bind("<Return>", lambda _: self.suchen())
        self.ersatz.bind("<Return>", lambda _: self.suchen())

    def _eingabe(self, eltern, text, breite):
        tk.Label(eltern, text=text, bg=B.FARBEN["grund"], fg=B.FARBEN["text"],
                 font=self.s.text).pack(side="left", padx=(0, 6))
        feld = tk.Entry(eltern, font=self.s.text, width=breite, relief="solid", bd=1,
                        bg=B.FARBEN["karte"], fg=B.FARBEN["text"])
        feld.pack(side="left", padx=(0, 12))
        return feld

    def aktualisieren(self):
        self.suchen()

    def suchen(self):
        self.leeren()
        begriff = self.such.get().strip()
        if not begriff:
            self.treffer, self.baum = [], None
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Oben einen Suchbegriff eingeben.",
                    "Gesucht wird in allen veröffentlichten Seiten. Ein Leerzeichen im Suchtext "
                    "passt auch auf einen Zeilenwechsel. Termine, News und Statistiken stehen in "
                    "eigenen Dateien - die findet die Suche nicht, dafür gibt es eigene Seiten.")
            return
        self.treffer = ersetzen.suche(begriff, self.gross_klein.get())
        seiten = len({t["seite"] for t in self.treffer})
        B.abschnitt(self.inhalt, self.s, "Treffer",
                    f"{len(self.treffer)} Stelle(n) auf {seiten} Seite(n) · Strg/Umschalt-Klick "
                    "wählt mehrere, Strg+A alle")
        if not self.treffer:
            B.karte(self.inhalt, self.s, uebersicht.INFO, f"„{begriff}“ kommt im sichtbaren Text nicht vor.")
            self.baum = None
            return
        self.baum = self.tabelle(self.inhalt, ("Seite", "Zeile", "Fundstelle"), (190, 55, 460),
                                 hoehe=min(len(self.treffer), 16), zeilenzahl=len(self.treffer))
        for nummer, t in enumerate(self.treffer):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(t["seite"], t["zeile"],
                                     f"…{t['vorher'][-38:]} »{t['treffer']}« {t['nachher'][:38]}…"))
        self.baum.bind("<Control-a>", lambda _: (self.baum.selection_set(self.baum.get_children()), "break")[1])
        self.baum.bind("<Control-A>", lambda _: (self.baum.selection_set(self.baum.get_children()), "break")[1])

    def _auswahl(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Nichts ausgewählt",
                                "Bitte zuerst in der Liste die Stellen anklicken, die ersetzt werden "
                                "sollen (Strg/Umschalt-Klick für mehrere, Strg+A für alle).")
            return None
        return [self.treffer[int(i)] for i in self.baum.selection()]

    def _ersatz_ok(self):
        fehler = ersetzen.pruefe_ersatz(self.ersatz.get())
        if fehler:
            messagebox.showerror("Ersatztext prüfen", fehler)
            return False
        return True

    def vorschau(self):
        auswahl = self._auswahl()
        if not auswahl or not self._ersatz_ok():
            return
        try:
            meldung = ersetzen.vorschau_zeigen(auswahl, self.ersatz.get())
        except (OSError, ValueError) as fehler:
            meldung = str(fehler)
        if meldung:
            messagebox.showinfo("Vorschau", meldung)

    def _ausfuehren(self, auswahl):
        try:
            geaendert = ersetzen.ersetze(auswahl, self.ersatz.get())
        except (OSError, ValueError) as fehler:
            _fehler_zeigen("Nicht ersetzt", fehler)
            geaendert = []
        if geaendert:
            messagebox.showinfo("Ersetzt", f"{len(auswahl)} Stelle(n) ersetzt in:\n\n  "
                                + "\n  ".join(geaendert)
                                + "\n\nZurücknehmen geht über „Verlauf“ bzw. „Rückgängig“.")
        self.suchen()
        self.app.fuss_auffrischen()

    def ersetzen_auswahl(self):
        auswahl = self._auswahl()
        if not auswahl or not self._ersatz_ok():
            return
        ersatz = self.ersatz.get()
        seiten = sorted({t["seite"] for t in auswahl})
        if not messagebox.askyesno(
                "Ersetzen",
                f"{len(auswahl)} Stelle(n) „{auswahl[0]['treffer']}“ durch „{ersatz}“ ersetzen?\n\n"
                + ("Der Ersatztext ist leer - die Stellen werden gelöscht.\n\n" if not ersatz else "")
                + "Betroffen: " + ", ".join(seiten)):
            return
        self._ausfuehren(auswahl)

    def einzeln(self):
        """Geht die ausgewaehlten Stellen (ohne Auswahl: alle) einzeln durch."""
        if not self.treffer or not self._ersatz_ok():
            return
        liste = ([self.treffer[int(i)] for i in self.baum.selection()]
                 if self.baum and self.baum.selection() else list(self.treffer))
        ersatz, ja = self.ersatz.get(), []
        for nummer, t in enumerate(liste, 1):
            antwort = messagebox.askyesnocancel(
                f"Stelle {nummer} von {len(liste)}",
                f"{t['seite']}, Zeile {t['zeile']}\n\n…{t['vorher']} »{t['treffer']}« {t['nachher']}…\n\n"
                f"Durch „{ersatz}“ ersetzen?\n\nJa = ersetzen · Nein = überspringen · "
                "Abbrechen = aufhören (bis hierher Bestätigtes wird ersetzt)")
            if antwort is None:
                break
            if antwort:
                ja.append(t)
        if ja:
            self._ausfuehren(ja)
