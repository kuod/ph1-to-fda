"""Drugs that won approval for something new in the window, and the products with many approvals.

openFDA labels each approved supplement's class; "Efficacy" supplements are the ones that carry new
indications, but they also carry new populations and dosing, so counts are efficacy supplements, not
a clean count of indications. For the busiest products the ClinicalTrials.gov history is crawled and
grouped by condition, which shows the pipeline hanging off one product.
"""
import collections, concurrent.futures as cf, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json
from taxonomy import parent, TA_OVERRIDE, condition_group, COND_GROUPS
import importlib.util


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


enrich, classify, trials = load("02_enrich"), load("03_classify"), load("04_trials_approved")
D = os.path.join(os.path.dirname(__file__), "..", "data")
OFDA = "https://api.fda.gov/drug/drugsfda.json"
W0, W1 = "20161021", "20261020"
TOP = 60


def fetch_apps(prefix):
    q = f"application_number:{prefix}* AND submissions.submission_class_code:EFFICACY AND submissions.submission_status_date:[{W0} TO {W1}]"
    out, skip = [], 0
    while True:
        d = get_json(OFDA, {"search": q, "limit": 1000, "skip": skip})
        out += d.get("results", [])
        skip += 1000
        if skip >= d["meta"]["results"]["total"]:
            return out


def summarise(a):
    subs = a.get("submissions", [])
    orig = sorted(s["submission_status_date"] for s in subs if s["submission_type"] == "ORIG" and s["submission_status"] == "AP")
    eff = [s for s in subs if s["submission_type"] == "SUPPL" and s.get("submission_class_code") == "EFFICACY"
           and s["submission_status"] == "AP" and W0 <= s["submission_status_date"] <= W1]
    p = a["products"][0]
    return dict(
        app=a["application_number"], brand=p["brand_name"].title(),
        ingredient=", ".join(x["name"].lower() for x in p.get("active_ingredients", []))[:80],
        sponsor=a["sponsor_name"], orig=orig[0] if orig else None,
        eff=[dict(d=f'{s["submission_status_date"][:4]}-{s["submission_status_date"][4:6]}-{s["submission_status_date"][6:]}',
                  n=s["submission_number"], pr=(s.get("review_priority") or "").title(),
                  o=any(x.get("code") == "Orphan" for x in s.get("submission_property_type", []))) for s in sorted(eff, key=lambda s: s["submission_status_date"])])


def full_label(brand, ingredient):
    """Newest label's complete Indications and Usage text (enrich.label truncates to 600 characters)."""
    b = re.sub(r"\s*\(.*?\)", "", brand).upper()
    for q in (f'openfda.brand_name:"{b}"', f'openfda.generic_name:"{re.split(r"[ ,]", ingredient.lower())[0]}"'):
        try:
            d = get_json("https://api.fda.gov/drug/label.json", {"search": q, "limit": 5})
        except RuntimeError:
            continue
        res = [r for r in d.get("results", []) if r.get("indications_and_usage")]
        if res:
            return " ".join(max(res, key=lambda r: r.get("effective_time", ""))["indications_and_usage"])[:30000]
    return ""


def in_label(group, label):
    """Does the product's current label mention this condition? (keyword match: approximate)"""
    rx = dict(COND_GROUPS).get(group)
    if rx:
        return bool(re.search(rx, label, re.I))
    words = [w for w in re.findall(r"[a-z]{5,}", group.lower()) if w not in ("cancer", "disease", "syndrome", "patients", "disorder")]
    return bool(words) and any(w in label.lower() for w in words)


