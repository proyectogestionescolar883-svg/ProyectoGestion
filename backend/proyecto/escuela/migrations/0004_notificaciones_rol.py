"""Agrega `notificaciones.rol` (registro histórico; `managed=False`).

El DDL y el tipo viven en `escuela/schema.py`. Esta migración sólo agrega la
columna si falta. La reversión es no-op para no quitar una columna soportada.
"""
from django.db import migrations

from escuela import schema

COLUMNAS = tuple(
    (tabla, columna, ddl)
    for tabla, columna, ddl, _relleno, _nota in schema.COLUMNAS
    if tabla == 'notificaciones' and columna == 'rol'
)


def agregar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        existentes = schema.columnas_de(cursor, 'notificaciones')
        for _tabla, columna, ddl in COLUMNAS:
            if columna in existentes:
                continue
            cursor.execute(
                f'ALTER TABLE {schema._q(cursor, "notificaciones")} '
                f'ADD COLUMN {schema._q(cursor, columna)} '
                f'{schema._ddl_para(cursor, ddl)}'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0003_crear_tabla_cargas_unicas'),
    ]

    operations = [
        migrations.RunPython(agregar, migrations.RunPython.noop),
    ]
