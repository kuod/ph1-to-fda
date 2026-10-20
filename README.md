# ph1-to-fda

Ten years of first-time FDA drug approvals, traced from Phase 1.

Every first-time FDA drug approval from October 2016 to October 2026 (576 products: 492 from CDER and 84 cell, gene, vaccine and blood products from CBER), with each drug's Phase 1–3 history, the programs that fell away on the way, and a modelled sales curve for years 1–10. Design follows the [Pharma & Biotech Almanac](https://kuod.github.io/pharma-biotech-almanac/).

Live page: https://kuod.github.io/ph1-to-fda/

## Views

**Funnel** — Alluvial of drug programs that entered Phase 1 in 2009–2018 at 26 large sponsors, flowing through Phase 2, Phase 3 and FDA approval, with halted, stalled and still-active branches. Colour by outcome, company or therapeutic area; filter by company, area and start year; click a column or a ribbon to list its programs in a panel beside the chart (✕ or Esc closes it). Below it, studies started vs halted per phase.

**Baseball Cards** — Hit rate and Phase 1 / 2 / 3 pass rates for each of the 17 sponsors with six or more approvals, plus approvals per year, median years from first registered start to approval, orphan share and top estimated earner. Cards built on fewer than 50 programs are flagged.

**Approvals** — Searchable, sortable table of all approvals. Each row expands to a development timeline, studies started and halted per phase (with the stated reasons and links to ClinicalTrials.gov) and the modelled sales curve. CSV download. A toggle adds drugs first approved earlier that won a new indication (efficacy supplement) in the window.

**Product Pipelines** — Ranks products by efficacy supplements approved in the window; pick one for an approval timeline with halted studies marked beneath it, and a table of the conditions its Phase 1–3 studies cover. Conditions are flagged as approved (in the label), halted, or both, with the stopped studies and their stated reasons one click away.

**Buckets** — Interactive scatter of first-time approvals by approvals since launch (one and done, one then a few, one then many, franchise) against modelled sales. Switch the y metric, log/linear, filter by area or company, pin a drug.

**Revenue y1–y10** — Modelled net sales by year since approval, stacked by company, area, drug type or approval year, with a low–high band, and the largest estimated earners.

**BD201** — A proposed 13-week MBA elective on biopharma business development built on this almanac: weekly sessions, readings, discussion questions, assignments and insight boxes computed live from the data, ending with a deal-committee capstone on the acquired-biotech approvals. Reading citations were written from memory and should be checked before use.

**Who & What** — Sponsor → therapeutic area → drug type alluvial for the approvals in view.

## How it is built

No build step for the site: `index.html` plus `data.js` and two vendored libraries (d3, d3-sankey). The data is produced by a Python pipeline in `tools/`:

| Step | Script | Output |
|---|---|---|
| 1 | `01_approvals.py` | FDA CDER novel approvals (2021–2026 tables; 2016–2020 rebuilt from openFDA Type 1 originals) |
| 2 | `02_enrich.py` | Sponsor, review priority, orphan flag, label text via openFDA |
| 3 | `03_classify.py` | Parent company, therapeutic area, drug type |
| 4 | `04_trials_approved.py` | Each approved drug's Phase 1–3 studies from ClinicalTrials.gov |
| 5 | `05_trials_sponsors.py` | All Phase 1–3 industry studies 2008–2018 for 26 large sponsors |
| 6 | `06_programs.py` | Group studies into programs; outcome per program |
| 7 | `07_build.py` | Revenue model, company cards, `data.js` |
| 9 | `09_cber.py` | CBER first approvals: cell and gene therapies, vaccines, blood products (run before 03) |
| 8 | `08_expansions.py` | Efficacy supplements per product, earlier-approved drugs with new indications, per-condition pipelines for the busiest products (run before 07) |

```sh
pip install -r requirements.txt
for s in 01 02 09 03 04 05 06 08 07; do python3 tools/${s}_*.py; done   # re-fetches everything; responses are cached in .cache/
python3 -m http.server                               # then open http://localhost:8000
node tools/check-scripts.js && node tools/check-data.js
```

Large raw crawls (`data/trials_*_raw.json`) are not committed; the pipeline regenerates them.

## Read this before quoting a number

- **Revenue is modelled, not reported.** Central peak sales come from therapeutic-area medians with modifiers for orphan status, drug type, review priority and sponsor scale, with editorial peaks for about seventy well-known drugs. Years 1–10 follow an S-curve. Bands are 0.35×–2.6×.
- **Funnel rates are descriptive and probably flattering.** Pooled, they read 42% / 50% / 60% for the three phases and 13% overall against rough industry benchmarks of 52% / 29% / 58% and 8%, because failures that cannot be identified go uncounted. A program is identified from ClinicalTrials.gov intervention records, so how many failures a company shows depends on how it labels studies. Thin samples lean toward winners, and renamed assets can look like Phase 1 failures. Company comparisons are indicative only. Details are on the page's Method tab.
- **Scope.** CDER novel approvals plus CBER's first approvals of cell therapies, gene therapies, vaccines and blood and plasma products. CBER first-approval dates were set by hand from FDA announcements because CBER's pages keep only recent letters. Albumin, fibrin sealants and hemostats, diagnostics and allergenics are not included. CBER products have no orphan, priority-review or supplement data, so they are left out of those statistics and out of the Buckets and Product Pipelines views. Phase 1 is often unregistered, so some approved drugs show none.

## Sources

FDA CDER Novel Drug Approvals and Drugs@FDA (via openFDA) · ClinicalTrials.gov API v2 · d3 (ISC) and d3-sankey (BSD-3-Clause), vendored in `vendor/`.

## License

MIT, see [LICENSE](LICENSE).
