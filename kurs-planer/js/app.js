/*
 * Offline nutzen: als App installieren (Symbol auf Desktop, Startmenü, Dock
 * oder Home-Bildschirm, eigenes Fenster, läuft ohne Internet) oder als einzelne
 * HTML-Datei herunterladen.
 *
 * Per Knopfdruck installieren können nur Chrome und Edge (Windows, Mac,
 * Android). Überall sonst – vor allem in Safari auf iPad, iPhone und Mac –
 * erlaubt der Browser das nur über sein eigenes Menü; dann zeigt das Fenster
 * die Schritte. Die Anleitungen der anderen Geräte stehen aufklappbar darunter.
 */
(function () {
  'use strict';

  const ZIP_URL = 'https://github.com/D00ani/BKC_Strecken_Planer/archive/refs/heads/main.zip';
  // „Teilen“-Symbol von Safari, damit man es in der Leiste wiedererkennt
  const SHARE_ICON = '<svg class="step-icon" viewBox="0 0 24 24" aria-hidden="true">' +
    '<path d="M12 15V3M8 7l4-4 4 4M7 10H5v11h14V10h-2" fill="none" stroke="currentColor" ' +
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  const $ = (id) => document.getElementById(id);
  const dialog = $('app-dialog');
  const installButton = $('btn-install');
  const hint = $('install-hint');
  const hosted = location.protocol === 'https:' || location.protocol === 'http:';
  let installPrompt = null;              // vom Browser angebotene Installation

  const isInstalled = () =>
    window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

  function platform() {
    const ua = navigator.userAgent;
    // iPadOS gibt sich als Mac aus, hat aber einen Touchscreen.
    if (/iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return 'ios';
    if (/Android/.test(ua)) return 'android';
    if (/Firefox\//.test(ua)) return 'firefox';
    if (/Edg\//.test(ua)) return 'edge';
    if (/Chrome\//.test(ua)) return 'chrome';
    if (/Safari\//.test(ua) && /Macintosh/.test(ua)) return 'safari';
    return 'other';
  }

  const isMobile = () => ['ios', 'android'].includes(platform());

  // Anleitungen für die Wege über das Browsermenü
  const TUTORIALS = {
    ios: {
      title: 'iPad und iPhone (Safari)',
      intro: 'In Safari auf iPad und iPhone legst du das Symbol so an:',
      steps: [
        'Die Seite in Safari öffnen – nicht in der Vorschau einer anderen App.',
        'Auf „Teilen“ ' + SHARE_ICON + ' tippen: am iPad oben rechts, am iPhone unten in der Mitte.',
        'In der Liste nach unten blättern und „Zum Home-Bildschirm“ wählen.',
        'Oben rechts auf „Hinzufügen“ tippen.'
      ],
      outro: 'Danach liegt der Kurs-Planer als Symbol auf dem Home-Bildschirm, öffnet sich ohne ' +
        'Adressleiste und startet ohne Internet.'
    },
    safari: {
      title: 'Mac (Safari)',
      intro: 'In Safari am Mac kommt der Kurs-Planer so ins Dock:',
      steps: [
        'Die Seite in Safari öffnen.',
        'In der Menüleiste „Ablage“ öffnen – oder in der Symbolleiste auf „Teilen“ ' + SHARE_ICON + ' klicken.',
        '„Zum Dock hinzufügen …“ wählen.',
        'Mit „Hinzufügen“ bestätigen.'
      ],
      outro: 'Danach öffnet sich der Kurs-Planer über das Symbol im Dock im eigenen Fenster. ' +
        'Das geht ab macOS 14 (Sonoma).'
    },
    android: {
      title: 'Android (Chrome)',
      intro: 'Auf Android legst du das Symbol über das Browsermenü an:',
      steps: [
        'Oben rechts das Menü <b>⋮</b> öffnen.',
        '„App installieren“ oder „Zum Startbildschirm hinzufügen“ wählen.',
        'Mit „Installieren“ bestätigen.'
      ],
      outro: 'Danach liegt der Kurs-Planer als Symbol auf dem Startbildschirm und startet ohne Internet.'
    },
    chrome: {
      title: 'Windows und Mac (Chrome)',
      intro: 'In Chrome geht es über das Menü so:',
      steps: [
        'Oben rechts das Menü <b>⋮</b> öffnen.',
        '„Streamen, speichern und teilen“ wählen.',
        'Auf „Seite als App installieren“ klicken und bestätigen.'
      ],
      outro: 'Ist die App schon installiert, findest du sie im Startmenü bzw. im Launchpad.'
    },
    edge: {
      title: 'Windows und Mac (Edge)',
      intro: 'In Edge geht es über das Menü so:',
      steps: [
        'Oben rechts das Menü <b>…</b> öffnen.',
        '„Apps“ wählen.',
        'Auf „Diese Website als App installieren“ klicken und bestätigen.'
      ],
      outro: 'Ist die App schon installiert, findest du sie im Startmenü bzw. im Launchpad.'
    }
  };

  // Schritte und Schlusssatz einer Anleitung als Elemente
  function tutorialNodes(tutorial) {
    const list = document.createElement('ol');
    tutorial.steps.forEach((html) => {
      const item = document.createElement('li');
      item.innerHTML = html;              // nur die festen Texte von oben
      list.appendChild(item);
    });
    const outro = document.createElement('p');
    outro.textContent = tutorial.outro;
    return [list, outro];
  }

  // Oben: was auf diesem Gerät gilt. Darunter aufklappbar: die übrigen Geräte.
  function show(intro, own) {
    hint.textContent = intro;
    $('install-tutorial').replaceChildren(...(own ? tutorialNodes(own) : []));

    const others = $('other-tutorials');
    others.replaceChildren();
    others.hidden = !hosted;
    if (!hosted) return;
    const heading = document.createElement('h3');
    heading.textContent = own ? 'Anleitungen für andere Geräte' : 'Anleitungen für alle Geräte';
    others.appendChild(heading);
    Object.values(TUTORIALS).filter((tutorial) => tutorial !== own).forEach((tutorial) => {
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = tutorial.title;
      details.append(summary, ...tutorialNodes(tutorial));
      others.appendChild(details);
    });
  }

  function refresh() {
    const kind = platform();
    const tutorial = TUTORIALS[kind];
    installButton.hidden = true;
    // Der Download ist für Windows und Mac gedacht. Die Einzeldatei baut nur
    // die Online-Seite; eine heruntergeladene Kopie kann sich nicht selbst lesen.
    $('download-section').hidden = isMobile();
    $('single-file').hidden = !hosted;

    if (isInstalled()) {
      show('Die App ist auf diesem Gerät installiert und läuft ohne Internet.');
    } else if (!hosted) {
      show('Du nutzt eine heruntergeladene Kopie. Sie läuft ohne Internet; ' +
        'als App installieren lässt sich nur die Online-Seite.');
    } else if (installPrompt) {
      installButton.hidden = false;
      show(kind === 'android'
        ? 'Legt das Kurs-Planer-Symbol auf den Startbildschirm. Die App läuft danach ohne Internet.'
        : 'Legt ein Symbol an (Windows: Desktop und Startmenü, Mac: Launchpad und Dock). ' +
          'Die App öffnet sich im eigenen Fenster und läuft ohne Internet.');
    } else if (tutorial) {
      show(tutorial.intro, tutorial);
    } else {
      show('Dieser Browser kann keine Apps installieren. Öffne die Seite in Chrome, Edge oder Safari – ' +
        'oder lade die Datei herunter.');
    }
  }

  async function install() {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;                // jedes Angebot gilt nur einmal
    refresh();
  }

  function openDialog() {
    refresh();
    dialog.showModal();
  }

  // ---------- Installation ----------

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();                  // eigenen Knopf statt der Browser-Leiste
    installPrompt = e;
    refresh();
  });

  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    refresh();
  });

  installButton.addEventListener('click', install);
  $('btn-app').addEventListener('click', openDialog);
  $('zip-link').href = ZIP_URL;

  // ---------- Einzeldatei ----------

  // Baut aus der Seite eine einzige HTML-Datei: Styles und Skripte werden
  // eingebettet, damit ein Doppelklick genügt und nichts daneben liegen muss.
  async function buildSingleFile() {
    const load = async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(url + ': ' + response.status);
      return response.text();
    };
    let html = await load('index.html');

    const embed = async (pattern, wrap) => {
      const matches = Array.from(html.matchAll(pattern));
      const contents = await Promise.all(matches.map((match) => load(match[1])));
      // Ersetzen per Funktion: im Code stehen Zeichenfolgen wie $&, die replace sonst deutet.
      matches.forEach((match, i) => {
        html = html.replace(match[0], () => wrap(contents[i]));
      });
    };
    await embed(/<link rel="stylesheet" href="([^"]+)">/g, (css) => '<style>\n' + css + '\n</style>');
    // „</script“ und „<!--“ im Code würden das eingebettete Skript vorzeitig beenden.
    await embed(/<script src="([^"]+)"><\/script>/g, (code) =>
      '<script>\n' + code.replace(/<\/script/gi, '<\\/script').replace(/<!--/g, '<\\!--') + '\n</script>');

    // Das Symbol einbetten; Verweise auf Dateien, die es dann nicht mehr gibt, entfernen.
    const icon = await load('icons/icon.svg');
    html = html.replace(/<link rel="icon"[^>]*>/, () =>
      '<link rel="icon" href="data:image/svg+xml;base64,' + btoa(icon) + '">');
    html = html.replace(/\s*<link rel="(?:manifest|apple-touch-icon)"[^>]*>/g, '');
    return html;
  }

  $('btn-download').addEventListener('click', async () => {
    const button = $('btn-download');
    button.disabled = true;
    try {
      const url = URL.createObjectURL(new Blob([await buildSingleFile()], { type: 'text/html;charset=utf-8' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'Kurs-Planer.html';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      hint.textContent = 'Die Datei ließ sich gerade nicht zusammenstellen (keine Verbindung?). ' +
        'Bitte später noch einmal versuchen.';
    }
    button.disabled = false;
  });

  // ---------- Start ----------

  if (hosted && 'serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js');
  }
})();
