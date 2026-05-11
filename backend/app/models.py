from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ClassStatus(StrEnum):
    taught = "taught"
    canceled = "canceled"
    rescheduled = "rescheduled"
    extra = "extra"
    pending = "pending"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeachingClass(Base):
    __tablename__ = "teaching_classes"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_teaching_classes_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(160))
    classroom: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)


class ScheduleRule(Base):
    __tablename__ = "schedule_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    teaching_class_id: Mapped[int] = mapped_column(ForeignKey("teaching_classes.id"))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    active_from: Mapped[date] = mapped_column(Date)
    active_until: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    teaching_class: Mapped[TeachingClass] = relationship()


class ClassRecord(Base):
    __tablename__ = "class_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    schedule_rule_id: Mapped[int | None] = mapped_column(ForeignKey("schedule_rules.id"))
    teaching_class_id: Mapped[int] = mapped_column(ForeignKey("teaching_classes.id"))
    classroom: Mapped[str | None] = mapped_column(String(120))
    date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[ClassStatus] = mapped_column(Enum(ClassStatus), default=ClassStatus.pending)
    fee_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    schedule_rule: Mapped[ScheduleRule | None] = relationship()
    teaching_class: Mapped[TeachingClass] = relationship()


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)


class EditLog(Base):
    __tablename__ = "edit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("class_records.id", ondelete="CASCADE"))
    field_name: Mapped[str] = mapped_column(String(80))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    record: Mapped[ClassRecord] = relationship()
