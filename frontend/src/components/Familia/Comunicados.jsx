import { useData } from '../../context/DataContext';
import { parseCurso } from '../../utils/orientacion';

function comunicadoAplicaAcurso(comunicado, cursoObj, cursoNombre) {
  const alcances = Array.isArray(comunicado?.alcances) ? comunicado.alcances : [];
  if (!alcances.length) return true;
  const parts = parseCurso(cursoObj?.nombre_curso || cursoNombre || '');
  return alcances.some((alcance) => {
    const hasCiclo = alcance.id_ciclo !== null && alcance.id_ciclo !== undefined;
    const hasCurso = alcance.curso !== null && alcance.curso !== undefined;
    const hasDivision = alcance.division !== null && alcance.division !== undefined;
    const hasMateria = alcance.id_materia !== null && alcance.id_materia !== undefined;
    if (!hasCiclo && !hasCurso && !hasDivision && !hasMateria) return true;
    if (hasCiclo) {
      if (cursoObj?.id_ciclo === null || cursoObj?.id_ciclo === undefined) return false;
      if (Number(cursoObj.id_ciclo) !== Number(alcance.id_ciclo)) return false;
    }
    if (hasCurso && parts.anio !== Number(alcance.curso)) return false;
    if (hasDivision && parts.division !== Number(alcance.division)) return false;
    return true;
  });
}

function Comunicados({ hijo }) {
  const { comunicadosFamilia, cursosObj, getEstudianteById } = useData();
  const estudiante = getEstudianteById(hijo?.alumnoId);
  const cursoObj = cursosObj.find(
    (c) => c.id_curso != null && estudiante?.id_curso != null && String(c.id_curso) === String(estudiante.id_curso),
  ) || null;
  const comunicados = (Array.isArray(comunicadosFamilia) ? comunicadosFamilia : [])
    .filter((c) => comunicadoAplicaAcurso(c, cursoObj, hijo?.curso))
    .sort((a, b) => String(b.fecha || '').localeCompare(String(a.fecha || '')));

  return (
    <div className="card">
      <div className="card-header-flex">
        <h3><i className="fas fa-bullhorn" aria-hidden="true" /> Comunicados del curso {hijo.curso}</h3>
      </div>

      {comunicados.length === 0 ? (
        <p className="empty-state-message empty-state-centered">
          No hay comunicados para este curso en este momento.
        </p>
      ) : (
        <div className="familia-comunicados-list">
          {comunicados.map((c) => (
            <article key={c.id} className="familia-comunicado-item">
              <div className="familia-comunicado-meta">
                <span className="badge role-badge-display">{c.fecha}</span>
                <h4>{c.titulo}</h4>
              </div>
              <p>{c.descripcion}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export default Comunicados;
