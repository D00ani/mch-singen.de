=======================================================
HINWEISE ZUR WARTUNG UND PFLEGE DER MCH SINGEN WEBSEITE
=======================================================

Dieses Dokument ist ein Leitfaden zur Pflege der Webseite. Es erklärt dir, wie du
Rennen aktualisierst, PDFs verknüpfst, Downloads steuerst und Statistiken eintragen kannst.

Bitte bearbeite die Dateien (wie HTML oder TXT) immer mit einem einfachen
Texteditor (z. B. Notepad, Notepad++, VS Code).

-------------------------------------------------------
1. DIE ORDNER-STRUKTUR (Wo finde ich was?)
-------------------------------------------------------

/ (Hauptverzeichnis)
  index.html              -> Startseite
  404.html                -> Fehlerseite
  robots.txt, sitemap.xml -> SEO-Dateien

/pages/                   -> Alle Unterseiten (statistiken.html, aktuelles.html etc.)
/css/                     -> Design-Dateien (Farben, Layouts, Abstände)
/js/                      -> Eigene Steuerungs-Skripte (Timer, Kalender-Downloads etc.)
/js/vendor/               -> Eingebundene Bibliotheken (chart.js, klaro.js) - NICHT bearbeiten!
/webfonts/                -> Schriftarten

/tools/                   -> Alle Pflege- und Hilfsskripte (siehe Abschnitt 10!)

/data/                    -> Textdateien und JSON für Timer, Countdown und Live-Daten
  timer.txt               -> Kart-Renntermine und Countdown
  timer_trial.txt         -> Trial-Termine und Countdown
  trainingstermine2026.txt -> Trainingstermine fürs Kalender-Download (jährlich aktualisieren)
  trainingstermine2026_excel-export.txt -> unveränderter Excel-Export als Beleg
  statistik.json          -> Zahlen der Diagramme auf der Statistik-Seite
  livedata.json           -> Live-Timing-Daten (wird von live.html genutzt)

/media/                   -> Alle Medien-Dateien
  /logos/                 -> Vereinslogo (favicon.png) und DMV-Logo (dmv.png)
  /bilder/                -> Fotos, nach Thema sortiert
    /kartsport/           -> Kart-Bilder (kart_abteilung.jpg, mach1-kart.png)
    /trial/               -> Trial-Bilder (trial1.jpg, trial2.jpg, trial_abteilung.jpg)
    /geschichte/          -> Historische Fotos
    /ueber-uns/           -> Team-Fotos
    mch_pic.jpg           -> Allgemeines Vereinsbild
  /videos/                -> Videos (onboard.mp4)
  /sponsoren/             -> Sponsoren-Logos
  /dokumente/             -> Alle PDFs und Dokumente
    /archiv/              -> Jahresauswertungen nach Jahr sortiert (2016 - aktuell)
    /wertungen/           -> Aktuelle Saisonwertungen (BKC etc.)
    /termine/             -> Terminpläne als PDF
    regelwerk.pdf         -> Aktuelles Regelwerk
    anmeldeformular.pdf   -> Anmeldeformular (Mitgliedschaft)
    kurzausschreibung*.pdf -> Kurzausschreibungen für Rennen

-------------------------------------------------------
2. RENN-KALENDER & COUNTDOWN ÄNDERN (timer.txt)
-------------------------------------------------------
Der Countdown auf der Startseite ("Nächstes Rennen...") berechnet sich automatisch.
Datei-Pfad: /data/timer.txt

Aufbau einer Zeile (strikt getrennt durch Semikolon ';'):
Tag;Monat;Jahr;Uhrzeit;Verein;Ort;GoogleMaps-Link;PDF-Link

Beispiel-Zeile:
07;June;2026;09:00;AC;Engen;https://maps.app.goo.gl/aUnnexHkVk5SySza6;/media/dokumente/kurzausschreibungacengen2026.pdf

WICHTIGE REGELN für die timer.txt:
1. Die Monate MÜSSEN zwingend auf ENGLISCH geschrieben werden! (June, July, etc.)
2. Es dürfen KEINE Leerzeichen vor oder nach dem Semikolon (;) stehen.

EINFACHER GEHT'S MIT DEM TOOL statt von Hand zu tippen:
    python tools/termine_verwalten.py
(oder per Doppelklick auf website-pflege.bat eine Ebene über mch-arbeit/ ->
Menüpunkt "Renntermine verwalten", siehe Abschnitt 10)
Fragt Kart/Trial ab, dann Hinzufuegen/Bearbeiten/Loeschen:
  - Hinzufuegen: laesst bekannte Vereine/Orte per Nummer auswaehlen
    (Maps-Link wird automatisch uebernommen), prueft Datum/Uhrzeit auf
    Gueltigkeit, erkennt Duplikate und schlaegt den PDF-Dateinamen
    automatisch vor.
  - Bearbeiten/Loeschen: zeigt alle vorhandenen Termine nummeriert an,
    Termin auswaehlen und Werte anpassen (Enter = behalten) oder loeschen.
Schreibt danach direkt in timer.txt bzw. timer_trial.txt.

-------------------------------------------------------
3. KURZAUSSCHREIBUNG (PDF) VERKNÜPFEN
-------------------------------------------------------
Wird eine PDF verlinkt, erscheint unter dem Timer automatisch ein Download-Button.

Die PDF-Pfade für alle Rennen der laufenden Saison sind bereits in der timer.txt
vorausgeplant. Die Webseite prüft beim Laden automatisch per HEAD-Anfrage, ob die
Datei auf dem Server tatsächlich existiert:
  - Datei NICHT vorhanden -> Button bleibt unsichtbar, kein Fehler
  - Datei vorhanden       -> Button erscheint beim nächsten Seitenaufruf automatisch

DU MUSST NUR NOCH:
  PDF-Datei mit dem richtigen Namen in /media/dokumente/ hochladen - fertig!

