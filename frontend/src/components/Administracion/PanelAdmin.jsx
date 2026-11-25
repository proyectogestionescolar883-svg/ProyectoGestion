import { useEffect, useMemo, useState } from 'react';
import { useData } from '../../context/DataContext';
import { useToast } from '../../context/ToastContext';
import { updateUsuario } from '../../services/api';
import { cleanDNI, formatDNI } from '../../utils/dni';
import { mensajeErrorAmigable } from '../../utils/errores';
import ProfileBanner from '../Shared/ProfileBanner';

function cleanTelefono(value) {
  if (!value) return '';
  return String(value).replace(/[^\d+\-()\s]/g, '');
}

function datosFormulario(directivo) {
  return {
    nombre: directivo?.nombre || '',
    apellido: directivo?.apellido || '',
    dni: formatDNI(directivo?.dni || ''),
    telefono: cleanTelefono(directivo?.telefono || ''),
    cargo: directivo?.cargo || '',
  };
}

function StatCard({ icon, value, label, color }) {
  return (
    <div className="stat-card">
      <i className={`fas ${icon} stat-card-icon`} style={{ color: color || 'var(--primary-color)' }} aria-hidden="true" />
      <div className="stat-card-value" style={{ color: color || 'inherit' }}>
        {value ?? '—'}
      </div>
      <div className="stat-card-label">
        {label}
      </div>
    </div>
  );
}

