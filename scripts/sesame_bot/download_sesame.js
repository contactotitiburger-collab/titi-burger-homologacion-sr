// SESAME → descarga reporte "Grupos y tipos de registro"
// Uso:
//   node download_sesame.js                          (Última semana, output /tmp)
//   node download_sesame.js --headed                 (debug visual)
//   node download_sesame.js --week-offset 3          (hace 3 semanas atrás usando el mismo dropdown "Última semana" con navegación por rango custom)
//   node download_sesame.js --from 2026-05-04 --to 2026-05-10 --sem 19
//                                                    (rango custom, guarda como sesame_export_sem19.xlsx)
//   node download_sesame.js --keep-open              (deja el browser abierto para reutilizar sesión)
//
// Diseño:
//   1. Aceptar cookies en cada pantalla.
//   2. Login 2 pasos.
//   3. Navegar a /admin/reports/reports-list, click en "Grupos y tipos de registro".
//   4. Abrir dropdown de fecha:
//      - Si hay --from/--to → seleccionar "Personalizado" y llenar los datepickers.
//      - Si --week-offset N=0 → "Esta semana"; N=1 → "Última semana"; N>=2 → "Personalizado" con rango calculado.
//      - Si no hay flags → "Última semana".
//   5. Click "Generar EXCEL", ir a Descargas, descargar.
//   6. Renombrar al output según --sem o fecha.

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const CREDS_PATH = '/home/tito/.openclaw/credentials/sesame/tito.json';
const NOMINA_DIR = '/home/tito/.openclaw/data/nomina';

const SELECTORS = {
  emailInput: 'input[type=email]',
  passwordInput: 'input[type=password]',
  nextButton: { role: 'button', name: /^(Next|Siguiente)$/i },
  loginButton: { role: 'button', name: /^(Log\s*in|Iniciar\s*sesi[oó]n|Entrar)$/i },
  acceptCookies: 'button:has-text("Aceptar todo")',
  groupsTypesLink: 'text=Grupos y tipos de registro',
  dateRangeInput: 'input.form-select',
  dateRangeOption: (label) => `div.select-option:has-text("${label}")`,
  generateExcelButton: 'button:has-text("Generar EXCEL")',
  downloadsTableRow: 'tr:has-text("XLSX")',
  downloadIcon: 'svg[aria-label="icon-download"]',
};

const URLS = {
  login: 'https://app.sesametime.com/login',
  reportsList: 'https://app.sesametime.com/admin/reports/reports-list',
  downloads: 'https://app.sesametime.com/admin/company/reports/latest-reports',
};

function todayStr() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function fmtDate(d) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

async function acceptCookies(page, label = '') {
  try {
    const btn = page.locator(SELECTORS.acceptCookies).first();
    if (await btn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await btn.click({ force: true });
      await page.waitForTimeout(1200);
      console.log(`   cookies aceptadas (${label})`);
      return true;
    }
  } catch (_) { /* ignore */ }
  return false;
}

async function safeScreenshot(page, label) {
  const ts = Date.now();
  const out = `/tmp/sesame_error_${label}_${ts}.png`;
  try {
    await page.screenshot({ path: out, fullPage: true });
    return out;
  } catch { return null; }
}

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    headed: args.includes('--headed'),
    fromDate: null,
    toDate: null,
    sem: null,
    output: null,
  };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--from') opts.fromDate = args[i+1];
    if (args[i] === '--to') opts.toDate = args[i+1];
    if (args[i] === '--sem') opts.sem = args[i+1];
    if (args[i] === '--output') opts.output = args[i+1];
  }
  return opts;
}

// Meses en español para navegar el calendar v-calendar
const MESES_ES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];

async function currentCalendarTitle(page) {
  // El título del calendar tiene clase .vc-title y contiene "julio 2026" (o similar)
  const title = await page.locator('.vc-title').first().textContent({ timeout: 5000 }).catch(() => null);
  if (!title) return null;
  const parts = title.trim().toLowerCase().split(/\s+/);
  if (parts.length < 2) return null;
  const mesIdx = MESES_ES.indexOf(parts[0]);
  const year = parseInt(parts[1], 10);
  if (mesIdx < 0 || isNaN(year)) return null;
  return { year, month: mesIdx + 1, raw: title.trim() };
}

async function navigateToMonth(page, targetYear, targetMonth) {
  // Ir hacia atrás/adelante hasta que .vc-title muestre el mes deseado
  for (let i = 0; i < 24; i++) {
    const cur = await currentCalendarTitle(page);
    if (!cur) throw new Error('No se pudo leer vc-title del calendar');
    if (cur.year === targetYear && cur.month === targetMonth) return;
    const targetTotalMonths = targetYear * 12 + (targetMonth - 1);
    const curTotalMonths = cur.year * 12 + (cur.month - 1);
    const arrow = targetTotalMonths < curTotalMonths ? '.vc-arrow.is-left' : '.vc-arrow.is-right';
    const btn = page.locator(arrow).first();
    await btn.click();
    await page.waitForTimeout(250);
  }
  throw new Error(`No pude navegar el calendar a ${targetYear}-${targetMonth}`);
}

