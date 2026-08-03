# -*- coding: utf-8 -*-
"""
Die einzelnen Seiten der Fenster-Oberflaeche.

Jede Seite ist eine Klasse mit Titel, Aufbau und einer aktualisieren()-
Methode. Sie rufen dieselben Funktionen auf wie die Terminal-Werkzeuge -
die Logik steht weiterhin nur an einer Stelle.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import functools
import os
import shutil
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aenderungsprotokoll
import archiv_pflege
import ausschreibung_pdf
import fenster_bausteine as B
import medien_aufraeumen
import pflege_hilfen as h
import pruefe_seite
import termine_verwalten as tv
import uebersicht
import vorschau

ROOT = h.ROOT


# ------------------------------------------------------------------
# Grundgeruest
# ------------------------------------------------------------------

class Seite:
    """Basis: Kopfzeile mit Titel und Knoepfen, darunter ein rollbarer Bereich."""

    titel = ""
    untertitel = ""

    def __init__(self, app, eltern):
        self.app = app
        self.s = app.schriften
        self.rahmen = tk.Frame(eltern, bg=B.FARBEN["grund"])

        self._kopfzeile()
        self.fest = tk.Frame(self.rahmen, bg=B.FARBEN["grund"])
        self.fest.pack(fill="x", padx=18)

        huelle = tk.Frame(self.rahmen, bg=B.FARBEN["grund"])
        huelle.pack(fill="both", expand=True, padx=18, pady=(14, 0))
        self.leinwand, self.inhalt, _ = B.rollbereich(huelle)

        self.baue()

    def _kopfzeile(self):
        kopf = tk.Frame(self.rahmen, bg=B.FARBEN["grund"])
        kopf.pack(fill="x", padx=18, pady=(18, 12))

        # Erst die Knopfleiste packen: sie bekommt so genau den Platz, den sie
        # braucht, und der Titel nimmt sich den Rest (sonst wird rechts abgeschnitten).
        self.aktionen = tk.Frame(kopf, bg=B.FARBEN["grund"])
        self.aktionen.pack(side="right", anchor="n")

        links = tk.Frame(kopf, bg=B.FARBEN["grund"])
        links.pack(side="left", fill="x", expand=True)
        tk.Label(links, text=self.titel, bg=B.FARBEN["grund"], fg=B.FARBEN["text"],
                 font=self.s.titel, anchor="w").pack(anchor="w")
        if self.untertitel:
            tk.Label(links, text=self.untertitel, bg=B.FARBEN["grund"],
                     fg=B.FARBEN["gedimmt"], font=self.s.klein, anchor="w",
                     justify="left", wraplength=520).pack(anchor="w")

    def knopf(self, text, befehl, art="neben"):
        k = B.knopf(self.aktionen, text, befehl, self.s, art)
        k.pack(side="right", padx=(6, 0))
        return k

    def leeren(self):
        for kind in self.inhalt.winfo_children():
            kind.destroy()

    def baue(self):
        """Einmaliger Aufbau - Unterklassen ueberschreiben das."""

    def aktualisieren(self):
        """Bei jedem Aufruf der Seite - Unterklassen ueberschreiben das."""

    def zeigen(self):
        self.rahmen.pack(fill="both", expand=True)
        self.aktualisieren()

    def verbergen(self):
        self.rahmen.pack_forget()

    # -------------------------------------------------- Tabellen
    def tabelle(self, eltern, spalten, breiten, hoehe=9, zeilenzahl=None):
        huelle = tk.Frame(eltern, bg=B.FARBEN["grund"])
        huelle.pack(fill="both", expand=True)

        baum = ttk.Treeview(huelle, columns=spalten, show="headings", height=hoehe)
        # Bildlaufleiste nur, wenn wirklich mehr Zeilen da sind als Platz
        if zeilenzahl is None or zeilenzahl > hoehe:
            leiste = ttk.Scrollbar(huelle, orient="vertical", command=baum.yview)
            baum.configure(yscrollcommand=leiste.set)
            leiste.pack(side="right", fill="y")
        baum.pack(side="left", fill="both", expand=True)

        for spalte, breite in zip(spalten, breiten):
            baum.heading(spalte, text=spalte.upper())
            baum.column(spalte, width=breite,
                        anchor="e" if spalte in ("Größe",) else "w")
        return baum


# ------------------------------------------------------------------
# Uebersicht
# ------------------------------------------------------------------

class UebersichtSeite(Seite):
    titel = "Was steht an?"
    untertitel = "Alles, was gerade Aufmerksamkeit braucht — beim Start automatisch geprüft."

    def baue(self):
        self.knopf("Neu prüfen", self.aktualisieren)
        self.tafel = tk.Frame(self.fest, bg=B.FARBEN["tief"])
        self.tafel.pack(fill="x")

    def aktualisieren(self):
        self._boxentafel()
        self.leeren()

        B.abschnitt(self.inhalt, self.s, "Braucht Aufmerksamkeit",
                    "nach Dringlichkeit sortiert")

        # pruefe_veroeffentlichung faellt weg - das steht in der Fussleiste
        hinweise = uebersicht.sammle(ausser={"pruefe_veroeffentlichung"})
        offen = [e for e in hinweise if e[0] != uebersicht.LAGE]

        for stufe, text, wohin, werkzeug in offen:
            B.karte(self.inhalt, self.s, stufe, text,
                    None if werkzeug else wohin,
                    "Öffnen" if werkzeug else None,
                    (lambda w=werkzeug: self.app.oeffne(w)) if werkzeug else None)

        if not offen:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Nichts Offenes — alles auf Stand.")

    def _boxentafel(self):
        for kind in self.tafel.winfo_children():
            kind.destroy()

        innen = tk.Frame(self.tafel, bg=B.FARBEN["tief"])
        innen.pack(fill="x", padx=20, pady=14)

        for rennen in uebersicht.naechste_rennen():
            block = tk.Frame(innen, bg=B.FARBEN["tief"])
            block.pack(side="left", padx=(0, 34))
            tk.Label(block, text=f"NÄCHSTES RENNEN — {rennen['sportart'].upper()}",
                     bg=B.FARBEN["tief"], fg=B.FARBEN["rail_text"],
                     font=self.s.label).pack(anchor="w")

            if rennen["tage"] is None:
                tk.Label(block, text="—", bg=B.FARBEN["tief"], fg=B.FARBEN["gelb"],
                         font=self.s.zahl).pack(anchor="w")
                tk.Label(block, text="kein Termin mehr eingetragen", bg=B.FARBEN["tief"],
                         fg=B.FARBEN["rail_text"], font=self.s.klein).pack(anchor="w")
            else:
                zeile = tk.Frame(block, bg=B.FARBEN["tief"])
                zeile.pack(anchor="w")
                tk.Label(zeile, text=str(rennen["tage"]), bg=B.FARBEN["tief"],
                         fg=B.FARBEN["gelb"], font=self.s.zahl).pack(side="left")
                tk.Label(zeile, text="  Tage", bg=B.FARBEN["tief"],
                         fg=B.FARBEN["rail_text"], font=self.s.klein).pack(
                             side="left", anchor="s", pady=(0, 5))
                tk.Label(block, text=rennen["deutsch"], bg=B.FARBEN["tief"],
                         fg=B.FARBEN["rail_text"], font=self.s.klein).pack(anchor="w")

        stand = tk.Frame(innen, bg=B.FARBEN["tief"])
        stand.pack(side="left")
        tk.Label(stand, text="ZULETZT VERÖFFENTLICHT", bg=B.FARBEN["tief"],
                 fg=B.FARBEN["rail_text"], font=self.s.label).pack(anchor="w")
        tk.Label(stand, text=self._letzte_veroeffentlichung(), bg=B.FARBEN["tief"],
                 fg=B.FARBEN["weiss"], font=self.s.kopf).pack(anchor="w", pady=(6, 0))

    def _letzte_veroeffentlichung(self):
        text = uebersicht._git("log", "-1", "--format=%cd", "--date=short")
        if not text:
            return "unbekannt"
        try:
            wann = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return text
        tage = (date.today() - wann).days
        seit = "heute" if tage == 0 else ("gestern" if tage == 1 else f"vor {tage} Tagen")
        return f"{wann.strftime('%d.%m.%Y')}  ({seit})"


# ------------------------------------------------------------------
# Webseite pruefen
# ------------------------------------------------------------------

class PruefenSeite(Seite):
    titel = "Webseite prüfen"
    untertitel = ("Findet das, was auf GitHub Pages kaputt wäre, hier aber "
                  "funktioniert — und alles, was Besucher oder Google stört.")

    def baue(self):
        self.extern = tk.BooleanVar(value=False)
        self.knopf("Prüfung starten", self.starten, "haupt")
        tk.Checkbutton(self.aktionen, text="Internet-Links",
                       variable=self.extern, bg=B.FARBEN["grund"],
                       fg=B.FARBEN["text"], font=self.s.klein,
                       activebackground=B.FARBEN["grund"], selectcolor=B.FARBEN["karte"],
                       cursor="hand2").pack(side="right", padx=(0, 10))
        self.laeuft = False

    def aktualisieren(self):
        if not self.inhalt.winfo_children():
            self.leeren()
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Noch nicht geprüft.",
                    "Oben rechts auf „Prüfung starten“ — dauert ohne Internet-Links "
                    "unter einer Sekunde.")

    def starten(self):
        if self.laeuft:
            return
        self.laeuft = True
        self.leeren()
        B.karte(self.inhalt, self.s, uebersicht.INFO, "Prüfe …",
                "Bei eingeschalteter Internet-Prüfung dauert das ein paar Sekunden.")

        extern = self.extern.get()

        def arbeit():
            gruppen = [
                (0, "Tote Verweise (Link führt ins Leere)", pruefe_seite.pruefe_verweise()[0]),
                (0, "Falsche Groß-/Kleinschreibung (bricht erst auf dem Server)",
                 pruefe_seite.pruefe_verweise()[1]),
                (0, "Build-Schritt fehlt (Änderung ist online unsichtbar)",
                 pruefe_seite.pruefe_build_aktuell()),
                (0, "Externe Dienste ohne Klaro-Eintrag (DSGVO)",
                 pruefe_seite.pruefe_drittanbieter()),
                (1, "Externe Links ohne Antwort",
                 pruefe_seite.pruefe_externe_links(fortschritt=False) if extern else []),
                (1, "Dieselbe id mehrfach auf einer Seite", pruefe_seite.pruefe_doppelte_ids()),
                (1, "Bilder ohne alt-Text", pruefe_seite.pruefe_alt_texte()),
                (1, "Titel, Beschreibung, Vorschaubild", pruefe_seite.pruefe_meta()),
                (1, "Angekündigte PDFs noch nicht hochgeladen",
                 pruefe_seite.pruefe_angekuendigte_pdfs()),
            ]
            return gruppen

        B.im_hintergrund(self.rahmen, arbeit, self._fertig)

    def _fertig(self, gruppen):
        self.laeuft = False
        self.leeren()

        gefunden = [(stufe, name, eintraege) for stufe, name, eintraege in gruppen if eintraege]
        if not gefunden:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Alles in Ordnung — keine Probleme gefunden.",
                    "Weder tote Verweise noch Schreibweise, Build, alt-Texte oder Meta-Angaben.")
            return

        fehler = sum(1 for stufe, _, _ in gefunden if stufe == 0)
        B.abschnitt(self.inhalt, self.s, "Ergebnis",
                    f"{fehler} Fehlergruppe(n), {len(gefunden) - fehler} Hinweisgruppe(n)")

        for stufe, name, eintraege in gefunden:
            B.karte(self.inhalt, self.s, stufe, f"{name} — {len(eintraege)}")
            kasten = tk.Text(self.inhalt, height=min(len(eintraege), 7), font=self.s.daten,
                             wrap="none", bg=B.FARBEN["karte"], fg=B.FARBEN["gedimmt"],
                             relief="solid", bd=1, padx=10, pady=6)
            kasten.pack(fill="x", pady=(0, 14))
            kasten.insert("1.0", "\n".join(str(e) for e in eintraege))
            kasten.configure(state="disabled")


# ------------------------------------------------------------------
# Medien aufraeumen
# ------------------------------------------------------------------

class MedienSeite(Seite):
    titel = "Medien aufräumen"
    untertitel = ("Was unter media/ niemand mehr braucht und was unnötig groß ist. "
                  "Gelöschtes lässt sich über „Rückgängig“ zurückholen.")

    def baue(self):
        self.knopf("Verwaiste löschen", self.loeschen, "warnung")
        self.knopf("Neu einlesen", self.aktualisieren)
        self.verwaist = []

    def aktualisieren(self):
        self.leeren()
        B.karte(self.inhalt, self.s, uebersicht.INFO, "Lese media/ ein …")
        B.im_hintergrund(self.rahmen, self._sammeln, self._zeigen)

    def _sammeln(self):
        dateien = medien_aufraeumen.medien_dateien()
        seiten_text, werkzeug_text = medien_aufraeumen.text_inhalte()
        verwaist, nur_werkzeug = medien_aufraeumen.finde_verwaiste(
            dateien, seiten_text, werkzeug_text)
        return {
            "dateien": dateien,
            "verwaist": verwaist,
            "nur_werkzeug": nur_werkzeug,
            "zu_gross": medien_aufraeumen.finde_zu_grosse(dateien),
            "ohne_webp": medien_aufraeumen.finde_ohne_webp(dateien),
        }

    def _zeigen(self, daten):
        self.leeren()
        self.verwaist = daten["verwaist"]

        gesamt = sum(os.path.getsize(p) for p in daten["dateien"]) / 1024 / 1024
        B.abschnitt(self.inhalt, self.s, "Bestand",
                    f"{len(daten['dateien'])} Dateien · {gesamt:.1f} MB")

        zeilen = []
        for pfad in daten["verwaist"]:
            zeilen.append((medien_aufraeumen.kurz(pfad), "Verwaist — von keiner Seite verlinkt",
                           self._groesse(pfad)))
        for pfad in daten["nur_werkzeug"]:
            zeilen.append((medien_aufraeumen.kurz(pfad),
                           "Nur noch im Werkzeug eingetragen", self._groesse(pfad)))
        for pfad, kb, art in daten["zu_gross"]:
            zeilen.append((medien_aufraeumen.kurz(pfad), f"Zu groß ({art})",
                           self._groesse(pfad)))
        for pfad in daten["ohne_webp"]:
            zeilen.append((medien_aufraeumen.kurz(pfad), "Ohne WebP-Fassung",
                           self._groesse(pfad)))

        if not zeilen:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Nichts aufzuräumen — jede Datei wird gebraucht und ist handlich.")
            return

        baum = self.tabelle(self.inhalt, ("Datei", "Zustand", "Größe"),
                            (330, 250, 80), hoehe=min(len(zeilen), 12),
                            zeilenzahl=len(zeilen))
        for zeile in zeilen:
            baum.insert("", "end", values=zeile)

        if daten["verwaist"]:
            frei = sum(os.path.getsize(p) for p in daten["verwaist"]) // 1024
            tk.Label(self.inhalt,
                     text=f"{len(daten['verwaist'])} verwaiste Datei(en) — "
                          f"{frei} KB würden frei.",
                     bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                     font=self.s.klein).pack(anchor="w", pady=(10, 0))

        videos = [(p, kb) for p, kb, art in daten["zu_gross"] if art == "Video"]
        if videos:
            self._video_tipps(videos)

    def _groesse(self, pfad):
        kb = os.path.getsize(pfad) / 1024
        return f"{kb/1024:.1f} MB" if kb > 1024 else f"{kb:.0f} KB"

    def _video_tipps(self, videos):
        tk.Frame(self.inhalt, bg=B.FARBEN["linie"], height=1).pack(fill="x", pady=16)
        B.abschnitt(self.inhalt, self.s, "Video kleiner bekommen")
        tk.Label(self.inhalt, justify="left", anchor="w", wraplength=640,
                 bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"], font=self.s.klein,
                 text=("Ein Video mit autoplay lädt JEDER Besucher komplett, auch am "
                       "Handy. Reihenfolge: Tonspur raus (bei „muted“ hört sie ohnehin "
                       "niemand), neu kodieren, zusätzlich ein modernes Format anbieten "
                       "(AV1 spart gegenüber H.264 etwa die Hälfte). Dafür wird ffmpeg "
                       "gebraucht — kostenlos von ffmpeg.org.")).pack(anchor="w", pady=(0, 8))

        befehle = []
        for pfad, _ in videos:
            stamm = os.path.splitext(medien_aufraeumen.kurz(pfad))[0]
            kurz = medien_aufraeumen.kurz(pfad)
            befehle += [
                f"ffmpeg -i {kurz} -c:v libsvtav1 -crf 34 -preset 6 -an {stamm}.av1.mp4",
                f"ffmpeg -i {kurz} -c:v libvpx-vp9 -crf 34 -b:v 0 -an {stamm}.webm",
                f"ffmpeg -i {kurz} -c:v libx264 -crf 24 -preset slow -an "
                f"-movflags +faststart {stamm}.klein.mp4",
            ]

        kasten = tk.Text(self.inhalt, height=len(befehle), font=self.s.daten, wrap="none",
                         bg=B.FARBEN["karte"], fg=B.FARBEN["text"],
                         relief="solid", bd=1, padx=10, pady=6)
        kasten.pack(fill="x")
        kasten.insert("1.0", "\n".join(befehle))
        kasten.configure(state="disabled")

    def loeschen(self):
        if not self.verwaist:
            messagebox.showinfo("Nichts zu löschen",
                                "Es gibt keine verwaisten Dateien.")
            return

        liste = "\n".join("  " + medien_aufraeumen.kurz(p) for p in self.verwaist[:12])
        rest = f"\n  … und {len(self.verwaist) - 12} weitere" if len(self.verwaist) > 12 else ""
        if not messagebox.askyesno(
                "Verwaiste Dateien löschen",
                f"{len(self.verwaist)} Datei(en) werden gelöscht:\n\n{liste}{rest}\n\n"
                "Jede wird vorher gesichert und lässt sich über „Letzte Änderung "
                "rückgängig“ zurückholen.\n\nFortfahren?"):
            return

        for pfad in self.verwaist:
            h.sicherung_anlegen(pfad)
            os.remove(pfad)

        messagebox.showinfo("Gelöscht",
                            f"{len(self.verwaist)} Datei(en) gelöscht (gesichert).")
        self.aktualisieren()
        self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Ausschreibungs-PDF
# ------------------------------------------------------------------

class PdfSeite(Seite):
    titel = "Ausschreibungs-PDF einpflegen"
    untertitel = ("Beim Eintragen eines Termins wird der PDF-Pfad angekündigt, die Datei "
                  "kommt oft Wochen später. Bis dahin bleibt der Download-Button unsichtbar.")

    def baue(self):
        self.knopf("PDF auswählen …", self.hochladen, "haupt")
        self.knopf("Namen aufräumen", self.namen_aufraeumen)
        self.gruppen = {}
        self.baum = None

    def aktualisieren(self):
        self.leeren()
        self.gruppen = ausschreibung_pdf.fehlende_ausschreibungen()
        alle = ausschreibung_pdf.lade_termine()
        fehlend = sum(len(v) for v in self.gruppen.values())

        B.abschnitt(self.inhalt, self.s, "Termine",
                    f"{len(alle)} insgesamt · {fehlend} warten auf ihre PDF")

        if not self.gruppen:
            B.karte(self.inhalt, self.s, uebersicht.INFO,
                    "Alle angekündigten PDFs sind vorhanden.",
                    "Eine PDF zu einem Termin hinzufügen geht über „Renntermine“.")
            return

        self.baum = self.tabelle(self.inhalt, ("Erwartete Datei", "Gehört zu", "Zustand"),
                                 (300, 280, 110), hoehe=min(len(self.gruppen), 10),
                                 zeilenzahl=len(self.gruppen))
        for pfad, termine in self.gruppen.items():
            heikel = not ausschreibung_pdf.SAUBER_MUSTER.fullmatch(pfad)
            wann = ", ".join(t["zeile"].split(";")[0] + "." + t["zeile"].split(";")[1][:3]
                             for t in termine)
            self.baum.insert("", "end", iid=pfad,
                             values=(os.path.basename(pfad),
                                     f"{termine[0]['sportart']} · {wann}",
                                     "Name heikel" if heikel else "Fehlt"))

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Zeile auswählen, dann oben auf „PDF auswählen …“. Die Datei wird "
                       "an die erwartete Stelle kopiert und richtig benannt — "
                       "abtippen ist nicht nötig.")).pack(anchor="w", pady=(12, 0))

    def _auswahl(self):
        if not self.baum:
            return None
        markiert = self.baum.selection()
        if markiert:
            return markiert[0]
        if len(self.gruppen) == 1:
            return next(iter(self.gruppen))
        messagebox.showinfo("Keine Zeile gewählt",
                            "Bitte zuerst in der Liste anklicken, welche PDF gemeint ist.")
        return None

    def hochladen(self):
        if not self.gruppen:
            messagebox.showinfo("Nichts offen", "Es fehlt keine PDF.")
            return

        zielpfad = self._auswahl()
        if not zielpfad:
            return
        betroffene = self.gruppen[zielpfad]

        quelle = filedialog.askopenfilename(
            title=f"PDF für {os.path.basename(zielpfad)} auswählen",
            filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")])
        if not quelle:
            return

        if not ausschreibung_pdf.ist_pdf(quelle):
            if not messagebox.askyesno(
                    "Keine PDF?",
                    "Der Inhalt sieht nicht nach einer PDF-Datei aus.\n\nTrotzdem verwenden?"):
                return

        neuer_pfad = zielpfad
        if not ausschreibung_pdf.SAUBER_MUSTER.fullmatch(zielpfad):
            vorschlag = ausschreibung_pdf.sauberer_name(zielpfad)
            if messagebox.askyesno(
                    "Dateiname aufräumen?",
                    f"Der angekündigte Name enthält Zeichen, die beim Hochladen leicht "
                    f"schiefgehen:\n\n  bisher:  {zielpfad}\n  sauber:  {vorschlag}\n\n"
                    "Sauberen Namen verwenden? Der Termin-Eintrag wird mit geändert."):
                neuer_pfad = vorschlag

        ziel = os.path.join(ROOT, neuer_pfad.lstrip("/"))
        if os.path.isfile(ziel):
            if not messagebox.askyesno(
                    "Datei ersetzen?",
                    f"An dieser Stelle liegt bereits eine Datei:\n\n{neuer_pfad}\n\nErsetzen?"):
                return
            h.sicherung_anlegen(ziel)

        try:
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            shutil.copy2(quelle, ziel)
        except OSError as fehler:
            messagebox.showerror("Kopieren fehlgeschlagen", str(fehler))
            return

        if neuer_pfad != zielpfad:
            ausschreibung_pdf.schreibe_pdf_pfad(betroffene, neuer_pfad)

        rennen = "\n".join("  " + t["sportart"] + ": " +
                           __import__("termine_verwalten").beschreibe_termin(t["zeile"])
                           for t in betroffene)
        messagebox.showinfo(
            "Eingepflegt",
            f"{os.path.getsize(ziel)//1024} KB kopiert nach\n{neuer_pfad}\n\n"
            f"Der Download-Button ist jetzt sichtbar bei:\n{rennen}")
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def namen_aufraeumen(self):
        treffer = ausschreibung_pdf.heikle_namen()
        if not treffer:
            messagebox.showinfo("Alles sauber",
                                "Alle PDF-Pfade sind so geschrieben, dass der "
                                "GitHub-Server sie sicher findet.")
            return

        geaendert = 0
        for pfad, termine in treffer.items():
            vorschlag = ausschreibung_pdf.sauberer_name(pfad)
            vorhanden = os.path.join(ROOT, pfad.lstrip("/"))
            zusatz = ("\n\nDie Datei ist noch nicht hochgeladen — es ändert sich nur "
                      "der Eintrag im Termin.") if not os.path.isfile(vorhanden) else ""
            if not messagebox.askyesno(
                    "Umbenennen?",
                    f"  bisher:  {pfad}\n  sauber:  {vorschlag}\n\n"
                    f"Betrifft {len(termine)} Termin(e).{zusatz}"):
                continue

            if os.path.isfile(vorhanden):
                neu = os.path.join(ROOT, vorschlag.lstrip("/"))
                os.makedirs(os.path.dirname(neu), exist_ok=True)
                h.sicherung_anlegen(vorhanden)
                os.replace(vorhanden, neu)
            ausschreibung_pdf.schreibe_pdf_pfad(termine, vorschlag)
            geaendert += 1

        if geaendert:
            messagebox.showinfo("Fertig", f"{geaendert} Pfad(e) aufgeräumt.")
            self.aktualisieren()
            self.app.fuss_auffrischen()


# ------------------------------------------------------------------
# Vorschau
# ------------------------------------------------------------------

class VorschauSeite(Seite):
    titel = "Vorschau im Browser"
    untertitel = ("Zeigt die Seite so, wie sie online aussieht — nur auf diesem Rechner. "
                  "Es wird nichts veröffentlicht.")

    def baue(self):
        self.server = None
        self.port = None
        self.knopf_start = self.knopf("Vorschau starten", self.umschalten, "haupt")

    def aktualisieren(self):
        self.leeren()

        if self.server:
            adresse = f"http://localhost:{self.port}/"
            B.karte(self.inhalt, self.s, uebersicht.INFO, f"Läuft unter {adresse}",
                    "Nur auf diesem Rechner sichtbar.", "Im Browser öffnen",
                    lambda: webbrowser.open(adresse))
            B.abschnitt(self.inhalt, self.s, "Direkt zu einer Seite")
            for name, pfad in vorschau.SEITEN:
                B.karte(self.inhalt, self.s, 2, name, adresse + pfad, "Öffnen",
                        functools.partial(webbrowser.open, adresse + pfad))
        else:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Vorschau läuft nicht.",
                    "Oben rechts starten — dann öffnet sich der Browser.")

        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Ein Doppelklick auf index.html reicht dafür nicht: der Browser lädt "
                       "die Datei dann über file:// und blockt genau das, was die Seite "
                       "braucht — Countdown, Suche und Live-Timing holen ihre Daten "
                       "nach und blieben leer.\n\n"
                       "Änderungen an HTML und Bildern sieht man sofort nach F5. Bei "
                       "Änderungen an CSS/JS vorher das technische Update laufen lassen, "
                       "sonst zeigt die Vorschau den alten Stand.")
                 ).pack(anchor="w", pady=(14, 0))

    def umschalten(self):
        if self.server:
            self.beenden()
        else:
            self.starten()

    def starten(self):
        self.port = vorschau.freier_port()
        if self.port is None:
            messagebox.showerror(
                "Kein freier Port",
                "Zwischen 8000 und 8019 ist nichts frei.\n\n"
                "Läuft vielleicht noch eine Vorschau in einem anderen Fenster?")
            return

        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", self.port),
            functools.partial(vorschau.Handler, directory=ROOT))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

        self.knopf_start.configure(text="Vorschau beenden")
        self.aktualisieren()
        webbrowser.open(f"http://localhost:{self.port}/")

    def beenden(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.knopf_start.configure(text="Vorschau starten")
        self.aktualisieren()
