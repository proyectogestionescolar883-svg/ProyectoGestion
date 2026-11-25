"""Verificación del flujo mínimo de Administración → Configuración.

Recorre la API con un usuario administrador y comprueba, de punta a punta, que
los cinco catálogos se pueden administrar sin tocar SQL:

    1. Crear un ciclo lectivo (+ rechazar año duplicado / de 2 dígitos).
    2. Crear un curso que usa ese ciclo.
    3. Crear un módulo horario (+ rechazar hora_fin < hora_inicio).
    4. Crear un período de evaluación (+ rechazar orden duplicado).
    5. Confirmar que los cinco estados base existen y están protegidos.
    6. Crear un tipo de acta.
    7. Confirmar que el ciclo nuevo ya aparece en el listado que alimenta los
       select del resto de la aplicación.

Además comprueba que las reglas de borrado en uso responden HTTP 400 y no 500.

A diferencia de `manage.py test`, este comando corre contra la base REAL
(como `verificar_esquema` y los demás comandos de diagnóstico), así que crea y
borra datos de prueba. Cada corrida genera una marca única y la incluye en los
nombres creados; la limpieza se hace solo por esa marca o por los IDs creados
en la corrida. Si se interrumpe, se puede limpiar con:

    python manage.py verificar_flujo_configuracion --limpiar --marca MARCA

Sin `--marca` ni IDs de una corrida, `--limpiar` no borra nada y lo avisa.

Uso:
    python manage.py verificar_flujo_configuracion
    python manage.py verificar_flujo_configuracion --anio 2099 --limpiar --marca MARCA
"""
import json
import re
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken

from escuela.models import (
    CicloLectivo,
    Curso,
    CursoMateria,
    Horario,
    Materia,
    Modulos,
    PeriodoEvaluacion,
    Rol,
    TipoActa,
    Usuario,
    UsuarioRol,
)

BASE = '/api'
ESTADOS_BASE_ESPERADOS = ['Presente', 'Ausente', 'Tarde', 'Retirado', 'Justificado']

# Datos de la prueba negativa de permisos: debe ser rechazado por permiso
# (403) ANTES de que cualquier validación del serializer pueda aceptarlo, así que
# el cuerpo es deliberadamente válido en todos los catálogos.
DATOS_SIN_PERMISO = {
    'nombre': 'No deberíaCrearse',
    'nombre_tipo': 'No deberíaCrearse',
    'nombre_periodo': 'No deberíaCrearse',
    'nombre_estado': 'No deberíaCrearse',
    'orden_periodo': 99,
    'hora_inicio': '07:00',
    'hora_fin': '07:30',
    'anio': 2098,
}


