# Ten Years of First-Time Drug Approvals

Every first-time FDA drug approval from October 2016 to October 2026 (490 drugs), with each drug's Phase 1–3 history, the programs that fell away on the way, and a modelled sales curve for years 1–10. Design follows the [Pharma & Biotech Almanac](https://kuod.github.io/pharma-biotech-almanac/).

Live page: https://kuod.github.io/easy-as/

## Views

**Funnel** — Alluvial of drug programs that entered Phase 1 in 2009–2018 at 26 large sponsors, flowing through Phase 2, Phase 3 and FDA approval, with halted, stalled and still-active branches. Colour by outcome, company or therapeutic area; filter by company, area and start year; click a column to list its programs. Below it, studies started vs halted per phase.

**Baseball Cards** — Hit rate and Phase 1 / 2 / 3 pass rates for each of the 17 sponsors with six or more approvals, plus approvals per year, median years from first registered start to approval, orphan share and top estimated earner. Cards built on fewer than 50 programs are flagged.

**Approvals** — Searchable, sortable table of all approvals. Each row expands to a development timeline, studies started and halted per phase (with the stated reasons and links to ClinicalTrials.gov) and the modelled sales curve. CSV download.

**Revenue y1–y10** — Modelled net sales by year since approval, stacked by company, area, drug type or approval year, with a low–high band, and the largest estimated earners.

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

```sh
pip install -r requirements.txt
for s in tools/0[1-7]_*.py; do python3 "$s"; done   # re-fetches everything; responses are cached in .cache/
python3 -m http.server                               # then open http://localhost:8000
node tools/check-scripts.js && node tools/check-data.js
```

Large raw crawls (`data/trials_*_raw.json`) are not committed; the pipeline regenerates them.

## Read this before quoting a number

- **Revenue is modelled, not reported.** Central peak sales come from therapeutic-area medians with modifiers for orphan status, drug type, review priority and sponsor scale, with editorial peaks for about seventy well-known drugs. Years 1–10 follow an S-curve. Bands are 0.35×–2.6×.
- **Funnel rates are descriptive.** A program is identified from ClinicalTrials.gov intervention records, so how many failures a company shows depends on how it labels studies. Thin samples lean toward winners, and renamed assets can look like Phase 1 failures. Company comparisons are indicative only. Details are on the page's Method tab.
- **Scope.** CDER novel approvals only; CBER products (vaccines, gene and cell therapies) are excluded. Phase 1 is often unregistered, so some approved drugs show none.

## Sources

FDA CDER Novel Drug Approvals and Drugs@FDA (via openFDA) · ClinicalTrials.gov API v2 · d3 (ISC) and d3-sankey (BSD-3-Clause), vendored in `vendor/`.

## License

MIT, see [LICENSE](LICENSE).
