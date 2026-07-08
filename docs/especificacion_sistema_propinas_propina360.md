# Especificación del sistema web: Gestión Avanzada de Propinas

## 1. Nombre del sistema

**Propina360 — Sistema Web de Gestión, Cálculo, Anticipos y Pagos de Propinas en CLP**

---

## 2. Objetivo general

Desarrollar una aplicación web responsiva para registrar trabajadores, aprobar usuarios, administrar turnos, registrar fondos diarios de propina, calcular la distribución proporcional por puntos, gestionar anticipos, preparar cierres mensuales y controlar pagos de propinas en pesos chilenos (**CLP**).

El sistema debe permitir que los trabajadores creen su propia cuenta desde la página pública, queden pendientes de aprobación y posteriormente sean configurados por el administrador con sus datos laborales: RUN chileno, código interno derivado del RUN, tipo de contrato, sección, cargo y cantidad de puntos.

El sistema debe separar completamente la experiencia del **administrador** y la del **trabajador**. El administrador opera desde una ruta administrativa, por ejemplo `http://localhost:3000/admin`, mientras que los trabajadores acceden al dashboard regular después del login normal, por ejemplo `http://localhost:3000/dashboard` o `/`.

---

## 3. Alcance del sistema

El sistema será una aplicación web multiusuario orientada a negocios donde la propina se acumula en un fondo común diario y se distribuye a trabajadores según puntos y elegibilidad.

Debe incluir:

- Backend web con API REST.
- Base de datos MySQL o MariaDB.
- Frontend web responsivo con React + Bootstrap.
- Autenticación con JWT.
- Creación pública de usuarios trabajadores.
- Bandeja administrativa de solicitudes de usuario pendientes.
- Aprobación o rechazo administrativo de solicitudes de usuario con razón obligatoria.
- Completado administrativo de ficha laboral para usuarios aprobados.
- Gestión administrativa de trabajadores activos.
- Registro de RUN chileno y generación automática de código interno.
- Gestión de puntos por trabajador e historial de vigencia.
- Gestión de tipos de contrato fulltime y parttime.
- Registro administrativo de turnos.
- Registro administrativo de propina diaria en CLP, incluyendo el valor del punto calculado para cada día.
- Cálculo diario de reparto por puntos.
- Cierre mensual de propinas.
- Solicitudes de anticipo por trabajador.
- Aprobación o rechazo de anticipos por administrador con razón obligatoria.
- Descuento inmediato de anticipos aprobados sobre la propina acumulada disponible del trabajador.
- Registro de pagos mensuales.
- Dashboard administrativo exclusivo.
- Dashboard administrativo con navegación lateral y tarjeta inicial de solicitudes de usuario pendientes.
- Dashboard trabajador exclusivo con navegación lateral y propina acumulada del periodo actual al inicio.
- Sección separada para crear nuevo trabajador, accesible desde la barra lateral administrativa.
- Validaciones, restricciones y pruebas automatizadas.
- Documentación técnica de reportes y auditoría dentro de la carpeta `docs/`, sin pantallas de reportes ni auditoría dentro de la aplicación.

No se incluyen en esta primera versión:

- Integración bancaria real.
- Firma electrónica.
- Emisión de liquidaciones laborales oficiales.
- Integración con SII.
- Aplicación móvil nativa.
- Módulo visible de reportes dentro de la aplicación.
- Módulo visible de auditoría dentro de la aplicación.
- Gestión de múltiples locales o empresas, salvo que se agregue en una versión futura.

---

## 4. Tipo de aplicación y tecnologías sugeridas

Aplicación web transaccional multiusuario.

Tecnologías sugeridas:

- Backend: Python 3 con FastAPI.
- Base de datos: MySQL o MariaDB.
- ORM: SQLAlchemy.
- Migraciones: Alembic.
- Frontend: React + Bootstrap.
- Cliente HTTP: Axios o Fetch API.
- Autenticación: JWT con refresh token.
- Validación backend: Pydantic.
- Pruebas backend: Pytest.
- Pruebas frontend: Vitest o Jest + Testing Library.
- Pruebas end-to-end: Playwright o Cypress.
- Cobertura: pytest-cov, coverage.py y herramienta equivalente para frontend.

Arquitectura mínima:

```text
frontend-react-bootstrap/
backend-fastapi/
database-mysql-mariadb/
docs/
tests/
```

---

## 5. Roles, rutas y separación de experiencia

### 5.1 Rol administrador

El administrador es un usuario único inicial con credenciales predeterminadas para pruebas. Puede administrar toda la operación del sistema.

Ruta principal:

```text
/admin
```

Operaciones disponibles:

- Iniciar sesión como administrador.
- Ver dashboard administrativo.
- Revisar solicitudes de usuario pendientes de aprobación.
- Aprobar o rechazar solicitudes de usuario con razón obligatoria.
- Completar ficha laboral de usuarios aprobados pendientes de configuración.
- Crear, editar, activar y desactivar trabajadores.
- Configurar RUN, puntos, sección, cargo y tipo de contrato.
- Registrar y corregir turnos.
- Registrar fondos diarios de propina.
- Ejecutar cálculo diario de propinas.
- Generar y confirmar cierre mensual.
- Aprobar o rechazar anticipos.
- Preparar y registrar pagos.
- Resolver reclamos de turno aceptando o rechazando con razón obligatoria.
- Configurar parámetros generales del sistema.
- Cerrar sesión.

### 5.2 Rol trabajador

El trabajador es un usuario registrado desde la página pública y aprobado posteriormente por el administrador.

Ruta principal regular:

```text
/dashboard
```

Operaciones disponibles:

- Crear cuenta desde el formulario público.
- Recibir confirmación explícita de solicitud creada y pendiente de confirmación administrativa.
- Iniciar sesión si fue aprobado.
- Cerrar sesión.
- Ver dashboard personal.
- Ver la propina acumulada disponible del periodo actual.
- Ver pagos pasados.
- Ver pagos pendientes.
- Ver solicitudes de anticipo pasadas.
- Crear solicitud de anticipo.
- Cancelar solicitud de anticipo pendiente.
- Verificar turnos registrados.
- Crear reclamo por turno incorrecto.
- Editar datos personales permitidos.
- Cambiar contraseña.

### 5.3 Restricción de separación

- El dashboard del administrador no debe compartir layout, menú ni rutas con el dashboard del trabajador.
- El trabajador no puede acceder a rutas `/admin`, aunque conozca la URL.
- El administrador no usa el dashboard regular de trabajador.
- El formulario de login no debe mostrar selector de rol o tipo de usuario; `/admin` siempre presenta login administrativo y `/dashboard` o `/` siempre presentan login de trabajador.
- Ambos dashboards deben usar barra lateral para separar secciones y evitar que todas las funciones queden acumuladas en una sola pantalla.
- Los componentes visuales reutilizables pueden compartirse internamente, pero las vistas y permisos deben estar separados.

---

## 6. Flujo principal general

1. Una persona entra a la página pública.
2. Crea su usuario con datos personales básicos.
3. El sistema muestra el mensaje `peticion creada, usuario pendiente de confirmacion`.
4. El sistema crea una solicitud administrativa de usuario y deja la cuenta en estado pendiente.
5. El administrador entra por `/admin`.
6. El administrador revisa solicitudes de usuario pendientes desde dashboard o sección de solicitudes.
7. El administrador aprueba o rechaza la solicitud con una razón obligatoria.
8. Si aprueba, el usuario queda pendiente de completar ficha laboral.
9. El administrador completa la ficha laboral del trabajador.
10. El sistema valida RUN chileno y genera código interno.
11. El administrador registra turnos y propinas diarias.
12. El sistema calcula la propina diaria según puntos y elegibilidad, registrando el valor del punto del día.
13. El trabajador inicia sesión en el dashboard regular.
14. El trabajador ve su propina acumulada disponible, pagos, anticipos y turnos.
15. El trabajador puede solicitar anticipos o reclamar turnos.
16. El administrador aprueba anticipos, resuelve reclamos con razón y cierra el periodo mensual.
17. El administrador registra pagos mensuales.
18. El trabajador consulta pagos pasados y pendientes.

---

## 7. Funcionalidades principales

