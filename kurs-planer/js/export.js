/*
 * PDF-Export: das ganze Blatt auf einer DIN-A4-Seite, damit der Streckenplan
 * am Veranstaltungsort ausgehängt werden kann (Rahmenausschreibung 6.2 h).
 *
 * Vor dem Speichern fragt ein Fenster nach dem Namen (Überschrift und
 * Dateiname) und ob Maße und Stand in der Kopfzeile stehen sollen. Die
 * Angaben gehören zum Plan und werden mit ihm gespeichert.
 */
(function (KP) {
  'use strict';

  const PAGE_MARGIN = 10;      // mm
  const HEADER_HEIGHT = 10;    // mm
  const IMAGE_PIXELS = 3000;   // längere Bildkante, rund 270 dpi auf A4

  const $ = (id) => document.getElementById(id);
  const dialog = $('pdf-dialog');

  // options: { title, size, date } – ohne Angabe gelten die des Plans
  KP.buildPdf = function (options) {
    const opts = options || KP.editor.pdfOptions();
    const plan = KP.editor.renderPlan(IMAGE_PIXELS);
    const state = KP.editor.getState();
    const meters = (value) => value.toLocaleString('de-DE');
    const pdf = new window.jspdf.jsPDF({
      orientation: plan.widthMeters >= plan.heightMeters ? 'landscape' : 'portrait',
      unit: 'mm',
      format: 'a4'
    });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();

    // Ohne Überschrift, Maße und Stand entfällt die Kopfzeile, das Bild wird größer.
    const header = opts.title || opts.size || opts.date ? HEADER_HEIGHT : 0;
    const mmPerMeter = Math.min(
      (pageWidth - 2 * PAGE_MARGIN) / plan.widthMeters,
      (pageHeight - 2 * PAGE_MARGIN - header) / plan.heightMeters
    );
    const width = plan.widthMeters * mmPerMeter;
    const height = plan.heightMeters * mmPerMeter;
    const left = (pageWidth - width) / 2;

    const info = [];
    if (opts.size) {
      info.push('Blatt ' + meters(state.field.width) + ' × ' + meters(state.field.height) + ' m');
      if (state.grid) info.push('1 Kästchen = 1 m');
      info.push('Maßstab ca. 1:' + Math.round(1000 / mmPerMeter));
    }
    if (opts.date) info.push('Stand ' + new Date().toLocaleDateString('de-DE'));

    if (opts.title) {
      pdf.setFontSize(14);
      pdf.text(opts.title, left, PAGE_MARGIN + 5);
    }
    if (info.length) {
      pdf.setFontSize(9);
      pdf.text(info.join('  ·  '), left + width, PAGE_MARGIN + 5, { align: 'right' });
    }
    pdf.addImage(plan.dataUrl, 'PNG', left, PAGE_MARGIN + header, width, height, undefined, 'FAST');
    return pdf;
  };

  // Dateiname aus dem Namen: ohne Zeichen, die Windows und macOS nicht erlauben
  function fileName(title) {
    const name = title.replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, ' ').trim().slice(0, 80);
    return (name || 'streckenplan') + '.pdf';
  }

  $('btn-export').addEventListener('click', () => {
    const opts = KP.editor.pdfOptions();
    $('pdf-title').value = opts.title;
    $('pdf-size').checked = opts.size;
    $('pdf-date').checked = opts.date;
    dialog.showModal();
    $('pdf-title').select();
  });

  $('pdf-cancel').addEventListener('click', () => dialog.close());

  // „PDF speichern“ ist der einzige Absende-Knopf, damit die Eingabetaste speichert.
  dialog.querySelector('form').addEventListener('submit', () => {
    const opts = {
      title: $('pdf-title').value.trim(),
      size: $('pdf-size').checked,
      date: $('pdf-date').checked
    };
    KP.editor.setPdfOptions(opts);
    KP.buildPdf(opts).save(fileName(opts.title));
  });
})(window.KP);
