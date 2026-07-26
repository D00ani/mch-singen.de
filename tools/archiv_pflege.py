# -*- coding: utf-8 -*-
"""
Interaktiv das Jahresarchiv (pages/archiv.html + media/dokumente/archiv/)
pflegen, statt HTML von Hand zu ergaenzen (siehe README Abschnitt 6).

Ausfuehren: python tools/archiv_pflege.py
"""
import os
import re
import shutil
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIV_PATH = os.path.join(ROOT, "pages", "archiv.html")
ARCHIV_MEDIA_DIR = os.path.join(ROOT, "media", "dokumente", "archiv")
WERTUNGEN_DIR = os.path.join(ROOT, "media", "dokumente", "wertungen")

JN_VALIDIERER = lambda a: None if a.lower() in ("j", "n") else "Bitte j oder n."
JAHR_VALIDIERER = lambda a: None if a.isdigit() and len(a) == 4 else "Muss eine 4-stellige Jahreszahl sein."

LISTE_ANKER = '<div style="margin-top: 30px;">'
DETAILS_MUSTER = re.compile(
    r'<details class="archive-year">\s*<summary>Saison (\d{4})</summary>\s*'
    r'<div class="archive-content">\s*<ul>(.*?)</ul>\s*</div>\s*</details>',
    re.DOTALL
)
LI_MUSTER = re.compile(
    r'<li><a href="([^"]*)" target="_blank"><i class="fa-solid fa-file-pdf"></i> (.*?)</a></li>'
)


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
    with open(ARCHIV_PATH, "r", encoding="utf-8", newline="") as f:
        return f.read()


