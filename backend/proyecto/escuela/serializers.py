import unicodedata
from datetime import datetime, timedelta, timezone as dt_timezone

from rest_framework import serializers

from django.utils import timezone

from django.db import transaction
from django.db.utils import IntegrityError

from escuela.storage import media_url
from escuela.utils import (
    HORA_CORTE_TURNO,
    alumno_pertenece_a_curso_materia,
    es_estado_asistencia_base,
    franjas_se_solapan,
    normalizar_dni,
    obtener_docente_activo,
)


class EnteroOpcionalField(serializers.IntegerField):
    """Entero que acepta '', null y no presente como 'sin valor'."""

    def to_internal_value(self, data):
        if data is None or data == '':
            return None
        return super().to_internal_value(data)

from escuela.models import (
    AdelantoHoras,
    Acta,
    ActaAlumno,
    ActaCurso,
    ActaDocente,
    Alumno,
    Asistencia,
    AsistenciaDocente,
    Calificacion,
    CargaUnica,
    CicloLectivo,
    ActividadDocente,
    ActividadDocenteArchivo,
    Comunicado,
    ComunicadoAlcance,
    ComunicadoArchivo,
    Curso,
    CursoMateria,
    DdjjDocente,
    DiagnosticoGrupal,
    Directivo,
    Docente,
    EstadoAsistencia,
    EventoInstitucional,
    HistorialCambio,
    Horario,
    HorariosEspeciales,
    InscripcionMateria,
    LibroTema,
    Materia,
    Modulos,
    Notificacion,
    PadreTutor,
    PeriodoEvaluacion,
    Planificacion,
    Preceptor,
    Rol,
    SuplenciaDocente,
    TipoAccion,
    TipoActa,
    TutorAlumno,
    Usuario,
    UsuarioRol,
    HistorialAcademico,
    IntensificacionAcademica,
    MateriaAdeudada,
    ActividadMateriaAdeudada,
    RendicionMateriaAdeudada,
    HistorialCursoAlumno,
    BloqueoHorarioAlumno,
    PromocionAlumno,
    RecursadaMateria,
    RecursadaCalificacion,
    BloqueoMateriaRecursada,
    RegistroRendicionPrevia,
    ResultadoActividadAdeudada,
    SituacionMateriaAlumno,
)


def _assign_role(usuario, nombre_rol):
    if not usuario or not nombre_rol:
        return
    rol, _ = Rol.objects.get_or_create(nombre_rol=nombre_rol)
    UsuarioRol.objects.get_or_create(id_usuario=usuario, id_rol=rol)


def _vincular_tutor_alumnos(padre, alumnos_ids):
    """Crea los vínculos N:M tutor-alumno sin pisar los vínculos de otros
    tutores (un alumno puede tener papá y mamá).
    
    Mantiene además ``alumnos.id_tutor`` como "tutor principal" (solo cuando el
    alumno no tenía ninguno) por compatibilidad con lecturas previas."""
    if not alumnos_ids:
        return
    for alumno_id in alumnos_ids:
        TutorAlumno.objects.get_or_create(id_tutor=padre, id_alumno_id=alumno_id)
    Alumno.objects.filter(id_alumno__in=alumnos_ids, id_tutor_id__isnull=True).update(id_tutor=padre)


_sentinel = object()


def _fecha_programada_aware(fecha):
    if isinstance(fecha, datetime) and timezone.is_naive(fecha):
        return timezone.make_aware(fecha, dt_timezone.utc)
    return fecha


def _formatear_fecha_programada(fecha):
    fecha = _fecha_programada_aware(fecha)
    return timezone.localtime(fecha).isoformat() if fecha else None


class FechaProgramadaField(serializers.DateTimeField):
    def to_representation(self, value):
        return super().to_representation(_fecha_programada_aware(value))


def _validar_programacion_estado(usuario):
    """Valida las fechas programadas de una cuenta (punto 5.9, R1).

    `aplicar_programaciones_usuario` aplica el campo que ya venció y lo limpia,
    así que las fechas forman una línea de tiempo que arranca en el estado
    actual. La primera acción agendada tiene que ser la opuesta a ese estado; si
    no, no aplica ningún cambio y el usuario queda distinto al esperado.

    Vale tanto con las dos fechas como con una sola: una cuenta habilitada no
    puede programar solo una habilitación (no haría nada), y al revés. Se valida
    contra el estado actual de la cuenta, no contra la fecha de hoy: agendar una
    re-habilitación posterior a una deshabilitación ya programada es válido.
    """
    fecha_deshabilitacion = _fecha_programada_aware(usuario.fecha_deshabilitacion_programada)
    fecha_habilitacion = _fecha_programada_aware(usuario.fecha_habilitacion_programada)
    if not fecha_deshabilitacion and not fecha_habilitacion:
        return

    if fecha_deshabilitacion and fecha_habilitacion:
        if fecha_deshabilitacion <= fecha_habilitacion:
            primero, campo_incorrecto = 'deshabilitacion', 'fecha_deshabilitacion_programada'
        else:
            primero, campo_incorrecto = 'habilitacion', 'fecha_habilitacion_programada'
    elif fecha_deshabilitacion:
        primero, campo_incorrecto = 'deshabilitacion', 'fecha_deshabilitacion_programada'
    else:
        primero, campo_incorrecto = 'habilitacion', 'fecha_habilitacion_programada'

    esperada = 'deshabilitacion' if usuario.estado else 'habilitacion'
    if primero == esperada:
        return

    def _fmt(fecha):
        return timezone.localtime(fecha).strftime('%d/%m/%Y %H:%M') if fecha else '—'

    if fecha_deshabilitacion and fecha_habilitacion:
        if usuario.estado:
            mensaje = (
                f'La cuenta está habilitada: la deshabilitación ({_fmt(fecha_deshabilitacion)}) '
                f'tiene que ser anterior a la habilitación ({_fmt(fecha_habilitacion)}).'
            )
        else:
            mensaje = (
                f'La cuenta está deshabilitada: la habilitación ({_fmt(fecha_habilitacion)}) '
                f'tiene que ser anterior a la deshabilitación ({_fmt(fecha_deshabilitacion)}).'
            )
    elif usuario.estado:
        mensaje = (
            'La cuenta está habilitada: la primera fecha programada tiene que ser una '
            'deshabilitación (una habilitación no aplicaría ningún cambio).'
        )
    else:
        mensaje = (
            'La cuenta está deshabilitada: la primera fecha programada tiene que ser una '
            'habilitación (una deshabilitación no aplicaría ningún cambio).'
        )
    raise serializers.ValidationError({campo_incorrecto: mensaje})


def _proxima_accion_programada(usuario):
    """Acción programada más próxima (la de menor fecha), o None (R2).

    Antes se devolvía siempre la deshabilitación si existía, aunque la
    habilitación fuera anterior. Con la validación de
    `_validar_programacion_estado` la más temprana es la acción opuesta al
    estado actual.
    """
    if not usuario:
        return None
    candidatas = []
    if usuario.fecha_deshabilitacion_programada:
        candidatas.append(('deshabilitar', usuario.fecha_deshabilitacion_programada))
    if usuario.fecha_habilitacion_programada:
        candidatas.append(('habilitar', usuario.fecha_habilitacion_programada))
    if not candidatas:
        return None
    tipo, fecha = min(candidatas, key=lambda c: _fecha_programada_aware(c[1]))
    return {'tipo': tipo, 'fecha': _formatear_fecha_programada(fecha)}


def _ciclo_lectivo_actual_id():
    ciclo = CicloLectivo.objects.filter(estado=True).order_by('-anio').first()
    return ciclo.pk if ciclo else None


def _validar_cursos_preceptor(cursos_ids, preceptor=None):
    """R7: no quitar cursos a otro preceptor sin aviso."""
    if not cursos_ids:
        return
    conflictos = Curso.objects.filter(id_curso__in=cursos_ids).exclude(
        id_preceptor__isnull=True,
    )
    if preceptor is not None:
        conflictos = conflictos.exclude(id_preceptor=preceptor)
    nombres = [
        f'{c.nombre_curso} ({c.id_preceptor.nombre} {c.id_preceptor.apellido})'
        for c in conflictos.select_related('id_preceptor')
    ]
    if nombres:
        raise serializers.ValidationError({
            'cursos_ids': (
                'Estos cursos ya tienen otro preceptor asignado: '
                + '; '.join(nombres)
            ),
        })


def _validar_curso_materia_docente(ids, docente=None):
    """R7: no reemplazar al docente titular sin aviso."""
    if not ids:
        return
    qs = CursoMateria.objects.filter(id_curso_materia__in=ids).select_related(
        'id_curso', 'id_materia', 'id_docente',
    )
    ciclo_id = _ciclo_lectivo_actual_id()
    if ciclo_id:
        qs = qs.filter(id_curso__id_ciclo_id=ciclo_id)
    nombres = []
    for cm in qs:
        actual = cm.id_docente
        if actual is None or (docente is not None and actual.pk == docente.pk):
            continue
        nombres.append(
            f'{cm.id_curso.nombre_curso} - {cm.id_materia.nombre_materia} '
            f'({actual.apellido}, {actual.nombre})'
        )
    if nombres:
        raise serializers.ValidationError({
            'curso_materia_ids': (
                'Estas materias ya tienen otro docente titular: '
                + '; '.join(nombres)
            ),
        })


def _build_usuario_account(
    *,
    instance,
    validated_data,
    username_key='usuario_nombre',
    role_name=None,
    require_password_on_create=True,
):
    id_usuario_existente = validated_data.pop('id_usuario_existente', None)
    username = validated_data.pop(username_key, None)
    if username is None and username_key != 'usuario':
        username = validated_data.pop('usuario', None)
    contrasena = validated_data.pop('contrasena', None)
    estado = validated_data.pop('estado', None)
    fecha_deshabilitacion_programada = validated_data.pop('fecha_deshabilitacion_programada', _sentinel)
    fecha_habilitacion_programada = validated_data.pop('fecha_habilitacion_programada', _sentinel)

    usuario = instance.id_usuario if getattr(instance, 'id_usuario_id', None) else None
    if usuario is None and id_usuario_existente is not None:
        try:
            usuario = Usuario.objects.get(id_usuario=id_usuario_existente)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError({
                'id_usuario_existente': 'El usuario seleccionado no existe.'
            })
    creating_usuario = usuario is None
    reusing_existente = id_usuario_existente is not None and not creating_usuario
    estado_anterior = None if creating_usuario else usuario.estado

    if creating_usuario and not username:
        raise serializers.ValidationError({username_key: 'El usuario es obligatorio.'})
    if creating_usuario and username and str(username).strip().isdigit():
        raise serializers.ValidationError({
            username_key: 'El nombre de usuario no puede ser sólo números; use letras y/o números.',
        })
    if creating_usuario and require_password_on_create and not contrasena:
        raise serializers.ValidationError({'contrasena': 'La contrasena es obligatoria para crear el usuario.'})
    if creating_usuario and username and Usuario.objects.filter(usuario=username).exists():
        raise serializers.ValidationError({
            username_key: 'Ya existe un usuario con ese nombre de usuario.'
        })

    if usuario is None:
        usuario = Usuario(
            usuario=username,
            estado=estado if estado is not None else True,
            fecha_deshabilitacion_programada=None if fecha_deshabilitacion_programada is _sentinel else fecha_deshabilitacion_programada,
            fecha_habilitacion_programada=None if fecha_habilitacion_programada is _sentinel else fecha_habilitacion_programada,
        )
    else:
        if not reusing_existente:
            if username is not None:
                usuario.usuario = username
            if estado is not None:
                # R3: al cambiar el estado a mano, las programaciones pendientes
                # dejan de ser coherentes (la primera acción ya no sería la
                # opuesta al nuevo estado). Si el cliente no manda fechas, se
                # limpian para no bloquear el guardado con un error de fechas.
                if (
                    estado != usuario.estado
                    and fecha_deshabilitacion_programada is _sentinel
                    and fecha_habilitacion_programada is _sentinel
                ):
                    usuario.fecha_deshabilitacion_programada = None
                    usuario.fecha_habilitacion_programada = None
                usuario.estado = estado
            if fecha_deshabilitacion_programada is not _sentinel:
                usuario.fecha_deshabilitacion_programada = fecha_deshabilitacion_programada
            if fecha_habilitacion_programada is not _sentinel:
                usuario.fecha_habilitacion_programada = fecha_habilitacion_programada

    if contrasena and not reusing_existente:
        usuario.set_password(contrasena)
    elif creating_usuario and require_password_on_create:
        raise serializers.ValidationError({'contrasena': 'La contrasena es obligatoria para crear el usuario.'})

    try:
        _validar_programacion_estado(usuario)
        usuario.save()
    except IntegrityError:
        raise serializers.ValidationError({
            username_key: 'Ya existe un usuario con ese nombre de usuario.'
        })
    if getattr(instance, 'id_usuario_id', None) != usuario.id_usuario:
        instance.id_usuario = usuario

    if role_name:
        _assign_role(usuario, role_name)

    if (creating_usuario and usuario.estado) or (
        not creating_usuario and estado_anterior != usuario.estado
    ):
        from escuela.notifications import notificar_estado_cuenta
        notificar_estado_cuenta(usuario)

    return usuario, validated_data


# ---------- Catálogos / tablas auxiliares ----------

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'


class EstadoAsistenciaSerializer(serializers.ModelSerializer):
    # Marca los cinco estados de los que depende la lógica de asistencia
    # (ver `utils.ESTADOS_ASISTENCIA_BASE`). Es un campo calculado: no agrega
    # ninguna columna a la tabla.
    es_base = serializers.SerializerMethodField()

    class Meta:
        model = EstadoAsistencia
        fields = '__all__'
        read_only_fields = ('es_base',)

    def get_es_base(self, obj):
        return es_estado_asistencia_base(obj.nombre_estado)

    def validate_nombre_estado(self, value):
        nombre = (value or '').strip()
        if not nombre:
            raise serializers.ValidationError('El nombre del estado es obligatorio.')
        if len(nombre) > 50:
            raise serializers.ValidationError(
                'El nombre del estado puede tener hasta 50 caracteres.'
            )
        qs = EstadoAsistencia.objects.filter(nombre_estado__iexact=nombre)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Ya existe un estado de asistencia con ese nombre.'
            )

        # Renombrar un estado base rompería el registro de asistencias, que lo
        # reconoce por su nombre exacto. Se permite cambiar mayúsculas y espacios
        # (el nombre sigue siendo "Presente"), pero no convertirlo en otro texto.
        if self.instance is not None:
            anterior = (self.instance.nombre_estado or '').strip()
            if es_estado_asistencia_base(anterior) and nombre != anterior:
                raise serializers.ValidationError(
                    f'"{anterior}" es un estado base del sistema: no se puede '
                    'cambiar su nombre porque el registro de asistencias lo '
                    'reconoce por ese nombre exacto.'
                )
        return nombre


class TipoActaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoActa
        fields = '__all__'

    def validate_nombre_tipo(self, value):
        nombre = (value or '').strip()
        if not nombre:
            raise serializers.ValidationError('El nombre del tipo de acta es obligatorio.')
        if len(nombre) > 50:
            raise serializers.ValidationError(
                'El nombre del tipo de acta puede tener hasta 50 caracteres.'
            )
        qs = TipoActa.objects.filter(nombre_tipo__iexact=nombre)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un tipo de acta con ese nombre.')
        return nombre


class TipoAccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoAccion
        fields = '__all__'


class PeriodoEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoEvaluacion
        fields = '__all__'
        read_only_fields = ('fecha_eliminacion',)

    def validate_orden_periodo(self, value):
        # La columna es NULL en el esquema, así que el campo llega como
        # opcional: la obligatoriedad se comprueba acá y en `validate`.
        if value is None:
            raise serializers.ValidationError('El orden del período es obligatorio.')
        if value < 1:
            raise serializers.ValidationError(
                'El orden del período debe ser un número entero positivo.'
            )
        return value

    def validate(self, attrs):
        # `nombre_periodo` es blank/null en el modelo: la obligatoriedad y el
        # recorte se resuelven acá para que el mensaje sea explícito.
        nombre = attrs.get(
            'nombre_periodo',
            getattr(self.instance, 'nombre_periodo', None),
        )
        if not nombre or not str(nombre).strip():
            raise serializers.ValidationError({
                'nombre_periodo': 'El nombre del período es obligatorio.',
            })
        attrs['nombre_periodo'] = str(nombre).strip()

        # El orden identifica la posición del período en el consolidado de
        # calificaciones, así que no puede repetirse entre períodos activos.
        orden = attrs.get(
            'orden_periodo',
            getattr(self.instance, 'orden_periodo', None),
        )
        if orden is None:
            raise serializers.ValidationError({
                'orden_periodo': 'El orden del período es obligatorio.',
            })
        if orden < 1:
            raise serializers.ValidationError({
                'orden_periodo': (
                    'El orden del período debe ser un número entero positivo.'
                ),
            })
        qs = PeriodoEvaluacion.all_objects.filter(
            orden_periodo=orden, estado=True,
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({
                'orden_periodo': (
                    f'Ya existe un período de evaluación activo con el '
                    f'orden {orden}.'
                ),
            })
        return attrs


class CicloLectivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloLectivo
        fields = '__all__'
        read_only_fields = ('fecha_eliminacion',)

    def validate_anio(self, value):
        if value is None:
            raise serializers.ValidationError('El año del ciclo lectivo es obligatorio.')
        # La columna física es `YEAR(4)`, que en MariaDB solo admite de 1901 a
        # 2155. Sin este rango, un año como 3000 pasaba la validación y
        # reventaba al insertar con un DataError (HTTP 500) en vez de un 400.
        if not (1901 <= value <= 2155):
            raise serializers.ValidationError(
                'El año del ciclo lectivo debe estar entre 1901 y 2155 '
                '(por ejemplo, 2026).'
            )
        return value

    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({
                'fecha_fin': (
                    'La fecha de fin no puede ser anterior a la fecha de inicio.'
                ),
            })
        if inicio and inicio.month == 1:
            raise serializers.ValidationError({
                'fecha_inicio': (
                    'El ciclo lectivo no puede comenzar en enero; use una fecha '
                    'acorde al calendario escolar (desde febrero/marzo).'
                ),
            })

        # Un año con dos ciclos activos rompería los filtros por ciclo de toda
        # la aplicación (cursos, comunicados, reportes). La tabla no tiene
        # índice único, así que la regla se valida acá.
        anio = attrs.get('anio', getattr(self.instance, 'anio', None))
        if anio is not None:
            qs = CicloLectivo.all_objects.filter(anio=anio, estado=True)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'anio': 'Ya existe un ciclo lectivo activo con ese año.',
                })
            for campo, fecha in (('fecha_inicio', inicio), ('fecha_fin', fin)):
                if fecha is not None and fecha.year != anio:
                    raise serializers.ValidationError({
                        campo: f'La fecha debe corresponder al año lectivo {anio}.',
                    })
        if inicio and fin:
            solapados = CicloLectivo.all_objects.filter(
                estado=True,
                fecha_inicio__lte=fin,
                fecha_fin__gte=inicio,
            )
            if self.instance is not None:
                solapados = solapados.exclude(pk=self.instance.pk)
            if solapados.exists():
                raise serializers.ValidationError({
                    'fecha_inicio': 'Las fechas se superponen con otro ciclo lectivo activo.',
                })
        return attrs


def _normalizar_texto(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower()

class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = '__all__'

    def validate(self, attrs):
        if self.instance is None:
            return attrs
        nombre = attrs.get('nombre_materia', self.instance.nombre_materia)
        if nombre:
            normalizado = _normalizar_texto(nombre)
            for m in Materia.objects.all().exclude(pk=self.instance.pk):
                if _normalizar_texto(m.nombre_materia) == normalizado:
                    raise serializers.ValidationError({
                        'nombre_materia': 'Ya existe una materia con ese nombre.'
                    })
        return attrs

    def create(self, validated_data):
        nombre = validated_data.get('nombre_materia')
        if nombre:
            normalizado = _normalizar_texto(nombre)
            for m in Materia.objects.all():
                if _normalizar_texto(m.nombre_materia) == normalizado:
                    if m.activo:
                        raise serializers.ValidationError({
                            'nombre_materia': 'Ya existe una materia con ese nombre.'
                        })
                    for attr, value in validated_data.items():
                        setattr(m, attr, value)
                    m.activo = True
                    m.save()
                    return m
        return Materia.objects.create(**validated_data, activo=True)


# ---------- Personas ----------

class UsuarioSerializer(serializers.ModelSerializer):
    fecha_deshabilitacion_programada = FechaProgramadaField(required=False, allow_null=True)
    fecha_habilitacion_programada = FechaProgramadaField(required=False, allow_null=True)
    roles = serializers.SerializerMethodField()
    contrasena = serializers.CharField(write_only=True, required=False)
    usuario_nombre = serializers.CharField(write_only=True, required=False)
    nombre = serializers.CharField(write_only=True, required=False)
    apellido = serializers.CharField(write_only=True, required=False)
    dni = serializers.CharField(write_only=True, required=False)
    telefono = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    cargo = serializers.CharField(write_only=True, required=False)
    id_usuario_existente = EnteroOpcionalField(write_only=True, required=False, allow_null=True)
    estado_label = serializers.SerializerMethodField()
    proxima_accion_programada = serializers.SerializerMethodField()
    # Read-only fields from Directivo
    directivo_nombre = serializers.SerializerMethodField()
    directivo_apellido = serializers.SerializerMethodField()
    directivo_dni = serializers.SerializerMethodField()
    directivo_telefono = serializers.SerializerMethodField()
    directivo_cargo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
            'id_usuario_existente',
            'usuario',
            'usuario_nombre',
            'contrasena',
            'estado',
            'fecha_deshabilitacion_programada',
            'fecha_habilitacion_programada',
            'ultimo_acceso',
            'roles',
            'estado_label',
            'proxima_accion_programada',
            'nombre',
            'apellido',
            'dni',
            'telefono',
            'cargo',
            'directivo_nombre',
            'directivo_apellido',
            'directivo_dni',
            'directivo_telefono',
            'directivo_cargo',
        ]
        extra_kwargs = {
            'contrasena': {'write_only': True},
            'usuario': {'read_only': True},
        }

    def get_roles(self, obj):
        user_roles = UsuarioRol.objects.filter(id_usuario=obj).select_related('id_rol')
        return [ur.id_rol.nombre_rol for ur in user_roles]

    def get_estado_label(self, obj):
        if getattr(obj, 'eliminado', False):
            return 'Eliminado'
        return 'Habilitado' if obj.estado else 'Deshabilitado'

    def get_proxima_accion_programada(self, obj):
        return _proxima_accion_programada(obj)

    def get_directivo_nombre(self, obj):
        directivo = Directivo.objects.filter(id_usuario=obj).first()
        return directivo.nombre if directivo else None

    def get_directivo_apellido(self, obj):
        directivo = Directivo.objects.filter(id_usuario=obj).first()
        return directivo.apellido if directivo else None

    def get_directivo_dni(self, obj):
        directivo = Directivo.objects.filter(id_usuario=obj).first()
        return directivo.dni if directivo else None

    def get_directivo_telefono(self, obj):
        directivo = Directivo.objects.filter(id_usuario=obj).first()
        return directivo.telefono if directivo else None

    def get_directivo_cargo(self, obj):
        directivo = Directivo.objects.filter(id_usuario=obj).first()
        return directivo.cargo if directivo else None

    def validate(self, attrs):
        valores_programacion = {
            'estado': attrs.get(
                'estado',
                getattr(self.instance, 'estado', True),
            ),
            'fecha_deshabilitacion_programada': attrs.get(
                'fecha_deshabilitacion_programada',
                getattr(self.instance, 'fecha_deshabilitacion_programada', None),
            ),
            'fecha_habilitacion_programada': attrs.get(
                'fecha_habilitacion_programada',
                getattr(self.instance, 'fecha_habilitacion_programada', None),
            ),
        }
        _validar_programacion_estado(Usuario(**valores_programacion))

        usuario_nombre = attrs.get('usuario_nombre')
        if usuario_nombre:
            existentes = Usuario.objects.filter(usuario=usuario_nombre)
            if self.instance is not None:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                raise serializers.ValidationError({
                    'usuario_nombre': 'Ese nombre de usuario ya está en uso.',
                })

        dni = attrs.get('dni')
        if dni:
            dni = normalizar_dni(dni)
            existentes = Directivo.all_objects.filter(dni=dni)
            if self.instance is not None:
                existentes = existentes.exclude(id_usuario=self.instance)
            if existentes.exists():
                raise serializers.ValidationError({
                    'dni': 'Ese DNI ya pertenece a otro directivo.',
                })

        if (
            self.instance is None
            and attrs.get('id_usuario_existente') is None
            and not attrs.get('contrasena')
        ):
            raise serializers.ValidationError({
                'contrasena': 'La contraseña es obligatoria al crear un usuario.',
            })
        return attrs

    def create(self, validated_data):
        contrasena = validated_data.pop('contrasena', None)
        roles = self.initial_data.get('roles', [])
        id_usuario_existente = validated_data.pop('id_usuario_existente', None)
        nombre = validated_data.pop('nombre', None)
        apellido = validated_data.pop('apellido', None)
        dni = validated_data.pop('dni', None)
        if dni:
            dni = normalizar_dni(dni)
        telefono = validated_data.pop('telefono', None)
        cargo = validated_data.pop('cargo', None)
        usuario_nombre = validated_data.pop('usuario_nombre', None)

        if id_usuario_existente is not None:
            usuario = Usuario.objects.filter(id_usuario=id_usuario_existente).first()
            if usuario is None:
                raise serializers.ValidationError({
                    'id_usuario_existente': 'El usuario seleccionado no existe.'
                })
            if Alumno.objects.filter(id_usuario_id=id_usuario_existente).exists():
                raise serializers.ValidationError({
                    'id_usuario_existente': 'El usuario seleccionado es un alumno y no puede recibir otro rol.'
                })
        else:
            if not usuario_nombre:
                raise serializers.ValidationError({'usuario_nombre': 'El usuario es obligatorio.'})
            usuario = Usuario(usuario=usuario_nombre, **validated_data)
            if contrasena:
                usuario.set_password(contrasena)
            usuario.save()

        # Assign roles
        if roles:
            for role_name in roles:
                rol = Rol.objects.filter(nombre_rol=role_name).first()
                if rol:
                    UsuarioRol.objects.get_or_create(id_usuario=usuario, id_rol=rol)

        # Create Directivo if fields are provided
        if nombre and apellido and dni:
            directivo = Directivo.all_objects.filter(id_usuario=usuario).first()
            if directivo is not None:
                directivo.nombre = nombre
                directivo.apellido = apellido
                directivo.dni = dni
                if telefono is not None:
                    directivo.telefono = telefono
                if cargo:
                    directivo.cargo = cargo
                # `all_objects` incluye perfiles dados de baja lógica: al reutilizar
                # uno hay que reactivarlo (id_usuario es OneToOne, no admite dos).
                directivo.estado = True
                directivo.fecha_eliminacion = None
                directivo.save()
            else:
                Directivo.objects.create(
                    id_usuario=usuario,
                    nombre=nombre,
                    apellido=apellido,
                    dni=dni,
                    telefono=telefono or '',
                    cargo=cargo or ('Director' if 'director' in roles else 'Administrador')
                )
        # Ensure admin users always have a Directivo profile
        elif any(rol in roles for rol in ('admin', 'director')):
            directivo = Directivo.all_objects.filter(id_usuario=usuario).first()
            if directivo is None:
                # Generate fallback data from username
                parts = usuario.usuario.replace('_', ' ').split()
                if len(parts) >= 2:
                    fb_nombre = ' '.join(parts[:-1]).title()
                    fb_apellido = parts[-1].title()
                else:
                    fb_nombre = usuario.usuario.title()
                    fb_apellido = 'Admin'
                fb_dni = f'{usuario.id_usuario:08d}'
                Directivo.objects.create(
                    id_usuario=usuario,
                    nombre=fb_nombre,
                    apellido=fb_apellido,
                    dni=fb_dni,
                    telefono='',
                    cargo='Director' if 'director' in roles else 'Administrador'
                )
            else:
                # Reutilizar el perfil dado de baja lógica reactivándolo.
                directivo.estado = True
                directivo.fecha_eliminacion = None
                directivo.save()

        return usuario

    def update(self, instance, validated_data):
        contrasena = validated_data.pop('contrasena', None)
        nombre = validated_data.pop('nombre', None)
        apellido = validated_data.pop('apellido', None)
        dni = validated_data.pop('dni', None)
        if dni:
            dni = normalizar_dni(dni)
        telefono = validated_data.pop('telefono', None)
        cargo = validated_data.pop('cargo', None)
        usuario_nombre = validated_data.pop('usuario_nombre', None)

        if usuario_nombre is not None:
            instance.usuario = usuario_nombre

        # R3: al cambiar el estado a mano se limpian las programaciones
        # pendientes (dejarían de ser coherentes con el nuevo estado) si el
        # cliente no mandó fechas explícitas.
        nuevo_estado = validated_data.get('estado', _sentinel)
        if (
            nuevo_estado is not _sentinel
            and nuevo_estado != instance.estado
            and 'fecha_deshabilitacion_programada' not in validated_data
            and 'fecha_habilitacion_programada' not in validated_data
        ):
            instance.fecha_deshabilitacion_programada = None
            instance.fecha_habilitacion_programada = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if contrasena:
            instance.set_password(contrasena)

        instance.save()

        # Update Directivo if exists and fields are provided
        if nombre or apellido or dni or telefono or cargo:
            directivo = Directivo.all_objects.filter(id_usuario=instance).first()
            if directivo:
                if nombre:
                    directivo.nombre = nombre
                if apellido:
                    directivo.apellido = apellido
                if dni:
                    directivo.dni = dni
                if telefono is not None:
                    directivo.telefono = telefono
                if cargo is not None:
                    directivo.cargo = cargo
                directivo.estado = True
                directivo.fecha_eliminacion = None
                directivo.save()

        # Ensure admin users always have a Directivo profile
        admin_rol = Rol.objects.filter(nombre_rol='admin').first()
        if admin_rol and UsuarioRol.objects.filter(id_usuario=instance, id_rol=admin_rol).exists():
            directivo = Directivo.all_objects.filter(id_usuario=instance).first()
            if directivo is None:
                parts = instance.usuario.replace('_', ' ').split()
                if len(parts) >= 2:
                    fb_nombre = ' '.join(parts[:-1]).title()
                    fb_apellido = parts[-1].title()
                else:
                    fb_nombre = instance.usuario.title()
                    fb_apellido = 'Admin'
                fb_dni = f'{instance.id_usuario:08d}'
                Directivo.objects.create(
                    id_usuario=instance,
                    nombre=fb_nombre,
                    apellido=fb_apellido,
                    dni=fb_dni,
                    telefono='',
                    cargo='Administrador'
                )
            else:
                directivo.estado = True
                directivo.fecha_eliminacion = None
                directivo.save()

        return instance


class PadreTutorSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='id_usuario.usuario', read_only=True)
    usuario_nombre = serializers.CharField(write_only=True, required=False)
    contrasena = serializers.CharField(write_only=True, required=False)
    estado = serializers.BooleanField(write_only=True, required=False)
    fecha_deshabilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    fecha_habilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    id_usuario_existente = EnteroOpcionalField(write_only=True, required=False, allow_null=True)
    # Declarado explícitamente para evitar el UniqueValidator automático de DRF:
    # al agregar el rol a un usuario que ya posee un perfil de tutor/familia
    # (sin el rol, por ejemplo), su propio DNI no es un conflicto.
    dni = serializers.CharField(max_length=20, required=True)
    alumnos_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )
    alumnos = serializers.SerializerMethodField()
    cantidad_alumnos = serializers.SerializerMethodField()
    usuario_estado = serializers.SerializerMethodField()
    usuario_fecha_deshabilitacion_programada = serializers.SerializerMethodField()
    usuario_fecha_habilitacion_programada = serializers.SerializerMethodField()
    estado_label = serializers.SerializerMethodField()
    proxima_accion_programada = serializers.SerializerMethodField()

    class Meta:
        model = PadreTutor
        fields = [
            'id_tutor',
            'id_usuario',
            'id_usuario_existente',
            'usuario',
            'usuario_nombre',
            'contrasena',
            'estado',
            'fecha_deshabilitacion_programada',
            'fecha_habilitacion_programada',
            'nombre',
            'apellido',
            'dni',
            'correo',
            'tipo',
            'telefono',
            'direccion',
            'alumnos_ids',
            'alumnos',
            'cantidad_alumnos',
            'usuario_estado',
            'usuario_fecha_deshabilitacion_programada',
            'usuario_fecha_habilitacion_programada',
            'estado_label',
            'proxima_accion_programada',
        ]
        extra_kwargs = {
            'id_usuario': {'read_only': True},
            'telefono': {'required': False, 'allow_blank': True, 'allow_null': True},
            'direccion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'correo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'tipo': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate_dni(self, value):
        return normalizar_dni(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        dni = attrs.get('dni')
        id_usuario_existente = attrs.get('id_usuario_existente')
        if dni:
            dni = normalizar_dni(dni)
            attrs['dni'] = dni
            if id_usuario_existente:
                # Al agregar el rol a un usuario existente no se rechaza el DNI:
                # create() reutiliza el perfil que ya tiene esa persona.
                return attrs
            if self.instance:
                if PadreTutor.all_objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un/a tutor/familia con este/a dni.'})
            else:
                if PadreTutor.all_objects.filter(dni=dni).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un/a tutor/familia con este/a dni.'})
        return attrs

    def get_alumnos(self, obj):
        alumnos = [ta.id_alumno for ta in obj.tutoralumno_set.all()]
        return [
            {
                'id_alumno': al.id_alumno,
                'nombre': al.nombre,
                'apellido': al.apellido,
                'dni': al.dni,
                'id_curso': al.id_curso_id,
                'curso_nombre': al.id_curso.nombre_curso if al.id_curso else None,
                'ciclo_anio': al.id_curso.id_ciclo.anio if al.id_curso and al.id_curso.id_ciclo else None,
            }
            for al in alumnos
        ]

    def get_cantidad_alumnos(self, obj):
        return len(obj.tutoralumno_set.all())

    def get_estado_label(self, obj):
        if not obj.id_usuario:
            return 'Sin usuario'
        return 'Habilitado' if obj.id_usuario.estado else 'Deshabilitado'

    def get_proxima_accion_programada(self, obj):
        return _proxima_accion_programada(obj.id_usuario)

    def get_usuario_estado(self, obj):
        return obj.id_usuario.estado if obj.id_usuario else None

    def get_usuario_fecha_deshabilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_deshabilitacion_programada
        return _formatear_fecha_programada(value)

    def get_usuario_fecha_habilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_habilitacion_programada
        return _formatear_fecha_programada(value)

    def create(self, validated_data):
        alumnos_ids = validated_data.pop('alumnos_ids', [])
        id_usuario_existente = validated_data.get('id_usuario_existente')

        # Si se está agregando el rol a un usuario existente (Agregar rol), validar asignaciones requeridas
        if id_usuario_existente is not None:
            if Alumno.objects.filter(id_usuario_id=id_usuario_existente).exists():
                raise serializers.ValidationError({
                    'id_usuario_existente': 'El usuario seleccionado es un alumno y no puede recibir otro rol.'
                })
            if not alumnos_ids:
                raise serializers.ValidationError({
                    'alumnos_ids': 'Debe asignar al menos un alumno al agregar el rol de tutor/familia.'
                })
        # No se rechaza que la persona ya tenga perfil de tutor/familia: ese perfil
        # se reutiliza y se le reassignan los alumnos indicados (ver más abajo).
        # Sin `id_usuario_existente` se crea una cuenta nueva: aquí
        # `id_usuario_existente` es None y filtrar por él se traduce a
        # `id_usuario_id IS NULL`, una comprobación sin sentido que hacía
        # saltar "El usuario seleccionado ya tiene perfil de tutor/familia"
        # al crear un tutor nuevo. El duplicado de usuario_nombre ya lo
        # valida `_build_usuario_account`.

        try:
            with transaction.atomic():
                usuario, validated_data = _build_usuario_account(
                    instance=self.instance or PadreTutor(),
                    validated_data=validated_data,
                    username_key='usuario_nombre',
                    role_name='familia',
                )

                tutor_existente = PadreTutor.all_objects.filter(id_usuario=usuario).first()
                dni = validated_data.get('dni')
                if tutor_existente is None and dni:
                    # Solo se reutiliza una fila huérfana (sin usuario) o el propio
                    # perfil de la persona; nunca el de otro usuario.
                    perfil_por_dni = PadreTutor.all_objects.filter(dni=dni).first()
                    if perfil_por_dni is not None and perfil_por_dni.id_usuario_id is not None:
                        raise serializers.ValidationError({
                            'dni': 'Ya existe un/a tutor/familia con este/a dni asociado a otro usuario.'
                        })
                    tutor_existente = perfil_por_dni
                if tutor_existente is not None:
                    # `all_objects` incluye los perfiles dados de baja lógica: al
                    # reutilizar uno hay que reactivarlo, ya que `id_usuario` es
                    # OneToOne y no admite un segundo perfil del mismo usuario.
                    if tutor_existente.id_usuario_id != usuario.id_usuario:
                        tutor_existente.id_usuario = usuario
                    for attr, value in validated_data.items():
                        setattr(tutor_existente, attr, value)
                    tutor_existente.estado = True
                    tutor_existente.fecha_eliminacion = None
                    tutor_existente.save()
                    padre = tutor_existente
                    # Se reemplazan únicamente los vínculos de este tutor.
                    TutorAlumno.objects.filter(id_tutor=padre).delete()
                else:
                    padre = PadreTutor.objects.create(id_usuario=usuario, **validated_data)
                _vincular_tutor_alumnos(padre, alumnos_ids)
        except IntegrityError:
            raise serializers.ValidationError({
                'dni': 'Ya existe un/a tutor/familia con este/a dni.'
            })
        return padre

    def update(self, instance, validated_data):
        alumnos_ids = validated_data.pop('alumnos_ids', None)
        usuario, validated_data = _build_usuario_account(
            instance=instance,
            validated_data=validated_data,
            username_key='usuario_nombre',
            role_name='familia',
        )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.id_usuario = usuario
        instance.save()
        if alumnos_ids is not None:
            # Reemplaza SOLO los vínculos de este tutor; no toca a otros tutores.
            TutorAlumno.objects.filter(id_tutor=instance).delete()
            _vincular_tutor_alumnos(instance, alumnos_ids)
        return instance


class PreceptorSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='id_usuario.usuario', read_only=True)
    usuario_nombre = serializers.CharField(write_only=True, required=False)
    contrasena = serializers.CharField(write_only=True, required=False)
    estado = serializers.BooleanField(write_only=True, required=False)
    fecha_deshabilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    fecha_habilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    id_usuario_existente = EnteroOpcionalField(write_only=True, required=False, allow_null=True)
    # Declarado explícitamente para evitar el UniqueValidator automático de DRF:
    # al agregar el rol a un usuario que ya posee un perfil de preceptor (sin rol),
    # su mismo DNI no debe ser considerado como conflicto (validate() ya lo excluye).
    dni = serializers.CharField(max_length=20, required=True)
    cursos_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )
    cursos_asignados = serializers.SerializerMethodField()
    usuario_estado = serializers.SerializerMethodField()
    usuario_fecha_ultimo_acceso = serializers.SerializerMethodField()
    usuario_fecha_deshabilitacion_programada = serializers.SerializerMethodField()
    usuario_fecha_habilitacion_programada = serializers.SerializerMethodField()
    estado_label = serializers.SerializerMethodField()
    proxima_accion_programada = serializers.SerializerMethodField()

    class Meta:
        model = Preceptor
        fields = [
            'id_preceptor',
            'id_usuario',
            'id_usuario_existente',
            'usuario',
            'usuario_nombre',
            'contrasena',
            'estado',
            'fecha_deshabilitacion_programada',
            'fecha_habilitacion_programada',
            'nombre',
            'apellido',
            'dni',
            'correo',
            'telefono',
            'cursos_ids',
            'cursos_asignados',
            'usuario_estado',
            'usuario_fecha_ultimo_acceso',
            'usuario_fecha_deshabilitacion_programada',
            'usuario_fecha_habilitacion_programada',
            'estado_label',
            'proxima_accion_programada',
        ]
        extra_kwargs = {
            'id_usuario': {'read_only': True},
            'correo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'telefono': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate_dni(self, value):
        return normalizar_dni(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        dni = attrs.get('dni')
        id_usuario_existente = attrs.get('id_usuario_existente')
        if dni:
            dni = normalizar_dni(dni)
            attrs['dni'] = dni
            if id_usuario_existente:
                # Al agregar el rol a un usuario existente no se rechaza el DNI:
                # si ya existe un perfil de preceptor con ese DNI (propio o de otra
                # cuenta), create() reutilizará esos datos existentes.
                return attrs
            if self.instance:
                if Preceptor.all_objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un/a preceptor con este/a dni.'})
            else:
                if Preceptor.all_objects.filter(dni=dni).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un/a preceptor con este/a dni.'})
        return attrs

    def get_cursos_asignados(self, obj):
        cursos = obj.curso_set.all()
        return [
            {
                'id_curso': curso.id_curso,
                'nombre_curso': curso.nombre_curso,
                'ciclo_anio': curso.id_ciclo.anio if curso.id_ciclo else None,
            }
            for curso in cursos
        ]

    def get_estado_label(self, obj):
        if not obj.id_usuario:
            return 'Sin usuario'
        return 'Habilitado' if obj.id_usuario.estado else 'Deshabilitado'

    def get_proxima_accion_programada(self, obj):
        return _proxima_accion_programada(obj.id_usuario)

    def get_usuario_estado(self, obj):
        return obj.id_usuario.estado if obj.id_usuario else None

    def get_usuario_fecha_ultimo_acceso(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.ultimo_acceso
        return value.isoformat() if value else None

    def get_usuario_fecha_deshabilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_deshabilitacion_programada
        return _formatear_fecha_programada(value)

    def get_usuario_fecha_habilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_habilitacion_programada
        return _formatear_fecha_programada(value)

    def _role_name_from_context(self):
        return 'jefe_preceptores' if self.context.get('rol') == 'jefe_preceptores' else 'preceptor'

    def _role_name_for_update(self, instance):
        if not getattr(instance, 'id_usuario_id', None):
            return self._role_name_from_context()
        return None

    def _role_name_from_instance(self, instance):
        if not getattr(instance, 'id_usuario_id', None):
            return self._role_name_from_context()
        roles = set(
            UsuarioRol.objects.filter(id_usuario=instance.id_usuario)
            .values_list('id_rol__nombre_rol', flat=True)
        )
        if 'jefe_preceptores' in roles:
            return 'jefe_preceptores'
        if 'preceptor' in roles:
            return 'preceptor'
        return self._role_name_from_context()

    def create(self, validated_data):
        cursos_ids = validated_data.pop('cursos_ids', [])
        es_jefe = self._role_name_from_context() == 'jefe_preceptores'
        id_usuario_existente = validated_data.get('id_usuario_existente')

        # Si se está agregando el rol a un usuario existente (Agregar rol), validar asignaciones requeridas
        if id_usuario_existente is not None:
            if Alumno.objects.filter(id_usuario_id=id_usuario_existente).exists():
                raise serializers.ValidationError({
                    'id_usuario_existente': 'El usuario seleccionado es un alumno y no puede recibir otro rol.'
                })
            if not es_jefe and not cursos_ids:
                raise serializers.ValidationError({
                    'cursos_ids': 'Debe asignar al menos un curso al agregar el rol de preceptor.'
                })
        
        try:
            with transaction.atomic():
                usuario, validated_data = _build_usuario_account(
                    instance=self.instance or Preceptor(),
                    validated_data=validated_data,
                    username_key='usuario_nombre',
                    role_name=self._role_name_from_context(),
                )

                preceptor_existente = Preceptor.all_objects.filter(id_usuario=usuario).first()
                dni = validated_data.get('dni')
                if preceptor_existente is None and dni:
                    # Reutilizar un perfil existente solo si es del mismo usuario o
                    # si es una fila huérfana (sin usuario asignado). Nunca "robar" el
                    # perfil de otra persona: eso genera DNI duplicados o corrupción.
                    perfil_por_dni = Preceptor.all_objects.filter(dni=dni).first()
                    if perfil_por_dni is not None and perfil_por_dni.id_usuario_id is not None:
                        raise serializers.ValidationError({
                            'dni': 'Ya existe un/a preceptor con este/a dni asociado a otro usuario.'
                        })
                    preceptor_existente = perfil_por_dni
                if preceptor_existente is not None:
                    # `all_objects` incluye los perfiles dados de baja lógica: al
                    # reutilizar uno hay que reactivarlo, ya que `id_usuario` es
                    # OneToOne y no admite un segundo perfil del mismo usuario.
                    if preceptor_existente.id_usuario_id != usuario.id_usuario:
                        preceptor_existente.id_usuario = usuario
                    for attr, value in validated_data.items():
                        setattr(preceptor_existente, attr, value)
                    preceptor_existente.estado = True
                    preceptor_existente.fecha_eliminacion = None
                    preceptor_existente.save()
                    preceptor = preceptor_existente
                else:
                    preceptor = Preceptor.objects.create(id_usuario=usuario, **validated_data)

                if not es_jefe and cursos_ids:
                    _validar_cursos_preceptor(cursos_ids, preceptor)
                    cursos_a_desasignar = Curso.objects.filter(id_preceptor=preceptor)
                    ciclo_id = _ciclo_lectivo_actual_id()
                    if ciclo_id:
                        cursos_a_desasignar = cursos_a_desasignar.filter(id_ciclo_id=ciclo_id)
                    cursos_a_desasignar.update(id_preceptor=None)
                    Curso.objects.filter(id_curso__in=cursos_ids).update(id_preceptor=preceptor)
        except IntegrityError:
            raise serializers.ValidationError({
                'dni': 'Ya existe un/a preceptor con este/a dni.'
            })
        return preceptor

    def update(self, instance, validated_data):
        cursos_ids = validated_data.pop('cursos_ids', None)
        es_jefe = self._role_name_from_instance(instance) == 'jefe_preceptores'
        usuario, validated_data = _build_usuario_account(
            instance=instance,
            validated_data=validated_data,
            username_key='usuario_nombre',
            role_name=self._role_name_for_update(instance),
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if cursos_ids is not None and not es_jefe:
            _validar_cursos_preceptor(cursos_ids, instance)
            cursos_a_desasignar = Curso.objects.filter(id_preceptor=instance)
            ciclo_id = _ciclo_lectivo_actual_id()
            if ciclo_id:
                cursos_a_desasignar = cursos_a_desasignar.filter(id_ciclo_id=ciclo_id)
            cursos_a_desasignar.update(id_preceptor=None)
            Curso.objects.filter(id_curso__in=cursos_ids).update(id_preceptor=instance)

        return instance


class DdjjDocenteSerializer(serializers.ModelSerializer):
    archivo = serializers.FileField(write_only=True, required=False)
    docente_nombre = serializers.CharField(source='id_docente.nombre', read_only=True)
    docente_apellido = serializers.CharField(source='id_docente.apellido', read_only=True)
    ciclo_anio = serializers.CharField(source='id_ciclo.anio', read_only=True)
    nombre_archivo = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()
    presentada = serializers.SerializerMethodField()

    class Meta:
        model = DdjjDocente
        fields = [
            'id_ddjj',
            'id_docente',
            'id_ciclo',
            'ciclo_anio',
            'docente_nombre',
            'docente_apellido',
            'archivo',
            'archivo_url',
            'nombre_archivo',
            'fecha_carga',
            'presentada',
            'verificada',
        ]
        extra_kwargs = {
            'verificada': {'read_only': True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'id_ciclo' not in attrs or attrs['id_ciclo'] is None:
            ciclo_id = _ciclo_lectivo_actual_id()
            if ciclo_id:
                attrs['id_ciclo'] = CicloLectivo.objects.filter(id_ciclo=ciclo_id).first()
        docente = attrs.get('id_docente') or getattr(self.instance, 'id_docente', None)
        ciclo = attrs.get('id_ciclo') or getattr(self.instance, 'id_ciclo', None)
        if docente and ciclo:
            qs = DdjjDocente.objects.filter(id_docente=docente, id_ciclo=ciclo)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'id_docente': 'Ya existe una D.D.J.J. presentada para este docente en el ciclo lectivo actual.'}
                )
        return attrs

    def get_nombre_archivo(self, obj):
        if not obj.ruta_archivo:
            return None
        return obj.ruta_archivo.name.split('/')[-1]

    def get_archivo_url(self, obj):
        if not obj.ruta_archivo:
            return None
        try:
            return obj.ruta_archivo.url
        except Exception:
            return media_url(obj.ruta_archivo.name)

    def get_presentada(self, obj):
        return bool(obj.ruta_archivo)

    def create(self, validated_data):
        archivo = validated_data.pop('archivo', None)
        if not archivo:
            raise serializers.ValidationError({'archivo': 'Debes adjuntar un archivo para la DDJJ.'})

        validated_data['verificada'] = False
        instance = DdjjDocente(**validated_data)
        instance.ruta_archivo = archivo
        instance.save()
        return instance

    def update(self, instance, validated_data):
        raise serializers.ValidationError({'archivo': 'Ya posee una D.D.J.J. presentada.'})


class ActividadDocenteArchivoSerializer(serializers.ModelSerializer):
    archivo = serializers.FileField(write_only=True, required=False)
    archivo_url = serializers.SerializerMethodField()
    nombre_archivo = serializers.SerializerMethodField()
    es_principal = serializers.SerializerMethodField()

    class Meta:
        model = ActividadDocenteArchivo
        fields = [
            'id_archivo',
            'id_actividad',
            'archivo',
            'archivo_url',
            'nombre_archivo',
            'fecha_carga',
            'es_principal',
        ]
        extra_kwargs = {
            'id_actividad': {'read_only': True},
        }

    def get_nombre_archivo(self, obj):
        if not obj.ruta_archivo:
            return None
        return obj.ruta_archivo.name.split('/')[-1]

    def get_archivo_url(self, obj):
        if not obj.ruta_archivo:
            return None
        try:
            return obj.ruta_archivo.url
        except Exception:
            return media_url(obj.ruta_archivo.name)

    def get_es_principal(self, obj):
        actividad = getattr(obj, '_actividad', None) or getattr(obj, 'id_actividad', None)
        if not actividad or not getattr(actividad, 'ruta_archivo', None) or not obj.ruta_archivo:
            return False
        return actividad.ruta_archivo.name == obj.ruta_archivo.name

    def create(self, validated_data):
        archivo = validated_data.pop('archivo', None)
        if not archivo:
            raise serializers.ValidationError({'archivo': 'Debes adjuntar un archivo.'})
        instance = ActividadDocenteArchivo(**validated_data)
        instance.ruta_archivo = archivo
        instance.save()
        return instance


class ActividadDocenteSerializer(serializers.ModelSerializer):
    archivo = serializers.FileField(write_only=True, required=False, allow_null=True)
    archivos = serializers.SerializerMethodField()
    curso_nombre = serializers.CharField(source='id_curso_materia.id_curso.nombre_curso', read_only=True)
    materia_nombre = serializers.CharField(source='id_curso_materia.id_materia.nombre_materia', read_only=True)
    docente_nombre = serializers.CharField(source='id_docente.nombre', read_only=True)
    docente_apellido = serializers.CharField(source='id_docente.apellido', read_only=True)
    nombre_archivo = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()
    fecha_subida = serializers.DateTimeField(source='fecha_creacion', read_only=True)
    hora_subida = serializers.SerializerMethodField()

    class Meta:
        model = ActividadDocente
        fields = [
            'id_actividad',
            'id_docente',
            'id_curso_materia',
            'curso_nombre',
            'materia_nombre',
            'docente_nombre',
            'docente_apellido',
            'titulo',
            'descripcion',
            'archivo',
            'archivos',
            'archivo_url',
            'nombre_archivo',
            'fecha_creacion',
            'fecha_subida',
            'hora_subida',
        ]
        extra_kwargs = {
            'id_docente': {'read_only': True},
            'ruta_archivo': {'read_only': True},
        }

    def _archivos_queryset(self, obj):
        archivos = list(obj.archivos_adjuntos.all().order_by('id_archivo'))
        for archivo in archivos:
            archivo._actividad = obj
        return archivos

    def get_archivos(self, obj):
        archivos = self._archivos_queryset(obj)
        if archivos:
            return ActividadDocenteArchivoSerializer(archivos, many=True).data
        if not obj.ruta_archivo:
            return []
        fake = ActividadDocenteArchivo(id_archivo=None, id_actividad=obj, fecha_carga=obj.fecha_creacion)
        fake.ruta_archivo.name = obj.ruta_archivo.name
        fake._actividad = obj
        return [ActividadDocenteArchivoSerializer(fake).data]

    def get_nombre_archivo(self, obj):
        archivos = self._archivos_queryset(obj)
        if archivos:
            return archivos[0].ruta_archivo.name.split('/')[-1]
        if not obj.ruta_archivo:
            return None
        return obj.ruta_archivo.name.split('/')[-1]

    def get_archivo_url(self, obj):
        archivos = self._archivos_queryset(obj)
        if archivos:
            try:
                return archivos[0].ruta_archivo.url
            except Exception:
                return media_url(archivos[0].ruta_archivo.name)
        if not obj.ruta_archivo:
            return None
        try:
            return obj.ruta_archivo.url
        except Exception:
            return media_url(obj.ruta_archivo.name)

    def get_hora_subida(self, obj):
        if not obj.fecha_creacion:
            return None
        return obj.fecha_creacion.strftime('%H:%M')

    def _get_docente_actual(self, request):
        if not request or not request.user or not request.user.is_authenticated:
            return None
        username = request.user.username
        usuario_obj = Usuario.objects.filter(usuario=username).first()
        if not usuario_obj:
            return None
        return Docente.objects.filter(id_usuario=usuario_obj).first()

    def validate(self, attrs):
        request = self.context.get('request')
        docente_actual = self._get_docente_actual(request)
        if not docente_actual:
            raise serializers.ValidationError({'detail': 'No se pudo identificar el docente autenticado.'})

        curso_materia = attrs.get('id_curso_materia') or getattr(self.instance, 'id_curso_materia', None)
        if not curso_materia:
            raise serializers.ValidationError({'id_curso_materia': 'Debes seleccionar un curso y una materia válidos.'})

        resultado = obtener_docente_activo(curso_materia.id_curso_materia)
        if not resultado.docente or resultado.docente.id_docente != docente_actual.id_docente:
            raise serializers.ValidationError({'id_curso_materia': 'No tienes permiso para usar esa asignación.'})

        return attrs

    def create(self, validated_data):
        archivo_legacy = validated_data.pop('archivo', None)
        validated_data.pop('id_docente', None)
        request = self.context.get('request')
        docente_actual = self._get_docente_actual(request)
        if not docente_actual:
            raise serializers.ValidationError({'detail': 'No se pudo identificar el docente autenticado.'})

        instance = ActividadDocente(**validated_data)
        instance.id_docente = docente_actual
        instance.ruta_archivo = ''
        instance.save()

        archivos = list(self.context.get('uploaded_files') or [])
        if archivo_legacy is not None:
            archivos = [archivo_legacy, *archivos]

        for archivo in archivos:
            ActividadDocenteArchivo.objects.create(id_actividad=instance, ruta_archivo=archivo)

        primer_archivo = instance.archivos_adjuntos.order_by('id_archivo').first()
        if primer_archivo:
            instance.ruta_archivo = primer_archivo.ruta_archivo.name
            instance.save(update_fields=['ruta_archivo'])
        return instance

    def update(self, instance, validated_data):
        archivo_legacy = validated_data.pop('archivo', None)
        validated_data.pop('id_docente', None)
        validated_data.pop('id_curso_materia', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        archivos = list(self.context.get('uploaded_files') or [])
        if archivo_legacy is not None:
            archivos = [archivo_legacy, *archivos]

        for archivo in archivos:
            ActividadDocenteArchivo.objects.create(id_actividad=instance, ruta_archivo=archivo)

        if not instance.ruta_archivo:
            primer_archivo = instance.archivos_adjuntos.order_by('id_archivo').first()
            if primer_archivo:
                instance.ruta_archivo = primer_archivo.ruta_archivo.name
                instance.save(update_fields=['ruta_archivo'])
        return instance


class DocenteSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='id_usuario.usuario', read_only=True)
    usuario_nombre = serializers.CharField(write_only=True, required=False)
    contrasena = serializers.CharField(write_only=True, required=False)
    estado = serializers.BooleanField(write_only=True, required=False)
    fecha_deshabilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    fecha_habilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    id_usuario_existente = EnteroOpcionalField(write_only=True, required=False, allow_null=True)
    correo = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    # Declarado explícitamente para evitar el UniqueValidator automático de DRF:
    # al agregar el rol a un usuario que ya posee un perfil de docente (sin rol),
    # su mismo DNI no debe considerarse como conflicto (validate() ya lo excluye).
    dni = serializers.CharField(max_length=20, required=True)
    curso_materia_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )
    ddjj_id = serializers.SerializerMethodField()
    ruta_ddjj = serializers.SerializerMethodField()
    ddjj_presentada = serializers.SerializerMethodField()
    ddjj_verificada = serializers.SerializerMethodField()
    ddjj_fecha_carga = serializers.SerializerMethodField()
    ddjj_nombre_archivo = serializers.SerializerMethodField()
    ddjj_url = serializers.SerializerMethodField()
    usuario_estado = serializers.SerializerMethodField()
    usuario_fecha_deshabilitacion_programada = serializers.SerializerMethodField()
    usuario_fecha_habilitacion_programada = serializers.SerializerMethodField()
    estado_label = serializers.SerializerMethodField()
    proxima_accion_programada = serializers.SerializerMethodField()

    class Meta:
        model = Docente
        fields = [
            'id_docente',
            'id_usuario',
            'id_usuario_existente',
            'usuario',
            'usuario_nombre',
            'contrasena',
            'estado',
            'fecha_deshabilitacion_programada',
            'fecha_habilitacion_programada',
            'nombre',
            'apellido',
            'dni',
            'correo',
            'telefono',
            'ddjj_id',
            'ruta_ddjj',
            'ddjj_presentada',
            'ddjj_verificada',
            'ddjj_fecha_carga',
            'ddjj_nombre_archivo',
            'ddjj_url',
            'usuario_estado',
            'usuario_fecha_deshabilitacion_programada',
            'usuario_fecha_habilitacion_programada',
            'estado_label',
            'proxima_accion_programada',
            'curso_materia_ids',
        ]
        extra_kwargs = {
            'id_usuario': {'read_only': True},
            'correo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'telefono': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate_dni(self, value):
        return normalizar_dni(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        dni = attrs.get('dni')
        id_usuario_existente = attrs.get('id_usuario_existente')
        if dni:
            dni = normalizar_dni(dni)
            attrs['dni'] = dni
            if id_usuario_existente:
                # Al agregar el rol a un usuario existente no se rechaza el DNI:
                # create() reutiliza el perfil que ya tiene esa persona.
                return attrs
            if self.instance:
                if Docente.all_objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un/a docente con este/a dni.'})
            else:
                if Docente.all_objects.filter(dni=dni).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un/a docente con este/a dni.'})
        return attrs

    def _get_ddjj(self, obj):
        ciclo_id = _ciclo_lectivo_actual_id()
        if not ciclo_id:
            return None
        return obj.ddjj_docente.filter(id_ciclo_id=ciclo_id).first()

    def get_ddjj_id(self, obj):
        ddjj = self._get_ddjj(obj)
        return ddjj.id_ddjj if ddjj else None

    def get_ruta_ddjj(self, obj):
        ddjj = self._get_ddjj(obj)
        if not ddjj or not ddjj.ruta_archivo:
            return None
        try:
            return ddjj.ruta_archivo.url
        except Exception:
            return media_url(ddjj.ruta_archivo.name)

    def get_ddjj_presentada(self, obj):
        return self._get_ddjj(obj) is not None

    def get_ddjj_verificada(self, obj):
        ddjj = self._get_ddjj(obj)
        return bool(ddjj and ddjj.verificada)

    def get_ddjj_fecha_carga(self, obj):
        ddjj = self._get_ddjj(obj)
        if not ddjj:
            return None
        return ddjj.fecha_carga

    def get_ddjj_nombre_archivo(self, obj):
        ddjj = self._get_ddjj(obj)
        if not ddjj or not ddjj.ruta_archivo:
            return None
        return ddjj.ruta_archivo.name.split('/')[-1]

    def get_ddjj_url(self, obj):
        ddjj = self._get_ddjj(obj)
        if not ddjj or not ddjj.ruta_archivo:
            return None
        try:
            return ddjj.ruta_archivo.url
        except Exception:
            return media_url(ddjj.ruta_archivo.name)

    def get_usuario_estado(self, obj):
        return obj.id_usuario.estado if obj.id_usuario else None

    def get_usuario_fecha_deshabilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_deshabilitacion_programada
        return _formatear_fecha_programada(value)

    def get_usuario_fecha_habilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_habilitacion_programada
        return _formatear_fecha_programada(value)

    def get_estado_label(self, obj):
        if not obj.id_usuario:
            return 'Sin usuario'
        return 'Habilitado' if obj.id_usuario.estado else 'Deshabilitado'

    def get_proxima_accion_programada(self, obj):
        return _proxima_accion_programada(obj.id_usuario)

    def create(self, validated_data):
        curso_materia_ids = validated_data.pop('curso_materia_ids', [])
        id_usuario_existente = validated_data.get('id_usuario_existente')

        # Si se está agregando el rol a un usuario existente (Agregar rol), validar asignaciones requeridas
        if id_usuario_existente is not None:
            if Alumno.objects.filter(id_usuario_id=id_usuario_existente).exists():
                raise serializers.ValidationError({
                    'id_usuario_existente': 'El usuario seleccionado es un alumno y no puede recibir otro rol.'
                })
            if not curso_materia_ids:
                raise serializers.ValidationError({
                    'curso_materia_ids': 'Debe asignar al menos una relación curso-materia al agregar el rol de docente.'
                })
        # No se rechaza que la persona ya tenga perfil de docente: en ese caso el
        # perfil se reutiliza (ver más abajo). Solo se impedía duplicarlo, que era
        # justo el error que veía el usuario al reasignar un rol.
        # Sin `id_usuario_existente` se crea una cuenta nueva: filtrar por None
        # se traduce a `id_usuario_id IS NULL` y producía el error falso
        # "El usuario seleccionado ya tiene perfil de docente". El duplicado de
        # usuario_nombre lo valida `_build_usuario_account`.

        try:
            with transaction.atomic():
                usuario, validated_data = _build_usuario_account(
                    instance=self.instance or Docente(),
                    validated_data=validated_data,
                    username_key='usuario_nombre',
                    role_name='docente',
                )

                docente_existente = Docente.all_objects.filter(id_usuario=usuario).first()
                dni = validated_data.get('dni')
                if docente_existente is None and dni:
                    # Reutilizar un perfil existente solo si es del mismo usuario o
                    # si es una fila huérfana (sin usuario asignado). Nunca "robar" el
                    # perfil de otra persona: eso genera DNI duplicados o corrupción.
                    perfil_por_dni = Docente.all_objects.filter(dni=dni).first()
                    if perfil_por_dni is not None and perfil_por_dni.id_usuario_id is not None:
                        raise serializers.ValidationError({
                            'dni': 'Ya existe un/a docente con este/a dni asociado a otro usuario.'
                        })
                    docente_existente = perfil_por_dni
                if docente_existente is not None:
                    # `all_objects` incluye los perfiles dados de baja lógica: si el
                    # perfil se reutiliza hay que reactivarlo, porque `id_usuario` es
                    # OneToOne y una fila nueva con el mismo usuario sería duplicada.
                    if docente_existente.id_usuario_id != usuario.id_usuario:
                        docente_existente.id_usuario = usuario
                    for attr, value in validated_data.items():
                        setattr(docente_existente, attr, value)
                    docente_existente.estado = True
                    docente_existente.fecha_eliminacion = None
                    docente_existente.save()
                    docente = docente_existente
                else:
                    docente = Docente.objects.create(id_usuario=usuario, **validated_data)

                # Asignar curso_materia si se proporcionaron
                if curso_materia_ids:
                    _validar_curso_materia_docente(curso_materia_ids, docente)
                    CursoMateria.objects.filter(
                        id_curso_materia__in=curso_materia_ids,
                    ).update(id_docente=docente)
        except IntegrityError:
            raise serializers.ValidationError({
                'dni': 'Ya existe un/a docente con este/a dni.'
            })

        return docente

    def update(self, instance, validated_data):
        curso_materia_ids = validated_data.pop('curso_materia_ids', None)
        usuario, validated_data = _build_usuario_account(
            instance=instance,
            validated_data=validated_data,
            username_key='usuario_nombre',
            role_name='docente',
        )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.id_usuario = usuario
        instance.save()

        if curso_materia_ids is not None:
            _validar_curso_materia_docente(curso_materia_ids, instance)
            CursoMateria.objects.filter(
                id_curso_materia__in=curso_materia_ids,
            ).update(id_docente=instance)
        return instance


class DirectivoSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='id_usuario.usuario', read_only=True)
    usuario_estado = serializers.SerializerMethodField()
    usuario_fecha_deshabilitacion_programada = serializers.SerializerMethodField()
    usuario_fecha_habilitacion_programada = serializers.SerializerMethodField()

    class Meta:
        model = Directivo
        fields = '__all__'

    def get_usuario_estado(self, obj):
        return obj.id_usuario.estado if obj.id_usuario else None

    def get_usuario_fecha_deshabilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_deshabilitacion_programada
        return _formatear_fecha_programada(value)

    def get_usuario_fecha_habilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_habilitacion_programada
        return _formatear_fecha_programada(value)


class AlumnoSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='id_usuario.usuario', read_only=True)
    usuario_nombre = serializers.CharField(write_only=True, required=False)
    contrasena = serializers.CharField(write_only=True, required=False)
    estado = serializers.BooleanField(write_only=True, required=False)
    fecha_deshabilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    fecha_habilitacion_programada = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    id_usuario_existente = EnteroOpcionalField(write_only=True, required=False, allow_null=True)
    curso_nombre = serializers.CharField(
        source='id_curso.nombre_curso', read_only=True, default=None,
    )
    ciclo_anio = serializers.IntegerField(
        source='id_curso.id_ciclo.anio', read_only=True, default=None,
    )
    tutor_nombre = serializers.SerializerMethodField()
    usuario_estado = serializers.SerializerMethodField()
    usuario_fecha_deshabilitacion_programada = serializers.SerializerMethodField()
    usuario_fecha_habilitacion_programada = serializers.SerializerMethodField()
    estado_label = serializers.SerializerMethodField()
    proxima_accion_programada = serializers.SerializerMethodField()

    class Meta:
        model = Alumno
        fields = [
            'id_alumno',
            'id_usuario',
            'id_usuario_existente',
            'usuario',
            'usuario_nombre',
            'contrasena',
            'estado',
            'fecha_deshabilitacion_programada',
            'fecha_habilitacion_programada',
            'id_tutor',
            'id_curso',
            'nombre',
            'apellido',
            'dni',
            'fecha_nacimiento',
            'direccion',
            'telefono',
            'procedencia',
            'curso_nombre',
            'ciclo_anio',
            'tutor_nombre',
            'usuario_estado',
            'usuario_fecha_deshabilitacion_programada',
            'usuario_fecha_habilitacion_programada',
            'estado_label',
            'proxima_accion_programada',
        ]
        extra_kwargs = {
            'id_usuario': {'read_only': True},
            'id_tutor': {'required': False, 'allow_null': True},
            'id_curso': {'required': False, 'allow_null': True},
            'direccion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'telefono': {'required': False, 'allow_blank': True, 'allow_null': True},
            'procedencia': {'required': False, 'allow_blank': True, 'allow_null': True},
            'dni': {'validators': []},
        }

    def validate_dni(self, value):
        value = normalizar_dni(value)
        digitos = ''.join(ch for ch in str(value) if ch.isdigit())
        if not digitos.isdigit() or not (30_000_000 <= int(digitos) <= 65_000_000):
            raise serializers.ValidationError(
                'El DNI del estudiante debe estar entre 30.000.000 y 65.000.000.'
            )
        qs = Alumno.all_objects.filter(dni=value)
        if getattr(self.instance, 'id_alumno', None) is not None:
            qs = qs.exclude(id_alumno=self.instance.id_alumno)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un estudiante con ese DNI.')
        return value

    def get_tutor_nombre(self, obj):
        if obj.id_tutor:
            return f'{obj.id_tutor.apellido}, {obj.id_tutor.nombre}'
        return None

    def get_usuario_estado(self, obj):
        return obj.id_usuario.estado if obj.id_usuario else None

    def get_usuario_fecha_deshabilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_deshabilitacion_programada
        return _formatear_fecha_programada(value)

    def get_usuario_fecha_habilitacion_programada(self, obj):
        if not obj.id_usuario:
            return None
        value = obj.id_usuario.fecha_habilitacion_programada
        return _formatear_fecha_programada(value)

    def get_estado_label(self, obj):
        if not obj.id_usuario:
            return 'Sin usuario'
        return 'Habilitado' if obj.id_usuario.estado else 'Deshabilitado'

    def get_proxima_accion_programada(self, obj):
        return _proxima_accion_programada(obj.id_usuario)

    def create(self, validated_data):
        id_usuario_existente = validated_data.get('id_usuario_existente')
        if id_usuario_existente is not None and Alumno.objects.filter(id_usuario_id=id_usuario_existente).exists():
            raise serializers.ValidationError({
                'id_usuario_existente': 'El usuario seleccionado ya tiene perfil de alumno.'
            })
        usuario, validated_data = _build_usuario_account(
            instance=self.instance or Alumno(),
            validated_data=validated_data,
            username_key='usuario_nombre',
            role_name='alumno',
        )
        alumno = Alumno.objects.create(id_usuario=usuario, **validated_data)
        return alumno

    def update(self, instance, validated_data):
        usuario, validated_data = _build_usuario_account(
            instance=instance,
            validated_data=validated_data,
            username_key='usuario_nombre',
            role_name='alumno',
        )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.id_usuario = usuario
        instance.save()
        return instance


# ---------- Estructura académica ----------

class CursoSerializer(serializers.ModelSerializer):
    preceptor_nombre = serializers.SerializerMethodField()
    preceptor_nombre_completo = serializers.SerializerMethodField()
    ciclo_anio = serializers.IntegerField(
        source='id_ciclo.anio', read_only=True, default=None,
    )
    turno_calculado = serializers.SerializerMethodField()

    class Meta:
        model = Curso
        fields = '__all__'

    def get_preceptor_nombre(self, obj):
        if obj.id_preceptor:
            return f'{obj.id_preceptor.apellido}, {obj.id_preceptor.nombre}'
        return None

    def get_preceptor_nombre_completo(self, obj):
        if obj.id_preceptor:
            return f'{obj.id_preceptor.nombre} {obj.id_preceptor.apellido}'
        return None

    def get_turno_calculado(self, obj):
        horarios = []
        for cm in obj.cursomateria_set.all():
            horarios.extend(cm.horario_set.all())
        manana = 0
        tarde = 0
        for h in horarios:
            if h.id_modulo and h.id_modulo.hora_inicio:
                if h.id_modulo.hora_inicio.hour < HORA_CORTE_TURNO:
                    manana += 1
                else:
                    tarde += 1
        if manana > tarde:
            return 'Mañana'
        if tarde > manana:
            return 'Tarde'
        return ''

    def validate(self, attrs):
        nombre = attrs.get('nombre_curso', getattr(self.instance, 'nombre_curso', None))
        ciclo = attrs.get('id_ciclo', getattr(self.instance, 'id_ciclo', None))
        if nombre and ciclo is not None:
            qs = Curso.objects.filter(nombre_curso=nombre, id_ciclo=ciclo)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'nombre_curso': 'Ya existe un curso con ese año, división y ciclo lectivo.'
                })
        return attrs

    def create(self, validated_data):
        from escuela.utils import activar_o_crear
        lookup = {
            'nombre_curso': validated_data.get('nombre_curso'),
            'id_ciclo': validated_data.get('id_ciclo'),
        }
        defaults = {k: v for k, v in validated_data.items() if k not in lookup}
        instance, _ = activar_o_crear(Curso, lookup, defaults)
        return instance


class CursoMateriaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(
        source='id_curso.nombre_curso', read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_materia.nombre_materia', read_only=True, default=None,
    )
    # Punto 5.2: la orientación se lee del curso (Curso.orientacion), nunca se
    # infiere a partir del año o la división.
    curso_orientacion = serializers.CharField(
        source='id_curso.orientacion', read_only=True, default=None,
    )
    id_docente = serializers.PrimaryKeyRelatedField(
        queryset=Docente.objects.all(), required=False, allow_null=True,
    )
    docente_nombre = serializers.SerializerMethodField()
    horarios_count = serializers.SerializerMethodField()

    class Meta:
        model = CursoMateria
        fields = '__all__'

    def get_docente_nombre(self, obj):
        if obj.id_docente_id:
            return f'{obj.id_docente.apellido}, {obj.id_docente.nombre}'
        return None

    def get_horarios_count(self, obj):
        return len(obj.horario_set.all()) + len(obj.horariosespeciales_set.all())

    def validate(self, attrs):
        curso = attrs.get('id_curso', getattr(self.instance, 'id_curso', None))
        materia = attrs.get('id_materia', getattr(self.instance, 'id_materia', None))
        if curso is not None and materia is not None:
            qs = CursoMateria.objects.filter(id_curso=curso, id_materia=materia)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'Ya existe una asignación de esa materia para este curso.'
                )
        return attrs

    def create(self, validated_data):
        from escuela.utils import activar_o_crear
        lookup = {
            'id_curso': validated_data.get('id_curso'),
            'id_materia': validated_data.get('id_materia'),
        }
        defaults = {k: v for k, v in validated_data.items() if k not in lookup}
        instance, _ = activar_o_crear(CursoMateria, lookup, defaults)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'id_curso' in data and data['id_curso'] is not None:
            try:
                data['curso_nombre'] = instance.id_curso.nombre_curso
            except:
                data['curso_nombre'] = None
        if 'id_materia' in data and data['id_materia'] is not None:
            try:
                data['materia_nombre'] = instance.id_materia.nombre_materia
            except:
                data['materia_nombre'] = None
        return data


