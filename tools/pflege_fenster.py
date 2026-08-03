# -*- coding: utf-8 -*-
"""
Die Webseiten-Pflege als Fenster.

Der Rahmen: Seitenleiste links, gewaehlte Seite rechts, Veroeffentlichen
unten. Die Seiten selbst stehen in tools/fenster_seiten.py, die
Bedienelemente in tools/fenster_bausteine.py.

Werkzeuge, die noch keine eigene Fensterseite haben, oeffnen sich
unveraendert in einem eigenen Terminalfenster - es ist dieselbe Datei,
die auch das Menue aufruft.

Ausfuehren: python tools/pflege_fenster.py
(oder per Doppelklick auf webseiten-fenster.bat eine Ebene ueber mch-arbeit/)
"""
import io
import os
import subprocess
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aenderungsprotokoll
import fenster_bausteine as B
import fenster_seiten as S
import fenster_seiten_inhalte as I
import fenster_seiten_personen as P
import fenster_seiten_rest as R
import fenster_seiten_sponsoren as SP
import fenster_seiten_statistik as ST
import fenster_seiten_technik as TE
import fenster_seiten_texte as T
import jaehrliches_update
import pflege_hilfen as h
import pruefe_seite
import update_sitemap

ROOT = h.ROOT
FEHLERDATEI = os.path.join(ROOT, "tools", "letzter-fehler.txt")

# Seiten, die es im Fenster selbst gibt
SEITEN = {
    "uebersicht": S.UebersichtSeite,
    "pruefen":    S.PruefenSeite,
    "medien":     S.MedienSeite,
    "pdf":        S.PdfSeite,
    "vorschau":   S.VorschauSeite,
    "termine":    I.RenntermineSeite,
    "archiv":     I.ArchivSeite,
    "news":       T.NewsSeite,
    "faq":        T.FaqSeite,
    "technik":    TE.TechnikSeite,
    "team":       P.TeamSeite,
    "statistiken": ST.StatistikenSeite,
    "sponsoren":  SP.SponsorenSeite,
    "bilder":     R.BilderSeite,
    "trainingstermine": R.TrainingstermineSeite,
    "rennwochenende":   R.RennwochenendeSeite,
    "saisonwechsel":    R.SaisonwechselSeite,
}

# Werkzeug-Modul -> Fensterseite. Was hier nicht steht, oeffnet sich
# weiterhin im Terminal.
MODUL_ZU_SEITE = {
    "pruefe_seite":      "pruefen",
    "medien_aufraeumen": "medien",
    "ausschreibung_pdf": "pdf",
    "vorschau":          "vorschau",
    "termine_verwalten": "termine",
    "archiv_pflege":     "archiv",
    "news_pflege":       "news",
    "faq_pflege":        "faq",
    "jaehrliches_update": "technik",
    "team_pflege":       "team",
    "statistiken_pflege": "statistiken",
    "sponsoren_pflege":  "sponsoren",
    "bilder_pflege":     "bilder",
    "trainingstermine_import": "trainingstermine",
    "rennwochenende":    "rennwochenende",
    "saisonwechsel":     "saisonwechsel",
}

# Seitenleiste: (Gruppe, [(Beschriftung, Ziel)])
# Ziel: "#name" = Fensterseite, "@name" = Methode, sonst Modulname
WERKZEUGE = [
    ("Übersicht", [
        ("Was steht an?", "#uebersicht"),
    ]),
    ("Inhalte pflegen", [
        ("Live-Timing", "livetiming_sync"),
        ("Nach dem Rennen", "#rennwochenende"),
        ("Renntermine", "#termine"),
        ("Ausschreibungs-PDF", "#pdf"),
        ("Trainingstermine", "#trainingstermine"),
        ("Statistiken", "#statistiken"),
        ("News-Karten", "#news"),
        ("Jahresarchiv", "#archiv"),
        ("Sponsoren & Links", "#sponsoren"),
        ("Vorstand & Trainer", "#team"),
        ("Fragen & Antworten", "#faq"),
        ("Bilder aufnehmen", "#bilder"),
    ]),
    ("Nachsehen", [
        ("Vorschau im Browser", "#vorschau"),
        ("Webseite prüfen", "#pruefen"),
        ("Medien aufräumen", "#medien"),
    ]),
    ("Technik", [
        ("Saisonwechsel", "#saisonwechsel"),
        ("Technisches Update", "#technik"),
        ("Letzte Änderung rückgängig", "@rueckgaengig"),
    ]),
]


