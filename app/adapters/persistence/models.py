"""SQLAlchemy ORM models — maps to PostgreSQL tables."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.persistence.database import Base


class OfficeModel(Base):
    __tablename__ = "offices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    managers: Mapped[list["ManagerModel"]] = relationship(back_populates="office")
    assignments: Mapped[list["AssignmentModel"]] = relationship(back_populates="office")


class ManagerModel(Base):
    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    office_id: Mapped[int] = mapped_column(Integer, ForeignKey("offices.id"), nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(20)), nullable=False, default=list)
    current_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    office: Mapped["OfficeModel"] = relationship(back_populates="managers")
    assignments: Mapped[list["AssignmentModel"]] = relationship(back_populates="manager")

    __table_args__ = (Index("idx_managers_office", "office_id"),)


class TicketModel(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[str | None] = mapped_column(String(500), nullable=True)
    segment: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    building: Mapped[str | None] = mapped_column(String(50), nullable=True)
    client_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    client_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    analytics: Mapped["TicketAnalyticsModel | None"] = relationship(
        back_populates="ticket", uselist=False
    )
    assignment: Mapped["AssignmentModel | None"] = relationship(
        back_populates="ticket", uselist=False
    )

    __table_args__ = (
        Index("idx_tickets_segment", "segment"),
        Index("idx_tickets_city", "city"),
    )


class TicketAnalyticsModel(Base):
    __tablename__ = "ticket_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    ticket_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="RU")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    ticket: Mapped["TicketModel"] = relationship(back_populates="analytics")

    __table_args__ = (
        Index("idx_analytics_type", "ticket_type"),
        Index("idx_analytics_language", "language"),
    )


class AssignmentModel(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    manager_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.id"), nullable=False
    )
    office_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("offices.id"), nullable=False
    )
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    assignment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    ticket: Mapped["TicketModel"] = relationship(back_populates="assignment")
    manager: Mapped["ManagerModel"] = relationship(back_populates="assignments")
    office: Mapped["OfficeModel"] = relationship(back_populates="assignments")

    __table_args__ = (
        Index("idx_assignments_manager", "manager_id"),
        Index("idx_assignments_office", "office_id"),
    )


class RoundRobinStateModel(Base):
    __tablename__ = "round_robin_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rr_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
