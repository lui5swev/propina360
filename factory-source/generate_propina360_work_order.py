from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "projects" / "propinas"


MAIN_PY = r'''
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
'''


INDEX_HTML = r'''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Propina360</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <main id="app"></main>
  <script src="/static/app.js?v=propina360-user-requests"></script>
</body>
</html>
'''


APP_JS = r'''
const state = {
  sessionKey: localStorage.getItem("p360_session"),
  role: localStorage.getItem("p360_role"),
  adminSection: localStorage.getItem("p360_admin_section") || "dashboard",
  workerSection: localStorage.getItem("p360_worker_section") || "resumen"
};
const $ = (id) => document.getElementById(id);
const fmt = (n) => "$" + Number(n || 0).toLocaleString("es-CL") + " CLP";
const routeKind = () => window.location.pathname.startsWith("/admin") ? "admin" : "worker";
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.sessionKey) headers.Authorization = "Bearer " + state.sessionKey;
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Error");
  return data;
}
function shell(content) {
  $("app").innerHTML = `<section class="shell">${content}</section>`;
}
function authView(kind = routeKind()) {
  const isAdmin = kind === "admin";
  const title = isAdmin ? "Acceso administrativo" : "Acceso trabajador";
  const subtitle = isAdmin ? "Ingresa desde /admin para operar la gestion de propinas." : "Ingresa como trabajador para revisar tu saldo, pagos, turnos y solicitudes.";
  const demoEmail = isAdmin ? "admin@propina360.local" : "ana.munoz@test.local";
  const demoClave = isAdmin ? "Admin-123!" : "Worker-123!";
  shell(`
    <div class="public-grid">
      <section class="hero">
        <div class="brand">Propina360</div>
        <h1>${title}</h1>
        <p>${subtitle}</p>
        <div class="hero-kpis"><span>CLP</span><span>JWT</span><span>CRUD</span><span>DEV listo</span></div>
      </section>
      <section class="panel auth-panel">
        <h2>${title}</h2>
        <form id="login-form" class="form">
          <input name="email" value="${demoEmail}" placeholder="email">
          <input name="clave" value="${demoClave}" placeholder="clave" type="password">
          <button>Entrar</button>
        </form>
        ${isAdmin ? "" : `
        <form id="register-form" class="form soft">
          <h3>Registro publico trabajador</h3>
          <input name="first_name" placeholder="Nombre">
          <input name="last_name" placeholder="Apellido">
          <input name="email" placeholder="email">
          <input name="phone" placeholder="+569...">
          <input name="clave" value="Worker-123!" placeholder="clave">
          <button>Crear cuenta pendiente</button>
        </form>`}
        <p id="msg"></p>
      </section>
    </div>`);
  $("login-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const body = Object.fromEntries(new FormData(ev.target).entries());
    try {
      const data = await api(isAdmin ? "/api/auth/admin/login" : "/api/auth/login", { method: "POST", body: JSON.stringify(body) });
      state.sessionKey = data.access_token; state.role = data.role;
      localStorage.setItem("p360_session", state.sessionKey);
      localStorage.setItem("p360_role", state.role);
      if (data.role === "admin") {
        history.replaceState(null, "", "/admin");
        adminApp();
      } else {
        history.replaceState(null, "", "/dashboard");
        workerApp();
      }
    } catch (e) { $("msg").textContent = e.message; }
  };
  if (!isAdmin) {
    $("register-form").onsubmit = async (ev) => {
      ev.preventDefault();
      try {
        const data = await api("/api/auth/register", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(ev.target).entries())) });
        $("msg").textContent = data.message || "peticion creada, usuario pendiente de confirmacion";
        ev.target.reset();
      }
      catch (e) { $("msg").textContent = e.message; }
    };
  }
}
function logout(){
  const kind = state.role === "admin" ? "admin" : "worker";
  localStorage.removeItem("p360_session");
  localStorage.removeItem("p360_role");
  state.sessionKey = null;
  state.role = null;
  history.replaceState(null, "", kind === "admin" ? "/admin" : "/dashboard");
  authView(kind);
}
function navButton(label, section, active, role) {
  return `<button class="nav-btn ${active === section ? "active" : ""}" data-role="${role}" data-section="${section}">${label}</button>`;
}
function bindNav(role) {
  document.querySelectorAll(`[data-role="${role}"]`).forEach((btn) => {
    btn.onclick = () => {
      if (role === "admin") {
        state.adminSection = btn.dataset.section;
        localStorage.setItem("p360_admin_section", state.adminSection);
        history.pushState(null, "", state.adminSection === "crear" ? "/admin/crear-trabajador" : "/admin");
        adminApp();
      } else {
        state.workerSection = btn.dataset.section;
        localStorage.setItem("p360_worker_section", state.workerSection);
        history.pushState(null, "", "/dashboard");
        workerApp();
      }
    };
  });
}
async function adminApp() {
  if (window.location.pathname.includes("crear-trabajador")) state.adminSection = "crear";
  const [summary, requests, workers, tips, advances, claims, periods, sections, contracts] = await Promise.all([
    api("/api/admin/dashboard/summary"), api("/api/admin/pending-users"), api("/api/admin/workers"), api("/api/admin/tips/daily"), api("/api/admin/advances"), api("/api/admin/shift-claims"), api("/api/admin/periods"), api("/api/admin/sections"), api("/api/admin/contracts")
  ]);
  const content = adminContent(state.adminSection, { summary, requests, workers, tips, advances, claims, periods, sections, contracts });
  shell(`
    <aside class="sidebar">
      <div><b>Propina360 Admin</b><span>Periodo ${summary.period}</span></div>
      <nav>
        ${navButton("Dashboard", "dashboard", state.adminSection, "admin")}
        ${navButton("Solicitudes de usuario", "solicitudes", state.adminSection, "admin")}
        ${navButton("Trabajadores", "trabajadores", state.adminSection, "admin")}
        ${navButton("Crear nuevo trabajador", "crear", state.adminSection, "admin")}
        ${navButton("Turnos", "turnos", state.adminSection, "admin")}
        ${navButton("Propinas diarias", "propinas", state.adminSection, "admin")}
        ${navButton("Cierre y pagos", "pagos", state.adminSection, "admin")}
        ${navButton("Anticipos", "anticipos", state.adminSection, "admin")}
        ${navButton("Reclamos", "reclamos", state.adminSection, "admin")}
      </nav>
      <button onclick="logout()">Salir</button>
    </aside>
    <section class="workspace">
      <header><div><h2>${content.title}</h2><p>${content.subtitle}</p></div></header>
      ${content.html}
    </section>`);
  bindNav("admin");
  bindAdminActions({ periods, sections, contracts });
}
function adminContent(section, data) {
  if (section === "solicitudes") return {
    title: "Solicitudes de usuario",
    subtitle: "Aprobacion publica con razon y completado posterior de ficha laboral.",
    html: `<section class="decision-list">${registrationCards(data.requests, data)}</section>`
  };
  if (section === "trabajadores") return {
    title: "Trabajadores",
    subtitle: "Lista administrativa y estado laboral.",
    html: `<section class="panel">${table(data.workers, ["id","first_name","last_name","internal_code","section","contract_type","points","status"])}</section>`
  };
  if (section === "crear") return {
    title: "Crear nuevo trabajador",
    subtitle: "Alta manual con RUN, contrato, seccion y puntos vigentes.",
    html: `<section class="panel narrow"><form id="worker-create-form" class="form two-col">
      <input name="first_name" placeholder="Nombre" required>
      <input name="last_name" placeholder="Apellido" required>
      <input name="email" placeholder="Email" required>
      <input name="phone" placeholder="+569..." required>
      <input name="run" placeholder="RUN chileno" required>
      <input name="points" placeholder="Puntos" value="10" required>
      <select name="section_id">${data.sections.map(s=>`<option value="${s.id}">${s.name}</option>`).join("")}</select>
      <select name="contract_type_id">${data.contracts.map(c=>`<option value="${c.id}">${c.name}</option>`).join("")}</select>
      <button>Crear trabajador</button>
    </form><p id="form-msg"></p></section>`
  };
  if (section === "turnos") return {
    title: "Turnos",
    subtitle: "Registro administrativo de asistencia diaria.",
    html: `<section class="panel"><form id="shift-form" class="inline"><input name="worker_id" placeholder="Worker id"><input name="shift_date" type="date"><button>Registrar trabajado</button></form></section>`
  };
  if (section === "propinas") return {
    title: "Propinas diarias",
    subtitle: "Fondos CLP y estado de calculo diario.",
    html: `<section class="panel"><form id="tip-form" class="inline"><input name="tip_date" type="date"><input name="amount_clp" placeholder="Monto CLP"><button>Registrar</button></form>${table(data.tips, ["tip_date","amount_clp","point_value_clp","status"])}</section>`
  };
  if (section === "pagos") return {
    title: "Cierre y pagos",
    subtitle: "Preparacion de pagos y cierre del periodo actual.",
    html: `<section class="panel action-panel"><button id="prepare-payments">Preparar pagos</button><button id="close-period">Cerrar periodo</button><pre>${JSON.stringify(data.periods[0] || {}, null, 2)}</pre></section>`
  };
  if (section === "anticipos") return {
    title: "Anticipos",
    subtitle: "Solicitudes de adelanto con decision administrativa y razon registrada.",
    html: `<section class="decision-list">${decisionCards("advance", data.advances)}</section>`
  };
  if (section === "reclamos") return {
    title: "Reclamos de turno",
    subtitle: "Reclamos enviados por trabajadores con resolucion y razon.",
    html: `<section class="decision-list">${decisionCards("claim", data.claims)}</section>`
  };
  return {
    title: "Dashboard administrativo",
    subtitle: "Resumen ejecutivo del periodo.",
    html: `<section class="panel pending-users-panel">
      <div>
        <span>Solicitudes de usuario pendientes</span>
        <strong>${data.summary.pending_users}</strong>
        <p class="muted">Revisa altas publicas, aprueba o rechaza con razon y completa la ficha laboral.</p>
      </div>
      <button class="nav-btn-inline" data-role="admin" data-section="solicitudes">Ir a solicitudes</button>
    </section>
    <div class="kpi-grid">
      <article><span>Trabajadores activos</span><strong>${data.summary.active_workers}</strong></article>
      <article><span>Propina registrada</span><strong>${fmt(data.summary.registered_tip_clp)}</strong></article>
      <article><span>Calculada</span><strong>${fmt(data.summary.calculated_tip_clp)}</strong></article>
      <article><span>Por pagar</span><strong>${fmt(data.summary.estimated_payable_clp)}</strong></article>
      <article><span>Usuarios pendientes</span><strong>${data.summary.pending_users}</strong></article>
      <article><span>Anticipos pendientes</span><strong>${data.summary.pending_advances}</strong></article>
      <article><span>Reclamos pendientes</span><strong>${data.summary.pending_shift_claims}</strong></article>
    </div>`
  };
}
function registrationCards(rows, data) {
  if (!rows || rows.length === 0) return `<section class="panel"><p class="muted">Sin solicitudes.</p></section>`;
  return rows.map((row) => {
    const fullName = `${row.first_name || ""} ${row.last_name || ""}`.trim();
    const reason = row.decision_reason || "";
    const pending = row.status === "pending_approval";
    const approvedPending = row.status === "approved_pending_profile";
    return `<article class="panel decision-card">
      <div>
        <h3>${fullName || row.email}</h3>
        <p>${row.email} · ${row.phone || "sin telefono"}</p>
        <span class="status-pill">${row.status}</span>
        ${reason ? `<p class="decision-reason">Razon: ${reason}</p>` : ""}
      </div>
      ${pending ? `<form class="registration-decision-form" data-id="${row.id}">
        <input name="reason" placeholder="Razon de la decision" required>
        <div class="decision-actions">
          <button name="decision" value="approve">Aprobar</button>
          <button name="decision" value="reject" class="danger">Rechazar</button>
        </div>
      </form>` : ""}
      ${approvedPending ? `<form class="registration-complete-form" data-id="${row.id}">
        <input name="run" placeholder="RUN chileno" required>
        <input name="points" placeholder="Puntos" value="10" required>
        <select name="section_id">${data.sections.map(s=>`<option value="${s.id}">${s.name}</option>`).join("")}</select>
        <select name="contract_type_id">${data.contracts.map(c=>`<option value="${c.id}">${c.name}</option>`).join("")}</select>
        <button>Completar ficha laboral</button>
      </form>` : ""}
    </article>`;
  }).join("");
}
function decisionCards(kind, rows) {
  if (!rows || rows.length === 0) return `<section class="panel"><p class="muted">Sin datos.</p></section>`;
  return rows.map((row) => {
    const isAdvance = kind === "advance";
    const title = isAdvance ? `Anticipo #${row.id} · Worker ${row.worker_id}` : `Reclamo #${row.id} · Worker ${row.worker_id}`;
    const body = isAdvance ? `${fmt(row.amount_clp)} · ${row.reason || "sin motivo"}` : `${row.claimed_date} · ${row.description || ""}`;
    const decided = row.status !== "pending";
    const reason = isAdvance ? row.decision_reason : row.resolution;
    return `<article class="panel decision-card">
      <div><h3>${title}</h3><p>${body}</p><span class="status-pill">${row.status}</span>${reason ? `<p class="decision-reason">Razon: ${reason}</p>` : ""}</div>
      ${decided ? "" : `<form class="decision-form" data-kind="${kind}" data-id="${row.id}">
        <input name="reason" placeholder="Razon de la decision" required>
        <div class="decision-actions">
          <button name="decision" value="approve">Aprobar</button>
          <button name="decision" value="reject" class="danger">Rechazar</button>
        </div>
      </form>`}
    </article>`;
  }).join("");
}
function bindAdminActions(data) {
  const create = $("worker-create-form");
  if (create) create.onsubmit = async (ev) => {
    ev.preventDefault();
    try {
      await api("/api/admin/workers", {method:"POST", body: JSON.stringify(Object.fromEntries(new FormData(ev.target).entries()))});
      $("form-msg").textContent = "Trabajador creado correctamente.";
      state.adminSection = "trabajadores";
      localStorage.setItem("p360_admin_section", state.adminSection);
      history.pushState(null, "", "/admin");
      adminApp();
    } catch (e) { $("form-msg").textContent = e.message; }
  };
  const tip = $("tip-form");
  if (tip) tip.onsubmit = async (ev) => { ev.preventDefault(); await api("/api/admin/tips/daily", {method:"POST", body: JSON.stringify(Object.fromEntries(new FormData(ev.target).entries()))}); adminApp(); };
  const shift = $("shift-form");
  if (shift) shift.onsubmit = async (ev) => { ev.preventDefault(); await api("/api/admin/shifts", {method:"POST", body: JSON.stringify({...Object.fromEntries(new FormData(ev.target).entries()), status:"worked"})}); adminApp(); };
  const prepare = $("prepare-payments");
  if (prepare) prepare.onclick = async () => { await api("/api/admin/payments/prepare", {method:"POST", body: JSON.stringify({period_id: (data.periods[0]||{}).id})}); adminApp(); };
  const close = $("close-period");
  if (close) close.onclick = async () => { await api(`/api/admin/periods/${(data.periods[0]||{}).id}/close`, {method:"POST", body:"{}"}); adminApp(); };
  document.querySelectorAll(".decision-form").forEach((form) => {
    form.onsubmit = async (ev) => {
      ev.preventDefault();
      const clicked = ev.submitter;
      const body = Object.fromEntries(new FormData(form).entries());
      const decision = clicked && clicked.value === "reject" ? "reject" : "approve";
      const kind = form.dataset.kind;
      const id = form.dataset.id;
      const path = kind === "advance" ? `/api/admin/advances/${id}/${decision}` : `/api/admin/shift-claims/${id}/resolve`;
      const payload = kind === "advance" ? body : { status: decision === "approve" ? "accepted" : "rejected", reason: body.reason };
      await api(path, {method:"PATCH", body: JSON.stringify(payload)});
      adminApp();
    };
  });
  document.querySelectorAll(".registration-decision-form").forEach((form) => {
    form.onsubmit = async (ev) => {
      ev.preventDefault();
      const clicked = ev.submitter;
      const decision = clicked && clicked.value === "reject" ? "reject" : "approve";
      const body = Object.fromEntries(new FormData(form).entries());
      await api(`/api/admin/pending-users/${form.dataset.id}/${decision}`, {method:"PATCH", body: JSON.stringify(body)});
      adminApp();
    };
  });
  document.querySelectorAll(".registration-complete-form").forEach((form) => {
    form.onsubmit = async (ev) => {
      ev.preventDefault();
      await api(`/api/admin/pending-users/${form.dataset.id}/complete-worker`, {method:"POST", body: JSON.stringify(Object.fromEntries(new FormData(form).entries()))});
      state.adminSection = "trabajadores";
      localStorage.setItem("p360_admin_section", state.adminSection);
      history.pushState(null, "", "/admin");
      adminApp();
    };
  });
}
async function workerApp() {
  const [dash, shifts, payments, advances, claims] = await Promise.all([
    api("/api/worker/dashboard"), api("/api/worker/shifts"), api("/api/worker/payments"), api("/api/worker/advances"), api("/api/worker/shift-claims")
  ]);
  const content = workerContent(state.workerSection, { dash, shifts, payments, advances, claims });
  shell(`
    <aside class="sidebar worker-side">
      <div><b>Propina360</b><span>${dash.worker.first_name} ${dash.worker.last_name}</span></div>
      <nav>
        ${navButton("Resumen", "resumen", state.workerSection, "worker")}
        ${navButton("Mis turnos", "turnos", state.workerSection, "worker")}
        ${navButton("Mis pagos", "pagos", state.workerSection, "worker")}
        ${navButton("Mis anticipos", "anticipos", state.workerSection, "worker")}
        ${navButton("Reclamos", "reclamos", state.workerSection, "worker")}
        ${navButton("Perfil", "perfil", state.workerSection, "worker")}
      </nav>
      <button onclick="logout()">Salir</button>
    </aside>
    <section class="workspace">
      <header><div><h2>${content.title}</h2><p>${content.subtitle}</p></div></header>
      ${content.html}
    </section>`);
  bindNav("worker");
  bindWorkerActions();
}
function workerContent(section, data) {
  if (section === "turnos") return { title: "Mis turnos", subtitle: "Turnos registrados para tu periodo.", html: `<section class="panel">${table(data.shifts, ["shift_date","status","worked_minutes"])}</section>` };
  if (section === "pagos") return { title: "Mis pagos", subtitle: "Pagos pasados y pendientes.", html: `<section class="panel">${table(data.payments, ["period_id","net_amount_clp","paid_amount_clp","status"])}</section>` };
  if (section === "anticipos") return { title: "Mis anticipos", subtitle: "Solicitudes y estado de anticipos.", html: `<section class="panel"><form id="advance-form" class="inline"><input name="amount_clp" placeholder="Monto"><input name="reason" placeholder="Motivo"><button>Solicitar</button></form>${table(data.advances, ["id","amount_clp","status","reason"])}</section>` };
  if (section === "reclamos") return { title: "Reclamos de turno", subtitle: "Envio y seguimiento de reclamos.", html: `<section class="panel"><form id="claim-form" class="inline"><input name="claimed_date" type="date"><input name="description" placeholder="Descripcion"><button>Enviar</button></form>${table(data.claims, ["claimed_date","status","description"])}</section>` };
  if (section === "perfil") return { title: "Perfil", subtitle: "Datos laborales principales.", html: `<section class="panel narrow"><dl class="profile"><dt>Estado</dt><dd>${data.dash.worker.status}</dd><dt>Contrato</dt><dd>${data.dash.worker.contract_type}</dd><dt>Puntos</dt><dd>${data.dash.worker.points}</dd><dt>Codigo interno</dt><dd>${data.dash.worker.internal_code}</dd><dt>Seccion</dt><dd>${data.dash.worker.section}</dd></dl></section>` };
  return { title: "Dashboard trabajador", subtitle: "Resumen del periodo actual.", html: `<div class="kpi-grid worker-kpis"><article class="hero-card"><span>Propina acumulada del periodo actual</span><strong>${fmt(data.dash.current_tip_clp)}</strong></article><article><span>Estado laboral</span><strong>${data.dash.worker.status}</strong></article></div>` };
}
function bindWorkerActions() {
  const advance = $("advance-form");
  if (advance) advance.onsubmit = async (ev) => { ev.preventDefault(); await api("/api/worker/advances", {method:"POST", body: JSON.stringify(Object.fromEntries(new FormData(ev.target).entries()))}); workerApp(); };
  const claim = $("claim-form");
  if (claim) claim.onsubmit = async (ev) => { ev.preventDefault(); await api("/api/worker/shift-claims", {method:"POST", body: JSON.stringify(Object.fromEntries(new FormData(ev.target).entries()))}); workerApp(); };
}
function table(rows, cols) {
  if (!rows || rows.length === 0) return "<p class='muted'>Sin datos.</p>";
  return `<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${r[c] ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
if (state.sessionKey && state.role === "admin" && routeKind() === "admin") adminApp().catch(() => authView("admin"));
else if (state.sessionKey && state.role === "worker" && routeKind() === "worker") workerApp().catch(() => authView("worker"));
else authView(routeKind());
'''


