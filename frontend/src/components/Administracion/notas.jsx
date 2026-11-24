import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../../context/DataContext';
import { useAuth } from '../../context/AuthContext';
import PanelEstudiantes from '../Profesores/PanelEstudiantes';

function Notas({ navContext }) {
  const {
    cursosObj,
    cursoMateria,
    docentes,
    getMateriasByCurso,
    selectedCursoId,
  } = useData();
  const { user } = useAuth();
  const puedeEditar = ['admin', 'director'].includes(user?.role);
  const navNotasAplicado = useRef(null);

  // Punto 1.4: la vista consume la selección global del header. No se vuelve a
  // mostrar el selector de Año/División porque ya está en el header del rol.
  const cursoObj = useMemo(
    () =>
      (cursosObj || []).find((c) => String(c.id_curso) === String(selectedCursoId || '')) || null,
    [cursosObj, selectedCursoId],
  );
  const curso = cursoObj?.nombre_curso || '';
  const cursoId = cursoObj?.id_curso || null;

  const [materia, setMateria] = useState('');

  const materiasCurso = useMemo(
    () => (curso ? getMateriasByCurso(curso) : []),
    [curso, getMateriasByCurso],
  );

  // Al cambiar de curso, la materia elegida deja de ser válida.
  useEffect(() => {
    setMateria((prev) => (materiasCurso.includes(prev) ? prev : (materiasCurso[0] ?? '')));
  }, [materiasCurso]);

  useEffect(() => {
    const marca = navContext?.timestamp;
    if (!marca || navNotasAplicado.current === marca) return;
    const cmId = navContext?.cursoMateriaId ?? navContext?.curso_materia_id;
    const idMateria = navContext?.materiaId ?? navContext?.materia_id;
    const nombreMateria = navContext?.materiaNombre ?? navContext?.materia_nombre;
    let objetivo = '';
    if (cmId) {
      objetivo = (cursoMateria || []).find(
        (cm) => String(cm.id) === String(cmId) || String(cm.id_curso_materia) === String(cmId),
      )?.materia_nombre || '';
    }
    if (!objetivo && nombreMateria) objetivo = String(nombreMateria);
    if (!objetivo && idMateria) {
      objetivo = (cursoMateria || []).find(
        (cm) => String(cm.id_materia) === String(idMateria),
      )?.materia_nombre || '';
    }
    if (!objetivo || !materiasCurso.includes(objetivo)) return;
    navNotasAplicado.current = marca;
    setMateria(objetivo);
  }, [navContext, cursoMateria, materiasCurso]);

  const cursoMateriaEntry = useMemo(
    () =>
      (cursoMateria || []).find(
        (cm) => cm.curso_nombre === curso && cm.materia_nombre === materia,
      ) || null,
    [cursoMateria, curso, materia],
  );
  const docenteId = cursoMateriaEntry?.id_docente ?? docentes?.find((d) => d.activo !== false)?.id ?? null;
  const puedeEditarReal = puedeEditar && Boolean(docenteId);

  return (
    <div>
      <div className="card">
        <div className="card-header-flex">
          <h3><i className="fas fa-graduation-cap" aria-hidden="true" /> Calificaciones — {curso || '…'} › {materia || '…'}</h3>
          {!puedeEditarReal && <span className="badge role-badge-display">Solo lectura</span>}
        </div>

        <div className="filter-row">
          <div className="form-group-filter">
            <label htmlFor="materia-notas">Materia</label>
            <select
              id="materia-notas"
              value={materia}
              onChange={(e) => setMateria(e.target.value)}
              disabled={!curso || materiasCurso.length === 0}
            >
              {materiasCurso.length === 0 && <option value="">Sin materias</option>}
              {materiasCurso.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {cursoObj && cursoMateriaEntry ? (
        <>
          {!puedeEditarReal && (
            <div
              style={{
                background: '#eef2ff',
                borderLeft: '4px solid #4f46e5',
                borderRadius: '8px',
                padding: '10px 14px',
                fontSize: '0.9rem',
                color: '#3730a3',
                lineHeight: '1.6',
                marginBottom: '16px',
              }}
            >
              <i className="fas fa-lock" style={{ marginRight: '8px' }} aria-hidden="true" />
              Vista de solo lectura: se muestran las calificaciones, intensificaciones y previas cargadas por el docente.
            </div>
          )}
          <PanelEstudiantes
            cursoMateriaId={cursoMateriaEntry.id}
            cursoId={Number(cursoId)}
            cursoNombre={curso}
            materiaNombre={materia}
            docenteId={docenteId}
            puedeEditar={puedeEditarReal}
            mostrarBannerSuplencia={false}
            alumnoId={navContext?.alumnoId ?? navContext?.id_alumno ?? navContext?.alumno_id}
          />
        </>
      ) : (
        <div className="card empty-state-card">
          <p className="empty-state-message">
            Seleccione un curso y una materia para ver la planilla de calificaciones.
          </p>
        </div>
      )}
    </div>
  );
}

export default Notas;