from datetime import datetime
from django.utils import timezone
from django.db import transaction
from escuela.models import (
    Alumno, Curso, Materia, CursoMateria, Calificacion, PeriodoEvaluacion,
    HistorialAcademico, MateriaAdeudada, HistorialCursoAlumno, PromocionAlumno,
    IntensificacionAcademica,
    RecursadaMateria, BloqueoHorarioAlumno, RegistroRendicionPrevia,
    RendicionMateriaAdeudada, SituacionMateriaAlumno, Horario, HorariosEspeciales,
    NOTA_APROBACION,
)
from escuela.notifications import notificar_alumno


def estado_por_cuatrimestres(nota1, nota2):
    """Regla ÚNICA de aprobación por cuatrimestres, compartida con las
    intensificaciones (`_intensif_habilitada` en views.py): una materia se
    aprueba sólo si AMBOS cuatrimestres tienen nota y alcanzan
    `NOTA_APROBACION`. Con un solo cuatrimestre cargado NO se aprueba (no se
    promedia una sola nota). Devuelve `(estado_materia, periodo_aprobacion)`.

    Antes el cierre aprobaba por promedio de las notas disponibles, lo que
    contradecía la habilitación de intensificaciones (Diciembre se habilita si
    el 2.º cuatrimestre es < NOTA_APROBACION) y aprobaba materias con una sola
    nota cargada."""
    if nota1 is None and nota2 is None:
        return 'no_cursada', None
    if nota1 is None or nota2 is None:
        return 'adeudada', None
    if nota1 >= NOTA_APROBACION and nota2 >= NOTA_APROBACION:
        return 'aprobada', 'cuatrimestre'
    return 'adeudada', None


def consolidar_historial_alumno(alumno, anio_lectivo):
    """Consolida las calificaciones del año y actualiza/crea el historial académico."""
    curso_actual = alumno.id_curso
    if not curso_actual:
        return

    curso_materias = CursoMateria.objects.filter(id_curso=curso_actual, activo=True)
    periodos = PeriodoEvaluacion.objects.filter(estado=True).order_by('orden_periodo')
    p1 = periodos.filter(orden_periodo=1).first()
    p2 = periodos.filter(orden_periodo=2).first()

    for cm in curso_materias:
        cals = Calificacion.objects.filter(id_alumno=alumno, id_curso_materia=cm)
        nota1 = None
        nota2 = None
        if p1:
            n1_obj = cals.filter(id_periodo=p1).first()
            if n1_obj:
                nota1 = n1_obj.nota_numerica
        if p2:
            n2_obj = cals.filter(id_periodo=p2).first()
            if n2_obj:
                nota2 = n2_obj.nota_numerica

        notas_validos = [n for n in [nota1, nota2] if n is not None]
        nota_final = sum(notas_validos) / len(notas_validos) if notas_validos else None

        estado_materia, periodo_aprob = estado_por_cuatrimestres(nota1, nota2)
        intensificacion_aprobada = IntensificacionAcademica.objects.filter(
            id_historial__id_alumno=alumno,
            id_historial__id_materia=cm.id_materia,
            id_historial__anio_lectivo=anio_lectivo,
            estado='APROBADA',
        ).exists()
        if intensificacion_aprobada:
            estado_materia = 'intensificacion'
            periodo_aprob = 'intensificacion'
            nota_final = None

        HistorialAcademico.objects.update_or_create(
            id_alumno=alumno,
            id_curso_materia=cm,
            anio_lectivo=anio_lectivo,
            defaults={
                'id_curso': curso_actual,
                'id_materia': cm.id_materia,
                'nota_1_cuatrimestre': nota1,
                'nota_2_cuatrimestre': nota2,
                'nota_final': nota_final,
                'estado_materia': estado_materia,
                'periodo_aprobacion': periodo_aprob,
                'anio_aprobacion': anio_lectivo if estado_materia in ('aprobada', 'intensificacion') else None,
            }
        )

        if estado_materia == 'adeudada':
            MateriaAdeudada.objects.get_or_create(
                id_alumno=alumno,
                id_materia=cm.id_materia,
                id_curso_origen=curso_actual,
                defaults={
                    'tipo_deuda': 'PREVIA',
                    'estado': 'ADEUDADA',
                    'fecha_generacion': timezone.now()
                }
            )

        _notificar_consolidacion(alumno, cm, estado_materia)


