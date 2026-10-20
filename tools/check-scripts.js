#!/usr/bin/env node
// Syntax-check every inline <script> block in index.html. Run: node tools/check-scripts.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!blocks.length) { console.error('no inline scripts found'); process.exit(2); }
let bad = 0;
blocks.forEach((src, i) => {
  try { new vm.Script(src, { filename: `index.html#script${i}` }); }
  catch (e) { bad++; console.error(`script ${i}: ${e.message}`); }
});
console.log(`${blocks.length} script block(s), ${bad} syntax error(s)`);
process.exit(bad ? 1 : 0);
