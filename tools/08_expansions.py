"""Drugs that won approval for something new in the window, and the products with many approvals.

openFDA labels each approved supplement's class; "Efficacy" supplements are the ones that carry new
indications, but they also carry new populations and dosing, so counts are efficacy supplements, not
a clean count of indications. For the busiest products the ClinicalTrials.gov history is crawled and
grouped by condition, which shows the pipeline hanging off one product.
"""
import collections, concurrent.futures as cf, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json
from taxonomy import parent, TA_OVERRIDE, condition_group
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


def conditions_matrix(studies):
    """Studies -> one row per condition group with counts by phase and status."""
    rows = collections.defaultdict(lambda: dict(p1=0, p2=0, p3=0, active=0, done=0, halted=0, last=0, first=9999))
    for s in studies:
        lv = 3 if "PHASE3" in s["phases"] else 2 if "PHASE2" in s["phases"] else 1
        y = int(s["start"][:4]) if s["start"][:4].isdigit() else None
        for g in {condition_group(c) for c in s["cond"]}:
            r = rows[g]
            r[f"p{lv}"] += 1
            st = s["status"]
            r["active"] += st in trials_active
            r["halted"] += st in ("TERMINATED", "WITHDRAWN", "SUSPENDED")
            r["done"] += st == "COMPLETED"
            if y:
                r["last"], r["first"] = max(r["last"], y), min(r["first"], y)
    out = [dict(g=g, **r) for g, r in rows.items()]
    out.sort(key=lambda r: -(r["p1"] + r["p2"] + r["p3"]))
    return out[:30]


trials_active = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}


def pipeline(p):
    rt, _, brand = trials.roots(p["ingredient"], p["brand"])
    toks = rt + [brand.lower()]
    got = {}
    for t in toks:
        for s in trials.fetch(t, cap_pages=6):
            sl = trials.slim(s)
            got[sl["id"]] = sl
    sts = [s for s in got.values() if s["cls"] == "INDUSTRY" and trials.mentions(s, toks)]
    return dict(n=len(sts), conds=conditions_matrix(sts))


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
        return TA_OVERRIDE.get(bid) or classify.ta_of(r), classify.modality(r), r["use"]

    with cf.ThreadPoolExecutor(6) as ex:
        labs = list(ex.map(label_of, rows))
    for a, (ta, mod, use) in zip(rows, labs):
        a.update(ta=ta, modality=mod, use=use[:200], company=parent(a["sponsor"]), id=re.sub(r"[^a-z0-9]+", "-", a["brand"].lower()).strip("-") + "-" + a["app"].lower())
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
