"""Verificación de persistencia/rollback/limpieza contra la base MySQL real.

Escenario 14 del plan: verificar con datos FICTICIOS (marcadores únicos)
que el flujo académico del RITE persiste correctamente en la base real
y que, al hacer ROLLBACK, no queda NINGÚN registro ficticio.

SEGURIDAD:
- Todo corre dentro de una única transacción (transaction.atomic).
- Al final se fuerza `set_rollback(True)`: no se escribe nada definitivo.
- Después del rollback se comprueba por SQL directo que los marcadores
  ficticios ya no existen en ninguna tabla involucrada.

USO:
    python manage.py verificar_rite_mysql
"""

import uuid
from datetime import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from escuela.academico import (
    consolidar_historial_alumno,
    detectar_superposiciones_y_bloqueos,
)
from escuela.models import (
    ActividadMateriaAdeudada,
    Alumno,
    Calificacion,
    CicloLectivo,
    Curso,
    CursoMateria,
    Docente,
    HistorialAcademico,
    MateriaAdeudada,
    Modulos,
    PeriodoEvaluacion,
    RecursadaMateria,
    ResultadoActividadAdeudada,
    Rol,
    Usuario,
    UsuarioRol,
)



def _dni_libre(prefijo):
    n = 0
    while True:
        dni = f'{prefijo}{n:03d}'
        if not Alumno.objects.filter(dni=dni).exists():
            return dni
        n += 1


def _filas(tabla, where, params):
    with connection.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM `{tabla}` WHERE {where}', params)
        return cur.fetchone()[0]