| N° | Funcionalidad o flujo |
|---|---|
| 1 | Crear cuenta pública de trabajador. |
| 2 | Confirmar registro con mensaje de petición creada y dejar usuario pendiente de confirmación. |
| 3 | Iniciar sesión como trabajador aprobado. |
| 4 | Iniciar sesión como administrador por ruta /admin. |
| 5 | Cerrar sesión. |
| 6 | Recuperar contraseña. |
| 7 | Aprobar solicitud de usuario pendiente con razón obligatoria. |
| 8 | Rechazar solicitud de usuario pendiente con razón obligatoria. |
| 9 | Completar ficha de trabajador desde usuario aprobado pendiente de configuración. |
| 10 | Editar datos laborales del trabajador. |
| 11 | Configurar puntos vigentes del trabajador. |
| 12 | Cambiar tipo de contrato. |
| 13 | Activar trabajador. |
| 14 | Desactivar trabajador. |
| 15 | Crear sección o área de trabajo. |
| 16 | Registrar turno individual. |
| 17 | Registrar turnos masivos por día. |
| 18 | Corregir turno antes de cierre. |
| 19 | Anular turno con motivo. |
| 20 | Registrar propina diaria y conservar el valor del punto calculado para ese día. |
| 21 | Editar propina diaria antes de cierre. |
| 22 | Calcular distribución diaria. |
| 23 | Recalcular distribución diaria antes del cierre mensual. |
| 24 | Generar previsualización del cierre mensual. |
| 25 | Confirmar cierre mensual. |
| 26 | Preparar pagos mensuales. |
| 27 | Registrar pago mensual. |
| 28 | Solicitar anticipo como trabajador. |
| 29 | Aprobar anticipo como administrador con razón y descuento inmediato del saldo disponible. |
| 30 | Rechazar anticipo como administrador con razón obligatoria. |
| 31 | Cancelar solicitud de anticipo pendiente. |
| 32 | Ver dashboard trabajador con propina acumulada disponible del periodo actual. |
| 33 | Ver historial personal de pagos. |
| 34 | Ver pagos pendientes personales. |
| 35 | Ver solicitudes personales pasadas. |
| 36 | Verificar turnos registrados personales. |
| 37 | Crear reclamo de turno. |
| 38 | Resolver reclamo de turno como administrador con razón obligatoria. |
| 39 | Consultar dashboard administrativo. |
| 40 | Consultar lista de trabajadores y filtros. |
| 41 | Navegar dashboard administrativo por barra lateral separada. |
| 42 | Navegar dashboard trabajador por barra lateral separada. |
| 43 | Crear nuevo trabajador desde sección administrativa independiente. |
| 44 | Ver solicitudes de usuario pendientes como tarjeta destacada del dashboard administrativo. |

---

## 8. Casos de uso diferenciados

## 8.1 Casos de uso del administrador

### CU-A01: Iniciar sesión como administrador

**Actor:** Administrador.

**Flujo:**

1. Administrador abre /admin.
2. Ingresa email y contraseña predeterminados o actualizados.
3. Sistema valida credenciales y rol.
4. Sistema muestra dashboard administrativo con barra lateral, tarjeta de solicitudes de usuario pendientes y accesos a secciones administrativas.

**Resultado esperado:** Administrador accede a operaciones administrativas.

### CU-A02: Aprobar solicitud de usuario trabajador

**Actor:** Administrador.

**Flujo:**

1. Administrador entra a solicitudes de usuario pendientes.
2. Revisa datos de registro.
3. Ingresa la razón de aprobación.
4. Aprueba la solicitud.
5. Sistema deja al usuario en estado aprobado pendiente de completar ficha laboral.

**Resultado esperado:** Usuario queda habilitado para configurar su ficha laboral, pero todavía no participa como trabajador activo.

### CU-A02B: Rechazar solicitud de usuario trabajador

**Actor:** Administrador.

**Flujo:**

1. Administrador entra a solicitudes de usuario pendientes.
2. Revisa datos de registro.
3. Ingresa la razón de rechazo.
4. Rechaza la solicitud.
5. Sistema conserva la razón y marca la solicitud como rechazada.

**Resultado esperado:** Usuario no puede iniciar sesión como trabajador y la decisión queda trazada.

### CU-A03: Configurar ficha laboral

**Actor:** Administrador.

**Flujo:**

1. Selecciona usuario aprobado pendiente de ficha laboral o trabajador existente.
2. Ingresa RUN, sección, cargo, tipo de contrato y puntos.
3. Sistema valida RUN y genera código interno.
4. Administrador guarda cambios.

**Resultado esperado:** Trabajador queda activo y elegible para cálculos.

### CU-A04: Registrar turnos diarios

**Actor:** Administrador.

**Flujo:**

1. Entra a registro de turnos.
2. Selecciona fecha y trabajadores.
3. Marca turnos trabajados o ausencias.
4. Sistema valida duplicados y periodo abierto.

**Resultado esperado:** Turnos quedan disponibles para cálculo de propinas.

### CU-A05: Registrar propina diaria

**Actor:** Administrador.

**Flujo:**

1. Selecciona fecha.
2. Ingresa monto total CLP.
3. Sistema valida monto y duplicidad.
4. Guarda fondo diario.

**Resultado esperado:** Propina diaria queda registrada.

### CU-A06: Calcular reparto diario

**Actor:** Administrador.

**Flujo:**

1. Selecciona día con propina registrada.
2. Sistema identifica trabajadores elegibles.
3. Calcula proporción por puntos.
4. Registra en la propina diaria el valor del punto calculado para ese día.
5. Aplica redondeos y registra sobrante.

**Resultado esperado:** Reparto diario queda calculado.

### CU-A07: Cerrar periodo mensual

**Actor:** Administrador.

**Flujo:**

1. Selecciona periodo.
2. Sistema valida días, anticipos y cálculos.
3. Previsualiza saldos.
4. Administrador confirma cierre.

**Resultado esperado:** Periodo queda cerrado y listo para pago.

### CU-A08: Gestionar pagos

**Actor:** Administrador.

**Flujo:**

1. Selecciona periodo cerrado.
2. Prepara pagos.
3. Marca pago como pagado.
4. Sistema registra fecha, monto y responsable.

**Resultado esperado:** Pago queda registrado en historial del trabajador.

### CU-A09: Gestionar anticipos

**Actor:** Administrador.

**Flujo:**

1. Revisa solicitudes pendientes.
2. Evalúa saldo disponible.
3. Ingresa una razón obligatoria para aprobar o rechazar.
4. Aprueba o rechaza la solicitud.
5. Si aprueba, el sistema descuenta inmediatamente el monto del saldo disponible del trabajador y actualiza la preparación de pago del periodo.
6. Sistema notifica estado.

**Resultado esperado:** Solicitud queda resuelta.

### CU-A10: Resolver reclamo de turno

**Actor:** Administrador.

**Flujo:**

1. Abre reclamo.
2. Compara con turnos registrados.
3. Ingresa una razón obligatoria de aceptación o rechazo.
4. Acepta o rechaza.
5. Si acepta, corrige turno antes del cierre.

**Resultado esperado:** Reclamo queda cerrado.


## 8.2 Casos de uso del trabajador

### CU-T01: Crear usuario desde página pública

**Actor:** Trabajador.

**Flujo:**

1. Trabajador abre registro.
2. Ingresa email, nombre, apellido, teléfono y contraseña.
3. Sistema valida datos.
4. Sistema muestra `peticion creada, usuario pendiente de confirmacion`.
5. Sistema deja cuenta pendiente de aprobación administrativa.

**Resultado esperado:** Registro queda pendiente de revisión administrativa.

### CU-T02: Iniciar sesión como trabajador

**Actor:** Trabajador.

**Flujo:**

1. Ingresa email y contraseña.
2. Sistema valida usuario aprobado y activo.
3. Sistema muestra dashboard regular.

**Resultado esperado:** Trabajador accede a su información personal.

### CU-T03: Ver propina acumulada del periodo

**Actor:** Trabajador.

**Flujo:**

1. Ingresa al dashboard.
2. Sistema obtiene periodo actual.
3. Muestra la propina acumulada disponible del periodo actual, ya descontando anticipos aprobados aplicables.

**Resultado esperado:** Trabajador ve su estado económico actualizado.

### CU-T04: Verificar turnos registrados

**Actor:** Trabajador.

**Flujo:**

1. Entra a mis turnos.
2. Filtra por periodo.
3. Revisa días trabajados o ausencias.

**Resultado esperado:** Trabajador valida información usada para cálculo.

### CU-T05: Crear reclamo de turno

**Actor:** Trabajador.

**Flujo:**

1. Selecciona fecha reclamada.
2. Describe el problema.
3. Envía reclamo.
4. Sistema lo deja pendiente.

**Resultado esperado:** Administrador puede revisar la discrepancia.

### CU-T06: Solicitar anticipo

**Actor:** Trabajador.

**Flujo:**

1. Entra a anticipos.
2. Ingresa monto CLP y motivo.
3. Sistema valida saldo disponible y múltiplo de 10.
4. Envía solicitud.

**Resultado esperado:** Solicitud queda pendiente.

### CU-T07: Cancelar anticipo pendiente

**Actor:** Trabajador.

**Flujo:**

1. Abre solicitud pendiente.
2. Selecciona cancelar.
3. Sistema confirma acción.

**Resultado esperado:** Solicitud queda cancelada.

### CU-T08: Consultar pagos pasados

**Actor:** Trabajador.

**Flujo:**

1. Entra a pagos pasados.
2. Selecciona periodo.
3. Sistema muestra monto pagado y detalle.

**Resultado esperado:** Trabajador consulta su historial.

### CU-T09: Consultar pagos pendientes

**Actor:** Trabajador.

**Flujo:**

1. Entra a pagos pendientes.
2. Sistema muestra periodos cerrados no pagados o pagos preparados.

**Resultado esperado:** Trabajador conoce montos por cobrar.

### CU-T10: Cerrar sesión

**Actor:** Trabajador o administrador.

**Flujo:**

1. Usuario presiona salir.
2. Sistema invalida sesión local y token cuando aplique.
3. Redirige al login.

**Resultado esperado:** Sesión finaliza correctamente.


---

## 9. Dashboard del administrador

El dashboard administrativo debe estar disponible solo desde `/admin` y mostrar información global del sistema.

Indicadores mínimos:

- Total de trabajadores activos.
- Total de solicitudes de usuario pendientes de confirmación.
- Total de propina registrada en el periodo actual.
- Total de propina calculada en el periodo actual.
- Total de anticipos pendientes.
- Total de anticipos aprobados del periodo.
- Total estimado por pagar al cierre mensual.
- Días del periodo con propina registrada.
- Días del periodo pendientes de cálculo.
- Reclamos de turno pendientes.
- Últimos turnos registrados.
- Últimos pagos marcados como pagados.

Bloque destacado obligatorio:

```text
Solicitudes de usuario pendientes: X
```

Este bloque debe aparecer en el dashboard inicial del administrador y debe permitir navegar directamente a la sección de solicitudes de usuario.

Accesos rápidos:

- Revisar solicitudes de usuario.
- Gestionar trabajadores.
- Registrar turnos.
- Registrar propina diaria.
- Calcular propina diaria.
- Cerrar periodo mensual.
- Revisar anticipos.
- Registrar pagos.
- Resolver reclamos.
- Configuración general.

Reglas:

- Debe cargar datos reales desde API.
- Debe bloquearse para cualquier usuario sin rol administrador.
- Debe organizar las secciones mediante barra lateral, incluyendo Dashboard, Solicitudes de usuario, Trabajadores, Crear nuevo trabajador, Turnos, Propinas diarias, Cierre y pagos, Anticipos y Reclamos.
- La sección de Trabajadores no debe duplicar el botón de crear nuevo trabajador si este ya existe en la barra lateral.
- No debe mostrar módulos de reportes ni auditoría como secciones de la aplicación.

---

## 10. Dashboard del trabajador

El dashboard del trabajador debe ser la primera vista después de iniciar sesión en la ruta regular.

Indicador principal obligatorio al inicio:

```text
Propina acumulada del periodo actual: $X CLP
```

Debe mostrar:

- Propina acumulada disponible del periodo actual.
- Últimos turnos registrados.
- Próximo pago pendiente, si existe.
- Solicitudes de anticipo recientes.
- Reclamos de turno recientes.
- Estado laboral: activo, pendiente, inactivo o suspendido.
- Tipo de contrato.
- Puntos vigentes.

Reglas:

- El trabajador solo puede ver sus propios datos.
- No puede modificar turnos ni pagos.
- Puede reclamar turnos incorrectos.
- Puede solicitar anticipos si está activo.
- La vista inicial no debe mostrar tarjetas separadas de anticipos aprobados ni saldo estimado; esos detalles pertenecen a las secciones de anticipos y pagos.
- El dashboard trabajador debe organizar sus secciones mediante barra lateral, incluyendo Resumen, Mis turnos, Mis pagos, Mis anticipos, Reclamos y Perfil.
- La moneda siempre se muestra en CLP, con separador de miles chileno.

---

## 11. Manejo de CLP, decimales, redondeo y sobrantes

La moneda del sistema es siempre **CLP**.

Aunque los montos pagables en pesos chilenos deben ser enteros, el cálculo interno puede usar decimales para mantener precisión proporcional.

### 11.1 Fórmula base de reparto diario

```text
puntos_totales_dia = suma de puntos de trabajadores elegibles
participacion_trabajador = puntos_trabajador / puntos_totales_dia
monto_bruto_trabajador = propina_dia * participacion_trabajador
```

### 11.2 Redondeo pagable

Todo monto que será pagado debe redondearse hacia abajo al múltiplo de 10 CLP más cercano.

Ejemplo:

```text
Monto bruto calculado: $12.347 CLP
Monto pagable:         $12.340 CLP
Sobrante:              $7 CLP
```

### 11.3 Sobrante mensual

Los sobrantes diarios generados por redondeo se acumulan durante el mes.

Al cierre mensual:

1. Se calcula el total de sobrantes acumulados.
2. Se identifica el último día trabajado del periodo.
3. Se redistribuye el sobrante equitativamente entre los trabajadores elegibles de ese último día.
4. Cada redistribución también se redondea hacia abajo al múltiplo de 10 CLP.
5. Si vuelve a quedar sobrante, se arrastra al siguiente mes.
6. El arrastre debe quedar documentado en la tabla `rounding_remainders`.

---

## 12. Modelo de datos mínimo: 40+ tablas

| N° | Tabla | Propósito |
|---|---|---|
| 1 | users | Cuentas de acceso al sistema. |
| 2 | roles | Roles disponibles: admin y worker. |
| 3 | permissions | Permisos internos por módulo. |
| 4 | role_permissions | Relación rol-permiso. |
| 5 | user_sessions | Sesiones JWT o refresh tokens. |
| 6 | password_reset_tokens | Tokens de recuperación de contraseña. |
| 7 | worker_registration_requests | Solicitudes públicas de usuario con estado, razón de decisión y transición a ficha laboral. |
| 8 | workers | Ficha laboral de trabajadores. |
| 9 | worker_personal_data | Datos personales extendidos. |
| 10 | contract_types | Tipos de contrato: fulltime y parttime. |
| 11 | worker_statuses | Estados laborales. |
| 12 | sections | Secciones o áreas de trabajo. |
| 13 | positions | Cargos o funciones. |
| 14 | worker_points_history | Historial de puntos por vigencia. |
| 15 | worker_contract_history | Historial de cambios de contrato. |
| 16 | periods | Periodos mensuales. |
| 17 | calendar_days | Días calendario del sistema. |
| 18 | shifts | Turnos registrados. |
| 19 | shift_types | Tipos de turno. |
| 20 | shift_statuses | Estados del turno. |
| 21 | shift_claims | Reclamos de turno de trabajadores. |
| 22 | shift_claim_statuses | Estados de reclamos. |
| 23 | daily_tip_funds | Fondos diarios de propina. |
| 24 | daily_tip_calculations | Cabecera de cálculo diario. |
| 25 | daily_tip_calculation_details | Detalle de reparto diario por trabajador. |
| 26 | rounding_remainders | Sobrantes por redondeo. |
| 27 | monthly_closures | Cierres mensuales. |
| 28 | monthly_closure_details | Detalle por trabajador del cierre. |
| 29 | advance_requests | Solicitudes de anticipo. |
| 30 | advance_request_statuses | Estados de anticipo. |
| 31 | advance_decisions | Aprobaciones o rechazos de anticipos. |
| 32 | payments | Pagos mensuales. |
| 33 | payment_details | Desglose de pagos. |
| 34 | payment_statuses | Estados de pago. |
| 35 | worker_balances | Saldos consolidados por trabajador y periodo. |
| 36 | adjustments | Ajustes administrativos de saldo. |
| 37 | notifications | Notificaciones internas. |
| 38 | system_settings | Parámetros del sistema. |
| 39 | audit_logs | Registro técnico interno de acciones críticas. |
| 40 | document_artifacts | Documentos generados del proyecto en carpeta docs. |
| 41 | api_logs | Registro técnico de llamadas relevantes. |
| 42 | app_errors | Errores controlados de aplicación. |

---

## 13. Campos principales por tabla clave

### 13.1 Tabla `users`

```text
id
email
password_hash
first_name
last_name
phone
role_id
status
created_at
updated_at
```

Estados mínimos de usuario trabajador:

```text
pending_approval
approved_pending_profile
approved
rejected
```

### 13.2 Tabla `workers`

```text
id
user_id
run
internal_code
section_id
position_id
contract_type_id
worker_status_id
hired_at
terminated_at
created_at
updated_at
```

### 13.3 Tabla `worker_points_history`

```text
id
worker_id
points
valid_from
valid_to
created_by
reason
created_at
updated_at
```

### 13.4 Tabla `shifts`

```text
id
worker_id
shift_date
shift_type_id
status_id
start_time
end_time
worked_minutes
created_by
voided_by
void_reason
created_at
updated_at
```

### 13.5 Tabla `daily_tip_funds`

```text
id
tip_date
amount_clp
point_value_clp
status
registered_by
notes
created_at
updated_at
```

`point_value_clp` debe registrar el valor del punto usado para la propina diaria calculada en esa fecha.

### 13.6 Tabla `daily_tip_calculation_details`

```text
id
calculation_id
worker_id
contract_type
points_used
eligible
raw_amount_clp
payable_amount_clp
rounding_remainder_clp
created_at
```

### 13.7 Tabla `monthly_closures`

```text
id
period_id
status
total_gross_clp
total_payable_clp
total_advances_clp
total_remainder_clp
carried_remainder_clp
closed_by
closed_at
created_at
updated_at
```

### 13.8 Tabla `advance_requests`

```text
id
worker_id
period_id
amount_clp
reason
status_id
decision_reason
requested_at
cancelled_at
created_at
updated_at
```

`decision_reason` debe completarse tanto al aprobar como al rechazar la solicitud.

### 13.9 Tabla `payments`

```text
id
worker_id
period_id
gross_amount_clp
advance_discount_clp
adjustment_amount_clp
net_amount_clp
paid_amount_clp
status_id
paid_at
paid_by
created_at
updated_at
```

### 13.10 Tabla `audit_logs`

```text
id
user_id
module
action
entity_name
entity_id
old_values_json
new_values_json
ip_address
created_at
```

Nota: `audit_logs` existe para trazabilidad técnica, pero no debe existir una pantalla de auditoría dentro de la aplicación.

---

## 14. Endpoints API mínimos:

| Método | Endpoint | Descripción |
|---|---|---|
| POST | /api/auth/register | Registro público de trabajador |
| POST | /api/auth/login | Login regular de trabajador |
| POST | /api/auth/admin/login | Login administrativo |
| POST | /api/auth/logout | Cerrar sesión |
| POST | /api/auth/refresh | Renovar token |
| GET | /api/auth/me | Obtener usuario autenticado |
| POST | /api/auth/password/forgot | Solicitar recuperación |
| POST | /api/auth/password/reset | Restablecer contraseña |
| GET | /api/admin/dashboard/summary | Resumen dashboard administrador |
| GET | /api/admin/dashboard/current-period | KPIs periodo actual admin |
| GET | /api/admin/pending-users | Listar solicitudes de usuario pendientes |
| GET | /api/admin/pending-users/{id} | Ver solicitud de usuario pendiente |
| PATCH | /api/admin/pending-users/{id}/approve | Aprobar solicitud de usuario con razón |
| PATCH | /api/admin/pending-users/{id}/reject | Rechazar solicitud de usuario con razón |
| POST | /api/admin/pending-users/{id}/complete-worker | Completar ficha laboral de usuario aprobado |
| GET | /api/admin/workers | Listar trabajadores |
| POST | /api/admin/workers | Crear trabajador manualmente |
| GET | /api/admin/workers/{id} | Ver trabajador |
| PUT | /api/admin/workers/{id} | Editar trabajador |
| PATCH | /api/admin/workers/{id}/activate | Activar trabajador |
| PATCH | /api/admin/workers/{id}/deactivate | Desactivar trabajador |
| GET | /api/admin/workers/{id}/points | Historial de puntos |
| POST | /api/admin/workers/{id}/points | Crear vigencia de puntos |
| PUT | /api/admin/workers/{id}/points/{point_id} | Editar puntos no cerrados |
| GET | /api/admin/contracts | Listar tipos de contrato |
| GET | /api/admin/sections | Listar secciones |
| POST | /api/admin/sections | Crear sección |
| PUT | /api/admin/sections/{id} | Editar sección |
| GET | /api/admin/shifts | Listar turnos |
| POST | /api/admin/shifts | Registrar turno |
| POST | /api/admin/shifts/bulk | Carga masiva de turnos |
| GET | /api/admin/shifts/{id} | Ver turno |
| PUT | /api/admin/shifts/{id} | Editar turno |
| PATCH | /api/admin/shifts/{id}/void | Anular turno |
| GET | /api/admin/tips/daily | Listar propinas diarias |
| POST | /api/admin/tips/daily | Registrar propina diaria |
| GET | /api/admin/tips/daily/{date} | Ver propina diaria |
| PUT | /api/admin/tips/daily/{date} | Editar propina diaria |
| POST | /api/admin/tips/daily/{date}/calculate | Calcular reparto diario |
| POST | /api/admin/tips/daily/{date}/recalculate | Recalcular reparto diario |
| GET | /api/admin/periods | Listar periodos mensuales |
| POST | /api/admin/periods | Crear periodo mensual |
| GET | /api/admin/periods/{id}/preview | Previsualizar cierre |
| POST | /api/admin/periods/{id}/close | Cerrar periodo |
| POST | /api/admin/periods/{id}/reopen | Reabrir periodo con motivo |
| GET | /api/admin/payments | Listar pagos |
| POST | /api/admin/payments/prepare | Preparar pagos del periodo |
| PATCH | /api/admin/payments/{id}/mark-paid | Marcar pago como pagado |
| PATCH | /api/admin/payments/{id}/void | Anular pago |
| GET | /api/admin/advances | Listar solicitudes de anticipo |
| GET | /api/admin/advances/{id} | Ver solicitud de anticipo |
| PATCH | /api/admin/advances/{id}/approve | Aprobar anticipo con razón y descuento inmediato |
| PATCH | /api/admin/advances/{id}/reject | Rechazar anticipo con razón |
| GET | /api/admin/shift-claims | Listar reclamos |
| PATCH | /api/admin/shift-claims/{id}/resolve | Resolver reclamo con razón |
| GET | /api/admin/settings | Ver configuración |
| PUT | /api/admin/settings | Actualizar configuración |
| GET | /api/worker/dashboard | Dashboard trabajador |
| GET | /api/worker/current-period | Periodo actual del trabajador |
| GET | /api/worker/shifts | Mis turnos |
| GET | /api/worker/shifts/{id} | Detalle de mi turno |
| GET | /api/worker/payments | Mis pagos |
| GET | /api/worker/payments/pending | Mis pagos pendientes |
| GET | /api/worker/advances | Mis anticipos |
| POST | /api/worker/advances | Solicitar anticipo |
| PATCH | /api/worker/advances/{id}/cancel | Cancelar anticipo pendiente |
| GET | /api/worker/shift-claims | Mis reclamos |
| POST | /api/worker/shift-claims | Crear reclamo de turno |
| GET | /api/worker/profile | Ver perfil |
| PUT | /api/worker/profile | Editar datos personales permitidos |

---

## 15. Pantallas principales:

| N° | Pantalla |
|---|---|
| 1 | Login regular |
| 2 | Registro público de usuario |
| 3 | Recuperación de contraseña |
| 4 | Dashboard trabajador |
| 5 | Resumen de propina acumulada del periodo |
| 6 | Mis turnos registrados |
| 7 | Detalle de turno trabajador |
| 8 | Mis pagos pasados |
| 9 | Mis pagos pendientes |
| 10 | Mis solicitudes de anticipo |
| 11 | Nueva solicitud de anticipo |
| 12 | Detalle de solicitud de anticipo |
| 13 | Mis reclamos de turno |
| 14 | Nuevo reclamo de turno |
| 15 | Perfil de trabajador |
| 16 | Cambiar contraseña |
| 17 | Ruta /admin/login o acceso administrativo |
| 18 | Dashboard administrador /admin |
| 19 | Solicitudes de usuario pendientes |
| 20 | Detalle y decisión de solicitud de usuario |
| 21 | Trabajadores activos |
| 22 | Crear nuevo trabajador en página/sección independiente |
| 23 | Configuración de puntos |
| 24 | Tipos de contrato y secciones |
| 25 | Registro de turnos |
| 26 | Carga masiva de turnos |
| 27 | Registro de propina diaria |
| 28 | Cálculo diario de propinas |
| 29 | Cierre mensual |
| 30 | Gestión de pagos mensuales |
| 31 | Gestión de anticipos |
| 32 | Gestión de reclamos de turno |
| 33 | Configuración general del sistema |

Importante: no se incluyen pantallas de reportes ni auditoría, porque esas secciones se entregan como documentación del proyecto en `docs/` y no como módulos visibles del sistema.

---

## 16. Diseño visual e interfaz de usuario

### 16.1 Estilo general

El sistema debe tener una interfaz limpia, moderna y administrativa, orientada a claridad operativa.

Lineamientos visuales:

- Diseño responsivo con Bootstrap.
- Paleta principal sugerida: azul oscuro, celeste y gris claro.
- Color de éxito: verde para pagos realizados y aprobaciones.
- Color de advertencia: amarillo/naranjo para solicitudes de usuario pendientes, cierres incompletos y solicitudes pendientes.
- Color de error: rojo para rechazos, anulaciones y validaciones críticas.
- Tipografía sans-serif legible, por ejemplo Inter, Roboto o system-ui.
- Tarjetas KPI grandes para montos CLP.
- Tablas con filtros, búsqueda y paginación.
- Formularios con validaciones visibles bajo cada campo.
- Botones críticos con modal de confirmación.

### 16.2 Layout administrador

- Ruta base: `/admin`.
- Menú lateral fijo en escritorio.
- Menú colapsable en móvil.
- Encabezado con nombre del administrador, botón de salir y periodo activo.
- Dashboard con tarjetas KPI, bloque destacado de solicitudes de usuario pendientes y accesos rápidos.
- Secciones navegables desde la barra lateral: Dashboard, Solicitudes de usuario, Trabajadores, Crear nuevo trabajador, Turnos, Propinas diarias, Cierre y pagos, Anticipos y Reclamos.
- La creación de trabajador debe abrir una sección o página dedicada, por ejemplo `/admin/crear-trabajador`.
- La lista de trabajadores no debe mostrar un botón duplicado de creación si la acción ya está disponible en la barra lateral.
- Tablas administrativas densas, con filtros por fecha, trabajador, estado y periodo.

### 16.3 Layout trabajador

- Ruta base regular: `/dashboard` o `/`.
- Navegación lateral simple con secciones separadas.
- Primera tarjeta destacada: propina acumulada disponible del periodo.
- Accesos visibles a pagos, anticipos, turnos y perfil.
- Menor densidad de datos que el administrador.
- Mensajes explicativos sobre cómo se calculan propinas y anticipos.

### 16.4 Responsividad

```text
Móvil:      320px a 767px
Tablet:     768px a 1023px
Escritorio: 1024px o superior
```

Reglas:

- En móvil, tablas administrativas pueden transformarse en tarjetas.
- El dashboard trabajador debe priorizar la propina acumulada.
- Las acciones críticas deben ser fáciles de pulsar en pantalla táctil.
- Los formularios deben usar una columna en móvil y dos columnas en escritorio.
- Los montos CLP deben estar alineados y formateados consistentemente.

---

## 17. Reglas de negocio críticas:

