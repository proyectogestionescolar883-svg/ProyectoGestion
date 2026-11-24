# Hallazgos del rol Familia/Tutor

Fecha: 2026-11-24  
Estado general: **corregido**.  
Alcance: auditoría y corrección del portal Familia (selector de hijo, notificaciones, vistas compartidas) y de los endpoints/permisos que consume. Los 9 hallazgos fueron corregidos (algunos compartidos con Alumno) y validados con `npm run build`, `python manage.py check` y `git diff --check`.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto. Los ítems marcados como compartidos también aparecen en `docs/HALLAZGOS_ROL_ALUMNO.md`.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| FAM-01 | P0 | Endpoints de actas devuelven actas de todos los alumnos; el filtro por hijo solo se hace en el cliente. |
| FAM-02 | P0 | `/api/inscripciones/` se carga globalmente sin scope ni `?alumno=`. |
| FAM-03 | P1 | El panel de materias adeudadas ignora el hijo seleccionado para intensificaciones y rendiciones. |
| FAM-04 | P1 | La navegación desde notificaciones se vuelve a aplicar al cambiar de hijo o marcar leídas. |
| FAM-05 | P1 | PDF de materias adeudadas con URL relativa sin construir (compartido con Alumno). |
| FAM-06 | P1 | `?id_alumno=abc` en asistencias genera 500 en vez de 400/404. |
| FAM-07 | P2 | Comunicados: clave React inexistente y vigencia siempre verdadera (compartido con Alumno). |
| FAM-08 | P2 | El estado vacío de materias adeudadas oculta intensificaciones sin deuda cargada. |
| FAM-09 | P2 | El RITE de Familia usa el año calendario en vez del ciclo del hijo (compartido con Alumno). |

## Correcciones aplicadas

| ID | Estado | Cómo se solucionó |
|---|---|---|
| FAM-01 | Corregido | Los viewsets de actas acotan el queryset cuando el rol efectivo es `familia` o `alumno`: `ActaViewSet` restringe a actas vinculadas a los alumnos permitidos y a sus cursos; `ActaAlumnoViewSet` filtra `id_alumno__in=alumnos_permitidos()`; `ActaCursoViewSet` filtra por los cursos de esos alumnos; `ActaDocenteViewSet` deriva los docentes de esos cursos. Admin/Director/Preceptor/Jefe conservan el ámbito amplio. |
| FAM-02 | Corregido | `InscripcionMateriaViewSet.get_queryset()` aplica `alumnos_permitidos()` antes del filtro opcional `?alumno=`; el parámetro se convierte a `int` y un valor inválido devuelve `qs.none()` en vez de un 500. La familia ya no descarga inscripciones globales. |
| FAM-03 | Corregido | `RendicionMateriaAdeudadaViewSet` ahora respeta `?alumno=` después de `alumnos_permitidos()`; las intensificaciones ya habían sido corregidas en `AL-09`. El panel compartido sigue enviando `?alumno=<hijo>` a los cuatro endpoints. |
| FAM-04 | Corregido | `FamiliaDashboard` agregó `navAplicadoRef` con early return por `navIntent.timestamp`. Un mismo `navIntent` navega una sola vez aunque cambien `hijos`/`notificaciones`. |
| FAM-05 | Corregido | Resuelto en la pasada de Alumno por ser archivo compartido: `PanelMateriasAdeudadas.jsx` usa `buildMediaUrl(act.archivo_pdf)` en los dos botones de descarga. |
| FAM-06 | Corregido | En `alumno_detalle`, `id_alumno` se convierte con `int()` dentro de `try/except (TypeError, ValueError)` y responde 400 si no es numérico; si no pertenece al tutor sigue respondiendo 404. |
| FAM-07 | Corregido | La vigencia usa `ciclosLectivos` (objetos con `id_ciclo`, `anio`, `estado`) desde la pasada de Alumno; además la fila de la tabla usa `key={c.id || c.id_comunicado}`, compatible con el shape que construye `DataContext`. |
| FAM-08 | Corregido | El panel ya no hace early return solo por `deudas.length === 0`. Si no hay deudas pero hay intensificaciones, actividades o rendiciones, genera filas derivadas por materia y reutiliza el mismo render; el estado vacío aparece solo cuando los cuatro arrays están vacíos. |
| FAM-09 | Corregido | `AlumnoSerializer` expone `ciclo_anio`, `DataContext` lo conserva al armar `estudiantes`, y `Calificaciones.jsx` usa `estudiante.ciclo_anio` con fallback al año calendario. |

