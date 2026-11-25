"""Crea usuarios de prueba con un rol real en `usuario_roles`.

Uso:
    SEED_PASSWORD_ADMIN_TEST=... SEED_PASSWORD_DOCENTE_TEST=... \
        python manage.py seed_usuarios

Todas las contraseñas se leen de `SEED_PASSWORD_<USUARIO>` (en mayúsculas,
con los guiones bajos del nombre de usuario). No hay contraseñas por defecto:
si falta alguna variable el comando se detiene antes de escribir nada.

Los usuarios son: admin_test, docente_test, preceptor_test,
jefe_preceptores_test, familia_test, alumno_test, director_test y gperez.
Se crean con `get_or_create`, se les asigna su rol y, para `gperez`, se crea un
perfil `Directivo` con DNI placeholder inválido (`SIN-DNI-gperez`) porque no
hay un DNI real cargado. Ese placeholder no debe usarse como DNI válido.
"""

import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from escuela.models import Directivo, Rol, Usuario, UsuarioRol


USUARIOS_PRUEBA = [
    {'usuario': 'admin_test', 'rol': 'admin'},
    {'usuario': 'docente_test', 'rol': 'docente'},
    {'usuario': 'preceptor_test', 'rol': 'preceptor'},
    {'usuario': 'jefe_preceptores_test', 'rol': 'jefe_preceptores'},
    {'usuario': 'familia_test', 'rol': 'familia'},
    {'usuario': 'alumno_test', 'rol': 'alumno'},
    {'usuario': 'director_test', 'rol': 'director'},
    {
        'usuario': 'gperez',
        'rol': 'director',
        'nombre': 'Guillermo',
        'apellido': 'Pérez',
    },
]


def _variable_password(usuario):
    return 'SEED_PASSWORD_' + usuario.upper()


class Command(BaseCommand):
    help = 'Crea usuarios de prueba con contraseñas desde variables de entorno'

    def handle(self, *args, **options):
        faltantes = [
            data['usuario'] for data in USUARIOS_PRUEBA
            if not os.environ.get(_variable_password(data['usuario']))
        ]
        if faltantes:
            raise CommandError(
                'Faltan variables de entorno: %s'
                % ', '.join(_variable_password(u) for u in faltantes)
            )

        for data in USUARIOS_PRUEBA:
            rol, _ = Rol.objects.get_or_create(nombre_rol=data['rol'])
            contrasena = os.environ[_variable_password(data['usuario'])]

            usuario, created = Usuario.objects.get_or_create(
                usuario=data['usuario'],
                defaults={
                    'contrasena': make_password(contrasena),
                    'estado': True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  Creado: {data['usuario']}"
                ))
            else:
                self.stdout.write(f"  Ya existe: {data['usuario']}")

            if not UsuarioRol.objects.filter(
                id_usuario=usuario, id_rol=rol,
            ).exists():
                UsuarioRol.objects.create(id_usuario=usuario, id_rol=rol)
                self.stdout.write(f"    Rol asignado: {data['rol']}")

            if data['rol'] == 'director' and 'nombre' in data and 'apellido' in data:
                Directivo.objects.get_or_create(
                    id_usuario=usuario,
                    defaults={
                        'nombre': data['nombre'],
                        'apellido': data['apellido'],
                        'dni': 'SIN-DNI-' + data['usuario'],
                        'cargo': 'Director',
                    },
                )
                self.stdout.write(
                    f"    Perfil Directivo creado: {data['nombre']} {data['apellido']}"
                )

        self.stdout.write(self.style.SUCCESS('\nUsuarios de prueba listos.'))
