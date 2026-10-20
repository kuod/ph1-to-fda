"""Crawl Phase 1-3 industry studies (started 2008-2018) for the large sponsors.

This is the denominator for pipeline attrition: every investigational program a
company started, not just the ones that reached approval.
"""
import concurrent.futures as cf, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json
import importlib.util

spec = importlib.util.spec_from_file_location("t4", os.path.join(os.path.dirname(__file__), "04_trials_approved.py"))
t4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t4)

D = os.path.join(os.path.dirname(__file__), "..", "data")
U = "https://clinicaltrials.gov/api/v2/studies"
FROM, TO = "2008-01-01", "2018-12-31"

SPONSORS = {
    "Pfizer": ["Pfizer", "Wyeth", "Seagen", "Array BioPharma", "Medivation", "Arena Pharmaceuticals", "Biohaven", "Global Blood Therapeutics"],
    "Merck & Co.": ["Merck Sharp & Dohme", "Schering-Plough", "Organon", "Acceleron"],
    "Novartis": ["Novartis", "Alcon", "Avexis", "Endocyte"],
    "Roche": ["Hoffmann-La Roche", "Genentech", "Chugai", "Spark Therapeutics"],
    "AstraZeneca": ["AstraZeneca", "MedImmune", "Alexion", "Acerta Pharma"],
    "GSK": ["GlaxoSmithKline", "Tesaro", "ViiV Healthcare"],
    "Sanofi": ["Sanofi", "Genzyme", "Ablynx", "Principia Biopharma", "Bioverativ"],
    "Eli Lilly": ["Eli Lilly and Company", "Loxo Oncology"],
    "Bristol Myers Squibb": ["Bristol-Myers Squibb", "Celgene", "Juno Therapeutics", "Mirati Therapeutics", "MyoKardia"],
    "Johnson & Johnson": ["Janssen", "Actelion", "Johnson & Johnson"],
    "AbbVie": ["AbbVie", "Allergan", "Pharmacyclics", "Cerevel", "ImmunoGen"],
    "Amgen": ["Amgen", "Horizon Pharma", "ChemoCentryx"],
    "Takeda": ["Takeda", "Shire", "Millennium Pharmaceuticals", "Baxalta"],
    "Gilead Sciences": ["Gilead Sciences", "Kite, A Gilead Company", "Immunomedics"],
    "Bayer": ["Bayer"],
    "Novo Nordisk": ["Novo Nordisk"],
    "Regeneron": ["Regeneron Pharmaceuticals"],
    "Boehringer Ingelheim": ["Boehringer Ingelheim"],
    "Vertex": ["Vertex Pharmaceuticals"],
    "Astellas": ["Astellas Pharma"],
    "Daiichi Sankyo": ["Daiichi Sankyo"],
    "Biogen": ["Biogen"],
    "Eisai": ["Eisai"],
    "UCB": ["UCB Biopharma", "Zogenix"],
    "Otsuka": ["Otsuka Pharmaceutical", "Lundbeck"],
    "Merck KGaA": ["EMD Serono", "Merck KGaA"],
    "Servier": ["Servier", "Institut de Recherches Internationales Servier"],
}


def crawl(job):
    parent, lead = job
    out, tok = [], None
    for _ in range(40):
        p = {"query.lead": lead, "pageSize": 1000, "fields": t4.FIELDS,
             "filter.advanced": f"{t4.FILTER} AND AREA[StartDate]RANGE[{FROM},{TO}] AND AREA[LeadSponsorClass]INDUSTRY"}
        if tok:
            p["pageToken"] = tok
        d = get_json(U, p)
        out += [t4.slim(s) for s in d.get("studies", [])]
        tok = d.get("nextPageToken")
        if not tok:
            break
    return parent, lead, out


def main():
    jobs = [(p, q) for p, qs in SPONSORS.items() for q in qs]
    res = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for parent, lead, studies in ex.map(crawl, jobs):
            print(f"{parent:22s} {lead:40s} {len(studies)}")
            for s in studies:
                res.setdefault(parent, {})[s["id"]] = s
    json.dump({p: list(v.values()) for p, v in res.items()}, open(os.path.join(D, "trials_sponsors_raw.json"), "w"))


if __name__ == "__main__":
    main()