| Código | Regla de negocio |
|---|---|
| RN-01 | La moneda única del sistema es CLP y no se permite configurar otra moneda en esta versión. |
| RN-02 | Todo usuario trabajador debe registrarse desde la pantalla pública de creación de cuenta. |
| RN-03 | Un usuario registrado por sí mismo queda en estado pendiente hasta decisión del administrador. |
| RN-04 | Solo el administrador puede aprobar solicitudes de usuario y dejarlas pendientes de completar ficha laboral. |
| RN-05 | Solo existe un usuario administrador predeterminado en los datos iniciales del sistema. |
| RN-06 | El administrador accede únicamente a través de la ruta /admin después de autenticarse. |
| RN-07 | Los trabajadores acceden al dashboard regular después de iniciar sesión, sin usar una ruta administrativa. |
| RN-08 | El dashboard del administrador y el dashboard del trabajador son completamente distintos. |
| RN-09 | El trabajador solo puede consultar información asociada a su propia cuenta y trabajador vinculado. |
| RN-10 | El administrador puede administrar usuarios, trabajadores, turnos, propinas, anticipos, cierres, pagos y configuraciones. |
| RN-11 | El administrador puede configurar puntos, tipo de contrato, sección, cargo y estado laboral de cada trabajador. |
| RN-12 | El RUN chileno es obligatorio para trabajadores aprobados. |
| RN-13 | El código interno del trabajador se genera automáticamente desde el RUN normalizado. |
| RN-14 | El código interno no debe ser ingresado manualmente por el administrador. |
| RN-15 | Un trabajador activo debe tener tipo de contrato definido antes de participar en cálculos. |
| RN-16 | Los tipos de contrato mínimos son fulltime y parttime. |
| RN-17 | Un trabajador fulltime participa en todos los días válidos del periodo, salvo ausencias o exclusiones registradas. |
| RN-18 | Un trabajador parttime participa solo en los días donde tenga turno trabajado registrado y validado. |
| RN-19 | Un trabajador sin puntos vigentes no puede recibir distribución de propinas. |
| RN-20 | La cantidad de puntos debe estar vigente por fecha para permitir cambios históricos. |
| RN-21 | Los cambios de puntos no deben alterar cierres mensuales ya confirmados. |
| RN-22 | La propina diaria corresponde a un fondo común único del día. |
| RN-23 | La propina diaria solo puede ser registrada o modificada por el administrador. |
| RN-24 | No puede existir más de un fondo de propina diario activo para la misma fecha y local. |
| RN-25 | El reparto diario se calcula en proporción a los puntos participantes del día. |
| RN-25B | Cada propina diaria calculada debe guardar el valor del punto utilizado ese día. |
| RN-26 | Para el reparto diario se consideran únicamente trabajadores elegibles para esa fecha. |
| RN-27 | Si un día no tiene trabajadores elegibles, el sistema no permite cerrar el cálculo diario. |
| RN-28 | Si la propina diaria es cero, el sistema permite registrar el día, pero el reparto será cero. |
| RN-29 | El monto bruto calculado puede usar decimales internamente para mantener precisión. |
| RN-30 | Todo monto pagable al trabajador debe redondearse hacia abajo al múltiplo de 10 CLP más cercano. |
| RN-31 | El redondeo hacia abajo nunca puede generar un pago superior al saldo calculado. |
| RN-32 | La diferencia causada por redondeo se acumula como sobrante del periodo. |
| RN-33 | El sobrante mensual se redistribuye equitativamente en el último día trabajado del periodo. |
| RN-34 | Si luego de redistribuir el sobrante mensual vuelve a quedar sobrante, se arrastra al mes siguiente. |
| RN-35 | El sobrante arrastrado debe quedar asociado al periodo de origen y al periodo destino. |
| RN-36 | El cierre mensual consolida propinas diarias, anticipos aprobados, ajustes autorizados, sobrantes y pagos. |
| RN-37 | No se puede cerrar un periodo mensual si existen días pendientes de cálculo obligatorio. |
| RN-38 | No se puede cerrar un periodo mensual si existen anticipos aprobados sin aplicar al saldo. |
| RN-39 | No se puede registrar pago mensual si el periodo no está cerrado. |
| RN-40 | No se puede modificar una propina diaria incluida en un cierre mensual confirmado. |
| RN-41 | No se puede modificar un turno incluido en un cierre mensual confirmado. |
| RN-42 | El trabajador puede solicitar anticipos solo si está activo. |
| RN-43 | El trabajador no puede aprobar su propia solicitud de anticipo. |
| RN-44 | Solo el administrador puede aprobar o rechazar anticipos. |
| RN-45 | Un anticipo aprobado se descuenta inmediatamente del saldo disponible del trabajador y del pago mensual del periodo correspondiente. |
| RN-46 | Un anticipo rechazado no modifica el saldo del trabajador. |
| RN-47 | Un anticipo no puede superar la propina acumulada disponible del trabajador, salvo permiso administrativo explícito configurado. |
| RN-48 | Todas las solicitudes de anticipo deben tener estado: pendiente, aprobada, rechazada, cancelada o aplicada. |
| RN-49 | El trabajador puede cancelar una solicitud solo mientras esté pendiente. |
| RN-50 | Los pagos pueden estar en estado pendiente, preparado, pagado, anulado o corregido. |
| RN-51 | Un pago pagado no puede editarse directamente; debe corregirse mediante ajuste o anulación autorizada. |
| RN-52 | Todo pago debe registrar fecha, monto CLP, trabajador, periodo y responsable. |
| RN-53 | El dashboard del trabajador debe mostrar al inicio la propina acumulada disponible del periodo actual. |
| RN-54 | La propina acumulada disponible del dashboard trabajador debe descontar anticipos aprobados aplicables. |
| RN-55 | La vista inicial del trabajador no debe duplicar tarjetas de anticipos aprobados ni saldo estimado; esos datos se consultan en secciones específicas. |
| RN-56 | Los trabajadores pueden verificar sus turnos registrados, pero no pueden editarlos directamente. |
| RN-57 | Los trabajadores pueden enviar reclamos de turno cuando detecten errores. |
| RN-58 | El administrador puede resolver reclamos de turno aceptándolos o rechazándolos. |
| RN-59 | Las acciones críticas deben registrarse internamente en auditoría técnica, aunque no exista pantalla de auditoría en la aplicación. |
| RN-60 | Los reportes y auditorías del proyecto se entregan como documentos técnicos en la carpeta docs, no como módulos visibles en la interfaz. |
| RN-61 | La eliminación física de trabajadores, pagos, turnos, propinas y cierres no está permitida; se usa desactivación o anulación lógica. |
| RN-62 | Las contraseñas siempre deben almacenarse con hash seguro y nunca como texto plano. |
| RN-63 | Toda ruta protegida debe validar token JWT y permisos del usuario autenticado. |
| RN-64 | Las operaciones administrativas no deben estar disponibles para usuarios trabajadores aunque conozcan la URL. |
| RN-65 | La creación pública de usuario debe mostrar el mensaje `peticion creada, usuario pendiente de confirmacion`. |
| RN-66 | El login no debe mostrar selector de tipo de usuario; el rol esperado queda determinado por la ruta `/admin` o `/dashboard`. |
| RN-67 | La aprobación y el rechazo de solicitudes de usuario requieren razón obligatoria. |
| RN-68 | Una solicitud de usuario aprobada no crea trabajador activo hasta completar RUN, contrato, sección, cargo y puntos. |
| RN-69 | La aprobación y el rechazo de anticipos requieren razón obligatoria. |
| RN-70 | La resolución de reclamos requiere razón obligatoria tanto si se acepta como si se rechaza. |
| RN-71 | El dashboard administrativo debe mostrar solicitudes de usuario pendientes en una tarjeta destacada. |
| RN-72 | Los dashboards de administrador y trabajador deben separar sus funcionalidades mediante barra lateral. |

---

## 18. Validaciones y restricciones CHECK:

Estas validaciones deben implementarse combinando frontend, backend y base de datos. Las reglas de integridad crítica deben reforzarse en backend y base de datos, no solo en frontend.

