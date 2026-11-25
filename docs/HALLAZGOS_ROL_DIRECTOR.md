# Hallazgos del rol Director

Fecha: 2026-11-24  
Estado general: **corregido**.  
Alcance: auditoría de código del panel Director (perfil, administración de administradores, Personas, notificaciones, roles, estados programados, DDJJ y documentación asociada) y de los endpoints/permisos que consume. El director comparte `AdminDashboard` con el administrador; los hallazgos compartidos ya documentados en `docs/HALLAZGOS_ROL_ADMINISTRADOR.md` no se repiten salvo que el director tenga una manifestación distinta. Se corrigieron los 8 hallazgos; queda pendiente la validación funcional en navegador.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto o error de contrato no crítico. Los ítems marcados como **compartidos** aparecen también en otro MD de rol, pero acá se documentan por tener una causa o corrección diferente.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| DIR-01 | P1 | Editar un administrador quita los demás roles, incluso el rol `director` del propio director. |
| DIR-02 | P1 | El director recibe E4/E21 de actas aunque la guía dice explícitamente que no. |
| DIR-03 | P2 | “Agregar rol: administrador” muestra el nombre del rol vacío en la confirmación. |
| DIR-04 | P2 | La leyenda de acciones anuncia “Eliminar” pero la tabla no ofrece esa acción. |
| DIR-05 | P2 | Agregar el rol admin a un director existente le sobrescribe el `cargo`. |
| DIR-06 | P2 | Los cambios de estado programados no emiten E14 “Cuenta habilitada/deshabilitada”. |
| DIR-07 | P2 | La documentación promete alta de “administrador/directivo”, pero no hay flujo para crear el rol `director`. |
| DIR-08 | P2 | `mi-ddjj` permite presentar una DDJJ por otro docente y autonotificar E9 al director. |

## DIR-01 — Editar un administrador quita los roles restantes

- **Síntoma:** `<USUARIO_DIRECTOR_PRUEBA>` tiene roles `admin`, `director` y `familia` (`docs/GUIA_TESTEO_MiSecundaria7.md:18`). Si entra como Director, abre Administración → Administradores, edita un administrador —incluso a sí mismo— y guarda, el payload envía siempre `roles: ['admin']`. El serializer borra todas las filas `UsuarioRol` y deja solamente `admin`. Después de recargar, el usuario ya no tiene `director` y pierde las acciones exclusivas del rol.
- **Causa:** `administradores.jsx` fija `roles: ['admin']` tanto en alta como en edición. `UsuarioSerializer.update()` toma `roles` desde `initial_data` y reemplaza la relación completa. El toggle de estado no envía `roles`, por eso no produce este efecto.
- **Ubicación:**
  - `frontend/src/components/Administracion/administradores.jsx:291-301`
  - `frontend/src/components/Administracion/administradores.jsx:308-313`
  - `frontend/src/components/Administracion/administradores.jsx:252-258` (toggle sin `roles`)
  - `backend/proyecto/escuela/serializers.py:814-857`
  - `backend/proyecto/escuela/views.py:1637-1656`
  - `frontend/src/context/AuthContext.jsx:37-44`, `:82-94`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:18`, `:404`
- **Verificación:** lectura directa del payload, del `update()` del serializer, del `perform_update()` del viewset y del usuario de prueba de la guía.
- **Corrección sugerida:** en edición no enviar `roles` salvo que exista un control explícito para cambiarlos; si se envían, combinar con los roles actuales y validar jerarquía. Prohibir además que un director se quite su propio rol `director` por esta vía.
- **Corrección aplicada:** el formulario sólo envía `roles` en alta; `UsuarioSerializer.update()` dejó de reemplazar `UsuarioRol` y `quitar-rol` rechaza que un actor se quite su propio rol. El listado de `UsuarioViewSet` incluye `admin` y `director`, y el formulario permite elegir el rol a crear sin modificar roles al editar.
- **Criterio de aceptación:** después de editar `<USUARIO_DIRECTOR_PRUEBA>`, `GET /api/me/` sigue devolviendo `['admin','director','familia']`; las acciones exclusivas de director siguen respondiendo `200`; editar otro administrador no agrega ni quita roles no solicitados.

## DIR-02 — E4/E21 llegan al director aunque la guía lo prohíbe (compartido con ADM-02)

- **Síntoma:** al crear un acta de curso (E21) o un acta de estudiante (E4), la campana del Director muestra esas notificaciones. La guía indica que E21 va sólo a preceptores del curso + jefe y E4 a estudiante + familia + preceptores del curso + jefe, con casillas explícitas “NO debería llegarte”.
- **Causa:** los helpers de actas recorren `_usuarios_directivos()`, que incluye a los roles `admin` y `director`. La corrección propuesta en `ADM-02` (crear `_usuarios_directores()` para actas) seguiría notificando al director; por eso este hallazgo requiere una corrección distinta: excluir a ambos roles directivos de E4/E21, o cambiar la documentación antes de tocar el código.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:5139-5156`
  - `backend/proyecto/escuela/views.py:7083-7093`
  - `backend/proyecto/escuela/views.py:7316-7349`
  - `backend/proyecto/escuela/views.py:7627-7689`
  - `backend/proyecto/escuela/notifications.py:43-55`
  - Referencias: `docs/GUIA_TESTEO_MiSecundaria7.md:407`, `:425-426`, `:439`, `:454`; `docs/PLAN_NOTIFICACIONES_MiSecundaria7.md:373`
