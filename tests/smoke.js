#!/usr/bin/env node
// Playwright smoke test: opens every tab, exercises the main controls, and fails on
// console errors, page errors or horizontal overflow at 390px.
// Run: npm install && npx playwright install chromium && npm run test:ui
const { chromium } = require('playwright');
const path = require('path');
const url = 'file://' + path.join(__dirname, '..', 'index.html');
const TABS = ['funnel', 'cards', 'approvals', 'products', 'buckets', 'revenue', 'flow', 'bd201', 'method'];

let failed = 0, passed = 0, cur = '';
async function step(name, fn) {
  cur = name;
  try { await fn(); passed++; console.log('ok   ' + name); }
  catch (e) { failed++; console.log('FAIL ' + name + '\n     ' + String(e.message).split('\n')[0]); }
}
function assert(c, msg) { if (!c) throw new Error(msg); }

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const problems = [];
  page.on('console', m => { if (m.type() === 'error') problems.push(`[${cur}] console: ${m.text()}`); });
  page.on('pageerror', e => problems.push(`[${cur}] pageerror: ${e.message}`));
  page.on('requestfailed', r => problems.push('requestfailed: ' + r.url()));
  await page.goto(url);
  await page.waitForSelector('#stats .stat');

  const open = async t => { await page.click(`#tabbtn-${t}`); await page.waitForSelector(`#tab-${t}.active`); };

  await step('every tab opens and is selected', async () => {
    for (const t of TABS) {
      await open(t);
      assert(await page.getAttribute(`#tabbtn-${t}`, 'aria-selected') === 'true', t + ' not aria-selected');
      assert((await page.textContent(`#tab-${t}`)).trim().length > 50, t + ' is empty');
    }
  });

  await step('funnel: node opens side panel, row expands, Esc closes', async () => {
    await open('funnel');
    assert(await page.locator('#sk-funnel g[role=button]').count() >= 4, 'few funnel nodes');
    await page.locator('#sk-funnel g[role=button]').first().click();
    await page.waitForSelector('#f-split.open');
    assert(await page.locator('#f-list tr.row').count() > 0, 'no programs listed');
    await page.locator('#f-list tr.row').first().click();
    assert(await page.locator('#f-list tr.row.open').count() === 1, 'row did not expand');
    await page.keyboard.press('Escape');
    assert(await page.locator('#f-split.open').count() === 0, 'Esc did not close panel');
  });

  await step('funnel: keyboard opens panel, close button closes it', async () => {
    const node = page.locator('#sk-funnel g[role=button]').nth(1);
    await node.focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('#f-split.open');
    await page.click('#f-close');
    assert(await page.locator('#f-split.open').count() === 0, 'close button failed');
  });

  await step('funnel: filters change the view', async () => {
    const before = await page.textContent('#f-fn');
    await page.locator('#f-co .chip').first().click();
    const after = await page.textContent('#f-fn');
    assert(before !== after, 'company chip did not change count');
    await page.click('#f-clear');
    await page.selectOption('#f-ta', { index: 1 });
    assert(await page.textContent('#f-fn') !== before, 'area filter did not change count');
    await page.selectOption('#f-ta', 'all');
    await page.click('#f-color button[data-v=company]');
    assert(await page.locator('#f-color button.on[data-v=company]').count() === 1, 'colour toggle');
  });

  await step('cards: render and sort', async () => {
    await open('cards');
    assert(await page.locator('#cards > *').count() >= 10, 'few cards');
    await page.click('#c-sort button[data-v=hit]');
    assert(await page.locator('#c-sort button.on[data-v=hit]').count() === 1, 'sort not applied');
  });

  await step('approvals: search, row expand, include toggle', async () => {
    await open('approvals');
    const total = await page.locator('#a-table tbody tr.row').count();
    assert(total > 50, 'few rows');
    await page.locator('#a-table tbody tr.row').first().click();
    assert(await page.locator('#a-table tr.detail').count() === 1, 'row detail missing');
    await page.fill('#a-q', 'zzzznomatch');
    assert(await page.locator('#a-table tbody tr.row').count() === 0, 'search not filtering');
    await page.fill('#a-q', '');
    const c0 = await page.textContent('#a-count');
    await page.locator('#tab-approvals .incl-toggle').click();
    assert(await page.textContent('#a-count') !== c0, 'toggle did not change count');
    await page.locator('#tab-approvals .incl-toggle').click();
    assert(await page.textContent('#a-count') === c0, 'toggle did not restore count');
    await page.selectOption('#a-ta', { index: 1 });
    assert(await page.textContent('#a-count') !== c0, 'area filter did not change count');
  });

  await step('products: select a product', async () => {
    await open('products');
    await page.selectOption('#p-sel', { index: 2 });
    assert((await page.textContent('#p-detail')).length > 100, 'no product detail');
  });

  await step('buckets: metric, scale and filters', async () => {
    await open('buckets');
    assert(await page.locator('#b-plot circle').count() > 20, 'few dots');
    await page.selectOption('#b-y', 'cum');
    await page.click('#b-scale button[data-v=lin]');
    await page.click('#b-age button[data-v="0"]');
    await page.selectOption('#b-ta', { index: 1 });
    assert(await page.locator('#b-plot circle').count() > 0, 'no dots after filter');
  });

  await step('revenue: stack by and cohort', async () => {
    await open('revenue');
    await page.click('#r-by button[data-v=ta]');
    await page.click('#r-proj button[data-v=elapsed]');
    assert(await page.locator('#r-top tbody tr.row').count() > 0, 'no top earners');
    await page.locator('#r-top tbody tr.row').first().click();
    assert(await page.locator('#r-top tr.detail').count() === 1, 'earner detail missing');
  });

  await step('flow: sankey and toggle', async () => {
    await open('flow');
    assert(await page.locator('#sk-flow path').count() > 5, 'few ribbons');
    await page.selectOption('#w-n', '10');
    await page.locator('#tab-flow .incl-toggle').click();
    assert(await page.locator('#sk-flow path').count() > 5, 'flow empty after toggle');
  });

  await step('BD201: accordion expand all / collapse all / single', async () => {
    await open('bd201');
    const n = await page.locator('#bd-weeks details').count();
    assert(n >= 10, 'expected 13 weeks, got ' + n);
    await page.click('#bd-open');
    assert(await page.locator('#bd-weeks details[open]').count() === n, 'expand all');
    await page.click('#bd-close');
    assert(await page.locator('#bd-weeks details[open]').count() === 0, 'collapse all');
    await page.locator('#bd-weeks summary').nth(2).click();
    assert(await page.locator('#bd-weeks details[open]').count() === 1, 'single toggle');
  });

  await step('a11y: funnel table alternative lists programs via keyboard', async () => {
    await open('funnel');
    await page.locator('#f-alt summary').click();
    assert(await page.locator('#f-alt-body button[data-pick^="l:"]').count() > 3, 'no ribbon buttons');
    await page.locator('#f-alt-body button[data-pick^="l:"]').first().focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('#f-split.open');
    assert(await page.locator('#f-list tr.row').count() > 0, 'ribbon list empty');
    await page.keyboard.press('Escape');
    assert(await page.locator('#f-split.open').count() === 0, 'Esc did not close');
  });

  await step('a11y: buckets dots are keyboard operable and have a table', async () => {
    await open('buckets');
    assert(await page.locator('#b-plot circle[tabindex="0"]').count() === 1, 'expected one roving tab stop');
    await page.locator('#b-plot circle[tabindex="0"]').focus();
    const first = await page.evaluate(() => document.activeElement.__data__.id);
    await page.keyboard.press('ArrowRight');
    const second = await page.evaluate(() => document.activeElement.__data__.id);
    assert(first !== second, 'arrow key did not move focus');
    await page.keyboard.press('Enter');
    assert(await page.locator('#b-pin .rate').count() > 0, 'Enter did not pin');
    assert(await page.evaluate(id => document.activeElement.__data__ && document.activeElement.__data__.id === id, second), 'focus lost after pin');
    await page.keyboard.press('Escape');
    assert(await page.locator('#b-pin .rate').count() === 0, 'Esc did not unpin');
    await page.locator('#b-alt summary').click();
    assert(await page.locator('#b-alt-body tbody tr').count() === await page.locator('#b-plot circle').count(), 'table rows differ from dots');
  });

  await step('a11y: flow table alternative', async () => {
    await open('flow');
    assert(await page.locator('#w-alt-body tbody tr').count() > 5, 'flow table short');
  });

  await step('prose counts are filled from the data', async () => {
    const r = await page.evaluate(() => {
      const P = window.DATA.meta.prose;
      const els = [...document.querySelectorAll('[data-fill]')];
      return { empty: els.filter(e => !e.textContent.trim()).length, n: els.length,
        method: document.querySelector('#tab-method').textContent, stats: document.querySelector('#stats').textContent, P };
    });
    assert(r.n >= 10 && r.empty === 0, 'unfilled data-fill spans');
    assert(r.method.includes(`${r.P.p1}% Phase 1`) && r.method.includes(`${r.P.nAnchor} well-known drugs`), 'Method prose not from data');
    assert(r.stats.includes(String(r.P.nDrugs)), 'masthead count differs from meta.prose');
  });

  await step('no console or page errors on desktop', async () => {
    assert(problems.length === 0, problems.join(' | '));
  });

  // phone width: no horizontal page overflow on any tab
  const phone = await browser.newPage({ viewport: { width: 390, height: 800 } });
  const pproblems = [];
  phone.on('console', m => { if (m.type() === 'error') pproblems.push(m.text()); });
  phone.on('pageerror', e => pproblems.push(e.message));
  await phone.goto(url);
  await phone.waitForSelector('#stats .stat');
  for (const t of TABS) {
    await step(`390px: no horizontal overflow on ${t}`, async () => {
      await phone.click(`#tabbtn-${t}`);
      await phone.waitForSelector(`#tab-${t}.active`);
      if (t === 'bd201') await phone.click('#bd-open');
      const o = await phone.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
      assert(o.sw <= o.cw, `scrollWidth ${o.sw} > ${o.cw}`);
    });
  }
  await step('no console or page errors at 390px', async () => { assert(pproblems.length === 0, pproblems.join(' | ')); });

  await browser.close();
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})();
