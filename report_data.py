CLAIMS_LAYOUT = [
    ("Short Term Hospitalization", "facility", "521", "percent"),
    ("STR National Avg. for Hospitalization", "national", "521", "percent"),
    ("STR State National Avg. for Hospitalization", "state", "521", "percent"),
    ("STR ED Visit", "facility", "522", "percent"),
    ("STR ED Visits National Avg.", "national", "522", "percent"),
    ("STR ED Visits State Avg.", "state", "522", "percent"),
    ("LT Hospitalization", "facility", "551", "rate"),
    ("LT National Avg. for Hospitalization", "national", "551", "rate"),
    ("LT State National Avg. for Hospitalization", "state", "551", "rate"),
    ("ED Visit", "facility", "552", "rate"),
    ("LT ED Visits National Avg.", "national", "552", "rate"),
    ("LT ED Visits State Avg.", "state", "552", "rate"),
]


def rating_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def star_text(value):
    n = rating_int(value)
    if n is None:
        return str(value) if value else "N/A"
    return f"{'★' * n}{'☆' * (5 - n)}  ({n}/5)"


def fmt_claim(value, kind):
    if value is None:
        return "N/A"
    return f"{value:.1f}%" if kind == "percent" else f"{value:.2f}"


def build_rows(data):
    rows = [
        ("field", "Name of Facility", data.get("name", "")),
        ("field", "Location", data.get("location", "")),
        ("field", "EMR", data.get("emr", "")),
        ("field", "Census Capacity", str(data.get("census_capacity", ""))),
        ("field", "Current Census", str(data.get("current_census", ""))),
        ("field", "Type of Patient", data.get("patient_type", "")),
        ("field", "Previous Coverage from Medelite", data.get("prev_coverage", "")),
        ("field", "Previous Provider Performance from Medelite", data.get("prev_performance", "")),
        ("field", "Medical Coverage", data.get("medical_coverage", "")),
        ("rating", "Overall Star Rating", data.get("overall_rating")),
        ("rating", "Health Inspection", data.get("health_inspection_rating")),
        ("rating", "Staffing", data.get("staffing_rating")),
        ("rating", "Quality of Resident Care", data.get("quality_rating")),
    ]
    claims = data.get("claims")
    if claims:
        rows.append(("section", "Hospitalization & ED Metrics", None))
        for label, scope, code, kind in CLAIMS_LAYOUT:
            rows.append(("field", label, fmt_claim(claims.get(scope, {}).get(code), kind)))
    return rows