def _notificar_consolidacion(alumno, cm, estado_materia):
    """E13 — Promoción / no promoción (por materia) durante el cierre del ciclo.

    Se emite durante la consolidación del ciclo: cuando una materia queda
    `aprobada` (promoción) o `adeudada` (no promoción) se notifica al
    estudiante y a su familia por materia. La deduplicación por contenido
    evita repetir la notificación si el cierre se vuelve a procesar.
    """
    if estado_materia not in ('aprobada', 'adeudada'):
        return
    materia = cm.id_materia
    nombre = materia.nombre_materia if materia else 'la materia'
    if estado_materia == 'aprobada':
        titulo = 'Materia aprobada'
        mensaje = f'Resultado del ciclo: la materia {nombre} fue aprobada.'
    else:
        titulo = 'Materia adeudada'
        mensaje = f'Resultado del ciclo: la materia {nombre} quedó adeudada.'
    notificar_alumno(alumno=alumno, titulo=titulo, mensaje=mensaje, nav={
        'destino': 'boletin',
        'params': {
            # 5.1: curso y curso-materia para que la vista destino abra con el
            # contexto completo de la notificación.
            'cursoId': alumno.id_curso_id if alumno else None,
            'materiaId': materia.id_materia if materia else None,
            'cursoMateriaId': cm.id_curso_materia if cm else None,
            'estado': estado_materia,
        }
    })


@transaction.atomic
def procesar_cierre_ciclo(anio_lectivo):
    """Procesa el cierre de ciclo lectivo para todos los alumnos activos."""
    alumnos = Alumno.objects.filter(estado=True).select_related('id_curso')
    procesados = 0
    omitidos = []
    for alumno in alumnos:
        if not alumno.id_curso:
            omitidos.append({
                'id_alumno': alumno.id_alumno,
                'nombre': f'{alumno.apellido}, {alumno.nombre}',
            })
            continue
        consolidar_historial_alumno(alumno, anio_lectivo)
        procesados += 1

        historial_curso, _ = HistorialCursoAlumno.objects.update_or_create(
            id_alumno=alumno,
            anio_lectivo=anio_lectivo,
            defaults={
                'id_curso': alumno.id_curso,
                'estado': 'FINALIZADO',
                'fecha_finalizacion': timezone.now().date()
            }
        )

        materias_curso = list(CursoMateria.objects.filter(id_curso=alumno.id_curso, activo=True))
        historiales_anio = {
            h.id_curso_materia_id: h.estado_materia
            for h in HistorialAcademico.objects.filter(
                id_alumno=alumno, anio_lectivo=anio_lectivo,
                id_curso_materia__in=[cm.pk for cm in materias_curso],
            )
        }
        todas_aprobadas = bool(materias_curso) and all(
            historiales_anio.get(cm.pk) in ('aprobada', 'intensificacion')
            for cm in materias_curso
        )
        curso_destino = Curso.objects.filter(
            id_ciclo__anio=anio_lectivo + 1,
            nombre_curso=alumno.id_curso.nombre_curso,
            orientacion=alumno.id_curso.orientacion,
        ).first() or Curso.objects.filter(
            id_ciclo__anio=anio_lectivo + 1,
            nombre_curso=alumno.id_curso.nombre_curso,
        ).first()
        PromocionAlumno.objects.update_or_create(
            id_alumno=alumno,
            id_historial_curso=historial_curso,
            anio_lectivo=anio_lectivo,
            defaults={
                'resultado': 'PROMOVIDO' if todas_aprobadas else 'REPITENTE',
                'curso_origen': alumno.id_curso,
                'curso_destino': curso_destino,
                'fecha_resolucion': timezone.now(),
            }
        )

        previas_pendientes = MateriaAdeudada.objects.filter(
            id_alumno=alumno, estado='ADEUDADA', tipo_deuda='PREVIA'
        ).order_by('fecha_generacion')

        if previas_pendientes.count() > 4:
            excedentes = previas_pendientes[4:]
            for ex in excedentes:
                ex.tipo_deuda = 'RECURSADA'
                ex.save(update_fields=['tipo_deuda'])
                curso_recursada = Curso.objects.filter(
                    id_ciclo__anio=anio_lectivo + 1,
                    nombre_curso=ex.id_curso_origen.nombre_curso,
                    orientacion=ex.id_curso_origen.orientacion,
                ).first() or Curso.objects.filter(
                    id_ciclo__anio=anio_lectivo + 1,
                    nombre_curso=ex.id_curso_origen.nombre_curso,
                ).first() or ex.id_curso_origen
                RecursadaMateria.objects.get_or_create(
                    id_alumno=alumno,
                    id_materia=ex.id_materia,
                    id_curso_origen=ex.id_curso_origen,
                    id_curso_recursada=curso_recursada,
                    anio_inicio=anio_lectivo,
                    defaults={
                        'estado': 'ACTIVA',
                        'motivo': 'Exceso de 4 previas (recursada obligatoria)',
                        'fecha_registro': timezone.now()
                    }
                )

    return {'procesados': procesados, 'omitidos': omitidos}


