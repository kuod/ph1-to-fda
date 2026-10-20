"""Pull each approved drug's Phase 1-3 development history from ClinicalTrials.gov.

Pass 1 searches the INN/brand. Code names (e.g. MK-3475) that appear in the same
intervention as the INN are harvested and searched in pass 2, so early studies
registered under the code name are linked to the eventual approved drug.
"""
import concurrent.futures as cf, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json, marketed_before

D = os.path.join(os.path.dirname(__file__), "..", "data")
U = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = "NCTId,LeadSponsorName,LeadSponsorClass,Phase,OverallStatus,StartDate,CompletionDate,WhyStopped,InterventionName,InterventionOtherName,InterventionType,ArmGroupType,ArmGroupInterventionName,Condition,StudyType"
CODE = re.compile(r"\b([A-Z]{1,6}[- ]?\d{2,7}[A-Z]{0,3}(?:-\d{1,4})?)\b")
BAD_CODE = re.compile(r"^(PHASE|COVID|SARS|NCT|HIV|ISRCTN|GLP|II|III|IV|SGLT|CD|IL|IGG|HER|PD|TNF|EGFR|VEGF|BCL|BRAF|KRAS|MG|ML|HBV|HCV)-?\d")
FILTER = "AREA[StudyType]INTERVENTIONAL AND AREA[Phase](PHASE1 OR PHASE2 OR PHASE3)"


STOP = {"insulin", "sodium", "hydrochloride", "air", "fish", "ethinyl", "human", "recombinant", "factor", "acid", "oil", "vaccine", "alfa", "beta", "pegol"}


def roots(ing, brand):
    """Distinctive search words for each active; components already marketed before the window are
    dropped (they would drag in thousands of unrelated studies) unless that leaves nothing."""
    out = []
    for a in re.split(r",\s*|\s+and\s+", ing):
        ws = [re.sub(r"-[a-z]{4}$", "", w) for w in a.strip().split(" ") if not w.startswith("(")]
        w = next((w for w in ws if w.lower() not in STOP and len(w) > 4), None)
        if w and w not in out:
            out.append(w)
    novel = [w for w in out if not marketed_before(w)]
    return (novel or out), (not novel), re.sub(r"\s*\(.*?\)|\s+co-?pack.*", "", brand, flags=re.I).strip()


def fetch(term, cap_pages=4):
    studies, tok = [], None
    for _ in range(cap_pages):
        p = {"query.intr": term, "filter.advanced": FILTER, "pageSize": 1000, "fields": FIELDS}
        if tok:
            p["pageToken"] = tok
        d = get_json(U, p)
        studies += d.get("studies", [])
        tok = d.get("nextPageToken")
        if not tok:
            break
    return studies


def slim(s):
    p = s["protocolSection"]
    a = p.get("armsInterventionsModule", {})
    sc = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    sm = p.get("statusModule", {})
    return dict(
        id=p["identificationModule"]["nctId"], sponsor=sc.get("name", ""), cls=sc.get("class", ""),
        phases=p.get("designModule", {}).get("phases", []), status=sm.get("overallStatus", ""),
        start=sm.get("startDateStruct", {}).get("date", ""), end=sm.get("completionDateStruct", {}).get("date", ""),
        why=sm.get("whyStopped", ""),
        iv=[dict(n=i.get("name", ""), o=i.get("otherNames", []), t=i.get("type", "")) for i in a.get("interventions", [])],
        arms=[dict(t=g.get("type", ""), iv=g.get("interventionNames", [])) for g in a.get("armGroups", [])],
        cond=p.get("conditionsModule", {}).get("conditions", [])[:3],
    )


def mentions(st, toks):
    for i in st["iv"]:
        blob = " ".join([i["n"]] + i["o"]).lower()
        if any(t.lower() in blob for t in toks):
            return True
    return False


def codes_in(st, toks):
    out = set()
    for i in st["iv"]:
        names = [i["n"]] + i["o"]
        if any(t.lower() in " ".join(names).lower() for t in toks):
            for n in names:
                for m in CODE.findall(n.upper()):
                    out.add(m.replace(" ", "-"))
    return {c for c in out if not BAD_CODE.match(c)}


def one(a):
    rt, formulation, brand = roots(a["ingredient"], a["brand"])
    toks = rt + [brand.lower()]
    got = {}
    for t in toks:
        for s in fetch(t):
            got[s["protocolSection"]["identificationModule"]["nctId"]] = slim(s)
    sts = [s for s in got.values() if mentions(s, toks)]
    codes = set()
    for s in sts:
        codes |= codes_in(s, toks)
    for c in sorted(codes)[:6]:
        for s in fetch(c):
            sl = slim(s)
            if sl["id"] not in got and mentions(sl, [c]):
                got[sl["id"]] = sl
                sts.append(sl)
    a = dict(a)
    a["tokens"], a["codes"], a["studies"], a["formulation"] = toks, sorted(codes)[:6], sts, formulation or a.get("center") == "CBER"
    return a


def main():
    ap = json.load(open(os.path.join(D, "approvals_clean.json")))
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(one, ap))
    print(len(res), "drugs;", sum(1 for r in res if not r["studies"]), "with no registered studies;",
          sum(len(r["studies"]) for r in res), "study links")
    json.dump(res, open(os.path.join(D, "trials_approved_raw.json"), "w"))


if __name__ == "__main__":
    main()
