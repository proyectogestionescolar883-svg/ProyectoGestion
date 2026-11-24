# Hallazgos del rol Preceptor

Fecha: 2026-11-24  
Estado general: **corregido** (con salvedad documentada en `PRE-05`).  
Alcance: auditoría de código del panel Preceptor (perfil, estudiantes, tutores, docentes, asistencias, notas/RITE, actas, horarios, adelantos, libros, proyectos, comunicados y navegación desde notificaciones) y de los endpoints/permisos que consume. Se corrigieron los 14 hallazgos; queda pendiente la validación funcional en navegador.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto o error de contrato no crítico. Los ítems marcados como compartidos también aparecen en otros MD de rol.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| PRE-01 | P0 | `PATCH`/`DELETE /api/asistencias/{id}/` no acotan el curso del preceptor. |
| PRE-02 | P0 | `asistencia-diaria` y `registro-diario` devuelven datos de cualquier curso. |
| PRE-03 | P1 | El RITE del preceptor siempre muestra 0 inasistencias y 0 tardanzas. |
| PRE-04 | P1 | Justificar asistencias ignora el modo solo lectura y el bloqueo por evento/carga. |
| PRE-05 | P1 | `navIntent` del preceptor descarta los parámetros concretos de la notificación. |
| PRE-06 | P1 | Un PATCH de adelanto puede moverlo a un curso no asignado. |
| PRE-07 | P1 | Un PATCH de horario puede reasignarlo a otra curso-materia. |
| PRE-08 | P1 | La carga de asistencias ignora los adelantos de horas. |
| PRE-09 | P1 | Usuarios `jefe_preceptores + preceptor` leen todas las curso-materias pero no pueden modificarlas. |
| PRE-10 | P2 | `preceptor-materia` devuelve 500 con `curso_materia`/`fecha` inválidos. |
| PRE-11 | P2 | Roles inconsistentes en las acciones de asistencia docente. |
| PRE-12 | P2 | `ActaDocenteViewSet` no respeta el rol activo en usuarios multirrol. |
| PRE-13 | P2 | Comunicados: vigencia y alcance por materia incorrectos (compartido). |
| PRE-14 | P2 | Notificaciones antiguas de calificaciones no muestran “Ver” para el preceptor. |

## PRE-01 — Asistencias: modificar y borrar no respeta el curso asignado

- **Síntoma:** un preceptor puede hacer `PATCH` o `DELETE` de una asistencia de cualquier curso, aunque `create()` sí esté acotado a sus cursos.
- **Causa:** `AsistenciaViewSet.get_queryset()` usa `alumnos_permitidos()`, que devuelve `None` para preceptor porque está en `ROLES_AMPLIOS`. `perform_update()` y `perform_destroy()` validan evento/docente activo/carga única, pero nunca comparan `id_curso_materia.id_curso` con `_preceptor_cursos_ids()`.
- **Ubicación:**
  - `backend/proyecto/escuela/permissions.py:14`
  - `backend/proyecto/escuela/permissions.py:109-110`
  - `backend/proyecto/escuela/permissions.py:228-236`
  - `backend/proyecto/escuela/views.py:3531-3543`
  - `backend/proyecto/escuela/views.py:3573-3594`
  - Contraste: `backend/proyecto/escuela/views.py:4121-4134` (sí acota `create()`)
- **Verificación:** lectura directa del queryset, del permiso y de los `perform_*`.
- **Corrección sugerida:** extraer el chequeo de `4124-4134` a un helper y llamarlo también en update/destroy, validando curso actual y curso destino si cambia `id_curso_materia`.
- **Corrección aplicada:** `AsistenciaViewSet._check_asistencia_curso_access()` usa `roles_efectivos()` + `_es_preceptor_operativo()` y valida el curso del curso-materia actual y del destino en `perform_update()`, y del actual en `perform_destroy()`. Los roles amplios y docentes siguen sin acotarse por este helper.
- **Criterio de aceptación:** `PATCH`/`DELETE` fuera de `_preceptor_cursos_ids()` devuelve 403; admin/director/docente conservan su comportamiento actual.

## PRE-02 — Acciones `asistencia-diaria` y `registro-diario` sin scope

