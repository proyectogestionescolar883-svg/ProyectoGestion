"""Agrega borrado lógico a `calificaciones`, `horarios` y `horarios_especiales`.

Por qué existe esta migración
-----------------------------
La migración ``0007_sincronizar_esquema_managed_false`` ya aplica el DDL
declarativo de ``escuela/schema.py``, pero en una base que la corrió **antes**
de que esas tres tablas entraran en ``SOFT_DELETE_TABLAS`` las columnas siguen
faltando: la 0007 ya figura como aplicada y no vuelve a ejecutarse.

Consecuencia observada (hallazgo C5 de la auditoría): sus ``DELETE`` eran
físicos y no dejaban rastro en ``historial_cambios``, y el borrado lógico no
era posible.

Qué hace
--------
Delega otra vez en ``escuela.schema.aplicar_esquema()``, que es idempotente y
no destructivo: solo agrega las columnas que falten y rellena las filas
existentes con el valor por defecto del modelo (``estado = 1``). El relleno es
clave: ``ActivoManager`` filtra ``estado=True``, así que sin él los registros
ya cargados desaparecerían de los listados.

``migrate escuela 0008`` la revierte (baja solo las columnas que agregó esta
migración); en una base de producción es preferible dejar la migración
aplicada.
"""
from django.db import migrations

from escuela import schema

# Tablas que esta migración incorpora al borrado lógico.
_TABLAS_NUEVAS = ('calificaciones', 'horarios', 'horarios_especiales')


def _aplicar(apps, schema_editor):
    schema.aplicar_esquema(
        schema_editor.connection,
        log=lambda msg: None,
    )


def _revertir(apps, schema_editor):
    """Elimina SOLO las columnas que agregó esta migración.

    Es la operación inversa simétrica y existe para poder deshacer la
    migración en un entorno de pruebas. En producción es preferible dejar la
    migración aplicada: perder columnas implicaría perder datos.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existentes = schema.tablas_de(cursor)
        for tabla, columna, *_ in reversed(schema.COLUMNAS):
            if tabla not in _TABLAS_NUEVAS or tabla not in existentes:
                continue
            if columna not in schema.columnas_de(cursor, tabla):
                continue
            cursor.execute(f'ALTER TABLE `{tabla}` DROP COLUMN `{columna}`')


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0008_seed_estados_asistencia'),
    ]

    operations = [
        migrations.RunPython(_aplicar, _revertir),
    ]
