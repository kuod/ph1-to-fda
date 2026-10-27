"""Group raw studies into drug programs and follow each through Ph1 -> Ph2 -> Ph3 -> approval.

Program identity: interventions in experimental arms are linked when they share an
intervention record (name + otherNames), e.g. "Ixekizumab" ~ "LY2439821". A program
is kept only when it carries one of its sponsor's own code prefixes (LY, PF, MK ...)
or matches an FDA approval, which screens out marketed comparators and add-on drugs.

Stage reached = the highest phase of any registered study, with Phase 1/2 counted as 2
and Phase 2/3 counted as 3. Outcome of a program that stopped short of approval:
  ongoing - a study is still active/recruiting (excluded from success-rate denominators)
  halted  - the last study at its highest phase was terminated/withdrawn/suspended
  stalled - studies completed (or status unknown) with no later phase registered
"""
import collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import TA
from common import get_json, marketed_before

D = os.path.join(os.path.dirname(__file__), "..", "data")
CODE = re.compile(r"\b([A-Z]{1,6})[- ]?(\d{2,7})([A-Z]{0,3})\b")
SKIP_PREFIX = {"PHASE", "COVID", "SARS", "NCT", "HIV", "II", "III", "IV", "HPV", "HBV", "HCV", "RSV", "CD", "IL", "PD", "TNF", "IGG", "IGE", "LDL", "HDL", "SC", "IV", "IM", "BID", "QD", "MG", "ML", "VEGF", "EGFR", "HER", "GLP", "DPP", "SGLT", "BCL", "BRAF", "KRAS", "MEK", "ALK", "NSCLC", "CTLA", "PCSK", "COX", "ACE", "ARB", "UK", "US", "EU", "ISRCTN", "WHO", "CAR"}
NOISE = re.compile(r"\b(placebo|matching|standard|care|therapy|treatment|injection|tablets?|capsules?|oral|solution|infusion|subcutaneous|intravenous|sc|iv|im|bid|qd|qw|q\dw|high|low|dose|doses|mg|mcg|ug|ml|vs|and|plus|control|comparator|arm|group|part|cohort|formulation|fasted|fed|single|multiple|ascending|reference|test|period|sequence)\b|[\d.]+\s*(mg|mcg|ug|g|ml|iu|%|kg)?", re.I)
ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "AVAILABLE"}
HALT = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}
# The funnel covers CDER products only. CBER products (vaccines, cell and gene therapy, blood products) are on the approval list, but the
# big-sponsor crawl finds only a few of their programs, so counting their failures without their successes would drag the hit rate down.
CBER = re.compile(r"vaccin|toxoid|conjugate|virus.like|mrna|\baav|adenovir|lentivir|\bad26\b|leucel|\bcar[- ]?t|-cel\b|cabtagene|cell therapy|gene therapy|immunoglobulin|\bivig\b|antihemophilic|factor (viii|ix|x)\b|coagulation factor|plasma|albumin|allergen|\bbcg\b|\bmenveo|denvax", re.I)
OK_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}
from config import COHORT_FROM, COHORT_TO
STEM = re.compile(r"(mab|nib|stat|vir|gliptin|gliflozin|tide|ase|cept|parib|ciclib|lisib|tinib|rsen|siran|dipine|sartan|prazole|mycin|statin|oxetine|zomib|lutamide|gliptin|limus|setron|pitant|gepant|degib|metinib|rafenib)$")


def level(s):
    ph = set(s["phases"])
    return 3 if "PHASE3" in ph else 2 if "PHASE2" in ph else 1 if "PHASE1" in ph else 0


def year(d):
    return int(d[:4]) if d and d[:4].isdigit() else None


def tokens(iv):
    """Normalised alias tokens for one intervention record."""
    out = set()
    for n in [iv["n"]] + list(iv["o"]):
        for m in CODE.finditer(n.upper()):
            if m.group(1) not in SKIP_PREFIX:
                out.add(f"{m.group(1)}{m.group(2)}{m.group(3)}")
        base = re.sub(r"\(.*?\)", " ", n)
        base = NOISE.sub(" ", base)
        base = re.sub(r"[^A-Za-z\- ]", " ", base).strip().lower()
        base = re.sub(r"\s+", " ", base)
        if 5 <= len(base) <= 40 and not CODE.fullmatch(base.upper()) and len(base.split()) <= 3:
            out.add(base)
    return out