# ---------- Suplencias docentes ----------

DIAS_SEMANA_ES_SUPL = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


def _bloques_cm_suplencia(cm_id, dia_semana):
    tiempos = []
    for h in Horario.objects.filter(id_curso_materia_id=cm_id, dia_semana=dia_semana, id_modulo__isnull=False).select_related('id_modulo'):
        if h.id_modulo and h.id_modulo.hora_inicio and h.id_modulo.hora_fin:
            tiempos.append((h.id_modulo.hora_inicio, h.id_modulo.hora_fin))
    for h in HorariosEspeciales.objects.filter(id_curso_materia_id=cm_id, dia_semana=dia_semana):
        if h.hora_inicio and h.hora_fin:
            tiempos.append((h.hora_inicio, h.hora_fin))
    tiempos.sort(key=lambda x: x[0])
    bloques = []
    for inicio, fin in tiempos:
        if bloques and inicio <= bloques[-1][1]:
            bloques[-1] = (bloques[-1][0], max(bloques[-1][1], fin))
        else:
            bloques.append((inicio, fin))
    return bloques


class SuplenciaDocenteSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso', read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia', read_only=True, default=None,
    )
    id_docente_suplente = serializers.PrimaryKeyRelatedField(
        queryset=Docente.objects.all(), required=False, allow_null=True,
    )
    suplente_nombre = serializers.SerializerMethodField()
    titular_id = serializers.SerializerMethodField()
    titular_nombre = serializers.SerializerMethodField()
    docente_activo_hoy = serializers.SerializerMethodField()
    estado_label = serializers.SerializerMethodField()
    fecha_finalizacion_real = serializers.SerializerMethodField()
    nuevo_docente = serializers.DictField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = SuplenciaDocente
        fields = [
            'id_suplencia',
            'id_curso_materia',
            'curso_nombre',
            'materia_nombre',
            'id_docente_suplente',
            'suplente_nombre',
            'titular_id',
            'titular_nombre',
            'docente_activo_hoy',
            'nivel',
            'motivo',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'estado_label',
            'fecha_finalizacion_real',
            'fecha_creacion',
            'fecha_modificacion',
            'nuevo_docente',
        ]
        extra_kwargs = {
            'fecha_creacion': {'read_only': True},
            'fecha_modificacion': {'read_only': True},
        }

    def get_suplente_nombre(self, obj):
        if obj.id_docente_suplente_id:
            return f'{obj.id_docente_suplente.apellido}, {obj.id_docente_suplente.nombre}'
        return None

    def get_titular_id(self, obj):
        try:
            return obj.id_curso_materia.id_docente_id
        except Exception:
            return None

    def get_titular_nombre(self, obj):
        try:
            cm = obj.id_curso_materia
        except Exception:
            return None
        if cm and cm.id_docente_id:
            return f'{cm.id_docente.apellido}, {cm.id_docente.nombre}'
        return None

    def get_docente_activo_hoy(self, obj):
        cm_id = getattr(obj, 'id_curso_materia_id', None)
        if not cm_id:
            return None
        try:
            cm = obj.id_curso_materia
        except Exception:
            return None
        if cm is None:
            return None
        titular = cm.id_docente
        activas = getattr(cm, '_suplencias_activas', None)
        if activas is None:
            activas = list(
                SuplenciaDocente.objects
                .filter(
                    id_curso_materia_id=cm_id,
                    estado=True,
                    fecha_inicio__lte=timezone.localdate(),
                    fecha_fin__gte=timezone.localdate(),
                )
                .order_by('-nivel', '-fecha_inicio')
                .select_related('id_docente_suplente', 'id_curso_materia')
            )
        suplencia = activas[0] if activas else None
        if suplencia:
            docente = suplencia.id_docente_suplente
            if not docente:
                return None
            return {
                'id_docente': docente.id_docente,
                'nombre': f'{docente.apellido}, {docente.nombre}',
                'es_suplencia': True,
            }
        if not titular:
            return None
        return {
            'id_docente': titular.id_docente,
            'nombre': f'{titular.apellido}, {titular.nombre}',
            'es_suplencia': False,
        }

    def get_estado_label(self, obj):
        # C6/S2: una suplencia está "Finalizada" si fue dada de baja (estado=False)
        # o si su `fecha_fin` ya pasó; no alcanza con mirar `estado`, porque
        # "finalizar" conserva estado=True y cierra la fecha.
        if not obj.estado:
            return 'Finalizada'
        if obj.fecha_fin and obj.fecha_fin < timezone.localdate():
            return 'Finalizada'
        return 'Activa'

    def get_fecha_finalizacion_real(self, obj):
        if obj.estado and obj.fecha_fin and obj.fecha_fin < timezone.localdate():
            return obj.fecha_fin
        if obj.fecha_modificacion:
            return timezone.localtime(obj.fecha_modificacion).date()
        return obj.fecha_fin

    def validate(self, attrs):
        cm = attrs.get('id_curso_materia') or (self.instance.id_curso_materia if self.instance else None)
        if cm is None:
            raise serializers.ValidationError(
                {'id_curso_materia': 'Debe indicar la materia asignada.'}
            )

        suplente = attrs.get('id_docente_suplente') or (
            self.instance.id_docente_suplente if self.instance else None
        )
        nuevo_docente = attrs.get('nuevo_docente') or {}

        if suplente is None and not nuevo_docente:
            raise serializers.ValidationError(
                'Debe indicar el docente suplente (existente) o cargar los datos de un nuevo docente.'
            )

        fi = attrs.get('fecha_inicio') or (self.instance.fecha_inicio if self.instance else None)
        ff = attrs.get('fecha_fin') or (self.instance.fecha_fin if self.instance else None)
        if fi and ff and fi > ff:
            raise serializers.ValidationError(
                {'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'}
            )

        if cm.id_docente_id and suplente is not None and suplente.id_docente == cm.id_docente_id:
            raise serializers.ValidationError(
                'El docente suplente no puede ser el mismo que el docente titular de la materia.'
            )

        if not (fi and ff):
            return attrs

        nivel = attrs.get('nivel') or (self.instance.nivel if self.instance else None) or 1

        exclude = None
        if self.instance:
            exclude = SuplenciaDocente.all_objects.filter(pk=self.instance.pk).first()

        if suplente is not None:
            duplicada = SuplenciaDocente.objects.filter(
                id_curso_materia=cm,
                id_docente_suplente=suplente,
                nivel=nivel,
                fecha_inicio=fi,
                fecha_fin=ff,
            )
            if exclude is not None:
                duplicada = duplicada.exclude(pk=exclude.pk)
            if duplicada.exists():
                raise serializers.ValidationError(
                    'Ya existe una suplencia idéntica para ese docente, materia y período.'
                )

        solapada = SuplenciaDocente.objects.filter(
            id_curso_materia=cm,
            nivel=nivel,
            estado=True,
            fecha_inicio__lte=ff,
            fecha_fin__gte=fi,
        )
        if exclude is not None:
            solapada = solapada.exclude(pk=exclude.pk)
        if solapada.exists():
            raise serializers.ValidationError(
                'Ya existe una suplencia activa de ese nivel para esa materia en el período indicado.'
            )

        ciclo = CicloLectivo.objects.filter(estado=True).order_by('-anio').first()
        if ciclo and (
            (ciclo.fecha_inicio and fi < ciclo.fecha_inicio)
            or (ciclo.fecha_fin and ff > ciclo.fecha_fin)
        ):
            raise serializers.ValidationError(
                'Las fechas de la suplencia deben estar dentro del ciclo lectivo activo.'
            )

        if suplente is not None:
            cm_ids = set(CursoMateria.objects.filter(id_docente=suplente).values_list('pk', flat=True))
            cm_ids.update(
                SuplenciaDocente.objects.filter(
                    id_docente_suplente=suplente, estado=True,
                    fecha_inicio__lte=ff, fecha_fin__gte=fi,
                ).values_list('id_curso_materia_id', flat=True)
            )
            cm_ids.discard(cm.pk)
            if exclude is not None:
                cm_ids.discard(exclude.id_curso_materia_id)
            dia = fi
            while dia <= ff:
                dia_semana = DIAS_SEMANA_ES_SUPL[dia.weekday()]
                bloques_nuevos = _bloques_cm_suplencia(cm.pk, dia_semana)
                for otro_cm_id in cm_ids:
                    for ini_nuevo, fin_nuevo in bloques_nuevos:
                        for ini_otro, fin_otro in _bloques_cm_suplencia(otro_cm_id, dia_semana):
                            if franjas_se_solapan(ini_nuevo, fin_nuevo, ini_otro, fin_otro):
                                raise serializers.ValidationError(
                                    'El docente suplente ya tiene otra clase asignada en ese horario.'
                                )
                dia += timedelta(days=1)

        return attrs

    def create(self, validated_data):
        suplente = validated_data.get('id_docente_suplente')
        if suplente is None:
            nuevo = validated_data.pop('nuevo_docente', None) or {}
            if not nuevo:
                raise serializers.ValidationError(
                    {'nuevo_docente': 'Debe indicar el docente suplente o sus datos de alta.'}
                )
            docente_serializer = DocenteSerializer(data=nuevo)
            docente_serializer.is_valid(raise_exception=True)
            validated_data['id_docente_suplente'] = docente_serializer.save()
        else:
            validated_data.pop('nuevo_docente', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        nuevo = validated_data.pop('nuevo_docente', None) or {}
        if nuevo:
            docente_serializer = DocenteSerializer(data=nuevo)
            docente_serializer.is_valid(raise_exception=True)
            validated_data['id_docente_suplente'] = docente_serializer.save()
        return super().update(instance, validated_data)


class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulos
        fields = '__all__'

    def validate_nombre(self, value):
        nombre = (value or '').strip()
        if not nombre:
            raise serializers.ValidationError('El nombre del módulo es obligatorio.')
        if len(nombre) > 50:
            raise serializers.ValidationError(
                'El nombre del módulo puede tener hasta 50 caracteres.'
            )
        qs = Modulos.objects.filter(nombre__iexact=nombre)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un módulo con ese nombre.')
        return nombre

    def validate(self, attrs):
        inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        fin = attrs.get('hora_fin', getattr(self.instance, 'hora_fin', None))
        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError({
                'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.',
            })
        return attrs


def _conflicto_de_horario(
    *, curso_id, docente_id, aula, dia_semana, hora_inicio, hora_fin,
    excluir_horario=None, excluir_especial=None,
):
    """Busca choques de curso, docente o aula contra la grilla ya cargada.

    Compara contra los horarios regulares (la franja sale del módulo) y los
    horarios especiales (hora_inicio/hora_fin) por igual: un curso, un docente
    o un aula no pueden estar en dos lugares a la vez. Devuelve el mensaje del
    primer choque encontrado, o ``None`` si no hay ninguno.
    """
    if not dia_semana or hora_inicio is None or hora_fin is None:
        return None

    aula_norm = (aula or '').strip().lower()
    candidatos = []
    for h in Horario.objects.filter(
        dia_semana__iexact=dia_semana, id_modulo__isnull=False,
    ).select_related('id_modulo', 'id_curso_materia'):
        if excluir_horario is not None and h.pk == excluir_horario:
            continue
        candidatos.append((
            h.id_curso_materia.id_curso_id,
            h.id_curso_materia.id_docente_id,
            h.aula,
            h.id_modulo.hora_inicio,
            h.id_modulo.hora_fin,
        ))
    for h in HorariosEspeciales.objects.filter(
        dia_semana__iexact=dia_semana,
    ).select_related('id_curso_materia'):
        if excluir_especial is not None and h.pk == excluir_especial:
            continue
        candidatos.append((
            h.id_curso_materia.id_curso_id,
            h.id_curso_materia.id_docente_id,
            h.aula,
            h.hora_inicio,
            h.hora_fin,
        ))

    for curso_existente, docente_existente, aula_existente, ini, fin in candidatos:
        if not franjas_se_solapan(hora_inicio, hora_fin, ini, fin):
            continue
        if curso_id is not None and curso_existente == curso_id:
            return 'El curso ya tiene otra materia asignada en ese día y franja horaria.'
        if docente_id is not None and docente_existente == docente_id:
            return 'El docente ya tiene otra clase en ese día y franja horaria.'
        if aula_norm and (aula_existente or '').strip().lower() == aula_norm:
            return 'El aula ya está ocupada por otro curso en ese día y franja horaria.'
    return None


class HorarioSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso',
        read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia',
        read_only=True, default=None,
    )
    docente_nombre = serializers.SerializerMethodField()
    id_curso = serializers.IntegerField(
        source='id_curso_materia.id_curso.id_curso',
        read_only=True, default=None,
    )
    modulo_nombre = serializers.CharField(
        source='id_modulo.nombre',
        read_only=True, default=None,
    )
    modulo_hora_inicio = serializers.TimeField(
        source='id_modulo.hora_inicio',
        read_only=True, default=None,
    )
    modulo_hora_fin = serializers.TimeField(
        source='id_modulo.hora_fin',
        read_only=True, default=None,
    )

    class Meta:
        model = Horario
        fields = '__all__'
        read_only_fields = ('fecha_eliminacion',)

    def get_docente_nombre(self, obj):
        docente = getattr(obj.id_curso_materia, 'id_docente', None)
        if docente:
            return f'{docente.apellido}, {docente.nombre}'
        return None

    def validate(self, attrs):
        cm = attrs.get('id_curso_materia', getattr(self.instance, 'id_curso_materia', None))
        modulo = attrs.get('id_modulo', getattr(self.instance, 'id_modulo', None))
        dia_semana = attrs.get('dia_semana', getattr(self.instance, 'dia_semana', None))
        aula = attrs.get('aula', getattr(self.instance, 'aula', None))
        if cm is not None and modulo is not None:
            err = _conflicto_de_horario(
                curso_id=cm.id_curso_id,
                docente_id=cm.id_docente_id,
                aula=aula,
                dia_semana=dia_semana,
                hora_inicio=modulo.hora_inicio,
                hora_fin=modulo.hora_fin,
                excluir_horario=self.instance.pk if self.instance else None,
            )
            if err:
                raise serializers.ValidationError({'non_field_errors': [err]})
        return attrs


class HorarioEspecialSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso',
        read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia',
        read_only=True, default=None,
    )
    id_curso = serializers.IntegerField(
        source='id_curso_materia.id_curso.id_curso',
        read_only=True, default=None,
    )

    class Meta:
        model = HorariosEspeciales
        fields = '__all__'
        read_only_fields = ('fecha_eliminacion',)

    def validate(self, attrs):
        inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        fin = attrs.get('hora_fin', getattr(self.instance, 'hora_fin', None))
        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError({
                'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.',
            })
        cm = attrs.get('id_curso_materia', getattr(self.instance, 'id_curso_materia', None))
        dia_semana = attrs.get('dia_semana', getattr(self.instance, 'dia_semana', None))
        aula = attrs.get('aula', getattr(self.instance, 'aula', None))
        if cm is not None and inicio and fin:
            err = _conflicto_de_horario(
                curso_id=cm.id_curso_id,
                docente_id=cm.id_docente_id,
                aula=aula,
                dia_semana=dia_semana,
                hora_inicio=inicio,
                hora_fin=fin,
                excluir_especial=self.instance.pk if self.instance else None,
            )
            if err:
                raise serializers.ValidationError({'non_field_errors': [err]})
        return attrs


class InscripcionMateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InscripcionMateria
        fields = '__all__'


