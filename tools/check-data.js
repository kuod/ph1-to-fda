#!/usr/bin/env node
// Sanity-check data.js. Run: node tools/check-data.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'data.js'), 'utf8'), ctx);
const { drugs, programs, cards, meta } = ctx.window.DATA;
const errs = [];
const ids = new Set();
drugs.forEach(d => {
  if (ids.has(d.id)) errs.push('duplicate id ' + d.id); ids.add(d.id);
  if (d.rev.y.length !== 10 || d.rev.lo.length !== 10 || d.rev.hi.length !== 10) errs.push('revenue length ' + d.id);
  if (d.rev.y.some((v, i) => v > d.rev.hi[i] + 0.01 || v < d.rev.lo[i] - 0.01)) errs.push('band ' + d.id);
  if (d.date < meta.from_) errs.push('before window ' + d.id);
  if (!d.company || !d.ta) errs.push('missing company/ta ' + d.id);
});
const outcomes = new Set(['approved', 'halted', 'stalled', 'ongoing']);
programs.forEach(p => { if (!outcomes.has(p.outcome)) errs.push('outcome ' + p.name); if (p.reached < 1 || p.reached > 3) errs.push('reached ' + p.name); });
cards.forEach(c => ['hit', 'p1', 'p2', 'p3'].forEach(k => { if (c[k] != null && (c[k] < 0 || c[k] > 1)) errs.push('rate ' + c.company + k); }));
const unmapped = drugs.filter(d => d.ta === 'Other');
if (unmapped.length) console.warn('warning: ' + unmapped.length + ' drugs in "Other": ' + unmapped.map(d => d.brand).join(', '));
console.log(`${drugs.length} drugs, ${programs.length} programs, ${cards.length} cards, ${errs.length} problem(s)`);
errs.slice(0, 20).forEach(e => console.error(e));
process.exit(errs.length ? 1 : 0);