- **Verificación:** comparación directa entre los bucles de notificación, la matriz de la guía y el plan de notificaciones. El ítem 4 de la sección Director quedó alineado: E4/E21 no llegan al director.
- **Corrección sugerida:** definir una sola política. Si se respeta la guía, quitar el bucle `_usuarios_directivos()` de `_notificar_acta_curso()` y `_notificar_acta_alumno()`, o filtrar ambos roles directivos. Si se decide que director sí debe ver actas, actualizar `GUIA...:407`, `:425-426`, `:439`, `:454` y `PLAN_NOTIFICACIONES...:373` antes de modificar el emisor.
- **Corrección aplicada:** se respetó la guía: E4 y E21 ya no incluyen a roles `admin` ni `director`. E4 sigue yendo a estudiante + familia + preceptores + jefe; E21 sólo a preceptores del curso + jefe, y E8/E9 siguen usando `_usuarios_directivos()`.
- **Criterio de aceptación:** crear un acta de curso y un acta de estudiante no genera notificación para el director; E21 llega a preceptores del curso + jefe, E4 a estudiante + familia + preceptores + jefe, y E8/E9 siguen llegando al director.

## DIR-03 — Nombre de rol vacío en “Agregar rol: administrador”

- **Síntoma:** en el paso final del modal se lee “Se asignará el rol **” sin texto. En los módulos de docentes/preceptores el mismo modal sí muestra “Docente”, “Preceptor”, etc.
- **Causa:** el llamado desde `administradores.jsx` no pasa la prop `rol`, por lo que `AgregarRolModal` cae en `ROLE_CONFIG[rol] || { needAssignment: false, minSelection: 0 }`, sin `label`.
- **Ubicación:**
  - `frontend/src/components/Administracion/administradores.jsx:627-635`
  - `frontend/src/components/Shared/AgregarRolModal.jsx:87`
  - `frontend/src/components/Shared/AgregarRolModal.jsx:652`
  - Contraste: `frontend/src/components/Administracion/docentes.jsx:1040-1048`
