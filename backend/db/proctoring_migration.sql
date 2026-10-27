-- Proctoring Database Migration
-- Creates tables for tracking proctoring state and security violation events.
-- Usage: mysql -u root -p ai_interview_db < db/proctoring_migration.sql

USE ai_interview_db;

CREATE TABLE IF NOT EXISTS interview_proctoring_state (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL UNIQUE,
  status ENUM('CHECKING', 'ACTIVE', 'WARNING', 'PAUSED', 'TERMINATED', 'COMPLETED') DEFAULT 'ACTIVE',
  violation_count INT DEFAULT 0,
  max_violations INT DEFAULT 4,
  paused_reason VARCHAR(255) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_proctoring_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  severity ENUM('INFO', 'WARNING', 'PAUSE', 'TERMINATE') DEFAULT 'WARNING',
  question_number INT NULL,
  duration_seconds DECIMAL(6,2) NULL,
  metadata JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);
