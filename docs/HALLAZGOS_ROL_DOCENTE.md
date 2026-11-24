# Hallazgos del rol Docente

Fecha: 2026-11-24  
Estado general: **corregido**.  
Alcance: auditoría de código del panel Docente (perfil, calificaciones, asistencias, actas, diagnósticos, comunicados, libro de temas y planificación) y de los endpoints/permisos que consume. Se corrigieron los 12 hallazgos; queda pendiente la validación funcional en navegador.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto o error de contrato no crítico. Los ítems marcados como compartidos también aparecen en `docs/HALLAZGOS_ROL_ALUMNO.md` o `docs/HALLAZGOS_ROL_FAMILIA.md`.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| DOC-01 | P0 | `GET /api/docentes/` devuelve todos los docentes a un usuario docente. |
| DOC-02 | P0 | Las suplencias habilitan escritura en unas capas y no en otras. |
| DOC-03 | P0 | Escrituras de notas/asistencias/intensificaciones no validan que el alumno pertenezca al curso-materia. |
| DOC-04 | P1 | `/api/cursos/` y `/api/curso-materia/` no acotan su queryset al docente. |
| DOC-05 | P1 | Guardar asistencias rompe con `ReferenceError: cargarAsistencias is not defined`. |
| DOC-06 | P1 | “Diagnósticos grupales” abre la vista equivocada y `PanelInfo` queda inalcanzable. |
| DOC-07 | P1 | La vista de diagnósticos ignora suplencias y comparaciones de ids por tipo. |
| DOC-08 | P1 | Las notificaciones de actas llevan a “Actas”, pero no abren el `actaId`. |
| DOC-09 | P1 | Ids no numéricos en acciones docentes generan 500 en vez de 400. |
| DOC-10 | P2 | Comunicados del docente: vigencia y alcance por suplencia incorrectos (compartido). |
| DOC-11 | P2 | `AvisoDatosMaestros` llama un hook dentro de `try/catch`. |
| DOC-12 | P2 | `filterset_fields` declarado pero Django Filter no está configurado (global). |

## DOC-01 — Exposición masiva de datos de docentes

- **Síntoma:** un usuario con rol `docente` puede listar todos los docentes, no solo su propia ficha.
- **Causa:** `PuedeGestionarPersonas` usa `_puede_escribir()`, que permite lectura a cualquier autenticado. `DocenteViewSet.get_queryset()` tiene ramas para roles amplios, preceptor, alumno y familia, pero no para `docente`.
- **Datos expuestos:** nombre, apellido, DNI, correo, teléfono, usuario y metadatos/URL de DDJJ. La contraseña **no** se expone: es `write_only`.
- **Ubicación:**
  - `backend/proyecto/escuela/permissions.py:179-185`
  - `backend/proyecto/escuela/permissions.py:200-211`
  - `backend/proyecto/escuela/views.py:2042-2065`
  - `backend/proyecto/escuela/serializers.py:1600-1661`
  - `frontend/src/context/DataContext.jsx:351`
- **Verificación:** lectura directa del permiso, del queryset y del serializer; el frontend descarga `/api/docentes/` al iniciar.
- **Corrección sugerida:** agregar rama `elif 'docente' in roles` en `DocenteViewSet.get_queryset()` devolviendo solo el docente vinculado a `request.user` (o ampliarlo a docentes de sus cursos si el negocio lo requiere).
- **Corrección aplicada:** se agregó `_es_docente_operativo()` y la rama correspondiente en `DocenteViewSet.get_queryset()`: el docente solo recibe su propio perfil, sin afectar roles amplios ni preceptores operativos.
- **Criterio de aceptación:** un docente solo recibe su propio registro en `/api/docentes/`; un intento de filtrar por otro `id_docente`/`dni` no amplía el resultado.

## DOC-02 — Suplencias con permisos incoherentes

