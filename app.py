import altair as alt
import pandas as pd
import requests
import streamlit as st

from cms_api import (
    care_compare_link,
    fetch_facility_claims,
    fetch_provider,
    national_averages,
    state_averages,
)
from docx_report import build_docx
from pdf_report import build_pdf
from report_data import rating_int


@st.cache_data(show_spinner=False)
def _national():
    return national_averages()


@st.cache_data(show_spinner=False)
def _state(state):
    return state_averages(state)


CLAIMS_CHARTS = [
    ("Short-Term Hospitalization", "521", "%"),
    ("Short-Term ED Visit", "522", "%"),
    ("Long-Term Hospitalization", "551", "per 1,000 days"),
    ("Long-Term ED Visit", "552", "per 1,000 days"),
]
SOURCES = ["Facility", "State", "National"]
SOURCE_COLORS = ["#0B7285", "#F5B301", "#6C757D"]


def _metric_df(claims, code):
    return pd.DataFrame({
        "Source": SOURCES,
        "Score": [claims[s.lower()].get(code) for s in SOURCES],
    })


def _metric_chart(claims, code):
    return (
        alt.Chart(_metric_df(claims, code))
        .mark_bar()
        .encode(
            x=alt.X("Source:N", sort=SOURCES, title=None),
            y=alt.Y("Score:Q", title=None),
            color=alt.Color(
                "Source:N",
                scale=alt.Scale(domain=SOURCES, range=SOURCE_COLORS),
                legend=None,
            ),
        )
        .properties(height=200)
    )


def _legend_html():
    items = "".join(
        f'<span style="display:inline-flex;align-items:center;margin:0 12px;">'
        f'<span style="width:12px;height:12px;background:{c};display:inline-block;'
        f'margin-right:6px;border-radius:2px;"></span>{name}</span>'
        for name, c in zip(SOURCES, SOURCE_COLORS)
    )
    return f'<div style="text-align:center;margin:2px 0 10px;">{items}</div>'


def _rating_card(label, value):
    n = rating_int(value)
    if n is None:
        stars, sub = '<span style="color:#888">N/A</span>', ""
    else:
        stars = (
            f'<span style="color:#F5B301">{"★" * n}</span>'
            f'<span style="color:#3a3f44">{"★" * (5 - n)}</span>'
        )
        sub = f'<div style="font-size:13px;color:#9aa3ab">{n} / 5</div>'
    return (
        '<div style="text-align:center;padding:10px 4px;">'
        f'<div style="font-size:13px;color:#9aa3ab;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:26px;letter-spacing:3px;line-height:1;">{stars}</div>'
        f'{sub}</div>'
    )


def _render_charts(report):
    st.subheader("Star ratings")
    cards = [
        ("Overall", report["overall_rating"]),
        ("Health Inspection", report["health_inspection_rating"]),
        ("Staffing", report["staffing_rating"]),
        ("Quality of Care", report["quality_rating"]),
    ]
    for col, (label, value) in zip(st.columns(4), cards):
        col.markdown(_rating_card(label, value), unsafe_allow_html=True)

    claims = report.get("claims")
    if claims:
        st.subheader("Hospitalization & ED metrics vs. benchmarks")
        st.caption("Lower is better — facility compared to its state and national averages.")
        st.markdown(_legend_html(), unsafe_allow_html=True)
        cols = st.columns(2) + st.columns(2)
        for col, (label, code, unit) in zip(cols, CLAIMS_CHARTS):
            col.markdown(f"**{label}** ({unit})")
            col.altair_chart(_metric_chart(claims, code), use_container_width=True)


st.set_page_config(page_title="Facility Assessment Snapshot", page_icon="🏥", layout="centered")

st.markdown(
    """
    <div style="background:#0B7285;color:white;text-align:center;padding:14px;border-radius:6px;">
      <div style="font-size:22px;font-weight:700;">INFINITE — Managed by MEDELITE</div>
      <div style="font-size:14px;letter-spacing:2px;">FACILITY ASSESSMENT SNAPSHOT</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

ccn = st.text_input("CCN (CMS Certification Number)", placeholder="e.g. 686123").strip()

if st.button("Look up facility", type="primary") and ccn:
    try:
        with st.spinner("Fetching CMS data…"):
            provider = fetch_provider(ccn)
        if provider is None:
            st.error(f"No facility found for CCN {ccn}.")
            st.session_state.pop("provider", None)
        else:
            st.session_state.provider = provider
        st.session_state.pop("generated", None)
    except requests.RequestException as e:
        st.error(f"CMS API request failed: {e}")

provider = st.session_state.get("provider")

if provider:
    st.success(f"Loaded: {provider['name']}  ·  {provider['state']}")

    with st.form("report"):
        st.subheader("Report inputs")
        name = st.text_input("Facility name (override)", value=provider["name"])
        location = st.text_input("Location", value=provider["address"])
        emr = st.text_input("EMR", placeholder="e.g. PCC, MatrixCare")
        col1, col2 = st.columns(2)
        census_capacity = col1.text_input("Census Capacity", value=provider["certified_beds"])
        current_census = col2.text_input("Current Census", placeholder="e.g. 112")
        patient_type = st.text_input("Type of Patient", placeholder="e.g. Long-term & Short-term")
        prev_coverage = st.selectbox("Previous Coverage from Medelite", ["Yes", "No"])
        prev_performance = st.text_input(
            "Previous Provider Performance from Medelite", placeholder="e.g. About 30 patients/day"
        )
        medical_coverage = st.text_input("Medical Coverage", placeholder="e.g. Optometry, PCP, Podiatry")
        submitted = st.form_submit_button("Generate report", type="primary")

    if submitted:
        report = {
            "ccn": provider["ccn"],
            "state": provider["state"],
            "name": name,
            "location": location,
            "emr": emr,
            "census_capacity": census_capacity,
            "current_census": current_census,
            "patient_type": patient_type,
            "prev_coverage": prev_coverage,
            "prev_performance": prev_performance,
            "medical_coverage": medical_coverage,
            "overall_rating": provider["overall_rating"],
            "health_inspection_rating": provider["health_inspection_rating"],
            "staffing_rating": provider["staffing_rating"],
            "quality_rating": provider["quality_rating"],
            "source_url": care_compare_link(provider["ccn"]),
        }
        with st.spinner("Compiling report and computing benchmark averages…"):
            report["claims"] = {
                "facility": fetch_facility_claims(provider["ccn"]),
                "national": _national(),
                "state": _state(provider["state"]),
            }
            report["pdf"] = build_pdf(report)
            report["docx"] = build_docx(report)
        st.session_state.generated = report

    report = st.session_state.get("generated")
    if report and report["ccn"] == provider["ccn"]:
        _render_charts(report)
        st.write("")
        _, d1, d2, _ = st.columns([1, 3, 3, 1])
        d1.download_button(
            "⬇ Download PDF",
            data=report["pdf"],
            file_name=f"facility_snapshot_{report['ccn']}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
        d2.download_button(
            "⬇ Download Word (.docx)",
            data=report["docx"],
            file_name=f"facility_snapshot_{report['ccn']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True,
        )

    st.caption(f"Source: {care_compare_link(provider['ccn'])}")