- **Verificación:** lectura directa del componente compartido y búsqueda de todos los llamados a `<AgregarRolModal />`.
- **Corrección sugerida:** agregar `rol="admin"` en el llamado de `administradores.jsx`.
- **Corrección aplicada:** `administradores.jsx` pasa `rol={rolParaAgregar}` y `AgregarRolModal` incorporó la configuración `director`, además de un `label` por defecto para no mostrar un nombre vacío.
- **Criterio de aceptación:** el paso 3 muestra “Se asignará el rol **Administrador** a esta persona.”

## DIR-04 — Leyenda con acción “Eliminar” inexistente

- **Síntoma:** la tabla “Administradores” muestra en la leyenda el ícono y texto “Eliminar”, pero cada fila sólo ofrece Editar y Deshabilitar/Habilitar.
- **Causa:** desincronización entre `AccionesLeyenda` y `AccionesCelda`. La guía del director sólo pide crear y editar administradores, no borrarlos.
- **Ubicación:**
  - `frontend/src/components/Administracion/administradores.jsx:566`
  - `frontend/src/components/Administracion/administradores.jsx:608-615`
  - `frontend/src/components/Shared/AccionesLeyenda.jsx:1-11`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:404`
- **Verificación:** lectura directa de la leyenda y de las acciones renderizadas por fila.
- **Corrección sugerida:** quitar `'eliminar'` de la leyenda de este módulo. Alternativamente, implementar la acción con confirmación y refresco, pero eso implicaría habilitar borrado no pedido.
- **Corrección aplicada:** se quitó `'eliminar'` de `AccionesLeyenda`; la leyenda ahora coincide con Editar y Deshabilitar/Habilitar.
- **Criterio de aceptación:** la leyenda coincide exactamente con los botones disponibles en cada fila.

## DIR-05 — Asignar rol admin sobrescribe el cargo de un director existente

- **Síntoma:** al usar “Agregar rol: administrador” sobre un usuario que ya es director pero no admin (por ejemplo `<USUARIO_VICEDIRECTOR1_PRUEBA>`, cargo “Vicedirectora”), su perfil `Directivo` queda con `cargo = "Administrador"`. El perfil muestra el valor nuevo en vez del original.
- **Causa:** `/usuarios/sin-rol` no devuelve `cargo`, el frontend fija `cargo: 'Administrador'` en el payload y `UsuarioSerializer.create()` reutiliza el perfil `Directivo` existente y sobrescribe ese campo.
- **Ubicación:**
  - `frontend/src/components/Administracion/administradores.jsx:333-344`
  - `backend/proyecto/escuela/views.py:1920-1932`
  - `backend/proyecto/escuela/serializers.py:760-775`
  - `frontend/src/components/Administracion/PanelAdmin.jsx:74-79`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:404`
- **Verificación:** lectura directa del flujo. La no devolución de `cargo` en el listado `sin-rol` impide al frontend preservarlo.
- **Corrección sugerida:** no enviar `cargo` cuando se reutilice un usuario con perfil `Directivo` existente, o devolver `cargo` en `/usuarios/sin-rol` y preservarlo. Si el cambio es intencional, el modal debe advertirlo explícitamente.
- **Corrección aplicada:** `handleAgregarRol` ya no envía `cargo`, por lo que `UsuarioSerializer.create()` conserva el cargo del perfil `Directivo` reutilizado. En alta nueva, el cargo por defecto se deriva del rol elegido (`Administrador`/`Director`).
- **Criterio de aceptación:** agregar el rol admin a un director conserva su cargo previo, o el modal informa claramente que se cambiará a “Administrador”.

## DIR-06 — Cambios de estado programados no emiten E14 (compartido con ADM-04)

