import { Fragment, useEffect, useState } from 'react';
import { useToast } from '../../context/ToastContext';
import { useData } from '../../context/DataContext';
import FormModal from '../../components/Shared/FormModal';
import AgregarRolModal from '../../components/Shared/AgregarRolModal';
import QuitarRolModal from '../../components/Shared/QuitarRolModal';
import AccionesCelda from '../../components/Shared/AccionesCelda';
import NumericInput from '../../components/Shared/NumericInput';
import { createUsuario, getUsuarios, updateUsuario, getUsuariosConRol, getUsuariosSinRol, quitarRolUsuario } from '../../services/api';
import { formatDNI } from '../../utils/dni';
import confirmarEliminacion from '../../utils/confirmarEliminacion';
import LoadingScreen from '../Shared/LoadingScreen';
import AccionesLeyenda from '../Shared/AccionesLeyenda';
import { aInputDateTime as toInputDateTime, aApiDateTime, errorProgramacion, ZONA_PROGRAMACION } from '../../utils/programacionEstado';

function formatDateTime(value) {
  if (!value) return '---';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '---';
  return new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short', timeZone: ZONA_PROGRAMACION }).format(date);
}

function estadoLabel(estado) {
  if (estado === null || estado === undefined) return 'Sin usuario';
  return estado ? 'Habilitado' : 'Deshabilitado';
}

const ROLES_DIRECTIVOS = [
  { value: 'admin', label: 'Administrador', cargo: 'Administrador' },
  { value: 'director', label: 'Director', cargo: 'Director' },
];

function cargoPorRol(rol) {
  return ROLES_DIRECTIVOS.find((opcion) => opcion.value === rol)?.cargo || 'Administrador';
}

function getNextAction(usuario) {
  if (usuario.estado === null || usuario.estado === undefined) return 'Sin usuario';
  if (usuario.estado && usuario.fecha_deshabilitacion_programada) {
    return `Deshabilitar el ${formatDateTime(usuario.fecha_deshabilitacion_programada)}`;
  }
  if (!usuario.estado && usuario.fecha_habilitacion_programada) {
    return `Habilitar el ${formatDateTime(usuario.fecha_habilitacion_programada)}`;
  }
  if (usuario.fecha_deshabilitacion_programada) {
    return `Deshabilitar el ${formatDateTime(usuario.fecha_deshabilitacion_programada)}`;
  }
  if (usuario.fecha_habilitacion_programada) {
    return `Habilitar el ${formatDateTime(usuario.fecha_habilitacion_programada)}`;
  }
  return '---';
}

const formVacio = {
  usuario: '',
  contrasena: '',
  nombre: '',
  apellido: '',
  dni: '',
  telefono: '',
  cargo: 'Administrador',
  rol: 'admin',
  estado: true,
  fecha_deshabilitacion_programada: '',
  fecha_habilitacion_programada: '',
  id_usuario_existente: '',
  modo_creacion: 'nuevo', // 'nuevo' | 'existente'
};

