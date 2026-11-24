# Hallazgos del rol Jefe de Preceptores

Fecha: 2026-11-24  
Estado general: **corregido**.  
Alcance: auditoría de código del panel Jefe de Preceptores (perfil, administración de preceptores, asignación de cursos, seguimiento, estadísticas, comunicados, notificaciones y navegación) y de los endpoints/permisos que consume. Se corrigieron los 11 hallazgos; queda pendiente la validación funcional en navegador.

Convención: `P0` = exposición de datos o fallo crítico, `P1` = funcionalidad rota, `P2` = dato/visual incorrecto o error de contrato no crítico. Los ítems marcados como compartidos también aparecen en otros MD de rol. Los hallazgos `PRE-09`, `PRE-11` y `PRE-12` del MD de Preceptor también aplican a este rol y no se repiten acá; ya fueron corregidos en ese rol.

## Resumen

| ID | Prioridad | Síntesis |
|---|---|---|
| JEFE-01 | P0 | Un jefe puede modificar/borrar un perfil de jefe omitiendo `?rol=jefe_preceptores`. |
| JEFE-02 | P1 | “Supervisión de Preceptores” existe pero no es alcanzable desde el panel. |
| JEFE-03 | P1 | El botón “Ver” de notificaciones de horario lleva a “Mi Perfil”. |
| JEFE-04 | P1 | El jefe recibe directamente la notificación “Suplencia asignada”, que la guía excluye. |
| JEFE-05 | P1 | El jefe puede escribir horarios aunque la documentación dice que no. |
| JEFE-06 | P2 | Comunicados: la lista del jefe no coincide con lo que la API le muestra. |
| JEFE-07 | P2 | Tutores usa el curso sin resolver cuando se elige sólo el año. |
| JEFE-08 | P2 | “Último Acceso” del perfil siempre muestra “Nunca”. |
| JEFE-09 | P2 | Filas “Sin perfil” repiten la clave de React y pueden quedar trabadas. |
| JEFE-10 | P2 | `actividades-docente`: lectura amplia para el jefe y escritura denegada. |
| JEFE-11 | P2 | Mensaje de error incorrecto al quitar roles privilegiados. |

## JEFE-01 — Perfiles de jefe editables omitiendo el parámetro de rol