- **Síntoma:** al consultar asistencias por nombre de curso, un preceptor puede ver datos de un curso que no tiene asignado.
- **Causa:** ambas acciones resuelven `Curso.objects.filter(nombre_curso=...).first()` y arman el queryset sin pasar por `get_queryset()` ni por `_es_preceptor_operativo()`. Como son `GET`, el permiso `PuedeRegistrarAsistencias` las permite a cualquier autenticado.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:3880-3904` (`asistencia-diaria`)
  - `backend/proyecto/escuela/views.py:3956-3987` (`registro-diario`)
  - `backend/proyecto/escuela/permissions.py:228-236`
  - Consumidores: `frontend/src/services/api.js:339,346`, `frontend/src/components/Preceptores/asistencias.jsx:100,129`
- **Verificación:** lectura directa de las acciones y del permiso; no hay validación de rol ni de cursos asignados.
- **Corrección sugerida:** después de resolver `curso_obj`, validar `_es_preceptor_operativo()` contra `_preceptor_cursos_ids()` y aplicar el mismo alcance a los demás roles. Rechazar nombres de curso ambiguos con 400/409 en vez de elegir `.first()`.
- **Corrección aplicada:** ambas acciones verifican `_es_preceptor_operativo()` contra `_preceptor_cursos_ids()`, aplican `alumnos_permitidos()` cuando no es `None`, y responden `409` si el nombre de curso es ambiguo.
- **Criterio de aceptación:** una consulta fuera del curso asignado devuelve 403 y un nombre duplicado no devuelve datos arbitrarios.

## PRE-03 — RITE del preceptor con inasistencias siempre en cero

- **Síntoma:** todos los RITE del panel de notas muestran `Inasist: 0 | Tardanzas: 0`, incluso cuando hay ausentes registrados.
- **Causa:** `DataContext` reemplaza la carga global de asistencias por `Promise.resolve([])` para evitar la tabla completa, pero `notas.jsx` sigue consumiendo `asistenciasAdmin` para armar `inasistenciasPorMateria`. Ese array siempre queda vacío.
- **Ubicación:**
  - `frontend/src/context/DataContext.jsx:361-367`
  - `frontend/src/context/DataContext.jsx:629-639`
  - `frontend/src/components/Preceptores/notas.jsx:10-15`
  - `frontend/src/components/Preceptores/notas.jsx:107`
  - `frontend/src/components/Preceptores/notas.jsx:115-130`
  - `frontend/src/components/Preceptores/notas.jsx:27,45,68`
- **Verificación:** lectura directa del loader y del consumidor; el comentario del loader dice que ningún componente usa el dato, lo cual es falso para `notas.jsx`.
- **Corrección sugerida:** cargar asistencias desde los endpoints con scope del preceptor para el curso/año del RITE y pasarlas a `Notas`, o quitar el consumo de `asistenciasAdmin` si el RITE debe usar otra fuente.
- **Corrección aplicada:** `Notas` consume `getAsistenciasPreceptorMateria()` por cada curso-materia del curso filtrado, descarta filas sintéticas `id: null` y alimenta `inasistenciasPorMateria` desde `asistenciasRite`. Ya no depende de `asistenciasAdmin`.
- **Criterio de aceptación:** el RITE muestra ausencias/tardanzas reales por materia y el PDF exportado coincide con la pantalla.

## PRE-04 — Justificación de asistencias burla el solo lectura

- **Síntoma:** con evento institucional con bloqueo activo, el banner dice que la información es de solo lectura, pero el checkbox “Justificado” sigue habilitado y envía el `PATCH`. También ocurre en la pestaña “por materia”, donde el banner dice que el preceptor sólo puede visualizar.
- **Causa:** `soloLectura = readOnly || bloqueaEscritura` se calcula pero no se usa en `puedeJustificar` ni en el `onChange`. El backend `justificar` valida rol y curso, pero no llama `_bloquear_si_evento_institucional()` ni revisa `carga_de_item()`, a diferencia de `perform_update`.
- **Ubicación:**
  - `frontend/src/components/Preceptores/asistencias.jsx:245-251`
  - `frontend/src/components/Preceptores/asistencias.jsx:446-451`
  - `frontend/src/components/Preceptores/asistencias.jsx:536`
  - `frontend/src/components/Preceptores/asistencias.jsx:555-575`
  - `backend/proyecto/escuela/views.py:4001-4035`
  - Contraste: `backend/proyecto/escuela/views.py:3573-3582`
- **Verificación:** lectura directa del checkbox, del handler y de la acción del backend.
- **Corrección sugerida:** incluir `!soloLectura` en `puedeJustificar`, deshabilitar el input y reforzar la acción con las mismas barreras de update. Revisar además si el `readOnly` de “por materia” debe prohibir también la justificación.
- **Corrección aplicada:** `soloLectura` ahora incluye `tab === 'materia'`; `puedeJustificar` exige `!soloLectura` y el checkbox queda `disabled`. En backend, `justificar` usa `roles_efectivos()`, llama `_bloquear_si_evento_institucional()` y rechaza estados `bloqueado_cargado`/`bloqueado_vencido` de `carga_de_item()`.
- **Criterio de aceptación:** con evento bloqueante o carga cerrada/vencida no se puede justificar desde la UI ni desde la API; en “por materia” no hay controles de escritura.

## PRE-05 — Navegación desde notificaciones pierde el contexto

- **Síntoma:** las notificaciones llevan a la sección correcta, pero no abren el curso/materia/fecha/alumno/acta/adelanto/evento correspondiente.
- **Causa:** `PreceptorDashboard` sólo lee `anio`, `cursoNombre`/`curso` y `cursoId` de `navIntent.params`. El backend emite otros ids que `DataContext` tampoco propaga a la vista destino.
- **Ubicación:**
  - `frontend/src/components/Preceptores/PreceptorDashboard.jsx:47-72`
  - `frontend/src/context/DataContext.jsx:261-289`
  - Backend emite:
    - `views.py:7218-7224` (`cursoMateriaId`, `alumnoId` en notas)
    - `views.py:7249-7255` (`cursoMateriaId`, `fecha` en asistencias)
    - `views.py:7335-7340` (`actaId`)
    - `views.py:7383-7388` (`adelantoId`)
    - `views.py:7821-7826` (`eventoId`)
    - `views.py:7988-7993` (`horarioId`, `cursoMateriaId`)
  - Mapeo de destinos correcto: `frontend/src/utils/navDestinos.js:59-69`
- **Verificación:** contraste directo entre los parámetros emitidos y los consumidos.
- **Corrección sugerida:** resolver `cursoMateriaId` contra `cursoMateria` para derivar curso/materia, y pasar `fecha`, `alumnoId`, `actaId`, `adelantoId` y `eventoId` a `Asistencias`, `Notas`, `Actas`, `AdelantosHoras` y `CalendarioInstitucional`. Mantener el guard por `timestamp`.
- **Corrección aplicada:** `PreceptorDashboard` guarda `navContext` con todos los parámetros, resuelve `cursoMateriaId` contra `cursoMateria`/`cursosObj` para preseleccionar curso y deriva la materia para comunicados. `Asistencias` aplica `cursoMateriaId`/`fecha`/`alumnoId`, `Notas` expande el RITE de `alumnoId`, `Actas` abre el `actaId` y `CalendarioInstitucional` ubica y abre el `eventoId`, cada uno con guard por `timestamp`. `horarioId` ya queda cubierto por el curso derivado del `cursoMateriaId` y el selector global.
- **Salvedad:** no se implementó el resaltado de `adelantoId` dentro de `frontend/src/components/Shared/AdelantosHoras.jsx` porque `AGENTS.md` lo marca como resuelto y no se puede tocar sin pedido explícito. La navegación abre el módulo con el contexto de curso ya aplicado.
- **Criterio de aceptación:** cada notificación abre el registro concreto con el contexto ya seleccionado (salvedad de `adelantoId` documentada).

## PRE-06 — Adelantos: PATCH valida el curso anterior

- **Síntoma:** un preceptor del curso A puede editar un adelanto de A y cambiarle `id_curso` al curso B, al que no está asignado.
- **Causa:** `perform_update()` llama `_check_curso_acceso(instancia.id_curso_id)`, pero el curso que se valida en el contexto es `serializer.validated_data['id_curso']`. `id_curso` es escribible en el serializer.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:3085-3094`
  - `backend/proyecto/escuela/views.py:3115-3128`
  - `backend/proyecto/escuela/serializers.py:3253-3268`
  - Contraste correcto: `backend/proyecto/escuela/views.py:2949-2952` (curso-materia sí valida el destino)
