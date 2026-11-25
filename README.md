# MiSecundaria7

## Estructura del proyecto

- `backend/`: Backend Django.
- `frontend/`: Frontend Vite + React.

## Instalación

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Ejecución

### Backend

```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm run dev
```

## Esquema de la base (importante)

Todos los modelos de `escuela` usan `managed = False`: `migrate` **no** crea ni
altera esas tablas. Para ampliar el esquema físico hay que pasar por la
especificación declarativa de `backend/proyecto/escuela/schema.py`.

```bash
# comparar el esquema físico con los modelos (sale con código 1 si hay desvío)
python manage.py verificar_esquema

# aplicar el DDL faltante (idempotente y no destructivo)
python manage.py verificar_esquema --aplicar

# garantizar los estados de asistencia base (idempotente; ya lo hace la
# migración 0008, sirve para reponerlos si alguien los borró)
python manage.py seed_estados_asistencia

# tests (crean una base `test_*` aparte; nunca tocan la real)
python manage.py test escuela
```

## Datos maestros (Administración → Configuración)

Los catálogos base —ciclos lectivos, módulos horarios, períodos de evaluación,
estados de asistencia y tipos de acta— se administran desde
**Administración → Configuración** (solo `admin` y `director`), sin necesidad de
`INSERT` manuales en la base de datos. Crear, editar, desactivar y reactivar está
disponible en pantalla; donde el registro está en uso, la interfaz lo explica y
la API responde `HTTP 400` en vez de fallar.

Dos comandos de diagnóstico recorren el flujo completo contra la base real
(crean datos de prueba y **los borran al terminar**):

```bash
# flujo mínimo de punta a punta + guardas de borrado + permisos
python manage.py verificar_flujo_configuracion

# borrar datos de una corrida anterior que haya quedado a medias
python manage.py verificar_flujo_configuracion --limpiar
```

Detalles en `docs/DOCUMENTACION_TECNICA.md` y
`docs/HISTORIAL.md` §16.

En PostgreSQL/Supabase no aplica el `GRANT ... test\_%` de MySQL: Django crea la
base `test_<DB_NAME>` con el rol configurado, que debe tener `CREATEDB` en el
entorno de pruebas. La base de producción nunca se usa para tests.

Detalles en `docs/DOCUMENTACION_TECNICA.md` §14.3 y
`docs/REFERENCIA_BD.md` §19.

## Despliegue del frontend

El frontend se despliega en Vercel desde `frontend/` (`frontend/vercel.json`),
bajo el base path `/misecundaria7/`; el backend se despliega en Vercel desde
`backend/` (`backend/vercel.json`). No se sube un zip a un host externo: Vercel
construye y publica automáticamente desde el repositorio. Las variables
`VITE_API_URL`, `DB_*`, `DJANGO_SECRET_KEY`, `CORS_ALLOWED_ORIGINS` y
`CSRF_TRUSTED_ORIGINS` se configuran en el panel de Vercel; ver
`docs/DEPLOY_VERCEL_SUPABASE.md`.

```bash
cd frontend
npm run build
```

## Documentación

Todo en [`docs/`](docs):

- [`DOCUMENTACION_TECNICA.md`](docs/DOCUMENTACION_TECNICA.md) — arquitectura, esquema de BD, despliegue
- [`REFERENCIA_BD.md`](docs/REFERENCIA_BD.md) — modelo de datos tabla por tabla; ver §"Alineación con el esquema real"
- [`DEPLOY_VERCEL_SUPABASE.md`](docs/DEPLOY_VERCEL_SUPABASE.md) — deploy en Vercel con PostgreSQL/Supabase
- [`../ESTRUCTURA_BASE_DE_DATOS.md`](ESTRUCTURA_BASE_DE_DATOS.md) — volcado de las 80 tablas reales (columnas, nulabilidad y FKs)
- [`HISTORIAL.md`](docs/HISTORIAL.md) — bitácora de cambios
- [`REGLAS_DESARROLLO.md`](docs/REGLAS_DESARROLLO.md) — reglas de código
- [`ESTANDARES_UI.md`](docs/ESTANDARES_UI.md) y [`VISUAL_STANDARD.md`](docs/VISUAL_STANDARD.md) — criterios visuales
- [`GUIA_TESTEO_MiSecundaria7.md`](docs/GUIA_TESTEO_MiSecundaria7.md) — cómo probar
- [`PLAN_*.md`](docs) — planes de correcciones (registro histórico; no son estado vigente)
- [`RELEVAMIENTO_SISTEMA_SECUNDARIA7.md`](docs/RELEVAMIENTO_SISTEMA_SECUNDARIA7.md) y [`REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md`](docs/REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md) — relevamiento y requisitos (el relevamiento es histórico)
- [`docs/_backup/`](docs/_backup) — versiones anteriores de los análisis (consulta histórica)

## Git

El repositorio ignora dependencias instaladas, entornos virtuales y archivos temporales mediante `.gitignore`.
