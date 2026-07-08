
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
