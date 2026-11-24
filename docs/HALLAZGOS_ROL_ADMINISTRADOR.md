# Hallazgos del rol Administrador

Fecha: 2026-11-24  
Estado general: **corregido**.  
Alcance: auditoría de código del panel Administrador (perfil, administración de personas, estructura académica, horarios, asistencias, RITE, actas, comunicados, notificaciones y navegación) y de los endpoints/permisos que consume. Queda pendiente la validación funcional en navegador.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto o error de contrato no crítico. Los ítems marcados como compartidos también aparecen en otros MD de rol. Los hallazgos `PRE-11`, `PRE-12` y `JEFE-11` del MD de Preceptor/Jefe también aplican a este rol y no se repiten acá.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| ADM-01 | P1 | Un administrador puede modificar/borrar perfiles de Directivo/Administrador por API directa. |
| ADM-02 | P1 | El administrador recibe notificaciones E4/E21 de actas que la guía excluye. |
| ADM-03 | P1 | El administrador no puede deshabilitar/habilitar usuarios por `/api/usuarios/`. |
| ADM-04 | P2 | Cambiar el estado desde los perfiles no emite E14 “Cuenta habilitada/deshabilitada”. |
| ADM-05 | P1 | Las notificaciones E8/E9 no muestran “Ver” para el administrador. |
| ADM-06 | P1 | El botón “Ver” ignora ids/fechas de la notificación y abre la vista con contexto genérico. |
| ADM-07 | P1 | RITE está fijo en solo lectura aunque admin/director pueden escribir calificaciones. |
| ADM-08 | P1 | Asistencias está fijo en solo lectura aunque admin/director pueden cargar asistencias. |
| ADM-09 | P2 | “Ver horarios” omite siempre el Sábado. |
| ADM-10 | P2 | Creación de actas: la guía habilita al admin, el código y los requerimientos lo prohíben. |
| ADM-11 | P2 | Documentación contradictoria sobre quién puede gestionar administradores/directivos. |

## ADM-01 — Perfiles de Directivo/Administrador editables por un administrador

