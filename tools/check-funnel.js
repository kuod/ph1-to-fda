#!/usr/bin/env node
// Re-derive the pooled funnel rates from data.js programs and compare with meta.funnel and the README prose.
// Prints our rates against the published benchmarks. Run: node tools/check-funnel.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'data.js'), 'utf8'), ctx);
const { programs, meta, cards } = ctx.window.DATA;
const F = meta.funnel, errs = [];
function pooled(ps) {
  const res = ps.filter(p => p.outcome !== 'ongoing'), r2 = res.filter(p => p.reached >= 2), r3 = res.filter(p => p.reached >= 3);
  const ok = res.filter(p => p.outcome === 'approved'), ok3 = r3.filter(p => p.outcome === 'approved');
  return { n: res.length, p1: r2.length / res.length, p2: r3.length / r2.length, p3: ok3.length / r3.length, hit: ok.length / res.length };
}
const near = (a, b) => Math.abs(a - b) < 0.0006;
function cmp(name, got, want) {
  if (got.n !== want.n) errs.push(`${name}.n: recomputed ${got.n} vs meta ${want.n}`);
  ['p1', 'p2', 'p3', 'hit'].forEach(k => { if (!near(got[k], want[k])) errs.push(`${name}.${k}: recomputed ${got[k]} vs meta ${want[k]}`); });
}
const all = pooled(programs);
cmp('all', all, F.all);
const n = {};
programs.forEach(p => { if (p.outcome !== 'ongoing') n[p.company] = (n[p.company] || 0) + 1; });
const deepSet = new Set(Object.keys(n).filter(c => n[c] >= F.deepMin));
cmp('deep', pooled(programs.filter(p => deepSet.has(p.company))), F.deep);
if (deepSet.size !== F.deepSponsors) errs.push('deepSponsors');
// each card must agree with its programs, and every rate must sit inside its interval
cards.forEach(c => {
  const r = pooled(programs.filter(p => p.company === c.company));
  if (c.resolvedN !== r.n || (c.hit != null && Math.abs(c.hit - r.hit) > 0.0006)) errs.push('card rate ' + c.company);
  ['hit', 'p1', 'p2', 'p3'].forEach(k => { const ci = c[k + 'ci']; if (c[k] != null && !(ci && ci[0] <= c[k] + 1e-9 && c[k] <= ci[1] + 1e-9)) errs.push('ci ' + c.company + k); });
});
// benchmarks: arithmetic cross-checks against the figures quoted in their citations
const bio = F.bench.find(b => b.id === 'bio2021'), wong = F.bench.find(b => b.id === 'wong2019');
if (!(bio && wong)) errs.push('benchmarks missing');
else {
  if (Math.abs(0.520 * 0.289 * 0.578 * 0.906 - bio.hit) > 0.0005) errs.push('BIO phase transitions do not multiply to the LOA');
  if (Math.abs(0.578 * 0.906 - bio.p3) > 0.0015) errs.push('BIO Phase 3 to approval');
  [bio, wong].forEach(b => { if (!b.cite || !/^https:\/\//.test(b.url)) errs.push('benchmark citation ' + b.id); });
}
// README quotes the pooled numbers; keep them honest
const readme = fs.readFileSync(path.join(__dirname, '..', 'README.md'), 'utf8');
const r0 = v => Math.round(v * 100) + '%';
[[all.p1, 'all Ph1'], [all.p2, 'all Ph2'], [all.p3, 'all Ph3'], [all.hit, 'all overall'], [F.deep.p1, 'deep Ph1'], [F.deep.p2, 'deep Ph2'], [F.deep.p3, 'deep Ph3']].forEach(([v, l]) => { if (!readme.includes(r0(v))) errs.push('README is missing ' + r0(v) + ' (' + l + ')'); });
if (!readme.includes((F.deep.hit * 100).toFixed(1) + '%')) errs.push('README is missing deep overall ' + (F.deep.hit * 100).toFixed(1) + '%');
const pc = v => (v * 100).toFixed(1).padStart(5) + '%';
console.log('                    n   Ph1→2  Ph2→3  Ph3→appr  overall');
const line = (l, o) => console.log(l.padEnd(14), String(o.n || '').padStart(5), pc(o.p1), pc(o.p2), pc(o.p3), ' ', pc(o.hit));
line('all sponsors', all); line('well covered', F.deep); line('thin', F.thin); F.bench.forEach(b => line(b.id, b));
console.log(`${errs.length} problem(s)`);
errs.forEach(e => console.error(e));
process.exit(errs.length ? 1 : 0);