| N° | Validación o restricción |
|---|---|
| 1 | El email de registro es obligatorio. |
| 2 | El email debe tener formato válido. |
| 3 | El email debe ser único entre usuarios activos y pendientes. |
| 4 | El nombre es obligatorio. |
| 5 | El nombre debe tener entre 2 y 80 caracteres. |
| 6 | El apellido es obligatorio. |
| 7 | El apellido debe tener entre 2 y 80 caracteres. |
| 8 | El teléfono es obligatorio en registro de trabajador. |
| 9 | El teléfono debe aceptar formato chileno +56 o 9 dígitos nacionales normalizados. |
| 10 | La contraseña es obligatoria. |
| 11 | La contraseña debe tener al menos 8 caracteres. |
| 12 | La contraseña debe incluir al menos una letra mayúscula. |
| 13 | La contraseña debe incluir al menos una letra minúscula. |
| 14 | La contraseña debe incluir al menos un número. |
| 15 | La contraseña debe incluir al menos un símbolo. |
| 16 | La confirmación de contraseña debe coincidir. |
| 17 | No se permite registrar usuario con estado inicial activo desde formulario público. |
| 18 | El estado inicial de registro público debe ser pendiente_aprobacion. |
| 18B | El registro público debe devolver el mensaje `peticion creada, usuario pendiente de confirmacion`. |
| 19 | El RUN es obligatorio al completar ficha de trabajador. |
| 20 | El RUN debe cumplir formato chileno válido. |
| 21 | El dígito verificador del RUN debe ser correcto. |
| 22 | El RUN debe ser único. |
| 23 | El código interno generado desde RUN debe ser único. |
| 24 | El código interno no puede contener puntos, guion ni espacios. |
| 25 | El tipo de contrato es obligatorio para trabajador activo. |
| 26 | El tipo de contrato solo puede ser fulltime o parttime. |
| 27 | La cantidad de puntos es obligatoria para trabajador activo. |
| 28 | La cantidad de puntos debe ser mayor que 5. |
| 29 | La cantidad de puntos no puede superar 20. |
| 30 | Los puntos deben ser numeros enteros. |
| 31 | La fecha de vigencia de puntos es obligatoria. |
| 32 | No se permiten dos configuraciones de puntos vigentes para el mismo trabajador en la misma fecha. |
| 33 | El cargo del trabajador no puede superar 100 caracteres. |
| 34 | La sección del trabajador debe existir y estar activa. |
| 35 | No se puede activar trabajador sin RUN válido. |
| 36 | No se puede activar trabajador sin tipo de contrato. |
| 37 | No se puede activar trabajador sin puntos vigentes. |
| 38 | No se puede aprobar solicitud de usuario que no esté pendiente. |
| 39 | No se puede rechazar solicitud de usuario que no esté pendiente. |
| 39B | Aprobar o rechazar una solicitud de usuario requiere razón no vacía. |
| 39C | No se puede crear trabajador activo desde una solicitud aprobada sin completar RUN, contrato, sección y puntos. |
| 40 | La fecha de turno es obligatoria. |
| 41 | La fecha de turno no puede ser anterior a la fecha mínima configurada del sistema. |
| 42 | La fecha de turno no puede estar dentro de un periodo cerrado. |
| 43 | La hora de inicio del turno es obligatoria si se registran horas. |
| 44 | La hora de término debe ser posterior a la hora de inicio. |
| 45 | La duración de turno no puede ser negativa. |
| 46 | La duración de turno no puede superar 24 horas. |
| 47 | No se permite turno duplicado para el mismo trabajador, fecha y tipo de turno. |
| 48 | El estado de turno solo puede ser programado, trabajado, ausente, corregido o anulado. |
| 49 | Un turno anulado debe tener motivo. |
| 50 | Un trabajador inactivo no puede recibir nuevos turnos. |
| 51 | La fecha de propina diaria es obligatoria. |
| 52 | La propina diaria debe estar expresada en CLP. |
| 53 | El monto de propina diaria no puede ser negativo. |
| 54 | El monto de propina diaria no puede superar el máximo operativo configurado. |
| 55 | El monto de propina diaria debe ser entero en CLP. |
| 56 | No se permite propina diaria duplicada para la misma fecha. |
| 57 | No se puede editar propina diaria cerrada. |
| 58 | No se puede calcular día sin monto de propina registrado. |
| 59 | No se puede calcular día sin trabajadores elegibles cuando el monto es mayor a cero. |
| 60 | El total de puntos participantes debe ser mayor que 0. |
| 60B | El valor del punto diario debe quedar registrado junto a la propina diaria calculada. |
| 61 | El porcentaje de participación calculado debe estar entre 0 y 100. |
| 62 | La suma de porcentajes del día debe ser 100% antes de redondeos. |
| 63 | El monto asignado bruto no puede ser negativo. |
| 64 | El monto pagable redondeado debe ser múltiplo de 10. |
| 65 | El monto pagable redondeado no puede superar el monto bruto. |
| 66 | El sobrante por redondeo no puede ser negativo. |
| 67 | El sobrante acumulado debe ser menor que 10 por cada operación individual de redondeo. |
| 68 | El periodo mensual debe tener mes entre 1 y 12. |
| 69 | El año del periodo mensual debe ser igual o mayor a 2020. |
| 70 | No se permiten periodos duplicados para el mismo mes y año. |
| 71 | No se puede cerrar periodo con días pendientes obligatorios. |
| 72 | No se puede cerrar periodo con cálculos diarios inconsistentes. |
| 73 | No se puede reabrir periodo sin motivo administrativo. |
| 74 | La solicitud de anticipo debe tener monto mayor que 0. |
| 75 | La solicitud de anticipo debe estar en CLP. |
| 76 | La solicitud de anticipo debe tener motivo con máximo 500 caracteres. |
| 77 | El monto de anticipo debe ser múltiplo de 10 CLP. |
| 78 | El monto de anticipo no puede superar saldo disponible si la regla de sobregiro está desactivada. |
| 79 | Un trabajador inactivo no puede solicitar anticipo. |
| 80 | No se puede aprobar solicitud que no esté pendiente. |
| 81 | No se puede rechazar solicitud que no esté pendiente. |
| 82 | Una aprobación de anticipo requiere usuario administrador. |
| 83 | Una aprobación de anticipo requiere fecha de decisión. |
| 84 | Toda aprobación o rechazo de anticipo requiere razón. |
| 84B | Un anticipo aprobado debe descontarse inmediatamente del saldo disponible del periodo del trabajador. |
| 85 | La fecha de pago es obligatoria al marcar pago como pagado. |
| 86 | La fecha de pago no puede estar en el futuro. |
| 87 | El monto pagado debe ser mayor o igual a 0. |
| 88 | El monto pagado debe ser múltiplo de 10 CLP. |
| 89 | El monto pagado no puede superar saldo neto pendiente salvo ajuste autorizado. |
| 90 | No se puede pagar trabajador inactivo sin cierre pendiente asociado. |
| 91 | No se puede registrar dos pagos pagados para el mismo trabajador y periodo sin anular el anterior. |
| 92 | La observación de anulación de pago es obligatoria. |
| 93 | El reclamo de turno debe indicar fecha reclamada. |
| 94 | El reclamo de turno debe tener descripción entre 10 y 1000 caracteres. |
| 95 | No se puede crear reclamo sobre periodo cerrado salvo permiso especial. |
| 96 | Un reclamo resuelto no puede editarse. |
| 96B | Resolver un reclamo aceptado o rechazado requiere razón. |
| 97 | Las rutas /admin requieren rol administrador. |
| 98 | Las rutas regulares de trabajador requieren usuario aprobado y trabajador activo. |
| 99 | Un trabajador no puede consultar datos de otro trabajador. |
| 100 | Los parámetros de configuración solo pueden modificarse por administrador. |
| 101 | El valor máximo operativo de propina diaria debe ser mayor que 0. |
| 102 | El valor máximo operativo de anticipo debe ser mayor que 0. |
| 103 | Los filtros de fecha deben tener fecha desde menor o igual a fecha hasta. |
| 104 | La paginación debe limitar tamaño de página a un máximo configurado. |
| 105 | Los archivos/documentos generados en docs no deben exponer contraseñas reales. |
| 106 | El login público de trabajador no debe permitir cambiar visualmente a rol administrador. |
| 107 | El login administrativo solo debe mostrarse entrando a `/admin`. |
| 108 | La barra lateral debe permitir acceder a solicitudes de usuario en administración. |
| 109 | El dashboard inicial del administrador debe mostrar contador de solicitudes de usuario pendientes. |
| 110 | La lista de trabajadores no debe duplicar la acción de crear trabajador cuando existe sección dedicada en barra lateral. |

---

## 19. Requisitos no funcionales

## RNF-01 Seguridad básica

El sistema debe proteger rutas con JWT, almacenar contraseñas con hash seguro y aplicar permisos por rol.

## RNF-02 Separación por rol

La experiencia visual, navegación y permisos del administrador y trabajador deben estar claramente separados.

## RNF-03 Integridad de datos

La base de datos debe usar claves primarias, claves foráneas, índices, restricciones únicas y checks donde corresponda.

## RNF-04 Trazabilidad técnica

Las acciones críticas deben registrarse internamente en `audit_logs`, aunque no exista una pantalla de auditoría.

## RNF-05 Usabilidad

La interfaz debe ser clara para trabajadores y administradores, evitando sobrecargar el dashboard trabajador.

## RNF-06 Responsividad

El sistema debe funcionar en escritorio, tablet y móvil.

## RNF-07 Rendimiento

Las listas deben usar paginación, filtros e índices.

## RNF-08 Mantenibilidad

La lógica de cálculo de propinas debe estar separada en servicios reutilizables y testeables.

## RNF-09 Precisión monetaria

Los cálculos internos deben evitar errores de punto flotante usando enteros en centavos equivalentes o Decimal.

## RNF-10 Documentación

Debe incluir README, endpoints, modelo de datos, pruebas, datos iniciales y documentos técnicos de reportes/auditoría en `docs/`.

---

## 20. Diseño y plan de pruebas

### 20.1 Tipos de pruebas

- Pruebas unitarias de servicios de negocio.
- Pruebas unitarias de validadores.
- Pruebas de integración de base de datos.
- Pruebas de endpoints API.
- Pruebas de autenticación y permisos.
- Pruebas de solicitudes públicas de usuario y completado de ficha laboral.
- Pruebas de cálculo de propinas.
- Pruebas de redondeo y sobrantes.
- Pruebas de cierre mensual.
- Pruebas de anticipos.
- Pruebas de pagos.
- Pruebas frontend de formularios principales.
- Pruebas end-to-end de flujos críticos.

