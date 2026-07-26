# -*- coding: utf-8 -*-
"""
Interaktiv die Vereinsmeister/Wanderpokal-Tabellen und die
"Vereinsbestleistungen"-Rekord-Boxen in pages/statistiken.html pflegen,
statt HTML von Hand zu kopieren/bearbeiten (siehe README Abschnitt 5).

Ausfuehren: python tools/statistiken_pflege.py
"""
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATISTIKEN_PATH = os.path.join(ROOT, "pages", "statistiken.html")

JN_VALIDIERER = lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n."

WANDERPOKAL_TABELLEN = [
    {"name": "Wanderpokal-Sieger (Jugend)", "anker": "Die Wanderpokal-Sieger (Jugend)"},
    {"name": "Wanderpokal-Sieger (Erwachsen)", "anker": "Die Wanderpokal-Sieger (Erwachsen)"},
]


def frage(text, validierer=None, pflicht=True):
    while True:
        antwort = input(text).strip()
        if not antwort:
            if pflicht:
                print("  -> Darf nicht leer sein.")
                continue
            return antwort
        if validierer:
            fehler = validierer(antwort)
            if fehler:
                print(f"  -> {fehler}")
                continue
        return antwort


def frage_mit_default(text, default):
    antwort = input(f"{text} [{default}]: ").strip()
    return antwort if antwort else default


def lade_html():
    with open(STATISTIKEN_PATH, "r", encoding="utf-8", newline="") as f:
        return f.read()


def speichere_html(inhalt):
    with open(STATISTIKEN_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(inhalt)


# ------------------------------------------------------------------
# Wanderpokal-Tabellen (Jahr;Gewinner/in;Klasse)
# ------------------------------------------------------------------

def finde_tbody(html, anker_text):
    pos = html.find(anker_text)
    if pos == -1:
        raise ValueError(f"Anker '{anker_text}' nicht in statistiken.html gefunden.")
    start_tag = html.find("<tbody>", pos)
    ende_tag = html.find("</tbody>", start_tag)
    if start_tag == -1 or ende_tag == -1:
        raise ValueError("Zugehoerige <tbody>...</tbody> nicht gefunden.")
    return start_tag + len("<tbody>"), ende_tag


def parse_zeilen(tbody_inhalt):
    return [re.findall(r"<td>(.*?)</td>", m.group(1), re.DOTALL)
            for m in re.finditer(r"<tr>(.*?)</tr>", tbody_inhalt, re.DOTALL)]


def erkenne_einrueckung(tbody_inhalt):
    m = re.search(r"[ \t]*<tr>", tbody_inhalt)
    return m.group(0)[:-len("<tr>")] if m else "                    "


def baue_zeile(werte, einrueckung):
    tds = "".join(f"<td>{w}</td>" for w in werte)
    return f"{einrueckung}<tr>{tds}</tr>"


def waehle_tabelle():
    print("\nWelche Tabelle?")
    for i, t in enumerate(WANDERPOKAL_TABELLEN, start=1):
        print(f"  {i}) {t['name']}")
    auswahl = frage(
        f"Auswahl (1-{len(WANDERPOKAL_TABELLEN)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(WANDERPOKAL_TABELLEN) else "Ungueltige Auswahl."
    )
    return WANDERPOKAL_TABELLEN[int(auswahl) - 1]


def zeige_zeilen(zeilen):
    for i, z in enumerate(zeilen, start=1):
        print(f"  {i}) Jahr {z[0]} - {z[1]} ({z[2]})")


def wanderpokal_hinzufuegen():
    tabelle = waehle_tabelle()
    html = lade_html()
    start, ende = finde_tbody(html, tabelle["anker"])
    tbody_inhalt = html[start:ende]
    zeilen = parse_zeilen(tbody_inhalt)
    einrueckung = erkenne_einrueckung(tbody_inhalt)

    print(f"\nAktuelle Eintraege in '{tabelle['name']}':")
    zeige_zeilen(zeilen) if zeilen else print("  (noch keine)")

    jahr = frage("\nJahr: ", lambda a: None if a.isdigit() and len(a) == 4 else "Muss eine 4-stellige Jahreszahl sein.")
    gewinner = frage("Gewinner/in (z. B. Max M.): ")
    klasse = frage("Klasse (z. B. 3, 1c): ")

    for z in zeilen:
        if z[0] == jahr:
            print(f"\nACHTUNG: Fuer Jahr {jahr} gibt es schon einen Eintrag ({z[1]}, {z[2]}).")
            weiter = frage("Trotzdem hinzufuegen? (j/n): ", JN_VALIDIERER)
            if weiter.lower() != "j":
                print("Abgebrochen.")
                return
            break

    neue_zeile = baue_zeile([jahr, gewinner, klasse], einrueckung)
    print(f"\nNeue Zeile: {neue_zeile.strip()}")
    if frage("Hinzufuegen? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen.")
        return

    neuer_tbody_inhalt = f"\r\n{neue_zeile}{tbody_inhalt}" if not tbody_inhalt.startswith("\r\n") else \
        tbody_inhalt.replace("\r\n", f"\r\n{neue_zeile}\r\n", 1)
    # Einfacher und robuster: neue Zeile direkt nach dem Zeilenumbruch nach <tbody> einfuegen
    erster_umbruch = tbody_inhalt.find("\r\n")
    if erster_umbruch == -1:
        neuer_tbody_inhalt = f"\r\n{neue_zeile}" + tbody_inhalt
    else:
        neuer_tbody_inhalt = tbody_inhalt[:erster_umbruch + 2] + neue_zeile + "\r\n" + tbody_inhalt[erster_umbruch + 2:]

    neues_html = html[:start] + neuer_tbody_inhalt + html[ende:]
    speichere_html(neues_html)
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_PATH, ROOT)}")


