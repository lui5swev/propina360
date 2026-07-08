# Propina360

Sistema web para gestion, calculo, anticipos, reclamos, cierres y pagos de propinas en CLP.

Esta copia esta preparada como repositorio independiente para GitHub. Incluye el backend FastAPI funcional, frontend servido por el backend, frontend React de referencia, esquema SQL, especificacion, documentos de pruebas, work order y evidencias seleccionadas de WEBFORGE.

## Estructura

```text
backend-fastapi/              Backend FastAPI + UI standalone + pruebas
frontend-react-bootstrap/     Frontend React/Vite de referencia
database-mysql-mariadb/       Esquema SQL objetivo
docs/                         Especificacion y evidencia documental
factory-source/               Work order y generador usado por la fabrica
factory-evidence/             Reportes seleccionados de materializacion
```

## Ejecucion local

```bash
cd backend-fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18765
```

Abrir:

- Admin: http://127.0.0.1:18765/admin
- Trabajador: http://127.0.0.1:18765/dashboard
- API docs: http://127.0.0.1:18765/docs

Credenciales de desarrollo:

- Admin: `admin@propina360.local` / `Admin-123!`
- Trabajador: `ana.munoz@test.local` / `Worker-123!`

## Pruebas

```bash
cd backend-fastapi
PYTHONPATH=. python3 -m pytest -q
```

Resultado esperado en el estado empaquetado:

```text
5 passed
```

## Cobertura

```bash
cd backend-fastapi
PYTHONPATH=. python3 -m pytest --cov=app --cov-report=term-missing -q
```

La evidencia actual documentada reporta pruebas automatizadas pasando y cobertura de codigo inferior a 100%. Ver `docs/documento_pruebas_validacion_evidencias_propina360.md`.

## GitHub

```bash
git init
git add .
git commit -m "Initial Propina360 package"
git branch -M main
git remote add origin <URL_DEL_REPOSITORIO>
git push -u origin main
```

## Notas de seguridad

- La base SQLite local no se versiona.
- Las credenciales seed son solo para desarrollo.
- Cambiar `PROPINA360_SIGNING_KEY` antes de usar un ambiente no local.