def starte_werkzeug(modul):
    """Oeffnet ein Werkzeug in einem eigenen Konsolenfenster."""
    pfad = os.path.join(ROOT, "tools", f"{modul}.py")
    if not os.path.isfile(pfad):
        messagebox.showerror("Nicht gefunden", f"{modul}.py gibt es nicht.")
        return
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)   # nur unter Windows
    try:
        subprocess.Popen([sys.executable, pfad], cwd=ROOT, creationflags=flags)
    except OSError as fehler:
        messagebox.showerror("Start nicht möglich", str(fehler))


def mitschnitt(funktion, *args, **kwargs):
    """Fuehrt eine Terminal-Funktion aus und faengt ihre Ausgabe ein."""
    puffer = io.StringIO()
    try:
        with redirect_stdout(puffer), redirect_stderr(puffer):
            ergebnis = funktion(*args, **kwargs)
    except Exception:
        return None, puffer.getvalue() + "\n" + traceback.format_exc()
    return ergebnis, puffer.getvalue()


class PflegeFenster:

    def __init__(self, wurzel):
        self.wurzel = wurzel
        wurzel.title("MCH Singen — Webseiten-Pflege")
        wurzel.geometry("1100x780")
        wurzel.minsize(940, 620)
        wurzel.configure(bg=B.FARBEN["grund"])

        self.schriften = B.Schriften()
        self._tabellen_stil()

        self.rail_knoepfe = {}
        self.seiten = {}
        self.aktuelle = None

        rahmen = tk.Frame(wurzel, bg=B.FARBEN["grund"])
        rahmen.pack(fill="both", expand=True)

        self._baue_rail(rahmen)

        self.haupt = tk.Frame(rahmen, bg=B.FARBEN["grund"])
        self.haupt.pack(side="left", fill="both", expand=True)

        self._baue_fussleiste()
        self.seitenbereich = tk.Frame(self.haupt, bg=B.FARBEN["grund"])
        self.seitenbereich.pack(fill="both", expand=True)

        self.zeige_seite("uebersicht")
        self.fuss_auffrischen()

    def _tabellen_stil(self):
        stil = ttk.Style()
        if "clam" in stil.theme_names():
            stil.theme_use("clam")     # nur clam laesst sich frei einfaerben
        stil.configure("Treeview",
                       background=B.FARBEN["karte"], fieldbackground=B.FARBEN["karte"],
                       foreground=B.FARBEN["text"], font=self.schriften.text,
                       rowheight=26, borderwidth=1, relief="solid")
        stil.configure("Treeview.Heading", font=self.schriften.label,
                       background=B.FARBEN["erhoben"], foreground=B.FARBEN["gedimmt"],
                       relief="flat", padding=6)
        stil.map("Treeview", background=[("selected", B.FARBEN["blau"])],
                 foreground=[("selected", B.FARBEN["weiss"])])

    # -------------------------------------------------- Seitenleiste
    def _baue_rail(self, eltern):
        rail = tk.Frame(eltern, bg=B.FARBEN["tief"], width=208)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)

        kopf = tk.Frame(rail, bg=B.FARBEN["tief"])
        kopf.pack(fill="x", padx=14, pady=(14, 6))
        tk.Label(kopf, text="MCH", bg=B.FARBEN["gelb"], fg=B.FARBEN["tief"],
                 font=self.schriften.marke, padx=7, pady=4).pack(side="left")
        beschriftung = tk.Frame(kopf, bg=B.FARBEN["tief"])
        beschriftung.pack(side="left", padx=8)
        tk.Label(beschriftung, text="Webseiten-Pflege", bg=B.FARBEN["tief"],
                 fg=B.FARBEN["weiss"], font=self.schriften.kopf).pack(anchor="w")
        tk.Label(beschriftung, text="Arbeitsordner: arbeit", bg=B.FARBEN["tief"],
                 fg=B.FARBEN["rail_text"], font=self.schriften.klein).pack(anchor="w")

        for gruppe, punkte in WERKZEUGE:
            tk.Label(rail, text=gruppe.upper(), bg=B.FARBEN["tief"],
                     fg=B.FARBEN["rail_text"], font=self.schriften.label,
                     anchor="w").pack(fill="x", padx=14, pady=(11, 1))
            for beschriftung, ziel in punkte:
                self._rail_knopf(rail, beschriftung, ziel)

    def _rail_knopf(self, rail, beschriftung, ziel):
        knopf = tk.Label(rail, text="  " + beschriftung, bg=B.FARBEN["tief"],
                         fg=B.FARBEN["rail_text"], font=self.schriften.knopf,
                         anchor="w", padx=11, pady=3, cursor="hand2")
        knopf.pack(fill="x")

        if ziel.startswith("#"):
            self.rail_knoepfe[ziel[1:]] = knopf

        def betreten(_):
            if self.aktuelle != ziel[1:]:
                knopf.configure(bg=B.FARBEN["rail_hell"], fg=B.FARBEN["weiss"])

        def verlassen(_):
            if self.aktuelle != ziel[1:]:
                knopf.configure(bg=B.FARBEN["tief"], fg=B.FARBEN["rail_text"])

        knopf.bind("<Enter>", betreten)
        knopf.bind("<Leave>", verlassen)

        if ziel.startswith("#"):
            knopf.bind("<Button-1>", lambda _: self.zeige_seite(ziel[1:]))
        elif ziel.startswith("@"):
            knopf.bind("<Button-1>", lambda _: getattr(self, ziel[1:])())
        else:
            knopf.bind("<Button-1>", lambda _: starte_werkzeug(ziel))

    # -------------------------------------------------- Seitenwechsel
    def zeige_seite(self, name):
        if name not in SEITEN:
            return
        if self.aktuelle == name:
            self.seiten[name].aktualisieren()
            return

        if self.aktuelle:
            self.seiten[self.aktuelle].verbergen()
            alt = self.rail_knoepfe.get(self.aktuelle)
            if alt:
                alt.configure(bg=B.FARBEN["tief"], fg=B.FARBEN["rail_text"])

        if name not in self.seiten:
            self.seiten[name] = SEITEN[name](self, self.seitenbereich)

        self.aktuelle = name
        neu = self.rail_knoepfe.get(name)
        if neu:
            neu.configure(bg=B.FARBEN["rail_hell"], fg=B.FARBEN["weiss"])
        self.seiten[name].zeigen()

    def oeffne(self, werkzeug):
        """Von den Karten der Uebersicht aus: Fensterseite, wenn es eine
        gibt - sonst das Werkzeug im Terminal."""
        seite = MODUL_ZU_SEITE.get(werkzeug)
        if seite:
            self.zeige_seite(seite)
        else:
            starte_werkzeug(werkzeug)

    # -------------------------------------------------- Fussleiste
    def _baue_fussleiste(self):
        leiste = tk.Frame(self.haupt, bg=B.FARBEN["erhoben"],
                          highlightbackground=B.FARBEN["linie"], highlightthickness=1)
        leiste.pack(fill="x", side="bottom")

        links = tk.Frame(leiste, bg=B.FARBEN["erhoben"])
        links.pack(side="left", padx=18, pady=11)
        self.fuss_titel = tk.Label(links, text="", bg=B.FARBEN["erhoben"],
                                   fg=B.FARBEN["text"], font=self.schriften.kopf, anchor="w")
        self.fuss_titel.pack(anchor="w")
        self.fuss_text = tk.Label(links, text="", bg=B.FARBEN["erhoben"],
                                  fg=B.FARBEN["gedimmt"], font=self.schriften.klein, anchor="w")
        self.fuss_text.pack(anchor="w")

        self.knopf_pushen = B.knopf(leiste, "Veröffentlichen …", self.veroeffentlichen,
                                    self.schriften, "haupt", padx=18, pady=7)
        self.knopf_pushen.pack(side="right", padx=(6, 18), pady=11)

        B.knopf(leiste, "Vorschau im Browser",
                lambda: self.zeige_seite("vorschau"), self.schriften).pack(side="right", pady=11)

    def fuss_auffrischen(self):
        zeilen, _ = mitschnitt(aenderungsprotokoll.sammle)
        zeilen = zeilen or []
        if zeilen:
            self.fuss_titel.configure(text=f"{len(zeilen)} Änderung(en) liegen bereit")
            self.fuss_text.configure(
                text="Noch nichts veröffentlicht — alles liegt im Arbeitsordner")
            self.knopf_pushen.configure(state="normal", bg=B.FARBEN["blau"])
        else:
            self.fuss_titel.configure(text="Nichts zu veröffentlichen")
            self.fuss_text.configure(text="Der Arbeitsordner ist mit der Live-Seite gleich")
            self.knopf_pushen.configure(state="disabled", bg=B.FARBEN["matt"])

    # -------------------------------------------------- Rueckgaengig
    def rueckgaengig(self):
        stand = h.letzte_sicherung()
        if not stand:
            messagebox.showinfo(
                "Nichts rückgängig zu machen",
                "Es liegt keine Sicherung vor.\n\nVor jeder Änderung legt das Werkzeug "
                "automatisch eine an — hier war seitdem noch keine.")
            return

        if not messagebox.askyesno(
                "Rückgängig machen",
                f"{stand['relativ']}\n\nwird auf den Stand von {stand['zeitpunkt']} "
                "zurückgesetzt.\n\nFortfahren?"):
            return

        try:
            h.sicherung_zuruecknehmen(stand)
        except OSError as fehler:
            messagebox.showerror("Fehlgeschlagen", str(fehler))
            return

        messagebox.showinfo("Zurückgesetzt",
                            f"{stand['relativ']} steht wieder auf dem vorherigen Stand.")
        if self.aktuelle:
            self.seiten[self.aktuelle].aktualisieren()
        self.fuss_auffrischen()

    # -------------------------------------------------- Veroeffentlichen
    def veroeffentlichen(self):
        VeroeffentlichenFenster(self)


