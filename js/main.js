// ==========================================
// MCH Singen - Haupt-JavaScript
// Zuständig für: Navigation, Sidebar, Dark-Mode, Touch-Gesten
// ==========================================

document.addEventListener('DOMContentLoaded', () => {

    // --- 0. SKIP-LINK (Tastatur/Screenreader: direkt zum Inhalt springen) ---
    // Der Verweis steht inzwischen im Markup jeder Seite - er ist damit auch
    // dann da, wenn JavaScript nicht laeuft. Dieses Stueck legt ihn nur noch
    // an, falls er auf einer Seite fehlt, und haengt keinen zweiten an.
    (function initSkipLink() {
        const main = document.querySelector('main');
        if (!main) return;
        if (!main.id) main.id = 'main-content';
        if (document.querySelector('.skip-link')) return;

        const skipLink = document.createElement('a');
        skipLink.className = 'skip-link';
        skipLink.href = `#${main.id}`;
        skipLink.textContent = 'Zum Inhalt springen';
        document.body.prepend(skipLink);
    })();

    // --- 1. SIDEBAR & NAVIGATION LOGIK ---
    const sideMenu = document.getElementById('side-menu');
    const openMenuBtn = document.getElementById('open-menu');
    const closeMenuBtn = document.getElementById('close-menu');

    // Die Schublade hat seit der Leiste am unteren Rand ZWEI Zugaenge: den
    // Menue-Knopf im Kopf (ab 769px) und den Knopf "Menue" in der Leiste
    // (darunter). Beide muessen ihren aria-expanded-Zustand mitfuehren,
    // sonst meldet ein Vorleseprogramm "zugeklappt", waehrend das Menue
    // offen dasteht.
    const menueOeffner = [openMenuBtn, document.querySelector('.tabbar-menue')]
        .filter(Boolean);

    function oeffnerZustand(offen) {
        menueOeffner.forEach(b => b.setAttribute('aria-expanded', String(offen)));
    }

    // Abdunkelnder Hintergrund: einmal anlegen, gilt fuer alle Seiten.
    // Bewusst hier statt im HTML, damit nicht siebzehn Dateien angefasst
    // werden muessen. Ein Klick darauf schliesst ueber den bereits
    // vorhandenen Klick-daneben-Handler weiter unten.
    let scrim = null;
    if (sideMenu) {
        scrim = document.createElement('div');
        scrim.className = 'sidebar-scrim';
        scrim.setAttribute('aria-hidden', 'true');
        document.body.appendChild(scrim);
    }

    // Merkt sich, von wo aus das Menue geoeffnet wurde, damit der Fokus
    // beim Schliessen genau dorthin zurueckkehrt.
    let fokusVorher = null;

    function fokussierbareElemente() {
        return sideMenu.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
    }

    function openSidebar() {
        if (!sideMenu) return;
        fokusVorher = document.activeElement;
        sideMenu.style.willChange = 'transform';
        sideMenu.classList.add('open');
        if (scrim) scrim.classList.add('open');
        oeffnerZustand(true);

        // Fokus ins Panel holen, sonst steht er weiter hinter dem Menue
        // und die Tastaturbedienung beginnt im verdeckten Seiteninhalt.
        (closeMenuBtn || fokussierbareElemente()[0])?.focus();

        sideMenu.addEventListener('transitionend', () => {
            sideMenu.style.willChange = 'auto';
        }, { once: true });
    }

    function closeSidebar() {
        if (!sideMenu || !sideMenu.classList.contains('open')) return;
        sideMenu.style.willChange = 'transform';
        sideMenu.classList.remove('open');
        if (scrim) scrim.classList.remove('open');
        oeffnerZustand(false);

        // Fokus zurueck an den Ausgangspunkt. Ohne das landet er nach dem
        // Schliessen am Seitenanfang und man navigiert von vorne.
        if (fokusVorher && document.contains(fokusVorher)) fokusVorher.focus();
        else if (menueOeffner.length) menueOeffner[0].focus();
        fokusVorher = null;

        sideMenu.addEventListener('transitionend', () => {
            sideMenu.style.willChange = 'auto';
        }, { once: true });
    }

    // Escape schliesst, und solange das Menue offen ist bleibt der Fokus
    // darin gefangen (Tab am Ende springt zurueck an den Anfang).
    document.addEventListener('keydown', (e) => {
        if (!sideMenu || !sideMenu.classList.contains('open')) return;

        if (e.key === 'Escape') {
            closeSidebar();
            return;
        }
        if (e.key !== 'Tab') return;

        const elemente = fokussierbareElemente();
        if (!elemente.length) return;
        const erstes = elemente[0];
        const letztes = elemente[elemente.length - 1];

        if (e.shiftKey && document.activeElement === erstes) {
            e.preventDefault();
            letztes.focus();
        } else if (!e.shiftKey && document.activeElement === letztes) {
            e.preventDefault();
            erstes.focus();
        }
    });

    menueOeffner.forEach(knopf => {
        knopf.addEventListener('click', (e) => {
            openSidebar();
            // Ohne das faengt der Klick-daneben-Handler weiter unten den
            // eigenen Klick ab und schliesst sofort wieder zu.
            e.stopPropagation();
        });
    });

    if (closeMenuBtn) {
        closeMenuBtn.addEventListener('click', () => {
            closeSidebar();
        });
    }

    // Klick außerhalb des Menüs schließt es
    document.addEventListener('click', (e) => {
        if (sideMenu && sideMenu.classList.contains('open') && !sideMenu.contains(e.target)) {
            closeSidebar();
        }
    });

    // --- 2. DARK MODE TOGGLE ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const body = document.body;

    // theme-color Meta-Tag für mobile Browser-Toolbar.
    // index.html bringt bereits eines mit - dann das nehmen, statt ein zweites
    // anzuhängen (bei zwei Tags gilt das erste, unser Wert käme nie an).
    let themeColorMeta = document.querySelector('meta[name="theme-color"]');
    if (!themeColorMeta) {
        themeColorMeta = document.createElement('meta');
        themeColorMeta.name = 'theme-color';
        document.head.appendChild(themeColorMeta);
    }

    // Theme laden: gespeicherte Präferenz hat Vorrang, sonst System-Einstellung
    const savedTheme = localStorage.getItem('dark-mode');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

    if (savedTheme === 'enabled' || (savedTheme === null && prefersDark.matches)) {
        body.classList.add('dark-mode');
    }

    // System-Theme-Änderungen live verfolgen (nur wenn kein manueller Override)
    prefersDark.addEventListener('change', (e) => {
        if (localStorage.getItem('dark-mode') === null) {
            body.classList.toggle('dark-mode', e.matches);
            updateThemeIcon();
        }
    });

    // Transitions erst nach dem ersten Render aktivieren (verhindert FOUC beim Dark-Mode-Load)
    requestAnimationFrame(() => requestAnimationFrame(() => {
        body.classList.add('transitions-ready');
    }));

    function updateThemeIcon() {
        if (themeToggleBtn) {
            themeToggleBtn.innerHTML = body.classList.contains('dark-mode') ?
                '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
        }
        themeColorMeta.content = body.classList.contains('dark-mode') ? '#1a1a1a' : '#0047cc';
    }
    updateThemeIcon(); // Initiale Icon-Anzeige

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            localStorage.setItem('dark-mode', body.classList.contains('dark-mode') ? 'enabled' : 'disabled');
            updateThemeIcon();
        });
    }

    // --- 3. MOBILE SWIPE GESTURE (Wisch-Menü) ---
    let touchstartX = 0;
    let touchstartY = 0;

    document.addEventListener('touchstart', (e) => { 
        touchstartX = e.changedTouches[0].screenX; 
        touchstartY = e.changedTouches[0].screenY;
    }, {passive: true});

    document.addEventListener('touchend', (e) => {
        let dx = e.changedTouches[0].screenX - touchstartX;
        let dy = Math.abs(e.changedTouches[0].screenY - touchstartY);
        
        // Nur reagieren, wenn es ein horizontaler Wisch war (kein Scrollen)
        if (dy < 50) {
            // Wisch nach rechts (am linken Rand starten) -> Öffnen
            if (dx > 70 && touchstartX < 80) {
                openSidebar();
            }
            // Wisch nach links -> Schließen
            else if (dx < -70) {
                closeSidebar();
            }
        }
    }, {passive: true});

    // --- 4. GLASSMORPHISM HEADER ON SCROLL ---
    const header = document.querySelector('header');
    if (header) {
        window.addEventListener('scroll', () => {
            header.classList.toggle('header-scrolled', window.scrollY > 60);
            if (window.innerWidth <= 768) {
                header.classList.toggle('header-compact', window.scrollY > 50);
            }
        }, { passive: true });
    }

    // --- 5. SCROLL REVEAL ANIMATIONEN ---
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

    // --- 5b. SKELETON LOADING FÜR LAZY IMAGES ---
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
        if (!img.complete) {
            img.classList.add('img-skeleton');
            const removeSkeleton = () => img.classList.remove('img-skeleton');
            img.addEventListener('load', removeSkeleton, { once: true });
            img.addEventListener('error', removeSkeleton, { once: true });
        }
    });

    // --- 6. SCROLL-TO-TOP BUTTON ---
    const scrollBtn = document.createElement('button');
    scrollBtn.id = 'scroll-to-top';
    scrollBtn.setAttribute('aria-label', 'Nach oben scrollen');
    scrollBtn.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
    document.body.appendChild(scrollBtn);

    window.addEventListener('scroll', () => {
        scrollBtn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    scrollBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });


    // --- 8. BEVORSTEHENDE TERMINE: Pulsierender Dot ---
    (function tagUpcomingEvents() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        document.querySelectorAll('.news-card').forEach(card => {
            const dateEl = card.querySelector('.news-date');
            if (!dateEl) return;
            const matches = [...dateEl.textContent.matchAll(/(\d{1,2})\.(\d{2})\.(\d{4})/g)];
            if (!matches.length) return;
            const m = matches[matches.length - 1];
            const eventDate = new Date(+m[3], +m[2] - 1, +m[1]);
            if (eventDate >= today) card.classList.add('news-card-upcoming');
        });
    })();

    // --- 9. KLARO COOKIE CONSENT RELOAD ---
    document.addEventListener('click', function(e) {
        if (e.target.closest('.cm-btn') || e.target.closest('.cn-button')) {
            setTimeout(() => { window.location.reload(true); }, 400);
        }
    });

    // --- 10. SCROLL PROGRESS BAR ---
    const progressBar = document.createElement('div');
    progressBar.id = 'scroll-progress';
    document.body.prepend(progressBar);

    window.addEventListener('scroll', () => {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (docHeight > 0) {
            progressBar.style.width = `${(window.scrollY / docHeight) * 100}%`;
        }
    }, { passive: true });

    // Abschnitt 11 (MODERNER FOOTER) ist entfallen. Er hat den kompletten
    // Fussbereich per innerHTML neu gebaut - das Markup in den Seiten
    // wurde dabei jedes Mal verworfen. Jetzt steht der Fussbereich als
    // echtes Markup in jeder Seite, mit einer zusaetzlichen Spalte fuer
    // Anschrift, Telefon und Trainingszeit.

    // Die frueheren Abschnitte 12 (HEADER INLINE NAVIGATION) und 13
    // (BREADCRUMB NAVIGATION) sind entfallen. Beide bauten ihr Markup erst
    // im Browser zusammen: die Navigation als Streifen aus sechs
    // Versalien-Pillen, der Breadcrumb als erstes Kind von <main>.
    // Ersetzt durch echtes Markup in den Seiten - die Hauptnavigation
    // (siehe Abschnitt 16) fuehrt jetzt alle Seiten ueber Aufklappmenues,
    // und der Breadcrumb steht im Seitenkopf jeder Unterseite. Damit
    // springt beim Laden nichts mehr nach und beides ist ohne JavaScript da.

    // --- 13b. HEADER CTA-BUTTON "MITGLIED WERDEN" ---
    (function initHeaderCTA() {
        const socialHeader = document.querySelector('.social-header');
        if (!socialHeader) return;

        const isSubpage = !!document.querySelector('link[href^="../css"]');
        const b = isSubpage ? '../' : '';

        const cta = document.createElement('a');
        cta.href = `${b}pages/mitglied-werden.html`;
        cta.className = 'header-cta-btn';
        cta.title = 'Mitglied werden';
        cta.innerHTML = '<i class="fa-solid fa-user-plus"></i><span>Mitglied werden</span>';

        socialHeader.insertBefore(cta, socialHeader.firstChild);
    })();

    // --- 16. OFFLINE BANNER ---
    (function initOfflineBanner() {
        const banner = document.createElement('div');
        banner.id = 'offline-banner';
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-live', 'assertive');
        document.body.prepend(banner);

        function showOffline() {
            banner.innerHTML = '<i class="fa-solid fa-wifi"></i> Keine Internetverbindung – einige Inhalte sind möglicherweise nicht verfügbar.';
            banner.classList.remove('back-online');
            banner.classList.add('visible');
        }

        function showOnline() {
            banner.innerHTML = '<i class="fa-solid fa-circle-check"></i> Verbindung wiederhergestellt.';
            banner.classList.add('back-online', 'visible');
            setTimeout(() => banner.classList.remove('visible', 'back-online'), 3000);
        }

        window.addEventListener('offline', showOffline);
        window.addEventListener('online', showOnline);

        if (!navigator.onLine) showOffline();
    })();

    // --- 14. SIDEBAR AKTIVER LINK (automatische Erkennung) ---
    (function initSidebarActive() {
        const navLinks = document.querySelectorAll('#side-menu nav ul li a');
        if (!navLinks.length) return;

        const path = window.location.pathname.toLowerCase();
        const currentFile = path.split('/').pop() || 'index.html';

        navLinks.forEach(link => {
            link.classList.remove('menu_current');
            const href = (link.getAttribute('href') || '').toLowerCase().split('?')[0];
            if (!href || href.startsWith('http')) return;
            const hrefFile = href.split('/').pop();
            if (!hrefFile) return;

            const isHome = hrefFile === 'index.html';
            const isCurrentHome = isHome && (currentFile === 'index.html' || currentFile === '');
            const isCurrentPage = !isHome && currentFile === hrefFile;

            if (isCurrentHome || isCurrentPage) {
                link.classList.add('menu_current');
            }
        });
    })();

    // --- 15. SIDEBAR SECTION LABELS ---
    (function initSidebarLabels() {
        const navList = document.querySelector('#side-menu nav ul');
        if (!navList) return;
        const sections = [
            { key: 'aktuelles',    label: 'Neuigkeiten'    },
            { key: 'ueber-uns',    label: 'Sport & Verein' },
            { key: 'teamkleidung', label: 'Mitmachen'      },
            { key: 'geschichte',   label: 'Mehr'           },
        ];
        [...navList.querySelectorAll('li')].forEach(li => {
            const href = li.querySelector('a')?.getAttribute('href') ?? '';
            const match = sections.find(s => href.includes(s.key));
            if (!match) return;
            const label = document.createElement('li');
            label.className = 'nav-section-label';
            label.setAttribute('aria-hidden', 'true');
            label.textContent = match.label;
            navList.insertBefore(label, li);
        });
    })();

    // --- 16. HAUPTNAVIGATION (Desktop-Leiste) ---
    // Die Leiste wird ab 900px per CSS eingeblendet. Aufgeklappt wird
    // ohnehin schon per :hover und :focus-within - dieses Stueck ergaenzt
    // nur das, was CSS nicht kann: Klick-Umschalten (Touchscreen-Notebooks),
    // Escape zum Schliessen und die Markierung der aktuellen Seite.
    (function initMainNav() {
        const nav = document.querySelector('.main-nav');
        if (!nav) return;

        // -- aktuelle Seite markieren (gleiche Logik wie im Seitenmenue) --
        const path = window.location.pathname.toLowerCase();
        const currentFile = path.split('/').pop() || 'index.html';

        nav.querySelectorAll('a[href]').forEach(link => {
            const href = (link.getAttribute('href') || '').toLowerCase().split('?')[0];
            if (!href || href.startsWith('http')) return;
            const hrefFile = href.split('/').pop();
            if (!hrefFile) return;

            const isHome = hrefFile === 'index.html';
            const treffer = isHome
                ? (currentFile === 'index.html' || currentFile === '')
                : currentFile === hrefFile;
            if (!treffer) return;

            link.classList.add('is-active');
            link.setAttribute('aria-current', 'page');

            // Liegt der Treffer in einem Aufklappfeld, bekommt auch der
            // zugehoerige Reiter die Markierung - sonst zeigt die Leiste
            // im zugeklappten Zustand nirgends an, wo man ist.
            const gruppe = link.closest('.main-nav-item');
            const reiter = gruppe && gruppe.querySelector(':scope > .main-nav-link');
            if (reiter && reiter !== link) reiter.classList.add('is-active');
        });

        // -- Aufklappen und Zuklappen per Klick --
        // Aufgeklappt wird sonst schon per :hover und :focus-within (CSS).
        // Ein Klick muss deshalb BEIDES uebersteuern koennen, sonst haelt
        // der Zeiger auf dem Reiter das Feld offen und der Klick wirkt
        // folgenlos. Dafuer gibt es die Klasse "zu"; sie faellt weg, sobald
        // der Zeiger den Reiter verlaesst.
        const gruppen = [...nav.querySelectorAll('.main-nav-item.has-sub')];

        function istOffen(gruppe) {
            const feld = gruppe.querySelector(':scope > .main-nav-sub');
            return !!feld && getComputedStyle(feld).visibility === 'visible';
        }

        function zuklappen(gruppe, merken) {
            gruppe.classList.remove('open');
            gruppe.classList.toggle('zu', !!merken);
            const schalter = gruppe.querySelector(':scope > .main-nav-link');
            if (schalter) schalter.setAttribute('aria-expanded', 'false');
        }

        function schliesseAlle(ausser) {
            gruppen.forEach(g => { if (g !== ausser) zuklappen(g, false); });
        }

        gruppen.forEach(gruppe => {
            const schalter = gruppe.querySelector(':scope > .main-nav-link');
            if (!schalter || schalter.tagName !== 'BUTTON') return;

            schalter.addEventListener('click', () => {
                if (istOffen(gruppe)) {
                    zuklappen(gruppe, true);
                    // Ohne blur() haelt :focus-within das Feld offen.
                    schalter.blur();
                } else {
                    gruppe.classList.remove('zu');
                    gruppe.classList.add('open');
                    schalter.setAttribute('aria-expanded', 'true');
                }
                schliesseAlle(gruppe);
            });

            // Verlaesst der Zeiger den Reiter, gilt wieder der Normalfall:
            // Hover klappt auf, Klick klappt zu.
            gruppe.addEventListener('mouseleave', () => zuklappen(gruppe, false));
        });

        // Klick daneben und Escape schliessen wieder.
        document.addEventListener('click', e => {
            if (!e.target.closest('.main-nav-item.has-sub')) schliesseAlle(null);
        });

        document.addEventListener('keydown', e => {
            if (e.key !== 'Escape') return;
            const offen = gruppen.find(istOffen);
            if (!offen) return;
            const schalter = offen.querySelector(':scope > .main-nav-link');
            // "zu" merken, weil der Fokus gleich wieder auf den Reiter geht.
            zuklappen(offen, true);
            if (schalter) schalter.focus();
        });
    })();


    // --- 17. TABELLEN AUF DEM HANDY ---
    // Unter 700px werden die Tabellen zu Bloecken gestapelt (css/mobile.css).
    // Damit man dann noch weiss, was ein Wert bedeutet, bekommt jede Zelle
    // die Spaltenueberschrift als data-spalte; das CSS blendet sie davor ein.
    //
    // Warum hier und nicht im Markup: tools/statistiken_pflege.py legt neue
    // Zeilen als schlichtes <td>Wert</td> an und liest sie mit genau diesem
    // Muster wieder ein. Stuende das Attribut im HTML, wuerde das Werkzeug
    // die Zeilen nicht mehr finden - und neu angelegte Zeilen haetten die
    // Beschriftung ohnehin nicht. Zur Laufzeit gesetzt gilt es fuer alle
    // Zeilen, egal wer sie eingetragen hat.
    (function initTabellenBeschriftung() {
        document.querySelectorAll('table.stats-table').forEach(tabelle => {
            const kopf = [...tabelle.querySelectorAll('thead th')]
                .map(th => th.textContent.trim());
            if (!kopf.length) return;
            tabelle.querySelectorAll('tbody tr').forEach(zeile => {
                [...zeile.children].forEach((zelle, i) => {
                    if (kopf[i]) zelle.setAttribute('data-spalte', kopf[i]);
                });
            });
        });
    })();


    // --- 18. ONBOARD-VIDEO: AM RECHNER VON SELBST, AUF DEM HANDY AUF TIPP ---
    // Das Video wiegt 8,4 MB. Frueher stand autoplay direkt im Markup, damit
    // lud es auch am Handy bei jedem Aufruf ueber Mobilfunk. Die Quelle steht
    // deshalb in data-src und wird hier je nach Geraet gesetzt.
    (function initOnboardVideo() {
        const video = document.querySelector('video.track-video[data-src]');
        if (!video) return;

        function quelleSetzen() {
            if (video.src) return;
            video.src = video.dataset.src;
        }

        // Grosser Bildschirm: laden und losspielen wie bisher.
        // matchMedia statt Fensterbreite, damit auch ein gedrehtes Tablet
        // richtig einsortiert wird.
        if (window.matchMedia('(min-width: 769px)').matches) {
            video.preload = 'auto';
            video.autoplay = true;
            quelleSetzen();
            // play() kann abgelehnt werden (Energiesparmodus, Datensparmodus).
            // Dann bleibt einfach das Standbild mit Abspielknopf stehen.
            const versuch = video.play();
            if (versuch && typeof versuch.catch === 'function') versuch.catch(() => {});
            return;
        }

        // Handy: erst laden, wenn jemand wirklich abspielen will.
        video.addEventListener('play', quelleSetzen);
        video.addEventListener('click', quelleSetzen);
    })();

    // --- 19. SCHNELLZUGRIFF UNTEN: AKTUELLE SEITE MARKIEREN ---
    // Gleiche Erkennung wie im Seitenmenue (Abschnitt 14). Die Leiste
    // selbst steht im Markup jeder Seite, damit sie auch ohne JavaScript
    // da ist - nur die Markierung kommt von hier.
    (function initTabbarActive() {
        const links = document.querySelectorAll('.tabbar a.tabbar-link');
        if (!links.length) return;

        const pfad = window.location.pathname.toLowerCase();
        const aktuell = pfad.split('/').pop() || 'index.html';

        links.forEach(link => {
            const ziel = (link.getAttribute('href') || '').toLowerCase().split('?')[0];
            const datei = ziel.split('/').pop();
            if (!datei) return;

            const istStart = datei === 'index.html';
            const trifftStart = istStart && (aktuell === 'index.html' || aktuell === '');
            const trifftSeite = !istStart && aktuell === datei;

            if (trifftStart || trifftSeite) {
                link.classList.add('is-active');
                link.setAttribute('aria-current', 'page');
            }
        });
    })();

    // --- 20. BREADCRUMB: GRUPPE AUFKLAPPBAR ---
    // Die mittlere Stufe ("Startseite / Sport / Kartsport") steht als
    // schlichter Text im Markup und bleibt ohne JavaScript genau das.
    // Hier wird ein Schalter daraus, der die Geschwisterseiten zeigt -
    // also dasselbe Feld, das am Desktop beim Darueberfahren aufklappt.
    //
    // Der Inhalt wird aus der vorhandenen Hauptnavigation geholt und nicht
    // noch einmal aufgeschrieben. Unterhalb von 900px ist die Leiste nur
    // ausgeblendet, im Markup steht sie weiterhin. So koennen die beiden
    // Listen gar nicht auseinanderlaufen: wer oben eine Seite ergaenzt,
    // hat sie hier automatisch mit drin.
    (function initBreadcrumbGruppe() {
        const stufe = document.querySelector('.breadcrumb-gruppe');
        if (!stufe) return;

        const gruppe = (stufe.dataset.gruppe || '').toLowerCase();
        if (!gruppe) return;

        // Passenden Reiter der Hauptnavigation suchen (Verein/Sport/Aktuelles).
        const reiter = [...document.querySelectorAll('.main-nav-item.has-sub')]
            .find(li => {
                const kopf = li.querySelector('.main-nav-link');
                return kopf && kopf.textContent.trim().toLowerCase().startsWith(gruppe);
            });
        const quelle = reiter && reiter.querySelector('.main-nav-sub');
        // Ohne Vorlage bleibt die Stufe der lesbare Text, der sie ohne
        // JavaScript ohnehin waere.
        if (!quelle) return;

        const pfad = window.location.pathname.toLowerCase();
        const aktuell = pfad.split('/').pop() || 'index.html';

        const huelle = document.createElement('span');
        huelle.className = 'breadcrumb-gruppe-huelle';

        const knopf = document.createElement('button');
        knopf.type = 'button';
        knopf.className = 'breadcrumb-gruppe-btn';
        knopf.setAttribute('aria-expanded', 'false');
        knopf.innerHTML = stufe.textContent.trim() +
            ' <i class="fa-solid fa-chevron-down breadcrumb-gruppe-chevron" aria-hidden="true"></i>';

        const feld = document.createElement('ul');
        feld.className = 'breadcrumb-gruppe-feld';
        feld.hidden = true;

        quelle.querySelectorAll('li > a').forEach(a => {
            const zeile = document.createElement('li');
            const kopie = a.cloneNode(true);
            const datei = (kopie.getAttribute('href') || '').toLowerCase().split('/').pop();
            if (datei && datei === aktuell) kopie.setAttribute('aria-current', 'page');
            zeile.appendChild(kopie);
            feld.appendChild(zeile);
        });
        if (!feld.children.length) return;

        knopf.setAttribute('aria-label',
            'Weitere Seiten im Bereich ' + stufe.textContent.trim());

        huelle.appendChild(knopf);
        huelle.appendChild(feld);
        stufe.replaceWith(huelle);

        function zu() {
            feld.hidden = true;
            knopf.setAttribute('aria-expanded', 'false');
        }

        knopf.addEventListener('click', (e) => {
            e.stopPropagation();
            const offen = knopf.getAttribute('aria-expanded') === 'true';
            feld.hidden = offen;
            knopf.setAttribute('aria-expanded', String(!offen));
        });

        document.addEventListener('click', (e) => {
            if (!feld.hidden && !huelle.contains(e.target)) zu();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !feld.hidden) {
                zu();
                knopf.focus();
            }
        });
    })();

});