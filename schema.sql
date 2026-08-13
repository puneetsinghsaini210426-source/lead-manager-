PRAGMA foreign_keys = ON;

CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL
);

CREATE TABLE leads (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    product TEXT NOT NULL,
    status TEXT NOT NULL,
    call_on DATE,
    call_type TEXT DEFAULT 'Call',
    priority TEXT DEFAULT 'Normal',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE RESTRICT
);

CREATE TABLE follow_up_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE
);

-- Indexes for faster search
CREATE INDEX idx_clients_mobile ON clients(mobile);
CREATE INDEX idx_clients_name ON clients(name);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_call_on ON leads(call_on);
CREATE INDEX idx_leads_product ON leads(product);
CREATE INDEX idx_leads_client_id ON leads(client_id);
CREATE INDEX idx_notes_lead_id ON follow_up_notes(lead_id);
