# FactLens — Automated PDF Fact-Checker

> Upload any PDF. FactLens extracts every verifiable claim, cross-references it against live web data in real time, and flags what's wrong — with evidence and sources.

---

## 🔗 Live Demo
**[https://factlens-checker.streamlit.app](https://factlens-checker.streamlit.app)**

---

## What it does

| Step | Description |
|------|-------------|
| **Extract** | Parses every verifiable claim from the PDF: statistics, dates, financial figures, product facts, research findings |
| **Verify** | Each claim is independently checked against live web data using DuckDuckGo Search + Groq AI |
| **Report** | Claims flagged as ✅ **Verified**, ⚠️ **Inaccurate** (with correct value), or ❌ **False** — with source links |

---

## 🆓 Completely Free — No Credit Card Needed

This app uses the **Groq API** which has a completely free tier:
- Get your free API key at **[console.groq.com](https://console.groq.com)**
- Sign up with Google or GitHub — no credit card, no payment
- Free tier is more than enough for fact-checking any PDF

---

## Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/prateekbhatt282018-create/factlens-.git
cd factlens-
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

### 4. Run the app
```bash
streamlit run app.py
```
Opens at **http://localhost:8501**

### 5. Get your free API key
1. Go to **[console.groq.com](https://console.groq.com)**
2. Sign up with Google or GitHub
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)
5. Paste it into the app when prompted

---

## Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to **[share.streamlit.io](https://share.streamlit.io)** → New app
3. Select repo → branch `main` → file `app.py`
4. Click **Deploy** — live in ~2 minutes

No environment variables or secrets needed. Users enter their own Groq API key directly in the UI.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| PDF Parsing | PyMuPDF (fitz) |
| AI Model | Groq — LLaMA 3.3 70B Versatile |
| Live Web Search | DuckDuckGo Search API (free, no key needed) |
| Deployment | Streamlit Cloud |

---

## How verification works

1. **Claim extraction** — Groq LLaMA reads the full PDF text and returns a structured JSON list of every verifiable claim with category labels (statistic, date, financial, product, research)

2. **Live web search** — For each claim, the app searches DuckDuckGo in real time to find current, authoritative data

3. **AI verification** — Groq compares the live web results against the claim and delivers a verdict:
   - `Verified` — matches current reliable data
   - `Inaccurate` — real data but wrong or outdated figure (shows correct value)
   - `False` — contradicts known facts or no credible evidence found

4. **Downloadable report** — Full `.txt` report with all verdicts, explanations, and sources

---

## Supported PDF Types

✅ Text-based PDFs — articles, reports, whitepapers, press releases, marketing decks, research papers

❌ Scanned/image PDFs — photos of pages where text cannot be extracted

**Tip:** To check if your PDF works — open it and try to select/highlight text with your mouse. If you can select text, it will work perfectly.

---

## Project Structure

```
factlens/
├── app.py            # Main Streamlit application
├── requirements.txt  # Python dependencies
├── README.md         # This file
└── .gitignore
```

---

## Requirements

```
streamlit>=1.35.0
groq>=1.0.0
PyMuPDF>=1.24.0
requests>=2.31.0
```

---

## License
MIT
