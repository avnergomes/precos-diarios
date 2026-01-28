/**
 * Controle de acesso - Precos Diarios
 *
 * Planilha esperada:
 * - Aba "access"
 *   Colunas: code | status | expires_at | notes
 *   status: "active" para liberar, qualquer outro valor bloqueia
 *   expires_at: opcional (YYYY-MM-DD). Se vazio, sem expiracao.
 * - Aba "log" (opcional)
 *   Colunas: timestamp | email | site | code | result | user_agent | ip
 */
const SPREADSHEET_ID = '1bwiH0HTIngFw2ZfAXLQI-YlpajJvVTuFsfugHLYOUhE/';
const ACCESS_SHEET = 'access';
const LOG_SHEET = 'log';

function doGet(e) {
  const params = e.parameter || {};
  const email = (params.email || '').toString().trim().toLowerCase();
  const code = (params.code || '').toString().trim();
  const site = (params.site || '').toString().trim();

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
