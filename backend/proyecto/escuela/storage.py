import hashlib
import hmac
import mimetypes
import time
from urllib.parse import quote, unquote, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import connection


RUTA_MEDIA = '/media/'
RUTA_API_MEDIA = '/api/media/'
PREFIJOS = (RUTA_MEDIA, RUTA_API_MEDIA)


def normalizar_ruta(valor):
    if not valor:
        return ''
    texto = str(valor).strip()
    if not texto:
        return ''
    if texto.startswith(('http://', 'https://')):
        texto = urlparse(texto).path
    texto = unquote(texto).split('?', 1)[0]
    for prefijo in PREFIJOS:
        if texto.startswith(prefijo):
            texto = texto[len(prefijo):]
            break
    return texto.lstrip('/')


def _firma(ruta, exp):
    mensaje = f'{ruta}|{exp}'.encode('utf-8')
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), mensaje, hashlib.sha256).hexdigest()


def media_url(valor, expires_in=None):
    ruta = normalizar_ruta(valor)
    if not ruta:
        return ''
    if expires_in is None:
        expires_in = getattr(settings, 'MEDIA_URL_EXPIRES_IN', 3600)
    exp = int(time.time()) + int(expires_in)
    return f'{RUTA_API_MEDIA}{quote(ruta, safe="/")}?exp={exp}&sig={_firma(ruta, exp)}'


def verificar_firma(ruta, exp, sig):
    if not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if exp_int < int(time.time()):
        return False
    return hmac.compare_digest(_firma(normalizar_ruta(ruta), exp_int), str(sig))


class DatabaseStorage(Storage):
    def _save(self, name, content):
        if hasattr(content, 'seek'):
            content.seek(0)
        datos = content.read()
        if isinstance(datos, str):
            datos = datos.encode('utf-8')
        content_type = getattr(content, 'content_type', None) or ''
        ruta = normalizar_ruta(name)
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM media_blobs WHERE ruta = %s', [ruta])
            valor = datos
            if connection.vendor == 'postgresql':
                from psycopg2 import Binary
                valor = Binary(datos)
            cursor.execute(
                'INSERT INTO media_blobs (ruta, contenido, content_type, tamano) VALUES (%s, %s, %s, %s)',
                [ruta, valor, content_type, len(datos)],
            )
        return ruta

    def _open(self, name, mode='rb'):
        with connection.cursor() as cursor:
            cursor.execute('SELECT contenido FROM media_blobs WHERE ruta = %s', [normalizar_ruta(name)])
            fila = cursor.fetchone()
        if not fila:
            raise FileNotFoundError(name)
        contenido = fila[0]
        if hasattr(contenido, 'tobytes'):
            contenido = contenido.tobytes()
        return ContentFile(contenido, name=name)

    def delete(self, name):
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM media_blobs WHERE ruta = %s', [normalizar_ruta(name)])

    def exists(self, name):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM media_blobs WHERE ruta = %s', [normalizar_ruta(name)])
            return cursor.fetchone() is not None

    def size(self, name):
        with connection.cursor() as cursor:
            cursor.execute('SELECT tamano FROM media_blobs WHERE ruta = %s', [normalizar_ruta(name)])
            fila = cursor.fetchone()
        return int(fila[0]) if fila and fila[0] is not None else 0

    def url(self, name):
        return media_url(name)

    def content_type(self, name):
        with connection.cursor() as cursor:
            cursor.execute('SELECT content_type FROM media_blobs WHERE ruta = %s', [normalizar_ruta(name)])
            fila = cursor.fetchone()
        if fila and fila[0]:
            return fila[0]
        return mimetypes.guess_type(name)[0] or 'application/octet-stream'
