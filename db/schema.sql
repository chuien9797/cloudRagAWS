-- =============================================================
-- CloudRAG PostgreSQL Schema
-- Phase 4a
-- =============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================
-- users
-- =============================================================
CREATE TABLE IF NOT EXISTS users (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email            VARCHAR(255) NOT NULL UNIQUE,
    password_hash    TEXT         NOT NULL,
    full_name        VARCHAR(255),
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
    last_login       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);


-- =============================================================
-- documents
-- =============================================================
CREATE TABLE IF NOT EXISTS documents (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename             VARCHAR(255) NOT NULL,
    s3_uri               TEXT,
    chroma_doc_id        VARCHAR(255),
    doc_type             VARCHAR(100),
    status               VARCHAR(20)  NOT NULL DEFAULT 'uploading'
                             CHECK (status IN ('uploading', 'processing', 'indexed', 'failed', 'deleted')),
    is_public            BOOLEAN      NOT NULL DEFAULT FALSE,
    characters_extracted INT,
    total_chunks         INT,
    uploaded_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id  ON documents (user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status   ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_is_public ON documents (is_public);


-- =============================================================
-- chat_sessions
-- =============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL DEFAULT 'New chat',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions (user_id);


-- =============================================================
-- chat_messages
-- =============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id                UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID      NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role              VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content           TEXT      NOT NULL,
    prompt_tokens     INT,
    completion_tokens INT,
    total_tokens      INT,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages (session_id);


-- =============================================================
-- message_citations
-- =============================================================
CREATE TABLE IF NOT EXISTS message_citations (
    id              UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      UUID      NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    document_id     UUID      NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text      TEXT      NOT NULL,
    page_number     INT,
    chunk_index     INT,
    relevance_score FLOAT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citations_message_id  ON message_citations (message_id);
CREATE INDEX IF NOT EXISTS idx_citations_document_id ON message_citations (document_id);


-- =============================================================
-- auto-update updated_at on every UPDATE
-- =============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER set_updated_at_users
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE OR REPLACE TRIGGER set_updated_at_documents
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE OR REPLACE TRIGGER set_updated_at_chat_sessions
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE OR REPLACE TRIGGER set_updated_at_chat_messages
    BEFORE UPDATE ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();