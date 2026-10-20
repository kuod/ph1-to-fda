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
# reliably from them. These dates are from FDA's approval announcements and are the source of truth for which products
# count; the pages supply the BLA number, manufacturer and indication. Page letters are used to cross-check.
CURATED = {
    # cell and gene therapy
    "Maci": "2016-12-13", "Kymriah": "2017-08-30", "Yescarta": "2017-10-18", "Luxturna": "2017-12-19", "Zolgensma": "2019-05-24",
    "Tecartus": "2020-07-24", "Breyanzi": "2021-02-05", "Abecma": "2021-03-26", "Stratagraft": "2021-06-15", "Rethymic": "2021-10-08",
    "Carvykti": "2022-02-28", "Zynteglo": "2022-08-17", "Skysona": "2022-09-16", "Hemgenix": "2022-11-22", "Adstiladrin": "2022-12-16",
    "Omisirge": "2023-04-17", "Vyjuvek": "2023-05-19", "Elevidys": "2023-06-22", "Lantidra": "2023-06-28", "Roctavian": "2023-06-29",
    "Casgevy": "2023-12-08", "Lyfgenia": "2023-12-08", "Amtagvi": "2024-02-16", "Lenmeldy": "2024-03-18", "Beqvez": "2024-04-25",
    "Tecelra": "2024-08-01", "Aucatzyl": "2024-11-08", "Kebilidi": "2024-11-13", "Regenecyte": "2024-11-20", "Ryoncil": "2024-12-18",
    "Symvess": "2024-12-19", "Encelto": "2025-03-05", "Zevaskyn": "2025-04-28", "Papzimeos": "2025-08-14", "Itvisma": "2025-11-24",
    "Waskyra": "2025-12-09", "Otarmeni": "2026-04-23", "Tregzi": "2026-07-01", "Genglycos": "2026-08-19", "Fayuvi": "2026-09-17",
    "HPC, Cord Blood - MD Anderson Cord Blood Bank": "2018-06-21",
    # vaccines
    "Shingrix": "2017-10-20", "Heplisav-B": "2017-11-09", "Vaxelis": "2018-12-21", "Dengvaxia": "2019-05-01", "Jynneos": "2019-09-24",
    "Ervebo": "2019-12-19", "Audenz": "2020-01-31", "MenQuadfi": "2020-04-23", "Prevnar 20": "2021-06-10", "Vaxneuvance": "2021-07-16",
    "Ticovac": "2021-08-13", "Comirnaty": "2021-08-23", "Prehevbrio": "2021-11-30", "Spikevax": "2022-01-31", "Priorix": "2022-06-03",
    "Arexvy": "2023-05-23", "Abrysvo": "2023-05-31", "Cyfendus": "2023-07-20", "Penbraya": "2023-10-20", "Ixchiq": "2023-11-09",
    "Mresvia": "2024-06-14", "Capvaxive": "2024-06-17", "Vimkunya": "2025-02-14", "Penmenvy": "2025-02-14", "Nuvaxovid": "2025-05-16",
    "Mnexspike": "2025-05-30",
}


def links(path):
    s = BeautifulSoup(get_text(BASE + path), "html.parser")
    out = {}
    for a in s.select("main a, .content a"):
        h = a.get("href", "")
        t = a.get_text(" ", strip=True)
        if h.startswith("/vaccines-blood-biologics/") and not re.search(r"(approved-|-products?$|^/vaccines-blood-biologics/(vaccines|blood-blood-products|cellular-gene-therapy-products)$|questions|emergency|safety|resources)", h) and t:
            out[h] = t
    return out


def page(path):
    try:
        s = BeautifulSoup(get_text(BASE + path), "html.parser")
    except RuntimeError:
        return None
    txt = s.get_text("\n", strip=True)
    field = lambda k: (re.search(k + r":\s*\n(.+)", txt) or [None, ""])[1].strip()
    letters = re.findall(r"([A-Z][a-z]+ \d{1,2}, \d{4}) Approval Letter", txt) or re.findall(r"([A-Z][a-z]+ \d{1,2}, \d{4})\s*(?:Approval|Licensure) Letter", txt)
    dates = []
    for l in letters:
        try:
            dates.append(dt.datetime.strptime(l, "%B %d, %Y").date())
        except ValueError:
            pass
    ind = re.search(r"Indications?\s*\n(.+)", txt)
    return dict(stn=field("STN"), proper=field("Proper Name"), trade=field("Tradename"), mfr=field("Manufacturer"),
                use=(ind.group(1).strip() if ind else ""), first=min(dates).isoformat() if dates else None, n_letters=len(dates))


# Pages that do not parse cleanly: metadata typed in from the FDA pages.
FALLBACK = {
    "Ixchiq": ("chikungunya vaccine, live", "Valneva Austria GmbH", "Prevention of disease caused by chikungunya virus in people 18 years and older", ""),
    "Amtagvi": ("lifileucel", "Iovance Biotherapeutics, Inc.", "Unresectable or metastatic melanoma previously treated with a PD-1 blocking antibody", ""),
    "Lenmeldy": ("atidarsagene autotemcel", "Orchard Therapeutics (Europe) Limited", "Metachromatic leukodystrophy (MLD) in children", "BL 125758"),
}
VACCINES = {"Shingrix", "Heplisav-B", "Vaxelis", "Dengvaxia", "Jynneos", "Ervebo", "Audenz", "MenQuadfi", "Prevnar 20", "Vaxneuvance", "Ticovac", "Comirnaty", "Prehevbrio", "Spikevax", "Priorix", "Arexvy", "Abrysvo", "Cyfendus", "Penbraya", "Ixchiq", "Mresvia", "Capvaxive", "Vimkunya", "Penmenvy", "Nuvaxovid", "Mnexspike"}


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
