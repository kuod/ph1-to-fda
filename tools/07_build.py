"""Assemble everything the page needs into site data (data.js): approvals with trial
history and modelled revenue, pipeline programs for the alluvial, and company cards.

Revenue is MODELLED, not reported. Peak sales = therapeutic-area median x modifiers
(orphan, modality, review priority, sponsor scale), or an editorial peak for well-known
blockbusters; years 1-10 follow an S-shaped ramp. See the Method tab / README.
"""
import collections, datetime as dt, json, math, os, re, statistics, sys

sys.path.insert(0, os.path.dirname(__file__))
from reported_sales import REPORTED, SRC

D = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(os.path.dirname(__file__), "..", "data.js")
TODAY = dt.date.fromisoformat(os.environ.get("PH1_TO_FDA_TODAY", dt.date.today().isoformat()))  # drives years-elapsed and the page's end date
HALT = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}
BIG = {"Pfizer", "Merck & Co.", "Novartis", "Roche", "AstraZeneca", "GSK", "Sanofi", "Eli Lilly", "Bristol Myers Squibb", "Johnson & Johnson",
       "AbbVie", "Amgen", "Takeda", "Gilead Sciences", "Bayer", "Novo Nordisk", "Regeneron", "Boehringer Ingelheim", "Vertex", "Astellas",
       "Daiichi Sankyo", "Biogen", "Eisai", "UCB", "Otsuka", "Merck KGaA"}

TA_PEAK = {"Oncology": 700, "Immunology": 1200, "Metabolic & Endocrine": 600, "Neurology": 500, "Cardiovascular": 700,
           "Infectious disease": 300, "Hematology": 350, "Respiratory": 450, "Gastroenterology": 350, "Dermatology": 250,
           "Ophthalmology": 400, "Renal & Urology": 300, "Women's health": 200, "Musculoskeletal": 250, "Psychiatry": 400,
           "Pain & Anesthesia": 150, "Diagnostic imaging": 40, "Other": 150}
MOD_MULT = {"Blood / plasma product": 0.8, "Cell therapy": 0.9, "Gene therapy": 1.1, "Vaccine": 1.3, "Antibody / ADC": 1.3, "Protein / biologic": 1.1, "Oligonucleotide": 0.9, "Peptide": 1.0, "Radiopharmaceutical": 0.7, "Small molecule": 1.0}
# EDITORIAL peak-sales anchors ($M/yr), set by hand from recollection of public commentary and NOT sourced: they are tagged "editorial" on the page.
# A drug with a verified FY2025 figure in reported_sales.py gets a sourced floor under its peak (the peak is at least what was already sold). Everything else is modelled.
ANCHOR = {"ozempic": 18000, "mounjaro": 20000, "dupixent": 16000, "skyrizi": 18000, "biktarvy": 14000, "trikafta-copackaged": 12000, "rinvoq": 8000,
          "ocrevus": 7000, "vyndaqel": 6000, "verzenio": 5500, "imfinzi": 6000, "kisqali": 4500, "enhertu": 6000, "erleada": 3500,
          "tezspire": 2500, "nurtec-odt": 1500, "ubrelvy": 1200, "paxlovid": 6000, "veklury": 5600, "cabenuva": 2500, "rybrevant": 3500,
          "kerendia": 1000, "leqvio": 1200, "leqembi": 800, "camzyos": 1000, "reblozyl": 2500, "padcev": 2500, "polivy": 1500,
          "trodelvy": 1500, "tepezza": 1800, "evenity": 1200, "aimovig": 700, "emgality": 1100, "ajovy": 700, "xofluza": 1000,
          "evrysdi": 1800, "zeposia": 1000, "vabysmo": 4500, "olumiant": 1500, "calquence": 3500, "brukinsa": 3000, "jaypirca": 700,
          "lumakras": 500, "tukysa": 400, "libtayo": 1500, "darzalex-faspro": 0, "imbruvica": 0, "tecvayli": 900, "elrexfio": 400,
          "talvey": 400, "ohtuvayre": 800, "cobenfy": 1500, "journavx": 600, "rezdiffra": 1500, "wainua": 500, "amvuttra": 3000,
          "onpattro": 450, "givlaari": 250, "oxlumo": 300, "winrevair": 2500, "kesimpta": 0, "zepzelca": 350, "tagrisso": 0,
          "xtandi": 0, "lorbrena": 800, "scemblix": 1000, "welireg": 500, "tivdak": 150, "orserdu": 250, "krazati": 500,
          "veozah": 700, "lybalvi": 500, "caplyta": 1200, "qulipta": 1100, "zavzpret": 150, "adbry": 600, "ebglyss": 500,
          "nemluvio": 400, "sotyktu": 600, "litfulo": 400, "velsipity": 300, "omvoh": 1200, "entyvio": 0, "cibinqo": 300}
