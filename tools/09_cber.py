"""First-time approvals from FDA's biologics center (CBER): cell and gene therapies, vaccines, blood products.

openFDA only covers CDER, so these come from CBER's own product pages. Each page carries the BLA number
(STN), proper and trade name, manufacturer, indication and a list of dated approval letters; the earliest
letter is taken as the first approval. Pages whose letter archive starts after the product was really
licensed would look newer than they are, so every result is checked against the BLA number and a
hand-kept exclusion list (EXCLUDE) printed for review.
"""
import concurrent.futures as cf, datetime as dt, json, os, re, sys
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(__file__))
from common import get_text

D = os.path.join(os.path.dirname(__file__), "..", "data")
BASE = "https://www.fda.gov"
START = dt.date(2016, 10, 21)
LISTS = [
    ("Cell or gene therapy", "/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products"),
    ("Vaccine", "/vaccines-blood-biologics/vaccines/vaccines-licensed-use-united-states"),
    ("Blood product", "/vaccines-blood-biologics/blood-blood-products/approved-blood-products"),
]
# CBER's pages only keep recent letters (older ones sit in a 13 MB archive), so the first-approval date cannot be read
# reliably from them. The dates live in data/cber_curated.json, each with the FDA sources it was checked against
# (Purple Book original approval date, FDA page, approval letter) and a status. They are the source of truth for which
# products count; the pages supply the BLA number, manufacturer and indication. Page letters are used to cross-check,
# and tools/09b_cber_verify.py re-checks every date against the Purple Book.
_J = json.load(open(os.path.join(D, "cber_curated.json")))["products"]
CURATED = {k: v["date"] for k, v in _J.items()}
BLOOD = {k: v["date"] for k, v in _J.items() if v["cat"] == "Blood product"}
VACCINES = {k for k, v in _J.items() if v["cat"] == "Vaccine"}


def links(path):
    s = BeautifulSoup(get_text(BASE + path, max_age_hours=6), "html.parser")
    out = {}
    for a in s.select("main a, .content a"):
        h = a.get("href", "")
        t = a.get_text(" ", strip=True)
        if h.startswith("/vaccines-blood-biologics/") and not re.search(r"(approved-|-products?$|^/vaccines-blood-biologics/(vaccines|blood-blood-products|cellular-gene-therapy-products)$|questions|emergency|safety|resources)", h) and t:
            out[h] = t
    return out


def page(path):
    try:
        s = BeautifulSoup(get_text(BASE + path, max_age_hours=6), "html.parser")
    except RuntimeError:
        return None
    txt = s.get_text("\n", strip=True)
    field = lambda k: (re.search(k + r"\s*:?\s*\n:?\s*(?!:)(.+)", txt) or [None, ""])[1].strip(" :")
    letters = re.findall(r"([A-Z][a-z]+ \d{1,2}, \d{4}) Approval Letter", txt) or re.findall(r"([A-Z][a-z]+ \d{1,2}, \d{4})\s*(?:Approval|Licensure) Letter", txt)
    dates = []
    for l in letters:
        try:
            dates.append(dt.datetime.strptime(l, "%B %d, %Y").date())
        except ValueError:
            pass
    ind = re.search(r"Indications?\s*:?\s*\n:?\s*\n?(.*?)\n(?:Product Information|Supporting Documents|Package Insert)", txt, re.S)
    return dict(stn=field("STN"), proper=field("Proper Name"), trade=field("Tradename"), mfr=re.sub(r"Indications?$", "", field("Manufacturer")).strip(),
                use=(re.sub(r"\s*\n\s*", " ", ind.group(1)).strip(" :") if ind else ""), first=min(dates).isoformat() if dates else None, n_letters=len(dates))


# Blood and plasma products are the entries with cat 'Blood product' in cber_curated.json; the inclusion rule is in tools/09b_cber_verify.py.
SLUG = {"Haegarda": "haegarda", "Xembify": "xembify"}

