# Hallazgos del rol Alumno/Estudiante

Fecha: 2026-11-24  
Estado general: **corregido**.  
Alcance: auditoría y corrección del flujo usado por `alumno`/`estudiante` en frontend y backend. Los 9 hallazgos fueron corregidos y validados con `npm run build`, `python manage.py check` y `git diff --check`. Este MD reemplaza a los documentos genéricos de hallazgos ya cerrados.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| AL-01 | P0 | `GET /api/alumnos/` devuelve todos los estudiantes a un usuario alumno. |
| AL-02 | P1 | Los PDF de Materias Adeudadas apuntan al origin del frontend, no al backend. |
| AL-03 | P1 | Las notificaciones de actividades abren “Materias Adeudadas” en vez de “Actividades”. |
| AL-04 | P1 | El filtro de vigencia de comunicados siempre deja pasar comunicados viejos. |
| AL-05 | P1 | Las URLs de archivos firman con 5 minutos de expiración y quedan cacheadas. |
| AL-06 | P2 | El RITE usa el año calendario en vez del ciclo lectivo. |
| AL-07 | P2 | El panel de recursadas muestra el curso en la columna de año. |
| AL-08 | P2 | La vista de horarios pide adelantos de horas y recibe 403 silencioso. |
| AL-09 | P2 | El parámetro `?alumno=` se ignora en intensificaciones. |

## Correcciones aplicadas

| ID | Estado | Cómo se solucionó |
|---|---|---|
| AL-01 | Corregido | `AlumnoViewSet.get_queryset()` ahora calcula `roles_activos`/`rol_activo` con `roles_efectivos()`/`rol_activo_usuario()` y, cuando el usuario opera como `alumno`, filtra `id_usuario=usuario_obj` antes de aplicar `?curso=`. El filtro por otro curso/DNI no amplía el resultado. Multi-rol con header respeta el rol elegido; sin header, un usuario con un único rol `alumno` también queda acotado. |
| AL-02 | Corregido | `PanelMateriasAdeudadas.jsx` importa `buildMediaUrl` y lo usa en los dos `href` de `archivo_pdf`; los PDF vuelven a resolverse contra el origin del backend. |
| AL-03 | Corregido | `navDestinos.js` mapea `actividades -> actividades`. Además, `EstudianteDashboard` agregó `navAplicadoRef` con guard por `navIntent.timestamp`, igual que los otros dashboards, evitando reprocesar la misma navegación. |
| AL-04 | Corregido | `ComunicadosView` dejó de usar `aniosLectivos` (lista de números) y usa `ciclosLectivos` (objetos con `id_ciclo`, `anio`, `estado`). Solo pasa el ciclo activo de mayor año y exige que `alcance.id_ciclo` coincida; sin ciclo activo, no muestra comunicados con alcance. |
| AL-05 | Corregido | `media_url()` usa TTL por defecto de 3600 s (`settings.MEDIA_URL_EXPIRES_IN` si está definido) en vez de 300 s. La firma HMAC y `verificar_firma()` no cambiaron; los callers explícitos con 3600 siguen igual. |
| AL-06 | Corregido | `AlumnoSerializer` expone `ciclo_anio` desde `id_curso.id_ciclo.anio`; `handleDescargarRite` usa `miEstudiante.ciclo_anio` con fallback a `cursosObj` y recién entonces al año calendario. |
| AL-07 | Corregido | El boletín devuelve `curso` (curso de recursada), `curso_origen`, `ciclo_anio` (`anio_inicio`) y mantiene `anio` para el RITE. `PanelEstudiante` muestra el curso en “Curso / División” y `ciclo_anio` en “Año Lectivo”. |
| AL-08 | Corregido | `VistaHorarios` acepta `cargarAdelantos = true`; el dashboard del alumno pasa `false`, por lo que no se llama a `getAdelantosHoras()` ni se genera el 403 silencioso. El resto de las vistas conservan el comportamiento anterior. |
| AL-09 | Corregido | `IntensificacionAcademicaViewSet.get_queryset()` aplica `?alumno=` después de `alumnos_permitidos()`; un id inválido devuelve `qs.none()` en vez de un 500. |

Validación: `npm run build` terminó con `✓ built` (warning de chunks >500 kB es benigno), `python manage.py check` informó `System check identified no issues (1 silenced).` y `git diff --check` no reportó errores. No se hicieron commits ni pushes.

## AL-01 — Exposición masiva de datos de estudiantes

- **Síntoma:** un usuario con rol `alumno` puede listar todos los alumnos, no solo su propia ficha.
- **Causa:** `PuedeGestionarPersonas` usa `_puede_escribir()`, que permite lectura a cualquier autenticado. `AlumnoViewSet.get_queryset()` tiene ramas para preceptor, roles amplios, familia y docente, pero no para `alumno`.
- **Datos expuestos:** DNI, fecha de nacimiento, dirección, teléfono, procedencia, curso, tutor y usuario. La contraseña **no** se expone: es `write_only`.
- **Ubicación:**
  - `backend/proyecto/escuela/permissions.py:179-185`
  - `backend/proyecto/escuela/permissions.py:200-211`
  - `backend/proyecto/escuela/views.py:1952-1985`
  - `backend/proyecto/escuela/serializers.py:1881`
  - `backend/proyecto/escuela/serializers.py:1898-1924`
  - `frontend/src/context/DataContext.jsx:351`