- **Verificación:** lectura directa de `perform_update` y del serializer.
- **Corrección sugerida:** calcular `curso_destino` desde `validated_data` y llamar `_check_curso_acceso()` para el curso actual y el destino antes de guardar.
- **Corrección aplicada:** `AdelantoHorasViewSet.perform_update()` vuelve a llamar `_check_curso_acceso()` cuando `validated_data['id_curso']` cambia el curso de la instancia.
- **Criterio de aceptación:** mover un adelanto a un curso no asignado devuelve 403 y no persiste.

## PRE-07 — Horarios: PATCH valida la instancia anterior

- **Síntoma:** un preceptor puede reasignar un horario a una curso-materia de otro curso; la validación de permisos se hace contra el horario original.
- **Causa:** `perform_update()` de `HorarioViewSet` y `HorarioEspecialViewSet` usa `_check_horario_write_access(serializer.instance)`, pero `id_curso_materia` sigue siendo escribible porque ambos serializers usan `fields = '__all__'`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:3210-3212`
  - `backend/proyecto/escuela/views.py:3278-3280`
  - `backend/proyecto/escuela/serializers.py:2497-2527`
  - `backend/proyecto/escuela/serializers.py:2555-2572`
- **Verificación:** lectura directa de los `perform_update` y de los `Meta.fields`.
- **Corrección sugerida:** en ambos viewsets, validar también `serializer.validated_data.get('id_curso_materia')`.
- **Corrección aplicada:** ambos `perform_update()` validan la instancia y el `id_curso_materia` destino con `_check_horario_write_access()`.
- **Criterio de aceptación:** un PATCH que cambia `id_curso_materia` a otro curso devuelve 403.

## PRE-08 — Carga de asistencias ignora adelantos de horas

- **Síntoma:** con un adelanto que reemplaza el horario original, `server-time` puede indicar “en horario”, pero el intento de guardar asistencias es rechazado por “esperando/terminado”.
- **Causa:** `server_time()` llama `_horarios_hoy(cm_id, dia, fecha)`, que sí incorpora adelantos cuando recibe `fecha`. `AsistenciaViewSet.create()` llama `_horarios_hoy(cm_id, dia)` sin la fecha, por lo que sólo ve horarios normales.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:3596-3609`
  - `backend/proyecto/escuela/views.py:3681-3707`
  - `backend/proyecto/escuela/views.py:4167-4171`