- **Síntoma:** un usuario con rol puro `jefe_preceptores` puede hacer `PATCH` o `DELETE /api/preceptores/{id}/` sobre el perfil de otro jefe si no envía `?rol=jefe_preceptores`. Puede cambiar sus datos, asignarle cursos y hasta borrar el perfil, con la consiguiente pérdida del rol `jefe_preceptores`.
- **Causa:** el rol objetivo se infiere sólo del query param. Sin `rol`, `get_queryset()` devuelve todos los perfiles de preceptor/jefe al jefe, `get_serializer_context()` usa `'preceptor'`, y `perform_update()`/`perform_destroy()` ejecutan la autorización débil `_require_admin_or_director()` en lugar de `_require_admin_or_director_only()`. En el borrado se quita el rol `preceptor`, no `jefe_preceptores`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:2511-2527`
  - `backend/proyecto/escuela/views.py:2529-2542`
  - `backend/proyecto/escuela/views.py:2561-2588`
  - `backend/proyecto/escuela/serializers.py:1221-1227`
  - `backend/proyecto/escuela/serializers.py:1295-1316`
  - `backend/proyecto/escuela/permissions.py:200-211`
- **Verificación:** lectura directa del viewset y del serializer. La UI normal siempre envía `rol=preceptor` en `AdminPreceptores.jsx:239-241`, `:317-324` y `:343`; el ataque es por llamada API directa.
- **Corrección sugerida:** inferir el rol objetivo desde `UsuarioRol` del usuario del perfil, no desde el query string. Un jefe debe recibir `403` para crear/editar/borrar cualquier objetivo con `jefe_preceptores`, con o sin parámetros. Mantener su acceso a perfiles `preceptor`. El borrado debe quitar el rol que realmente corresponda al perfil eliminado.
- **Corrección aplicada:** `PreceptorViewSet._is_jefe_target(instance=None)` consulta `UsuarioRol` del perfil en update/destroy, ignorando el query param; en create (sin instancia) conserva el param porque es el único modo de declarar el rol nuevo. `perform_update()` y `perform_destroy()` exigen `_require_admin_or_director_only()` cuando el objetivo real es jefe. El serializer usa `_role_name_from_instance()` para no reasignar cursos a un perfil jefe aunque venga sin `rol`. El borrado quita `jefe_preceptores` cuando corresponde, y el historial usa la tabla correcta. Las decisiones de actor pasaron a `roles_efectivos()`.
- **Criterio de aceptación:** `PATCH`/`DELETE` sobre un perfil jefe por un jefe devuelve 403; admin/director siguen pudiendo gestionarlos; el rol quitado al borrar es siempre el del perfil eliminado.

## JEFE-02 — Supervisión de Preceptores no reachable desde el panel

- **Síntoma:** el módulo “Supervisión de Preceptores” no se puede abrir. No aparece en el menú y no hay vista que lo renderice, aunque el componente, la función de API y el endpoint están implementados.
- **Causa:** `SupervisionPreceptores.jsx` no se importa en `JefePreceptorDashboard.jsx`; `sidebarMenu.js` no incluye una entrada `supervision`; el `switch` de vistas tampoco tiene ese `case`. El componente queda como código muerto.
- **Ubicación:**
  - `frontend/src/components/JefePreceptores/SupervisionPreceptores.jsx:60-79`
  - `frontend/src/services/api.js:796-799`
  - `frontend/src/components/JefePreceptores/JefePreceptorDashboard.jsx:163-269`
  - `frontend/src/components/JefePreceptores/sidebarMenu.js:14-35`
  - `backend/proyecto/escuela/views.py:6299-6373`
  - `backend/proyecto/escuela/urls.py:67`
  - Requerimiento: `docs/REQUERIMIENTOS_SISTEMA_SECUNDARIA7.md:227`, `docs/RELEVAMIENTO_SISTEMA_SECUNDARIA7.md:186`
- **Verificación:** búsqueda de importaciones: el único consumidor de `getSupervisionPreceptores()` era el propio componente no renderizado.
- **Corrección sugerida:** agregar la entrada al menú de “Seguimiento Escolar” y el `case 'supervision'` en `renderView()`, o quitar el módulo y el endpoint si se decidió no incluirlo.
- **Corrección aplicada:** `JefePreceptorDashboard.jsx` importa `SupervisionPreceptores` y agrega `case 'supervision'`; `sidebarMenu.js` incluye la entrada en “Gestión de Jefatura”. El componente se autollama con `getSupervisionPreceptores()` y consume los campos que devuelve el endpoint.
- **Criterio de aceptación:** el jefe puede abrir “Supervisión de Preceptores” desde el sidebar y ve el listado devuelto por `/api/supervision-preceptores/`.

## JEFE-03 — Notificaciones de horario navegan a “Mi Perfil”

- **Síntoma:** al hacer clic en “Ver” de una notificación “Cambio de horario”, el panel queda en “Mi Perfil” en lugar de mostrar los horarios.
- **Causa:** `navDestinos.js` normaliza `jefe_preceptores` a `preceptor`, y el mapa de preceptor traduce `horarios` a la vista `horarios`. El dashboard del jefe llama a `viewDesdeDestino(..., 'preceptor')`, pero su `switch` no implementa `horarios`, por lo que cae en `default` y renderiza `PanelJefePreceptor`.
- **Ubicación:**
  - `frontend/src/utils/navDestinos.js:59-69`
  - `frontend/src/utils/navDestinos.js:91-100`
  - `frontend/src/components/JefePreceptores/JefePreceptorDashboard.jsx:85-92`
  - `frontend/src/components/JefePreceptores/JefePreceptorDashboard.jsx:263-268`
  - `backend/proyecto/escuela/views.py:7988-8006`
  - `frontend/src/components/JefePreceptores/sidebarMenu.js:14-35`
- **Verificación:** el backend emite `nav_destino: 'horarios'` para jefes; el dashboard no tenía caso `horarios` ni el menú del jefe ofrecía esa sección.
- **Corrección sugerida:** crear una vista de horarios para el jefe y agregarla al menú, o quitar el destino `horarios` del mapa normalizado cuando el rol sea jefe para que la notificación no muestre “Ver”.
- **Corrección aplicada:** se eligió crear la vista. `JefePreceptorDashboard.jsx` importa `VistaHorarios` y agrega `case 'horarios'` en modo consulta (`cursosOptions={cursosObj}`, `cursoForzado={cursosResueltos.ids[0]}`, `cargarAdelantos={false}`). `sidebarMenu.js` incluye “Horarios” en “Seguimiento Escolar”. `navDestinos.js` ya mapeaba `horarios → horarios`, por lo que no se modificó.
- **Criterio de aceptación:** ninguna notificación del jefe abre “Mi Perfil” por error; “Ver” abre una sección válida de horarios.

## JEFE-04 — Notificación “Suplencia asignada” enviada de forma directa al jefe

- **Síntoma:** un jefe sin curso asignado recibe igualmente el aviso “Suplencia asignada” cuando se crea una suplencia en cualquier curso.
- **Causa:** `_notificar_suplencia_asignada()` recorre `_usuarios_con_rol('jefe_preceptores')` y emite el aviso con segmento `SEGMENTO_JEFE_PRECEPTORES`, además del docente suplente, preceptores del curso y directivos.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:7441-7476`
  - `backend/proyecto/escuela/views.py:3001-3003`
  - Referencias: `docs/GUIA_TESTEO_MiSecundaria7.md:303`, `docs/GUIA_TESTEO_MiSecundaria7.md:321`, `docs/PLAN_NOTIFICACIONES_MiSecundaria7.md:353`
