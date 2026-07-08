
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DB_URL = os.getenv("PROPINA360_DB_URL", "sqlite:///./propina360.db")
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
SIGNING_KEY = os.getenv("PROPINA360_SIGNING_KEY", "dev-local-key")


def now() -> dt.datetime:
    return dt.datetime.utcnow()


def current_period_key() -> tuple[int, int]:
    today = dt.date.today()
    return today.year, today.month


def clp(value: int | Decimal) -> str:
    return "$" + f"{int(value):,}".replace(",", ".") + " CLP"


def round_down_10(value: Decimal) -> int:
    amount = int(value.to_integral_value(rounding=ROUND_DOWN))
    return amount - (amount % 10)


def normalize_run(run: str) -> str:
    return "".join(ch for ch in run.upper() if ch.isdigit() or ch == "K")


def validate_run(run: str) -> bool:
    value = normalize_run(run)
    if len(value) < 2:
        return False
    body, dv = value[:-1], value[-1]
    factor = 2
    total = 0
    for digit in reversed(body):
        if not digit.isdigit():
            return False
        total += int(digit) * factor
        factor = 2 if factor == 7 else factor + 1
    expected_raw = 11 - (total % 11)
    expected = "0" if expected_raw == 11 else "K" if expected_raw == 10 else str(expected_raw)
    return dv == expected


def internal_code(run: str) -> str:
    value = normalize_run(run)
    return "TRAB-" + value[:-1]


def hash_pass(plain: str, email: str) -> str:
    salt = hashlib.sha256(email.lower().encode()).hexdigest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 90000).hex()
    return f"pbkdf2${salt}${digest}"


def check_pass(plain: str, stored: str, email: str) -> bool:
    return hmac.compare_digest(hash_pass(plain, email), stored)


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def make_token(user: "User") -> str:
    payload = {"sub": user.id, "role": user.role.name, "exp": (now() + dt.timedelta(hours=8)).isoformat()}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(SIGNING_KEY.encode(), raw, hashlib.sha256).digest()
    return b64(raw) + "." + b64(sig)


def read_token(token: str) -> dict[str, Any]:
    try:
        raw_part, sig_part = token.split(".", 1)
        raw = base64.urlsafe_b64decode(raw_part + "=" * (-len(raw_part) % 4))
        expected = b64(hmac.new(SIGNING_KEY.encode(), raw, hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig_part):
            raise ValueError("bad signature")
        payload = json.loads(raw)
        if dt.datetime.fromisoformat(payload["exp"]) < now():
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="token invalido") from exc


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(180), unique=True, nullable=False, index=True)
    pass_hash = Column(String(220), nullable=False)
    first_name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    phone = Column(String(30), nullable=False, default="")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    status = Column(String(40), nullable=False, default="pending_approval")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    role = relationship("Role")
    worker = relationship("Worker", back_populates="user", uselist=False)


class WorkerRegistrationRequest(Base):
    __tablename__ = "worker_registration_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(30), default="pending")
    decision_reason = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    user = relationship("User")


class Section(Base):
    __tablename__ = "sections"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    active = Column(Boolean, default=True)


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)


class ContractType(Base):
    __tablename__ = "contract_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True, nullable=False)


class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    run = Column(String(20), unique=True, nullable=False)
    internal_code = Column(String(30), unique=True, nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    contract_type_id = Column(Integer, ForeignKey("contract_types.id"), nullable=False)
    status = Column(String(30), default="active")
    hired_at = Column(Date, default=dt.date.today)
    user = relationship("User", back_populates="worker")
    section = relationship("Section")
    position = relationship("Position")
    contract_type = relationship("ContractType")
    points_history = relationship("WorkerPointsHistory", back_populates="worker")


class WorkerPointsHistory(Base):
    __tablename__ = "worker_points_history"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    points = Column(Integer, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    reason = Column(String(240), default="initial")
    worker = relationship("Worker", back_populates="points_history")


class Period(Base):
    __tablename__ = "periods"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    status = Column(String(30), default="open")
    __table_args__ = (UniqueConstraint("year", "month", name="uq_period"),)


class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    shift_date = Column(Date, nullable=False)
    shift_type = Column(String(30), default="regular")
    status = Column(String(30), default="worked")
    start_time = Column(String(10), default="")
    end_time = Column(String(10), default="")
    worked_minutes = Column(Integer, default=480)
    void_reason = Column(Text, default="")
    worker = relationship("Worker")
    __table_args__ = (UniqueConstraint("worker_id", "shift_date", "shift_type", name="uq_shift_day_type"),)


class DailyTipFund(Base):
    __tablename__ = "daily_tip_funds"
    id = Column(Integer, primary_key=True)
    tip_date = Column(Date, unique=True, nullable=False)
    amount_clp = Column(Integer, nullable=False)
    point_value_clp = Column(Numeric(12, 2), default=0)
    status = Column(String(30), default="registered")
    notes = Column(Text, default="")


class DailyTipCalculation(Base):
    __tablename__ = "daily_tip_calculations"
    id = Column(Integer, primary_key=True)
    tip_date = Column(Date, unique=True, nullable=False)
    total_points = Column(Integer, default=0)
    total_amount_clp = Column(Integer, default=0)
    total_payable_clp = Column(Integer, default=0)
    total_remainder_clp = Column(Numeric(12, 2), default=0)
    calculated_at = Column(DateTime, default=now)


class DailyTipCalculationDetail(Base):
    __tablename__ = "daily_tip_calculation_details"
    id = Column(Integer, primary_key=True)
    calculation_id = Column(Integer, ForeignKey("daily_tip_calculations.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    points_used = Column(Integer, nullable=False)
    eligible = Column(Boolean, default=True)
    raw_amount_clp = Column(Numeric(12, 2), nullable=False)
    payable_amount_clp = Column(Integer, nullable=False)
    rounding_remainder_clp = Column(Numeric(12, 2), nullable=False)
    worker = relationship("Worker")


class RoundingRemainder(Base):
    __tablename__ = "rounding_remainders"
    id = Column(Integer, primary_key=True)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=False)
    source_date = Column(Date, nullable=False)
    amount_clp = Column(Numeric(12, 2), nullable=False)
    status = Column(String(30), default="pending")


class AdvanceRequest(Base):
    __tablename__ = "advance_requests"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=False)
    amount_clp = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="pending")
    decision_reason = Column(Text, default="")
    requested_at = Column(DateTime, default=now)
    worker = relationship("Worker")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=False)
    gross_amount_clp = Column(Integer, default=0)
    advance_discount_clp = Column(Integer, default=0)
    adjustment_amount_clp = Column(Integer, default=0)
    net_amount_clp = Column(Integer, default=0)
    paid_amount_clp = Column(Integer, default=0)
    status = Column(String(30), default="prepared")
    paid_at = Column(DateTime, nullable=True)
    worker = relationship("Worker")


