/*
 * Element-Katalog. Jedes Element ist eine Konva.Group in Metern, deren
 * Ursprung der Drehpunkt ist. Die Darstellung folgt den Skizzen der
 * Rahmenausschreibung: stehende Pylone = graues Quadrat, liegende Pylone =
 * graues Dreieck.
 *
 * Ein Preset der Toolbar kann aus mehreren Elementen bestehen (parts): die
 * Pylonen der Figur, ihre Fahrtrichtungspfeile, einzelne Gassen ... Diese
 * Teile bleiben einzeln verschieb- und löschbar.
 */
(function (KP) {
  'use strict';

  const R = KP.RULES;
  const F = R.pylon.foot;
  const INK = '#1a1a1a';
  const PYLON_STYLE = {
    fill: '#c4c4c4', stroke: '#2f2f2f', strokeWidth: 0.03,
    hitStrokeWidth: 0.5      // vergrößert nur die Trefferfläche
  };
  const LINE_WIDTH = 0.05;
  const ARROW_STYLE = {
    stroke: INK, fill: INK, strokeWidth: LINE_WIDTH,
    pointerLength: 0.45, pointerWidth: 0.35, hitStrokeWidth: 0.6
  };
  const ARROW_HEIGHT = 0.4;  // Rahmenhöhe eines geraden Pfeils
  // Pfeile der Figuren stehen außerhalb, mittig vor den Ein- und Ausfahrten.
  const ARROW_GAP = 0.3;
  const ARROW_LENGTH = 1.5;
  // Unsichtbare Grifffläche um die Pylonen einer Figur, damit man sie nicht
  // genau an einer Pylone greifen muss.
  const GRIP_PADDING = F / 2 + 0.25;
  // Text wird in Zentimetern gesetzt und verkleinert, damit die Schriftmessung
  // des Browsers nicht mit Schriftgrößen unter 1 px arbeiten muss.
  const TEXT_SCALE = 0.01;
  // Mittenabstand stehende–liegende Pylone: zwischen Fuß und Spitze liegt
  // eine Pylonenhöhe.
  const MARKER_OFFSET = F / 2 + R.pylon.height * 1.5;

  const pt = (x, y) => ({ x, y });
  const deg = (rad) => (rad * 180) / Math.PI;
  // Mittenabstand zweier Pylonen bei lichtem Abstand gap
  const pitch = (gap) => gap + F;

  // Maße, die von der eingestellten Spurbreite abhängen
  function dims() {
    const lane = KP.settings.trackWidth + R.laneExtra;    // lichte Fahrspurbreite
    return { lane, D: lane + F, p: pitch(R.figurePylonGap) };
  }

  // ---------- Katalog ----------

  KP.elements = {};

  KP.registerElement = function (def) {
    KP.elements[def.id] = def;
  };

  // options: Breite/Höhe, Spiegelung, Text – je nach Element
  KP.createElement = function (id, options) {
    const node = KP.elements[id].build(options || {});
    node.name('element');
    node.setAttr('elementType', id);
    node.setAttr('options', options || {});
    node.draggable(true);
    return node;
  };

  // Teile, aus denen ein Preset beim Ablegen besteht (relativ zum Ablagepunkt).
  KP.presetParts = function (id) {
    const def = KP.elements[id];
    return def.parts ? def.parts() : [{ id, x: 0, y: 0 }];
  };

  // Vorschaubild für die Toolbar, direkt aus der echten Zeichnung erzeugt.
  KP.renderPreview = function (id, sizePx) {
    const node = new Konva.Group();
    KP.presetParts(id).forEach((part) => {
      const child = KP.elements[part.id].build(part.options || {});
      child.position({ x: part.x, y: part.y });
      child.rotation(part.rotation || 0);
      node.add(child);
    });
    node.find('.note').forEach((n) => n.hide());
    const box = node.getClientRect();
    const scale = Math.min(70, (sizePx * 0.84) / Math.max(box.width, box.height));
    // Bei großen Figuren wären maßstäbliche Pylonen unsichtbar klein.
    const grow = Math.max(1, 4 / (F * scale));
    node.find('.pylon').forEach((n) => n.scale({ x: grow, y: grow }));
    node.scale({ x: scale, y: scale });
    node.position({
      x: sizePx / 2 - (box.x + box.width / 2) * scale,
      y: sizePx / 2 - (box.y + box.height / 2) * scale
    });
    return node.toDataURL({ x: 0, y: 0, width: sizePx, height: sizePx, pixelRatio: 2 });
  };

  // ---------- Zeichenbausteine ----------

  function standingShape(x, y, rotation) {
    return new Konva.Rect(Object.assign({
      name: 'pylon', x, y, rotation: rotation || 0,
      width: F, height: F, offsetX: F / 2, offsetY: F / 2
    }, PYLON_STYLE));
  }

  // 50 cm lang (Pylonenhöhe), die Spitze zeigt bei 0° nach rechts.
  function lyingShape(x, y, rotation) {
    const h = R.pylon.height / 2;
    return new Konva.Line(Object.assign({
      name: 'pylon', x, y, rotation: rotation || 0,
      points: [-h, -F / 2, h, 0, -h, F / 2], closed: true
    }, PYLON_STYLE));
  }

  // Beschriftungskästchen wie „Haltelinie“ im Regelwerk, um (x, y) zentriert
  function textBox(text, x, y) {
    const label = new Konva.Label({ name: 'note', x, y, scaleX: TEXT_SCALE, scaleY: TEXT_SCALE });
    label.add(new Konva.Tag({ fill: '#ffffff', stroke: INK, strokeWidth: 3 }));
    label.add(new Konva.Text({
      text, fontSize: 45, fontFamily: 'Verdana, Arial, sans-serif', padding: 12, fill: INK
    }));
    label.offset({ x: label.width() / 2, y: label.height() / 2 });
    return label;
  }

  // Punkte von a bis b in gleichen Abständen möglichst nahe am Sollabstand.
  function between(a, b, spacing) {
    const n = Math.max(1, Math.round(Math.hypot(b.x - a.x, b.y - a.y) / spacing));
    const out = [];
    for (let i = 0; i <= n; i++) {
      out.push(pt(a.x + ((b.x - a.x) * i) / n, a.y + ((b.y - a.y) * i) / n));
    }
    return out;
  }

  // Pylonenpositionen entlang eines Linienzugs; auf jedem Eckpunkt steht eine.
  function alongPath(points, spacing) {
    const out = [points[0]];
    for (let i = 1; i < points.length; i++) {
      out.push(...between(points[i - 1], points[i], spacing).slice(1));
    }
    return out;
  }

  // Positionen auf einem Kreisbogen von a0 bis a1 (Bogenmaß), beide Enden inklusive.
  function alongArc(cx, cy, r, a0, a1, spacing) {
    const n = Math.max(1, Math.round((Math.abs(a1 - a0) * r) / spacing));
    const out = [];
    for (let i = 0; i <= n; i++) {
      const a = a0 + ((a1 - a0) * i) / n;
      out.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a), angle: a });
    }
    return out;
  }

  // Verschiebt einen Linienzug seitlich um d, Ecken auf Gehrung.
  function offsetPath(points, d) {
    const normals = [];
    for (let i = 1; i < points.length; i++) {
      const dx = points[i].x - points[i - 1].x;
      const dy = points[i].y - points[i - 1].y;
      const len = Math.hypot(dx, dy);
      normals.push(pt(dy / len, -dx / len));
    }
    return points.map((p, i) => {
      const a = normals[Math.max(0, i - 1)];
      const b = normals[Math.min(normals.length - 1, i)];
      const mx = a.x + b.x;
      const my = a.y + b.y;
      const k = d / (mx * a.x + my * a.y);
      return pt(p.x + mx * k, p.y + my * k);
    });
  }

  // Rundet die Ecken eines Linienzugs mit Kreisbögen aus (Radius in Metern,
  // bei kurzen Schenkeln entsprechend kleiner). Ergebnis: dichte Punktfolge.
  function roundPath(points, radius) {
    const out = [];
    const push = (p) => {
      const last = out[out.length - 1];
      if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 1e-6) out.push(p);
    };
    push(points[0]);
    for (let i = 1; i < points.length - 1; i++) {
      const corner = points[i];
      const toPrev = pt(points[i - 1].x - corner.x, points[i - 1].y - corner.y);
      const toNext = pt(points[i + 1].x - corner.x, points[i + 1].y - corner.y);
      const lenPrev = Math.hypot(toPrev.x, toPrev.y);
      const lenNext = Math.hypot(toNext.x, toNext.y);
      const a = pt(toPrev.x / lenPrev, toPrev.y / lenPrev);
      const b = pt(toNext.x / lenNext, toNext.y / lenNext);
      const inner = Math.acos(Math.max(-1, Math.min(1, a.x * b.x + a.y * b.y)));
      if (!radius || inner > Math.PI - 0.01) {
        push(corner);
        continue;
      }
      // Benachbarte Ecken teilen sich einen Schenkel je zur Hälfte.
      const tangent = Math.min(
        radius / Math.tan(inner / 2),
        i === 1 ? lenPrev : lenPrev / 2,
        i === points.length - 2 ? lenNext : lenNext / 2
      );
      const r = tangent * Math.tan(inner / 2);
      const bisector = Math.hypot(a.x + b.x, a.y + b.y);
      const center = pt(
        corner.x + ((a.x + b.x) / bisector) * (r / Math.sin(inner / 2)),
        corner.y + ((a.y + b.y) / bisector) * (r / Math.sin(inner / 2))
      );
      const from = Math.atan2(corner.y + a.y * tangent - center.y, corner.x + a.x * tangent - center.x);
      let sweep = Math.atan2(corner.y + b.y * tangent - center.y, corner.x + b.x * tangent - center.x) - from;
      if (sweep > Math.PI) sweep -= 2 * Math.PI;
      if (sweep < -Math.PI) sweep += 2 * Math.PI;
      const steps = Math.max(2, Math.ceil(Math.abs(sweep) / (Math.PI / 18)));
      for (let k = 0; k <= steps; k++) {
        const angle = from + (sweep * k) / steps;
        push(pt(center.x + r * Math.cos(angle), center.y + r * Math.sin(angle)));
      }
    }
    push(points[points.length - 1]);
    return out;
  }

  // Führt eine Zeichenfunktion aus. Ergebnis: die Gruppe mit den Pylonen und
  // die Zusatzteile (Pfeile, Nummern), die eigene Elemente werden.
  function runFigure(draw, mirrored) {
    const group = new Konva.Group();
    const placed = new Set();
    const box = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
    const extras = [];
    let origin = null;
    let autoGrip = true;
    const mx = (x) => (mirrored ? -x : x);

    const place = (shape) => {
      const key = Math.round(shape.x() * 1000) + '/' + Math.round(shape.y() * 1000);
      if (placed.has(key)) return;            // gemeinsame Eckpylone nur einmal setzen
      placed.add(key);
      box.x0 = Math.min(box.x0, shape.x());
      box.y0 = Math.min(box.y0, shape.y());
      box.x1 = Math.max(box.x1, shape.x());
      box.y1 = Math.max(box.y1, shape.y());
      group.add(shape);
    };

    const fig = {
      standing: (x, y, rotation) => {
        place(standingShape(mx(x), y, mirrored ? -(rotation || 0) : rotation));
      },
      lying: (x, y, rotation) => {
        place(lyingShape(mx(x), y, mirrored ? 180 - (rotation || 0) : rotation));
      },
      wall: (points, spacing) => {
        alongPath(points, spacing).forEach((p) => fig.standing(p.x, p.y));
      },
      line: (points) => {
        group.add(new Konva.Line({
          points: points.map((v, i) => (i % 2 ? v : mx(v))),
          stroke: INK, strokeWidth: LINE_WIDTH, hitStrokeWidth: 0.6
        }));
      },
      // Beschriftungskästchen bei (x, y) mit Pfeil auf (tx, ty) – ein eigenes
      // Element, damit es sich verschieben, umbenennen und löschen lässt
      callout: (text, x, y, tx, ty) => {
        extras.push({ id: 'beschriftung', x, y, options: { text, tx: tx - x, ty: ty - y } });
      },
      // Drehpunkt festlegen (sonst: Mitte der Pylonen)
      origin: (x, y) => { origin = pt(mx(x), y); },
      // Runde Grifffläche um den Ursprung statt des Rechtecks (Kreisel)
      roundGrip: (radius) => {
        autoGrip = false;
        const grip = new Konva.Circle({ name: 'grip', radius, fill: 'transparent' });
        group.add(grip);
        grip.moveToBottom();
      },
      // Fahrtrichtung: gerader Pfeil von (x1, y1) nach (x2, y2)
      direction: (x1, y1, x2, y2) => {
        extras.push({
          id: 'pfeil', x: (x1 + x2) / 2, y: (y1 + y2) / 2,
          rotation: deg(Math.atan2(y2 - y1, x2 - x1)),
          options: { width: Math.hypot(x2 - x1, y2 - y1) }
        });
      },
      // Fahrtrichtung entlang eines Wegs durch die Punkte, Ecken ausgerundet.
      // Der Weg wird auf seinen Rahmen normiert (-0,5 … 0,5).
      route: (points, radius) => {
        const path = roundPath(points, radius);
        const xs = path.map((q) => q.x);
        const ys = path.map((q) => q.y);
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
        const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
        const width = Math.max(Math.max(...xs) - Math.min(...xs), ARROW_HEIGHT);
        const height = Math.max(Math.max(...ys) - Math.min(...ys), ARROW_HEIGHT);
        const norm = (v) => Math.round(v * 1e4) / 1e4;
        extras.push({
          id: 'pfeil-weg', x: cx, y: cy,
          options: { width, height, path: path.map((q) => [norm((q.x - cx) / width), norm((q.y - cy) / height)]) }
        });
      },
      // Gerader Pfeil vor einer Öffnung bei (x, y): fährt in Richtung (dx, dy) hinein
      enter: (x, y, dx, dy) => {
        const far = ARROW_GAP + ARROW_LENGTH;
        fig.direction(x - dx * far, y - dy * far, x - dx * ARROW_GAP, y - dy * ARROW_GAP);
      },
      // Gerader Pfeil hinter einer Öffnung bei (x, y): fährt in Richtung (dx, dy) hinaus
      leave: (x, y, dx, dy) => {
        const far = ARROW_GAP + ARROW_LENGTH;
        fig.direction(x + dx * ARROW_GAP, y + dy * ARROW_GAP, x + dx * far, y + dy * far);
      },
      // Fahrtrichtung: Bogenpfeil ('pfeil-kurve' 90°, 'pfeil-wende' 180°) um (cx, cy)
      turn: (id, cx, cy, width, height, rotation, mirror) => {
        extras.push({ id, x: cx, y: cy, rotation: rotation || 0, options: { width, height, mirror } });
      },
      number: (text, x, y) => {
        extras.push({ id: 'nummer', x, y, options: { text } });
      }
    };

    draw(fig, dims());

    const o = origin || pt((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2);
    if (autoGrip) {
      const grip = new Konva.Rect({
        name: 'grip', fill: 'transparent',
        x: box.x0 - GRIP_PADDING, y: box.y0 - GRIP_PADDING,
        width: box.x1 - box.x0 + 2 * GRIP_PADDING, height: box.y1 - box.y0 + 2 * GRIP_PADDING
      });
      group.add(grip);
      grip.moveToBottom();
    }
    group.offset(o);
    return {
      group,
      extras: extras.map((e) => Object.assign({}, e, { x: e.x - o.x, y: e.y - o.y }))
    };
  }

  // Figur aus Pylonen; ihre Pfeile werden beim Ablegen eigene Elemente.
  function register(category, id, label, draw, extra) {
    KP.registerElement(Object.assign({
      id, label, category,
      build: (options) => runFigure(draw, Boolean(options.mirror)).group,
      parts: () => [{ id, x: 0, y: 0 }].concat(runFigure(draw, false).extras)
    }, extra));
  }

  // Preset, das nur aus selbständigen Teilen besteht (z. B. die Gassen der Z-Gasse).
  function registerSet(category, id, label, layout, extra) {
    KP.registerElement(Object.assign({
      id, label, category,
      parts() {
        const parts = layout(dims(), this);
        const xs = parts.map((p) => p.x);
        const ys = parts.map((p) => p.y);
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
        const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
        return parts.map((p) => Object.assign({}, p, { x: p.x - cx, y: p.y - cy }));
      }
    }, extra));
  }

  // ---------- Elemente mit einstellbarer Größe ----------

  // layout(shape, size, options) setzt die Geometrie; die Größe wird gesetzt statt
  // skaliert, damit Linienstärken und Pfeilspitzen gleich bleiben.
  function registerSized(def, makeShape, layout) {
    KP.registerElement(Object.assign(def, {
      layout,
      build(options) {
        const group = new Konva.Group();
        const size = {
          width: options.width || def.size.width,
          height: options.height || def.size.height
        };
        group.setAttr('boxSize', size);
        const shape = makeShape(group);
        shape.name('box');
        group.add(shape);
        layout(shape, size, options);
        return group;
      }
    }));
  }

  KP.setElementSize = function (node, width, height) {
    const size = { width, height };
    node.setAttr('boxSize', size);
    KP.elements[node.getAttr('elementType')]
      .layout(node.findOne('.box'), size, node.getAttr('options'));
  };

  const rectLayout = (rect, size) => {
    rect.setAttrs({ x: -size.width / 2, y: -size.height / 2, width: size.width, height: size.height });
  };

  // Pfeil, dessen Auswahlrahmen genau dem eingestellten Maß entspricht
  // (ohne die überstehende Pfeilspitze).
  function arrowShape(group, tension) {
    const arrow = new Konva.Arrow(Object.assign({ points: [0, 0, 0, 0], tension }, ARROW_STYLE));
    arrow.getSelfRect = () => {
      const size = group.getAttr('boxSize');
      return { x: -size.width / 2, y: -size.height / 2, width: size.width, height: size.height };
    };
    return arrow;
  }

  // Punkte auf einem Ellipsenbogen um (cx, cy), Winkel in Grad.
  // options.mirror spiegelt den Bogen, options.reverse kehrt die Fahrtrichtung um.
  function arcPoints(cx, cy, rx, ry, from, to, options) {
    const points = [];
    for (let a = from; a <= to; a += 22.5) {
      const x = cx + rx * Math.cos((a * Math.PI) / 180);
      points.push([options.mirror ? -x : x, cy + ry * Math.sin((a * Math.PI) / 180)]);
    }
    if (options.reverse) points.reverse();
    return [].concat(...points);
  }

  // ---------- Basis-Elemente ----------

  register('Basis-Elemente', 'pylon-standing', 'Pylone stehend', (fig) => fig.standing(0, 0));
  register('Basis-Elemente', 'pylon-lying', 'Pylone liegend', (fig) => fig.lying(0, 0));

  // ---------- Fahrtrichtung ----------

  registerSized({
    id: 'pfeil', label: 'Pfeil gerade', category: 'Fahrtrichtung',
    hint: 'Fahrtrichtung. Länge über die Griffe ändern. Rechtsklick > „Pfeile spiegeln“ kehrt die Richtung um.',
    resize: 'length', arrow: true, size: { width: 3, height: ARROW_HEIGHT }
  }, (group) => arrowShape(group, 0), (arrow, size, options) => {
    const half = (Boolean(options.mirror) !== Boolean(options.reverse) ? -1 : 1) * size.width / 2;
    arrow.points([-half, 0, half, 0]);
  });

  // Von links unten nach oben, dann nach rechts (gespiegelt: nach links)
  registerSized({
    id: 'pfeil-kurve', label: 'Pfeil Kurve', category: 'Fahrtrichtung',
    hint: 'Fahrtrichtung in einer Kurve. Größe über die Griffe ändern. „Spiegeln“ biegt zur anderen Seite, Rechtsklick > „Pfeile spiegeln“ kehrt die Richtung um.',
    resize: 'both', arrow: true, size: { width: 2, height: 2 }
  }, (group) => arrowShape(group, 0.5), (arrow, size, options) => {
    arrow.points(arcPoints(size.width / 2, size.height / 2, size.width, size.height, 180, 270, options));
  });

  // Von links unten über oben nach rechts unten (gespiegelt: andersherum)
  registerSized({
    id: 'pfeil-wende', label: 'Pfeil Wende', category: 'Fahrtrichtung',
    hint: 'Fahrtrichtung bei einer Wende. Größe über die Griffe ändern. Rechtsklick > „Pfeile spiegeln“ kehrt die Richtung um.',
    resize: 'both', arrow: true, size: { width: 3, height: 1.5 }
  }, (group) => arrowShape(group, 0.5), (arrow, size, options) => {
    arrow.points(arcPoints(0, size.height / 2, size.width / 2, size.height, 180, 360, options));
  });

  // Pfeil entlang eines frei geformten Wegs – so kommen die Fahrtrichtungen der
  // Figuren. Der Weg wächst mit dem Rahmen mit.
  registerSized({
    id: 'pfeil-weg', label: 'Pfeil', category: 'Fahrtrichtung', hidden: true,
    resize: 'both', arrow: true, size: { width: 2, height: 2 }
  }, (group) => arrowShape(group, 0), (arrow, size, options) => {
    const path = options.path || [[-0.5, 0], [0.5, 0]];
    const points = path.map((q) => [(options.mirror ? -q[0] : q[0]) * size.width, q[1] * size.height]);
    if (options.reverse) points.reverse();
    arrow.points([].concat(...points));
  });

  // Nummernkästchen für die Reihenfolge (Brezel)
  KP.registerElement({
    id: 'nummer', label: 'Nummer', category: 'Fahrtrichtung', hidden: true, editableText: true,
    build(options) {
      const group = new Konva.Group();
      group.add(textBox(options.text || '1', 0, 0));
      return group;
    }
  });

  // Beschriftungskästchen mit Hinweispfeil, wie „Haltelinie“ im Regelwerk.
  // options.tx/ty: Ziel des Pfeils, gemessen von der Mitte des Kästchens
  KP.registerElement({
    id: 'beschriftung', label: 'Beschriftung', category: 'Start / Ziel', hidden: true, editableText: true,
    build(options) {
      const group = new Konva.Group();
      const label = textBox(options.text || 'Text', 0, 0);
      const tx = (options.mirror ? -1 : 1) * (options.tx || 0);
      const ty = options.ty || 0;
      if (tx || ty) {
        const w = label.width() * TEXT_SCALE;
        const h = label.height() * TEXT_SCALE;
        group.add(new Konva.Arrow({
          name: 'note',
          points: [(Math.sign(tx) * w) / 2, (Math.sign(ty) * h) / 2, tx, ty],
          stroke: INK, fill: INK, strokeWidth: 0.03,
          pointerLength: 0.3, pointerWidth: 0.22, hitStrokeWidth: 0.5
        }));
      }
      group.add(label);
      return group;
    }
  });

  // ---------- Gelände ----------

  // Rechteck mit Beschriftung in der Mitte (options.text). Die Schrift passt
  // sich der Fläche an: höchstens 70 % der Breite und die halbe Höhe.
  function areaLayout(rect, size, options) {
    rectLayout(rect, size);
    const group = rect.getParent();
    let label = group.findOne('.label');
    if (!label) {
      label = new Konva.Text({
        name: 'label', fontFamily: 'Verdana, Arial, sans-serif', fontStyle: 'bold', fill: INK,
        scaleX: TEXT_SCALE, scaleY: TEXT_SCALE, listening: false
      });
      group.add(label);
    }
    const text = (options.text || '').trim();
    label.visible(Boolean(text));
    if (!text) return;
    label.setAttrs({ text, fontSize: 100 });
    const widthPerMeter = label.width() * TEXT_SCALE;     // Textbreite bei 1 m Schrifthöhe
    const height = Math.max(0.3, Math.min((0.7 * size.width) / widthPerMeter, 0.5 * size.height));
    label.fontSize(height * 100);
    label.offset({ x: label.width() / 2, y: label.height() / 2 });
  }

  // Nicht befahrbare Fläche, z. B. Gebäude, Grünstreifen oder fehlende Platzecke
  registerSized({
    id: 'sperrflaeche', label: 'Sperrfläche', category: 'Gelände',
    hint: 'Nicht befahrbare Fläche, z. B. Gebäude. Größe über die Griffe ändern, Doppelklick zum Beschriften.',
    resize: 'both', background: true, editableText: true, size: { width: 6, height: 4 }
  }, () => new Konva.Rect({
    fill: 'rgba(120, 126, 134, 0.55)', stroke: '#5a6068', strokeWidth: 0.05
  }), areaLayout);

  // Grenze, die nicht überfahren werden darf, z. B. Bordstein oder Absperrung
  registerSized({
    id: 'sperrlinie', label: 'Sperrlinie', category: 'Gelände',
    hint: 'Linie, die nicht überfahren werden darf. Länge über die Griffe ändern.',
    resize: 'length', size: { width: 6, height: 0.15 }
  }, () => new Konva.Rect({ fill: INK, hitStrokeWidth: 0.6 }), rectLayout);

  // ---------- Start / Ziel ----------

  // Start- bzw. Ziellinie: geschlossene Linie zwischen zwei Pylonen (6.2 a).
  // Beschriftung und Richtungspfeil sind eigene Teile und lassen sich entfernen.
  const gateLine = (text) => (fig) => {
    const inner = R.finishLane.width / 2;
    const row = inner + F / 2;
    fig.standing(0, -row);
    fig.standing(0, row);
    fig.line([0, -inner, 0, inner]);
    fig.callout(text, 1.6, -row - 1.1, 0, -inner * 0.5);
    fig.direction(-1.8, 0, 1.8, 0);
  };

  register('Start / Ziel', 'start', 'Start', gateLine('Start'));
  register('Start / Ziel', 'ziel-linie', 'Ziel', gateLine('Ziel'));

  // Halteraum / Zielgasse wie in der Skizze: 2,50 m breit, 8–10 m lang,
  // Seitenlinien an der Innenkante der Pylonen, Haltelinie am Ende.
  register('Start / Ziel', 'ziel', 'Zielgasse', (fig) => {
    const p = pitch(R.finishLane.pylonGap);
    const inner = R.finishLane.width / 2;
    const row = inner + F / 2;
    const count = Math.ceil((R.finishLane.minLength - F) / p) + 1;   // Außenlänge ≥ 8 m
    const x0 = -F / 2;
    const x1 = (count - 1) * p + F / 2;
    for (let i = 0; i < count; i++) {
      fig.standing(i * p, -row);
      fig.standing(i * p, row);
    }
    fig.line([x0, -inner, x1, -inner, x1, inner, x0, inner]);
    fig.callout('Haltelinie', x1 + 1.9, -row - 1.1, x1, -0.1);
    fig.direction(x0, 0, x1 - 1.3, 0);
  });

  // ---------- Figuren ----------

  register('Figuren', 'tor', 'Pylonentor', (fig) => {
    const width = R.gate.preset + F;
    fig.standing(0, 0);
    fig.standing(width, 0);
    fig.direction(width / 2, 1.4, width / 2, -1.4);
  });

  // Vier Pylonen in einer Linie = zwei Tore, dazwischen eine liegende Pylone
  register('Figuren', 'wechseltor', 'Wechseltor', (fig) => {
    const gate = R.gate.preset + F;
    const gap = R.changeGate.preset + F;
    [0, gate, gate + gap, 2 * gate + gap].forEach((x) => fig.standing(x, 0));
    fig.lying(gate + gap / 2, 0, 180);
    const first = gate / 2;
    const second = gate + gap + gate / 2;
    fig.route([pt(first, -1.6), pt(first, 1.5), pt(second, 1.5), pt(second, -1.6)], 1.0);
  });

  // Einzelne stehende Pylone mit liegender Pylone, deren Spitze auf den Fuß
  // zeigt. Drehpunkt ist die stehende Pylone: um 180° gedreht wechselt die Seite.
  register('Figuren', 'slalom-pylone', 'Slalom-Pylone', (fig) => {
    fig.standing(0, 0);
    fig.lying(0, MARKER_OFFSET, -90);
    fig.origin(0, 0);
  }, { hidden: true });

  // Mehrere Aufgaben aus einzelnen Pylonen in einer Linie, wechselseitig zu
  // durchfahren. Jede Pylone ist mit ihrem Bogenpfeil ein eigenes Teil.
  registerSet('Figuren', 'schweizer-slalom', 'Schweizer Slalom', (d, def) => {
    const parts = [];
    for (let i = 0; i < def.count.value; i++) {
      const x = i * R.swissSlalom.preset;
      const flipped = i % 2 === 1;            // liegende Pylone oben, Bogen unten
      parts.push({ id: 'slalom-pylone', x, y: 0, rotation: flipped ? 180 : 0, group: 'p' + i });
      parts.push({
        id: 'pfeil-wende', x, y: flipped ? 0.45 : -0.45, rotation: flipped ? 180 : 0, group: 'p' + i,
        options: { width: 2.6, height: 0.9, mirror: flipped }
      });
    }
    return parts;
  }, { count: { label: 'Anzahl', min: 1, max: 20, value: 4 } });

  // Drei Pylonen im Dreieck, Fuß an Fuß
  register('Figuren', 'wende', 'Wende', (fig) => {
    fig.standing(-F / 2, F / 2);
    fig.standing(F / 2, F / 2);
    fig.standing(0, -F / 2);
    fig.turn('pfeil-wende', 0, 0, 2.4, 1.6);
  });

  // Gerade Spurgasse: beidseitig ohne Abstand, mindestens 3 Pylonen hintereinander
  register('Figuren', 'spurgasse', 'Spurgasse gerade', (fig, d) => {
    const width = Math.min(R.lane.max, Math.max(R.lane.min, d.lane)) + F;
    for (let i = 0; i < 5; i++) {
      fig.standing(i * F, 0);
      fig.standing(i * F, width);
    }
    fig.direction(-ARROW_LENGTH, width / 2, 4 * F + ARROW_LENGTH, width / 2);
  });

  // Je Seite 3 Pylonen gerade, 5 schräg, 3 gerade; die Gasse versetzt sich um eine Spurbreite.
  register('Figuren', 's-spurgasse', 'S-Spurgasse', (fig, d) => {
    const center = [pt(0, 0), pt(2 * d.p, 0), pt(8 * d.p, -d.D), pt(10 * d.p, -d.D)];
    fig.wall(offsetPath(center, d.D / 2), d.p);
    fig.wall(offsetPath(center, -d.D / 2), d.p);
    fig.route([pt(-ARROW_LENGTH, 0), center[1], center[2], pt(10 * d.p + ARROW_LENGTH, -d.D)], 2.0);
  });

  // Einzelne Gasse der Z-Gasse: zwei Reihen mit je 5 Pylonen
  register('Figuren', 'z-gasse-teil', 'Z-Gasse (einzelne Gasse)', (fig, d) => {
    fig.wall([pt(0, 0), pt(0, 4 * d.p)], d.p);
    fig.wall([pt(d.D, 0), pt(d.D, 4 * d.p)], d.p);
  }, { hidden: true });

  // Drei Gassen, die im Wechsel durchfahren werden. Jede Gasse ist ein eigenes
  // Element, damit sie parallel oder versetzt aufgebaut werden kann.
  registerSet('Figuren', 'z-gasse', 'Z-Gasse', (d) => {
    const next = d.D + R.zLane.preset + F;      // Mittenabstand zweier Gassen
    const length = 4 * d.p;
    const bend = 1.2;                           // Höhe der Wendepfeile
    const parts = [0, 1, 2].map((i) => ({ id: 'z-gasse-teil', x: i * next, y: 0 }));
    parts.push({
      id: 'pfeil-wende', x: next / 2, y: -length / 2 - ARROW_GAP - bend / 2,
      options: { width: next, height: bend }
    });
    parts.push({
      id: 'pfeil-wende', x: 1.5 * next, y: length / 2 + ARROW_GAP + bend / 2, rotation: 180,
      options: { width: next, height: bend, mirror: true }
    });
    const outside = length / 2 + ARROW_GAP + ARROW_LENGTH / 2;
    parts.push({ id: 'pfeil', x: 0, y: outside, rotation: -90, options: { width: ARROW_LENGTH } });
    parts.push({ id: 'pfeil', x: 2 * next, y: -outside, rotation: -90, options: { width: ARROW_LENGTH } });
    return parts;
  });

  // Z: obere Gasse, schräge Gasse, untere Gasse. In der Verlängerung der
  // schrägen Gasse steht an beiden Ecken eine Wende aus drei Pylonen, um die
  // herum gewendet wird. Die Figur ist punktsymmetrisch.
  register('Figuren', 'z-figur', 'Z-Figur', (fig, d) => {
    const angle = (55 * Math.PI) / 180;        // Neigung der schrägen Gasse
    const slope = Math.tan(angle);
    const left = pt(5 * d.p, d.D);             // hier knickt die untere Reihe in die Schräge ab
    const right = pt(left.x + d.D / Math.sin(angle), d.D);
    const down = (from, length) =>
      pt(from.x - Math.cos(angle) * length, from.y + Math.sin(angle) * length);
    const rightEnd = down(right, 6 * d.p);
    const center = pt((left.x + rightEnd.x) / 2, (left.y + rightEnd.y) / 2);
    const same = (q) => q;
    const flip = (q) => pt(2 * center.x - q.x, 2 * center.y - q.y);   // Punktspiegelung

    // Die Wende setzt die rechte schräge Wand auf Höhe der oberen Reihe fort.
    const turn = right.x + d.D / slope;
    const turnPylons = [pt(turn, 0), pt(turn + F, 0), pt(turn + F, -F)];
    [same, flip].forEach((place) => {
      fig.wall([pt(0, 0), pt(6 * d.p, 0)].map(place), d.p);
      fig.wall([pt(0, d.D), left, down(left, 6 * d.p)].map(place), d.p);
      turnPylons.map(place).forEach((q) => fig.standing(q.x, q.y));
    });

    // Oben durch, links herum um die Wende, schräg hinunter, rechts herum um
    // die zweite Wende und unten hinaus – alles auf den Gassenachsen.
    const lane = d.D / 2;
    const openingTop = pt((left.x + right.x) / 2, d.D);
    const openingBottom = flip(openingTop);
    const onAxis = (y) => pt(openingTop.x + (openingTop.y - y) / slope, y);
    const clear = 1.5 * F + 1.1;               // Abstand des Bogens von der Wende
    const loop = [pt(turn + clear, lane), pt(turn + clear, -clear), onAxis(-clear)];
    const exit = flip(pt(-ARROW_LENGTH, lane));
    fig.direction(-ARROW_LENGTH, lane, 6 * d.p + 0.5, lane);
    fig.route([pt(6 * d.p + 0.9, lane)].concat(loop, [openingBottom]), 1.0);
    fig.route([down(openingBottom, 0.4)].concat(loop.slice().reverse().map(flip), [exit]), 1.0);
  });

  // Stamm links, zwei Äste rechts. Die Innenreihen liegen in der Flucht der
  // Stammreihen, davor steht eine einzelne Pylone als Spitze.
  register('Figuren', 'ypsilon', 'Ypsilon', (fig, d) => {
    const x = (i) => i * d.p;
    [-1, 1].forEach((s) => {
      const inner = (s * d.D) / 2;
      const outer = s * 1.5 * d.D;
      fig.wall([pt(0, inner), pt(x(2), inner), pt(x(7), outer), pt(x(10), outer)], d.p);
      fig.wall([pt(x(8), inner), pt(x(10), inner)], d.p);
    });
    fig.standing(x(7), 0);
    // Oben hinein, am Stamm hinaus und außen wenden, zurück und unten hinaus
    fig.enter(x(10), -d.D, -1, 0);
    fig.route([pt(-ARROW_GAP, 0.4), pt(-2.1, 0.4), pt(-2.1, -0.4), pt(-ARROW_GAP, -0.4)], 0.4);
    fig.leave(x(10), d.D, 1, 0);
  });

  // Einfahrt oben rechts, Ausfahrt unten links
  register('Figuren', 'kasten', 'Kasten', (fig, d) => {
    const w = 2 * d.p + d.D;
    const h = 4 * d.p;
    fig.wall([pt(2 * d.p, 0), pt(0, 0), pt(0, h)], d.p);
    fig.wall([pt(w, 0), pt(w, h), pt(w - 2 * d.p, h)], d.p);
    fig.enter(w - d.D / 2, 0, 0, 1);
    fig.leave(d.D / 2, h, 0, 1);
  });

  // Einfahrt rechts oben, Ausfahrt unten links
  register('Figuren', 'kasten-90', 'Kasten 90°', (fig, d) => {
    const size = 2 * d.p + d.D;
    fig.wall([pt(size, 0), pt(0, 0), pt(0, size)], d.p);
    fig.wall([pt(size, d.D), pt(size, size), pt(size - 2 * d.p, size)], d.p);
    fig.enter(size, d.D / 2, -1, 0);
    fig.leave(d.D / 2, size, 0, 1);
  });

  // Zwei Gassen links, geschlossener Kasten in der Mitte, eine Gasse rechts
  register('Figuren', 'schneckenhaus', 'Schneckenhaus', (fig, d) => {
    const h = 4 * d.p;
    const boxWidth = Math.round(R.snailBox / d.p) * d.p;
    const columns = [0, d.D, 2 * d.D, 2 * d.D + boxWidth, 3 * d.D + boxWidth];
    columns.forEach((x) => fig.wall([pt(x, 0), pt(x, h)], d.p));
    fig.wall([pt(columns[2], 0), pt(columns[3], 0)], d.p);
    fig.wall([pt(columns[2], h), pt(columns[3], h)], d.p);

    // Außen hoch, oben herum, rechts runter, unten herum, innen hoch
    const lane1 = d.D / 2;
    const lane2 = 1.5 * d.D;
    const lane3 = columns[3] + d.D / 2;
    const top = -ARROW_GAP;
    const bottom = h + ARROW_GAP;
    fig.enter(lane1, h, 0, -1);
    fig.route([pt(lane1, top), pt(lane1, top - 2.0), pt(lane3, top - 2.0), pt(lane3, top)], 1.2);
    fig.route([pt(lane3, bottom), pt(lane3, bottom + 1.7), pt(lane2, bottom + 1.7), pt(lane2, bottom)], 1.2);
    fig.direction(lane2, top, lane2, top - 1.1);
  });

  // Zwei sich kreuzende Gassen, vier Winkel
  register('Figuren', 'kreuz', 'Kreuz', (fig, d) => {
    const c = d.D / 2;
    const arm = c + 2 * d.p;
    [-1, 1].forEach((sx) => [-1, 1].forEach((sy) => {
      fig.wall([pt(sx * arm, sy * c), pt(sx * c, sy * c), pt(sx * c, sy * arm)], d.p);
    }));
    // Von links gerade durch, außen in einer runden Schleife nach oben und
    // von dort durch die zweite Gasse nach unten hinaus.
    const a = arm + ARROW_GAP;
    fig.enter(-arm, 0, 1, 0);
    fig.route([pt(a, 0), pt(2 * a, 0), pt(2 * a, -2 * a), pt(0, -2 * a), pt(0, -a)], a);
    fig.leave(0, arm, 0, 1);
  });

  // Quergasse oben, in der Mitte zweigt eine Gasse nach unten ab. Die Mündung
  // ist über je eine schräg gestellte Pylone aufgeweitet.
  register('Figuren', 'brezel', 'Brezel', (fig, d) => {
    const mouth = d.D / 2 + 0.6;
    const half = mouth + 2 * d.p;
    const bottom = d.D + 4 * d.p;
    fig.wall([pt(-half, 0), pt(half, 0)], d.p);
    [-1, 1].forEach((s) => {
      fig.wall([
        pt(s * half, d.D), pt(s * mouth, d.D),
        pt((s * d.D) / 2, d.D + 2 * d.p), pt((s * d.D) / 2, bottom)
      ], d.p);
    });

    // 1: von links hinein und nach unten hinaus, 2: rechts außen herum und
    // von rechts wieder hinein, 3: links außen herum, 4: gerade durch und hinaus.
    const upper = 0.35 * d.D;                  // gerade Durchfahrt
    const lower = 0.65 * d.D;                  // Einfahrt der Schleifen
    const edge = half + ARROW_GAP;
    const exit = bottom + ARROW_GAP;
    const side = edge + 1.9;
    const below = exit + 1.9;
    fig.enter(-half, upper, 1, 0);
    fig.number('1', -edge - ARROW_LENGTH / 2, upper - 0.55);
    fig.route([pt(0, exit), pt(0, below), pt(side, below), pt(side, lower), pt(edge, lower)], 1.4);
    fig.number('2', side + 0.45, (below + lower) / 2);
    fig.route([pt(0, exit), pt(0, below), pt(-side, below), pt(-side, lower), pt(-edge, lower)], 1.4);
    fig.number('3', -side - 0.45, (below + lower) / 2);
    fig.leave(half, upper, 1, 0);
    fig.number('4', edge + ARROW_LENGTH / 2, upper - 0.55);
  });

  // Pfeil mittig durch ein Eck: von unten hinein, rechts hinaus. size = Außenmaß
  function corner(fig, lane, size, radius) {
    const far = size + ARROW_LENGTH;
    fig.route([pt(lane / 2, far), pt(lane / 2, lane / 2), pt(far, lane / 2)], radius);
  }

  // Außen rechtwinklig; innen je 2 Pylonen gerade, 2 schräg, 2 gerade
  register('Figuren', 'deutsches-eck', 'Deutsches Eck', (fig, d) => {
    const cut = 2 * d.p;                       // Schenkel der Abschrägung
    const size = d.D + cut + d.p;
    fig.wall([pt(size, 0), pt(0, 0), pt(0, size)], d.p);
    fig.wall([pt(d.D, size), pt(d.D, d.D + cut), pt(d.D + cut, d.D), pt(size, d.D)], d.p);
    corner(fig, d.D, size, 0.9);
  });

  // Winkel aus fünf Pylonen außen und einer Pylone innen
  register('Figuren', 'normales-eck', 'Normales Eck', (fig, d) => {
    fig.wall([pt(d.D, 0), pt(0, 0), pt(0, d.D)], d.D / 2);
    fig.standing(d.D, d.D);
    corner(fig, d.D, d.D, 0.6);
  });

  // Dritte Skizze im Regelwerk: äußere Ecke abgeschrägt, innen eine Pylone
  register('Figuren', 'eck-schraeg', 'Eck abgeschrägt', (fig, d) => {
    const cut = d.D - d.p;
    fig.wall([pt(0, d.D), pt(0, cut), pt(cut, 0), pt(d.D, 0)], d.p);
    fig.standing(d.D, d.D);
    corner(fig, d.D, d.D, 0.6);
  });

  // Innenkreis Ø 10 m, außen die Fahrspur. Links oben die Einfahrt A (3 m) mit
  // je einer liegenden Pylone außen daneben, darunter die Ausfahrt B.
  register('Figuren', 'kreisel', 'Kreisel', (fig, d) => {
    const spacing = pitch(R.roundabout.pylonGap);
    const ri = R.roundabout.innerDiameter / 2;
    const ro = ri + d.D;
    const onRing = (r, a) => fig.standing(r * Math.cos(a), r * Math.sin(a), deg(a));
    const opening = (clear) => 2 * Math.asin((clear + F) / (2 * ro));

    alongArc(0, 0, ri, 0, 2 * Math.PI, spacing).slice(1).forEach((p) => onRing(ri, p.angle));

    // Pylone an der Einfahrt; die liegende Pylone zeigt von außen auf ihren Fuß.
    const entryPylon = (a, away) => {
      const dir = a + away * 0.35;
      onRing(ro, a);
      fig.lying(
        ro * Math.cos(a) + MARKER_OFFSET * Math.cos(dir),
        ro * Math.sin(a) + MARKER_OFFSET * Math.sin(dir),
        deg(dir) + 180
      );
    };

    const step = spacing / ro;
    const entry = opening(R.roundabout.entry);
    const exit = opening(d.lane);
    const span = entry + 2 * step + exit;
    let a = Math.PI + span / 2;
    entryPylon(a, 1);
    a -= entry;
    entryPylon(a, -1);
    a -= step;
    onRing(ro, a);
    a -= step;
    onRing(ro, a);
    a -= exit;
    alongArc(0, 0, ro, a, a - (2 * Math.PI - span), spacing).slice(0, -1)
      .forEach((p) => onRing(ro, p.angle));

    // Einfahrt A hinein, Ausfahrt B hinaus (die Richtung im Kreisel ist frei)
    const radial = (angle, from, to) => fig.direction(
      from * Math.cos(angle), from * Math.sin(angle), to * Math.cos(angle), to * Math.sin(angle)
    );
    radial(Math.PI + span / 2 - entry / 2, ro + ARROW_GAP + ARROW_LENGTH, ro + ARROW_GAP);
    radial(a + exit / 2, ro + ARROW_GAP, ro + ARROW_GAP + ARROW_LENGTH);

    // Im Kreisel: drei Bogenpfeile mittig in der Fahrspur (oben, rechts, unten).
    // Von der Einfahrt aus gegen den Uhrzeigersinn, so ist der Kreisel bis zur
    // Ausfahrt einmal ganz umrundet.
    const lane = ri + d.D / 2;
    [1.5 * Math.PI, 0, 0.5 * Math.PI].forEach((at) => {
      fig.route(alongArc(0, 0, lane, at + Math.PI / 6, at - Math.PI / 6, 0.5));
    });

    fig.origin(0, 0);
    // Überall im Kreis greifbar, auch in der Mitte. Was im Kreisel platziert
    // wird, liegt als kleineres Element darüber und bleibt wählbar.
    fig.roundGrip(ro + GRIP_PADDING);
  });
})(window.KP);
