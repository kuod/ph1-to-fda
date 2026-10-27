#!/usr/bin/env node
// Sanity-check data.js. Run: node tools/check-data.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'data.js'), 'utf8'), ctx);
const { drugs, programs, cards, meta, expansions, products } = ctx.window.DATA;
const errs = [];
const ids = new Set();
drugs.forEach(d => {
  if (ids.has(d.id)) errs.push('duplicate id ' + d.id); ids.add(d.id);
  if (d.rev.y.length !== 10 || d.rev.lo.length !== 10 || d.rev.hi.length !== 10) errs.push('revenue length ' + d.id);
  if (d.rev.y.some((v, i) => v > d.rev.hi[i] + 0.01 || v < d.rev.lo[i] - 0.01)) errs.push('band ' + d.id);
  if (d.date < meta.from_) errs.push('before window ' + d.id);
  if (!d.company || !d.ta) errs.push('missing company/ta ' + d.id);
});
products.forEach(p => { if (!p.pipe || !p.d.length) errs.push('product ' + p.id); });
expansions.forEach(e => { if (!e.d.length) errs.push('expansion ' + e.id); });
drugs.forEach(d => {
  if (d.date > meta.built) errs.push('after build date ' + d.id);
  if (d.center === 'CBER' && (d.orphan || d.supps !== null)) errs.push('CBER fields ' + d.id);
  if (d.center !== 'CBER' && !Array.isArray(d.supps)) errs.push('CDER supps ' + d.id);
});
const names = new Set(drugs.map(d => d.brand.toLowerCase() + '|' + d.center));
if (names.size !== drugs.length) errs.push('duplicate brand within a center');
const unk = drugs.filter(d => d.company === 'Unknown');
if (unk.length) console.warn('warning: unknown sponsor: ' + unk.map(d => d.brand).join(', '));
cards.forEach(c => { if (c.approvals !== drugs.filter(d => d.company === c.company).length) errs.push('card count ' + c.company); });
const outcomes = new Set(['approved', 'halted', 'stalled', 'ongoing']);
programs.forEach(p => { if (!outcomes.has(p.outcome)) errs.push('outcome ' + p.name); if (p.reached < 1 || p.reached > 3) errs.push('reached ' + p.name); });
cards.forEach(c => ['hit', 'p1', 'p2', 'p3'].forEach(k => { if (c[k] != null && (c[k] < 0 || c[k] > 1)) errs.push('rate ' + c.company + k); }));
const unmapped = drugs.filter(d => d.ta === 'Other');
if (unmapped.length) console.warn('warning: ' + unmapped.length + ' drugs in "Other": ' + unmapped.map(d => d.brand).join(', '));
console.log(`${drugs.length} drugs, ${programs.length} programs, ${cards.length} cards, ${expansions.length} expansions, ${products.length} products, ${errs.length} problem(s)`);
errs.slice(0, 20).forEach(e => console.error(e));
const funnelStatus = require('child_process').spawnSync(process.execPath, [path.join(__dirname, 'check-funnel.js')], { stdio: 'inherit' }).status;  // pooled funnel rates vs programs, README and benchmarks
process.exit(errs.length || funnelStatus ? 1 : 0);
