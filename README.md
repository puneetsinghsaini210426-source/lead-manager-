# Lead Manager (Flask + SQLite)

Simple local Lead Management app.

Setup

1. Create a virtualenv and install deps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Open http://127.0.0.1:5000 in your browser.

Files

- `app.py` — Flask application
- `database.py` — sqlite helper and initializer
- `schema.sql` — database schema
- `database/leads.db` — created on first run
- `backups/` — backups are stored here

Backup & Restore

- Click Backup to create a timestamped copy in `backups/`.
- Use Restore to upload a `.db` file and overwrite the active database.

Import / Export

- Use the **Export** link in the nav or Backups page to download an Excel file (`leads_export.xlsx`) containing all leads and full follow-up notes.
- Use the **Import** link to upload a CSV or Excel file. Required columns: `client_name` (or `name`), `client_mobile` (or `mobile`), `product`. Optional: `status`, `call_on`, `call_type`, `priority`, `notes`.
# lead-manager-