Validación: `npm run build` terminó con `✓ built` (warning de chunks >500 kB es benigno), `python manage.py check` informó `System check identified no issues (1 silenced).` y `git diff --check` no reportó errores. No se hicieron commits ni pushes.

## FAM-01 — Actas sin scope: el filtro por hijo es solo visual

- **Síntoma:** una familia podría recibir en la respuesta de la API actas de alumnos que no son sus hijos. El portal las oculta en pantalla, pero el dato viaja en la respuesta.
- **Causa:** `PuedeGestionarActas` hereda de `_puede_escribir()`: toda lectura autenticada pasa. `ActaViewSet`, `ActaAlumnoViewSet`, `ActaCursoViewSet` y `ActaDocenteViewSet` no acotan el queryset a `alumnos_permitidos()`/`alumno_ids_familia()`. El frontend carga los cuatro endpoints al inicio y recién después filtra `actasEstudiante` por `alumnoId`.
- **Ubicación:**
  - `backend/proyecto/escuela/permissions.py:179-185`
  - `backend/proyecto/escuela/permissions.py:214-225`
  - `backend/proyecto/escuela/views.py:5047-5076` (`ActaViewSet`)
  - `backend/proyecto/escuela/views.py:5139-5146` (`ActaAlumnoViewSet`)
  - `backend/proyecto/escuela/views.py:5149-5156` (`ActaCursoViewSet`)
  - `backend/proyecto/escuela/views.py:5159-5170` (`ActaDocenteViewSet`)
  - `frontend/src/context/DataContext.jsx:350-386`
  - `frontend/src/context/DataContext.jsx:641-670`
  - `frontend/src/components/Familia/Actas.jsx:8-11`
- **Verificación:** lectura directa de permisos, viewsets y del filtro cliente `.filter((a) => a.alumnoId === hijo.alumnoId)`.
- **Corrección sugerida:** agregar `get_queryset()` con scope por rol en los viewsets de actas; para familia, limitar a `id_alumno__in=alumno_ids_familia(request)` (y cursos/docentes derivados de esos alumnos).
- **Criterio de aceptación:** una llamada directa a `/api/acta-alumno/` con token de familia solo devuelve relaciones de sus hijos.

## FAM-02 — Inscripciones globales sin filtro por alumno

