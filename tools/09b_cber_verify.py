"""Re-check the CBER first-approval dates against FDA's own records.

Run after 09_cber.py (or any time; it only reads). Every entry in data/cber_curated.json is compared with the Original
approval date that FDA's Purple Book lists for its BLA. A mismatch fails the run unless the entry has a `note`
explaining which record was preferred (for example a replacement approval letter dated after the original).
"""
import csv, datetime as dt, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_text

D = os.path.join(os.path.dirname(__file__), "..", "data")
PB_PAGE = "https://purplebooksearch.fda.gov/downloads"


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
                print(f"  note kept: {name} curated {e['date']} vs Purple Book {d}")
            else:
                bad.append(f"{name}: curated {e['date']} but Purple Book says {d}, and the entry has no note")
        if e.get("purple_book") != (d.isoformat() if d else None):
            bad.append(f"{name}: purple_book field {e.get('purple_book')} is stale (file says {d})")
    print(len(cur), "curated products checked;", len(bad), "problems")
    for b in bad:
        print("PROBLEM:", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
