# Lead Manager (Flask + SQLite)

Simple local Lead Management app.

## Production data storage

The app uses one server-side database. Leads are not tied to a browser, laptop, or phone.
For Render, do not rely on the default project directory for production data: Render's
service filesystem is ephemeral and can be reset after a redeploy or restart. Attach a
persistent disk to the service, for example mounted at `/var/data`, and set these
environment variables:

```text
DATA_DIR=/var/data
DATABASE_PATH=/var/data/leads.db
BACKUP_DIR=/var/data/backups
```

After deploying with the persistent disk, all devices using the same service URL will
read and write the same database. Export the current local leads before deployment and
use the Import page after deployment if the hosted database starts empty.

SQLite is suitable for one Render service instance with a persistent disk. If you scale
to multiple instances, migrate to a managed PostgreSQL database instead; separate
instances must not share a SQLite file over a network filesystem.

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

3. Open http://127.0.0.1:5001 in your browser (app defaults to port 5001 locally).

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