def exp_ivs(s):
    names = set()
    for a in s["arms"]:
        if a["t"] == "EXPERIMENTAL":
            for x in a["iv"]:
                names.add(x.split(": ", 1)[-1].strip().lower())
    out = []
    for i in s["iv"]:
        if i["t"] in OK_TYPES and (not names or i["n"].strip().lower() in names):
            out.append(i)
    return out


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def ta_of_conditions(conds):
    text = " ".join(conds)
    best = max(((len(re.findall(rx, text, re.I)), -i, n) for i, (n, rx) in enumerate(TA) if n != "Diagnostic imaging"))
    return best[2] if best[0] > 0 else "Other"


def prefix_owner(sponsor_studies):
    """Learn each sponsor's own code prefixes: prefixes used mostly by that sponsor."""
    cnt = collections.defaultdict(collections.Counter)
    for sp, sts in sponsor_studies.items():
        for s in sts:
            seen = set()
            for iv in exp_ivs(s):
                for t in tokens(iv):
                    m = re.match(r"^([A-Z]{1,6})\d", t)
                    if m and (m.group(1), t) not in seen:
                        seen.add((m.group(1), t))
                        cnt[m.group(1)][sp] += 1
    own = collections.defaultdict(set)
    for pre, c in cnt.items():
        tot = sum(c.values())
        sp, n = c.most_common(1)[0]
        if tot >= 4 and n / tot >= 0.6:
            own[sp].add(pre)
    return own


def build():
    sponsor_studies = json.load(open(os.path.join(D, "trials_sponsors_raw.json")))
    approved = json.load(open(os.path.join(D, "trials_approved_raw.json")))
    own = prefix_owner(sponsor_studies)
    # approved-drug alias index: INN root, brand, and code names harvested from the registry
    atok = {}
    for a in approved:
        for t in set(a["tokens"]) | {c.replace("-", "") for c in a["codes"]}:
            atok.setdefault(t.lower(), []).append(a)
    programs = []
    for sp, sts in sponsor_studies.items():
        uf = UF()
        rec = []
        for s in sts:
            ivs = exp_ivs(s)
            toks_per = [tokens(i) for i in ivs]
            for ts in toks_per:
                ts = sorted(ts)
                for t in ts[1:]:
                    uf.union(ts[0], t)
            rec.append((s, [t for ts in toks_per for t in ts]))
        groups = collections.defaultdict(lambda: dict(toks=set(), studies={}))
        for s, ts in rec:
            for t in ts:
                g = groups[uf.find(t)]
                g["toks"].add(t)
                g["studies"][s["id"]] = s
        for root, g in groups.items():
            codes = [t for t in g["toks"] if re.match(r"^[A-Z]{1,6}\d", t)]
            if any(re.match(r"^([A-Z]{1,6})\d", c).group(1) in own[sp] for c in codes) or any(t.lower() in atok for t in g["toks"]):
                programs.append(dict(company=sp, toks=sorted(g["toks"]), studies=list(g["studies"].values()), own_code=True))
    for pr in programs:
        hit = None
        for t in pr["toks"]:
            for a in atok.get(t.lower(), []):
                hit = a
                break
            if hit:
                break
        if not hit:
            for t in pr["toks"]:
                for w in t.split():
                    for a in atok.get(w.lower(), []):
                        hit = a
                        break
        pr["approved"] = hit["id"] if hit else None
        pr["_ap"] = hit
    merged = {}
    rest = []
    for pr in programs:
        if pr["approved"]:
            k = (pr["company"], pr["approved"])
            if k in merged:
                m = merged[k]
                m["toks"] = sorted(set(m["toks"]) | set(pr["toks"]))
                m["studies"] = list({s["id"]: s for s in m["studies"] + pr["studies"]}.values())
            else:
                merged[k] = pr
        else:
            rest.append(pr)
    # an approval credited to several crawled sponsors (e.g. licensing partners) stays with the one holding the FDA application
    return rest + list(merged.values()), approved