BEQUEMER GEHT ES ÜBER DAS WERKZEUG:
    python tools/ausschreibung_pdf.py
  (oder Menüpunkt "Ausschreibungs-PDF einpflegen")
Es zeigt, welche PDFs noch fehlen und zu welchem Rennen sie gehören, und
kopiert die Datei von dort, wo sie gerade liegt (Downloads, Desktop, USB),
an genau die angekündigte Stelle - mit dem richtigen Namen, ohne Abtippen.
Im Explorer die Datei mit Rechtsklick "Als Pfad kopieren" greifen und im
Werkzeug einfügen.

Wichtig beim Dateinamen (GitHub-Server sind streng):
  - Nur Kleinbuchstaben, keine Leerzeichen, keine Umlaute
  - Beispiel: kurzausschreibungmchsingen2026.pdf
  - Den erwarteten Dateinamen für jedes Rennen findest du in /data/timer.txt
    (letztes Feld jeder Zeile, nach dem 7. Semikolon)
  - Steht dort schon ein heikler Name (z. B. mit "ß"), räumt ihn der
    Menüpunkt "Heikle Dateinamen aufräumen" auf und schreibt die timer.txt
    gleich mit um.

-------------------------------------------------------
3b. MEDIEN RICHTIG VERLINKEN (PDFs, Bilder)
-------------------------------------------------------
Vier Stolpersteine - die Werkzeuge korrigieren sie inzwischen automatisch
und sagen dir, was sie geändert haben:

1. IMMER Schrägstriche "/", NIE Backslashes "\"
   Der Windows-Explorer zeigt "\", das Web kennt nur "/".
       \media\dokumente\datei.pdf     -> kaputt
       ../media/dokumente/datei.pdf   -> richtig

2. Der Anfang hängt davon ab, WO die Datei steht, in der der Link steht:
       Seiten in /pages/ (aktuelles.html, archiv.html, ...):  ../media/...
       index.html (Hauptverzeichnis):                         media/...
   Das "../" heißt "einen Ordner nach oben" - von /pages/ aus muss man
   erst hoch, bevor man /media/ findet.

3. AUSNAHME 404.html: dort ALLE Pfade mit führendem "/" (ab der Wurzel)
       /media/logos/favicon.png    /css/bundle.min.css    /pages/suche.html
   Grund: GitHub Pages liefert 404.html bei JEDER unbekannten Adresse aus,
   die Adresszeile im Browser behält aber die aufgerufene Adresse. Bei
   einem toten Link wie /pages/alte-seite.html würde "css/bundle.min.css"
   als /pages/css/bundle.min.css gesucht - dann steht die Fehlerseite ohne
   Design, ohne Menü da und alle ihre Links führen wieder ins Leere.
   Das Verlinken mit "/" geht nur, weil die Seite unter einer eigenen
   Domain (CNAME: mch-singen.de) direkt auf der Wurzel liegt.

   ZUM PRÜFEN: einfach eine erfundene Adresse TIEF in der Seite aufrufen,
   z. B. mch-singen.de/pages/gibtsnicht.html - nicht nur mch-singen.de/xyz.
   Nur die tiefe Adresse deckt diesen Fehler auf.

4. AUSNAHME /data/timer.txt und timer_trial.txt: dort OHNE "../" und OHNE "/"
       ...;media/dokumente/kurzausschreibungacengen2026.pdf
   Grund: Der Countdown läuft nur auf index.html, und das Skript setzt den
   Pfad unverändert als Link ein.

WOHIN GEHÖRT WAS:
   Wertungen    -> /media/dokumente/wertungen/
   Terminpläne  -> /media/dokumente/termine/
   Jahresarchiv -> /media/dokumente/archiv/<JAHR>/
   Bilder       -> /media/bilder/<thema>/

Externe Links (auf fremde Webseiten) bekommen zusätzlich
target="_blank" rel="noopener noreferrer" - das setzen die Werkzeuge
ebenfalls von allein.

NEUES RENNEN EINTRAGEN (wenn ein Termin noch nicht in der timer.txt steht):
  Zeile am Ende ergänzen nach dem Schema aus Abschnitt 2.
  Den PDF-Pfad als 8. Feld eintragen. Sobald du die Datei hochlädst, erscheint
  der Button automatisch. Fehlt die PDF noch, bleibt das Feld leer oder du trägst
  den Pfad schon vor - der Button bleibt solange unsichtbar bis die Datei da ist.

-------------------------------------------------------
4. TERMINE FÜR DEN KALENDER-DOWNLOAD (Aktuelles)
-------------------------------------------------------
Auf der Seite "Aktuelles" können Mitglieder Termine in ihren Handy-Kalender speichern.

- RENN-TERMINE:
  Werden völlig automatisch aus der Datei /data/timer.txt (Siehe Punkt 2) generiert.

- TRAININGSTERMINE:
  Werden über eine eigene Textdatei gesteuert.
  Datei-Pfad: /data/trainingstermine2026.txt

  Aufbau der Zeile: Tag;Monat;Jahr;Startzeit-Endzeit;Gruppe
  Beispiel: 15;Mai;2026;10:00-13:30;1
  (Gruppe 3 = Termin gilt für BEIDE Gruppen)

  WICHTIG hierbei: Schreibe die Monate in dieser Datei auf DEUTSCH! (Mai, Juni, Juli etc.).

  DAS MACHT DAS TOOL FÜR DICH - von Hand ist das fehleranfällig:
      python tools/trainingstermine_import.py
  (oder website-pflege.bat -> "Trainingstermine importieren")
  Du legst einfach den Excel-Export als .txt in /data/ ab. Das Tool erkennt
  die Trainingszeiten-Spalten, wandelt die Tab-Tabelle in obiges Format um,
  repariert die Excel-Kodierung (Umlaute!), überspringt Zeilen ohne Gruppe
  (Stammtische, Rennen) und passt den Dateinamen in /js/aktuelles.js an.
  Der unveränderte Export bleibt als *_excel-export.txt liegen.

  ACHTUNG (war bis Juli 2026 ein Fehler): Wird der Excel-Export ungewandelt
  abgelegt, findet die Webseite KEINE Termine und der Kalender-Download
  liefert eine leere Datei - ohne sichtbare Fehlermeldung.