- **Verificación:** lectura directa de ambos llamados al helper.
- **Corrección sugerida:** pasar `fecha_registro` a `_horarios_hoy()` en `create()` y usar el mismo conjunto de franjas para `_bloque_actual()`.
- **Corrección aplicada:** `create()` pasa `fecha_registro` a `_horarios_hoy()`; `_bloque_actual()` ya lo hacía, por lo que `server-time` y guardado usan el mismo conjunto de franjas.
- **Criterio de aceptación:** la carga habilitada por un adelanto es aceptada por `create()`; el bloque original cancelado por el adelanto no habilita carga.

## PRE-09 — Curso-materia: lectura amplia y escritura acotada para multirrol

- **Síntoma:** un usuario con roles `jefe_preceptores + preceptor` ve todas las curso-materias, pero recibe 403 al querer modificar las de cursos donde no es preceptor.
- **Causa:** `get_queryset()` usa `es_rol_amplio()`, que incluye `jefe_preceptores`, mientras `_check_preceptor_curso_access()` sólo exceptúa a admin/director y exige `preceptor` + cursos asignados para el resto. `_es_preceptor_operativo()` ya define que los roles de gestión no quedan acotados, pero no se usa acá.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:268-279`
  - `backend/proyecto/escuela/views.py:2898-2911`
  - `backend/proyecto/escuela/views.py:2932-2941`
  - `backend/proyecto/escuela/permissions.py:14`
  - `backend/proyecto/escuela/permissions.py:73-74`
- **Verificación:** lectura directa de las tres funciones.
- **Corrección sugerida:** usar `_es_preceptor_operativo()` o `roles_efectivos()` en `_check_preceptor_curso_access()` y en los `perform_*`, alineando lectura y escritura.
- **Corrección aplicada:** `_check_preceptor_curso_access()` usa `roles_efectivos()`, exceptúa `admin`/`director`/`jefe_preceptores` y delega el resto a `_es_preceptor_operativo()`. La rama de lectura ya estaba corregida y no se modificó.
- **Criterio de aceptación:** los roles de gestión ven y gestionan todo el ámbito; preceptor puro queda acotado a sus cursos en lectura y escritura.

## PRE-10 — `preceptor-materia` devuelve 500 con parámetros inválidos

- **Síntoma:** `?curso_materia=abc` o `?fecha=2026-13-99` produce error interno en vez de 400.
- **Causa:** `CursoMateria.objects.get(id_curso_materia=cm_id)` sólo captura `DoesNotExist`, no `ValueError`. `datetime.strptime(fecha_str, '%Y-%m-%d')` se ejecuta sin `try/except`.
- **Ubicación:** `backend/proyecto/escuela/views.py:3814-3824`, `backend/proyecto/escuela/views.py:3840`
- **Verificación:** lectura directa del bloque. El alcance por curso sí está bien implementado en `3809-3824`.
- **Corrección sugerida:** validar ambos parámetros al inicio con `int()` y `datetime.strptime()` dentro de `try/except (TypeError, ValueError)`, respondiendo 400 con mensaje claro.
- **Corrección aplicada:** `preceptor_materia` valida `curso_materia`, `fecha` y `alumno` con conversiones protegidas y responde `400` antes de tocar ORM; usa la fecha parseada para filtrar y calcular el día de la semana.
- **Criterio de aceptación:** parámetros malformados devuelven 400; valores válidos siguen funcionando igual.

## PRE-11 — Roles inconsistentes en asistencia docente

- **Síntoma:** un `jefe_preceptores` ve “docentes disponibles”, pero recibe 403 en “hoy”, “historial” y al registrar asistencia docente.
- **Causa:** cada action define su propia lista de roles: `docentes_disponibles` incluye `jefe_preceptores`; `hoy` e `historial` no; `registrar-asistencia-docente` lo rechaza explícitamente.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:4235-4239`
  - `backend/proyecto/escuela/views.py:4420-4424`
  - `backend/proyecto/escuela/views.py:4547-4551`
  - `backend/proyecto/escuela/views.py:4591-4597`
