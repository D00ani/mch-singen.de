# -*- coding: utf-8 -*-
"""
Gemeinsame Bausteine fuer die Fenster-Oberflaeche (tools/pflege_fenster.py):
Farben, Schriften und die immer gleichen Bedienelemente.

Damit sehen alle Seiten gleich aus, ohne dass jede ihre eigenen Farbwerte
und Abstaende mitbringt - und eine Aenderung hier wirkt ueberall.

Wird nicht direkt ausgefuehrt.
"""
import html as html_modul
import queue
import threading
import tkinter as tk
from tkinter import font as tkfont

# Dieselben Farben wie die Webseite (css/style.css, :root), damit sich
# Werkzeug und Seite wie eine Sache anfuehlen.
FARBEN = {
    "blau":      "#0047cc",
    "tief":      "#001b5e",
    "gelb":      "#ffcc00",
    "faellig":   "#c62828",
    "hinweis":   "#b26a00",
    "gut":       "#1e8e3e",
    "grund":     "#eef1f7",
    "karte":     "#ffffff",
    "erhoben":   "#f7f9fc",
    "linie":     "#d5dce9",
    "text":      "#131c33",
    "gedimmt":   "#5c6684",
    "rail_text": "#b9c6e8",
    "rail_hell": "#0a2a7a",
    "weiss":     "#ffffff",
    "matt":      "#b9c6e8",
}

# Dringlichkeitsstufen (dieselben Zahlen wie in tools/uebersicht.py)
STUFEN_FARBE = {-1: FARBEN["blau"], 0: FARBEN["faellig"],
                1: FARBEN["hinweis"], 2: FARBEN["gedimmt"]}
STUFEN_ZEICHEN = {-1: "", 0: "!", 1: "–", 2: ""}


class Schriften:
    """Sucht sich beim Start die beste vorhandene Schriftfamilie aus.

    Bahnschrift ist die DIN-Schrift und liegt jedem Windows bei - passend
    fuer einen Motorsportverein und keine Wette auf eine Webschrift.
    """

    def __init__(self):
        vorhanden = set(tkfont.families())

        def familie(*kandidaten):
            for name in kandidaten:
                if name in vorhanden:
                    return name
            return kandidaten[-1]

        anzeige = familie("Bahnschrift", "DIN Alternate", "Segoe UI Semibold", "Segoe UI")
        text = familie("Segoe UI", "Helvetica Neue", "DejaVu Sans")
        daten = familie("Consolas", "Cascadia Mono", "DejaVu Sans Mono", "Courier")

        self.titel  = tkfont.Font(family=anzeige, size=15, weight="bold")
        self.kopf   = tkfont.Font(family=anzeige, size=11, weight="bold")
        self.label  = tkfont.Font(family=anzeige, size=8)
        self.marke  = tkfont.Font(family=anzeige, size=10, weight="bold")
        self.knopf  = tkfont.Font(family=anzeige, size=10)
        self.text   = tkfont.Font(family=text, size=10)
        self.fett   = tkfont.Font(family=text, size=10, weight="bold")
        self.klein  = tkfont.Font(family=text, size=9)
        self.zahl   = tkfont.Font(family=daten, size=26, weight="bold")
        self.daten  = tkfont.Font(family=daten, size=9)


# ------------------------------------------------------------------
# Bedienelemente
# ------------------------------------------------------------------

def knopf(eltern, text, befehl, schriften, art="neben", **zusatz):
    """art: 'haupt' (blau gefuellt), 'neben' (umrandet), 'warnung' (rot)."""
    stil = {
        "haupt":   dict(bg=FARBEN["blau"], fg=FARBEN["weiss"], relief="flat", bd=0,
                        activebackground=FARBEN["tief"], activeforeground=FARBEN["weiss"]),
        "neben":   dict(bg=FARBEN["karte"], fg=FARBEN["text"], relief="solid", bd=1,
                        activeforeground=FARBEN["blau"]),
        "warnung": dict(bg=FARBEN["karte"], fg=FARBEN["faellig"], relief="solid", bd=1,
                        activeforeground=FARBEN["faellig"]),
    }[art]
    einstellungen = dict(font=schriften.knopf, padx=14, pady=6, cursor="hand2",
                         disabledforeground=FARBEN["matt"])
    einstellungen.update(stil)
    einstellungen.update(zusatz)   # Angaben des Aufrufers gewinnen
    return tk.Button(eltern, text=text, command=befehl, **einstellungen)


