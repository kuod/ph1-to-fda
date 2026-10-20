"""Shared helpers: cached HTTP GETs so the pipeline is re-runnable and polite."""
import hashlib, json, os, time, requests

CACHE = os.environ.get("EASY_AS_CACHE", os.path.join(os.path.dirname(__file__), "..", ".cache"))
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
        except requests.exceptions.ConnectionError:
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


def get_text(url, retries=4):
    key = hashlib.sha1(url.encode()).hexdigest()
    path = os.path.join(CACHE, key + ".html")
    if os.path.exists(path):
        return open(path).read()
    for i in range(retries):
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=90)
        if r.status_code == 200:
            open(path, "w").write(r.text)
            return r.text
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed {url}")


_MKT = {}


def marketed_before(word, cutoff="20161021"):
    """True if an NDA/BLA for this active ingredient was approved before the window opened."""
    if word not in _MKT:
        d = get_json("https://api.fda.gov/drug/drugsfda.json", {"search": f'products.active_ingredients.name:"{word.upper()}"', "limit": 100})
        dates = [s["submission_status_date"] for a in d.get("results", []) for s in a.get("submissions", [])
                 if s["submission_type"] == "ORIG" and s["submission_status"] == "AP" and a["application_number"][:3] in ("NDA", "BLA")]
        _MKT[word] = bool(dates) and min(dates) < cutoff
    return _MKT[word]
