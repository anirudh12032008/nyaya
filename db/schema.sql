CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY,
  created_at TEXT,
  module TEXT,
  status TEXT,
  urgency TEXT,
  client_name TEXT,
  summary TEXT,
  draft_md TEXT,
  sections_json TEXT,
  deadline TEXT,
  assigned_to INTEGER,
  eligible_aid INTEGER,
  eligibility_reason TEXT,
  intake_seconds REAL,
  trace_json TEXT,
  facts_json TEXT,
  council_json TEXT,
  outcome TEXT,
  outcome_note TEXT,
  outcome_at TEXT,
  copilot_json TEXT
);

CREATE TABLE IF NOT EXISTS volunteers (
  id INTEGER PRIMARY KEY,
  name TEXT,
  load INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY,
  case_id INTEGER,
  rating TEXT,
  note TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  case_id INTEGER,
  type TEXT,
  payload TEXT,
  ts TEXT
);

CREATE TABLE IF NOT EXISTS annexures (
  id INTEGER PRIMARY KEY,
  case_id INTEGER,
  filename TEXT,
  path TEXT,
  kind TEXT,
  label TEXT,
  summary TEXT,
  matches_item TEXT,
  created_at TEXT
);