- **Verificación:** la guía de testeo indica explícitamente que el jefe **no** recibe ese aviso directo; sí lo recibe como preceptor si además tiene ese rol en el curso afectado.
- **Corrección sugerida:** eliminar el bucle de jefes del helper. Conservar el aviso por segmento preceptor cuando el jefe sea el preceptor asignado del curso.
- **Corrección aplicada:** se eliminó el bucle `_usuarios_con_rol('jefe_preceptores')`. La rama de `_preceptores_para_cursos([cm.id_curso_id])` se conserva, cubriendo al jefe que también es preceptor del curso afectado.
- **Criterio de aceptación:** con un jefe puro y un curso no asignado a él, no se crea notificación E17 para ese usuario.

## JEFE-05 — Escritura de horarios permitida por código, prohibida por la guía

- **Síntoma:** un jefe puro puede `POST`, `PATCH` y `DELETE` en `/api/horarios/` y `/api/horarios-especiales/` para cualquier curso.
- **Causa:** `PuedeGestionarHorarios` incluía `jefe_preceptores` en la puerta de escritura y `_verificar_escritura_horario()` devolvía sin validar para los roles de gestión, entre ellos el jefe. La guía de testeo dice lo contrario.
- **Ubicación:**
  - `backend/proyecto/escuela/permissions.py:150-167`
  - `backend/proyecto/escuela/views.py:282-295`
  - `backend/proyecto/escuela/views.py:3167`
  - `backend/proyecto/escuela/views.py:3202`
  - `backend/proyecto/escuela/views.py:3226`
  - `backend/proyecto/escuela/views.py:3269`
  - Referencia: `docs/GUIA_TESTEO_MiSecundaria7.md:509`
- **Verificación:** el docstring de `PuedeGestionarHorarios` afirmaba que el jefe gestiona; la guía afirma que el jefe **no** escribe horarios. Se adoptó la guía como política vigente.
- **Corrección sugerida:** quitar `jefe_preceptores` de `PuedeGestionarHorarios` y de `_verificar_escritura_horario()`; el jefe conserva lectura.
- **Corrección aplicada:** `PuedeGestionarHorarios.has_permission()` sólo habilita escritura a `admin`, `director` y `preceptor`; `_verificar_escritura_horario()` usa `roles_efectivos()` y sólo exceptúa a `admin`/`director`. Ambos docstrings se actualizaron. La lectura del jefe no se modificó.
- **Criterio de aceptación:** política de escritura de horarios para el jefe definida y coherente entre código, documentación y UI: el jefe lee, no escribe.

