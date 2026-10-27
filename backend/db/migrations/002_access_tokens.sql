CREATE TABLE IF NOT EXISTS interview_access_tokens (
  scope ENUM('candidate', 'session') NOT NULL,
  resource_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (scope, resource_id)
);
