from datetime import timezone as dt_timezone

from django.db import models, transaction
from django.utils import timezone

from escuela.models import Usuario
from escuela.notifications import notificar_estado_cuenta


def _fecha_aware(fecha):
    if fecha and timezone.is_naive(fecha):
        return timezone.make_aware(fecha, dt_timezone.utc)
    return fecha


def aplicar_programaciones_usuario(now=None):
    now = _fecha_aware(now or timezone.now())

    usuarios = Usuario.objects.filter(
        eliminado=False,
    ).filter(
        models.Q(
            estado=True,
            fecha_deshabilitacion_programada__isnull=False,
            fecha_deshabilitacion_programada__lte=now,
        )
        | models.Q(
            estado=False,
            fecha_habilitacion_programada__isnull=False,
            fecha_habilitacion_programada__lte=now,
        )
    )

    with transaction.atomic():
        for usuario in usuarios:
            update_fields = []

            fecha_deshabilitacion = _fecha_aware(usuario.fecha_deshabilitacion_programada)
            fecha_habilitacion = _fecha_aware(usuario.fecha_habilitacion_programada)

            if usuario.estado and fecha_deshabilitacion and fecha_deshabilitacion <= now:
                usuario.estado = False
                usuario.fecha_deshabilitacion_programada = None
                update_fields.extend(['estado', 'fecha_deshabilitacion_programada'])

            if (not usuario.estado) and fecha_habilitacion and fecha_habilitacion <= now:
                usuario.estado = True
                usuario.fecha_habilitacion_programada = None
                update_fields.extend(['estado', 'fecha_habilitacion_programada'])

            if update_fields:
                usuario.save(update_fields=list(dict.fromkeys(update_fields)))
                notificar_estado_cuenta(usuario)


def sincronizar_estados_usuarios():
    aplicar_programaciones_usuario()

