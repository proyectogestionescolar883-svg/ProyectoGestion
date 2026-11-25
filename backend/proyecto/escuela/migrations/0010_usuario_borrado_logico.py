"""Diferencia "deshabilitado" de "eliminado" en `usuarios` (R4).

`estado = 0` sigue siendo el deshabilitado normal; `eliminado = 1` marca la
baja lógica definitiva del usuario. El DDL lo declara `escuela/schema.py` en
forma portable para MySQL y Postgres; esta migración sólo agrega la columna si
falta. La reversión es no-op para no quitar una columna soportada.
"""
from django.db import migrations

from escuela import schema

COLUMNAS = tuple(
    (tabla, columna, ddl)
    for tabla, columna, ddl, _relleno, _nota in schema.COLUMNAS
    if tabla == 'usuarios' and columna == 'eliminado'
)


def _aplicar(apps, schema_editor):
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

    dependencies = [
        ('escuela', '0009_borrado_logico_calificaciones_horarios'),
    ]

    operations = [
        migrations.RunPython(_aplicar, migrations.RunPython.noop),
    ]
