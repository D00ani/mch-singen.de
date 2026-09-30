/*
 * Datei: Streckenplan speichern (Strg/Cmd+S) und öffnen (Strg/Cmd+O).
 * Chrome und Edge am PC schreiben direkt in die gewählte Datei; alle anderen
 * Browser – auch auf iPad/iPhone und Android – legen sie als Download ab.
 */
(function (KP) {
  'use strict';

  const FILE_NAME = 'streckenplan.json';
  const PICKER = {
    types: [{ description: 'Kurs-Planer Streckenplan', accept: { 'application/json': ['.json'] } }]
  };
  const input = document.getElementById('file-input');
  let handle = null;                     // Datei, in die zuletzt gespeichert wurde

  function download(text) {
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = FILE_NAME;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function save() {
    const text = JSON.stringify(KP.editor.getState());
    let name = FILE_NAME;
    try {
      if (!window.showSaveFilePicker) throw new Error('kein Dateidialog');
      if (!handle) {
        handle = await window.showSaveFilePicker(Object.assign({ suggestedName: FILE_NAME }, PICKER));
      }
      const writable = await handle.createWritable();
      await writable.write(text);
      await writable.close();
      name = handle.name;
    } catch (err) {
      if (err.name === 'AbortError') return;      // Dialog abgebrochen
      handle = null;
      download(text);
    }
    KP.editor.markSaved();
    KP.editor.notify('Gespeichert: ' + name);
  }

  function load(text, name) {
    let state = null;
    try {
      state = JSON.parse(text);
    } catch (err) {
      // keine JSON-Datei – wird unten gemeldet
    }
    if (!state || !state.field || !Array.isArray(state.elements)) {
      KP.editor.notify('„' + name + '“ ist kein Streckenplan des Kurs-Planers.');
      return false;
    }
    KP.editor.loadState(state);
    KP.editor.notify('Geöffnet: ' + name);
    return true;
  }

  async function open() {
    if (!window.showOpenFilePicker) {
      input.click();
      return;
    }
    try {
      const [picked] = await window.showOpenFilePicker(PICKER);
      const file = await picked.getFile();
      if (load(await file.text(), file.name)) handle = picked;
    } catch (err) {
      if (err.name !== 'AbortError') input.click();
    }
  }

  input.addEventListener('change', async () => {
    const file = input.files[0];
    input.value = '';
    if (!file) return;
    handle = null;
    load(await file.text(), file.name);
  });

  document.getElementById('btn-save').addEventListener('click', save);
  document.getElementById('btn-open').addEventListener('click', open);

  window.addEventListener('keydown', (e) => {
    if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
    const key = e.key.toLowerCase();
    if (key === 's') {
      e.preventDefault();
      save();
    } else if (key === 'o') {
      e.preventDefault();
      open();
    }
  });

  // Beim Schließen warnen, solange ungespeicherte Änderungen bestehen.
  window.addEventListener('beforeunload', (e) => {
    if (!KP.editor.isDirty()) return;
    e.preventDefault();
    e.returnValue = '';
  });

  KP.file = { save, open, load };
})(window.KP);