-------------------------------------------------------
5. STATISTIKEN PFLEGEN (Vereinsmeister etc.)
-------------------------------------------------------
Die Bestenlisten und Vereinsmeister sind fest in die Webseite eingebaut.

Um ein neues Jahr einzutragen:
1. Öffne die Datei /pages/statistiken.html
2. Suche nach der gewünschten Tabelle (z. B. Trial oder Kart).
3. Kopiere die oberste HTML-Tabellenzeile (alles von <tr> bis zum dazugehörigen </tr>).
4. Füge diese kopierte Zeile direkt darunter (oder darüber) als neue Zeile ein.
5. Ändere das Jahr und den Namen zwischen den <td>...</td> Klammern.
   Beispiel: <td>2026</td> <td>Max Mustermann</td>

HINWEIS ZUM DATENSCHUTZ: Du kannst in der HTML-Datei den vollen Namen eintragen.
Ein Skript auf der Webseite sorgt automatisch dafür, dass der Nachname der Fahrer
auf der fertigen Webseite nur mit einem Buchstaben abgekürzt wird (z. B. "Max M.").

EINFACHER GEHT'S MIT DEM TOOL statt HTML-Zeilen von Hand zu kopieren:
    python tools/statistiken_pflege.py
(oder per Doppelklick auf website-pflege.bat -> Menüpunkt "Statistiken-Seite
pflegen", siehe Abschnitt 10)
Deckt ALLE Bereiche der Statistik-Seite ab, jeweils mit nummerierter Auswahl
zum Hinzufügen/Bearbeiten/Löschen, ohne HTML anzufassen:
  - Tabelle "Unsere Top-Platzierungen" (inkl. Fett-Hervorhebung der Platzierung)
  - Wanderpokal-Sieger Jugend und Erwachsen
  - Die "Vereinsbestleistungen"-Boxen
  - Die Meilenstein-Zahlen oben (Gegründet, Aktive Fahrer, Pokale, Mitglieder)
  - Die Diagramm-Werte und deren Überschriften

ZU DEN DIAGRAMMEN: Die Zahlen stehen seit Juli 2026 in /data/statistik.json
und NICHT mehr in js/statistiken.js. Dadurch ist nach einer Änderung KEIN
Build-Schritt mehr nötig. Das Diagramm "Dieses Jahr (Bisher)" wird weiterhin
automatisch aus der Wertungs-PDF berechnet (Abschnitt 5b) und lässt sich
deshalb nicht von Hand ändern.

-------------------------------------------------------
5b. CHART "DIESES JAHR (BISHER)" AUTOMATISCH AKTUALISIEREN
-------------------------------------------------------
Der Balken-Chart "Dieses Jahr (Bisher)" auf der Statistik-Seite (1./2./3.-Plätze
von MCH Singen) muss NICHT mehr von Hand aus der PDF abgezählt werden.

SO GEHT'S:
1. Neue/aktualisierte Wertungs-PDF wie gewohnt hochladen nach:
   /media/dokumente/wertungen/bkcgesamtwertung_<JAHR>.pdf
2. Einmal ausführen:
       python tools/update_statistik.py
   Das Skript sucht in der PDF die Vereinswertungs-Tabelle, findet automatisch
   die Zeile von "MCH Singen" (unabhängig davon, auf welchem Rang/in welcher
   Zeile der Verein gerade steht) und schreibt die Zahlen nach
   /data/statistik.json.
3. Fertig - die Webseite liest diese Datei beim Aufruf der Statistik-Seite
   automatisch ein. KEIN Build-Schritt nötig (nur eine JSON-Datei, kein JS/CSS).

Einmalige Vorbereitung auf einem neuen PC: pip install pdfplumber

Betrifft NUR den Chart "Dieses Jahr (Bisher)". Die Charts "Gesamt (seit 2016)"
und "Saison 2025" sind feste Werte in js/statistiken.js und müssten dort von
Hand geändert werden (siehe Abschnitt 9 für den nötigen Build-Schritt danach).

-------------------------------------------------------
6. JAHRESARCHIV ERWEITERN
-------------------------------------------------------
Am Ende einer Saison die Gesamtauswertung ins Archiv aufnehmen:

Schritt 1: PDF hochladen
Neuen Ordner unter /media/dokumente/archiv/JAHR/ anlegen und PDF dort hinein.
Beispiel: /media/dokumente/archiv/2026/BKC_Gesamtauswertung_2026.pdf

Schritt 2: In archiv.html verlinken
Öffne /pages/archiv.html und ergänze oben in der Liste einen neuen Eintrag nach dem
Muster der bestehenden Einträge.

EINFACHER GEHT'S MIT DEM TOOL statt HTML von Hand zu ergaenzen:
    python tools/archiv_pflege.py
(oder per Doppelklick auf website-pflege.bat -> Menüpunkt "Jahresarchiv
pflegen", siehe Abschnitt 10)
Legt bei einer neuen Saison automatisch den Ordner media/dokumente/archiv/JAHR/
an, erkennt eine bereits hochgeladene bkcgesamtwertung_JAHR.pdf aus
media/dokumente/wertungen/ und bietet an, sie direkt als Archiv-PDF zu
kopieren. Danach koennen weitere Eintraege pro Saison hinzugefuegt,
bearbeitet oder geloescht werden.

-------------------------------------------------------
7. TEXTE UND BILDER AUSTAUSCHEN
-------------------------------------------------------
TEXTE: Öffne die .html Datei, suche die Textpassage und ändere den Text ZWISCHEN
den spitzen HTML-Klammern (z.B. <p>Dein Text</p>).

BILDER: Lade das neue Bild in den passenden Unterordner unter /media/bilder/ hoch.
Suche in der .html Datei nach dem <img src="..."> Code und ersetze den Pfad.
HINWEIS: Die meisten Bilder werden zusätzlich als schnelles WebP-Format
ausgeliefert (<picture>-Blöcke im HTML).

  NEUES Bild aufnehmen -> das Tool nimmt dir die Arbeit ab:
      python tools/bilder_pflege.py
  (oder website-pflege.bat -> "Bilder aufnehmen")
  Es zeigt alle Bilder ohne WebP-Fassung, fragt nach dem Verwendungszweck
  (Kopfbereich/Textbereich/Vorschaubild/Logo), erzeugt die passenden Größen
  und gibt den fertigen <picture>-Block zum Einfügen aus.

  BESTEHENDES Bild ERSETZT (gleicher Dateiname) -> wie bisher:
      python tools/optimize_images.py
  Das erzeugt die vorhandenen .webp-Fassungen neu (siehe Abschnitt 9).

LOGOS: Das MCH-Logo (favicon.png) und das DMV-Logo (dmv.png) liegen unter /media/logos/.
Im Header/Footer wird die kleine Version mch-logo-128.png verwendet (Ladezeit!).

-------------------------------------------------------
8. WICHTIGE HINWEISE ZU GITHUB PAGES
-------------------------------------------------------
- ACHTUNG GROSS-/KLEINSCHREIBUNG: Die Linux-Server von GitHub sind extrem streng.
  Wenn im Code steht: <img src="media/Foto.jpg">, die Datei aber foto.jpg heißt,
  wird sie auf GitHub nicht angezeigt!
- LADEZEIT: Wenn du etwas hochlädst, dauert es 1-3 Minuten, bis die Änderungen online sind.
- BROWSER-CACHE: Drücke auf der Webseite Strg + F5 (oder Cmd + Shift + R am Mac),
  um das Laden der neuesten Version zu erzwingen!

-------------------------------------------------------
9. PERFORMANCE-BUILD (WICHTIG BEI CSS/JS-ÄNDERUNGEN!)
-------------------------------------------------------
Die Webseite lädt aus Geschwindigkeitsgründen NICHT die Original-Dateien,
sondern minifizierte Versionen:
  - css/bundle.min.css  = alle css/*.css Basis-Dateien zusammengefasst
  - css/index.min.css, kartsport.min.css, live.min.css
  - js/*.min.js         = minifizierte Kopien der js/*.js Dateien

DAS BEDEUTET: Wenn du eine .css- oder .js-Datei änderst, ist die Änderung
ERST online sichtbar, nachdem du einmal dieses Kommando ausgeführt hast:

    python tools/build_assets.py

(Einmalige Vorbereitung auf einem neuen PC: Python installieren, dann
 "pip install csscompressor rjsmin Pillow" ausführen.)

Bei neuen oder ersetzten BILDERN entsprechend:

    python tools/optimize_images.py

HTML-Dateien und /data/-Dateien kannst du wie gewohnt direkt ändern,
dafür ist KEIN Build nötig.

-------------------------------------------------------
10. WEBSEITEN-PFLEGE - EIN WERKZEUG FÜR ALLES (website-pflege.bat)
-------------------------------------------------------
ES GIBT ZWEI STARTPUNKTE, BEIDE MACHEN DASSELBE:

  website-pflege.bat   -> Menü im Terminal (dieser Abschnitt)
  webseiten-fenster.bat -> Fenster mit Maus (Abschnitt 12)

Das Fenster deckt bisher die Übersicht und das Veröffentlichen ab; alle
übrigen Werkzeuge öffnet es in einem eigenen Terminalfenster. Es sind
dieselben Dateien unter /tools/ - nichts ist doppelt vorhanden, und was
im einen geändert wird, gilt sofort auch im anderen.

Eine Ebene über /mch-arbeit/ und /mch-singen.de-main/ liegt
website-pflege.bat - der EINE Startpunkt für die gesamte Wartung.
Einfach per Doppelklick starten.

BEIM START STEHT, WAS ANSTEHT: Noch vor dem Menü kommt eine kurze
Lagemeldung - nächstes Rennen, fehlende Ausschreibungen, veraltetes
Copyright-Jahr, vergessener Build, noch nicht Veröffentlichtes. So muss man
nicht selbst daran denken, was fällig ist. Der Punkt "Was steht an?" im
Menü zeigt dieselbe Übersicht noch einmal.

Dann im Menü wählen:

 0) Live-Timing: Zeiten der Zeitmessung auf die Seite bringen -> Abschnitt 11
 0b) Nach dem Rennen (Assistent)
    Geht die vier Schritte durch, die nach jedem Rennen anfallen:
    Ergebnisse in die Statistik, News-Karte, Bilder, Archiv-Eintrag.
    Man wählt oben das Rennen aus (aus den Terminen der letzten Wochen),
    danach steht es bei jedem Schritt im Kopf des Fensters. Jeder Schritt
    lässt sich mit "n" überspringen - es sind dieselben Werkzeuge wie im
    Hauptmenü, nur ohne die Gefahr, einen davon zu vergessen.
 1) Renntermine (Kart/Trial) verwalten          -> Abschnitt 2
 1b) Ausschreibungs-PDF einpflegen              -> Abschnitt 3
    Beim Eintragen eines Termins wird der PDF-Pfad schon angekündigt, die
    Datei kommt aber oft erst Wochen später. Dieses Werkzeug zeigt, welche
    PDFs noch fehlen, und kopiert die Datei an genau die angekündigte
    Stelle - man muss den Pfad also nicht abtippen. Enthält der
    angekündigte Name Umlaute oder Großbuchstaben, wird ein sauberer Name
    vorgeschlagen und der Termin-Eintrag gleich mit umgeschrieben.
 2) Trainingstermine importieren (Excel-Export) -> Abschnitt 4
 3) Statistiken-Seite pflegen                   -> Abschnitt 5
    (Top-Platzierungen, Vereinsmeister, Rekorde, Meilensteine, Diagramme)
 4) News-Karten auf "Aktuelles" pflegen
    Neue Meldung anlegen (Datum, Titel, Text, Kennzeichen, Link),
    bestehende ändern oder löschen - ohne HTML-Blöcke zu kopieren.
 5) Jahresarchiv pflegen                        -> Abschnitt 6
 5b) Sponsoren-Seite pflegen
    Deckt die KOMPLETTE Seite sponsoren-links.html ab, kein HTML nötig:
      - Sponsoren (Logos): hinzufügen, bearbeiten, entfernen
      - Befreundete Vereine: Einträge samt Sinnbild verwalten
      - Nützliche Links: dito
      - Zahlen oben (Gegründet, Mitglieder, Events, Sportarten)
      - Aufruf "Werde Sponsor": Einleitung, die drei Vorteils-Kästen,
        Beschriftung der Schaltfläche

    NEUEN SPONSOR ANLEGEN: Logo-Datei nach /media/sponsoren/ legen (Dateiname
    klein, ohne Umlaute und Leerzeichen), dann im Werkzeug auswählen. Es
    erzeugt die WebP-Fassung, berechnet die Anzeigegröße und legt die
    Banden-Karte an der gewünschten Stelle an.

    ZUR ANZEIGEGRÖSSE: Die Logos haben sehr unterschiedliche Seitenverhältnisse.
    Würde man alle gleich hoch anzeigen, wirkten hochkante Logos halb so groß
    wie querformatige. Das Werkzeug rechnet deshalb für jedes Logo eine eigene
    Größe aus, sodass alle dieselbe FLÄCHE einnehmen - deswegen stehen in
    sponsoren-links.html bei jedem Logo andere width/height-Werte.
    Nach einem Logo-Tausch "Alle Logo-Größen neu berechnen" aufrufen.

    "Logos in WebP umwandeln" wandelt noch vorhandene JPG/PNG-Logos um und
    bindet sie direkt ein (spart deutlich Ladezeit - bei den sieben Logos
    waren es 532 KB vorher, 116 KB nachher). Die alten Dateien können dabei
    gelöscht werden.
 5c) Vorstand & Trainer pflegen
    Personen auf "Über uns" hinzufügen, bearbeiten oder entfernen.
    Beim Bearbeiten werden gezielt einzelne Felder ersetzt - Besonderheiten
    einzelner Karten (Instagram-Verlinkung, Spruch statt E-Mail, besonderer
    Bildausschnitt) bleiben dabei erhalten. Wird ein Name geändert, zieht das
    Werkzeug ihn an allen drei Stellen mit (Bildbeschriftung, Überschrift,
    Bildbeschreibung).
    Für ein neues Foto: Datei nach /media/bilder/ueber-uns/ legen.

 5d) Fragen & Antworten (FAQ) pflegen
    Frage und Antwort eingeben - fertig, kein HTML nötig. Für Hervorhebungen
    und Links gibt es eine einfache Schreibweise:
        **wichtig**                   -> wichtig (fett)
        [Kartsport](kartsport.html)   -> Link auf die Kartsport-Seite
    Beim Bearbeiten wird bestehendes HTML in dieselbe Schreibweise
    zurückverwandelt, es geht also nichts verloren. Verweist ein Link auf
    eine Seite, die es nicht gibt, warnt das Werkzeug sofort.

 6) Bilder aufnehmen (WebP + HTML-Block)        -> Abschnitt 7
 6b) Vorschau im Browser
    Startet einen kleinen Webserver auf diesem Rechner und öffnet die Seite
    im Browser - so, wie sie später online aussieht. Es wird nichts
    veröffentlicht, das sieht nur dieser Rechner.
    WARUM NICHT EINFACH index.html DOPPELKLICKEN: Der Browser lädt die
    Datei dann über file:// und blockt genau die Sachen, die die Seite
    braucht - Countdown, Suche und Live-Timing holen ihre Daten per fetch
    und bleiben leer. Unbekannte Adressen zeigen hier dieselbe 404-Seite
    wie bei GitHub Pages.
    Bei Änderungen an CSS/JS vorher den Build laufen lassen (Abschnitt 9),
    sonst zeigt die Vorschau noch den alten Stand.
 7) Webseite prüfen
    Findet tote Links, falsche Groß-/Kleinschreibung (die auf dem
    GitHub-Server Bilder verschwinden lässt!), vergessene Build-Schritte
    und noch nicht hochgeladene Kurzausschreibungen.
    Dazu kommen Prüfungen, die erst später auffallen würden:
      - Bilder ohne alt-Text (Screenreader und Google sehen dort nichts)
      - fehlende oder doppelte Seitenbeschreibung, fehlendes Vorschaubild
        beim Teilen (og:image), fehlender canonical-Link
      - dieselbe id zweimal auf einer Seite (JavaScript findet dann nur
        das erste Element - der Rest tut still nichts mehr)
      - externe Dienste ohne Eintrag in js/klaro-config.js: alles, was von
        einem fremden Server nachgeladen wird, braucht eine Einwilligung
        (DSGVO). Solange die Seite alles selbst ausliefert, meldet die
        Prüfung nichts - sie schlägt an dem Tag an, an dem jemand z. B.
        ein YouTube-Video oder eine Google-Schriftart einbaut.
    AUF NACHFRAGE AUCH DIE LINKS INS INTERNET: Beim direkten Aufruf wird
    gefragt, ob auch die externen Links geprüft werden sollen (dauert ein
    paar Sekunden, braucht Internet). Sponsoren- und Vereinsseiten ziehen
    um oder verschwinden, ohne dass es jemand merkt. Beim automatischen
    Prüfen vor dem Veröffentlichen bleibt das aus, damit es schnell geht.
 7b) Medien aufräumen
    Zeigt für /media/, was niemand mehr braucht und was zu groß ist:
      - von keiner Seite mehr verlinkt (kann weg)
      - nicht mehr auf der Seite, aber noch in einem Werkzeug eingetragen
        (z. B. in optimize_images.py - erst dort austragen)
      - unnötig groß (Bilder über 300 KB, PDFs über 2 MB, Videos über 5 MB)
      - Bilder ohne WebP-Fassung
    Gelöschte Dateien werden vorher gesichert und lassen sich über "Letzte
    Änderung rückgängig machen" zurückholen.
    Für zu große Videos werden die fertigen ffmpeg-Befehle ausgegeben.
    Ein Video mit autoplay lädt JEDER Besucher komplett, auch am Handy -
    hier lohnt sich die Mühe am meisten. Reihenfolge: Tonspur raus (bei
    "muted" hört sie ohnehin niemand), neu kodieren, und zusätzlich ein
    modernes Format anbieten (AV1 spart gegenüber H.264 etwa die Hälfte).
 8) Saisonwechsel-Assistent
    Führt beim Jahreswechsel Schritt für Schritt durch alles: Archiv,
    Diagramm einfrieren, Vereinsmeister, Trainings- und Renntermine,
    technisches Update. Jeder Schritt lässt sich überspringen.
 9) Technisches Update (Statistik/Bilder/Copyright/Build + Push)
    Führt aus: update_statistik.py, optimize_images.py,
    update_copyright_year.py (setzt "© <Jahr>" im Footer aller Seiten)
    und build_assets.py.
10) Letzte Änderung rückgängig machen
    Vor jeder Änderung legt das Werkzeug automatisch eine Sicherung an
    (Ordner .pflege-sicherungen/, bleibt lokal). Damit lässt sich ein
    Vertipper zurückholen - auch nachdem er schon gepusht wurde.

MIT "x" IMMER EINEN SCHRITT ZURÜCK: An JEDER Eingabestelle bringt dich
ein "x" einen Schritt zurück - im Menü eine Ebene höher, in einem Formular
zu der Frage davor (die falsche Eingabe wird verworfen und neu gestellt).
"x" in der ersten Frage bricht die Aktion ab, ohne etwas zu speichern.
Man kann sich also nie "verrennen" und muss ein Formular nicht mehr zu
Ende ausfüllen, nur weil man sich vertippt hat.
(Nebenwirkung: Ein einzelnes "x" lässt sich dadurch nicht als Wert
eingeben - bei einem Namen o. ä. einfach "X." schreiben.)

NEUE EINTRÄGE WERDEN AUTOMATISCH EINSORTIERT - sie landen nicht mehr
einfach oben, sondern an der Stelle, wo sie hingehören. Das Werkzeug sagt
dir vorher, wo der Eintrag landet ("Wird an Position 5 von 9 einsortiert"):
  - Wanderpokal-Sieger und Top-Platzierungen: neuestes Jahr zuerst
    (trägst du 2021 nach, rutscht es unter 2022)
  - Jahresarchiv: neueste Saison oben
  - Renntermine: chronologisch nach Datum und Uhrzeit
  - News-Karten: hier steht im Datum Freitext ("Saison 2026"), das lässt
    sich nicht zuverlässig sortieren - deshalb fragt das Werkzeug, an
    welcher Stelle des Abschnitts die Karte stehen soll.

VERÖFFENTLICHEN BEIM BEENDEN: Beim Beenden mit "0" prüft das Werkzeug die
Seite, aktualisiert die Datumsangaben in sitemap.xml und veröffentlicht
dann alles Geänderte (Commit in arbeit -> Merge nach main -> Push).
Werden beim Prüfen Fehler gefunden, wird vorher gefragt, ob trotzdem
veröffentlicht werden soll.

VORHER STEHT IN KLARTEXT DA, WAS RAUSGEHT - nicht die Dateinamen, sondern
was sich für Besucher ändert:
    Aktuelles: 2 News-Karten neu (jetzt 7)
    Renntermine Kart: 1 Termin neu (05.July.2026 09:00 - MCH Singen)
    Jahresarchiv: 1 Saison neu (jetzt 12)
    Bild neu: rennen1.webp
Danach kommt die Frage, ob veröffentlicht werden soll. Mit "n" bleibt
alles im Arbeitsordner liegen und geht nicht verloren - beim nächsten
Start steht es wieder in der Lagemeldung.

Nach jedem Menüpunkt kommt man wieder zurück ins Hauptmenü - so lassen
sich in einem Durchgang z. B. Renntermine eintragen, die Statistik-Seite
aktualisieren und eine News-Karte anlegen, bevor alles zusammen online geht.

website-pflege.bat liegt bewusst außerhalb beider Git-Ordner (ist also
nicht Teil des Repos) und muss bei einem neuen PC neu angelegt werden;
die Python-Werkzeuge selbst liegen in /tools/ und sind versioniert.

Einmalige Vorbereitung auf einem neuen PC: Python installieren, dann
"pip install pdfplumber csscompressor rjsmin Pillow" ausführen.

-------------------------------------------------------
11. LIVE-TIMING AM RENNTAG (live-timing.bat)
-------------------------------------------------------
Die Live-Seite (pages/live.html) zeigt die Zeiten, die das Programm
"Zeitmessung_Kart" misst. Dazwischen sitzt das Werkzeug
tools/livetiming_sync.py. Es LIEST nur - an der Zeitmessung und ihrer
Datenbank wird NICHTS verändert.

SO LÄUFT ES:
  Zeitmessung speichert einen Lauf
    -> in ihre Access-Datenbank Zeitmessung_Kart_Data.accdb
    -> livetiming_sync.py liest sie alle paar Sekunden
    -> schreibt data/livedata.json
    -> committet + merged + pusht die Datei, sobald sich etwas ändert
    -> live.html holt sich die Datei alle 3 Sekunden neu

AM RENNTAG:
  1. Zeitmessung ganz normal starten und Starter erfassen.
  2. live-timing.bat per Doppelklick starten (liegt neben
     website-pflege.bat), dann "1) Live-Timing starten".
  3. Laufen lassen. Beenden mit Strg+C - der letzte Stand wird dabei
     noch veröffentlicht.

BEIM ERSTEN MAL: Menüpunkt "Einstellungen" öffnen, den Pfad zur Datei
Zeitmessung_Kart_Data.accdb eintragen UND den Namen der Veranstaltung
setzen - der steht dann im Kopf der Live-Seite. Das Werkzeug sucht sie sonst
selbst - erst in der App.config der Zeitmessung, dann im Ordner
Zeitmessung_Kart/Zeitmessung_Kart_Data/ neben den Webseiten-Ordnern.
Die Einstellungen landen in tools/livetiming.config.json (bleibt lokal,
weil der Pfad auf jedem Rechner anders ist).

"Status / Selbsttest" zeigt, ob die Datenbank lesbar ist, welche Renntage
darin stehen und wie viele Ergebnisse für den gewählten Tag herauskommen -
gut zum Ausprobieren VOR dem Rennen.

WAS AUF DER SEITE LANDET:
  LaufNr 1 in der Datenbank -> Knopf "1. WL"
  LaufNr 2                  -> Knopf "2. WL"
  LaufNr 0                  -> Knopf "Gesamtergebnis"
  Klasse "1a"               -> "Klasse 1a"
Platzierung und Rückstände (auf Erste(n) und auf Vordermann) rechnet das
Werkzeug selbst aus. Wird ein Lauf wiederholt, zählt automatisch der
neueste Eintrag. Starter ohne gültige Zeit ("ADW") stehen hinten.

TRAININGSLÄUFE GIBT ES HIER NICHT: Die Zeitmessung schreibt nur
Einführungsrunde + 1./2. Wertungslauf pro Starter in die Ergebnistabelle.
Das freie Training landet nur in ihrer History-Liste, ohne Startnummer und
Klasse - daraus lässt sich keine Tabelle bauen. Deshalb gibt es auf der
Live-Seite keinen "TL"-Knopf mehr.

BEISPIELDATEN ZUM VORFÜHREN:
Menüpunkt "Beispieldaten zum Vorführen erzeugen" (oder
python tools/livetiming_beispiel.py) füllt die Live-Seite mit erfundenen
Namen und Zeiten - praktisch, um die Seite außerhalb eines Rennens zu
zeigen. Der Kopf weist sie als "(Beispieldaten)" aus, das Archiv bleibt
unberührt. Am Renntag überschreibt das echte Live-Timing sie automatisch.

WAS DIE SEITE SONST NOCH KANN:
  - Sie startet im GESAMTERGEBNIS - dort steht das ganze Feld auf einen
    Blick. Über die Knöpfe kommst du in die einzelnen Läufe und Klassen.
  - Ist ein Fahrer mit Stern vorgemerkt, springt die Seite beim Öffnen zu
    ihm. Steht er schon im Gesamtergebnis, bleibt sie dort und scrollt nur;
    hat er noch kein Gesamtergebnis, wechselt sie in seinen Lauf.
  - Sie sagt ehrlich, wie alt der Stand ist: "Live · Stand 14:32" bei
    frischen Zeiten, sonst "Letzte Zeit vor 12 Min." bzw. "Keine aktuellen
    Zeiten". Ergebnisse eines vergangenen Renntags gelten nie als live.
  - Auf der STARTSEITE erscheint automatisch ein Knopf "Jetzt live", solange
    die Zeitnahme an DIESEM Tag frische Ergebnisse liefert (höchstens 45
    Minuten alt). Ohne Rennen bleibt die Startseite unverändert.
  - Ein Klick auf eine Fahrerzeile merkt den Fahrer vor (gelb hinterlegt,
    Stern). Praktisch, um das eigene Kind zu verfolgen. Bleibt im Browser
    gespeichert, auch beim Wechsel zwischen Klassen.
  - Neue Zeiten blitzen kurz auf, Positionswechsel bekommen einen Pfeil.
  - Die schnellste Gesamtzeit eines Wertungslaufs bekommt das Abzeichen
    "Bestzeit" (Strafsekunden sind darin enthalten).
  - Klassen und Läufe ohne Starter werden ausgegraut.

VERGANGENE RENNTAGE:
Jeder Renntag wird zusätzlich unter data/ergebnisse/<Datum>.json abgelegt
und bleibt dauerhaft abrufbar - die nächste Veranstaltung überschreibt ihn
nicht mehr. Unter der Tabelle stehen die vergangenen Renntage zum Anklicken.
Direktlink für einen bestimmten Tag (z. B. für die Archiv-Seite):
    pages/live.html?tag=2026-05-04

LIVE-TIMING AUF EINEM ANDEREN LAPTOP:
Das Werkzeug selbst braucht KEINE Zusatzpakete - nur Python 3 und die
Standardbibliothek. Nötig sind:
  1. Windows. Der Zugriff läuft über PowerShell und den Access-Treiber,
     einen Mac oder Linux-Rechner unterstützt das nicht.
  2. Der Access-Treiber (Microsoft Access Database Engine / ACE OLEDB).
     Wenn die Zeitmessung auf dem Laptop läuft, ist er da. ACHTUNG auf die
     Bit-Version: Die Zeitmessung ist ein 32-Bit-Programm, deshalb ist auf
     manchen Rechnern NUR der 32-Bit-Treiber installiert, auf anderen nur
     der 64-Bit-Treiber. Das Werkzeug probiert beides automatisch durch
     (64-Bit-PowerShell, dann 32-Bit-PowerShell) - du musst nichts
     einstellen. Im Menüpunkt "Status / Selbsttest" steht unter "Zugriff",
     welcher Weg funktioniert hat.
  3. Python 3 mit "python" im Suchpfad (die .bat ruft es so auf).
  4. Beide Git-Ordner (mch-arbeit und mch-singen.de-main) sowie ein
     Push-Zugang zu GitHub - sonst wird lokal geschrieben, aber nichts
     veröffentlicht.
  5. Einmalig im Menüpunkt "Einstellungen" den Pfad zur Datenbank setzen.
     Die Einstellungen liegen in tools/livetiming.config.json und werden
     bewusst NICHT mit übertragen, weil der Pfad auf jedem Rechner anders
     ist.

VOR DEM RENNEN EINMAL TESTEN: "Status / Selbsttest" aufrufen. Er sagt, ob
die Datenbank gefunden und gelesen werden kann, über welchen Weg, welche
Renntage darin stehen und wie viele Ergebnisse für heute herauskämen.

INTERNET AN DER STRECKE: Ohne Verbindung schreibt das Werkzeug weiter
brav die Datei und sammelt die Commits - veröffentlicht wird erst, sobald
wieder Netz da ist. Es bricht nicht ab. Ein Handy-Hotspot reicht völlig,
die Datei ist nur wenige Kilobyte groß.

WENN ETWAS KLEMMT:
  - "Datenbank nicht gefunden" -> Pfad in den Einstellungen prüfen.
  - Zeitmessung darf die Datenbank geöffnet haben, das stört nicht.
    Fällt sie kurz aus, läuft das Werkzeug weiter und der zuletzt
    veröffentlichte Stand bleibt stehen.
  - Es wird bewusst NUR data/livedata.json veröffentlicht. Angefangene
    Änderungen an anderen Dateien bleiben liegen und gehen nicht raus.
  - Zwischen zwei Veröffentlichungen liegen mindestens 60 Sekunden
    (einstellbar), damit GitHub nicht bremst. GitHub Pages braucht danach
    wie immer 1-3 Minuten.

-------------------------------------------------------
12. DAS FENSTER (webseiten-fenster.bat)
-------------------------------------------------------
Dieselbe Pflege wie im Terminal, nur mit der Maus. Doppelklick auf
webseiten-fenster.bat - eine Ebene über /mch-arbeit/, direkt neben
website-pflege.bat.

WAS DAS FENSTER SELBST KANN:

  ÜBERSICHT (die Startseite)
    Oben die Boxentafel: nächstes Kart- und Trial-Rennen als Countdown in
    Tagen, dazu wann zuletzt veröffentlicht wurde. Darunter Karten mit
    allem, was Aufmerksamkeit braucht - farbiger Streifen links, rot für
    fällig, orange für Hinweise. Wo ein Werkzeug das Problem löst, sitzt
    daneben ein "Öffnen"-Knopf, der genau dorthin führt.
    "Neu prüfen" liest alles noch einmal ein.

  VERÖFFENTLICHEN
    Unten steht immer, wie viele Änderungen bereitliegen. Der Knopf
    "Veröffentlichen …" öffnet ein Fenster, das ZUERST zeigt, was rausgeht
    (in Klartext, siehe Abschnitt 10), dann die Sitemap aktualisiert und
    die Seite prüft. Erst danach lässt sich der Knopf drücken. Werden
    Fehler gefunden, heißt er "Trotzdem veröffentlichen" - man kann also,
    muss aber nicht.

  WEBSEITE PRÜFEN
    Alle Prüfungen aus Abschnitt 10 als Ergebnisliste: pro Fund eine Karte
    mit Anzahl, darunter die betroffenen Stellen. Der Haken "Internet-Links"
    schaltet die Prüfung der externen Adressen dazu (dauert ein paar
    Sekunden, braucht Verbindung).

  MEDIEN AUFRÄUMEN
    Tabelle mit Datei, Zustand und Größe: verwaist, nur noch im Werkzeug
    eingetragen, zu groß, ohne WebP-Fassung. "Verwaiste löschen" fragt mit
    voller Liste nach und sichert vorher jede Datei. Bei zu großen Videos
    stehen die fertigen ffmpeg-Befehle zum Kopieren darunter.

  AUSSCHREIBUNGS-PDF EINPFLEGEN
    Liste der Termine, die noch auf ihre PDF warten. Zeile anklicken,
    "PDF auswählen ..." - Datei suchen, fertig. Sie wird an die erwartete
    Stelle kopiert und richtig benannt. Heikle Namen (Umlaute, "ß",
    Großbuchstaben) werden beim Einpflegen oder über "Namen aufräumen"
    korrigiert, die timer.txt gleich mit.

  VORSCHAU IM BROWSER
    Startet und beendet den Vorschau-Server und listet jede Unterseite mit
    eigenem Knopf auf.

  LETZTE ÄNDERUNG RÜCKGÄNGIG
    Wie im Terminal, nur mit Nachfrage-Fenster statt j/n.

DIE ÜBRIGEN WERKZEUGE (Renntermine, Statistiken, News, Archiv, Sponsoren,
Vorstand, FAQ, Bilder, Live-Timing, Trainingstermine, Saisonwechsel,
Technisches Update) stehen ebenfalls in der Seitenleiste, öffnen sich aber
noch in einem eigenen Terminalfenster - unverändert, mit denselben Fragen
wie über das Menü.

BEIDES GLEICHZEITIG OFFEN ZU HABEN ist keine gute Idee: beide schreiben in
dieselben Dateien. Nacheinander ist völlig unproblematisch.

TECHNISCHES: Gebaut mit Tkinter, das jedem Python beiliegt - es muss also
nichts nachinstalliert werden. Die Schrift ist Bahnschrift (die DIN-Schrift,
liegt jedem Windows bei), die Farben sind die der Webseite aus css/style.css.
=======================================================
