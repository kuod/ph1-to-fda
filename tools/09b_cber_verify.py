"""Re-check the CBER first-approval dates and the blood-product coverage against FDA's own records.

Run after 09_cber.py (or any time; it only reads). Three jobs:

1. Dates. Every entry in data/cber_curated.json is compared with the Original approval date that FDA's Purple Book
   lists for its BLA. A mismatch fails the run unless the entry has a `note` explaining which record was preferred.
2. Coverage. Every CBER Original BLA approved on or after the window start is classified. Blood and plasma products
   are selected by BLOOD_RULE below, applied mechanically to the Purple Book proper name, so the edge of the list is
   not a judgement call made one product at a time. Products that pass the rule but are missing from the curated file
   fail the run; products excluded by rule, and CBER products outside the three groups, are listed in
   data/cber_coverage.json for review.
3. Index. The "Fractionated Plasma Products" index on fda.gov (about 120 links across category pages) is crawled to
   product level, to show how much of the in-window list FDA's own index actually links.

Inclusion rule for blood and plasma products (cat "Blood product"): a CBER-regulated Original BLA approved in the window
whose active is a human plasma protein or its recombinant counterpart (immune globulins, coagulation and anticoagulant
factors, fibrinogen, C1 esterase inhibitor, plasminogen, prothrombin complex, ADAMTS13, factor Xa antidote). A new brand of
an immune globulin or factor counts because it is its own BLA with its own approval. Excluded by rule: albumin (no new
therapeutic), fibrin sealants, thrombin and hemostatic patches (topical), allergenic extracts, fecal microbiota, tissue
grafts, and anything that is not an Original BLA (diagnostics, reagents, supplements).
"""
import concurrent.futures as cf, csv, datetime as dt, io, json, os, re, sys
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(__file__))
from common import get_text

D = os.path.join(os.path.dirname(__file__), "..", "data")
BASE = "https://www.fda.gov"
START = dt.date(2016, 10, 21)
PB_PAGE = "https://purplebooksearch.fda.gov/downloads"
INDEX = "/vaccines-blood-biologics/approved-blood-products/fractionated-plasma-products"

BLOOD_RULE = re.compile(r"immune globulin|globulin \(human\)|coagulation factor|antihemophilic|fibrinogen|c1 esterase|prothrombin complex|plasminogen|adamts13|"
                        r"factor (?:viii|ix|x|xiii|vii)|von willebrand|antithrombin|alpha.?1.?(?:proteinase|antitrypsin)|protein c\b|rho\(d\)", re.I)
NOT_BLOOD = [("allergenic extract or patch test", re.compile(r"allergen|pollen|\bmites?\b|patch test|epicutaneous|extract", re.I)),
             ("albumin", re.compile(r"albumin", re.I)),
             ("topical (fibrin sealant, thrombin, hemostat)", re.compile(r"fibrin sealant|thrombin, topical|hemosta|sealant", re.I)),
             ("fecal microbiota", re.compile(r"fecal microbiota", re.I)),
             ("tissue graft", re.compile(r"graft|allograft", re.I))]


def purple_book():
    """Latest monthly Purple Book data file: all licensed biologics with Original and supplement rows."""
    pg = get_text(PB_PAGE, max_age_hours=24 * 7)
    urls = re.findall(r'href="(https://www\.accessdata\.fda\.gov/drugsatfda_docs/PurpleBook/\d{4}/[^"]+\.csv)"', pg)
    if not urls:
        raise RuntimeError("no Purple Book csv link found on " + PB_PAGE)
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

    def when(u):
        m = re.search(r"/(\d{4})/purplebook-search-([a-z]+)-data-download", u, re.I)
        return (int(m.group(1)), months.index(m.group(2).lower())) if m and m.group(2).lower() in months else (0, 0)

    url = max(urls, key=when)  # newest monthly file
    lines = get_text(url, max_age_hours=24 * 7).lstrip("﻿").split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("N/R/U"))
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))
    return url, [r for r in rows if r.get("Supplement Number") in ("0", "") and r.get("Submission Type") == "Original"]


def pb_date(r):
    try:
        return dt.datetime.strptime(r["Approval Date"], "%B %d, %Y").date()
    except (ValueError, KeyError):
        return None


def crawl_index():
    """Product pages reachable from the fractionated-plasma index (category pages down to products), as {path: (title, STN)}."""
    skip = re.compile(r"(approved-blood-products$|licensed-products-blas|new-drug-applications|premarket|510k|blood-donor|infectious-disease-tests|grouping|supporting-documents|development-approval|questions|safety|emergency|about-fda)")

    def fetch(path):
        try:
            return BeautifulSoup(get_text(BASE + path, max_age_hours=6), "html.parser")
        except Exception:  # a page that keeps failing is skipped, not fatal; the count of crawled pages is reported
            return None

    def kids(s):
        return {a.get("href"): a.get_text(" ", strip=True) for a in s.select("main a, .content a")
                if a.get("href", "").startswith("/vaccines-blood-biologics/") and "#" not in a["href"] and a.get_text(strip=True)}

    root = kids(fetch(INDEX))
    seen, frontier, prods = {INDEX}, {h: t for h, t in root.items() if not skip.search(h)}, {}
    for depth in range(4):
        with cf.ThreadPoolExecutor(6) as ex:
            res = list(ex.map(fetch, frontier))
        nxt = {}
        for (h, t), s in zip(frontier.items(), res):
            seen.add(h)
            if s is None:
                continue
            txt = s.get_text("\n", strip=True)
            stn = re.search(r"\bSTN\s*:?\s*\n:?\s*(?!:)(.+)", txt)
            if stn and re.search(r"Tradename|Proper Name", txt):
                prods[h] = (t, stn.group(1).strip())
            elif depth < 3:
                nxt.update({h2: t2 for h2, t2 in kids(s).items() if h2 not in seen and h2 not in root and not skip.search(h2)})
        frontier = nxt
        if not frontier:
            break
    return len(seen), prods


