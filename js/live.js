document.addEventListener("DOMContentLoaded", function() {

    // --- 1. ZUSTAND SPEICHERN ---
    let activeClass = "Klasse 3"; // Start-Klasse
    let activeRun = "1. WL";      // Start-Lauf
    let isGesamt = false;         // Gesamtergebnis-Modus

    let liveData = [];            // Zwischenspeicher für die JSON-Daten
    let lastUpdate = "";          // Uhrzeit des letzten neuen Ergebnisses
    let standIso = "";            // derselbe Zeitpunkt als vollständiger Zeitstempel
    let renntagIso = "";          // Tag, zu dem die Ergebnisse gehören
    let bestzeitSchluessel = "";  // schnellste Gesamtzeit des Renntags

    function heuteIso() {
        const d = new Date();
        return d.getFullYear() + '-' +
               String(d.getMonth() + 1).padStart(2, '0') + '-' +
               String(d.getDate()).padStart(2, '0');
    }

    const gridContainer = document.getElementById('live-grid');
    const headerBar = document.getElementById('live-header-bar');
    const eventDate = document.querySelector('.event-date');
    const eventTitle = document.querySelector('.event-title');
    const liveStatus = document.getElementById('live-status');
    const archivHinweis = document.getElementById('archiv-hinweis');
    const archivListe = document.getElementById('archiv-liste');

    // Archivansicht: ?tag=2026-05-04 zeigt einen vergangenen Renntag.
    // Dann wird nicht mehr nachgeladen - die Daten ändern sich ja nicht mehr.
    const archivTag = (new URLSearchParams(window.location.search).get('tag') || "").trim();
    const istArchiv = /^\d{4}-\d{2}-\d{2}$/.test(archivTag);
    const datenQuelle = istArchiv
        ? `../data/ergebnisse/${archivTag}.json`
        : `../data/livedata.json`;

    // --- 2. KLICK-LOGIK FÜR DIE BUTTONS ---
    const classButtons = document.querySelectorAll('#class-filters .btn-filter');
    const runButtons = document.querySelectorAll('#run-filters .btn-filter');
    const allBtn = document.querySelector('.btn-filter[data-type="all"]');

    // Sobald der Besucher selbst filtert, wird nicht mehr automatisch
    // umgeschaltet (siehe waehleBelegteAnsicht weiter unten).
    let nutzerHatGewaehlt = false;

    classButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            classButtons.forEach(b => b.classList.remove('active'));
            if(allBtn) allBtn.classList.remove('active');
            this.classList.add('active');

            activeClass = this.innerText.trim();
            isGesamt = false;
            nutzerHatGewaehlt = true;
            renderTable();
        });
    });

    runButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            runButtons.forEach(b => b.classList.remove('active'));
            if(allBtn) allBtn.classList.remove('active');
            this.classList.add('active');

            activeRun = this.innerText.trim();
            isGesamt = false;
            nutzerHatGewaehlt = true;
            renderTable();
        });
    });

    if(allBtn) {
        allBtn.addEventListener('click', function() {
            classButtons.forEach(b => b.classList.remove('active'));
            runButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            isGesamt = true;
            nutzerHatGewaehlt = true;
            renderTable();
        });
    }

    // --- 3. HILFSFUNKTIONEN ---

    // Macht aus "01:00,39" eine echte Zahl (60390), mit der der Browser sortieren kann.
    // Alles, was keine Zeit ist (leer oder "ADW" bei Ausschluss), kommt ans Ende.
    const ZEIT_MUSTER = /^(\d{1,3}):([0-5]?\d),(\d{1,2})$/;
    const OHNE_ZEIT = 999999999;
    function parseTimeToMs(timeStr) {
        let treffer = ZEIT_MUSTER.exec((timeStr || "").trim());
        if (!treffer) return OHNE_ZEIT;
        let m = parseInt(treffer[1], 10);
        let s = parseInt(treffer[2], 10);
        let hundertstel = parseInt(treffer[3].padEnd(2, '0'), 10);
        return (m * 60 * 1000) + (s * 1000) + (hundertstel * 10);
    }

    // Aus 60390 wird wieder "01:00,39"
    function msToZeit(ms) {
        const hundertstel = Math.round(Math.abs(ms) / 10);
        const m = Math.floor(hundertstel / 6000);
        const s = Math.floor(hundertstel / 100) % 60;
        const h = hundertstel % 100;
        return String(m).padStart(2, '0') + ':' +
               String(s).padStart(2, '0') + ',' +
               String(h).padStart(2, '0');
    }

    // Strafsekunden kommen als "(12)" aus der Zeitnahme - lesbarer als "+12 s"
    function strafeLesbar(fehler) {
        const zahl = /^\((\d+)\)$/.exec(String(fehler || "").trim());
        return zahl ? `+${zahl[1]} s` : String(fehler || "");
    }

    // Namen und Vereine kommen aus der Zeitmessung und werden dort von Hand
    // getippt - vor dem Einsetzen ins HTML also entschaerfen.
    function escapeHtml(wert) {
        return String(wert === undefined || wert === null ? "" : wert)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    const vereinfacht = t => (t || "").replace(/\s+/g, '').toUpperCase();

    // Erkennt einen Starter wieder - über Läufe und Neuladen hinweg
    const fahrerSchluessel = d => vereinfacht(d.klasse) + '#' + String(d.startnummer);
    const eintragSchluessel = d => fahrerSchluessel(d) + '@' + vereinfacht(d.lauf);

    // Sucht zu einem Starter die Zeit eines einzelnen Wertungslaufs.
    // Im Gesamtergebnis steht nur die Summe beider Läufe - die Einzelzeiten
    // liegen als eigene Einträge (Lauf "1. WL" / "2. WL") in denselben Daten.
    function einzelzeit(driver, lauf) {
        const treffer = liveData.find(d =>
            vereinfacht(d.lauf) === vereinfacht(lauf) &&
            String(d.startnummer) === String(driver.startnummer) &&
            vereinfacht(d.klasse) === vereinfacht(driver.klasse));
        return treffer ? treffer.zeit_total : "";
    }

    // --- 4. GEMERKTE FAHRER (bleiben im Browser gespeichert) ---
    const SPEICHER = 'mch-live-gemerkt';
    let gemerkt = new Set();
    try {
        gemerkt = new Set(JSON.parse(localStorage.getItem(SPEICHER) || "[]"));
    } catch (e) { /* Speicher nicht verfügbar - dann eben ohne */ }

    function merkenUmschalten(schluessel) {
        if (gemerkt.has(schluessel)) gemerkt.delete(schluessel);
        else gemerkt.add(schluessel);
        try {
            localStorage.setItem(SPEICHER, JSON.stringify([...gemerkt]));
        } catch (e) { /* nicht speicherbar, gilt dann nur für diesen Besuch */ }
        renderTable();
    }

    // Ein Klick auf die Zeile merkt den Fahrer vor. Über Delegation, weil die
    // Tabelle bei jeder Aktualisierung neu gezeichnet wird.
    gridContainer.addEventListener('click', function(e) {
        const zeile = e.target.closest('.driver-row');
        if (zeile && zeile.dataset.fahrer) merkenUmschalten(zeile.dataset.fahrer);
    });
    gridContainer.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const zeile = e.target.closest('.driver-row');
        if (zeile && zeile.dataset.fahrer) {
            e.preventDefault();
            merkenUmschalten(zeile.dataset.fahrer);
        }
    });

    // --- 5. ÄNDERUNGEN SEIT DEM LETZTEN NEUEN ERGEBNIS ---
    // Damit lassen sich neue Zeiten hervorheben und Positionswechsel zeigen.
    let letzterStand = null;              // Stand, zu dem die Merker gehören
    let letzteZeiten = {};                // Eintrag -> Gesamtzeit
    let letztePlaetze = {};               // Ansicht -> { Eintrag: Platz }
    let veraenderungen = { neu: {}, richtung: {} };

    function ansichtsSchluessel() {
        return isGesamt ? 'GESAMT' : vereinfacht(activeClass) + '|' + vereinfacht(activeRun);
    }

    // --- 6. FRISCHE DES STANDES ---
    // "07:38:52" allein sagt nicht, ob die Zeitnahme noch läuft. Mit dem
    // vollen Zeitstempel lässt sich das Alter ausrechnen und ehrlich anzeigen.
    function standAktualisieren() {
        if (!liveStatus) return;

        if (istArchiv) {
            liveStatus.textContent = "Abgeschlossen";
            liveStatus.className = 'live-status live-status--archiv';
            return;
        }
        if (!lastUpdate) {
            liveStatus.textContent = "Warte auf Zeitnahme";
            liveStatus.className = 'live-status live-status--aus';
            return;
        }
        // Ergebnisse eines vergangenen Renntags sind nie "live", auch wenn die
        // Datei gerade erst geschrieben wurde.
        if (renntagIso && renntagIso !== heuteIso()) {
            liveStatus.textContent = "Abgeschlossener Renntag";
            liveStatus.className = 'live-status live-status--archiv';
            return;
        }

        const stand = standIso ? new Date(standIso) : null;
        const alterMin = (stand && !isNaN(stand))
            ? Math.max(0, Math.floor((Date.now() - stand.getTime()) / 60000))
            : 0;

        if (alterMin < 3) {
            liveStatus.textContent = `Live &middot; Stand ${lastUpdate}`.replace('&middot;', '·');
            liveStatus.className = 'live-status live-status--live';
        } else if (alterMin < 45) {
            liveStatus.textContent = `Letzte Zeit vor ${alterMin} Min.`;
            liveStatus.className = 'live-status live-status--ruhig';
        } else {
            liveStatus.textContent = `Keine aktuellen Zeiten · zuletzt ${lastUpdate}`;
            liveStatus.className = 'live-status live-status--aus';
        }
    }
    // Auch ohne neue Daten weiterzählen, damit "vor 5 Min." nicht stehen bleibt
    setInterval(standAktualisieren, 30000);

    // --- 7. FILTER-KNÖPFE: leere Auswahlmöglichkeiten ausgrauen ---
    function filterAbgleichen() {
        const klassenMitDaten = new Set(liveData.map(d => vereinfacht(d.klasse)));
        const laeufeMitDaten = new Set(liveData.map(d => vereinfacht(d.lauf)));

        classButtons.forEach(b => {
            const leer = liveData.length > 0 && !klassenMitDaten.has(vereinfacht(b.innerText));
            b.classList.toggle('btn-filter--leer', leer);
            b.disabled = leer && !b.classList.contains('active');
            b.title = leer ? 'An diesem Renntag ohne Starter' : '';
        });
        runButtons.forEach(b => {
            const leer = liveData.length > 0 && !laeufeMitDaten.has(vereinfacht(b.innerText));
            b.classList.toggle('btn-filter--leer', leer);
            b.disabled = leer && !b.classList.contains('active');
            b.title = leer ? 'Noch nicht gefahren' : '';
        });
        if (allBtn) {
            const leer = liveData.length > 0 && !laeufeMitDaten.has('GESAMT');
            allBtn.classList.toggle('btn-filter--leer', leer);
            allBtn.disabled = leer && !allBtn.classList.contains('active');
            allBtn.title = leer ? 'Noch kein Starter hat beide Läufe beendet' : '';
        }
    }

    // Beim ersten Laden auf eine Ansicht springen, in der auch wirklich Zeiten
    // stehen. Sonst landet der Besucher auf der Voreinstellung (Klasse 3 / 1. WL)
    // und sieht eine leere Tabelle, obwohl das Rennen längst läuft.
    // Ist ein Fahrer vorgemerkt, hat dessen Ansicht Vorrang.
    function waehleBelegteAnsicht() {
        if (nutzerHatGewaehlt || isGesamt || liveData.length === 0) return;

        const hatDaten = (klasse, lauf) => liveData.some(d =>
            vereinfacht(d.klasse) === vereinfacht(klasse) &&
            vereinfacht(d.lauf) === vereinfacht(lauf));

        const ansichtSetzen = (klasse, lauf) => {
            runButtons.forEach(b => b.classList.remove('active'));
            classButtons.forEach(b => b.classList.remove('active'));
            for (const b of classButtons) if (b.innerText.trim() === klasse) b.classList.add('active');
            for (const b of runButtons) if (b.innerText.trim() === lauf) b.classList.add('active');
            activeClass = klasse;
            activeRun = lauf;
            nutzerHatGewaehlt = true;
        };

        // Vorgemerkter Fahrer: die Ansicht wählen, in der er auftaucht
        if (gemerkt.size > 0) {
            for (const laufBtn of runButtons) {
                const lauf = laufBtn.innerText.trim();
                const treffer = liveData.find(d =>
                    vereinfacht(d.lauf) === vereinfacht(lauf) &&
                    gemerkt.has(fahrerSchluessel(d)));
                if (treffer) {
                    for (const klasseBtn of classButtons) {
                        if (vereinfacht(klasseBtn.innerText) === vereinfacht(treffer.klasse)) {
                            ansichtSetzen(klasseBtn.innerText.trim(), lauf);
                            return;
                        }
                    }
                }
            }
        }

        if (hatDaten(activeClass, activeRun)) {
            nutzerHatGewaehlt = true;   // Voreinstellung passt, nicht mehr eingreifen
            return;
        }

        for (const laufBtn of runButtons) {
            for (const klasseBtn of classButtons) {
                const lauf = laufBtn.innerText.trim();
                const klasse = klasseBtn.innerText.trim();
                if (!hatDaten(klasse, lauf)) continue;

                runButtons.forEach(b => b.classList.remove('active'));
                classButtons.forEach(b => b.classList.remove('active'));
                laufBtn.classList.add('active');
                klasseBtn.classList.add('active');
                activeRun = lauf;
                activeClass = klasse;
                nutzerHatGewaehlt = true;
                return;
            }
        }
    }

    // Zustandsmeldung statt leerer Tabelle
    function zeigeHinweis(titel, text, icon) {
        gridContainer.innerHTML = `
            <div class="live-empty">
                <i class="fa-solid ${icon}"></i>
                <h2>${titel}</h2>
                <p>${text}</p>
            </div>`;
    }

    // --- 8. TABELLE BAUEN (HTML GENERIEREN) ---
    function renderTable() {
        if (!liveData || liveData.length === 0) {
            headerBar.innerHTML = `Live-Timing`;
            zeigeHinweis("Noch keine Zeiten",
                "Sobald die Zeitnahme an der Strecke läuft, erscheinen die Ergebnisse " +
                "hier von selbst - die Seite muss nicht neu geladen werden.",
                "fa-stopwatch");
            return;
        }

        // A) Daten filtern (Robust gegen fehlende Leerzeichen, z.B. "1.WL" vs "1. WL")
        let filteredData;
        let titel;
        if (!isGesamt) {
            let normalizedActiveRun = vereinfacht(activeRun);
            let normalizedActiveClass = vereinfacht(activeClass);

            filteredData = liveData.filter(d =>
                vereinfacht(d.klasse) === normalizedActiveClass &&
                vereinfacht(d.lauf) === normalizedActiveRun);

            // Schöner Name für den blauen Balken (aus 1. WL wird 1. Wertungslauf)
            let titleLauf = activeRun;
            if (activeRun === "1. WL") titleLauf = "1. Wertungslauf";
            if (activeRun === "2. WL") titleLauf = "2. Wertungslauf";

            titel = `${titleLauf} &middot; ${activeClass}`;
        } else {
            // Das Gesamtergebnis ist ein eigener Lauf ("Gesamt" = beide
            // Wertungsläufe zusammen), nicht einfach alle Zeilen auf einmal -
            // sonst stünden Einzel- und Gesamtzeiten wild gemischt in einer Tabelle.
            filteredData = liveData.filter(d => vereinfacht(d.lauf) === "GESAMT");
            titel = "Gesamtergebnis &middot; alle Klassen";
        }

        // B) AUTOMATISCHES SORTIEREN & PLATZIERUNG KORRIGIEREN
        // Nach Gesamtzeit sortieren (schnellste Zeit zuerst)
        filteredData.sort((a, b) => {
            return parseTimeToMs(a.zeit_total) - parseTimeToMs(b.zeit_total);
        });

        // Den Platz (1, 2, 3...) streng von oben nach unten neu durchnummerieren!
        // Die Rückstände werden hier ebenfalls neu gerechnet und NICHT aus der
        // JSON übernommen: dort stehen sie je Klasse, im Gesamtergebnis werden
        // aber alle Klassen zusammen gewertet - die Werte passten dann nicht.
        let bestzeit = null;
        let vorherige = null;
        filteredData.forEach((driver, index) => {
            driver.platz = index + 1;

            const zeit = parseTimeToMs(driver.zeit_total);
            const gueltig = zeit !== OHNE_ZEIT;
            if (gueltig && bestzeit === null) bestzeit = zeit;

            driver._aufErsten = (gueltig && bestzeit !== null && index > 0)
                ? '+' + msToZeit(zeit - bestzeit) : "";
            driver._aufVordermann = (gueltig && vorherige !== null && index > 0)
                ? '+' + msToZeit(zeit - vorherige) : "";
            if (gueltig) vorherige = zeit;
        });

        // C) Positionswechsel seit dem letzten neuen Ergebnis festhalten
        const ansicht = ansichtsSchluessel();
        if (letzterStand !== lastUpdate) {
            veraenderungen = { neu: {}, richtung: {} };
        }
        const vorherPlaetze = letztePlaetze[ansicht];
        if (letzterStand !== lastUpdate && vorherPlaetze) {
            filteredData.forEach(d => {
                const s = eintragSchluessel(d);
                const alt = vorherPlaetze[s];
                if (alt === undefined) veraenderungen.neu[s] = true;
                else if (alt !== d.platz) veraenderungen.richtung[s] = alt > d.platz ? 'auf' : 'ab';
            });
        }
        if (letzterStand !== lastUpdate) {
            filteredData.forEach(d => {
                const s = eintragSchluessel(d);
                if (letzteZeiten[s] !== undefined && letzteZeiten[s] !== d.zeit_total) {
                    veraenderungen.neu[s] = true;
                }
            });
        }
        letztePlaetze[ansicht] = {};
        filteredData.forEach(d => { letztePlaetze[ansicht][eintragSchluessel(d)] = d.platz; });

        // D) Kopfzeile über der Tabelle
        headerBar.innerHTML = titel +
            `<span class="results-count">${filteredData.length} Starter</span>`;

        if (filteredData.length === 0) {
            headerBar.innerHTML = titel;
            zeigeHinweis("Für diese Auswahl liegen noch keine Zeiten vor",
                "Wähle eine andere Klasse oder einen anderen Lauf - oder warte, " +
                "bis diese Gruppe gefahren ist.",
                "fa-filter-circle-xmark");
            return;
        }

        // E) Tabellenkopf. Im Gesamtergebnis kommt eine Spalte mit den beiden
        // Einzelläufen dazu - gleiches Muster wie Differenz/Intervall: zwei
        // Werte übereinander in der Reihenfolge des Spaltenkopfs.
        gridContainer.classList.toggle('result-grid--gesamt', isGesamt);

        let html = `
            <div class="grid-header grid-header--mitte">Platz</div>
            <div class="grid-header grid-header--mitte">Nr.</div>
            <div class="grid-header">Fahrer &middot; Ortsclub</div>
            ${isGesamt ? '<div class="grid-header grid-header--rechts">1. WL<br>2. WL</div>' : ''}
            <div class="grid-header grid-header--rechts">Gesamtzeit</div>
            <div class="grid-header grid-header--rechts">Differenz<br>Intervall</div>
        `;

        // F) Eine Zeile je Fahrer
        filteredData.forEach((driver) => {
            const ausgefallen = parseTimeToMs(driver.zeit_total) === OHNE_ZEIT;
            const fSchluessel = fahrerSchluessel(driver);
            const eSchluessel = eintragSchluessel(driver);
            const istGemerkt = gemerkt.has(fSchluessel);
            const istBestzeit = eSchluessel === bestzeitSchluessel;

            // Zweite Zeile der Zeit-Spalte: reine Fahrzeit und Strafsekunden.
            // Nur zeigen, wenn sie etwas hinzufügt (bei Strafzeit null ist die
            // Fahrzeit gleich der Gesamtzeit).
            let zeitDetail = "";
            if (driver.fehler) {
                zeitDetail = `${escapeHtml(driver.zeit_raw)} ` +
                             `<span class="zeit-strafe">${escapeHtml(strafeLesbar(driver.fehler))}</span>`;
            } else if (ausgefallen && driver.zeit_raw) {
                zeitDetail = escapeHtml(driver.zeit_raw);
            }

            // Rückstand: der Führende bekommt kein "+00:00,00", sondern ein Wort
            let rueckstand;
            if (driver.platz === 1) {
                rueckstand = `<span class="diff-fuehrend">Führend</span>`;
            } else if (driver._aufErsten) {
                // Reihenfolge wie im Spaltenkopf: Differenz zum Führenden,
                // darunter das Intervall zum Vordermann
                rueckstand =
                    `<span class="diff-first">${driver._aufErsten}</span>` +
                    (driver._aufVordermann
                        ? `<span class="diff-prev">${driver._aufVordermann}</span>`
                        : "");
            } else {
                rueckstand = `<span class="diff-prev">&ndash;</span>`;
            }

            // Im Gesamtergebnis die beiden Einzelläufe zeigen - so ist
            // nachvollziehbar, woraus sich die Gesamtzeit zusammensetzt.
            let laeufeZelle = "";
            if (isGesamt) {
                const wl1 = einzelzeit(driver, "1. WL");
                const wl2 = einzelzeit(driver, "2. WL");
                laeufeZelle = `
                    <div class="cell-laeufe">
                        <span class="lauf-zeit"><span class="lauf-name">1. WL</span>${wl1 ? escapeHtml(wl1) : '&ndash;'}</span>
                        <span class="lauf-zeit"><span class="lauf-name">2. WL</span>${wl2 ? escapeHtml(wl2) : '&ndash;'}</span>
                    </div>`;
            }

            const richtung = veraenderungen.richtung[eSchluessel];
            const pfeil = richtung
                ? `<span class="platz-pfeil platz-pfeil--${richtung}" aria-hidden="true"></span>`
                : "";

            const klassen = [
                'driver-row',
                `driver-row--platz${driver.platz}`,
                istGemerkt ? 'driver-row--gemerkt' : '',
                veraenderungen.neu[eSchluessel] ? 'driver-row--neu' : '',
            ].filter(Boolean).join(' ');

            html += `
                <div class="${klassen}" data-fahrer="${escapeHtml(fSchluessel)}"
                     role="button" tabindex="0" aria-pressed="${istGemerkt}"
                     title="${istGemerkt ? 'Merken aufheben' : 'Fahrer merken'}">
                    <div class="cell-platz">
                        <span class="platz-badge">${driver.platz}</span>${pfeil}
                    </div>
                    <div class="cell-nr">
                        <span class="startnummer">${escapeHtml(driver.startnummer)}</span>
                    </div>
                    <div class="cell-fahrer">
                        <span class="driver-name">${escapeHtml(driver.name)}${
                            istGemerkt ? '<i class="fa-solid fa-star fahrer-merker" title="Gemerkt"></i>' : ''}${
                            istBestzeit ? '<span class="bestzeit-abzeichen"><i class="fa-solid fa-bolt"></i>Bestzeit</span>' : ''}</span>
                        <span class="driver-club">${escapeHtml(driver.club)}</span>
                    </div>
                    ${laeufeZelle}
                    <div class="cell-zeit">
                        <span class="zeit-gesamt${ausgefallen ? ' zeit-gesamt--ausfall' : ''}">${escapeHtml(driver.zeit_total)}</span>
                        ${zeitDetail ? `<span class="zeit-detail">${zeitDetail}</span>` : ''}
                    </div>
                    <div class="cell-diff">${rueckstand}</div>
                </div>
            `;
        });

        gridContainer.innerHTML = html;
        zumGemerktenFahrerSpringen();

        // Merker für den nächsten Vergleich fortschreiben
        if (letzterStand !== lastUpdate) {
            letzteZeiten = {};
            liveData.forEach(d => { letzteZeiten[eintragSchluessel(d)] = d.zeit_total; });
            letzterStand = lastUpdate;
        }
    }

    // Beim ersten Aufbau zum vorgemerkten Fahrer scrollen - genau EINMAL.
    // Sonst würde die Seite alle drei Sekunden unter dem Finger wegspringen.
    let schonGesprungen = false;
    function zumGemerktenFahrerSpringen() {
        if (schonGesprungen || gemerkt.size === 0) return;

        const zeile = gridContainer.querySelector('.driver-row--gemerkt');
        if (!zeile) return;
        schonGesprungen = true;

        // Auf dem Desktop ist die Zeile "display: contents" und hat selbst
        // keinen Kasten - dann muss die erste Zelle das Ziel sein.
        const ziel = getComputedStyle(zeile).display === 'contents'
            ? zeile.firstElementChild : zeile;
        if (!ziel) return;

        // Steht der Fahrer ohnehin schon im Bild, nicht scrollen
        const kasten = ziel.getBoundingClientRect();
        if (kasten.top >= 90 && kasten.bottom <= window.innerHeight) return;

        const sanft = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        ziel.scrollIntoView({ behavior: sanft ? 'smooth' : 'auto', block: 'center' });
    }

    // --- 9. BESTZEIT DES RENNTAGS ---
    // Schnellste Gesamtzeit eines einzelnen Wertungslaufs, Strafsekunden für
    // Pylonen und Fahrfehler sind darin bereits enthalten. Das Gesamtergebnis
    // bleibt außen vor - es ist die Summe zweier Läufe und nicht vergleichbar.
    function bestzeitBestimmen() {
        let beste = OHNE_ZEIT;
        let schluessel = "";
        liveData.forEach(d => {
            if (vereinfacht(d.lauf) === "GESAMT") return;
            const ms = parseTimeToMs(d.zeit_total);
            if (ms < beste) { beste = ms; schluessel = eintragSchluessel(d); }
        });
        bestzeitSchluessel = beste === OHNE_ZEIT ? "" : schluessel;
    }

    // --- 10. ARCHIV: Liste vergangener Renntage ---
    async function archivListeLaden() {
        if (!archivListe) return;
        try {
            const antwort = await fetch(`../data/ergebnisse/index.json?t=${Date.now()}`);
            if (!antwort.ok) return;
            const tage = (await antwort.json()).renntage || [];
            const andere = tage.filter(t => t.datum !== archivTag);
            if (andere.length === 0) return;

            archivListe.innerHTML =
                `<h2 class="archiv-titel">Vergangene Renntage</h2>` +
                `<ul class="archiv-tage">` +
                andere.slice(0, 12).map(t =>
                    `<li><a href="live.html?tag=${encodeURIComponent(t.datum)}">` +
                    `<span class="archiv-datum">${escapeHtml(t.anzeige)}</span>` +
                    `<span class="archiv-info">${t.starter} Starter</span></a></li>`).join('') +
                `</ul>`;
            archivListe.hidden = false;
        } catch (e) { /* kein Archiv vorhanden - dann nichts anzeigen */ }
    }

    // --- 11. DATEN LADEN (Der "Puls") ---
    // data/livedata.json wird von tools/livetiming_sync.py aus der Datenbank
    // der Zeitmessung erzeugt und bei jeder Änderung neu veröffentlicht.
    async function fetchLiveData() {
        try {
            // Das "?t=" am Ende umgeht den Browser-Cache, damit immer die neuste Datei geladen wird
            const response = await fetch(`${datenQuelle}?t=${new Date().getTime()}`);
            if (response.ok) {
                const data = await response.json();
                liveData = Array.isArray(data.results) ? data.results : [];
                lastUpdate = data.last_update || "";
                standIso = data.stand_iso || "";
                renntagIso = data.datum_iso || "";
                // Renntag und Veranstaltung aus den Daten übernehmen, damit im
                // Kopf nicht die Angaben einer vergangenen Veranstaltung stehen
                if (eventDate && data.datum) eventDate.innerText = data.datum;
                if (eventTitle && data.veranstaltung) eventTitle.innerText = data.veranstaltung;
                bestzeitBestimmen();
                standAktualisieren();
                filterAbgleichen();
                waehleBelegteAnsicht();
                renderTable(); // Tabelle sofort mit neuen Daten zeichnen
            } else if (istArchiv) {
                headerBar.innerHTML = "Renntag nicht gefunden";
                zeigeHinweis("Diesen Renntag gibt es nicht",
                    "Für das angefragte Datum liegen keine Ergebnisse vor.",
                    "fa-calendar-xmark");
            }
        } catch (error) {
            console.log("Warte auf Verbindung zur Zeitnahme...");
        }
    }

    if (istArchiv && archivHinweis) {
        archivHinweis.hidden = false;
    }

    // Beim Start sofort einmal laden...
    fetchLiveData();
    archivListeLaden();

    // ...und ab dann alle 3 Sekunden nach neuen Daten schauen.
    // Im Archiv nicht - dort ändert sich nichts mehr.
    if (!istArchiv) setInterval(fetchLiveData, 3000);

});
