import streamlit as st
import fitz  # PyMuPDF
import json
import re
import time
import requests
from datetime import datetime
from groq import Groq

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactLens – Automated Fact Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #0e7c7b 100%);
  border-radius: 16px; padding: 2.4rem 2rem 1.8rem 2rem;
  margin-bottom: 1.8rem; color: white;
}
.main-header h1 { font-size: 2.3rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
.main-header p  { font-size: 1rem; color: #94d0cc; margin: 0.4rem 0 0 0; }

.stat-card {
  background: white; border-radius: 12px; padding: 1.1rem 1rem;
  border: 1px solid #e2e8f0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); text-align: center;
}
.stat-card .number { font-size: 2rem; font-weight: 700; }
.stat-card .label  { font-size: 0.75rem; color: #64748b; margin-top: 2px;
                     text-transform: uppercase; letter-spacing: 0.5px; }

.claim-card { border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom: 0.9rem;
              border-left: 5px solid; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.claim-card.verified   { border-color:#10b981; background:#f0fdf4; }
.claim-card.inaccurate { border-color:#f59e0b; background:#fffbeb; }
.claim-card.false      { border-color:#ef4444; background:#fef2f2; }
.claim-card.unknown    { border-color:#94a3b8; background:#f8fafc; }

.badge { display:inline-block; padding:3px 10px; border-radius:20px;
         font-size:0.73rem; font-weight:600; letter-spacing:0.4px; text-transform:uppercase; }
.badge-verified   { background:#d1fae5; color:#065f46; }
.badge-inaccurate { background:#fef3c7; color:#92400e; }
.badge-false      { background:#fee2e2; color:#991b1b; }
.badge-unknown    { background:#e2e8f0; color:#475569; }

.claim-text    { font-size:.97rem; font-weight:600; color:#1e293b; margin:.45rem 0 .3rem 0; }
.claim-verdict { font-size:.88rem; color:#374151; margin:.35rem 0; }
.claim-correct { font-size:.88rem; color:#065f46; background:#d1fae5;
                 border-radius:6px; padding:5px 9px; margin-top:.45rem; }
.claim-source  { font-size:.78rem; color:#6b7280; font-style:italic; margin-top:.35rem; }

.upload-zone { border:2px dashed #cbd5e1; border-radius:12px; padding:2.5rem;
               text-align:center; background:#f8fafc; }
.how-box { background:#f1f5f9; border-radius:10px; padding:1rem 1.2rem; }
.info-box { background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:1rem 1.2rem; }

div[data-testid="stFileUploader"] { border:none; }
.stButton > button {
  background: linear-gradient(135deg,#0e7c7b,#1e3a5f);
  color:white; border:none; border-radius:8px;
  padding:.55rem 2rem; font-weight:600; font-size:1rem; width:100%;
}
.stButton > button:hover { opacity:.88; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🔍 FactLens</h1>
  <p>Upload any PDF — every factual claim is extracted, verified against live web data, and flagged as Verified, Inaccurate, or False.</p>
</div>
""", unsafe_allow_html=True)

MODEL    = "llama-3.3-70b-versatile"
VERDICT_EMOJI = {"Verified":"✅","Inaccurate":"⚠️","False":"❌","Unknown":"❓"}
VERDICT_CLASS = {"Verified":"verified","Inaccurate":"inaccurate","False":"false","Unknown":"unknown"}
BADGE_CLASS   = {"Verified":"badge-verified","Inaccurate":"badge-inaccurate",
                 "False":"badge-false","Unknown":"badge-unknown"}

# ── PDF extraction ────────────────────────────────────────────────────────────
def extract_pdf_text(uploaded_file) -> str:
    raw = uploaded_file.read()
    doc = fitz.open(stream=raw, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    full = "\n".join(pages).strip()
    if not full:
        raise ValueError("This PDF appears to be image-based (scanned). Please use a text-based PDF.")
    return full

# ── Web search via DuckDuckGo (free, no key needed) ──────────────────────────
def web_search(query: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1&skip_disambig=1"
        r = requests.get(url, headers=headers, timeout=6)
        data = r.json()
        snippets = []
        if data.get("AbstractText"):
            snippets.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                snippets.append(topic["Text"])
        if snippets:
            return " | ".join(snippets[:3])
        return "No direct result found. Using AI knowledge for verification."
    except Exception:
        return "Web search unavailable. Using AI knowledge for verification."

# ── Extract claims via Groq ───────────────────────────────────────────────────
def extract_claims(client: Groq, text: str) -> list[dict]:
    prompt = f"""You are a precise claim-extraction engine.

Identify EVERY verifiable factual claim in the text below. A verifiable claim includes:
- Statistics or percentages (e.g. "conversion rate improved by 40%")
- Specific dates or years (e.g. "launched in 2019", "by Q3 2024")
- Named figures or rankings (e.g. "#1 platform", "500 million users")
- Financial data (e.g. "valued at $10B", "revenue of $3.2M")
- Technical specs or product facts
- Named research or study results

Return ONLY a raw JSON array — no markdown, no explanation.
Each element:
{{
  "id": <integer starting at 1>,
  "claim": "<exact or close paraphrase of the claim>",
  "context": "<one sentence of surrounding context>",
  "category": "<statistic | date | financial | product | research | other>"
}}

Do NOT include opinions or non-verifiable statements.

TEXT TO ANALYZE:
{text[:6000]}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=4000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    match = re.search(r'\[[\s\S]*\]', raw)
    if match:
        return json.loads(match.group())
    return json.loads(raw)

# ── Verify one claim ──────────────────────────────────────────────────────────
def verify_claim(client: Groq, claim: dict) -> dict:
    # Get live web context first
    search_query = f"{claim['claim']} fact check"
    web_context  = web_search(search_query)

    prompt = f"""You are a rigorous fact-checker with access to current web data.

CLAIM TO VERIFY:
Claim    : {claim['claim']}
Context  : {claim['context']}
Category : {claim['category']}

LIVE WEB DATA FOUND:
{web_context}

Using the web data above AND your knowledge, fact-check this claim carefully.

Return ONLY a raw JSON object — no markdown, no preamble:
{{
  "id": {claim['id']},
  "verdict": "<Verified | Inaccurate | False>",
  "confidence": "<High | Medium | Low>",
  "explanation": "<2-3 sentences with specific evidence supporting your verdict>",
  "correct_value": "<if Inaccurate or False: the correct figure or fact; otherwise null>",
  "source": "<name of source or URL used>"
}}

Verdict definitions:
- Verified   : claim matches current reliable data
- Inaccurate : real data but wrong/outdated figure — always provide correct_value
- False      : contradicts established facts or zero credible evidence"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=800,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            result = json.loads(match.group())
            result["id"] = claim["id"]
            return result
        except Exception:
            pass
    return {
        "id": claim["id"], "verdict": "Unknown", "confidence": "Low",
        "explanation": "Verification could not be completed.",
        "correct_value": None, "source": "N/A"
    }

# ── Render claim card ─────────────────────────────────────────────────────────
def render_card(claim: dict, result: dict):
    verdict  = result.get("verdict", "Unknown")
    css_cls  = VERDICT_CLASS.get(verdict, "unknown")
    badge_cl = BADGE_CLASS.get(verdict, "badge-unknown")
    emoji    = VERDICT_EMOJI.get(verdict, "❓")
    correct  = result.get("correct_value")
    conf     = result.get("confidence", "")
    correct_html = (f'<div class="claim-correct">✏️ <strong>Correct value:</strong> {correct}</div>'
                    if correct else "")
    st.markdown(f"""
<div class="claim-card {css_cls}">
  <span class="badge {badge_cl}">{emoji} {verdict}</span>
  &nbsp;&nbsp;<span style="font-size:.76rem;color:#6b7280;">
    Confidence: {conf} &nbsp;·&nbsp; Category: {claim.get('category','—')}
  </span>
  <p class="claim-text">"{claim['claim']}"</p>
  <p class="claim-verdict">{result.get('explanation','')}</p>
  {correct_html}
  <p class="claim-source">📎 Source: {result.get('source','N/A')}</p>
</div>""", unsafe_allow_html=True)

# ── UI ────────────────────────────────────────────────────────────────────────
col_up, col_info = st.columns([2, 1])

with col_up:
    st.markdown("#### 📄 Upload your PDF")
    st.markdown("""
<div style="font-size:.85rem;color:#64748b;margin-bottom:.5rem;">
✅ Accepted: Any <b>text-based PDF</b> — reports, articles, whitepapers, marketing decks, research papers<br>
❌ Not supported: Scanned/image PDFs (photos of pages) — text cannot be extracted from images
</div>""", unsafe_allow_html=True)
    uploaded = st.file_uploader("PDF file", type=["pdf"], label_visibility="collapsed")

with col_info:
    st.markdown("""
<div class="how-box">
<strong>How it works</strong><br><br>
1️⃣ &nbsp;<b>Extract</b> — every stat, date, figure and named fact pulled from PDF<br><br>
2️⃣ &nbsp;<b>Search</b> — each claim checked against live web + AI knowledge<br><br>
3️⃣ &nbsp;<b>Report</b> — flagged <b>Verified</b>, <b>Inaccurate</b>, or <b>False</b> with evidence
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# API key box
st.markdown("""
<div class="info-box">
<b>🔑 Get your FREE Groq API Key (takes 1 minute, no credit card)</b><br>
1. Go to <a href="https://console.groq.com" target="_blank"><b>console.groq.com</b></a><br>
2. Sign up with Google or GitHub<br>
3. Click <b>API Keys</b> → <b>Create API Key</b> → copy it
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

api_key = st.text_input(
    "Paste your Groq API Key here",
    type="password",
    placeholder="gsk_...",
    help="Free key — no credit card needed. Never stored."
)

run = st.button("🚀 Run Fact Check", disabled=(uploaded is None or not api_key))
st.divider()

# ── Pipeline ──────────────────────────────────────────────────────────────────
if run and uploaded and api_key:
    client = Groq(api_key=api_key)

    with st.status("Starting…", expanded=True) as status:

        # Extract text
        st.write("📖 Reading PDF…")
        try:
            pdf_text = extract_pdf_text(uploaded)
        except ValueError as e:
            st.error(f"⚠️ {e}")
            st.stop()
        except Exception as e:
            st.error(f"Could not read PDF: {e}")
            st.stop()
        st.write(f"✅ Extracted ~{len(pdf_text.split()):,} words")

        # Extract claims
        st.write("🧠 Identifying verifiable claims…")
        try:
            claims = extract_claims(client, pdf_text)
        except Exception as e:
            st.error(f"Claim extraction failed: {e}")
            st.stop()
        st.write(f"✅ Found **{len(claims)}** verifiable claims — verifying now…")
        status.update(label=f"Verifying {len(claims)} claims…", state="running")

        # Verify each claim
        results = []
        bar = st.progress(0, text="Verifying…")
        for i, claim in enumerate(claims):
            st.write(f"🔍 [{i+1}/{len(claims)}] *{claim['claim'][:85]}{'…' if len(claim['claim'])>85 else ''}*")
            try:
                res = verify_claim(client, claim)
            except Exception:
                res = {"id": claim["id"], "verdict": "Unknown", "confidence": "Low",
                       "explanation": "Verification failed.", "correct_value": None, "source": "N/A"}
            results.append((claim, res))
            bar.progress((i + 1) / len(claims), text=f"Verified {i+1}/{len(claims)}")
            time.sleep(0.2)

        status.update(label="✅ Fact-check complete!", state="complete")

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown("## 📊 Results Summary")
    verdicts     = [r["verdict"] for _, r in results]
    n_verified   = verdicts.count("Verified")
    n_inaccurate = verdicts.count("Inaccurate")
    n_false      = verdicts.count("False")
    total        = len(results)
    pct_ok       = round(n_verified / total * 100) if total else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(f'<div class="stat-card"><div class="number">{total}</div><div class="label">Total Claims</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card"><div class="number" style="color:#10b981">{n_verified}</div><div class="label">✅ Verified</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card"><div class="number" style="color:#f59e0b">{n_inaccurate}</div><div class="label">⚠️ Inaccurate</div></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-card"><div class="number" style="color:#ef4444">{n_false}</div><div class="label">❌ False</div></div>',unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="stat-card"><div class="number" style="color:#6366f1">{pct_ok}%</div><div class="label">Accuracy Rate</div></div>',unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab_all, tab_bad, tab_ok_t = st.tabs([
        f"All Claims ({total})",
        f"🚨 Issues ({n_inaccurate + n_false})",
        f"✅ Verified ({n_verified})"
    ])
    with tab_all:
        for c,r in results: render_card(c,r)
    with tab_bad:
        bad = [(c,r) for c,r in results if r["verdict"] in ("Inaccurate","False")]
        if not bad: st.info("No issues found.")
        else:
            for c,r in bad: render_card(c,r)
    with tab_ok_t:
        ok = [(c,r) for c,r in results if r["verdict"]=="Verified"]
        if not ok: st.info("No verified claims.")
        else:
            for c,r in ok: render_card(c,r)

    # ── Download ──────────────────────────────────────────────────────────────
    st.divider()
    lines = [
        "FACTLENS — AUTOMATED FACT-CHECK REPORT",
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Document  : {uploaded.name}",
        f"Claims    : {total}  |  Verified: {n_verified}  |  Inaccurate: {n_inaccurate}  |  False: {n_false}",
        "="*68, ""
    ]
    for claim, res in results:
        lines += [
            f"[{res['verdict'].upper()}] Claim #{claim['id']} ({claim.get('category','')}) — Confidence: {res.get('confidence','')}",
            f"Claim    : {claim['claim']}",
            f"Analysis : {res.get('explanation','')}",
        ]
        if res.get("correct_value"):
            lines.append(f"Correct  : {res['correct_value']}")
        lines += [f"Source   : {res.get('source','N/A')}", ""]

    st.download_button("⬇️ Download Full Report (.txt)",
                       data="\n".join(lines),
                       file_name=f"factlens_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                       mime="text/plain")

elif not uploaded:
    st.markdown("""
<div class="upload-zone">
  <p style="font-size:2rem;margin:0">📄</p>
  <p style="font-weight:600;color:#334155;margin:.5rem 0">Upload a PDF to begin</p>
  <p style="color:#64748b;font-size:.9rem">Text-based PDFs only — reports, articles, whitepapers, marketing decks</p>
</div>""", unsafe_allow_html=True)

st.markdown("""
<br><hr style="border-color:#e2e8f0">
<p style="text-align:center;color:#94a3b8;font-size:.78rem">
FactLens &nbsp;·&nbsp; Powered by Groq LLaMA 3.3 70B + DuckDuckGo Live Search
&nbsp;·&nbsp; Claims verified against real-time web data
</p>""", unsafe_allow_html=True)
