# AuroraCart at a Crossroads

A profitability & operations diagnostic for the AuroraCart case study: an EDA notebook,
a shared cleaning module, and an interactive Plotly Dash dashboard.

## Files

| File | What it is |
|---|---|
| `data-AuroraCart.csv` | Raw case-study export (15,000 orders, Jan 2023 – Dec 2025). |
| `data_prep.py` | Single source of truth for cleaning + feature engineering. Imported by both the notebook and the dashboard so their numbers can never drift apart. |
| `viz_theme.py` | Shared Plotly theme (colorblind-validated palette, fonts, chart chrome) used by both artifacts. |
| `AuroraCart_EDA.ipynb` | The analysis: data-quality audit, cleaning walkthrough, and the investigation that produced the findings below. Pre-executed — outputs are baked in. |
| `dashboard.py` | The interactive deliverable — a 4-tab Plotly Dash app with global filters. |
| `assets/style.css` | Dashboard styling (Dash auto-loads anything in `assets/`). |
| `requirements.txt` / `requirements-dev.txt` | Deployment deps / notebook-only extras. |
| `render.yaml`, `Procfile` | Deployment config for Render (see below). |

## The business story

**Context.** AuroraCart's net revenue nearly doubled from 2023 to 2025 (₹29.3M → ₹58.1M).

**Tension.** Profit did not keep pace: overall profit margin fell from **12.4% → 8.9% → 7.1%**
over the same three years. Growth is being purchased, not earned for free.

**Evidence, drilled down:**
1. **Electronics** drives ~46% of revenue but runs at **−4.9% margin** — the single
   largest category is losing money at scale.
2. **Flash Deals** carry the deepest average discount (24%) and are the only promotion
   type with **negative margin (−2.0%)**; no-promotion orders are the most profitable
   demand AuroraCart has (15.2% margin).
3. The **"Premium" customer segment** has the highest average order value but the
   **lowest margin (2.9%)** of any segment — the label doesn't match the economics.
4. **Paid acquisition** (Marketplace Ads, Paid Social) spends 6.9–8.6% of the revenue
   it generates on marketing, compressing an already-thin margin further.
5. **On-time delivery sits around 40–45%** company-wide regardless of fulfillment mode,
   correlates with lower ratings (r ≈ −0.48), and **triples the complaint rate** on late
   orders (12.4% vs 3.9%).

**Recommendations** (ranked by expected impact, each tied to the evidence above):
1. Re-price or re-cost Electronics at the subcategory level before scaling it further.
2. Restructure or retire Flash Deals; protect the no-promotion demand base.
3. Fix on-time delivery before spending more on customer acquisition.

**Limitations:** synthetic dataset; returns are not netted out of `Net_Revenue`; no
SKU-level cost breakdown to fully decompose *why* Electronics is unprofitable;
delivery-delay → rating is a credible association, not proven causation. Full detail,
with the numbers behind each claim, is in the notebook (§9–11).

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Dashboard only:
pip install -r requirements.txt
python dashboard.py              # http://127.0.0.1:8050

# Notebook (adds Jupyter on top of the dashboard deps):
pip install -r requirements-dev.txt
jupyter notebook AuroraCart_EDA.ipynb
```

## Deploying the dashboard for free — Render

**Why Render:** the dashboard is a Dash app, i.e. a standard Flask/WSGI Python web
service — that's exactly what Render's free **Web Service** tier is built for: connect
a GitHub repo, it detects Python, runs `gunicorn`, and gives you a public HTTPS URL,
no credit card and no Dockerfile required. (Streamlit Community Cloud isn't an option
here since this dashboard is deliberately built in Dash, not Streamlit; Hugging Face
Spaces would work too but needs a Dockerfile for a non-Streamlit/Gradio app, which is
more setup for the same result.)

The one trade-off: Render's **free** tier spins the service down after ~15 minutes of
no traffic, so the *first* request after a quiet period takes ~30–50 seconds to wake
up. Open the link a few minutes before you need it (e.g. before your presentation) and
it'll be instant from then on.

### Steps

1. **Push this repo to GitHub** (already done if you're reading this from the repo).
2. Go to **[render.com](https://render.com)** → sign up / log in with GitHub — free,
   no card needed.
3. Click **New +** → **Blueprint**, and point it at this repository. Render will read
   `render.yaml` automatically and pre-fill everything (service name, build command
   `pip install -r requirements.txt`, start command
   `gunicorn dashboard:server --workers 2 --timeout 120`, free plan).
   - *No Blueprint option, or prefer manual setup?* Use **New +** → **Web Service**
     instead, pick this repo, and set:
     - **Runtime:** Python 3
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn dashboard:server --workers 2 --timeout 120`
     - **Instance Type:** Free
4. Click **Deploy**. First deploy takes a few minutes (installing pandas/numpy/plotly).
5. Once it's live, Render gives you a URL like `https://auroracart-dashboard.onrender.com`
   — that's your shareable, always-on (with the cold-start caveat above) dashboard link.
6. Every future `git push` to the connected branch auto-redeploys.

No other free service was materially better for this specific app: Streamlit Cloud
only hosts Streamlit apps; Hugging Face Spaces needs a Dockerfile for Dash; Railway and
Fly.io both dropped their no-card free tiers. Render's Python web service is the
simplest path from "Dash app in a repo" to "public URL" without extra config files
beyond what's already in this repo.
