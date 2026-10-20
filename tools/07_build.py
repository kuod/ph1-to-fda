"""Assemble everything the page needs into site data (data.js): approvals with trial
history and modelled revenue, pipeline programs for the alluvial, and company cards.

Revenue is MODELLED, not reported. Peak sales = therapeutic-area median x modifiers
(orphan, modality, review priority, sponsor scale), or an editorial peak for well-known
blockbusters; years 1-10 follow an S-shaped ramp. See the Method tab / README.
"""
import collections, datetime as dt, json, math, os, re, statistics, sys

D = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(os.path.dirname(__file__), "..", "data.js")
TODAY = dt.date(2026, 10, 20)
HALT = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}
BIG = {"Pfizer", "Merck & Co.", "Novartis", "Roche", "AstraZeneca", "GSK", "Sanofi", "Eli Lilly", "Bristol Myers Squibb", "Johnson & Johnson",
       "AbbVie", "Amgen", "Takeda", "Gilead Sciences", "Bayer", "Novo Nordisk", "Regeneron", "Boehringer Ingelheim", "Vertex", "Astellas",
       "Daiichi Sankyo", "Biogen", "Eisai", "UCB", "Otsuka", "Merck KGaA"}

TA_PEAK = {"Oncology": 700, "Immunology": 1200, "Metabolic & Endocrine": 600, "Neurology": 500, "Cardiovascular": 700,
           "Infectious disease": 300, "Hematology": 350, "Respiratory": 450, "Gastroenterology": 350, "Dermatology": 250,
           "Ophthalmology": 400, "Renal & Urology": 300, "Women's health": 200, "Musculoskeletal": 250, "Psychiatry": 400,
           "Pain & Anesthesia": 150, "Diagnostic imaging": 40, "Other": 150}
MOD_MULT = {"Cell therapy": 0.9, "Gene therapy": 1.1, "Vaccine": 1.3, "Antibody / ADC": 1.3, "Protein / biologic": 1.1, "Oligonucleotide": 0.9, "Peptide": 1.0, "Radiopharmaceutical": 0.7, "Small molecule": 1.0}
# Editorial peak-sales anchors ($M/yr, approximate, from public commentary) for clear outliers; everything else is purely modelled.
ANCHOR = {"ozempic": 18000, "mounjaro": 20000, "dupixent": 16000, "skyrizi": 18000, "biktarvy": 14000, "trikafta": 12000, "rinvoq": 8000,
          "ocrevus": 7000, "vyndaqel": 6000, "verzenio": 5500, "imfinzi": 6000, "kisqali": 4500, "enhertu": 6000, "erleada": 3500,
          "tezspire": 2500, "nurtec": 1500, "ubrelvy": 1200, "paxlovid": 6000, "veklury": 5600, "cabenuva": 2500, "rybrevant": 3500,
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
               "heplisav-b": 300, "vaxelis": 400, "penbraya": 300, "nuvaxovid": 900, "mnexspike": 300, "amtagvi": 300, "roctavian": 50})
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
    if bid in ANCHOR:
        peak, tag = ANCHOR[bid], "anchor"
    else:
        peak = TA_PEAK.get(ta, 150) * MOD_MULT.get(mod, 1.0) * (0.5 if orphan else 1.0) * (1.1 if a["priority"] == "Priority" else 1.0)
        size = 1.8 if a["company"] in BIG else 1.0 if npeers >= 3 else 0.65
        peak, tag = peak * size * 0.45, "model"  # 0.45 calibrates the un-anchored tail to ~$60B of 2025 in-year sales
    t_peak = 4 if orphan else 5 if ta == "Oncology" else 7 if ta in ("Immunology", "Metabolic & Endocrine") else 6
    fr = SHAPE.get(bid) or ramp(t_peak)
    if bid not in SHAPE:
        fr = [fr[0] * 0.5] + fr[1:]  # launch year is a partial year
    mid = [round(peak * f, 1) for f in fr]
    lo, hi = 0.35, 2.6
    return dict(peak=round(peak), basis=tag, y=mid, lo=[round(v * lo, 1) for v in mid], hi=[round(v * hi, 1) for v in mid])


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
        hit=rate(len(ok), len(res)),
        p1=rate(len(r2), len(res)), p1n=[len(r2), len(res)],
        p2=rate(len(r3), len(r2)), p2n=[len(r3), len(r2)],
        p3=rate(len(ok3), len(r3)), p3n=[len(ok3), len(r3)],
        flagship=max(drugs, key=lambda d: d["rev"]["peak"])["brand"],
        rev10=round(sum(sum(d["rev"]["y"]) for d in drugs)),
    )


def main():
    ap = json.load(open(os.path.join(D, "trials_approved_raw.json")))
    progs = json.load(open(os.path.join(D, "programs.json")))
    peers = collections.Counter(a["company"] for a in ap)
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
    meta = dict(built=TODAY.isoformat(), from_="2016-10-21", n=len(drugs), cohort="2009-2018", programs=len(pr), expansions=len(expansions))
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
