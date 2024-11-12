BEGIN;

ALTER TABLE now_playing RENAME COLUMN progress TO position;

DELETE FROM now_playing;

COMMIT;
