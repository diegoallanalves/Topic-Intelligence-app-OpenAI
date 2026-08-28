from __future__ import annotations

import html
import re
import pandas as pd
import plotly.express as px
import streamlit as st

from classifier import classify_dataframe
from topics import TOPICS
from utils import normalize_required_columns, to_excel_bytes, trap_audit

st.set_page_config(page_title="Topic Intelligence App", page_icon="🧭", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.5rem}.hero{background:linear-gradient(100deg,#edf5ff,#f6f0ff);border:1px solid #d6e5ff;border-radius:18px;padding:16px 20px;margin-bottom:16px}
.card{border-radius:16px;padding:15px 17px;margin:7px 0 12px;border-left:7px solid;box-shadow:0 4px 16px rgba(0,0,0,.055)}
.blue{background:#eaf3ff;border-color:#2f80ed}.green{background:#eafbf1;border-color:#27ae60}.purple{background:#f3ecff;border-color:#8e44ad}.orange{background:#fff4e5;border-color:#f2994a}.red{background:#ffecec;border-color:#eb5757}
.label{font-size:.77rem;font-weight:800;letter-spacing:.055em;text-transform:uppercase;opacity:.72}.body{font-size:.94rem;line-height:1.45;margin-top:5px}.main{font-size:1.03rem;font-weight:700;line-height:1.4;margin-top:5px}
[data-testid="stMetric"]{background:#f8faff;border:1px solid #e1e8f5;padding:12px;border-radius:14px}
</style>
""", unsafe_allow_html=True)


def esc(v):
    return html.escape("" if pd.isna(v) else str(v))


def card(label, body, css="blue", main=False):
    klass = "main" if main else "body"
    st.markdown(f'<div class="card {css}"><div class="label">{esc(label)}</div><div class="{klass}">{esc(body)}</div></div>', unsafe_allow_html=True)


def get_key():
    try:
        return str(st.secrets.get("OPENAI_API_KEY", ""))
    except Exception:
        return ""


st.title("🧭 Topic Intelligence App")
st.markdown('<div class="hero"><b>Provision-first Congressional policy classification.</b> Read <b>Mechanism → Analytical Summary → Title</b>, extract what the bill legally does, then assign exactly one of the 22 approved topics.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Upload")
    uploaded = st.file_uploader("Upload master Excel", type=["xlsx", "xls"])
    st.caption("Required: Mechanism, Analytical Summary, Title")
    st.divider()
    st.header("🔐 OpenAI")
    saved_key = get_key()
    if saved_key:
        st.success("API key detected in Streamlit Secrets")
        api_key = saved_key
    else:
        api_key = st.text_input("OpenAI API key", type="password", help="Not saved by the app or GitHub.")
    model = st.text_input("Model", value="gpt-5.6-terra", help="Change this if your API project uses another available model.")
    retries = st.select_slider("Retries", [0,1,2,3], value=2)
    st.divider()
    st.caption("The full classification policy lives in classification_policy.md. No TF-IDF score chooses the topic.")

if uploaded is None:
    st.info("👈 Upload an Excel file to begin.")
    st.stop()

try:
    raw = normalize_required_columns(pd.read_excel(uploaded))
except Exception as exc:
    st.error(f"Could not read Excel: {exc}")
    st.stop()

missing = [c for c in ["Mechanism","Analytical Summary","Title"] if c not in raw.columns]
if missing:
    st.error("Missing required column(s): " + ", ".join(missing))
    st.stop()

st.success(f"Loaded {len(raw):,} rows × {len(raw.columns):,} columns")
with st.expander("Preview source data"):
    cols = [c for c in ["Congress","Bill","Title","Mechanism","Analytical Summary"] if c in raw.columns]
    st.dataframe(raw[cols].head(15), use_container_width=True, hide_index=True)

if "classified" not in st.session_state:
    st.session_state.classified = None

if st.button(f"✨ Classify {len(raw):,} rows with OpenAI", type="primary", use_container_width=True, disabled=not bool(api_key)):
    progress = st.progress(0)
    status = st.empty()
    def update(done,total,msg):
        progress.progress(0 if total == 0 else min(done/total,1.0)); status.caption(msg)
    with st.spinner("Extracting provisions and applying the 22-topic policy…"):
        st.session_state.classified = classify_dataframe(raw, api_key, model.strip(), update, int(retries))
    progress.progress(1.0)

if not api_key:
    st.warning("Add an API key in the sidebar, or configure OPENAI_API_KEY in Streamlit Secrets.")

if st.session_state.classified is None:
    st.caption("No API request is made until you press Classify.")
    st.stop()

df = st.session_state.classified
valid = df[df["Topic"].isin(TOPICS)].copy()
errors = int((df["Classification Error"].astype(str).str.len()>0).sum())
warnings = int((df["Classification Warning"].astype(str).str.len()>0).sum())
review = int(valid["Topic Confidence"].isin([50,70]).sum())

st.divider(); st.header("📌 Classification overview")
a,b,c,d,e = st.columns(5)
a.metric("Rows",len(df)); b.metric("Classified",len(valid)); c.metric("Topics",f"{valid['Topic'].nunique()}/22"); d.metric("Review 50/70",review); e.metric("Errors / warnings",f"{errors} / {warnings}")

if len(valid):
    counts = valid["Topic"].value_counts().rename_axis("Topic").reset_index(name="Bills")
    t1,t2,t3,t4 = st.tabs(["Topic ranking","Composition","Confidence","Transformer-trap audit"])
    with t1:
        fig=px.bar(counts.sort_values("Bills"),x="Bills",y="Topic",orientation="h",text="Bills",color="Bills",color_continuous_scale="Blues",title="Bills by assigned topic")
        fig.update_layout(height=max(560,31*len(counts)),yaxis_title="",coloraxis_showscale=False); st.plotly_chart(fig,use_container_width=True)
    with t2:
        x,y=st.columns(2)
        with x:
            fig=px.pie(counts,names="Topic",values="Bills",hole=.52,title="Topic share"); st.plotly_chart(fig,use_container_width=True)
        with y:
            fig=px.treemap(counts,path=["Topic"],values="Bills",color="Bills",color_continuous_scale="Viridis",title="Topic treemap"); st.plotly_chart(fig,use_container_width=True)
    with t3:
        conf=valid["Topic Confidence"].value_counts().reindex([50,70,85,95],fill_value=0).rename_axis("Confidence").reset_index(name="Bills")
        fig=px.bar(conf,x="Confidence",y="Bills",text="Bills",color="Confidence",color_continuous_scale="RdYlGn",title="Policy-rubric confidence"); fig.update_layout(coloraxis_showscale=False); st.plotly_chart(fig,use_container_width=True)
    with t4:
        audit=trap_audit(valid); st.caption("Audit only — these terms never choose the topic. This shows whether known consequence-language terms survive into the extracted legal provision.")
        long=audit.melt(id_vars="Term",value_vars=["Source mentions","Provision mentions"],var_name="Location",value_name="Rows")
        fig=px.bar(long,x="Term",y="Rows",color="Location",barmode="group",text="Rows",title="Source text vs extracted provision"); st.plotly_chart(fig,use_container_width=True); st.dataframe(audit,use_container_width=True,hide_index=True)

st.divider(); st.header("🔎 Evidence Explorer")
explore=valid.copy()
f1,f2,f3=st.columns([1.6,1,1])
with f1: query=st.text_input("Search",placeholder="bill, provision, mechanism…")
with f2: topic_filter=st.selectbox("Topic",["All topics"]+TOPICS)
with f3: review_only=st.toggle("50 / 70 only")
if query.strip():
    p=re.escape(query.strip()); mask=pd.Series(False,index=explore.index)
    for col in [c for c in ["Bill","Title","Provision","Mechanism","Analytical Summary"] if c in explore.columns]: mask |= explore[col].fillna("").astype(str).str.contains(p,case=False,regex=True)
    explore=explore.loc[mask]
if topic_filter!="All topics": explore=explore[explore["Topic"]==topic_filter]
if review_only: explore=explore[explore["Topic Confidence"].isin([50,70])]

if len(explore):
    labels={i:f"{r.get('Bill',i)} | {str(r['Title'])[:75]} → {r['Topic']}" for i,r in explore.head(1500).iterrows()}
    idx=st.selectbox("Choose a row",list(labels),format_func=lambda i:labels[i]); row=explore.loc[idx]
    left,right=st.columns([1.35,1],gap="large")
    with left:
        st.subheader("Source text"); card("Mechanism — first source",row.get("Mechanism",""),"orange",True); card("Analytical Summary — gap fill / confirmation",row.get("Analytical Summary",""),"purple"); card("Title — tie-break / fallback",row.get("Title",""),"blue")
    with right:
        st.subheader("Classification evidence"); conf=int(row["Topic Confidence"]); css="green" if conf in [85,95] else ("orange" if conf==70 else "red")
        card("Extracted PROVISION",row["Provision"],"green",True); card("Assigned TOPIC",row["Topic"],"blue",True); card("TOPIC_CONFIDENCE",conf,css); card("TOPIC_RUNNER_UP",row["Topic Runner-Up"],"purple")
        if str(row.get("Classification Warning","")).strip(): card("Validation warning",row["Classification Warning"],"orange")

st.divider(); st.header("🧪 Human review queue")
queue=df[df["Topic Confidence"].isin([50,70]) | (df["Classification Warning"].astype(str).str.len()>0) | (df["Classification Error"].astype(str).str.len()>0)]
qcols=[c for c in ["Topic Confidence","Topic","Topic Runner-Up","Provision","Congress","Bill","Title","Classification Warning","Classification Error"] if c in queue.columns]
if len(queue): st.dataframe(queue[qcols],use_container_width=True,hide_index=True,height=380)
else: st.success("No 50/70 rows, warnings or errors.")

st.divider(); st.header("📦 Processed data")
show=[c for c in ["Topic","Provision","Topic Confidence","Topic Runner-Up","Congress","Bill","Title","Mechanism","Analytical Summary"] if c in df.columns]
st.dataframe(df[show],use_container_width=True,hide_index=True,height=460)
st.download_button("⬇️ Download post-processed Excel",to_excel_bytes(df),"Topic_Intelligence_Classified.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary",use_container_width=True)
st.caption("The workbook keeps the original columns, adds the classification fields, and includes a Human Review worksheet.")