def detectar_superposiciones_y_bloqueos(alumno, anio_lectivo):
    """Detecta superposiciones horarias entre materias recursadas y el año actual."""
    curso_actual = alumno.id_curso
    if not curso_actual:
        return

    recursadas_activas = RecursadaMateria.objects.filter(
        id_alumno=alumno, estado='ACTIVA'
    ).select_related('id_curso_recursada', 'id_materia')

    if not recursadas_activas.exists():
        return

    cms_actuales = CursoMateria.objects.filter(id_curso=curso_actual, activo=True)

    for rec in recursadas_activas:
        cm_recs = CursoMateria.objects.filter(id_curso=rec.id_curso_recursada, id_materia=rec.id_materia)
        if not cm_recs.exists():
            continue
        cm_rec = cm_recs.first()
        horarios_rec = list(Horario.objects.filter(id_curso_materia=cm_rec))

        for cm_act in cms_actuales:
            if cm_act.id_materia == rec.id_materia:
                continue
            horarios_act = list(Horario.objects.filter(id_curso_materia=cm_act))

            for hr in horarios_rec:
                for ha in horarios_act:
                    if hr.dia_semana and ha.dia_semana and hr.dia_semana.lower() == ha.dia_semana.lower():
                        if hr.id_modulo_id and ha.id_modulo_id and hr.id_modulo_id == ha.id_modulo_id:
                            BloqueoHorarioAlumno.objects.update_or_create(
                                id_alumno=alumno,
                                id_materia_bloqueada=cm_act.id_materia,
                                defaults={
                                    'id_curso_materia_bloqueada': cm_act,
                                    'id_materia_prioritaria': rec.id_materia,
                                    'id_curso_materia_prioritaria': cm_rec,
                                    'id_materia_recursada': rec.id_materia,
                                    'id_curso_materia_recursada': cm_rec,
                                    'motivo': 'SUPERPOSICION_RECURSADA',
                                    'estado': True,
                                    'fecha_bloqueo': timezone.now(),
                                    'observaciones': f'Bloqueada por superposición con recursada de {rec.id_materia.nombre_materia}'
                                }
                            )

                            SituacionMateriaAlumno.objects.update_or_create(
                                id_alumno=alumno,
                                id_curso_materia=cm_act,
                                anio_lectivo=anio_lectivo,
                                defaults={
                                    'situacion': 'BLOQUEADA',
                                    'motivo_bloqueo': f'Superposición con recursada de {rec.id_materia.nombre_materia}',
                                    'fecha_inicio': timezone.now()
                                }
                            )