- **Síntoma:** al iniciar, cualquier usuario autenticado (incluida Familia) descarga todas las inscripciones de materias; el parámetro `?alumno=` existe pero no se usa.
- **Causa:** `InscripcionMateriaViewSet` permite lectura a cualquier autenticado y solo aplica `?alumno=` cuando viene explícitamente. `getInscripciones()` no envía parámetros y `DataContext` dispara `ensureData(['inscripciones', ...])` para todos los roles.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:3289-3301`
  - `backend/proyecto/escuela/permissions.py:126-132`
  - `frontend/src/services/api.js:625-628`
  - `frontend/src/context/DataContext.jsx:105-115`
  - `frontend/src/context/DataContext.jsx:928-932`
- **Verificación:** contraste entre el filtro opcional del backend y el loader sin params del frontend.
- **Corrección sugerida:** scope por `alumnos_permitidos()` en `get_queryset()` y enviar `?alumno=<hijo>` desde Familia cuando se cargue por alumno.
- **Criterio de aceptación:** una familia solo recibe inscripciones de sus hijos, incluso si llama directo a la API.

## FAM-03 — Materias adeudadas mezcla hermanos

- **Síntoma:** con dos hijos, seleccionar uno puede mostrar intensificaciones y rendiciones del otro cuando coinciden por nombre de materia.
- **Causa:** el panel compartido envía `?alumno=<id>` a los cuatro endpoints. `MateriaAdeudada` y `Actividades` sí respetan ese parámetro, pero `IntensificacionAcademicaViewSet` y `RendicionMateriaAdeudadaViewSet` solo usan `alumnos_permitidos()`, que para familia devuelve **todos** los hijos. Además, las intensificaciones se indexan por `materia_nombre`.
- **Ubicación:**
  - `frontend/src/components/Familia/FamiliaDashboard.jsx:108-125`
  - `frontend/src/components/Familia/PanelMateriasAdeudadasFamilia.jsx:9-15`
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:77-83`
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:99-127`
  - `backend/proyecto/escuela/views.py:6592-6597` (intensificaciones, sin `alumno`)
  - `backend/proyecto/escuela/views.py:6970-6982` (rendiciones, sin `alumno`)
  - `backend/proyecto/escuela/views.py:6676-6684` y `6866-6874` (sí respetan `alumno`)
  - `backend/proyecto/escuela/permissions.py:101-123`
- **Verificación:** lectura directa de los cuatro querysets y del armado de mapas por materia.
- **Corrección sugerida:** en ambos viewsets, validar `query_params['alumno']` contra `alumnos_permitidos()` y filtrar por él; en el frontend, keyar también por `id_alumno` como defensa adicional.
- **Criterio de aceptación:** al cambiar de hijo, el panel muestra exclusivamente datos de ese `id_alumno`.

## FAM-04 — `navIntent` se reaplica solo

- **Síntoma:** después de abrir una sección desde una notificación, cambiar de hijo o marcar otra notificación como leída vuelve a llevar a la vista/hijo anterior.
- **Causa:** el efecto de `navIntent` depende de `[navIntent, hijos]`, y `hijos` se recalcula cuando cambia `notificaciones`. Marcar leídas y el sondeo reemplazan el array de notificaciones, por lo que el efecto vuelve a correr con el mismo `navIntent`; no hay guard de “ya aplicado”.
- **Ubicación:**
  - `frontend/src/components/Familia/FamiliaDashboard.jsx:31-47`
  - `frontend/src/components/Familia/FamiliaDashboard.jsx:56-67`
  - `frontend/src/context/DataContext.jsx:1105-1107`
  - `frontend/src/context/DataContext.jsx:1116-1119`
  - `frontend/src/context/DataContext.jsx:1136-1146`
  - Referencia de guard correcto: `frontend/src/components/Preceptores/PreceptorDashboard.jsx:44-50`
- **Verificación:** comparación directa con el patrón ya corregido en Preceptores/Jefe de Preceptores.
- **Corrección sugerida:** `navAplicadoRef = useRef(null)` con early return si `navAplicadoRef.current === navIntent.timestamp`.
- **Criterio de aceptación:** un `navIntent` navega una sola vez; los cambios posteriores de notificaciones no alteran la vista elegida manualmente.

## FAM-05 — PDF de materias adeudadas con `href` crudo

- **Síntoma:** “Descargar PDF” de intensificaciones/previas abre 404 o HTML del SPA en vez del archivo.
- **Causa:** el serializer devuelve `/api/media/...?exp=...&sig=...`; el componente lo usa directo en `href`. El frontend tiene `base: '/misecundaria7/'` y no hay proxy para `/api`.
- **Ubicación:**
  - `backend/proyecto/escuela/serializers.py:3499-3502`
  - `backend/proyecto/escuela/storage.py:39-44`
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:233`
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:289`
  - `frontend/vite.config.js:4-10`
  - Contraste correcto: `frontend/src/components/Familia/Actas.jsx:40-48`
- **Verificación:** mismo defecto reportado como `AL-02`; se repite acá porque el portal Familia usa el panel compartido.
- **Corrección sugerida:** `href={buildMediaUrl(act.archivo_pdf)}`.
- **Criterio de aceptación:** el PDF se abre contra el origin de la API.

## FAM-06 — `id_alumno` no numérico produce 500

- **Síntoma:** `GET /api/asistencias/alumno-detalle/?id_alumno=abc` devuelve error interno en vez de 400/404.
- **Causa:** para rol `familia`, el valor de query params se pasa directo a `Alumno.objects.filter(id_alumno=alumno_id, ...)`. El `try/except` solo captura `PadreTutor.DoesNotExist` y `Alumno.DoesNotExist`, no `ValueError`.
- **Ubicación:** `backend/proyecto/escuela/views.py:3755-3768`
- **Verificación:** lectura directa del bloque `familia` del action `alumno_detalle`.
- **Corrección sugerida:** convertir con `int(alumno_id)` dentro de `try/except (TypeError, ValueError)` y responder 400; mantener 404 si no pertenece al tutor.
- **Criterio de aceptación:** valores inválidos devuelven 400 y valores ajenos devuelven 404, sin 500.

## FAM-07 — Comunicados: clave rota y vigencia inactiva

- **Síntoma:** warnings de React por `key` duplicado/inexistente y comunicados de ciclos anteriores que siguen apareciendo.
- **Causa:** `ComunicadosView` usa `key={c.id_comunicado}`, pero `DataContext` solo deja `id: c.id_comunicado`. Además, `comunicadoEstaVigente()` busca `id_ciclo` dentro de `aniosLectivos`, que son números; el `find` falla y cae en “ciclo no encontrado = vigente”.
- **Ubicación:**
  - `frontend/src/components/Shared/ComunicadosView.jsx:47-60`
  - `frontend/src/components/Shared/ComunicadosView.jsx:329`
  - `frontend/src/context/DataContext.jsx:572-573`
  - `frontend/src/context/DataContext.jsx:751-777`
  - `frontend/src/components/Familia/FamiliaDashboard.jsx:149-154`
- **Verificación:** Familia llama directo a `ComunicadosView`, no al wrapper viejo que sí usa `c.id`.
- **Corrección sugerida:** `key={c.id}` y usar `ciclosLectivos` para resolver `id_ciclo -> anio`.
- **Criterio de aceptación:** sin warnings de clave y comunicados viejos ocultos.

## FAM-08 — Sin deudas cargadas se ocultan intensificaciones

- **Síntoma:** un hijo con situaciones `INTENSIFICANDO` pero sin fila en `MateriaAdeudada` ve “El estudiante no tiene materias adeudadas”, aunque existan actividades/intensificaciones cargadas.
- **Causa:** el early return del panel solo revisa `deudas.length === 0`. El backend de actividades incluye explícitamente `SituacionMateriaAlumno(situacion='INTENSIFICANDO')`, que es un universo distinto de `MateriaAdeudada`.
- **Ubicación:**
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:138-147`
  - `backend/proyecto/escuela/views.py:6877-6891`
  - `backend/proyecto/escuela/academico.py:90-100`
  - `backend/proyecto/escuela/views.py:7953-7958`