- **Verificación:** lectura directa de las cuatro acciones.
- **Corrección sugerida:** unificar la política en un helper de roles permitidos y usarlo en las cuatro acciones, tanto para lectura como para escritura.
- **Corrección aplicada:** `_puede_asistencia_docente()` centraliza la política (`admin`/`director`/`preceptor`, con `roles_efectivos()`) y lo usan `docentes_disponibles`, `hoy`, `historial` y `registrar_asistencia_docente`. El jefe puro ya no ve “docentes disponibles”.
- **Criterio de aceptación:** las cuatro acciones coinciden en quién puede consultar y registrar; si jefe no debe registrar, tampoco debería ver docentes disponibles con ese fin.

## PRE-12 — `ActaDocenteViewSet` ignora el rol activo

- **Síntoma:** un usuario con roles `docente + preceptor` que opera como docente no ve filtradas sus actas docente.
- **Causa:** `get_queryset()` usa `es_rol_amplio()`, que mira todos los roles reales e incluye `preceptor`. El resto de `ActaPropiedadMixin` ya usa `roles_efectivos()` para respetar `X-Rol-Activo`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:5159-5170`
  - `backend/proyecto/escuela/views.py:5020-5027`
  - `backend/proyecto/escuela/permissions.py:14`
  - `backend/proyecto/escuela/permissions.py:73-74`
- **Verificación:** lectura directa de ambos puntos.
- **Corrección sugerida:** reemplazar `es_rol_amplio(self.request)` por `roles_efectivos(self.request)` en este filtro.
- **Corrección aplicada:** el filtro usa `self._roles_usuario()` (que devuelve `roles_efectivos()`), por lo que el rol activo manda también en `ActaDocenteViewSet`.
- **Criterio de aceptación:** el filtro respeta el rol activo; docente puro sigue viendo sólo sus actas y preceptor puro ve todas las del ámbito.

## PRE-13 — Comunicados: vigencia y materia no se aplican bien (compartido)

- **Síntoma:** comunicados de ciclos anteriores siguen apareciendo como vigentes; un comunicado con alcance por materia se muestra a todo el preceptor del curso.
- **Causa:** `comunicadoEstaVigente()` buscaba `id_ciclo` en `aniosLectivos`, que es un array de números, por lo que el `find` fallaba y caía en “ciclo no encontrado = vigente”. Además, `comunicadoMatchesAlcance()` calcula `hasMateria` pero nunca lo usa, y la rama `preceptor` filtra sólo por curso.
- **Ubicación:**
  - `frontend/src/components/Shared/ComunicadosView.jsx:22-38`
  - `frontend/src/components/Shared/ComunicadosView.jsx:47-60`
  - `frontend/src/components/Shared/ComunicadosView.jsx:159-166`
  - `frontend/src/context/DataContext.jsx:572-573`
  - Referencias: `AL-04`, `FAM-07`, `DOC-10`
- **Verificación:** mismo defecto de vigencia reportado en otros roles, más el `hasMateria` calculado y descartado en el helper.
- **Corrección sugerida:** resolver `id_ciclo` contra `ciclosLectivos` y decidir explícitamente si el preceptor debe ver comunicados por materia o sólo generales de curso; en el primer caso, pasar el id de materia al matcher.
- **Corrección aplicada:** la vigencia con `ciclosLectivos` y `estado === false` ya venía corregida desde el fix compartido. Se extendió `comunicadoMatchesAlcance()`/`comunicadoMatchesCurso()` con un tercer argumento `idMateria`: los roles sin selección de materia mantienen el comportamiento previo (`undefined`), mientras el preceptor pasa `null` cuando no hay materia elegida (oculta comunicados por materia) o el `id_materia` derivado de `cursoMateria` cuando la notificación lo trae.
- **Criterio de aceptación:** comunicados viejos ocultos y alcance por materia coherente con la política definida.

## PRE-14 — Notificaciones antiguas de calificaciones sin “Ver”

- **Síntoma:** una notificación vieja sin `nav_destino` cuyo título dice “calificación” no muestra el botón “Ver” para el preceptor.
- **Causa:** `destinoDesdeTitulo()` devuelve `calificaciones`, pero el mapa del rol preceptor sólo define `notas`. `tieneVistaParaDestino()` oculta la acción porque no hay vista para ese destino.
- **Ubicación:**
  - `frontend/src/utils/navDestinos.js:59-69`
  - `frontend/src/utils/navDestinos.js:116-118`
  - `frontend/src/utils/navDestinos.js:124-130`
  - `frontend/src/components/Notificaciones.jsx:109-117`
- **Verificación:** lectura directa del fallback y del mapa del rol.
- **Corrección sugerida:** agregar alias `calificaciones` (y, si aplica, `boletin`/`previas`/`rendiciones`) al mapa de preceptor, o normalizar `destinoDesdeTitulo()` a destinos por rol.
- **Corrección aplicada:** el mapa de `preceptor` incluye alias `calificaciones`, `boletin`, `previas`, `rendiciones`, `intensificaciones` y `recursadas` hacia `notas`. `jefe_preceptores` queda cubierto por `ROL_EQUIV`.
- **Criterio de aceptación:** las notificaciones antiguas de calificaciones navegan a la vista “Notas” del preceptor.

## Orden sugerido de corrección

1. `PRE-01`, `PRE-02` — scope de lectura/escritura de asistencias.
2. `PRE-03`, `PRE-04`, `PRE-05` — RITE, solo lectura y navegación visibles.
3. `PRE-06`, `PRE-07`, `PRE-08`, `PRE-09` — adelantos, horarios y multirrol.
4. `PRE-10` a `PRE-14` — validaciones, consistencia de roles y compartidos.

## Revisado sin hallazgos

- `create()` de asistencias sí acota el curso del preceptor en `views.py:4124-4134`.
- `preceptor-materia` sí valida cursos asignados en `views.py:3809-3824`; el hallazgo `PRE-10` es sólo por parámetros malformados.
- Actas de curso: `DataContext.jsx:688-703` mapea `curso` e `id_acta_curso`; `actas.jsx:323-325`, `464` y `486-489` usan los ids correctos. No hay lista vacía por falta de `curso`.
- PDFs del panel Preceptor usan `buildMediaUrl()` en `actas.jsx`, `LibroTemasPreceptor.jsx` y `Proyectos.jsx`.
- `Horarios` recibe y aplica `cursoGlobal` correctamente en `frontend/src/components/Administracion/horarios.jsx:534-574`.
- `PreceptorDashboard` ya tiene guard `navAplicadoRef` para no reaplicar un `navIntent` (`PreceptorDashboard.jsx:44-50`).
- El orden de hooks en `AvisoDatosMaestros` y `useRiteAcademico` no presenta violaciones para este rol.
