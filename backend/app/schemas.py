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


class StudentGroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    notes: str | None = None


class StudentGroupCreate(StudentGroupBase):
    pass


class StudentGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    notes: str | None = None


class StudentGroupRead(StudentGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CourseBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    default_duration_minutes: int = Field(default=60, gt=0)
    default_rate: Decimal = Field(default=Decimal("0"), ge=0)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    default_duration_minutes: int | None = Field(default=None, gt=0)
    default_rate: Decimal | None = Field(default=None, ge=0)


class CourseRead(CourseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ScheduleRuleBase(BaseModel):
    user_id: int = 1
    student_group_id: int
    course_id: int
    weekday: int = Field(ge=0, le=6)
    start_time: Time
    duration_minutes: int = Field(gt=0)
    active_from: Date
    active_until: Date | None = None
    is_active: bool = True
    notes: str | None = None


class ScheduleRuleCreate(ScheduleRuleBase):
    pass


class ScheduleRuleUpdate(BaseModel):
    student_group_id: int | None = None
    course_id: int | None = None
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
    student_group: StudentGroupRead
    course: CourseRead


class ClassRecordBase(BaseModel):
    user_id: int = 1
    schedule_rule_id: int | None = None
    student_group_id: int
    course_id: int
    date: Date
    start_time: Time
    duration_minutes: int = Field(gt=0)
    status: ClassStatus = ClassStatus.pending
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None


class ClassRecordCreate(ClassRecordBase):
    pass


class ClassRecordUpdate(BaseModel):
    schedule_rule_id: int | None = None
    student_group_id: int | None = None
    course_id: int | None = None
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
    student_group: StudentGroupRead
    course: CourseRead


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


class StatsByStudent(BaseModel):
    student_group_id: int
    student_group_name: str
    taught_count: int
    total_minutes: int
    salary: Decimal


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
    by_student: list[StatsByStudent]


class EditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    edited_at: DateTime
