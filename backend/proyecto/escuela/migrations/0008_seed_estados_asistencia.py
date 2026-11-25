"""Carga idempotente de los estados de asistencia base del sistema.

El registro de asistencias resuelve el estado por nombre exacto (lógica
cableada en `views.py`). Sin estos cinco registros el registro de asistencias
de alumnos y de docentes falla con HTTP 400, así que son catálogo del sistema y
no datos de negocio: se garantiza su existencia con un seed, igual que hace
`0006_seed_tipos_accion` con `tipos_accion`.

Es un seed de DATOS, no de esquema: no altera ninguna tabla ni columna (los
modelos son `managed = False` y el DDL se gobierna desde `escuela/schema.py`).

El reverso sólo considera los IDs que esta corrida creó efectivamente; si la
reversión ocurre en otro proceso, no hay IDs registrados y no se borra nada.
"""
from django.db import migrations

from escuela.utils import (
    ESTADOS_ASISTENCIA_BASE,
    seed_estados_asistencia_base,
)

_CREADOS_POR_CORRIDA = set()


def sembrar(apps, schema_editor):
    EstadoAsistencia = apps.get_model('escuela', 'EstadoAsistencia')
    try:
        antes = set(
            EstadoAsistencia.objects.filter(
                nombre_estado__in=ESTADOS_ASISTENCIA_BASE,
            ).values_list('nombre_estado', flat=True)
        )
    except Exception:
        antes = set()

    seed_estados_asistencia_base()

    try:
        nuevos = EstadoAsistencia.objects.filter(
            nombre_estado__in=ESTADOS_ASISTENCIA_BASE,
        ).exclude(nombre_estado__in=antes).values_list('pk', flat=True)
        _CREADOS_POR_CORRIDA.update(int(pk) for pk in nuevos)
    except Exception:
        pass


def deshacer(apps, schema_editor):
    if not _CREADOS_POR_CORRIDA:
        return

    EstadoAsistencia = apps.get_model('escuela', 'EstadoAsistencia')
    try:
        estados = EstadoAsistencia.objects.filter(
            pk__in=_CREADOS_POR_CORRIDA,
            nombre_estado__in=ESTADOS_ASISTENCIA_BASE,
        )
        for estado in estados:
            if _tiene_asistencias(apps, estado):
                continue
            estado.delete()
        _CREADOS_POR_CORRIDA.clear()
    except Exception:
        pass


def _tiene_asistencias(apps, estado):
    try:
        con_curso = apps.get_model('escuela', 'Asistencia')
        if con_curso.objects.filter(id_estado_asistencia=estado).exists():
            return True
    except Exception:
        pass
    try:
        docente = apps.get_model('escuela', 'AsistenciaDocente')
        if docente.objects.filter(id_estado_asistencia=estado).exists():
            return True
    except Exception:
        pass
    return False


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0007_sincronizar_esquema_managed_false'),
    ]

    operations = [
        migrations.RunPython(sembrar, deshacer),
    ]
