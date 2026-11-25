"""Agrega `ddjj_docente.verificada` (registro histórico; `managed=False`).

El DDL y el tipo viven en `escuela/schema.py`. Esta migración sólo agrega la
columna si falta. La reversión es no-op para no quitar una columna soportada.
"""
from django.db import migrations

from escuela import schema

COLUMNAS = tuple(
    (tabla, columna, ddl)
    for tabla, columna, ddl, _relleno, _nota in schema.COLUMNAS
    if tabla == 'ddjj_docente' and columna == 'verificada'
)


def agregar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        existentes = schema.columnas_de(cursor, 'ddjj_docente')
        for _tabla, columna, ddl in COLUMNAS:
            if columna in existentes:
                continue
            cursor.execute(
                f'ALTER TABLE {schema._q(cursor, "ddjj_docente")} '
                f'ADD COLUMN {schema._q(cursor, columna)} '
                f'{schema._ddl_para(cursor, ddl)}'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0004_notificaciones_rol'),
    ]

    operations = [
        migrations.RunPython(agregar, migrations.RunPython.noop),
    ]