# ---------- Calificaciones ----------

class CalificacionSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.SerializerMethodField()
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia',
        read_only=True, default=None,
    )
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso',
        read_only=True, default=None,
    )
    periodo_nombre = serializers.CharField(
        source='id_periodo.nombre_periodo',
        read_only=True, default=None,
    )

    class Meta:
        model = Calificacion
        fields = '__all__'
        read_only_fields = ('fecha_eliminacion',)

    def get_alumno_nombre(self, obj):
        if obj.id_alumno:
            return f'{obj.id_alumno.apellido}, {obj.id_alumno.nombre}'
        return None

    def validate(self, attrs):
        # N3: la nota se valida en el backend (1–10); el input del frontend no
        # es suficiente porque la API es accesible directamente.
        nota = attrs.get('nota_numerica', serializers.empty)
        if nota is not serializers.empty and nota is not None:
            if nota < 1 or nota > 10:
                raise serializers.ValidationError({
                    'nota_numerica': 'La nota debe estar entre 1 y 10.'
                })

        # N3: una sola calificación por alumno + materia (curso_materia) + período.
        alumno = attrs.get('id_alumno', getattr(self.instance, 'id_alumno', None))
        cm = attrs.get('id_curso_materia', getattr(self.instance, 'id_curso_materia', None))
        periodo = attrs.get('id_periodo', getattr(self.instance, 'id_periodo', None))
        if alumno is not None and cm is not None:
            if not alumno_pertenece_a_curso_materia(
                getattr(alumno, 'pk', alumno),
                getattr(cm, 'pk', cm),
            ):
                raise serializers.ValidationError({
                    'id_alumno': 'El estudiante no pertenece al curso de esta materia.'
                })
        if alumno is not None and cm is not None and periodo is not None:
            qs = Calificacion.all_objects.filter(
                id_alumno=alumno,
                id_curso_materia=cm,
                id_periodo=periodo,
                estado=True,
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'id_periodo': 'Ya existe una calificación de este alumno para esta materia en este período.'
                })
        return attrs

    def create(self, validated_data):
        alumno = validated_data.get('id_alumno')
        cm = validated_data.get('id_curso_materia')
        periodo = validated_data.get('id_periodo')
        if alumno is not None and cm is not None and periodo is not None:
            existente = Calificacion.all_objects.filter(
                id_alumno=alumno,
                id_curso_materia=cm,
                id_periodo=periodo,
                estado=False,
            ).first()
            if existente is not None:
                for attr, value in validated_data.items():
                    setattr(existente, attr, value)
                existente.estado = True
                existente.fecha_eliminacion = None
                existente.save()
                return existente
        return super().create(validated_data)