# CBER products (editorial peaks, $M/yr, approximate public sales to date)
ANCHOR.update({"comirnaty": 37000, "spikevax": 18000, "shingrix": 3800, "prevnar-20": 6000, "arexvy": 1500, "abrysvo": 1000, "capvaxive": 600,
               "kymriah": 600, "yescarta": 1500, "carvykti": 2000, "breyanzi": 1200, "abecma": 500, "tecartus": 450, "zolgensma": 1400,
               "luxturna": 80, "elevidys": 900, "hemgenix": 200, "casgevy": 400, "vyjuvek": 350, "adstiladrin": 300, "jynneos": 600,
               "heplisav-b": 300, "vaxelis": 400, "altuviiio": 1500, "haegarda": 600, "xembify": 400, "panzyga": 400, "jivi": 300, "esperoct": 300, "rebinyn": 150, "andexxa": 150, "kedrab": 150, "penbraya": 300, "nuvaxovid": 900, "mnexspike": 300, "amtagvi": 300, "roctavian": 50})
ANCHOR = {k: v for k, v in ANCHOR.items() if v}
SHAPE = {"comirnaty": [1.0, 0.55, 0.22, 0.14, 0.12, 0.1, 0.1, 0.1, 0.1, 0.1], "spikevax": [1.0, 0.4, 0.15, 0.12, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
         "paxlovid": [0.95, 0.9, 0.8, 0.7, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35],
         "veklury": [0.5, 1.0, 0.7, 0.4, 0.3, 0.25, 0.22, 0.2, 0.18, 0.16]}


def ramp(t_peak):
    fr = []
    for k in range(1, 11):
        x = 1 / (1 + math.exp(-(k - 0.55 * t_peak) / (0.18 * t_peak)))
        fr.append(x)
    top = fr[min(len(fr) - 1, int(t_peak))] if t_peak < 10 else fr[-1]
    return [min(1.0, f / max(fr[-1], 1e-9)) if t_peak >= 8 else min(1.0, f / top) for f in fr]


def revenue(a, npeers):
    bid = a["id"]
    orphan, ta, mod = a["orphan"], a["ta"], a["modality"]
    rep = REPORTED.get(bid)
    ed = ANCHOR.get(bid)
    if ed is not None:
        # reported sales already at or above the editorial peak make the peak sourced; otherwise the editorial figure stands, with the reported floor shown beside it
        peak, tag = (rep[0], "reported") if rep and rep[0] >= ed else (ed, "editorial")
    else:
        peak = TA_PEAK.get(ta, 150) * MOD_MULT.get(mod, 1.0) * (0.5 if orphan else 1.0) * (1.1 if a["priority"] == "Priority" else 1.0)
        size = 1.8 if a["company"] in BIG else 1.0 if npeers >= 3 else 0.65
        peak, tag = peak * size * 0.45, "model"  # 0.45 was set so the un-anchored tail sums to ~$60B of 2025 in-year sales: an assumed target, not a reported total (issue #4)
        if rep and rep[0] > peak:
            peak, tag = rep[0], "reported"
    t_peak = 4 if orphan else 5 if ta == "Oncology" else 7 if ta in ("Immunology", "Metabolic & Endocrine") else 6
    fr = SHAPE.get(bid) or ramp(t_peak)
    if bid not in SHAPE:
        fr = [fr[0] * 0.5] + fr[1:]  # launch year is a partial year
    mid = [round(peak * f, 1) for f in fr]
    lo, hi = 0.35, 2.6
    extra = dict(rep=rep[0], src=rep[1], note=rep[2]) if rep else {}
    if ed is not None:
        extra["ed"] = ed
    return dict(**extra, peak=round(peak), basis=tag, y=mid, lo=[round(v * lo, 1) for v in mid], hi=[round(v * hi, 1) for v in mid])


def reconcile(drugs, fy=2025):
    """Modelled calendar-fy sales of the drugs with a verified reported figure, against that figure. Also splits the modelled total by basis."""
    rows = []
    unsrc = []  # editorial anchors with no reported figure
    before = 0  # the same drugs and years with the editorial anchors alone (before the sourced floors)
    by_basis = collections.Counter()
    for d in drugs:
        k = fy - int(d["date"][:4])
        v = d["rev"]["y"][k] if 0 <= k < 10 else 0
        by_basis[d["rev"]["basis"]] += v
        r = d["rev"]
        if r["basis"] == "editorial" and "rep" not in r:
            unsrc.append(v)
        if "rep" in r:
            rows.append((d["id"], d["brand"], r["rep"], v))
            before += v * (r["ed"] / r["peak"]) if r.get("ed") else v
    tot = sum(by_basis.values())
    out = dict(fy=fy, n=len(rows), reported=round(sum(r[2] for r in rows)), modelled=round(sum(r[3] for r in rows)), modelledEditorial=round(before), unsourcedN=len(unsrc), unsourced=round(sum(unsrc)), total=round(tot),
               byBasis={b: round(v) for b, v in by_basis.items()})
    print(f"FY{fy} reconciliation: {len(rows)} drugs with a reported figure: reported ${out['reported']/1000:.1f}B vs modelled ${out['modelled']/1000:.1f}B; modelled total ${tot/1000:.0f}B ({', '.join(f'{b} ${v/1000:.0f}B' for b, v in by_basis.items())})")
    for r in sorted(rows, key=lambda r: -abs(r[3] - r[2]))[:12]:
        print(f"   {r[1]:14} reported {r[2]:>7,.0f}  modelled {r[3]:>7,.0f}  gap {r[3]-r[2]:>+8,.0f}")
    return out


def ymd(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s if len(s) == 10 else s + "-01")
    except ValueError:
        return None


def level(s):
    ph = set(s["phases"])
    return 3 if "PHASE3" in ph else 2 if "PHASE2" in ph else 1 if "PHASE1" in ph else 0


def trial_summary(a):
    appr = dt.date.fromisoformat(a["date"])
    ph = {1: [], 2: [], 3: []}
    studies = [s for s in a["studies"] if s["cls"] == "INDUSTRY"]  # development history: sponsor-run studies, not investigator-initiated ones
    if a.get("formulation"):  # new formulation/combination of a marketed component: keep only the sponsor's own studies
        words = {w for w in re.split(r"\W+", ((a["sponsor"] or "") + " " + a["company"]).lower()) if len(w) > 3 and w not in ("pharma", "therapeutics", "inc")}
        studies = [s for s in studies if any(w in s["sponsor"].lower() for w in words)]
    a = dict(a, studies=studies)
    for s in studies:
        d = ymd(s["start"])
        lv = level(s)
        if d and lv and d <= appr:
            ph[lv].append((d, s))
    out = {}
    for lv in (1, 2, 3):
        ss = sorted(ph[lv], key=lambda x: x[0])
        out[f"p{lv}"] = dict(n=len(ss), halted=sum(1 for _, s in ss if s["status"] in HALT), first=ss[0][0].isoformat()[:7] if ss else None)
    halted = [dict(id=s["id"], ph=lv, st=s["status"].title(), why=(s["why"] or "")[:140], sp=s["sponsor"][:30], yr=d.year)
              for lv in (1, 2, 3) for d, s in ph[lv] if s["status"] in HALT]
    halted.sort(key=lambda h: (-bool(h["why"]), h["ph"]))
    out["halted"] = halted[:6]
    firsts = [dt.date.fromisoformat(out[f"p{lv}"]["first"] + "-01") for lv in (1, 2, 3) if out[f"p{lv}"]["first"]]
    out["devYears"] = round((appr - min(firsts)).days / 365.25, 1) if firsts else None
    out["entry"] = next((lv for lv in (1, 2, 3) if out[f"p{lv}"]["n"]), None)
    out["conds"] = [c for c, _ in collections.Counter(c for s in studies for c in s["cond"]).most_common(2)]
    return out


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k of n, as [lo, hi] rounded to 3 places (None when n is 0)."""
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


# Published funnel benchmarks, each checked against the source document (see issue #3). They are shown beside our pooled rates on the Method tab.
# BIO/Informa/QLS: phase-by-phase transitions for all programs Biomedtracker tracked, 2011-2020 (Fig. 1 and Fig. 5 tables). Note its 57.8% is Phase III -> NDA/BLA
# filing; Phase III -> approval is 52.4% (its table of LOA from Phase III), and 7.9% is the LOA from Phase I.
# Wong, Siah & Lo 2019 (corrected Table 1): path-by-path POS, all indications, industry-sponsored, 2000-2015 data.
BENCH = [
    dict(id="bio2021", name="BIO / Informa / QLS 2021", span="2011-2020", p1=0.520, p2=0.289, p3=0.524, hit=0.079,
         cite="BIO, Informa Pharma Intelligence and QLS Advisors, Clinical Development Success Rates and Contributing Factors 2011-2020 (February 2021): Phase I to II 52.0% (n=4,414), II to III 28.9% (n=4,933), III to NDA/BLA 57.8% (n=1,928) and NDA/BLA to approval 90.6%; likelihood of approval from Phase III 52.4%, from Phase I 7.9% (n=12,728).",
         url="https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf"),
    dict(id="wong2019", name="Wong, Siah & Lo 2019", span="2000-2015", p1=0.664, p2=0.583, p3=0.590, hit=0.138,
         cite="Wong CH, Siah KW, Lo AW. Estimation of clinical trial success rates and related parameters. Biostatistics 2019;20(2):273-286, corrected Table 1 (path-by-path, all indications): Phase 1 to 2 66.4%, 2 to 3 58.3%, 3 to approval 59.0%, Phase 1 to approval 13.8%.",
         url="https://doi.org/10.1093/biostatistics/kxx069"),
]
DEEP_MIN = 50  # a sponsor with at least this many resolved programs counts as well covered (the cards' "Thin sample" line)


def pooled(coh):
    """Pooled funnel rates over resolved (not ongoing) cohort programs, with Wilson intervals."""
    res = [p for p in coh if p["outcome"] != "ongoing"]
    r2 = [p for p in res if p["reached"] >= 2]
    r3 = [p for p in res if p["reached"] >= 3]
    ok = [p for p in res if p["outcome"] == "approved"]
    ok3 = [p for p in r3 if p["outcome"] == "approved"]
    out = dict(n=len(res), approved=len(ok), r2=len(r2), r3=len(r3), ok3=len(ok3))
    for k, a, b in (("p1", len(r2), len(res)), ("p2", len(r3), len(r2)), ("p3", len(ok3), len(r3)), ("hit", len(ok), len(res))):
        out[k] = round(a / b, 4) if b else None
        out[k + "ci"] = wilson(a, b)
    return out


def funnel_stats(progs):
    """Pooled rates for the whole cohort, for well-covered sponsors only, and for the splits that show how much each known bias moves them."""
    coh = [p for p in progs if p["cohort"]]
    res = collections.Counter(p["company"] for p in coh if p["outcome"] != "ongoing")
    deep = {c for c, n in res.items() if n >= DEEP_MIN}
    appr = [p for p in coh if p["outcome"] == "approved"]
    yr = lambda p: p["first"]["1"][:4]
    return dict(
        all=pooled(coh), deep=pooled([p for p in coh if p["company"] in deep]), thin=pooled([p for p in coh if p["company"] not in deep]),
        early=pooled([p for p in coh if yr(p) <= "2013"]), late=pooled([p for p in coh if yr(p) >= "2014"]),
        deepMin=DEEP_MIN, deepSponsors=len(deep), sponsors=len(res),
        approvedNoCode=sum(1 for p in appr if not p["code"]), approvedN=len(appr))


def card(company, drugs, progs):
    coh = [p for p in progs if p["company"] == company and p["cohort"]]
    res = [p for p in coh if p["outcome"] != "ongoing"]
    r2 = [p for p in res if p["reached"] >= 2]
    r3 = [p for p in res if p["reached"] >= 3]
    ok = [p for p in res if p["outcome"] == "approved"]
    ok3 = [p for p in r3 if p["outcome"] == "approved"]
    rate = lambda n, d: round(n / d, 3) if d else None
    dev = [d["trials"]["devYears"] for d in drugs if d["trials"]["devYears"] is not None]
    by_y = collections.Counter(d["year"] for d in drugs)
    return dict(
        company=company, approvals=len(drugs), byYear=[by_y.get(y, 0) for y in range(2016, 2027)],
        orphan=round(sum(d["orphan"] for d in drugs if d["center"] != "CBER") / max(1, sum(1 for d in drugs if d["center"] != "CBER")), 2),
        topTA=collections.Counter(d["ta"] for d in drugs).most_common(1)[0][0],
        topMod=collections.Counter(d["modality"] for d in drugs).most_common(1)[0][0],
        medDev=round(statistics.median(dev), 1) if dev else None,
        cohortN=len(coh), resolvedN=len(res), ongoingN=len(coh) - len(res),
        hit=rate(len(ok), len(res)), hitci=wilson(len(ok), len(res)),
        p1=rate(len(r2), len(res)), p1n=[len(r2), len(res)], p1ci=wilson(len(r2), len(res)),
        p2=rate(len(r3), len(r2)), p2n=[len(r3), len(r2)], p2ci=wilson(len(r3), len(r2)),
        p3=rate(len(ok3), len(r3)), p3n=[len(ok3), len(r3)], p3ci=wilson(len(ok3), len(r3)),
        flagship=max(drugs, key=lambda d: d["rev"]["peak"])["brand"],
        rev10=round(sum(sum(d["rev"]["y"]) for d in drugs)),
    )


def main():
    ap = json.load(open(os.path.join(D, "trials_approved_raw.json")))
    progs = json.load(open(os.path.join(D, "programs.json")))
    peers = collections.Counter(a["company"] for a in ap)
    ids = {a["id"] for a in ap}
    missing = [k for k in list(ANCHOR) + list(SHAPE) if k not in ids]
    if missing:  # a typo here silently drops a blockbuster back to the generic model
        sys.exit("ANCHOR/SHAPE keys match no drug id: " + ", ".join(missing))
    drugs = []
    for a in ap:
        t = trial_summary(a)
        e = (TODAY - dt.date.fromisoformat(a["date"])).days / 365.25
        d = dict(id=a["id"], brand=a["brand"], ingredient=a["ingredient"].split(",")[0][:48], date=a["date"], year=a["year"], company=a["company"],
                 sponsor=a["sponsor"], ta=a["ta"], modality=a["modality"], use=a["use"], priority=a["priority"] or "Standard",
                 orphan=a["orphan"], app=a["app"], trials=t, elapsed=round(e, 1), center=a.get("center", "CDER"))
        d["rev"] = revenue(a, peers[a["company"]])
        drugs.append(d)
    pr = [dict(company=p["company"], name=p["name"], reached=p["reached"], outcome=p["outcome"], ta=p["ta"], approved=p["approved"],
               y=int(p["first"]["1"][:4]) if p["first"]["1"] else None, st=p["started"], ha=p["halted"], cd=p["conds"], why=p["why"][:1]) for p in progs if p["cohort"]]
    counts = collections.Counter(d["company"] for d in drugs)
    cards = [card(c, [d for d in drugs if d["company"] == c], progs) for c, n in counts.items() if n >= 6 and c in BIG]
    cards.sort(key=lambda c: -c["approvals"])
    # approvals won in the window by drugs first approved earlier (the toggle), and the products with many approvals
    ex = json.load(open(os.path.join(D, "expansions.json")))
    by_novel = {e["novel"]: e for e in ex if e["novel"]}
    for d in drugs:
        e = by_novel.get(d["id"])
        d["supps"] = None if d["center"] == "CBER" else [x["d"][:7] for x in e["eff"]] if e else []  # supplement data is CDER-only
    yr = lambda e: [int(x["d"][:4]) for x in e["eff"]]
    expansions = [dict(id=e["id"], brand=e["brand"], ingredient=e["ingredient"].split(",")[0][:40], company=e["company"], ta=e["ta"], modality=e["modality"],
                       first=e["orig"][:4] if e["orig"] else None, use=e["use"], d=[x["d"][:7] for x in e["eff"]],
                       prod=("pipeline" in e)) for e in ex if e["earlier"]]
    products = [dict(id=e["novel"] or e["id"], brand=e["brand"], ingredient=e["ingredient"].split(",")[0][:40], company=e["company"], ta=e["ta"],
                     first=e["orig"][:4] if e["orig"] else None, novel=bool(e["novel"]), d=[x["d"][:7] for x in e["eff"]],
                     pr=sum(1 for x in e["eff"] if x["pr"] == "Priority"), orphan=sum(1 for x in e["eff"] if x["o"]), pipe=e["pipeline"])
                for e in ex if "pipeline" in e]
    for e in expansions:
        if e["prod"]:
            e["id"] = e["id"]
    recon = reconcile(drugs)
    meta = dict(built=TODAY.isoformat(), from_="2016-10-21", n=len(drugs), cohort="2009-2018", programs=len(pr), expansions=len(expansions), recon=recon, src=SRC,
                funnel=dict(funnel_stats(progs), bench=BENCH))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("window.DATA=" + json.dumps(dict(meta=meta, drugs=drugs, programs=pr, cards=cards, expansions=expansions, products=products), separators=(",", ":")) + ";\n")
    print(f"{len(drugs)} drugs, {len(pr)} cohort programs, {len(cards)} company cards; data.js {os.path.getsize(OUT)/1e6:.2f} MB")
    for y in range(2017, 2027):
        tot = 0
        for d in drugs:
            k = y - int(d["date"][:4])
            if 0 <= k < 10:
                tot += d["rev"]["y"][k]
        print(y, f"${tot/1000:.0f}B modelled in-year sales (year k = calendar offset)")
    print(sorted(((d["rev"]["peak"], d["brand"]) for d in drugs), reverse=True)[:12])


if __name__ == "__main__":
    main()