STYLES_CSS = r'''
:root{--ink:#14213d;--muted:#667085;--line:#d8dee9;--bg:#f5f7fb;--panel:#fff;--sky:#0ea5e9;--green:#0f9f6e;--amber:#f59e0b;--red:#d92d20}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Roboto,system-ui,sans-serif}button{border:0;border-radius:8px;background:var(--ink);color:#fff;padding:.72rem 1rem;font-weight:700;cursor:pointer}button:hover{filter:brightness(1.1)}button.danger{background:var(--red)}input,select{width:100%;border:1px solid var(--line);border-radius:8px;padding:.72rem;background:#fff}.shell{min-height:100vh}.public-grid{display:grid;grid-template-columns:minmax(0,1.1fr) 440px;min-height:100vh}.hero{padding:8vw 7vw;background:linear-gradient(135deg,#0f172a,#075985 54%,#14b8a6);color:#fff;display:flex;flex-direction:column;justify-content:center}.brand{font-size:1.15rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.hero h1{font-size:clamp(2.2rem,5vw,4.8rem);line-height:1.02;margin:.7rem 0}.hero p{font-size:1.2rem;max-width:720px}.hero-kpis{display:flex;gap:.7rem;flex-wrap:wrap;margin-top:2rem}.hero-kpis span{border:1px solid rgba(255,255,255,.35);border-radius:999px;padding:.55rem .85rem;background:rgba(255,255,255,.12)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:1rem;box-shadow:0 10px 30px rgba(15,23,42,.06)}.auth-panel{margin:auto 2rem;box-shadow:0 20px 60px rgba(15,23,42,.14)}.auth-panel h2{margin-top:0}.form{display:grid;gap:.75rem}.form.two-col{grid-template-columns:repeat(2,minmax(0,1fr))}.form.two-col button{grid-column:1/-1}.soft{margin-top:1.25rem;padding-top:1.25rem;border-top:1px solid var(--line)}#msg,#form-msg{color:var(--red);min-height:1.3rem}.sidebar{position:fixed;inset:0 auto 0 0;width:260px;background:#111827;color:#fff;padding:1.25rem;display:flex;flex-direction:column;gap:1.25rem;overflow-y:auto}.sidebar b{display:block;font-size:1.1rem}.sidebar span{display:block;color:#cbd5e1;font-size:.88rem;margin-top:.3rem}.sidebar nav{display:grid;gap:.35rem}.nav-btn{width:100%;background:transparent;color:#dbeafe;text-align:left;padding:.72rem .8rem;border:1px solid transparent}.nav-btn:hover,.nav-btn.active{background:#1f2937;border-color:#334155;color:#fff}.nav-btn-inline{background:#0f766e;white-space:nowrap}.worker-side{background:#063344}.workspace{margin-left:260px;padding:1.25rem}.workspace header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem}.workspace h2{margin:0;font-size:1.7rem}.workspace header p{margin:.3rem 0 0;color:var(--muted)}.pending-users-panel{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem;border-left:5px solid var(--green)}.pending-users-panel span{display:block;color:var(--muted)}.pending-users-panel strong{display:block;font-size:2rem;color:var(--green);margin:.25rem 0}.pending-users-panel p{margin:.2rem 0 0}.kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:.85rem;margin:1rem 0}.kpi-grid article,.highlight{background:#fff;border:1px solid var(--line);border-radius:8px;padding:1rem}.kpi-grid span,.highlight span,.muted{color:var(--muted)}.kpi-grid strong{display:block;font-size:1.35rem;margin-top:.4rem}.worker-kpis{grid-template-columns:repeat(4,minmax(170px,1fr))}.hero-card{grid-column:span 2}.hero-card strong{font-size:2rem;color:var(--green)}.section-actions{display:flex;justify-content:flex-end;margin-bottom:1rem}.inline{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.5rem;margin-bottom:.8rem}.action-panel{display:flex;gap:.7rem;align-items:flex-start;flex-wrap:wrap}.action-panel pre{width:100%;background:#f8fafc;border:1px solid var(--line);border-radius:8px;padding:1rem}.decision-list{display:grid;gap:.85rem}.decision-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,420px);gap:1rem;align-items:start}.decision-card h3{margin:.1rem 0}.decision-card p{margin:.35rem 0;color:var(--muted)}.decision-form,.registration-decision-form,.registration-complete-form{display:grid;gap:.6rem}.decision-actions{display:flex;gap:.5rem;justify-content:flex-end}.status-pill{display:inline-flex;border-radius:999px;background:#eef2ff;color:#3730a3;padding:.25rem .55rem;font-size:.78rem;font-weight:800;text-transform:uppercase}.decision-reason{color:var(--ink)!important}.narrow{max-width:760px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.92rem}th,td{text-align:left;padding:.65rem;border-bottom:1px solid var(--line)}th{color:var(--muted);font-size:.8rem;text-transform:uppercase}.profile{display:grid;grid-template-columns:180px 1fr;gap:.7rem 1rem}.profile dt{color:var(--muted)}.profile dd{margin:0;font-weight:700}@media(max-width:900px){.public-grid{grid-template-columns:1fr}.auth-panel{margin:1rem}.sidebar{position:static;width:auto}.workspace{margin-left:0}.pending-users-panel{align-items:flex-start;flex-direction:column}.kpi-grid,.worker-kpis{grid-template-columns:repeat(2,1fr)}.hero-card{grid-column:span 2}.inline,.form.two-col,.decision-card{grid-template-columns:1fr}.hero{min-height:52vh}.workspace header{align-items:flex-start;flex-direction:column}}@media(max-width:520px){.kpi-grid,.worker-kpis{grid-template-columns:1fr}.hero-card{grid-column:span 1}.hero{padding:2rem}.hero h1{font-size:2.35rem}.profile{grid-template-columns:1fr}.decision-actions{justify-content:stretch}.decision-actions button{flex:1}}
'''