- **Síntoma:** un usuario con rol puro `admin` puede hacer `PATCH` o `DELETE /api/directivos/{id}/` y modificar el DNI, cargo, teléfono, usuario asociado o borrar el perfil de un director o de otro administrador. La UI oculta “Administradores” para el rol admin, pero el endpoint queda expuesto.
- **Causa:** `DirectivoViewSet` usa `IsAdminOrDirectorForWrite`, que habilita escritura a `admin` y `director`, y `DirectivoSerializer.Meta.fields = '__all__'`. No hay restricción por rol del objetivo. La guía dice explícitamente que el botón de crear/editar admins debe estar deshabilitado para el rol admin.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:2591-2596`
  - `backend/proyecto/escuela/permissions.py:126-132`
  - `backend/proyecto/escuela/serializers.py:1858-1860`
  - `frontend/src/components/Administracion/sidebarMenu.js:14`
  - Referencias: `docs/GUIA_TESTEO_MiSecundaria7.md:337`, `docs/REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md:105`
- **Verificación:** lectura directa del viewset, del permiso y del serializer. El ocultamiento del menú no bloquea llamadas API directas.
- **Corrección sugerida:** permitir que `admin` sólo lea `/api/directivos/`; restringir creación/edición/borrado a `director`. Si se quiere impedir también que un director modifique a otro director, agregar esa validación fina.
- **Criterio de aceptación:** `POST`/`PATCH`/`DELETE /api/directivos/{id}/` por un admin puro devuelve `403`; el director conserva la gestión.
- **Corrección aplicada:** `DirectivoViewSet` usa `SoloDirectorEscribeDirectivos`; el admin puro conserva sólo lectura. `UsuarioViewSet` exige director únicamente cuando el objetivo o los roles solicitados son privilegiados.

## ADM-02 — Notificaciones de actas E4/E21 enviadas al administrador

- **Síntoma:** el administrador recibe “Acta de curso” (E21) y “Acta de conducta” (E4) aunque la guía indica que **no** debe recibirlas. La guía dice que E21 va sólo a preceptores del curso + jefe, y E4 a estudiante + familia + preceptores del curso + jefe.
- **Causa:** los helpers de actas recorren `_usuarios_directivos()` para avisar a “directivos”, y esa función incluye explícitamente los roles `admin` y `director`. Como `admin` y `director` comparten `SEGMENTO_DIRECTIVO`, el administrador ve las notificaciones en su campana.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:5144-5156`
  - `backend/proyecto/escuela/views.py:7083-7093`
  - `backend/proyecto/escuela/views.py:7341-7349` (acta de curso)
  - `backend/proyecto/escuela/views.py:7681-7689` (acta de conducta)
  - `backend/proyecto/escuela/notifications.py:46-49`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:391-392`
- **Verificación:** comparación directa entre los bucles de notificación y el checklist de la guía.
- **Corrección sugerida:** no crear `_usuarios_directores()` porque seguiría notificando al director; excluir ambos roles directivos de los helpers de E4/E21 y mantener `_usuarios_directivos()` para E8/E9, que sí corresponden al administrador.
- **Criterio de aceptación:** no se crean notificaciones E4/E21 para roles `admin` ni `director`; E4 sigue yendo a estudiante + familia + preceptores + jefe, y E21 sólo a preceptores del curso + jefe.
- **Corrección aplicada:** los helpers de E4/E21 dejaron de incluir a `admin` y `director`, y E21 dejó de incluir estudiantes y familias para respetar la matriz. E8/E9 siguen usando `_usuarios_directivos()`.

## ADM-03 — Estado de usuarios bloqueado por la puerta director-only de `/api/usuarios/`

- **Síntoma:** desde la sección de administración no se puede deshabilitar/habilitar un usuario mediante `/api/usuarios/`: la API responde `403 Solo directores pueden modificar administradores`, incluso si el objetivo es un estudiante, docente o preceptor sin rol privilegiado.
- **Causa:** `UsuarioViewSet.perform_update()` exige `director` para **cualquier** actualización, sin mirar el usuario target ni los roles que se están cambiando. El mensaje también es engañoso porque no se está modificando un administrador.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:1638-1656`
  - `backend/proyecto/escuela/views.py:1608-1619` (creación con el mismo criterio)
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:369`
- **Verificación:** lectura directa del viewset. La guía de administrador incluye “Deshabilitar / habilitar un usuario” como acción del rol.
- **Corrección sugerida:** evaluar los roles del usuario destino y los roles solicitados. Permitir al admin actualizar estado de usuarios no privilegiados; exigir `director` sólo para crear/modificar cuentas con rol `admin` o `director`.
- **Criterio de aceptación:** el admin puede deshabilitar/habilitar un alumno/docente/preceptor; no puede crear ni modificar administradores/directores.
- **Corrección aplicada:** `UsuarioViewSet` resolvió los roles del objetivo y de la solicitud. El listado admin excluye `admin`/`director`, y `perform_update`/`perform_destroy` aplican el bloqueo director-only sólo a cuentas privilegiadas.

## ADM-04 — E14 no se emite al cambiar el estado desde los formularios de perfil

- **Síntoma:** cuando el administrador deshabilita/habilita un docente, preceptor, alumno o tutor desde su formulario, no se genera la notificación E14 “Cuenta deshabilitada/habilitada” para el usuario afectado.
- **Causa:** los toggles usan los endpoints de perfil (`/api/docentes/`, `/api/preceptores/`, `/api/alumnos/`, `/api/padres-tutores/`), que pasan por `PuedeGestionarPersonas` (admin permitido) pero no llaman a `notificar_estado_cuenta()`. Ese helper sólo se invoca al crear un usuario y en `UsuarioViewSet.perform_update()`, que el admin no puede usar según `ADM-03`.
- **Ubicación:**
  - `backend/proyecto/escuela/serializers.py:333-338`
  - `backend/proyecto/escuela/views.py:1629`, `:1656`
  - `backend/proyecto/escuela/views.py:7782-7791`
  - `backend/proyecto/escuela/permissions.py:200-211`
  - Frontend: `frontend/src/components/Administracion/docentes.jsx:575-577`, `frontend/src/components/Administracion/preceptores.jsx:395-408`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:369`
- **Verificación:** búsqueda global de `notificar_estado_cuenta`: no aparece en los serializers de perfil ni en los viewsets de alta/edición de personas.
- **Corrección sugerida:** centralizar la comparación `estado_anterior` vs `estado_nuevo` en un mixin usado por todos los viewsets que pueden cambiar `usuario.estado`, y emitir E14 una sola vez por transición real.
- **Criterio de aceptación:** todo cambio de estado, vía `/api/usuarios/` o vía perfil, crea exactamente una notificación E14 para el usuario afectado.
- **Corrección aplicada:** `_build_usuario_account()` compara `estado_anterior` con el estado final y llama a `notificar_estado_cuenta()` también cuando el cambio viene de un endpoint de perfil.

