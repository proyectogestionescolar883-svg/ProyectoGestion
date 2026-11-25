"""
Comando para crear automáticamente la estructura fija de cursos:
6 años (1° a 6°) x 3 divisiones (1 a 3) = 18 cursos por ciclo lectivo.

Uso:
    python manage.py seed_cursos

Es idempotente: busca con `all_objects`, así que también encuentra cursos dados
de baja lógicamente y los reactiva en vez de crear duplicados. Si no existe
ningún ciclo activo, crea uno para el año actual.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from escuela.models import CicloLectivo, Curso


class Command(BaseCommand):
    help = 'Crea o reactiva los 18 cursos fijos (6 años x 3 divisiones) por ciclo activo'

    def handle(self, *args, **options):
        ciclos = list(CicloLectivo.objects.filter(estado=True))
        if not ciclos:
            anio = timezone.localdate().year
            ciclo = CicloLectivo.all_objects.filter(anio=anio).first()
            if ciclo is None:
                ciclo = CicloLectivo.all_objects.create(
                    anio=anio,
                    fecha_inicio=date(anio, 3, 1),
                    fecha_fin=date(anio, 12, 15),
                    estado=True,
                )
            elif not ciclo.estado or ciclo.fecha_eliminacion:
                ciclo.estado = True
                ciclo.fecha_eliminacion = None
                ciclo.save()
            ciclos = [ciclo]

        creados = 0
        reactivados = 0
        for ciclo in ciclos:
            for anio in range(1, 7):
                for div in range(1, 4):
                    nombre = f'{anio}°{div}'
                    _curso, accion = self._asegurar_curso(ciclo, nombre)
                    if accion == 'creado':
                        creados += 1
                    elif accion == 'reactivado':
                        reactivados += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Ciclo {ciclo.anio}: 18 cursos asegurados'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Cursos nuevos creados: {creados}, reactivados: {reactivados}'
            )
        )

    def _asegurar_curso(self, ciclo, nombre):
        curso = Curso.all_objects.filter(nombre_curso=nombre, id_ciclo=ciclo).first()
        if curso is None:
            curso = Curso.all_objects.create(
                nombre_curso=nombre,
                id_ciclo=ciclo,
                orientacion='Mañana',
                estado=True,
                activo=True,
            )
            return curso, 'creado'

        reactivado = False
        if hasattr(curso, 'activo') and not curso.activo:
            curso.activo = True
            reactivado = True
        if hasattr(curso, 'estado') and not curso.estado:
            curso.estado = True
            reactivado = True
        if getattr(curso, 'fecha_eliminacion', None):
            curso.fecha_eliminacion = None
            reactivado = True
        if reactivado:
            curso.save()
        return curso, 'reactivado' if reactivado else 'existente'
