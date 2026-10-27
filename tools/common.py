"""Shared helpers: cached HTTP GETs so the pipeline is re-runnable and polite."""
import hashlib, json, os, re, sys, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from config import START_YMD

CACHE = os.environ.get("PH1_TO_FDA_CACHE") or os.environ.get("EASY_AS_CACHE") or os.path.join(os.path.dirname(__file__), "..", ".cache")
os.makedirs(CACHE, exist_ok=True)
UA = {"User-Agent": "ph1-to-fda-research/1.0 (github.com/kuod/ph1-to-fda)"}


def get_json(url, params=None, retries=5, pause=0.0):
    key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=90)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(3 * (i + 1))
            continue
        if r.status_code == 404:
            data = {"_404": True}
            break
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (i + 1))
            continue
        r.raise_for_status()
        data = r.json()
        break
    else:
        raise RuntimeError(f"failed {url} {params}")
    with open(path, "w") as f:
        json.dump(data, f)
    if pause:
        time.sleep(pause)
    return data


def get_text(url, retries=4, max_age_hours=None):
    """Cached GET. Pages that change (the current year's approvals table, CBER pages) pass max_age_hours so a re-run cannot serve stale data."""
    key = hashlib.sha1(url.encode()).hexdigest()
    path = os.path.join(CACHE, key + ".html")
    if os.path.exists(path) and (max_age_hours is None or time.time() - os.path.getmtime(path) < max_age_hours * 3600):
        return open(path).read()
    for i in range(retries):
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=90)
        if r.status_code == 200:
            open(path, "w").write(r.text)
            return r.text
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed {url}")


_MKT = {}


def marketed_before(word, cutoff=START_YMD):
    """True if an NDA/BLA with this active ingredient (or brand) was approved before the window opened.
    Ingredient search uses a stem wildcard so salt/ester names still match (isavuconazole ~ isavuconazonium)."""
    word = re.sub(r"[^A-Za-z]", "", word)
    if len(word) < 6:
        return False
    if word not in _MKT:
        stem = word.upper()[: max(7, len(word) - 3)]
        hit = False
        for q in (f'products.active_ingredients.name:{stem}*', f'products.brand_name:"{word.upper()}"'):
            try:
                d = get_json("https://api.fda.gov/drug/drugsfda.json", {"search": q, "limit": 100})
            except RuntimeError:
                continue
            dates = [s["submission_status_date"] for a in d.get("results", []) for s in a.get("submissions", [])
                     if s["submission_type"] == "ORIG" and s["submission_status"] == "AP" and a["application_number"][:3] in ("NDA", "BLA")]
            hit = hit or (bool(dates) and min(dates) < cutoff)
        _MKT[word] = hit
    return _MKT[word]