def conditions_matrix(studies, label=""):
    """Studies -> one row per condition group with counts by phase and status, a label flag and the halted studies."""
    rows = collections.defaultdict(lambda: dict(p1=0, p2=0, p3=0, active=0, done=0, halted=0, last=0, first=9999, h=[]))
    for s in studies:
        lv = 3 if "PHASE3" in s["phases"] else 2 if "PHASE2" in s["phases"] else 1
        y = int(s["start"][:4]) if s["start"][:4].isdigit() else None
        for g in {condition_group(c) for c in s["cond"]}:
            r = rows[g]
            r[f"p{lv}"] += 1
            st = s["status"]
            r["active"] += st in trials_active
            if st in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
                r["halted"] += 1
                hy = int(s["end"][:4]) if s["end"][:4].isdigit() and int(s["end"][:4]) <= 2026 else y
                r["h"].append(dict(id=s["id"], ph=lv, y=hy, st=st.title(), why=(s["why"] or "")[:160]))
            r["done"] += st == "COMPLETED"
            if y:
                r["last"], r["first"] = max(r["last"], y), min(r["first"], y)
    out = [dict(g=g, lab=in_label(g, label), **dict(r, h=sorted(r["h"], key=lambda x: (not x["why"], -x["y"] if x["y"] else 0))[:8])) for g, r in rows.items()]
    out.sort(key=lambda r: -(r["p1"] + r["p2"] + r["p3"]))
    return out[:30]


trials_active = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}


def pipeline(p):
    p["label"] = full_label(p["brand"], p["ingredient"]) or p.get("label", "")
    rt, _, brand = trials.roots(p["ingredient"], p["brand"])
    toks = rt + [brand.lower()]
    got = {}
    for t in toks:
        for s in trials.fetch(t, cap_pages=6):
            sl = trials.slim(s)
            got[sl["id"]] = sl
    sts = [s for s in got.values() if s["cls"] == "INDUSTRY" and trials.mentions(s, toks)]
    halts = collections.Counter()
    for s in sts:
        if s["status"] in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
            y = s["end"][:4] if s["end"][:4].isdigit() and int(s["end"][:4]) <= 2026 else s["start"][:4]
            if y.isdigit():
                halts[y] += 1
    return dict(n=len(sts), conds=conditions_matrix(sts, p.get("label", "")), hy=dict(sorted(halts.items())))


def main():
    novel = {a["app"]: a["id"] for a in json.load(open(os.path.join(D, "approvals_clean.json"))) if a["app"]}
    apps = [summarise(a) for pre in ("NDA", "BLA") for a in fetch_apps(pre)]
    apps = [a for a in apps if a["eff"]]
    print(len(apps), "applications with efficacy supplements in the window")
    rows = []
    for a in apps:
        a["novel"] = novel.get(a["app"])
        a["earlier"] = bool(a["orig"] and a["orig"] < W0) or (a["orig"] is None and not a["novel"])
        if not a["novel"] and not a["earlier"]:
            continue  # a first approval inside the window that is not on the novel list (e.g. 505(b)(2) or new formulation)
        rows.append(a)

    def label_of(a):
        lb = enrich.label(a["brand"], a["ingredient"])
        r = dict(brand=a["brand"], ingredient=a["ingredient"], use=classify.clean_use(lb["ind"]), epc=lb["epc"], label_ind=lb["ind"], app=a["app"])
        bid = re.sub(r"[^a-z0-9]+", "-", a["brand"].lower()).strip("-")
        return TA_OVERRIDE.get(bid) or classify.ta_of(r), classify.modality(r), r["use"], lb["ind"]

    with cf.ThreadPoolExecutor(6) as ex:
        labs = list(ex.map(label_of, rows))
    for a, (ta, mod, use, lab) in zip(rows, labs):
        a.update(ta=ta, modality=mod, use=use[:200], label=lab[:8000], company=parent(a["sponsor"]), id=re.sub(r"[^a-z0-9]+", "-", a["brand"].lower()).strip("-") + "-" + a["app"].lower())
    rows.sort(key=lambda a: -len(a["eff"]))
    top = [a for a in rows if len(a["eff"]) >= 3][:TOP]
    with cf.ThreadPoolExecutor(4) as ex:
        for a, pl in zip(top, ex.map(pipeline, top)):
            a["pipeline"] = pl
    print(len(rows), "products;", sum(1 for a in rows if a["earlier"]), "approved before the window;", len(top), "with pipelines")
    print([(a["brand"], len(a["eff"])) for a in rows[:15]])
    json.dump(rows, open(os.path.join(D, "expansions.json"), "w"))


if __name__ == "__main__":
    main()