# ---------- Asistencias ----------

class AsistenciaSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.SerializerMethodField()
    estado_nombre = serializers.CharField(
        source='id_estado_asistencia.nombre_estado',
        read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia',
        read_only=True, default=None,
    )
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso',
        read_only=True, default=None,
    )

    class Meta:
        model = Asistencia
        fields = '__all__'

    def get_alumno_nombre(self, obj):
        if obj.id_alumno:
            return f'{obj.id_alumno.apellido}, {obj.id_alumno.nombre}'
        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        alumno = attrs.get('id_alumno', getattr(self.instance, 'id_alumno', None))
        cm = attrs.get('id_curso_materia', getattr(self.instance, 'id_curso_materia', None))
        if alumno is not None and cm is not None:
            if not alumno_pertenece_a_curso_materia(
                getattr(alumno, 'pk', alumno),
                getattr(cm, 'pk', cm),
            ):
                raise serializers.ValidationError({
                    'id_alumno': 'El estudiante no pertenece al curso de esta materia.'
                })
        justificado = attrs.get('justificado', getattr(self.instance, 'justificado', False))
        estado = attrs.get('id_estado_asistencia', getattr(self.instance, 'id_estado_asistencia', None))
        nombre = getattr(estado, 'nombre_estado', None)
        if justificado and nombre and nombre not in ('Ausente', 'Justificado'):
            raise serializers.ValidationError(
                {'justificado': 'Solo se puede justificar una asistencia ausente.'}
            )
        if nombre == 'Justificado':
            ausente = EstadoAsistencia.objects.filter(nombre_estado='Ausente').first()
            if ausente:
                attrs['id_estado_asistencia'] = ausente
                attrs['justificado'] = True
        return attrs

    def update(self, instance, validated_data):
        estado = validated_data.get('id_estado_asistencia')
        if estado and getattr(estado, 'nombre_estado', None) not in ('Ausente', 'Justificado'):
            validated_data['justificado'] = False
        return super().update(instance, validated_data)


class AsistenciaDocenteSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.SerializerMethodField()
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia',
        read_only=True, default=None,
    )
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso',
        read_only=True, default=None,
    )
    estado_nombre = serializers.CharField(
        source='id_estado_asistencia.nombre_estado',
        read_only=True, default=None,
    )

    class Meta:
        model = AsistenciaDocente
        fields = '__all__'

    def get_docente_nombre(self, obj):
        if obj.id_docente:
            return f'{obj.id_docente.apellido}, {obj.id_docente.nombre}'
        return None


# ---------- Actas ----------

class ActaSerializer(serializers.ModelSerializer):
    tipo_acta_nombre = serializers.CharField(
        source='id_tipo_acta.nombre_tipo',
        read_only=True, default=None,
    )
    creador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Acta
        fields = '__all__'
        # El creador NO es editable por el cliente: el backend lo asigna en
        # `perform_create` con el usuario autenticado real. Evita suplantar
        # a otro usuario como autor del acta.
        read_only_fields = ('id_usuario_creador',)

    def get_creador_nombre(self, obj):
        if obj.id_usuario_creador:
            return obj.id_usuario_creador.usuario
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ruta_archivo'] = media_url(data.get('ruta_archivo'))
        return data


class ActaAlumnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActaAlumno
        fields = '__all__'


class ActaCursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActaCurso
        fields = '__all__'


class ActaDocenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActaDocente
        fields = '__all__'


# ---------- Comunicados ----------

class ComunicadoArchivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComunicadoArchivo
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ruta_archivo'] = media_url(data.get('ruta_archivo'))
        return data


class ComunicadoAlcanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComunicadoAlcance
        fields = '__all__'


class ComunicadoAlcancesField(serializers.Field):
    def to_representation(self, value):
        if value is None:
            return []
        if hasattr(value, 'all'):
            queryset = value.all().order_by('id_alcance')
        else:
            queryset = value
        return ComunicadoAlcanceSerializer(queryset, many=True).data

    def to_internal_value(self, data):
        if data in (None, ''):
            return []
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise serializers.ValidationError('Los alcances deben enviarse como una lista.')
        normalizados = []
        for item in data:
            if not isinstance(item, dict):
                raise serializers.ValidationError('Cada alcance debe ser un objeto válido.')
            normalizados.append(item)
        return normalizados


class ComunicadoSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='id_curso.nombre_curso', read_only=True, default=None)
    creador_nombre = serializers.SerializerMethodField()
    materia_nombre = serializers.CharField(source='id_materia.nombre_materia', read_only=True, default=None)
    archivos = ComunicadoArchivoSerializer(many=True, read_only=True)
    alcances = ComunicadoAlcancesField(required=False)
    alcance = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Comunicado
        fields = '__all__'
        read_only_fields = ('id_usuario_creador',)

    def validate(self, attrs):
        alcances = attrs.get('alcances')
        if alcances is None:
            alcance = self.initial_data.get('alcance') or {}
            if alcance:
                if not isinstance(alcance, dict):
                    raise serializers.ValidationError({'alcance': 'Debe ser un objeto válido.'})
                alcances = [alcance]
            else:
                alcances = []

        if not isinstance(alcances, list):
            raise serializers.ValidationError({'alcances': 'Debe ser una lista válida.'})

        def _validate_alcance_item(item):
            if not isinstance(item, dict):
                raise serializers.ValidationError({'alcances': 'Cada alcance debe ser un objeto válido.'})
            id_ciclo = item.get('id_ciclo')
            curso = item.get('curso')
            division = item.get('division')
            id_materia = item.get('id_materia') or attrs.get('id_materia')

            if (curso is not None or division is not None) and not id_ciclo:
                raise serializers.ValidationError({'alcances': 'Si se envía curso o división, id_ciclo es obligatorio.'})
            if division is not None and curso is None:
                raise serializers.ValidationError({'alcances': 'La división requiere un curso.'})
            if id_materia and (id_ciclo is None or curso is None or division is None):
                raise serializers.ValidationError({'alcances': 'La materia específica requiere ciclo, curso y división.'})

        for item in alcances:
            _validate_alcance_item(item)

        attrs['alcances'] = alcances

        return attrs

    def _build_alcance_kwargs(self, comunicado, alcance_data):
        alcance_data = alcance_data or {}
        return {
            'id_comunicado': comunicado,
            'id_ciclo_id': alcance_data.get('id_ciclo') or None,
            'curso': alcance_data.get('curso') if alcance_data.get('curso') is not None else None,
            'division': alcance_data.get('division') if alcance_data.get('division') is not None else None,
            'id_materia_id': alcance_data.get('id_materia') if alcance_data.get('id_materia') is not None else None,
        }

    def create(self, validated_data):
        alcances_data = validated_data.pop('alcances', None)
        alcance_data = validated_data.pop('alcance', None)
        if alcances_data is None:
            alcances_data = [alcance_data] if alcance_data else []
        elif alcance_data:
            alcances_data = [*alcances_data, alcance_data]
        validated_data['id_curso'] = None
        validated_data['id_materia'] = None
        request = self.context.get('request')
        username = getattr(getattr(request, 'user', None), 'username', None)
        if username:
            validated_data['id_usuario_creador'] = Usuario.objects.filter(usuario=username).first()
        comunicado = Comunicado.objects.create(**validated_data)
        if not alcances_data:
            alcances_data = [{}]
        ComunicadoAlcance.objects.bulk_create(
            [ComunicadoAlcance(**self._build_alcance_kwargs(comunicado, alcance)) for alcance in alcances_data]
        )
        return comunicado

    def update(self, instance, validated_data):
        alcances_data = validated_data.pop('alcances', None)
        alcance_data = validated_data.pop('alcance', None)
        if alcances_data is None:
            alcances_data = [alcance_data] if alcance_data else None
        elif alcance_data:
            alcances_data = [*alcances_data, alcance_data]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.id_curso = None
        instance.id_materia = None
        instance.save()

        if alcances_data is not None:
            instance.alcances.all().delete()
            if not alcances_data:
                alcances_data = [{}]
            ComunicadoAlcance.objects.bulk_create(
                [ComunicadoAlcance(**self._build_alcance_kwargs(instance, alcance)) for alcance in alcances_data]
            )

        return instance

    def get_creador_nombre(self, obj):
        if not obj.id_usuario_creador:
            return None
        usuario = obj.id_usuario_creador
        preceptor = Preceptor.objects.filter(id_usuario=usuario).first()
        if preceptor:
            return f"{preceptor.apellido}, {preceptor.nombre}"
        docente = Docente.objects.filter(id_usuario=usuario).first()
        if docente:
            return f"{docente.apellido}, {docente.nombre}"
        directivo = Directivo.objects.filter(id_usuario=usuario).first()
        if directivo:
            return f"{directivo.apellido}, {directivo.nombre}"
        alumno = Alumno.objects.filter(id_usuario=usuario).first()
        if alumno:
            return f"{alumno.apellido}, {alumno.nombre}"
        padre = PadreTutor.objects.filter(id_usuario=usuario).first()
        if padre:
            return f"{padre.apellido}, {padre.nombre}"
        return usuario.usuario


# ---------- Planificaciones / Proyectos ----------

class PlanificacionSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Planificacion
        fields = '__all__'

    def get_docente_nombre(self, obj):
        if obj.id_docente_id and hasattr(obj, 'id_docente') and obj.id_docente:
            return f"{obj.id_docente.nombre} {obj.id_docente.apellido}"
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ruta_archivo'] = media_url(data.get('ruta_archivo'))
        return data


# ---------- Diagnósticos grupales ----------

class DiagnosticoGrupalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticoGrupal
        fields = '__all__'


# ---------- Notificaciones ----------

import json
import re

class NotificacionSerializer(serializers.ModelSerializer):
    """Serializa una notificación.

    `id_usuario` (destinatario) e `id_alumno` (alumno relacionado) son de
    solo lectura: se fijan al crearse internamente la notificación, nunca
    desde la API pública. La autorización no depende de estos campos sino
    del usuario autenticado.

    Corrección posterior: los marcadores internos [ref:...] y [nav:...] se
    almacenan en la base de datos (para deduplicación y navegación) pero se
    ocultan al cliente. El campo ``mensaje`` expone el texto visible limpio,
    y ``nav_destino``/``nav_params`` exponen los metadatos de navegación.
    """
    mensaje = serializers.SerializerMethodField()
    nav_destino = serializers.SerializerMethodField()
    nav_params = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = '__all__'
        read_only_fields = ('id_notificacion', 'id_usuario', 'id_alumno')

    @staticmethod
    def _limpiar_mensaje(mensaje):
        """Elimina marcadores internos [ref:...] y [nav:...] para visualización."""
        if not mensaje:
            return ''
        mensaje = re.sub(r'\s*\[ref:[^\]]+\]', '', mensaje)
        mensaje = re.sub(r'\s*\[nav:\{.*?\}\s*\]', '', mensaje)
        return mensaje.strip()

    def _extraer_nav(self, obj):
        """Extrae metadatos de navegación del mensaje si están presentes."""
        if not obj.mensaje:
            return {}
        # Buscar bloque de navegación al final del mensaje: [nav:{...}]
        match = re.search(r'\[nav:(\{.*?\})\s*\]', obj.mensaje)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {}

    def get_mensaje(self, obj):
        return self._limpiar_mensaje(obj.mensaje)

    def get_nav_destino(self, obj):
        nav = self._extraer_nav(obj)
        return nav.get('destino')

    def get_nav_params(self, obj):
        nav = self._extraer_nav(obj)
        return nav.get('params', {})


# ---------- Historial ----------

TABLAS_MODIFICADAS_LABEL = {
    'alumnos': 'Estudiantes',
    'tutores': 'Tutores/familias',
    'docentes': 'Docentes',
    'preceptores': 'Preceptores',
    'jefes_preceptores': 'Jefes de Preceptores',
    'directores': 'Directores',
    'usuarios': 'Usuarios',
    'comunicados': 'Comunicados',
    'actas': 'Actas',
    'diagnosticos': 'Diagnósticos',
    'cursos': 'Cursos',
    'materias': 'Materias',
    'asignaciones_cursos': 'Asignaciones de Cursos',
    'eventos_institucionales': 'Eventos Institucionales',
    'libro_temas': 'Libro de Temas',
}


class HistorialCambioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='id_usuario.usuario', read_only=True)
    usuario_nombre_completo = serializers.SerializerMethodField()
    accion = serializers.CharField(source='id_tipo_accion.nombre_accion', read_only=True)
    roles_usuario = serializers.SerializerMethodField()
    tabla_label = serializers.SerializerMethodField()
    fecha_formateada = serializers.SerializerMethodField()

    class Meta:
        model = HistorialCambio
        fields = [
            'id_historial',
            'id_usuario',
            'usuario_nombre',
            'usuario_nombre_completo',
            'roles_usuario',
            'id_tipo_accion',
            'accion',
            'tabla_modificada',
            'tabla_label',
            'id_registro',
            'valor_anterior',
            'valor_nuevo',
            'fecha',
            'fecha_formateada',
        ]

    def get_usuario_nombre_completo(self, obj):
        """Devuelve el nombre completo (apellido, nombre) del usuario responsable.
        Busca en Preceptor, Docente, Directivo, PadreTutor, Alumno según corresponda."""
        usuario = obj.id_usuario
        if not usuario:
            return None
        # Preceptor
        try:
            preceptor = usuario.preceptor
        except Preceptor.DoesNotExist:
            preceptor = None
        if preceptor:
            return f'{preceptor.apellido}, {preceptor.nombre}'
        # Docente
        try:
            docente = usuario.docente
        except Docente.DoesNotExist:
            docente = None
        if docente:
            return f'{docente.apellido}, {docente.nombre}'
        # Directivo (Administrador/Director)
        try:
            directivo = usuario.directivo
        except Directivo.DoesNotExist:
            directivo = None
        if directivo:
            return f'{directivo.apellido}, {directivo.nombre}'
        # Padre/Tutor
        try:
            tutor = usuario.padretutor
        except PadreTutor.DoesNotExist:
            tutor = None
        if tutor:
            return f'{tutor.apellido}, {tutor.nombre}'
        # Alumno
        try:
            alumno = usuario.alumno
        except Alumno.DoesNotExist:
            alumno = None
        if alumno:
            return f'{alumno.apellido}, {alumno.nombre}'
        # Fallback al username
        return usuario.usuario

    def get_roles_usuario(self, obj):
        roles = obj.id_usuario.usuariorol_set.all()
        return [ur.id_rol.nombre_rol for ur in roles]

    def get_tabla_label(self, obj):
        return TABLAS_MODIFICADAS_LABEL.get(obj.tabla_modificada, obj.tabla_modificada or '')

    def get_fecha_formateada(self, obj):
        if not obj.fecha:
            return None
        return obj.fecha.strftime('%d/%m/%Y %H:%M')


# ---------- Login ----------

class LoginSerializer(serializers.Serializer):
    usuario = serializers.CharField()
    contrasena = serializers.CharField(write_only=True)