- **Síntoma:** un docente suplente ve habilitadas acciones de escritura en la UI, pero varios endpoints devuelven 403 o listados vacíos; el titular ve datos que ya no puede editar.
- **Causa:** `_materias_docente_ids()` y `_verificar_docente_activo_materia()` tratan al suplente como docente activo, pero `alumnos_permitidos()` sólo consulta `CursoMateria.id_docente`. Encima, varios componentes filtran con `cm.id_docente === miDocente.id` en vez de usar el mapa de suplencias.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:1321-1348`
  - `backend/proyecto/escuela/views.py:1351-1379`
  - `backend/proyecto/escuela/permissions.py:101-123`
  - Consumidores de `alumnos_permitidos()`: `backend/proyecto/escuela/views.py:3541`, `6398`, `6594`, `6666`, `6972`, `7027`
  - `frontend/src/components/Shared/DiagnosticosView.jsx:68-75`
  - `frontend/src/components/Shared/ComunicadosView.jsx:115-146`
  - `frontend/src/components/Profesores/PanelProfesores.jsx:141-147`
- **Verificación:** lectura directa de los tres helpers y contraste con los consumidores.
- **Corrección sugerida:** unificar el alcance en una sola función (por ejemplo, `materias_docente_ids(request)`) y usarla tanto para `alumnos_permitidos()` como para los filtros del frontend; el frontend debe consumir `puedeEditar`/`esSuplente` en vez de comparar titularidad.
- **Corrección aplicada:** `materias_docente_ids_para()` vive en `permissions.py` y es la única fuente de alcance; `_materias_docente_ids()` de `views.py` delega en ella, y `alumnos_permitidos()`, el scope de materias adeudadas/historial y los filtros de `DiagnosticosView`/`ComunicadosView` consumen las asignaciones derivadas del panel (titularidad + suplencias vigentes) con comparación por `String()`.
- **Criterio de aceptación:** durante una suplencia activa, el suplente puede ver y editar exactamente las mismas materias/alumnos que el titular, y el titular queda en modo solo lectura sin 403 inesperados.

## DOC-03 — Escrituras sin validar alumno contra curso-materia

- **Síntoma:** un docente podría cargar notas, asistencias o intensificaciones de un alumno de otro curso enviando un `id_alumno` ajeno junto con un `id_curso_materia` propio.
- **Causa:** la verificación fina se hace sobre el curso-materia (`_verificar_docente_activo_materia`), pero los serializers aceptan `id_alumno` sin comprobar que pertenezca a `id_curso.id_curso`. En intensificaciones, `_resolver_o_crear_historial()` llega a crear un `HistorialAcademico` con alumno y curso arbitrarios.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:3394-3419` (carga batch de calificaciones)
  - `backend/proyecto/escuela/views.py:3447-3467` (`perform_create` de calificaciones)
  - `backend/proyecto/escuela/serializers.py:2622-2656` (`CalificacionSerializer.validate`)
  - `backend/proyecto/escuela/views.py:4117-4229` (`AsistenciaViewSet.create`)
  - `backend/proyecto/escuela/views.py:6563-6584` (`_resolver_o_crear_historial`)
  - `backend/proyecto/escuela/views.py:6610-6636` (`IntensificacionAcademicaViewSet.create`)
- **Verificación:** lectura directa de los bloques; el frontend envía `id_alumno` desde la fila seleccionada, pero el backend no validaba la relación.
- **Corrección sugerida:** en los tres flujos, resolver el alumno y verificar `id_alumno.id_curso_id == cm.id_curso_id` antes de `serializer.save()` / `get_or_create()`; responder `400` con mensaje explícito si no coincide.
- **Corrección aplicada:** `alumno_pertenece_a_curso_materia()` en `utils.py` es la validación compartida. La usan `CalificacionSerializer.validate()`, `AsistenciaSerializer.validate()`, `_resolver_o_crear_historial()` y el alta de intensificaciones con `id_historial` directo, mediante `_validar_alumno_en_curso_materia()`.
- **Criterio de aceptación:** cualquier request con `id_alumno` de otro curso es rechazado, incluso si el `id_curso_materia` pertenece al docente autenticado.

## DOC-04 — Cursos y curso-materia sin scope para docente

