from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from spikes.rls.rls_demo import documents_for_current_tenant, set_tenant, tenant_engine

pytestmark = pytest.mark.spike


@pytest.fixture(scope="module")
def app_engine():
    url = os.getenv("RLS_APP_DATABASE_URL")
    if not url:
        pytest.skip("Defina RLS_APP_DATABASE_URL após iniciar spikes/rls/compose.yaml")
    engine = tenant_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def admin_engine():
    url = os.getenv("RLS_ADMIN_DATABASE_URL")
    if not url:
        pytest.skip("Defina RLS_ADMIN_DATABASE_URL após iniciar spikes/rls/compose.yaml")
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


def test_tenant_a_cannot_read_tenant_b_through_orm_session(app_engine):
    with Session(app_engine) as session, session.begin():
        set_tenant(session, "tenant-a")
        rows = documents_for_current_tenant(session)
        assert rows and all(row.tenant_id == "tenant-a" for row in rows)


def test_tenant_a_cannot_read_tenant_b_through_raw_sql(app_engine):
    with Session(app_engine) as session, session.begin():
        set_tenant(session, "tenant-a")
        rows = session.execute(text("SELECT tenant_id FROM documents WHERE tenant_id = 'tenant-b'")).all()
        assert rows == []


def test_tenant_a_cannot_insert_update_or_delete_tenant_b_rows(app_engine):
    with Session(app_engine) as session, session.begin():
        set_tenant(session, "tenant-a")
        update_count = session.execute(
            text("UPDATE documents SET content = 'alterado' WHERE tenant_id = 'tenant-b'")
        ).rowcount
        delete_count = session.execute(
            text("DELETE FROM documents WHERE tenant_id = 'tenant-b'")
        ).rowcount
        assert update_count == 0
        assert delete_count == 0
        with pytest.raises(DBAPIError):
            session.execute(
                text("INSERT INTO documents (tenant_id, content) VALUES ('tenant-b', 'invasao')")
            )


def test_without_tenant_policy_denies_all_rows(app_engine):
    with Session(app_engine) as session, session.begin():
        rows = session.execute(text("SELECT id FROM documents")).all()
        assert rows == []


def test_transaction_local_tenant_does_not_leak_through_pool(app_engine):
    with Session(app_engine) as session, session.begin():
        set_tenant(session, "tenant-a")
        assert documents_for_current_tenant(session)
    with Session(app_engine) as next_session, next_session.begin():
        rows = next_session.execute(text("SELECT id FROM documents")).all()
        assert rows == []


def test_superuser_bypasses_rls_even_with_force_rls(admin_engine):
    # Demonstração do limite do mecanismo: superusuários/BYPASSRLS ignoram a política.
    with admin_engine.connect() as connection:
        rows = connection.execute(text("SELECT DISTINCT tenant_id FROM documents ORDER BY tenant_id")).all()
    assert [row[0] for row in rows] == ["tenant-a", "tenant-b"]
