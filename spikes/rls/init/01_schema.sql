-- Somente dados sintéticos para o spike descartável.
CREATE ROLE rls_app LOGIN PASSWORD 'rls_spike_only_password'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    content TEXT NOT NULL
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO rls_app;
GRANT USAGE, SELECT ON SEQUENCE documents_id_seq TO rls_app;

INSERT INTO documents (tenant_id, content) VALUES
    ('tenant-a', 'documento de teste A'),
    ('tenant-b', 'documento de teste B');
