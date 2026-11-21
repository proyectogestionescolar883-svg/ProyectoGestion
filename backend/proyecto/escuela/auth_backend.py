import threading

from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password

from escuela.models import Usuario, UsuarioRol


_rol_activo = threading.local()


class UsuarioBackend:
    """
    Backend de autenticación que valida contra la tabla 'usuarios'
    de la base de datos sistema_escolar.

    Busca el usuario en la tabla custom, verifica la contraseña hasheada,
    y devuelve (o crea) un django.contrib.auth.User para que DRF/JWT
    funcionen correctamente.
    """

    def authenticate(self, request, username=None, password=None):
        try:
            usuario = Usuario.objects.get(
                usuario=username, estado=True, eliminado=False,
            )
        except Usuario.DoesNotExist:
            return None

        if not check_password(password, usuario.contrasena):
            return None

        django_user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'is_active': True,
            },
        )
        return django_user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


def get_roles_reales(username):
    """Todos los roles asignados al usuario, sin importar el rol activo."""
    try:
        usuario = Usuario.objects.get(usuario=username)
    except Usuario.DoesNotExist:
        return []
    roles = (
        UsuarioRol.objects.filter(id_usuario=usuario)
        .select_related('id_rol')
        .order_by('id_rol__nombre_rol')
    )
    return [ur.id_rol.nombre_rol for ur in roles]


def get_roles_for_usuario(username):
    """Roles vigentes para la operación (R6).

    Si el middleware de rol activo recibió `X-Rol-Activo` y el rol pertenece
    al usuario, se devuelve solo ese rol. Sin ese header se mantienen todos
    los roles para no romper clientes externos.
    """
    roles = get_roles_reales(username)
    rol = getattr(_rol_activo, 'rol', None)
    if rol and rol in roles:
        return [rol]
    return roles


def establecer_rol_activo(username, rol):
    if not username or not rol:
        _rol_activo.rol = None
        return
    _rol_activo.rol = rol if rol in get_roles_reales(username) else None


def limpiar_rol_activo():
    _rol_activo.rol = None
