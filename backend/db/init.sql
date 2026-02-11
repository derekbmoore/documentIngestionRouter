-- Document Ingestion Router — Database Initialization
-- =====================================================
-- Creates required PostgreSQL extensions.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Full-text search trigger for chunks
CREATE OR REPLACE FUNCTION chunks_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- NOTE: The trigger is created after the table exists (via Alembic or init_db)
-- CREATE TRIGGER chunks_search_vector_trigger
--     BEFORE INSERT OR UPDATE ON chunks
--     FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_update();
