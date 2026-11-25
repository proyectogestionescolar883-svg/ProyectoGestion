"""Carga idempotentemente los tipos de acción por defecto (registro histórico).

Usa el modelo histórico con `get_or_create`, portable en MySQL y Postgres.
La tabla es `managed=False`, así que si todavía no existe se omite sin fallar.
La reversión es no-op: estos registros son catálogo del sistema.
"""
from django.db import migrations
from django.db.utils import OperationalError, ProgrammingError

TIPOS_ACCION_BASE = (
    'Crear',
    'Modificar',
    'Eliminar',
    'Cambio de contraseña',
    'Cambio de rol',
    'Habilitar',
    'Deshabilitar',
    'Finalizar',
)


def sembrar(apps, schema_editor):
    try:
        TipoAccion = apps.get_model('escuela', 'TipoAccion')
        for nombre in TIPOS_ACCION_BASE:
            TipoAccion.objects.get_or_create(nombre_accion=nombre)
    except (OperationalError, ProgrammingError):
        return


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0005_ddjj_docente_verificada'),
    ]

    operations = [
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
