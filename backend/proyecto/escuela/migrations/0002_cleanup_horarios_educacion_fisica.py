"""Limpieza histórica de horarios de Educación Física (inactiva).

La limpieza física original se conservaba en esta migración, pero los modelos
son `managed=False` y el esquema actual usa borrado lógico. Para no destruir
datos en una base real se deja como no-op en ambos sentidos.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0001_usuario_fechas_programadas'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
