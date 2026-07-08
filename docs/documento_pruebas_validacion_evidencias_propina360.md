# Documento de pruebas, validacion y evidencias - Propina360

## 1. Proposito

Este documento consolida el diseño y plan de pruebas del proyecto Propina360, el checklist de completitud del producto, la evidencia de las validaciones y restricciones CHECK definidas en la especificacion actualizada, y la evidencia disponible de pruebas automatizadas y cobertura.

Fuente funcional principal:

- `projects/propinas/especificacion_sistema_propinas_propina360.md`

Artefactos de ejecucion y evidencia usados:

- `runs/propina360-v0001/final-report.json`
- `runs/propina360-v0001/validation-report.json`
- `project/propina360/sandboxes/DEV/workspace/backend-fastapi/tests/test_propina360.py`
- `project/propina360/sandboxes/DEV/workspace/backend-fastapi/app/main.py`
- `project/propina360/sandboxes/DEV/workspace/backend-fastapi/app/static/app.js`

## 2. Diseno y plan de pruebas

### 2.1 Objetivos de prueba

Las pruebas deben demostrar que el sistema:

- Mantiene separadas las experiencias de administrador y trabajador.
- Permite registro publico de trabajador como solicitud pendiente.
- Muestra el mensaje `peticion creada, usuario pendiente de confirmacion`.
- Permite aprobacion o rechazo administrativo con razon.
- Permite completar ficha laboral despues de aprobar una solicitud.
- Calcula propinas por puntos y elegibilidad fulltime/parttime.
- Registra `point_value_clp` para cada propina diaria calculada.
- Descuenta inmediatamente anticipos aprobados desde la propina acumulada disponible.
- Exige razon al aprobar/rechazar anticipos y al resolver reclamos.
- Protege rutas por JWT y rol.
- Mantiene CRUDs y flujos administrativos principales operativos.

### 2.2 Capas de prueba

| Capa | Alcance | Evidencia esperada |
|---|---|---|
| Unitarias | Validadores, calculo, RUN, hashing, saldos, puntos | `pytest` sobre servicios y funciones |
| Integracion backend | SQLAlchemy, relaciones, seed, periodos, calculos, pagos | `pytest` con base SQLite local |
| API | Auth, admin, worker, anticipos, reclamos, pagos | Pruebas HTTP o cliente ASGI |
| UI funcional | Login por ruta, sidebar, solicitudes, dashboard admin/trabajador | E2E Playwright/Cypress o pruebas DOM |
| Fabrica WEBFORGE | Materializacion, artefactos, politicas, P01-P12 | `final-report.json` y `validation-report.json` |
| Cobertura | Cobertura de codigo y cobertura de requisitos | `pytest-cov`, matriz CHECK y trazabilidad |

### 2.3 Casos criticos

| Codigo | Flujo | Resultado esperado |
|---|---|---|
| CP-AUTH-01 | Admin entra por `/admin` | Login administrativo sin selector de rol |
| CP-AUTH-02 | Trabajador entra por `/dashboard` | Login trabajador sin selector de rol |
| CP-REG-01 | Registro publico valido | Solicitud pendiente y mensaje de confirmacion |
| CP-REG-02 | Aprobar solicitud con razon | Usuario queda `approved_pending_profile` |
| CP-REG-03 | Completar ficha laboral | Trabajador queda activo con RUN, codigo y puntos |
| CP-REG-04 | Rechazar solicitud con razon | Solicitud queda rechazada y trazada |
| CP-TIP-01 | Registrar y calcular propina diaria | Reparto por puntos, redondeo y `point_value_clp` |
| CP-ADV-01 | Solicitar anticipo valido | Solicitud queda pendiente |
| CP-ADV-02 | Aprobar anticipo con razon | Descuento inmediato en saldo disponible |
| CP-ADV-03 | Rechazar anticipo con razon | No modifica saldo |
| CP-CLAIM-01 | Crear reclamo valido | Reclamo queda pendiente |
| CP-CLAIM-02 | Resolver reclamo con razon | Estado y razon quedan guardados |
| CP-DASH-01 | Dashboard admin | Muestra solicitudes de usuario pendientes |
| CP-DASH-02 | Dashboard trabajador | Muestra propina acumulada disponible |

## 3. Checklist de validacion de completitud del producto