async function clickDay(page, isoDate) {
  // Los días tienen selector .vc-day.id-YYYY-MM-DD. El content clickeable es .vc-day-content dentro.
  // isoDate: "YYYY-MM-DD"
  const daySel = `.vc-day.id-${isoDate}:not(.is-not-in-month) .vc-day-content`;
  const dayLoc = page.locator(daySel).first();
  const cnt = await dayLoc.count();
  if (cnt === 0) {
    // Fallback: sin filtro is-not-in-month (por si es visible como "in prev/next month")
    const dayLoc2 = page.locator(`.vc-day.id-${isoDate} .vc-day-content`).first();
    const cnt2 = await dayLoc2.count();
    if (cnt2 === 0) throw new Error(`Día ${isoDate} no visible en el calendar`);
    await dayLoc2.click({ force: true });
  } else {
    await dayLoc.click({ force: true });
  }
  await page.waitForTimeout(300);
}

async function selectPersonalizado(page, fromDate, toDate) {
  // fromDate/toDate en formato YYYY-MM-DD.
  console.log(`   -> "Personalizado" con ${fromDate} .. ${toDate}`);

  // Paso 1: abrir dropdown y elegir "Personalizado"
  const dateInput = page.locator(SELECTORS.dateRangeInput).first();
  await dateInput.waitFor({ state: 'visible', timeout: 15000 });
  await dateInput.click();
  await page.waitForTimeout(800);
  const opt = page.locator(SELECTORS.dateRangeOption('Personalizado')).first();
  if (await opt.count() === 0) {
    const shot = await safeScreenshot(page, 'no_personalizado');
    throw new Error(`No encontré opción "Personalizado". Screenshot: ${shot}`);
  }
  await opt.click();
  await page.waitForTimeout(1500);

  // Paso 2: click en el 2º input.form-select (el que muestra el rango) para abrir el datepicker
  const allSelects = await page.locator('input.form-select').all();
  if (allSelects.length < 2) {
    const shot = await safeScreenshot(page, 'no_range_input');
    throw new Error(`Esperaba >= 2 inputs form-select tras Personalizado, encontré ${allSelects.length}. Screenshot: ${shot}`);
  }
  await allSelects[1].click();
  await page.waitForTimeout(1200);

  // Paso 3: navegar y clickear día de inicio, luego día de fin
  const [fy, fm, fd] = fromDate.split('-').map(x => parseInt(x, 10));
  const [ty, tm, td] = toDate.split('-').map(x => parseInt(x, 10));

  await navigateToMonth(page, fy, fm);
  await clickDay(page, fromDate);
  console.log(`   -> click inicio ${fromDate}`);

  // Si el fin cae en otro mes, navegar
  if (fy !== ty || fm !== tm) {
    await navigateToMonth(page, ty, tm);
  }
  await clickDay(page, toDate);
  console.log(`   -> click fin ${toDate}`);

  await page.waitForTimeout(1500);
  // Cerrar el datepicker haciendo click fuera (por si sigue abierto)
  try { await page.locator('body').click({ position: { x: 10, y: 400 } }); } catch {}
  await page.waitForTimeout(800);

  // Verificar que el rango quedó reflejado
  const newVal = await allSelects[1].inputValue().catch(() => '');
  console.log(`   -> rango aplicado en input: "${newVal}"`);
}

async function selectUltimaSemana(page) {
  const dateInput = page.locator(SELECTORS.dateRangeInput).first();
  await dateInput.waitFor({ state: 'visible', timeout: 15000 });
  await dateInput.click();
  await page.waitForTimeout(1000);
  const opt = page.locator(SELECTORS.dateRangeOption('Última semana')).first();
  if (await opt.count() === 0) {
    const shot = await safeScreenshot(page, 'no_ultima');
    throw new Error(`No encontré "Última semana". Screenshot: ${shot}`);
  }
  await opt.click();
  await page.waitForTimeout(1500);
}