def summarise(pr, ap_by_id):
    sts = pr["studies"]
    # approved programs: use the drug's full registry history (all sponsors) up to approval
    if pr["approved"]:
        a = ap_by_id[pr["approved"]]
        sts = {s["id"]: s for s in sts}
        for s in a["studies"]:
            sts.setdefault(s["id"], s)
        sts = list(sts.values())
    by = collections.defaultdict(list)
    for s in sts:
        by[level(s)].append(s)
    first = {}
    for lv in (1, 2, 3):
        ys = sorted(s["start"] for s in by.get(lv, []) if s["start"])
        first[lv] = ys[0] if ys else None
    reached = max(by) if by else 0
    started = {lv: len(by.get(lv, [])) for lv in (1, 2, 3)}
    halted = {lv: sum(1 for s in by.get(lv, []) if s["status"] in HALT) for lv in (1, 2, 3)}
    why = [s["why"] for s in by.get(reached, []) if s["status"] in HALT and s["why"]][:2]
    if pr["approved"]:
        outcome = "approved"
    else:
        top = by.get(reached, [])
        if any(s["status"] in ACTIVE for s in sts):
            outcome = "ongoing"
        else:
            last = sorted(top, key=lambda s: s["start"] or "")[-1] if top else None
            outcome = "halted" if last and last["status"] in HALT else "stalled"
    conds = collections.Counter(c for s in sts for c in s["cond"])
    return dict(reached=reached, started=started, halted=halted, first=first, outcome=outcome, why=why,
                conds=[c for c, _ in conds.most_common(3)], n=len(sts))


def cber_marketed():
    try:
        return set(json.load(open(os.path.join(D, "cber_marketed_names.json"))))
    except FileNotFoundError:
        return set()


def main():
    programs, approved = build()
    ap_by_id = {a["id"]: a for a in approved}
    out = []
    for pr in programs:
        sm = summarise(pr, ap_by_id)
        f1 = sm["first"][1]
        code = next((t for t in pr["toks"] if re.match(r"^[A-Z]{1,6}\d", t)), None)
        words = [t for t in pr["toks"] if not re.match(r"^[A-Z]{1,6}\d", t) and " " not in t and len(t) >= 6]
        inn = [t for t in words if STEM.search(t)]
        name = (inn or sorted(words, key=len))[:1]
        label = ap_by_id[pr["approved"]]["brand"] if pr["approved"] else (name[0].title() if name else code)
        out.append(dict(company=pr["company"], name=label, code=code, **sm,
                        approved=pr["approved"], ta=(ap_by_id[pr["approved"]]["ta"] if pr["approved"] else ta_of_conditions(sm["conds"])),
                        cohort=bool(f1 and COHORT_FROM <= year(f1) <= COHORT_TO)))
    # Drugs already marketed before the window would otherwise read as failures: drop programs whose INN has an older FDA approval.
    marketed = marketed_before

    cber_old = cber_marketed()  # CBER products not first approved in the window (their pages cannot be dated, so any listed product outside our set is treated as already marketed)
    n_pre = n_cber = 0
    for p, pr in zip(out, programs):
        if p["approved"]:
            continue
        names = " ".join([i["n"] + " " + " ".join(i["o"]) for s in pr["studies"] for i in s["iv"]])
        if CBER.search(names + " " + " ".join(pr["toks"])):
            p["cohort"], p["outcome"], n_cber = False, "cber", n_cber + 1
            continue
        words = {t for t in pr["toks"] if not re.match(r"^[A-Z]{1,6}\d", t) and " " not in t and len(t) >= 6}  # single-word aliases only: a multi-word token is usually a combination arm, and its partner drug says nothing about this program
        if any(marketed(w) or w.lower() in cber_old for w in words):
            p["cohort"], p["outcome"], n_pre = False, "premarketed", n_pre + 1
    print(n_pre, "programs dropped: ingredient or brand already FDA-approved before Oct 2016;", n_cber, "dropped as CBER products")
    # an approval matched under several crawled sponsors (licensing partners) stays with the company holding the FDA application
    home = {a["id"]: a["company"] for a in json.load(open(os.path.join(D, "approvals_clean.json")))}
    best = {}
    for p in out:
        if p["approved"]:
            k = p["approved"]
            score = (p["company"] == home.get(k), p["n"])
            if k not in best or score > best[k][0]:
                best[k] = (score, p)
    out = [p for p in out if not p["approved"] or best[p["approved"]][1] is p]
    for p in out:  # approved CBER products are matched but kept out of the funnel for the reason above
        if p["approved"] and ap_by_id[p["approved"]].get("center") == "CBER":
            p["cohort"], p["outcome"] = False, "cber"
    json.dump(out, open(os.path.join(D, "programs.json"), "w"))
    c = collections.Counter((p["company"], p["cohort"]) for p in out)
    coh = [p for p in out if p["cohort"]]
    print(len(out), "programs;", len(coh), "in Ph1 cohort", COHORT_FROM, "-", COHORT_TO)
    print(collections.Counter(p["outcome"] for p in coh))
    print("approved programs matched:", len({p["approved"] for p in out if p["approved"]}), "of", len(approved))


if __name__ == "__main__":
    main()
