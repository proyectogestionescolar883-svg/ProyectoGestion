import threading

from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

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
        sincronizar_auth_user(usuario)
        django_user.refresh_from_db(fields=['is_active'])
        return django_user

    def get_user(self, user_id):
        try:
            django_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        usuario = Usuario.objects.filter(usuario=django_user.username).first()
        if usuario and (not usuario.estado or usuario.eliminado):
            return None
        return django_user


def sincronizar_auth_user(usuario):
    if not usuario or not getattr(usuario, 'usuario', None):
        return None
    activo = bool(usuario.estado) and not bool(usuario.eliminado)
    django_user, created = User.objects.get_or_create(
        username=usuario.usuario,
        defaults={'is_active': activo},
    )
    if not created and django_user.is_active != activo:
        django_user.is_active = activo
        django_user.save(update_fields=['is_active'])
    return django_user


class UsuarioJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        django_user = super().get_user(validated_token)
        usuario = Usuario.objects.filter(usuario=django_user.username).first()
        if usuario and (not usuario.estado or usuario.eliminado):
            raise AuthenticationFailed('Usuario deshabilitado o eliminado.', code='user_inactive')
        return django_user


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
    rol_usuario = getattr(_rol_activo, 'username', None)
    if rol and rol_usuario == username and rol in roles:
        return [rol]
    return roles


def get_usuario_activo_local():
    return getattr(_rol_activo, 'username', None)


def establecer_rol_activo(username, rol):
    if not username:
        limpiar_rol_activo()
        return
    _rol_activo.username = username
    _rol_activo.rol = None
    if rol and rol in get_roles_reales(username):
        _rol_activo.rol = rol


def limpiar_rol_activo():
    _rol_activo.username = None
    _rol_activo.rol = None
