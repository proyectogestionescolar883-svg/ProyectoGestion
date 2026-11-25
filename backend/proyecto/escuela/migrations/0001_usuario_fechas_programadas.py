"""Columnas de programación de usuarios (registro histórico; `managed=False`).

El DDL lo declara `escuela/schema.py`. Esta migración sólo agrega lo que falte,
usando la inspección portable de ese módulo. La reversión es no-op para no
quitar columnas que hoy forman parte del esquema soportado.
"""
from django.db import migrations

from escuela import schema

COLUMNAS = tuple(
    (tabla, columna, ddl)
    for tabla, columna, ddl, _relleno, _nota in schema.COLUMNAS
    if tabla == 'usuarios'
    and columna in (
        'fecha_deshabilitacion_programada',
        'fecha_habilitacion_programada',
    )
)


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        existentes = schema.columnas_de(cursor, 'usuarios')
        for _tabla, columna, ddl in COLUMNAS:
            if columna in existentes:
                continue
            cursor.execute(
                f'ALTER TABLE {schema._q(cursor, "usuarios")} '
                f'ADD COLUMN {schema._q(cursor, columna)} '
                f'{schema._ddl_para(cursor, ddl)}'
            )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

