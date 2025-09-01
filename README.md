
# Streamlit + MSSQL Demo (Tkinter sample converted to web)

This repo shows how to use **SQL Server (MSSQL)** as the backend for a simple Streamlit web UI.
It mirrors the earlier Tkinter sample: insert/update inventory via a stored procedure, search via a TVF, and show a summary via a view.

## Contents

- `app.py` — Streamlit web app
- `db.py` — database helper (uses `pymssql` so you don't need a system ODBC driver)
- `schema.sql` — sample SQL schema: table, stored procedure, TVF, and view
- `requirements.txt` — Python deps
- `.streamlit/secrets.toml` — example (do **not** commit real credentials)

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Set secrets (see below), then:
streamlit run app.py
```

## Configure MSSQL connection

Streamlit reads secrets from `.streamlit/secrets.toml` **or** Streamlit Cloud's project settings.

Create `.streamlit/secrets.toml`:

```toml
[mssql]
server = "localhost"         # or "192.168.1.10"
port   = 1433
user   = "sa"                # or a limited SQL user
password = "YourStrong!Pass"
database = "DemoDB"
timeout  = 5
```

> **Important:** The app expects the objects from `schema.sql` to exist (table `dbo.Stok`, SP `dbo.Sp_StokEkleVeyaArtir`, TVF `dbo.Fn_StokAra`, view `dbo.Vw_StokOzet`). Run `schema.sql` once on your MSSQL server (SSMS or sqlcmd).

## Deploy to Streamlit Community Cloud

1. Push these files to a public GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Pick your repo & branch, app path = `app.py`.
4. In **Secrets** panel, paste your `[mssql]` block from above.
5. Deploy.

> **Note:** We use `pymssql` to avoid the OS-level ODBC driver dependency. If you prefer `pyodbc`, install and configure Microsoft's ODBC Driver in your environment and adjust `db.py` accordingly.

## Quick demo

- **Insert/Increase:** Fill the form (Malzeme, Kalite, Boy, Adet) → "Ekle/Artır (SP)".
- **Search (TVF):** Type in "Ara (Malzeme)" and click "Ara (TVF)".
- **Summary:** Click "Özet Görünüm (View)".

