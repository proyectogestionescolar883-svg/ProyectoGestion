"""Correcciones puntuales de datos de la auditoría (bloque B; registro histórico).

Las sentencias van parametrizadas y los valores que identifican personas (DNI,
usuario, correo) o registros sin clave natural estable (eventos) se toman de
variables de entorno `CORRECCION_0012_*`. Si no se definen, esa corrección se
omite. No hay PKs hardcoded y la reversión es no-op: `MIGRATION_MODULES` deja
estas migraciones fuera de `migrate`.
"""
import os

from django.db import migrations


def _env(nombre):
    return os.environ.get(nombre) or None


ANIO_CICLO = 2026
FECHA_INICIO_CICLO = '2026-03-01'
FECHA_FIN_CICLO = '2026-12-18'
APELLIDO_INCORRECTO = 'Guitierrez'
APELLIDO_CORRECTO = 'Gutiérrez'
NUEVA_DESCRIPCION_EVENTO = 'Capacitación Docente'

SQL = [
    (
        """
        UPDATE ciclos_lectivos
        SET fecha_inicio = %s, fecha_fin = %s
        WHERE anio = %s
        """,
        (FECHA_INICIO_CICLO, FECHA_FIN_CICLO, ANIO_CICLO),
    ),
]

_USUARIO_FAMILIA = _env('CORRECCION_0012_USUARIO_FAMILIA')
if _USUARIO_FAMILIA:
    SQL.append((
        """
        INSERT INTO usuario_roles (id_usuario, id_rol)
        SELECT u.id_usuario, r.id_rol
        FROM usuarios u, roles r
        WHERE u.usuario = %s AND r.nombre_rol = %s
          AND NOT EXISTS (
              SELECT 1 FROM usuario_roles ur
              WHERE ur.id_usuario = u.id_usuario AND ur.id_rol = r.id_rol
          )
        """,
        (_USUARIO_FAMILIA, 'familia'),
    ))

for _tabla in ('docentes', 'preceptores', 'directivos', 'padres_tutores'):
    SQL.append((
        f'UPDATE {_tabla} SET apellido = %s WHERE apellido = %s',
        (APELLIDO_CORRECTO, APELLIDO_INCORRECTO),
    ))

_DNI_DOCENTE = _env('CORRECCION_0012_DNI_DOCENTE_TITULAR')
_CURSO_TITULAR = _env('CORRECCION_0012_NOMBRE_CURSO_TITULAR')
_MATERIA_TITULAR = _env('CORRECCION_0012_NOMBRE_MATERIA_TITULAR')
if _DNI_DOCENTE and _CURSO_TITULAR and _MATERIA_TITULAR:
    SQL.append((
        """
        UPDATE curso_materia
        SET id_docente = (SELECT d.id_docente FROM docentes d WHERE d.dni = %s)
        WHERE id_docente IS NULL
          AND id_curso_materia = (
              SELECT id_curso_materia FROM (
                  SELECT cm.id_curso_materia
                  FROM curso_materia cm
                  JOIN cursos c ON c.id_curso = cm.id_curso
                  JOIN materias m ON m.id_materia = cm.id_materia
                  WHERE c.nombre_curso = %s AND m.nombre_materia = %s
                  LIMIT 1
              ) AS candidato
          )
        """,
        (_DNI_DOCENTE, _CURSO_TITULAR, _MATERIA_TITULAR),
    ))

_DESCRIPCION_CAPACITACION = _env('CORRECCION_0012_DESCRIPCION_CAPACITACION')
if _DESCRIPCION_CAPACITACION:
    SQL.append((
        """
        UPDATE eventos_institucionales
        SET descripcion = %s
        WHERE descripcion = %s
        """,
        (NUEVA_DESCRIPCION_EVENTO, _DESCRIPCION_CAPACITACION),
    ))

_DESCRIPCION_FERIADO = _env('CORRECCION_0012_DESCRIPCION_FERIADO')
if _DESCRIPCION_FERIADO:
    SQL.append((
        """
        UPDATE eventos_institucionales
        SET permanente = FALSE
        WHERE descripcion = %s
        """,
        (_DESCRIPCION_FERIADO,),
    ))

_DNI_TUTOR = _env('CORRECCION_0012_DNI_TUTOR')
_CORREO_TUTOR = _env('CORRECCION_0012_CORREO_TUTOR')
if _DNI_TUTOR and _CORREO_TUTOR:
    SQL.append((
        """
        UPDATE padres_tutores
        SET correo = %s
        WHERE dni = %s
        """,
        (_CORREO_TUTOR, _DNI_TUTOR),
    ))


def aplicar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for sql, params in SQL:
            cursor.execute(sql, params)


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0011_ddjj_por_ciclo'),
    ]

    operations = [
        migrations.RunPython(aplicar, migrations.RunPython.noop),
    ]
