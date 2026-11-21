"""Diferencia "deshabilitado" de "eliminado" en `usuarios` (R4).

`estado = 0` sigue siendo el deshabilitado normal; `eliminado = 1` marca la
baja lógica definitiva del usuario. Así una habilitación programada no puede
reactivar a un usuario eliminado.

El DDL es explícito y portable (BOOLEAN en vez de TINYINT) porque la base real
es Postgres/Supabase y `escuela.schema.aplicar_esquema()` es MySQL-only.
"""
from django.db import migrations


SQL_AGREGAR = """
ALTER TABLE usuarios
    ADD COLUMN eliminado BOOLEAN NOT NULL DEFAULT FALSE
"""

SQL_QUITAR = """
ALTER TABLE usuarios
    DROP COLUMN eliminado
"""


def _aplicar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_AGREGAR)


def _revertir(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_QUITAR)


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0009_borrado_logico_calificaciones_horarios'),
    ]

    operations = [
        migrations.RunPython(_aplicar, _revertir),
    ]
