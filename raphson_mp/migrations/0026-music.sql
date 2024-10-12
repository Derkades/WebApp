BEGIN;

CREATE INDEX idx_session_user ON session(user);
CREATE INDEX idx_now_playing_timestamp ON now_playing(timestamp);
CREATE INDEX idx_scanner_log_timestamp ON scanner_log(timestamp);

COMMIT;