- **Síntoma:** el docente recibe en la API el listado completo de cursos y asignaciones; el panel sólo filtra localmente con `String(cm.id_curso) === cursoId` y `materia_nombre`.
- **Causa:** `CursoViewSet.get_queryset()` y `CursoMateriaViewSet.get_queryset()` tienen ramas para roles amplios, preceptor, alumno y familia, pero no para `docente`. El permiso de escritura de curso-materia sí está restringido a admin/director/preceptor, pero la lectura queda abierta.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:2771-2803` (`CursoViewSet`)
  - `backend/proyecto/escuela/views.py:2898-2930` (`CursoMateriaViewSet`)
  - `backend/proyecto/escuela/permissions.py:258-271`
  - `frontend/src/components/Profesores/PanelProfesores.jsx:141-147`
- **Verificación:** lectura directa de ambos querysets; no había rama `docente` en el código original.
- **Corrección sugerida:** agregar rama `docente` usando `_materias_docente_ids(docente)` para curso-materia y los `id_curso` derivados para cursos. Mantener el fix de preceptors operativos existente.
- **Corrección aplicada:** ambos viewsets ahora acotan su queryset con `_es_docente_operativo()` + `_materias_docente_ids()`, respetando titularidad y suplencias vigentes y sin alterar las ramas de preceptor/alumno/familia.
- **Criterio de aceptación:** una llamada directa a `/api/cursos/` o `/api/curso-materia/` con token de docente devuelve sólo sus cursos/materias (titularidad + suplencias vigentes).

## DOC-05 — `cargarAsistencias` fuera de alcance al guardar

- **Síntoma:** después de guardar asistencia, el toast de éxito aparece pero la tabla no se refresca y la consola marca `ReferenceError: cargarAsistencias is not defined`.
- **Causa:** `cargarAsistencias` se declara dentro del `useEffect` de carga y se invoca desde `handleGuardar`, fuera de ese ámbito.
- **Ubicación:**
  - `frontend/src/components/Profesores/PanelAsistencia.jsx:97-138`
  - `frontend/src/components/Profesores/PanelAsistencia.jsx:206-214`
- **Verificación:** lectura directa de la declaración local y del llamado en el handler.
- **Corrección sugerida:** extraer `cargarAsistencias` a un `useCallback` del componente (con `estudiantesCurso`, `cursoMateriaId` y `fechaSeleccionada` en dependencias) y usarlo tanto en el efecto como después de guardar.
- **Corrección aplicada:** `cargarAsistencias` ahora es un `useCallback` con cancelación por señal; el efecto inicial y `handleGuardar` invocan la misma función.
- **Criterio de aceptación:** guardar asistencia actualiza la tabla sin errores en consola.

## DOC-06 — “Diagnósticos grupales” abre la vista incorrecta

- **Síntoma:** al hacer clic en “Diagnósticos grupales” se abre el listado global `DiagnosticosView`, no el formulario de información/diagnóstico del curso.
- **Causa:** el ítem del menú emitía `info`, pero `PanelProfesores` evaluaba ese valor primero y renderizaba `DiagnosticosView` en la rama global; el bloque que renderiza `PanelInfo` quedaba debajo y era inalcanzable.
- **Ubicación:**
  - `frontend/src/components/Profesores/sidebarMenu.js:30`
  - `frontend/src/components/Profesores/PanelProfesores.jsx:197-204`
  - `frontend/src/components/Profesores/PanelProfesores.jsx:236-244`
  - `frontend/src/components/Profesores/PanelInfo.jsx:8-58`
- **Verificación:** lectura directa del orden de las ramas condicionales.
- **Corrección sugerida:** sacar `info` de la rama global y dejar que el bloque con `cursoId && materiaSeleccionada && cursoMateriaActivo` renderice `PanelInfo`; si se quiere conservar `DiagnosticosView`, darle un id de menú propio.
- **Corrección aplicada:** el menú emite `diagnosticos` para `PanelInfo` y `diagnosticos-historial` para `DiagnosticosView`. La rama global conflictiva se eliminó y `PanelInfo` recibe `puedeEditar` desde `cursosEditables`.
- **Criterio de aceptación:** el menú “Diagnósticos grupales” abre `PanelInfo` para el curso/materia seleccionados y respeta el aviso de solo lectura por suplencia.

## DOC-07 — Diagnósticos docentes ignoran suplencias

- **Síntoma:** con una suplencia activa, el suplente no ve los diagnósticos del curso aunque el panel general lo habilite; el titular sí los ve mientras debería estar en solo lectura.
- **Causa:** `DiagnosticosView` calculaba `misAsignaciones` con `cm.id_docente === miDocente.id`, sin consultar `mapSuplencias` ni `cursosEditables`, que sí vienen desde `PanelProfesores`.
- **Ubicación:**
  - `frontend/src/components/Shared/DiagnosticosView.jsx:68-75`
  - `frontend/src/components/Shared/DiagnosticosView.jsx:78-79`
  - `frontend/src/components/Profesores/PanelProfesores.jsx:199-203`
- **Verificación:** lectura directa del caso `docente` y comparación con `misAsignaciones` del panel.
- **Corrección sugerida:** reutilizar `cursosEditables`/mapa de suplencias para derivar `misCursos`, y bloquear la creación/edición cuando `puedeEditar` sea falso.
- **Corrección aplicada:** `PanelProfesores` pasa `misAsignaciones` a `DiagnosticosView`; los cursos visibles y el filtro por curso usan `String()` sobre ese conjunto, y `puedeCrear`/`cursoEsEditable` respetan `cursosEditables` (incluido el caso de conjunto vacío).
- **Criterio de aceptación:** diagnósticos visibles para el docente activo real de cada curso; formulario deshabilitado para el titular durante la suplencia.

## DOC-08 — Notificaciones de actas no abren el acta

- **Síntoma:** al hacer clic en una notificación de nueva acta se abre la pestaña “Actas”, pero no se resalta ni se abre el acta indicada.
- **Causa:** el backend manda `navIntent.params.actaId`, `PanelProfesores` sólo traducía el `destino` a sección, y `ActasDocente` no consumía `navIntent` ni `actaId`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:7335-7340`
  - `backend/proyecto/escuela/views.py:7644-7649`
  - `frontend/src/components/Profesores/PanelProfesores.jsx:50-55`
  - `frontend/src/components/Profesores/ActasDocente.jsx:1-24` (no importaba `navIntent`)
  - Contraste: `frontend/src/context/DataContext.jsx:1116-1119`
