"""DDJJ por ciclo lectivo (R13).

La DDJJ pasa de ser única por docente a única por docente y ciclo. La columna
se crea nullable para no romper filas históricas; el serializer y la vista
siempre la cargan con el ciclo activo.
"""
from django.db import migrations


SQL_AGREGAR = """
ALTER TABLE ddjj_docente
    ADD COLUMN id_ciclo INTEGER NULL
"""

SQL_RELLENAR = """
UPDATE ddjj_docente
SET id_ciclo = (
    SELECT id_ciclo FROM ciclos_lectivos
    WHERE estado = TRUE
    ORDER BY anio DESC
    LIMIT 1
)
"""

SQL_QUITAR = """
ALTER TABLE ddjj_docente
    DROP COLUMN id_ciclo
"""


def _aplicar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_AGREGAR)
        cursor.execute(SQL_RELLENAR)


def _revertir(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_QUITAR)


class Migration(migrations.Migration):

    dependencies = [
        ('escuela', '0010_usuario_borrado_logico'),
    ]

    operations = [
        migrations.RunPython(_aplicar, _revertir),
    ]
