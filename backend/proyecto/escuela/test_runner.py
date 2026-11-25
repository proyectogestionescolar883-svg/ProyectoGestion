"""Test runner de la escuela.

Los modelos de la app `escuela` usan `managed = False` y no tienen
migraciones que creen tablas (las tablas existen solo en la base real).
Por eso `manage.py test` no puede usar el esquema estándar de Django:
Django crea la base de testing vacía.

Este runner copia SOLO la estructura (CREATE TABLE) de la base real al
test DB después de que Django la crea, de modo que los tests corren sobre
un esquema idéntico al de producción pero sin datos reales. Nunca se
escribe sobre la base real.
"""

import re
import warnings

from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner


class EscuelaDiscoverRunner(DiscoverRunner):
    """DiscoverRunner que replica el esquema real en el test database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._real_db_settings = dict(settings.DATABASES['default'])
        self._real_db_settings['OPTIONS'] = dict(
            settings.DATABASES['default'].get('OPTIONS') or {}
        )

    def setup_databases(self, **kwargs):
        old_config = super().setup_databases(**kwargs)
        self._copiar_esquema()
        return old_config

    def _conectar_real(self):
        cfg = self._real_db_settings
        vendor = connections['default'].vendor
        if vendor == 'postgresql':
            import psycopg2
            return psycopg2.connect(
                host=cfg.get('HOST') or 'localhost',
                port=int(cfg['PORT']) if cfg.get('PORT') else 5432,
                user=cfg.get('USER') or 'postgres',
                password=cfg.get('PASSWORD') or '',
                dbname=cfg['NAME'],
                sslmode=cfg.get('OPTIONS', {}).get('sslmode', 'require'),
            )
        import MySQLdb
        return MySQLdb.connect(
            host=cfg.get('HOST') or 'localhost',
            port=int(cfg['PORT']) if cfg.get('PORT') else 3306,
            user=cfg.get('USER') or 'root',
            passwd=cfg.get('PASSWORD') or '',
            db=cfg['NAME'],
            charset=cfg.get('OPTIONS', {}).get('charset', 'utf8mb4'),
        )

    def _copiar_esquema(self):
        test_conn = connections['default']
        vendor = test_conn.vendor
        if vendor not in {'mysql', 'postgresql'}:
            warnings.warn(
                'EscuelaDiscoverRunner: la copia de esquema solo está '
                'implementada para MySQL y PostgreSQL; se omite en otros motores.',
                RuntimeWarning,
            )
            return
        test_name = test_conn.settings_dict['NAME']
        if not self._real_db_settings['NAME'] or test_name is None:
            return

        real = self._conectar_real()
        cur_real = real.cursor()
        cur_test = test_conn.cursor()
        try:
            if vendor == 'mysql':
                self._copiar_mysql(cur_real, cur_test)
            else:
                self._copiar_postgres(cur_real, cur_test)
        finally:
            cur_real.close()
            cur_test.close()
            real.close()

    def _copiar_mysql(self, cur_real, cur_test):
        quote = connections['default'].ops.quote_name
        cur_test.execute('SHOW TABLES')
        existentes = {row[0] for row in cur_test.fetchall()}
        cur_real.execute('SHOW TABLES')
        tablas = sorted(row[0] for row in cur_real.fetchall())

        cur_test.execute('SET FOREIGN_KEY_CHECKS=0')
        try:
            for tabla in tablas:
                if tabla in existentes:
                    continue
                cur_real.execute(f'SHOW CREATE TABLE {quote(tabla)}')
                fila = cur_real.fetchone()
                if not fila:
                    continue
                cur_test.execute(fila[1])
        finally:
            cur_test.execute('SET FOREIGN_KEY_CHECKS=1')

    def _copiar_postgres(self, cur_real, cur_test):
        quote = connections['default'].ops.quote_name
        cur_test.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        existentes = {row[0] for row in cur_test.fetchall()}
        cur_real.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        tablas = [row[0] for row in cur_real.fetchall()]

        restricciones = {}
        for tabla in tablas:
            if tabla in existentes:
                continue
            cur_real.execute(
                "SELECT c.column_name, "
                "pg_catalog.format_type(a.atttypid, a.atttypmod), "
                "c.is_nullable, pg_catalog.pg_get_expr(d.adbin, d.adrelid) "
                "FROM information_schema.columns c "
                "JOIN pg_class cl ON cl.relname = c.table_name "
                "AND cl.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = c.table_schema) "
                "JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attname = c.column_name "
                "LEFT JOIN pg_attrdef d ON d.adrelid = cl.oid AND d.adnum = a.attnum "
                "WHERE c.table_schema = 'public' AND c.table_name = %s "
                "ORDER BY c.ordinal_position",
                (tabla,),
            )
            columnas = []
            for nombre, tipo, nullable, default in cur_real.fetchall():
                parte = f'{quote(nombre)} {tipo}'
                if nullable == 'NO':
                    parte += ' NOT NULL'
                if default:
                    secuencia = re.search(r"nextval\('([^']+)'", default)
                    if secuencia:
                        nombre_secuencia = secuencia.group(1).split('.')[-1]
                        cur_test.execute(
                            f'CREATE SEQUENCE IF NOT EXISTS {quote(nombre_secuencia)}'
                        )
                    else:
                        parte += f' DEFAULT {default}'
                columnas.append(parte)
            if not columnas:
                continue
            cur_test.execute(f'CREATE TABLE {quote(tabla)} ({", ".join(columnas)})')

            cur_real.execute(
                "SELECT tc.constraint_type, kcu.column_name, "
                "ccu.table_name, ccu.column_name, rc.delete_rule "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "ON tc.constraint_name = kcu.constraint_name "
                "AND tc.table_schema = kcu.table_schema "
                "LEFT JOIN information_schema.constraint_column_usage ccu "
                "ON tc.constraint_name = ccu.constraint_name "
                "AND tc.table_schema = ccu.table_schema "
                "LEFT JOIN information_schema.referential_constraints rc "
                "ON tc.constraint_name = rc.constraint_name "
                "AND tc.table_schema = rc.constraint_schema "
                "WHERE tc.table_schema = 'public' AND tc.table_name = %s "
                "ORDER BY tc.constraint_type, kcu.ordinal_position",
                (tabla,),
            )
            primarias = []
            unicas = []
            foraneas = []
            for tipo, columna, tabla_ref, columna_ref, regla in cur_real.fetchall():
                if tipo == 'PRIMARY KEY':
                    primarias.append(columna)
                elif tipo == 'UNIQUE':
                    unicas.append(columna)
                elif tipo == 'FOREIGN KEY' and tabla_ref and columna_ref:
                    regla = regla if regla in {
                        'CASCADE', 'RESTRICT', 'SET NULL', 'SET DEFAULT',
                    } else 'NO ACTION'
                    foraneas.append((columna, tabla_ref, columna_ref, regla))
            restricciones[tabla] = (primarias, unicas, foraneas)

        for tabla, (primarias, unicas, foraneas) in restricciones.items():
            if primarias:
                columnas_pk = ', '.join(quote(c) for c in primarias)
                cur_test.execute(f'ALTER TABLE {quote(tabla)} ADD PRIMARY KEY ({columnas_pk})')
            for columna in unicas:
                cur_test.execute(f'ALTER TABLE {quote(tabla)} ADD UNIQUE ({quote(columna)})')
            for columna, tabla_ref, columna_ref, regla in foraneas:
                cur_test.execute(
                    f'ALTER TABLE {quote(tabla)} ADD FOREIGN KEY ({quote(columna)}) '
                    f'REFERENCES {quote(tabla_ref)} ({quote(columna_ref)}) '
                    f'ON DELETE {regla}'
                )