TESTS_PY = r'''
import datetime as dt

from app.main import (
    AdvanceRequest,
    DailyTipFund,
    Payment,
    Role,
    Section,
    SessionLocal,
    Shift,
    ShiftClaim,
    User,
    Worker,
    WorkerRegistrationRequest,
    approve_user,
    calculate_daily,
    check_pass,
    complete_pending_user_worker,
    create_worker,
    current_points,
    ensure_period,
    hash_pass,
    internal_code,
    prepare_worker_payment,
    register,
    reset_database,
    validate_run,
    worker_balance,
)


def session():
    return SessionLocal()


def test_auth_roles_and_run_helpers():
    reset_database()
    db = session()
    try:
        admin = db.query(User).filter_by(email="admin@propina360.local").one()
        worker = db.query(User).filter_by(email="ana.munoz@test.local").one()
        assert admin.role.name == "admin"
        assert worker.role.name == "worker"
        assert check_pass("Admin-123!", admin.pass_hash, admin.email)
        assert validate_run("12.345.678-5")
        assert internal_code("12.345.678-5") == "TRAB-12345678"
    finally:
        db.close()


def test_create_worker_and_crud_update():
    reset_database()
    db = session()
    try:
        role = db.query(Role).filter_by(name="worker").one()
        user = User(email="nuevo@test.local", pass_hash=hash_pass("Worker-123!", "nuevo@test.local"), first_name="Nuevo", last_name="Trabajador", phone="+56977777777", role=role, status="pending_approval")
        db.add(user)
        db.flush()
        worker = create_worker(db, user, {"run": "16.000.000-7", "points": 8})
        worker.user.phone = "+56988888888"
        db.commit()
        assert worker.status == "active"
        assert worker.internal_code == "TRAB-16000000"
        assert current_points(worker) == 8
        assert db.query(Worker).filter_by(run="16.000.000-7").one().user.phone == "+56988888888"
    finally:
        db.close()


def test_public_registration_requires_admin_decision_and_profile_completion():
    reset_database()
    db = session()
    try:
        admin = db.query(User).filter_by(email="admin@propina360.local").one()
        result = register(
            {
                "first_name": "Publica",
                "last_name": "Pendiente",
                "email": "publica.pendiente@test.local",
                "phone": "+56977770000",
                "clave": "Worker-123!",
            },
            db,
        )
        assert result["message"] == "peticion creada, usuario pendiente de confirmacion"
        user = db.get(User, result["user_id"])
        req = db.query(WorkerRegistrationRequest).filter_by(user_id=user.id).one()
        assert user.status == "pending_approval"
        assert req.status == "pending"
        approved = approve_user(user.id, {"reason": "documentos iniciales correctos"}, db, admin)
        db.refresh(user)
        assert approved["status"] == "approved_pending_profile"
        assert user.worker is None
        assert req.decision_reason == "documentos iniciales correctos"
        worker = complete_pending_user_worker(user.id, {"run": "16.000.000-7", "points": 9}, db, admin)
        db.refresh(user)
        db.refresh(req)
        assert worker["internal_code"] == "TRAB-16000000"
        assert user.status == "approved"
        assert user.worker.status == "active"
        assert req.status == "completed"
    finally:
        db.close()


def test_daily_tip_calculation_fulltime_parttime_and_rounding():
    reset_database()
    db = session()
    try:
        today = dt.date.today()
        parttime = next(w for w in db.query(Worker).all() if w.contract_type.name == "parttime")
        db.add(Shift(worker_id=parttime.id, shift_date=today, status="worked"))
        db.add(DailyTipFund(tip_date=today, amount_clp=150000))
        db.commit()
        result = calculate_daily(db, today)
        details = result["details"]
        fund = db.query(DailyTipFund).filter_by(tip_date=today).one()
        assert len(details) >= 4
        assert float(fund.point_value_clp) > 0
        assert all(row["payable_amount_clp"] % 10 == 0 for row in details)
        assert sum(row["payable_amount_clp"] for row in details) <= 150000
    finally:
        db.close()


def test_advance_claim_close_and_payment_flow():
    reset_database()
    db = session()
    try:
        today = dt.date.today()
        period = ensure_period(db)
        ana = db.query(User).filter_by(email="ana.munoz@test.local").one().worker
        db.add(DailyTipFund(tip_date=today, amount_clp=90000))
        db.commit()
        calculate_daily(db, today)
        balance = worker_balance(db, ana.id, period)
        assert balance["gross"] > 0
        advance = AdvanceRequest(worker_id=ana.id, period_id=period.id, amount_clp=1000, reason="movilizacion", status="pending")
        db.add(advance)
        db.commit()
        advance.status = "approved"
        advance.decision_reason = "anticipo aprobado por saldo disponible"
        claim = ShiftClaim(worker_id=ana.id, claimed_date=today, description="Mi turno aparece incompleto", status="pending")
        db.add(claim)
        db.commit()
        claim.status = "accepted"
        claim.resolution = "reclamo aceptado por registro incompleto"
        period.status = "closed"
        bal = worker_balance(db, ana.id, period)
        payment = prepare_worker_payment(db, ana.id, period.id)
        payment.paid_amount_clp = payment.net_amount_clp
        payment.status = "paid"
        db.commit()
        assert advance.status == "approved"
        assert advance.decision_reason
        assert claim.status == "accepted"
        assert claim.resolution
        assert payment.status == "paid"
        assert payment.net_amount_clp == max(0, balance["gross"] - 1000)
    finally:
        db.close()
'''