class ShiftClaim(Base):
    __tablename__ = "shift_claims"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    claimed_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(30), default="pending")
    resolution = Column(Text, default="")
    worker = relationship("Worker")


class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)
    value = Column(String(240), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    module = Column(String(80), nullable=False)
    action = Column(String(80), nullable=False)
    entity_name = Column(String(80), nullable=False)
    entity_id = Column(Integer, nullable=True)
    new_values_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=now)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def item(obj: Any) -> dict[str, Any]:
    data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for key, value in list(data.items()):
        if isinstance(value, (dt.date, dt.datetime)):
            data[key] = value.isoformat()
        if isinstance(value, Decimal):
            data[key] = float(value)
    if isinstance(obj, Worker):
        data.update(
            {
                "email": obj.user.email,
                "first_name": obj.user.first_name,
                "last_name": obj.user.last_name,
                "section": obj.section.name,
                "position": obj.position.name,
                "contract_type": obj.contract_type.name,
                "points": current_points(obj),
            }
        )
    return data


def registration_item(db: Session, user: User) -> dict[str, Any]:
    req = db.query(WorkerRegistrationRequest).filter_by(user_id=user.id).first()
    data = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "request_id": req.id if req else None,
        "request_status": req.status if req else "",
        "decision_reason": req.decision_reason if req else "",
        "request_created_at": req.created_at.isoformat() if req and req.created_at else "",
    }
    return data


def audit(db: Session, user_id: int | None, module: str, action: str, entity: str, entity_id: int | None, values: dict[str, Any]) -> None:
    db.add(AuditLog(user_id=user_id, module=module, action=action, entity_name=entity, entity_id=entity_id, new_values_json=json.dumps(values, default=str)))


def ensure_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        db.add(role)
        db.flush()
    return role


def ensure_named(db: Session, model: Any, name: str) -> Any:
    row = db.query(model).filter_by(name=name).first()
    if not row:
        row = model(name=name)
        db.add(row)
        db.flush()
    return row


def ensure_period(db: Session, year: int | None = None, month: int | None = None) -> Period:
    if year is None or month is None:
        year, month = current_period_key()
    period = db.query(Period).filter_by(year=year, month=month).first()
    if not period:
        period = Period(year=year, month=month)
        db.add(period)
        db.flush()
    return period


def current_points(worker: Worker, on_date: dt.date | None = None) -> int:
    on_date = on_date or dt.date.today()
    points = [
        row.points
        for row in worker.points_history
        if row.valid_from <= on_date and (row.valid_to is None or row.valid_to >= on_date)
    ]
    return points[-1] if points else 0


def create_worker(db: Session, user: User, payload: dict[str, Any]) -> Worker:
    run = payload.get("run", "")
    if not validate_run(run):
        raise HTTPException(status_code=422, detail="RUN chileno invalido")
    section = db.get(Section, int(payload.get("section_id") or ensure_named(db, Section, "Salon").id))
    position = db.get(Position, int(payload.get("position_id") or ensure_named(db, Position, "Garzon").id))
    contract = db.get(ContractType, int(payload.get("contract_type_id") or ensure_named(db, ContractType, "fulltime").id))
    points = int(payload.get("points", 10))
    if points < 6 or points > 20:
        raise HTTPException(status_code=422, detail="puntos fuera de rango")
    worker = Worker(
        user=user,
        run=run,
        internal_code=internal_code(run),
        section=section,
        position=position,
        contract_type=contract,
        status=payload.get("status", "active"),
    )
    db.add(worker)
    db.flush()
    db.add(WorkerPointsHistory(worker=worker, points=points, valid_from=dt.date.fromisoformat(payload.get("valid_from", dt.date.today().isoformat())), reason="alta"))
    user.status = "approved"
    return worker


