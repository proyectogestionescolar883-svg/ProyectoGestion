# Deploy en Vercel + Supabase — resumen y pendientes

> **Propósito:** dejar anotado, muy por encima, qué se hizo para migrar y deployar el sistema, y qué queda al pendiente.
>
> **Última actualización:** 2026-11-16

---

## Qué se hizo

- **Migración de la base** de MySQL local a **Supabase (PostgreSQL)**: ~80 tablas y ~2225 filas, con claves foráneas y secuencias reseteadas. Conteos verificados contra MySQL.
- **Backend (Django)** deployado en Vercel → `https://secundaria7-backend.vercel.app`
- **Frontend (Vite/React)** deployado en Vercel → `https://secundaria7-frontend.vercel.app`
- **Auto-deploy**: la rama `main` del repo nuevo `ProyectoGestion` está enlazada a ambos proyectos → cada `git push` a `main` deploya backend y frontend.
- Repo nuevo (origin): `github.com/proyectogestionescolar883-svg/ProyectoGestion`.

## Configuración en Vercel

| Proyecto | Dominio | Root dir | Framework | Env principales |
|---|---|---|---|---|
| `secundaria7-backend` | secundaria7-backend.vercel.app | `backend` | Django | `DB_*`, `DJANGO_*`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` |
| `secundaria7-frontend` | secundaria7-frontend.vercel.app | `frontend` | Vite | `VITE_API_URL` |

- **Base de datos (Supabase):** se usa el **pooler en modo transacción** `aws-1-us-east-1.pooler.supabase.com:6543`, usuario `postgres.<project-ref>`. La conexión directa (`db.<ref>.supabase.co`) es IPv6 y Vercel no la alcanza.
- **Deployment Protection** desactivada en ambos proyectos.

## Cambios de código relevantes

- `backend/proyecto/wsgi.py` y `asgi.py`: agregan su carpeta al `sys.path` para poder importar `escuela` en Vercel.
- `backend/proyecto/settings.py`: base de datos condicional MySQL/PostgreSQL por variables de entorno; `DISABLE_SERVER_SIDE_CURSORS = True` (requerido por el pooler transaccional); CORS/CSRF por env.
- `backend/requirements.txt`: se agregó `psycopg2-binary`.
- `frontend/vercel.json`: rewrites para el base path `/misecundaria7/`.
- `backend/vercel.json` y `backend/.vercelignore`.
- `backend/proyecto/settings.py`: `MIGRATION_MODULES = {'escuela': None}`. Los modelos son `managed=False` y el esquema se controla con `schema.py` / `manage.py verificar_esquema` (ahora compatible con Postgres); `makemigrations --check --dry-run` ya no propone un `initial` falso. Las migraciones 0001–0012 quedan como registro histórico, no se ejecutan automáticamente..

## Pendientes / al pendiente

- [ ] **Seguridad — contraseñas:** todas las cuentas quedaron con contraseña `123` (aplicada directo en la tabla `usuarios`). Incluye las cuentas **admin** (`mfernandez`, `rgutierrez`) → el sitio público queda accesible para cualquiera. **Resetear a algo seguro y forzar cambio.**
- [ ] **Rotar la contraseña de `postgres` de Supabase** (desde el Dashboard → Settings → Database, o vía Management API con un PAT; por SQL no se puede: "only superusers can alter privileged roles").
- [ ] Confirmar que los **backups** de Supabase estén activos.
- [ ] Revisar si `deploy/`, `estructura base de datos/` y `misecundaria7-frontend.zip` siguen haciendo falta.