- **Verificación:** contrato entre el early return y el endpoint de actividades. Sin datos reales reproducidos, pero confirmado por código.
- **Corrección sugerida:** mostrar el estado vacío solo si `deudas`, `actividades`, `intensificaciones` y `rendiciones` están vacíos; si faltan deudas pero hay intensificaciones, renderizar una sección derivada de esos arrays.
- **Criterio de aceptación:** el panel nunca contradiga las actividades/intensificaciones que el propio backend devuelve.

## FAM-09 — RITE con año calendario en vez del ciclo del hijo

- **Síntoma:** el PDF del RITE puede decir “Ciclo lectivo: 2026” aunque el hijo pertenezca a otro ciclo.
- **Causa:** `anioLectivo: new Date().getFullYear()`. El dato correcto ya está disponible como `estudiante.ciclo_anio`.
- **Ubicación:**
  - `frontend/src/components/Familia/Calificaciones.jsx:79-93`
  - `frontend/src/components/Familia/Calificaciones.jsx:85`
  - `frontend/src/context/DataContext.jsx:510-516`
  - `frontend/src/components/Familia/Resumen.jsx:143`
  - `frontend/src/utils/rite.js:175,200`
- **Verificación:** mismo patrón que `AL-06`, pero en el componente de Familia.
- **Corrección sugerida:** `anioLectivo: estudiante.ciclo_anio || new Date().getFullYear()`.
- **Criterio de aceptación:** el PDF respeta el ciclo del estudiante seleccionado.

## Orden en que se aplicaron las correcciones

1. `FAM-01`, `FAM-02` — scope en backend.
2. `FAM-03`, `FAM-06` — datos por hijo y errores de API.
3. `FAM-04`, `FAM-05` — navegación y descargas.
4. `FAM-07`, `FAM-08`, `FAM-09` — consistencia visual.

## Revisado sin hallazgos

Asistencias por hijo (`useAsistenciasAlumno` y `alumno-detalle` con tutor validado), campana de notificaciones por hijo, actividades por hijo, `ActividadDocenteViewSet` con scope previo al filtro `?curso=`, horarios/calendario, destinos de `navDestinos.js` para familia y el shape de `CalificacionSerializer` frente al mapeo de `DataContext`.
