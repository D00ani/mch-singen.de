# -*- coding: utf-8 -*-
"""
Fensterseite fuer die Seite "Sponsoren & Links".

Fuenf Bereiche, oben umschaltbar: die Sponsoren-Banden, die beiden
Linklisten (befreundete Vereine und nuetzliche Links), die Zahlen im Kopf
und der Aufruf "Werde Sponsor".

Die Anzeigegroesse der Logos rechnet das Werkzeug aus: alle Logos sollen
dieselbe FLAECHE einnehmen, sonst wirken hochkante Logos halb so gross
wie querformatige.

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
import sponsoren_pflege as sp
import uebersicht
from fenster_seiten import Seite

ROOT = h.ROOT

SPONSOREN = "Sponsoren (Logos)"
ZAHLEN = "Zahlen oben"
AUFRUF = "Aufruf „Werde Sponsor“"


class SponsorenSeite(Seite):
    titel = "Sponsoren & Links"
    untertitel = ("Banden, befreundete Vereine, nützliche Links, die Zahlen im Kopf "
                  "und der Sponsoren-Aufruf — die komplette Seite ohne HTML.")

    VORNE = "Ganz vorne"

    def baue(self):
        self.knopf_loeschen = self.knopf("Löschen", self.loeschen, "warnung")
        self.knopf("Bearbeiten", self.bearbeiten)
        self.knopf_neu = self.knopf("Neuer Eintrag", self.neu, "haupt")

        self.bereich = tk.StringVar(value=SPONSOREN)
        wahl = tk.Frame(self.fest, bg=B.FARBEN["grund"])
        wahl.pack(fill="x", pady=(0, 4))
        namen = [SPONSOREN] + [l["name"] for l in sp.LINKLISTEN] + [ZAHLEN, AUFRUF]
        for name in namen:
            tk.Radiobutton(wahl, text=name, value=name, variable=self.bereich,
                           command=self.aktualisieren, bg=B.FARBEN["grund"],
                           fg=B.FARBEN["text"], font=self.s.text, cursor="hand2",
                           activebackground=B.FARBEN["grund"],
                           selectcolor=B.FARBEN["karte"]).pack(side="left", padx=(0, 12))
        self.baum = None
        self.eintraege = []

    def _linkliste(self):
        return next((l for l in sp.LINKLISTEN if l["name"] == self.bereich.get()), None)

    # -------------------------------------------------- Anzeige
    def aktualisieren(self):
        self.leeren()
        art = self.bereich.get()

        anlegbar = art == SPONSOREN or self._linkliste() is not None
        self.knopf_neu.configure(state="normal" if anlegbar else "disabled",
                                 bg=B.FARBEN["blau"] if anlegbar else B.FARBEN["matt"])
        self.knopf_loeschen.configure(state="normal" if anlegbar else "disabled")

        if art == SPONSOREN:
            self._zeige_sponsoren()
        elif self._linkliste():
            self._zeige_links(self._linkliste())
        elif art == ZAHLEN:
            self._zeige_zahlen()
        else:
            self._zeige_aufruf()

        if self.baum:
            self.baum.bind("<Double-1>", lambda _: self.bearbeiten())

    def _zeige_sponsoren(self):
        html = sp.lade_html()
        self.eintraege = sp.finde_sponsoren(html)
        frei = sp.freie_logodateien(html)

        B.abschnitt(self.inhalt, self.s, "Sponsoren-Banden",
                    f"{len(self.eintraege)} Banden · {len(frei)} unbenutzte Logo-Datei(en)")

        if not self.eintraege:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Noch keine Bande angelegt.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Name", "Webseite", "Anzeigegröße", "Logo"),
                                 (185, 275, 105, 105),
                                 hoehe=min(len(self.eintraege), 12),
                                 zeilenzahl=len(self.eintraege))
        for nummer, sponsor in enumerate(self.eintraege):
            masse = re.search(r'width="(\d+)"\s+height="(\d+)"', sponsor["match"].group(0))
            groesse = f"{masse.group(1)}×{masse.group(2)}" if masse else "—"
            ziel = sponsor["link"] if sponsor["link"] not in ("#", "") else "(kein Link)"

            # Ein Logo kann selbst schon WebP sein - dann braucht es keine
            # zusaetzliche <source>-Zeile und die waere trotzdem "nein".
            endung = os.path.splitext(sponsor["bild"])[1].lstrip(".").upper()
            logo = endung if (sponsor["webp"] or endung == "WEBP") else f"{endung} (kein WebP)"

            self.baum.insert("", "end", iid=str(nummer),
                             values=(B.lesbar(sponsor["name"]), ziel, groesse, logo))

        B.knopf(self.inhalt, "Alle Logo-Größen neu berechnen", self.groessen_neu,
                self.s).pack(anchor="w", pady=(12, 0))
        tk.Label(self.inhalt, bg=B.FARBEN["grund"], fg=B.FARBEN["gedimmt"],
                 font=self.s.klein, justify="left", anchor="w", wraplength=640,
                 text=("Jedes Logo bekommt eine eigene Größe, damit alle dieselbe FLÄCHE "
                       "einnehmen — sonst wirken hochkante Logos halb so groß wie "
                       "querformatige. Nach einem Logo-Tausch neu berechnen lassen.")).pack(
                           anchor="w", pady=(8, 0))

    def _zeige_links(self, liste):
        html = sp.lade_html()
        try:
            self.eintraege, _, _, _ = sp.finde_links(html, liste["anker"])
        except ValueError as fehler:
            B.karte(self.inhalt, self.s, 0, "Liste nicht gefunden", str(fehler))
            self.baum = None
            return

        B.abschnitt(self.inhalt, self.s, liste["name"], f"{len(self.eintraege)} Einträge")

        if not self.eintraege:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Noch keine Einträge.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Name", "Adresse", "Sinnbild"),
                                 (220, 330, 130),
                                 hoehe=min(len(self.eintraege), 12),
                                 zeilenzahl=len(self.eintraege))
        for nummer, eintrag in enumerate(self.eintraege):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(B.lesbar(eintrag["name"]), eintrag["link"],
                                     eintrag["sinnbild"].split()[-1]))

    def _zeige_zahlen(self):
        html = sp.lade_html()
        self.eintraege = list(sp.ZAHL_MUSTER.finditer(html))

        B.abschnitt(self.inhalt, self.s, "Zahlen im Kopf der Seite",
                    f"{len(self.eintraege)} Angaben")

        if not self.eintraege:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Keine Zahlen gefunden.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Zahl", "Beschriftung"), (140, 530),
                                 hoehe=min(len(self.eintraege), 10),
                                 zeilenzahl=len(self.eintraege))
        for nummer, treffer in enumerate(self.eintraege):
            self.baum.insert("", "end", iid=str(nummer),
                             values=(B.lesbar(treffer.group(2)), B.lesbar(treffer.group(4))))

    def _zeige_aufruf(self):
        html = sp.lade_html()
        self.eintraege = []

        einleitung = sp.AUFRUF_TEXT_MUSTER.search(html)
        knopf = sp.AUFRUF_KNOPF_MUSTER.search(html)
        vorteile = list(sp.VORTEIL_MUSTER.finditer(html))

        B.abschnitt(self.inhalt, self.s, "Aufruf „Werde Sponsor“",
                    f"{len(vorteile)} Vorteils-Kästen")

        zeilen = []
        if einleitung:
            self.eintraege.append(("einleitung", einleitung))
            zeilen.append(("Einleitungstext",
                           B.lesbar(re.sub(r"<[^>]+>", " ", einleitung.group(2)).strip())))
        for treffer in vorteile:
            self.eintraege.append(("vorteil", treffer))
            zeilen.append((f"Vorteil: {B.lesbar(treffer.group(2))}",
                           B.lesbar(treffer.group(4).strip())))
        if knopf:
            self.eintraege.append(("knopf", knopf))
            zeilen.append(("Beschriftung der Schaltfläche",
                           B.lesbar(knopf.group(2).strip())))

        if not zeilen:
            B.karte(self.inhalt, self.s, uebersicht.INFO, "Aufruf-Bereich nicht gefunden.")
            self.baum = None
            return

        self.baum = self.tabelle(self.inhalt, ("Teil", "Inhalt"), (230, 440),
                                 hoehe=min(len(zeilen), 10), zeilenzahl=len(zeilen))
        for nummer, (teil, inhalt) in enumerate(zeilen):
            self.baum.insert("", "end", iid=str(nummer), values=(teil, inhalt))

    def _gewaehlt(self):
        if not self.baum or not self.baum.selection():
            messagebox.showinfo("Nichts gewählt",
                                "Bitte zuerst eine Zeile in der Liste anklicken.")
            return None
        return int(self.baum.selection()[0])

    # -------------------------------------------------- Neu
    def neu(self):
        if self.bereich.get() == SPONSOREN:
            self._sponsor_neu()
        elif self._linkliste():
            self._link_neu(self._linkliste())

    def _sponsor_neu(self):
        html = sp.lade_html()
        sponsoren = sp.finde_sponsoren(html)
        frei = sp.freie_logodateien(html)

        if not frei:
            messagebox.showinfo(
                "Kein freies Logo",
                "In media/sponsoren/ liegt keine Datei, die noch keiner Bande "
                "zugeordnet ist.\n\nBitte das Logo zuerst dort ablegen — "
                "Dateiname klein, ohne Umlaute und Leerzeichen.")
            return

        felder = [
            {"schluessel": "datei", "beschriftung": "Logo-Datei", "art": "auswahl",
             "optionen": [os.path.basename(p) for p in frei]},
            {"schluessel": "name", "beschriftung": "Name"},
            {"schluessel": "link", "beschriftung": "Webseite", "pflicht": False,
             "hinweis": "leer = kein Link"},
        ]
        if sponsoren:
            felder.append({"schluessel": "stelle", "beschriftung": "Position",
                           "art": "auswahl",
                           "optionen": [self.VORNE] +
                                       [f"Nach {B.lesbar(s['name'])}" for s in sponsoren]})

        werte = B.frage_formular(
            self.rahmen, self.s, "Neue Sponsoren-Bande", felder,
            einleitung="Die WebP-Fassung wird erzeugt und die Anzeigegröße so "
                       "berechnet, dass das Logo dieselbe Fläche einnimmt wie die "
                       "anderen.")
        if not werte:
            return

        quelle = next(p for p in frei if os.path.basename(p) == werte["datei"])
        try:
            webp_name = sp.erzeuge_webp(quelle)
        except Exception as fehler:
            messagebox.showerror("WebP fehlgeschlagen", str(fehler))
            return

        bild_relativ = f"../media/sponsoren/{os.path.basename(quelle)}"
        webp_relativ = f"../media/sponsoren/{webp_name}" if webp_name else ""

        masse = sp.bildmasse(bild_relativ)
        if not masse:
            messagebox.showerror("Bild nicht lesbar",
                                 f"{bild_relativ} konnte nicht geöffnet werden.")
            return
        breite, hoehe = sp.anzeigegroesse(*masse)

        karte = sp.baue_karte(B.fuer_html(werte["name"]), werte["link"] or "#",
                              bild_relativ, webp_relativ, breite, hoehe)

        stelle = 0
        if sponsoren:
            moeglichkeiten = [self.VORNE] + [f"Nach {B.lesbar(s['name'])}" for s in sponsoren]
            stelle = moeglichkeiten.index(werte["stelle"])

        h.schreibe_datei(sp.SPONSOREN_HTML,
                         sp.fuege_sponsor_ein(html, karte, sponsoren, stelle))
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def _link_felder(self, eintrag=None):
        sinnbilder = [f"{name}  ({klasse.split()[-1]})" for name, klasse in sp.SINNBILDER]
        vorgabe = sinnbilder[0]
        if eintrag:
            passend = [s for s, (_, k) in zip(sinnbilder, sp.SINNBILDER)
                       if k == eintrag["sinnbild"]]
            vorgabe = passend[0] if passend else sinnbilder[0]
        return [
            {"schluessel": "name", "beschriftung": "Name"},
            {"schluessel": "link", "beschriftung": "Adresse",
             "hinweis": "vollständig mit https://"},
            {"schluessel": "sinnbild", "beschriftung": "Sinnbild", "art": "auswahl",
             "optionen": sinnbilder},
        ], vorgabe

    def _link_neu(self, liste):
        html = sp.lade_html()
        eintraege, start, ende, inhalt = sp.finde_links(html, liste["anker"])
        felder, vorgabe = self._link_felder()

        werte = B.frage_formular(self.rahmen, self.s, f"Neuer Eintrag — {liste['name']}",
                                 felder, {"sinnbild": vorgabe},
                                 einleitung="Wird unten an die Liste angehängt.")
        if not werte:
            return

        klasse = dict(zip([f"{n}  ({k.split()[-1]})" for n, k in sp.SINNBILDER],
                          [k for _, k in sp.SINNBILDER]))[werte["sinnbild"]]
        eintraege.append({"name": B.fuer_html(werte["name"]), "link": werte["link"],
                          "sinnbild": klasse})
        sp.schreibe_links(html, start, ende, eintraege, inhalt)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Bearbeiten
    def bearbeiten(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return
        art = self.bereich.get()
        if art == SPONSOREN:
            self._sponsor_bearbeiten(nummer)
        elif self._linkliste():
            self._link_bearbeiten(self._linkliste(), nummer)
        elif art == ZAHLEN:
            self._zahl_bearbeiten(nummer)
        else:
            self._aufruf_bearbeiten(nummer)

    def _sponsor_bearbeiten(self, nummer):
        sponsor = self.eintraege[nummer]
        werte = B.frage_formular(
            self.rahmen, self.s, "Sponsoren-Bande bearbeiten", [
                {"schluessel": "name", "beschriftung": "Name"},
                {"schluessel": "link", "beschriftung": "Webseite", "pflicht": False,
                 "hinweis": "leer = kein Link"},
            ],
            {"name": B.lesbar(sponsor["name"]),
             "link": "" if sponsor["link"] in ("#", "") else sponsor["link"]},
            einleitung="Die Anzeigegröße wird aus dem Logo neu berechnet.")
        if not werte:
            return

        masse = sp.bildmasse(sponsor["bild"])
        if masse:
            breite, hoehe = sp.anzeigegroesse(*masse)
        else:
            alt = re.search(r'width="(\d+)"\s+height="(\d+)"', sponsor["match"].group(0))
            breite, hoehe = (int(alt.group(1)), int(alt.group(2))) if alt else (120, 80)
            messagebox.showwarning(
                "Logo-Datei fehlt",
                f"{sponsor['bild']} wurde nicht gefunden — die bisherige Größe "
                "bleibt stehen.")

        karte = sp.baue_karte(B.fuer_html(werte["name"]), werte["link"] or "#",
                              sponsor["bild"], sponsor["webp"], breite, hoehe)
        html = sp.lade_html()
        aktuell = sp.finde_sponsoren(html)
        if nummer >= len(aktuell):
            messagebox.showerror("Nicht mehr vorhanden",
                                 "Die Bande wurde zwischenzeitlich entfernt.")
            self.aktualisieren()
            return

        h.schreibe_datei(sp.SPONSOREN_HTML,
                         sp.ersetze_sponsor(html, aktuell[nummer], karte))
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def _link_bearbeiten(self, liste, nummer):
        html = sp.lade_html()
        eintraege, start, ende, inhalt = sp.finde_links(html, liste["anker"])
        if nummer >= len(eintraege):
            self.aktualisieren()
            return

        felder, vorgabe = self._link_felder(eintraege[nummer])
        werte = B.frage_formular(
            self.rahmen, self.s, "Eintrag bearbeiten", felder,
            {"name": B.lesbar(eintraege[nummer]["name"]),
             "link": eintraege[nummer]["link"], "sinnbild": vorgabe})
        if not werte:
            return

        klasse = dict(zip([f"{n}  ({k.split()[-1]})" for n, k in sp.SINNBILDER],
                          [k for _, k in sp.SINNBILDER]))[werte["sinnbild"]]
        eintraege[nummer] = {"name": B.fuer_html(werte["name"]), "link": werte["link"],
                             "sinnbild": klasse}
        sp.schreibe_links(html, start, ende, eintraege, inhalt)
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def _zahl_bearbeiten(self, nummer):
        treffer = self.eintraege[nummer]
        werte = B.frage_formular(
            self.rahmen, self.s, "Zahl bearbeiten", [
                {"schluessel": "zahl", "beschriftung": "Zahl",
                 "hinweis": "Freitext, z. B. „100+“"},
                {"schluessel": "text", "beschriftung": "Beschriftung"},
            ],
            {"zahl": B.lesbar(treffer.group(2)), "text": B.lesbar(treffer.group(4))})
        if not werte:
            return

        html = sp.lade_html()
        alle = list(sp.ZAHL_MUSTER.finditer(html))
        if nummer >= len(alle):
            self.aktualisieren()
            return

        m = alle[nummer]
        ersatz = (m.group(1) + B.fuer_html(werte["zahl"]) + m.group(3)
                  + B.fuer_html(werte["text"]) + m.group(5))
        h.schreibe_datei(sp.SPONSOREN_HTML, html[:m.start()] + ersatz + html[m.end():])
        self.aktualisieren()
        self.app.fuss_auffrischen()

    def _aufruf_bearbeiten(self, nummer):
        art, treffer = self.eintraege[nummer]

        if art == "einleitung":
            felder = [{"schluessel": "text", "beschriftung": "Einleitung",
                       "art": "mehrzeilig"}]
            werte = {"text": B.lesbar(re.sub(r"<[^>]+>", " ", treffer.group(2)).strip())}
            muster, gruppe = sp.AUFRUF_TEXT_MUSTER, 2
        elif art == "knopf":
            felder = [{"schluessel": "text", "beschriftung": "Beschriftung"}]
            werte = {"text": B.lesbar(treffer.group(2).strip())}
            muster, gruppe = sp.AUFRUF_KNOPF_MUSTER, 2
        else:
            felder = [
                {"schluessel": "titel", "beschriftung": "Überschrift"},
                {"schluessel": "text", "beschriftung": "Text", "art": "mehrzeilig"},
            ]
            werte = {"titel": B.lesbar(treffer.group(2)),
                     "text": B.lesbar(treffer.group(4).strip())}
            muster, gruppe = sp.VORTEIL_MUSTER, None

        neu = B.frage_formular(self.rahmen, self.s, "Aufruf bearbeiten", felder, werte)
        if not neu:
            return

        html = sp.lade_html()
        if art == "vorteil":
            alle = list(sp.VORTEIL_MUSTER.finditer(html))
            eigene = [n for n, (a, _) in enumerate(self.eintraege) if a == "vorteil"]
            stelle = eigene.index(nummer)
            if stelle >= len(alle):
                self.aktualisieren()
                return
            m = alle[stelle]
            ersatz = (m.group(1) + B.fuer_html(neu["titel"]) + m.group(3)
                      + B.fuer_html(neu["text"]) + m.group(5))
        else:
            m = muster.search(html)
            if not m:
                self.aktualisieren()
                return
            ersatz = m.group(1) + B.fuer_html(neu["text"]) + m.group(3)

        h.schreibe_datei(sp.SPONSOREN_HTML, html[:m.start()] + ersatz + html[m.end():])
        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Loeschen
    def loeschen(self):
        nummer = self._gewaehlt()
        if nummer is None:
            return

        if self.bereich.get() == SPONSOREN:
            sponsor = self.eintraege[nummer]
            if not messagebox.askyesno(
                    "Bande löschen",
                    f"{B.lesbar(sponsor['name'])}\n\n"
                    "Die Logo-Dateien bleiben liegen — nur die Bande verschwindet.\n\n"
                    "Wirklich löschen?"):
                return
            html = sp.lade_html()
            aktuell = sp.finde_sponsoren(html)
            if nummer < len(aktuell):
                h.schreibe_datei(sp.SPONSOREN_HTML,
                                 sp.entferne_sponsor(html, aktuell[nummer]))

        elif self._linkliste():
            liste = self._linkliste()
            if not messagebox.askyesno(
                    "Eintrag löschen",
                    f"{B.lesbar(self.eintraege[nummer]['name'])}\n\nWirklich löschen?"):
                return
            html = sp.lade_html()
            eintraege, start, ende, inhalt = sp.finde_links(html, liste["anker"])
            if nummer < len(eintraege):
                del eintraege[nummer]
                sp.schreibe_links(html, start, ende, eintraege, inhalt)

        self.aktualisieren()
        self.app.fuss_auffrischen()

    # -------------------------------------------------- Groessen
    def groessen_neu(self):
        html = sp.lade_html()
        sponsoren = sp.finde_sponsoren(html)

        aenderungen = []
        for sponsor in sponsoren:
            masse = sp.bildmasse(sponsor["bild"])
            if not masse:
                continue
            breite, hoehe = sp.anzeigegroesse(*masse)
            alt = re.search(r'width="(\d+)"\s+height="(\d+)"', sponsor["match"].group(0))
            if alt and (int(alt.group(1)), int(alt.group(2))) != (breite, hoehe):
                aenderungen.append((sponsor["name"], alt.group(1), alt.group(2),
                                    breite, hoehe))

        if not aenderungen:
            messagebox.showinfo("Nichts zu tun",
                                "Alle Anzeigegrößen stimmen bereits.")
            return

        liste = "\n".join(f"  {name}: {ab}×{ah}  →  {nb}×{nh}"
                          for name, ab, ah, nb, nh in aenderungen)
        if not messagebox.askyesno("Größen neu berechnen",
                                   f"{len(aenderungen)} Logo(s) ändern sich:\n\n"
                                   f"{liste}\n\nÜbernehmen?"):
            return

        # Von hinten nach vorne, damit fruehere Positionen gueltig bleiben
        for sponsor in reversed(sponsoren):
            masse = sp.bildmasse(sponsor["bild"])
            if not masse:
                continue
            breite, hoehe = sp.anzeigegroesse(*masse)
            karte = sp.baue_karte(sponsor["name"], sponsor["link"], sponsor["bild"],
                                  sponsor["webp"], breite, hoehe)
            html = sp.ersetze_sponsor(html, sponsor, karte)

        h.schreibe_datei(sp.SPONSOREN_HTML, html)
        self.aktualisieren()
        self.app.fuss_auffrischen()