| Item | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Backend FastAPI inicia sin errores | Cumple | `uvicorn app.main:app` usado en validaciones previas |
| 2 | Frontend se sirve desde backend | Cumple | `app/static/index.html`, `app/static/app.js`, `app/static/styles.css` |
| 3 | Base de datos local operativa | Cumple | `propina360.db`, `SessionLocal`, `reset_database()` |
| 4 | WEBFORGE completa ciclo | Cumple | `runs/propina360-v0001/final-report.json` con `status complete` |
| 5 | Artefactos requeridos presentes | Cumple | `validation-report.json` sin faltantes |
| 6 | Admin inicial existe | Cumple | `test_auth_roles_and_run_helpers` |
| 7 | Trabajador seed existe | Cumple | `test_auth_roles_and_run_helpers` |
| 8 | Registro publico crea solicitud | Cumple | `test_public_registration_requires_admin_decision_and_profile_completion` |
| 9 | Mensaje de registro publico | Cumple | Assertion sobre `peticion creada, usuario pendiente de confirmacion` |
| 10 | Aprobacion con estado intermedio | Cumple | Assertion sobre `approved_pending_profile` |
| 11 | Completar ficha laboral | Cumple | Assertion sobre trabajador activo y codigo interno |
| 12 | RUN chileno validado | Cumple | `validate_run` probado |
| 13 | Codigo interno desde RUN | Cumple | `internal_code` probado |
| 14 | Calculo diario de propinas | Cumple | `test_daily_tip_calculation_fulltime_parttime_and_rounding` |
| 15 | Valor del punto diario | Cumple | Assertion `fund.point_value_clp > 0` |
| 16 | Redondeo a multiplo de 10 | Cumple | Assertion sobre `payable_amount_clp % 10 == 0` |
| 17 | Anticipos con descuento | Cumple parcial | Cubierto por `worker_balance` y `prepare_worker_payment`; falta prueba HTTP dedicada |
| 18 | Reclamos con razon | Cumple parcial | Cubierto a nivel modelo/servicio; falta prueba HTTP dedicada |
| 19 | Dashboard admin con solicitudes | Cumple parcial | Evidencia estatica en `app.js`; falta E2E visual |
| 20 | Dashboard trabajador con saldo disponible | Cumple parcial | Evidencia estatica y API; falta E2E visual |
| 21 | Login sin selector de rol | Cumple parcial | Evidencia estatica en `app.js`; falta E2E visual |
| 22 | Sidebar admin/trabajador | Cumple parcial | Evidencia estatica en `app.js` y `styles.css`; falta E2E visual |
| 23 | Pruebas automatizadas pasan | Cumple | `5 passed` |
| 24 | Cobertura de codigo 100% | No cumple hoy | `pytest-cov` reporta 64.39% |
| 25 | Cobertura de evidencia critica de fabrica 100% | Cumple | `final-report.json`: `evidence_coverage_critical_claims: 100` |

## 4. Evidencia de validaciones y restricciones CHECK

La especificacion actualizada define validaciones CHECK numeradas hasta 110, incluyendo identificadores intermedios 18B, 39B, 39C, 60B, 84B y 96B. La evidencia se organiza por bloque para mantener trazabilidad sin duplicar toda la especificacion.

| CHECK | Area | Evidencia funcional | Evidencia automatizada actual |
|---|---|---|---|
| 1-18B | Registro publico, email, nombre, telefono, clave, estado inicial y mensaje | `register()`, `User`, `WorkerRegistrationRequest` | Parcial: `test_public_registration_requires_admin_decision_and_profile_completion` cubre registro valido, estado pendiente y mensaje |
| 19-24 | RUN, digito verificador, unicidad y codigo interno | `validate_run()`, `internal_code()`, `create_worker()` | Parcial: `test_auth_roles_and_run_helpers`, `test_create_worker_and_crud_update`, prueba de completar ficha |
| 25-34 | Contrato, puntos, vigencia, cargo y seccion | `create_worker()`, `WorkerPointsHistory`, `Section`, `ContractType` | Parcial: `test_create_worker_and_crud_update` cubre puntos y creacion basica |
| 35-39C | Activacion, aprobacion/rechazo de solicitud y completado de ficha | `approve_user()`, `complete_pending_user_worker()`, `reject_user()` | Parcial: prueba cubre aprobacion y completado; falta rechazo sin razon |
| 40-50 | Turnos, fechas, horas, duplicidad, anulacion e inactividad | `Shift`, endpoints `/api/admin/shifts*` | No cubierto por prueba automatizada dedicada |
| 51-60B | Propina diaria, monto, duplicidad, calculo, elegibilidad, puntos y valor del punto | `DailyTipFund`, `calculate_daily()`, `eligible_workers()` | Parcial: `test_daily_tip_calculation_fulltime_parttime_and_rounding` cubre monto valido, elegibilidad, redondeo y `point_value_clp` |
| 61-67 | Porcentajes, monto bruto, monto pagable y sobrantes | `DailyTipCalculation`, `DailyTipCalculationDetail`, `RoundingRemainder` | Parcial: prueba valida montos pagables y limite contra fondo diario |
| 68-73 | Periodos mensuales, duplicidad, cierre y reapertura | `Period`, `ensure_period()`, endpoints `/api/admin/periods*` | Parcial: `test_advance_claim_close_and_payment_flow` usa periodo y cierre a nivel modelo |
| 74-84B | Anticipos, monto, motivo, saldo, decision y descuento inmediato | `AdvanceRequest`, `worker_balance()`, `prepare_worker_payment()`, endpoint `admin_advance_decide()` | Parcial: `test_advance_claim_close_and_payment_flow` valida descuento en pago; falta prueba HTTP de razon obligatoria |
| 85-92 | Pagos, fecha, monto, duplicidad, anulacion | `Payment`, `prepare_worker_payment()` | Parcial: `test_advance_claim_close_and_payment_flow` cubre preparacion y pago |
| 93-96B | Reclamos, descripcion, periodo, resolucion y razon | `ShiftClaim`, endpoint `admin_claim_resolve()` | Parcial: prueba valida resolucion y razon a nivel modelo; falta prueba HTTP de razon obligatoria |
| 97-100 | Rutas protegidas, permisos admin/trabajador y aislamiento de datos | `current_user()`, `require_admin()`, `require_worker()` | No cubierto por prueba HTTP automatizada dedicada |
| 101-105 | Configuracion, paginacion, filtros y documentos sin secretos | `SystemSetting`, docs y reportes de seguridad WEBFORGE | Parcial: `validation-report.json`, `security-review.md`, `secrets-report.json` |
| 106-110 | Login por ruta, sidebar, solicitudes admin, contador y no duplicar crear trabajador | `app/static/app.js`, `app/static/styles.css` | Evidencia estatica; falta prueba E2E visual/DOM automatizada |