def eligible_workers(db: Session, tip_date: dt.date) -> list[tuple[Worker, int]]:
    workers = db.query(Worker).filter_by(status="active").all()
    result: list[tuple[Worker, int]] = []
    for worker in workers:
        points = current_points(worker, tip_date)
        if points <= 0:
            continue
        worked = db.query(Shift).filter_by(worker_id=worker.id, shift_date=tip_date).filter(Shift.status.in_(["worked", "corrected"])).first()
        absent = db.query(Shift).filter_by(worker_id=worker.id, shift_date=tip_date, status="absent").first()
        if worker.contract_type.name == "fulltime" and not absent:
            result.append((worker, points))
        elif worker.contract_type.name == "parttime" and worked:
            result.append((worker, points))
    return result


def calculate_daily(db: Session, tip_date: dt.date) -> dict[str, Any]:
    fund = db.query(DailyTipFund).filter_by(tip_date=tip_date).first()
    if not fund:
        raise HTTPException(status_code=404, detail="propina diaria no registrada")
    db.query(DailyTipCalculationDetail).filter(DailyTipCalculationDetail.calculation_id.in_(db.query(DailyTipCalculation.id).filter_by(tip_date=tip_date))).delete(synchronize_session=False)
    db.query(DailyTipCalculation).filter_by(tip_date=tip_date).delete()
    participants = eligible_workers(db, tip_date)
    if fund.amount_clp > 0 and not participants:
        raise HTTPException(status_code=422, detail="sin trabajadores elegibles")
    calc = DailyTipCalculation(tip_date=tip_date, total_amount_clp=fund.amount_clp)
    db.add(calc)
    db.flush()
    total_points = sum(points for _, points in participants)
    total_payable = 0
    total_remainder = Decimal("0")
    for worker, points in participants:
        raw = Decimal(fund.amount_clp) * Decimal(points) / Decimal(total_points or 1)
        payable = round_down_10(raw)
        rem = raw - Decimal(payable)
        total_payable += payable
        total_remainder += rem
        db.add(DailyTipCalculationDetail(calculation_id=calc.id, worker_id=worker.id, points_used=points, raw_amount_clp=raw, payable_amount_clp=payable, rounding_remainder_clp=rem))
    calc.total_points = total_points
    calc.total_payable_clp = total_payable
    calc.total_remainder_clp = total_remainder
    fund.point_value_clp = Decimal(fund.amount_clp) / Decimal(total_points) if total_points else Decimal("0")
    fund.status = "calculated"
    period = ensure_period(db, tip_date.year, tip_date.month)
    db.add(RoundingRemainder(period_id=period.id, source_date=tip_date, amount_clp=total_remainder, status="pending"))
    db.commit()
    return {"calculation": item(calc), "details": [item(row) for row in db.query(DailyTipCalculationDetail).filter_by(calculation_id=calc.id).all()]}


