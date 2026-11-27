# -*- coding: utf-8 -*-
"""
Gemeinsame Bausteine fuer die Fenster-Oberflaeche (tools/pflege_fenster.py):
Farben, Schriften und die immer gleichen Bedienelemente.

Damit sehen alle Seiten gleich aus, ohne dass jede ihre eigenen Farbwerte
und Abstaende mitbringt - und eine Aenderung hier wirkt ueberall.

Wird nicht direkt ausgefuehrt.
"""
import calendar
import html as html_modul
import queue
import re
import threading
import tkinter as tk
from datetime import date
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


# ------------------------------------------------------------------
# Datum und Uhrzeit
# ------------------------------------------------------------------

MONATE_LANG = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
               "August", "September", "Oktober", "November", "Dezember"]
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
UHRZEIT_MUSTER = r"([01]\d|2[0-3]):[0-5]\d"


def datum_lesen(text):
    """Findet ein Datum in "08.08.2026", "Sa, 08.08.2026" oder "8.8.26".
    None, wenn keins drinsteht oder es den Tag nicht gibt."""
    treffer = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text or "")
    if not treffer:
        return None
    tag, monat, jahr = (int(x) for x in treffer.groups())
    if jahr < 100:
        jahr += 2000
    try:
        return date(jahr, monat, tag)
    except ValueError:
        return None


def datum_schreiben(tag, mit_wochentag=False):
    """08.08.2026 oder - wie auf der Webseite ueblich - Sa, 08.08.2026."""
    kurz = tag.strftime("%d.%m.%Y")
    return f"{WOCHENTAGE_KURZ[tag.weekday()]}, {kurz}" if mit_wochentag else kurz


class Kalender(tk.Toplevel):
    """Monatskalender zum Anklicken - statt Tag, Monat und Jahr einzeln
    einzutippen. Ruft waehlen(date) auf und schliesst sich.

    Bedienung: Klick auf einen Tag; Pfeile oben oder Bild auf/ab blaettern
    den Monat; "Heute" springt zum heutigen Tag; Esc schliesst."""

    def __init__(self, eltern, schriften, start, waehlen, anker):
        super().__init__(eltern)
        self.s = schriften
        self.waehlen = waehlen
        self.gewaehlt = start
        self.monat = (start or date.today()).replace(day=1)

        self.title("Datum wählen")
        self.configure(bg=FARBEN["karte"], highlightbackground=FARBEN["linie"],
                       highlightthickness=1)
        self.transient(eltern)
        self.resizable(False, False)

        kopf = tk.Frame(self, bg=FARBEN["tief"])
        kopf.pack(fill="x")
        pfeil = dict(bg=FARBEN["tief"], fg=FARBEN["weiss"], relief="flat", bd=0,
                     font=self.s.kopf, cursor="hand2", padx=12, pady=6,
                     activebackground=FARBEN["rail_hell"], activeforeground=FARBEN["weiss"])
        tk.Button(kopf, text="‹", command=lambda: self._blaettern(-1), **pfeil).pack(side="left")
        tk.Button(kopf, text="›", command=lambda: self._blaettern(1), **pfeil).pack(side="right")
        self.titel = tk.Label(kopf, bg=FARBEN["tief"], fg=FARBEN["weiss"], font=self.s.kopf)
        self.titel.pack(side="left", expand=True)

        self.gitter = tk.Frame(self, bg=FARBEN["karte"])
        self.gitter.pack(padx=10, pady=(8, 4))

        fuss = tk.Frame(self, bg=FARBEN["karte"])
        fuss.pack(fill="x", padx=10, pady=(0, 10))
        knopf(fuss, "Heute", lambda: self._nimm(date.today()), schriften,
              padx=10, pady=3).pack(side="left")
        knopf(fuss, "Abbrechen", self._zu, schriften, padx=10, pady=3).pack(side="right")

        self.bind("<Escape>", lambda _: self._zu())
        self.bind("<Prior>", lambda _: self._blaettern(-1))
        self.bind("<Next>", lambda _: self._blaettern(1))
        self.protocol("WM_DELETE_WINDOW", self._zu)

        self._zeichnen()
        self.update_idletasks()
        x = anker.winfo_rootx()
        y = anker.winfo_rooty() + anker.winfo_height() + 4
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.focus_set()

    def _blaettern(self, schritt):
        jahr, monat = self.monat.year, self.monat.month + schritt
        if monat < 1:
            jahr, monat = jahr - 1, 12
        elif monat > 12:
            jahr, monat = jahr + 1, 1
        self.monat = date(jahr, monat, 1)
        self._zeichnen()

    def _zeichnen(self):
        for kind in self.gitter.winfo_children():
            kind.destroy()
        self.titel.configure(text=f"{MONATE_LANG[self.monat.month - 1]} {self.monat.year}")
        for spalte, name in enumerate(WOCHENTAGE_KURZ):
            tk.Label(self.gitter, text=name, bg=FARBEN["karte"], width=4,
                     fg=FARBEN["faellig"] if spalte == 6 else FARBEN["gedimmt"],
                     font=self.s.klein).grid(row=0, column=spalte, pady=(0, 4))
        heute = date.today()
        wochen = calendar.Calendar(firstweekday=0).monthdatescalendar(self.monat.year, self.monat.month)
        for reihe, woche in enumerate(wochen, start=1):
            for spalte, tag in enumerate(woche):
                if tag.month != self.monat.month:
                    tk.Label(self.gitter, text="", bg=FARBEN["karte"], width=4).grid(row=reihe, column=spalte)
                    continue
                gewaehlt = tag == self.gewaehlt
                tk.Button(
                    self.gitter, text=str(tag.day), width=3, relief="flat", bd=0, cursor="hand2",
                    font=self.s.fett if tag == heute else self.s.text,
                    bg=FARBEN["blau"] if gewaehlt else FARBEN["karte"],
                    fg=FARBEN["weiss"] if gewaehlt else (FARBEN["blau"] if tag == heute else FARBEN["text"]),
                    activebackground=FARBEN["tief"], activeforeground=FARBEN["weiss"],
                    command=lambda t=tag: self._nimm(t)).grid(row=reihe, column=spalte, padx=1, pady=1)

    def _nimm(self, tag):
        self._zu()
        self.waehlen(tag)

    def _zu(self):
        self.grab_release()
        eltern = self.master
        self.destroy()
        try:
            eltern.grab_set()   # das Formular darunter bleibt modal
        except tk.TclError:
            pass