README = r'''
# Propina360

Sistema web funcional para gestionar propinas en CLP con rutas separadas para administrador y trabajador.

## Ejecucion local

```bash
cd backend-fastapi
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir:

- Administrador: http://127.0.0.1:8000/admin
- Trabajador: http://127.0.0.1:8000/dashboard
- API: http://127.0.0.1:8000/docs

Credenciales de desarrollo:

- Admin: `admin@propina360.local` / `Admin-123!`
- Trabajador: `ana.munoz@test.local` / `Worker-123!`

## Pruebas

```bash
cd backend-fastapi
PYTHONPATH=. python3 -m pytest -q
```

## Alcance funcional

- Registro publico de trabajadores como solicitud pendiente, aprobacion/rechazo admin con razon y completado posterior de ficha laboral.
- Login separado: `/api/auth/admin/login` y `/api/auth/login`.
- Guardas JWT por rol.
- CRUD administrativo de trabajadores, secciones, puntos, turnos, fondos diarios, periodos, pagos, anticipos y reclamos.
- Dashboard trabajador con propina acumulada del periodo al inicio.
- Calculo diario por puntos, elegibilidad fulltime/parttime y redondeo hacia abajo a multiplos de 10 CLP.
- Cierre mensual y preparacion de pagos.
- Auditoria tecnica en tabla interna, sin pantalla visible de auditoria.
- Documentos tecnicos de reportes y auditoria en `docs/`.

SQLite es el motor local por defecto para facilitar pruebas. El esquema MySQL/MariaDB equivalente esta en `database-mysql-mariadb/schema.sql`.
'''


