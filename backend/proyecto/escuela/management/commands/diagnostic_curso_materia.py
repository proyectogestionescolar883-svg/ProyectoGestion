from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from escuela import schema
from escuela.models import CursoMateria


class Command(BaseCommand):
    help = 'Diagnóstico completo del problema CursoMateria'

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-detalles', action='store_true',
            help='Muestra NAME/USER/HOST/PORT de la base (por defecto ocultos).',
        )

    def handle(self, *args, **options):
        mostrar = options['db_detalles']
        cfg = settings.DATABASES['default']
        self.stdout.write('=== DIAGNÓSTICO COMPLETO CURSO_MATERIA ===\n')

        self.stdout.write('1. CONFIGURACIÓN DATABASES:')
        self.stdout.write(f'   ENGINE: {cfg["ENGINE"]}')
        for clave in ('NAME', 'USER', 'HOST', 'PORT'):
            valor = cfg.get(clave) if mostrar else '(oculto; usar --db-detalles)'
            self.stdout.write(f'   {clave}: {valor}')

        engine = cfg['ENGINE']
        db_type = 'MariaDB/MySQL' if 'mysql' in engine else 'SQLite' if 'sqlite' in engine else 'Otro'
        self.stdout.write(f'\n2. MOTOR DE BASE DE DATOS: {db_type}')

        self.stdout.write('\n3. NOMBRE DE LA BASE DE DATOS:')
        self.stdout.write(
            f'   {cfg.get("NAME") if mostrar else "(oculto; usar --db-detalles)"}'
        )

        self.stdout.write('\n4. MODELO CURSOMATERIA:')
        self.stdout.write(f'   Meta.db_table: {CursoMateria._meta.db_table}')
        self.stdout.write(f'   Meta.managed: {CursoMateria._meta.managed}')
        self.stdout.write('   Campos:')
        for field in CursoMateria._meta.get_fields():
            self.stdout.write(f'     - {field.name} ({field.__class__.__name__})')

        self.stdout.write('\n5. CONNECTION SETTINGS_DICT:')
        self.stdout.write(f'   {self._redactar(dict(connection.settings_dict), mostrar)}')

        self.stdout.write('\n6. CONTEO ORM:')
        count_orm = CursoMateria.objects.count()
        self.stdout.write(f'   CursoMateria.objects.count() = {count_orm}')

        self.stdout.write('\n7. QUERYSET DEL ENDPOINT:')
        qs = CursoMateria.objects.select_related('id_curso', 'id_materia', 'id_docente').all()
        self.stdout.write(f'   QuerySet: {qs}')
        self.stdout.write(f'   Count: {qs.count()}')

        self.stdout.write('\n8. SQL GENERADO:')
        sql, params = qs.query.sql_with_params()
        self.stdout.write(f'   SQL: {sql}')
        self.stdout.write(f'   Params: {params}')

        self.stdout.write('\n9. VERIFICACIÓN DE TABLA:')
        with connection.cursor() as cursor:
            tablas = schema.tablas_de(cursor)
            if CursoMateria._meta.db_table in tablas:
                self.stdout.write(f'   Tabla {CursoMateria._meta.db_table} EXISTE')
                cursor.execute(
                    f'SELECT COUNT(*) FROM {schema._q(cursor, CursoMateria._meta.db_table)}'
                )
                count_sql = cursor.fetchone()[0]
                self.stdout.write(
                    f'   COUNT(*) FROM {CursoMateria._meta.db_table} (SQL directo): {count_sql}'
                )
            else:
                self.stdout.write(f'   Tabla {CursoMateria._meta.db_table} NO EXISTE')

        self.stdout.write('\n10. TABLAS EN LA BASE DE DATOS:')
        self.stdout.write(f'   Total tablas: {len(tablas)}')
        for tabla in sorted(tablas):
            self.stdout.write(f'     - {tabla}')

        self.stdout.write('\n=== FIN DEL DIAGNÓSTICO ===')

    def _redactar(self, cfg, mostrar):
        sensibles = {'NAME', 'USER', 'HOST', 'PORT'}
        resultado = {}
        for clave, valor in cfg.items():
            if clave == 'PASSWORD':
                resultado[clave] = '***'
            elif clave == 'TEST' and isinstance(valor, dict):
                resultado[clave] = {
                    k: ('***' if k in sensibles and not mostrar else v)
                    for k, v in valor.items()
                }
            elif clave in sensibles and not mostrar:
                resultado[clave] = '(oculto; usar --db-detalles)'
            else:
                resultado[clave] = valor
        return resultado
