-- D1 schema for meals table
CREATE TABLE IF NOT EXISTS meals (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  ingredients JSON NOT NULL,
  instructions JSON NOT NULL,
  created_at DATETIME NOT NULL
);
