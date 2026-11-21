from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse

from escuela.storage import normalizar_ruta, verificar_firma


def media_proxy(request, ruta):
    if not verificar_firma(ruta, request.GET.get('exp'), request.GET.get('sig')):
        return HttpResponse('Enlace inválido o expirado', status=403)
    nombre = normalizar_ruta(ruta)
    if not nombre or not default_storage.exists(nombre):
        return HttpResponse('Archivo no encontrado', status=404)
    respuesta = FileResponse(
        default_storage.open(nombre, 'rb'),
        content_type=default_storage.content_type(nombre),
    )
    respuesta['Cache-Control'] = 'private, max-age=300'
    return respuesta