class VeroeffentlichenFenster:
    """Zeigt in Klartext, was rausgeht, und veroeffentlicht auf Knopfdruck."""

    def __init__(self, eltern):
        self.eltern = eltern
        self.s = eltern.schriften

        self.fenster = tk.Toplevel(eltern.wurzel)
        self.fenster.title("Veröffentlichen")
        self.fenster.geometry("720x620")
        self.fenster.configure(bg=B.FARBEN["grund"])
        self.fenster.transient(eltern.wurzel)
        self.fenster.grab_set()

        self._baue()
        self.fenster.after(60, self._pruefen)

    def _baue(self):
        kopf = tk.Frame(self.fenster, bg=B.FARBEN["tief"])
        kopf.pack(fill="x")
        tk.Label(kopf, text="Das wird veröffentlicht", bg=B.FARBEN["tief"],
                 fg=B.FARBEN["weiss"], font=self.s.kopf).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(kopf, text="Commit im Arbeitsordner, Merge nach main, Push zu GitHub Pages",
                 bg=B.FARBEN["tief"], fg=B.FARBEN["rail_text"],
                 font=self.s.klein).pack(anchor="w", padx=20, pady=(0, 14))

        koerper = tk.Frame(self.fenster, bg=B.FARBEN["grund"])
        koerper.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(koerper, text="ÄNDERUNGEN", bg=B.FARBEN["grund"], fg=B.FARBEN["text"],
                 font=self.s.kopf, anchor="w").pack(fill="x")

        zeilen, _ = mitschnitt(aenderungsprotokoll.sammle)
        zeilen = zeilen or ["(nichts)"]

        # Feste Hoehe mit Bildlauf - sonst schiebt eine lange Liste die
        # Pruefausgabe darunter aus dem Fenster.
        liste = tk.Text(koerper, height=min(len(zeilen), 8), font=self.s.text, wrap="word",
                        bg=B.FARBEN["karte"], fg=B.FARBEN["text"],
                        relief="solid", bd=1, padx=10, pady=6, cursor="arrow")
        liste.pack(fill="x", pady=(6, 16))
        liste.insert("1.0", "\n".join("•  " + zeile for zeile in zeilen))
        liste.configure(state="disabled")

        tk.Label(koerper, text="PRÜFUNG DER SEITE", bg=B.FARBEN["grund"], fg=B.FARBEN["text"],
                 font=self.s.kopf, anchor="w").pack(fill="x")

        self.ausgabe = tk.Text(koerper, height=11, font=self.s.daten, wrap="word",
                               bg=B.FARBEN["karte"], fg=B.FARBEN["text"],
                               relief="solid", bd=1, padx=10, pady=8)
        self.ausgabe.pack(fill="both", expand=True, pady=(6, 0))
        self.ausgabe.insert("1.0", "Sitemap wird aktualisiert und die Seite geprüft …\n")
        self.ausgabe.configure(state="disabled")

        fuss = tk.Frame(self.fenster, bg=B.FARBEN["erhoben"],
                        highlightbackground=B.FARBEN["linie"], highlightthickness=1)
        fuss.pack(fill="x", side="bottom")

        self.stand = tk.Label(fuss, text="", bg=B.FARBEN["erhoben"], fg=B.FARBEN["gedimmt"],
                              font=self.s.klein, anchor="w", justify="left")
        self.stand.pack(side="left", padx=18, pady=12)

        self.knopf_los = B.knopf(fuss, "Jetzt veröffentlichen", self._los,
                                 self.s, "haupt", padx=18, pady=7,
                                 state="disabled", bg=B.FARBEN["matt"])
        self.knopf_los.pack(side="right", padx=(6, 18), pady=12)

        self.knopf_zu = B.knopf(fuss, "Abbrechen", self.fenster.destroy, self.s)
        self.knopf_zu.pack(side="right", pady=12)

    def _schreibe(self, text, ersetzen=False):
        self.ausgabe.configure(state="normal")
        if ersetzen:
            self.ausgabe.delete("1.0", "end")
        self.ausgabe.insert("end", text)
        self.ausgabe.see("end")
        self.ausgabe.configure(state="disabled")

    def _pruefen(self):
        def arbeit():
            _, ausgabe_sitemap = mitschnitt(
                update_sitemap.pruefe_und_aktualisiere, automatisch=True)
            sauber, ausgabe_pruefung = mitschnitt(pruefe_seite.pruefe_alles, still=True)
            return sauber, ausgabe_sitemap + ausgabe_pruefung

        B.im_hintergrund(self.fenster, arbeit, lambda e: self._pruefung_fertig(*e))

    def _pruefung_fertig(self, sauber, ausgabe):
        self._schreibe(ausgabe.strip() or "Alles in Ordnung — keine Probleme gefunden.",
                       ersetzen=True)
        if sauber:
            self.stand.configure(text="Prüfung ohne Fehler.", fg=B.FARBEN["gut"])
            self.knopf_los.configure(text="Jetzt veröffentlichen")
        else:
            self.stand.configure(text="Es wurden Fehler gefunden (siehe oben).",
                                 fg=B.FARBEN["faellig"])
            self.knopf_los.configure(text="Trotzdem veröffentlichen")
        self.knopf_los.configure(state="normal", bg=B.FARBEN["blau"])

    def _los(self):
        self.knopf_los.configure(state="disabled", bg=B.FARBEN["matt"], text="Läuft …")
        self.knopf_zu.configure(state="disabled")
        self.stand.configure(text="Commit, Merge, Push …", fg=B.FARBEN["gedimmt"])
        self._schreibe("\n\n--- Veröffentlichen ---\n")

        B.im_hintergrund(
            self.fenster,
            lambda: mitschnitt(jaehrliches_update.commit_merge_push,
                               "Webseiten-Pflege: Aenderungen aktualisiert"),
            lambda e: self._fertig(*e))

    def _fertig(self, erfolg, ausgabe):
        self._schreibe(ausgabe)
        self.knopf_zu.configure(state="normal", text="Schließen")

        if erfolg:
            self.stand.configure(text="Gepusht. GitHub Pages braucht 1–3 Minuten.",
                                 fg=B.FARBEN["gut"])
        else:
            self.stand.configure(text="Nicht veröffentlicht — siehe Meldung oben.",
                                 fg=B.FARBEN["faellig"])
            self.knopf_los.configure(state="normal", bg=B.FARBEN["blau"],
                                     text="Erneut versuchen")

        self.eltern.fuss_auffrischen()


def _fehler_festhalten(bericht):
    """Beim Start ueber webseiten-fenster.bat laeuft das Programm ohne
    Konsole - eine Fehlermeldung waere sonst spurlos weg."""
    try:
        with open(FEHLERDATEI, "w", encoding="utf-8") as datei:
            datei.write(bericht)
    except OSError:
        pass


def main():
    wurzel = None
    try:
        wurzel = tk.Tk()
        PflegeFenster(wurzel)
    except BaseException:
        bericht = traceback.format_exc()
        _fehler_festhalten(bericht)
        try:
            messagebox.showerror(
                "Fehler beim Start",
                f"{bericht}\n\nDieser Text steht auch in:\n{FEHLERDATEI}")
        except Exception:
            pass   # ohne funktionierendes Tk bleibt nur die Datei
        raise

    if os.path.isfile(FEHLERDATEI):
        os.remove(FEHLERDATEI)   # Start hat geklappt, alte Meldung weg

    wurzel.mainloop()


if __name__ == "__main__":
    main()
