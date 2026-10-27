"""Shared refresh configuration (tools/config.json): the approval window and as-of date.

Every pipeline step imports from here instead of hard-coding dates.
"""
import datetime as dt, json, os

_C = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))

START = dt.date.fromisoformat(_C["window_start"])
ASOF = dt.date.fromisoformat(os.environ.get("PH1_TO_FDA_TODAY") or _C["as_of"] or dt.date.today().isoformat())
COHORT_FROM, COHORT_TO = _C["cohort_from"], _C["cohort_to"]
CRAWL_FROM, CRAWL_TO = _C["crawl_from"], _C["crawl_to"]
START_YMD = START.strftime("%Y%m%d")
ASOF_YMD = ASOF.strftime("%Y%m%d")