class Formular(tk.Toplevel):
    """Eingabefenster fuer einen Datensatz.

    felder: Liste von Woerterbuechern
        schluessel    Name im Ergebnis
        beschriftung  Text links daneben
        art           "text" (Standard), "auswahl", "mehrzeilig",
                      "datum" (Feld mit Kalender-Knopf),
                      "uhrzeit" (Feld mit Auswahlliste in Viertelstunden)
        format        nur bei "datum": "kurz" (08.08.2026, Standard) oder
                      "wochentag" (Sa, 08.08.2026)
        frei          nur bei "datum": True = auch Freitext wie "Saison 2026"
                      erlaubt, der Kalender ist dann eine Hilfe
        art "datei"   Feld mit Knopf "Auswählen…". Dazu: basis (Ordner der
                      Webseite), ordner (Startordner und Ziel beim Kopieren,
                      relativ zu basis), praefix ("" oder "../" - wie der Pfad
                      geschrieben wird), typen (Liste fuer den Dateidialog)
        art "vorlage" Auswahl, die beim Wechsel andere Felder ausfuellt.
                      vorlagen = {Anzeige: {schluessel: wert, ...}}. Taucht
                      im Ergebnis nicht auf.
        hoehe, breite nur bei "mehrzeilig": Zeilen und Zeichen (Standard 4 x 36)
        optionen      Liste, nur bei "auswahl" (frei=True: auch eigene Eingabe)
        pruefer       Funktion(wert) -> Fehlertext oder None
        hinweis       kleine Zeile unter dem Feld
        pflicht       True/False (Standard True)

    vorschau: Funktion(werte) -> None oder Meldungstext. Gibt es sie, steht
    im Fuss ein Knopf "Vorschau im Browser". Sie bekommt die Eingaben so,
    wie sie gerade dastehen (ungeprueft), und zeigt den Entwurf an, ohne zu
    speichern - siehe vorschau.entwurf_zeigen().

    Nach wait_window() steht das Ergebnis in .werte (dict) oder ist None,
    wenn abgebrochen wurde.
    """

    def __init__(self, eltern, schriften, titel, felder, werte=None, einleitung=None,
                 vorschau=None):
        super().__init__(eltern)
        self.s = schriften
        self.felder = felder
        self._vorschau_befehl = vorschau
        self.werte = None
        self._eingaben = {}
        self._fehlerzeilen = {}
        self._reihenfolge = []      # Eingabefelder in der Reihenfolge von oben nach unten

        self.title(titel)
        self.configure(bg=FARBEN["grund"])
        self.transient(eltern)
        self.resizable(False, False)

        kopf = tk.Frame(self, bg=FARBEN["tief"])
        kopf.pack(fill="x")
        tk.Label(kopf, text=titel, bg=FARBEN["tief"], fg=FARBEN["weiss"],
                 font=schriften.kopf).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(kopf, text=einleitung or "Pflichtfelder sind nicht besonders markiert - "
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
        if vorschau:
            knopf(fuss, "Vorschau im Browser", self._vorschau, schriften,
                  fg=FARBEN["blau"]).pack(side="right", padx=(0, 6), pady=12)
        if felder:
            tk.Label(fuss, text="Enter = nächstes Feld · im letzten Feld speichern · Esc = abbrechen",
                     bg=FARBEN["erhoben"], fg=FARBEN["gedimmt"], font=schriften.klein,
                     wraplength=230 if vorschau else 0,
                     justify="left").pack(side="left", padx=18, pady=12)

        self.bind("<Escape>", lambda _: self.destroy())

        self.update_idletasks()
        self._mittig(eltern)
        self.grab_set()
        if self._reihenfolge:
            self._fokus(self._reihenfolge[0])

    # -------------------------------------------------- Navigation
    def _fokus(self, widget):
        widget.focus_set()
        if isinstance(widget, tk.Entry):
            # Inhalt markieren: weitertippen ersetzt, Pfeiltaste stellt sich davor
            widget.select_range(0, "end")
            widget.icursor("end")

    def _weiter(self, widget, schritt=1):
        """Enter/Tab springt ins naechste Feld. Hinter dem letzten wird
        gespeichert - so laesst sich ein Formular ohne Maus ausfuellen."""
        if widget not in self._reihenfolge:
            return "break"
        ziel = self._reihenfolge.index(widget) + schritt

        if ziel >= len(self._reihenfolge):
            self._speichern()
            return "break"
        self._fokus(self._reihenfolge[max(ziel, 0)])
        return "break"      # verhindert, dass Tk zusaetzlich selbst weiterspringt

    def _feld(self, eltern, reihe, feld, wert):
        tk.Label(eltern, text=feld["beschriftung"], bg=FARBEN["grund"], fg=FARBEN["text"],
                 font=self.s.text, anchor="w").grid(row=reihe, column=0, sticky="w",
                                                    padx=(0, 14), pady=(0, 2))

        art = feld.get("art", "text")
        if art == "auswahl":
            from tkinter import ttk
            eingabe = ttk.Combobox(eltern, values=feld["optionen"], font=self.s.text,
                                   state="normal" if feld.get("frei") else "readonly", width=34)
            eingabe.set(wert or (feld["optionen"][0] if feld["optionen"] else ""))
        elif art == "vorlage":
            from tkinter import ttk
            eingabe = ttk.Combobox(eltern, values=list(feld["vorlagen"]), font=self.s.text,
                                   state="readonly", width=34)
            eingabe.set("")
            eingabe.bind("<<ComboboxSelected>>",
                         lambda _, e=eingabe, f=feld: self._vorlage_anwenden(f, e.get()))
        elif art == "mehrzeilig":
            eingabe = tk.Text(eltern, height=feld.get("hoehe", 4), width=feld.get("breite", 36),
                              font=self.s.text, wrap="word",
                              relief="solid", bd=1, bg=FARBEN["karte"], fg=FARBEN["text"])
            eingabe.insert("1.0", wert)
        elif art == "uhrzeit":
            from tkinter import ttk
            zeiten = [f"{stunde:02d}:{minute:02d}" for stunde in range(6, 23) for minute in (0, 15, 30, 45)]
            eingabe = ttk.Combobox(eltern, values=zeiten, font=self.s.text, width=34)
            eingabe.set(wert)
        else:
            eingabe = tk.Entry(eltern, font=self.s.text, width=36, relief="solid", bd=1,
                               bg=FARBEN["karte"], fg=FARBEN["text"])
            eingabe.insert(0, wert)

        platz = eingabe
        if art == "datei":
            platz = tk.Frame(eltern, bg=FARBEN["grund"])
            eingabe.destroy()
            eingabe = tk.Entry(platz, font=self.s.text, width=24, relief="solid", bd=1,
                               bg=FARBEN["karte"], fg=FARBEN["text"])
            eingabe.insert(0, wert)
            eingabe.pack(side="left", fill="x", expand=True)
            knopf(platz, "Auswählen…", lambda e=eingabe, f=feld: self._datei_waehlen(e, f), self.s,
                  padx=10, pady=1).pack(side="left", padx=(6, 0))
        elif art == "datum":
            # Feld bleibt zum Tippen da; der Knopf daneben oeffnet den Kalender
            platz = tk.Frame(eltern, bg=FARBEN["grund"])
            eingabe.destroy()
            eingabe = tk.Entry(platz, font=self.s.text, width=24, relief="solid", bd=1,
                               bg=FARBEN["karte"], fg=FARBEN["text"])
            eingabe.insert(0, wert)
            eingabe.pack(side="left", fill="x", expand=True)
            knopf(platz, "Kalender", lambda e=eingabe, f=feld: self._kalender(e, f), self.s,
                  padx=10, pady=1).pack(side="left", padx=(6, 0))
            eingabe.bind("<Alt-Down>", lambda _, e=eingabe, f=feld: self._kalender(e, f))
            eingabe.bind("<F4>", lambda _, e=eingabe, f=feld: self._kalender(e, f))

        platz.grid(row=reihe, column=1, sticky="ew", pady=(0, 2))
        self._eingaben[feld["schluessel"]] = eingabe
        self._reihenfolge.append(eingabe)

        if art == "mehrzeilig":
            # Hier muss Enter einen Absatz machen - zum Weiterspringen dient Tab
            eingabe.bind("<Tab>", lambda _, w=eingabe: self._weiter(w, 1))
            eingabe.bind("<Shift-Tab>", lambda _, w=eingabe: self._weiter(w, -1))
            eingabe.bind("<ISO_Left_Tab>", lambda _, w=eingabe: self._weiter(w, -1))
            eingabe.bind("<Control-Return>", lambda _: self._speichern())
        else:
            eingabe.bind("<Return>", lambda _, w=eingabe: self._weiter(w, 1))
            eingabe.bind("<KP_Enter>", lambda _, w=eingabe: self._weiter(w, 1))
            eingabe.bind("<Shift-Return>", lambda _, w=eingabe: self._weiter(w, -1))

        hinweis = feld.get("hinweis", "")
        if art == "datum" and not hinweis:
            hinweis = ("Kalender-Knopf (oder F4) - oder tippen, z. B. 08.08.2026"
                       + (" - Freitext geht auch" if feld.get("frei") else ""))
        if art == "vorlage" and not hinweis:
            hinweis = "füllt die Felder darunter aus - danach lässt sich alles noch ändern"
        if art == "mehrzeilig":
            # Enter ist hier der Absatz - das muss dabeistehen, sonst sucht
            # man vergeblich nach dem Weiterspringen.
            zusatz = "Enter macht einen Absatz, Tab springt weiter"
            hinweis = f"{hinweis}\n{zusatz}" if hinweis else zusatz

        if hinweis:
            tk.Label(eltern, text=hinweis, bg=FARBEN["grund"], fg=FARBEN["gedimmt"],
                     font=self.s.klein, anchor="w", justify="left",
                     wraplength=300).grid(row=reihe + 1, column=1, sticky="w")

        fehler = tk.Label(eltern, text="", bg=FARBEN["grund"], fg=FARBEN["faellig"],
                          font=self.s.klein, anchor="w", justify="left", wraplength=300)
        fehler.grid(row=reihe + 2, column=1, sticky="w", pady=(0, 10))
        self._fehlerzeilen[feld["schluessel"]] = fehler

    def _setze(self, schluessel, wert):
        eingabe = self._eingaben.get(schluessel)
        if eingabe is None:
            return
        from tkinter import ttk
        if isinstance(eingabe, tk.Text):
            eingabe.delete("1.0", "end")
            eingabe.insert("1.0", wert)
        elif isinstance(eingabe, ttk.Combobox):
            # Vor tk.Entry pruefen: die Combobox ist auch ein Entry, und bei
            # reinen Auswahlfeldern (readonly) greift insert() nicht
            eingabe.set(wert)
        else:
            eingabe.delete(0, "end")
            eingabe.insert(0, wert)
        if schluessel in self._fehlerzeilen:
            self._fehlerzeilen[schluessel].configure(text="")

    def _vorlage_anwenden(self, feld, auswahl):
        for schluessel, wert in feld["vorlagen"].get(auswahl, {}).items():
            self._setze(schluessel, wert)

    def _datei_waehlen(self, eingabe, feld):
        """Dateidialog; liegt die Datei ausserhalb der Webseite, wird sie nach
        Rueckfrage in den passenden Ordner kopiert."""
        import os
        import shutil
        from tkinter import filedialog, messagebox

        basis = feld["basis"]
        ordner = feld.get("ordner", "")
        startordner = os.path.join(basis, ordner)
        pfad = filedialog.askopenfilename(
            parent=self, title=f"{feld['beschriftung']} auswählen",
            initialdir=startordner if os.path.isdir(startordner) else basis,
            filetypes=feld.get("typen") or [("Alle Dateien", "*.*")])
        if not pfad:
            return
        pfad = os.path.abspath(pfad)
        if os.path.commonpath([pfad, os.path.abspath(basis)]) != os.path.abspath(basis):
            ziel = os.path.join(startordner, os.path.basename(pfad))
            if not messagebox.askyesno(
                    "Datei übernehmen?",
                    f"„{os.path.basename(pfad)}“ liegt außerhalb der Webseite.\n\n"
                    f"In den Ordner {ordner or 'der Webseite'} kopieren und von dort verlinken?",
                    parent=self):
                return
            if os.path.exists(ziel) and not messagebox.askyesno(
                    "Datei ersetzen?", f"{os.path.basename(ziel)} gibt es dort schon. Ersetzen?",
                    parent=self):
                return
            os.makedirs(startordner, exist_ok=True)
            shutil.copy2(pfad, ziel)
            pfad = ziel
        relativ = os.path.relpath(pfad, basis).replace("\\", "/")
        eingabe.delete(0, "end")
        eingabe.insert(0, feld.get("praefix", "") + relativ)
        self._fehlerzeilen[feld["schluessel"]].configure(text="")

    def _kalender(self, eingabe, feld):
        def gewaehlt(tag):
            eingabe.delete(0, "end")
            eingabe.insert(0, datum_schreiben(tag, feld.get("format") == "wochentag"))
            self._fehlerzeilen[feld["schluessel"]].configure(text="")
            eingabe.focus_set()
        Kalender(self, self.s, datum_lesen(eingabe.get()), gewaehlt, eingabe)
        return "break"

    def _lies(self, schluessel):
        eingabe = self._eingaben[schluessel]
        if isinstance(eingabe, tk.Text):
            return eingabe.get("1.0", "end").strip()
        return eingabe.get().strip()

    def _vorschau(self):
        """Zeigt den Entwurf im Browser - gespeichert wird dabei nichts."""
        from tkinter import messagebox
        werte = {f["schluessel"]: self._lies(f["schluessel"])
                 for f in self.felder if f.get("art") != "vorlage"}
        for feld in self.felder:
            pruefer = feld.get("pruefer")
            wert = werte.get(feld["schluessel"])
            meldung = pruefer(wert) if (pruefer and wert) else None
            self._fehlerzeilen[feld["schluessel"]].configure(text=meldung or "")
            if meldung:
                return
        try:
            meldung = self._vorschau_befehl(werte)
        except Exception as fehler:          # Vorschau darf das Formular nie kippen
            meldung = f"Die Vorschau ging nicht: {fehler}"
        if meldung:
            messagebox.showinfo("Vorschau", meldung, parent=self)

    def _speichern(self):
        werte, fehlerhaft = {}, False
        for feld in self.felder:
            schluessel = feld["schluessel"]
            if feld.get("art") == "vorlage":
                continue        # nur eine Ausfuellhilfe, kein eigener Wert
            wert = self._lies(schluessel)
            meldung = None

            art = feld.get("art", "text")
            if not wert and feld.get("pflicht", True):
                meldung = "Darf nicht leer sein."
            elif wert and art == "datum" and not feld.get("frei"):
                tag = datum_lesen(wert)
                if tag:
                    # "8.8.26" wird zu "08.08.2026" - so steht es einheitlich in der Datei
                    wert = datum_schreiben(tag, feld.get("format") == "wochentag")
                else:
                    meldung = "Kein gültiges Datum - bitte TT.MM.JJJJ oder den Kalender."
            elif wert and art == "uhrzeit" and not re.fullmatch(UHRZEIT_MUSTER, wert):
                meldung = "Uhrzeit bitte als HH:MM, z. B. 09:00."
            if not meldung and wert and feld.get("pruefer"):
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


def frage_formular(eltern, schriften, titel, felder, werte=None, einleitung=None,
                   vorschau=None):
    """Zeigt ein Formular und wartet auf die Eingabe. Gibt dict oder None."""
    fenster = Formular(eltern, schriften, titel, felder, werte, einleitung, vorschau)
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
