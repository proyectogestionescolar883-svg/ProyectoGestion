from escuela.auth_backend import establecer_rol_activo, limpiar_rol_activo
from escuela.usuario_estado import aplicar_programaciones_usuario


METODOS_ESCRITURA = {'POST', 'PUT', 'PATCH', 'DELETE'}


class RolActivoMiddleware:
    """Fija el rol elegido en el header `X-Rol-Activo` para la request (R6).

    El valor se valida contra los roles reales del usuario antes de guardarlo
    en el contexto local de hilo, así un cliente no puede inventarse un rol.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        username = None
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            username = user.username
        establecer_rol_activo(username, request.headers.get('X-Rol-Activo'))
        try:
            return self.get_response(request)
        finally:
            limpiar_rol_activo()


class UsuarioEstadoProgramadoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # R11: las lecturas no cambian estados; aplicar programaciones en cada
        # GET abría una transacción innecesaria en cada request.
        if request.method in METODOS_ESCRITURA:
            aplicar_programaciones_usuario()
        return self.get_response(request)
