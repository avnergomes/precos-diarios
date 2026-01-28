/**
 * Controle de acesso - Precos Diarios
 *
 * INSTRUCOES:
 * 1. Abra https://script.google.com
 * 2. Crie um novo projeto
 * 3. Cole este codigo no editor
 * 4. Clique em "Implantar" > "Nova implantacao"
 * 5. Tipo: "Aplicativo da Web"
 * 6. Executar como: "Eu"
 * 7. Quem tem acesso: "Qualquer pessoa"
 *
 * CONFIGURACAO:
 * - Crie uma planilha do Google Sheets
 * - Copie o ID da planilha da URL (entre /d/ e /edit)
 * - Cole o ID na variavel SPREADSHEET_ID abaixo
 *
 * ESTRUTURA DA PLANILHA:
 * - Aba "access"
 *   Colunas: code | status | expires_at | notes
 *   status: "active" para liberar, qualquer outro valor bloqueia
 *   expires_at: opcional (YYYY-MM-DD). Se vazio, sem expiracao.
 * - Aba "log"
 *   Colunas: timestamp | email | site | code | result | user_agent | ip
 */
const SPREADSHEET_ID = '1bwiH0HTIngFw2ZfAXLQI-YlpajJvVTuFsfugHLYOUhE';
const ACCESS_SHEET = 'access';
const LOG_SHEET = 'log';

const ACCESS_COLUMNS = ['code', 'status', 'expires_at', 'notes'];
const LOG_COLUMNS = ['timestamp', 'email', 'site', 'code', 'result', 'user_agent', 'ip'];

function doGet(e) {
  const params = e.parameter || {};
  const email = (params.email || '').toString().trim().toLowerCase();
  const code = (params.code || '').toString().trim();
  const site = (params.site || '').toString().trim();

  ensureSheets();

  if (!email || !code) {
    return respond({ ok: false, message: 'Informe email e codigo.' });
  }

  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ACCESS_SHEET);
  if (!sheet) {
    return respond({ ok: false, message: 'Planilha de acesso nao encontrada.' });
  }

  const data = sheet.getDataRange().getValues();
  const header = data.shift();
  const codeIndex = header.indexOf('code');
  const statusIndex = header.indexOf('status');
  const expiresIndex = header.indexOf('expires_at');

  if (codeIndex === -1 || statusIndex === -1) {
    return respond({ ok: false, message: 'Colunas obrigatorias ausentes.' });
  }

  let match = null;
  data.forEach((row) => {
    if (row[codeIndex] && row[codeIndex].toString().trim() === code) {
      match = row;
    }
  });

  if (!match) {
    logAttempt(email, site, code, 'denied');
    return respond({ ok: false, message: 'Codigo invalido.' });
  }

  const status = (match[statusIndex] || '').toString().trim().toLowerCase();
  if (status !== 'active') {
    logAttempt(email, site, code, 'blocked');
    return respond({ ok: false, message: 'Acesso bloqueado.' });
  }

  if (expiresIndex !== -1) {
    const expiresRaw = match[expiresIndex];
    if (expiresRaw) {
      const expiresAt = new Date(expiresRaw);
      if (!isNaN(expiresAt.getTime()) && expiresAt.getTime() < Date.now()) {
        logAttempt(email, site, code, 'expired');
        return respond({ ok: false, message: 'Codigo expirado.' });
      }
    }
  }

  const expiration = resolveExpiration(match, expiresIndex);
  logAttempt(email, site, code, 'granted');
  return respond({
    ok: true,
    token: Utilities.getUuid(),
    expiresAt: expiration
  });
}

function resolveExpiration(row, expiresIndex) {
  if (expiresIndex === -1) {
    return new Date(Date.now() + 1000 * 60 * 60 * 24 * 7).toISOString();
  }
  const raw = row[expiresIndex];
  if (!raw) {
    return new Date(Date.now() + 1000 * 60 * 60 * 24 * 7).toISOString();
  }
  const dt = new Date(raw);
  if (isNaN(dt.getTime())) {
    return new Date(Date.now() + 1000 * 60 * 60 * 24 * 7).toISOString();
  }
  return dt.toISOString();
}

function logAttempt(email, site, code, result) {
  try {
    ensureSheets();
    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(LOG_SHEET);
    if (!sheet) return;
    sheet.appendRow([
      new Date().toISOString(),
      email,
      site,
      code,
      result,
      (Session.getActiveUser() || '').toString(),
      getClientIp()
    ]);
  } catch (err) {
    // ignore logging errors
  }
}

function ensureSheets() {
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);

  let accessSheet = spreadsheet.getSheetByName(ACCESS_SHEET);
  if (!accessSheet) {
    accessSheet = spreadsheet.insertSheet(ACCESS_SHEET);
    accessSheet.getRange(1, 1, 1, ACCESS_COLUMNS.length).setValues([ACCESS_COLUMNS]);
    formatHeader(accessSheet, ACCESS_COLUMNS.length, '#0ea5e9');
    accessSheet.setFrozenRows(1);
  }

  let logSheet = spreadsheet.getSheetByName(LOG_SHEET);
  if (!logSheet) {
    logSheet = spreadsheet.insertSheet(LOG_SHEET);
    logSheet.getRange(1, 1, 1, LOG_COLUMNS.length).setValues([LOG_COLUMNS]);
    formatHeader(logSheet, LOG_COLUMNS.length, '#0f172a');
    logSheet.setFrozenRows(1);
  }
}

function setupSheet() {
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);

  let accessSheet = spreadsheet.getSheetByName(ACCESS_SHEET);
  if (accessSheet) {
    spreadsheet.deleteSheet(accessSheet);
  }
  accessSheet = spreadsheet.insertSheet(ACCESS_SHEET);
  accessSheet.getRange(1, 1, 1, ACCESS_COLUMNS.length).setValues([ACCESS_COLUMNS]);
  formatHeader(accessSheet, ACCESS_COLUMNS.length, '#0ea5e9');
  accessSheet.setFrozenRows(1);
  accessSheet.autoResizeColumns(1, ACCESS_COLUMNS.length);

  let logSheet = spreadsheet.getSheetByName(LOG_SHEET);
  if (logSheet) {
    spreadsheet.deleteSheet(logSheet);
  }
  logSheet = spreadsheet.insertSheet(LOG_SHEET);
  logSheet.getRange(1, 1, 1, LOG_COLUMNS.length).setValues([LOG_COLUMNS]);
  formatHeader(logSheet, LOG_COLUMNS.length, '#0f172a');
  logSheet.setFrozenRows(1);
  logSheet.autoResizeColumns(1, LOG_COLUMNS.length);
}

function formatHeader(sheet, columnCount, color) {
  const headerRange = sheet.getRange(1, 1, 1, columnCount);
  headerRange.setFontWeight('bold');
  headerRange.setBackground(color);
  headerRange.setFontColor('#FFFFFF');
}

function getClientIp() {
  try {
    return Session.getActiveUser().getEmail() || '';
  } catch (err) {
    return '';
  }
}

function respond(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