function Administradores() {
  const toast = useToast();
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const [formData, setFormData] = useState({
    usuario: '',
    contrasena: '',
    nombre: '',
    apellido: '',
    dni: '',
    telefono: '',
    cargo: 'Administrador',
    rol: 'admin',
    estado: true,
    fecha_deshabilitacion_programada: '',
    fecha_habilitacion_programada: '',
    id_usuario_existente: '',
    modo_creacion: 'nuevo', // 'nuevo' | 'existente'
  });
  const [error, setError] = useState('');
  const [mostrarAgregarRol, setMostrarAgregarRol] = useState(false);
  const [rolParaAgregar, setRolParaAgregar] = useState('admin');
  const [guardandoAgregarRol, setGuardandoAgregarRol] = useState(false);
  const [mostrarQuitarRol, setMostrarQuitarRol] = useState(false);
  const [rolParaQuitar, setRolParaQuitar] = useState('admin');
  const [quitandoRol, setQuitandoRol] = useState(false);
  const [guardandoUsuario, setGuardandoUsuario] = useState(false);
  const [personasConRol, setPersonasConRol] = useState([]);

  const [personasParaAgregarRol, setPersonasParaAgregarRol] = useState([]);
  const [cargandoPersonasSinRol, setCargandoPersonasSinRol] = useState(false);

  const cargarPersonasSinRol = async (rol = rolParaAgregar) => {
    setCargandoPersonasSinRol(true);
    try {
      const data = await getUsuariosSinRol(rol);
      setPersonasParaAgregarRol(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cargar administradores');
    } finally {
      setCargandoPersonasSinRol(false);
    }
  };

  useEffect(() => {
    cargarPersonasSinRol();
  }, [rolParaAgregar]);

  const { refreshData } = useData() || {};

  const resetForm = () => ({
    usuario: '',
    contrasena: '',
    nombre: '',
    apellido: '',
    dni: '',
    telefono: '',
    cargo: 'Administrador',
    rol: 'admin',
    estado: true,
    fecha_deshabilitacion_programada: '',
    fecha_habilitacion_programada: '',
    id_usuario_existente: '',
    modo_creacion: 'nuevo',
  });

  const fetchUsuarios = async () => {
    try {
      const data = await getUsuarios(true); // incluir deshabilitados
      const adminUsers = (Array.isArray(data) ? data : []).filter(
        (u) => u.roles && u.roles.some((rol) => rol === 'admin' || rol === 'director'),
      );
      setUsuarios(adminUsers);
    } catch (err) {
      toast.error('Error al cargar administradores');
    } finally {
      setLoading(false);
    }
  };

  /** Refresca la lista local y el estado global, para que el cambio se vea de
   *  inmediato sin recargar la página (punto 1.2 del plan de arreglos). */
  const refrescar = async () => {
    await fetchUsuarios();
    if (typeof refreshData === 'function') {
      try {
        await refreshData();
      } catch {
        toast.warning('El cambio se guardó, pero no se pudo actualizar el resumen global.');
      }
    }
  };

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const cerrarModal = () => {
    setShowModal(false);
    setEditingUsuario(null);
    setFormData(resetForm());
  };

  const handleCreate = () => {
    setEditingUsuario(null);
    setFormData(resetForm());
    setError('');
    setShowModal(true);
  };

  const handleEdit = (usuario) => {
    setEditingUsuario(usuario);
    setFormData({
      usuario: usuario.usuario || '',
      contrasena: '',
      nombre: usuario.directivo_nombre || '',
      apellido: usuario.directivo_apellido || '',
      dni: usuario.directivo_dni || '',
      telefono: usuario.directivo_telefono || '',
      cargo: usuario.directivo_cargo || 'Administrador',
      rol: usuario.roles?.includes('director') ? 'director' : 'admin',
      estado: usuario.estado !== false,
      fecha_deshabilitacion_programada: toInputDateTime(usuario.fecha_deshabilitacion_programada),
      fecha_habilitacion_programada: toInputDateTime(usuario.fecha_habilitacion_programada),
      id_usuario_existente: '',
      modo_creacion: 'nuevo',
    });
    setError('');
    setShowModal(true);
  };

  const handleToggleEstado = async (usuario) => {
    try {
      // Solo cambiamos el estado, no borramos el usuario
      await updateUsuario(usuario.id_usuario, {
        estado: !usuario.estado,
        // Mantener datos del perfil - no incluir campos que puedan provocar eliminación
      });
      toast.success(usuario.estado ? 'Administrador deshabilitado correctamente.' : 'Administrador habilitado correctamente.');
      await refrescar();
    } catch (err) {
      toast.error('Error al actualizar el estado del administrador: ' + (err.response?.data?.detail || 'Error desconocido'));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setGuardandoUsuario(true);

    // 5.9 — si se cargan las dos fechas, la primera de la línea de tiempo tiene
    // que ser la opuesta al estado que se está guardando; si no, la primera de
    // las dos no haría nada. En creación no hay estado previo todavía, así que
    // se toma el que se está por guardar.
    const errorFechas = errorProgramacion({
      estadoInicial: formData.estado === false ? false : true,
      deshabilitacion: formData.fecha_deshabilitacion_programada,
      habilitacion: formData.fecha_habilitacion_programada,
    });
    if (errorFechas && (formData.fecha_deshabilitacion_programada || formData.fecha_habilitacion_programada)) {
      toast.warning(errorFechas);
      setGuardandoUsuario(false);
      return;
    }

    try {
      const formDataCopy = { ...formData };
      delete formDataCopy.id_usuario_existente;

      const normalisedPayload = {
        ...formDataCopy,
        usuario_nombre: formData.usuario,
        fecha_deshabilitacion_programada: aApiDateTime(formData.fecha_deshabilitacion_programada),
        fecha_habilitacion_programada: aApiDateTime(formData.fecha_habilitacion_programada),
      };

      const payload = { ...normalisedPayload };

      delete payload.modo_creacion;
      delete payload.id_usuario;
      delete payload.usuario;
      delete payload.rol;
      if (!editingUsuario) {
        payload.roles = [formData.rol];
      }

      if (editingUsuario) {
        if (!formData.contrasena) {
          delete payload.contrasena;
        }
        await updateUsuario(editingUsuario.id_usuario, payload);
        toast.success('Administrador actualizado correctamente.');
      } else {
        // Validar contraseña solo si es creación nueva
        if (!payload.contrasena) {
          toast.warning('La contrasena es obligatoria para crear un administrador.');
          return;
        }
        await createUsuario(payload);
        toast.success('Administrador creado correctamente.');
      }

      cerrarModal();
      await refrescar();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al guardar administrador');
    } finally {
      setGuardandoUsuario(false);
    }
  };

  const handleAgregarRol = async ({ persona }) => {
    setGuardandoAgregarRol(true);
    try {
      await createUsuario({
        id_usuario_existente: Number(persona.id_usuario ?? persona.id),
        roles: [rolParaAgregar],
        nombre: persona.nombre || '',
        apellido: persona.apellido || '',
        dni: persona.dni || '',
        telefono: persona.telefono || '',
      });
      const etiquetaRol = ROLES_DIRECTIVOS.find((opcion) => opcion.value === rolParaAgregar)?.label || 'Administrador';
      toast.success(`Rol "${etiquetaRol}" asignado correctamente.`);
      setMostrarAgregarRol(false);
      await refrescar();
    } catch (err) {
      const data = err.response?.data;
      toast.error(data?.error || data?.detail || 'Error al asignar rol');
    } finally {
      setGuardandoAgregarRol(false);
    }
  };

  const cargarPersonasConRol = async (rol = rolParaQuitar) => {
    try {
      const data = await getUsuariosConRol(rol);
      setPersonasConRol(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cargar administradores');
    }
  };

  const handleQuitarRol = async (persona) => {
    setQuitandoRol(true);
    try {
      await quitarRolUsuario(Number(persona.id_usuario), rolParaQuitar);
      const etiquetaRol = ROLES_DIRECTIVOS.find((opcion) => opcion.value === rolParaQuitar)?.label || 'Administrador';
      toast.success(`Rol "${etiquetaRol}" quitado correctamente.`);
      setMostrarQuitarRol(false);
      await refrescar();
    } catch (err) {
      const data = err.response?.data;
      toast.error(data?.error || data?.detail || 'Error al quitar rol');
    } finally {
      setQuitandoRol(false);
    }
  };

  if (loading) {
    return <LoadingScreen text="Cargando administradores" />;
  }

  const renderFormulario = () => (
    <FormModal title={editingUsuario ? 'Editar Administrador' : 'Nuevo Administrador'} onClose={cerrarModal} error={error} onClearError={() => setError('')}>
      <form onSubmit={handleSubmit}>
        <div className="standard-modal-body" style={{ display: 'grid', gap: '14px' }}>
          <section className="preceptor-form-section">
            <h4>Datos de acceso</h4>
            <div className="preceptor-form-row preceptor-form-row--two">
              <div className="form-group-filter">
                <label htmlFor="usuario">Usuario</label>
                <input
                  type="text"
                  id="usuario"
                  value={formData.usuario}
                  onChange={(e) => setFormData({ ...formData, usuario: e.target.value })}
                  required
                  disabled={!!editingUsuario}
                />
              </div>

              <div className="form-group-filter">
                <label htmlFor="contrasena">
                  Contrasena {editingUsuario ? '(dejar en blanco para mantener)' : ''}
                </label>
                <input
                  type="password"
                  id="contrasena"
                  value={formData.contrasena}
                  onChange={(e) => setFormData({ ...formData, contrasena: e.target.value })}
                  required={!editingUsuario}
                />
              </div>
            </div>
          </section>
          
          <section className="preceptor-form-section">
            <h4>Estado de la cuenta</h4>
            <div className="preceptor-form-row preceptor-form-row--status">
              <div className="form-group-filter">
                <label htmlFor="admin-estado" className="preceptor-status-toggle">
                  <input
                    id="admin-estado"
                    type="checkbox"
                    checked={formData.estado}
                    onChange={(e) => setFormData({ ...formData, estado: e.target.checked })}
                    disabled={guardandoUsuario}
                  />
                  <span>{estadoLabel(formData.estado)}</span>
                </label>
              </div>

              <div className="form-group-filter">
                <label htmlFor="fecha_deshabilitacion_programada">Fecha deshabilitación programada</label>
                <input
                  type="datetime-local"
                  id="fecha_deshabilitacion_programada"
                  value={formData.fecha_deshabilitacion_programada}
                  onChange={(e) => setFormData({ ...formData, fecha_deshabilitacion_programada: e.target.value })}
                />
              </div>

              <div className="form-group-filter">
                <label htmlFor="fecha_habilitacion_programada">Fecha habilitación programada</label>
                <input
                  type="datetime-local"
                  id="fecha_habilitacion_programada"
                  value={formData.fecha_habilitacion_programada}
                  onChange={(e) => setFormData({ ...formData, fecha_habilitacion_programada: e.target.value })}
                />
              </div>
            </div>
          </section>
          
          <section className="preceptor-form-section">
            <h4>Datos personales</h4>
            <div className="preceptor-form-row preceptor-form-row--two">
              <div className="form-group-filter">
                <label htmlFor="nombre">Nombre</label>
                <input
                  type="text"
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  required
                  
                />
              </div>

              <div className="form-group-filter">
                <label htmlFor="apellido">Apellido</label>
                <input
                  type="text"
                  id="apellido"
                  value={formData.apellido}
                  onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                  required
                  
                />
              </div>
            </div>

            <div className="preceptor-form-row preceptor-form-row--two">
              <div className="form-group-filter">
                <label htmlFor="dni">DNI</label>
                <input
                  type="text"
                  id="dni"
                  value={formData.dni}
                  onChange={(e) => setFormData({ ...formData, dni: formatDNI(e.target.value) })}
                  required
                  
                />
              </div>

              <div className="form-group-filter">
                <NumericInput
                  id="telefono"
                  label="Telefono"
                  value={formData.telefono}
                  onChange={(val) => setFormData({ ...formData, telefono: val })}
                  placeholder="Ej: 1123456789"
                />
              </div>
            </div>
          </section>
          
          <section className="preceptor-form-section">
            <h4>Datos administrativos</h4>
            <div className="preceptor-form-row preceptor-form-row--two">
              <div className="form-group-filter">
                <label htmlFor="rol">Rol</label>
                <select
                  id="rol"
                  value={formData.rol}
                  onChange={(e) => setFormData({
                    ...formData,
                    rol: e.target.value,
                    cargo: cargoPorRol(e.target.value),
                  })}
                  disabled={!!editingUsuario || guardandoUsuario}
                >
                  {ROLES_DIRECTIVOS.map((opcion) => (
                    <option key={opcion.value} value={opcion.value}>{opcion.label}</option>
                  ))}
                </select>
              </div>

              <div className="form-group-filter">
                <label htmlFor="cargo">Cargo</label>
                <input
                  type="text"
                  id="cargo"
                  value={formData.cargo}
                  onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                />
              </div>
            </div>
          </section>
        </div>
        <div className="standard-modal-footer">
          <button type="submit" className="btn btn-primary">
            <i className="fas fa-save" aria-hidden="true" /> {editingUsuario ? 'Actualizar' : 'Crear'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={cerrarModal}>Cancelar</button>
        </div>
      </form>
    </FormModal>
  );

  return (
    <div className="card">
      <div className="card-header-flex">
        <h3><i className="fas fa-user-shield" aria-hidden="true" /> Directivos</h3>
        <div className="header-actions">
          <select
            aria-label="Rol a asignar"
            value={rolParaAgregar}
            onChange={(e) => setRolParaAgregar(e.target.value)}
            disabled={guardandoAgregarRol}
            style={{ minWidth: 150 }}
          >
            {ROLES_DIRECTIVOS.map((opcion) => (
              <option key={opcion.value} value={opcion.value}>{opcion.label}</option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={() => setMostrarAgregarRol(true)}
          >
            <i className="fas fa-user-tag" aria-hidden="true" /> Agregar rol
          </button>
          <select
            aria-label="Rol a quitar"
            value={rolParaQuitar}
            onChange={(e) => setRolParaQuitar(e.target.value)}
            disabled={quitandoRol}
            style={{ minWidth: 150 }}
          >
            {ROLES_DIRECTIVOS.map((opcion) => (
              <option key={opcion.value} value={opcion.value}>{opcion.label}</option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-outline-danger"
            onClick={() => {
              cargarPersonasConRol(rolParaQuitar);
              setMostrarQuitarRol(true);
            }}
          >
            <i className="fas fa-user-minus" aria-hidden="true" /> Quitar rol
          </button>
          <span className="header-actions-sep" aria-hidden="true" />
          <button type="button" className="btn btn-primary" onClick={handleCreate}>
            <i className="fas fa-plus" aria-hidden="true" /> Nuevo {ROLES_DIRECTIVOS.find((opcion) => opcion.value === formData.rol)?.label || 'Administrador'}
          </button>
        </div>
      </div>

      <AccionesLeyenda acciones={['editar', 'habilitar', 'deshabilitar']} />

      <div className="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Nombre</th>
              <th>Apellido</th>
              <th>DNI</th>
              <th>Telefono</th>
              <th>Cargo</th>
              <th>Estado</th>
              <th>Proxima accion</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.length === 0 ? (
              <tr>
                <td colSpan="9" className="empty-state-message">
                  No hay directivos registrados.
                </td>
              </tr>
            ) : (
              usuarios.map((u) => (
                <Fragment key={u.id_usuario}>
                  <tr>
                    <td className="table-cell-strong">{u.usuario}</td>
                    <td>{u.directivo_nombre || '---'}</td>
                    <td>{u.directivo_apellido || '---'}</td>
                    <td>{formatDNI(u.directivo_dni) || '---'}</td>
                    <td>{u.directivo_telefono || '---'}</td>
                    <td>{u.directivo_cargo || '---'}</td>
                    <td>
                      <span className={`badge ${u.estado ? 'badge-success' : 'badge-danger'}`}>
                        {estadoLabel(u.estado)}
                      </span>
                    </td>
                    <td>{getNextAction(u)}</td>
                    <AccionesCelda
                      acciones={[
                        { accion: 'editar', onClick: () => handleEdit(u) },
                        { accion: u.estado ? 'deshabilitar' : 'habilitar', onClick: () => handleToggleEstado(u) },
                      ]}
                      entidad="administrador"
                    />
                  </tr>
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && renderFormulario()}

      {mostrarAgregarRol && (
        <AgregarRolModal
          titulo={`Agregar rol: ${ROLES_DIRECTIVOS.find((opcion) => opcion.value === rolParaAgregar)?.label || 'Administrador'}`}
          subtitulo="Seleccioná una persona existente para asignarle el rol. Se reutilizará su mismo usuario: no se crean usuarios y no se sobrescriben roles."
          personas={personasParaAgregarRol}
          onClose={() => setMostrarAgregarRol(false)}
          onAgregar={handleAgregarRol}
          guardando={guardandoAgregarRol}
          rol={rolParaAgregar}
        />
      )}

      {mostrarQuitarRol && (
        <QuitarRolModal
          titulo={`Quitar rol: ${ROLES_DIRECTIVOS.find((opcion) => opcion.value === rolParaQuitar)?.label || 'Administrador'}`}
          subtitulo={`Seleccioná una persona para quitarle el rol "${ROLES_DIRECTIVOS.find((opcion) => opcion.value === rolParaQuitar)?.label || 'Administrador'}". Se eliminará únicamente la asignación de este rol; el usuario, la persona y sus otros roles permanecerán intactos.`}
          personas={personasConRol}
          onClose={() => setMostrarQuitarRol(false)}
          onQuitar={handleQuitarRol}
          quitando={quitandoRol}
        />
      )}
    </div>
  );
}

export default Administradores;
