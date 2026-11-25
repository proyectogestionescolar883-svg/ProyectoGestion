# Deploy en Vercel + Supabase — resumen y pendientes

> **Propósito:** dejar anotado, muy por encima, qué se hizo para migrar y deployar el sistema, y qué queda al pendiente.
>
> **Última actualización:** 2026-11-24
>
> **Estado actual:** producción con PostgreSQL (Supabase); las credenciales se
> leen de variables de entorno y nunca se documentan en este archivo.

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

- **Base de datos (Supabase/PostgreSQL):** se usa el **pooler en modo transacción** en `<HOST>:6543` con `<DB_USER>` y `<DB_PASSWORD>` (valores reales sólo en las env vars de Vercel). La conexión directa es IPv6 y Vercel no la alcanza.
- **Deployment Protection** desactivada en ambos proyectos.

## Cambios de código relevantes

- `backend/proyecto/wsgi.py` y `asgi.py`: agregan su carpeta al `sys.path` para poder importar `escuela` en Vercel.
- `backend/proyecto/settings.py`: base de datos condicional MySQL/PostgreSQL por variables de entorno; `DISABLE_SERVER_SIDE_CURSORS = True` (requerido por el pooler transaccional); CORS/CSRF por env.
- `backend/requirements.txt`: se agregó `psycopg2-binary`.
- `frontend/vercel.json`: rewrites para el base path `/misecundaria7/`.
- `backend/vercel.json` y `backend/.vercelignore`.
- `backend/proyecto/settings.py`: `MIGRATION_MODULES = {'escuela': None}`. Los modelos son `managed=False` y el esquema se controla con `schema.py` / `manage.py verificar_esquema --aplicar` (compatible con Postgres, usa `current_schema()`); `makemigrations --check --dry-run` ya no propone un `initial` falso. Las migraciones 0001–0012 quedan como registro histórico, no se ejecutan automáticamente.

## Pendientes / al pendiente

- [ ] **Seguridad — contraseñas:** las cuentas de prueba quedaron con una contraseña débil conocida (valor redactado: `<DB_PASSWORD>`), aplicada directo en la tabla `usuarios`. Incluye cuentas **admin** (identificadores redactados: `<ADMIN_USER_1>`, `<ADMIN_USER_2>`) → el sitio público queda accesible para cualquiera. **Resetear a algo seguro y forzar cambio.**
- [ ] **Rotación externa (a cargo del usuario, fuera de este repo):** contraseña de `<DB_USER>` en Supabase y `<DJANGO_SECRET_KEY>` en Vercel. La rotación real no se realiza ni se registra en la documentación.
- [ ] Confirmar que los **backups** de Supabase estén activos.
- [ ] Revisar si `deploy/`, `estructura base de datos/` y `misecundaria7-frontend.zip` siguen haciendo falta.
