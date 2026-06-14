# FactLens — Automated PDF Fact-Checker

> Upload any PDF. FactLens extracts every verifiable claim, cross-references it against **live Google Search data** in real time, and flags what's wrong — with evidence and sources.

---

## 🔗 Live Demo
**[https://factlens.streamlit.app](https://factlens.streamlit.app)**

---

## What it does

| Step | Description |
|------|-------------|
| **Extract** | Parses every verifiable claim from the PDF: statistics, dates, financial figures, product facts, research findings |
| **Verify** | Each claim is independently verified using Gemini 2.0 Flash + Google Search Grounding (live web) |
| **Report** | Claims flagged as ✅ **Verified**, ⚠️ **Inaccurate** (with correct value), or ❌ **False** — with source links |

---

## 🆓 Completely Free — No Credit Card Needed

This app uses the **Google Gemini API** which has a free tier:
- Get your free API key at **[aistudio.google.com](https://aistudio.google.com)**
- No credit card, no payment, no billing setup
- Free tier: 15 requests/minute — more than enough for fact-checking

---

## Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/factlens.git
cd factlens
```

### 2. Create virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run
```bash
streamlit run app.py
```
Opens at **http://localhost:8501**

### 5. Get free API key
Go to [aistudio.google.com](https://aistudio.google.com) → Sign in with Google → **Get API Key** → paste it in the app

---

## Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select repo → branch `main` → file `app.py`
4. Click **Deploy** — live in ~2 minutes

No environment variables or secrets needed. Users enter their own API key in the UI.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| PDF Parsing | PyMuPDF (fitz) |
| AI Model | Google Gemini 2.0 Flash |
| Live Web Search | Google Search Grounding (built into Gemini) |
| Deployment | Streamlit Cloud |

---

## How verification works

1. **Claim extraction** — Gemini reads the full PDF and returns a structured JSON list of every verifiable claim with category labels
2. **Live web verification** — For each claim, Gemini fires a Google Search, reads authoritative sources, and compares them against the stated claim
3. **Verdict**:
   - `Verified` — matches current reliable data
   - `Inaccurate` — real data but wrong/outdated figure (shows correct value)
   - `False` — contradicts known facts or no evidence found
4. **Downloadable report** — full .txt report with all verdicts, explanations, and sources

---

## Project Structure

```
factlens/
├── app.py            # Main Streamlit application
├── requirements.txt  # Python dependencies (3 packages)
├── README.md         # This file
└── .gitignore
```

---

## License
MIT
