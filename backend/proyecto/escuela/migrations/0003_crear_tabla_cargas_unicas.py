"""Crea `cargas_unicas` desde el DDL portable de `escuela/schema.py`.

La tabla sigue siendo `managed=False`; esta migración es un registro histórico
y sólo la crea si no existe. La reversión es no-op para no perder datos.
"""
from django.db import migrations

from escuela import schema


def crear(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if 'cargas_unicas' in schema.tablas_de(cursor):
            return
        cursor.execute(schema.TABLAS_NUEVAS['cargas_unicas'][schema._vendor(cursor)])


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0002_cleanup_horarios_educacion_fisica'),
    ]

    operations = [
        migrations.RunPython(crear, migrations.RunPython.noop),
    ]
