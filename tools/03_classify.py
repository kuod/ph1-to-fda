"""Parent company, therapeutic area, modality, and cleaned-up fields for every approval."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import parent, TA, MODALITY, TA_OVERRIDE, SPONSOR_OVERRIDE, PARENTS, CBER_TA, CBER_GENE

D = os.path.join(os.path.dirname(__file__), "..", "data")
DIAG = re.compile(r"\b(F[ -]?18|Ga[ -]?68|Cu[ -]?64|Tc[ -]?99m?|Zr[ -]?89|Lu[ -]?177|gallium|fluorine|technetium|flotufolastat|piflufolastat|fluciclovine)\b|diagnos|imaging|PET", re.I)


def clean_use(u):
    u = u.replace("\xa0", " ")
    u = re.sub(r"^\s*(INDICATIONS (AND|&) USAGE:?\s*)?\d?\.?\d*\s*(INDICATIONS (AND|&) USAGE:?\s*)?", "", u)
    u = re.sub(r"\s*Press Release.*$", "", u)
    return u[:240]


def ta_of(r):
    use = r["use"]
    text = " ".join([use, " ".join(r["epc"]), r["ingredient"]])
    if re.search(r"radioactive diagnostic|diagnostic (agent|radiopharm)|\bPET\b|positron emission|optical imaging|fluorescen\w+ imaging|\b(detect|visuali[sz]e|identify|imaging)\b.*\b(lesions?|tumou?rs?|lymph nodes?|plaque)", text) and not re.search(r"lutetium|\btreat", use, re.I):
        return "Diagnostic imaging"
    scores = []
    for name, rx in TA:
        if name == "Diagnostic imaging":
            continue
        # weight the short FDA use sentence 3x over the longer label text
        s = 3 * len(re.findall(rx, use, re.I)) + len(re.findall(rx, text, re.I))
        scores.append((s, -[n for n, _ in TA].index(name), name))
    scores.sort(reverse=True)
    return scores[0][2] if scores[0][0] > 0 else "Other"


def modality(r):
    app = r.get("app", "")
    ing = r["ingredient"].lower()
    if app.startswith("BLA"):
        if re.search(r"mab|cept\b|ximab|zumab|umab", ing):
            return "Antibody / ADC"
        if re.search(r"vedotin|deruxtecan|govitecan|tesirine|mafodotin|ozogamicin|tansine", ing):
            return "Antibody / ADC"
        return "Protein / biologic"
    if re.search(r"siran|sen sodium|rsen|ersen|sarsen|golodirsen|viltolarsen|nusinersen|inotersen|tofersen|eplontersen|olezarsen|eteplirsen|casimersen|volanesorsen|imetelstat|pegcetacoplan|avacincaptad|pegaptanib|defibrotide|aptamer", ing):
        return "Oligonucleotide"
    if re.search(r"\bf[- ]?18\b|ga[- ]?68|cu[- ]?64|lu[- ]?177|lutetium|gallium|tc[- ]?99|technetium|zirconium|flotufolastat|piflufolastat", ing):
        return "Radiopharmaceutical"
    if re.search(r"tide\b|tide acetate|glutide|pressin|relin|tocin|relix", ing):
        return "Peptide"
    return "Small molecule"


def main():
    rows = json.load(open(os.path.join(D, "approvals_enriched.json")))
    out = []
    for r in rows:
        bid = re.sub(r"[^a-z0-9]+", "-", r["brand"].lower()).strip("-")
        sp = r.get("sponsor_raw") or SPONSOR_OVERRIDE.get(bid)
        out.append(dict(
            id=re.sub(r"[^a-z0-9]+", "-", r["brand"].lower()).strip("-"),
            brand=re.sub(r"\s*\(.*?\)", "", r["brand"]).strip(),
            ingredient=r["ingredient"], date=r["date"], year=int(r["date"][:4]),
            sponsor=sp, company=parent(sp), use=clean_use(r["use"] if len(r["use"]) > 12 else r["ingredient"].capitalize()), ta=TA_OVERRIDE.get(bid) or ta_of(r), modality=modality(r),
            priority=r.get("priority", ""), orphan=bool(r.get("orphan")), app=r.get("app", ""),
        ))
    # CBER products (cell and gene therapy, vaccines): same record shape, area and modality set by hand, no review-priority or orphan data
    cb = os.path.join(D, "cber_raw.json")
    if os.path.exists(cb):
        for r in json.load(open(cb)):
            bid = re.sub(r"[^a-z0-9]+", "-", r["brand"].lower()).strip("-")
            if r["cat"] == "Vaccine":
                ta, mod = "Infectious disease", "Vaccine"
            elif r["cat"] == "Blood product":
                ta, mod = CBER_TA.get(bid) or "Hematology", "Blood / plasma product"
            else:
                ta = CBER_TA.get(bid) or ta_of(dict(use=r["use"], epc=[], ingredient=r["ingredient"], label_ind=r["use"]))
                mod = "Gene therapy" if bid in CBER_GENE else "Cell therapy"
            out.append(dict(id=bid, brand=r["brand"], ingredient=r["ingredient"], date=r["date"], year=int(r["date"][:4]), sponsor=r["sponsor"],
                            company=parent(r["sponsor"]), use=clean_use(r["use"]), ta=ta, modality=mod, priority="", orphan=False,
                            app=("BLA " + re.sub(r"\D", "", r["stn"])[:6]) if r["stn"] else "", center="CBER"))
    for o in out:
        o.setdefault("center", "CDER")
    # fold variants of one unmapped sponsor ("Ascendis" / "Ascendis Bone") into the shortest name
    fixed = {p for _, p in PARENTS}
    names = sorted({o["company"] for o in out if o["company"] not in fixed}, key=len)
    fold = {n: next((m for m in names if m != n and n.startswith(m + " ")), n) for n in names}
    for o in out:
        o["company"] = fold.get(o["company"], o["company"])
    json.dump(out, open(os.path.join(D, "approvals_clean.json"), "w"), indent=1)
    import collections
    print(collections.Counter(o["ta"] for o in out).most_common())
    print(collections.Counter(o["modality"] for o in out).most_common())
    print(collections.Counter(o["company"] for o in out).most_common(40))
    print("Other:", [(o["brand"], o["use"][:60]) for o in out if o["ta"] == "Other"])


if __name__ == "__main__":
    main()
