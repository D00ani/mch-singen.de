# -*- coding: utf-8 -*-
"""
Reparaturen zu den Funden von tools/pruefe_seite.py.

Das Pruefwerkzeug sagt, WAS nicht stimmt - dieses Modul behebt es:
  - tote Verweise auf eine andere (vorhandene) Datei umbiegen, mit
    Vorschlaegen aehnlich heissender Dateien aus dem Projekt
  - eine fehlende Datei genau dort ablegen, wo der Link sie erwartet
  - falsche Gross-/Kleinschreibung in Pfaden korrigieren
  - angekuendigte PDFs in data/timer*.txt umbiegen oder austragen
  - externe Adressen auf allen Seiten ersetzen
  - alt-Texte, Seitenbeschreibungen und Schreibweisen nachtragen
  - Seiten in den Suchindex (js/suche.js) aufnehmen oder austragen
  - Build-Schritt anstossen, Fundstelle im Editor oeffnen

Jede Aenderung an einer bestehenden Datei laeuft ueber
pflege_hilfen.schreibe_datei() und legt vorher eine Sicherung an -
"Rueckgaengig" im Pflege-Fenster holt den alten Stand zurueck.

Benutzt vom Pflege-Fenster (Seite "Webseite pruefen") und von
python tools/pruefe_seite.py (Frage am Ende: "jetzt beheben?").
"""
import difflib
import html as html_modul
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import pruefe_seite as p

ROOT = h.ROOT

# Unter Windows kein schwarzes Konsolenfenster aufpoppen lassen
OHNE_FENSTER = 0x08000000 if os.name == "nt" else 0


def anzeige(pfad):
    """Pfad ab dem Hauptordner, mit Schraegstrichen - so wie auf der Webseite."""
    return os.path.relpath(pfad, ROOT).replace(os.sep, "/")


# ------------------------------------------------------------------
# Projektdateien und Vorschlaege
# ------------------------------------------------------------------

# Ordner, in denen keine Dateien fuer die Webseite liegen
NICHT_DURCHSUCHEN = {".git", ".pflege-sicherungen", "_backups", "new_site", "node_modules",
                     "__pycache__", "kurs-planer", "tools", ".claude", ".vscode"}


def projektdateien():
    for wurzel, ordner, dateien in os.walk(ROOT):
        ordner[:] = [o for o in ordner if o not in NICHT_DURCHSUCHEN and not o.startswith(".")]
        for datei in dateien:
            yield os.path.join(wurzel, datei)


def vorschlaege(ziel, anzahl=8):
    """Vorhandene Dateien, die wahrscheinlich gemeint sind.

    Reihenfolge: gleicher Name an anderer Stelle, dann aehnliche Namen mit
    derselben Endung (z. B. ..._2025.pdf statt ..._2026.pdf), dann was sonst
    im selben Ordner liegt.
    """
    name = os.path.basename(ziel).lower()
    endung = os.path.splitext(name)[1]
    alle = list(projektdateien())
    gleiche_endung = [d for d in alle if os.path.splitext(d)[1].lower() == endung] or alle

    treffer = [d for d in alle if os.path.basename(d).lower() == name]

    nach_name = {}
    for d in gleiche_endung:
        nach_name.setdefault(os.path.basename(d).lower(), []).append(d)
    for aehnlich in difflib.get_close_matches(name, list(nach_name), n=anzahl * 2, cutoff=0.55):
        treffer += sorted(nach_name[aehnlich])

    ordner = os.path.dirname(ziel)
    if os.path.isdir(ordner):
        treffer += sorted(os.path.join(ordner, d) for d in os.listdir(ordner)
                          if os.path.splitext(d)[1].lower() == endung)

    eindeutig = []
    for d in treffer:
        d = os.path.normpath(d)
        if d not in eindeutig and os.path.isfile(d):
            eindeutig.append(d)
    return eindeutig[:anzahl]


def web_pfad(von_datei, ziel, ab_wurzel=False):
    """Pfad, mit dem die Seite von_datei auf ziel verlinkt."""
    if ab_wurzel:
        return "/" + anzeige(ziel)
    return os.path.relpath(ziel, os.path.dirname(von_datei)).replace(os.sep, "/")


def im_projekt(pfad):
    try:
        return os.path.commonpath([os.path.normpath(pfad), ROOT]) == os.path.normpath(ROOT)
    except ValueError:      # anderes Laufwerk
        return False


