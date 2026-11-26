from urllib.parse import quote

from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse

from escuela.storage import (
    PROPOSITO_MEDIA,
    es_mime_adjunto,
    es_mime_inline,
    normalizar_ruta,
    tipo_mime_segmento,
    verificar_firma,
)


def media_proxy(request, ruta):
    usuario = request.GET.get('usr', '')
    proposito = request.GET.get('fin') or PROPOSITO_MEDIA
    if not usuario or not verificar_firma(
        ruta,
        request.GET.get('exp'),
        request.GET.get('sig'),
        usuario,
        proposito,
    ):
        return HttpResponse('Enlace inválido o expirado', status=403)
    nombre = normalizar_ruta(ruta)
    if not nombre or not default_storage.exists(nombre):
        return HttpResponse('Archivo no encontrado', status=404)
    tipo = tipo_mime_segmento(default_storage.content_type(nombre))
    if not es_mime_inline(tipo) and not es_mime_adjunto(tipo):
        tipo = 'application/octet-stream'
    respuesta = FileResponse(
        default_storage.open(nombre, 'rb'),
        content_type=tipo,
    )
    respuesta['Cache-Control'] = 'private, max-age=300'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    if not es_mime_inline(tipo):
        seguro = nombre.replace('\r', '').replace('\n', '').replace('"', '')
        respuesta['Content-Disposition'] = (
            "attachment; filename*=UTF-8''" + quote(seguro, safe='')
        )
    return respuesta