- **Síntoma:** el director carga “Fecha de deshabilitación programada” o “Fecha de habilitación programada” en Administradores. Cuando llega la fecha, la cuenta cambia de estado en la próxima request de escritura, pero no se genera “Cuenta deshabilitada/habilitada” (E14). El toggle manual sí emite E14.
- **Causa:** `aplicar_programaciones_usuario()` hace `usuario.save(update_fields=...)` directo desde el middleware y no importa ni llama a `notificar_estado_cuenta()`. El único hook E14 está en `UsuarioViewSet.perform_update()`, que cubre el cambio manual. `ADM-04` documenta la ruta de formularios de perfil; este hallazgo cubre la ruta programada.
- **Ubicación:**
  - `backend/proyecto/escuela/usuario_estado.py:7-41`
  - `backend/proyecto/escuela/middleware.py:30-39`
  - `backend/proyecto/escuela/views.py:1637-1656`
  - `backend/proyecto/escuela/views.py:7782-7791`
  - `backend/proyecto/escuela/notifications.py:174-199`
  - Frontend: `frontend/src/components/Administracion/administradores.jsx:418-453`
  - Referencias: `docs/PLAN_NOTIFICACIONES_MiSecundaria7.md:347`, `docs/GUIA_TESTEO_MiSecundaria7.md:418`
- **Verificación:** lectura de `usuario_estado.py` completo y búsqueda global de `notificar_estado_cuenta`: no aparece en el módulo de programaciones ni en el middleware.
- **Corrección sugerida:** llamar a `notificar_estado_cuenta(usuario)` dentro de `aplicar_programaciones_usuario()` una sola vez por transición real, manteniendo el hook manual y evitando duplicados.
- **Corrección aplicada:** `aplicar_programaciones_usuario()` importa y ejecuta `notificar_estado_cuenta(usuario)` después de `save()`, una sola vez por usuario con estado realmente cambiado. El hook manual de `perform_update()` sigue vigente.
- **Criterio de aceptación:** con una fecha vencida, la próxima request genera exactamente una E14 para el usuario afectado; el toggle manual sigue generando una; no se duplica al refrescar.

## DIR-07 — Alta de “directivo” documentada pero no implementada

- **Síntoma:** los requerimientos dicen `RF-USR-05 — Alta de administrador/directivo con cargo`. En la UI del director, “Nuevo Administrador” siempre envía `roles: ['admin']`; no existe opción para crear un `director`. `POST /api/directivos/` crea el perfil pero no asigna `UsuarioRol`. Aunque `POST /api/usuarios/` aceptaría `roles: ['director']`, `UsuarioViewSet.get_queryset()` filtra el listado a usuarios con rol `admin`, así que ese director no aparece en el panel.
- **Causa:** roles hardcodeados en el frontend, desacoplamiento entre perfil `Directivo` y roles `UsuarioRol`, y filtro de listado restringido a `admin`.
- **Ubicación:**
  - `docs/REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md:97-105`
  - `frontend/src/components/Administracion/administradores.jsx:291-301`
  - `frontend/src/components/Administracion/administradores.jsx:333-344`
  - `backend/proyecto/escuela/serializers.py:753-758`, `:760-779`
  - `backend/proyecto/escuela/views.py:1577-1592`
- **Verificación:** búsqueda de `roles: [` en el frontend: sólo aparece `['admin']` en `administradores.jsx`. No hay flujo UI para `director`.
- **Corrección sugerida:** definir una política única. Si el director debe crear directores, agregar el selector de rol, enviar `roles: ['director']`, asignar el rol en el mismo flujo y ampliar el queryset a `nombre_rol__in=['admin','director']`. Si no debe hacerlo, cambiar el requerimiento a “Alta de administrador con cargo” y aclarar que los directores son datos preexistentes.
- **Corrección aplicada:** se implementó la política de alta de directivos. El formulario permite elegir `Administrador`/`Director`, envía `roles` sólo en creación, el serializer crea/actualiza el perfil `Directivo` con cargo coherente, `UsuarioViewSet` lista ambos roles y “Agregar rol” también puede asignar `director`. Sólo un director puede crear cualquiera de los dos roles.
- **Criterio de aceptación:** documento, UI y API coinciden; crear un directivo desde el panel genera usuario con rol `director`, perfil `Directivo` y el registro aparece en la lista correspondiente.