def nach_ziel(befunde):
    """Funde zum selben fehlenden Ziel zusammenfassen: {ziel: [befund, ...]}"""
    gruppen = {}
    for befund in befunde:
        gruppen.setdefault(befund["ziel"], []).append(befund)
    return gruppen


# ------------------------------------------------------------------
# Verweise in Seiten ersetzen
# ------------------------------------------------------------------

def _verweis_muster(alt):
    # Nur ganze Pfade: davor und dahinter ein Anfuehrungszeichen, Leerzeichen
    # (srcset), Komma oder eine Klammer (url(...)). So wird aus
    # "bild.jpg" nicht versehentlich ein Teil von "bild.jpg.bak".
    return re.compile(r"(?<=[\"'\s,(])" + re.escape(alt) + r"(?=[\"'\s,)])")


def ersetze_in_datei(datei, ersetzungen):
    """ersetzungen: {alter_pfad: neuer_pfad}. Schreibt die Datei einmal
    (eine Sicherung je Aufruf). Gibt die Zahl der Ersetzungen zurueck."""
    inhalt = h.lies_datei(datei)
    gesamt = 0
    for alt, neu in ersetzungen.items():
        if alt == neu:
            continue
        inhalt, anzahl = _verweis_muster(alt).subn(lambda _m, n=neu: n, inhalt)
        gesamt += anzahl
    if gesamt:
        h.schreibe_datei(datei, inhalt)
    return gesamt


def ziel_umbiegen(stellen, neues_ziel):
    """Alle Verweise der Funde (gleiches fehlendes Ziel) zeigen danach auf
    neues_ziel - fuer jede Seite mit ihrem eigenen relativen Pfad.
    Gibt [(seite, alt, neu, anzahl), ...] zurueck."""
    je_datei = {}
    for befund in stellen:
        neu = web_pfad(befund["datei"], neues_ziel, befund["verweis"].startswith("/"))
        je_datei.setdefault(befund["datei"], {})[befund["verweis"]] = neu

    bericht = []
    for datei, ersetzungen in je_datei.items():
        anzahl = ersetze_in_datei(datei, ersetzungen)
        for alt, neu in ersetzungen.items():
            bericht.append((anzeige(datei), alt, neu, anzahl))
    return bericht


def richtiger_pfad(datei, verweis):
    """Der Verweis mit der Gross-/Kleinschreibung, die auf der Platte steht."""
    if verweis.startswith("/"):
        ordner, vorne, teile = ROOT, "/", verweis.lstrip("/").split("/")
    else:
        ordner, vorne, teile = os.path.dirname(datei), "", verweis.split("/")

    neu = []
    for teil in teile:
        if teil in ("", ".", ".."):
            neu.append(teil)
            ordner = os.path.normpath(os.path.join(ordner, teil)) if teil else ordner
            continue
        try:
            eintraege = os.listdir(ordner)
        except OSError:
            eintraege = []
        if teil not in eintraege:
            teil = next((e for e in eintraege if e.lower() == teil.lower()), teil)
        neu.append(teil)
        ordner = os.path.join(ordner, teil)
    return vorne + "/".join(neu)


def schreibweise_korrigieren(befunde):
    """Korrigiert alle uebergebenen Schreibweise-Funde. Gibt den Bericht zurueck."""
    je_datei = {}
    for befund in befunde:
        je_datei.setdefault(befund["datei"], {})[befund["verweis"]] = \
            richtiger_pfad(befund["datei"], befund["verweis"])
    bericht = []
    for datei, ersetzungen in je_datei.items():
        anzahl = ersetze_in_datei(datei, ersetzungen)
        for alt, neu in ersetzungen.items():
            bericht.append((anzeige(datei), alt, neu, anzahl))
    return bericht


def datei_hinlegen(quelle, ziel):
    """Kopiert quelle genau an den Ort, an dem der Link sie erwartet.
    Ueberschreibt nie etwas."""
    if os.path.exists(ziel):
        raise FileExistsError(f"{anzeige(ziel)} gibt es schon.")
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    shutil.copy2(quelle, ziel)
    return ziel