def wanderpokal_bearbeiten_oder_loeschen(loeschen):
    tabelle = waehle_tabelle()
    html = lade_html()
    start, ende = finde_tbody(html, tabelle["anker"])
    tbody_inhalt = html[start:ende]
    zeilen = parse_zeilen(tbody_inhalt)
    einrueckung = erkenne_einrueckung(tbody_inhalt)

    if not zeilen:
        print("\nKeine Eintraege vorhanden.")
        return

    zeige_zeilen(zeilen)
    idx = int(frage(
        f"\nWelchen Eintrag {'loeschen' if loeschen else 'bearbeiten'}? (1-{len(zeilen)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(zeilen) else "Ungueltige Auswahl."
    )) - 1

    if loeschen:
        print(f"\nLoeschen: Jahr {zeilen[idx][0]} - {zeilen[idx][1]} ({zeilen[idx][2]})")
        if frage("Wirklich loeschen? (j/n): ", JN_VALIDIERER).lower() != "j":
            print("Abgebrochen.")
            return
        del zeilen[idx]
    else:
        print(f"\nAktuell: Jahr {zeilen[idx][0]} - {zeilen[idx][1]} ({zeilen[idx][2]})")
        jahr = frage_mit_default("Jahr", zeilen[idx][0])
        gewinner = frage_mit_default("Gewinner/in", zeilen[idx][1])
        klasse = frage_mit_default("Klasse", zeilen[idx][2])
        print(f"\nNeu: Jahr {jahr} - {gewinner} ({klasse})")
        if frage("Aendern? (j/n): ", JN_VALIDIERER).lower() != "j":
            print("Abgebrochen.")
            return
        zeilen[idx] = [jahr, gewinner, klasse]

    letzter_tr = tbody_inhalt.rfind("</tr>")
    schluss_rest = tbody_inhalt[letzter_tr + len("</tr>"):] if letzter_tr != -1 else "\r\n"
    if zeilen:
        neuer_tbody_inhalt = "\r\n" + "\r\n".join(baue_zeile(z, einrueckung) for z in zeilen) + schluss_rest
    else:
        neuer_tbody_inhalt = schluss_rest
    neues_html = html[:start] + neuer_tbody_inhalt + html[ende:]
    speichere_html(neues_html)
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_PATH, ROOT)}")


# ------------------------------------------------------------------
# Vereinsbestleistungen (Rekord-Boxen)
# ------------------------------------------------------------------