def main():
    cur = json.load(open(os.path.join(D, "cber_curated.json")))["products"]
    pb_url, pb = purple_book()
    by_bla = {}
    for r in sorted((r for r in pb if r["Center"] == "CBER"), key=lambda r: pb_date(r) or dt.date.max, reverse=True):
        by_bla[re.sub(r"\D", "", r["BLA Number"])] = r  # a BLA can carry several Original rows (new presentations); the earliest is the approval
    bad = []

    print("Purple Book file:", pb_url)
    for name, e in cur.items():
        r = by_bla.get(e.get("bla", ""))
        if not r:
            bad.append(f"{name}: BLA {e.get('bla')} not found among CBER Original BLAs in the Purple Book")
            continue
        d = pb_date(r)
        if d is None or d.isoformat() != e["date"]:
            if e.get("note"):
                print(f"  note kept: {name} curated {e['date']} vs Purple Book {d} ({e['note'][:70]}...)")
            else:
                bad.append(f"{name}: curated {e['date']} but Purple Book says {d}, and the entry has no note")
        if e.get("purple_book") != (d.isoformat() if d else None):
            bad.append(f"{name}: purple_book field {e.get('purple_book')} is stale (file says {d})")
    print(len(cur), "curated products checked;", len(bad), "problems")

    have = {re.sub(r"\D", "", e.get("bla", "")) for e in cur.values()}
    cov = dict(purple_book_file=pb_url, window_start=START.isoformat(), blood_rule=BLOOD_RULE.pattern, blood_missing=[], blood_excluded_by_rule=[], other_cber_not_curated=[])
    for bla, r in sorted(by_bla.items(), key=lambda kv: pb_date(kv[1]) or START):
        d = pb_date(r)
        if bla in have or d is None or d < START:
            continue
        item = dict(bla=bla, brand=r["Proprietary Name"].strip(), proper_name=r["Proper Name"].strip(), applicant=r["Applicant"].strip(), approved=d.isoformat(), status=r["Licensure"])
        why = next((w for w, rx in NOT_BLOOD if rx.search(r["Proper Name"] + " " + r["Proprietary Name"])), None)
        if why:
            cov["blood_excluded_by_rule"].append(dict(item, reason=why))
        elif BLOOD_RULE.search(r["Proper Name"]):
            cov["blood_missing"].append(item)
        else:
            cov["other_cber_not_curated"].append(item)
    # curated blood products must satisfy the rule too, so the rule and the file cannot drift apart
    for name, e in cur.items():
        if e["cat"] == "Blood product":
            r = by_bla.get(e["bla"])
            if r and not BLOOD_RULE.search(r["Proper Name"]):
                bad.append(f"{name}: in the blood list but its Purple Book name {r['Proper Name']!r} does not match the rule")
    for it in cov["blood_missing"]:
        bad.append(f"blood product passes the rule but is not in cber_curated.json: {it['brand']} (BLA {it['bla']}, {it['approved']})")

    print("\nIndex crawl (this takes a few hundred page fetches the first time) ...")
    n_pages, prods = crawl_index()
    idx_bla = {re.sub(r"\D", "", stn.split(";")[0].split("/")[0]): (t, h) for h, (t, stn) in prods.items()}
    blood = {n: e for n, e in cur.items() if e["cat"] == "Blood product"}
    cov["index"] = dict(pages_crawled=n_pages, product_pages=len(prods),
                        in_window_blood_linked=sorted(n for n, e in blood.items() if e["bla"] in idx_bla),
                        in_window_blood_not_linked=sorted(n for n, e in blood.items() if e["bla"] not in idx_bla))
    print(f"{n_pages} index pages, {len(prods)} product pages; {len(cov['index']['in_window_blood_linked'])} of {len(blood)} curated blood products are linked from the index, "
          f"{len(cov['index']['in_window_blood_not_linked'])} are not (their own FDA pages exist).")
    json.dump(cov, open(os.path.join(D, "cber_coverage.json"), "w"), indent=1, ensure_ascii=False)
    print(f"Excluded by rule: {len(cov['blood_excluded_by_rule'])}; other CBER originals not curated: {len(cov['other_cber_not_curated'])} (see data/cber_coverage.json)")
    for b in bad:
        print("PROBLEM:", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
