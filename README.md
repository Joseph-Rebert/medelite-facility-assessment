# Facility Assessment Snapshot Generator

A Streamlit micro-app for Medelite that looks up a skilled nursing facility by its
CCN (CMS Certification Number), pulls public CMS data, merges it with manual
operational inputs, and exports a polished, print-ready PDF report.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires Python 3.9+.

Test facility: CCN **686123** (Kendall Lakes Healthcare and Rehab Center, FL).

## How it works

- `cms_api.py` — queries the public CMS Provider Data Catalog datastore.
  - Provider Information dataset `4pq5-n9py`: name, address, certified beds,
    average residents/day, and the four star ratings.
  - Medicare Claims Quality Measures dataset `ijh5-nb2v`: the four facility
    hospitalization/ED measures (short-stay rehospitalization & outpatient ED,
    long-stay hospitalizations & outpatient ED per 1000 resident days).
- `report_data.py` — the shared, framework-neutral field/claims layout consumed by
  both exporters, so the PDF and Word documents never drift apart.
- `pdf_report.py` — renders the report with ReportLab. Bundles DejaVu Sans
  (`assets/fonts/`) so the star glyphs render reliably on any host.
- `docx_report.py` — renders the same report as an editable Word document.
- `app.py` — the Streamlit UI: CCN lookup, name override, manual inputs, rating
  cards, benchmark charts, and PDF / Word downloads.

## Bonus features

- **Word (.docx) export** alongside the PDF, from the same shared layout.
- **Charts & cards**: star ratings shown as metric cards, plus short-stay and
  long-stay hospitalization/ED metrics charted against the state and national
  benchmarks.
- **All 12 hospitalization/ED metrics** with computed state/national averages.

## Field mapping

| Report field | Source |
|---|---|
| Name of Facility | CMS API, with optional manual override |
| Location | CMS API (address, city, state) |
| Census Capacity | CMS `number_of_certified_beds` |
| Overall / Health Inspection / Staffing / Quality of Resident Care | CMS star ratings |
| EMR, Current Census, Type of Patient, Previous Coverage, Previous Provider Performance, Medical Coverage | Manual input |

## Engineering assumptions

- **Server-side API calls.** The CMS API does not send CORS headers, so a pure
  browser SPA cannot read it directly. Streamlit runs the requests server-side,
  which sidesteps the problem with no separate proxy.
- **Live data over the sample sheet.** The provided sample PDF for CCN 686123 is
  a stale snapshot (e.g. it shows 120 beds / overall ★1); the live CMS API now
  returns updated values (150 beds / overall ★5). The app reports current live
  data and treats the sample as a layout reference, not a value target.
- **Download flow.** "Generate PDF" compiles the report, then a "Download PDF"
  button serves the file — the idiomatic Streamlit pattern.
- **State & national averages are computed.** CMS publishes the four claims
  measures per facility but not as a clean per-measure average dataset, so the app
  computes the state and national averages as the mean of all facilities'
  adjusted scores for each measure (paginated in parallel, cached with
  `st.cache_data` so the national set is fetched once per session).

## Branding

The header (`INFINITE — Managed by MEDELITE` / `FACILITY ASSESSMENT SNAPSHOT` /
state) is static platform branding and is never overwritten by the facility name.
