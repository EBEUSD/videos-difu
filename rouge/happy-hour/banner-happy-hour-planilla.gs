/**
 * Receptor de eventos del banner Happy Hour.
 * Va pegado en: la planilla → Extensiones → Apps Script.
 * Cada evento del banner llega acá y se anota como una fila en la hoja "Eventos".
 * La hoja "Resumen" cuenta cuántas veces pasó cada cosa y cuántas personas distintas.
 */
const HOJA = 'Eventos';
const EVENTOS = ['banner_visto', 'raspado_iniciado', 'cupon_revelado', 'cupon_copiado', 'click_productos'];
const NOMBRES = ['Vieron el banner', 'Empezaron a raspar', 'Revelaron el cupón', 'Copiaron el cupón', 'Fueron a ver productos'];

function doGet(e) { return recibir(e); }
function doPost(e) { return recibir(e); }

function recibir(e) {
  const p = (e && e.parameter) || {};
  if (EVENTOS.indexOf(p.en) < 0) return ContentService.createTextOutput('ignorado');
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(8000);
    hoja().appendRow([
      new Date(), p.en, p.cid || '', p.estado || '', p.metodo || '', p.origen || '',
      p.copiado || '', p.segundos_raspando || '', p.cupon || '', p.dispositivo || '', p.dl || ''
    ]);
  } catch (err) {
    // si hay demasiados eventos a la vez y no consigue turno, se descarta ese evento
  } finally {
    try { lock.releaseLock(); } catch (x) { }
  }
  return ContentService.createTextOutput('ok');
}

function hoja() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(HOJA);
  if (!sh) {
    sh = ss.insertSheet(HOJA);
    sh.appendRow(['Fecha y hora', 'Evento', 'Visitante', 'Estado', 'Método', 'Origen del clic',
      'Copiado', 'Segundos raspando', 'Cupón', 'Dispositivo', 'Página']);
    sh.setFrozenRows(1);
    sh.getRange('A:A').setNumberFormat('dd/mm/yyyy hh:mm:ss');
    resumen(ss);
  }
  return sh;
}

/* Hoja con los totales: se arma sola la primera vez que llega un evento */
function resumen(ss) {
  let r = ss.getSheetByName('Resumen');
  if (r) return;
  r = ss.insertSheet('Resumen', 0);
  r.getRange('A1:E1').setValues([['Paso', 'Evento', 'Veces (total)', 'Personas (total)', 'Veces hoy']]).setFontWeight('bold');
  // separador de fórmulas según el idioma de la planilla: en español es ";" y en inglés ","
  const s = /^en/.test(ss.getSpreadsheetLocale()) ? ',' : ';';
  EVENTOS.forEach(function (ev, i) {
    const f = i + 2;
    r.getRange(f, 1, 1, 2).setValues([[NOMBRES[i], ev]]);
    r.getRange(f, 3).setFormula('=COUNTIF(Eventos!B:B' + s + 'B' + f + ')');
    r.getRange(f, 4).setFormula('=IFERROR(COUNTUNIQUEIFS(Eventos!C:C' + s + 'Eventos!B:B' + s + 'B' + f + ')' + s + '0)');
    r.getRange(f, 5).setFormula('=COUNTIFS(Eventos!B:B' + s + 'B' + f + s + 'Eventos!A:A' + s + '">="&TODAY())');
  });
  r.autoResizeColumns(1, 5);
}

/* Borra la hoja Resumen y la vuelve a armar (Ejecutar → rehacerResumen) */
function rehacerResumen() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const r = ss.getSheetByName('Resumen');
  if (r) ss.deleteSheet(r);
  resumen(ss);
}

/* Para probar a mano desde el editor: Ejecutar → prueba. Agrega una fila "banner_visto" de prueba. */
function prueba() {
  recibir({ parameter: { en: 'banner_visto', cid: 'prueba', estado: 'prueba', cupon: 'EXTRA15' } });
}
