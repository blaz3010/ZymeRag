CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
DO $$ BEGIN
    CREATE TYPE file_type_enum AS ENUM (
        'pdf',
        'csv',
        'txt',
        'docx',
        'image',
        'audio',
        'video',
        'website'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS contents (
    id          BIGSERIAL       PRIMARY KEY,
    content_id  VARCHAR(255)    UNIQUE NOT NULL,
    name        TEXT            NOT NULL,
    file_type   file_type_enum  NOT NULL DEFAULT 'pdf',
    file_size   BIGINT          CHECK (file_size >= 0),     -- bytes; NULL if unknown
    chunks      INTEGER         NOT NULL DEFAULT 0 CHECK (chunks >= 0),
    inserted_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ                                  -- soft delete
);

CREATE TABLE IF NOT EXISTS feeds (
    id          BIGSERIAL       PRIMARY KEY,
    feed_id     VARCHAR(255)    UNIQUE NOT NULL,
    url         TEXT            NOT NULL,
    chunks      INTEGER         NOT NULL DEFAULT 0 CHECK (chunks >= 0),
    inserted_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),      -- last re-crawl timestamp
    deleted_at  TIMESTAMPTZ                                  -- soft delete
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_contents_content_id
    ON contents(content_id);

CREATE INDEX IF NOT EXISTS idx_contents_file_type
    ON contents(file_type);

CREATE INDEX IF NOT EXISTS idx_contents_active
    ON contents(content_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_contents_file_type_active
    ON contents(file_type)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_feeds_feed_id
    ON feeds(feed_id);

CREATE INDEX IF NOT EXISTS idx_feeds_active
    ON feeds(feed_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_feeds_updated_at_active
    ON feeds(updated_at ASC)
    WHERE deleted_at IS NULL;