def ins_projekt_kopieren(quelle, zielordner):
    """Datei von ausserhalb (z. B. Downloads) in einen Projektordner kopieren.
    Gibt den neuen Pfad zurueck; bei gleichem Namen wird durchnummeriert."""
    os.makedirs(zielordner, exist_ok=True)
    stamm, endung = os.path.splitext(os.path.basename(quelle))
    ziel = os.path.join(zielordner, stamm + endung)
    nummer = 2
    while os.path.exists(ziel):
        ziel = os.path.join(zielordner, f"{stamm}-{nummer}{endung}")
        nummer += 1
    shutil.copy2(quelle, ziel)
    return ziel


# ------------------------------------------------------------------
# Angekuendigte PDFs (data/timer.txt, data/timer_trial.txt)
# ------------------------------------------------------------------

def timer_pdf_aendern(timer_datei, alt, neu):
    """Spalte 8 (PDF) jeder Zeile, die alt ankuendigt, auf neu setzen.
    neu = "" traegt die Ankuendigung aus (der Knopf bleibt dann weg)."""
    zeilen = h.lies_datei(timer_datei).splitlines(keepends=True)
    anzahl = 0
    for i, zeile in enumerate(zeilen):
        kern = zeile.rstrip("\r\n")
        if kern.lstrip().startswith("#"):
            continue
        teile = kern.split(";")
        if len(teile) >= 8 and teile[7].strip() == alt:
            teile[7] = neu
            zeilen[i] = ";".join(teile) + zeile[len(kern):]
            anzahl += 1
    if anzahl:
        h.schreibe_datei(timer_datei, "".join(zeilen))
    return anzahl


def timer_pfad(ziel):
    """Pfade in timer.txt gelten ab dem Hauptordner (ohne ../)."""
    return anzeige(ziel)


# ------------------------------------------------------------------
# Externe Adressen
# ------------------------------------------------------------------

def adresse_ersetzen(dateien, alt, neu):
    gesamt = 0
    for datei in dateien:
        inhalt = h.lies_datei(datei)
        neu_inhalt = inhalt.replace(f'href="{alt}"', f'href="{neu}"')
        if neu_inhalt != inhalt:
            gesamt += inhalt.count(f'href="{alt}"')
            h.schreibe_datei(datei, neu_inhalt)
    return gesamt


# ------------------------------------------------------------------
# Texte: alt, Beschreibung, Schreibweisen
# ------------------------------------------------------------------

def attribut(text):
    """Text sicher fuer ein HTML-Attribut (Anfuehrungszeichen, & usw.)."""
    return html_modul.escape(text or "", quote=True)


def alt_eintragen(datei, tag, alttext):
    """Setzt alt="..." in genau das <img>-Tag, das die Pruefung gefunden hat.
    Leerer Text = reines Schmuckbild (alt="" ist dafuer richtig)."""
    inhalt = h.lies_datei(datei)
    if tag not in inhalt:
        raise ValueError("Das Bild steht nicht mehr so in der Seite - bitte neu prüfen.")
    neu = tag[:4] + f' alt="{attribut(alttext)}"' + tag[4:]
    h.schreibe_datei(datei, inhalt.replace(tag, neu, 1))


def beschreibung_lesen(datei):
    treffer = p.BESCHREIBUNG_MUSTER.search(h.lies_datei(datei))
    return html_modul.unescape(treffer.group(1)) if treffer else ""


def beschreibung_setzen(datei, text):
    """meta description setzen. og:description zieht mit, wenn sie bisher
    denselben Text hatte. Fehlt die Zeile, kommt sie unter den viewport."""
    inhalt = h.lies_datei(datei)
    wert = attribut(text)
    treffer = p.BESCHREIBUNG_MUSTER.search(inhalt)
    if treffer:
        alt = treffer.group(1)
        inhalt = inhalt[:treffer.start(1)] + wert + inhalt[treffer.end(1):]
        og = re.search(r'(<meta\s+property="og:description"\s+content=")([^"]*)(")',
                       inhalt, re.IGNORECASE)
        if og and og.group(2) == alt:
            inhalt = inhalt[:og.start(2)] + wert + inhalt[og.end(2):]
    else:
        zeilenende = "\r\n" if "\r\n" in inhalt else "\n"
        viewport = re.search(r'([ \t]*)<meta\s+name="viewport"[^>]*>\r?\n', inhalt, re.IGNORECASE)
        if viewport:
            neu = f'{viewport.group(1)}<meta name="description" content="{wert}">{zeilenende}'
            inhalt = inhalt[:viewport.end()] + neu + inhalt[viewport.end():]
        else:
            stelle = inhalt.lower().find("</head>")
            if stelle == -1:
                raise ValueError("Kein <head> gefunden.")
            inhalt = (inhalt[:stelle] + f'    <meta name="description" content="{wert}">'
                      f"{zeilenende}" + inhalt[stelle:])
    h.schreibe_datei(datei, inhalt)