## DIR-08 — `mi-ddjj` permite suplantación y autonotificación E9

- **Síntoma:** un director con `X-Rol-Activo: director` puede llamar `POST /api/ddjj-docente/mi-ddjj/?id_docente=<otro>` y guardar una DDJJ a nombre de ese docente. `_notificar_ddjj_presentada()` avisa a todos los directivos sin excluir al actor, por lo que el director recibe “DDJJ presentada” por una acción que él mismo realizó.
- **Causa:** `_get_docente_from_request()` toma `id_docente` del body/query para admin/director, y el action `mi_ddjj` llama a `serializer.save()` directamente sin pasar por `_can_manage()` ni por un `perform_create()` que excluya al actor. El endpoint `mi-ddjj` por su nombre debería operar sólo sobre el docente autenticado.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:2117-2167`
  - `backend/proyecto/escuela/views.py:2240-2250`
  - `backend/proyecto/escuela/views.py:7588-7607`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:414`, `:442`
- **Verificación:** lectura directa del action y del emisor. No se encontró documentación que habilite expresamente a un director a presentar la DDJJ por otro docente.
- **Corrección sugerida:** rechazar `id_docente` para el actor directivo en `mi_ddjj` y exigir el docente autenticado. Si se decide conservar la delegación, pasar el actor al emisor, excluirlo de destinatarios y aclarar en el mensaje que fue presentada por el directivo en nombre del docente.
- **Corrección aplicada:** se adoptó la política de titularidad: `mi_ddjj` resuelve siempre el perfil del docente autenticado e ignora `id_docente` de body/query. Un directivo sin perfil docente recibe `403`, por lo que no puede presentar DDJJ ajenas ni autonotificarse E9.
- **Criterio de aceptación:** E9 se crea cuando el docente titular presenta su propia DDJJ; si un directivo gestiona una DDJJ ajena, no se autonotifica y el mensaje identifica al operador.

## Orden sugerido de corrección

1. `DIR-01` — pérdida del rol director al editar administradores.
2. `DIR-02` — política de E4/E21 y coherencia documental.
3. `DIR-07`, `DIR-08` — contrato de alta de directivos y suplantación de DDJJ.
4. `DIR-05`, `DIR-06` — preservación de cargo y E14 programado.
5. `DIR-03`, `DIR-04` — textos y leyendas de UI.

## Revisado sin hallazgos

- El sidebar muestra “Administradores” y “Configuración” sólo para director/admin; “Administradores” está marcado `directorOnly` en `sidebarMenu.js:14` y `sidebar/sidebar.jsx:28-36`, coherente con la guía.
- `PanelAdmin.jsx:48-56` muestra la etiqueta “Director” correctamente cuando el rol activo es `director`.
- El header usa el selector global de **un solo curso** (Año lectivo → Año → División) en `AdminDashboard.jsx:41-45`, `:106-110`. La multiselección descripta en versiones anteriores quedó fuera de vigencia; no reintroducirla.
- `navAplicadoRef` en `AdminDashboard.jsx:52-58` evita reaplicar un `navIntent` por refrescos.
- E8/E9, E15, E17, E20, cambios de estructura, cambios de horario y comunicados llegan al segmento directivo según la guía; el problema de “Ver” es `ADM-05`/`ADM-06`, compartido y no repetido.
- `ADM-01` no aplica al director: el director sí debe poder gestionar administradores/directivos.
- `ADM-03` no aplica al director: la puerta director-only de `/api/usuarios/` funciona para este rol.
- `ADM-05`, `ADM-06`, `ADM-07`, `ADM-08`, `ADM-09`, `ADM-10` y `ADM-11` ya están documentados en el MD de Administrador y no tienen manifestación distinta en director, excepto `DIR-02` y `DIR-06`.
- No se modificaron `AdelantosHoras.jsx` ni `AsistenciasUnificada.jsx`.
