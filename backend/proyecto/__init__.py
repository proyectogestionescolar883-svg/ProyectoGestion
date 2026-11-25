import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

if os.environ.get('DB_ENGINE', 'django.db.backends.mysql') == 'django.db.backends.mysql':
    import pymysql

    pymysql.install_as_MySQLdb()
    pymysql.version_info = (2, 2, 7, 'final', 0)