# Was NICHT angefasst wird: Tags (samt Attributen/Adressen), Kommentare,
# Skripte und Stile. Ersetzt wird nur sichtbarer Text.
_NICHT_TEXT = re.compile(r"(<(?:script|style)\b.*?</(?:script|style)>|<!--.*?-->|<[^>]+>)",
                         re.DOTALL | re.IGNORECASE)


def schreibweise_vereinheitlichen(datei, muster, gewuenscht):
    teile = _NICHT_TEXT.split(h.lies_datei(datei))
    anzahl = 0
    for i in range(0, len(teile), 2):
        teile[i], n = re.subn(muster, gewuenscht, teile[i])
        anzahl += n
    if anzahl:
        h.schreibe_datei(datei, "".join(teile))
    return anzahl


# ------------------------------------------------------------------
# Suchindex (js/suche.js)
# ------------------------------------------------------------------

def _js_text(wert):
    return (wert or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").strip()


def suche_url(datei):
    """Adresse, unter der suche.js (liegt in pages/) die Seite fuehrt."""
    if os.path.dirname(os.path.normpath(datei)) == os.path.normpath(os.path.join(ROOT, "pages")):
        return os.path.basename(datei)
    return "../" + anzeige(datei)


def suche_vorgaben(datei):
    """Titel und Beschreibung als Vorschlag aus der Seite selbst."""
    inhalt = h.lies_datei(datei)
    titel = p.TITEL_MUSTER.search(inhalt)
    titel = html_modul.unescape(titel.group(1)).split(" - ")[0].strip() if titel else ""
    return {"titel": titel, "beschreibung": beschreibung_lesen(datei)}


def suche_eintrag_anlegen(datei, titel, beschreibung, stichwoerter):
    js = h.lies_datei(p.SUCHE_JS)
    zeilenende = "\r\n" if "\r\n" in js else "\n"
    start = js.find("const websiteSeiten = [")
    schluss = js.find("];", start)
    if start == -1 or schluss == -1:
        raise ValueError("Liste websiteSeiten in js/suche.js nicht gefunden.")

    zeile = (f"    {{ url: '{_js_text(suche_url(datei))}', titel: '{_js_text(titel)}', "
             f"beschreibung: '{_js_text(beschreibung)}', "
             f"keywords: '{_js_text(stichwoerter).lower()}' }},{zeilenende}")

    # Vor den ersten Verweis nach draussen (Shop) - die eigenen Seiten
    # stehen so weiter zusammen.
    extern = js.find("{ url: 'http", start, schluss)
    if extern != -1:
        stelle = js.rfind("\n", start, extern) + 1
    else:
        stelle = js.rfind("\n", start, schluss) + 1
        vorher = js[start:stelle].rstrip()
        if vorher.endswith("}"):
            js = js[:start] + vorher + "," + js[start + len(vorher):]
            stelle += 1
    h.schreibe_datei(p.SUCHE_JS, js[:stelle] + zeile + js[stelle:])


def suche_eintrag_entfernen(url):
    zeilen = h.lies_datei(p.SUCHE_JS).splitlines(keepends=True)
    behalten = [z for z in zeilen
                if f"url: '{url}'" not in z and not z.strip().startswith(f"'{url}':")]
    if len(behalten) == len(zeilen):
        return 0
    h.schreibe_datei(p.SUCHE_JS, "".join(behalten))
    return len(zeilen) - len(behalten)


# ------------------------------------------------------------------
# Build und Editor
# ------------------------------------------------------------------

def bauen():
    """tools/build_assets.py ausfuehren. Gibt (ok, ausgabe) zurueck."""
    try:
        ergebnis = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "build_assets.py")],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180, creationflags=OHNE_FENSTER)
    except (OSError, subprocess.SubprocessError) as fehler:
        return False, str(fehler)
    return ergebnis.returncode == 0, (ergebnis.stdout or "") + (ergebnis.stderr or "")


