// ==========================================
// MCH Singen - Haupt-JavaScript
// Zuständig für: Navigation, Sidebar, Dark-Mode, Touch-Gesten
// ==========================================

document.addEventListener('DOMContentLoaded', () => {

    // --- 0. SKIP-LINK (Tastatur/Screenreader: direkt zum Inhalt springen) ---
    (function initSkipLink() {
        const main = document.querySelector('main');
        if (!main) return;
        if (!main.id) main.id = 'main-content';

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

    function openSidebar() {
        if (!sideMenu) return;
        sideMenu.style.willChange = 'transform';
        sideMenu.classList.add('open');
        if (openMenuBtn) openMenuBtn.setAttribute('aria-expanded', 'true');
        sideMenu.addEventListener('transitionend', () => {
            sideMenu.style.willChange = 'auto';
        }, { once: true });
    }

    function closeSidebar() {
        if (!sideMenu) return;
        sideMenu.style.willChange = 'transform';
        sideMenu.classList.remove('open');
        if (openMenuBtn) openMenuBtn.setAttribute('aria-expanded', 'false');
        sideMenu.addEventListener('transitionend', () => {
            sideMenu.style.willChange = 'auto';
        }, { once: true });
    }

    if (openMenuBtn) {
        openMenuBtn.addEventListener('click', (e) => {
            openSidebar();
            e.stopPropagation();
        });
    }

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

    // theme-color Meta-Tag für mobile Browser-Toolbar
    const themeColorMeta = document.createElement('meta');
    themeColorMeta.name = 'theme-color';
    document.head.appendChild(themeColorMeta);

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

    // --- 11. MODERNER FOOTER ---
    (function initFooter() {
        const footer = document.querySelector('footer');
        if (!footer) return;
        const isSubpage = !!document.querySelector('link[href^="../css"]');
        const b = isSubpage ? '../' : '';
        footer.innerHTML = `
            <div class="footer-inner">
                <div class="footer-col footer-brand">
                    <a href="${b}index.html" title="Zur Startseite">
                        <img src="${b}media/logos/mch-logo-128.png" alt="MCH Logo" class="footer-logo" width="128" height="128" loading="lazy">
                    </a>
                    <p class="footer-tagline">Motorsport aus Leidenschaft</p>
                    <p class="footer-desc">Der Motorsportclub "Hohentwiel" e.V. ist ein gemeinnütziger Verein in Singen - aktiver Kart- und Trialsport für Jung und Alt.</p>
                    <a href="https://www.instagram.com/mch_singen/" target="_blank" rel="noopener noreferrer" class="footer-social-btn">
                        <i class="fa-brands fa-instagram"></i> Instagram folgen
                    </a>
                </div>
                <div class="footer-col">
                    <h3 class="footer-heading">Sport</h3>
                    <ul class="footer-links">
                        <li><a href="${b}pages/kartsport.html"><i class="fa-solid fa-flag-checkered"></i> Kartsport</a></li>
                        <li><a href="${b}pages/trialsport.html"><i class="fa-solid fa-motorcycle"></i> Trialsport</a></li>
                        <li><a href="${b}pages/sommerferienprogramm.html"><i class="fa-solid fa-sun"></i> Ferienprogramm</a></li>
                        <li><a href="${b}pages/aktuelles.html"><i class="fa-solid fa-newspaper"></i> Aktuelles</a></li>
                        <li><a href="${b}pages/statistiken.html"><i class="fa-solid fa-chart-line"></i> Statistiken</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h3 class="footer-heading">Verein & Info</h3>
                    <ul class="footer-links">
                        <li><a href="${b}pages/ueber-uns.html"><i class="fa-solid fa-users"></i> Über uns</a></li>
                        <li><a href="${b}pages/mitglied-werden.html"><i class="fa-solid fa-user-plus"></i> Mitglied werden</a></li>
                        <li><a href="${b}pages/kontakt.html"><i class="fa-solid fa-envelope"></i> Kontakt</a></li>
                        <li><a href="${b}pages/faq.html"><i class="fa-solid fa-circle-question"></i> FAQ</a></li>
                        <li><a href="${b}pages/impressum-datenschutz.html"><i class="fa-solid fa-scale-balanced"></i> Impressum</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <span>© 2026 Motorsportclub Singen Hohentwiel e.V. | <a href="#" onclick="return klaro.show();">Cookie-Einstellungen</a></span>
                <p class="designer-credit">Created by <a href="https://www.instagram.com/dnl_kr">Daniel Krieger</a></p>
            </div>
        `;
    })();

    // --- 12. HEADER INLINE NAVIGATION ---
    (function initHeaderNav() {
        const header = document.querySelector('header');
        if (!header) return;

        const isSubpage = !!document.querySelector('link[href^="../css"]');
        const b = isSubpage ? '../' : '';
        const path = window.location.pathname.toLowerCase();

        const links = [
            { href: `${b}index.html`,                      icon: 'fa-house',           label: 'Startseite' },
            { href: `${b}pages/aktuelles.html`,            icon: 'fa-newspaper',       label: 'Aktuelles' },
            { href: `${b}pages/kartsport.html`,            icon: 'fa-flag-checkered',  label: 'Kartsport' },
            { href: `${b}pages/trialsport.html`,           icon: 'fa-motorcycle',      label: 'Trialsport' },
            { href: `${b}pages/ueber-uns.html`,            icon: 'fa-users',           label: 'Über uns' },
            { href: `${b}pages/kontakt.html`,              icon: 'fa-envelope',        label: 'Kontakt' },
        ];

        const nav = document.createElement('nav');
        nav.className = 'header-nav';

        links.forEach(({ href, icon, label }) => {
            const a = document.createElement('a');
            a.href = href;
            a.innerHTML = `<i class="fa-solid ${icon}"></i><span>${label}</span>`;

            const filename = href.split('/').pop().toLowerCase();
            const isHome = filename === 'index.html';
            const isCurrentHome = isHome && (path === '/' || path.endsWith('/index.html') || path.endsWith('/'));
            const isCurrentPage = !isHome && path.endsWith(filename);

            if (isCurrentHome || isCurrentPage) {
                a.classList.add('active');
            }

            nav.appendChild(a);
        });

        header.appendChild(nav);
    })();

    // --- 13. BREADCRUMB NAVIGATION ---
    (function initBreadcrumb() {
        const isSubpage = !!document.querySelector('link[href^="../css"]');
        if (!isSubpage) return;

        const pageNames = {
            'aktuelles.html':               'Aktuelles & Termine',
            'archiv.html':                  'Archiv',
            'faq.html':                     'FAQ',
            'geschichte.html':              'Geschichte',
            'impressum-datenschutz.html':   'Impressum & Datenschutz',
            'kartsport.html':               'Kartsport',
            'kontakt.html':                 'Kontakt',
            'live.html':                    'Live-Ergebnisse',
            'mitglied-werden.html':         'Mitglied werden',
            'sommerferienprogramm.html':    'Sommerferienprogramm',
            'sponsoren-links.html':         'Sponsoren & Links',
            'statistiken.html':             'Statistiken',
            'suche.html':                   'Suche',
            'trialsport.html':              'Trialsport',
            'ueber-uns.html':               'Über uns',
        };

        const filename = window.location.pathname.split('/').pop() || '';
        const currentName = pageNames[filename];
        if (!currentName) return;

        const heroCrumb = document.querySelector('.page-hero-breadcrumb');
        if (heroCrumb) {
            heroCrumb.innerHTML = `<a href="../index.html"><i class="fa-solid fa-house"></i> Startseite</a><span>›</span>${currentName}`;
            return;
        }

        const main = document.querySelector('main');
        if (!main) return;

        const nav = document.createElement('nav');
        nav.className = 'breadcrumb';
        nav.setAttribute('aria-label', 'Breadcrumb');
        nav.innerHTML = `<a href="../index.html"><i class="fa-solid fa-house"></i> Startseite</a><span class="breadcrumb-sep" aria-hidden="true">›</span><span aria-current="page">${currentName}</span>`;
        main.insertBefore(nav, main.firstChild);
    })();

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

});