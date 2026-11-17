# Estructura de la base de datos — Sistema Escolar

> Generado automaticamente desde la base PostgreSQL (Supabase) el 2026-11-16.
> Tablas en el esquema `public`: **80**.
> Los modelos Django usan `managed = False`: este esquema es la referencia real.

---

## Indice de tablas

- [acta_alumno](#acta_alumno)
- [acta_curso](#acta_curso)
- [acta_docente](#acta_docente)
- [actas](#actas)
- [actas_documentacion](#actas_documentacion)
- [actividad_docente_archivos](#actividad_docente_archivos)
- [actividades_docentes](#actividades_docentes)
- [actividades_materias_adeudadas](#actividades_materias_adeudadas)
- [adelantos_horas](#adelantos_horas)
- [agenda_orientacion](#agenda_orientacion)
- [alumnos](#alumnos)
- [asistencias](#asistencias)
- [asistencias_docentes](#asistencias_docentes)
- [auth_group](#auth_group)
- [auth_group_permissions](#auth_group_permissions)
- [auth_permission](#auth_permission)
- [auth_user](#auth_user)
- [auth_user_groups](#auth_user_groups)
- [auth_user_user_permissions](#auth_user_user_permissions)
- [bloqueos_horarios_alumno](#bloqueos_horarios_alumno)
- [bloqueos_materias_recursadas](#bloqueos_materias_recursadas)
- [calificaciones](#calificaciones)
- [cargas_unicas](#cargas_unicas)
- [ciclos_lectivos](#ciclos_lectivos)
- [comunicado_alcance](#comunicado_alcance)
- [comunicado_archivo](#comunicado_archivo)
- [comunicados](#comunicados)
- [curso_materia](#curso_materia)
- [cursos](#cursos)
- [ddjj_docente](#ddjj_docente)
- [derivaciones](#derivaciones)
- [diagnosticos_grupales](#diagnosticos_grupales)
- [directivos](#directivos)
- [django_admin_log](#django_admin_log)
- [django_content_type](#django_content_type)
- [django_migrations](#django_migrations)
- [django_session](#django_session)
- [docentes](#docentes)
- [estados_asistencia](#estados_asistencia)
- [eventos_institucionales](#eventos_institucionales)
- [historial_academico](#historial_academico)
- [historial_cambios](#historial_cambios)
- [historial_cursos_alumno](#historial_cursos_alumno)
- [horarios](#horarios)
- [horarios_especiales](#horarios_especiales)
- [inclusion_educativa](#inclusion_educativa)
- [informes_distritales](#informes_distritales)
- [informes_orientacion](#informes_orientacion)
- [inscripciones_materias](#inscripciones_materias)
- [intensificaciones_academicas](#intensificaciones_academicas)
- [libro_temas](#libro_temas)
- [materias](#materias)
- [materias_adeudadas](#materias_adeudadas)
- [materias_recursadas_calificaciones](#materias_recursadas_calificaciones)
- [mediaciones_acuerdos](#mediaciones_acuerdos)
- [modulos](#modulos)
- [notificaciones](#notificaciones)
- [padres_tutores](#padres_tutores)
- [periodos_evaluacion](#periodos_evaluacion)
- [planificaciones](#planificaciones)
- [preceptores](#preceptores)
- [promociones_alumno](#promociones_alumno)
- [proyectos_pii](#proyectos_pii)
- [recursadas_materias](#recursadas_materias)
- [red_institucional](#red_institucional)
- [registro_rendiciones_previas](#registro_rendiciones_previas)
- [rendiciones_materias_adeudadas](#rendiciones_materias_adeudadas)
- [resultados_actividades_adeudadas](#resultados_actividades_adeudadas)
- [roles](#roles)
- [seguimiento_eoe](#seguimiento_eoe)
- [seguimiento_social](#seguimiento_social)
- [situacion_estudiante](#situacion_estudiante)
- [situaciones_conflicto](#situaciones_conflicto)
- [situaciones_materias_alumno](#situaciones_materias_alumno)
- [suplencias_docentes](#suplencias_docentes)
- [tipos_accion](#tipos_accion)
- [tipos_acta](#tipos_acta)
- [tutor_alumno](#tutor_alumno)
- [usuario_roles](#usuario_roles)
- [usuarios](#usuarios)

---

### acta_alumno

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_acta_alumno` | integer | no |  | PK |
| `id_acta` | integer | no |  | FK->actas(id_acta) |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |

### acta_curso

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_acta_curso` | integer | no |  | PK |
| `id_acta` | integer | no |  | FK->actas(id_acta) |
| `id_curso` | integer | no |  | FK->cursos(id_curso) |

### acta_docente

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_acta_docente` | integer | no |  | PK |
| `id_acta` | integer | no |  | FK->actas(id_acta) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |

### actas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_acta` | integer | no |  | PK |
| `id_usuario_creador` | integer | no |  | FK->usuarios(id_usuario) |
| `id_tipo_acta` | integer | no |  | FK->tipos_acta(id_tipo_acta) |
| `titulo` | varchar(255) | si |  |  |
| `descripcion` | text | si |  |  |
| `fecha` | timestamp | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### actas_documentacion

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `tipo_documento` | varchar(50) | si |  |  |
| `descripcion` | text | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `fecha` | date | si |  |  |
| `destinatario` | varchar(255) | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### actividad_docente_archivos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_archivo` | integer | no |  | PK |
| `id_actividad` | integer | no |  | FK->actividades_docentes(id_actividad) |
| `ruta_archivo` | varchar(255) | no |  |  |
| `fecha_carga` | timestamp | no | CURRENT_TIMESTAMP |  |

### actividades_docentes

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_actividad` | integer | no |  | PK |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `titulo` | varchar(150) | no |  |  |
| `descripcion` | text | si |  |  |
| `ruta_archivo` | varchar(255) | no |  |  |
| `fecha_creacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### actividades_materias_adeudadas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_actividad` | integer | no |  | PK |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `titulo` | varchar(150) | no |  |  |
| `descripcion` | text | si |  |  |
| `archivo_pdf` | varchar(500) | no |  |  |
| `tipo` | text | no |  |  |
| `periodo_intensificacion` | varchar(50) | si |  |  |
| `fecha_publicacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `activo` | boolean | no | true |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### adelantos_horas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_adelanto` | integer | no |  | PK |
| `id_curso` | integer | no |  | FK->cursos(id_curso) |
| `id_materia` | integer | no |  | FK->materias(id_materia) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `fecha_adelanto` | date | no |  |  |
| `hora_inicio` | time | no |  |  |
| `hora_fin` | time | no |  |  |
| `mantener_horario_original` | boolean | no | false |  |
| `motivo` | varchar(255) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `id_usuario_autorizador` | integer | no |  | FK->usuarios(id_usuario) |
| `fecha_creacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_modificacion` | timestamp | no | CURRENT_TIMESTAMP |  |

### agenda_orientacion

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `tipo_actividad` | varchar(50) | si |  |  |
| `fecha` | date | si |  |  |
| `hora` | time | si |  |  |
| `participantes` | varchar(255) | si |  |  |
| `motivo` | varchar(255) | si |  |  |
| `observaciones` | text | si |  |  |
| `estado_agenda` | varchar(30) | si | 'Programada'::character varying |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### alumnos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_alumno` | integer | no |  | PK |
| `id_usuario` | integer | si |  | FK->usuarios(id_usuario) |
| `id_tutor` | integer | si |  | FK->padres_tutores(id_tutor) |
| `id_curso` | integer | si |  | FK->cursos(id_curso) |
| `nombre` | varchar(100) | no |  |  |
| `apellido` | varchar(100) | no |  |  |
| `dni` | varchar(20) | no |  |  |
| `fecha_nacimiento` | date | si |  |  |
| `direccion` | varchar(255) | si |  |  |
| `telefono` | varchar(30) | si |  |  |
| `procedencia` | varchar(100) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### asistencias

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_asistencia` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_usuario` | integer | no |  | FK->usuarios(id_usuario) |
| `id_estado_asistencia` | integer | no |  | FK->estados_asistencia(id_estado_asistencia) |
| `justificado` | boolean | no | false |  |
| `fecha` | date | no |  |  |
| `hora` | time | no |  |  |

### asistencias_docentes

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_asistencia_docente` | integer | no |  | PK |
| `id_docente` | integer | no |  |  |
| `id_curso_materia` | integer | no |  |  |
| `id_usuario` | integer | no |  |  |
| `id_estado_asistencia` | integer | no |  |  |
| `fecha` | date | no |  |  |
| `hora` | time | no |  |  |

### auth_group

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `name` | varchar(150) | no |  |  |

### auth_group_permissions

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | bigint | no |  | PK |
| `group_id` | integer | no |  | FK->auth_group(id) |
| `permission_id` | integer | no |  | FK->auth_permission(id) |

### auth_permission

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `name` | varchar(255) | no |  |  |
| `content_type_id` | integer | no |  | FK->django_content_type(id) |
| `codename` | varchar(100) | no |  |  |

### auth_user

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `password` | varchar(128) | no |  |  |
| `last_login` | timestamp | si |  |  |
| `is_superuser` | boolean | no |  |  |
| `username` | varchar(150) | no |  |  |
| `first_name` | varchar(150) | no |  |  |
| `last_name` | varchar(150) | no |  |  |
| `email` | varchar(254) | no |  |  |
| `is_staff` | boolean | no |  |  |
| `is_active` | boolean | no |  |  |
| `date_joined` | timestamp | no |  |  |

### auth_user_groups

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | bigint | no |  | PK |
| `user_id` | integer | no |  | FK->auth_user(id) |
| `group_id` | integer | no |  | FK->auth_group(id) |

### auth_user_user_permissions

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | bigint | no |  | PK |
| `user_id` | integer | no |  | FK->auth_user(id) |
| `permission_id` | integer | no |  | FK->auth_permission(id) |

### bloqueos_horarios_alumno

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_bloqueo` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_materia_bloqueada` | integer | no |  | FK->materias(id_materia) |
| `id_curso_materia_bloqueada` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_materia_prioritaria` | integer | no |  | FK->materias(id_materia) |
| `id_curso_materia_prioritaria` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_materia_recursada` | integer | no |  | FK->materias(id_materia) |
| `id_curso_materia_recursada` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `motivo` | text | no | 'SUPERPOSICION_RECURSADA'::text |  |
| `estado` | boolean | no | true |  |
| `fecha_bloqueo` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_desbloqueo` | timestamp | si |  |  |
| `observaciones` | text | si |  |  |

### bloqueos_materias_recursadas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_bloqueo` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_materia_recursada` | integer | no |  | FK->materias_adeudadas(id_materia_adeudada) |
| `id_curso_materia_bloqueada` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `motivo` | varchar(255) | no |  |  |
| `anio_lectivo` | integer | no |  |  |
| `activo` | boolean | no | true |  |
| `fecha_registro` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_desactivacion` | timestamp | si |  |  |

### calificaciones

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_calificacion` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `id_periodo` | integer | no |  | FK->periodos_evaluacion(id_periodo) |
| `pre_nota` | varchar(10) | si |  |  |
| `nota_numerica` | numeric(4,2) | si |  |  |
| `diagnostico` | text | si |  |  |
| `fecha_carga` | timestamp | si |  |  |
| `intensificacion_1c` | numeric(4,2) | si |  |  |
| `diciembre` | numeric(4,2) | si |  |  |
| `febrero` | numeric(4,2) | si |  |  |
| `calificacion_final` | numeric(4,2) | si |  |  |

### cargas_unicas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_carga_unica` | integer | no |  | PK |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_docente` | integer | si |  | FK->docentes(id_docente) |
| `fecha` | date | no |  |  |
| `fecha_inicio` | timestamp | no |  |  |
| `fecha_vencimiento` | timestamp | no |  |  |
| `pendientes` | varchar(120) | no | '[]'::character varying |  |
| `asistencias_cargada` | boolean | no | false |  |
| `libro_cargada` | boolean | no | false |  |
| `fecha_creacion` | timestamp | no | CURRENT_TIMESTAMP |  |

### ciclos_lectivos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_ciclo` | integer | no |  | PK |
| `anio` | integer | no |  |  |
| `fecha_inicio` | date | si |  |  |
| `fecha_fin` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### comunicado_alcance

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_alcance` | integer | no |  | PK |
| `id_comunicado` | integer | no |  | FK->comunicados(id_comunicado) |
| `id_ciclo` | integer | si |  | FK->ciclos_lectivos(id_ciclo) |
| `curso` | integer | si |  |  |
| `division` | integer | si |  |  |
| `id_materia` | integer | si |  | FK->materias(id_materia) |

### comunicado_archivo

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_comunicado_archivo` | integer | no |  | PK |
| `id_comunicado` | integer | no |  | FK->comunicados(id_comunicado) |
| `ruta_archivo` | varchar(255) | no |  |  |

### comunicados

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_comunicado` | integer | no |  | PK |
| `id_usuario_creador` | integer | si |  |  |
| `id_curso` | integer | si |  | FK->cursos(id_curso) |
| `id_materia` | integer | si |  | FK->materias(id_materia) |
| `titulo` | varchar(255) | no |  |  |
| `cuerpo` | text | si |  |  |
| `fecha` | timestamp | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### curso_materia

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_curso_materia` | integer | no |  | PK |
| `id_curso` | integer | no |  | FK->cursos(id_curso) |
| `id_materia` | integer | no |  | FK->materias(id_materia) |
| `id_docente` | integer | si |  | FK->docentes(id_docente) |
| `activo` | boolean | no | true |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### cursos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_curso` | integer | no |  | PK |
| `id_preceptor` | integer | si |  | FK->preceptores(id_preceptor) |
| `id_ciclo` | integer | si |  | FK->ciclos_lectivos(id_ciclo) |
| `nombre_curso` | varchar(50) | no |  |  |
| `activo` | boolean | no | true |  |
| `orientacion` | varchar(50) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### ddjj_docente

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_ddjj` | integer | no |  | PK |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `ruta_archivo` | varchar(255) | no |  |  |
| `fecha_carga` | timestamp | no | CURRENT_TIMESTAMP |  |
| `verificada` | boolean | no | false |  |

### derivaciones

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `destinatario` | varchar(255) | si |  |  |
| `tipo_organismo` | varchar(100) | si |  |  |
| `motivo` | varchar(255) | si |  |  |
| `descripcion` | text | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `estado_derivacion` | varchar(30) | si | 'Pendiente'::character varying |  |
| `fecha_derivacion` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### diagnosticos_grupales

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_diagnostico_grupal` | integer | no |  | PK |
| `id_curso` | integer | no |  | FK->cursos(id_curso) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `fecha` | date | si |  |  |
| `descripcion` | text | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### directivos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_directivo` | integer | no |  | PK |
| `id_usuario` | integer | si |  | FK->usuarios(id_usuario) |
| `nombre` | varchar(100) | no |  |  |
| `apellido` | varchar(100) | no |  |  |
| `dni` | varchar(20) | no |  |  |
| `telefono` | varchar(30) | si |  |  |
| `cargo` | varchar(100) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### django_admin_log

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `action_time` | timestamp | no |  |  |
| `object_id` | text | si |  |  |
| `object_repr` | varchar(200) | no |  |  |
| `action_flag` | smallint | no |  |  |
| `change_message` | text | no |  |  |
| `content_type_id` | integer | si |  | FK->django_content_type(id) |
| `user_id` | integer | no |  | FK->auth_user(id) |

### django_content_type

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `app_label` | varchar(100) | no |  |  |
| `model` | varchar(100) | no |  |  |

### django_migrations

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | bigint | no |  | PK |
| `app` | varchar(255) | no |  |  |
| `name` | varchar(255) | no |  |  |
| `applied` | timestamp | no |  |  |

### django_session

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `session_key` | varchar(40) | no |  | PK |
| `session_data` | text | no |  |  |
| `expire_date` | timestamp | no |  |  |

### docentes

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_docente` | integer | no |  | PK |
| `id_usuario` | integer | si |  | FK->usuarios(id_usuario) |
| `nombre` | varchar(100) | no |  |  |
| `apellido` | varchar(100) | no |  |  |
| `dni` | varchar(20) | no |  |  |
| `correo` | varchar(100) | si |  |  |
| `telefono` | varchar(30) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### estados_asistencia

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_estado_asistencia` | integer | no |  | PK |
| `nombre_estado` | varchar(50) | no |  |  |

### eventos_institucionales

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_evento` | integer | no |  | PK |
| `tipo_evento` | text | no |  |  |
| `descripcion` | varchar(255) | no |  |  |
| `fecha` | date | no |  |  |
| `permanente` | boolean | no | false |  |
| `alcance` | text | no | 'todo_dia'::text |  |
| `hora_inicio` | time | si |  |  |
| `hora_fin` | time | si |  |  |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `fecha_creacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_modificacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### historial_academico

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_historial` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_curso` | integer | no |  | FK->cursos(id_curso) |
| `id_materia` | integer | no |  | FK->materias(id_materia) |
| `anio_lectivo` | integer | no |  |  |
| `nota_1_cuatrimestre` | numeric(4,2) | si |  |  |
| `nota_2_cuatrimestre` | numeric(4,2) | si |  |  |
| `nota_final` | numeric(4,2) | si |  |  |
| `estado_materia` | text | no | 'no_cursada'::text |  |
| `periodo_aprobacion` | text | si |  |  |
| `anio_aprobacion` | integer | si |  |  |
| `es_recursada` | boolean | no | false |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### historial_cambios

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_historial` | integer | no |  | PK |
| `id_usuario` | integer | no |  | FK->usuarios(id_usuario) |
| `id_tipo_accion` | integer | no |  | FK->tipos_accion(id_tipo_accion) |
| `tabla_modificada` | varchar(100) | si |  |  |
| `id_registro` | integer | si |  |  |
| `valor_anterior` | text | si |  |  |
| `valor_nuevo` | text | si |  |  |
| `fecha` | timestamp | si |  |  |

### historial_cursos_alumno

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_historial_curso` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_curso` | integer | no |  | FK->cursos(id_curso) |
| `anio_lectivo` | integer | no |  |  |
| `estado` | text | no | 'CURSANDO'::text |  |
| `fecha_ingreso` | date | si |  |  |
| `fecha_finalizacion` | date | si |  |  |
| `observaciones` | text | si |  |  |

### horarios

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_horario` | integer | no |  | PK |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `dia_semana` | varchar(20) | si |  |  |
| `aula` | varchar(50) | si |  |  |
| `id_modulo` | integer | si |  | FK->modulos(id_modulo) |

### horarios_especiales

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_horario_especial` | integer | no |  | PK |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `dia_semana` | varchar(20) | no |  |  |
| `hora_inicio` | time | no |  |  |
| `hora_fin` | time | no |  |  |
| `aula` | varchar(50) | si |  |  |

### inclusion_educativa

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `tipo` | varchar(10) | si |  |  |
| `escuela_origen` | varchar(255) | si |  |  |
| `maestra_especial` | varchar(200) | si |  |  |
| `informacion` | text | si |  |  |
| `observaciones` | text | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### informes_distritales

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `titulo` | varchar(255) | si |  |  |
| `descripcion` | text | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `equipo_origen` | varchar(100) | si |  |  |
| `estado_informe` | varchar(30) | si | 'Recibido'::character varying |  |
| `fecha` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### informes_orientacion

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `equipo` | varchar(10) | si |  |  |
| `tipo_informe` | varchar(100) | si |  |  |
| `periodo` | varchar(50) | si |  |  |
| `contenido` | text | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `fecha` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### inscripciones_materias

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_inscripcion` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `estado` | varchar(50) | si |  |  |
| `fecha_inscripcion` | date | si |  |  |

### intensificaciones_academicas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_intensificacion` | integer | no |  | PK |
| `id_historial` | integer | no |  | FK->historial_academico(id_historial) |
| `periodo` | text | no |  |  |
| `anio_rendicion` | integer | no |  |  |
| `nota` | numeric(4,2) | si |  |  |
| `estado` | text | no | 'PENDIENTE'::text |  |
| `fecha_registro` | timestamp | no | CURRENT_TIMESTAMP |  |

### libro_temas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_libro_tema` | integer | no |  | PK |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `fecha` | date | no |  |  |
| `hora_inicio` | time | no |  |  |
| `hora_fin` | time | no |  |  |
| `descripcion` | text | no |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_modificacion` | timestamp | no | CURRENT_TIMESTAMP |  |

### materias

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_materia` | integer | no |  | PK |
| `nombre_materia` | varchar(100) | no |  |  |
| `activo` | boolean | no | true |  |
| `descripcion` | text | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### materias_adeudadas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_materia_adeudada` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_materia` | integer | no |  | FK->materias(id_materia) |
| `id_curso_origen` | integer | no |  | FK->cursos(id_curso) |
| `tipo_deuda` | text | no | 'PREVIA'::text |  |
| `estado` | text | no | 'ADEUDADA'::text |  |
| `fecha_generacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_aprobacion` | timestamp | si |  |  |
| `id_curso_actual` | integer | si |  | FK->cursos(id_curso) |
| `observaciones` | text | si |  |  |

### materias_recursadas_calificaciones

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_calificacion_recursada` | integer | no |  | PK |
| `id_recursada` | integer | no |  | FK->recursadas_materias(id_recursada) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `periodo` | varchar(50) | no |  |  |
| `nota` | numeric(4,2) | si |  |  |
| `diagnostico` | text | si |  |  |
| `fecha_carga` | timestamp | no | CURRENT_TIMESTAMP |  |

### mediaciones_acuerdos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `id_situacion` | integer | si |  |  |
| `fecha` | date | si |  |  |
| `participantes` | text | si |  |  |
| `problema` | text | si |  |  |
| `acuerdos` | text | si |  |  |
| `responsables` | text | si |  |  |
| `fecha_revision` | date | si |  |  |
| `cumplimiento` | varchar(30) | si | 'Pendiente'::character varying |  |
| `observaciones` | text | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### modulos

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_modulo` | integer | no |  | PK |
| `nombre` | varchar(50) | no |  |  |
| `hora_inicio` | time | no |  |  |
| `hora_fin` | time | no |  |  |

### notificaciones

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_notificacion` | integer | no |  | PK |
| `id_usuario` | integer | no |  | FK->usuarios(id_usuario) |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `titulo` | varchar(255) | si |  |  |
| `mensaje` | text | si |  |  |
| `fecha` | timestamp | si |  |  |
| `leida` | boolean | si | false |  |
| `rol` | varchar(32) | si |  |  |

### padres_tutores

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_tutor` | integer | no |  | PK |
| `id_usuario` | integer | si |  | FK->usuarios(id_usuario) |
| `nombre` | varchar(100) | no |  |  |
| `apellido` | varchar(100) | no |  |  |
| `dni` | varchar(20) | no |  |  |
| `telefono` | varchar(30) | si |  |  |
| `correo` | varchar(100) | si |  |  |
| `tipo` | varchar(30) | si |  |  |
| `direccion` | varchar(255) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### periodos_evaluacion

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_periodo` | integer | no |  | PK |
| `nombre_periodo` | varchar(100) | si |  |  |
| `orden_periodo` | integer | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### planificaciones

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_planificacion` | integer | no |  | PK |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `contenido` | text | si |  |  |
| `objetivos` | text | si |  |  |
| `salidas` | text | si |  |  |
| `fundamentacion` | text | si |  |  |
| `estado` | text | no | 'Borrador'::text |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `fecha_subida` | timestamp | si |  |  |
| `fecha_ultima_modificacion` | timestamp | si |  |  |
| `eliminado` | boolean | no | false |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### preceptores

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_preceptor` | integer | no |  | PK |
| `id_usuario` | integer | si |  | FK->usuarios(id_usuario) |
| `nombre` | varchar(100) | no |  |  |
| `apellido` | varchar(100) | no |  |  |
| `dni` | varchar(20) | no |  |  |
| `correo` | varchar(100) | si |  |  |
| `telefono` | varchar(30) | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### promociones_alumno

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_promocion` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_historial_curso` | integer | no |  | FK->historial_cursos_alumno(id_historial_curso) |
| `anio_lectivo` | integer | no |  |  |
| `resultado` | text | no |  |  |
| `curso_origen` | integer | no |  | FK->cursos(id_curso) |
| `curso_destino` | integer | si |  | FK->cursos(id_curso) |
| `fecha_resolucion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `observaciones` | text | si |  |  |

### proyectos_pii

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `anio` | integer | si |  |  |
| `diagnostico` | text | si |  |  |
| `problematicas` | text | si |  |  |
| `objetivos` | text | si |  |  |
| `lineas_intervencion` | text | si |  |  |
| `acciones` | text | si |  |  |
| `responsables` | text | si |  |  |
| `seguimiento` | text | si |  |  |
| `evaluacion` | text | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### recursadas_materias

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_recursada` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_materia` | integer | no |  | FK->materias(id_materia) |
| `id_curso_origen` | integer | no |  | FK->cursos(id_curso) |
| `id_curso_recursada` | integer | no |  | FK->cursos(id_curso) |
| `anio_inicio` | integer | no |  |  |
| `anio_finalizacion` | integer | si |  |  |
| `estado` | text | no | 'ACTIVA'::text |  |
| `motivo` | varchar(255) | si |  |  |
| `fecha_registro` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_finalizacion` | timestamp | si |  |  |
| `observaciones` | text | si |  |  |

### red_institucional

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `nombre_inst` | varchar(255) | si |  |  |
| `tipo` | varchar(100) | si |  |  |
| `contacto` | varchar(100) | si |  |  |
| `telefono` | varchar(50) | si |  |  |
| `correo` | varchar(100) | si |  |  |
| `localidad` | varchar(100) | si |  |  |
| `referente` | varchar(200) | si |  |  |
| `observaciones` | text | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### registro_rendiciones_previas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_registro` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_materia_adeudada` | integer | no |  | FK->materias_adeudadas(id_materia_adeudada) |
| `id_materia` | integer | no |  | FK->materias(id_materia) |
| `id_curso_origen` | integer | no |  | FK->cursos(id_curso) |
| `anio_rendicion` | integer | no |  |  |
| `periodo` | text | no |  |  |
| `nota` | numeric(4,2) | si |  |  |
| `resultado` | text | no |  |  |
| `id_docente` | integer | si |  | FK->docentes(id_docente) |
| `fecha_rendicion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `observaciones` | text | si |  |  |

### rendiciones_materias_adeudadas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_rendicion` | integer | no |  | PK |
| `id_materia_adeudada` | integer | no |  | FK->materias_adeudadas(id_materia_adeudada) |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_docente` | integer | no |  | FK->docentes(id_docente) |
| `anio_rendicion` | integer | no |  |  |
| `periodo` | text | no |  |  |
| `nota` | numeric(4,2) | si |  |  |
| `estado` | text | no | 'PENDIENTE'::text |  |
| `fecha_rendicion` | timestamp | si |  |  |
| `observaciones` | text | si |  |  |
| `fecha_registro` | timestamp | no | CURRENT_TIMESTAMP |  |

### resultados_actividades_adeudadas

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_resultado` | integer | no |  | PK |
| `id_actividad` | integer | no |  | FK->actividades_materias_adeudadas(id_actividad) |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_intensificacion` | integer | si |  | FK->intensificaciones_academicas(id_intensificacion) |
| `nota` | numeric(4,2) | si |  |  |
| `estado` | text | no | 'PENDIENTE'::text |  |
| `fecha_evaluacion` | timestamp | si |  |  |
| `observaciones` | text | si |  |  |

### roles

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_rol` | integer | no |  | PK |
| `nombre_rol` | varchar(50) | no |  |  |

### seguimiento_eoe

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `categoria` | varchar(60) | si |  |  |
| `motivo` | varchar(255) | si |  |  |
| `descripcion` | text | si |  |  |
| `intervenciones` | text | si |  |  |
| `observaciones` | text | si |  |  |
| `estado_seguimiento` | varchar(30) | si | 'Abierto'::character varying |  |
| `fecha_seguimiento` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### seguimiento_social

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `situacion` | varchar(255) | si |  |  |
| `contexto` | text | si |  |  |
| `factores` | text | si |  |  |
| `diagnostico_socioeducativo` | text | si |  |  |
| `intervenciones` | text | si |  |  |
| `observaciones` | text | si |  |  |
| `estado_seguimiento` | varchar(30) | si | 'Abierto'::character varying |  |
| `fecha_seguimiento` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### situacion_estudiante

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `observaciones_generales` | text | si |  |  |
| `situacion_familiar` | text | si |  |  |
| `situacion_salud` | text | si |  |  |
| `necesidades_acompanamiento` | text | si |  |  |
| `situaciones_particulares` | text | si |  |  |
| `residencia_institucional` | boolean | si | false |  |
| `observaciones_equipo` | text | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### situaciones_conflicto

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | integer | no |  | PK |
| `id_alumno` | integer | si |  | FK->alumnos(id_alumno) |
| `id_usuario_creador` | integer | si |  | FK->usuarios(id_usuario) |
| `alumnos_involucrados` | text | si |  |  |
| `tipo_situacion` | varchar(100) | si |  |  |
| `descripcion` | text | si |  |  |
| `personas_intervinientes` | text | si |  |  |
| `intervenciones` | text | si |  |  |
| `acuerdos` | text | si |  |  |
| `derivacion` | varchar(255) | si |  |  |
| `ruta_archivo` | varchar(255) | si |  |  |
| `estado_conflicto` | varchar(30) | si | 'Abierto'::character varying |  |
| `fecha_situacion` | date | si |  |  |
| `estado` | boolean | si | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | si | CURRENT_TIMESTAMP |  |
| `fecha_actualizacion` | timestamp | si |  |  |

### situaciones_materias_alumno

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_situacion` | integer | no |  | PK |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `anio_lectivo` | integer | no |  |  |
| `situacion` | text | no | 'CURSANDO'::text |  |
| `motivo_bloqueo` | text | si |  |  |
| `es_materia_original` | boolean | no | true |  |
| `fecha_inicio` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_fin` | timestamp | si |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |

### suplencias_docentes

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_suplencia` | integer | no |  | PK |
| `id_curso_materia` | integer | no |  | FK->curso_materia(id_curso_materia) |
| `id_docente_suplente` | integer | no |  | FK->docentes(id_docente) |
| `nivel` | smallint | no | '1'::smallint |  |
| `motivo` | varchar(255) | si |  |  |
| `fecha_inicio` | date | no |  |  |
| `fecha_fin` | date | no |  |  |
| `estado` | boolean | no | true |  |
| `fecha_eliminacion` | timestamp | si |  |  |
| `fecha_creacion` | timestamp | no | CURRENT_TIMESTAMP |  |
| `fecha_modificacion` | timestamp | no | CURRENT_TIMESTAMP |  |

### tipos_accion

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_tipo_accion` | integer | no |  | PK |
| `nombre_accion` | varchar(50) | no |  |  |

### tipos_acta

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_tipo_acta` | integer | no |  | PK |
| `nombre_tipo` | varchar(50) | no |  |  |

### tutor_alumno

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id` | bigint | no |  | PK |
| `id_tutor` | integer | no |  | FK->padres_tutores(id_tutor) |
| `id_alumno` | integer | no |  | FK->alumnos(id_alumno) |

### usuario_roles

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_usuario` | integer | no |  | PK, FK->usuarios(id_usuario) |
| `id_rol` | integer | no |  | PK, FK->roles(id_rol) |

### usuarios

| Columna | Tipo | Nulo | Default | Clave |
|---|---|---|---|---|
| `id_usuario` | integer | no |  | PK |
| `usuario` | varchar(50) | no |  |  |
| `contrasena` | varchar(255) | no |  |  |
| `estado` | boolean | si | true |  |
| `ultimo_acceso` | timestamp | si |  |  |
| `fecha_deshabilitacion_programada` | timestamp | si |  |  |
| `fecha_habilitacion_programada` | timestamp | si |  |  |
