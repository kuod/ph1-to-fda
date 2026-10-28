"""Report on the sponsor -> parent mapping (data/sponsor_parents.json): writes data/sponsor_review.json.

Sponsors come from data/approvals_clean.json and data/expansions.json. Four groups:

- mapped_no_shared_token: a rule credited the sponsor to a parent whose name shares no word with it (SEAGEN -> Pfizer). Most
  are real acquisitions; each one is a claim a human should be able to check, and a new one must be reviewed
  (tools/test_taxonomy.py fails until this file lists it).
- unmapped: no rule matched; the sponsor stands as its own parent under a cleaned name. Some of these are subsidiaries or
  were acquired by a larger company (see unverified_candidates in sponsor_parents.json).
- possible_variants: two different parent names that look like one company (a typo, or one name contained in the other).
- sponsor_variants: one parent reached through several sponsor strings (informational).

Run: python3 tools/sponsor_report.py
"""
import collections, difflib, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import AS_OF, GENERIC, match_rule

D = os.path.join(os.path.dirname(__file__), "..", "data")


def load(name):
    with open(os.path.join(D, name)) as f:
        return json.load(f)


def tokens(s):
    s = re.sub(r"[,.()/&-]", " ", (s or "").upper())
    s = re.sub(GENERIC, " ", s)
    return {t.lower() for t in s.split() if len(t) >= 3}


def share(a, b):
    """Two names share a word when a word of one starts with a word of the other (ModernaTX / Moderna)."""
    return any(x == y or (min(len(x), len(y)) >= 4 and (x.startswith(y) or y.startswith(x))) for x in tokens(a) for y in tokens(b))


def sponsor_rows():
    """{sponsor string: (company as shown on the page, [brands])} from the committed data files."""
    by = {}
    for o in load("approvals_clean.json"):
        by.setdefault(o["sponsor"] or "", (o["company"], []))[1].append(o["brand"])
    for e in load("expansions.json"):
        by.setdefault(e["sponsor"] or "", (e["company"], []))[1].append(e["brand"] + " (earlier-approved)")
    return by


def build():
    by = sponsor_rows()
    mapped, unmapped = [], []
    for sp, (company, brands) in sorted(by.items()):
        par, pat = match_rule(sp)
        row = dict(sponsor=sp, parent=company, brands=sorted(set(brands))[:6], n=len(brands))
        if pat is None:
            unmapped.append(row)
        elif not share(sp, par):
            mapped.append(dict(row, pattern=pat))
    names = collections.Counter(c for c, _ in by.values())
    variants = []
    ns = sorted(names)
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            ta, tb = tokens(a), tokens(b)
            if difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85 or (ta and tb and (ta <= tb or tb <= ta)):
                variants.append([a, b])
    multi = collections.defaultdict(list)
    for sp, (c, _) in by.items():
        multi[c].append(sp)
    spec = load("sponsor_parents.json")
    return dict(as_of=AS_OF, n_sponsor_strings=len(by), n_parents=len(names),
                mapped_no_shared_token=mapped, unmapped=unmapped, possible_variants=variants,
                sponsor_variants={p: sorted(s) for p, s in sorted(multi.items()) if len(s) > 1},
                unverified_candidates=spec.get("unverified_candidates", []))


def main():
    r = build()
    with open(os.path.join(D, "sponsor_review.json"), "w") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)
    print(f"as of {r['as_of']}: {r['n_sponsor_strings']} sponsor strings -> {r['n_parents']} parents")
    print(f"  {len(r['mapped_no_shared_token'])} mapped to a parent sharing no word with the sponsor (review each)")
    print(f"  {len(r['unmapped'])} sponsors with no rule (their own cleaned name is the parent)")
    print(f"  {len(r['possible_variants'])} possible variant pairs: {r['possible_variants']}")
    print(f"  {len(r['unverified_candidates'])} unverified candidate mappings listed in sponsor_parents.json")


if __name__ == "__main__":
    main()