def karte(eltern, schriften, stufe, titel, unterzeile=None, knopf_text=None,
          knopf_befehl=None):
    """Ein Eintrag mit farbigem Streifen links - das Grundelement der
    Uebersicht und aller Ergebnislisten."""
    farbe = STUFEN_FARBE.get(stufe, FARBEN["gedimmt"])

    rahmen = tk.Frame(eltern, bg=FARBEN["karte"],
                      highlightbackground=FARBEN["linie"], highlightthickness=1)
    rahmen.pack(fill="x", pady=(0, 8))

    tk.Frame(rahmen, bg=farbe, width=4).pack(side="left", fill="y")

    zeichen = STUFEN_ZEICHEN.get(stufe, "")
    if zeichen:
        tk.Label(rahmen, text=zeichen, bg=FARBEN["karte"], fg=farbe,
                 font=schriften.marke, width=2).pack(side="left", padx=(8, 0))
    else:
        tk.Frame(rahmen, bg=FARBEN["karte"], width=16).pack(side="left")

    if knopf_text and knopf_befehl:
        k = knopf(rahmen, knopf_text, knopf_befehl, schriften, "neben",
                  fg=FARBEN["blau"], padx=12, pady=2)
        k.pack(side="right", padx=12)

    inhalt = tk.Frame(rahmen, bg=FARBEN["karte"])
    inhalt.pack(side="left", fill="x", expand=True, padx=10, pady=9)
    tk.Label(inhalt, text=titel, bg=FARBEN["karte"], fg=FARBEN["text"],
             font=schriften.fett, anchor="w", justify="left").pack(anchor="w")
    if unterzeile:
        tk.Label(inhalt, text=unterzeile, bg=FARBEN["karte"], fg=FARBEN["gedimmt"],
                 font=schriften.klein, anchor="w", justify="left").pack(anchor="w")
    return rahmen


def abschnitt(eltern, schriften, ueberschrift, notiz=None):
    """Ueberschrift mit optionaler Randbemerkung. Gibt den Rahmen zurueck,
    in den der Inhalt gepackt wird."""
    kopf = tk.Frame(eltern, bg=FARBEN["grund"])
    kopf.pack(fill="x", pady=(0, 8))
    tk.Label(kopf, text=ueberschrift.upper(), bg=FARBEN["grund"], fg=FARBEN["text"],
             font=schriften.kopf).pack(side="left")
    if notiz:
        tk.Label(kopf, text=notiz, bg=FARBEN["grund"], fg=FARBEN["gedimmt"],
                 font=schriften.klein).pack(side="left", padx=10)
    return kopf


def rollbereich(eltern):
    """Scrollbarer Bereich. Gibt (leinwand, innenrahmen, rollleiste) zurueck;
    die Bildlaufleiste blendet sich selbst aus, wenn alles hineinpasst."""
    leinwand = tk.Canvas(eltern, bg=FARBEN["grund"], highlightthickness=0)
    leiste = tk.Scrollbar(eltern, orient="vertical", command=leinwand.yview)
    leinwand.configure(yscrollcommand=leiste.set)
    leinwand.pack(side="left", fill="both", expand=True)

    innen = tk.Frame(leinwand, bg=FARBEN["grund"])
    fenster_id = leinwand.create_window((0, 0), window=innen, anchor="nw")

    def anpassen(_=None):
        leinwand.configure(scrollregion=leinwand.bbox("all"))
        passt = innen.winfo_reqheight() <= leinwand.winfo_height()
        if passt and leiste.winfo_ismapped():
            leiste.pack_forget()
        elif not passt and not leiste.winfo_ismapped():
            leiste.pack(side="right", fill="y", before=leinwand)

    innen.bind("<Configure>", anpassen)
    leinwand.bind("<Configure>",
                  lambda e: (leinwand.itemconfigure(fenster_id, width=e.width), anpassen()))
    return leinwand, innen, leiste


def lesbar(text):
    """HTML-Schreibweise fuer die Anzeige aufloesen: '&amp;' wird zu '&'."""
    return html_modul.unescape(text or "")


def fuer_html(text):
    """Gegenstueck zu lesbar(): '&' wird wieder zu '&amp;'.

    Anfuehrungszeichen bleiben unangetastet - die Texte landen zwischen
    Tags, nicht in Attributen.
    """
    return html_modul.escape(text or "", quote=False)


