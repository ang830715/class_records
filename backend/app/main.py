from datetime import date, timedelta
from decimal import Decimal
from os import getenv
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from .auth import authenticate_user, create_access_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .models import ClassRecord, ClassStatus, EditLog, ScheduleRule, Semester, TeachingClass, User
from .schedule_import import extract_schedule_from_image
from .schema_management import ensure_runtime_columns
from .schemas import (
    AccountUpdate,
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserUpdate,
    AuthTokenRead,
    ClassRecordCreate,
    ClassRecordRead,
    ClassRecordUpdate,
    EditLogRead,
    LoginRequest,
    PasswordUpdate,
    ScheduleImportResult,
    ScheduleRuleCreate,
    ScheduleRuleRead,
    ScheduleRuleUpdate,
    SemesterCreate,
    SemesterRead,
    StatsByClass,
    StatsRead,
    TeachingClassCreate,
    TeachingClassRead,
    TeachingClassUpdate,
    TodayItem,
    UserRead,
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin_user(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


AdminUser = Annotated[User, Depends(require_admin_user)]

cors_origins = [
    origin.strip()
    for origin in getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app = FastAPI(title="Teaching Record System", version="0.2.0", root_path=getenv("ROOT_PATH", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns(engine)
    with Session(engine) as db:
        user = db.get(User, 1)
        initial_email = getenv("INITIAL_ADMIN_EMAIL")
        initial_password = getenv("INITIAL_ADMIN_PASSWORD")
        initial_name = getenv("INITIAL_ADMIN_NAME", "Teacher")
        if user is None:
            user = User(id=1, name=initial_name, email=initial_email, is_active=True, is_admin=True)
            db.add(user)
        else:
            user.name = user.name or initial_name
            user.is_admin = True
            if initial_email and not user.email:
                user.email = initial_email
        if initial_password and not user.password_hash:
            user.password_hash = hash_password(initial_password)
        db.commit()


@app.post("/auth/login", response_model=AuthTokenRead)
def login(payload: LoginRequest, db: DbSession) -> AuthTokenRead:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthTokenRead(access_token=create_access_token(user), user=user)


@app.get("/auth/me", response_model=UserRead)
def me(current_user: CurrentUser) -> User:
    return current_user


@app.put("/auth/me", response_model=UserRead)
def update_me(payload: AccountUpdate, db: DbSession, current_user: CurrentUser) -> User:
    next_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == next_email, User.id != current_user.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    current_user.name = payload.name.strip()
    current_user.email = next_email
    db.commit()
    db.refresh(current_user)
    return current_user


@app.put("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(payload: PasswordUpdate, db: DbSession, current_user: CurrentUser) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def ensure_email_available(db: Session, email: str, exclude_user_id: int | None = None) -> str:
    next_email = normalize_email(email)
    query = select(User).where(func.lower(User.email) == next_email)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    existing = db.scalar(query)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    return next_email


@app.get("/admin/users", response_model=list[UserRead])
def list_admin_users(db: DbSession, current_user: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())))


@app.post("/admin/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_admin_user(payload: AdminUserCreate, db: DbSession, current_user: AdminUser) -> User:
    item = User(
        name=payload.name.strip(),
        email=ensure_email_available(db, payload.email),
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/admin/users/{user_id}", response_model=UserRead)
def update_admin_user(user_id: int, payload: AdminUserUpdate, db: DbSession, current_user: AdminUser) -> User:
    item = get_or_404(db, User, user_id)
    values = payload.model_dump(exclude_unset=True)
    if item.id == current_user.id and values.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")
    if item.id == current_user.id and values.get("is_admin") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove your own admin access")
    if "email" in values and values["email"] is not None:
        item.email = ensure_email_available(db, values["email"], exclude_user_id=item.id)
    if "name" in values and values["name"] is not None:
        item.name = values["name"].strip()
    if "is_active" in values and values["is_active"] is not None:
        item.is_active = values["is_active"]
    if "is_admin" in values and values["is_admin"] is not None:
        item.is_admin = values["is_admin"]
    db.commit()
    db.refresh(item)
    return item


@app.put("/admin/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_admin_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: DbSession,
    current_user: AdminUser,
) -> None:
    item = get_or_404(db, User, user_id)
    item.password_hash = hash_password(payload.new_password)
    db.commit()


def get_or_404(db: Session, model: type, item_id: int):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def schedule_query(user_id: int = 1) -> Select[tuple[ScheduleRule]]:
    return (
        select(ScheduleRule)
        .where(ScheduleRule.user_id == user_id)
        .options(selectinload(ScheduleRule.teaching_class))
        .order_by(ScheduleRule.weekday, ScheduleRule.start_time)
    )


def record_query(user_id: int = 1) -> Select[tuple[ClassRecord]]:
    return (
        select(ClassRecord)
        .where(ClassRecord.user_id == user_id)
        .options(selectinload(ClassRecord.teaching_class))
        .order_by(ClassRecord.date.desc(), ClassRecord.start_time.desc())
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/classes", response_model=list[TeachingClassRead])
def list_classes(db: DbSession, current_user: CurrentUser) -> list[TeachingClass]:
    return list(db.scalars(select(TeachingClass).order_by(TeachingClass.name)))


@app.post("/classes", response_model=TeachingClassRead, status_code=status.HTTP_201_CREATED)
def create_class(payload: TeachingClassCreate, db: DbSession, current_user: CurrentUser) -> TeachingClass:
    item = TeachingClass(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/classes/{class_id}", response_model=TeachingClassRead)
def update_class(class_id: int, payload: TeachingClassUpdate, db: DbSession, current_user: CurrentUser) -> TeachingClass:
    item = get_or_404(db, TeachingClass, class_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, db: DbSession, current_user: CurrentUser) -> None:
    db.delete(get_or_404(db, TeachingClass, class_id))
    db.commit()


@app.get("/schedule", response_model=list[ScheduleRuleRead])
def list_schedule(db: DbSession, current_user: CurrentUser) -> list[ScheduleRule]:
    return list(db.scalars(schedule_query(current_user.id)))


@app.post("/schedule", response_model=ScheduleRuleRead, status_code=status.HTTP_201_CREATED)
def create_schedule_rule(payload: ScheduleRuleCreate, db: DbSession, current_user: CurrentUser) -> ScheduleRule:
    if payload.active_until and payload.active_until < payload.active_from:
        raise HTTPException(status_code=400, detail="active_until must be after active_from")
    get_or_404(db, TeachingClass, payload.teaching_class_id)
    values = payload.model_dump()
    values["user_id"] = current_user.id
    item = ScheduleRule(**values)
    db.add(item)
    db.commit()
    return get_or_404(db, ScheduleRule, item.id)


@app.put("/schedule/{rule_id}", response_model=ScheduleRuleRead)
def update_schedule_rule(rule_id: int, payload: ScheduleRuleUpdate, db: DbSession, current_user: CurrentUser) -> ScheduleRule:
    item = get_or_404(db, ScheduleRule, rule_id)
    if item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    values = payload.model_dump(exclude_unset=True)
    if "teaching_class_id" in values and values["teaching_class_id"] is not None:
        get_or_404(db, TeachingClass, values["teaching_class_id"])
    active_from = values.get("active_from", item.active_from)
    active_until = values.get("active_until", item.active_until)
    if active_until and active_until < active_from:
        raise HTTPException(status_code=400, detail="active_until must be after active_from")
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    return get_or_404(db, ScheduleRule, rule_id)


@app.delete("/schedule", status_code=status.HTTP_204_NO_CONTENT)
def clear_schedule(db: DbSession, current_user: CurrentUser) -> None:
    rule_ids = list(db.scalars(select(ScheduleRule.id).where(ScheduleRule.user_id == current_user.id)))
    if not rule_ids:
        return
    db.execute(
        update(ClassRecord)
        .where(ClassRecord.user_id == current_user.id, ClassRecord.schedule_rule_id.in_(rule_ids))
        .values(schedule_rule_id=None)
    )
    db.execute(delete(ScheduleRule).where(ScheduleRule.user_id == current_user.id, ScheduleRule.id.in_(rule_ids)))
    db.commit()


@app.delete("/schedule/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_rule(rule_id: int, db: DbSession, current_user: CurrentUser) -> None:
    item = get_or_404(db, ScheduleRule, rule_id)
    if item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.execute(
        update(ClassRecord)
        .where(ClassRecord.user_id == current_user.id, ClassRecord.schedule_rule_id == item.id)
        .values(schedule_rule_id=None)
    )
    db.delete(item)
    db.commit()


@app.post("/schedule/import-image", response_model=ScheduleImportResult)
async def import_schedule_image(current_user: CurrentUser, image: UploadFile = File(...)) -> ScheduleImportResult:
    return await run_in_threadpool(extract_schedule_from_image, await image.read(), image.content_type or "")


@app.get("/records", response_model=list[ClassRecordRead])
def list_records(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ClassRecord]:
    query = record_query(current_user.id)
    if start_date:
        query = query.where(ClassRecord.date >= start_date)
    if end_date:
        query = query.where(ClassRecord.date <= end_date)
    return list(db.scalars(query))


@app.post("/records", response_model=ClassRecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: ClassRecordCreate, db: DbSession, current_user: CurrentUser) -> ClassRecord:
    get_or_404(db, TeachingClass, payload.teaching_class_id)
    if payload.schedule_rule_id is not None:
        rule = get_or_404(db, ScheduleRule, payload.schedule_rule_id)
        if rule.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    values = payload.model_dump()
    values["user_id"] = current_user.id
    item = ClassRecord(**values)
    db.add(item)
    db.commit()
    return get_or_404(db, ClassRecord, item.id)


@app.put("/records/{record_id}", response_model=ClassRecordRead)
def update_record(record_id: int, payload: ClassRecordUpdate, db: DbSession, current_user: CurrentUser) -> ClassRecord:
    item = get_or_404(db, ClassRecord, record_id)
    if item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    values = payload.model_dump(exclude_unset=True)
    if "teaching_class_id" in values and values["teaching_class_id"] is not None:
        get_or_404(db, TeachingClass, values["teaching_class_id"])
    if "schedule_rule_id" in values and values["schedule_rule_id"] is not None:
        rule = get_or_404(db, ScheduleRule, values["schedule_rule_id"])
        if rule.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    for key, value in values.items():
        old_value = getattr(item, key)
        if old_value != value:
            db.add(
                EditLog(
                    record_id=item.id,
                    field_name=key,
                    old_value=None if old_value is None else str(old_value),
                    new_value=None if value is None else str(value),
                )
            )
            setattr(item, key, value)
    db.commit()
    return get_or_404(db, ClassRecord, record_id)


@app.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: DbSession, current_user: CurrentUser) -> None:
    item = get_or_404(db, ClassRecord, record_id)
    if item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.delete(item)
    db.commit()


@app.get("/records/{record_id}/edits", response_model=list[EditLogRead])
def list_record_edits(record_id: int, db: DbSession, current_user: CurrentUser) -> list[EditLog]:
    record = get_or_404(db, ClassRecord, record_id)
    if record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return list(db.scalars(select(EditLog).where(EditLog.record_id == record_id).order_by(EditLog.edited_at.desc())))


@app.get("/today", response_model=list[TodayItem])
def today(db: DbSession, current_user: CurrentUser, target_date: date | None = None) -> list[TodayItem]:
    target = target_date or date.today()
    user_id = current_user.id
    schedules = list(
        db.scalars(
            schedule_query(user_id)
            .where(ScheduleRule.weekday == target.weekday())
            .where(ScheduleRule.is_active.is_(True))
            .where(ScheduleRule.active_from <= target)
            .where((ScheduleRule.active_until.is_(None)) | (ScheduleRule.active_until >= target))
        )
    )
    records = list(db.scalars(record_query(user_id).where(ClassRecord.date == target)))
    records_by_schedule = {record.schedule_rule_id: record for record in records if record.schedule_rule_id is not None}
    items: list[TodayItem] = []
    for rule in schedules:
        record = records_by_schedule.get(rule.id)
        items.append(
            TodayItem(
                kind="matched" if record else "expected",
                schedule_rule=rule,
                record=record,
                expected_date=target,
            )
        )
    scheduled_ids = {rule.id for rule in schedules}
    for record in records:
        if record.schedule_rule_id not in scheduled_ids:
            items.append(TodayItem(kind="actual", schedule_rule=None, record=record, expected_date=target))
    return sorted(items, key=lambda item: (item.record.start_time if item.record else item.schedule_rule.start_time))


@app.get("/missing-days", response_model=list[date])
def missing_days(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> list[date]:
    user_id = current_user.id
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    rules = list(db.scalars(schedule_query(user_id).where(ScheduleRule.is_active.is_(True))))
    records = {
        row[0]
        for row in db.execute(
            select(ClassRecord.date).where(
                ClassRecord.user_id == user_id,
                ClassRecord.date >= start_date,
                ClassRecord.date <= end_date,
            )
        )
    }
    missing: list[date] = []
    current = start_date
    while current <= end_date:
        has_schedule = any(
            rule.weekday == current.weekday()
            and rule.active_from <= current
            and (rule.active_until is None or rule.active_until >= current)
            for rule in rules
        )
        if has_schedule and current not in records:
            missing.append(current)
        current += timedelta(days=1)
    return missing


@app.get("/stats", response_model=StatsRead)
def stats(
    db: DbSession,
    current_user: CurrentUser,
    range: str = Query(default="month", pattern="^(week|month|semester|custom)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    semester_id: int | None = None,
) -> StatsRead:
    user_id = current_user.id
    today_date = date.today()
    if range == "week":
        start = today_date - timedelta(days=today_date.weekday())
        end = start + timedelta(days=6)
    elif range == "month":
        start = today_date.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
    elif range == "semester":
        semester = db.get(Semester, semester_id) if semester_id else db.scalar(
            select(Semester)
            .where(Semester.start_date <= today_date, Semester.end_date >= today_date)
            .order_by(Semester.start_date.desc())
        )
        if semester is None:
            raise HTTPException(status_code=404, detail="No matching semester found")
        start, end = semester.start_date, semester.end_date
    else:
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="custom range requires start_date and end_date")
        start, end = start_date, end_date
    if end < start:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    records = list(
        db.scalars(
            record_query(user_id)
            .where(ClassRecord.date >= start)
            .where(ClassRecord.date <= end)
        )
    )

    def count(record_status: ClassStatus) -> int:
        return sum(1 for record in records if record.status == record_status)

    taught_records = [record for record in records if record.status == ClassStatus.taught]
    salary = sum((Decimal(record.fee_amount) for record in taught_records), Decimal("0"))
    total_minutes = sum(record.duration_minutes for record in taught_records)
    by_class_rows = db.execute(
        select(
            TeachingClass.id,
            TeachingClass.name,
            func.count(ClassRecord.id),
            func.coalesce(func.sum(ClassRecord.duration_minutes), 0),
        )
        .join(ClassRecord, ClassRecord.teaching_class_id == TeachingClass.id)
        .where(
            ClassRecord.user_id == user_id,
            ClassRecord.date >= start,
            ClassRecord.date <= end,
            ClassRecord.status == ClassStatus.taught,
        )
        .group_by(TeachingClass.id, TeachingClass.name)
        .order_by(TeachingClass.name)
    )

    return StatsRead(
        start_date=start,
        end_date=end,
        taught_count=count(ClassStatus.taught),
        canceled_count=count(ClassStatus.canceled),
        rescheduled_count=count(ClassStatus.rescheduled),
        extra_count=count(ClassStatus.extra),
        pending_count=count(ClassStatus.pending),
        total_minutes=total_minutes,
        salary=salary,
        by_class=[
            StatsByClass(
                teaching_class_id=row[0],
                class_name=row[1],
                taught_count=row[2],
                total_minutes=row[3],
            )
            for row in by_class_rows
        ],
    )


@app.get("/semesters", response_model=list[SemesterRead])
def list_semesters(db: DbSession, current_user: CurrentUser) -> list[Semester]:
    return list(db.scalars(select(Semester).order_by(Semester.start_date.desc())))


@app.post("/semesters", response_model=SemesterRead, status_code=status.HTTP_201_CREATED)
def create_semester(payload: SemesterCreate, db: DbSession, current_user: CurrentUser) -> Semester:
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    item = Semester(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
