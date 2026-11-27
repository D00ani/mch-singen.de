# -*- coding: utf-8 -*-
"""
Texte und Zahlen der Webseite, die im Pflege-Fenster unter "Texte & Zahlen"
geaendert werden - dazu der Umschalter fuer den Shop-Link.

Jede pflegbare Stelle traegt im HTML eine Markierung, z. B.
    <strong data-pflege="zahl.kinder">20+</strong>
Steht derselbe Schluessel an mehreren Stellen (die Trainingszeit im
Fussbereich aller Seiten, "20+" auf Start- und Kart-Seite), aendert ein
Speichern alle gemeinsam. Neue Stellen: Markierung ins HTML setzen und
unten in FELDER eintragen.

Im markierten Element darf nur Text stehen - dazu hoechstens <strong>
(im Fenster als **fett** geschrieben) und <br> (im Fenster ein
Zeilenwechsel). Links, Bilder oder Listen gehoeren nicht hinein.

Alle Shop-Links tragen data-shop-link. Sie zeigen entweder auf die
Auffangseite pages/shop.html (solange der Shop des Anbieters nicht geht)
oder auf die Adresse des echten Shops.

Wird nicht direkt ausgefuehrt, siehe tools/pflege_fenster.py.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import vorschau

ROOT = h.ROOT

# (Gruppe, Schluessel, Beschriftung, Hinweis, Feldart)
FELDER = [
    ("Startseite", "start.kicker", "Zeile über der Überschrift", "z. B. „Gegründet 1954 · Mitglied im DMV“", "text"),
    ("Startseite", "start.lead", "Einleitung unter der Überschrift", "der erste Satz unter „Motorsport aus Leidenschaft“", "mehrzeilig"),
    ("Startseite", "start.lead-zusatz", "Zusatz zur Einleitung", "steht nur am Computer hinter der Einleitung", "text"),
    ("Startseite", "start.wer-kurz", "„Wer wir sind“ in Kurzform", "am Handy über den drei Zahlen", "mehrzeilig"),
    ("Zahlen", "zahl.gegruendet", "Gründungsjahr", "Startseite", "text"),
    ("Zahlen", "zahl.kinder", "Kinder und Jugendliche im Kart",
     "Startseite und Kart-Seite. Im Text der Kart-Seite steht die Zahl zusätzlich "
     "(„über 20 Kindern“) - den unter „Kart-Seite“ mit anpassen", "text"),
    ("Zahlen", "zahl.erwachsene", "Erwachsene und Trainer im Kart", "Kart-Seite", "text"),
    ("Zahlen", "zahl.bkc-laeufe", "BKC-Läufe pro Saison", "Startseite und Kart-Seite", "text"),
    ("Training", "training.kart-tag", "Kart-Training: Tag", "z. B. „Samstags“ - Startseite und Fußbereich aller Seiten", "text"),
    ("Training", "training.kart-zeit", "Kart-Training: Uhrzeit", "z. B. „9:00 – 13:30 Uhr“ - Startseite und Fußbereich aller Seiten", "text"),
    ("Training", "training.trial", "Trial-Training", "z. B. „Jeden 2. Samstag“ - Startseite", "text"),
    ("Adresse", "adresse.gelaende-strasse", "Trainingsgelände: Straße",
     "Startseite und Fußbereich aller Seiten. Nicht mit dabei: die Karten-Links (Google Maps), "
     "die Angaben für Suchmaschinen und die Texte auf der FAQ- und der Ferienprogramm-Seite", "text"),
    ("Adresse", "adresse.gelaende-ort", "Trainingsgelände: PLZ und Ort",
     "z. B. „78224 Singen (Hohentwiel)“ - Startseite und Fußbereich aller Seiten", "text"),
    ("Adresse", "adresse.verein-strasse", "Vereinsadresse: Straße",
     "Impressum (zweimal) und Kontaktseite. Die Angaben für Suchmaschinen auf der "
     "Startseite laufen nicht mit", "text"),
    ("Adresse", "adresse.verein-ort", "Vereinsadresse: PLZ und Ort", "Impressum und Kontaktseite", "text"),
    ("Adresse", "adresse.telefon", "Telefon", "Impressum (zweimal) und Kontaktseite", "text"),
    ("Kart-Seite", "kart.einleitung", "Einleitung oben",
     "steht am Handy noch einmal im aufklappbaren Text - beide ändern sich gemeinsam", "mehrzeilig"),
    ("Kart-Seite", "kart.buehne-satz", "Kurzsatz im Seitenkopf", "nur am Handy", "mehrzeilig"),
    ("Kart-Seite", "kart.kurz", "Kurzfassung über den Zahlen", "nur am Handy", "mehrzeilig"),
    ("Kart-Seite", "kart.slalom", "Absatz „Wir fahren hauptsächlich …“", "", "mehrzeilig"),
    ("Kart-Seite", "kart.abteilung", "Absatz „Derzeit besteht unsere Kartabteilung …“",
     "Die Zahlen hier stehen unabhängig von den Zahlen-Kacheln (Bereich „Zahlen“) - "
     "beide anpassen", "mehrzeilig"),
    ("Kart-Seite", "kart.kursplaner", "Text zum Kurs-Planer", "", "mehrzeilig"),
    ("Trial-Seite", "trial.einleitung", "Einleitung oben",
     "steht am Handy noch einmal im aufklappbaren Text - beide ändern sich gemeinsam", "mehrzeilig"),
    ("Trial-Seite", "trial.buehne-satz", "Kurzsatz im Seitenkopf", "nur am Handy", "mehrzeilig"),
    ("Trial-Seite", "trial.kurz", "Kurzfassung", "nur am Handy", "mehrzeilig"),
    ("Trial-Seite", "trial.schule", "Absatz „Ob für Kinder, Jugendliche …“", "", "mehrzeilig"),
    ("Trial-Seite", "trial.profil", "Einleitung „Was macht Trial aus?“", "", "mehrzeilig"),
    ("Trial-Seite", "trial.termine", "Hinweis auf die Termine", "über dem Link zur Partnerseite", "mehrzeilig"),
    ("Trial-Seite", "trial.faszination", "„Faszination Trialsport“: erster Satz", "", "mehrzeilig"),
    ("Trial-Seite", "trial.eigene-motorraeder", "„Faszination“: Kurzfassung", "nur am Handy", "mehrzeilig"),
    ("Trial-Seite", "trial.zuschauen", "„Faszination“: langer Absatz", "nur am Computer", "mehrzeilig"),
    ("Mitglied werden", "preis.beitrag-kinder", "Beitrag Kinder (unter 12 Jahre)", "z. B. „5,00 €“", "text"),
    ("Mitglied werden", "preis.beitrag-jugend", "Beitrag Jugendliche (12-18 Jahre)", "z. B. „10,00 €“", "text"),
    ("Mitglied werden", "preis.beitrag-erwachsene", "Beitrag Erwachsene (ab 18 Jahre)", "z. B. „15,00 €“", "text"),
    ("Mitglied werden", "preis.beitrag-eltern", "Beitrag Elternteil (Passiv/Aktiv)", "z. B. „15,00 €“", "text"),
    ("Mitglied werden", "preis.kart-erwachsene", "Training Kart (Erwachsene)", "je Training, z. B. „4,00 €“", "text"),
    ("Mitglied werden", "preis.kart-kinder", "Training Kart (Kinder)", "je Training, z. B. „3,00 €“", "text"),
    ("Mitglied werden", "preis.probetraining", "Probetraining (Kart)", "z. B. „15,00 €“", "text"),
    ("Mitglied werden", "preis.trial-erwachsene", "Training Trial (Erwachsene)", "„--,00 €“ = noch kein Preis", "text"),
    ("Mitglied werden", "preis.trial-kinder", "Training Trial (Kinder)", "„--,00 €“ = noch kein Preis", "text"),
]

SHOP_AUFFANG = "Auffangseite"
SHOP_HINWEIS = ("Die Auffangseite sagt Besuchern, dass der Shop gerade nicht erreichbar ist. "
                "Läuft der Shop wieder, hier seine Adresse eintragen.")
_STELLE = (r'<(?P<tag>[a-z][a-z0-9]*)(?P<attr>[^>]*\sdata-pflege="{schluessel}"[^>]*)>'
           r'(?P<inhalt>(?:[^<]|<br\s*/?>|<strong>[^<]*</strong>)*)</(?P=tag)>')
PREIS_MUSTER = r"(\d{1,3}(\.\d{3})*|--),\d{2} €"
_SHOP_LINK = re.compile(r'<a\s(?P<attr>[^>]*\bdata-shop-link\b[^>]*)>')
_ATTRIBUT = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)(?:="([^"]*)")?')


def html_dateien():
    """Alle veroeffentlichten Seiten (Vorschlags-Entwuerfe ausgenommen)."""
    dateien = [os.path.join(ROOT, "index.html"), os.path.join(ROOT, "404.html")]
    ordner = os.path.join(ROOT, "pages")
    dateien += [os.path.join(ordner, n) for n in sorted(os.listdir(ordner))
                if n.endswith(".html") and "vorschlag" not in n]
    return [d for d in dateien if os.path.exists(d)]


def _anzeige(datei):
    return os.path.relpath(datei, ROOT).replace("\\", "/")


def html_zu_text(inhalt):
    """HTML des markierten Elements -> Text fuers Fenster.
    <strong>x</strong> wird **x**, <br> ein Zeilenwechsel."""
    inhalt = re.sub(r"<strong>([^<]*)</strong>", r"**\1**", inhalt)
    zeilen = re.split(r"<br\s*/?>", inhalt)
    return "\n".join(" ".join(html.unescape(z).split()) for z in zeilen).strip()


def text_zu_html(wert):
    """Gegenstueck zu html_zu_text(). Leerzeilen fallen weg - ein Absatz
    in der Webseite waere ein eigenes Element."""
    zeilen = [" ".join(z.split()) for z in wert.strip().split("\n")]
    return "<br>".join(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>",
                              html.escape(z, quote=False))
                       for z in zeilen if z)


def lies_alle():
    """{schluessel: {"wert": text, "stellen": [datei, ...], "abweichend": bool}}

    abweichend: an den Stellen steht nicht ueberall dasselbe (z. B. nach
    einer Handaenderung an nur einer Seite)."""
    gefunden = {}
    muster = re.compile(_STELLE.format(schluessel=r'(?P<schluessel>[^"]+)'))
    for datei in html_dateien():
        for treffer in muster.finditer(h.lies_datei(datei)):
            wert = html_zu_text(treffer.group("inhalt"))
            eintrag = gefunden.setdefault(treffer.group("schluessel"),
                                          {"wert": wert, "stellen": [], "werte": set()})
            eintrag["stellen"].append(_anzeige(datei))
            eintrag["werte"].add(wert)
    for eintrag in gefunden.values():
        eintrag["abweichend"] = len(eintrag.pop("werte")) > 1
    return gefunden


def pruefe_wert(wert):
    """Fehlertext oder None. Nur Text - HTML gehoert nicht hierher."""
    if "<" in wert or ">" in wert:
        return "Bitte ohne spitze Klammern - hier steht nur Text."
    if wert.count("**") % 2:
        return "Fettschrift bitte mit ** davor UND dahinter, z. B. **wichtig**."
    return None


def pruefe_preis(wert):
    """Preise stehen einheitlich als "5,00 €" bzw. "--,00 €" da."""
    fehler = pruefe_wert(wert)
    if fehler:
        return fehler
    if not re.fullmatch(PREIS_MUSTER, wert.strip()):
        return ("Bitte so schreiben: 5,00 € - mit Komma, zwei Nachkommastellen, "
                "Leerzeichen und €. „--,00 €“ heißt: noch kein Preis.")
    return None


def pruefer_fuer(schluessel):
    return pruefe_preis if schluessel.startswith("preis.") else pruefe_wert


def neue_texte(schluessel, wert, markieren=False):
    """{Datei: neuer Inhalt} fuer alle Dateien, in denen sich etwas aendert.
    markieren=True setzt zusaetzlich die Vorschau-Markierung an die Stellen
    (nur fuer die Vorschau, nie zum Speichern)."""
    neu = text_zu_html(wert)
    muster = re.compile(_STELLE.format(schluessel=re.escape(schluessel)))

    def ersetzen(m):
        anfang = f"<{m.group('tag')}{m.group('attr')}>"
        if markieren:
            anfang = vorschau.markiere_tag(anfang)
        return f"{anfang}{neu}</{m.group('tag')}>"

    ergebnis = {}
    for datei in html_dateien():
        alt = h.lies_datei(datei)
        text = muster.sub(ersetzen, alt)
        if text != alt:
            ergebnis[datei] = text
    return ergebnis


def setze(schluessel, wert):
    """Schreibt wert an alle Stellen mit diesem Schluessel. Gibt die Liste
    der geaenderten Dateien zurueck. Jede Datei wird vorher gesichert und
    laesst sich ueber "Letzte Änderung rückgängig" zuruecknehmen."""
    geaendert = []
    for datei, text in neue_texte(schluessel, wert).items():
        h.schreibe_datei(datei, text)
        geaendert.append(_anzeige(datei))
    return geaendert


def zeige_vorschau(seiten, bevorzugt="index.html"):
    """Oeffnet den Entwurf {Datei: Text} im Browser. Gibt None oder einen
    Hinweis zurueck, falls sich nichts aendert."""
    if not seiten:
        return "An der Webseite ändert sich damit nichts - es gibt nichts zu zeigen."
    namen = {_anzeige(d): t for d, t in seiten.items()}
    start = bevorzugt if bevorzugt in namen else next(iter(namen))
    vorschau.entwurf_zeigen(namen, start)
    return None


def vorschau_zeigen(schluessel, wert):
    return zeige_vorschau(neue_texte(schluessel, wert, markieren=True))


# ------------------------------------------------------------------
# Shop-Link
# ------------------------------------------------------------------

def _auffang_ziel(datei):
    """Wie die Auffangseite von dieser Datei aus heisst."""
    name = _anzeige(datei)
    if name == "404.html":
        return "/pages/shop.html"     # die Fehlerseite rechnet ab der Wurzel
    return "shop.html" if name.startswith("pages/") else "pages/shop.html"


def shop_stand():
    """(SHOP_AUFFANG, None) oder ("extern", adresse) - abgelesen am ersten
    markierten Link der Startseite."""
    treffer = _SHOP_LINK.search(h.lies_datei(os.path.join(ROOT, "index.html")))
    if not treffer:
        return SHOP_AUFFANG, None
    href = dict((n, w) for n, w in _ATTRIBUT.findall(treffer.group("attr"))).get("href", "")
    return ("extern", href) if href.startswith("http") else (SHOP_AUFFANG, None)


def pruefe_shop_adresse(adresse):
    if not re.fullmatch(r"https://[^\s\"<>]+", adresse.strip()):
        return "Bitte die volle Adresse mit https:// angeben."
    return None


def shop_setzen(adresse=None):
    """adresse=None: alle Shop-Links auf die Auffangseite; sonst auf den
    echten Shop (neuer Tab). Gibt die geaenderten Dateien zurueck."""
    geaendert = []
    for datei in html_dateien():
        alt = h.lies_datei(datei)

        def neu_bauen(treffer):
            attribute = [(n, w) for n, w in _ATTRIBUT.findall(treffer.group("attr"))
                         if n not in ("href", "target", "rel")]
            vorne = [("href", adresse or _auffang_ziel(datei))]
            if adresse:
                vorne += [("target", "_blank"), ("rel", "noopener noreferrer")]
            # Werte aus dem HTML sind schon maskiert (&amp;) - erst zurueck,
            # dann einmal maskieren, sonst wird daraus &amp;amp;
            teile = [f'{n}="{html.escape(html.unescape(w))}"' if (w or n == "href") else n
                     for n, w in vorne + attribute]
            return "<a " + " ".join(teile) + ">"

        text = _SHOP_LINK.sub(neu_bauen, alt)
        if text != alt:
            h.schreibe_datei(datei, text)
            geaendert.append(_anzeige(datei))
    return geaendert
