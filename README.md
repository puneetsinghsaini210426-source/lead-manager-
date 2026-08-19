# Lead Manager (Flask + SQLite)

Simple local Lead Management app.

## Production data storage

The app uses one server-side database. Leads are not tied to a browser, laptop, or phone.
For Render Free, do not rely on the default project directory for production data:
Render documents that local files are lost when a free service spins down, restarts, or
redeploys, and Free web services cannot attach persistent disks. Use a hosted PostgreSQL
database instead. Supabase Free is a practical option for this small app (500 MB); its
database can pause after inactivity, but pausing is different from deleting the data.

Create a Supabase project, open **Connect**, choose **Session pooler**, and set the
pooler connection string as this Render environment variable. Do not use the direct
connection string beginning with `db.<project-ref>.supabase.co`; Supabase documents
that direct endpoint as IPv6-only on the free tier, while Render is IPv4-only.

```text
DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-REGION.pooler.supabase.com:5432/postgres?sslmode=require
```

Use the exact host, region, username, and password shown by Supabase. The pooler
username normally looks like `postgres.PROJECT_REF`, and Session pooler uses port `5432`.
Transaction pooler uses port `6543`, but Session pooler is the better fit for this
long-running Flask/Gunicorn service.

The app creates the PostgreSQL tables automatically on startup. All devices using the
same Render URL then read and write the same hosted database. Export the current local
leads before deployment and use the Import page after setting `DATABASE_URL` if the
hosted database starts empty.

Render's own Free Postgres is not suitable as a permanent free choice because Render's
current documentation says Free Postgres expires after 30 days. Supabase Free can also
pause after a week of inactivity, so the first request after a pause may be slower, but
the database contents remain available when the project resumes. Keep regular exports
for important data because the Supabase Free plan does not include downloadable backups.

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
- `database.py` — SQLite/PostgreSQL helper and initializer
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
