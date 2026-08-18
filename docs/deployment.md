# Deploying the dashboard for free on Render

**Why Render:** the dashboard is a Dash app, i.e. a standard Flask/WSGI Python web
service, and that is exactly what Render's free **Web Service** tier is built for:
connect a GitHub repo, it detects Python, runs `gunicorn`, and gives you a public
HTTPS URL, no credit card and no Dockerfile required. (Streamlit Community Cloud
isn't an option here since this dashboard is deliberately built in Dash, not
Streamlit; Hugging Face Spaces would work too but needs a Dockerfile for a
non-Streamlit/Gradio app, which is more setup for the same result.)

The one trade-off: Render's **free** tier spins the service down after ~15
minutes of no traffic, so the *first* request after a quiet period takes ~30-50
seconds to wake up. Open the link a few minutes before you need it (before your
presentation, say) and it'll be instant from then on.

## What the repo already provides

| File | Role |
| --- | --- |
| `render.yaml` | Blueprint: service name, build and start commands, free plan, Python version |
| `Procfile` | The same start command, for platforms that read a Procfile instead |
| `app.py` | The WSGI entrypoint at the repository root, where hosting platforms look |
| `requirements.txt` | Installs the `auroracart` package from `src/` along with its pinned dependencies |

The start command is `gunicorn app:server`; `app.py` re-exports `server` from
`auroracart.dashboard`, so the package layout is invisible to the platform.

## Steps

1. **Push this repo to GitHub** (already done if you're reading this from the repo).
2. Go to **[render.com](https://render.com)** and sign up or log in with GitHub.
   Free, no card needed.
3. Click **New +** → **Blueprint**, and point it at this repository. Render will
   read `render.yaml` automatically and pre-fill everything (service name, build
   command `pip install -r requirements.txt`, start command
   `gunicorn app:server --workers 2 --timeout 120`, free plan).
   - *No Blueprint option, or prefer manual setup?* Use **New +** → **Web
     Service** instead, pick this repo, and set:
     - **Runtime:** Python 3
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:server --workers 2 --timeout 120`
     - **Instance Type:** Free
4. Click **Deploy**. First deploy takes a few minutes (installing
   pandas/numpy/plotly).
5. Once it's live, Render gives you a URL like
   `https://auroracart-dashboard.onrender.com`. That is your shareable dashboard
   link, always on, with the cold-start caveat above.
6. Every future `git push` to the connected branch auto-redeploys.

## Where the data comes from

The dataset is committed at `data/raw/data-AuroraCart.csv` and loaded at import
time, so there is nothing to provision: no database, no object store, no
environment variables. If you ever need to point the app at a dataset somewhere
else, set `AURORACART_DATA_DIR` and `auroracart.paths` will resolve `raw/` under
it instead.

## Why not the alternatives

No other free service was materially better for this specific app: Streamlit
Cloud only hosts Streamlit apps; Hugging Face Spaces needs a Dockerfile for
Dash; Railway and Fly.io both dropped their no-card free tiers. Render's Python
web service is the simplest path from "Dash app in a repo" to "public URL"
without extra config files beyond what's already in this repo.
