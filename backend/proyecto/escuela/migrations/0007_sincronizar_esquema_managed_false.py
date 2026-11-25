"""Sincroniza el esquema físico de las tablas `managed=False` con los modelos.

Por qué existe esta migración
-----------------------------
Todos los modelos de `escuela` usan `managed = False`, así que Django nunca
crea ni altera esas tablas. El esquema se provisionaba solo con el volcado SQL
de referencia (`deploy/sql/sistema_escolar.mariadb.sql`), que es una foto
antigua del MySQL original y **no** incluye:

  * las columnas de borrado lógico `estado` / `fecha_eliminacion`
    (las usa `ActivoManager`, `utils.marcar_eliminado` y varios serializers),
  * los flags `activo` de `materias`, `cursos` y `curso_materia`
    (`utils.activar_o_crear` y los filtros `activo=True` de las vistas),
  * columnas de funcionalidad que el backend y el frontend ya usan:
    `cursos.orientacion`, `padres_tutores.correo`/`tipo`,
    `asistencias.hora`/`justificado`, `horarios.id_modulo`,
    `notificaciones.id_alumno` y el contenido pedagógico de
    `planificaciones`.

Consecuencia observada: `/api/materias/`, `/api/cursos/`, `/api/docentes/`,
`/api/alumnos/`, `/api/calificaciones/`, `/api/actas/` y casi todos los demás
listados devolvían HTTP 500 con
`(1054, "Unknown column 'materias.activo' in 'SELECT'")`.

Qué hace
--------
Delega en `escuela.schema.aplicar_esquema()`, que recorre la especificación
declarativa `escuela/schema.py` y ejecuta solo el DDL que falta. Es:

* **idempotente**: cada sentencia se valida contra `information_schema`,
  así que se puede reejecutar sin fallar ni duplicar nada;
* **no destructivo**: únicamente ADD COLUMN / ADD INDEX / ADD CONSTRAINT y
  MODIFY COLUMN para alinear la nulabilidad. Nunca DROP, TRUNCATE, DELETE
  ni ALTER destructivo; los datos existentes se conservan y se rellenan con
  el valor por defecto del modelo.

La reversión es no-op: el DDL es parte del esquema soportado declarado en
`schema.py` y bajarlo dejaría la base fuera de servicio. `INVENTARIO` deja
explícito qué cubre esta migración dentro de esa declaración.
"""
from django.db import migrations

from escuela import schema

INVENTARIO = {
    'tablas': tuple(schema.TABLAS_NUEVAS),
    'columnas': tuple(
        (tabla, columna) for tabla, columna, *_ in schema.COLUMNAS
    ),
    'indices': tuple(spec['indice'] for spec in schema.INDICES),
    'unicos': tuple(spec['indice'] for spec in schema.UNICOS),
}


def _aplicar(apps, schema_editor):
    schema.aplicar_esquema(
        schema_editor.connection,
        log=lambda msg: None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0006_seed_tipos_accion'),
    ]

    operations = [
        migrations.RunPython(_aplicar, migrations.RunPython.noop),
    ]