### 4.1 Lectura de evidencia CHECK

- **Cumple automatizado**: existe assertion en `tests/test_propina360.py`.
- **Cumple parcial**: la funcionalidad existe y hay evidencia indirecta o estatica, pero falta una prueba dedicada para todo el CHECK.
- **No cubierto por prueba automatizada dedicada**: debe incorporarse al backlog de cobertura 100%.

## 5. Evidencia de pruebas automatizadas

### 5.1 Comando de pruebas unitarias/integracion

Comando ejecutado:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Resultado observado:

```text
5 passed
```

Pruebas cubiertas:

- `test_auth_roles_and_run_helpers`
- `test_create_worker_and_crud_update`
- `test_public_registration_requires_admin_decision_and_profile_completion`
- `test_daily_tip_calculation_fulltime_parttime_and_rounding`
- `test_advance_claim_close_and_payment_flow`

### 5.2 Comando de cobertura de codigo al 100%

Comando ejecutado:

```bash
PYTHONPATH=. python3 -m pytest --cov=app --cov-report=term-missing --cov-fail-under=100 -q
```

Resultado observado:

```text
5 passed
ERROR: Coverage failure: total of 64 is less than fail-under=100
TOTAL 893 statements, 318 missing, 64.39% coverage
```

Conclusion de evidencia:

- Las pruebas automatizadas actuales pasan.
- La cobertura de codigo automatizada **no alcanza 100%** en el estado actual.
- No es correcto declarar cobertura de codigo 100% con la evidencia existente.
- La fabrica si reporta `evidence_coverage_critical_claims: 100`, lo que corresponde a cobertura de evidencias criticas del ciclo WEBFORGE, no a cobertura de lineas de codigo.

## 6. Brecha para lograr cobertura automatizada 100%

Para declarar cobertura automatizada 100% de forma verificable se requiere agregar pruebas dedicadas para:

- Login trabajador/admin por ruta y bloqueo cruzado.
- Endpoints protegidos `require_admin` y `require_worker`.
- Rechazo de solicitud de usuario con y sin razon.
- Aprobacion de solicitud sin razon.
- Completar ficha laboral en estado invalido.
- CRUD completo de trabajadores, secciones, turnos, propinas, periodos, pagos, anticipos y reclamos.
- Anulacion de turnos y pagos.
- Reapertura de periodo con motivo.
- Endpoints worker: dashboard, shifts, payments, advances, claims y profile.
- Validaciones negativas de montos, fechas, duplicados y estados no pendientes.
- UI o E2E para sidebar, dashboard admin con solicitudes pendientes, login sin selector de rol y creacion de trabajador separada.

## 7. Dictamen de completitud

| Dimension | Estado actual | Dictamen |
|---|---|---|
| Ciclo WEBFORGE | Completo | Aprobado por fabrica |
| Artefactos requeridos | Presentes | Aprobado |
| Pruebas automatizadas basicas | 5/5 pasan | Aprobado |
| Validaciones CHECK | Especificadas y parcialmente evidenciadas | Requiere ampliar pruebas |
| Cobertura critica WEBFORGE | 100% | Aprobado como evidencia de fabrica |
| Cobertura de codigo automatizada | 64.39% | No cumple meta 100% |

El producto tiene evidencia funcional y de fabrica suficiente para demostrar los flujos principales implementados. La meta de cobertura automatizada 100% queda definida, pero no esta alcanzada por la suite actual.