### 20.2 Cobertura esperada

La meta de cobertura automatizada es 100% sobre:

- Servicios de cálculo de propinas.
- Servicios de redondeo y sobrantes.
- Validadores de RUN, montos, fechas y estados.
- Servicios de solicitudes de usuario, anticipos y reclamos.
- Servicios de cierre mensual.
- Servicios de pagos.
- Permisos y guards de rutas críticas.

Para frontend, la cobertura debe incluir las vistas y componentes principales de login por ruta, registro, dashboard trabajador con barra lateral, dashboard admin con barra lateral, solicitudes de usuario, creación independiente de trabajador, turnos, propinas, anticipos y pagos.

### 20.3 Casos funcionales y casos límite

| Código | Caso de prueba | Datos / condición | Resultado esperado |
|---|---|---|---|
| CP-01 | Registro público válido | Nombre, apellido, email único, teléfono y contraseña fuerte. | Usuario queda pendiente de aprobación y se muestra `peticion creada, usuario pendiente de confirmacion`. |
| CP-02 | Registro con email duplicado | Email ya existente. | Sistema rechaza registro. |
| CP-03 | Registro con contraseña débil | Contraseña sin número ni símbolo. | Sistema muestra validación. |
| CP-04 | Login trabajador pendiente | Usuario registrado no aprobado. | Sistema bloquea acceso. |
| CP-05 | Login admin en ruta regular | Credenciales admin en login normal. | Sistema redirige o bloquea según política y exige /admin. |
| CP-06 | Login trabajador en /admin | Trabajador intenta entrar a /admin. | Sistema devuelve autorización insuficiente. |
| CP-07 | Aprobar solicitud de usuario válida | Solicitud pendiente y razón informada. | Usuario queda aprobado pendiente de completar ficha laboral. |
| CP-07A | Completar ficha laboral aprobada | RUN válido, contrato, sección y puntos. | Trabajador queda activo. |
| CP-07B | Rechazar solicitud sin razón | Solicitud pendiente sin razón. | Sistema rechaza operación. |
| CP-08 | RUN inválido | RUN con DV incorrecto. | Sistema rechaza activación. |
| CP-09 | RUN duplicado | RUN ya usado por otro trabajador. | Sistema rechaza operación. |
| CP-10 | Puntos negativos | Puntos = -1. | Sistema rechaza valor. |
| CP-11 | Puntos cero | Puntos = 0. | Sistema no permite activar trabajador para cálculo. |
| CP-12 | Puntos extremos | Puntos = 1000000. | Sistema rechaza por rango máximo. |
| CP-13 | Turno duplicado | Mismo trabajador, fecha y tipo. | Sistema rechaza duplicidad. |
| CP-14 | Turno con hora final menor | Inicio 18:00, término 10:00 sin regla nocturna. | Sistema rechaza rango. |
| CP-15 | Turno en periodo cerrado | Intentar modificar turno de mes cerrado. | Sistema bloquea operación. |
| CP-16 | Propina diaria válida | Monto 150000 CLP. | Fondo diario queda registrado. |
| CP-17 | Propina negativa | Monto -1000. | Sistema rechaza valor negativo. |
| CP-18 | Propina cero | Monto 0. | Sistema permite día con reparto cero. |
| CP-19 | Propina extrema | Monto superior al máximo configurado. | Sistema rechaza por rango. |
| CP-20 | Propina con decimales | Monto 150000.50. | Sistema rechaza porque CLP operativo es entero. |
| CP-21 | Cálculo sin trabajadores elegibles | Día con monto mayor a cero y sin turnos/puntos. | Sistema no calcula. |
| CP-22 | Cálculo fulltime | Fulltime con puntos vigentes sin turno registrado. | Participa del cálculo diario. |
| CP-23 | Cálculo parttime sin turno | Parttime sin turno trabajado. | No participa del cálculo diario. |
| CP-24 | Cálculo parttime con turno | Parttime con turno trabajado. | Participa del cálculo diario. |
| CP-25 | Redondeo a múltiplo de 10 | Monto bruto 1234 CLP. | Monto pagable 1230 CLP y sobrante 4. |
| CP-25A | Valor del punto diario | Propina calculada con puntos elegibles. | Propina diaria conserva `point_value_clp` del día. |
| CP-26 | Sobrante mensual | Sobrantes acumulados del periodo. | Se redistribuyen en último día trabajado. |
| CP-27 | Sobrante persistente | Redistribución genera nuevo sobrante. | Sobrante se arrastra al mes siguiente. |
| CP-28 | Anticipo válido | Monto menor al saldo disponible y múltiplo de 10. | Solicitud queda pendiente. |
| CP-29 | Anticipo negativo | Monto -5000. | Sistema rechaza. |
| CP-30 | Anticipo no múltiplo de 10 | Monto 10005. | Sistema rechaza. |
| CP-31 | Anticipo superior al saldo | Monto mayor al saldo disponible. | Sistema rechaza si sobregiro desactivado. |
| CP-32 | Aprobar anticipo no pendiente | Solicitud rechazada previamente. | Sistema bloquea cambio. |
| CP-32A | Aprobar anticipo con razón | Solicitud pendiente, saldo disponible y razón. | Sistema aprueba y descuenta inmediatamente del saldo disponible. |
| CP-32B | Decidir anticipo sin razón | Solicitud pendiente sin razón. | Sistema rechaza operación. |
| CP-33 | Cerrar periodo con día pendiente | Existe día obligatorio sin cálculo. | Sistema bloquea cierre. |
| CP-34 | Cerrar periodo correcto | Todos los días calculados y anticipos aplicados. | Periodo queda cerrado. |
| CP-35 | Pago antes de cierre | Periodo abierto. | Sistema bloquea pago. |
| CP-36 | Pago válido | Saldo neto múltiplo de 10. | Pago queda pagado. |
| CP-37 | Pago con fecha futura | Fecha posterior a hoy. | Sistema rechaza. |
| CP-38 | Trabajador intenta ver otro perfil | ID de otro trabajador. | Sistema devuelve 403. |
| CP-39 | Reclamo con texto corto | Descripción menor a 10 caracteres. | Sistema rechaza. |
| CP-39A | Resolver reclamo sin razón | Reclamo pendiente sin razón administrativa. | Sistema rechaza operación. |
| CP-39B | Resolver reclamo con razón | Reclamo pendiente con razón y decisión. | Sistema guarda estado y razón. |
| CP-40 | Logout | Usuario autenticado presiona salir. | Sesión se cierra y rutas quedan protegidas. |
| CP-41 | Dashboard admin muestra solicitudes | Existen solicitudes pendientes. | Tarjeta inicial muestra contador y acceso a sección. |
| CP-42 | Login sin selector de rol | Usuario entra a `/admin` o `/dashboard`. | Se muestra login correspondiente sin cambiar tipo de usuario manualmente. |

---

## 21. Checklist de validación de completitud del producto

```text
[ ] El backend FastAPI inicia sin errores.
[ ] El frontend React + Bootstrap inicia sin errores.
[ ] La base de datos MySQL/MariaDB conecta correctamente.
[ ] Las migraciones crean todas las tablas requeridas.
[ ] Existe usuario administrador inicial único.
[ ] El administrador puede iniciar sesión desde /admin.
[ ] Un trabajador no puede acceder a /admin.
[ ] Existe pantalla pública de registro de usuario.
[ ] El registro público deja usuarios pendientes de aprobación.
[ ] El registro público muestra `peticion creada, usuario pendiente de confirmacion`.
[ ] El administrador puede aprobar solicitudes de usuario pendientes con razón.
[ ] El administrador puede rechazar solicitudes de usuario pendientes con razón.
[ ] El administrador puede completar ficha laboral de usuario aprobado.
[ ] El dashboard administrativo muestra solicitudes de usuario pendientes.
[ ] El sistema valida RUN chileno.
[ ] El sistema genera código interno desde RUN.
[ ] El administrador puede configurar puntos.
[ ] El administrador puede configurar tipo de contrato.
[ ] El administrador puede registrar turnos.
[ ] El administrador puede registrar propina diaria en CLP.
[ ] La propina diaria registra el valor del punto calculado del día.
[ ] El sistema calcula reparto diario por puntos.
[ ] El sistema diferencia fulltime y parttime.
[ ] El sistema redondea pagos hacia abajo a múltiplos de 10 CLP.
[ ] El sistema acumula sobrantes por redondeo.
[ ] El sistema redistribuye sobrantes al final del mes.
[ ] El sistema arrastra sobrante al mes siguiente si corresponde.
[ ] El trabajador ve propina acumulada al inicio de su dashboard.
[ ] La propina acumulada del trabajador descuenta anticipos aprobados del periodo.
[ ] El trabajador ve pagos pasados.
[ ] El trabajador ve pagos pendientes.
[ ] El trabajador puede solicitar anticipos.
[ ] El administrador puede aprobar anticipos con razón y descuento inmediato.
[ ] El administrador puede rechazar anticipos con razón.
[ ] El trabajador puede verificar turnos registrados.
[ ] El trabajador puede crear reclamo de turno.
[ ] El administrador puede resolver reclamos con razón.
[ ] El administrador puede cerrar periodo mensual.
[ ] El administrador puede preparar pagos.
[ ] El administrador puede marcar pagos como pagados.
[ ] Las contraseñas se guardan con hash seguro.
[ ] Todas las rutas protegidas validan JWT.
[ ] Las operaciones administrativas validan rol admin.
[ ] El login no muestra selector de tipo de usuario.
[ ] Admin y trabajador tienen barras laterales con secciones separadas.
[ ] Crear nuevo trabajador existe como sección independiente.
[ ] No existen pantallas de reportes dentro de la aplicación.
[ ] No existen pantallas de auditoría dentro de la aplicación.
[ ] Los documentos técnicos de reportes están en docs/.
[ ] Los documentos técnicos de auditoría están en docs/.
[ ] La interfaz es responsiva en móvil.
[ ] La interfaz es responsiva en tablet.
[ ] La interfaz es responsiva en escritorio.
[ ] Las pruebas unitarias pasan correctamente.
[ ] Las pruebas de integración pasan correctamente.
[ ] Las pruebas end-to-end críticas pasan correctamente.
[ ] La cobertura definida alcanza 100% en lógica crítica.
[ ] El README explica instalación y ejecución.
```