def speichere_html(inhalt):
    with open(ARCHIV_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(inhalt)


def parse_jahre(html):
    jahre = []
    for m in DETAILS_MUSTER.finditer(html):
        lis = LI_MUSTER.findall(m.group(2))
        jahre.append({"match": m, "jahr": m.group(1), "lis": lis})
    return jahre


def zeige_jahre(jahre):
    for i, j in enumerate(jahre, start=1):
        print(f"  {i}) Saison {j['jahr']} ({len(j['lis'])} Eintrag/Eintraege)")


def zeige_lis(lis):
    for i, (href, text) in enumerate(lis, start=1):
        print(f"  {i}) {text}  ->  {href}")


def pruefe_pdf_existiert(relativer_pfad_von_seite):
    """relativer_pfad_von_seite ist relativ zu /pages/, z. B. ../media/dokumente/archiv/2026/x.pdf"""
    absoluter_pfad = os.path.normpath(os.path.join(ROOT, "pages", relativer_pfad_von_seite))
    return os.path.isfile(absoluter_pfad)


def baue_li(href, text, einrueckung):
    return f'{einrueckung}<li><a href="{href}" target="_blank"><i class="fa-solid fa-file-pdf"></i> {text}</a></li>'


def baue_details_block(jahr, lis, einrueckung="                "):
    items = "\r\n".join(baue_li(href, text, einrueckung + "    " * 3) for href, text in lis)
    return (
        f'{einrueckung}<details class="archive-year">\r\n'
        f'{einrueckung}    <summary>Saison {jahr}</summary>\r\n'
        f'{einrueckung}    <div class="archive-content">\r\n'
        f'{einrueckung}        <ul>\r\n'
        f'{items}\r\n'
        f'{einrueckung}        </ul>\r\n'
        f'{einrueckung}    </div>\r\n'
        f'{einrueckung}</details>'
    )


def frage_neuen_li_eintrag(jahr):
    print("\nNeuer Eintrag fuer dieses Jahr (z. B. 'BKC Gesamtwertung 2026 (PDF)'):")
    beschreibung = frage("  Beschreibungstext: ")

    vorschlag = f"../media/dokumente/archiv/{jahr}/BKC_Gesamtauswertung_{jahr}.pdf"
    pfad = frage_mit_default("  Pfad zur PDF (relativ zu /pages/)", vorschlag)

    if not pruefe_pdf_existiert(pfad):
        print(f"  ACHTUNG: Datei nicht gefunden unter media/dokumente/... - Pfad wird trotzdem eingetragen,")
        print("  Link bleibt aber tot, bis die Datei tatsaechlich dort hochgeladen wird.")
    return pfad, beschreibung


def kopiere_wertungs_pdf_falls_vorhanden(jahr):
    quelle = os.path.join(WERTUNGEN_DIR, f"bkcgesamtwertung_{jahr}.pdf")
    if not os.path.isfile(quelle):
        return None
    ziel_ordner = os.path.join(ARCHIV_MEDIA_DIR, jahr)
    ziel_datei = os.path.join(ziel_ordner, f"BKC_Gesamtauswertung_{jahr}.pdf")
    print(f"\nGefunden: media/dokumente/wertungen/bkcgesamtwertung_{jahr}.pdf")
    uebernehmen = frage(
        f"Als Archiv-PDF nach media/dokumente/archiv/{jahr}/BKC_Gesamtauswertung_{jahr}.pdf kopieren? (j/n): ",
        JN_VALIDIERER
    )
    if uebernehmen.lower() != "j":
        return None
    os.makedirs(ziel_ordner, exist_ok=True)
    shutil.copy2(quelle, ziel_datei)
    print(f"Kopiert nach {os.path.relpath(ziel_datei, ROOT)}")
    return f"../media/dokumente/archiv/{jahr}/BKC_Gesamtauswertung_{jahr}.pdf", f"BKC Gesamtwertung {jahr} (PDF)"


def jahr_hinzufuegen():
    html = lade_html()
    jahre = parse_jahre(html)

    jahr = frage("\nJahr der neuen Saison: ", JAHR_VALIDIERER)
    for j in jahre:
        if j["jahr"] == jahr:
            print(f"\nACHTUNG: Saison {jahr} existiert im Archiv bereits.")
            weiter = frage("Trotzdem eine weitere Saison-Box mit diesem Jahr anlegen? (j/n): ", JN_VALIDIERER)
            if weiter.lower() != "j":
                print("Abgebrochen.")
                return
            break

    os.makedirs(os.path.join(ARCHIV_MEDIA_DIR, jahr), exist_ok=True)

    lis = []
    auto = kopiere_wertungs_pdf_falls_vorhanden(jahr)
    if auto:
        lis.append(auto)

    if not lis:
        lis.append(frage_neuen_li_eintrag(jahr))

    while True:
        weiter = frage("\nNoch einen Eintrag fuer diese Saison hinzufuegen (z. B. Trainingsplan)? (j/n): ", JN_VALIDIERER)
        if weiter.lower() != "j":
            break
        lis.append(frage_neuen_li_eintrag(jahr))

    neuer_block = baue_details_block(jahr, lis)
    print("\nNeue Saison-Box:")
    print(neuer_block)
    if frage("\nIns Archiv einfuegen? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen.")
        return

    pos = html.find(LISTE_ANKER)
    if pos == -1:
        raise ValueError("Anker fuer die Archiv-Liste nicht gefunden.")
    einfuege_pos = html.find("\r\n", pos) + 2
    neues_html = html[:einfuege_pos] + neuer_block + "\r\n\r\n" + html[einfuege_pos:]
    speichere_html(neues_html)
    print(f"\nGespeichert in {os.path.relpath(ARCHIV_PATH, ROOT)}")


def jahr_loeschen():
    html = lade_html()
    jahre = parse_jahre(html)
    if not jahre:
        print("\nKeine Archiv-Jahre vorhanden.")
        return

    zeige_jahre(jahre)
    idx = int(frage(
        f"\nWelche Saison komplett loeschen? (1-{len(jahre)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(jahre) else "Ungueltige Auswahl."
    )) - 1
    jahr = jahre[idx]["jahr"]

    print(f"\nLoeschen: Saison {jahr} (alle {len(jahre[idx]['lis'])} Eintraege, HTML-Box)")
    print("HINWEIS: Die PDF-Dateien unter media/dokumente/archiv/ werden NICHT geloescht, nur der Listeneintrag.")
    if frage("Wirklich loeschen? (j/n): ", JN_VALIDIERER).lower() != "j":
        print("Abgebrochen.")
        return

    m = jahre[idx]["match"]
    start = m.start()
    while start > 0 and html[start - 1] in " \t":
        start -= 1
    ende = m.end()
    # Genau EINE angrenzende Leerzeile mitentfernen (bevorzugt die danach,
    # damit bei einem "mittleren" Block Vorgaenger und Nachfolger wieder
    # durch genau eine Leerzeile getrennt bleiben).
    if html[ende:ende + 4] == "\r\n\r\n":
        ende += 4
    elif html[:start].endswith("\r\n\r\n"):
        start -= 4
    neues_html = html[:start] + html[ende:]
    speichere_html(neues_html)
    print(f"\nGeloescht. {os.path.relpath(ARCHIV_PATH, ROOT)} aktualisiert.")


def eintrag_verwalten():
    html = lade_html()
    jahre = parse_jahre(html)
    if not jahre:
        print("\nKeine Archiv-Jahre vorhanden. Zuerst eine Saison anlegen.")
        return

    zeige_jahre(jahre)
    idx = int(frage(
        f"\nWelche Saison? (1-{len(jahre)}): ",
        lambda a: None if a.isdigit() and 1 <= int(a) <= len(jahre) else "Ungueltige Auswahl."
    )) - 1
    jahr_eintrag = jahre[idx]
    jahr = jahr_eintrag["jahr"]
    lis = list(jahr_eintrag["lis"])

    print(f"\nEintraege in Saison {jahr}:")
    zeige_lis(lis)

    print("\n1) Eintrag hinzufuegen\n2) Eintrag bearbeiten\n3) Eintrag loeschen\n0) Zurueck")
    wahl = frage("Was moechtest du tun? (0-3): ", lambda a: None if a in ("0", "1", "2", "3") else "Bitte 0-3 eingeben.")

    if wahl == "0":
        return
    elif wahl == "1":
        lis.append(frage_neuen_li_eintrag(jahr))
    elif wahl in ("2", "3"):
        if not lis:
            print("\nKeine Eintraege vorhanden.")
            return
        li_idx = int(frage(
            f"Welcher Eintrag? (1-{len(lis)}): ",
            lambda a: None if a.isdigit() and 1 <= int(a) <= len(lis) else "Ungueltige Auswahl."
        )) - 1
        if wahl == "3":
            print(f"\nLoeschen: {lis[li_idx][1]}")
            if frage("Wirklich loeschen? (j/n): ", JN_VALIDIERER).lower() != "j":
                print("Abgebrochen.")
                return
            del lis[li_idx]
        else:
            href, text = lis[li_idx]
            neuer_text = frage_mit_default("Beschreibungstext", text)
            neuer_href = frage_mit_default("Pfad zur PDF", href)
            if frage("Aendern? (j/n): ", JN_VALIDIERER).lower() != "j":
                print("Abgebrochen.")
                return
            lis[li_idx] = (neuer_href, neuer_text)

    neuer_block = baue_details_block(jahr, lis)
    m = jahr_eintrag["match"]
    neues_html = html[:m.start()] + neuer_block + html[m.end():]
    speichere_html(neues_html)
    print(f"\nGespeichert in {os.path.relpath(ARCHIV_PATH, ROOT)}")


def main():
    print("=" * 60)
    print("  Jahresarchiv pflegen")
    print("=" * 60)
    while True:
        html = lade_html()
        print("\nVorhandene Saisons:")
        zeige_jahre(parse_jahre(html))
        print("\n1) Neue Saison anlegen\n2) Eintraege einer Saison verwalten\n3) Ganze Saison loeschen\n0) Beenden")
        wahl = frage("Was moechtest du tun? (0-3): ", lambda a: None if a in ("0", "1", "2", "3") else "Bitte 0-3 eingeben.")
        try:
            if wahl == "0":
                break
            elif wahl == "1":
                jahr_hinzufuegen()
            elif wahl == "2":
                eintrag_verwalten()
            else:
                jahr_loeschen()
        except ValueError as e:
            print(f"\nFehler: {e}")
    print("\nFertig.")


if __name__ == "__main__":
    main()