## ADM-05 — E8/E9 sin botón “Ver” para el administrador

- **Síntoma:** al llegar “Planificación para revisión” (E8) o “DDJJ presentada” (E9), la notificación no muestra “Ver”. El administrador tiene que buscar manualmente el docente dentro de Administración → Docentes.
- **Causa:** el backend emite `nav_destino: 'planificaciones'` y `'ddjj'`, pero `MAPA_POR_ROL.admin` no incluye esas claves. `Notificaciones.jsx` oculta el botón cuando `tieneVistaParaDestino()` devuelve falso. Sin embargo el panel sí tiene UI de verificación de planificaciones y consulta de DDJJ dentro de `docentes.jsx`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:7496-7530`
  - `backend/proyecto/escuela/views.py:7588-7607`
  - `frontend/src/utils/navDestinos.js:70-87`
  - `frontend/src/components/Notificaciones.jsx:109-118`
  - `frontend/src/components/Notificaciones.jsx:163-169`
  - `frontend/src/components/Administracion/docentes.jsx:241-253`, `:650-663`, `:771-789`
- **Verificación:** lectura directa de los emisores, del mapa de destinos admin y de la lógica de render de “Ver”. `director` se normaliza a `admin`, así que el problema aplica a ambos roles directivos.
- **Corrección sugerida:** agregar `planificaciones: 'docentes'` y `ddjj: 'docentes'` al mapa `admin`, y hacer que `AdminDashboard`/`Docentes` consuman `planificacionId`/`ddjjId` para abrir el docente correcto.
- **Criterio de aceptación:** E8/E9 muestran “Ver” y abren la pestaña de planificaciones/DDJJ del docente correspondiente.
- **Corrección aplicada:** `MAPA_POR_ROL.admin` incluye `planificaciones` y `ddjj`, y `Docentes.jsx` consume `planificacionId`/`ddjjId` para filtrar y desplegar el docente destino.

## ADM-06 — Navegación desde notificaciones ignora el registro destino

- **Síntoma:** al hacer clic en “Ver” de muchas notificaciones, el panel abre la sección correcta pero no el registro al que apunta la notificación: notas sin el alumno/curso-materia, asistencias sin la fecha, suplencias sin la suplencia, actas sin el acta, horarios sin el horario.
- **Causa:** `navegarDesdeNotificacion()` guarda `params` completos en `navIntent`, pero `AdminDashboard` sólo lee `anioLectivo`/`año`, `cursoNombre` y `cursoId`. El resto de los parámetros se descarta. Ningún componente de `Administracion` consume `navIntent`; las vistas sólo reciben `filtrosProps` con año/cursos globales.
- **Ubicación:**
  - `frontend/src/context/DataContext.jsx:1116-1119`
  - `frontend/src/components/Administracion/AdminDashboard.jsx:55-84`
  - `frontend/src/components/Administracion/AdminDashboard.jsx:145-152`
  - `frontend/src/components/Administracion/AdminDashboard.jsx:163-216`
  - Emisores de ejemplo: `backend/proyecto/escuela/views.py:7218-7224` (notas), `:7249-7255` (asistencias), `:7335-7340` (actas), `:7441-7446` (suplencias), `:7988-7994` (horarios)
- **Verificación:** búsqueda de `navIntent` en `frontend/src/components/Administracion`: el único consumidor es el dashboard y sólo usa los parámetros de curso/año.
- **Corrección sugerida:** propagar `navIntent.params` a las vistas destino o agregar un efecto por vista que seleccione el registro por id/fecha. Mantener el guard por `timestamp` para no reaplicar en refrescos.
- **Criterio de aceptación:** cada notificación con “Ver” abre el registro concreto, no sólo el módulo genérico.
- **Corrección aplicada:** `AdminDashboard` publica `navContext` para todas las vistas y resuelve curso desde `cursoMateriaId`. Notas, asistencias, docentes, suplencias, actas y horarios consumen ids/fechas con guard por `timestamp`; `PanelEstudiantes` resalta el alumno destino.

## ADM-07 — RITE de administración fijo en solo lectura

- **Síntoma:** el módulo “RITE” del administrador muestra el badge “Solo lectura”, el aviso “Vista de solo lectura” y pasa `puedeEditar={false}` a `PanelEstudiantes`. El administrador no puede cargar ni editar calificaciones desde el panel.
- **Causa:** valores hardcoded en `notas.jsx`. El backend `PuedeEscribirCalificaciones` sí incluye `admin` y `director`, y la guía de administración pide “Cargar/editar notas”.
- **Ubicación:**
  - `frontend/src/components/Administracion/notas.jsx:43-49`
  - `frontend/src/components/Administracion/notas.jsx:85-96`
  - `frontend/src/components/Profesores/PanelEstudiantes.jsx:417`, `:496-752`
  - `backend/proyecto/escuela/permissions.py:188-197`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:350`