class Command(BaseCommand):
    help = 'Verifica persistencia, rollback y limpieza en MySQL real con datos ficticios.'

    def handle(self, *args, **options):
        out = self.stdout.write
        anio = 2100
        prefijo_dni = '98800'
        marca = uuid.uuid4().hex[:8]
        apellido_marca = f'FICTICIO_{marca}'
        materia_prefijo = f'E2E-{marca}-'
        curso_nombre = f'E2E-CURSO-{marca}'
        modulo_nombre = f'E2E-M1-{marca}'
        periodo_nombre = f'E2E-1C-{marca}'
        nombres_materia = [
            f'{materia_prefijo}Matematica',
            f'{materia_prefijo}Lengua',
            f'{materia_prefijo}Historia',
        ]
        usuario_admin = f'e2e_admin_{marca}'
        hosts = settings.ALLOWED_HOSTS or ['localhost']
        fallo_transaccion = False

        out('=' * 72)
        out('Verificación en MySQL real (sistema_escolar) con ROLLBACK final')
        out(f'  Anio lectivo de prueba: {anio}  |  Marcador: {apellido_marca}')
        out('=' * 72)

        try:
            with transaction.atomic():
                out('\n[1/5] Creando datos ficticios dentro de la transacción...')

                ciclo = CicloLectivo.objects.create(anio=anio)
                curso = Curso.objects.create(
                    nombre_curso=curso_nombre, id_ciclo=ciclo, activo=True,
                )
                curso_id = curso.id_curso

                doc = Docente.objects.create(
                    nombre='Docente', apellido=apellido_marca, dni=_dni_libre(prefijo_dni),
                )

                cms = {}
                for n in nombres_materia:
                    from escuela.models import Materia
                    materia = Materia.objects.create(nombre_materia=n)
                    cm = CursoMateria.objects.create(
                        id_curso=curso, id_materia=materia, id_docente=doc, activo=True,
                    )
                    cms[n] = (materia, cm)

                alumno = Alumno.objects.create(
                    nombre='Lucas', apellido=apellido_marca,
                    dni=_dni_libre(prefijo_dni), id_curso=curso,
                )
                alumno_id = alumno.id_alumno

                periodos = PeriodoEvaluacion.objects.filter(estado=True).order_by('orden_periodo')
                p1 = periodos.filter(orden_periodo=1).first()
                p2 = periodos.filter(orden_periodo=2).first()
                if p1 is None or p2 is None:
                    raise RuntimeError('No hay periodos de evaluacion activos (1 y 2) en la base real.')

                materias_names = list(cms)
                for n in materias_names[:2]:  # dos materias desaprobadas
                    _, cm = cms[n]
                    Calificacion.objects.create(
                        id_alumno=alumno, id_curso_materia=cm, id_docente=doc,
                        id_periodo=p1, nota_numerica=4,
                    )
                    Calificacion.objects.create(
                        id_alumno=alumno, id_curso_materia=cm, id_docente=doc,
                        id_periodo=p2, nota_numerica=4,
                    )
                _, cm_aprobada = cms[materias_names[2]]  # una materia aprobada
                Calificacion.objects.create(
                    id_alumno=alumno, id_curso_materia=cm_aprobada, id_docente=doc,
                    id_periodo=p1, nota_numerica=8,
                )
                Calificacion.objects.create(
                    id_alumno=alumno, id_curso_materia=cm_aprobada, id_docente=doc,
                    id_periodo=p2, nota_numerica=9,
                )

                out(f'    Alumno {alumno_id} / curso {curso_id} / docentes/materias creados.')

                out('[2/5] Ejecutando lógica académica real (cierre por alumno)...')
                consolidar_historial_alumno(alumno, anio)

                out('[3/5] Verificación de PERSISTENCIA por SQL directo...')
                checks = [
                    ('alumnos', 'id_alumno=%s AND apellido=%s', 1, (alumno_id, apellido_marca)),
                    ('cursos', 'id_curso=%s AND nombre_curso=%s', 1, (curso_id, curso_nombre)),
                    ('calificaciones', 'id_alumno=%s', 6, (alumno_id,)),
                    ('historial_academico', 'id_alumno=%s', 3, (alumno_id,)),
                    ('materias_adeudadas', "id_alumno=%s AND tipo_deuda='PREVIA' AND estado='ADEUDADA'", 2, (alumno_id,)),
                    ('historial_cursos_alumno', 'id_alumno=%s', 0, (alumno_id,)),
                ]
                ok_persistencia = True
                for tabla, where, esperado, params in [
                    c if len(c) == 4 else (c[0], c[1], c[2], ())
                    for c in checks
                ]:
                    total = _filas(tabla, where, params)
                    estado = 'OK' if total == esperado else 'DIFERENTE'
                    if total != esperado:
                        ok_persistencia = False
                    out(f'    {estado}: {tabla} = {total} (esperado {esperado})')

                if not ok_persistencia:
                    raise RuntimeError('La persistencia por SQL no coincide con lo esperado.')

                out('[4/5] Endpoint real /api/boletin-academico/...')
                from django.contrib.auth.models import User as DjangoUser
                from rest_framework.test import APIClient
                from rest_framework_simplejwt.tokens import RefreshToken

                from django.contrib.auth.hashers import make_password

                rol_admin, _ = Rol.objects.get_or_create(nombre_rol='admin')
                usr = Usuario.objects.create(
                    usuario=usuario_admin,
                    contrasena=make_password(uuid.uuid4().hex),
                    estado=True,
                )
                UsuarioRol.objects.create(id_usuario=usr, id_rol=rol_admin)
                duser, _ = DjangoUser.objects.get_or_create(username=usuario_admin)
                token = str(RefreshToken.for_user(duser).access_token)

                client = APIClient()
                client.credentials(
                    HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_HOST=hosts[0],
                )
                resp = client.get(f'/api/boletin-academico/{alumno_id}/')
                if resp.status_code != 200:
                    raise RuntimeError(f'RITE endpoint devolvio {resp.status_code}: {resp.content[:200]}')
                data = resp.json()
                if len(data['previas']) != 2:
                    raise RuntimeError(f'RITE: se esperaban 2 previas, llego {len(data["previas"])}')
                if len(data['recursadas']) != 0 or len(data['intensificaciones_1c']) != 0:
                    raise RuntimeError('RITE: no deberia haber recursadas ni intensificaciones 1C.')
                out('    RITE OK: 2 previas, 0 recursadas, 0 intensificaciones 1C.')

                out('    Previas del RITE:')
                for p in data['previas']:
                    out(f"      - {p['materia']} | {p['anio']} | {p['rendiciones']!r} | {p['calificacion_final']!r}")

                out('    Rendición de previa (endpoint real rendir/)...')
                ma = MateriaAdeudada.objects.get(id_alumno=alumno, id_materia=cms[materias_names[0]][0])
                resp = client.post(
                    f'/api/materias-adeudadas/{ma.id_materia_adeudada}/rendir/',
                    {'nota': 8, 'periodo': 'MARZO', 'anio_rendicion': anio + 1,
                     'id_docente': doc.id_docente},
                    format='json',
                )
                if resp.status_code != 200:
                    raise RuntimeError(f'rendir devolvio {resp.status_code}: {resp.content[:200]}')
                out(f"    Rendir OK: {resp.json()['estado']}")

                out('    Verificación por SQL de la rendición...')
                checks_rend = [
                    ('rendiciones_materias_adeudadas', 'id_alumno=%s', 1, (alumno_id,)),
                    ('registro_rendiciones_previas', 'id_alumno=%s', 1, (alumno_id,)),
                    ('materias_adeudadas', "id_alumno=%s AND id_materia=%s AND estado='APROBADA'", 1, (alumno_id, ma.id_materia_id)),
                ]
                for tabla, where, esperado, params in checks_rend:
                    total = _filas(tabla, where, params)
                    estado = 'OK' if total == esperado else 'DIFERENTE'
                    if total != esperado:
                        ok_persistencia = False
                    out(f'    {estado}: {tabla} = {total} (esperado {esperado})')
                if not ok_persistencia:
                    raise RuntimeError('Persistencia de rendición no coincide.')

                out('    Superposición horaria y bloqueo...')
                mod = Modulos.objects.create(
                    nombre=modulo_nombre, hora_inicio=time(8, 0), hora_fin=time(9, 0),
                )
                cm_rec = cms[materias_names[0]][1]
                cm_bloq = cms[materias_names[2]][1]
                RecursadaMateria.objects.create(
                    id_alumno=alumno, id_materia=cms[materias_names[0]][0],
                    id_curso_origen=curso, id_curso_recursada=curso,
                    anio_inicio=anio, estado='ACTIVA', fecha_registro=timezone.now(),
                )
                from escuela.models import Horario
                Horario.objects.create(id_curso_materia=cm_rec, dia_semana='Lunes', id_modulo=mod)
                Horario.objects.create(id_curso_materia=cm_bloq, dia_semana='Lunes', id_modulo=mod)
                detectar_superposiciones_y_bloqueos(alumno, anio)

                checks_bloq = [
                    ('bloqueos_horarios_alumno', 'id_alumno=%s', 1, (alumno_id,)),
                    ('situaciones_materias_alumno', "id_alumno=%s AND situacion='BLOQUEADA'", 1, (alumno_id,)),
                ]
                for tabla, where, esperado, params in [
                    c if len(c) == 4 else (c[0], c[1], c[2], ()) for c in checks_bloq
                ]:
                    total = _filas(tabla, where, params)
                    estado = 'OK' if total == esperado else 'DIFERENTE'
                    if total != esperado:
                        ok_persistencia = False
                    out(f'    {estado}: {tabla} = {total} (esperado {esperado})')
                if not ok_persistencia:
                    raise RuntimeError('Persistencia de bloqueo no coincide.')

                resp = client.get(f'/api/boletin-academico/{alumno_id}/')
                bloq = resp.json()['bloqueos_por_materia']
                out(f"    Bloqueo visible en RITE: {list(bloq)}")
                if not any(v.get('bloqueada') for v in bloq.values()):
                    raise RuntimeError('El RITE no refleja la materia bloqueada.')

                out('\n[5/5] ROLLBACK...')
                transaction.set_rollback(True)

        except Exception as exc:  # noqa: BLE001
            fallo_transaccion = True
            out(f'\nERROR: {exc}')
            out('(el bloque atomic() ya descartó la transacción por el error)')

        out('\nVerificación de LIMPIEZA (después del rollback) por SQL directo:')
        limpieza_checks = [
            ('alumnos', "apellido=%s", (apellido_marca,)),
            ('cursos', 'nombre_curso=%s', (curso_nombre,)),
            ('curso_materia', "id_curso IN (SELECT id_curso FROM cursos WHERE nombre_curso=%s)", (curso_nombre,)),
            ('docentes', "apellido=%s", (apellido_marca,)),
            ('historial_academico', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('materias_adeudadas', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('historial_cursos_alumno', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('recursadas_materias', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('bloqueos_horarios_alumno', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('situaciones_materias_alumno', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('rendiciones_materias_adeudadas', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('registro_rendiciones_previas', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('calificaciones', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('actividades_materias_adeudadas', "id_docente IN (SELECT id_docente FROM docentes WHERE apellido=%s)", (apellido_marca,)),
            ('resultados_actividades_adeudadas', "id_alumno IN (SELECT id_alumno FROM alumnos WHERE apellido=%s)", (apellido_marca,)),
            ('periodos_evaluacion', 'nombre_periodo=%s', (periodo_nombre,)),
            ('modulos', 'nombre=%s', (modulo_nombre,)),
            ('usuarios', 'usuario=%s', (usuario_admin,)),
            ('usuario_roles', "id_usuario IN (SELECT id_usuario FROM usuarios WHERE usuario=%s)", (usuario_admin,)),
            ('auth_user', 'username=%s', (usuario_admin,)),
        ]
        limpio = True
        for tabla, where, params in limpieza_checks:
            total = _filas(tabla, where, params)
            estado = 'LIMPIO' if total == 0 else 'SUCIO'
            if total != 0:
                limpio = False
            out(f'    {estado}: {tabla} = {total}')

        materias_restantes = _filas(
            'materias',
            'nombre_materia LIKE %s', (materia_prefijo + '%',),
        )
        estado_mat = 'LIMPIO' if materias_restantes == 0 else 'SUCIO'
        if materias_restantes != 0:
            limpio = False
        out(f'    {estado_mat}: materias = {materias_restantes}')

        if limpio and not fallo_transaccion:
            out('\nRESULTADO: LIMPIEZA VERIFICADA (0 registros ficticios restantes).')
        else:
            out('\nRESULTADO: QUEDARON REGISTROS FICTICIOS O FALLÓ LA TRANSACCIÓN.')
            raise SystemExit(1)

    @staticmethod
    def assert_equal_previas(out, data, esperado):
        total = len(data['previas'])
        estado = 'OK' if total == esperado else 'DIFERENTE'
        if total != esperado:
            raise RuntimeError(f'previas devuelve {total}, esperado {esperado}')
        out(f'    {estado}: RITE previas = {total} (esperado {esperado})')
