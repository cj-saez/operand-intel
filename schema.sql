CREATE TABLE IF NOT EXISTS funds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    vintage INTEGER,
    status TEXT,
    committed REAL,
    called REAL,
    total_value REAL,
    moic REAL,
    tvpi REAL,
    rvpi REAL,
    dvpi REAL,
    preferred_return REAL DEFAULT 0.08,
    carry_rate REAL DEFAULT 0.20,
    cash_on_hand REAL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id TEXT REFERENCES funds(id),
    name TEXT NOT NULL,
    short_name TEXT,
    sector TEXT,
    status TEXT,
    state TEXT,
    formed_date TEXT,
    invested REAL DEFAULT 0,
    realized REAL DEFAULT 0,
    unrealized REAL DEFAULT 0,
    total_return REAL DEFAULT 0,
    moic REAL,
    irr REAL,
    ownership_pct REAL,
    ev_ebitda_original REAL,
    tev_original REAL,
    ebitda_current REAL,
    ev_ebitda_current REAL,
    tev_current REAL,
    net_debt REAL,
    equity_value REAL,
    current_mark_notes TEXT,
    tear_sheet_url TEXT,
    investment_summary_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cash_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    fund_id TEXT REFERENCES funds(id),
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS searchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Identity
    searcher_identifier TEXT,
    searcher_name TEXT,
    llc_name TEXT,
    search_type TEXT,
    -- Demographics
    ethnicity TEXT,
    gender TEXT,
    estimated_age TEXT,
    marital_status TEXT,
    -- Education
    education TEXT,
    took_eta_class INTEGER DEFAULT 0,
    completed_eta_internship INTEGER DEFAULT 0,
    -- Background
    professional_background TEXT,
    post_mba_years TEXT,
    -- Capital & Structure
    search_capital_target REAL,
    capital_value_per_unit REAL,
    total_units INTEGER,
    capital_raised REAL,
    capital_called REAL,
    -- Geography
    location_general TEXT,
    location_specific TEXT,
    -- Industries
    target_industries TEXT,
    -- Risk / Score
    headline_score INTEGER,
    score_color TEXT,
    risk_positive TEXT,
    risk_mixed TEXT,
    risk_negative TEXT,
    score_signals TEXT,
    overall_take TEXT,
    -- Fund tracking
    fund_id TEXT REFERENCES funds(id),
    sector TEXT,
    status TEXT,
    company_acquired TEXT,
    operand_participation INTEGER DEFAULT 0,
    -- PPM data
    ppm_raw TEXT,
    -- Meta
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