- **Verificación:** lectura directa de permiso, queryset y serializer; el frontend descarga `/api/alumnos/` al iniciar.
- **Corrección sugerida:** agregar rama `elif 'alumno' in roles` en `AlumnoViewSet.get_queryset()` filtrando por `id_usuario=request.user` (o el propio `Alumno` del usuario). Alternativamente, restringir el permiso de lectura por rol.
- **Criterio de aceptación:** un alumno solo recibe su propio registro en `/api/alumnos/`; un intento de filtrar por otro `id_curso`/`dni` no amplía el resultado.

## AL-02 — PDFs de Materias Adeudadas con origen equivocado

- **Síntoma:** los botones “Descargar PDF” de intensificaciones y previas abren una ruta rota, HTML del SPA o 404.
- **Causa:** el serializer reemplaza `archivo_pdf` por `media_url(...)`, que devuelve `/api/media/...?exp=...&sig=...`. El componente usa ese valor directamente en `href`. Como el frontend tiene `base: '/misecundaria7/'` y no hay proxy para `/api`, el navegador resuelve la URL contra Vercel en vez de contra la API.
- **Ubicación:**
  - `backend/proyecto/escuela/serializers.py:3499-3502`
  - `backend/proyecto/escuela/storage.py:39-44`
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:233`
  - `frontend/src/components/Shared/PanelMateriasAdeudadas.jsx:289`
  - `frontend/src/utils/medios.js`
  - `frontend/vite.config.js:4-11`
- **Verificación:** `href={act.archivo_pdf}` crudo en ambos bloques; `buildMediaUrl()` existe pero no se usa acá.
- **Corrección sugerida:** construir el `href` con `buildMediaUrl(act.archivo_pdf)` y revisar los demás consumidores de URLs firmadas.
- **Criterio de aceptación:** ambos botones descargan/abren el PDF contra `https://api.secundaria7.dpdns.org/api/media/...`.

## AL-03 — Notificaciones de actividades llevan a la vista incorrecta