class Command(BaseCommand):
    help = 'Verifica el flujo mínimo de Configuración contra la base real y limpia lo que crea.'

    def add_arguments(self, parser):
        parser.add_argument('--anio', type=int, default=2099,
                            help='Año del ciclo lectivo de prueba (por defecto 2099).')
        parser.add_argument('--usuario', default='adminsecundaria7',
                            help='Usuario administrador con el que se prueba (por defecto adminsecundaria7).')
        parser.add_argument('--limpiar', action='store_true',
                            help='Solo borra los datos de una corrida anterior y sale.')
        parser.add_argument('--marca', default=None,
                            help='Marca única de una corrida anterior, para --limpiar.')

    def handle(self, *args, **options):
        anio = options['anio']
        marca = options['marca'] or uuid.uuid4().hex[:10]
        if not re.fullmatch(r'[0-9a-fA-F]{1,16}', marca):
            raise CommandError(
                '--marca debe ser hexadecimal de 1 a 16 caracteres: %s' % marca
            )
        self.stdout.write('Marca de esta corrida: %s' % marca)

        if options['limpiar']:
            borrados = self._limpiar(anio, marca)
            if borrados:
                self.stdout.write(self.style.SUCCESS(
                    'Datos de prueba borrados: %d fila(s).' % borrados))
            return

        fallos, creado = self._recorrer(anio, options['usuario'], marca)
        self._limpiar(anio, marca, creado)

        pendientes = {k: v for k, v in self._pendientes(anio, marca, creado).items() if v}
        if pendientes:
            self.stdout.write(self.style.ERROR(
                'Quedaron datos de prueba: %s' % pendientes))
            fallos += 1
        else:
            self.stdout.write(self.style.SUCCESS(
                'Base limpia: solo permanecen los estados base del sistema.'))

        if fallos:
            self.stdout.write(self.style.ERROR('RESULTADO: %d verificación(es) fallida(s)' % fallos))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('RESULTADO: todas las verificaciones OK'))

    # ------------------------------------------------------------------

    def _host(self):
        return settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'

    def _titulo(self, texto):
        self.stdout.write('\n' + '=' * 72)
        self.stdout.write(texto)
        self.stdout.write('=' * 72)

    def _pedir(self, cli, metodo, ruta, **kw):
        r = getattr(cli, metodo)(ruta, **kw)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.content[:200].decode('utf-8', 'replace')

    def _ok(self, etiqueta, codigo, esperado, cuerpo=None, detalle=False):
        bien = codigo in esperado
        self.stdout.write('  [%s] %s: HTTP %s (esperado %s)'
                          % ('OK   ' if bien else 'FALLA', etiqueta, codigo, sorted(esperado)))
        if not bien or detalle:
            self.stdout.write('        cuerpo: %s' % str(cuerpo)[:300])
        return bien

    def _recorrer(self, anio, nombre_usuario, marca):
        fallos = 0
        admin = User.objects.filter(username=nombre_usuario).first()
        if not admin:
            self.stderr.write(self.style.ERROR(
                'No existe el usuario %s en auth_user.' % nombre_usuario))
            return 1, {}

        # `test.Client` usa el host `testserver`, que no está en ALLOWED_HOSTS
        # (el proyecto define hosts reales), así que se fija uno válido.
        cli = Client(
            HTTP_HOST=self._host(),
            HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(admin).access_token),
        )
        cli_anonimo = Client(HTTP_HOST=self._host())
        creado = {}

        # -- 1) ciclo lectivo -------------------------------------------
        self._titulo('1) Crear un ciclo lectivo')
        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/ciclos-lectivos/',
                                  data=json.dumps({'anio': anio, 'estado': True}),
                                  content_type='application/json')
        fallos += not self._ok('crear ciclo', cod, {201}, cuerpo)
        if cod != 201:
            return fallos, creado
        creado['ciclo'] = cuerpo['id_ciclo']

        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/ciclos-lectivos/',
                                  data=json.dumps({'anio': anio, 'estado': True}),
                                  content_type='application/json')
        fallos += not self._ok('rechazar año duplicado', cod, {400}, cuerpo)

        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/ciclos-lectivos/',
                                  data=json.dumps({'anio': 25, 'estado': True}),
                                  content_type='application/json')
        fallos += not self._ok('rechazar año de 2 dígitos', cod, {400}, cuerpo)

        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/ciclos-lectivos/',
                                  data=json.dumps({'anio': 2030,
                                                   'fecha_inicio': '2030-03-01',
                                                   'fecha_fin': '2030-01-01'}),
                                  content_type='application/json')
        fallos += not self._ok('rechazar fecha_fin anterior al inicio', cod, {400}, cuerpo)

        # -- 2) curso que usa el ciclo ----------------------------------
        self._titulo('2) Crear un curso que usa ese ciclo')
        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/cursos/',
                                   data=json.dumps({
                                       'nombre_curso': f'{anio}°1 {marca}',
                                       'id_ciclo': creado['ciclo'],
                                      'activo': True,
                                  }),
                                  content_type='application/json')
        fallos += not self._ok('crear curso', cod, {201}, cuerpo)
        if cod == 201:
            creado['curso'] = cuerpo['id_curso']
            self.stdout.write('        turno calculado por el backend: %r'
                              % cuerpo.get('turno'))

        # -- 3) módulo horario ------------------------------------------
        self._titulo('3) Crear un módulo horario')
        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/modulos/',
                                  data=json.dumps({'nombre': f'Módulo Prueba {marca}',
                                                    'hora_inicio': '07:30',
                                                   'hora_fin': '08:10'}),
                                  content_type='application/json')
        fallos += not self._ok('crear módulo', cod, {201}, cuerpo)
        if cod == 201:
            creado['modulo'] = cuerpo['id_modulo']

        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/modulos/',
                                  data=json.dumps({'nombre': f'Módulo Invertido {marca}',
                                                    'hora_inicio': '08:10',
                                                   'hora_fin': '07:30'}),
                                  content_type='application/json')
        fallos += not self._ok('rechazar hora_fin anterior a hora_inicio', cod, {400}, cuerpo)

        # -- 4) período de evaluación ----------------------------------
        self._titulo('4) Crear un período de evaluación')
        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/periodos/',
                                  data=json.dumps({'nombre_periodo': f'1er Cuatrimestre {marca}',
                                                    'orden_periodo': 1}),
                                  content_type='application/json')
        fallos += not self._ok('crear período', cod, {201}, cuerpo)
        if cod == 201:
            creado['periodo'] = cuerpo['id_periodo']

        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/periodos/',
                                  data=json.dumps({'nombre_periodo': f'Repetido {marca}',
                                                    'orden_periodo': 1}),
                                  content_type='application/json')
        fallos += not self._ok('rechazar orden duplicado', cod, {400}, cuerpo)

        # -- 5) estados de asistencia base ------------------------------
        self._titulo('5) Confirmar que los estados base existen y están protegidos')
        cod, cuerpo = self._pedir(cli, 'get', f'{BASE}/estados-asistencia/')
        fallos += not self._ok('listar estados', cod, {200})
        if cod == 200:
            nombres = sorted(e['nombre_estado'] for e in cuerpo)
            esperados = sorted(ESTADOS_BASE_ESPERADOS)
            if nombres != esperados:
                self.stdout.write(self.style.ERROR(
                    '  [FALLA] estados = %s, esperado %s' % (nombres, esperados)))
                fallos += 1
            else:
                self.stdout.write('  [OK   ] los cinco estados base están cargados')

            base = next((e for e in cuerpo if e['nombre_estado'] == 'Presente'), None)
            if base:
                fallos += not self._ok('"Presente" viene marcado como es_base',
                                       200 if base.get('es_base') else 500, {200}, base)
                cod, cuerpo = self._pedir(
                    cli, 'delete',
                    f"{BASE}/estados-asistencia/{base['id_estado_asistencia']}/")
                fallos += not self._ok('no se puede eliminar un estado base', cod, {400}, cuerpo)
                self.stdout.write('        mensaje: %s' % str(cuerpo)[:200])
                cod, cuerpo = self._pedir(
                    cli, 'patch',
                    f"{BASE}/estados-asistencia/{base['id_estado_asistencia']}/",
                    data=json.dumps({'nombre_estado': 'Presente_old'}),
                    content_type='application/json')
                fallos += not self._ok('no se puede renombrar un estado base',
                                       cod, {400}, cuerpo)

        # -- 6) tipo de acta --------------------------------------------
        self._titulo('6) Crear un tipo de acta')
        cod, cuerpo = self._pedir(cli, 'post', f'{BASE}/tipos-acta/',
                                  data=json.dumps({'nombre_tipo': f'Acta de evaluación {marca}'}),
                                  content_type='application/json')
        fallos += not self._ok('crear tipo de acta', cod, {201}, cuerpo)
        if cod == 201:
            creado['tipo_acta'] = cuerpo['id_tipo_acta']

        # -- 7) los catálogos ya están disponibles ---------------------
        self._titulo('7) El ciclo nuevo ya aparece en el listado de los select')
        cod, cuerpo = self._pedir(cli, 'get', f'{BASE}/ciclos-lectivos/')
        fallos += not self._ok('listar ciclos', cod, {200})
        if cod == 200:
            anios = [c['anio'] for c in cuerpo]
            if anio not in anios:
                self.stdout.write(self.style.ERROR(
                    '  [FALLA] el listado no incluye %s (trae %s)' % (anio, anios)))
                fallos += 1
            else:
                self.stdout.write('  [OK   ] el listado por defecto ya incluye %s' % anio)

        # -- reglas de borrado en uso (400, nunca 500) ------------------
        self._titulo('Reglas de borrado en uso: HTTP 400, nunca 500')
        cod, cuerpo = self._pedir(cli, 'delete',
                                  f"{BASE}/ciclos-lectivos/{creado['ciclo']}/")
        fallos += not self._ok('desactivar ciclo con un curso activo', cod, {400}, cuerpo)
        self.stdout.write('        mensaje: %s' % str(cuerpo)[:250])

        if creado.get('modulo') and creado.get('curso'):
            materia = Materia.objects.create(
                nombre_materia=f'Materia Prueba {marca}', estado=True,
            )
            creado['materia'] = materia.id_materia
            cm = CursoMateria.objects.create(
                id_curso_id=creado['curso'], id_materia=materia,
                estado=True, activo=True,
            )
            creado['curso_materia'] = cm.id_curso_materia
            horario = Horario.objects.create(
                id_curso_materia=cm, id_modulo_id=creado['modulo'],
                dia_semana='Lunes', aula=f'Aula Prueba {marca}',
            )
            creado['horario'] = horario.id_horario
            cod, cuerpo = self._pedir(cli, 'delete',
                                      f"{BASE}/modulos/{creado['modulo']}/")
            fallos += not self._ok('eliminar módulo con un horario asignado',
                                   cod, {400}, cuerpo)
            self.stdout.write('        mensaje: %s' % str(cuerpo)[:250])

        # -- permisos ---------------------------------------------------
        # El caso positivo ya está cubierto: los cinco catálogos se crearon
        # más arriba con este mismo token de administrador (todos HTTP 201).
        # Falta comprobar que los demás roles NO pueden escribir.
        self._titulo('Permisos: escritura restringida a admin/director')
        # El backend de autenticación crea la fila de `auth_user` correspondiente
        # en el primer login, así que un usuario de `usuarios` que nunca entré
        # puede no tenerla. Se replica ese `get_or_create` para poder firmar un
        # token; si la fila no existía, se borra al terminar para no dejar
        # rastro. Los roles se resuelven por `usuario` + `usuario_roles`, así que
        # el token refleja los permisos reales de la persona.
        rol_preceptor, _ = Rol.objects.get_or_create(nombre_rol='preceptor')
        usuario_preceptor, creado_usuario = Usuario.objects.get_or_create(
            usuario='luciapreceptora',
            defaults={'contrasena': 'sin-uso', 'estado': True},
        )
        vinculo_creado = False
        if not UsuarioRol.objects.filter(
            id_usuario=usuario_preceptor, id_rol=rol_preceptor,
        ).exists():
            UsuarioRol.objects.create(
                id_usuario=usuario_preceptor, id_rol=rol_preceptor,
            )
            vinculo_creado = True

        preceptor, creado_preceptor = User.objects.get_or_create(
            username='luciapreceptora', defaults={'is_active': True},
        )
        if creado_usuario:
            creado['usuario_preceptor'] = usuario_preceptor.pk
        if creado_usuario or creado_preceptor:
            creado['usuario_preceptor_auth'] = preceptor.pk
        try:
            cli_preceptor = Client(
                HTTP_HOST=self._host(),
                HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(preceptor).access_token),
            )
            for etiqueta, ruta in (
                ('crear ciclo lectivo', 'ciclos-lectivos/'),
                ('crear módulo horario', 'modulos/'),
                ('crear período de evaluación', 'periodos/'),
                ('crear estado de asistencia', 'estados-asistencia/'),
                ('crear tipo de acta', 'tipos-acta/'),
            ):
                cod, cuerpo = self._pedir(
                    cli_preceptor, 'post', f'{BASE}/{ruta}',
                    data=json.dumps(DATOS_SIN_PERMISO),
                    content_type='application/json',
                )
                fallos += not self._ok(f'preceptor no puede {etiqueta}', cod, {403}, cuerpo)
        finally:
            if vinculo_creado:
                UsuarioRol.objects.filter(
                    id_usuario_id=usuario_preceptor.pk, id_rol_id=rol_preceptor.pk,
                ).delete()
            if creado_usuario:
                Usuario.objects.filter(pk=usuario_preceptor.pk).delete()
            if creado.get('usuario_preceptor_auth'):
                User.objects.filter(pk=creado['usuario_preceptor_auth']).delete()

        cod, cuerpo = self._pedir(cli_anonimo, 'get', f'{BASE}/ciclos-lectivos/')
        fallos += not self._ok('anónimo no puede listar (401)', cod, {401}, cuerpo)
        cod, cuerpo = self._pedir(cli_anonimo, 'post', f'{BASE}/ciclos-lectivos/',
                                  data=json.dumps({'anio': anio}),
                                  content_type='application/json')
        fallos += not self._ok('anónimo no puede crear (401)', cod, {401}, cuerpo)

        return fallos, creado

    # ------------------------------------------------------------------

    def _ids_de_prueba(self, anio, marca, creado=None):
        creado = creado or {}

        def ids(clave):
            valor = creado.get(clave)
            if valor is None:
                return set()
            if isinstance(valor, (list, tuple, set)):
                return {int(v) for v in valor}
            return {int(valor)}

        ciclos = ids('ciclo')
        cursos = ids('curso')
        modulos = ids('modulo')
        periodos = ids('periodo')
        tipos_acta = ids('tipo_acta')
        materias = ids('materia')
        cms = ids('curso_materia')
        horarios = ids('horario')

        if marca and not any(creado.values()):
            cursos_marcados = list(
                Curso.all_objects.filter(nombre_curso__contains=marca)
                .values_list('id_curso', 'id_ciclo_id')
            )
            cursos.update(curso for curso, _ in cursos_marcados)
            ciclos.update(ciclo for _, ciclo in cursos_marcados if ciclo)
            modulos.update(
                Modulos.objects.filter(nombre__contains=marca)
                .values_list('id_modulo', flat=True)
            )
            periodos.update(
                PeriodoEvaluacion.all_objects.filter(nombre_periodo__contains=marca)
                .values_list('id_periodo', flat=True)
            )
            tipos_acta.update(
                TipoActa.objects.filter(nombre_tipo__contains=marca)
                .values_list('id_tipo_acta', flat=True)
            )
            materias.update(
                Materia.all_objects.filter(nombre_materia__contains=marca)
                .values_list('id_materia', flat=True)
            )
        if cursos:
            ciclos.update(
                Curso.all_objects.filter(id_curso__in=cursos)
                .values_list('id_ciclo_id', flat=True)
            )
        if ciclos:
            cursos.update(
                Curso.all_objects.filter(id_ciclo_id__in=ciclos)
                .values_list('id_curso', flat=True)
            )
        if cursos:
            cms.update(
                CursoMateria.all_objects.filter(id_curso_id__in=cursos)
                .values_list('id_curso_materia', flat=True)
            )
        if materias:
            cms.update(
                CursoMateria.all_objects.filter(id_materia_id__in=materias)
                .values_list('id_curso_materia', flat=True)
            )
        if cms:
            horarios.update(
                Horario.objects.filter(id_curso_materia_id__in=cms)
                .values_list('id_horario', flat=True)
            )
        return {
            'ciclos': ciclos, 'cursos': cursos, 'modulos': modulos,
            'periodos': periodos, 'tipos_acta': tipos_acta,
            'materias': materias, 'cms': cms, 'horarios': horarios,
        }

    def _limpiar(self, anio, marca=None, creado=None):
        from escuela.models import Acta, Calificacion, ComunicadoAlcance

        ids = self._ids_de_prueba(anio, marca, creado)
        if not any(ids.values()):
            self.stdout.write(self.style.WARNING(
                'No se pasó --marca ni hay IDs de una corrida: no se borró nada.'
            ))
            return 0

        borrados = 0
        if ids['horarios']:
            borrados += Horario.objects.filter(
                id_horario__in=ids['horarios'],
            ).delete()[0]
        if ids['cms']:
            borrados += CursoMateria.all_objects.filter(
                id_curso_materia__in=ids['cms'],
            ).delete()[0]
        if ids['cursos']:
            borrados += Curso.all_objects.filter(
                id_curso__in=ids['cursos'],
            ).delete()[0]

        ciclos_a_borrar = set(ids['ciclos'])
        if ciclos_a_borrar:
            con_cursos = set(
                Curso.all_objects.filter(id_ciclo_id__in=ciclos_a_borrar)
                .values_list('id_ciclo_id', flat=True).distinct()
            )
            ciclos_a_borrar -= con_cursos
        if ciclos_a_borrar:
            borrados += ComunicadoAlcance.objects.filter(
                id_ciclo_id__in=ciclos_a_borrar,
            ).delete()[0]
            borrados += CicloLectivo.all_objects.filter(
                id_ciclo__in=ciclos_a_borrar,
            ).delete()[0]

        materias_a_borrar = set(ids['materias'])
        if materias_a_borrar:
            con_cm = set(
                CursoMateria.all_objects.filter(id_materia_id__in=materias_a_borrar)
                .values_list('id_materia_id', flat=True).distinct()
            )
            materias_a_borrar -= con_cm
        if materias_a_borrar:
            borrados += Materia.objects.filter(
                id_materia__in=materias_a_borrar,
            ).delete()[0]

        modulos_a_borrar = set(ids['modulos'])
        if modulos_a_borrar:
            con_horarios = set(
                Horario.objects.filter(id_modulo_id__in=modulos_a_borrar)
                .values_list('id_modulo_id', flat=True).distinct()
            )
            modulos_a_borrar -= con_horarios
        if modulos_a_borrar:
            borrados += Modulos.objects.filter(
                id_modulo__in=modulos_a_borrar,
            ).delete()[0]

        periodos_a_borrar = set(ids['periodos'])
        if periodos_a_borrar:
            con_notas = set(
                Calificacion.all_objects.filter(id_periodo_id__in=periodos_a_borrar)
                .values_list('id_periodo_id', flat=True).distinct()
            )
            periodos_a_borrar -= con_notas
        if periodos_a_borrar:
            borrados += PeriodoEvaluacion.all_objects.filter(
                id_periodo__in=periodos_a_borrar,
            ).delete()[0]

        tipos_a_borrar = set(ids['tipos_acta'])
        if tipos_a_borrar:
            con_actas = set(
                Acta.all_objects.filter(id_tipo_acta_id__in=tipos_a_borrar)
                .values_list('id_tipo_acta_id', flat=True).distinct()
            )
            tipos_a_borrar -= con_actas
        if tipos_a_borrar:
            borrados += TipoActa.objects.filter(
                id_tipo_acta__in=tipos_a_borrar,
            ).delete()[0]

        return borrados

    def _pendientes(self, anio, marca=None, creado=None):
        ids = self._ids_de_prueba(anio, marca, creado)
        return {
            'ciclos_lectivos': CicloLectivo.all_objects.filter(
                id_ciclo__in=ids['ciclos']).count(),
            'cursos': Curso.all_objects.filter(id_curso__in=ids['cursos']).count(),
            'materias': Materia.objects.filter(id_materia__in=ids['materias']).count(),
            'modulos': Modulos.objects.filter(id_modulo__in=ids['modulos']).count(),
            'periodos': PeriodoEvaluacion.all_objects.filter(
                id_periodo__in=ids['periodos']).count(),
            'tipos_acta': TipoActa.objects.filter(
                id_tipo_acta__in=ids['tipos_acta']).count(),
        }
