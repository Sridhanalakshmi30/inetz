-- Run once on existing databases before using the consent endpoint.
-- Existing candidates intentionally remain without consent.
ALTER TABLE candidates ADD COLUMN consent_given_at DATETIME NULL;
