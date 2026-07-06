document.addEventListener("DOMContentLoaded", function() {
    
    // --- 1. ZUSTAND SPEICHERN ---
    let activeClass = "Klasse 3"; // Start-Klasse
    let activeRun = "TL";         // Start-Lauf
    let isGesamt = false;         // Gesamtergebnis-Modus
    
    let liveData = [];            // Zwischenspeicher für die JSON-Daten
    
    const gridContainer = document.getElementById('live-grid');
    const headerBar = document.getElementById('live-header-bar');

    // --- 2. KLICK-LOGIK FÜR DIE BUTTONS ---
    const classButtons = document.querySelectorAll('#class-filters .btn-filter');
    const runButtons = document.querySelectorAll('#run-filters .btn-filter');
    const allBtn = document.querySelector('.btn-filter[data-type="all"]');

    classButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            classButtons.forEach(b => b.classList.remove('active'));
            if(allBtn) allBtn.classList.remove('active');
            this.classList.add('active');
            
            activeClass = this.innerText.trim();
            isGesamt = false;
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
            renderTable();
        });
    });

    if(allBtn) {
        allBtn.addEventListener('click', function() {
            classButtons.forEach(b => b.classList.remove('active'));
            runButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            isGesamt = true;
            renderTable();
        });
    }

    // --- 3. HILFSFUNKTION: ZEIT IN MILLISEKUNDEN UMRECHNEN ---
    // Macht aus "01:00,39" eine echte Zahl (60390), mit der der Browser sortieren kann
    function parseTimeToMs(timeStr) {
        if (!timeStr || timeStr.trim() === "") return 999999999; // Ohne Zeit ganz nach hinten
        try {
            let parts = timeStr.split(',');
            let ms = parts.length > 1 ? parseInt(parts[1]) * 10 : 0; // ,39 wird zu 390ms
            let minSec = parts[0].split(':');
            let m = parseInt(minSec[0]) || 0;
            let s = parseInt(minSec[1]) || 0;
            return (m * 60 * 1000) + (s * 1000) + ms;
        } catch(e) {
            return 999999999;
        }
    }

    // --- 4. TABELLE BAUEN (HTML GENERIEREN) ---
    function renderTable() {
        if (!liveData || liveData.length === 0) {
            headerBar.innerText = "Keine Daten verfügbar / Warte auf Signal...";
            gridContainer.innerHTML = "";
            return;
        }

        // A) Daten filtern (Robust gegen fehlende Leerzeichen, z.B. "1.WL" vs "1. WL")
        let filteredData = liveData;
        if (!isGesamt) {
            let normalizedActiveRun = activeRun.replace(/\s+/g, '').toUpperCase();
            let normalizedActiveClass = activeClass.replace(/\s+/g, '').toUpperCase();

            filteredData = liveData.filter(d => {
                let jsonLauf = (d.lauf || "").replace(/\s+/g, '').toUpperCase();
                let jsonKlasse = (d.klasse || "").replace(/\s+/g, '').toUpperCase();
                return jsonKlasse === normalizedActiveClass && jsonLauf === normalizedActiveRun;
            });
            
            // Schöner Name für den blauen Balken (aus TL wird Trainingslauf etc.)
            let titleLauf = activeRun;
            if (activeRun === "TL") titleLauf = "Trainingslauf";
            if (activeRun === "1. WL") titleLauf = "1. Wertungslauf";
            if (activeRun === "2. WL") titleLauf = "2. Wertungslauf";
            
            headerBar.innerText = `${titleLauf} | ${activeClass}`;
        } else {
            headerBar.innerText = `Gesamtergebnis (Alle Klassen)`;
        }

        // B) AUTOMATISCHES SORTIEREN & PLATZIERUNG KORRIGIEREN
        // Nach Gesamtzeit sortieren (schnellste Zeit zuerst)
        filteredData.sort((a, b) => {
            return parseTimeToMs(a.zeit_total) - parseTimeToMs(b.zeit_total);
        });

        // Den Platz (1, 2, 3...) streng von oben nach unten neu durchnummerieren!
        filteredData.forEach((driver, index) => {
            driver.platz = index + 1;
        });

        // C) Tabellenkopf einfügen
        let html = `
            <div class="grid-header" style="text-align: center;">Platz</div>
            <div class="grid-header" style="text-align: center;">#</div>
            <div class="grid-header">Fahrer<br>Ortsclub</div>
            <div class="grid-header" style="text-align: right;">Zeit</div>
            <div class="grid-header-diff">Differenz<br>Intervall</div>
            <div class="grid-header gap-fill" style="grid-column: 3 / 5;"></div>
        `;

        if(filteredData.length === 0) {
            html += `<div style="grid-column: 1/5; padding: 20px; text-align: center; color: #666;">Noch keine Zeiten für diese Auswahl.</div>`;
            gridContainer.innerHTML = html;
            return;
        }

        // D) Fahrer-Zeilen & Differenzen generieren
        filteredData.forEach((driver) => {
            // Die eigentliche Fahrer-Zeile
            html += `
                <div class="driver-row">
                    <div class="driver-cell" style="text-align: center; font-weight: bold;">${driver.platz}</div>
                    <div class="driver-cell" style="text-align: center;">${driver.startnummer}</div>
                    <div class="driver-cell">
                        <div class="driver-name">${driver.name}</div>
                        <div class="driver-club">${driver.club}</div>
                    </div>
                    <div class="driver-cell time-cell">
                        ${driver.zeit_raw}<br>
                        ${driver.fehler && driver.fehler !== "" ? driver.fehler + '<br>' : ''}
                        ${driver.zeit_total}
                    </div>
                </div>
            `;

            // Der Differenz-Kasten (wird bei JEDEM Fahrer direkt unter ihm angezeigt)
            html += `
                <div class="gap-row">
                    <div class="gap-cell" style="grid-column: 1 / 3;">
                        ${String(driver.platz) === "1" ? '00:00,00<br><br><br>' : `${driver.diff_first || ''}<br>${driver.diff_prev || ''}<br><br>`}
                    </div>
                    <div class="gap-empty" style="grid-column: 3 / 5;"></div>
                </div>
            `;
        });

        gridContainer.innerHTML = html;
    }

    // --- 5. DATEN VOM SERVER LADEN (Der "Puls") ---
    async function fetchLiveData() {
        try {
            // Das "?t=" am Ende umgeht den Browser-Cache, damit immer die neuste Datei geladen wird
            const response = await fetch(`../data/livedata.json?t=${new Date().getTime()}`);
            if (response.ok) {
                const data = await response.json();
                liveData = data.results;
                renderTable(); // Tabelle sofort mit neuen Daten zeichnen
            }
        } catch (error) {
            console.log("Warte auf Verbindung zur Zeitnahme...");
        }
    }

    // Beim Start sofort einmal laden...
    fetchLiveData();
    
    // ...und ab dann alle 3 Sekunden nach neuen Daten schauen
    setInterval(fetchLiveData, 3000); 

});