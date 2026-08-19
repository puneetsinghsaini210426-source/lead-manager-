import sqlite3
import os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')
POSTGRES_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'postgres_schema.sql')


def is_postgres(db_path):
    return str(db_path).startswith(('postgres://', 'postgresql://'))


class PostgresRow(dict):
    def __init__(self, row):
        super().__init__({
            key: value.isoformat() if hasattr(value, 'isoformat') else value
            for key, value in row.items()
        })

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(tuple(self.keys())[key])
        return super().__getitem__(key)


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=()):
        return self._cursor.execute(query.replace('?', '%s'), params)

    def fetchone(self):
        row = self._cursor.fetchone()
        return PostgresRow(row) if row is not None else None

    def fetchall(self):
        return [PostgresRow(row) for row in self._cursor.fetchall()]


class PostgresConnection:
    def __init__(self, url):
        import psycopg
        from psycopg.rows import dict_row
        try:
            self._connection = psycopg.connect(url, row_factory=dict_row, connect_timeout=15)
        except psycopg.OperationalError as error:
            if '.supabase.co' in url and '.pooler.supabase.com' not in url:
                raise RuntimeError(
                    'Supabase direct database connections use IPv6 and are unreachable from Render. '
                    'Use the Supabase Session pooler URL (aws-REGION.pooler.supabase.com:5432) in DATABASE_URL.'
                ) from error
            raise

    def cursor(self):
        return PostgresCursor(self._connection.cursor())

    def execute(self, query, params=()):
        return self._connection.execute(query.replace('?', '%s'), params)

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()


def get_db(db_path):
    if is_postgres(db_path):
        return PostgresConnection(db_path)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(db_path):
    if is_postgres(db_path):
        conn = PostgresConnection(db_path)
        with open(POSTGRES_SCHEMA_PATH, 'r') as schema_file:
            statements = [statement.strip() for statement in schema_file.read().split(';') if statement.strip()]
        for statement in statements:
            conn.execute(statement)
        conn.commit()
        conn.close()
        return
    if not os.path.exists(db_path):
        with open(SCHEMA_PATH, 'r') as f:
            schema = f.read()
        conn = sqlite3.connect(db_path)
        conn.executescript(schema)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.commit()
        conn.close()


def ensure_columns(db_path):
    if is_postgres(db_path):
        init_db(db_path)
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(clients)")
    client_cols = [r[1] for r in cur.fetchall()]
    client_columns = {
        'email': 'TEXT',
        'company': 'TEXT',
        'job_title': 'TEXT',
        'address': 'TEXT',
        'city': 'TEXT',
        'notes': 'TEXT',
        'updated_at': 'DATETIME',
    }
    for name, definition in client_columns.items():
        if name not in client_cols:
            cur.execute(f'ALTER TABLE clients ADD COLUMN {name} {definition}')
    if 'updated_at' not in client_cols:
        cur.execute('UPDATE clients SET updated_at = created_at WHERE updated_at IS NULL')

    cur.execute("PRAGMA table_info(leads)")
    cols = [r[1] for r in cur.fetchall()]
    lead_columns = {
        'call_type': "TEXT DEFAULT 'Call'",
        'priority': "TEXT DEFAULT 'Normal'",
        'source': "TEXT DEFAULT 'Direct'",
        'source_detail': 'TEXT',
        'description': 'TEXT',
        'estimated_value': 'NUMERIC',
        'currency': "TEXT DEFAULT 'INR'",
        'probability': 'INTEGER DEFAULT 0',
        'last_contacted_at': 'DATETIME',
        'next_follow_up_at': 'DATETIME',
        'converted_at': 'DATETIME',
        'lost_reason': 'TEXT',
        'owner': 'TEXT',
    }
    for name, definition in lead_columns.items():
        if name not in cols:
            cur.execute(f'ALTER TABLE leads ADD COLUMN {name} {definition}')

    cur.executescript('''
        CREATE TABLE IF NOT EXISTS lead_activities (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL DEFAULT 'Note',
            title TEXT,
            details TEXT,
            scheduled_for DATETIME,
            completed_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS tags (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            color TEXT DEFAULT '#64748b',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lead_tags (
            lead_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (lead_id, tag_id),
            FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);
        CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
        CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);
        CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
        CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON leads(updated_at);
        CREATE INDEX IF NOT EXISTS idx_leads_next_follow_up ON leads(next_follow_up_at);
        CREATE INDEX IF NOT EXISTS idx_activities_lead_id ON lead_activities(lead_id);
        CREATE INDEX IF NOT EXISTS idx_activities_scheduled_for ON lead_activities(scheduled_for);
    ''')
    conn.commit()
    conn.close()