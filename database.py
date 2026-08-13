import sqlite3
import os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def get_db(db_path):
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(db_path):
    if not os.path.exists(db_path):
        with open(SCHEMA_PATH, 'r') as f:
            schema = f.read()
        conn = sqlite3.connect(db_path)
        conn.executescript(schema)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.commit()
        conn.close()


def ensure_columns(db_path):
    # Ensure optional columns exist for migrations: call_type, priority
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(leads)")
    cols = [r[1] for r in cur.fetchall()]
    if 'call_type' not in cols:
        cur.execute("ALTER TABLE leads ADD COLUMN call_type TEXT DEFAULT 'Call'")
    if 'priority' not in cols:
        cur.execute("ALTER TABLE leads ADD COLUMN priority TEXT DEFAULT 'Normal'")
    conn.commit()
    conn.close()