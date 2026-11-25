"""DDJJ por ciclo lectivo (R13; registro histórico con `managed=False`).

La columna y el backfill portable del ciclo activo más reciente están en
`escuela/schema.py`. Esta migración delega en esa declaración, que es
idempotente y respeta MySQL y Postgres. La reversión es no-op.
"""
from django.db import migrations

from escuela import schema


def _aplicar(apps, schema_editor):
    schema.aplicar_esquema(schema_editor.connection, log=lambda msg: None)


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0010_usuario_borrado_logico'),
    ]

    operations = [
        migrations.RunPython(_aplicar, migrations.RunPython.noop),
    ]