- **Síntoma:** al hacer clic en “Ver” de una notificación de nueva actividad, se abre Materias Adeudadas en vez de Actividades.
- **Causa:** el backend emite `destino: 'actividades'` para actividades docentes y de materias adeudadas, pero el mapa del rol alumno lo transforma en `'materias-adeudadas'`. Además, el dashboard recibe `actividadId` en `navIntent.params` pero no lo usa.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:7917`
  - `backend/proyecto/escuela/views.py:7941`
  - `frontend/src/utils/navDestinos.js:22`
  - `frontend/src/components/Estudiante/EstudianteDashboard.jsx:42-47`
  - `frontend/src/components/Estudiante/EstudianteDashboard.jsx:291-295`
- **Verificación:** existe la vista `actividades` con `<ActividadesView userRole="alumno" />`, por lo que el destino correcto ya está implementado.
- **Corrección sugerida:** mapear `actividades -> actividades` y, si se quiere resaltar la actividad, propagar `actividadId` a `ActividadesView`.
- **Criterio de aceptación:** cualquier notificación de actividad abre la pestaña Actividades del estudiante.

## AL-04 — Comunicados viejos aparecen como vigentes

- **Síntoma:** se muestran comunicados de años lectivos anteriores aunque tengan alcance por ciclo.
- **Causa:** `comunicadoEstaVigente()` espera que `aniosLectivos` sea una lista de objetos con `id_ciclo` y `anio`, pero `DataContext` la construye como lista de números. `Math.max(...aniosLectivos)` funciona, pero `.find((c) => c.id_ciclo === ...)` nunca empareja y cae en “ciclo no encontrado = vigente”.
- **Ubicación:**
  - `frontend/src/components/Shared/ComunicadosView.jsx:47-60`
  - `frontend/src/components/Shared/ComunicadosView.jsx:57`
  - `frontend/src/components/Shared/ComunicadosView.jsx:58`
  - `frontend/src/context/DataContext.jsx:572-573`
- **Verificación:** contraste directo entre la forma generada en `DataContext` y la consumida en `ComunicadosView`.
- **Corrección sugerida:** usar los ciclos completos (`ciclosLectivos`) para la búsqueda por `id_ciclo`, y el año numérico solo para comparar vigencia; o normalizar `aniosLectivos` a objetos.
- **Criterio de aceptación:** un comunicado con alcance a un ciclo anterior quede oculto para el alumno.

## AL-05 — URLs firmadas expiran y quedan cacheadas

- **Síntoma:** después de unos minutos, los archivos/PDF dejan de abrir y salta `403 Enlace inválido o expirado`.
- **Causa:** `media_url()` firma con `expires_in=300` (5 minutos). Los componentes guardan la URL devuelta en estado local y la reutilizan.
- **Ubicación:**
  - `backend/proyecto/escuela/storage.py:39-44`
  - `backend/proyecto/escuela/storage.py:47-50`
  - `backend/proyecto/escuela/media_views.py`
- **Verificación:** firma HMAC con `exp` calculado en `media_url` y validado en `verificar_firma`.
- **Corrección sugerida:** regenerar la URL al hacer clic (llamada liviana al backend) o extender el TTL con un valor razonable para la sesión.
- **Criterio de aceptación:** un archivo abierto desde una pantalla que quedó quieta 10 minutos siga descargándose.

## AL-06 — RITE con año calendario en vez de ciclo lectivo

- **Síntoma:** el encabezado del RITE puede mostrar un año distinto al ciclo lectivo seleccionado (por ejemplo, en enero/febrero).
- **Causa:** `anioLectivo` se calcula con `new Date().getFullYear()`.
- **Ubicación:** `frontend/src/components/Estudiante/EstudianteDashboard.jsx:140`
- **Verificación:** lectura directa del armado de `riteHTML`.
- **Corrección sugerida:** tomar el ciclo vigente de `ciclosLectivos`/`aniosLectivos` del `DataContext`.
- **Criterio de aceptación:** el RITE muestra el mismo año lectivo que los selectores globales.

## AL-07 — Recursadas: curso en la columna de año

- **Síntoma:** en el panel de recursadas, “Curso en recursada” y “Año Lectivo” muestran datos mal etiquetados.
- **Causa:** el frontend lee `r.curso`/`r.curso_nombre` y `r.ciclo_anio`; el serializer del boletín devuelve `materia` y `anio`, donde `anio` es `id_curso_origen.nombre_curso`.
- **Ubicación:**
  - `frontend/src/components/Estudiante/PanelEstudiante.jsx:131-138`
  - `backend/proyecto/escuela/views.py:8216-8228`
- **Verificación:** contraste directo entre el objeto entregado y las claves consumidas.
- **Corrección sugerida:** alinear el serializer y el componente: `materia` en la columna materia, `anio`/curso con etiqueta correcta y un campo explícito para el ciclo lectivo si hace falta.
- **Criterio de aceptación:** la tabla muestra materia, curso y año lectivo con etiquetas coherentes.

## AL-08 — Horarios del alumno: 403 silencioso por adelantos de horas

- **Síntoma:** la vista de horarios del estudiante puede quedar incompleta o sin adelantos, sin mensaje visible.
- **Causa:** `VistaHorarios` llama a `getAdelantosHoras()` junto con horarios y suplencias. `PuedeGestionarAdelantos` solo habilita admin/director/jefe/preceptor, por lo que un alumno recibe 403; el `.catch(() => [])` lo esconde.
- **Ubicación:**
  - `frontend/src/components/Estudiante/EstudianteDashboard.jsx:208`
  - `frontend/src/components/Administracion/VistaHorarios.jsx:374-380`
  - `backend/proyecto/escuela/permissions.py:284-299`
- **Verificación:** import y render de `VistaHorarios` en el dashboard; permiso y llamada confirmados.
- **Corrección sugerida:** permitir lectura de adelantos al alumno (alcance de su curso) o saltear esa llamada cuando `userRole === 'alumno'`.
- **Criterio de aceptación:** la vista de horarios del alumno carga sin 403 y muestra solo lo que debe ver.

## AL-09 — `?alumno=` se ignora en intensificaciones

- **Síntoma:** al filtrar intensificaciones por un alumno concreto, el resultado no cambia. Afecta principalmente a familia multihijo, pero se detectó al auditar notificaciones del estudiante.
- **Causa:** `IntensificacionAcademicaViewSet.get_queryset()` solo usa `alumnos_permitidos(request)`; esa función no lee `query_params['alumno']`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:6592-6597`
  - `backend/proyecto/escuela/permissions.py:101-123`
- **Verificación:** lectura de ambas funciones; no hay lectura del parámetro `alumno`.
- **Corrección sugerida:** si el parámetro viene en la request, validar que pertenezca a `alumnos_permitidos()` y filtrar por él.
- **Criterio de aceptación:** `?alumno=<id>` devuelve solo las intensificaciones de ese alumno cuando el usuario tiene permiso sobre él.

## Orden en que se aplicaron las correcciones

1. `AL-01` — exposición de datos.
2. `AL-02`, `AL-05` — URLs de archivos.
3. `AL-03`, `AL-04` — navegación y vigencia visibles por el alumno.
4. `AL-06`, `AL-07`, `AL-08`, `AL-09` — consistencia de datos y permisos.

## Revisado sin hallazgos

Perfil del estudiante, calificaciones/RITE principal, asistencias y notificaciones en sí mismas no mostraron contratos rotos en esta pasada, salvo los destinos descritos en `AL-03`.