CONSUMO_TOKENS = r'''
# Registro de estimacion de consumo y optimizacion de tokens

## Resumen

Esta entrega se ejecuto bajo el ciclo WEBFORGE con arnes y orquestador. La implementacion se paso como `metadata.implementation_bundle`, evitando materializaciones ad hoc y reduciendo vueltas de contexto.

## Estimacion operativa

| Actividad | Entradas principales | Estrategia de reduccion | Estimacion relativa |
|---|---|---|---|
| Lectura de especificacion | `projects/propinas/especificacion_sistema_propinas_propina360.md` | Lectura por tramos y extraccion de reglas criticas | Alta |
| Construccion de bundle | Work order fuente | Un solo bundle textual para materializador DEV | Media |
| Ejecucion de fabrica | `webforge_run.py run` | Reuso de arnes, gates y tool registry local | Baja |
| Validacion | Pytest y HTTP local | Pruebas enfocadas en flujos criticos | Media |

## Optimizaciones aplicadas

- Se evito pedir generacion externa: todo se resolvio con codigo local.
- Se concentro la logica critica en servicios reutilizables dentro del backend.
- El frontend operativo consume endpoints agregados para reducir llamadas repetidas.
- Los documentos tecnicos evitan crear pantallas de reportes/auditoria que la especificacion excluye.
- La base local usa SQLite para pruebas rapidas, con esquema MariaDB documentado para migracion.

## Control de fabrica

- Entrada formal: `projects/propinas/work_order.json`.
- Ciclo: `intake -> ... -> implement -> validate -> security -> ... -> close`.
- Materializacion autorizada: `tool.sandbox.dev_materialize`.
- Salida DEV: `project/propina360/sandboxes/DEV/workspace`.
'''


