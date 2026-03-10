ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

UPDATE users
SET password_hash = '{noop}password123'
WHERE password_hash IS NULL OR trim(password_hash) = '';

ALTER TABLE users
    ALTER COLUMN password_hash SET NOT NULL;