---

## 22. Datos iniciales de prueba

### 22.1 Administrador único predeterminado

Estas credenciales son solo para ambiente de desarrollo o pruebas. En producción deben cambiarse inmediatamente.

```text
Nombre: Administrador Sistema
Email: admin@propina360.local
Contraseña: Admin-123!
Rol: administrador
Ruta de acceso: /admin
Estado: activo
```

Reglas:

- Debe existir un único administrador inicial.
- No debe permitirse crear administradores desde el registro público.
- Las credenciales deben cargarse mediante seed inicial.
- La contraseña debe almacenarse hasheada en base de datos.

### 22.2 Trabajadores ficticios de prueba

| Nombre | Apellido | Email | Teléfono | RUN | Código interno | Contrato | Puntos | Sección |
|---|---|---|---|---|---|---|---|---|
| Ana | Muñoz | ana.munoz@test.local | +56911111111 | 11.111.111-1 | TRAB-11111111 | fulltime | 10 | Cocina |
| Bruno | Paredes | bruno.paredes@test.local | +56922222222 | 12.345.678-5 | TRAB-12345678 | parttime | 7 | Barra |
| Camila | Rojas | camila.rojas@test.local | +56933333333 | 14.000.000-0 | TRAB-14000000 | fulltime | 12 | Salón |
| Diego | Soto | diego.soto@test.local | +56944444444 | 17.000.000-5 | TRAB-17000000 | parttime | 6 | Salón |
| Elisa | Vargas | elisa.vargas@test.local | +56955555555 | 19.000.000-1 | TRAB-19000000 | fulltime | 9 | Caja |

Contraseña inicial sugerida para todos los trabajadores de prueba:

```text
Worker-123!
```

Estos trabajadores deben cargarse como usuarios aprobados y trabajadores activos para facilitar pruebas de turnos, propinas, anticipos, cierres y pagos.

---

## 23. Estructura sugerida del backend

```text
backend/
  app/
    main.py
    config.py
    database.py
    auth/
    users/
    admin/
    workers/
    shifts/
    tips/
    periods/
    advances/
    payments/
    claims/
    settings/
    audit_internal/
    shared/
  migrations/
  tests/
  requirements.txt
  README.md
```

Reglas:

- Cada módulo debe tener rutas, modelos, esquemas y servicios.
- La lógica de cálculo de propinas no debe estar directamente en endpoints.
- Las operaciones críticas deben usar transacciones.
- Los cálculos monetarios deben usar `Decimal` o enteros seguros.
- Las pruebas deben cubrir servicios críticos al 100%.

---

## 24. Estructura sugerida del frontend

```text
frontend/
  src/
    api/
    auth/
    components/
    layouts/
      AdminLayout.jsx
      WorkerLayout.jsx
      PublicLayout.jsx
    pages/
      public/
        Login.jsx
        Register.jsx
        ForgotPassword.jsx
      admin/
        AdminDashboard.jsx
        PendingUsers.jsx
        UserRequestDecision.jsx
        Workers.jsx
        CreateWorker.jsx
        WorkerForm.jsx
        Shifts.jsx
        DailyTips.jsx
        DailyCalculation.jsx
        MonthlyClosure.jsx
        Payments.jsx
        Advances.jsx
        ShiftClaims.jsx
        Settings.jsx
      worker/
        WorkerDashboard.jsx
        MyShifts.jsx
        MyPayments.jsx
        MyAdvances.jsx
        NewAdvance.jsx
        MyClaims.jsx
        Profile.jsx
    routes/
    hooks/
    utils/
    styles/
  public/
  package.json
  README.md
```

Reglas:

- Separar rutas públicas, administrativas y de trabajador.
- Proteger `/admin` con guard de rol administrador.
- Proteger dashboard trabajador con usuario aprobado y trabajador activo.
- Usar componentes visuales reutilizables sin mezclar permisos.
- Validar formularios antes de enviar al backend.
- Manejar estados de carga, error y éxito.

---

## 25. Documentación del proyecto

Los reportes y auditorías no deben aparecer como secciones dentro de la aplicación. Deben existir como documentos técnicos del proyecto.

Estructura sugerida:

```text
docs/
  especificacion_funcional.md
  modelo_datos.md
  endpoints_api.md
  plan_pruebas.md
  matriz_validaciones.md
  documento_reportes.md
  documento_auditoria_tecnica.md
  guia_instalacion.md
  guia_usuario_admin.md
  guia_usuario_trabajador.md
```

### 25.1 Documento de reportes

Debe describir qué información podría extraerse del sistema para evaluación, por ejemplo:

- Propina diaria por fecha.
- Distribución diaria por trabajador.
- Cierre mensual por trabajador.
- Anticipos por periodo.
- Pagos realizados.
- Reclamos de turno.

Estos reportes son documentación o consultas técnicas, no pantallas del sistema.

### 25.2 Documento de auditoría técnica

Debe describir qué acciones se registran internamente:

- Login y logout.
- Aprobación de usuarios.
- Cambios de puntos.
- Cambios de contrato.
- Registro o edición de turnos.
- Registro o edición de propinas.
- Cálculos diarios.
- Cierres mensuales.
- Aprobación o rechazo de anticipos.
- Registro de pagos.
- Anulaciones o reaperturas.

La auditoría existe en base de datos y documentación técnica, no como pantalla de consulta en la aplicación.

---

## 26. Criterios de aceptación

El sistema se considera terminado cuando cumple lo siguiente:

- Permite registro público de usuarios trabajadores.
- Muestra mensaje de petición creada y usuario pendiente de confirmación después del registro público.
- Permite aprobación y rechazo administrativo de solicitudes de usuario con razón obligatoria.
- Permite completar ficha laboral después de aprobar la solicitud de usuario.
- Permite login diferenciado para administrador y trabajadores.
- No muestra selector visible de tipo de usuario en el login.
- Protege ruta `/admin` para administrador.
- Muestra dashboard administrativo exclusivo.
- Muestra solicitudes de usuario pendientes en el dashboard administrativo.
- Muestra dashboard trabajador exclusivo.
- Ambos dashboards organizan sus secciones mediante barra lateral.
- El dashboard trabajador muestra la propina acumulada disponible del periodo al inicio.
- Permite administrar trabajadores, RUN, código interno, contrato, puntos y sección.
- La creación de nuevo trabajador está separada como sección administrativa independiente.
- Genera código interno derivado del RUN.
- Permite registrar turnos.
- Permite registrar propina diaria en CLP.
- Registra el valor del punto calculado en cada propina diaria.
- Calcula propina por puntos y elegibilidad fulltime/parttime.
- Redondea pagos hacia abajo a múltiplos de 10 CLP.
- Acumula y redistribuye sobrantes según regla mensual.
- Permite solicitar, aprobar, rechazar y cancelar anticipos.
- Al aprobar un anticipo, descuenta inmediatamente el monto del saldo disponible del trabajador.
- Aprobar o rechazar anticipos requiere razón.
- Permite cerrar periodos mensuales.
- Permite registrar pagos mensuales.
- Permite consultar pagos pasados y pendientes por trabajador.
- Permite verificar turnos personales.
- Permite crear y resolver reclamos de turno con razón administrativa.
- No contiene pantallas visibles de reportes ni auditoría.
- Incluye documentos técnicos de reportes y auditoría en `docs/`.
- Incluye pruebas automatizadas para lógica crítica.
- Incluye checklist de completitud.
- Incluye datos iniciales de prueba.

---

## 27. Definición final del producto mínimo viable

El producto mínimo viable debe ser una aplicación web llamada **Propina360**, desarrollada con **FastAPI, React, Bootstrap y MySQL/MariaDB**, que permita gestionar integralmente el registro, cálculo, anticipos, cierres y pagos de propinas en CLP.

Debe incluir creación pública de usuarios con solicitud administrativa, aprobación o rechazo con razón, completado posterior de ficha laboral, dashboards separados con navegación lateral, administración de trabajadores, creación independiente de nuevo trabajador, turnos, propinas diarias con registro de valor del punto, reglas de reparto por puntos, diferenciación fulltime/parttime, cálculo mensual, redondeo pagable a múltiplos de 10 pesos, manejo de sobrantes, solicitudes de anticipo con decisión razonada y descuento inmediato al aprobar, pagos, reclamos resueltos con razón, validaciones robustas, pruebas automatizadas y documentación técnica completa.