## JEFE-06 — Comunicados: lista del jefe no coincide con la API

- **Síntoma:** un jefe que también tiene perfil de preceptor con cursos asignados ve menos comunicados en el panel que los que la API le devuelve. Además podían aparecer comunicados de ciclos anteriores como vigentes.
- **Causa:** `ComunicadosView` filtraba la rama `jefe_preceptores` por los cursos del perfil de preceptor cuando éste tenía cursos, mientras `_comunicado_visible_para_ctx()` devuelve `True` para jefe sin mirar alcances. En paralelo, `comunicadoEstaVigente()` buscaba el `id_ciclo` dentro de `aniosLectivos`, que `DataContext` arma como números.
- **Ubicación:**
  - `frontend/src/components/Shared/ComunicadosView.jsx:47-60`
  - `frontend/src/components/Shared/ComunicadosView.jsx:168-176`
  - `frontend/src/components/JefePreceptores/ComunicadosJefe.jsx:300`
  - `frontend/src/context/DataContext.jsx:572-573`
  - `backend/proyecto/escuela/views.py:827-831`
  - Referencias compartidas: `AL-04`, `FAM-07`, `DOC-10`, `PRE-13`
- **Verificación:** comparación directa entre el filtro del frontend y `_comunicado_visible_para_ctx()`.
- **Corrección sugerida:** alinear el listado del jefe con la API (sólo filtro de vigencia, sin filtro por cursos propios) y normalizar la comparación de ciclos usando `ciclosLectivos` completos.
- **Corrección aplicada:** la vigencia con `ciclosLectivos` ya venía corregida desde el fix compartido. La rama `jefe_preceptores` de `ComunicadosView` se simplificó a `comunicados.filter(c => comunicadoEstaVigente(c, ciclosLectivos))`, eliminando el filtro por `misCursos` del perfil de preceptor.
- **Criterio de aceptación:** el jefe ve todos los comunicados vigentes que devuelve la API; los comunicados de ciclos anteriores quedan ocultos.

## JEFE-07 — Tutores ignora la resolución global de curso

- **Síntoma:** si se elige un año lectivo y después sólo el año académico (por ejemplo `1°`, sin división), el listado de tutores queda vacío, mientras el resto del panel interpreta esa selección como “sin curso”.
- **Causa:** `JefePreceptorDashboard` calcula `cursosResueltos` con `resolverCursosSeleccionados()` y se lo pasa a casi todas las vistas, pero a `TutoresFamilias` le pasaba `cursos` y `curso` crudos. `tutoresPorAnioYCurso()` aplica el filtro con `1°`, que no coincide con ningún curso real (`1°1`, `1°2`, ...).
- **Ubicación:**
  - `frontend/src/components/JefePreceptores/JefePreceptorDashboard.jsx:154-161`
  - `frontend/src/components/JefePreceptores/JefePreceptorDashboard.jsx:186-190`
  - `frontend/src/utils/seleccionCurso.js:8-22`
  - `frontend/src/components/Preceptores/tutoresFamilias.jsx:130-136`
  - `frontend/src/components/Preceptores/preceptorUtils.js:86-100`
- **Verificación:** lectura directa de las props y del helper de filtro.
- **Corrección sugerida:** pasar `cursos={cursosResueltos.nombres}` y `curso={cursosResueltos.nombres[0] || ''}` a `TutoresFamilias`, igual que al resto de las vistas.
- **Corrección aplicada:** `TutoresFamilias` recibe `{...filtrosProps}` en lugar de `cursos`/`curso` crudos, por lo que usa `cursosResueltos.nombres` y el primero de ellos.
- **Criterio de aceptación:** con un año sin división, tutores interpreta “sin selección” igual que las demás secciones y no muestra una lista vacía engañosa.

