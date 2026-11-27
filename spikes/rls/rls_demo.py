"""Helpers SQLAlchemy mínimos para o spike de isolamento por tenant."""
from __future__ import annotations

from sqlalchemy import BigInteger, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


def set_tenant(session: Session, tenant_id: str) -> None:
    """Define tenant somente até o fim da transação atual (não vaza pelo pool)."""
    session.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})


def documents_for_current_tenant(session: Session) -> list[Document]:
    from sqlalchemy import select
    return list(session.scalars(select(Document).order_by(Document.id)).all())


def tenant_engine(url: str):
    from sqlalchemy import create_engine
    return create_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)
