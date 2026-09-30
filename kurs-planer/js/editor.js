/*
 * Arbeitsfläche: Stage, Raster, Ansicht (Zoom/Verschieben), Auswahl über die
 * Ebenen Figur/Teil/Pylone, Verschieben mit Hilfslinien, Kontextmenü,
 * Rückgängig und Ziehen aus der Toolbar – jeweils mit Maus und Touch.
 * Weltkoordinaten sind Meter; die Stage-Skalierung (Pixel pro Meter) ist
 * gleichzeitig der Zoom.
 */
(function (KP) {
  'use strict';

  const BASE_PX_PER_M = 40;           // entspricht 100 % Zoom
  const MIN_PX_PER_M = 4;
  const MAX_PX_PER_M = 400;
  const ROTATE_STEP = 15;             // Grad
  const FIT_MARGIN = 36;              // Pixel, lässt Platz für die Achsbeschriftung
  const ACCENT = '#1a73e8';
  const TITLE = document.title;
  // Finger brauchen größere Griffe als der Mauszeiger.
  const COARSE = window.matchMedia('(pointer: coarse)').matches;

  const field = { width: 50, height: 30 };
  let snapStep = 0.25;

  const $ = (id) => document.getElementById(id);
  const container = $('stage');

  const stage = new Konva.Stage({
    container,
    width: container.clientWidth,
    height: container.clientHeight
  });
  const gridLayer = new Konva.Layer({ listening: false });
  const elementLayer = new Konva.Layer();
  const uiLayer = new Konva.Layer();      // Auswahlrahmen etc., gehört nicht zum Plan
  stage.add(gridLayer, elementLayer, uiLayer);

  // ---------- Raster ----------

  gridLayer.add(new Konva.Shape({
    sceneFunc(context) {
      const c = context._context;
      const pxPerM = stage.scaleX();
      const px = 1 / pxPerM;              // ein Bildschirmpixel in Metern
      const w = field.width;
      const h = field.height;

      const lines = (step, color) => {
        c.beginPath();
        for (let x = step; x < w; x += step) { c.moveTo(x, 0); c.lineTo(x, h); }
        for (let y = step; y < h; y += step) { c.moveTo(0, y); c.lineTo(w, y); }
        c.strokeStyle = color;
        c.lineWidth = px;
        c.stroke();
      };
      const label = (text, x, y, align, baseline) => {
        c.save();
        c.translate(x, y);
        c.scale(px, px);
        c.textAlign = align;
        c.textBaseline = baseline;
        c.fillText(text, 0, 0);
        c.restore();
      };

      c.fillStyle = '#ffffff';
      c.fillRect(0, 0, w, h);
      if (pxPerM >= 8) lines(1, '#e4e7eb');
      lines(5, '#b4bcc6');
      c.strokeStyle = '#4a5560';
      c.lineWidth = 1.5 * px;
      c.strokeRect(0, 0, w, h);

      c.fillStyle = '#4a5560';
      c.font = '11px system-ui, sans-serif';
      const labelStep = pxPerM >= 8 ? 5 : 10;
      for (let x = 0; x <= w; x += labelStep) label(String(x), x, -6 * px, 'center', 'bottom');
      for (let y = labelStep; y <= h; y += labelStep) label(String(y), -6 * px, y, 'right', 'middle');
    }
  }));

  // ---------- Ansicht ----------

  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

  function setView(pxPerM, pos) {
    stage.scale({ x: pxPerM, y: pxPerM });
    stage.position(pos);
    transformer.forceUpdate();
    $('zoom-label').textContent = Math.round((pxPerM / BASE_PX_PER_M) * 100) + ' %';
  }

  // point: Bildschirmposition, die beim Zoomen an Ort und Stelle bleibt
  function zoomAt(point, factor) {
    const old = stage.scaleX();
    const pxPerM = clamp(old * factor, MIN_PX_PER_M, MAX_PX_PER_M);
    const world = { x: (point.x - stage.x()) / old, y: (point.y - stage.y()) / old };
    setView(pxPerM, { x: point.x - world.x * pxPerM, y: point.y - world.y * pxPerM });
  }

  function zoomAtCenter(factor) {
    zoomAt({ x: stage.width() / 2, y: stage.height() / 2 }, factor);
  }

  function fitView() {
    const pxPerM = clamp(
      Math.min(
        (stage.width() - 2 * FIT_MARGIN) / field.width,
        (stage.height() - 2 * FIT_MARGIN) / field.height
      ),
      MIN_PX_PER_M, MAX_PX_PER_M
    );
    setView(pxPerM, {
      x: (stage.width() - field.width * pxPerM) / 2,
      y: (stage.height() - field.height * pxPerM) / 2
    });
    gridLayer.batchDraw();
  }

  // Bild des ganzen Platzes für den Export, unabhängig vom aktuellen Zoom.
  function renderPlan(maxPixels) {
    const margin = 1.5;                   // Meter, Platz für die Achsbeschriftung
    const pxPerM = stage.scaleX();
    const region = {
      x: stage.x() - margin * pxPerM,
      y: stage.y() - margin * pxPerM,
      width: (field.width + 2 * margin) * pxPerM,
      height: (field.height + 2 * margin) * pxPerM
    };
    uiLayer.hide();
    const dataUrl = stage.toDataURL(Object.assign({
      pixelRatio: maxPixels / Math.max(region.width, region.height)
    }, region));
    uiLayer.show();
    return {
      dataUrl,
      widthMeters: field.width + 2 * margin,
      heightMeters: field.height + 2 * margin
    };
  }

  // ---------- Auswahl ----------

  const GUIDE_COLOR = '#e5007d';
  const GUIDE_DISTANCE = 6;           // Pixel, Fangbereich der Hilfslinien
  const GUIDE_LENGTH = 1000;          // Meter, reicht über jeden Platz hinaus
  let guidesEnabled = true;

  const MIN_SIZE = 0.5;               // Meter, kleinste Sperrfläche/-linie
  const ANCHORS = {
    both: ['top-left', 'top-center', 'top-right', 'middle-right',
      'bottom-right', 'bottom-center', 'bottom-left', 'middle-left'],
    length: ['middle-left', 'middle-right']
  };

  const transformer = new Konva.Transformer({
    resizeEnabled: false,
    keepRatio: false,
    flipEnabled: false,
    ignoreStroke: true,               // Rahmen = reines Maß, ohne Linienstärke
    boundBoxFunc: (oldBox, newBox) =>
      (newBox.width < MIN_SIZE * stage.scaleX() || newBox.height < 0.1 * stage.scaleX() ? oldBox : newBox),
    rotationSnaps: Array.from({ length: 360 / ROTATE_STEP }, (_, i) => i * ROTATE_STEP),
    rotationSnapTolerance: 4,
    rotateAnchorOffset: COARSE ? 40 : 26,
    padding: 5,
    anchorSize: COARSE ? 18 : 9,
    anchorCornerRadius: COARSE ? 9 : 5,
    borderStroke: ACCENT,
    anchorStroke: ACCENT
  });
  const marquee = new Konva.Rect({
    fill: 'rgba(26, 115, 232, 0.12)',
    stroke: ACCENT,
    strokeWidth: 1,
    strokeScaleEnabled: false,
    listening: false,
    visible: false
  });
  const guideStyle = {
    stroke: GUIDE_COLOR, strokeWidth: 1, strokeScaleEnabled: false,
    dash: [6, 4], listening: false, visible: false
  };
  const guideV = new Konva.Line(guideStyle);
  const guideH = new Konva.Line(guideStyle);
  uiLayer.add(guideV, guideH, transformer, marquee);

  let selection = [];
  const allElements = () => elementLayer.find('.element');
  const defOf = (node) => KP.elements[node.getAttr('elementType')];

  function attachTransformer() {
    // Größe ändern geht nur bei einem einzeln gewählten Element mit Griffen.
    const resize = selection.length === 1 ? defOf(selection[0]).resize : null;
    transformer.resizeEnabled(Boolean(resize));
    transformer.enabledAnchors(ANCHORS[resize] || ANCHORS.both);
    transformer.nodes(selection);
  }

  function setSelection(nodes) {
    selection = nodes;
    attachTransformer();
    updateUi();
  }

  // ---------- Figuren und ihre Ebenen ----------

  // Was gemeinsam abgelegt wurde, gehört zu einer Figur ('figure'); die Pylonen
  // einer aufgelösten Gruppe teilen sich zusätzlich ein 'part'. Ein Klick wählt
  // die oberste Ebene, jeder Doppelklick geht eine Ebene tiefer:
  // Figur -> Teil (Gasse, Pfeil, Pylonengruppe) -> einzelne Pylone.
  // scope hält fest, welche Ebenen gerade „betreten“ sind.
  let idCount = 0;
  let scope = [];

  const pathOf = (node) => [node.getAttr('figure'), node.getAttr('part')].filter(Boolean);

  function setPath(node, path) {
    node.setAttr('figure', path[0]);
    node.setAttr('part', path[1]);
  }

  function enteredDepth(path) {
    let depth = 0;
    while (depth < scope.length && scope[depth] === path[depth]) depth++;
    return depth;
  }

  // Alles, was ein Klick auf das Element auf der aktuellen Ebene wählt.
  function unitOf(element) {
    const path = pathOf(element);
    const depth = enteredDepth(path);
    scope = scope.slice(0, depth);        // andere Figur angeklickt: Ebenen verlassen
    if (depth >= path.length) return [element];
    return allElements().filter((n) => {
      const other = pathOf(n);
      return path.slice(0, depth + 1).every((id, i) => other[i] === id);
    });
  }

  const elementAt = (target) =>
    (target === stage ? null : target.findAncestor('.element', true));

  function selectElement(element, additive) {
    const unit = unitOf(element);
    if (!additive) {
      setSelection(unit);
    } else if (selection.includes(element)) {
      setSelection(selection.filter((n) => !unit.includes(n)));
    } else {
      setSelection(selection.concat(unit.filter((n) => !selection.includes(n))));
    }
  }

  // Löst eine Pylonengruppe in einzelne Pylonen-Elemente auf, die weiter zur
  // selben Figur gehören. Gibt die Pylone zurück, die dem Mauszeiger am nächsten ist.
  function explode(group) {
    const shapes = group.find('.pylon');
    if (shapes.length < 2) return null;
    const path = pathOf(group).concat('teil-' + (++idCount));
    // Ohne Zeiger auf der Arbeitsfläche (Figur nur angetippt und über die Leiste
    // aufgelöst) zählt die Mitte der Figur.
    const pointer = stage.getRelativePointerPosition() || group.position();
    const transform = group.getTransform();
    let nearest = null;
    let best = Infinity;
    shapes.forEach((shape) => {
      const pos = transform.point(shape.position());
      const node = KP.createElement(shape.getClassName() === 'Rect' ? 'pylon-standing' : 'pylon-lying');
      node.position(pos);
      node.rotation(group.rotation() + shape.rotation());
      setPath(node, path);
      elementLayer.add(node);
      const distance = Math.hypot(pos.x - pointer.x, pos.y - pointer.y);
      if (distance < best) {
        best = distance;
        nearest = node;
      }
    });
    stripPylons(group);
    if (group.getChildren().length) {
      setPath(group, path);               // Linien/Beschriftung bleiben als Teil erhalten
    } else {
      group.destroy();
    }
    sortElements();
    return nearest;
  }

  function stripPylons(group) {
    group.find('.pylon, .grip').forEach((shape) => shape.destroy());
    group.setAttr('exploded', true);
  }

  // Kleine Elemente nach oben, damit sie über großen Figuren greifbar bleiben;
  // Sperrflächen ganz nach unten.
  function sortElements() {
    const area = (node) => {
      if (defOf(node).background) return Infinity;
      const box = node.getClientRect({ skipTransform: true });
      return box.width * box.height;
    };
    allElements()
      .map((node) => ({ node, area: area(node) }))
      .sort((a, b) => b.area - a.area)
      .forEach((entry) => entry.node.moveToTop());
  }

  function addElement(id, pos) {
    const parts = KP.presetParts(id);
    const figure = parts.length > 1 ? 'figur-' + (++idCount) : undefined;
    const nodes = parts.map((part) => {
      const node = KP.createElement(part.id, part.options);
      node.position({ x: pos.x + part.x, y: pos.y + part.y });
      node.rotation(part.rotation || 0);
      // group: Teile, die innerhalb der Figur zusammengehören (Pylone + ihr Pfeil)
      setPath(node, [figure, part.group && figure + '/' + part.group]);
      elementLayer.add(node);
      return node;
    });
    sortElements();
    scope = [];
    setSelection(nodes);
    commit();
    return nodes;
  }

  function deleteSelection() {
    const nodes = selection;
    setSelection([]);
    nodes.forEach((node) => node.destroy());
    commit();
  }

  // ---------- Zustand: Speichern, Laden, Rückgängig ----------

  function getState() {
    return {
      version: 1,
      field: { width: field.width, height: field.height },
      trackWidth: KP.settings.trackWidth,
      idCount,
      elements: allElements().map((node) => ({
        type: node.getAttr('elementType'),
        x: node.x(),
        y: node.y(),
        rotation: node.rotation(),
        options: Object.assign({}, node.getAttr('options'), node.getAttr('boxSize')),
        figure: node.getAttr('figure'),
        part: node.getAttr('part'),
        exploded: node.getAttr('exploded') || undefined
      }))
    };
  }

  function applyState(state) {
    setSelection([]);
    scope = [];
    allElements().forEach((node) => node.destroy());
    field.width = state.field.width;
    field.height = state.field.height;
    $('field-width').value = field.width;
    $('field-height').value = field.height;
    KP.settings.trackWidth = state.trackWidth || KP.settings.trackWidth;
    $('track-width').value = KP.settings.trackWidth.toFixed(2);
    idCount = Math.max(idCount, state.idCount || 0);
    state.elements.forEach((item) => {
      if (!KP.elements[item.type]) return;
      const node = KP.createElement(item.type, item.options);
      node.position({ x: item.x, y: item.y });
      node.rotation(item.rotation || 0);
      setPath(node, [item.figure, item.part]);
      if (item.exploded) stripPylons(node);
      elementLayer.add(node);
    });
    sortElements();
    gridLayer.batchDraw();
    updateUi();
  }

  // Verlauf: nach jeder Änderung wird der ganze Plan als Text festgehalten.
  const HISTORY_LIMIT = 100;
  const history = { stack: [], index: -1, saved: null };

  function commit() {
    const state = JSON.stringify(getState());
    if (state !== history.stack[history.index]) {
      history.stack = history.stack.slice(Math.max(0, history.index + 2 - HISTORY_LIMIT), history.index + 1);
      history.stack.push(state);
      history.index = history.stack.length - 1;
    }
    updateUi();
  }

  // step -1 = rückgängig, +1 = wiederholen
  function stepHistory(step) {
    const target = history.index + step;
    if (target < 0 || target >= history.stack.length) return;
    history.index = target;
    applyState(JSON.parse(history.stack[target]));
  }

  const isDirty = () => history.stack[history.index] !== history.saved;

  function markSaved() {
    history.saved = history.stack[history.index];
    updateUi();
  }

  // Plan aus einer Datei; das Laden ist selbst ein Schritt im Verlauf.
  function loadState(state) {
    applyState(state);
    fitView();
    commit();
    markSaved();
  }

  let notifyTimer = null;

  function notify(text) {
    $('status-message').textContent = text;
    clearTimeout(notifyTimer);
    notifyTimer = setTimeout(() => { $('status-message').textContent = ''; }, 5000);
  }

  // Dreht die Auswahl um ihren gemeinsamen Mittelpunkt.
  function rotateSelection(deg) {
    if (!selection.length) return;
    const cx = selection.reduce((sum, n) => sum + n.x(), 0) / selection.length;
    const cy = selection.reduce((sum, n) => sum + n.y(), 0) / selection.length;
    const rad = (deg * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    selection.forEach((n) => {
      const dx = n.x() - cx;
      const dy = n.y() - cy;
      n.position({ x: cx + dx * cos - dy * sin, y: cy + dx * sin + dy * cos });
      n.rotation(n.rotation() + deg);
    });
    commit();
  }

  // Spiegelt die Auswahl an der senkrechten Achse durch ihren Mittelpunkt.
  // Die Elemente werden gespiegelt neu gezeichnet (kein negativer Maßstab),
  // damit Beschriftungen lesbar bleiben.
  function mirrorSelection() {
    if (!selection.length) return;
    const cx = selection.reduce((sum, n) => sum + n.x(), 0) / selection.length;
    const mirrored = selection.map((old) => {
      const options = Object.assign({}, old.getAttr('options'), old.getAttr('boxSize'), {
        mirror: !old.getAttr('options').mirror
      });
      const node = KP.createElement(old.getAttr('elementType'), options);
      node.position({ x: 2 * cx - old.x(), y: old.y() });
      node.rotation(-old.rotation());
      setPath(node, pathOf(old));
      if (old.getAttr('exploded')) stripPylons(node);
      elementLayer.add(node);
      old.destroy();
      return node;
    });
    sortElements();
    setSelection(mirrored);
    commit();
  }

  // Kehrt die Fahrtrichtung um: jeder Pfeil der Auswahl zeigt auf demselben
  // Weg in die Gegenrichtung.
  const arrowsInSelection = () => selection.filter((n) => defOf(n).arrow);

  function flipArrows() {
    arrowsInSelection().forEach((node) => {
      const options = node.getAttr('options');
      const size = node.getAttr('boxSize');
      options.reverse = !options.reverse;
      KP.setElementSize(node, size.width, size.height);
    });
    commit();
  }

  // ---------- Verschieben: Raster und Hilfslinien ----------

  const snapValue = (v) => (snapStep ? Math.round(v / snapStep) * snapStep : v);
  const snapPoint = (p) => ({ x: snapValue(p.x), y: snapValue(p.y) });

  // Ausrichtungsrahmen eines Elements in Metern: bei Pylonen-Figuren die
  // Pylonenmitten, sonst der Umriss.
  function alignBox(node) {
    const pylons = node.find('.pylon');
    if (!pylons.length) {
      const r = node.getClientRect({ relativeTo: elementLayer, skipStroke: true });
      return { x0: r.x, y0: r.y, x1: r.x + r.width, y1: r.y + r.height };
    }
    const transform = node.getTransform();
    const box = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
    pylons.forEach((pylon) => {
      const p = transform.point(pylon.position());
      box.x0 = Math.min(box.x0, p.x);
      box.y0 = Math.min(box.y0, p.y);
      box.x1 = Math.max(box.x1, p.x);
      box.y1 = Math.max(box.y1, p.y);
    });
    return box;
  }

  // Kanten und Mitte eines Rahmens auf einer Achse
  const edges = (a, b) => [a, (a + b) / 2, b];

  // Nächstgelegene Fluchtlinie: stop = Kante/Mitte eines ruhenden Elements,
  // value = Kante/Mitte der gezogenen Auswahl.
  function nearestStop(stops, values, tolerance) {
    let best = null;
    values.forEach((value) => {
      stops.forEach((stop) => {
        const diff = stop - value;
        if (Math.abs(diff) < tolerance && (!best || Math.abs(diff) < Math.abs(best.diff))) {
          best = { diff, at: stop };
        }
      });
    });
    return best;
  }

  function showGuide(line, points) {
    line.visible(Boolean(points));
    if (points) line.points(points);
  }

  // Beim Ziehen bewegt sich die ganze Auswahl um denselben Versatz. Liegt eine
  // Kante oder die Mitte in einer Flucht mit einem anderen Element, rastet die
  // Auswahl dort ein und die Hilfslinie erscheint; sonst gilt das Raster.
  let drag = null;

  elementLayer.on('dragstart', (e) => {
    const primary = e.target;
    if (!selection.includes(primary)) selectElement(primary, false);
    const moving = new Set(selection);
    const stops = { x: [], y: [] };
    if (guidesEnabled) {
      allElements().forEach((node) => {
        if (moving.has(node) || defOf(node).category === 'Fahrtrichtung') return;
        const box = alignBox(node);
        stops.x.push(...edges(box.x0, box.x1));
        stops.y.push(...edges(box.y0, box.y1));
      });
    }
    // Ausgerichtet werden die Pylonen, nicht die mitwandernden Pfeile.
    const bodies = selection.filter((n) => defOf(n).category !== 'Fahrtrichtung');
    const box = (bodies.length ? bodies : selection).map(alignBox).reduce((a, b) => ({
      x0: Math.min(a.x0, b.x0), y0: Math.min(a.y0, b.y0),
      x1: Math.max(a.x1, b.x1), y1: Math.max(a.y1, b.y1)
    }));
    // Am Raster rastet die Figur selbst ein, auch wenn man sie an einem ihrer
    // Pfeile greift: maßgeblich ist das größte Element ohne Pfeil.
    const area = (n) => {
      const r = n.getClientRect({ skipTransform: true });
      return r.width * r.height;
    };
    const anchor = bodies.includes(primary) || !bodies.length
      ? primary
      : bodies.reduce((a, b) => (area(b) > area(a) ? b : a));
    drag = {
      primary,
      anchor,
      starts: new Map(selection.map((n) => [n, n.position()])),
      box,
      stops
    };
    transformer.nodes([]);                // Rahmen erst nach dem Ziehen wieder zeigen
  });

  elementLayer.on('dragmove', () => {
    if (!drag) return;
    const from = drag.starts.get(drag.primary);
    const raw = drag.primary.position();
    const rawDx = raw.x - from.x;
    const rawDy = raw.y - from.y;
    const anchor = drag.starts.get(drag.anchor);
    const grid = snapPoint({ x: anchor.x + rawDx, y: anchor.y + rawDy });
    const tolerance = GUIDE_DISTANCE / stage.scaleX();
    const b = drag.box;
    const gx = nearestStop(drag.stops.x, edges(b.x0 + rawDx, b.x1 + rawDx), tolerance);
    const gy = nearestStop(drag.stops.y, edges(b.y0 + rawDy, b.y1 + rawDy), tolerance);
    const dx = gx ? rawDx + gx.diff : grid.x - anchor.x;
    const dy = gy ? rawDy + gy.diff : grid.y - anchor.y;
    drag.starts.forEach((start, node) => {
      node.position({ x: start.x + dx, y: start.y + dy });
    });
    showGuide(guideV, gx && [gx.at, -GUIDE_LENGTH, gx.at, GUIDE_LENGTH]);
    showGuide(guideH, gy && [-GUIDE_LENGTH, gy.at, GUIDE_LENGTH, gy.at]);
    updateUi();
  });

  elementLayer.on('dragend', () => {
    drag = null;
    showGuide(guideV, null);
    showGuide(guideH, null);
    attachTransformer();
    commit();
  });

  elementLayer.on('mouseover', () => { container.style.cursor = 'move'; });
  elementLayer.on('mouseout', () => { container.style.cursor = ''; });

  transformer.on('transform', () => {
    const node = selection[0];
    const resize = defOf(node).resize;
    if (resize && selection.length === 1) {
      const size = node.getAttr('boxSize');
      KP.setElementSize(
        node,
        size.width * node.scaleX(),
        resize === 'both' ? size.height * node.scaleY() : size.height
      );
      node.scale({ x: 1, y: 1 });
    }
    updateUi();
  });
  transformer.on('transformend', commit);

  // ---------- Maus: Auswahl, Auswahlrahmen, Ansicht verschieben ----------

  let pan = null;
  let panMode = false;                    // Leertaste gedrückt
  let marqueeStart = null;

  const marqueeDragged = () =>
    marquee.visible() && Math.max(marquee.width(), marquee.height()) * stage.scaleX() > 3;

  function setPanMode(on) {
    if (panMode === on) return;
    panMode = on;
    elementLayer.listening(!on);
    uiLayer.listening(!on);
    container.style.cursor = on ? 'grab' : '';
  }

  stage.on('mousedown', (e) => {
    if (e.evt.button !== 0 || panMode) {
      e.evt.preventDefault();
      pan = {
        clientX: e.evt.clientX, clientY: e.evt.clientY, x: stage.x(), y: stage.y(),
        moved: false,
        // Rechtsklick ohne Ziehen öffnet das Kontextmenü dieses Elements
        element: e.evt.button === 2 ? elementAt(e.target) : null
      };
      return;
    }
    if (e.target !== stage) return;
    marqueeStart = stage.getRelativePointerPosition();
    marquee.setAttrs({ x: marqueeStart.x, y: marqueeStart.y, width: 0, height: 0, visible: true });
  });

  window.addEventListener('mousemove', (e) => {
    if (pan) {
      const dx = e.clientX - pan.clientX;
      const dy = e.clientY - pan.clientY;
      if (!pan.moved && Math.hypot(dx, dy) < 4) return;
      pan.moved = true;
      container.style.cursor = 'grabbing';
      setView(stage.scaleX(), { x: pan.x + dx, y: pan.y + dy });
    } else if (marqueeStart) {
      stage.setPointersPositions(e);
      const p = stage.getRelativePointerPosition();
      marquee.setAttrs({
        x: Math.min(p.x, marqueeStart.x),
        y: Math.min(p.y, marqueeStart.y),
        width: Math.abs(p.x - marqueeStart.x),
        height: Math.abs(p.y - marqueeStart.y)
      });
    }
  });

  window.addEventListener('mouseup', (e) => {
    if (pan) {
      if (!pan.moved && pan.element) openMenu(pan.element, e.clientX, e.clientY);
      pan = null;
      container.style.cursor = panMode ? 'grab' : '';
    }
    if (!marqueeStart) return;
    if (marqueeDragged()) {
      const box = marquee.getClientRect();
      // Wie beim Klick zählt die ganze Figur, auch wenn der Rahmen nur ein Teil berührt.
      scope = [];
      const hits = new Set();
      allElements()
        .filter((n) => Konva.Util.haveIntersection(box, n.getClientRect()))
        .forEach((n) => unitOf(n).forEach((member) => hits.add(member)));
      const additive = e.shiftKey || e.ctrlKey || e.metaKey;
      setSelection(Array.from(additive ? new Set(selection.concat(Array.from(hits))) : hits));
    }
    marqueeStart = null;
    marquee.visible(false);
  });

  stage.on('click tap', (e) => {
    if (e.evt.button || panMode) return;
    if (e.type === 'tap' && suppressTap) return;   // Finger hat verschoben, gezoomt oder das Menü geöffnet
    if (marqueeDragged()) return;         // wird im mouseup ausgewertet
    if (e.target.getLayer() === uiLayer) return;
    const additive = e.evt.shiftKey || e.evt.ctrlKey || e.evt.metaKey;
    const element = elementAt(e.target);
    if (element) {
      selectElement(element, additive);
    } else if (!additive) {
      scope = [];
      setSelection([]);
    }
  });

  // Doppelklick: eine Ebene tiefer. Ganz unten wird die Pylonengruppe in
  // einzelne Pylonen aufgelöst, die sich dann einzeln verschieben/löschen lassen.
  let lastDrill = 0;

  // Geht von diesem Element aus eine Ebene tiefer.
  function drill(element) {
    const path = pathOf(element);
    const depth = enteredDepth(path);
    if (depth < path.length) {
      scope = path.slice(0, depth + 1);
      setSelection(unitOf(element));
      return;
    }
    const pylon = explode(element);
    if (pylon) {
      scope = pathOf(pylon);
      setSelection([pylon]);
      commit();
    }
  }

  const canDrill = (element) =>
    enteredDepth(pathOf(element)) < pathOf(element).length || element.find('.pylon').length > 1;

  // ---------- Beschriftung (Sperrfläche) ----------

  const textDialog = $('text-dialog');
  let textTarget = null;

  // Das einzeln gewählte Element, falls es sich beschriften lässt
  const textElement = () =>
    (selection.length === 1 && defOf(selection[0]).editableText ? selection[0] : null);

  function editText(node) {
    textTarget = node;
    $('text-input').value = node.getAttr('options').text || '';
    textDialog.showModal();
    $('text-input').select();
  }

  // „Übernehmen“ ist der einzige Absende-Knopf, damit die Eingabetaste übernimmt.
  $('text-cancel').addEventListener('click', () => textDialog.close());

  // Übernommen wird beim Absenden des Formulars; es schließt das Fenster selbst.
  // (Auf das close-Ereignis ist nach einem Abbrechen nicht immer Verlass.)
  textDialog.querySelector('form').addEventListener('submit', () => {
    const node = textTarget;
    if (!node || !node.getLayer()) return;
    const size = node.getAttr('boxSize');
    node.getAttr('options').text = $('text-input').value.trim();
    KP.setElementSize(node, size.width, size.height);
    commit();
  });

  stage.on('dblclick dbltap', (e) => {
    const element = elementAt(e.target);
    if (!element) return;
    // Konva meldet bei schnellem Weiterklicken jeden Klick als Doppelklick;
    // ein Dreifachklick soll aber nicht gleich zwei Ebenen tiefer gehen.
    const now = performance.now();
    if (now - lastDrill < Konva.dblClickWindow) return;
    lastDrill = now;
    if (defOf(element).editableText && !canDrill(element)) {
      setSelection([element]);
      editText(element);
      return;
    }
    drill(element);
  });

  stage.on('wheel', (e) => {
    e.evt.preventDefault();
    zoomAt(stage.getPointerPosition(), Math.exp(-clamp(e.evt.deltaY, -200, 200) * 0.0015));
  });

  container.addEventListener('contextmenu', (e) => e.preventDefault());

  // ---------- Touch ----------

  // Ein Finger auf freier Fläche verschiebt die Ansicht, zwei Finger zoomen,
  // langes Drücken auf ein Element öffnet das Kontextmenü. Elemente ziehen,
  // Antippen und Doppeltippen erledigt Konva über dieselben Wege wie die Maus.
  const LONG_PRESS = 550;                 // Millisekunden
  let touchPan = null;
  let pinch = null;
  let press = null;
  let suppressTap = false;

  const touchPoint = (touch) => {
    const rect = container.getBoundingClientRect();
    return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
  };

  function pinchState(touches) {
    const a = touchPoint(touches[0]);
    const b = touchPoint(touches[1]);
    return {
      distance: Math.hypot(b.x - a.x, b.y - a.y),
      center: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
    };
  }

  function cancelPress() {
    if (press) clearTimeout(press.timer);
    press = null;
  }

  stage.on('touchstart', (e) => {
    const touches = e.evt.touches;
    cancelPress();
    closeMenu();
    if (touches.length === 2) {
      // Zweiter Finger: ein begonnenes Ziehen abbrechen und zoomen.
      e.evt.preventDefault();
      Konva.DD._dragElements.forEach((entry) => entry.node.stopDrag());
      pinch = pinchState(touches);
      touchPan = null;
      suppressTap = true;
      return;
    }
    if (touches.length !== 1) return;
    suppressTap = false;
    const touch = touches[0];
    const element = elementAt(e.target);
    if (element) {
      press = {
        clientX: touch.clientX,
        clientY: touch.clientY,
        timer: setTimeout(() => {
          press = null;
          if (drag) return;
          suppressTap = true;
          openMenu(element, touch.clientX, touch.clientY);
        }, LONG_PRESS)
      };
    } else if (e.target === stage) {
      e.evt.preventDefault();             // sonst reicht der Browser Mausereignisse nach
      touchPan = { clientX: touch.clientX, clientY: touch.clientY, x: stage.x(), y: stage.y() };
    }
  });

  stage.on('touchmove', (e) => {
    const touches = e.evt.touches;
    if (touches.length === 2 && pinch) {
      e.evt.preventDefault();
      const now = pinchState(touches);
      zoomAt(pinch.center, now.distance / pinch.distance);
      setView(stage.scaleX(), {
        x: stage.x() + now.center.x - pinch.center.x,
        y: stage.y() + now.center.y - pinch.center.y
      });
      pinch = now;
      return;
    }
    const touch = touches[0];
    if (press && Math.hypot(touch.clientX - press.clientX, touch.clientY - press.clientY) > 8) cancelPress();
    if (!touchPan) return;
    e.evt.preventDefault();
    const dx = touch.clientX - touchPan.clientX;
    const dy = touch.clientY - touchPan.clientY;
    if (Math.hypot(dx, dy) > 4) suppressTap = true;
    setView(stage.scaleX(), { x: touchPan.x + dx, y: touchPan.y + dy });
  });

  stage.on('touchend', (e) => {
    const touches = e.evt.touches;
    cancelPress();
    if (touches.length < 2) pinch = null;
    // Nach dem Zoomen bleibt ein Finger liegen: mit ihm weiter verschieben.
    touchPan = touches.length === 1
      ? { clientX: touches[0].clientX, clientY: touches[0].clientY, x: stage.x(), y: stage.y() }
      : null;
  });

  // ---------- Kontextmenü (Rechtsklick oder langes Drücken auf ein Element) ----------

  const menu = $('context-menu');
  const actions = {
    'flip-arrows': flipArrows,
    text: () => editText(textElement()),
    delete: deleteSelection
  };

  function openMenu(element, clientX, clientY) {
    if (!selection.includes(element)) selectElement(element, false);
    menu.querySelector('[data-action="flip-arrows"]').disabled = arrowsInSelection().length === 0;
    menu.querySelector('[data-action="text"]').hidden = !textElement();
    menu.hidden = false;
    menu.style.left = Math.min(clientX, window.innerWidth - menu.offsetWidth - 4) + 'px';
    menu.style.top = Math.min(clientY, window.innerHeight - menu.offsetHeight - 4) + 'px';
  }

  function closeMenu() {
    menu.hidden = true;
  }

  menu.addEventListener('click', (e) => {
    const action = actions[e.target.dataset.action];
    if (!action) return;
    closeMenu();
    action();
  });

  menu.addEventListener('contextmenu', (e) => e.preventDefault());
  window.addEventListener('pointerdown', (e) => {
    if (!menu.contains(e.target)) closeMenu();
  }, true);
  window.addEventListener('blur', closeMenu);
  stage.on('wheel', closeMenu);

  // ---------- Drag-and-Drop aus der Toolbar ----------

  function buildPalette() {
    const sections = new Map();           // Kategorie -> Liste in der Toolbar
    Object.values(KP.elements).forEach((def) => {
      if (def.hidden) return;             // nur als Teil einer Figur verwendet
      if (!sections.has(def.category)) {
        const heading = document.createElement('h2');
        heading.textContent = def.category;
        const list = document.createElement('div');
        list.className = 'palette';
        $('palette').append(heading, list);
        sections.set(def.category, list);
      }

      const item = document.createElement('div');
      item.className = 'palette-item';
      item.title = def.hint || def.label;

      const img = new Image();
      img.src = KP.renderPreview(def.id, 44);
      img.alt = '';
      img.draggable = false;

      const text = document.createElement('span');
      text.textContent = def.label;

      item.append(img, text);

      // Anzahl der Teile (Schweizer Slalom) direkt am Element einstellen
      if (def.count) {
        const input = document.createElement('input');
        input.type = 'number';
        input.min = def.count.min;
        input.max = def.count.max;
        input.value = def.count.value;
        input.title = def.count.label;
        input.setAttribute('aria-label', def.label + ': ' + def.count.label);
        input.addEventListener('change', () => {
          const value = Math.round(Number(input.value));
          if (Number.isFinite(value)) def.count.value = clamp(value, def.count.min, def.count.max);
          input.value = def.count.value;
          img.src = KP.renderPreview(def.id, 44);
        });
        const row = document.createElement('label');
        row.className = 'palette-count';
        row.append(def.count.label, input);
        item.append(row);
      }

      enablePaletteDrag(item, def, img);
      sections.get(def.category).appendChild(item);
    });
  }

  // Bildschirmpunkt (relativ zur Arbeitsfläche) in Meter
  const toWorld = (x, y) => ({
    x: (x - stage.x()) / stage.scaleX(),
    y: (y - stage.y()) / stage.scaleX()
  });

  // Ziehen mit Maus, Finger oder Stift auf die Arbeitsfläche. Kurzes Antippen
  // legt das Element in die Mitte der Ansicht. Scrollt der Browser stattdessen
  // die Toolbar, meldet er pointercancel und es passiert nichts.
  function enablePaletteDrag(item, def, img) {
    item.addEventListener('pointerdown', (down) => {
      if (down.button !== 0 || down.target.closest('.palette-count')) return;
      let ghost = null;

      const move = (e) => {
        if (e.pointerId !== down.pointerId) return;
        if (!ghost) {
          if (Math.hypot(e.clientX - down.clientX, e.clientY - down.clientY) < 6) return;
          ghost = img.cloneNode();
          ghost.className = 'drag-ghost';
          document.body.appendChild(ghost);
        }
        ghost.style.left = e.clientX + 'px';
        ghost.style.top = e.clientY + 'px';
      };

      const end = (e) => {
        if (e.pointerId !== down.pointerId) return;
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', end);
        window.removeEventListener('pointercancel', end);
        if (ghost) ghost.remove();
        if (e.type === 'pointercancel') return;
        const rect = container.getBoundingClientRect();
        const inside = e.clientX >= rect.left && e.clientX <= rect.right &&
          e.clientY >= rect.top && e.clientY <= rect.bottom;
        if (ghost && inside) {
          addElement(def.id, snapPoint(toWorld(e.clientX - rect.left, e.clientY - rect.top)));
        } else if (!ghost) {
          addElement(def.id, snapPoint(toWorld(stage.width() / 2, stage.height() / 2)));
        }
      };

      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', end);
      window.addEventListener('pointercancel', end);
    });
  }

  // ---------- Tastatur ----------

  const isFormField = (el) =>
    el instanceof HTMLInputElement || el instanceof HTMLSelectElement;

  window.addEventListener('keydown', (e) => {
    if (isFormField(e.target) || document.querySelector('dialog[open]')) return;
    const ctrl = e.ctrlKey || e.metaKey;
    if (e.code === 'Space') {
      e.preventDefault();
      setPanMode(true);
    } else if (ctrl && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      stepHistory(e.shiftKey ? 1 : -1);
    } else if (ctrl && e.key.toLowerCase() === 'y') {
      e.preventDefault();
      stepHistory(1);
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault();
      deleteSelection();
    } else if (e.key === 'Escape') {
      closeMenu();
      scope = [];
      setSelection([]);
    } else if (e.key.toLowerCase() === 'r' && !ctrl) {
      rotateSelection(e.shiftKey ? -ROTATE_STEP : ROTATE_STEP);
    } else if (e.key.toLowerCase() === 'm' && !ctrl) {
      mirrorSelection();
    } else if (e.key.toLowerCase() === 'a' && ctrl) {
      e.preventDefault();
      setSelection(allElements());
    }
  });

  window.addEventListener('keyup', (e) => {
    if (e.code !== 'Space') return;
    if (!isFormField(e.target)) e.preventDefault();   // kein Klick auf fokussierte Buttons
    setPanMode(false);
  });

  window.addEventListener('blur', () => setPanMode(false));

  // ---------- Menü- und Statusleiste ----------

  const meters = (v) =>
    v.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' m';

  function updateUi() {
    ['btn-rotate-left', 'btn-rotate-right', 'btn-mirror', 'btn-delete'].forEach((id) => {
      $(id).disabled = selection.length === 0;
    });
    $('btn-undo').disabled = history.index <= 0;
    $('btn-redo').disabled = history.index >= history.stack.length - 1;
    document.title = (isDirty() ? '• ' : '') + TITLE;

    let text = 'Keine Auswahl';
    if (selection.length === 1) {
      const n = selection[0];
      const angle = Math.round(((n.rotation() % 360) + 360) % 360) % 360;
      const def = defOf(n);
      const size = n.getAttr('boxSize');
      text = def.label +
        ' · x: ' + meters(n.x()) + ' · y: ' + meters(n.y()) + ' · ' + angle + '°';
      if (size) {
        text += def.resize === 'both'
          ? ' · ' + meters(size.width) + ' × ' + meters(size.height)
          : ' · Länge: ' + meters(size.width);
      }
    } else if (selection.length > 1) {
      text = selection.length + ' Elemente ausgewählt';
    }
    $('status-selection').textContent = text;

    const count = allElements().length;
    $('status-count').textContent = count + (count === 1 ? ' Element' : ' Elemente');
  }

  stage.on('mousemove', () => {
    const p = stage.getRelativePointerPosition();
    $('status-pos').textContent = 'x: ' + meters(p.x) + '   y: ' + meters(p.y);
  });
  stage.on('mouseleave', () => {
    $('status-pos').textContent = 'x: –   y: –';
  });

  $('btn-undo').addEventListener('click', () => stepHistory(-1));
  $('btn-redo').addEventListener('click', () => stepHistory(1));
  $('btn-rotate-left').addEventListener('click', () => rotateSelection(-ROTATE_STEP));
  $('btn-rotate-right').addEventListener('click', () => rotateSelection(ROTATE_STEP));
  $('btn-mirror').addEventListener('click', mirrorSelection);
  $('btn-delete').addEventListener('click', deleteSelection);
  $('btn-zoom-in').addEventListener('click', () => zoomAtCenter(1.25));
  $('btn-zoom-out').addEventListener('click', () => zoomAtCenter(1 / 1.25));
  $('btn-fit').addEventListener('click', fitView);

  $('btn-help').addEventListener('click', () => $('help-dialog').showModal());


  // Fenster (Hilfe, App): ein Klick daneben schließt sie.
  document.querySelectorAll('dialog').forEach((dialog) => {
    dialog.addEventListener('click', (e) => {
      if (e.target === dialog) dialog.close();
    });
  });

  $('snap-step').addEventListener('change', (e) => {
    snapStep = Number(e.target.value);
  });
  $('guides').addEventListener('change', (e) => {
    guidesEnabled = e.target.checked;
  });

  function onFieldSizeChange() {
    const read = (input, fallback) => {
      const value = Math.round(Number(input.value));
      const size = Number.isFinite(value) && value > 0
        ? clamp(value, Number(input.min), Number(input.max))
        : fallback;
      input.value = size;
      return size;
    };
    field.width = read($('field-width'), field.width);
    field.height = read($('field-height'), field.height);
    fitView();
    commit();
  }
  $('field-width').addEventListener('change', onFieldSizeChange);
  $('field-height').addEventListener('change', onFieldSizeChange);

  // Wirkt auf Figuren, die danach platziert werden.
  $('track-width').addEventListener('change', (e) => {
    const input = e.target;
    const value = Number(input.value);
    if (Number.isFinite(value) && value > 0) {
      KP.settings.trackWidth = clamp(value, Number(input.min), Number(input.max));
    }
    input.value = KP.settings.trackWidth.toFixed(2);
    commit();
  });

  new ResizeObserver(() => {
    stage.size({ width: container.clientWidth, height: container.clientHeight });
  }).observe(container);

  // ---------- Start ----------

  buildPalette();
  fitView();
  commit();
  markSaved();

  KP.editor = {
    stage, elementLayer, field, addElement, fitView, renderPlan,
    getState, loadState, isDirty, markSaved, notify
  };
})(window.KP);