- **Verificación:** búsqueda de `navIntent`/`actaId` en `ActasDocente`; no había consumo del parámetro.
- **Corrección sugerida:** propagar `navIntent.params.actaId` a `ActasDocente` y abrir el modal/detalle correspondiente con un guard por `timestamp` para no reaplicar la navegación.
- **Corrección aplicada:** `PanelProfesores` propaga `navIntent`; `ActasDocente` resalta la fila, fuerza las secciones visibles y abre el modal de edición cuando el acta pertenece a estudiante o curso. El guard por `timestamp` evita reaplicar la navegación.
- **Criterio de aceptación:** la notificación de acta abre el acta exacta y no se reaplica al refrescar notificaciones.

## DOC-09 — Ids no numéricos generan 500 en acciones docentes

- **Síntoma:** requests con `curso_materia=abc` (o valores no numéricos en acciones vinculadas) devuelven error interno en vez de `400`.
- **Causa:** los valores de query/body se pasaban directo a filtros ORM o a helpers que hacen `filter(...=cm_id)` / `get(pk=cm_id)`. Django lanza `ValueError` antes de cualquier validación.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:4117` (`id_curso_materia` del body en asistencias)
  - `backend/proyecto/escuela/views.py:4145` (`carga_de_item(cm_id, ...)`)
  - `backend/proyecto/escuela/views.py:4176` (`CursoMateria.objects.get(id_curso_materia=cm_id)`)
  - `backend/proyecto/escuela/views.py:5515` (`obtener_contexto_docente_para_clase(cm_id, ...)`)
  - Consumidores frontend: `frontend/src/components/Profesores/PanelAsistencia.jsx:47`, `frontend/src/components/Profesores/PanelLibroTemas.jsx:5-14`
- **Verificación:** lectura directa de los puntos donde el valor sin convertir entra en ORM.
- **Corrección sugerida:** validar/convertir con `int()` dentro de `try/except (TypeError, ValueError)` al inicio de cada action y responder `400 {'error': 'id_curso_materia inválido'}`.
- **Corrección aplicada:** `AsistenciaViewSet.create()` valida `id_curso_materia`, el batch de calificaciones valida `id_calificacion`, `obtener_contexto_docente_para_clase()` normaliza `cm_id`, y el alta de intensificaciones valida `id_historial` antes de consultar ORM.
- **Criterio de aceptación:** ningún id malformado produce 500; siempre hay 400 con mensaje.

## DOC-10 — Comunicados: vigencia y alcance por suplencia (compartido)

- **Síntoma:** comunicados de ciclos anteriores siguen apareciendo como vigentes; durante una suplencia el suplente no ve comunicados de sus materias.
- **Causa:** `comunicadoEstaVigente()` buscaba `id_ciclo` dentro de `aniosLectivos`, que son números, por lo que el `find` fallaba y caía en “ciclo no encontrado = vigente”. Además, el caso `docente` filtraba `cursoMateria` por `id_docente === miDocente.id`.
- **Ubicación:**
  - `frontend/src/components/Shared/ComunicadosView.jsx:47-60`
  - `frontend/src/components/Shared/ComunicadosView.jsx:115-146`
  - `frontend/src/context/DataContext.jsx:572-573`
  - `frontend/src/context/DataContext.jsx:751-777`
  - Referencias: `AL-04`, `FAM-07`, `DOC-02`
- **Verificación:** mismo defecto reportado en los MD de Alumno y Familia, más el filtro de titularidad exclusiva en el caso docente.
- **Corrección sugerida:** usar `ciclosLectivos` para resolver `id_ciclo -> anio` y derivar las asignaciones del docente con el mapa de suplencias.
- **Corrección aplicada:** `comunicadoEstaVigente()` usa `ciclosLectivos` (fix compartido con Alumno/Familia) y ahora descarta `estado === false`; el caso docente usa `misAsignaciones` del panel, por lo que incluye suplencias, compara ids por `String()` y no depende de titularidad estricta.
- **Criterio de aceptación:** comunicados viejos ocultos y suplente con el mismo alcance de comunicados que el titular.

## DOC-11 — Hook de `useAuth` dentro de `try/catch`

- **Síntoma:** posible fallo de lint/reglas de React y comportamiento dependiente de que el componente esté o no dentro de `AuthProvider`.
- **Causa:** `AvisoDatosMaestros` llamaba `useAuth()` dentro de un bloque `try`, lo que viola la regla de hooks de nivel superior. El fallback existía para tests, pero el patrón era incorrecto.
- **Ubicación:** `frontend/src/components/Shared/AvisoDatosMaestros.jsx:28-43`
- **Verificación:** lectura directa del componente.
- **Corrección sugerida:** mover `const { user } = useAuth() || {}` al nivel superior del componente y eliminar el `try/catch`.
- **Corrección aplicada:** `AuthContext` exporta `useAuthOpcional()` (usa `useContext` sin lanzar) y `AvisoDatosMaestros` lo invoca de forma incondicional al nivel superior, sin `try/catch`.
- **Criterio de aceptación:** componente sin errores de reglas de hooks y con el mismo comportamiento dentro/fuera del provider.

## DOC-12 — `filterset_fields` declarado pero inactivo (global)

- **Síntoma:** filtros como `?id_curso=` o `?dni=` en `/api/alumnos/` parecían no hacer nada.
- **Causa:** `AlumnoViewSet` declara `filterset_fields`, pero el proyecto no configura `DjangoFilterBackend` ni `DEFAULT_FILTER_BACKENDS`, y no hay ningún `FilterSet` definido. El atributo es ignorado por DRF.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:1947`
  - `backend/proyecto/settings.py:235-242`