# ---------- Eventos Institucionales ----------

class EventoInstitucionalSerializer(serializers.ModelSerializer):
    creado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = EventoInstitucional
        fields = '__all__'

    def get_creado_por_nombre(self, obj):
        if not obj.id_usuario_creador:
            return None
        try:
            preceptor = obj.id_usuario_creador.preceptor
        except Preceptor.DoesNotExist:
            preceptor = None
        if preceptor:
            return f'{preceptor.apellido}, {preceptor.nombre}'
        try:
            admin = obj.id_usuario_creador.directivo
        except Directivo.DoesNotExist:
            admin = None
        if admin:
            return f'{admin.apellido}, {admin.nombre}'
        return obj.id_usuario_creador.usuario


# ---------- Libro de Temas ----------

class CargaUnicaSerializer(serializers.ModelSerializer):
    """Serializa una ventana de carga única de 20 minutos para el frontend."""
    pendientes = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    tiempo_restante_seg = serializers.SerializerMethodField()

    class Meta:
        model = CargaUnica
        fields = '__all__'

    def get_pendientes(self, obj):
        return obj.pendientes_lista()

    def get_estado(self, obj):
        return 'vencida' if timezone.localtime() > obj.fecha_vencimiento else 'activa'

    def get_tiempo_restante_seg(self, obj):
        restante = obj.fecha_vencimiento - timezone.localtime()
        return 0 if restante.total_seconds() <= 0 else int(restante.total_seconds())


class LibroTemaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(
        source='id_curso_materia.id_curso.nombre_curso', read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_curso_materia.id_materia.nombre_materia', read_only=True, default=None,
    )
    id_docente = serializers.PrimaryKeyRelatedField(
        queryset=Docente.objects.all(), required=False, allow_null=True,
    )
    docente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = LibroTema
        fields = '__all__'

    def get_docente_nombre(self, obj):
        if obj.id_docente_id:
            return f'{obj.id_docente.apellido}, {obj.id_docente.nombre}'
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ruta_archivo'] = media_url(data.get('ruta_archivo'))
        return data

    def validate(self, attrs):
        cm = attrs.get('id_curso_materia') or (self.instance.id_curso_materia if self.instance else None)
        fecha = attrs.get('fecha') or (self.instance.fecha if self.instance else None)
        hora_inicio = attrs.get('hora_inicio') or (self.instance.hora_inicio if self.instance else None)
        hora_fin = attrs.get('hora_fin') or (self.instance.hora_fin if self.instance else None)
        if hora_inicio is not None and hora_fin is not None and hora_fin <= hora_inicio:
            raise serializers.ValidationError({
                'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.',
            })
        if cm is not None and fecha is not None and hora_inicio is not None and hora_fin is not None:
            qs = LibroTema.objects.filter(
                id_curso_materia=cm,
                fecha=fecha,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            for registro in qs:
                if franjas_se_solapan(hora_inicio, hora_fin, registro.hora_inicio, registro.hora_fin):
                    raise serializers.ValidationError(
                        'Ya existe un registro del Libro de Temas para esta materia y fecha en ese horario.'
                    )
        return attrs


# ---------- Adelantos de horas ----------

class AdelantoHorasSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(
        source='id_curso.nombre_curso', read_only=True, default=None,
    )
    materia_nombre = serializers.CharField(
        source='id_materia.nombre_materia', read_only=True, default=None,
    )
    id_curso = serializers.PrimaryKeyRelatedField(queryset=Curso.objects.all())
    id_materia = serializers.PrimaryKeyRelatedField(queryset=Materia.objects.all())
    id_docente = serializers.PrimaryKeyRelatedField(queryset=Docente.objects.all())
    docente_nombre = serializers.SerializerMethodField()
    autorizador_nombre = serializers.SerializerMethodField()
    estado_label = serializers.SerializerMethodField()
    finalizado = serializers.SerializerMethodField()
    modulos = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False, allow_empty=False, write_only=True,
    )
    modulos_detalle = serializers.SerializerMethodField()

    class Meta:
        model = AdelantoHoras
        fields = '__all__'
        extra_kwargs = {
            'fecha_creacion': {'read_only': True},
            'fecha_modificacion': {'read_only': True},
            'id_usuario_autorizador': {'read_only': True},
            'hora_inicio': {'required': False},
            'hora_fin': {'required': False},
        }

    def get_docente_nombre(self, obj):
        if obj.id_docente_id:
            return f'{obj.id_docente.apellido}, {obj.id_docente.nombre}'
        return None

    def get_autorizador_nombre(self, obj):
        if obj.id_usuario_autorizador_id:
            return obj.id_usuario_autorizador.usuario
        return None

    def get_estado_label(self, obj):
        if not obj.estado:
            return 'Eliminado'
        return 'Activo'

    def get_finalizado(self, obj):
        """Un adelanto se considera finalizado cuando su horario ya pasó."""
        from datetime import datetime
        if not obj.estado:
            return True
        fin = timezone.make_aware(datetime.combine(obj.fecha_adelanto, obj.hora_fin))
        return timezone.localtime() >= fin

    def get_modulos_detalle(self, obj):
        """Módulos completos contenidos en la franja horaria del adelanto."""
        if not obj.hora_inicio or not obj.hora_fin:
            return []
        modulos = self.context.get('_adelanto_modulos')
        if modulos is None:
            modulos = list(Modulos.objects.order_by('hora_inicio'))
            self.context['_adelanto_modulos'] = modulos
        return [
            {
                'id_modulo': m.id_modulo,
                'nombre': m.nombre,
                'hora_inicio': str(m.hora_inicio)[:5],
                'hora_fin': str(m.hora_fin)[:5],
            }
            for m in modulos
            if m.hora_inicio is not None and m.hora_fin is not None
            and m.hora_inicio >= obj.hora_inicio and m.hora_fin <= obj.hora_fin
        ]

    def validate(self, attrs):
        from datetime import datetime
        from django.db.models import Q

        id_curso = attrs.get('id_curso') or (self.instance.id_curso if self.instance else None)
        id_materia = attrs.get('id_materia') or (self.instance.id_materia if self.instance else None)
        id_docente = attrs.get('id_docente') or (self.instance.id_docente if self.instance else None)
        fecha = attrs.get('fecha_adelanto') or (self.instance.fecha_adelanto if self.instance else None)

        if fecha and fecha < timezone.localdate():
            raise serializers.ValidationError(
                {'fecha_adelanto': 'No se puede cargar un adelanto en una fecha pasada.'}
            )

        # --- Módulos seleccionados → hora_inicio / hora_fin calculados ---
        modulos_ids = attrs.pop('modulos', None)
        if modulos_ids is not None:
            mods = sorted(
                Modulos.objects.filter(id_modulo__in=modulos_ids),
                key=lambda m: m.hora_inicio,
            )
            if len(mods) != len(set(modulos_ids)):
                raise serializers.ValidationError(
                    {'modulos': 'Uno o más módulos seleccionados no existen.'}
                )
            if not mods:
                raise serializers.ValidationError(
                    {'modulos': 'Debe seleccionar al menos un módulo.'}
                )
            for anterior, siguiente in zip(mods, mods[1:]):
                if siguiente.hora_inicio != anterior.hora_fin:
                    raise serializers.ValidationError(
                        {'modulos': 'Los módulos seleccionados deben ser consecutivos.'}
                    )
            attrs['hora_inicio'] = mods[0].hora_inicio
            attrs['hora_fin'] = mods[-1].hora_fin

        hora_inicio = attrs.get('hora_inicio') or (self.instance.hora_inicio if self.instance else None)
        hora_fin = attrs.get('hora_fin') or (self.instance.hora_fin if self.instance else None)

        # --- Relación docente + curso + materia (asignación real) ---
        cm_adelanto = None
        if id_docente is not None and id_curso is not None and id_materia is not None:
            for candidato in CursoMateria.objects.filter(
                id_curso=id_curso, id_materia=id_materia, estado=True,
            ):
                activo = obtener_docente_activo(candidato.pk, fecha or timezone.localdate())
                if activo.docente and activo.docente.pk == id_docente.pk:
                    cm_adelanto = candidato
                    break
            if cm_adelanto is None:
                raise serializers.ValidationError(
                    {'non_field_errors': [
                        'El docente no es el titular ni el suplente activo de esa materia en ese curso.'
                    ]}
                )

        if hora_inicio is not None and hora_fin is not None:
            if isinstance(hora_inicio, str):
                hora_inicio = datetime.strptime(hora_inicio, '%H:%M').time()
            if isinstance(hora_fin, str):
                hora_fin = datetime.strptime(hora_fin, '%H:%M').time()
            if hora_inicio >= hora_fin:
                raise serializers.ValidationError(
                    {'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.'}
                )
            attrs['hora_inicio'] = hora_inicio
            attrs['hora_fin'] = hora_fin

        # --- Solapamiento: mismo curso, misma fecha, franja que se superpone ---
        if id_curso is not None and fecha is not None and hora_inicio is not None and hora_fin is not None:
            qs = AdelantoHoras.objects.filter(
                id_curso=id_curso,
                fecha_adelanto=fecha,
                estado=True,
            ).filter(
                Q(hora_inicio__lt=hora_fin) & Q(hora_fin__gt=hora_inicio)
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'non_field_errors': [
                        'Los módulos seleccionados se superponen con otro adelanto existente para este curso.'
                    ]}
                )

        if cm_adelanto and fecha and hora_inicio and hora_fin:
            dia = DIAS_SEMANA_ES_SUPL[fecha.weekday()]
            destino = _bloques_cm_suplencia(cm_adelanto.pk, dia)
            otros_cm = CursoMateria.objects.filter(
                id_docente=id_docente, estado=True,
            ).exclude(pk=cm_adelanto.pk)
            for otro in otros_cm:
                for ini_otro, fin_otro in _bloques_cm_suplencia(otro.pk, dia):
                    for ini_dest, fin_dest in destino:
                        if franjas_se_solapan(ini_dest, fin_dest, ini_otro, fin_otro):
                            raise serializers.ValidationError(
                                {'non_field_errors': [
                                    'El docente ya tiene otra clase asignada en esa fecha y horario.'
                                ]}
                            )
        return attrs


# ---------- Sistema Académico Avanzado ----------

class HistorialAcademicoSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.SerializerMethodField()
    materia_nombre = serializers.CharField(source='id_materia.nombre_materia', read_only=True, default='')
    curso_nombre = serializers.CharField(source='id_curso.nombre_curso', read_only=True, default='')

    class Meta:
        model = HistorialAcademico
        fields = '__all__'

    def get_alumno_nombre(self, obj):
        alumno = getattr(obj, 'id_alumno', None)
        if alumno:
            return f'{alumno.apellido}, {alumno.nombre}'
        return ''


class IntensificacionAcademicaSerializer(serializers.ModelSerializer):
    id_alumno = serializers.IntegerField(source='id_historial.id_alumno_id', read_only=True)
    id_curso_materia = serializers.IntegerField(source='id_historial.id_curso_materia_id', read_only=True)
    alumno_nombre = serializers.SerializerMethodField()
    materia_nombre = serializers.CharField(source='id_historial.id_materia.nombre_materia', read_only=True, default='')

    class Meta:
        model = IntensificacionAcademica
        fields = '__all__'

    def get_alumno_nombre(self, obj):
        historial = getattr(obj, 'id_historial', None)
        if historial and getattr(historial, 'id_alumno', None):
            a = historial.id_alumno
            return f'{a.apellido}, {a.nombre}'
        return ''

    def validate_nota(self, value):
        # N3: la nota de intensificación también se valida 1–10 en el backend
        # (alimenta la regla de aprobación `_intensif_habilitada`/`_procesar`).
        if value is not None and (value < 1 or value > 10):
            raise serializers.ValidationError('La nota debe estar entre 1 y 10.')
        return value


class MateriaAdeudadaSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='id_materia.nombre_materia', read_only=True, default='')
    curso_origen_nombre = serializers.CharField(source='id_curso_origen.nombre_curso', read_only=True, default='')
    curso_actual_nombre = serializers.CharField(source='id_curso_actual.nombre_curso', read_only=True, default='')
    alumno_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAdeudada
        fields = '__all__'

    def get_alumno_nombre(self, obj):
        alumno = getattr(obj, 'id_alumno', None)
        if alumno:
            return f'{alumno.apellido}, {alumno.nombre}'
        return ''


class ActividadMateriaAdeudadaSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='id_curso_materia.id_materia.nombre_materia', read_only=True, default='')
    curso_nombre = serializers.CharField(source='id_curso_materia.id_curso.nombre_curso', read_only=True, default='')
    docente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ActividadMateriaAdeudada
        fields = '__all__'

    def get_docente_nombre(self, obj):
        if obj.id_docente:
            return f"{obj.id_docente.apellido}, {obj.id_docente.nombre}"
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['archivo_pdf'] = media_url(data.get('archivo_pdf'))
        return data


class RendicionMateriaAdeudadaSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RendicionMateriaAdeudada
        fields = '__all__'

    def get_docente_nombre(self, obj):
        if obj.id_docente:
            return f"{obj.id_docente.apellido}, {obj.id_docente.nombre}"
        return ''


class HistorialCursoAlumnoSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='id_curso.nombre_curso', read_only=True, default='')

    class Meta:
        model = HistorialCursoAlumno
        fields = '__all__'


class BloqueoHorarioAlumnoSerializer(serializers.ModelSerializer):
    materia_bloqueada_nombre = serializers.CharField(source='id_materia_bloqueada.nombre_materia', read_only=True, default='')
    materia_prioritaria_nombre = serializers.CharField(source='id_materia_prioritaria.nombre_materia', read_only=True, default='')
    materia_recursada_nombre = serializers.CharField(source='id_materia_recursada.nombre_materia', read_only=True, default='')

    class Meta:
        model = BloqueoHorarioAlumno
        fields = '__all__'


class PromocionAlumnoSerializer(serializers.ModelSerializer):
    curso_origen_nombre = serializers.CharField(source='curso_origen.nombre_curso', read_only=True, default='')
    curso_destino_nombre = serializers.CharField(source='curso_destino.nombre_curso', read_only=True, default='')

    class Meta:
        model = PromocionAlumno
        fields = '__all__'


class RecursadaMateriaSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='id_materia.nombre_materia', read_only=True, default='')
    curso_origen_nombre = serializers.CharField(source='id_curso_origen.nombre_curso', read_only=True, default='')
    curso_recursada_nombre = serializers.CharField(source='id_curso_recursada.nombre_curso', read_only=True, default='')

    class Meta:
        model = RecursadaMateria
        fields = '__all__'


class RecursadaCalificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecursadaCalificacion
        fields = '__all__'


class BloqueoMateriaRecursadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloqueoMateriaRecursada
        fields = '__all__'


class RegistroRendicionPreviaSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='id_materia.nombre_materia', read_only=True, default='')
    curso_origen_nombre = serializers.CharField(source='id_curso_origen.nombre_curso', read_only=True, default='')

    class Meta:
        model = RegistroRendicionPrevia
        fields = '__all__'


class ResultadoActividadAdeudadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoActividadAdeudada
        fields = '__all__'


class SituacionMateriaAlumnoSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='id_curso_materia.id_materia.nombre_materia', read_only=True, default='')
    curso_nombre = serializers.CharField(source='id_curso_materia.id_curso.nombre_curso', read_only=True, default='')

    class Meta:
        model = SituacionMateriaAlumno
        fields = '__all__'


