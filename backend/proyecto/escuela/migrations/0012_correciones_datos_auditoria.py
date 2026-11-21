"""Correcciones puntuales de datos de la auditoría (bloque B).

Sólo datos identificados de forma unambiguousa por la auditoría:
B2 (fechas del ciclo), B5 (rol familia), B6 (apellido), B7 (titular),
B9 (typo), B10 (feriado permanente) y B11 (correo).
"""
from django.db import migrations


SQL = [
    """
    UPDATE ciclos_lectivos
    SET fecha_inicio = '2026-03-01', fecha_fin = '2026-12-18'
    WHERE anio = 2026
    """,
    """
    INSERT INTO usuario_roles (id_usuario, id_rol)
    SELECT u.id_usuario, r.id_rol
    FROM usuarios u, roles r
    WHERE u.usuario = '1' AND r.nombre_rol = 'familia'
      AND NOT EXISTS (
          SELECT 1 FROM usuario_roles ur
          WHERE ur.id_usuario = u.id_usuario AND ur.id_rol = r.id_rol
      )
    """,
    "UPDATE docentes SET apellido = 'Gutiérrez' WHERE apellido = 'Guitierrez'",
    "UPDATE preceptores SET apellido = 'Gutiérrez' WHERE apellido = 'Guitierrez'",
    "UPDATE directivos SET apellido = 'Gutiérrez' WHERE apellido = 'Guitierrez'",
    "UPDATE padres_tutores SET apellido = 'Gutiérrez' WHERE apellido = 'Guitierrez'",
    """
    UPDATE curso_materia
    SET id_docente = 1
    WHERE id_curso_materia = 1 AND id_docente IS NULL
    """,
    """
    UPDATE eventos_institucionales
    SET descripcion = 'Capacitación Docente'
    WHERE id_evento = 2
    """,
    """
    UPDATE eventos_institucionales
    SET permanente = FALSE
    WHERE id_evento = 1
    """,
    """
    UPDATE padres_tutores
    SET correo = 'silvina.molina@yahoo.com'
    WHERE id_tutor = 4
    """,
]


def aplicar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for sql in SQL:
            cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0011_ddjj_por_ciclo'),
    ]

    operations = [
        migrations.RunPython(aplicar, migrations.RunPython.noop),
    ]
