"""WSGI entrypoint for the AuroraCart dashboard.

Kept at the repository root because that is where hosting platforms look:

    gunicorn app:server        # Render / Procfile
    python app.py              # local dev server on http://127.0.0.1:8050

The app itself lives in ``src/auroracart/dashboard.py``.
"""

from auroracart.dashboard import app, main, server

__all__ = ["app", "server", "main"]

if __name__ == "__main__":
    main()
