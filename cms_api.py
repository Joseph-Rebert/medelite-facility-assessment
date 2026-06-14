from concurrent.futures import ThreadPoolExecutor

import requests

BASE = "https://data.cms.gov/provider-data/api/1/datastore/query"
SQL = "https://data.cms.gov/provider-data/api/1/datastore/sql"
PROVIDER_DATASET = "4pq5-n9py"
CLAIMS_DATASET = "ijh5-nb2v"
CLAIMS_DIST = "19fa35fb-11f0-5ed8-999e-52f272a25b01"
PAGE = 1500
CARE_COMPARE_URL = "https://www.medicare.gov/care-compare/details/nursing-home/{ccn}"

CLAIMS_MEASURES = [
    ("521", "Short Term Hospitalization", "STR", "Hospitalization", "percent"),
    ("522", "STR ED Visit", "STR", "ED Visits", "percent"),
    ("551", "LT Hospitalization", "LT", "Hospitalization", "rate"),
    ("552", "ED Visit", "LT", "ED Visits", "rate"),
]


def _query(dataset, ccn):
    params = {
        "conditions[0][property]": "cms_certification_number_ccn",
        "conditions[0][value]": ccn,
        "conditions[0][operator]": "=",
    }
    r = requests.get(f"{BASE}/{dataset}/0", params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("results", [])


def fetch_provider(ccn):
    rows = _query(PROVIDER_DATASET, ccn)
    if not rows:
        return None
    r = rows[0]
    address = ", ".join(
        p for p in (r.get("provider_address"), r.get("citytown"), r.get("state")) if p
    )
    return {
        "ccn": ccn,
        "name": r.get("provider_name", "").title(),
        "legal_name": r.get("legal_business_name", ""),
        "address": address,
        "state": r.get("state", ""),
        "certified_beds": r.get("number_of_certified_beds", ""),
        "avg_residents_per_day": r.get("average_number_of_residents_per_day", ""),
        "overall_rating": r.get("overall_rating", ""),
        "health_inspection_rating": r.get("health_inspection_rating", ""),
        "staffing_rating": r.get("staffing_rating", ""),
        "quality_rating": r.get("qm_rating", ""),
    }


def care_compare_link(ccn):
    return CARE_COMPARE_URL.format(ccn=ccn)


def fetch_facility_claims(ccn):
    rows = _query(CLAIMS_DATASET, ccn)
    scores = {}
    for r in rows:
        score = r.get("adjusted_score")
        if score not in (None, ""):
            scores[r.get("measure_code")] = float(score)
    return scores


def _count(where):
    params = {"limit": 1, "results": "false"}
    for i, (prop, val) in enumerate(where):
        params[f"conditions[{i}][property]"] = prop
        params[f"conditions[{i}][value]"] = val
        params[f"conditions[{i}][operator]"] = "="
    r = requests.get(f"{BASE}/{CLAIMS_DATASET}/0", params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("count", 0)


def _page(where_sql, offset):
    q = f'[SELECT adjusted_score FROM {CLAIMS_DIST}][WHERE {where_sql}][LIMIT {PAGE} OFFSET {offset}]'
    r = requests.get(SQL, params={"query": q}, timeout=40)
    r.raise_for_status()
    return [float(x["Adjusted Score"]) for x in r.json() if x.get("Adjusted Score") not in (None, "")]


def _averages(state=None):
    def where_sql(code):
        clause = f'measure_code = "{code}"'
        return clause + f' AND state = "{state}"' if state else clause

    def conditions(code):
        c = [("measure_code", code)]
        return c + [("state", state)] if state else c

    with ThreadPoolExecutor(max_workers=4) as pool:
        counts = dict(zip(
            (c for c, *_ in CLAIMS_MEASURES),
            pool.map(lambda c: _count(conditions(c)), (c for c, *_ in CLAIMS_MEASURES)),
        ))

    tasks = [
        (code, off)
        for code, *_ in CLAIMS_MEASURES
        for off in range(0, counts.get(code, 0), PAGE)
    ]
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = pool.map(lambda t: (t[0], _page(where_sql(t[0]), t[1])), tasks)

    buckets = {code: [] for code, *_ in CLAIMS_MEASURES}
    for code, vals in results:
        buckets[code].extend(vals)
    return {code: (sum(v) / len(v) if v else None) for code, v in buckets.items()}


def national_averages():
    return _averages()


def state_averages(state):
    return _averages(state)
