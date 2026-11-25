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

La reversión es no-op: esas columnas son parte del esquema soportado y bajarlas
rompería los managers con borrado lógico.
"""
from django.db import migrations

from escuela import schema

_TABLAS_NUEVAS = ('calificaciones', 'horarios', 'horarios_especiales')

INVENTARIO = {
    'columnas': tuple(
        (tabla, columna)
        for tabla, columna, *_ in schema.COLUMNAS
        if tabla in _TABLAS_NUEVAS
    ),
}


def _aplicar(apps, schema_editor):
    schema.aplicar_esquema(
        schema_editor.connection,
        log=lambda msg: None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0008_seed_estados_asistencia'),
    ]

    operations = [
        migrations.RunPython(_aplicar, migrations.RunPython.noop),
    ]
