-- Run once against an existing interview database before deploying this update.
ALTER TABLE interview_sessions ADD COLUMN role_key VARCHAR(64) NULL AFTER candidate_id;