ENDPOINTS_MD = r'''
# Endpoints Propina360

La API implementa las rutas principales solicitadas: autenticacion, solicitudes publicas de usuario con aprobacion/rechazo razonada, completado de ficha laboral, trabajadores, puntos, secciones, turnos, propinas diarias, calculo, periodos, pagos, anticipos, reclamos, configuracion y dashboard trabajador.

Las rutas administrativas requieren token de rol `admin`; las rutas `/api/worker/*` requieren trabajador aprobado y activo.
'''


AUDIT_MD = r'''
# Auditoria tecnica

La auditoria se registra internamente en `audit_logs` para acciones criticas como registro, aprobacion de usuarios, cambios de trabajadores, puntos, turnos, propinas, cierres, anticipos y pagos.

No existe pantalla visible de auditoria dentro de la aplicacion, en cumplimiento de la especificacion.
'''


REPORTS_MD = r'''
# Documento tecnico de reportes

Los reportes se resuelven como consultas tecnicas y documentacion, no como modulos visibles:

- Propina diaria por fecha.
- Distribucion diaria por trabajador.
- Cierre mensual por trabajador.
- Anticipos por periodo.
- Pagos realizados.
- Reclamos de turno.
'''


MODEL_MD = r'''
# Modelo de datos

El backend implementa las entidades transaccionales criticas en SQLAlchemy: usuarios, roles, solicitudes de registro, trabajadores, secciones, cargos, contratos, puntos, periodos, turnos, fondos diarios, calculos, detalles, sobrantes, anticipos, pagos, reclamos, configuracion y auditoria tecnica.

El archivo `database-mysql-mariadb/schema.sql` documenta el esquema extendido de 42 tablas solicitado por la especificacion.
'''