class Formular(tk.Toplevel):
    """Eingabefenster fuer einen Datensatz.

    felder: Liste von Woerterbuechern
        schluessel    Name im Ergebnis
        beschriftung  Text links daneben
        art           "text" (Standard), "auswahl", "mehrzeilig"
        optionen      Liste, nur bei "auswahl"
        pruefer       Funktion(wert) -> Fehlertext oder None
        hinweis       kleine Zeile unter dem Feld
        pflicht       True/False (Standard True)

    Nach wait_window() steht das Ergebnis in .werte (dict) oder ist None,
    wenn abgebrochen wurde.
    """

    def __init__(self, eltern, schriften, titel, felder, werte=None, einleitung=None):
        super().__init__(eltern)
        self.s = schriften
        self.felder = felder
        self.werte = None
        self._eingaben = {}
        self._fehlerzeilen = {}

        self.title(titel)
        self.configure(bg=FARBEN["grund"])
        self.transient(eltern)
        self.resizable(False, False)

        kopf = tk.Frame(self, bg=FARBEN["tief"])
        kopf.pack(fill="x")
        tk.Label(kopf, text=titel, bg=FARBEN["tief"], fg=FARBEN["weiss"],
                 font=schriften.kopf).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(kopf, text=einleitung or "Pflichtfelder sind nicht besonders markiert — "
                                          "leer lassen geht nur, wo es dabeisteht.",
                 bg=FARBEN["tief"], fg=FARBEN["rail_text"], font=schriften.klein,
                 wraplength=520, justify="left").pack(anchor="w", padx=20, pady=(0, 14))

        koerper = tk.Frame(self, bg=FARBEN["grund"])
        koerper.pack(fill="both", expand=True, padx=20, pady=16)
        koerper.columnconfigure(1, weight=1)

        for reihe, feld in enumerate(felder):
            self._feld(koerper, reihe * 3, feld, (werte or {}).get(feld["schluessel"], ""))

        fuss = tk.Frame(self, bg=FARBEN["erhoben"],
                        highlightbackground=FARBEN["linie"], highlightthickness=1)
        fuss.pack(fill="x", side="bottom")
        knopf(fuss, "Speichern", self._speichern, schriften, "haupt",
              padx=18, pady=7).pack(side="right", padx=(6, 18), pady=12)
        knopf(fuss, "Abbrechen", self.destroy, schriften).pack(side="right", pady=12)

        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<Return>", lambda _: self._speichern())

        self.update_idletasks()
        self._mittig(eltern)
        self.grab_set()
        erstes = felder[0]["schluessel"] if felder else None
        if erstes:
            self._eingaben[erstes].focus_set()

    def _feld(self, eltern, reihe, feld, wert):
        tk.Label(eltern, text=feld["beschriftung"], bg=FARBEN["grund"], fg=FARBEN["text"],
                 font=self.s.text, anchor="w").grid(row=reihe, column=0, sticky="w",
                                                    padx=(0, 14), pady=(0, 2))

        art = feld.get("art", "text")
        if art == "auswahl":
            from tkinter import ttk
            eingabe = ttk.Combobox(eltern, values=feld["optionen"], font=self.s.text,
                                   state="readonly", width=34)
            eingabe.set(wert or (feld["optionen"][0] if feld["optionen"] else ""))
        elif art == "mehrzeilig":
            eingabe = tk.Text(eltern, height=4, width=36, font=self.s.text, wrap="word",
                              relief="solid", bd=1, bg=FARBEN["karte"], fg=FARBEN["text"])
            eingabe.insert("1.0", wert)
        else:
            eingabe = tk.Entry(eltern, font=self.s.text, width=36, relief="solid", bd=1,
                               bg=FARBEN["karte"], fg=FARBEN["text"])
            eingabe.insert(0, wert)

        eingabe.grid(row=reihe, column=1, sticky="ew", pady=(0, 2))
        self._eingaben[feld["schluessel"]] = eingabe

        if feld.get("hinweis"):
            tk.Label(eltern, text=feld["hinweis"], bg=FARBEN["grund"], fg=FARBEN["gedimmt"],
                     font=self.s.klein, anchor="w", justify="left",
                     wraplength=300).grid(row=reihe + 1, column=1, sticky="w")

        fehler = tk.Label(eltern, text="", bg=FARBEN["grund"], fg=FARBEN["faellig"],
                          font=self.s.klein, anchor="w", justify="left", wraplength=300)
        fehler.grid(row=reihe + 2, column=1, sticky="w", pady=(0, 10))
        self._fehlerzeilen[feld["schluessel"]] = fehler

    def _lies(self, schluessel):
        eingabe = self._eingaben[schluessel]
        if isinstance(eingabe, tk.Text):
            return eingabe.get("1.0", "end").strip()
        return eingabe.get().strip()

    def _speichern(self):
        werte, fehlerhaft = {}, False
        for feld in self.felder:
            schluessel = feld["schluessel"]
            wert = self._lies(schluessel)
            meldung = None

            if not wert and feld.get("pflicht", True):
                meldung = "Darf nicht leer sein."
            elif wert and feld.get("pruefer"):
                meldung = feld["pruefer"](wert)

            self._fehlerzeilen[schluessel].configure(text=meldung or "")
            if meldung:
                fehlerhaft = True
            werte[schluessel] = wert

        if fehlerhaft:
            return
        self.werte = werte
        self.destroy()

    def _mittig(self, eltern):
        x = eltern.winfo_rootx() + (eltern.winfo_width() - self.winfo_width()) // 2
        y = eltern.winfo_rooty() + (eltern.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def frage_formular(eltern, schriften, titel, felder, werte=None, einleitung=None):
    """Zeigt ein Formular und wartet auf die Eingabe. Gibt dict oder None."""
    fenster = Formular(eltern, schriften, titel, felder, werte, einleitung)
    eltern.wait_window(fenster)
    return fenster.werte


def im_hintergrund(widget, arbeit, fertig):
    """Laesst arbeit() in einem Thread laufen und ruft fertig(ergebnis) im
    Hauptthread auf.

    Tkinter darf ausschliesslich aus dem Hauptthread bedient werden. Der
    Thread legt sein Ergebnis deshalb nur in die Warteschlange; abgeholt
    wird es von einer after()-Schleife im Hauptthread.
    """
    post = queue.Queue()

    def abholen():
        try:
            fertig(post.get_nowait())
        except queue.Empty:
            widget.after(80, abholen)

    threading.Thread(target=lambda: post.put(arbeit()), daemon=True).start()
    widget.after(80, abholen)