- **Verificación:** comparación directa entre la UI, el permiso de escritura y la guía.
- **Corrección sugerida:** calcular `puedeEditar` desde el rol real (`admin`/`director`) y pasar `docenteId={null}`; conservar las validaciones finas del backend por curso-materia. Si la política es de solo lectura, actualizar permiso y documentación.
- **Criterio de aceptación:** el admin/director puede cargar y editar notas desde el panel RITE, o la política de solo lectura queda documentada de forma coherente.
- **Corrección aplicada:** `notas.jsx` deriva `puedeEditar` del rol activo (`admin`/`director`) y elimina el badge/aviso de solo lectura para esos roles.

## ADM-08 — Asistencias de administración fijas en solo lectura

- **Síntoma:** el módulo “Asistencias” muestra el badge “Solo lectura” y no expone los controles de carga masiva ni de justificación, aunque el backend habilita escritura a administradores/directores.
- **Causa:** el componente renderiza el badge fijo y los botones de acción están condicionados a un estado de solo lectura; `PuedeRegistrarAsistencias` sí incluye a `admin` y `director`. La guía pide “Cargar asistencia en bloque / por curso; marcar ausencias”.
- **Ubicación:**
  - `frontend/src/components/Administracion/asistencias.jsx:195-198`
  - `frontend/src/components/Administracion/asistencias.jsx:200-270`
  - `frontend/src/components/Administracion/asistencias.jsx:416`
  - `backend/proyecto/escuela/permissions.py:228-236`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:349`
- **Verificación:** lectura directa del componente y del permiso. El backend ya resuelve alcance por curso/materia en el viewset.
- **Corrección sugerida:** habilitar los controles de carga/justificación para `admin` y `director`, manteniendo el bloqueo por suspensión y las validaciones del viewset.
- **Criterio de aceptación:** el admin puede cargar asistencia en bloque y justificar inasistencias desde su panel.
- **Corrección aplicada:** `asistencias.jsx` habilita guardado masivo y justificación para `admin`/`director`, respetando suspensiones y usando `estadosAsistencia`, `createAsistencia` y `patchJustificar`.

## ADM-09 — “Ver horarios” del administrador omite el Sábado

- **Síntoma:** al abrir los horarios desde el panel de administración no aparece la columna “Sábado”, aunque el formulario de carga sí permite seleccionarlo y guardarlo.
- **Causa:** hay dos constantes `DIAS` distintas: `horarios.jsx` incluye `'Sábado'`, pero `VistaHorarios.jsx`, que es la vista de consulta, sólo incluye Lunes a Viernes. Los horarios del sábado se guardan pero no se muestran.
- **Ubicación:**
  - `frontend/src/components/Administracion/horarios.jsx:22`
  - `frontend/src/components/Administracion/VistaHorarios.jsx:7`
  - `frontend/src/components/Administracion/VistaHorarios.jsx:80-124`
  - `frontend/src/components/Administracion/VistaHorarios.jsx:261-281`
- **Verificación:** comparación directa de ambas constantes y del render de la grilla.
- **Corrección sugerida:** unificar en una sola constante compartida con los seis días, o decidir por política que el sábado no se usa y quitarlo también del formulario.
- **Criterio de aceptación:** todos los días configurables aparecen tanto en carga como en consulta.
- **Corrección aplicada:** `VistaHorarios.jsx` incluye `Sábado` en `DIAS`, igual que el formulario de carga.

## ADM-10 — Creación de actas: guía y código se contradicen

- **Síntoma:** la guía de administrador dice “Crear actas de curso/estudiante”, pero el panel deshabilita “Nueva acta” para admin/director y el backend excluye esos roles de `ROLES_CREAR_ACTA`. Los requerimientos tampoco listan al admin como creador.
- **Causa:** documentación desactualizada o política no definida. El código es coherente internamente: UI y backend coinciden en que admin/director sólo visualizan y gestionan actas existentes.
- **Ubicación:**
  - `docs/GUIA_TESTEO_MiSecundaria7.md:351`
  - `docs/REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md:155-156`
  - `backend/proyecto/escuela/views.py:5014-5017`
  - `frontend/src/components/Preceptores/actas.jsx:237-243`
- **Verificación:** comparación directa de los tres contratos (guía, requerimientos, código).
- **Corrección sugerida:** si la política es que admin no crea actas, quitar el ítem 14 de la guía o aclarar que aplica sólo a preceptor/docente/jefe. Si se quiere habilitar al admin, agregarlo a `ROLES_CREAR_ACTA` y al `puedeCrearActa` del frontend y actualizar los requerimientos.
- **Criterio de aceptación:** guía, requerimientos, permisos y UI describen la misma política de creación de actas.
- **Corrección aplicada:** la guía y los requerimientos ahora indican que admin/director no crean actas; sólo visualizan y gestionan las existentes.

## ADM-11 — Documentación contradictoria sobre gestión de administradores/directivos

- **Síntoma:** los requerimientos dicen que el rol admin tiene “Gestión completa: … administradores” y que los directivos son administrables por admin, pero la guía dice que el admin **no** debe crear/editar admins y que los roles `admin`/`director` los quita sólo un director. El código implementa un criterio mixto: bloquea crear usuarios con rol admin pero permite al admin editar/borrar perfiles de directivos (`ADM-01`).
- **Causa:** contrato de roles no unificado entre documentos y permisos.
- **Ubicación:**
  - `docs/REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md:25`, `:46`, `:105`, `:453`
  - `docs/GUIA_TESTEO_MiSecundaria7.md:337`, `:404`
  - `frontend/src/components/Administracion/sidebarMenu.js:14`
  - `backend/proyecto/escuela/views.py:1608-1619`, `:1646-1652`, `:1667-1675`
  - `backend/proyecto/escuela/permissions.py:31-34`, `:126-132`
- **Verificación:** lectura cruzada de documentación, sidebar y permisos.
- **Corrección sugerida:** definir una sola regla jerárquica (admin < director) y reflejarla en los cuatro lugares: requerimientos, guía, sidebar y permisos. `ADM-01` se resuelve una vez definida esa regla.
- **Criterio de aceptación:** no queda ningún documento que habilite al admin para gestionar administradores/directivos si la política es negarlo.
- **Corrección aplicada:** se unificó la jerarquía `admin < director` en permisos, `UsuarioViewSet`, `DirectivoViewSet`, sidebar, guía y requerimientos.

## Orden sugerido de corrección

1. `ADM-01`, `ADM-03`, `ADM-11` — jerarquía de roles y límites de escritura.
2. `ADM-05`, `ADM-06` — navegación y botón “Ver” de notificaciones.
3. `ADM-07`, `ADM-08` — permisos de edición reales en RITE y asistencias.
4. `ADM-02`, `ADM-04` — notificaciones E4/E21 y E14.
5. `ADM-09`, `ADM-10` — consistencia visual y documental.

## Revisado sin hallazgos

- El sidebar oculta “Administradores” para el rol admin en `sidebarMenu.js:14` y `sidebar/sidebar.js:28-35`; coincide con la guía, aunque no bloquea API directa (`ADM-01`).
- El header de administración mantiene la multiselección actual de cursos (`AdminDashboard.jsx:41-45`, `:106-110`); no se propone cambiarlo.
- `NavAplicadoRef` evita reaplicar un `navIntent` por refrescos de datos (`AdminDashboard.jsx:52-58`).
- Los destinos `ciclos_lectivos`, `modulos_horarios`, `periodos_evaluacion`, `estados_asistencia` y `tipos_acta` sí están mapeados para admin en `navDestinos.js:80-87`.
- La verificación de planificaciones y la consulta de DDJJ existen dentro de `docentes.jsx`; el problema es de destino de notificación, no de módulo faltante (`ADM-05`).
- `PuedeGestionarPersonas` habilita correctamente a admin/director para editar alumnos, docentes, preceptores y tutores (`permissions.py:200-211`).
- `PuedeGestionarActas` habilita a admin/director para editar/eliminar actas existentes; la contradicción es sólo sobre crearlas (`ADM-10`).
- No se modificaron `AdelantosHoras.jsx` ni `AsistenciasUnificada.jsx`.
