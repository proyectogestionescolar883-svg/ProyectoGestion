# Hallazgos nuevos (fuera de la auditoría)

Errores detectados al revisar/arreglar los ítems de `Auditoría MiSecundaria7.docx`
que **no** figuran en esa auditoría, más datos del propio informe que no pueden
corregirse sin una decisión externa. Los grupos **1 a 4 ya están corregidos** y
se conservan acá como registro; el grupo 5 queda documentado a la espera de una
decisión de datos.

---

## 1. Patrón C3 repetido fuera de la auditoría

Misma clase de bug que C3: un filtro/chequeo por `'preceptor' in roles` acota la
consulta a los cursos del preceptor aunque el usuario tenga **además** un rol de
gestión (`admin` / `director` / `jefe_preceptores`), que debería ver todo el
ámbito. La auditoría solo listó `CursoMateriaViewSet`, `HorarioViewSet` y
`HorarioEspecialViewSet` (ya corregidos en `views.py`). Estas otras vistas tienen
el mismo patrón y **no** están en la auditoría (que aclara no haber revisado en
detalle asistencias-docente, actividades ni notificaciones):

- `backend/proyecto/escuela/views.py:2338` — `ActividadDocenteViewSet.get_queryset`:
  `if 'preceptor' in roles` sin bypass para roles de gestión. Un `admin` solo ve
  todo, pero un `admin` + `preceptor` (p. ej. usuario `rgutierrez`) queda acotado
  a sus cursos de preceptor.
- `backend/proyecto/escuela/views.py:5829` — `NotificacionViewSet.enviar_carga_unica`
  (`@action`): idem (lanza `PermissionDenied` si el curso no es uno de sus cursos
  de preceptor).
- `backend/proyecto/escuela/views.py:3793` — `AsistenciaViewSet.preceptor_materia`
  (`@action`): `cursos_ids = _preceptor_cursos_ids(request) if 'preceptor' in roles
  else None` → un `admin` + `preceptor` queda acotado a sus cursos.
- `backend/proyecto/escuela/views.py:4225` — `AsistenciaDocenteViewSet.docentes_disponibles`
  (`@action`): idem.
- `backend/proyecto/escuela/views.py:4410` — `AsistenciaDocenteViewSet.hoy`
  (`@action`): idem.
- `backend/proyecto/escuela/views.py:4537` — `AsistenciaDocenteViewSet.historial`
  (`@action`): idem.
- `backend/proyecto/escuela/views.py:4581` — `AsistenciaDocenteViewSet.registrar_asistencia_docente`
  (`@action`): idem.

**Resuelto:** las 7 vistas usan `_es_preceptor_operativo()`; los roles de gestión
ya no quedan acotados a los cursos de preceptor.

---

## 2. `verificar_esquema` / `schema.py` son MySQL-only (fallan en Postgres)

Detectado al implementar C5 (borrado lógico de `calificaciones`, `horarios` y
`horarios_especiales`). `escuela/schema.py` está escrito para MariaDB/MySQL: usa
`DATABASE()` y `SHOW`/`information_schema` con sintaxis MySQL.

Consecuencia en la base real (Postgres/Supabase):

```text
manage.py verificar_esquema
django.db.utils.ProgrammingError: function database() does not exist
LINE 1: ...OM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()...
```

`schema.tablas_de()`, `columnas_de()`, `es_nullable()`, `indices_de()`,
`constraints_de()` y `verificar_esquema()` —y por lo tanto el comando
`manage.py verificar_esquema`— **no corren contra Postgres**. `aplicar_esquema()`
(migración 0007/0009) y `sql_esquema()` (comando `generar_sql_esquema`, que solo
emite texto) no se ven afectados en la práctica porque la migración no se ejecuta
en producción (Vercel solo corre `collectstatic`).

**Resuelto:** `schema.py` detecta `connection.vendor`, usa `current_schema()` y
comillas dobles en Postgres, `DATABASE()` y backticks en MySQL. `verificar_esquema`
corre en Supabase y `verificar_esquema --aplicar` alineó los 7 desvíos restantes
(3 columnas a NOT NULL, 2 índices y 2 FKs). `sql_esquema()` sigue emitiendo SQL
MySQL/MariaDB.

---

## 3. `makemigrations --check` siempre pide un `0010_initial` (preexistente)

Detectado al validar C5. `manage.py makemigrations --check --dry-run` responde
que falta una migración inicial con **todos** los modelos (`CreateModel` de
`Acta`, `Alumno`, `Calificacion`, ...). No es un problema introducido por C5:
ninguna migración de `escuela` (0001–0009) declara `CreateModel` —la 0001 es
`initial = True` pero solo hace `ALTER TABLE` crudo—, así que el *estado* de
migraciones no conoce los modelos.

Es consecuencia de que todos los modelos usan `managed = False` y el esquema se
provisiona desde `escuela/schema.py` / el volcado SQL, no desde migraciones. No
se debe generar ese `0010_initial`: sería un cambio grande y fuera de alcance.
**Resuelto:** `settings.py` define `MIGRATION_MODULES = {'escuela': None}`: el
esquema se controla con `verificar_esquema`, no con migraciones, y
`makemigrations --check --dry-run` devuelve `No changes detected`. Las migraciones
0001–0012 quedan como registro histórico; Vercel no ejecuta `migrate`.

---

## 4. `quitar_rol` usa SQL de MySQL (falla en Postgres)

Detectado al revisar R4/R6. En `backend/proyecto/escuela/views.py:1684`
(`quitar_rol`, acción de `UsuarioViewSet`) había un `cursor.execute()` con
`UPDATE curso_materia cm JOIN docentes d ON ...`, sintaxis **MySQL-only**.
En Postgres/Supabase esa sentencia falla con error de sintaxis cerca de `JOIN`.
**Resuelto:** se reemplazó el `UPDATE ... JOIN ...` por ORM
(`Docente.all_objects` + `CursoMateria.all_objects.update(id_docente=None)`),
portable en MySQL y Postgres.

---

## 5. Datos del bloque B sin corrección automática

- **B1 (126 choques de docente en la grilla regular):** H3 agregó validación para
  altas nuevas, pero no se borró ningún horario histórico: no hay criterio para
  elegir cuál de las dos materias conservar.
- **B3 (DNIs fuera de rango):** no se inventaron DNIs nuevos. Se agregó la regla
  30.000.000–65.000.000 para altas/ediciones (`AlumnoSerializer`) y el cierre de
  ciclo ahora devuelve `omitidos` en vez de saltear alumnos sin curso en silencio.
- **B8 (prenotas incoherentes):** N4 las define como resultado cualitativo
  independiente de la nota numérica; no se modificaron los datos existentes.