def worker_balance(db: Session, worker_id: int, period: Period) -> dict[str, int]:
    details = (
        db.query(DailyTipCalculationDetail)
        .join(DailyTipCalculation, DailyTipCalculation.id == DailyTipCalculationDetail.calculation_id)
        .filter(DailyTipCalculationDetail.worker_id == worker_id)
        .filter(DailyTipCalculation.tip_date >= dt.date(period.year, period.month, 1))
        .filter(DailyTipCalculation.tip_date < (dt.date(period.year + (period.month // 12), (period.month % 12) + 1, 1)))
        .all()
    )
    gross = sum(int(row.payable_amount_clp) for row in details)
    advances = sum(row.amount_clp for row in db.query(AdvanceRequest).filter_by(worker_id=worker_id, period_id=period.id, status="approved").all())
    return {"gross": gross, "advances": advances, "net": max(0, gross - advances)}


def prepare_worker_payment(db: Session, worker_id: int, period_id: int) -> Payment:
    period = db.get(Period, period_id)
    bal = worker_balance(db, worker_id, period)
    payment = db.query(Payment).filter_by(worker_id=worker_id, period_id=period_id).first()
    if not payment:
        payment = Payment(worker_id=worker_id, period_id=period_id)
        db.add(payment)
    payment.gross_amount_clp = bal["gross"]
    payment.advance_discount_clp = bal["advances"]
    payment.net_amount_clp = bal["net"]
    if payment.status != "paid":
        payment.status = "prepared"
    return payment


def ensure_schema_compatibility() -> None:
    if not DB_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(daily_tip_funds)").fetchall()}
        if "point_value_clp" not in columns:
            conn.exec_driver_sql("ALTER TABLE daily_tip_funds ADD COLUMN point_value_clp NUMERIC(12, 2) DEFAULT 0")


def seed_data() -> None:
    Base.metadata.create_all(engine)
    ensure_schema_compatibility()
    db = SessionLocal()
    try:
        admin_role = ensure_role(db, "admin")
        worker_role = ensure_role(db, "worker")
        cocina = ensure_named(db, Section, "Cocina")
        barra = ensure_named(db, Section, "Barra")
        salon = ensure_named(db, Section, "Salon")
        caja = ensure_named(db, Section, "Caja")
        garzon = ensure_named(db, Position, "Garzon")
        cajero = ensure_named(db, Position, "Cajero")
        cocinero = ensure_named(db, Position, "Cocinero")
        full = ensure_named(db, ContractType, "fulltime")
        part = ensure_named(db, ContractType, "parttime")
        ensure_period(db)
        for key, value in [("currency", "CLP"), ("max_daily_tip_clp", "5000000"), ("allow_advance_overdraft", "false")]:
            if not db.query(SystemSetting).filter_by(key=key).first():
                db.add(SystemSetting(key=key, value=value))
        if not db.query(User).filter_by(email="admin@propina360.local").first():
            db.add(User(email="admin@propina360.local", pass_hash=hash_pass("Admin-123!", "admin@propina360.local"), first_name="Administrador", last_name="Sistema", phone="+56900000000", role=admin_role, status="active"))
        fixtures = [
            ("Ana", "Munoz", "ana.munoz@test.local", "+56911111111", "11.111.111-1", full, 10, cocina, cocinero),
            ("Bruno", "Paredes", "bruno.paredes@test.local", "+56922222222", "12.345.678-5", part, 7, barra, garzon),
            ("Camila", "Rojas", "camila.rojas@test.local", "+56933333333", "14.000.000-0", full, 12, salon, garzon),
            ("Diego", "Soto", "diego.soto@test.local", "+56944444444", "17.000.000-5", part, 6, salon, garzon),
            ("Elisa", "Vargas", "elisa.vargas@test.local", "+56955555555", "19.000.000-1", full, 9, caja, cajero),
        ]
        for first, last, email, phone, run, contract, points, section, position in fixtures:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(email=email, pass_hash=hash_pass("Worker-123!", email), first_name=first, last_name=last, phone=phone, role=worker_role, status="approved")
                db.add(user)
                db.flush()
            if not user.worker:
                worker = Worker(user=user, run=run, internal_code=internal_code(run), section=section, position=position, contract_type=contract, status="active")
                db.add(worker)
                db.flush()
                db.add(WorkerPointsHistory(worker=worker, points=points, valid_from=dt.date(dt.date.today().year, dt.date.today().month, 1), reason="seed"))
        db.commit()
    finally:
        db.close()


def reset_database() -> None:
    Base.metadata.drop_all(engine)
    seed_data()


seed_data()
app = FastAPI(title="Propina360 API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="falta token")
    payload = read_token(authorization.removeprefix("Bearer ").strip())
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="usuario no existe")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="solo administrador")
    return user


def require_worker(user: User = Depends(current_user)) -> User:
    if user.role.name != "worker" or user.status != "approved" or not user.worker or user.worker.status != "active":
        raise HTTPException(status_code=403, detail="solo trabajador activo")
    return user


@app.get("/")
@app.get("/admin")
@app.get("/admin/{path:path}")
@app.get("/dashboard")
@app.get("/dashboard/{path:path}")
def spa() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "propina360", "currency": "CLP"}


@app.post("/api/auth/register")
def register(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    required = ["email", "first_name", "last_name", "phone", "clave"]
    if any(not payload.get(key) for key in required):
        raise HTTPException(status_code=422, detail="faltan campos obligatorios")
    if db.query(User).filter_by(email=payload["email"].lower()).first():
        raise HTTPException(status_code=409, detail="email duplicado")
    role = db.query(Role).filter_by(name="worker").one()
    user = User(email=payload["email"].lower(), pass_hash=hash_pass(payload["clave"], payload["email"].lower()), first_name=payload["first_name"], last_name=payload["last_name"], phone=payload["phone"], role=role, status="pending_approval")
    db.add(user)
    db.flush()
    db.add(WorkerRegistrationRequest(user_id=user.id))
    audit(db, user.id, "auth", "register", "users", user.id, {"status": user.status})
    db.commit()
    return {"status": "pending_approval", "user_id": user.id, "message": "peticion creada, usuario pendiente de confirmacion"}


def login_common(payload: dict[str, Any], db: Session, admin: bool) -> dict[str, Any]:
    user = db.query(User).filter_by(email=payload.get("email", "").lower()).first()
    if not user or not check_pass(payload.get("clave", ""), user.pass_hash, user.email):
        raise HTTPException(status_code=401, detail="credenciales invalidas")
    if admin and user.role.name != "admin":
        raise HTTPException(status_code=403, detail="ruta administrativa")
    if not admin and user.role.name != "worker":
        raise HTTPException(status_code=403, detail="use /admin")
    if user.role.name == "worker" and user.status != "approved":
        raise HTTPException(status_code=403, detail="usuario pendiente de aprobacion")
    return {"access_token": make_token(user), "token_type": "bearer", "role": user.role.name, "user": item(user)}


@app.post("/api/auth/login")
def login(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    return login_common(payload, db, admin=False)


@app.post("/api/auth/admin/login")
def admin_login(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    return login_common(payload, db, admin=True)


@app.post("/api/auth/logout")
def logout(user: User = Depends(current_user)) -> dict[str, str]:
    return {"status": "closed"}


@app.post("/api/auth/refresh")
def refresh(user: User = Depends(current_user)) -> dict[str, str]:
    return {"access_token": make_token(user), "token_type": "bearer"}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)) -> dict[str, Any]:
    return {"user": item(user), "worker": item(user.worker) if user.worker else None}


@app.post("/api/auth/password/forgot")
@app.post("/api/auth/password/reset")
def pass_flow() -> dict[str, str]:
    return {"status": "accepted_for_development"}


@app.get("/api/admin/dashboard/summary")
def admin_summary(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    period = ensure_period(db)
    tips = db.query(DailyTipFund).all()
    calc = db.query(DailyTipCalculation).all()
    pending_advances = db.query(AdvanceRequest).filter_by(status="pending").count()
    approved_advances = db.query(AdvanceRequest).filter_by(period_id=period.id, status="approved").all()
    return {
        "active_workers": db.query(Worker).filter_by(status="active").count(),
        "pending_users": db.query(WorkerRegistrationRequest).filter_by(status="pending").count(),
        "registered_tip_clp": sum(t.amount_clp for t in tips),
        "calculated_tip_clp": sum(c.total_payable_clp for c in calc),
        "pending_advances": pending_advances,
        "approved_advances_clp": sum(a.amount_clp for a in approved_advances),
        "estimated_payable_clp": sum(worker_balance(db, w.id, period)["net"] for w in db.query(Worker).all()),
        "days_with_tip": len(tips),
        "days_pending_calculation": len([t for t in tips if t.status != "calculated"]),
        "pending_shift_claims": db.query(ShiftClaim).filter_by(status="pending").count(),
        "period": f"{period.year}-{period.month:02d}",
    }


@app.get("/api/admin/dashboard/current-period")
def admin_current_period(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    period = ensure_period(db)
    return item(period)


@app.get("/api/admin/pending-users")
def pending_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    rows = db.query(WorkerRegistrationRequest).order_by(WorkerRegistrationRequest.id.desc()).all()
    return [registration_item(db, db.get(User, row.user_id)) for row in rows]


@app.get("/api/admin/pending-users/{user_id}")
def pending_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="usuario no existe")
    return registration_item(db, user)


@app.patch("/api/admin/pending-users/{user_id}/approve")
def approve_user(user_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user or user.status != "pending_approval":
        raise HTTPException(status_code=422, detail="usuario no pendiente")
    reason = payload.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="razon requerida")
    user.status = "approved_pending_profile"
    req = db.query(WorkerRegistrationRequest).filter_by(user_id=user.id).first()
    if req:
        req.status = "approved_pending_profile"
        req.decision_reason = reason
    audit(db, admin.id, "admin", "approve_user_request", "users", user.id, {"reason": reason, "status": user.status})
    db.commit()
    return registration_item(db, user)


@app.post("/api/admin/pending-users/{user_id}/complete-worker")
def complete_pending_user_worker(user_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user or user.status != "approved_pending_profile":
        raise HTTPException(status_code=422, detail="usuario no aprobado para completar ficha")
    worker = create_worker(db, user, payload)
    req = db.query(WorkerRegistrationRequest).filter_by(user_id=user.id).first()
    if req:
        req.status = "completed"
    audit(db, admin.id, "admin", "complete_user_worker", "workers", worker.id, item(worker))
    db.commit()
    db.refresh(worker)
    return item(worker)


@app.patch("/api/admin/pending-users/{user_id}/reject")
def reject_user(user_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user or user.status != "pending_approval":
        raise HTTPException(status_code=422, detail="usuario no pendiente")
    reason = payload.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="razon requerida")
    user.status = "rejected"
    req = db.query(WorkerRegistrationRequest).filter_by(user_id=user.id).first()
    if req:
        req.status = "rejected"
        req.decision_reason = reason
    audit(db, admin.id, "admin", "reject_user", "users", user.id, {"reason": reason})
    db.commit()
    return registration_item(db, user)


@app.get("/api/admin/workers")
def workers(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(w) for w in db.query(Worker).all()]


@app.post("/api/admin/workers")
def workers_create(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    email = payload["email"].lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="email duplicado")
    role = db.query(Role).filter_by(name="worker").one()
    user = User(email=email, pass_hash=hash_pass(payload.get("clave", "Worker-123!"), email), first_name=payload["first_name"], last_name=payload["last_name"], phone=payload.get("phone", ""), role=role, status="approved")
    db.add(user)
    db.flush()
    worker = create_worker(db, user, payload)
    audit(db, admin.id, "workers", "create", "workers", worker.id, item(worker))
    db.commit()
    db.refresh(worker)
    return item(worker)


@app.get("/api/admin/workers/{worker_id}")
def workers_get(worker_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="no existe")
    return item(worker)


@app.put("/api/admin/workers/{worker_id}")
def workers_update(worker_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="no existe")
    if "run" in payload:
        if not validate_run(payload["run"]):
            raise HTTPException(status_code=422, detail="RUN chileno invalido")
        worker.run = payload["run"]
        worker.internal_code = internal_code(payload["run"])
    for attr in ["section_id", "position_id", "contract_type_id", "status"]:
        if attr in payload:
            setattr(worker, attr, payload[attr])
    for attr in ["first_name", "last_name", "phone"]:
        if attr in payload:
            setattr(worker.user, attr, payload[attr])
    audit(db, admin.id, "workers", "update", "workers", worker.id, payload)
    db.commit()
    db.refresh(worker)
    return item(worker)


@app.patch("/api/admin/workers/{worker_id}/activate")
@app.patch("/api/admin/workers/{worker_id}/deactivate")
def workers_toggle(worker_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    worker = db.get(Worker, worker_id)
    worker.status = "active" if request.url.path.endswith("activate") else "inactive"
    audit(db, admin.id, "workers", worker.status, "workers", worker.id, {})
    db.commit()
    return item(worker)


@app.get("/api/admin/workers/{worker_id}/points")
def worker_points(worker_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(p) for p in db.query(WorkerPointsHistory).filter_by(worker_id=worker_id).all()]


@app.post("/api/admin/workers/{worker_id}/points")
def worker_points_create(worker_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    points = int(payload["points"])
    if points < 6 or points > 20:
        raise HTTPException(status_code=422, detail="puntos fuera de rango")
    row = WorkerPointsHistory(worker_id=worker_id, points=points, valid_from=dt.date.fromisoformat(payload.get("valid_from", dt.date.today().isoformat())), reason=payload.get("reason", "ajuste"))
    db.add(row)
    audit(db, admin.id, "workers", "points", "worker_points_history", worker_id, payload)
    db.commit()
    return item(row)


@app.put("/api/admin/workers/{worker_id}/points/{point_id}")
def worker_points_update(worker_id: int, point_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = db.get(WorkerPointsHistory, point_id)
    row.points = int(payload.get("points", row.points))
    row.reason = payload.get("reason", row.reason)
    db.commit()
    return item(row)


@app.get("/api/admin/contracts")
def contracts(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(c) for c in db.query(ContractType).all()]


@app.get("/api/admin/sections")
def sections(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(s) for s in db.query(Section).all()]


@app.post("/api/admin/sections")
def sections_create(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = Section(name=payload["name"], active=True)
    db.add(row)
    db.commit()
    return item(row)


@app.put("/api/admin/sections/{section_id}")
def sections_update(section_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = db.get(Section, section_id)
    row.name = payload.get("name", row.name)
    row.active = bool(payload.get("active", row.active))
    db.commit()
    return item(row)


@app.get("/api/admin/shifts")
def shifts(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(s) for s in db.query(Shift).order_by(Shift.shift_date.desc()).all()]


@app.post("/api/admin/shifts")
def shifts_create(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    shift = Shift(worker_id=int(payload["worker_id"]), shift_date=dt.date.fromisoformat(payload["shift_date"]), shift_type=payload.get("shift_type", "regular"), status=payload.get("status", "worked"), start_time=payload.get("start_time", ""), end_time=payload.get("end_time", ""), worked_minutes=int(payload.get("worked_minutes", 480)))
    db.add(shift)
    db.commit()
    return item(shift)


@app.post("/api/admin/shifts/bulk")
def shifts_bulk(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    created = []
    for worker_id in payload.get("worker_ids", []):
        created.append(shifts_create({**payload, "worker_id": worker_id}, db, admin))
    return {"created": created}


@app.get("/api/admin/shifts/{shift_id}")
def shifts_get(shift_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    return item(db.get(Shift, shift_id))


@app.put("/api/admin/shifts/{shift_id}")
def shifts_update(shift_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = db.get(Shift, shift_id)
    for attr in ["status", "start_time", "end_time", "worked_minutes"]:
        if attr in payload:
            setattr(row, attr, payload[attr])
    db.commit()
    return item(row)


@app.patch("/api/admin/shifts/{shift_id}/void")
def shifts_void(shift_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = db.get(Shift, shift_id)
    row.status = "void"
    row.void_reason = payload.get("reason", "anulacion administrativa")
    db.commit()
    return item(row)


@app.get("/api/admin/tips/daily")
def tips_daily(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(t) for t in db.query(DailyTipFund).order_by(DailyTipFund.tip_date.desc()).all()]


@app.post("/api/admin/tips/daily")
def tips_create(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    amount = int(payload["amount_clp"])
    if amount < 0:
        raise HTTPException(status_code=422, detail="monto negativo")
    tip = DailyTipFund(tip_date=dt.date.fromisoformat(payload["tip_date"]), amount_clp=amount, notes=payload.get("notes", ""))
    db.add(tip)
    db.commit()
    return item(tip)


@app.get("/api/admin/tips/daily/{tip_date}")
def tips_get(tip_date: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    return item(db.query(DailyTipFund).filter_by(tip_date=dt.date.fromisoformat(tip_date)).first())


@app.put("/api/admin/tips/daily/{tip_date}")
def tips_update(tip_date: str, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    tip = db.query(DailyTipFund).filter_by(tip_date=dt.date.fromisoformat(tip_date)).first()
    tip.amount_clp = int(payload.get("amount_clp", tip.amount_clp))
    tip.notes = payload.get("notes", tip.notes)
    tip.status = "registered"
    db.commit()
    return item(tip)


@app.post("/api/admin/tips/daily/{tip_date}/calculate")
@app.post("/api/admin/tips/daily/{tip_date}/recalculate")
def tips_calculate(tip_date: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    return calculate_daily(db, dt.date.fromisoformat(tip_date))


@app.get("/api/admin/periods")
def periods(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(p) for p in db.query(Period).all()]


@app.post("/api/admin/periods")
def periods_create(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    return item(ensure_period(db, int(payload["year"]), int(payload["month"])))


@app.get("/api/admin/periods/{period_id}/preview")
def periods_preview(period_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    period = db.get(Period, period_id)
    rows = []
    for worker in db.query(Worker).all():
        bal = worker_balance(db, worker.id, period)
        rows.append({"worker": item(worker), **bal})
    return {"period": item(period), "workers": rows, "total_net_clp": sum(row["net"] for row in rows)}


@app.post("/api/admin/periods/{period_id}/close")
def periods_close(period_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    period = db.get(Period, period_id)
    period.status = "closed"
    db.commit()
    return periods_preview(period_id, db, admin)


@app.post("/api/admin/periods/{period_id}/reopen")
def periods_reopen(period_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    period = db.get(Period, period_id)
    if not payload.get("reason"):
        raise HTTPException(status_code=422, detail="motivo requerido")
    period.status = "open"
    db.commit()
    return item(period)


@app.get("/api/admin/payments")
def payments(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(p) for p in db.query(Payment).all()]


@app.post("/api/admin/payments/prepare")
def payments_prepare(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    period = db.get(Period, int(payload.get("period_id") or ensure_period(db).id))
    prepared = []
    for worker in db.query(Worker).all():
        bal = worker_balance(db, worker.id, period)
        payment = db.query(Payment).filter_by(worker_id=worker.id, period_id=period.id).first()
        if not payment:
            payment = Payment(worker_id=worker.id, period_id=period.id)
            db.add(payment)
        payment.gross_amount_clp = bal["gross"]
        payment.advance_discount_clp = bal["advances"]
        payment.net_amount_clp = bal["net"]
        payment.status = "prepared"
        prepared.append(payment)
    db.commit()
    return {"prepared": [item(p) for p in prepared]}


@app.patch("/api/admin/payments/{payment_id}/mark-paid")
def payments_paid(payment_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    payment = db.get(Payment, payment_id)
    payment.paid_amount_clp = int(payload.get("paid_amount_clp", payment.net_amount_clp))
    payment.paid_at = now()
    payment.status = "paid"
    db.commit()
    return item(payment)


@app.patch("/api/admin/payments/{payment_id}/void")
def payments_void(payment_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    payment = db.get(Payment, payment_id)
    payment.status = "void"
    db.commit()
    return item(payment)


@app.get("/api/admin/advances")
def admin_advances(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(a) for a in db.query(AdvanceRequest).all()]


@app.get("/api/admin/advances/{advance_id}")
def admin_advance_get(advance_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    return item(db.get(AdvanceRequest, advance_id))


@app.patch("/api/admin/advances/{advance_id}/approve")
@app.patch("/api/admin/advances/{advance_id}/reject")
def admin_advance_decide(advance_id: int, request: Request, payload: dict[str, Any] | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = db.get(AdvanceRequest, advance_id)
    if row.status != "pending":
        raise HTTPException(status_code=422, detail="solicitud no pendiente")
    reason = (payload or {}).get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="razon requerida")
    row.status = "approved" if request.url.path.endswith("approve") else "rejected"
    row.decision_reason = reason
    payment = None
    if row.status == "approved":
        payment = prepare_worker_payment(db, row.worker_id, row.period_id)
        db.flush()
        audit(db, admin.id, "advances", "approve", "advance_requests", row.id, {"reason": reason, "payment_id": payment.id})
    else:
        audit(db, admin.id, "advances", "reject", "advance_requests", row.id, {"reason": reason})
    db.commit()
    return {"advance": item(row), "payment": item(payment) if payment else None}


@app.get("/api/admin/shift-claims")
def admin_claims(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> list[dict[str, Any]]:
    return [item(c) for c in db.query(ShiftClaim).all()]


@app.patch("/api/admin/shift-claims/{claim_id}/resolve")
def admin_claim_resolve(claim_id: int, payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, Any]:
    row = db.get(ShiftClaim, claim_id)
    reason = payload.get("reason", payload.get("resolution", "")).strip()
    if not reason:
        raise HTTPException(status_code=422, detail="razon requerida")
    row.status = payload.get("status", "accepted")
    row.resolution = reason
    audit(db, admin.id, "shift_claims", row.status, "shift_claims", row.id, {"reason": reason})
    db.commit()
    return item(row)


@app.get("/api/admin/settings")
def settings_get(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, str]:
    return {row.key: row.value for row in db.query(SystemSetting).all()}


@app.put("/api/admin/settings")
def settings_put(payload: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> dict[str, str]:
    for key, value in payload.items():
        row = db.query(SystemSetting).filter_by(key=key).first()
        if row:
            row.value = str(value)
        else:
            db.add(SystemSetting(key=key, value=str(value)))
    db.commit()
    return settings_get(db, admin)


@app.get("/api/worker/dashboard")
def worker_dashboard(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    period = ensure_period(db)
    bal = worker_balance(db, user.worker.id, period)
    return {
        "period": item(period),
        "worker": item(user.worker),
        "current_tip_clp": bal["net"],
        "gross_tip_clp": bal["net"],
        "headline": f"Propina acumulada del periodo actual: {clp(bal['net'])}",
        "recent_shifts": [item(s) for s in db.query(Shift).filter_by(worker_id=user.worker.id).order_by(Shift.shift_date.desc()).limit(5).all()],
        "recent_advances": [item(a) for a in db.query(AdvanceRequest).filter_by(worker_id=user.worker.id).order_by(AdvanceRequest.requested_at.desc()).limit(5).all()],
        "recent_claims": [item(c) for c in db.query(ShiftClaim).filter_by(worker_id=user.worker.id).limit(5).all()],
    }


@app.get("/api/worker/current-period")
def worker_period(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    return item(ensure_period(db))


@app.get("/api/worker/shifts")
def worker_shifts(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> list[dict[str, Any]]:
    return [item(s) for s in db.query(Shift).filter_by(worker_id=user.worker.id).all()]


@app.get("/api/worker/shifts/{shift_id}")
def worker_shift_get(shift_id: int, db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    row = db.get(Shift, shift_id)
    if not row or row.worker_id != user.worker.id:
        raise HTTPException(status_code=403, detail="fuera de alcance")
    return item(row)


@app.get("/api/worker/payments")
def worker_payments(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> list[dict[str, Any]]:
    return [item(p) for p in db.query(Payment).filter_by(worker_id=user.worker.id).all()]


@app.get("/api/worker/payments/pending")
def worker_payments_pending(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> list[dict[str, Any]]:
    return [item(p) for p in db.query(Payment).filter_by(worker_id=user.worker.id).filter(Payment.status != "paid").all()]


@app.get("/api/worker/advances")
def worker_advances(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> list[dict[str, Any]]:
    return [item(a) for a in db.query(AdvanceRequest).filter_by(worker_id=user.worker.id).all()]


@app.post("/api/worker/advances")
def worker_advance_create(payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    amount = int(payload["amount_clp"])
    if amount <= 0 or amount % 10:
        raise HTTPException(status_code=422, detail="anticipo debe ser positivo y multiplo de 10")
    period = ensure_period(db)
    if amount > worker_balance(db, user.worker.id, period)["net"]:
        raise HTTPException(status_code=422, detail="anticipo supera saldo estimado")
    row = AdvanceRequest(worker_id=user.worker.id, period_id=period.id, amount_clp=amount, reason=payload.get("reason", "solicitud trabajador"))
    db.add(row)
    db.commit()
    return item(row)


@app.patch("/api/worker/advances/{advance_id}/cancel")
def worker_advance_cancel(advance_id: int, db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    row = db.get(AdvanceRequest, advance_id)
    if not row or row.worker_id != user.worker.id or row.status != "pending":
        raise HTTPException(status_code=422, detail="no cancelable")
    row.status = "cancelled"
    db.commit()
    return item(row)


@app.get("/api/worker/shift-claims")
def worker_claims(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> list[dict[str, Any]]:
    return [item(c) for c in db.query(ShiftClaim).filter_by(worker_id=user.worker.id).all()]


@app.post("/api/worker/shift-claims")
def worker_claim_create(payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    if len(payload.get("description", "")) < 10:
        raise HTTPException(status_code=422, detail="descripcion muy corta")
    row = ShiftClaim(worker_id=user.worker.id, claimed_date=dt.date.fromisoformat(payload["claimed_date"]), description=payload["description"])
    db.add(row)
    db.commit()
    return item(row)


@app.get("/api/worker/profile")
def worker_profile(db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    return {"user": item(user), "worker": item(user.worker)}


@app.put("/api/worker/profile")
def worker_profile_update(payload: dict[str, Any], db: Session = Depends(get_db), user: User = Depends(require_worker)) -> dict[str, Any]:
    for attr in ["phone", "first_name", "last_name"]:
        if attr in payload:
            setattr(user, attr, payload[attr])
    db.commit()
    return worker_profile(db, user)
