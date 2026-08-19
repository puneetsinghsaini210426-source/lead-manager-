PRAGMA foreign_keys = ON;

CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT NOT NULL UNIQUE,
    email TEXT,
    company TEXT,
    job_title TEXT,
    address TEXT,
    city TEXT,
    notes TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE leads (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    product TEXT NOT NULL,
    status TEXT NOT NULL,
    call_on DATE,
    call_type TEXT DEFAULT 'Call',
    priority TEXT DEFAULT 'Normal',
    source TEXT DEFAULT 'Direct',
    source_detail TEXT,
    description TEXT,
    estimated_value NUMERIC,
    currency TEXT DEFAULT 'INR',
    probability INTEGER DEFAULT 0,
    last_contacted_at DATETIME,
    next_follow_up_at DATETIME,
    converted_at DATETIME,
    lost_reason TEXT,
    owner TEXT,
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

CREATE TABLE lead_activities (
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

CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    color TEXT DEFAULT '#64748b',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lead_tags (
    lead_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (lead_id, tag_id),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);

-- Indexes for faster search
CREATE INDEX idx_clients_mobile ON clients(mobile);
CREATE INDEX idx_clients_name ON clients(name);
CREATE INDEX idx_clients_email ON clients(email);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_call_on ON leads(call_on);
CREATE INDEX idx_leads_product ON leads(product);
CREATE INDEX idx_leads_client_id ON leads(client_id);
CREATE INDEX idx_leads_priority ON leads(priority);
CREATE INDEX idx_leads_source ON leads(source);
CREATE INDEX idx_leads_updated_at ON leads(updated_at);
CREATE INDEX idx_leads_next_follow_up ON leads(next_follow_up_at);
CREATE INDEX idx_notes_lead_id ON follow_up_notes(lead_id);
CREATE INDEX idx_activities_lead_id ON lead_activities(lead_id);
CREATE INDEX idx_activities_scheduled_for ON lead_activities(scheduled_for);