function PanelAdmin({ miDirectivo, user }) {
  const { estudiantes, docentes, preceptores, padresTutores, cursosObj, materiasObj, planificaciones, comunicados, actas, administradores, refreshData } = useData();
  const toast = useToast();
  const esDirector = user?.role === 'director';
  const [editando, setEditando] = useState(false);
  const [guardando, setGuardando] = useState(false);

  const directivoContext = user?.id != null
    ? administradores.find((d) => String(d.id_usuario) === String(user.id))
    : null;
  const directivo = esDirector ? (directivoContext || miDirectivo) : miDirectivo;
  const [formData, setFormData] = useState(() => datosFormulario(directivo));

  useEffect(() => {
    if (!editando) setFormData(datosFormulario(directivo));
  }, [directivo, editando]);

  const handleGuardar = async (event) => {
    event.preventDefault();
    if (!esDirector) return;
    const idUsuario = directivo?.id_usuario ?? user?.id;
    if (!idUsuario) {
      toast.error('No se pudo identificar el usuario del directivo.');
      return;
    }
    setGuardando(true);
    try {
      await updateUsuario(idUsuario, {
        nombre: formData.nombre.trim(),
        apellido: formData.apellido.trim(),
        dni: cleanDNI(formData.dni),
        telefono: cleanTelefono(formData.telefono),
        cargo: formData.cargo.trim(),
      });
      await refreshData();
      setEditando(false);
      toast.success('Mis datos personales se actualizaron correctamente.');
    } catch (err) {
      toast.error(mensajeErrorAmigable(err, 'No se pudieron actualizar tus datos personales.'));
    } finally {
      setGuardando(false);
    }
  };

  const systemStats = useMemo(() => ({
    estudiantes: (estudiantes ?? []).length,
    docentes: (docentes ?? []).length,
    preceptores: (preceptores ?? []).length,
    familias: (padresTutores ?? []).length,
    cursos: (cursosObj ?? []).length,
    materias: (materiasObj ?? []).length,
    proyectos: (planificaciones ?? []).length,
    comunicados: (comunicados ?? []).length,
    actas: (actas ?? []).length,
  }), [estudiantes, docentes, preceptores, padresTutores, cursosObj, materiasObj, planificaciones, comunicados, actas]);

  const rolLabel = user?.role === 'director' ? 'Director' : 'Administrador';

  return (
    <div className="card">
      <ProfileBanner
        icon="fa-user-shield"
        nombre={directivo ? `${directivo.apellido}, ${directivo.nombre}` : (user?.username || 'Administrador')}
        rol={rolLabel}
        estado="Activo"
      />

      <div className="profile-grid">
        {directivo ? (
          <>
            <div>
              <label className="profile-label">Nombre Completo</label>
              <p className="profile-value">{directivo.apellido}, {directivo.nombre}</p>
            </div>
            <div>
              <label className="profile-label">Documento (DNI)</label>
              <p className="profile-value">{formatDNI(directivo.dni)}</p>
            </div>
            {directivo.telefono && (
              <div>
                <label className="profile-label">Teléfono de Contacto</label>
                <p className="profile-value">{directivo.telefono}</p>
              </div>
            )}
            {directivo.cargo && (
              <div>
                <label className="profile-label">Cargo</label>
                <p className="profile-value">{directivo.cargo}</p>
              </div>
            )}
          </>
        ) : (
          <div>
            <label className="profile-label">Perfil</label>
            <p className="profile-value">Sin datos de perfil cargados.</p>
          </div>
        )}
        <div>
          <label className="profile-label">Usuario</label>
          <p className="profile-value">{user?.username || (directivo ? `${directivo.apellido}, ${directivo.nombre}` : '—')}</p>
        </div>
        <div>
          <label className="profile-label">Rol</label>
          <p className="profile-value">{rolLabel}</p>
        </div>
      </div>

      {esDirector && (
        <div className="inline-form-container">
          <section className="preceptor-form-section">
            <h4>Mis datos personales</h4>
            {!editando ? (
              <>
                <div className="profile-grid">
                  <div>
                    <label className="profile-label">Nombre</label>
                    <p className="profile-value">{directivo?.nombre || '—'}</p>
                  </div>
                  <div>
                    <label className="profile-label">Apellido</label>
                    <p className="profile-value">{directivo?.apellido || '—'}</p>
                  </div>
                  <div>
                    <label className="profile-label">DNI</label>
                    <p className="profile-value">{formatDNI(directivo?.dni) || '—'}</p>
                  </div>
                  <div>
                    <label className="profile-label">Teléfono</label>
                    <p className="profile-value">{directivo?.telefono || '—'}</p>
                  </div>
                  <div>
                    <label className="profile-label">Cargo</label>
                    <p className="profile-value">{directivo?.cargo || '—'}</p>
                  </div>
                </div>
                <div className="standard-modal-footer">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setEditando(true)}
                    disabled={!directivo}
                  >
                    <i className="fas fa-pen" aria-hidden="true" /> Editar mis datos
                  </button>
                </div>
              </>
            ) : (
              <form className="preceptor-form" onSubmit={handleGuardar}>
                <div className="preceptor-form-row preceptor-form-row--two">
                  <div className="form-group-filter">
                    <label htmlFor="mi-nombre">Nombre</label>
                    <input
                      id="mi-nombre"
                      type="text"
                      value={formData.nombre}
                      onChange={(e) => setFormData((prev) => ({ ...prev, nombre: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="form-group-filter">
                    <label htmlFor="mi-apellido">Apellido</label>
                    <input
                      id="mi-apellido"
                      type="text"
                      value={formData.apellido}
                      onChange={(e) => setFormData((prev) => ({ ...prev, apellido: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="form-group-filter">
                    <label htmlFor="mi-dni">DNI</label>
                    <input
                      id="mi-dni"
                      type="text"
                      value={formData.dni}
                      onChange={(e) => setFormData((prev) => ({ ...prev, dni: formatDNI(e.target.value) }))}
                      required
                    />
                  </div>
                  <div className="form-group-filter">
                    <label htmlFor="mi-telefono">Teléfono</label>
                    <input
                      id="mi-telefono"
                      type="text"
                      value={formData.telefono}
                      onChange={(e) => setFormData((prev) => ({ ...prev, telefono: cleanTelefono(e.target.value) }))}
                    />
                  </div>
                  <div className="form-group-filter">
                    <label htmlFor="mi-cargo">Cargo</label>
                    <input
                      id="mi-cargo"
                      type="text"
                      value={formData.cargo}
                      onChange={(e) => setFormData((prev) => ({ ...prev, cargo: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="standard-modal-footer">
                  <button type="submit" className="btn btn-primary" disabled={guardando}>
                    <i className="fas fa-save" aria-hidden="true" /> Guardar
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setEditando(false)}
                    disabled={guardando}
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}

      <div className="stats-grid">
        <StatCard icon="fa-user-graduate" value={systemStats.estudiantes} label="Estudiantes" />
        <StatCard icon="fa-chalkboard-teacher" value={systemStats.docentes} label="Docentes" />
        <StatCard icon="fa-user-tie" value={systemStats.preceptores} label="Preceptores" />
        <StatCard icon="fa-users" value={systemStats.familias} label="Familias" />
        <StatCard icon="fa-school" value={systemStats.cursos} label="Cursos" />
        <StatCard icon="fa-book" value={systemStats.materias} label="Materias" />
        <StatCard icon="fa-folder-open" value={systemStats.proyectos} label="Proyectos" />
        <StatCard icon="fa-bullhorn" value={systemStats.comunicados} label="Comunicados" />
        <StatCard icon="fa-file-signature" value={systemStats.actas} label="Actas" />
      </div>
    </div>
  );
}

export default PanelAdmin;