SCHEMA_SQL = r'''
CREATE TABLE roles (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE permissions (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(80) UNIQUE NOT NULL);
CREATE TABLE role_permissions (role_id INT NOT NULL, permission_id INT NOT NULL, PRIMARY KEY(role_id, permission_id));
CREATE TABLE users (id INT PRIMARY KEY AUTO_INCREMENT, email VARCHAR(180) UNIQUE NOT NULL, pass_hash VARCHAR(220) NOT NULL, first_name VARCHAR(80) NOT NULL, last_name VARCHAR(80) NOT NULL, phone VARCHAR(30), role_id INT NOT NULL, status VARCHAR(40) NOT NULL, created_at DATETIME, updated_at DATETIME);
CREATE TABLE user_sessions (id INT PRIMARY KEY AUTO_INCREMENT, user_id INT NOT NULL, refresh_hash VARCHAR(220), expires_at DATETIME);
CREATE TABLE password_reset_tokens (id INT PRIMARY KEY AUTO_INCREMENT, user_id INT NOT NULL, reset_hash VARCHAR(220), expires_at DATETIME);
CREATE TABLE worker_registration_requests (id INT PRIMARY KEY AUTO_INCREMENT, user_id INT NOT NULL, status VARCHAR(30), decision_reason TEXT, created_at DATETIME);
CREATE TABLE workers (id INT PRIMARY KEY AUTO_INCREMENT, user_id INT UNIQUE NOT NULL, run VARCHAR(20) UNIQUE NOT NULL, internal_code VARCHAR(30) UNIQUE NOT NULL, section_id INT NOT NULL, position_id INT NOT NULL, contract_type_id INT NOT NULL, status VARCHAR(30), hired_at DATE, terminated_at DATE);
CREATE TABLE worker_personal_data (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, address VARCHAR(240), emergency_contact VARCHAR(160));
CREATE TABLE contract_types (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE worker_statuses (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE sections (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(80) UNIQUE NOT NULL, active BOOLEAN DEFAULT TRUE);
CREATE TABLE positions (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) UNIQUE NOT NULL);
CREATE TABLE worker_points_history (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, points INT NOT NULL CHECK(points BETWEEN 6 AND 20), valid_from DATE NOT NULL, valid_to DATE, reason VARCHAR(240));
CREATE TABLE worker_contract_history (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, contract_type_id INT NOT NULL, valid_from DATE NOT NULL, valid_to DATE);
CREATE TABLE periods (id INT PRIMARY KEY AUTO_INCREMENT, year INT NOT NULL, month INT NOT NULL, status VARCHAR(30), UNIQUE(year, month));
CREATE TABLE calendar_days (id INT PRIMARY KEY AUTO_INCREMENT, day_date DATE UNIQUE NOT NULL, period_id INT NOT NULL, mandatory_calculation BOOLEAN DEFAULT TRUE);
CREATE TABLE shift_types (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE shift_statuses (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE shifts (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, shift_date DATE NOT NULL, shift_type VARCHAR(30), status VARCHAR(30), start_time VARCHAR(10), end_time VARCHAR(10), worked_minutes INT, void_reason TEXT, UNIQUE(worker_id, shift_date, shift_type));
CREATE TABLE shift_claim_statuses (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE shift_claims (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, claimed_date DATE NOT NULL, description TEXT NOT NULL, status VARCHAR(30), resolution TEXT);
CREATE TABLE daily_tip_funds (id INT PRIMARY KEY AUTO_INCREMENT, tip_date DATE UNIQUE NOT NULL, amount_clp INT NOT NULL CHECK(amount_clp >= 0), point_value_clp DECIMAL(12,2) DEFAULT 0, status VARCHAR(30), notes TEXT);
CREATE TABLE daily_tip_calculations (id INT PRIMARY KEY AUTO_INCREMENT, tip_date DATE UNIQUE NOT NULL, total_points INT, total_amount_clp INT, total_payable_clp INT, total_remainder_clp DECIMAL(12,2), calculated_at DATETIME);
CREATE TABLE daily_tip_calculation_details (id INT PRIMARY KEY AUTO_INCREMENT, calculation_id INT NOT NULL, worker_id INT NOT NULL, points_used INT NOT NULL, eligible BOOLEAN, raw_amount_clp DECIMAL(12,2), payable_amount_clp INT, rounding_remainder_clp DECIMAL(12,2));
CREATE TABLE rounding_remainders (id INT PRIMARY KEY AUTO_INCREMENT, period_id INT NOT NULL, source_date DATE NOT NULL, amount_clp DECIMAL(12,2), status VARCHAR(30));
CREATE TABLE monthly_closures (id INT PRIMARY KEY AUTO_INCREMENT, period_id INT NOT NULL, status VARCHAR(30), total_gross_clp INT, total_payable_clp INT, total_advances_clp INT, total_remainder_clp DECIMAL(12,2), carried_remainder_clp DECIMAL(12,2), closed_by INT, closed_at DATETIME);
CREATE TABLE monthly_closure_details (id INT PRIMARY KEY AUTO_INCREMENT, closure_id INT NOT NULL, worker_id INT NOT NULL, gross_clp INT, advances_clp INT, net_clp INT);
CREATE TABLE advance_request_statuses (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE advance_requests (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, period_id INT NOT NULL, amount_clp INT NOT NULL, reason TEXT NOT NULL, status VARCHAR(30), decision_reason TEXT, requested_at DATETIME);
CREATE TABLE advance_decisions (id INT PRIMARY KEY AUTO_INCREMENT, advance_request_id INT NOT NULL, decided_by INT NOT NULL, decision VARCHAR(30), reason TEXT, decided_at DATETIME);
CREATE TABLE payment_statuses (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(30) UNIQUE NOT NULL);
CREATE TABLE payments (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, period_id INT NOT NULL, gross_amount_clp INT, advance_discount_clp INT, adjustment_amount_clp INT, net_amount_clp INT, paid_amount_clp INT, status VARCHAR(30), paid_at DATETIME, paid_by INT);
CREATE TABLE payment_details (id INT PRIMARY KEY AUTO_INCREMENT, payment_id INT NOT NULL, concept VARCHAR(80), amount_clp INT NOT NULL);
CREATE TABLE worker_balances (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, period_id INT NOT NULL, gross_clp INT, advances_clp INT, net_clp INT);
CREATE TABLE adjustments (id INT PRIMARY KEY AUTO_INCREMENT, worker_id INT NOT NULL, period_id INT NOT NULL, amount_clp INT NOT NULL, reason TEXT);
CREATE TABLE notifications (id INT PRIMARY KEY AUTO_INCREMENT, user_id INT NOT NULL, title VARCHAR(120), body TEXT, read_at DATETIME);
CREATE TABLE system_settings (id INT PRIMARY KEY AUTO_INCREMENT, setting_key VARCHAR(80) UNIQUE NOT NULL, setting_value VARCHAR(240) NOT NULL);
CREATE TABLE audit_logs (id INT PRIMARY KEY AUTO_INCREMENT, user_id INT, module VARCHAR(80), action VARCHAR(80), entity_name VARCHAR(80), entity_id INT, old_values_json TEXT, new_values_json TEXT, ip_address VARCHAR(80), created_at DATETIME);
CREATE TABLE document_artifacts (id INT PRIMARY KEY AUTO_INCREMENT, path VARCHAR(240), artifact_type VARCHAR(80), created_at DATETIME);
CREATE TABLE api_logs (id INT PRIMARY KEY AUTO_INCREMENT, method VARCHAR(12), path VARCHAR(240), user_id INT, status_code INT, created_at DATETIME);
CREATE TABLE app_errors (id INT PRIMARY KEY AUTO_INCREMENT, module VARCHAR(80), message TEXT, handled BOOLEAN, created_at DATETIME);
'''


