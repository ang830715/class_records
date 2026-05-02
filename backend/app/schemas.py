from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from datetime import time as Time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import ClassStatus


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    created_at: DateTime


class TeachingClassBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    classroom: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class TeachingClassCreate(TeachingClassBase):
    pass


class TeachingClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    classroom: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class TeachingClassRead(TeachingClassBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ScheduleRuleBase(BaseModel):
    user_id: int = 1
    teaching_class_id: int
    weekday: int = Field(ge=0, le=6)
    start_time: Time
    duration_minutes: int = Field(default=60, gt=0)
    active_from: Date
    active_until: Date | None = None
    is_active: bool = True
    notes: str | None = None


class ScheduleRuleCreate(ScheduleRuleBase):
    pass


class ScheduleRuleUpdate(BaseModel):
    teaching_class_id: int | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: Time | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    active_from: Date | None = None
    active_until: Date | None = None
    is_active: bool | None = None
    notes: str | None = None


class ScheduleRuleRead(ScheduleRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teaching_class: TeachingClassRead


class ClassRecordBase(BaseModel):
    user_id: int = 1
    schedule_rule_id: int | None = None
    teaching_class_id: int
    classroom: str | None = Field(default=None, max_length=120)
    date: Date
    start_time: Time
    duration_minutes: int = Field(default=60, gt=0)
    status: ClassStatus = ClassStatus.pending
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None


class ClassRecordCreate(ClassRecordBase):
    pass


class ClassRecordUpdate(BaseModel):
    schedule_rule_id: int | None = None
    teaching_class_id: int | None = None
    classroom: str | None = Field(default=None, max_length=120)
    date: Date | None = None
    start_time: Time | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    status: ClassStatus | None = None
    fee_amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class ClassRecordRead(ClassRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: DateTime
    updated_at: DateTime
    teaching_class: TeachingClassRead


class SemesterBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    start_date: Date
    end_date: Date


class SemesterCreate(SemesterBase):
    pass


class SemesterRead(SemesterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TodayItem(BaseModel):
    kind: str
    schedule_rule: ScheduleRuleRead | None = None
    record: ClassRecordRead | None = None
    expected_date: Date


class StatsByClass(BaseModel):
    teaching_class_id: int
    class_name: str
    taught_count: int
    total_minutes: int


class StatsRead(BaseModel):
    start_date: Date
    end_date: Date
    taught_count: int
    canceled_count: int
    rescheduled_count: int
    extra_count: int
    pending_count: int
    total_minutes: int
    salary: Decimal
    by_class: list[StatsByClass]


class EditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    edited_at: DateTime
