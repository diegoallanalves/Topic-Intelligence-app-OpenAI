from __future__ import annotations

import html
import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from classifier import classify_dataframe
from topics import TOPICS
from utils import normalize_required_columns, to_excel_bytes, trap_audit


st.set_page_config(
    page_title="Topic Intelligence App",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2.5rem;}
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(246,248,252,.98));
    border: 1px solid rgba(18,59,109,.12);
    padding: 14px 16px;
    border-radius: 16px;
    box-shadow: 0 4px 18px rgba(0,0,0,.04);
}
.hero {
    background: linear-gradient(100deg,#EDF5FF,#F6F0FF);
    border:1px solid #D6E5FF;
    border-radius:18px;
    padding:16px 20px;
    margin: 0 0 16px 0;
}
.card {
    border-radius: 16px;
    padding: 15px 17px;
    margin: 7px 0 12px 0;
    border-left: 7px solid;
    box-shadow: 0 4px 16px rgba(0,0,0,.055);
}
.blue   {background:#EAF3FF; border-color:#2F80ED;}
.green  {background:#EAFBF1; border-color:#27AE60;}
.purple {background:#F3ECFF; border-color:#8E44AD;}
.orange {background:#FFF4E5; border-color:#F2994A;}
.red    {background:#FFECEC; border-color:#EB5757;}
.gray   {background:#F5F6F8; border-color:#7F8C8D;}
.card-label {font-size:.77rem; font-weight:800; letter-spacing:.055em; text-transform:uppercase; opacity:.72;}
.card-main {font-size:1.02rem; font-weight:700; margin-top:4px; line-height:1.35;}
.card-body {font-size:.92rem; line-height:1.45; margin-top:5px;}
.small-note {font-size:.84rem; opacity:.75;}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value) -> str:
    return html.escape("" if pd.isna(value) else str(value))


def card(label: str, body: str, css: str, main: bool = False):
    body_class = "card-main" if main else "card-body"
    st.markdown(
        f'<div class="card {css}"><div class="card-label">{esc(label)}</div>'
        f'<div class="{body_class}">{esc(body)}</div></div>',
        unsafe_allow_html=True,
    )


def get_secret_key() -> str:
    # Streamlit Cloud / local secrets first, then environment variable.
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return str(key)
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")


st.title("🧭 Topic Intelligence App")
st.markdown(
    '<div class="hero"><b>Provision-first policy classification.</b> '
    'The app reads <b>Mechanism → Analytical Summary → Title</b>, asks the OpenAI model '
    'to extract the operative legal provision, applies your 22-topic policy and strict '
    'tie-break ladder, then exposes the result for human audit.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("📂 1. Upload data")
    uploaded = st.file_uploader(
        "Upload master Excel file",
        type=["xlsx", "xls"],
        help="Required fields: Mechanism, Analytical Summary, Title.",
    )

    st.divider()
    st.header("🔐 2. OpenAI")
    secret_key = get_secret_key()
    if secret_key:
        st.success("API key detected securely.")
        api_key = secret_key
    else:
        api_key = st.text_input(
            "OpenAI API key",
            type="password",
            help="Used only for this Streamlit session. For deployment, use Streamlit Secrets.",
        )
        st.caption("Do not commit API keys to GitHub.")

    model = st.text_input(
        "Model",
        value="gpt-5.6-terra",
        help="Use a model available to your OpenAI API project. GPT-5.6 Terra is a balanced default.",
    )
    retries = st.select_slider("Retries on malformed output", options=[0, 1, 2, 3], value=2)

    st.divider()
    st.header("🧠 Method")
    st.caption(
        "Full classification_policy.md is sent as the instruction policy. "
        "No TF-IDF or keyword score decides the topic."
    )

    with st.expander("Required input fields"):
        st.code("Mechanism\nAnalytical Summary\nTitle", language=None)


if uploaded is None:
    st.info("👈 Upload the master Excel file to begin.")
    st.stop()

try:
    raw_df = normalize_required_columns(pd.read_excel(uploaded))
except Exception as exc:
    st.error(f"Could not read the Excel file: {exc}")
    st.stop()

missing = [c for c in ["Mechanism", "Analytical Summary", "Title"] if c not in raw_df.columns]
if missing:
    st.error("Missing required column(s): " + ", ".join(missing))
    st.stop()

st.success(f"Loaded {len(raw_df):,} rows × {len(raw_df.columns):,} columns.")

preview_cols = [c for c in ["Congress", "Bill", "Title", "Mechanism", "Analytical Summary"] if c in raw_df.columns]
with st.expander("Preview uploaded data", expanded=False):
    st.dataframe(raw_df[preview_cols].head(15), use_container_width=True, hide_index=True)

if "classified_df" not in st.session_state:
    st.session_state.classified_df = None
    st.session_state.source_signature = None

source_signature = (uploaded.name, len(raw_df), tuple(raw_df.columns))

run_col, clear_col = st.columns([3, 1])
with run_col:
    run = st.button(
        f"✨ Classify {len(raw_df):,} rows with OpenAI",
        type="primary",
        use_container_width=True,
        disabled=not bool(api_key),
    )
with clear_col:
    if st.button("Clear results", use_container_width=True):
        st.session_state.classified_df = None
        st.session_state.source_signature = None
        st.rerun()

if not api_key:
    st.warning("Add your OpenAI API key to enable classification.")

if run:
    progress = st.progress(0)
    status = st.empty()

    def update_progress(done: int, total: int, message: str):
        value = 0 if total == 0 else min(done / total, 1.0)
        progress.progress(value)
        status.caption(message)

    with st.spinner("Applying the provision-first classification policy…"):
        try:
            classified = classify_dataframe(
                raw_df,
                api_key=api_key,
                model=model.strip(),
                progress_callback=update_progress,
                max_retries=int(retries),
            )
            st.session_state.classified_df = classified
            st.session_state.source_signature = source_signature
            progress.progress(1.0)
            status.caption("Classification complete.")
        except Exception as exc:
            st.error(f"Classification stopped: {exc}")

df = st.session_state.classified_df
if df is None:
    st.caption(
        "The app only calls the API after you press the classification button, "
        "so uploading or exploring the page does not consume API calls."
    )
    st.stop()

if st.session_state.source_signature != source_signature:
    st.warning("You uploaded a different file. Press Classify to generate results for this file.")
    st.stop()

valid = df[df["Topic"].isin(TOPICS)].copy()
error_count = int((df["Classification Error"].astype(str).str.len() > 0).sum())
warning_count = int((df["Classification Warning"].astype(str).str.len() > 0).sum())
review_mask = valid["Topic Confidence"].isin([50, 70])
review_count = int(review_mask.sum())

st.divider()
st.header("📌 Classification overview")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Rows processed", f"{len(df):,}")
c2.metric("Successfully classified", f"{len(valid):,}")
c3.metric("Topics represented", f"{valid['Topic'].nunique()}/22" if len(valid) else "0/22")
c4.metric("Human review: 50/70", f"{review_count:,}")
c5.metric("Errors / warnings", f"{error_count} / {warning_count}")

if not len(valid):
    st.error("No valid classifications were produced. Open the Errors table below.")
else:
    counts = valid["Topic"].value_counts().rename_axis("Topic").reset_index(name="Bills")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Topic ranking", "Composition", "Confidence", "Congress × Topic", "Transformer-trap audit"]
    )

    with tab1:
        fig = px.bar(
            counts.sort_values("Bills"),
            x="Bills",
            y="Topic",
            orientation="h",
            text="Bills",
            color="Bills",
            color_continuous_scale="Blues",
            title="Bills by assigned topic",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=max(560, 31 * len(counts)),
            yaxis_title="",
            coloraxis_showscale=False,
            margin=dict(l=10, r=40, t=55, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        a, b = st.columns(2)
        with a:
            fig = px.pie(counts, names="Topic", values="Bills", hole=.52, title="Topic share")
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(height=520, legend=dict(orientation="h", y=-.2))
            st.plotly_chart(fig, use_container_width=True)
        with b:
            fig = px.treemap(
                counts,
                path=["Topic"],
                values="Bills",
                color="Bills",
                color_continuous_scale="Viridis",
                title="Topic treemap",
            )
            fig.update_layout(height=520, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        conf_counts = (
            valid["Topic Confidence"]
            .value_counts()
            .reindex([50, 70, 85, 95], fill_value=0)
            .rename_axis("Confidence")
            .reset_index(name="Bills")
        )
        a, b = st.columns(2)
        with a:
            fig = px.bar(
                conf_counts,
                x="Confidence",
                y="Bills",
                text="Bills",
                color="Confidence",
                color_continuous_scale="RdYlGn",
                title="Policy-rubric confidence",
            )
            fig.update_layout(coloraxis_showscale=False, height=430)
            st.plotly_chart(fig, use_container_width=True)
        with b:
            conf_topic = (
                valid.groupby("Topic", as_index=False)["Topic Confidence"]
                .mean()
                .sort_values("Topic Confidence")
            )
            fig = px.bar(
                conf_topic,
                x="Topic Confidence",
                y="Topic",
                orientation="h",
                color="Topic Confidence",
                color_continuous_scale="RdYlGn",
                title="Average rubric score by topic",
            )
            fig.update_layout(
                height=max(430, 28 * len(conf_topic)),
                yaxis_title="",
                xaxis_range=[45, 100],
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        if "Congress" not in valid.columns:
            st.info("No Congress column was found.")
        else:
            cross = valid.groupby(["Congress", "Topic"], dropna=False).size().reset_index(name="Bills")
            mode = st.radio("View", ["Stacked bars", "Heatmap"], horizontal=True)
            if mode == "Stacked bars":
                fig = px.bar(
                    cross, x="Congress", y="Bills", color="Topic",
                    title="Topic mix by Congress"
                )
                fig.update_layout(height=550)
            else:
                pivot = cross.pivot(index="Topic", columns="Congress", values="Bills").fillna(0)
                fig = px.imshow(
                    pivot,
                    aspect="auto",
                    text_auto=True,
                    color_continuous_scale="Blues",
                    title="Congress × Topic heatmap",
                )
                fig.update_layout(height=max(530, 30 * len(pivot)), yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    with tab5:
        audit = trap_audit(valid)
        st.markdown(
            "**Audit only — never used to choose the topic.** "
            "This compares how often known trap terms occur in the source text versus "
            "how often they survive into the extracted legal PROVISION."
        )
        long = audit.melt(
            id_vars="Term",
            value_vars=["Source mentions", "Provision mentions"],
            var_name="Location",
            value_name="Rows",
        )
        fig = px.bar(
            long,
            x="Term",
            y="Rows",
            color="Location",
            barmode="group",
            text="Rows",
            title="Did consequence-language terms survive into the provision?",
        )
        fig.update_layout(height=470)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(audit, use_container_width=True, hide_index=True)

st.divider()
st.header("🔎 Evidence Explorer")

explore = valid.copy()
f1, f2, f3 = st.columns([1.7, 1.1, 1])
with f1:
    query = st.text_input("Search", placeholder="Bill, title, provision, mechanism, summary…")
with f2:
    topic_filter = st.selectbox("Topic", ["All topics"] + TOPICS)
with f3:
    review_only = st.toggle("50 / 70 only")

if query.strip():
    pattern = re.escape(query.strip())
    search_cols = [c for c in ["Bill", "Title", "Provision", "Mechanism", "Analytical Summary"] if c in explore.columns]
    mask = pd.Series(False, index=explore.index)
    for col in search_cols:
        mask |= explore[col].fillna("").astype(str).str.contains(pattern, case=False, regex=True)
    explore = explore.loc[mask]

if topic_filter != "All topics":
    explore = explore.loc[explore["Topic"] == topic_filter]
if review_only:
    explore = explore.loc[explore["Topic Confidence"].isin([50, 70])]

st.caption(f"{len(explore):,} row(s) match.")

if len(explore):
    labels = {
        idx: f"{row.get('Bill', idx)} | {str(row['Title'])[:80]} → {row['Topic']}"
        for idx, row in explore.head(1500).iterrows()
    }
    idx = st.selectbox(
        "Choose a Congressional action",
        list(labels.keys()),
        format_func=lambda x: labels[x],
    )
    row = explore.loc[idx]

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("Source text")
        card("Mechanism — first source", row.get("Mechanism", ""), "orange", main=True)
        card("Analytical Summary — gap fill / confirmation", row.get("Analytical Summary", ""), "purple")
        card("Title — tie-break / named place / fallback", row.get("Title", ""), "blue")

    with right:
        st.subheader("Model output")
        conf = int(row["Topic Confidence"])
        conf_css = "green" if conf in (85, 95) else ("orange" if conf == 70 else "red")
        card("Extracted PROVISION", row["Provision"], "green", main=True)
        card("Assigned TOPIC", row["Topic"], "blue", main=True)
        card("TOPIC_CONFIDENCE", str(conf), conf_css)
        card("TOPIC_RUNNER_UP", row["Topic Runner-Up"], "purple")

        if str(row.get("Classification Warning", "")).strip():
            card("Validation warning", row["Classification Warning"], "orange")
        if str(row.get("Classification Error", "")).strip():
            card("Classification error", row["Classification Error"], "red")

st.divider()
st.header("🧪 Human review queue")
review = df[
    df["Topic Confidence"].isin([50, 70])
    | (df["Classification Warning"].astype(str).str.len() > 0)
    | (df["Classification Error"].astype(str).str.len() > 0)
].copy()

review_cols = [
    c for c in [
        "Topic Confidence", "Topic", "Topic Runner-Up", "Provision",
        "Congress", "Bill", "Title", "Classification Warning", "Classification Error"
    ] if c in review.columns
]
if len(review):
    st.dataframe(review[review_cols], use_container_width=True, hide_index=True, height=390)
else:
    st.success("No 50/70 rows, validation warnings, or classification errors.")

with st.expander("API / parser errors", expanded=False):
    errors = df[df["Classification Error"].astype(str).str.len() > 0]
    if len(errors):
        st.dataframe(
            errors[[c for c in ["Bill", "Title", "Classification Error"] if c in errors.columns]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No API/parser errors.")

st.divider()
st.header("📦 Processed data & download")

display_cols = [
    c for c in [
        "Topic", "Provision", "Topic Confidence", "Topic Runner-Up",
        "Congress", "Bill", "Title", "Mechanism", "Analytical Summary"
    ] if c in df.columns
]
st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=470)

excel_bytes = to_excel_bytes(df)
st.download_button(
    "⬇️ Download post-processed Excel",
    data=excel_bytes,
    file_name="Topic_Intelligence_Classified.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    use_container_width=True,
)

st.caption(
    "The Excel export keeps every original column and adds Topic, Provision, "
    "Topic Confidence, Topic Runner-Up, warnings/errors and raw model output. "
    "A separate Human Review worksheet contains the rows requiring attention."
)
