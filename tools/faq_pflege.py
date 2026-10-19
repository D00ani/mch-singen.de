# -*- coding: utf-8 -*-
"""
Fragen & Antworten auf pages/faq.html pflegen.

Damit man kein HTML tippen muss, gibt es eine einfache Schreibweise:
    **fett**                  ->  fetter Text
    [Kartsport](kartsport.html)  ->  Link auf eine andere Seite
Beim Bearbeiten wird bestehendes HTML in dieselbe Schreibweise
zurueckverwandelt, sodass nichts verlorengeht.

Ausfuehren: python tools/faq_pflege.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
FAQ_HTML = os.path.join(ROOT, "pages", "faq.html")

CONTAINER_ANKER = '<div class="faq-container">'
# Die Frage ist seit dem Barrierefreiheits-Umbau ein <button> mit
# aria-Attributen, die Antwort traegt eine id. Das alte Muster kannte nur
# <div class="faq-question"> ohne Attribute und fand dadurch KEINE einzige
# Frage mehr. Erkannt werden jetzt beide Schreibweisen.
FRAGE_MUSTER = re.compile(
    r'<div class="faq-item">\s*'
    r'<(?P<tag>div|button)\b[^>]*\bclass="faq-question"[^>]*>\s*<span>(?P<frage>.*?)</span>\s*'
    r'<i class="[^"]*"[^>]*></i>\s*</(?P=tag)>\s*'
    r'<div class="faq-answer"[^>]*>\s*(?P<antwort>.*?)\s*</div>\s*</div>',
    re.DOTALL,
)

# Was die einfache Schreibweise abbilden kann. Steckt mehr in einer Antwort
# (z. B. das Kart-Foto), ginge es beim Zurueckverwandeln verloren.
EINFACHE_TAGS = {"a", "strong", "b", "br"}

# Seiten, auf die sich in Antworten haeufig verlinken laesst
BEKANNTE_SEITEN = [
    "kartsport.html", "trialsport.html", "mitglied-werden.html", "kontakt.html",
    "aktuelles.html", "statistiken.html", "sommerferienprogramm.html",
    "ueber-uns.html", "geschichte.html", "sponsoren-links.html", "archiv.html",
]


def html_zu_einfach(text):
    """HTML einer Antwort in die einfache Schreibweise umwandeln."""
    text = re.sub(r'<a href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def einfach_zu_html(text):
    """Einfache Schreibweise zurueck in HTML."""
    def link(m):
        name, ziel = m.group(1), m.group(2)
        # Externe Seiten oeffnen wie ueberall auf der Website in einem
        # neuen Tab - html_zu_einfach() hatte diese Angaben abgestreift.
        if ziel.startswith(("http://", "https://")):
            return f'<a href="{ziel}" target="_blank" rel="noopener noreferrer">{name}</a>'
        return f'<a href="{ziel}">{name}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text.strip()


def hat_sonderinhalt(antwort_html):
    """True, wenn die Antwort mehr enthaelt als die einfache Schreibweise
    kennt (Bild, Absatz ...) - das ginge beim Bearbeiten verloren."""
    tags = {t.lower() for t in re.findall(r"</?([a-zA-Z][a-zA-Z0-9]*)", antwort_html)}
    return bool(tags - EINFACHE_TAGS)


def lade_html():
    return h.lies_datei(FAQ_HTML)


def zeilenende(html):
    """Zeilenende des FAQ-Bereichs ('\\n' oder '\\r\\n'), damit neue
    Eintraege keine gemischten Zeilenenden in die Datei bringen."""
    anker = html.find(CONTAINER_ANKER)
    if anker != -1:
        ende = html.find("\n", anker)
        if ende > 0 and html[ende - 1] == "\r":
            return "\r\n"
    return "\n"


def nummern_ordnen(html):
    """Vergibt die Verknuepfung Frage <-> Antwort (aria-controls / id)
    fortlaufend neu. Nach Einfuegen, Verschieben oder Loeschen passen die
    Nummern sonst nicht mehr - oder zwei Antworten haetten dieselbe id."""
    for attribut in ("aria-controls", "id"):
        zaehler = iter(range(1, 10_000))
        html = re.sub(rf'\b{attribut}="faq-antwort-\d+"',
                      lambda _: f'{attribut}="faq-antwort-{next(zaehler)}"', html)
    return html


def speichere_html(html):
    h.schreibe_datei(FAQ_HTML, nummern_ordnen(html))


def finde_fragen(html):
    return [{"match": m, "frage": m.group("frage").strip(),
             "antwort_html": m.group("antwort").strip()}
            for m in FRAGE_MUSTER.finditer(html)]


def baue_eintrag(frage, antwort_html, einrueckung=" " * 12, nl="\n"):
    # Gleicher Aufbau wie die vorhandenen Fragen auf der Seite: <button>
    # fuer die Tastaturbedienung, aria-controls/id verknuepfen Frage und
    # Antwort. Die Nummer 0 ist ein Platzhalter - die richtige vergibt
    # nummern_ordnen() beim Speichern.
    return nl.join([
        f'{einrueckung}<div class="faq-item">',
        f'{einrueckung}    <button type="button" class="faq-question" aria-expanded="false" aria-controls="faq-antwort-0">',
        f"{einrueckung}        <span>{frage}</span>",
        f'{einrueckung}        <i class="fa-solid fa-chevron-down faq-icon"></i>',
        f"{einrueckung}    </button>",
        f'{einrueckung}    <div class="faq-answer" id="faq-antwort-0" role="region">',
        f"{einrueckung}        {antwort_html}",
        f"{einrueckung}    </div>",
        f"{einrueckung}</div>",
    ])


def kurz(text, laenge=70):
    text = html_zu_einfach(text)
    return text if len(text) <= laenge else text[:laenge - 1] + "…"


def erklaere_schreibweise():
    print("\nSo kannst du die Antwort schreiben (kein HTML noetig):")
    print("  **wichtig**                     -> wichtig (fett)")
    print("  [Kartsport](kartsport.html)     -> Link auf die Kartsport-Seite")
    print("  Verlinkbare Seiten: " + ", ".join(BEKANNTE_SEITEN[:5]) + ", ...")


def pruefe_links(antwort_html):
    """Warnt, wenn eine verlinkte Seite gar nicht existiert."""
    for ziel in re.findall(r'<a href="([^"]*)"', antwort_html):
        if ziel.startswith(("http", "#", "mailto:")):
            continue
        if not os.path.isfile(os.path.join(ROOT, "pages", ziel)):
            print(f"  ACHTUNG: Die verlinkte Seite '{ziel}' gibt es nicht.")


def frage_hinzufuegen():
    html = lade_html()
    fragen = finde_fragen(html)

    erklaere_schreibweise()
    eingaben = h.formular([
        ("frage", lambda _: h.frage("\nFrage: ")),
        ("antwort", lambda _: h.frage("Antwort: ")),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    antwort_html = einfach_zu_html(eingaben["antwort"])
    pruefe_links(antwort_html)

    print(f"\nFrage:   {eingaben['frage']}")
    print(f"Antwort: {eingaben['antwort']}")
    if not h.frage_ja("Hinzufuegen? (j/n): "):
        print("Abgebrochen.")
        return

    stelle = len(fragen)
    if fragen:
        moeglichkeiten = [f"Ganz oben (vor '{kurz(fragen[0]['frage'], 45)}')"]
        moeglichkeiten += [f"Nach '{kurz(f['frage'], 45)}'" for f in fragen]
        stelle = h.waehle_option("An welcher Stelle?", moeglichkeiten)

    nl = zeilenende(html)
    neuer_eintrag = baue_eintrag(eingaben["frage"], antwort_html, nl=nl)

    if not fragen:
        anker = html.find(CONTAINER_ANKER)
        if anker == -1:
            raise ValueError("Der FAQ-Bereich wurde in faq.html nicht gefunden.")
        einfuegepunkt = html.find("\n", anker) + 1
        neues_html = html[:einfuegepunkt] + neuer_eintrag + nl + html[einfuegepunkt:]
    elif stelle == 0:
        anfang = fragen[0]["match"].start()
        while anfang > 0 and html[anfang - 1] in " \t":
            anfang -= 1
        neues_html = html[:anfang] + neuer_eintrag + nl + nl + html[anfang:]
    else:
        ende = fragen[stelle - 1]["match"].end()
        neues_html = html[:ende] + nl + nl + neuer_eintrag + html[ende:]

    speichere_html(neues_html)
    print(f"\nGespeichert in {os.path.relpath(FAQ_HTML, ROOT)}")


def frage_bearbeiten():
    html = lade_html()
    fragen = finde_fragen(html)

    index = h.waehle_aus_liste(fragen, "bearbeiten", lambda f: kurz(f["frage"]))
    if index is None:
        return
    eintrag = fragen[index]

    alte_antwort = html_zu_einfach(eintrag["antwort_html"])
    print(f"\nFrage:   {eintrag['frage']}")
    print(f"Antwort: {alte_antwort}")
    if hat_sonderinhalt(eintrag["antwort_html"]):
        print("\nHINWEIS: Diese Antwort enthaelt ein Bild oder eine Formatierung, die die")
        print("einfache Schreibweise nicht kennt. Bleibt die Antwort unveraendert, bleibt")
        print("auch das erhalten. Wird sie geaendert, geht es verloren.")
    erklaere_schreibweise()
    print("\nEnter = unveraendert lassen, x = ein Feld zurueck.\n")

    eingaben = h.formular([
        ("frage", lambda _: h.frage_mit_default("Frage", eintrag["frage"])),
        ("antwort", lambda _: h.frage_mit_default("Antwort", alte_antwort)),
    ])
    if eingaben is None:
        print("Abgebrochen.")
        return

    if eingaben["antwort"] == alte_antwort:
        # Antwort nicht angefasst -> Original-HTML behalten (Bilder, Absaetze)
        antwort_html = eintrag["antwort_html"]
    else:
        antwort_html = einfach_zu_html(eingaben["antwort"])
        pruefe_links(antwort_html)

    if eingaben["frage"] == eintrag["frage"] and eingaben["antwort"] == alte_antwort:
        print("\nNichts geaendert.")
        return
    if not h.frage_ja("Aendern? (j/n): "):
        print("Abgebrochen.")
        return

    m = eintrag["match"]
    anfang = m.start()
    while anfang > 0 and html[anfang - 1] in " \t":
        anfang -= 1
    neuer_eintrag = baue_eintrag(eingaben["frage"], antwort_html, nl=zeilenende(html))
    speichere_html(html[:anfang] + neuer_eintrag + html[m.end():])
    print(f"\nGespeichert in {os.path.relpath(FAQ_HTML, ROOT)}")


def frage_loeschen():
    html = lade_html()
    fragen = finde_fragen(html)

    index = h.waehle_aus_liste(fragen, "loeschen", lambda f: kurz(f["frage"]))
    if index is None:
        return

    print(f"\nLoeschen: {fragen[index]['frage']}")
    if not h.frage_ja("Wirklich loeschen? (j/n): "):
        print("Abgebrochen.")
        return

    m = fragen[index]["match"]
    anfang = m.start()
    while anfang > 0 and html[anfang - 1] in " \t":
        anfang -= 1
    ende = m.end()
    while ende < len(html) and html[ende] in "\r\n":
        ende += 1

    speichere_html(html[:anfang] + html[ende:])
    print(f"\nGeloescht. {os.path.relpath(FAQ_HTML, ROOT)} aktualisiert.")


def main():
    print("=" * 60)
    print("  Fragen & Antworten pflegen")
    print("=" * 60)
    while True:
        fragen = finde_fragen(lade_html())
        print(f"\n{len(fragen)} Fragen auf der Seite:")
        for i, eintrag in enumerate(fragen, start=1):
            print(f"  {i}) {kurz(eintrag['frage'])}")

        aktion = h.menue("Was moechtest du tun?", [
            ("Frage hinzufuegen", frage_hinzufuegen),
            ("Frage bearbeiten", frage_bearbeiten),
            ("Frage entfernen", frage_loeschen),
        ])
        if aktion is None:
            break
        try:
            h.fuehre_aus(aktion)
        except ValueError as fehler:
            print(f"\nFehler: {fehler}")
    print("\nFertig.")


if __name__ == "__main__":
    main()