RECORD_BOX_MUSTER = re.compile(
    r'(<div class="record-box">\s*<h3>)(<i[^>]*></i>\s*)([^<]*?)(\s*</h3>\s*<p>)(.*?)(</p>\s*</div>)',
    re.DOTALL
)


def parse_record_boxes(html):
    boxen = []
    for m in RECORD_BOX_MUSTER.finditer(html):
        titel = m.group(3).strip()
        p_inhalt = m.group(5)
        teile = p_inhalt.split("<br>")
        felder = []
        for teil in teile:
            fm = re.match(r"<strong>(.*?)</strong>\s*(.*)", teil.strip(), re.DOTALL)
            if fm:
                felder.append((fm.group(1).strip().rstrip(":"), fm.group(2).strip()))
        boxen.append({"match": m, "titel": titel, "felder": felder})
    return boxen


def record_boxen_bearbeiten():
    html = lade_html()
    boxen = parse_record_boxes(html)
    if not boxen:
        print("\nKeine Rekord-Boxen gefunden.")
        return

    print("\nVereinsbestleistungen:")
    for i, b in enumerate(boxen, start=1):
        details = ", ".join(f"{label} {wert}" for label, wert in b["felder"])
        print(f"  {i}) {b['titel']} - {details}")

    idx = int(frage(
        f"\nWelche Box bearbeiten? (1-{len(boxen)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(boxen) else "Ungueltige Auswahl."
    )) - 1
    box = boxen[idx]

    print(f"\nAktuell: {box['titel']}")
    neuer_titel = frage_mit_default("Titel", box["titel"])
    neue_felder = []
    for label, wert in box["felder"]:
        neues_label = frage_mit_default("  Feldname", label)
        neuer_wert = frage_mit_default("  Wert", wert)
        neue_felder.append((neues_label, neuer_wert))

    neuer_p_inhalt = "<br>".join(f"<strong>{label}:</strong> {wert}" for label, wert in neue_felder)

    m = box["match"]
    ersatz = m.group(1) + m.group(2) + neuer_titel + m.group(4) + neuer_p_inhalt + m.group(6)

    print(f"\nAlt: {html[m.start():m.end()]}")
    print(f"Neu: {ersatz}")
    if frage("Aendern? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen.")
        return

    neues_html = html[:m.start()] + ersatz + html[m.end():]
    speichere_html(neues_html)
    print(f"\nGespeichert in {os.path.relpath(STATISTIKEN_PATH, ROOT)}")


# ------------------------------------------------------------------
# Menue
# ------------------------------------------------------------------

def vereinsmeister_menue():
    while True:
        print("\n1) Neuen Vereinsmeister/Wanderpokal-Sieger hinzufuegen\n2) Eintrag bearbeiten\n3) Eintrag loeschen\n0) Zurueck")
        wahl = frage("Was moechtest du tun? (0-3): ", lambda a: None if a in ("0", "1", "2", "3") else "Bitte 0-3 eingeben.")
        if wahl == "0":
            return
        try:
            if wahl == "1":
                wanderpokal_hinzufuegen()
            elif wahl == "2":
                wanderpokal_bearbeiten_oder_loeschen(loeschen=False)
            else:
                wanderpokal_bearbeiten_oder_loeschen(loeschen=True)
        except ValueError as e:
            print(f"\nFehler: {e}")


def rekorde_menue():
    while True:
        try:
            record_boxen_bearbeiten()
        except ValueError as e:
            print(f"\nFehler: {e}")
        weiter = frage("\nNoch eine Box bearbeiten? (j/n): ", JN_VALIDIERER)
        if weiter.lower() != "j":
            return


def main():
    print("=" * 60)
    print("  Statistiken-Seite pflegen")
    print("=" * 60)
    while True:
        print("\n1) Vereinsmeister / Wanderpokal-Sieger\n2) Vereinsbestleistungen (Rekorde)\n0) Beenden")
        wahl = frage("Was moechtest du tun? (0-2): ", lambda a: None if a in ("0", "1", "2") else "Bitte 0-2 eingeben.")
        if wahl == "0":
            break
        elif wahl == "1":
            vereinsmeister_menue()
        else:
            rekorde_menue()
    print("\nFertig.")


if __name__ == "__main__":
    main()