## JEFE-08 — “Último Acceso” siempre muestra “Nunca”

- **Síntoma:** el perfil del jefe mostraba “Último Acceso: Nunca” incluso después de haber iniciado sesión varias veces.
- **Causa:** `PanelJefePreceptor` leía `miPreceptor.usuario_fecha_ultimo_acceso`, campo que no existía en `PreceptorSerializer` ni en el mapeo de `DataContext`. El fallback de directivo también leía `admin.usuario_fecha_ultimo_acceso`, que no se mapeaba. `/api/me/` tampoco devuelve `ultimo_acceso`, aunque el modelo `Usuario` sí lo tiene.
- **Ubicación:**
  - `frontend/src/components/JefePreceptores/PanelJefePreceptor.jsx:42`
  - `frontend/src/components/JefePreceptores/PanelJefePreceptor.jsx:91-94`
  - `frontend/src/components/JefePreceptores/JefePreceptorDashboard.jsx:48-60`
  - `frontend/src/context/DataContext.jsx:471-499`
  - `backend/proyecto/escuela/serializers.py:1133-1157`
  - `backend/proyecto/escuela/views.py:1286-1290`
- **Verificación:** búsqueda global: el único consumidor de `ultimoAcceso` era ese panel; ningún productor entregaba el campo con ese nombre.
- **Corrección sugerida:** exponer `ultimo_acceso` en `PreceptorSerializer` (o en `/me/`), mapearlo en `DataContext` como `usuario_fecha_ultimo_acceso` y usarlo en el panel.
- **Corrección aplicada:** `PreceptorSerializer` expone `usuario_fecha_ultimo_acceso` desde `obj.id_usuario.ultimo_acceso` (ISO o `null`). `DataContext` mapea ese campo tanto en preceptores como en administradores, y el fallback de `JefePreceptorDashboard` ya lo propagaba a `PanelJefePreceptor`.
- **Criterio de aceptación:** el panel muestra la fecha real del último ingreso, o la fila desaparece por diseño.

## JEFE-09 — Claves de React repetidas en preceptores sin perfil

- **Síntoma:** cuando hay varios usuarios con rol `preceptor` pero sin fila en `Preceptor`, React emitía advertencias de clave duplicada y las filas “Sin perfil” podían actualizarse de forma trabada.
- **Causa:** todas las filas sintetizadas usaban `id_preceptor: null`, y el `Fragment` las claveaba con `p.id_preceptor`.
- **Ubicación:**
  - `frontend/src/components/JefePreceptores/AdminPreceptores.jsx:169-186`
  - `frontend/src/components/JefePreceptores/AdminPreceptores.jsx:685-686`
- **Verificación:** lectura directa del armado de `lista` y del render.
- **Corrección sugerida:** usar `p.id_usuario` o una clave compuesta estable, por ejemplo `` `sin-perfil-${p.id_usuario}` ``.
- **Corrección aplicada:** el `Fragment` usa `p.sin_perfil ? \`sin-perfil-${p.id_usuario}\` : p.id_preceptor`. Las filas con perfil conservan su clave original.
- **Criterio de aceptación:** varias filas “Sin perfil” se renderizan sin warnings y se pueden completar/actualizar de forma independiente.

## JEFE-10 — Actividades docentes: lectura amplia y escritura denegada para el jefe

