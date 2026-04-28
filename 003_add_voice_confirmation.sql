-- Migration: Add voice confirmation fields to Alert model
-- Purpose: Support voice-based safety confirmation for elderly care alerts
-- Safety: Track all voice confirmation attempts for audit trail

-- Add voice confirmation status enum type
CREATE TYPE voice_confirmation_status AS ENUM (
    'pending',           -- Voice prompt triggered, waiting for response
    'confirmed_safe',    -- Elder responded with safe phrase
    'unclear',          -- Response received but didn't match safe phrases
    'no_response',      -- No response after max attempts
    'help_requested',   -- Elder said help-related words
    'failed',           -- Voice system error (transcription failed)
    'device_error'      -- Device offline or unavailable
);

-- Add voice confirmation fields to Alert table
ALTER TABLE alert ADD COLUMN voice_confirmation_status voice_confirmation_status DEFAULT NULL;
ALTER TABLE alert ADD COLUMN voice_confirmation_attempted_at TIMESTAMP DEFAULT NULL;
ALTER TABLE alert ADD COLUMN voice_confirmation_response_text TEXT DEFAULT NULL;
ALTER TABLE alert ADD COLUMN voice_confirmation_confidence FLOAT DEFAULT NULL;

-- Create index for anti-loop check (30 minute cooldown per alert type)
CREATE INDEX idx_alert_voice_antiloop
ON alert(elder_id, alert_type, voice_confirmation_attempted_at)
WHERE voice_confirmation_attempted_at IS NOT NULL;

-- Create index for recent voice attempts (family visibility)
CREATE INDEX idx_alert_voice_recent
ON alert(family_id, voice_confirmation_status, voice_confirmation_attempted_at)
WHERE voice_confirmation_status IS NOT NULL;

-- Add audit trail column for tracking voice system integration
ALTER TABLE alert ADD COLUMN voice_confirmation_device_id VARCHAR(255) DEFAULT NULL;

-- Create audit table for detailed voice confirmation logging
CREATE TABLE voice_confirmation_audit (
    id BIGSERIAL PRIMARY KEY,
    family_id BIGINT NOT NULL,
    elder_id VARCHAR(255) NOT NULL,
    alert_id BIGINT NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    alert_level VARCHAR(20) NOT NULL,
    attempt_number INT NOT NULL,
    status voice_confirmation_status NOT NULL,
    response_text TEXT DEFAULT NULL,
    response_confidence FLOAT DEFAULT NULL,
    device_id VARCHAR(255) DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    attempted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (family_id) REFERENCES family(id) ON DELETE CASCADE,
    FOREIGN KEY (alert_id) REFERENCES alert(id) ON DELETE CASCADE
);

-- Create indices for voice confirmation audit trail
CREATE INDEX idx_voice_audit_elder ON voice_confirmation_audit(elder_id, attempted_at);
CREATE INDEX idx_voice_audit_family ON voice_confirmation_audit(family_id, attempted_at);
CREATE INDEX idx_voice_audit_status ON voice_confirmation_audit(status, attempted_at);

-- Update comment on Alert table
COMMENT ON COLUMN alert.voice_confirmation_status IS 'Status of voice confirmation attempt: pending, confirmed_safe, unclear, no_response, help_requested, failed, device_error';
COMMENT ON COLUMN alert.voice_confirmation_attempted_at IS 'Timestamp when voice confirmation was triggered';
COMMENT ON COLUMN alert.voice_confirmation_response_text IS 'Raw transcribed response from speech-to-text (for audit trail)';
COMMENT ON COLUMN alert.voice_confirmation_confidence IS 'Confidence score 0.0-1.0 for response classification';
COMMENT ON COLUMN alert.voice_confirmation_device_id IS 'ID of voice device that handled confirmation';

COMMENT ON TABLE voice_confirmation_audit IS 'Detailed audit trail of all voice confirmation attempts for safety compliance and debugging';