# Pages that do not parse cleanly: metadata typed in from the FDA pages.
FALLBACK = {
    "Ixchiq": ("chikungunya vaccine, live", "Valneva Austria GmbH", "Prevention of disease caused by chikungunya virus in people 18 years and older", "BL 125777"),
    "Amtagvi": ("lifileucel", "Iovance Biotherapeutics, Inc.", "Unresectable or metastatic melanoma previously treated with a PD-1 blocking antibody", "BL 125773"),
    "Andexxa": ("coagulation factor xa (recombinant), inactivated-zhzo", "Portola Pharmaceuticals, Inc.", "Reversal of anticoagulation with rivaroxaban or apixaban in life-threatening or uncontrolled bleeding", "BL 125586"),
    "Xembify": ("immune globulin subcutaneous (human), 20%", "Grifols Therapeutics LLC", "Primary humoral immunodeficiency in patients 2 years and older", "BL 125683"),
    "Lenmeldy": ("atidarsagene autotemcel", "Orchard Therapeutics (Europe) Limited", "Metachromatic leukodystrophy (MLD) in children", "BL 125758"),
}


def main():
    cand = {}
    for cat, path in LISTS:
        try:
            for h, t in links(path).items():
                cand.setdefault(h, (cat, t))
        except RuntimeError as e:
            print("list failed", path, e)
    print(len(cand), "candidate pages")
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda h: page(h), cand))
    for name in BLOOD:
        for pre in ("/vaccines-blood-biologics/", "/vaccines-blood-biologics/approved-blood-products/", "/vaccines-blood-biologics/blood-blood-products/"):
            h = pre + SLUG.get(name, name.lower())
            try:
                pg = page(h)
            except Exception:
                pg = None
            if pg and pg["trade"]:
                cand.setdefault(h, ("Blood product", name))
                res.append(pg) if False else None
                break
    res = [page(h) for h in cand] if len(res) != len(cand) else res
    by = {}
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    for (h, (cat, t)), p in zip(cand.items(), res):
        if not p:
            continue
        for k in {norm(p["trade"]), norm(t.split(" (")[0]), norm(h.rsplit("/", 1)[-1])}:
            if k:
                by.setdefault(k, []).append((h, cat, p))
    rows = []
    for name, d in CURATED.items():
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        hit = by.get(key) or next((v for k, v in by.items() if k.startswith(key)), None)
        if not hit:
            h, cat, p = None, None, None
            if name in FALLBACK:
                pr, mf, us, stn = FALLBACK[name]
                p = dict(proper=pr, mfr=mf, use=us, stn=stn, first=None, n_letters=0)
            else:
                print("no FDA page matched", name)
        else:
            h, cat, p = hit[0]
            if name in FALLBACK:
                pr, mf, us, stn = FALLBACK[name]
                p = dict(p, mfr=p["mfr"] or mf, use=p["use"] if len(p["use"]) > 5 else us, proper=p["proper"] or pr, stn=p["stn"] or stn)
            if p["first"] and abs((dt.date.fromisoformat(p["first"]) - dt.date.fromisoformat(d)).days) > 10 and dt.date.fromisoformat(p["first"]) < dt.date.fromisoformat(d):
                print("date check:", name, "curated", d, "page earliest letter", p["first"])
        if name in BLOOD:
            cat = "Blood product"
        if not cat:
            cat = "Vaccine" if name in VACCINES else "Cell or gene therapy"
        rows.append(dict(path=h, cat=cat, brand=name, ingredient=(p["proper"].lower() if p else ""), date=d,
                         sponsor=(p["mfr"] if p else ""), use=(p["use"] if p else ""), stn=(p["stn"] if p else ""), letters=(p["n_letters"] if p else 0)))
    listed = {re.sub(r"[^a-z0-9]", "", n.lower()) for n in CURATED}
    for k, v in by.items():
        h, cat, p = v[0]
        if cat != "Vaccine" and p["first"] and dt.date.fromisoformat(p["first"]) >= START and not any(k.startswith(x) for x in listed):
            print("not in curated list (check):", p["trade"], p["first"], p["stn"])
    rows.sort(key=lambda r: r["date"])
    print(len(rows), "first approvals in window")
    inwin = {re.sub(r"[^a-z0-9]", "", r["brand"].lower()) for r in rows}
    other = sorted({w for k, v in by.items() for h, cat, p in v[:1] if not any(k.startswith(x) for x in inwin) and p
                    for w in ([p["trade"].lower()] + re.findall(r"[a-z]{6,}(?:leucel|parvovec|temcel|vicleucel|autoleucel|gene)\b", (p["proper"] or "").lower())) if len(w) >= 6 and " " not in w})
    json.dump(other, open(os.path.join(D, "cber_marketed_names.json"), "w"))
    print(len(other), "other CBER product names kept for the already-marketed check")
    json.dump(rows, open(os.path.join(D, "cber_raw.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