- **Verificación:** búsqueda de `DjangoFilterBackend`/`FilterSet` en todo el backend; no hay configuración.
- **Corrección sugerida:** implementar el filtrado manualmente en `get_queryset()` (leyendo `request.query_params`) o instalar/configurar django-filter. Elegir una sola forma para no duplicar scopes por rol.
- **Corrección aplicada:** se eligió filtrado manual en `AlumnoViewSet.get_queryset()` para `id_curso` y `dni`, aplicado después del scope por rol. No se agregó `DjangoFilterBackend` para no duplicar scopes.
- **Criterio de aceptación:** los filtros declarados realmente acotan resultados y respetan el scope del docente.

## Orden sugerido de corrección

1. `DOC-01`, `DOC-02`, `DOC-03`, `DOC-04` — scope y permisos en backend.
2. `DOC-05`, `DOC-06`, `DOC-07`, `DOC-08` — flujos visibles del panel docente.
3. `DOC-09` — validación de ids y errores 400.
4. `DOC-10`, `DOC-11`, `DOC-12` — consistencia y contratos compartidos.

## Revisado sin hallazgos

- Edición de planificaciones: `PanelPlanif.jsx:142-160` ya envía `contenido`/`objetivos`/`salidas`/`fundamentacion`, campos que existen en `Planificacion` (`models.py:716-733`); no envía `descripcion`.
- `navDestinos.js` para docente: `actas -> actas` y `materias_adeudadas -> actividades` son consistentes con las ramas existentes en `PanelProfesores.jsx:197-282`.
- Carga de notas y asistencias: los serializers sí reciben `id_alumno` del request; ahora además validan la pertenencia al curso de la materia.
- URLs firmadas al editar actividades de materias adeudadas: `PanelMateriasAdeudadasDocente.jsx` reenvía la URL y `storage.py:18-31` la normaliza; no requiere fix.
- Hook `navIntent` de docente no se reaplica solo: el efecto depende sólo de `[navIntent]` (`PanelProfesores.jsx:50-55`).
- Contadores de `PanelDocente.jsx:38-55`: ids numéricos y comparaciones consistentes en el shape actual de `DataContext`.