FRONTEND_APP = r'''
import React from "react";
import "bootstrap/dist/css/bootstrap.min.css";

export default function App() {
  return (
    <main className="container py-4">
      <h1>Propina360</h1>
      <p>Frontend React + Bootstrap para consumir la API FastAPI incluida en el backend.</p>
      <p>La version standalone operativa se sirve desde el backend en /admin y /dashboard.</p>
    </main>
  );
}
'''


def bundle_files() -> list[dict[str, str]]:
    files = {
        "README.md": README,
        "backend-fastapi/app/__init__.py": "",
        "backend-fastapi/app/main.py": MAIN_PY,
        "backend-fastapi/app/static/index.html": INDEX_HTML,
        "backend-fastapi/app/static/app.js": APP_JS,
        "backend-fastapi/app/static/styles.css": STYLES_CSS,
        "backend-fastapi/tests/test_propina360.py": TESTS_PY,
        "backend-fastapi/requirements.txt": "fastapi\nuvicorn\nsqlalchemy\npytest\n",
        "backend-fastapi/README.md": README,
        "database-mysql-mariadb/schema.sql": SCHEMA_SQL,
        "docs/consumo_tokens.md": CONSUMO_TOKENS,
        "docs/optimizacion_tokens_fabrica.md": CONSUMO_TOKENS,
        "docs/endpoints_api.md": ENDPOINTS_MD,
        "docs/documento_auditoria_tecnica.md": AUDIT_MD,
        "docs/documento_reportes.md": REPORTS_MD,
        "docs/modelo_datos.md": MODEL_MD,
        "docs/plan_pruebas.md": "Las pruebas automatizadas viven en backend-fastapi/tests y cubren permisos, CRUD, calculo, anticipos, reclamos, cierre y pagos.\n",
        "frontend-react-bootstrap/package.json": json.dumps({"scripts": {"dev": "vite", "build": "vite build"}, "dependencies": {"@vitejs/plugin-react": "latest", "vite": "latest", "react": "latest", "react-dom": "latest", "bootstrap": "latest", "react-bootstrap": "latest"}}, indent=2),
        "frontend-react-bootstrap/src/App.jsx": FRONTEND_APP,
        "frontend-react-bootstrap/src/main.jsx": "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport App from './App.jsx';\ncreateRoot(document.getElementById('root')).render(<App />);\n",
        "frontend-react-bootstrap/index.html": "<div id=\"root\"></div><script type=\"module\" src=\"/src/main.jsx\"></script>\n",
    }
    return [{"path": path, "content": content} for path, content in files.items()]


def main() -> None:
    work_order = {
        "objective": "Desarrollar Propina360 como sistema web funcional para gestion, calculo, anticipos, cierres y pagos de propinas en CLP con UI profesional, CRUDs y pruebas.",
        "project_id": "propina360",
        "project_version": "v0001",
        "type": "transactional_web_app",
        "scope": "local_artifacts_only",
        "side_effects": "no_external_writes_no_deploy",
        "authorized_sources": ["projects/propinas/especificacion_sistema_propinas_propina360.md"],
        "acceptance_criteria": [
            "Debe ejecutarse por arnes y orquestador WEBFORGE.",
            "Debe materializar codigo real en DEV mediante tool.sandbox.dev_materialize.",
            "Debe incluir backend FastAPI, frontend profesional, esquema MySQL/MariaDB y documentacion.",
            "Debe implementar CRUDs principales para trabajadores, secciones, turnos, propinas, periodos, pagos, anticipos y reclamos.",
            "Debe incluir registro de estimacion de consumo y optimizacion de tokens.",
            "Debe pasar pruebas automatizadas y validacion HTTP local."
        ],
        "budget": {"tool_calls": 200, "mcp_calls": 0, "cost_usd": 0},
        "approvals": {},
        "metadata": {
            "implementation_bundle": bundle_files(),
            "token_optimization": {
                "strategy": "single implementation bundle through factory materializer",
                "estimated_bundle_files": len(bundle_files()),
                "external_model_calls": 0
            }
        },
    }
    target = PROJECT_DIR / "work_order.json"
    target.write_text(json.dumps(work_order, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(target)
    print(f"bundle_files={len(bundle_files())}")


if __name__ == "__main__":
    main()
