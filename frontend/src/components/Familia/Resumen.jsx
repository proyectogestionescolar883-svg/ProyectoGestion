import { useData } from '../../context/DataContext';
import { useAsistenciasAlumno } from '../../hooks/useAsistenciasAlumno';
import { cursoConOrientacion } from '../../utils/orientacion';
import { formatDNI } from '../../utils/dni';

const clamp = (n) => Math.max(0, Math.min(100, Math.round(n)));

function StatTile({ icon, label, value, color }) {
  return (
    <div className="card familia-stat-card">
      <i className={`fas ${icon} familia-stat-icon`} style={color ? { color } : undefined} aria-hidden="true" />
      <span className="familia-stat-label">{label}</span>
      <strong className="familia-stat-value">{value}</strong>
    </div>
  );
}

function EstadoTile({ label, estado, color }) {
  return (
    <div className="card familia-stat-card">
      <i className="fas fa-medal familia-stat-icon" style={{ color }} aria-hidden="true" />
      <span className="familia-stat-label">{label}</span>
      <span className="familia-estado-pill" style={{ backgroundColor: `${color}1a`, color }}>
        {estado}
      </span>
    </div>
  );
}

function Resumen({ hijo }) {
  const { calificacionesFamilia, cursosObj, getEstudianteById, materiasPorCurso } = useData();
  const estudiante = getEstudianteById(hijo?.alumnoId);
  const cursoObj = (Array.isArray(cursosObj) ? cursosObj : []).find(
    (c) => c.id_curso != null && estudiante?.id_curso != null && String(c.id_curso) === String(estudiante.id_curso),
  ) || null;
  const turno = cursoObj?.turno_calculado || '—';
  const preceptor = cursoObj?.preceptor_nombre_completo || '—';
  const calificaciones = (Array.isArray(calificacionesFamilia) ? calificacionesFamilia : []).filter(
    (c) => c.alumnoId != null && hijo?.alumnoId != null && String(c.alumnoId) === String(hijo.alumnoId),
  );

  // Las asistencias no salen del contexto global: ahí `asistenciasRaw` está
  // pineado a `[]` (tabla completa sin paginar) y por eso el Resumen mostraba
  // 0/0/0/0 aunque hubiera cargas. Se piden acotadas por alumno.
  const {
    presente: presentes,
    ausente: ausentes,
    tarde: tardanzas,
    total: registradas,
  } = useAsistenciasAlumno(estudiante?.id);

  const porcentajeAsistencia =
    registradas > 0 ? clamp((presentes / registradas) * 100) : 0;

  const notas = calificaciones
    .flatMap((c) => [c.nota1, c.nota2])
    .filter((n) => n !== '' && n !== null && n !== undefined && !Number.isNaN(Number(n)))
    .map(Number);
  const promedio = notas.length > 0
    ? (notas.reduce((acc, n) => acc + n, 0) / notas.length).toFixed(1)
    : '—';

  const promedioNum = Number(promedio);
  let estado = 'Sin calificaciones';
  let estadoColor = '#9aa5b1';
  if (!Number.isNaN(promedioNum) && notas.length > 0) {
    if (promedioNum >= 7) {
      estado = 'Promocionado';
      estadoColor = '#15803d';
    } else if (promedioNum >= 4) {
      estado = 'En condiciones de promover';
      estadoColor = '#b45309';
    } else {
      estado = 'En seguimiento';
      estadoColor = '#b91c1c';
    }
  }

  const nombreCurso = cursoObj?.nombre_curso || hijo?.curso || '';
  const materiasCount = materiasPorCurso[nombreCurso]?.length ?? '—';
  const cursoParaMostrar = cursoObj || hijo?.curso;

  return (
    <div>
      <div className="familia-resumen-grid">
        <StatTile icon="fa-graduation-cap" label="Curso" value={cursoConOrientacion(cursoParaMostrar)} />
        <StatTile icon="fa-clock" label="Turno" value={turno} />
        <StatTile icon="fa-users" label="Vínculo" value={hijo.vinculo || '—'} />
        <EstadoTile label="Estado académico" estado={estado} color={estadoColor} />
      </div>

      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header-flex">
          <h3><i className="fas fa-chart-pie" aria-hidden="true" /> Resumen académico</h3>
        </div>
        <div className="familia-academico-grid">
          <div className="card familia-academico-item center">
            <span className="familia-stat-label">Promedio general</span>
            <strong className="familia-stat-value font-accent">{promedio}</strong>
          </div>
          <div className="card familia-academico-item">
            <span className="familia-stat-label">Asistencia reciente</span>
            <strong className="familia-stat-value font-accent">{porcentajeAsistencia}%</strong>
            <div className="familia-asist-bar">
              <div className="familia-asist-bar-fill" style={{ width: `${porcentajeAsistencia}%` }} />
            </div>
            <div className="familia-asist-nums">
              <span className="ok">Presentes: <strong>{presentes}</strong></span>
              <span>Ausentes: <strong>{ausentes}</strong></span>
              <span>Tardanzas: <strong>{tardanzas}</strong></span>
              <span>Registros: <strong>{registradas}</strong></span>
            </div>
          </div>
          <div className="card familia-academico-item center">
            <span className="familia-stat-label">Materias del ciclo</span>
            <strong className="familia-stat-value font-accent">{materiasCount}</strong>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header-flex">
          <h3><i className="fas fa-user-graduate" aria-hidden="true" /> Información del estudiante</h3>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap' }}>
          <div className="familia-avatar">
            <i className="fas fa-user-graduate" aria-hidden="true" />
          </div>
          <div>
            <strong className="familia-stat-value">{hijo.nombre}</strong>
            <div className="familia-hijo-pill" style={{ marginTop: '6px' }}>
              {cursoConOrientacion(cursoParaMostrar)}
            </div>
          </div>
        </div>
        <div className="familia-chip-grid">
          <div className="familia-chip">
            <span className="familia-chip-label">DNI</span>
            <span className="familia-chip-value">{hijo.dni && hijo.dni !== '—' ? formatDNI(hijo.dni) : '—'}</span>
          </div>
          <div className="familia-chip">
            <span className="familia-chip-label">Fecha de nacimiento</span>
            <span className="familia-chip-value">{estudiante?.fecha_nacimiento || '—'}</span>
          </div>
          <div className="familia-chip">
            <span className="familia-chip-label">Curso</span>
            <span className="familia-chip-value">{cursoConOrientacion(cursoParaMostrar)}</span>
          </div>
          <div className="familia-chip">
            <span className="familia-chip-label">Ciclo lectivo</span>
            <span className="familia-chip-value">{cursoObj?.ciclo_anio || '—'}</span>
          </div>
          <div className="familia-chip">
            <span className="familia-chip-label">Turno</span>
            <span className="familia-chip-value">{turno}</span>
          </div>
          <div className="familia-chip">
            <span className="familia-chip-label">Preceptor</span>
            <span className="familia-chip-value">{preceptor}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Resumen;