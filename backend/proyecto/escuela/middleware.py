from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from rest_framework.throttling import SimpleRateThrottle

from escuela.auth_backend import establecer_rol_activo, limpiar_rol_activo
from escuela.usuario_estado import sincronizar_estados_usuarios


class _RutaThrottle(SimpleRateThrottle):
    ruta = ''

    def get_cache_key(self, request, view):
        if request.path.lower().rstrip('/') != self.ruta:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class LoginRateThrottle(_RutaThrottle):
    scope = 'login'
    ruta = '/api/login'


class TokenRefreshRateThrottle(_RutaThrottle):
    scope = 'refresh'
    ruta = '/api/token/refresh'


class RolActivoMiddleware:
    """Fija el rol elegido en el header `X-Rol-Activo` para la request (R6).

    El valor se valida contra los roles reales del usuario autenticado antes
    de guardarlo en el contexto local de hilo, así un cliente no puede
    inventarse un rol.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self._async_mode = iscoroutinefunction(get_response)
        if self._async_mode:
            markcoroutinefunction(self)

    def _establecer(self, request):
        user = getattr(request, 'user', None)
        username = user.username if user is not None and getattr(user, 'is_authenticated', False) else None
        establecer_rol_activo(username, request.headers.get('X-Rol-Activo'))

    def __call__(self, request):
        if self._async_mode:
            return self.__acall__(request)
        self._establecer(request)
        try:
            return self.get_response(request)
        finally:
            limpiar_rol_activo()

    async def __acall__(self, request):
        await sync_to_async(self._establecer, thread_sensitive=True)(request)
        try:
            return await self.get_response(request)
        finally:
            await sync_to_async(limpiar_rol_activo, thread_sensitive=True)()


class UsuarioEstadoProgramadoMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self._async_mode = iscoroutinefunction(get_response)
        if self._async_mode:
            markcoroutinefunction(self)

    def __call__(self, request):
        if self._async_mode:
            return self.__acall__(request)
        sincronizar_estados_usuarios()
        return self.get_response(request)

    async def __acall__(self, request):
        await sync_to_async(sincronizar_estados_usuarios, thread_sensitive=True)()
        return await self.get_response(request)