- **Síntoma:** un jefe puro podía consultar `/api/actividades-docente/` y ver actividades de todos los docentes/cursos, pero `POST`, `PATCH` y `DELETE` devolvían `403`.
- **Causa:** `ActividadDocenteViewSet.get_queryset()` no tenía rama para jefe puro: `_es_preceptor_operativo()` devuelve `False` por el rol de gestión y no había ningún otro `elif`, por lo que quedaba el queryset completo. En cambio, `PuedeGestionarAmbitoDocente` sólo habilitaba escritura para `admin`, `director` y `docente`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:2324-2331`
  - `backend/proyecto/escuela/views.py:2343-2388`
  - `backend/proyecto/escuela/views.py:268-279`
  - `backend/proyecto/escuela/permissions.py:179-185`
  - `backend/proyecto/escuela/permissions.py:246-255`
- **Verificación:** el dashboard del jefe no expone esta vista, pero el endpoint está montado y es accesible.
- **Corrección sugerida:** definir la política: restringir la lectura del jefe a los cursos que supervisa o darle escritura explícita si el jefe debe cargar actividades docentes.
- **Corrección aplicada:** se adoptó la política de **lectura amplia y escritura denegada**, coherente con JEFE-05. `get_queryset()` usa `roles_efectivos()` y agrega una rama explícita `elif roles & {'admin', 'director', 'jefe_preceptores'}: pass`. `PuedeGestionarAmbitoDocente` y los `perform_*` siguen sin habilitar escritura al jefe, documentando la regla en el código y en este MD.
- **Criterio de aceptación:** lectura y escritura de actividades docentes para el jefe siguen una sola regla documentada: consulta global, sin carga.

## JEFE-11 — Mensaje de error incorrecto al quitar roles privilegiados

- **Síntoma:** cuando un jefe intentaba quitar `jefe_preceptores`, `admin` o `director`, el mensaje decía que esos roles los quitaba “un director (admin, director) o un administrador (jefe de preceptores)”, lo que sugería que el jefe sí podía hacerlo.
- **Causa:** el texto del `403` en `quitar-rol` no coincidía con `puede_quitar_rol()`: `admin`/`director` los quita sólo `director`; `jefe_preceptores` lo quitan sólo `admin` o `director`; el jefe sólo puede quitar `preceptor`, `docente`, `familia` y `alumno`.
- **Ubicación:**
  - `backend/proyecto/escuela/views.py:1740-1753`
  - `backend/proyecto/escuela/permissions.py:23-35`
- **Verificación:** comparación directa entre el mensaje y la función de permiso.
- **Corrección sugerida:** reescribir el mensaje para indicar que el jefe no puede quitar roles privilegiados y nombrar correctamente a los roles habilitados.
- **Corrección aplicada:** `quitar-rol` usa `roles_efectivos()` y devuelve un detalle por rol: `admin`/`director` → “Solo un director puede quitar los roles admin o director.”; `jefe_preceptores` → “Solo un administrador o un director puede quitar el rol jefe_preceptores.”
- **Criterio de aceptación:** el `403` describe con precisión la regla real de `puede_quitar_rol()`.

## Orden sugerido de corrección

1. `JEFE-01` — escape de permisos sobre perfiles de jefe.
2. `JEFE-03`, `JEFE-04`, `JEFE-05` — notificaciones, navegación y política de horarios.
3. `JEFE-02` — hacer alcanzable la supervisión de preceptores.
4. `JEFE-06`, `JEFE-07`, `JEFE-08`, `JEFE-09`, `JEFE-10`, `JEFE-11` — consistencia de datos, claves y mensajes.

## Revisado sin hallazgos

- `navAplicadoRef` en `JefePreceptorDashboard.jsx` evita reaplicar un `navIntent` cuando se refrescan los datos.
- El header del jefe usa un solo curso por vez (Año lectivo → Año → División); no se reintrodujo multiselección.
- `Estudiantes`, `Docentes`, `TutoresFamilias` y `Asistencias` reciben `readOnly` en `JefePreceptorDashboard.jsx`.
- `Notas` es una vista consolidada de sólo lectura con exportación PDF; no expone edición de calificaciones.
- `Actas` es escribible por el jefe por diseño: `PuedeGestionarActas` incluye `jefe_preceptores`.
- `EstadisticasPreceptoria` sí está enlazada desde el menú “Gestión de Jefatura”; el problema de alcanzabilidad era sólo de `SupervisionPreceptores`.
- `AdminPreceptores` envía `rol=preceptor` en las operaciones normales de alta/edición/borrado; `JEFE-01` requería una llamada API directa.
- No se modificaron `AdelantosHoras.jsx` ni `AsistenciasUnificada.jsx`.
