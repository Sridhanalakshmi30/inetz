-- Run this once to create the database and tables.
-- Usage: mysql -u root -p < db/schema.sql

CREATE DATABASE IF NOT EXISTS ai_interview_db;
USE ai_interview_db;

CREATE TABLE IF NOT EXISTS candidates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255),
  email VARCHAR(255),
  resume_filename VARCHAR(255),
  resume_raw_text LONGTEXT,
  parsed_resume JSON,
  consent_given_at DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interview_sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT NOT NULL,
  role_key VARCHAR(64) NULL,
  interview_plan JSON,
  status ENUM('in_progress','completed','abandoned') DEFAULT 'in_progress',
  started_at DATETIME,
  ended_at DATETIME NULL,
  duration_minutes INT DEFAULT 15,
  current_topic_index INT DEFAULT 0,
  question_count INT DEFAULT 0,
  FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_turns (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  turn_number INT NOT NULL,
  topic VARCHAR(255),
  question_text TEXT,
  answer_text TEXT,
  answer_source ENUM('typed','voice','mixed') DEFAULT 'typed',
  technical_score DECIMAL(4,1),
  depth_score DECIMAL(4,1),
  relevance_score DECIMAL(4,1),
  rationale TEXT,
  adaptive_decision ENUM('follow_up','new_topic','change_difficulty','end_topic'),
  answered_at DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_reports (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL UNIQUE,
  overall_score DECIMAL(5,2),
  skill_scores JSON,
  strengths JSON,
  weaknesses JSON,
  feedback_text TEXT,
  recommendation VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_access_tokens (
  scope ENUM('candidate', 'session') NOT NULL,
  resource_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (scope, resource_id)
);