async function loginAndNavigate(page, creds) {
  console.log('[login] Cargando...');
  await page.goto(URLS.login, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2500);
  await acceptCookies(page, 'login');

  await page.waitForSelector(SELECTORS.emailInput, { timeout: 15000 });
  await page.fill(SELECTORS.emailInput, creds.email);

  const nextLoc = page.getByRole(SELECTORS.nextButton.role, { name: SELECTORS.nextButton.name });
  if (await nextLoc.count() > 0) {
    await nextLoc.first().click();
    await page.waitForSelector(SELECTORS.passwordInput, { state: 'visible', timeout: 15000 });
  } else {
    await page.waitForSelector(SELECTORS.passwordInput, { timeout: 15000 });
  }
  await page.fill(SELECTORS.passwordInput, creds.password);
  const loginLoc = page.getByRole(SELECTORS.loginButton.role, { name: SELECTORS.loginButton.name });
  if (await loginLoc.count() === 0) throw new Error('No login submit button');
  await loginLoc.first().click();
  await page.waitForURL(u => !u.toString().includes('/login'), { timeout: 30000 });
  console.log('   -> post-login:', page.url());
}

async function goToReport(page) {
  await page.goto(URLS.reportsList, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2000);
  await acceptCookies(page, 'reports-list');
  const link = page.locator(SELECTORS.groupsTypesLink).first();
  await link.waitFor({ state: 'visible', timeout: 15000 });
  await link.click();
  await page.waitForTimeout(4000);
  await acceptCookies(page, 'report-page');
  await page.waitForTimeout(1000);
  if (!page.url().includes('checkTypeCollection')) {
    const shot = await safeScreenshot(page, 'wrong_report');
    throw new Error(`URL inesperada: ${page.url()}. Screenshot: ${shot}`);
  }
}

async function generateAndDownload(page, targetPath) {
  console.log('   -> click "Generar EXCEL"...');
  const excelBtn = page.locator(SELECTORS.generateExcelButton).locator('visible=true').first();
  await excelBtn.waitFor({ state: 'visible', timeout: 15000 });
  await excelBtn.click();

  console.log('   -> esperando /latest-reports...');
  await page.waitForURL(/latest-reports/, { timeout: 45000 }).catch(() => {});
  if (!page.url().includes('latest-reports')) {
    console.log('   -> navego manual a Descargas');
    await page.goto(URLS.downloads, { waitUntil: 'domcontentloaded' });
  }
  await page.waitForTimeout(3000);
  await acceptCookies(page, 'descargas');

  // Refrescar hasta que aparezca la primera fila con XLSX reciente (hasta 60s)
  console.log('   -> esperando fila XLSX...');
  const xlsxRow = page.locator(SELECTORS.downloadsTableRow).first();
  await xlsxRow.waitFor({ state: 'visible', timeout: 60000 });

  console.log('   -> click icono descarga...');
  const dlIcon = xlsxRow.locator(SELECTORS.downloadIcon).first();
  await dlIcon.waitFor({ state: 'visible', timeout: 15000 });

  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 60000 }),
    dlIcon.click(),
  ]);
  await download.saveAs(targetPath);
  return targetPath;
}

async function run() {
  const opts = parseArgs();
  const t0 = Date.now();
  const creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf8'));
  if (!creds.email || !creds.password) throw new Error('Credentials missing');

  // Asegurar dir de output
  if (!fs.existsSync(NOMINA_DIR)) fs.mkdirSync(NOMINA_DIR, { recursive: true });

  // Determinar output path
  let outPath;
  if (opts.output) {
    outPath = opts.output;
  } else if (opts.sem) {
    const sn = String(opts.sem).padStart(2, '0');
    outPath = path.join(NOMINA_DIR, `sesame_export_sem${sn}.xlsx`);
  } else {
    outPath = `/tmp/sesame_export_${todayStr()}.xlsx`;
  }

  const browser = await chromium.launch({ headless: !opts.headed });
  const ctx = await browser.newContext({
    acceptDownloads: true,
    viewport: { width: 1400, height: 900 },
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(25000);

  try {
    await loginAndNavigate(page, creds);
    await goToReport(page);

    // Elegir rango
    if (opts.fromDate && opts.toDate) {
      await selectPersonalizado(page, opts.fromDate, opts.toDate);
    } else {
      await selectUltimaSemana(page);
    }

    await generateAndDownload(page, outPath);

    const stat = fs.statSync(outPath);
    const kb = stat.size / 1024;
    if (kb < 5) throw new Error(`Archivo pesa solo ${kb.toFixed(2)} KB`);

    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`OK: ${outPath} (${kb.toFixed(1)} KB) en ${elapsed}s`);
    console.log(JSON.stringify({ ok: true, path: outPath, sizeKB: +kb.toFixed(1), elapsedS: +elapsed }));
    return { ok: true, path: outPath, sizeKB: kb };
  } catch (err) {
    const shot = await safeScreenshot(page, 'fatal');
    console.error('FAIL:', err.message);
    if (shot) console.error('Screenshot:', shot);
    console.log(JSON.stringify({ ok: false, error: err.message, screenshot: shot }));
    return { ok: false, error: err.message, screenshot: shot };
  } finally {
    await browser.close();
  }
}

run().then(res => { if (!res.ok) process.exit(1); });
