"""Attach sponsor, review designations and label indication text to each approval (openFDA)."""
import json, os, re, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json

D = os.path.join(os.path.dirname(__file__), "..", "data")
DF = "https://api.fda.gov/drug/drugsfda.json"
LB = "https://api.fda.gov/drug/label.json"


def clean_brand(b):
    return re.sub(r"\s*\(.*?\)", "", b).strip()


def find_app(brand, date):
    b = clean_brand(brand).upper()
    for field in ("products.brand_name", "openfda.brand_name"):
        d = get_json(DF, {"search": f'{field}:"{b}"', "limit": 10})
        for a in d.get("results", []):
            for s in a["submissions"]:
                if s["submission_type"] == "ORIG" and s["submission_status"] == "AP":
                    sd = s["submission_status_date"]
                    if abs(int(sd[:4]) * 372 + int(sd[4:6]) * 31 + int(sd[6:]) - (int(date[:4]) * 372 + int(date[5:7]) * 31 + int(date[8:]))) <= 62:
                        return a, s
    return None, None


def label(brand, ingredient=""):
    b = clean_brand(brand).upper()
    r = {}
    tries = [f'openfda.brand_name:"{b}"', f'openfda.brand_name:{b.split()[0]}']
    ing = re.split(r"[ ,]", ingredient.lower())[0] if ingredient else ""
    if ing:
        tries += [f'openfda.generic_name:"{ing}"', f'openfda.substance_name:"{ing.upper()}"']
    for q in tries:
        d = get_json(LB, {"search": q, "limit": 1})
        if d.get("results") and d["results"][0].get("indications_and_usage"):
            r = d["results"][0]
            break
    return {"ind": " ".join(r.get("indications_and_usage", []))[:600],
            "epc": (r.get("openfda", {}).get("pharm_class_epc") or [])[:3]}


def main():
    raw = json.load(open(os.path.join(D, "approvals_raw.json")))
    seen, rows = set(), []
    for r in sorted(raw, key=lambda r: r["date"]):
        key = r["ingredient"].split(",")[0].lower().split(" ")[0] if r["src"] != "fda-novel-list" else r["ingredient"].lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)
    miss = 0
    for r in rows:
        a, s = find_app(r["brand"], r["date"])
        if a:
            r["app"] = a["application_number"]
            r["sponsor_raw"] = a["sponsor_name"]
            r["priority"] = (s.get("review_priority") or "").title()
            r["orphan"] = any(p.get("code") == "Orphan" for p in s.get("submission_property_type", []))
        else:
            miss += 1
            r["sponsor_raw"] = None
        lb = label(r["brand"], r["ingredient"])
        r["label_ind"], r["epc"] = lb["ind"], lb["epc"]
        if not r.get("use"):
            r["use"] = re.sub(r"^INDICATIONS AND USAGE:?\s*(\d\.?\d?\s*)?", "", lb["ind"])[:240]
    print(len(rows), "approvals;", miss, "without openFDA match")
    for r in rows:
        if not r["sponsor_raw"]:
            print("  no sponsor:", r["brand"], r["date"])
    json.dump(rows, open(os.path.join(D, "approvals_enriched.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
