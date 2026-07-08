# Manifiesto del paquete Propina360

## Incluido

- Codigo backend FastAPI: `backend-fastapi/app/`
- UI standalone servida por FastAPI: `backend-fastapi/app/static/`
- Pruebas backend: `backend-fastapi/tests/`
- Dependencias Python: `backend-fastapi/requirements.txt`
- Frontend React/Vite de referencia: `frontend-react-bootstrap/`
- Esquema MySQL/MariaDB: `database-mysql-mariadb/schema.sql`
- Especificacion funcional: `docs/especificacion_sistema_propinas_propina360.md`
- Documento de pruebas y evidencias: `docs/documento_pruebas_validacion_evidencias_propina360.md`
- Work order de fabrica: `factory-source/work_order.json`
- Generador de work order: `factory-source/generate_propina360_work_order.py`
- Evidencia de fabrica: `factory-evidence/`

## Excluido intencionalmente

- `propina360.db`
- `.coverage`
- `__pycache__/`
- `.pytest_cache/`
- `node_modules/`
- Artefactos completos de otras ejecuciones o proyectos ajenos a Propina360

## Estado de validacion

- WEBFORGE: `complete`
- Validacion de artefactos: `pass`
- Pytest backend: `5 passed`
- Cobertura de codigo: documentada como brecha; no alcanza 100% en la suite actual.
