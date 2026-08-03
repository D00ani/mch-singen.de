# -*- coding: utf-8 -*-
"""
Fensterseiten zum Pflegen von Inhalten (Liste + Formular).

Aufbau ist ueberall gleich: Tabelle mit dem Vorhandenen, oben rechts
"Neu / Bearbeiten / Loeschen", die Eingabe laeuft ueber das gemeinsame
Formularfenster aus tools/fenster_bausteine.py.

Gelesen und geschrieben wird mit denselben Funktionen wie im Terminal -
die Dateiformate stehen weiterhin nur an einer Stelle.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import os
import sys
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archiv_pflege
import ausschreibung_pdf
import fenster_bausteine as B
import pflege_hilfen as h
import termine_verwalten as tv
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT


# ------------------------------------------------------------------
# Renntermine
# ------------------------------------------------------------------

class RenntermineSeite(Seite):
    titel = "Renntermine verwalten"
    untertitel = ("Die Termine, aus denen der Countdown auf der Startseite und der "
                  "Kalender-Download entstehen.")

    DATEIEN = {"Kart": "timer.txt", "Trial": "timer_trial.txt"}

    def baue(self):
        self.sportart = tk.StringVar(value="Kart")
        self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf("Neuer Termin", self.neu, "haupt")

        wahl = tk.Frame(self.fest, bg=B.FARBEN["grund"])
        wahl.pack(fill="x", pady=(0, 4))
        for name in self.DATEIEN:
            tk.Radiobutton(wahl, text=name, value=name, variable=self.sportart,
                           command=self.aktualisieren, bg=B.FARBEN["grund"],
                           fg=B.FARBEN["text"], font=self.s.text, cursor="hand2",
                           activebackground=B.FARBEN["grund"],
                           selectcolor=B.FARBEN["karte"]).pack(side="left", padx=(0, 14))
        self.baum = None

    # -------------------------------------------------- Daten
    def _datei(self):
        return os.path.join(ROOT, "data", self.DATEIEN[self.sportart.get()])

    def _zeilen(self):
        return h.lies_zeilen(self._datei())

    def _spalten(self, zeile):
        """Eine timer.txt-Zeile als lesbare Tabellenzeile."""
        teile = (zeile.split(";") + [""] * 8)[:8]
        monat = tv.MONAT_ALIASE.get(teile[1].strip().lower())
        if monat and teile[0].strip().isdigit():
            datum = f"{int(teile[0]):02d}.{monat[0]:02d}.{teile[2]}"
        else:
            datum = f"{teile[0]}.{teile[1]}.{teile[2]}"

        if not teile[7]:
            pdf = "—"
        elif ausschreibung_pdf.pdf_existiert(teile[7]):
            pdf = os.path.basename(teile[7])
        else:
            pdf = os.path.basename(teile[7]) + "  (fehlt)"
        return datum, teile[3], teile[4], teile[5], pdf

    def aktualisieren(self):
        self.leeren()
        zeilen = self._zeilen()

        B.abschnitt(self.inhalt, self.s, f"{self.sportart.get()}-Termine",
                    f"{len(zeilen)} Einträge · data/{self.DATEIEN[self.sportart.get()]}")

        if not zeilen:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Noch keine Termine eingetragen.", "Oben rechts auf „Neuer Termin“.")
            self.baum = None
            return

        self.baum = self.tabelle(
            self.inhalt, ("Datum", "Zeit", "Verein", "Ort", "PDF"),
            (95, 60, 80, 180, 230), hoehe=min(len(zeilen), 14), zeilenzahl=len(zeilen))
        for nummer, zeile in enumerate(zeilen):
            self.baum.insert("", "end", iid=str(nummer), values=self._spalten(zeile))
        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Keine Zeile gewählt",
                                "Bitte zuerst einen Termin in der Liste anklicken.")
            return None
        return int(self.baum.selection()[0])

    # -------------------------------------------------- Formular
    def _felder(self, zeilen):
        _, reihenfolge = tv.lade_bekannte_orte(zeilen)
        orte = [f"{verein} {ort}" for verein, ort in reihenfolge]
        return [
            {"schluessel": "tag", "beschriftung": "Tag", "pruefer": h.TAG_VALIDIERER,
             "hinweis": "1–31"},
            {"schluessel": "monat", "beschriftung": "Monat", "art": "auswahl",
             "optionen": tv.MONATE_DE},
            {"schluessel": "jahr", "beschriftung": "Jahr", "pruefer": h.JAHR_VALIDIERER},
            {"schluessel": "uhrzeit", "beschriftung": "Uhrzeit",
             "pruefer": h.UHRZEIT_VALIDIERER, "hinweis": "HH:MM, z. B. 09:00"},
            {"schluessel": "verein", "beschriftung": "Verein",
             "hinweis": "Kürzel, z. B. AC, MSC, MSG, MCH"},
            {"schluessel": "ort", "beschriftung": "Ort"},
            {"schluessel": "link", "beschriftung": "Maps-Link",
             "pruefer": h.LINK_VALIDIERER,
             "hinweis": "bereits bekannt: " + (", ".join(orte[:3]) or "noch nichts")},
            {"schluessel": "pdf", "beschriftung": "PDF-Pfad", "pflicht": False,
             "hinweis": "leer lassen, wenn die Ausschreibung noch fehlt"},
        ]

    def _zu_werten(self, zeile):
        teile = (zeile.split(";") + [""] * 8)[:8]
        monat = tv.MONAT_ALIASE.get(teile[1].strip().lower())
        return {"tag": teile[0], "monat": tv.MONATE_DE[monat[0] - 1] if monat else "",
                "jahr": teile[2], "uhrzeit": teile[3], "verein": teile[4],
                "ort": teile[5], "link": teile[6], "pdf": teile[7]}

    def _zu_zeile(self, werte):
        monat_nr, monat_en = tv.MONAT_ALIASE[werte["monat"].lower()]
        try:
            date(int(werte["jahr"]), monat_nr, int(werte["tag"]))
        except ValueError:
            messagebox.showerror(
                "Kein gültiges Datum",
                f"{werte['tag']}.{monat_nr}.{werte['jahr']} gibt es im Kalender nicht.")
            return None

        pfad, korrekturen = h.normalisiere_medienpfad(werte["pdf"], praefix="")
        if korrekturen:
            messagebox.showinfo("Pfad angepasst", "\n".join(korrekturen) + f"\n\n{pfad}")

        return ";".join([werte["tag"].zfill(2), monat_en, werte["jahr"], werte["uhrzeit"],
                         werte["verein"], werte["ort"], werte["link"], pfad])

    def _speichern(self, zeilen, neue_zeile, ersetze=None):
        if ersetze is not None:
            del zeilen[ersetze]
        # Chronologisch einsortieren, damit die Datei der Saison folgt
        stelle = h.einfuege_position([tv.termin_schluessel(z) for z in zeilen],
                                     tv.termin_schluessel(neue_zeile), absteigend=False)
        zeilen.insert(stelle, neue_zeile)
        h.schreibe_zeilen(self._datei(), zeilen)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def neu(self):
        zeilen = self._zeilen()
        werte = B.frage_formular(
            self.rahmen, self.s, f"Neuer {self.sportart.get()}-Termin", self._felder(zeilen),
            einleitung="Der Termin wird automatisch an die richtige Stelle der Saison "
                       "einsortiert — um die Reihenfolge musst du dich nicht kümmern.")
        if not werte:
            return
        zeile = self._zu_zeile(werte)
        if zeile:
            self._speichern(zeilen, zeile)

    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        zeilen = self._zeilen()
        werte = B.frage_formular(
            self.rahmen, self.s, "Termin bearbeiten", self._felder(zeilen),
            self._zu_werten(zeilen[nummer]),
            einleitung="Wird das Datum geändert, rutscht der Termin an die passende Stelle.")
        if not werte:
            return
        zeile = self._zu_zeile(werte)
        if zeile:
            self._speichern(zeilen, zeile, ersetze=nummer)

    def loeschen(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        zeilen = self._zeilen()
        if not messagebox.askyesno("Termin löschen",
                                   f"{tv.beschreibe_termin(zeilen[nummer])}\n\n"
                                   "Wirklich löschen?"):
            return
        del zeilen[nummer]
        h.schreibe_zeilen(self._datei(), zeilen)
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Jahresarchiv
# ------------------------------------------------------------------

class ArchivSeite(Seite):
    titel = "Jahresarchiv pflegen"
    untertitel = "Die aufklappbaren Saison-Kästen auf der Archiv-Seite mit ihren PDFs."

    def baue(self):
        self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Eintrag hinzufügen", self.eintrag_neu)
        self.knopf("Neue Saison", self.saison_neu, "haupt")
        self.baum = None

    def _jahre(self):
        return archiv_pflege.parse_jahre(archiv_pflege.lade_html())

    def aktualisieren(self):
        self.leeren()
        jahre = self._jahre()

        B.abschnitt(self.inhalt, self.s, "Saisons",
                    f"{len(jahre)} Saison(s) · "
                    f"{sum(len(j['lis']) for j in jahre)} Einträge insgesamt")

        if not jahre:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Noch keine Saison angelegt.",
                    "Oben rechts auf „Neue Saison“.")
            self.baum = None
            return

        huelle = tk.Frame(self.inhalt, bg=B.FARBEN["grund"])
        huelle.pack(fill="both", expand=True)

        self.baum = ttk.Treeview(huelle, columns=("ziel",), show="tree headings", height=14)
        self.baum.heading("#0", text="SAISON / EINTRAG")
        self.baum.heading("ziel", text="PDF-DATEI")
        self.baum.column("#0", width=340)
        self.baum.column("ziel", width=300)
        leiste = ttk.Scrollbar(huelle, orient="vertical", command=self.baum.yview)
        self.baum.configure(yscrollcommand=leiste.set)
        leiste.pack(side="right", fill="y")
        self.baum.pack(side="left", fill="both", expand=True)

        for nummer, jahr in enumerate(jahre):
            knoten = self.baum.insert(
                "", "end", iid=f"j{nummer}",
                text=f"Saison {jahr['jahr']}   ({len(jahr['lis'])})", open=True)
            for lauf, (href, text) in enumerate(jahr["lis"]):
                fehlt = "" if archiv_pflege.pruefe_pdf_existiert(href) else "   (fehlt)"
                self.baum.insert(knoten, "end", iid=f"j{nummer}e{lauf}", text="  " + text,
                                 values=(os.path.basename(href) + fehlt,))

        self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

    def _auswahl(self):
        """(jahr_nummer, eintrag_nummer oder None) - None ohne Auswahl."""
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Nichts gewählt",
                                "Bitte zuerst eine Saison oder einen Eintrag anklicken.")
            return None
        kennung = self.baum.selection()[0]
        if "e" in kennung:
            jahr, eintrag = kennung[1:].split("e")
            return int(jahr), int(eintrag)
        return int(kennung[1:]), None

    def _eintrag_felder(self):
        return [
            {"schluessel": "text", "beschriftung": "Beschriftung",
             "hinweis": "z. B. „BKC Gesamtwertung 2026 (PDF)“"},
            {"schluessel": "pfad", "beschriftung": "Pfad zur PDF",
             "hinweis": "ab /pages/ gerechnet, also mit ../ am Anfang"},
        ]

    def _liste_schreiben(self, jahre, nummer, lis):
        """Ersetzt den HTML-Block einer Saison durch die neue Eintragsliste."""
        html = archiv_pflege.lade_html()
        block = archiv_pflege.baue_details_block(jahre[nummer]["jahr"], lis)
        archiv_pflege.speichere_html(
            archiv_pflege.ersetze_block(html, jahre[nummer]["match"], block))
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def saison_neu(self):
        jahre = self._jahre()
        jahr_jetzt = str(date.today().year)

        werte = B.frage_formular(
            self.rahmen, self.s, "Neue Saison anlegen",
            [{"schluessel": "jahr", "beschriftung": "Jahr", "pruefer": h.JAHR_VALIDIERER}]
            + self._eintrag_felder(),
            {"jahr": jahr_jetzt,
             "text": f"BKC Gesamtwertung {jahr_jetzt} (PDF)",
             "pfad": f"../media/dokumente/archiv/{jahr_jetzt}/"
                     f"BKC_Gesamtauswertung_{jahr_jetzt}.pdf"},
            einleitung="Die Saison wird nach Jahr einsortiert — die neueste steht oben. "
                       "Ein erster Eintrag gehört gleich dazu.")
        if not werte:
            return

        if any(j["jahr"] == werte["jahr"] for j in jahre):
            if not messagebox.askyesno(
                    "Saison gibt es schon",
                    f"Saison {werte['jahr']} steht bereits im Archiv.\n\n"
                    "Trotzdem einen zweiten Kasten mit diesem Jahr anlegen?"):
                return

        pfad, _ = h.normalisiere_medienpfad(werte["pfad"], praefix="../")
        block = archiv_pflege.baue_details_block(werte["jahr"], [(pfad, werte["text"])])
        html = archiv_pflege.lade_html()

        stelle = h.einfuege_position([(int(j["jahr"]),) for j in jahre],
                                     (int(werte["jahr"]),), absteigend=True)
        if stelle < len(jahre):
            anker = jahre[stelle]["match"].start()
            while anker > 0 and html[anker - 1] in " \t":
                anker -= 1
            neu = html[:anker] + block + "\r\n\r\n" + html[anker:]
        elif jahre:
            ende = jahre[-1]["match"].end()
            neu = html[:ende] + "\r\n\r\n" + block + html[ende:]
        else:
            pos = html.find(archiv_pflege.LISTE_ANKER)
            if pos == -1:
                messagebox.showerror("Nicht möglich",
                                     "Der Anker für die Archiv-Liste wurde nicht gefunden.")
                return
            einfuege = html.find("\r\n", pos) + 2
            neu = html[:einfuege] + block + "\r\n\r\n" + html[einfuege:]

        archiv_pflege.speichere_html(neu)
        os.makedirs(os.path.join(archiv_pflege.ARCHIV_MEDIA_DIR, werte["jahr"]), exist_ok=True)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def eintrag_neu(self):
        auswahl = self._auswahl()
        if not auswahl:
            return
        nummer, _ = auswahl
        jahre = self._jahre()
        jahr = jahre[nummer]["jahr"]

        werte = B.frage_formular(
            self.rahmen, self.s, f"Eintrag für Saison {jahr}", self._eintrag_felder(),
            {"pfad": f"../media/dokumente/archiv/{jahr}/BKC_Gesamtauswertung_{jahr}.pdf"})
        if not werte:
            return
        pfad, _ = h.normalisiere_medienpfad(werte["pfad"], praefix="../")
        self._liste_schreiben(jahre, nummer,
                              list(jahre[nummer]["lis"]) + [(pfad, werte["text"])])

    def bearbeiten(self):
        auswahl = self._auswahl()
        if not auswahl:
            return
        nummer, eintrag = auswahl
        if eintrag is None:
            messagebox.showinfo(
                "Saison gewählt",
                "Zum Ändern bitte einen einzelnen Eintrag anklicken.\n\n"
                "Eine ganze Saison lässt sich nur anlegen oder löschen.")
            return

        jahre = self._jahre()
        href, text = jahre[nummer]["lis"][eintrag]
        werte = B.frage_formular(self.rahmen, self.s, "Eintrag bearbeiten",
                                 self._eintrag_felder(), {"text": text, "pfad": href})
        if not werte:
            return
        pfad, _ = h.normalisiere_medienpfad(werte["pfad"], praefix="../")
        lis = list(jahre[nummer]["lis"])
        lis[eintrag] = (pfad, werte["text"])
        self._liste_schreiben(jahre, nummer, lis)

    def loeschen(self):
        auswahl = self._auswahl()
        if not auswahl:
            return
        nummer, eintrag = auswahl
        jahre = self._jahre()

        if eintrag is not None:
            _, text = jahre[nummer]["lis"][eintrag]
            if not messagebox.askyesno("Eintrag löschen", f"{text}\n\nWirklich löschen?"):
                return
            lis = list(jahre[nummer]["lis"])
            del lis[eintrag]
            if not lis:
                messagebox.showinfo(
                    "Letzter Eintrag",
                    "Das war der letzte Eintrag dieser Saison — der Kasten wird "
                    "mit entfernt.")
                self._saison_entfernen(jahre, nummer)
            else:
                self._liste_schreiben(jahre, nummer, lis)
            return

        jahr = jahre[nummer]
        if not messagebox.askyesno(
                "Ganze Saison löschen",
                f"Saison {jahr['jahr']} mit allen {len(jahr['lis'])} Einträgen.\n\n"
                "Die PDF-Dateien unter media/ bleiben liegen — nur der Kasten auf der "
                "Seite verschwindet.\n\nWirklich löschen?"):
            return
        self._saison_entfernen(jahre, nummer)

    def _saison_entfernen(self, jahre, nummer):
        html = archiv_pflege.lade_html()
        treffer = jahre[nummer]["match"]
        start, ende = treffer.start(), treffer.end()
        while start > 0 and html[start - 1] in " \t":
            start -= 1
        # Genau EINE angrenzende Leerzeile mitnehmen, damit der Abstand stimmt
        if html[ende:ende + 4] == "\r\n\r\n":
            ende += 4
        elif html[:start].endswith("\r\n\r\n"):
            start -= 4
        archiv_pflege.speichere_html(html[:start] + html[ende:])
        self.aktualisieren()
        self.app.fuss_auffrischen()
