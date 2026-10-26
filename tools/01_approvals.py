"""Build the list of first-time (novel) FDA approvals for the last 10 years.

2021-2026: parsed from FDA's official "Novel Drug Approvals" tables (CDER).
Oct 2016-2020: those pages have moved/been retired, so we derive the list from
openFDA/Drugs@FDA as ORIG-1 approvals classed TYPE 1 (NMEs and new biologics)
and check the yearly counts against CDER's published annual totals.
"""
import collections, datetime as dt, json, os, re, sys
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json, get_text

START = dt.date(2016, 10, 21)
OFDA = "https://api.fda.gov/drug/drugsfda.json"
OFFICIAL = {2016: 22, 2017: 46, 2018: 59, 2019: 48, 2020: 53}  # CDER annual totals


def official(year):
    url = f"https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-{year}"
    soup = BeautifulSoup(get_text(url, max_age_hours=6 if year >= dt.date.today().year - 1 else None), "html.parser")
    out = []
    for tr in soup.find("table").find_all("tr")[1:]:
        c = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(c) < 5:
            continue
        m, d, y = c[3].split("/")
        y = int(y) + 2000 if int(y) < 100 else int(y)  # FDA's 2022 table has Tzield as 11/18/0022
        out.append(dict(brand=c[1], ingredient=c[2], date=dt.date(y, int(m), int(d)).isoformat(),
                        use=re.sub(r"\s*Drug Trials Snapshot.*$", "", c[4]).strip(), src="fda-novel-list"))
    return out


# FDA retired the 2016-2020 pages; these Wayback snapshots hold the originals. They are used to catch anything the openFDA rebuild misses.
WAYBACK = {2016: "20230103193910", 2017: "20230121035629", 2018: "20230121035625", 2019: "20230110202020", 2020: "20230121035641"}
OLD = "https://www.fda.gov/drugs/new-drugs-fda-cders-new-molecular-entities-and-new-therapeutic-biological-products/novel-drug-approvals-%d"


def archived(year):
    soup = BeautifulSoup(get_text(f"https://web.archive.org/web/{WAYBACK[year]}id_/{OLD % year}"), "html.parser")
    out = []
    for tr in soup.find_all("tr")[1:]:
        c = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(c) >= 5 and re.search(r"\d+/\d+/\d{2,4}", c[3]):
            m, d, _ = c[3].split("/")  # the archived tables contain year typos (2028, 0022), so trust the year of the page
            out.append(dict(brand=c[1], ingredient=c[2], date=dt.date(year, int(m), int(d)).isoformat(),
                            use=re.sub(r"\s*Drug Tr\w+ Snapshot.*$", "", c[4]).strip(), src="fda-archived-list"))
    return out


def ofda_apps(search):
    apps, skip = [], 0
    while True:
        d = get_json(OFDA, {"search": search, "limit": 1000, "skip": skip})
        apps += d.get("results", [])
        skip += 1000
        if skip >= d.get("meta", {}).get("results", {}).get("total", 0):
            return apps


def derived(y0, y1):
    out = []
    for prefix in ("NDA", "BLA"):
        apps = ofda_apps(f'application_number:{prefix}* AND submissions.submission_status_date:[{y0}0101 TO {y1}1231]')
        for a in apps:
            for s in a["submissions"]:
                if (s["submission_type"] == "ORIG" and s["submission_number"] == "1" and s["submission_status"] == "AP"
                        and (s.get("submission_class_code") or "").startswith("TYPE 1")
                        and "TYPE 1" == s["submission_class_code"].split(",")[0].split("/")[0].strip()
                        and y0 * 10000 <= int(s["submission_status_date"]) <= y1 * 10000 + 1231):
                    d = s["submission_status_date"]
                    p = a["products"][0]
                    ai = ", ".join(x["name"].lower() for x in p.get("active_ingredients", []))
                    out.append(dict(brand=p["brand_name"].title(), ingredient=ai, date=f"{d[:4]}-{d[4:6]}-{d[6:]}",
                                    app=a["application_number"], src="openfda-type1"))
    return out


def main():
    rows = []
    for y in range(2021, 2027):
        rows += official(y)
    rows += derived(2016, 2020)
    # add anything on FDA's original lists that the Type 1 rebuild missed (matched on brand or ingredient, and on year)
    def norm(x):  # same drug under two names: DOTATOC is edotreotide, PSMA-11 is gozetotide
        x = re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", x.lower()))
        return x.replace("dotatoc", "edotreotide").replace("psma", "gozetotide")
    have = {(norm(r["brand"]), r["date"][:4]) for r in rows} | {(norm(r["ingredient"]).split("and")[0][:12], r["date"][:4]) for r in rows}
    added = []
    for y in WAYBACK:
        try:
            for a in archived(y):
                if a["date"] >= START.isoformat() and (norm(a["brand"]), a["date"][:4]) not in have and (norm(a["ingredient"])[:12], a["date"][:4]) not in have \
                        and not any(norm(a["brand"])[:6] == k[0][:6] and k[1] == a["date"][:4] for k in have) \
                        and not any(k[1] == a["date"][:4] and len(norm(a["brand"])) >= 8 and (norm(a["brand"]) in k[0] or k[0] in norm(a["brand"])) for k in have):
                    rows.append(a)
                    added.append(a["brand"])
        except RuntimeError as e:
            print("archive unavailable for", y, e)
    print("added from FDA's archived lists:", added)
    rows = [r for r in rows if r["date"] >= START.isoformat()]
    print("raw counts", sorted(collections.Counter(r["date"][:4] for r in rows).items()))
    json.dump(rows, open(os.path.join(os.path.dirname(__file__), "..", "data", "approvals_raw.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
