
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
