import hashlib
import hmac
import mimetypes
import time
from urllib.parse import quote, unquote, urlparse

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import connection, transaction

from escuela.auth_backend import get_usuario_activo_local


RUTA_MEDIA = '/media/'
RUTA_API_MEDIA = '/api/media/'
PREFIJOS = (RUTA_MEDIA, RUTA_API_MEDIA)

MIME_INLINE = frozenset({
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
    'image/bmp',
})
MIME_ATTACHMENT = frozenset({
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/octet-stream',
    'text/plain',
    'text/csv',
})

TAMANO_MAXIMO_MEDIA = 20 * 1024 * 1024
PROPOSITO_MEDIA = 'media'


def tipo_mime_segmento(content_type):
    return (content_type or '').split(';', 1)[0].strip().lower()


def es_mime_inline(content_type):
    return tipo_mime_segmento(content_type) in MIME_INLINE


def es_mime_adjunto(content_type):
    return tipo_mime_segmento(content_type) in MIME_ATTACHMENT


def normalizar_ruta(valor):
    if not valor:
        return ''
    texto = str(valor).strip()
    if not texto:
        return ''
    if texto.startswith(('http://', 'https://')):
        texto = urlparse(texto).path
    texto = unquote(texto).split('?', 1)[0].replace('\\', '/')
    if len(texto) >= 2 and texto[0].isalpha() and texto[1] == ':':
        raise SuspiciousFileOperation('Ruta de archivo no permitida.')
    for prefijo in PREFIJOS:
        if texto.startswith(prefijo):
            texto = texto[len(prefijo):]
            break
    texto = texto.lstrip('/')
    if any(parte == '..' for parte in texto.split('/')):
        raise SuspiciousFileOperation('Ruta de archivo no permitida.')
    return '/'.join(parte for parte in texto.split('/') if parte and parte != '.')


def _detectar_mime(datos, declarado=''):
    if datos.startswith(b'%PDF-'):
        return 'application/pdf'
    if datos.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if datos.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if datos.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if datos[:4] == b'RIFF' and datos[8:12] == b'WEBP':
        return 'image/webp'
    if datos.startswith(b'BM'):
        return 'image/bmp'
    if datos.startswith(b'PK\x03\x04'):
        if b'word/document.xml' in datos[:4096]:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        return 'application/octet-stream'
    if datos.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        return 'application/msword'
    try:
        texto = datos.decode('utf-8')
    except UnicodeDecodeError:
        return 'application/octet-stream'
    if any(ord(caracter) < 32 and caracter not in '\t\n\r' for caracter in texto):
        return 'application/octet-stream'
    if declarado in ('text/csv', 'text/plain'):
        return declarado
    return 'text/plain'


def _firma(ruta, exp, usuario='', proposito=PROPOSITO_MEDIA):
    mensaje = f'{ruta}|{exp}|{usuario or ""}|{proposito or PROPOSITO_MEDIA}'.encode('utf-8')
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), mensaje, hashlib.sha256).hexdigest()


def media_url(valor, expires_in=None, usuario=None, proposito=None):
    ruta = normalizar_ruta(valor)
    if not ruta:
        return ''
    if expires_in is None:
        expires_in = getattr(settings, 'MEDIA_URL_EXPIRES_IN', 3600)
    if usuario is None:
        usuario = get_usuario_activo_local() or ''
    proposito = proposito or PROPOSITO_MEDIA
    exp = int(time.time()) + int(expires_in)
    firma = _firma(ruta, exp, usuario, proposito)
    return (
        f'{RUTA_API_MEDIA}{quote(ruta, safe="/")}'
        f'?exp={exp}&sig={firma}&usr={quote(str(usuario), safe="")}'
        f'&fin={quote(proposito, safe="")}'
    )


def verificar_firma(ruta, exp, sig, usuario='', proposito=None):
    if not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if exp_int < int(time.time()):
        return False
    proposito = proposito or PROPOSITO_MEDIA
    return hmac.compare_digest(
        _firma(normalizar_ruta(ruta), exp_int, usuario, proposito),
        str(sig),
    )


class DatabaseStorage(Storage):
    def _save(self, name, content):
        if hasattr(content, 'seek'):
            content.seek(0)
        datos = content.read()
        if isinstance(datos, str):
            datos = datos.encode('utf-8')
        declarado = tipo_mime_segmento(getattr(content, 'content_type', None) or '')
        ruta = normalizar_ruta(name)
        limite = getattr(settings, 'MEDIA_MAX_SIZE', TAMANO_MAXIMO_MEDIA)
        if len(datos) > int(limite):
            raise SuspiciousFileOperation('El archivo supera el tamaño máximo permitido.')
        detectado = _detectar_mime(datos, declarado)
        if declarado in MIME_INLINE and declarado != detectado and detectado == 'application/octet-stream':
            raise SuspiciousFileOperation('El contenido del archivo no coincide con el tipo declarado.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM media_blobs WHERE ruta = %s', [ruta])
                valor = datos
                if connection.vendor == 'postgresql':
                    from psycopg2 import Binary
                    valor = Binary(datos)
                cursor.execute(
                    'INSERT INTO media_blobs (ruta, contenido, content_type, tamano) VALUES (%s, %s, %s, %s)',
                    [ruta, valor, detectado, len(datos)],
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