def zeile_von(datei, suche):
    if not suche:
        return 1
    try:
        inhalt = open(datei, encoding="utf-8", errors="replace").read()
    except OSError:
        return 1
    stelle = inhalt.find(suche)
    return inhalt.count("\n", 0, stelle) + 1 if stelle >= 0 else 1


def stelle_oeffnen(datei, suche=None):
    """Datei im Editor oeffnen, moeglichst gleich an der Fundstelle.
    VS Code springt in die Zeile, Notepad++ auch, Notepad nur in die Datei."""
    zeile = zeile_von(datei, suche)
    code = shutil.which("code")
    if code:
        subprocess.Popen(["cmd", "/c", code, "-g", f"{datei}:{zeile}"] if os.name == "nt"
                         else [code, "-g", f"{datei}:{zeile}"], creationflags=OHNE_FENSTER)
        return
    for kandidat in (r"C:\Program Files\Notepad++\notepad++.exe",
                     r"C:\Program Files (x86)\Notepad++\notepad++.exe"):
        if os.path.isfile(kandidat):
            subprocess.Popen([kandidat, f"-n{zeile}", datei])
            return
    subprocess.Popen(["notepad.exe", datei])


# ------------------------------------------------------------------
# Terminal: python tools/pruefe_seite.py -> "jetzt beheben?"
# ------------------------------------------------------------------

def terminal_reparatur():
    tote, schreibweise = p.befunde_verweise()

    if schreibweise:
        print(f"\n{len(schreibweise)} Pfad(e) mit falscher Gross-/Kleinschreibung:")
        for befund in schreibweise:
            print(f"  {befund['anzeige']}: {befund['verweis']} -> "
                  f"{richtiger_pfad(befund['datei'], befund['verweis'])}")
        if h.frage_ja("Alle korrigieren? (j/n): "):
            for seite, alt, neu, _ in schreibweise_korrigieren(schreibweise):
                print(f"  korrigiert in {seite}: {neu}")

    for ziel, stellen in nach_ziel(tote).items():
        seiten = sorted({b["anzeige"] for b in stellen})
        print(f"\nFehlt: {anzeige(ziel)}")
        print(f"  verlinkt in: {', '.join(seiten)}")
        kandidaten = vorschlaege(ziel)
        optionen = [f"Link umbiegen auf {anzeige(k)}" for k in kandidaten]
        optionen += ["Anderen Pfad eingeben (ab Hauptordner, z. B. media/dokumente/x.pdf)",
                     "Datei von woanders genau hierher kopieren",
                     "Ueberspringen"]
        try:
            wahl = h.waehle_option("Was tun?", optionen)
        except h.Zurueck:
            continue
        if wahl == len(optionen) - 1:
            continue
        try:
            if wahl < len(kandidaten):
                neues_ziel = kandidaten[wahl]
            elif wahl == len(kandidaten):
                eingabe = h.frage("Neuer Pfad: ").strip().replace("\\", "/").lstrip("/")
                while eingabe.startswith("../"):
                    eingabe = eingabe[3:]
                neues_ziel = os.path.normpath(os.path.join(ROOT, eingabe))
                if not os.path.isfile(neues_ziel) and \
                        not h.frage_ja("Die Datei gibt es nicht - trotzdem eintragen? (j/n): "):
                    continue
            else:
                quelle = h.frage("Pfad der Datei (z. B. aus Downloads): ").strip().strip('"')
                if not os.path.isfile(quelle):
                    print("  Datei nicht gefunden - uebersprungen.")
                    continue
                datei_hinlegen(quelle, ziel)
                print(f"  Abgelegt: {anzeige(ziel)}")
                continue
            for seite, alt, neu, _ in ziel_umbiegen(stellen, neues_ziel):
                print(f"  {seite}: {alt} -> {neu}")
        except h.Zurueck:
            continue
        except (OSError, ValueError) as fehler:
            print(f"  Nicht geklappt: {fehler}")

    if p.pruefe_build_aktuell() and h.frage_ja("\nBuild-Schritt jetzt ausfuehren? (j/n): "):
        ok, ausgabe = bauen()
        print(ausgabe.strip() or ("Fertig." if ok else "Fehlgeschlagen."))

    print("\nZum Kontrollieren noch einmal pruefen: python tools/pruefe_seite.py")
